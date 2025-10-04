# fastsig.py  (extended)
from __future__ import annotations

import mmap
import pathlib
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

# Tunables
HEAD_WINDOW = 4096  # bytes from the start we always map/check
ZIP_TAIL_WINDOW = 70 * 1024  # EOCD + max comment + slack
PDF_TAIL_WINDOW = 8 * 1024
RAR_SFX_MAX = 1 * 1024 * 1024  # RAR SFX preface window
HDF5_SCAN_LIMIT = 64 * 1024  # scan first 64 KiB for HDF5 at 512*N offsets
ZIP_SUBTYPE_TAIL = 256 * 1024  # scan tail for central dir filenames
ISO_PVD_OFFSET = 16 * 2048 + 1  # ECMA-119: "CD001" at sector 16, byte 1
OLE_CFBF = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


@dataclass(frozen=True)
class Match:
    kind: str
    confidence: float
    details: Optional[str] = None
    full: bool = True


def _startswith(buf: memoryview, sig: bytes, offset: int = 0) -> bool:
    if offset + len(sig) > len(buf):
        return False
    return buf[offset : offset + len(sig)] == sig


def _equals(buf: memoryview, start: int, sig: bytes) -> bool:
    end = start + len(sig)
    if end > len(buf):
        return False
    return buf[start:end] == sig


def _find_within(buf: memoryview, sig: bytes, limit: int) -> int:
    return bytes(buf[:limit]).find(sig)


def _rfind_within(buf: memoryview, sig: bytes, limit_from_end: int) -> int:
    tail = bytes(buf[-limit_from_end:]) if limit_from_end < len(buf) else bytes(buf)
    return tail.rfind(sig)


def _riff_form(buf: memoryview, form: bytes) -> bool:
    # b"RIFF" + 4 size bytes + form (WAVE/AVI /WEBP)
    return _startswith(buf, b"RIFF", 0) and _startswith(buf, form, 8)


def _u32_le(buf: memoryview, offset: int = 0) -> int:
    if offset + 4 > len(buf):
        return -1
    b0, b1, b2, b3 = buf[offset : offset + 4]
    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)


def _test_pe(buf: memoryview) -> bool:
    # DOS MZ + e_lfanew -> "PE\0\0"
    if not _startswith(buf, b"MZ", 0) or len(buf) < 0x40:
        return False
    peoff = _u32_le(buf, 0x3C)
    if peoff < 0 or peoff + 4 > len(buf):
        return False
    return _startswith(buf, b"PE\x00\x00", peoff)


