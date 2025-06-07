# Updated Streamlit App using flatlib with DEMO Ephemeris (Streamlit Cloud Compatible)

import streamlit as st
import yfinance as yf
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from flatlib.chart import Chart
from flatlib import ephem
import datetime
import plotly.graph_objects as go

# === Force flatlib to use DEMO ephemeris (no swisseph) === #
ephem.set_ephem_dir('DEMO')

# Constants
DEFAULT_TIME = datetime.time(10, 0)  # 10 AM IST
DEFAULT_LOCATION = GeoPos('28.6139', '77.2090')  # New Delhi as default location

# Vimshottari Mahadasha Years
DASHA_YEARS = {
    'KET': 7,
    'VEN': 20,
    'SUN': 6,
    'MOON': 10,
    'MAR': 7,
    'RAH': 18,
    'JUP': 16,
    'SAT': 19,
    'MER': 17
}

DASHA_SEQUENCE = ['KET', 'VEN', 'SUN', 'MOON', 'MAR', 'RAH', 'JUP', 'SAT', 'MER']

# Helper functions
def get_moon_position(date):
    dt_str = date.strftime('%Y/%m/%d %H:%M:%S')
    dt = Datetime(dt_str, "+05:30")
    chart = Chart(dt, DEFAULT_LOCATION)
    moon = chart.get(const.MOON)
    return float(moon.lon)

def get_dasha_start_index(moon_lon):
    nakshatra_index = int(moon_lon // (360 / 27))
    return nakshatra_index % 9

def get_dasha_balance(moon_lon):
    degrees_per_nakshatra = 360 / 27
    pos_in_nakshatra = moon_lon % degrees_per_nakshatra
    portion = 1 - (pos_in_nakshatra / degrees_per_nakshatra)
    return portion

def build_dasha_periods(start_idx, balance, start_date):
    periods = []
    idx = start_idx
    current_date = start_date

    # First dasha (partial)
    first_lord = DASHA_SEQUENCE[idx]
    years = DASHA_YEARS[first_lord] * balance
    delta = datetime.timedelta(days=years * 365.25)
    next_date = current_date + delta
    periods.append((first_lord, current_date, next_date))
    current_date = next_date

    # Next full dashas
    for _ in range(8):
        idx = (idx + 1) % 9
        lord = DASHA_SEQUENCE[idx]
        years = DASHA_YEARS[lord]
        delta = datetime.timedelta(days=years * 365.25)
        next_date = current_date + delta
        periods.append((lord, current_date, next_date))
        current_date = next_date

    return periods

def plot_with_dashas(df, dasha_periods):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'))

    colors = ['#FFCCCC','#CCFFCC','#CCCCFF','#FFCC99','#99CCFF','#FF99CC','#CCFF99','#9999FF','#FF9966']

    for i, (lord, start, end) in enumerate(dasha_periods):
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=colors[i % len(colors)], opacity=0.2,
            annotation_text=lord, annotation_position="top left",
            line_width=0
        )

    fig.update_layout(title="Stock Price with Vimshottari Mahadasha",
                      xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)

# Streamlit UI
st.title("Vimshottari Dasha Stock Analyzer (Cloud Compatible)")

symbol = st.text_input("Enter NSE stock symbol", value="RELIANCE").upper()
listing_date = st.date_input("Enter Listing Date", value=datetime.date(2000, 1, 1))

if st.button("Calculate & Plot"):
    try:
        listing_dt = datetime.datetime.combine(listing_date, DEFAULT_TIME)
        moon_lon = get_moon_position(listing_dt)
        start_idx = get_dasha_start_index(moon_lon)
        balance = get_dasha_balance(moon_lon)

        dasha_periods = build_dasha_periods(start_idx, balance, listing_dt)

        st.success(f"Starting Mahadasha: {DASHA_SEQUENCE[start_idx]} (Balance: {balance:.2%})")

        df = yf.download(symbol + ".NS", start=listing_date.strftime('%Y-%m-%d'))
        if df.empty:
            st.warning("No stock data found. Please check the symbol and date.")
        else:
            plot_with_dashas(df, dasha_periods)

    except Exception as e:
        st.error(f"Error: {e}")

