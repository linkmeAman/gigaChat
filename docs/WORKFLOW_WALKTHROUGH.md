# Workflow Walkthrough – tests.yml

## What triggers it

- `on: push` to `master` and `aman` branches
- `on: pull_request` to `master` branch

## What it does

1. Checkout code
2. Set up Python (matrix: 3.8, 3.9, 3.10)
3. Install dependencies
4. Run tests with coverage
5. Upload coverage to Codecov
6. Store coverage HTML report as artifact
7. Verify coverage threshold (80%)

## Issues Found

- [ ] No permission specifications (too broad by default)
- [ ] Using floating action versions (@v2, @v3)
- [ ] No dependency caching
- [ ] No concurrency control (wastes resources)
- [ ] No timeout limits
- [ ] No artifact retention policy
- [ ] Python matrix includes older versions (3.8, 3.9)

## Fixed YAML (annotated)

```yaml
# .github/workflows/tests.yml
name: Tests

# Trigger on pushes to main branches and PRs
on:
  push:
    branches: [ master, aman ]
  pull_request:
    branches: [ master ]

# Cancel in-progress runs on new pushes
concurrency:
  group: tests-${{ github.ref }}
  cancel-in-progress: true

# Explicitly set required permissions
permissions:
  contents: read
  checks: write    # Required for test results
  pull-requests: write  # Required for coverage comments

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15  # Prevent hung jobs
    strategy:
      fail-fast: false  # Continue testing other versions if one fails
      matrix:
        python-version: ["3.10", "3.11", "3.12"]  # Updated to modern versions

    steps:
      - name: Checkout
        uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608  # v4.1.0

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@65d7f2d534ac1bc67fcd62888c5f4f3d2cb2b236  # v4.7.1
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip wheel setuptools
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run Tests with Coverage
        env:
          ENV_FILE: .env.test
          DATABASE_URL: sqlite:///./test.db
          PYTHONPATH: .
        run: |
          pytest --cov=app --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@eaaf4bedf32dbdc6b720b63067d99c4d77d6047d  # v3.1.4
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: true
          verbose: true

      - name: Upload Coverage HTML Report
        if: always()  # Upload even if tests fail
        uses: actions/upload-artifact@694cdabd8bdb0f10b2cea11669e1bf5453eed0a6  # v4.0.0
        with:
          name: coverage-report-py${{ matrix.python-version }}
          path: htmlcov/
          retention-days: 7  # Auto-delete after a week

      - name: Check Coverage Threshold
        run: |
          coverage report --fail-under=80
```

## Key Improvements

1. **Security**: Added explicit permissions
2. **Performance**:
   - Added concurrency control
   - Added dependency caching
   - Set job timeout
3. **Reliability**:
   - Pinned action versions to exact commits
   - Updated Python versions to modern ones
   - Added retention policy for artifacts
4. **UX**:
   - Added PYTHONPATH
   - Added version suffix to artifact names
   - Upload coverage even on test failure
