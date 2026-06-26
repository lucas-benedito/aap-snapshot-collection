## Contributing

We welcome contributions to the AAP Migration Collection. This guide covers the development setup, testing, and contribution process.

## Setup Development Environment

```bash
mkdir -p ansible_collections/ansible/
git clone git@github.com:ansible-automation-platform/aap-snapshot-collection ansible_collections/ansible/aap_snapshot
cd ansible_collections/ansible/aap_snapshot
```

The directory structure is important. `ansible_collections/ansible/aap_snapshot` is where this repo should live for Ansible to resolve it correctly.

```
ansible_collections
└── ansible
    └── aap_snapshot
        ├── galaxy.yml
        ├── LICENSE
        ├── playbooks
        ├── plugins
        ├── README.md
        ├── roles
        └── tests
```

### Install Dependencies

```bash
pip install ansible-core ansible-lint black flake8
ansible-galaxy collection install -r requirements.yml
```

## Testing

### Linting

```bash
ansible-lint roles/
```

### Syntax Check

```bash
ansible-playbook --syntax-check playbooks/artifact_export.yaml
ansible-playbook --syntax-check playbooks/artifact_import.yaml
```

### Unit Tests

```bash
python -m pytest tests/unit/ -v
```

### Pre-commit

This project uses pre-commit hooks for code quality. Install and run:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Excluding Paths from Collection Build

When adding files for testing, documentation, or CI, exclude them in `galaxy.yml` under `build_ignore:` so they do not ship in the collection tarball.

Verify your exclusion:

```bash
ansible-galaxy collection build . --force --output-path=./
tar -tf aap-snapshot-*.tar.gz | head -30
```

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Make your changes, ensuring all lint checks and tests pass.
3. Sign off your commits (`git commit -s`) to certify the [Developer Certificate of Origin](DCO).
4. Open a pull request with a clear description of the change.

## Reporting Issues

To report a bug or request a feature, open an issue in this repository.

If you have a fix, please open a pull request and reference the issue.
