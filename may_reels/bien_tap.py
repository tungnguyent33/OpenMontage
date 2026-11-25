"""Biên tập kịch bản TRƯỚC khi sinh giọng và dựng (C2b, 2026-11-21).

Luồng một lần biên tập (bien_tap):
  1. Python kiểm chữ (kiem_may): âm tiết hook, câu dài nhất, cụm từ cấm, câu sáo, hook sáo, kiểu câu văn AI, từ tránh,
     và cấu trúc phần `kich_ban` của ke_hoach.json (3 góc kể, 5 hook theo 5 công thức khác nhau, hook ba phần).
     Lỗi chặn -> không gọi biên tập, điểm 0, trả về người viết.
  2. Ghi bien_tap/dau_vao.json: CHỈ kịch bản (lời, thẻ chữ, hook ba phần, nguồn đã trích), chủ đề, nhóm đối tượng,
     rubric kịch bản và kết quả máy kiểm. KHÔNG có lập luận của người viết (góc kể, lý do chọn, phương án hook,
     quyet_dinh). Biên tập (claude -p, skills/may-reels/bien-tap.md) chỉ được Read đúng hai file: skill và dau_vao.json.
  3. Python cộng điểm theo brand/<kenh>/rubric-kich-ban.yaml, áp trần theo lỗi máy đo được, so ngưỡng.
     Ghi bien_tap/vong-<n>.json và diem_kich_ban.json (bản mới nhất) trong thư mục dự án.

Mọi trọng số, ngưỡng và danh sách đọc từ brand/<kenh>/ (rubric-kich-ban.yaml, hook.yaml, giong-noi.yaml,
dinh-dang.yaml, doi-tuong.yaml); file này không viết cứng giá trị riêng của kênh.
"""
from __future__ import annotations

import difflib
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from may_reels.cham_diem import bo_dau, tim_cum_tu
from may_reels.giong import am_tiet, chuan_hoa_doc

GOC = Path(__file__).resolve().parent.parent
SKILL_BIEN_TAP = "skills/may-reels/bien-tap.md"
THU_MUC = "bien_tap"
CANH_BAO_DUOI_NGUONG = "Kịch bản dưới ngưỡng"
CANH_BAO_LOI_BIEN_TAP = "Biên tập lỗi, chưa có điểm kịch bản"


class LoiRubricKichBan(RuntimeError):
    pass


# ---------------------------------------------------------------- đọc cấu hình kênh
def _yaml(p: Path) -> dict:
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.is_file() else {}


def co_rubric(kenh: str, goc: Path = GOC) -> bool:
    return (goc / "brand" / kenh / "rubric-kich-ban.yaml").is_file()


def doc_rubric_kb(kenh: str, goc: Path = GOC) -> dict:
    p = goc / "brand" / kenh / "rubric-kich-ban.yaml"
    if not p.is_file():
        raise LoiRubricKichBan(f"Chưa có brand/{kenh}/rubric-kich-ban.yaml")
    rb = _yaml(p)
    tong = sum(float(v.get("trong_so", 0)) for v in (rb.get("tieu_chi") or {}).values())
    if abs(tong - 100) > 1e-6:
        raise LoiRubricKichBan(f"rubric-kich-ban.yaml: tổng trọng số = {tong}, phải bằng 100")
    for ma, t in (rb.get("tran") or {}).items():
        if t.get("tieu_chi") not in (rb.get("tieu_chi") or {}):
            raise LoiRubricKichBan(f"rubric-kich-ban.yaml: tran.{ma} trỏ tới tiêu chí không có: {t.get('tieu_chi')}")
    return rb


def doc_thu_vien(kenh: str, goc: Path = GOC) -> dict:
    """hook.yaml, giong-noi.yaml, giu-chan.yaml, dinh-dang.yaml, doi-tuong.yaml (bản thật, thiếu thì bản mẫu)."""
    b = goc / "brand" / kenh
    dt = b / "doi-tuong.yaml"
    return {"hook": _yaml(b / "hook.yaml"), "giong_noi": _yaml(b / "giong-noi.yaml"), "giu_chan": _yaml(b / "giu-chan.yaml"),
            "dinh_dang": _yaml(b / "dinh-dang.yaml"),
            "doi_tuong": _yaml(dt if dt.is_file() else b / "doi-tuong.mau.yaml")}


