import astropy.units as u

from neclib.core import get_quantity


class TestGetQuantity:
    def test_single_scalar_value(self) -> None:
        assert get_quantity(1, unit="deg") == 1 * u.deg
        assert get_quantity(1, unit="m/s") == 1 * u.m / u.s

    def test_multiple_scalar_values(self) -> None:
        values = (1, 2.1)
        expected = u.Quantity([1, 2.1], u.deg)
        actual = get_quantity(*values, unit="deg")
        assert (actual.value == expected.value).all()

        values = (1, 2)
        expected = u.Quantity([1, 2], u.m / u.s)
        actual = get_quantity(*values, unit="m/s")
        assert (actual.value == expected.value).all()

    def test_single_array_value(self) -> None:
        assert get_quantity([1], unit="deg") == [1] * u.deg

        values = [1, 2, 3]
        expected = u.Quantity([1, 2, 3], u.m / u.s)
        actual = get_quantity(values, unit="m/s")
        assert (actual.value == expected.value).all()

    def test_multiple_array_values(self) -> None:
        values = ([1, 2.1], [3, 4])
        expected = u.Quantity([[1, 2.1], [3, 4]], u.deg)
        actual = get_quantity(*values, unit="deg")
        assert (actual.value == expected.value).all()

        values = ([1, 2], [3, 4])
        expected = u.Quantity([[1, 2], [3, 4]], u.m / u.s)
        actual = get_quantity(*values, unit="m/s")
        assert (actual.value == expected.value).all()

    def test_single_quantity_value(self) -> None:
        assert get_quantity(1 * u.deg) == 1 * u.deg
        assert get_quantity(1 * u.m / u.s, unit="km/s") == 0.001 * u.km / u.s

    def test_multiple_quantity_values(self) -> None:
        values = (1 * u.deg, 2 * u.deg)
        expected = u.Quantity([1, 2], u.arcmin) * 60
        actual = get_quantity(*values, unit=u.arcmin)
        assert (actual.value == expected.value).all()

        values = (1 * u.m / u.s, 2.1 * u.m / u.s)
        expected = u.Quantity([1, 2.1], u.m / u.s)
        actual = get_quantity(*values)
        assert (actual.value == expected.value).all()

    def test_single_quantity_array_value(self) -> None:
        assert get_quantity([1] * u.deg, unit="arcsec") == [1] * u.arcsec * 3600

        value = (1, 2, 3) * u.m / u.s
        assert (get_quantity(value) == value).all()

    def test_multiple_quantity_array_values(self) -> None:
        values = ([1, 2.1] * u.deg, [3, 4] * u.deg)
        expected = u.Quantity([[1, 2.1], [3, 4]], u.deg) * 60
        actual = get_quantity(*values, unit=u.arcmin)
        assert (actual.value == expected.value).all()

        values = ([1, 2] * u.m / u.s, [3, 4] * u.m / u.s)
        expected = u.Quantity([[1, 2], [3, 4]], unit=u.m / u.s)
        actual = get_quantity(*values)
        assert (actual.value == expected.value).all()
