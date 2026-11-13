# pyTrade: Secondary Strategy Backtest - Setup, Run and Analysis Guide

Keep this file in `~/pieTrade`. Open it whenever you want to build, run or read the backtests that choose the secondary strategy.

## What this is (in plain English)

The bot trades the **EMA Trend Following** strategy first (the **primary**). When it finds no signal, it tries a **secondary** strategy. The current secondary (Breakout) trades more often but loses more than it wins.

There are two candidate replacements:

- **COA 1 - `Breakout_V2`**: the same breakout idea with stricter rules and quicker exits.
- **COA 2 - `Range_Reversion`**: a new strategy that trades quiet, sideways markets. Those are the markets where the EMA strategy never fires.

Live trading produces too few trades to tell which is better. A **backtest** replays the last 12 months of real 15-minute candles through the bot's own strategy code, one candle at a time, as if it were trading live. It records every trade it *would* have made. Hundreds of trades take minutes instead of months.

```
OANDA history     ->  data/*.csv               (downloaded once, then cached)
pyTrade_backtest.py  ->  results/<run>.csv     (one row per simulated trade)
pyTrade_backtest_report.py  ->  tables, PASS/FAIL checks, equity curves
```

You run the backtest **four times**, changing only the secondary strategy:

| Run | `--secondary` | What it tells you |
|---|---|---|
| Baseline | `none` | EMA strategy alone. The number to beat |
| Current | `breakout` | Your current setup. Should confirm the losses you saw live |
| COA 1 | `breakout_v2` | Does the stricter breakout earn its place? |
| COA 2 | `range` | Does the new range strategy earn its place? |

> The backtest is a **fair comparison**, not a profit forecast. It cannot copy the AI agent's hourly pair choice or the news filter, and real spreads are sometimes wider. Treat any result as "probably a bit better than live".

---

## Key ideas you need first

**R (risk unit).** Every trade risks a fixed amount: the distance from entry to stop loss. That amount is **1R**. A trade that hits a 1.5R take profit scores **+1.5R**. One that hits its stop scores **-1R**. One closed early at half way to the stop scores **-0.5R**. Measuring in R makes trades on different pairs and position sizes comparable. Your money result is roughly R × your risk per trade (e.g. 1% of the account).

**Win rate alone means nothing.** A strategy with 1.5R targets only needs to win **40%** of trades to break even. The formula is `break-even win % = 1 / (1 + RR)`:

| Take profit (RR) | Break-even win rate |
|---|---|
| 1.0R (EMA strategy) | 50% |
| 1.5R (Breakout_V2) | 40% |
| 2.0R (old Breakout) | 33% |
| ~0.8-1.2R (Range_Reversion, varies) | 45-55% |

**Spread eats small stops.** OANDA charges a spread on every trade. With a 1.2 pip spread and an 8 pip stop, every trade starts **0.15R** down. That is why the backtest must include spread. It is also why very tight stops on 15-minute charts often look good on paper and lose live.

**In-sample vs out-of-sample.** The 12 months are split. The **first 8 months (in-sample)** are for adjusting settings. The **last 4 months (out-of-sample, OOS)** are kept as an exam the strategy has never seen. **Only out-of-sample results decide the winner.** If you tune and judge on the same data, you are just fitting the past, and the strategy will disappoint live.

---

## Part 1: One-time setup

Open a terminal (`Ctrl + Alt + T`). The `(base)` at the start of the prompt means Anaconda is active.

### 1.1 Build the files with Copilot

Run these Copilot prompts in order (they were given in the planning chat). Commit to Git after each one.

1. `tools/breakout_report.py` - live-trade diagnosis
2. `pyTrade_backtest.py` - the backtester
3. `pyTrade_BreakoutV2_Strategy.py` - COA 1
4. `pyTrade_RangeReversion_Strategy.py` + `validate_range` in `pyTrade_trade_guards.py` - COA 2
5. `pyTrade_backtest_report.py` - the analysis report (**Prompt R** below)

**Prompt R - analysis report:**

