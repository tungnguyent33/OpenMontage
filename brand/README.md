# Bộ nhận diện kênh (brand)

Mỗi kênh một thư mục riêng. Các kênh không dùng chung file nào với nhau.

```
brand/
├── vanxuan/                    Đào tạo lái xe Vạn Xuân
│   ├── brand.json              SINH TỰ ĐỘNG từ thư mục kênh — đừng sửa tay
│   ├── quy-tac-rieng.yaml      SỬA TAY — cụm từ cấm, quy tắc nội dung, nguồn cảnh bị loại
│   ├── cau-hinh.yaml           SỬA TAY — tiền tố mã video, thư mục video, font
│   ├── assets/                 logo.png, logo-emblem.png, fonts/
│   └── _local/                 SINH TỰ ĐỘNG, GITIGNORE — toàn văn context/*.md (không đưa lên repo public)
└── <kênh-khác>/                (thêm sau, cùng cấu trúc)
```

## Cập nhật một kênh

Dữ liệu gốc của kênh (channel.yaml, banned.md, kho cảnh...) sửa ở thư mục kênh gốc, rồi nạp lại:

```powershell
tools_local\py.cmd tools_local/nap_kenh.py --id <mã>     # thư mục kênh = $KENH_GOC_DIR/<mã> (đặt trong .env)
tools_local\py.cmd tools_local/nap_kenh.py "<thư mục kênh gốc>"
```

Thư mục kênh gốc chỉ được đọc. `quy-tac-rieng.yaml` và `cau-hinh.yaml` không bị ghi đè. `brand.json` không chứa đường dẫn tuyệt đối: file của kênh = `$KENH_GOC_DIR/<mã>/<file_tuong_doi>`.

## Thêm kênh mới

1. Chuẩn bị thư mục kênh gốc có `channel.yaml` (nên có trường `id`, vd. `id: kenhmoi`).
2. Tạo `brand/<id>/cau-hinh.yaml` (tiền tố mã video, thư mục video, font) — xem mẫu ở `vanxuan/`. Thiếu thì brand.json ghi `canh_bao`.
3. (Tùy chọn) tạo `brand/<id>/quy-tac-rieng.yaml` nếu kênh có quy tắc riêng.
4. Chạy `tools_local\py.cmd tools_local/nap_kenh.py --id <id>`.
5. Khi yêu cầu video, nói rõ "cho kênh <id>".

Mã kênh: chữ thường không dấu, số, `-` hoặc `_`.
