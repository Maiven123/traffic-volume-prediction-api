import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Traffic Volume Predictor", layout="wide")

GOLD = "#D4AF37"
TEXT = "#EDEAE0"
MUTED = "#9AA0A6"
MAX_VOLUME = 7300

WEATHER_OPTIONS = [
    "Clear",
    "Clouds",
    "Drizzle",
    "Fog",
    "Haze",
    "Mist",
    "Rain",
    "Smoke",
    "Snow",
    "Squall",
    "Thunderstorm",
]

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@300;400;500;600&display=swap');

.stApp {
    background:
        radial-gradient(1100px 520px at 8% -8%, rgba(212,175,55,0.13) 0%, transparent 60%),
        radial-gradient(900px 480px at 100% 0%, rgba(120,90,20,0.10) 0%, transparent 55%),
        #0A0C10;
    color: #EDEAE0;
    font-family: 'Inter', sans-serif;
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2.2rem; max-width: 1200px; }

.hero { padding: 1.2rem 0 1.6rem 0; border-bottom: 1px solid rgba(212,175,55,0.25); margin-bottom: 1.8rem; }
.eyebrow { color: #D4AF37; letter-spacing: 0.32em; font-size: 0.72rem; font-weight: 600; margin-bottom: 0.6rem; }
.hero-title { font-family: 'Playfair Display', serif; font-size: 3rem; font-weight: 700; line-height: 1.1; margin: 0; color: #F4EFE2; }
.hero-title span { color: #D4AF37; }
.hero-sub { color: #9AA0A6; font-size: 1.02rem; max-width: 720px; margin-top: 0.9rem; line-height: 1.6; }

.panel-title { font-family: 'Playfair Display', serif; font-size: 1.35rem; color: #F4EFE2; margin: 0 0 0.2rem 0; }
.panel-rule { width: 46px; height: 2px; background: #D4AF37; margin: 0.35rem 0 1rem 0; border-radius: 2px; }

.level { display: inline-block; padding: 0.45rem 1.1rem; border: 1px solid; border-radius: 999px; font-weight: 600; letter-spacing: 0.06em; font-size: 0.88rem; text-transform: uppercase; }
.muted { color: #9AA0A6; font-size: 0.92rem; margin-top: 0.5rem; }
.placeholder { border: 1px dashed rgba(212,175,55,0.35); border-radius: 18px; padding: 3.5rem 2rem; text-align: center; color: #9AA0A6; background: rgba(255,255,255,0.02); }
.placeholder h3 { font-family: 'Playfair Display', serif; color: #D4AF37; margin-bottom: 0.6rem; }

.section-title { font-family: 'Playfair Display', serif; font-size: 1.7rem; color: #F4EFE2; margin: 2.6rem 0 0.2rem 0; }
.info-card { border: 1px solid rgba(212,175,55,0.22); border-radius: 18px; padding: 1.4rem 1.5rem; background: linear-gradient(160deg, rgba(255,255,255,0.045), rgba(255,255,255,0.01)); height: 100%; }
.info-card h4 { font-family: 'Playfair Display', serif; color: #D4AF37; margin: 0 0 0.6rem 0; font-size: 1.15rem; }
.info-card p { color: #C9C6BB; font-size: 0.93rem; line-height: 1.65; margin: 0; }
.footer-note { text-align: center; color: #6F747C; font-size: 0.82rem; margin: 3rem 0 1rem 0; letter-spacing: 0.04em; }

.stButton > button { width: 100%; border-radius: 12px; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #E6C36A, #B8902C);
    border: 0;
    padding: 0.75rem 1rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    box-shadow: 0 8px 24px rgba(212,175,55,0.22);
}
.stButton > button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color: #0A0C10 !important; font-weight: 600; }
div[data-testid="stMetric"] { background: rgba(255,255,255,0.03); border: 1px solid rgba(212,175,55,0.2); border-radius: 14px; padding: 0.9rem 1rem; }
div[data-testid="stMetricLabel"] p { color: #9AA0A6; }
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)


def default_api_url():
    try:
        return st.secrets["API_URL"]
    except Exception:
        return os.getenv("API_URL", "http://127.0.0.1:8000")


def call_predict(api_url, payload, timeout=90):
    try:
        response = requests.post(
            f"{api_url.rstrip('/')}/predict", json=payload, timeout=timeout
        )
    except requests.exceptions.Timeout:
        return None, "The server took too long to respond. Please try again in a moment."
    except requests.exceptions.ConnectionError:
        return None, (
            "Could not reach the API. Check the API URL in the sidebar "
            "and make sure the server is running."
        )
    except requests.exceptions.RequestException as exc:
        return None, f"Unexpected network error: {exc}"

    if response.status_code == 200:
        return response.json(), None

    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text
    return None, f"The API rejected the request (HTTP {response.status_code}): {detail}"


def fetch_profile(api_url, payload, chosen_date):
    def one_hour(hour):
        body = dict(payload)
        body["date_time"] = datetime.combine(chosen_date, time(hour)).isoformat()
        result, _ = call_predict(api_url, body, timeout=60)
        return None if result is None else result["predicted_traffic_volume"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(one_hour, range(24)))


def traffic_level(volume):
    if volume < 1500:
        return "Light traffic", "#4CAF82", "Roads are largely free-flowing."
    if volume < 3500:
        return "Moderate traffic", "#E6C36A", "Steady flow with occasional slowdowns."
    if volume < 5500:
        return "Heavy traffic", "#E08A3C", "Expect congestion, especially near peak hours."
    return "Severe traffic", "#D9534F", "Near-capacity flow, delays are likely."


def build_gauge(volume, color):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=volume,
            number={"font": {"color": GOLD, "size": 58}},
            title={"text": "vehicles per hour", "font": {"color": MUTED, "size": 15}},
            gauge={
                "axis": {"range": [0, MAX_VOLUME], "tickcolor": MUTED, "tickfont": {"color": MUTED}},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 1500], "color": "rgba(76,175,130,0.16)"},
                    {"range": [1500, 3500], "color": "rgba(230,195,106,0.16)"},
                    {"range": [3500, 5500], "color": "rgba(224,138,60,0.16)"},
                    {"range": [5500, MAX_VOLUME], "color": "rgba(217,83,79,0.16)"},
                ],
            },
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
    )
    return fig


def build_profile_chart(profile, selected_hour):
    hours = list(range(24))
    labels = [f"{h:02d}:00" for h in hours]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hours,
            y=profile,
            text=labels,
            mode="lines",
            line=dict(color=GOLD, width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(212,175,55,0.10)",
            hovertemplate="%{text}<br>%{y:,.0f} vehicles per hour<extra></extra>",
        )
    )
    if profile[selected_hour] is not None:
        fig.add_trace(
            go.Scatter(
                x=[selected_hour],
                y=[profile[selected_hour]],
                mode="markers",
                marker=dict(size=14, color=GOLD, line=dict(color="#0A0C10", width=3)),
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT),
        showlegend=False,
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(0, 24, 3)),
            ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)],
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Vehicles per hour",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
            rangemode="tozero",
        ),
    )
    return fig


with st.sidebar:
    st.markdown("### API connection")
    api_url = st.text_input("API URL", value=default_api_url())
    if st.button("Test connection"):
        try:
            health = requests.get(f"{api_url.rstrip('/')}/health", timeout=90)
            if health.status_code == 200:
                st.success("The API is online and healthy.")
            else:
                st.error(f"The API answered with HTTP {health.status_code}.")
        except requests.exceptions.RequestException:
            st.error("Could not reach the API.")
    st.caption(
        "Free hosting may put the API to sleep after inactivity. "
        "The first request can take up to a minute."
    )

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">MACHINE LEARNING PROJECT</div>
        <h1 class="hero-title">Interstate <span>Traffic Volume</span> Predictor</h1>
        <p class="hero-sub">
            Estimate hourly vehicle flow on a major interstate from the time of day,
            the calendar and the weather. Powered by a Random Forest model served
            through a FastAPI service.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.35], gap="large")

with left:
    st.markdown(
        '<div class="panel-title">Conditions</div><div class="panel-rule"></div>',
        unsafe_allow_html=True,
    )
    chosen_date = st.date_input("Date", value=date.today())
    chosen_time = st.time_input("Time", value=time(17, 0), step=3600)

    unit = st.radio("Temperature unit", ["Celsius", "Kelvin"], horizontal=True)
    if unit == "Celsius":
        celsius = st.slider("Temperature (C)", -30.0, 40.0, 15.0, 0.5)
        kelvin = celsius + 273.15
    else:
        kelvin = st.slider("Temperature (K)", 243.0, 313.0, 288.0, 0.5)

    weather = st.selectbox("Weather", WEATHER_OPTIONS, index=WEATHER_OPTIONS.index("Clouds"))
    clouds = st.slider("Cloud cover (%)", 0, 100, 40)

    rain_col, snow_col = st.columns(2)
    rain = rain_col.number_input("Rain, last hour (mm)", 0.0, 999.0, 0.0, 0.1)
    snow = snow_col.number_input("Snow, last hour (mm)", 0.0, 100.0, 0.0, 0.1)

    holiday_choice = st.selectbox("Public holiday", ["Detect automatically", "Yes", "No"])

    predict_clicked = st.button("Predict traffic volume", type="primary")

payload = {
    "date_time": datetime.combine(chosen_date, chosen_time).isoformat(),
    "temp": round(kelvin, 2),
    "rain_1h": float(rain),
    "snow_1h": float(snow),
    "clouds_all": int(clouds),
    "weather_main": weather,
}
if holiday_choice == "Yes":
    payload["is_holiday"] = 1
elif holiday_choice == "No":
    payload["is_holiday"] = 0

with right:
    st.markdown(
        '<div class="panel-title">Forecast</div><div class="panel-rule"></div>',
        unsafe_allow_html=True,
    )

    if predict_clicked:
        with st.spinner(
            "Contacting the prediction service. The first request may take up to "
            "a minute while the server wakes up."
        ):
            result, error = call_predict(api_url, payload)
            profile = fetch_profile(api_url, payload, chosen_date) if result else None
        if error:
            st.session_state["error"] = error
            st.session_state.pop("result", None)
        else:
            st.session_state.pop("error", None)
            st.session_state["result"] = {
                "volume": result["predicted_traffic_volume"],
                "features": result["features_used"],
                "profile": profile,
                "hour": chosen_time.hour,
            }

    if "error" in st.session_state:
        st.error(st.session_state["error"])
    elif "result" in st.session_state:
        saved = st.session_state["result"]
        volume = saved["volume"]
        label, color, message = traffic_level(volume)

        st.plotly_chart(build_gauge(volume, color))
        st.markdown(
            f'<div class="level" style="border-color:{color};color:{color}">{label}</div>'
            f'<p class="muted">{message} Typical model error is about 250 vehicles per hour.</p>',
            unsafe_allow_html=True,
        )

        profile = saved["profile"]
        if profile and any(v is not None for v in profile):
            st.markdown(
                '<div class="panel-title" style="margin-top:1.6rem">The whole day</div>'
                '<div class="panel-rule"></div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(build_profile_chart(profile, saved["hour"]))
            st.caption("The same weather conditions are applied to every hour of the selected date.")

            valid = [(h, v) for h, v in enumerate(profile) if v is not None]
            peak = max(valid, key=lambda item: item[1])
            quiet = min(valid, key=lambda item: item[1])
            m1, m2, m3 = st.columns(3)
            m1.metric("Selected hour", f"{saved['hour']:02d}:00")
            m2.metric("Peak hour", f"{peak[0]:02d}:00", f"{peak[1]:,} per hour", delta_color="off")
            m3.metric("Quietest hour", f"{quiet[0]:02d}:00", f"{quiet[1]:,} per hour", delta_color="off")

        with st.expander("Features sent to the model"):
            st.json(saved["features"])
        st.caption("Traffic levels are illustrative bands chosen for readability.")
    else:
        st.markdown(
            '<div class="placeholder"><h3>Ready when you are</h3>'
            "Set the conditions on the left and press Predict to see the expected "
            "traffic volume and how it evolves across the day.</div>",
            unsafe_allow_html=True,
        )

st.markdown('<div class="section-title">Behind the prediction</div><div class="panel-rule"></div>', unsafe_allow_html=True)

cards = [
    (
        "The data",
        "Hourly vehicle counts for Interstate 94 westbound, between Minneapolis and "
        "St. Paul, joined with weather and holiday information from 2012 to 2018.",
    ),
    (
        "The model",
        "A Random Forest of 200 trees trained on time, weather and holiday features. "
        "Training, validation and test sets follow chronological order, so the model "
        "is always evaluated on the future.",
    ),
    (
        "The accuracy",
        "On the held-out test period the model reaches an R2 of 0.96 with a mean "
        "absolute error of about 250 vehicles per hour.",
    ),
]
for column, (title, body) in zip(st.columns(3, gap="large"), cards):
    column.markdown(
        f'<div class="info-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="footer-note">Built with scikit-learn, FastAPI and Streamlit</div>',
    unsafe_allow_html=True,
)
