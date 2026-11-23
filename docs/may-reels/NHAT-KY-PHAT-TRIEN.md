# Máy Reels: nhật ký phát triển

Mỗi phiên một mục, mới nhất ở trên. Ghi việc đã làm, quyết định, số đo, việc bỏ dở. Trạng thái hiện tại: `TRANG-THAI.md`.

File tạo ngày 2026-11-19. Các mục từ 2026-11-15 đến 2026-11-18 (cuối file) chuyển nguyên văn từ `KE-HOACH.md` mục 1, 7–10 ngày 2026-11-21; các phiên đó còn ở lịch sử git của nhánh `kenh-vanxuan`. Quyết định đã chốt: `QUYET-DINH.md`.

## 2026-11-23 (2): sửa điểm 0 giả khi sản xuất, thêm Điều 89 khoản 3 điểm a

**Đã làm:**
- `san_xuat.qua_bien_tap`: biên tập hỏng thì thử lại 1 lần; vẫn hỏng thì không trả người viết sửa theo điểm 0, dựng tiếp với kế hoạch hiện có, `diem_kich_ban` trống, cảnh báo "Biên tập lỗi, chưa có điểm kịch bản" (`bien_tap.CANH_BAO_LOI_BIEN_TAP`). Nhật ký ghi "biên tập lỗi", không ghi "kịch bản 0/75"; dòng `san_xuat` và log in "kịch bản -" thay cho "None".
- Hàm thử lại chung `bien_tap.bien_tap_thu_lai`; `so_sanh_kich_ban._bien_tap_1_lan_thu_lai` gọi nó rồi ném `LoiBienTap` như trước.
- Nguồn `a1-xe-150cc`: ô "Nguồn cần đối chiếu" trong `chu-de.md` của kênh gốc (theo yêu cầu người dùng, sao lưu `chu-de.md.bak-20261123-225509`) đổi từ "… và Điều 89" thành "Luật 36/2024/QH15 Điều 57 khoản 1 điểm a; Điều 89 khoản 2 điểm a và khoản 3 điểm a"; nạp lại `brand.json`. `projects/_may_reels/nguon_luat/vanxuan/a1-xe-150cc.json` (ngoài git, sao lưu `.json.bak-20261123`) thêm nguyên văn khoản 3 điểm a. Nguyên văn lấy từ nguồn n4 của kế hoạch so sánh vx-005; phần đầu câu đối chiếu lại khớp từng chữ trên hethongphapluat.com (không phải trang chính thức).

**Chưa làm:** tab Ý tưởng trên Sheet còn `nguon_de_xuat` cũ của `a1-xe-150cc` (không ghi Sheet trong phiên này). Ô "Ý chính" của chủ đề chưa có ý "đổi sang hạng A vẫn dưới 175 phân khối".

**Test:** `tests/may_reels` 360/360 (thêm 2 test biên tập hỏng khi sản xuất).

## 2026-11-23: C2b việc 6, so sánh trước sau

**Mục tiêu:** viết lại 3 video đã làm bằng bộ biên kịch (chỉ kế hoạch, không dựng), chấm cạnh bản cũ bằng cùng một biên tập, báo chi phí thêm.

**Đã làm:**
- Lệnh `bien-kich so-sanh --ma <mã> [--ma ...]` (`may_reels/so_sanh_kich_ban.py`). Kịch bản cũ lấy từ `ke_hoach.json`, hoặc dựng lại từ `artifacts/script.json` với dự án dựng tay (vx-005). Kết quả và báo cáo ở `projects/_may_reels/so-sanh/` (bị git bỏ qua). Không đụng `projects/<mã>/`, không ghi Sheet.
- Sửa lỗi báo cáo ghi "Điểm cũ 0" khi biên tập hỏng: `KetQuaBienTap.loi_agent`. So sánh ghi "lỗi" cho bản đó, thử lại đúng 1 lần (cả người viết lẫn biên tập), rồi chạy tiếp video sau. Có test.
- Lần chạy 2026-11-22 hỏng cả 3 video vì phiên đó đi qua router AI local (Connection refused). Đã gỡ cấu hình router, chạy lại 2026-11-23 bằng Claude Code trực tiếp.

**Kết quả** (ngưỡng 75, không vòng sửa nào):

| Video | Cũ | Mới |
|---|---|---|
| vx-005 A1 lái xe 150cc | 59 | 86 |
| vx-006 ngã tư không đèn, không biển | 73 | 90 |
| vx-007 vòng xuyến | 79 | 84 |

- Biên tập thêm trung bình 51 s và 0,43 USD mỗi video (claude -p tự báo; gói Claude Code không tính theo lượt). Người viết lần đầu 324 s, 1,97 USD.
- Biên tập bắt được ở bản mới:
  - câu không có trong trích nguồn (vx-007 "ngược chiều kim đồng hồ"; vx-006 "xe to hay xe nhỏ");
  - lời kêu gọi lệch người xem (vx-005);
  - câu đọc tên luật dài; chữ trên màn hình lặp lời nói.
- Người duyệt sửa tay sau khi chấm (chưa chấm lại):
  - vx-005 s6 thêm ý A1 đổi sang hạng A vẫn giới hạn dưới 175 phân khối (Điều 89 khoản 3);
  - vx-005 kêu gọi đổi thành mời học hạng A. Câu này chưa có trong danh sách CTA của kênh;
  - vx-007 giữ câu ngược chiều kim đồng hồ như điều quan sát trên đường, bỏ gắn nguồn luật.

**Còn dở:** luồng sản xuất (`qua_bien_tap`) vẫn coi biên tập hỏng là điểm 0.

**Test:** `tests/may_reels` 358/358. Toàn bộ repo 3307 qua, 1 hỏng (test webp upstream).

## 2026-11-21 (2): C2b, bộ biên kịch

**Mục tiêu:** kịch bản đạt mức người viết nội dung chuyên nghiệp; lỗi kịch bản bị bắt trước khi tốn công sinh giọng và dựng. Chạy theo `LO-TRINH.md` bước 3, trước C1 và C2.

**Đã làm:**
- **Việc 1.** `skills/may-reels/bien-kich.md` (mới) nhận toàn bộ phần viết lời: nhịp, phụ đề, giọng, cụm từ cấm, CTA, thẻ chữ, quy trình viết. `san-xuat-khong-hoi.md` trỏ sang skill này ở bước 1; phần chọn cảnh, caption, nguồn luật giữ nguyên. `yeu_cau.json` có thêm `dinh_dang` (định dạng của chủ đề), `cau_hoi_khach` (rỗng tới C1).
- **Việc 2.** Chép 6 file và LICENSE của marketingskills (MIT, commit `5b2b400eec1e…`) vào `docs/may-reels/tham-khao/marketingskills/`, có README; không cài thành skill. Viết lại cho tiếng Việt và luật của kênh, thành 4 file trong `brand/vanxuan/`:
  - `hook.yaml`: 12 công thức hook, mỗi công thức 2 ví dụ đủ ba phần, kèm `hook_sao`;
  - `giong-noi.yaml`: xưng hô theo giọng máy / giọng thầy, độ dài câu, 25 từ tránh, cách nói số và điều luật;
  - `giu-chan.yaml`: 9 kỹ thuật giữ người xem;
  - `rubric-kich-ban.yaml`: 10 tiêu chí, tổng 100, ngưỡng 75, 2 vòng sửa, giới hạn máy kiểm, 7 kiểu câu văn AI (từ mục No AI Tells), bảng trần điểm.

  Mọi mục đều `gia_thuyet`.
