"""Dọn media theo trạng thái duyệt trên tab Hàng chờ.

    python -m may_reels don-dep [--that]

Mặc định CHẠY THỬ: in sẽ xóa gì và giải phóng bao nhiêu MB, không xóa gì. --that mới xóa, và ghi một dòng Nhật ký.

Luật (Sheet là nguồn sự thật, NGUYEN-TAC.md mục 2; máy chỉ ĐỌC cột duyet):
1. Mọi nền tảng của một mã video đều "Bỏ": xóa media của dự án projects/<mã> (kể cả renders/final.mp4, cache giọng,
   review/) và bản xem thử của mã đó trên Drive. Giữ ke_hoach.json, checkpoint, điểm và mọi file .json.
2. Mọi nền tảng đã có quyết định ("Duyệt"/"Bỏ"), ít nhất một "Duyệt", và lần cuối máy cập nhật dòng (cap_nhat_luc,
   thường là lúc đăng) cũ hơn san-xuat.yaml don_dep.giu_sau_duyet_ngay (mặc định 30) ngày: chỉ giữ renders/final.mp4
   và file .json; xóa phần media còn lại.
Không bao giờ: xóa gì của mã còn dòng "Chờ duyệt", "Sửa" hoặc ô trống (chưa có quyết định); xóa file ngoài
projects/<mã>/ và thư mục xem thử; đụng thư mục kênh gốc ($KENH_GOC_DIR). "Media" = video, âm thanh, ảnh; file chữ
nhỏ (.html, .txt, .md) không tính.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from may_reels.cot_sheet import HANG_CHO, NHAT_KY
from may_reels.sheet import BangNguon, bay_gio_vn, chuan, doc_dong, them_nhat_ky

GOC = Path(__file__).resolve().parent.parent
MEDIA = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg",
         ".png", ".jpg", ".jpeg", ".webp", ".gif"}
NGAY_MAC_DINH = 30
MB = 1024 * 1024


@dataclass
class ViecDon:
    ma_video: str
    luat: str                      # "bo" | "qua_han"
    ly_do: str
    file: list[Path] = field(default_factory=list)
    xem_thu: list[Path] = field(default_factory=list)
    giai_phong: int = 0


def _ngay_giu(kenh: str, goc: Path) -> int:
    try:
        from may_reels.dung.ke_hoach import doc_san_xuat
        return int((doc_san_xuat(kenh, goc).get("don_dep") or {}).get("giu_sau_duyet_ngay", NGAY_MAC_DINH))
    except (FileNotFoundError, ImportError, ValueError):
        return NGAY_MAC_DINH


def _trong(p: Path, thu_muc: Path) -> bool:
    try:
        p.resolve().relative_to(thu_muc.resolve())
        return True
    except ValueError:
        return False


def _kenh_goc() -> Path | None:
    v = os.environ.get("KENH_GOC_DIR", "").strip().strip('"').strip("'")
    return Path(v) if v else None


def file_media(P: Path, giu: set[Path]) -> list[Path]:
    """File media trong dự án (không theo symlink), trừ các file trong `giu` và mọi .json."""
    giu_r = {g.resolve() for g in giu}
    ra = []
    for goc, _d, files in os.walk(P):
        for f in files:
            p = Path(goc) / f
            if p.is_symlink() or p.suffix.lower() not in MEDIA or p.resolve() in giu_r:
                continue
            ra.append(p)
    return sorted(ra)


def giai_phong(xoa: list[Path], giu: list[Path]) -> int:
    """Số byte thật được trả lại: một file hard link chỉ giải phóng khi mọi link đều bị xóa."""
    giu_ino = set()
    for g in giu:
        try:
            st = g.stat()
            if st.st_ino:
                giu_ino.add((st.st_dev, st.st_ino))
        except OSError:
            pass
    nhom: dict[tuple, list[os.stat_result]] = {}
    tong = 0
    for p in xoa:
        try:
            st = p.stat()
        except OSError:
            continue
        if not st.st_ino:
            tong += st.st_size
            continue
        nhom.setdefault((st.st_dev, st.st_ino), []).append(st)
    for k, ds in nhom.items():
        if k not in giu_ino and len(ds) >= ds[0].st_nlink:
            tong += ds[0].st_size
    return tong


def _moc(dong: list[dict]) -> datetime | None:
    moc = None
    for d in dong:
        try:
            t = datetime.strptime((d.get("cap_nhat_luc") or "").strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        moc = t if moc is None or t > moc else moc
    return moc


def lap_ke_hoach(bang: BangNguon, *, goc: Path = GOC, bay_gio: datetime | None = None,
                 thu_muc_xem_thu: Path | None = None) -> tuple[list[ViecDon], list[str]]:
    """Trả về (việc dọn, ghi chú các mã bỏ qua). Không xóa gì."""
    from may_reels.hang_cho import ban_xem_thu_cu
    bay_gio = bay_gio or datetime.strptime(bay_gio_vn(), "%Y-%m-%d %H:%M:%S")
    nhom: dict[str, list[dict]] = {}
    for d in doc_dong(bang, HANG_CHO):
        if d.get("ma_video"):
            nhom.setdefault(d["ma_video"], []).append(d)
    kg = _kenh_goc()
    viec, bo_qua = [], []
    for ma, dong in sorted(nhom.items()):
        duyet = [chuan(d.get("duyet")) for d in dong]
        P = goc / "projects" / ma
        co_du_an = P.is_dir() and _trong(P, goc / "projects") and P.name == ma and not ma.startswith("_")
        if kg and co_du_an and (_trong(P, kg) or _trong(kg, P)):
            bo_qua.append(f"{ma}: dự án trùng thư mục kênh gốc, không đụng")
            continue
        if all(x == "Bỏ" for x in duyet):
            v = ViecDon(ma, "bo", "mọi nền tảng 'Bỏ'")
            if co_du_an:
                v.file = file_media(P, set())
            if thu_muc_xem_thu and thu_muc_xem_thu.is_dir():
                v.xem_thu = ban_xem_thu_cu(thu_muc_xem_thu, ma, giu="")
            v.giai_phong = giai_phong(v.file + v.xem_thu, [])
        elif all(x in ("Duyệt", "Bỏ") for x in duyet) and "Duyệt" in duyet:
            if not co_du_an:
                continue
            ngay = _ngay_giu(dong[0].get("kenh", ""), goc)
            moc = _moc(dong)
            if moc is None or bay_gio - moc <= timedelta(days=ngay):
                continue
            final = P / "renders" / "final.mp4"
            v = ViecDon(ma, "qua_han", f"đã duyệt, cập nhật lần cuối {moc:%Y-%m-%d} (> {ngay} ngày)")
            v.file = file_media(P, {final})
            v.giai_phong = giai_phong(v.file, [final])
        else:
            bo_qua.append(f"{ma}: còn nền tảng chưa có quyết định ({', '.join(sorted(set(duyet)) or 'trống')})")
            continue
        # Lưới an toàn: chỉ xóa trong projects/<mã> và thư mục xem thử; không bao giờ trong thư mục kênh gốc.
        v.file = [f for f in v.file if co_du_an and _trong(f, P) and not (kg and _trong(f, kg))]
        v.xem_thu = [f for f in v.xem_thu if thu_muc_xem_thu and _trong(f, thu_muc_xem_thu)
                     and not (kg and _trong(f, kg))]
        if v.file or v.xem_thu:
            viec.append(v)
    return viec, bo_qua


def thuc_hien(viec: list[ViecDon]) -> tuple[int, list[str]]:
    """Xóa thật. Trả về (số file đã xóa, lỗi)."""
    n, loi = 0, []
    for v in viec:
        for f in v.file + v.xem_thu:
            try:
                f.unlink()
                n += 1
            except OSError as e:
                loi.append(f"{f}: {e}")
    return n, loi


def don_dep(bang: BangNguon, *, that: bool = False, goc: Path = GOC, bay_gio: datetime | None = None,
            thu_muc_xem_thu: Path | None = None, log: Callable[[str], None] = print) -> dict:
    import time
    from may_reels.dung_luong import thu_muc_xem_thu as tm_env
    t0 = time.monotonic()
    xt = thu_muc_xem_thu if thu_muc_xem_thu is not None else tm_env()
    viec, bo_qua = lap_ke_hoach(bang, goc=goc, bay_gio=bay_gio, thu_muc_xem_thu=xt)
    tien_to = "" if that else "[thử] "
    for v in viec:
        log(f"{tien_to}{v.ma_video} ({v.ly_do}): xóa {len(v.file)} file dự án + {len(v.xem_thu)} bản xem thử, "
            f"giải phóng {v.giai_phong / MB:.1f} MB")
    for b in bo_qua:
        log(f"   bỏ qua {b}")
    tong = sum(v.giai_phong for v in viec)
    kq = {"viec": viec, "bo_qua": bo_qua, "giai_phong": tong, "da_xoa": 0, "loi": []}
    if not that:
        log(f"[thử] Sẽ giải phóng {tong / MB:.1f} MB. Thêm --that để xóa thật.")
        return kq
    kq["da_xoa"], kq["loi"] = thuc_hien(viec)
    log(f"Đã xóa {kq['da_xoa']} file, giải phóng {tong / MB:.1f} MB" + (f", lỗi {len(kq['loi'])}" if kq["loi"] else ""))
    for x in kq["loi"]:
        log(f"   x {x}")
    chi_tiet = (f"giải phóng {tong / MB:.1f} MB, {kq['da_xoa']} file; " +
                "; ".join(f"{v.ma_video}:{v.luat}" for v in viec) +
                (f"; lỗi {len(kq['loi'])}" if kq["loi"] else ""))
    them_nhat_ky(bang, NHAT_KY, [{"thoi_gian": bay_gio_vn(), "kenh": "", "ma": "", "buoc": "don_dep", "che_do": "that",
                                  "ket_qua": "loi" if kq["loi"] else "ok", "chi_tiet": chi_tiet[:500], "chi_phi_vnd": "0",
                                  "thoi_gian_chay_giay": f"{time.monotonic() - t0:.1f}", "so_luot_tro_ly": "0"}])
    return kq
