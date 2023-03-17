import time

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import FK4, AltAz, SkyCoord, get_body
from astropy.time import Time

from neclib import config
from neclib.coordinates import CoordCalculator

from ..conftest import configured_tester_factory


class TestCoordCalculator(configured_tester_factory("config_default")):
    def test_diffraction_param_type(self) -> None:
        calc = CoordCalculator(location=config.location)
        assert isinstance(calc.obswl, u.Quantity)
        assert isinstance(calc.obsfreq, u.Quantity)
        assert isinstance(calc.relative_humidity, u.Quantity)
        assert isinstance(calc.pressure, u.Quantity)
        assert isinstance(calc.temperature, u.Quantity)

    def test_diffraction_param_update(self) -> None:
        calc = CoordCalculator(location=config.location)
        calc.obswl = 1.0
        calc.obsfreq = 1.0
        calc.relative_humidity = 1.0
        calc.pressure = 1.0
        calc.temperature = 1.0
        assert calc.obswl == 1.0 * u.mm
        assert calc.obsfreq == 1.0 * u.GHz
        assert calc.relative_humidity == 1.0 * u.dimensionless_unscaled
        assert calc.pressure == 1.0 * u.hPa
        assert calc.temperature == 1.0 * u.deg_C

    def test_coordinate_skycoord(self) -> None:
        calc = CoordCalculator(location=config.location)
        now = Time(time.time(), format="unix")

        # No obstime
        coord = calc.coordinate.from_builtins(
            lon=45, lat=-60, unit="deg", frame="fk5"
        ).skycoord
        expected = SkyCoord(45, -60, unit="deg", frame="fk5")
        assert coord.data.lon.to_value("deg") == pytest.approx(
            expected.data.lon.to_value("deg")
        )
        assert coord.data.lat.to_value("deg") == pytest.approx(
            expected.data.lat.to_value("deg")
        )

        # With obstime
        coord = calc.coordinate.from_builtins(
            lon=45, lat=-60, unit="deg", frame="fk5", time=now
        ).skycoord
        expected = SkyCoord(45, -60, unit="deg", frame="fk5", obstime=now)
        assert coord.data.lon.to_value("deg") == pytest.approx(
            expected.data.lon.to_value("deg")
        )
        assert coord.data.lat.to_value("deg") == pytest.approx(
            expected.data.lat.to_value("deg")
        )

    class TestCoordinateTransformTo:
        def test_same_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.coordinate.from_skycoord(coord).transform_to("fk5")
            assert transformed.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg")
            )

        def test_similar_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            now = time.time()
            frame = FK4(obstime=Time(now, format="unix"))
            transformed = calc.coordinate.from_skycoord(coord).transform_to(frame)
            expected = coord.transform_to(frame)
            assert transformed.lon.to_value("deg") != pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") != pytest.approx(
                coord.data.lat.to_value("deg")
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg")
            )

        def test_different_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.coordinate.from_skycoord(coord).transform_to("galactic")
            expected = coord.transform_to("galactic")
            assert transformed.lon.to_value("deg") != pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") != pytest.approx(
                coord.data.lat.to_value("deg")
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg")
            )

        def test_to_altaz_frame(self) -> None:
            now = time.time()
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")

            # Test with obstime as an argument
            _coord = calc.coordinate.from_skycoord(coord)
            _coord = _coord.replicate(time=now)
            transformed = _coord.transform_to("altaz")
            expected = coord.transform_to(
                AltAz(obstime=Time(now, format="unix"), location=config.location)
            )
            assert transformed.lon.to_value("deg") != pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") != pytest.approx(
                coord.data.lat.to_value("deg")
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg")
            )

            # Test with obstime contained in frame object
            _coord = calc.coordinate.from_skycoord(coord)
            _coord = _coord.replicate(time=now)
            transformed = _coord.transform_to(AltAz(obstime=Time(now, format="unix")))
            expected = coord.transform_to(
                AltAz(obstime=Time(now, format="unix"), location=config.location)
            )
            assert transformed.lon.to_value("deg") != pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") != pytest.approx(
                coord.data.lat.to_value("deg")
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg")
            )

        def test_from_altaz_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(
                0,
                0,
                unit="deg",
                frame="altaz",
                location=config.location,
                obstime=Time(time.time(), format="unix"),
            )
            transformed = calc.coordinate.from_skycoord(coord).transform_to("fk5")
            expected = coord.transform_to("fk5")
            assert transformed.lon.to_value("deg") != pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") != pytest.approx(
                coord.data.lat.to_value("deg")
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg")
            )

        def test_from_altaz_to_altaz(self) -> None:
            now = Time(time.time(), format="unix")
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(
                10, 20, unit="deg", frame="altaz", location=config.location, obstime=now
            )
            transformed = calc.coordinate.from_skycoord(coord).transform_to("altaz")
            assert transformed.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg"), abs=1e-10
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg"), abs=1e-10
            )

        def test_altaz_with_no_obstime_is_error(self) -> None:
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="altaz", location=config.location
                )
                calc.coordinate.from_skycoord(coord).transform_to("fk5")
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="fk5", location=config.location
                )
                calc.coordinate.from_skycoord(coord).transform_to("altaz")
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="altaz", location=config.location
                )
                calc.coordinate.from_skycoord(coord).transform_to("altaz")

        def test_frame_name_dialect(self) -> None:
            calc = CoordCalculator(location=config.location)

            # J2000 <-> FK5
            coord = SkyCoord(10, 20, unit="deg", frame="fk5")
            transformed = calc.coordinate.from_skycoord(coord).transform_to("j2000")
            assert transformed.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg")
            )

            # B1950 <-> FK4
            coord = SkyCoord(10, 20, unit="deg", frame="fk4")
            transformed = calc.coordinate.from_skycoord(coord).transform_to("b1950")
            assert transformed.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg")
            )

            # Horizontal <-> AltAz
            now = Time(time.time(), format="unix")
            coord = SkyCoord(
                10, 20, unit="deg", frame="altaz", location=config.location, obstime=now
            )
            transformed = calc.coordinate.from_skycoord(coord).transform_to(
                "horizontal"
            )
            assert transformed.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg"), abs=1e-10
            )
            assert transformed.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg"), abs=1e-10
            )

    class TestToApparentAltAz:
        def test_length(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")

            # Single obstime specified
            coord = SkyCoord(0, 0, unit="deg", frame="fk5", obstime=now)
            transformed = calc.coordinate.from_skycoord(coord).to_apparent_altaz()
            assert coord.size == 1
            assert transformed.size == 1

            # Single obstime specified for multiple coordinates
            coord = SkyCoord([0, 0, 0], [0, 0, 0], unit="deg", frame="fk5", obstime=now)
            transformed = calc.coordinate.from_skycoord(coord).to_apparent_altaz()
            assert coord.size == 3
            assert transformed.shape == (3,)

            # All obstime specified
            coord = SkyCoord(
                [0, 0, 0],
                [0, 0, 0],
                unit="deg",
                frame="fk5",
                obstime=Time(np.r_[now.unix, now.unix, now.unix], format="unix"),
            )
            transformed = calc.coordinate.from_skycoord(coord).to_apparent_altaz()
            assert coord.size == 3
            assert transformed.size == 3

        def test_dont_track_altaz(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time([time.time() + i / 50 for i in range(50)], format="unix")
            coord = SkyCoord(
                [0] * 50,
                [0] * 50,
                unit="deg",
                frame="altaz",
                location=config.location,
                obstime=now,
            )
            transformed = calc.coordinate.from_builtins(
                lon=0, lat=0, frame="altaz", time=now, unit="deg"
            ).to_apparent_altaz()
            assert coord.size == 50
            assert transformed.size == 50
            assert transformed.az.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg")
            )
            assert transformed.alt.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg")
            )

    class TestCartesianOffsetBy:
        def test_same_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            offset = calc.coordinate_delta.from_builtins(
                d_lon=2, d_lat=-2, unit="deg", frame="fk5"
            )

            coord = SkyCoord(45, -60, unit="deg", frame="fk5")
            result = calc.coordinate.from_skycoord(coord).cartesian_offset_by(offset)
            assert result.lon.to_value("deg") == pytest.approx(47)
            assert result.lat.to_value("deg") == pytest.approx(-62)
            assert result.frame.name == "fk5"

            coord = SkyCoord([45, 46], [-60, -59], unit="deg", frame="fk5")
            result = calc.coordinate.from_skycoord(coord).cartesian_offset_by(offset)
            assert result.lon.to_value("deg") == pytest.approx([47, 48])
            assert result.lat.to_value("deg") == pytest.approx([-62, -61])
            assert result.frame.name == "fk5"

        def test_different_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord([45, 46], [60, 59], unit="deg", frame="fk5").galactic
            offset = calc.coordinate_delta.from_builtins(
                d_lon=2, d_lat=-2, unit="deg", frame="fk5"
            )
            result = calc.coordinate.from_skycoord(coord).cartesian_offset_by(offset)
            assert result.lon.to_value("deg") == pytest.approx([47, 48])
            assert result.lat.to_value("deg") == pytest.approx([58, 57])
            assert result.frame.name == "fk5"

        def test_altaz_offset(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord([45, 46], [60, 59], unit="deg", frame="fk5")
            expected = coord.transform_to(AltAz(obstime=now, location=config.location))
            offset = calc.coordinate_delta.from_builtins(
                d_lon=2, d_lat=-2, unit="deg", frame="altaz"
            )
            _coord = calc.coordinate.from_skycoord(coord)
            _coord = _coord.replicate(time=now)
            result = _coord.cartesian_offset_by(offset)
            assert result.frame.name == "altaz"
            assert result.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg") + 2
            )
            assert result.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg") - 2
            )

        def test_offset_of_altaz_coord(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord(
                [45, 46],
                [60, 59],
                unit="deg",
                frame="altaz",
                location=config.location,
                obstime=now,
            )
            offset = calc.coordinate_delta.from_builtins(
                d_lon=2, d_lat=-2, unit="deg", frame="fk5"
            )
            expected = coord.fk5
            result = calc.coordinate.from_skycoord(coord).cartesian_offset_by(offset)
            assert result.frame.name == "fk5"
            assert result.lon.to_value("deg") == pytest.approx(
                expected.data.lon.to_value("deg") + 2
            )
            assert result.lat.to_value("deg") == pytest.approx(
                expected.data.lat.to_value("deg") - 2
            )

        def test_altaz_offset_of_altaz_coord(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord(
                [45, 46],
                [60, 59],
                unit="deg",
                frame="altaz",
                location=config.location,
                obstime=now,
            )
            offset = calc.coordinate_delta.from_builtins(
                d_lon=2, d_lat=-2, unit="deg", frame="altaz"
            )
            result = calc.coordinate.from_skycoord(coord).cartesian_offset_by(offset)
            assert result.frame.name == "altaz"
            assert result.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg") + 2
            )
            assert result.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg") - 2
            )

        def test_offset_for_each(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord([45, 46], [60, 59], unit="deg", frame="fk5")
            offset = calc.coordinate_delta.from_builtins(
                d_lon=[2, 4], d_lat=[-2, 2], unit="deg", frame="fk5"
            )
            _coord = calc.coordinate.from_skycoord(coord)
            _coord = _coord.replicate(time=now)
            result = _coord.cartesian_offset_by(offset)
            assert result.frame.name == "fk5"
            assert result.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg") + [2, 4]
            )
            assert result.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg") + [-2, 2]
            )

        def test_offset_broadcast(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord(45, -60, unit="deg", frame="fk5")
            offset = calc.coordinate_delta.from_builtins(
                d_lon=[2, 4], d_lat=[-2, 2], unit="deg", frame="fk5"
            )
            _coord = calc.coordinate.from_skycoord(coord)
            _coord = _coord.replicate(time=now)
            result = _coord.cartesian_offset_by(offset)
            assert result.frame.name == "fk5"
            assert result.lon.to_value("deg") == pytest.approx(
                coord.data.lon.to_value("deg") + [2, 4]
            )
            assert result.lat.to_value("deg") == pytest.approx(
                coord.data.lat.to_value("deg") + [-2, 2]
            )
