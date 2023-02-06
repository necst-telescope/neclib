from neclib.core.formatting import html_repr_of_dict


class TestHTMLReprOfDict:
    def test_type_name(self):
        expected = """\
<span>builtins.dict</span><hr><details><summary>0 elements</summary>\
<table><thead><tr><th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody></tbody>\
</table></details><details><summary>0 elements have alias key(s)</summary><table>\
<thead><tr><th>Key</th><th>Aliases</th></tr></thead><tbody></tbody></table></details>\
<details><summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th>\
<th>Type</th></tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict({}) == expected

        expected = """\
<span>builtins.float</span><hr><details><summary>0 elements</summary>\
<table><thead><tr><th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody></tbody>\
</table></details><details><summary>0 elements have alias key(s)</summary><table>\
<thead><tr><th>Key</th><th>Aliases</th></tr></thead><tbody></tbody></table></details>\
<details><summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th>\
<th>Type</th></tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict({}, float) == expected

        expected = """\
<span>builtins.NoneType</span><hr><details><summary>0 elements</summary>\
<table><thead><tr><th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody></tbody>\
</table></details><details><summary>0 elements have alias key(s)</summary><table>\
<thead><tr><th>Key</th><th>Aliases</th></tr></thead><tbody></tbody></table></details>\
<details><summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th>\
<th>Type</th></tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict({}, type(None)) == expected

    def test_element_repr(self) -> None:
        expected = """\
<span>builtins.dict</span><hr><details><summary>1 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td>\
<td><code>1</code></td><td>int</td></tr></tbody></table></details><details>\
<summary>0 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody></tbody></table></details><details>\
<summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th><th>Type</th>\
</tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict({"a": 1}) == expected

        expected = """\
<span>builtins.dict</span><hr><details><summary>2 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr><tr><td>b</td><td><code>2.0</code></td>\
<td>float</td></tr></tbody></table></details><details>\
<summary>0 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody></tbody></table></details><details>\
<summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th><th>Type</th>\
</tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict(dict(a=1, b=2.0)) == expected

    def test_alias_repr(self) -> None:
        expected = """\
<span>builtins.dict</span><hr><details><summary>1 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr></tbody></table></details><details>\
<summary>1 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody><tr><td><code>a</code></td><td><code>q</code></td>\
</tr></tbody></table></details><details><summary>0 metadata</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody></tbody></table></details>"""
        assert html_repr_of_dict({"a": 1}, aliases={"q": "a"}) == expected

        expected = """\
<span>builtins.dict</span><hr><details><summary>1 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr></tbody></table></details><details>\
<summary>1 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody><tr><td><code>a</code></td><td><code>q, r</code>\
</td></tr></tbody></table></details><details><summary>0 metadata</summary><table>\
<thead><tr><th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody></tbody></table>\
</details>"""
        assert html_repr_of_dict({"a": 1}, aliases={"q": "a", "r": "a"}) == expected

        expected = """\
<span>builtins.dict</span><hr><details><summary>2 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr><tr><td>b</td><td><code>2</code></td><td>int</td>\
</tr></tbody></table></details><details><summary>2 elements have alias key(s)</summary>\
<table><thead><tr><th>Key</th><th>Aliases</th></tr></thead><tbody><tr><td>\
<code>a</code></td><td><code>q</code></td></tr><tr><td><code>b</code></td><td>\
<code>r</code></td></tr></tbody></table></details><details>\
<summary>0 metadata</summary><table><thead><tr><th>Key</th><th>Value</th><th>Type</th>\
</tr></thead><tbody></tbody></table></details>"""
        assert (
            html_repr_of_dict({"a": 1, "b": 2}, aliases={"q": "a", "r": "b"})
            == expected
        )

    def test_metadata_repr(self) -> None:
        expected = """\
<span>builtins.dict</span><hr><details><summary>1 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr></tbody></table></details><details>\
<summary>0 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody></tbody></table></details><details>\
<summary>1 metadata</summary><table><thead><tr><th>Key</th><th>Value</th><th>Type</th>\
</tr></thead><tbody><tr><td>f</td><td><code>1</code></td><td>int</td></tr></tbody>\
</table></details>"""
        assert html_repr_of_dict({"a": 1}, metadata={"f": 1}) == expected

        expected = """\
<span>builtins.dict</span><hr><details><summary>1 elements</summary><table><thead><tr>\
<th>Key</th><th>Value</th><th>Type</th></tr></thead><tbody><tr><td>a</td><td>\
<code>1</code></td><td>int</td></tr></tbody></table></details><details>\
<summary>0 elements have alias key(s)</summary><table><thead><tr><th>Key</th>\
<th>Aliases</th></tr></thead><tbody></tbody></table></details><details>\
<summary>2 metadata</summary><table><thead><tr><th>Key</th><th>Value</th><th>Type</th>\
</tr></thead><tbody><tr><td>f</td><td><code>1</code></td><td>int</td></tr><tr>\
<td>g</td><td><code>2.0</code></td><td>float</td></tr></tbody></table></details>"""
        assert html_repr_of_dict({"a": 1}, metadata={"f": 1, "g": 2.0}) == expected
