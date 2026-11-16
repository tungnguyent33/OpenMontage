# Máy Reels: chấm điểm video đã render

Skill cho agent chạy không tương tác (`claude -p`), do `may_reels/cham_diem.py` gọi sau khi video đã dựng xong (lệnh `san-xuat`, `sua`, `thay-canh`, `cham-lai`). Skill áp dụng cho **mọi kênh**. Trọng số, ngưỡng và mô tả từng tiêu chí đọc từ `brand/<kenh>/rubric.yaml`, không đọc từ skill này.

## Nguyên tắc: chấm trên VIDEO, không chấm trên kịch bản

Kịch bản (`ke_hoach.json`) chỉ cho biết agent viết kế hoạch **định** làm gì. Bạn chấm cái **người xem thật sự thấy và nghe**. Khi kịch bản và bằng chứng của video khác nhau, tin bằng chứng.

Bằng chứng của video (máy đã chuẩn bị sẵn trong `projects/<ma_video>/`):

| File | Là gì |
|---|---|
| `review/bang_chung.json` | Tóm tắt: lời chép từ âm thanh cuối, chữ trên màn hình, số đo của máy, chủ đề, các tiêu chí bạn phải chấm |
| `review/hook-0.0s.png`, `hook-0.5s.png`, `hook-1.5s.png`, `hook-3.0s.png` | Khung hình 3 giây đầu |
| `review/khung-*.png` | 6 khung trải đều video |
| `review/luoi.png` | Lưới khung, mỗi ô cách nhau 4 giây |
| `review/chep_loi.json` | Lời PhoWhisper nghe được từ âm thanh **cuối** (không phải lời trong kịch bản) |
| `ke_hoach.json` | Kế hoạch: chỉ dùng để biết ý định, nguồn luật đã trích, CTA đã chọn |
| `brand/<kenh>/brand.json` | `chu_de` (câu hỏi, `y_chinh`, `nguon_doi_chieu`), `cta`, `lien_he`, `mau` |

Mở các ảnh bằng Read. Phải xem **cả bốn** khung hook và lưới khung trước khi chấm.

## Việc của agent: chỉ ghi MỘT file

Ghi `projects/<ma_video>/renders/score.json` như sau, chỉ gồm các tiêu chí có `nguon: agent` (danh sách nằm trong `bang_chung.json` → `tieu_chi_agent`):

```json
{"tieu_chi": {
  "hook": {"diem": 14, "ly_do": "Mở bằng câu hỏi có chữ to từ 0,1s; khung đầu là cảnh sân tập có chuyển động."},
  "dung_gia_tri": {"diem": 12, "ly_do": "..."},
  "phu_de": {"diem": 9, "ly_do": "..."},
  "cta": {"diem": 10, "ly_do": "..."}
}}
```

- `diem`: số từ 0 đến `toi_da` của tiêu chí. `ly_do`: **một câu**, nêu bằng chứng cụ thể (giây nào, khung nào, câu nào).
- Không chấm các tiêu chí `nguon: may` (nhịp, chân thực, thương hiệu, kỹ thuật): máy tự đo và sẽ ghi đè.
- Không tính tổng. Máy tự cộng, áp trần và ghi lại file theo `schemas/may-reels/score.schema.json`.

## Cách chấm từng tiêu chí của agent

- **hook**:
  - Câu mở đầu nghe được có câu hỏi, mâu thuẫn hoặc con số không?
  - Có chữ trên màn hình trong 0,5 giây đầu không? Xem `hook-0.5s.png` và `do_dac.moc_chu_dau`.
  - Khung `hook-0.0s.png` có phải logo, màn hình trống hay màu trơn không?

  Thiếu một ý thì trừ khoảng một phần ba. Khung đầu là logo hoặc màn hình trống thì cho tối đa một phần năm.
- **dung_gia_tri**:
  - Lời nghe được có trả lời đúng **câu hỏi của chủ đề** (`chu_de.chu_de`) không?
  - Có khớp `y_chinh` và nguồn luật không?
  - Người xem có học được một điều cụ thể, làm theo được không?

  Sai luật, hoặc trả lời lạc đề, thì tối đa 3.
- **phu_de**: chữ đúng dấu tiếng Việt (so `chep_loi` và khung hình), không quá 2 dòng, không bị cắt, không che thẻ chữ, đọc được trên nền. Máy đã đo số dòng, vùng an toàn và tương phản (`do_dac.phu_de`), nên bạn chấm phần mắt mới thấy được.
- **cta**: chỉ **một** lời kêu gọi, nói rõ người xem cần làm gì (nhắn số nào, bình luận gì, lưu video). Xem `do_dac.cta`.

## Chống chấm dễ dãi

- Điểm tối đa chỉ dành cho tiêu chí không có lỗi nào bạn chỉ ra được. Nếu `ly_do` có chữ "nhưng", "hơi", "chưa" thì điểm không được là tối đa.
- Không được nâng điểm vì kịch bản hay. Chỉ chấm cái có trong video.
- Máy vẫn áp trần lên điểm của bạn khi đo được lỗi cứng: chữ xuất hiện muộn, 3 giây đầu đứng yên, phụ đề quá 2 dòng, CTA không nguyên văn. Đừng chấm bù cho các lỗi đó.

## Kết thúc

Ghi `renders/score.json` xong thì dừng. Trả lời một dòng, ví dụ: "Đã chấm 4 tiêu chí: hook 14/20, đúng 12/15, phụ đề 9/10, CTA 10/10."
