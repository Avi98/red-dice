PY_VERSION = 3.12

clean_venv:
	@echo "cleaning up"
	rm -rf .venv

install_python:
	@echo "Installing python version $(PY_VERSION)"
	uv  python install $(PY_VERSION)

pin_python:
	@echo "Pinning python version"
	uv python pin $(PY_VERSION)

install:
	@echo "Installing python decencies"
	uv venv && uv sync --all-groups

local_startup:
	@echo "Setup local env"
	$(MAKE) clean_venv
	$(MAKE) install_python
	$(MAKE) pin_python
	$(MAKE) install

test:
	pytest --cov just_one_sql