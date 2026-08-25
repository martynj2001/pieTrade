##########################################################
#      Impliment a 20:50 EMA Pull Back Strategy          #
##########################################################
# Description:                                           #
#                                                        #
# EMA pullback strategy using the 20/50 indicators.      #
# Simple EMA FOREX startegy:                             #
#                                                        #
# Step 1 - Define the Trend using the 50 EMA, Price is   #
# above 50 EMA then this is an uptrend, price is below   #
# the 50 EMA then this is a downtrend                    #
#                                                        #
# Only trade with the trend.                             #
#                                                        #
# Step 2 - Use the 20 EMA for pullback entries.          #
#                                                        #
# In an uptrend:                                         #
# price rises, price dips back towards the 20 EMA.       #
# This dip is the entry point.                           #
#                                                        #
# In a downtrend:                                        #
# Price falls, Price rises back towards the 20 EMA.      #
# This rise is the entry point.                          #
#                                                        #
# Step 3 - Entry Rules (simple)                          #
#                                                        #
# You entry a trade when:                                #
# 1. Price pulls back to 20 EMA.                         #
# 2. A 'rejection candle forms (long wick, strong close) #
# 3. You entry on the break of that candle's high        #
# (uptrend) or low (downtrend)                           #
#                                                        #
# Step 4 - Stop-loss placement (this portects if the     #
# trend fails)                                           #
#                                                        #
# Uptrend: stop goes below the swing low.                #
# Downtrend: stop goes above the swing high              #
#                                                        #
# Step 5 - Take profit options                           #
#                                                        #
# Choose one:                                            #
# 1. Fixed 2R (twice your risk)                          #
# 2. Exit when proce closes beyond the 20 EMA in the     #
# opposite direction.                                    #
#                                                        #
##########################################################

import pandas_ta_classic as ta

import config

def get_indicators(df, high_ind, low_ind):

    ema_High = "EMA_" + str(high_ind)
    ema_Low = "EMA_" + str(low_ind)

    #EMAs
    df[ema_Low] = ta.ema(df["close"], length=low_ind)
    df[ema_High] = ta.ema(df["close"], length=high_ind)

    # ATR Stop_Loss
    df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    return df

# Function: has_clear_trend()                                         #
# Description:                                                        #
# Check that there is enough distence between'close' price and 50 EMA #
# to avoid flat choppy market.                                        #
# Market is not trending strongly enough to justify a pullback trade  #
# k= a multiplyer taht defines how strict you want the trend filter   #
# to be:                                                              #
#  0.25 - very strict (trend must be very strong                      #
#  0.5 - balanced (default value)                                     #
#  1.0 - loose (trend filter barely matters)                          #

def has_clear_trend(row, k=0.5):

    distence = abs(row["close"] - row["EMA_50"])
    threshold = k * row["ATR_14"]
    return distence > threshold

# Functions: is_downtrend() & is_uptrend()                            #
# Description:                                                        #
# Detects current trend and returns True or False                     #

def is_downtrend(row):
    if row["close"] < row["EMA_50"]:
        return True
    else: 
        return False

def is_uptrend(row):
    if row["close"] > row["EMA_50"]:
        return True
    else: 
        return False

# Function: pullback_to_ema20                                            #
# Description:                                                           #
# Detects if the current candle touched or got near the 20 EMA. Returns  #
# True if it did indicating a Pullback has been detected.                #

def pullback_to_ema20(row):

    tolerance = 0.25 * row["ATR_14"]

    # Candle touches the 20 EMA
    touched = row["low"] <= row["EMA_20"] <= row["high"]

    # Candle closes very near the 20 EMA
    near = abs(row["close"] - row["EMA_20"]) <= tolerance

    return touched or near

# Function: rejection_candle()                                           #
# Description:                                                           #
# Functions to calulate if a rejection candle has formed showing         #
# a strong rejection of a price level.
#
# Wick_factor is the mulitplyer to compare wick size to body size        #
# this ensures you only detect candles with a strong rejection.          #

def rejection_candle_uptrend(row, wick_factor=1.5):

    body = abs(row["close"] - row["open"])
    lower_wick = row["close"] - row["low"]
    return (
        row["close"] > row["open"] and
        lower_wick >= wick_factor * body
    )

def rejection_candle_downtrend(row, wick_factor=1.5):

    body = abs(row["close"] - row["open"])
    upper_wick = row["high"] - row["close"]
    return (
        row["close"] < row["open"] and
        upper_wick >= wick_factor * body
    )

