"""Dữ liệu chiến lược nội dung (may_reels/chien_luoc.py, prompt C0). Test dùng BẢN MẪU *.mau.yaml và các file được
commit (dinh-dang.yaml, lich.yaml), vì file thật (doi-tuong, dinh-vi, ban-hang) chỉ có trên máy người dùng."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from may_reels import chien_luoc as CL

REPO = Path(__file__).resolve().parents[2]
BRAND = REPO / "brand" / "vanxuan"


def _goc(tmp_path: Path, *, kho: list | None = None) -> Path:
    """Repo giả: kênh kenhthu, file riêng tạo từ bản mẫu, file chung chép nguyên, san-xuat.yaml và brand.json tối thiểu."""
    goc = tmp_path / "repo"
    b = goc / "brand" / "kenhthu"
    b.mkdir(parents=True)
    shutil.copytree(REPO / "schemas" / "may-reels", goc / "schemas" / "may-reels")
    for ten in CL.FILE_RIENG:
        shutil.copyfile(BRAND / f"{ten}.mau.yaml", b / f"{ten}.mau.yaml")
        shutil.copyfile(BRAND / f"{ten}.mau.yaml", b / f"{ten}.yaml")
    for ten in CL.FILE_CHUNG:
        shutil.copyfile(BRAND / f"{ten}.yaml", b / f"{ten}.yaml")
    shutil.copyfile(BRAND / "san-xuat.yaml", b / "san-xuat.yaml")
    (b / "brand.json").write_text(json.dumps({"kho_canh": kho or []}, ensure_ascii=False), encoding="utf-8")
    return goc


def _sua(goc: Path, ten: str, ham) -> None:
    p = goc / "brand" / "kenhthu" / f"{ten}.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    ham(d)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("ten,file", [(t, f"{t}.mau.yaml") for t in CL.FILE_RIENG] +
                                    [(t, f"{t}.yaml") for t in CL.FILE_CHUNG])
def test_file_trong_repo_dung_schema(ten, file):
    d = CL._chuoi_hoa_ngay(yaml.safe_load((BRAND / file).read_text(encoding="utf-8")))
    assert CL.loi_schema(ten, d) == []


def test_ban_mau_dung_cau_truc_va_kiem_tra_khong_loi(tmp_path):
    bc = CL.kiem_tra("kenhthu", _goc(tmp_path), hom_nay=dt.date(2026, 11, 20))
    assert not bc.loi, (bc.thieu_file, bc.loi_schema, bc.loi_tham_chieu)
    assert "ban-hang" in bc.muc_trong and bc.gia_thuyet
    assert set(bc.chua_du_so_lieu) == set(CL.CAN_SO_LIEU)   # bản mẫu chưa có số liệu đã xác nhận
    assert bc.mua.startswith("Trước Tết") and "NGOÀI" not in bc.mua


def test_thieu_file_rieng_bao_tao_tu_ban_mau(tmp_path):
    goc = _goc(tmp_path)
    (goc / "brand/kenhthu/ban-hang.yaml").unlink()
    bc = CL.kiem_tra("kenhthu", goc)
    assert bc.loi and any("ban-hang.mau.yaml" in x for x in bc.thieu_file)
    with pytest.raises(CL.LoiThieuFile, match="mau.yaml"):
        CL.doc("kenhthu", "ban-hang", goc)


def test_tham_chieu_sai(tmp_path):
    goc = _goc(tmp_path)
    _sua(goc, "dinh-dang", lambda d: d["dinh_dang"][0].update(nhom_chinh=["n9"]))
    _sua(goc, "dinh-dang", lambda d: d["dinh_dang"][-1].update(khung_nhip="khong-co"))
    _sua(goc, "lich", lambda d: d["tuan"][0].update(dinh_dang=["khong-co-dinh-dang"]))
    bc = CL.kiem_tra("kenhthu", goc)
    t = "\n".join(bc.loi_tham_chieu)
    assert "n9" in t and "khong-co" in t and "khong-co-dinh-dang" in t


def test_sai_schema_thi_dung_lai(tmp_path):
    goc = _goc(tmp_path)
    _sua(goc, "dinh-dang", lambda d: d["dinh_dang"][0].update(tang="ban_hang"))
    bc = CL.kiem_tra("kenhthu", goc)
    assert bc.loi_schema and not bc.thieu_canh


def test_uu_dai_het_han_va_so_lieu_da_xac_nhan(tmp_path):
    goc = _goc(tmp_path)

    def ban_hang(d):
        d["uu_dai"] = [{"noi_dung": "Giảm 10%", "het_han": "2026-11-01", "trang_thai": "da_xac_nhan"},
                       {"noi_dung": "Tặng bộ đề", "het_han": "2027-01-01", "trang_thai": "da_xac_nhan"}]
        d["giay_to"] = {"danh_sach": ["Căn cước"], "trang_thai": "da_xac_nhan", "ngay_cap_nhat": "2026-11-20"}
    _sua(goc, "ban-hang", ban_hang)
    bc = CL.kiem_tra("kenhthu", goc, hom_nay=dt.date(2026, 11, 20))
    assert bc.uu_dai_het_han == ["Giảm 10% (hết hạn 2026-11-01)"]
    assert bc.chua_du_so_lieu["dang-ky-mang-gi"] == ["quy_trinh_dang_ky"]   # giấy tờ đã có, quy trình chưa


def test_dinh_dang_thieu_canh_khop_the_va_loai(tmp_path):
    kho = [{"ma": "a", "dung_duoc": True, "loai": "BROLL", "the": ["san-tap"]},
           {"ma": "b", "dung_duoc": False, "loai": "NOI", "the": ["noi-truoc-may"]},   # không dùng được: không tính
           {"ma": "c", "dung_duoc": True, "loai": "ANH", "the": ["nhan-bang"]}]
    bc = CL.kiem_tra("kenhthu", _goc(tmp_path, kho=kho))
    assert bc.thieu_canh["di-xe-chua-co-bang"] == ["Thầy nói trước máy"]          # sân tập có, thầy nói thì không
    assert "ngay-thi-nhan-bang" in bc.thieu_canh and "Cảnh nhận bằng" not in bc.thieu_canh["ngay-thi-nhan-bang"]
    assert "thi-thu-3-cau" not in bc.thieu_canh                                    # máy tự dựng


def test_file_rieng_bi_gitignore_ban_mau_thi_khong():
    def bo_qua(p: str) -> bool:
        return subprocess.run(["git", "check-ignore", "-q", p], cwd=REPO).returncode == 0
    for ten in CL.FILE_RIENG:
        assert bo_qua(f"brand/vanxuan/{ten}.yaml"), ten
        assert not bo_qua(f"brand/vanxuan/{ten}.mau.yaml"), ten
    for ten in CL.FILE_CHUNG:
        assert not bo_qua(f"brand/vanxuan/{ten}.yaml"), ten
    assert bo_qua("docs/may-reels/CHIEN-LUOC-NOI-DUNG.md")


def test_file_commit_khong_duong_dan_tuyet_doi_khong_so_dien_thoai():
    files = [BRAND / f"{t}.mau.yaml" for t in CL.FILE_RIENG] + [BRAND / f"{t}.yaml" for t in CL.FILE_CHUNG]
    for f in files:
        s = f.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:[\\/]|/Users/|/home/", s), f
        assert not re.search(r"\b0\d{2,3}[ .]?\d{3}[ .]?\d{3,4}\b", s), f     # số điện thoại


def test_mua_theo_su_kien_khong_tinh_la_o_trong(tmp_path):
    """lich.yaml (2026-11-21): mùa "quy định mới" tính theo sự kiện, không có ngày cố định -> không báo ô trống."""
    bc = CL.kiem_tra("kenhthu", _goc(tmp_path))
    assert "lich" not in bc.muc_trong
    goc = _goc(tmp_path / "b")
    _sua(goc, "lich", lambda d: [m.pop("theo_su_kien", None) for m in d["mua"]])
    assert any("quy-dinh-moi" in x for x in CL.kiem_tra("kenhthu", goc).muc_trong["lich"])
