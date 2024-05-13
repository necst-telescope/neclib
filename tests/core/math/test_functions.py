from neclib.core.math import Functions


class TestFunctions:
    def test_normal(self) -> None:
        assert abs(Functions.Normal(0, 1)(-1) - 0.24197072451914337) < 1e-12
        assert abs(Functions.Normal(0, 1)(0) - 0.3989422804014327) < 1e-12
        assert abs(Functions.Normal(0, 1)(1) - 0.24197072451914337) < 1e-12

    def test_sigmoid(self) -> None:
        assert abs(Functions.Sigmoid(0, 1)(-1) - 0.2689414213699951) < 1e-12
        assert abs(Functions.Sigmoid(0, 1)(0) - 0.5) < 1e-12
        assert abs(Functions.Sigmoid(0, 1)(1) - 0.7310585786300049) < 1e-12
