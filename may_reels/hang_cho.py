"""Đưa video vào tab Hàng chờ để người duyệt.

- Bản xem thử: bản NHẸ (san-xuat.yaml xem_thu: 720x1280, CRF 28, AAC 96k) chép vào MAY_REELS_XEM_THU_DIR (thư mục
  đồng bộ của Google Drive for desktop), tên file = mã video (+ -v<n> khi sửa); bản cũ của cùng mã bị xóa.
  Bản trên Drive chỉ để duyệt. Bản đăng (chất lượng đầy đủ) ở thư mục exports/ trên máy.
  Không dùng Drive API, không dùng service account. link_xem_thu = tên file (+ link thư mục MAY_REELS_XEM_THU_LINK nếu có).
  Thiếu MAY_REELS_XEM_THU_DIR: link_xem_thu = đường dẫn file trên máy, kèm cảnh báo.
- Mỗi nền tảng một dòng: link_xem_thu, caption, hashtag, diem_qa, canh_bao, duyet = "Chờ duyệt" (ngoại lệ khoi_tao,
  NGUYEN-TAC.md mục 2). Cột trạng thái đăng để trống.
- export_bundle đóng gói thư mục đăng tay (video + description.txt) cho từng nền tảng; đường dẫn ghi vào ghi_chu_may.
- Lưu bản ghi local projects/_may_reels/hang_cho/<ma_video>.json (file, sha1) để khâu đăng kiểm tra đúng bản đã duyệt.
- Không đổi nội dung dòng đã được người xử lý (duyet khác trống/Chờ duyệt, hoặc đã có trạng thái đăng).

Lệnh: python -m may_reels hang-cho them --video <mp4> --kenh <mã> --caption-file <txt> [--ma <mã video>]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from may_reels.cot_sheet import HANG_CHO, NEN_TANG
from may_reels.kiem_tra_video import cum_tu_cam, do_thong_so, loi_thong_so, tim_cum_tu_cam
from may_reels.sheet import GIA_TRI_CHO, BangNguon, chuan, doc_dong, ghi_theo_khoa

GOC = Path(__file__).resolve().parent.parent
MA_VIDEO = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
KHOA_HASHTAG = {"fb_reels": "facebook", "yt_shorts": "youtube", "tiktok": "tiktok"}
CANH_BAO_CO_SAN = "Video có sẵn, chưa qua chấm điểm QA"
DUYET_CHO = {"", GIA_TRI_CHO}
BIEN_XEM_THU_DIR = "MAY_REELS_XEM_THU_DIR"
BIEN_XEM_THU_LINK = "MAY_REELS_XEM_THU_LINK"


class LoiHangCho(ValueError):
    pass


def thu_muc_ban_ghi(goc: Path | None = None) -> Path:
    return (goc or GOC) / "projects" / "_may_reels" / "hang_cho"


def sha1_file(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def tao_ma(ten: str) -> str:
    s = unicodedata.normalize("NFD", ten).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def hashtag_cua(brand: dict, nen_tang: str) -> list[str]:
    return [h for h in (brand.get("hashtags") or {}).get(KHOA_HASHTAG[nen_tang], []) if h]


def doc_ban_ghi(ma_video: str, goc: Path | None = None) -> dict | None:
    p = thu_muc_ban_ghi(goc) / f"{ma_video}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _bien(ten: str) -> str:
    return os.environ.get(ten, "").strip().strip('"').strip("'")


XEM_THU_MAC_DINH = {"rong": 720, "cao": 1280, "crf": 28, "am_thanh_kbps": 96}


def cau_hinh_xem_thu(kenh: str, goc: Path | None = None) -> dict:
    """san-xuat.yaml mục xem_thu; kênh chưa có file (video đưa vào bằng hang-cho them) thì dùng mặc định."""
    try:
        from may_reels.dung.ke_hoach import doc_san_xuat
        return {**XEM_THU_MAC_DINH, **(doc_san_xuat(kenh, goc).get("xem_thu") or {})}
    except (FileNotFoundError, ImportError):
        return dict(XEM_THU_MAC_DINH)


def nen_xem_thu(src: Path, dst: Path, cfg: dict) -> None:
    """Bản nhẹ chỉ để duyệt: 720x1280, CRF 28, AAC 96k. Bản đăng giữ nguyên trên máy (exports/)."""
    import subprocess
    w, h = int(cfg["rong"]), int(cfg["cao"])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,"
                    "format=yuv420p", "-c:v", "libx264", "-crf", str(int(cfg["crf"])), "-preset", "medium",
                    "-c:a", "aac", "-b:a", f"{int(cfg['am_thanh_kbps'])}k", "-movflags", "+faststart", str(dst)],
                   check=True)


def ban_xem_thu_cu(thu_muc: Path, ma_video: str, giu: str) -> list[Path]:
    """Các bản xem thử khác của cùng mã video: <ma>.mp4 hoặc <ma>-v<n>.mp4 (không bắt nhầm mã dài hơn)."""
    mau = re.compile(re.escape(ma_video) + r"(-v\d+)?\.mp4", re.IGNORECASE)
    return [f for f in thu_muc.iterdir() if f.is_file() and f.name != giu and mau.fullmatch(f.name)]


def chep_xem_thu(video: Path, ma_video: str, *, phien_ban: str = "", cfg: dict | None = None) -> tuple[str, list[str]]:
    """Nén bản xem thử nhẹ vào thư mục đồng bộ Drive, xóa bản cũ của cùng mã. Trả về (link_xem_thu, cảnh báo)."""
    d = _bien(BIEN_XEM_THU_DIR)
    if not d:
        return str(video), [f"Chưa đặt {BIEN_XEM_THU_DIR}: link_xem_thu là đường dẫn trên máy"]
    thu_muc = Path(d)
    if not thu_muc.is_dir():
        return str(video), [f"{BIEN_XEM_THU_DIR} không tồn tại ({thu_muc}): link_xem_thu là đường dẫn trên máy"]
    ten = f"{ma_video}{phien_ban}.mp4"
    # Nén ra file tạm cạnh video gốc rồi mới chép vào Drive: Drive không đồng bộ một file đang ghi dở.
    tam = video.with_name(f".xem-thu-{ma_video}.mp4")
    try:
        nen_xem_thu(video, tam, cfg or dict(XEM_THU_MAC_DINH))
        shutil.copyfile(tam, thu_muc / ten)
    finally:
        tam.unlink(missing_ok=True)
    canh_bao = []
    for f in ban_xem_thu_cu(thu_muc, ma_video, ten):
        try:
            f.unlink()
        except OSError as e:
            canh_bao.append(f"Không xóa được bản xem thử cũ {f.name}: {e}")
    link = _bien(BIEN_XEM_THU_LINK)
    return (f"{ten} — {link}" if link else ten), canh_bao


def lien_ket_video(thu_muc_xuat: Path, video: Path) -> None:
    """export_bundle chép video vào bundle: thay bản chép bằng hard link tới bản gốc (cùng nội dung, không tốn ổ đĩa).

    Mỗi video ~150 MB; không liên kết thì một video tốn 4-5 bản trên ổ. Ổ không hỗ trợ hard link thì giữ bản chép.
    """
    for f in thu_muc_xuat.glob("video/*"):
        if not f.is_file() or f.stat().st_size != video.stat().st_size:
            continue
        try:
            if os.path.samefile(f, video):
                continue
            tam = f.with_name(f.name + ".lienket")
            os.link(video, tam)
            os.replace(tam, f)
        except OSError:
            pass


def go_lien_ket_cu(thu_muc_xuat: Path, video: Path) -> None:
    """Trước khi đóng gói lại: gỡ hard link cũ trỏ tới chính video (export_bundle không chép đè được lên nó)."""
    for f in thu_muc_xuat.glob("video/*"):
        try:
            if f.is_file() and os.path.samefile(f, video):
                f.unlink()
        except OSError:
            pass


def dong_goi(video: Path, *, ma_video: str, tieu_de: str, mo_ta: str, hashtags: list[str], nen_tang: str,
             thu_muc: Path) -> Path:
    """export_bundle: thư mục đăng tay cho một nền tảng (video + description.txt)."""
    from tools.publishers.export_bundle import ExportBundle
    go_lien_ket_cu(Path(thu_muc), Path(video))
    res = ExportBundle().execute({"video_path": str(video), "title": tieu_de, "project_name": ma_video,
                                  "export_dir": str(thu_muc), "description": mo_ta, "hashtags": hashtags,
                                  "platform": nen_tang})
    if not res.success:
        raise LoiHangCho(f"export_bundle lỗi: {res.error}")
    lien_ket_video(Path(res.data["export_path"]), Path(video))
    return Path(res.data["export_path"])


@dataclass
class KetQuaThem:
    ma_video: str
    nen_tang: list[str]
    link_xem_thu: str = ""
    loi: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)
    them: int = 0
    cap_nhat: int = 0
    giu_nguyen: int = 0


def dua_vao_hang_cho(bang: BangNguon, *, video: Path, kenh: str, ma_video: str, tieu_de: str, caption: dict[str, str],
                     nen_tang: list[str], brand: dict, diem_qa: str = "", canh_bao: list[str] | None = None,
                     thu_muc_xuat: Path | None = None, thu: bool = False, goc: Path | None = None,
                     do=None, thong_tin_them: dict | None = None, phien_ban: str = "",
                     cho_phep_cap_nhat_duyet: bool = False, ban_moi: bool = False) -> KetQuaThem:
    """Kiểm tra rồi đưa video vào Hàng chờ. Có lỗi thì không ghi gì (kq.loi khác rỗng)."""
    goc = goc or GOC
    do = do or do_thong_so
    video = Path(video).resolve()
    kq = KetQuaThem(ma_video, list(nen_tang), canh_bao=list(canh_bao or []))
    if not MA_VIDEO.fullmatch(ma_video or ""):
        raise LoiHangCho(f"Mã video không hợp lệ: {ma_video!r}")
    if not video.is_file():
        raise LoiHangCho(f"Không thấy video: {video}")
    ts = do(video)
    cam = cum_tu_cam(brand)
    for x in nen_tang:
        kq.loi += loi_thong_so(ts, x)
        if not (caption.get(x) or "").strip():
            kq.loi.append(f"{x}: caption trống")
        trung = tim_cum_tu_cam((caption.get(x) or "") + "\n" + " ".join(hashtag_cua(brand, x)), cam)
        if trung:
            kq.loi.append(f"{x}: caption/hashtag chứa cụm từ cấm {trung}")
    sha = sha1_file(video)
    cu = doc_ban_ghi(ma_video, goc)
    if cu and cu.get("sha1") != sha and not (cho_phep_cap_nhat_duyet or ban_moi):
        kq.loi.append(f"Mã {ma_video} đã dùng cho một file khác (sha1 {cu.get('sha1', '')[:10]}). Dùng --ma khác.")
    # Chế độ sửa: chỉ được thay video khi KHÔNG còn nền tảng nào đang "Duyệt"/"Bỏ" của mã này; nếu không,
    # bản mới sẽ mang theo lời duyệt dành cho bản cũ.
    duoc_phep = DUYET_CHO | ({"Sửa"} if cho_phep_cap_nhat_duyet else set())
    da_xu_ly = [d["nen_tang"] for d in doc_dong(bang, HANG_CHO)
                if d.get("ma_video") == ma_video
                and (d.get("nen_tang") in nen_tang or cho_phep_cap_nhat_duyet)
                and (chuan(d.get("trang_thai_dang")) or chuan(d.get("duyet")) not in duoc_phep)]
    if da_xu_ly:
        kq.loi.append(f"Dòng {ma_video} trên {da_xu_ly} đã được duyệt, bỏ hoặc đã xử lý: không đổi nội dung "
                      f"(đặt các dòng đó về Sửa nếu muốn sửa cả video)")
    if kq.loi:
        return kq

    if thu:
        kq.link_xem_thu = "(chạy thử: chưa chép bản xem thử)"
        dong = [{"ma_video": ma_video, "kenh": kenh, "nen_tang": x} for x in nen_tang]
        kgt = ghi_theo_khoa(bang, HANG_CHO, dong, thu=True)
        kq.them, kq.cap_nhat, kq.giu_nguyen = len(kgt.them), len(kgt.cap_nhat), len(kgt.giu_nguyen)
        return kq

    kq.link_xem_thu, cb = chep_xem_thu(video, ma_video, phien_ban=phien_ban, cfg=cau_hinh_xem_thu(kenh, goc))
    kq.canh_bao += cb
    thu_muc_xuat = thu_muc_xuat or (goc / "projects" / "_may_reels" / "xuat" / ma_video)
    dong = []
    for x in nen_tang:
        tags = hashtag_cua(brand, x)
        xuat = dong_goi(video, ma_video=ma_video, tieu_de=tieu_de, mo_ta=caption[x], hashtags=tags, nen_tang=x,
                        thu_muc=thu_muc_xuat / x)
        try:
            xuat_hien = xuat.resolve().relative_to(goc.resolve()).as_posix()
        except ValueError:
            xuat_hien = str(xuat)
        dong.append({"ma_video": ma_video, "kenh": kenh, "nen_tang": x, "link_xem_thu": kq.link_xem_thu,
                     "caption": caption[x], "hashtag": " ".join(tags), "diem_qa": str(diem_qa),
                     "canh_bao": "; ".join(kq.canh_bao), "duyet": GIA_TRI_CHO,
                     "ghi_chu_may": f"Thư mục đăng tay: {xuat_hien}"})
    ban_ghi = {"ma_video": ma_video, "kenh": kenh, "video": str(video), "sha1": sha, "nen_tang": list(nen_tang),
               "link_xem_thu": kq.link_xem_thu, "tieu_de": tieu_de,
               "thong_so": {"rong": ts.rong, "cao": ts.cao, "giay": ts.giay, "fps": ts.fps}, **(thong_tin_them or {})}
    p = thu_muc_ban_ghi(goc) / f"{ma_video}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ban_ghi, ensure_ascii=False, indent=2), encoding="utf-8")
    kgt = ghi_theo_khoa(bang, HANG_CHO, dong, ngoai_le_duyet="sua" if cho_phep_cap_nhat_duyet else "khoi_tao")
    kq.them, kq.cap_nhat, kq.giu_nguyen = len(kgt.them), len(kgt.cap_nhat), len(kgt.giu_nguyen)
    return kq


def them_video(bang: BangNguon, *, video: Path, kenh: str, caption_file: Path, ma: str | None = None,
               nen_tang: list[str] | None = None, thu: bool = False, goc: Path | None = None,
               do=None) -> KetQuaThem:
    """Lệnh `hang-cho them`: một video có sẵn, một caption dùng chung cho mọi nền tảng."""
    from may_reels.cau_hinh_dang import doc_cau_hinh_dang
    from may_reels.chu_de import doc_brand
    goc = goc or GOC
    if not Path(caption_file).is_file():
        raise LoiHangCho(f"Không thấy file caption: {caption_file}")
    brand = doc_brand(kenh, goc)
    nt = list(nen_tang or doc_cau_hinh_dang(kenh, goc).nen_tang or NEN_TANG)
    cap = unicodedata.normalize("NFC", Path(caption_file).read_text(encoding="utf-8")).strip()
    if not cap:
        raise LoiHangCho("Caption trống")
    ma_video = ma or tao_ma(Path(video).stem)
    tieu_de = next((x.strip() for x in cap.splitlines() if x.strip()), ma_video)[:100]
    return dua_vao_hang_cho(bang, video=Path(video), kenh=kenh, ma_video=ma_video, tieu_de=tieu_de,
                            caption={x: cap for x in nt}, nen_tang=nt, brand=brand, canh_bao=[CANH_BAO_CO_SAN],
                            thu=thu, goc=goc, do=do, thong_tin_them={"caption_file": str(Path(caption_file).resolve())})
