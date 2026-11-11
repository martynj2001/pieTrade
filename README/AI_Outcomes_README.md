# pyTrade: AI Agent Outcomes - Setup and Run Guide

Keep this file in `~/pieTrade`. Open it whenever you want to set up, run or check the outcomes scripts.

## What this is (in plain English)

Every hour the AI agent logs which pair and market it would trade (the **decision**).
Nothing in that log says whether the choice was good. The **outcomes script** does that:

1. About an hour after each decision it downloads the real 15-minute candles for that hour from OANDA, for every pair the AI could have chosen.
2. It records how that hour behaved:
   - **range** - how far price travelled (in pips, and relative to a normal candle)
   - **efficiency** - net move divided by total range. 1 = a clean one-way trend, 0 = went nowhere. Your strategies want high values.
3. The **report** then compares the AI's pick with your fixed pair and the simple "highest ADX" rule.

```
bot (AI agent ON)  ->  agent_decisions table   (hourly, written by the bot)
outcomes script    ->  agent_outcomes table    (hourly at :10, run by cron)
report / web page  ->  compares them           (run when you want to look)
```

> The results measure how *trendy* each choice turned out to be. They are **not profit**.
> Real profit evidence only comes later, from live trading.

Without the outcomes script the report shows "no data".

---

## Part 1: One-time setup

Open a terminal (`Ctrl + Alt + T`). The `(base)` at the start of the prompt means Anaconda is active - that is the Python the bot uses.

### 1.1 Go to the bot folder and check the files exist

```
cd ~/pieTrade
ls pyTrade_agent_outcomes.py pyTrade_agent_report.py pyTrade_trades_db.py config.py
```

All four names should print with no "No such file" error.
If `pyTrade_agent_outcomes.py` is missing, the AI-selector prompt was not fully built. Do not continue until it exists.

### 1.2 Find your Python and check the libraries

```
which python3
python3 -c "import oandapyV20, pandas; print('libraries OK')"
```

- Write down the path `which python3` prints (expected: `/home/martyn/anaconda3/bin/python3`). You need it in 1.6.
- If you see `ModuleNotFoundError`, install the missing library, e.g. `pip install oandapyV20`, then repeat.

### 1.3 Check config.py has your OANDA settings

The outcomes script only needs OANDA (it never calls the AI). Check without printing the keys:

```
python3 -c "import config; print('OANDA key set:', bool(config.OANDA_API_KEY.strip()), '| environment:', config.OANDA_ENVIRON)"
```

You want `OANDA key set: True | environment: practice`.
**Never paste config.py (or the key) into chats, Copilot or Git.**

### 1.4 Check the database has the AI tables

```
sqlite3 ~/pieTrade/Trades_db/pytrade.db ".tables"
```

The list should include `agent_decisions` and `agent_outcomes`.

- If `sqlite3` is not found: `sudo apt install sqlite3`
- If the two tables are missing: start the bot once (Start button, then Stop). It creates them. Or run:
  `python3 -c "import pyTrade_trades_db as t; t.create_database()"`

### 1.5 Do a manual test run

```
cd ~/pieTrade
python3 pyTrade_agent_outcomes.py
```

It prints how many decisions it processed. **"0 decisions processed" is normal** when nothing is waiting yet (the bot has not logged any decisions, or the latest is less than about 65 minutes old).

For a full test that needs no real data and never touches your real database, use the self-test:

```
python3 pyTrade_selftest.py --no-api --outcomes
```

Look at the **section 10** lines at the bottom. `PASS` means the outcomes script and the report both work.

### 1.6 Install the hourly schedule (cron)

Cron is Linux's built-in scheduler (Mint has it already). It runs the script at 10 minutes past every hour. If the computer was off or asleep, the next run catches up on any hours it missed.

Cron does **not** load Anaconda, so the full Python path is required. Plain `python3` would use the system Python, which lacks your libraries, and fail silently.

1. Type: `crontab -e` (if asked for an editor, choose `nano`)
2. Go to the bottom and paste this line (use your own path from step 1.2 if different):

   ```
   10 * * * * cd ~/pieTrade && /home/martyn/anaconda3/bin/python3 pyTrade_agent_outcomes.py >> ~/pieTrade/outcomes_cron.log 2>&1
   ```
3. Save: `Ctrl+O`, `Enter`, then `Ctrl+X`
4. Check it was saved: `crontab -l`

The end of the line (`>> outcomes_cron.log 2>&1`) saves everything the script prints, including errors, to `~/pieTrade/outcomes_cron.log`.

To switch it off later: `crontab -e` and put a `#` at the start of the line.

### 1.7 Set up checklist

- [ ] Files exist (1.1)
- [ ] Libraries import (1.2)
- [ ] OANDA key is set (1.3)
- [ ] `agent_decisions` and `agent_outcomes` tables exist (1.4)
- [ ] Manual run works (1.5)
- [ ] Cron line saved (1.6)
- [ ] In the bot: Settings page, **AI Agent** switch ON, and `AGENT_SHADOW = True` in config.py (this logs decisions without trading on them)

---

## Part 2: Running it manually

Use this whenever you want fresh numbers right now instead of waiting for the next :10.

```
cd ~/pieTrade
python3 pyTrade_agent_outcomes.py
```

- It only processes decisions that are at least about 65 minutes old and have not been processed yet.
- Running it twice is safe: finished decisions are skipped.
- It works at weekends and with the bot stopped, because it only needs past candles.

### Re-calculating a decision's outcomes (rarely needed)

If outcomes look wrong for a decision, delete its rows and run the script again. **Back up first:**

