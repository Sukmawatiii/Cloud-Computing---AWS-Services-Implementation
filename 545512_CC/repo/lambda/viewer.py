"""Lambda loan-viewer (READ-ONLY). Handler: viewer.lambda_handler

Lewat Lambda Function URL:
  GET /loans   -> daftar semua peminjaman (Read)
  GET /health  -> cek akses ke bucket S3
"""
import loan_store as store


def lambda_handler(event, context):
    method, path = store.request_info(event)
    path = path.rstrip("/") or "/"

    if method == "GET" and path == "/health":
        try:
            return store.respond(200, {"service": "loan-viewer", "status": "ok", "storage": store.ping()})
        except Exception as exc:  # noqa: BLE001
            return store.respond(503, {"service": "loan-viewer", "status": "error", "detail": str(exc)})

    if method == "GET" and path == "/loans":
        return store.respond(200, store.list_loans())

    return store.respond(404 if method == "GET" else 405, {"error": "route tidak tersedia di loan-viewer"})
