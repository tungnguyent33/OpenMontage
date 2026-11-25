"""Lệnh y-tuong (C1): lịch tuần, điều kiện định dạng, dữ kiện đã xác nhận, kiểm kết quả agent, ghi Sheet. Agent giả."""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

import pytest
import yaml

from may_reels import sheet as S
from may_reels import y_tuong as Y
from may_reels.cot_sheet import CAU_HOI_KHACH, NHAT_KY, Y_TUONG
from tests.may_reels.sheet_gia import BangGia

HOM_NAY = dt.date(2026, 11, 25)       # thứ Tư; tuần tới = 2026-W49 (30/11 .. 6/12)
TUAN = "2026-W49"

LICH = {"phien_ban": 1, "tuan": [
    {"thu": 2, "tang": "keo_xem", "dinh_dang": ["luat-hoi"]},
    {"thu": 3, "tang": "chuyen_doi", "dinh_dang": ["chua-bang", "so-truot"]},
    {"thu": 4, "tang": "niem_tin", "dinh_dang": ["buoi-hoc"]},
    {"thu": 5, "tang": "chuyen_doi", "dinh_dang": ["hoc-phi-gom-gi"]},
    {"thu": 6, "tang": "keo_xem", "dinh_dang": ["tra-loi-binh-luan", "luat-hoi"]},
    {"thu": 7, "tang": "niem_tin", "dinh_dang": ["buoi-hoc"]},
    {"thu": 8, "tang": "chuyen_doi", "dinh_dang": ["lich-khai-giang"]},
], "mua": [{"ma": "tet", "ten": "Trước Tết", "tu_ngay": "2026-11-17", "den_ngay": "2027-02-05", "nhom": ["n1", "n5"],
            "goc": "về quê", "dieu_kien_duoc_noi": ['Chỉ nói "có bằng trước Tết" nếu lịch học và lịch thi kịp']}],
    "mua_dang_chay": "tet"}


def _dd(ma, tang, **k):
    return {"ma": ma, "ten": ma, "tang": tang, "nhom_chinh": [], "hook_mau": "", "giong": "may", "canh_can": [],
            "dieu_kien": "", "trang_thai": "gia_thuyet", **k}


DINH_DANG = {"phien_ban": 1, "dinh_dang": [
    _dd("luat-hoi", "keo_xem", khung_nhip="hoi"), _dd("chua-bang", "chuyen_doi", nhom_chinh=["n1"]),
    _dd("so-truot", "chuyen_doi", nhom_chinh=["n4", "n1"]), _dd("buoi-hoc", "niem_tin"),
    _dd("hoc-phi-gom-gi", "chuyen_doi"), _dd("lich-khai-giang", "chuyen_doi"),
    _dd("tra-loi-binh-luan", "keo_xem", theo_cau_hoi=True)]}

DOI_TUONG = {"phien_ban": 1, "nhom": [
    {"ma": f"n{i}", "uu_tien": i, "ten": f"Nhóm {i}", "ai_quyet_dinh": "chính họ",
     "noi_lo": [f"Lo {i}a", f"Lo {i}b"], "khoanh_khac_mua": [], "bang_chung_thuyet_phuc": [], "trang_thai": "gia_thuyet"}
    for i in range(1, 6)]}

