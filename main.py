"""
MPSC Katta — AI Topic Pack Generator
One topic in -> Marathi learning pack out.

Uses Gemini Developer API (Google AI Studio), not ChatGPT Go.
Does NOT invent PYQs: questions must come from local source files or grounded web pages with traceable references.
All generated material remains DRAFT until human/source verification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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
NOTES_MIN_WORDS = 2_400
NOTES_TARGET_MIN = 2_800
NOTES_TARGET_MAX = 3_500
PRACTICE_MCQ_COUNT = 50


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


def collect_sources(topic_id: str) -> tuple[str, list[dict[str, Any]], str]:
    """
    Collect local TXT/MD/PDF references. Files inside a pyq/ folder are
    isolated from lesson notes and sent only to PYQ extraction.
    PDF extraction is text-only; scanned PDFs need manual/OCR processing.
    """
    candidates: list[Path] = []
    topic_sources_dir = SOURCES_ROOT / topic_id
    if topic_sources_dir.exists():
        for path in topic_sources_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name.lower() == "readme.md" or path.name.lower().endswith("reference_log.md"):
                continue
            if path.suffix.lower() in {".txt", ".md", ".pdf"} and path not in candidates:
                candidates.append(path)

    blocks: list[str] = []
    pyq_blocks: list[str] = []
    metadata: list[dict[str, Any]] = []
    remaining = MAX_SOURCE_CHARS

    for path in sorted(candidates):
        if remaining <= 0:
            break

        relative = str(path.relative_to(ROOT))
        is_pyq_source = "pyq" in {part.lower() for part in Path(relative).parts}

        if path.suffix.lower() in {".txt", ".md"}:
            body = read_text_file(path)
            if not body:
                continue
            body = body[:remaining]
            if is_pyq_source:
                pyq_blocks.append(
                    f"\n\n===== LOCAL PYQ SOURCE: {relative} =====\n{body}"
                )
            else:
                blocks.append(f"\n\n===== REFERENCE SOURCE: {relative} =====\n{body}")
            metadata.append({
                "file": relative,
                "type": "text",
                "purpose": "pyq" if is_pyq_source else "reference",
                "characters_included": len(body),
            })
            remaining -= len(body)

        elif path.suffix.lower() == ".pdf":
            if PdfReader is None:
                metadata.append({
                    "file": relative,
                    "type": "pdf",
                    "purpose": "pyq" if is_pyq_source else "reference",
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
                    if is_pyq_source:
                        pyq_blocks.append(
                            f"\n\n===== LOCAL PYQ PDF: {relative} =====\n{combined}"
                        )
                    else:
                        blocks.append(
                            f"\n\n===== REFERENCE PDF: {relative} =====\n{combined}"
                        )
                    metadata.append({
                        "file": relative,
                        "type": "pdf",
                        "purpose": "pyq" if is_pyq_source else "reference",
                        "pages_with_extractable_text": len(pdf_parts),
                        "note": "Page labels are provided for human checking; scanned pages may not extract.",
                    })
                else:
                    metadata.append({
                        "file": relative,
                        "type": "pdf",
                        "purpose": "pyq" if is_pyq_source else "reference",
                        "status": "No selectable text extracted; scanned PDF needs manual processing.",
                    })
            except Exception as exc:
                metadata.append({
                    "file": relative,
                    "type": "pdf",
                    "purpose": "pyq" if is_pyq_source else "reference",
                    "status": f"Could not read PDF: {exc}",
                })

    return "\n".join(blocks), metadata, "\n".join(pyq_blocks)


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


def is_temporary_server_error(error: Exception) -> bool:
    """Return True only for transient server/availability errors."""
    message = str(error).lower()
    status = getattr(error, "code", None) or getattr(error, "status_code", None)
    if status in (500, 502, 503, 504):
        return True
    markers = (
        "503 unavailable",
        "service unavailable",
        "temporarily overloaded",
        "500 internal",
        "502 bad gateway",
        "504 deadline_exceeded",
        "gateway timeout",
    )
    return any(marker in message for marker in markers)


def generate_text(
    client: genai.Client,
    model: str,
    prompt: str,
    max_output_tokens: int,
    use_web_search: bool,
    json_mode: bool = False,
    thinking_level: str | None = None,
) -> tuple[str, Any, str]:
    config: dict[str, Any] = {
        "temperature": 0.35,
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        config["response_mime_type"] = "application/json"
    selected_thinking = (thinking_level or os.getenv("GEMINI_THINKING_LEVEL", "high")).strip().lower()
    if selected_thinking not in {"minimal", "low", "medium", "high"}:
        raise ValueError("GEMINI_THINKING_LEVEL must be minimal, low, medium or high.")
    config["thinking_config"] = types.ThinkingConfig(thinking_level=selected_thinking)
    if use_web_search:
        config["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    # If the primary model is overloaded, try a cheaper stable fallback.
    # 503 is temporary service capacity; 429 quota errors are not retried here.
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()
    model_candidates = [model]
    if fallback_model and fallback_model != model:
        model_candidates.append(fallback_model)

    waits = (3, 8, 15)
    last_error: Exception | None = None

    for model_index, candidate_model in enumerate(model_candidates):
        for attempt in range(len(waits) + 1):
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=prompt,
                    config=config,
                )
                response_text = (response.text or "").strip()
                if not response_text:
                    raise RuntimeError(
                        "The model returned no text. Check API quota, model access and safety feedback."
                    )
                if candidate_model != model:
                    print(f"Fallback model succeeded: {candidate_model}")
                return response_text, get_grounding_metadata(response), candidate_model
            except Exception as exc:
                last_error = exc
                if not is_temporary_server_error(exc):
                    raise
                if attempt < len(waits):
                    delay = waits[attempt]
                    print(
                        f"{candidate_model} is temporarily unavailable. "
                        f"Retry {attempt + 1}/{len(waits)} in {delay} seconds..."
                    )
                    time.sleep(delay)
                elif model_index + 1 < len(model_candidates):
                    print(
                        f"{candidate_model} is still overloaded after retries. "
                        f"Switching to fallback: {model_candidates[model_index + 1]}"
                    )
                else:
                    raise

    if last_error:
        raise last_error
    raise RuntimeError("Generation failed without a response.")


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
    topic_guidance: str = "",
) -> str:
    source_instructions = (
        "स्थानिक संदर्भ साहित्य वापरा. संबंधित महत्त्वाच्या तथ्याजवळ फाइलचे नाव व PDF पृष्ठ/विभाग द्या. "
        "स्रोतामध्ये नसलेला दावा त्या स्रोताने सिद्ध झाला असे दाखवू नका."
        if source_text
        else
        "स्थानिक संदर्भ साहित्य नाही. Google Search grounding वापरून अधिकृत सरकारी, संग्रहालय, विद्यापीठीय "
        "आणि peer-reviewed स्रोतांना प्राधान्य द्या. स्रोत न सापडल्यास दावे बनवू नका; मर्यादा स्पष्ट ठेवा."
    )
    web_instructions = (
        "Google Search grounding उपलब्ध आहे. विशेषतः दिनांक, स्थळे, पुरातत्त्वीय दावे आणि मतभेद तपासा. "
        "शेवटी विद्यार्थ्याला उपयोगी अशी निवडक संदर्भसूची द्या; फक्त प्रत्यक्ष वापरलेले स्रोत नोंदवा."
        if web_search else
        "Web search वापरलेले नाही. संदिग्ध किंवा अद्ययावत दाव्यांना निश्चित तथ्य म्हणून मांडू नका."
    )

    return f"""
