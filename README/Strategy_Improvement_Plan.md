# pyTrade: Strategy Improvement and Go-Live Plan

Keep this file in `~/pieTrade` next to `Backtest_README.md`. It takes you from the first comparison report (12 Nov 2026) to a go / no-go decision, using automated tests wherever possible.

## Where we are (plain English)

The first comparison report said **"Keep EMA only"**. But the full picture is worse, and more useful, than that:

| Finding | Evidence (last 4 months, out-of-sample) | What it means |
|---|---|---|
| **The primary (EMA) strategy is losing** | `none`: 413 trades, avg R **-0.14**, PF 0.75 | This is the biggest problem. No secondary can rescue a losing primary |
| **Breakout_V2 barely trades** | 8-9 trades in 4 months | The rules are so strict it almost never fires. We can't judge it yet |
| **Range_Reversion barely trades** | 3 trades in 4 months | Same: too strict to judge |
| **The validator hurts every strategy** | `none` -55.9R vs `none_val` -62.8R; Breakout 0.00 vs -0.08 | Early exits are cutting winners more than they save losers |
| **"Breakout beats none" is misleading** | `breakout` passes "Versus none" | Only because breakout trades fill the one-trade-per-pair slot, which blocks some losing EMA trades. The breakout itself only broke even |

**Why the new strategies don't fire (most likely):**

- **Breakout_V2** asks for a squeeze (a quiet, low-volatility market) **and** passes through the guard that needs ADX above 24 (a strong trend). These two rules contradict each other. Right after a squeeze, ADX is almost always low.
- **Range_Reversion** stacks five filters (low ADX, Bollinger pierce, RSI below 35, confirmation candle, H1 near EMA50). Each one is sensible, but together they almost never line up. The general ADX > 24 guard may also still be blocking it.

The **funnel report** in Phase 0 will prove which filter is the blocker before anything is changed.

**A note on the last 4 months.** You have now looked at that period several times. It is no longer a clean "exam". From now on the plan uses three things it hasn't seen: **walk-forward testing**, **pairs never used for tuning**, and the **demo account**.

> Be prepared for a valid outcome of "no strategy has an edge yet". Most simple 15-minute forex strategies don't. The point of this plan is to find out cheaply on history, not expensively with real money.

---

## The plan at a glance

| Phase | What | How long | Automated? | Gate to pass |
|---|---|---|---|---|
| 0 | Upgrade the test tools + funnel check | 1 evening | Copilot prompts | Tools run; blockers found |
| 1 | Fix the **primary** (EMA) | Overnight run | Yes | Primary out-of-sample avg R > 0 |
| 2 | Make the secondaries **fire**, then tune | Overnight run | Yes | Each ≥ 60 trades, avg R ≥ +0.05 |
| 3 | Test running **all three together** (EMA → V2 → Range) | 1 run | Yes | Whole bot beats every single-strategy setup |
| 4 | Robustness (unseen pairs, wider spreads) + **go-live check** | 1 run | Yes | Script prints `GO DEMO` |
| 5 | Demo account forward test | 4 weeks | Weekly cron report | Live matches backtest |
| 6 | Live, small risk | 4 weeks | Weekly cron report | Then scale up |

---

## Key ideas for this plan

**Walk-forward testing.** Instead of tuning once and hoping, the computer repeats this four times:

```
24 months of history
|------ train 12m ------|- test 3m -|
      |------ train 12m ------|- test 3m -|
            |------ train 12m ------|- test 3m -|
                  |------ train 12m ------|- test 3m -|
```

In each **train** period it picks the best settings. It then trades the next **test** period with those settings, without changing anything. The four test periods together give 12 months of honest results, because every test trade used settings picked *before* that period. This is the standard professional method, and it is fully automatic.

**One setting at a time.** Testing every combination of 8 settings would mean hundreds of runs and guarantees "finding" something that only worked by luck. Instead, the optimiser tries each setting's values in turn, keeps the best, and moves on. That is about 15-20 runs per window.

