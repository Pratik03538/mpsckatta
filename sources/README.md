# Source Material Guide

For each topic, create a folder such as:

~~~text
sources/
└── HIS-001/
    ├── textbook_notes.pdf
    ├── reference.md
    └── pyq/
        ├── mpsc_question_paper.pdf
        ├── official_answer_key.pdf
        └── verified_question_record.md
~~~

## Reference files

Put textbook/reference files directly inside **sources/TOPIC-ID/**. Supported formats:

- Text-selectable PDF
- TXT
- Markdown

## PYQ files

Put actual MPSC question-paper PDFs, official answer keys and carefully sourced PYQ records only inside **sources/TOPIC-ID/pyq/**.

For a Markdown/TXT record, include:
- Exact question wording and all options
- Exam name and year
- Paper name/number and question number
- Source URL
- Answer source URL, if available
- Whether the original MPSC paper and official final answer key have been checked

The script keeps files inside **pyq/** separate from lesson notes. It extracts text from PDFs with **pypdf**; it does not OCR scanned PDF pages.

Google Search grounding is enabled by default to discover actual past questions and source URLs. Use **--no-web-research** to disable it. Search results may identify third-party archives, but those must not be described as officially verified until cross-checked with the original MPSC paper and final answer key.

Do not store AI mock questions or practice sets in the PYQ folder. Do not invent question wording, exam details, question numbers, source URLs or answers.

Check copyright/licence before republishing any source. Free access is not the same as permission to republish.
