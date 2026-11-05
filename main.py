"""
MPSC Katta — single-topic local workspace
Topic: HIS-001 | प्रागैतिहासिक काळ

This script does not call an AI API. Use the prompt in prompts/HIS-001_prompt.md
in ChatGPT, save the reviewed draft to output/HIS-001/detailed_notes.md,
then run: python main.py --check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
TOPIC_ID = "HIS-001"
TOPIC_DIR = PROJECT_ROOT / "output" / TOPIC_ID
NOTES_FILE = TOPIC_DIR / "detailed_notes.md"
SOURCE_LOG = PROJECT_ROOT / "sources" / "HIS-001_reference_log.md"
PROMPT_FILE = PROJECT_ROOT / "prompts" / "HIS-001_prompt.md"

TARGET_MIN_WORDS = 2_000
TARGET_MAX_WORDS = 2_600
REVIEW_MIN_WORDS = 1_800

REQUIRED_TERMS = (
    "पुरापाषाण",
    "मध्यपाषाण",
    "नवपाषाण",
    "महाराष्ट्र",
)


def initialize_workspace() -> None:
    """Create expected local folders without overwriting any existing work."""
    folders = (
        PROJECT_ROOT / "prompts",
        PROJECT_ROOT / "sources",
        TOPIC_DIR,
    )
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    print(f"Project: {PROJECT_ROOT}")
    print(f"Topic: {TOPIC_ID} — प्रागैतिहासिक काळ")
    print(f"Prompt: {PROMPT_FILE}")
    print(f"Source log: {SOURCE_LOG}")
    print(f"Notes file: {NOTES_FILE}")

    if not NOTES_FILE.exists():
        NOTES_FILE.write_text(
            "# प्रागैतिहासिक काळ\n\n"
            "- Topic ID: HIS-001\n"
            "- स्थिती: Draft — तथ्य-पडताळणी बाकी\n\n"
            "## नोट्स\n\n"
            "ChatGPT मधून तयार केलेला आणि संपादित केलेला मजकूर येथे जोडा.\n",
            encoding="utf-8",
        )
        print("Created a starter notes file.")
    else:
        print("Existing notes file found; it was not changed.")

    print("\nNext:")
    print("1. Open prompts/HIS-001_prompt.md in PyCharm.")
    print("2. Use that prompt in ChatGPT.")
    print("3. Save the Marathi notes in output/HIS-001/detailed_notes.md.")
    print("4. Run: python main.py --check")


def count_words(text: str) -> int:
    """Count whitespace-separated words."""
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    cleaned = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", cleaned)
    return len(re.findall(r"\S+", cleaned))


def quality_check() -> int:
    """Perform basic structure checks; this does not verify historical facts."""
    if not NOTES_FILE.exists():
        print(f"ERROR: Notes file not found: {NOTES_FILE}")
        print("Run python main.py first, then add your notes.")
        return 1

    notes = NOTES_FILE.read_text(encoding="utf-8").strip()
    if not notes:
        print("ERROR: Notes file is empty.")
        return 1

    word_count = count_words(notes)
    headings = re.findall(r"(?m)^#{1,3}\s+.+$", notes)
    print(f"Topic: {TOPIC_ID} — प्रागैतिहासिक काळ")
    print(f"Approximate word count: {word_count}")
    print(f"Markdown headings found: {len(headings)}")

    issues: list[str] = []

    if word_count < REVIEW_MIN_WORDS:
        issues.append(
            f"Notes are shorter than the initial 25-minute target "
            f"({REVIEW_MIN_WORDS}+ words suggested)."
        )
    elif word_count < TARGET_MIN_WORDS:
        issues.append(
            f"Notes are below the preferred range "
            f"({TARGET_MIN_WORDS}–{TARGET_MAX_WORDS} words). Review depth."
        )
    elif word_count > TARGET_MAX_WORDS:
        issues.append(
            f"Notes exceed the preferred range "
            f"({TARGET_MIN_WORDS}–{TARGET_MAX_WORDS} words). "
            "Check for repetition and unnecessary detail."
        )
    else:
        print("Length check: within the preferred range.")

    for term in REQUIRED_TERMS:
        if term not in notes:
            issues.append(f"Topic coverage check: '{term}' was not found.")

    source_markers = ("स्रोत-पडताळणी", "स्रोत पडताळणी", "संदर्भ")
    if not any(marker in notes for marker in source_markers):
        issues.append("Add a source-verification section.")

    if len(headings) < 8:
        issues.append(
            "Use clear section headings so students can navigate the notes."
        )

    if issues:
        print("\nReview suggestions:")
        for item in issues:
            print(f"- {item}")
    else:
        print("Basic structure checks passed.")

    print(
        "\nIMPORTANT: This script only checks file presence, approximate "
        "length and a few structure markers. It cannot verify dates, "
        "archaeological claims, source quality, copyright or answer accuracy."
    )
    print("Human source-check and approval are required before publication.")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local workspace helper for MPSC Katta HIS-001."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check the HIS-001 notes file's approximate length and structure.",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Create expected local folders and starter notes file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.check:
        return quality_check()

    # Default action is safe initialization; it never overwrites notes.
    initialize_workspace()
    return 0


if __name__ == "__main__":
    sys.exit(main())
