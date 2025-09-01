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
"""Support for translating compact relative crossreferences in docstrings."""

from __future__ import annotations

import ast
import re
import sys
from typing import Any, Callable, List, Optional, cast

from griffe import Alias, Docstring, GriffeError, Object
from mkdocstrings import get_logger

__all__ = [
    "substitute_relative_crossrefs"
]

logger = get_logger(__name__)

def _re_or(*exps: str) -> str:
    """Construct an "or" regular expression from a sequence of regular expressions.

    Arguments:
        *exps: two or more regular expressions

    Returns:
        regular expression string
    """
    return "(?:" + "|".join(f"(?:{exp})" for exp in exps) + ")"


def _re_named(name: str, exp: str, optional: bool = False) -> str:
    """Construct a named regular expression.

    Arguments:
        name: the name for the regular expression group to create
        exp: the regular expression to be named
        optional: if true, then the entire expression group will be made optional

    Returns:
        regular expression string
    """
    optchar = "?" if optional else ""
    return f"(?P<{name}>{exp}){optchar}"

_RE_CROSSREF = re.compile(r"\[([^\[\]]+?)\]\[([^\[\]]*?)\]")
"""Regular expression that matches general cross-references."""

_RE_REL_CROSSREF = re.compile(r"\[([^\[\]]+?)\]\[(\??(?:[\.^\(][^\]]*?|[^\]]*?\.))\]")
"""Regular expression that matches relative cross-reference expressions in doc-string.

This will match a cross reference where the path expression either ends in '.'
or begins with '.', '^' or '('.
"""

_RE_REL = re.compile(
    _re_named(
        "parent",
        _re_or(
            _re_named("up", r"(?:\^+|\.+(?=\.))") + r"\.?",
            _re_named("class", r"\([cC]\)\.?"),
            _re_named("module", r"\([mM]\)\.?"),
            _re_named("package", r"\([pP]\)\.?"),
            _re_named("current", r"\."),
        ),
        optional=True,
    )
    + _re_named("relname", r"(?:[a-zA-Z_][a-zA-Z0-9_\.]*)?")
)
"""Regular expression that matches a relative path reference.

This has two main parts a 'parent' group that matches the parent prefix expression,
if present, and a 'relname' group that matches the relative path text and any
final '.' character.

If the 'parent' group is matched, then exactly one of its subgroups will be present:

- 'up': an expression of the form '\\^'+ '\\.'? or '\\.\\.+'
- 'class': an expression of the form '(c)' '.'?
- 'module': an expression of the form '(m)' '.'?
- 'package': an expression of the form '(p)' '.'?
- 'current': an expression of the form '.'
"""

_RE_ID = re.compile("[a-zA-Z_][a-zA-Z0-9_.]*")
"""Regular expression that matches a qualified python identifier."""


def _always_ok(_ref: str) -> bool:
    return True


