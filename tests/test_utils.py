import pytest
from remoteFoil.utils import nones, bools, print_table


class TestUtils:
    def test_nones(self):
        for i in range(100):
            assert len(nones(i)) == i
        assert nones(1)[0] is None
        assert type(nones(-10)) is list
        with pytest.raises(TypeError):
            nones('hello')

    def test_bools(self):
        assert bools(1) == 'yes'
        assert bools(0) == 'no'
        assert bools(None) == 'no'
        assert bools(-1) == 'yes'
        assert bools('hello') == 'yes'

    def test_print_table(self, capsys):
        headers = ['#', 'one', 'three', 'giraffe']
        rows = [['1', 'two', 'four', 'monkey'],
                ['2', '+++++++++++++++++++++++++', 'five', '.']]
        sizes = (100, 6, 100, 100)

        expected = '# one    three giraffe \n' \
                   '- ------ ----- ------- \n' \
                   '1 two    four  monkey  \n' \
                   '2 ++++++ five  .       \n' \
                   '  ++++++               \n' \
                   '  ++++++               \n' \
                   '  ++++++               \n' \
                   '  +                    \n'
        print_table(headers, rows, sizes)
        out = capsys.readouterr()
        assert out.out == expected
        with pytest.raises(TypeError):
            print_table(headers, rows)
        with pytest.raises(TypeError):
            print_table(headers)


