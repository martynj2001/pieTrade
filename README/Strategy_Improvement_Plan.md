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

## Phase 0 results (13 Nov 2026) - 24 months, 5 pairs, default settings

| Run | Strategy | Trades | Win % | Avg R | Total R | Avg win / avg loss |
|---|---|---|---|---|---|---|
| none | EMA | 2,535 | 47.5 | **-0.09** | -236 | +0.91 / -1.00 |
| breakout_v2 | Breakout_V2 | 62 | 25.8 | -0.27 | -17 | +1.20 / -0.78 |
| range | Range_Reversion | 20 | 30.0 | -0.37 | -7 | +0.38 / -0.69 |

What this tells us:

1. **The EMA entries are a coin flip, and the spread is the loss.** With a 1R stop and a 1R target, a random entry wins about 50%. EMA wins 47.5%. After spread, each win pays only +0.91R, so the strategy needs about 52% just to break even. It was negative in **8 of 9 quarters** and on **all 5 pairs**, so this isn't bad luck. Two levers can help:
   - **Bigger stops and targets on M15.** Spread is a fixed number of pips, so it becomes a smaller share of each trade.
   - **The 1-hour timeframe (H1).** The typical candle range (ATR) is roughly 2-3× bigger, so the spread costs a much smaller share of each trade.
   The Phase 1 grid now tests both (Phase 1 and Phase 1b).
2. **Both secondaries still barely fire at their default settings:** Breakout_V2 about 0.6 trades a week, Range about 0.2 a week. That was expected, because Prompt 0.2 kept the old behaviour as the default. The **loose-settings frequency check** (new Phase 0 step 3) shows whether the loosened rules fire often enough before anything runs overnight.
3. **Range_Reversion's target is too small for its stop.** Its average win is +0.38R against an average loss of -0.69R, because the middle Bollinger band is often close to the entry. Prompt 0.6 adds a choice of target (middle or opposite band) and stop buffer, and the Range grid tests them.
4. **The funnel tables (which filter blocks the most) are still needed.** They print to the terminal and aren't saved in the CSV or JSON files. Step 3 saves them with `tee`.

### Loose-settings check results (13 Nov 2026) - **both secondaries PASS the frequency gate**

| Strategy (loosest settings) | Trades (24 months) | Trades/week | Win % | Avg win / avg loss | Avg R |
|---|---|---|---|---|---|
| EMA (for comparison) | 2,535 | 24 | 47.5 | +0.91 / -1.00 | -0.09 |
| Breakout_V2 | 826 | 8 | 31.4 | +1.28 / -0.72 | **-0.09** |
| Range_Reversion | 2,176 | 22 | 43.1 | +0.81 / -0.79 | **-0.10** |

What this tells us:

1. **Both now trade often enough to tune** (the target was 150+). Phase 2 can go ahead for both.
2. **Three completely different strategies all lose about the same amount: -0.09 to -0.10R per trade.** That is the signature of entries with no edge, where the loss is just the trading cost (spread). Each trade starts about 0.1R down, so a strategy needs a real edge bigger than that just to break even. This makes Phase 1b (H1 timeframe) and the new **zero-spread check** (step 4) the most important tests in the plan.
3. **Breakout_V2's quick exits cost more than they save.** 334 trades (40%) were closed early by `manage()` at an average of -0.47R. Those exits halve each loss, but they also cut off trades that might have reached the +1.36R target. The grid now tests `manage()` on and off.
4. **The H1 trend check blocked 642 Breakout_V2 signals,** almost as many as it allowed (826). A breakout from a squeeze often starts a *new* trend, so the old H1 trend can disagree with it. The grid now tests the check on and off.
5. **Range_Reversion's time stop (8 candles) is closing trades too early.** Its 919 time-stop exits averaged +0.08R, meaning many were heading the right way when closed. The grid now tests 8 and 16 candles.
### Zero-spread check results (13 Nov 2026) - **the M15 entries have no edge**

