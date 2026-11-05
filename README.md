# MPSC Katta

A Marathi common-classroom content workspace for MPSC preparation. The first milestone is one subject and one topic: History — HIS-001, प्रागैतिहासिक काळ.

## What the one-topic generator creates

Run **main.py** with a Topic ID, subject and topic name. It creates:

- Student-friendly Marathi lesson notes (editorial target: about 2,000–2,600 words)
- Visual revision pack (Mermaid flowchart/mind map, timeline and comparison table)
- **50 Practice MCQs** with answers and explanations
- 10-question topic test
- 10 flashcards
- 5 quick-recall questions
- PYQ candidates extracted from local sources and discovered through Google Search grounding
- Research-source metadata and an internal quality report

The topic-specific file under **prompts/** is an internal coverage guide. The generator uses it to plan coverage, but is instructed not to expose the internal checklist, study-time budget, word target, quality status or admin workflow in student notes.

All generated files are saved under **output/TOPIC-ID/**. Nothing is automatically sent to Telegram.

## Gemini API settings

The generator uses Google's official **google-genai** Python SDK and Gemini Developer API. A ChatGPT Go subscription does not provide OpenAI API credits or a Gemini API key.

The generator uses:
- **Thinking level high** for lesson notes and PYQ research.
- **Thinking level medium** for visuals and practice question generation.
- **Google Search grounding ON by default** for factual research and web-based PYQ discovery.
- A primary model and fallback model configured in .env.

Gemini model names, API availability, quotas and pricing can change. Google Search grounding may consume project quota or incur charges after applicable free allowances. Check Google's current [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) before large batch runs. Do not submit confidential information to a third-party AI service.

Google AI Studio API key page: https://aistudio.google.com/apikey

## PyCharm setup

1. Clone this repository or open your existing local clone.
2. Create/activate your virtual environment.
3. In the PyCharm Terminal run:

   ~~~powershell
   python -m pip install -r requirements.txt
   ~~~

4. Copy **.env.example** to **.env**.
5. Open **.env** and set GEMINI_API_KEY to your own Google AI Studio key.
6. Review GEMINI_MODEL, GEMINI_FALLBACK_MODEL, GEMINI_THINKING_LEVEL and GEMINI_AUX_THINKING_LEVEL if needed.
7. Never commit .env or paste the API key in chat.

Example model settings:

   ~~~env
   GEMINI_MODEL=gemini-3.8-flash
   GEMINI_FALLBACK_MODEL=gemini-3.6-flash
   GEMINI_THINKING_LEVEL=high
   GEMINI_AUX_THINKING_LEVEL=medium
   ~~~

## Run one topic

~~~powershell
python main.py --topic-id HIS-001 --subject "इतिहास" --topic "प्रागैतिहासिक काळ"
~~~

Google Search grounding is enabled by default. To conserve search quota or work offline with local sources only:

~~~powershell
python main.py --topic-id HIS-001 --subject "इतिहास" --topic "प्रागैतिहासिक काळ" --no-web-research
~~~

## Supplying reference material and PYQs

Create a topic folder:

~~~text
sources/
└── HIS-001/
    ├── textbook_notes.pdf
    ├── reference.md
    └── pyq/
        ├── mpsc_question_paper.pdf
        ├── verified_question_record.md
        └── scanned_paper.pdf
~~~

Supported inputs: text-selectable PDF, TXT and Markdown. Put textbook/reference files directly inside **sources/TOPIC-ID/**. Put actual question papers or carefully sourced PYQ records only inside **sources/TOPIC-ID/pyq/**.

Only files in the **pyq/** subfolder are sent to the PYQ extraction stage; they are kept separate from lesson notes. The PDF reader does not OCR scanned pages. Scanned PDFs may need OCR/manual transcription.

The first HIS-001 source record is **sources/HIS-001/pyq/HIS-001_mpsc_rajyaseva_2022_gs1_q93.md**: a third-party archive lists MPSC Rajyaseva 2022 GS Paper 1, Q93 on Bagor as a Mesolithic site. It is marked as a candidate; the original MPSC paper and official final answer key still need checking.

The web search stage tries to find actual MPSC questions, not model/practice questions. Each candidate must carry its question source URL and exam/year/paper/question number where available. A third-party archive is not treated as proof that the official answer key has been checked.

## Output files

~~~text
output/
└── TOPIC-ID/
    ├── README.md
    ├── detailed_notes.md
    ├── visuals.md
    ├── practice_mcqs.md
    ├── topic_test.md
    ├── flashcards.md
    ├── quick_recall.md
    ├── pyq_candidates.md
    ├── research_sources.json
    └── quality_report.md
~~~

## Accuracy and publishing rules

- AI-generated notes and MCQs are drafts until reviewed.
- Practice MCQs must never be labelled as PYQs.
- A PYQ must have a traceable source. Verify wording against the original question paper and answer against the official final key.
- Check dates, place names, interpretations, PYQ answer keys and explanations against reliable sources.
- Never mark a claim or answer as officially verified without evidence.
- Check copyright/licence before republishing source material. Free access does not automatically grant republication rights.
- **quality_report.md** checks structure and counts only; it does not certify factual accuracy.
