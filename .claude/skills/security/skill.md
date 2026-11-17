# Security

This bot places real orders against a live OANDA account when `account_type=live` in `config/oanda.cfg`. Treat credential handling and order-submission code paths as high-stakes: a mistake here causes financial loss, not just a bug.

## Credentials

- `config/oanda.cfg` holds `access_token` and `account_id` and is gitignored (`*.cfg`). Never hardcode a token/account ID in a `.py` file, commit a filled-in `.cfg`, or print `self.access_token` / `self.SECURE_HEADER` to logs, console output, or commit messages.
- CI materializes `config/oanda.cfg` from the `OANDA_CONFIG_DEMO` / `OANDA_CONFIG_LIVE` GitHub Actions secrets (`.github/workflows/`). Don't add a workflow step that echoes the config file, uploads it as a build artifact, or writes it somewhere world-readable on the EC2 host.
- `OandaApi.__init__` builds `self.SECURE_HEADER` with the bearer token and attaches it to `self.session.headers`. If you add new logging around requests (`__make_request`), log the URL/params/status, not `self.session.headers` or the raw request object.
- If you ever need to read or restate a token value (e.g. while debugging a 401), redact it in anything written to a file, log, or terminal output that could be shared — show at most the last 4 characters.

## Network calls

- All OANDA REST/streaming calls go through `https://api-fxtrade.oanda.com` / `https://api-fxpractice.oanda.com` (`oanda_api.py`). Don't downgrade to `http://` or disable TLS verification (no code currently sets `verify=False` — keep it that way).
- `account_type` (`practice` vs `live`) selects the hostname. When adding test/debug code or examples, default to pointing at `practice` and call out explicitly in the diff/PR if something targets `live`.

## Order submission / financial blast radius

- `TradingStrategyBase.submit_order()` gates the real `self.api.place_order(order=order)` call behind `if not self.unit_test:`. Any new manual-run or debug entry point that can reach `submit_order`/`place_order` must have an equivalent guard (`unit_test`, `backtest`, or a new explicit flag) so that running it by accident doesn't place a live order.
- `strategy.backtest = True` suppresses live-only logging/order submission paths (per CLAUDE.md). When adding a new live-only side effect (order placement, position close, alerting), check both `self.unit_test` and `self.backtest` the way existing code does, rather than adding an unconditional call.
- Stop-loss/take-profit math (`utils.convert_perc_to_pips`, `convert_perc_to_ls_price`, `convert_perc_to_tp_price`) directly determines real position risk. Treat changes to these functions, or to `sl_perc`/`tp_perc`/`trailing_sl` handling in `create_order()`, as high-risk: a sign error or unit mismatch here can submit an order with no effective stop-loss. Don't refactor this math without manually verifying the resulting price/distance against the strategy's config values.
- `OandaApi.place_order` raises/logs on `rejectReason` but otherwise trusts the broker response; don't add code that silently retries or resubmits an order on ambiguous failure without confirming the original order didn't fill (duplicate-order risk).

## Secrets in logs and backtest artifacts

- `logs/` (rotating per-pair/strategy logs) and `code/backtesting/data/*.pcl` are run artifacts, not secrets by default, but both can end up containing full request/response bodies if verbose debug logging is re-enabled (`oanda_api.py` has commented-out `logger.debug` lines that dump full candle/response data). These don't currently include the token, but double-check before enabling any new debug log that serializes `self.config`, `self.SECURE_HEADER`, or a full `requests.Response`/`Session` object.
- Don't commit anything from `logs/` or `code/backtesting/data/` — these are run output, not source, even though they may not be in `.gitignore` today.

## Dependency/deploy surface

- `.github/workflows/` deploys over SSH to EC2 on pushes to `demo`/`live`, and syncs Lambda zips under `code/lambda/` on change. Treat any modification to these workflow files, the SSH deploy step, or `code/lambda/start_ec2_lambda.py`/`stop_ec2_lambda.py` (which control real AWS EC2 instances) as a change that affects shared infrastructure — flag it explicitly rather than modifying silently as a side effect of an unrelated change.
- `code/trading/utils/errors.py` and exception handling throughout should fail closed for anything that could lead to an unintended trade (e.g. prefer raising/stopping the bot over swallowing an error and continuing to trade on stale/partial data).
