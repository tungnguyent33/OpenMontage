# Kịch bản mẫu chuẩn

Mỗi định dạng trong `brand/vanxuan/dinh-dang.yaml` có một file `<ma_dinh_dang>.yaml` ở thư mục này, viết ngày 2026-11-21 (C2b). Mỗi file gồm: lời đọc theo đoạn, thẻ chữ, hook ba phần và chú thích vì sao hay.

**Trạng thái.** Máy soạn bản nháp `trang_thai: cho_duyet`. Anh sửa lời rồi đổi thành `da_duyet`. Skill `skills/may-reels/bien-kich.md` chỉ dùng mẫu `da_duyet` làm ví dụ; mẫu `cho_duyet` bị bỏ qua.

**Repo công khai.** Các file ở đây được commit, nên **không** ghi học phí, số buổi, ngày khai giảng, ưu đãi hay lời học viên thật. Chỗ cần các số liệu đó để ô `[chờ anh xác nhận]`, kể cả khi `ban-hang.yaml` (chỉ có ở máy) đã có số. Khi sản xuất video thật, người viết lấy số từ `ban-hang.yaml` (chỉ mục `da_xac_nhan`). Không có số thì bỏ ý đó khỏi video, **không** để ô trống trong lời đọc.

**Luật.** Ý luật trong mẫu lấy từ `y_chinh` của chủ đề đã có nguồn. Khi sản xuất, người viết vẫn phải mở nguồn và trích nguyên văn (`skills/may-reels/san-xuat-khong-hoi.md`).

**CTA.** Đoạn `cta` là nguyên văn một câu trong `brand.json` → `cta`. Mã theo dõi `VX..` và lời kêu gọi theo mồi nhử sẽ có ở bước C2; mẫu ghi CTA muốn dùng sau này ở `cta_sau_nay`.

**Trạm phân tích.** Lúc soạn, `<KENH_GOC_DIR>/vanxuan/mau/` mới có một mẫu khác ngành (`TONG-HOP.md`), chưa có thư mục `ket-qua/`. Mẫu ở đây chỉ dùng bài học chung của mẫu đó: mỗi ý một cảnh, chữ chỉ giữ ý chính. Chưa có bài học nào từ video đối thủ.

**Cấu trúc file:**

| Khóa | Ý nghĩa |
|---|---|
| `ma_dinh_dang`, `ten`, `giong` | Theo `dinh-dang.yaml` |
| `nhom_doi_tuong`, `noi_lo` | Nhóm trong `doi-tuong.yaml` và nỗi lo được gỡ |
| `cong_thuc_hook` | Mã trong `hook.yaml` |
| `chu_de_vi_du` | Chủ đề dùng để viết mẫu |
| `hook` | `hinh` (0–3 giây), `noi` (câu nói đầu, trùng lời `s1`), `chu` (thẻ chữ `s1`) |
| `doan` | `id`, `vai` (`hook` / `than` / `chot` / `cta`), `loi` (lời đọc = phụ đề), `the` (`"DÒNG 1 / dòng 2"`, `null` ở CTA) |
| `vi_sao_hay` | Chú thích cho người viết: kỹ thuật nào, ở đâu |
| `can_xac_nhan` | Những gì anh cần điền hay kiểm trước khi duyệt |
| `trang_thai`, `ngay_cap_nhat` | `cho_duyet` / `da_duyet` |

`tests/may_reels/test_bien_tap.py` kiểm từng mẫu:
- đủ một mẫu cho mỗi định dạng;
- trạng thái hợp lệ;
- không có cụm từ cấm hay câu sáo;
- hook trong giới hạn âm tiết;
- câu không quá dài;
- thời lượng ước lượng trong 30–50 giây;
- CTA đúng nguyên văn.
