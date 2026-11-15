# Máy Reels: cài đặt đăng bài

Làm sau khi đã xong `CAI-DAT-GOOGLE.md` (Sheet). Tóm tắt API, quyền và giới hạn của từng nền tảng nằm trong `API-DANG-BAI.md`.

**Quy tắc chung:** mọi token và file khóa chỉ nằm trong `.env` hoặc thư mục `secrets/`. Cả hai đều bị gitignore. `brand/<kênh>/dang-bai.yaml` được commit, nên file này chỉ chứa **tên biến** và **ID công khai** (ID Page, ID kênh). Máy từ chối đọc file nếu thấy giá trị trông giống token.

Các bước trên giao diện web của Meta và Google ghi theo tài liệu đã đọc ngày 2026-11-15. Tên nút và menu có thể đã đổi. Chỗ nào **chưa xác minh** thì có ghi rõ.

---

## A. Facebook Reels: app Meta và Page token dài hạn

Cần có: tài khoản Facebook có vai trò trên Page `facebook.com/hoclaixephutho`, đủ quyền đăng nội dung (Meta gọi là `CREATE_CONTENT`).

### A1. Tạo app Meta

1. Mở https://developers.facebook.com/apps và chọn **Create App**.
2. Chọn mục đích liên quan tới quản lý Page. Thêm quyền **Facebook Login** để xin được các quyền dưới đây. Tên và thứ tự các bước tạo app **chưa xác minh**.
3. Ghi lại **App ID** và **App Secret** (trong App settings → Basic). App Secret là bí mật: không gửi cho ai, không dán vào chat.

Tài liệu Reels không nói rõ app cần App Review hay Advanced Access để đăng lên Page của chính bạn (**chưa xác minh**). Hãy thử ở chế độ Development trước. Nếu Meta báo thiếu quyền thì mới tính tới App Review.

### A2. Lấy token người dùng ngắn hạn

1. Mở **Graph API Explorer**: https://developers.facebook.com/tools/explorer
2. Chọn app vừa tạo, chọn **User Token**, rồi thêm ba quyền: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
3. Bấm **Generate Access Token** và đồng ý cấp quyền cho Page.

### A3. Đổi sang token dài hạn, rồi lấy Page token

Chạy trong PowerShell trên máy này. Mỗi lệnh sẽ hỏi giá trị, nên giá trị không bị lưu vào lịch sử lệnh:

```powershell
$appId   = Read-Host "App ID"
$secret  = Read-Host "App Secret"
$ngan    = Read-Host "Token ngắn hạn"
$dai = (Invoke-RestMethod "https://graph.facebook.com/v27.0/oauth/access_token?grant_type=fb_exchange_token&client_id=$appId&client_secret=$secret&fb_exchange_token=$ngan").access_token
$me  = (Invoke-RestMethod "https://graph.facebook.com/v27.0/me?fields=id&access_token=$dai").id
(Invoke-RestMethod "https://graph.facebook.com/v27.0/$me/accounts?access_token=$dai").data | Select-Object name, id, access_token
```

- Lệnh thứ tư đổi token ngắn hạn sang token người dùng dài hạn (khoảng 60 ngày).
- Lệnh cuối liệt kê các Page bạn quản lý. Mỗi Page có `id` và `access_token`, và theo tài liệu của Meta, token này **không có hạn** trừ vài trường hợp bị vô hiệu.
- Lệnh `me?fields=id` để lấy ID người dùng: tài liệu ghi endpoint là `{app-scoped-user-id}/accounts`, còn cách lấy ID bằng `me` là của mình, **chưa xác minh** trong tài liệu đã đọc.

### A4. Ghi vào cấu hình

- `.env`: `VANXUAN_FB_PAGE_TOKEN=<access_token của Page>`
- `brand/vanxuan/dang-bai.yaml`: `fb_reels.page_id: "<id của Page>"`

Xong thì đóng PowerShell để xóa các biến tạm.

---

## B. YouTube Shorts và Google Drive: OAuth client

YouTube cần quyền của **chủ kênh**. Drive cũng cần quyền của **bạn**: theo tài liệu của Google, service account không có dung lượng Drive nên không tải file lên được. Cả hai dùng chung một OAuth client.

### B1. Bật API

Trong project Google Cloud đã tạo ở `CAI-DAT-GOOGLE.md`, vào **APIs & Services → Library** và bật:
- **YouTube Data API v3**
- **Google Drive API**

### B2. Màn hình đồng ý OAuth

1. Vào **APIs & Services → OAuth consent screen**. Giao diện mới có thể nằm trong mục **Google Auth Platform**.
2. Chọn User type **External**. Điền tên app (ví dụ "Máy Reels") và email liên hệ.
3. **Quan trọng:** nếu để trạng thái xuất bản là **Testing**, refresh token **hết hạn sau 7 ngày**, và máy sẽ ngừng đăng YouTube mà không báo trước. Hãy bấm **Publish app** để chuyển sang **In production**.
   - Khi đăng nhập, Google có thể hiện cảnh báo "Google hasn't verified this app". Vì app là của chính bạn, chọn **Advanced** rồi **Go to … (unsafe)**.
   - App chưa xác minh có bị giới hạn gì thêm không: **chưa xác minh**.

