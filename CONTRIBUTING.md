# Contributing to mkdocstrings-python-xref

This project's environment and developemtn tasks are managed using [pixi] 
(previously it used conda and make). 

## Prerequisites

* [install pixi][pixi-install]

## Development setup

To (re)create a pixi development environment for this project, from inside
the source tree run:

```
pixi reinstall
```

This is actually optional, since pixi will automatically install the
environment the first time you run a command. 

See `pixi task list` for a list of available tasks.

## Versioning

The versions will generally track the version of [mkdocstrings_python][] on which it depends.

[mkdocstrings_python]: https://github.com/mkdocstrings/python


[pixi]: https://pixi.sh/latest/
[pixi-install]: https://pixi.sh/latest/installation/
