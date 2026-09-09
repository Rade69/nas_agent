"""Windows Job Object pomoćni modul (QM-1).

Dodjeljuje backend pod-proces u Windows Job Object sa
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, tako da OS kernel garantovano ubija dijete
kad god roditeljski proces nestane (uredan izlaz, crash, TerminateProcess,
gašenje struje) — bez ikakvog koda na backend strani. Implementirano preko
ctypes-a, bez zavisnosti od pywin32. Na non-Windows platformama funkcije su
no-op (vraćaju None) — living-parent polling se dodaje u QM-9b/c.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_ulonglong),
        ("PerJobUserTimeLimit", ctypes.c_ulonglong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),  # ULONG_PTR
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _kernel32.OpenProcess.restype = ctypes.c_void_p
    _kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
else:
    _kernel32 = None


def assign_to_job_object(pid: int) -> int | None:
    """Dodijeli proces u job sa KILL_ON_JOB_CLOSE; vraća job handle (caller ga
    drži otvorenim dok backend živi) ili None ako mehanizam nije dostupan."""
    if _kernel32 is None:
        return None

    hjob = _kernel32.CreateJobObjectW(None, None)
    if not hjob:
        return None

    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = _kernel32.SetInformationJobObject(
        hjob,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        _kernel32.CloseHandle(hjob)
        return None

    hproc = _kernel32.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
    if not hproc:
        _kernel32.CloseHandle(hjob)
        return None

    ok = _kernel32.AssignProcessToJobObject(hjob, hproc)
    _kernel32.CloseHandle(hproc)
    if not ok:
        _kernel32.CloseHandle(hjob)
        return None

    return hjob


def close_job_object(handle: int | None) -> None:
    """Zatvori job handle — KILL_ON_JOB_CLOSE tada ubija dijete (ili, ako je
    handle nestao jer je roditelj umro, kernel je već ubio job)."""
    if handle is None or _kernel32 is None:
        return
    _kernel32.CloseHandle(handle)