| Strategy | Trades | Win % | Avg R, no spread | Likely true range (95%) | Positive quarters |
|---|---|---|---|---|---|
| EMA | 2,551 | 49.9 | **+0.00** | -0.04 to +0.04 | 4 of 9 |
| Breakout_V2 (loose) | 830 | 32.8 | **+0.03** | -0.05 to +0.10 | 3 of 9 |
| Range_Reversion (loose) | 2,164 | 47.5 | **+0.01** | -0.04 to +0.05 | 3 of 9 |

With no trading cost at all, all three break even. EMA wins 49.9% with a 1:1 target, exactly what random entries would do. None is positive in more than half the quarters, and the pairs that do well differ between strategies. **Decision:** tuning settings on M15 would mostly fit noise, so the M15 overnight runs (Phase 1 and Phase 2 on M15) are **paused**. The next test is the **H1 quick check** (Phase 0 step 5) before any further tuning.

### H1 quick-check results (13 Nov 2026) - **no edge on H1 either**

| Strategy (H1) | Trades | Avg R, no spread | Likely true range (95%) | Avg R, normal spread | Positive quarters (no spread) |
|---|---|---|---|---|---|
| EMA | 747 | +0.02 | -0.06 to +0.09 | -0.03 | 6 of 9 |
| Breakout_V2 (loose) | 201 | -0.02 | -0.18 to +0.14 | -0.09 | 4 of 9 |
| Range_Reversion (loose) | 757 | -0.02 | -0.11 to +0.06 | -0.10 | 5 of 9 |

As expected, H1 halves the spread cost (about 0.05R per trade instead of 0.09R). But the entries are still about break-even before costs. EMA is the least bad, but +0.02 is well inside the noise and below the +0.05 bar.

**Phase 0 conclusion.** The EMA pullback, squeeze breakout and Bollinger range entries have no measurable edge on M15 or H1 for these pairs. Changing their settings can't create an edge that isn't there, so **Phases 1-4 are on hold for these strategies.** The next step is Phase 0B below: screen new entry ideas, starting with higher timeframes, using the same tools.

6. **The funnel table didn't work as intended.** Most strategies don't log *why* they reject a candle (Range only logs "No signal"), so the table mostly listed EMA signals that were skipped because a trade was already open. Now that both strategies trade often enough, the funnel isn't needed. Ignore it.

---

## The plan at a glance

| Phase | What | How long | Automated? | Gate to pass |
|---|---|---|---|---|
| 0 | Upgrade the test tools + funnel check | 1 evening | Copilot prompts | Tools run; blockers found |
| 1 | Fix the **primary** (EMA) on M15, then 1b on H1 | 2 overnight runs | Yes | Primary out-of-sample avg R > 0 on the better timeframe |
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

### Prompt 0.6 - H1 timeframe and Range target options (added 13 Nov)

```
Make ONLY these changes; reply with a short summary.
1. pyTrade_backtest.py: add --granularity M15|H1 (default M15). For H1, signals and exits run on H1 candles and the guards' H1 trend input receives H4 candles (download and cache H4 the same way).
2. RangeReversionEngine: kwargs tp_target "mid"|"band" (band = opposite Bollinger band, default "mid") and sl_atr (ATR buffer beyond the signal-candle extreme, default 0.5).
3. pyTrade_optimise.py: optional grid key "args" (dict) passed to every backtest call as --key value.
```

### Prompt 0.7 - switches for the new grid steps (added 13 Nov)

