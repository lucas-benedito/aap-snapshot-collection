# Changelog

## [1.0.0]

### Added

- **Export workflow** - full artifact export from RPM, containerized, and OCP deployments
  - SDP v1.0 artifact format with manifest, checksums, and versioning
  - Component export roles for controller, hub, gateway, and EDA
  - Hub content (Pulp) export support
  - Custom config export for RPM controller
- **Import workflow** - artifact import to containerized and OCP targets
  - Database restore with automatic credential extraction
  - Secret synchronization (Kubernetes Secrets and podman secrets)
  - OCP support with temporary migration resources and operator lifecycle
- **Reconcile workflow** - post-import state corrections
  - Gateway: schema migrations, vestigial object cleanup, resource server reset
  - Controller: orphaned instance deprovisioning
  - Hub: Pulp content repair
  - EDA: resource sync
- **Verification** - standalone artifact validation playbook
- **Modules** - `aap_component_info` (RPM discovery), `validate_migration_artifact` (artifact validation)
- **Filters** - `parse_aap_version` (version string parsing)
- **Shared infrastructure** - `ocp_utils` role, `postgresql` role, inventory group normalization
