CONDA := conda
ECHO := echo
RM := rm
RMDIR := $(RM) -rf
CAT := cat
TOUCH := touch

# OS specific values
ifndef OS
	# maxOs or linux
	USERNAME := $(shell whoami)
else
	# windows
endif

COVERAGE_HTML := $(abspath htmlcov)

# If you want to override default variables in your own source tree,
# define a custom.mk file, for instance to use the name 'garconf-dev' for
# the conda development environment, you could use the entry:
#
#     override DEV_ENV := garconf-dev
-include custom.mk

# General env/build/deploy args
PACKAGE := mkdocstrings-python-xref
PACKAGE_VERSION_PATH := src/mkdocstrings_handlers/python_xref/VERSION
VERSION := $(strip $(file < $(PACKAGE_VERSION_PATH)))

SRC_FILES := $(wildcard src/mkdocstrings_handlers/garpy_python/*.py) $(PYTHON_VERSION_PATH)

# Env names
DEV_ENV := mkxref-dev

# Whether to run targets in current env or explicitly in $(DEV_ENV)
CURR_ENV_BASENAME := $(shell basename $(CONDA_PREFIX))
ifeq ($(CURR_ENV_BASENAME), $(DEV_ENV))
	CONDA_RUN :=
else
	CONDA_RUN := conda run -n $(DEV_ENV) --no-capture-output
endif

# Testing args
PYTEST_ARGS :=
TOX_ARGS :=
PYLINT_ARGS :=
MYPY_ARGS :=

DOC_DIR := docs
MKDOC_CONFIG := mkdocs.yml
MKDOC_FILES := $(MKDOC_CONFIG) $(wildcard $(DOC_DIR)/user/*.md)

# 'make help' colors
TOP_COLOR :=\033[0;34m
SECTION_COLOR :=\033[0;32m
COLORLESS :=\033[0m

help:
	@$(ECHO)
	@$(ECHO) "$(TOP_COLOR)=== Make targets ===$(COLORLESS)"
	@$(ECHO) "$(SECTION_COLOR)--- conda environment ---$(COLORLESS)"
	@$(ECHO) "create-dev      - Create conda development environment named '$(DEV_ENV)'."
	@$(ECHO) "update-dev      - Update conda development environment '$(DEV_ENV)'."
	@$(ECHO) "clean-dev       - Remove $(DEV_ENV) conda environment"
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- test ---$(COLORLESS)"
	@$(ECHO) "pytest          - Run pytest in '$(DEV_ENV)' environment."
	@$(ECHO) "test            - Run tests and linting in '$(DEV_ENV)' environment."
	@$(ECHO) "coverage-test   - Runs pytest instrumented for coverage and generates html report"
	@$(ECHO) "coverage-show   - Open html coverage report in a web browser."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- lint ---$(COLORLESS)"
	@$(ECHO) "lint            - Run linting commands in '$(DEV_ENV)' environment."
	@$(ECHO) "pylint          - Run pylint in '$(DEV_ENV)' environment."
	@$(ECHO) "mypy            - Run mypy in '$(DEV_ENV)' environment."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- build ---$(COLORLESS)"
	@$(ECHO) "build           - Build wheel"
	@$(ECHO) "build-wheel     - Build wheel."
	@$(ECHO) "build-conda     - Build conda package (requires whl2conda)"
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- upload ---$(COLORLESS)"
	@$(ECHO) "upload          - Upload wheel to pypi (requires authorization)"
	@$(ECHO) "check-upload    - Verify file for upload"
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- documentation ---$(COLORLESS)"
	@$(ECHO) "doc             - Build HTML documentation in site/ directory."
	@$(ECHO) "doc-strict      - Build documentation but fail if any warnings"
	@$(ECHO) "showdoc         - Show HTML documentation using local HTML server."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- cleanup ---$(COLORLESS)"
	@$(ECHO) "clean           - Remove generated files."
	@$(ECHO) "clean-test      - Remove generated test files including tox environments."
	@$(ECHO) "clean-doc       - Remove generated documentation files."
	@$(ECHO)
	@$(ECHO) "$(TOP_COLOR)====================$(COLORLESS)"
	@$(ECHO)

dev-install:
	$(CONDA_RUN) pip install -e . --no-deps --no-build-isolation

create-dev:
	$(CONDA) env create -f environment.yml --yes
	$(MAKE) dev-install

createdev: create-dev

update-dev:
	$(CONDA) env update -f environment.yml
	$(MAKE) dev-install

updatedev: update-dev

create-ci-env: create-dev

clean-dev:
	-$(CONDA) env remove -n $(DEV_ENV)

pytest:
	$(CONDA_RUN) pytest -sv -ra $(PYTEST_ARGS) tests

test: lint pytest

test-all:  test tox

.coverage:
	@$(CONDA_RUN) pytest -ra $(PYTEST_ARGS) --cov --cov-report=html --cov-report=term -- tests

coverage-test:
	@$(MAKE) -B .coverage

coverage: coverage-test

coverage-show:
	@$(CONDA_RUN) python -m webbrowser file://$(COVERAGE_HTML)/index.html

pylint:
	$(CONDA_RUN) pylint src/mkdocstrings_handlers tests $(PYLINT_ARGS)

mypy:
	$(CONDA_RUN) mypy $(MYPY_ARGS)

lint: pylint mypy

WHEEL_FILE := dist/$(subst -,_,$(PACKAGE))-$(VERSION)-py3-none-any.whl
CONDA_FILE := dist/$(PACKAGE)-$(VERSION)-py_0.conda

$(WHEEL_FILE):
	$(CONDA_RUN) pip wheel . --no-deps --no-build-isolation -w dist

build-wheel: $(WHEEL_FILE)

$(CONDA_FILE): $(WHEEL_FILE)
	$(CONDA_RUN) whl2conda build $(WHEEL_FILE)

build-conda: $(CONDA_FILE)

build: build-wheel

site/index.html: $(MKDOC_FILES) $(SRC_FILES)
	$(CONDA_RUN) mkdocs build -f $(MKDOC_CONFIG)

site/.doc-strict: $(MKDOC_FILES) $(SRC_FILES)
	$(CONDA_RUN) mkdocs build -f $(MKDOC_CONFIG) --strict
	$(CONDA_RUN) linkchecker -f linkcheckerrc.ini site
	$(TOUCH) site/.doc-strict

doc: site/index.html

docs: doc

doc-strict: site/.doc-strict

showdoc: site/index.html
	$(CONDA_RUN) mkdocs serve -f $(MKDOC_CONFIG)

showdocs: showdoc

doc-deploy:
	$(CONDA_RUN) mike deploy -F $(MKDOC_CONFIG) -u $(VERSION) latest
	$(CONDA_RUN) mike set-default -F $(MKDOC_CONFIG) latest

mike-deploy: doc-deploy
mike-build: doc-deploy

doc-push:
	git push origin gh-pages

doc-upload: doc-push

doc-serve-all:
	$(CONDA_RUN) mike serve -F $(MKDOC_CONFIG)

mike-serve: doc-serve-all

check-upload:
	$(CONDA_RUN) twine check $(WHEEL_FILE)

upload: check-upload
	# NOTE: --skip-existing doesn't seem to actually work
	$(CONDA_RUN) twine upload --skip-existing $(WHEEL_FILE)

anaconda-upload: $(CONDA_FILE)
	# you will need to log in first
	anaconda upload --user garpy $(CONDA_FILE)

clean-build:
	-@$(RMDIR) build
	-@$(RMDIR) dist

clean-doc:
	-@$(RMDIR) site

clean-tox:
	-@$(RMDIR) .tox
	-@$(RM) tox-env.yml tox-requirements.txt

clean-test: clean-coverage clean-tox
	-@$(RMDIR) .pytest_cache
	-@$(RMDIR) .mypy_cache

clean-coverage:
	-@$(RMDIR) $(COVERAGE_HTML) .coverage .coverage.*

clean-python:
	-@python -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	-@python -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"

clean: clean-doc clean-python clean-test clean-build
