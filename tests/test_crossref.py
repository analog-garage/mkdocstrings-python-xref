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
"""Unit tests for relative crossref expansion."""

from __future__ import annotations

import inspect
import logging
import re
from ast import literal_eval
from pathlib import Path
from textwrap import dedent
from typing import Callable, Optional

import griffe
import pytest
from griffe import Class, Docstring, Function, Module, Object, LinesCollection

# noinspection PyProtectedMember
from mkdocstrings_handlers.python_xref.crossref import (
    IncompatibleRef,
    _RE_CROSSREF,
    _RE_REL_CROSSREF,
    _RelativeCrossrefProcessor,
    substitute_relative_crossrefs, doc_value_offset_to_location,
)

def test_RelativeCrossrefProcessor(caplog: pytest.LogCaptureFixture) -> None:
    """Unit test for internal _RelativeCrossrefProcessor class.

    Arguments:
        caplog: fixture
    """
    mod1 = Module(name="mod1", filepath=Path("mod1.py"))
    mod2 = Module(name="mod2", parent=mod1, filepath=Path("mod2.py"))
    mod1.members.update(mod2=mod2)
    cls1 = Class(name="Class1", parent=mod2)
    mod2.members.update(Class1=cls1)
    meth1 = Function(name="meth1", parent=cls1)
    cls1.members.update(meth1=meth1)

    def assert_sub(parent: Object, title: str, ref: str,
                   expected: str = "",
                   *,
                   warning: str = "",
                   relative: bool = True,
                   checkref: Optional[Callable[[str],bool]] = None
                   ) -> None:
        """Tests a relative crossref substitution

        Arguments:
            parent: assumed parent object for docstring
            title: the title portion of the cross-reference expression
            ref: the reference path section of the cross-reference expression
            expected: the expected new value for the cross-reference
            warning: if specified, is regexp matching expected warning message
            relative: true if relative reference is expected
            checkref: reference checking function
        """
        if not expected:
            expected = ref
        crossref = f"[{title}][{ref}]"
        doc = Docstring(parent=parent, value=f"subject\n\n{crossref}\n", lineno=42)
        match = _RE_REL_CROSSREF.search(doc.value)
        if relative:
            assert match is not None
        else:
            assert match is None
            match = _RE_CROSSREF.search(doc.value)
            assert match is not None
        caplog.clear()
        actual = _RelativeCrossrefProcessor(doc, checkref=checkref)(match)
        if warning:
            assert len(caplog.records) == 1
            _, level, msg = caplog.record_tuples[0]
            assert level == logging.WARNING
            assert re.search(warning, msg)
            assert f"{parent.filepath}:44:" in msg
        else:
            assert not caplog.records
        assert actual == f"[{title}][{expected}]"

    assert_sub(cls1, "foo", ".", "mod1.mod2.Class1.foo")
    assert_sub(meth1, "foo", "^", "mod1.mod2.Class1")
    assert_sub(meth1, "foo", "^.", "mod1.mod2.Class1.foo")
    assert_sub(meth1, "foo", "..", "mod1.mod2.Class1.foo")
    assert_sub(meth1, "foo", "^.bar", "mod1.mod2.Class1.bar")
    assert_sub(meth1, "foo", "(c)", "mod1.mod2.Class1")
    assert_sub(meth1, "foo", "(c).", "mod1.mod2.Class1.foo")
    assert_sub(meth1, "foo", "(C).baz", "mod1.mod2.Class1.baz")
    assert_sub(meth1, "foo", "(c).baz.", "mod1.mod2.Class1.baz.foo")
    assert_sub(meth1, "foo", "(m).", "mod1.mod2.foo")
    assert_sub(meth1, "foo", "mod3.", "mod3.foo")
    assert_sub(meth1, "foo", "^^.", "mod1.mod2.foo", checkref = lambda x: True)
    assert_sub(meth1, "foo", "...", "mod1.mod2.foo", checkref = lambda x: True)
    assert_sub(meth1, "Class1", "(p).mod2.", "mod1.mod2.Class1")
    assert_sub(mod1, "Class1", "(P).mod2.Class1", "mod1.mod2.Class1")

    # disable checking

    def assert_nocheck(val: str) -> bool:
        pytest.fail(f"unexpected check of '{val}'")
        return False

    assert_sub(cls1, "foo", "?.", "mod1.mod2.Class1.foo", checkref=assert_nocheck)
    assert_sub(cls1, "foo", "?mod1.mod2.Class1.foo", "mod1.mod2.Class1.foo",
               checkref=assert_nocheck, relative=False)

    # Error cases

    assert_sub(meth1, "foo", ".", ".", warning="Cannot use '.'")
    assert_sub(meth1, "foo", ".bar", ".bar", warning="Cannot use '.'")
    assert_sub(meth1, "foo", ".bad+syntax", warning="Bad syntax")
    assert_sub(meth1, "bad id", "..", warning="not a qualified identifier")
    assert_sub(mod2, "foo", "(c)", warning="not in a class")
    assert_sub(meth1, "foo", "^^^^", warning="too many levels")
    assert_sub(meth1, "foo", "..", "mod1.mod2.Class1.foo",
               warning = "Cannot load reference 'mod1.mod2.Class1.foo'",
               checkref=lambda x: False)
    assert_sub(meth1, "foo", "mod1.mod2.Class1.foo", "mod1.mod2.Class1.foo",
               warning = "Cannot load reference 'mod1.mod2.Class1.foo'",
               relative=False,
               checkref=lambda x: False)


