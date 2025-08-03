@echo off
echo Running unit tests only (excluding E2E tests)...
python -m pytest tests/ -v --ignore=tests/e2e/
echo.
echo Unit tests completed.
echo.
echo To run E2E tests separately, use: tests\e2e\test_e2e.bat
