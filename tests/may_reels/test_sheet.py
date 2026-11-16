"""Lớp nối Sheet: tạo tab, không ghi cột người, không trùng dòng, chịu được người sửa Sheet cùng lúc."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from may_reels import sheet as S
from may_reels.chu_de import nap_chu_de
from may_reels.cot_sheet import HANG_CHO, NHAT_KY, TAT_CA, Y_TUONG, NGUOI
from tests.may_reels.sheet_gia import BangGia

REPO = Path(__file__).resolve().parents[2]
GIO = lambda: "2026-11-15 10:00:00"  # noqa: E731


@pytest.fixture()
def bang():
    b = BangGia()
    S.khoi_tao(b)
    return b


def cot(tab_gia, ten):
    return tab_gia.doc_tat_ca()[0].index(ten) + 1


# ---------------------------------------------------------------- cấu trúc cột
def test_khai_bao_cot_dung_yeu_cau():
    assert [t.ten for t in TAT_CA] == ["Ý tưởng", "Hàng chờ", "Cần quay", "Số liệu", "Nhật ký"]
    assert Y_TUONG.ten_cot == ["ma", "kenh", "tru_cot", "dinh_dang", "chu_de", "hook_de_xuat",
                               "nguon_doi_chieu", "diem", "duyet_chu_de", "trang_thai_san_xuat", "nguon_de_xuat",
                               "trich_nguyen_van", "link_nguon", "ngay_tra", "ghi_chu_may", "xac_nhan_nguon"]
    assert Y_TUONG.cot_nguoi == ["duyet_chu_de", "xac_nhan_nguon"]
    assert Y_TUONG.lay("xac_nhan_nguon").lua_chon == ("Đúng", "Sai")
    assert Y_TUONG.lay("duyet_chu_de").lua_chon == ("Chờ", "Làm", "Bỏ")
    assert HANG_CHO.ten_cot == ["ma_video", "kenh", "nen_tang", "link_xem_thu", "caption", "hashtag", "diem_qa",
                                "canh_bao", "duyet", "ghi_chu_sua", "gio_dang", "trang_thai_dang", "link_bai",
                                "id_bai", "loi", "cap_nhat_luc", "ghi_chu_may", "diem_cua_toi", "nhan_xet"]
    assert HANG_CHO.cot_nguoi == ["duyet", "ghi_chu_sua", "gio_dang", "diem_cua_toi", "nhan_xet"]
    assert HANG_CHO.lay("duyet").lua_chon == ("Chờ duyệt", "Duyệt", "Sửa", "Bỏ")
    assert HANG_CHO.khoa == ("ma_video", "nen_tang")
    for t in TAT_CA:
        for k in t.khoa:
            assert t.lay(k).cua != NGUOI


# ---------------------------------------------------------------- init
def test_init_tao_5_tab_tieu_de_mau_va_dropdown():
    b = BangGia()
    kq = S.khoi_tao(b)
    assert kq.tab_tao_moi == [t.ten for t in TAT_CA]
    for t in TAT_CA:
        assert b.tab(t.ten).doc_tat_ca()[0] == t.ten_cot
    vang = [r["repeatCell"] for r in b.yeu_cau_dinh_dang
            if "repeatCell" in r and r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor") == S.MAU_COT_NGUOI
            and r["repeatCell"]["range"]["startRowIndex"] == 1]
    so_cot_nguoi = sum(len(t.cot_nguoi) for t in TAT_CA)
    assert len(vang) == so_cot_nguoi
    dd = {(r["setDataValidation"]["range"]["sheetId"], r["setDataValidation"]["range"]["startColumnIndex"]):
          [v["userEnteredValue"] for v in r["setDataValidation"]["rule"]["condition"]["values"]]
          for r in b.yeu_cau_dinh_dang if "setDataValidation" in r}
    yt, hc = b.tab("Ý tưởng"), b.tab("Hàng chờ")
    assert dd[(yt.sheet_id, cot(yt, "duyet_chu_de") - 1)] == ["Chờ", "Làm", "Bỏ"]
    assert dd[(hc.sheet_id, cot(hc, "duyet") - 1)] == ["Chờ duyệt", "Duyệt", "Sửa", "Bỏ"]
    assert (hc.sheet_id, cot(hc, "ghi_chu_sua") - 1) not in dd


def test_init_chay_lai_khong_tao_gi_them(bang):
    truoc = [(t.title, t.doc_tat_ca()) for t in bang.tabs]
    kq = S.khoi_tao(bang)
    assert kq.tab_tao_moi == [] and kq.cot_them == {}
    assert [(t.title, t.doc_tat_ca()) for t in bang.tabs] == truoc


def test_init_them_cot_thieu_vao_cuoi_khong_dung_cot_va_du_lieu_cua_nguoi():
    b = BangGia()
    t = b.tao_tab("Ý tưởng", 1000, 4)
    for i, v in enumerate(["kenh", "ma", "cot_rieng_cua_toi", "chu_de"], start=1):
        t.dat(1, i, v)
    for i, v in enumerate(["k1", "a", "ghi chú riêng", "Chủ đề A"], start=1):
        t.dat(2, i, v)
    kq = S.khoi_tao(b, [Y_TUONG])
    tieu_de = t.doc_tat_ca()[0]
    assert tieu_de[:4] == ["kenh", "ma", "cot_rieng_cua_toi", "chu_de"]
    assert set(Y_TUONG.ten_cot) <= set(tieu_de)
    assert t.doc_tat_ca()[1][:4] == ["k1", "a", "ghi chú riêng", "Chủ đề A"]
    assert "chu_de" not in kq.cot_them["Ý tưởng"]


def test_init_che_do_thu_khong_ghi():
    b = BangGia()
    kq = S.khoi_tao(b, thu=True)
    assert len(kq.tab_tao_moi) == 5 and b.tabs == [] and b.yeu_cau_dinh_dang == []


# ---------------------------------------------------------------- ghi theo khóa
def test_tu_choi_ghi_cot_nguoi_truoc_khi_cham_sheet(bang):
    yt = bang.tab("Ý tưởng")
    doc_truoc = yt.so_lan_doc
    with pytest.raises(S.LoiGhiCotNguoi):
        S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a", "duyet_chu_de": "Làm"}])
    with pytest.raises(S.LoiGhiCotNguoi):
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": "tiktok", "duyet": "Duyệt"}])
    assert yt.so_lan_doc == doc_truoc and yt.lan_ghi[1:] == [] and yt.lan_them == []


def test_khong_de_cot_nguoi_khi_cap_nhat(bang):
    yt = bang.tab("Ý tưởng")
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a", "chu_de": "Cũ"}])
    yt.dat(2, cot(yt, "duyet_chu_de"), "Làm")  # người duyệt
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a", "chu_de": "Mới", "diem": "80"}])
    assert yt.lay(2, cot(yt, "duyet_chu_de")) == "Làm"
    assert yt.lay(2, cot(yt, "chu_de")) == "Mới"
    cot_nguoi = {cot(yt, c) for c in Y_TUONG.cot_nguoi}
    for lan in yt.lan_ghi[1:]:
        assert not {c for _, c, _ in lan} & cot_nguoi


def test_dong_moi_de_trong_cot_nguoi(bang):
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": "tiktok", "caption": "c"}], bay_gio=GIO)
    hc = bang.tab("Hàng chờ")
    for c in HANG_CHO.cot_nguoi:
        assert hc.lay(2, cot(hc, c)) == ""
    assert hc.lay(2, cot(hc, "cap_nhat_luc")) == "2026-11-15 10:00:00"


def test_khong_trung_dong_va_khong_ghi_khi_khong_doi(bang):
    d = [{"ma_video": "x-1", "nen_tang": "tiktok", "caption": "c"},
         {"ma_video": "x-1", "nen_tang": "yt_shorts", "caption": "c"}]
    S.ghi_theo_khoa(bang, HANG_CHO, d, bay_gio=GIO)
    hc = bang.tab("Hàng chờ")
    so_ghi = len(hc.lan_ghi)
    kq = S.ghi_theo_khoa(bang, HANG_CHO, d, bay_gio=GIO)
    assert kq.them == [] and len(kq.giu_nguyen) == 2
    assert len(hc.doc_tat_ca()) == 3 and len(hc.lan_ghi) == so_ghi


def test_cap_nhat_dung_dong_va_tu_ghi_thoi_diem(bang):
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": "tiktok"},
                                     {"ma_video": "x-2", "nen_tang": "tiktok"}], bay_gio=GIO)
    kq = S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-2", "nen_tang": "tiktok", "trang_thai_dang": "da_dang"}],
                         bay_gio=lambda: "2026-11-16 08:00:00")
    hc = bang.tab("Hàng chờ")
    assert kq.cap_nhat == {("x-2", "tiktok"): ["trang_thai_dang"]}
    assert hc.lay(3, cot(hc, "trang_thai_dang")) == "da_dang"
    assert hc.lay(3, cot(hc, "cap_nhat_luc")) == "2026-11-16 08:00:00"
    assert hc.lay(2, cot(hc, "cap_nhat_luc")) == "2026-11-15 10:00:00"


def test_tim_cot_theo_ten_khi_nguoi_doi_cho_cot():
    b = BangGia()
    t = b.tao_tab("Ý tưởng", 1000, 12)
    dao = list(reversed(Y_TUONG.ten_cot))
    for i, v in enumerate(dao, start=1):
        t.dat(1, i, v)
    S.ghi_theo_khoa(b, Y_TUONG, [{"kenh": "k1", "ma": "a", "chu_de": "A"}])
    assert t.lay(2, dao.index("chu_de") + 1) == "A"
    assert t.lay(2, dao.index("ma") + 1) == "a"


def test_nguoi_chen_dong_trong_luc_may_ghi_thi_ghi_lai_dung_dong(bang):
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a"}, {"kenh": "k1", "ma": "b"}])
    yt = bang.tab("Ý tưởng")
    da_chen = []

    def nguoi_chen(tab, lan):
        if not da_chen:  # ngay sau lần đọc đầu, người chèn một dòng lên trên
            da_chen.append(lan)
            tab.chen_dong(2, ["ghi tay"])

    yt.truoc_khi_doc = None
    so_lan = yt.so_lan_doc

    def hook(tab, lan):
        if lan == so_lan + 2:  # giữa lần đọc tính toán và lần đọc kiểm tra
            nguoi_chen(tab, lan)
    yt.truoc_khi_doc = hook
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "b", "chu_de": "B"}])
    hang = yt.doc_tat_ca()
    dong_b = next(h for h in hang if h[cot(yt, "ma") - 1] == "b")
    assert dong_b[cot(yt, "chu_de") - 1] == "B"
    assert hang[1][0] == "ghi tay" and hang[1][cot(yt, "chu_de") - 1] == ""


def test_dong_doi_cho_lien_tuc_thi_bao_loi(bang):
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a"}])
    yt = bang.tab("Ý tưởng")
    yt.truoc_khi_doc = lambda tab, lan: tab.chen_dong(2, [f"chèn {lan}"])  # người chèn dòng liên tục
    with pytest.raises(S.LoiDongDoiCho):
        S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a", "chu_de": "X"}])


def test_dau_vao_trung_khoa_hoac_thieu_khoa(bang):
    with pytest.raises(S.LoiSheet):
        S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a"}, {"kenh": "k1", "ma": "a"}])
    with pytest.raises(S.LoiSheet):
        S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1"}])


def test_cung_ma_khac_kenh_la_hai_dong(bang):
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "a"}, {"kenh": "k2", "ma": "a"}])
    assert len(bang.tab("Ý tưởng").doc_tat_ca()) == 3


def test_chua_init_thi_bao_loi_cau_truc():
    with pytest.raises(S.LoiCauTruc):
        S.ghi_theo_khoa(BangGia(), Y_TUONG, [{"kenh": "k1", "ma": "a"}])


def test_nhat_ky_chi_them_dong(bang):
    S.them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": "t1", "buoc": "x"}])
    S.them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": "t2", "buoc": "x"}])
    nk = bang.tab("Nhật ký")
    assert [h[0] for h in nk.doc_tat_ca()[1:]] == ["t1", "t2"]
    assert nk.lan_ghi[1:] == []


def test_ghi_raw_giu_nguyen_chuoi(bang):
    S.ghi_theo_khoa(bang, Y_TUONG, [{"kenh": "k1", "ma": "007", "chu_de": "  1/3 "}])
    yt = bang.tab("Ý tưởng")
    assert yt.lay(2, cot(yt, "ma")) == "007" and yt.lay(2, cot(yt, "chu_de")) == "1/3"


# ---------------------------------------------------------------- nạp chủ đề
def brand_gia(goc: Path, kenh: str = "kenhthu") -> None:
    p = goc / "brand" / kenh
    p.mkdir(parents=True)
    p.joinpath("brand.json").write_text(json.dumps({"id": kenh, "chu_de": [
        {"ma": "a", "tru_cot": "t", "dinh_dang": "hoi-dap", "chu_de": "A?", "nguon_doi_chieu": "n", "da_lam": True},
        {"ma": "b", "tru_cot": "t", "dinh_dang": "giai-thich", "chu_de": "B?", "nguon_doi_chieu": "n", "da_lam": False},
    ]}, ensure_ascii=False), encoding="utf-8")


def test_nap_chu_de_khong_trung_va_khong_lui_tien_do(bang, tmp_path):
    brand_gia(tmp_path)
    da, chua = nap_chu_de(bang, "kenhthu", goc=tmp_path)
    assert len(da.them) + len(chua.them) == 2
    yt = bang.tab("Ý tưởng")
    tt = cot(yt, "trang_thai_san_xuat")
    assert yt.lay(2, tt) == "đã làm" and yt.lay(3, tt) == "ý tưởng"
    yt.dat(3, tt, "đang sản xuất")           # máy đã tiến tới
    yt.dat(3, cot(yt, "duyet_chu_de"), "Làm")  # người đã duyệt
    da, chua = nap_chu_de(bang, "kenhthu", goc=tmp_path)
    assert da.them == chua.them == [] and da.cap_nhat == chua.cap_nhat == {}
    assert len(yt.doc_tat_ca()) == 3
    assert yt.lay(3, tt) == "đang sản xuất" and yt.lay(3, cot(yt, "duyet_chu_de")) == "Làm"


def test_nap_chu_de_che_do_thu(bang, tmp_path):
    brand_gia(tmp_path)
    da, chua = nap_chu_de(bang, "kenhthu", thu=True, goc=tmp_path)
    assert len(da.them) + len(chua.them) == 2
    assert len(bang.tab("Ý tưởng").doc_tat_ca()) == 1


def test_nap_chu_de_kenh_khong_hop_le(bang, tmp_path):
    with pytest.raises(ValueError):
        nap_chu_de(bang, "../x", goc=tmp_path)
    with pytest.raises(FileNotFoundError):
        nap_chu_de(bang, "khongco", goc=tmp_path)


# ---------------------------------------------------------------- CLI và môi trường
def test_cli_init_va_nap_chu_de_voi_bang_gia(monkeypatch, tmp_path, capsys):
    from may_reels import __main__ as cli
    from may_reels import chu_de
    b = BangGia()
    monkeypatch.setattr(cli, "mo_tu_env", lambda: b)
    brand_gia(tmp_path)
    monkeypatch.setattr(chu_de, "GOC", tmp_path)
    assert cli.main(["sheet", "init"]) == 0
    assert cli.main(["sheet", "nap-chu-de", "--kenh", "kenhthu"]) == 0
    assert cli.main(["sheet", "nap-chu-de", "--kenh", "kenhthu"]) == 0
    out = capsys.readouterr().out
    assert "thêm 2 dòng" in out and "thêm 0 dòng" in out
    assert len(b.tab("Ý tưởng").doc_tat_ca()) == 3
    assert [h[3] for h in b.tab("Nhật ký").doc_tat_ca()[1:]] == ["sheet.init", "sheet.nap_chu_de", "sheet.nap_chu_de"]


def test_mo_tu_env_thieu_bien(monkeypatch, tmp_path):
    monkeypatch.delenv(S.BIEN_SA_JSON, raising=False)
    monkeypatch.delenv(S.BIEN_SHEET_ID, raising=False)
    with pytest.raises(S.LoiSheet, match="MAY_REELS_SA_JSON"):
        S.mo_tu_env(goc=tmp_path)
    monkeypatch.setenv(S.BIEN_SA_JSON, "secrets/khong-co.json")
    monkeypatch.setenv(S.BIEN_SHEET_ID, "abc")
    with pytest.raises(S.LoiSheet, match="Không thấy file khóa"):
        S.mo_tu_env(goc=tmp_path)


def test_import_khong_keo_thu_vien_mang():
    code = "import sys, may_reels.sheet, may_reels.chu_de, may_reels.__main__; print('gspread' in sys.modules)"
    kq = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    assert kq.returncode == 0, kq.stderr
    assert kq.stdout.strip() == "False"


def test_khong_viet_cung_ten_kenh():
    for p in (REPO / "may_reels").rglob("*.py"):
        assert "vanxuan" not in p.read_text(encoding="utf-8").lower(), p


def test_env_example_co_bien_may_reels():
    s = (REPO / ".env.example").read_text(encoding="utf-8")
    assert "MAY_REELS_SA_JSON=" in s and "MAY_REELS_SHEET_ID=" in s


def test_adapter_gspread_ghi_raw_va_append_cuoi_bang():
    pytest.importorskip("gspread")
    from gspread.utils import InsertDataOption, ValueInputOption

    class WsGia:
        title, id, col_count = "Hàng chờ", 7, 16

        def __init__(self):
            self.goi = []

        def batch_update(self, data, **kw):
            self.goi.append(("batch_update", data, kw))

        def append_rows(self, values, **kw):
            self.goi.append(("append_rows", values, kw))

    ws = WsGia()
    t = S.GspreadTab(ws)
    t.ghi_o([(2, 3, "a"), (10, 28, "b")])
    t.them_dong([["x", "y"]])
    t.ghi_o([])
    t.them_dong([])
    (_, data, kw1), (_, values, kw2) = ws.goi
    assert data == [{"range": "C2", "values": [["a"]]}, {"range": "AB10", "values": [["b"]]}]
    assert kw1["value_input_option"] == ValueInputOption.raw
    assert values == [["x", "y"]]
    assert kw2 == {"value_input_option": ValueInputOption.raw, "insert_data_option": InsertDataOption.insert_rows,
                   "table_range": "A1"}
    assert (t.title, t.sheet_id, t.so_cot) == ("Hàng chờ", 7, 16)


# ---------------------------------------------------------------- ngoại lệ cột duyet
def test_ngoai_le_khoi_tao_chi_ghi_dong_moi_va_chi_cho_duyet(bang):
    hc = bang.tab("Hàng chờ")
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": "tiktok", "duyet": "Chờ duyệt"}],
                    ngoai_le_duyet="khoi_tao", bay_gio=GIO)
    assert hc.lay(2, cot(hc, "duyet")) == "Chờ duyệt"
    hc.dat(2, cot(hc, "duyet"), "Duyệt")  # người duyệt
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": "tiktok", "duyet": "Chờ duyệt"}],
                    ngoai_le_duyet="khoi_tao", bay_gio=GIO)
    assert hc.lay(2, cot(hc, "duyet")) == "Duyệt"
    with pytest.raises(S.LoiGhiCotNguoi):
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-2", "nen_tang": "tiktok", "duyet": "Duyệt"}],
                        ngoai_le_duyet="khoi_tao")
    with pytest.raises(S.LoiGhiCotNguoi):  # không có ngoại lệ thì vẫn cấm
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-2", "nen_tang": "tiktok", "duyet": "Chờ duyệt"}])
    with pytest.raises(S.LoiGhiCotNguoi):  # ngoại lệ chỉ áp cho cột duyet
        S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-2", "nen_tang": "tiktok", "ghi_chu_sua": "x"}],
                        ngoai_le_duyet="khoi_tao")


def test_ngoai_le_sua_chi_doi_o_dang_la_sua(bang):
    hc = bang.tab("Hàng chờ")
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": n, "duyet": "Chờ duyệt"} for n in ("tiktok", "fb_reels")],
                    ngoai_le_duyet="khoi_tao", bay_gio=GIO)
    hc.dat(2, cot(hc, "duyet"), "Sửa")
    hc.dat(3, cot(hc, "duyet"), "Bỏ")
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-1", "nen_tang": n, "duyet": "Chờ duyệt"} for n in ("tiktok", "fb_reels")],
                    ngoai_le_duyet="sua", bay_gio=GIO)
    assert hc.lay(2, cot(hc, "duyet")) == "Chờ duyệt" and hc.lay(3, cot(hc, "duyet")) == "Bỏ"
    # sua không tạo dòng mới có duyet
    S.ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": "x-9", "nen_tang": "tiktok", "duyet": "Chờ duyệt"}],
                    ngoai_le_duyet="sua", bay_gio=GIO)
    assert next(h for h in hc.doc_tat_ca() if h[0] == "x-9")[cot(hc, "duyet") - 1] == ""
