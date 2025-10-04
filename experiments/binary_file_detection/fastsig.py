
"""
fastsig.py
-----------
A small, bindet-inspired binary file type detector focused on speed.

Design highlights:
- Two-pass strategy (start, end) with memory-mapped I/O to avoid unnecessary copies.
- Anchored checks for "magic numbers" near the start of the file.
- Optional tail scan for formats whose canonical marker is at the end (e.g., ZIP EOCD, PDF %%EOF).
- Optional bounded search windows (e.g., RAR SFX can place the magic up to 1 MiB from start).

Pure standard library only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Iterable, Tuple, Dict, Any
import mmap
import os

# Tunables (adjust if you like)
HEAD_WINDOW = 4096                  # bytes from the start we always map/check
ZIP_TAIL_WINDOW = 70 * 1024         # EOCD + max comment (~65535) + a little slack
PDF_TAIL_WINDOW = 8 * 1024          # usually enough to see %%EOF
RAR_SFX_MAX = 1 * 1024 * 1024       # per RAR note: SFX may be up to ~1 MiB before archive

@dataclass(frozen=True)
class Match:
    kind: str
    confidence: float
    details: Optional[str] = None
    full: bool = True

def _startswith(buf: memoryview, sig: bytes, offset: int = 0) -> bool:
    if offset + len(sig) > len(buf):
        return False
    return buf[offset:offset + len(sig)] == sig

def _equals(buf: memoryview, start: int, sig: bytes) -> bool:
    end = start + len(sig)
    if end > len(buf):
        return False
    return buf[start:end] == sig

def _find_within(buf: memoryview, sig: bytes, limit: int) -> int:
    # memoryview doesn't have .find, so cast to bytes once (slice-limited)
    return bytes(buf[:limit]).find(sig)

def _rfind_within(buf: memoryview, sig: bytes, limit_from_end: int) -> int:
    tail = bytes(buf[-limit_from_end:]) if limit_from_end < len(buf) else bytes(buf)
    return tail.rfind(sig)

def _riff_form(buf: memoryview, form: bytes) -> bool:
    # RIFF container check: b"RIFF" + 4 size bytes + form (e.g., b"WAVE", b"AVI ", b"WEBP")
    return _startswith(buf, b"RIFF", 0) and _startswith(buf, form, 8)

def _macho_magic(u32: int) -> bool:
    return u32 in (
        0xFEEDFACE, 0xFEEDFACF, 0xCEFAEDFE, 0xCFFAEDFE,  # Mach-O 32/64 LE/BE
        0xCAFEBABE, 0xBEBAFECA                          # Universal / fat binary
    )

def _u32_le(buf: memoryview, offset: int = 0) -> int:
    if offset + 4 > len(buf): return -1
    b0, b1, b2, b3 = buf[offset:offset+4]
    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)

def detect_file(path: str) -> Optional[Match]:
    """Detect a file's type.
    Fast path: magic at start. Slow path: bounded tail scan or bounded head scan.
    Returns a Match or None if unknown.
    """
    try:
        size = os.path.getsize(path)
        if size == 0:
            return None
        with open(path, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            mv = memoryview(mm)

            # Head slice
            head_len = min(HEAD_WINDOW, len(mv))
            head = mv[:head_len]

            # 1) Strong start-anchored signatures
            if _startswith(head, b"\x89PNG\r\n\x1a\n"):
                return Match("png", 0.99, "PNG signature @ 0", True)

            if _startswith(head, b"\xFF\xD8\xFF"):  # JPEG SOI + marker
                return Match("jpeg", 0.9, "JPEG SOI", False)  # probable; could validate EOI

            if _startswith(head, b"GIF87a") or _startswith(head, b"GIF89a"):
                return Match("gif", 0.99, "GIF header", True)

            if _riff_form(head, b"WAVE"):
                return Match("wav", 0.99, "RIFF/WAVE", True)

            if _riff_form(head, b"AVI "):
                return Match("avi", 0.99, "RIFF/AVI", True)

            if _riff_form(head, b"WEBP"):
                return Match("webp", 0.99, "RIFF/WEBP", True)

            if _startswith(head, b"fLaC"):
                return Match("flac", 0.99, "fLaC header", True)

            if _startswith(head, b"OggS"):
                # Could peek for 'OpusHead' or 'vorbis' a bit later; keep it simple
                return Match("ogg", 0.9, "Ogg container", False)

            if _startswith(head, b"%PDF-"):
                # Check for EOF marker near end
                tail_window = min(PDF_TAIL_WINDOW, len(mv))
                if _rfind_within(mv, b"%%EOF", tail_window) != -1:
                    return Match("pdf", 0.99, "PDF header + EOF near end", True)
                else:
                    return Match("pdf", 0.7, "PDF header only", False)

            if _startswith(head, b"\x7fELF"):
                return Match("elf", 0.99, "ELF magic", True)

            # Mach-O / fat binaries: check first u32
            if head_len >= 4 and _macho_magic(_u32_le(head, 0)):
                return Match("macho", 0.95, "Mach-O/Fat magic", False)

            # xz: FD 37 7A 58 5A 00
            if _startswith(head, b"\xFD7zXZ\x00"):
                return Match("xz", 0.99, "xz header", True)

            # zstd: 28 B5 2F FD
            if _startswith(head, b"\x28\xB5\x2F\xFD"):
                return Match("zstd", 0.99, "zstd header", True)

            # gzip: 1F 8B 08
            if _startswith(head, b"\x1F\x8B\x08"):
                return Match("gzip", 0.99, "gzip header", True)

            # 7z: 37 7A BC AF 27 1C
            if _startswith(head, b"\x37\x7A\xBC\xAF\x27\x1C"):
                return Match("7z", 0.99, "7z header", True)

            # tar: "ustar" at offset 257
            if head_len >= 262 and _equals(head, 257, b"ustar"):
                return Match("tar", 0.95, "ustar field at 257", False)

            # wasm: 00 61 73 6D + version
            if _startswith(head, b"\x00asm"):
                return Match("wasm", 0.99, "WASM magic", True)

            # Java class: CA FE BA BE
            if _startswith(head, b"\xCA\xFE\xBA\xBE"):
                return Match("java-class", 0.99, "CAFEBABE", True)

            # ICO: 00 00 01 00
            if _startswith(head, b"\x00\x00\x01\x00"):
                return Match("ico", 0.99, "ICO", True)

            # BMP: 42 4D
            if _startswith(head, b"BM"):
                return Match("bmp", 0.9, "BMP", False)

            # MP3: ID3 tag (not exhaustive)
            if _startswith(head, b"ID3"):
                return Match("mp3", 0.8, "ID3 tag", False)

            # 2) End-anchored or start-window scans

            # ZIP: look for EOCD near end. Note: EOCD is 'PK\x05\x06'.
            tail_scan = min(ZIP_TAIL_WINDOW, len(mv))
            if _rfind_within(mv, b"PK\x05\x06", tail_scan) != -1 or _rfind_within(mv, b"PK\x06\x06", tail_scan) != -1:
                return Match("zip", 0.95, "EOCD near end", True)

            # RAR: RAR4 and RAR5 signatures can appear after SFX up to ~1 MiB.
            head_scan = min(RAR_SFX_MAX, len(mv))
            pos_rar4 = _find_within(mv, b"Rar!\x1A\x07\x00", head_scan)
            pos_rar5 = _find_within(mv, b"Rar!\x1A\x07\x01\x00", head_scan)
            if pos_rar4 != -1 or pos_rar5 != -1:
                return Match("rar", 0.95, "RAR signature within SFX window", True)

            # Unknown
            return None
    except (OSError, ValueError):
        return None

# Convenience: batch detection (helps when you want to overlap I/O with threads)
def detect_many(paths: Iterable[str]) -> Dict[str, Optional[Match]]:
    out: Dict[str, Optional[Match]] = {}
    for p in paths:
        out[p] = detect_file(p)
    return out

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python -m fastsig <file> [more files...]")
        sys.exit(2)
    result = {p: (detect_file(p).__dict__ if detect_file(p) else None) for p in sys.argv[1:]}
    print(json.dumps(result, indent=2))
