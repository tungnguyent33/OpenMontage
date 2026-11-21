# Máy Reels: trạng thái

Đọc file này đầu mỗi phiên phát triển. Chi tiết thiết kế ở `KE-HOACH.md`, nguyên tắc ở `NGUYEN-TAC.md`, lịch sử thay đổi ở `NHAT-KY-PHAT-TRIEN.md`. Cập nhật file này trước mỗi commit.

## Cập nhật lần cuối: 2026-11-21 (C0 commit)

Thứ tự các bước tiếp theo: xem LO-TRINH.md (chỉ có ở máy).

**File chỉ có trên máy, không có trên GitHub** (bị `.gitignore`, xem `NGUYEN-TAC.md` mục 11):
- `docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`: chiến lược nội dung, nguồn sự thật về nội dung (đổi tên từ "Chiến lược nội dung ra học viên – Đào tạo lái xe Vạn Xuân.md" ngày 2026-11-20).
- `brand/vanxuan/doi-tuong.yaml`, `dinh-vi.yaml`, `ban-hang.yaml`: dữ liệu kinh doanh thật. Repo chỉ có bản mẫu `*.mau.yaml`; máy khác phải tạo từ bản mẫu.

File này được tạo ngày 2026-11-19. Trước đó trạng thái chỉ nằm trong `KE-HOACH.md` (các mục "Việc còn lại / chưa làm").

### Đã có và chạy được

| Phần | Lệnh / file |
|---|---|
| Ý tưởng, Sheet | `sheet init`, tab Chủ đề / Hàng chờ / Cần quay / Quyền hình / Nhật ký |
| Nguồn luật | `nguon-luat`, `ap-dung` (máy đề xuất, người xác nhận; ưu tiên văn bản hợp nhất) |
| Sản xuất không hỏi | `san-xuat` (agent viết ke_hoach.json, pipeline HyperFrames, giọng VieNeu) |
| Chấm điểm | `may_reels/cham_diem.py` theo `brand/<kênh>/rubric.yaml`, chặn cứng, `cham-lai`, `hieu-chinh` |
| Bố cục cảnh sơ đồ | **Mới 2026-11-20.** `hf.py`: trong cảnh sơ đồ ngã tư / vòng xuyến, dòng phụ + nguồn luật hiện 2,6 s rồi mờ, xe chạy sau đó; sơ đồ thu phóng bằng viewBox vào khoảng trống giữa tiêu đề và phụ đề; phụ đề hạ xuống y 1075; vòng xuyến: xe trong vòng rời vòng trước khi xe chờ vào, số đặt cạnh xe chờ |
| Cỡ chữ và vùng an toàn | **Mới 2026-11-19.** `may_reels/co_chu.py`: mọi chữ trên màn hình từ 42px (đọc từ nguồn HyperFrames), không ra ngoài vùng an toàn (hyperframes check). Áp trần tiêu chí `phu_de`, ghi `canh_bao` |
| Chiến lược nội dung (C0) | **Mới 2026-11-20.** `brand/<kênh>/doi-tuong.yaml`, `dinh-vi.yaml`, `ban-hang.yaml` (chỉ trên máy), `dinh-dang.yaml`, `lich.yaml`; schema trong `schemas/may-reels/`; `may_reels/chien_luoc.py`, lệnh `chien-luoc kiem-tra --kenh <mã>`. Chưa có code nào khác dùng các file này (sản xuất vẫn theo `san-xuat.yaml khung_nhip`) |
| Hàng chờ, sửa | `hang-cho them`, `sua`, `thay-canh`, `dung-lai --ma <mã>` (mới 2026-11-20: dựng lại theo mẫu, giữ kế hoạch) |
| Đăng | `dang [--that]` (FB Reels, YT Shorts qua API; TikTok bàn giao qua Drive để đăng tay) |
| Kho cảnh (Prompt 6) | `kho nap` (tự nạp, gắn nhãn, quyền hình, số lần dùng, viết lại KHO.md), `kho thieu` (danh sách quay theo buổi) |
| Dọn dẹp | `dung-luong`, `don-dep` |

### Đang dở

- **C2b (biên kịch, biên tập kịch bản) tạm dừng** ngày 2026-11-20 để làm C0 trước; C0 đã commit 2026-11-21, C2b là bước 3 của LO-TRINH.md. Ở C2b, kịch bản mẫu cần số liệu chưa xác nhận để ô `[chờ anh xác nhận]`.
- Trạm phân tích video (`Claude code/tram-phan-tich`, repo riêng) chưa có kết quả mẫu nào: chờ người dùng chép video vào `channels/vanxuan/mau/video/`.