def ma_cong_thuc(tv: dict) -> set[str]:
    return {c.get("ma") for c in (tv.get("hook") or {}).get("cong_thuc") or [] if c.get("ma")}


def dinh_dang_cua(tv: dict, chu_de: dict, khung_nhip: str | None) -> dict | None:
    """Định dạng (dinh-dang.yaml) của chủ đề: theo mã định dạng của chủ đề, rồi theo khung nhịp (định dạng luật)."""
    ds = (tv.get("dinh_dang") or {}).get("dinh_dang") or []
    for d in ds:
        if d.get("ma") and d.get("ma") == chu_de.get("dinh_dang"):
            return d
    for d in ds:
        if khung_nhip and d.get("khung_nhip") == khung_nhip:
            return d
    return None


def nhom_cua(tv: dict, ma: str | None) -> dict | None:
    return next((n for n in (tv.get("doi_tuong") or {}).get("nhom") or [] if n.get("ma") == ma), None)


# ---------------------------------------------------------------- văn bản
def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def tach_cau(s: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<=[.?!])\s+", _nfc(s).strip()) if c.strip()]


def so_am_tiet(s: str) -> int:
    return len(am_tiet(chuan_hoa_doc(s)))


def la_trich_luat(cau: str) -> bool:
    """Câu trích nguyên văn luật: không dò từ tránh / văn AI (lời luật không phải lời của kênh)."""
    c = _nfc(cau).casefold()
    return " ghi:" in f" {c}" or any(q in cau for q in ('"', "“", "”"))


def the_chu(d: dict) -> str:
    t = d.get("the") or {}
    return f"{t.get('dong1', '')} / {t.get('dong2', '')}" if t else ""


def _gon(s: str) -> str:
    return " ".join(re.findall(r"\w+", bo_dau(s)))


