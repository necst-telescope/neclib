from neclib.utils import update_list


def test_update_list():
    parameter = [1, 2]
    update_list(parameter, 3)
    expected = [2, 3]
    assert parameter == expected
