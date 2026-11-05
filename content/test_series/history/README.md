# MPSC Katta — Ancient Indian History MCQ Test Series

ही test series MPSC Saral Seva / Group B-C प्रकारच्या objective परीक्षांच्या इतिहास सरावासाठी आहे. आत्ता यामध्ये HIS-001 ते HIS-010 हे 10 प्राचीन भारत विषय समाविष्ट आहेत. हा पूर्ण MPSC History syllabus किंवा full GS mock नाही.

## विद्यार्थ्यांसाठी उपलब्ध चाचण्या

| Test ID | घटक | प्रश्न | वेळ |
|---|---|---:|---:|
| HIS-SEC-001 | प्रागैतिहासिक काळ + सिंधू संस्कृती | 50 | 30 मिनिटे |
| HIS-SEC-002 | वैदिक संस्कृती + महाजनपदे + जैन-बौद्ध परंपरा | 50 | 30 मिनिटे |
| HIS-SEC-003 | मौर्य साम्राज्य + अशोक | 50 | 30 मिनिटे |
| HIS-SEC-004 | मौर्योत्तर राजवंश + सातवाहन | 50 | 30 मिनिटे |
| HIS-MOCK-001 | HIS-001 ते HIS-010 प्राचीन भारत मिश्रित मॉक | 100 | 60 मिनिटे |

याशिवाय प्रत्येक topic folder मध्ये स्वतंत्र 50 प्रश्नांची topic test आहे.

## प्रश्नपत्रिका व उत्तरतालिका

प्रत्येक HIS-001 ते HIS-010 फोल्डरमध्ये:
- `practice_mcqs.md` — 50 प्रश्न, पर्याय, उत्तर व स्पष्टीकरणासह विद्यार्थी अभ्यास संच.
- `practice_mcqs.json` — bot / website साठी canonical MCQ records.
- `topic_test.md` — उत्तर न दाखवणारी MCQ प्रश्नपत्रिका.
- `topic_test_answer_key.md` — योग्य उत्तरे व स्पष्टीकरण.
- `topic_test.json` — machine-readable test.
- HIS-009 आणि HIS-010 मध्ये `sources_and_further_reading.md` आहे.

## MPSC Saral Seva / Group B-C default scoring profile

- बरोबर उत्तर: +1.
- चुकीचे उत्तर: −0.25.
- एकापेक्षा जास्त पर्याय mark केले: −0.25.
- A–E पैकी एकही पर्याय नोंदवला नाही: −0.25.
- E (उत्तर द्यायचे नाही) निवडले: 0.

हा अभ्यासासाठीचा default profile आहे. प्रत्येक MPSC भरतीची प्रश्नसंख्या, वेळ आणि गुणपद्धती त्या परीक्षेच्या अद्ययावत अधिकृत जाहिरातीनुसार configure करावी.

## Automation contract

- Test JSON मधील `questions[].question_id` व `source_file` ने मूळ MCQ शोधा.
- प्रश्न सोडवताना A–D पर्याय दाखवा; उत्तर, बरोबर पर्याय व स्पष्टीकरण submission नंतरच दाखवा.
- E हा “not attempted” response आहे; तो प्रश्नाचा पाचवा content option नाही.
- Attempt log मध्ये test_id, question_id, selected_option, response_status, score आणि timestamp नोंदवा.
- Authored questions कधीही PYQ म्हणून दाखवू नका. Verified PYQ साठी मूळ अधिकृत paper व final answer key दोन्ही तपासणे बंधनकारक आहे.

## पुढील विस्तार

उर्वरित प्राचीन भारत, मध्ययुगीन भारत, मराठा इतिहास, आधुनिक भारत आणि महाराष्ट्रातील समाजसुधारक/चळवळी यांसाठीही अशीच 50-MCQ topic banks व sectional tests तयार करायचे आहेत.
