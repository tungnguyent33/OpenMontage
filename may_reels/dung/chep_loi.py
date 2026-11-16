"""Chép lời ÂM THANH CUỐI của bản đã render bằng PhoWhisper (bằng chứng cho chấm điểm và chặn cứng).

Chạy bằng Python có faster_whisper (MAY_REELS_PY_GIONG, giống bước sinh giọng):
    python -m may_reels.dung.chep_loi <video.mp4> <ra.json> [--model kiendt/PhoWhisper-large-ct2]
Ra: {"sha1": <sha1 video>, "model": ..., "van_ban": "...", "doan": [{"start", "end", "text"}]}
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def chep(video: Path, model: str) -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from faster_whisper import WhisperModel
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       check=True)
        wm = WhisperModel(model, device="cpu", compute_type="int8")
        segs, _ = wm.transcribe(str(wav), language="vi", beam_size=5, vad_filter=False)
        doan = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    return {"model": model, "van_ban": " ".join(d["text"] for d in doan), "doan": doan}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("ra")
    ap.add_argument("--model", default="kiendt/PhoWhisper-large-ct2")
    ap.add_argument("--sha1", default="")
    a = ap.parse_args()
    kq = chep(Path(a.video), a.model)
    kq["sha1"] = a.sha1
    Path(a.ra).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(kq["van_ban"][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
