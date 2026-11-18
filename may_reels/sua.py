"""Làm lại video đã ở Hàng chờ.

`python -m may_reels sua`: dòng Hàng chờ có duyet = "Sửa".
  1. Đọc ghi_chu_sua (mọi nền tảng của cùng mã video).
  2. Agent sửa ke_hoach.json hiện có theo ghi chú (bản cũ lưu ke_hoach.truoc-sua-<n>.json).
  3. Chỉ đổi caption -> không dựng lại. Đổi lời/thẻ/cảnh -> dựng lại mọi stage; giọng của đoạn không đổi lấy lại
     từ cache (assets/audio/_da_dat), nên chỉ sinh lại đoạn bị sửa.
  4. Cập nhật link_xem_thu (bản xem thử mới, hậu tố -v<n>), caption, diem_qa, canh_bao;
     đưa duyet từ "Sửa" về "Chờ duyệt" — NGOẠI LỆ máy được ghi cột duyet (NGUYEN-TAC.md mục 2).

`python -m may_reels thay-canh`: dòng Cần quay có trang_thai_quay = "Đã quay" (và trang_thai_nap còn trống).
  Agent thay cảnh tạm (sơ đồ) bằng cảnh thật mới trong kho (chạy tools_local/nap_kenh.py trước), máy dựng lại và
  cập nhật Hàng chờ. Không đổi ô duyet. Nền tảng nào đã "Duyệt"/"Bỏ" thì không thay video (lời duyệt là cho bản cũ).
  Agent không tìm được cảnh khớp -> giữ sơ đồ, ghi trang_thai_nap để người biết.

Video không có ke_hoach.json (đưa vào bằng `hang-cho them`) thì không làm lại tự động được: ghi lỗi lên dòng.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import CAN_QUAY, HANG_CHO, NHAT_KY
from may_reels.job import chuyen_trang_thai
from may_reels.san_xuat import (GOC, MA_OK, SKILL, _luu_job, _yeu_cau, canh_bao_duoi_nguong, cap_nhat_su_dung_an_toan,
                                cham_mac_dinh, chay_dung, goi_agent, nhat_ky_cham)
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky

TAT_CA_STAGE = ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"]


def _lam_lai(bang: BangNguon, ma_video: str, ghi_chu: str, *, che_do: str, goc: Path, agent, dung, log,
             cham=None) -> dict:
    """che_do: 'sua' hoặc 'thay_canh'. Trả về {trang_thai, loi, dung_lai, doi}."""
    from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat
    from may_reels.hang_cho import dua_vao_hang_cho
    kq = {"ma_video": ma_video, "trang_thai": "loi", "loi": "", "dung_lai": False, "doi": True}
    P = goc / "projects" / ma_video
    if not (P / "ke_hoach.json").is_file() or not (P / "reel_job.json").is_file():
        raise RuntimeError("video không do máy sản xuất (không có ke_hoach.json): sửa tay rồi đưa lại vào hàng chờ")
    job = json.loads((P / "reel_job.json").read_text(encoding="utf-8"))
    kenh = job["kenh"]
    brand, sx = doc_brand(kenh, goc), doc_san_xuat(kenh, goc)
    n = len(list(P.glob("ke_hoach.truoc-sua-*.json"))) + 1
    cu = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
    shutil.copyfile(P / "ke_hoach.json", P / f"ke_hoach.truoc-sua-{n}.json")
    cd = next((c for c in brand.get("chu_de") or [] if c.get("ma") == job["ma_chu_de"]), {"ma": job["ma_chu_de"]})
    _yeu_cau(P, job, cd, brand, sx, None, ghi_chu, goc)
    phan = "'Vòng sửa' cho lệnh sua" if che_do == "sua" else "'Vòng sửa' cho lệnh thay-canh"
    ra = agent(f"Đọc và làm đúng theo {SKILL}, phần {phan}. Dự án: projects/{ma_video}. "
               f"Đọc projects/{ma_video}/yeu_cau.json (mục ghi_chu_sua) và SỬA projects/{ma_video}/ke_hoach.json.",
               du_an=P, goc=goc)
    if ra.get("is_error"):
        raise RuntimeError(f"agent lỗi: {str(ra.get('result'))[:300]}")
    moi = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
    if moi == cu:
        (P / f"ke_hoach.truoc-sua-{n}.json").unlink()
        kq.update(trang_thai="khong_doi", doi=False)
        return kq
    job = chuyen_trang_thai(job, "dang_san_xuat", ly_do=f"{che_do} lần {n}: {ghi_chu[:200]}")
    _luu_job(P, job)
    chi_caption = {k: v for k, v in cu.items() if k != "caption"} == {k: v for k, v in moi.items() if k != "caption"}
    tom: dict = {}
    if not chi_caption:
        kq["dung_lai"] = True
        ma_thoat, tom = dung(ma_video, goc=goc, stages=TAT_CA_STAGE)
        if ma_thoat != MA_OK:
            job = chuyen_trang_thai(job, "loi", loi=f"dựng lại lỗi ({ma_thoat}): {tom.get('loi', '')}"[:500])
            _luu_job(P, job)
            raise RuntimeError(f"dựng lại lỗi ({ma_thoat}): {tom.get('loi', '')}")
    nhan = "Đã sửa theo ghi chú" if che_do == "sua" else "Đã thay cảnh tạm bằng cảnh thật"
    kc = (cham or cham_mac_dinh)(ma_video, goc=goc, log=log, tom=tom)
    nhat_ky_cham(bang, kenh, ma_video, kc)
    if kc.chan:
        job = chuyen_trang_thai(job, "loi", loi=("Chặn cứng: " + "; ".join(kc.chan))[:500])
        _luu_job(P, job)
        raise RuntimeError("Chặn cứng: " + "; ".join(kc.chan))
    diem = kc.diem_qa
    nguong = int((sx.get("cham_diem") or {}).get("nguong", 75))
    canh_bao = ((canh_bao_duoi_nguong(kc, nguong) if diem is not None and diem < nguong else [])
                + list(kc.canh_bao) + list(tom.get("canh_bao") or []) + [f"{nhan} lần {n} ({bay_gio_vn()})"])
    hq = dua_vao_hang_cho(bang, video=P / "renders" / "final.mp4", kenh=kenh, ma_video=ma_video, tieu_de=moi["tieu_de"],
                          caption=moi["caption"], nen_tang=job["nen_tang_dich"], brand=brand,
                          diem_qa=str(diem if diem is not None else ""), canh_bao=canh_bao, thu_muc_xuat=P / "exports",
                          goc=goc, phien_ban=f"-v{n + 1}", cho_phep_cap_nhat_duyet=(che_do == "sua"), ban_moi=True,
                          thong_tin_them={"du_an": f"projects/{ma_video}"})
    if hq.loi:
        raise RuntimeError("; ".join(hq.loi))
    job.setdefault("metadata", {})["canh_tam"] = [t["doan"] for t in moi["thieu_canh"]]
    job = chuyen_trang_thai(job, "cho_duyet", ly_do=f"{nhan} lần {n}")
    _luu_job(P, job)
    kq["trang_thai"] = "cho_duyet"
    cap_nhat_su_dung_an_toan(kenh, goc, log)
    return kq


def _nhat_ky(bang, buoc: str, kq: dict) -> None:
    try:
        them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": bay_gio_vn(), "kenh": "", "ma": kq["ma_video"], "buoc": buoc,
                                     "che_do": "that", "ket_qua": "loi" if kq["trang_thai"] == "loi" else "ok",
                                     "chi_tiet": (kq["loi"] or kq["trang_thai"] + (" (dựng lại)" if kq["dung_lai"] else ""))[:500],
                                     "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kq["giay"]), "so_luot_tro_ly": "1"}])
    except Exception:  # pragma: no cover
        pass


def sua(bang: BangNguon, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent,
        dung: Callable[..., tuple[int, dict]] = chay_dung, log: Callable[[str], None] = print,
        cham: Callable | None = None) -> list[dict]:
    nhom: dict[str, list[dict]] = {}
    for d in doc_dong(bang, HANG_CHO):
        if chuan(d.get("duyet")) == "Sửa":
            nhom.setdefault(d["ma_video"], []).append(d)
    ket_qua = []
    for ma_video, dong in nhom.items():
        t0 = time.monotonic()
        ghi_chu = "\n".join(f"[{d['nen_tang']}] {d.get('ghi_chu_sua', '').strip()}" for d in dong
                            if (d.get("ghi_chu_sua") or "").strip())
        try:
            if not ghi_chu:
                raise RuntimeError("chọn Sửa nhưng ghi_chu_sua trống")
            kq = _lam_lai(bang, ma_video, ghi_chu, che_do="sua", goc=goc, agent=agent, dung=dung, log=log, cham=cham)
        except Exception as e:
            kq = {"ma_video": ma_video, "trang_thai": "loi", "loi": f"{type(e).__name__}: {e}"[:500], "dung_lai": False}
            try:
                ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": ma_video, "nen_tang": d["nen_tang"],
                                                "loi": f"Sửa tự động không được: {kq['loi']}"} for d in dong])
            except Exception:  # pragma: no cover
                pass
        kq["giay"] = round(time.monotonic() - t0, 1)
        log(f"{ma_video}: {kq['trang_thai']} {'(dựng lại)' if kq['dung_lai'] else ''} {kq['loi']}")
        _nhat_ky(bang, "sua", kq)
        ket_qua.append(kq)
    if not nhom:
        log("Không có dòng nào chọn 'Sửa'.")
    return ket_qua


def thay_canh(bang: BangNguon, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent,
              dung: Callable[..., tuple[int, dict]] = chay_dung, log: Callable[[str], None] = print,
              cham: Callable | None = None) -> list[dict]:
    nhom: dict[str, list[dict]] = {}
    for d in doc_dong(bang, CAN_QUAY):
        if chuan(d.get("trang_thai_quay")) == "Đã quay" and not chuan(d.get("trang_thai_nap")) and d.get("ma_video"):
            nhom.setdefault(d["ma_video"], []).append(d)
    ket_qua = []
    for ma_video, dong in nhom.items():
        t0 = time.monotonic()
        ghi_chu = ("Người dùng đã quay bổ sung và nạp lại kho cảnh. Thay cảnh tạm (so_do) bằng cảnh thật mới trong kho_canh "
                   "cho các đoạn sau; đoạn nào chưa có cảnh khớp thì giữ sơ đồ. Không đổi lời đọc.\n" +
                   "\n".join(f"- {d.get('ma_yeu_cau')}: {d.get('mo_ta_canh', '')}" +
                             (f" (ghi chú người: {d['ghi_chu_nguoi']})" if d.get("ghi_chu_nguoi") else "") for d in dong))
        try:
            kq = _lam_lai(bang, ma_video, ghi_chu, che_do="thay_canh", goc=goc, agent=agent, dung=dung, log=log,
                          cham=cham)
            nap = (f"đã thay vào {ma_video} ({bay_gio_vn()})" if kq["trang_thai"] == "cho_duyet"
                   else "chưa thấy cảnh mới khớp ý trong kho (đã chạy nap_kenh.py chưa?)")
        except Exception as e:
            kq = {"ma_video": ma_video, "trang_thai": "loi", "loi": f"{type(e).__name__}: {e}"[:500], "dung_lai": False}
            nap = f"lỗi: {kq['loi'][:200]}"
        try:
            ghi_theo_khoa(bang, CAN_QUAY, [{"ma_yeu_cau": d["ma_yeu_cau"], "trang_thai_nap": nap} for d in dong])
        except Exception:  # pragma: no cover
            pass
        kq["giay"] = round(time.monotonic() - t0, 1)
        log(f"{ma_video}: {kq['trang_thai']} {'(dựng lại)' if kq['dung_lai'] else ''} {kq['loi']}")
        _nhat_ky(bang, "thay_canh", kq)
        ket_qua.append(kq)
    if not nhom:
        log("Không có cảnh nào đánh dấu 'Đã quay' đang chờ thay.")
    return ket_qua
