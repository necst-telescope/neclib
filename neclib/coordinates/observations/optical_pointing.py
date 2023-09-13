from typing import List, Union

from astropy.time import Time

from neclib import config
from neclib.coordinates.convert import CoordCalculator


class OpticalPointingSpec:
    def __init__(self, time: Union[float, str], format: str):
        cal = CoordCalculator(config.location)
        now = Time(time, format=format)

    def to_altaz(self, target: float, frame: str, unit: str, time=now):
        coord = cal.coordinate(
            lon=target[0], lat=target[1], frame=frame, time=time, unit=unit
        )
        altaz_coord = coord.to_apparent_altaz()
        return altaz_coord

    def sort(self, target_list: List[Union[float, str]], magnitude):
        az_range = (
            config.antenna.drive_warning_limit_az
        )  # ValueRange オブジェクト。正直critical limitでもいいんだけどルート決めから観測まで時間差が若干あることを加味してwarning？
        el_range = config.antenna.drive_warning_limit_el
        data = []
        for target in len(target_list):
            # ターゲットを`to_altaz`に渡して変換
            if (
                az
                in az_range & el
                in el_range & multiple
                == " " & vmag
                < magnitude & pmra
                <= pmramax & pmdec
                <= pmdecmax
            ):
                data.append(...)  # 天体番号、RADec、AltAz、pmRADec(?), vmagを追記。
        # Azでソート
        # Az30deg毎に区切ってElソート。毎回昇順と降順を切り替える。`sdata`
        return sdata
