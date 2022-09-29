from pathlib import Path
from typing import List, Tuple, Union

import astropy.constants as const
import astropy.units as u
import pytest
from astropy.coordinates import AltAz, EarthLocation, FK5, SkyCoord, get_body
from astropy.time import Time

from neclib.coordinates import CoordCalculator
from neclib.parameters import PointingError
from neclib.typing import QuantityValue

obstime = pytest.mark.parametrize(
    "obstime", [1662697435.261011, Time(1662697435.261011, format="unix")]
)
temperature = pytest.mark.parametrize(
    "temperature", [290 << u.K, (290 << u.K).to("deg_C", equivalencies=u.temperature())]
)
obs_spectrum = pytest.mark.parametrize(
    "obs_spectrum", [{"obsfreq": 230 << u.GHz}, {"obswl": const.c / (230 << u.GHz)}]
)


Coord = Union[float, List[float]]


class ExpectedValue:
    @staticmethod
    def parse_config(**kwargs) -> None:
        obstime = kwargs.get("obstime")
        obstime = obstime if isinstance(obstime, Time) else Time(obstime, format="unix")

        obswl = kwargs.get("obswl", None)
        obsfreq = kwargs.get("obsfreq", None)
        obswl = obswl if obsfreq is None else const.c / obsfreq

        temperature = kwargs.get("temperature", None)
        temperature = (
            temperature
            if temperature is None
            else temperature.to("deg_C", equivalencies=u.temperature())
        )
        return {
            "location": kwargs.get("location"),
            "obstime": obstime,
            "pressure": kwargs.get("pressure", None),
            "temperature": temperature,
            "humidity": kwargs.get("humidity", None),
            "obswl": obswl,
            "pointing_param_path": kwargs.get("pointing_param_path", None),
        }

    @staticmethod
    def get_altaz_frame(
        location: EarthLocation,
        obstime: Time,
        pressure: u.Quantity = None,
        temperature: u.Quantity = None,
        humidity: float = None,
        obswl: u.Quantity = None,
        **kwargs
    ) -> AltAz:
        return AltAz(
            location=location,
            obstime=obstime,
            pressure=pressure,
            temperature=temperature,
            relative_humidity=humidity,
            obswl=obswl,
        )

    @staticmethod
    def pointing_error_correction(
        pointing_param_path: Path, az: QuantityValue, el: QuantityValue, **kwargs
    ) -> Tuple[Coord, Coord]:
        corrector = PointingError.from_file(pointing_param_path)
        return corrector.refracted2apparent(az, el)

    @classmethod
    def to_altaz(cls, coord: SkyCoord, **kwargs) -> Tuple[Coord, Coord]:
        altaz = coord.transform_to(cls.get_altaz_frame(**kwargs))

        pointing_param_path = kwargs.get("pointing_param_path", None)
        if pointing_param_path is None:
            return altaz.az.deg, altaz.alt.deg

        az, el = cls.pointing_error_correction(
            pointing_param_path, az=altaz.az, el=altaz.alt
        )
        return az.to_value("deg"), el.to_value("deg")

    @classmethod
    def get_solar_system_body(cls, name: str, **kwargs) -> Tuple[Coord, Coord]:
        kwargs = cls.parse_config(**kwargs)
        coord = get_body(name, kwargs["obstime"])
        return cls.to_altaz(coord, **kwargs)

    @classmethod
    def get_celestial_body(cls, name: str, **kwargs) -> Tuple[Coord, Coord]:
        kwargs = cls.parse_config(**kwargs)
        coord = SkyCoord.from_name(name)
        return cls.to_altaz(coord, **kwargs)

    @classmethod
    def get_converted_coord(
        cls,
        lon: QuantityValue,
        lat: QuantityValue,
        frame: str,
        unit: str = None,
        **kwargs
    ) -> Tuple[Coord, Coord]:
        kwargs = cls.parse_config(**kwargs)
        coord = SkyCoord(lon, lat, frame=frame, unit=unit)
        return cls.to_altaz(coord, **kwargs)


