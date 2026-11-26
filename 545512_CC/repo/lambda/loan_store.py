"""Lapisan penyimpanan bersama: satu objek JSON di S3 = satu peminjaman.

Dipakai oleh dua Lambda (loan-viewer dan loan-admin), dikemas di dalam zip masing-masing.
Key objek: loans/<loan_id>.json
"""
import json
import os
import re

import boto3
from botocore.exceptions import ClientError

PREFIX = "loans/"
ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _s3():
    return boto3.client("s3")


def _bucket():
    return os.environ["BUCKET_NAME"]


def _key(loan_id):
    return f"{PREFIX}{loan_id}.json"


def valid_id(loan_id):
    """Cegah path aneh (mis. ../) masuk ke key S3."""
    return bool(loan_id) and bool(ID_PATTERN.match(loan_id))


def ping():
    _s3().head_bucket(Bucket=_bucket())
    return True


def list_loans():
    s3, items = _s3(), []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=_bucket(), Prefix=PREFIX):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=_bucket(), Key=obj["Key"])["Body"].read()
            items.append(json.loads(body))
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_loan(loan_id):
    try:
        body = _s3().get_object(Bucket=_bucket(), Key=_key(loan_id))["Body"].read()
    except ClientError as err:
        if err.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
    return json.loads(body)


def save_loan(item):
    _s3().put_object(
        Bucket=_bucket(),
        Key=_key(item["loan_id"]),
        Body=json.dumps(item).encode("utf-8"),
        ContentType="application/json",
    )
    return item


def delete_loan(loan_id):
    """Return True jika terhapus, False jika memang tidak ada (S3 delete biasa tidak memberi tahu)."""
    s3 = _s3()
    try:
        s3.head_object(Bucket=_bucket(), Key=_key(loan_id))
    except ClientError as err:
        if err.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise
    s3.delete_object(Bucket=_bucket(), Key=_key(loan_id))
    return True


def respond(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body)}


def request_info(event):
    """Ambil method dan path dari event Lambda Function URL (payload v2)."""
    http = event.get("requestContext", {}).get("http", {})
    return http.get("method", ""), (event.get("rawPath") or "/")
