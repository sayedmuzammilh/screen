import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="NASDAQ Screener", layout="wide")
st.title("📉 NASDAQ Stock Screener - Continuous Fall & Fundamentals")

# User inputs
x_days = st.slider("📉 Number of continuous red days", min_value=2, max_value=10, value=3)
min_drop = st.slider("📉 Minimum total % drop over x days", min_value=1, max_value=50, value=5)

st.markdown(f"🔍 Screening NASDAQ stocks that have fallen {x_days} days in a row and dropped ≥ {min_drop}%.")

@st.cache_data(show_spinner=False)
def get_nasdaq_tickers():
    url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
    df = pd.read_csv(url)
    return df["Symbol"].dropna().unique().tolist()

@st.cache_data(show_spinner=False)
def get_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        rev_g = info.get("revenueGrowth", 0) * 100
        earn_g = info.get("earningsGrowth", 0) * 100
        debt_eq = info.get("debtToEquity", 999)
        return rev_g, earn_g, debt_eq
    except:
        return 0, 0, 999

def check_red_days(ticker, x, min_pct_drop):
    try:
        df = yf.download(ticker, period=f"{x+5}d", interval="1d", progress=False)
        df = df.tail(x)
        if len(df) < x:
            return False, None, None
        closes = df['Close']
        if all(closes.iloc[i] < closes.iloc[i-1] for i in range(1, len(closes))):
            drop = (closes.iloc[0] - closes.iloc[-1]) / closes.iloc[0] * 100
            if drop >= min_pct_drop:
                return True, round(drop, 2), df
    except:
        return False, None, None
    return False, None, None

# Main processing
nasdaq_tickers = get_nasdaq_tickers()
results = []
charts = {}

with st.spinner("🔎 Scanning tickers..."):
    for ticker in nasdaq_tickers:
        valid, drop_pct, df = check_red_days(ticker, x_days, min_drop)
        if valid:
            rev_g, earn_g, debt_eq = get_fundamentals(ticker)
            if rev_g > 5 and earn_g > 7 and debt_eq < 20:
                results.append({
                    "Ticker": ticker,
                    "Drop %": drop_pct,
                    "Revenue Growth %": round(rev_g, 2),
                    "Earnings Growth %": round(earn_g, 2),
                    "Debt/Equity": round(debt_eq, 2)
                })
                charts[ticker] = df

# Display results
if results:
    df_results = pd.DataFrame(results)
    st.success(f"✅ {len(results)} stocks found.")
    st.dataframe(df_results, use_container_width=True)

    st.subheader("📈 Charts")
    for ticker in df_results["Ticker"]:
        df_chart = charts[ticker]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'], mode='lines+markers', name='Close'))
        fig.update_layout(title=f"{ticker} - Last {x_days} Days", xaxis_title="Date", yaxis_title="Close Price")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ No stocks found matching all criteria.")
