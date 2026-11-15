"""Phần chữ của may_reels/giong.py (không cần VieNeu/Whisper)."""
import pytest

from may_reels.giong import am_tiet, chuan_hoa_doc, do_khop, doc_so


@pytest.mark.parametrize("n,doc", [
    (0, "không"), (1, "một"), (10, "mười"), (11, "mười một"), (15, "mười lăm"), (21, "hai mươi mốt"),
    (24, "hai mươi tư"), (50, "năm mươi"), (100, "một trăm"), (105, "một trăm linh năm"),
    (125, "một trăm hai mươi lăm"), (150, "một trăm năm mươi"), (175, "một trăm bảy mươi lăm"),
    (279, "hai trăm bảy mươi chín"), (1005, "một nghìn không trăm linh năm"),
    (2025, "hai nghìn không trăm hai mươi lăm"), (2000, "hai nghìn"), (1000000, "một triệu"),
])
def test_doc_so(n, doc):
    assert doc_so(n) == doc


def test_chuan_hoa_doc():
    s = chuan_hoa_doc("Bằng A1 cấp từ 2025 chỉ lái xe đến 125 phân khối, xe điện đến 11 kW.")
    assert s == ("Bằng A một cấp từ hai nghìn không trăm hai mươi lăm chỉ lái xe đến một trăm hai mươi lăm "
                 "phân khối, xe điện đến mười một ki lô oát.")


def test_am_tiet_va_do_khop():
    can = am_tiet("Có bằng A một, lái xe?")
    assert can == ["có", "bằng", "a", "một", "lái", "xe"]
    assert do_khop(can, can) == 1.0
    assert do_khop(can, ["có", "băng", "a", "một", "lái", "xe"]) < 1.0


def test_do_khop_bo_duoi_whisper_bia_va_biet_danh():
    can = am_tiet("Nhắn Za lô, để nhận bộ câu ôn thi A một.")
    nghe = am_tiet("nhắn salo để nhận bộ câu ôn thi a một bộ một")
    assert do_khop(can, nghe) == 1.0
    assert do_khop(can, am_tiet("nhắn salo để nhận bộ cơ ô ti a một")) < 0.95


def test_chuan_hoa_doc_cta_dien_thoai():
    from may_reels.giong import co_dien_thoai, so_am_hien_thi
    cta = "Nhắn Zalo 0823 279 999 để nhận bộ câu ôn thi A1."
    assert chuan_hoa_doc(cta) == ("Nhắn Za lô không tám hai ba, hai bảy chín, chín chín chín để nhận bộ câu ôn thi "
                                  "A một.")
    assert co_dien_thoai(cta) and not co_dien_thoai("Từ năm 2025 đến 125 phân khối")
    assert sum(so_am_hien_thi(t, dien_thoai=True) for t in cta.split()) == 20


def test_duoi_thua_phan_biet_chu_bia_va_doc_lap():
    from may_reels.giong import DUOI_THUA_TOI_DA, duoi_thua_giay
    tu = [{"w": "a", "s": 0.0, "e": 0.3}, {"w": "một", "s": 0.3, "e": 0.6}]
    bia = tu + [{"w": "nắn", "s": 4.26, "e": 4.28}, {"w": "ba", "s": 4.38, "e": 4.38}]   # đo thật ở vx-thu-may s8
    lap = tu + [{"w": "nhắn", "s": 0.8, "e": 1.0}, {"w": "zalo", "s": 1.0, "e": 1.5}]
    assert duoi_thua_giay(tu, 2) == 0.0
    assert duoi_thua_giay(bia, 2) <= DUOI_THUA_TOI_DA < duoi_thua_giay(lap, 2)
