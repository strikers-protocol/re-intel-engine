"""
AI Analysis Service — Groq API (Free)
Text model  : openai/gpt-oss-120b
Image mode  : extract strings + hex from image file, describe via text prompt
Updated     : June 2026
"""
import os, time, re, base64, struct
from pathlib import Path
from groq import Groq

TARGETS = {
    "software":  "Software / Application (APK, EXE, DLL, SO)",
    "firmware":  "Firmware / IoT Device",
    "hardware":  "Hardware Component / Device",
    "code":      "Source Code / Script",
    "network":   "Network Traffic / Protocol",
}
MODES = {
    "full":       "Full Deep Analysis",
    "components": "Components & Technologies Used",
    "logic":      "Logic & Execution Flow",
    "security":   "Security Audit & Vulnerabilities",
    "bugs":       "Bug Detection & Root Cause",
}
LANG_INSTR = {
    "hinglish": "Write in Hinglish — mix Hindi and English naturally. Use English for all technical terms, Hindi for explanations.",
    "english":  "Write in clear, precise technical English.",
    "hindi":    "Write in Hindi (Devanagari). Use English technical terms only where unavoidable.",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MODEL      = "openai/gpt-oss-120b"


def is_image_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTS


def extract_strings_from_bytes(data: bytes, min_len=4, max_count=200) -> list:
    import re as _re
    found = _re.findall(rb"[ -~]{" + str(min_len).encode() + rb",}", data)
    seen, result = set(), []
    for s in found:
        try:
            d = s.decode("ascii", errors="ignore").strip()
            if d and d not in seen:
                seen.add(d); result.append(d)
                if len(result) >= max_count: break
        except Exception: pass
    return result


def build_image_text_prompt(target_type, analysis_mode, language, user_text, filename, strings, filesize):
    """
    Since gpt-oss-120b does not support image_url arrays,
    we pass whatever we can extract as text + ask user to describe what they see.
    """
    t_label = TARGETS.get(target_type, target_type)
    m_label = MODES.get(analysis_mode, analysis_mode)
    lang    = LANG_INSTR.get(language, LANG_INSTR["hinglish"])
    extra   = f"\nUser description of image: {user_text}" if user_text.strip() else ""

    strings_block = "\n".join(strings[:80]) if strings else "No readable strings found"

    return f"""You are an elite hardware reverse engineer and IoT security researcher with 20+ years of experience.

{lang}

TASK: Perform a "{m_label}" on a hardware/PCB image file.

IMAGE FILE: {filename} ({filesize:,} bytes)
EXTRACTED READABLE STRINGS FROM FILE:
{strings_block}
{extra}

Based on the filename, file metadata, extracted strings, and any user description provided above, perform your best reverse engineering analysis. If the user described a hardware device (like NodeMCU, ESP8266, Arduino etc.), analyze that specific hardware in detail.

Respond in EXACTLY this markdown structure:

## OVERVIEW
What is this device/hardware? What is its purpose? Who makes it? What is it used for?

## COMPONENTS IDENTIFIED
List EVERY component, chip, module, connector, or part:
**[Component Name]** (Category: MCU/WiFi/Power/Interface/Sensor/Passive)
Purpose: what it does on this board.
Details: markings, model numbers, specifications.

## LOGIC & EXECUTION FLOW
How does this hardware work? Step-by-step:
1. Power path — how it receives and regulates power
2. Main processor — what it runs, clock speed, memory
3. Communication — protocols supported (WiFi/BT/UART/SPI/I2C etc.)
4. I/O — pins/ports available and what they do
5. Programming — how you flash/program this device

## ISSUES & VULNERABILITIES
**[Issue Name]** | Severity: Critical / High / Medium / Low / Info
- **What**: description
- **Where**: location on board
- **Impact**: security/reliability consequence
- **Fix**: recommendation

## DESIGN DECISIONS & ARCHITECTURE
Why was it designed this way? Tradeoffs? What does the layout reveal?

## INTELLIGENCE SUMMARY
| Field | Value |
|---|---|
| Device Type | (what it is) |
| Main Chip | (primary MCU/SoC) |
| Connectivity | (WiFi/BT/etc) |
| Operating Voltage | (3.3V/5V/etc) |
| Programming Interface | (USB/UART/JTAG) |
| Complexity | Low / Medium / High / Expert |
| Risk Level | None / Low / Medium / High / Critical |
| Primary Use Case | one line |
| Confidence | X% |"""


def build_text_prompt(target_type, analysis_mode, language, user_text, file_info=None):
    t_label = TARGETS.get(target_type, target_type)
    m_label = MODES.get(analysis_mode, analysis_mode)
    lang    = LANG_INSTR.get(language, LANG_INSTR["hinglish"])

    file_block = ""
    if file_info:
        file_block = f"""
FILE METADATA:
- Filename : {file_info.get('filename','N/A')}
- Type     : {file_info.get('file_type','N/A')}
- Size     : {file_info.get('file_size',0):,} bytes
- SHA256   : {file_info.get('sha256','N/A')}
- MD5      : {file_info.get('md5','N/A')}
PARSED METADATA: {file_info.get('metadata',{})}
HEX DUMP (first 256 bytes):
{file_info.get('hex_dump','N/A')}
EXTRACTED STRINGS (first 80):
{chr(10).join(file_info.get('strings',[])[:80])}
RAW TEXT:
{file_info.get('raw_text','')[:4000]}
"""
    user_block = f"\nUSER INPUT:\n{user_text[:3000]}" if user_text.strip() else ""

    return f"""You are an elite reverse engineer and security researcher with 20+ years of experience.

{lang}

TASK: Perform a "{m_label}" on the following {t_label}.
{file_block}{user_block}

Respond in EXACTLY this markdown structure:

## OVERVIEW
What is this? What does it do? What is its purpose?

## COMPONENTS IDENTIFIED
**[Component Name]** (Category: Library/Protocol/Chip/Algorithm/Framework)
Purpose: role it plays.
Details: version, variant, config if detectable.

## LOGIC & EXECUTION FLOW
Numbered walkthrough. Reference actual data from input. Explain the "why".

## ISSUES & VULNERABILITIES
**[Issue Name]** | Severity: Critical / High / Medium / Low / Info
- **What**: description
- **Where**: exact location
- **Impact**: consequence
- **Fix**: recommendation

If none found: "No significant issues detected."

## DESIGN DECISIONS & ARCHITECTURE
Why built this way? What tradeoffs? What does it reveal?

## INTELLIGENCE SUMMARY
| Field | Value |
|---|---|
| Target Type | {t_label} |
| Analysis Mode | {m_label} |
| Complexity | Low / Medium / High / Expert |
| Risk Level | None / Low / Medium / High / Critical |
| Primary Purpose | one line |
| Tech Stack | comma list |
| Confidence | X% |

No preamble. No closing remarks."""


def extract_summary_fields(result_md):
    fields = {"risk_level": "Unknown", "complexity": "Unknown", "confidence": 0.0}
    try:
        for line in result_md.splitlines():
            if "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    key, val = parts[0].lower(), parts[1]
                    if "risk" in key:
                        for lvl in ["Critical","High","Medium","Low","None"]:
                            if lvl.lower() in val.lower():
                                fields["risk_level"] = lvl; break
                    elif "complexity" in key:
                        for lvl in ["Expert","High","Medium","Low"]:
                            if lvl.lower() in val.lower():
                                fields["complexity"] = lvl; break
                    elif "confidence" in key:
                        nums = re.findall(r"\d+", val)
                        if nums: fields["confidence"] = float(nums[0])
    except Exception:
        pass
    return fields


async def run_analysis(target_type, analysis_mode, language, user_text, file_info=None):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return {
            "success": False, "error": "GROQ_API_KEY not set in .env",
            "result_md": "## ERROR\n\nGROQ_API_KEY missing in .env file.",
            "tokens_used": 0, "duration_ms": 0,
            "risk_level": "Unknown", "complexity": "Unknown", "confidence": 0.0,
        }

    client   = Groq(api_key=api_key)
    t0       = time.time()
    filename = file_info.get("filename", "") if file_info else ""

    try:
        # ── IMAGE FILE — text-based analysis ─────────────────────────────────
        if file_info and is_image_file(filename):
            file_path = file_info.get("file_path_original", "")
            filesize  = file_info.get("file_size", 0)
            strings   = []
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                strings = extract_strings_from_bytes(data)
            except Exception:
                pass

            prompt = build_image_text_prompt(
                target_type, analysis_mode, language,
                user_text, filename, strings, filesize
            )

        # ── TEXT / BINARY ─────────────────────────────────────────────────────
        else:
            prompt = build_text_prompt(target_type, analysis_mode, language, user_text, file_info)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.2,
        )

        result_md   = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        duration_ms = int((time.time() - t0) * 1000)
        summary     = extract_summary_fields(result_md)
        return {
            "success": True, "result_md": result_md,
            "tokens_used": tokens_used, "duration_ms": duration_ms,
            **summary,
        }

    except Exception as e:
        return {
            "success": False, "error": str(e),
            "result_md": f"## ERROR\n\nAnalysis failed: {str(e)}",
            "tokens_used": 0, "duration_ms": int((time.time() - t0) * 1000),
            "risk_level": "Unknown", "complexity": "Unknown", "confidence": 0.0,
        }
