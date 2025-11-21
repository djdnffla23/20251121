"""Minimal Flask web server for Monte Carlo option pricing.

The server exposes:
- A browser form at `/` for interactive pricing using a payoff expression.
- A JSON API at `/api/price` for programmatic access.

Run the server:
    python web_option_server.py
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from flask import Flask, jsonify, render_template_string, request

from monte_carlo_option import monte_carlo_option_price, payoff_from_expression

app = Flask(__name__)


def _parse_inputs(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Normalize and validate pricing inputs from a mapping.

    Returns a tuple of (params, payoff_expression).
    """

    def as_float(name: str) -> float:
        value = data.get(name, "")
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a number.")

    def as_int(name: str) -> int:
        value = data.get(name, "")
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be an integer.")
        if int_value <= 0:
            raise ValueError(f"{name} must be positive.")
        return int_value

    payoff_expression = (data.get("payoff") or "").strip()
    if not payoff_expression:
        raise ValueError("payoff expression is required.")

    params = {
        "spot": as_float("spot"),
        "maturity": as_float("maturity"),
        "rate": as_float("rate"),
        "volatility": as_float("volatility"),
        "steps": as_int("steps"),
        "paths": as_int("paths"),
    }

    return params, payoff_expression


def _format_result(result) -> Dict[str, Any]:
    """Create a lightweight JSON-serializable view of the result."""

    sample_paths = result.paths[:3]
    sample_payoffs = result.payoffs[:5]
    return {
        "price": result.price,
        "sample_payoffs": sample_payoffs,
        "sample_paths": sample_paths,
        "path_count": len(result.paths),
        "steps": len(result.paths[0]) - 1 if result.paths else 0,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    result_payload: Dict[str, Any] | None = None

    defaults = {
        "spot": 100.0,
        "maturity": 1.0,
        "rate": 0.05,
        "volatility": 0.2,
        "steps": 50,
        "paths": 5000,
        "payoff": "max(price - 100, 0)",
    }

    if request.method == "POST":
        try:
            params, payoff_expression = _parse_inputs(request.form)
            payoff_fn = payoff_from_expression(payoff_expression)
            result = monte_carlo_option_price(payoff=payoff_fn, **params)
            result_payload = _format_result(result)
            message = f"Estimated option price: {result.price:.6f}"
        except ValueError as exc:
            message = str(exc)

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Monte Carlo Option Pricer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem auto; max-width: 800px; }
            label { display: block; margin-top: 0.5rem; }
            input, textarea { width: 100%; padding: 0.5rem; }
            .result { background: #f6f8fa; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
            .error { color: #b00020; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; }
            button { margin-top: 1rem; padding: 0.6rem 1.2rem; }
            code { background: #eef; padding: 0.1rem 0.3rem; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>Monte Carlo Option Pricer</h1>
        <p>Provide model inputs and a payoff expression that references <code>price</code> (terminal) and <code>path</code> (full path).</p>
        <form method="post">
            <div class="grid">
                {% for name, label in [('spot','Spot price'),('maturity','Maturity (years)'),('rate','Risk-free rate'),('volatility','Volatility'),('steps','Steps per path'),('paths','Number of paths')] %}
                    <label>{{ label }}<input name="{{ name }}" value="{{ request.form.get(name, defaults[name]) }}" required></label>
                {% endfor %}
            </div>
            <label>Payoff expression
                <textarea name="payoff" rows="2" required>{{ request.form.get('payoff', defaults['payoff']) }}</textarea>
            </label>
            <button type="submit">Run simulation</button>
        </form>
        {% if message %}
            <div class="result {{ 'error' if result_payload is none else '' }}">{{ message }}</div>
        {% endif %}
        {% if result_payload %}
            <div class="result">
                <h3>Result</h3>
                <p><strong>Price:</strong> {{ '%.6f'|format(result_payload['price']) }}</p>
                <p><strong>Paths simulated:</strong> {{ result_payload['path_count'] }} | <strong>Steps per path:</strong> {{ result_payload['steps'] }}</p>
                <p><strong>Sample payoffs:</strong> {{ result_payload['sample_payoffs'] }}</p>
                <details>
                    <summary>Show sample paths (first 3)</summary>
                    <pre>{{ result_payload['sample_paths']|tojson(indent=2) }}</pre>
                </details>
            </div>
        {% endif %}
        <h2>API usage</h2>
        <p>Send a JSON POST to <code>/api/price</code> with the same fields as the form:</p>
        <pre>{
  "spot": 100,
  "maturity": 1,
  "rate": 0.05,
  "volatility": 0.2,
  "steps": 50,
  "paths": 10000,
  "payoff": "max(price - 100, 0)"
}</pre>
    </body>
    </html>
    """

    return render_template_string(template, message=message, result_payload=result_payload, defaults=defaults)


@app.post("/api/price")
def api_price():
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object.")
        params, payoff_expression = _parse_inputs(payload)
        payoff_fn = payoff_from_expression(payoff_expression)
        result = monte_carlo_option_price(payoff=payoff_fn, **params)
        return jsonify(_format_result(result))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