def giong_nhau(a: str, b: str) -> float:
    a, b = _gon(a), _gon(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _cau_sao(brand: dict, khoa: str) -> list[str]:
    return [c for c in ((brand.get("cam") or {}).get(khoa) or []) if c and "…" not in c and "..." not in c]


# ---------------------------------------------------------------- 1. máy kiểm
@dataclass
class KiemMay:
    chan: list[str] = field(default_factory=list)          # lỗi chặn: không gọi biên tập
    tran: dict[str, list[str]] = field(default_factory=dict)  # mã trần (rubric tran) -> bằng chứng
    canh_bao: list[str] = field(default_factory=list)
    do: dict = field(default_factory=dict)

    def them_tran(self, ma: str, bang_chung: str) -> None:
        self.tran.setdefault(ma, []).append(bang_chung)


def co_uu_dai_thuong_xuyen(ban_hang: dict | None) -> bool:
    """Kênh có ưu đãi thường xuyên đã xác nhận (ban-hang.yaml uu_dai thuong_xuyen: true)."""
    return any(isinstance(u, dict) and u.get("noi_dung") and u.get("thuong_xuyen") and u.get("trang_thai") == "da_xac_nhan"
               for u in (ban_hang or {}).get("uu_dai") or [])


def doc_ban_hang(kenh: str, goc: Path = GOC) -> dict | None:
    """ban-hang.yaml thật của kênh (chỉ có ở máy); không có thì None (không dùng bản mẫu thay)."""
    p = goc / "brand" / kenh / "ban-hang.yaml"
    return _yaml(p) if p.is_file() else None


def kiem_may(kh: dict, brand: dict, rb: dict, tv: dict, *, cau_truc: bool = True,
             ban_hang: dict | None = None) -> KiemMay:
    km = KiemMay()
    cfg = rb.get("kiem_tra_may") or {}
    doan = kh.get("doan") or []
    if not doan:
        km.chan.append("kế hoạch không có đoạn nào")
        return km
    noi_dung = [d for d in doan if d.get("vai") != "cta"]   # CTA là nguyên văn brand.json: không chấm câu chữ

    # Hook đọc trong 3 giây
    hook = doan[0].get("loi") or ""
    n_hook = so_am_tiet(hook)
    km.do["hook_am_tiet"] = n_hook
    if n_hook > int(cfg.get("hook_am_tiet_toi_da", 13)):
        km.them_tran("hook_dai", f"s1: {n_hook} âm tiết > {cfg.get('hook_am_tiet_toi_da', 13)}")

    # Câu dài nhất
    cau = [(d["id"], c, so_am_tiet(c)) for d in noi_dung for c in tach_cau(d.get("loi") or "")]
    if cau:
        dai = max(cau, key=lambda x: x[2])
        km.do["cau_dai_nhat"] = {"doan": dai[0], "cau": dai[1], "am_tiet": dai[2]}
        toi_da = int(cfg.get("cau_am_tiet_toi_da", 26))
        for i, c, n in cau:
            if n > toi_da:
                km.them_tran("cau_dai", f"{i}: {n} âm tiết > {toi_da}: {c[:80]}")

    # Cụm từ cấm, câu sáo (lời + thẻ chữ, cả CTA vì lời CTA cũng hiện)
    van_ban = [(d["id"], d.get("loi") or "") for d in doan] + [(d["id"] + ".the", the_chu(d)) for d in doan if d.get("the")]
    cam = [c for c in ((brand.get("cam") or {}).get("cum_tu_cam") or []) + ((brand.get("cam") or {}).get("cum_tu_cam_du_an") or [])]
    for noi, t in van_ban:
        for c in tim_cum_tu(t, cam):
            km.chan.append(f"{noi}: cụm từ cấm '{c}'")
        for c in tim_cum_tu(t, _cau_sao(brand, "cau_sao_da_chot")):
            km.chan.append(f"{noi}: câu sáo đã cấm '{c}'")
        for c in tim_cum_tu(t, _cau_sao(brand, "cau_sao_cho_duyet")):
            km.them_tran("cau_sao", f"{noi}: '{c}'")

    # Ưu đãi thường xuyên: không nói hạn chót, "sắp hết"
    ut = cfg.get("uu_dai_thuong_xuyen") or {}
    if co_uu_dai_thuong_xuyen(ban_hang) and ut.get("cum_gap_gap"):
        for d in doan:
            t = (d.get("loi") or "") + " . " + the_chu(d)
            if tim_cum_tu(t, ut.get("tu_nhan_biet") or []):
                for c in tim_cum_tu(t, ut["cum_gap_gap"]):
                    km.chan.append(f"{d['id']}: ưu đãi thường xuyên không có hạn, không nói '{c}'")

    # Hook sáo (câu nói đầu + chữ hook)
    hook_sao = [h for h in (tv.get("hook") or {}).get("hook_sao") or [] if h]
    for c in tim_cum_tu(hook + " " + the_chu(doan[0]), hook_sao):
        km.them_tran("hook_sao", f"s1: '{c}'")

    # Kiểu câu văn AI, từ tránh: chỉ lời của kênh (bỏ câu trích luật)
    mau = [(m.get("ma"), re.compile(m.get("mau", "(?!)"), re.I)) for m in cfg.get("mau_van_ai") or []]
    tu_tranh = [x.get("tu") for x in ((tv.get("giong_noi") or {}).get("tu_tranh") or {}).get("danh_sach") or [] if x.get("tu")]
    dem_tranh = []
    for noi, t in [(d["id"], d.get("loi") or "") for d in noi_dung] + [(d["id"] + ".the", the_chu(d)) for d in noi_dung if d.get("the")]:
        for c in tach_cau(t) or [t]:
            if la_trich_luat(c):
                continue
            cf = _nfc(c).casefold()
            for ma, rx in mau:
                if rx.search(cf):
                    km.them_tran("van_ai", f"{noi}: kiểu '{ma}': {c[:80]}")
            for x in tim_cum_tu(c, tu_tranh):
                dem_tranh.append(f"{noi}: '{x}'")
    if dem_tranh:
        km.canh_bao.append("Từ tránh: " + "; ".join(dem_tranh))
        if len(dem_tranh) >= int(cfg.get("tu_tranh_toi_da", 2)):
            for x in dem_tranh:
                km.them_tran("tu_tranh", x)

    if cau_truc:
        _kiem_cau_truc(kh, tv, cfg, km)
    return km


def _kiem_cau_truc(kh: dict, tv: dict, cfg: dict, km: KiemMay) -> None:
    kb = kh.get("kich_ban")
    if not kb:
        km.chan.append("thiếu phần kich_ban (góc kể, 5 hook, bản 1, sửa bản 2): viết theo skills/may-reels/bien-kich.md")
        return
    doan = kh["doan"]
    hooks = [kb.get("hook_chon") or {}] + list(kb.get("phuong_an_hook") or [])
    co = ma_cong_thuc(tv)
    ct = [h.get("cong_thuc") for h in hooks]
    km.do["cong_thuc_hook"] = ct[0]
    if len(hooks) != 5:
        km.chan.append(f"cần đúng 5 hook (1 chọn + 4 phương án), đang có {len(hooks)}")
    la = [c for c in ct if c not in co]
    if co and la:
        km.chan.append(f"công thức hook không có trong hook.yaml: {la}")
    if len(set(ct)) != len(ct):
        km.chan.append(f"5 hook phải theo 5 công thức khác nhau: {ct}")
    if len(kb.get("goc_ke") or []) != 3:
        km.chan.append("cần đúng 3 góc kể")
    if _nfc(hooks[0].get("cau_noi", "")).strip() != _nfc(doan[0].get("loi", "")).strip():
        km.chan.append("hook_chon.cau_noi phải trùng nguyên văn lời đoạn s1")
    if doan[0].get("the") and _gon(hooks[0].get("chu_man_hinh", "")) != _gon(the_chu(doan[0])):
        km.chan.append(f"hook_chon.chu_man_hinh phải là thẻ chữ của s1 dạng 'DÒNG 1 / dòng 2': {the_chu(doan[0])!r}")
    nguong = float(cfg.get("hook_giong_nhau", 0.8))
    for i, h in enumerate(hooks):
        phan = [("hình", h.get("hinh_0_3s", "")), ("câu nói", h.get("cau_noi", "")), ("chữ", h.get("chu_man_hinh", ""))]
        for a in range(3):
            for b in range(a + 1, 3):
                if giong_nhau(phan[a][1], phan[b][1]) >= nguong:
                    tin = f"hook {i + 1} ({h.get('cong_thuc')}): {phan[a][0]} lặp {phan[b][0]}"
                    (km.them_tran("hook_lap", tin) if i == 0 else km.canh_bao.append(tin))
    ids = {d["id"] for d in doan}
    thua = [x.get("id") for x in kb.get("ban_1") or [] if x.get("id") not in ids]
    if thua:
        km.chan.append(f"ban_1 có đoạn không tồn tại: {thua}")
    nhom = {n.get("ma") for n in (tv.get("doi_tuong") or {}).get("nhom") or []}
    if nhom and kb.get("nhom_doi_tuong") not in nhom | {"moi_nhom"}:
        km.chan.append(f"nhom_doi_tuong {kb.get('nhom_doi_tuong')!r} không có trong doi-tuong.yaml")
    dd = {d.get("ma") for d in (tv.get("dinh_dang") or {}).get("dinh_dang") or []}
    if dd and kb.get("dinh_dang") not in dd:
        km.chan.append(f"dinh_dang {kb.get('dinh_dang')!r} không có trong dinh-dang.yaml")


# ---------------------------------------------------------------- 2. đầu vào biên tập
def dau_vao(kh: dict, brand: dict, rb: dict, tv: dict, km: KiemMay) -> dict:
    """Đúng những gì biên tập được thấy. Không có goc_ke, ly_do_*, phuong_an_hook, ban_1, sua_ban_2, quyet_dinh."""
    kb = kh.get("kich_ban") or {}
    cd = next((c for c in brand.get("chu_de") or [] if c.get("ma") == kh.get("ma_chu_de")), {})
    s1 = kh["doan"][0]
    hc = kb.get("hook_chon") or {}
    dd = (next((d for d in (tv.get("dinh_dang") or {}).get("dinh_dang") or [] if d.get("ma") == kb.get("dinh_dang")), None)
          or dinh_dang_cua(tv, cd, kh.get("khung_nhip")) or {})
    gn = tv.get("giong_noi") or {}
    return {
        "ma_video": kh.get("ma_video"),
        "chu_de": {k: cd.get(k) for k in ("ma", "chu_de", "y_chinh", "nguon_doi_chieu")},
        "nhom_doi_tuong": nhom_cua(tv, kb.get("nhom_doi_tuong")) or kb.get("nhom_doi_tuong") or "chưa ghi",
        "noi_lo": kb.get("noi_lo") or "chưa ghi",
        "dinh_dang": {k: dd.get(k) for k in ("ma", "ten", "tang", "giong")},
        "kich_ban": {
            "tieu_de": kh.get("tieu_de"),
            "hook": {"hinh_0_3s": hc.get("hinh_0_3s") or ((s1.get("canh") or {}).get("mo_ta") or "chưa ghi"),
                     "cau_noi": s1.get("loi"), "chu_man_hinh": the_chu(s1)},
            "doan": [{"id": d["id"], "vai": d["vai"], "loi": d["loi"], "the": the_chu(d), "nguon_ids": d.get("nguon_ids") or []}
                     for d in kh["doan"]],
            "nguon_luat": [{k: n.get(k) for k in ("id", "ten_ngan", "dieu_khoan", "trich_nguyen_van")}
                           for n in kh.get("nguon_luat") or []],
        },
        "cta_cua_kenh": brand.get("cta") or [],
        "rubric": {m: {"ten": t.get("ten"), "toi_da": t.get("trong_so"), "mo_ta": t.get("mo_ta")}
                   for m, t in (rb.get("tieu_chi") or {}).items()},
        "kiem_tra_may": {"tran": {m: {"tieu_chi": (rb.get("tran") or {}).get(m, {}).get("tieu_chi"),
                                      "toi_da": (rb.get("tran") or {}).get(m, {}).get("toi_da"), "bang_chung": v}
                                  for m, v in km.tran.items()},
                         "canh_bao": km.canh_bao, "do": km.do},
        "giong_noi": {k: gn.get(k) for k in ("xung_ho", "do_dai_cau", "tu_tranh", "cach_noi_so")},
        "giu_chan": [{"ten": k.get("ten"), "cach_dung": k.get("cach_dung")} for k in (tv.get("giu_chan") or {}).get("ky_thuat") or []],
        "hook_sao": (tv.get("hook") or {}).get("hook_sao") or [],
        "cau_sao": _cau_sao(brand, "cau_sao_da_chot") + _cau_sao(brand, "cau_sao_cho_duyet"),
        "mau_van_ai": (rb.get("kiem_tra_may") or {}).get("mau_van_ai") or [],
    }


# ---------------------------------------------------------------- 3. điểm
@dataclass
class KetQuaBienTap:
    ma_video: str
    diem: int = 0
    nguong: int = 75
    chan: list[str] = field(default_factory=list)
    tieu_chi: list[dict] = field(default_factory=list)
    goi_y_sua: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    cong_thuc_hook: str = ""
    giay: float = 0.0
    giay_agent: float = 0.0
    so_luot_agent: int = 0
    chi_phi_agent_usd: float = 0.0
    loi_agent: str = ""          # biên tập (claude -p) hỏng: điểm 0 là điểm giả, không phải điểm kịch bản

    @property
    def dat(self) -> bool:
        return not self.chan and self.diem >= self.nguong

    def ly_do_tru(self) -> list[str]:
        mat = sorted((t for t in self.tieu_chi if t["diem"] < t["toi_da"]), key=lambda t: t["diem"] - t["toi_da"])
        return [f"{t['ten']} -{t['toi_da'] - t['diem']:g}: {t.get('ly_do', '')}" + (f" (trần máy: {t['tran']})" if t.get("tran") else "")
                for t in mat]

    def phan_hoi(self) -> str:
        """Gửi người viết ở vòng sửa kịch bản."""
        dong = [f"Điểm kịch bản {self.diem} < {self.nguong} (biên tập trước khi dựng). Đây là vòng sửa KỊCH BẢN: sửa lời "
                "và thẻ chữ theo các mục dưới, giữ cảnh, nguồn và caption trừ khi lời đổi buộc phải đổi theo."]
        if self.chan:
            dong += ["Lỗi chặn (máy kiểm):"] + [f"- {x}" for x in self.chan]
        lt = self.ly_do_tru()
        if lt:
            dong += ["Lý do trừ điểm, nặng nhất trước:"] + [f"- {x}" for x in lt]
        if self.goi_y_sua:
            dong += ["Gợi ý sửa của biên tập:"] + [f"- {x}" for x in self.goi_y_sua]
        return "\n".join(dong)


def tinh_diem(rb: dict, agent_tc: dict, km: KiemMay) -> tuple[list[dict], int]:
    tran_tc: dict[str, list[tuple[float, str]]] = {}
    for ma in km.tran:
        t = (rb.get("tran") or {}).get(ma)
        if t:
            tran_tc.setdefault(t["tieu_chi"], []).append((float(t["toi_da"]), t.get("ly_do", ma)))
    ra = []
    for ma, t in (rb.get("tieu_chi") or {}).items():
        toi_da = float(t.get("trong_so", 0))
        a = agent_tc.get(ma) if isinstance(agent_tc.get(ma), dict) else {}
        try:
            d = float(a.get("diem"))
        except (TypeError, ValueError):
            d, a = 0.0, {"ly_do": "biên tập không chấm tiêu chí này"}
        d = max(0.0, min(toi_da, d))
        muc = {"ma": ma, "ten": t.get("ten", ma), "toi_da": toi_da, "diem": d, "ly_do": str(a.get("ly_do", ""))[:300]}
        for tran, ly_do in tran_tc.get(ma, []):
            if d > tran:
                d = tran
                muc["diem"], muc["tran"] = d, ly_do
        ra.append(muc)
    tong = 0 if km.chan else int(round(sum(m["diem"] for m in ra)))
    return ra, tong


def goi_agent_bien_tap(prompt: str, *, du_an: Path, goc: Path = GOC) -> dict:
    from may_reels.san_xuat import goi_agent
    rel = du_an.relative_to(goc).as_posix()
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=(f"{THU_MUC}/diem.json",), web=False,
                     doc=(SKILL_BIEN_TAP, f"{rel}/{THU_MUC}/dau_vao.json"),
                     he_thong=("Bạn là BIÊN TẬP kịch bản cho Máy Reels, chạy KHÔNG TƯƠNG TÁC: không có người để hỏi. Chỉ làm "
                               f"theo {SKILL_BIEN_TAP}. Chỉ đọc {SKILL_BIEN_TAP} và {rel}/{THU_MUC}/dau_vao.json; chỉ ghi "
                               f"{rel}/{THU_MUC}/diem.json."))


