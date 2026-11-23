# Máy Reels: trạng thái

**Cửa vào duy nhất.** Đọc file này đầu mỗi phiên phát triển, rồi `NGUYEN-TAC.md`. Cập nhật trước mỗi commit (quy tắc kết thúc phiên, `NGUYEN-TAC.md` mục 9).

Máy Reels biến nhánh `kenh-vanxuan` của OpenMontage thành máy tự sản xuất video dọc 9:16 (Facebook Reels, YouTube Shorts, TikTok) cho từng kênh trong `brand/`.
Agent (`claude -p`) chỉ viết kế hoạch video; Python dựng (HyperFrames, giọng VieNeu), chấm điểm theo rubric và đưa vào Hàng chờ trên Google Sheet.
Người chỉ duyệt ở hai chỗ trên Sheet: duyệt chủ đề (cổng A) và duyệt video trước khi đăng (cổng B).

Đọc thêm: [NGUYEN-TAC.md](NGUYEN-TAC.md) (nguyên tắc), [QUYET-DINH.md](QUYET-DINH.md) (quyết định đã chốt), [KE-HOACH.md](KE-HOACH.md) (kế hoạch, rủi ro), [NHAT-KY-PHAT-TRIEN.md](NHAT-KY-PHAT-TRIEN.md) (lịch sử), `CHIEN-LUOC-NOI-DUNG.md` (chiến lược nội dung, chỉ có ở máy, không commit). Cách dùng cho người vận hành: `HUONG-DAN-SU-DUNG.md` mục 10.

Thứ tự các bước tiếp theo: xem LO-TRINH.md (chỉ có ở máy).

## Cập nhật lần cuối: 2026-11-23 (sửa điểm 0 giả khi sản xuất; thêm Điều 89 khoản 3 điểm a)

## Các prompt đã chạy

Lấy từ git log và `LO-TRINH.md`. Chi tiết từng phiên: `NHAT-KY-PHAT-TRIEN.md`.

| Prompt | Ngày | Commit | Kết quả |
|---|---|---|---|
| 0: Khảo sát, chốt nguyên tắc | 2026-11-15 | `30b50c9`, `0c73d66` | `NGUYEN-TAC.md`, `KE-HOACH.md`; câu 1–19 trong `QUYET-DINH.md`; bỏ đường dẫn tuyệt đối khỏi `brand.json` |
| 1: Sheet điều khiển | 2026-11-15 | `189f521` | `sheet init`, tab Ý tưởng / Hàng chờ / Cần quay / Nhật ký; schema job |
| 2: Đăng bài | 2026-11-15 | `0772c9b` | Code publisher có, **chưa đăng thật**; để sau, các bước khác không đụng publisher |
| 3A: Sản xuất không cần hỏi | 2026-11-15, 16 | `b4451d4`, `fe5428a`, `82aff7f` | `san-xuat`, `dung`, cảnh tạm bằng sơ đồ, `thay-canh` |
| Phụ: Tối ưu dung lượng | 2026-11-16 | `dd58d53` | `dung-luong`, `don-dep`, bản xem thử 720p |
| 4A: Chấm nội dung, hiệu chỉnh | 2026-11-16 | `ef6232b` | `rubric.yaml`, chặn cứng, `cham-lai`, `hieu-chinh` |
| Phụ: Nguồn luật | 2026-11-16, 17 | `3ed17ea`, `3b2d04b`, `89e50dd` | `nguon-luat`, `ap-dung`; tới mức khoản |
| 6: Kho cảnh và gợi ý quay | 2026-11-18, 19 | `226ee1b`, `87e6ea5`, `fdc6e75` | `kho nap`, `kho thieu`, KHO.md tự sinh; giữ PhoWhisper |
| Kiểm tra cỡ chữ | 2026-11-19, 20 | `9b04abf`, `7a0e086`, `bdbd47c` | Chữ ≥ 42px, vùng an toàn; dòng nguồn chỉ khi trích luật |
| Phụ: `dung-lai` | 2026-11-20 | `e8f1ca4` | Dựng lại theo mẫu, giữ kế hoạch |
| 5, 5A | — | — | Bỏ, thay bằng bộ C (`QUYET-DINH.md` B6) |
| C0: Nạp chiến lược | 2026-11-21 | `e6c9288` (.gitignore `81798b7`) | `dinh-dang.yaml`, `lich.yaml`, schema, `chien-luoc kiem-tra` |
| M: Trí nhớ dự án | 2026-11-21 | `daa8eeb` | File này, `QUYET-DINH.md`, tách `KE-HOACH.md`, `test_tai_lieu.py` |
| C0b-1: Trạm phân tích | 2026-11-20 | repo riêng | Xong phần thử nghiệm (ở repo `tram-phan-tich`) |
| C2b: Bộ biên kịch | 2026-11-21, 2026-11-23 | `6d0f07f` (việc 1–5), `bdecc1b` (việc 6), `358ad96` (sửa điểm 0 giả khi sản xuất) | `bien-kich.md`, `bien-tap.md`, `may_reels/bien_tap.py`; thư viện hook, giọng nói, giữ chân, rubric kịch bản; 16 kịch bản mẫu (đã duyệt 2026-11-23). Việc 6: `bien-kich so-sanh` trên vx-005/006/007, điểm kịch bản cũ 59/73/79 → mới 86/90/84, biên tập thêm ~51 s mỗi video |
| C1: Chủ đề theo nhóm, lịch tuần | — | — | chưa chạy |
| C2: Kịch bản chuyển đổi, mã VX | — | — | chưa chạy |
| C3: Video giọng thật của thầy | — | — | chưa chạy |
| C0b-2: Nối kết quả trạm | — | — | chưa chạy |
| C4: Mẫu trả lời Zalo | — | — | chưa chạy |
| C5: Xem lại hằng tuần | — | — | chưa chạy |
| C6: Trường nguồn trong Odoo | — | — | chưa chạy (repo Odoo, không thuộc repo này) |
| 7: Lịch chạy tự động | — | — | chưa chạy |

