"""Dòng lệnh Máy Reels.

    python -m may_reels sheet init [--thu]
    python -m may_reels sheet nap-chu-de --kenh <mã> [--thu]
    python -m may_reels hang-cho them --video <mp4> --kenh <mã> --caption-file <txt> [--ma <mã video>] [--thu]
    python -m may_reels dung --du-an <ma_video> [--stage ...]
    python -m may_reels san-xuat --kenh <mã> --so-luong 3
    python -m may_reels sua
    python -m may_reels thay-canh
    python -m may_reels dang [--that]
    python -m may_reels dang-nhap drive
    python -m may_reels dang-nhap youtube --kenh <mã>
    python -m may_reels dung-luong [--cache]
    python -m may_reels don-dep [--that]
    python -m may_reels cham-lai --kenh <mã>
    python -m may_reels hieu-chinh --kenh <mã>
    python -m may_reels nguon-luat --kenh <mã> [--ma ...] [--thu]
    python -m may_reels nguon-luat ap-dung --kenh <mã> [--thu]

--thu: chỉ in ra việc sẽ làm, không ghi gì lên Sheet.
`dang` mặc định là CHẠY THỬ; chỉ --that mới đăng thật (chỉ người dùng được bật).
"""
from __future__ import annotations

import argparse
from pathlib import Path
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


def lenh_dung(a) -> int:
    """Dựng một dự án có ke_hoach.json. Dòng cuối stdout là JSON tóm tắt. Mã thoát: 0 ok, 10 kế hoạch sai,
    11 thiếu cảnh, 12 không qua tự kiểm, 13 cổng idea chưa mở, 1 lỗi khác."""
    import json
    from may_reels.dung.pipeline import LoiCongDuyet, LoiKeHoach, LoiQA, LoiThieuCanhDung, Pipeline
    tom: dict = {"ma_video": a.du_an}
    ma = 0
    try:
        kq = Pipeline(a.du_an).chay(a.stage or None)
        tom.update(diem_ky_thuat=kq.diem_ky_thuat, canh_bao=kq.canh_bao, thoi_gian=kq.thoi_gian,
                   video=str(kq.video) if kq.video else None)
        c = Path("projects") / a.du_an / "checkpoint_compose.json"
        if c.exists():
            tom["tru_diem"] = json.loads(c.read_text(encoding="utf-8"))["artifacts"]["final_review"]["metadata"].get("tru_diem")
    except LoiKeHoach as e:
        ma, tom["loi"] = 10, str(e)
    except LoiThieuCanhDung as e:
        ma, tom["loi"], tom["thieu_canh"] = 11, str(e), e.thieu
    except LoiQA as e:
        ma, tom["loi"] = 12, str(e)
    except LoiCongDuyet as e:
        ma, tom["loi"] = 13, str(e)
    print(json.dumps(tom, ensure_ascii=False))
    return ma


def lenh_san_xuat(a) -> int:
    from may_reels.san_xuat import san_xuat
    ds = san_xuat(mo_tu_env(), a.kenh, a.so_luong, ca_cho_quay=a.ca_cho_quay, ca_loi=a.ca_loi)
    for k in ds:
        print(f"{k.ma_video}: {k.trang_thai} | QA {k.diem_qa} | {k.giay:.0f}s (agent {k.giay_agent:.0f}s, "
              f"{k.so_luot_agent} lượt, vòng sửa {k.vong}) | {'; '.join(k.canh_bao)} {k.loi}")
    return 0 if all(k.trang_thai != "loi" for k in ds) else 1


def lenh_thay_canh(a) -> int:
    from may_reels.sua import thay_canh
    ds = thay_canh(mo_tu_env())
    return 0 if all(k["trang_thai"] != "loi" for k in ds) else 1


def lenh_sua(a) -> int:
    from may_reels.sua import sua
    ds = sua(mo_tu_env())
    return 0 if all(k["trang_thai"] != "loi" for k in ds) else 1


def lenh_dung_luong(a) -> int:
    from may_reels.dung_luong import bao_cao
    from tools_local.nap_kenh import nap_env
    nap_env()
    bao_cao(cache=a.cache)
    return 0


def lenh_don_dep(a) -> int:
    from may_reels.don_dep import don_dep
    from tools_local.nap_kenh import nap_env
    nap_env()
    kq = don_dep(mo_tu_env(), that=a.that)
    return 1 if kq["loi"] else 0


def lenh_cham_lai(a) -> int:
    from may_reels.hieu_chinh import cham_lai
    from tools_local.nap_kenh import nap_env
    nap_env()
    ds = cham_lai(mo_tu_env(), a.kenh)
    return 0 if all(k["trang_thai"] != "loi" for k in ds) else 1


def lenh_hieu_chinh(a) -> int:
    from may_reels.hieu_chinh import hieu_chinh
    hieu_chinh(mo_tu_env(), a.kenh)
    return 0


