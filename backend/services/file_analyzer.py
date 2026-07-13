"""
File Analysis Service
Real file parsing: binary, hex, strings extraction, file type detection
"""
import os
import re
import struct
import zipfile
import hashlib
from pathlib import Path
from typing import Optional


# ── File Type Detection ───────────────────────────────────────────────────────
FILE_SIGNATURES = {
    b"\x50\x4b\x03\x04": "APK/ZIP",
    b"\x4d\x5a":         "PE Executable (EXE/DLL)",
    b"\x7f\x45\x4c\x46": "ELF Binary (Linux/Android)",
    b"\xca\xfe\xba\xbe": "Java Class / Mach-O Fat",
    b"\xfe\xed\xfa\xce": "Mach-O 32-bit (macOS)",
    b"\xfe\xed\xfa\xcf": "Mach-O 64-bit (macOS)",
    b"\x89\x50\x4e\x47": "PNG Image",
    b"\xff\xd8\xff":     "JPEG Image",
    b"\x25\x50\x44\x46": "PDF Document",
    b"\x1f\x8b":         "GZIP Compressed",
    b"\x42\x5a\x68":     "BZIP2 Compressed",
    b"\xfd\x37\x7a\x58": "XZ Compressed",
    b"\x52\x61\x72\x21": "RAR Archive",
    b"\x00\x00\x00":     "Binary/Firmware",
}

KNOWN_EXTS = {
    ".apk":  "Android Package",
    ".exe":  "Windows Executable",
    ".dll":  "Windows DLL",
    ".so":   "Linux Shared Library",
    ".elf":  "ELF Binary",
    ".bin":  "Raw Binary/Firmware",
    ".hex":  "Intel HEX / ASCII Hex",
    ".fw":   "Firmware Image",
    ".img":  "Disk/Flash Image",
    ".pcap": "Network Capture",
    ".cap":  "Network Capture",
}


def detect_file_type(data: bytes, filename: str = "") -> str:
    # Check magic bytes
    for magic, ftype in FILE_SIGNATURES.items():
        if data[:len(magic)] == magic:
            return ftype
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext in KNOWN_EXTS:
        return KNOWN_EXTS[ext]
    # Check if text
    try:
        data[:512].decode("utf-8")
        return "Text/Script"
    except Exception:
        pass
    return "Unknown Binary"


# ── String Extraction ─────────────────────────────────────────────────────────
def extract_strings(data: bytes, min_len: int = 5, max_count: int = 300) -> list[str]:
    """Extract printable ASCII strings from binary data."""
    pattern = rb"[ -~]{" + str(min_len).encode() + rb",}"
    found = re.findall(pattern, data)
    strings = []
    seen = set()
    for s in found:
        try:
            decoded = s.decode("ascii", errors="ignore").strip()
            if decoded and decoded not in seen:
                seen.add(decoded)
                strings.append(decoded)
                if len(strings) >= max_count:
                    break
        except Exception:
            continue
    return strings


# ── Hex Dump ─────────────────────────────────────────────────────────────────
def hex_dump(data: bytes, max_bytes: int = 512) -> str:
    """Create a formatted hex dump of binary data."""
    chunk = data[:max_bytes]
    lines = []
    for i in range(0, len(chunk), 16):
        row = chunk[i:i+16]
        hex_part  = " ".join(f"{b:02x}" for b in row).ljust(48)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{i:08x}  {hex_part}  |{ascii_part}|")
    if len(data) > max_bytes:
        lines.append(f"... ({len(data) - max_bytes} more bytes)")
    return "\n".join(lines)


# ── PE (EXE/DLL) Analysis ─────────────────────────────────────────────────────
def analyze_pe(data: bytes) -> dict:
    info = {}
    try:
        # DOS header check
        if data[:2] != b"MZ":
            return info
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
            return info
        machine = struct.unpack_from("<H", data, pe_offset+4)[0]
        info["architecture"] = {0x014c: "x86 (32-bit)", 0x8664: "x64 (64-bit)", 0x01c0: "ARM", 0xaa64: "ARM64"}.get(machine, f"Unknown ({hex(machine)})")
        num_sections = struct.unpack_from("<H", data, pe_offset+6)[0]
        info["sections"] = num_sections
        timestamp = struct.unpack_from("<I", data, pe_offset+8)[0]
        info["compile_timestamp"] = timestamp
        characteristics = struct.unpack_from("<H", data, pe_offset+22)[0]
        flags = []
        if characteristics & 0x0002: flags.append("Executable")
        if characteristics & 0x2000: flags.append("DLL")
        if characteristics & 0x0020: flags.append("Large address aware")
        info["characteristics"] = flags
    except Exception:
        pass
    return info


# ── ELF Analysis ─────────────────────────────────────────────────────────────
def analyze_elf(data: bytes) -> dict:
    info = {}
    try:
        if data[:4] != b"\x7fELF":
            return info
        info["class"]      = "64-bit" if data[4] == 2 else "32-bit"
        info["endianness"] = "Little-endian" if data[5] == 1 else "Big-endian"
        etype = struct.unpack_from("<H", data, 16)[0]
        info["type"] = {1: "Relocatable", 2: "Executable", 3: "Shared Library", 4: "Core"}.get(etype, f"Unknown ({etype})")
        machine = struct.unpack_from("<H", data, 18)[0]
        info["machine"] = {0x28: "ARM", 0xB7: "AArch64", 0x3E: "x86-64", 0x03: "x86"}.get(machine, f"Unknown ({hex(machine)})")
    except Exception:
        pass
    return info


