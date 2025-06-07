import streamlit as st
import yfinance as yf
import swisseph as swe
import datetime
import pytz
import plotly.graph_objects as go

# --- Constants ---
AYANAMSHA_MODE = swe.SIDM_LAHIRI  # Chitrapaksha Lahiri Ayanamsa
DEFAULT_LISTING_TIME = datetime.time(10, 0)  # 10:00 AM IST

# Vimshottari Dasha lengths in years (Mahadasha)
DASHA_YEARS = [
    6,  # Ketu
    16, # Venus
    10, # Sun
    7,  # Moon
    18, # Mars
    17, # Rahu
    19, # Jupiter
    20, # Saturn
    15  # Mercury
]

DASHA_NAMES = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

# --- Functions ---

def get_julian_day(date, time_obj, tzinfo):
    """Convert date+time+timezone to Julian Day (UT) for Swiss Ephemeris"""
    dt = datetime.datetime.combine(date, time_obj)
    dt_utc = dt.astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    return jd

def get_moon_longitude(jd_ut):
    """Return Moon longitude (degrees) at given Julian Day UT"""
    moon_pos = swe.calc_ut(jd_ut, swe.MOON)[0]
    return moon_pos

def get_dasha_start_index(moon_longitude):
    """Calculate starting dasha index (0-8) based on moon's nakshatra"""
    nakshatra = int(moon_longitude // (360/27))
    # Vimshottari Dasha sequence starts from Ketu (index 0)
    # The starting dasha is based on the nakshatra index modulo 9
    # Vimshottari sequence order is fixed; starting point shifts by nakshatra.
    return (7 - nakshatra) % 9  # Adjusted per classical Vimshottari system

def get_dasha_balance(moon_longitude):
    """Calculate remaining portion of current dasha (0-1)"""
    nakshatra_pos = moon_longitude % (360/27)
    portion = 1 - (nakshatra_pos / (360/27))
    return portion

def build_dasha_periods(start_index, balance, start_jd):
    """Build list of (name, start_date, end_date) for Mahadasha periods"""
    periods = []
    current_jd = start_jd
    # First dasha uses balance fraction
    length_years = DASHA_YEARS[start_index] * balance
    length_days = length_years * 365.25
    end_jd = current_jd + length_days
    periods.append((DASHA_NAMES[start_index], swe.revjul(end_jd)[:3], swe.revjul(current_jd)[:3]))  # start, end dates
    
    current_jd = end_jd
    # Next dashas full length
    for i in range(1,9):
        idx = (start_index + i) % 9
        length_years = DASHA_YEARS[idx]
        length_days = length_years * 365.25
        end_jd = current_jd + length_days
        periods.append((DASHA_NAMES[idx], swe.revjul(current_jd)[:3], swe.revjul(end_jd)[:3]))
        current_jd = end_jd
    return periods

def revjul_to_date(rj):
    """Convert revjul output tuple (year, month, day, hour) to date string"""
    y,m,d = rj[0], rj[1], rj[2]
    return datetime.date(y,m,d)

def plot_price_with_dasha(df, dasha_periods):
    """Plot stock price with dasha colored bands"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'))

    colors = ['#FFCCCC','#CCFFCC','#CCCCFF','#FFCC99','#99CCFF','#FF99CC','#CCFF99','#9999FF','#FF9966']

    for i, (name, start_rj, end_rj) in enumerate(dasha_periods):
        start_date = revjul_to_date(start_rj)
        end_date = revjul_to_date(end_rj)
        fig.add_vrect(
            x0=start_date, x1=end_date,
            fillcolor=colors[i%len(colors)], opacity=0.2,
            layer="below", line_width=0,
            annotation_text=name,
            annotation_position="top left"
        )
    fig.update_layout(title="Stock Price with Vimshottari Mahadasha",
                      xaxis_title="Date",
                      yaxis_title="Price")
    st.plotly_chart(fig, use_container_width=True)

# --- Streamlit UI ---

st.title("Vimshottari Dasha Stock Analyzer")

symbol = st.text_input("Enter NSE stock symbol or index (e.g. RELIANCE, NIFTY)", value="RELIANCE").upper()

listing_date_input = st.date_input("Enter Listing Date (if unknown, use default)", value=datetime.date(2000,1,1))

# For demo, you can replace above default date with fetched listing date later

if st.button("Calculate and Plot"):
    try:
        # Step 1: Get Julian Day UT for listing date + 10 AM IST
        ist = pytz.timezone('Asia/Kolkata')
        jd_ut = get_julian_day(listing_date_input, DEFAULT_LISTING_TIME, ist)

        # Step 2: Get Moon longitude at listing
        moon_lon = get_moon_longitude(jd_ut)

        # Step 3: Calculate starting dasha index & balance
        dasha_start_idx = get_dasha_start_index(moon_lon)
        dasha_balance = get_dasha_balance(moon_lon)

        # Step 4: Build dasha periods
        dasha_periods = build_dasha_periods(dasha_start_idx, dasha_balance, jd_ut)

        # Step 5: Fetch stock price history
        ticker = yf.Ticker(symbol + ".NS")
        df = ticker.history(period="max")

        st.write(f"**Moon longitude at listing:** {moon_lon:.2f}°")
        st.write(f"**Starting Mahadasha:** {DASHA_NAMES[dasha_start_idx]} (Balance: {dasha_balance:.2%})")
        st.write("### Vimshottari Mahadasha Periods (approximate):")
        for name, start_rj, end_rj in dasha_periods:
            st.write(f"{name}: {revjul_to_date(start_rj)} to {revjul_to_date(end_rj)}")

        # Step 6: Plot price + dasha periods
        plot_price_with_dasha(df, dasha_periods)

    except Exception as e:
        st.error(f"Error: {e}")
