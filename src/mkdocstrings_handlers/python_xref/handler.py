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
"""
Implementation of python_xref handler
"""

from __future__ import annotations

import atexit
import difflib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field, fields
from functools import partial
from pathlib import Path
from typing import Any, ClassVar, Literal, Mapping, MutableMapping, Optional
from warnings import warn

from mkdocs.config.defaults import MkDocsConfig
from mkdocstrings import CollectorItem, get_logger
from mkdocstrings_handlers.python import PythonHandler, PythonOptions, PythonConfig

from .crossref import IncompatibleRef, substitute_relative_crossrefs

__all__ = [
    'PythonRelXRefHandler'
]

logger = get_logger(__name__)

@dataclass(frozen=True, kw_only=True)
class PythonRelXRefOptions(PythonOptions):
    check_crossrefs: bool = True
    check_crossrefs_exclude: list[str | re.Pattern] = field(default_factory=list)
    compatibility_check: Literal[False, "warn", "error"] = False
    compatibility_patch: str | Literal[False] = False

class PythonRelXRefHandler(PythonHandler):
    """Extended version of mkdocstrings Python handler

    * Converts relative cross-references into full references
    * Checks cross-references early in order to produce errors with source location
    """

    name: ClassVar[str] = "python_xref"
    """Override the handler name"""

    def __init__(self, config: PythonConfig, base_dir: Path, **kwargs: Any) -> None:
        """Initialize the handler.

        Parameters:
            config: The handler configuration.
            base_dir: The base directory of the project.
            **kwargs: Arguments passed to the parent constructor.
        """
        self.check_crossrefs = config.options.pop('check_crossrefs', True)
        exclude = config.options.pop('check_crossrefs_exclude', [])
        self.check_crossrefs_exclude = [re.compile(p) for p in exclude]
        self.compatibility_check: Literal[False, "warn", "error"] = (
            config.options.pop('compatibility_check', False)
        )
        self.compatibility_patch: str | Literal[False] = (
            config.options.pop('compatibility_patch', False)
        )
        self._incompatible_refs: list[IncompatibleRef] = []
        super().__init__(config, base_dir, **kwargs)
        if self.compatibility_patch:
            atexit.register(self._write_patch_file)

    def get_options(self, local_options: Mapping[str, Any]) -> PythonRelXRefOptions:
        local_options = dict(local_options)
        check_crossrefs = local_options.pop(
            'check_crossrefs', self.check_crossrefs)
        check_crossrefs_exclude = local_options.pop(
            'check_crossrefs_exclude', self.check_crossrefs_exclude)
        compatibility_check = local_options.pop(
            'compatibility_check', self.compatibility_check)
        compatibility_patch = local_options.pop(
            'compatibility_patch', self.compatibility_patch)
        _opts = super().get_options(local_options)
        opts = PythonRelXRefOptions(
            check_crossrefs=check_crossrefs,
            check_crossrefs_exclude=check_crossrefs_exclude,
            compatibility_check=compatibility_check,
            compatibility_patch=compatibility_patch,
            **{field.name: getattr(_opts, field.name) for field in fields(_opts)}
        )
        return opts

    def render(self, data: CollectorItem, options: PythonOptions, locale: str | None = None) -> str:
        if options.relative_crossrefs:
            if isinstance(options, PythonRelXRefOptions) and options.check_crossrefs:
                checkref = partial(
                    self._check_ref, exclude=options.check_crossrefs_exclude)
            else:
                checkref = None

            # Collect incompatible refs if compatibility features are enabled
            incompat: list[IncompatibleRef] | None = None
            if isinstance(options, PythonRelXRefOptions) and (
                options.compatibility_check or options.compatibility_patch
            ):
                incompat = []

            substitute_relative_crossrefs(
                data, checkref=checkref, incompatible_refs=incompat,
            )

            if incompat and isinstance(options, PythonRelXRefOptions):
                self._handle_incompatible_refs(incompat, options)

        try:
            return super().render(data, options, locale=locale)
        except Exception:  # pragma: no cover
            print(f"{data.path=}")
            raise

    def _handle_incompatible_refs(
        self,
        refs: list[IncompatibleRef],
        options: PythonRelXRefOptions,
    ) -> None:
        """Report and/or record incompatible cross-references.

        Arguments:
            refs: list of incompatible cross-references found
            options: handler options
        """
        if options.compatibility_check:
            if options.compatibility_check == "error":
                level = logging.ERROR
            else:
                level = logging.WARNING
            for ref in refs:
                prefix = f"file://{ref.filepath}:"
                if ref.line >= 0:
                    prefix += f"{ref.line}:"
                    if ref.col >= 0:
                        prefix += f"{ref.col}:"
                prefix += " \n"
                reasons = ", ".join(ref.reasons)
                logger.log(
                    level,
                    "%sIncompatible cross-reference %s (%s)",
                    prefix, ref.original, reasons,
                )

        if options.compatibility_patch:
            self._incompatible_refs.extend(refs)

    def get_templates_dir(self, handler: Optional[str] = None) -> Path:
        """See [render][.barf]"""
        # use same templates as standard python handler
        if handler == self.name:
            handler = 'python'
        return super().get_templates_dir(handler)

    def get_extended_templates_dirs(self, handler: str) -> list[Path]:
        # use same templates as standard python handler
        if handler == self.name:
            handler = 'python'
        return super().get_extended_templates_dirs(handler)

    def _check_ref(self, ref : str, exclude: list[str | re.Pattern] = []) -> bool:
        """Check for existence of reference"""
        for ex in exclude:
            if re.match(ex, ref):
                return True
        try:
            self.collect(ref, PythonOptions())
            return True
        except Exception:  # pylint: disable=broad-except
            # Only expect a CollectionError but we may as well catch everything.
            return False

    def _write_patch_file(self) -> None:
        """Write or remove the compatibility patch file.

        If incompatible refs were collected, writes a unified diff patch to the
        path specified by `compatibility_patch`. If no incompatibilities were
        found, removes any existing patch file from a previous run.
        """
        if not self.compatibility_patch:
            return

        patch_path = Path(self.compatibility_patch)

        if not self._incompatible_refs:
            if patch_path.exists():
                patch_path.unlink()
                logger.info("Removed existing scompatibility patch %s (no incompatibilities found)", patch_path)
            return

        patches = _generate_patch(self._incompatible_refs)
        patch_path.write_text(patches, encoding="utf-8")
        logger.info("Wrote compatibility patch to %s", patch_path)


