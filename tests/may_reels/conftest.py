"""Test của Máy Reels không gọi FFmpeg nén, PhoWhisper hay claude -p trừ khi test tự yêu cầu.

- Bản xem thử: "video" giả (vài byte) không nén được -> chép file. Test cần FFmpeg thật gọi NEN_XEM_THU_THAT.
- Vùng an toàn khi chấm thật: hyperframes check thay bằng báo cáo rỗng.
- Chấm điểm (san_xuat / sua / cham-lai): thay bằng cham_gia, lấy điểm từ tóm tắt bước dựng (tom["diem_qa"]) để các
  test luồng cũ giữ nguyên kịch bản điểm. Test chấm thật dùng may_reels.cham_diem.cham_video với agent/chép lời giả.
- Biên tập kịch bản (san_xuat): thay bằng bien_tap_gia (luôn đạt). Test biên tập thật ở test_bien_tap.py.
"""
from __future__ import annotations

import shutil

import pytest

from may_reels import hang_cho
from may_reels.cham_diem import KetQuaCham

NEN_XEM_THU_THAT = hang_cho.nen_xem_thu


def cham_gia(ma_video, *, goc, log=None, tom=None):
    d = (tom or {}).get("diem_qa", 90)
    kc = KetQuaCham(ma_video, diem_qa=d, diem_ky_thuat=100)
    if d is not None and d < 100:
        kc.ly_do_tru = [f"Hook 0-3 giây -{100 - d}: câu mở đầu không có câu hỏi"]
    kc.chan = list((tom or {}).get("chan") or [])
    return kc


def bien_tap_gia(P, *, goc, log=None):
    """Biên tập kịch bản giả: luôn đạt (test biên tập thật ở test_bien_tap.py, agent giả)."""
    from may_reels.bien_tap import KetQuaBienTap
    return KetQuaBienTap(P.name, diem=88, nguong=75, cong_thuc_hook="goi-dung-nguoi")


@pytest.fixture(autouse=True)
def _khong_goi_ngoai(monkeypatch):
    monkeypatch.setattr("may_reels.san_xuat.bien_tap_mac_dinh", bien_tap_gia)
    monkeypatch.setattr(hang_cho, "nen_xem_thu", lambda src, dst, cfg: shutil.copyfile(src, dst))
    monkeypatch.setattr("may_reels.san_xuat.cham_mac_dinh", cham_gia)
    monkeypatch.setattr("may_reels.sua.cham_mac_dinh", cham_gia)
    # Vùng an toàn: không chạy hyperframes check (Chrome, mạng) trong test; test riêng tự truyền kiem_vung.
    monkeypatch.setattr("may_reels.cham_diem.kiem_vung_mac_dinh", lambda hf, phien_ban: ({"layout": {"findings": []}}, ""))
