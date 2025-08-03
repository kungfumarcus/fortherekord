set PYTHONPATH=src
python -m pytest tests/ --ignore=tests/e2e/ --cov=src/fortherekord --cov-report=html --cov-report=term-missing -v
start htmlcov\index.html
