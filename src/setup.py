#  Copyright (c) 2022.   Analog Devices Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from setuptools import setup, find_namespace_packages
import os

from garpy.setuptools import read_requires_from_env_yml, read_version

os.chdir(os.path.dirname(__file__) or '.')
src = '.'
name = 'garpy.mkdocstrings'

try:
    requires = read_requires_from_env_yml(os.path.join(src, 'runtime-env.yml'))

    setup(
        name=name,
        version=read_version(os.path.join(src, 'mkdocstrings_handlers', 'garpy_python')),
        packages=find_namespace_packages(src, include=['mkdocstrings_handlers', 'mkdocstrings_handlers.*']),
        package_dir={'':src,},
        package_data={'': ['VERSION','py.typed'],},
        url='https://gitlab.analog.com/boston-garage/garpy.mkdocstrings',
        install_requires=requires.install_requires,
        python_requires=requires.python_requires,
        description='Enhanced mkdocstrings python handler',
        author='Christopher Barber',
        classifiers=[
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10'
        ],
    )
except Exception as ex:
    print(ex)
    raise
