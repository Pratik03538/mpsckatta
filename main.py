"""
MPSC Katta — AI Topic Pack Generator
One topic in -> Marathi learning pack out.

Uses Gemini Developer API (Google AI Studio), not ChatGPT Go.
Does NOT invent PYQs: extraction is attempted only from PDFs supplied by the user.
All generated material remains DRAFT until human/source verification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


ROOT = Path(__file__).resolve().parent
SOURCES_ROOT = ROOT / "sources"
OUTPUT_ROOT = ROOT / "output"

load_dotenv(ROOT / ".env")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
MAX_SOURCE_CHARS = 55_000
NOTES_MIN_WORDS = 1_800
NOTES_TARGET_MIN = 2_000
NOTES_TARGET_MAX = 2_800


def safe_folder_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    cleaned = cleaned.strip("-_")
    if not cleaned:
        raise ValueError("Topic ID must contain letters or numbers.")
    return cleaned[:50]


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace").strip()


def collect_sources(topic_id: str) -> tuple[str, list[dict[str, Any]]]:
    """
    Collect local TXT/MD/PDF sources. PDF extraction is not OCR.
    Put topic-specific references in sources/TOPIC-ID/.
    """
    candidates: list[Path] = []
    topic_sources_dir = SOURCES_ROOT / topic_id
    if topic_sources_dir.exists():
        for path in topic_sources_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name.lower() == "readme.md" or path.name.lower().endswith("reference_log.md"):
                continue
            if path.suffix.lower() in {".txt", ".md", ".pdf"}:
                if path not in candidates:
                    candidates.append(path)

    blocks: list[str] = []
    metadata: list[dict[str, Any]] = []
    remaining = MAX_SOURCE_CHARS

    for path in sorted(candidates):
        if remaining <= 0:
            break

        if path.suffix.lower() in {".txt", ".md"}:
            body = read_text_file(path)
            if not body:
                continue
            body = body[:remaining]
            blocks.append(f"\n\n===== SOURCE: {path.relative_to(ROOT)} =====\n{body}")
            metadata.append({
                "file": str(path.relative_to(ROOT)),
                "type": "text",
                "characters_included": len(body),
            })
            remaining -= len(body)

        elif path.suffix.lower() == ".pdf":
            if PdfReader is None:
                metadata.append({
                    "file": str(path.relative_to(ROOT)),
                    "type": "pdf",
                    "status": "pypdf missing; run pip install -r requirements.txt",
                })
                continue

            try:
                reader = PdfReader(str(path))
                pdf_parts: list[str] = []
                for page_number, page in enumerate(reader.pages, start=1):
                    if remaining <= 0:
                        break
                    page_text = (page.extract_text() or "").strip()
                    if not page_text:
                        continue
                    page_block = (
                        f"\n[PDF SOURCE: {path.name} | PAGE: {page_number}]\n"
                        f"{page_text}"
                    )
                    page_block = page_block[:remaining]
                    pdf_parts.append(page_block)
                    remaining -= len(page_block)

                combined = "\n".join(pdf_parts)
                if combined:
                    blocks.append(combined)
                    metadata.append({
                        "file": str(path.relative_to(ROOT)),
                        "type": "pdf",
                        "pages_with_extractable_text": len(pdf_parts),
                        "note": "Page labels are provided for human checking; scanned pages may not extract.",
                    })
                else:
                    metadata.append({
                        "file": str(path.relative_to(ROOT)),
                        "type": "pdf",
                        "status": "No selectable text extracted; scanned PDF needs OCR/manual checking.",
                    })
            except Exception as exc:
                metadata.append({
                    "file": str(path.relative_to(ROOT)),
                    "type": "pdf",
                    "status": f"Could not read PDF: {exc}",
                })

    return "\n".join(blocks), metadata


def build_client() -> genai.Client:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. Copy .env.example to .env and add "
            "your Google AI Studio API key. Never commit .env to GitHub."
        )
    return genai.Client(api_key=api_key)


def get_grounding_metadata(response: Any) -> Any:
    try:
        candidate = response.candidates[0]
        metadata = getattr(candidate, "grounding_metadata", None)
        if metadata is None:
            return None
        if hasattr(metadata, "model_dump"):
            return metadata.model_dump(mode="json")
        return str(metadata)
    except (AttributeError, IndexError, TypeError):
        return None


def generate_text(
    client: genai.Client,
    model: str,
    prompt: str,
    max_output_tokens: int,
    use_web_search: bool,
    json_mode: bool = False,
) -> tuple[str, Any]:
    config: dict[str, Any] = {
        "temperature": 0.35,
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        config["response_mime_type"] = "application/json"
    if use_web_search:
        config["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(
            "The model returned no text. Check API quota, model access and safety feedback."
        )
    return text, get_grounding_metadata(response)


def json_from_response(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    fence = chr(96) * 3
    if cleaned.startswith(fence):
        cleaned = cleaned[len(fence):].strip()
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:].strip()
        if cleaned.endswith(fence):
            cleaned = cleaned[:-len(fence)].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI response did not contain a JSON object.")
    payload = json.loads(cleaned[start:end + 1])
    if not isinstance(payload, dict):
        raise ValueError("AI response JSON must be an object.")
    return payload


def word_count(text: str) -> int:
    fence = re.escape(chr(96) * 3)
    without_code = re.sub(
        r"\n" + fence + r".*?\n.*?\n" + fence + r"\n",
        " ",
        text,
        flags=re.DOTALL,
    )
    return len(re.findall(r"\S+", without_code))


def notes_prompt(
    subject: str,
    topic_id: str,
    topic: str,
    source_text: str,
    web_search: bool,
) -> str:
    source_instructions = (
        "दिलेल्या स्थानिक स्रोतांना प्राधान्य द्या. प्रत्येक महत्त्वाच्या "
        "तथ्याजवळ [स्रोत: फाइलचे नाव, पृष्ठ/विभाग] अशी नोंद द्या. "
        "स्रोतामध्ये नसलेला दावा त्याच स्रोताने सिद्ध झाला असे दाखवू नका."
        if source_text
        else
        "स्थानिक संदर्भ साहित्य दिलेले नाही. म्हणून हे संशोधनाधारित प्रारूप "
        "म्हणून तयार करा; स्वतःहून पुस्तक, लेखक, पृष्ठ क्रमांक किंवा URL "
        "बनवू नका. खात्री नसलेले/वादग्रस्त दावे स्पष्टपणे चिन्हांकित करा. "
        "शेवटी स्रोत-पडताळणी आवश्यक असलेल्या दाव्यांची सूची द्या."
    )
    web_instructions = (
        "Google Search grounding उपलब्ध आहे. अधिकृत/विश्वसनीय शैक्षणिक व "
        "सरकारी स्रोतांना प्राधान्य द्या. स्रोतांचा मजकूर बनवू नका."
        if web_search else
        "Web search grounding वापरलेले नाही. अद्ययावत किंवा संदिग्ध तथ्यांना "
        "पडताळणी आवश्यक म्हणून चिन्हांकित करा."
    )

    return f"""
