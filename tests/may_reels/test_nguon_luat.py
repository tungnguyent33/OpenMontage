"""Máy đề xuất nguồn luật, người xác nhận, máy áp dụng vào chu-de.md; san-xuat từ chối chủ đề thiếu nguồn. Agent giả."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from may_reels import sheet as S
from may_reels.cot_sheet import NHAT_KY, Y_TUONG
from may_reels.nguon_luat import (ap_dung, du_muc_khoan, khong_can_nguon, kiem_de_xuat, sua_dong_chu_de,
                                  tra_nguon)
from may_reels.san_xuat import LY_DO_THIEU_NGUON, MA_OK, san_xuat
from tests.may_reels.sheet_gia import BangGia
from tests.may_reels.test_san_xuat import BRAND, agent_gia, dung_gia, nha_may  # noqa: F401


# ---------------------------------------------------------------- mức chi tiết
@pytest.mark.parametrize("nguon,du", [
    ("Luật 36/2024/QH15, Điều 22, khoản 2", True),
    ("Luật 36/2024/QH15, Điều 22, khoản 2, 3", True),
    ("Luật 36/2024/QH15 Điều 57 khoản 1 điểm a", True),
    ("Luật 36/2024/QH15 Điều 57 khoản 1 điểm a và Điều 89", False),   # Điều 89 chưa có khoản
    ("Luật 36/2024/QH15 Điều 9", False),
    ("Luật 36/2024/QH15 (điều về người lái xe mô tô, xe gắn máy)", False),
    ("Luật 36/2024/QH15 Điều 11; QCVN 41:2024", False),
    ("QCVN 41:2024 (phụ lục biển báo cấm)", False),
    ("QCVN 41:2024 (phần vạch kẻ đường)", False),
    ("QCVN 41:2024/BGTVT, Phụ lục C, biển P.102", True),
    ("QCVN 41:2024/BGTVT, vạch 1.1", True),
    ("TT 12/2025/TT-BCA Phụ lục II mục A", True),
    ("Luật 36/2024/QH15 (điều về tuổi người lái xe); context/business.md", False),
    ("Luật 36/2024/QH15, Điều 59, khoản 1, điểm a; context/business.md", True),
    ("Thông tư về sát hạch GPLX hiện hành", False),
    ("Không cần nguồn luật", True),
    ("", False),
])
def test_du_muc_khoan(nguon, du):
    assert du_muc_khoan(nguon) is du


def test_khong_can_nguon_khong_phan_biet_hoa_thuong():
    assert khong_can_nguon("Không cần nguồn luật") and khong_can_nguon("không cần nguồn luật (hậu trường)")


# ---------------------------------------------------------------- kiểm tra kết quả agent
TOT = {"nguon_de_xuat": "Luật 36/2024/QH15, Điều 22, khoản 2", "trich_nguyen_van": "Tại nơi giao nhau không có báo hiệu …",
       "link_nguon": "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=1", "ngay_tra": "2026-11-16"}


def test_kiem_de_xuat_hop_le():
    dx = kiem_de_xuat("a", TOT, "2026-11-16")
    assert dx.nguon_de_xuat == TOT["nguon_de_xuat"] and dx.link_nguon == TOT["link_nguon"] and dx.ghi_chu == []


@pytest.mark.parametrize("sua,tim", [
    ({"nguon_de_xuat": "Luật 36/2024/QH15, Điều 22"}, "chưa tới mức khoản"),
    ({"trich_nguyen_van": ""}, "thiếu trích"),
    ({"trich_nguyen_van": " ".join(["chữ"] * 90)}, "quá dài"),
    ({"link_nguon": ""}, "thiếu link"),
])
def test_kiem_de_xuat_bo_khi_khong_dat(sua, tim):
    dx = kiem_de_xuat("a", {**TOT, **sua}, "2026-11-16")
    assert dx.nguon_de_xuat == "" and any(tim in x for x in dx.ghi_chu)


def test_kiem_de_xuat_khong_tim_duoc_mau_thuan_va_link_khong_chinh_thuc():
    dx = kiem_de_xuat("a", {"nguon_de_xuat": "", "ly_do_khong_tim_duoc": "Luật không quy định khung giờ còi"}, "d")
    assert dx.nguon_de_xuat == "" and "khung giờ còi" in dx.ghi_chu[0]
    dx = kiem_de_xuat("a", {**TOT, "mau_thuan_y_chinh": "Luật cấm hẳn, không có khung giờ",
                            "link_nguon": "https://thuvienphapluat.vn/x"}, "d")
    assert dx.nguon_de_xuat and any("MÂU THUẪN" in x for x in dx.ghi_chu)
    assert any("không thuộc cổng chính thức" in x for x in dx.ghi_chu)


# ---------------------------------------------------------------- lệnh nguon-luat
@pytest.fixture()
def kenh_thu(tmp_path):
    goc = tmp_path / "repo"
    (goc / "brand/kt").mkdir(parents=True)
    b = copy.deepcopy(BRAND)
    b["chu_de"] = [
        {"ma": "thieu", "chu_de": "Có được X?", "y_chinh": "Không", "nguon_doi_chieu": "Luật 1/2024 (điều về X)"},
        {"ma": "du", "chu_de": "Y?", "y_chinh": "Có", "nguon_doi_chieu": "Luật 1/2024, Điều 2, khoản 1"},
        {"ma": "da-lam", "chu_de": "Z?", "y_chinh": "Có", "nguon_doi_chieu": "Luật 1/2024 Điều 3", "da_lam": True},
        {"ma": "hau-truong", "chu_de": "H", "y_chinh": "-", "nguon_doi_chieu": "Không cần nguồn luật"},
        {"ma": "sai-roi", "chu_de": "S?", "y_chinh": "Có", "nguon_doi_chieu": "Luật 1/2024 Điều 4"},
        {"ma": "khong-thay", "chu_de": "K?", "y_chinh": "Có", "nguon_doi_chieu": "Luật 1/2024"},
    ]
    (goc / "brand/kt/brand.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    bang = BangGia()
    S.khoi_tao(bang)
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": c["ma"], "chu_de": c["chu_de"],
                                     "nguon_doi_chieu": c["nguon_doi_chieu"]} for c in b["chu_de"]])
    return goc, bang, b


def dat_nguoi(bang, ma, cot, gia_tri):
    t = bang.tab("Ý tưởng")
    h = t.doc_tat_ca()
    r = next(i for i, x in enumerate(h, start=1) if i > 1 and x[h[0].index("ma")] == ma)
    t.dat(r, h[0].index(cot) + 1, gia_tri)


def agent_tra(goi: list):
    def ham(prompt, *, du_an, goc, ma):
        yc = json.loads((du_an / f"{ma}.yeu_cau.json").read_text(encoding="utf-8"))
        goi.append(yc)
        kq = {**TOT, "nguon_de_xuat": "Luật 1/2024, Điều 7, khoản 2"} if ma == "thieu" else \
            {"nguon_de_xuat": "", "ly_do_khong_tim_duoc": "Không thấy điều nào quy định"}
        (du_an / f"{ma}.json").write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 30000, "total_cost_usd": 0.42}
    return ham


def test_tra_nguon_chi_chu_de_can_va_ghi_sheet(kenh_thu):
    goc, bang, _ = kenh_thu
    dat_nguoi(bang, "sai-roi", "xac_nhan_nguon", "Sai")  # người đã xét: không tra đè
    goi = []
    ds = tra_nguon(bang, "kt", goc=goc, agent=agent_tra(goi), log=lambda s: None)
    assert [d.ma for d in ds] == ["thieu", "khong-thay"]
    assert goi[0]["y_chinh"] == "Không" and goi[0]["chu_de"] == "Có được X?"
    rows = {d["ma"]: d for d in S.doc_dong(bang, Y_TUONG)}
    a = rows["thieu"]
    assert a["nguon_de_xuat"] == "Luật 1/2024, Điều 7, khoản 2" and a["link_nguon"].startswith("https://vbpl.vn")
    assert a["trich_nguyen_van"] and a["ngay_tra"] == "2026-11-16" and a["xac_nhan_nguon"] == ""
    assert rows["khong-thay"]["nguon_de_xuat"] == "" and "Không thấy điều nào" in rows["khong-thay"]["ghi_chu_may"]
    assert rows["thieu"]["nguon_doi_chieu"] == "Luật 1/2024 (điều về X)"  # chưa áp dụng khi người chưa xác nhận
    nk = [d for d in S.doc_dong(bang, NHAT_KY) if d["buoc"] == "nguon_luat"]
    assert len(nk) == 2 and "0.42 USD" in nk[0]["chi_tiet"]


def test_tra_nguon_che_do_thu_khong_goi_agent(kenh_thu):
    goc, bang, _ = kenh_thu
    ds = tra_nguon(bang, "kt", goc=goc, thu=True, agent=lambda *a, **k: pytest.fail("không được gọi"),
                   log=lambda s: None)
    assert {d.ma for d in ds} == {"thieu", "sai-roi", "khong-thay"}


# ---------------------------------------------------------------- nguon-luat ap-dung
CHU_DE_MD = ("# Kho chủ đề\r\n\r\n| Mã | Trụ cột | Định dạng | Chủ đề (câu hỏi) | Ý chính cần kiểm | Nguồn cần đối chiếu | Trend |\r\n"
             "|---|---|---|---|---|---|---|\r\n"
             "| thieu | T | hoi-dap | Có được X? | Không | Luật 1/2024 (điều về X) | |\r\n"
             "| sai-roi | T | hoi-dap | S? | Có | Luật 1/2024 Điều 4 | 3 |\r\n")


def test_ap_dung_chi_dong_dung_sao_luu_va_nap_lai(kenh_thu, tmp_path):
    goc, bang, b = kenh_thu
    tm = tmp_path / "kenh-goc"
    tm.mkdir()
    (tm / "chu-de.md").write_bytes(CHU_DE_MD.encode("utf-8"))
    tra_nguon(bang, "kt", goc=goc, agent=agent_tra([]), log=lambda s: None)
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": "sai-roi", "nguon_de_xuat": "Luật 1/2024, Điều 4, khoản 9"}])
    dat_nguoi(bang, "thieu", "xac_nhan_nguon", "Đúng")
    dat_nguoi(bang, "sai-roi", "xac_nhan_nguon", "Sai")
    nap = []

    def nap_gia(kenh, g):  # giả nap_kenh.py: brand.json lấy nguồn mới từ chu-de.md
        nap.append(kenh)
        b2 = copy.deepcopy(b)
        next(c for c in b2["chu_de"] if c["ma"] == "thieu")["nguon_doi_chieu"] = "Luật 1/2024, Điều 7, khoản 2"
        (g / "brand/kt/brand.json").write_text(json.dumps(b2, ensure_ascii=False), encoding="utf-8")
    ra = []
    kq = ap_dung(bang, "kt", goc=goc, thu_muc_kenh=tm, nap=nap_gia, log=ra.append)
    moi = (tm / "chu-de.md").read_bytes().decode("utf-8")
    assert moi == CHU_DE_MD.replace("| Luật 1/2024 (điều về X) |", "| Luật 1/2024, Điều 7, khoản 2 |")
    assert kq["sao_luu"].read_bytes().decode("utf-8") == CHU_DE_MD and nap == ["kt"]
    assert kq["sai"] == ["sai-roi"] and any("SAI" in x and "y_chinh" in x for x in ra)
    rows = {d["ma"]: d for d in S.doc_dong(bang, Y_TUONG)}
    assert rows["thieu"]["nguon_doi_chieu"] == "Luật 1/2024, Điều 7, khoản 2"   # sheet nap-chu-de đã chạy
    assert rows["sai-roi"]["nguon_doi_chieu"] == "Luật 1/2024 Điều 4"
    assert "Đã áp dụng" in rows["thieu"]["ghi_chu_may"]
    # chạy lại: nguồn đã bằng đề xuất -> không làm gì, không sao lưu thêm
    kq2 = ap_dung(bang, "kt", goc=goc, thu_muc_kenh=tm, nap=nap_gia, log=lambda s: None)
    assert kq2["ap_dung"] == [] and len(list(tm.glob("chu-de.md.bak-*"))) == 1


def test_ap_dung_che_do_thu_khong_ghi(kenh_thu, tmp_path):
    goc, bang, _ = kenh_thu
    tm = tmp_path / "kenh-goc"
    tm.mkdir()
    (tm / "chu-de.md").write_bytes(CHU_DE_MD.encode("utf-8"))
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": "thieu", "nguon_de_xuat": "Luật 1/2024, Điều 7, khoản 2"}])
    dat_nguoi(bang, "thieu", "xac_nhan_nguon", "Đúng")
    kq = ap_dung(bang, "kt", goc=goc, thu_muc_kenh=tm, thu=True, nap=lambda *a: pytest.fail("không nạp"),
                 log=lambda s: None)
    assert kq["ap_dung"] and (tm / "chu-de.md").read_bytes().decode("utf-8") == CHU_DE_MD
    assert not list(tm.glob("chu-de.md.bak-*"))


def test_sua_dong_chu_de_tu_choi_ky_tu_bang_va_ma_trung():
    with pytest.raises(ValueError):
        sua_dong_chu_de(CHU_DE_MD, "thieu", "a | b")
    with pytest.raises(ValueError):
        sua_dong_chu_de(CHU_DE_MD + "| thieu | x | x | x | x | x | |\r\n", "thieu", "Luật 1, Điều 1, khoản 1")


# ---------------------------------------------------------------- san-xuat từ chối chủ đề thiếu nguồn
def test_san_xuat_tu_choi_chu_de_chua_toi_muc_khoan(nha_may):  # noqa: F811
    goc, bang = nha_may
    b = json.loads((goc / "brand/kenhthu/brand.json").read_text(encoding="utf-8"))
    b["chu_de"][0]["nguon_doi_chieu"] = "Luật Thử 1/2024 (điều về ngã tư)"
    (goc / "brand/kenhthu/brand.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), log=lambda s: None,
                  dung=dung_gia({"kt-005-cd-b": [(MA_OK, {"diem_qa": 90})]}))
    assert [k.ma_video for k in ds] == ["kt-005-cd-b"]  # cd-a bị từ chối, không chiếm chỗ
    rows = {d["ma"]: d for d in S.doc_dong(bang, Y_TUONG)}
    assert rows["cd-a"]["ghi_chu_may"] == LY_DO_THIEU_NGUON and rows["cd-a"]["trang_thai_san_xuat"] == "ý tưởng"
    assert not (goc / "projects/kt-005-cd-a").exists()


def test_san_xuat_khong_can_nguon_luat_thi_khong_chan(nha_may):  # noqa: F811
    goc, bang = nha_may
    b = json.loads((goc / "brand/kenhthu/brand.json").read_text(encoding="utf-8"))
    b["chu_de"][0]["nguon_doi_chieu"] = "Không cần nguồn luật"
    (goc / "brand/kenhthu/brand.json").write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_gia([]), log=lambda s: None,
                  dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})]}))
    assert [k.ma_video for k in ds] == ["kt-005-cd-a"]


def test_ap_dung_chu_de_may_sua_dung_file_cua_may(kenh_thu, tmp_path):
    goc, bang, b = kenh_thu
    b2 = copy.deepcopy(b)
    b2["chu_de"].append({"ma": "may-moi", "chu_de": "M?", "y_chinh": "Có", "nguon_doi_chieu": "Luật 1/2024",
                         "tep": "chu-de-may.md"})
    (goc / "brand/kt/brand.json").write_text(json.dumps(b2, ensure_ascii=False), encoding="utf-8")
    tm = tmp_path / "kenh-goc"
    tm.mkdir()
    (tm / "chu-de.md").write_bytes(CHU_DE_MD.encode("utf-8"))
    may = CHU_DE_MD.replace("| thieu | T | hoi-dap | Có được X? | Không | Luật 1/2024 (điều về X) | |\r\n", "").replace(
        "| sai-roi | T | hoi-dap | S? | Có | Luật 1/2024 Điều 4 | 3 |", "| may-moi | T | luat | M? | Có | Luật 1/2024 | |")
    (tm / "chu-de-may.md").write_bytes(may.encode("utf-8"))
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": "may-moi", "nguon_de_xuat": "Luật 1/2024, Điều 2, khoản 3"}])
    dat_nguoi(bang, "may-moi", "xac_nhan_nguon", "Đúng")
    kq = ap_dung(bang, "kt", goc=goc, thu_muc_kenh=tm, nap=lambda k, g: None, log=lambda s: None)
    assert [m for m, *_ in kq["ap_dung"]] == ["may-moi"]
    assert (tm / "chu-de.md").read_bytes().decode("utf-8") == CHU_DE_MD          # file của người không đổi
    assert "| may-moi | T | luat | M? | Có | Luật 1/2024, Điều 2, khoản 3 |" in (tm / "chu-de-may.md").read_text(encoding="utf-8")
    assert [x.name.split(".bak-")[0] for x in kq["sao_luu_tat_ca"]] == ["chu-de-may.md"]