- **Việc 3.** `brand/vanxuan/kich-ban-mau/`: 16 kịch bản mẫu, mỗi định dạng của `dinh-dang.yaml` một file, đều `cho_duyet`, kèm `vi_sao_hay` và `can_xac_nhan`.
  - Mọi số liệu bán hàng để ô `[chờ anh xác nhận]`, vì repo công khai.
  - Ý luật chỉ lấy từ `y_chinh` đã có nguồn.
  - Ước lượng 30–36 giây mỗi mẫu.
  - Trạm phân tích mới có 1 mẫu khác ngành, chưa có `ket-qua/`: chỉ dùng bài học chung (mỗi ý một cảnh, chữ chỉ giữ ý chính).
- **Việc 4.** Schema `ke_hoach_video` thêm `kich_ban`, không bắt buộc nên kế hoạch cũ vẫn hợp lệ: nhóm, nỗi lo, 3 góc kể, `hook_chon` và 4 `phuong_an_hook` (mỗi hook có công thức, hình 0–3 giây, câu nói, chữ), `ban_1`, `sua_ban_2`.
- **Việc 5.** `may_reels/bien_tap.py`:
  - Máy kiểm chữ trước khi gọi biên tập. Lỗi chặn thì không gọi biên tập, điểm 0.
  - Biên tập (`skills/may-reels/bien-tap.md`) chạy `claude -p` riêng, chỉ được Read đúng 2 file: skill và `bien_tap/dau_vao.json`. File đầu vào không có góc kể, lý do chọn, phương án hook, bản 1, `quyet_dinh`. Thêm tham số `doc=` cho `goi_agent`.
  - Python cộng điểm và áp trần.
  - `san_xuat.qua_bien_tap`: sau bản kế hoạch đầu, dưới ngưỡng thì trả về người viết, tối đa 2 vòng, rồi vẫn dựng kèm cảnh báo "Kịch bản dưới ngưỡng".
  - Hàng chờ thêm 2 cột máy `diem_kich_ban`, `cong_thuc_hook`; Nhật ký thêm bước `bien_tap`.
- **Việc 6 (so sánh trước sau): chưa xong.** Lần chạy đầu hỏng vì hết hạn mức Claude. Code dở để ngoài commit việc 1–5, chạy lại ở phiên sau.
- Quyết định: `QUYET-DINH.md` B11.

**Số đo:** chưa có, chờ việc 6.

**Test** (chạy trên đúng bản commit, xuất từ index; không có việc 6): `tests/may_reels` 355/355, trong đó 4 test `.gitignore` chạy trong repo thật vì cần git. Toàn bộ repo: 3305 qua, 18 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết"). Đã sửa bản đồ file trong `TRANG-THAI.md` (tên file thiếu tiền tố `brand/<kênh>/` làm `test_tai_lieu` hỏng).

**Chưa làm / để sau:**
- Lệnh `sua` và `thay-canh` không chạy biên tập.
- Vòng sửa QA video không biên tập lại.
- Tab Câu hỏi khách (C1) chưa có nên `cau_hoi_khach` luôn rỗng.
- Mã VX và CTA theo mồi nhử để C2.

## 2026-11-21: bước M, trí nhớ dự án

**Mục tiêu:** phiên Claude Code mới đọc đúng trạng thái Máy Reels trong vài phút, không cần người dùng dán lại bối cảnh.

**Đã làm:**
- `TRANG-THAI.md` viết lại thành cửa vào duy nhất (122 dòng): Máy Reels là gì, bảng prompt (cả bộ C, lấy từ git log và `LO-TRINH.md`), các lệnh lấy từ `__main__.py`, bản đồ file, việc đang dở, lỗi đã biết, việc chờ người dùng, việc tiếp theo.
- Tách `KE-HOACH.md` (426 → 188 dòng), không bỏ nội dung, số mục và số câu cũ giữ nguyên để các chỗ trỏ trong code và cấu hình vẫn tìm được:
  - mục 6 (câu 1–19), 3.2, 4 và quyết định ở mục 9, 10 → `QUYET-DINH.md` (mới) mục A, B1–B5; thêm B6–B10 từ nhật ký (bộ C, dữ liệu chỉ ở máy, trạm, bố cục cảnh sơ đồ, dòng nguồn luật); "Việc còn chờ người dùng" → mục C;
  - mục 1, 7, 8, 9 (thiết kế, kết quả), 10 → nhật ký này, các mục 2026-11-15 đến 2026-11-19 (1);
  - còn lại ở `KE-HOACH.md`: sơ đồ luồng, 3.1, rủi ro 5.1–5.4, thêm 5.5 (phát hiện khi làm kho cảnh còn hiệu lực); bảng "mục cũ đi đâu" ở đầu file.
- `CLAUDE.md`: khối ngắn ở đầu (phát triển Máy Reels thì đọc `TRANG-THAI.md`, `NGUYEN-TAC.md` trước; `AGENT_GUIDE.md` chỉ khi đụng pipeline). Ghi vào "Điểm chạm upstream".
- `NGUYEN-TAC.md`: mục 7 thêm danh sách file chỉ có ở máy (có `LO-TRINH.md`) và lệnh kiểm trước khi commit; mục 9 thêm quy tắc kết thúc phiên; sửa các chỗ trỏ "KE-HOACH.md mục 6" sang `QUYET-DINH.md`. `HUONG-DAN-SU-DUNG.md` mục 10: danh sách tài liệu mới.
- Test `tests/may_reels/test_tai_lieu.py` (6): `TRANG-THAI.md` tồn tại, ≤ 200 dòng; đọc cây argparse của `__main__.py`, mọi lệnh lá có trong `TRANG-THAI.md`; mọi đường dẫn trong bản đồ file tồn tại (bỏ qua dòng "chỉ có ở máy" và `<KENH_GOC_DIR>`).
- Không sửa code đang chạy. Chú thích trong `.py`/`.yaml` vẫn ghi "KE-HOACH.md câu N"; `QUYET-DINH.md` giải thích chỗ đọc.

**Test:** `tests/may_reels` 312/312; toàn repo 3258 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, hỏng từ trước).

## 2026-11-20 (4): prompt C0, dữ liệu chiến lược nội dung

**Bối cảnh:** prompt C2b (biên kịch) cần `dinh-dang.yaml` và `doi-tuong.yaml` mà chưa có. Người dùng dừng C2b, chạy C0 trước.

