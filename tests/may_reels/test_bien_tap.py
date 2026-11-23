"""Bộ biên kịch (C2b): thư viện tay nghề, kịch bản mẫu, máy kiểm chữ, biên tập (agent giả), vòng sửa trong sản xuất,
so sánh trước sau. Không gọi mạng, không gọi claude -p."""
from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from may_reels import bien_tap as BT
from may_reels import sheet as S
from may_reels.cot_sheet import HANG_CHO, NHAT_KY
from may_reels.dung.ke_hoach import giay_uoc_luong
from may_reels.san_xuat import MA_OK, san_xuat
from tests.may_reels.test_san_xuat import BRAND, CTA, SX, dung_gia, ke_hoach, nha_may  # noqa: F401 (fixture)

REPO = Path(__file__).resolve().parents[2]
KENH = REPO / "brand" / "vanxuan"
THU_VIEN = ("rubric-kich-ban.yaml", "hook.yaml", "giong-noi.yaml", "giu-chan.yaml", "dinh-dang.yaml")
TRANG_THAI = {"gia_thuyet", "da_xac_nhan"}


def _y(ten: str) -> dict:
    return yaml.safe_load((KENH / ten).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tv() -> dict:
    t = BT.doc_thu_vien("vanxuan", REPO)
    t["doi_tuong"] = _y("doi-tuong.mau.yaml")   # test dùng bản mẫu (bản thật chỉ có ở máy)
    return t


@pytest.fixture(scope="module")
def rb() -> dict:
    return BT.doc_rubric_kb("vanxuan", REPO)


@pytest.fixture(scope="module")
def brand_that() -> dict:
    return json.loads((KENH / "brand.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- thư viện tay nghề
def test_rubric_kich_ban_tong_100_va_tran_tro_dung(rb):
    assert sum(t["trong_so"] for t in rb["tieu_chi"].values()) == 100
    assert {t["tieu_chi"] for t in rb["tran"].values()} <= set(rb["tieu_chi"])
    assert rb["nguong"] and rb["so_vong_sua"] >= 1
    for m in rb["kiem_tra_may"]["mau_van_ai"]:   # mỗi mẫu bắt được ví dụ của chính nó
        assert re.search(m["mau"], m["vi_du"].casefold()), m["ma"]


def test_hook_yaml_du_cong_thuc_va_vi_du_dung_luat(tv, rb, brand_that):
    hk = tv["hook"]
    ct = hk["cong_thuc"]
    assert 10 <= len(ct) <= 12 and len({c["ma"] for c in ct}) == len(ct)
    dd = {d["ma"] for d in tv["dinh_dang"]["dinh_dang"]}
    nhom = {n["ma"] for n in tv["doi_tuong"]["nhom"]}
    cam = brand_that["cam"]["cum_tu_cam"] + brand_that["cam"]["cum_tu_cam_du_an"] + brand_that["cam"]["cau_sao_da_chot"]
    toi_da = rb["kiem_tra_may"]["hook_am_tiet_toi_da"]
    for c in ct:
        assert {"ma", "ten", "mo_ta", "khi_dung", "nhom_hop", "dinh_dang_hop", "vi_du", "loi_hay_gap"} <= set(c), c["ma"]
        assert c["trang_thai"] in TRANG_THAI and c["ngay_cap_nhat"]
        assert set(c["dinh_dang_hop"]) <= dd and set(c["nhom_hop"]) <= nhom, c["ma"]
        assert len(c["vi_du"]) == 2
        for v in c["vi_du"]:
            assert BT.so_am_tiet(v["noi"]) <= toi_da, (c["ma"], v["noi"])
            assert not BT.tim_cum_tu(v["noi"] + " " + v["chu"], cam + hk["hook_sao"]), v
            assert " / " in v["chu"]
            for a, b in (("hinh", "noi"), ("noi", "chu"), ("hinh", "chu")):
                assert BT.giong_nhau(v[a], v[b]) < rb["kiem_tra_may"]["hook_giong_nhau"], (c["ma"], a, b)


def test_giong_noi_va_giu_chan_co_trang_thai(tv):
    gn = tv["giong_noi"]
    for muc in ("xung_ho", "do_dai_cau", "tu_nen_dung", "tu_tranh", "cach_noi_so"):
        assert gn[muc]["trang_thai"] in TRANG_THAI, muc
    assert all(x["tu"] and x["thay"] for x in gn["tu_tranh"]["danh_sach"])
    kt = tv["giu_chan"]["ky_thuat"]
    assert len(kt) >= 6 and all(k["trang_thai"] in TRANG_THAI and k["cach_dung"] for k in kt)


# ---------------------------------------------------------------- kịch bản mẫu
def _mau() -> list[tuple[Path, dict]]:
    return [(f, yaml.safe_load(f.read_text(encoding="utf-8"))) for f in sorted((KENH / "kich-ban-mau").glob("*.yaml"))]


def _ke_hoach_tu_mau(m: dict) -> dict:
    doan = []
    for d in m["doan"]:
        the = None
        if d["the"]:
            a, b = d["the"].split(" / ", 1)
            the = {"dong1": a, "dong2": b}
        doan.append({"id": d["id"], "vai": d["vai"], "loi": d["loi"], "the": the, "nguon_ids": []})
    return {"doan": doan}


def test_moi_dinh_dang_co_dung_mot_kich_ban_mau(tv):
    dd = {d["ma"] for d in tv["dinh_dang"]["dinh_dang"]}
    ma = [m["ma_dinh_dang"] for _, m in _mau()]
    assert sorted(ma) == sorted(dd)
    for f, m in _mau():
        assert f.stem == m["ma_dinh_dang"]


@pytest.mark.parametrize("f,m", _mau(), ids=lambda x: x.stem if isinstance(x, Path) else "")
def test_kich_ban_mau_qua_may_kiem(f, m, tv, rb, brand_that):
    assert m["trang_thai"] in {"cho_duyet", "da_duyet"} and m["ngay_cap_nhat"]
    assert m["cong_thuc_hook"] in BT.ma_cong_thuc(tv)
    assert m["vi_sao_hay"] and m["giong"] in {"may", "thay"}
    kh = _ke_hoach_tu_mau(m)
    km = BT.kiem_may(kh, brand_that, rb, tv, cau_truc=False)
    assert not km.chan and not km.tran, (km.chan, km.tran)
    doan = kh["doan"]
    assert [d["id"] for d in doan] == [f"s{i}" for i in range(1, len(doan) + 1)]
    assert doan[0]["vai"] == "hook" and doan[-1]["vai"] == "cta" and doan[-2]["vai"] == "chot"
    assert doan[-1]["loi"] in brand_that["cta"] and doan[-1]["the"] is None
    assert m["hook"]["noi"] == doan[0]["loi"] and m["hook"]["chu"] == m["doan"][0]["the"]
    for d in doan[:-1]:
        assert len(d["the"]["dong1"]) <= 22 and d["the"]["dong1"] == d["the"]["dong1"].upper(), d["id"]
        assert len(d["the"]["dong2"]) <= 34, d["id"]
        # repo công khai: không học phí, không số tiền (số liệu bán hàng để ô [chờ anh xác nhận])
        assert not re.search(r"\d{1,3}(?:[.,]\d{3})+|\d+\s*(?:triệu|nghìn|đồng|đ)\b", d["loi"]), d["id"]
    lo, hi = SX["khung_hinh"]["thoi_luong_giay"]
    tong = sum(giay_uoc_luong(d["loi"], SX["am_tiet_moi_giay"]) for d in doan) + 0.3 * (len(doan) - 1) + 1.5
    assert lo <= tong <= hi, f"{tong:.1f}s"


# ---------------------------------------------------------------- máy kiểm chữ
def kich_ban(**kw) -> dict:
    hook = {"cong_thuc": "goi-dung-nguoi", "hinh_0_3s": "Ngã tư nhỏ ở quê, hai xe máy cùng đến",
            "cau_noi": "Ngã tư không đèn, ai đi trước?", "chu_man_hinh": "NGÃ TƯ / AI ĐI TRƯỚC?"}
    pa = [dict(hook, cong_thuc=c, cau_noi=f"Câu hook số {i}", chu_man_hinh=f"CHỮ {i} / dòng hai khác hẳn")
          for i, c in enumerate(("hoi-dung-noi-lo", "noi-nguoc", "con-so-cu-the", "tinh-huong-quen"), start=2)]
    kb = {"nhom_doi_tuong": "n1", "noi_lo": "Sợ bị phạt", "nguon_noi_lo": "doi_tuong", "dinh_dang": "luat-hoi-nhanh-dap-dung",
          "goc_ke": ["Kể theo tình huống đi đường", "Kể theo câu đố trái phải", "Kể theo lỗi thi sa hình"],
          "goc_chon": 1, "ly_do_goc": "Hợp nhóm n1 nhất", "hook_chon": hook, "ly_do_hook": "Gọi đúng tình huống",
          "phuong_an_hook": pa, "ban_1": [{"id": "s1", "loi": "Bản 1"}], "sua_ban_2": ["s2: tách câu"]}
    kb.update(kw)
    return kb


def kh_moi(**kw) -> dict:
    kh = ke_hoach()
    kh["kich_ban"] = kich_ban()
    kh.update(kw)
    return kh


def km_cua(kh, tv, rb, brand=BRAND, cau_truc=True):
    return BT.kiem_may(kh, brand, rb, tv, cau_truc=cau_truc)


def test_ke_hoach_co_kich_ban_hop_schema_va_qua_may_kiem(tv, rb):
    from may_reels.dung.ke_hoach import kiem_tra
    kh = kh_moi()
    assert kiem_tra(kh, BRAND, SX)[0] == []
    km = km_cua(kh, tv, rb)
    assert km.chan == [], km.chan
    assert km.do["cong_thuc_hook"] == "goi-dung-nguoi"


def test_ke_hoach_cu_khong_kich_ban_van_hop_schema():
    from may_reels.dung.ke_hoach import kiem_tra
    assert kiem_tra(ke_hoach(), BRAND, SX)[0] == []


@pytest.mark.parametrize("sua,tim", [
    (lambda k: k.pop("kich_ban"), "thiếu phần kich_ban"),
    (lambda k: k["kich_ban"]["phuong_an_hook"].pop(), "đúng 5 hook"),
    (lambda k: k["kich_ban"]["phuong_an_hook"][0].update(cong_thuc="goi-dung-nguoi"), "5 công thức khác nhau"),
    (lambda k: k["kich_ban"]["phuong_an_hook"][0].update(cong_thuc="khong-co"), "không có trong hook.yaml"),
    (lambda k: k["kich_ban"]["hook_chon"].update(cau_noi="Câu khác"), "trùng nguyên văn"),
    (lambda k: k["kich_ban"]["hook_chon"].update(chu_man_hinh="CHỮ KHÁC / hẳn"), "thẻ chữ của s1"),
    (lambda k: k["kich_ban"].update(goc_ke=["a b c d e", "f g h i j"]), "3 góc kể"),
    (lambda k: k["kich_ban"].update(nhom_doi_tuong="n9"), "doi-tuong.yaml"),
    (lambda k: k["kich_ban"].update(dinh_dang="khong-co"), "dinh-dang.yaml"),
    (lambda k: k["kich_ban"].update(ban_1=[{"id": "s99", "loi": "x"}]), "ban_1"),
    (lambda k: k["doan"][1].update(loi="Học ở đây bao đỗ nhé."), "cụm từ cấm"),
])
def test_may_kiem_chan(sua, tim, tv, rb):
    kh = kh_moi()
    sua(kh)
    km = km_cua(kh, tv, rb)
    assert any(tim in x for x in km.chan), km.chan


def test_may_kiem_tran_hook_dai_cau_dai_van_ai_tu_tranh(tv, rb, brand_that):
    kh = kh_moi()
    kh["doan"][0]["loi"] = "Có bằng A1 lái xe 150 phân khối được không câu trả lời là tùy năm cấp"
    kh["kich_ban"]["hook_chon"]["cau_noi"] = kh["doan"][0]["loi"]
    kh["doan"][1]["loi"] = ("Không phải xe to được đi trước, mà là xe đến từ bên phải của bạn. Người tham gia giao thông "
                            "phải tuân thủ, đối với phương tiện thì cũng vậy.")
    kh["doan"][2]["loi"] = ("Khoản 2 Điều 22 ghi: nơi giao nhau không có báo hiệu đi theo vòng xuyến, phương tiện phải "
                            "nhường đường cho xe đi đến từ bên phải theo đúng quy định của luật giao thông đường bộ.")
    km = km_cua(kh, tv, rb, brand=brand_that)
    assert {"hook_dai", "van_ai", "tu_tranh", "cau_dai"} <= set(km.tran), km.tran
    assert all("s3" not in x for x in km.tran.get("van_ai", []) + km.tran.get("tu_tranh", []))  # câu trích luật không dò
    assert any("s3" in x for x in km.tran["cau_dai"])


def test_may_kiem_hook_ba_phan_lap(tv, rb):
    kh = kh_moi()
    kh["kich_ban"]["hook_chon"]["hinh_0_3s"] = "Ngã tư không đèn, ai đi trước"
    assert "hook_lap" in km_cua(kh, tv, rb).tran


def test_cau_sao_cho_duyet_va_hook_sao(tv, rb, brand_that):
    kh = kh_moi()
    kh["doan"][0]["loi"] = "Dừng lướt, ngã tư không đèn ai đi trước?"
    kh["kich_ban"]["hook_chon"]["cau_noi"] = kh["doan"][0]["loi"]
    kh["doan"][4]["loi"] = "Nhớ ba điều này là qua ngã tư nhanh chóng và an toàn hơn."
    km = km_cua(kh, tv, rb, brand=brand_that)
    assert "hook_sao" in km.tran and "cau_sao" in km.tran


def test_tinh_diem_ap_tran_va_chan_ve_0(rb):
    agent = {m: {"diem": t["trong_so"], "ly_do": "tốt"} for m, t in rb["tieu_chi"].items()}
    agent["cu_the"] = {"diem": 999, "ly_do": "quá"}
    del agent["cau_chot"]
    km = BT.KiemMay(tran={"cau_dai": ["s3: 31 âm tiết"]})
    tc, tong = BT.tinh_diem(rb, agent, km)
    d = {t["ma"]: t for t in tc}
    assert d["cu_the"]["diem"] == rb["tieu_chi"]["cu_the"]["trong_so"]
    assert d["cau_chot"]["diem"] == 0 and "không chấm" in d["cau_chot"]["ly_do"]
    assert d["mot_y_cau_ngan"]["diem"] == rb["tran"]["cau_dai"]["toi_da"] and d["mot_y_cau_ngan"]["tran"]
    assert tong == 100 - rb["tieu_chi"]["cau_chot"]["trong_so"] - (rb["tieu_chi"]["mot_y_cau_ngan"]["trong_so"]
                                                                  - rb["tran"]["cau_dai"]["toi_da"])
    _, tong_chan = BT.tinh_diem(rb, agent, BT.KiemMay(chan=["cụm từ cấm"]))
    assert tong_chan == 0


# ---------------------------------------------------------------- biên tập: một lần (agent giả)
@pytest.fixture()
def repo_bt(tmp_path):
    goc = tmp_path / "repo"
    b = goc / "brand" / "kenhthu"
    b.mkdir(parents=True)
    for f in THU_VIEN:
        shutil.copyfile(KENH / f, b / f)
    shutil.copyfile(KENH / "doi-tuong.mau.yaml", b / "doi-tuong.mau.yaml")
    (b / "brand.json").write_text(json.dumps(BRAND, ensure_ascii=False), encoding="utf-8")
    (b / "san-xuat.yaml").write_text(yaml.safe_dump(SX, allow_unicode=True), encoding="utf-8")
    (goc / "projects").mkdir()
    return goc


def agent_bien_tap(goi: list, diem: dict | None = None, goi_y=("s3: tách câu",)):
    def ham(prompt, *, du_an, goc):
        goi.append((prompt, du_an))
        rb = BT.doc_rubric_kb("kenhthu", goc)
        tc = {m: {"diem": (diem or {}).get(m, t["trong_so"] - 1), "ly_do": "bằng chứng"} for m, t in rb["tieu_chi"].items()}
        (du_an / "bien_tap" / "diem.json").write_text(json.dumps({"tieu_chi": tc, "goi_y_sua": list(goi_y)},
                                                                 ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 2000, "total_cost_usd": 0.05}
    return ham


def test_bien_tap_dau_vao_khong_co_lap_luan_nguoi_viet(repo_bt):
    P = repo_bt / "projects" / "kt-001-cd-a"
    P.mkdir()
    kh = kh_moi()
    kh["kich_ban"]["ly_do_goc"] = "LẬP LUẬN BÍ MẬT GÓC"
    kh["kich_ban"]["ly_do_hook"] = "LẬP LUẬN BÍ MẬT HOOK"
    kh["kich_ban"]["goc_ke"] = ["GÓC KỂ BÍ MẬT 1", "GÓC KỂ BÍ MẬT 2", "GÓC KỂ BÍ MẬT 3"]
    kh["kich_ban"]["sua_ban_2"] = ["SỬA BẢN 2 BÍ MẬT"]
    kh["kich_ban"]["ban_1"] = [{"id": "s1", "loi": "BẢN 1 BÍ MẬT"}]
    kh["quyet_dinh"] = [{"category": "x", "subject": "y", "selected": "QUYẾT ĐỊNH BÍ MẬT", "reason": "z"}]
    (P / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
    goi = []
    kq = BT.bien_tap(P, goc=repo_bt, agent=agent_bien_tap(goi), log=lambda s: None)
    dv = (P / "bien_tap" / "dau_vao.json").read_text(encoding="utf-8")
    assert "BÍ MẬT" not in dv and "Câu hook số 2" not in dv   # cả 4 phương án hook
    d = json.loads(dv)
    assert d["kich_ban"]["hook"]["cau_noi"] == kh["doan"][0]["loi"] and d["nhom_doi_tuong"]["ma"] == "n1"
    assert d["rubric"].keys() == BT.doc_rubric_kb("kenhthu", repo_bt)["tieu_chi"].keys()
    assert len(goi) == 1 and "bien_tap/dau_vao.json" in goi[0][0]
    # 10 tiêu chí x (tối đa - 1) = 90, trừ trần "câu dài" của s2 (dài cố ý trong ke_hoach() mẫu): 9 -> 4
    assert "cau_dai" in json.loads((P / "diem_kich_ban.json").read_text(encoding="utf-8"))["kiem_may"]
    assert kq.diem == 85 and kq.dat and kq.cong_thuc_hook == "goi-dung-nguoi" and kq.goi_y_sua == ["s3: tách câu"]
    assert kq.so_luot_agent == 1 and kq.chi_phi_agent_usd == pytest.approx(0.05)
    assert json.loads((P / "diem_kich_ban.json").read_text(encoding="utf-8"))["diem_kich_ban"] == 85
    assert (P / "bien_tap" / "vong-0.json").is_file()
    BT.bien_tap(P, goc=repo_bt, agent=agent_bien_tap(goi), log=lambda s: None)
    assert (P / "bien_tap" / "vong-1.json").is_file()


def test_bien_tap_chan_khong_goi_agent(repo_bt):
    P = repo_bt / "projects" / "kt-001-cd-a"
    P.mkdir()
    kh = kh_moi()
    del kh["kich_ban"]
    (P / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
    goi = []
    kq = BT.bien_tap(P, goc=repo_bt, agent=agent_bien_tap(goi), log=lambda s: None)
    assert goi == [] and kq.diem == 0 and not kq.dat and "thiếu phần kich_ban" in kq.phan_hoi()


def test_agent_bien_tap_chi_doc_duoc_hai_file(repo_bt, monkeypatch):
    lenh = {}

    class R:
        returncode, stdout, stderr = 0, '{"result": "ok"}', ""

    def chay(cmd, **kw):
        lenh["cmd"] = cmd
        return R()
    monkeypatch.setattr("may_reels.san_xuat.shutil.which", lambda x: "claude")
    monkeypatch.setattr("may_reels.san_xuat.subprocess.run", chay)
    P = repo_bt / "projects" / "kt-001-cd-a"
    P.mkdir()
    BT.goi_agent_bien_tap("x", du_an=P, goc=repo_bt)
    cmd = lenh["cmd"]
    cong_cu = cmd[cmd.index("--allowed-tools") + 1].split(" ")
    assert sorted(cong_cu) == sorted(["Read(./skills/may-reels/bien-tap.md)",
                                      "Read(./projects/kt-001-cd-a/bien_tap/dau_vao.json)",
                                      "Write(./projects/kt-001-cd-a/bien_tap/diem.json)",
                                      "Edit(./projects/kt-001-cd-a/bien_tap/diem.json)"])


# ---------------------------------------------------------------- sản xuất: biên tập trước khi dựng
def bien_tap_lan_luot(diem: list[int], goi: list):
    def ham(P, *, goc, log=None):
        d = diem.pop(0)
        goi.append((P.name, d))
        kq = BT.KetQuaBienTap(P.name, diem=d, nguong=75, cong_thuc_hook="noi-nguoc", giay_agent=3, so_luot_agent=1)
        kq.tieu_chi = [{"ma": "cu_the", "ten": "Cụ thể", "toi_da": 10, "diem": 2, "ly_do": "chung chung"}]
        kq.goi_y_sua = ["s3: nói tên lỗi"]
        return kq
    return ham


def agent_viet(goi: list):
    def ham(prompt, *, du_an, goc):
        goi.append(json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8")))
        kh = kh_moi(ma_video=du_an.name, ma_chu_de=du_an.name.split("-", 2)[2])
        (du_an / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 1000}
    return ham


def _co_rubric(goc):
    shutil.copyfile(KENH / "rubric-kich-ban.yaml", goc / "brand/kenhthu/rubric-kich-ban.yaml")


def test_san_xuat_bien_tap_duoi_nguong_tra_ve_nguoi_viet_roi_dung(nha_may):
    goc, bang = nha_may
    _co_rubric(goc)
    viet, bt = [], []
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_viet(viet), bien_tap=bien_tap_lan_luot([60, 82], bt),
                  dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})]}), log=lambda s: None)
    k = ds[0]
    assert k.trang_thai == "cho_duyet" and k.diem_kich_ban == 82 and k.vong_kich_ban == 1
    assert [d for _, d in bt] == [60, 82] and len(viet) == 2
    assert viet[1]["phan_hoi"].startswith("Điểm kịch bản 60 < 75") and "s3: nói tên lỗi" in viet[1]["phan_hoi"]
    assert "dinh_dang" not in viet[0] or viet[0]["dinh_dang"]["ma"]          # kênh thử không có dinh-dang.yaml
    assert viet[0]["cau_hoi_khach"] == []
    hang = S.doc_dong(bang, HANG_CHO)
    assert {d["diem_kich_ban"] for d in hang} == {"82"} and {d["cong_thuc_hook"] for d in hang} == {"noi-nguoc"}
    assert not any("Kịch bản dưới ngưỡng" in d["canh_bao"] for d in hang)
    nk = [d for d in S.doc_dong(bang, NHAT_KY) if d["buoc"] == "bien_tap"]
    assert [d["ket_qua"] for d in nk] == ["loi", "ok"]
    assert k.so_luot_agent == 2 + 2   # 2 lượt viết + 2 lượt biên tập (cham_gia không tính lượt)


def test_san_xuat_het_vong_bien_tap_van_dung_kem_canh_bao(nha_may):
    goc, bang = nha_may
    _co_rubric(goc)
    viet, bt = [], []
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_viet(viet), bien_tap=bien_tap_lan_luot([50, 55, 60], bt),
                  dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})]}), log=lambda s: None)
    k = ds[0]
    assert k.trang_thai == "cho_duyet" and k.diem_kich_ban == 60 and len(viet) == 3 and len(bt) == 3
    hang = S.doc_dong(bang, HANG_CHO)
    assert all(d["canh_bao"].startswith("Kịch bản dưới ngưỡng (60/75)") for d in hang)


