# Bộ nhận diện kênh (brand)

Mỗi kênh một thư mục riêng. Các kênh không dùng chung file nào với nhau.

```
brand/
├── vanxuan/                    Đào tạo lái xe Vạn Xuân
│   ├── brand.json              SINH TỰ ĐỘNG từ thư mục kênh — đừng sửa tay
│   ├── quy-tac-rieng.yaml      SỬA TAY — cụm từ cấm, quy tắc nội dung, nguồn cảnh bị loại
│   └── assets/                 logo.png, logo-emblem.png, fonts/
└── <kênh-khác>/                (thêm sau, cùng cấu trúc)
```

## Cập nhật một kênh

Dữ liệu gốc của kênh (channel.yaml, banned.md, kho cảnh...) sửa ở thư mục kênh gốc, rồi nạp lại:

```powershell
python tools_local/nap_kenh.py "<thư mục kênh gốc>"
```

Thư mục kênh gốc chỉ được đọc. `quy-tac-rieng.yaml` không bị ghi đè.

## Thêm kênh mới

1. Chuẩn bị thư mục kênh gốc có `channel.yaml` (nên có trường `id`, vd. `id: kenhmoi`).
2. (Tùy chọn) tạo `brand/<id>/quy-tac-rieng.yaml` nếu kênh có quy tắc riêng — xem mẫu ở `vanxuan/`.
3. Chạy `python tools_local/nap_kenh.py "<thư mục kênh>"` (thêm `--id <mã>` nếu channel.yaml không có `id`).
4. Khi yêu cầu video, nói rõ "cho kênh <id>".

Mã kênh: chữ thường không dấu, số, `-` hoặc `_`.
