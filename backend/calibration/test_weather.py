import requests

# Test coordinates around your region
lat, lng = 30.1234, 78.5678
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"

res = requests.get(url).json()
current = res.get("current", {})
print("Weather API Success!")
print(f"Wind Speed: {current.get('wind_speed_10m')} km/h")
print(f"Wind Direction: {current.get('wind_direction_10m')}°")
print(f"Relative Humidity: {current.get('relative_humidity_2m')}%")