तुम्ही महाराष्ट्रातील MPSC विद्यार्थ्यांसाठी शिकवणारे अनुभवी इतिहास शिक्षक,
मराठी शैक्षणिक लेखक आणि तथ्य-पडताळणी करणारे संपादक आहात.

विषय: {subject}
Topic ID: {topic_id}
Topic Name: {topic}

उद्दिष्ट:
विद्यार्थ्याला विषय समजून घ्यायचा आहे; केवळ पाठांतर नको.
'काय, का, कसे, पुरावा काय, परिणाम काय' हे संबंध समजावून सांगा.

भाषा व शैली:
- सोपी, नैसर्गिक, शुद्ध मराठी; देवनागरी लिपी.
- लहान परिच्छेद, आकर्षक उपशीर्षके, अर्थपूर्ण उदाहरणे.
- महत्त्वाच्या संज्ञा प्रथम आल्यावर सोपा अर्थ.
- कोरडे bullet points देऊन थांबू नका; संकल्पना समजावून सांगा.
- बनावट गोष्टी, काल्पनिक ऐतिहासिक घटना किंवा अतिशयोक्ती नको.

खोली:
सुमारे 2,000–2,800 मराठी शब्दांचे मुख्य notes तयार करा.
25 मिनिटांच्या लक्षपूर्वक अभ्यासासाठी पुरेशी खोली असावी.
शब्दसंख्या वाढवण्यासाठी पुनरावृत्ती किंवा filler नको.

