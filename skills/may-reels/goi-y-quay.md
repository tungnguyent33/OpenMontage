# Máy Reels: gợi ý cần quay gì

Skill cho agent chạy không tương tác (`claude -p`), do lệnh `python -m may_reels kho thieu --kenh <mã>` gọi. Skill áp dụng cho **mọi kênh**.

**Mục tiêu:** một danh sách quay **gộp theo buổi**, để người quay đi một buổi mà ra cảnh cho nhiều video. Máy chủ động nói cần quay gì, thay vì đợi từng video thiếu cảnh rồi mới báo.

## Đầu vào: `goi_y_quay.yeu_cau.json`

- `chu_de`: chủ đề cần làm (`ma`, `chu_de`, `y_chinh`, `tru_cot`, `dinh_dang`). `da_duyet: true` là chủ đề người đã chọn "Làm", ưu tiên hơn chủ đề `da_duyet: false` (chưa quyết, chỉ có khi chạy với `--ca-chua-duyet`).
- `thu_vien_dinh_dang`: khung nhịp theo trụ cột (hook, thân, chốt, CTA; thời lượng từng phần). Dùng để biết mỗi video cần những loại cảnh nào và dài bao nhiêu.
- `khung_hinh`: khung xuất của kênh.
- `kho_canh`: cảnh đang có. `dung_duoc: false` kèm `ly_do_loai` là cảnh không dùng được. `so_lan_dung` là số video đã dùng cảnh đó. Một cảnh đã dùng nhiều lần thì nên quay cảnh thay thế.
- `yeu_cau_dang_mo`: cảnh mà các video đang chờ đã yêu cầu (tab Cần quay, chưa quay). `ma_video` có giá trị là video đã dựng bằng cảnh tạm hoặc đang chờ quay.
- `quyen_hinh`, `quy_tac_kenh`: quy tắc của kênh về người lên hình và nội dung.

## Cách làm

1. **Với từng chủ đề**, đọc `y_chinh` và khung nhịp của trụ cột. Liệt kê những cảnh video đó cần: cảnh minh họa cho từng ý, cảnh người nói trước máy cho hook, câu chốt hoặc CTA (nếu định dạng có), cảnh làm mẫu thao tác.
2. **So với kho.** Cảnh nào kho đã có bản `dung_duoc: true`, khớp ý, chất lượng `tot`/`dung-duoc` và chưa dùng quá nhiều thì **không** đề xuất quay lại. Chỉ đề xuất cảnh còn thiếu, cảnh kho có nhưng hỏng (độ phân giải thấp, gắn với một mùa, lộ mặt hay biển số không tránh được), hoặc cảnh đã dùng từ 3 lần trở lên.
3. **Gộp và ưu tiên.**
   - Một cảnh phục vụ được nhiều chủ đề thì gộp thành một (ví dụ cận tay bật xi-nhan dùng cho cả chủ đề vòng xuyến lẫn chủ đề chuyển làn).
   - Ưu tiên (`uu_tien` 1 = quay trước) theo thứ tự: cảnh đáp ứng `yeu_cau_dang_mo`, rồi cảnh dùng lại được cho nhiều video, rồi cảnh cho chủ đề đã duyệt.
   - Cảnh đáp ứng một yêu cầu đang mở thì ghi mã yêu cầu đó vào `gop_yeu_cau`. Khi người quay đánh dấu "Đã quay", máy dùng trường này để biết video nào đã đủ cảnh.
