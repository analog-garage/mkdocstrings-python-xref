#  Copyright (c) 2022=2023.   Analog Devices Inc.
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

from collections import ChainMap
from pathlib import Path
from typing import Any, List, Mapping, Optional

from griffe import Object
from mkdocstrings.loggers import get_logger
from mkdocstrings_handlers.python.handler import PythonHandler

from .crossref import substitute_relative_crossrefs

__all__ = [
    'PythonRelXRefHandler'
]

logger = get_logger(__name__)

class PythonRelXRefHandler(PythonHandler):
    """Extended version of mkdocstrings Python handler

    * Converts relative cross-references into full references
    * Checks cross-references early in order to produce errors with source location
    """

    handler_name: str = __name__.rsplit('.', 2)[1]

    default_config = dict(
        PythonHandler.default_config,
        relative_crossrefs = False,
        check_crossrefs = True,
    )

    def __init__(self,
                 theme: str,
                 custom_templates: Optional[str] = None,
                 config_file_path: Optional[str] = None,
                 paths: Optional[List[str]] = None,
                 locale: str = "en",
                 **_config: Any,
                 ):
        super().__init__(
            handler = self.handler_name,
            theme = theme,
            custom_templates = custom_templates,
            config_file_path = config_file_path,
            paths = paths,
            locale=locale,
        )

    def render(self, data: Object, config: Mapping[str,Any]) -> str:
        final_config = ChainMap(config, self.default_config) # type: ignore[arg-type]

        if final_config["relative_crossrefs"]:
            checkref = self._check_ref if final_config["check_crossrefs"] else None
            substitute_relative_crossrefs(data, checkref=checkref)

        try:
            return super().render(data, config)
        except Exception:  # pragma: no cover
            print(f"{data.path=}")
            raise

    def get_templates_dir(self, handler: Optional[str] = None) -> Path:
        """See [render][.barf]"""
        if handler == self.handler_name:
            handler = 'python'
        return super().get_templates_dir(handler)

    def _check_ref(self, ref:str) -> bool:
        """Check for existence of reference"""
        try:
            self.collect(ref, {})
            return True
        except Exception:  # pylint: disable=broad-except
            # Only expect a CollectionError but we may as well catch everything.
            return False

