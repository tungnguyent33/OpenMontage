"""Chuẩn hóa âm lượng bằng FFmpeg loudnorm hai lượt (đo rồi chỉnh tuyến tính) và đo lại bằng ebur128."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def do(p: Path) -> dict:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tom = r.stderr[r.stderr.rindex("Summary:"):]
    return {"lufs": float(re.search(r"I:\s+(-?[\d.]+) LUFS", tom).group(1)),
            "true_peak_dbfs": float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tom).group(1))}


def _bo_loc(src: Path, lufs: float, dinh: float) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
                        f"loudnorm=I={lufs}:TP={dinh}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return (f"loudnorm=I={lufs}:TP={dinh}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


def chuan_hoa_wav(src: Path, dst: Path, lufs: float = -14.0, dinh: float = -1.0) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", _bo_loc(src, lufs, dinh), "-ar", "48000",
                    "-ac", "1", str(dst)], check=True)
    return do(dst)


def tuy_chon_render(sx: dict) -> list[str]:
    """Tham số nén cho `hyperframes render`, từ san-xuat.yaml mục xuat. Nén một lần ở đây; chuan_hoa_mp4 giữ hình."""
    x = sx.get("xuat") or {}
    return ["--crf", str(int(x.get("crf", 20))), "--max-bitrate", str(x.get("max_bitrate", "12M")),
            "--buffer-size", str(x.get("buffer_size", "24M"))]


def chuan_hoa_mp4(src: Path, dst: Path, lufs: float = -14.0, dinh: float = -1.0) -> dict:
    """Giữ nguyên hình (copy), chỉ chuẩn hóa tiếng. HyperFrames trộn lại tiếng và làm to hơn đầu vào."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-c:v", "copy", "-af", _bo_loc(src, lufs, dinh),
                    "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)], check=True)
    return do(dst)
