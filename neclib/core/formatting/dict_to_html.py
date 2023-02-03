"""String or rich-text representation of NECLIB data types."""

__all__ = ["html_repr_of_dict"]

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type


def html_repr_of_dict(
    __dict: Dict[Any, Any],
    __type: Optional[Type[Any]] = None,
    /,
    *,
    aliases: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
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
    if __type is None:
        __type = type(__dict)
    if aliases is None:
        aliases = {}
    if metadata is None:
        metadata = {}

    pkg = getattr(__type, "__module__", "")
    typename = getattr(__type, "__name__", str(__type))
    type_repr = f"<span>{f'{pkg}.' if pkg else ''}{typename}</span><hr>"

    element_repr = [
        f"<tr><td>{k}</td><td><code>{v}</code></td><td>{type(v).__name__}</td></tr>"
        for k, v in __dict.items()
    ]

    metadata_repr = [
        f"<tr><td>{k}</td><td><code>{v}</code></td><td>{type(v).__name__}</td></tr>"
        for k, v in metadata.items()
    ]

    _aliases: Dict[str, List[str]] = defaultdict(list)
    # Reverse the aliases to show [Actual Key : Alias Key 1, Alias Key 2] style
    # representation
    for k, v in aliases.items():
        _aliases[v].append(k)
    alias_repr = [
        f"<tr><td><code>{k}</code></td><td><code>{', '.join(v)}</code></td></tr>"
        for k, v in _aliases.items()
    ]

    repr_ = f"""
    {type_repr}
    <details><summary>{len(element_repr)} elements</summary>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Value</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
                {''.join(element_repr)}
            </tbody>
        </table>
    </details>
    <details><summary>{len(alias_repr)} elements have alias key(s)</summary>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Aliases</th>
                </tr>
            </thead>
            <tbody>
                {''.join(alias_repr)}
            </tbody>
        </table>
    </details>
    <details><summary>{len(metadata_repr)} metadata</summary>
        <table>
            <thead>
                <tr>
                    <th>Key</th>
                    <th>Value</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>
                {''.join(metadata_repr)}
            </tbody>
        </table>
    </details>
    """
    return re.sub(r"\n\s*", "", repr_)  # Remove all newlines and indentation