तुम्ही महाराष्ट्रातील MPSC विद्यार्थ्यांसाठी शिकवणारे उत्कृष्ट इतिहास शिक्षक,
मराठी कथनात्मक शैक्षणिक लेखक आणि काटेकोर तथ्य-पडताळणी करणारे संपादक आहात.

विषय: {subject}
आतील Topic ID: {topic_id}
विद्यार्थ्याला शिकवायचा विषय: {topic}

## मुख्य ध्येय
विद्यार्थ्याला पाठांतर करायला लावण्याऐवजी त्याच्या डोळ्यांसमोर भूतकाळ उभा राहील अशा पद्धतीने शिकवा.
वाचताना कुतूहल वाढले पाहिजे. प्रत्येक महत्त्वाच्या बदलामागचे कारण, प्रक्रिया, पुरावा आणि परिणाम
विद्यार्थ्याला स्वतःच्या शब्दांत समजावता आले पाहिजेत.

## विद्यार्थ्यांसाठी लेखनशैली
- संपूर्ण मजकूर सोप्या, नैसर्गिक, शुद्ध मराठीत आणि देवनागरी लिपीत लिहा.
- सुरुवातीला एक प्रभावी प्रश्न, पुराव्यावर आधारित प्रसंग किंवा आजच्या जीवनाशी जोडणारा विचार द्या.
- लहान, प्रवाही परिच्छेद लिहा. प्रत्येक परिच्छेद एक कल्पना पुढे नेईल.
- अवघड संज्ञेचा अर्थ ती पहिल्यांदा येते तेव्हाच साध्या भाषेत उलगडा करा.
- योग्य ठिकाणी “कल्पना करा”, “थोडा विचार करा”, “यातून काय समजते?” अशा संवादात्मक ओळी वापरा.
- तुलना, लहान तक्ते, कालरेषा, उदाहरणे आणि लक्षात राहतील अशा उपमा वापरा.
- कोरड्या मुद्द्यांची यादी, पाठ्यपुस्तकी यांत्रिक रचना, वारंवार पुनरावृत्ती आणि filler टाळा.
- बनावट संवाद, काल्पनिक ऐतिहासिक प्रसंग, नाट्यमय पण पुराव्याविना दावे किंवा अतिशयोक्ती नको.
- फक्त परीक्षेसाठी नव्हे, तर विषय समजण्यासाठी लिहा. आवश्यक तेथे परीक्षेतील गोंधळ समजावून सांगा.

