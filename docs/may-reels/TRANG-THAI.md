# Máy Reels: trạng thái

Đọc file này đầu mỗi phiên phát triển. Chi tiết thiết kế ở `KE-HOACH.md`, nguyên tắc ở `NGUYEN-TAC.md`, lịch sử thay đổi ở `NHAT-KY-PHAT-TRIEN.md`. Cập nhật file này trước mỗi commit.

## Cập nhật lần cuối: 2026-11-19

File này được tạo ngày 2026-11-19. Trước đó trạng thái chỉ nằm trong `KE-HOACH.md` (các mục "Việc còn lại / chưa làm").

### Đã có và chạy được

| Phần | Lệnh / file |
|---|---|
| Ý tưởng, Sheet | `sheet init`, tab Chủ đề / Hàng chờ / Cần quay / Quyền hình / Nhật ký |
| Nguồn luật | `nguon-luat`, `ap-dung` (máy đề xuất, người xác nhận; ưu tiên văn bản hợp nhất) |
| Sản xuất không hỏi | `san-xuat` (agent viết ke_hoach.json, pipeline HyperFrames, giọng VieNeu) |
| Chấm điểm | `may_reels/cham_diem.py` theo `brand/<kênh>/rubric.yaml`, chặn cứng, `cham-lai`, `hieu-chinh` |
| Cỡ chữ và vùng an toàn | **Mới 2026-11-19.** `may_reels/co_chu.py`: mọi chữ trên màn hình từ 42px (đọc từ nguồn HyperFrames), không ra ngoài vùng an toàn (hyperframes check). Áp trần tiêu chí `phu_de`, ghi `canh_bao` |
| Hàng chờ, sửa | `hang-cho them`, `sua`, `thay-canh` |
| Đăng | `dang [--that]` (FB Reels, YT Shorts qua API; TikTok bàn giao qua Drive để đăng tay) |
| Kho cảnh (Prompt 6) | `kho nap` (tự nạp, gắn nhãn, quyền hình, số lần dùng, viết lại KHO.md), `kho thieu` (danh sách quay theo buổi) |
| Dọn dẹp | `dung-luong`, `don-dep` |

### Đang dở

- **vx-006 đang ở "Sửa" trên Sheet nhưng `ghi_chu_sua` trống** ở cả 3 dòng (fb_reels, yt_shorts, tiktok). `sua` sẽ ghi lỗi "chọn Sửa nhưng ghi_chu_sua trống" mà không dựng lại, nên ngày 2026-11-19 **chưa chạy**. Chờ người ghi ghi chú (ví dụ: "dựng lại theo mẫu chữ 42px", hoặc nội dung cần sửa).
  - Bản cũ của vx-006 (render 2026-11-16) có 13 nhóm chữ dưới 42px: nguồn luật 30px, chữ cạnh logo 28px, màn kết 32–40px, dòng phụ thẻ chữ 34px, số trên xe 34px. Dựng lại bằng mẫu mới thì hết: đã thử trên bản sao HTML, không đụng dự án thật; `hyperframes check --at-transitions` báo 0 chữ ngoài vùng an toàn, tương phản 55/55.
- vx-007 "Chờ duyệt" (72→70 điểm, dưới ngưỡng 75). Video dựng trước khi có kiểm tra cỡ chữ nên cũng có chữ nhỏ. Chấm lại (`cham-lai`) hoặc dựng lại thì mới hiện cảnh báo mới.
- Prompt 6 (kho cảnh và danh sách quay): **phần máy làm được đã xong**. Việc cuối là so sánh model chép lời, có kết luận ngày 2026-11-19 (giữ PhoWhisper, `KE-HOACH.md` mục 10). Còn lại đều cần người quyết, xem mục dưới.

### Chờ người dùng

1. `ghi_chu_sua` cho vx-006 (xem trên).
2. Facebook: đã có quyền admin Fanpage (người dùng xác nhận ngày 2026-11-19). Còn thiếu `fb_reels.page_id` trong `brand/vanxuan/dang-bai.yaml` và `VANXUAN_FB_PAGE_TOKEN` trong `.env` (cách lấy: `CAI-DAT-DANG-BAI.md` mục A). `dang` chạy thử khô ngày 2026-11-19: FB và YT bị chặn vì thiếu cấu hình, chỉ TikTok bàn giao được.
3. YouTube: `yt_shorts.kenh_id`, `made_for_kids`, `contains_synthetic_media`.
4. Giờ đăng (11:30 hay 19:30), số video mỗi ngày (`KE-HOACH.md` câu 6).
5. Giấy phép thương mại của VieNeu và PhoWhisper: chưa xác minh.
6. Lịch sử git (commit `dc52b79`, đã đẩy lên GitHub) còn bản `brand.json` có đường dẫn tuyệt đối. Không viết lại lịch sử khi chưa hỏi.
7. vx-006: người xem khung giây 20,2 để xác nhận agent chấm có đúng không khi cho rằng sơ đồ vẽ sai thứ tự xe.
8. Nghe 0–16 s của `canh-quay/Nhieu_hoc_vien_nu_Cancanh.mp4` (thầy có nói "vừa xoay bánh đi vòng quay lại chứ"?), để biết rãnh giọng tách bằng rea-video giúp chép lời hay khiến model bịa.

### Test

- 2026-11-19: `tests/may_reels` 288/288. Toàn bộ repo: 3212 qua, 19 bỏ qua, 1 hỏng (test upstream bên dưới).
- Một test upstream hỏng từ trước, không liên quan Máy Reels: `tests/tools/test_fal_resume_output_format.py::test_checkpoint_only_resume_preserves_media_format[webp]` (đã kiểm: vẫn hỏng khi cất các thay đổi của Máy Reels).