4. **Gộp theo buổi** theo địa điểm và thời điểm quay, ví dụ "Sân tập buổi sáng", "Phòng học", "Đường thật gần trung tâm". Mỗi buổi khoảng 1–2 giờ.
5. **Viết từng cảnh để người không chuyên quay được ngay:**
   - `mo_ta`: quay cái gì, ai làm gì;
   - `goc_may`: đặt máy ở đâu, cao bao nhiêu, cỡ cảnh (rộng / trung / trung cận / cận / chi tiết), đứng yên hay đi theo;
   - `cam_doc`: luôn là `true` (khung 9:16). Chỉ ghi `false` kèm `ly_do_ngang` khi thật sự cần;
   - `thoi_luong_giay`: `[tối thiểu, tối đa]`. Cảnh minh họa thường 3–6 giây, quay 2 lần (một lần máy đứng yên, một lần đi chậm theo). Cảnh nói trước máy dài theo lời thoại, cộng 2 giây ở đầu và 2 giây ở cuối;
   - `loi_thoai`: bắt buộc với cảnh `NOI`. Viết đúng câu người hướng dẫn sẽ nói, ngắn, dễ nói một hơi, khớp `y_chinh`. Không hứa kết quả thi, không bịa số liệu, không đưa điều luật chưa có nguồn;
   - `anh_sang`: giờ nên quay, hướng đứng so với mặt trời hoặc cửa sổ, tránh ngược sáng;
   - `tieng_on`: tiếng xe, gió, đông người; cần mic cài áo không; giữ yên lặng 3 giây đầu;
   - `xin_phep`: người lên hình cần đồng ý gì. Người hướng dẫn phải đồng ý dùng hình trên mạng. Học viên chỉ được lên hình khi đã đồng ý bằng tin nhắn hoặc giấy viết; nếu không thì quay từ phía sau hoặc từ dưới chân, không thấy mặt. Biển số xe quay nghiêng hoặc tránh. Không quay giấy tờ, bảng điểm có tên.
6. Không đề xuất cảnh tạo bằng AI, cảnh stock, hay cảnh vi phạm `quy_tac_kenh`.

## Kết quả: chỉ ghi MỘT file `goi_y_quay.json` trong thư mục được giao

```json
{
  "buoi": [
    {
      "ten": "<tên buổi>",
      "dia_diem": "<địa điểm>",
      "thoi_diem": "<giờ nên quay>",
      "canh": [
        {
          "ma": "<ma-canh-khong-dau>",
          "loai": "BROLL",
          "mo_ta": "<quay gì>",
          "goc_may": "<đặt máy thế nào>",
          "cam_doc": true,
          "thoi_luong_giay": [3, 6],
          "loi_thoai": null,
          "anh_sang": "<lưu ý ánh sáng>",
          "tieng_on": "<lưu ý tiếng ồn>",
          "xin_phep": "<ai cần đồng ý gì>",
          "phuc_vu_chu_de": ["<ma chủ đề>"],
          "gop_yeu_cau": ["<ma_yeu_cau đang mở>"],
          "uu_tien": 1,
          "ly_do": "<vì sao cần: kho thiếu gì>"
        }
      ]
    }
  ],
  "ghi_chu_chung": "<lưu ý chung cho cả danh sách, có thể bỏ trống>"
}
```

Ví dụ trên chỉ minh họa **định dạng**: mọi giá trị trong ngoặc nhọn phải thay bằng nội dung thật.

Máy kiểm tra trước khi ghi Sheet và từ chối cả danh sách khi:
- `ma` không phải chữ thường không dấu nối gạch ngang (tối đa 40 ký tự), hoặc bị trùng;
- `loai` khác `NOI`, `BROLL`, `THAO`;
- thiếu `mo_ta`, `goc_may`, `anh_sang`, `tieng_on` hoặc `xin_phep`;
- cảnh `NOI` không có `loi_thoai`;
- `phuc_vu_chu_de` hoặc `gop_yeu_cau` có mã không nằm trong đầu vào, hoặc cảnh không phục vụ gì.

Mã cảnh giữ ổn định giữa các lần chạy khi vẫn là cùng một cảnh, để dòng trên tab Cần quay được cập nhật chứ không bị nhân đôi.

## Kết thúc

Ghi file xong thì dừng. Trả lời một dòng: "<số cảnh> cảnh, <số buổi> buổi; quay trước: <mã cảnh ưu tiên 1>".
