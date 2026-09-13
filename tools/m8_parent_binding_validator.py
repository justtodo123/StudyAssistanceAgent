"""Read-only P2 parent-binding validator for Windows.

This program never creates, mutates, enumerates by path, or deletes an object.
It opens the volume root and each target component with NtCreateFile using a
relative RootDirectory handle, FILE_OPEN_REPARSE_POINT, and full sharing.
The emitted payloads are only valid after every invariant is checked.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys

ntdll = ctypes.WinDLL("ntdll.dll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

NTSTATUS_SUCCESS = 0
STATUS_BUFFER_TOO_SMALL = 0xC0000023
STATUS_BUFFER_OVERFLOW = 0x80000005
STATUS_OBJECT_NAME_NOT_FOUND = 0xC0000034
STATUS_REPARSE_POINT_ENCOUNTERED = 0xC000050B

OBJ_CASE_INSENSITIVE = 0x00000040
FILE_OPEN = 0x00000001
FILE_DIRECTORY_FILE = 0x00000001
FILE_NON_DIRECTORY_FILE = 0x00000040
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_LIST_DIRECTORY = 0x00000001
FILE_READ_ATTRIBUTES = 0x00000080
SYNCHRONIZE = 0x00100000
READ_CONTROL = 0x00020000
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
FILE_SHARE_DELETE = 0x4
SECURITY_INFORMATION = 0x00000007  # owner | group | dacl
SE_FILE_OBJECT = 0x00000001

FileStandardInformation = 5
FileInternalInformation = 6
FileStreamInformation = 22
FileAttributeTagInformation = 35
FileIdInformation = 59

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

class UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT),
                ("Buffer", wintypes.LPWSTR)]

class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Length", wintypes.ULONG), ("RootDirectory", wintypes.HANDLE),
                ("ObjectName", ctypes.POINTER(UNICODE_STRING)), ("Attributes", wintypes.ULONG),
                ("SecurityDescriptor", wintypes.LPVOID), ("SecurityQualityOfService", wintypes.LPVOID)]

class IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [("Status", wintypes.LONG), ("Information", ctypes.c_size_t)]

class FILE_ID_128(ctypes.Structure):
    _fields_ = [("Identifier", ctypes.c_ubyte * 16)]

class FILE_ID_INFORMATION(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_longlong), ("FileId", FILE_ID_128)]

class FILE_STANDARD_INFORMATION(ctypes.Structure):
    _fields_ = [("AllocationSize", ctypes.c_longlong), ("EndOfFile", ctypes.c_longlong),
                ("NumberOfLinks", wintypes.ULONG), ("DeletePending", wintypes.BOOLEAN),
                ("Directory", wintypes.BOOLEAN)]

class FILE_INTERNAL_INFORMATION(ctypes.Structure):
    _fields_ = [("IndexNumber", ctypes.c_longlong)]

class FILE_ATTRIBUTE_TAG_INFORMATION(ctypes.Structure):
    _fields_ = [("FileAttributes", wintypes.DWORD), ("ReparseTag", wintypes.DWORD)]

ntdll.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.ULONG,
    ctypes.POINTER(OBJECT_ATTRIBUTES), ctypes.POINTER(IO_STATUS_BLOCK), ctypes.c_void_p,
    wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG]
ntdll.NtCreateFile.restype = wintypes.LONG
ntdll.NtQueryInformationFile.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO_STATUS_BLOCK),
    ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG]
ntdll.NtQueryInformationFile.restype = wintypes.LONG
ntdll.NtQuerySecurityObject.argtypes = [wintypes.HANDLE, wintypes.ULONG, ctypes.c_void_p,
    wintypes.ULONG, ctypes.POINTER(wintypes.ULONG)]
ntdll.NtQuerySecurityObject.restype = wintypes.LONG
ntdll.NtClose.argtypes = [wintypes.HANDLE]
ntdll.NtClose.restype = wintypes.LONG
kernel32.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
    wintypes.LPWSTR, wintypes.DWORD]
kernel32.GetVolumeInformationW.restype = wintypes.BOOL


def nt_ok(status: int) -> bool:
    return status >= 0


def status_hex(status: int) -> str:
    return f"0x{status & 0xffffffff:08x}"


def checked(status: int, action: str) -> None:
    if not nt_ok(status):
        raise OSError(f"{action} failed with NTSTATUS {status_hex(status)}")


def unicode_string(text: str):
    buf = ctypes.create_unicode_buffer(text)
    us = UNICODE_STRING(len(text.encode("utf-16-le")), len(text.encode("utf-16-le")) + 2, ctypes.cast(buf, wintypes.LPWSTR))
    return us, buf


def open_nt(name: str, root: wintypes.HANDLE | None, directory: bool) -> wintypes.HANDLE:
    us, _keepalive = unicode_string(name)
    oa = OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES), root, ctypes.pointer(us), 0, None, None)
    iosb = IO_STATUS_BLOCK()
    handle = wintypes.HANDLE()
    access = READ_CONTROL | FILE_READ_ATTRIBUTES | SYNCHRONIZE | (FILE_LIST_DIRECTORY if directory else 0)
    options = FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT | (FILE_DIRECTORY_FILE if directory else FILE_NON_DIRECTORY_FILE)
    status = ntdll.NtCreateFile(ctypes.byref(handle), access, ctypes.byref(oa), ctypes.byref(iosb),
                                None, 0, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                FILE_OPEN, options, None, 0)
    checked(status, f"NtCreateFile({name!r})")
    return handle


def close(handle):
    if handle and handle.value not in (0, INVALID_HANDLE_VALUE):
        checked(ntdll.NtClose(handle), "NtClose")


def query_info(handle, klass, size):
    buf = ctypes.create_string_buffer(size)
    iosb = IO_STATUS_BLOCK()
    checked(ntdll.NtQueryInformationFile(handle, ctypes.byref(iosb), buf, size, klass),
            f"NtQueryInformationFile({klass})")
    return buf, int(iosb.Information)


def security_descriptor(handle) -> bytes:
    size = 4096
    while True:
        buf = ctypes.create_string_buffer(size)
        needed = wintypes.ULONG()
        status = ntdll.NtQuerySecurityObject(handle, SECURITY_INFORMATION, buf, size, ctypes.byref(needed))
        if status in (STATUS_BUFFER_TOO_SMALL, STATUS_BUFFER_OVERFLOW):
            size = max(size * 2, int(needed.value) + 1)
            continue
        checked(status, "NtQuerySecurityObject")
        return bytes(buf[: int(needed.value)])


def filesystem_for_volume(root: str) -> tuple[str, str]:
    drive = os.path.splitdrive(root)[0] + "\\"
    serial = wintypes.DWORD(); flags = wintypes.DWORD(); max_component = wintypes.DWORD()
    fs_name = ctypes.create_unicode_buffer(64)
    ok = kernel32.GetVolumeInformationW(drive, None, 0, ctypes.byref(serial), ctypes.byref(max_component),
                                        ctypes.byref(flags), fs_name, len(fs_name))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    fs = fs_name.value.lower()
    if fs not in {"ntfs", "refs"}:
        raise ValueError(f"unsupported filesystem {fs!r}; protocol allows ntfs/refs only")
    return fs, drive


def identity(handle, expected_fs: str, expected_serial: str | None = None) -> dict:
    raw, _ = query_info(handle, FileIdInformation, ctypes.sizeof(FILE_ID_INFORMATION))
    fi = FILE_ID_INFORMATION.from_buffer_copy(raw)
    file_id = bytes(fi.FileId.Identifier).hex()
    serial = f"{ctypes.c_ulonglong(fi.VolumeSerialNumber).value & 0xffffffffffffffff:016x}"
    std_raw, _ = query_info(handle, FileStandardInformation, ctypes.sizeof(FILE_STANDARD_INFORMATION))
    std = FILE_STANDARD_INFORMATION.from_buffer_copy(std_raw)
    if int(std.NumberOfLinks) != 1:
        raise ValueError(f"NumberOfLinks={std.NumberOfLinks}, expected 1")
    attrs_raw, _ = query_info(handle, FileAttributeTagInformation, ctypes.sizeof(FILE_ATTRIBUTE_TAG_INFORMATION))
    attrs = FILE_ATTRIBUTE_TAG_INFORMATION.from_buffer_copy(attrs_raw)
    if int(attrs.FileAttributes) & 0x400:
        raise ValueError("reparse point encountered; FILE_OPEN_REPARSE_POINT does not permit acceptance")
    streams = enumerate_streams(handle)
    if bool(std.Directory):
        # Directory and volume-root handles may legitimately report no stream
        # records. Any reported stream on a directory is rejected.
        if streams:
            raise ValueError(f"directory exposes unexpected streams: {streams!r}")
    elif streams != [":$DATA"]:
        raise ValueError(f"file exposes unexpected streams: {streams!r}")
    acl = security_descriptor(handle)
    if expected_serial and serial != expected_serial:
        raise ValueError(f"volume serial mismatch: {serial} != {expected_serial}")
    return {"volume_serial": serial, "filesystem": expected_fs, "file_id": file_id,
            "acl_sha256": hashlib.sha256(acl).hexdigest()}


def enumerate_streams(handle) -> list[str]:
    size = 4096
    while True:
        raw, used = query_info(handle, FileStreamInformation, size)
        data = raw[:used]
        names = []
        offset = 0
        while offset < len(data):
            if len(data) - offset < 24:
                raise ValueError("truncated FILE_STREAM_INFORMATION record")
            next_offset = int.from_bytes(data[offset:offset+4], "little")
            name_len = int.from_bytes(data[offset+4:offset+8], "little")
            name_start = offset + 24
            name_end = name_start + name_len
            if name_end > len(data):
                raise ValueError("truncated stream name")
            names.append(data[name_start:name_end].decode("utf-16-le"))
            if next_offset == 0:
                break
            if next_offset < 24 or offset + next_offset > len(data):
                raise ValueError("invalid stream record offset")
            offset += next_offset
        if names or used < size:
            return names
        size *= 2


def filesystem_for_volume_guid(native_device: str) -> tuple[str, str]:
    """Determine the filesystem of a GUID-addressed volume, read-only.

    GetVolumeInformationW also accepts a `\\\\?\\Volume{GUID}\\` path, so the
    same API used for drive letters is reused without inventing a mapping.
    """
    serial = wintypes.DWORD()
    flags = wintypes.DWORD()
    max_component = wintypes.DWORD()
    fs_name = ctypes.create_unicode_buffer(64)
    ok = kernel32.GetVolumeInformationW(native_device, None, 0,
                                        ctypes.byref(serial), ctypes.byref(max_component),
                                        ctypes.byref(flags), fs_name, len(fs_name))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    fs = fs_name.value.lower()
    if fs not in {"ntfs", "refs"}:
        raise ValueError(f"unsupported filesystem {fs!r}; protocol allows ntfs/refs only")
    return fs, native_device


def walk(volume_root: str, components: list[str]) -> tuple[dict, dict]:
    if not components or any(not c or c in {".", ".."} or "/" in c or "\\" in c or ":" in c or "\x00" in c for c in components):
        raise ValueError("components are not safe TARGET_COMPONENT values")
    fs, device = filesystem_for_volume(volume_root)
    root_handle = open_nt("\\??\\" + device, None, True)
    handles = [root_handle]
    try:
        root_id = identity(root_handle, fs)
        current = root_handle
        for component in components:
            child = open_nt(component, current, True)
            handles.append(child)
            # The component is accepted only after the opened handle itself
            # passes identity checks; this prevents path/case aliases from
            # being treated as the requested parent.
            child_id = identity(child, fs, root_id["volume_serial"])
            if child_id["file_id"] == root_id["file_id"] and components:
                raise ValueError("component walk returned volume root identity")
            current = child
        parent_id = identity(current, fs, root_id["volume_serial"])
        return root_id, parent_id
    finally:
        for handle in reversed(handles):
            close(handle)


VOLUME_GUID_PREFIX = "\\\\?\\Volume{"


def parse_volume_guid_path(path: str) -> tuple[str, list[str]]:
    """Split a `\\\\?\\Volume{GUID}\\<component>...` path without touching the fs."""
    text = str(path)
    if not text.startswith(VOLUME_GUID_PREFIX) or "}" not in text:
        raise ValueError(f"path is not a volume GUID path: {path}")
    end = text.index("}") + 1
    root = text[:end]
    if not root.endswith("\\"):
        root += "\\"
    remainder = text[end:].lstrip("\\")
    if not remainder:
        return root, []
    return root, remainder.split("\\")


def components_for(path: Path) -> tuple[str, list[str]]:
    text = str(path)
    if text.startswith(VOLUME_GUID_PREFIX):
        return parse_volume_guid_path(text)
    absolute = Path(os.path.abspath(text))
    drive = absolute.drive
    if not drive:
        raise ValueError(f"path has no drive: {path}")
    parts = list(absolute.parts)
    root = drive + "\\"
    if parts and parts[0].rstrip("\\") == drive.rstrip("\\"):
        parts = parts[1:]
    return root, parts


def validate(path) -> dict:
    root, components = components_for(path)
    volume_id, parent_id = walk(root, components)
    return {"volume_root": volume_id, "components": components, "parent": parent_id,
            "opened_by": "NtCreateFile", "walk": "volume-root-component-walk",
            "root_directory_relative": True, "share_mask": "read-write-delete", "no_follow": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=str)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = {str(path): validate(path) for path in args.paths}
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(encoded, encoding="utf-8", newline="\n")
    sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