BAN_HANG = {"phien_ban": 1,
            "khoa_hoc": [{"ma": "a1", "ten": "Hạng A1", "hoc_phi_vnd": 1500000, "gom": ["Học"], "khong_gom": ["Lệ phí"],
                          "so_buoi": None, "thoi_gian_hoc": "", "trang_thai": "da_xac_nhan"}],
            "quy_trinh_dang_ky": {"buoc": [], "trang_thai": "gia_thuyet"},
            "giay_to": {"danh_sach": [], "trang_thai": "gia_thuyet"},
            "lich_khai_giang": [{"khoa": "", "ngay": None, "trang_thai": "gia_thuyet"}],
            "uu_dai": [{"noi_dung": "Đi nhóm 3 người, mỗi người bớt 50.000đ", "thuong_xuyen": True, "het_han": None,
                        "ngay_xem_lai": "2027-05-23", "trang_thai": "da_xac_nhan"},
                       {"noi_dung": "Giảm 300.000đ", "thuong_xuyen": False, "het_han": "2026-01-01",
                        "trang_thai": "da_xac_nhan"}],
            "cau_hoi_thuong_gap": [{"hoi": "Học ở đâu?", "tra_loi": "Sân A.", "trang_thai": "da_xac_nhan"},
                                   {"hoi": "Bao giờ thi?", "tra_loi": "Chưa chắc.", "trang_thai": "gia_thuyet"}],
            "nguoi_dong_y_len_hinh": [{"ma": "", "trang_thai": "gia_thuyet"}],
            "moi_nhu": [{"ma": "", "nhom_hop": [], "trang_thai": "gia_thuyet"}],
            "cho_xac_nhan": [{"noi_dung": "Phí thi lại"}]}

BRAND = {"id": "kt", "cam": {"cum_tu_cam": ["bao đậu"], "cum_tu_cam_du_an": ["không phát sinh"],
                             "cau_sao_da_chot": ["bạn có biết"], "cau_sao_cho_duyet": ["dễ dàng"]},
         "chu_de": [{"ma": "luat-cu", "tru_cot": "Hỏi", "dinh_dang": "hoi-dap", "chu_de": "Đèn vàng?", "y_chinh": "Được đi",
                     "nguon_doi_chieu": "Luật 36/2024/QH15 Điều 11", "da_lam": False},
                    {"ma": "da-lam", "tru_cot": "Hỏi", "dinh_dang": "hoi-dap", "chu_de": "X?", "y_chinh": "",
                     "nguon_doi_chieu": "Luật 1", "da_lam": True},
                    {"ma": "hau-truong", "tru_cot": "Hậu", "dinh_dang": "x", "chu_de": "H", "y_chinh": "",
                     "nguon_doi_chieu": "Không cần nguồn luật", "da_lam": False}]}


@pytest.fixture()
def kenh(tmp_path):
    goc = tmp_path / "repo"
    b = goc / "brand" / "kt"
    b.mkdir(parents=True)
    for ten, d in (("lich", LICH), ("dinh-dang", DINH_DANG), ("doi-tuong", DOI_TUONG), ("ban-hang", BAN_HANG)):
        (b / f"{ten}.yaml").write_text(yaml.safe_dump(d, allow_unicode=True), encoding="utf-8")
    (b / "san-xuat.yaml").write_text(yaml.safe_dump({"khung_nhip": {"hoi": {"tru_cot": "Hỏi nhanh"}}},
                                                    allow_unicode=True), encoding="utf-8")
    (b / "hook.yaml").write_text(yaml.safe_dump({"hook_sao": ["dừng lướt"], "cong_thuc": [{"ma": "goi-dung-nguoi"}]},
                                                allow_unicode=True), encoding="utf-8")
    (b / "rubric-kich-ban.yaml").write_text(yaml.safe_dump(
        {"kiem_tra_may": {"uu_dai_thuong_xuyen": {"cum_gap_gap": ["sắp hết", "chỉ còn"]}}}, allow_unicode=True),
        encoding="utf-8")
    (b / "brand.json").write_text(json.dumps(BRAND, ensure_ascii=False), encoding="utf-8")
    bang = BangGia()
    S.khoi_tao(bang)
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": c["ma"], "chu_de": c["chu_de"], "dinh_dang": c["dinh_dang"],
                                     "trang_thai_san_xuat": "đã làm" if c["da_lam"] else "ý tưởng"}
                                    for c in BRAND["chu_de"]])
    tm = tmp_path / "kenh-goc"
    tm.mkdir()
    return goc, bang, tm