**Đã làm:**
- File chiến lược đổi tên thành `docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`, đưa vào `.gitignore` (chỉ trên máy). Theo yêu cầu người dùng, `brand/*/ban-hang.yaml`, `doi-tuong.yaml`, `dinh-vi.yaml` cũng vào `.gitignore`; repo chỉ có bản mẫu `*.mau.yaml` cùng cấu trúc, không có dữ liệu thật.
- Dữ liệu `brand/vanxuan/`, mỗi mục có `trang_thai` (`gia_thuyet`/`da_xac_nhan`) và `ngay_cap_nhat`:
  - `doi-tuong.yaml`: 5 nhóm n1..n5 lấy nguyên bảng "Ai là người mua".
  - `dinh-vi.yaml`: lời hứa, 5 trụ, đối thủ so sánh, điều không làm.
  - `dinh-dang.yaml`: 16 định dạng = 11 định dạng mới + dòng "Luật (5 trụ cột)" tách thành 5 định dạng `luat-*`, mỗi cái trỏ `khung_nhip` có sẵn trong `san-xuat.yaml` (không chuyển khung nhịp ra khỏi `san-xuat.yaml`, code sản xuất không đổi). 11 định dạng mới có `nhip` cùng cấu trúc. Khóa `giong` (`may`/`thay`) theo nguyên tắc 5; `canh_can` khai báo thẻ/loại cảnh chấp nhận để đối chiếu kho.
  - `lich.yaml`: lịch 7 ngày, 3 mùa, `mua_dang_chay: truoc-tet` (2026-11-17 → 2027-02-05; ngày Tết cần người kiểm lại).
  - `ban-hang.yaml`: mẫu trống; máy chỉ ghi 2 số của bài Facebook cũ vào `cho_xac_nhan`.
- Schema `schemas/may-reels/{doi-tuong,dinh-vi,dinh-dang,lich,ban-hang}.schema.json`.
- `may_reels/chien_luoc.py` + lệnh `chien-luoc kiem-tra --kenh <mã> [--chi-tiet]`: thiếu file (báo tạo từ bản mẫu), lỗi schema (dừng kiểm tiếp), tham chiếu chéo (nhóm, định dạng, khung nhịp, mùa đang chạy), mục trống, ưu đãi hết hạn, định dạng chưa đủ số liệu đã xác nhận, định dạng thiếu cảnh (khớp `canh_can` với thẻ/loại của cảnh `dung_duoc` trong `kho_canh`), số chờ xác nhận, giả thuyết.
- `NGUYEN-TAC.md` mục 11 "Nguyên tắc nội dung" (7 nguyên tắc, bảng file dữ liệu) và bảng điểm chạm upstream (`.gitignore`, `schemas/`). `KE-HOACH.md`: bộ C thay Prompt 5 và 5A. `HUONG-DAN-SU-DUNG.md`: lệnh mới, cách tạo file thật từ bản mẫu.
- Test `tests/may_reels/test_chien_luoc.py` (13): file trong repo đúng schema, bản mẫu kiểm không lỗi, thiếu file riêng, tham chiếu sai, sai schema dừng, ưu đãi hết hạn, số liệu đã xác nhận, thiếu cảnh, `.gitignore` đúng, không đường dẫn tuyệt đối / số điện thoại trong file commit.
- `nap_kenh.py` và `brand.json` không đổi.

**Test:** `tests/may_reels` 305/305; toàn repo 3236 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, hỏng từ trước).

**Kết quả `chien-luoc kiem-tra --kenh vanxuan`:** cấu trúc đúng; 4 định dạng chưa làm được vì `ban-hang.yaml` trống; 8 định dạng thiếu cảnh (7 cần "thầy nói trước máy", 1 "học viên nói trước máy", "nhận bằng"); `ban-hang.yaml` 21 ô trống; `lich.yaml` 2 mùa chưa có ngày; 2 số chờ xác nhận; mọi mục còn là giả thuyết.

**Chưa làm:** chưa có code sản xuất nào dùng các file này (C1, C2 sẽ dùng). C2b tạm dừng.

**Bổ sung 2026-11-21 (bước 1 của LO-TRINH.md, trước khi commit C0):** `lich.yaml` mùa hè 2027-06-15 → 2027-08-31; mùa "quy định mới" tính theo sự kiện (30 ngày trước đến 30 ngày sau ngày luật có hiệu lực), ghi bằng khóa mới `theo_su_kien` (`lich.schema.json`), không có ngày cố định nên `chien-luoc kiem-tra` không báo ô trống (test `test_mua_theo_su_kien_khong_tinh_la_o_trong`). Người dùng điền `ban-hang.yaml` (chỉ trên máy): học phí A1, A, ưu đãi (chưa có ngày hết hạn nên máy chưa dùng), lý thuyết online, lịch thi, đánh giá Google Maps (số liệu chỉ ghi trong file trên máy); sân thực hành và "không phát sinh" còn là giả thuyết. `tests/may_reels` 306/306; toàn repo 3237 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, từ trước).

## 2026-11-20 (3): lệnh `dung-lai`

**Vì sao:** `sua` chỉ dựng lại khi agent đổi `ke_hoach.json`. Sửa mẫu (`hf.py`) thì kế hoạch giữ nguyên, `sua` báo "khong_doi"; vx-007 cần dựng lại hai lần chỉ vì đổi mẫu.

**Đã làm:**
- `may_reels/sua.py`: tách phần "dựng → chấm → đưa vào Hàng chờ → job cho_duyet" thành `_dung_cham_dua` (dùng chung cho `sua`, `thay-canh`, `dung-lai`). `_lam_lai(che_do="dung_lai")` không gọi agent, không sao lưu kế hoạch, luôn dựng lại. Hậu tố bản xem thử lấy theo `-vK` lớn nhất trên Hàng chờ (`_phien_ban_hang_cho`).
- `dung_lai()`: từ chối **trước khi dựng** nếu mã chưa có trên Hàng chờ hoặc có dòng đã Duyệt / Bỏ / đã đăng; ghi Nhật ký bước `dung_lai`.
- `python -m may_reels dung-lai --ma <mã>`: nhận mã rút gọn khớp đúng một dự án (`vx-007` → `vx-007-vong-xuyen`).
- Test `test_dung_lai_giu_ke_hoach_khong_goi_agent_va_tu_choi_khi_da_duyet`. `HUONG-DAN-SU-DUNG.md` có lệnh mới.
- Chạy thật cho vx-007: `cho_duyet`, bản xem thử `-v3`, điểm 70 (trần cảnh tạm), dòng nguồn chỉ còn ở s2 và s5.
- Test: `tests/may_reels` 292/292; toàn repo 3218 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, hỏng từ trước).
- Theo nhận xét của agent chấm (chữ mồ côi ở tiêu đề), thêm `text-wrap:balance` cho tiêu đề thẻ chữ; chưa dựng lại vx-007 cho thay đổi này.

## 2026-11-20 (2): dòng nguồn luật chỉ hiện khi cần

**Yêu cầu của người dùng:** trích dẫn luật chỉ nên xuất hiện khi cần; xuất hiện thường xuyên thì che cảnh chính.

**Trước:** mọi đoạn có `nguon_ids` đều có dòng nguồn trên thẻ chữ (vx-006: 5 cảnh, vx-007: 5 cảnh).

**Đã làm (`may_reels/dung/hf.py`):** dòng nguồn chỉ hiện ở đoạn mà **lời đọc đang trích luật** (`TRICH_LUAT`: luật, Điều n, khoản n, điểm x, nghị định, thông tư, quy chuẩn, QCVN) và **mỗi nguồn một lần** (lần trích đầu). Áp vào kế hoạch hiện có: vx-006 còn s2, s3; vx-007 còn s2, s5. `nguon_ids` vẫn giữ trong kế hoạch (bước chặn cứng dùng). Caption cả 3 nền tảng đã ghi nguồn đầy đủ (kiểm vx-007). `skills/may-reels/san-xuat-khong-hoi.md` ghi quy tắc mới và yêu cầu caption ghi nguồn đầy đủ. Test `test_dong_nguon_chi_hien_khi_loi_trich_luat_moi_nguon_mot_lan`.

