from __future__ import annotations

import warnings
from collections import defaultdict
from dataclasses import fields
from io import StringIO
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from ..exceptions import NECSTAccessibilityWarning

if TYPE_CHECKING:
    from ..data_type.status_manager import StatusManager


def html_repr_of_status(a: StatusManager):
    colors = defaultdict(lambda: f"C{len(colors)}")
    data_fields = [f for f in fields(a.ctx_type) if f.name not in [a.start, a.stop]]
    max_field_name_length = max(len(f.name) for f in data_fields)

    with plt.style.context("Solarize_Light2"), plt.rc_context(  # type: ignore
        {"font.family": "monospace", "font.size": 9}
    ):
        height = len(data_fields) * 0.5
        width = max_field_name_length * 0.05 + 5
        fig, ax = plt.subplots(figsize=(width, height))
        _x = {_a.start for _a in a.ctx} | {_a.stop for _a in a.ctx}
        x = sorted(_x)
        d = [a.get(_x) for _x in x]

        for _x, _d in zip(x, d):
            start, stop = getattr(_d, a.start), getattr(_d, a.stop)
            if (start is None) or (stop is None):
                continue
            width = stop - start

            for i, field in enumerate(data_fields):
                name = field.name
                id = str(getattr(_d, name))
                ax.barh(i, width, left=start, height=0.8, color=colors[id])
                ax.text(
                    start + width / 2, i, getattr(_d, name), ha="center", va="center"
                )
        ax.set(
            xlim=(x[0], x[-1]),
            yticks=range(len(data_fields)),
            yticklabels=[f.name for f in data_fields],
        )
        ax.grid(False)
        ax.invert_yaxis()

        warnings.simplefilter("error", UserWarning)
        try:
            fig.tight_layout()
        except UserWarning:
            warnings.simplefilter("default", UserWarning)
            warnings.warn(
                "tight_layout failed. This can be caused by non-zero default value of "
                "`start` and/or `stop` attributes.",
                NECSTAccessibilityWarning,
            )

        _svg = StringIO()
        fig.savefig(_svg, format="svg")
        plt.close()
        _svg.seek(0)
        return _svg.read()
