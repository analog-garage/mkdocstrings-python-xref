### Using conda

```
conda install \
   -c conda-forge \
   -c https://artifactory.analog.com/artifactory/garage-conda-local \
   garpy.mkdocstrings
```

Or if you have configured the garage-conda-local custom channel:

```
conda install -c conda-forge -c garage-conda-local garpy.config
```

or include entry in the appropriate conda environment YAML file for your project.

### Using pip

```
pip install \
   --extra-index-url https://artifactory.analog.com/artifactory/adi-pypi-local \
   garpy.mkdocstrings
```

or include entry in the appropriate pip requirements.txt file for your project.


