# Debugging

Common failure scenarios and recovery procedures for the
`ansible.aap_snapshot` collection.

## OCP Import Failures

When an OCP import fails mid-run, the `always` block in the import playbook
attempts automatic recovery: it scales operators back to 1 replica and
un-idles the AAP CR. However, some resources require manual cleanup depending
on where the failure occurred.

### Leftover Temporary Resources

During OCP import, the playbook creates a temporary PVC and PostgreSQL
deployment to stage the artifact and run database restores. By default
(`keep_temp_on_failure: true`), these resources are preserved on failure so
you can inspect the artifact contents and database state inside the
temporary pod.

**Identify leftover resources:**

```bash
oc get deployment,pvc -n <namespace> | grep aap-snapshot-temp
```

Default resource names:

| Resource | Default Name |
|----------|-------------|
| Deployment | `aap-snapshot-temp-postgres` |
| PVC | `aap-snapshot-temp` |

**Clean up when done investigating:**

```bash
oc delete deployment aap-snapshot-temp-postgres -n <namespace>
oc delete pvc aap-snapshot-temp -n <namespace>
```

**To auto-clean on failure instead**, set `keep_temp_on_failure=false`:

```bash
ansible-playbook ansible.aap_snapshot.artifact_import \
  -e keep_temp_on_failure=false \
  ...
```

### AAP CR Stuck in Idle State

The import playbook sets `spec.idle_aap: true` on the AAP CR before restoring
databases. The `always` block attempts to un-idle automatically, but if that
recovery step also fails, AAP remains idled with all component pods scaled
to zero.

**Check if AAP is idled:**

```bash
oc get aap <instance-name> -n <namespace> \
  -o jsonpath='{.spec.idle_aap}'; echo
```

If this returns `true`, AAP is still idled.

**Un-idle manually:**

```bash
oc patch aap <instance-name> -n <namespace> --type merge \
  -p '{"spec":{"idle_aap":false,"database":{"idle_disabled":false}}}'
```

After un-idling, the operator reconciles and restarts component pods. If
child CRs (AutomationController, AutomationHub, EDA) are also stuck with
`idle_deployment: true`, patch them individually:

```bash
# Example for controller
oc get automationcontroller -n <namespace> -o name | \
  xargs -I{} oc patch {} -n <namespace> --type merge \
  -p '{"spec":{"idle_deployment":false}}'
```

### Operators Stuck at Zero Replicas

The import playbook scales the gateway and controller operator deployments
to zero before database restores. Recovery scales them back to 1, but if
recovery fails the operators stay down and no reconciliation occurs.

**Check operator replica counts:**

```bash
oc get deployment -n <namespace> \
  aap-gateway-operator-controller-manager \
  automation-controller-operator-controller-manager
```

**Scale back manually:**

```bash
oc scale deployment aap-gateway-operator-controller-manager \
  --replicas=1 -n <namespace>
oc scale deployment automation-controller-operator-controller-manager \
  --replicas=1 -n <namespace>
```

### Pods in CrashLoopBackOff After Import

If component pods crash after database restore, the most common causes are:

1. **Secret key mismatch** — the Django SECRET_KEY or database encryption key
   in the Kubernetes Secret doesn't match what's in the restored database.
   Check the reconcile phase output for secret patching errors.

2. **Schema version mismatch** — the restored database schema is from a
   different AAP version than the target operator. The gateway reconcile
   runs `aap-gateway-manage migrate` to apply schema differences, but large
   version gaps may cause migration failures.

3. **Temporary pod was cleaned up too early** — if the temp PostgreSQL pod
   was deleted before all restores completed, some databases may be partially
   restored.

**Inspect pod logs:**

```bash
# Gateway
oc logs -n <namespace> -l app.kubernetes.io/component=<instance-name>-gateway \
  -c api --tail=50

# Controller
oc logs -n <namespace> -l app.kubernetes.io/component=<instance-name>-controller \
  -c <instance-name>-task --tail=50
```

**Nuclear recovery** — delete the AAP CR and recreate it for a fresh
deployment, then re-run the import:

```bash
oc delete aap <instance-name> -n <namespace>
# Wait for all pods to terminate
oc get pods -n <namespace> -w
# Recreate the CR and re-run import
```

## Export Failures

### Permission Denied on Artifact Directory

If the export fails with permission errors creating or writing to the
artifact directory, check whether `--become` was passed on the CLI. The
collection manages privilege escalation internally per-play — a global
`--become` causes localhost plays to create directories as root, which
blocks later fetch operations that run as the regular user.

**Fix:** Remove `--become` from the CLI invocation. The RPM export
sub-playbooks set `become: true` only on plays that require root access
on remote hosts.

If a root-owned artifact directory already exists from a failed run:

```bash
sudo rm -rf ./artifact/
```

### Database Export Timeouts

Large databases may exceed the default `pg_dump` timeout. The export uses
async tasks — check the async status file on the remote host if the task
reports a timeout:

```bash
ssh <host> "ls -la /tmp/backups/automation-platform/"
```

## Artifact Verification Failures

### Checksum Mismatch

If `artifact_verify` reports checksum failures, the artifact may have been
corrupted during transfer. Re-export from the source environment or verify
the file was transferred with an integrity check:

```bash
sha256sum <artifact-file>
# Compare against the .sha256 sidecar file created during export
cat <artifact-file>.sha256
```

### Missing Components in Manifest

If the manifest lists fewer components than expected, verify that the source
inventory includes the correct host groups. The collection only exports
components whose groups are present and populated in the inventory.

## Useful Diagnostic Commands

### OCP Environment

```bash
# Full status overview
oc get aap,pods,pvc,deployment -n <namespace>

# Check AAP CR conditions
oc get aap <instance-name> -n <namespace> \
  -o jsonpath='{.status.conditions}' | python3 -m json.tool

# Check for leftover import resources
oc get deployment,pvc -n <namespace> | grep aap-snapshot-temp

# Verify operator health
oc get csv -n <namespace> | grep aap
```

### Artifact Inspection

```bash
# List artifact contents
tar tf <artifact-file>

# Read manifest without extracting
tar xf <artifact-file> artifact/manifest.yml -O

# Validate artifact standalone
ansible-playbook ansible.aap_snapshot.artifact_verify \
  -e artifact_file=<artifact-file>
```
