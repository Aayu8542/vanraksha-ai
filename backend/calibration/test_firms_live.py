import os
import requests

# Replace with your NASA FIRMS MAP_KEY
MAP_KEY = "YOUR_FIRMS_MAP_KEY"

# Test area: [west, south, east, north] (e.g. around 30.1N, 78.5E)
# Format for FIRMS API: /api/area/csv/[MAP_KEY]/[SOURCE]/[W,S,E,N]/[DAY_RANGE]
coords = "78.4,30.0,78.6,30.2"
source = "VIIRS_SNPP_NRT"
day_range = "5" # look back 5 days

url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{coords}/{day_range}"

response = requests.get(url)
print("FIRMS Status Code:", response.status_code)
print("Sample Response:")
print("\n".join(response.text.splitlines()[:5]))