def them_cau_hoi(bang, *dong):
    t = bang.tab(CAU_HOI_KHACH.ten)
    h = t.doc_tat_ca()[0]
    for i, d in enumerate(dong, start=len(t.doc_tat_ca()) + 1):
        for k, v in d.items():
            t.dat(i, h.index(k) + 1, v)


def dat_o(bang, tab, ma, cot, v):
    t = bang.tab(tab)
    h = t.doc_tat_ca()
    r = next(i for i, x in enumerate(h, start=1) if i > 1 and x[h[0].index("ma")] == ma)
    t.dat(r, h[0].index(cot) + 1, v)


# ---------------------------------------------------------------- tuần, tiền, dữ kiện
def test_tuan_toi_va_ngay_cua_thu():
    assert Y.tuan_toi(HOM_NAY) == TUAN
    t2 = Y.thu_hai_cua(TUAN)
    assert t2 == dt.date(2026, 11, 30) and Y.ngay_cua(t2, 8) == dt.date(2026, 12, 6)
    for sai in ("2026-49", "2026-W54", ""):
        with pytest.raises(Y.LoiYTuong):
            Y.thu_hai_cua(sai)


@pytest.mark.parametrize("vb,tien", [
    ("Học phí 1.500.000đ trọn gói", {1500000}), ("chỉ 1,5 triệu", {1500000}), ("giảm 70 nghìn", {70000}),
    ("giảm 70k mỗi người", {70000}), ("3.100.000 đồng", {3100000}), ("đi xe 10 năm, Điều 11", set()),
])
def test_so_tien(vb, tien):
    assert Y.so_tien(vb) == tien


def test_du_kien_chi_lay_muc_da_xac_nhan():
    co, thieu, tien = Y.du_kien(BAN_HANG, HOM_NAY)
    ids = {x["id"] for x in co}
    assert {"khoa_hoc.a1.hoc_phi", "khoa_hoc.a1.gom", "khoa_hoc.a1.khong_gom", "uu_dai.0",
            "cau_hoi_thuong_gap.0"} == ids
    assert tien == {1500000, 50000}           # ưu đãi hết hạn (300.000đ) không được nói
    assert any("số buổi" in x for x in thieu) and any("mồi nhử" in x for x in thieu)
    assert any("Phí thi lại" in x for x in thieu) and any("lịch khai giảng" in x for x in thieu)
    assert "KHÔNG nói hạn chót" in next(x for x in co if x["id"] == "uu_dai.0")["noi_dung"]
    assert Y.du_kien(None, HOM_NAY)[0] == []


# ---------------------------------------------------------------- ô của tuần
def test_dau_vao_o_dieu_kien_du_phong_mua(kenh):
    goc, bang, _ = kenh
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    o = {x.thu: x for x in v["o"]}
    assert len(o) == 7 and all(not x.bo for x in o.values())
    assert o[2].dinh_dang == ["luat-hoi"] and o[2].ngay == dt.date(2026, 11, 30)
    # thứ 5: học phí chưa đủ ô (so_buoi trống) -> dự phòng bằng định dạng chuyển đổi của ngày khác
    assert o[5].dinh_dang == ["chua-bang", "so-truot"] and "khoa_hoc" in o[5].du_phong
    assert o[8].du_phong and "lich_khai_giang" in o[8].du_phong
    # thứ 6: chưa có câu hỏi khách -> bỏ trả lời bình luận
    assert o[6].dinh_dang == ["luat-hoi"]
    # mùa: 2 ô chuyển đổi đầu tiên phải nói với nhóm của mùa
    assert o[3].mua == ["n1", "n5"] and o[5].mua == ["n1", "n5"] and o[8].mua == []
    yc = v["yeu_cau"]
    assert [x["ma"] for x in yc["chu_de_luat_con_lai"]] == ["luat-cu"]
    assert {"nhom": "n1", "noi_lo": "Lo 1a"} in yc["ma_tran_chua_lam"]
    assert set(yc["chua_thu"]["nhom"]) == {"n1", "n2", "n3", "n4", "n5"}
    assert "luat-hoi" in yc["chua_thu"]["dinh_dang"]


