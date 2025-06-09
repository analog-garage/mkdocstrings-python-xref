Configuration is the same as with [mkdocstrings-python][] except
that the handler name should be `python_xref` instead of `python`. Because
this handler extends the standard [mkdocstrings-python][] handler, the same options are
available.

Additional options are added by this extension. Currently, there are three:

* **relative_crossrefs**: `bool` - if set to true enables use of relative path syntax in
    cross-references.
    
* **check_crossrefs**: `bool` - enables early checking of all cross-references. Note that
    this option only takes affect if **relative_crossrefs** is also true. This option is
    true by default, so this option is used to disable checking. Checking can
    also be disabled on a per-case basis by prefixing the reference with '?', e.g.
    `[something][?dontcheckme]`.

* **check_crossrefs_exclude**: `list[str]` - exclude cross-references matching any of these
    regex patterns from crossref checking. This option can be used disabling checking on
    libraries which are very expensive to import without having to disable checking for all
    cross-references.

!!! Example "mkdocs.yml plugins specifications using this handler"

    === "Always check"

        !!! warning

            Crossrefs to libraries which are expensive to import (e.g., machine learning
            frameworks) can cause very slow build times when checked!

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                import:
                - https://docs.python.org/3/objects.inv
                - https://pytorch.org/docs/stable/objects.inv
                options:
                  relative_crossrefs: yes
        ```

    === "Check all but listed exclusions"

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                import:
                - https://docs.python.org/3/objects.inv
                - https://pytorch.org/docs/stable/objects.inv
                options:
                  relative_crossrefs: yes
                  check_crossrefs_exclude:
                  - "^torch\\.(.*)"
        ```

    === "Never check"

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                import:
                - https://docs.python.org/3/objects.inv
                - https://pytorch.org/docs/stable/objects.inv
                options:
                  relative_crossrefs: yes
                  check_crossrefs: no
        ```



[mkdocstrings-python]: https://mkdocstrings.github.io/python/
