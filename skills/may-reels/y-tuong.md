# Máy Reels: chủ đề theo nhóm và lịch tuần

Skill cho agent chạy không tương tác (`claude -p`), do lệnh `python -m may_reels y-tuong --kenh <mã> --tuan <yyyy-Www>` gọi. Skill áp dụng cho **mọi kênh**; mọi giá trị riêng nằm trong `yeu_cau.json` (Python đã đọc từ `brand/<kenh>/`).

**Mục tiêu:** lấp các ô còn trống của lịch tuần, mỗi ô một chủ đề. Mỗi chủ đề nói rõ **cho ai** (một nhóm), **gỡ nỗi lo gì** (một nỗi lo), **ở tầng nào** (kéo xem / niềm tin / chuyển đổi), và có một câu hook gọi đúng người hoặc đúng nỗi lo ngay câu đầu. Người duyệt chủ đề trên Sheet (Làm / Bỏ) rồi mới sản xuất; bạn không viết kịch bản.

Python kiểm lại mọi thứ bạn ghi. Chủ đề sai luật bị gửi trả một lần; lần hai vẫn sai thì bị bỏ.

## Đầu vào: `yeu_cau.json`

- `o`: các ô cần lấp. Mỗi ô có `thu` (2..7, 8 = Chủ Nhật), `ngay`, `tang`, `dinh_dang_duoc` (định dạng làm được tuần này, **theo thứ tự ưu tiên**), `ghi_chu_lich`, `nhom_mua_bat_buoc` (ô của mùa: nhóm phải thuộc danh sách này), `du_phong` (định dạng của ngày đó không làm được, Python đưa định dạng cùng tầng của ngày khác).
- `mua`: mùa đang chạy (`nhom`, `goc`, `dieu_kien_duoc_noi`) hoặc `null`.
- `doi_tuong`: các nhóm, mỗi nhóm có `noi_lo`, `khoanh_khac_mua`, `bang_chung_thuyet_phuc`, `ai_quyet_dinh`. `dinh_vi`: lời hứa của kênh.
- `du_kien_da_xac_nhan`: dữ kiện bán hàng **được nói** (`id`, `noi_dung`). `du_kien_chua_co`: dữ kiện **chưa có**, không được nói, không được đoán.
- `cau_hoi_khach_chua_dung`: câu hỏi thật của khách (`ma_cau_hoi`, `cau_hoi`, `nhom` nếu biết).
- `ma_tran_chua_lam`: các cặp nhóm × nỗi lo chưa có chủ đề nào (đã xếp theo ưu tiên nhóm).
- `chu_de_luat_con_lai`: chủ đề luật đã có trong kho của kênh, chưa làm, chưa lên lịch.
- `da_len_lich_gan_day`: chủ đề đã lên lịch quanh tuần này (nhóm, nỗi lo, định dạng, ngày).
- `chua_thu`: nhóm và định dạng chưa có video nào.
- `cong_thuc_hook`: công thức hook của kênh. `cam`: cụm từ cấm, câu sáo, hook sáo, cụm gấp gáp, nội dung cấm.
- `phan_hoi` (chỉ có ở vòng 2): lỗi Python tìm thấy theo từng ô, lỗi chung, và các chủ đề đã đạt.

## Cách làm

1. **Với từng ô, chọn định dạng.** Lấy định dạng đầu tiên trong `dinh_dang_duoc`. Chỉ lấy định dạng sau khi định dạng đầu bị trùng (bước 4) hoặc cần cho chủ đề "thử mới" (bước 5); ghi lý do ở `ly_do`.
2. **Chọn nguồn chủ đề theo đúng thứ tự:**
   1. `cau_hoi_khach_chua_dung`: câu hỏi thật của khách hợp với tầng và định dạng của ô. Ghi `nguon_y_tuong: "cau_hoi_khach"` và `ma_cau_hoi`. Mỗi câu hỏi dùng cho một chủ đề. Câu hỏi có `nhom` thì chủ đề cho đúng nhóm đó. Nỗi lo được viết bằng chữ của khách.
   2. `ma_tran_chua_lam`: một cặp nhóm × nỗi lo chưa làm, ưu tiên nhóm đứng đầu. Ghi `nguon_y_tuong: "ma_tran"`; `noi_lo` chép **đúng nguyên văn** một mục trong `noi_lo` của nhóm.
   3. Chủ đề luật: với ô kéo xem có định dạng luật, ưu tiên dùng lại `chu_de_luat_con_lai` (ghi `ma_co_san`, không viết lại `chu_de`, `y_chinh`); không có cái hợp thì viết chủ đề luật mới. Ghi `nguon_y_tuong: "luat"`.