def test_san_xuat_khong_co_rubric_kich_ban_thi_bo_qua(nha_may):
    goc, bang = nha_may
    bt = []
    ds = san_xuat(bang, "kenhthu", 1, goc=goc, agent=agent_viet([]), bien_tap=bien_tap_lan_luot([10], bt),
                  dung=dung_gia({"kt-005-cd-a": [(MA_OK, {"diem_qa": 90})]}), log=lambda s: None)
    assert ds[0].trang_thai == "cho_duyet" and bt == [] and ds[0].diem_kich_ban is None
    assert {d["diem_kich_ban"] for d in S.doc_dong(bang, HANG_CHO)} == {""}


# ---------------------------------------------------------------- so sánh trước sau
def test_so_sanh_viet_lai_chi_ke_hoach_va_bao_cao(repo_bt):
    from may_reels.so_sanh_kich_ban import THU_MUC, so_sanh
    goc = repo_bt
    P = goc / "projects" / "kt-005-cd-a"
    P.mkdir()
    cu = ke_hoach(ma_video="kt-005-cd-a")
    (P / "ke_hoach.json").write_text(json.dumps(cu, ensure_ascii=False), encoding="utf-8")
    (P / "reel_job.json").write_text(json.dumps({"ma_video": "kt-005-cd-a", "kenh": "kenhthu", "ma_chu_de": "cd-a",
                                                 "chu_de": "A?"}), encoding="utf-8")
    truoc = sorted(p.name for p in P.iterdir())
    viet = []

    def agent(prompt, *, du_an, goc):
        if "bien-tap.md" in prompt:
            return agent_bien_tap([])(prompt, du_an=du_an, goc=goc)
        viet.append(json.loads((du_an / "yeu_cau.json").read_text(encoding="utf-8")))
        kh = kh_moi(ma_video="kt-005-cd-a")
        kh["doan"][4]["loi"] = "Có biển thì nhường bên trái, không biển thì bên phải."
        (du_an / "ke_hoach.json").write_text(json.dumps(kh, ensure_ascii=False), encoding="utf-8")
        return {"result": "ok", "duration_ms": 5000, "total_cost_usd": 0.3}

    import may_reels.bien_tap as mod
    ds = so_sanh(["kt-005-cd-a"], goc=goc, agent=agent,
                 bien_tap=lambda p, goc, log, cau_truc=True: mod.bien_tap(p, goc=goc, log=log, cau_truc=cau_truc,
                                                                         agent=agent_bien_tap([])),
                 log=lambda s: None)
    k = ds[0]
    assert not k.loi and k.cu.diem == 85 and k.moi.diem == 85 and k.loi_ke_hoach == []
    assert viet[0]["nguon_luat_da_mo"] == cu["nguon_luat"] and viet[0]["che_do"].startswith("so_sanh")
    assert sorted(p.name for p in P.iterdir()) == truoc            # không đụng dự án gốc
    bc = (goc / THU_MUC / "BAO-CAO.md").read_text(encoding="utf-8")
    assert "Nhớ ba điều này" in bc and "Có biển thì nhường bên trái" in bc and "**chọn**" in bc


