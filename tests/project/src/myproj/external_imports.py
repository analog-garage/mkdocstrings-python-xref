#  Copyright (c) 2026.   Analog Devices Inc.
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
"""Test fixture module that imports from an external (stdlib) package.

This module exists to test that [substitute_relative_crossrefs][.] does
not recurse into external package aliases. Importing ``os`` causes griffe
to create Alias members pointing into the ``os`` module tree.
"""

import os
from pathlib import Path

def example() -> Path:
    """Return a path based on [os.getcwd][os.getcwd].

    Uses [Path][.] to wrap the result.
    """
    return Path(os.getcwd())
