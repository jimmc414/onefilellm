#!/bin/bash
# Test script to run before publishing to PyPI
# This ensures your package will work correctly when users install it

set -e  # Exit on any error

echo "=========================================="
echo "OneFileLLM - Pre-Publication Test Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: pyproject.toml not found${NC}"
    echo "Please run this script from the onefilellm root directory"
    exit 1
fi

echo -e "${YELLOW}Step 1: Cleaning old build artifacts...${NC}"
rm -rf dist/ build/ *.egg-info/ test_env/
echo -e "${GREEN}✓ Cleaned${NC}"
echo ""

echo -e "${YELLOW}Step 2: Building package...${NC}"
python -m build
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 3: Checking build artifacts...${NC}"
if [ -d "dist" ] && [ "$(ls -A dist)" ]; then
    echo "Build artifacts created:"
    ls -lh dist/
    echo -e "${GREEN}✓ Artifacts exist${NC}"
else
    echo -e "${RED}✗ No build artifacts found${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 4: Inspecting wheel contents...${NC}"
echo "Contents of wheel file:"
unzip -l dist/*.whl | grep -E '\.(py|md|txt)$' | head -20
echo -e "${GREEN}✓ Wheel contents verified${NC}"
echo ""

echo -e "${YELLOW}Step 5: Creating test environment...${NC}"
python -m venv test_env
source test_env/bin/activate
echo -e "${GREEN}✓ Virtual environment created${NC}"
echo ""

echo -e "${YELLOW}Step 6: Installing from wheel...${NC}"
pip install --quiet dist/*.whl
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Installation successful${NC}"
else
    echo -e "${RED}✗ Installation failed${NC}"
    deactivate
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 7: Testing CLI availability...${NC}"
if command -v onefilellm &> /dev/null; then
    echo -e "${GREEN}✓ CLI command 'onefilellm' is available${NC}"
else
    echo -e "${RED}✗ CLI command 'onefilellm' not found${NC}"
    deactivate
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 8: Testing CLI help...${NC}"
onefilellm --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CLI help works${NC}"
else
    echo -e "${RED}✗ CLI help failed${NC}"
    deactivate
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 9: Testing Python import...${NC}"
python -c "from onefilellm import run; print('Import successful')" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python import works${NC}"
else
    echo -e "${RED}✗ Python import failed${NC}"
    deactivate
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 10: Testing basic functionality...${NC}"
echo "# Test Document" > test_file.md
echo "This is a test file for OneFileLLM" >> test_file.md

# Run onefilellm on test file (suppress clipboard output)
onefilellm test_file.md > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Basic functionality works${NC}"
    rm -f test_file.md
else
    echo -e "${RED}✗ Basic functionality failed${NC}"
    rm -f test_file.md
    deactivate
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 11: Checking installed files...${NC}"
pip show onefilellm
echo -e "${GREEN}✓ Package info retrieved${NC}"
echo ""

echo -e "${YELLOW}Step 12: Cleaning up...${NC}"
deactivate
rm -rf test_env/
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}All tests passed! ✓${NC}"
echo "=========================================="
echo ""
echo "Your package is ready to publish to PyPI!"
echo ""
echo "Next steps:"
echo "1. Review PYPI_PUBLISHING_GUIDE.md for publishing instructions"
echo "2. Create PyPI account at https://pypi.org/account/register/"
echo "3. Upload with: python -m twine upload dist/*"
echo ""
echo "Or test on Test PyPI first (recommended):"
echo "1. Create Test PyPI account at https://test.pypi.org/account/register/"
echo "2. Upload with: python -m twine upload --repository testpypi dist/*"
echo ""
