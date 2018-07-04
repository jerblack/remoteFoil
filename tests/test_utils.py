import pytest
from req.utils import nones, bools, print_table

def test_nones():
    for i in range(100):
        assert len(nones(i)) == i
    assert nones(1)[0] is None
    assert type(nones(-10)) is list
    with pytest.raises(TypeError):
        nones('hello')

def test_bools():
    assert bools(1) == 'yes'
    assert bools(0) == 'no'
    assert bools(None) == 'no'
    assert bools(-1) == 'yes'


def test_print_table():
    headers = ['#', 'one', 'three', 'giraffe']
    data = [['1', 'two', 'four', 'monkey'],
            ['2', '+++++++++++++++++++++++++', 'five', '.']]
    sizes = (4, 6, 6, 10)
    pass