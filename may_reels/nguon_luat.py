"""Máy đề xuất nguồn luật cho chủ đề; người chỉ xác nhận (KE-HOACH.md mục 6 câu 14).

    python -m may_reels nguon-luat --kenh <mã> [--ma <mã chủ đề> ...] [--thu]
        Chủ đề CHƯA LÀM có nguon_doi_chieu chưa tới mức khoản (QCVN: mục / phụ lục / số hiệu biển, vạch) và chưa có
        xac_nhan_nguon: agent (claude -p, skills/may-reels/tra-nguon-luat.md) mở văn bản chính thức, ghi
        projects/_may_reels/nguon_luat/<kenh>/<ma>.json. Python kiểm tra rồi ghi tab Ý tưởng: nguon_de_xuat,
        trich_nguyen_van, link_nguon, ngay_tra, ghi_chu_may. Không tìm được thì nguon_de_xuat trống + lý do.
    python -m may_reels nguon-luat ap-dung --kenh <mã> [--thu]
        xac_nhan_nguon = "Đúng": chép nguon_de_xuat vào cột "Nguồn cần đối chiếu" của dòng đó trong chu-de.md ở thư mục
        kênh gốc (sao lưu trước, chỉ đổi đúng ô đó), chạy tools_local/nap_kenh.py và sheet nap-chu-de.
        "Sai": giữ nguyên, báo người sửa y_chinh (rồi xóa ô xac_nhan_nguon và chạy lại nguon-luat).
Người vẫn là bước quyết định: máy KHÔNG tự áp dụng đề xuất chưa được xác nhận, không bật nguon_luat_da_mo.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import NHAT_KY, Y_TUONG
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky

GOC = Path(__file__).resolve().parent.parent
SKILL = "skills/may-reels/tra-nguon-luat.md"
KHONG_CAN = "không cần nguồn luật"
TU_TOI_DA_TRICH = 80          # skill yêu cầu khoảng 60 chữ; quá 80 chữ thì coi là không phải đoạn trích ngắn
TEN_MIEN_CHINH_THUC = ("vbpl.vn", "chinhphu.vn", "congbao.chinhphu.vn", "quochoi.vn", "moj.gov.vn", "mt.gov.vn",
                       "bocongan.gov.vn", "csgt.vn", "gov.vn")
COT_CHU_DE_NGUON = 6          # chỉ số ô "Nguồn cần đối chiếu" khi tách dòng bảng chu-de.md theo "|"


# ---------------------------------------------------------------- mức chi tiết của nguồn
def _bo_dau(s: str) -> str:
    from may_reels.cham_diem import bo_dau
    return bo_dau(s)


_VB_LUAT = re.compile(r"\b(luat|nghi dinh|thong tu|tt|nd|quyet dinh|bo luat)\b")
# "điểm a" (một chữ cái đứng riêng), không bắt "thời điểm"; "mục/phụ lục" phải theo sau là số, số La Mã hoặc một chữ cái.
_MUC = r"\b(muc|phu luc)\s+(\d+|[ivx]+|[a-z])\b"
_KHOAN = re.compile(r"\bkhoan\s+\d|\bdiem\s+[a-z]\b|" + _MUC)
_QCVN = re.compile(r"\bqcvn\b")
_QCVN_MUC = re.compile(_MUC + r"|\bdieu\s+\d|\b[pwrsi]\s?\.\s?\d{3}|\bvach\s+(so\s+)?\d")


def khong_can_nguon(nguon: str) -> bool:
    return KHONG_CAN in chuan(nguon or "").casefold()


def du_muc_khoan(nguon: str) -> bool:
    """Mọi phần (tách bằng ';') có nhắc văn bản luật đều ghi tới khoản/điểm; QCVN tới mục/phụ lục/số hiệu biển, vạch.
    Phần không phải văn bản pháp luật (vd. context/business.md) không xét. Trống = chưa đủ."""
    if khong_can_nguon(nguon):
        return True
    phan = [p.strip() for p in re.split(r";", nguon or "") if p.strip()]
    if not phan:
        return False
    co_luat = False
    for p in phan:
        b = _bo_dau(p)
        if _QCVN.search(b):
            co_luat = True
            if not _QCVN_MUC.search(b):
                return False
        elif _VB_LUAT.search(b):
            co_luat = True
            # Mỗi lần nhắc "Điều N" phải kèm khoản/điểm/mục ("Điều 57 khoản 1 và Điều 89": Điều 89 chưa đủ).
            doan = [d for d in re.split(r"(?=\bdieu\s+\d)", b) if d.strip()]
            co_dieu = [d for d in doan if re.match(r"dieu\s+\d", d)]
            if not all(_KHOAN.search(d) for d in (co_dieu or [b])):
                return False
    return co_luat


# ---------------------------------------------------------------- kết quả agent
@dataclass
class DeXuat:
    ma: str
    nguon_de_xuat: str = ""
    trich_nguyen_van: str = ""
    link_nguon: str = ""
    ngay_tra: str = ""
    ghi_chu: list[str] = field(default_factory=list)
    giay_agent: float = 0.0
    chi_phi_usd: float = 0.0
    loi: str = ""


def kiem_de_xuat(ma: str, raw: dict, ngay: str) -> DeXuat:
    """Kiểm tra file agent ghi. Đề xuất không đạt thì bỏ trống nguon_de_xuat và ghi lý do (không đoán)."""
    dx = DeXuat(ma, ngay_tra=str(raw.get("ngay_tra") or ngay))
    nguon = " ".join(str(raw.get("nguon_de_xuat") or "").split())
    trich = " ".join(str(raw.get("trich_nguyen_van") or "").split())
    link = str(raw.get("link_nguon") or "").strip()
    if raw.get("mau_thuan_y_chinh"):
        dx.ghi_chu.append(f"MÂU THUẪN y_chinh: {raw['mau_thuan_y_chinh']}")
    if raw.get("hieu_luc"):
        dx.ghi_chu.append(f"Hiệu lực: {raw['hieu_luc']}")
    if not nguon:
        dx.ghi_chu.append(f"Không đề xuất: {raw.get('ly_do_khong_tim_duoc') or 'agent không ghi lý do'}")
        return dx
    ly_do = []
    if not du_muc_khoan(nguon):
        ly_do.append("đề xuất chưa tới mức khoản/mục")
    if not trich:
        ly_do.append("thiếu trích nguyên văn")
    elif len(trich.split()) > TU_TOI_DA_TRICH:
        ly_do.append(f"trích {len(trich.split())} chữ, quá dài")
    if not re.match(r"^https?://", link):
        ly_do.append("thiếu link đã mở")
    if ly_do:
        dx.ghi_chu.append(f"Bỏ đề xuất '{nguon}': {', '.join(ly_do)}")
        return dx
    host = re.sub(r"^https?://", "", link).split("/")[0].lower()
    if not any(host == d or host.endswith("." + d) for d in TEN_MIEN_CHINH_THUC):
        dx.ghi_chu.append(f"Link không thuộc cổng chính thức ({host}): kiểm tra kỹ trước khi chọn Đúng")
    dx.nguon_de_xuat, dx.trich_nguyen_van, dx.link_nguon = nguon, trich, link
    return dx


def goi_agent_tra(prompt: str, *, du_an: Path, goc: Path, ma: str) -> dict:
    from may_reels.san_xuat import goi_agent
    return goi_agent(prompt, du_an=du_an, goc=goc, ghi=(f"{ma}.json",), web=True,
                     he_thong=("Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi. Chỉ làm theo "
                               f"{SKILL}. Chỉ ghi đúng một file {ma}.json trong thư mục được giao."))


# ---------------------------------------------------------------- lệnh nguon-luat
def can_tra(dong: dict, brand_cd: dict) -> bool:
    nguon = brand_cd.get("nguon_doi_chieu") or dong.get("nguon_doi_chieu") or ""
    return (not brand_cd.get("da_lam") and not chuan(dong.get("xac_nhan_nguon"))
            and not khong_can_nguon(nguon) and not du_muc_khoan(nguon))


def tra_nguon(bang: BangNguon, kenh: str, *, goc: Path = GOC, chi_ma: list[str] | None = None, thu: bool = False,
              agent: Callable[..., dict] = goi_agent_tra, log: Callable[[str], None] = print) -> list[DeXuat]:
    from may_reels.chu_de import doc_brand
    brand = doc_brand(kenh, goc)
    cd = {c["ma"]: c for c in brand.get("chu_de") or []}
    dong = {d["ma"]: d for d in doc_dong(bang, Y_TUONG) if d.get("kenh") == kenh}
    ds = [m for m in cd if (not chi_ma or m in chi_ma) and can_tra(dong.get(m, {}), cd[m])]
    if not ds:
        log("Không có chủ đề nào cần tra nguồn (đã tới mức khoản, đã làm, đã xác nhận, hoặc 'Không cần nguồn luật').")
        return []
    thu_muc = goc / "projects" / "_may_reels" / "nguon_luat" / kenh
    thu_muc.mkdir(parents=True, exist_ok=True)
    ra = []
    for ma in ds:
        c = cd[ma]
        log(f"== {ma}: {c.get('chu_de')} | hiện tại: {c.get('nguon_doi_chieu')!r}")
        if thu:
            ra.append(DeXuat(ma))
            continue
        t0 = time.monotonic()
        yc = {"ma": ma, "kenh": kenh, "chu_de": c.get("chu_de"), "y_chinh": c.get("y_chinh"),
              "nguon_doi_chieu_hien_tai": c.get("nguon_doi_chieu"), "tru_cot": c.get("tru_cot"),
              "ngay_hom_nay": bay_gio_vn()[:10]}
        (thu_muc / f"{ma}.yeu_cau.json").write_text(json.dumps(yc, ensure_ascii=False, indent=1), encoding="utf-8")
        f = thu_muc / f"{ma}.json"
        f.unlink(missing_ok=True)
        rel = thu_muc.relative_to(goc).as_posix()
        try:
            r = agent(f"Đọc và làm đúng theo {SKILL}. Đọc {rel}/{ma}.yeu_cau.json rồi ghi {rel}/{ma}.json.",
                      du_an=thu_muc, goc=goc, ma=ma)
            raw = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
            dx = kiem_de_xuat(ma, raw, bay_gio_vn()[:10])
            if r.get("is_error") or not f.is_file():
                dx.loi = f"agent lỗi: {str(r.get('result'))[:200]}"
                dx.ghi_chu.append(dx.loi)
            dx.giay_agent = round((r.get("duration_ms") or 0) / 1000, 1)
            dx.chi_phi_usd = float(r.get("total_cost_usd") or 0)
        except Exception as e:
            dx = DeXuat(ma, ngay_tra=bay_gio_vn()[:10], loi=f"{type(e).__name__}: {e}"[:300])
            dx.ghi_chu.append(dx.loi)
        ghi_theo_khoa(bang, Y_TUONG, [{"kenh": kenh, "ma": ma, "nguon_de_xuat": dx.nguon_de_xuat,
                                       "trich_nguyen_van": dx.trich_nguyen_van, "link_nguon": dx.link_nguon,
                                       "ngay_tra": dx.ngay_tra, "ghi_chu_may": "\n".join(dx.ghi_chu)[:1000]}])
        giay = round(time.monotonic() - t0, 1)
        try:
            them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": ma, "buoc": "nguon_luat",
                                          "che_do": "that", "ket_qua": "loi" if dx.loi else "ok",
                                          "chi_tiet": (f"{dx.nguon_de_xuat or '(không đề xuất)'}; claude báo "
                                                       f"{dx.chi_phi_usd:.2f} USD; " + "; ".join(dx.ghi_chu))[:500],
                                          "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(giay), "so_luot_tro_ly": "1"}])
        except Exception:  # pragma: no cover
            pass
        log(f"   -> {dx.nguon_de_xuat or '(không đề xuất)'} | {dx.giay_agent:.0f}s, {dx.chi_phi_usd:.2f} USD"
            + (f" | {'; '.join(dx.ghi_chu)}" if dx.ghi_chu else ""))
        ra.append(dx)
    return ra


# ---------------------------------------------------------------- lệnh nguon-luat ap-dung
def sua_dong_chu_de(text: str, ma: str, nguon: str) -> tuple[str, str]:
    """Thay ô "Nguồn cần đối chiếu" của đúng dòng mã `ma`. Trả về (văn bản mới, giá trị cũ). Giữ kiểu xuống dòng."""
    if "|" in nguon or "\n" in nguon:
        raise ValueError("nguon_de_xuat không được chứa '|' hay xuống dòng")
    dong = text.split("\n")
    vt = [i for i, d in enumerate(dong) if d.startswith(f"| {ma} |")]
    if len(vt) != 1:
        raise ValueError(f"chu-de.md: tìm thấy {len(vt)} dòng mã {ma!r} (cần đúng 1)")
    i = vt[0]
    cr = dong[i].endswith("\r")
    o = (dong[i][:-1] if cr else dong[i]).split("|")
    cu = o[COT_CHU_DE_NGUON].strip()
    o[COT_CHU_DE_NGUON] = f" {nguon} "
    dong[i] = "|".join(o) + ("\r" if cr else "")
    return "\n".join(dong), cu


def chay_nap_kenh(kenh: str, goc: Path) -> None:
    r = subprocess.run([sys.executable, "tools_local/nap_kenh.py", "--id", kenh], cwd=goc, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if r.returncode != 0:
        raise RuntimeError(f"nap_kenh.py lỗi: {r.stderr.strip()[-500:]}")


def ap_dung(bang: BangNguon, kenh: str, *, goc: Path = GOC, thu_muc_kenh: Path | None = None, thu: bool = False,
            nap: Callable[[str, Path], None] = chay_nap_kenh, log: Callable[[str], None] = print) -> dict:
    from may_reels.chu_de import doc_brand, nap_chu_de
    if thu_muc_kenh is None:
        from tools_local.nap_kenh import nap_env, thu_muc_kenh as tmk
        nap_env()
        thu_muc_kenh = tmk(kenh)
    if not thu_muc_kenh or not (thu_muc_kenh / "chu-de.md").is_file():
        raise RuntimeError(f"Không thấy chu-de.md của kênh {kenh} (KENH_GOC_DIR)")
    cd = {c["ma"]: c for c in doc_brand(kenh, goc).get("chu_de") or []}
    dung, sai = [], []
    for d in doc_dong(bang, Y_TUONG):
        if d.get("kenh") != kenh:
            continue
        x = chuan(d.get("xac_nhan_nguon"))
        if x == "Đúng" and d.get("nguon_de_xuat") and (cd.get(d["ma"]) or {}).get("nguon_doi_chieu") != d["nguon_de_xuat"]:
            dung.append(d)
        elif x == "Sai":
            sai.append(d)
    kq = {"ap_dung": [], "sai": [d["ma"] for d in sai], "sao_luu": None}
    for d in sai:
        log(f"{d['ma']}: xác nhận SAI. Giữ nguyên chu-de.md. Sửa y_chinh trong chu-de.md, xóa ô xac_nhan_nguon rồi chạy "
            f"lại nguon-luat. (đề xuất: {d.get('nguon_de_xuat') or '-'})")
    if not dung:
        log("Không có đề xuất 'Đúng' nào cần áp dụng.")
        return kq
    # Chủ đề máy đề xuất (y-tuong) nằm ở chu-de-may.md (brand.json ghi "tep"); còn lại ở chu-de.md của người.
    theo_tep: dict[str, list[dict]] = {}
    for d in dung:
        theo_tep.setdefault((cd.get(d["ma"]) or {}).get("tep") or "chu-de.md", []).append(d)
    van_ban: dict[str, str] = {}
    for tep, ds in theo_tep.items():
        f = thu_muc_kenh / tep
        if not f.is_file():
            raise RuntimeError(f"Không thấy {tep} của kênh {kenh} (KENH_GOC_DIR)")
        text = f.read_bytes().decode("utf-8")
        for d in ds:
            text, cu = sua_dong_chu_de(text, d["ma"], d["nguon_de_xuat"])
            kq["ap_dung"].append((d["ma"], cu, d["nguon_de_xuat"]))
            log(f"{'[thử] ' if thu else ''}{d['ma']} ({tep}): {cu!r} -> {d['nguon_de_xuat']!r}")
        van_ban[tep] = text
    if thu:
        return kq
    sao_luu = []
    for tep, text in van_ban.items():
        f = thu_muc_kenh / tep
        sl = f.with_name(f"{tep}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(f, sl)
        sao_luu.append(sl)
        f.write_bytes(text.encode("utf-8"))
    sl = sao_luu[0]
    kq["sao_luu"], kq["sao_luu_tat_ca"] = sl, sao_luu
    nap(kenh, goc)
    nap_chu_de(bang, kenh, goc=goc)
    ghi_theo_khoa(bang, Y_TUONG, [{"kenh": kenh, "ma": m, "ghi_chu_may": f"Đã áp dụng vào chu-de.md ({bay_gio_vn()})"}
                                  for m, _c, _n in kq["ap_dung"]])
    them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": "", "buoc": "nguon_luat.ap_dung",
                                  "che_do": "that", "ket_qua": "ok",
                                  "chi_tiet": f"áp dụng {[m for m, *_ in kq['ap_dung']]}; sao lưu {[x.name for x in sao_luu]}"[:500],
                                  "chi_phi_vnd": "0", "thoi_gian_chay_giay": "0", "so_luot_tro_ly": "0"}])
    log(f"Đã sao lưu {', '.join(x.name for x in sao_luu)}, chạy nap_kenh.py và sheet nap-chu-de.")
    return kq
