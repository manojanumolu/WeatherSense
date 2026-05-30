# WeatherSense 🌤️

A live animated weather dashboard powered by OpenWeatherMap.

## Local Setup

1. Get a free API key at https://openweathermap.org/api
2. Create `.streamlit/secrets.toml` and add:
   ```
   OWM_API_KEY = "your_key_here"
   ```
3. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to https://share.streamlit.io → **New app** → select this repo → main file: `app.py`
3. In **Advanced settings → Secrets** add:
   ```
   OWM_API_KEY = "your_key_here"
   ```
4. Click **Deploy**

Your app will be live at:
`https://share.streamlit.io/YOUR_USERNAME/WeatherSense/main/app.py`
