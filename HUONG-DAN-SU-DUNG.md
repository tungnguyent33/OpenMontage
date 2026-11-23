# Hướng dẫn sử dụng OpenMontage

OpenMontage là hệ thống dựng video do trợ lý AI điều khiển (Claude Code, Cursor, Codex...). Bạn **không chạy một lệnh "làm video"** nào cả. Bạn mở thư mục này trong Claude Code, nói bằng lời mình muốn video gì, rồi trợ lý tự đi qua từng bước: nghiên cứu → kịch bản → kế hoạch cảnh → tạo tư liệu → dựng → xuất file. Ở các bước sáng tạo, trợ lý **dừng lại chờ bạn duyệt**.

---

## 1. Cài đặt lần đầu (Windows)

**Cần có sẵn:** Python 3.10 trở lên, FFmpeg, Node.js (bản 22.23.4+ / 24.22.1+ / 26.12.1+), Claude Code.

Mở PowerShell tại thư mục `OpenMontage\OpenMontage` rồi chạy:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install "pip>=26.2.2"
python -m pip install -r requirements.txt
cd remotion-composer; npm install; cd ..
python -m pip install piper-tts
Copy-Item .env.example .env      # bỏ qua nếu đã có .env
```

- Nếu `npm install` báo lỗi `ERR_INVALID_ARG_TYPE`, chạy `npx --yes npm install` thay thế.
- Có `make` (Git Bash) thì chỉ cần `make setup`.
- Máy hiện tại đã có `.venv` và `.env`, nên chỉ cần **kích hoạt môi trường** mỗi lần dùng:
  `.\.venv\Scripts\Activate.ps1`

**In tiếng Việt không lỗi (PYTHONUTF8=1).** Console Windows mặc định dùng cp1252, nên Python báo `UnicodeEncodeError` khi in chữ có dấu. Chọn một trong ba cách:

```powershell
$env:PYTHONUTF8 = "1"                       # cho phiên PowerShell hiện tại
tools_local\py.cmd <script.py> [tham số]    # wrapper: tự đặt PYTHONUTF8=1 rồi gọi Python của .venv
setx PYTHONUTF8 1                           # đặt vĩnh viễn cho tài khoản Windows (mở lại PowerShell)
```

**Kiểm tra máy có những công cụ gì:**

```powershell
make preflight
# hoặc
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.support_envelope(), indent=2))"
```

---

## 2. Khóa API (tùy chọn)

Mọi khóa đều **không bắt buộc**. Không có khóa nào vẫn làm được video bằng công cụ miễn phí: giọng Piper/VieNeu, cảnh quay sẵn có trong kho kênh, kho miễn phí (Archive.org, NASA, Wikimedia), dựng bằng Remotion/HyperFrames, xử lý bằng FFmpeg.

Muốn thêm, mở file `.env` và điền:

| Khóa | Dùng để |
|---|---|
| `PEXELS_API_KEY`, `PIXABAY_API_KEY`, `UNSPLASH_ACCESS_KEY` | Ảnh/video stock miễn phí (đăng ký free) |
| `FAL_KEY` | Ảnh FLUX, video Kling/Veo/MiniMax (trả phí) |
| `ELEVENLABS_API_KEY` | Giọng đọc cao cấp, nhạc, hiệu ứng âm thanh |
| `OPENAI_API_KEY`, `GOOGLE_API_KEY` | Giọng đọc, tạo ảnh |
| `SUNO_API_KEY` | Nhạc nền theo yêu cầu |

Chi tiết giá và gói miễn phí: `docs/PROVIDERS.md`.

> Không chia sẻ file `.env` cho ai, không đưa lên GitHub.

---

## 3. Làm một video — quy trình thường ngày

### Bước 1: Mở Claude Code trong thư mục dự án

```powershell
cd "C:\Users\Thinkpad P15V3\Desktop\Claude code\OpenMontage\OpenMontage"
claude
```

### Bước 2: Nói yêu cầu bằng tiếng Việt

Càng rõ càng tốt: **chủ đề, độ dài, khổ (dọc 9:16 / ngang), nền tảng, có lời đọc hay không, có nhạc hay không, kênh nào**.

Ví dụ cho kênh Vạn Xuân:

```text
Làm video Short 45 giây dọc 9:16 cho kênh vanxuan, chủ đề "Đi xe máy có được đeo tai nghe không?".
Giọng nam đọc, phụ đề, dùng cảnh quay trong kho kênh, không nhạc, chỉ dùng công cụ miễn phí.
```

Các ví dụ khác:

```text
Làm video giải thích hoạt hình 60 giây về cách mạng nơ-ron học, có lời đọc và phụ đề.
Đây là link một video TikTok mình thích, làm cho mình video tương tự nhưng về chủ đề ôn thi A1.
Làm phim tư liệu 75 giây về thành phố trong mưa, chỉ dùng cảnh quay thật, không lời đọc, có nhạc.
```

Xem thêm câu lệnh mẫu trong `PROMPT_GALLERY.md`.

### Bước 3: Duyệt ở các điểm dừng

Trợ lý sẽ dừng để hỏi bạn ở những chỗ quan trọng:

1. **Đề xuất / ý tưởng** — hướng làm, công cụ dùng, ước tính chi phí.
2. **Kịch bản + kế hoạch cảnh** — lời đọc, cảnh nào đi với câu nào.
3. **Khung xem trước** — vài ảnh chụp từ video trước khi xuất bản cuối.

Trả lời ngắn gọn là được: `ok, tiếp tục đi`, hoặc nói cụ thể chỗ cần sửa (`câu 3 đổi thành...`, `bỏ nhạc`, `chữ to hơn`).

### Bước 4: Nhận file

Video cuối nằm trong `projects/<tên-dự-án>/renders/`. Trước khi đưa cho bạn, trợ lý tự kiểm tra: độ dài, khung hình, âm lượng (chuẩn −14 LUFS), phụ đề.

---

## 4. Theo dõi tiến độ trực quan — Backlot

Backlot là bảng theo dõi chạy trên máy, tự cập nhật khi trợ lý làm việc: bước nào xong, kịch bản, ảnh từng cảnh, chi phí đã tiêu.

```powershell
python -m backlot open                 # danh sách mọi dự án
python -m backlot open vx-demo-01      # bảng của một dự án
python scripts/backlot_simulate_run.py # xem thử một lượt chạy giả lập
```

---

## 5. Dữ liệu kênh (brand)

Mỗi kênh có **một thư mục riêng** trong `brand/` để mọi video dùng đúng màu, font, logo, số điện thoại, câu kêu gọi (CTA), hashtag, kho cảnh quay và quy tắc của kênh đó. Các kênh không dùng chung file nào.

```
brand/vanxuan/
├── brand.json            sinh tự động — đừng sửa tay
├── quy-tac-rieng.yaml    sửa tay — cụm từ cấm, quy tắc nội dung, nguồn cảnh bị loại
├── cau-hinh.yaml         sửa tay — tiền tố mã video, thư mục video, font cần chép
├── assets/               logo, fonts
└── _local/               sinh tự động, KHÔNG commit (gitignore) — toàn văn context/*.md của kênh
```

Hiện có: **`brand/vanxuan/`** — Đào tạo lái xe Vạn Xuân (màu navy `#0E3970`, xanh `#048DD1`, cam `#E4661F`; font Be Vietnam Pro). Chi tiết xem `brand/README.md`.

**Đổi quy tắc riêng của kênh** (vd. thêm cụm từ cấm): sửa `brand/vanxuan/quy-tac-rieng.yaml` rồi chạy lại lệnh nạp bên dưới.

**Cập nhật lại khi dữ liệu kênh thay đổi** (thư mục kênh gốc chỉ được đọc, không bị sửa):

```powershell
tools_local\py.cmd tools_local/nap_kenh.py --id vanxuan
```

Lệnh này đọc thư mục kênh từ biến `KENH_GOC_DIR` trong `.env`. Biến này trỏ tới **thư mục chứa các kênh**, không phải thư mục của một kênh:

```
KENH_GOC_DIR='C:/<đường dẫn>/video-agent-team/channels'
```

Muốn chỉ định thẳng một thư mục kênh thì vẫn dùng được `tools_local\py.cmd tools_local/nap_kenh.py "<thư mục kênh>"`.

`brand.json` **không chứa đường dẫn tuyệt đối**, vì repo đang public. Cảnh trong kho chỉ ghi `file_tuong_doi`, nên file thật nằm ở `$KENH_GOC_DIR/<mã-kênh>/<file_tuong_doi>`. Toàn văn `context/*.md` được chép sang `brand/<mã-kênh>/_local/context/`. Thư mục này bị gitignore, đừng commit nó.

**Thêm kênh mới:**
1. Tạo `brand/<mã-kênh>/cau-hinh.yaml` theo mẫu của Vạn Xuân, gồm `tien_to_ma_video`, `thu_muc_video` và `fonts`. Thiếu file này thì lệnh nạp vẫn chạy, nhưng ghi `canh_bao`: không dò được chủ đề đã làm và không chép font.
2. Nếu kênh có quy tắc riêng, tạo thêm `quy-tac-rieng.yaml`.
3. Chạy lệnh nạp với `--id <mã-kênh>`.

Kênh mới nằm riêng ở `brand/<mã-kênh>/`, không ảnh hưởng đến Vạn Xuân. Khi yêu cầu video, nói rõ `cho kênh <mã-kênh>`.

---

## 6. Cấu trúc một dự án (ví dụ `projects/vx-demo-01`)

| File / thư mục | Nội dung |
|---|---|
| `project.json` | Tên, loại quy trình, kênh |
| `nhat-ky.md` | Nhật ký từng bước: giờ, công cụ, chi phí, ghi chú |
| `ban-chep-loi.md` | Bản chép lời đọc để duyệt |
| `artifacts/` | `brief.json`, `script.json`, `scene_plan.json`, nhật ký quyết định |
| `assets/` | Giọng đọc, ảnh, nhạc, video tư liệu |
| `hf/` | Dự án HyperFrames (dựng hình bằng HTML) |
| `preview/` | Ảnh xem trước để duyệt |
| `renders/` | **Video thành phẩm** |
| `checkpoint_*.json` | Điểm lưu — trợ lý làm tiếp được từ đây nếu bị ngắt |

Các script trong dự án mẫu (chạy bằng `python <tên>.py` trong thư mục dự án):

| Script | Việc làm |
|---|---|
| `kich_ban.py` | Ghi kịch bản + kế hoạch cảnh ra `artifacts/` |
| `sinh_giong.py` | Sinh giọng đọc VieNeu (giọng "Hải Đăng"), miễn phí, chạy CPU |
| `ghep_giong.py` | Ghép các đoạn giọng đã có, không sinh lại |
| `nghe_lai.py` | Nghe lại giọng bằng PhoWhisper để lấy mốc thời gian từng chữ |
| `can_phu_de.py` | Khớp chữ phụ đề đúng nguyên văn kịch bản với mốc giọng |
| `chuan_bi_canh.py` | Cắt cảnh từ kho kênh ra 1080×1920, 30 fps |
| `dung_hf.py` | Viết dự án HyperFrames từ dữ liệu đã duyệt |

**Muốn sửa video đã làm:** chỉ cần nói với trợ lý, ví dụ `Trong vx-demo-01, đổi câu cuối thành ... rồi xuất lại`. Trợ lý sẽ sửa đúng bước cần thiết, không làm lại từ đầu.

---

## 7. Các loại video (pipeline)

| Loại | Dùng khi |
|---|---|
| Animated Explainer | Video giải thích, giáo dục |
| Animation | Chữ động, đồ họa chuyển động |
| Talking Head | Có cảnh quay người nói |
| Screen Demo | Quay màn hình hướng dẫn phần mềm |
| Hybrid | Cảnh quay thật + đồ họa bổ sung (dự án vx-demo-01 dùng loại này) |
| Documentary Montage | Ghép cảnh quay thật từ kho miễn phí |
| Clip Factory | Cắt một video dài thành nhiều clip ngắn |
| Podcast Repurpose | Biến podcast thành video |
| Localization & Dub | Dịch, lồng tiếng, phụ đề video có sẵn |
| Cinematic | Trailer, teaser |
| Avatar Spokesperson | Người dẫn ảo |
| Character Animation | Hoạt hình nhân vật SVG |

Không cần nhớ tên — trợ lý tự chọn theo yêu cầu. Nói rõ nếu muốn ép một loại.

---

## 8. Kiểm soát chi phí

Thiết lập trong `config.yaml`, mục `budget`:

- `total_usd: 10.00` — trần chi phí cho mỗi dự án.
- `single_action_approval_usd: 0.50` — việc nào tốn trên $0,50 phải hỏi bạn trước.
- `require_approval_for_new_paid_tool: true` — dùng công cụ trả phí mới lần đầu phải hỏi.
- `mode: warn` — cảnh báo khi gần hết. Đổi sang `cap` để chặn cứng.

Muốn chắc chắn 0 đồng: thêm câu **"chỉ dùng công cụ miễn phí"** vào yêu cầu.

---

## 9. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Activate.ps1 cannot be loaded` | Chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ffmpeg is not recognized` | Cài FFmpeg và thêm vào PATH, mở lại terminal |
| `npm install` lỗi `ERR_INVALID_ARG_TYPE` | Dùng `npx --yes npm install` |
| Giọng đọc sai số / từ viết tắt (vd. "150cc" thành "xi si") | Yêu cầu trợ lý viết cách đọc riêng, vd. "150 phân khối"; chữ trên màn hình vẫn giữ nguyên |
| HyperFrames lỗi khi dựng | `make hyperframes-doctor` |
| Thiếu công cụ / không thấy nhà cung cấp | `make preflight` để xem máy đang có gì |
| Muốn xem thử không cần khóa | `make demo` (xem danh sách: `make demo-list`) |

---

## 10. Máy Reels (đang xây: sản xuất vào Hàng chờ chạy được; đăng bài tạm hoãn)

Máy Reels là dự án biến nhánh `kenh-vanxuan` thành máy tự sản xuất và đăng video dọc 9:16 (Facebook Reels, YouTube Shorts, TikTok) cho từng kênh. Bạn chỉ duyệt trên Google Sheet ở hai chỗ: duyệt chủ đề và duyệt video trước khi đăng. Hiện đã có lớp nối Google Sheet (`may_reels/`). Phần sản xuất và đăng video chưa có. Tài liệu:

- `docs/may-reels/TRANG-THAI.md`: **cửa vào**: Máy Reels đang ở đâu, các lệnh, bản đồ file, việc đang dở, việc chờ bạn, việc tiếp theo.
- `docs/may-reels/NGUYEN-TAC.md`: nguyên tắc phát triển (code đặt ở đâu, Sheet là nguồn sự thật về duyệt, đăng bài mặc định chạy thử, quy tắc cấm của kênh, bí mật, chi phí, quy tắc kết thúc phiên).
- `docs/may-reels/QUYET-DINH.md`: các quyết định đã chốt (câu 1–19 ngày 2026-11-15 và các quyết định sau), mục C là những gì còn chưa chốt.
- `docs/may-reels/KE-HOACH.md`: sơ đồ luồng, cách chạy không dừng, các rủi ro còn hiệu lực.
- `docs/may-reels/NHAT-KY-PHAT-TRIEN.md`: lịch sử từng phiên phát triển (mới nhất ở trên).

- `docs/may-reels/CAI-DAT-GOOGLE.md`: tạo service account, chia sẻ Sheet, cách dùng các cột trên Sheet.
- `docs/may-reels/CAI-DAT-DANG-BAI.md`: app Meta và Page token, OAuth client cho YouTube và Drive, ý nghĩa các trạng thái đăng.
- `docs/may-reels/API-DANG-BAI.md`: tóm tắt API đăng bài từ tài liệu chính thức, kèm ngày đọc.

Khóa và file service account (ví dụ khóa Google Sheet) để trong thư mục `secrets/`, thư mục này đã được gitignore.

**Google Sheet "Máy Reels"** (làm theo `CAI-DAT-GOOGLE.md` trước, điền `MAY_REELS_SA_JSON` và `MAY_REELS_SHEET_ID` trong `.env`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r may_reels/requirements.txt   # một lần
tools_local\py.cmd -m may_reels sheet init --thu                          # xem trước, không ghi
tools_local\py.cmd -m may_reels sheet init                                # tạo 5 tab: Ý tưởng, Hàng chờ, Cần quay, Số liệu, Nhật ký
tools_local\py.cmd -m may_reels sheet nap-chu-de --kenh vanxuan           # đẩy chủ đề của kênh lên tab Ý tưởng
```

- Chạy lại bao nhiêu lần cũng không tạo tab trùng hay dòng trùng.
- Cột nền vàng là cột của bạn, máy không ghi vào đó.
- Trên tab Ý tưởng, chọn **Làm** để duyệt một chủ đề. Trên tab Hàng chờ, chọn **Duyệt** để cho đăng.

**Sản xuất video vào Hàng chờ**

Cấu hình một lần:
- Trong `.env`, đặt `MAY_REELS_XEM_THU_DIR` là thư mục đồng bộ của Google Drive for desktop. Máy chép bản xem thử vào đây.
- Có thể đặt thêm `MAY_REELS_XEM_THU_LINK` là link của thư mục đó trên Drive.
- Các quyết định sản xuất của kênh nằm trong `brand/<kênh>/san-xuat.yaml`:
  - runtime HyperFrames, giọng VieNeu "Hải Đăng", không nhạc;
  - 1080×1920, 30 fps, 30–50 giây;
  - phụ đề, màn kết có logo và hotline;
  - trần chi phí 0 USD;
  - khung nhịp cho từng trụ cột nội dung.

**Chiến lược nội dung và dữ liệu bán hàng (từ 2026-11-20).** Nguồn sự thật về nội dung là `docs/may-reels/CHIEN-LUOC-NOI-DUNG.md`. File này chỉ có trên máy, không lên GitHub. Máy đọc 5 file trong `brand/vanxuan/`:

- `doi-tuong.yaml` (5 nhóm người mua), `dinh-vi.yaml` (lời hứa), `ban-hang.yaml` (học phí, giấy tờ, lịch khai giảng, ưu đãi, mồi nhử, người đồng ý lên hình). Ba file này có dữ liệu kinh doanh thật nên **chỉ để trên máy**. Repo chỉ có bản mẫu `*.mau.yaml`. Máy khác cần tạo từ bản mẫu, ví dụ: `copy brand\vanxuan\ban-hang.mau.yaml brand\vanxuan\ban-hang.yaml`.
- `dinh-dang.yaml` (16 định dạng, có khung nhịp) và `lich.yaml` (lịch tuần, mùa): commit bình thường.
- **Máy không tự điền `ban-hang.yaml`.** Bạn điền và đổi `trang_thai` thành `da_xac_nhan` khi chắc chắn. Số chưa chắc (ví dụ học phí trong bài Facebook cũ) để ở mục `cho_xac_nhan`, máy không dùng mục này. Định dạng "Học phí gồm gì", "Đăng ký cần mang gì", "Lịch khai giảng", "Học viên kể" chỉ làm được khi mục tương ứng đã xác nhận.
- Không ghi họ tên, số điện thoại hay ảnh học viên vào `ban-hang.yaml`. Người đồng ý lên hình chỉ ghi mã (ví dụ `hv-01`), vai trò và ngày đồng ý.

```powershell
tools_local\py.cmd -m may_reels chien-luoc kiem-tra --kenh vanxuan              # tóm tắt
tools_local\py.cmd -m may_reels chien-luoc kiem-tra --kenh vanxuan --chi-tiet   # liệt kê hết ô trống, giả thuyết
```

Báo cáo gồm: thiếu file, lỗi cấu trúc, tham chiếu sai (mã nhóm, mã định dạng, khung nhịp), mùa đang chạy, ưu đãi hết hạn, định dạng chưa làm được vì thiếu số liệu, định dạng thiếu cảnh trong kho (ví dụ chưa có cảnh "thầy nói trước máy"), ô trống, số chờ xác nhận, giả thuyết chưa xác nhận. Lệnh trả mã 1 nếu có lỗi cấu trúc hoặc tham chiếu.

**Bộ biên kịch: kịch bản được biên tập trước khi dựng (từ 2026-11-21).** Mỗi video `san-xuat` qua các bước sau:

1. Agent viết lời theo `skills/may-reels/bien-kich.md`:
   - chọn nhóm đối tượng và nỗi lo;
   - viết 3 góc kể;
   - viết 5 hook theo 5 công thức trong `brand/vanxuan/hook.yaml`, mỗi hook có hình, câu nói, chữ;
   - viết bản 1, đọc to, sửa thành bản 2.
2. Máy kiểm chữ: hook dài, câu dài, cụm từ cấm, câu sáo, kiểu câu văn AI.
3. Một biên tập riêng chấm kịch bản theo `brand/vanxuan/rubric-kich-ban.yaml`. Biên tập không đọc được lập luận của người viết.
4. Dưới 75 điểm thì người viết sửa, tối đa 2 vòng, rồi mới sinh giọng và dựng.

Hàng chờ có thêm cột `diem_kich_ban` (điểm biên tập) và `cong_thuc_hook` (công thức hook đã dùng). Chạy `sheet init` một lần để thêm 2 cột này. Dưới ngưỡng thì cột `canh_bao` ghi "Kịch bản dưới ngưỡng".

- **Kịch bản mẫu chờ bạn duyệt:** `brand/vanxuan/kich-ban-mau/`, mỗi định dạng một file.
  - Bạn sửa lời và điền các ô `[chờ anh xác nhận]` ngay trong file, nhưng **không ghi số bán hàng thật vào đây** (file lên GitHub), chỉ ghi lời.
  - Xong thì đổi `trang_thai: cho_duyet` thành `da_duyet`. Máy chỉ học theo mẫu đã duyệt.
- **Thư viện tay nghề** (sửa tay): `hook.yaml`, `giong-noi.yaml` (xưng hô, từ tránh, cách nói số), `giu-chan.yaml`, `rubric-kich-ban.yaml` (tiêu chí, ngưỡng, giới hạn âm tiết). Mọi mục đều là `gia_thuyet` cho tới khi buổi xem lại hằng tuần có số liệu.
- **So sánh trước sau** (chỉ viết kế hoạch, không dựng, không ghi Sheet):

```powershell
tools_local\py.cmd -m may_reels bien-kich so-sanh --ma vx-006-giao-nhau-khong-bao-hieu --ma vx-007-vong-xuyen
```

Báo cáo nằm ở `projects/_may_reels/so-sanh/BAO-CAO.md`, gồm:
- lời cũ cạnh lời mới;
- 5 hook;
- điểm từng tiêu chí;
- thời gian và chi phí thêm mỗi video.

Biên tập hỏng ở video nào thì điểm video đó ghi "lỗi" (không phải 0). Máy thử lại 1 lần rồi chạy tiếp video sau.

**Nguồn luật: máy tra, bạn xác nhận.** `san-xuat` từ chối chủ đề có nội dung luật mà `nguon_doi_chieu` chưa ghi tới mức khoản. Với QCVN, mức cần đạt là mục, phụ lục hoặc số hiệu biển/vạch. Mỗi lần nhắc một Điều đều phải có khoản. Lý do từ chối ghi ở cột `ghi_chu_may` của tab Ý tưởng. Chủ đề ghi "Không cần nguồn luật" thì không bị kiểm tra.

```powershell
tools_local\py.cmd -m may_reels nguon-luat --kenh vanxuan            # agent tra điều khoản cho chủ đề còn thiếu
tools_local\py.cmd -m may_reels nguon-luat ap-dung --kenh vanxuan    # chép nguồn bạn đã xác nhận "Đúng" vào chu-de.md
```

1. `nguon-luat` gọi agent (`skills/may-reels/tra-nguon-luat.md`). Agent mở văn bản chính thức, ưu tiên `chinhphu.vn` và `vbpl.vn`, kiểm tra hiệu lực, rồi ghi lên tab Ý tưởng:
   - `nguon_de_xuat` (văn bản, điều, khoản, điểm);
   - `trich_nguyen_van`;
   - `link_nguon`;
   - `ngay_tra`.

   Không tìm được điều khoản khớp thì ô đề xuất để trống, lý do ghi ở `ghi_chu_may`. Nếu `y_chinh` mâu thuẫn với văn bản, `ghi_chu_may` ghi "MÂU THUẪN y_chinh", và máy không tự sửa `y_chinh`. Chủ đề đã có giá trị ở `xac_nhan_nguon` thì không bị tra đè.
2. Bạn đọc đoạn trích và mở link, rồi chọn `xac_nhan_nguon` = **Đúng** hoặc **Sai**. Máy không bao giờ tự áp dụng đề xuất chưa được xác nhận.
3. `nguon-luat ap-dung` xử lý từng dòng theo xác nhận:
   - **Đúng:** máy sao lưu `chu-de.md` trong thư mục kênh gốc thành `chu-de.md.bak-<giờ>`, chỉ đổi ô nguồn của dòng đó, rồi chạy `nap_kenh.py` và `sheet nap-chu-de`.
   - **Sai:** máy giữ nguyên và in nhắc. Bạn sửa `y_chinh` trong `chu-de.md`, xóa ô `xac_nhan_nguon`, rồi chạy lại `nguon-luat`.

```powershell
tools_local\py.cmd -m may_reels san-xuat --kenh vanxuan --so-luong 3   # các chủ đề đã chọn "Làm" -> Hàng chờ
tools_local\py.cmd -m may_reels sua                                     # dựng lại các dòng chọn "Sửa" theo ghi_chu_sua
tools_local\py.cmd -m may_reels dung-lai --ma vx-007                    # dựng lại theo mẫu mới, giữ nguyên kế hoạch
tools_local\py.cmd -m may_reels dung --du-an <ma_video>                 # dựng lại một dự án có sẵn ke_hoach.json
```

- **`san-xuat`** xử lý từng chủ đề như sau:
  1. Gọi Claude Code không tương tác (`claude -p`) với skill `skills/may-reels/san-xuat-khong-hoi.md`. Agent chỉ viết `projects/<mã video>/ke_hoach.json` (lời đọc, thẻ chữ, nguồn luật, cảnh từ kho, caption).
  2. Máy tự dựng: sinh giọng có nghe lại, cắt cảnh, HyperFrames, tự kiểm, chấm điểm QA.
  3. Video đạt thì vào **Hàng chờ** với `duyet` = "Chờ duyệt". Thiếu cảnh thật thì vào **Cần quay**.

  Điểm dưới 75 sau 2 vòng sửa thì video vẫn vào Hàng chờ, kèm cảnh báo "Dưới ngưỡng". Job hỏng không làm dừng job khác. Mỗi job ghi một dòng vào Nhật ký, gồm thời gian chạy và số lượt chạy trợ lý.
- **Thời gian:** mỗi video mất khoảng 20–40 phút trên máy này. Phần lâu nhất là sinh và nghe lại giọng trên CPU. Giới hạn thời gian của agent và của bước dựng đặt bằng `MAY_REELS_GIAY_AGENT` và `MAY_REELS_GIAY_DUNG`.
- **Duyệt trên tab Hàng chờ:**
  - Chọn **Duyệt** để cho đăng.
  - Chọn **Sửa** và ghi lý do vào `ghi_chu_sua`, rồi chạy lệnh `sua`. Máy sửa kế hoạch, dựng lại (đoạn giọng không đổi thì dùng lại), cập nhật bản xem thử (tên file có hậu tố `-v2`, `-v3`…) và đưa ô về "Chờ duyệt".
  - **Chỉ đổi mẫu đồ họa, không đổi nội dung** (ví dụ cỡ chữ, bố cục sơ đồ): `sua` sẽ báo "không đổi" vì kế hoạch giữ nguyên. Dùng `dung-lai --ma <mã>` (nhận mã rút gọn như `vx-007`): máy dựng lại theo mẫu hiện tại, chấm lại, tạo bản xem thử `-v<n>` mới và đưa các dòng về "Chờ duyệt". Lệnh từ chối nếu mã có dòng đã "Duyệt", "Bỏ" hoặc đã đăng.
  - Muốn sửa một nền tảng thì các nền tảng khác của cùng video cũng phải chưa chọn "Duyệt"/"Bỏ", vì máy không thay video đã có lời duyệt.
- **Thư mục đăng tay** của từng nền tảng (video + `description.txt`) được ghi ở cột `ghi_chu_may`.
- **Thiếu cảnh thật:** máy dùng **cảnh tạm** là sơ đồ động (ngã tư, vòng xuyến, chữ lớn), vẽ bằng code, không AI, không stock. Video vẫn vào Hàng chờ kèm cảnh báo "Có cảnh tạm", và tab **Cần quay** vẫn ghi yêu cầu quay.
- **Thay cảnh tạm bằng cảnh thật:**
  1. Quay xong thì chọn **Đã quay** ở cột `trang_thai_quay` trên tab Cần quay.
  2. Chép file vào `canh-quay/moi-quay/` rồi nạp kho cảnh (xem mục "Kho cảnh" bên dưới).
  3. Chạy lệnh thay cảnh:

  ```powershell
  tools_local\py.cmd -m may_reels kho nap --kenh vanxuan
  tools_local\py.cmd -m may_reels thay-canh                              # thay sơ đồ bằng cảnh thật, dựng lại, cập nhật Hàng chờ
  tools_local\py.cmd -m may_reels san-xuat --kenh vanxuan --ca-cho-quay  # dựng lại cả chủ đề đang "chờ quay" bằng cảnh tạm
  ```
- **Máy ngủ:** trong lúc `san-xuat`, `sua`, `thay-canh`, `dung` chạy, máy được giữ không tự ngủ (Windows `SetThreadExecutionState`), nhưng **gập máy thì vẫn ngủ** và lô sẽ dừng theo. Giới hạn thời gian `MAY_REELS_GIAY_DUNG` tính cả lúc máy ngủ, nên job đang chạy sẽ bị đánh dấu lỗi. Chạy lại job lỗi bằng `san-xuat --kenh vanxuan --ca-loi`.
- **Điểm QA trên Sheet (`diem_qa`) là điểm nội dung theo rubric** `brand/<kênh>/rubric.yaml` (tổng 100). Mọi trọng số và ngưỡng nằm trong file đó:

  | Tiêu chí | Điểm | Ai chấm |
  |---|---|---|
  | Hook 0–3 giây | 20 | agent; máy áp trần nếu chữ muộn hơn 0,5 giây hoặc 3 giây đầu đứng yên |
  | Đúng và có giá trị | 15 | agent |
  | Nhịp: không quá 4 giây không đổi hình hoặc không nhấn | 10 | máy |
  | Chân thực: tỉ lệ thời lượng cảnh quay thật; dưới 60% thì tối đa 5 điểm, cảnh báo "Nhiều cảnh tạm" | 15 | máy |
  | Phụ đề đọc được | 10 | agent; máy áp trần nếu quá 2 dòng, ra ngoài vùng an toàn hoặc thiếu tương phản |
  | Thương hiệu: màu, font, logo, màn kết | 10 | máy |
  | CTA | 10 | agent; máy áp trần nếu CTA không nguyên văn hoặc có nhiều CTA |
  | Kỹ thuật: quy đổi từ `diem_ky_thuat` (ffprobe, LUFS, khung đen, phụ đề) | 10 | máy |

  - Agent chấm bằng skill `skills/may-reels/cham-diem.md`, **trên video đã render**: khung hook ở 0 / 0,5 / 1,5 / 3 giây, lưới khung, lời PhoWhisper nghe được từ âm thanh cuối. Kết quả ghi ở `projects/<mã>/renders/score.json`, mỗi tiêu chí có điểm và một câu lý do.
  - **Trần tổng:** hook dưới 8 điểm, hoặc cảnh thật dưới 40% thời lượng, thì tổng tối đa 70.
  - **Chặn cứng:** máy không đưa video vào Hàng chờ (job sang `loi`) nếu gặp một trong ba trường hợp sau:
    - nghe thấy hoặc nhìn thấy cụm từ cấm hay câu sáo đã chốt, kể cả khi viết không dấu;
    - có con số hoặc số hiệu luật không nằm trong `y_chinh`/`nguon_doi_chieu` của chủ đề (số điện thoại, địa chỉ, CTA của kênh và số đếm 1–10 được miễn);
    - có tài sản không thuộc kho kênh hoặc brand.
  - Chặn số hiệu luật rất chặt. Nếu `nguon_doi_chieu` chỉ ghi "Luật 36/2024/QH15 (điều về …)" thì một video nói "Điều 22" sẽ bị chặn. Có hai cách gỡ: ghi rõ điều khoản vào `nguon_doi_chieu` của chủ đề, hoặc thêm `nguon_luat_da_mo` vào `rubric.yaml` mục `chan_cung.nguon_so_cho_phep` để cho phép nguồn agent đã mở và trích nguyên văn.
  - **Dưới ngưỡng** (`san-xuat.yaml` mục `cham_diem.nguong`): máy gửi lý do trừ điểm cho agent sửa kế hoạch, tối đa 2 vòng. Vẫn dưới ngưỡng thì video vào Hàng chờ, cột `canh_bao` ghi "Dưới ngưỡng (điểm/ngưỡng)" và 2 lý do nặng nhất. Cột `canh_bao` có tối đa 3 dòng.
  - **Hiệu chỉnh theo bạn:** ghi `diem_cua_toi` (1–10) và `nhan_xet` trên tab Hàng chờ. Đây là cột của bạn, máy không ghi vào. Chưa có hai cột này thì chạy `sheet init`: lệnh này thêm cột còn thiếu và không tạo trùng.

  ```powershell
  tools_local\py.cmd -m may_reels cham-lai --kenh vanxuan     # chấm lại mọi video trong Hàng chờ, không dựng lại
  tools_local\py.cmd -m may_reels hieu-chinh --kenh vanxuan   # so điểm máy với điểm của bạn, đề xuất sửa rubric.yaml
  ```

  `hieu-chinh` **chỉ đề xuất**, không sửa `rubric.yaml`. Báo cáo lưu ở `projects/_may_reels/hieu-chinh/<kênh>-<ngày>.md`.
- **Bản xem thử trên Drive chỉ để duyệt.** Máy chép lên `MAY_REELS_XEM_THU_DIR` một bản nhẹ (720×1280, CRF 28, tiếng AAC 96k, cấu hình ở `san-xuat.yaml` mục `xem_thu`). **Đăng tay thì lấy file trong thư mục `exports/`** của dự án (đường dẫn ở cột `ghi_chu_may`), đó là bản đủ chất lượng. Khi `sua` tạo bản `-v<n>` mới, máy xóa bản xem thử cũ của cùng mã video trong thư mục Drive.
- **Dung lượng ổ đĩa:**
  - Bản cuối nén một lần ngay trong `hyperframes render` (`san-xuat.yaml` mục `xuat`: CRF 20, tối đa 12 Mb/s). Bước chuẩn hóa tiếng không nén lại hình. Thử với vx-006: dung lượng từ 42 MB xuống 19 MB, SSIM 0,9925, điểm QA không đổi.
  - Cảnh trung gian `hf/assets/video/*.mp4` (CRF 18) bị xóa sau khi compose đạt. `sua`, `thay-canh` và `dung --stage compose` tự cắt lại từ kho kênh khi thiếu. Cache giọng `assets/audio/_da_dat/` và ảnh kiểm tra `review/` được giữ.
  - Bản đóng gói đăng tay dùng hard link nên không tốn thêm chỗ. HyperFrames từ chối render khi ổ còn dưới khoảng 1 GB.

  ```powershell
  tools_local\py.cmd -m may_reels dung-luong            # dung lượng theo dự án và theo loại, cộng thư mục xem thử
  tools_local\py.cmd -m may_reels dung-luong --cache    # thêm cache dùng chung (model, npm/npx) và cách dọn; không xóa
  tools_local\py.cmd -m may_reels don-dep               # CHẠY THỬ: in sẽ xóa gì, giải phóng bao nhiêu MB
  tools_local\py.cmd -m may_reels don-dep --that        # xóa thật, ghi một dòng Nhật ký
  ```

  `don-dep` đọc tab Hàng chờ:
  - Mã video có **mọi** nền tảng chọn **Bỏ**: xóa toàn bộ media của dự án (cả `final.mp4`, cache giọng, `review/`) và bản xem thử trên Drive. Giữ `ke_hoach.json`, checkpoint, điểm và mọi file `.json`. Nếu sau đó đổi ý thì chạy `sua`: máy sinh lại giọng nên lâu hơn.
  - Mã video mà mọi nền tảng đã có quyết định (Duyệt/Bỏ, ít nhất một Duyệt), và lần cuối máy cập nhật dòng (`cap_nhat_luc`, thường là lúc đăng) đã quá 30 ngày (`san-xuat.yaml` mục `don_dep.giu_sau_duyet_ngay`): chỉ giữ `renders/final.mp4` và file `.json`.
  - Không đụng mã còn dòng "Chờ duyệt", "Sửa" hoặc ô trống, dự án không có dòng nào trên Hàng chờ, và thư mục kênh gốc (`KENH_GOC_DIR`). File chữ nhỏ (`.html`, `.txt`) được giữ.

**Kho cảnh: quay xong thả file vào, máy tự nạp**

1. Chép video và ảnh vừa quay vào `<thư mục kênh gốc>/canh-quay/moi-quay/`. Được tạo thư mục con theo ngày, giữ nguyên tên file gốc. File nằm yên tại chỗ sau khi nạp, đừng đổi tên hay chuyển đi.
2. Chạy:

   ```powershell
   tools_local\py.cmd -m may_reels kho nap --kenh vanxuan --thu   # xem trước file nào sẽ được nạp
   tools_local\py.cmd -m may_reels kho nap --kenh vanxuan         # nạp thật
   ```

   Với mỗi file chưa có trong `canh-quay/_kho/index.json`, máy:
   - đo thông số (kích thước, hướng dọc/ngang, fps, thời lượng, độ to), tách cảnh và trích khung hình bằng các tool `audio_probe`, `scene_detect`, `frame_sampler`;
   - nếu có tiếng thì chép lời tiếng Việt (PhoWhisper qua tool `transcriber`, chạy bằng Python ở `MAY_REELS_PY_GIONG`);
   - cho agent xem lưới khung hình để ghi nhãn: mô tả, địa điểm, cỡ cảnh, thẻ, đoạn dùng được (từ giây nào đến giây nào), chất lượng, rủi ro (mặt học viên, biển số, tên người, giấy tờ), cách xử lý. Python kiểm nhãn trước khi đưa vào kho; nhãn sai thì ghi lỗi, lần chạy sau tự gắn lại;
   - ghi vào `index.json` và `nhan.json` theo đúng định dạng cũ của kho, rồi chạy `nap_kenh.py` để sinh lại `brand.json`.

   Mỗi file mất vài giây để phân tích, cộng thời gian chép lời (chạy bằng CPU vì GPU thiếu thư viện CUDA) và khoảng 1–2 phút cho agent gắn nhãn.
3. **Quyền hình.**
   - Cảnh **không có mặt người** dùng được ngay.
   - Cảnh **có mặt người** (agent thấy mặt, hoặc ghi rủi ro mặt học viên/người ngoài) chưa được dùng. Máy liệt kê cảnh đó ở tab **Quyền hình** trên Sheet, kèm đường dẫn lưới khung hình `canh-quay/_kho/<mã>/khung.jpg` để bạn xem lại.
   - Khi người trong hình đã đồng ý, chọn `xac_nhan_quyen` = **Đồng ý**. Lần `kho nap` sau, máy chép xác nhận vào `quyen_hinh.bo_sung` của `channel.yaml` (sao lưu `channel.yaml.bak-<giờ>` trước), rồi cảnh mới dùng được. Chọn **Không** thì cảnh không bao giờ được dùng.
4. **Số lần dùng cảnh.** Sau mỗi video vào Hàng chờ (kể cả sau `sua`, `thay-canh`), máy ghi `so_lan_dung` và `ngay_dung_gan_nhat` vào từng cảnh trong `index.json`. Agent sản xuất nhận hai số này và ưu tiên cảnh ít dùng, lâu chưa dùng. Chỉ tính video đã dựng xong; dựng lại hay sửa không làm đếm trùng.
5. **Job chờ quay tự quay về sản xuất.** Một job đang "chờ quay" sẽ tự vào hàng sản xuất ở lần `san-xuat` kế tiếp, không cần `--ca-cho-quay`, khi đủ hai điều kiện:
   - mọi dòng của job ở tab Cần quay là **Đã quay** (hoặc được một dòng gợi ý quay gộp vào, xem bước 6, đánh dấu Đã quay);
   - `kho nap` đã nạp ít nhất một file sau khi yêu cầu được tạo.

   Máy ghi `trang_thai_nap` của các dòng đó. Video đã dựng bằng cảnh tạm (đang chờ duyệt) thì vẫn dùng `thay-canh` như trước.
6. **Máy nói cần quay gì:**

   ```powershell
   tools_local\py.cmd -m may_reels kho thieu --kenh vanxuan --thu             # xem danh sách, không ghi Sheet
   tools_local\py.cmd -m may_reels kho thieu --kenh vanxuan                   # ghi tab Cần quay + bản gửi Zalo
   tools_local\py.cmd -m may_reels kho thieu --kenh vanxuan --ca-chua-duyet   # gợi ý cả cho chủ đề chưa chọn Làm/Bỏ
   ```

   Agent (`skills/may-reels/goi-y-quay.md`) đối chiếu chủ đề đã chọn **Làm**, thư viện định dạng (`khung_nhip` trong `san-xuat.yaml`) và các yêu cầu đang mở với kho, rồi viết danh sách quay **gộp theo buổi**. Mỗi cảnh có mô tả, góc máy, cầm dọc, thời lượng, lời thoại (cảnh nói trước máy), lưu ý ánh sáng và tiếng ồn, lưu ý xin phép người lên hình, và phục vụ những chủ đề nào. Cảnh dùng lại được cho nhiều video được xếp lên trước.
   - Danh sách ghi vào tab Cần quay với mã `vanxuan:goi-y:<mã cảnh>`. Dòng bạn đã chọn Đã quay/Không quay thì không bị ghi đè. Gợi ý cũ không còn trong lần chạy mới thì ghi lý do, không xóa dòng.
   - Bản văn bản gọn để dán Zalo cho người quay: `projects/_may_reels/kho/vanxuan/goi-y-quay-<ngày>.txt`.
   - Chạy `sheet init` một lần nếu tab Cần quay chưa có các cột mới (`buoi`, `loai_canh`, `goc_may`, `thoi_luong`, `loi_thoai`, `luu_y`, `xin_phep`, `gop_yeu_cau`, `uu_tien`) hoặc chưa có tab Quyền hình.

**Đăng bài** (tạm hoãn; làm theo `CAI-DAT-DANG-BAI.md` trước):

```powershell
tools_local\py.cmd -m may_reels dang-nhap drive                     # một lần, mở trình duyệt
tools_local\py.cmd -m may_reels dang-nhap youtube --kenh vanxuan    # một lần, chọn đúng kênh
tools_local\py.cmd -m may_reels hang-cho them --video "<mp4>" --kenh vanxuan --caption-file "<txt>"
tools_local\py.cmd -m may_reels dang                                # CHẠY THỬ: in ra sẽ đăng gì
tools_local\py.cmd -m may_reels dang --that                         # ĐĂNG THẬT các dòng đã chọn Duyệt
```

- `dang` không có `--that` thì không gọi API nền tảng và không ghi tab Hàng chờ.
- TikTok chưa đăng qua API: máy chép video và caption vào thư mục Drive "Chờ đăng TikTok" để bạn đăng tay.
- Mỗi lần chạy, máy ghi một dòng vào tab Nhật ký.

**Chạy kiểm thử** (cần làm sau mỗi lần sửa code):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # một lần, để có pytest
tools_local\py.cmd -m pytest -q                                     # toàn bộ (khoảng 8 phút)
tools_local\py.cmd -m pytest -q tests/may_reels                     # riêng phần Máy Reels
```

---

## 11. Tài liệu tham khảo trong repo

- `README.md` — giới thiệu đầy đủ (tiếng Anh)
- `AGENT_GUIDE.md` — luật làm việc của trợ lý AI
- `PROMPT_GALLERY.md` — câu lệnh mẫu kèm chi phí
- `docs/PROVIDERS.md` — danh sách nhà cung cấp, giá, gói miễn phí
- `docs/ARCHITECTURE.md` — kiến trúc hệ thống
- `backlot/README.md` — bảng theo dõi Backlot
