"""Lớp nối Google Sheet "Máy Reels".

Quy tắc ghi (docs/may-reels/NGUYEN-TAC.md mục 2):
- Tìm dòng theo khóa của tab (cot_sheet.Tab.khoa), tìm cột theo TÊN ở dòng 1.
- Chỉ ghi vào cột của máy. Muốn ghi cột của người là lỗi, báo trước khi gọi mạng.
- Không xóa dòng, không sắp xếp lại, không ghi lại cả bảng: chỉ ghi đúng từng ô
  có giá trị đổi, và thêm dòng mới bằng append (máy chủ Google tự chèn ở cuối).
- Người dùng có thể đang mở Sheet: ngay trước khi ghi, đọc lại và kiểm tra dòng
  đích vẫn mang đúng khóa; lệch thì tính lại (tối đa SO_LAN_THU lần) rồi mới báo lỗi.
- Ghi bằng chế độ RAW: Sheet không tự đổi "1/3" thành ngày hay bỏ số 0 ở đầu mã.

gspread chỉ được import bên trong GspreadBangTinh.mo(), để import module này không
cần thư viện mạng (test chạy bằng bảng giả, xem tests/may_reels/sheet_gia.py).
"""
from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Protocol

from may_reels.cot_sheet import TAT_CA, Tab

BIEN_SA_JSON = "MAY_REELS_SA_JSON"
BIEN_SHEET_ID = "MAY_REELS_SHEET_ID"
PHAM_VI = ["https://www.googleapis.com/auth/spreadsheets"]  # chỉ Sheets, không cần quyền Drive
SO_LAN_THU = 3
SO_DONG_TAB_MOI = 1000
TZ_VN = timezone(timedelta(hours=7))

MAU_COT_NGUOI = {"red": 1.0, "green": 0.976, "blue": 0.8}   # vàng nhạt
MAU_TIEU_DE = {"red": 0.93, "green": 0.93, "blue": 0.93}


class LoiSheet(Exception):
    """Lỗi chung của lớp nối Sheet."""


class LoiGhiCotNguoi(LoiSheet):
    """Máy định ghi vào cột của người."""


class LoiCauTruc(LoiSheet):
    """Tab hoặc cột không đúng như khai báo (thường là chưa chạy `sheet init`)."""


class LoiDongDoiCho(LoiSheet):
    """Dòng đích bị người dùng chèn/xóa/sắp xếp trong lúc máy đang ghi, thử lại vẫn lệch."""


# ---------------------------------------------------------------- giao diện
class TabNguon(Protocol):
    """Phần tối thiểu của một worksheet mà máy dùng. Bản thật bọc gspread, bản giả dùng trong test."""

    title: str
    sheet_id: int
    so_cot: int

    def doc_tat_ca(self) -> list[list[str]]: ...
    def ghi_o(self, o: list[tuple[int, int, str]]) -> None: ...   # (dòng, cột) đánh số từ 1
    def them_dong(self, dong: list[list[str]]) -> None: ...
    def mo_rong_cot(self, so_cot_them: int) -> None: ...


class BangNguon(Protocol):
    def danh_sach_tab(self) -> list[TabNguon]: ...
    def tao_tab(self, ten: str, so_dong: int, so_cot: int) -> TabNguon: ...
    def dinh_dang(self, yeu_cau: list[dict]) -> None: ...


# ---------------------------------------------------------------- bản thật (gspread)
def a1(dong: int, cot: int) -> str:
    chu = ""
    while cot:
        cot, du = divmod(cot - 1, 26)
        chu = chr(65 + du) + chu
    return f"{chu}{dong}"


