"""Dòng lệnh Máy Reels.

    python -m may_reels sheet init [--thu]
    python -m may_reels sheet nap-chu-de --kenh <mã> [--thu]

--thu: chỉ in ra việc sẽ làm, không ghi gì lên Sheet.
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
    a = ap.parse_args(argv)
    try:
        return a.ham(a)
    except (LoiSheet, FileNotFoundError, ValueError) as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
