#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from ansible.errors import AnsibleFilterError


def parse_aap_version(version_string):
    """Parse an AAP version string into structured components.

    Handles formats: "2.6.3", "2.7", "2.6.3-rc1", "15.2"

    Returns dict with keys: major, minor, patch, major_minor, full
    """
    if not isinstance(version_string, str):
        raise AnsibleFilterError(f"parse_aap_version expects a string, got {type(version_string).__name__}")

    version_string = version_string.strip()

    # Strip Operator CSV prefix (e.g. "aap-operator.v2.6.0-0.1777410689")
    csv_match = re.match(r"^[a-z0-9-]+\.v", version_string)
    prefix_len = csv_match.end() if csv_match else 0
    parseable = version_string[prefix_len:]

    match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", parseable)

    if not match:
        raise AnsibleFilterError(f"Cannot parse version string: '{version_string}'. " f"Expected format: MAJOR.MINOR[.PATCH]")

    major = match.group(1)
    minor = match.group(2)
    patch = match.group(3) or "0"

    result = {
        "major": major,
        "minor": minor,
        "patch": patch,
        "major_minor": f"{major}.{minor}",
        "full": version_string,
    }

    remainder = parseable[match.end():]
    if remainder.startswith("-"):
        release = remainder[1:]
        parts = release.split(".", 1)
        if len(parts) == 2:
            result["timestamp"] = parts[1]

    return result


class FilterModule:
    def filters(self):
        return {
            "parse_aap_version": parse_aap_version,
        }
