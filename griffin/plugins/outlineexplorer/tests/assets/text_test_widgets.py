# -*- coding: utf-8 -*-
"""
Griffin Editor

This is a temporary script file.
"""


import os
import sys


# %% functions
def d():
    def inner():
        return 2
    return inner


# ---- func 1 and 2

def func1():
    for i in range(3):
        print(i)


def func2():
    if True:
        pass

# ---- other functions

# %%% cell level 2
def a():
    pass

# %%%% cell level 3
def b():
    pass

# %%%%% cell level 4
def c():
    pass

# %%%% cell level 3-1
def func3():
    pass

# %% classes
class Class1:
    def __init__(self):
        super(Class1, self).__init__()
        self.x = 2

    def method3(self):
        pass

    def method2(self):
        pass

    def method1(self):
        pass