- **vx-007: "Chờ duyệt", bản xem thử `vx-007-vong-xuyen-v3.mp4`** (2026-11-20 21:27, `dung-lai`): đã có sửa xe chồng nhau, xe 2 không bị che, bố cục cảnh sơ đồ, khoảng cách từ phụ đề, dòng nguồn chỉ ở s2 và s5. Điểm 70 (dưới 75) vì trần tổng "phần lớn là cảnh tạm" (cảnh thật 40%); kỹ thuật 96. Agent chấm còn nêu tiêu đề thẻ chữ xuống dòng để lại một chữ mồ côi: đã thêm `text-wrap:balance` cho tiêu đề **sau** khi dựng v3.
- Dựng lại khi chỉ đổi mẫu: đã có lệnh `dung-lai` (2026-11-20).
- vx-006: người dùng đã đổi sang "Duyệt" (2026-11-20), dựng ngày 2026-11-16 theo mẫu cũ (chữ dưới 42px).
- Prompt 6 (kho cảnh và danh sách quay): **phần máy làm được đã xong**. Việc cuối là so sánh model chép lời, có kết luận ngày 2026-11-19 (giữ PhoWhisper, `KE-HOACH.md` mục 10). Còn lại đều cần người quyết, xem mục dưới.

### Chờ người dùng

0. **`brand/vanxuan/ban-hang.yaml`** (chỉ trên máy): đã có học phí A1/A, ưu đãi, lý thuyết, lịch thi, đánh giá (2026-11-21). Còn thiếu: khoản gồm/không gồm (lệ phí thi, cấp bằng, khám sức khỏe, thi lại), ngày hết hạn ưu đãi, xác nhận sân thực hành và câu "không phát sinh", số buổi, quy trình, giấy tờ, lịch khai giảng, mồi nhử, người đồng ý lên hình. Kho cảnh chưa có "thầy nói trước máy" (7 định dạng cần), "học viên nói trước máy", "nhận bằng".

1. Gợi ý tự động hóa (hook, cấu hình) cho Máy Reels: đã đưa người dùng ngày 2026-11-20, chưa cài, chờ chọn.
2. Facebook: đã có quyền admin Fanpage (người dùng xác nhận ngày 2026-11-19). Còn thiếu `fb_reels.page_id` trong `brand/vanxuan/dang-bai.yaml` và `VANXUAN_FB_PAGE_TOKEN` trong `.env` (cách lấy: `CAI-DAT-DANG-BAI.md` mục A). `dang` chạy thử khô ngày 2026-11-19: FB và YT bị chặn vì thiếu cấu hình, chỉ TikTok bàn giao được.
3. YouTube: `yt_shorts.kenh_id`, `made_for_kids`, `contains_synthetic_media`.
4. Giờ đăng (11:30 hay 19:30), số video mỗi ngày (`KE-HOACH.md` câu 6).
5. Giấy phép thương mại của VieNeu và PhoWhisper: chưa xác minh.
6. Lịch sử git (commit `dc52b79`, đã đẩy lên GitHub) còn bản `brand.json` có đường dẫn tuyệt đối. Không viết lại lịch sử khi chưa hỏi.
7. vx-006: người xem khung giây 20,2 để xác nhận agent chấm có đúng không khi cho rằng sơ đồ vẽ sai thứ tự xe.
8. Nghe 0–16 s của `canh-quay/Nhieu_hoc_vien_nu_Cancanh.mp4` (thầy có nói "vừa xoay bánh đi vòng quay lại chứ"?), để biết rãnh giọng tách bằng rea-video giúp chép lời hay khiến model bịa.

### Test

- 2026-11-21 (C0 commit): `tests/may_reels` 306/306. Toàn bộ repo: 3237 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới, số hỏng không tăng).
- 2026-11-20 (sau `dung-lai`): `tests/may_reels` 292/292. Toàn bộ repo: 3218 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới).
- 2026-11-19: `tests/may_reels` 288/288. Toàn bộ repo: 3212 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới).
- Một test upstream hỏng từ trước, không liên quan Máy Reels: `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]` (đã kiểm: vẫn hỏng khi cất các thay đổi của Máy Reels).