def test_ke_hoach_cu_tu_script_json(tmp_path):
    from may_reels.so_sanh_kich_ban import ke_hoach_cu
    P = tmp_path / "p"
    (P / "artifacts").mkdir(parents=True)
    secs = [{"id": f"s{i}", "text": f"Lời {i}.", **({"source_ref": "Luật X, Điều 1 — https://x.vn"} if i in (2, 3) else {})}
            for i in range(1, 6)]
    (P / "artifacts" / "script.json").write_text(json.dumps({"title": "T", "sections": secs}), encoding="utf-8")
    kh = ke_hoach_cu(P, {"ma_video": "m", "kenh": "k", "ma_chu_de": "c"}, SX, {"tru_cot": "1 phút luật mới"})
    assert [d["vai"] for d in kh["doan"]] == ["hook", "than", "than", "chot", "cta"]
    assert kh["khung_nhip"] == "mot-phut-luat-moi" and len(kh["nguon_luat"]) == 1
    assert kh["nguon_luat"][0]["link"] == "https://x.vn" and kh["doan"][1]["nguon_ids"] == ["n1"]


def _du_an_so_sanh(goc, ma):
    P = goc / "projects" / ma
    P.mkdir()
    (P / "ke_hoach.json").write_text(json.dumps(ke_hoach(ma_video=ma), ensure_ascii=False), encoding="utf-8")
    (P / "reel_job.json").write_text(json.dumps({"ma_video": ma, "kenh": "kenhthu", "ma_chu_de": "cd-a", "chu_de": "A?"}),
                                     encoding="utf-8")


