#!/bin/bash
cd ~/pieTrade
P=EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD
for S in none breakout breakout_v2 range; do
  echo "=== $S ==="
  python3 pyTrade_backtest.py --pairs $P --months 12 --oos-months 4 --secondary $S || exit 1
  python3 pyTrade_backtest.py --pairs $P --months 12 --oos-months 4 --secondary $S --live-validation --tag val || exit 1
done
ls results/
