# Máy Reels: quyết định đã chốt

Mỗi quyết định một mục: ngày, quyết định, lý do, file liên quan. **Không xóa mục cũ.** Khi đổi quyết định, thêm mục mới và ghi "Thay bởi …" vào mục cũ. Trạng thái hiện tại: `TRANG-THAI.md`; nguyên tắc: `NGUYEN-TAC.md`.

File tạo ngày 2026-11-21, tách từ `KE-HOACH.md` (mục 3.2, 4, 6, quyết định ở mục 9 và 10). Câu 1–19 giữ đúng số của `KE-HOACH.md` mục 6 cũ: code và cấu hình (`brand/vanxuan/san-xuat.yaml`, `dang-bai.yaml`, `may_reels/nguon_luat.py`, `kho_chep_loi.py`, `pipeline_defs/may-reels.yaml`) vẫn ghi "KE-HOACH.md câu N" hay "mục 6"; các chỗ đó nay đọc ở đây.

---

## A. Câu 1–19: người dùng trả lời ngày 2026-11-15

Ba câu 5, 6 và 17 có chỗ người dùng **còn để trống** trong bản trả lời. Những chỗ đó ghi **chưa chốt**, máy không tự đoán. Cập nhật về sau ghi ngay trong câu.

### Google Sheet và cách duyệt

**Câu 1. Sheet "Máy Reels", truy cập bằng service account** (2026-11-15)
- Tạo Sheet mới tên "Máy Reels" trong tài khoản Google của người dùng. Máy truy cập bằng **service account**: người dùng chia sẻ Sheet cho email của service account. File khóa để trong `secrets/` (đã gitignore), đường dẫn đọc từ `.env`.
- File: `may_reels/sheet.py`, `docs/may-reels/CAI-DAT-GOOGLE.md`.

**Câu 2. Ô Duyệt là dropdown** (2026-11-15)
- Ba giá trị: `Duyệt` / `Sửa` / `Bỏ`. Chọn `Sửa` thì đi kèm cột ghi chú của người. Mọi giá trị khác, kể cả ô trống, đều tính là **chưa duyệt**.
- **Cập nhật 2026-11-15** theo yêu cầu xây lớp nối Sheet (thay cho bản trên, xem `NGUYEN-TAC.md` mục 2):
  - Tab Hàng chờ: cột `duyet`, dropdown `Chờ duyệt` / `Duyệt` / `Sửa` / `Bỏ`.
  - Tab Ý tưởng: cột `duyet_chu_de`, dropdown `Chờ` / `Làm` / `Bỏ`. Cổng A mở khi chọn `Làm`.
  - Ô trống được hiểu là giá trị chờ, vì máy không ghi vào cột của người, kể cả giá trị mặc định.
  - Khóa của tab Ý tưởng là `kenh` + `ma`, không chỉ `ma`. Lý do: một Sheet dùng cho mọi kênh (câu 4), mà mã chủ đề trong `brand.json` chỉ duy nhất trong một kênh.
- File: `may_reels/cot_sheet.py`, `may_reels/sheet.py`.

**Câu 3. Xem video qua link Google Drive** (2026-11-15)
- Máy tải video lên Drive rồi ghi link vào hàng chờ.
- File: `may_reels/drive.py`, `may_reels/hang_cho.py`.

**Câu 4. Một Sheet cho mọi kênh** (2026-11-15)
- Có cột Kênh (mã kênh trong `brand/<id>/`).

### Đăng bài

**Câu 5. Tài khoản đăng** (2026-11-15)
- Facebook: Fanpage `facebook.com/hoclaixephutho`. Người dùng sẽ tự tạo app Meta. Có quyền admin Fanpage hay chưa: **chưa chốt** (bản trả lời còn để trống `<có / chưa có>`).
  - **Cập nhật 2026-11-19:** người dùng xác nhận đã có quyền admin Fanpage. Còn thiếu `fb_reels.page_id` trong `brand/vanxuan/dang-bai.yaml` và token trong `.env`.
- YouTube: kênh nào thì **chưa chốt** (bản trả lời còn để trống `<tên hoặc link kênh>`).
- TikTok: chưa đăng ký app. Giai đoạn đầu người dùng **đăng tay**. Máy chỉ chuẩn bị file và caption, không gọi API TikTok.
- File: `brand/vanxuan/dang-bai.yaml`, `tools/publishers/`.