**Trạm phân tích video** là repo riêng `tram-phan-tich`. OpenMontage không cài rea-video, không gọi trạm, chỉ đọc kết quả ở `<KENH_GOC_DIR>/vanxuan/mau/ket-qua/`.

## Lệnh `python -m may_reels`

Chạy bằng `tools_local\py.cmd -m may_reels …` (có `PYTHONUTF8=1`). Chi tiết tham số: `--help` hoặc `HUONG-DAN-SU-DUNG.md`.

- `sheet init`: tạo tab và cột còn thiếu trên Sheet.
- `sheet nap-chu-de --kenh <mã>`: đẩy chủ đề của kênh lên tab Ý tưởng.
- `hang-cho them`: đưa một video có sẵn vào Hàng chờ.
- `dang [--that]`: đăng các dòng đã Duyệt (mặc định chạy thử; chưa đăng thật lần nào).
- `dung --du-an <mã>`: dựng một dự án từ `ke_hoach.json`.
- `san-xuat --kenh <mã>`: agent viết kế hoạch, dựng, chấm, đưa vào Hàng chờ.
- `sua`: sửa và dựng lại các video chọn Sửa trên Hàng chờ.
- `dung-lai --ma <mã>`: dựng lại theo mẫu hiện tại, giữ kế hoạch.
- `thay-canh`: thay cảnh tạm bằng cảnh thật khi Cần quay ghi "Đã quay".
- `chien-luoc kiem-tra --kenh <mã>`: kiểm dữ liệu chiến lược của kênh.
- `bien-kich so-sanh --ma <mã video> [--ma ...]`: viết lại kịch bản video đã làm bằng bộ biên kịch (chỉ kế hoạch), chấm cạnh bản cũ, báo cáo ở `projects/_may_reels/so-sanh/BAO-CAO.md`.
- `cham-lai --kenh <mã>`: chấm lại video trong Hàng chờ theo rubric.
- `hieu-chinh --kenh <mã>`: so điểm máy với `diem_cua_toi`, đề xuất sửa rubric.
- `nguon-luat [ap-dung] --kenh <mã>`: máy đề xuất điều khoản luật; `ap-dung` chép nguồn đã xác nhận.
- `kho nap --kenh <mã>`: nạp clip mới quay vào kho cảnh.
- `kho thieu --kenh <mã>`: danh sách cần quay theo buổi.
- `dung-luong`: báo dung lượng media (chỉ đọc).
- `don-dep [--that]`: dọn media theo trạng thái duyệt.
- `dang-nhap drive|youtube`: đăng nhập OAuth Google một lần.

