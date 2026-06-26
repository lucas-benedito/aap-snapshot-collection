#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: aap_component_info
author: Red Hat (@RedHatOfficial)
short_description: Discover AAP component information from RPM installations
description:
  - Gathers version, database credentials, and secret keys from an AAP
    component installed via RPM.
  - Reads Django settings directly via Python import instead of parsing
    shell command output.
  - Only works on RPM-based AAP hosts where the component's Django
    application is importable. For containerized hosts, use
    podman_container_exec with manage commands instead.
version_added: "1.0.0"

options:
  component:
    description:
      - The AAP component to gather information from.
    required: true
    type: str
    choices: [controller, hub, gateway, eda]
  gather:
    description:
      - List of information types to gather.
    type: list
    elements: str
    default: [version, db_credentials, secrets]
    choices: [version, db_credentials, secrets]
  manage_cmd:
    description:
      - Path or name of the component's manage command.
      - Defaults are component-specific (awx-manage, pulpcore-manager, etc.).
    type: str
  environment:
    description:
      - Extra environment variables to set before Django initialization.
    type: dict
    default: {}

notes:
  - This module must run on the RPM host where the component is installed.
  - For containerized deployments, use podman_container_exec with the
    manage command instead.
"""

EXAMPLES = r"""
- name: Gather all info from controller
  ansible.aap_snapshot.aap_component_info:
    component: controller
  become: true
  become_user: awx
  register: controller_info

- name: Gather only version from hub
  ansible.aap_snapshot.aap_component_info:
    component: hub
    gather: [version]
  become: true
  become_user: pulp

- name: Use gathered DB credentials
  ansible.builtin.debug:
    msg: "DB host is {{ controller_info.db_credentials.host }}"
"""

RETURN = r"""
version:
  description: Component version string.
  returned: when 'version' in gather
  type: str
  sample: "4.6.15"
db_credentials:
  description: Database connection parameters from Django settings.
  returned: when 'db_credentials' in gather
  type: dict
  contains:
    host:
      description: Database hostname.
      type: str
    port:
      description: Database port.
      type: str
    name:
      description: Database name.
      type: str
    user:
      description: Database username.
      type: str
    password:
      description: Database password. Callers MUST use no_log on the task.
      type: str
    options:
      description: Additional connection options (SSL certs, etc.).
      type: dict
secrets:
  description: Component-specific secret keys and credentials. Callers MUST use no_log on the task.
  returned: when 'secrets' in gather
  type: dict
aap_version:
  description: AAP platform version (only returned for gateway component).
  returned: when component is gateway and 'version' in gather
  type: str
  sample: "2.6.3"