```
Create pyTrade_backtest_report.py (standalone; no other file changes). Read every results/*.csv from pyTrade_backtest.py; run name = file name. Arg --sample in|out|all (default out).
1. Per run (all strategies): trades, trades/week, win %, avg R, total R, profit factor, max drawdown R, longest losing streak.
2. Per run, secondary strategy rows only: same columns + break-even win % (1/(1+avg win R/avg loss R)) and PASS/FAIL for avg R >= 0.10, PF >= 1.2, trades >= 60.
3. Per run vs run "none": total R difference and drawdown ratio; PASS if total R higher and ratio <= 1.5.
4. Secondary rows: avg R + count by pair, by UTC entry hour, by exit reason.
5. Save results/{run}_equity.png (cumulative R vs exit time, all strategies).
Last line: run passing every check with highest total R, else "Keep EMA only".
```

**Prompt F - only if the results files are not named after the secondary:**

```
In pyTrade_backtest.py only: save trades to results/{secondary}.csv (overwrite). Add --spread-mult (default 1.0) multiplying every SPREAD_PIPS value. Reply with a short summary.
```

### 1.2 Check the files exist

```
cd ~/pieTrade
ls pyTrade_backtest.py pyTrade_backtest_report.py pyTrade_BreakoutV2_Strategy.py pyTrade_RangeReversion_Strategy.py tools/breakout_report.py
```

All five names should print with no "No such file" error.

### 1.3 Check the libraries

```
python3 -c "import oandapyV20, pandas, pandas_ta_classic, matplotlib; print('libraries OK')"
```

If you see `ModuleNotFoundError`, install the missing library, e.g. `pip install matplotlib`, then repeat.

### 1.4 Check the backtester's options

```
python3 pyTrade_backtest.py --help
```

You should see `--pairs`, `--months`, `--oos-months`, `--secondary` (and `--spread-mult` if you ran Prompt F). If any are missing, ask Copilot to add just that argument.

### 1.5 Check OANDA settings

The backtester downloads history with your **practice** key. It never places orders.

```
python3 -c "import config; print('OANDA key set:', bool(config.OANDA_API_KEY.strip()), '| environment:', config.OANDA_ENVIRON)"
```

You want `OANDA key set: True | environment: practice`.
**Never paste config.py (or the key) into chats, Copilot or Git.** Also add `data/` and `results/` to `.gitignore` - they are large and can be rebuilt.

### 1.6 Setup checklist

- [ ] Files exist (1.2)
- [ ] Libraries import (1.3)
- [ ] `--help` shows the options (1.4)
- [ ] OANDA key set, environment `practice` (1.5)
- [ ] `data/` and `results/` in `.gitignore`

---

## Part 2: How the backtester works inside

You don't need to edit this code, but knowing what each piece does tells you where to look when results seem wrong. Copilot may use slightly different names. Search the file for the job described.

### 2.1 The parts of `pyTrade_backtest.py`

| Part (likely name) | What it does |
|---|---|
| `parse_args()` | Reads `--pairs`, `--months`, `--oos-months`, `--secondary` |
| `load_candles(pair, gran)` | Downloads M15 and H1 candles with `InstrumentsCandlesFactory` (OANDA only gives 5,000 candles per request, so this pages through them). Saves to `data/{pair}_{gran}.csv`. Next time it reads the file instead of downloading |
| engine map | Turns `breakout` / `breakout_v2` / `range` into the strategy classes. `TrendFollowingEngine` is always primary |
| `run_pair(pair)` | The main loop - see 2.2 |
| `simulate_exit(...)` | Walks forward candle by candle checking stop loss, take profit and `manage()` |
| `summarise(trades)` | Prints the quick table at the end of a run |

### 2.2 The main loop, one candle at a time

For each closed 15-minute candle `i`:

1. **Skip if a trade is already open** on this pair (the bot only holds one per pair).
2. **Ask the primary.** Call the EMA engine's signal method on candles `0..i` only - never later ones.
3. **Check the guards.** Run the same `TradeGuards` checks the live bot's `_try_entry` uses. The H1 trend check only sees **H1 candles that had closed by then**.
4. **If no primary signal**, ask the secondary the same way (with its own guard: `validate_breakout` or `validate_range`).
5. **Enter at the open of candle `i+1`**, plus half the spread for a buy, minus half for a sell. You can never trade at the price of the candle that gave the signal - it has already closed.
6. **Follow the trade** candle by candle until it exits:
   - Low touches the stop loss → exit at the stop, **-1R**.
   - High touches the take profit → exit at the target.
   - **Both in the same candle** → count it as the **stop**. You can't tell which came first, so assume the worst.
   - `manage()` returns `"close"` → exit at that candle's close (the quick-exit rules).
