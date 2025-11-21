"""Binomial option pricing model implementation.

The module implements the Cox-Ross-Rubinstein binomial tree for both European and
American options. It uses only the Python standard library.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from typing import List, Literal

OptionType = Literal["call", "put"]


def _validate_parameters(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
) -> None:
    if spot <= 0:
        raise ValueError("Spot price must be positive.")
    if strike <= 0:
        raise ValueError("Strike price must be positive.")
    if maturity <= 0:
        raise ValueError("Maturity must be positive.")
    if steps <= 0:
        raise ValueError("Steps must be a positive integer.")
    if volatility < 0:
        raise ValueError("Volatility must be non-negative.")


@dataclass
class BinomialTreeResult:
    """Container for binomial pricing outputs."""

    price: float
    asset_prices: List[List[float]]
    option_values: List[List[float]]


def binomial_option_price(
    spot: float,
    strike: float,
    maturity: float,
    rate: float,
    volatility: float,
    steps: int,
    option_type: OptionType = "call",
    american: bool = False,
    dividend: float = 0.0,
) -> BinomialTreeResult:
    """Price an option with the Cox-Ross-Rubinstein binomial model.

    Args:
        spot: Current underlying price (S0).
        strike: Strike price (K).
        maturity: Time to maturity in years (T).
        rate: Risk-free interest rate (r) as a decimal.
        volatility: Volatility of the underlying (sigma) as a decimal.
        steps: Number of binomial time steps (N).
        option_type: "call" or "put".
        american: If True, perform early exercise checks at each node.
        dividend: Continuous dividend yield (q) as a decimal.

    Returns:
        BinomialTreeResult with the price and intermediate lattice values.
    """
    _validate_parameters(spot, strike, maturity, rate, volatility, steps)

    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'.")

    dt = maturity / steps
    up = exp(volatility * sqrt(dt))
    down = 1 / up
    growth = exp((rate - dividend) * dt)
    probability = (growth - down) / (up - down)

    if not 0 <= probability <= 1:
        raise ValueError("Arbitrage detected: adjust parameters (N, sigma, or rate).")

    # Build asset price lattice.
    asset_prices: List[List[float]] = []
    for step in range(steps + 1):
        level = [spot * (up ** j) * (down ** (step - j)) for j in range(step + 1)]
        asset_prices.append(level)

    # Terminal option values.
    option_values: List[List[float]] = [[] for _ in range(steps + 1)]
    terminal_values = []
    for price in asset_prices[-1]:
        if option_type == "call":
            payoff = max(price - strike, 0)
        else:
            payoff = max(strike - price, 0)
        terminal_values.append(payoff)
    option_values[-1] = terminal_values

    discount = exp(-rate * dt)

    # Backward induction.
    for step in range(steps - 1, -1, -1):
        current_values = []
        for node in range(step + 1):
            continuation = discount * (
                probability * option_values[step + 1][node + 1]
                + (1 - probability) * option_values[step + 1][node]
            )
            if american:
                intrinsic = (
                    max(asset_prices[step][node] - strike, 0)
                    if option_type == "call"
                    else max(strike - asset_prices[step][node], 0)
                )
                node_value = max(continuation, intrinsic)
            else:
                node_value = continuation
            current_values.append(node_value)
        option_values[step] = current_values

    return BinomialTreeResult(
        price=option_values[0][0], asset_prices=asset_prices, option_values=option_values
    )


if __name__ == "__main__":
    result = binomial_option_price(
        spot=100,
        strike=100,
        maturity=1,
        rate=0.05,
        volatility=0.2,
        steps=50,
        option_type="call",
    )
    print(f"European call price: {result.price:.4f}")
