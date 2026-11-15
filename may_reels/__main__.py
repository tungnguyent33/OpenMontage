"""Dòng lệnh Máy Reels.

    python -m may_reels sheet init [--thu]
    python -m may_reels sheet nap-chu-de --kenh <mã> [--thu]
    python -m may_reels hang-cho them --video <mp4> --kenh <mã> --caption-file <txt> [--ma <mã video>] [--thu]
    python -m may_reels dang [--that]
    python -m may_reels dang-nhap drive
    python -m may_reels dang-nhap youtube --kenh <mã>

--thu: chỉ in ra việc sẽ làm, không ghi gì lên Sheet.
`dang` mặc định là CHẠY THỬ; chỉ --that mới đăng thật (chỉ người dùng được bật).
"""
from __future__ import annotations

import argparse
import sys
import time

from may_reels.cot_sheet import NHAT_KY, TAT_CA
from may_reels.sheet import LoiSheet, bay_gio_vn, khoi_tao, mo_tu_env, them_nhat_ky


def _ghi_nhat_ky(bang, kenh: str, buoc: str, thu: bool, ket_qua: str, chi_tiet: str, bat_dau: float) -> None:
    dong = {"thoi_gian": bay_gio_vn(), "kenh": kenh, "ma": "", "buoc": buoc,
            "che_do": "thu" if thu else "that", "ket_qua": ket_qua, "chi_tiet": chi_tiet[:500],
            "chi_phi_vnd": "0", "thoi_gian_chay_giay": f"{time.monotonic() - bat_dau:.1f}", "so_luot_tro_ly": "0"}
    if thu:
        print(f"[thử] Nhật ký sẽ ghi: {dong}")
        return
    them_nhat_ky(bang, NHAT_KY, [dong])


def lenh_init(a) -> int:
    bat_dau = time.monotonic()
    bang = mo_tu_env()
    kq = khoi_tao(bang, TAT_CA, thu=a.thu)
    tien_to = "[thử] " if a.thu else ""
    for t in kq.tab_tao_moi:
        print(f"{tien_to}Tạo tab: {t}")
    for t, cot in kq.cot_them.items():
        if t not in kq.tab_tao_moi:
            print(f"{tien_to}Thêm cột vào {t}: {', '.join(cot)}")
    for t in kq.tab_da_co:
        if t not in kq.cot_them:
            print(f"Tab đã đủ cột: {t}")
    if a.thu and NHAT_KY.ten in kq.tab_tao_moi:
        print("[thử] Tab Nhật ký chưa có nên không ghi nhật ký.")
        return 0
    chi_tiet = f"tạo {kq.tab_tao_moi or 'không'}; thêm cột {kq.cot_them or 'không'}"
    _ghi_nhat_ky(bang, "", "sheet.init", a.thu, "ok", chi_tiet, bat_dau)
    return 0


def lenh_nap_chu_de(a) -> int:
    from may_reels.chu_de import nap_chu_de
    bat_dau = time.monotonic()
    bang = mo_tu_env()
    kq_da, kq_chua = nap_chu_de(bang, a.kenh, thu=a.thu)
    tien_to = "[thử] " if a.thu else ""
    them = kq_da.them + kq_chua.them
    cap_nhat = {**kq_da.cap_nhat, **kq_chua.cap_nhat}
    giu = kq_da.giu_nguyen + kq_chua.giu_nguyen
    print(f"{tien_to}Kênh {a.kenh}: thêm {len(them)} dòng, cập nhật {len(cap_nhat)}, giữ nguyên {len(giu)}")
    for k in them:
        print(f"   + {k[1]}")
    for k, cot in cap_nhat.items():
        print(f"   ~ {k[1]}: {', '.join(cot)}")
    for c in kq_da.canh_bao + kq_chua.canh_bao:
        print(f"   ! {c}")
    chi_tiet = f"thêm {len(them)}, cập nhật {len(cap_nhat)}, giữ nguyên {len(giu)}"
    _ghi_nhat_ky(bang, a.kenh, "sheet.nap_chu_de", a.thu, "ok", chi_tiet, bat_dau)
    return 0


def lenh_hang_cho_them(a) -> int:
    from pathlib import Path
    from may_reels.hang_cho import them_video
    bat_dau = time.monotonic()
    bang = mo_tu_env()
    kq = them_video(bang, video=Path(a.video), kenh=a.kenh, caption_file=Path(a.caption_file), ma=a.ma,
                    nen_tang=a.nen_tang or None, thu=a.thu)
    tien_to = "[thử] " if a.thu else ""
    if kq.loi:
        for x in kq.loi:
            print(f"   x {x}")
        print(f"LỖI: không đưa {kq.ma_video} vào Hàng chờ ({len(kq.loi)} lỗi)", file=sys.stderr)
        if not a.thu:
            _ghi_nhat_ky(bang, a.kenh, "hang_cho.them", False, "loi", f"{kq.ma_video}: {'; '.join(kq.loi)}", bat_dau)
        return 2
    print(f"{tien_to}{kq.ma_video}: {', '.join(kq.nen_tang)} | thêm {kq.them}, cập nhật {kq.cap_nhat}, giữ nguyên {kq.giu_nguyen}")
    print(f"{tien_to}Xem thử: {kq.link_xem_thu}")
    print("Duyệt trên tab Hàng chờ: chọn 'Duyệt' ở cột duyet (ô trống = Chờ duyệt).")
    _ghi_nhat_ky(bang, a.kenh, "hang_cho.them", a.thu, "ok",
                 f"{kq.ma_video}: thêm {kq.them}, cập nhật {kq.cap_nhat}", bat_dau)
    return 0


