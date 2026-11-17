# Code Style

Conventions observed in this codebase. Match what's already there in the file/module you're editing rather than introducing a new style.

## Naming

- Functions, methods, and variables: `snake_case` (`check_if_need_open_trade`, `trading_strategy`).
- Classes are inconsistently named across the codebase — some `PascalCase` (`TradingStrategyBase`, `OandaApi`, `Order`), some `Pascal_Case_With_Underscores` (`Trading_Session`, `Trade_Action`). Match the existing class's convention when extending it; don't rename existing classes to "fix" this.
- Private/internal methods use Python name-mangling (`__make_request`, `__handle_response`), not a single leading underscore.
- Config/constant-like values read from `.ini`/`.cfg` are assigned as instance attributes in `UPPER_CASE` when they map to indicator parameters (`self.SMA`, `self.DEV`) and `snake_case` otherwise (`self.units_to_trade`, `self.sl_perc`). Follow the existing pattern for the attribute's category rather than picking one style globally.

## Imports and module setup

- Each module computes its own ancestor directory and appends it to `sys.path` at import time:
  ```python
  file = Path(__file__).resolve()
  parent, root = file.parent, file.parents[1]
  sys.path.append(str(root))
  ```
  This is inconsistent between directories (see CLAUDE.md's "Import path quirk" section) — copy the exact pattern used by sibling files in the same directory, don't invent a new `sys.path` depth.
- `logger = logging.getLogger()` (the root logger, no name argument) is used everywhere instead of `logging.getLogger(__name__)`. Keep using the unnamed root logger for consistency with existing log handler setup.

## Types and docstrings

- Type hints are partial and inline, not comprehensive: `self.api: OandaApi = api`, `def get_position(self, instrument) -> pd.DataFrame`. Add inline hints on parameters/returns you touch, but don't do a sweeping pass to add hints across a whole file as a side effect of an unrelated change.
- Real docstrings are rare. Explanatory context is instead written as a bare triple-quoted string statement placed inside the function body (see `strategy_base.py::create_order`) or as a `#` comment directly above the relevant line. Follow whichever of the two the surrounding function already uses.
- `# type: ignore` comments appear next to dict-key assignments that confuse the type checker (`oanda_api.py`). Reuse this rather than restructuring the dict just to satisfy the checker.

## Error handling

- `OandaApi.__make_request` returns an `(ok: bool, data: dict)` tuple rather than raising on HTTP failure; callers check `ok` before touching `data`. Follow this tuple-return pattern for new broker-facing calls instead of raising exceptions across the API boundary.
- Exceptions that should stop a trading loop are raised explicitly with a constructed message and logged first (`logger.error(error); raise Exception(error)` in `strategy_base.py::submit_order`). Don't swallow an error that should halt order submission — log it and re-raise.
- Commented-out code (e.g. `# result = self.api.create_order(order=order)`) is sometimes left in place as a marker of an alternate path. Don't delete pre-existing commented-out lines unless the change you're making specifically concerns that line.

## Formatting

- f-strings are the standard string formatting method; avoid `%`-formatting or `.format()`.
- `logger.debug(...)` calls that print large structures (candle data, full request/response bodies) are frequently left commented out rather than removed, so they can be re-enabled during debugging. Follow this convention for new verbose debug logging rather than deleting it once it's no longer needed for the immediate task.
- Manual/smoke-test entry points live at the bottom of a module behind `if __name__ == "__main__":`, often followed by a one-line comment showing the invocation (`# python oanda_api.py`). Keep this pattern for any module that benefits from a standalone run.

## pandas

- Candle/indicator data is a single mutable `self.data: pd.DataFrame`, built up by assigning new columns in place (`strategy_calc.py`) rather than returning new DataFrames. Follow the existing column-assignment style instead of refactoring into a functional/immutable pipeline.