## Bản đồ file

- `may_reels/`: code Python của máy (Sheet, job, sản xuất, chấm điểm, kho, nguồn luật, đăng, dọn dẹp). Điểm vào `__main__.py`.
- `may_reels/dung/`: bộ dựng tất định (kiểm kế hoạch, giọng, cảnh, HyperFrames `hf.py`, tự kiểm).
- `skills/may-reels/`: skill cho agent `claude -p` (sản xuất, biên kịch, biên tập, chấm điểm, tra nguồn luật, gắn nhãn cảnh, gợi ý quay).
- `may_reels/bien_tap.py`, `may_reels/so_sanh_kich_ban.py`: biên tập kịch bản trước khi dựng (máy kiểm chữ, biên tập riêng, điểm), so sánh trước sau.
- `brand/<kênh>/hook.yaml`, `brand/<kênh>/giong-noi.yaml`, `brand/<kênh>/giu-chan.yaml`, `brand/<kênh>/rubric-kich-ban.yaml`: thư viện tay nghề của bộ biên kịch (sửa tay).
- `brand/<kênh>/kich-ban-mau/`: kịch bản mẫu mỗi định dạng; chỉ mẫu `da_duyet` được dùng làm ví dụ.
- `docs/may-reels/tham-khao/marketingskills/`: nguồn tham khảo (MIT, ghim commit), không phải skill.
- `brand/<kênh>/`: dữ liệu từng kênh. `brand.json` do `tools_local/nap_kenh.py` sinh; cấu hình `san-xuat.yaml`, `rubric.yaml`, `dang-bai.yaml`, `dinh-dang.yaml`, `lich.yaml`; bản mẫu `*.mau.yaml`.
- `brand/<kênh>/ban-hang.yaml`, `doi-tuong.yaml`, `dinh-vi.yaml`: dữ liệu kinh doanh thật (chỉ có ở máy, không commit).
- `brand/<kênh>/_local/`: toàn văn context của kênh (chỉ có ở máy, không commit).
- `schemas/may-reels/`: schema JSON (kế hoạch video, job, điểm, dữ liệu chiến lược).
- `tests/may_reels/`: test của Máy Reels.
- `tools/publishers/`: publisher Facebook Reels, YouTube Shorts, TikTok bàn giao; `export_bundle.py` của upstream.
- `pipeline_defs/may-reels.yaml`: manifest chạy không dừng (`QUYET-DINH.md` B1).
- `tools_local/`: `nap_kenh.py` (sinh `brand.json`), `py.cmd`.
- `docs/may-reels/`: tài liệu (file này, nguyên tắc, quyết định, kế hoạch, nhật ký, cài đặt Google, cài đặt đăng bài, API).
- `docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`, `docs/may-reels/LO-TRINH.md`: chiến lược nội dung, thứ tự các bước (chỉ có ở máy, không commit).
- `.env`, `secrets/`: khóa, token, service account (chỉ có ở máy, không commit).
- `<KENH_GOC_DIR>/<kênh>/`: thư mục kênh gốc ngoài repo (kho cảnh `canh-quay/`, `mau/`).

## Đang dở

- Nguồn `a1-xe-150cc` đã thêm Điều 89 khoản 3 điểm a (chu-de.md, brand.json, kết quả tra nguồn); tab Ý tưởng trên Sheet còn `nguon_de_xuat` cũ, ô Ý chính chưa có ý đổi sang hạng A.
- **Lời kêu gọi mời học hạng A** (người duyệt sửa vx-005 trong bản so sánh) chưa có trong danh sách `cta` của kênh; thêm vào thư mục kênh gốc trước khi dựng.
- **vx-007 "Chờ duyệt"**, bản `vx-007-vong-xuyen-v3.mp4` (2026-11-20, `dung-lai`): điểm 70 (dưới 75) vì trần tổng "phần lớn là cảnh tạm" (40% cảnh thật); kỹ thuật 96. `text-wrap:balance` cho tiêu đề thêm **sau** khi dựng v3.
- vx-006: người dùng đã đổi sang "Duyệt" (2026-11-20); dựng ngày 2026-11-16 theo mẫu cũ (chữ dưới 42px).
- Dữ liệu C0 chưa có code sản xuất nào dùng (sản xuất vẫn theo `san-xuat.yaml khung_nhip`); C1, C2 sẽ dùng.

