# Máy Reels: API đăng bài (tóm tắt từ tài liệu chính thức)

**Ngày đọc: 2026-11-15.** Mọi thông tin dưới đây lấy từ các trang tài liệu chính thức ghi ở từng mục, đọc trong ngày này, không viết theo trí nhớ. Chỗ nào tài liệu không nói rõ thì ghi **chưa xác minh**. Nền tảng có thể đổi API bất cứ lúc nào, nên trước khi sửa code đăng bài phải đọc lại tài liệu và cập nhật ngày đọc.

| Nền tảng | Cách đăng trong Máy Reels | File code |
|---|---|---|
| Facebook Reels (Page) | API, Page access token | `tools/publishers/facebook_reels.py` |
| YouTube Shorts | API, OAuth của chủ kênh, refresh token trong `secrets/` | `tools/publishers/youtube_shorts.py` |
| TikTok | **Đăng tay.** Máy chép video và caption vào thư mục Drive "Chờ đăng TikTok" | `tools/publishers/tiktok_handoff.py` |

---

## 1. Facebook Reels cho Page

**Nguồn:**
- https://developers.facebook.com/docs/video-api/guides/reels-publishing (trang không ghi ngày cập nhật; ví dụ dùng Graph API **v27.0**)
- https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived (lấy token dài hạn)

### Endpoint (3 bước + kiểm tra)

| Bước | Lệnh |
|---|---|
| 1. Khởi tạo phiên tải lên | `POST https://graph.facebook.com/v27.0/{page-id}/video_reels`, tham số `upload_phase=start`, `access_token` (Page token). Trả về `video_id` và `upload_url`. |
| 2. Tải file lên | `POST https://rupload.facebook.com/video-upload/v27.0/{video-id}`, header `Authorization: OAuth {token}`, `offset` (thường là `0`), `file_size` (tính bằng byte); body là dữ liệu nhị phân (`application/octet-stream`). Trả về `{"success": true}`. Muốn tải tiếp từ chỗ dừng thì gửi lại với `offset` = `bytes_transfered` lấy từ endpoint trạng thái. |
| 3. Đăng | `POST https://graph.facebook.com/v27.0/{page-id}/video_reels`, tham số `video_id`, `upload_phase=finish`, `video_state=PUBLISHED` (hoặc `DRAFT`, `SCHEDULED`). Tùy chọn: `description`, `title`, `scheduled_publish_time`, `is_ai_generated`, `place`. |
| Kiểm tra | `GET https://graph.facebook.com/v27.0/{video-id}?fields=status`. Kết quả có `uploading_phase`, `processing_phase` (`not_started` / `in_progress` / `completed` / `error`), `publishing_phase` (`publish_status`: `draft` / `scheduled` / `published` / `error`, `publish_time`) và `video_status`. |

Tài liệu tự mâu thuẫn ở bước 3: bảng ghi `upload_phase` "should be `complete`", trong khi danh sách giá trị hợp lệ chỉ có `{start, finish}`. Code dùng `finish`, theo danh sách giá trị.

Link bài đăng: code đọc trường `permalink_url` của video. Trang hướng dẫn Reels không nhắc tới trường này, nên **chưa xác minh**. Nếu không đọc được thì cột `link_bai` để trống, còn `id_bai` vẫn được ghi.

### Quyền và token

- Cần **Page access token** của một người dùng có quyền `CREATE_CONTENT` trên Page.
- Quyền phải được cấp qua Facebook Login: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
- Trang Reels **không nói gì** về App Review, Advanced Access hay xác minh doanh nghiệp. Vì vậy chưa xác minh được rằng app ở chế độ Development có đăng được lên Page của chính admin hay không.
- Token dài hạn:
  - Đổi token người dùng ngắn hạn qua `GET oauth/access_token` với `grant_type=fb_exchange_token`, `client_id`, `client_secret`, `fb_exchange_token`. Token người dùng dài hạn "generally lasts about 60 days".
  - Sau đó gọi `GET {app-scoped-user-id}/accounts` bằng token người dùng dài hạn. Page token nhận được ở bước này "do not have an expiration date and only expire or are invalidated under certain conditions".
  - Lệnh có App Secret thì không được chạy phía client.