def test_dau_vao_giu_o_da_co_va_dung_cau_hoi_khach(kenh):
    goc, bang, _ = kenh
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": "cu", "ngay_du_kien": "2026-11-30", "doi_tuong": "n1",
                                     "noi_lo": "Lo 1a", "dinh_dang": "luat-hoi"}])
    them_cau_hoi(bang, {"kenh": "kt", "ngay": "2026-11-20", "nen_tang": "Facebook", "cau_hoi": "Học mấy buổi?"},
                 {"kenh": "", "cau_hoi": "Không có kênh"})
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    o = {x.thu: x for x in v["o"]}
    assert o[2].bo and o[6].dinh_dang == ["tra-loi-binh-luan", "luat-hoi"]
    assert [c["cau_hoi"] for c in v["cau_hoi_chua"]] == ["Học mấy buổi?"]
    assert v["cau_hoi_chua"][0]["ma_cau_hoi"].startswith("ch-")
    assert any("thiếu cột kenh" in x for x in v["canh_bao"])
    assert {"nhom": "n1", "noi_lo": "Lo 1a"} not in v["yeu_cau"]["ma_tran_chua_lam"]


def test_danh_ma_cau_hoi_on_dinh_khong_dung_cot_nguoi(kenh):
    _, bang, _ = kenh
    them_cau_hoi(bang, {"kenh": "kt", "cau_hoi": "A?"}, {"kenh": "kt", "cau_hoi": "A?"})
    t = bang.tab(CAU_HOI_KHACH.ten)
    truoc = [r[1:] for r in t.doc_tat_ca()]
    ra = S.danh_ma_dong(bang, CAU_HOI_KHACH, lambda d: "ch-x")
    assert [m for _r, m in ra] == ["ch-x", "ch-x-2"]
    assert [r[1:] for r in t.doc_tat_ca()] == truoc        # chỉ cột mã đổi
    assert S.danh_ma_dong(bang, CAU_HOI_KHACH, lambda d: "ch-y") == []   # đã có mã: không đánh lại


# ---------------------------------------------------------------- kiểm chủ đề
def tot(thu, **k):
    base = {"thu": thu, "dinh_dang": "chua-bang", "doi_tuong": "n1", "noi_lo": "Lo 1a", "nguon_y_tuong": "ma_tran",
            "ma": f"chu-de-{thu}", "chu_de": "Đi xe 10 năm chưa có bằng, học có khó?", "y_chinh": "Không khó.",
            "hook_de_xuat": "Đi xe mười năm chưa có bằng?", "co_noi_dung_luat": False, "du_kien_dung": [],
            "du_kien_thieu": [], "thu_moi": False}
    return {**base, **k}


def bo_tuan():
    return [tot(2, dinh_dang="luat-hoi", ma_co_san="luat-cu", ma="", nguon_y_tuong="luat", noi_lo="Lo 1b",
                co_noi_dung_luat=True, thu_moi=True),
            tot(3), tot(4, dinh_dang="buoi-hoc", doi_tuong="n4", noi_lo="Lo 4a"),
            tot(5, doi_tuong="n5", noi_lo="Lo 5a", dinh_dang="chua-bang",
                chu_de="Học phí A1 1.500.000đ gồm gì?", du_kien_dung=["khoa_hoc.a1.hoc_phi"]),
            tot(6, dinh_dang="luat-hoi", doi_tuong="n3", noi_lo="Lo 3a", nguon_y_tuong="luat", ma="luat-moi",
                co_noi_dung_luat=True, nguon_doi_chieu="Luật 36/2024/QH15"),
            tot(7, dinh_dang="buoi-hoc", doi_tuong="n2", noi_lo="Lo 2a"),
            tot(8, dinh_dang="so-truot", doi_tuong="n4", noi_lo="Lo 4b")]