class GspreadTab:
    def __init__(self, ws) -> None:
        self._ws = ws

    @property
    def title(self) -> str:
        return self._ws.title

    @property
    def sheet_id(self) -> int:
        return self._ws.id

    @property
    def so_cot(self) -> int:
        return self._ws.col_count

    def doc_tat_ca(self) -> list[list[str]]:
        return self._ws.get_all_values()

    def ghi_o(self, o: list[tuple[int, int, str]]) -> None:
        if o:
            from gspread.utils import ValueInputOption
            self._ws.batch_update([{"range": a1(d, c), "values": [[v]]} for d, c, v in o],
                                  value_input_option=ValueInputOption.raw)

    def them_dong(self, dong: list[list[str]]) -> None:
        if dong:
            from gspread.utils import InsertDataOption, ValueInputOption
            self._ws.append_rows(dong, value_input_option=ValueInputOption.raw,
                                 insert_data_option=InsertDataOption.insert_rows, table_range="A1")

    def mo_rong_cot(self, so_cot_them: int) -> None:
        if so_cot_them > 0:
            self._ws.add_cols(so_cot_them)


class GspreadBangTinh:
    def __init__(self, sh) -> None:
        self._sh = sh

    @classmethod
    def mo(cls, sa_json: str | Path, sheet_id: str) -> "GspreadBangTinh":
        import gspread  # thư viện mạng: chỉ import khi thật sự mở Sheet
        gc = gspread.service_account(filename=str(sa_json), scopes=PHAM_VI)
        return cls(gc.open_by_key(sheet_id))

    def danh_sach_tab(self) -> list[TabNguon]:
        return [GspreadTab(w) for w in self._sh.worksheets()]

    def tao_tab(self, ten: str, so_dong: int, so_cot: int) -> TabNguon:
        return GspreadTab(self._sh.add_worksheet(title=ten, rows=so_dong, cols=so_cot))

    def dinh_dang(self, yeu_cau: list[dict]) -> None:
        if yeu_cau:
            self._sh.batch_update({"requests": yeu_cau})


def mo_tu_env(goc: Path | None = None) -> GspreadBangTinh:
    """Mở Sheet theo MAY_REELS_SA_JSON và MAY_REELS_SHEET_ID trong .env (đường dẫn tương đối tính từ gốc repo)."""
    goc = goc or Path(__file__).resolve().parent.parent
    try:
        from dotenv import load_dotenv
        load_dotenv(goc / ".env", override=False)
    except ImportError:
        pass
    sa = os.environ.get(BIEN_SA_JSON, "").strip().strip('"').strip("'")
    sid = os.environ.get(BIEN_SHEET_ID, "").strip().strip('"').strip("'")
    thieu = [b for b, v in ((BIEN_SA_JSON, sa), (BIEN_SHEET_ID, sid)) if not v]
    if thieu:
        raise LoiSheet(f"Chưa đặt {', '.join(thieu)} trong .env (xem docs/may-reels/CAI-DAT-GOOGLE.md)")
    p = Path(sa)
    if not p.is_absolute():
        p = goc / p
    if not p.is_file():
        raise LoiSheet(f"Không thấy file khóa service account: {sa} (đặt trong secrets/)")
    return GspreadBangTinh.mo(p, sid)


# ---------------------------------------------------------------- tiện ích
def chuan(v) -> str:
    """Giá trị ô dạng chuỗi: NFC, bỏ khoảng trắng hai đầu. None -> ''."""
    if v is None:
        return ""
    return unicodedata.normalize("NFC", str(v)).strip()


def bay_gio_vn() -> str:
    return datetime.now(TZ_VN).strftime("%Y-%m-%d %H:%M:%S")


def tim_tab(bang: BangNguon, ten: str) -> TabNguon | None:
    for t in bang.danh_sach_tab():
        if chuan(t.title) == chuan(ten):
            return t
    return None


def ban_do_cot(tieu_de: list[str]) -> dict[str, int]:
    """Tên cột -> số thứ tự cột (từ 1). Tên trùng thì lấy cột đầu tiên."""
    out: dict[str, int] = {}
    for i, ten in enumerate(tieu_de, start=1):
        ten = chuan(ten)
        if ten and ten not in out:
            out[ten] = i
    return out


# ---------------------------------------------------------------- init
@dataclass
class KetQuaInit:
    tab_tao_moi: list[str] = field(default_factory=list)
    cot_them: dict[str, list[str]] = field(default_factory=dict)
    tab_da_co: list[str] = field(default_factory=list)


