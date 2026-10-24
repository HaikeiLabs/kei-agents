# PyPI Distribution Plan for kei-agents

This document outlines the distribution strategy for the `kei-agents` Python package, including the release workflow, security requirements, and migration path for consumers. All external resources referenced below are **planned** and have not yet been provisioned.

## Overview

| Distribution Channel | Purpose | Status |
|---------------------|---------|--------|
| [PyPI (Public)](https://pypi.org/) | Primary wheel/sdist distribution endpoint | **Planned** |
| [AWS ECR](https://docs.aws.amazon.com/ecr/) | Final Chat Harness container registry | **Planned** |
| AWS S3 | CI artifact/archive only (not a pip index) | Optional |
| [AWS CodeArtifact](https://docs.aws.amazon.com/codeartifact/) | Private alternative if public PyPI is rejected | Backup |

## Package Identity

### Name Ownership (Prerequisite)

- **Package name**: `kei-agents`
- **Status**: Unverified. Before any publication, a maintainer must:
  1. Check name availability at [pypi.org/project/kei-agents/](https://pypi.org/project/kei-agents/)
  2. If unclaimed: register the name by publishing a placeholder or claiming it via the PyPI account
  3. If claimed by another party: coordinate transfer or select an alternate name
- **Ownership distinction**: PyPI project ownership (managed via a PyPI account) is separate from GitHub organization ownership. A maintainer must be both a PyPI project owner and a GitHub repository admin to manage the full release pipeline.
- **Action required**: Verify or reserve the name before Phase 1 (see Phased Rollout).

Reference: [PEP 503 – Simple Repository API (name normalization)](https://peps.python.org/pep-0503/)

## Versioning Strategy

### Semantic Versioning (SemVer)

The project follows [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

- **MAJOR**: Incompatible API changes
- **MINOR**: New backward-compatible functionality
- **PATCH**: Backward-compatible bug fixes
- **PRERELEASE**: Alpha (`0.1.0a1`), Beta (`0.1.0b1`), RC (`0.1.0rc1`)
- **BUILD**: Build metadata (ignored for precedence)

### Immutable Releases

All releases are **immutable**. Once published to PyPI:
- **Never overwrite** an existing version
- Use **yanking** to mark a release as deprecated (see Rollback section)
- Each version is permanent and reproducible
- Deletion of a published version is an **exceptional** operation (see below), not a rollback mechanism

Reference: [PyPA – Distributing packages](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)

## Release Workflow

### Tag/Release Flow

1. **Create version tag** on `main`:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

2. **GitHub Actions** triggers on tag push (planned `publish.yaml`):
   - Builds wheel and sdist via Hatch
   - Runs validation tests
   - Publishes to PyPI via Trusted Publishing (OIDC)
   - Creates GitHub Release

### Hatch Build Commands

The project uses [Hatch](https://hatch.pypa.io/) as the build backend.

```bash
# Install Hatch
pip install hatch

# Build wheel and sdist
hatch build

# Build specific targets
hatch build wheel
hatch build sdist
```

Reference: [Hatch build configuration](https://hatch.pypa.io/latest/config/build/)

## Build Validation

### Wheel + SDist Validation

Before publishing, validate the built artifacts:

```bash
# Install validation tools
pip install twine

# Verify distributions (metadata, filename, etc.)
twine check dist/*
```

### Isolated Install Tests

Test installation in an isolated environment to ensure dependencies are correct:

```bash
# Create virtual environment
python -m venv test-env
source test-env/bin/activate

# Install from local wheel
pip install dist/kei-agents-*.whl

# Verify installation
python -c "from agents import AgentDefinition, Permission; print(Permission.DRIVE_READ.value)"
```

## PyPI Publishing

### Trusted Publishing via OIDC (Planned)

The project **will use** [GitHub Actions PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) for secure, tokenless publishing. This is **not yet provisioned**.

**Key principle**: No long-lived API tokens stored in GitHub secrets.

```
[GitHub Actions] --OIDC token--> [PyPI] --verify--> [Publisher config] --publish--> [Package]
```

#### Required Configuration (Not Yet Provisioned)

1. **PyPI Pending Publisher Setup**:
   - Navigate to: https://pypi.org/manage/account/publishing/
   - Add a pending publisher with:
     - GitHub repository: `HaikeiLabs/kei-agents`
     - Workflow filename: `publish.yaml`
     - Environment name: `release`
   - **Action required**: A PyPI project owner must complete this setup before first publish

2. **GitHub Environment Protection**:
   - Configure the `release` environment with:
     - Required reviewers (proposed: 2 maintainers)
     - Branch restriction: `main` only
   - Reference: [GitHub – Environment protection rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#environment-protection-rules)

#### Planned Workflow

The existing `build.yaml` (which uses a static `PYPI_TOKEN` secret) must be replaced with a Trusted Publishing workflow:

```yaml
# .github/workflows/publish.yaml (planned)
name: Publish

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write  # Required for OIDC
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Hatch
        run: pip install hatch

      - name: Build package
        run: hatch build

      - name: Verify distribution
        run: |
          pip install twine
          twine check dist/*

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        # No password – uses OIDC token automatically
```

Reference: [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)

## Attestations and Provenance

### SLSA Compliance (Planned)

For supply chain security, implement [SLSA provenance attestations](https://slsa.dev/):

```yaml
# Planned addition to publish.yaml
- name: Generate SLSA provenance
  uses: slsa-framework/slsa-github-generator/generic/v1@v1
  with:
    output: provenance.intoto.jsonl
    source: ${{ github.sha }}
    build: ${{ github.sha }}
```

Reference: [SLSA GitHub Generator](https://github.com/slsa-framework/slsa-github-generator)

## Dependency Policy

### Core Dependencies

```toml
dependencies = [
    "pydantic>=2.0",
]
```

### Lockfile Strategy

- **No lockfiles** for library packages (unlike applications)
- Consumers manage their own dependency constraints
- Use flexible version specifiers (`>=2.0`) to allow compatibility

Reference: [PyPA – Distributing packages (dependencies)](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)

## Pre-releases and TestPyPI

### Proposed Decision: Use TestPyPI for Initial Verification

For the initial release, we propose:
- **First publish to TestPyPI** to validate the pipeline end-to-end
- Then publish to production PyPI

### When to Use TestPyPI

- Validating the full build/publish pipeline before first production release
- Testing complex dependency resolution
- Pre-release verification before major versions

```yaml
# TestPyPI publish (planned)
- uses: pypa/gh-action-pypi-publish@release/v1
  with:
    repository-url: https://test.pypi.org/legacy/
```

Reference: [Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/)

## Rollback and Yanking

### Immutability Principle

Published releases are **immutable**. The rollback strategy is:
1. **Yank** the problematic release (marks it as unavailable for new installs)
2. **Publish a new version** with the fix

Deletion of a published release is an **exceptional** operation (e.g., accidental publication of secrets) and requires direct contact with PyPI staff. It is not a rollback mechanism.

### How to Yank a Release

Yanking is performed by a **PyPI project owner** through the web interface:

1. Navigate to: https://pypi.org/manage/project/kei-agents/releases/
2. Select the release to yank
3. Provide a yank reason (visible to consumers)
4. To un-yank, repeat the process and clear the yank status

Only project owners with the appropriate permissions can yank or un-yank releases.

### Yanking Use Cases

- Security vulnerability in released package
- Critical bug discovered post-release
- Accidental sensitive data exposure

References:
- [PyPI Help – Yanked releases](https://pypi.org/help/#yanked)
- [PEP 592 – Yanked files in the Simple API](https://peps.python.org/pep-0592/)

## Consumer Migration: Kei-Chat-Harness

### Current State

Kei-Chat-Harness currently installs `kei-agents` via:
```toml
# Exact Git SHA dependency (current)
kei-agents = { git = "https://github.com/HaikeiLabs/kei-agents.git", rev = "abc123def" }
```

### Target State

Migrate to PyPI version:
```toml
# kei-agents in pyproject.toml
kei-agents == "0.1.0"  # exact version
# or
kei-agents = ">=0.1.0,<1.0.0"  # range
```

### Migration Steps

1. Update `pyproject.toml` in Kei-Chat-Harness
2. Update CI/CD pipelines to pin versions
3. Add version checking to deployment pipelines
4. Document migration in release notes

Reference: [pip – Dependency resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/)

## Container Registry: AWS ECR

### ECR Image Build Boundary

```
Source: PyPI (kei-agents==version)
    |
    v
Dockerfile in Kei-Chat-Harness
    |
    v
AWS ECR Private Registry
    |
    v
Chat Harness Deployment
```

### Configuration Required (Planned)

> **Security requirement**: Long-lived AWS access keys and secret keys are **prohibited** in GitHub Actions. All AWS access must use OIDC role assumption.

1. **Create ECR repository** (one-time, via AWS console or CLI with proper IAM):
   ```bash
   aws ecr create-repository --repository-name kei-chat-harness
   ```

2. **Configure GitHub Actions** to push to ECR using OIDC:
   ```yaml
   # Planned .github/workflows/ecr-publish.yaml (in Kei-Chat-Harness)
   name: Publish to ECR

   on:
     push:
       branches: [main]

   jobs:
     build-and-push:
       runs-on: ubuntu-latest
       permissions:
         id-token: write  # Required for OIDC role assumption
         contents: read

       steps:
         - uses: actions/checkout@v4

         - name: Configure AWS credentials (OIDC)
           uses: aws-actions/configure-aws-credentials@v4
           with:
             role-to-assume: arn:aws:iam::ACCOUNT_ID:role/github-ecr-push
             aws-region: us-east-1

         - name: Build and push image
           run: |
             aws ecr get-login-password --region us-east-1 | \
               docker login --username AWS --password-stdin \
               ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
             docker build -t kei-chat-harness:${{ github.sha }} .
             docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/kei-chat-harness:${{ github.sha }}
   ```

3. **IAM trust policy** for the role (one-time setup):
   ```json
   {
     "Effect": "Allow",
     "Principal": {
       "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
     },
     "Action": "sts:AssumeRoleWithWebIdentity",
     "Condition": {
       "StringEquals": {
         "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
         "token.actions.githubusercontent.com:sub": "repo:HaikeiLabs/kei-chat-harness:ref:refs/heads/main"
       }
     }
   }
   ```

Reference: [AWS – Configure AWS credentials for GitHub Actions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)

## Release Ownership

### Maintainer Responsibilities

| Role | Responsibility |
|------|----------------|
| Release Manager | Creates tags, monitors CI, handles incidents |
| PyPI Admin | Manages Trusted Publishing configuration, yanking |
| Security Owner | Handles vulnerability disclosures, emergency yanks |

### Required GitHub Permissions

- **Admin**: Full project settings, environment configuration
- **Maintainer**: Merge PRs, create releases
- **Release environment**: Proposed 2 required reviewers for production releases

## Phased Rollout

### Phase 1: Prerequisites and Internal Testing (Week 1-2)

- [ ] Verify or reserve `kei-agents` name on PyPI
- [ ] Configure PyPI Trusted Publishing (pending publisher)
- [ ] Set up GitHub `release` environment with protection rules
- [ ] Create `publish.yaml` workflow
- [ ] Test pipeline with a pre-release tag (`v0.1.0a1`) to TestPyPI

### Phase 2: Production Publish (Week 3-4)

- [ ] Publish `v0.1.0` to production PyPI
- [ ] Update Kei-Chat-Harness to use PyPI version
- [ ] Run integration tests in staging

### Phase 3: Container Pipeline (Week 5+)

- [ ] Configure ECR repository and OIDC role
- [ ] Add Dockerfile build step in Chat Harness
- [ ] Announce release on blog/documentation
- [ ] Monitor for consumer issues

## Acceptance Criteria

| Criterion | Definition |
|-----------|------------|
| Name Verified | `kei-agents` name confirmed available or owned by HaikeiLabs on PyPI |
| Build Success | `hatch build` produces wheel + sdist without errors |
| Validation | `twine check` passes on both artifacts |
| Isolated Install | Fresh venv install works with no dependency errors |
| Trusted Publishing | OIDC-based publish succeeds (no password in secrets) |
| Environment Protection | Release requires configured reviewers, targets `main` only |
| Provenance | SLSA attestations generated for each release |
| Yank Capability | Yanking via PyPI web UI tested successfully |
| Consumer Migration | Kei-Chat-Harness uses `kei-agents==version` |
| ECR Integration | Container images build from PyPI package via OIDC |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| PyPI name already taken | Critical | Verify before Phase 1; have alternate name ready |
| Token/credential exposure | Critical | Use Trusted Publishing (OIDC) and OIDC role assumption; no long-lived secrets |
| Malicious version published | High | Require reviewers on release environment; use Trusted Publishing |
| Dependency conflict | Medium | Test in isolated environment before publish |
| S3 artifact bloat | Low | Implement a retention policy (proposed: 30 days, to be confirmed) |
| CodeArtifact fallback needed | Low | Document migration path if PyPI rejected |

### If Public PyPI Rejected

Fall back to **AWS CodeArtifact**:

```bash
# Configure CodeArtifact auth (one-time, via AWS CLI with proper IAM)
aws codeartifact login --tool pip --domain haikei --domain-owner ACCOUNT_ID

# Install from CodeArtifact
pip install kei-agents --index-url https://ACCOUNT_ID.d.codeartifact.us-east-1.amazonaws.com/pypi/haikei/simple/
```

Reference: [CodeArtifact – Getting started](https://docs.aws.amazon.com/codeartifact/latest/ug/getting-started.html)

## Implementation PRs

The following PRs are required to implement this plan:

1. **`feat: configure PyPI Trusted Publishing`**
   - Verify/reserve `kei-agents` name on PyPI
   - Add pending publisher in PyPI account
   - Create `.github/workflows/publish.yaml`
   - Add `release` environment with protection rules
   - Remove static `PYPI_TOKEN` from existing `build.yaml`

2. **`feat: add SLSA provenance attestations`**
   - Integrate `slsa-framework/slsa-github-generator` into publish workflow
   - Generate and attach provenance to each release

3. **`feat: migrate Kei-Chat-Harness to PyPI`**
   - Update dependency from Git SHA to `kei-agents==version`
   - Update CI/CD version pinning

4. **`feat: configure ECR image build with OIDC`**
   - Create ECR repository
   - Set up OIDC role with proper trust policy
   - Add Dockerfile build step in Chat Harness
   - Configure GitHub Actions ECR push

5. **`docs: update README and CONTRIBUTING`**
   - Add PyPI version badge to README (after first publish)
   - Update CONTRIBUTING.md with release process
   - Remove or gate PyPI links until first publish

## References

- [PyPI documentation](https://docs.pypi.org/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Hatch Build Backend](https://hatch.pypa.io/)
- [Semantic Versioning](https://semver.org/)
- [SLSA](https://slsa.dev/)
- [PyPA – Distributing packages](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)
- [PyPA – Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/)
- [GitHub – Environment protection rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#environment-protection-rules)
- [AWS – OIDC identity providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [AWS CodeArtifact](https://docs.aws.amazon.com/codeartifact/)
- [PEP 503 – Simple Repository API](https://peps.python.org/pep-0503/)
- [PEP 592 – Yanked files in the Simple API](https://peps.python.org/pep-0592/)
- [PyPI Help – Yanked releases](https://pypi.org/help/#yanked)
- [pip – Dependency resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/)
