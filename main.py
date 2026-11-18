from datetime import datetime
from pathlib import Path
from typing import Optional
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_WEATHER_CLASSES = [
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

model = joblib.load(BASE_DIR / "Final_model.pkl")
artifacts = joblib.load(BASE_DIR / "model_scaler.pkl")

model.n_jobs = 1
scaler = artifacts.get("scaler")
FEATURE_COLUMNS = list(artifacts["feature_columns"])
HOLIDAY_DATES = {str(d) for d in artifacts.get("holiday_dates", [])}

encoder_classes = list(getattr(artifacts.get("weather_encoder"), "classes_", []))
if encoder_classes and all(isinstance(c, str) for c in encoder_classes):
    WEATHER_OPTIONS = encoder_classes
else:
    WEATHER_OPTIONS = DEFAULT_WEATHER_CLASSES

WEATHER_CODES = {name: index for index, name in enumerate(WEATHER_OPTIONS)}
WEATHER_LOOKUP = {name.lower(): name for name in WEATHER_OPTIONS}

app = FastAPI(
    title="Traffic Volume Prediction API",
    version="1.0.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)


class TrafficInput(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date_time": "2018-09-30T17:00:00",
                    "temp": 288,
                    "rain_1h": 0,
                    "snow_1h": 0,
                    "clouds_all": 40,
                    "weather_main": "Clouds",
                    "is_holiday": 0,
                }
            ]
        }
    }

    date_time: datetime
    temp: float = Field(..., gt=0)
    rain_1h: float = Field(0, ge=0, lt=1000)
    snow_1h: float = Field(0, ge=0)
    clouds_all: int = Field(..., ge=0, le=100)
    weather_main: str
    is_holiday: Optional[int] = Field(None, ge=0, le=1)


def build_features(data: TrafficInput) -> pd.DataFrame:
    weather_name = WEATHER_LOOKUP.get(data.weather_main.strip().lower())
    if weather_name is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown weather_main. Allowed values: {WEATHER_OPTIONS}",
        )

    dt = data.date_time
    is_holiday = data.is_holiday
    if is_holiday is None:
        is_holiday = int(dt.date().isoformat() in HOLIDAY_DATES)

    row = {
        "temp": data.temp,
        "rain_1h": data.rain_1h,
        "snow_1h": data.snow_1h,
        "clouds_all": data.clouds_all,
        "weather_main": WEATHER_CODES[weather_name],
        "hour": dt.hour,
        "dayofweek": dt.weekday(),
        "month": dt.month,
        "is_weekend": int(dt.weekday() >= 5),
        "is_holiday": int(is_holiday),
    }

    X = pd.DataFrame([row]).reindex(columns=FEATURE_COLUMNS)
    if scaler is not None:
        X = pd.DataFrame(scaler.transform(X), columns=FEATURE_COLUMNS)
    return X


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/predict")
def predict(data: TrafficInput):
    X = build_features(data)
    prediction = float(model.predict(X)[0])
    return {
        "predicted_traffic_volume": max(0, round(prediction)),
        "unit": "vehicles per hour",
        "features_used": {k: float(v) for k, v in X.iloc[0].to_dict().items()},
    }
