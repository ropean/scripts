# Git Change PR Authors

A professional-grade Bash script for modifying author and committer information in Git Pull Request branches.

## 🎯 Overview

This script helps you standardize author information across commits in a PR branch without affecting the base branch. It's perfect for cleaning up author information before merging, fixing incorrect git configurations, or unifying multiple authors to a single identity.

## ✨ Features

- ✅ **Selective Modification**: Only modifies commits in the specified range
- ✅ **Base Branch Protection**: Never touches commits in the base branch
- ✅ **Message Preservation**: Keeps all commit messages unchanged
- ✅ **Merge Commit Handling**: Automatically skips merge commits during rebase
- ✅ **Automatic Backup**: Creates a backup branch for easy rollback
- ✅ **Interactive Workflow**: Confirmation prompts with sensible defaults
- ✅ **Smart Push**: Optional automatic push with cleanup
- ✅ **Error Handling**: Comprehensive validation and error messages
- ✅ **Professional Output**: Color-coded, easy-to-read terminal output

## 📋 Requirements

- Git 2.0 or higher
- Bash 4.0 or higher
- Write access to the repository
- Clean working directory (no uncommitted changes)

## 🚀 Quick Start

### 1. Configure Author Information

Edit the script and set your desired author information:

```bash
NEW_AUTHOR_NAME="Your Name"
NEW_AUTHOR_EMAIL="your.email@example.com"
NEW_COMMITTER_NAME="Your Name"
NEW_COMMITTER_EMAIL="your.email@example.com"
```

### 2. Run the Script

```bash
# Modify commits after main branch
./git-change-pr-authors.sh main

# Or specify a commit hash
./git-change-pr-authors.sh abc123def456
```

### 3. Follow the Prompts

The script will:
1. Show you which commits will be modified
2. Ask for confirmation (just press Enter to proceed)
3. Modify the commits
4. Offer to push changes automatically

## 📖 Usage Examples

### Example 1: Standard PR Workflow

```bash
# You're on feature branch, want to clean up authors before merge
$ git checkout feature-branch
$ ./git-change-pr-authors.sh main

[INFO] Current branch: feature-branch
[STEP] Base: main (branch)
[STEP] Commits to be modified: 5

  abc123 - Add feature X (by old.author@example.com)
  def456 - Fix bug Y (by another.author@example.com)
  ...

Continue? (Y/n): ⏎

[INFO] Successfully modified 5 commits!

Choose option (1/2/3, default=1): ⏎

[INFO] Successfully pushed changes
[INFO] Done! ✨
```

### Example 2: Modify Last Few Commits

```bash
# Only modify the last 3 commits
$ ./git-change-pr-authors.sh HEAD~3
```

### Example 3: Modify from Specific Commit

```bash
# Modify all commits after a specific commit hash
$ ./git-change-pr-authors.sh 059027114dd2419b20ddcbdf409ff3da15d715aa
```

### Example 4: Cautious Approach (Keep Backup)

```bash
$ ./git-change-pr-authors.sh main

Continue? (Y/n): y

Choose option (1/2/3, default=1): 2  # Keep backup

[INFO] Successfully pushed changes
[INFO] Backup branch preserved: backup-pr-authors-20251106-153023
```

## 🎨 Interactive Options

### First Confirmation: Proceed with Modification?

```
Continue? (Y/n):
```

- Press **Enter** or type **y**: Proceed with modification
- Type **n**: Cancel operation
- Default: **Yes**

### Second Choice: What to Do Next?

```
Choose option (1/2/3, default=1):
```

**Option 1** (Recommended, Default):
- Push changes to remote
- Delete backup branch
- Complete cleanup

**Option 2** (Cautious):
- Push changes to remote
- Keep backup branch for safety

**Option 3** (Manual):
- Don't push automatically
- Don't delete backup
- You handle everything manually

## 🔍 How It Works

### Step-by-Step Process

1. **Validation**
   - Checks if you're in a Git repository
   - Validates the base reference exists
   - Ensures no uncommitted changes
   - Verifies base is an ancestor of HEAD

2. **Analysis**
   - Counts commits to be modified
   - Detects merge commits (will be skipped)
   - Displays commit list for review

3. **Backup**
   - Creates timestamped backup branch
   - Format: `backup-pr-authors-YYYYMMDD-HHMMSS`

4. **Modification**
   - Uses interactive rebase
   - Modifies each commit's author/committer
   - Preserves commit messages and changes
   - Skips merge commits automatically

5. **Post-Processing**
   - Shows modified commits
   - Offers push and cleanup options
   - Provides rollback instructions

### What Gets Modified?

**Modified:**
- ✅ Author Name
- ✅ Author Email
- ✅ Committer Name
- ✅ Committer Email
- ✅ Commit Hash (due to history rewrite)