3. **Nhóm và nỗi lo.** Mỗi chủ đề đúng **một** nhóm và **một** nỗi lo. Ô có `nhom_mua_bat_buoc` thì nhóm phải thuộc danh sách đó, góc kể theo `mua.goc`. Nhóm nên thuộc `nhom_chinh` của định dạng; định dạng không có nhóm chính thì chọn nhóm có nỗi lo khớp nhất. Với nhóm mà người trả tiền khác người học (xem `ai_quyet_dinh`), chủ đề nói với người quyết định.
   Video kéo xem (luật) vẫn có nhóm và nỗi lo: chọn nhóm mà câu luật đó chạm tới nhiều nhất (ví dụ mức phạt → người đi xe chưa có bằng, nỗi lo "Sợ bị phạt").
4. **Chống trùng.** Cùng nhóm + cùng nỗi lo + cùng định dạng với một chủ đề trong `da_len_lich_gan_day` (60 ngày) hoặc với chủ đề khác trong tuần là **trùng**. Đổi nỗi lo, đổi nhóm, hoặc đổi định dạng.
5. **Thử mới.** Ít nhất 1 chủ đề trong tuần dành cho một nhóm hoặc một định dạng trong `chua_thu`; đánh dấu `thu_moi: true`.
6. **Chủ đề chuyển đổi** chỉ dựa vào `du_kien_da_xac_nhan`. Ghi các `id` đã dựa vào ở `du_kien_dung`. Chủ đề cần một dữ kiện trong `du_kien_chua_co` (số buổi, giấy tờ, lịch khai giảng, mồi nhử…) thì **không viết chủ đề đó**: chọn góc khác không cần dữ kiện thiếu; không còn góc nào thì để ô đó vào `bo_qua` kèm lý do ghi rõ thiếu dữ kiện gì.
7. **Chủ đề có nội dung luật** (`co_noi_dung_luat: true`): ghi văn bản cần đối chiếu ở `nguon_doi_chieu` (tên văn bản, và Điều/khoản nếu biết chắc). Bạn **không** tra luật ở bước này; lệnh `nguon-luat` sẽ mở văn bản chính thức sau. `y_chinh` là ý bạn cho là đúng, ghi rõ "cần kiểm" nếu không chắc. Chủ đề không có nội dung luật: `co_noi_dung_luat: false`.
8. **Viết.**
   - `chu_de`: câu hỏi hoặc tình huống, ngắn, bằng lời người xem hay nói.
   - `y_chinh`: 1–2 câu: video sẽ nói gì để gỡ nỗi lo, bằng chứng nào (lấy từ `bang_chung_thuyet_phuc`, `du_kien_da_xac_nhan`).
   - `hook_de_xuat`: câu nói đầu tiên, đọc trong 3 giây (khoảng 13 âm tiết), **gọi đúng người hoặc đúng nỗi lo ngay câu đầu**. Dùng một công thức trong `cong_thuc_hook`, ghi mã ở `cong_thuc_hook`.
   - `ma` (chủ đề mới): chữ thường không dấu, gạch nối, tối đa 40 ký tự, ví dụ `di-xe-10-nam-chua-bang`.
9. **Cấm:** cụm từ cấm, câu sáo, hook sáo trong `cam`; hứa kết quả thi ("bao đậu"…); số tiền, số buổi, ngày, ưu đãi không có trong `du_kien_da_xac_nhan`; gấp gáp giả ("sắp hết", "chỉ còn", hạn chót không có thật); nêu tên hay hạ thấp trung tâm khác; câu trong ngoặc kép ở `mua.dieu_kien_duoc_noi` khi chưa đủ điều kiện ghi kèm.

## Kết quả: chỉ ghi MỘT file `y_tuong.json` trong thư mục được giao

```json
{
  "chu_de": [
    {
      "thu": 3,
      "dinh_dang": "<mã trong dinh_dang_duoc của ô>",
      "doi_tuong": "<mã nhóm>",
      "noi_lo": "<một nỗi lo>",
      "nguon_y_tuong": "cau_hoi_khach | ma_tran | luat",
      "ma_cau_hoi": null,
      "ma_co_san": null,
      "ma": "<mã chủ đề mới, bỏ trống nếu có ma_co_san>",
      "chu_de": "<câu hỏi / tình huống>",
      "y_chinh": "<video nói gì, bằng chứng gì>",
      "hook_de_xuat": "<câu nói đầu>",
      "cong_thuc_hook": "<mã công thức>",
      "co_noi_dung_luat": false,
      "nguon_doi_chieu": "<văn bản cần đối chiếu; bỏ trống nếu không có nội dung luật>",
      "du_kien_dung": ["<id trong du_kien_da_xac_nhan>"],
      "du_kien_thieu": [],
      "thu_moi": false,
      "ly_do": "<vì sao chọn nguồn, nhóm, định dạng này; một câu>"
    }
  ],
  "bo_qua": [
    {"thu": 5, "ly_do": "<chỉ khi không viết được chủ đề nào cho ô: thiếu dữ kiện gì>"}
  ]
}
```

Mỗi ô trong `o` có đúng một mục trong `chu_de` hoặc trong `bo_qua`. Vòng 2: giữ các chủ đề trong `phan_hoi.chu_de_da_dat` (trừ khi cần đổi một chủ đề để sửa lỗi chung), viết lại các ô bị lỗi, ghi lại toàn bộ file.
