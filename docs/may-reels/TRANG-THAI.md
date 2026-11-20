# Máy Reels: trạng thái

Đọc file này đầu mỗi phiên phát triển. Chi tiết thiết kế ở `KE-HOACH.md`, nguyên tắc ở `NGUYEN-TAC.md`, lịch sử thay đổi ở `NHAT-KY-PHAT-TRIEN.md`. Cập nhật file này trước mỗi commit.

## Cập nhật lần cuối: 2026-11-20

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
| Hàng chờ, sửa | `hang-cho them`, `sua`, `thay-canh` |
| Đăng | `dang [--that]` (FB Reels, YT Shorts qua API; TikTok bàn giao qua Drive để đăng tay) |
| Kho cảnh (Prompt 6) | `kho nap` (tự nạp, gắn nhãn, quyền hình, số lần dùng, viết lại KHO.md), `kho thieu` (danh sách quay theo buổi) |
| Dọn dẹp | `dung-luong`, `don-dep` |

### Đang dở

- **vx-007: đã sửa và dựng lại ngày 2026-11-20** (`sua`, ghi chú ở J8): xe 2 của cảnh s3 chuyển xuống nhánh dưới; lỗi hai xe chồng nhau ở giây ~13 hết; mẫu bố cục mới. Đang "Chờ duyệt". Điểm 70 (dưới ngưỡng 75), do trần tổng "phần lớn là cảnh tạm" (cảnh thật 40%); kỹ thuật 87 → 96; 0 chữ dưới 42px, 0 chữ ngoài vùng an toàn.
  - Agent chấm còn nêu: (1) trong 2,6 s đầu của cảnh sơ đồ, ô nguồn luật che mép trên vòng xuyến (cố ý: lúc đó xe chưa chạy, chữ mờ trước khi xe chạy); (2) phụ đề "KHÔNG CÓ" ở ~25,6 s trông dính liền, do từ đang đọc phóng 1,08. Đã sửa mẫu (khoảng cách giữa các từ phụ đề) **sau** khi vx-007 dựng xong, nên bản đang ở Hàng chờ chưa có sửa này.
- **Dựng lại khi chỉ đổi mẫu:** `sua` chỉ dựng lại nếu agent đổi `ke_hoach.json`. Sửa mẫu (`hf.py`) mà kế hoạch không đổi thì `sua` báo "khong_doi". Chưa có lệnh "dựng lại + chấm + cập nhật Hàng chờ" khi kế hoạch giữ nguyên.
- vx-006: người dùng đã đổi sang "Duyệt" (2026-11-20), dựng ngày 2026-11-16 theo mẫu cũ (chữ dưới 42px).
- Prompt 6 (kho cảnh và danh sách quay): **phần máy làm được đã xong**. Việc cuối là so sánh model chép lời, có kết luận ngày 2026-11-19 (giữ PhoWhisper, `KE-HOACH.md` mục 10). Còn lại đều cần người quyết, xem mục dưới.

### Chờ người dùng

1. Có cần lệnh dựng lại khi chỉ đổi mẫu không (xem "Đang dở").
2. Facebook: đã có quyền admin Fanpage (người dùng xác nhận ngày 2026-11-19). Còn thiếu `fb_reels.page_id` trong `brand/vanxuan/dang-bai.yaml` và `VANXUAN_FB_PAGE_TOKEN` trong `.env` (cách lấy: `CAI-DAT-DANG-BAI.md` mục A). `dang` chạy thử khô ngày 2026-11-19: FB và YT bị chặn vì thiếu cấu hình, chỉ TikTok bàn giao được.
3. YouTube: `yt_shorts.kenh_id`, `made_for_kids`, `contains_synthetic_media`.
4. Giờ đăng (11:30 hay 19:30), số video mỗi ngày (`KE-HOACH.md` câu 6).
5. Giấy phép thương mại của VieNeu và PhoWhisper: chưa xác minh.
6. Lịch sử git (commit `dc52b79`, đã đẩy lên GitHub) còn bản `brand.json` có đường dẫn tuyệt đối. Không viết lại lịch sử khi chưa hỏi.
7. vx-006: người xem khung giây 20,2 để xác nhận agent chấm có đúng không khi cho rằng sơ đồ vẽ sai thứ tự xe.
8. Nghe 0–16 s của `canh-quay/Nhieu_hoc_vien_nu_Cancanh.mp4` (thầy có nói "vừa xoay bánh đi vòng quay lại chứ"?), để biết rãnh giọng tách bằng rea-video giúp chép lời hay khiến model bịa.

### Test

- 2026-11-20: `tests/may_reels` 290/290. Toàn bộ repo: 3216 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới).
- 2026-11-19: `tests/may_reels` 288/288. Toàn bộ repo: 3212 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới).
- Một test upstream hỏng từ trước, không liên quan Máy Reels: `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]` (đã kiểm: vẫn hỏng khi cất các thay đổi của Máy Reels).