def test_substitute_relative_crossrefs(caplog: pytest.LogCaptureFixture) -> None:
    """Unit test for substitute_relative_crossrefs.

    Arguments:
        caplog: fixture
    """
    caplog.clear()

    mod1 = Module(name="mod1", filepath=Path("mod1.py"))
    mod2 = Module(name="mod2", parent=mod1, filepath=Path("mod2.py"))
    mod1.members["mod2"] = mod2
    cls1 = Class(name="Class1", parent=mod2)
    mod2.members["Class1"] = cls1
    meth1 = Function(name="meth1", parent=cls1)
    cls1.members["meth1"] = meth1

    meth1.docstring = Docstring(
        """
    [foo][..]
    [bar][(m).]
    """,
        parent=meth1,
        lineno=42,
        endlineno=45,
    )

    mod1.docstring = Docstring(
        """
    [mod2.Class1][.]
    """,
        parent=mod1,
        lineno=23,
        endlineno=25,
    )

    substitute_relative_crossrefs(mod1)

    assert meth1.docstring.value == inspect.cleandoc(
        """
    [foo][mod1.mod2.Class1.foo]
    [bar][mod1.mod2.bar]
    """
    )

    assert len(caplog.records) == 0

def make_docstring_from_source(
    source: str,
    *,
    lineno: int = 1,
    mod_name: str = "mod",
    mod_dir: Path = Path(""),
) -> Docstring:
    """
    Create a docstring object from source code.

    Args:
        source: raw source code containing docstring source lines
        lineno: line number of docstring starting quotes
        mod_name: name of module
        mod_dir: module directory
    """
    filepath = mod_dir.joinpath(mod_name).with_suffix(".py")
    parent = Object("", lines_collection=LinesCollection())
    mod = Module(name=mod_name, filepath=filepath, parent=parent)
    lines = source.splitlines(keepends=False)
    if lineno > 1:
        # Insert empty lines to pad to the desired line number
        lines = [""] * (lineno - 1) + lines
    mod.lines_collection[filepath] = lines
    doc = Docstring(
        parent=mod,
        value=inspect.cleandoc(eval(source)),
        lineno=lineno,
        endlineno=len(lines)
    )
    return doc

