# Repository Setup Guide

This guide helps you set up the repository for open source development with proper branch protection and automated checks.

## 🛡️ Branch Protection Setup

### 1. Navigate to Repository Settings
- Go to your GitHub repository
- Click **Settings** → **Branches**

### 2. Add Branch Protection Rule for `master`

Click **Add rule** and configure:

**Branch name pattern:** `master`

**Protect matching branches:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: `1`
  - ✅ Dismiss stale PR approvals when new commits are pushed
  - ✅ Require review from code owners (optional)

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks:**
    - `lint`
    - `test` 
    - `build`

- ✅ **Require conversation resolution before merging**
- ✅ **Require linear history** (optional, keeps git history clean)
- ✅ **Include administrators** (applies rules to repo admins too)

### 3. Enable GitHub Actions
- Go to **Settings** → **Actions** → **General**
- Select **Allow all actions and reusable workflows**
- Under **Workflow permissions**, select **Read and write permissions**

## 🔧 Recommended Repository Settings

### 4. General Settings
**Settings** → **General**:
- ✅ **Allow squash merging** (recommended)
- ❌ **Allow merge commits** (optional, disable for cleaner history)
- ❌ **Allow rebase merging** (optional)
- ✅ **Always suggest updating pull request branches**
- ✅ **Automatically delete head branches**

### 5. Security Settings
**Settings** → **Security & analysis**:
- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**

## 🤖 Automated Checks Explained

Our CI pipeline includes three main jobs:

### `lint` Job
- Runs **flake8** for Python syntax and style checking
- Checks **black** formatting compliance
- Validates **isort** import sorting

### `test` Job  
- Runs **pytest** with basic health checks
- Tests core application functionality
- Creates basic tests if none exist

### `build` Job
- Builds Docker image to ensure successful builds
- Performs basic container health checks
- Tests application startup

## 🚀 Single Developer Workflow

As the sole developer, you can still benefit from this setup:

1. **Create feature branches** from `master`
2. **Make your changes** and push to feature branch
3. **Open a pull request** to `master`
4. **Wait for CI checks** to pass (typically 2-3 minutes)
5. **Merge the PR** once checks pass

### Example Workflow:
```bash
# Create and switch to feature branch
git checkout -b feature/new-dashboard-widget
git push -u origin feature/new-dashboard-widget

# Make changes and commit
git add .
git commit -m "Add new dashboard widget for CPU trends"
git push

# Open PR on GitHub, wait for checks, then merge
```

## 📋 Pre-commit Setup (Optional)

For local development quality checks:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black
        language_version: python3.11

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        args: [--max-line-length=88]
EOF

# Install the git hook scripts
pre-commit install
```

## 🎯 Benefits of This Setup

1. **Quality Assurance**: All code is automatically tested before merging
2. **Consistent Style**: Automated formatting and linting
3. **Documentation**: PR templates ensure good descriptions
4. **Community Ready**: Easy for contributors to understand the process
5. **Deployment Safety**: Build tests catch Docker issues early

## ⚠️ Troubleshooting

### CI Checks Failing?
1. **Lint errors**: Run `make lint` locally to see issues
2. **Test failures**: Run `make test` locally
3. **Build issues**: Try `docker build .` locally

### Branch Protection Too Strict?
You can temporarily disable branch protection if needed, but it's recommended to fix the underlying issues instead.

## 📞 Need Help?

- Check the [GitHub Actions documentation](https://docs.github.com/en/actions)
- Review our [CONTRIBUTING.md](CONTRIBUTING.md) guide
- Open an issue if you encounter problems

---

**Happy coding! 🎉**