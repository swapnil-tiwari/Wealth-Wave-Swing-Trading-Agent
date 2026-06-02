
# backtest.py
import pandas as pd
import numpy as np
import os, json

DATA_FOLDER = "data"
INITIAL_CAPITAL = 100000
TRADE_SIZE = 10000
START_DATE = "2025-01-01"

portfolio_cash = INITIAL_CAPITAL
open_positions = {}
trade_log = []
daily_equity = []

def prepare_stock(df):
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["EMA220"] = df["Close"].ewm(span=220, adjust=False).mean()
    df["EMA100"] = df["Close"].ewm(span=100, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA75"] = df["Close"].ewm(span=75, adjust=False).mean()
    df["52W_HIGH"] = df["Close"].rolling(252).max().shift(1)
    df["52W_LOW"] = df["Close"].rolling(252).min()

    below_ema = (df["Close"] < df["EMA220"])
    df["DIPPED_90"] = below_ema.rolling(90).sum() > 0

    df["FILTER"] = (
        (df["SMA150"] > df["EMA220"]) &
        (df["Close"] > df["SMA50"]) &
        (df["SMA50"] > df["SMA150"]) &
        (df["Close"] > (1.25 * df["52W_LOW"])) &
        (df["DIPPED_90"])
    )

    df["ENTRY_SIGNAL"] = df["FILTER"] & (df["Close"] > df["52W_HIGH"])
    return df

stock_data = {}
for f in os.listdir(DATA_FOLDER):
    if f.endswith(".csv"):
        sym = f.replace(".csv","")
        df = pd.read_csv(os.path.join(DATA_FOLDER,f))
        df = prepare_stock(df)
        stock_data[sym] = df

all_dates = sorted(list(set(pd.concat([x["Date"] for x in stock_data.values()]))))

for current_date in all_dates:
    if current_date < pd.to_datetime(START_DATE):
        continue

    remove = []
    for symbol, pos in open_positions.items():
        df = stock_data[symbol]
        row = df[df["Date"] == current_date]
        if len(row)==0: continue
        row = row.iloc[0]

        exit_signal = (
            row["Close"] < row["EMA75"] or
            row["Close"] < pos["entry_price"] * 0.85
        )

        if exit_signal:
            idx = df[df["Date"]==current_date].index[0] + 1
            if idx >= len(df): continue
            exit_row = df.iloc[idx]
            exit_price = exit_row["Open"]
            pnl = (exit_price - pos["entry_price"]) * pos["shares"]

            portfolio_cash += pos["shares"] * exit_price

            trade_log.append({
                "Symbol":symbol,
                "EntryDate":pos["entry_date"],
                "ExitDate":exit_row["Date"],
                "EntryPrice":pos["entry_price"],
                "ExitPrice":exit_price,
                "Shares":pos["shares"],
                "PnL":pnl,
                "HoldingDays":(exit_row["Date"]-pos["entry_date"]).days
            })
            remove.append(symbol)

    for s in remove:
        del open_positions[s]

    for symbol, df in stock_data.items():
        if symbol in open_positions:
            continue

        row = df[df["Date"] == current_date]
        if len(row)==0: continue
        row = row.iloc[0]

        if not row["ENTRY_SIGNAL"]:
            continue

        idx = df[df["Date"]==current_date].index[0] + 1
        if idx >= len(df): continue

        next_row = df.iloc[idx]
        entry_price = next_row["Open"]

        if portfolio_cash < TRADE_SIZE:
            continue

        shares = int(TRADE_SIZE / entry_price)
        if shares <= 0:
            continue

        cost = shares * entry_price
        portfolio_cash -= cost

        open_positions[symbol] = {
            "entry_price": entry_price,
            "shares": shares,
            "entry_date": next_row["Date"]
        }

    equity = portfolio_cash
    for symbol, pos in open_positions.items():
        df = stock_data[symbol]
        row = df[df["Date"] == current_date]
        if len(row):
            equity += pos["shares"] * row.iloc[0]["Close"]

    daily_equity.append([current_date, equity])

trades = pd.DataFrame(trade_log)
equity_df = pd.DataFrame(daily_equity, columns=["Date","Equity"])

open_rows = []
unrealized = 0
for symbol, pos in open_positions.items():
    last_close = stock_data[symbol]["Close"].iloc[-1]
    pnl = (last_close - pos["entry_price"]) * pos["shares"]
    unrealized += pnl
    open_rows.append({
        "Symbol":symbol,
        "EntryDate":pos["entry_date"],
        "EntryPrice":pos["entry_price"],
        "CurrentPrice":last_close,
        "Shares":pos["shares"],
        "UnrealizedPnL":pnl
    })

pd.DataFrame(open_rows).to_csv("open_positions.csv", index=False)
trades.to_csv("trade_log.csv", index=False)
equity_df.to_csv("equity_curve.csv", index=False)

summary = {
    "initial_capital": INITIAL_CAPITAL,
    "realized_pnl": float(trades["PnL"].sum()) if len(trades) else 0,
    "unrealized_pnl": float(unrealized),
    "current_equity": float(equity_df["Equity"].iloc[-1]) if len(equity_df) else INITIAL_CAPITAL
}
with open("summary.json","w") as f:
    json.dump(summary,f,indent=2)

print("Backtest complete")
