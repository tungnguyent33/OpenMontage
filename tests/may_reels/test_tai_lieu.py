"""Trí nhớ dự án: TRANG-THAI.md là cửa vào, phải khớp code và repo (NGUYEN-TAC.md mục 9, quy tắc kết thúc phiên)."""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DOCS = GOC / "docs" / "may-reels"
TRANG_THAI = DOCS / "TRANG-THAI.md"
MAIN = GOC / "may_reels" / "__main__.py"

# File chỉ có ở máy (bị .gitignore): bản đồ file chỉ ghi tên, test không đòi tồn tại.
CHI_CO_O_MAY = "chỉ có ở máy"


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def lenh_trong_main(nguon: str) -> set[str]:
    """Đọc cây argparse trong __main__.py: trả về các lệnh lá, dạng "nhom lenh" cho lệnh con."""
    nhom: dict[str, str] = {}      # biến subparsers -> tiền tố lệnh
    parser: dict[str, str] = {}    # biến parser -> tên lệnh đầy đủ
    la: set[str] = set()
    for dong in nguon.splitlines():
        m = re.match(r"\s*(\w+)\s*=\s*(\w+)\.add_subparsers\(", dong)
        if m:
            bien, cha = m.groups()
            if cha in parser:  # parser có lệnh con: không còn là lệnh lá
                nhom[bien] = parser[cha]
                la.discard(parser[cha])
            else:
                nhom[bien] = ""
            continue
        m = re.match(r"\s*(\w+)\s*=\s*(\w+)\.add_parser\(\"([^\"]+)\"", dong)
        if m and m.group(2) in nhom:
            bien, cha, ten = m.groups()
            day_du = f"{nhom[cha]} {ten}".strip()
            if ".add_subparsers(" in dong:
                nhom[bien] = day_du
            else:
                parser[bien] = day_du
                la.add(day_du)
    return la


def ban_do_file(noi_dung: str) -> list[tuple[str, str]]:
    """(đường dẫn đầu tiên trong dấu `…` của mỗi dòng gạch đầu dòng, cả dòng) trong mục "Bản đồ file"."""
    m = re.search(r"^## Bản đồ file\n(.*?)(?=^## )", noi_dung, re.S | re.M)
    assert m, "TRANG-THAI.md thiếu mục '## Bản đồ file'"
    kq = []
    for dong in m.group(1).splitlines():
        if not dong.startswith("- "):
            continue
        for duong_dan in re.findall(r"`([^`]+)`", dong.split(":", 1)[0]):
            kq.append((duong_dan, dong))
    return kq


def test_trang_thai_ton_tai_va_ngan():
    assert TRANG_THAI.is_file()
    so_dong = len(_doc(TRANG_THAI).splitlines())
    assert so_dong <= 200, f"TRANG-THAI.md dài {so_dong} dòng (tối đa 200)"


def test_tai_lieu_tri_nho_ton_tai():
    for ten in ("NGUYEN-TAC.md", "QUYET-DINH.md", "NHAT-KY-PHAT-TRIEN.md", "KE-HOACH.md"):
        assert (DOCS / ten).is_file(), ten


def test_doc_lenh_tu_main():
    lenh = lenh_trong_main(_doc(MAIN))
    # vài lệnh chắc chắn có, để bộ đọc không lặng lẽ trả về rỗng
    assert {"sheet init", "kho nap", "chien-luoc kiem-tra", "san-xuat", "dang"} <= lenh
    assert "sheet" not in lenh and "chien-luoc" not in lenh


def test_moi_lenh_trong_main_co_trong_trang_thai():
    noi_dung = _doc(TRANG_THAI)
    thieu = sorted(l for l in lenh_trong_main(_doc(MAIN)) if f"`{l}" not in noi_dung)
    assert not thieu, f"Lệnh chưa ghi trong TRANG-THAI.md: {thieu}"


def test_moi_duong_dan_trong_ban_do_file_ton_tai():
    muc = ban_do_file(_doc(TRANG_THAI))
    assert len(muc) >= 8
    thieu = []
    for duong_dan, dong in muc:
        if CHI_CO_O_MAY in dong or duong_dan.startswith("<KENH_GOC_DIR>"):
            continue
        p = GOC / duong_dan.replace("<kênh>", "vanxuan")
        if not p.exists():
            thieu.append(duong_dan)
    assert not thieu, f"Đường dẫn trong bản đồ file không tồn tại: {thieu}"


def test_file_chi_co_o_may_khong_bi_doi_hoi_ton_tai():
    muc = ban_do_file(_doc(TRANG_THAI))
    rieng = {d for d, dong in muc if CHI_CO_O_MAY in dong}
    assert "docs/may-reels/LO-TRINH.md" in rieng
    assert "docs/may-reels/CHIEN-LUOC-NOI-DUNG.md" in rieng
