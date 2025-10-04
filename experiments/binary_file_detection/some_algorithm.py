from __future__ import annotations

import io
import os
from typing import Tuple

# Tunables (picked to bias toward "catch all binaries" while sparing normal UTF text)
HEAD_SAMPLE_SIZE = 4096
TAIL_SAMPLE_SIZE = 4096
ASCII_PRINTABLE_THRESHOLD = 0.95  # raise to be stricter, lower to be more permissive
UTF16_ZERO_LANE_THRESHOLD = 0.30  # share of zeros in one lane to consider UTF-16-like
UTF32_ZERO_LANE_STRICT = 0.80  # share of zeros in the "zero lanes" to consider UTF-32-like

# Precompute an "allowed ASCII-ish" table for fast counting.
_ALLOWED_ASCII = [False] * 256
for b in range(0x20, 0x7F):  # Printable ASCII
    _ALLOWED_ASCII[b] = True
for b in (9, 10, 11, 12, 13, 27, 8):  # \t \n \v \f \r ESC \b
    _ALLOWED_ASCII[b] = True
_ALLOWED_ASCII = tuple(_ALLOWED_ASCII)

# Optional: a looser table that treats 0xA0–0xFF as printable (legacy 8-bit text)
_ALLOWED_ASCII_OR_8BIT = list(_ALLOWED_ASCII)
for b in range(0xA0, 256):
    _ALLOWED_ASCII_OR_8BIT[b] = True
_ALLOWED_ASCII_OR_8BIT = tuple(_ALLOWED_ASCII_OR_8BIT)

# Known BOMs
BOM_UTF8 = b"\xef\xbb\xbf"
BOM_UTF16LE = b"\xff\xfe"
BOM_UTF16BE = b"\xfe\xff"
BOM_UTF32LE = b"\xff\xfe\x00\x00"
BOM_UTF32BE = b"\x00\x00\xfe\xff"


def _has_bom(sample: bytes) -> bool:
    return (
        sample.startswith(BOM_UTF8)
        or sample.startswith(BOM_UTF16LE)
        or sample.startswith(BOM_UTF16BE)
        or sample.startswith(BOM_UTF32LE)
        or sample.startswith(BOM_UTF32BE)
    )


def _valid_utf8(sample: bytes) -> bool:
    # CPython’s decoder is C-optimized and very fast on small buffers.
    try:
        sample.decode("utf-8", "strict")
        return True
    except UnicodeDecodeError:
        return False


def _ascii_ratio(sample: bytes, accept_legacy_8bit: bool) -> float:
    table = _ALLOWED_ASCII_OR_8BIT if accept_legacy_8bit else _ALLOWED_ASCII
    allowed = sum(1 for b in sample if table[b])
    return allowed / max(1, len(sample))


def _looks_like_utf16(sample: bytes) -> bool:
    if len(sample) < 4:
        return False
    even = sample[0::2]
    odd = sample[1::2]
    # Pick the lane with many zeros and require the other lane be ASCII-ish.
    even_zero = even.count(0) / max(1, len(even))
    odd_zero = odd.count(0) / max(1, len(odd))
    if even_zero > UTF16_ZERO_LANE_THRESHOLD and _ascii_ratio(odd, False) > 0.80:
        return True
    return bool(odd_zero > UTF16_ZERO_LANE_THRESHOLD and _ascii_ratio(even, False) > 0.8)


def _looks_like_utf32(sample: bytes) -> bool:
    if len(sample) < 8:
        return False
    lanes = [sample[i::4] for i in range(4)]
    zero_ratios = [lane.count(0) / max(1, len(lane)) for lane in lanes]
    # One lane should be the “text lane” (few zeros), three lanes mostly zeros.
    text_lane = min(range(4), key=lambda i: zero_ratios[i])
    if zero_ratios[text_lane] < 0.10 and all(
        (i == text_lane) or (zr > UTF32_ZERO_LANE_STRICT) for i, zr in enumerate(zero_ratios)
    ):
        return _ascii_ratio(lanes[text_lane], False) > 0.80
    return False


def _chunk_is_text(sample: bytes, *, accept_legacy_8bit: bool) -> bool:
    if not sample:
        return True  # empty files are treated as text
    if _has_bom(sample):
        return True
    # Fast path: valid UTF-8
    if _valid_utf8(sample):
        return True
    # Guard against misclassifying UTF-16/32 as binary due to NULs.
    if _looks_like_utf16(sample) or _looks_like_utf32(sample):
        return True
    # Hard fail: unexplained NUL present
    if b"\x00" in sample:
        return False
    # ASCII-ish ratio heuristic
    return _ascii_ratio(sample, accept_legacy_8bit) >= ASCII_PRINTABLE_THRESHOLD


def _read_head_and_tail(f: io.BufferedReader, tail_size: int) -> Tuple[bytes, bytes]:
    head = f.read(HEAD_SAMPLE_SIZE)
    try:
        f.raw.raw._parent.tell()  # not portable; avoid
    except Exception:
        pass
    # Portable way: use file size and seek
    try:
        size = os.fstat(f.fileno()).st_size
    except Exception:
        size = None
    tail = b""
    if size is not None and size > HEAD_SAMPLE_SIZE + tail_size:
        try:
            f.seek(max(0, size - tail_size))
            tail = f.read(tail_size)
        finally:
            pass
    return head, tail


def is_binary_file(
    path: str,
    *,
    accept_legacy_8bit_text: bool = False,
    read_tail: bool = True,
) -> bool:
    """
    Robust, format-agnostic binary detector.
    - High recall for 'binary' by design.
    - UTF-8/16/32 text is preserved as text.
    - Optionally recognize legacy 8-bit text encodings.
    """
    try:
        with open(path, "rb", buffering=0) as raw:
            buf = io.BufferedReader(raw, buffer_size=max(HEAD_SAMPLE_SIZE, TAIL_SAMPLE_SIZE))
            head, tail = _read_head_and_tail(buf, TAIL_SAMPLE_SIZE if read_tail else 0)

            head_text = _chunk_is_text(head, accept_legacy_8bit=accept_legacy_8bit_text)
            if not head_text:
                return True  # strong binary signal early

            if read_tail and tail:
                tail_text = _chunk_is_text(tail, accept_legacy_8bit=accept_legacy_8bit_text)
                if not tail_text:
                    return True

            # Both chunks look texty → call it text.
            return False
    except (IsADirectoryError, PermissionError, FileNotFoundError):
        # Do not classify; let your traversal layer handle these.
        return False
