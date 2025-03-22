#  Copyright (c) 2022-2025.   Analog Devices Inc.
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
"""Unit test for mkdocstrings_handlers.python_xref.handler module"""

from __future__ import annotations

import logging
import os
from os import PathLike
from pathlib import Path
from typing import Any

import pytest

from griffe import Docstring, Object, Module
from mkdocstrings import CollectionError
from mkdocstrings_handlers.python import PythonConfig
from mkdocstrings_handlers.python import PythonHandler
from mkdocstrings_handlers.python_xref.handler import (
    PythonRelXRefHandler,
    PythonRelXRefOptions
)

def test_handler(tmpdir: PathLike,
                 monkeypatch: pytest.MonkeyPatch,
                 caplog: pytest.LogCaptureFixture) -> None:
    """Unit test for PythonRelXRefHandler class

    This is a minimal whitebox test that just checks whether PythonHandler class has been
    overridden correctly. A separate test should do doc generation and check the results.
    """

    os.mkdir(os.path.join(tmpdir, 'path1'))
    os.mkdir(os.path.join(tmpdir, 'path2'))
    os.makedirs(os.path.join(tmpdir, 'custom_templates', 'python'))

    #
    # Test construction
    #

    config = PythonConfig(  # type: ignore[call-arg]
        paths = ['path1', 'path2'],
    )

    handler = PythonRelXRefHandler(
        config,
        Path(tmpdir),
        theme = 'material',
        custom_templates = 'custom_templates',
    )
    assert handler.name == 'python_xref'

    # NOTE: these could break if PythonHandler changes
    # pylint: disable=protected-access
    assert handler.name == 'python_xref'
    # assert handler._config_file_path == config_file
    assert os.path.join(tmpdir, 'path1') in handler._paths
    assert os.path.join(tmpdir, 'path2') in handler._paths

    #
    # Test get_templates_dir() redirection
    #

    assert handler.get_templates_dir(handler.name) == handler.get_templates_dir('python')

    #
    # Test render()
    #

    def fake_collect(_self: PythonHandler, identifier: str, _config: dict) -> Any:
        if identifier.startswith('mod'):
            return Object(identifier)
        raise CollectionError(identifier)

    def fake_render(_self: PythonHandler, data: Object, _config: dict) -> str:
        assert data.docstring is not None
        return data.docstring.value

    # Monkeypatch render/collect methods on parent class
    monkeypatch.setattr(PythonHandler, 'collect', fake_collect)
    monkeypatch.setattr(PythonHandler, 'render', fake_render)

    obj = Module(name='mod', filepath= Path('mod.py'))
    docstring = "[foo][.] [bar][bad.]"
    obj.docstring = Docstring(docstring, parent=obj)

    rendered = handler.render(obj, PythonRelXRefOptions())
    assert rendered == docstring

    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=False), # type: ignore[call-arg]
    )
    assert rendered == docstring

    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=True), # type: ignore[call-arg]
    )
    assert rendered == "[foo][mod.foo] [bar][bad.bar]"
    assert len(caplog.records) == 1
    _, level, msg = caplog.record_tuples[0]
    assert level == logging.WARNING
    assert "Cannot load reference 'bad.bar'" in msg
    caplog.clear()

    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=True, check_crossrefs=False), # type: ignore[call-arg]
    )
    assert rendered == "[foo][mod.foo] [bar][bad.bar]"
    assert len(caplog.records) == 0

    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=True, check_crossrefs=False), # type: ignore[call-arg]
    )
    assert rendered == "[foo][mod.foo] [bar][bad.bar]"
    assert len(caplog.records) == 0

    docstring = "\n\n[foo][bad.foo]"
    obj.docstring = Docstring(docstring, parent=obj)
    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=True), # type: ignore[call-arg]
    )
    assert rendered == "[foo][bad.foo]"
    assert len(caplog.records) == 1
    _, level, msg = caplog.record_tuples[0]
    assert level == logging.WARNING
    assert "Cannot load reference 'bad.foo'" in msg
    caplog.clear()

    docstring = "[foo][?bad.foo] [bar][?bad.]"
    obj.docstring = Docstring(docstring, parent=obj)
    rendered = handler.render(
        obj,
        PythonRelXRefOptions(relative_crossrefs=True, check_crossrefs=True), # type: ignore[call-arg]
    )
    assert rendered == "[foo][bad.foo] [bar][bad.bar]"
    assert len(caplog.records) == 0