def _yeu_cau_dinh_dang(tab: Tab, sheet_id: int, cot: dict[str, int]) -> list[dict]:
    rq: list[dict] = [
        {"updateSheetProperties": {"properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                                   "fields": "gridProperties.frozenRowCount"}},
    ]
    for c in tab.cot:
        i = cot[c.ten] - 1
        rq.append({"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True},
                                           "backgroundColor": MAU_COT_NGUOI if c.cua_nguoi else MAU_TIEU_DE}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)"}})
        if c.cua_nguoi:
            rq.append({"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
                "cell": {"userEnteredFormat": {"backgroundColor": MAU_COT_NGUOI}},
                "fields": "userEnteredFormat.backgroundColor"}})
        if c.lua_chon:
            rq.append({"setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
                "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in c.lua_chon]},
                         "strict": True, "showCustomUi": True}}})
    return rq


def khoi_tao(bang: BangNguon, cac_tab: Iterable[Tab] = TAT_CA, thu: bool = False) -> KetQuaInit:
    """Tạo tab còn thiếu, thêm cột còn thiếu vào CUỐI dòng tiêu đề, tô màu, đặt dropdown.

    Không xóa tab, không xóa hay đổi chỗ cột có sẵn, không đụng vào dữ liệu từ dòng 2.
    Chạy lại nhiều lần cho cùng kết quả.
    """
    kq = KetQuaInit()
    dinh_dang: list[dict] = []
    for tab in cac_tab:
        ws = tim_tab(bang, tab.ten)
        if ws is None:
            kq.tab_tao_moi.append(tab.ten)
            kq.cot_them[tab.ten] = tab.ten_cot
            if thu:
                continue
            ws = bang.tao_tab(tab.ten, SO_DONG_TAB_MOI, len(tab.cot))
            ws.ghi_o([(1, i, ten) for i, ten in enumerate(tab.ten_cot, start=1)])
            cot = {ten: i for i, ten in enumerate(tab.ten_cot, start=1)}
        else:
            kq.tab_da_co.append(tab.ten)
            hang = ws.doc_tat_ca()
            tieu_de = [chuan(x) for x in (hang[0] if hang else [])]
            while tieu_de and not tieu_de[-1]:
                tieu_de.pop()
            cot = ban_do_cot(tieu_de)
            thieu = [t for t in tab.ten_cot if t not in cot]
            if thieu:
                kq.cot_them[tab.ten] = thieu
                if thu:
                    continue
                bat_dau = len(tieu_de) + 1
                can = bat_dau + len(thieu) - 1 - ws.so_cot
                if can > 0:
                    ws.mo_rong_cot(can)
                ws.ghi_o([(1, bat_dau + k, ten) for k, ten in enumerate(thieu)])
                for k, ten in enumerate(thieu):
                    cot[ten] = bat_dau + k
            if thu:
                continue
        dinh_dang += _yeu_cau_dinh_dang(tab, ws.sheet_id, cot)
    if not thu:
        bang.dinh_dang(dinh_dang)
    return kq


# ---------------------------------------------------------------- ghi theo khóa
@dataclass
class KetQuaGhi:
    them: list[tuple[str, ...]] = field(default_factory=list)
    cap_nhat: dict[tuple[str, ...], list[str]] = field(default_factory=dict)  # khóa -> các cột đã đổi
    giu_nguyen: list[tuple[str, ...]] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)


# NGOẠI LỆ DUY NHẤT máy được ghi cột của người (docs/may-reels/NGUYEN-TAC.md mục 2):
#   khoi_tao: dòng MỚI của Hàng chờ được ghi duyet = "Chờ duyệt" (dòng đã có: không đụng)
#   sua     : lệnh `sua` đưa duyet từ "Sửa" về "Chờ duyệt" sau khi dựng lại (ô khác "Sửa": không đụng)
COT_DUYET = "duyet"
GIA_TRI_CHO = "Chờ duyệt"
NGOAI_LE_DUYET = {"khoi_tao": None, "sua": "Sửa"}  # tên -> giá trị hiện tại bắt buộc (None = chỉ dòng mới)