"""

import ast
import json
import os
import subprocess

from ansible.module_utils.basic import AnsibleModule

COMPONENT_DEFAULTS = {
    "controller": {
        "manage_cmd": "awx-manage",
        "package_name": "awx",
        "secret_key_file": "/etc/tower/SECRET_KEY",
        "settings_module": None,
    },
    "hub": {
        "manage_cmd": "pulpcore-manager",
        "package_name": "pulpcore",
        "secret_key_file": None,
        "settings_module": "pulpcore.app.settings",
        "settings_file": "/etc/pulp/settings.py",
        "db_fields_key_file": "/etc/pulp/certs/database_fields.symmetric.key",
    },
    "gateway": {
        "manage_cmd": "aap-gateway-manage",
        "package_name": "aap-gateway",
        "secret_key_file": "/etc/ansible-automation-platform/gateway/SECRET_KEY",
        "version_file": "/etc/ansible-automation-platform/VERSION",
        "settings_module": None,
    },
    "eda": {
        "manage_cmd": "aap-eda-manage",
        "package_name": "aap_eda",
        "secret_key_file": "/etc/ansible-automation-platform/eda/SECRET_KEY",
        "settings_module": None,
    },
}


def _get_version(manage_cmd, package_name):
    cmd_str = f"from importlib.metadata import version; print(version('{package_name}'))"
    for shell_args in [["--no-imports"], []]:
        try:
            result = subprocess.run(
                [manage_cmd, "shell"] + shell_args + ["-c", cmd_str],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().splitlines()
                return lines[-1].strip(), None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return None, f"Version discovery failed for {package_name} via {manage_cmd}"


_DB_EXTRACT_TEMPLATE = (
    "{import_line}; "
    "import json; "
    "db = {settings_var}.DATABASES['default']; "
    "print(json.dumps({{"
    "'host': db.get('HOST', ''), "
    "'port': str(db.get('PORT', '5432')), "
    "'name': db.get('NAME', ''), "
    "'user': db.get('USER', ''), "
    "'password': db.get('PASSWORD', ''), "
    "'options': db.get('OPTIONS', {{}})"
    "}}))"
)


def _get_db_credentials(manage_cmd, component, environment):
    try:
        if component == "hub":
            cmd_str = _DB_EXTRACT_TEMPLATE.format(
                import_line="from dynaconf import settings as dynaconf_settings",
                settings_var="dynaconf_settings",
            )
        else:
            cmd_str = _DB_EXTRACT_TEMPLATE.format(
                import_line="from django.conf import settings",
                settings_var="settings",
            )

        env = os.environ.copy()
        env.update(environment)

        result = subprocess.run(
            [manage_cmd, "shell", "--no-imports", "-c", cmd_str],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            check=False,
        )

        if result.returncode != 0:
            result = subprocess.run(
                [manage_cmd, "shell", "-c", cmd_str],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                check=False,
            )

        if result.returncode != 0:
            return None, f"DB credential discovery failed: {result.stderr.strip()}"

        # awx-manage shell may emit warnings before the JSON output
        for line in reversed(result.stdout.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line), None
        return None, "DB credential discovery failed: no JSON found in output"
    except Exception as e:
        return None, f"DB credential discovery failed: {str(e)}"


def _read_file_secret(filepath):
    try:
        with open(filepath, "r") as f:
            return f.read().strip(), None
    except FileNotFoundError:
        return None, f"Secret file not found: {filepath}"
    except PermissionError:
        return None, f"Permission denied reading: {filepath}"


def _get_hub_secret_key(settings_file):
    try:
        with open(settings_file, "r") as f:
            content = f.read()

        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SECRET_KEY":
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value), None

        return None, "SECRET_KEY not found as a constant in settings.py"
    except Exception as e:
        return None, f"Failed to parse settings.py: {str(e)}"


def _get_gateway_resource_keys(manage_cmd):
    keys = {}
    warnings = []
    for cluster_name in ["controller", "hub", "eda"]:
        try:
            cmd_str = (
                "import json; "
                f"clusters = ServiceCluster.objects.filter(name='{cluster_name}'); "
                "result = None\n"
                "if clusters.exists():\n"
                "  active_keys = clusters.first().service_keys.filter(is_active=True)\n"
                "  if active_keys.exists():\n"
                "    result = active_keys.first().secret\n"
                "print(json.dumps({'secret': result}))"
            )

            result = subprocess.run(
                [manage_cmd, "shell_plus", "--quiet-load", "--no-imports", "-c", cmd_str],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                result = subprocess.run(
                    [manage_cmd, "shell_plus", "--quiet-load", "-c", cmd_str],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                if data.get("secret"):
                    keys[f"{cluster_name}_resource_key"] = data["secret"]
            elif result.returncode != 0:
                warnings.append(f"Failed to query {cluster_name} resource key: " f"{result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            warnings.append(f"Timed out querying {cluster_name} resource key")
        except Exception as e:
            warnings.append(f"Error querying {cluster_name} resource key: {e}")

    return keys, warnings


def _get_secrets(component, defaults, manage_cmd):
    secrets = {}
    errors = []

    secret_key_file = defaults.get("secret_key_file")
    if secret_key_file:
        value, err = _read_file_secret(secret_key_file)
        if err:
            errors.append(err)
        else:
            secrets[f"{component}_secret_key"] = value

    if component == "hub":
        settings_file = defaults.get("settings_file", "")
        value, err = _get_hub_secret_key(settings_file)
        if err:
            errors.append(err)
        else:
            secrets["hub_secret"] = value

        db_key_file = defaults.get("db_fields_key_file", "")
        value, err = _read_file_secret(db_key_file)
        if err:
            errors.append(err)
        else:
            secrets["hub_db_fields_encryption_key"] = value

    if component == "gateway":
        resource_keys, resource_warnings = _get_gateway_resource_keys(manage_cmd)
        secrets.update(resource_keys)
        errors.extend(resource_warnings)

    return secrets, errors


def main():
    module = AnsibleModule(
        argument_spec=dict(
            component=dict(
                type="str",
                required=True,
                choices=["controller", "hub", "gateway", "eda"],
            ),
            gather=dict(
                type="list",
                elements="str",
                default=["version", "db_credentials", "secrets"],
                choices=["version", "db_credentials", "secrets"],
            ),
            manage_cmd=dict(type="str", default=None),
            environment=dict(type="dict", default={}),
        ),
        supports_check_mode=True,
    )

    component = module.params["component"]
    gather = module.params["gather"]
    defaults = COMPONENT_DEFAULTS[component]
    manage_cmd = module.params["manage_cmd"] or defaults["manage_cmd"]
    environment = module.params["environment"]

    if defaults.get("settings_module"):
        environment.setdefault("DJANGO_SETTINGS_MODULE", defaults["settings_module"])
        if component == "hub":
            environment.setdefault("PULP_SETTINGS", "/etc/pulp/settings.py")

    result = dict(changed=False)
    all_errors = []

    package_name = defaults.get("package_name", "")

    if "version" in gather:
        version, err = _get_version(manage_cmd, package_name)
        if err:
            all_errors.append(err)
        elif not version:
            all_errors.append(f"Empty version output from {manage_cmd}")
        else:
            result["version"] = version

        if component == "gateway":
            version_file = defaults.get("version_file", "")
            aap_version, err = _read_file_secret(version_file)
            if err:
                all_errors.append(err)
            else:
                result["aap_version"] = aap_version

    if "db_credentials" in gather:
        creds, err = _get_db_credentials(manage_cmd, component, environment)
        if err:
            all_errors.append(err)
        else:
            result["db_credentials"] = creds

    if "secrets" in gather:
        secrets, errs = _get_secrets(component, defaults, manage_cmd)
        all_errors.extend(errs)
        result["secrets"] = secrets

    if all_errors:
        module.fail_json(msg="; ".join(all_errors), **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
