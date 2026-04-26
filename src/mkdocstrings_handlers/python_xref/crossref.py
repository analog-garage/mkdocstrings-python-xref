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
"""Support for translating compact relative crossreferences in docstrings."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, cast

from griffe import Alias, Docstring, GriffeError, Object
from mkdocstrings import get_logger

__all__ = [
    "IncompatibleRef",
    "substitute_relative_crossrefs",
]

logger = get_logger(__name__)


@dataclass
class IncompatibleRef:
    """Record of a cross-reference using xref-only syntax."""

    filepath: str
    """Source file path."""
    line: int
    """Line number in source file (1-based)."""
    col: int
    """Column number in source file (1-based)."""
    original: str
    """Original cross-reference text, e.g. ``[title][ref]``."""
    replacement: str
    """Standard-compatible replacement text."""
    reasons: list[str] = field(default_factory=list)
    """Description of incompatible syntax elements found."""

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

_RE_CROSSREF = re.compile(
    r"(?<![a-zA-Z0-9_\]`])"        # not preceded by identifier char, ], or `
    r"\[(?!\d+\])"                   # title bracket: title must not be purely numeric
    r"([^\[\],:]+?)"                 # title: 1+ chars, no brackets/commas/colons
    r"\]\["                          # close title bracket, open ref bracket
    r"([a-zA-Z_?^.(][^\[\],:]*?|)"  # ref: empty OR starts with a valid crossref start char
    r"\]"
)
"""Regular expression that matches general cross-references.

Matches expressions of the form ``[title][ref]`` with the following restrictions
to avoid false positives from array indexing, slices, and similar constructs:

- Not preceded by an identifier character (letter, digit, ``_``), ``]``, or a
  backtick.  This prevents matching expressions like ``array[i][j]``.
- The title (first ``[...]``) must not consist solely of digits, and must not
  contain commas or colons (which indicate indexing or slice expressions).