**The score.** Settings are ranked by `avg R × √trades`. This rewards a real edge (avg R) but also needs enough trades to trust it. Settings with fewer than 30 trades in a train period score zero.

**Same settings in backtest and live.** All tuned settings are saved in one JSON file (`strategy_params.json`) that both the backtester and the bot read. That way the bot can't drift away from what was tested.

---

## Phase 0: Upgrade the test tools (one evening)

Run these Copilot prompts in order. Commit to Git after each one.

### Prompt 0.1 - backtester upgrades

```
In pyTrade_backtest.py only. Reply with a short summary.
1. --params FILE: JSON with optional keys primary, secondary, guards, validation (constructor kwargs for those objects) and config (attrs set on config before building). Missing keys = current defaults.
2. --from/--to YYYY-MM-DD limit the simulated period (indicators still warm up on earlier candles).
3. --secondary accepts a comma list (e.g. breakout_v2,range), tried in order after the primary.
4. --funnel: attach a logging.Handler to each engine/guard logger; when a candle gives no trade, count the last message (first 50 chars) per strategy; print counts sorted desc.
5. Also write results/{name}_summary.json: per strategy and all: trades, win %, avg R, total R, PF, max DD R.
6. --jobs N: run pairs in parallel processes.
```

### Prompt 0.2 - strategy settings become adjustable

```
Make ONLY these changes; each new value is a constructor kwarg whose default keeps current behaviour. Reply with a short summary.
- TrendFollowingEngine: allowed_hours (UTC hour list, None = all), max_trend_k (cap on |close-EMA50|/ATR, None = off).
- BreakoutV2Engine: squeeze_pct, hours, max_ema_dist_atr, rr_ratio, adx_mode "threshold"|"rising" (rising = ADX now > ADX 3 bars ago).
- RangeReversionEngine: adx_max, rsi_level (BUY below it, SELL above 100-it, None = off), bb_std, need_confirm_candle, h1_max_dist_atr.
- pyTrade_backtest.py and pyTrade_bot.py: skip the ADX>threshold guard for Range_Reversion and for engines with adx_mode "rising".
```

### Prompt 0.3 - walk-forward optimiser

```
Create pyTrade_optimise.py (no other file changes). Reply with a short summary.
Args: --grid FILE --pairs --months 24 --jobs N.
Grid JSON: {"secondary": "...", "base": params, "base_from": optional params file merged first, "steps": [{"path": "primary.rr_ratio", "values": [...]}, ...]}.
Walk-forward: train 12 months, test 3, step 3 (4 windows ending at the last candle).
Per window: start from base; for each step in order try each value by running pyTrade_backtest.py (subprocess, --live-validation, --params temp file, --from/--to train period, --tag wf_tmp); keep the best score = avg R * sqrt(trades) for the secondary (primary if secondary is none), -inf if trades < 30. Then run the chosen params on the test period.
Save results/wf_{secondary}.csv (window, chosen params, train and test summary per strategy), results/wf_{secondary}_trades.csv (all test trades, with a window column) and results/wf_{secondary}_final.json (last window's params).
```

### Prompt 0.4 - go-live check

```
Create pyTrade_golive_check.py (no other file changes). Reply with a short summary.
Args: --run NAME (reads results/wf_{NAME}_trades.csv), --baseline none, optional --stress FILE, --unseen FILE (backtest trade CSVs).
Print PASS/FAIL with the value for:
G1 whole bot: avg R >= 0.05, PF >= 1.15, total R > baseline run's total R.
G2 each non-primary strategy: trades >= 60, avg R >= 0.05, PF >= 1.10.
G3 total R positive in >= 3 of 4 windows.
G4 stress file avg R > 0.
G5 unseen file avg R > 0.
G6 max DD R <= 25 and longest loss streak <= 15.
Last line: "GO DEMO" or "NO GO: <failed gates>".
```

