import ee

try:
    # Use your exact Project ID
    ee.Initialize(project='vanraksha-ai-27380')

    dem = ee.Image('USGS/SRTMGL1_003')
    print("✅ Google Earth Engine Verification Successful!")
    print("Dataset ID retrieved:", dem.getInfo()['id'])

except Exception as e:
    print("❌ GEE Verification Failed:")
    print(e)

import ee

try:
    ee.Initialize(project='vanraksha-ai-27380')

    # Load ESA WorldCover
    worldcover = ee.ImageCollection("ESA/WorldCover/v100").first()
    
    print("✅ Google Earth Engine Verification Successful!")
    print("Dataset ID:", worldcover.get('system:id').getInfo())
    print("Bands Available:", worldcover.bandNames().getInfo())

except Exception as e:
    print("❌ Verification Failed:", e)