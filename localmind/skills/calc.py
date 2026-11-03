"""Calculator skill: safe arithmetic via the Python AST.

This evaluates arithmetic expressions WITHOUT using ``eval``. It parses the
expression into an AST and walks only an allow-list of numeric node types, so it
cannot run arbitrary code, import modules or access names.

Supported: + - * / // % ** , parentheses, unary minus/plus and a handful of
safe functions (abs, round, sqrt, min, max) plus the constants pi and e.

Integer results are capped at ``_MAX_INT_BITS`` bits (about 3000 digits), and a
power whose result would exceed that cap is rejected *before* it is computed, so
an input such as ``9 ** 9 ** 9`` returns an error message immediately instead of
hanging. Float overflow (e.g. ``10.0 ** 400``) is reported the same way.

Examples that route here::

    calc 2 + 2 * 3
    what is 12 / 4
    (5 + 3) ** 2
"""

from __future__ import annotations

import ast
import math
import operator as op
import re

from . import Skill, SkillContext

# Allowed binary and unary operators mapped to their implementations.
_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_UNARY_OPS = {ast.UAdd: op.pos, ast.USub: op.neg}

# Safe, side-effect-free callables and constants the parser may reference.
_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


class _UnsafeExpression(ValueError):
    """Raised when an expression contains a disallowed construct."""


class _TooLarge(ValueError):
    """Raised when a result would exceed the size limits below."""


#: Largest integer (in bits) any step may produce: about 3,000 decimal digits.
_MAX_INT_BITS = 10_000


def _check_size(value):
    """Reject integer results above ``_MAX_INT_BITS``; pass others through."""
    if isinstance(value, int) and value.bit_length() > _MAX_INT_BITS:
        raise _TooLarge(f"result has more than {_MAX_INT_BITS} bits")
    return value


def _safe_pow(base, exponent):
    """``base ** exponent`` that refuses integer powers above the size cap.

    The size check happens before the power is computed, because CPython's
    big-integer power cannot be interrupted once it starts.
    """
    if (
        isinstance(base, int)
        and isinstance(exponent, int)
        and exponent > 0
        and abs(base) > 1
        and exponent * math.log2(abs(base)) > _MAX_INT_BITS
    ):
        raise _TooLarge(f"result would have more than {_MAX_INT_BITS} bits")
    return base ** exponent


def _evaluate(node: ast.AST) -> float:
    """Recursively evaluate an allow-listed AST node, else raise."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):  # numeric literal
        if isinstance(node.value, (int, float)):
            return node.value
        raise _UnsafeExpression("only numeric literals are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow):
            return _check_size(_safe_pow(left, right))
        return _check_size(_BIN_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCTIONS.get(node.func.id)
        if fn is None:
            raise _UnsafeExpression(f"function '{node.func.id}' is not allowed")
        if node.keywords:
            raise _UnsafeExpression("keyword arguments are not allowed")
        return _check_size(fn(*[_evaluate(arg) for arg in node.args]))
    raise _UnsafeExpression("unsupported expression")


def safe_eval(expression: str) -> float:
    """Parse and evaluate ``expression`` safely; raise on anything disallowed."""
    tree = ast.parse(expression, mode="eval")
    return _evaluate(tree)


def _extract_expression(query: str) -> str:
    """Strip 'calc'/'what is' style prefixes and return the math expression."""
    text = query.strip()
    text = re.sub(
        # Only ":" is a separator; a "-" here is the expression's own minus sign.
        r"^\s*(calc(ulate)?|compute|what\s+is|eval(uate)?)\s*:?\s*",
        "",
        text,
        flags=re.I,
    )
    return text.strip().rstrip("?")


def run(query: str, context: SkillContext) -> str:
    """Handle a calculation request and return a human-readable reply."""
    expression = _extract_expression(query)
    if not expression:
        return "What should I calculate? e.g. 'calc 2 + 2 * 3'."
    try:
        result = safe_eval(expression)
    except _UnsafeExpression as exc:
        return f"I can only do safe arithmetic: {exc}."
    except _TooLarge as exc:
        return f"That number is too large to calculate: {exc}."
    except OverflowError:
        return f"Could not evaluate '{expression}': the result is too large."
    except (SyntaxError, ZeroDivisionError, ValueError, TypeError) as exc:
        return f"Could not evaluate '{expression}': {exc}."
    # Present whole-number floats without a trailing ".0".
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"{expression} = {result}"


SKILL = Skill(
    name="calc",
    keywords=["calc", "calculate", "compute", "math"],
    run=run,
    description="Evaluate safe arithmetic expressions (no eval, AST allow-list).",
)
