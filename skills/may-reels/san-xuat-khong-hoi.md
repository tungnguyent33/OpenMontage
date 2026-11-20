# Máy Reels: sản xuất không hỏi người

Skill cho agent chạy không tương tác (`claude -p`), do `python -m may_reels san-xuat` hoặc `python -m may_reels sua` gọi. Skill này áp dụng cho **mọi kênh**. Mọi giá trị riêng của kênh đều đọc từ `brand/<kenh>/`.

**Nguồn gốc:** prompt "Prompt 3" trong tài liệu bộ prompt của người dùng **không có trong repo**. Skill này viết theo danh sách yêu cầu người dùng gửi ngày 2026-11-15; chưa đối chiếu với tài liệu gốc.

## Việc của agent: chỉ viết MỘT file

Agent chỉ viết `projects/<ma_video>/ke_hoach.json`, theo schema `schemas/may-reels/ke_hoach_video.schema.json`. File này là phần **sáng tạo**: lời đọc, thẻ chữ, nguồn luật, cảnh chọn từ kho, caption và các quyết định đã tự đưa ra.

Mọi bước sau đó do Python làm theo cách tất định (`may_reels/dung/`): sinh giọng, nghe lại, cắt cảnh, dựng HyperFrames, tự kiểm, đóng gói, ghi Sheet. Agent **không** gọi tool OpenMontage, không chạy lệnh, không ghi file nào khác, không đăng bài.

**Không hỏi người.** Mọi quyết định thường phải hỏi đã chốt trong `brand/<kenh>/san-xuat.yaml`: runtime, giọng, nhạc, khung hình, thời lượng, phụ đề, màn kết, chi phí. Quyết định nào agent phải tự đưa ra thì ghi vào mảng `quyet_dinh` của kế hoạch. Mảng này được chép vào `decision_log`, mỗi mục gồm `category`, `subject`, `options_considered`, `selected` và `reason`.

## Đầu vào

Đọc `projects/<ma_video>/yeu_cau.json` (máy tạo sẵn). File này có:
- `ma_video`, `kenh`, `chu_de` (một dòng `chu_de[]` của `brand.json`: `ma`, `tru_cot`, `dinh_dang`, `chu_de`, `y_chinh`, `nguon_doi_chieu`);
- `khung_nhip`: khóa trong `san-xuat.yaml`;
- `so_lan_dung_canh`: số video trước (đã dựng xong) đã dùng mỗi cảnh;
- `ngay_dung_canh_gan_nhat`: ngày gần nhất mỗi cảnh được dùng (`YYYY-MM-DD`). Cảnh không có trong hai mục này là cảnh chưa dùng;
- `phan_hoi`: lỗi kiểm tra hoặc điểm QA của vòng trước. Có mục này nghĩa là đang ở vòng sửa: sửa đúng các lỗi được nêu.
- `ghi_chu_sua`: chỉ có khi chạy bằng lệnh `sua`. Ý kiến của người duyệt, phải làm theo.

Đọc thêm:
- `brand/<kenh>/brand.json`:
  - `kho_canh`, `cam`, `cta`, `hashtags`, `kenh`, `lien_he`;
  - `context` → `ban_local`: giọng văn và chân dung khách hàng, nếu file local có trên máy.
- `brand/<kenh>/san-xuat.yaml` (`khung_nhip`, `am_tiet_moi_giay`, `canh`) và `brand/<kenh>/quy-tac-rieng.yaml`.

## Quy tắc nội dung (bắt buộc)

1. **Nhịp cố định** theo `san-xuat.yaml` → `khung_nhip[<khóa>]`:
   - `hook` → các đoạn `than` → `chot` → `cta`;
   - id đoạn đánh số `s1`, `s2`, …;
   - **hook phải đọc xong trong 3 giây**: khoảng 13 âm tiết trở xuống, vì giọng đọc nhanh cỡ `am_tiet_moi_giay`;
   - tổng thời lượng phải nằm trong `khung_hinh.thoi_luong_giay` (30–50 giây).
