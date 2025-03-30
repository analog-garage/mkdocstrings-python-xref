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
"""This is another module.

This is a [bad][.] reference.
"""

from .foo import Foo

class Bar(Foo):
    """See [bar][.] method."""

    def bar(self) -> None:
        """This is in the [Bar][(c)] class.
        Also see the [foo][^.] method and the [func][(m).] function.
        """

    def foo(self) -> None:
        """Overrides [Foo.foo][^^^.foo.]"""


def func() -> None:
    """This is a function in the [bar][(m)] module."""


class Bad:
    """More bad references"""
    def bad_ref_leading_space(self) -> None:
        """

        This is a [bad][.] reference with leading space
        """