def kiem_tra_cot_may(tab: Tab, dong: Iterable[dict], ngoai_le_duyet: str | None = None) -> None:
    """Báo lỗi nếu có dòng định ghi vào cột của người hoặc cột không khai báo. Gọi trước khi chạm mạng."""
    nguoi = set(tab.cot_nguoi)
    co = set(tab.ten_cot)
    if ngoai_le_duyet is not None and ngoai_le_duyet not in NGOAI_LE_DUYET:
        raise LoiSheet(f"Ngoại lệ không tồn tại: {ngoai_le_duyet!r}")
    for d in dong:
        if ngoai_le_duyet and COT_DUYET in nguoi and COT_DUYET in d:
            if d[COT_DUYET] != GIA_TRI_CHO:
                raise LoiGhiCotNguoi(f"Ngoại lệ {ngoai_le_duyet}: cột duyet chỉ được ghi {GIA_TRI_CHO!r}")
            d = {k: v for k, v in d.items() if k != COT_DUYET}
        sai = sorted(set(d) & nguoi)
        if sai:
            raise LoiGhiCotNguoi(f"Tab {tab.ten!r}: máy không được ghi cột của người {sai}")
        la = sorted(set(d) - co)
        if la:
            raise LoiCauTruc(f"Tab {tab.ten!r}: cột không khai báo {la}")


def _khoa(tab: Tab, gia_tri: dict | list, cot: dict[str, int] | None = None) -> tuple[str, ...]:
    if isinstance(gia_tri, dict):
        return tuple(chuan(gia_tri.get(k)) for k in tab.khoa)
    return tuple(chuan(gia_tri[cot[k] - 1]) if cot[k] - 1 < len(gia_tri) else "" for k in tab.khoa)


def _o(hang: list[str], so_cot: int) -> str:
    return chuan(hang[so_cot - 1]) if so_cot - 1 < len(hang) else ""


