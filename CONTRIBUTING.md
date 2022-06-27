# Contributing to garpy.mkdocstrings

## Prerequisites

* conda must be installed on your machine
* make must be installed in your base conda environment
* [garconda][] must be installed in your base conda environment

## Development install

To (re)create a conda development environment for this project run:

```
make createdev
conda activate garconfig-dev
```

After you have created the environment for the first time, you can configure your IDE
to use that for this project.

To update the environment after pulling or modifying project dependencies, you can use

```
make updatedev
```

This is just an optimization. If it does not work (e.g. can happen when switching to an old branch), just use `createdev`.

## Versioning and Release process

This project follows the [basic garpy.* versioning and release process](https://gitlab.analog.com/boston-garage/garpy/-/blob/master/developer-docs/basic-release-process.md).

At least initially, the versions will track the version of [mkdocstrings_python][] on which it depends.

[garconda]: http://boston-garage.pages.gitlab.analog.com/garconda/
[mkdocstrings_python]: https://github.com/mkdocstrings/python