# Function: stop_loss()                                                  #
# Description:                                                           #
# A stop loss is a safety exit. Closes the trade if the price goes X far #
# against me. Placed at the Swing Low (for buys) and Swing Low           #
# (for sells)                                                            #
# Swing Low is: The lowest low of the last N candles before entry.       #
# Swing High is: The highest high of the last N candles beofre entry.    #
# N = 5, 10, 20                                                          #
# index = the candle no. where the entry signal began.                   #


def stop_loss(df, trade_type, index, slb=config.SWING_BACK):
	
	#change to use an ATR based stop loss. Add check for minial 0.05. 
	# Avoids large unit trade positions. 

    if trade_type:
        stop_loss = swing_low(df, index, slb)
    else:
        stop_loss = swing_high(df, index, slb)
    print(f'Stop Loss = {stop_loss}')
    return stop_loss

def swing_low(df, slb, index):
    start = max(0, index - slb) # check that index > 5, if not use index = 0
    return df["low"].iloc[start:index+1].min() #return the lowest of the values

def swing_high(df, index, slb):
    start = max (0, index - slb)
    return df["high"].iloc[start:index+1].max()

def atr_stop_loss(trade_type, row, atr, k=1.5):

    sl_distence = atr * k

    # Check for min stop loss distencee
    if sl_distence < 0.05:
        sl_distence = 0.05

    if trade_type:
        # Buy
        return row["high"] - sl_distence
    else:
        # Sell
        return row["low"] + sl_distence
    


    

# Function: take_profit()                                                #
# Description:                                                           #
# If price reaches the take profit, close the trade and loack in profit  #
# Uses Fixed 2R target - you take profit at twice your risk              #

def take_profit(entry_price, stop_loss, trade_type):

    if trade_type:                      # Buy/Long set up
        risk = entry_price - stop_loss
        tp = entry_price + (2 * risk)
    else:                               # Sell/Short set up
        risk = stop_loss - entry_price
        tp = entry_price - (2 * risk)

    return tp

# Function: order_units()                                               #
# Description:                                                          #
# Calculates the number of units to trade using a risk based potition   #
# sizing. DEpendent on how much you are willing to lose if the stop     #
# is hit and how far away the stop loss is (in price units)             #

def order_units(trade_type, entry_price, stop_loss): 


    if trade_type: # Buy/Long setup
        sl_distence = entry_price - stop_loss
    else:
        sl_distence =  stop_loss - entry_price

    units = config.MONEY_RISK / sl_distence

    return int(units)

# Function: order_data()                                                #
# Description:                                                          #
# Builds the data arguments required to place an order                  #

def order_data(stop_loss, take_profit, instrument, units, trade_type):

    if not trade_type: # Sell/Short set up
        units = -abs(units) 

    data = {
            "order": {
                "instrument": instrument,
                "units": units, 
                "type": "MARKET",
                "stopLossOnFill": {"price": f"{stop_loss:.3f}"},
                "takeProfitOnFill": {"price": f"{take_profit:.3f}"}
            }
        }
    return data

def strat_5020_Pullback(df, instrument):

    trade_type = None

    # Compute EMAs
    get_indicators(df=df, high_ind=50, low_ind=20)

    # Get latest data
    row = df.iloc[-1]
    #index = len(df) -1 #True index only required if using sming high or low stop loss
    data = {}

    # detect Long or Short setup
    if is_uptrend(row) and has_clear_trend(row=row) and pullback_to_ema20(row=row):
        if rejection_candle_uptrend(row):
            # Allow long setup (Buy)
            # Build Trade:
            trade_type = True
            sl = atr_stop_loss(trade_type, row, row["ATR_14"])
            tp = take_profit(row['high'], sl, trade_type)
            units = order_units(trade_type, row['high'], sl)
            data = order_data(sl, tp, instrument, units, trade_type)
            return data
    elif is_downtrend(row) and has_clear_trend(row=row) and pullback_to_ema20(row=row):
        if rejection_candle_downtrend(row):
            # Allow short setup (Sell)
            # Build Trade:
            trade_type = False
            sl = atr_stop_loss(trade_type, row, row["ATR_14"])
            tp = take_profit(row['low'], sl, trade_type)
            units = order_units(trade_type, row['low'], sl)
            data = order_data(sl, tp, instrument, units, trade_type)
            print (" Probably SELL")
            return data
    else:
        return None
        
