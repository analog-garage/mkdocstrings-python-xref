Configuration is the same as with [mkdocstrings-python][] except
that the handler name should be `python_xref` instead of `python`. Because
this handler extends the standard [mkdocstrings-python][] handler, the same options are
available.

Additional options are added by this extension. Currently, there are two:

* **relative_crossrefs** - if set to true enables use of relative path syntax in
    cross-references.
    
* **check_crossrefs** - enables early checking of all cross-references. Note that
    this option only takes affect if **relative_crossrefs** is also true. This option is
    true by default, so this option is used to disable checking. Checking can
    also be disabled on a per-case basis by prefixing the reference with '?', e.g.
    `[something][?dontcheckme]`.

!!! Example "mkdocs.yml plugins specification using this handler"

```yaml
plugins:
- search
- mkdocstrings:
    default_handler: python_xref
    handlers:
      python_xref:
        import:
        - https://docs.python.org/3/objects.inv
        options:
          docstring_style: google
          docstring_options:
            ignore_init_summary: yes
          merge_init_into_class: yes
          relative_crossrefs: yes
          check_crossrefs: no
          separate_signature: yes
          show_source: no
          show_root_full_path: no
```

[mkdocstrings-python]: https://mkdocstrings.github.io/python/
