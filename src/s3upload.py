import boto3
import os
import shutil

_session = None

def _createSession():
    global _session
    if _session == None:
        _session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_S3_REGION"),
        )
    return _session


def upload(filePath, filename):

    if os.getenv("ENVIRONMENT") != "development":
        # Create an S3 client
        s3 = _createSession().client("s3")

        # Upload a file to an S3 bucket
        return s3.upload_file(filePath, os.getenv("BUCKET_NAME"), filename)

    local_path = (
        os.getenv("DEV_UPLOAD_PATH") + "/" + os.getenv("BUCKET_NAME") + "/" + filePath
    )

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    shutil.copy2(filePath, local_path)