def lenh_nguon_luat(a) -> int:
    from may_reels.nguon_luat import ap_dung, tra_nguon
    from tools_local.nap_kenh import nap_env
    nap_env()
    bang = mo_tu_env()
    if a.viec == "ap-dung":
        ap_dung(bang, a.kenh, thu=a.thu)
        return 0
    ds = tra_nguon(bang, a.kenh, chi_ma=a.ma, thu=a.thu)
    if ds and not a.thu:
        print(f"Tổng: {len(ds)} chủ đề, đề xuất {sum(1 for d in ds if d.nguon_de_xuat)}, "
              f"claude báo {sum(d.chi_phi_usd for d in ds):.2f} USD. Xác nhận ở cột xac_nhan_nguon (tab Ý tưởng), "
              f"rồi chạy: nguon-luat ap-dung --kenh {a.kenh}")
    return 1 if any(d.loi for d in ds) else 0


def giu_may_thuc(bat: bool) -> None:
    """Windows: không cho máy tự ngủ khi đang sản xuất (SetThreadExecutionState). Gập máy vẫn ngủ."""
    import os
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if bat else 0))
    except Exception:  # pragma: no cover
        pass


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

    p = sub.add_parser("dung", help="dựng một dự án từ ke_hoach.json (pipeline may-reels)")
    p.add_argument("--du-an", required=True, help="mã video = tên thư mục trong projects/")
    p.add_argument("--stage", nargs="+", choices=["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"])
    p.set_defaults(ham=lenh_dung)

    p = sub.add_parser("san-xuat", help="sản xuất các chủ đề đã chọn Làm (agent + dựng + hàng chờ)")
    p.add_argument("--kenh", required=True)
    p.add_argument("--so-luong", type=int, default=3)
    p.add_argument("--ca-cho-quay", action="store_true",
                   help="dựng lại cả chủ đề đang chờ quay, dùng cảnh tạm (sơ đồ) cho đoạn thiếu cảnh")
    p.add_argument("--ca-loi", action="store_true", help="dựng lại cả chủ đề có job đang lỗi")
    p.set_defaults(ham=lenh_san_xuat)

    p = sub.add_parser("sua", help="sửa và dựng lại các video được chọn Sửa trên Hàng chờ")
    p.set_defaults(ham=lenh_sua)

    p = sub.add_parser("thay-canh", help="thay cảnh tạm bằng cảnh thật khi Cần quay ghi 'Đã quay'")
    p.set_defaults(ham=lenh_thay_canh)

    p = sub.add_parser("dung-luong", help="báo dung lượng media theo dự án và theo loại (chỉ đọc)")
    p.add_argument("--cache", action="store_true", help="báo thêm cache dùng chung (model, npm/npx); không xóa")
    p.set_defaults(ham=lenh_dung_luong)

    p = sub.add_parser("don-dep", help="dọn media theo trạng thái duyệt trên Hàng chờ (mặc định chạy thử)")
    p.add_argument("--that", action="store_true", help="xóa thật (mặc định chỉ in sẽ xóa gì)")
    p.set_defaults(ham=lenh_don_dep)

    p = sub.add_parser("cham-lai", help="chấm lại video trong Hàng chờ theo rubric (không dựng lại)")
    p.add_argument("--kenh", required=True)
    p.set_defaults(ham=lenh_cham_lai)

    p = sub.add_parser("hieu-chinh", help="so điểm máy với diem_cua_toi, đề xuất sửa rubric.yaml (không tự sửa)")
    p.add_argument("--kenh", required=True)
    p.set_defaults(ham=lenh_hieu_chinh)

    p = sub.add_parser("nguon-luat", help="máy đề xuất điều khoản luật cho chủ đề; ap-dung chép nguồn đã xác nhận")
    p.add_argument("viec", nargs="?", choices=["ap-dung"], help="ap-dung: chép đề xuất có xac_nhan_nguon = Đúng")
    p.add_argument("--kenh", required=True)
    p.add_argument("--ma", nargs="+", help="chỉ tra các mã chủ đề này")
    p.add_argument("--thu", action="store_true", help="chỉ in việc sẽ làm")
    p.set_defaults(ham=lenh_nguon_luat)

    p = sub.add_parser("dang-nhap", help="đăng nhập OAuth Google một lần (mở trình duyệt)")
    p.add_argument("dich_vu", choices=["drive", "youtube"])
    p.add_argument("--kenh")
    p.set_defaults(ham=lenh_dang_nhap)

    a = ap.parse_args(argv)
    dai = a.ham in (lenh_san_xuat, lenh_sua, lenh_thay_canh, lenh_dung, lenh_cham_lai, lenh_nguon_luat)
    if dai:
        giu_may_thuc(True)
    try:
        return a.ham(a)
    except (LoiSheet, FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 2
    finally:
        if dai:
            giu_may_thuc(False)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
