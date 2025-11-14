# Recommended pyproject.toml Improvements

## Current vs. Recommended Configuration

### Current pyproject.toml Issues

Your current `pyproject.toml` is functional but could be improved before publishing to PyPI.

---

## ⚠️ Critical Issues

### 1. Overly Strict Dependency Versions

**Current:**
```toml
dependencies = [
    "requests==2.31.0",
    "beautifulsoup4==4.11.1",
    "PyPDF2==2.10.0",
    # ... many more with exact versions
]
```

**Problem:** Users with newer versions of these packages will get conflicts.

**Recommended:**
```toml
dependencies = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.11.1",
    "PyPDF2>=2.10.0",
    # ... etc
]
```

**Why:** Using `>=` allows users to have newer versions while ensuring minimum requirements are met.

---

## 📝 Recommended Additions

### 2. Add Author Information

**Add:**
```toml
[project]
name = "onefilellm"
version = "0.1.0"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
maintainers = [
    {name = "Your Name", email = "your.email@example.com"}
]
```

### 3. Add Keywords for Discoverability

**Add:**
```toml
keywords = [
    "llm",
    "content-aggregation",
    "ai",
    "github",
    "web-scraping",
    "documentation",
    "data-collection",
    "xml",
    "clipboard"
]
```

### 4. Improve Description

**Current:**
```toml
description = "A one-file LLM"
```

**Recommended:**
```toml
description = "Content aggregator for LLMs - Collect and structure multi-source data into a single XML file"
```

### 5. Add License Field

**Add:**
```toml
license = {text = "MIT"}
```

### 6. Add More Classifiers

**Current:**
```toml
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
```

**Recommended:**
```toml
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Text Processing :: Markup :: XML",
]
```

---

## 🔧 Complete Recommended pyproject.toml

Here's what your improved `pyproject.toml` should look like:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "onefilellm"
version = "0.1.0"
description = "Content aggregator for LLMs - Collect and structure multi-source data into a single XML file"
readme = "readme.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = [
    "llm",
    "content-aggregation",
    "ai",
    "github",
    "web-scraping",
    "documentation",
    "data-collection",
    "xml",
    "clipboard"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Text Processing :: Markup :: XML",
]

dependencies = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.11.1",
    "PyPDF2>=2.10.0",
    "tiktoken>=0.3.0",
    "nltk>=3.7",
    "nbformat>=5.4.0",
    "nbconvert>=6.5.0",
    "youtube-transcript-api>=0.4.1",
    "pyperclip>=1.8.2",
    "wget>=3.2",
    "tqdm>=4.64.0",
    "rich>=12.4.4",
    "pandas>=1.3.0",
    "openpyxl>=3.0.0",
    "xlrd>=2.0.0",
    "tabulate>=0.8.0",
    "PyYAML>=6.0",
    "python-dotenv>=0.19.0",
    "aiohttp>=3.8.0",
    "readability-lxml>=0.8.0",
    "lxml>=4.9.0",
]

[project.urls]
"Homepage" = "https://github.com/jimmc414/onefilellm"
"Bug Tracker" = "https://github.com/jimmc414/onefilellm/issues"
"Documentation" = "https://github.com/jimmc414/onefilellm/blob/main/readme.md"
"Source Code" = "https://github.com/jimmc414/onefilellm"

[project.scripts]
onefilellm = "cli:entry_point"

[tool.setuptools]
py-modules = ["onefilellm", "cli", "utils"]
```

---

## 🎯 Optional: Support for Optional Dependencies

If some features are optional, you can add:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=22.0.0",
    "flake8>=4.0.0",
]
```

Then users can install with:
```bash
pip install onefilellm[dev]
```

---

## 📋 Changes Summary

### Must Change:
1. ✅ Change `==` to `>=` for all dependencies
2. ✅ Add author information (name/email)

### Should Change:
3. ✅ Improve description
4. ✅ Add keywords for discoverability
5. ✅ Add more classifiers
6. ✅ Add license field
7. ✅ Add version numbers to dependencies that don't have them

### Nice to Have:
8. ✅ Add more project URLs (documentation, source)
9. ✅ Add optional dependencies for dev tools

---

## ⚡ Quick Apply Script

You can apply these changes manually or use the updated `pyproject.toml` I've provided above.

**Before making changes:**
```bash
# Backup current file
cp pyproject.toml pyproject.toml.backup
```

**After making changes:**
```bash
# Test that it's valid
python -m build
```

---

## 🔍 Dependency Version Notes

For packages without version numbers in your current file, here are recommended minimums:

- `tiktoken` → `tiktoken>=0.3.0`
- `pandas` → `pandas>=1.3.0`
- `openpyxl` → `openpyxl>=3.0.0`
- `xlrd` → `xlrd>=2.0.0`
- `tabulate` → `tabulate>=0.8.0`
- `PyYAML` → `PyYAML>=6.0`
- `python-dotenv` → `python-dotenv>=0.19.0`
- `aiohttp` → `aiohttp>=3.8.0`
- `readability-lxml` → `readability-lxml>=0.8.0`
- `lxml` → `lxml>=4.9.0`

---

## 🚨 Before Publishing

1. Review and update the `pyproject.toml` with recommended changes
2. Replace "Your Name" and "your.email@example.com" with real values
3. Test build: `python -m build`
4. Test install: `pip install dist/*.whl`
5. Proceed with PyPI upload

---

## 💡 Why These Changes Matter

| Change | Benefit |
|--------|---------|
| `>=` instead of `==` | Prevents dependency conflicts |
| Author info | Shows package maintainer |
| Keywords | Makes package discoverable via search |
| Better description | Helps users understand what it does |
| More classifiers | Improves PyPI categorization |
| License field | Clear licensing information |
| Version minimums | Documents required features |
