# mkdocstrings-python-xref

Python handler for [mkdocstrings] supporting relative cross-references.

[![pypi version](https://img.shields.io/pypi/v/mkdocstrings-python-xref.svg)](https://pypi.org/project/mkdocstrings-python-xref/)
[![conda version](https://img.shields.io/conda/vn/conda-forge/mkdocstrings-python-xref)](https://anaconda.org/conda-forge/whl2conda)
[![documentation](https://img.shields.io/badge/docs-mkdocs%20material-blue.svg?style=flat)](https://analog-garage.github.io/mkdocstrings-python-xref/)  
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mkdocstrings-python-xref)
![GitHub](https://img.shields.io/github/license/analog-garage/mkdocstrings-python-xref)  
[![CI](https://github.com/analog-garage/mkdocstrings-python-xref/actions/workflows/main.yml/badge.svg)](https://github.com/analog-garage/mkdocstrings-python-xref/actions/workflows/main.yml)
![GitHub issues](https://img.shields.io/github/issues/analog-garage/mkdocstrings-python-xref)

[mkdocstrings] is an awesome plugin for [MkDocs] that can generate Markdown API documentation
from comments in code. The standard [python handler][mkdocstrings-python] allows you to
create cross-reference links using the syntax `[<title>][<path>]` where the path must
either be the fully qualified name of the referent or is empty, in which case the path
is taken from the title. This works well when the names are short, but can be burdensome
in larger codebases with deeply nested package structures.

This package extends [mkdocstrings-python] to support a relative cross-reference syntax,
that allows you to write doc-strings with cross-references like:

```python
class MyClass:
    def this_method(self):
        """
        See [other_method][..] from [MyClass][(c)]
        """
```
rather than:

```python
class MyClass:
    def this_method(self):
        """
        See [other_method][mypkg.mymod.MyClass.other_method] 
        from [MyClass][mypkg.mymod.Myclass]
        """
```

Another benefit of this extension is that it will report source locations for bad references
so that errors are easier to find and fix. For example:

```bash
$ mkdocs build
INFO    -  Cleaning site directory
INFO    -  Building documentation to directory: /home/jdoe/my-project/site
WARNING -  mkdocstrings_handlers: file:///home/jdoe/my-project/src/myproj/bar.py:16:
           Cannot load reference 'myproj.bar.bad'
```

For further details, please see the [Documentation](https://analog-garage.github.io/mkdocstrings-python-xref/)

[MkDocs]: https://mkdocs.readthedocs.io/
[mkdocstrings]: https://github.com/mkdocstrings/mkdocstrings
[mkdocstrings-python]: https://github.com/mkdocstrings/python
