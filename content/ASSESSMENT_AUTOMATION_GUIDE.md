# MPSC Katta — Student Content & Automation Contract (v1.0)

## विद्यार्थी थेट पाठवण्यासाठी

प्रत्येक History topic मध्ये पुढील फाइल्स उपलब्ध आहेत:

- `detailed_notes.md` — मराठीत विद्यार्थी-केंद्रित, स्वतंत्रपणे वाचता येणारा धडा.
- `practice_mcqs.md` — 50 सराव प्रश्न; प्रत्येक प्रश्नाखाली A–D पर्याय, योग्य पर्याय, बरोबर उत्तर आणि स्पष्टीकरण.
- `pyq.md` — अधिकृतरीत्या पडताळलेले PYQ उपलब्ध आहेत का याची स्पष्ट नोंद; PYQ नसल्यास अभ्यासासाठीचे प्रश्नप्रकार स्वतंत्रपणे दिलेले.
- `quick_recall.md`, `flashcards.md`, `visuals.md`, `topic_test.md` — पुनरावृत्ती व स्वमूल्यांकनासाठी.

ही Markdown फाइल्स वाचनीय आणि थेट विद्यार्थी-वितरणासाठी आहेत. MCQ/PYQ automation साठी JSON फाइल्स वापराव्यात.

## मशीन-वाचनीय फाइल्स

प्रत्येक topic साठी:

- `practice_mcqs.json` — canonical MCQ dataset.
- `pyq.json` — verified PYQ registry, unverified candidates आणि non-PYQ question patterns.

सर्व JSON फाइल्स `content/schemas/assessment_format_v1.json` या schema शी सुसंगत ठेवाव्यात.

## MCQ field contract

प्रत्येक item मध्ये हे स्थिर fields आहेत:

| Field | अर्थ |
|---|---|
| `question_id` | स्थिर ID, उदा. `HIS-003-MCQ-012` |
| `question_no` | topic मधील क्रमांक |
| `question` | प्रश्नाचा मजकूर |
| `options.A` … `options.D` | चार पर्याय |
| `correct_option` | योग्य पर्यायाचे अक्षर A/B/C/D |
| `answer` | योग्य पर्यायाचा पूर्ण मजकूर |
| `explanation` | विद्यार्थ्यांसाठी स्पष्टीकरण |
| `source_status` | `author_created_practice_not_pyq` |
| `student_forwardable` | सराव MCQ विद्यार्थी-वितरणासाठी योग्य असल्यास true |

MCQ हे नव्याने तयार केलेले सराव प्रश्न आहेत. त्यांना PYQ म्हणून दाखवू नये.

## PYQ forwarding rule — अत्यावश्यक

Automation ने **फक्त** `pyq.json` मधील `verified_items` मधील records पाठवावेत, आणि प्रत्येक record साठी हे सर्व तपासावे:

1. `verification_status === "verified"`
2. `official_paper_verified === true`
3. `official_final_answer_key_verified === true`
4. `student_forwardable === true`

`unverified_candidates` कधीही विद्यार्थी किंवा Telegram group ला पाठवू नयेत. `question_patterns` हे अभ्यासासाठीचे नव्याने मांडलेले प्रश्नप्रकार आहेत; ते PYQ नाहीत.

सध्या HIS-001 मध्ये तृतीय-पक्षीय archive मधील 2 candidates आहेत; मूळ प्रश्नपत्रिका आणि अधिकृत अंतिम उत्तरतालिका पडताळली नसल्याने ते `unverified_candidates` मध्येच राहतात. सर्व topics मध्ये सध्या `verified_items` रिकामे आहेत.

## Suggested bot flow

1. Topic folder निवडा.
2. MCQ पाठवायचे असल्यास `practice_mcqs.json` मधील `items` क्रमाने वाचा.
3. प्रत्येक message मध्ये `question_no`, `question`, `options`, `correct_option`, `answer`, `explanation` वापरा.
4. PYQ पाठवताना वरचा four-condition verification filter लागू करा.
5. पाठवलेला `question_id` log करा, म्हणजे duplicate messages टाळता येतील.

## स्थिर naming convention

- Topic: `HIS-001` … `HIS-008`
- MCQ: `HIS-001-MCQ-001`
- PYQ: `HIS-001-PYQ-001`
- Pattern: `HIS-001-PATTERN-001`

Question number बदलू नका; content बदलला तरी stable ID कायम ठेवा. प्रश्न हटवला तर ID पुन्हा वापरू नका.


## MPSC MCQ test-series contract (v1.1)

- Each `content/history/HIS-xxx/topic_test.md` is now a 50-question MCQ-only paper; the matching `topic_test_answer_key.md` contains answers and explanations; `topic_test.json` is the bot/test-engine source.
- The Ancient India test-series index is `content/test_series/history/ancient_india_test_series.json`; read `content/test_series/history/README.md` before building the bot flow.
- Resolve mixed-test references using `questions[].question_id` and `source_file`; do not copy a different question into a reference slot.
- During an attempt, display only the question and A–D answer choices. Reveal the correct choice, answer and explanation only after submission.
- MPSC objective OMR has a fifth response option E for “not attempted”. E is a response status, not a fifth factual answer choice. For the current MPSC Saral Seva / Group B-C practice profile (1 mark/question), correct = +1; wrong/multiple/fully blank A–E = −0.25; E = 0. The updated marking/OMR instruction is effective 2026-03-01. For any other exam profile, take marks-per-question and penalty from that exam's latest MPSC notification.
- Keep all authored MCQs labelled `author_created_practice_not_pyq`. The mixed tests are not official papers and must not be represented as PYQs or full GS papers.


### Current default exam profile

`MPSC_GROUP_BC_PRACTICE`: 1 mark per question, 25% deduction for incorrect/multiple/fully blank A-E responses, E means explicitly not attempted for 0 marks. Topic tests use 50 questions / 50 marks / 30 minutes. The History-only 100-question mixed mock uses 100 marks / 60 minutes. This is a practice preset; configure another MPSC recruitment exam from its current official notification rather than assuming all MPSC exams have identical timing and scoring.
