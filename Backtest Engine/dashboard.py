
# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(layout="wide")
st.title("Wealth Wave Strategy Dashboard")

summary = json.load(open("summary.json"))
trades = pd.read_csv("trade_log.csv") if __import__("os").path.exists("trade_log.csv") else pd.DataFrame()
open_pos = pd.read_csv("open_positions.csv") if __import__("os").path.exists("open_positions.csv") else pd.DataFrame()
equity = pd.read_csv("equity_curve.csv") if __import__("os").path.exists("equity_curve.csv") else pd.DataFrame()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Current Equity", f"₹{summary['current_equity']:,.0f}")
c2.metric("Realized P&L", f"₹{summary['realized_pnl']:,.0f}")
c3.metric("Unrealized P&L", f"₹{summary['unrealized_pnl']:,.0f}")
c4.metric("Net P&L", f"₹{summary['realized_pnl']+summary['unrealized_pnl']:,.0f}")

tabs = st.tabs(["Equity","Open Positions","Closed Trades"])

with tabs[0]:
    if len(equity):
        fig = px.line(equity, x="Date", y="Equity")
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.dataframe(open_pos, use_container_width=True)

with tabs[2]:
    st.dataframe(trades, use_container_width=True)
