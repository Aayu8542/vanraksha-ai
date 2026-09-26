import yaml
import pandas as pd
import numpy as np

# A try-except for sklearn so the script doesn't completely fail if the user hasn't pip installed it yet
try:
    from sklearn.metrics import confusion_matrix
except ImportError:
    print("Warning: scikit-learn is not installed. Please run: pip install scikit-learn pandas numpy pyyaml")
    confusion_matrix = None

# Import custom modules
from goes_fetch import fetch_and_grid_goes_data
from firms_fetch import fetch_firms_data, label_grid
from scoring import fetch_gee_covariates, calculate_probability_score

def run_calibration_pipeline():
    """
    Main pipeline script.
    1. Loads config.
    2. Fetches GOES grid & thermal anomalies.
    3. Fetches FIRMS fire points & joins to grid (ground truth).
    4. Fetches GEE covariates (NDVI, Slope, Dryness).
    5. Calculates scores.
    6. Sweeps thresholds to generate a Precision/Recall evaluation.
    """
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    print("=== VanaRaksha AI: Stage 1 Calibration Pipeline ===")
    
    # 1. GOES Thermal Data
    df_grid = fetch_and_grid_goes_data(config)
    
    # 2. FIRMS Ground Truth
    df_firms = fetch_firms_data(config)
    df_labeled = label_grid(df_grid, df_firms, res_km=config['grid']['resolution_km'])
    
    # 3. GEE Covariates
    df_full = fetch_gee_covariates(df_labeled, config)
    
    # 4. Score Calculation
    df_scored = calculate_probability_score(df_full, config)
    
    # 5. Threshold Sweep & Evaluation
    print("\nSweeping threshold values against FIRMS ground truth...")
    
    if confusion_matrix is None:
        print("Skipping evaluation metrics due to missing scikit-learn.")
        return
        
    y_true = df_scored['is_fire_actual']
    y_scores = df_scored['prob_score']
    
    # Generate a range of possible thresholds
    thresholds_to_test = np.arange(0.1, 1.0, 0.1)
    
    results = []
    for t in thresholds_to_test:
        y_pred = (y_scores >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        far = fp / (fp + tn) if (fp + tn) > 0 else 0 # False Alarm Rate
        
        results.append({
            'Threshold': round(t, 2),
            'Precision': round(precision, 3),
            'Recall (Hit Rate)': round(recall, 3),
            'False Alarm Rate': round(far, 3),
            'True Positives': tp,
            'False Positives': fp,
            'False Negatives': fn
        })
        
    df_results = pd.DataFrame(results)
    print("\nCalibration Results:")
    print(df_results.to_string(index=False))
    
    # Save the report
    generate_markdown_report(df_results, df_scored, config)
    
def generate_markdown_report(df_results, df_scored, config):
    """Generates the calibration_report.md with summary statistics."""
    
    # Find mis-scored cells (High score but no actual fire, or Low score but actual fire)
    t_low = config['thresholds']['low_confidence']
    
    false_alarms = df_scored[(df_scored['prob_score'] >= t_low) & (df_scored['is_fire_actual'] == 0)]
    missed_fires = df_scored[(df_scored['prob_score'] < t_low) & (df_scored['is_fire_actual'] == 1)]
    
    report_content = f"""# VanaRaksha AI - Calibration Report
    
## Configuration Summary
- **Region:** {config['region']['name']}
- **Date Range:** {config['date_range']['start']} to {config['date_range']['end']}
- **Resolution:** {config['grid']['resolution_km']} km
- **Weights:**
  - Thermal Anomaly: {config['scoring_weights']['thermal_anomaly']}
  - NDVI (Dryness): {config['scoring_weights']['ndvi_dryness']}
  - Days Since Rain: {config['scoring_weights']['days_since_rain']}
  - Slope: {config['scoring_weights']['slope']}

## Threshold Sweep Analysis (Precision / Recall)
This table shows how different probability thresholds impact the detection rate (Recall) vs the False Alarm Rate. Use this to manually tune the Low/Medium/High cutoffs in `config.yaml`.

{df_results.to_markdown(index=False)}

## Mis-scored Cells (Sanity Check)
*Below is a sample of cells that were confidently scored but contradicted the FIRMS ground truth. Review these to see if weights need adjusting (e.g., highly reflective bare ground causing false thermal anomalies).*

### Sample False Alarms (Score >= {t_low}, No FIRMS Fire)
{false_alarms[['timestamp', 'lon', 'lat', 'thermal_anomaly', 'prob_score']].head(5).to_markdown(index=False)}

### Sample Missed Fires (Score < {t_low}, FIRMS Fire Confirmed)
{missed_fires[['timestamp', 'lon', 'lat', 'thermal_anomaly', 'prob_score']].head(5).to_markdown(index=False)}

"""

    with open("calibration_report.md", "w") as f:
        f.write(report_content)
        
    print("\nReport written to calibration_report.md")

if __name__ == "__main__":
    run_calibration_pipeline()