## Lỗi đã biết

- Test upstream hỏng từ trước, không liên quan Máy Reels: `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]`.
- Điểm agent chấm dao động khoảng ±7 giữa các lần (vx-006: 76 → 79 → 72); cần `diem_cua_toi` để `hieu-chinh`.
- GPU không dùng được cho faster-whisper (thiếu CUDA 12), chép lời chạy CPU; Hugging Face không tạo symlink cache (`WinError 1314`). Xem `KE-HOACH.md` mục 5.5.
- Cảnh báo `content_overlap` của hyperframes check (số trên xe đè thẻ chữ khi xe đi qua) còn, là chồng lớp có chủ ý.
- Lịch sử git (commit `dc52b79`, đã lên GitHub) còn `brand.json` có đường dẫn tuyệt đối. Không viết lại lịch sử khi chưa hỏi.

## Chờ người dùng

1. `brand/vanxuan/ban-hang.yaml` (chỉ có ở máy): còn thiếu khoản gồm/không gồm, ngày hết hạn ưu đãi, xác nhận sân thực hành và câu "không phát sinh", số buổi, quy trình, giấy tờ, lịch khai giảng, mồi nhử, người đồng ý lên hình. Chặn một phần C1, và C2, C4.
2. Kho cảnh chưa có "thầy nói trước máy" (7 định dạng cần), "học viên nói trước máy", "nhận bằng". Chặn C3 phần 2.
3. ~~Duyệt 16 kịch bản mẫu C2b~~: người dùng duyệt cả 16 ngày 2026-11-23 (`da_duyet`).
4. Facebook: `fb_reels.page_id` trong `brand/vanxuan/dang-bai.yaml` và token trong `.env` (`CAI-DAT-DANG-BAI.md` mục A). YouTube: `kenh_id`, `made_for_kids`, `contains_synthetic_media`. Giờ đăng, số video mỗi ngày (`QUYET-DINH.md` câu 6).
5. Giấy phép thương mại của VieNeu và PhoWhisper: chưa xác minh.
6. Bốn quyết định chấm điểm của máy (`QUYET-DINH.md` B3); gợi ý tự động hóa (2026-11-20) chưa chọn.
7. vx-006: xem khung giây 20,2 (agent cho rằng sơ đồ vẽ sai thứ tự xe). Đổi vx-006 sang Sửa kèm ghi chú nếu cần.
8. Nghe 0–16 s của `canh-quay/Nhieu_hoc_vien_nu_Cancanh.mp4` (thầy có nói "vừa xoay bánh đi vòng quay lại chứ"?).
9. Thả 15–20 video mẫu vào `<KENH_GOC_DIR>/vanxuan/mau/video/` và chạy trạm (chặn C0b-2).

## Việc tiếp theo

C1 (chủ đề theo nhóm và lịch tuần), rồi C2, C3 phần 1. Thứ tự đầy đủ và điều kiện từng bước: LO-TRINH.md (chỉ có ở máy).

## Test

- 2026-11-23 (sửa điểm 0 giả): `tests/may_reels` 360/360. Toàn bộ repo: 3309 qua, 19 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết").
- 2026-11-23 (C2b việc 6): `tests/may_reels` 358/358. Toàn bộ repo: 3307 qua, 19 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết").
- 2026-11-21 (C2b việc 1–5): `tests/may_reels` 355/355. Toàn bộ repo: 3305 qua, 18 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết").
- 2026-11-21 (bước M): `tests/may_reels` 312/312. Toàn bộ repo: 3258 qua, 19 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết").
- 2026-11-21 (C0 commit): `tests/may_reels` 306/306. Toàn bộ repo: 3237 qua, 19 bỏ qua, 1 hỏng (test upstream ở "Lỗi đã biết").
- 2026-11-20 (sau `dung-lai`): `tests/may_reels` 292/292. Toàn bộ repo: 3218 qua, 19 bỏ qua, 1 hỏng.