def test_doc_value_offset_to_location() -> None:
    """Unit test for _doc_value_offset_to_location."""
    doc1 = make_docstring_from_source(
        dedent(
            '''
            """first
            second
            third
            """
            '''
        ).lstrip("\n"),
    )

    # note columns start with 1
    assert doc_value_offset_to_location(doc1, 0) == (1, 4)
    assert doc_value_offset_to_location(doc1, 3) == (1, 7)
    assert doc_value_offset_to_location(doc1, 7) == (2, 2)
    assert doc_value_offset_to_location(doc1, 15) == (3, 3)

    doc2 = make_docstring_from_source(
        dedent(
            '''   
               """   first
                  second
                   third
               """  # a comment
               
            # another comment
            '''
        ).lstrip("\n"),
        lineno=3,
    )

    assert doc_value_offset_to_location(doc2, 0) == (3, 10)
    assert doc_value_offset_to_location(doc2, 6) == (4, 7)
    assert doc_value_offset_to_location(doc2, 15) == (5, 9)

    # Remove parent so that source is not available
    doc2.parent = None
    assert doc_value_offset_to_location(doc2, 0) == (3, -1)

    doc3 = make_docstring_from_source(
        dedent(
            """
            '''
                first
              second
            '''
            """
        ).lstrip("\n"),
    )

    assert doc_value_offset_to_location(doc3, 0) == (2, 5)
    assert doc_value_offset_to_location(doc3, 6) == (3, 3)

def test_griffe() -> None:
    """
    Test substitution on griffe rep of local project
    Returns:

    """
    this_dir = Path(__file__).parent
    test_src_dir  = this_dir / "project" / "src"
    myproj = griffe.load(
        "myproj",
        search_paths = [ test_src_dir ],
    )
    substitute_relative_crossrefs(myproj)
    # TODO - grovel output


