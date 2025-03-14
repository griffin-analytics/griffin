#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Project Contributors
#
# Distributed under the terms of the MIT License
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Bootstrap Griffin.

Execute Griffin from source checkout.
"""

# Standard library imports
import argparse
import os
import shutil
import subprocess
import sys
import time
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path

# Local imports
from install_dev_repos import DEVPATH, REPOS, install_repo


# =============================================================================
# ---- Setup logger
# =============================================================================
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('Bootstrap')
logger.addHandler(h)
logger.setLevel('INFO')

time_start = time.time()


# =============================================================================
# ---- Parse command line
# =============================================================================
parser = argparse.ArgumentParser(
    usage="python bootstrap.py [options] [-- griffin_options]",
    epilog="""\
Arguments for Griffin's main script are specified after the --
symbol (example: `python bootstrap.py -- --hide-console`).
Type `python bootstrap.py -- --help` to read about Griffin
options.""")
parser.add_argument('--gui', default=None,
                    help="GUI toolkit: pyqt5, pyside2, pyqt6 or pyside6")
parser.add_argument('--hide-console', action='store_true', default=False,
                    help="Hide parent console window (Windows only)")
parser.add_argument('--safe-mode', dest="safe_mode",
                    action='store_true', default=False,
                    help="Start Griffin with a clean configuration directory")
parser.add_argument('--debug', action='store_true',
                    default=False, help="Run Griffin in debug mode")
parser.add_argument('--filter-log', default='',
                    help="Comma-separated module name hierarchies whose log "
                         "messages should be shown. e.g., "
                         "griffin.plugins.completion,griffin.plugins.editor")
parser.add_argument('--no-install', action='store_true', default=False,
                    help="Do not install Griffin or its subrepos")
parser.add_argument('griffin_options', nargs='*')

args = parser.parse_args()

assert args.gui in (None, "pyqt5", "pyside2", "pyqt6", "pyside6"), (
    "Invalid GUI toolkit option '%s'" % args.gui
)


# =============================================================================
# ---- Install sub repos
# =============================================================================
installed_dev_repo = False
if not args.no_install:
    prev_branch = None
    boot_branch_file = DEVPATH / ".boot_branch.txt"
    if boot_branch_file.exists():
        prev_branch = boot_branch_file.read_text()

    result = subprocess.run(
        ["git", "-C", DEVPATH, "merge-base", "--fork-point", "master"],
        capture_output=True
    )
    branch = "master" if result.stdout else "not master"
    boot_branch_file.write_text(branch)

    logger.info("Previous root branch: %s; current root branch: %s",
                prev_branch, branch)

    if branch != prev_branch:
        logger.info("Detected root branch change to/from master. "
                    "Will reinstall Griffin in editable mode.")
        REPOS[DEVPATH.name]["editable"] = False

    for name in REPOS.keys():
        # Don't install the griffin-remote-services subrepo because it's not
        # necessary on the Griffin side.
        if name != "griffin-remote-services":
            if not REPOS[name]['editable']:
                install_repo(name)
                installed_dev_repo = True
            else:
                logger.info("%s installed in editable mode", name)

if installed_dev_repo:
    logger.info("Restarting bootstrap to pick up installed subrepos")
    if '--' in sys.argv:
        sys.argv.insert(sys.argv.index('--'), '--no-install')
    else:
        sys.argv.append('--no-install')
    result = subprocess.run([sys.executable, *sys.argv])
    sys.exit(result.returncode)

# Local imports
# Must follow install_repo in case Griffin was not originally installed.
from griffin import get_versions

logger.info("Executing Griffin from source checkout")

# Prepare arguments for Griffin's main script
original_sys_argv = sys.argv.copy()
sys.argv = [sys.argv[0]] + args.griffin_options


# =============================================================================
# ---- Update os.environ
# =============================================================================
# Store variable to be used in self.restart (restart Griffin instance)
os.environ['GRIFFIN_BOOTSTRAP_ARGS'] = str(original_sys_argv[1:])

# Start Griffin with a clean configuration directory for testing purposes
if args.safe_mode:
    os.environ['GRIFFIN_SAFE_MODE'] = 'True'

# To activate/deactivate certain things for development
os.environ['GRIFFIN_DEV'] = 'True'

if args.debug:
    # safety check - Griffin config should not be imported at this point
    if "griffin.config.base" in sys.modules:
        sys.exit("ERROR: Can't enable debug mode - Griffin is already imported")
    logger.info("Switching debug mode on")
    os.environ["GRIFFIN_DEBUG"] = "3"
    if len(args.filter_log) > 0:
        logger.info("Displaying log messages only from the "
                    "following modules: %s", args.filter_log)
    os.environ["GRIFFIN_FILTER_LOG"] = args.filter_log
    # this way of interaction suxx, because there is no feedback
    # if operation is successful

# Selecting the GUI toolkit: PyQt5 if installed
if args.gui is None:
    try:
        import PyQt5  # analysis:ignore
        logger.info("PyQt5 is detected, selecting")
        os.environ['QT_API'] = 'pyqt5'
    except ImportError:
        sys.exit("ERROR: No PyQt5 detected!")
else:
    logger.info("Skipping GUI toolkit detection")
    os.environ['QT_API'] = args.gui


# =============================================================================
# ---- Check versions
# =============================================================================
# Checking versions (among other things, this has the effect of setting the
# QT_API environment variable if this has not yet been done just above)
versions = get_versions(reporev=True)
logger.info("Imported Griffin %s - Revision %s, Branch: %s; "
            "[Python %s %dbits, Qt %s, %s %s on %s]",
            versions['griffin'], versions['revision'], versions['branch'],
            versions['python'], versions['bitness'], versions['qt'],
            versions['qt_api'], versions['qt_api_ver'], versions['system'])

# Check that we have the right qtpy version
from griffin.utils import programs
if not programs.is_module_installed('qtpy', '>=1.1.0'):
    sys.exit("ERROR: Your qtpy version is outdated. Please install qtpy "
             "1.1.0 or higher to be able to work with Griffin!")


# =============================================================================
# ---- Execute Griffin
# =============================================================================
if args.hide_console and os.name == 'nt':
    logger.info("Hiding parent console (Windows only)")
    sys.argv.append("--hide-console")  # Windows only: show parent console

# Reset temporary config directory if starting in --safe-mode
if args.safe_mode or os.environ.get('GRIFFIN_SAFE_MODE'):
    from griffin.config.base import get_conf_path  # analysis:ignore
    conf_dir = Path(get_conf_path())
    if conf_dir.is_dir():
        shutil.rmtree(conf_dir)

logger.info("Running Griffin")
from griffin.app import start  # analysis:ignore

time_lapse = time.time() - time_start
logger.info("Bootstrap completed in %s%s",
            time.strftime("%H:%M:%S.", time.gmtime(time_lapse)),
            # gmtime() converts float into tuple, but loses milliseconds
            ("%.4f" % time_lapse).split('.')[1])

start.main()
