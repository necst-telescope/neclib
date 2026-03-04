import numpy as np
from typing import Generator

import astropy.units as u

from .observation_spec_base import (
    ObservationMode,
    ObservationSpec,
    TimeKeeper,
    Waypoint,
)

# NOTE:
# - convert.cartesian_offset_by() is currently a simple lon/lat addition.
# - Therefore, equal-spacing mapping in spherical coordinates may require a cos(lat)
#   correction for d_lon (X direction). This script provides an opt-in correction.
# - For large fields or near poles, a spherical offset implementation in convert.py
#   is the proper long-term fix.


class GridSpec(ObservationSpec):
    __slots__ = ("_hot_time_keeper", "_off_time_keeper")
    _repr_frame = "altaz"

    # cos(lat) ~ 0 での暴走を避ける閾値
    # （小領域近似が成立しない領域）
    _COS_MIN = 1e-3

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Multi-PS用の TimeKeeper を初期化
        # (.obsのパラメータを監視します)
        self._hot_time_keeper = TimeKeeper(self["load_interval"])
        self._off_time_keeper = TimeKeeper(self["off_interval"])

    def observe(self) -> Generator[Waypoint, None, None]:
        """観測の主シーケンス。

        - 走査順: 蛇行（往復, boustrophedon）
        - Multi-PS: OFF/HOT 判定は「各ON点の直前」に挿入
                - カウント: ON点ごとに 1 point を加算
                    （HOT/OFF自体はカウントしない）
        """
        unit = "point"

        for coord in self._points():
            pid = getattr(coord, "id", None) or "UNKNOWN"

            # HOT観測のタイミング判定（ONの直前に挿入）
            if self._hot_time_keeper.should_observe:
                self._hot_time_keeper.tell_observed()
                yield self.hot(f"HOT@{pid}")

            # OFF観測のタイミング判定（ONの直前に挿入）
            if self._off_time_keeper.should_observe:
                self._off_time_keeper.tell_observed()
                yield self.off(f"OFF@{pid}")

            # 1点観測した、とカウント
            # （HOT/OFF 自体はカウントしない設計）
            self._hot_time_keeper.increment(unit)
            self._off_time_keeper.increment(unit)

            # ON点
            yield coord

        # 観測終了時に補間用のキャリブレーションを実行
        # （ログ上わかりやすいIDにする）
        yield self.hot("HOT@END")
        yield self.off("OFF@END")

    @property
    def _on_point(self) -> Waypoint:
        return Waypoint(
            mode=ObservationMode.ON,
            reference=self._reference,
            integration=self["integ_on"],
        )

    @staticmethod
    def _lat_to_cos(lat) -> float:
        """緯度(Dec/El/b 等)に相当する量から cos(lat) を返す。

        Parameters
        ----------
        lat : float or astropy.units.Quantity
            単位付きの場合は角度単位を想定。
            単位なしの場合は「度」とみなす。

        Returns
        -------
        float
            cos(lat)（次元なし）
        """
        if isinstance(lat, u.Quantity):
            lat_rad = lat.to_value(u.rad)
        else:
            lat_rad = np.deg2rad(float(lat))
        return float(np.cos(lat_rad))

    @staticmethod
    def _format_point_id(ix: int, iy: int) -> str:
        """ログ追跡しやすい (ix,iy) 形式のIDを返す（0始まり）。"""
        return f"({ix:02d},{iy:02d})"

    def _infer_reference_lat_in_frame(self, frame: str):
        """reference座標を指定 frame へ変換して lat を取得する。"""
        # offset を掛けない reference 自体の座標が欲しいので
        # reference を直接指定
        tmp = Waypoint(mode=ObservationMode.ON, reference=self._reference)
        sc = tmp.coordinates

        # parse_frame 互換の解釈を使う（J2000/GALACTIC 等）
        from ..convert import (
            to_astropy_type,
        )  # local import to avoid hard dependency at import time

        fr = to_astropy_type.frame(frame)
        sc2 = sc.transform_to(fr)
        return sc2.spherical.lat

    def _reference_lat_for_cos(self, frame: str, coord_sys: str):
        """cos補正に使う基準緯度(lat)を決める。

        優先順位:
          1) cos_correction_ref_lat: offset frame (frame) での緯度を明示指定
              （推奨）
          2) reference座標を frame へ変換して lat を推定
              （J2000->GALACTIC など混在でも安全）
          3) (後方互換) delta_coord が無い、または
              frame==coord_sys の場合のみ beta_on を使用

        Notes
        -----
                - delta_coord != coord_sys のとき、beta_on は
                    「中心座標フレームの緯度」の可能性が高く、
                    offset frame の lat と一致しないため、
                    原則として使用しません。
        """
        # 1) explicit override (in offset frame)
        # NOTE: ObservationSpec inherits from Parameters, which is *not* a dict-like
        # mapping and does not provide `.get()`. Use the raw parameter dict instead.
        params = self.parameters
        ref_lat_override = params.get("cos_correction_ref_lat", None)
        if ref_lat_override is not None:
            return ref_lat_override

        # 2) inference from reference coordinate
        try:
            return self._infer_reference_lat_in_frame(frame)
        except Exception as e_infer:
            # 3) legacy fallback only when safe
            try:
                delta_coord = params.get("delta_coord", None)
                # delta_coord が未指定（None）の場合、
                # frame は coord_sys 由来のはずなので safe
                safe_legacy = (delta_coord is None) or (str(frame) == str(coord_sys))
                if safe_legacy and (params.get("beta_on", None) is not None):
                    return self["beta_on"]
            except Exception:
                pass

            raise ValueError(
                "cos_correction=True needs a reference latitude in "
                "the same frame as offsets.\n"
                "- Tried to infer reference lat by transforming to "
                f"frame={frame!r}, but failed: {e_infer}\n"
                "- Please set cos_correction_ref_lat "
                "(e.g., 'cos_correction_ref_lat[deg]' = "
                "<b or Dec in offset frame>)."
            ) from e_infer

    def _points(self) -> Generator[Waypoint, None, None]:
        """グリッドの ON 観測点を生成する（蛇行走査）。

        i_y が偶数行:  x = 0 -> n_x-1
        i_y が奇数行:  x = n_x-1 -> 0
        """
        on_point = self._on_point.reference

        # .obsファイルからグリッドパラメータを読み込み
        n_x, n_y = int(self["n_x"]), int(self["n_y"])
        if (n_x <= 0) or (n_y <= 0):
            raise ValueError("n_x and n_y must be positive integers.")

        start_x, start_y = self["start_x"], self["start_y"]
        step_x, step_y = self["step_x"], self["step_y"]

        # 0ステップは明らかに不正
        if step_x == 0 or step_y == 0:
            raise ValueError("step_x and step_y must be non-zero.")

        # グリッドの座標系を取得
        # （指定がなければcoord_sysをフォールバックとして使用）
        params = self.parameters
        coord_sys = params.get("coord_sys", "J2000")
        frame = params.get("delta_coord", coord_sys)

        # cos(y)補正のフラグを取得
        # （デフォルトはFalseで安全側に倒す）
        do_cos_correction = bool(params.get("cos_correction", False))

        if do_cos_correction:
            ref_lat = self._reference_lat_for_cos(
                frame=str(frame), coord_sys=str(coord_sys)
            )
            cos_y = self._lat_to_cos(ref_lat)

            # 極付近では近似が破綻するため
            # 黙ってクランプせずに明示的に停止
            if abs(cos_y) < self._COS_MIN:
                raise ValueError(
                    "cos_correction would diverge near the pole: "
                    f"cos(lat)={cos_y:.3e} < {self._COS_MIN}. "
                    f"(offset frame={frame!r}, lat={ref_lat})"
                )

            # X方向の始点とステップ幅を天球上の実角距離に補正
            start_x_calc = start_x / cos_y
            step_x_calc = step_x / cos_y
        else:
            start_x_calc = start_x
            step_x_calc = step_x

        # 始点から順番にステップ幅を足してグリッド座標を生成
        # （蛇行, raster）
        for i_y in range(n_y):
            if i_y % 2 == 0:
                x_indices = range(n_x)
            else:
                x_indices = range(n_x - 1, -1, -1)

            for i_x in x_indices:
                offset = (
                    start_x_calc + i_x * step_x_calc,
                    start_y + i_y * step_y,
                    frame,
                )
                wp = Waypoint(
                    mode=ObservationMode.ON,
                    reference=on_point,
                    offset=offset,
                    integration=self["integ_on"],
                )
                wp.id = self._format_point_id(i_x, i_y)
                yield wp
