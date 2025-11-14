# OneFileLLM - PyPI Publishing Guide

This guide will walk you through publishing OneFileLLM to PyPI so that users can install it with `pip install onefilellm`.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Pre-Publication Checklist](#pre-publication-checklist)
3. [Building the Package](#building-the-package)
4. [Testing Locally](#testing-locally)
5. [Creating PyPI Accounts](#creating-pypi-accounts)
6. [Publishing to Test PyPI (Recommended First)](#publishing-to-test-pypi-recommended-first)
7. [Publishing to Production PyPI](#publishing-to-production-pypi)
8. [Verifying Installation](#verifying-installation)
9. [Future Updates](#future-updates)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Install Build Tools

```bash
pip install --upgrade build twine
```

**What these do:**
- `build`: Creates distribution packages (`.tar.gz` and `.whl` files)
- `twine`: Securely uploads packages to PyPI

### 2. Verify Your pyproject.toml

Your current `pyproject.toml` looks good! Here's what's configured:

```toml
[project]
name = "onefilellm"
version = "0.1.0"
description = "A one-file LLM"
readme = "readme.md"
requires-python = ">=3.8"
```

**Important fields:**
- `name`: Must be unique on PyPI (currently "onefilellm" is available)
- `version`: Follow semantic versioning (MAJOR.MINOR.PATCH)
- `readme`: Will be displayed on PyPI project page

---

## Pre-Publication Checklist

### 1. Check Package Name Availability

Visit: https://pypi.org/project/onefilellm/

If you get a 404 error, the name is available. ✅ (As of now, it's available)

### 2. Review Your Dependencies

Current dependencies in `pyproject.toml`:
```
requests==2.31.0
beautifulsoup4==4.11.1
PyPDF2==2.10.0
tiktoken
nltk==3.7
nbformat==5.4.0
nbconvert==6.5.0
youtube-transcript-api==0.4.1
pyperclip==1.8.2
wget==3.2
tqdm==4.64.0
rich==12.4.4
pandas
openpyxl
xlrd
tabulate
PyYAML
python-dotenv
aiohttp
readability-lxml
lxml
```

**Recommendation:** Consider relaxing version pins for better compatibility:
- `requests>=2.31.0` instead of `requests==2.31.0`
- This allows users with newer versions to install without conflicts

### 3. Add Package Metadata (Optional but Recommended)

You may want to add to `pyproject.toml`:

```toml
[project]
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["llm", "content-aggregation", "ai", "github", "web-scraping"]
license = {text = "MIT"}
```

### 4. Verify LICENSE File

✅ You have a `LICENSE` file - make sure it contains the MIT license text.

### 5. Clean Build Artifacts (if any exist)

```bash
# Remove old build artifacts
rm -rf dist/ build/ *.egg-info/
```

---

## Building the Package

### 1. Navigate to Project Root

```bash
cd /path/to/onefilellm
```

### 2. Build Distribution Packages

```bash
python -m build
```

**Expected output:**
```
* Creating venv isolated environment...
* Installing packages in isolated environment... (setuptools>=61.0)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist...
* Successfully built onefilellm-0.1.0.tar.gz and onefilellm-0.1.0-py3-none-any.whl
```

**This creates:**
- `dist/onefilellm-0.1.0.tar.gz` (source distribution)
- `dist/onefilellm-0.1.0-py3-none-any.whl` (wheel distribution)

### 3. Verify Build Contents

```bash
# List contents of the wheel
unzip -l dist/onefilellm-0.1.0-py3-none-any.whl

# Should include:
# - onefilellm.py
# - cli.py
# - utils.py
# - readme.md
# - LICENSE
```

---

## Testing Locally

### 1. Create a Test Virtual Environment

```bash
# Create fresh test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
```

### 2. Install from Built Package

```bash
pip install dist/onefilellm-0.1.0-py3-none-any.whl
```

### 3. Test Installation

```bash
# Test CLI command
onefilellm --help

# Test Python import
python -c "from onefilellm import run; print('Import successful')"
```

### 4. Run Basic Functionality Test

```bash
# Create test file
echo "# Test Document" > test.md

# Run onefilellm on it
onefilellm test.md

# Verify output is copied to clipboard
```

### 5. Clean Up Test Environment

```bash
deactivate
rm -rf test_env test.md
```

---

## Creating PyPI Accounts

### 1. Create PyPI Account (Production)

1. Visit: https://pypi.org/account/register/
2. Fill in:
   - Username
   - Email address
   - Password
3. Verify your email address
4. Enable Two-Factor Authentication (2FA) - **REQUIRED for new projects**

### 2. Create Test PyPI Account (Recommended for Testing)

1. Visit: https://test.pypi.org/account/register/
2. Create separate account (Test PyPI is independent from PyPI)
3. Verify email

### 3. Generate API Tokens

**For Test PyPI:**
1. Go to: https://test.pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `onefilellm-test`
4. Scope: "Entire account" (for first upload)
5. Copy token - it starts with `pypi-`
6. **SAVE THIS TOKEN** - you'll only see it once!

**For Production PyPI:**
1. Go to: https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Token name: `onefilellm-prod`
4. Scope: "Entire account" (for first upload)
5. Copy token
6. **SAVE THIS TOKEN** - you'll only see it once!

**Security Note:** After first upload, create project-scoped tokens for better security.

---

## Publishing to Test PyPI (Recommended First)

### Why Test PyPI First?
- Test the upload process without affecting production PyPI
- Verify package installs correctly
- Catch any issues before going live

### 1. Upload to Test PyPI

```bash
python -m twine upload --repository testpypi dist/*
```

**You'll be prompted:**
```
Enter your username: __token__
Enter your password: <paste your Test PyPI token here>
```

**Note:** Username is literally `__token__` (with underscores)

### 2. Verify Upload

Visit: https://test.pypi.org/project/onefilellm/

You should see your project page with:
- Version 0.1.0
- README content displayed
- Dependencies listed

### 3. Test Installation from Test PyPI

```bash
# Create new test environment
python -m venv test_pypi_env
source test_pypi_env/bin/activate

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ onefilellm

# Test it
onefilellm --help

# Clean up
deactivate
rm -rf test_pypi_env
```

**Note:** `--extra-index-url` is needed because dependencies are on production PyPI

---

## Publishing to Production PyPI

### 1. Final Checks

Before publishing to production:
- ✅ Tested installation from Test PyPI works
- ✅ CLI command works correctly
- ✅ Python imports work
- ✅ README displays correctly on Test PyPI
- ✅ All dependencies resolve correctly

### 2. Upload to Production PyPI

```bash
python -m twine upload dist/*
```

**You'll be prompted:**
```
Enter your username: __token__
Enter your password: <paste your Production PyPI token here>
```

### 3. Verify Upload

Visit: https://pypi.org/project/onefilellm/

### 4. Test Installation

```bash
# Create fresh environment
python -m venv verify_install
source verify_install/bin/activate

# Install from PyPI (should work now!)
pip install onefilellm

# Test
onefilellm --help

# Clean up
deactivate
rm -rf verify_install
```

---

## Verifying Installation

### Complete Installation Test

```bash
# 1. Fresh environment
python -m venv final_test
source final_test/bin/activate

# 2. Install
pip install onefilellm

# 3. Test CLI
onefilellm --help
onefilellm --alias-list

# 4. Test Python API
python << EOF
from onefilellm import run
print("Python API import successful!")
EOF

# 5. Test real functionality
echo "# Test" > test.md
onefilellm test.md

# 6. Clean up
deactivate
rm -rf final_test test.md
```

---

## Future Updates

### Version Numbering

Follow semantic versioning:
- **PATCH** (0.1.X): Bug fixes, no breaking changes
- **MINOR** (0.X.0): New features, backwards compatible
- **MAJOR** (X.0.0): Breaking changes

### Publishing Updates

1. **Update version in `pyproject.toml`:**
   ```toml
   version = "0.1.1"  # or 0.2.0, or 1.0.0
   ```

2. **Clean old builds:**
   ```bash
   rm -rf dist/ build/ *.egg-info/
   ```

3. **Build new version:**
   ```bash
   python -m build
   ```

4. **Upload to PyPI:**
   ```bash
   python -m twine upload dist/*
   ```

5. **Tag in Git:**
   ```bash
   git tag -a v0.1.1 -m "Release version 0.1.1"
   git push origin v0.1.1
   ```

### Project-Scoped Tokens (After First Upload)

For better security, create project-scoped tokens:

1. Go to: https://pypi.org/manage/project/onefilellm/settings/
2. Create token with scope: "Project: onefilellm"
3. Use this token for future uploads
4. Delete account-scoped token

---

## Troubleshooting

### Error: "File already exists"

**Cause:** Version 0.1.0 already uploaded
**Solution:** You cannot re-upload the same version. Increment version number in `pyproject.toml`

### Error: "Invalid or non-existent authentication"

**Cause:** Wrong API token
**Solution:**
- Verify you're using `__token__` as username
- Check token is for correct PyPI (test vs production)
- Regenerate token if needed

### Error: "The name 'onefilellm' is too similar to an existing project"

**Cause:** PyPI detected name similarity
**Solution:** Choose different package name in `pyproject.toml`

### Package installs but CLI command not found

**Cause:** Entry point not configured correctly
**Solution:** Check `pyproject.toml` has:
```toml
[project.scripts]
onefilellm = "cli:entry_point"
```

### Import errors after installation

**Cause:** Dependencies not installed
**Solution:** Check all dependencies in `pyproject.toml` are correct and available on PyPI

### README not displaying on PyPI

**Cause:** Markdown formatting issues
**Solution:**
- Ensure `readme = "readme.md"` in `pyproject.toml`
- Check README uses standard Markdown (not GitHub-specific features)

---

## Security Best Practices

1. **Never commit API tokens** to git
2. **Use 2FA** on PyPI account
3. **Use project-scoped tokens** after first upload
4. **Rotate tokens periodically**
5. **Review dependencies** for known vulnerabilities

### Store Tokens Securely

Create `~/.pypirc` for convenience (optional):

```ini
[testpypi]
  username = __token__
  password = <your Test PyPI token>

[pypi]
  username = __token__
  password = <your PyPI token>
```

**Security:**
```bash
chmod 600 ~/.pypirc  # Restrict file permissions
```

Then upload without entering credentials:
```bash
twine upload --repository pypi dist/*
```

---

## Maintenance Checklist

### Regular Maintenance

- [ ] Monitor PyPI downloads: https://pypistats.org/packages/onefilellm
- [ ] Watch for security vulnerabilities in dependencies
- [ ] Update dependencies when needed
- [ ] Respond to user issues on GitHub
- [ ] Release bug fixes and new features

### Before Each Release

- [ ] Update version in `pyproject.toml`
- [ ] Update changelog/release notes
- [ ] Run tests locally
- [ ] Build package: `python -m build`
- [ ] Test installation in fresh environment
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Create git tag
- [ ] Update GitHub release page

---

## Summary

### Quick Reference Commands

```bash
# One-time setup
pip install --upgrade build twine

# For each release
rm -rf dist/ build/ *.egg-info/
python -m build
python -m twine upload --repository testpypi dist/*  # Test first
python -m twine upload dist/*                         # Then production

# Verify
pip install onefilellm
onefilellm --help
```

### Important URLs

- Production PyPI: https://pypi.org/
- Test PyPI: https://test.pypi.org/
- Your project: https://pypi.org/project/onefilellm/ (after publishing)
- Stats: https://pypistats.org/packages/onefilellm (after publishing)
- Token management: https://pypi.org/manage/account/token/

---

## Next Steps

1. **Create PyPI and Test PyPI accounts**
2. **Generate API tokens** for both
3. **Build your package** with `python -m build`
4. **Test locally** in a virtual environment
5. **Upload to Test PyPI** first
6. **Verify installation** from Test PyPI works
7. **Upload to Production PyPI**
8. **Celebrate!** 🎉 Your package is now installable with `pip install onefilellm`

---

**Questions or issues?** Check the official Python Packaging Guide:
https://packaging.python.org/tutorials/packaging-projects/
