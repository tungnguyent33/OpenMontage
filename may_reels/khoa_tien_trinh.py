"""Khóa file ngăn hai tiến trình `dang` chạy cùng lúc.

Dùng khóa của hệ điều hành (msvcrt trên Windows, fcntl trên Linux/macOS): tiến trình
chết thì hệ điều hành tự nhả khóa, không để lại khóa "kẹt".
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path


class LoiDangChay(RuntimeError):
    pass


@contextmanager
def khoa(duong_dan: Path):
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    f = open(duong_dan, "a+", encoding="utf-8")
    try:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise LoiDangChay(f"Một tiến trình đăng bài khác đang chạy (khóa {duong_dan.name}). Thử lại sau.") from e
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    finally:
        f.close()
