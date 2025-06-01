# Pull Request

## Description
<!-- Provide a brief description of the changes in this PR -->

## Type of Change
<!-- Mark the relevant option with an "x" -->
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🧪 Test improvements
- [ ] 🔒 Security improvement
- [ ] 🏗️ Infrastructure/tooling change

## Related Issues
<!-- Link to any related issues -->
Fixes #(issue number)
Relates to #(issue number)

## Changes Made
<!-- Describe the specific changes made in this PR -->
-
-
-

## Testing
<!-- Describe how you tested these changes -->
- [ ] Unit tests pass locally (`pytest tests/unit/`)
- [ ] Integration tests pass locally (`pytest tests/integration/`)
- [ ] Manual testing completed
- [ ] Added new tests for new functionality
- [ ] All existing tests still pass

### Test Evidence
<!-- Include any relevant test output, screenshots, or examples -->
```bash
# Example of running tests
pytest tests/ -v
```

## Code Quality
<!-- Confirm code quality checks -->
- [ ] Code follows the project style guidelines (`black`, `isort`)
- [ ] Code passes linting (`flake8`)
- [ ] Type checking passes (`mypy`)
- [ ] Security scan passes (`bandit`)
- [ ] No new security vulnerabilities introduced

### Quality Check Commands
```bash
# Run these commands to verify code quality
make format-check  # or: black --check ocode_python/ && isort --check-only ocode_python/
make lint         # or: flake8 ocode_python/ && mypy ocode_python/
make security     # or: bandit -r ocode_python/
```

## Documentation
<!-- Confirm documentation updates -->
- [ ] Updated relevant documentation
- [ ] Added docstrings for new functions/classes
- [ ] Updated CLAUDE.md if development process changed
- [ ] Updated README.md if user-facing changes
- [ ] Added/updated examples if applicable

## Breaking Changes
<!-- If this introduces breaking changes, describe them here -->
- None

OR

- [ ] Updated version number appropriately
- [ ] Added migration guide or notes
- [ ] Updated changelog/release notes

## Performance Impact
<!-- Describe any performance implications -->
- [ ] No performance impact
- [ ] Performance improvement (describe)
- [ ] Minor performance impact (acceptable)
- [ ] Significant performance impact (requires discussion)

## Security Considerations
<!-- Describe any security implications -->
- [ ] No security impact
- [ ] Security improvement
- [ ] Requires security review
- [ ] New security considerations documented

## Deployment Notes
<!-- Any special deployment considerations -->
- [ ] No special deployment requirements
- [ ] Requires environment variable changes
- [ ] Requires configuration updates
- [ ] Requires migration steps

## Screenshots/Examples
<!-- If applicable, add screenshots or examples of the changes -->

## Checklist
<!-- Confirm you've completed these steps -->
- [ ] I have read the [CONTRIBUTING.md](../CONTRIBUTING.md) guide
- [ ] My code follows the project's coding standards
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Additional Notes
<!-- Any additional information that reviewers should know -->

---

### For Maintainers
<!-- This section is for maintainer use -->
- [ ] Ready for review
- [ ] Requires design discussion
- [ ] Requires breaking change approval
- [ ] Requires security review
- [ ] Ready to merge