def bien_tap(P: Path, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent_bien_tap,
             cau_truc: bool = True, log: Callable[[str], None] = print) -> KetQuaBienTap:
    """Biên tập ke_hoach.json trong thư mục P (dự án, hoặc thư mục so sánh). Không ném lỗi agent ra ngoài: agent hỏng
    thì điểm 0 kèm lý do, để luồng sản xuất quyết định."""
    from may_reels.dung.ke_hoach import doc_brand
    t0 = time.monotonic()
    kh = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
    kenh = kh["kenh"]
    brand, rb, tv = doc_brand(kenh, goc), doc_rubric_kb(kenh, goc), doc_thu_vien(kenh, goc)
    kq = KetQuaBienTap(kh.get("ma_video", P.name), nguong=int(rb.get("nguong", 75)))
    km = kiem_may(kh, brand, rb, tv, cau_truc=cau_truc, ban_hang=doc_ban_hang(kenh, goc))
    kq.chan, kq.canh_bao = list(km.chan), list(km.canh_bao)
    kq.cong_thuc_hook = ((kh.get("kich_ban") or {}).get("hook_chon") or {}).get("cong_thuc", "")
    bt = P / THU_MUC
    bt.mkdir(parents=True, exist_ok=True)
    (bt / "dau_vao.json").write_text(json.dumps(dau_vao(kh, brand, rb, tv, km), ensure_ascii=False, indent=1, default=str),
                                     encoding="utf-8")
    agent_tc: dict = {}
    if not km.chan:
        f = bt / "diem.json"
        f.unlink(missing_ok=True)
        rel = bt.relative_to(goc).as_posix()
        ra = agent(f"Đọc và làm đúng theo {SKILL_BIEN_TAP}. Đọc {rel}/dau_vao.json rồi ghi {rel}/diem.json.",
                   du_an=P, goc=goc)
        kq.so_luot_agent += 1
        kq.giay_agent += (ra.get("duration_ms") or 0) / 1000
        kq.chi_phi_agent_usd += float(ra.get("total_cost_usd") or 0)
        try:
            out = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        except ValueError:
            out = {}
        agent_tc = out.get("tieu_chi") or {}
        if isinstance(agent_tc, list):
            agent_tc = {x.get("ma"): x for x in agent_tc if isinstance(x, dict)}
        kq.goi_y_sua = [str(x)[:300] for x in out.get("goi_y_sua") or []][:8]
        if ra.get("is_error") or not agent_tc:
            kq.loi_agent = f"biên tập không ghi được diem.json: {str(ra.get('result'))[:200]}"
            kq.canh_bao.append(kq.loi_agent)
    kq.tieu_chi, kq.diem = tinh_diem(rb, agent_tc, km)
    kq.giay = round(time.monotonic() - t0, 1)
    ket = {"ma_video": kq.ma_video, "diem_kich_ban": kq.diem, "nguong": kq.nguong, "dat": kq.dat, "chan": kq.chan,
           "tieu_chi": kq.tieu_chi, "goi_y_sua": kq.goi_y_sua, "canh_bao": kq.canh_bao, "loi_agent": kq.loi_agent,
           "kiem_may": km.tran,
           "do": km.do, "cong_thuc_hook": kq.cong_thuc_hook, "rubric_phien_ban": rb.get("phien_ban"),
           "agent": {"so_luot": kq.so_luot_agent, "giay": round(kq.giay_agent, 1),
                     "chi_phi_usd": round(kq.chi_phi_agent_usd, 4)}, "giay": kq.giay}
    n = len(list(bt.glob("vong-*.json")))
    (bt / f"vong-{n}.json").write_text(json.dumps(ket, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (P / "diem_kich_ban.json").write_text(json.dumps(ket, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    log(f"  [{kq.ma_video}] kịch bản {kq.diem}/{kq.nguong}" + (f"; CHẶN: {'; '.join(kq.chan)[:200]}" if kq.chan else ""))
    return kq


def bien_tap_thu_lai(bien_tap_fn: Callable, P: Path, *, goc: Path = GOC, log: Callable[[str], None] = print,
                     **kw) -> KetQuaBienTap:
    """Gọi biên tập; biên tập hỏng (loi_agent) thì thử lại đúng 1 lần. Trả kết quả lần cuối, cộng dồn lượt, giây và
    chi phí của cả hai lần. Vẫn hỏng thì kết quả còn loi_agent: người gọi quyết (KHÔNG dùng điểm 0 của nó)."""
    kqb = bien_tap_fn(P, goc=goc, log=log, **kw)
    if not kqb.loi_agent:
        return kqb
    log(f"  biên tập lỗi, thử lại 1 lần: {kqb.loi_agent[:200]}")
    kqb2 = bien_tap_fn(P, goc=goc, log=log, **kw)
    for a in ("so_luot_agent", "giay_agent", "chi_phi_agent_usd"):
        setattr(kqb2, a, getattr(kqb2, a) + getattr(kqb, a))
    return kqb2