**Câu 6. Giờ đăng, số video mỗi ngày** (2026-11-15)
- Đăng cùng giờ trên các nền tảng. Số video mỗi ngày cho mỗi nền tảng ghi `<1>`, nên tạm hiểu là 1 nhưng vẫn coi là **chưa chốt** (có thể là chỗ chưa điền). Giờ đăng là 11:30 hay 19:30: **chưa chốt**.

**Câu 7. Đăng thật bằng cờ dòng lệnh** (2026-11-15)
- Chuyển sang đăng thật bằng **cờ dòng lệnh**, không bằng ô trên Sheet. Chỉ người dùng được bật cờ này. Không có cờ thì mặc định chạy thử.
- File: `may_reels/dang_bai.py` (`dang --that`), `NGUYEN-TAC.md` mục 3.

**Câu 8. Một bản 9:16 dùng chung** (2026-11-15)
- Một bản cho cả 3 nền tảng. Facebook dùng profile `instagram_reels`. Brief ghi `target_platform = "generic"`, danh sách nền tảng ghi trong `brief.metadata`. **Không sửa** `lib/media_profiles.py`.
- Lý do: `brief.target_platform` không có `facebook`, `lib/media_profiles.py` không có profile Facebook Reels; thêm profile là sửa file lõi.

### Chạy không dừng

**Câu 9. Phương án 2: manifest riêng `pipeline_defs/may-reels.yaml`** (2026-11-15)
- Đã ghi vào "Điểm chạm upstream" của `NGUYEN-TAC.md`. Phân tích hai phương án: mục B1 bên dưới.

**Câu 10. `claude -p` theo lịch Windows Task Scheduler** (2026-11-15)
- Chạy trên chính máy này. Điều kiện: **phải chạy thử thật ở bước sản xuất** trước khi tin dùng. Sổ chi phí ghi **số lượt chạy** và **thời gian chạy** của trợ lý, không đo token.

