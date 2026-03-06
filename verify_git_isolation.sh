#!/bin/bash
# Verification script for Git isolation between project and database repos

echo "=========================================="
echo "Git Isolation Verification Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check project Git exists
echo "Test 1: Project Git Repository"
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Project Git repo found at .git/"
else
    echo -e "${RED}✗ FAIL${NC} - Project Git repo not found"
    exit 1
fi
echo ""

# Test 2: Check database Git exists
echo "Test 2: Database Git Repository"
if [ -d "data/.git" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Database Git repo found at data/.git/"
else
    echo -e "${RED}✗ FAIL${NC} - Database Git repo not found"
    echo -e "${YELLOW}→ Fix: Run 'python3 server/db_version.py' to initialize${NC}"
    exit 1
fi
echo ""

# Test 3: Check project .gitignore excludes database Git
echo "Test 3: Project .gitignore Configuration"
if grep -q "data/.git/" .gitignore; then
    echo -e "${GREEN}✓ PASS${NC} - Project .gitignore excludes data/.git/"
else
    echo -e "${RED}✗ FAIL${NC} - Project .gitignore does NOT exclude data/.git/"
    echo -e "${YELLOW}→ Fix: Add 'data/.git/' to .gitignore${NC}"
    exit 1
fi
echo ""

# Test 4: Verify project Git doesn't see database Git
echo "Test 4: Project Git Isolation"
# Check if project Git can see the database .git directory (should NOT)
if git status --porcelain | grep -q "^?? data/.git/"; then
    echo -e "${RED}✗ FAIL${NC} - Project Git CAN see data/.git/ directory (isolation broken)"
    echo "   Git status shows:"
    git status --porcelain | grep "data/.git"
    exit 1
else
    echo -e "${GREEN}✓ PASS${NC} - Project Git does NOT see data/.git/ directory (properly isolated)"
fi

# Check if project Git can see the SQL dump (should NOT unless you want to track it)
if git status --porcelain | grep -q "^?? data/.*\.sql"; then
    echo -e "${YELLOW}⚠ INFO${NC} - Project Git can see SQL dumps in data/ (this is OK, but they're ignored)"
fi
echo ""

# Test 5: Check database .gitignore exists
echo "Test 5: Database .gitignore Configuration"
if [ -f "data/.gitignore" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Database .gitignore exists"
    if grep -q "*.db" data/.gitignore && grep -q "snapshots/" data/.gitignore; then
        echo -e "${GREEN}✓ PASS${NC} - Database .gitignore properly configured"
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - Database .gitignore may be incomplete"
    fi
else
    echo -e "${RED}✗ FAIL${NC} - Database .gitignore not found"
    exit 1
fi
echo ""

# Test 6: Check snapshot directory exists
echo "Test 6: Snapshot Directory"
if [ -d "data/snapshots" ]; then
    snapshot_count=$(ls data/snapshots/*.db 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ PASS${NC} - Snapshot directory exists ($snapshot_count snapshots)"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Snapshot directory not yet created (will be created on first use)"
fi
echo ""

# Test 7: Verify database file exists
echo "Test 7: Database File"
if [ -f "data/bird_data_complete.db" ]; then
    db_size=$(du -h data/bird_data_complete.db | cut -f1)
    echo -e "${GREEN}✓ PASS${NC} - Database file exists ($db_size)"
else
    echo -e "${RED}✗ FAIL${NC} - Database file not found"
    exit 1
fi
echo ""

# Test 8: Check for SQL dump (created by version control)
echo "Test 8: SQL Dump File (Version Control)"
if [ -f "data/bird_data_complete.sql" ]; then
    sql_size=$(du -h data/bird_data_complete.sql | cut -f1)
    echo -e "${GREEN}✓ PASS${NC} - SQL dump exists ($sql_size)"
else
    echo -e "${YELLOW}⚠ INFO${NC} - SQL dump not yet created (will be created on first commit)"
fi
echo ""

# Test 9: Check database Git configuration
echo "Test 9: Database Git Configuration"
cd data
if git config user.email > /dev/null 2>&1; then
    db_git_email=$(git config user.email)
    echo -e "${GREEN}✓ PASS${NC} - Database Git has user.email: $db_git_email"
else
    echo -e "${RED}✗ FAIL${NC} - Database Git user.email not configured"
    exit 1
fi
cd ..
echo ""

# Test 10: Count commits in each repo
echo "Test 10: Commit Counts"
project_commits=$(git rev-list --count HEAD 2>/dev/null || echo "0")
echo "   Project Git: $project_commits commits"

cd data
db_commits=$(git rev-list --count HEAD 2>/dev/null || echo "0")
echo "   Database Git: $db_commits commits"
cd ..

if [ "$db_commits" = "0" ]; then
    echo -e "${YELLOW}⚠ INFO${NC} - Database Git has no commits yet (make a database change to create first commit)"
else
    echo -e "${GREEN}✓ PASS${NC} - Database Git is tracking changes"
fi
echo ""

# Final Summary
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ All critical tests passed!${NC}"
echo ""
echo "The two Git repositories are properly isolated:"
echo "  • Project Git tracks code (*.py, *.yaml, *.md)"
echo "  • Database Git tracks data (bird_data_complete.sql)"
echo "  • No conflicts or interference between repos"
echo ""
echo "Next steps:"
echo "  1. Start the backend: ./run_app.sh"
echo "  2. Open NestDB in browser: http://localhost:8501"
echo "  3. Make a database edit to create first commit"
echo "  4. View version history in the 'Version History' tab"
echo ""
