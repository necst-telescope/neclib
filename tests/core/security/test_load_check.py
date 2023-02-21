import astropy.units as u

from neclib.core.security import LoadChecker


class TestLoadChecker:
    def test_cpu_count(self) -> None:
        assert isinstance(LoadChecker.cpu_count, int)
        assert LoadChecker().cpu_count > 0

    def test_cpu_usage(self) -> None:
        usage = LoadChecker().cpu_usage()
        assert usage.unit.is_equivalent(u.percent)
        assert (usage >= 0 * u.percent).all()
        assert (usage <= 100 * u.percent).all()
        assert len(usage) == LoadChecker.cpu_count

    def test_loadavg(self) -> None:
        load = LoadChecker().loadavg()
        assert len(load) == 3
        assert all(0 <= _load for _load in load)
        assert all(_load <= 1 for _load in load)

    def test_memory_available(self) -> None:
        available = LoadChecker().memory_available()
        assert available.unit.is_equivalent(u.byte)
        assert available >= 0 * u.byte

    def test_disk_usage(self) -> None:
        usage = LoadChecker().disk_usage()
        assert usage.unit.is_equivalent(u.percent)
        assert usage >= 0 * u.percent
        assert usage <= 100 * u.percent

    def test_network_amount(self) -> None:
        amount = LoadChecker().network_amount()
        assert amount["sent"].unit.is_equivalent(u.byte / u.s)
        assert amount["recv"].unit.is_equivalent(u.byte / u.s)
        assert amount["sent"] >= 0 * u.byte / u.s
        assert amount["recv"] >= 0 * u.byte / u.s