def test_kiem_bo_tuan_hop_le(kenh):
    goc, bang, _ = kenh
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    kq = Y.kiem({"chu_de": bo_tuan()}, v)
    assert kq.loi == {} and kq.loi_chung == [] and len(kq.hop_le) == 7


@pytest.mark.parametrize("sua,tim", [
    ({"dinh_dang": "buoi-hoc"}, "không thuộc ô này"),
    ({"doi_tuong": "n2", "noi_lo": "Lo 2a"}, "ô mùa"),
    ({"noi_lo": "Lo tự nghĩ"}, "không có trong noi_lo"),
    ({"hook_de_xuat": "Học ở đây bao đậu"}, "cụm từ cấm"),
    ({"hook_de_xuat": "Dừng lướt nếu chưa có bằng"}, "hook sáo"),
    ({"y_chinh": "Ưu đãi sắp hết"}, "gấp gáp giả"),
    ({"y_chinh": "Học phí chỉ 900.000đ"}, "số tiền chưa xác nhận"),
    ({"du_kien_dung": ["khoa_hoc.a1.so_buoi"]}, "không phải dữ kiện đã xác nhận"),
    ({"du_kien_thieu": ["số buổi học"]}, "thiếu dữ kiện bán hàng"),
    ({"ma": "Có Dấu"}, "chữ thường không dấu"),
    ({"ma": "luat-cu"}, "đã có"),
    ({"co_noi_dung_luat": True, "nguon_doi_chieu": "Không cần nguồn luật"}, "văn bản cần đối chiếu"),
    ({"nguon_y_tuong": "cau_hoi_khach", "ma_cau_hoi": "ch-khong"}, "không phải câu hỏi khách"),
    ({"chu_de": "Có bằng trước Tết không?"}, "có bằng trước Tết"),
])
def test_kiem_bat_loi(kenh, sua, tim):
    goc, bang, _ = kenh
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    ds = bo_tuan()
    ds[1] = {**ds[1], **sua}
    kq = Y.kiem({"chu_de": ds}, v)
    assert 3 in kq.loi and any(tim in x for x in kq.loi[3]), kq.loi