अनिवार्य रचना:
1. रोचक सुरुवात / विचार करायला लावणारा प्रश्न.
2. अध्ययन उद्दिष्टे.
3. संकल्पना आणि ऐतिहासिक पार्श्वभूमी.
4. कालखंड/घटना/उपघटक क्रमाने सविस्तर स्पष्टीकरण.
5. कारणे, प्रक्रिया आणि परिणाम यांचे संबंध.
6. भारताचा आणि महाराष्ट्राचा संदर्भ (विषयानुसार लागू असल्यास).
7. तुलना तक्ता / कालरेषा / महत्त्वाच्या संज्ञा.
8. पुरावा काय सांगतो आणि त्यातून काय निष्कर्ष काढता येत नाही.
9. MPSC परीक्षेच्या दृष्टीने महत्त्वाचे मुद्दे.
10. सामान्य गैरसमज व विद्यार्थ्यांच्या चुका.
11. पाच संकल्पनाधारित self-check प्रश्न आणि उत्तरे.
12. झटपट पुनरावलोकन.
13. स्रोत-पडताळणी स्थिती: पडताळलेले, वादग्रस्त, अजून पडताळायचे.

तथ्य नियम:
- प्रदेशानुसार दिनांक/घटनांमध्ये फरक असल्यास स्पष्ट सांगा.
- विद्वानांचे मत आणि निश्चित पुरावा वेगळे दाखवा.
- बनावट संदर्भ, पुस्तक, लेखक, वर्ष, पृष्ठ क्रमांक किंवा PYQ नको.
- मूळ प्रश्नपत्रिकेतून पुष्टी नसताना कोणताही प्रश्न PYQ म्हणून देऊ नका.
- AI ने तयार केलेले प्रश्न नेहमी Practice MCQ म्हणूनच ओळखा.

स्रोत सूचना:
{source_instructions}
{web_instructions}

स्थानिक संदर्भ साहित्य:
-----------------------
{source_text if source_text else "स्थानिक स्रोत उपलब्ध नाहीत."}
-----------------------

विद्यार्थ्याला थेट शिकवण्यासाठी तयार Markdown notes द्या.
"""


def visuals_prompt(subject: str, topic_id: str, topic: str, notes: str) -> str:
    return f"""
खालील विषयासाठी मराठीत Visual Revision Pack तयार करा.
Subject: {subject}; Topic ID: {topic_id}; Topic: {topic}

मजकूर:
{notes[:18000]}

यामध्ये हे द्या:
1. एक Mermaid flowchart किंवा mind map.
2. एक timeline किंवा क्रमवार तक्ता.
3. एक comparison table.
4. 5 visual memory cues, पण तथ्य बदलू नका.
5. प्रत्येक visual मध्ये वापरलेली तथ्ये notes शी सुसंगत असावीत.
6. अनिश्चित तथ्यांना निश्चित म्हणून दाखवू नका.

फक्त Markdown द्या. Mermaid code fences वापरू शकता.
"""


def practice_prompt(subject: str, topic_id: str, topic: str, notes: str) -> str:
    return f"""
तुम्ही MPSC मराठी माध्यमासाठी प्रश्नसंच तयार करणारे शिक्षक आहात.
विषय: {subject}; Topic ID: {topic_id}; Topic: {topic}

