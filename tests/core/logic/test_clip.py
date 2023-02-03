from neclib.core.logic import clip


class TestClip:
    def test_clip(self) -> None:
        assert clip(0.5, 0, 1) == 0.5
        assert clip(-1, 0, 1) == 0
        assert clip(2, 0, 1) == 1
        assert clip(0, 0, 1) == 0
        assert clip(1, 0, 1) == 1
        assert clip(-0.5, -1, 0) == -0.5
        assert clip(1, -1, 0) == 0
        assert clip(-2, -1, 0) == -1
        assert clip(0, -1, 0) == 0
        assert clip(-1, -1, 0) == -1

    def test_clip_by_abs(self) -> None:
        assert clip(50, absmax=5) == 5
        assert clip(-50, absmax=5) == -5
        assert clip(5, absmax=50) == 5
        assert clip(-5, absmax=50) == -5
