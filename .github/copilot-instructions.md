# Instructions for Copilot

## Git
- Work in the current folder and branch. Never create new branches or worktrees.
- Do not commit to main.
- Make small commits with short messages.

## Project
- pyTrade is a Python FOREX bot using the OANDA API. The account currency is GBP.
- Keep changes minimal. Do not refactor unrelated code.
- Keep existing function signatures backward compatible (add optional parameters only).
- Never edit ui_pyTrade_GUI_v2.py (it is generated from the .ui file).
- Never hardcode API keys or database paths. Use config.py and the PYTRADE_DB environment variable.
- Per-pair values (pip size, minimum stop, price precision) come from pyTrade_instruments.py.

## Style
- Python with type hints and short docstrings.
- Be concise. Do not add extra files, comments or tests unless asked.
