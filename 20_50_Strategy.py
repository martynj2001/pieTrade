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

import pandas as pd
import pandas_ta_classic as ta

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
# DEtects current trend and returns True or False                     #

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
# Detects if the current candle touch or get near the 20 EMA. Returns    #
# True is it did indicatign a Pullback has been detected.                #

def pullback_to_ema20(row):

    tolerance = 0.25 * row["ATR_14"]

    # Candle touches the 20 EMA
    touched = row["low"] <= row["EMA_20"] <= row["high"]

    # Candle closes very near the 20 EMA
    near = abs(row["close"] - row["EMA_20"]) <= tolerance

    return touched or near

# Function: rejection_candle()                                           #
# Description:                                                           #
#                                                                        #

def rejection_candle():
    return

# Function: stop_loss()                                                  #
# Description:                                                           #
# 
def stop_loss():
    return

# Function: ake_profit()                                                 #
# Description:                                                           #
# 
def take_profit():
    return

def strat_5020_Pullback(df):

    long_setup, short_setup = False

    # Define Take Profit ration
    tp_ratio = 1.5

    # Compute EMAs
    get_indicators(df=df, high_ind=50, low_ind=20)

    # Get latest data
    row = df.iloc[-1]

    # Generate Long or Short setup
    if is_uptrend(row) and has_clear_trend(row=row) and pullback_to_ema20(row=row):
        # Allow long setup (Buy)
        print (" Probably BUY")
    elif is_downtrend(row) and has_clear_trend(row=row) and pullback_to_ema20(row=row):
        # Allow short setup (Sell)
        print(" Probably SELL")
