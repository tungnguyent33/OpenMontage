"""So sánh kịch bản cũ và kịch bản viết lại bằng bộ biên kịch (C2b, việc 6).

`python -m may_reels bien-kich so-sanh --ma <mã video> [--ma ...]`

Mỗi mã video đã làm:
  1. Kịch bản cũ: projects/<ma>/ke_hoach.json (hoặc artifacts/script.json với dự án dựng tay trước khi có ke_hoach)
     chép sang projects/_may_reels/so-sanh/<ma>/cu/, chấm bằng đúng biên tập mới (không kiểm phần kich_ban vì bản cũ
     không có).
  2. Kịch bản mới: người viết (claude -p, san-xuat-khong-hoi.md + bien-kich.md) viết lại vào .../moi/ke_hoach.json,
     qua biên tập như lúc sản xuất (tối đa so_vong_sua vòng). Chỉ kế hoạch: KHÔNG sinh giọng, KHÔNG dựng, không ghi
     Sheet, không đụng projects/<ma>/.
  3. Báo cáo projects/_may_reels/so-sanh/BAO-CAO.md: lời cũ cạnh lời mới, 5 hook, điểm từng tiêu chí, lỗi kế hoạch
     (may_reels/dung/ke_hoach.kiem_tra), thời gian và chi phí thêm mỗi video.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from may_reels.san_xuat import GOC, KetQuaJob, _yeu_cau, goi_agent, prompt_viet, qua_bien_tap

THU_MUC = Path("projects") / "_may_reels" / "so-sanh"


def ke_hoach_cu(P: Path, job: dict, sx: dict, chu_de: dict) -> dict:
    f = P / "ke_hoach.json"
    if f.is_file():
        return json.loads(f.read_text(encoding="utf-8"))
    sc = json.loads((P / "artifacts" / "script.json").read_text(encoding="utf-8"))
    secs = sc.get("sections") or []
    n = len(secs)
    khung = next((k for k, v in (sx.get("khung_nhip") or {}).items() if v.get("tru_cot") == chu_de.get("tru_cot")), "")
    doan, nguon, ref = [], [], {}
    for i, s in enumerate(secs):
        ids = []
        if s.get("source_ref"):
            if s["source_ref"] not in ref:
                ref[s["source_ref"]] = f"n{len(ref) + 1}"
                van_ban, _, link = s["source_ref"].partition(" — ")
                nguon.append({"id": ref[s["source_ref"]], "van_ban": van_ban, "ten_ngan": van_ban[:40],
                              "dieu_khoan": van_ban.rsplit(",", 1)[-1].strip(), "link": link.strip(),
                              "ngay_mo": "", "trich_nguyen_van": ""})
            ids = [ref[s["source_ref"]]]
        vai = "hook" if i == 0 else "cta" if i == n - 1 else "chot" if i == n - 2 else "than"
        doan.append({"id": s.get("id") or f"s{i + 1}", "vai": vai, "loi": s.get("text", ""), "the": None,
                     "nguon_ids": ids, "canh": None})
    return {"phien_ban": 1, "ma_video": job["ma_video"], "kenh": job["kenh"], "ma_chu_de": job["ma_chu_de"],
            "tieu_de": sc.get("title") or job.get("chu_de", ""), "khung_nhip": khung, "nguon_luat": nguon, "doan": doan,
            "caption": {}, "thieu_canh": [], "quyet_dinh": [],
            "_ghi_chu": "Dựng lại từ artifacts/script.json (dự án dựng tay, chưa có ke_hoach.json): không có thẻ chữ."}


@dataclass
class KetQuaSoSanh:
    ma_video: str
    chu_de: str = ""
    cu: object = None
    moi: object = None
    kh_cu: dict = field(default_factory=dict)
    kh_moi: dict = field(default_factory=dict)
    loi_ke_hoach: list[str] = field(default_factory=list)
    giay_viet: float = 0.0
    usd_viet: float = 0.0
    giay_them: float = 0.0       # biên tập + vòng viết lại kịch bản: phần tốn thêm so với quy trình cũ
    usd_them: float = 0.0
    so_luot_them: int = 0
    vong: int = 0
    loi: str = ""


class LoiBienTap(RuntimeError):
    """Biên tập (claude -p) hỏng cả lần thử lại: không có điểm thật cho bản này."""


def _diem(kqb) -> str:
    """Điểm để in: 'lỗi' khi biên tập hỏng hoặc không chạy được, không bao giờ in điểm giả 0."""
    if kqb is None or getattr(kqb, "loi_agent", ""):
        return "lỗi"
    return str(kqb.diem)


def _bien_tap_1_lan_thu_lai(bien_tap: Callable, P: Path, *, goc: Path, log: Callable[[str], None], **kw):
    """Gọi biên tập; hỏng thì thử lại đúng 1 lần; vẫn hỏng thì ném LoiBienTap."""
    kqb = bien_tap(P, goc=goc, log=log, **kw)
    if not kqb.loi_agent:
        return kqb
    log(f"  biên tập lỗi, thử lại 1 lần: {kqb.loi_agent[:200]}")
    kqb2 = bien_tap(P, goc=goc, log=log, **kw)
    for a in ("so_luot_agent", "giay_agent", "chi_phi_agent_usd"):
        setattr(kqb2, a, getattr(kqb2, a) + getattr(kqb, a))
    if kqb2.loi_agent:
        raise LoiBienTap(kqb2.loi_agent)
    return kqb2


def so_sanh_mot(ma: str, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent, bien_tap: Callable | None = None,
                log: Callable[[str], None] = print) -> KetQuaSoSanh:
    from may_reels.bien_tap import bien_tap as bien_tap_that
    from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat, kiem_tra
    bien_tap = bien_tap or bien_tap_that
    P = goc / "projects" / ma
    job = json.loads((P / "reel_job.json").read_text(encoding="utf-8"))
    kenh = job["kenh"]
    brand, sx = doc_brand(kenh, goc), doc_san_xuat(kenh, goc)
    chu_de = next((c for c in brand.get("chu_de") or [] if c.get("ma") == job["ma_chu_de"]), {})
    kq = KetQuaSoSanh(ma, chu_de.get("chu_de") or job.get("chu_de", ""))
    S = goc / THU_MUC / ma
    cu, moi = S / "cu", S / "moi"
    for d in (cu, moi):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    kq.kh_cu = ke_hoach_cu(P, job, sx, chu_de)
    (cu / "ke_hoach.json").write_text(json.dumps(kq.kh_cu, ensure_ascii=False, indent=2), encoding="utf-8")
    loi: list[str] = []
    log(f"== {ma}: chấm kịch bản cũ")
    try:
        kq.cu = _bien_tap_1_lan_thu_lai(bien_tap, cu, goc=goc, log=log, cau_truc=False)
    except LoiBienTap as e:
        loi.append(f"biên tập bản cũ lỗi (đã thử lại 1 lần): {e}")

    them = {"che_do": "so_sanh: chỉ viết kế hoạch, không dựng",
            "nguon_luat_da_mo": [n for n in kq.kh_cu.get("nguon_luat") or [] if n.get("trich_nguyen_van")]}
    _yeu_cau(moi, job, chu_de, brand, sx, None, None, goc, them=them)
    for lan in range(2):  # người viết hỏng thì thử lại đúng 1 lần
        log(f"== {ma}: viết lại bằng bộ biên kịch" + (" (thử lại)" if lan else ""))
        ra = agent(prompt_viet(moi, goc), du_an=moi, goc=goc)
        kq.giay_viet += (ra.get("duration_ms") or 0) / 1000
        kq.usd_viet += float(ra.get("total_cost_usd") or 0)
        if not ra.get("is_error") and (moi / "ke_hoach.json").is_file():
            break
    else:
        loi.append(f"agent không viết được ke_hoach.json (đã thử lại 1 lần): {str(ra.get('result'))[:300]}")
        kq.loi = "; ".join(loi)
        return kq
    kj = KetQuaJob(ma, job["ma_chu_de"])
    try:
        kq.moi = qua_bien_tap(moi, kj, kenh=kenh, goc=goc, agent=agent, log=log,
                              bien_tap=lambda p, goc, log: _bien_tap_1_lan_thu_lai(bien_tap, p, goc=goc, log=log),
                              ghi_yeu_cau=lambda ph: _yeu_cau(moi, job, chu_de, brand, sx, ph, None, goc, them=them))
    except LoiBienTap as e:
        loi.append(f"biên tập bản mới lỗi (đã thử lại 1 lần): {e}")
    except RuntimeError as e:
        loi.append(str(e))
    kq.loi = "; ".join(loi)
    kq.giay_them, kq.usd_them, kq.so_luot_them, kq.vong = kj.giay_agent, kj.chi_phi_agent_usd, kj.so_luot_agent, kj.vong_kich_ban
    kq.kh_moi = json.loads((moi / "ke_hoach.json").read_text(encoding="utf-8"))
    kq.loi_ke_hoach = kiem_tra(kq.kh_moi, brand, sx)[0]
    return kq


# ---------------------------------------------------------------- báo cáo
def _o(s) -> str:
    return str(s or "").replace("|", "/").replace("\n", " ")


def bao_cao(ds: list[KetQuaSoSanh]) -> str:
    dong = ["# So sánh kịch bản cũ và mới (C2b)", "",
            "Mỗi video: kịch bản cũ và kịch bản viết lại bằng bộ biên kịch, chấm bằng **cùng một biên tập** "
            "(`skills/may-reels/bien-tap.md`, `brand/<kenh>/rubric-kich-ban.yaml`). Chỉ kế hoạch, chưa dựng.", "",
            "| Video | Điểm cũ | Điểm mới | Vòng sửa | Thêm mỗi video (biên tập + viết lại) |", "|---|---|---|---|---|"]
    for k in ds:
        dong.append(f"| {k.ma_video} | {_diem(k.cu)} | {_diem(k.moi)} | {k.vong} | {k.giay_them:.0f} s, {k.so_luot_them} lượt, "
                    f"claude báo {k.usd_them:.2f} USD |")
    n = [k for k in ds if k.moi]
    if n:
        dong += ["", f"Trung bình thêm mỗi video: {sum(k.giay_them for k in n) / len(n):.0f} s agent, "
                     f"{sum(k.usd_them for k in n) / len(n):.2f} USD (claude -p tự báo; gói Claude Code không tính "
                     "tiền theo lượt, con số này để so sánh). Người viết lần đầu (có cả trước C2b): "
                     f"{sum(k.giay_viet for k in n) / len(n):.0f} s, {sum(k.usd_viet for k in n) / len(n):.2f} USD."]
    for k in ds:
        dong += ["", f"## {k.ma_video}: {k.chu_de}", ""]
        if k.loi:
            dong += [f"**Lỗi:** {k.loi}", ""]
        kb = (k.kh_moi or {}).get("kich_ban") or {}
        if kb:
            dong += [f"- Nhóm: `{kb.get('nhom_doi_tuong')}`. Nỗi lo: {kb.get('noi_lo')} ({kb.get('nguon_noi_lo')}). "
                     f"Định dạng: `{kb.get('dinh_dang')}`.",
                     "- Ba góc kể: " + " / ".join(f"({i + 1}) {g}" for i, g in enumerate(kb.get("goc_ke") or []))
                     + f". Chọn {kb.get('goc_chon')}: {kb.get('ly_do_goc')}", ""]
            dong += ["| Hook | Công thức | Hình 0-3 giây | Câu nói | Chữ |", "|---|---|---|---|---|"]
            for i, h in enumerate([kb.get("hook_chon") or {}] + list(kb.get("phuong_an_hook") or [])):
                dong.append(f"| {'**chọn**' if i == 0 else i + 1} | {_o(h.get('cong_thuc'))} | {_o(h.get('hinh_0_3s'))} | "
                            f"{_o(h.get('cau_noi'))} | {_o(h.get('chu_man_hinh'))} |")
            dong += ["", f"Lý do chọn hook: {kb.get('ly_do_hook')}", ""]
        dong += ["| Đoạn | Kịch bản cũ | Kịch bản mới |", "|---|---|---|"]
        cu = (k.kh_cu or {}).get("doan") or []
        moi = (k.kh_moi or {}).get("doan") or []
        for i in range(max(len(cu), len(moi))):
            a = cu[i] if i < len(cu) else {}
            b = moi[i] if i < len(moi) else {}
            ta = f" [{a['the']['dong1']} / {a['the']['dong2']}]" if a.get("the") else ""
            tb = f" [{b['the']['dong1']} / {b['the']['dong2']}]" if b.get("the") else ""
            dong.append(f"| {_o(b.get('id') or a.get('id'))} {_o(b.get('vai') or a.get('vai'))} | {_o(a.get('loi'))}{_o(ta)} | "
                        f"{_o(b.get('loi'))}{_o(tb)} |")
        if (k.kh_cu or {}).get("_ghi_chu"):
            dong += ["", f"_{k.kh_cu['_ghi_chu']}_"]
        dong += ["", "| Tiêu chí | Tối đa | Cũ | Mới | Lý do (mới) |", "|---|---|---|---|---|"]
        tc_cu = {t["ma"]: t for t in getattr(k.cu, "tieu_chi", []) or []} if _diem(k.cu) != "lỗi" else {}
        tc_moi = {t["ma"]: t for t in getattr(k.moi, "tieu_chi", []) or []} if _diem(k.moi) != "lỗi" else {}
        for ma_tc in list(tc_moi) + [m for m in tc_cu if m not in tc_moi]:
            c, t = tc_cu.get(ma_tc), tc_moi.get(ma_tc)
            g = t or c
            d_c = format(c["diem"], "g") if c else "lỗi"
            d_t = format(t["diem"], "g") if t else "lỗi"
            dong.append(f"| {_o(g['ten'])} | {g['toi_da']:g} | {d_c} | {d_t} | {_o((t or {}).get('ly_do'))}"
                        + (f" (trần máy: {_o(t['tran'])})" if t and t.get("tran") else "") + " |")
        for ten, kqb in (("cũ", k.cu), ("mới", k.moi)):
            if kqb and (kqb.chan or kqb.canh_bao):
                dong.append(f"\nMáy kiểm bản {ten}: " + "; ".join((kqb.chan or []) + (kqb.canh_bao or [])))
        if k.moi and k.moi.goi_y_sua:
            dong += ["", "Gợi ý còn lại của biên tập (bản mới):"] + [f"- {g}" for g in k.moi.goi_y_sua]
        if k.loi_ke_hoach:
            dong += ["", "Lỗi kế hoạch nếu đem dựng (`may_reels/dung/ke_hoach.py`):"] + [f"- {x}" for x in k.loi_ke_hoach]
    return "\n".join(dong) + "\n"


def so_sanh(ma_ds: list[str], *, goc: Path = GOC, log: Callable[[str], None] = print, **kw) -> list[KetQuaSoSanh]:
    ds = []
    for ma in ma_ds:
        try:
            ds.append(so_sanh_mot(ma, goc=goc, log=log, **kw))
        except Exception as e:  # một video hỏng không kéo video khác
            ds.append(KetQuaSoSanh(ma, loi=f"{type(e).__name__}: {e}"[:500]))
    f = goc / THU_MUC / "BAO-CAO.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(bao_cao(ds), encoding="utf-8")
    log(f"Báo cáo: {f.relative_to(goc).as_posix()}")
    return ds