7. **Record the trade** and carry on from the candle after the exit.

### 2.3 What each strategy engine must provide

| Method | Job |
|---|---|
| `strategy_name` | Label saved on every trade (`EMA_TrendFollowing`, `Breakout`, `Breakout_V2`, `Range_Reversion`) |
| `add_indicators(df)` | Adds the indicator columns (EMAs, ATR, Donchian, Bollinger, RSI, ADX). Run once on the whole history. These indicators only look backwards, so that is safe |
| signal method (existing name) | Looks at the latest candle and returns BUY / SELL / nothing, plus stop loss and take profit |
| `manage(trade, df)` | *New for Breakout_V2 and Range_Reversion.* Called every candle while the trade is open. Returns `"close"` to exit early, otherwise `None` |

The `manage()` rules in plain English:

- **Breakout_V2**: "The breakout failed" (closed back inside the range within 4 candles), or "it's going nowhere" (6 candles and never reached +0.5R).
- **Range_Reversion**: "The range has turned into a trend" (ADX above 25), or "it's taking too long" (8 candles).

### 2.4 The guards

| Guard (in `pyTrade_trade_guards.py`) | Used for | Passes when |
|---|---|---|
| trend-following check | EMA strategy | M15 EMA20/50 agree, ADX(14) > threshold, H1 trend agrees |
| `validate_breakout` | Breakout, Breakout_V2 | Close is beyond the level, ADX OK, H1 trend agrees |
| `validate_range` (new) | Range_Reversion | M15 ADX < 20 and H1 price close to its EMA50 (no strong H1 trend) |

### 2.5 What a results row means

| Column | Meaning |
|---|---|
| `pair`, `strategy`, `direction` | What was traded |
| `entry_time`, `exit_time` | UTC times |
| `r` | Result in R (after spread) |
| `bars_held` | Number of 15-minute candles the trade was open |
| `exit_reason` | `sl`, `tp`, or the `manage()` reason (e.g. `failed_breakout`, `time_stop`, `adx_rising`) |
| `sample` | `in` (first 8 months) or `out` (last 4 months) |

---

## Part 3: Running the backtests

### 3.1 Step A - diagnose your live trades first (5 minutes)

```
cd ~/pieTrade
python3 tools/breakout_report.py
```

Write down for each strategy: number of trades, win %, average R. Also note:

- **Hours where Breakout lost most.** If losses cluster outside 07:00-10:00 and 12:00-15:00 UTC, that supports COA 1's session rule.
- **Win % by ADX bucket.** If low-ADX breakouts lose most, the market was ranging, which supports COA 2.
- **% of losses closed within 60 minutes.** If high, breakouts are failing almost immediately, which supports COA 1's failed-breakout exit.

### 3.2 Step B - first download and calibration run

Pick the pairs from your session table (example below - use your own). The first run downloads about 25,000 candles per pair, so give it a few minutes.

```
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary breakout
```

**Calibration check - do this before trusting anything.** Compare the backtest's numbers for `EMA_TrendFollowing` and `Breakout` with your live numbers from Step A. They won't match exactly (different time period, no AI agent, no news filter). But the story should agree:

- Breakout should lose in the backtest too.
- The EMA strategy's average R should be the same sign as live.

If the backtest shows Breakout winning big, the backtester is probably "seeing the future". Go to **Troubleshooting** before going further.

### 3.3 Step C - the four comparison runs

Use **exactly the same** `--pairs`, `--months` and `--oos-months` every time. Only `--secondary` changes.

```
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary none
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary breakout
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary breakout_v2
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary range
```

Then:

```
ls results/
```

You should see `none.csv`, `breakout.csv`, `breakout_v2.csv`, `range.csv`.

### 3.4 Step D - spread stress test

Real spreads widen at night and around news. Re-run the two candidates with spreads 50% wider (needs Prompt F). **Save the normal results first**, because the run overwrites the file:

```
cp results/breakout_v2.csv results/breakout_v2_normal.csv
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 12 --oos-months 4 --secondary breakout_v2 --spread-mult 1.5
mv results/breakout_v2.csv results/breakout_v2_spread15.csv
mv results/breakout_v2_normal.csv results/breakout_v2.csv
```

Repeat for `range`. A strategy whose average R drops from +0.15 to below zero with slightly wider spreads is too fragile to trade.

---

## Part 4: Analysing the results

### 4.1 Run the report