**Câu 11. Runtime HyperFrames** (2026-11-15)
- Chốt một lần trong `brand/vanxuan/`, sau đó máy không hỏi lại. Điều kiện: phải dựng xong được một video từ đầu đến cuối. **Đã đạt ngày 2026-11-15** với `projects/vx-005-a1-xe-150cc` (`NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-15 (2)). Runtime đã ghi vào `brand/vanxuan/san-xuat.yaml`.
- Lý do: manifest `hybrid` ghi "typically uses render_runtime='remotion'", còn `idea-director.md` ghi "neither is an auto-default". vx-demo-01 đã dựng bằng HyperFrames (`hyperframes check` báo 0 lỗi, có ảnh xem trước).

**Câu 12. Ngưỡng 75 điểm** (2026-11-15)
- Trượt sau 2 vòng sửa thì video vẫn vào hàng chờ, kèm cảnh báo "Dưới ngưỡng".
- File: `brand/vanxuan/san-xuat.yaml` (`nguong`), `brand/vanxuan/rubric.yaml`.

### Nội dung và quyền

**Câu 13. Chỉ dùng 12 chủ đề chưa làm** (2026-11-15)
- Trước mắt chỉ dùng **12 chủ đề chưa làm** trong `chu-de.md`. Việc máy tự đề xuất chủ đề mới để sang giai đoạn sau (bước C1 trong lộ trình).

**Câu 14. Nguồn luật** (2026-11-15)
- Với mỗi nguồn luật, lưu vào dự án: link, ngày mở, và điều khoản được dẫn. **Người duyệt chủ đề** chịu trách nhiệm xác nhận điều khoản đúng.
- **Cập nhật 2026-11-16:**
  - Người duyệt chủ đề tự tra văn bản, rồi ghi `nguon_doi_chieu` trong `chu-de.md` của kênh **đến số khoản**. Ví dụ: "Luật 36/2024/QH15, Điều 22, khoản 2, 3".
  - Chặn cứng chỉ cho phép đúng các điều, khoản đã ghi. Cách ghi liệt kê "khoản 2, 3" hoặc "khoản 2 và 3" được hiểu là cả hai khoản.
  - `nguon_luat_da_mo` trong `rubric.yaml` **giữ tắt**: máy không tự tin vào nguồn agent mở.
  - Đã áp dụng cho `giao-nhau-khong-bao-hieu` (Điều 22 khoản 2) và `vong-xuyen` (Điều 22 khoản 2, 3). Người dùng xác nhận trực tiếp với văn bản luật.
- **Cập nhật 2026-11-16 (sau đó): máy đề xuất, người xác nhận.** Thay cho việc người tự tra ở cập nhật trên.
  - Người duyệt không phải tự tra văn bản. Lệnh `nguon-luat` cho agent (`skills/may-reels/tra-nguon-luat.md`) mở văn bản chính thức, kiểm tra hiệu lực, rồi ghi lên tab Ý tưởng các cột của máy: `nguon_de_xuat`, `trich_nguyen_van`, `link_nguon`, `ngay_tra`, `ghi_chu_may`.
  - Người chọn `xac_nhan_nguon` (Đúng/Sai). **Người vẫn là bước quyết định.**
  - `nguon-luat ap-dung` chỉ chép những đề xuất được chọn "Đúng" vào `chu-de.md`, sao lưu trước khi sửa.
  - `nguon_luat_da_mo` **vẫn tắt**.
  - **"Tới mức khoản"** (`may_reels/nguon_luat.py`, hàm `du_muc_khoan`):
    - Mỗi lần nhắc "Điều N" phải kèm khoản, điểm hoặc mục.
    - QCVN phải có mục, phụ lục, Điều, hoặc số hiệu biển/vạch.
    - Phần không phải văn bản pháp luật (ví dụ `context/business.md`) không xét.
    - Vì vậy `a1-xe-150cc` ("Điều 57 khoản 1 điểm a và Điều 89") cũng thuộc diện phải tra, do Điều 89 chưa có khoản.
  - `san-xuat` từ chối chủ đề chưa đạt mức trên và ghi lý do vào `ghi_chu_may`. Ngoại lệ: chủ đề ghi "Không cần nguồn luật".
- **Cập nhật 2026-11-17** (commit `89e50dd`): ưu tiên văn bản hợp nhất chính thức khi tra nguồn luật.

**Câu 15. Tự cắt khung, không tự làm mờ** (2026-11-15)
- Máy **được tự cắt khung** theo vùng ghi trong `can_xu_ly`. Máy **không tự làm mờ** mặt người và biển số. Cảnh cần làm mờ thì chỉ dùng đoạn không cần xử lý.
- File: `brand/vanxuan/san-xuat.yaml` (`tu_cat_khung`), `NGUYEN-TAC.md` mục 5.

**Câu 16. Chưa dùng nhạc nền** (2026-11-15)
- File: `brand/vanxuan/san-xuat.yaml` (`nhac_nen: khong`).

**Câu 17. Giọng VieNeu "Hải Đăng"** (2026-11-15)
- Dùng làm tool chính thức hay chờ người dùng kiểm tra giấy phép: bản trả lời ban đầu còn để trống.
- **Cập nhật 2026-11-15:** người dùng chốt giọng VieNeu "Hải Đăng" trong `brand/vanxuan/san-xuat.yaml`. Máy gọi VieNeu qua `may_reels/giong.py`, không qua tool trong `tools/audio/`. Giấy phép thương mại của VieNeu vẫn **chưa xác minh**.

### Dữ liệu trên repo public

**Câu 18. Bỏ đường dẫn tuyệt đối và nội dung riêng khỏi repo** (2026-11-15)
- Đồng ý. Đã sửa `tools_local/nap_kenh.py` (xem `KE-HOACH.md` mục 5.1):
  - `brand.json` không còn đường dẫn tuyệt đối.
  - Thư mục kênh gốc đọc từ `KENH_GOC_DIR` trong `.env`.
  - Toàn văn `context/*.md` tách sang `brand/<id>/_local/` (bị gitignore).
  - Tiền tố mã video, thư mục video và font chuyển sang `brand/<id>/cau-hinh.yaml`.
  - Lịch sử git cũ vẫn còn bản `brand.json` có đường dẫn tuyệt đối và toàn văn context: commit `dc52b79` đã đẩy lên GitHub. **Không viết lại lịch sử git khi chưa hỏi người dùng.**

**Câu 19. Số liệu cần lấy** (2026-11-15)
- Lượt xem, thời gian xem trung bình, lượt chia sẻ, bình luận; cột tin nhắn do người dùng nhập tay (máy không ghi vào cột này).
- Đo ở 3 mốc: 1, 3 và 7 ngày sau khi đăng.

---

## B. Quyết định thiết kế khác

### B1. Chạy không dừng: phương án 2 (2026-11-15, câu 9)

**Phương án 1: chỉ thêm skill bọc ngoài, giữ manifest `hybrid`.** Skill ghi một mục `approval_policy` dựa trên dòng Sheet đã duyệt chủ đề, rồi ghi `human_approved=True` cho cả `script`, `scene_plan`, `assets`.
- Ưu điểm: không thêm file nào vào thư mục lõi.
- Nhược điểm: người chưa hề xem kịch bản, kế hoạch cảnh hay tư liệu mà checkpoint vẫn ghi "người đã duyệt". Như vậy là dùng cờ duyệt sai nghĩa, và nhật ký kiểm tra sẽ nói sai sự thật.

**Phương án 2 (đã chọn): manifest riêng `pipeline_defs/may-reels.yaml` cộng skill bọc ngoài.**
- Chép cấu trúc stage của `hybrid.yaml` và trỏ `skill` của từng stage về director skill có sẵn của hybrid (`pipelines/hybrid/*-director`). Không viết director mới.
- `idea: human_approval_default: true` ứng với cổng (A) trên Sheet. `publish: true` ứng với cổng (B). `script`, `scene_plan`, `assets`, `edit`, `compose` đặt `false`.
- Thay cho cổng của người ở các stage đó là cổng tự động: reviewer + `may_reels/cham_diem.py`. Trượt thì làm lại tối đa 2 vòng (đúng `reviewer.md`), vẫn trượt thì đánh dấu "bỏ" hoặc "cần quay" trên Sheet.
- Lý do: cổng duyệt vẫn được code ép đúng như upstream thiết kế, và checkpoint chỉ ghi `human_approved=True` ở đúng hai chỗ người thật sự duyệt.
- Cái giá: phải thêm file vào `pipeline_defs/`. `lib/pipeline_loader.py` chỉ đọc từ `PIPELINE_DEFS_DIR`, và `_stage_requires_approval()` gọi `load_pipeline_readonly(pipeline_type)` không kèm thư mục khác, nên manifest không đặt trong `may_reels/` được. Việc này được ghi ở "Điểm chạm upstream".
- Bối cảnh (code upstream bắt buộc gì): `KE-HOACH.md` mục 3.1.

**Luật chọn runtime và hỏi trước khi đổi**, dùng chung cho cả hai phương án: người dùng chốt một lần cho mỗi kênh (runtime, giọng, có nhạc hay không), ghi trong `brand/<id>/`. Mỗi lần chạy, máy ghi lại quyết định `render_runtime_selection` vào `decision_log` với đủ cả hai runtime trong `options_considered` và lý do "đã chốt theo cấu hình kênh". Gặp vật cản (runtime hỏng, thiếu cảnh, thiếu nguồn luật), máy không tự đổi hướng: dừng video đó và ghi lý do lên Sheet.

### B2. Pipeline `hybrid` (2026-11-15)

| Pipeline | Hợp với loại video nào (theo manifest) | Có khớp video "cảnh thật từ kho + đồ họa chữ" không |
|---|---|---|
| **`hybrid`** | "Source footage plus support visuals". Stage `assets` có `subtitle_gen`, `tts_selector`, `diagram_gen`. `compose` dùng `video_compose` + `hyperframes_compose` + `audio_mixer`. `stability: production`. | **Khớp.** Cảnh thật là lớp chính, đồ họa chữ, phụ đề và giọng đọc là lớp hỗ trợ. vx-demo-01 cũng đã chọn `hybrid`. Mục review_focus "Source content remains visually primary" và "Optional generated inserts do not eclipse source truth" khớp với quy tắc cấm của kênh. |
| `talking-head` | Footage có "a person speaking". Stage `script` **bắt buộc** `transcriber`, và section phải có mốc thời gian lấy từ transcript của footage. `stability: beta`. | Không khớp. Lời đọc ở đây là giọng TTS chạy theo kịch bản, không có người nói trước máy quay. Chỉ hợp nếu sau này kênh quay thầy nói trực tiếp (bước C3). |
| `clip-factory` | Một nguồn dài (webinar, livestream) cắt ra nhiều clip ngắn. `script` bắt buộc `transcriber` và phải tìm ra "N candidate clips". `stability: beta`. | Không khớp. Kho có 24 cảnh ngắn (video dài nhất khoảng 31 giây), không có nguồn dài để cắt. Cái hợp với máy là ý "nhiều video một lượt", và việc đó làm ở lớp skill bọc ngoài. |

Ghi chú: `documentary-montage` (lấy cảnh từ kho stock miễn phí và kho lưu trữ mở) chưa đọc chi tiết. Theo mô tả trong `AGENT_GUIDE.md` thì nó dựa vào stock bên ngoài, trái với quy tắc "không stock nước ngoài".

### B3. Chấm điểm nội dung theo rubric (2026-11-16, máy đề xuất, **chờ người xác nhận**)

Thiết kế và kết quả chạy: `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-16. File: `may_reels/cham_diem.py`, `brand/vanxuan/rubric.yaml`, `skills/may-reels/cham-diem.md`.

1. **Trần tổng.** Rubric gốc không đủ để hai mẫu hỏng "3 giây đầu là logo" và "80% cảnh tạm" rơi xuống dưới ngưỡng: hook bằng 0 vẫn còn 80 điểm. Vì vậy `rubric.yaml` có thêm mục `tran_tong`: hook dưới 8 điểm, hoặc cảnh thật dưới 40% thời lượng, thì tổng tối đa 70.
2. **Video bị chặn vẫn được agent chấm,** để người đọc vẫn hiểu video đó ra sao. `dat` = false, và video không vào Hàng chờ.
3. **Miễn cho số không phải số liệu.** Số đếm 1–10 đứng riêng, cùng số điện thoại, địa chỉ và CTA của kênh, không bị coi là số liệu. Số hiệu luật thì luôn phải có nguồn.
4. **Hai cột của người không có dropdown,** vì người dùng tự tạo cột. Máy đọc điểm một cách linh hoạt, chấp nhận giá trị từ 1 đến 10.

### B4. Quyền hình chỉ áp cho cảnh có mặt người (2026-11-17, người dùng chốt)

- `nap_kenh.py` chỉ áp điều kiện ngày và `bo_sung` của `quyen_hinh` cho cảnh có mặt người; cảnh không có mặt người dùng được ngay. Cảnh có mặt người lên tab **Quyền hình**; người chọn "Đồng ý" thì lần `kho nap` sau chép vào `quyen_hinh.bo_sung` của `channel.yaml`.
- Cảnh có mặt người mặc định `dung_duoc = false` cho tới khi người xác nhận quyền hình.
- File: `tools_local/nap_kenh.py`, `may_reels/kho.py`.

### B5. PhoWhisper là model chép lời mặc định (2026-11-19)

- Thử base / large-v3 / PhoWhisper-large trên 2 clip thật. PhoWhisper sát lời thật nhất, không bịa câu ở đoạn lặng; `large-v3` bịa câu "đăng ký kênh". Bảng so sánh: `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-19 (1). Commit `fdc6e75`.
- Không thử lại large-v3 ở các bước sau.
- File: `may_reels/kho_chep_loi.py` (`kiendt/PhoWhisper-large-ct2`).

### B6. Bộ prompt C thay Prompt 5 và 5A (2026-11-20)

- Chiến lược nội dung (`docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`, chỉ có ở máy) đưa vào máy qua bộ C: C0 dữ liệu kênh; C0b học từ video mẫu (trạm phân tích); C1 chủ đề theo nhóm và lịch; C2 mã theo dõi, tiêu chí "đúng đối tượng"; C2b bộ biên kịch; C3 video giọng thật của thầy; C4 mẫu trả lời Zalo, số liệu theo mã; C5 xem lại hằng tuần; C6 trường nguồn trong hệ thống quản lý học viên (repo khác). Prompt 5 và 5A cũ không làm nữa.
- Prompt 2 (đăng bài thật) để sau: các bước chỉ dùng Hàng chờ và `export_bundle`, không đụng publisher.
- Thứ tự chạy các bước: `docs/may-reels/LO-TRINH.md` (chỉ có ở máy, không commit). C2b chạy trước C1 và C2.

### B7. Dữ liệu kinh doanh thật chỉ để trên máy (2026-11-20, mở rộng 2026-11-21)

- `docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`, `brand/*/ban-hang.yaml`, `doi-tuong.yaml`, `dinh-vi.yaml` bị `.gitignore`; repo chỉ có bản mẫu `*.mau.yaml` cùng cấu trúc. 2026-11-21 thêm `docs/may-reels/LO-TRINH.md` (commit `81798b7`).
- Lý do: repo công khai; học phí, ưu đãi, số liệu bán hàng và chiến lược là thông tin kinh doanh.
- File: `.gitignore`, `NGUYEN-TAC.md` mục 7 và 11, `tests/may_reels/test_chien_luoc.py`.

### B8. Trạm phân tích video là repo riêng (2026-11-20)

- Trạm phân tích (`tram-phan-tich`, repo riêng) bóc video mẫu; OpenMontage không cài rea-video, không gọi trạm, chỉ đọc kết quả ở `<KENH_GOC_DIR>/vanxuan/mau/ket-qua/`.

### B9. Cảnh sơ đồ: thu gọn chữ khi có sơ đồ (2026-11-20, người dùng chọn)

- Trong cảnh sơ đồ ngã tư / vòng xuyến: tiêu đề tối đa 80px; dòng phụ + nguồn luật hiện 2,6 s rồi mờ, xe chạy sau đó; sơ đồ thu phóng vào khoảng trống giữa tiêu đề và phụ đề.
- Lý do: lần `sua` đầu cho vx-007 dựng hỏng vì số trên xe (42px) đè lên dòng nguồn và phụ đề. Chi tiết: `NHAT-KY-PHAT-TRIEN.md`, mục 2026-11-20.
- File: `may_reels/dung/hf.py`.

### B10. Dòng nguồn luật chỉ hiện khi lời đọc trích luật (2026-11-20, theo yêu cầu người dùng)

- Mỗi nguồn hiện một lần, ở đoạn lời đọc trích luật đầu tiên. Caption vẫn ghi nguồn đầy đủ. Commit `bdbd47c`.
- Lý do: dòng nguồn xuất hiện thường xuyên che cảnh chính.

### B11. Bộ biên kịch: biên tập kịch bản trước khi dựng (2026-11-21, C2b; con số là máy đề xuất, **chờ người xác nhận**)

- **Tách người viết và biên tập.** Người viết (`skills/may-reels/bien-kich.md`) ghi 3 góc kể, 5 hook theo 5 công thức, bản 1, những gì đã sửa ở bản 2 vào `ke_hoach.json` → `kich_ban`. Biên tập (`skills/may-reels/bien-tap.md`) chạy bằng một phiên `claude -p` riêng và chỉ được Read đúng 2 file: skill và `bien_tap/dau_vao.json` (`goi_agent(doc=...)`). File đầu vào do Python lọc sẵn, không có lập luận của người viết. Lý do: biên tập phải đọc như người xem lần đầu.
- **Máy kiểm trước, biên tập sau.** Python kiểm: hook tối đa 13 âm tiết, câu dài nhất tối đa 26 âm tiết, cụm từ cấm, câu sáo, hook sáo, 7 kiểu câu văn AI, từ tránh, cấu trúc `kich_ban`. Lỗi chặn thì không gọi biên tập và điểm bằng 0. Lỗi đo được thì áp trần lên tiêu chí. Rubric 10 tiêu chí, tổng 100, ngưỡng 75, tối đa 2 vòng sửa; hết vòng vẫn dựng kèm cảnh báo "Kịch bản dưới ngưỡng". Mọi con số nằm trong `brand/<kenh>/rubric-kich-ban.yaml` và đều là giả thuyết.
- **Chỉ biên tập bản đầu.** Biên tập chạy một lần, sau bản kế hoạch đầu tiên. Các vòng sửa sau (lỗi kế hoạch, QA video dưới ngưỡng) không biên tập lại. Lệnh `sua` và `thay-canh` cũng không biên tập. Kênh chưa có `rubric-kich-ban.yaml` thì bỏ qua bước này.
- **Kịch bản mẫu chỉ dùng khi đã duyệt.** `brand/<kenh>/kich-ban-mau/*.yaml` máy soạn ở trạng thái `cho_duyet`; người viết chỉ dùng mẫu `da_duyet` làm ví dụ. Mẫu được commit lên repo công khai nên số liệu bán hàng luôn để ô `[chờ anh xác nhận]`.
- **Hàng chờ có thêm 2 cột máy:** `diem_kich_ban` và `cong_thuc_hook`, nối vào cuối. Mục đích: buổi xem lại hằng tuần (C5) so được công thức hook nào thắng.
- **Nguồn tham khảo** marketingskills (MIT, commit `5b2b400`) chép vào `docs/may-reels/tham-khao/marketingskills/`, không cài thành skill.
- File: `may_reels/bien_tap.py`, `may_reels/san_xuat.py` (`qua_bien_tap`), `may_reels/so_sanh_kich_ban.py`, `brand/vanxuan/hook.yaml`, `giong-noi.yaml`, `giu-chan.yaml`, `rubric-kich-ban.yaml`.
- **Cập nhật 2026-11-23: biên tập hỏng không phải điểm 0.** Biên tập (`claude -p`) không ghi được `diem.json` thì thử lại 1 lần (`bien_tap.bien_tap_thu_lai`, dùng chung cho sản xuất và `bien-kich so-sanh`). Vẫn hỏng: sản xuất dừng biên tập, dựng tiếp với kế hoạch hiện có, `diem_kich_ban` trống, cảnh báo "Biên tập lỗi, chưa có điểm kịch bản"; `so-sanh` ghi "lỗi". Lý do: điểm 0 là điểm giả, trả người viết sửa theo nó chỉ tốn lượt agent và có thể làm hỏng kịch bản tốt. Không chặn video vì người vẫn duyệt ở cổng B.

### B12. Ưu đãi thường xuyên, cấm hứa "không phát sinh" (2026-11-23, người dùng chốt)

- **Ưu đãi thường xuyên** không có ngày hết hạn: `ban-hang.yaml` `uu_dai[].thuong_xuyen: true`, `het_han: null`, `ngay_xem_lai` bắt buộc (schema `ban-hang.schema.json`, if/then). `chien-luoc kiem-tra` không báo hết hạn, chỉ báo khi quá `ngay_xem_lai`. Kịch bản không nói hạn chót hay "sắp hết": máy chặn đoạn nhắc ưu đãi ("ưu đãi", "giảm") có cụm gấp gáp (`rubric-kich-ban.yaml` `kiem_tra_may.uu_dai_thuong_xuyen`), chỉ khi kênh có ưu đãi thường xuyên đã xác nhận. Lý do: không tạo gấp gáp giả (`NGUYEN-TAC.md` mục 11).
- **Không hứa "không phát sinh".** Thêm vào `quy-tac-rieng.yaml` `cum_tu_cam`: "không phát sinh", "không phát sinh chi phí", "trọn gói 100%", "không mất thêm đồng nào". Câu chi phí đã duyệt: "Đã gồm học, khám sức khỏe và lệ phí thi. Ngoài ra chỉ còn lệ phí cấp bằng theo quy định, và phí thi lại nếu chưa đạt." Lý do: còn lệ phí cấp bằng và phí thi lại người học tự trả.
- File: `schemas/may-reels/ban-hang.schema.json`, `may_reels/chien_luoc.py`, `may_reels/bien_tap.py`, `brand/vanxuan/quy-tac-rieng.yaml`, `brand/vanxuan/rubric-kich-ban.yaml`, `skills/may-reels/bien-kich.md`.

---

## C. Còn chưa chốt

Danh sách gốc ở cuối `KE-HOACH.md` mục 6 (2026-11-15), kèm cập nhật:

- Câu 5: ~~có quyền admin Fanpage chưa~~ (đã có, 2026-11-19); kênh YouTube nào: **chưa chốt**.
- Câu 6: số video mỗi ngày (xác nhận 1), giờ đăng 11:30 hay 19:30: **chưa chốt**.
- Giấy phép thương mại của VieNeu và PhoWhisper (câu 17): chưa xác minh.
- Có viết lại lịch sử git để xóa bản `brand.json` cũ khỏi GitHub hay không (câu 18): chưa hỏi.
- B3: bốn quyết định của máy về chấm điểm, chờ người xác nhận.
- Gợi ý tự động hóa (hook, cấu hình) cho Máy Reels: đã đưa người dùng ngày 2026-11-20, chưa chọn.
