"""Test của Máy Reels dùng "video" giả (vài byte), FFmpeg không nén được: thay bước nén bản xem thử bằng chép file.
Test cần FFmpeg thật thì gọi NEN_XEM_THU_THAT."""
from __future__ import annotations

import shutil

import pytest

from may_reels import hang_cho

NEN_XEM_THU_THAT = hang_cho.nen_xem_thu


@pytest.fixture(autouse=True)
def _nen_xem_thu_bang_chep(monkeypatch):
    monkeypatch.setattr(hang_cho, "nen_xem_thu", lambda src, dst, cfg: shutil.copyfile(src, dst))