```
python3 pyTrade_backtest_report.py
```

This shows **out-of-sample only** (the exam results). Use `--sample in` when tuning (Part 5).

### 4.2 What each number means

| Number | Plain meaning | Good | Worry |
|---|---|---|---|
| **trades** | How many trades in the period | 60+ for the secondary in 4 months | Under 30: too few to judge, it could be luck |
| **trades/week** | How busy the strategy is | Whatever you are happy with | - |
| **win %** | % of trades that made money | Above its break-even win % | Below break-even |
| **avg R** (expectancy) | **Average result per trade. The most important number** | +0.10R or more | Zero or negative |
| **total R** | avg R × trades - the overall result | Higher than baseline | Lower than baseline |
| **profit factor (PF)** | Total won ÷ total lost. 1.0 = break-even | 1.2+ | Under 1.1 |
| **max drawdown R** | Worst drop from a high point in the running total | Small compared with total R | Bigger than total R |
| **longest losing streak** | Most losses in a row | - | Ask: could I sit through this live? |

**Worked example.** 100 trades: 40 wins averaging +1.5R, 60 losses averaging -1R.
Won = 60R, lost = 60R, total = **0R**, avg R = **0.00**, PF = **1.00**.
A 40% win rate sounds poor, and a 1.5R target sounds good, but together they make nothing. This is why you judge on **avg R and PF**, not win rate.

### 4.3 Read the report section by section

**Section 1 - whole run.** Find the `none` row: that is your baseline. Each other row is "EMA + that secondary". Quick read: did adding the secondary raise **total R** without making **max drawdown** much worse?

**Section 2 - secondary only.** This isolates the secondary's own trades. It must pass all three checks:

- [ ] avg R ≥ +0.10
- [ ] profit factor ≥ 1.2
- [ ] at least 60 trades

Also compare **win %** with the **break-even win %** shown next to it. A healthy strategy sits clearly above its break-even line, not just touching it.

**Section 3 - versus baseline.** Must pass:

