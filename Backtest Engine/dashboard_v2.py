
import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Wealth Wave Strategy Dashboard", layout="wide")

# ---------- Load Data ----------
summary = json.load(open("summary.json")) if os.path.exists("summary.json") else {}

trades = pd.read_csv("trade_log.csv") if os.path.exists("trade_log.csv") else pd.DataFrame()
open_pos = pd.read_csv("open_positions.csv") if os.path.exists("open_positions.csv") else pd.DataFrame()
equity = pd.read_csv("equity_curve.csv") if os.path.exists("equity_curve.csv") else pd.DataFrame()

# ---------- Calculations ----------
if not trades.empty:
    trades["ReturnPct"] = ((trades["ExitPrice"] - trades["EntryPrice"]) / trades["EntryPrice"]) * 100

if not open_pos.empty:
    open_pos["ReturnPct"] = ((open_pos["CurrentPrice"] - open_pos["EntryPrice"]) / open_pos["EntryPrice"]) * 100

initial_capital = summary.get("initial_capital", 100000)
current_equity = summary.get("current_equity", initial_capital)
realized_pnl = summary.get("realized_pnl", 0)
unrealized_pnl = summary.get("unrealized_pnl", 0)

portfolio_return = ((current_equity - initial_capital) / initial_capital) * 100

# ---------- Header ----------
st.title("📈 Wealth Wave Strategy Dashboard")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Current Equity", f"₹{current_equity:,.0f}")
c2.metric("Portfolio Return", f"{portfolio_return:.2f}%")
c3.metric("Realized P&L", f"₹{realized_pnl:,.0f}")
c4.metric("Unrealized P&L", f"₹{unrealized_pnl:,.0f}")
c5.metric("Net P&L", f"₹{realized_pnl + unrealized_pnl:,.0f}")

tabs = st.tabs([
    "📊 Portfolio Overview",
    "🟢 Open Positions",
    "🔴 Closed Trades",
    "📈 Analytics",
    "🏆 Symbol Analysis"
])

# ---------- Overview ----------
with tabs[0]:
    st.subheader("Equity Curve")

    if not equity.empty:
        fig = px.line(equity, x="Date", y="Equity")
        st.plotly_chart(fig, use_container_width=True)

        equity["Peak"] = equity["Equity"].cummax()
        equity["DrawdownPct"] = ((equity["Equity"] / equity["Peak"]) - 1) * 100

        fig2 = px.area(
            equity,
            x="Date",
            y="DrawdownPct",
            title="Drawdown %"
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------- Open Positions ----------
with tabs[1]:
    st.subheader("Open Positions")

    if not open_pos.empty:

        winners = (open_pos["ReturnPct"] > 0).sum()
        losers = (open_pos["ReturnPct"] <= 0).sum()

        a,b,c,d = st.columns(4)

        a.metric("Open Trades", len(open_pos))
        b.metric("Winning Positions", winners)
        c.metric("Losing Positions", losers)
        d.metric("Avg Return %", f"{open_pos['ReturnPct'].mean():.2f}%")

        st.dataframe(
            open_pos.style.format({
                "EntryPrice":"{:.2f}",
                "CurrentPrice":"{:.2f}",
                "UnrealizedPnL":"{:.2f}",
                "ReturnPct":"{:.2f}%"
            }),
            use_container_width=True
        )

        fig = px.bar(
            open_pos.sort_values("ReturnPct"),
            x="Symbol",
            y="ReturnPct",
            title="Open Position Returns (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------- Closed Trades ----------
with tabs[2]:
    st.subheader("Closed Trades")

    if not trades.empty:

        winners = trades[trades["PnL"] > 0]
        losers = trades[trades["PnL"] <= 0]

        win_rate = (len(winners) / len(trades)) * 100 if len(trades) else 0

        a,b,c,d = st.columns(4)

        a.metric("Closed Trades", len(trades))
        b.metric("Win Rate", f"{win_rate:.2f}%")
        c.metric("Avg Win", f"{winners['ReturnPct'].mean():.2f}%" if len(winners) else "0%")
        d.metric("Avg Loss", f"{losers['ReturnPct'].mean():.2f}%" if len(losers) else "0%")

        st.dataframe(
            trades.style.format({
                "EntryPrice":"{:.2f}",
                "ExitPrice":"{:.2f}",
                "PnL":"{:.2f}",
                "ReturnPct":"{:.2f}%"
            }),
            use_container_width=True
        )

# ---------- Analytics ----------
with tabs[3]:

    if not trades.empty:

        gross_profit = trades.loc[trades["PnL"] > 0, "PnL"].sum()
        gross_loss = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())

        profit_factor = gross_profit / gross_loss if gross_loss else 0

        st.metric("Profit Factor", f"{profit_factor:.2f}")

        fig = px.histogram(
            trades,
            x="ReturnPct",
            nbins=25,
            title="Closed Trade Return Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

# ---------- Symbol Analysis ----------
with tabs[4]:

    if not trades.empty:

        symbol_stats = trades.groupby("Symbol").agg(
            Trades=("Symbol","count"),
            TotalPnL=("PnL","sum"),
            AvgReturn=("ReturnPct","mean")
        ).reset_index()

        st.dataframe(
            symbol_stats.sort_values("TotalPnL", ascending=False),
            use_container_width=True
        )

        fig = px.bar(
            symbol_stats.sort_values("TotalPnL"),
            x="Symbol",
            y="TotalPnL",
            title="PnL by Symbol"
        )

        st.plotly_chart(fig, use_container_width=True)

st.sidebar.header("Strategy Summary")
st.sidebar.write(f"Initial Capital: ₹{initial_capital:,.0f}")
st.sidebar.write(f"Current Equity: ₹{current_equity:,.0f}")
st.sidebar.write(f"Portfolio Return: {portfolio_return:.2f}%")
