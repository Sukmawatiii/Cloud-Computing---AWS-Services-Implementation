"""Tes lokal kedua Lambda memakai moto (S3 palsu). Jalankan: pytest -q"""
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))
os.environ.update(AWS_DEFAULT_REGION="us-east-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
                  BUCKET_NAME="loans-test", ADMIN_KEY="rahasia")


def ev(method, path, body=None, key="rahasia"):
    headers = {"x-admin-key": key} if key else {}
    return {"requestContext": {"http": {"method": method}}, "rawPath": path, "headers": headers,
            "body": json.dumps(body) if body is not None else None}


@pytest.fixture
def lambdas():
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket="loans-test")
        import admin, viewer
        yield viewer.lambda_handler, admin.lambda_handler


def test_health(lambdas):
    viewer, admin = lambdas
    assert json.loads(viewer(ev("GET", "/health", key=None), None)["body"])["storage"] is True
    assert admin(ev("GET", "/health", key=None), None)["statusCode"] == 200


def test_full_crud_flow(lambdas):
    viewer, admin = lambdas
    r = admin(ev("POST", "/loans", {"item_name": "Proyektor", "borrower_name": "Sukma"}), None)
    assert r["statusCode"] == 201
    loan = json.loads(r["body"])
    loan_id = loan["loan_id"]
    assert loan["status"] == "BORROWED"
    assert admin(ev("POST", "/loans", {}), None)["statusCode"] == 400

    # viewer membaca data yang ditulis admin (bucket yang sama)
    listed = json.loads(viewer(ev("GET", "/loans", key=None), None)["body"])
    assert [x["loan_id"] for x in listed] == [loan_id]

    r = admin(ev("PUT", f"/loans/{loan_id}", {"status": "RETURNED"}), None)
    body = json.loads(r["body"])
    assert r["statusCode"] == 200 and body["status"] == "RETURNED" and body["return_date"]
    assert admin(ev("PUT", f"/loans/{loan_id}", {"status": "XXX"}), None)["statusCode"] == 400
    assert admin(ev("PUT", f"/loans/{loan_id}", {}), None)["statusCode"] == 400
    missing_id = "00000000-0000-0000-0000-000000000000"
    assert admin(ev("PUT", f"/loans/{missing_id}", {"status": "RETURNED"}), None)["statusCode"] == 404

    assert admin(ev("DELETE", f"/loans/{loan_id}"), None)["statusCode"] == 200
    assert admin(ev("DELETE", f"/loans/{loan_id}"), None)["statusCode"] == 404
    assert json.loads(viewer(ev("GET", "/loans", key=None), None)["body"]) == []


def test_admin_requires_key_and_viewer_is_readonly(lambdas):
    viewer, admin = lambdas
    assert admin(ev("POST", "/loans", {"item_name": "a", "borrower_name": "b"}, key=None), None)["statusCode"] == 401
    assert admin(ev("DELETE", "/loans/x", key="salah"), None)["statusCode"] == 401
    assert viewer(ev("POST", "/loans", {"item_name": "a"}, key=None), None)["statusCode"] == 405


def test_bad_id_is_rejected_not_used_as_key(lambdas):
    _, admin = lambdas
    assert admin(ev("DELETE", "/loans/..%2Fsecret"), None)["statusCode"] == 404
