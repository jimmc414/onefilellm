# Pre-Publication Checklist for OneFileLLM

Complete this checklist before publishing to PyPI.

## ✅ Package Configuration

- [ ] `pyproject.toml` has correct version number
- [ ] `pyproject.toml` has accurate description
- [ ] `pyproject.toml` has all required dependencies
- [ ] `pyproject.toml` has correct Python version requirement
- [ ] `pyproject.toml` has valid project URLs
- [ ] `pyproject.toml` has correct entry point: `onefilellm = "cli:entry_point"`

## ✅ Documentation

- [ ] `readme.md` is accurate and up-to-date
- [ ] `readme.md` installation instructions will be correct after PyPI publish
- [ ] `LICENSE` file exists and is correct (MIT)
- [ ] All example commands in README are tested and work

## ✅ Code Quality

- [ ] All Python files have proper imports
- [ ] `cli.py` entry_point function works
- [ ] `onefilellm.py` has `run()` function that can be imported
- [ ] No syntax errors in any Python files
- [ ] No hardcoded secrets or tokens in code

## ✅ Dependencies

- [ ] All dependencies in `pyproject.toml` are available on PyPI
- [ ] Version constraints are reasonable (not overly restrictive)
- [ ] No conflicting dependency versions
- [ ] All required dependencies are listed
- [ ] Optional dependencies are marked as optional (if any)

## ✅ Testing

- [ ] CLI works: `python cli.py --help`
- [ ] Module can be imported: `python -c "from onefilellm import run"`
- [ ] Basic functionality test passes
- [ ] Tested on clean Python environment
- [ ] Tested on Python 3.8, 3.9, 3.10, 3.11+ (if possible)

## ✅ Build Process

- [ ] Installed build tools: `pip install build twine`
- [ ] Cleaned old builds: `rm -rf dist/ build/ *.egg-info/`
- [ ] Successfully built: `python -m build`
- [ ] Build artifacts exist in `dist/` directory
- [ ] Inspected wheel contents: `unzip -l dist/*.whl`
- [ ] All necessary files are included in wheel
- [ ] No unnecessary files in wheel (tests, .git, etc.)

## ✅ Local Testing

- [ ] Created fresh virtual environment
- [ ] Installed from built wheel: `pip install dist/*.whl`
- [ ] CLI command works: `onefilellm --help`
- [ ] Python API works: `from onefilellm import run`
- [ ] Tested basic functionality end-to-end
- [ ] No import errors or missing dependencies

## ✅ PyPI Account Setup

- [ ] Created PyPI account at https://pypi.org/
- [ ] Verified email address
- [ ] Enabled Two-Factor Authentication (2FA)
- [ ] Created API token for publishing
- [ ] Saved API token securely
- [ ] (Optional) Created Test PyPI account at https://test.pypi.org/

## ✅ Name Availability

- [ ] Checked package name is available: https://pypi.org/project/onefilellm/
- [ ] Package name matches `name` in `pyproject.toml`
- [ ] No trademark issues with package name

## ✅ Version Control

- [ ] All changes committed to git
- [ ] Working directory is clean: `git status`
- [ ] Created version tag (e.g., `v0.1.0`)
- [ ] Tag matches version in `pyproject.toml`

## ✅ First Upload to Test PyPI (Recommended)

- [ ] Uploaded to Test PyPI: `twine upload --repository testpypi dist/*`
- [ ] Checked project page: https://test.pypi.org/project/onefilellm/
- [ ] README displays correctly on Test PyPI
- [ ] Installed from Test PyPI in fresh environment
- [ ] CLI works from Test PyPI installation
- [ ] Python import works from Test PyPI installation

## ✅ Production PyPI Upload

- [ ] Ready to publish to production PyPI
- [ ] Have production PyPI API token
- [ ] Uploaded to PyPI: `twine upload dist/*`
- [ ] Checked project page: https://pypi.org/project/onefilellm/
- [ ] README displays correctly on PyPI

## ✅ Post-Publication Verification

- [ ] Created fresh environment
- [ ] Installed from PyPI: `pip install onefilellm`
- [ ] Verified CLI: `onefilellm --help`
- [ ] Verified Python API: `from onefilellm import run`
- [ ] Tested actual functionality
- [ ] Created git tag for this release
- [ ] Pushed tag to GitHub
- [ ] Created GitHub release (optional)

## ✅ Announcement

- [ ] Updated README on GitHub (if needed)
- [ ] Announced release on GitHub Discussions/Releases
- [ ] Closed GitHub issue #74
- [ ] Updated any other relevant documentation

---

## Quick Test Script

Save this as `test_install.sh` and run before publishing:

```bash
#!/bin/bash
set -e

echo "Creating test environment..."
python -m venv test_env
source test_env/bin/activate

echo "Installing from wheel..."
pip install dist/onefilellm-*.whl

echo "Testing CLI..."
onefilellm --help
onefilellm --alias-list

echo "Testing Python import..."
python -c "from onefilellm import run; print('✅ Import successful')"

echo "Testing basic functionality..."
echo '# Test Document' > test.md
onefilellm test.md
rm test.md

echo "Cleanup..."
deactivate
rm -rf test_env

echo "✅ All tests passed!"
```

---

## Common Issues and Solutions

### Issue: CLI command not found after install
**Check:** `pyproject.toml` has correct entry point
```toml
[project.scripts]
onefilellm = "cli:entry_point"
```

### Issue: Import errors
**Check:** All modules listed in `py-modules`:
```toml
[tool.setuptools]
py-modules = ["onefilellm", "cli", "utils"]
```

### Issue: Dependencies not installing
**Check:** All dependencies in `pyproject.toml` exist on PyPI with correct names

### Issue: README not showing on PyPI
**Check:** `pyproject.toml` has `readme = "readme.md"`

### Issue: "File already exists" error
**Solution:** Increment version number - you cannot re-upload the same version

---

## Version Checklist

Current version in `pyproject.toml`: **0.1.0**

Before each new release:
1. Update version number in `pyproject.toml`
2. Clean builds: `rm -rf dist/ build/ *.egg-info/`
3. Rebuild: `python -m build`
4. Upload: `twine upload dist/*`
5. Tag in git: `git tag v0.1.1 && git push --tags`
