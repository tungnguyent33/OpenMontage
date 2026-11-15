"""Đọc brand/<kenh>/dang-bai.yaml: tên biến môi trường và ID Page/kênh, KHÔNG chứa khóa.

File này được commit lên repo public, nên mọi giá trị trông giống token bị từ chối.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from may_reels.cot_sheet import NEN_TANG

GOC = Path(__file__).resolve().parent.parent
TEN_BIEN = re.compile(r"^[A-Z][A-Z0-9_]*$")
MA_KENH = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Mặc định lấy từ docs/may-reels/API-DANG-BAI.md (đọc ngày 2026-11-15).
GIOI_HAN_24H_MAC_DINH = {"fb_reels": 30, "yt_shorts": 100, "tiktok": 15}
# Phạm vi đếm giới hạn: "kenh" = đếm riêng từng kênh; "chung" = đếm chung mọi kênh (quota YouTube tính theo project).
PHAM_VI_GIOI_HAN = {"fb_reels": "kenh", "yt_shorts": "chung", "tiktok": "kenh"}


class LoiCauHinh(ValueError):
    pass


@dataclass
class CauHinhDang:
    kenh: str
    nen_tang: list[str]
    fb_reels: dict = field(default_factory=dict)
    yt_shorts: dict = field(default_factory=dict)
    tiktok: dict = field(default_factory=dict)
    gioi_han_24h: dict = field(default_factory=dict)

    def cua(self, nen_tang: str) -> dict:
        return getattr(self, nen_tang)

    def thieu(self, nen_tang: str) -> list[str]:
        """Những mục cấu hình còn thiếu để đăng thật lên nền tảng này (rỗng = đủ)."""
        c = self.cua(nen_tang)
        out = []
        if nen_tang == "fb_reels":
            if not str(c.get("page_id") or "").strip():
                out.append("fb_reels.page_id")
            out += self._thieu_bien(c, "bien_token", "fb_reels")
        elif nen_tang == "yt_shorts":
            if not str(c.get("kenh_id") or "").strip():
                out.append("yt_shorts.kenh_id")
            out += self._thieu_bien(c, "bien_token_file", "yt_shorts")
        elif nen_tang == "tiktok":
            if (c.get("che_do") or "tay") != "tay":
                out.append("tiktok.che_do: chỉ hỗ trợ 'tay' (xem API-DANG-BAI.md mục 3)")
            for b in ("MAY_REELS_GOOGLE_CLIENT_SECRET",):
                if not os.environ.get(b, "").strip():
                    out.append(f"biến môi trường {b}")
        return out

    @staticmethod
    def _thieu_bien(c: dict, khoa: str, nt: str) -> list[str]:
        ten = c.get(khoa)
        if not ten:
            return [f"{nt}.{khoa}"]
        if not os.environ.get(ten, "").strip():
            return [f"biến môi trường {ten} (khai trong {nt}.{khoa})"]
        return []

    def gioi_han(self, nen_tang: str) -> int:
        return int(self.gioi_han_24h.get(nen_tang, GIOI_HAN_24H_MAC_DINH[nen_tang]))


def _kiem_khong_co_bi_mat(d, duong: str = "") -> None:
    if isinstance(d, dict):
        for k, v in d.items():
            p = f"{duong}.{k}" if duong else str(k)
            if str(k).startswith("bien_"):
                if v and not TEN_BIEN.fullmatch(str(v)):
                    raise LoiCauHinh(f"{p} phải là TÊN biến môi trường (chữ hoa, số, _), không phải giá trị khóa")
            _kiem_khong_co_bi_mat(v, p)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            _kiem_khong_co_bi_mat(v, f"{duong}[{i}]")
    elif isinstance(d, str) and (len(d) > 60 or d.startswith(("EAA", "ya29.", "1//"))):
        raise LoiCauHinh(f"{duong}: giá trị trông giống token/khóa. dang-bai.yaml chỉ được chứa tên biến và ID")


def doc_cau_hinh_dang(kenh: str, goc: Path | None = None) -> CauHinhDang:
    goc = goc or GOC
    if not MA_KENH.fullmatch(kenh or ""):
        raise LoiCauHinh(f"Mã kênh không hợp lệ: {kenh!r}")
    p = goc / "brand" / kenh / "dang-bai.yaml"
    if not p.is_file():
        raise LoiCauHinh(f"Chưa có brand/{kenh}/dang-bai.yaml (xem docs/may-reels/CAI-DAT-DANG-BAI.md)")
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    _kiem_khong_co_bi_mat(d)
    nt = list(d.get("nen_tang") or NEN_TANG)
    sai = [x for x in nt if x not in NEN_TANG]
    if sai:
        raise LoiCauHinh(f"dang-bai.yaml: nền tảng không hỗ trợ {sai}")
    return CauHinhDang(kenh=kenh, nen_tang=nt, fb_reels=d.get("fb_reels") or {},
                       yt_shorts=d.get("yt_shorts") or {}, tiktok=d.get("tiktok") or {},
                       gioi_han_24h=d.get("gioi_han_24h") or {})