```
Make ONLY these changes; each new kwarg defaults to current behaviour. Reply with a short summary.
1. BreakoutV2Engine: manage_exits (bool, False = never call manage()); require_h1_trend (bool, False = pyTrade_backtest.py and pyTrade_bot.py skip the H1 trend guard for this engine).
2. RangeReversionEngine: max_bars (time-stop candles in manage(), default 8).
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

3. **Loose-settings frequency check (added 13 Nov).** This runs each secondary with its loosest settings and saves the funnel table to a text file (`tee`):

```
cd ~/pieTrade
mkdir -p grids
cat > grids/loose_v2.json <<'EOF'
{"secondary": {"adx_mode": "rising", "squeeze_pct": 0.7, "hours": [7,8,9,10,11,12,13,14,15], "max_ema_dist_atr": 3.0}}
EOF
cat > grids/loose_range.json <<'EOF'
{"secondary": {"adx_max": 25, "rsi_level": null, "bb_std": 1.8, "need_confirm_candle": false, "h1_max_dist_atr": 2.5, "tp_target": "band"}}
EOF
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --secondary breakout_v2 --params grids/loose_v2.json --funnel --tag loose --jobs 5 | tee funnel_v2_loose.txt
python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --secondary range --params grids/loose_range.json --funnel --tag loose --jobs 5 | tee funnel_range_loose.txt
```

**Pass:** each secondary makes at least **150 trades over the 24 months** (about 1.5 a week across the 5 pairs). That gives the optimiser enough trades in each 12-month train period, and about 75 in the combined 12 months of test trades that gate G2 judges.

**Fail:** send me `funnel_v2_loose.txt` / `funnel_range_loose.txt`. The top rejection reason shows which rule to loosen or remove next. Don't start the Phase 2 overnight run for a secondary that fails this check.

Avg R doesn't matter at this stage. The check is only "does it trade often enough to be tunable?".

4. **Zero-spread check (added 13 Nov, about 15 minutes).** This runs the same three setups with **no trading cost** at all. It answers one question: *do the entries have any edge before costs?*

```
cd ~/pieTrade
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --secondary none --spread-mult 0 --tag zero --jobs 5
python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --secondary breakout_v2 --params grids/loose_v2.json --spread-mult 0 --tag zero --jobs 5
python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --secondary range --params grids/loose_range.json --spread-mult 0 --tag zero --jobs 5
cat results/*_zero_summary.json
```

How to read each strategy's avg R with zero spread:

| Avg R at zero spread | Meaning | What it means for the plan |
|---|---|---|
| **+0.05 or more** | The entries have a small real edge. Spread is what kills it | Promising. Wider stops (Phase 1 grid) and H1 (Phase 1b) can recover it |
| **About 0 (-0.03 to +0.03)** | The entries are no better than a coin flip | Tuning will mostly fit noise. H1 is the main hope; otherwise the entry idea needs replacing |
| **Below -0.03** | The entries are worse than random | Something is wrong with the strategy logic. Send me the file before tuning |

This is a diagnostic only. **Never use zero-spread results for any go-live decision**, because real trades always pay the spread.

5. **H1 quick check (added 13 Nov, needs Prompt 0.6).** This runs the same three setups on 1-hour candles, with and without spread. It takes about 30 minutes, with no tuning.

```
cd ~/pieTrade
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
for M in 1 0; do
  python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --granularity H1 --secondary none --spread-mult $M --tag h1_s$M --jobs 5
  python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --granularity H1 --secondary breakout_v2 --params grids/loose_v2.json --spread-mult $M --tag h1_s$M --jobs 5
  python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --granularity H1 --secondary range --params grids/loose_range.json --spread-mult $M --tag h1_s$M --jobs 5
done
ls results/*h1_s*_summary.json
```

(`h1_s1` = normal spread, `h1_s0` = zero spread.) Note: Breakout_V2's `hours` setting still applies on H1, so it can only trade 07:00-15:00 UTC.

| H1 result for a strategy | Next step |
|---|---|
| Zero-spread avg R **≥ +0.05** and normal-spread avg R above 0 | Promising. Run that strategy's walk-forward grid on H1 (`"args": {"granularity": "H1"}`) |
| Zero-spread avg R ≥ +0.05, but normal-spread ≤ 0 | A small edge that costs eat. Try the walk-forward grid with wider stops (`atr_multiplier` 2.5-3.0) |
| Zero-spread avg R **about 0** | No edge on H1 either. Settings won't fix it; the entry idea needs replacing |

---

## Phase 0B: Screen new entry ideas (added 13 Nov)

**The rule from now on:** no strategy gets tuned until it passes a **screening test** on default settings, 24+ months of data, with no tuning:

| Screening check | Pass mark |
|---|---|
| Avg R with **zero spread** | **≥ +0.05** |
| Avg R with **normal spread** | **> 0** |
| Positive quarters (normal spread) | At least 60% |
| Trades | At least 100 |

Only strategies that pass go into the walk-forward tuning (Phases 1-4). Tuning a strategy that fails screening only fits the past.

### Option A (try first): bolt-on strategies for the current M15 bot

These keep the bot as it is: 15-minute candles, session-based, each strategy in its own class. What makes them different from the three that failed is **where the edge is supposed to come from**. The failed strategies all looked for indicator shapes on a 15-minute chart. These rely on something structural about the market:

| # | Strategy | The structural reason it might work | New code |
|---|---|---|---|
| A1 | **London Opening Range Breakout** | Price drifts in a narrow range during the quiet Asian hours. At the London open, trading volume jumps and price often breaks out of that range and keeps going | One new class |
| A2 | **Range_Reversion on "linked-economy" pairs** | AUD/NZD, EUR/CHF and EUR/GBP pair two closely tied economies, so they spend far more time moving sideways than the majors do | None (pairs only) |
| A3 | **Daily-trend filter** | Trends lasting weeks to months are the best-documented pattern in currencies. This only allows M15 trades in the direction of the daily trend | One small guard option |

None of these is proven. Each must pass the same screening test before any tuning.

**Prompt A1 - Opening Range strategy (also adds `--primary`, so a strategy can be screened on its own):**

```
Create pyTrade_ORB_Strategy.py: class OpeningRangeEngine, same interface as BreakoutEngine, strategy_name "Opening_Range". Kwargs: range_start=0, range_end=7, entry_end=10, exit_hour=16 (UTC hours), buffer_atr=0.1, min_range_atr=2.0, max_range_atr=8.0, sl_mode="mid" ("mid"|"opposite"), rr_ratio=1.5, atr_len=14, min_sl_dist.
- add_indicators: ATR_14; OR_High/OR_Low = that UTC day's high/low over candles with range_start <= hour < range_end (NaN before range_end).
- BUY when hour in [range_end, entry_end), close > OR_High + buffer_atr*ATR, range width within min/max_range_atr*ATR, and no earlier candle today since range_end closed outside the range. SELL mirrors.
- SL = range midpoint or opposite side (sl_mode), respecting min_sl_dist; TP = rr_ratio * risk.
- manage(trade, df) -> "close" when the latest candle's hour >= exit_hour or its date is after the entry date.
Also: pyTrade_backtest.py gets --primary ema|breakout|breakout_v2|range|orb (default ema) and --secondary accepts orb; pyTrade_backtest.py and pyTrade_bot.py skip the ADX and H1-trend guards for Opening_Range; pyTrade_validation.py resolve_strategy_type maps "opening_range" to the time check only. Reply with a short summary.
```

How it trades, in plain English: it marks the high and low of 00:00-07:00 UTC. Between 07:00 and 10:00 it buys the first 15-minute candle that closes above the range (or sells below it). The stop goes at the middle of the range, the target is 1.5× the risk, and anything still open at 16:00 UTC is closed. It takes at most one trade per pair per day.

**Prompt A3 - daily-trend option for the guards:**

```
In pyTrade_trade_guards.py, pyTrade_backtest.py and pyTrade_bot.py only: TradeGuards kwarg trend_tf "H1"|"D" (default "H1"). For "D" the H1-trend check uses closed daily candles instead (download/cache D the same way): BUY only if D close > D EMA50 and > the D close 60 days earlier; SELL mirrors. Reply with a short summary.
```

**Screening runs (about 30 minutes; M15, 24 months, each with normal and zero spread):**

Add spreads for the cross pairs to `SPREAD_PIPS` first (typical OANDA practice values: AUD_NZD 2.5, EUR_CHF 1.8, EUR_GBP 1.5).

```
cd ~/pieTrade
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
X=AUD_NZD,EUR_CHF,EUR_GBP
echo '{"guards": {"trend_tf": "D"}}' > grids/daily_trend.json
for M in 1 0; do
  # A1: Opening Range on its own
  python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --primary orb --secondary none --spread-mult $M --tag a1_s$M --jobs 5
  # A2: Range_Reversion on its own, linked-economy pairs
  python3 pyTrade_backtest.py --pairs $X --months 24 --oos-months 4 --primary range --secondary none --params grids/loose_range.json --spread-mult $M --tag a2_s$M --jobs 3
  # A3: EMA with the daily-trend filter
  python3 pyTrade_backtest.py --pairs $P --months 24 --oos-months 4 --primary ema --secondary none --params grids/daily_trend.json --spread-mult $M --tag a3_s$M --jobs 5
done
ls results/*_a?_s?_summary.json
```

Send the 6 summary JSON files plus the CSVs. Results files are named after the secondary (`none_a1_s1...`), so the tag tells you which test is which: `a1` = Opening Range, `a2` = Range on crosses, `a3` = EMA with daily trend; `s1` = normal spread, `s0` = zero spread.

Notes:
- **A2 and EUR/GBP:** this is the pair whose stop was "clamped" in the live bot. If its backtest stops look oversized (very few trades reach target), judge A2 on AUD/NZD and EUR/CHF alone.
- **A3 can also be combined with A1** if both look promising: `--primary orb --params grids/daily_trend.json` will only work once the Opening Range strategy is told to use the daily guard. Ask for that prompt if needed.
- **Wiring a winner into the bot** is one line per strategy: the bot already loads engines by name, and `strategy_params.json` carries the settings (Prompt 0.5).

### Option B: the same ideas on H4 and daily candles

The best-documented pattern in currency markets is **trend following on longer timeframes** (days to weeks, not minutes). The classic version is a 20-day Donchian channel breakout, which is exactly your original `BreakoutEngine`. On H4 and daily candles:

- Price moves are larger compared with the spread, so costs become small (roughly 0.01-0.02R per trade).
- Trends are smoother and less noisy than on 15-minute charts.
- **The trade-off: far fewer trades** (a few a week across many pairs), held for days. So screening uses **9 pairs** and **5 years** of data.

Note: trades held overnight pay or receive **financing** (swap) on OANDA. The backtester ignores this. It is small for most pairs over a few days, but check it before any demo.

**Prompt 0.8:**

```
In pyTrade_backtest.py only: --granularity also accepts H4 and D (trend input: D candles for H4, W candles for D; download and cache the same way; for H4/D ignore hours rules and the session-boundary validation check). Allow --months up to 72. Reply with a short summary.
```

Add spreads for the new pairs to `SPREAD_PIPS` in config.py if they aren't there (typical OANDA practice values: NZD_USD 1.6, USD_CHF 1.6, EUR_JPY 1.8, GBP_JPY 2.8).

**Screening run (about 1 hour):**

```
cd ~/pieTrade
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,NZD_USD,USD_CHF,EUR_JPY,GBP_JPY
for G in H4 D; do
  for M in 1 0; do
    python3 pyTrade_backtest.py --pairs $P --months 60 --oos-months 12 --granularity $G --secondary none --spread-mult $M --tag ${G}_s$M --jobs 5
    python3 pyTrade_backtest.py --pairs $P --months 60 --oos-months 12 --granularity $G --secondary breakout --spread-mult $M --tag ${G}_s$M --jobs 5
  done
done
ls results/*_H4_s*_summary.json results/*_D_s*_summary.json
```

This screens 4 setups: EMA on H4 and D, and EMA + classic Donchian breakout on H4 and D. In the `breakout` runs, look at the **Breakout** strategy row on its own. Send the 8 summary JSON files plus the CSVs.

**If something passes:** it becomes the new primary (or secondary). Run Phases 1-4 for it, with `"args": {"granularity": "H4"}` (or `"D"`) in the grids and `--months 60`.

**If nothing passes:** the honest conclusion is that simple indicator strategies don't beat costs on these markets. The bot stays on the demo account as an engineering project, and any new idea is screened the same way before it's built in.

---

## Phase 1: Fix the primary (overnight)

The primary decides whether the bot can make money at all, so it comes first.

### What to change, and why

| Setting | Where | Current | Values to test | Why |
|---|---|---|---|---|
| `rr_ratio` (take-profit size) | `primary` | 1.0 | 1.0, 1.5, 2.0 | After spread, a 1R target only pays about +0.9R, so the strategy needs to win 53% of the time just to break even. A bigger target cuts the spread's share |
| `atr_multiplier` (stop size) | `primary` | 1.5 | 1.5, 2.0, 2.5, 3.0 | A wider stop gets "noise-stopped" less, and spread costs a smaller fraction of R. Phase 0 showed spread is the main loss |
| `trend_filter_k` (minimum trend strength) | `primary` | 0.5 | 0.5, 1.0 | Live data hinted that trades with trend strength 1-2 did best |
| `pullback_tolerance_k` | `primary` | 0.25 | 0.15, 0.25, 0.5 | How close price must come to EMA20. Tighter = cleaner pullbacks, fewer trades |
| `wick_factor` | `primary` | 1.5 | 1.0, 1.5, 2.0 | How strong the rejection candle must be. Higher = stronger rejection only |
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
    {"path": "primary.atr_multiplier", "values": [1.5, 2.0, 2.5, 3.0]},
    {"path": "primary.trend_filter_k", "values": [0.5, 1.0]},
    {"path": "primary.pullback_tolerance_k", "values": [0.15, 0.25, 0.5]},
    {"path": "primary.wick_factor", "values": [1.0, 1.5, 2.0]},
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

### Phase 1b: the same test on the 1-hour timeframe (run the following night)

Phase 0 showed the spread is most of the EMA strategy's loss. On H1 candles the stop is roughly 2-3× wider in pips, so the same spread costs a much smaller share of each trade. Testing H1 straight away, instead of only if M15 fails, saves a week.

Save as `grids/grid_primary_h1.json`. It is the same as the M15 grid, plus `"args"`. Allowed hours are dropped, because H1 trades last many hours anyway.

```json
{
  "secondary": "none",
  "args": {"granularity": "H1"},
  "base": {},
  "steps": [
    {"path": "primary.rr_ratio", "values": [1.0, 1.5, 2.0]},
    {"path": "primary.atr_multiplier", "values": [1.5, 2.0, 2.5]},
    {"path": "primary.trend_filter_k", "values": [0.5, 1.0]},
    {"path": "primary.pullback_tolerance_k", "values": [0.15, 0.25, 0.5]},
    {"path": "primary.wick_factor", "values": [1.0, 1.5, 2.0]},
    {"path": "primary.max_trend_k", "values": [null, 2.0, 3.0]},
    {"path": "guards.adx_threshold", "values": [20, 24, 28]},
    {"path": "validation.enable_session_check", "values": [true, false]},
    {"path": "validation.enable_time_check", "values": [true, false]}
  ]
}
```

```
mv results/wf_none.csv results/wf_none_m15.csv; mv results/wf_none_trades.csv results/wf_none_m15_trades.csv; cp results/wf_none_final.json results/wf_none_m15_final.json
nohup python3 pyTrade_optimise.py --grid grids/grid_primary_h1.json --pairs EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD --months 24 --jobs 5 > wf_primary_h1.log 2>&1 &
```

The first command keeps the M15 results so the H1 run doesn't overwrite them.

**Pick the timeframe:** compare the 12 months of test trades from M15 (`wf_none_m15_trades.csv`) and H1 (`wf_none_trades.csv`). Choose the one with the higher **total R**, as long as it has at least 3 of 4 positive windows. Leave the winner's files named `wf_none*.*`, because Phase 2 reads `results/wf_none_final.json`. If H1 wins, Phase 2 must also run on H1: add `"args": {"granularity": "H1"}` to the secondary grids.

### Read the result

Open `results/wf_none.csv` and look at the **test** columns for each window.

- **Pass:** the 12 months of test trades have avg R > 0, and at least 3 of 4 windows are positive. Go to Phase 2.
- **Look at the chosen settings.** If all four windows pick the same values (e.g. `rr_ratio` 1.5 every time), that is a strong sign the setting is real. If they jump around, the setting doesn't matter much or the edge is weak.
- **Fail (avg R ≤ 0 on both M15 and H1, even with the best settings):** stop here. The EMA pullback idea doesn't have an edge on these pairs. Send me both `wf_none` files and we'll rethink the primary before going further.

---

## Phase 2: Make the secondaries fire, then tune (overnight)

Each secondary uses the primary settings picked in Phase 1 (`base_from`), so it is tested alongside the improved primary.

**First target: frequency.** A secondary must pass the Phase 0 loose-settings check: at least **150 trades over 24 months** (about 1.5 a week across the 5 pairs). Only start the overnight run for secondaries that passed it. The grids start with the loosest sensible values so the optimiser can tighten from there.

### Breakout_V2 - what to change, and why

| Setting | Values | Why |
|---|---|---|
| `adx_mode` | threshold, rising | **The key fix.** "Rising ADX" means "a trend is starting", which is compatible with a squeeze. "ADX > 24" isn't |
| `squeeze_pct` | 0.3, 0.5, 0.7 | Lets "fairly quiet" markets count, not only "very quiet" ones |
| `hours` | London/NY opens only; 07-15 UTC | Wider window = more trades |
| `max_ema_dist_atr` | 2.0, 3.0 | Live data: 35 of 37 breakouts were entered more than 2 ATR from EMA50, and lost |
| `rr_ratio` | 1.5, 2.0 | Target size |
| `enable_breakout_checks` (validation) | on, off | The "Donchian re-entry" exit made the old breakout worse |
| `manage_exits` | on, off | Loose check: 40% of trades were closed early at -0.47R on average. Does letting them run to stop or target do better? |
| `require_h1_trend` | on, off | Loose check: the H1 trend guard blocked 642 signals. A new breakout may start a new trend that the H1 hasn't caught up with yet |

Save as `grids/grid_breakout_v2.json` (the base is now the loose settings that passed the frequency check):

```json
{
  "secondary": "breakout_v2",
  "base_from": "results/wf_none_final.json",
  "base": {"secondary": {"adx_mode": "rising", "squeeze_pct": 0.7, "hours": [7,8,9,10,11,12,13,14,15], "max_ema_dist_atr": 3.0}},
  "steps": [
    {"path": "secondary.manage_exits", "values": [true, false]},
    {"path": "secondary.require_h1_trend", "values": [true, false]},
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
| `tp_target` | mid, band | Phase 0: avg win +0.38R against avg loss -0.69R. The middle band is often too close. The opposite band roughly doubles the target |
| `sl_atr` | 0.5, 1.0 | A bigger buffer beyond the turning candle means fewer stop-outs from small wicks |
| `max_bars` | 8, 16 | Loose check: 919 time-stop exits averaged +0.08R. Many trades were still heading towards target when closed |

Save as `grids/grid_range.json` (the base is now the loose settings that passed the frequency check):

```json
{
  "secondary": "range",
  "base_from": "results/wf_none_final.json",
  "base": {"secondary": {"adx_max": 25, "rsi_level": null, "bb_std": 1.8, "need_confirm_candle": false, "h1_max_dist_atr": 2.5, "tp_target": "band"}},
  "steps": [
    {"path": "secondary.tp_target", "values": ["band", "mid"]},
    {"path": "secondary.max_bars", "values": [8, 16]},
    {"path": "secondary.sl_atr", "values": [0.5, 1.0]},
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
| Tune the primary on H1 | `python3 pyTrade_optimise.py --grid grids/grid_primary_h1.json --pairs ... --months 24 --jobs 5` |
| Loose frequency check | Phase 0 step 3 (saves `funnel_*_loose.txt`) |
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