### Thông số video

| Mục | Giới hạn |
|---|---|
| File | `.mp4` (khuyên dùng) |
| Tỉ lệ | 9:16 |
| Độ phân giải | khuyên dùng 1080×1920, tối thiểu 540×960 |
| Khung hình | 24–60 fps, fps cố định, quét liên tục (progressive) |
| Thời lượng | 3–90 giây (tối đa 60 giây nếu đăng thành story của Page) |
| Mã hóa | H.264 / H.265 (hỗ trợ cả VP9, AV1); 4:2:0; closed GOP 2–5 giây |
| Âm thanh | AAC LC, 48 kHz, stereo, từ 128 kbps |
| Dung lượng tối đa | tài liệu không ghi |

### Giới hạn

- "Reels API is limited to 30 API-published posts within a 24-hour moving period", tính trên `POST /{page_id}/video_reels`. Meta khuyên app tự giữ giới hạn này.
- Chỉ đăng được lên Page, không đăng lên trang cá nhân. Đăng lên Page luôn ở chế độ công khai.
- Mã lỗi có trong tài liệu:
  - `100`: thiếu tham số;
  - `1363040`: tỉ lệ khung không hỗ trợ;
  - `1363127`: độ phân giải không hỗ trợ;
  - `1363128`: thời lượng không hỗ trợ;
  - `1363129`: fps không hỗ trợ;
  - lỗi khi tải file: `OffsetInvalidError`, `PartialRequestError`, `ProcessingFailedError`.

---

## 2. YouTube Data API: `videos.insert`

**Nguồn:**
- https://developers.google.com/youtube/v3/docs/videos/insert (không ghi ngày cập nhật)
- https://developers.google.com/youtube/v3/revision_history (lịch sử thay đổi)
- https://developers.google.com/youtube/v3/getting-started (quota)
- https://developers.google.com/youtube/v3/docs/videos/list
- https://support.google.com/youtube/answer/15424877 (điều kiện để là Shorts)
- https://developers.google.com/identity/protocols/oauth2 (thời hạn refresh token)

### Endpoint

- Tải lên: `POST https://www.googleapis.com/upload/youtube/v3/videos`, tham số `part=snippet,status`. Ví dụ của Google dùng kiểu tải lên `resumable`. Code dùng `MediaFileUpload(resumable=True)` của `google-api-python-client`.
- Đọc lại: `videos.list` với `part=status` và `id=<video id>` để lấy `status.privacyStatus`. Tốn 1 đơn vị quota.
- MIME chấp nhận: `video/*`, `application/octet-stream`. File tối đa 256 GB.
- Các trường có thể đặt:
  - `snippet.title`, `snippet.description`, `snippet.tags[]`, `snippet.categoryId`, `snippet.defaultLanguage`;
  - `status.privacyStatus`, `status.publishAt`, `status.selfDeclaredMadeForKids`, `status.containsSyntheticMedia`, `status.embeddable`, `status.license`, `status.publicStatsViewable`;
  - `recordingDetails.recordingDate`.
- Trang `videos.list` không liệt kê các thuộc tính của `status`, nên các giá trị của `uploadStatus` và `rejectionReason` **chưa xác minh**.

### Quyền (scope OAuth)

- `videos.insert` nhận một trong các scope: `youtube.upload`, `youtube`, `youtubepartner`, `youtube.force-ssl`.
- Trang `videos.list` không ghi scope cần có để đọc video của chính mình. Code xin thêm `youtube.readonly` để đọc lại `privacyStatus`. Việc này dựa trên suy luận, **chưa xác minh**.
- Refresh token:
  - Project có màn hình đồng ý OAuth loại External mà trạng thái xuất bản là **"Testing"** thì refresh token **hết hạn sau 7 ngày**. Muốn máy chạy lâu dài thì phải chuyển ứng dụng sang "In production".
  - Mỗi tài khoản Google có tối đa 100 refresh token cho một OAuth client. Vượt quá thì token cũ nhất bị vô hiệu mà không báo trước.
  - Refresh token cũng hết hạn nếu 6 tháng không dùng.

