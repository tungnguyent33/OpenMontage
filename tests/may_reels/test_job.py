"""Máy trạng thái của job."""
from __future__ import annotations

import jsonschema
import pytest

from may_reels.job import CHUYEN_HOP_LE, KET_THUC, TRANG_THAI, LoiChuyenTrangThai, chuyen_trang_thai, tao_job

LUC = "2026-11-15T10:00:00+07:00"


def job_moi(**kw):
    d = dict(ma_video="kt-005", kenh="kenhthu", ma_chu_de="a", chu_de="A?", dinh_dang="hoi-dap",
             nen_tang_dich=["fb_reels", "yt_shorts", "tiktok"], project_dir="projects/kt-005", luc=LUC)
    d.update(kw)
    return tao_job(**d)


def test_duong_di_binh_thuong():
    j = job_moi()
    for den in ["dang_san_xuat", "cho_duyet", "da_duyet", "da_dang"]:
        j = chuyen_trang_thai(j, den, luc=LUC)
    assert j["trang_thai"] == "da_dang"
    assert [b["den"] for b in j["lich_su"]] == ["y_tuong", "dang_san_xuat", "cho_duyet", "da_duyet", "da_dang"]


def test_nhanh_cho_quay_va_sua():
    j = chuyen_trang_thai(job_moi(), "dang_san_xuat")
    j = chuyen_trang_thai(j, "cho_quay", ly_do="thiếu cảnh vòng xuyến")
    j = chuyen_trang_thai(j, "dang_san_xuat")
    j = chuyen_trang_thai(j, "cho_duyet")
    j = chuyen_trang_thai(j, "dang_san_xuat", ly_do="Sửa: đổi hook")
    assert j["trang_thai"] == "dang_san_xuat"


@pytest.mark.parametrize("tu,den", [
    ("y_tuong", "cho_duyet"), ("y_tuong", "da_dang"), ("dang_san_xuat", "da_duyet"),
    ("dang_san_xuat", "da_dang"), ("cho_quay", "cho_duyet"), ("cho_duyet", "da_dang"),
    ("da_duyet", "dang_san_xuat"), ("da_dang", "bo"), ("bo", "y_tuong"),
])
def test_tu_choi_buoc_nhay_khong_hop_le(tu, den):
    j = job_moi()
    j["trang_thai"] = tu
    with pytest.raises(LoiChuyenTrangThai):
        chuyen_trang_thai(j, den)


def test_bang_chuyen_day_du_va_trang_thai_ket_thuc():
    assert set(CHUYEN_HOP_LE) == set(TRANG_THAI)
    for tt in KET_THUC:
        assert CHUYEN_HOP_LE[tt] == frozenset()
    for tt, dich in CHUYEN_HOP_LE.items():
        assert dich <= set(TRANG_THAI)
        if tt not in KET_THUC:
            assert "bo" in dich


def test_khong_sua_job_cu():
    j = job_moi()
    j2 = chuyen_trang_thai(j, "dang_san_xuat")
    assert j["trang_thai"] == "y_tuong" and len(j["lich_su"]) == 1 and len(j2["lich_su"]) == 2


def test_loi_phai_kem_thong_bao_va_xoa_khi_thoat():
    j = chuyen_trang_thai(job_moi(), "dang_san_xuat")
    with pytest.raises(LoiChuyenTrangThai):
        chuyen_trang_thai(j, "loi")
    j = chuyen_trang_thai(j, "loi", loi="HyperFrames render lỗi")
    assert j["loi"] == "HyperFrames render lỗi"
    j = chuyen_trang_thai(j, "dang_san_xuat")
    assert j["loi"] is None


def test_trang_thai_khong_ton_tai():
    with pytest.raises(LoiChuyenTrangThai):
        chuyen_trang_thai(job_moi(), "xuat_ban")


@pytest.mark.parametrize("sai", [
    {"project_dir": "C:/Users/x/projects/kt-005"},
    {"project_dir": "../projects/kt-005"},
    {"nen_tang_dich": []},
    {"nen_tang_dich": ["facebook"]},
    {"nen_tang_dich": ["tiktok", "tiktok"]},
    {"kenh": "Kênh Thử"},
])
def test_schema_tu_choi_job_sai(sai):
    with pytest.raises(jsonschema.ValidationError):
        job_moi(**sai)
