from itertools import islice

import astropy.units as u

from neclib.coordinates.observations import (
    GridSpec,
    OTFSpec,
    PSWSpec,
    RadioPointingSpec,
)
from neclib.coordinates.observations.observation_spec_base import (
    ObservationMode,
    TimeKeeper,
)
from neclib.core.units import point, scan


def _mode_id_pairs(spec, n):
    return [(wp.mode, wp.id) for wp in islice(spec.observe(), n)]


def _make_grid_spec():
    return GridSpec(
        relative=True,
        coord_sys="altaz",
        lambda_on=0 * u.deg,
        beta_on=0 * u.deg,
        delta_lambda=1 * u.deg,
        delta_beta=1 * u.deg,
        integ_hot=1 * u.s,
        integ_off=1 * u.s,
        integ_on=1 * u.s,
        load_interval=2 * point,
        off_interval=3 * point,
        n_x=6,
        n_y=1,
        start_x=0 * u.deg,
        start_y=0 * u.deg,
        step_x=1 * u.deg,
        step_y=1 * u.deg,
    )


def _make_psw_spec():
    return PSWSpec(
        relative=True,
        coord_sys="altaz",
        lambda_on=0 * u.deg,
        beta_on=0 * u.deg,
        delta_lambda=1 * u.deg,
        delta_beta=1 * u.deg,
        integ_hot=1 * u.s,
        integ_off=1 * u.s,
        integ_on=1 * u.s,
        load_interval=2 * point,
        off_interval=3 * point,
        n=6,
    )


def test_otf_hot_due_is_deferred_until_next_off(data_dir):
    spec = OTFSpec.from_file(data_dir / "sample_otf.toml")
    spec._hot_time_keeper = TimeKeeper(2 * scan)
    spec._off_time_keeper = TimeKeeper(3 * scan)

    got = _mode_id_pairs(spec, 10)
    expected = [
        (ObservationMode.HOT, "0"),
        (ObservationMode.OFF, "0"),
        (ObservationMode.ON, "0"),
        (ObservationMode.ON, "1"),
        (ObservationMode.ON, "2"),
        (ObservationMode.HOT, "3"),
        (ObservationMode.OFF, "3"),
        (ObservationMode.ON, "3"),
        (ObservationMode.ON, "4"),
        (ObservationMode.ON, "5"),
    ]

    assert got == expected


def test_radio_pointing_scan_hot_due_is_deferred_until_next_off(data_dir):
    spec = RadioPointingSpec.from_file(data_dir / "sample_radio_pointing.toml")
    spec._parameters["method"] = -1
    spec._parameters["n"] = 4
    spec._hot_time_keeper = TimeKeeper(2 * scan)
    spec._off_time_keeper = TimeKeeper(3 * scan)

    got = _mode_id_pairs(spec, 10)
    expected = [
        (ObservationMode.HOT, "0-0"),
        (ObservationMode.OFF, "0-0"),
        (ObservationMode.ON, "0-0"),
        (ObservationMode.ON, "0-1"),
        (ObservationMode.ON, "1-0"),
        (ObservationMode.HOT, "1-1"),
        (ObservationMode.OFF, "1-1"),
        (ObservationMode.ON, "1-1"),
        (ObservationMode.ON, "2-0"),
        (ObservationMode.ON, "2-1"),
    ]

    assert got == expected


def test_grid_hot_due_is_deferred_until_next_off():
    spec = _make_grid_spec()

    got = _mode_id_pairs(spec, 10)
    expected = [
        (ObservationMode.HOT, "HOT@(00,00)"),
        (ObservationMode.OFF, "OFF@(00,00)"),
        (ObservationMode.ON, "(00,00)"),
        (ObservationMode.ON, "(01,00)"),
        (ObservationMode.ON, "(02,00)"),
        (ObservationMode.HOT, "HOT@(03,00)"),
        (ObservationMode.OFF, "OFF@(03,00)"),
        (ObservationMode.ON, "(03,00)"),
        (ObservationMode.ON, "(04,00)"),
        (ObservationMode.ON, "(05,00)"),
    ]

    assert got == expected


def test_psw_hot_due_is_deferred_until_next_off():
    spec = _make_psw_spec()

    got = _mode_id_pairs(spec, 10)
    expected = [
        (ObservationMode.HOT, "0-0"),
        (ObservationMode.OFF, "0-0"),
        (ObservationMode.ON, "0-0"),
        (ObservationMode.ON, "1-0"),
        (ObservationMode.ON, "2-0"),
        (ObservationMode.HOT, "3-0"),
        (ObservationMode.OFF, "3-0"),
        (ObservationMode.ON, "3-0"),
        (ObservationMode.ON, "4-0"),
        (ObservationMode.ON, "5-0"),
    ]

    assert got == expected


def test_otf_off_interval_is_not_advanced_by_hot_due_without_off(data_dir):
    spec = OTFSpec.from_file(data_dir / "sample_otf.toml")
    spec._hot_time_keeper = TimeKeeper(1 * scan)
    spec._off_time_keeper = TimeKeeper(4 * scan)

    got = _mode_id_pairs(spec, 8)
    expected = [
        (ObservationMode.HOT, "0"),
        (ObservationMode.OFF, "0"),
        (ObservationMode.ON, "0"),
        (ObservationMode.ON, "1"),
        (ObservationMode.ON, "2"),
        (ObservationMode.ON, "3"),
        (ObservationMode.HOT, "4"),
        (ObservationMode.OFF, "4"),
    ]

    assert got == expected
