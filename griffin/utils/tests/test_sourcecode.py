# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 

"""Tests for sourcecode.py"""

import os
import sys

import pytest

from griffin.utils import sourcecode


def test_normalize_eols():
    text = "a\nb\r\nc\rd"
    assert sourcecode.normalize_eols(text) == "a\nb\nc\nd"


def test_get_primary_at():
    code = 'import functools\nfunctools.partial'
    assert sourcecode.get_primary_at(code, len(code)) == 'functools.partial'


def test_get_identifiers():
    code = 'import functools\nfunctools.partial'
    assert set(sourcecode.get_identifiers(code)) == set(['import', 'functools',
                                                         'functools.partial'])


def test_split_source():
    code = 'import functools\nfunctools.partial'
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']
    code = code.replace('\n', '\r\n')
    assert sourcecode.split_source(code) == ['import functools', 'functools.partial']


def test_path_components():
    if not os.name == 'nt':
        path_components0 = ['', '', 'documents', 'test', 'test.py']
    else:
        path_components0 = ['c:', '', 'documents', 'test', 'test.py']
    path0 = os.path.join(*path_components0)
    assert sourcecode.path_components(path0) == path_components0


def test_differentiate_prefix():
    if not os.name == 'nt':
        path_components0 = ['','','documents','test','test.py']
        path_components1 = ['','','documents','projects','test','test.py']
    else:
        path_components0 = ['c:','','documents','test','test.py']
        path_components1 = ['c:','','documents','projects','test','test.py']
    diff_path0 = os.path.join(*['test'])
    diff_path1 = os.path.join(*['projects','test'])
    assert sourcecode.differentiate_prefix(
                        path_components0, path_components1) ==  diff_path0
    assert sourcecode.differentiate_prefix(
                        path_components1, path_components0) ==  diff_path1

def test_get_same_name_files():
    files_path_list = []
    if not os.name == 'nt':
        fname0 = os.path.join(*['','','documents','test','test.py'])
        files_path_list.append(fname0)
        fname1 = os.path.join(*['','','documents','projects','test','test.py'])
        files_path_list.append(fname1)
        same_name_files = [['','','documents','test','test.py'],
                           ['','','documents','projects','test','test.py']]
    else:
        fname0 = os.path.join(*['c:','','documents','test','test.py'])
        files_path_list.append(fname0)
        fname1 = os.path.join(*['c:','','documents','projects','test','test.py'])
        files_path_list.append(fname1)
        same_name_files = [['c:','','documents','test','test.py'],
                           ['c:','','documents','projects','test','test.py']]
        assert sourcecode.get_same_name_files(files_path_list
                                              ,'test.py') == same_name_files

def test_shortest_path():
    if not os.name == 'nt':
        files_path_list =[['','','documents','test','test.py'],
                          ['','','documents','projects','test','test.py']]
        shortest_path = os.path.join(*['','','documents','test','test.py'])
    else:
        files_path_list =[['c:','','documents','test','test.py'],
                          ['c:','','documents','projects','test','test.py']]
        shortest_path = os.path.join(*['c:','','documents','test','test.py'])
    assert sourcecode.shortest_path(files_path_list) == shortest_path


def test_disambiguate_fname():
    files_path_list = []
    if not os.name == 'nt':
        fname0 = os.path.join(*['','','documents','test','test.py'])
        files_path_list.append(fname0)
        fname1 = os.path.join(*['','','documents','projects','test','test.py'])
        files_path_list.append(fname1)
    else:
        fname0 = os.path.join(*['c:','','documents','test','test.py'])
        files_path_list.append(fname0)
        fname1 = os.path.join(*['c:','','documents','projects','test','test.py'])
        files_path_list.append(fname1)
    title0 = 'test.py - ' + os.path.join(*['test'])
    title1 = 'test.py - ' + os.path.join(*['projects','test'])
    assert sourcecode.disambiguate_fname(files_path_list, fname0) == title0
    assert sourcecode.disambiguate_fname(files_path_list, fname1) == title1


def test_get_eol_chars():
    eol_chars = sourcecode.get_eol_chars('foo\r\n')
    assert eol_chars == '\r\n'


def test_get_eol_chars_no_eol():
    eol_chars = sourcecode.get_eol_chars('foo')

    if os.name == 'nt':
        assert eol_chars == "\r\n"
    elif sys.platform.startswith('linux'):
        assert eol_chars == "\n"
    elif sys.platform == 'darwin':
        assert eol_chars == "\r"


if __name__ == '__main__':
    pytest.main()

