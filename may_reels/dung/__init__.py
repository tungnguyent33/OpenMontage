"""Dựng video Máy Reels theo cách tất định, từ ke_hoach.json do agent viết.

Agent (skills/may-reels/san-xuat-khong-hoi.md) chỉ viết projects/<ma_video>/ke_hoach.json:
lời đọc, thẻ chữ, nguồn luật, cảnh chọn từ kho, caption. Mọi bước sau là Python:

  ke_hoach.py  kiểm tra kế hoạch, sinh brief/script/scene_plan
  giong_chay.py sinh giọng VieNeu + PhoWhisper nghe lại (chạy bằng Python có vieneu/faster_whisper)
  canh.py      tính đoạn cắt theo mốc giọng thật, cắt cảnh từ kho kênh bằng FFmpeg
  am_thanh.py  chuẩn hóa âm lượng
  hf.py        viết dự án HyperFrames
  kiem_tra.py  final_review và điểm QA
  pipeline.py  chạy các stage của pipeline may-reels, ghi checkpoint, đo thời gian

Không file nào ở đây viết cứng giá trị của một kênh: mọi thứ đọc từ brand/<kenh>/.
"""
