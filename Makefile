CONDA := conda
GARCONDA := garconda --min-version 0.3.4
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
SRC := src

PACKAGE := garpy.mkdocstrings
PACKAGE_VERSION_PATH := $(SRC)/mkdocstrings_handlers/garpy_python/VERSION
PACKAGE_COMMAND := $(CAT) $(PACKAGE_VERSION_PATH)
PACKAGE_VER := $(shell $(PACKAGE_COMMAND))

SRC_FILES := $(wildcard src/mkdocstrings_handlers/garpy_python/*.py) $(PYTHON_VERSION_PATH)

USE_TEST_CHANNEL :=
ifeq ($(USE_TEST_CHANNEL),)
	UPLOAD_TEST :=
	UPLOAD_OVERWRITE :=
else
	UPLOAD_TEST :=-test
	UPLOAD_OVERWRITE :=--overwrite
endif
CONDA_UPLOAD_CHANNEL := garage-conda-local$(UPLOAD_TEST)
PYPI_UPLOAD_CHANNEL := adi-pypi-local$(UPLOAD_TEST)

# Env names
DEV_ENV := garpy.mkdocstrings

# Creation args
CREATE_DEV_ARGS := --file runtime-env.yml --file test-env.yml --file doc-env.yml
GARCONDA_CREATE_ARGS := $(CREATE_DEV_ARGS)
DEV_CREATE := $(GARCONDA) create-dev -n $(DEV_ENV) $(GARCONDA_CREATE_ARGS) --python-version 3.8
CI_CREATE := $(DEV_CREATE)

# Verify upload args
VERIFY_UPLOAD := $(GARCONDA) verify-upload --expect-version $(PACKAGE_VER) --request-version $(PACKAGE_VER) $(PACKAGE)
VERIFY_UPLOAD_CONDA := $(VERIFY_UPLOAD) --conda-channel $(CONDA_UPLOAD_CHANNEL)
VERIFY_UPLOAD_WHEEL := $(VERIFY_UPLOAD) --pypi-channel $(PYPI_UPLOAD_CHANNEL)

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
	@$(ECHO) "create-ci-env   - Create CI conda environment named $(DEV_ENV)."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- test ---$(COLORLESS)"
	@$(ECHO) "pytest          - Run pytest in '$(DEV_ENV)' environment."
	@$(ECHO) "test            - Run tests and linting in '$(DEV_ENV)' environment."
#	@$(ECHO) "test-all        - Run all tests against all supported environments"
#	@$(ECHO) "                  and linting {% if cookiecutter.pre_commit == "yes" -%} and pre-commit {%- endif %} in '$(DEV_ENV)' environment."
	@$(ECHO) "coverage-test   - Runs pytest instrumented for coverage and generates html report"
	@$(ECHO) "coverage-show   - Open html coverage report in a web browser."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- lint ---$(COLORLESS)"
	@$(ECHO) "lint            - Run linting commands in '$(DEV_ENV)' environment."
	@$(ECHO) "pylint          - Run pylint in '$(DEV_ENV)' environment."
	@$(ECHO) "mypy            - Run mypy in '$(DEV_ENV)' environment."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- build ---$(COLORLESS)"
	@$(ECHO) "build           - Build wheel and conda package."
	@$(ECHO) "build-wheel     - Build wheel."
	@$(ECHO) "build-conda     - Build conda package."
	@$(ECHO)
	@$(ECHO) "$(SECTION_COLOR)--- upload ---$(COLORLESS)"
	@$(ECHO) "upload          - Upload conda package and wheel to artifactory"
	@$(ECHO) "                  Run 'make upload USE_TEST_CHANNEL=1' to upload to test channel."
	@$(ECHO) "upload-wheel    - Upload wheel to artifactory channel $(PYPI_UPLOAD_CHANNEL)"
	@$(ECHO) "upload-conda    - Upload conda package to artifactory channel $(CONDA_UPLOAD_CHANNEL)"
	@$(ECHO) "verify-upload   - Install uploaded package into test environment and verify it can be imported."
	@$(ECHO) "                  Run 'verify-upload USE_TEST_CHANNEL=1' to verify upload from test channel."
	@$(ECHO) "verify-upload-wheel - Verify upload of only wheel."
	@$(ECHO) "verify-upload-conda - Verify upload of only conda package."
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

create-dev:
	$(DEV_CREATE)

createdev: create-dev

update-dev:
	$(DEV_CREATE) --update

updatedev: update-dev

create-ci-env:
	$(CI_CREATE)

clean-dev:
	-$(CONDA) env remove -n $(DEV_ENV)

pytest:
	$(CONDA_RUN) pytest -sv -ra $(PYTEST_ARGS) tests

test: lint pytest

# We generate the tox dependency files from the official versions.
tox-env.yml: runtime-env.yml test-env.yml
	$(GARCONDA) env merge --out $@ $^

tox-requirements.txt: runtime-env.yml test-env.yml
	$(GARCONDA) env merge --for-pip --out $@ $^

tox-dependencies: tox-env.yml tox-requirements.txt

tox: tox-dependencies
	$(CONDA_RUN) tox $(TOX_ARGS)

test-all:  test tox

.coverage:
	@$(CONDA_RUN) pytest -ra $(PYTEST_ARGS) --cov --cov-report=html --cov-report=term -- tests

coverage-test:
	@$(MAKE) -B .coverage

coverage-show:
	@$(CONDA_RUN) python -m webbrowser file://$(COVERAGE_HTML)/index.html

pylint:
	$(CONDA_RUN) pylint src/mkdocstrings_handlers/* tests/* $(PYLINT_ARGS)

mypy:
	$(CONDA_RUN) mypy $(MYPY_ARGS)

lint: pylint mypy

build-wheel:
	$(CONDA_RUN) pip wheel . --no-deps --no-build-isolation -w dist

conda-meta-data.json: runtime-env.yml pyproject.toml
	$(CONDA_RUN) hatchling-garconda metadata --overwrite --out $@

build-conda: conda-meta-data.json
	$(GARCONDA) build $(abspath .)

build-conda-no-test: conda-meta-data.json
	$(GARCONDA) build $(abspath .) --no-test

build: build-wheel build-conda

upload-wheel:
	$(GARCONDA) upload-pypi -u $(USERNAME) dist/* -c $(PYPI_UPLOAD_CHANNEL)

upload-conda:
	$(GARCONDA) upload '$(PACKAGE)-$(PACKAGE_VER)-*' -u $(USERNAME) -y -c $(CONDA_UPLOAD_CHANNEL) $(UPLOAD_OVERWRITE)

upload: upload-wheel upload-conda

verify-upload-wheel:
	$(CONDA_RUN) $(VERIFY_UPLOAD_WHEEL)

verify-upload-conda:
	$(CONDA_RUN) $(VERIFY_UPLOAD_CONDA)

verify-upload: verify-upload-wheel verify-upload-conda

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
