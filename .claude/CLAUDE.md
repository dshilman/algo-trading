# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An automated forex trading bot for the OANDA platform. It streams live prices, builds 5-minute candles, computes technical indicators, and runs pluggable strategy classes (MACD, mean-reversion, momentum) that decide when to open/close trades. Includes a backtesting framework and AWS EC2/Lambda deployment plumbing. Educational project — see Risk Disclaimer in README.md.

## Commands

Install dependencies:
```bash
pip install -r code/requirements.txt
```

Run a single trading pair bot (strategy key must exist in `code/trading/pairs.ini`), from repo root:
```bash
python3 code/trading/trading_bot.py EUR_USD#1
```

Start/stop/restart all configured pairs (reads the pair list hardcoded in these scripts, run from repo root):
```bash
./start_trading.sh
./stop_trading.sh
./restart_trading.sh
```

Run backtesting (from `code/backtesting/`, note the relative `../../config` and `../trading/pairs.ini` paths baked into the script):
```bash
cd code/backtesting
python3 trading_bot_backtest.py EUR_USD#1 --days 30 --refresh True
```
`--refresh True` re-fetches candles from OANDA and caches them as a pickle in `code/backtesting/data/`; without it, the cached `.pcl` file for that pair/days combo is reused (and must already exist).

Run the "unit test" driver (from `code/unit/`; this is a live/manual run against the API with `unit_test=True`, not a pytest suite — there is no pytest/unittest test runner in this repo):
```bash
cd code/unit
python3 trading_bot_unit.py EUR_USD#1 --stop 5
```

No linter, formatter, or CI test step is configured. The `.github/workflows/` only deploy over SSH to EC2 on push to `demo`/`live` branches and sync Lambda zips on changes under `code/lambda/`.

## Configuration

- `config/oanda.cfg` — OANDA credentials (`account_id`, `access_token`, `account_type` = `practice`/`live`); gitignored (`*.cfg`). CI workflows materialize it from the `OANDA_CONFIG_DEMO`/`OANDA_CONFIG_LIVE` secrets.
- `code/trading/pairs.ini` — one `[PAIR#N]` section per running strategy instance; `strategy=<module>.<ClassName>` (e.g. `macd_1.TradingStrategy`) picks which strategy class loads at runtime via `__import__`. Each section's key is the `trading_strategy` argument passed to `trading_bot.py`/`trading_bot_backtest.py`.
- `start_trading.sh`/`stop_trading.sh` hardcode the active `pair#strategy` set and must be kept in sync with `pairs.ini` and the `trader_oanda_*.sh` one-liner launcher scripts.

## Architecture

### Class hierarchy (strategy stack)

Each strategy class is built by layering mixins, each adding one concern on top of the previous (`code/trading/strategies/base/`):

```
TradingStrategyBase      # loads pairs.ini config, builds Order objects, submits orders via OandaApi
  -> TradingStrategyCalc    # raw ticks -> 5-min OHLC candles, computes indicators (SMA/BB/RSI/EMA/momentum/prediction)
    -> TradingStrategyExec    # the open/close/stop-loss/take-profit decision loop (determine_trade_action)
      -> TradingStrategyMACD | TradingStrategyMeanReverse   # indicator sets specific to the family
        -> macd_1 / macd_2 / mean_reverse_1 / mean_reverse_2 / momentum   # concrete entry/exit rules
```

Concrete strategies (leaf classes in `code/trading/strategies/*.py`) only implement `check_if_need_open_trade()` and, optionally, override `check_if_need_close_trade()`/`calc_indicators()`/`set_strategy_indicators()`. Everything else (position tracking, stop-loss/take-profit, pause windows, order submission) is inherited from the base chain — read `strategy_exec.py` before touching entry/exit logic, since most of the state machine lives there, not in the leaf strategy files.

### Runtime flow (`code/trading/trading_bot.py` — `Trader`)

