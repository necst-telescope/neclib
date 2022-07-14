#!/usr/bin/env python3

import numpy as np
from astropy.coordinates import AltAz, Angle, EarthLocation, SkyCoord
from astropy.units import Quantity


def map_on_lonlat_quantity(func, coord):
    LON, LAT, CoordSys = 0, 1, 2
    return (func(coord[LON]), func(coord[LAT]), coord[CoordSys])


def separator():
    print("======================")


separator()

given_absolute_point = (Angle("1h2m3s"), Angle("10d20m30s"), "fk5")
print("given_absolute_point :", given_absolute_point)
print(
    "expected_absolute_point :",
    map_on_lonlat_quantity(lambda x: x.deg, given_absolute_point),
)

separator()

given_on_point = (Angle("15h25m35s"), Angle("50d40m30s"), "fk5")
print("given_on_point :", given_on_point)
print(
    "given_on_point_arcsec :",
    map_on_lonlat_quantity(lambda x: x.arcsec, given_on_point),
)

given_offset_1 = (Angle("3arcsec"), Angle("20arcsec"), "fk5")
given_offset_2 = (Angle("3arcsec"), Angle("20arcsec"), "galactic")
print("given_offset_1 :", given_offset_1)
print("given_offset_2 :", given_offset_2)

expected_coord_1 = (
    (given_on_point[0] + given_offset_1[0]).to_value("deg"),
    (given_on_point[1] + given_offset_1[1]).to_value("deg"),
    given_offset_1[2],
)
print("expected_coord_1 :", expected_coord_1)
print(
    "expected_coord_1_arcsec :",
    map_on_lonlat_quantity(lambda x: x * 3600, expected_coord_1),
)
expected_coord_1_coslat_applied = (
    (given_on_point[0] + given_offset_1[0] / np.cos(given_on_point[1])).to_value("deg"),
    (given_on_point[1] + given_offset_1[1]).to_value("deg"),
    given_offset_1[2],
)
print("expected_coord_1_coslat_applied :", expected_coord_1_coslat_applied)
_galactic_given_on_point = (
    SkyCoord(*given_on_point[0:2], frame=given_on_point[2])
    .transform_to("galactic")
    .data
)
expected_coord_2 = (
    (_galactic_given_on_point.lon + given_offset_2[0]).to_value("deg"),
    (_galactic_given_on_point.lat + given_offset_2[1]).to_value("deg"),
    given_offset_2[2],
)
print("expected_coord_2 :", expected_coord_2)
print(
    "expected_coord_2_arcsec :",
    map_on_lonlat_quantity(lambda x: x * 3600, expected_coord_2),
)
expected_coord_2_coslat_applied = (
    (
        _galactic_given_on_point.lon
        + given_offset_2[0] / np.cos(_galactic_given_on_point.lat)
    ).to_value("deg"),
    (_galactic_given_on_point.lat + given_offset_2[1]).to_value("deg"),
    given_offset_2[2],
)
print("expected_coord_2_coslat_applied :", expected_coord_2_coslat_applied)

separator()

_LOC_NANTEN2 = EarthLocation(
    lon=Quantity("-67.70308139deg"),
    lat=Quantity("-22.96995611deg"),
    height=Quantity("4863.85m"),
)  # Make result insensitive to update of N-CONST

altaz_kwargs = {"location": _LOC_NANTEN2, "obstime": "2022-04-21T04:24:50"}
print("altaz_kwargs :", altaz_kwargs)

given_altaz_on_point = (Angle("195d10m5s"), Angle("30d40m50s"), "altaz")
given_offset_3 = (Angle("3arcsec"), Angle("20arcsec"), "altaz")
given_offset_4 = (Angle("3arcsec"), Angle("20arcsec"), "fk5")
print("given_altaz_on_point :", given_altaz_on_point)
print("given_offset_3 :", given_offset_3)
print("given_offset_4 :", given_offset_4)

