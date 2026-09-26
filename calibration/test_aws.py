import boto3
from botocore import UNSIGNED
from botocore.config import Config

try:
    # Create an anonymous S3 client
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    # Try listing 5 files from the public GOES-16 bucket
    response = s3.list_objects_v2(Bucket='noaa-goes16', MaxKeys=5)

    print("✅ AWS Verification Successful!")
    print("Found files in NOAA GOES Bucket:")
    for obj in response.get('Contents', []):
        print(" -", obj['Key'])

except Exception as e:
    print("❌ AWS Verification Failed:")
    print(e)