"""Bangun seluruh infrastruktur dengan SATU perintah (aman dijalankan berulang kali).

    python3 scripts/deploy.py

Membuat: bucket S3, Lambda loan-viewer + loan-admin (role LabRole), dan Lambda Function URL untuk keduanya.
Hasil (URL dan admin key) disimpan di deploy_output.json (JANGAN di-commit).
Jalankan dari VS Code Lab IDE atau CloudShell di sandbox (kredensial sudah terpasang).
"""
import io
import json
import pathlib
import secrets
import sys
import zipfile

import boto3
from botocore.exceptions import ClientError, ParamValidationError

REGION = "us-east-1"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "deploy_output.json"
FUNCTIONS = {"loan-viewer": "viewer", "loan-admin": "admin"}  # nama fungsi -> file handler


def step(msg):
    print(f"\n>> {msg}")


def ok(msg):
    print(f"   OK  {msg}")


def fail(msg, exc):
    print(f"   GAGAL  {msg}\n   Detail: {exc}")
    print("   Jalankan 'python3 scripts/teardown.py' untuk membersihkan, lalu kirim pesan di atas ke asisten/dosen.")
    sys.exit(1)


def build_zip(handler_file):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / "lambda" / f"{handler_file}.py", f"{handler_file}.py")
        z.write(ROOT / "lambda" / "loan_store.py", "loan_store.py")
    return buf.getvalue()


def main():
    session = boto3.Session(region_name=REGION)
    account = session.client("sts").get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account}:role/LabRole"
    bucket = f"loans-demo-{account}"
    s3, lam = session.client("s3"), session.client("lambda")
    previous = json.loads(OUT.read_text()) if OUT.exists() else {}
    admin_key = previous.get("admin_key") or secrets.token_urlsafe(16)

    # 1. S3
    step(f"S3: bucket {bucket}")
    try:
        try:
            s3.head_bucket(Bucket=bucket)
            ok("bucket sudah ada")
        except ClientError:
            s3.create_bucket(Bucket=bucket)  # us-east-1 tidak butuh LocationConstraint
            ok("bucket dibuat")
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={k: True for k in (
                "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")},
        )
        ok("Block Public Access aktif")
    except ClientError as exc:
        fail("S3 ditolak", exc)

    urls = {}
    for name, handler in FUNCTIONS.items():
        env = {"Variables": {"BUCKET_NAME": bucket}}
        if handler == "admin":
            env["Variables"]["ADMIN_KEY"] = admin_key

        # 2. Lambda
        step(f"Lambda: {name}")
        code = build_zip(handler)
        try:
            try:
                lam.create_function(
                    FunctionName=name, Runtime="python3.12", Role=role_arn, Handler=f"{handler}.lambda_handler",
                    Code={"ZipFile": code}, Timeout=10, MemorySize=128, Environment=env,
                )
                ok("fungsi dibuat")
            except lam.exceptions.ResourceConflictException:
                lam.update_function_code(FunctionName=name, ZipFile=code)
                lam.get_waiter("function_updated_v2").wait(FunctionName=name)
                lam.update_function_configuration(FunctionName=name, Environment=env)
                ok("fungsi sudah ada, kode dan konfigurasi diperbarui")
            lam.get_waiter("function_active_v2").wait(FunctionName=name)
            lam.get_waiter("function_updated_v2").wait(FunctionName=name)
        except ClientError as exc:
            fail(f"Lambda {name} ditolak (cek role LabRole)", exc)

        # 3. Function URL (pengganti API Gateway)
        step(f"Function URL: {name}")
        try:
            try:
                cfg = lam.get_function_url_config(FunctionName=name)
                ok("URL sudah ada")
            except lam.exceptions.ResourceNotFoundException:
                cfg = lam.create_function_url_config(FunctionName=name, AuthType="NONE")
                ok("URL dibuat")
            urls[name] = cfg["FunctionUrl"].rstrip("/")

            # Auth NONE butuh dua izin publik (aturan AWS sejak Okt 2025)
            for sid, kwargs in (
                ("PublicInvokeUrl", dict(Action="lambda:InvokeFunctionUrl", FunctionUrlAuthType="NONE")),
                ("PublicInvokeFunction", dict(Action="lambda:InvokeFunction", InvokedViaFunctionUrl=True)),
            ):
                try:
                    lam.add_permission(FunctionName=name, StatementId=sid, Principal="*", **kwargs)
                    ok(f"izin {kwargs['Action']} ditambahkan")
                except lam.exceptions.ResourceConflictException:
                    ok(f"izin {kwargs['Action']} sudah ada")
                except ParamValidationError:
                    # boto3 versi lama belum mengenal InvokedViaFunctionUrl
                    kwargs.pop("InvokedViaFunctionUrl", None)
                    lam.add_permission(FunctionName=name, StatementId=sid, Principal="*", **kwargs)
                    print("   CATATAN boto3 lama: izin InvokeFunction dipasang tanpa batasan 'via Function URL'")
        except ClientError as exc:
            fail(f"Function URL {name} ditolak", exc)

    OUT.write_text(json.dumps({
        "region": REGION, "bucket": bucket, "admin_key": admin_key,
        "viewer_url": urls["loan-viewer"], "admin_url": urls["loan-admin"],
    }, indent=2))

    print("\n==================== SELESAI ====================")
    print(f"Bucket S3  : {bucket}")
    print(f"Viewer URL : {urls['loan-viewer']}")
    print(f"Admin URL  : {urls['loan-admin']}")
    print(f"Admin key  : {admin_key}   (header: x-admin-key)")
    print("Detail tersimpan di deploy_output.json. Tes cepat: python3 scripts/demo.py --auto")


if __name__ == "__main__":
    main()
