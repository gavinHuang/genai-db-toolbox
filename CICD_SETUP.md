# CI/CD Pipeline Setup Guide

This repository includes a comprehensive CI/CD pipeline that automatically tests, builds, and publishes your package to PyPI.

## Workflow Overview

The pipeline consists of several jobs that run automatically:

### 1. **Test Job** 
- Runs on every push and pull request
- Tests against Python 3.10, 3.11, and 3.12
- Performs linting (Black, isort, flake8)
- Runs type checking (mypy)
- Executes test suite with coverage reporting

### 2. **Build Job**
- Runs on every push (after tests pass)
- Builds the package using `python -m build`
- Validates the package with `twine check`
- Uploads build artifacts

### 3. **Publish to TestPyPI**
- Runs on pushes to `main` branch
- Publishes to TestPyPI for testing
- Allows you to test installation before official release

### 4. **Publish to PyPI**
- Runs only when you create a version tag (e.g., `v1.0.0`)
- Publishes the official release to PyPI

## Required Setup

### 1. GitHub Repository Secrets

You need to configure the following secrets in your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Add the following repository secrets:

#### For PyPI Publishing:
- **`PYPI_API_TOKEN`**: Your PyPI API token
  - Go to https://pypi.org/manage/account/token/
  - Create a new API token
  - Copy the token (starts with `pypi-`)

#### For TestPyPI Publishing (Optional but recommended):
- **`TEST_PYPI_API_TOKEN`**: Your TestPyPI API token
  - Go to https://test.pypi.org/manage/account/token/
  - Create a new API token
  - Copy the token (starts with `pypi-`)

### 2. GitHub Environments (Optional)

For additional security, you can create environments:

1. Go to Settings → Environments
2. Create two environments:
   - `pypi` (for production releases)
   - `test-pypi` (for test releases)
3. Add protection rules and required reviewers if desired

## Usage

### Development Workflow

1. **Push code changes**: The pipeline automatically runs tests and builds
2. **Create Pull Request**: Tests run to ensure code quality
3. **Merge to main**: Builds and publishes to TestPyPI for testing

### Release Workflow

1. **Update version** in `pyproject.toml`
2. **Create and push a tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. **Automatic publication**: Package is built and published to PyPI

### Testing Your Package

After pushing to main, you can test the package from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pbix-to-mcp
```

## Workflow Features

- ✅ **Caching**: Pip dependencies are cached for faster builds
- ✅ **Matrix Testing**: Tests against multiple Python versions
- ✅ **Code Quality**: Automatic linting and type checking
- ✅ **Coverage**: Test coverage reporting with Codecov
- ✅ **Artifact Storage**: Build artifacts are preserved
- ✅ **Skip Existing**: Won't fail if version already exists on TestPyPI
- ✅ **Environment Protection**: Separate environments for test and production

## Troubleshooting

### Common Issues

1. **Secret not found**: Ensure `PYPI_API_TOKEN` is correctly set in repository secrets
2. **Version conflict**: Update version in `pyproject.toml` before creating tags
3. **Test failures**: Fix failing tests before the build job will run
4. **Linting errors**: Run `black`, `isort`, and `flake8` locally to fix formatting

### Local Testing

Run the same checks locally:

```bash
# Install dev dependencies
pip install -e .[dev]

# Run linting
black pbix_to_mcp/ tests/
isort pbix_to_mcp/ tests/
flake8 pbix_to_mcp/ tests/

# Run type checking
mypy pbix_to_mcp/

# Run tests
pytest tests/ --cov=pbix_to_mcp

# Build package
python -m build
```

## Package Versioning

The workflow supports both:
- Manual versioning in `pyproject.toml`
- Automatic versioning with `setuptools-scm` (if configured)

For releases, always update the version number and create a corresponding git tag.