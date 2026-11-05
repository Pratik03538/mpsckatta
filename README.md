# MPSC Katta

A Marathi common classroom content workspace for MPSC preparation. The first milestone is one subject and one topic: History — HIS-001, प्रागैतिहासिक काळ.

## What the one-file generator creates

The single Python script, main.py, asks for one Topic ID, subject and topic name, then creates:

- Detailed Marathi notes (target 2,000–2,800 words)
- Visual revision pack (Mermaid flowchart/mind map, timeline and comparison table)
- 30 practice MCQs with answers and explanations
- 10-question topic test
- 10 flashcards
- 5 quick-recall questions
- PYQ candidates extracted only from source question-paper PDFs supplied in sources/TOPIC-ID/pyq/
- Research-source metadata and a quality report

All generated files are saved under output/TOPIC-ID/.

## Important: API and subscription

This generator uses the Gemini Developer API through Google AI Studio. A ChatGPT Go subscription does not provide OpenAI API credits or an API key. Gemini has a limited free tier for eligible models and accounts; quotas can change. Google states that free-tier content may be used to improve its products. Do not submit private or confidential information.

Default model: gemini-3.8-flash. You can override it with the --model argument or GEMINI_MODEL in your .env file.

Google AI Studio API key page: https://aistudio.google.com/apikey

## PyCharm setup

1. Clone this repository or open your existing local clone.
2. Create/activate your virtual environment.
3. In the PyCharm Terminal run:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy .env.example to .env.
5. Open .env and set GEMINI_API_KEY to your own Google AI Studio key.
6. Never commit .env or paste the API key in chat.

## Run one topic

Interactive:

```powershell
python main.py
```

Or provide the fields directly:

```powershell
python main.py --topic-id HIS-001 --subject "इतिहास" --topic "प्रागैतिहासिक काळ"
```

To enable Google Search grounding (uses search-grounding quota):

```powershell
python main.py --topic-id HIS-001 --subject "इतिहास" --topic "प्रागैतिहासिक काळ" --web-research
```

Web grounding is off by default to avoid using search quota without your choice.

## Supplying source material

Create a topic folder:

```text
sources/
└── HIS-001/
    ├── textbook_notes.pdf
    ├── reference.txt
    └── pyq/
        └── mpsc_question_paper.pdf
```

Supported inputs: text-selectable PDF, TXT and Markdown. The PDF reader does not perform OCR. Scanned PDFs may not produce extracted text.

Only PDFs placed inside the pyq subfolder are treated as possible question-paper sources. If no such PDF is provided, the script leaves the PYQ section empty rather than inventing exam questions.

## Output files

```text
output/
└── HIS-001/
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
```

## Accuracy and publication rules

- AI output is a draft, not automatically verified study material.
- Notes should explain concepts, causes, processes and results; they should not be filler or memorization-only bullet lists.
- Check dates, place names, historical interpretations, answer keys and explanations against reliable sources.
- PYQ candidates are never treated as confirmed PYQs until matched to the original paper and official answer key.
- AI-created questions are labelled Practice MCQs, never PYQs.
- Source-page labels are useful for review but are not proof that a PDF is an official paper.
- Check copyright/licence before republishing any source. Free access does not automatically grant republication rights.
- The quality report checks approximate length and item counts only. It does not certify factual accuracy.

## Publishing

Nothing is automatically sent to Telegram. Review the content, verify sources and answers, approve it manually, and only then publish.
