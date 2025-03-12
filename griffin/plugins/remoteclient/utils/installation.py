# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

from griffin.plugins.ipythonconsole import GRIFFIN_KERNELS_VERSION
from griffin.config.base import running_remoteclient_tests
from griffin.plugins.remoteclient import GRIFFIN_REMOTE_VERSION


SERVER_ENV = "griffin-remote"
PACKAGE_NAME = "griffin-remote-services"
SCRIPT_URL = (
    f"https://raw.githubusercontent.com/griffin-ide/"
    f"{PACKAGE_NAME}/master/scripts"
)


def get_installer_command(platform: str) -> str:
    if platform == "win":
        raise NotImplementedError("Windows is not supported yet")

    if running_remoteclient_tests():
        return (
            "\n"  # server should be aready installed in the test environment
        )

    return (
        f'"${{SHELL}}" <(curl -L {SCRIPT_URL}/installer.sh) '
        f'"{GRIFFIN_REMOTE_VERSION}" "{GRIFFIN_KERNELS_VERSION}"'
    )


def get_server_version_command(platform: str) -> str:
    return (
        f"${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} python -c "
        "'import griffin_remote_services as sprs; print(sprs.__version__)'"
    )