def lenh_dang(a) -> int:
    from may_reels.dang_bai import chay_dang
    from may_reels.khoa_tien_trinh import LoiDangChay
    bang = mo_tu_env()
    if a.that:
        print("CHẾ ĐỘ ĐĂNG THẬT")
    else:
        print("Chạy thử (thêm --that để đăng thật). Không gọi API nền tảng, không ghi tab Hàng chờ.")
    try:
        bc = chay_dang(bang, that=a.that)
    except LoiDangChay as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 3
    for d in bc.dong:
        print(d)
    if a.that:
        print(f"Kết quả: đăng {bc.da_dang}, bàn giao TikTok {bc.ban_giao}, lỗi {bc.loi}, cần kiểm tra {bc.kiem_tra}, bỏ qua {bc.bo_qua}")
    else:
        print(f"Chạy thử: sẽ đăng {bc.se_dang}, bỏ qua {bc.bo_qua}, lỗi nội dung {bc.loi}, kẹt {bc.kiem_tra}")
    return 1 if bc.loi else 0


def lenh_dang_nhap(a) -> int:
    from may_reels.google_oauth import (BIEN_DRIVE_TOKEN, PHAM_VI_DRIVE, PHAM_VI_YOUTUBE, dang_nhap,
                                        duong_dan_tu_bien, nap_creds)
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
    except ImportError:
        pass
    if a.dich_vu == "drive":
        from may_reels.drive import TOKEN_MAC_DINH
        p = dang_nhap(duong_dan_tu_bien(BIEN_DRIVE_TOKEN, TOKEN_MAC_DINH), PHAM_VI_DRIVE)
        print(f"Đã lưu token Drive vào {p.name} (thư mục secrets/, không commit)")
        return 0
    if not a.kenh:
        print("LỖI: cần --kenh", file=sys.stderr)
        return 2
    from may_reels.cau_hinh_dang import doc_cau_hinh_dang
    ch = doc_cau_hinh_dang(a.kenh)
    ten_bien = ch.yt_shorts.get("bien_token_file")
    if not ten_bien:
        print(f"LỖI: brand/{a.kenh}/dang-bai.yaml thiếu yt_shorts.bien_token_file", file=sys.stderr)
        return 2
    p = dang_nhap(duong_dan_tu_bien(ten_bien), PHAM_VI_YOUTUBE)
    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=nap_creds(p, PHAM_VI_YOUTUBE), cache_discovery=False)
    kenh = [(c["id"], c["snippet"]["title"]) for c in yt.channels().list(part="id,snippet", mine=True).execute().get("items", [])]
    print(f"Đã lưu token YouTube vào {p.name}. Token này thuộc kênh: {kenh}")
    muon = str(ch.yt_shorts.get("kenh_id") or "")
    if not muon:
        print(f"Ghi ID kênh (UC...) vào brand/{a.kenh}/dang-bai.yaml mục yt_shorts.kenh_id.")
    elif muon not in [c[0] for c in kenh]:
        print(f"CẢNH BÁO: kenh_id trong dang-bai.yaml ({muon}) không khớp token. Đăng nhập lại và chọn đúng kênh.")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m may_reels")
    sub = ap.add_subparsers(dest="nhom", required=True)
    sheet = sub.add_parser("sheet", help="Google Sheet Máy Reels").add_subparsers(dest="lenh", required=True)
    p = sheet.add_parser("init", help="tạo tab và cột còn thiếu")
    p.add_argument("--thu", action="store_true", help="chỉ in việc sẽ làm")
    p.set_defaults(ham=lenh_init)
    p = sheet.add_parser("nap-chu-de", help="đẩy chủ đề của một kênh lên tab Ý tưởng")
    p.add_argument("--kenh", required=True, help="mã kênh trong brand/")
    p.add_argument("--thu", action="store_true", help="chỉ in việc sẽ làm")
    p.set_defaults(ham=lenh_nap_chu_de)

    hc = sub.add_parser("hang-cho", help="tab Hàng chờ").add_subparsers(dest="lenh", required=True)
    p = hc.add_parser("them", help="đưa một video có sẵn vào Hàng chờ")
    p.add_argument("--video", required=True)
    p.add_argument("--kenh", required=True)
    p.add_argument("--caption-file", required=True)
    p.add_argument("--ma", help="mã video (mặc định lấy từ tên file)")
    p.add_argument("--nen-tang", nargs="+", choices=["fb_reels", "yt_shorts", "tiktok"],
                   help="mặc định: danh sách nen_tang trong dang-bai.yaml")
    p.add_argument("--thu", action="store_true", help="chỉ kiểm tra và in, không tải lên, không ghi Sheet")
    p.set_defaults(ham=lenh_hang_cho_them)

    p = sub.add_parser("dang", help="đăng các dòng đã Duyệt trong Hàng chờ (mặc định chạy thử)")
    p.add_argument("--that", action="store_true", help="ĐĂNG THẬT")
    p.set_defaults(ham=lenh_dang)

    p = sub.add_parser("dang-nhap", help="đăng nhập OAuth Google một lần (mở trình duyệt)")
    p.add_argument("dich_vu", choices=["drive", "youtube"])
    p.add_argument("--kenh")
    p.set_defaults(ham=lenh_dang_nhap)

    a = ap.parse_args(argv)
    try:
        return a.ham(a)
    except (LoiSheet, FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
