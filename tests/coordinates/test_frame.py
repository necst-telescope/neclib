from astropy.coordinates import FK5, ICRS, AltAz, Angle, Galactic, SkyOffsetFrame

from neclib.coordinates import describe_frame, parse_frame


class TestParseFrame:
    def test_builtin_frame(self):
        assert parse_frame("fk5") is FK5
        assert parse_frame("icrs") is ICRS
        assert parse_frame("galactic") is Galactic
        assert parse_frame("altaz") is AltAz

    def test_offset_frame(self):
        parsed = parse_frame("origin=FK5(0deg, 0deg), rotation=0deg")
        assert parsed.origin == FK5("0deg", "0deg")
        assert parsed.rotation == Angle("0deg")
        assert isinstance(parsed, SkyOffsetFrame)

        parsed = parse_frame("origin=Galactic(10deg, 0deg), rotation=20deg")
        assert parsed.origin == Galactic("10deg", "0deg")
        assert parsed.rotation == Angle("20deg")
        assert isinstance(parsed, SkyOffsetFrame)


class TestDescribeFrame:
    def test_builtin_frame(self):
        assert describe_frame(AltAz) == "altaz"
        assert describe_frame(FK5) == "fk5"
        assert describe_frame(Galactic) == "galactic"
        assert describe_frame(ICRS) == "icrs"
        assert describe_frame(FK5()) == "fk5"

    def test_offset_frame(self):
        frame = SkyOffsetFrame(origin=FK5("0deg", "0deg"), rotation=Angle("0deg"))
        description = describe_frame(frame)
        assert isinstance(description, str)
        assert parse_frame(description) == frame

        frame = SkyOffsetFrame(
            origin=Galactic("10deg", "0deg"), rotation=Angle("20deg")
        )
        description = describe_frame(frame)
        assert isinstance(description, str)
        assert parse_frame(description) == frame