### Chế độ hiển thị: thay đổi mới

- Revision history ngày **2 tháng 11 năm 2026**: video tải lên từ project API chưa xác minh "are no longer restricted to private viewing mode", tức là bỏ quy định ngày 28 tháng 7 năm 2020.
- Không đặt `status.privacyStatus` thì mặc định là `public`. Tuy vậy, "Certain uploads might default to private based on creator account settings".
- Vì hai điều trên, code luôn đặt `privacyStatus=public`, rồi **đọc lại** để chắc chắn video đang công khai.

### Quota và giới hạn

- Mặc định mỗi ngày mỗi project được 100 lượt gọi `search.list`, **100 lượt gọi `videos.insert`**, và 10.000 đơn vị dùng chung cho các endpoint còn lại. Google ghi rằng mức này "subject to change".
- Từ ngày 1 tháng 6 năm 2026, `videos.insert` có ngăn quota riêng.
- Lỗi `uploadLimitExceeded` (400) xảy ra khi người dùng vượt số lượt tải lên cho phép. Con số giới hạn của từng kênh không được công bố.
- Thời điểm quota được đặt lại về 0: tài liệu đã đọc không ghi.

### Điều kiện để thành Shorts

- Video dài tối đa 3 phút, tỉ lệ vuông hoặc dọc, tải lên từ ngày 15 tháng 10 năm 2024. Không có trường API riêng cho Shorts: video đủ điều kiện thì YouTube tự xếp vào Shorts.
- Tài liệu đã đọc không ghi giới hạn fps cho Shorts.

---

## 3. TikTok Content Posting API (chưa dùng)

**Nguồn:**
- https://developers.tiktok.com/doc/content-posting-api-get-started (cập nhật ngày 4 tháng 8 năm 2026)
- https://developers.tiktok.com/doc/content-posting-api-reference-direct-post (cập nhật ngày 27 tháng 10 năm 2026)
- https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide (cập nhật ngày 4 tháng 8 năm 2026)
- https://developers.tiktok.com/doc/content-sharing-guidelines

### Endpoint (Direct Post)

- Khởi tạo: `POST https://open.tiktokapis.com/v2/post/publish/video/init/`. Body gồm:
  - `post_info`: `title`, `privacy_level` (bắt buộc), `disable_comment`...;
  - `source_info`: `source` = `FILE_UPLOAD` hoặc `PULL_FROM_URL`. `PULL_FROM_URL` chỉ nhận URL thuộc domain đã xác minh.
- Tải lên: `PUT` vào `upload_url` nhận được ở bước khởi tạo.
- Trạng thái: `POST https://open.tiktokapis.com/v2/post/publish/status/fetch/` với `publish_id`.
- `privacy_level` phải là một trong các giá trị mà `/creator_info/query/` trả về.

### Quyền và kiểm định

- Scope `video.publish`. App phải được duyệt scope này, người dùng phải cấp quyền, và trong cấu hình sản phẩm Content Posting API phải bật Direct Post.
- **Client chưa qua kiểm định (audit):**
  - chỉ đăng được ở chế độ `SELF_ONLY`;
  - tối đa 5 người dùng đăng trong 24 giờ;
  - tài khoản đăng phải đang ở chế độ riêng tư.

  Lỗi tương ứng: `unaudited_client_can_only_post_to_private_accounts`.
- Yêu cầu giao diện (content sharing guidelines):
  - Phải hiện nickname của người tạo nội dung.
  - Người dùng tự chọn chế độ hiển thị từ dropdown, **không có giá trị mặc định**.
  - Chỉ gửi nội dung lên TikTok sau khi người dùng đồng ý rõ ràng.

### Giới hạn