def test_kiem_trung_60_ngay_va_trong_tuan(kenh):
    goc, bang, _ = kenh
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "kt", "ma": "cu", "ngay_du_kien": "2026-11-10", "doi_tuong": "n1",
                                     "noi_lo": "Lo 1a", "dinh_dang": "chua-bang"}])
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    kq = Y.kiem({"chu_de": bo_tuan()}, v)
    assert any("trùng chủ đề cu" in x for x in kq.loi[3])
    ds = bo_tuan()
    ds[3] = {**ds[1], "thu": 5, "ma": "khac"}       # thứ 5 lặp đúng bộ ba của thứ 3
    v2 = Y.dau_vao(BangGiaTu(bang, bo="cu"), "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    kq2 = Y.kiem({"chu_de": ds}, v2)
    assert any("trong cùng tuần" in x for x in kq2.loi[5])


class BangGiaTu:
    """Bảng giả đọc dữ liệu của bảng khác nhưng bỏ một dòng Ý tưởng theo mã (không đụng bảng gốc)."""
    def __init__(self, goc, bo):
        self._b = copy.deepcopy(goc)
        t = self._b.tab("Ý tưởng")
        h = t.o[0]
        t.o = [r for r in t.o if not (len(r) > h.index("ma") and r[h.index("ma")] == bo)]

    def __getattr__(self, k):
        return getattr(self._b, k)


def test_kiem_bat_buoc_mot_chu_de_thu_moi(kenh):
    goc, bang, _ = kenh
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    ds = [{**c, "thu_moi": False} for c in bo_tuan()]
    kq = Y.kiem({"chu_de": ds}, v)
    assert any("thu_moi" in x for x in kq.loi_chung)


def test_kiem_o_thieu_va_bo_qua(kenh):
    goc, bang, _ = kenh
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    ds = [c for c in bo_tuan() if c["thu"] not in (5, 8)]
    kq = Y.kiem({"chu_de": ds, "bo_qua": [{"thu": 8, "ly_do": "thiếu lịch khai giảng"}]}, v)
    assert kq.loi[5] == ["ô chưa có chủ đề"] and kq.bo == {8: "thiếu lịch khai giảng"}


# ---------------------------------------------------------------- chạy cả lệnh
def agent_gia(cac_vong: list[dict], goi: list):
    def ham(prompt, *, du_an, goc):
        yc = json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8"))
        goi.append(yc)
        (du_an / "y_tuong.json").write_text(json.dumps(cac_vong[len(goi) - 1], ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 60000, "total_cost_usd": 0.31}
    return ham


def test_chay_ghi_chu_de_may_sheet_cau_hoi_nhat_ky_va_vong_sua(kenh):
    goc, bang, tm = kenh
    them_cau_hoi(bang, {"kenh": "kt", "ngay": "2026-11-20", "cau_hoi": "Học mấy buổi thì thi được?", "nhom": "n3"})
    ma_ch = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)["cau_hoi_chua"][0]["ma_cau_hoi"]
    vong1 = bo_tuan()
    vong1[4] = tot(6, dinh_dang="tra-loi-binh-luan", doi_tuong="n3", noi_lo="Học mấy buổi", ma="hoc-may-buoi",
                   nguon_y_tuong="cau_hoi_khach", ma_cau_hoi=ma_ch)
    vong1[1] = {**vong1[1], "hook_de_xuat": "Bao đậu cho người chưa có bằng"}   # lỗi: sửa ở vòng 2
    vong1 = [c for c in vong1 if c["thu"] != 8]
    vong2 = [c if c["thu"] != 3 else tot(3) for c in vong1]
    goi, nap = [], []
    kq = Y.chay(bang, "kt", TUAN, goc=goc, agent=agent_gia([{"chu_de": vong1}, {
        "chu_de": vong2, "bo_qua": [{"thu": 8, "ly_do": "thiếu lịch khai giảng"}]}], goi),
        nap=lambda k, g: nap.append(k), thu_muc_kenh=tm, hom_nay=HOM_NAY, log=lambda s: None)
    assert len(goi) == 2 and "phan_hoi" in goi[1] and "3" in goi[1]["phan_hoi"]["loi_theo_o"]
    assert len(kq.chu_de) == 6 and kq.so_luot == 2 and abs(kq.chi_phi_usd - 0.62) < 1e-9 and nap == ["kt"]
    assert any("Chủ Nhật" in o and "thiếu lịch khai giảng" in ly for o, ly in kq.bo)
    md = (tm / Y.CHU_DE_MAY).read_text(encoding="utf-8")
    assert "| chu-de-3 | chua-bang | chua-bang |" in md and "luat-cu" not in md      # chủ đề có sẵn không chép lại
    assert "| hoc-may-buoi | tra-loi-binh-luan | tra-loi-binh-luan |" in md
    assert "| chu-de-4 | buoi-hoc | buoi-hoc | Đi xe 10 năm chưa có bằng, học có khó? | Không khó. | Không cần nguồn luật | |" in md
    rows = {d["ma"]: d for d in S.doc_dong(bang, Y_TUONG)}
    r = rows["chu-de-3"]
    assert (r["doi_tuong"], r["noi_lo"], r["tang"], r["ngay_du_kien"]) == ("n1", "Lo 1a", "chuyen_doi", "2026-12-01")
    assert r["duyet_chu_de"] == "" and r["trang_thai_san_xuat"] == "ý tưởng" and "mồi nhử" in r["ghi_chu_may"]
    cu = rows["luat-cu"]
    assert cu["dinh_dang"] == "luat-hoi" and cu["chu_de"] == "Đèn vàng?" and cu["ngay_du_kien"] == "2026-11-30"
    assert "thử mới" in cu["nguon_y_tuong"]
    assert rows["hoc-may-buoi"]["cau_hoi_khach"] == "Học mấy buổi thì thi được?"
    ch = S.doc_dong(bang, CAU_HOI_KHACH)[0]
    assert ch["da_dung_cho"] == "hoc-may-buoi" and ch["cau_hoi"] == "Học mấy buổi thì thi được?"
    nk = S.doc_dong(bang, NHAT_KY)
    assert any(d["buoc"] == "y_tuong" and d["so_luot_tro_ly"] == "2" and "0.62 USD" in d["chi_tiet"] for d in nk)
    assert any(d["buoc"] == "y_tuong.bo" and "lịch khai giảng" in d["chi_tiet"] for d in nk)
    # chạy lại cùng tuần: ô đã có thì giữ, chỉ còn Chủ Nhật trống
    v = Y.dau_vao(bang, "kt", TUAN, goc=goc, hom_nay=HOM_NAY)
    assert [x.thu for x in v["o"] if not x.bo] == [8]
    out = Y.in_ket_qua(kq)
    assert "nguon-luat" in out and "--ma luat-cu" in out and "--ma chu-de-3" not in out


def test_chay_che_do_thu_khong_goi_agent_khong_ghi(kenh):
    goc, bang, tm = kenh
    truoc = copy.deepcopy([t.o for t in bang.tabs])
    kq = Y.chay(bang, "kt", TUAN, goc=goc, thu=True, agent=lambda *a, **k: pytest.fail("không gọi"),
                nap=lambda *a: pytest.fail("không nạp"), thu_muc_kenh=tm, hom_nay=HOM_NAY, log=lambda s: None)
    assert kq.chu_de == [] and [t.o for t in bang.tabs] == truoc and not (tm / Y.CHU_DE_MAY).exists()


def test_ghi_chu_de_may_sao_luu_va_giu_dong_cu(tmp_path):
    Y.ghi_chu_de_may(tmp_path, [{"ma": "a", "tru_cot": "T", "dinh_dang": "d", "chu_de": "A | B", "y_chinh": "x\ny",
                                 "nguon_doi_chieu": "Không cần nguồn luật"}])
    sl = Y.ghi_chu_de_may(tmp_path, [{"ma": "b", "tru_cot": "T", "dinh_dang": "d", "chu_de": "B", "y_chinh": "",
                                      "nguon_doi_chieu": "n"}])
    md = (tmp_path / Y.CHU_DE_MAY).read_text(encoding="utf-8")
    assert "| a | T | d | A / B | x y | Không cần nguồn luật | |" in md and "| b | T | d | B |  | n | |" in md
    assert sl and "| b |" not in sl.read_text(encoding="utf-8")
    from tools_local.nap_kenh import doc_chu_de
    assert [r["ma"] for r in doc_chu_de(md, None, None)] == ["a", "b"]


def test_san_xuat_cau_hoi_khach_chuoi_thanh_danh_sach():
    import inspect
    from may_reels import san_xuat
    assert "[chk] if isinstance(chk, str)" in inspect.getsource(san_xuat._yeu_cau)


def test_tru_cot_dinh_dang_luat_theo_khung_nhip():
    sx = {"khung_nhip": {"hoi": {"tru_cot": "Hỏi nhanh"}}}
    assert Y.tru_cot_cua({"ma": "luat-hoi", "ten": "Luật", "khung_nhip": "hoi"}, sx) == "Hỏi nhanh"
    assert Y.tru_cot_cua({"ma": "chua-bang", "ten": "Chưa bằng"}, sx) == "Chưa bằng"
