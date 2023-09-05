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
"""Integration test for python_xref handler"""

import os
import re
import subprocess as sp
import sys
from os import PathLike
from pathlib import Path
from typing import Dict, List, Tuple

import bs4

this_dir = Path(__file__).parent

test_project_dir = this_dir.joinpath('project').absolute()
test_project_mkdocs = test_project_dir.joinpath('mkdocs.yml')
bar_src_file = test_project_dir.joinpath('src', 'myproj', 'bar.py')


def check_autorefs(autorefs: List[bs4.Tag], cases: Dict[Tuple[str,str],str] ) -> None:
    """
    Verify autorefs contain expected cases

    Arguments:
        autorefs: list of autoref tags parsed from HTML
        cases: mapping from (<location>,<title>) to generated reference tag
            where <location? is the qualified name of the object whose doc string
            contains the cross-reference, and <title> is the text in the cross-reference.
    """
    cases = cases.copy()
    for autoref in autorefs:
        curid = autoref.find_previous(id=True).attrs['id']
        text = autoref.string
        href = autoref.attrs['href']
        expected_href = cases.get((curid, text))
        if expected_href:
            assert href == expected_href
            cases.pop((curid, text))

    assert len(cases) == 0


def test_integration(tmpdir: PathLike) -> None:
    """An integration test that runs mkdocs on a tiny sample project and
    grovels the generated HTML to see that the links were resolved.
    """

    site_dir = Path(tmpdir).joinpath('site')
    mkdocs_cmd = [
        'mkdocs',
        'build',
        '-f',
        str(test_project_mkdocs),
        '-d',
        str(site_dir)
    ]
    result = sp.run(mkdocs_cmd, stdout=sp.PIPE, stderr=sp.PIPE, encoding='utf8', check=False)

    assert result.returncode == 0

    m = re.search(
        r"WARNING.*file://(/.*/myproj/bar.py):(\d+):\s*\n\s*Cannot load reference '(.*)'",
        result.stderr
    )
    assert m is not None
    if os.path.sep == '/':
        assert m[1] == str(bar_src_file)
    assert m[3] == 'myproj.bar.bad'
    if sys.version_info >= (3,8):
        # Source location not accurate in python 3.7
        bad_line = int(m[2])
        bar_lines = bar_src_file.read_text().splitlines()
        assert '[bad]' in bar_lines[bad_line - 1]

    bar_html = site_dir.joinpath('bar', 'index.html').read_text()
    bar_bs = bs4.BeautifulSoup(bar_html, 'html.parser')

    autorefs: List[bs4.Tag] = bar_bs.find_all('a', attrs=['autorefs'])
    assert len(autorefs) >= 5

    check_autorefs(
        autorefs,
        {
            ('myproj.bar.Bar', 'bar') : '#myproj.bar.Bar.bar',
            ('myproj.bar.Bar.bar' , 'Bar') : '#myproj.bar.Bar',
            ('myproj.bar.Bar.bar', 'foo') : '#myproj.bar.Bar.foo',
            ('myproj.bar.Bar.bar', 'func') : '#myproj.bar.func',
            ('myproj.bar.Bar.foo', 'Foo.foo') : '../foo/#myproj.foo.Foo.foo',
            ('myproj.bar.func', 'bar') : '#myproj.bar'
        }
    )

    baz_html = site_dir.joinpath('pkg-baz', 'index.html').read_text()
    baz_bs = bs4.BeautifulSoup(baz_html, 'html.parser')

    autorefs = baz_bs.find_all('a', attrs=['autorefs'])
    assert len(autorefs) >= 1

    check_autorefs(
        autorefs,
        {
            ('myproj.pkg.baz', 'func') : '../pkg/#myproj.pkg.func',
        }
    )


