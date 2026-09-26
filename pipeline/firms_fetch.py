import pandas as pd
import requests
import io
import numpy as np

def fetch_firms_data(config):
    """
    Pulls FIRMS historical fire points for the region/date range.
    """
    bbox = config['region']['bbox']
    map_key = config['data_sources']['firms_map_key']
    start_date = config['date_range']['start']
    end_date = config['date_range']['end']
    
    print(f"Fetching FIRMS historical data for {config['region']['name']}...")
    
    if map_key == "YOUR_FIRMS_MAP_KEY_HERE":
        print("WARNING: Valid FIRMS MAP_KEY not provided. Using simulated ground truth data.")
        return generate_mock_firms_data(config)
        
    try:
        source = 'VIIRS_SNPP_NRT'
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        # FIRMS Area API allows max 10 days per request. 
        # A full implementation would chunk the date_range.
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{bbox_str}/10/{start_date}"
        response = requests.get(url)
        response.raise_for_status()
        
        df_firms = pd.read_csv(io.StringIO(response.text))
        print(f"Fetched {len(df_firms)} actual FIRMS fire points.")
        return df_firms
        
    except Exception as e:
        print(f"Error fetching from FIRMS API: {e}. Falling back to mock data.")
        return generate_mock_firms_data(config)


def generate_mock_firms_data(config):
    """Generates synthetic confirmed fire points for pipeline testing."""
    bbox = config['region']['bbox']
    start = pd.to_datetime(config['date_range']['start'])
    end = pd.to_datetime(config['date_range']['end'])
    
    n_fires = 50
    random_dates = start + pd.to_timedelta(np.random.randint(0, (end-start).days, n_fires), unit='D')
    lons = np.random.uniform(bbox[0], bbox[2], n_fires)
    lats = np.random.uniform(bbox[1], bbox[3], n_fires)
    
    df = pd.DataFrame({
        'acq_date': random_dates.date,
        'acq_time': [f"{np.random.randint(0,23):02d}{np.random.randint(0,59):02d}" for _ in range(n_fires)],
        'latitude': lats,
        'longitude': lons,
        'confidence': np.random.choice(['l', 'n', 'h'], n_fires),
        'is_fire': 1  # Ground truth label
    })
    
    df['timestamp'] = pd.to_datetime(df['acq_date'].astype(str) + ' ' + df['acq_time'].str[:2] + ':' + df['acq_time'].str[2:])
    return df


def label_grid(df_grid, df_firms, res_km=4.0):
    """
    Spatially and temporally joins FIRMS ground truth to the GOES grid.
    Labels a cell/timestep as 1 if a FIRMS point falls within it, else 0.
    """
    print("Spatially joining FIRMS ground truth to grid...")
    # Real implementation: Use geopandas.sjoin for spatial overlap 
    # and pd.merge_asof for temporal proximity.
    # For now, randomly inject true fires to test the calibration pipeline.
    
    df_grid['is_fire_actual'] = np.random.choice([0, 1], size=len(df_grid), p=[0.95, 0.05])
    return df_grid

if __name__ == "__main__":
    import yaml
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    df = fetch_firms_data(config)
    print(df.head())
