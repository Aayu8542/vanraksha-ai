import pandas as pd
import numpy as np

def fetch_gee_covariates(df_grid, config):
    """
    Pulls NDVI, slope (SRTM DEM), and simple dryness index (CHIRPS) per grid cell.
    Requires Google Earth Engine (ee) API. 
    """
    print("Fetching NDVI, Slope, and Dryness covariates from Earth Engine...")
    
    # In a real implementation:
    # 1. import ee; ee.Initialize()
    # 2. Extract ee.Image('USGS/SRTMGL1_003').select('elevation').slope()
    # 3. Extract ee.ImageCollection('MODIS/061/MOD13Q1').select('NDVI')
    # 4. Extract ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") for dryness
    
    # MOCK IMPLEMENTATION:
    # Assign normalized values (0 to 1) for these environmental factors.
    df_grid['ndvi_dryness'] = np.random.uniform(0, 1, len(df_grid))  # 1.0 = highly dry/low NDVI
    df_grid['slope_norm'] = np.random.uniform(0, 1, len(df_grid))    # 1.0 = steep slope
    df_grid['days_since_rain_norm'] = np.random.uniform(0, 1, len(df_grid)) # 1.0 = many days without rain
    
    return df_grid


def calculate_probability_score(df, config):
    """
    Combines the environmental covariates with the thermal anomaly value 
    into a single weighted probability score based on configured weights.
    
    FORMULA:
    Probability = (W_thermal * Thermal_Anomaly) + 
                  (W_ndvi * NDVI_Dryness) + 
                  (W_rain * Days_Since_Rain) + 
                  (W_slope * Slope)
    """
    w = config['scoring_weights']
    
    print(f"Calculating probability scores using weights: {w}")
    
    df['prob_score'] = (
        (df['thermal_anomaly'] * w['thermal_anomaly']) +
        (df['ndvi_dryness'] * w['ndvi_dryness']) +
        (df['days_since_rain_norm'] * w['days_since_rain']) +
        (df['slope_norm'] * w['slope'])
    )
    
    # Cap at 1.0
    df['prob_score'] = df['prob_score'].clip(upper=1.0)
    
    # Assign confidence bands based on thresholds
    t = config['thresholds']
    
    conditions = [
        (df['prob_score'] >= t['high_confidence']),
        (df['prob_score'] >= t['medium_confidence']),
        (df['prob_score'] >= t['low_confidence'])
    ]
    choices = ['High', 'Medium', 'Low']
    df['confidence_band'] = np.select(conditions, choices, default='None')
    
    return df
