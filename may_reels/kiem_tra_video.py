"""Kiểm tra file video và caption trước khi đưa vào Hàng chờ và trước khi đăng.

Giới hạn lấy từ docs/may-reels/API-DANG-BAI.md (tài liệu chính thức, đọc ngày 2026-11-15).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

TI_LE_9_16 = 9 / 16
SAI_SO_TI_LE = 0.01

# (thời lượng tối thiểu, tối đa) giây; (fps tối thiểu, tối đa); cạnh ngắn tối thiểu; cạnh dài tối đa. None = tài liệu không ghi.
GIOI_HAN = {
    "fb_reels": {"giay": (3, 90), "fps": (24, 60), "canh_ngan_min": 540, "canh_dai_max": None},
    "yt_shorts": {"giay": (None, 180), "fps": (None, None), "canh_ngan_min": None, "canh_dai_max": None},
    "tiktok": {"giay": (None, 600), "fps": (23, 60), "canh_ngan_min": 360, "canh_dai_max": 4096},
}


@dataclass
class ThongSo:
    rong: int
    cao: int
    giay: float
    fps: float


def do_thong_so(video: Path) -> ThongSo:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("Không thấy ffprobe (cài FFmpeg)")
    kq = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,avg_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, encoding="utf-8")
    if kq.returncode != 0:
        raise RuntimeError(f"ffprobe lỗi: {kq.stderr.strip()[:300]}")
    d = json.loads(kq.stdout)
    s = (d.get("streams") or [{}])[0]
    fps_raw = s.get("avg_frame_rate") or "0/1"
    fps = float(Fraction(fps_raw)) if fps_raw != "0/0" else 0.0
    return ThongSo(int(s.get("width") or 0), int(s.get("height") or 0),
                   float((d.get("format") or {}).get("duration") or 0), fps)


def loi_thong_so(ts: ThongSo, nen_tang: str) -> list[str]:
    g = GIOI_HAN[nen_tang]
    loi = []
    if not ts.rong or not ts.cao:
        return ["không đọc được kích thước khung hình"]
    if abs(ts.rong / ts.cao - TI_LE_9_16) > SAI_SO_TI_LE:
        loi.append(f"tỉ lệ {ts.rong}x{ts.cao} không phải 9:16")
    lo, hi = g["giay"]
    if lo is not None and ts.giay < lo:
        loi.append(f"dài {ts.giay:.1f}s, ngắn hơn {lo}s")
    if hi is not None and ts.giay > hi:
        loi.append(f"dài {ts.giay:.1f}s, quá {hi}s")
    lo, hi = g["fps"]
    if lo is not None and ts.fps < lo - 0.01:
        loi.append(f"{ts.fps:.2f} fps, dưới {lo}")
    if hi is not None and ts.fps > hi + 0.01:
        loi.append(f"{ts.fps:.2f} fps, quá {hi}")
    ngan, dai = min(ts.rong, ts.cao), max(ts.rong, ts.cao)
    if g["canh_ngan_min"] and ngan < g["canh_ngan_min"]:
        loi.append(f"cạnh ngắn {ngan}px, dưới {g['canh_ngan_min']}px")
    if g["canh_dai_max"] and dai > g["canh_dai_max"]:
        loi.append(f"cạnh dài {dai}px, quá {g['canh_dai_max']}px")
    return [f"{nen_tang}: {x}" for x in loi]


def cum_tu_cam(brand: dict) -> list[str]:
    cam = brand.get("cam") or {}
    return [c for c in (cam.get("cum_tu_cam") or []) + (cam.get("cum_tu_cam_du_an") or []) if c and c.strip()]


def _chuan(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").casefold()


def tim_cum_tu_cam(van_ban: str, cam: list[str]) -> list[str]:
    t = _chuan(van_ban)
    return [c for c in cam if _chuan(c).strip() and _chuan(c).strip() in t]
