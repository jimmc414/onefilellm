# PyPI Publishing - Quick Reference Card

## 🚀 First Time Setup

```bash
# 1. Install tools
pip install --upgrade build twine

# 2. Create accounts
# Visit: https://pypi.org/account/register/
# Visit: https://test.pypi.org/account/register/

# 3. Generate API tokens
# PyPI: https://pypi.org/manage/account/token/
# Test PyPI: https://test.pypi.org/manage/account/token/
```

---

## 📦 Build Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info/

# Build package
python -m build

# Verify contents
ls -lh dist/
unzip -l dist/*.whl
```

---

## 🧪 Test Locally

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install from local wheel
pip install dist/onefilellm-0.1.0-py3-none-any.whl

# Test it
onefilellm --help
python -c "from onefilellm import run"

# Cleanup
deactivate
rm -rf test_env
```

---

## 🎯 Upload to Test PyPI (RECOMMENDED FIRST)

```bash
# Upload
python -m twine upload --repository testpypi dist/*

# Credentials when prompted:
# Username: __token__
# Password: <your-test-pypi-token>

# Verify
# Visit: https://test.pypi.org/project/onefilellm/

# Test install
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            onefilellm
```

---

## 🚢 Upload to Production PyPI

```bash
# Upload
python -m twine upload dist/*

# Credentials when prompted:
# Username: __token__
# Password: <your-production-pypi-token>

# Verify
# Visit: https://pypi.org/project/onefilellm/

# Test install
pip install onefilellm
```

---

## 🔄 Publishing Updates

```bash
# 1. Update version in pyproject.toml
#    version = "0.1.1"  # or 0.2.0, or 1.0.0

# 2. Clean and rebuild
rm -rf dist/ build/ *.egg-info/
python -m build

# 3. Upload
python -m twine upload dist/*

# 4. Tag in git
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1
```

---

## 🔑 Store Credentials (Optional)

Create `~/.pypirc`:

```ini
[testpypi]
  username = __token__
  password = pypi-...your-test-token...

[pypi]
  username = __token__
  password = pypi-...your-prod-token...
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

Then upload without entering credentials:
```bash
twine upload --repository testpypi dist/*  # Test PyPI
twine upload dist/*                         # Production PyPI
```

---

## ⚠️ Common Errors

### "File already exists"
**Cause:** Cannot re-upload same version
**Fix:** Increment version in `pyproject.toml`

### "Invalid authentication"
**Fix:** Use `__token__` as username (with underscores)

### CLI command not found
**Fix:** Check `pyproject.toml`:
```toml
[project.scripts]
onefilellm = "cli:entry_point"
```

### Import error after install
**Fix:** Check all dependencies are in `pyproject.toml`

---

## 📊 Useful URLs

| Purpose | URL |
|---------|-----|
| PyPI Project Page | https://pypi.org/project/onefilellm/ |
| Test PyPI Project Page | https://test.pypi.org/project/onefilellm/ |
| Create PyPI Account | https://pypi.org/account/register/ |
| Create Test PyPI Account | https://test.pypi.org/account/register/ |
| Manage PyPI Tokens | https://pypi.org/manage/account/token/ |
| Package Statistics | https://pypistats.org/packages/onefilellm |
| Check Name Availability | https://pypi.org/project/PACKAGENAME/ |

---

## 🎯 Recommended Workflow

1. ✅ **Test locally** (install from wheel)
2. ✅ **Upload to Test PyPI**
3. ✅ **Test install from Test PyPI**
4. ✅ **Upload to Production PyPI**
5. ✅ **Test install from Production PyPI**
6. ✅ **Tag release in git**
7. ✅ **Update GitHub**

---

## 📋 Version Numbering

Follow **Semantic Versioning**:

- `0.1.0` → `0.1.1` - Bug fixes (PATCH)
- `0.1.0` → `0.2.0` - New features (MINOR)
- `0.9.0` → `1.0.0` - Breaking changes (MAJOR)

---

## 🔒 Security Tips

- ✅ Enable 2FA on PyPI account
- ✅ Use API tokens (not passwords)
- ✅ Never commit tokens to git
- ✅ Use project-scoped tokens after first upload
- ✅ Rotate tokens periodically
- ✅ Set `~/.pypirc` permissions to 600

---

## 📞 Getting Help

- Python Packaging Guide: https://packaging.python.org/
- PyPI Help: https://pypi.org/help/
- Test PyPI: https://test.pypi.org/
- Issue tracker: https://github.com/pypa/packaging-problems
