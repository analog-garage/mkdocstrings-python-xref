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
"""
Implementation of python_xref handler
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field, fields
from functools import partial
from pathlib import Path
from typing import Any, ClassVar, Mapping, MutableMapping, Optional
from warnings import warn

from mkdocs.config.defaults import MkDocsConfig
from mkdocstrings import CollectorItem, get_logger
from mkdocstrings_handlers.python import PythonHandler, PythonOptions, PythonConfig

from .crossref import substitute_relative_crossrefs

__all__ = [
    'PythonRelXRefHandler'
]

logger = get_logger(__name__)

# TODO python 3.9 - remove when 3.9 support is dropped
_dataclass_options = {"frozen": True}
if sys.version_info >= (3, 10):
    _dataclass_options["kw_only"] = True

@dataclass(**_dataclass_options)
class PythonRelXRefOptions(PythonOptions):
    check_crossrefs: bool = True
    check_crossrefs_exclude: list[str | re.Pattern] = field(default_factory=list)

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
        super().__init__(config, base_dir, **kwargs)

    def get_options(self, local_options: Mapping[str, Any]) -> PythonRelXRefOptions:
        local_options = dict(local_options)
        check_crossrefs = local_options.pop(
            'check_crossrefs', self.check_crossrefs)
        check_crossrefs_exclude = local_options.pop(
            'check_crossrefs_exclude', self.check_crossrefs_exclude)
        _opts = super().get_options(local_options)
        opts = PythonRelXRefOptions(
            check_crossrefs=check_crossrefs,
            check_crossrefs_exclude=check_crossrefs_exclude,
            **{field.name: getattr(_opts, field.name) for field in fields(_opts)}
        )
        return opts

    def render(self, data: CollectorItem, options: PythonOptions) -> str:
        if options.relative_crossrefs:
            if isinstance(options, PythonRelXRefOptions) and options.check_crossrefs:
                checkref = partial(
                    self._check_ref, exclude=options.check_crossrefs_exclude)
            else:
                checkref = None
            substitute_relative_crossrefs(data, checkref=checkref)

        try:
            return super().render(data, options)
        except Exception:  # pragma: no cover
            print(f"{data.path=}")
            raise

    def get_templates_dir(self, handler: Optional[str] = None) -> Path:
        """See [render][.barf]"""
        if handler == self.name:
            handler = 'python'
        return super().get_templates_dir(handler)

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