### B3. Tạo OAuth client

1. Vào **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Ở Application type, chọn **Desktop app**, rồi bấm **Create**. Tải file JSON về.
3. Chuyển file vào `secrets\google-oauth-client.json`. Trong `.env` đã có sẵn dòng `MAY_REELS_GOOGLE_CLIENT_SECRET=secrets/google-oauth-client.json`.

### B4. Đăng nhập một lần

```powershell
.\.venv\Scripts\python.exe -m pip install -r may_reels/requirements.txt
tools_local\py.cmd -m may_reels dang-nhap drive
tools_local\py.cmd -m may_reels dang-nhap youtube --kenh vanxuan
```

- Mỗi lệnh mở trình duyệt. Chọn đúng tài khoản Google rồi bấm đồng ý.
- Với YouTube: nếu tài khoản có nhiều kênh (Brand Account), hãy **chọn đúng kênh của trung tâm**.
- Token được lưu vào `secrets/google-drive-token.json` và `secrets/youtube-vanxuan.json`. Đường dẫn lấy theo biến `VANXUAN_YT_TOKEN_FILE` trong `.env`.
- Lệnh `dang-nhap youtube` in ra ID kênh (dạng `UC...`). Ghi ID này vào `brand/vanxuan/dang-bai.yaml`, mục `yt_shorts.kenh_id`. Máy kiểm tra token đúng kênh trước mỗi lần tải lên, và từ chối nếu không khớp.

### B5. Các ô còn để trống trong `dang-bai.yaml`

| Ô | Ý nghĩa | Để trống |
|---|---|---|
| `yt_shorts.made_for_kids` | Khai báo video có dành cho trẻ em không (`status.selfDeclaredMadeForKids`) | Không gửi; YouTube sẽ hỏi trong Studio |
| `yt_shorts.contains_synthetic_media` | Khai báo nội dung tổng hợp (giọng đọc TTS có cần khai không thì bạn quyết định) | Không gửi |
| `fb_reels.is_ai_generated` | Tham số `is_ai_generated` của Reels | Không gửi |
| `yt_shorts.category_id` | Danh mục YouTube | Không gửi |

---

## C. TikTok: đăng tay

Chưa cần cài gì thêm ngoài đăng nhập Drive (bước B4).
- Khi một dòng TikTok được Duyệt, lệnh `dang --that` chép video và file `caption.txt` vào Drive, thư mục **"Chờ đăng TikTok/<mã video>"**.
- Máy ghi `trang_thai_dang = cho_dang_tay`, và link thư mục được ghi vào cột `link_bai`.
- Bạn mở link, tải video về điện thoại rồi đăng tay.

Điều kiện để sau này chuyển sang đăng bằng API: `API-DANG-BAI.md` mục 3.

---

## D. Kiểm tra trước lần đăng thật đầu tiên

```powershell
tools_local\py.cmd -m may_reels hang-cho them --video "<đường dẫn mp4>" --kenh vanxuan --caption-file "<caption.txt>" --thu
tools_local\py.cmd -m may_reels hang-cho them --video "<đường dẫn mp4>" --kenh vanxuan --caption-file "<caption.txt>"
```

1. Chạy hai lệnh trên. Lệnh có `--thu` chỉ kiểm tra; lệnh thứ hai tải bản xem thử lên Drive và tạo các dòng trong Hàng chờ.
2. Trên tab **Hàng chờ**: xem video qua `link_xem_thu`, rồi chọn **Duyệt** ở cột `duyet`.
3. Chạy `tools_local\py.cmd -m may_reels dang` (chạy thử). Lệnh in ra những gì **sẽ** đăng, không gọi API nền tảng và không ghi Hàng chờ.
4. Chỉ khi đã chắc chắn mới chạy `tools_local\py.cmd -m may_reels dang --that`.

### Trạng thái trong cột `trang_thai_dang`

| Giá trị | Ý nghĩa | Bạn cần làm |
|---|---|---|
| *(trống)* | Chưa đăng | — |
| `dang_tai_len` | Máy đang tải lên | Chờ. Kẹt quá 30 phút thì máy tự chuyển sang `can_kiem_tra` |
| `da_dang` | Đã đăng; có `id_bai` và `link_bai` | — |
| `cho_dang_tay` | TikTok: đã chép sang Drive | Đăng tay |
| `loi_thu_lai` | Lỗi mạng hoặc vượt giới hạn; lần chạy sau máy tự thử lại | — |
| `loi` | Lỗi quyền hoặc lỗi nội dung (xem cột `loi`); máy không tự thử lại | Sửa nguyên nhân, rồi sửa ô này thành `loi_thu_lai` |
| `can_kiem_tra` | Không rõ bài đã lên chưa, hoặc đã lên nhưng chưa công khai | Kiểm tra trên nền tảng. Nếu chắc chắn bài **chưa** lên thì sửa ô thành `loi_thu_lai`; nếu đã lên thì giữ nguyên |

Dòng đã có `id_bai` thì máy **không bao giờ** đăng lại. Máy còn giữ một sổ đăng riêng trên máy này (`projects/_may_reels/so_dang.jsonl`): kể cả khi ghi lên Sheet bị lỗi, lần chạy sau máy vẫn biết video đã lên và chỉ sửa lại Sheet.
