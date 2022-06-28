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
"""Unit test for mkdocstrings_handlers.garpy_python.handler module"""

from __future__ import annotations

import logging
import os
from os import PathLike
from pathlib import Path
from typing import Any

import pytest

from griffe.dataclasses import Docstring, Object, Module
from mkdocstrings.handlers.base import CollectionError
from mkdocstrings_handlers.python.handler import PythonHandler

from mkdocstrings_handlers.garpy_python.handler import GarpyPythonHandler

def test_handler(tmpdir: PathLike,
                 monkeypatch: pytest.MonkeyPatch,
                 caplog: pytest.LogCaptureFixture) -> None:
    """Unit test for GarpyPythonHandler class

    This is a minimal whitebox test that just checks whether PythonHandler class has been
    overridden correctly. A separate test should do doc generation and check the results.
    """

    config_file = os.path.join(tmpdir, 'mkdocs.yml')

    #
    # Test construction
    #

    handler = GarpyPythonHandler(
        'material',
        config_file_path = config_file,
        custom_templates = 'custom_templates',
        paths = ['path1', 'path2']
    )
    assert handler.handler_name == 'garpy_python'

    # NOTE: these could break if PythonHandler changes
    # pylint: disable=protected-access
    assert handler._handler == 'garpy_python'
    assert handler._theme == 'material'
    assert handler._config_file_path == config_file
    assert handler._custom_templates == 'custom_templates'
    assert os.path.join(tmpdir, 'path1') in handler._paths
    assert os.path.join(tmpdir, 'path2') in handler._paths

    #
    # Test get_templates_dir() redirection
    #

    assert handler.get_templates_dir(handler.handler_name) == handler.get_templates_dir('python')

    #
    # Test render()
    #

    def fake_collect(_self: PythonHandler, identifier: str, _config: dict) -> Any:
        if identifier.startswith('mod'):
            return Object(identifier)
        else:
            raise CollectionError(identifier)

    def fake_render(_self: PythonHandler, data: Object, _config: dict) -> str:
        assert data.docstring is not None
        return data.docstring.value

    monkeypatch.setattr(PythonHandler, 'collect', fake_collect)
    monkeypatch.setattr(PythonHandler, 'render', fake_render)

    obj = Module(name='mod', filepath= Path('mod.py'))
    docstring = "[foo][.] [bar][bad.]"
    obj.docstring = Docstring(docstring, parent=obj)

    rendered = handler.render(obj, {})
    assert rendered == docstring

    rendered = handler.render(obj, dict(relative_crossrefs=False))
    assert rendered == docstring

    rendered = handler.render(obj, dict(relative_crossrefs=True))
    assert rendered == "[foo][mod.foo] [bar][bad.bar]"

    assert len(caplog.records) == 1
    _, level, msg = caplog.record_tuples[0]
    assert level == logging.WARNING
    assert 'Cannot load reference' in msg