**Lỗi trong lúc làm:** viết regex qua heredoc sinh ra ký tự điều khiển backspace (mã 0x08) thay cho hai ký tự gạch chéo ngược + b (ranh giới từ trong regex), regex không khớp gì. Chính câu này lần đầu cũng bị ghi sai y như vậy. Đã thay và rà mọi file `.py` của Máy Reels: không còn ký tự này.

**Test:** `tests/may_reels` 291/291 (không chạy lại toàn repo cho thay đổi này).

**Chưa áp vào video đang ở Hàng chờ:** vx-007 cần dựng lại; `sua` không dựng lại khi kế hoạch không đổi (xem `TRANG-THAI.md`).

## 2026-11-20: vx-007 sửa (hai xe chồng nhau, xe bị thẻ chữ che) và bố cục cảnh sơ đồ

**Yêu cầu:** người dùng thấy ở vx-007 cảnh s3, khoảng giây 13, hai xe chồng lên nhau. Người dùng ghi `ghi_chu_sua` (J8): xe 2 chờ ở nhánh trên bị thẻ chữ che, cho xuống nhánh dưới.

**Nguyên nhân và sửa (`may_reels/dung/hf.py`):**
- Vòng xuyến: xe đi trong vòng quay tới phía xe chờ rồi **đứng yên trong vòng**; xe chờ vào vòng và chạy đè lên nó. Sửa: xe trong vòng mờ đi (rời vòng) ngay sau khi qua nhánh xe chờ, trước khi xe chờ vào. Test `test_vong_xuyen_xe_trong_vong_ra_truoc_khi_xe_cho_vao`.
- Lần `sua` đầu (2026-11-20 20:26) **dựng hỏng** ở hyperframes check: số trên xe (42px) đè lên dòng nguồn luật (cảnh s5, ~19–20 s) và lên phụ đề (cảnh s3, xe 2 ở nhánh dưới). Gốc: sơ đồ chiếm y 480–1580 trong khi thẻ chữ chiếm y 452–~850 và phụ đề y 1050–1215; chữ 42px làm thẻ cao thêm.
- Người dùng chọn phương án "thu gọn chữ khi có sơ đồ". Đã làm:
  - Cảnh sơ đồ ngã tư / vòng xuyến: tiêu đề tối đa 80px; dòng phụ + nguồn luật hiện `SD_DOC_GIAY` = 2,6 s (tối đa nửa cảnh) rồi mờ; mọi chuyển động của xe dời sau mốc đó (`t0`).
  - Sơ đồ thu phóng bằng `viewBox` (`bo_cuc_so_do`) để vùng cần thấy (`TAM_VUNG`) nằm trong khoảng giữa đáy tiêu đề và phụ đề. Tọa độ bên trong không đổi nên `svgOrigin` của GSAP vẫn đúng. Đường kéo dài, điểm xuất phát/điểm ra đẩy xa theo tỉ lệ. Số trên xe giữ 42px và lệch 90px trên màn hình.
  - Vòng xuyến: số của xe chờ đặt bên cạnh xe (vuông góc nhánh), không đè lên làn trong vòng khi sơ đồ nhỏ.
  - Phụ đề của cảnh sơ đồ có class `thap` (top `PD_TOP_SO_DO` = 1075). Thử 1160 và 1090: hyperframes check báo phụ đề 2 dòng ra ngoài mép dưới (Reels/Shorts ~1248). `cham_diem.do_phu_de` đo cả vị trí này; regex nhóm phụ đề nhận class thêm.
  - Phụ đề: thêm khoảng cách giữa các từ (`margin 0 0.09em`) vì từ đang đọc phóng 1,08 làm "KHÔNG CÓ" trông dính liền (agent chấm phát hiện ở vx-007).
  - Test `test_canh_so_do_chu_mo_truoc_khi_xe_chay_va_so_do_vua_khoang_trong`.
- Kiểm trên bản sao HTML vx-007 (dữ liệu sau khi agent sửa kế hoạch): `hyperframes check --at-transitions` ok, 0 chữ ngoài vùng an toàn, 0 chữ đè chữ, tương phản 56/56; xem ảnh chụp các mốc 5–22 s.

**Chạy `sua` lần 2:** trả `ke_hoach.json` về bản trước lần sửa (`ke_hoach.truoc-sua-1.json`) để agent sửa lại theo ghi chú (nếu không, kế hoạch đã đổi từ lần 1 thì `sua` báo "khong_doi" và không dựng). Agent chọn cùng vị trí xe như lần 1 (s2: xe 1 nhánh dưới, xe 2 nhánh phải; s3: xe 2 nhánh dưới); chỉ khác câu mô tả cảnh. Kết quả: `cho_duyet`, điểm 70 (trần tổng cảnh tạm), kỹ thuật 96, chữ đạt 42px, không ra ngoài vùng an toàn.

**Lỗi phát hiện thêm:** sau khi `sua` thành công, cột `loi` của dòng fb_reels vẫn giữ "Sửa tự động không được…" của lần 1, vì `dua_vao_hang_cho` không bao giờ ghi cột `loi`. Sửa `may_reels/hang_cho.py`: bản video mới (`ban_moi`, dùng bởi `sua` và `thay-canh`) thì xóa `loi`. Test: `test_sua_dua_duyet_ve_cho_duyet_va_chan_khi_co_dong_da_duyet` đặt sẵn lỗi cũ và kiểm đã xóa. Đã xóa tay ô `loi` của vx-007 fb_reels trên Sheet thật (đúng việc mã mới sẽ làm).

**Test:** `tests/may_reels` 290/290; toàn bộ repo 3216 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, hỏng từ trước).

**Chưa làm:** lệnh dựng lại khi chỉ đổi mẫu; vx-007 đang ở Hàng chờ chưa có khoảng cách từ phụ đề mới.

## 2026-11-19 (2): cỡ chữ tối thiểu và vùng an toàn cho mọi chữ trên màn hình

**Yêu cầu:** mọi chữ trên màn hình, kể cả dòng nguồn luật và màn kết, đạt cỡ tối thiểu theo `skills/creative/short-form.md` và nằm trong vùng an toàn. Đọc cỡ từ nguồn HyperFrames, không đoán từ ảnh. Thiếu thì trừ điểm và ghi `canh_bao`. Sửa mẫu đồ họa nếu mẫu làm chữ nguồn luật nhỏ hơn mức đó.

**Đã làm:**
- `may_reels/co_chu.py` (mới):
  - `do_co_chu`: dựng cây phần tử của `hf/index.html` và `hf/compositions/*.html`, áp CSS trong `<style>` (bộ chọn `#id`, `.class`, thẻ, con cháu; độ ưu tiên; rule sau thắng), style inline, kế thừa từ cha, đơn vị px / em / rem / %. `<text font-size>` của SVG nhân tỉ lệ `width / viewBox`. Bỏ phần tử `data-layout-ignore`.
  - `chay_check` + `doc_ngoai_vung`: `npx hyperframes@<phiên bản> check --json --no-craft --no-contrast`, lấy cảnh báo `outside_safe_zone` (TikTok / Reels / Shorts trên layout thật trong trình duyệt).
