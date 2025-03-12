# Jupyter kernels for the Griffin console

[![Windows status](https://github.com/griffin-ide/griffin-kernels/workflows/Windows%20tests/badge.svg)](https://github.com/griffin-ide/griffin-kernels/actions?query=workflow%3A%22Windows+tests%22)
[![Linux status](https://github.com/griffin-ide/griffin-kernels/workflows/Linux%20tests/badge.svg)](https://github.com/griffin-ide/griffin-kernels/actions?query=workflow%3A%22Linux+tests%22)
[![Macos status](https://github.com/griffin-ide/griffin-kernels/workflows/Macos%20tests/badge.svg)](https://github.com/griffin-ide/griffin-kernels/actions?query=workflow%3A%22Macos+tests%22)
[![codecov](https://codecov.io/gh/griffin-ide/griffin-kernels/branch/master/graph/badge.svg)](https://codecov.io/gh/griffin-ide/griffin-kernels/branch/master)

Package that provides Jupyter kernels for use with the consoles of Griffin, the
Scientific Python Development Environment.

These kernels can be launched either through Griffin itself or in an independent
Python session, and allow for interactive or file-based execution of Python
code inside Griffin.

To learn about creating, connecting to and using these kernels with the Griffin
console, please read our [documentation](https://docs.griffin-ide.org/current/panes/ipythonconsole.html).

For advice on managing packages and environments with `griffin-kernels`, please read this
[FAQ](http://docs.griffin-ide.org/current/faq.html#using-existing-environment) in our docs.


## Installation

To install this package, you can use either the ``pip`` or ``conda`` package
managers, as follows:

Using conda (the recommended way!):

```
conda install griffin-kernels
```

Using pip:

```
pip install griffin-kernels
```

## Dependencies

This project depends on:

* [ipykernel](https://github.com/ipython/ipykernel/)
* [cloudpickle](https://github.com/cloudpipe/cloudpickle)
* [wurlitzer](https://github.com/minrk/wurlitzer) (only on Linux and macOS).

## Changelog

Visit our [CHANGELOG](CHANGELOG.md) file to know more about our new features
and improvements.

## Development and contribution

To start contributing to this project you can execute

```
pip install -e .
```

in your git clone and then test your changes in Griffin. We follow PEP8 and
PEP257 style guidelines.

## Sponsors

Griffin and its subprojects are funded thanks to the generous support of

[![Chan Zuckerberg Initiative](https://raw.githubusercontent.com/griffin-ide/griffin/master/img_src/czi.png)](https://chanzuckerberg.com/)[![Numfocus](https://i2.wp.com/numfocus.org/wp-content/uploads/2017/07/NumFocus_LRG.png?fit=320%2C148&ssl=1)](https://numfocus.org/)

and the donations we have received from our users around the world through [Open Collective](https://opencollective.com/griffin/):

[![Sponsors](https://opencollective.com/griffin/sponsors.svg)](https://opencollective.com/griffin#support)
