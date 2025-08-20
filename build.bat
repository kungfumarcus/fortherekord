@echo off
python -m black --line-length 100 src/ tests/ && python -m flake8 src/ tests/ && python -m pylint src/fortherekord && python -m mypy src/fortherekord
