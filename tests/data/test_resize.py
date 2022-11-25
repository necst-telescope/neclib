import time

from neclib.data import Resize


class TestResize:
    def test_resize_without_interp(self):
        r = Resize()
        r.push([-4, -3, -2, -1, 0], time.time() - 1)
        r.push([1, 2, 3, 4, 5], time.time())
        r.push([6, 7, 8, 9, 10], time.time())
        assert r.get((0, 5)) == [3.5, 4.5, 5.5, 6.5, 7.5]
        assert r.get((0, 5)) == [3.5, 4.5, 5.5, 6.5, 7.5]

    def test_resize_with_interp(self):
        r = Resize()
        r.push([-4, -3, -2, -1, 0], time.time() - 1)
        r.push([1, 2, 3, 4, 5], time.time())
        r.push([6, 7, 8, 9, 10], time.time())
        assert r.get((0, 5), 3) == [3.5, 5.5, 7.5]
        assert r.get((0, 5), 3) == [3.5, 5.5, 7.5]

    def test_auto_timestamp(self):
        r = Resize()
        r.push([1, 2, 3, 4, 5])
        r.push([6, 7, 8, 9, 10])
        assert r.get((0, 5)) == [3.5, 4.5, 5.5, 6.5, 7.5]
        assert r.get((0, 5)) == [3.5, 4.5, 5.5, 6.5, 7.5]
