PYTHON ?= python3

.PHONY: test build release release-patch release-minor release-major

test:
	uv run pytest -q

build:
	uv build

release:
ifndef VERSION
	$(error VERSION is required, e.g. make release VERSION=0.2.1)
endif
	$(PYTHON) -m tools.release --version $(VERSION)

release-patch:
	$(PYTHON) -m tools.release --bump patch

release-minor:
	$(PYTHON) -m tools.release --bump minor

release-major:
	$(PYTHON) -m tools.release --bump major
