# Máy Reels: bộ biên kịch (viết lời)

Skill cho agent viết kế hoạch (`claude -p`). Được gọi từ `skills/may-reels/san-xuat-khong-hoi.md`, bước 1, khi chạy lệnh `san-xuat` hoặc `sua`. Skill áp dụng cho **mọi kênh**; mọi giá trị riêng đọc từ `brand/<kenh>/`.

Skill này lo phần **lời**: lời đọc, thẻ chữ, câu hook, câu chốt, CTA. Phần chọn cảnh, caption và nguồn luật vẫn theo `san-xuat-khong-hoi.md`.

**Mục tiêu:** kịch bản đạt mức người viết nội dung chuyên nghiệp. Sau khi bạn ghi `ke_hoach.json`, một **biên tập độc lập** (`skills/may-reels/bien-tap.md`) chấm kịch bản trên chữ, trước khi máy sinh giọng và dựng. Biên tập chỉ thấy kịch bản, chủ đề, nhóm đối tượng và rubric; **không thấy lập luận của bạn**. Vì vậy chữ phải tự đứng được.

## Đọc trước khi viết

| File | Lấy gì |
|---|---|
| `projects/<ma_video>/yeu_cau.json` | `chu_de`, `dinh_dang` (định dạng của chủ đề), `khung_nhip`, `cau_hoi_khach`, `phan_hoi` |
| `brand/<kenh>/doi-tuong.yaml` (chưa có thì `doi-tuong.mau.yaml`) | Nhóm đối tượng: `noi_lo`, `khoanh_khac_mua`, `bang_chung_thuyet_phuc` |
| `brand/<kenh>/dinh-dang.yaml` | Định dạng: `tang`, `nhom_chinh`, `giong` (`may` / `thay`), `nhip` hoặc `khung_nhip`, `dieu_kien` |
| `brand/<kenh>/hook.yaml` | Công thức hook (`cong_thuc[].ma`) và danh sách `hook_sao` |
| `brand/<kenh>/giong-noi.yaml` | Xưng hô, độ dài câu, từ nên dùng, `tu_tranh`, cách nói số và điều luật |
| `brand/<kenh>/giu-chan.yaml` | Kỹ thuật giữ người xem |
| `brand/<kenh>/rubric-kich-ban.yaml` | Biên tập chấm theo gì; giới hạn máy kiểm (`kiem_tra_may`) |
| `brand/<kenh>/kich-ban-mau/*.yaml` | Kịch bản mẫu. **Chỉ dùng mẫu có `trang_thai: da_duyet` làm ví dụ.** Mẫu `cho_duyet` là bản nháp chưa được người duyệt: không đọc, không bắt chước |
| `brand/<kenh>/brand.json` | `cam` (cụm từ cấm, câu sáo), `cta`, `kenh.khan_gia`; `context` → `ban_local` (giọng văn, chân dung khách) nếu có trên máy |
| `brand/<kenh>/san-xuat.yaml` | `khung_nhip`, `am_tiet_moi_giay`, `khung_hinh.thoi_luong_giay` |
| `brand/<kenh>/ban-hang.yaml` (nếu có) | Chỉ những mục `trang_thai: da_xac_nhan`. Học phí, số buổi, ngày, ưu đãi chưa xác nhận thì **không nói** |

## Quy trình viết (một lần chạy, ghi vào `ke_hoach.json` → `kich_ban`)

### 1. Người, nỗi lo, định dạng

- `nhom_doi_tuong`: một mã nhóm trong `doi-tuong.yaml`. Lấy theo `yeu_cau.json` → `dinh_dang.nhom_chinh` (chọn nhóm hợp nhất với chủ đề). Định dạng không có nhóm chính thì chọn nhóm có nỗi lo khớp chủ đề nhất; thật sự cho mọi người thì ghi `moi_nhom`.
- `noi_lo`: nỗi lo mà video gỡ, **bằng chữ của khách**. Thứ tự ưu tiên:
  1. Câu trong `yeu_cau.json` → `cau_hoi_khach` (`nguon_noi_lo: cau_hoi_khach`).
  2. Mục `noi_lo` của nhóm trong `doi-tuong.yaml` (`nguon_noi_lo: doi_tuong`).
  3. Câu hỏi của chủ đề (`nguon_noi_lo: chu_de`).
- `dinh_dang`: mã trong `dinh-dang.yaml` (`yeu_cau.json` → `dinh_dang.ma`).

### 2. Ba góc kể

