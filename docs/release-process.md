# Branch Protection Setup

To prevent releases when tests fail, we recommend setting up GitHub branch protection rules:

## 1. Automatic Protection (via GitHub CLI)

```bash
# Install GitHub CLI if not already installed
# Then run these commands:

gh api repos/kungfumarcus/fortherekord/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":0}' \
  --field restrictions=null
```

## 2. Manual Setup (via GitHub Web UI)

1. Go to: https://github.com/kungfumarcus/fortherekord/settings/branches
2. Click "Add rule" for `main` branch
3. Enable:
   - ✅ "Require status checks to pass before merging"
   - ✅ "Require branches to be up to date before merging"
   - ✅ Select "test" status check
   - ✅ "Include administrators" (optional but recommended)

## 3. Workflow Protection

Our workflows now have smart test verification:

```
Tag Push → Check Tests → Build Job → Release Job
            ↓           ↓          ↓
      API CHECK IF   ONLY IF     ONLY IF
      TESTS PASSED   TESTS OK    BUILD OK
```

When you push a tag:
1. **Check Tests Job**: Queries GitHub API to verify the Test workflow passed for this commit
2. **Build Job**: Only runs if tests passed
3. **Release Job**: Only runs if builds succeed

If tests haven't run or failed for the tagged commit, the entire workflow stops immediately.

## 4. Best Practices

1. **Only tag from main branch**: Ensure main is always tested
2. **Use semantic versioning**: `v1.2.3` format
3. **Test before tagging**: Run `unit_test.bat` and `e2e_test.bat` locally first

## 5. Release Process

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull

# 2. Run tests locally
./unit_test.bat
./e2e_test.bat

# 3. Create and push tag (only if tests pass)
git tag v1.2.3
git push origin v1.2.3

# 4. GitHub Actions will:
#    - Run tests again
#    - Build executables (if tests pass)
#    - Create release (if builds succeed)
```