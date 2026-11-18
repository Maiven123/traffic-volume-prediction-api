# Traffic Volume Prediction API

A REST API built with FastAPI that predicts hourly traffic volume on an interstate highway using a Random Forest regressor trained on the Metro Interstate Traffic Volume dataset.

## Model

- Algorithm: Random Forest Regressor (scikit-learn)
- Split: chronological, 70% train, 15% validation, 15% test
- Test performance: R2 = 0.96, MAE = approximately 250 vehicles per hour

## Features

The API builds these features from the request:

| Feature | Source |
| --- | --- |
| temp, rain_1h, snow_1h, clouds_all | Request body |
| weather_main | Request body, label-encoded |
| hour, dayofweek, month | Derived from date_time |
| is_weekend | Derived from date_time |
| is_holiday | Request body, or looked up from the holiday dates seen during training |

## Project Structure

```
.
|-- api/
|   |-- main.py
|   |-- Final_model.pkl
|   |-- model_scaler.pkl
|   `-- requirements.txt
|-- streamlit_app/
|   |-- app.py
|   `-- requirements.txt
|-- .streamlit/
|   `-- config.toml
`-- README.md
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r api/requirements.txt
uvicorn main:app --reload --app-dir api
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

Open http://127.0.0.1:8000/docs to try the API in the browser.

## Endpoints

### GET /health

Returns `{"status": "healthy"}`.

### POST /predict

Request:

```json
{
  "date_time": "2018-09-30T17:00:00",
  "temp": 288.28,
  "rain_1h": 0,
  "snow_1h": 0,
  "clouds_all": 40,
  "weather_main": "Clouds",
  "is_holiday": 0
}
```

Response:

```json
{
  "predicted_traffic_volume": 3000,
  "unit": "vehicles per hour",
  "features_used": {}
}
```

The values above are illustrative. The `features_used` object lists the encoded features sent to the model.

### Input rules

| Field | Rule |
| --- | --- |
| date_time | ISO 8601 datetime |
| temp | Kelvin, greater than 0 |
| rain_1h | Millimeters, 0 or more, below 1000 |
| snow_1h | Millimeters, 0 or more |
| clouds_all | Integer from 0 to 100 |
| weather_main | One of: Clear, Clouds, Drizzle, Fog, Haze, Mist, Rain, Smoke, Snow, Squall, Thunderstorm |
| is_holiday | Optional, 0 or 1 |

Invalid input returns HTTP 422 with a description of the problem.

## Web App

A Streamlit interface in `streamlit_app/` sends the inputs to the API and displays the prediction, a traffic level gauge, and a 24-hour profile for the selected date.

```bash
uvicorn main:app --reload --app-dir api
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

The app reads the API address from the `API_URL` environment variable or from a Streamlit secret named `API_URL`. It defaults to `http://127.0.0.1:8000`.

## Deployment

The service runs on Render with:

- Root directory: `api`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variable: `PYTHON_VERSION=3.12.8`

The scikit-learn version in `requirements.txt` must match the version used to train the model, because the model is stored as a pickle file.
