# Máy Reels: gắn nhãn một cảnh quay mới

Skill cho agent chạy không tương tác (`claude -p`), do lệnh `python -m may_reels kho nap --kenh <mã>` gọi cho từng file mới trong thư mục mới quay của kênh. Skill áp dụng cho **mọi kênh**.

**Vai trò:** bạn ghi lại **điều nhìn thấy**. Python kiểm nhãn trước khi đưa vào kho. Nhãn sai mà trông chắc chắn còn tệ hơn nhãn thận trọng, nhất là ở `mat_nguoi` và `rui_ro`, vì hai trường này quyết định cảnh có được lên mạng hay không.

## Đầu vào (thư mục được giao trong prompt)

- `yeu_cau.json`:
  - `ma`, `file`, `loai_file` (`video` hoặc `anh`), `rong`, `cao`, `huong` (`doc`/`ngang`/`vuong`), `fps`, `thoi_luong` (giây);
  - `chuyen_canh`: mốc giây máy phát hiện có chuyển cảnh;
  - `co_am_thanh`, `lufs`;
  - `loi_noi`: `co_loi`, `so_tu`, `trich` (máy chép, có thể sai từ; dưới 4 từ coi như không có lời);
  - `loi_thoai_srt`: lời nói theo mốc giây (rỗng nếu không có);
  - `the_da_co`: các từ khóa kho đang dùng.
- `khung.jpg`: lưới khung hình chia đều clip, mỗi ô có in mốc giây ở góc trên trái. Ảnh tĩnh thì là chính ảnh đó thu nhỏ. Xem bằng Read.

## Kết quả: chỉ ghi MỘT file `nhan.json` trong thư mục được giao

```json
{
  "loai": "BROLL",
  "mo_ta": "<một câu: thấy gì, ai làm gì>",
  "dia_diem": "san-tap",
  "co_canh": "trung",
  "chuyen_dong": "dung-yen",
  "the": ["<tu-khoa>", "<tu-khoa>"],
  "doan_dung_duoc": [[0.0, 6.5]],
  "chat_luong": "dung-duoc",
  "ghi_chu": "<lý do nếu kém; đặc điểm đáng chú ý>",
  "rui_ro": [],
  "duoc_dung": true,
  "can_xu_ly": "",
  "loi_noi": "",
  "mat_nguoi": false
}
```

Ví dụ trên chỉ minh họa **định dạng**: mọi giá trị phải lấy từ khung hình và đầu vào thật.

| Trường | Giá trị được phép | Cách điền |
|---|---|---|
| `loai` | `NOI` / `BROLL` / `THAO` / `ANH` | NOI: người nói trước máy (có lời nói rõ, nhìn vào ống kính). BROLL: cảnh minh họa không lời. THAO: làm mẫu một thao tác (chạy vòng số 8, dừng đúng vạch). Ảnh tĩnh luôn là ANH. |
| `mo_ta` | một câu | Chỉ điều thấy được. **Không đoán tên, tuổi, quan hệ** của người trong hình. |
| `dia_diem` | `san-tap` / `phong-hoc` / `duong-thuc` / `van-phong` / `khac` | |
| `co_canh` | `rong` / `trung` / `trung-can` / `can` / `chi-tiet` | Cỡ cảnh chủ đạo. |
| `chuyen_dong` | `dung-yen` / `lia` / `theo-sau` / `tien-lai` / `rung` | Chuyển động của máy quay. |
| `the` | danh sách từ khóa | Không dấu, chữ thường, nối bằng gạch ngang (`vong-so-8`, `xi-nhan`, `tay-ga`). Đủ để tìm cảnh theo kịch bản. **Dùng lại từ trong `the_da_co`** khi cùng nghĩa, không đặt từ mới đồng nghĩa. |
| `doan_dung_duoc` | `[[vào, ra], ...]` giây | Đoạn hình ổn: không rung mạnh, không mất nét, không chuyển cảnh giữa chừng, **không có đoạn lộ rủi ro** nếu tránh được. Ước theo mốc trên `khung.jpg` và `chuyen_canh`, làm tròn 0,5 giây, tăng dần, không chồng nhau, nằm trong `0`..`thoi_luong`. Ảnh tĩnh để `[]`. |
| `chat_luong` | `tot` / `dung-duoc` / `kem` | `kem` khi tối, ngược sáng, rung, mất nét, gió to: ghi lý do vào `ghi_chu`. |
| `ghi_chu` | chữ | Lý do chất lượng; khung quay ngang thì ghi "ngang: dựng dọc sẽ cắt hai bên"; cảnh gắn với một dịp (băng rôn lễ, Tết) thì ghi để tránh dùng ngoài mùa. |
| `rui_ro` | tập con của `mat-hoc-vien`, `bien-so`, `giay-to`, `ten-nguoi`, `nguoi-ngoai` | Ghi mọi rủi ro thấy được ở **bất kỳ** khung nào. |
| `duoc_dung` | true / false | `false` khi nội dung hỏng hoặc rủi ro không tránh được bằng cách chỉ dùng một đoạn. Không chắc thì `true` kèm `can_xu_ly`. Việc chờ xác nhận quyền hình **không** do trường này quyết định: máy tự xử lý theo `mat_nguoi`. |
| `can_xu_ly` | chữ | Bắt buộc khi có `rui_ro` hoặc `mat_nguoi`: chỉ dùng đoạn x–y, cắt khung vào vùng nào (theo % bề ngang và chiều cao), che biển số, cần xin phép ai. |
| `loi_noi` | chữ | Tóm tắt nội dung lời nói nếu `loi_noi.co_loi`; bỏ trống nếu không. Không chép lại nguyên văn. |
| `mat_nguoi` | true / false | `true` nếu ở bất kỳ khung nào thấy **mặt người nhận ra được**. Không tính: đội mũ bảo hiểm kín mặt, quay lưng, ở xa nhỏ hơn khoảng 1/10 khung. **Không chắc thì ghi `true`.** |

Máy tự điền các trường còn lại của bản ghi kho (`nguon`, `rong_nguon`, `cao_nguon`, `dung_cho`). Không ghi các trường đó.

## Quy tắc

- Chỉ ghi điều nhìn thấy trong `khung.jpg` hoặc có trong `yeu_cau.json`.
- Không đọc, không sửa file nào ngoài thư mục được giao. Không ghi file nào ngoài `nhan.json`.
- Ghi file xong thì dừng. Trả lời một dòng: "<ma>: <loai>, <mo_ta ngắn>, mat_nguoi=<true/false>".
