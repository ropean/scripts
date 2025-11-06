# Git Author Scripts - Complete Guide

A professional collection of Git scripts for managing author information across different scopes.

## 📚 Script Overview

| Script | Scope | Speed | Use Case |
|--------|-------|-------|----------|
| [git-change-commit.sh](#1-git-change-commitsh) | 1 commit | ⚡ Fast | Fix one specific commit |
| [git-change-pr-authors.sh](#2-git-change-pr-authorssh) | Commit range | ⚡ Fast | Clean up PR branch |
| [git-change-all-authors.sh](#3-git-change-all-authorssh) | ALL commits | 🐌 Slow | Standardize entire repo |
| [git-change-all-authors-fast.sh](#4-git-change-all-authors-fastsh) | ALL commits | 🚀 Very Fast | Large repositories |

---

## 🎯 Quick Decision Tree

```
What do you need to do?
│
├─ Fix ONE specific commit?
│  └─ Use: git-change-commit.sh
│
├─ Clean up a PR branch (multiple commits)?
│  └─ Use: git-change-pr-authors.sh
│
├─ Standardize ALL commits in repository?
│  │
│  ├─ Small repo (< 1,000 commits)?
│  │  └─ Use: git-change-all-authors.sh
│  │
│  └─ Large repo (> 1,000 commits)?
│     └─ Use: git-change-all-authors-fast.sh
```

---

## 1. git-change-commit.sh

**The Surgical Tool** - Fix one specific commit

### When to Use

✅ **Use when:**
- You need to fix ONE specific commit
- You know the exact commit hash
- Other commits are fine, only this one needs fixing
- You want to change the commit message too (optional)

❌ **Don't use when:**
- You need to fix multiple commits
- You want to clean up a PR branch
- You need to fix all commits in the repository

### Usage

```bash
# Fix author only, keep message
./git-change-commit.sh abc123def456

# Fix author AND change message
./git-change-commit.sh abc123def456 "New commit message"
```

### Example Scenario

```
You have this history:
  A → B → C → D → E
      ↑
      This one commit has wrong author

After running:
  A → B' → C' → D' → E'
      ↑
      Only this commit's author is fixed
      (C, D, E are updated due to hash change)
```

### Performance
- **Speed**: ⚡ Very Fast (< 1 second)
- **Commits affected**: 1 + all subsequent commits

---

## 2. git-change-pr-authors.sh

**The PR Cleaner** - Clean up Pull Request branches

### When to Use

✅ **Use when:**
- You're working on a PR branch
- Multiple commits need author fixes
- You want to clean up before merging
- You only want to modify commits AFTER a base branch

❌ **Don't use when:**
- You only need to fix one commit
- You need to fix ALL commits (including main branch)
- You want to modify the base branch too

### Usage

```bash
# Clean up PR branch based on main
./git-change-pr-authors.sh main

# Clean up from specific commit
./git-change-pr-authors.sh abc123def456

# Clean up based on develop
./git-change-pr-authors.sh develop
```

### Example Scenario

```
You have this structure:
  main:     A → B → C (don't touch)
                 ↓
  feature:       D → E → F (fix these)
                 ↑   ↑   ↑
              Different authors

After running:
  main:     A → B → C (unchanged)
                 ↓
  feature:       D' → E' → F' (all fixed)
                 ↑    ↑    ↑
              Unified author
```

### Features

- ✅ Interactive confirmation (default: Yes)
- ✅ Shows merge commits (automatically skipped)
- ✅ Automatic backup branch
- ✅ Optional automatic push and cleanup
- ✅ Preserves commit messages

### Performance
- **Speed**: ⚡ Fast (< 1 second per commit)
- **Commits affected**: Only commits after base

---

## 3. git-change-all-authors.sh

**The Repository Standardizer** - Unify all authors (Standard Version)

### When to Use

✅ **Use when:**
- You need to change ALL commits in repository
- You want to unify all authors to single identity
- Repository is small to medium (< 10,000 commits)
- You don't have git-filter-repo installed

❌ **Don't use when:**
- You only need to fix a PR branch
- You only need to fix one commit
- Repository is very large (> 10,000 commits)
- You need fast execution

### Usage

```bash
# Standard usage (no parameters needed)
./git-change-all-authors.sh
```

### Example Scenario

```
Before:
  Commit A - Author: John <john@example.com>
  Commit B - Author: Jane <jane@example.com>
  Commit C - Author: Bob <bob@example.com>
  Commit D - Author: Alice <alice@example.com>

After:
  Commit A' - Author: Wei Guo <wei.guo@moodys.com>
  Commit B' - Author: Wei Guo <wei.guo@moodys.com>
  Commit C' - Author: Wei Guo <wei.guo@moodys.com>
  Commit D' - Author: Wei Guo <wei.guo@moodys.com>
```

### Performance

| Repository Size | Estimated Time |
|----------------|----------------|
| 100 commits | ~10 seconds |
| 1,000 commits | ~1-2 minutes |
| 10,000 commits | ~10-30 minutes |
| 50,000 commits | ~1-2 hours |

### Features

- ✅ Works on all Git versions
- ✅ No additional dependencies
- ✅ Creates backup branch
- ✅ Shows before/after comparison

---

## 4. git-change-all-authors-fast.sh

**The Speed Demon** - Unify all authors (Fast Version)

### When to Use

✅ **Use when:**
- Repository has > 1,000 commits
- git-change-all-authors.sh is too slow
- You need fast execution time
- You have git-filter-repo installed

❌ **Don't use when:**
- You only need to fix a PR branch
- You only need to fix one commit
- Repository is small (< 1,000 commits)
- git-filter-repo is not available

### Installation Required

```bash
# macOS
brew install git-filter-repo

# Ubuntu/Debian
apt install git-filter-repo

# Using pip
pip3 install git-filter-repo
```

### Usage

```bash
# Standard usage (no parameters needed)
./git-change-all-authors-fast.sh
```

### Performance Comparison

| Repository Size | Standard Version | Fast Version | Speed Up |
|----------------|------------------|--------------|----------|
| 1,000 commits | 1 minute | 5 seconds | 12x |
| 10,000 commits | 20 minutes | 1 minute | 20x |
| 50,000 commits | 2 hours | 5 minutes | 24x |
| 100,000 commits | 10 hours | 15 minutes | 40x |

### Important Differences

⚠️ **Remote URLs are removed** (safety feature)
- You must re-add remotes manually:
  ```bash
  git remote add origin <url>
  ```

⚠️ **Creates full repository backup**
- Backup is a complete copy of the repository directory
- Located at: `../<repo-name>-backup-YYYYMMDD-HHMMSS/`

---

## 📊 Comparison Matrix

### By Use Case

| Use Case | Recommended Script |
|----------|-------------------|
| Fix one wrong commit | git-change-commit.sh |
| Clean up PR before merge | git-change-pr-authors.sh |
| Standardize small repo | git-change-all-authors.sh |
| Standardize large repo | git-change-all-authors-fast.sh |
| Fix last 3 commits | git-change-pr-authors.sh HEAD~3 |
| Hide all historical authors | git-change-all-authors-fast.sh |

### By Repository Size

| Commits | Recommended Script | Execution Time |
|---------|-------------------|----------------|
| < 10 | git-change-commit.sh | < 1 second |
| 10-100 | git-change-pr-authors.sh | < 10 seconds |
| 100-1,000 | git-change-all-authors.sh | 1-2 minutes |
| > 1,000 | git-change-all-authors-fast.sh | 1-15 minutes |

### By Requirements

| Script | Git Version | Additional Tools | Complexity |
|--------|-------------|-----------------|------------|
| git-change-commit.sh | 2.0+ | None | Simple |
| git-change-pr-authors.sh | 2.0+ | None | Simple |
| git-change-all-authors.sh | 2.0+ | None | Simple |
| git-change-all-authors-fast.sh | 2.22+ | git-filter-repo | Medium |

---

## 🚀 Getting Started

### 1. Choose Your Script

Use the decision tree above to select the right script for your needs.

### 2. Configure Author Information

Edit the script and set your author information:

```bash
NEW_AUTHOR_NAME="Your Name"
NEW_AUTHOR_EMAIL="your.email@example.com"
NEW_COMMITTER_NAME="Your Name"
NEW_COMMITTER_EMAIL="your.email@example.com"
```

### 3. Run the Script

```bash
# Make executable (first time only)
chmod +x git-change-*.sh

# Run the script
./git-change-pr-authors.sh main
```

### 4. Follow the Prompts

All scripts provide:
- Clear information about what will be modified
- Interactive confirmation
- Automatic backups
- Rollback instructions

---

## ⚠️ Important Warnings

### All Scripts

- ✅ **Rewrite Git history** - commit hashes will change
- ✅ **Force push required** - use `git push --force-with-lease`
- ✅ **Coordinate with team** - inform collaborators before rewriting shared branches
- ✅ **Automatic backups** - all scripts create backups for safety

### Best Practices

1. **Always review** the list of commits before confirming
2. **Test on a branch** first if unsure
3. **Communicate with team** before rewriting shared history
4. **Keep backups** until you're certain everything is correct
5. **Use force-with-lease** instead of force when pushing

---

## 🆘 Emergency Rollback

If something goes wrong, all scripts create backups:

```bash
# List backup branches
git branch | grep backup

# Restore from backup
git reset --hard backup-pr-authors-20251106-153023

# Force push to remote (if already pushed)
git push --force-with-lease
```

---

## 📖 Additional Resources

- [git-change-pr-authors-README.md](git-change-pr-authors-README.md) - Detailed guide for PR script
- [git-change-pr-authors-CHEATSHEET.md](git-change-pr-authors-CHEATSHEET.md) - Quick reference
- [Git Documentation](https://git-scm.com/doc)
- [git-filter-repo](https://github.com/newren/git-filter-repo)

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues or pull requests.

## 📄 License

MIT License - free to use and modify.

## 👤 Author

**Wei Guo**
- Email: wei.guo@moodys.com

---

**Made with ❤️ for the Git community**

*Last updated: November 2025*

