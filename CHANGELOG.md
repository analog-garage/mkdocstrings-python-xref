# mkdocstring-python-xref changes

*Note that versions roughly correspond to the version of mkdocstrings-python that they 
are compatible with.*

## 1.16.2

* Improved source locations for errors in docstrings now including column offset.

## 1.16.1

* Fix sdist distributions (should enable conda-forge to build)

## 1.16.0

* Compatibility with mkdocstrings-python 1.16.*
* Removed some deprecated imports from mkdocstrings

## 1.14.1

* Restrict to mkdocstrings-python <1.16 (see bug #32)

## 1.14.0

* Work with mkdocstrings-python 1.14 or later
* Drop python 3.8 support
* Fix extra files in wheel's RECORD

## 1.6.2

* Use griffe 1.0 or later

## 1.6.1

* Available on conda-forge

## 1.6.0

* Added explicit option to disable cross-reference checking.
* When enabled, check all cross-references, not just relative ones
* If reference begins with '?', don't check cross-reference.

## 1.5.3

First public release