- `may_reels/cham_diem.py`: thêm `do_dac.co_chu` và `do_dac.vung_an_toan` vào bằng chứng và `score.json`. Tiêu chí `phu_de`: có chữ dưới ngưỡng thì trần `khi_chu_nho`; có chữ ngoài vùng thì trần `khi_ngoai_vung`. Thêm một dòng `canh_bao`, ví dụ "Chữ dưới 42px: chữ cạnh logo 28px; nguồn luật 30px; màn kết 32-40px; …". Không chạy được hyperframes check thì chỉ ghi "Chưa đo được vùng an toàn", không trừ điểm. Có tham số `kiem_vung` để test thay hàm giả.
- `brand/vanxuan/rubric.yaml`: tiêu chí `phu_de` đổi tên thành "Phụ đề và chữ đọc được"; thêm `co_chu_toi_thieu: 42`, `khi_chu_nho: 5`, `khi_ngoai_vung: 5`. Code không viết cứng ngưỡng: `hf.py` đọc cùng số này qua `co_chu_toi_thieu()`.
- `skills/may-reels/cham-diem.md`: agent dùng `do_dac.co_chu` / `do_dac.vung_an_toan`, không ước lượng cỡ chữ từ ảnh.
- **Sửa mẫu đồ họa `may_reels/dung/hf.py`.** Khung nhịp (`san-xuat.yaml khung_nhip`) chỉ quy định thời lượng các đoạn, còn cỡ chữ nằm trong mẫu.
  - Nguồn luật 30 → 42px, rộng tối đa `XCW` = 660 (x ≤ 780). Lý do: ở 42px dòng này xuống 2 dòng, quá y 840, mà từ y 840 trở xuống TikTok chỉ an toàn tới x 780. hyperframes check đã báo lỗi này khi để rộng 768.
  - Dòng phụ thẻ chữ: cỡ nhỏ nhất 34 → 42px. Chữ cạnh logo 28 → 42px. Màn kết: dòng tên 34, "ZALO" 40, địa chỉ 32 → 42px.
  - Số trên xe của sơ đồ 34 → 42px (vòng tròn r 28 → 33). Nhãn "ĐƯỜNG ƯU TIÊN" 30 → 42px, tách 2 dòng để không vượt x 888.
  - Số trên xe chỉ hiện khi xe gần tới điểm dừng chờ, mờ đi trước khi xe chạy ra khỏi khung. Điểm xuất phát và điểm ra nằm ngoài vùng an toàn: trước đây hyperframes check đã báo 2 lần (báo cáo 2026-11-16), lấy mẫu dày thì báo 6 lần.
  - `text-wrap: balance` cho dòng phụ, nguồn luật, CTA và địa chỉ màn kết. Mỗi cụm địa chỉ giữa hai dấu phẩy không bị ngắt dòng.
- Test: `tests/may_reels/test_co_chu.py` (8 test: cascade, kế thừa, em, inline, SVG, gộp nhóm, mẫu đạt 42px, đọc ngưỡng từ rubric, đọc báo cáo hyperframes, áp trần và `canh_bao`, `score.json`). `conftest.py` thay hyperframes check bằng báo cáo rỗng. `test_html_so_do` kiểm nhãn đường ưu tiên 2 dòng và mọi chữ ≥ 42px.

**Số đo:**
- vx-006 bản đang ở Hàng chờ (mẫu cũ): 177 phần tử chữ, nhỏ nhất 28px, 13 nhóm dưới 42px.
- Mẫu mới, dựng lại HTML vx-006 trên **bản sao** (dự án thật không đổi): 0 chữ dưới 42px. `hyperframes check --at-transitions`: 0 chữ ngoài vùng an toàn, tương phản 55/55. Đã xem ảnh chụp các mốc 6 s, 12 s, 31,5 s.

**Test:** `tests/may_reels` 288/288; toàn bộ repo 3212 qua, 19 bỏ qua, 1 hỏng (`test_fal_resume_output_format[webp]`, hỏng từ trước, không liên quan).

**Chưa làm / bỏ dở:**
- `sua` cho vx-006: chưa chạy vì `ghi_chu_sua` trống (xem `TRANG-THAI.md`).
- Cảnh báo `content_overlap` của hyperframes check (số trên xe chồng lên thẻ chữ hoặc phụ đề khi xe đi qua) vẫn còn. Đây là chồng lớp có chủ ý (ghi trong `hf.py`) và không thuộc yêu cầu này.

## 2026-11-19 (1): kết luận so sánh model chép lời

Commit `fdc6e75`. Chạy nốt phép so sánh base / large-v3 / PhoWhisper trên 2 clip thật (bắt đầu 2026-11-17, xem mục đó). Kết luận: giữ PhoWhisper (`QUYET-DINH.md` B5). Chuyển nguyên văn từ `KE-HOACH.md` mục 10 ngày 2026-11-21:

**Có cần PhoWhisper không: ĐÃ kết luận (2026-11-19): giữ PhoWhisper làm mặc định.** Thử trên 2 clip thật có tiếng trong kho (`Nhieu_hoc_vien_nu_Cancanh.mp4`, `Video quay demo/snaptik...mp4`). Cả ba model đều chạy qua tool `transcriber` (`python -m may_reels.kho_chep_loi`) bằng CPU int8, lần lượt từng model, khi máy còn khoảng 12 GB RAM trống. Lần thử ngày 2026-11-17 bị dừng vì thiếu bộ nhớ; ngày 2026-11-19 chạy lại phần còn thiếu.

| Clip 1 (38 giây, khoảng 2,5 giây có lời) | Thời gian | Kết quả |
|---|---|---|
| `base` | 2,3 giây | "Đi theo đi lúc quen là chết hả hình? Đúng rồi" (sai từ) |
| `large-v3` | khoảng 25 phút (chạy cùng lúc với test, 2026-11-17) | "Đi thế không đến lúc quen là chết hết" |
| PhoWhisper-large | 79 giây | "đi thế lâu đến lúc quen là chết hết. / đúng. / mời." |
| Bản chép cũ trong kho (script của bộ kit) | — | "đi thế đến lúc quen là chết đấy…", kèm một câu bịa ở đoạn lặng |

| Clip 2 (78 giây, người quay nhắc học viên trên sân tập) | Thời gian | Kết quả |
|---|---|---|
| `base` | vài giây | 8 đoạn, sai nhiều từ: "Cái này sẽ đi qua khoan trình một ai thí luôn", "Bắt buộc và hảo luật tí ở ai bờ", "Tổng tích một phát vấn đô" |
| `large-v3` | 22 giây | **Bịa hoàn toàn:** một đoạn duy nhất 9–65 giây "Các bạn hãy đăng ký kênh để ủng hộ kênh của mình nhé." |
| PhoWhisper-large | 35 giây | "ngày sẽ đi hoàn chỉnh một bài thi luôn rồi … thời điểm này nó hơi hẹp nên là nhiều khi phải bắt buộc phải … một phát vẫn đỗ đấy thế là đúng rồi đấy bắt xe lại." |
| Bản chép cũ trong kho | — | Trùng từng chữ với PhoWhisper (script của bộ kit có lẽ cũng dùng PhoWhisper, nên đây không phải bằng chứng độc lập) |

