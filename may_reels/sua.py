"""Sửa video theo ghi chú người duyệt: `python -m may_reels sua`.

Dòng Hàng chờ có duyet = "Sửa":
  1. Đọc ghi_chu_sua (mọi nền tảng của cùng mã video).
  2. Agent sửa ke_hoach.json hiện có theo ghi chú (bản cũ lưu ke_hoach.truoc-sua-<n>.json).
  3. Chỉ đổi caption -> không dựng lại. Đổi lời/thẻ/cảnh -> dựng lại mọi stage; giọng của đoạn không đổi lấy lại
     từ cache (assets/audio/_da_dat), nên chỉ sinh lại đoạn bị sửa.
  4. Cập nhật link_xem_thu (bản xem thử mới, tên có hậu tố -v<n>), caption, diem_qa, canh_bao;
     đưa duyet từ "Sửa" về "Chờ duyệt" — NGOẠI LỆ máy được ghi cột duyet (NGUYEN-TAC.md mục 2).
Video không có ke_hoach.json (đưa vào bằng `hang-cho them`) thì không sửa tự động được: ghi cảnh báo.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import HANG_CHO, NHAT_KY
from may_reels.job import chuyen_trang_thai
from may_reels.san_xuat import (GOC, MA_OK, SKILL, _luu_job, _yeu_cau, chay_dung, goi_agent)
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky


def sua(bang: BangNguon, *, goc: Path = GOC, agent: Callable[..., dict] = goi_agent,
        dung: Callable[..., tuple[int, dict]] = chay_dung, log: Callable[[str], None] = print) -> list[dict]:
    from may_reels.dung.ke_hoach import doc_brand, doc_san_xuat
    from may_reels.hang_cho import dua_vao_hang_cho
    nhom: dict[str, list[dict]] = {}
    for d in doc_dong(bang, HANG_CHO):
        if chuan(d.get("duyet")) == "Sửa":
            nhom.setdefault(d["ma_video"], []).append(d)
    ket_qua = []
    for ma_video, dong in nhom.items():
        t0 = time.monotonic()
        kq = {"ma_video": ma_video, "trang_thai": "loi", "loi": "", "giay": 0.0, "dung_lai": False}
        P = goc / "projects" / ma_video
        ghi_chu = "\n".join(f"[{d['nen_tang']}] {d.get('ghi_chu_sua', '').strip()}" for d in dong
                            if (d.get("ghi_chu_sua") or "").strip())
        try:
            if not (P / "ke_hoach.json").is_file() or not (P / "reel_job.json").is_file():
                raise RuntimeError("video không do máy sản xuất (không có ke_hoach.json): sửa tay rồi đưa lại vào hàng chờ")
            if not ghi_chu:
                raise RuntimeError("chọn Sửa nhưng ghi_chu_sua trống")
            job = json.loads((P / "reel_job.json").read_text(encoding="utf-8"))
            kenh = job["kenh"]
            brand, sx = doc_brand(kenh, goc), doc_san_xuat(kenh, goc)
            n = len(list(P.glob("ke_hoach.truoc-sua-*.json"))) + 1
            cu = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
            shutil.copyfile(P / "ke_hoach.json", P / f"ke_hoach.truoc-sua-{n}.json")
            job = chuyen_trang_thai(job, "dang_san_xuat", ly_do=f"Sửa lần {n}: {ghi_chu[:200]}")
            _luu_job(P, job)
            cd = next((c for c in brand.get("chu_de") or [] if c.get("ma") == job["ma_chu_de"]), {"ma": job["ma_chu_de"]})
            _yeu_cau(P, job, cd, brand, sx, None, ghi_chu, goc)
            ra = agent(f"Đọc và làm đúng theo {SKILL}, phần 'Vòng sửa' cho lệnh sua. Dự án: projects/{ma_video}. "
                       f"Đọc projects/{ma_video}/yeu_cau.json (mục ghi_chu_sua) và SỬA projects/{ma_video}/ke_hoach.json.",
                       du_an=P, goc=goc)
            if ra.get("is_error"):
                raise RuntimeError(f"agent lỗi: {str(ra.get('result'))[:300]}")
            moi = json.loads((P / "ke_hoach.json").read_text(encoding="utf-8"))
            chi_caption = {k: v for k, v in cu.items() if k != "caption"} == {k: v for k, v in moi.items() if k != "caption"}
            tom = {}
            if not chi_caption:
                kq["dung_lai"] = True
                ma_thoat, tom = dung(ma_video, goc=goc, stages=["idea", "script", "scene_plan", "assets", "edit",
                                                               "compose", "publish"])
                if ma_thoat != MA_OK:
                    raise RuntimeError(f"dựng lại lỗi ({ma_thoat}): {tom.get('loi', '')}")
            canh_bao = list(tom.get("canh_bao") or []) + [f"Đã sửa theo ghi chú lần {n} ({bay_gio_vn()})"]
            diem = tom.get("diem_qa")
            if diem is None:
                c = json.loads((P / "checkpoint_compose.json").read_text(encoding="utf-8"))
                diem = c["artifacts"]["final_review"]["metadata"].get("diem_qa")
            hq = dua_vao_hang_cho(bang, video=P / "renders" / "final.mp4", kenh=kenh, ma_video=ma_video,
                                  tieu_de=moi["tieu_de"], caption=moi["caption"], nen_tang=job["nen_tang_dich"],
                                  brand=brand, diem_qa=str(diem if diem is not None else ""), canh_bao=canh_bao,
                                  thu_muc_xuat=P / "exports", goc=goc, phien_ban=f"-v{n + 1}",
                                  cho_phep_cap_nhat_duyet=True, thong_tin_them={"du_an": f"projects/{ma_video}"})
            if hq.loi:
                raise RuntimeError("; ".join(hq.loi))
            job = chuyen_trang_thai(job, "cho_duyet", ly_do=f"Đã sửa lần {n}")
            _luu_job(P, job)
            kq["trang_thai"] = "cho_duyet"
        except Exception as e:
            kq["loi"] = f"{type(e).__name__}: {e}"[:500]
            try:
                ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": ma_video, "nen_tang": d["nen_tang"],
                                                "loi": f"Sửa tự động không được: {kq['loi']}"} for d in dong])
            except Exception:  # pragma: no cover
                pass
        kq["giay"] = round(time.monotonic() - t0, 1)
        log(f"{ma_video}: {kq['trang_thai']} {'(dựng lại)' if kq['dung_lai'] else ''} {kq['loi']}")
        try:
            them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": bay_gio_vn(), "kenh": "", "ma": ma_video, "buoc": "sua",
                                         "che_do": "that", "ket_qua": "ok" if kq["trang_thai"] == "cho_duyet" else "loi",
                                         "chi_tiet": (kq["loi"] or ("dựng lại" if kq["dung_lai"] else "chỉ sửa caption"))[:500],
                                         "chi_phi_vnd": "0", "thoi_gian_chay_giay": str(kq["giay"]),
                                         "so_luot_tro_ly": "1"}])
        except Exception:  # pragma: no cover
            pass
        ket_qua.append(kq)
    if not nhom:
        log("Không có dòng nào chọn 'Sửa'.")
    return ket_qua
