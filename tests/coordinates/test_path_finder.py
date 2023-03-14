from typing import List, Tuple

import astropy.units as u
import numpy as np
import numpy.typing as npt
import pytest

from neclib import config
from neclib.coordinates import PathFinder
from neclib.coordinates.path_finder import CoordinateGenerator

from ..conftest import configured_tester_factory

frames = pytest.mark.parametrize(
    "frame", ["fk5", "fk4", "altaz", "origin=fk5(45deg,-60deg),rotation=10deg"]
)
offset_frames = pytest.mark.parametrize(
    "offset_frame", ["fk5", "fk4", "altaz", "origin=fk5(-45deg,60deg),rotation=-10deg"]
)
scan_frames = pytest.mark.parametrize(
    "scan_frame", ["fk5", "fk4", "altaz", "origin=fk5(45deg,-60deg),rotation=10deg"]
)
target_names = pytest.mark.parametrize("name", ["sun", "M42"])
# The intention of parameter selection:
# - Coordinate Frames
#   - FK5 for time-independent frame
#   - FK4 for time-dependent frame (obstime is in frame attributes)
#   - AltAz for time-dependent and location-specific frame
#   - origin=... for custom expression of offset coordinate
# - Celestial Bodies
#   - Sun for time-dependent target (motion in celestial coordinate is not ignorable)
#   - M42 for time-independent target (proper motion is ignorable)


def stack_results(
    generator: CoordinateGenerator, n: int = 1
) -> Tuple[u.Quantity, u.Quantity, List[float]]:
    az, el, time = [], [], []
    counter, send = 0, False

    while True:
        if (counter >= n) and (not send):
            break

        try:
            coord = generator.send(True) if send else next(generator)
            counter = 0 if send else counter
            send = False
        except StopIteration:
            break

        counter += 1 if coord.context.infinite else 0
        send = coord.context.waypoint and (counter >= n)

        az = np.r_[az, coord.az]
        el = np.r_[el, coord.el]
        time.extend(coord.time)

    return u.Quantity(az), u.Quantity(el), time


def get_derivative(
    array: npt.ArrayLike, coord: npt.ArrayLike, order: int = 1
) -> Tuple[np.ndarray, np.ndarray]:
    array, coord = np.asanyarray(array), np.asanyarray(coord)
    _derivative = np.diff(array, 1) / np.diff(coord, 1)
    _coord = (coord[1:] + coord[:-1]) / 2
    if order == 1:
        return _derivative, _coord
    elif order > 1:
        return get_derivative(_derivative, _coord, order - 1)
    else:
        raise ValueError(f"order must be >= 1; got {order}")


class TestPathFinder(configured_tester_factory("config_default")):
    class TestTrack:
        @target_names
        def test_name_query(self, name: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.track(name)

            n_cmd_per_section = pf.command_group_duration_sec * pf.command_freq
            az, el, time = stack_results(generator, 10)
            assert az.shape == el.shape == (10 * n_cmd_per_section,)
            assert len(time) == 10 * n_cmd_per_section

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @target_names
        @offset_frames
        def test_name_query_with_offset(self, name: str, offset_frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.track(name, offset=(1, 2, offset_frame), unit="deg")

            n_cmd_per_section = pf.command_group_duration_sec * pf.command_freq
            az, el, time = stack_results(generator, 10)
            assert az.shape == el.shape == (10 * n_cmd_per_section,)
            assert len(time) == 10 * n_cmd_per_section

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @frames
        def test_coord(self, frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.track(45, 60, frame, unit="deg")

            n_cmd_per_section = pf.command_group_duration_sec * pf.command_freq
            az, el, time = stack_results(generator, 10)
            assert az.shape == el.shape == (10 * n_cmd_per_section,)
            assert len(time) == 10 * n_cmd_per_section

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @frames
        @offset_frames
        def test_coord_with_offset(self, frame: str, offset_frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.track(45, 60, frame, unit="deg", offset=(1, 2, offset_frame))

            n_cmd_per_section = pf.command_group_duration_sec * pf.command_freq
            az, el, time = stack_results(generator, 10)
            assert az.shape == el.shape == (10 * n_cmd_per_section,)
            assert len(time) == 10 * n_cmd_per_section

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        def test_offset_without_unit_is_error(self) -> None:
            pf = PathFinder(config.location)
            with pytest.raises(ValueError):
                generator = pf.track("sun", offset=(1, 2, "fk5"))
                next(generator)

    class TestLinear:
        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @target_names
        @scan_frames
        def test_name_query(self, name: str, scan_frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                name,
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @target_names
        @offset_frames
        @scan_frames
        def test_name_query_with_offset(
            self, name: str, offset_frame: str, scan_frame: str
        ) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                name,
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
                offset=(1, 2, offset_frame),
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @frames
        @scan_frames
        def test_reference_target(self, frame: str, scan_frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                45,
                60,
                frame,
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @frames
        @offset_frames
        @scan_frames
        def test_reference_target_with_offset(
            self, frame: str, offset_frame: str, scan_frame: str
        ) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                45,
                60,
                frame,
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
                offset=(1, 2, offset_frame),
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @scan_frames
        def test_absolute_position(self, scan_frame: str) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()

        @pytest.mark.xfail(
            reason="Jump in speed causes outlier in acceleration, reason unknown.",
            raises=AssertionError,
        )
        @scan_frames
        @offset_frames
        def test_absolute_position_with_offset(
            self, offset_frame: str, scan_frame: str
        ) -> None:
            pf = PathFinder(config.location)
            generator = pf.linear(
                start=(-1, 0),
                stop=(1, 1),
                scan_frame=scan_frame,
                speed=0.1,
                unit="deg",
                margin=0.1,
                offset=(1, 2, offset_frame),
            )

            az, el, time = stack_results(generator, 10)

            v_az, _ = get_derivative(az, time, 1)
            v_el, _ = get_derivative(el, time, 1)
            assert np.isfinite(v_az).all()
            assert np.isfinite(v_el).all()
            assert (abs(v_az - np.mean(v_az)) <= np.std(v_az) * 10).all()
            assert (abs(v_el - np.mean(v_el)) <= np.std(v_el) * 10).all()
            a_az, _ = get_derivative(az, time, 2)
            a_el, _ = get_derivative(el, time, 2)
            assert np.isfinite(a_az).all()
            assert np.isfinite(a_el).all()
            assert (abs(a_az - np.mean(a_az)) <= np.std(a_az) * 10).all()
            assert (abs(a_el - np.mean(a_el)) <= np.std(a_el) * 10).all()
            dt = np.diff(time)
            assert (dt >= 0).all()