- Kết luận: PhoWhisper sát lời thật nhất trên cả hai clip, không bịa câu ở đoạn lặng. `large-v3` bịa câu kiểu "đăng ký kênh" trên clip 2, nên nguy hiểm hơn `base` vì câu bịa đọc trơn tru, khó nhận ra là sai. `base` sai từ quá nhiều để làm trích lời.
- Chỉ có 2 clip, phần lớn là tiếng nói xa, lẫn tiếng xe. Kết luận này đủ để giữ mặc định, chưa đủ để nói PhoWhisper đúng với lời thầy nói trước máy. Nhãn `loi_noi` vẫn do agent đọc lại trước khi trích.
- Tốc độ: PhoWhisper chạy CPU mất 35–80 giây mỗi clip ngắn. Con số 25 phút của `large-v3` ngày 2026-11-17 là do chạy cùng lúc với test, không phải tốc độ thường của model.
- Model lớn chạy CPU tốn khoảng 3 GB bộ nhớ. `kho nap` vẫn chạy chép lời lần lượt từng file, nên không nên chạy cùng việc nặng khác.
- **Phát hiện thêm:** gọi `base` theo tên (`--model base`) báo lỗi `json.exception.type_error.305` trên clip 2. Nguyên nhân: bản `Systran/faster-whisper-base` trong cache Hugging Face thiếu `config.json` (cùng lỗi symlink `WinError 1314` ở trên). Bản ở `~/.cache/whisper-local/faster-whisper-base` đủ file và chạy được. Mặc định của máy không dùng `base`, nên không sửa gì.
- GPU vẫn chưa dùng được (thiếu CUDA 12). Không cần cài để dùng PhoWhisper với kho hiện tại.

## 2026-11-18: `kho nap` tự viết lại KHO.md

Commit `87e6ea5` (2026-11-19). Từ `KE-HOACH.md` mục 10, "Việc còn lại".

- ~~`KHO.md` chưa được `kho nap` cập nhật~~ **Đã làm (2026-11-18):** `may_reels/kho_md.py`. Sau mỗi `kho nap`, mục 1 (Tóm tắt) và mục 2 (Bảng cảnh) được sinh lại từ `index.json`, `nhan.json` và quyền hình (cùng hàm `doc_kho` của `nap_kenh.py`, nên "dùng được" khớp `brand.json`: 20/24). Bảng có thêm hai cột "Đã dùng" và "Trạng thái". Mục 3 (Độ phủ theo chủ đề) và mục 4 (Nên quay thêm) cần agent đánh giá, nên được giữ nguyên từ bản cũ, kèm dòng "Máy ghi chú" liệt kê các cảnh nạp sau lần agent viết. Lần đầu ghi đè bản do subagent viết thì bản đó được sao lưu thành `KHO.md.bak-<giờ>` (trên máy này: `KHO.md.bak-20261118-214159`). Đã sinh lại `KHO.md` thật của Vạn Xuân.
  - Mất so với bản subagent: các ghi chú tự do ở mục 1 (giấy phép Mixkit, cảnh trùng khung, nhóm "Stock (Mixkit)" riêng). Thông tin này vẫn còn trong `ghi_chu` của `nhan.json` và trong bản sao lưu.

## 2026-11-17: kho cảnh tự nạp và máy gợi ý cần quay (Prompt 6)

Commit `226ee1b` (2026-11-18). Từ `KE-HOACH.md` mục 10. Quyết định quyền hình: `QUYET-DINH.md` B4. So sánh model chép lời: mục 2026-11-19 (1).

**Mục tiêu:** quay xong thả file vào một thư mục là máy tự phân tích, gắn nhãn, đưa vào kho; và máy chủ động nói cần quay gì.

**Đã làm:**
- `python -m may_reels kho nap --kenh <mã>` (`may_reels/kho.py`): quét `canh-quay/moi-quay/` của thư mục kênh gốc. File chưa có trong `canh-quay/_kho/index.json` được:
  - đo thông số và tách cảnh bằng `audio_probe`, `scene_detect`, `frame_sampler`, ghép thành lưới `khung.jpg` có in mốc giây;
  - chép lời bằng tool `transcriber` (`may_reels/kho_chep_loi.py`, chạy bằng `MAY_REELS_PY_GIONG`);
  - gắn nhãn bằng agent (`skills/may-reels/gan-nhan-canh.md`), Python kiểm nhãn rồi mới thêm vào `nhan.json`.
- **Định dạng bản ghi giữ nguyên** như `scripts/nap_canh_quay.py` và subagent `phan-loai-canh` của bộ kit kênh. Mã cảnh tính bằng cùng thuật toán; test kiểm rằng mã của cảnh cũ trong kho thật không đổi. Chỉ thêm khóa vào bản ghi `index.json`: `ngay_nap`, `nap_luc`, `nap_boi`, `so_lan_dung`, `ngay_dung_gan_nhat`. Chạy thử phân tích trên clip thật `Học Viên Nam_Hạng A_ trung cảnh.mp4`: mọi thông số khớp bản ghi cũ, mất 1,5 giây. Agent gắn nhãn clip đó sát nhãn cũ (cùng đoạn dùng được 0–11 giây, cùng rủi ro mặt học viên và biển số); khác ở `loai` (THAO thay vì BROLL).
- **Quyền hình** (người dùng chốt 2026-11-17): `nap_kenh.py` chỉ áp điều kiện ngày và `bo_sung` của `quyen_hinh` cho cảnh có mặt người; cảnh không có mặt người dùng được ngay. Cảnh có mặt người lên tab **Quyền hình**; người chọn "Đồng ý" thì lần `kho nap` sau chép vào `quyen_hinh.bo_sung` của `channel.yaml`. `brand.json` của Vạn Xuân không đổi sau khi sửa (24 cảnh cũ giữ nguyên kết quả).
- **Số lần dùng cảnh:** `so_lan_dung`, `ngay_dung_gan_nhat` ghi vào `index.json` sau mỗi video vào Hàng chờ (`san-xuat`, `sua`, `thay-canh`) và sau mỗi `kho nap`. Đếm lại từ `projects/*/ke_hoach.json` mỗi lần, chỉ tính video đã dựng xong, nên không đếm trùng. `so_lan_dung_canh` (dùng cho cảnh báo và QA) đổi sang cùng cách đếm: trước đây đếm cả kế hoạch của job lỗi hay đang chờ quay. Agent sản xuất (`san-xuat-khong-hoi.md`) nhận thêm `ngay_dung_canh_gan_nhat`. Lần chạy đầu: 8/24 cảnh đã dùng, nhiều nhất `hoc-vien-tap-xe-a-ga` 3 lần.
- **Job chờ quay tự quay về sản xuất:** xem `NGUYEN-TAC.md` mục 5.
- `python -m may_reels kho thieu --kenh <mã>` (`may_reels/goi_y_quay.py`, `skills/may-reels/goi-y-quay.md`): danh sách quay gộp theo buổi vào tab Cần quay và bản văn bản để gửi Zalo. Chạy thử thật (`--thu`) với 2 chủ đề đã duyệt và 6 yêu cầu đang mở: 10 cảnh, 3 buổi (đường thật, sân tập, thầy nói trước máy), qua bước kiểm ngay lần đầu.
- Sheet: thêm tab Quyền hình và 9 cột vào cuối tab Cần quay (`sheet init` đã chạy trên Sheet thật).

