Ambil nilai dari `deploy_output.json` (atau output `deploy.py`).

```bash
VIEWER=https://xxxx.lambda-url.us-east-1.on.aws
ADMIN=https://yyyy.lambda-url.us-east-1.on.aws
KEY=<admin_key>

curl $VIEWER/health
curl $ADMIN/health

# CREATE
curl -X POST $ADMIN/loans -H "x-admin-key: $KEY" -H "Content-Type: application/json" \
  -d '{"item_name":"Proyektor Epson","borrower_name":"Sukmawati"}'

# READ
curl $VIEWER/loans

# UPDATE (ganti <LOAN_ID> dengan loan_id dari respons CREATE)
curl -X PUT $ADMIN/loans/<LOAN_ID> -H "x-admin-key: $KEY" -H "Content-Type: application/json" \
  -d '{"status":"RETURNED"}'

# DELETE
curl -X DELETE $ADMIN/loans/<LOAN_ID> -H "x-admin-key: $KEY"

# Keamanan: tanpa key harus 401
curl -i -X POST $ADMIN/loans -H "Content-Type: application/json" -d '{"item_name":"x","borrower_name":"y"}'
```