आधार notes:
{notes[:18000]}

फक्त JSON object द्या. Markdown fences नकोत. खालील keys अनिवार्य आहेत:

{{
  "practice_mcqs": [
    {{
      "question": "मराठी प्रश्न",
      "options": {{"A":"पर्याय","B":"पर्याय","C":"पर्याय","D":"पर्याय"}},
      "correct_option": "A",
      "explanation": "योग्य उत्तर आणि इतर पर्याय का अयोग्य याचे स्पष्टीकरण",
      "concept": "तपासली जाणारी संकल्पना",
      "difficulty": "Easy/Medium/Hard"
    }}
  ],
  "topic_test": [
    {{
      "question": "मराठी प्रश्न",
      "options": {{"A":"पर्याय","B":"पर्याय","C":"पर्याय","D":"पर्याय"}},
      "correct_option": "A",
      "explanation": "स्पष्टीकरण",
      "concept": "संकल्पना",
      "difficulty": "Easy/Medium/Hard"
    }}
  ],
  "flashcards": [
    {{"front":"प्रश्न/संज्ञा","back":"उत्तर व छोटी समजावणी"}}
  ],
  "quick_recall": [
    {{"question":"आठवणीचा प्रश्न","answer":"संक्षिप्त समजावणी"}}
  ]
}}

अचूक संख्या:
- practice_mcqs: 30
- topic_test: 10
- flashcards: 10
- quick_recall: 5

नियम:
- सर्व प्रश्न मराठीत आणि विषयाशी थेट संबंधित असावेत.
- प्रश्न विविध प्रकारचे ठेवा: संकल्पना, कारण-परिणाम, तुलना, विधानाधारित, कालक्रम.
- प्रश्न एकमेकांची पुनरावृत्ती नसावेत.
- प्रत्येक प्रश्नाला एकच निर्विवाद योग्य उत्तर असावे.
- स्पष्टीकरण अर्थपूर्ण असावे; फक्त पर्यायाचे अक्षर नको.
- notes मध्ये आधार नसलेली नवी तथ्ये घालू नका.
- कोणत्याही प्रश्नाला PYQ म्हणू नका; हे सर्व Practice MCQ आहेत.
- JSON पूर्ण आणि parse करता येण्यासारखा द्या.
"""


def pyq_prompt(topic_id: str, topic: str, extracted_pdf_text: str) -> str:
    return f"""
तुम्हाला MPSC प्रश्नपत्रिकांच्या PDF मधून काढलेला मजकूर दिला आहे.
फक्त या मजकुरातून संबंधित प्रश्न शोधा.

Topic ID: {topic_id}
Topic: {topic}

कडक नियम:
- बाहेरील स्मरणावरून प्रश्न जोडू नका.
- प्रश्नाच्या मजकुरात बदल करू नका; OCR/मजकूर त्रुटी असल्यास review flag द्या.
- परीक्षा, वर्ष, पेपर, प्रश्न क्रमांक किंवा उत्तर स्रोतामध्ये स्पष्ट नसेल तर null द्या.
- प्रत्येक नोंदीत PDF filename आणि दिलेला page label नोंदवा.
- थेट संबंधित नसलेला प्रश्न समाविष्ट करू नका.
- स्रोतामध्ये उत्तरतालिका नसेल तर उत्तर null ठेवा.
- हा AI extraction candidate आहे; अंतिम PYQ म्हणून publish करण्यापूर्वी मानवी तपासणी आवश्यक आहे.

फक्त JSON द्या:
{{
 "pyq_candidates": [
   {{
     "question": "मूळ प्रश्न",
     "options": {{"A":"...","B":"...","C":"...","D":"..."}},
     "exam": null,
     "year": null,
     "paper": null,
     "question_number": null,
     "answer": null,
     "source_file": "PDF filename",
     "source_page": "PAGE label",
     "verification_status": "needs_human_verification",
     "notes": "काय तपासणे बाकी आहे"
   }}
 ]
}}

