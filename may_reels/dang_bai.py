"""Đăng bài từ tab Hàng chờ: `python -m may_reels dang [--that]`.

Python tất định, không gọi LLM. Không có --that thì chỉ in ra sẽ đăng gì: không gọi API
nền tảng, không ghi tab Hàng chờ (vẫn đọc Sheet và ghi một dòng Nhật ký).

Một dòng được đăng khi đủ tất cả:
  duyet == "Duyệt" (đúng chuỗi), trang_thai_dang trống hoặc "loi_thu_lai", id_bai trống,
  sổ đăng local chưa ghi nhận (ma_video, nen_tang), gio_dang đã đến (giờ Việt Nam; trống = ngay),
  cấu hình kênh đủ, chưa vượt giới hạn 24 giờ, file video khớp sha1 lúc đưa vào hàng chờ,
  file đúng thông số nền tảng, caption không chứa cụm từ cấm.

Chống đăng trùng:
  - đọc lại dòng ngay trước khi đăng; ghi "dang_tai_len" (cột cap_nhat_luc tự ghi thời điểm) trước khi tải lên;
  - thành công thì ghi sổ đăng local TRƯỚC, rồi mới ghi Sheet;
  - dòng kẹt ở "dang_tai_len" quá 30 phút -> "can_kiem_tra", không tự đăng lại;
  - lỗi ở bước cuối (bài có thể đã lên) -> "can_kiem_tra", không thử lại.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from may_reels.cau_hinh_dang import PHAM_VI_GIOI_HAN, CauHinhDang, LoiCauHinh, doc_cau_hinh_dang
from may_reels.chu_de import doc_brand
from may_reels.cot_sheet import HANG_CHO, NHAT_KY
from may_reels.hang_cho import doc_ban_ghi, sha1_file
from may_reels.khoa_tien_trinh import khoa
from may_reels.kiem_tra_video import cum_tu_cam, do_thong_so, loi_thong_so, tim_cum_tu_cam
from may_reels.sheet import BangNguon, chuan, doc_dong, ghi_theo_khoa, them_nhat_ky
from may_reels.so_dang import SoDang

GOC = Path(__file__).resolve().parent.parent
TZ_VN = timezone(timedelta(hours=7))

DUYET = "Duyệt"
TT_DANG_TAI_LEN = "dang_tai_len"
TT_DA_DANG = "da_dang"
TT_LOI = "loi"
TT_LOI_THU_LAI = "loi_thu_lai"
TT_CAN_KIEM_TRA = "can_kiem_tra"
TT_CHO_DANG_TAY = "cho_dang_tay"
TT_DUOC_DANG = {"", TT_LOI_THU_LAI}

PHUT_KET = 30
SO_LAN_THU_LAI_MANG = 2
CHO_THU_LAI_GIAY = (5, 15)
LOAI_THU_LAI_LAN_SAU = {"mang", "gioi_han"}


@dataclass
class KetQuaDang:
    thanh_cong: bool
    id_bai: str = ""
    link: str = ""
    visibility: str = ""
    loai_loi: str | None = None
    loi: str = ""
    ban_giao: bool = False  # TikTok: chỉ chép sang Drive, chưa đăng


CongCu = Callable[[dict], KetQuaDang]


@dataclass
class BaoCao:
    that: bool
    dong: list[str] = field(default_factory=list)
    da_dang: int = 0
    ban_giao: int = 0
    loi: int = 0
    se_dang: int = 0
    bo_qua: int = 0
    kiem_tra: int = 0

    def in_ra(self, s: str) -> None:
        self.dong.append(s)


# ---------------------------------------------------------------- thời gian
def bay_gio_vn() -> datetime:
    return datetime.now(TZ_VN)


def doc_gio_dang(s: str, bay_gio: datetime) -> datetime | None:
    """'' -> bay_gio. 'HH:MM' -> hôm nay. 'YYYY-MM-DD HH:MM[:SS]', 'DD/MM/YYYY HH:MM'. Sai định dạng -> None."""
    s = chuan(s)
    if not s:
        return bay_gio
    for dang in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, dang).replace(tzinfo=TZ_VN)
        except ValueError:
            pass
    try:
        t = datetime.strptime(s, "%H:%M")
        return bay_gio.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except ValueError:
        return None


def doc_luc(s: str) -> datetime | None:
    try:
        return datetime.strptime(chuan(s), "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_VN)
    except ValueError:
        return None


def chuoi_luc(t: datetime) -> str:
    return t.astimezone(TZ_VN).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- công cụ thật
def _tu_ket_qua_tool(res) -> KetQuaDang:
    entry = res.data["publish_log"]["entries"][0]
    if res.success:
        return KetQuaDang(True, entry.get("video_id", ""), entry.get("url") or entry.get("export_path", ""),
                          entry.get("visibility", ""), ban_giao=entry.get("status") == "exported")
    return KetQuaDang(False, entry.get("video_id", ""), "", "", res.data.get("loai_loi", "noi_dung"), res.error or "")


def cong_cu_that(ch: CauHinhDang) -> dict[str, CongCu]:
    def fb(yc: dict) -> KetQuaDang:
        from tools.publishers.facebook_reels import FacebookReels
        c = ch.fb_reels
        vao = {"video_path": yc["video_path"], "page_id": str(c["page_id"]), "token_env": c["bien_token"],
               "description": yc["mo_ta"], "hashtags": yc["hashtags"], "that": True}
        if c.get("is_ai_generated") is not None:
            vao["is_ai_generated"] = bool(c["is_ai_generated"])
        return _tu_ket_qua_tool(FacebookReels().execute(vao))

    def yt(yc: dict) -> KetQuaDang:
        from tools.publishers.youtube_shorts import YoutubeShorts
        c = ch.yt_shorts
        vao = {"video_path": yc["video_path"], "title": yc["tieu_de"], "description": yc["mo_ta"],
               "hashtags": yc["hashtags"], "channel_id": str(c["kenh_id"]), "token_file_env": c["bien_token_file"],
               "that": True}
        for khoa_cfg, khoa_vao in (("category_id", "category_id"), ("made_for_kids", "made_for_kids"),
                                   ("contains_synthetic_media", "contains_synthetic_media")):
            if c.get(khoa_cfg) not in (None, ""):
                vao[khoa_vao] = c[khoa_cfg]
        return _tu_ket_qua_tool(YoutubeShorts().execute(vao))

    def tt(yc: dict) -> KetQuaDang:
        from tools.publishers.tiktok_handoff import TiktokHandoff
        return _tu_ket_qua_tool(TiktokHandoff().execute({
            "video_path": yc["video_path"], "ma_video": yc["ma_video"], "caption": yc["mo_ta"],
            "hashtags": yc["hashtags"], "that": True}))

    return {"fb_reels": fb, "yt_shorts": yt, "tiktok": tt}


# ---------------------------------------------------------------- chạy
def _khoa_dong(d: dict) -> tuple[str, str]:
    return (d.get("ma_video", ""), d.get("nen_tang", ""))


def _ghi(bang: BangNguon, d: dict, **cot) -> None:
    ghi_theo_khoa(bang, HANG_CHO, [{"ma_video": d["ma_video"], "nen_tang": d["nen_tang"], **cot}])


def _kiem_noi_dung(d: dict, goc: Path, do) -> tuple[list[str], dict | None]:
    """Kiểm tra file và caption của một dòng. Trả về (lỗi, yêu cầu đăng)."""
    loi = []
    bg = doc_ban_ghi(d["ma_video"], goc)
    if not bg:
        return [f"không có bản ghi local cho {d['ma_video']} (đưa vào bằng `hang-cho them`)"], None
    video = Path(bg["video"])
    if not video.is_file():
        return [f"không thấy file video {video.name}"], None
    if sha1_file(video) != bg.get("sha1"):
        return ["file video đã đổi sau khi đưa vào hàng chờ (sha1 khác): không đăng bản chưa được duyệt"], None
    loi += loi_thong_so(do(video), d["nen_tang"])
    caption, hashtag = d.get("caption", ""), d.get("hashtag", "")
    trung = tim_cum_tu_cam(caption + "\n" + hashtag, cum_tu_cam(doc_brand(d["kenh"], goc)))
    if trung:
        loi.append(f"caption/hashtag chứa cụm từ cấm {trung}")
    if not caption.strip():
        loi.append("caption trống")
    dong_dau = next((x.strip() for x in caption.splitlines() if x.strip()), "")
    yc = {"ma_video": d["ma_video"], "video_path": str(video), "tieu_de": dong_dau,
          "mo_ta": caption.strip() + (("\n\n" + hashtag.strip()) if hashtag.strip() else ""),
          "hashtags": hashtag.split()}
    return loi, yc


def chay_dang(bang: BangNguon, *, that: bool = False, bay_gio: Callable[[], datetime] = bay_gio_vn,
              cong_cu: dict[str, CongCu] | None = None, so_dang: SoDang | None = None,
              file_khoa: Path | None = None, goc: Path | None = None, do=do_thong_so,
              ngu: Callable[[float], None] = time.sleep) -> BaoCao:
    goc = goc or GOC
    so_dang = so_dang or SoDang()
    file_khoa = file_khoa or (goc / "projects" / "_may_reels" / "dang.lock")
    bc = BaoCao(that)
    bat_dau = time.monotonic()
    with khoa(file_khoa):
        try:
            _chay(bang, bc, that, bay_gio, cong_cu, so_dang, goc, do, ngu)
            ket_qua = "loi" if bc.loi else "ok"
        except Exception as e:
            bc.in_ra(f"LỖI: {e}")
            ket_qua = "loi"
            raise
        finally:
            chi_tiet = (f"đăng {bc.da_dang}, bàn giao TikTok {bc.ban_giao}, lỗi {bc.loi}, cần kiểm tra {bc.kiem_tra}, "
                        f"bỏ qua {bc.bo_qua}" if that else f"chạy thử: sẽ đăng {bc.se_dang}, bỏ qua {bc.bo_qua}")
            try:
                them_nhat_ky(bang, NHAT_KY, [{
                    "thoi_gian": chuoi_luc(bay_gio()), "kenh": "", "ma": "", "buoc": "dang",
                    "che_do": "that" if that else "thu", "ket_qua": ket_qua, "chi_tiet": chi_tiet[:500],
                    "chi_phi_vnd": "0", "thoi_gian_chay_giay": f"{time.monotonic() - bat_dau:.1f}",
                    "so_luot_tro_ly": "0"}])
            except Exception as e:  # không để lỗi ghi nhật ký che lỗi chính
                bc.in_ra(f"! Không ghi được Nhật ký: {e}")
    return bc


def _chay(bang, bc: BaoCao, that, bay_gio, cong_cu, so_dang: SoDang, goc, do, ngu) -> None:
    bay = bay_gio()
    tien_to = "" if that else "[thử] "
    cau_hinh: dict[str, CauHinhDang | LoiCauHinh] = {}

    def ch_cua(kenh: str):
        if kenh not in cau_hinh:
            try:
                cau_hinh[kenh] = doc_cau_hinh_dang(kenh, goc)
            except LoiCauHinh as e:
                cau_hinh[kenh] = e
        return cau_hinh[kenh]

    dem_lan_nay: dict[tuple, int] = {}
    for d in doc_dong(bang, HANG_CHO):
        k = _khoa_dong(d)
        nhan = f"{k[0]}/{k[1]}"
        tt = chuan(d.get("trang_thai_dang"))
        so = so_dang.da_xu_ly(*k)

        # Sổ đăng nói đã đăng mà Sheet chưa ghi (lần trước ghi Sheet lỗi) -> sửa Sheet, không đăng lại.
        if so and so.get("loai") in ("dang", "ban_giao") and tt not in (TT_DA_DANG, TT_CHO_DANG_TAY, TT_CAN_KIEM_TRA):
            bc.in_ra(f"{tien_to}~ {nhan}: sổ đăng đã ghi nhận ({so.get('id_bai') or so.get('link')}), đồng bộ lại Sheet")
            if that:
                _ghi(bang, d, id_bai=so.get("id_bai", ""), link_bai=so.get("link", ""),
                     trang_thai_dang=TT_CHO_DANG_TAY if so.get("loai") == "ban_giao" else TT_DA_DANG)
            continue

        if tt == TT_DANG_TAI_LEN:
            luc = doc_luc(d.get("cap_nhat_luc", ""))
            if luc is None or bay - luc > timedelta(minutes=PHUT_KET):
                bc.kiem_tra += 1
                bc.in_ra(f"{tien_to}! {nhan}: kẹt ở {TT_DANG_TAI_LEN} từ {d.get('cap_nhat_luc') or '?'} -> {TT_CAN_KIEM_TRA}")
                if that:
                    _ghi(bang, d, trang_thai_dang=TT_CAN_KIEM_TRA,
                         loi=f"Kẹt ở {TT_DANG_TAI_LEN} quá {PHUT_KET} phút. Kiểm tra trên nền tảng xem bài đã lên chưa; "
                             f"chắc chắn chưa lên thì sửa ô này thành {TT_LOI_THU_LAI}.")
            continue

        if chuan(d.get("duyet")) != DUYET:
            continue
        if tt not in TT_DUOC_DANG:
            continue
        if chuan(d.get("id_bai")):
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: đã có id_bai, không bao giờ đăng lại")
            continue
        if so:
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: sổ đăng đã có mục '{so.get('loai')}', không đăng lại")
            continue
        gio = doc_gio_dang(d.get("gio_dang", ""), bay)
        if gio is None:
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: gio_dang '{d.get('gio_dang')}' sai định dạng (HH:MM hoặc YYYY-MM-DD HH:MM)")
            continue
        if gio > bay:
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: chờ tới {chuoi_luc(gio)}")
            continue
        ch = ch_cua(d.get("kenh", ""))
        if isinstance(ch, LoiCauHinh):
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: {ch}")
            continue
        if k[1] not in ch.nen_tang:
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: kênh {ch.kenh} không bật nền tảng {k[1]} trong dang-bai.yaml")
            continue
        thieu = ch.thieu(k[1])
        if thieu:
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: cấu hình chưa đủ: {', '.join(thieu)}")
            continue
        pham_vi = (k[1], ch.kenh) if PHAM_VI_GIOI_HAN[k[1]] == "kenh" else (k[1],)
        da = so_dang.dem_24h(k[1], ch.kenh if len(pham_vi) == 2 else None, bay) + dem_lan_nay.get(pham_vi, 0)
        if da >= ch.gioi_han(k[1]):
            bc.bo_qua += 1
            bc.in_ra(f"- {nhan}: đã đủ {ch.gioi_han(k[1])} bài/24 giờ cho {k[1]}, để lần chạy sau")
            continue

        loi, yc = _kiem_noi_dung(d, goc, do)
        if loi:
            bc.loi += 1
            bc.in_ra(f"{tien_to}x {nhan}: không đăng: {'; '.join(loi)}")
            if that:
                _ghi(bang, d, trang_thai_dang=TT_LOI, loi="; ".join(loi)[:500])
            continue

        if not that:
            bc.se_dang += 1
            dem_lan_nay[pham_vi] = dem_lan_nay.get(pham_vi, 0) + 1
            bc.in_ra(f"[thử] + {nhan}: SẼ {'bàn giao' if k[1] == 'tiktok' else 'đăng'} | {yc['tieu_de'][:60]}")
            continue

        _dang_mot(bang, bc, d, yc, ch, cong_cu, so_dang, bay_gio, ngu)
        dem_lan_nay[pham_vi] = dem_lan_nay.get(pham_vi, 0) + 1


def _dang_mot(bang, bc: BaoCao, d: dict, yc: dict, ch: CauHinhDang, cong_cu, so_dang: SoDang, bay_gio, ngu) -> None:
    k = _khoa_dong(d)
    nhan = f"{k[0]}/{k[1]}"
    # Đọc lại ngay trước khi đăng: người có thể vừa rút lại duyệt.
    moi = next((x for x in doc_dong(bang, HANG_CHO) if _khoa_dong(x) == k), None)
    if (not moi or chuan(moi.get("duyet")) != DUYET or chuan(moi.get("trang_thai_dang")) not in TT_DUOC_DANG
            or chuan(moi.get("id_bai"))):
        bc.bo_qua += 1
        bc.in_ra(f"- {nhan}: dòng vừa thay đổi trên Sheet, bỏ qua")
        return
    _ghi(bang, d, trang_thai_dang=TT_DANG_TAI_LEN, loi="")

    ham = (cong_cu or cong_cu_that(ch))[k[1]]
    kq = None
    for lan in range(SO_LAN_THU_LAI_MANG + 1):
        try:
            kq = ham(yc)
        except Exception as e:  # lỗi bất ngờ trong code: coi như không rõ bài đã lên chưa
            kq = KetQuaDang(False, loai_loi="khong_ro", loi=f"{type(e).__name__}: {e}")
        if kq.thanh_cong or kq.loai_loi != "mang" or lan == SO_LAN_THU_LAI_MANG:
            break
        bc.in_ra(f"  … {nhan}: lỗi mạng, thử lại lần {lan + 1}: {kq.loi[:120]}")
        ngu(CHO_THU_LAI_GIAY[min(lan, len(CHO_THU_LAI_GIAY) - 1)])

    luc = chuoi_luc(bay_gio())
    if kq.thanh_cong:
        so_dang.ghi({"luc": bay_gio().isoformat(), "kenh": ch.kenh, "ma_video": k[0], "nen_tang": k[1],
                     "id_bai": kq.id_bai, "link": kq.link, "loai": "ban_giao" if kq.ban_giao else "dang"})
        if kq.ban_giao:
            bc.ban_giao += 1
            bc.in_ra(f"+ {nhan}: đã chép sang Drive, chờ đăng tay: {kq.link}")
            _ghi(bang, d, trang_thai_dang=TT_CHO_DANG_TAY, link_bai=kq.link, loi="")
        elif kq.visibility and kq.visibility != "public":
            bc.kiem_tra += 1
            bc.in_ra(f"! {nhan}: đã tải lên ({kq.id_bai}) nhưng đang ở chế độ {kq.visibility}")
            _ghi(bang, d, trang_thai_dang=TT_CAN_KIEM_TRA, id_bai=kq.id_bai, link_bai=kq.link,
                 loi=f"Đã tải lên lúc {luc} nhưng privacyStatus = {kq.visibility}, chưa công khai. Kiểm tra trên nền tảng.")
        else:
            bc.da_dang += 1
            bc.in_ra(f"+ {nhan}: đã đăng {kq.id_bai} {kq.link}")
            _ghi(bang, d, trang_thai_dang=TT_DA_DANG, id_bai=kq.id_bai, link_bai=kq.link, loi="")
        return

    if kq.loai_loi == "khong_ro":
        bc.kiem_tra += 1
        tt, loi = TT_CAN_KIEM_TRA, f"Không rõ bài đã lên chưa ({luc}): {kq.loi}. Kiểm tra trên nền tảng trước khi cho đăng lại."
    elif kq.loai_loi in LOAI_THU_LAI_LAN_SAU:
        bc.loi += 1
        tt, loi = TT_LOI_THU_LAI, f"{kq.loai_loi} ({luc}): {kq.loi}"
    else:
        bc.loi += 1
        tt, loi = TT_LOI, f"{kq.loai_loi} ({luc}): {kq.loi}. Không tự thử lại."
    bc.in_ra(f"x {nhan}: {tt}: {kq.loi[:200]}")
    cot = {"trang_thai_dang": tt, "loi": loi[:500]}
    if kq.id_bai:
        cot["id_bai"] = kq.id_bai  # đã có id thì không bao giờ đăng lại dòng này
    _ghi(bang, d, **cot)
