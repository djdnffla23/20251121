"""Monte Carlo option pricer with user-defined payoff expressions."""
from __future__ import annotations

import ast
import builtins
import math
from dataclasses import dataclass
from random import gauss
from typing import Callable, List, Sequence


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive.")


def _validate_inputs(
    spot: float, maturity: float, rate: float, volatility: float, steps: int, paths: int
) -> None:
    _validate_positive("spot", spot)
    _validate_positive("maturity", maturity)
    _validate_positive("steps", float(steps))
    _validate_positive("paths", float(paths))
    if volatility < 0:
        raise ValueError("volatility must be non-negative.")


class _ExpressionValidator(ast.NodeVisitor):
    """Restrict payoff expressions to a safe subset of Python."""

    _allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.IfExp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Subscript,
        ast.Slice,
        ast.Index,
        ast.Attribute,
        ast.And,
        ast.Or,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.FloorDiv,
        ast.Mod,
        ast.USub,
        ast.UAdd,
    )

    _allowed_names = {"price", "path"}
    _helper_functions = {"max", "min"}
    _allowed_functions = {name for name in dir(math) if not name.startswith("__")}
    _allowed_functions.update(_helper_functions)

    def visit(self, node: ast.AST) -> None:  # type: ignore[override]
        if not isinstance(node, self._allowed_nodes):
            raise ValueError(f"Unsupported expression: {ast.dump(node)}")
        return super().visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # type: ignore[override]
        if node.id not in self._allowed_names and node.id not in self._allowed_functions:
            raise ValueError(f"Unknown name in payoff expression: {node.id}")

    def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
        if isinstance(node.func, ast.Attribute):
            if not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "math"
                and node.func.attr in self._allowed_functions
            ):
                raise ValueError("Only math module functions are allowed in calls.")
        elif isinstance(node.func, ast.Name):
            if node.func.id not in self._allowed_functions:
                raise ValueError(f"Function {node.func.id} is not allowed.")
        else:
            raise ValueError("Invalid function call in expression.")
        self.generic_visit(node)


def payoff_from_expression(expression: str) -> Callable[[float, Sequence[float]], float]:
    """Compile a user-provided expression into a payoff function.

    The expression can use:
    - ``price``: terminal asset price.
    - ``path``: full price path as a list of floats.
    - Functions from the :mod:`math` module such as ``max``, ``exp``, and ``sqrt``.
    """

    try:
        syntax_tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Invalid payoff expression: {exc}") from exc

    validator = _ExpressionValidator()
    validator.visit(syntax_tree)

    compiled = compile(syntax_tree, filename="<payoff>", mode="eval")

    allowed_globals = {name: getattr(math, name) for name in dir(math) if name in validator._allowed_functions}
    allowed_globals.update({func: getattr(builtins, func) for func in validator._helper_functions})
    allowed_globals.update({"math": math, "__builtins__": {}})

    def payoff(price: float, path: Sequence[float]) -> float:
        return float(eval(compiled, allowed_globals, {"price": price, "path": path}))

    return payoff


@dataclass
class MonteCarloResult:
    price: float
    payoffs: List[float]
    paths: List[List[float]]


def monte_carlo_option_price(
    *,
    spot: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
    paths: int,
    payoff: Callable[[float, Sequence[float]], float],
) -> MonteCarloResult:
    """Price an option with Geometric Brownian Motion using Monte Carlo simulation."""

    _validate_inputs(spot, maturity, rate, volatility, steps, paths)

    dt = maturity / steps
    drift = (rate - 0.5 * volatility * volatility) * dt
    diffusion = volatility * math.sqrt(dt)

    simulated_paths: List[List[float]] = []
    payoffs: List[float] = []

    for _ in range(paths):
        prices = [spot]
        price = spot
        for _ in range(steps):
            increment = drift + diffusion * gauss(0, 1)
            price *= math.exp(increment)
            prices.append(price)
        simulated_paths.append(prices)
        payoffs.append(payoff(price, prices))

    discount_factor = math.exp(-rate * maturity)
    price_estimate = discount_factor * sum(payoffs) / len(payoffs)

    return MonteCarloResult(price=price_estimate, payoffs=payoffs, paths=simulated_paths)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Monte Carlo option pricer with custom payoff expressions."
    )
    parser.add_argument("--spot", type=float, default=100.0, help="Initial asset price")
    parser.add_argument("--maturity", type=float, default=1.0, help="Time to maturity in years")
    parser.add_argument("--rate", type=float, default=0.05, help="Risk-free interest rate")
    parser.add_argument("--volatility", type=float, default=0.2, help="Asset volatility")
    parser.add_argument("--steps", type=int, default=50, help="Number of time steps per path")
    parser.add_argument("--paths", type=int, default=10000, help="Number of Monte Carlo paths")
    parser.add_argument(
        "--payoff",
        required=True,
        help=(
            "Payoff expression using 'price' for terminal price and 'path' for the full path. "
            "Example: 'max(price - 100, 0)' for a call option."
        ),
    )

    args = parser.parse_args()
    payoff_fn = payoff_from_expression(args.payoff)
    result = monte_carlo_option_price(
        spot=args.spot,
        maturity=args.maturity,
        rate=args.rate,
        volatility=args.volatility,
        steps=args.steps,
        paths=args.paths,
        payoff=payoff_fn,
    )
    print(f"Estimated option price: {result.price:.6f}")