### Prompt 0.5 - the bot uses the same settings file

```
In pyTrade_bot.py only: if strategy_params.json exists, build engines, TradeGuards and Validation with its kwargs (same format as pyTrade_backtest.py --params) and log "Loaded strategy_params.json". Reply with a short summary.
```

### Check Phase 0 worked

1. Download 24 months of history (the cache only had 12):

```
cd ~/pieTrade
rm -r data/
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --oos-months 4 --secondary none --jobs 5
```

2. **Run the funnel** for both new strategies:

```
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --oos-months 4 --secondary breakout_v2 --funnel --jobs 5
python3 pyTrade_backtest.py --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --oos-months 4 --secondary range --funnel --jobs 5
```

How to read it: the top line is the filter that rejects the most candles. If one filter rejects almost everything that the others let through, it is the blocker. **Send me the funnel tables.** If the blocker is not one the grids below already test, we add it.

---

## Phase 1: Fix the primary (overnight)

The primary decides whether the bot can make money at all, so it comes first.

### What to change, and why

| Setting | Where | Current | Values to test | Why |
|---|---|---|---|---|
| `rr_ratio` (take-profit size) | `primary` | 1.0 | 1.0, 1.5, 2.0 | After spread, a 1R target only pays about +0.9R, so the strategy needs to win 53% of the time just to break even. A bigger target cuts the spread's share |
| `atr_multiplier` (stop size) | `primary` | 1.5 | 1.5, 2.0, 2.5 | A wider stop gets "noise-stopped" less, and spread costs a smaller fraction of R |
| `trend_filter_k` (minimum trend strength) | `primary` | 0.5 | 0.5, 1.0 | Live data hinted that trades with trend strength 1-2 did best |
| `max_trend_k` (don't chase) | `primary` | off | off, 2.0, 3.0 | Avoids buying after the move has already happened |
| `adx_threshold` | `guards` | 24 | 20, 24, 28 | Trades more often or more selectively |
| `allowed_hours` | `primary` | all | all, 07-15 UTC | Liquid hours have tighter spreads and cleaner trends |
| `enable_session_check` | `validation` | on | on, off | It closed 28% of EMA trades before target in calibration |
| `enable_time_check` | `validation` | on | on, off | Same question for the time limit |

### The grid file

Save as `grids/grid_primary.json`:

```json
{
  "secondary": "none",
  "base": {},
  "steps": [
    {"path": "primary.rr_ratio", "values": [1.0, 1.5, 2.0]},
    {"path": "primary.atr_multiplier", "values": [1.5, 2.0, 2.5]},
    {"path": "primary.trend_filter_k", "values": [0.5, 1.0]},
    {"path": "primary.max_trend_k", "values": [null, 2.0, 3.0]},
    {"path": "guards.adx_threshold", "values": [20, 24, 28]},
    {"path": "primary.allowed_hours", "values": [null, [7,8,9,10,11,12,13,14,15]]},
    {"path": "validation.enable_session_check", "values": [true, false]},
    {"path": "validation.enable_time_check", "values": [true, false]}
  ]
}
```

### Run it

```
cd ~/pieTrade
mkdir -p grids
nohup python3 pyTrade_optimise.py --grid grids/grid_primary.json --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --jobs 5 > wf_primary.log 2>&1 &
```

`nohup ... &` keeps it running after you close the terminal. Check progress with `tail -n 20 wf_primary.log`.

### Read the result

Open `results/wf_none.csv` and look at the **test** columns for each window.

- **Pass:** the 12 months of test trades have avg R > 0, and at least 3 of 4 windows are positive. Go to Phase 2.
- **Look at the chosen settings.** If all four windows pick the same values (e.g. `rr_ratio` 1.5 every time), that is a strong sign the setting is real. If they jump around, the setting doesn't matter much or the edge is weak.
- **Fail (avg R ≤ 0 even with the best settings):** stop here. The EMA pullback idea on 15-minute candles doesn't have an edge on these pairs. Send me `wf_none.csv`. The usual next experiment is the same strategy on **1-hour** candles, where spread costs far less per trade.

---

## Phase 2: Make the secondaries fire, then tune (overnight)

Each secondary uses the primary settings picked in Phase 1 (`base_from`), so it is tested alongside the improved primary.

**First target: frequency.** A secondary must produce at least **5 trades per week across the 5 pairs**. That is enough for about 60 trades in a 3-month test window. The grids start with the loosest sensible values so the optimiser can tighten from there.

### Breakout_V2 - what to change, and why

| Setting | Values | Why |
|---|---|---|
| `adx_mode` | threshold, rising | **The key fix.** "Rising ADX" means "a trend is starting", which is compatible with a squeeze. "ADX > 24" isn't |
| `squeeze_pct` | 0.3, 0.5, 0.7 | Lets "fairly quiet" markets count, not only "very quiet" ones |
| `hours` | London/NY opens only; 07-15 UTC | Wider window = more trades |
| `max_ema_dist_atr` | 2.0, 3.0 | Live data: 35 of 37 breakouts were entered more than 2 ATR from EMA50, and lost |
| `rr_ratio` | 1.5, 2.0 | Target size |
| `enable_breakout_checks` (validation) | on, off | The "Donchian re-entry" exit made the old breakout worse |

Save as `grids/grid_breakout_v2.json`:

```json
{
  "secondary": "breakout_v2",
  "base_from": "results/wf_none_final.json",
  "base": {"secondary": {"adx_mode": "rising", "squeeze_pct": 0.5}},
  "steps": [
    {"path": "secondary.adx_mode", "values": ["rising", "threshold"]},
    {"path": "secondary.squeeze_pct", "values": [0.3, 0.5, 0.7]},
    {"path": "secondary.hours", "values": [[7,8,9,12,13,14], [7,8,9,10,11,12,13,14,15]]},
    {"path": "secondary.max_ema_dist_atr", "values": [2.0, 3.0]},
    {"path": "secondary.rr_ratio", "values": [1.5, 2.0]},
    {"path": "validation.enable_breakout_checks", "values": [true, false]}
  ]
}
```

### Range_Reversion - what to change, and why

| Setting | Values | Why |
|---|---|---|
| `adx_max` | 20, 25 | 25 still means "no real trend" but allows far more trades |
| `rsi_level` | 35, 40, off | RSI on top of a Bollinger pierce is a double filter. Off may be enough |
| `bb_std` | 1.8, 2.0, 2.2 | Narrower bands = more touches |
| `need_confirm_candle` | on, off | Waiting for a reversal candle costs entries |
| `h1_max_dist_atr` | 1.5, 2.5 | Looser "is the bigger picture ranging" check |

Save as `grids/grid_range.json`:

```json
{
  "secondary": "range",
  "base_from": "results/wf_none_final.json",
  "base": {"secondary": {"adx_max": 25, "rsi_level": null, "need_confirm_candle": false}},
  "steps": [
    {"path": "secondary.adx_max", "values": [20, 25]},
    {"path": "secondary.rsi_level", "values": [null, 35, 40]},
    {"path": "secondary.bb_std", "values": [1.8, 2.0, 2.2]},
    {"path": "secondary.need_confirm_candle", "values": [false, true]},
    {"path": "secondary.h1_max_dist_atr", "values": [1.5, 2.5]}
  ]
}
```

### Run both

```
nohup sh -c 'for G in breakout_v2 range; do python3 pyTrade_optimise.py --grid grids/grid_$G.json --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --jobs 5; done' > wf_secondary.log 2>&1 &
```

### Read the result

For each secondary, run:

```
python3 pyTrade_golive_check.py --run breakout_v2
python3 pyTrade_golive_check.py --run range
```

(G4 and G5 show as missing until Phase 4. That's expected.) Look at **G2**, the secondary's own trades:

- **Under 60 test trades:** still too strict. If the loosest values were chosen in every window, the idea itself is too rare. Drop it.
- **Enough trades, avg R ≤ 0:** the idea has no edge on these pairs. Drop it.
- **Enough trades, avg R ≥ +0.05:** it carries on to Phase 3.

---

## Phase 3: Run all three together

Only if **both** secondaries passed Phase 2. They are designed for different markets (trend pullback, squeeze breakout, quiet range), so they should rarely compete.

Save as `grids/grid_chain.json`. No tuning: it reuses each strategy's final settings.

```json
{
  "secondary": "breakout_v2,range",
  "base_from": "results/wf_breakout_v2_final.json",
  "base": {},
  "steps": []
}
```

Copy the `secondary` settings for Range from `results/wf_range_final.json` into `"base"` by hand. Then run:

```
python3 pyTrade_optimise.py --grid grids/grid_chain.json --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --jobs 5
python3 pyTrade_golive_check.py --run breakout_v2,range
```

**Pass:** whole-bot total R beats both single-secondary setups, and drawdown is no more than 1.5× worse. If it doesn't, keep the better single secondary. The bot also needs a small change to support two secondaries (Phase 6 prompt).

---

## Phase 4: Robustness and go-live check (automated)

Two final tests on things the optimiser never saw:

- **Unseen pairs:** 3 pairs from your session table that were never used for tuning (example below; use your own). Add realistic spreads for them in `SPREAD_PIPS`. JPY crosses are wider.
- **Wider spreads:** the same settings with spreads 50% wider.

Save this as `run_golive.sh`, then `chmod +x run_golive.sh`. Change `RUN` to the winner from Phase 2/3.

```bash
#!/bin/bash
cd ~/pieTrade
RUN=breakout_v2            # or range, or breakout_v2,range, or none
TAG=${RUN//,/_}
UNSEEN=NZD_USD,EUR_JPY,GBP_JPY
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
FROM=$(date -d '12 months ago' +%F)
python3 pyTrade_backtest.py --pairs $UNSEEN --months 24 --from $FROM --secondary $RUN --live-validation --params results/wf_${TAG}_final.json --tag unseen --jobs 3 || exit 1
python3 pyTrade_backtest.py --pairs $P --months 24 --from $FROM --secondary $RUN --live-validation --params results/wf_${TAG}_final.json --spread-mult 1.5 --tag stress --jobs 5 || exit 1
python3 pyTrade_golive_check.py --run $RUN --baseline none --unseen results/${TAG}_unseen.csv --stress results/${TAG}_stress.csv | tee results/golive_${TAG}.txt
```

```
./run_golive.sh
```

### The gates explained

| Gate | Test | Why it matters |
|---|---|---|
| G1 | Whole bot avg R ≥ +0.05, PF ≥ 1.15, beats EMA-only | The bot must make money overall, and adding the secondary must help |
| G2 | Each secondary: ≥ 60 trades, avg R ≥ +0.05, PF ≥ 1.10 | Each strategy must pay its own way |
| G3 | Positive in ≥ 3 of 4 test windows | Not one lucky quarter |
| G4 | Still positive with spreads 50% wider | Real spreads widen at night and around news |
| G5 | Positive on pairs never used for tuning | Proves it isn't fitted to 5 specific pairs |
| G6 | Max drawdown ≤ 25R, losing streak ≤ 15 | At 1% risk, 25R is a 25% fall. That's the most most people can sit through |

`GO DEMO` → Phase 5. `NO GO` → see "If it fails" below.

---

## Phase 5: Demo forward test (4 weeks, automated reporting)

1. Copy the winning settings into the file the bot reads (Prompt 0.5):

```
cp results/wf_breakout_v2_final.json strategy_params.json
```

2. Set the secondary strategy on the Settings page, and start the bot on the **practice** account. Check the log shows `Loaded strategy_params.json`.

3. Automate the weekly report. Run `crontab -e` and add this line (Sunday 18:00):

```
0 18 * * 0 cd ~/pieTrade && /home/martyn/anaconda3/bin/python3 tools/breakout_report.py >> ~/pieTrade/demo_weekly.log 2>&1
```

4. **Weekly check** (5 minutes): `tail -n 60 demo_weekly.log`. Compare each strategy's live avg R with its walk-forward test avg R.

**Stop rule (check weekly):** if the demo drawdown passes **1.5×** the backtest's max drawdown, stop and investigate. Don't wait for the 4 weeks to end.

**Demo go-live checklist (after 4 weeks):**

- [ ] At least 40 trades in total
- [ ] Whole-bot live avg R > 0
- [ ] Each strategy's live avg R is at least half its backtest avg R, **or** it has fewer than 15 trades (too early to judge, keep watching)
- [ ] No losing streak longer than the backtest's longest + 3
- [ ] No unexplained errors in the bot log

---

## Phase 6: Live, small risk

1. Use the same `strategy_params.json`. Set risk per trade to **0.25%** (a quarter of normal).
2. Keep the weekly cron report and the stop rule.
3. After 4 weeks with the same checklist passing, move to 0.5%, then after another 4 weeks to your normal risk.

If Phase 3 chose **both** secondaries, wire the chain into the bot first:

```
In pyTrade_bot.py, settings.json and the settings panel only: "secondary_strategy" becomes an ordered list (e.g. ["breakout_v2","range"]); the loop tries primary then each secondary in order, stopping at the first signal; _strategy_engine finds any engine by name. Reply with a short summary.
```

Also update the AI agent's `SYSTEM` text (Step 7 prompt from the planning chat), so it knows all the strategies in use.

---

## If it fails

| Result | Meaning | Next move |
|---|---|---|
| Phase 1 fails | EMA pullback on M15 has no edge here | Test the same strategy on H1 candles (spread costs about 1/3 as much per R). Send me `wf_none.csv` |
| A secondary never reaches 60 trades | The idea is too rare on M15 | Drop it, or try it on a lower timeframe only if spreads allow |
| G4 fails (spread) | The edge is thinner than the spread | Larger stops/targets, or a higher timeframe |
| G5 fails (unseen pairs) | Settings fitted to the 5 tuning pairs | Re-run the optimiser on all 8 pairs; check G3 again |
| Demo much worse than backtest | Usually real spreads, news, or the AI agent's pair choice | Compare by pair and by hour first; check the news filter is on |

**Running only the EMA strategy, or not trading at all, is a valid result.** Fewer trades that make money always beat more trades that lose it.

---

## Quick reference

| Task | Command |
|---|---|
| Funnel (why a strategy doesn't trade) | `python3 pyTrade_backtest.py --pairs ... --months 24 --oos-months 4 --secondary range --funnel --jobs 5` |
| Tune the primary | `python3 pyTrade_optimise.py --grid grids/grid_primary.json --pairs ... --months 24 --jobs 5` |
| Tune a secondary | `python3 pyTrade_optimise.py --grid grids/grid_range.json --pairs ... --months 24 --jobs 5` |
| Go-live check | `./run_golive.sh` |
| Watch a long run | `tail -n 20 wf_primary.log` |
| Demo weekly report | `tail -n 60 demo_weekly.log` |

| File | What it does |
|---|---|
| `pyTrade_optimise.py` | Walk-forward tuning; picks settings automatically |
| `pyTrade_golive_check.py` | Prints PASS/FAIL for the six gates |
| `grids/*.json` | Which settings to try, and in what order |
| `results/wf_*_final.json` | The chosen settings, ready to copy into `strategy_params.json` |
| `strategy_params.json` | The settings the live bot uses (same format as the backtester) |
| `run_golive.sh` | Unseen-pair and spread tests, then the go-live check |