1. `Trader.__init__` reads `pairs.ini`, dynamically imports the configured strategy class, and constructs it.
2. `start_trading()` reconciles any existing broker position (`reconcile_positions()`), then spawns two daemon threads:
   - `start_streaming()` — opens the OANDA price stream and pushes `(time, mid, bid, ask)` ticks into a shared `deque` (`ticker_data_deque`), guarded by `ticker_data_lock`. Reconnects on error up to `MAX_ERROR_COUNT`.
   - `refresh_strategy()` — every 30s, snapshots the deque, resamples ticks into 5-minute candles (`to_5_min_candles`), recomputes indicators, and calls `strategy.execute_strategy()`.
3. `determine_trade_action()` (in `strategy_exec.py`) is the core gate: if flat and within a trading window and spread is acceptable, ask the concrete strategy whether to open; if a full position is held, check stop-loss first, then the concrete strategy's close logic.
4. Trade/P&L bookkeeping is centralized in `Trading_Session` (`code/trading/dom/trading_session.py`), which is also thread-locked and prints a tabulated trade report at session end.

Backtesting (`code/backtesting/trading_bot_backtest.py`) reuses the exact same strategy classes, just replays historical candles row-by-row through `set_strategy_indicators()` + `determine_trade_action()` instead of running the streaming/threading loop — so changes to `strategy_exec.py`/`strategy_calc.py` affect both live trading and backtests identically. `strategy.backtest = True` suppresses live-only logging/order submission paths.

### Import path quirk

Modules add their own ancestor directory to `sys.path` at import time (`file.parents[1]`), and this is inconsistent between files — e.g. `code/trading/trading_bot.py` adds `code/` (so `trading.dom...` imports resolve), while `code/trading/api/oanda_api.py` adds `code/trading/` (so it imports `dom.order`/`utils.utils` without the `trading.` prefix). This only works end-to-end because running any entry point from repo root (`trading_bot.py`, `trading_bot_backtest.py`, `trading_bot_unit.py`) transitively imports every module and each one's `sys.path.append` call accumulates. If you add a new module or run a file directly/standalone, match the existing import style of sibling files in that same directory rather than introducing a new convention.

### Key domain objects (`code/trading/dom/`)

- `Trade_Action` — immutable intent (open/close, units, price, sl/tp flags) returned by strategy decision methods.
- `Order` — broker-facing order payload (stop-loss as fixed price or trailing distance, take-profit price) built by `TradingStrategyBase.create_order()`.
- `Trading_Session` — per-run trade log, running P&L, and open-position unit count (`have_units`), which `trading_bot.py` reconciles against the live broker position on startup.

### APIs (`code/trading/api/`)

- `OandaApi` — all broker I/O: REST candle fetch (`get_latest_price_candles`, `get_price_candles`), streaming (`stream_prices`), order placement (`place_order`), and position lookup (`get_position`).
- `yfinance_api.py` — an alternate/experimental data source (Yahoo Finance), not wired into `trading_bot.py`.

### Indicators (`code/trading/utils/tech_indicators.py`)

Rolling-window functions applied via `.rolling(n).apply(...)`: RSI, linear-regression slope/next-value prediction (`scikit-learn`), and a custom momentum/strength measure. These are the building blocks `strategy_calc.py` wires into `self.data` columns every refresh cycle.

## Repository layout

```
code/
  trading/           # live bot: api/, dom/, strategies/ (base/ + concrete), utils/, pairs.ini, trading_bot.py
  backtesting/        # trading_bot_backtest.py + cached data/results in data/
  lambda/             # AWS Lambda EC2 start/stop handlers
  unit/               # trading_bot_unit.py — manual limited-iteration run, not an automated test suite
  explore/            # Jupyter notebooks used for strategy prototyping
config/
  oanda.cfg           # gitignored credentials; crontab.txt for scheduled start/stop
logs/                 # rotating per-pair/strategy logs, written by both live and backtest runs
```