class _RelativeCrossrefProcessor:
    """
    A callable object that can substitute relative cross-reference expressions.

    This is intended to be used as a substitution function by `re.sub`
    to process relative cross-references in a doc-string.
    """

    _doc: Docstring
    _cur_match: re.Match | None
    _cur_input: str
    _cur_offset: int
    _cur_ref_parts: List[str]
    _ok: bool
    _check_ref: Callable[[str], bool]

    def __init__(self, doc: Docstring, checkref: Optional[Callable[[str], bool]] = None):
        self._doc = doc
        self._cur_match = None
        self._cur_input = ""
        self._cur_offset = 0
        self._cur_ref_parts = []
        self._check_ref = checkref or _always_ok
        self._ok = True

    def __call__(self, match: re.Match) -> str:
        """
        Process a cross-reference expression.

        This should be called with a match from the _RE_CROSSREF expression
        which matches expression of the form [<title>][<ref>].
        Group 1 matches the <title> and 2 the <ref>.
        """
        self._start_match(match)

        title = match[1]
        ref = match[2]

        checkref = self._check_ref
        if ref.startswith("?"):
            # Turn off cross-ref check
            ref = ref[1:]
            checkref = _always_ok

        new_ref = ""

        # TODO support special syntax to turn off checking

        if not _RE_REL_CROSSREF.fullmatch(match.group(0)):
            # Just a regular cross reference
            new_ref = ref if ref else title
        else:
            ref_match = _RE_REL.fullmatch(ref)
            if ref_match is None:
                self._error(f"Bad syntax in relative cross reference: '{ref}'")
            else:
                self._process_parent_specifier(ref_match)
                self._process_relname(ref_match)
                self._process_append_from_title(ref_match, title)

            if self._ok:
                new_ref = '.'.join(self._cur_ref_parts)
                logger.debug(
                    "cross-reference substitution\nin %s:\n[%s][%s] -> [...][%s]",
                    cast(Object, self._doc.parent).canonical_path, title, ref, new_ref
                )

        # builtin names get handled specially somehow, so don't check here
        if new_ref not in __builtins__ and not checkref(new_ref):  # type: ignore[operator]
            self._error(f"Cannot load reference '{new_ref}'")

        if new_ref:
            result = f"[{title}][{new_ref}]"
        else:
            result = match.group(0)

        return result

    def _start_match(self, match: re.Match) -> None:
        self._cur_match = match
        self._cur_offset = match.start(0)
        self._cur_input = match[0]
        self._ok = True
        self._cur_ref_parts.clear()

    def _process_relname(self, ref_match: re.Match) -> None:
        relname = ref_match.group("relname").strip(".")
        if relname:
            self._cur_ref_parts.append(relname)

    def _process_append_from_title(self, ref_match: re.Match, title_text: str) -> None:
        if ref_match.group(0).endswith("."):
            id_from_title = title_text.strip("`*")
            if not _RE_ID.fullmatch(id_from_title):
                self._error(f"Relative cross reference text is not a qualified identifier: '{id_from_title}'")
                return
            self._cur_ref_parts.append(id_from_title)

    def _process_parent_specifier(self, ref_match: re.Match) -> None:
        if not ref_match.group("parent"):
            return

        obj = self._doc.parent
        if obj is None:  # pragma: no cover
            self._error("INTERNAL ERROR: docstring lacks a parent!")
            return

        rel_obj = (
            self._process_current_specifier(obj, ref_match)
            or self._process_class_specifier(obj, ref_match)
            or self._process_module_specifier(obj, ref_match)
            or self._process_package_specifier(obj, ref_match)
            or self._process_up_specifier(obj, ref_match)
        )

        if rel_obj is not None and self._ok:
            self._cur_ref_parts.append(rel_obj.canonical_path)

    def _process_current_specifier(self, obj: Object, ref_match: re.Match) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("current"):
            if obj.is_function:
                self._error(
                    f"Cannot use '.' in function {obj.canonical_path}",
                    just_warn=False
                )
            else:
                rel_obj = obj
        return rel_obj

    def _process_class_specifier(self, obj: Object, ref_match: re.Match) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("class"):
            rel_obj = obj
            while not rel_obj.is_class:
                rel_obj = rel_obj.parent
                if rel_obj is None:
                    self._error(f"{obj.canonical_path} not in a class")
                    break
        return rel_obj

    def _process_module_specifier(self, obj: Object, ref_match: re.Match) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("module"):
            rel_obj = obj
            while not rel_obj.is_module:
                rel_obj = rel_obj.parent
                if rel_obj is None:  # pragma: no cover
                    self._error(f"{obj.canonical_path} not in a module!")
                    break
        return rel_obj

    def _process_package_specifier(self, obj: Object, ref_match: re.Match) -> Optional[Object]:
        # griffe does not distinguish between modules and packages, so we identify a package
        # as a module that contains other modules. A module that has no parent is considered to
        # be a package even if it does not contain modules.
        rel_obj: Object | None = None
        if ref_match.group("package"):
            rel_obj = obj
            if rel_obj.is_module and rel_obj.modules:
                # module contains modules, so it is a package
                return rel_obj

            while not rel_obj.is_module:
                rel_obj = rel_obj.parent
                if rel_obj is None:  # pragma: no cover
                    self._error(f"{obj.canonical_path} not in a module!")
                    break

            if rel_obj is not None and rel_obj.parent is not None:  # pragma: no branch
                # If module has no parent, we will treat it as a package
                rel_obj = rel_obj.parent

        return rel_obj

    def _process_up_specifier(self, obj: Object, ref_match: re.Match) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("up"):
            level = len(ref_match.group("up"))
            rel_obj = obj
            for _ in range(level):
                if rel_obj.parent is not None:
                    rel_obj = rel_obj.parent
                else:
                    self._error(f"'{ref_match.group('up')}' has too many levels for {obj.canonical_path}")
                    break
        return rel_obj

    def _error(self, msg: str, just_warn: bool = False) -> None:
        """Logs a warning for a specific crossref in a docstring.

        This will include the filepath and line number if available.

        Arguments:
            msg: the warning message to report
        """
        doc = self._doc
        parent = doc.parent
        prefix = ""
        if parent is not None:  # pragma: no branch
            # We include the file:// prefix because it helps IDEs such as PyCharm
            # recognize that this is a navigable location it can highlight.
            prefix = f"file://{parent.filepath}:"
            line, col = doc_value_offset_to_location(doc, self._cur_offset)
            if line >= 0:
                prefix += f"{line}:"
                if col >= 0:
                    prefix += f"{col}:"

            prefix += " \n"

        logger.warning(prefix + msg)

        self._ok = just_warn