PDF मधून काढलेला मजकूर:
-----------------------
{extracted_pdf_text[:MAX_SOURCE_CHARS]}
-----------------------
"""


def write_markdown_questions(
    rows: list[dict[str, Any]],
    title: str,
    include_difficulty: bool = True,
) -> str:
    lines = [f"# {title}", ""]
    if not rows:
        return "\n".join(lines + ["प्रश्न उपलब्ध नाहीत.", ""])

    for index, row in enumerate(rows, start=1):
        lines.append(f"## प्रश्न {index}")
        lines.append(str(row.get("question", "प्रश्न उपलब्ध नाही")))
        options = row.get("options") or {}
        for key in ("A", "B", "C", "D"):
            if key in options:
                lines.append(f"- **{key}.** {options[key]}")
        answer = row.get("correct_option")
        if answer:
            lines.append(f"\n**योग्य उत्तर:** {answer}")
        if row.get("explanation"):
            lines.append(f"\n**स्पष्टीकरण:** {row['explanation']}")
        if row.get("concept"):
            lines.append(f"\n**संकल्पना:** {row['concept']}")
        if include_difficulty and row.get("difficulty"):
            lines.append(f"\n**कठीणता:** {row['difficulty']}")
        lines.append("")
    return "\n".join(lines)


def write_flashcards(rows: list[dict[str, Any]]) -> str:
    lines = ["# Flashcards", ""]
    for i, item in enumerate(rows, start=1):
        lines += [
            f"## Card {i}",
            f"**प्रश्न:** {item.get('front', '')}",
            f"**उत्तर:** {item.get('back', '')}",
            "",
        ]
    return "\n".join(lines)


def write_recall(rows: list[dict[str, Any]]) -> str:
    lines = ["# Quick Recall", ""]
    for i, item in enumerate(rows, start=1):
        lines += [
            f"## {i}. {item.get('question', '')}",
            f"**उत्तर:** {item.get('answer', '')}",
            "",
        ]
    return "\n".join(lines)


def write_pyq(rows: list[dict[str, Any]], pdf_sources: list[str]) -> str:
    lines = [
        "# PYQ Candidates — मानवी पडताळणी आवश्यक",
        "",
        "हे प्रश्न फक्त दिलेल्या PDF मधून AI ने शोधलेले candidates आहेत. "
        "मूळ प्रश्नपत्रिका आणि अधिकृत उत्तरतालिका तपासल्याशिवाय publish करू नका.",
        "",
    ]
    if not pdf_sources:
        return "\n".join(lines + [
            "## सध्या PYQ उपलब्ध नाहीत",
            "",
            "या Topic ID साठी sources/TOPIC-ID/ मध्ये MPSC प्रश्नपत्रिकांच्या "
            "text-selectable PDF फाइल्स ठेवा आणि script पुन्हा चालवा.",
            "स्रोत नसताना AI कडून PYQ तयार करून घेतलेले नाहीत.",
            "",
        ])

    if not rows:
        lines += ["PDF स्रोत दिले, पण या विषयाशी संबंधित प्रश्न खात्रीने सापडले नाहीत.", ""]
    for i, row in enumerate(rows, start=1):
        lines += [
            f"## Candidate {i}",
            str(row.get("question", "")),
            f"- परीक्षा: {row.get('exam')}",
            f"- वर्ष: {row.get('year')}",
            f"- पेपर: {row.get('paper')}",
            f"- प्रश्न क्रमांक: {row.get('question_number')}",
            f"- उत्तर: {row.get('answer')}",
            f"- स्रोत: {row.get('source_file')} / {row.get('source_page')}",
            f"- स्थिती: {row.get('verification_status', 'needs_human_verification')}",
            f"- तपासणी नोंद: {row.get('notes', '')}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate one Marathi MPSC topic pack with Gemini."
    )
    parser.add_argument("--topic-id", help="Example: HIS-001")
    parser.add_argument("--subject", help="Example: इतिहास")
    parser.add_argument("--topic", help="Example: प्रागैतिहासिक काळ")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--web-research",
        action="store_true",
        help="Enable Google Search grounding (uses search-grounding quota).",
    )
    args = parser.parse_args()

    topic_id = args.topic_id or input("Topic ID (उदा. HIS-001): ").strip()
    subject = args.subject or input("विषय (उदा. इतिहास): ").strip()
    topic = args.topic or input("Topic Name (उदा. प्रागैतिहासिक काळ): ").strip()

    if not topic_id or not subject or not topic:
        print("ERROR: Topic ID, subject and topic name are required.")
        return 2

    topic_id = safe_folder_name(topic_id)
    output_dir = OUTPUT_ROOT / topic_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nMPSC Katta — AI Topic Pack Generator")
    print(f"Topic: {topic_id} | {subject} | {topic}")
    print(f"Model: {args.model}")
    print(f"Google Search grounding: {'ON' if args.web_research else 'OFF'}")

    source_text, source_metadata = collect_sources(topic_id)
    if source_text:
        print(f"Local reference material loaded ({len(source_text):,} characters).")
    else:
        print("No local reference material found. Output will be marked DRAFT.")

    try:
        client = build_client()
        research: dict[str, Any] = {
            "topic_id": topic_id,
            "subject": subject,
            "topic": topic,
            "model": args.model,
            "generated_at": datetime.now().astimezone().isoformat(),
            "web_search_grounding_enabled": args.web_research,
            "local_sources": source_metadata,
            "grounding_metadata": {},
        }

        print("\n[1/4] Detailed Marathi notes...")
        notes, grounding = generate_text(
            client,
            args.model,
            notes_prompt(subject, topic_id, topic, source_text, args.web_research),
            12000,
            args.web_research,
        )
        (output_dir / "detailed_notes.md").write_text(notes, encoding="utf-8")
        research["grounding_metadata"]["notes"] = grounding

        print("[2/4] Visual revision pack...")
        visuals, grounding = generate_text(
            client,
            args.model,
            visuals_prompt(subject, topic_id, topic, notes),
            4500,
            args.web_research,
        )
        (output_dir / "visuals.md").write_text(visuals, encoding="utf-8")
        research["grounding_metadata"]["visuals"] = grounding

        print("[3/4] MCQs, topic test, flashcards and quick recall...")
        practice_raw, grounding = generate_text(
            client,
            args.model,
            practice_prompt(subject, topic_id, topic, notes),
            12000,
            args.web_research,
            json_mode=True,
        )
        practice = json_from_response(practice_raw)
        research["grounding_metadata"]["practice"] = grounding

        mcqs = practice.get("practice_mcqs", [])
        tests = practice.get("topic_test", [])
        flashcards = practice.get("flashcards", [])
        recalls = practice.get("quick_recall", [])

        (output_dir / "practice_mcqs.md").write_text(
            write_markdown_questions(mcqs, "30 Practice MCQs"),
            encoding="utf-8",
        )
        (output_dir / "topic_test.md").write_text(
            write_markdown_questions(tests, "10 प्रश्नांची Topic Test"),
            encoding="utf-8",
        )
        (output_dir / "flashcards.md").write_text(
            write_flashcards(flashcards), encoding="utf-8"
        )
        (output_dir / "quick_recall.md").write_text(
            write_recall(recalls), encoding="utf-8"
        )

        print("[4/4] PYQ candidates from supplied question-paper PDFs...")
        pdf_files = [
            item["file"]
            for item in source_metadata
            if item.get("type") == "pdf"
            and item.get("pages_with_extractable_text", 0) > 0
            and any(part.lower() == "pyq" for part in Path(item["file"]).parts)
        ]
        pyq_rows: list[dict[str, Any]] = []
        if pdf_files and source_text:
            pyq_raw, grounding = generate_text(
                client,
                args.model,
                pyq_prompt(topic_id, topic, source_text),
                5000,
                False,
                json_mode=True,
            )
            pyq_data = json_from_response(pyq_raw)
            pyq_rows = pyq_data.get("pyq_candidates", [])
            research["grounding_metadata"]["pyq_extraction"] = grounding
        else:
            print("No extractable source-paper PDF; no PYQs will be invented.")

        (output_dir / "pyq_candidates.md").write_text(
            write_pyq(pyq_rows, pdf_files), encoding="utf-8"
        )

        (output_dir / "research_sources.json").write_text(
            json.dumps(research, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        notes_words = word_count(notes)
        warnings = []
        if notes_words < NOTES_MIN_WORDS:
            warnings.append(
                f"Notes are {notes_words} words; review whether 25-minute depth is sufficient."
            )
        elif not (NOTES_TARGET_MIN <= notes_words <= NOTES_TARGET_MAX):
            warnings.append(
                f"Notes are {notes_words} words; preferred target is "
                f"{NOTES_TARGET_MIN}-{NOTES_TARGET_MAX}."
            )
        if len(mcqs) != 30:
            warnings.append(f"Expected 30 practice MCQs; received {len(mcqs)}.")
        if len(tests) != 10:
            warnings.append(f"Expected 10 test questions; received {len(tests)}.")
        if len(flashcards) != 10:
            warnings.append(f"Expected 10 flashcards; received {len(flashcards)}.")
        if len(recalls) != 5:
            warnings.append(f"Expected 5 recall questions; received {len(recalls)}.")

        report = [
            f"# Quality Report — {topic_id}",
            "",
            "**Status: DRAFT — human fact-check and approval required**",
            "",
            f"- Subject: {subject}",
            f"- Topic: {topic}",
            f"- Notes word count: {notes_words}",
            f"- Practice MCQs: {len(mcqs)}",
            f"- Topic test questions: {len(tests)}",
            f"- Flashcards: {len(flashcards)}",
            f"- Quick recall questions: {len(recalls)}",
            f"- PYQ candidates extracted from source PDFs: {len(pyq_rows)}",
            f"- Local source items: {len(source_metadata)}",
            f"- Google Search grounding: {'Enabled' if args.web_research else 'Disabled'}",
            "",
            "## Review warnings",
            *([f"- {warning}" for warning in warnings] if warnings else ["- No count/length warnings."]),
            "",
            "## Mandatory manual checks",
            "- Historical dates, site names, interpretations and claims against reliable sources.",
            "- All answer keys and explanations.",
            "- PYQ wording, year, exam, paper, question number and official answer key.",
            "- Copyright/licence before republishing any source material.",
            "- Do not call AI-generated practice questions PYQs.",
            "",
            "This report checks structure and counts only; it does not certify factual accuracy.",
        ]
        (output_dir / "quality_report.md").write_text(
            "\n".join(report), encoding="utf-8"
        )

        index = [
            f"# {topic_id} — {topic}",
            "",
            f"- Subject: {subject}",
            "- Status: Draft — verification pending",
            "",
            "## Topic Pack",
            "- [Detailed Notes](detailed_notes.md)",
            "- [Visual Revision](visuals.md)",
            "- [Practice MCQs](practice_mcqs.md)",
            "- [Topic Test](topic_test.md)",
            "- [Flashcards](flashcards.md)",
            "- [Quick Recall](quick_recall.md)",
            "- [PYQ Candidates](pyq_candidates.md)",
            "- [Research Sources](research_sources.json)",
            "- [Quality Report](quality_report.md)",
        ]
        (output_dir / "README.md").write_text("\n".join(index), encoding="utf-8")

        print("\nSUCCESS — Topic pack generated.")
        print(f"Output folder: {output_dir}")
        print("Review quality_report.md before using or publishing anything.")
        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}")
        print(
            "Check .env/API key, model access, internet, free-tier quota, "
            "source files and SDK versions."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