class TestCoordCalculator:

    location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    pressure = 850 << u.hPa
    humidity = 0.5

    @obstime
    def test_get_altaz_by_name_no_weather(self, data_dir, obstime):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pointing_param_path": pointing_param_path,
        }

        bodies = [
            ("sun", ExpectedValue.get_solar_system_body("sun", **config)),
            ("RCW38", ExpectedValue.get_celestial_body("RCW38", **config)),
        ]
        calc = CoordCalculator(self.location, pointing_param_path)
        for body, (az_deg, el_deg) in bodies:
            az, el, _ = calc.get_altaz_by_name(body, obstime)
            assert az.to_value("deg") == pytest.approx(az_deg)
            assert el.to_value("deg") == pytest.approx(el_deg)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz_by_name_solar_system(
        self, data_dir, obstime, temperature, obs_spectrum
    ):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pressure": self.pressure,
            "temperature": temperature,
            "humidity": self.humidity,
            "pointing_param_path": pointing_param_path,
            **obs_spectrum,
        }
        bodies = [
            ("sun", ExpectedValue.get_solar_system_body("sun", **config)),
            ("moon", ExpectedValue.get_solar_system_body("moon", **config)),
            ("mercury", ExpectedValue.get_solar_system_body("mercury", **config)),
            ("venus", ExpectedValue.get_solar_system_body("venus", **config)),
            ("mars", ExpectedValue.get_solar_system_body("mars", **config)),
            ("jupiter", ExpectedValue.get_solar_system_body("jupiter", **config)),
            ("saturn", ExpectedValue.get_solar_system_body("saturn", **config)),
            ("uranus", ExpectedValue.get_solar_system_body("uranus", **config)),
            ("neptune", ExpectedValue.get_solar_system_body("neptune", **config)),
        ]
        calc = CoordCalculator(
            self.location,
            pointing_param_path,
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for body, (az_deg, el_deg) in bodies:
            az, el, _ = calc.get_altaz_by_name(body, obstime)
            assert az.to_value("deg") == pytest.approx(az_deg)
            assert el.to_value("deg") == pytest.approx(el_deg)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz_by_name_other_body(
        self, data_dir, obstime, temperature, obs_spectrum
    ):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pressure": self.pressure,
            "temperature": temperature,
            "humidity": self.humidity,
            "pointing_param_path": pointing_param_path,
            **obs_spectrum,
        }
        bodies = [
            ("IRC+10216", ExpectedValue.get_celestial_body("IRC+10216", **config)),
            ("RCW38", ExpectedValue.get_celestial_body("RCW38", **config)),
        ]
        calc = CoordCalculator(
            self.location,
            pointing_param_path,
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for body, (az_deg, el_deg) in bodies:
            az, el, _ = calc.get_altaz_by_name(body, obstime)
            assert az.to_value("deg") == pytest.approx(az_deg)
            assert el.to_value("deg") == pytest.approx(el_deg)

    def test_get_altaz_by_name_multi_time(self, data_dir):
        obstime = [1662697435.261011, 1662697445.261011]
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pointing_param_path": pointing_param_path,
        }
        bodies = [
            ("IRC+10216", ExpectedValue.get_celestial_body("IRC+10216", **config)),
            ("sun", ExpectedValue.get_solar_system_body("sun", **config)),
        ]
        calc = CoordCalculator(self.location, pointing_param_path)
        for body, (az_deg, el_deg) in bodies:
            az, el, _ = calc.get_altaz_by_name(body, obstime)
            assert az.to_value("deg") == pytest.approx(az_deg)
            assert el.to_value("deg") == pytest.approx(el_deg)

    @obstime
    def test_get_altaz_no_weather(self, data_dir, obstime):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pointing_param_path": pointing_param_path,
        }
        cases = [
            (10, 20, "fk5", "deg"),
            (10 << u.deg, 20 << u.deg, "fk5", None),
            (10, 20, "fk5", u.deg),
            (10 << u.deg, 20 << u.deg, FK5, None),
            (10, 20, FK5, u.deg),
        ]
        expected_az, expected_el = ExpectedValue.get_converted_coord(
            lon=10, lat=20, frame="fk5", unit="deg", **config
        )

        calc = CoordCalculator(self.location, pointing_param_path)
        for lon, lat, frame, unit in cases:
            az, el, _ = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to_value("deg") == pytest.approx(expected_az)
            assert el.to_value("deg") == pytest.approx(expected_el)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz(self, data_dir, obstime, temperature, obs_spectrum):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pressure": self.pressure,
            "temperature": temperature,
            "humidity": self.humidity,
            "pointing_param_path": pointing_param_path,
            **obs_spectrum,
        }
        cases = [
            (10, 20, "fk5", "deg"),
            (10 << u.deg, 20 << u.deg, "fk5", None),
            (10, 20, "fk5", u.deg),
            (10 << u.deg, 20 << u.deg, FK5, None),
            (10, 20, FK5, u.deg),
        ]
        expected_az, expected_el = ExpectedValue.get_converted_coord(
            lon=10, lat=20, frame="fk5", unit="deg", **config
        )

        calc = CoordCalculator(
            self.location,
            data_dir / "sample_pointing_param.toml",
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for lon, lat, frame, unit in cases:
            az, el, _ = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to_value("deg") == pytest.approx(expected_az)
            assert el.to_value("deg") == pytest.approx(expected_el)

    @obstime
    def test_get_altaz_array_single_time(self, data_dir, obstime):
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pointing_param_path": pointing_param_path,
        }
        cases = [
            ([10, 10], [20, 20], "fk5", "deg"),
            ([10, 10] << u.deg, [20, 20] << u.deg, "fk5", None),
            ([10, 10], [20, 20], "fk5", u.deg),
            ([10, 10] << u.deg, [20, 20] << u.deg, FK5, None),
            ([10, 10], [20, 20], FK5, u.deg),
        ]
        expected_az, expected_el = ExpectedValue.get_converted_coord(
            lon=[10, 10], lat=[20, 20], frame="fk5", unit="deg", **config
        )

        calc = CoordCalculator(self.location, data_dir / "sample_pointing_param.toml")
        for lon, lat, frame, unit in cases:
            az, el, _ = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to_value("deg") == pytest.approx(expected_az)
            assert el.to_value("deg") == pytest.approx(expected_el)

    def test_get_altaz_multi_time(self, data_dir):
        obstime = [1662697435.261011, 1662697445.261011]
        pointing_param_path = data_dir / "sample_pointing_param.toml"
        config = {
            "location": self.location,
            "obstime": obstime,
            "pointing_param_path": pointing_param_path,
        }
        cases = [
            (10, 20, "fk5", "deg"),
            (10 << u.deg, 20 << u.deg, "fk5", None),
            (10, 20, "fk5", u.deg),
            (10 << u.deg, 20 << u.deg, FK5, None),
            (10, 20, FK5, u.deg),
        ]
        expected_az, expected_el = ExpectedValue.get_converted_coord(
            lon=10, lat=20, frame="fk5", unit="deg", **config
        )

        calc = CoordCalculator(self.location, data_dir / "sample_pointing_param.toml")
        for lon, lat, frame, unit in cases:
            az, el, _ = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to_value("deg") == pytest.approx(expected_az)
            assert el.to_value("deg") == pytest.approx(expected_el)
