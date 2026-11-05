# Source Material Guide

For a topic, create a folder such as:

```text
sources/
└── HIS-001/
    ├── textbook_notes.pdf
    ├── reference.txt
    └── pyq/
        ├── mpsc_group_b_2022_question_paper.pdf
        └── rajyaseva_2019_gs1_question_paper.pdf
```

Supported source formats: text-selectable PDF, TXT and Markdown.

- Put textbook/reference files directly inside sources/TOPIC-ID/.
- Put actual MPSC question-paper PDFs only inside sources/TOPIC-ID/pyq/.
- The script extracts text from PDFs with pypdf. It does not OCR scanned PDFs.
- PYQ candidates are extracted only from PDFs in the pyq folder and still require human verification against the original paper and official answer key.
- Do not upload copyrighted books or papers unless you have the right to use them. Free access is not the same as permission to republish.
