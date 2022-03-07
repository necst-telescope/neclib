from neclib.utils import update_list


def test_update_list():
    list_ = [1, 2]
    update_list(list_, 3)
    expected = [2, 3]
    assert list_ == expected