**Phát hiện khi làm:**
- `lib/source_media_review.review_source_media` không dùng nguyên được cho kho: hàm ghi khung hình vào ngay thư mục chứa file gốc (`.source_review_frames_<tên>`), tức thư mục mới quay; và hàm đọc khóa `text` mà `transcriber` không trả về, nên phần tóm tắt lời nói luôn rỗng. `kho nap` gọi thẳng các tool mà hàm này dùng. Không sửa file upstream.
- `audio_probe` không đo phần hình. Kích thước khung (có tính cờ xoay của điện thoại) đo bằng ffprobe như `source_media_review` và `nap_canh_quay.py`.
- GPU của máy không dùng được cho faster-whisper: thiếu `cublas64_12.dll` (CUDA 12). `transcriber` tự chuyển sang CPU int8, nên chép lời model lớn chậm.
- Hugging Face không tạo được symlink trong cache trên Windows này (`WinError 1314`), nên tải model mới bị dở (`faster-whisper-large-v3` trong cache thiếu `model.bin`). Model dùng để so sánh được tải vào thư mục thường `~/.cache/whisper-local/`.


**Sống chung với script cũ của bộ kit:** `scripts/nap_canh_quay.py` quét cả `canh-quay/moi-quay/`. Nếu script cũ lập index trước, `kho nap` nhận các file đó về (ghi `ngay_nap` thật, gắn nhãn) chứ không bỏ qua; cảnh đã nạp bằng `kho nap` thì script cũ giữ nguyên vì `dau` không đổi. Hướng dẫn `canh-quay/DOC-TOI.md` trong thư mục kênh gốc vẫn chỉ tới script cũ: máy không sửa file đó.

- Mục 6 của yêu cầu (đường dẫn tuyệt đối trong `brand.json`) đã xử lý từ 2026-11-15 (`KE-HOACH.md` mục 5.1): `brand.json` không còn đường dẫn tuyệt đối, thư mục kênh gốc khai báo một lần bằng `KENH_GOC_DIR` trong `.env`. Lần này không đổi gì thêm. Còn lại: lịch sử git (commit `dc52b79`) vẫn chứa bản cũ.

## 2026-11-16: chấm điểm nội dung theo rubric

Commit `ef6232b`, `3ed17ea`. Từ `KE-HOACH.md` mục 9. Bốn quyết định của máy chờ người xác nhận: `QUYET-DINH.md` B3.

**Vì sao đổi:** `diem_qa` cũ (`DIEM_TRU` trong `may_reels/dung/kiem_tra.py`) chỉ đo kỹ thuật, nên video có nội dung yếu vẫn được 91. Từ nay:

- **`diem_ky_thuat`:** giữ nguyên công thức cũ, chỉ đổi tên. Không còn mục `canh_tam`, vì cảnh tạm đã được tính trong tiêu chí "Chân thực".
- **`diem_qa`:** tổng rubric `brand/<kenh>/rubric.yaml` (100 điểm, 8 tiêu chí). Trọng số, ngưỡng, trần và từ khóa đều nằm trong file này, code không viết cứng.
- **Chia việc:**
  - Python (`may_reels/cham_diem.py`) đo những gì tất định: nhịp, tỉ lệ thời lượng cảnh thật, phụ đề, thương hiệu, CTA, mốc chữ đầu, độ đứng yên của 3 giây đầu.
  - Agent (`claude -p`, `skills/may-reels/cham-diem.md`) chấm hook, độ đúng và giá trị, phụ đề, CTA từ **bằng chứng của bản đã render**: khung hook, lưới khung, lời PhoWhisper chép từ âm thanh cuối. Agent không chấm trên kịch bản.
  - Python áp trần lên điểm agent khi đo được lỗi cứng, rồi áp trần tổng. Kết quả ghi `renders/score.json` (`schemas/may-reels/score.schema.json`).
- **Chặn cứng** (không vào Hàng chờ, job sang `loi`) khi gặp một trong ba trường hợp, tất cả đều kiểm tra trên bản đã render:
  - cụm từ cấm hoặc câu sáo đã chốt, trong lời nghe được và chữ trên màn hình, kể cả viết không dấu;
  - số hoặc số hiệu luật ngoài `y_chinh`/`nguon_doi_chieu`;
  - tài sản ngoài kho kênh, brand hoặc sơ đồ được phép.
- **Vòng sửa:** dùng lại vòng phản hồi của `san_xuat.py`, nhưng nội dung phản hồi là lý do trừ điểm nội dung, nặng nhất trước. Tối đa 2 vòng. Vẫn dưới ngưỡng thì cột `canh_bao` ghi "Dưới ngưỡng (điểm/ngưỡng)" và 2 lý do nặng nhất; cột này tối đa 3 dòng.
- **Hiệu chỉnh:** tab Hàng chờ có thêm hai cột của người là `diem_cua_toi` và `nhan_xet`.
  - Lệnh `cham-lai` chấm lại video mà không dựng lại.
  - Lệnh `hieu-chinh` so điểm của máy với điểm của người, rồi đề xuất sửa `rubric.yaml`; lệnh này không tự sửa.

**Chạy thật ngày 2026-11-16** (`cham-lai`, `hieu-chinh`):

| Video | QA cũ (kỹ thuật) | QA mới | Hook | Đúng | Nhịp | Chân thực | Phụ đề | Thương hiệu | CTA | Kỹ thuật | Chặn |
|---|---|---|---|---|---|---|---|---|---|---|---|
| vx-005-a1-xe-150cc | — | bỏ qua | | | | | | | | | không có `ke_hoach.json` (dựng trước khi có máy) |
| vx-006-giao-nhau-khong-bao-hieu | 91 | 76 | 17/20 | 13/15 | 7/10 | 5/15 (43% cảnh thật) | 7/10 | 10/10 | 8/10 | 9,1/10 | Điều 22, khoản 2 |
| vx-007-vong-xuyen | 87 | 70 (trần tổng) | 18/20 | 12/15 | 7/10 | 5/15 (40% cảnh thật) | 8/10 | 10/10 | 10/10 | 8,7/10 | Điều 22, khoản 2, 3 |

- **Cả hai video bị chặn vì cùng một lý do:** `nguon_doi_chieu` của chủ đề chỉ ghi "Luật 36/2024/QH15 (điều về đi qua nơi giao nhau)", không ghi số điều. Agent đã mở link và trích nguyên văn Điều 22. Có hai cách gỡ, **người dùng chọn**:
  - ghi rõ điều khoản vào `nguon_doi_chieu` trong `chu-de.md` rồi nạp lại kho;
  - bật `nguon_luat_da_mo` trong `rubric.yaml`.
- **Agent tìm ra lỗi thật mà điểm kỹ thuật bỏ sót:** ở vx-006, khoảng giây 20, sơ đồ đè lên thẻ chữ làm chữ bị cụt ("Có xe thì n").
- **Thời gian mỗi video:** agent khoảng 36 giây (claude báo khoảng 0,45 USD), cộng thời gian PhoWhisper chép lời âm thanh cuối. Lời chép được lưu theo sha1 của video, nên lần chấm lại sau không phải chép nữa.
- **Sau khi sửa `nguon_doi_chieu`** (cùng ngày, xem `QUYET-DINH.md` câu 14), chạy lại `cham-lai`:
  - **Kết quả:** vx-006 và vx-007 hết bị chặn. vx-006 được 72, vx-007 được 70 (trần tổng vì cảnh tạm). Cả hai vẫn dưới ngưỡng 75; lý do nặng nhất là "Chân thực", với 43% và 40% cảnh thật.
  - **Điểm agent của vx-006 dao động giữa các lần chấm** (76 → 79 → 72). Lần cuối, agent cho "Đúng" 7/15 vì cho rằng sơ đồ ở giây 20,2 vẽ sai thứ tự xe. Điều này **chưa xác minh**: người cần xem khung đó. Độ dao động khoảng ±7 điểm cho thấy nên dùng `hieu-chinh` khi đã có `diem_cua_toi`, trước khi tin điểm sát ngưỡng.
