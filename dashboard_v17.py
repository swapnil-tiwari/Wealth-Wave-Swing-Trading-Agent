
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="52W Breakout Scanner", layout="wide")

# Auto refresh every 10 minutes
st_autorefresh(
    interval=600000,
    key="wealthwave_refresh"
)


st.markdown("""
<style>
.block-container {padding-top: 1rem;}
.metric-card{
    padding:16px;
    border-radius:14px;
    text-align:center;
    background: var(--secondary-background-color);
    border:1px solid rgba(128,128,128,.20);
}
.metric-value{
    font-size:28px;
    font-weight:700;
}
.metric-label{
    opacity:.8;
}
.header-card{
    padding:18px;
    border-radius:16px;
    text-align:center;
    background: var(--secondary-background-color);
    border:1px solid rgba(128,128,128,.20);
}
</style>
""", unsafe_allow_html=True)

def metric_card(title, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
    </div>
    """, unsafe_allow_html=True)



st.markdown("""
<style>
.ww-status-bar{
padding:10px;
border-radius:12px;
margin-bottom:12px;
text-align:center;
font-weight:600;
background:var(--secondary-background-color);
border:1px solid rgba(128,128,128,.2);
}
</style>
""", unsafe_allow_html=True)

FNO_FILE = "fno_symbols.csv"

REMAP = {
    "ZOMATO": "ETERNAL"
}

@st.cache_data(ttl=1800)
def load_symbols():
    df = pd.read_csv(FNO_FILE)
    return df["Symbol"].dropna().astype(str).str.strip().tolist()

def normalize_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def prepare(df):
    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA150"] = df["Close"].rolling(150).mean()
    df["EMA220"] = df["Close"].ewm(span=220, adjust=False).mean()
    df["EMA75"] = df["Close"].ewm(span=75, adjust=False).mean()

    df["52W_HIGH"] = df["Close"].rolling(252).max().shift(1)
    df["52W_LOW"] = df["Close"].rolling(252).min()

    below_ema = df["Close"] < df["EMA220"]

    df["DIPPED_90"] = (
        below_ema.rolling(90).sum() > 0
    )

    df["FILTER"] = (
        (df["SMA150"] > df["EMA220"])
        & (df["Close"] > df["SMA50"])
        & (df["SMA50"] > df["SMA150"])
        & (df["Close"] > (1.25 * df["52W_LOW"]))
        & (df["DIPPED_90"])
    )

    df["BREAKOUT"] = (
        df["Close"] > df["52W_HIGH"]
    )

    df["RECOVERY"] = (
        (df["Close"] > df["EMA220"])
        &
        (df["Close"].shift(1) <= df["EMA220"].shift(1))
    )

    df["FIRST_BREAKOUT_AFTER_RECOVERY"] = False
    df["BREAKOUT_PRICE"] = pd.NA

    recovery_points = df.index[df["RECOVERY"]]

    if len(recovery_points) > 0:

        latest_recovery = recovery_points[-1]

        recovery_pos = df.index.get_loc(latest_recovery)

        after_recovery = df.iloc[recovery_pos:]

        breakout_dates = after_recovery.index[
            after_recovery["BREAKOUT"]
        ]

        if len(breakout_dates) > 0:

            first_breakout_date = breakout_dates[0]

            breakout_price = float(
                df.loc[first_breakout_date, "Close"]
            )

            df.loc[
                first_breakout_date,
                "FIRST_BREAKOUT_AFTER_RECOVERY"
            ] = True

            df.loc[
                first_breakout_date:,
                "BREAKOUT_PRICE"
            ] = breakout_price

    df["BREAKOUT_PRICE"] = df["BREAKOUT_PRICE"].ffill()

    df["MOVE_FROM_BREAKOUT"] = (
        (df["Close"] - df["BREAKOUT_PRICE"])
        / df["BREAKOUT_PRICE"]
    ) * 100

    df["FRESH_BREAKOUT"] = (
        df["FIRST_BREAKOUT_AFTER_RECOVERY"]
    )

    return df

@st.cache_data(ttl=540)
def scan_market():

    rows = []

    symbols = load_symbols()

    progress = st.progress(0)

    for i, sym in enumerate(symbols):

        progress.progress((i + 1) / len(symbols))

        try:

            yahoo_symbol = REMAP.get(sym, sym) + ".NS"

            df = yf.download(
                yahoo_symbol,
                period="2y",
                auto_adjust=True,
                progress=False,
                threads=False
            )

            if df.empty:
                continue

            df = normalize_columns(df)

            if "Volume" not in df.columns:
                continue

            df = df[df["Volume"] > 0]

            if len(df) < 252:
                continue

            df = prepare(df)
            print(type(df))

            row = df.iloc[-1]

            if pd.isna(row["52W_HIGH"]):
                continue

            breakout_pct = (
                (float(row["Close"]) - float(row["52W_HIGH"]))
                / float(row["52W_HIGH"])
            ) * 100

            rows.append({
                "Symbol": sym,
                "CMP": round(float(row["Close"]), 2),
                "52W High": round(float(row["52W_HIGH"]), 2),
                "Breakout %": round(float(breakout_pct), 2),
                "Move From Breakout %": round(float(row["MOVE_FROM_BREAKOUT"]), 2),
                "Qualified": bool(row["FILTER"]),
                "Fresh Breakout": bool(row["FRESH_BREAKOUT"]),
                "EMA75": round(float(row["EMA75"]), 2)
            })

        except Exception as e:
            print(f"{sym} -> {e}")

    progress.empty()

    return pd.DataFrame(rows)


# ===== Wealth Wave UI =====
try:
    c_logo, c_title = st.columns([1,6])
    with c_logo:
        st.image("wealthwave_logo.jpg", width=110)
    with c_title:
        st.markdown("""
        <div class="header-card">
        <h1>🌊 Wealth Wave Breakout Scanner</h1>
        <p>Recovery → Consolidation → First Breakout After EMA220 Recovery</p>
        </div>
        """, unsafe_allow_html=True)
except:
    st.markdown("""
    <div class="header-card">
    <h1>🌊 Wealth Wave Breakout Scanner</h1>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="ww-status-bar">
🌊 Wealth Wave Scanner Active | Auto Refresh: 10 Minutes
</div>
""", unsafe_allow_html=True)

st.caption(f"Last Refresh: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}")


with st.expander("📖 Strategy Entry Conditions"):
    st.markdown("""
### Qualified Stock
- SMA150 > EMA220
- Close > SMA50
- SMA50 > SMA150
- Close > 1.25 × 52 Week Low
- Recovery above EMA220

### Fresh Breakout
- First 52 Week breakout after latest EMA220 recovery

### Workflow
⭐ Qualified + Fresh → Primary entries

👀 Near Breakouts → Watchlist

📈 Early Breakouts → Up to 3% from breakout

🔥 Extended → Already moved
""")

st.sidebar.title("🌊 Wealth Wave")
st.sidebar.divider()
st.sidebar.success("""
Recommended Order:

1. Qualified + Fresh

2. Near Breakouts

3. Early Breakouts

4. Extended
""")

col1, col2 = st.columns([1,5])

with col1:
    if st.button("🔄 Scan Again"):

        scan_market.clear()

        st.cache_data.clear()

        st.rerun()

data = scan_market()

if data.empty:
    st.error("No stocks processed. Check terminal output.")
    st.stop()

qualified_df = data[data["Qualified"]]

fresh_df = data[data["Fresh Breakout"]]

qualified_fresh_df = data[
    (data["Qualified"])
    &
    (data["Fresh Breakout"])
]

near_df = data[
    (data["Qualified"])
    &
    (data["Breakout %"] >= -3)
    &
    (data["Breakout %"] <= 0)
    &
    (
        data["Move From Breakout %"].fillna(0) <= 3
    )
]

early_df = data[
    (data["Move From Breakout %"] > 0)
    &
    (data["Move From Breakout %"] <= 3)
]

extended_df = data[
    data["Move From Breakout %"] > 3
]

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    metric_card("Scanned", len(data))
with c2:
    metric_card("🟢 Qualified", len(qualified_df))
with c3:
    metric_card("Fresh", len(fresh_df))
with c4:
    metric_card("Qualified+Fresh", len(qualified_fresh_df))
with c5:
    metric_card("👀 Near Breakouts", len(near_df))


tabs = st.tabs([
    "🟢 Qualified",
    "🔥 Fresh Breakouts",
    "⭐ Qualified + Fresh",
    "👀 Near Breakouts",
    "📈 Early Breakouts",
    "🚀 Extended",
    "📊 Chart"
])

with tabs[0]:
    st.info("Strong trend stocks that meet all Wealth Wave quality filters. These are fundamentally strong candidates preparing for a potential breakout.")
    st.dataframe(qualified_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[1]:
    st.info("Stocks giving their first 52-week breakout after recovering above EMA220. Represents the earliest stage of a potential new leadership trend.")
    st.dataframe(fresh_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[2]:
    st.success("Strong trend stocks delivering their first breakout after recovery. These represent the highest-probability Wealth Wave entry opportunities.")
    st.dataframe(qualified_fresh_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[3]:
    st.info("Qualified stocks trading within 3% of their 52-week high. Keep these on radar as they may trigger a breakout soon.")
    st.dataframe(near_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[4]:
    st.info("Stocks that have recently broken out and are within 3% of their breakout level. Suitable for traders who missed the initial breakout.")
    st.dataframe(early_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[5]:
    st.warning("Stocks that have already moved more than 3% above their breakout level. Indicates strength, but chasing entries may carry higher risk.")
    st.dataframe(extended_df.sort_values("Breakout %", ascending=False), use_container_width=True)

with tabs[6]:
    st.info("Visualize price action, moving averages, EMA220 recovery and breakout levels. Use this section to validate trade setups.")
    symbol = st.selectbox("Select Symbol", sorted(data["Symbol"].unique()))

    yahoo_symbol = REMAP.get(symbol, symbol) + ".NS"

    chart_df = yf.download(
        yahoo_symbol,
        period="2y",
        auto_adjust=True,
        progress=False
    )

    chart_df = normalize_columns(chart_df)
    chart_df = prepare(chart_df)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["SMA50"], name="SMA50"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["SMA150"], name="SMA150"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["EMA220"], name="EMA220"))
    fig.add_trace(go.Scatter(x=chart_df.index, y=chart_df["52W_HIGH"], name="52W High"))

    fig.update_layout(
        height=750,
        template="plotly",
        hovermode="x unified",
        title=f"{symbol} - Wealth Wave Analysis"
    )

    st.plotly_chart(fig, use_container_width=True)
