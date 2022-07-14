from astropy.coordinates import Angle
from astropy.units import Quantity

from neclib import units  # noqa: F401
from neclib.parameters import ObsParamData


class TestObsParamData:

    expected = {
        "OBSERVER": "amigos",
        "OBJECT": "OriKL",
        "MOLECULE_1": "12CO10",
        "LambdaOn": Angle("3h15m8s"),
        "BetaOn": Angle("15d30m59s"),
        "RELATIVE": False,
        "LambdaOff": Angle("3h50m46s"),
        "BetaOff": Angle("17d25m9s"),
        "position_angle": Quantity("30deg"),
        "OTADEL": True,
        "StartPositionX": Angle("120arcsec"),
        "StartPositionY": Angle("120arcsec"),
        "COORD_SYS": "J2000",
        "SCAN_DIRECTION": "X",
        "n": Quantity(30),
        "scan_spacing": Quantity("60arcsec"),
        "scan_length": Quantity("10s"),
        "scan_velocity": Quantity("600arcsec/s"),
        "ramp_pixel": Quantity(40),
        "integ_on": Quantity("0.1s"),
        "integ_off": Quantity("10s"),
        "integ_hot": Quantity("10s"),
        "off_interval": Quantity("1scan"),
        "load_interval": Quantity("5min"),
    }

    def test_from_file(self, data_dir):
        actual = ObsParamData.from_file(data_dir / "example_otf.obs.toml")
        for name, value in self.expected.items():
            assert getattr(actual, name) == value
            assert actual[name] == value