- The ref (second ``[...]``) must be empty or start with a letter, ``_``, ``?``,
  ``^``, ``.``, or ``(``. It must not contain commas or colons.
"""

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
    _incompatible_refs: list[IncompatibleRef] | None
    _cur_incompat_reasons: list[str]

    def __init__(
        self,
        doc: Docstring,
        checkref: Optional[Callable[[str], bool]] = None,
        incompatible_refs: Optional[list[IncompatibleRef]] = None,
    ):
        self._doc = doc
        self._cur_match = None
        self._cur_input = ""
        self._cur_offset = 0
        self._cur_ref_parts = []
        self._check_ref = checkref or _always_ok
        self._ok = True
        self._incompatible_refs = incompatible_refs
        self._cur_incompat_reasons = []

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
        original_ref = ref

        checkref = self._check_ref
        has_question_prefix = ref.startswith("?")
        if has_question_prefix:
            # Turn off cross-ref check
            ref = ref[1:]
            checkref = _always_ok
            self._add_incompat_reason("leading '?' suppresses reference checking")

        new_ref = ""
        std_ref_parts: list[str] = []

        if not _RE_REL_CROSSREF.fullmatch(match.group(0)):
            # Just a regular cross reference
            new_ref = ref if ref else title
            if has_question_prefix:
                std_ref_parts.append(ref if ref else title)
        else:
            ref_match = _RE_REL.fullmatch(ref)
            if ref_match is None:
                self._error(f"Bad syntax in relative cross reference: '{ref}'")
            else:
                self._process_parent_specifier(ref_match, std_ref_parts)
                self._process_relname(ref_match, std_ref_parts)
                self._process_append_from_title(ref_match, title, std_ref_parts)

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

        # Record incompatibility if any xref-only syntax was found
        if self._cur_incompat_reasons and self._incompatible_refs is not None and self._ok:
            std_ref = _assemble_std_ref(std_ref_parts) if std_ref_parts else new_ref
            self._record_incompatible_ref(
                match, original_ref, f"[{title}][{std_ref}]"
            )

        return result

    def _start_match(self, match: re.Match) -> None:
        self._cur_match = match
        self._cur_offset = match.start(0)
        self._cur_input = match[0]
        self._ok = True
        self._cur_ref_parts.clear()
        self._cur_incompat_reasons.clear()

    def _add_incompat_reason(self, reason: str) -> None:
        """Record an incompatibility reason for the current match."""
        self._cur_incompat_reasons.append(reason)

    def _record_incompatible_ref(
        self, match: re.Match, original_ref: str, replacement: str,
    ) -> None:
        """Record an incompatible cross-reference."""
        if self._incompatible_refs is None:
            return
        doc = self._doc
        parent = doc.parent
        filepath = str(parent.filepath) if parent is not None else "<unknown>"
        line, col = doc_value_offset_to_location(doc, self._cur_offset)
        self._incompatible_refs.append(IncompatibleRef(
            filepath=filepath,
            line=line,
            col=col,
            original=match.group(0),
            replacement=replacement,
            reasons=list(self._cur_incompat_reasons),
        ))

    def _process_relname(self, ref_match: re.Match, std_ref_parts: list[str]) -> None:
        relname = ref_match.group("relname").strip(".")
        if relname:
            self._cur_ref_parts.append(relname)
            std_ref_parts.append(relname)

    def _process_append_from_title(
        self, ref_match: re.Match, title_text: str, std_ref_parts: list[str],
    ) -> None:
        if ref_match.group(0).endswith("."):
            id_from_title = title_text.strip("`*")
            if not _RE_ID.fullmatch(id_from_title):
                self._error(f"Relative cross reference text is not a qualified identifier: '{id_from_title}'")
                return
            self._cur_ref_parts.append(id_from_title)
            # Trailing '.' after a name is xref-only "append title" syntax.
            # After non-alphanumeric (e.g. ')' in (m).) it's just a separator
            # absorbed by the dot prefix in standard form.
            ref_text = ref_match.group(0)
            if len(ref_text) >= 2 and ref_text[-2].isalnum():
                self._add_incompat_reason("trailing '.' appends title to reference")
                std_ref_parts.append(id_from_title)

    def _process_parent_specifier(
        self, ref_match: re.Match, std_ref_parts: list[str],
    ) -> None:
        if not ref_match.group("parent"):
            return

        obj = self._doc.parent
        if obj is None:  # pragma: no cover
            self._error("INTERNAL ERROR: docstring lacks a parent!")
            return

        rel_obj = (
            self._process_current_specifier(obj, ref_match, std_ref_parts)
            or self._process_class_specifier(obj, ref_match, std_ref_parts)
            or self._process_module_specifier(obj, ref_match, std_ref_parts)
            or self._process_package_specifier(obj, ref_match, std_ref_parts)
            or self._process_up_specifier(obj, ref_match, std_ref_parts)
        )

        if rel_obj is not None and self._ok:
            self._cur_ref_parts.append(rel_obj.canonical_path)

    def _process_current_specifier(
        self, obj: Object, ref_match: re.Match, std_ref_parts: list[str],
    ) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("current"):
            if obj.is_function:
                self._error(
                    f"Cannot use '.' in function {obj.canonical_path}",
                    just_warn=False
                )
            else:
                rel_obj = obj
                std_ref_parts.append('.')
        return rel_obj

    def _process_class_specifier(
        self, obj: Object, ref_match: re.Match, std_ref_parts: list[str],
    ) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("class"):
            rel_obj = obj
            levels = 0
            while not rel_obj.is_class:
                rel_obj = rel_obj.parent
                levels += 1
                if rel_obj is None:
                    self._error(f"{obj.canonical_path} not in a class")
                    break
            if rel_obj is not None:
                self._add_incompat_reason("'(c)' class specifier")
                std_ref_parts.append('.' * (levels + 1))
        return rel_obj

    def _process_module_specifier(
        self, obj: Object, ref_match: re.Match, std_ref_parts: list[str],
    ) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("module"):
            rel_obj = obj
            levels = 0
            while not rel_obj.is_module:
                rel_obj = rel_obj.parent
                levels += 1
                if rel_obj is None:  # pragma: no cover
                    self._error(f"{obj.canonical_path} not in a module!")
                    break
            if rel_obj is not None:
                self._add_incompat_reason("'(m)' module specifier")
                std_ref_parts.append('.' * (levels + 1))
        return rel_obj

    def _process_package_specifier(
        self, obj: Object, ref_match: re.Match, std_ref_parts: list[str],
    ) -> Optional[Object]:
        # griffe does not distinguish between modules and packages, so we identify a package
        # as a module that contains other modules. A module that has no parent is considered to
        # be a package even if it does not contain modules.
        rel_obj: Object | None = None
        if ref_match.group("package"):
            rel_obj = obj
            levels = 0
            if rel_obj.is_module and rel_obj.modules:
                # module contains modules, so it is a package
                self._add_incompat_reason("'(p)' package specifier")
                std_ref_parts.append('.' * (levels + 1))
                return rel_obj

            while not rel_obj.is_module:
                rel_obj = rel_obj.parent
                levels += 1
                if rel_obj is None:  # pragma: no cover
                    self._error(f"{obj.canonical_path} not in a module!")
                    break

            if rel_obj is not None and rel_obj.parent is not None:  # pragma: no branch
                # If module has no parent, we will treat it as a package
                rel_obj = rel_obj.parent
                levels += 1

            if rel_obj is not None:
                self._add_incompat_reason("'(p)' package specifier")
                std_ref_parts.append('.' * (levels + 1))

        return rel_obj

    def _process_up_specifier(
        self, obj: Object, ref_match: re.Match, std_ref_parts: list[str],
    ) -> Optional[Object]:
        rel_obj: Object | None = None
        if ref_match.group("up"):
            up_text = ref_match.group("up")
            level = len(up_text)
            uses_caret = '^' in up_text
            rel_obj = obj
            for _ in range(level):
                if rel_obj.parent is not None:
                    rel_obj = rel_obj.parent
                else:
                    self._error(f"'{up_text}' has too many levels for {obj.canonical_path}")
                    break
            if rel_obj is not None:
                if uses_caret:
                    self._add_incompat_reason("'^' caret specifier")
                # Standard dot-prefix equivalent: level+1 dots
                std_ref_parts.append('.' * (level + 1))
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


def _assemble_std_ref(parts: list[str]) -> str:
    """Assemble a standard cross-reference from parts.

    The first element may be a dot-prefix (e.g., ``..``), which is concatenated
    directly with the remaining parts (joined by ``'.'``).
    """
    if not parts:
        return ""
    prefix = parts[0]
    rest = parts[1:]
    if prefix and all(c == '.' for c in prefix):
        # Dot prefix: concatenate directly with rest
        return prefix + '.'.join(rest)
    # Regular name parts: join all with '.'
    return '.'.join(parts)


def substitute_relative_crossrefs(
    obj: Alias|Object,
    checkref: Optional[Callable[[str], bool]] = None,
    incompatible_refs: Optional[list[IncompatibleRef]] = None,
    *,
    _root_pkg: str = "",
    _visited: set[int] | None = None,
) -> None:
    """Recursively expand relative cross-references in all docstrings in tree.

    Only objects within the same root package are processed. Aliases that point
    to external packages are skipped to avoid recursing into third-party or stdlib
    code. Cycle detection via ``_visited`` prevents infinite recursion from cyclic
    imports within the project.

    Arguments:
        obj: a Griffe [Object][griffe.] whose docstrings should be modified
        checkref: optional function to check whether computed cross-reference is valid.
            Should return True if valid, False if not valid.
        incompatible_refs: if provided, incompatible cross-references will be appended
            to this list.
        _root_pkg: private — root package name used to filter external aliases.
            Derived automatically from ``obj`` on the first call; do not pass explicitly.
        _visited: private — set of already-visited object ids for cycle detection.
            Allocated automatically on the first call; do not pass explicitly.
    """
    if _visited is None:
        _visited = set()

    if isinstance(obj, Alias):
        try:
            obj = obj.target
        except GriffeError:
            # If alias could not be resolved, it probably refers
            # to an external package, not be documented.
            return

    # Cycle detection: if we've already processed this object, stop.
    obj_id = id(obj)
    if obj_id in _visited:
        return
    _visited.add(obj_id)

    # Determine the root package on the first (non-recursive) call.
    if not _root_pkg:
        _root_pkg = obj.canonical_path.split('.')[0]

    doc = obj.docstring

    if doc is not None:
        doc.value = _RE_CROSSREF.sub(
            _RelativeCrossrefProcessor(
                doc, checkref=checkref, incompatible_refs=incompatible_refs,
            ),
            doc.value,
        )

    for member in obj.members.values():
        if isinstance(member, Alias):
            # Resolve the alias target; skip if it belongs to a different (external) package.
            try:
                target = member.target
            except GriffeError:
                continue  # Unresolvable alias — likely an external package not being documented.
            if target.canonical_path.split('.')[0] != _root_pkg:
                continue  # External package alias — don't recurse into third-party/stdlib code.
        elif not isinstance(member, Object):  # pragma: no cover
            continue  # Defensive: griffe members should always be Alias or Object.
        substitute_relative_crossrefs(
            member, checkref=checkref, incompatible_refs=incompatible_refs,
            _root_pkg=_root_pkg, _visited=_visited,
        )

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
            rawvalue = str(ast.literal_eval(source))

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