def ghi_theo_khoa(
    bang: BangNguon,
    tab: Tab,
    dong: list[dict],
    *,
    chi_khi_trong: Iterable[str] = (),
    thu: bool = False,
    bay_gio: Callable[[], str] = bay_gio_vn,
    ngoai_le_duyet: str | None = None,
) -> KetQuaGhi:
    """Thêm hoặc cập nhật dòng theo khóa của tab. Chỉ ghi cột của máy.

    - Khóa trong `dong` phải đủ và không trùng nhau.
    - Giá trị None = không đụng tới ô đó. Chuỗi rỗng = xóa nội dung ô (chỉ cột máy).
    - `chi_khi_trong`: những cột chỉ được ghi khi ô đang trống (không đè tiến độ đã có).
    - `thu=True`: chỉ tính toán, không ghi gì.
    """
    if tab.chi_them:
        raise LoiSheet(f"Tab {tab.ten!r} không có khóa; dùng them_nhat_ky()")
    kiem_tra_cot_may(tab, dong, ngoai_le_duyet)
    chi_khi_trong = set(chi_khi_trong)
    da_thay: set[tuple[str, ...]] = set()
    for d in dong:
        k = _khoa(tab, d)
        if any(not x for x in k):
            raise LoiSheet(f"Tab {tab.ten!r}: dòng thiếu khóa {dict(zip(tab.khoa, k))}")
        if k in da_thay:
            raise LoiSheet(f"Tab {tab.ten!r}: khóa bị trùng trong dữ liệu đầu vào {k}")
        da_thay.add(k)

    ws = tim_tab(bang, tab.ten)
    if ws is None:
        raise LoiCauTruc(f"Chưa có tab {tab.ten!r}: chạy `python -m may_reels sheet init` trước")

    for _ in range(SO_LAN_THU):
        hang = ws.doc_tat_ca()
        cot = ban_do_cot(hang[0] if hang else [])
        thieu = [t for t in tab.ten_cot if t not in cot]
        if thieu:
            raise LoiCauTruc(f"Tab {tab.ten!r} thiếu cột {thieu}: chạy `python -m may_reels sheet init`")

        kq = KetQuaGhi()
        vi_tri: dict[tuple[str, ...], int] = {}
        for so_dong, h in enumerate(hang[1:], start=2):
            k = _khoa(tab, h, cot)
            if not any(k):
                continue
            if k in vi_tri:
                kq.canh_bao.append(f"Tab {tab.ten!r}: khóa {k} xuất hiện ở nhiều dòng; chỉ cập nhật dòng {vi_tri[k]}")
                continue
            vi_tri[k] = so_dong

        o_ghi: list[tuple[int, int, str]] = []
        dong_moi: list[list[str]] = []
        so_cot_tieu_de = max(cot.values())
        for d in dong:
            k = _khoa(tab, d)
            if k in vi_tri:
                r = vi_tri[k]
                h = hang[r - 1]
                doi = []
                for ten, v in d.items():
                    if v is None or ten in tab.khoa:
                        continue
                    hien = _o(h, cot[ten])
                    if ten == COT_DUYET and ngoai_le_duyet:
                        if NGOAI_LE_DUYET[ngoai_le_duyet] is None or hien != NGOAI_LE_DUYET[ngoai_le_duyet]:
                            continue  # khoi_tao không đụng dòng cũ; sua chỉ đổi ô đang là "Sửa"
                    if ten in chi_khi_trong and hien:
                        continue
                    if chuan(v) != hien:
                        o_ghi.append((r, cot[ten], chuan(v)))
                        doi.append(ten)
                if doi and tab.tu_dong_cap_nhat:
                    o_ghi.append((r, cot[tab.tu_dong_cap_nhat], bay_gio()))
                if doi:
                    kq.cap_nhat[k] = doi
                else:
                    kq.giu_nguyen.append(k)
            else:
                moi = [""] * so_cot_tieu_de
                for ten, v in d.items():
                    if ten == COT_DUYET and ngoai_le_duyet != "khoi_tao":
                        continue
                    if v is not None:
                        moi[cot[ten] - 1] = chuan(v)
                if tab.tu_dong_cap_nhat:
                    moi[cot[tab.tu_dong_cap_nhat] - 1] = bay_gio()
                dong_moi.append(moi)
                kq.them.append(k)

        if thu:
            return kq
        if o_ghi:
            # Người dùng có thể vừa chèn/xóa/sắp xếp dòng: kiểm tra lại khóa của từng dòng đích.
            moi_nhat = ws.doc_tat_ca()
            cot2 = ban_do_cot(moi_nhat[0] if moi_nhat else [])
            lech = cot2 != cot or any(
                r - 1 >= len(moi_nhat) or _khoa(tab, moi_nhat[r - 1], cot) != k for k, r in vi_tri.items()
                if k in kq.cap_nhat)
            if lech:
                continue
            ws.ghi_o(o_ghi)
        if dong_moi:
            ws.them_dong(dong_moi)
        return kq
    raise LoiDongDoiCho(f"Tab {tab.ten!r}: dòng bị thay đổi liên tục trong lúc ghi, đã thử {SO_LAN_THU} lần. Chạy lại sau.")


def them_nhat_ky(bang: BangNguon, tab: Tab, dong: list[dict], *, thu: bool = False) -> int:
    """Thêm dòng vào tab chỉ-thêm (Nhật ký). Không bao giờ sửa dòng cũ."""
    if not tab.chi_them:
        raise LoiSheet(f"Tab {tab.ten!r} có khóa; dùng ghi_theo_khoa()")
    kiem_tra_cot_may(tab, dong)
    if thu or not dong:
        return len(dong)
    ws = tim_tab(bang, tab.ten)
    if ws is None:
        raise LoiCauTruc(f"Chưa có tab {tab.ten!r}: chạy `python -m may_reels sheet init` trước")
    hang = ws.doc_tat_ca()
    cot = ban_do_cot(hang[0] if hang else [])
    thieu = [t for t in tab.ten_cot if t not in cot]
    if thieu:
        raise LoiCauTruc(f"Tab {tab.ten!r} thiếu cột {thieu}: chạy `python -m may_reels sheet init`")
    rong = max(cot.values())
    rows = []
    for d in dong:
        moi = [""] * rong
        for ten, v in d.items():
            if v is not None:
                moi[cot[ten] - 1] = chuan(v)
        rows.append(moi)
    ws.them_dong(rows)
    return len(rows)


