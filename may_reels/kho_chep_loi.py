"""Chép lời tiếng Việt của một cảnh quay mới nạp kho, bằng tool `transcriber` (tools/analysis/transcriber.py).

Chạy bằng Python có faster_whisper (MAY_REELS_PY_GIONG, giống bước sinh giọng), vì .venv không cài thư viện này:
    python -m may_reels.kho_chep_loi <file> <ra.json> [--model kiendt/PhoWhisper-large-ct2]

`--model` nhận tên cỡ của transcriber (base, large-v3...) hoặc mã/thư mục model CTranslate2; đổi mặc định bằng
MAY_REELS_MODEL_CHEP_LOI. Mặc định là PhoWhisper vì máy đã dùng nó để nghe lại giọng đọc, đã có sẵn trong cache và
chạy offline. Phép so sánh trên 2 clip thật CHƯA chạy xong (docs/may-reels/KE-HOACH.md mục 10).
Ra: {"model", "device", "ngon_ngu", "doan": [{"start", "end", "text"}], "so_tu", "giay_co_loi", "van_ban"}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

MODEL_MAC_DINH = "kiendt/PhoWhisper-large-ct2"


def chep(file: Path, model: str) -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from tools.analysis.transcriber import Transcriber
    with tempfile.TemporaryDirectory() as tmp:
        kq = Transcriber().execute({"input_path": str(file), "model_size": model, "language": "vi", "output_dir": tmp})
    if not kq.success:
        raise RuntimeError(f"transcriber lỗi: {kq.error}")
    doan = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in kq.data["segments"] if s["text"].strip()]
    van_ban = " ".join(d["text"] for d in doan)
    return {"model": model, "device": kq.data.get("device"), "ngon_ngu": kq.data.get("language"), "doan": doan,
            "so_tu": len(van_ban.split()), "giay_co_loi": round(sum(d["end"] - d["start"] for d in doan), 2),
            "van_ban": van_ban}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("ra")
    ap.add_argument("--model", default=os.environ.get("MAY_REELS_MODEL_CHEP_LOI") or MODEL_MAC_DINH)
    a = ap.parse_args()
    kq = chep(Path(a.file), a.model)
    Path(a.ra).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{kq['so_tu']} từ, {kq['giay_co_loi']} giây có lời ({kq['model']}, {kq['device']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
