import numpy as np
from neclib.utils import AzElData, ParameterList


class TestParameterList:
    def test_init(self):
        assert ParameterList() == ParameterList([])
        assert ParameterList(range(5)) == ParameterList([0, 1, 2, 3, 4])
        assert ParameterList([1, 2])[1] == 2

    def test_new(self):
        assert len(ParameterList.new(5)) == 5
        assert ParameterList.new(2, 0) == ParameterList([0, 0])

    def test_default_to_nan(self):
        assert np.isnan(ParameterList.new(1))

    def test_push(self):
        list_ = ParameterList.new(3, 0)
        list_.push(1)
        assert list_ == ParameterList([0, 0, 1])
        list_.push(2)
        assert list_ == ParameterList([0, 1, 2])

    def test_copy(self):
        original = ParameterList([1, 2])
        copied = original.copy()
        assert isinstance(copied, ParameterList)
        copied.push(3)
        assert copied[1] == 3
        assert original[1] != 3

    def test_map(self):
        original = ParameterList([1, 2])
        assert original.map(lambda x: x + 1) == ParameterList([2, 3])
        assert original.map(lambda x: 2 * x) == ParameterList([2, 4])

    def test_equality(self):
        assert ParameterList([1, 2]) == ParameterList([1, 2])
        assert ParameterList([1, 2]) != ParameterList([2, 1])
        list_ = [0, 1, 2]
        assert ParameterList(list_) == list_
        assert list_ == ParameterList(list_)


class TestAzElData:
    def test_fields(self):
        assert list(AzElData().__dict__.keys()) == ["az", "el"]

    def test_value_assignment(self):
        data = AzElData(az=[1, 2, 3], el=[4, 5, 6])
        data.az[2] = 300
        assert data.az == [1, 2, 300]
