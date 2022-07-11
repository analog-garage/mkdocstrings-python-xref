Configuration is the same as with [mkdocstrings-python][] except
that the handler name should be `garpy_python` instead of `python`. Because
this handler extends the standard [mkdocstrings-python][] handler, the same options are
available.

Additional options are added by this extension. Currently, there is only one:

* **relative_crossrefs** - if set to true enables use of relative path syntax in
    cross-references.

!!! Example "mkdocs.yml plugins specification using this handler"

```yaml
plugins:
- search
- mkdocstrings:
    default_handler: garpy_python
    handlers:
      garpy_python:
        import:
        - https://docs.python.org/3/objects.inv
        options:
          docstring_style: google
          docstring_options:
            ignore_init_summary: yes
          merge_init_into_class: yes
          relative_crossrefs: yes
          separate_signature: yes
          show_source: no
          show_root_full_path: no
```

[mkdocstrings-python]: https://mkdocstrings.github.io/python/
