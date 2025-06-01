# Release Process

This document outlines the release process for OCode, including versioning, testing, and deployment procedures.

## Overview

OCode uses semantic versioning and automated releases through GitHub Actions. The process is designed to ensure quality and consistency across all releases.

## Versioning Strategy

### Semantic Versioning (SemVer)
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes that require user action
- **MINOR**: New features that are backward compatible
- **PATCH**: Bug fixes and minor improvements

### Version Examples
```
0.1.0    - Initial alpha release
0.2.0    - New features added
0.2.1    - Bug fixes
1.0.0    - First stable release
1.1.0    - New backward-compatible features
2.0.0    - Breaking changes
```

### Pre-release Versions
```
1.0.0-alpha.1    - Alpha release
1.0.0-beta.1     - Beta release
1.0.0-rc.1       - Release candidate
```

## Release Types

### Automated Releases (Recommended)
Releases are automatically triggered when version tags are pushed to the repository.

#### Creating a Release
1. **Update Version**: Update version in `pyproject.toml`
2. **Create and Push Tag**:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```
3. **Automatic Process**: GitHub Actions will:
   - Run full test suite
   - Build packages
   - Publish to PyPI
   - Create GitHub release
   - Generate changelog

### Manual Releases
For emergency releases or when automation is unavailable:

```bash
# Manual release workflow
gh workflow run release.yml -f version=1.2.3 -f environment=production
```

## Release Checklist

### Pre-Release
- [ ] All tests pass on main branch
- [ ] Version number updated in `pyproject.toml`
- [ ] CHANGELOG.md updated (if maintaining manually)
- [ ] Documentation updated for new features
- [ ] Security scan passes
- [ ] Performance tests completed

### Release Validation
- [ ] Package builds successfully
- [ ] All dependencies resolved
- [ ] Installation tests pass on multiple platforms
- [ ] CLI commands work correctly
- [ ] Documentation renders properly

### Post-Release
- [ ] GitHub release created with proper changelog
- [ ] PyPI package available and installable
- [ ] Test installation on clean environment
- [ ] Update documentation links if needed
- [ ] Announce release (if applicable)

## Testing Strategy

### Automated Testing
Every release goes through comprehensive testing:

#### Unit Tests
```bash
pytest tests/unit/ -v --cov=ocode_python
```

#### Integration Tests
```bash
pytest tests/integration/ -v
```

#### Multi-Platform Testing
- Ubuntu (latest)
- macOS (latest)
- Windows (latest)
- Python 3.8, 3.9, 3.10, 3.11, 3.12

#### Security Testing
```bash
bandit -r ocode_python/
safety check
```

### Manual Testing
Before major releases, perform manual testing:

1. **Installation Testing**
   ```bash
   # Test pip installation
   pip install ocode==1.2.3

   # Test development installation
   pip install -e .

   # Test with different Python versions
   python3.8 -m pip install ocode==1.2.3
   python3.12 -m pip install ocode==1.2.3
   ```

2. **Functionality Testing**
   ```bash
   # Basic CLI functionality
   ocode --help
   ocode --version

   # Core features
   ocode -p "Hello world"
   ocode init
   ocode config --list
   ```

3. **Integration Testing**
   ```bash
   # Ollama integration
   ocode -p "Analyze this codebase"

   # Tool functionality
   ocode -p "Run tests and show results"
   ```

## Environment Configuration

### PyPI Environments

#### Test PyPI (Pre-releases)
- **URL**: https://test.pypi.org/
- **Usage**: Alpha, beta, and release candidates
- **Installation**: `pip install -i https://test.pypi.org/simple/ ocode==1.0.0a1`

#### Production PyPI (Stable Releases)
- **URL**: https://pypi.org/
- **Usage**: Stable releases only
- **Installation**: `pip install ocode==1.0.0`

### GitHub Secrets Required
- `PYPI_API_TOKEN`: Production PyPI token
- `TEST_PYPI_API_TOKEN`: Test PyPI token

## Common Release Scenarios

### Patch Release (Bug Fix)
```bash
# Example: 1.2.3 → 1.2.4
# Update pyproject.toml version
git add pyproject.toml
git commit -m "Bump version to 1.2.4"
git tag v1.2.4
git push origin main v1.2.4
```

### Minor Release (New Features)
```bash
# Example: 1.2.4 → 1.3.0
# Update pyproject.toml version
# Ensure all new features are documented
git add .
git commit -m "Bump version to 1.3.0"
git tag v1.3.0
git push origin main v1.3.0
```

### Major Release (Breaking Changes)
```bash
# Example: 1.3.0 → 2.0.0
# Update pyproject.toml version
# Create migration guide
# Update documentation for breaking changes
git add .
git commit -m "Bump version to 2.0.0 - breaking changes"
git tag v2.0.0
git push origin main v2.0.0
```

### Pre-release
```bash
# Example: 2.0.0-alpha.1
git tag v2.0.0-alpha.1
git push origin v2.0.0-alpha.1
# This will publish to Test PyPI automatically
```

## Troubleshooting

### Release Failed
1. Check GitHub Actions logs
2. Verify all tests pass locally
3. Ensure version format is correct
4. Check PyPI credentials

### Package Not Available
1. Check PyPI status page
2. Verify package was published successfully
3. Wait for PyPI propagation (up to 10 minutes)
4. Try clearing pip cache: `pip cache purge`

### Version Conflicts
1. Ensure version is unique
2. Check existing tags: `git tag -l`
3. Delete problematic tag if needed: `git tag -d v1.2.3`

## Rollback Procedures

### GitHub Release Rollback
```bash
# Delete release and tag
gh release delete v1.2.3 --yes
git tag -d v1.2.3
git push origin --delete v1.2.3
```

### PyPI Rollback
- PyPI does not allow deleting published packages
- Create a new patch version with fixes
- Consider yanking the problematic version on PyPI

## Monitoring and Metrics

### Release Metrics to Track
- Download statistics from PyPI
- Installation success rates
- Bug reports after release
- User feedback and issues

### Tools
- **PyPI Stats**: https://pypistats.org/packages/ocode
- **GitHub Insights**: Repository traffic and clones
- **Issue Tracker**: Monitor post-release issues

## Security Considerations

### Release Security
- All releases are built in isolated CI environment
- PyPI tokens are stored as GitHub secrets
- Release artifacts are signed (planned)
- Dependency scanning before release

### Vulnerability Response
1. **Critical Security Issues**: Immediate patch release
2. **Documentation**: Update security advisory
3. **Communication**: Notify users through appropriate channels

## Future Improvements

### Planned Enhancements
- [ ] Automatic changelog generation from commits
- [ ] Release artifact signing
- [ ] Automated documentation deployment
- [ ] Performance regression testing
- [ ] Beta user testing program
- [ ] Release candidate process for major versions

This process ensures reliable, high-quality releases while maintaining automation and reducing manual overhead.
