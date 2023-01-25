"""String or rich-text representation of NECLIB data types."""

__all__ = ["html_repr_of_dict"]

from typing import Any, Dict, Optional, Type


def html_repr_of_dict(
    __dict: Dict[Any, Any],
    __type: Optional[Type[Any]] = None,
    /,
    *,
    metadata: Dict[str, Any] = {},
) -> str:
    """Return a HTML representation of a dictionary.

    Parameters
    ----------
    __dict
        Dictionary to be represented.
    __type
        Type of the object, which this dictionary represents.
    metadata
        Metadata to be included in the representation.

    Returns
    -------
    rich_repr
        The HTML representation of the dictionary.

    """
    __type = f"""
    <span>{__type.__module__.split(".")[0]}.{__type.__name__}</span>
    <hr>
    """
    elements = [
        f"<tr><td>{k}</td><td><code>{v}</code></td><td>{type(v).__name__}</td></tr>"
        for k, v in __dict.items()
    ]
    metadata = [
        f"<tr><td>{k}</td><td><code>{v}</code></td><td>{type(v).__name__}</td></tr>"
        for k, v in metadata.items()
    ]
    return f"""
    {__type}
    <details><summary>{len(elements)} elements</summary>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Value</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
                {''.join(elements)}
            </tbody>
        </table>
    </details>
    <br>
    <details><summary>{len(metadata)} metadata</summary>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Value</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
                {''.join(metadata)}
            </tbody>
        </table>
    </details>
    """