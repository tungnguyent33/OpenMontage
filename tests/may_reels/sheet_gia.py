"""Google Sheet giả trong bộ nhớ, cùng giao diện với may_reels.sheet.GspreadBangTinh. Không gọi mạng."""
from __future__ import annotations

from typing import Callable


class TabGia:
    def __init__(self, title: str, sheet_id: int, so_dong: int = 1000, so_cot: int = 26):
        self.title = title
        self.sheet_id = sheet_id
        self.so_cot = so_cot
        self.so_dong = so_dong
        self.o: list[list[str]] = []
        self.lan_ghi: list[list[tuple[int, int, str]]] = []
        self.lan_them: list[list[list[str]]] = []
        self.so_lan_doc = 0
        self.truoc_khi_doc: Callable[["TabGia", int], None] | None = None  # giả lập người sửa Sheet

    # --- tiện ích cho test (giả lập thao tác của người) ---
    def dat(self, dong: int, cot: int, v: str) -> None:
        while len(self.o) < dong:
            self.o.append([])
        h = self.o[dong - 1]
        while len(h) < cot:
            h.append("")
        h[cot - 1] = v

    def lay(self, dong: int, cot: int) -> str:
        if dong - 1 < len(self.o) and cot - 1 < len(self.o[dong - 1]):
            return self.o[dong - 1][cot - 1]
        return ""

    def chen_dong(self, truoc_dong: int, gia_tri: list[str]) -> None:
        self.o.insert(truoc_dong - 1, list(gia_tri))

    # --- giao diện TabNguon ---
    def doc_tat_ca(self) -> list[list[str]]:
        self.so_lan_doc += 1
        if self.truoc_khi_doc:
            self.truoc_khi_doc(self, self.so_lan_doc)
        rong = max((len(h) for h in self.o), default=0)
        hang = [h + [""] * (rong - len(h)) for h in self.o]
        while hang and not any(hang[-1]):
            hang.pop()
        return [list(h) for h in hang]

    def ghi_o(self, o):
        o = list(o)
        self.lan_ghi.append(o)
        for d, c, v in o:
            if c > self.so_cot:
                raise IndexError(f"cột {c} vượt quá {self.so_cot}")
            self.dat(d, c, v)

    def them_dong(self, dong):
        self.lan_them.append([list(h) for h in dong])
        cuoi = len(self.doc_tat_ca_khong_dem())
        for i, h in enumerate(dong, start=cuoi + 1):
            for c, v in enumerate(h, start=1):
                self.dat(i, c, v)

    def doc_tat_ca_khong_dem(self):
        hang = [list(h) for h in self.o]
        while hang and not any(hang[-1]):
            hang.pop()
        return hang

    def mo_rong_cot(self, so_cot_them: int) -> None:
        self.so_cot += so_cot_them


class BangGia:
    def __init__(self):
        self.tabs: list[TabGia] = []
        self.yeu_cau_dinh_dang: list[dict] = []

    def danh_sach_tab(self):
        return list(self.tabs)

    def tao_tab(self, ten: str, so_dong: int, so_cot: int) -> TabGia:
        t = TabGia(ten, 100 + len(self.tabs), so_dong, so_cot)
        self.tabs.append(t)
        return t

    def dinh_dang(self, yeu_cau):
        self.yeu_cau_dinh_dang.extend(yeu_cau)

    def tab(self, ten: str) -> TabGia:
        return next(t for t in self.tabs if t.title == ten)