- [ ] total R higher than `none`
- [ ] drawdown ratio ≤ 1.5 (the worst drop is no more than 1.5× the baseline's)

**Section 4 - breakdowns (the "why").** Use these to understand the result, not to pick the winner:

- **By pair.** Is the profit spread across pairs, or does one pair carry everything? One-pair profit is fragile. If one pair loses badly every time, note it - the AI agent could avoid it later.
- **By UTC hour.** Breakout_V2 should only show trades in its session hours. If losses cluster in one hour, that is a candidate filter to test **in-sample**.
- **By exit reason.** This tells you whether the quick exits are working:
  - Many `failed_breakout` / `time_stop` exits with small losses (about -0.3R) **instead of** -1R stops = the quick exits are doing their job.
  - Quick exits with *positive* average R = they may be cutting winners. Test loosening them in-sample.
  - Mostly `sl` exits = the entry rules are the problem, not the exits.

**Section 5 - equity curves.** Open the PNGs:

```
xdg-open results/range_equity.png
```

- **Good**: a steady staircase upwards with shallow dips.
- **Bad**: flat for months, then one big jump. The profit came from a single lucky spell.
- **Bad**: rising in-sample, flat or falling in the last 4 months. The strategy was fitted to the past.

### 4.4 Making the decision

1. Cross out any candidate that fails a Section 2 or Section 3 check.
2. Cross out any candidate whose avg R goes negative in the spread stress test (3.4).
3. Cross out any candidate whose equity curve is one lucky jump.
4. **Of what's left, pick the highest total R.** The report's last line does steps 1 and 4 for you, but do 2 and 3 by eye.
5. **If nothing is left: keep the EMA strategy alone** (single-strategy mode). Fewer trades that make money beat more trades that lose it.

Record the outcome in this table so you can compare later:

| Run | Sec. trades | Sec. win % | Sec. avg R | Sec. PF | Total R | Max DD R | Stress avg R | Result |
|---|---|---|---|---|---|---|---|---|
| none | - | - | - | - | | | - | baseline |
| breakout | | | | | | | - | |
| breakout_v2 | | | | | | | | |
| range | | | | | | | | |

### 4.5 Red flags that mean the backtester is wrong, not brilliant

| What you see | Likely cause |
|---|---|
| Win % above 70% with 1.5R+ targets | Look-ahead: the strategy is seeing later candles |
| Avg R above +0.5 on any strategy | Look-ahead or no spread being charged |
| Breakout wins in backtest but lost live | Donchian channel includes the current candle (should be shifted by 1), or entry at signal-candle close |
| Hardly any `sl` exits | The same-candle rule (SL first) isn't applied |
| H1-filtered trades look too good | H1 candles still forming are being used |

Ask Copilot to check the specific suspect, e.g.:

```
In pyTrade_backtest.py, confirm (don't change other files): entry uses next candle open, DC levels are shifted by 1, only closed H1 candles are used, SL wins ties. Fix any that fail; reply with a short summary.
```

---

## Part 5: Tuning (in-sample only)

Only tune if a candidate is **close** to passing (e.g. avg R +0.05). Don't try to rescue one that is clearly losing.

1. Use `python3 pyTrade_backtest_report.py --sample in`. **Never look at out-of-sample while tuning.**
2. Change **one setting at a time** in `config.py` (the strategies read them with `getattr`), e.g. `BO_SQUEEZE_PCT` 0.2 / 0.3 / 0.4.
3. Try **at most 3 values** per setting and **at most about 5 tuning runs** per strategy. More than that and you are fitting noise.
4. Prefer a value whose **neighbours also do well**. If 0.3 is great but 0.2 and 0.4 are terrible, 0.3 was luck.
5. When finished, run once more and read **out-of-sample** - once. That is the exam result. Don't go back and tune again because the exam went badly.

---

## Part 6: After choosing - forward test on demo

1. Run the Step 7 Copilot prompt from the planning chat. It wires the winner into settings, the bot's position checks (`manage()`) and the AI agent.
2. Set `secondary_strategy` on the Settings page. Run on the **practice** account for 2-4 weeks.
3. Weekly: `python3 tools/breakout_report.py` and compare the secondary's live avg R with the backtest's out-of-sample avg R.

**Go-live checklist (all must be true):**

- [ ] At least 30 live secondary trades
- [ ] Live avg R is positive
- [ ] Live avg R is at least half the backtest's out-of-sample avg R
- [ ] No losing streak longer than the backtest's longest streak + 3

If the live result is much worse than the backtest, the usual causes are wider real spreads, news spikes, and the AI agent choosing pairs that suit the primary but not the secondary. Check the by-pair breakdown in the live report before changing any rules.

---

## Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Missing library or wrong Python | `pip install <name>`; check `which python3` is the Anaconda one |
| OANDA 401 / authorisation error | Wrong or expired key | Fix `OANDA_API_KEY` and `OANDA_ENVIRON` in config.py |
| Download stops part-way | Network blip or rate limit | Run again; cached candles are reused |
| Results look odd after changing `--months` | Old cached candles | Delete `data/` and run again |
| `0 trades` for the secondary | Rules too strict, or the guard always fails | Check `exit_reason`/logs; for `range`, confirm the ADX > threshold guard isn't applied to it |
| Very slow (over 30 minutes) | The signal method recalculates indicators every candle | Ask Copilot: "make the backtest loop reuse precomputed indicator columns" |
| Report says a run is missing | File not named after the secondary | Run Prompt F, then re-run the backtests |
| Backtest and live disagree completely | Look-ahead bias | Part 4.5 |

If stuck, copy the exact error text (never the keys) and ask for help.

---

## Quick reference

| Task | Command |
|---|---|
| Go to the bot folder | `cd ~/pieTrade` |
| Live-trade diagnosis | `python3 tools/breakout_report.py` |
| One backtest run | `python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD --months 12 --oos-months 4 --secondary range` |
| Out-of-sample report | `python3 pyTrade_backtest_report.py` |
| In-sample report (tuning) | `python3 pyTrade_backtest_report.py --sample in` |
| Open an equity curve | `xdg-open results/range_equity.png` |
| Clear cached candles | `rm -r data/` |

| File | What it does |
|---|---|
| `pyTrade_backtest.py` | Replays history through the strategies and saves simulated trades |
| `pyTrade_backtest_report.py` | Turns the results into tables, PASS/FAIL checks and equity curves |
| `pyTrade_BreakoutV2_Strategy.py` | COA 1 strategy |
| `pyTrade_RangeReversion_Strategy.py` | COA 2 strategy |
| `tools/breakout_report.py` | Win/loss analysis of your real trades from the database |
| `data/` | Cached OANDA candles (safe to delete) |
| `results/` | One CSV per run plus equity curve PNGs |
