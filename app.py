import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="NASDAQ Screener (Optimized)", layout="wide")
st.title("🚀 Optimized NASDAQ Screener (From Cached Data)")

x_days = st.slider("📉 Number of continuous red days", 2, 10, 3)
min_drop = st.slider("📉 Minimum total % drop", 1, 50, 5)
min_rev = st.slider("📈 Min Revenue Growth (%)", 0, 50, 5)
min_earn = st.slider("💰 Min Earnings Growth (%)", 0, 50, 7)
max_debt = st.slider("📉 Max Debt/Equity", 0, 200, 20)

# Load cached data
fundamentals = pd.read_parquet("cache/fundamentals.parquet")
prices = pd.read_parquet("cache/price_data.parquet")

# Filter fundamentals
filtered = fundamentals[
    (fundamentals["RevenueGrowth"] >= min_rev) &
    (fundamentals["EarningsGrowth"] >= min_earn) &
    (fundamentals["DebtEquity"] <= max_debt)
]

results = []
charts = {}

# Group price data
grouped = prices.groupby("Ticker")

progress = st.progress(0)
total = len(filtered)

for i, row in filtered.iterrows():
    ticker = row["Ticker"]
    if ticker not in grouped.groups: continue
    df = grouped.get_group(ticker).tail(x_days)
    if len(df) < x_days: continue
    closes = df["Close"].values
    if all(closes[i] < closes[i-1] for i in range(1, len(closes))):
        drop = (closes[0] - closes[-1]) / closes[0] * 100
        if drop >= min_drop:
            results.append({
                "Ticker": ticker,
                "Drop %": round(drop, 2),
                "Revenue Growth %": round(row["RevenueGrowth"], 2),
                "Earnings Growth %": round(row["EarningsGrowth"], 2),
                "Debt/Equity": round(row["DebtEquity"], 2)
            })
            charts[ticker] = df
    progress.progress(i / total)

# Display
if results:
    df_show = pd.DataFrame(results)
    st.success(f"✅ {len(results)} stocks found.")
    st.dataframe(df_show, use_container_width=True)

    for ticker in df_show["Ticker"]:
        df_chart = charts[ticker]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["Close"], mode="lines+markers"))
        fig.update_layout(title=f"{ticker} - Last {x_days} Days", xaxis_title="Date", yaxis_title="Close Price")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ No matching stocks found.")
