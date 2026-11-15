# Máy Reels: cài đặt Google Sheet

Máy đọc và ghi Google Sheet "Máy Reels" bằng một **service account**: một tài khoản máy của Google Cloud. Service account chỉ thấy được những Sheet bạn chia sẻ cho nó. Bạn làm các bước dưới đây một lần. Toàn bộ đều miễn phí: Google Sheets API không cần bật thanh toán.

Thời gian: khoảng 15 phút.

---

## Bước 1. Tạo project trên Google Cloud

1. Mở https://console.cloud.google.com/ bằng tài khoản Google sẽ sở hữu Sheet.
2. Bấm ô chọn project ở thanh trên cùng, chọn **New Project**.
3. Đặt tên, ví dụ `may-reels`, rồi bấm **Create**. Đợi tạo xong và chắc chắn project này đang được chọn.

## Bước 2. Bật Google Sheets API

1. Vào menu ☰ → **APIs & Services** → **Library**.
2. Tìm **Google Sheets API**, mở ra và bấm **Enable**.

Máy chỉ xin quyền `spreadsheets`, nên không cần bật Google Drive API.

## Bước 3. Tạo service account

1. Vào menu ☰ → **IAM & Admin** → **Service Accounts** → **Create service account**.
2. Điền **Service account name**, ví dụ `may-reels`, rồi bấm **Create and continue**.
3. Ở bước **Grant this service account access to project**, **không chọn role nào**. Bấm **Continue**, rồi **Done**.
   Service account không cần quyền gì trên project. Quyền duy nhất nó cần là quyền sửa Sheet, cấp ở bước 6.

## Bước 4. Tạo file khóa JSON

1. Trong danh sách Service Accounts, bấm vào email vừa tạo. Email có dạng `may-reels@<project>.iam.gserviceaccount.com`.
2. Chọn tab **Keys** → **Add key** → **Create new key** → **JSON** → **Create**. Trình duyệt sẽ tải về một file `.json`.
3. Tạo thư mục `secrets` ở gốc repo. Chuyển file vừa tải vào đó và đổi tên thành `may-reels-sa.json`:

   ```powershell
   New-Item -ItemType Directory -Force secrets
   Move-Item "$env:USERPROFILE\Downloads\<tên file vừa tải>.json" secrets\may-reels-sa.json
   ```

4. Kiểm tra file khóa đã bị gitignore. Lệnh dưới phải in ra dòng `secrets/`:

   ```powershell
   git check-ignore -v secrets\may-reels-sa.json
   ```

Nếu Google báo không cho tạo khóa (lỗi nhắc tới `iam.disableServiceAccountKeyCreation`), nghĩa là tài khoản đang nằm trong một tổ chức chặn việc tạo khóa. Khi đó hãy dùng một tài khoản Gmail cá nhân, hoặc nhờ quản trị viên tổ chức. Tài liệu này **chưa xác minh** trường hợp đó.

**File khóa này giống như mật khẩu:**
- Không gửi qua chat hay email, không commit lên git.
- Nếu lỡ để lộ: vào lại tab **Keys**, xóa khóa đó, rồi tạo khóa mới.

## Bước 5. Tạo Sheet "Máy Reels"

1. Mở https://sheets.new, đặt tên Sheet là **Máy Reels**.
2. Sao chép **ID của Sheet** từ thanh địa chỉ. ID là đoạn nằm giữa `/d/` và `/edit`:

   ```
   https://docs.google.com/spreadsheets/d/<ĐÂY LÀ ID>/edit#gid=0
   ```

Không cần tự tạo tab hay cột. Lệnh `sheet init` ở bước 8 sẽ tạo.

## Bước 6. Chia sẻ Sheet cho service account

1. Trong Sheet, bấm **Chia sẻ** (Share).
2. Dán email của service account. Email nằm trong trường `client_email` của file khóa, hoặc xem lại ở bước 4.1.
3. Chọn quyền **Người chỉnh sửa** (Editor). **Bỏ chọn** "Thông báo cho mọi người", vì service account không có hộp thư.
4. Bấm **Chia sẻ**.

