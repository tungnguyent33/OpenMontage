"""Phần dùng chung của các publisher Máy Reels (facebook_reels, youtube_shorts, tiktok_handoff).

Phân loại lỗi để may_reels/dang_bai.py quyết định có thử lại hay không:
  mang      lỗi mạng / máy chủ 5xx trước khi bài có thể đã được tạo  -> được thử lại
  gioi_han  nền tảng báo vượt giới hạn (HTTP 429)                     -> để lần chạy sau
  quyen     token/quyền (HTTP 401, 403)                               -> không thử lại
  noi_dung  nền tảng từ chối file hoặc tham số (HTTP 400, 404...)     -> không thử lại
  khong_ro  lỗi xảy ra ở bước cuối, bài CÓ THỂ đã lên                 -> không thử lại, cần người kiểm tra
Phân loại dựa trên mã HTTP, không dựa trên mã lỗi riêng của nền tảng mà tài liệu đã đọc không liệt kê đủ.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MANG, GIOI_HAN, QUYEN, NOI_DUNG, KHONG_RO = "mang", "gioi_han", "quyen", "noi_dung", "khong_ro"


class LoiDang(Exception):
    def __init__(self, loai: str, thong_bao: str) -> None:
        super().__init__(thong_bao)
        self.loai = loai


def loai_theo_http(ma: int | None) -> str:
    if ma is None:
        return MANG
    if ma == 429:
        return GIOI_HAN
    if ma in (401, 403):
        return QUYEN
    if ma >= 500:
        return MANG
    return NOI_DUNG


def bay_gio_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def publish_log(entry: dict[str, Any]) -> dict[str, Any]:
    """Bọc một entry thành publish_log và kiểm tra theo schemas/artifacts/publish_log.schema.json."""
    from schemas.artifacts import validate_artifact
    log = {"version": "1.0", "entries": [entry]}
    validate_artifact("publish_log", log)
    return log
