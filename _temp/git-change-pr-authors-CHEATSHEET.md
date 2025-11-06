# Git Change PR Authors - Quick Reference

## 🚀 Quick Start

```bash
# 1. Edit script configuration
NEW_AUTHOR_NAME="Your Name"
NEW_AUTHOR_EMAIL="your.email@example.com"

# 2. Run script
./git-change-pr-authors.sh main

# 3. Press Enter twice (use defaults)
```

## 📝 Common Commands

```bash
# Modify commits after main branch
./git-change-pr-authors.sh main

# Modify commits after develop
./git-change-pr-authors.sh develop

# Modify last 3 commits
./git-change-pr-authors.sh HEAD~3

# Modify from specific commit
./git-change-pr-authors.sh abc123def456
```

## 🎯 Interactive Prompts

### Prompt 1: Continue?
```
Continue? (Y/n):
```
- **Enter** or **y** = Yes, proceed
- **n** = No, cancel
- **Default**: Yes

### Prompt 2: What next?
```
Choose option (1/2/3, default=1):
```
- **1** = Push + Delete backup (recommended)
- **2** = Push + Keep backup
- **3** = Do nothing (manual)
- **Default**: 1

## 🆘 Emergency Rollback

```bash
# List backups
git branch | grep backup-pr-authors

# Restore from backup
git reset --hard backup-pr-authors-YYYYMMDD-HHMMSS

# Force push to remote
git push --force-with-lease
```

## ⚠️ Before Running

- [ ] You're in a Git repository
- [ ] No uncommitted changes
- [ ] You're on the correct branch
- [ ] You've edited the author config
- [ ] You've coordinated with team (if shared branch)

## ✅ After Running

- [ ] Review changes: `git log --format=fuller`
- [ ] Verify author info is correct
- [ ] Force push completed (if option 1 or 2)
- [ ] Delete backup (if option 1)
- [ ] Notify team members (if shared branch)

## 🔍 Verification Commands

```bash
# Check current author
git log --format="%an <%ae>" -1

# Check all authors in range
git log --format="%an <%ae>" main..HEAD | sort -u

# View full commit details
git log --format=fuller -1

# Compare with remote
git log --oneline HEAD..origin/$(git branch --show-current)
```

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| "Not a git repository" | `cd` into your repo |
| "Uncommitted changes" | `git stash` or commit |
| "Base not ancestor" | Check branch/commit exists |
| "Push failed" | Check remote status, retry push |
| "Detached HEAD" | `git checkout <branch>` |

## 💡 Pro Tips

1. **Always use option 1** for typical workflow
2. **Use option 2** if you're unsure
3. **Use option 3** to review before pushing
4. **Backup persists** until you delete it
5. **Force-with-lease** is safer than force

## 📊 What Changes

| Item | Modified? |
|------|-----------|
| Author Name | ✅ Yes |
| Author Email | ✅ Yes |
| Committer Name | ✅ Yes |
| Committer Email | ✅ Yes |
| Commit Hash | ✅ Yes |
| Commit Message | ❌ No |
| Code Changes | ❌ No |
| Author Date | ❌ No |
| Base Branch | ❌ No |

## 🎨 Output Colors

- 🟢 **[INFO]** - Informational
- 🔵 **[STEP]** - Progress
- 🟡 **[WARNING]** - Important
- 🔴 **[ERROR]** - Error

## 📞 Quick Help

```bash
# Show usage
./git-change-pr-authors.sh

# View script comments
head -100 git-change-pr-authors.sh

# Check Git version
git --version
```

---

**Remember**: This rewrites history! Use on feature branches, not main/master.

