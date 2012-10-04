
from flower.core.sync import *

def test_increment():
    i = 0
    i = increment(i)
    assert i == 1

    i = increment(i)
    assert i == 2


def test_decrement():
    i = 0
    i = decrement(i)
    assert i == -1

    i = decrement(i)
    assert i == -2

def test_combine():
    i = 1
    i = decrement(i)
    assert i == 0
    i = increment(i)
    assert i == 1


def test_read():
    i = 10
    v = atomic_read(i)
    assert i == v

def test_compare_and_swap():
    a, b = 1, 2
    a = compare_and_swap(a, b)

    assert a == b

    a, b = 1, 1
    r = compare_and_swap(a, b)
    assert a == 1
