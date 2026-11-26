"""Skrip demo untuk rekaman video: menjalankan alur CRUD lengkap dan menampilkan hasilnya.

    python3 scripts/demo.py          # berhenti tiap langkah, tekan Enter (enak untuk narasi)
    python3 scripts/demo.py --auto   # jalan tanpa berhenti
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

import boto3

cfg = json.loads((pathlib.Path(__file__).resolve().parent.parent / "deploy_output.json").read_text())
AUTO = "--auto" in sys.argv
n = 0


def step(title):
    global n
    n += 1
    if not AUTO and n > 1:
        input("\n[Enter untuk lanjut] ")
    print(f"\n{'=' * 64}\nLANGKAH {n}: {title}\n{'=' * 64}")


def call(method, url, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["x-admin-key"] = key
    data = json.dumps(body).encode() if body is not None else None
    print(f"$ {method} {url.replace(cfg['viewer_url'], '<VIEWER>').replace(cfg['admin_url'], '<ADMIN>')}"
          + (f"   body={json.dumps(body)}" if body else "") + ("   [x-admin-key: ****]" if key else ""))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method)) as r:
            code, text = r.status, r.read().decode()
    except urllib.error.HTTPError as err:
        code, text = err.code, err.read().decode()
    print(f"HTTP {code}")
    parsed = json.loads(text)
    print(json.dumps(parsed, indent=2))
    return parsed


V, A, K = cfg["viewer_url"], cfg["admin_url"], cfg["admin_key"]

step("Health check kedua Lambda (membuktikan akses ke S3)")
call("GET", f"{V}/health")
call("GET", f"{A}/health")

step("CREATE: admin menambah dua peminjaman (POST /loans)")
first = call("POST", f"{A}/loans", {"item_name": "Proyektor Epson", "borrower_name": "Sukmawati"}, K)
second = call("POST", f"{A}/loans", {"item_name": "Kabel HDMI 5m", "borrower_name": "Budi"}, K)

step("READ: viewer membaca daftar (GET /loans), tanpa kunci")
call("GET", f"{V}/loans")

step("UPDATE: admin menandai proyektor sudah dikembalikan (PUT /loans/{id})")
call("PUT", f"{A}/loans/{first['loan_id']}", {"status": "RETURNED"}, K)

step("KEAMANAN: tulis tanpa x-admin-key ditolak (401), viewer tidak punya route tulis (405)")
call("POST", f"{A}/loans", {"item_name": "x", "borrower_name": "y"})
call("POST", f"{V}/loans", {"item_name": "x", "borrower_name": "y"})

step("DELETE: admin menghapus peminjaman kabel (DELETE /loans/{id})")
call("DELETE", f"{A}/loans/{second['loan_id']}", key=K)

step("READ lagi: hanya proyektor (status RETURNED) yang tersisa")
call("GET", f"{V}/loans")

step("BUKTI STORAGE: isi bucket S3 (1 objek = 1 peminjaman)")
s3 = boto3.client("s3", region_name=cfg["region"])
objs = s3.list_objects_v2(Bucket=cfg["bucket"], Prefix="loans/").get("Contents", [])
print(f"$ aws s3 ls s3://{cfg['bucket']}/loans/")
for o in objs:
    print(f"{o['LastModified']:%Y-%m-%d %H:%M:%S} {o['Size']:>6} {o['Key']}")
print(f"\nTotal {len(objs)} objek.")