- Mỗi user access token: 6 request mỗi phút.
- Mỗi tài khoản người tạo: "typically around 15 posts per day". Con số này có thể khác nhau giữa các tài khoản, và tính chung cho mọi client Direct Post. Lỗi khi vượt: `spam_risk_too_many_posts`.
- Mỗi API client còn có giới hạn số người tạo nội dung hoạt động trong 24 giờ, lấy theo ước tính khi nộp đơn kiểm định.
- Video:
  - định dạng MP4 (khuyên dùng), WebM, MOV; mã hóa H.264 (khuyên dùng), H.265, VP8, VP9;
  - 23–60 fps;
  - cạnh ngắn nhất 360 px, cạnh dài nhất 4096 px;
  - tối đa 10 phút qua API, tối đa 4 GB;
  - mỗi chunk 5–64 MB; chunk cuối được tới 128 MB.

### Điều kiện để chuyển TikTok từ đăng tay sang API

1. Đăng ký app trên TikTok for Developers, thêm sản phẩm Content Posting API, bật Direct Post, xin scope `video.publish`.
2. **Qua kiểm định của TikTok.** Chưa qua thì bài chỉ hiện ở chế độ `SELF_ONLY` và tài khoản phải đang riêng tư, nên không dùng được cho kênh công khai.
3. Có bước xác nhận của người cho từng bài, đáp ứng content sharing guidelines:
   - hiện nickname tài khoản;
   - người tự chọn chế độ hiển thị, không có giá trị mặc định;
   - người đồng ý rõ ràng trước khi gửi.

   Cột `duyet` trên Sheet có thể là bước đồng ý này, nhưng việc TikTok chấp nhận cách đó hay không **chưa xác minh**. Phải hỏi trong đơn kiểm định.
4. Máy phải giữ giới hạn 6 request mỗi phút cho mỗi token và khoảng 15 bài mỗi ngày cho mỗi tài khoản.
5. Viết `tools/publishers/tiktok.py` theo cùng khuôn với hai publisher kia, rồi đổi cấu hình `tiktok.che_do` trong `brand/<id>/dang-bai.yaml` từ `tay` sang `api`.

---

## 4. Google Drive (bản xem thử và thư mục chờ đăng TikTok)

**Nguồn:** https://developers.google.com/workspace/drive/api/guides/about-shareddrives

- Google ghi: "Service accounts don't have storage quota and can't own files", và "they must upload files and folders into shared drives, or use OAuth 2.0 to upload items on behalf of a human user."
- Vì vậy service account dùng cho Sheet **không tải được video lên Drive của bạn**. Máy tải lên Drive bằng **OAuth của chính bạn** (scope `drive.file`: chỉ thấy file và thư mục do Máy Reels tạo ra). Token lưu trong `secrets/`.

---

## 5. Giới hạn máy tự áp dụng

Các giới hạn này đặt trong `may_reels/dang_bai.py`, cấu hình lại được trong `brand/<id>/dang-bai.yaml`, mục `gioi_han_24h`.

| Nền tảng | Số bài / 24 giờ (mặc định) | Lấy từ |
|---|---|---|
| `fb_reels` | 30 cho mỗi Page | Tài liệu Reels của Meta |
| `yt_shorts` | 100 | Quota mặc định 100 lượt `videos.insert` mỗi ngày **cho cả project**, tức tính chung mọi kênh |
| `tiktok` (đăng tay) | 15 | Mức "around 15 posts per day" cho mỗi tài khoản |

Kiểm tra file trước khi đăng (`may_reels/kiem_tra_video.py`):

| Nền tảng | Tỉ lệ | Thời lượng | fps | Kích thước |
|---|---|---|---|---|
| `fb_reels` | 9:16 | 3–90 giây | 24–60 | từ 540×960 |
| `yt_shorts` | 9:16 (yêu cầu của Máy Reels; YouTube nhận cả vuông) | ≤ 180 giây | không có giới hạn trong tài liệu đã đọc | — |
| `tiktok` | 9:16 | ≤ 600 giây | 23–60 | 360–4096 px |
