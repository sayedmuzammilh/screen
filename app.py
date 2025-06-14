import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.graph_objects as go
import io

# ---- Load NASDAQ Tickers and Metadata ----
@st.cache_data
def load_nasdaq_metadata():
    url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
    df = pd.read_csv(url)
    return df[['Symbol', 'Security Name']]

@st.cache_data
def get_sector_and_market_cap(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "N/A")
        market_cap = info.get("marketCap", 0)
        return sector, market_cap
    except:
        return "N/A", 0

# ---- Stock Screener Logic ----
def has_fallen_consecutively(ticker, days, min_drop_pct):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=f"{days + 5}d")
    hist = hist.tail(days)

    if len(hist) < days:
        return False, 0, hist

    closes = hist["Close"]
    daily_fall = closes.diff().dropna() < 0

    if daily_fall.sum() == days:
        total_drop_pct = ((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100
        if total_drop_pct < -min_drop_pct:
            return True, total_drop_pct, closes
    return False, 0, closes

def get_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    rev_g = info.get("revenueGrowth", 0) * 100
    earn_g = info.get("earningsGrowth", 0) * 100
    debt_eq = info.get("debtToEquity", 999)
    return rev_g, earn_g, debt_eq

def screen_stocks(df_meta, x_days, pct_drop, sector_filter, market_cap_filter):
    matched = []
    history_data = {}

    for _, row in df_meta.iterrows():
        ticker = row["Symbol"]
        try:
            sector, mcap = get_sector_and_market_cap(ticker)
            if (sector_filter != "All" and sector != sector_filter) or (mcap < market_cap_filter):
                continue

            is_down, drop_pct, closes = has_fallen_consecutively(ticker, x_days, pct_drop)
            if is_down:
                rev, earn, debt = get_fundamentals(ticker)
                if rev > 5 and earn > 7 and debt < 80:
                    matched.append({
                        "Ticker": ticker,
                        "Name": row["Security Name"],
                        "Sector": sector,
                        "Market Cap ($B)": round(mcap / 1e9, 2),
                        "Drop (%)": round(drop_pct, 2),
                        "Revenue Growth (%)": round(rev, 2),
                        "Earnings Growth (%)": round(earn, 2),
                        "Debt/Equity (%)": round(debt, 2)
                    })
                    history_data[ticker] = closes
        except Exception as e:
            continue

    return pd.DataFrame(matched), history_data

# ---- Streamlit UI ----
st.set_page_config(layout="wide")
st.title("📉 NASDAQ Stock Screener (Falling X Days + Fundamentals)")

nasdaq_df = load_nasdaq_metadata()
tickers = nasdaq_df["Symbol"].tolist()

x_days = st.slider("Consecutive Red Days", 2, 10, 5)
pct_drop = st.slider("Minimum % Drop over Period", 1, 20, 5)

# Sector and Market Cap Filters
sectors = ["All"] + sorted({get_sector_and_market_cap(t)[0] for t in tickers[:100]})
sector_filter = st.selectbox("Filter by Sector", sectors)
market_cap_filter = st.slider("Min Market Cap (Billion USD)", 0, 500, 10)

if st.button("🔍 Run Screener"):
    with st.spinner("Running screener..."):
        result_df, chart_data = screen_stocks(nasdaq_df, x_days, pct_drop, sector_filter, market_cap_filter * 1e9)

    if result_df.empty:
        st.warning("No matching stocks found.")
    else:
        st.success(f"✅ {len(result_df)} matching stocks found.")
        st.dataframe(result_df, use_container_width=True)

        # Export
        csv = result_df.to_csv(index=False).encode()
        st.download_button("📥 Download CSV", data=csv, file_name="stock_screener_results.csv", mime='text/csv')

        # Charts
        st.subheader("📈 Price Charts")
        for ticker in result_df["Ticker"]:
            st.markdown(f"**{ticker} - Last {x_days} Days**")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=chart_data[ticker].values,
                x=chart_data[ticker].index,
                mode="lines+markers",
                name=ticker
            ))
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
