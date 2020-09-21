# Core Library
import ast
import sys
from collections import defaultdict
from typing import Any, DefaultDict, Generator, List, Tuple, Type

# Third party
import astor

if sys.version_info < (3, 8):  # pragma: no cover (<PY38)
    # Third party
    import importlib_metadata
else:  # pragma: no cover (PY38+)
    # Core Library
    import importlib.metadata as importlib_metadata

SIM101 = (
    "SIM101 Multiple isinstance-calls which can be merged into a single "
    "call for variable '{var}'"
)
SIM201 = "SIM201 Use '{left} != {right}' instead of 'not {left} == {right}'"
SIM202 = "SIM202 Use '{left} == {right}' instead of 'not {left} != {right}'"
SIM203 = "SIM203 Use '{a} not in {b}' instead of 'not {a} in {b}'"
SIM204 = "SIM204 Use '{a} >= {b}' instead of 'not ({a} < {b})'"
SIM205 = "SIM205 Use '{a} > {b}' instead of 'not ({a} <= {b})'"
SIM206 = "SIM206 Use '{a} <= {b}' instead of 'not ({a} > {b})'"
SIM207 = "SIM207 Use '{a} < {b}' instead of 'not ({a} >= {b})'"
SIM208 = "SIM208 Use '{a}' instead of 'not (not {a})'"


def _get_duplicated_isinstance_call_by_node(node: ast.BoolOp) -> List[str]:
    """
    Get a list of isinstance arguments which could be shortened.

    This checks SIM101.

    Examples
    --------
    >> g = _get_duplicated_isinstance_call_by_node
    >> g("isinstance(a, int) or isinstance(a, float) or isinstance(b, int)
    ['a']
    >> g("isinstance(a, int) or isinstance(b, float) or isinstance(b, int)
    ['b']
    """
    counter: DefaultDict[str, int] = defaultdict(int)

    for call in node.values:
        # Make sure that this function call is actually a call of the built-in
        # "isinstance"
        if not isinstance(call, ast.Call) or len(call.args) != 2:
            continue
        function_name = astor.to_source(call.func).strip()
        if function_name != "isinstance":
            continue

        # Collect the name of the argument
        isinstance_arg0_name = astor.to_source(call.args[0]).strip()
        counter[isinstance_arg0_name] += 1
    return [arg0_name for arg0_name, count in counter.items() if count > 1]


def _get_duplicated_isinstance_calls(
    node: ast.BoolOp,
) -> List[Tuple[int, int, str]]:
    """Get a positions where the duplicate isinstance problem appears."""
    errors: List[Tuple[int, int, str]] = []
    if not isinstance(node.op, ast.Or):
        return errors

    for var in _get_duplicated_isinstance_call_by_node(node):
        errors.append((node.lineno, node.col_offset, SIM101.format(var=var)))
    return errors


def _get_not_equal_calls(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """
    Get a list of all calls where an unary 'not' is used for an equality.

    This checks SIM201.
    """
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.Eq)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM201.format(left=left, right=right))
    )

    return errors


def _get_not_non_equal_calls(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """
    Get a list of all calls where an unary 'not' is used for an quality.

    This checks SIM202.
    """
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.NotEq)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM202.format(left=left, right=right))
    )

    return errors


def _get_not_in_calls(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """
    Get a list of all calls where an unary 'not' is used for an in-check.

    This checks SIM203.
    """
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.In)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM203.format(a=left, b=right))
    )

    return errors


def _get_sim204(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """Get a list of all calls of the type "not (a < b)"."""
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.Lt)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM204.format(a=left, b=right))
    )
    return errors


def _get_sim205(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """Get a list of all calls of the type "not (a <= b)"."""
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.LtE)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM205.format(a=left, b=right))
    )
    return errors


def _get_sim206(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """Get a list of all calls of the type "not (a > b)"."""
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.Gt)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM206.format(a=left, b=right))
    )
    return errors


def _get_sim207(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """Get a list of all calls of the type "not (a >= b)"."""
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.Compare)
        or len(node.operand.ops) != 1
        or not isinstance(node.operand.ops[0], ast.GtE)
    ):
        return errors
    comparison = node.operand
    left = astor.to_source(comparison.left).strip()
    right = astor.to_source(comparison.comparators[0]).strip()
    errors.append(
        (node.lineno, node.col_offset, SIM207.format(a=left, b=right))
    )
    return errors


def _get_sim208(node: ast.UnaryOp) -> List[Tuple[int, int, str]]:
    """Get a list of all calls of the type "not (not a)"."""
    errors: List[Tuple[int, int, str]] = []
    if (
        not isinstance(node.op, ast.Not)
        or not isinstance(node.operand, ast.UnaryOp)
        or not isinstance(node.operand.op, ast.Not)
    ):
        return errors
    a = astor.to_source(node.operand.operand).strip()
    errors.append((node.lineno, node.col_offset, SIM208.format(a=a)))
    return errors


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: List[Tuple[int, int, str]] = []

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.errors += _get_duplicated_isinstance_calls(node)
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        self.errors += _get_not_equal_calls(node)
        self.errors += _get_not_non_equal_calls(node)
        self.errors += _get_not_in_calls(node)
        self.errors += _get_sim204(node)
        self.errors += _get_sim205(node)
        self.errors += _get_sim206(node)
        self.errors += _get_sim207(node)
        self.errors += _get_sim208(node)
        self.generic_visit(node)


class Plugin:
    name = __name__
    version = importlib_metadata.version(__name__)

    def __init__(self, tree: ast.AST):
        self._tree = tree

    def run(self) -> Generator[Tuple[int, int, str, Type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)

        for line, col, msg in visitor.errors:
            yield line, col, msg, type(self)
