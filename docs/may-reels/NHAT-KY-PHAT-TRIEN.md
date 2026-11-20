# Máy Reels: nhật ký phát triển

Mỗi phiên một mục, mới nhất ở trên. Ghi việc đã làm, quyết định, số đo, việc bỏ dở. Trạng thái hiện tại: `TRANG-THAI.md`.

File tạo ngày 2026-11-19. Các phiên trước ngày này được ghi trong `KE-HOACH.md` (mục 7–10) và trong lịch sử git của nhánh `kenh-vanxuan`.

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

Commit `fdc6e75`. Chạy nốt phép so sánh base / large-v3 / PhoWhisper trên 2 clip thật. Kết luận: giữ PhoWhisper. Chi tiết ở `KE-HOACH.md` mục 10.
