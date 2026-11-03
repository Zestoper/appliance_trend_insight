"""Render 무료 서버(512MB) 메모리 관리 도우미.

- rss_mb(): 지금 프로세스가 실제로 쓰는 메모리(MB)
- trim(): 파이썬 쓰레기 수거 + glibc가 쥐고 있는 빈 메모리를 운영체제에 돌려준다.
  큰 HTML을 파싱하고 나면 파이썬 객체는 지워져도 glibc가 메모리를 계속 쥐고 있어서
  실제 사용량(RSS)이 내려가지 않고 다음 작업과 겹쳐 512MB를 넘는다.
"""
import ctypes
import gc
import sys

_libc = None
if sys.platform.startswith("linux"):
    try:
        _libc = ctypes.CDLL("libc.so.6")
    except OSError:
        _libc = None


def rss_mb() -> int:
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return -1


def trim() -> int:
    gc.collect()
    if _libc is not None:
        try:
            _libc.malloc_trim(0)
        except Exception:
            pass
    return rss_mb()