2. **Lời đọc chính là phụ đề.** Viết đúng chính tả, câu ngắn, số viết bằng chữ số (2025, 125). Máy tự đổi sang cách đọc. Chỉ dùng `doc_rieng` khi máy chắc chắn sẽ đọc sai.
3. **Luật phải có nguồn.**
   - Mọi ý về luật đều gắn `nguon_ids`. Mỗi nguồn phải có văn bản, `ten_ngan` (dòng hiện trên màn hình), Điều/khoản, link, ngày mở và **trích nguyên văn**.
   - Agent phải **mở link bằng WebFetch** trong lần chạy này và trích đúng câu chữ. Ưu tiên văn bản trên `chinhphu.vn`, `vbpl.vn`, `quochoi.vn`. `nguon_doi_chieu` của chủ đề là gợi ý ban đầu.
   - Không mở được nguồn hoặc không chắc điều khoản → không nói ý đó. Không bịa số liệu, không hứa kết quả thi.
4. **Cụm từ cấm:** không dùng bất kỳ cụm nào trong `brand.json` → `cam.cum_tu_cam` và `cam.cum_tu_cam_du_an`, ở lời đọc, thẻ chữ và caption. Tránh cả câu sáo đã chốt (`cam.cau_sao_da_chot`).
5. **CTA:** đoạn `cta` là **nguyên văn** một câu trong `brand.json` → `cta`. Chọn câu khác với video gần nhất nếu biết. Đoạn này có `canh = null` và `the = null`, vì máy dựng màn kết có logo và hotline.
6. **Thẻ chữ** (`the`): `dong1` tối đa 22 ký tự, viết hoa; `dong2` tối đa 34 ký tự. Chọn `mau` là `cam` (nhấn mạnh) hoặc `xanh` (thông tin), và `kieu` là `hook`, `wipe`, `word` hoặc `scale`. Dòng nguồn trên thẻ do máy tự ghép từ `nguon_ids`, nhưng **chỉ hiện ở đoạn mà lời đọc đang trích luật** ("Luật…", "Điều…", "khoản…", "Nghị định…", "QCVN…") và mỗi nguồn chỉ hiện một lần, để không che cảnh. Vẫn gắn `nguon_ids` cho mọi ý về luật (máy dùng để chặn cứng), và **caption phải ghi nguồn đầy đủ** (tên văn bản, Điều, khoản).

## Chọn cảnh (chỉ từ kho kênh)

- Chỉ dùng cảnh trong `brand.json` → `kho_canh` có `dung_duoc: true`. **Không** dùng stock, không dùng hình hay video do AI tạo.
- Cảnh video phải có `vao` (giây trong file gốc) nằm trong `doan_dung_duoc`. Máy tự lấy đủ độ dài từ `vao`, và lùi lại nếu cần, nhưng không ra ngoài `doan_dung_duoc`. Hãy chọn `vao` sao cho từ đó về sau còn đủ dài: khoảng 5–10 giây cho đoạn thân.
- Đọc `rui_ro` và `can_xu_ly`:
  - Máy **được cắt khung** (`san-xuat.yaml` → `canh.tu_cat_khung`).
  - Máy **không tự làm mờ** mặt người và biển số (`canh.tu_lam_mo: false`). Cảnh cần làm mờ thì chỉ dùng đoạn không cần xử lý.
  - Cảnh có `mat_nguoi: true` chỉ dùng được khi `quyen_hinh.da_dong_y`.
- **Một cảnh không dùng quá một lần trong cùng video.** Ngoại lệ duy nhất: cảnh có thẻ trong `canh.lap_duoc_neu_the` (cảnh nói trước máy).
- **Ưu tiên cảnh ít dùng, rồi cảnh lâu chưa dùng.** Xem `so_lan_dung_canh` và `ngay_dung_canh_gan_nhat` trong `yeu_cau.json`.
  - Giữa các cảnh khớp ý ngang nhau: chọn cảnh chưa dùng, rồi cảnh có `so_lan_dung_canh` thấp hơn, rồi cảnh có ngày dùng gần nhất xa hơn.
  - Tránh cảnh đã dùng trong 7 ngày gần nhất khi có cảnh khác khớp ý. Người xem lướt nhiều video liền nhau nên dễ nhận ra cảnh lặp.
  - Cảnh đã dùng từ 3 lần trở lên bị trừ điểm QA.
  - Ý nào chỉ còn cảnh đã dùng nhiều lần mà không khớp hẳn thì ghi vào `thieu_canh` như mục dưới, đừng cố dùng lại.
