# VanaRaksha AI - Calibration Report
    
## Configuration Summary
- **Region:** Odisha
- **Date Range:** 2023-03-01 to 2023-06-30
- **Resolution:** 4.0 km
- **Weights:**
  - Thermal Anomaly: 0.5
  - NDVI (Dryness): 0.2
  - Days Since Rain: 0.2
  - Slope: 0.1

## Threshold Sweep Analysis (Precision / Recall)
This table shows how different probability thresholds impact the detection rate (Recall) vs the False Alarm Rate. Use this to manually tune the Low/Medium/High cutoffs in `config.yaml`.

|   Threshold |   Precision |   Recall (Hit Rate) |   False Alarm Rate |   True Positives |   False Positives |   False Negatives |
|------------:|------------:|--------------------:|-------------------:|-----------------:|------------------:|------------------:|
|         0.1 |       0.05  |               1     |              0.991 |                6 |               113 |                 0 |
|         0.2 |       0.04  |               0.667 |              0.833 |                4 |                95 |                 2 |
|         0.3 |       0.048 |               0.5   |              0.518 |                3 |                59 |                 3 |
|         0.4 |       0.04  |               0.167 |              0.211 |                1 |                24 |                 5 |
|         0.5 |       0     |               0     |              0.096 |                0 |                11 |                 6 |
|         0.6 |       0     |               0     |              0.026 |                0 |                 3 |                 6 |
|         0.7 |       0     |               0     |              0.009 |                0 |                 1 |                 6 |
|         0.8 |       0     |               0     |              0     |                0 |                 0 |                 6 |
|         0.9 |       0     |               0     |              0     |                0 |                 0 |                 6 |

## Mis-scored Cells (Sanity Check)
*Below is a sample of cells that were confidently scored but contradicted the FIRMS ground truth. Review these to see if weights need adjusting (e.g., highly reflective bare ground causing false thermal anomalies).*

### Sample False Alarms (Score >= 0.6, No FIRMS Fire)
| timestamp           |     lon |     lat |   thermal_anomaly |   prob_score |
|:--------------------|--------:|--------:|------------------:|-------------:|
| 2023-04-22 02:00:00 | 84.4712 | 22.4207 |          0.441323 |     0.646042 |
| 2023-06-13 04:00:00 | 82.3811 | 21.7    |          0.885788 |     0.73465  |
| 2023-06-23 14:00:00 | 81.5162 | 22.4928 |          0.696827 |     0.616543 |

### Sample Missed Fires (Score < 0.6, FIRMS Fire Confirmed)
| timestamp           |     lon |     lat |   thermal_anomaly |   prob_score |
|:--------------------|--------:|--------:|------------------:|-------------:|
| 2023-03-11 10:00:00 | 82.6333 | 18.6369 |       0.0126419   |     0.329895 |
| 2023-04-22 02:00:00 | 84.1829 | 20.7631 |       0.0286736   |     0.153795 |
| 2023-06-02 18:00:00 | 87.4261 | 22.0604 |       0.0390043   |     0.192129 |
| 2023-06-02 18:00:00 | 86.2369 | 22.3126 |       9.43797e-06 |     0.273089 |
| 2023-06-13 04:00:00 | 85.336  | 21.3396 |       0.348919    |     0.490656 |

