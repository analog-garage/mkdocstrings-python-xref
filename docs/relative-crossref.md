## Relative cross-references

By default, [mkdocstrings] only supports cross-references where the path is
fully qualified or is empty, in which case it is taken from the title. 
If you work with long package and class names or with namespace packages, this can result in a lot
of extra typing and harder to read doc-strings.

If you enable the `relative_crossrefs` option in the `garpy_python` handler options
in your mkdocs.yml file ([see configuration](config.md) for an example), then the handler 
will support more compact relative syntax:

=== "Absolute"

    ```python
    class MyClass:
        def this_method(self):
            """
            See [other_function][mypkg.mymod.MyClass.other_function] 
            from [MyClass][mypkg.mymod.Myclass]
            """
    ```

=== "Relative"

    ```python
    class MyClass:
        def this_method(self):
            """
            See [other_function][.] from [MyClass][^]
            """
    ```

The relative path specifier has the following form:

* If the path ends in `.` then the title text will be appended to the path
  (ignoring bold, italic or code markup).

* If the path begins with `.` then it will be expanded relative to the path
    of the doc-string in which it occurs. As a special case, if the current
    doc-string is for a function or method, then `.` will instead be
    expanded relative to the function's parent (i.e. the same as `^.`).

* If the path begins with `(c)`, that will be replaced by the path of the
    class that contains the doc-string

* If the path begins with `(m)`, that will be replaced by the path of the
    module that contains the doc-string

* If the path begins with one or more `^` characters, then that will go
   up one level in the path of the current doc string for each `^`
   
These are demonstrated here:

=== "Relative"

    ```python
    class MyClass:
        def this_method(self):
            """
            [`that_method`][.]
            [init method][(c).__init__]
            [this module][(m)]
            [OtherClass][(m).]
            [some_func][^^.]
            """
    ```

=== "Absolute"

    ```python
    class MyClass:
        def this_method(self):
            """
            [`that_method`][mypkg.mymod.MyClass.that_method]
            [init method][mypkg.mymod.MyClass.__init__]
            [this module][mypkg.mymod]
            [OtherClass][mypkg.mymod.OtherClass]
            [some_func][mypkg.mymod.some_func]
            [
            
            """
    ```

This has been [proposed as a feature in the standard python handler][relative-crossref-issue]
but has not yet been accepted.

[mkdocstrings]: https://mkdocstrings.github.io/
[mkdocstrings_python]: https://mkdocstrings.github.io/python/
[relative-crossref-issue]: https://github.com/mkdocstrings/python/issues/27

