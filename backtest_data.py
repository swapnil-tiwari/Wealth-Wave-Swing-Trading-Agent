import pandas as pd
import numpy as np
import os
from tqdm import tqdm

# ==========================
# CONFIG
# ==========================

DATA_FOLDER = "data"

INITIAL_CAPITAL = 100000
POSITION_SIZE_PCT = 0.10
MAX_POSITION_SIZE = INITIAL_CAPITAL * POSITION_SIZE_PCT

START_DATE = "2025-01-01"

# ==========================


portfolio_cash = INITIAL_CAPITAL
open_positions = {}
trade_log = []
daily_equity = []


def prepare_stock(df):

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values("Date")

    # Indicators
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA150'] = df['Close'].rolling(150).mean()

    df['EMA220'] = (
        df['Close']
        .ewm(span=220, adjust=False)
        .mean()
    )

    # Previous 52 week high
    df['52W_HIGH'] = (
        df['Close']
        .rolling(252)
        .max()
        .shift(1)
    )

    df['52W_LOW'] = (
        df['Close']
        .rolling(252)
        .min()
    )

    # Dipped below EMA in last 90 days
    below_ema = (df['Close'] < df['EMA220'])

    df['DIPPED_90'] = (
        below_ema
        .rolling(90)
        .sum()
        > 0
    )

    # Entry setup filters
    df['FILTER'] = (
        (df['SMA150'] > df['EMA220']) &
        (df['Close'] > df['SMA50']) &
        (df['SMA50'] > df['SMA150']) &
        (df['Close'] > (1.25 * df['52W_LOW'])) &
        (df['DIPPED_90'])
    )

    # Breakout signal
    df['ENTRY_SIGNAL'] = (
        df['FILTER'] &
        (df['Close'] > df['52W_HIGH'])
    )

    return df


# ==========================
# LOAD ALL STOCKS
# ==========================

stock_data = {}

files = [
    f for f in os.listdir(DATA_FOLDER)
    if f.endswith(".csv")
]

for file in tqdm(files):

    symbol = file.replace(".csv", "")

    try:

        df = pd.read_csv(
            os.path.join(DATA_FOLDER, file)
        )

        stock_data[symbol] = prepare_stock(df)

    except Exception as e:
        print(symbol, e)


# ==========================
# CREATE MASTER DATES
# ==========================

all_dates = sorted(
    list(
        set(
            pd.concat(
                [x['Date'] for x in stock_data.values()]
            )
        )
    )
)


# ==========================
# BACKTEST LOOP
# ==========================

for current_date in tqdm(all_dates):

    # ========= EXITS =========

    symbols_to_remove = []

    for symbol, position in open_positions.items():

        df = stock_data[symbol]

        row = df[df['Date']==current_date]

        if len(row)==0:
            continue

        row = row.iloc[0]

        exit_signal = (

            row['Close'] < row['EMA220']

            or

            row['Close'] <
            position['entry_price']*0.85
        )

        if exit_signal:

            next_idx = df[
                df['Date']==current_date
            ].index[0] + 1

            if next_idx >= len(df):
                continue

            exit_row = df.iloc[next_idx]

            exit_price = exit_row['Open']

            pnl = (
                exit_price -
                position['entry_price']
            ) * position['shares']

            portfolio_cash += (
                position['shares']
                * exit_price
            )

            trade_log.append({

                'Symbol':symbol,
                'EntryDate':position['entry_date'],
                'ExitDate':exit_row['Date'],
                'EntryPrice':position['entry_price'],
                'ExitPrice':exit_price,
                'Shares':position['shares'],
                'PnL':pnl

            })

            symbols_to_remove.append(symbol)

    for s in symbols_to_remove:
        del open_positions[s]


    # ========= ENTRIES =========

    for symbol, df in stock_data.items():

        if symbol in open_positions:
            continue

        row = df[df['Date']==current_date]

        if len(row)==0:
            continue

        row = row.iloc[0]

        if not row['ENTRY_SIGNAL']:
            continue

        next_idx = df[
            df['Date']==current_date
        ].index[0] + 1

        if next_idx >= len(df):
            continue

        next_row = df.iloc[next_idx]

        entry_price = next_row['Open']

        allocation = min(
            MAX_POSITION_SIZE,
            portfolio_cash
        )

        if allocation <= 0:
            continue

        shares = int(
            allocation / entry_price
        )

        if shares <=0:
            continue

        cost = shares * entry_price

        portfolio_cash -= cost

        open_positions[symbol] = {

            'entry_price':entry_price,
            'shares':shares,
            'entry_date':next_row['Date']

        }


    # ========= DAILY EQUITY =========

    current_equity = portfolio_cash

    for symbol, pos in open_positions.items():

        df = stock_data[symbol]

        row = df[df['Date']==current_date]

        if len(row)==0:
            continue

        current_equity += (
            pos['shares']
            * row.iloc[0]['Close']
        )

    daily_equity.append(
        [current_date,current_equity]
    )


# ==========================
# RESULTS
# ==========================

trades = pd.DataFrame(trade_log)

equity = pd.DataFrame(
    daily_equity,
    columns=['Date','Equity']
)

if len(trades):

    total_return = (
        (equity.iloc[-1]['Equity']
        - INITIAL_CAPITAL)
        / INITIAL_CAPITAL
    )*100

    win_rate = (
        (trades['PnL']>0).mean()
    )*100

    max_dd = (
        (
            equity['Equity']
            /
            equity['Equity'].cummax()
        ) -1
    ).min()*100

    print("\n====== RESULTS ======")

    print(
        f"Initial Capital : ₹{INITIAL_CAPITAL:,.0f}"
    )

    print(
        f"Final Capital : ₹{equity.iloc[-1]['Equity']:,.0f}"
    )

    print(
        f"Total Return : {total_return:.2f}%"
    )

    print(
        f"Win Rate : {win_rate:.2f}%"
    )

    print(
        f"Max Drawdown : {max_dd:.2f}%"
    )

    print(
        f"Total Trades : {len(trades)}"
    )
    print("\nOpen Positions Remaining:")
    print(len(open_positions))

    for sym, pos in open_positions.items():
     print(sym, pos)

    trades.to_csv(
        "trade_log.csv",
        index=False
    )

    equity.to_csv(
        "equity_curve.csv",
        index=False
    )

    print(
        "\nSaved trade_log.csv and equity_curve.csv"
    )

else:
    print("No trades found")