`goc_ke`: 3 cách kể khác nhau cho cùng chủ đề, mỗi góc **một câu**. Ví dụ với chủ đề vòng xuyến: kể theo tình huống đi đường; kể theo lỗi thi sa hình; kể theo câu đố trái hay phải. Chọn 1 (`goc_chon`: 1, 2 hoặc 3) và ghi `ly_do_goc` (vì sao góc này hợp nhóm và nỗi lo nhất).

### 3. Năm hook theo năm công thức

Viết đúng 5 hook theo **5 công thức khác nhau** trong `hook.yaml` (`cong_thuc` là `ma` của công thức). Mỗi hook đi theo thứ tự: nhóm đối tượng → nỗi lo → định dạng → **rồi mới** viết câu. Mỗi hook ghi đủ ba phần:

| Phần | Khóa | Việc |
|---|---|---|
| Hình 0–3 giây | `hinh_0_3s` | Cái người xem thấy: giữ ngón tay lại. Phải có trong kho cảnh hoặc dựng được bằng sơ đồ / thẻ chữ |
| Câu nói đầu | `cau_noi` | Mở vòng. Đọc xong trong 3 giây: tối đa `rubric-kich-ban.yaml` → `kiem_tra_may.hook_am_tiet_toi_da` âm tiết, tính sau khi đổi số sang chữ |
| Chữ trên màn hình | `chu_man_hinh` | Dạng `"DÒNG 1 / dòng 2"`. Neo ý cho người xem tắt tiếng |

**Ba phần bổ sung cho nhau, không lặp cùng một câu.** Chữ trên màn hình không chép lại câu nói. Hình không chỉ minh họa đúng câu nói. Máy đo độ giống nhau giữa ba phần và trừ điểm khi chúng lặp.

Chọn 1 hook làm `hook_chon` và ghi `ly_do_hook`. Giữ 4 hook còn lại trong `phuong_an_hook` để sau này thử. Hook đã chọn phải khớp kế hoạch:
- `hook_chon.cau_noi` **trùng nguyên văn** `doan[0].loi`.
- `hook_chon.chu_man_hinh` **là** thẻ chữ của `s1`, viết dạng `"<dong1> / <dong2>"`.
- `hook_chon.hinh_0_3s` khớp cảnh đã chọn cho `s1`.

Không dùng hook sáo (`hook.yaml` → `hook_sao`), câu sáo (`brand.json` → `cam`), hay công thức `loi-thu-nhan` cho giọng máy.

### 4. Bản 1, đọc to, bản 2

1. Viết bản 1 theo khung nhịp, ghi vào `ban_1` (`[{"id": "s1", "loi": "..."}, ...]`).
2. Đọc to bản 1 trong đầu, từng câu, theo nhịp của giọng đọc. Tìm:
   - chỗ hụt hơi;
   - câu ghép hai ý;
   - từ văn viết, từ Hán Việt nặng (`giong-noi.yaml` → `tu_tranh`);
   - chỗ chuyển đoạn bị hẫng;
   - câu chốt khó nhắc lại.
3. Sửa thành bản 2. Bản 2 chính là `doan[].loi`. Ghi từng thay đổi vào `sua_ban_2`, mỗi thay đổi một dòng, ví dụ: `"s3: tách câu trích luật thành 2 câu"`.

## Quy tắc lời (bắt buộc)

1. **Nhịp cố định** theo `san-xuat.yaml` → `khung_nhip[<khóa>]`:
   - thứ tự `hook` → các đoạn `than` → `chot` → `cta`; id đoạn là `s1`, `s2`, …;
   - hook đọc xong trong 3 giây;
   - tổng thời lượng trong `khung_hinh.thoi_luong_giay`.

   Định dạng có `nhip` riêng trong `dinh-dang.yaml` thì theo mô tả từng vai trong đó; khóa `khung_nhip` của kế hoạch vẫn là khóa trong `san-xuat.yaml`.
2. **Lời đọc chính là phụ đề.** Đúng chính tả. Số viết bằng chữ số (2025, 125), máy tự đổi sang cách đọc. Chỉ dùng `doc_rieng` khi máy chắc chắn sẽ đọc sai.
3. **Mỗi câu một ý.** Câu dài nhất không quá `kiem_tra_may.cau_am_tiet_toi_da` âm tiết. Câu trích luật dài thì tách: câu 1 nêu điều khoản, câu 2 nói lại cho dễ hiểu (`giong-noi.yaml` → `do_dai_cau`).
4. **Giọng theo định dạng** (`dinh-dang.yaml` → `giong`, chi tiết ở `giong-noi.yaml` → `xung_ho`):
   - `may`: người dẫn trung tính gọi người xem là "bạn", **không** xưng "thầy" hay "mình";
   - `thay`: lời thầy nói, xưng "thầy".
