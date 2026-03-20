test:
# 	poetry run pytest -vv
	poetry run pytest -vv --maxfail=1
# 	poetry run pytest -vv --disable-warnings --maxfail=1 --log-cli-level=DEBUG
#   poetry run pytest --cov=src --cov-report=xml --cov-report=term