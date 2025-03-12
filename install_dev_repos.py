#!/usr/bin/env python3
#
# Copyright © Griffin Project Contributors
# 
#

"""
Helper script for installing griffin and external-deps locally in editable mode.
"""

import argparse
from importlib.metadata import PackageNotFoundError, distribution
from json import loads
from logging import Formatter, StreamHandler, getLogger
import os
from pathlib import Path
from subprocess import check_output
import sys

from packaging.requirements import Requirement

# Remove current/script directory from sys.path[0] if added by the Python
# invocation, otherwise Griffin's install status may be incorrectly determined.
SYS_PATH_0 = Path(sys.path[0]).resolve()
if SYS_PATH_0 in (Path(__file__).resolve().parent, Path.cwd()):
    sys.path.pop(0)

DEVPATH = Path(__file__).resolve().parent
DEPS_PATH = DEVPATH / 'external-deps'
BASE_COMMAND = [sys.executable, '-m', 'pip', 'install', '--no-deps']

REPOS = {}
for p in [DEVPATH] + list(DEPS_PATH.iterdir()):
    if (
        p.name.startswith('.')
        or not p.is_dir()
        and not ((p / 'setup.py').exists() or (p / 'pyproject.toml').exists())
    ):
        continue

    try:
        dist = distribution(p.name)
    except PackageNotFoundError:
        dist = None
        editable = None
    else:
        direct_url = dist.read_text('direct_url.json')
        if direct_url:
            editable = (
                loads(direct_url).get('dir_info', {}).get('editable', False)
            )
        else:
            editable = (p == dist._path or p in dist._path.parents)

        # This fixes detecting that PyLSP was installed in editable mode under
        # some scenarios.
        # Fixes griffin-ide/griffin#19712
        if p.name == 'python-lsp-server':
            for f in dist.files:
                if 'editable' in f.name:
                    editable = True
                    break

    REPOS[p.name] = {'repo': p, 'dist': dist, 'editable': editable}

# ---- Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('InstallDevRepos')
logger.addHandler(h)
logger.setLevel('INFO')


def get_python_lsp_version():
    """Get current version to pass it to setuptools-scm."""
    req_file = DEVPATH / 'requirements' / 'main.yml'
    with open(req_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'python-lsp-server' not in line:
                continue
            line = line.split('-')[-1]
            specifiers = Requirement(line).specifier
            break
        else:
            return "0.0.0"

    for specifier in specifiers:
        if "=" in specifier.operator:
            return specifier.version
    else:
        return "0.0.0"


def install_repo(name, not_editable=False):
    """
    Install a single repo from source located in griffin/external-deps, ignoring
    dependencies, in standard or editable mode.

    Parameters
    ----------
    name : str
        Must be 'griffin' or the distribution name of a repo in
        griffin/external-deps.
    not_editable : bool (False)
        Install repo in standard mode (True) or editable mode (False).
        Editable mode uses pip's `-e` flag.

    """
    try:
        repo_path = REPOS[name]['repo']
    except KeyError:
        logger.warning('Distribution %r not valid. Must be one of %s',
                       name, set(REPOS.keys()))
        return

    install_cmd = BASE_COMMAND.copy()

    # PyLSP requires pretend version
    env = None
    if name == 'python-lsp-server':
        env = {**os.environ}
        env.update(
            {'SETUPTOOLS_SCM_PRETEND_VERSION': get_python_lsp_version()})

    if not_editable:
        mode = 'standard'
    else:
        # Add edit flag to install command
        install_cmd.append('-e')
        mode = 'editable'

    logger.info('Installing %r from source in %s mode.', name, mode)
    install_cmd.append(repo_path.as_posix())
    check_output(install_cmd, env=env)


def main(install=tuple(REPOS.keys()), no_install=tuple(), **kwargs):
    """
    Install all subrepos from source.

    Parameters
    ----------
    install : iterable (griffin and all repos in griffin/external-deps)
        Distribution names of repos to be installed from griffin/external-deps.
    no_install : iterable ()
        Distribution names to exclude from install.
    **kwargs :
        Keyword arguments passed to `install_repo`.

    """
    _install = set(install) - set(no_install)
    for repo in _install:
        install_repo(repo, **kwargs)


if __name__ == '__main__':
    # ---- Parse command line
    parser = argparse.ArgumentParser(
        usage="python install_dev_repos.py [options]")
    parser.add_argument(
        '--install', nargs='+',
        default=REPOS.keys(),
        help="Space-separated list of distribution names to install, e.g. "
             "qtconsole griffin-kernels. If option not provided, then all of "
             "the repos in griffin/external-deps are installed"
    )
    parser.add_argument(
        '--no-install', nargs='+', default=[],
        help="Space-separated list of distribution names to exclude from "
             "install. Default is empty list."
    )
    parser.add_argument(
        '--not-editable', action='store_true', default=False,
        help="Install in standard mode, not editable mode."
    )

    args = parser.parse_args()

    # ---- Install repos locally
    main(**vars(args))
