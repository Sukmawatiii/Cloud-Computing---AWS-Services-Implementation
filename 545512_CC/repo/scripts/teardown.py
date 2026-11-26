"""Hapus semua yang dibuat deploy.py (Lambda, Function URL, bucket S3 beserta isinya)."""
import pathlib

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
OUT = pathlib.Path(__file__).resolve().parent.parent / "deploy_output.json"

session = boto3.Session(region_name=REGION)
account = session.client("sts").get_caller_identity()["Account"]
bucket = f"loans-demo-{account}"
lam, s3 = session.client("lambda"), session.client("s3")

for name in ("loan-viewer", "loan-admin"):
    try:
        lam.delete_function_url_config(FunctionName=name)
    except ClientError:
        pass
    try:
        lam.delete_function(FunctionName=name)
        print("dihapus: Lambda", name)
    except ClientError as exc:
        print("lewati:", name, exc.response["Error"]["Code"])

try:
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objs:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
    s3.delete_bucket(Bucket=bucket)
    print("dihapus: bucket", bucket)
except ClientError as exc:
    print("lewati bucket:", exc.response["Error"]["Code"])

OUT.unlink(missing_ok=True)
