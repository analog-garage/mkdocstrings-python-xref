Configuration is the same as with [mkdocstrings-python][] except
that the handler name should be `python_xref` instead of `python`. Because
this handler extends the standard [mkdocstrings-python][] handler, the same options are
available.

Additional options are added by this extension:

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

* **compatibility_check**: `false`, `"warn"`, or `"error"` - when set, reports cross-references
    that use syntax not supported by the standard [mkdocstrings-python][] handler. This is
    useful when planning to migrate away from this extension. The incompatible syntax elements
    are: leading `^`, `(c)`, `(m)`, `(p)` specifiers; trailing `.` after a name (which
    appends the title); and leading `?` (which suppresses reference checking).

* **compatibility_patch**: `false` or a file path string - when set to a file path, generates
    a unified diff patch file that converts incompatible cross-references to the standard
    dot-prefix form. The patch file is overwritten on each build. If no incompatibilities are
    found, any existing patch file is removed. The generated patch can be applied with
    `git apply` or `patch -p1`.

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
                inventories:
                - url: https://docs.python.org/3/objects.inv
                  domains: [std, py]
                - url: https://pytorch.org/docs/stable/objects.inv
                  domains: [py]
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
                inventories:
                - url: https://docs.python.org/3/objects.inv
                  domains: [std, py]
                - url: https://pytorch.org/docs/stable/objects.inv
                  domains: [py]
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
                inventories:
                - url: https://docs.python.org/3/objects.inv
                  domains: [std, py]
                - url: https://pytorch.org/docs/stable/objects.inv
                  domains: [py]
                options:
                  relative_crossrefs: yes
                  check_crossrefs: no
        ```

!!! Example "Compatibility checking for migration"

    To check for incompatible syntax before migrating to the standard handler:

    === "Warn on incompatibilities"

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                options:
                  relative_crossrefs: yes
                  compatibility_check: warn
        ```

    === "Error on incompatibilities"

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                options:
                  relative_crossrefs: yes
                  compatibility_check: error
        ```

    === "Generate a patch file"

        ```yaml
        plugins:
        - mkdocstrings:
            default_handler: python_xref
            handlers:
              python_xref:
                options:
                  relative_crossrefs: yes
                  compatibility_check: warn
                  compatibility_patch: xref-compat.patch
        ```

        Then apply the patch:

        ```bash
        git apply xref-compat.patch
        ```



[mkdocstrings-python]: https://mkdocstrings.github.io/python/
