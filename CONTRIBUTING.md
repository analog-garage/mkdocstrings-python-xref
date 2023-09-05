# Contributing to mkdocstrings-python-xref

## Prerequisites

* conda must be installed on your machine
* make should be installed in your base conda environment

## Development install

To (re)create a conda development environment for this project run:

```
make createdev
conda activate mkxref-dev
```

After you have created the environment for the first time, you can configure your IDE
to use that for this project.

To update the environment after pulling or modifying project dependencies, you can use

```
make updatedev
```

This is just an optimization. If it does not work (e.g. can happen when switching to an old branch), just use `createdev`.

## Versioning

The versions will generally track the version of [mkdocstrings_python][] on which it depends.

[mkdocstrings_python]: https://github.com/mkdocstrings/python


