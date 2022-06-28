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
"""
Implementation of GarpyPythonHandler
"""

from __future__ import annotations

from collections import ChainMap
from pathlib import Path
from typing import Any, List, Optional

from griffe.dataclasses import Object
from mkdocstrings.loggers import get_logger
from mkdocstrings_handlers.python.handler import PythonHandler

from .crossref import substitute_relative_crossrefs

__all__ = [
    'GarpyPythonHandler'
]

logger = get_logger(__name__)

class GarpyPythonHandler(PythonHandler):
    """Extended version of mkdocstrings Python handler
    """

    handler_name: str = __name__.rsplit('.', 2)[1]

    default_config = dict(
        PythonHandler.default_config,
        relative_crossrefs = False,
    )

    def __init__(self,
                 theme: str,
                 custom_templates: Optional[str] = None,
                 config_file_path: Optional[str] = None,
                 paths: Optional[List[str]] = None,
                 **config: Any,
                 ):
        super().__init__(
            handler = self.handler_name,
            theme = theme,
            custom_templates = custom_templates,
            config_file_path = config_file_path,
            paths = paths,
            **config
        )

    def render(self, data: Object, config: dict) -> str:
        final_config = ChainMap(config, self.default_config)

        if final_config["relative_crossrefs"]:
            substitute_relative_crossrefs(data, checkref=self._check_ref)

        return super().render(data, config)

    def get_templates_dir(self, handler: str) -> Path:
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

