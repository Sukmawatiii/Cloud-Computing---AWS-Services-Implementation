"""Lambda loan-admin (READ-WRITE, hanya admin). Handler: admin.lambda_handler

Lewat Lambda Function URL. Semua route tulis wajib header  x-admin-key.
  POST   /loans        -> buat peminjaman baru (Create)
  PUT    /loans/{id}   -> ubah data / tandai dikembalikan (Update)
  DELETE /loans/{id}   -> hapus peminjaman (Delete)
  GET    /health       -> cek akses ke bucket S3 (tanpa key)
"""
import base64
import hmac
import json
import os
import uuid
from datetime import date, datetime, timezone

import loan_store as store

ALLOWED_STATUS = ("BORROWED", "RETURNED")
UPDATABLE = ("item_name", "borrower_name", "status", "return_date")


def _body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw)


def _authorized(event):
    expected = os.environ.get("ADMIN_KEY", "")
    given = (event.get("headers") or {}).get("x-admin-key", "")
    return bool(expected) and hmac.compare_digest(given, expected)


def lambda_handler(event, context):
    method, path = store.request_info(event)
    path = path.rstrip("/") or "/"

    if method == "GET" and path == "/health":
        try:
            return store.respond(200, {"service": "loan-admin", "status": "ok", "storage": store.ping()})
        except Exception as exc:  # noqa: BLE001
            return store.respond(503, {"service": "loan-admin", "status": "error", "detail": str(exc)})

    if not _authorized(event):
        return store.respond(401, {"error": "header x-admin-key tidak ada atau salah"})

    try:
        data = _body(event) if method in ("POST", "PUT") else {}
    except (ValueError, UnicodeDecodeError):
        return store.respond(400, {"error": "body harus JSON yang valid"})

    # ---- CREATE ----
    if method == "POST" and path == "/loans":
        missing = [f for f in ("item_name", "borrower_name") if not data.get(f)]
        if missing:
            return store.respond(400, {"error": "field wajib: " + ", ".join(missing)})
        item = {
            "loan_id": str(uuid.uuid4()),
            "item_name": data["item_name"],
            "borrower_name": data["borrower_name"],
            "loan_date": data.get("loan_date") or date.today().isoformat(),
            "status": "BORROWED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return store.respond(201, store.save_loan(item))

    # ---- UPDATE / DELETE: path /loans/{id} ----
    parts = path.split("/")
    if len(parts) == 3 and parts[1] == "loans" and method in ("PUT", "DELETE"):
        loan_id = parts[2]
        if not store.valid_id(loan_id):
            return store.respond(404, {"error": "loan tidak ditemukan"})

        if method == "DELETE":
            if store.delete_loan(loan_id):
                return store.respond(200, {"message": f"loan {loan_id} dihapus"})
            return store.respond(404, {"error": "loan tidak ditemukan"})

        # PUT
        if data.get("status") and data["status"] not in ALLOWED_STATUS:
            return store.respond(400, {"error": f"status harus salah satu dari {list(ALLOWED_STATUS)}"})
        if data.get("status") == "RETURNED" and not data.get("return_date"):
            data["return_date"] = date.today().isoformat()
        changes = {k: data[k] for k in UPDATABLE if data.get(k)}
        if not changes:
            return store.respond(400, {"error": f"tidak ada field yang diubah, pilih dari {list(UPDATABLE)}"})
        item = store.get_loan(loan_id)
        if item is None:
            return store.respond(404, {"error": "loan tidak ditemukan"})
        item.update(changes)
        return store.respond(200, store.save_loan(item))

    return store.respond(404, {"error": "route tidak tersedia di loan-admin"})
