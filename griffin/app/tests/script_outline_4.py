# Taken from the following comment:
# https://github.com/griffin-ide/griffin/issues/16406#issuecomment-917992317
#
# This helps to test a regression for issue griffin-ide/griffin#16406

import logging


def some_function():
    logging.info('Some message')


class SomeClass:
    def __init__(self):
        pass

    def some_method(self):
        pass
