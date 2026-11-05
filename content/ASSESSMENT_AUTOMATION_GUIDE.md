# MPSC Katta — Assessment & Automation Contract (v1.2)

## सध्याची History coverage

या working pack मध्ये HIS-001 ते HIS-010 (प्राचीन भारत) उपलब्ध आहेत. प्रत्येक topic मध्ये 50 authored practice MCQs, 50-question MCQ-only topic test, स्वतंत्र answer key आणि JSON उपलब्ध आहेत. HIS-001 ते HIS-008 साठी विस्तृत notes/flashcards/quick recall/visuals आहेत; HIS-009 व HIS-010 साठी सध्या संक्षिप्त notes व source references आहेत. उर्वरित HIS-011 ते HIS-094 अद्याप या pack मध्ये पूर्ण झालेले नाहीत.

सर्व MCQ हे authored practice आहेत; PYQ नाहीत.

## मुख्य files

प्रत्येक topic:
- `practice_mcqs.md` — विद्यार्थी वाचनासाठी प्रश्न, A–D पर्याय, उत्तर व स्पष्टीकरण.
- `practice_mcqs.json` — canonical question bank.
- `topic_test.md` — उत्तर न दाखवणारी 50 प्रश्नांची test paper.
- `topic_test_answer_key.md` — उत्तरे व स्पष्टीकरण.
- `topic_test.json` — bot/test-engine साठी machine-readable test.
- `pyq.json` / `pyq.md` — अधिकृत PYQ verification registry व स्थिती.

Test series:
- `content/test_series/history/ancient_india_test_series.json`
- `content/test_series/history/README.md`

Shared schema: `content/schemas/assessment_format_v1.json`.

## MCQ fields

प्रत्येक MCQ मध्ये:
- `question_id` — stable ID, उदा. `HIS-009-MCQ-001`
- `question_no`
- `question`
- `options.A`, `options.B`, `options.C`, `options.D`
- `correct_option` — A/B/C/D
- `answer` — योग्य पर्यायाचा पूर्ण मजकूर
- `explanation`
- `source_status: author_created_practice_not_pyq`
- `student_forwardable: true`

Content बदलले तरी stable ID विनाकारण बदलू नका. नवीन प्रश्न जोडताना नवीन क्रमांक व ID द्या; हटवलेला ID पुन्हा वापरू नका.

## MPSC test delivery

- Test JSON मधील `questions[].question_id` व `source_file` वापरून canonical MCQ शोधा.
- प्रश्न देताना प्रश्न व A–D पर्याय दाखवा. योग्य उत्तर, उत्तराचा मजकूर व स्पष्टीकरण submit केल्यानंतरच दाखवा.
- E हा “उत्तर द्यायचे नाही” असा OMR response आहे; तो पाचवा factual option नाही.
- सध्याचा Saral Seva / Group B-C practice preset: बरोबर +1; चुकीचे किंवा multiple mark −0.25; A–E पैकी काहीच mark न केल्यास −0.25; E निवडल्यास 0.
- Topic test: 50 प्रश्न / 50 गुण / 30 मिनिटे. 100 प्रश्नांचा Ancient History mixed mock: 100 गुण / 60 मिनिटे.
- हा practice preset आहे. विशिष्ट MPSC भरतीसाठी marks, time limit किंवा OMR rule बदलण्यापूर्वी त्या भरतीची नवीनतम अधिकृत जाहिरात तपासा.
- Attempt log मध्ये `test_id`, `question_id`, `selected_option`, `response_status`, `score`, `timestamp` नोंदवा. एका test attempt मध्ये duplicate question पाठवू नका.

## PYQ forwarding — अत्यावश्यक

फक्त `pyq.json` मधील `verified_items` मधून प्रश्न पाठवा आणि प्रत्येक item साठी सर्व अटी तपासा:
1. `verification_status === "verified"`
2. `official_paper_verified === true`
3. `official_final_answer_key_verified === true`
4. `student_forwardable === true`

`unverified_candidates` आणि `question_patterns` कधीही PYQ म्हणून पाठवू नका. सध्या या History pack मध्ये अधिकृतरीत्या verified PYQ नोंदवलेले नाहीत. HIS-001 मधील दोन third-party transcription candidates अप्रमाणित आहेत आणि forwarding बंद आहे.

## Test series contents

- HIS-SEC-001: प्रागैतिहासिक काळ + सिंधू संस्कृती — 50 प्रश्न.
- HIS-SEC-002: वैदिक संस्कृती + महाजनपदे + जैन-बौद्ध परंपरा — 50 प्रश्न.
- HIS-SEC-003: मौर्य साम्राज्य + अशोक — 50 प्रश्न.
- HIS-SEC-004: मौर्योत्तर राजवंश + सातवाहन — 50 प्रश्न.
- HIS-MOCK-001: HIS-001 ते HIS-010 मधील प्रत्येकी 10 प्रश्न — 100 प्रश्न.

ही Ancient History-only series आहे; full History किंवा full GS paper नाही.
