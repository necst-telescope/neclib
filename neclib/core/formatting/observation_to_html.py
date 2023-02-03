from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from ..inform import get_logger
from ..type_aliases import CoordFrameType

if TYPE_CHECKING:
    # Circular import
    from ...coordinates.observations.observation_spec_base import ObservationSpec

__all__ = ["html_repr_of_observation_spec"]

logger = get_logger(__name__)


def html_repr_of_observation_spec(
    observation_spec: ObservationSpec, /, *, frame: CoordFrameType = "fk5"
) -> str:
    """Return HTML representation of the observation specification."""

    waypoints = iter(observation_spec)
    waypoint_repr = []

    _svg = StringIO()
    with plt.style.context("dark_background"), plt.rc_context(
        {"font.family": "serif", "font.size": 9}
    ):
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.set(
            xlabel="Longitude [deg]",
            ylabel="Latitude [deg]",
            title=f"Waypoints in {frame.upper()} frame",
            aspect=1,
        )
        if frame.lower() not in ["altaz", "horizontal", "azel"]:
            ax.invert_xaxis()  # Celestial coordinate frames are generally right-handed.
        pt_kw = dict(ms=5, alpha=0.9)
        last_coord = None
        for i, wp in enumerate(waypoints):
            if i > 100:  # Limit the number of waypoints to be shown.
                waypoint_repr.append('<tr><td colspan="3">...</td></tr>')
                break

            coord = wp.coordinates.transform_to(frame)
            lon, lat = coord.data.lon.to_value("deg"), coord.data.lat.to_value("deg")
            try:
                nan_coord = (lon != lon) or (lat != lat)
            except ValueError:
                nan_coord = (lon != lon).any() or (lat != lat).any()

            if (coord.size == 0) or nan_coord:
                pass  # Cannot determine where to plot.
            elif coord.size == 1:
                if last_coord is not None:
                    _lon = [last_coord[0], lon]
                    _lat = [last_coord[1], lat]
                    ax.plot(_lon, _lat, c=wp.mode.__class__.DRIVE.value, zorder=-1)
                ax.plot(lon, lat, ".", c=wp.mode.value, **pt_kw)
                last_coord = (lon, lat)
            else:
                if last_coord is not None:
                    _lon = [last_coord[0], lon[0]]
                    _lat = [last_coord[1], lat[0]]
                    ax.plot(
                        _lon, _lat, c=wp.mode.__class__.DRIVE.value, zorder=-1, lw=1
                    )
                ax.plot(lon, lat, c=wp.mode.value, lw=0.3)
                last_coord = (lon[-1], lat[-1])

            try:
                _coord_str = [
                    f"({_lon:9.4f}, {_lat:9.4f})" for _lon, _lat in zip(lon, lat)
                ]
                coord_str = " &#x2192; ".join(_coord_str)
            except TypeError:
                coord_str = f"({lon:9.4f}, {lat:9.4f})"
            others = []
            for info in ["speed", "scan_frame", "integration", "id"]:
                attr = getattr(wp, info)
                if attr is not None:
                    others.append(f"{info}={attr}")
            waypoint_repr.append(
                f"""
                <tr>
                    <td>{wp.mode.name}</td>
                    <td><code>{coord_str}</code></td>
                    <td>{", ".join(others)}</td>
                </tr>
                """
            )
        ax.grid(True, c="#757")
        fig.tight_layout()
        fig.savefig(_svg, format="svg")
    _svg.seek(0)
    svg = _svg.read()
    plt.close(fig)  # Don't show the figure in Jupyter Notebook inline.

    return f"""
    <details><summary>{len(waypoint_repr)} waypoints</summary>
        <table>
            <thead>
                <tr>
                    <th>Mode</th>
                    <th>{frame.upper()} Coordinate [deg]</th>
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
