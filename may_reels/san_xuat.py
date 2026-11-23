"""Sản xuất hàng loạt: `python -m may_reels san-xuat --kenh <mã> --so-luong 3`.

Mỗi chủ đề có duyet_chu_de = "Làm" và chưa sản xuất -> một reel_job (projects/<ma_video>/reel_job.json):
  1. Agent (claude -p, skill skills/may-reels/san-xuat-khong-hoi.md) viết ke_hoach.json. Giới hạn thời gian.
  2. Dựng tất định trong tiến trình riêng: python -m may_reels dung --du-an <ma_video>. Giới hạn thời gian.
  3. Kế hoạch sai / QA dưới ngưỡng -> gửi phản hồi cho agent, tối đa san-xuat.yaml cham_diem.so_vong_sua vòng.
     Hết vòng mà vẫn dưới ngưỡng -> vẫn vào Hàng chờ kèm cảnh báo "Dưới ngưỡng".
  4. Thiếu cảnh thật -> tab Cần quay, job sang cho_quay, không dựng.
  5. Xong -> Hàng chờ (hang_cho.dua_vao_hang_cho), cập nhật trang_thai_san_xuat, ghi Nhật ký.
Job hỏng chỉ đánh dấu lỗi của job đó; các job khác vẫn chạy.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import CAN_QUAY, NHAT_KY, Y_TUONG
from may_reels.job import NHAN_TRANG_THAI, chuyen_trang_thai, kiem_tra as kiem_job, tao_job
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky

GOC = Path(__file__).resolve().parent.parent
TZ_VN = timezone(timedelta(hours=7))
SKILL = "skills/may-reels/san-xuat-khong-hoi.md"
GIAY_AGENT = int(os.environ.get("MAY_REELS_GIAY_AGENT", "1500"))
GIAY_DUNG = int(os.environ.get("MAY_REELS_GIAY_DUNG", "3600"))
# Mã thoát của `python -m may_reels dung`
MA_OK, MA_KE_HOACH, MA_THIEU_CANH, MA_QA, MA_CONG = 0, 10, 11, 12, 13
CANH_BAO_DUOI_NGUONG = "Dưới ngưỡng"
DA_SAN_XUAT = {"", NHAN_TRANG_THAI["y_tuong"]}

LOI_NHAC_HE_THONG = (
    "Bạn đang chạy KHÔNG TƯƠNG TÁC cho Máy Reels: không có người để hỏi, không được dừng chờ trả lời. "
    "Chỉ làm theo skill được chỉ định; bỏ qua mọi quy trình OpenMontage khác (không chạy pipeline, không hỏi chọn runtime). "
    "Chỉ ghi đúng một file ke_hoach.json trong thư mục dự án được giao. Mọi quyết định tự đưa ra ghi vào mảng quyet_dinh."
)


@dataclass
class KetQuaJob:
    ma_video: str
    ma_chu_de: str
    trang_thai: str = "loi"
    diem_qa: int | None = None
    canh_bao: list[str] = field(default_factory=list)
    loi: str = ""
    giay: float = 0.0
    so_luot_agent: int = 0
    giay_agent: float = 0.0
    chi_phi_agent_usd: float = 0.0  # claude -p tự báo total_cost_usd (chỉ ghi lại; trần 0 USD là cho công cụ dựng)
    thieu_canh: list[dict] = field(default_factory=list)
    vong: int = 0
    diem_kich_ban: int | None = None   # biên tập trước khi dựng (may_reels/bien_tap.py)
    cong_thuc_hook: str = ""
    vong_kich_ban: int = 0
    canh_bao_kich_ban: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- công cụ chạy ngoài
def goi_agent(prompt: str, *, du_an: Path, goc: Path = GOC, giay: int = GIAY_AGENT,
              ghi: tuple[str, ...] = ("ke_hoach.json",), web: bool = True, he_thong: str = LOI_NHAC_HE_THONG,
              doc: tuple[str, ...] | None = None) -> dict:
    """claude -p không tương tác. Chỉ được ghi các file `ghi` (tương đối trong dự án).
    `doc`: nếu có, CHỈ được Read đúng các file này (tương đối từ gốc repo; không Glob/Grep). Biên tập dùng để không
    đọc được lập luận của người viết. Trả về JSON kết quả (result, num_turns, duration_ms, is_error...)."""
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError("Không thấy lệnh claude (Claude Code CLI)")
    rel = du_an.relative_to(goc).as_posix()
    cong_cu = ([f"Read(./{p})" for p in doc] if doc is not None else ["Read", "Glob", "Grep"]) + \
        (["WebFetch", "WebSearch"] if web else [])
    for f in ghi:
        cong_cu += [f"Write(./{rel}/{f})", f"Edit(./{rel}/{f})"]
    cmd = [claude, "-p", prompt, "--output-format", "json", "--permission-mode", "dontAsk",
           "--allowed-tools", " ".join(cong_cu), "--append-system-prompt", he_thong, "--no-session-persistence"]
    t = time.monotonic()
    try:
        r = subprocess.run(cmd, cwd=goc, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=giay)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": f"agent quá {giay}s", "duration_ms": giay * 1000}
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
    except (ValueError, IndexError):
        out = {"result": r.stdout[-1000:]}
    out.setdefault("duration_ms", int((time.monotonic() - t) * 1000))
    if r.returncode != 0:
        out["is_error"] = True
        out.setdefault("result", r.stderr[-1000:])
    return out


def chay_dung(ma_video: str, *, goc: Path = GOC, giay: int = GIAY_DUNG, stages: list[str] | None = None) -> tuple[int, dict]:
    """Dựng trong tiến trình riêng (job hỏng không kéo job khác). Trả về (mã thoát, tóm tắt JSON)."""
    cmd = [sys.executable, "-m", "may_reels", "dung", "--du-an", ma_video] + (["--stage", *stages] if stages else [])
    try:
        r = subprocess.run(cmd, cwd=goc, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=giay,
                           env={**os.environ, "PYTHONUTF8": "1"})
    except subprocess.TimeoutExpired:
        return 1, {"loi": f"dựng quá {giay}s"}
    (goc / "projects" / ma_video / "dung.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    tom = {}
    for dong in reversed(r.stdout.strip().splitlines()):
        if dong.startswith("{"):
            try:
                tom = json.loads(dong)
                break
            except ValueError:
                pass
    if r.returncode != 0 and not tom:
        tom = {"loi": r.stderr.strip()[-800:]}
    return r.returncode, tom


# ---------------------------------------------------------------- chọn chủ đề, đặt mã
def _jobs(goc: Path) -> dict[str, dict]:
    """ma_chu_de -> reel_job (đọc projects/*/reel_job.json)."""
    out = {}
    for f in (goc / "projects").glob("*/reel_job.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out[j.get("ma_chu_de")] = j
    return out


LY_DO_THIEU_NGUON = ("Chưa sản xuất: nguon_doi_chieu chưa tới mức khoản (QCVN: mục/phụ lục/số hiệu). "
                     "Chạy `nguon-luat`, chọn xac_nhan_nguon = Đúng, rồi `nguon-luat ap-dung`.")


def chon_chu_de(bang: BangNguon, kenh: str, so_luong: int, goc: Path = GOC, ca_cho_quay: bool = False,
                ca_loi: bool = False, tu_choi: list | None = None) -> list[dict]:
    """Chủ đề "Làm" chưa sản xuất. ca_cho_quay: thêm chủ đề có job đang cho_quay (dựng lại với cảnh tạm).
    Chủ đề có nội dung luật mà nguon_doi_chieu (brand.json, từ chu-de.md) chưa tới mức khoản thì bị từ chối:
    thêm vào `tu_choi`, không chiếm chỗ. "Không cần nguồn luật" thì bỏ qua kiểm tra này."""
    from may_reels.dung.ke_hoach import doc_brand
    from may_reels.nguon_luat import du_muc_khoan
    cd_brand = {c.get("ma"): c for c in doc_brand(kenh, goc).get("chu_de") or []}
    jobs = _jobs(goc)
    out = []
    for r in doc_dong(bang, Y_TUONG):
        if r.get("kenh") != kenh or chuan(r.get("duyet_chu_de")) != "Làm":
            continue
        j = jobs.get(r.get("ma"))
        if j:
            lam_lai = ({"cho_quay"} if ca_cho_quay else set()) | ({"loi"} if ca_loi else set())
            # `kho nap` đánh dấu job chờ quay đã đủ cảnh quay và nạp: tự vào hàng sản xuất, không cần --ca-cho-quay.
            du_canh = j.get("trang_thai") == "cho_quay" and (j.get("metadata") or {}).get("san_sang_san_xuat_lai")
            if j.get("trang_thai") not in lam_lai and not du_canh:
                continue
            r = {**r, "_ma_video": j["ma_video"]}
        elif chuan(r.get("trang_thai_san_xuat")) not in DA_SAN_XUAT:
            continue
        nguon = (cd_brand.get(r.get("ma")) or {}).get("nguon_doi_chieu") or r.get("nguon_doi_chieu") or ""
        if not du_muc_khoan(nguon):
            if tu_choi is not None:
                tu_choi.append({**r, "_nguon": nguon})
            continue
        out.append(r)
        if len(out) >= so_luong:
            break
    return out


def so_tiep_theo(kenh: str, goc: Path = GOC) -> tuple[str, int]:
    from tools_local.nap_kenh import nap_env, thu_muc_kenh
    import yaml
    cfg_f = goc / "brand" / kenh / "cau-hinh.yaml"
    cfg = yaml.safe_load(cfg_f.read_text(encoding="utf-8")) if cfg_f.is_file() else {}
    tien_to = cfg.get("tien_to_ma_video") or kenh
    mau = re.compile(rf"^{re.escape(tien_to)}-(\d+)")
    ten = [p.name for p in (goc / "projects").iterdir() if p.is_dir()]
    nap_env()
    tm = thu_muc_kenh(kenh)
    if tm and cfg.get("thu_muc_video") and (tm / cfg["thu_muc_video"]).is_dir():
        ten += [p.name for p in (tm / cfg["thu_muc_video"]).iterdir()]
    so = [int(m.group(1)) for n in ten if (m := mau.match(n))]
    return tien_to, (max(so) + 1 if so else 1)


# ---------------------------------------------------------------- một job
def _yeu_cau(P: Path, job: dict, chu_de: dict, brand: dict, sx: dict, phan_hoi: str | None, ghi_chu_sua: str | None,
             goc: Path, them: dict | None = None) -> None:
    from may_reels.bien_tap import dinh_dang_cua, doc_thu_vien
    from may_reels.kho import thong_ke_dung_canh
    tk = thong_ke_dung_canh(goc, job["kenh"], job["ma_video"])
    khung = next((k for k, v in (sx.get("khung_nhip") or {}).items() if v.get("tru_cot") == chu_de.get("tru_cot")),
                 next(iter(sx.get("khung_nhip") or {"": None})))
    yc = {"ma_video": job["ma_video"], "kenh": job["kenh"], "khung_nhip": khung,
          "chu_de": {k: chu_de.get(k) for k in ("ma", "tru_cot", "dinh_dang", "chu_de", "y_chinh", "nguon_doi_chieu")},
          "so_lan_dung_canh": {m: t["so_lan"] for m, t in tk.items()},
          "ngay_dung_canh_gan_nhat": {m: t["ngay_gan_nhat"] for m, t in tk.items() if t["ngay_gan_nhat"]},
          "ngay_hom_nay": datetime.now(TZ_VN).date().isoformat()}
    # Bộ biên kịch (skills/may-reels/bien-kich.md): định dạng của chủ đề và nhóm đối tượng gợi ý.
    dd = dinh_dang_cua(doc_thu_vien(job["kenh"], goc), chu_de, khung)
    if dd:
        yc["dinh_dang"] = {k: dd.get(k) for k in ("ma", "ten", "tang", "nhom_chinh", "hook_mau", "giong")}
    # Câu hỏi khách (tab Câu hỏi khách, C1). Chưa có tab thì để rỗng: người viết dùng noi_lo trong doi-tuong.yaml.
    yc["cau_hoi_khach"] = list(chu_de.get("cau_hoi_khach") or [])
    if phan_hoi:
        yc["phan_hoi"] = phan_hoi
    if ghi_chu_sua:
        yc["ghi_chu_sua"] = ghi_chu_sua
    yc.update(them or {})
    (P / "yeu_cau.json").write_text(json.dumps(yc, ensure_ascii=False, indent=2), encoding="utf-8")


def _luu_job(P: Path, job: dict) -> None:
    kiem_job(job)
    (P / "reel_job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def _cap_nhat_y_tuong(bang, kenh: str, ma: str, trang_thai: str, diem: int | None = None) -> None:
    d = {"kenh": kenh, "ma": ma, "trang_thai_san_xuat": trang_thai}
    if diem is not None:
        d["diem"] = str(diem)
    ghi_theo_khoa(bang, Y_TUONG, [d])


def ghi_can_quay(bang, kenh: str, ma_chu_de: str, ma_video: str, thieu: list[dict]) -> None:
    luc = bay_gio_vn()
    ghi_theo_khoa(bang, CAN_QUAY, [{"ma_yeu_cau": f"{kenh}:{ma_chu_de}:{i}", "kenh": kenh, "ma_chu_de": ma_chu_de,
                                    "ma_video": ma_video, "y_can_canh": t.get("y_can_canh", ""),
                                    "mo_ta_canh": t.get("mo_ta_canh", ""), "goi_y_quay": t.get("goi_y_quay", ""),
                                    "ly_do": t.get("ly_do", ""), "tao_luc": luc}
                                   for i, t in enumerate(thieu, start=1)], chi_khi_trong={"tao_luc"})


def cap_nhat_su_dung_an_toan(kenh: str, goc: Path, log: Callable[[str], None] = print) -> None:
    """Sau mỗi video vào Hàng chờ: ghi so_lan_dung, ngay_dung_gan_nhat vào index.json của kho. Lỗi không làm hỏng job."""
    try:
        from may_reels.kho import cap_nhat_su_dung
        n = cap_nhat_su_dung(kenh, goc)
        if n:
            log(f"  kho cảnh: cập nhật số lần dùng của {n} cảnh")
    except Exception as e:  # pragma: no cover
        log(f"  ! không cập nhật được số lần dùng cảnh: {e}")


def bien_tap_mac_dinh(P: Path, *, goc: Path = GOC, log: Callable[[str], None] = print):
    from may_reels.bien_tap import bien_tap
    return bien_tap(P, goc=goc, log=log)


def prompt_viet(P: Path, goc: Path, phan_hoi: str | None = None) -> str:
    rel = P.relative_to(goc).as_posix()
    return (f"Đọc và làm đúng theo {SKILL}. Dự án: {rel}. Đọc {rel}/yeu_cau.json rồi viết {rel}/ke_hoach.json."
            + (" Đây là vòng sửa: xem mục phan_hoi." if phan_hoi else ""))


def qua_bien_tap(P: Path, kq: KetQuaJob, *, kenh: str, goc: Path, agent: Callable[..., dict],
                 bien_tap: Callable, ghi_yeu_cau: Callable[[str], None], log: Callable[[str], None] = print,
                 bang=None):
    """Biên tập kịch bản trước khi dựng: dưới ngưỡng thì trả về người viết sửa, tối đa rubric-kich-ban.yaml
    so_vong_sua vòng, rồi vẫn đi tiếp (kèm cảnh báo). Kênh chưa có rubric-kich-ban.yaml: bỏ qua bước này.
    Biên tập hỏng (claude -p không ghi được diem.json): thử lại 1 lần; vẫn hỏng thì KHÔNG coi là điểm 0, không trả
    người viết sửa theo điểm giả: dừng biên tập, đi tiếp với kế hoạch hiện có, diem_kich_ban để trống, kèm cảnh báo."""
    from may_reels.bien_tap import (CANH_BAO_DUOI_NGUONG as CB_KB, CANH_BAO_LOI_BIEN_TAP, bien_tap_thu_lai,
                                    co_rubric, doc_rubric_kb)
    if not co_rubric(kenh, goc):
        log(f"  [{P.name}] bỏ qua biên tập: chưa có brand/{kenh}/rubric-kich-ban.yaml")
        return None
    so_vong = int(doc_rubric_kb(kenh, goc).get("so_vong_sua", 2))
    kb = None
    for v in range(so_vong + 1):
        kq.vong_kich_ban = v
        log(f"  [{P.name}] biên tập kịch bản vòng {v}")
        kb = bien_tap_thu_lai(bien_tap, P, goc=goc, log=log)
        kq.so_luot_agent += kb.so_luot_agent
        kq.giay_agent += kb.giay_agent
        kq.chi_phi_agent_usd += kb.chi_phi_agent_usd
        if bang is not None:
            try:
                them_nhat_ky(bang, NHAT_KY, [{
                    "thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": kq.ma_video, "buoc": "bien_tap", "che_do": "that",
                    "ket_qua": "ok" if kb.dat else "loi",
                    "chi_tiet": ((f"biên tập lỗi (đã thử lại 1 lần), không có điểm kịch bản; vòng {v}; {kb.loi_agent}"
                                  if kb.loi_agent else
                                  f"kịch bản {kb.diem}/{kb.nguong}; vòng {v}; hook {kb.cong_thuc_hook}; "
                                  f"agent {kb.giay_agent:.0f}s" + (f"; CHẶN: {'; '.join(kb.chan)}" if kb.chan else "")))[:500],
                    "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kb.giay), "so_luot_tro_ly": str(kb.so_luot_agent)}])
            except Exception:  # pragma: no cover
                pass
        if kb.loi_agent:
            log(f"  [{P.name}] biên tập lỗi cả lần thử lại: đi tiếp không có điểm kịch bản")
            kq.diem_kich_ban, kq.cong_thuc_hook = None, kb.cong_thuc_hook
            kq.canh_bao_kich_ban = [CANH_BAO_LOI_BIEN_TAP]
            return kb
        if kb.dat or v == so_vong:
            break
        ph = kb.phan_hoi()
        ghi_yeu_cau(ph)
        log(f"  [{P.name}] viết lại kịch bản: {ph[:200]}")
        ra = agent(prompt_viet(P, goc, ph), du_an=P, goc=goc)
        kq.so_luot_agent += 1
        kq.giay_agent += (ra.get("duration_ms") or 0) / 1000
        kq.chi_phi_agent_usd += float(ra.get("total_cost_usd") or 0)
        if ra.get("is_error") or not (P / "ke_hoach.json").is_file():
            raise RuntimeError(f"agent không viết lại được ke_hoach.json: {str(ra.get('result'))[:300]}")
    kq.diem_kich_ban, kq.cong_thuc_hook = kb.diem, kb.cong_thuc_hook
    if not kb.dat:
        kq.canh_bao_kich_ban = [f"{CB_KB} ({kb.diem}/{kb.nguong})"]
    return kb


def _kb(kq: KetQuaJob) -> str:
    """Điểm kịch bản để in: '-' khi chưa chấm hoặc biên tập lỗi (không in điểm giả)."""
    return "-" if kq.diem_kich_ban is None else str(kq.diem_kich_ban)


def cham_mac_dinh(ma_video: str, *, goc: Path = GOC, log: Callable[[str], None] = print, tom: dict | None = None):
    from may_reels.cham_diem import cham_video
    return cham_video(ma_video, goc=goc, log=log, tom=tom)


def nhat_ky_cham(bang, kenh: str, ma_video: str, kc, buoc: str = "cham_diem") -> None:
    """Một dòng Nhật ký cho mỗi lần chấm (thời gian chạy và lượt agent)."""
    try:
        them_nhat_ky(bang, NHAT_KY, [{
            "thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": ma_video, "buoc": buoc, "che_do": "that",
            "ket_qua": "loi" if kc.chan else "ok",
            "chi_tiet": (f"QA {kc.diem_qa}; kỹ thuật {kc.diem_ky_thuat}; agent {kc.giay_agent:.0f}s"
                         + (f"; CHẶN: {'; '.join(kc.chan)}" if kc.chan else "")
                         + (f"; trừ: {kc.ly_do_tru[0]}" if kc.ly_do_tru else ""))[:500],
            "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kc.giay), "so_luot_tro_ly": str(kc.so_luot_agent)}])
    except Exception:  # pragma: no cover
        pass


def canh_bao_duoi_nguong(kc, nguong: int) -> list[str]:
    """'Dưới ngưỡng' + 2 lý do trừ điểm nặng nhất (đứng đầu cột canh_bao)."""
    return [f"{CANH_BAO_DUOI_NGUONG} ({kc.diem_qa}/{nguong})"] + kc.ly_do_tru[:2]


def san_xuat_mot(bang: BangNguon, chu_de: dict, ma_video: str, *, goc: Path = GOC,
                 agent: Callable[..., dict] = goi_agent, dung: Callable[..., tuple[int, dict]] = chay_dung,
                 cham: Callable | None = None, bien_tap: Callable | None = None,
                 log: Callable[[str], None] = print) -> KetQuaJob:
    from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat
    from may_reels.hang_cho import dua_vao_hang_cho
    t0 = time.monotonic()
    kenh, ma = chu_de["kenh"], chu_de["ma"]
    kq = KetQuaJob(ma_video, ma)
    brand, sx = doc_brand(kenh, goc), doc_san_xuat(kenh, goc)
    cd_brand = next((c for c in brand.get("chu_de") or [] if c.get("ma") == ma), {})
    cd = {**cd_brand, **{k: v for k, v in chu_de.items() if v}}
    P = goc / "projects" / ma_video
    P.mkdir(parents=True, exist_ok=True)
    phan_hoi = None
    if (P / "reel_job.json").is_file():  # job cũ (cho_quay hoặc loi): dựng lại, đoạn thiếu cảnh dùng cảnh tạm
        job = json.loads((P / "reel_job.json").read_text(encoding="utf-8"))
        # Bỏ cờ "đủ cảnh" trước khi dựng: nếu lại thiếu cảnh và về cho_quay, job không tự vào hàng sản xuất lần nữa.
        (job.get("metadata") or {}).pop("san_sang_san_xuat_lai", None)
        job = chuyen_trang_thai(job, "dang_san_xuat", ly_do=f"Dựng lại từ trạng thái {job['trang_thai']}")
        phan_hoi = ("Lần trước thiếu cảnh thật nên chưa dựng. Giữ thieu_canh, và cho mỗi đoạn trong thieu_canh dùng "
                    "cảnh tạm canh.so_do (xem skill mục Chọn cảnh). Kiểm tra lại kho: nếu nay đã có cảnh thật khớp ý thì dùng cảnh thật.")
    else:
        job = tao_job(ma_video=ma_video, kenh=kenh, ma_chu_de=ma, chu_de=cd.get("chu_de") or ma,
                      dinh_dang=cd.get("dinh_dang") or "khac", nen_tang_dich=["fb_reels", "yt_shorts", "tiktok"],
                      project_dir=f"projects/{ma_video}", luc=datetime.now(TZ_VN).isoformat(timespec="seconds"))
        job = chuyen_trang_thai(job, "dang_san_xuat", ly_do="Sheet: duyet_chu_de = Làm")
    _luu_job(P, job)
    _cap_nhat_y_tuong(bang, kenh, ma, NHAN_TRANG_THAI["dang_san_xuat"])
    cham = cham or cham_mac_dinh
    bien_tap = bien_tap or bien_tap_mac_dinh
    nguong = int((sx.get("cham_diem") or {}).get("nguong", 75))
    so_vong = int((sx.get("cham_diem") or {}).get("so_vong_sua", 2))
    tom: dict = {}
    try:
        for vong in range(so_vong + 1):
            kq.vong = vong
            _yeu_cau(P, job, cd, brand, sx, phan_hoi, None, goc)
            log(f"  [{ma_video}] agent vòng {vong}")
            ra = agent(prompt_viet(P, goc, phan_hoi), du_an=P, goc=goc)
            kq.so_luot_agent += 1
            kq.giay_agent += (ra.get("duration_ms") or 0) / 1000
            kq.chi_phi_agent_usd += float(ra.get("total_cost_usd") or 0)
            if ra.get("is_error") or not (P / "ke_hoach.json").is_file():
                raise RuntimeError(f"agent không viết được ke_hoach.json: {str(ra.get('result'))[:300]}")
            if vong == 0:
                # Biên tập kịch bản trước khi tốn công sinh giọng và dựng. Chỉ chạy một lần (bản đầu); các vòng sửa
                # sau là sửa lỗi kế hoạch / QA video, không biên tập lại.
                qua_bien_tap(P, kq, kenh=kenh, goc=goc, agent=agent, bien_tap=bien_tap, log=log, bang=bang,
                             ghi_yeu_cau=lambda ph: _yeu_cau(P, job, cd, brand, sx, ph, None, goc))
            log(f"  [{ma_video}] dựng")
            ma_thoat, tom = dung(ma_video, goc=goc, stages=["idea", "script", "scene_plan", "assets", "edit", "compose",
                                                           "publish"])
            if ma_thoat == MA_THIEU_CANH:
                kq.thieu_canh = tom.get("thieu_canh") or []
                ghi_can_quay(bang, kenh, ma, ma_video, kq.thieu_canh)
                job = chuyen_trang_thai(job, "cho_quay", ly_do=tom.get("loi", "thiếu cảnh"))
                _luu_job(P, job)
                _cap_nhat_y_tuong(bang, kenh, ma, NHAN_TRANG_THAI["cho_quay"])
                kq.trang_thai, kq.loi = "cho_quay", tom.get("loi", "")
                return kq
            if ma_thoat == MA_CONG:
                raise RuntimeError(tom.get("loi", "cổng idea chưa mở"))
            if ma_thoat in (MA_KE_HOACH, MA_QA):
                phan_hoi = ("Lỗi kế hoạch: " if ma_thoat == MA_KE_HOACH else "Bản dựng không qua tự kiểm: ") + tom.get("loi", "")
                log(f"  [{ma_video}] {phan_hoi[:200]}")
                if vong == so_vong:
                    raise RuntimeError(phan_hoi)
                continue
            if ma_thoat != MA_OK:
                raise RuntimeError(tom.get("loi", f"dựng lỗi mã {ma_thoat}"))
            log(f"  [{ma_video}] chấm điểm")
            kc = cham(ma_video, goc=goc, log=log, tom=tom)
            kq.so_luot_agent += kc.so_luot_agent
            kq.giay_agent += kc.giay_agent
            kq.chi_phi_agent_usd += kc.chi_phi_agent_usd
            nhat_ky_cham(bang, kenh, ma_video, kc)
            if kc.chan:  # chặn cứng: không vào Hàng chờ, không vòng sửa
                raise RuntimeError("Chặn cứng: " + "; ".join(kc.chan))
            kq.diem_qa = kc.diem_qa
            kq.canh_bao = list(kc.canh_bao) + list(tom.get("canh_bao") or [])
            if kq.diem_qa is not None and kq.diem_qa < nguong:
                if vong < so_vong:
                    phan_hoi = kc.phan_hoi(nguong)
                    log(f"  [{ma_video}] {phan_hoi[:300]}")
                    continue
                kq.canh_bao = canh_bao_duoi_nguong(kc, nguong) + kq.canh_bao
            break

        kh = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
        kq.canh_bao = kq.canh_bao_kich_ban + kq.canh_bao
        cot_them = {"diem_kich_ban": "" if kq.diem_kich_ban is None else str(kq.diem_kich_ban),
                    "cong_thuc_hook": kq.cong_thuc_hook}
        hq = dua_vao_hang_cho(bang, video=P / "renders" / "final.mp4", kenh=kenh, ma_video=ma_video, tieu_de=kh["tieu_de"],
                              caption=kh["caption"], nen_tang=job["nen_tang_dich"], brand=brand,
                              diem_qa=str(kq.diem_qa if kq.diem_qa is not None else ""), canh_bao=kq.canh_bao,
                              thu_muc_xuat=P / "exports", goc=goc, thong_tin_them={"du_an": f"projects/{ma_video}"},
                              cot_them=cot_them)
        if hq.loi:
            raise RuntimeError("không đưa được vào Hàng chờ: " + "; ".join(hq.loi))
        kq.canh_bao = hq.canh_bao
        if kh["thieu_canh"]:  # cảnh tạm: vẫn giữ yêu cầu quay để thay sau (lệnh thay-canh)
            kq.thieu_canh = kh["thieu_canh"]
            ghi_can_quay(bang, kenh, ma, ma_video, kh["thieu_canh"])
            job.setdefault("metadata", {})["canh_tam"] = [t["doan"] for t in kh["thieu_canh"]]
        job = chuyen_trang_thai(job, "cho_duyet", ly_do=f"QA {kq.diem_qa}")
        _luu_job(P, job)
        _cap_nhat_y_tuong(bang, kenh, ma, NHAN_TRANG_THAI["cho_duyet"], kq.diem_qa)
        kq.trang_thai = "cho_duyet"
        cap_nhat_su_dung_an_toan(kenh, goc, log)
        return kq
    except Exception as e:  # job hỏng: ghi lỗi, không ném ra ngoài
        kq.trang_thai, kq.loi = "loi", f"{type(e).__name__}: {e}"[:800]
        try:
            job = chuyen_trang_thai(job, "loi", loi=kq.loi)
            _luu_job(P, job)
            _cap_nhat_y_tuong(bang, kenh, ma, NHAN_TRANG_THAI["loi"])
        except Exception as e2:  # pragma: no cover
            kq.loi += f" | không cập nhật được trạng thái: {e2}"
        return kq
    finally:
        kq.giay = round(time.monotonic() - t0, 1)
        try:
            them_nhat_ky(bang, NHAT_KY, [{
                "thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": ma_video, "buoc": "san_xuat", "che_do": "that",
                "ket_qua": "ok" if kq.trang_thai in ("cho_duyet", "cho_quay") else "loi",
                "chi_tiet": (f"{kq.trang_thai}; QA {kq.diem_qa}; kịch bản {_kb(kq)}; vòng sửa {kq.vong}; "
                             f"agent {kq.giay_agent:.0f}s "
                             f"(claude báo {kq.chi_phi_agent_usd:.2f} USD); "
                             f"{'; '.join(kq.canh_bao)} {kq.loi}")[:500],
                "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kq.giay), "so_luot_tro_ly": str(kq.so_luot_agent)}])
        except Exception as e:  # pragma: no cover
            log(f"  ! không ghi được Nhật ký: {e}")


def san_xuat(bang: BangNguon, kenh: str, so_luong: int, *, goc: Path = GOC, log: Callable[[str], None] = print,
             ca_cho_quay: bool = False, ca_loi: bool = False, **kw) -> list[KetQuaJob]:
    tu_choi: list[dict] = []
    ds = chon_chu_de(bang, kenh, so_luong, goc, ca_cho_quay, ca_loi, tu_choi=tu_choi)
    for r in tu_choi:
        log(f"Từ chối {r['ma']}: nguồn {r['_nguon']!r} chưa tới mức khoản")
    if tu_choi:
        ghi_theo_khoa(bang, Y_TUONG, [{"kenh": kenh, "ma": r["ma"], "ghi_chu_may": LY_DO_THIEU_NGUON} for r in tu_choi])
    if not ds:
        log("Không có chủ đề nào đã chọn 'Làm' mà chưa sản xuất.")
        return []
    tien_to, so = so_tiep_theo(kenh, goc)
    ket_qua = []
    i_moi = 0
    for cd in ds:
        if cd.get("_ma_video"):
            ma_video = cd["_ma_video"]
        else:
            ma_video = f"{tien_to}-{so + i_moi:03d}-{cd['ma']}"
            i_moi += 1
        log(f"== {ma_video}: {cd.get('chu_de')}")
        kq = san_xuat_mot(bang, cd, ma_video, goc=goc, log=log, **kw)
        log(f"   -> {kq.trang_thai} | QA {kq.diem_qa} | kịch bản {_kb(kq)} | {kq.giay:.0f}s | "
            f"{'; '.join(kq.canh_bao)} {kq.loi}")
        ket_qua.append(kq)
    return ket_qua
