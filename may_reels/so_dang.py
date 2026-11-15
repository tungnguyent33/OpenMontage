"""Sổ đăng local (projects/_may_reels/so_dang.jsonl, bị gitignore theo projects/).

Ghi NGAY sau khi nền tảng báo thành công, trước khi ghi Sheet: nếu ghi Sheet lỗi thì
lần chạy sau vẫn biết video đã lên và không đăng lại. Cũng dùng để đếm giới hạn 24 giờ.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
THU_MUC = GOC / "projects" / "_may_reels"


class SoDang:
    def __init__(self, duong_dan: Path | None = None) -> None:
        self.p = duong_dan or THU_MUC / "so_dang.jsonl"

    def doc(self) -> list[dict]:
        if not self.p.is_file():
            return []
        out = []
        for dong in self.p.read_text(encoding="utf-8").splitlines():
            dong = dong.strip()
            if dong:
                out.append(json.loads(dong))
        return out

    def ghi(self, muc: dict) -> None:
        self.p.parent.mkdir(parents=True, exist_ok=True)
        with open(self.p, "a", encoding="utf-8") as f:
            f.write(json.dumps(muc, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def da_xu_ly(self, ma_video: str, nen_tang: str) -> dict | None:
        for m in self.doc():
            if m.get("ma_video") == ma_video and m.get("nen_tang") == nen_tang:
                return m
        return None

    def dem_24h(self, nen_tang: str, kenh: str | None, bay_gio: datetime) -> int:
        moc = bay_gio - timedelta(hours=24)
        n = 0
        for m in self.doc():
            if m.get("nen_tang") != nen_tang or (kenh is not None and m.get("kenh") != kenh):
                continue
            try:
                luc = datetime.fromisoformat(m["luc"])
            except (KeyError, ValueError):
                continue
            if luc >= moc:
                n += 1
        return n