def doc_dong(bang: BangNguon, tab: Tab) -> list[dict[str, str]]:
    """Đọc mọi dòng có dữ liệu thành dict theo tên cột (cả cột máy và cột người)."""
    ws = tim_tab(bang, tab.ten)
    if ws is None:
        raise LoiCauTruc(f"Chưa có tab {tab.ten!r}")
    hang = ws.doc_tat_ca()
    cot = ban_do_cot(hang[0] if hang else [])
    out = []
    for h in hang[1:]:
        d = {ten: _o(h, i) for ten, i in cot.items()}
        if any(d.values()):
            out.append(d)
    return out


def danh_ma_dong(bang: BangNguon, tab: Tab, tao_ma: Callable[[dict[str, str]], str], *,
                 thu: bool = False) -> list[tuple[int, str]]:
    """Tab do NGƯỜI thêm dòng (Câu hỏi khách): đánh mã vào cột khóa (cột của máy, một cột) cho dòng có dữ liệu mà
    chưa có mã. Mã do `tao_ma(dòng)` tính từ nội dung; trùng mã đã có thì thêm hậu tố -2, -3...
    Ngay trước khi ghi đọc lại: dòng đích đổi nội dung (người chèn, xóa, sửa) thì tính lại, tối đa SO_LAN_THU lần.
    Trả về [(số dòng, mã)]. Không đụng cột nào khác."""
    if len(tab.khoa) != 1:
        raise LoiSheet(f"Tab {tab.ten!r}: danh_ma_dong cần đúng một cột khóa")
    k = tab.khoa[0]
    ws = tim_tab(bang, tab.ten)
    if ws is None:
        raise LoiCauTruc(f"Chưa có tab {tab.ten!r}: chạy `python -m may_reels sheet init` trước")
    for _ in range(SO_LAN_THU):
        hang = ws.doc_tat_ca()
        cot = ban_do_cot(hang[0] if hang else [])
        thieu = [t for t in tab.ten_cot if t not in cot]
        if thieu:
            raise LoiCauTruc(f"Tab {tab.ten!r} thiếu cột {thieu}: chạy `python -m may_reels sheet init`")
        da_co = {_o(h, cot[k]) for h in hang[1:]} - {""}
        can: list[tuple[int, str, list[str]]] = []
        for so_dong, h in enumerate(hang[1:], start=2):
            d = {ten: _o(h, i) for ten, i in cot.items()}
            if d.get(k) or not any(d.get(c) for c in tab.cot_nguoi):
                continue
            goc_ma = tao_ma(d)
            ma, n = goc_ma, 2
            while ma in da_co:
                ma, n = f"{goc_ma}-{n}", n + 1
            da_co.add(ma)
            can.append((so_dong, ma, list(h)))
        if thu or not can:
            return [(r, m) for r, m, _h in can]
        moi = ws.doc_tat_ca()
        if ban_do_cot(moi[0] if moi else []) != cot or any(
                r - 1 >= len(moi) or [chuan(x) for x in moi[r - 1]] != [chuan(x) for x in h] for r, _m, h in can):
            continue
        ws.ghi_o([(r, cot[k], m) for r, m, _h in can])
        return [(r, m) for r, m, _h in can]
    raise LoiDongDoiCho(f"Tab {tab.ten!r}: dòng bị thay đổi liên tục trong lúc đánh mã, đã thử {SO_LAN_THU} lần.")
