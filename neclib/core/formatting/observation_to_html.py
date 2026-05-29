from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

from ..inform import get_logger
from ..types import CoordFrameType

if TYPE_CHECKING:
    # Circular import
    from ...coordinates.observations.observation_spec_base import ObservationSpec

__all__ = ["html_repr_of_observation_spec"]

logger = get_logger(__name__)


def html_repr_of_observation_spec(
    observation_spec: ObservationSpec, /, *, frame: CoordFrameType = "fk5"
) -> str:
    """Return HTML representation of the observation specification."""

    waypoint_repr = []

    _svg = StringIO()
    observation_spec.fig.savefig(_svg, format="svg")
    _svg.seek(0)
    svg = _svg.read()

    counter = 0
    for _, _wp in observation_spec.coords.groupby(level=0):
        if counter > 30:  # Limit the number of waypoints to be displayed.
            waypoint_repr.append('<tr><td colspan="3">...</td></tr>')
            break

        for mode, wp in _wp.groupby("mode", sort=False):
            counter += 1

            lon, lat = wp["lon"], wp["lat"]
            try:
                _coord_str = [
                    f"({_lon:9.4f}, {_lat:9.4f})" for _lon, _lat in zip(lon, lat)
                ]
                coord_str = " &#x2192; ".join(_coord_str)
            except TypeError:
                coord_str = f"({lon:9.4f}, {lat:9.4f})"
            others = []
            for info in ["speed", "scan_frame", "integration", "id"]:
                attr, *_ = wp[info].unique()
                if attr is not None:
                    others.append(f"{info}={attr}")
            waypoint_repr.append(
                f"""
                <tr>
                    <td>{mode.name}</td>
                    <td><code>{coord_str}</code></td>
                    <td>{", ".join(others)}</td>
                </tr>
                """
            )

    return f"""
    <details><summary>{observation_spec.coords.index[-1]} waypoints</summary>
        <table>
            <thead>
                <tr>
                    <th>Mode</th>
                    <th>{frame.upper()} Coordinate</th>
                    <th>Other Parameters</th>
                </tr>
            </thead>
            <tbody>
                {''.join(waypoint_repr)}
            </tbody>
        </table>
        <span>The time interval for OFF and HOT observations are not considered.</span>
    </details>
    <details open><summary>Graph</summary>
        {svg}
    </details>
    """