def test_so_sanh_bien_tap_loi_ghi_loi_thu_lai_1_lan_va_chay_tiep(repo_bt):
    """Biên tập hỏng: báo cáo ghi "lỗi" (không phải điểm 0), thử lại đúng 1 lần, video sau vẫn chạy."""
    from may_reels.so_sanh_kich_ban import THU_MUC, so_sanh
    import may_reels.bien_tap as mod
    goc = repo_bt
    for ma in ("kt-006-cd-a", "kt-007-cd-a"):
        _du_an_so_sanh(goc, ma)
    goi_bt = []

    def bt_agent(prompt, *, du_an, goc):
        goi_bt.append(du_an)
        if "kt-006" in str(du_an):
            return {"is_error": True, "result": "Connection refused", "duration_ms": 100}
        return agent_bien_tap([])(prompt, du_an=du_an, goc=goc)

    def agent(prompt, *, du_an, goc):
        (du_an / "ke_hoach.json").write_text(json.dumps(kh_moi(ma_video=du_an.parent.name), ensure_ascii=False),
                                             encoding="utf-8")
        return {"result": "ok", "duration_ms": 1000, "total_cost_usd": 0.1}

    ds = so_sanh(["kt-006-cd-a", "kt-007-cd-a"], goc=goc, agent=agent,
                 bien_tap=lambda p, goc, log, cau_truc=True: mod.bien_tap(p, goc=goc, log=log, cau_truc=cau_truc,
                                                                         agent=bt_agent),
                 log=lambda s: None)
    loi, ok = ds
    assert sum("kt-006" in str(p) for p in goi_bt) == 4          # cũ 2 lần + mới 2 lần, không hơn
    assert loi.moi is None and "biên tập bản cũ lỗi" in loi.loi and "biên tập bản mới lỗi" in loi.loi
    assert not ok.loi and ok.cu.diem == 85 and ok.moi.diem == 85
    bc = (goc / THU_MUC / "BAO-CAO.md").read_text(encoding="utf-8")
    assert "| kt-006-cd-a | lỗi | lỗi |" in bc and "| kt-007-cd-a | 85 | 85 |" in bc
    assert "Connection refused" in bc