## लांबी व खोली — ही अंतर्गत संपादकीय मर्यादा आहे
मुख्य नोट्स साधारण 2,800–3,500 मराठी शब्दांच्या असाव्यात. विषयाची गुणवत्ता महत्त्वाची;
माहिती नसताना शब्दसंख्या पूर्ण करण्यासाठी मजकूर वाढवू नका.

## रचना — विद्यार्थ्यांच्या समजुतीनुसार नैसर्गिक क्रम निवडा
सुरुवात, स्पष्टीकरण, उदाहरणे, भारत/महाराष्ट्र संदर्भ, तुलना आणि सारांश यांचा अर्थपूर्ण प्रवाह ठेवा.
सर्व मुद्दे स्वतंत्र checklist किंवा कठोर 13-section template मध्ये बदलू नका.
जिथे उपयुक्त असेल तिथे लहान चौकट द्या: “लक्षात ठेवा”, “हे का महत्त्वाचे?”, “पुरावा काय सांगतो?”
शेवटी विद्यार्थ्याला विषयाची जोडलेली समज मिळेल असा छोटा सारांश द्या.

## विद्यार्थ्यांच्या नोट्समध्ये अजिबात छापू नका
- Topic ID, अंतर्गत prompt, शिक्षकांसाठीचे निर्देश किंवा content-generation workflow.
- 55 मिनिटांचा अभ्यास आराखडा, 25 मिनिटांची शब्दमर्यादा, वेळेचे विभाग किंवा admin checklist.
- अंतर्गत पडताळणी स्थिती, quality score, “DRAFT”, review warnings किंवा स्रोत अपुरे असल्याची प्रशासकीय नोंद.
- “अध्ययन उद्दिष्टे” किंवा “स्रोत-पडताळणी checklist” अशी केवळ अंतर्गत नियोजनासाठी असलेली headings.
- या prompt मधील अंतर्गत coverage points जसेच्या तसे copy करू नका. ते फक्त विषयाचे कव्हरेज नियोजित करण्यासाठी आहेत.

