# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Griffin Bot
#
# 
# ----------------------------------------------------------------------------

from setuptools import find_packages
from setuptools import setup

from griffin_boilerplate import __version__


setup(
    # See: https://setuptools.readthedocs.io/en/latest/setuptools.html
    name="griffin-boilerplate",
    version=__version__,
    author="Griffin Bot",
    author_email="griffin.python@gmail.com",
    description="Plugin that registers a programmatic custom layout",
    license="MIT license",
    python_requires='>= 3.8',
    install_requires=[
        "qtpy",
        "qtawesome",
        "griffin>=6",
    ],
    packages=find_packages(),
    entry_points={
        "griffin.plugins": [
            "griffin_boilerplate = griffin_boilerplate.griffin.plugin:GriffinBoilerplate"
        ],
    },
    classifiers=[
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
    ],
)