# ── APK Analysis ─────────────────────────────────────────────────────────────
def analyze_apk(data: bytes, filename: str) -> dict:
    info = {"type": "Android APK", "files": [], "permissions": [], "components": []}
    try:
        import io
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            info["total_files"] = len(names)
            # Categorize files
            for name in names[:200]:
                if name.endswith(".dex"):
                    info["components"].append(f"DEX bytecode: {name}")
                elif name.startswith("lib/"):
                    info["components"].append(f"Native library: {name}")
                elif name.endswith(".xml"):
                    info["files"].append(name)
                elif name.startswith("assets/"):
                    info["files"].append(name)
            # Try to read manifest
            if "AndroidManifest.xml" in names:
                info["has_manifest"] = True
                raw = zf.read("AndroidManifest.xml")
                # Extract readable strings from binary manifest
                perm_strings = re.findall(rb"android\.permission\.[A-Z_]+", raw)
                info["permissions"] = list({p.decode("utf-8", errors="ignore") for p in perm_strings})[:30]
    except Exception as e:
        info["error"] = str(e)
    return info


# ── Intel HEX Parser ──────────────────────────────────────────────────────────
def analyze_intel_hex(text: str) -> dict:
    info = {"format": "Intel HEX", "records": 0, "data_records": 0, "start_address": None, "address_range": []}
    addresses = []
    try:
        for line in text.strip().splitlines():
            line = line.strip()
            if not line.startswith(":"):
                continue
            info["records"] += 1
            byte_count  = int(line[1:3], 16)
            address     = int(line[3:7], 16)
            record_type = int(line[7:9], 16)
            if record_type == 0:   # Data
                info["data_records"] += 1
                addresses.append(address)
            elif record_type == 1:  # EOF
                info["has_eof"] = True
            elif record_type == 5:  # Start linear address
                info["start_address"] = hex(int(line[9:17], 16))
        if addresses:
            info["address_range"] = [hex(min(addresses)), hex(max(addresses))]
    except Exception as e:
        info["error"] = str(e)
    return info


# ── PCAP Basic Info ───────────────────────────────────────────────────────────
def analyze_pcap(data: bytes) -> dict:
    info = {"format": "PCAP"}
    try:
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic == 0xa1b2c3d4:
            info["byte_order"] = "Little-endian"
        elif magic == 0xd4c3b2a1:
            info["byte_order"] = "Big-endian"
        version_major = struct.unpack_from("<H", data, 4)[0]
        version_minor = struct.unpack_from("<H", data, 6)[0]
        info["version"]    = f"{version_major}.{version_minor}"
        link_type = struct.unpack_from("<I", data, 20)[0]
        info["link_type"]  = {1: "Ethernet", 105: "IEEE 802.11 WiFi", 228: "Raw IPv4"}.get(link_type, f"Type {link_type}")
        info["file_size"]  = f"{len(data)/1024:.1f} KB"
    except Exception:
        pass
    return info


# ── Master Analyzer ───────────────────────────────────────────────────────────
async def analyze_file(file_path: str, filename: str, target_type: str) -> dict:
    """
    Main entry point. Reads file, detects type, runs appropriate parsers.
    Returns a structured dict to be passed to AI prompt.
    """
    result = {
        "filename":   filename,
        "file_type":  "Unknown",
        "file_size":  0,
        "sha256":     "",
        "md5":        "",
        "hex_dump":   "",
        "strings":    [],
        "metadata":   {},
        "raw_text":   "",
        "is_text":    False,
    }

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        result["file_size"]  = len(data)
        result["sha256"]     = hashlib.sha256(data).hexdigest()
        result["md5"]        = hashlib.md5(data).hexdigest()
        result["file_type"]  = detect_file_type(data, filename)
        result["hex_dump"]   = hex_dump(data, max_bytes=256)
        result["strings"]    = extract_strings(data, max_count=150)

        ext = Path(filename).suffix.lower()

        # Text file
        try:
            text = data.decode("utf-8")
            result["is_text"]   = True
            result["raw_text"]  = text[:8000]
            if ext in (".hex",) or text.strip().startswith(":"):
                result["metadata"] = analyze_intel_hex(text)
        except UnicodeDecodeError:
            pass  # Binary

        # PE binary
        if data[:2] == b"MZ":
            result["metadata"] = analyze_pe(data)

        # ELF binary
        elif data[:4] == b"\x7fELF":
            result["metadata"] = analyze_elf(data)

        # APK (ZIP)
        elif data[:4] == b"\x50\x4b\x03\x04" and ext == ".apk":
            result["metadata"] = analyze_apk(data, filename)

        # PCAP
        elif ext in (".pcap", ".cap"):
            result["metadata"] = analyze_pcap(data)

    except Exception as e:
        result["error"] = str(e)

    return result