5. **Giữ người xem** (`giu-chan.yaml`):
   - hook mở một câu hỏi, đoạn chốt trả lời đúng câu đó;
   - đoạn `s2` đi tiếp ngay ý hook;
   - mỗi đoạn một ý;
   - câu nối giữa các đoạn ("Tức là…", "Còn nếu…");
   - câu chốt ngắn, có nhịp.
6. **Không văn AI.** Không viết các kiểu câu trong `rubric-kich-ban.yaml` → `kiem_tra_may.mau_van_ai`:
   - "không phải X mà là Y";
   - "không chỉ… mà còn…";
   - tự hỏi tự đáp ("Kết quả? …");
   - hai chấm tiết lộ ("Mấu chốt là: …");
   - liệt kê ba vế "không…, không…, không…";
   - câu mở sáo ("Hãy tưởng tượng…");
   - gạch dài "—".

   Gặp các kiểu này thì quay về sự thật (điều luật, việc cần làm, tên lỗi) và viết lại từ đó. Không chỉ thay từ đồng nghĩa.
7. **Cụ thể.** Việc làm được ngay, tên lỗi, mốc ngày, con số có nguồn. Không có số thì nói định tính ("hay gặp"); **không** bịa phần trăm.
8. **Cụm từ cấm:** không dùng cụm nào trong `brand.json` → `cam.cum_tu_cam` và `cam.cum_tu_cam_du_an`, ở lời, thẻ chữ, caption. Không dùng câu sáo đã chốt (`cam.cau_sao_da_chot`). Tránh cả `cam.cau_sao_cho_duyet`. Không hứa kết quả thi. Không tạo gấp gáp giả.
9. **Số liệu bán hàng:** chỉ nói số, giá, ngày, ưu đãi có trong `ban-hang.yaml` ở trạng thái `da_xac_nhan`. Thiếu thì bỏ ý đó khỏi video. Ô `[chờ anh xác nhận]` chỉ dùng trong kịch bản mẫu, **không bao giờ** trong lời của video thật.
10. **CTA:** đoạn `cta` là **nguyên văn** một câu trong `brand.json` → `cta`.
    - Chọn câu hợp nhất với điều vừa học và với nhóm đối tượng. Ví dụ: video thi thử thì nhận bộ câu ôn; video "A hay B" thì bình luận để thầy chấm.
    - Đoạn này có `canh = null` và `the = null`.
11. **Thẻ chữ** (`the`):
    - `dong1` tối đa 22 ký tự, viết hoa; `dong2` tối đa 34 ký tự;
    - `mau` là `cam` (nhấn mạnh) hoặc `xanh` (thông tin); `kieu` là `hook`, `wipe`, `word` hoặc `scale`;
    - thẻ neo ý chính của đoạn, **không** chép lại cả câu lời đọc;
    - dòng nguồn trên thẻ do máy tự ghép (`san-xuat-khong-hoi.md`).

## Tự kiểm trước khi ghi

Máy sẽ kiểm lại các mục sau. Trượt mục chặn thì biên tập không chấm, điểm kịch bản bằng 0.
- [ ] Đủ 3 góc kể và 5 hook theo 5 công thức khác nhau, mã có trong `hook.yaml` *(chặn)*
- [ ] `hook_chon.cau_noi` trùng `s1`; `hook_chon.chu_man_hinh` trùng thẻ `s1` *(chặn)*
- [ ] Không cụm từ cấm, không câu sáo đã chốt *(chặn)*
- [ ] Hook trong giới hạn âm tiết; không câu nào quá dài *(trần điểm)*
- [ ] Ba phần hook không lặp nhau; không hook sáo, không văn AI, ít từ tránh *(trần điểm)*

## Vòng sửa kịch bản

`yeu_cau.json` → `phan_hoi` bắt đầu bằng "Điểm kịch bản" nghĩa là biên tập trả về.
- Sửa lời và thẻ chữ theo đúng các mục được nêu, nặng nhất trước.
- Giữ cảnh, nguồn và caption, trừ khi lời đổi buộc chúng phải đổi theo.
- Biên tập chê hook thì có thể đổi `hook_chon` sang một hook trong `phuong_an_hook`, nhưng vẫn giữ đủ 5 hook với 5 công thức.
- Cập nhật `ban_1` / `sua_ban_2` cho đúng lần sửa này.

Chỉ vòng sửa ở bước biên tập mới có tối đa `rubric-kich-ban.yaml` → `so_vong_sua` vòng. Hết số vòng đó, video vẫn được dựng và kèm cảnh báo "Kịch bản dưới ngưỡng".