## तथ्यनिष्ठतेचे नियम
- प्रदेशानुसार कालमर्यादा बदलत असल्यास ते स्पष्ट करा; एकच दिनांक संपूर्ण उपखंडाला लागू करू नका.
- पुरावा, संशोधकांचे अर्थलक्षण आणि वादग्रस्त मत वेगळे ओळखा.
- जागतिक मानवप्रजातींची माहिती आणि भारतीय स्थळांवरील थेट पुरावा एकमेकांत मिसळू नका.
- एखाद्या स्थळाचा भौगोलिक/कालखंडीय संदर्भ तपासा. उदाहरणार्थ, मेहरगढ आजच्या पाकिस्तानमध्ये आहे.
- सर्व नवपाषाण समुदायांकडे एकाच वेळी शेती, पशुपालन, चाकावरची भांडी आणि स्थिर वस्ती होती असे दाखवू नका.
- जंगली धान्याचा वापर, लागवडीचा पुरावा आणि पूर्ण domestication यांत फरक ठेवा.
- “सर्वात जुने”, “पहिले”, “संपूर्ण भारतात” असे व्यापक दावे ठोस स्रोतांशिवाय करू नका.
- बनावट लेखक, पुस्तक, URL, पृष्ठ क्रमांक, उत्खनन अहवाल किंवा उद्धरण तयार करू नका.
- AI ने तयार केलेल्या प्रश्नांना PYQ म्हणू नका.

## स्रोत सूचना
{source_instructions}
{web_instructions}

## अंतर्गत शिक्षक मार्गदर्शन — विद्यार्थ्यांना दाखवायचे नाही
खालील मार्गदर्शन विषयाचे पुरेसे कव्हरेज ठरवण्यासाठी आहे. याला नोट्समधील headings/checklist म्हणून छापू नका.
आवश्यक मुद्दे नैसर्गिक शिकवणीच्या प्रवाहात मिसळा; अप्रासंगिक/असमर्थित मुद्दे जबरदस्तीने घालू नका.

{topic_guidance if topic_guidance.strip() else "विषयाच्या नावानुसार उपयुक्त उपविषय ओळखा आणि विश्वसनीय पुराव्यांवरच आधारित रहा."}

## स्थानिक संदर्भ साहित्य
-----------------------
{source_text if source_text else "स्थानिक संदर्भ साहित्य उपलब्ध नाही."}
-----------------------

आता थेट विद्यार्थ्याला शिकवण्यासाठी तयार, आकर्षक आणि user-friendly Markdown नोट्स लिहा.
अंतर्गत मार्गदर्शन किंवा generation instructions आउटपुटमध्ये उघड करू नका.
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
तुम्ही MPSC मराठी माध्यमासाठी उच्च दर्जाचा प्रश्नसंच तयार करणारे शिक्षक आहात.
विषय: {subject}; Topic: {topic}

आधार नोट्स:
{notes[:26000]}

फक्त parse करता येणारा JSON object द्या. Markdown fences नकोत.
या रचनेत फक्त practice_mcqs ही key असावी:

{{
  "practice_mcqs": [
    {{
      "question": "मराठी प्रश्न",
      "options": {{"A":"पर्याय","B":"पर्याय","C":"पर्याय","D":"पर्याय"}},
      "correct_option": "A",
      "explanation": "योग्य उत्तराचे कारण आणि इतर पर्याय का अयोग्य आहेत याचे स्पष्टीकरण",
      "concept": "तपासली जाणारी संकल्पना",
      "difficulty": "Easy/Medium/Hard"
    }}
  ]
}}

अचूक संख्या: {PRACTICE_MCQ_COUNT} स्वतंत्र व दर्जेदार प्रश्न.

गुणवत्ता:
- संपूर्ण विषयाचे संतुलित coverage ठेवा; एकाच उपघटकावर प्रश्नांचा ढीग नको.
- साधारण 10 सोपे, 25 मध्यम आणि 15 कठीण प्रश्न ठेवा.
- संकल्पना, कारण-परिणाम, तुलना, कालक्रम, स्थळ-पुरावा, विधानाधारित, योग्य जोड्या व निष्कर्षाधारित प्रकार मिसळा.
- प्रश्नांची पुनरावृत्ती करू नका.
- प्रत्येक प्रश्नाला एकच निर्विवाद योग्य उत्तर असावे.
- प्रत्येक उत्तराचे अर्थपूर्ण स्पष्टीकरण द्या.
- उत्तरांची अक्षरे A/B/C/D यांत शक्य तितकी समतोल ठेवा.
- नोट्समध्ये आधार नसलेली नवी तथ्ये घालू नका.
- हे सर्व नव्याने तयार केलेले Practice MCQs आहेत; त्यांना PYQ म्हणू नका.
"""


def pyq_prompt(topic_id: str, topic: str, extracted_source_text: str) -> str:
    return f"""
