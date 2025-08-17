# CI/CD Specification

## Scope
Automated build, test, and deployment pipeline using GitHub Actions to create cross-platform executables for Windows and macOS.

## Out of Scope
- Package manager distribution (Chocolatey, Homebrew, etc.)

## Technical Requirements
- **Build Tool**: PyInstaller for creating standalone executables
- **CI Platform**: GitHub Actions for cross-platform builds
- **Versioning**: setuptools_scm for automatic version generation from git
- **Supported Platforms**: Windows (exe), macOS (app bundle or binary)

## Function Points

### Build Pipeline
Single pipeline with sequential stages triggered on push to main branch, test branch, and pull requests:

#### Stage 1: Code Quality & Testing
- Run linting checks using flake8 and pylint
- Execute type checking using mypy
- Execute unit tests using pytest
- Generate code coverage reports
- Fail pipeline if any quality checks or tests don't pass

#### Stage 2: Build
- Run on multiple operating systems (Windows, macOS)
- Install Python dependencies from pyproject.toml
- Generate version using setuptools_scm from git tags and commits
- Build standalone executables using PyInstaller with version metadata

#### Stage 3: E2E Testing
- Run end-to-end tests against built executables
- Test executable functionality with mock data
- Fail pipeline if E2E tests don't pass

#### Stage 4: Publish
- Upload artifacts: fortherekord.exe (Windows), fortherekord (macOS)
- Only run on test and main branches (skip for pull requests)

#### Stage 5: Cleanup (Test Branch Only)
- Delete previous test branch artifacts after successful publish
- Keep only the latest artifacts from current build

### Versioning Strategy

Uses setuptools_scm for automatic Python-standard version generation:

#### Main Versions
- Create git tag: `git tag v1.2.3 && git push origin v1.2.3`
- Tagged builds produce clean versions: `1.2.3`
- Used for official releases

#### Other Versions  
- **Test branch**: `1.2.4.branch5+g1a2b3c4` (configured via setuptools_scm)
- Format: `{next_version}.{branch}{commit_count}+g{git_hash}`
- No manual version management required