- **`hieu-chinh`:** chưa có `diem_cua_toi` nào nên chưa đề xuất. Hai cột này được `sheet init` thêm vào Sheet ngày 2026-11-16, vì trên Sheet thật lúc đó chưa có.

## 2026-11-15 (2): dựng một video từ đầu đến cuối (Việc 1)

Commit `b4451d4`. Từ `KE-HOACH.md` mục 8.

- **Dự án:** `projects/vx-005-a1-xe-150cc`, cùng chủ đề với vx-demo-01, dựng bằng manifest `pipeline_defs/may-reels.yaml`.
  - Có checkpoint ở cả 7 stage.
  - Có file `renders/final.mp4`: 1080×1920, 30 fps, 49,3 giây, −14,0 LUFS.
  - `final_review` đạt `pass`.
  - Stage publish chỉ dùng `export_bundle` và dừng ở `awaiting_human`.
  - Cổng idea ghi `human_approved=True` kèm tham chiếu ô `duyet_chu_de = "Làm"` trên Sheet.
- **Thời gian từng stage** (lần chạy cuối):

  | Stage | Thời gian |
  |---|---|
  | idea | 2,4 giây |
  | script | 0,1 giây |
  | scene_plan | 0,1 giây |
  | assets | khoảng 12 phút ở lần sinh giọng thật (29 lần sinh và nghe lại); 31 giây khi dùng lại cache |
  | edit | 0,2 giây |
  | compose | khoảng 2,5 phút (render 147 giây) |
  | publish | 0,2 giây |

- **Các chỗ agent còn muốn hỏi người**, kèm cách đã xử lý:
  1. Chọn runtime: chốt trong `san-xuat.yaml`.
  2. Chọn giọng: chốt trong `san-xuat.yaml`.
  3. Có nhạc không: chốt trong `san-xuat.yaml`.
  4. Đổi cảnh trùng ở s6: thành luật "không lặp cảnh trong video".
  5. Thời lượng giữ màn kết: thành `khung_hinh.giu_man_ket_giay`.
  6. Bản giọng nào đúng: PhoWhisper nghe lại, thay cho việc người nghe.
  7. Âm lượng sau khi HyperFrames trộn lại (−12,2 LUFS): thêm bước chuẩn hóa sau render.
  8. Hook dài 6,2 giây: thành luật "hook trong 3 giây". Luật này có sau khi `vx-005` đã dựng, nên `vx-005` vẫn vi phạm.
- **Đã sửa trong quá trình dựng:**
  - Giọng VieNeu đôi khi nuốt số hoặc đọc sai, nên bước sinh giọng có nghe lại tự động (`may_reels/giong.py`).
  - Bản đầu ghi checkpoint compose là `completed` dù `final_review` = `revise`; đã sửa thành chỉ ghi `completed` khi kết quả là `pass`.
- **Kiểm tra bộ dựng chung `may_reels/dung/`:** dự án `projects/vx-thu-may` (cùng nội dung, hook rút còn 2,7 giây) đạt điểm QA 100, dài 45,3 giây.

## 2026-11-15 (1): hiện trạng lúc lập kế hoạch, kết quả test nền

Commit `30b50c9`, `0c73d66`. Từ `KE-HOACH.md` mục 1 và 7.

**Hiện trạng ngày 2026-11-15, trước khi viết code Máy Reels:**

| Thành phần | Hiện trạng |
|---|---|
| Dữ liệu kênh | `brand/vanxuan/brand.json` do `tools_local/nap_kenh.py` sinh ra. Có 16 chủ đề (`chu_de`, 4 đã làm, 12 chưa làm), 24 cảnh trong kho (`kho_canh`, 20 dùng được: 8 video, 12 ảnh), quy tắc cấm (`cam`), quyền hình (`quyen_hinh`), CTA, hashtag theo nền tảng, màu, font, logo. |
| Dự án mẫu | `projects/vx-demo-01/` (bị gitignore, chỉ có trên máy này). Dùng pipeline `hybrid` + HyperFrames + giọng VieNeu "Hải Đăng" + PhoWhisper, chi phí 0 đ. Chỉ có checkpoint của `idea`, `script`, `scene_plan`. Thư mục `renders/` đang trống. **Chưa có bản dựng cuối nào được kiểm chứng từ đầu đến cuối.** Các bước sau `scene_plan` chạy bằng script riêng trong thư mục dự án, không ghi checkpoint. |
| Giọng đọc | `nhat-ky.md` của vx-demo-01 ghi "TTS 0/19 trong registry". VieNeu đang được gọi thẳng từ script, không phải tool của registry. |
| Publisher | Chỉ có `tools/publishers/export_bundle.py` (đóng gói tại máy, không tải lên đâu). |
| Số liệu sau khi đăng | Chưa thấy tool nào trong `tools/` lấy lượt xem hay tương tác từ các nền tảng (đã tìm "analytics", "insights", "view_count"; chỉ thấy trong tool phân tích video tham khảo). |

**Test nền:**

Chạy ngày 2026-11-15 bằng `.\.venv\Scripts\python.exe -m pytest -q` trên nhánh `kenh-vanxuan` (commit `dc52b79` cộng hai tài liệu này). Phải cài `requirements-dev.txt` trước, vì `.venv` chưa có pytest.

**2913 passed, 19 skipped, 2 failed** (khoảng 8 phút). Hai test hỏng đều nằm ở code upstream mà nhánh này không sửa:

- `tests/lib/test_terminal_frame_pacing.py::test_trace_matches_the_actual_terminal_scene_cursor`
- `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]`: file `.webp` bị gắn nhãn `data:image/png`.

Chưa tìm nguyên nhân, và chưa xác minh hai test này có hỏng trên máy khác hay không. Code của Máy Reels không được làm tăng con số 2 này.

Các test quét tài liệu (`test_skill_execute_examples.py`, `test_phase0_contracts.py`, `test_taste_governance_contracts.py`) đều qua sau khi thêm hai tài liệu.

**Lần chạy sau khi sửa `nap_kenh.py` (2026-11-15):**

Chạy bằng `tools_local\py.cmd -m pytest -q` (có `PYTHONUTF8=1`):

**2925 passed, 19 skipped, 1 failed** (khoảng 9 phút).

- Vẫn hỏng: `test_checkpoint_only_resume_preserves_media_format[webp]`, giống lần trước.
- Lần này qua: `test_trace_matches_the_actual_terminal_scene_cursor`. Chưa rõ nó qua là nhờ `PYTHONUTF8=1` hay vì test lúc qua lúc hỏng, nên **chưa xác minh**.
- Số test qua tăng 12 so với lần trước. Trong đó có 9 test mới ở `tests/may_reels/` và 1 test vừa nêu. Chưa đối chiếu nguồn gốc của 2 test còn lại.