def test_incompatible_refs() -> None:
    """Test detection of incompatible cross-references."""
    mod1 = Module(name="mod1", filepath=Path("mod1.py"))
    mod2 = Module(name="mod2", parent=mod1, filepath=Path("mod2.py"))
    mod1.members.update(mod2=mod2)
    cls1 = Class(name="Class1", parent=mod2)
    mod2.members.update(Class1=cls1)
    meth1 = Function(name="meth1", parent=cls1)
    cls1.members.update(meth1=meth1)

    def check_incompat(
        parent: Object,
        title: str,
        ref: str,
        *,
        expected_reasons: list[str] | None = None,
        expected_replacement: str = "",
    ) -> IncompatibleRef | None:
        """Test incompatible ref detection for a single crossref."""
        crossref = f"[{title}][{ref}]"
        doc = Docstring(parent=parent, value=crossref, lineno=1)
        incompat: list[IncompatibleRef] = []
        match = _RE_CROSSREF.search(doc.value)
        assert match is not None
        _RelativeCrossrefProcessor(doc, incompatible_refs=incompat)(match)
        if expected_reasons is None:
            assert len(incompat) == 0, f"Expected no incompatibilities, got {incompat}"
            return None
        assert len(incompat) == 1, f"Expected 1 incompatibility, got {len(incompat)}"
        result = incompat[0]
        for reason in expected_reasons:
            assert any(reason in r for r in result.reasons), (
                f"Expected reason containing '{reason}' in {result.reasons}"
            )
        if expected_replacement:
            assert result.replacement == expected_replacement
        return result

    # Standard syntax: no incompatibility
    check_incompat(meth1, "foo", "..bar", expected_reasons=None)
    check_incompat(cls1, "foo", ".", expected_reasons=None)
    check_incompat(meth1, "foo", "..", expected_reasons=None)
    check_incompat(meth1, "foo", "...", expected_reasons=None)

    # Caret specifier: incompatible
    check_incompat(
        meth1, "foo", "^",
        expected_reasons=["'^' caret"],
        expected_replacement="[foo][..]",
    )
    check_incompat(
        meth1, "foo", "^.",
        expected_reasons=["'^' caret"],
        expected_replacement="[foo][..]",
    )
    check_incompat(
        meth1, "foo", "^.bar",
        expected_reasons=["'^' caret"],
        expected_replacement="[foo][..bar]",
    )
    check_incompat(
        meth1, "foo", "^^",
        expected_reasons=["'^' caret"],
        expected_replacement="[foo][...]",
    )

    # Class specifier: incompatible
    check_incompat(
        meth1, "foo", "(c)",
        expected_reasons=["'(c)' class"],
        expected_replacement="[foo][..]",
    )
    check_incompat(
        meth1, "foo", "(c).",
        expected_reasons=["'(c)' class"],
        expected_replacement="[foo][..]",
    )
    check_incompat(
        meth1, "foo", "(C).baz",
        expected_reasons=["'(c)' class"],
        expected_replacement="[foo][..baz]",
    )
    check_incompat(
        meth1, "foo", "(C).baz.",
        expected_reasons=["'(c)' class", "trailing '.'"],
        expected_replacement="[foo][..baz.foo]",
    )

    # Module specifier: incompatible
    check_incompat(
        meth1, "foo", "(m).",
        expected_reasons=["'(m)' module"],
        expected_replacement="[foo][...]",
    )
    check_incompat(
        meth1, "foo", "(m).bar.",
        expected_reasons=["'(m)' module", "trailing '.'"],
        expected_replacement="[foo][...bar.foo]",
    )

    # Package specifier: incompatible
    check_incompat(
        meth1, "Class1", "(p).",
        expected_reasons=["'(p)' package"],
        expected_replacement="[Class1][....]",
    )
    check_incompat(
        meth1, "Class1", "(p).mod2.",
        expected_reasons=["'(p)' package", "trailing '.'"],
        expected_replacement="[Class1][....mod2.Class1]",
    )

    # Trailing dot only (no parent specifier): incompatible
    check_incompat(
        meth1, "foo", "mod3.",
        expected_reasons=["trailing '.'"],
        expected_replacement="[foo][mod3.foo]",
    )

    # Trailing dot after name with dot-prefix up specifier: incompatible
    check_incompat(
        meth1, "bar", "..foo.",
        expected_reasons=["trailing '.'"],
        expected_replacement="[bar][..foo.bar]",
    )

    # Question mark prefix: incompatible
    check_incompat(
        cls1, "foo", "?.",
        expected_reasons=["leading '?'"],
        expected_replacement="[foo][.]",
    )
    check_incompat(
        cls1, "foo", "?mod1.mod2.Class1.foo",
        expected_reasons=["leading '?'"],
        expected_replacement="[foo][mod1.mod2.Class1.foo]",
    )
    check_incompat(
        meth1, "foo", "?(m).",
        expected_reasons=["'(m)' module", "leading '?'"],
        expected_replacement="[foo][...]",
    )



def test_substitute_incompatible_refs() -> None:
    """Test incompatible ref collection through substitute_relative_crossrefs."""
    mod1 = Module(name="mod1", filepath=Path("mod1.py"))
    cls1 = Class(name="Class1", parent=mod1)
    mod1.members["Class1"] = cls1
    meth1 = Function(name="meth1", parent=cls1)
    cls1.members["meth1"] = meth1

    meth1.docstring = Docstring(
        "[foo][(c).] [bar][..bar]",
        parent=meth1,
        lineno=10,
    )

    incompat: list[IncompatibleRef] = []
    substitute_relative_crossrefs(mod1, incompatible_refs=incompat)

    # (c). is incompatible, .. is standard
    assert len(incompat) == 1
    assert incompat[0].original == "[foo][(c).]"
    assert incompat[0].replacement == "[foo][..]"
    assert any("(c)" in r for r in incompat[0].reasons)