```
cp ~/pieTrade/Trades_db/pytrade.db ~/pieTrade/Trades_db/pytrade.backup.db
sqlite3 ~/pieTrade/Trades_db/pytrade.db "DELETE FROM agent_outcomes WHERE decision_id = 123;"
python3 pyTrade_agent_outcomes.py
```

(Replace `123` with the decision `id`. Look ids up with `SELECT id, target_hour, status FROM agent_decisions ORDER BY id DESC LIMIT 10;`.)

---

## Part 3: Checking it is working

### Is cron running the script?

```
tail -n 20 ~/pieTrade/outcomes_cron.log
```

You should see a line every hour. Most say 0 decisions processed unless the bot ran in the previous hour.

### Are the numbers growing?

```
sqlite3 ~/pieTrade/Trades_db/pytrade.db "SELECT COUNT(*) AS decisions_ok FROM agent_decisions WHERE status='ok'; SELECT COUNT(*) AS outcome_rows FROM agent_outcomes;"
```

After the bot has run for a while, `outcome_rows` should grow (several rows per decision, one per candidate pair). Rows appear about 70 minutes after each decision.

### Is the AI itself healthy?

```
sqlite3 ~/pieTrade/Trades_db/pytrade.db "SELECT status, COUNT(*) FROM agent_decisions GROUP BY status;"
```

You want almost everything `ok`. Many `error` or `invalid` rows mean a problem with the agent or its API key.

---

## Part 4: Seeing the results

### In the terminal

```
cd ~/pieTrade
python3 pyTrade_agent_report.py --mode shadow --days 14
```

`--mode` can be `shadow`, `live` or `all`. `--days` limits it to the last N days (leave it off for everything).

### On the web dashboard

Start the API and the website (two terminals, both from `~/pieTrade`):

```
uvicorn api.main:app --host 0.0.0.0 --port 8000
cd web && npx ng serve --host 0.0.0.0
```

Open `http://localhost:4200/agent` (the **AI Agent** page). Use the Mode and period filters at the top, then Refresh.
First time only: `pip install -r requirements-api.txt` and `cd web && npm install`.

### How to read it

- **Go-live checklist**: all checks must pass before you consider letting the AI choose real pairs (about 150 usable hours, 95% or more of decisions ok, the AI beating both the fixed pair and the "highest ADX" rule, and not just in one session).
- **Agent vs Fixed vs Baseline**: higher efficiency and range are better. About 50% on "beats fixed" is a coin flip.
- **Only hours where the AI differed from the fixed pair** is where any real advantage will show.
- Fewer than about 150 hours of data means the numbers are noise. Wait.

---

## Part 5: Routine

**Daily (2 minutes, while the bot runs):**
- `tail -n 20 ~/pieTrade/outcomes_cron.log`: no errors?
- Status counts (Part 3): still mostly `ok`?

**Weekly:**
- Run the report or open the `/agent` page.
- Back up the database: `cp ~/pieTrade/Trades_db/pytrade.db ~/pieTrade/Trades_db/pytrade.backup.db`

**After about 2 weeks of shadow running:** check the go-live checklist. If it does not clearly pass, keep your fixed market sessions.

---

## Troubleshooting

| What you see | Likely cause | Fix |
|---|---|---|
| `0 decisions processed` | Nothing is waiting | Normal. Check the bot ran with the AI switch ON, and decisions are over 65 minutes old |
| `ModuleNotFoundError` | Wrong Python (common in cron) | Use the full Anaconda path in the cron line (1.6), or `pip install` the missing library |
| `no such table: agent_decisions` | Bot has not created the tables yet | Start the bot once, or run the `create_database()` command in 1.4 |
| OANDA error or 401 / authorisation message | Wrong or expired key in config.py | Fix `OANDA_API_KEY` and `OANDA_ENVIRON` (practice or live) |
| Cron log is empty after more than 1 hour | Cron did not run | `crontab -l` to confirm the line; `systemctl status cron`; the computer may have been off |
| Outcomes rows stay at 0 but decisions exist | Script errors silently | Run it by hand (Part 2) and read the message |
| Report says "no data yet" | No decisions or no outcomes yet | Run the bot with the AI switch ON, then the outcomes script |
| Report numbers look odd after a code change | Old test rows in the database | Back up, then inspect `agent_decisions` before deleting anything |

If stuck, copy the exact error text (never the keys) and ask for help.

---

## Quick reference

| Task | Command |
|---|---|
| Go to the bot folder | `cd ~/pieTrade` |
| Run outcomes now | `python3 pyTrade_agent_outcomes.py` |
| Test everything safely | `python3 pyTrade_selftest.py --no-api --outcomes` |
| Terminal report | `python3 pyTrade_agent_report.py --mode shadow --days 14` |
| Check the cron log | `tail -n 20 ~/pieTrade/outcomes_cron.log` |
| Show the cron job | `crontab -l` |
| Edit the cron job | `crontab -e` |
| Decision status counts | `sqlite3 ~/pieTrade/Trades_db/pytrade.db "SELECT status, COUNT(*) FROM agent_decisions GROUP BY status;"` |
| Back up the database | `cp ~/pieTrade/Trades_db/pytrade.db ~/pieTrade/Trades_db/pytrade.backup.db` |

| File | What it does |
|---|---|
| `pyTrade_agent_outcomes.py` | Measures how each hour turned out (run hourly by cron) |
| `pyTrade_agent_report.py` | Prints the comparison report |
| `pyTrade_selftest.py` | Safe offline test of the whole agent pipeline |
| `Trades_db/pytrade.db` | The database (tables `agent_decisions`, `agent_outcomes`) |
| `outcomes_cron.log` | Everything the hourly cron run printed |