## Bước 7. Ghi cấu hình vào `.env`

Mở file `.env` ở gốc repo và điền hai dòng sau. File `.env` không được commit.

```
MAY_REELS_SA_JSON=secrets/may-reels-sa.json
MAY_REELS_SHEET_ID=<ID ở bước 5>
```

Đường dẫn tương đối được tính từ gốc repo.

## Bước 8. Cài thư viện và chạy

```powershell
.\.venv\Scripts\python.exe -m pip install -r may_reels/requirements.txt
tools_local\py.cmd -m may_reels sheet init --thu                  # xem trước, không ghi gì
tools_local\py.cmd -m may_reels sheet init                        # tạo 5 tab
tools_local\py.cmd -m may_reels sheet nap-chu-de --kenh vanxuan   # đẩy chủ đề lên tab Ý tưởng
```

Chạy lại các lệnh trên bao nhiêu lần cũng không sao: không tạo tab trùng, không tạo dòng trùng, và không đụng tới ô bạn đã điền. Mỗi lần chạy thật, máy thêm một dòng vào tab **Nhật ký**.

Lỗi hay gặp:

| Thông báo | Cách xử lý |
|---|---|
| `Chưa đặt MAY_REELS_SA_JSON` hoặc `MAY_REELS_SHEET_ID` | Làm lại bước 7. |
| `Không thấy file khóa service account` | File không nằm đúng đường dẫn đã ghi trong `.env` (bước 4.3). |
| `PERMISSION_DENIED` / `403` | Chưa chia sẻ Sheet cho đúng email service account (bước 6), hoặc chưa bật Sheets API (bước 2). |
| `SpreadsheetNotFound` / `404` | ID Sheet sai (bước 5). |

---

## Dùng Sheet thế nào

- **Cột nền vàng nhạt là cột của bạn.** Máy không bao giờ ghi vào các cột này. Mọi cột khác là cột của máy. Bạn có sửa thì lần chạy sau máy sẽ ghi lại giá trị của nó.
- **Ý tưởng**, cột `duyet_chu_de` (Chờ / Làm / Bỏ): chỉ chủ đề được chọn **Làm** mới được đưa vào sản xuất. Ô trống được hiểu là Chờ.
- **Hàng chờ**, cột `duyet` (Chờ duyệt / Duyệt / Sửa / Bỏ):
  - Chỉ dòng được chọn **Duyệt** mới được đăng.
  - Chọn **Sửa** thì ghi lý do vào `ghi_chu_sua`.
  - Ô trống được hiểu là Chờ duyệt.
- **Cần quay**, cột `trang_thai_quay` (Chưa quay / Đã quay / Không quay): đánh dấu sau khi bạn quay bổ sung xong.
- **Số liệu**, cột `tin_nhan`: bạn tự nhập số tin nhắn.
- Bạn được phép:
  - lọc, sắp xếp, chèn dòng hay cột, thêm cột riêng của mình;
  - mở Sheet trong lúc máy đang chạy.

  Máy tìm dòng theo khóa và tìm cột theo tên ở dòng 1, nên các thao tác này không làm máy ghi nhầm ô.
- **Không đổi tên ô tiêu đề ở dòng 1**, và không xóa cột của máy. Nếu lỡ làm, chạy lại `sheet init`: máy sẽ thêm lại cột còn thiếu vào cuối bảng.

Khóa của từng tab, dùng để máy tìm đúng dòng:

| Tab | Khóa |
|---|---|
| Ý tưởng | `kenh` + `ma` |
| Hàng chờ | `ma_video` + `nen_tang` |
| Cần quay | `ma_yeu_cau` |
| Số liệu | `ma_video` + `nen_tang` + `moc_ngay` |
| Nhật ký | không có khóa, chỉ thêm dòng |

Danh sách cột của từng tab chỉ khai báo ở một chỗ: `may_reels/cot_sheet.py`.