def detect_file(path: str) -> Optional[Match]:
    try:
        size = pathlib.Path(path).stat().st_size
        if size == 0:
            return None
        with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            mv = memoryview(mm)

            head_len = min(HEAD_WINDOW, len(mv))
            head = mv[:head_len]

            # ===== 1) Executables/objects/containers (start-anchored) =====
            if _startswith(head, b"\x7fELF"):
                return Match("elf", 0.99, "ELF @0", True)

            # Mach-O (incl. fat)
            if head_len >= 4 and _u32_le(head, 0) in (
                0xFEEDFACE,
                0xFEEDFACF,
                0xCEFAEDFE,
                0xCFFAEDFE,
                0xCAFEBABE,
                0xBEBAFECA,
            ):
                return Match("macho", 0.95, "Mach-O/FAT @0", False)

            # PE/COFF (Windows EXE/DLL/SYS/PYD etc.)
            if _test_pe(head):
                return Match("pe", 0.99, "MZ + PE header", True)

            # WASM
            if _startswith(head, b"\x00asm"):
                return Match("wasm", 0.99, "WASM magic", True)

            # Java class
            if _startswith(head, b"\xca\xfe\xba\xbe"):
                return Match("java-class", 0.99, "CAFEBABE", True)

            # Erlang BEAM (FOR1 ... BEAM)
            if _startswith(head, b"FOR1") and _startswith(head, b"BEAM", 8):
                return Match("beam", 0.95, "FOR1/BEAM", True)

            # OLE Compound File (MSI, old Office docs, etc.)
            if _startswith(head, OLE_CFBF):
                return Match("ole-cfbf", 0.95, "D0 CF 11 E0 ...", False)

            # ===== 2) Archives / packages / disk images =====
            # ZIP via EOCD or Zip64 locator near end
            tail_scan = min(ZIP_TAIL_WINDOW, len(mv))
            if (
                _rfind_within(mv, b"PK\x05\x06", tail_scan) != -1
                or _rfind_within(mv, b"PK\x06\x06", tail_scan) != -1
            ):
                # Subtype hints by scanning tail for central directory filenames (no decompression)
                sub_tail = min(ZIP_SUBTYPE_TAIL, len(mv))
                tbytes = bytes(mv[-sub_tail:]) if sub_tail < len(mv) else bytes(mv)

                def has(name: bytes) -> bool:
                    return tbytes.find(name) != -1

                if has(b"AndroidManifest.xml"):
                    return Match("apk", 0.98, "zip + AndroidManifest.xml", True)
                if has(b"Payload/"):
                    return Match("ipa", 0.95, "zip + Payload/", True)
                if has(b"META-INF/MANIFEST.MF") and has(b"WEB-INF/"):
                    return Match("war", 0.95, "zip + WEB-INF/", True)
                if has(b"META-INF/application.xml"):
                    return Match("ear", 0.95, "zip + META-INF/application.xml", True)
                if has(b"META-INF/MANIFEST.MF"):
                    return Match("jar", 0.9, "zip + META-INF/MANIFEST.MF", False)
                if has(b"document.json") and has(b"meta.json"):
                    return Match("sketch", 0.9, "zip + Sketch JSONs", False)
                return Match("zip", 0.95, "EOCD near end", True)

            # 7z / gzip / xz / zstd / bzip2 / lzip / lz4
            if _startswith(head, b"\x37\x7a\xbc\xaf\x27\x1c"):
                return Match("7z", 0.99, "7z header", True)
            if _startswith(head, b"\x1f\x8b"):
                return Match("gzip", 0.99, "gzip header", True)
            if _startswith(head, b"\xfd7zXZ\x00"):
                return Match("xz", 0.99, "xz header", True)
            if _startswith(head, b"\x28\xb5\x2f\xfd"):
                return Match("zstd", 0.99, "zstd header", True)
            if _startswith(head, b"BZh"):
                return Match("bzip2", 0.99, "BZh", True)
            if _startswith(head, b"LZIP"):
                return Match("lzip", 0.99, "LZIP", True)
            if _startswith(head, b"\x04\x22\x4d\x18"):  # LZ4 Frame
                return Match("lz4", 0.99, "LZ4 frame", True)

            # RAR4/5 (allow SFX up to 1 MiB)
            head_scan = min(RAR_SFX_MAX, len(mv))
            if (
                _find_within(mv, b"Rar!\x1a\x07\x00", head_scan) != -1
                or _find_within(mv, b"Rar!\x1a\x07\x01\x00", head_scan) != -1
            ):
                return Match("rar", 0.95, "RAR signature within SFX window", True)

            # ar archive (used by .a static libs and .deb)
            if _startswith(head, b"!<arch>\n"):
                probe = bytes(mv[: min(8192, len(mv))])
                if b"debian-binary" in probe:
                    return Match("deb", 0.95, "ar + debian-binary", True)
                return Match("ar", 0.9, "Unix ar", False)

            # RPM
            if _startswith(head, b"\xed\xab\xee\xdb"):
                return Match("rpm", 0.99, "RPM magic", True)

            # CAB
            if _startswith(head, b"MSCF"):
                return Match("cab", 0.99, "MSCF", True)

            # ISO-9660: "CD001" at sector 16 (and usually again at sector 17)
            if (
                len(mv) > ISO_PVD_OFFSET + 4
                and mv[ISO_PVD_OFFSET : ISO_PVD_OFFSET + 5].tobytes() == b"CD001"
            ):
                return Match("iso9660", 0.98, "CD001 @ sector 16", True)

            # DMG (UDIF): 'koly' trailer 512 bytes from EOF (allow a small tail search)
            if len(mv) >= 512:
                # Exact trailer position:
                if mv[-512:-508].tobytes() == b"koly":
                    return Match("dmg", 0.98, "UDIF 'koly' trailer", True)
                # Fallback: search last few KiB for 'koly'
                if _rfind_within(mv, b"koly", min(4096, len(mv))) != -1:
                    return Match("dmg", 0.9, "UDIF trailer near end", False)

            # ===== 3) Images / design =====
            if _startswith(head, b"\x89PNG\r\n\x1a\n"):
                return Match("png", 0.99, "PNG", True)
            if _startswith(head, b"\xff\xd8\xff"):  # JPEG SOI
                # light sanity: common JFIF/EXIF tags near start
                if _find_within(mv, b"JFIF", 64) != -1 or _find_within(mv, b"Exif", 64) != -1:
                    return Match("jpeg", 0.95, "SOI + JFIF/EXIF", True)
                return Match("jpeg", 0.9, "SOI only", False)
            if _startswith(head, b"GIF87a") or _startswith(head, b"GIF89a"):
                return Match("gif", 0.99, "GIF", True)
            if _riff_form(head, b"WEBP"):
                return Match("webp", 0.99, "RIFF/WEBP", True)
            if _startswith(head, b"BM"):
                return Match("bmp", 0.9, "BMP", False)
            if _startswith(head, b"\x00\x00\x01\x00"):
                return Match("ico", 0.99, "ICO", True)
            # TIFF
            if _startswith(head, b"II*\x00") or _startswith(head, b"MM\x00*"):
                return Match("tiff", 0.99, "TIFF", True)
            # Photoshop
            if _startswith(head, b"8BPS"):
                return Match("psd", 0.99, "PSD", True)

            # ===== 4) Fonts =====
            # TrueType/OpenType: sfntVersion == 0x00010000 or 'OTTO'; TTC 'ttcf'; WOFF/WOFF2
            if head_len >= 4:
                tag = bytes(head[:4])
                if tag == b"\x00\x01\x00\x00" or tag == b"OTTO":
                    return Match("sfnt", 0.95, "TTF/OTF (sfnt)", False)
                if tag == b"ttcf":
                    return Match("ttc", 0.98, "TrueType Collection", True)
                if tag == b"wOFF":
                    return Match("woff", 0.98, "WOFF", True)
                if tag == b"wOF2":
                    return Match("woff2", 0.98, "WOFF2", True)

            # ===== 5) Databases / scientific data =====
            if _startswith(head, b"SQLite format 3\x00"):
                return Match("sqlite3", 0.99, "SQLite3", True)
            # NumPy .npy
            if _startswith(head, b"\x93NUMPY"):
                return Match("npy", 0.99, "NumPy NPY", True)
            # HDF5 signature may appear at 0,512,1024,2048,... (scan up to HDF5_SCAN_LIMIT)
            HDF5_SIG = b"\x89HDF\r\n\x1a\n"
            lim = min(HDF5_SCAN_LIMIT, len(mv))
            off = 0
            while off + 8 <= lim:
                if mv[off : off + 8].tobytes() == HDF5_SIG:
                    return Match("hdf5", 0.98, f"HDF5 sig @ {off}", True)
                off += 512
            # Parquet: PAR1 at start and end
            if _startswith(head, b"PAR1"):
                if _rfind_within(mv, b"PAR1", 16) != -1:
                    return Match("parquet", 0.99, "PAR1 head+tail", True)
                return Match("parquet", 0.9, "PAR1 head", False)
            # Arrow IPC / Feather v2: ARROW1 at head & tail
            if _startswith(head, b"ARROW1"):
                if _rfind_within(mv, b"ARROW1", 16) != -1:
                    return Match("arrow-ipc", 0.99, "ARROW1 head+tail", True)
                return Match("arrow-ipc", 0.9, "ARROW1 head", False)
            # .npz is just zip; covered above.

            # ===== 6) Documents =====
            if _startswith(head, b"%PDF-"):
                tw = min(PDF_TAIL_WINDOW, len(mv))
                if _rfind_within(mv, b"%%EOF", tw) != -1:
                    return Match("pdf", 0.99, "PDF header + EOF near end", True)
                return Match("pdf", 0.7, "PDF header only", False)

            # ===== 7) Audio / video containers =====
            # RIFF subtypes
            if _riff_form(head, b"WAVE"):
                return Match("wav", 0.99, "RIFF/WAVE", True)
            if _riff_form(head, b"AVI "):
                return Match("avi", 0.99, "RIFF/AVI", True)

            # MP4/MOV/M4A: 'ftyp' at offset 4
            if head_len >= 12 and _startswith(head, b"ftyp", 4):
                return Match("mp4-family", 0.98, "ISO BMFF (ftyp)", True)

            # Matroska/WebM: EBML header 1A 45 DF A3; look for docType strings near head
            if _startswith(head, b"\x1a\x45\xdf\xa3"):
                probe = bytes(mv[: min(4096, len(mv))])
                if b"webm" in probe:
                    return Match("webm", 0.98, "EBML + DocType=webm", True)
                if b"matroska" in probe:
                    return Match("mkv", 0.98, "EBML + DocType=matroska", True)
                return Match("matroska", 0.9, "EBML header", False)

            # ASF/WMV/WMA GUID
            if _startswith(head, bytes.fromhex("3026B2758E66CF11A6D900AA0062CE6C")):
                return Match("asf", 0.98, "ASF GUID", True)

            # FLV
            if _startswith(head, b"FLV"):
                return Match("flv", 0.99, "FLV", True)

            # Ogg container (Vorbis/Opus/Theora)
            if _startswith(head, b"OggS"):
                return Match("ogg", 0.9, "Ogg container", False)

            # MP3: ID3 or frame sync
            if _startswith(head, b"ID3"):
                return Match("mp3", 0.9, "ID3 tag", False)
            # quick frame sync check
            if head_len >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
                return Match("mp3", 0.7, "MPEG audio frame sync", False)

            # AAC ADTS: 12-bit sync 0xFFF with profile bits
            if head_len >= 2 and head[0] == 0xFF and (head[1] & 0xF6) in (0xF0, 0xF2, 0xF4):
                return Match("aac-adts", 0.7, "ADTS sync", False)

            # ===== 8) Fallbacks =====
            # tar (POSIX "ustar" at 257)
            if head_len >= 262 and _equals(head, 257, b"ustar"):
                return Match("tar", 0.95, "ustar field @257", False)

            # Unknown
            return None
    except (OSError, ValueError):
        return None


def detect_many(paths: Iterable[str]) -> Dict[str, Optional[Match]]:
    return {p: detect_file(p) for p in paths}