def _generate_patch(refs: list[IncompatibleRef]) -> str:
    """Generate a unified diff patch from incompatible cross-references.

    Arguments:
        refs: list of incompatible cross-references

    Returns:
        unified diff patch string
    """
    # Group refs by filepath
    by_file: dict[str, list[IncompatibleRef]] = defaultdict(list)
    for ref in refs:
        by_file[ref.filepath].append(ref)

    patch_parts: list[str] = []
    for filepath, file_refs in sorted(by_file.items()):
        try:
            original_lines = Path(filepath).read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError:
            logger.warning("Cannot read file for patch: %s", filepath)
            continue

        modified_lines = list(original_lines)
        # Sort refs by line (descending) to apply replacements from bottom to top
        for ref in sorted(file_refs, key=lambda r: (r.line, r.col), reverse=True):
            if ref.line < 1 or ref.line > len(modified_lines):
                # line is -1 when docstring has no line number info
                logger.warning(
                    "Cannot patch %s: no source location for %s",
                    filepath, ref.original,
                )
                continue
            line_idx = ref.line - 1
            line = modified_lines[line_idx]
            # Use column position for accurate replacement
            col_offset = ref.col - 1 if ref.col >= 1 else 0
            idx = line.find(ref.original, col_offset)
            if idx >= 0:
                modified_lines[line_idx] = (
                    line[:idx] + ref.replacement + line[idx + len(ref.original):]
                )

        if original_lines != modified_lines:
            diff = difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
            )
            patch_parts.append(''.join(diff))

    return '\n'.join(patch_parts)

def get_handler(
    handler_config: MutableMapping[str, Any],
    tool_config: MkDocsConfig,
    **kwargs: Any,
) -> PythonHandler:
    """Simply return an instance of `PythonRelXRefHandler`.

    Arguments:
        handler_config: The handler configuration.
        tool_config: The tool (SSG) configuration.

    Returns:
        An instance of `PythonRelXRefHandler`.
    """
    base_dir = Path(tool_config.config_file_path or "./mkdocs.yml").parent
    if "inventories" not in handler_config and "import" in handler_config:
        warn("The 'import' key is renamed 'inventories' for the Python handler", FutureWarning, stacklevel=1)
        handler_config["inventories"] = handler_config.pop("import", [])
    return PythonRelXRefHandler(
        config=PythonConfig.from_data(**handler_config),
        base_dir=base_dir,
        **kwargs,
    )
