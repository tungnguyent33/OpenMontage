"""Dữ liệu chiến lược nội dung của kênh: đọc và kiểm tra (prompt C0, 2026-11-20).

Nguồn sự thật về nội dung: docs/may-reels/CHIEN-LUOC-NOI-DUNG.md (chỉ ở trên máy). Dữ liệu máy đọc nằm ở brand/<kênh>/:

  file             commit?  ghi chú
  doi-tuong.yaml   không    nhóm đối tượng n1..; repo có doi-tuong.mau.yaml
  dinh-vi.yaml     không    lời hứa, trụ của lời hứa; repo có dinh-vi.mau.yaml
  ban-hang.yaml    không    học phí, giấy tờ, lịch, ưu đãi, mồi nhử. MÁY KHÔNG TỰ ĐIỀN; repo có ban-hang.mau.yaml
  dinh-dang.yaml   có       thư viện định dạng, khung nhịp
  lich.yaml        có       lịch tuần, mùa

File riêng (không commit) mà thiếu: báo cần tạo từ bản mẫu, không tự dùng bản mẫu thay.
`python -m may_reels chien-luoc kiem-tra --kenh <mã>` in báo cáo: lỗi schema, tham chiếu sai, mục trống, ưu đãi hết
hạn, định dạng thiếu cảnh trong kho (khớp canh_can với thẻ / loại của kho_canh dùng được), giả thuyết chưa xác nhận.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

GOC = Path(__file__).resolve().parent.parent
TZ_VN = dt.timezone(dt.timedelta(hours=7))
FILE_RIENG = ("doi-tuong", "dinh-vi", "ban-hang")   # dữ liệu kinh doanh thật: .gitignore, có bản .mau.yaml
FILE_CHUNG = ("dinh-dang", "lich")
TAT_CA = FILE_RIENG + FILE_CHUNG
# Khóa được phép để trống khi tìm "mục trống"
BO_QUA_TRONG = {"ghi_chu", "do_tuoi", "dieu_kien", "khong_lam", "doi_thu_so_sanh", "dieu_kien_duoc_noi", "nguon",
                "pham_vi", "han_dang_ky", "ngay_cap_nhat", "thoi_gian_hoc", "theo_cau_hoi",
                "nhom_chinh"}  # nhom_chinh rỗng = mọi nhóm (dinh-dang.yaml)


class LoiChienLuoc(RuntimeError):
    pass


class LoiThieuFile(LoiChienLuoc):
    pass


def _chuoi_hoa_ngay(x):
    """YAML đọc 2026-11-20 thành date; schema kiểm chuỗi YYYY-MM-DD."""
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()[:10]
    if isinstance(x, dict):
        return {k: _chuoi_hoa_ngay(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_chuoi_hoa_ngay(v) for v in x]
    return x


def duong_dan(kenh: str, ten: str, goc: Path = GOC, mau: bool = False) -> Path:
    return goc / "brand" / kenh / (f"{ten}.mau.yaml" if mau else f"{ten}.yaml")


def doc(kenh: str, ten: str, goc: Path = GOC) -> dict:
    """Đọc file thật. File riêng chưa có: LoiThieuFile kèm cách tạo từ bản mẫu."""
    p = duong_dan(kenh, ten, goc)
    if not p.is_file():
        if ten in FILE_RIENG and duong_dan(kenh, ten, goc, mau=True).is_file():
            raise LoiThieuFile(f"Chưa có brand/{kenh}/{ten}.yaml (chỉ để trên máy, không commit). Tạo từ bản mẫu: "
                               f"copy brand\\{kenh}\\{ten}.mau.yaml brand\\{kenh}\\{ten}.yaml rồi điền.")
        raise LoiThieuFile(f"Chưa có brand/{kenh}/{ten}.yaml")
    return _chuoi_hoa_ngay(yaml.safe_load(p.read_text(encoding="utf-8")) or {})


def loi_schema(ten: str, du_lieu: dict, goc: Path = GOC) -> list[str]:
    import jsonschema
    sc = json.loads((goc / "schemas" / "may-reels" / f"{ten}.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(sc)
    return [f"{ten}.yaml: {'/'.join(map(str, e.absolute_path)) or '(gốc)'}: {e.message}"
            for e in sorted(v.iter_errors(du_lieu), key=lambda e: list(map(str, e.absolute_path)))]


def _trong(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def muc_trong(du_lieu, duong: str = "") -> list[str]:
    """Các ô trống (""/null/[]), bỏ các khóa trong BO_QUA_TRONG. Mục danh sách chỉ có một phần tử toàn trống = 1 dòng."""
    ra: list[str] = []
    if isinstance(du_lieu, dict):
        for k, v in du_lieu.items():
            if k in BO_QUA_TRONG:
                continue
            p = f"{duong}.{k}" if duong else k
            if _trong(v):
                ra.append(p)
            else:
                ra += muc_trong(v, p)
    elif isinstance(du_lieu, list):
        for i, v in enumerate(du_lieu):
            ra += muc_trong(v, f"{duong}[{_nhan(v, i)}]")
    return ra


def _nhan(v, i: int) -> str:
    """Nhãn phần tử danh sách: mã (hoặc thứ) nếu có, không thì số thứ tự."""
    if isinstance(v, dict):
        for k in ("ma", "thu"):
            if v.get(k) not in (None, ""):
                return str(v[k])
    return str(i)


def gia_thuyet(du_lieu, duong: str = "") -> list[str]:
    """Đường dẫn các mục có trang_thai: gia_thuyet (kèm ma/ten nếu có cho dễ đọc)."""
    ra: list[str] = []
    if isinstance(du_lieu, dict):
        if du_lieu.get("trang_thai") == "gia_thuyet":
            ra.append(duong)
        for k, v in du_lieu.items():
            if isinstance(v, (dict, list)):
                ra += gia_thuyet(v, f"{duong}.{k}" if duong else k)
    elif isinstance(du_lieu, list):
        for i, v in enumerate(du_lieu):
            ra += gia_thuyet(v, f"{duong}[{_nhan(v, i)}]")
    return ra


def dinh_dang_thieu_canh(dinh_dang: dict, kho_canh: list[dict]) -> dict[str, list[str]]:
    """{mã định dạng: [mô tả loại cảnh không có cảnh dùng được nào khớp]}. Cảnh máy tự dựng thì bỏ qua."""
    kho = [k for k in kho_canh if k.get("dung_duoc")]
    ra: dict[str, list[str]] = {}
    for d in dinh_dang.get("dinh_dang") or []:
        thieu = []
        for c in d.get("canh_can") or []:
            if c.get("may_tu_dung"):
                continue
            the, loai = set(c.get("the_bat_ky") or []), set(c.get("loai_bat_ky") or [])
            if not any(the & set(k.get("the") or []) or k.get("loai") in loai for k in kho):
                thieu.append(c["mo_ta"])
        if thieu:
            ra[d["ma"]] = thieu
    return ra


def _co_so_lieu(ban_hang: dict | None, muc: str) -> bool:
    """ban-hang.yaml có mục này với ít nhất một phần tử đã xác nhận và không trống chưa."""
    if not ban_hang:
        return False
    v = ban_hang.get(muc)
    ds = v if isinstance(v, list) else [v] if isinstance(v, dict) else []
    return any(isinstance(x, dict) and x.get("trang_thai") == "da_xac_nhan" and not muc_trong(x) for x in ds)


# định dạng cần số liệu đã xác nhận trong ban-hang.yaml mới làm được (theo dieu_kien trong dinh-dang.yaml)
CAN_SO_LIEU = {"hoc-phi-gom-gi": ["khoa_hoc"], "dang-ky-mang-gi": ["giay_to", "quy_trinh_dang_ky"],
               "lich-khai-giang": ["lich_khai_giang"], "hoc-vien-ke": ["nguoi_dong_y_len_hinh"]}


@dataclass
class BaoCao:
    kenh: str
    hom_nay: str
    thieu_file: list[str] = field(default_factory=list)
    loi_schema: list[str] = field(default_factory=list)
    loi_tham_chieu: list[str] = field(default_factory=list)
    muc_trong: dict[str, list[str]] = field(default_factory=dict)
    uu_dai_het_han: list[str] = field(default_factory=list)
    uu_dai_xem_lai: list[str] = field(default_factory=list)   # ưu đãi thường xuyên đã quá ngay_xem_lai
    thieu_canh: dict[str, list[str]] = field(default_factory=dict)
    chua_du_so_lieu: dict[str, list[str]] = field(default_factory=dict)
    gia_thuyet: dict[str, list[str]] = field(default_factory=dict)
    cho_xac_nhan: list[str] = field(default_factory=list)
    mua: str = ""

    @property
    def loi(self) -> bool:
        return bool(self.thieu_file or self.loi_schema or self.loi_tham_chieu)


def kiem_tra(kenh: str, goc: Path = GOC, hom_nay: dt.date | None = None) -> BaoCao:
    hom_nay = hom_nay or dt.datetime.now(TZ_VN).date()
    bc = BaoCao(kenh, hom_nay.isoformat())
    dl: dict[str, dict] = {}
    for ten in TAT_CA:
        try:
            dl[ten] = doc(kenh, ten, goc)
        except LoiThieuFile as e:
            bc.thieu_file.append(str(e))
            continue
        bc.loi_schema += loi_schema(ten, dl[ten], goc)
    if bc.loi_schema:
        return bc  # dữ liệu sai cấu trúc: không kiểm tiếp để tránh báo lỗi dây chuyền

    # tham chiếu chéo
    nhom = {n["ma"] for n in (dl.get("doi-tuong") or {}).get("nhom") or []}
    dd = dl.get("dinh-dang") or {}
    ma_dd = [d["ma"] for d in dd.get("dinh_dang") or []]
    for m in {m for m in ma_dd if ma_dd.count(m) > 1}:
        bc.loi_tham_chieu.append(f"dinh-dang.yaml: mã {m} bị trùng")
    sx_p = goc / "brand" / kenh / "san-xuat.yaml"
    khung = {}
    if sx_p.is_file():
        khung = (yaml.safe_load(sx_p.read_text(encoding="utf-8")) or {}).get("khung_nhip") or {}
    for d in dd.get("dinh_dang") or []:
        if d.get("khung_nhip") and d["khung_nhip"] not in khung:
            bc.loi_tham_chieu.append(f"dinh-dang.yaml {d['ma']}: khung_nhip {d['khung_nhip']!r} không có trong san-xuat.yaml")
        if nhom:
            for n in d.get("nhom_chinh") or []:
                if n not in nhom:
                    bc.loi_tham_chieu.append(f"dinh-dang.yaml {d['ma']}: nhóm {n} không có trong doi-tuong.yaml")
    lich = dl.get("lich") or {}
    for t in lich.get("tuan") or []:
        for m in t.get("dinh_dang") or []:
            if ma_dd and m not in ma_dd:
                bc.loi_tham_chieu.append(f"lich.yaml thứ {t['thu']}: định dạng {m} không có trong dinh-dang.yaml")
    ma_mua = {m["ma"]: m for m in lich.get("mua") or []}
    for m in ma_mua.values():
        for n in m.get("nhom") or []:
            if nhom and n not in nhom:
                bc.loi_tham_chieu.append(f"lich.yaml mùa {m['ma']}: nhóm {n} không có trong doi-tuong.yaml")
    md = lich.get("mua_dang_chay")
    if md:
        if md not in ma_mua:
            bc.loi_tham_chieu.append(f"lich.yaml: mua_dang_chay {md!r} không có trong danh sách mùa")
        else:
            m = ma_mua[md]
            trong_mua = (not m.get("tu_ngay") or m["tu_ngay"] <= bc.hom_nay) and \
                        (not m.get("den_ngay") or bc.hom_nay <= m["den_ngay"])
            bc.mua = f"{m['ten']} ({m.get('tu_ngay')} → {m.get('den_ngay')})" + ("" if trong_mua else ": ĐÃ NGOÀI NGÀY CỦA MÙA")
    bh = dl.get("ban-hang")
    for mn in (bh or {}).get("moi_nhu") or []:
        for n in mn.get("nhom_hop") or []:
            if nhom and n not in nhom:
                bc.loi_tham_chieu.append(f"ban-hang.yaml mồi {mn.get('ma')!r}: nhóm {n} không có trong doi-tuong.yaml")

    # mục trống, giả thuyết
    theo_su_kien = {m["ma"] for m in lich.get("mua") or [] if m.get("theo_su_kien")}
    for ten, d in dl.items():
        tr = muc_trong({k: v for k, v in d.items() if k != "cho_xac_nhan"})
        if ten == "lich":  # mùa tính theo sự kiện thì không có ngày cố định: không tính là ô trống
            tr = [x for x in tr if not any(x in (f"mua[{m}].tu_ngay", f"mua[{m}].den_ngay") for m in theo_su_kien)]
        if ten == "ban-hang":  # ưu đãi thường xuyên không có het_han; ưu đãi có hạn không cần ngay_xem_lai
            bo = {f"uu_dai[{i}].{'het_han' if u.get('thuong_xuyen') else 'ngay_xem_lai'}"
                  for i, u in enumerate(d.get("uu_dai") or []) if isinstance(u, dict)}
            tr = [x for x in tr if x not in bo]
        if tr:
            bc.muc_trong[ten] = tr
        gt = gia_thuyet(d)
        if gt:
            bc.gia_thuyet[ten] = gt
    if bh:
        for u in bh.get("uu_dai") or []:
            if not u.get("noi_dung"):
                continue
            if u.get("thuong_xuyen"):  # ưu đãi thường xuyên: không có hạn, chỉ báo khi quá ngày xem lại
                if u["ngay_xem_lai"] < bc.hom_nay:
                    bc.uu_dai_xem_lai.append(f"{u['noi_dung']} (ngày xem lại {u['ngay_xem_lai']})")
            elif not u.get("het_han") or u["het_han"] < bc.hom_nay:
                bc.uu_dai_het_han.append(f"{u['noi_dung']} (hết hạn {u.get('het_han') or 'chưa ghi ngày'})")
        bc.cho_xac_nhan = [c["noi_dung"] for c in bh.get("cho_xac_nhan") or [] if c.get("noi_dung")]
    for ma, muc in CAN_SO_LIEU.items():
        if ma in ma_dd:
            thieu = [m for m in muc if not _co_so_lieu(bh, m)]
            if thieu:
                bc.chua_du_so_lieu[ma] = thieu

    # cảnh trong kho
    bj = goc / "brand" / kenh / "brand.json"
    kho = (json.loads(bj.read_text(encoding="utf-8")).get("kho_canh") or []) if bj.is_file() else []
    bc.thieu_canh = dinh_dang_thieu_canh(dd, kho)
    return bc


def in_bao_cao(bc: BaoCao, chi_tiet: bool = False) -> str:
    d = [f"Chiến lược nội dung kênh {bc.kenh} — kiểm ngày {bc.hom_nay}"]
    if bc.thieu_file:
        d += ["", "THIẾU FILE:"] + [f"  - {x}" for x in bc.thieu_file]
    if bc.loi_schema:
        d += ["", "LỖI CẤU TRÚC (schema):"] + [f"  - {x}" for x in bc.loi_schema]
    if bc.loi_tham_chieu:
        d += ["", "THAM CHIẾU SAI:"] + [f"  - {x}" for x in bc.loi_tham_chieu]
    if bc.mua:
        d += ["", f"Mùa đang chạy: {bc.mua}"]
    if bc.uu_dai_het_han:
        d += ["", "ƯU ĐÃI HẾT HẠN (máy không dùng):"] + [f"  - {x}" for x in bc.uu_dai_het_han]
    if bc.uu_dai_xem_lai:
        d += ["", "ƯU ĐÃI THƯỜNG XUYÊN QUÁ NGÀY XEM LẠI (xác nhận còn áp dụng rồi dời ngay_xem_lai; máy vẫn dùng):"]
        d += [f"  - {x}" for x in bc.uu_dai_xem_lai]
    if bc.chua_du_so_lieu:
        d += ["", "ĐỊNH DẠNG CHƯA LÀM ĐƯỢC vì ban-hang.yaml chưa có số liệu đã xác nhận:"]
        d += [f"  - {m}: cần {', '.join(v)}" for m, v in bc.chua_du_so_lieu.items()]
    if bc.thieu_canh:
        d += ["", "ĐỊNH DẠNG THIẾU CẢNH TRONG KHO (không có cảnh dùng được khớp thẻ/loại):"]
        d += [f"  - {m}: {'; '.join(v)}" for m, v in bc.thieu_canh.items()]
    if bc.muc_trong:
        d += ["", "MỤC TRỐNG:"]
        for ten, ds in bc.muc_trong.items():
            d.append(f"  {ten}.yaml: {len(ds)} ô" + ("" if chi_tiet else f" (ví dụ: {', '.join(ds[:6])}{' …' if len(ds) > 6 else ''})"))
            if chi_tiet:
                d += [f"    - {x}" for x in ds]
    if bc.cho_xac_nhan:
        d += ["", "CHỜ XÁC NHẬN (ban-hang.yaml cho_xac_nhan, máy không dùng):"] + [f"  - {x}" for x in bc.cho_xac_nhan]
    if bc.gia_thuyet:
        d += ["", "GIẢ THUYẾT CHƯA XÁC NHẬN:"]
        for ten, ds in bc.gia_thuyet.items():
            d.append(f"  {ten}.yaml: {len(ds)} mục" + ("" if chi_tiet else f" ({', '.join(ds[:5])}{' …' if len(ds) > 5 else ''})"))
            if chi_tiet:
                d += [f"    - {x}" for x in ds]
    d += ["", "KẾT LUẬN: " + ("CÓ LỖI, sửa trước khi dùng" if bc.loi else "cấu trúc đúng; còn việc cần người điền/xác nhận ở trên")]
    return "\n".join(d)