तुम्हाला स्थानिक PYQ फोल्डरमधील PDF/TXT/Markdown स्रोतांतून काढलेला मजकूर दिला आहे.
फक्त या मजकुरातून संबंधित प्रश्न शोधा.

Topic ID: {topic_id}
Topic: {topic}

कडक नियम:
- बाहेरील स्मरणावरून प्रश्न जोडू नका.
- प्रश्नाचा मूळ शब्दप्रयोग शक्य तितका तसाच ठेवा; OCR/टंक त्रुटी असल्यास review flag द्या.
- परीक्षा, वर्ष, पेपर, प्रश्न क्रमांक किंवा उत्तर स्रोतामध्ये स्पष्ट नसेल तर null द्या.
- प्रत्येक नोंदीत नेमके source filename आणि उपलब्ध page/section नोंदवा.
- एखाद्या secondary website चा URL स्रोत मजकुरात दिला असेल तर तो तसाच नोंदवा.
- स्रोतामध्ये उत्तरतालिका नसेल तर answer null ठेवा.
- mock test, coaching practice किंवा नव्याने लिहिलेला प्रश्न समाविष्ट करू नका.
- अंतिम प्रकाशनापूर्वी मूळ प्रश्नपत्रिका व अधिकृत अंतिम उत्तरतालिकेशी मानवी पडताळणी आवश्यक आहे.

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
     "source_file": "मजकुरातील अचूक filename",
     "source_page": null,
     "source_section": null,
     "source_url": null,
     "answer_source_url": null,
     "answer_verified": false,
     "source_type": "local_pdf_or_reference_record",
     "verification_status": "needs_human_verification",
     "notes": "काय तपासणे बाकी आहे"
   }}
 ]
}}

स्थानिक PYQ स्रोत:
-----------------------
{extracted_source_text[:MAX_SOURCE_CHARS]}
-----------------------
"""


def web_pyq_prompt(subject: str, topic_id: str, topic: str, notes: str) -> str:
    return f"""
Google Search grounding वापरून महाराष्ट्र लोकसेवा आयोगाच्या (MPSC) प्रत्यक्ष मागील प्रश्नपत्रिकांतील
या विषयाशी संबंधित प्रश्न शोधा.

विषय: {subject}
Topic ID: {topic_id}
घटक: {topic}

नोट्समधील विषयसीमा:
{notes[:10000]}

शोधाचे प्राधान्य:
1. प्रथम MPSC ची अधिकृत question paper आणि official final answer key.
2. अधिकृत कागदपत्र सापडत नसेल तर फक्त असा विश्वासार्ह PYQ archive वापरा ज्यात exam, year, paper,
   question number आणि प्रश्नाचे पर्याय स्पष्ट दिसतात.
3. फक्त topic शी थेट संबंधित प्रश्न निवडा. सर्व Ancient History प्रश्न या topic चे PYQ समजू नका.
4. प्रागैतिहासिक/पुरापाषाण/मध्यपाषाण/नवपाषाण, पुरावे, दगडी साधने किंवा त्या विशिष्ट स्थळांशी
   थेट संबंध असेल तेव्हाच समाविष्ट करा.

अत्यंत महत्त्वाचे:
- Coaching mock test, practice set, model question किंवा AI-generated प्रश्न PYQ म्हणून देऊ नका.
- प्रश्नाचा मूळ मजकूर उपलब्ध असल्यास तोच जतन करा. प्रश्न फक्त search snippet मध्ये अपूर्ण दिसत असेल तर वगळा.
- Exam/year/paper/question number स्रोतावर दिसत नसल्यास null ठेवा; अंदाज लावू नका.
- उत्तर official MPSC final key मध्येच तपासले असल्यास answer_verified=true करा.
- Third-party page वर उत्तर दिसत असल्यास answer_verified=false आणि source_type="third_party_archive" ठेवा.
- प्रत्येक प्रश्नासाठी source_url द्या. अधिकृत उत्तरतालिकेचा वेगळा URL उपलब्ध असल्यास answer_source_url द्या.
- एखादा relevant वास्तविक प्रश्न न सापडल्यास रिकामी यादी द्या. प्रश्न निर्माण करू नका.
- जास्त प्रश्न मिळवण्यासाठी गैर-संबंधित प्रश्न जबरदस्तीने जोडू नका.

