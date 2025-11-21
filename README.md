# 20251121 Monte Carlo option pricer

This repo contains a Monte Carlo option pricer that accepts arbitrary payoff expressions and a simple Flask web server for browser or API-based simulations.

## Setup
1. (Optional) Create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run the web server
Start the Flask server:
```bash
python web_option_server.py
```
By default it listens on `http://0.0.0.0:8000`.

### Browser form
Open `http://localhost:8000` and enter:
- `spot`, `maturity`, `rate`, `volatility`, `steps`, `paths`.
- `payoff`: an expression using `price` (terminal) and `path` (full trajectory), e.g. `max(price - 100, 0)`.

The page returns the estimated price plus sample payoffs/paths.

### JSON API
Send a POST to `/api/price` with the same fields:
```bash
curl -X POST http://localhost:8000/api/price \
  -H "Content-Type: application/json" \
  -d '{
        "spot": 100,
        "maturity": 1,
        "rate": 0.05,
        "volatility": 0.2,
        "steps": 50,
        "paths": 10000,
        "payoff": "max(price - 100, 0)"
      }'
```
The response contains the price and sample paths/payoffs.

## CLI Monte Carlo pricer
You can still run the existing CLI directly:
```bash
python monte_carlo_option.py --payoff "max(price - 100, 0)" --paths 10000 --steps 50
```
