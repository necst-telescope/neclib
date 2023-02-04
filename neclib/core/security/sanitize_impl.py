import ast
from typing import List, Union


def sanitize(
    content: str, known_variables: Union[str, List[str]] = [], max_length: int = 100
) -> None:
    if len(content) > max_length:
        raise ValueError(f"Value longer than {max_length} characters is prohibited.")
    if isinstance(known_variables, str):
        known_variables = [known_variables]
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and (node.id not in known_variables):
            raise ValueError(f"Use of unknown variable {node.id!r} is prohibited.")
