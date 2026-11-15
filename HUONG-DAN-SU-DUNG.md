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
└── assets/               logo, fonts
```

Hiện có: **`brand/vanxuan/`** — Đào tạo lái xe Vạn Xuân (màu navy `#0E3970`, xanh `#048DD1`, cam `#E4661F`; font Be Vietnam Pro). Chi tiết xem `brand/README.md`.

**Đổi quy tắc riêng của kênh** (vd. thêm cụm từ cấm): sửa `brand/vanxuan/quy-tac-rieng.yaml` rồi chạy lại lệnh nạp bên dưới.

**Cập nhật lại khi dữ liệu kênh thay đổi** (thư mục kênh gốc chỉ được đọc, không bị sửa):

```powershell
python tools_local/nap_kenh.py "C:\Users\Thinkpad P15V3\Desktop\Claude code\video-agent-team-kit\video-agent-team\channels\vanxuan"
```

**Thêm kênh mới:** chạy lệnh trên với thư mục của kênh đó. Kênh mới được tạo ở `brand/<mã-kênh>/`, không ảnh hưởng gì đến Vạn Xuân. Nếu kênh có quy tắc riêng, tạo `brand/<mã-kênh>/quy-tac-rieng.yaml` theo mẫu của Vạn Xuân trước khi nạp. Khi yêu cầu video, nói rõ `cho kênh <mã-kênh>`.

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

## 10. Tài liệu tham khảo trong repo

- `README.md` — giới thiệu đầy đủ (tiếng Anh)
- `AGENT_GUIDE.md` — luật làm việc của trợ lý AI
- `PROMPT_GALLERY.md` — câu lệnh mẫu kèm chi phí
- `docs/PROVIDERS.md` — danh sách nhà cung cấp, giá, gói miễn phí
- `docs/ARCHITECTURE.md` — kiến trúc hệ thống
- `backlot/README.md` — bảng theo dõi Backlot
