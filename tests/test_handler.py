#  Copyright (c) 2022-2026.   Analog Devices Inc.
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
import griffe
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
        mdx = [],
        mdx_config= {},
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

    def fake_render(_self: PythonHandler, data: Object, _config: dict, locale: str|None = None) -> str:
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

    #
    # Test compatibility_check option
    #

    mod_parent = Module(name='pkg', filepath=Path('pkg.py'))
    mod_child = Module(name='mod', filepath=Path('mod.py'), parent=mod_parent)
    mod_parent.members['mod'] = mod_child
    cls_test = griffe.Class(name='Cls', parent=mod_child)
    mod_child.members['Cls'] = cls_test
    meth_test = griffe.Function(name='meth', parent=cls_test)
    cls_test.members['meth'] = meth_test

    docstring = "[foo][(c).] [bar][..bar]"
    meth_test.docstring = Docstring(docstring, parent=meth_test)
    caplog.clear()
    rendered = handler.render(
        meth_test,
        PythonRelXRefOptions(
            relative_crossrefs=True,
            check_crossrefs=False,
            compatibility_check="warn",
        ), # type: ignore[call-arg]
    )
    # (c). is incompatible, ..bar is standard
    compat_warnings = [r for r in caplog.records if "Incompatible" in r.message]
    assert len(compat_warnings) == 1
    assert compat_warnings[0].levelno == logging.WARNING
    assert "(c)" in compat_warnings[0].message
    caplog.clear()

    # Test error level
    meth_test.docstring = Docstring("[foo][(c).]", parent=meth_test)
    rendered = handler.render(
        meth_test,
        PythonRelXRefOptions(
            relative_crossrefs=True,
            check_crossrefs=False,
            compatibility_check="error",
        ), # type: ignore[call-arg]
    )
    compat_errors = [r for r in caplog.records if "Incompatible" in r.message]
    assert len(compat_errors) == 1
    assert compat_errors[0].levelno == logging.ERROR
    caplog.clear()

    #
    # Test compatibility_patch option
    #

    patch_file = os.path.join(tmpdir, "compat.patch")
    config2 = PythonConfig(  # type: ignore[call-arg]
        paths=['path1'],
        options={'compatibility_patch': patch_file},
    )
    handler2 = PythonRelXRefHandler(
        config2,
        Path(tmpdir),
        theme='material',
        custom_templates='custom_templates',
        mdx=[],
        mdx_config={},
    )

    mod_src_path = Path(tmpdir) / 'mod2.py'
    mod_source = 'class C:\n    def m(self):\n        """[bar][(m).]"""\n'
    mod_src_path.write_text(mod_source)

    mod2 = Module(name='mod2', filepath=mod_src_path)
    cls2 = griffe.Class(name="C", parent=mod2)
    mod2.members["C"] = cls2
    meth2 = griffe.Function(name="m", parent=cls2)
    cls2.members["m"] = meth2
    meth2.docstring = Docstring("[bar][(m).]", parent=meth2, lineno=3)

    handler2.render(
        meth2,
        PythonRelXRefOptions(
            relative_crossrefs=True,
            check_crossrefs=False,
            compatibility_patch=patch_file,
        ), # type: ignore[call-arg]
    )

    # Trigger patch write
    handler2._write_patch_file()
    assert os.path.exists(patch_file)
    patch_content = Path(patch_file).read_text()
    assert "---" in patch_content
    assert "+++" in patch_content

    # Test that patch file is removed when no incompatibilities found
    handler2._incompatible_refs.clear()
    handler2._write_patch_file()
    assert not os.path.exists(patch_file)
