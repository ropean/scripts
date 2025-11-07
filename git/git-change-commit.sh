#!/bin/bash
#
# @title Git Change Single Commit
# @description Modify author/message for ONE specific commit in Git history
# @author Wei Guo
# @version 1.1.0
# @license MIT
# @repository https://github.com/ropean/scripts
# @requires git 2.0+, bash 4.0+
# @note This script rewrites Git history!
#
# @example
# Usage:
#   ./git-change-commit.sh <commit-hash> [new-message]
#   ./git-change-commit.sh abc123def456
#   ./git-change-commit.sh abc123def456 "New commit message"
#
################################################################################
# Git Change Single Commit
################################################################################
#
################################################################################
# DESCRIPTION
################################################################################
#
# This script modifies a SINGLE specific commit in your Git history. It's the
# surgical tool for fixing one particular commit that has incorrect author
# information or needs a message update.
#
# Key Features:
#   - Targets ONE specific commit by hash
#   - Can modify author/committer information
#   - Can optionally change commit message
#   - Automatically updates all subsequent commits
#   - Preserves code changes
#
# Use Cases:
#   - Fix author info on a specific commit that used wrong git config
#   - Update commit message for a specific commit
#   - Correct email address on one particular commit
#
################################################################################
# WHEN TO USE THIS SCRIPT
################################################################################
#
# ✅ Use git-change-commit.sh when:
#   - You need to fix ONE specific commit
#   - You know the exact commit hash
#   - Other commits are fine, only this one needs fixing
#
# ❌ Don't use this script when:
#   - You need to fix multiple commits → Use git-change-pr-authors.sh
#   - You need to fix ALL commits → Use git-change-all-authors.sh
#   - You want to clean up a PR branch → Use git-change-pr-authors.sh
#
################################################################################
# COMPARISON WITH OTHER SCRIPTS
################################################################################
#
# Script                        | Scope          | Use Case
# ------------------------------|----------------|---------------------------
# git-change-commit.sh          | 1 commit       | Fix one specific commit
# git-change-pr-authors.sh      | Range          | Clean up PR branch
# git-change-all-authors.sh     | All commits    | Standardize entire repo
# git-change-all-authors-fast.sh| All commits    | Fast version for large repos
#
################################################################################
# USAGE
################################################################################
#
# Syntax:
#   ./git-change-commit.sh <commit-hash> [new-message]
#
# Examples:
#   # Fix author only, keep message
#   ./git-change-commit.sh abc123def456
#
#   # Fix author AND change message
#   ./git-change-commit.sh abc123def456 "New commit message"
#
#   # Use full commit hash
#   ./git-change-commit.sh 9682778721b85046767d772b55ab12e25171e317
#
################################################################################
# CONFIGURATION
################################################################################
#
# Before using, modify these variables:
#   NEW_AUTHOR_NAME       - Your name
#   NEW_AUTHOR_EMAIL      - Your email
#   NEW_COMMITTER_NAME    - Usually same as author name
#   NEW_COMMITTER_EMAIL   - Usually same as author email
#
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - Modify these values to your information
NEW_AUTHOR_NAME="Wei Guo2"
NEW_AUTHOR_EMAIL="wei.guo2@moodys.com"
NEW_COMMITTER_NAME="Wei Guo2"
NEW_COMMITTER_EMAIL="wei.guo2@moodys.com"

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

# Function to show usage
show_usage() {
    echo "Usage: $0 <commit-hash> [new-message]"
    echo ""
    echo "Arguments:"
    echo "  commit-hash    The SHA-1 hash of the commit to modify"
    echo "  new-message    (Optional) The new commit message (use quotes for messages with spaces)"
    echo "                 If not provided, keeps the original message"
    echo ""
    echo "Examples:"
    echo "  $0 9682778721b85046767d772b55ab12e25171e317"
    echo "  $0 9682778721b85046767d772b55ab12e25171e317 \"Fix typo in README\""
    exit 1
}

# Check if at least one argument provided
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    print_error "Invalid number of arguments"
    show_usage
fi

COMMIT_HASH="$1"
NEW_MESSAGE="${2:-}"  # Optional second parameter

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not a git repository"
    exit 1
fi

# Check if commit exists
if ! git cat-file -e "$COMMIT_HASH^{commit}" 2>/dev/null; then
    print_error "Commit $COMMIT_HASH does not exist"
    exit 1
fi

# Save current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Current branch: $CURRENT_BRANCH"

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_error "You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

print_info "Starting commit modification for: $COMMIT_HASH"
if [ -n "$NEW_MESSAGE" ]; then
    print_info "New message: $NEW_MESSAGE"
else
    print_info "Keeping original commit message"
fi

# Create a temporary script for the rebase editor
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOF'
#!/bin/bash
sed -i.bak "1s/^pick /edit /" "$1"
EOF
chmod +x "$TEMP_SCRIPT"

# Export environment variables for the commit modification
export GIT_AUTHOR_NAME="$NEW_AUTHOR_NAME"
export GIT_AUTHOR_EMAIL="$NEW_AUTHOR_EMAIL"
export GIT_COMMITTER_NAME="$NEW_COMMITTER_NAME"
export GIT_COMMITTER_EMAIL="$NEW_COMMITTER_EMAIL"

# Function to cleanup
cleanup() {
    rm -f "$TEMP_SCRIPT"
    unset GIT_AUTHOR_NAME
    unset GIT_AUTHOR_EMAIL
    unset GIT_COMMITTER_NAME
    unset GIT_COMMITTER_EMAIL
}

# Set trap to ensure cleanup on exit
trap cleanup EXIT

# Start interactive rebase
print_info "Starting interactive rebase..."
GIT_SEQUENCE_EDITOR="$TEMP_SCRIPT" git rebase -i "${COMMIT_HASH}^" || {
    print_error "Rebase failed to start"
    git rebase --abort 2>/dev/null
    exit 1
}

# Amend the commit
print_info "Modifying commit..."
if [ -n "$NEW_MESSAGE" ]; then
    # Change both author/committer and message
    git commit --amend --reset-author -m "$NEW_MESSAGE" --no-verify || {
        print_error "Failed to amend commit"
        git rebase --abort
        exit 1
    }
else
    # Only change author/committer, keep original message
    git commit --amend --reset-author --no-edit --no-verify || {
        print_error "Failed to amend commit"
        git rebase --abort
        exit 1
    }
fi

# Continue rebase
print_info "Continuing rebase..."
git rebase --continue || {
    print_error "Failed to continue rebase"
    git rebase --abort
    exit 1
}

# Return to original branch (if detached HEAD occurred)
if [ "$(git rev-parse --abbrev-ref HEAD)" != "$CURRENT_BRANCH" ]; then
    print_info "Returning to branch: $CURRENT_BRANCH"
    git checkout "$CURRENT_BRANCH"
fi

print_info "Successfully modified commit!"
print_warning "Commit hash has changed due to history rewrite"
print_warning "If you've already pushed this commit, you'll need to force push: git push --force-with-lease"

# Show the modified commit
echo ""
print_info "Modified commit details:"
git log --format=fuller -1

exit 0