**Preserved:**
- ✅ Commit Message
- ✅ Code Changes
- ✅ Author Date (original timestamp)
- ✅ File History

**Skipped:**
- ⏭️ Merge Commits (automatically)
- ⏭️ Base Branch Commits

## ⚠️ Important Warnings

### History Rewriting

This script **rewrites Git history**. This means:

- ✅ All commit hashes will change
- ✅ Force push is required
- ✅ Coordinate with team members
- ✅ Use on feature branches, not main/master

### Force Push Safety

The script uses `git push --force-with-lease` which:

- ✅ Safer than `--force`
- ✅ Checks if remote has new commits
- ✅ Prevents accidental overwrites
- ✅ Fails if someone else pushed

### When to Use This Script

**Good Use Cases:**
- ✅ Cleaning up PR branches before merge
- ✅ Fixing incorrect git config
- ✅ Standardizing author info
- ✅ Personal feature branches

**Avoid Using For:**
- ❌ Main/master branches
- ❌ Shared branches with active collaborators
- ❌ Already merged commits
- ❌ Public release branches

## 🆘 Troubleshooting

### Problem: "Not a git repository"

**Solution:** Run the script from within a Git repository.

```bash
cd /path/to/your/git/repo
./git-change-pr-authors.sh main
```

### Problem: "You have uncommitted changes"

**Solution:** Commit or stash your changes first.

```bash
# Option 1: Stash changes
git stash

# Option 2: Commit changes
git commit -am "WIP: Save current work"
```

### Problem: "Base commit is not an ancestor"

**Solution:** Ensure you're on the correct branch and the base exists.

```bash
# Check your current branch
git branch

# Check if base branch exists
git branch -a | grep main
```

### Problem: "Push failed"

**Solution:** Someone else may have pushed to the branch.

```bash
# Check remote status
git fetch
git status

# If safe, force push
git push --force-with-lease
```

### Problem: Need to Undo Changes

**Solution:** Use the backup branch.

```bash
# List backup branches
git branch | grep backup-pr-authors

# Restore from backup
git reset --hard backup-pr-authors-20251106-153023

# Delete backup when done
git branch -D backup-pr-authors-20251106-153023
```

## 🔧 Advanced Usage

### Modify Specific Range

```bash
# From commit A to commit B
git checkout B
./git-change-pr-authors.sh A
```

### Dry Run (Manual Mode)

```bash
# Run script but choose option 3 (do nothing)
./git-change-pr-authors.sh main

# Choose option: 3
# Then manually review before pushing
git log --format=fuller
```

### Custom Author Per Run

Instead of editing the script, you can temporarily set environment variables:

```bash
# Set custom author for this run
export GIT_AUTHOR_NAME="Custom Name"
export GIT_AUTHOR_EMAIL="custom@example.com"
export GIT_COMMITTER_NAME="Custom Name"
export GIT_COMMITTER_EMAIL="custom@example.com"

# Run script
./git-change-pr-authors.sh main
```

## 📊 Output Explanation

### Color Coding

- 🟢 **Green [INFO]**: Informational messages
- 🔵 **Blue [STEP]**: Process steps
- 🟡 **Yellow [WARNING]**: Warnings and important notes
- 🔴 **Red [ERROR]**: Errors

### Sample Output

```
[INFO] Current branch: feature-branch
[STEP] Base: main (branch)
[STEP] Base commit: abc1234
[STEP] Total commits: 5 (including 1 merge commit(s))
[STEP] Commits to be modified: 4 (merge commits will be skipped by rebase)

  def456 - Add feature (by old@example.com)
  ghi789 - Fix bug (by another@example.com)
  jkl012 - Merge pull request #100 (by bot@github.com)
  mno345 - Update docs (by old@example.com)

[WARNING] Will change all authors to:
  Author: Wei Guo <wei.guo@moodys.com>
  Committer: Wei Guo <wei.guo@moodys.com>

Continue? (Y/n):
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

MIT License - feel free to use and modify as needed.

## 👤 Author

**Wei Guo**
- GitHub: [@your-github](https://github.com/your-github)
- Email: wei.guo@moodys.com

## 🙏 Acknowledgments

- Inspired by common Git workflow challenges
- Built with best practices from the Git community
- Tested in real-world PR scenarios

## 📚 Related Scripts

This script is part of a collection of Git utility scripts:

- `git-change-commit.sh` - Modify a single specific commit
- `git-change-all-authors.sh` - Modify all commits in repository
- `git-squash-to-single-commit.sh` - Squash all history to one commit

## 🔗 Resources

- [Git Documentation](https://git-scm.com/doc)
- [Git Rebase Guide](https://git-scm.com/docs/git-rebase)
- [Git Filter-Branch](https://git-scm.com/docs/git-filter-branch)

---

**Made with ❤️ for the Git community**

*Last updated: November 2025*

