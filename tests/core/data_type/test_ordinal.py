from neclib.core import Ordinal


class TestOrdinal:
    def test_operations(self) -> None:
        assert Ordinal(1) + Ordinal(2) == 3
        assert Ordinal(1) - Ordinal(2) == -1
        assert Ordinal(1) * Ordinal(2) == 2
        assert Ordinal(1) / Ordinal(2) == 0.5
        assert Ordinal(1) // Ordinal(2) == 0
        assert Ordinal(1) % Ordinal(2) == 1
        assert Ordinal(1) ** Ordinal(2) == 1

    def test_operations_with_int(self) -> None:
        assert Ordinal(1) + 2 == 3
        assert Ordinal(1) - 2 == -1
        assert Ordinal(1) * 2 == 2
        assert Ordinal(2) / 2 == 0.5
        assert Ordinal(1) // 2 == 0
        assert Ordinal(1) % 2 == 1
        assert Ordinal(1) ** 2 == 1

    def test_reverse_operations_with_int(self) -> None:
        assert 2 + Ordinal(1) == 3
        assert 2 - Ordinal(1) == 1
        assert 2 * Ordinal(1) == 2
        assert 2 / Ordinal(2) == 1
        assert 2 // Ordinal(1) == 2
        assert 2 % Ordinal(1) == 0
        assert 2 ** Ordinal(1) == 2

    def test_operations_with_float(self) -> None:
        assert Ordinal(1) + 2.0 == 3.0
        assert Ordinal(1) - 2.0 == -1.0
        assert Ordinal(1) * 2.0 == 2.0
        assert Ordinal(2) / 2.0 == 0.5
        assert Ordinal(1) // 2.0 == 0.0
        assert Ordinal(1) % 2.0 == 1.0
        assert Ordinal(1) ** 2.0 == 1.0

    def test_reverse_operations_with_float(self) -> None:
        assert 2.0 + Ordinal(1) == 3.0
        assert 2.0 - Ordinal(1) == 1.0
        assert 2.0 * Ordinal(1) == 2.0
        assert 2.0 / Ordinal(2) == 1.0
        assert 2.0 // Ordinal(1) == 2.0
        assert 2.0 % Ordinal(1) == 0.0
        assert 2.0 ** Ordinal(1) == 2.0

    def test_format(self) -> None:
        assert f"{Ordinal(1)}" == "1st"
        assert f"{Ordinal(2)}" == "2nd"
        assert f"{Ordinal(3)}" == "3rd"
        assert f"{Ordinal(4)}" == "4th"
        assert f"{Ordinal(11)}" == "11th"
        assert f"{Ordinal(12)}" == "12th"
        assert f"{Ordinal(13)}" == "13th"
        assert f"{Ordinal(14)}" == "14th"
        assert f"{Ordinal(21)}" == "21st"
        assert f"{Ordinal(22)}" == "22nd"
        assert f"{Ordinal(23)}" == "23rd"
        assert f"{Ordinal(24)}" == "24th"
        assert f"{Ordinal(101)}" == "101st"
        assert f"{Ordinal(102)}" == "102nd"
        assert f"{Ordinal(103)}" == "103rd"
        assert f"{Ordinal(104)}" == "104th"
        assert f"{Ordinal(111)}" == "111th"
        assert f"{Ordinal(112)}" == "112th"
        assert f"{Ordinal(113)}" == "113th"
        assert f"{Ordinal(114)}" == "114th"
        assert f"{Ordinal(121)}" == "121st"
        assert f"{Ordinal(122)}" == "122nd"
        assert f"{Ordinal(123)}" == "123rd"
        assert f"{Ordinal(124)}" == "124th"
