#!/bin/bash
#
# @title Git Change PR Authors
# @description Modify author and committer information for commits in a PR branch
# @author Wei Guo
# @version 2.0.0
# @license MIT
# @repository https://github.com/your-repo/git-scripts
# @requires git 2.0+, bash 4.0+
# @note This script rewrites Git history! Force push required!
#
# @example
# Usage:
#   ./git-change-pr-authors.sh <base-branch-or-commit>
#   ./git-change-pr-authors.sh main
#   ./git-change-pr-authors.sh 059027114dd2419b20ddcbdf409ff3da15d715aa
#
################################################################################
# Git Change PR Authors
################################################################################
#
################################################################################
# DESCRIPTION
################################################################################
#
# This script modifies the author and committer information for all commits
# from a specified base (branch or commit) to the current HEAD. It's designed
# for cleaning up author information in Pull Request branches before merging.
#
# Key Features:
#   - Modifies only commits in the specified range (doesn't touch base branch)
#   - Preserves commit messages and code changes
#   - Automatically handles merge commits (skips them during rebase)
#   - Creates automatic backup for easy rollback
#   - Interactive confirmation with sensible defaults
#   - Optional automatic push and cleanup
#   - Comprehensive error handling
#
# Use Cases:
#   - Standardize author information across a PR
#   - Fix incorrect author/email in commits
#   - Clean up commits before merging to main branch
#   - Unify multiple authors to a single identity
#
################################################################################
# USAGE
################################################################################
#
# Syntax:
#   ./git-change-pr-authors.sh <base-branch-or-commit>
#
# Examples:
#   # Modify all commits after main branch
#   ./git-change-pr-authors.sh main
#
#   # Modify commits after a specific commit hash
#   ./git-change-pr-authors.sh 059027114dd2419b20ddcbdf409ff3da15d715aa
#
#   # Modify commits after develop branch
#   ./git-change-pr-authors.sh develop
#
#   # Modify last 3 commits
#   ./git-change-pr-authors.sh HEAD~3
#
################################################################################
# CONFIGURATION
################################################################################
#
# Before using this script, modify the following variables to match your
# desired author information:
#
#   NEW_AUTHOR_NAME       - The name to use for all modified commits
#   NEW_AUTHOR_EMAIL      - The email to use for all modified commits
#   NEW_COMMITTER_NAME    - The committer name (usually same as author)
#   NEW_COMMITTER_EMAIL   - The committer email (usually same as author)
#
################################################################################

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

################################################################################
# COLOR CODES FOR OUTPUT
################################################################################

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

################################################################################
# CONFIGURATION VARIABLES
################################################################################
# 
# ⚠️  MODIFY THESE VALUES BEFORE RUNNING THE SCRIPT
#

NEW_AUTHOR_NAME="Wei Guo"
NEW_AUTHOR_EMAIL="wei.guo@moodys.com"
NEW_COMMITTER_NAME="Wei Guo"
NEW_COMMITTER_EMAIL="wei.guo@moodys.com"

################################################################################
# UTILITY FUNCTIONS
################################################################################

#
# Print an informational message in green
# Arguments:
#   $1 - Message to print
#
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

#
# Print an error message in red
# Arguments:
#   $1 - Error message to print
#
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#
# Print a warning message in yellow
# Arguments:
#   $1 - Warning message to print
#
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

#
# Print a step/progress message in blue
# Arguments:
#   $1 - Step message to print
#
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

#
# Display usage information and exit
# This function is called when invalid arguments are provided
#
show_usage() {
    cat << EOF
Usage: $0 <base-branch-or-commit>

Description:
  Modify author and committer information for all commits from the specified
  base to the current HEAD. Only changes author information while preserving
  commit messages and code changes.

Arguments:
  base-branch-or-commit    Branch name or commit hash to use as the base point.
                          Commits after this point will be modified.

Examples:
  # Modify commits after main branch (most common use case)
  $0 main

  # Modify commits after a specific commit hash
  $0 059027114dd2419b20ddcbdf409ff3da15d715aa

  # Modify commits after develop branch
  $0 develop

  # Modify last 3 commits only
  $0 HEAD~3

Notes:
  - This script will rewrite Git history
  - A backup branch is automatically created
  - Merge commits are automatically skipped during rebase
  - Force push is required to update remote branches

For more information, see the script header comments.
EOF
    exit 1
}