expected_coord_3 = (
    (given_altaz_on_point[0] + given_offset_3[0]).to_value("deg"),
    (given_altaz_on_point[1] + given_offset_3[1]).to_value("deg"),
    given_offset_3[2],
)
print("expected_coord_3 :", expected_coord_3)
expected_coord_3_coslat_applied = (
    (
        given_altaz_on_point[0] + given_offset_3[0] / np.cos(given_altaz_on_point[1])
    ).to_value("deg"),
    (given_altaz_on_point[1] + given_offset_3[1]).to_value("deg"),
    given_offset_3[2],
)
print("expected_coord_3_coslat_applied :", expected_coord_3_coslat_applied)
_fk5_given_altaz_on_point = (
    SkyCoord(*given_altaz_on_point[:2], frame=given_altaz_on_point[2], **altaz_kwargs)
    .transform_to("fk5")
    .data
)
expected_coord_4 = (
    (_fk5_given_altaz_on_point.lon + given_offset_4[0]).to_value("deg"),
    (_fk5_given_altaz_on_point.lat + given_offset_4[1]).to_value("deg"),
    given_offset_4[2],
)
print("expected_coord_4 :", expected_coord_4)
expected_coord_4_coslat_applied = (
    (
        _fk5_given_altaz_on_point.lon
        + given_offset_4[0] / np.cos(_fk5_given_altaz_on_point.lat)
    ).to_value("deg"),
    (_fk5_given_altaz_on_point.lat + given_offset_4[1]).to_value("deg"),
    given_offset_4[2],
)
print("expected_coord_4_coslat_applied :", expected_coord_4_coslat_applied)

separator()

given_fk5_on_point = (Angle("15h25m35s"), Angle("50d40m30s"), "fk5")
print("given_fk5_on_point :", given_fk5_on_point)
given_offset_5 = (Angle("3arcsec"), Angle("20arcsec"), "altaz")
print("given_offset_5 :", given_offset_5)
_altaz_given_on_point = (
    SkyCoord(*given_fk5_on_point[:2], frame=given_fk5_on_point[2])
    .transform_to(AltAz(**altaz_kwargs))
    .data
)
expected_coord_5 = (
    (_altaz_given_on_point.lon + given_offset_5[0]).to_value("deg"),
    (_altaz_given_on_point.lat + given_offset_5[1]).to_value("deg"),
    given_offset_5[2],
)
print("expected_coord_5 :", expected_coord_5)
expected_coord_5_coslat_applied = (
    (
        _altaz_given_on_point.lon
        + given_offset_5[0] / np.cos(_altaz_given_on_point.lat)
    ).to_value("deg"),
    (_altaz_given_on_point.lat + given_offset_5[1]).to_value("deg"),
    given_offset_5[2],
)
print("expected_coord_5_coslat_applied :", expected_coord_5_coslat_applied)

separator()

given_multiple_absolute_points = (
    Angle(["1h2m3s", "2h3m4s", "3h4m5s"]),
    Angle(["30d40m50s", "20d30m40s", "10d20m30s"]),
    "fk5",
)
print("given_multiple_absolute_points :", given_multiple_absolute_points)
expected_multiple_absolute_points = (
    given_multiple_absolute_points[0].to_value("deg"),
    given_multiple_absolute_points[1].to_value("deg"),
    given_multiple_absolute_points[2],
)
print("expected_multiple_absolute_points :", expected_multiple_absolute_points)

separator()

given_multiple_on_points = (
    Angle(["1h2m3s", "2h3m4s", "3h4m5s"]),
    Angle(["30d40m50s", "20d30m40s", "10d20m30s"]),
    "fk5",
)
given_single_offset = (Angle("3arcsec"), Angle("20arcsec"), "galactic")
print("given_multiple_on_points :", given_multiple_on_points)
print("given_single_offset :", given_single_offset)
_galactic_given_multiple_on_points = (
    SkyCoord(*given_multiple_on_points[:2], frame=given_multiple_on_points[2])
    .transform_to("galactic")
    .data
)
expected_multiple_coords_1 = (
    (_galactic_given_multiple_on_points.lon + given_single_offset[0]).to_value("deg"),
    (_galactic_given_multiple_on_points.lat + given_single_offset[1]).to_value("deg"),
    given_single_offset[2],
)
print("expected_multiple_coords_1 :", expected_multiple_coords_1)

given_multiple_offsets = (
    Angle(["1arcsec", "2arcsec", "3arcsec"]),
    Angle(["10arcsec", "20arcsec", "30arcsec"]),
    "galactic",
)
print("given_multiple_offsets :", given_multiple_offsets)
expected_multiple_coords_2 = (
    (_galactic_given_multiple_on_points.lon + given_multiple_offsets[0]).to_value(
        "deg"
    ),
    (_galactic_given_multiple_on_points.lat + given_multiple_offsets[1]).to_value(
        "deg"
    ),
    given_multiple_offsets[2],
)
print("expected_multiple_coords_2 :", expected_multiple_coords_2)

separator()