फक्त JSON object द्या:
{{
  "web_pyq_candidates": [
    {{
      "question": "स्रोतावर दिसणारा मूळ प्रश्न",
      "options": {{"A":"...","B":"...","C":"...","D":"..."}},
      "exam": null,
      "year": null,
      "paper": null,
      "question_number": null,
      "answer": null,
      "answer_verified": false,
      "source_url": "exact page URL",
      "answer_source_url": null,
      "source_type": "official_mpsc_or_third_party_archive",
      "verification_status": "original_paper_and_official_key_review_pending",
      "explanation": "थोडक्यात संकल्पना स्पष्ट करा; स्रोताबाहेरील दावे टाळा"
    }}
  ]
}}

एकही अचूक, थेट संबंधित PYQ न सापडल्यास:
{{"web_pyq_candidates": []}}
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


def write_pyq(
    local_rows: list[dict[str, Any]],
    local_sources: list[str],
    web_rows: list[dict[str, Any]] | None = None,
) -> str:
    web_rows = web_rows or []
    lines = [
        "# PYQ — मागील वर्षांचे प्रश्न",
        "",
        "येथे फक्त स्रोतांतून मिळालेले प्रश्न दिले आहेत. प्रकाशनापूर्वी मूळ MPSC प्रश्नपत्रिका आणि अधिकृत अंतिम उत्तरतालिका तपासा.",
        "AI-निर्मित सराव प्रश्न या विभागात मिसळलेले नाहीत.",
        "",
    ]

    def append_rows(rows: list[dict[str, Any]], heading: str, web: bool = False) -> None:
        lines.extend([f"## {heading}", ""])
        if not rows:
            lines.extend(["सध्या अचूक स्रोतासह प्रश्न सापडले नाहीत.", ""])
            return
        for i, row in enumerate(rows, start=1):
            lines.append(f"### प्रश्न {i}")
            lines.append(str(row.get("question", "प्रश्न उपलब्ध नाही")))
            options = row.get("options") or {}
            for key in ("A", "B", "C", "D"):
                if key in options:
                    lines.append(f"- **{key}.** {options[key]}")
            if row.get("answer"):
                lines.append(f"\n**स्रोतावर दिलेले उत्तर:** {row['answer']}")
                if row.get("answer_verified") is False:
                    lines.append("**टीप:** अधिकृत अंतिम उत्तरतालिकेशी पडताळणी बाकी.")
            if row.get("explanation"):
                lines.append(f"\n**स्पष्टीकरण:** {row['explanation']}")
            details = [
                ("परीक्षा", row.get("exam")),
                ("वर्ष", row.get("year")),
                ("पेपर", row.get("paper")),
                ("प्रश्न क्रमांक", row.get("question_number")),
            ]
            for label, value in details:
                if value not in (None, "", "null"):
                    lines.append(f"- {label}: {value}")
            if web:
                if row.get("source_url"):
                    lines.append(f"- प्रश्न स्रोत: {row['source_url']}")
                if row.get("answer_source_url"):
                    lines.append(f"- उत्तरतालिका स्रोत: {row['answer_source_url']}")
                lines.append(f"- स्रोत प्रकार: {row.get('source_type', 'अस्पष्ट')}")
                lines.append(f"- पडताळणी: {row.get('verification_status', 'मानवी पडताळणी आवश्यक')}")
            else:
                lines.append(f"- स्थानिक स्रोत: {row.get('source_file')}")
                if row.get("source_page"):
                    lines.append(f"- पृष्ठ: {row.get('source_page')}")
                if row.get("source_section"):
                    lines.append(f"- विभाग: {row.get('source_section')}")
                if row.get("source_url"):
                    lines.append(f"- मूळ URL: {row.get('source_url')}")
                if row.get("answer_source_url"):
                    lines.append(f"- उत्तरतालिका URL: {row.get('answer_source_url')}")
                if row.get("source_type"):
                    lines.append(f"- स्रोत प्रकार: {row.get('source_type')}")
                lines.append(f"- पडताळणी: {row.get('verification_status', 'मानवी पडताळणी आवश्यक')}")
            if row.get("notes"):
                lines.append(f"- तपासणी नोंद: {row['notes']}")
            lines.append("")

    if local_sources:
        append_rows(local_rows, "स्थानिक PDF / TXT / Markdown स्रोत")
    if web_rows:
        append_rows(web_rows, "Google Search मधून सापडलेले PYQ candidates", web=True)
    if not local_sources and not web_rows:
        lines.extend([
            "## सध्या PYQ उपलब्ध नाहीत",
            "",
            "या Topic ID साठी sources/TOPIC-ID/pyq/ मध्ये मूळ प्रश्नपत्रिका PDF किंवा तपासलेला PYQ source record ठेवा. "
            "Google Search बंद असल्यास --web-research वापरा.",
            "",
        ])
    elif local_sources and not local_rows and not web_rows:
        lines.extend([
            "स्रोत फाइल्स मिळाल्या, पण या topic शी थेट संबंधित प्रश्न निश्चितपणे ओळखता आले नाहीत.",
            "",
        ])
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
        dest="web_research",
        action="store_true",
        help="Enable Google Search grounding (enabled by default).",
    )
    parser.add_argument(
        "--no-web-research",
        dest="web_research",
        action="store_false",
        help="Disable Google Search grounding to conserve quota.",
    )
    parser.set_defaults(web_research=True)
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
    internal_dir = OUTPUT_ROOT / "_internal" / topic_id
    internal_dir.mkdir(parents=True, exist_ok=True)
    for stale_name in (
        "README.md", "topic_test.md", "flashcards.md", "quick_recall.md",
        "pyq_candidates.md", "quality_report.md", "research_sources.json",
    ):
        stale_path = output_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()

    print("\nMPSC Katta — AI Topic Pack Generator")
    print(f"Topic: {topic_id} | {subject} | {topic}")
    print(f"Model: {args.model}")
    print(f"Google Search grounding: {'ON' if args.web_research else 'OFF'}")
    print(f"Thinking level: notes/PYQ={os.getenv('GEMINI_THINKING_LEVEL', 'high')}, "
          f"visuals/MCQ={os.getenv('GEMINI_AUX_THINKING_LEVEL', 'medium')}")

    source_text, source_metadata, pyq_source_text = collect_sources(topic_id)
    guidance_path = ROOT / "prompts" / f"{topic_id}_prompt.md"
    topic_guidance = read_text_file(guidance_path) if guidance_path.exists() else ""
    if topic_guidance:
        print(f"Internal topic guidance loaded: {guidance_path.name}")
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

        research["models_used"] = {}
        print("\n[1/4] Detailed Marathi notes...")
        notes, grounding, used_model = generate_text(
            client,
            args.model,
            notes_prompt(
                subject, topic_id, topic, source_text, args.web_research, topic_guidance
            ),
            14000,
            args.web_research,
            thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "high"),
        )
        (output_dir / "detailed_notes.md").write_text(notes, encoding="utf-8")
        research["grounding_metadata"]["notes"] = grounding
        research["models_used"]["notes"] = used_model

        print("[2/4] Visual revision pack...")
        visuals, grounding, used_model = generate_text(
            client,
            args.model,
            visuals_prompt(subject, topic_id, topic, notes),
            4500,
            False,
            thinking_level=os.getenv("GEMINI_AUX_THINKING_LEVEL", "medium"),
        )
        (output_dir / "visuals.md").write_text(visuals, encoding="utf-8")
        research["grounding_metadata"]["visuals"] = grounding
        research["models_used"]["visuals"] = used_model

        print("[3/4] MCQs, topic test, flashcards and quick recall...")
        practice_raw, grounding, used_model = generate_text(
            client,
            args.model,
            practice_prompt(subject, topic_id, topic, notes),
            18000,
            False,
            json_mode=True,
            thinking_level=os.getenv("GEMINI_AUX_THINKING_LEVEL", "medium"),
        )
        practice = json_from_response(practice_raw)
        research["grounding_metadata"]["practice"] = grounding
        research["models_used"]["practice"] = used_model

        mcqs = practice.get("practice_mcqs", [])

        (output_dir / "practice_mcqs.md").write_text(
            write_markdown_questions(mcqs, f"{PRACTICE_MCQ_COUNT} सराव MCQ"),
            encoding="utf-8",
        )

        print("[4/4] PYQ extraction + Google Search research...")
        pyq_files = [
            item["file"]
            for item in source_metadata
            if item.get("purpose") == "pyq"
            and (
                item.get("characters_included", 0) > 0
                or item.get("pages_with_extractable_text", 0) > 0
            )
        ]
        local_pyq_rows: list[dict[str, Any]] = []
        web_pyq_rows: list[dict[str, Any]] = []

        if pyq_files and pyq_source_text:
            local_pyq_raw, grounding, used_model = generate_text(
                client,
                args.model,
                pyq_prompt(topic_id, topic, pyq_source_text),
                7000,
                False,
                json_mode=True,
                thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "high"),
            )
            pyq_data = json_from_response(local_pyq_raw)
            local_pyq_rows = pyq_data.get("pyq_candidates", [])
            research["grounding_metadata"]["pyq_local_extraction"] = grounding
            research["models_used"]["pyq_local_extraction"] = used_model
        else:
            print("No local PYQ PDF/TXT/Markdown source found.")

        if args.web_research:
            try:
                web_pyq_raw, grounding, used_model = generate_text(
                    client,
                    args.model,
                    web_pyq_prompt(subject, topic_id, topic, notes),
                    9000,
                    True,
                    json_mode=True,
                    thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "high"),
                )
                web_pyq_data = json_from_response(web_pyq_raw)
                web_pyq_rows = web_pyq_data.get("web_pyq_candidates", [])
                research["grounding_metadata"]["pyq_web_search"] = grounding
                research["models_used"]["pyq_web_search"] = used_model
            except Exception as exc:
                warnings_for_pyq = research.setdefault("warnings", [])
                warnings_for_pyq.append(f"Web PYQ search could not complete: {exc}")
                print(f"Web PYQ search unavailable; local PYQ results are retained. Reason: {exc}")
        else:
            print("Web PYQ search disabled by --no-web-research.")

        # Remove duplicate web hits already extracted from local source files.
        local_question_keys = {
            re.sub(r"\W+", "", str(row.get("question", "")).lower())
            for row in local_pyq_rows
        }
        web_pyq_rows = [
            row for row in web_pyq_rows
            if re.sub(r"\W+", "", str(row.get("question", "")).lower())
            not in local_question_keys
        ]

        (output_dir / "pyq.md").write_text(
            write_pyq(local_pyq_rows, pyq_files, web_pyq_rows),
            encoding="utf-8",
        )

        (internal_dir / "research_sources.json").write_text(
            json.dumps(research, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        notes_words = word_count(notes)
        warnings = research.get("warnings", [])
        if notes_words < NOTES_MIN_WORDS:
            warnings.append(
                f"Notes are {notes_words} words; review whether 25-minute depth is sufficient."
            )
        elif not (NOTES_TARGET_MIN <= notes_words <= NOTES_TARGET_MAX):
            warnings.append(
                f"Notes are {notes_words} words; preferred target is "
                f"{NOTES_TARGET_MIN}-{NOTES_TARGET_MAX}."
            )
        if len(mcqs) != PRACTICE_MCQ_COUNT:
            warnings.append(
                f"Expected {PRACTICE_MCQ_COUNT} practice MCQs; received {len(mcqs)}."
            )

        report = [
            f"# Quality Report — {topic_id}",
            "",
            "**Status: DRAFT — human fact-check and approval required**",
            "",
            f"- Subject: {subject}",
            f"- Topic: {topic}",
            f"- Notes word count: {notes_words}",
            f"- Practice MCQs: {len(mcqs)} (target: {PRACTICE_MCQ_COUNT})",
            f"- PYQ candidates from local sources: {len(local_pyq_rows)}",
            f"- PYQ candidates from web search: {len(web_pyq_rows)}",
            f"- Local source items: {len(source_metadata)}",
            f"- Google Search grounding: {'Enabled' if args.web_research else 'Disabled'}",
            f"- Gemini thinking level (notes/PYQ): {os.getenv('GEMINI_THINKING_LEVEL', 'high')}",
            f"- Gemini thinking level (visuals/MCQ): {os.getenv('GEMINI_AUX_THINKING_LEVEL', 'medium')}",
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
        (internal_dir / "quality_report.md").write_text(
            "\n".join(report), encoding="utf-8"
        )

        print("\nSUCCESS — Topic pack generated.")
        print(f"Student pack (4 files): {output_dir}")
        print(f"Internal audit files: {internal_dir}")
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