def substitute_relative_crossrefs(
    obj: Alias|Object,
    checkref: Optional[Callable[[str], bool]] = None,
) -> None:
    """Recursively expand relative cross-references in all docstrings in tree.

    Arguments:
        obj: a Griffe [Object][griffe.] whose docstrings should be modified
        checkref: optional function to check whether computed cross-reference is valid.
            Should return True if valid, False if not valid.
    """
    if isinstance(obj, Alias):
        try:
            obj = obj.target
        except GriffeError:
            # If alias could not be resolved, it probably refers
            # to an external package, not be documented.
            return

    doc = obj.docstring

    if doc is not None:
        doc.value = _RE_CROSSREF.sub(_RelativeCrossrefProcessor(doc, checkref=checkref), doc.value)

    for member in obj.members.values():
        if isinstance(member, (Alias,Object)):  # pragma: no branch
            substitute_relative_crossrefs(member, checkref=checkref)

def doc_value_offset_to_location(doc: Docstring, offset: int) -> tuple[int,int]:
    """
    Converts offset into doc.value to line and column in source file.

    Returns:
        line and column or else (-1,-1) if it cannot be computed
    """
    linenum = -1
    colnum = -2

    if doc.lineno is not None:
        linenum = doc.lineno # start of the docstring source
        # line offset with respect to start of cleaned up docstring
        lineoffset = clean_lineoffset = doc.value.count("\n", 0, offset)

        # look at original doc source, if available
        try:
            source = doc.source
            # compute docstring without cleaning up spaces and indentation
            rawvalue = str(safe_eval(source))

            # adjust line offset by number of lines removed from front of docstring
            lineoffset += leading_space(rawvalue).count("\n")

            if lineoffset == 0 and (m := re.match(r"(\s*['\"]{1,3}\s*)\S", source)):
                # is on the same line as opening quote
                colnum = offset + len(m.group(1))
            else:
                # indentation of first non-empty line in raw and cleaned up strings
                raw_line = rawvalue.splitlines()[lineoffset]
                clean_line = doc.value.splitlines()[clean_lineoffset]
                raw_indent = len(leading_space(raw_line))
                clean_indent = len(leading_space(clean_line))
                try:
                    linestart = doc.value.rindex("\n", 0, offset) + 1
                except ValueError: # pragma: no cover
                    linestart = 0 # paranoid check, should not really happen
                colnum = offset - linestart + raw_indent - clean_indent

        except Exception:
            # Don't expect to get here, but just in case, it is better to
            # not fix up the line/column than to die.
            pass

        linenum += lineoffset

    return linenum, colnum + 1


def leading_space(s: str) -> str:
    """Returns whitespace at the front of string."""
    if m := re.match(r"\s*", s):
        return m[0]
    return "" # pragma: no cover

if sys.version_info < (3, 10) or True:
    # TODO: remove when 3.9 support is dropped
    # In 3.9, literal_eval cannot handle comments in input
    def safe_eval(s: str) -> Any:
        """Safely evaluate a string expression."""
        return eval(s) #eval(s, dict(__builtins__={}), {})
else:
    save_eval = ast.literal_eval

