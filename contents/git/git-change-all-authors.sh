#!/bin/bash
#
# @title Git Change All Authors
# @description Standardize author information across ALL commits in repository
# @author Wei Guo
# @version 1.0.0
# @license MIT
# @repository https://github.com/ropean/scripts
# @requires git 2.0+, bash 4.0+
# @note This script rewrites ALL Git history! Use with extreme caution!
#
# @example
# Usage:
#   ./git-change-all-authors.sh
#
################################################################################
# Git Change All Authors
################################################################################
#
################################################################################
# DESCRIPTION
################################################################################
#
# This script rewrites the ENTIRE Git history to use a single unified author
# and committer for ALL commits across ALL branches. It's the "nuclear option"
# for standardizing author information across your entire repository.
#
# Key Features:
#   - Modifies ALL commits in ALL branches
#   - Unifies all author information to a single identity
#   - Preserves commit messages and code changes
#   - Creates automatic backup branch
#   - Works on repositories of any size (but may be slow)
#
# Use Cases:
#   - Standardize author info across entire repository
#   - Hide all historical author information
#   - Clean up repository before open-sourcing
#   - Unify commits from multiple authors to single identity
#
################################################################################
# WHEN TO USE THIS SCRIPT
################################################################################
#
# ✅ Use git-change-all-authors.sh when:
#   - You need to change ALL commits in the repository
#   - You want to unify all authors to a single identity
#   - You're cleaning up before open-sourcing
#   - Repository size is small to medium (< 10,000 commits)
#
# ❌ Don't use this script when:
#   - You only need to fix a PR branch → Use git-change-pr-authors.sh
#   - You only need to fix one commit → Use git-change-commit.sh
#   - Repository is very large → Use git-change-all-authors-fast.sh
#   - You want to preserve different authors
#
################################################################################
# COMPARISON WITH OTHER SCRIPTS
################################################################################
#
# Script                        | Scope          | Speed  | Use Case
# ------------------------------|----------------|--------|------------------
# git-change-commit.sh          | 1 commit       | Fast   | Fix one commit
# git-change-pr-authors.sh      | Commit range   | Fast   | Clean up PR
# git-change-all-authors.sh     | ALL commits    | Slow   | Standardize repo
# git-change-all-authors-fast.sh| ALL commits    | Fast   | Large repos
#
# Performance Comparison:
#   Small repo (< 100 commits):     Both scripts work fine
#   Medium repo (100-1000 commits): This script is acceptable
#   Large repo (1000-10000 commits): This script is slow (5-30 min)
#   Huge repo (> 10000 commits):    Use git-change-all-authors-fast.sh
#
################################################################################
# USAGE
################################################################################
#
# Syntax:
#   ./git-change-all-authors.sh
#
# No parameters needed - it processes all commits automatically.
#
# Examples:
#   # Standard usage
#   ./git-change-all-authors.sh
#
#   # The script will:
#   # 1. Show all current authors
#   # 2. Ask for confirmation
#   # 3. Create backup branch
#   # 4. Modify all commits
#   # 5. Show results
#
################################################################################
# CONFIGURATION
################################################################################
#
# Before using, modify these variables:
#   NEW_AUTHOR_NAME       - The unified author name
#   NEW_AUTHOR_EMAIL      - The unified author email
#   NEW_COMMITTER_NAME    - The unified committer name
#   NEW_COMMITTER_EMAIL   - The unified committer email
#
################################################################################
# PERFORMANCE NOTES
################################################################################
#
# This script uses git filter-branch which is slower but more compatible.
# For large repositories, consider using git-change-all-authors-fast.sh instead.
#
# Estimated execution time:
#   100 commits:    ~10 seconds
#   1,000 commits:  ~1-2 minutes
#   10,000 commits: ~10-30 minutes
#   50,000 commits: ~1-2 hours
#
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Modify these values to your information
NEW_AUTHOR_NAME="Wei Guo"
NEW_AUTHOR_EMAIL="wei.guo@moodys.com"
NEW_COMMITTER_NAME="Wei Guo"
NEW_COMMITTER_EMAIL="wei.guo@moodys.com"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not a git repository"
    exit 1
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_error "You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch: $CURRENT_BRANCH"

# Show current authors in the repository
echo ""
print_step "Current authors in repository:"
git log --format="%an <%ae>" | sort -u | while read -r author; do
    echo "  - $author"
done

echo ""
print_warning "This will change ALL commits to:"
echo "  Author: $NEW_AUTHOR_NAME <$NEW_AUTHOR_EMAIL>"
echo "  Committer: $NEW_COMMITTER_NAME <$NEW_COMMITTER_EMAIL>"
echo ""
print_warning "This operation will rewrite the entire Git history!"
print_warning "All commit hashes will change!"
echo ""

# Ask for confirmation
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Operation cancelled"
    exit 0
fi

# Create backup branch
BACKUP_BRANCH="backup-before-author-change-$(date +%Y%m%d-%H%M%S)"
print_step "Creating backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"
print_info "Backup created. You can restore with: git reset --hard $BACKUP_BRANCH"

# Method 1: Using git filter-branch (works on all Git versions)
print_step "Rewriting Git history..."

git filter-branch --env-filter "
    export GIT_AUTHOR_NAME='$NEW_AUTHOR_NAME'
    export GIT_AUTHOR_EMAIL='$NEW_AUTHOR_EMAIL'
    export GIT_COMMITTER_NAME='$NEW_COMMITTER_NAME'
    export GIT_COMMITTER_EMAIL='$NEW_COMMITTER_EMAIL'
" --tag-name-filter cat -- --branches --tags

# Clean up backup refs created by filter-branch
print_step "Cleaning up..."
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now

echo ""
print_info "Successfully changed all authors!"
echo ""
print_step "Verification - Current authors in repository:"
git log --format="%an <%ae>" | sort -u | while read -r author; do
    echo "  - $author"
done

echo ""
print_warning "Next steps:"
echo "  1. Review the changes: git log --format=fuller"
echo "  2. If satisfied, force push: git push --force-with-lease"
echo "  3. If you need to undo, restore backup: git reset --hard $BACKUP_BRANCH"
echo ""

exit 0

