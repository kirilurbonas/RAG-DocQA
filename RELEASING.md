# Release Guide for RAG-DocQA

This document describes the release process for RAG-DocQA.

## Release Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- `MAJOR`: Breaking changes or major new features
- `MINOR`: New features, backward compatible
- `PATCH`: Bug fixes, backward compatible

## Pre-Release Checklist

Before cutting a release:

1. **All Tests Pass**
   ```bash
   cd backend
   pytest tests -v
   flake8 . --select=E9,F63,F7,F82
   pip-audit -r requirements.txt
   ```

2. **Update Version Numbers**
   - Update version in `pyproject.toml` (if created)
   - Update version in any Docker image tags

3. **Update CHANGELOG.md**
   - Add new version section with date
   - List all changes under: Added, Fixed, Changed, Removed, Security
   - Include metrics or impact summary
   - Add migration guide if breaking changes

4. **Update README.md**
   - Update any version-specific documentation
   - Update links to version-specific features
   - Verify all code examples work

5. **Documentation Review**
   - Verify IMPROVEMENTS.md is current
   - Check SECURITY.md for any new security features
   - Update API documentation if endpoints changed

6. **Commit Message Convention**
   - Use format: `release: v1.2.3 - release description`
   - Include changelog summary in commit body

## Release Process

### 1. Create Release Commit

```bash
# Make sure everything is committed
git status

# Create release commit
git commit --allow-empty -m "release: v1.1.0 - Critical reliability fixes

Milestone 1 & 2 Completion:
- Document registry persistence
- Async I/O operations
- Streaming protocol fix
- OpenAI timeout/retry handling
- Dependency upgrades (7 critical fixes)
- Test suite implementation

See CHANGELOG.md for detailed changes."
```

### 2. Tag Release

```bash
# Create annotated tag (recommended)
git tag -a v1.1.0 -m "Release v1.1.0: Critical reliability fixes

See CHANGELOG.md for details.

Key improvements:
- Fixed document data loss on restart
- Fixed event loop blocking (async all I/O)
- Fixed streaming text loss (JSON SSE)
- Added health check endpoint
- Added comprehensive test suite
- 7+ dependency CVE fixes"

# Or lightweight tag (simpler)
git tag v1.1.0

# Push tag to remote
git push origin v1.1.0
git push origin main
```

### 3. Create GitHub Release

```bash
# Using gh CLI (recommended)
gh release create v1.1.0 \
  --title "v1.1.0: Critical Reliability Fixes" \
  --notes "See CHANGELOG.md for details and migration guide"

# Or manually via GitHub web UI:
# 1. Go to Releases page
# 2. Click "Draft a new release"
# 3. Select tag v1.1.0
# 4. Title: "v1.1.0: Critical Reliability Fixes"
# 5. Description: Copy from CHANGELOG.md
# 6. Click "Publish release"
```

### 4. Build and Push Docker Images (if applicable)

```bash
# Build images
docker build -t rag-docqa/backend:1.1.0 backend/
docker build -t rag-docqa/frontend:1.1.0 frontend/

# Tag as latest
docker tag rag-docqa/backend:1.1.0 rag-docqa/backend:latest
docker tag rag-docqa/frontend:1.1.0 rag-docqa/frontend:latest

# Push to registry
docker push rag-docqa/backend:1.1.0
docker push rag-docqa/backend:latest
docker push rag-docqa/frontend:1.1.0
docker push rag-docqa/frontend:latest
```

## Version Branches

For major releases, optionally create a maintenance branch:

```bash
# Create maintenance branch for v1.1
git branch release/v1.1
git push origin release/v1.1

# Subsequent patches for v1.1.x come from this branch
```

## Hotfixes (Patch Releases)

For urgent patch releases:

```bash
# Create from release branch (or tag)
git checkout -b hotfix/critical-bug release/v1.1

# Make fix and test
git commit -m "fix: critical bug fix

Details of fix"

# Test thoroughly
pytest tests -v

# Tag as patch release
git tag -a v1.1.1 -m "Hotfix: Critical bug fix"

# Push
git push origin hotfix/critical-bug
git push origin v1.1.1
git push origin main

# Merge back to main
git checkout main
git pull
git merge hotfix/critical-bug
git push origin main
```

## Changelog Entry Template

```markdown
## [X.X.X] - YYYY-MM-DD

### 🔒 Security & Reliability
- Item with high impact

### Added
- New feature 1
- New feature 2

### Fixed
- Bug fix 1
- Bug fix 2

### Changed
- Breaking change or significant change

### Removed
- Deprecated item

### 📊 Metrics
| Aspect | Before | After |
|--------|--------|-------|
```

## Release Notes Guidelines

### Good Release Notes Include:
- ✅ Summary of major changes (1-2 sentences)
- ✅ List of key improvements by category
- ✅ Breaking changes highlighted with `⚠️ BREAKING`
- ✅ Migration guide for breaking changes
- ✅ Links to detailed documentation
- ✅ Known issues or limitations
- ✅ Contributors (if applicable)

### Example:

```markdown
# v1.1.0: Critical Reliability Fixes

This release addresses critical production issues and adds comprehensive testing.

## Key Improvements

### 🔒 Reliability
- Fixed document data loss on restart (registry now persists)
- Fixed event loop blocking (all I/O is now async)
- Fixed streaming response text loss (JSON-encoded SSE frames)
- Added real health check endpoint (GET /health)

### 📊 Testing
- Comprehensive test suite for critical paths (~500 lines)
- CI/CD integration with automated pytest execution
- 30%+ coverage on core functionality

### 🛠️ Maintenance
- Upgraded 7 dependencies with known CVEs
- Added environment variable validation (Pydantic)
- Fixed deprecated datetime.utcnow() for Python 3.12+

## Migration Guide

See [CHANGELOG.md](CHANGELOG.md) for detailed migration steps.

## Breaking Changes

⚠️ If using RAGService directly:
```python
# OLD
doc = rag_service.process_and_store_document(...)

# NEW
doc = await rag_service.process_and_store_document_async(...)
```
```

## Post-Release

After publishing a release:

1. **Verify**:
   - [ ] Tag exists on GitHub
   - [ ] Release notes are published
   - [ ] Docker images pushed (if applicable)
   - [ ] Documentation is updated

2. **Announce**:
   - [ ] Post release notes to relevant channels
   - [ ] Update project documentation
   - [ ] Notify stakeholders

3. **Monitor**:
   - [ ] Watch for issues reported against new release
   - [ ] Prepare hotfix if critical issues found
   - [ ] Gather feedback for next release

## Long-term Support (LTS)

For LTS releases:
- Create branch: `release/vX.X` (e.g., `release/v1.0`)
- Backport critical fixes only
- Security fixes indefinitely (or stated end date)
- Bug fixes for 12 months

Example LTS timeline:
- v1.0.0 released (LTS designation)
- v1.0.1, v1.0.2, etc. released for 12 months
- After 12 months, only security fixes
- End of life announced 6 months in advance

## FAQ

**Q: How often should we release?**
A: When there are user-facing changes or bug fixes. Typically every 2-4 weeks.

**Q: Can we skip patch versions?**
A: No, always increment sequentially (1.1.0 → 1.1.1, not 1.1.5).

**Q: What if we need to release from an old branch?**
A: Create a new patch from the old tag:
```bash
git checkout v1.0.0
git checkout -b patch/v1.0.1
# Make fix
git tag v1.0.1
git push origin v1.0.1
```

**Q: Should we use annotated or lightweight tags?**
A: Annotated tags (with `-a`) are recommended. They include metadata and are better for releases.
