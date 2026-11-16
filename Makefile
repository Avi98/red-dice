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
	uv env && uv sync --all-groups

local_startup:
	@echo "Setup local env"
	clean_venv install_python pin_python install

