"""Compile agent-submitted Python expressions under a strict AST whitelist.

Submitted rules are evaluated only over small finite input spaces, so we allow
arithmetic, comparisons, boolean logic, conditional expressions, indexing and
calls to an explicit set of helper functions. Attribute access, lambdas,
comprehensions, imports and dunder names are rejected before compilation.
"""

from __future__ import annotations

import ast
from typing import Callable, Iterable, Mapping

_ALLOWED = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.Invert, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift, ast.Compare,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.IfExp,
    ast.Call, ast.Name, ast.Load, ast.Constant, ast.Subscript, ast.Slice, ast.Tuple,
    ast.List, ast.Set,
)
_MAX_POW = 64


def compile_expr(src: str, variables: Iterable[str], helpers: Mapping[str, Callable]) -> Callable[..., object]:
    """Return ``f(**bindings)`` evaluating ``src``; raise ValueError if it uses anything disallowed."""
    src = src.strip().strip("`").strip()
    if src.startswith("lambda"):
        raise ValueError("write a bare expression, not a lambda")
    if len(src) > 2000:
        raise ValueError("expression too long")
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"syntax error: {e.msg}") from None
    names = set(variables) | set(helpers)
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError(f"unknown name {node.id!r}")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in helpers):
            raise ValueError("only the listed helper functions may be called")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int) and abs(node.right.value) <= _MAX_POW):
                raise ValueError("exponent must be a small integer constant")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 64:
            raise ValueError("string constant too long")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            for side in (node.left, node.right):
                if isinstance(side, (ast.List, ast.Tuple)) or (isinstance(side, ast.Constant) and isinstance(side.value, str)):
                    raise ValueError("sequence repetition is not allowed")
    code = compile(tree, "<rule>", "eval")
    env = {"__builtins__": {}, **helpers}

    def fn(**bindings: object) -> object:
        return eval(code, env, bindings)  # noqa: S307 - AST-whitelisted above

    return fn