- Cảnh phải khớp ý của đoạn (xem `mo_ta`, `the`, `dia_diem`). Ghi lý do chọn vào `canh.ly_do_chon`.
- **Thiếu cảnh thật cho một ý:** không lấp bằng cảnh kho không khớp.
  1. Ghi một mục vào `thieu_canh` (`doan`, `y_can_canh`, `mo_ta_canh`, `goi_y_quay`, `ly_do`). Máy ghi mục này vào tab "Cần quay".
  2. Đoạn đó dùng **cảnh tạm** dạng sơ đồ động: `canh = {"so_do": {...}, "mo_ta": "..."}`. Máy vẽ sơ đồ bằng HTML/SVG, không dùng AI, không dùng stock. Video vẫn được dựng và vào Hàng chờ, kèm cảnh báo "Có cảnh tạm".
  3. Sau này, khi người dùng quay xong và nạp lại kho, lệnh `thay-canh` thay sơ đồ bằng cảnh thật.
- **Cách dùng sơ đồ** (`so_do`):
  - `giao_nhau`: ngã tư nhìn từ trên.
    - `xe` là tối đa 4 xe, mỗi xe có `tu` (`duoi`/`tren`/`trai`/`phai`: xe đến từ phía nào), `thu_tu` (1 = đi trước) và `loai` (`xe_may`, `o_to` hoặc `uu_tien` cho xe cứu thương, cứu hỏa).
    - `duong_uu_tien` (`ngang` hoặc `doc`) tô sáng con đường ưu tiên.
    - Thứ tự đi **phải đúng luật đã trích** trong `nguon_luat`.
  - `vong_xuyen`: vòng xuyến chạy ngược chiều kim đồng hồ.
    - Xe `thu_tu` 1 là xe đang đi trong vòng; xe số 2 trở đi chờ ở nhánh của mình.
    - Nên đặt xe chờ ở nhánh `trai`, `phai` hoặc `tren`, vì nhánh `duoi` bị phụ đề che.
  - `the_chu`: chữ lớn (`chu`, tối đa 60 ký tự) cho ý không vẽ được bằng hai kiểu trên.
- Chỉ đoạn có trong `thieu_canh` mới được dùng `so_do`. Mỗi cảnh tạm bị trừ 3 điểm QA, nên vẫn ưu tiên cảnh thật khi kho có cảnh khớp ý.

## Caption và hashtag

- `caption` có ba bản riêng: `fb_reels`, `yt_shorts`, `tiktok`. Mỗi bản:
  - mở đầu bằng câu hook;
  - tóm tắt ý chính;
  - có dòng `Nguồn: …` nếu có nội dung luật;
  - kết bằng CTA.
- Giọng văn từng nền tảng:
  - Facebook: đầy đủ nhất.
  - YouTube Shorts: ngắn gọn. Dòng đầu cũng là tiêu đề, nên đặt `tieu_de` tối đa 100 ký tự.
  - TikTok: ngắn nhất, thân mật.
- **Không tự viết hashtag.** Máy gắn hashtag riêng từng nền tảng từ `brand.json` → `hashtags` (`facebook`, `youtube`, `tiktok`).

## Vòng sửa

- `phan_hoi` liệt kê lỗi kế hoạch hoặc điểm QA dưới ngưỡng (`san-xuat.yaml` → `cham_diem.nguong`). Sửa đúng các mục đó và giữ nguyên phần đã đạt.
- Máy cho tối đa `cham_diem.so_vong_sua` vòng (2). Sau đó video vẫn vào Hàng chờ, kèm cảnh báo "Dưới ngưỡng".
- Lệnh `sua`: đọc `ghi_chu_sua` của người duyệt rồi sửa `ke_hoach.json` hiện có. Chỉ đổi phần người duyệt yêu cầu, không viết lại toàn bộ.
- Lệnh `thay-canh`: `yeu_cau.json` có `ghi_chu_sua` liệt kê các đoạn đang dùng cảnh tạm.
  - Tìm trong `kho_canh` (đã nạp lại) cảnh thật khớp ý của từng đoạn, rồi thay `canh` bằng cảnh đó và bỏ mục tương ứng khỏi `thieu_canh`.
  - Không có cảnh khớp thì giữ nguyên sơ đồ.
  - Không đổi lời đọc.

## Kết thúc

Ghi `ke_hoach.json` xong thì dừng. Trả lời một dòng tóm tắt, ví dụ: "Đã viết ke_hoach.json: 7 đoạn, 2 nguồn, 0 cảnh thiếu."
