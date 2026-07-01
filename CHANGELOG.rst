===================================
ansible.aap\_snapshot Release Notes
===================================

.. contents:: Topics

v1.0.2
======

Minor Changes
-------------

- Skip artifact transfer to temporary pod when the file already exists with a matching checksum.

Breaking Changes / Porting Guide
--------------------------------

- The ``artifact_file`` variable is now required for import and verify playbooks. It no longer defaults to ``aap-snapshot-latest.tar``.

Bugfixes
--------

- Cascade idle_deployment false directly to child CRs when un-idling to work around AAP-77947 where the gateway operator fails to propagate it.
- Reconcile gateway before waiting for other components to clear stale service_nodes that block the gateway operator reconciliation loop.
- Remove aap-snapshot-latest.tar symlink from export packaging - k8s_cp copies the symlink instead of the file content, breaking imports.
- Remove statefulset idle wait that caused timeout failures during import - the operator does not scale statefulsets during idle.
- Resolve symlinks and relative paths to absolute real paths before artifact transfer to prevent dangling links inside the temporary pod.
- Set database.idle_disabled on the AAP CR before idling to keep postgres running during database import.

v1.0.1
======

v1.0.0
======

Breaking Changes / Porting Guide
--------------------------------

- Role namespace and instance name variables are now decoupled from ``ocp_utils`` defaults. Use ``-e ocp_namespace=<ns>`` and ``-e aap_instance_name=<name>`` instead of ``-e ocp_utils_ocp_namespace=<ns>`` and ``-e ocp_utils_aap_instance_name=<name>``. The ``ocp_utils_*`` variables still work for the ``ocp_utils`` role itself but no longer propagate to other roles.

Bugfixes
--------

- Idle wait now checks Deployment and StatefulSet replica counts instead of pod label selectors that matched no pods. The previous ``app.kubernetes.io/managed-by`` value-match selector did not match actual pod labels, causing the wait to pass immediately and database restores to run against live pods with active connections.
- Idle wait scoped to AAP-managed resources using the ``app.kubernetes.io/part-of`` label selector, preventing false matches against non-AAP workloads in shared namespaces.
- User-provided extra vars ``ocp_namespace`` and ``aap_instance_name`` are now respected by all roles. Previously, roles hardcoded the namespace to ``aap`` or chained through ``ocp_utils`` defaults that only resolved when ``ocp_utils`` was explicitly included first, silently ignoring ``-e ocp_namespace=custom-ns``.

New Plugins
-----------

Filter
~~~~~~

- parse_aap_version - Parse an AAP version string into structured components

New Modules
-----------

- aap_component_info - Discover AAP component information from RPM installations
- validate_migration_artifact - Validate an AAP migration artifact

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
