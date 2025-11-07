#!/bin/bash
# @title Git Squash to Single Commit
# @description Create a fresh repository with a single commit, preserving current state
# @author Wei
# @version 1.0.0
#
# This script creates a completely new Git history with just one commit containing
# all current files. This is useful when you want to start fresh without any history.
#
# @example
# Usage:
#   ./git-squash-to-single-commit.sh [commit-message]
#   ./git-squash-to-single-commit.sh "Initial commit"
#
# @requires git
# @note This will completely remove all Git history!

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NEW_AUTHOR_NAME="Wei Guo"
NEW_AUTHOR_EMAIL="wei.guo@moodys.com"
DEFAULT_MESSAGE="Initial commit - consolidated history"

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

# Get commit message from argument or use default
COMMIT_MESSAGE="${1:-$DEFAULT_MESSAGE}"

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

echo ""
print_warning "This will:"
echo "  1. Delete ALL Git history"
echo "  2. Create a single new commit with all current files"
echo "  3. Use author: $NEW_AUTHOR_NAME <$NEW_AUTHOR_EMAIL>"
echo "  4. Commit message: $COMMIT_MESSAGE"
echo ""
print_warning "This operation CANNOT be easily undone!"
echo ""

# Ask for confirmation
read -p "Are you sure you want to continue? (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Operation cancelled"
    exit 0
fi

# Create backup branch
BACKUP_BRANCH="backup-before-squash-$(date +%Y%m%d-%H%M%S)"
print_step "Creating backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"
print_info "Backup created at: $BACKUP_BRANCH"

# Store the current tree
print_step "Saving current state..."
TREE=$(git write-tree)

# Create a new commit with the current tree
print_step "Creating new commit..."
export GIT_AUTHOR_NAME="$NEW_AUTHOR_NAME"
export GIT_AUTHOR_EMAIL="$NEW_AUTHOR_EMAIL"
export GIT_COMMITTER_NAME="$NEW_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$NEW_AUTHOR_EMAIL"

NEW_COMMIT=$(git commit-tree "$TREE" -m "$COMMIT_MESSAGE")

# Reset current branch to the new commit
print_step "Resetting branch to new commit..."
git reset --hard "$NEW_COMMIT"

# Clean up
unset GIT_AUTHOR_NAME
unset GIT_AUTHOR_EMAIL
unset GIT_COMMITTER_NAME
unset GIT_COMMITTER_EMAIL

echo ""
print_info "Successfully created fresh history!"
echo ""
print_step "New commit details:"
git log --format=fuller -1

echo ""
print_warning "Next steps:"
echo "  1. Review the changes: git log"
echo "  2. If satisfied, force push: git push --force-with-lease"
echo "  3. If you need to undo, restore backup: git reset --hard $BACKUP_BRANCH"
echo "  4. Delete backup branch when done: git branch -D $BACKUP_BRANCH"
echo ""

exit 0

