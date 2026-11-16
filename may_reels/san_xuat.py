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


# ---------------------------------------------------------------- công cụ chạy ngoài
def goi_agent(prompt: str, *, du_an: Path, goc: Path = GOC, giay: int = GIAY_AGENT) -> dict:
    """claude -p không tương tác. Trả về JSON kết quả (result, num_turns, duration_ms, is_error...)."""
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError("Không thấy lệnh claude (Claude Code CLI)")
    rel = du_an.relative_to(goc).as_posix()
    cmd = [claude, "-p", prompt, "--output-format", "json", "--permission-mode", "dontAsk",
           "--allowed-tools", f"Read Glob Grep WebFetch WebSearch Write(./{rel}/ke_hoach.json) Edit(./{rel}/ke_hoach.json)",
           "--append-system-prompt", LOI_NHAC_HE_THONG, "--no-session-persistence"]
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


def chon_chu_de(bang: BangNguon, kenh: str, so_luong: int, goc: Path = GOC, ca_cho_quay: bool = False,
                ca_loi: bool = False) -> list[dict]:
    """Chủ đề "Làm" chưa sản xuất. ca_cho_quay: thêm chủ đề có job đang cho_quay (dựng lại với cảnh tạm)."""
    jobs = _jobs(goc)
    out = []
    for r in doc_dong(bang, Y_TUONG):
        if r.get("kenh") != kenh or chuan(r.get("duyet_chu_de")) != "Làm":
            continue
        j = jobs.get(r.get("ma"))
        if j:
            lam_lai = ({"cho_quay"} if ca_cho_quay else set()) | ({"loi"} if ca_loi else set())
            if j.get("trang_thai") not in lam_lai:
                continue
            r = {**r, "_ma_video": j["ma_video"]}
        elif chuan(r.get("trang_thai_san_xuat")) not in DA_SAN_XUAT:
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
             goc: Path) -> None:
    from may_reels.dung.pipeline import so_lan_dung_canh
    khung = next((k for k, v in (sx.get("khung_nhip") or {}).items() if v.get("tru_cot") == chu_de.get("tru_cot")),
                 next(iter(sx.get("khung_nhip") or {"": None})))
    yc = {"ma_video": job["ma_video"], "kenh": job["kenh"], "khung_nhip": khung,
          "chu_de": {k: chu_de.get(k) for k in ("ma", "tru_cot", "dinh_dang", "chu_de", "y_chinh", "nguon_doi_chieu")},
          "so_lan_dung_canh": so_lan_dung_canh(goc, job["kenh"], job["ma_video"]),
          "ngay_hom_nay": datetime.now(TZ_VN).date().isoformat()}
    if phan_hoi:
        yc["phan_hoi"] = phan_hoi
    if ghi_chu_sua:
        yc["ghi_chu_sua"] = ghi_chu_sua
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


def san_xuat_mot(bang: BangNguon, chu_de: dict, ma_video: str, *, goc: Path = GOC,
                 agent: Callable[..., dict] = goi_agent, dung: Callable[..., tuple[int, dict]] = chay_dung,
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
    nguong = int((sx.get("cham_diem") or {}).get("nguong", 75))
    so_vong = int((sx.get("cham_diem") or {}).get("so_vong_sua", 2))
    tom: dict = {}
    try:
        for vong in range(so_vong + 1):
            kq.vong = vong
            _yeu_cau(P, job, cd, brand, sx, phan_hoi, None, goc)
            prompt = (f"Đọc và làm đúng theo {SKILL}. Dự án: projects/{ma_video}. Đọc projects/{ma_video}/yeu_cau.json "
                      f"rồi viết projects/{ma_video}/ke_hoach.json." + (" Đây là vòng sửa: xem mục phan_hoi." if phan_hoi else ""))
            log(f"  [{ma_video}] agent vòng {vong}")
            ra = agent(prompt, du_an=P, goc=goc)
            kq.so_luot_agent += 1
            kq.giay_agent += (ra.get("duration_ms") or 0) / 1000
            kq.chi_phi_agent_usd += float(ra.get("total_cost_usd") or 0)
            if ra.get("is_error") or not (P / "ke_hoach.json").is_file():
                raise RuntimeError(f"agent không viết được ke_hoach.json: {str(ra.get('result'))[:300]}")
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
            kq.diem_qa = tom.get("diem_qa")
            kq.canh_bao = list(tom.get("canh_bao") or [])
            if kq.diem_qa is not None and kq.diem_qa < nguong:
                if vong < so_vong:
                    phan_hoi = f"Điểm QA {kq.diem_qa} < {nguong}. Bị trừ: {json.dumps(tom.get('tru_diem'), ensure_ascii=False)}"
                    log(f"  [{ma_video}] {phan_hoi}")
                    continue
                kq.canh_bao.append(CANH_BAO_DUOI_NGUONG)
            break

        kh = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
        hq = dua_vao_hang_cho(bang, video=P / "renders" / "final.mp4", kenh=kenh, ma_video=ma_video, tieu_de=kh["tieu_de"],
                              caption=kh["caption"], nen_tang=job["nen_tang_dich"], brand=brand,
                              diem_qa=str(kq.diem_qa if kq.diem_qa is not None else ""), canh_bao=kq.canh_bao,
                              thu_muc_xuat=P / "exports", goc=goc, thong_tin_them={"du_an": f"projects/{ma_video}"})
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
                "chi_tiet": (f"{kq.trang_thai}; QA {kq.diem_qa}; vòng sửa {kq.vong}; agent {kq.giay_agent:.0f}s "
                             f"(claude báo {kq.chi_phi_agent_usd:.2f} USD); "
                             f"{'; '.join(kq.canh_bao)} {kq.loi}")[:500],
                "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kq.giay), "so_luot_tro_ly": str(kq.so_luot_agent)}])
        except Exception as e:  # pragma: no cover
            log(f"  ! không ghi được Nhật ký: {e}")


def san_xuat(bang: BangNguon, kenh: str, so_luong: int, *, goc: Path = GOC, log: Callable[[str], None] = print,
             ca_cho_quay: bool = False, ca_loi: bool = False, **kw) -> list[KetQuaJob]:
    ds = chon_chu_de(bang, kenh, so_luong, goc, ca_cho_quay, ca_loi)
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
        log(f"   -> {kq.trang_thai} | QA {kq.diem_qa} | {kq.giay:.0f}s | {'; '.join(kq.canh_bao)} {kq.loi}")
        ket_qua.append(kq)
    return ket_qua
