===================================
ansible.aap\_snapshot Release Notes
===================================

.. contents:: Topics

v0.0.1
======

Major Changes
-------------

- Add Python modules ``aap_component_info`` for RPM component discovery and ``validate_migration_artifact`` for artifact validation, and ``parse_aap_version`` filter plugin for version string parsing.
- Add full export workflow for RPM deployments with SDP v1.0 artifact format, component export roles for controller, hub (with Pulp content), gateway, and EDA, and standalone artifact verification playbook.
- Add import workflow for OCP targets with database restore, secret synchronization, operator lifecycle management, temporary migration resources, and post-import reconciliation for all four AAP components.

Breaking Changes / Porting Guide
--------------------------------

- aap_component_info - The ``gather`` parameter now enforces ``choices`` validation. Unrecognized values that were previously accepted silently will now produce a validation error.