################################################################################
# INPUT VALIDATION
################################################################################

# Check if exactly one argument is provided
if [ $# -ne 1 ]; then
    print_error "Invalid number of arguments"
    show_usage
fi

BASE_REF="$1"

################################################################################
# ENVIRONMENT CHECKS
################################################################################

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not a git repository"
    print_error "Please run this script from within a Git repository"
    exit 1
fi

# Validate that the base reference exists
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    print_error "Invalid branch or commit: $BASE_REF"
    print_error "Please provide a valid branch name or commit hash"
    exit 1
fi

# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" = "HEAD" ]; then
    print_error "You are in detached HEAD state"
    print_error "Please checkout a branch first: git checkout <branch-name>"
    exit 1
fi

print_info "Current branch: $CURRENT_BRANCH"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_error "You have uncommitted changes"
    print_error "Please commit or stash them first:"
    print_error "  git stash"
    print_error "  # or"
    print_error "  git commit -am 'Your message'"
    exit 1
fi

################################################################################
# COMMIT ANALYSIS
################################################################################

# Get the base commit hash
BASE_COMMIT=$(git rev-parse "$BASE_REF")

# Verify that base commit is an ancestor of current HEAD
# This ensures we're not trying to modify commits that aren't in our history
if ! git merge-base --is-ancestor "$BASE_COMMIT" HEAD 2>/dev/null; then
    print_error "Base commit $BASE_REF is not an ancestor of current HEAD"
    print_error "Cannot modify commits that are not in the current branch history"
    print_error ""
    print_error "Possible reasons:"
    print_error "  - The base branch/commit is ahead of your current branch"
    print_error "  - The base branch/commit is on a different branch line"
    print_error ""
    print_error "Please ensure you're on the correct branch and try again"
    exit 1
fi

# Count total commits in the range
COMMIT_COUNT=$(git rev-list --count ${BASE_REF}..HEAD)

# Count merge commits (these will be skipped by rebase)
MERGE_COUNT=$(git rev-list --merges --count ${BASE_REF}..HEAD)

# Calculate non-merge commits (actual commits that will be modified)
NON_MERGE_COUNT=$((COMMIT_COUNT - MERGE_COUNT))

# Exit early if there are no commits to modify
if [ "$COMMIT_COUNT" -eq 0 ]; then
    print_info "No commits to modify between $BASE_REF and HEAD"
    print_info "Your branch is up to date with the base"
    exit 0
fi

# Determine if BASE_REF is a branch or a commit hash
BASE_TYPE="commit"
if git show-ref --verify --quiet "refs/heads/$BASE_REF" 2>/dev/null; then
    BASE_TYPE="branch"
fi

################################################################################
# DISPLAY INFORMATION AND CONFIRMATION
################################################################################

# Display summary of what will be modified
echo ""
print_step "Base: $BASE_REF ($BASE_TYPE)"
print_step "Base commit: ${BASE_COMMIT:0:7}"
echo ""

# Show different messages depending on whether there are merge commits
if [ "$MERGE_COUNT" -gt 0 ]; then
    print_step "Total commits: $COMMIT_COUNT (including $MERGE_COUNT merge commit(s))"
    print_step "Commits to be modified: $NON_MERGE_COUNT (merge commits will be skipped by rebase)"
else
    print_step "Commits to be modified: $COMMIT_COUNT"
fi

echo ""
# Display the list of commits that will be affected
git log --oneline --format="  %h - %s (by %an <%ae>)" ${BASE_REF}..HEAD
echo ""

# Show what the new author information will be
print_warning "Will change all authors to:"
echo "  Author: $NEW_AUTHOR_NAME <$NEW_AUTHOR_EMAIL>"
echo "  Committer: $NEW_COMMITTER_NAME <$NEW_COMMITTER_EMAIL>"
echo ""

# Ask for user confirmation
# Default is 'yes' (just press Enter)
# Accepts: y, Y, yes, Yes, YES, or empty (Enter)
# Rejects: n, N, no, No, NO
read -p "Continue? (Y/n): " -r
echo

if [[ -z "$REPLY" ]] || [[ "$REPLY" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    print_info "Proceeding with modification..."
elif [[ "$REPLY" =~ ^[Nn]([Oo])?$ ]]; then
    print_info "Operation cancelled by user"
    exit 0
else
    print_error "Invalid input: $REPLY"
    print_error "Please enter 'y' or 'n'"
    exit 1
fi

################################################################################
# BACKUP CREATION
################################################################################

# Create a backup branch with timestamp
# This allows easy rollback if something goes wrong
BACKUP_BRANCH="backup-pr-authors-$(date +%Y%m%d-%H%M%S)"
print_step "Creating backup branch: $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"
print_info "Backup created. You can restore with: git reset --hard $BACKUP_BRANCH"

################################################################################
# ENVIRONMENT SETUP FOR REBASE
################################################################################

# Export environment variables that Git will use for author/committer info
# These are used by 'git commit --amend --reset-author'
export GIT_AUTHOR_NAME="$NEW_AUTHOR_NAME"
export GIT_AUTHOR_EMAIL="$NEW_AUTHOR_EMAIL"
export GIT_COMMITTER_NAME="$NEW_COMMITTER_NAME"
export GIT_COMMITTER_EMAIL="$NEW_COMMITTER_EMAIL"

#
# Cleanup function to unset environment variables
# This ensures we don't pollute the environment
#
cleanup() {
    unset GIT_AUTHOR_NAME
    unset GIT_AUTHOR_EMAIL
    unset GIT_COMMITTER_NAME
    unset GIT_COMMITTER_EMAIL
}

# Register cleanup function to run on script exit
trap cleanup EXIT

################################################################################
# REBASE SCRIPT PREPARATION
################################################################################

# Create a temporary script that will be used as GIT_SEQUENCE_EDITOR
# This script automatically changes all 'pick' commands to 'edit' commands
# in the rebase todo list, allowing us to modify each commit
TEMP_SCRIPT=$(mktemp)
cat > "$TEMP_SCRIPT" << 'EOF'
#!/bin/bash
# Automatically change all 'pick' to 'edit' in the rebase todo list
# This allows us to modify each commit's author information
sed -i.bak 's/^pick /edit /' "$1"
EOF
chmod +x "$TEMP_SCRIPT"

#
# Enhanced cleanup function that also removes temporary script
#
cleanup_all() {
    rm -f "$TEMP_SCRIPT"
    cleanup
}

# Update trap to use enhanced cleanup
trap cleanup_all EXIT

################################################################################
# INTERACTIVE REBASE EXECUTION
################################################################################

print_step "Starting rebase to modify commits..."
echo ""

# Start interactive rebase using our temporary script as the editor
# The script will automatically mark all commits for editing
GIT_SEQUENCE_EDITOR="$TEMP_SCRIPT" git rebase -i "$BASE_REF" || {
    print_error "Rebase failed to start"
    print_error "Aborting rebase and cleaning up..."
    git rebase --abort 2>/dev/null
    exit 1
}

################################################################################
# COMMIT MODIFICATION LOOP
################################################################################

# Track how many commits we actually modify
MODIFIED_COUNT=0

# Process each commit in the rebase
while true; do
    # Check if we're still in an active rebase
    # The rebase-merge directory exists only during an active rebase
    if [ ! -d "$(git rev-parse --git-dir)/rebase-merge" ]; then
        # Rebase is complete
        break
    fi
    
    # Amend the current commit with new author information
    # --reset-author: Use the environment variables for author/committer
    # --no-edit: Keep the existing commit message
    # --no-verify: Skip pre-commit and commit-msg hooks
    if git commit --amend --reset-author --no-edit --no-verify 2>/dev/null; then
        MODIFIED_COUNT=$((MODIFIED_COUNT + 1))
        CURRENT_COMMIT=$(git rev-parse --short HEAD)
        echo "  ✓ Modified commit $CURRENT_COMMIT"
    fi
    
    # Continue to the next commit in the rebase
    if ! git rebase --continue 2>/dev/null; then
        # Check if rebase is actually complete (not an error)
        if [ ! -d "$(git rev-parse --git-dir)/rebase-merge" ]; then
            # Rebase completed successfully
            break
        fi
        # Actual error occurred
        print_error "Failed to continue rebase"
        print_error "Aborting rebase and cleaning up..."
        git rebase --abort
        exit 1
    fi
done

################################################################################
# SUCCESS SUMMARY
################################################################################

echo ""
print_info "Successfully modified $MODIFIED_COUNT commits!"
print_warning "Commit hashes have changed due to history rewrite"
echo ""

# Display the modified commits with new author information
print_step "Modified commits:"
git log --format="  %h - %s (by %an <%ae>)" ${BASE_REF}..HEAD
echo ""

################################################################################
# POST-MODIFICATION OPTIONS
################################################################################

# Offer user options for next steps
print_warning "What would you like to do next?"
echo "  1. Push changes and delete backup (recommended)"
echo "  2. Just push changes (keep backup)"
echo "  3. Do nothing (manual operation)"
echo ""
read -p "Choose option (1/2/3, default=1): " -r
echo

# Default to option 1 if user just presses Enter
CHOICE="${REPLY:-1}"

case "$CHOICE" in
    1)
        # Option 1: Push and cleanup (most common workflow)
        print_step "Pushing changes to remote..."
        if git push --force-with-lease 2>&1; then
            print_info "Successfully pushed changes"
            print_step "Deleting backup branch..."
            git branch -D "$BACKUP_BRANCH"
            print_info "Backup branch deleted"
        else
            print_error "Push failed. Backup branch preserved: $BACKUP_BRANCH"
            print_info "You can try pushing manually: git push --force-with-lease"
            exit 1
        fi
        ;;
    2)
        # Option 2: Push but keep backup (cautious approach)
        print_step "Pushing changes to remote..."
        if git push --force-with-lease 2>&1; then
            print_info "Successfully pushed changes"
            print_info "Backup branch preserved: $BACKUP_BRANCH"
            print_warning "To delete backup later: git branch -D $BACKUP_BRANCH"
        else
            print_error "Push failed. Backup branch preserved: $BACKUP_BRANCH"
            print_info "You can try pushing manually: git push --force-with-lease"
            exit 1
        fi
        ;;
    3)
        # Option 3: Manual operation (for advanced users)
        print_info "No automatic actions taken"
        echo ""
        print_warning "Manual next steps:"
        echo "  1. Review changes: git log --format=fuller"
        echo "  2. Push changes: git push --force-with-lease"
        echo "  3. If you need to undo: git reset --hard $BACKUP_BRANCH"
        echo "  4. Delete backup when done: git branch -D $BACKUP_BRANCH"
        ;;
    *)
        # Invalid option
        print_error "Invalid option: $CHOICE"
        print_info "No actions taken. Backup preserved: $BACKUP_BRANCH"
        echo ""
        print_warning "Manual next steps:"
        echo "  1. Push changes: git push --force-with-lease"
        echo "  2. Delete backup: git branch -D $BACKUP_BRANCH"
        exit 1
        ;;
esac

################################################################################
# COMPLETION
################################################################################

echo ""
print_info "Done! ✨"
echo ""

exit 0
