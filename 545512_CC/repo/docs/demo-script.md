# Rencana video demo 

Perkiraan durasi 4-5 menit.

| Menit | Yang ditunjukkan | Yang diucapkan (garis besar) |
|---|---|---|
| 0:00 | Slide/diagram arsitektur | Use case peminjaman alat, Track C, dipecah jadi dua Lambda (viewer dan admin), storage S3 |
| 0:45 | Penyesuaian dari contoh track | API Gateway diganti Function URL, DynamoDB diganti S3 karena tidak tersedia di sandbox |
| 1:15 | Terminal: `python3 scripts/deploy.py` | Seluruh infrastruktur dibangun dengan satu perintah (reproducible) |
| 2:00 | Konsol AWS: Lambda (2 fungsi + Function URL), S3 bucket, role LabRole | Pemetaan ke diagram |
| 2:45 | Terminal: `python3 scripts/demo.py` | CREATE, READ, UPDATE, keamanan 401/405, DELETE |
| 4:00 | Konsol S3: isi `loans/` | Bukti data tersimpan sebagai objek JSON |
| 4:30 | Penutup | Keamanan (admin key, Block Public Access), batasan, rencana perbaikan |