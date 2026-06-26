# Ansible Collection - ansible.aap_snapshot

## Overview

This collection provides a complete migration framework for Ansible Automation
Platform (AAP) clusters. It exports platform data into a portable artifact and
imports it into a new deployment, supporting migration across all AAP
installation types.

**Supported migration paths:**

| Source | Target |
|--------|--------|
| RPM Installer | Containerized Installer |
| RPM Installer | OCP Operator |
| Containerized Installer | Containerized Installer |
| Containerized Installer | OCP Operator |
| OCP Operator | OCP Operator |

The collection handles four AAP components: Controller, Hub (with Pulp
content), Gateway, and EDA. Components are processed conditionally based on
what is present in the inventory and artifact.

## Quick Start

### Export

Create a migration artifact from a running AAP deployment:

```bash
# From an RPM deployment
ansible-playbook -i inventory ansible.aap_snapshot.artifact_export -e aap_platform=rpm

# From a containerized deployment
ansible-playbook -i inventory ansible.aap_snapshot.artifact_export -e aap_platform=containerized

# From an OCP operator deployment
ansible-playbook -i inventory ansible.aap_snapshot.artifact_export \
  -e aap_platform=operator \
  -e ocp_namespace=aap \
  -e aap_instance_name=aap
```

### Import

Restore a migration artifact into a target AAP deployment:

```bash
# Into a containerized deployment
ansible-playbook -i inventory ansible.aap_snapshot.artifact_import \
  -e aap_platform=containerized \
  -e artifact_dir=/path/to/artifacts \
  -e artifact=aap-snapshot-latest.tar

# Into an OCP operator deployment
ansible-playbook -i inventory ansible.aap_snapshot.artifact_import \
  -e aap_platform=operator \
  -e artifact_dir=/path/to/artifacts \
  -e artifact=aap-snapshot-latest.tar \
  -e ocp_namespace=aap \
  -e aap_instance_name=aap
```

### Verify

Validate an artifact without importing it:

```bash
ansible-playbook ansible.aap_snapshot.artifact_verify \
  -e artifact_dir=/path/to/artifacts \
  -e artifact=aap-snapshot-latest.tar
```

## Requirements

- Ansible core >= 2.16.0

### Collection Dependencies

| Collection | Version |
|------------|---------|
| `ansible.posix` | `>=1.6.0` |
| `community.postgresql` | `>=3.0.0` |
| `containers.podman` | `>=1.14.0` |
| `community.general` | `>=10.7.0` |
| `kubernetes.core` | `>=3.0.0` |

### Platform Requirements

- **RPM export:** SSH access to component hosts, `become` privileges
- **Containerized:** SSH access to component hosts, podman access
- **OCP Operator:** `kubeconfig` with cluster-admin or namespace-admin access

## Key Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `aap_platform` | Yes | - | Platform type: `rpm`, `containerized`, or `operator` |
| `artifact_dir` | No | `$PWD` | Directory for artifact creation/extraction |
| `artifact` | No | `aap-snapshot-latest.tar` | Artifact filename |
| `ocp_namespace` | OCP | `aap` | OpenShift namespace |
| `aap_instance_name` | OCP | `aap` | AAP CR instance name |
| `export_hub_content` | No | `true` | Include Pulp content data in artifact |
| `postgresql_db_type` | No | `managed` | Database topology: `managed` or `external` |

See [docs/variables.md](docs/variables.md) for the complete variable reference.

## Documentation

- [Architecture](docs/architecture.md) - collection structure, role hierarchy, plugin catalog
- [Artifact Format](docs/artifact-format.md) - SDP v1.0 artifact specification
- [Variables](docs/variables.md) - complete variable reference
- [Workflows](docs/workflows.md) - step-by-step export, import, and reconcile workflows

## Collection Structure

```
aap/migration/
├── playbooks/
│   ├── artifact_export.yaml          # Export entry point
│   ├── artifact_import.yaml          # Import entry point
│   ├── artifact_verify.yaml          # Verification entry point
│   ├── containerized/                # Containerized-specific playbooks
│   ├── rpm/                          # RPM-specific playbooks
│   ├── ocp/                          # OCP-specific playbooks
│   └── common/                       # Shared playbooks
├── roles/
│   ├── artifact/                     # Artifact lifecycle management
│   ├── common/                       # Inventory group normalization
│   ├── preflight/                    # Pre-migration validation
│   ├── export_component/             # Generic export orchestrator
│   ├── export_{controller,hub,gateway,eda}/
│   ├── import_component/             # Generic import orchestrator
│   ├── import_{controller,hub,gateway,eda}/
│   ├── reconcile_{controller,hub,gateway,eda}/
│   ├── automation{controller,hub,gateway,eda}/
│   ├── postgresql/                   # Database operations
│   ├── ocp_utils/                    # OCP cluster operations
│   └── ...
├── plugins/
│   ├── modules/
│   │   ├── aap_component_info.py     # RPM component discovery
│   │   └── validate_migration_artifact.py
│   └── filter/
│       └── aap_version.py            # Version string parsing
└── docs/
```

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and the pull request process.

## Reporting Issues

To report a bug or request a feature, please [open an issue](https://github.com/ansible-automation-platform/aap-snapshot-collection/issues).

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE) for details.
