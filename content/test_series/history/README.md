# MPSC Katta — Ancient Indian History MCQ Test Series

ही test series MPSC Rajyaseva Prelims च्या GS-I इतिहास सरावासाठी तयार केली आहे. सध्या यात repository मधील HIS-001 ते HIS-008 (प्राचीन भारत) हेच विषय समाविष्ट आहेत. हा पूर्ण GS Paper-I mock नाही; इतर विषयांची प्रश्नबँक जोडल्यावर स्वतंत्र full-GS mock तयार करावा.

## उपलब्ध चाचण्या

| Test ID | विभाग | प्रश्न | वेळ |
|---|---|---:|---:|
| HIS-SEC-001 | प्रागैतिहासिक काळ + सिंधू संस्कृती | 50 | 60 मिनिटे |
| HIS-SEC-002 | वैदिक ते श्रमण परंपरा | 50 | 60 मिनिटे |
| HIS-SEC-003 | मौर्य साम्राज्य + अशोक | 50 | 60 मिनिटे |
| HIS-MOCK-001 | प्राचीन भारत — मिश्रित इतिहास | 100 | 120 मिनिटे |

## Topic tests

प्रत्येक HIS-001 ते HIS-008 फोल्डरमध्ये:
- `topic_test.md` — उत्तर न दाखवणारी 50 प्रश्नांची MCQ प्रश्नपत्रिका.
- `topic_test_answer_key.md` — बरोबर पर्याय व स्पष्टीकरण.
- `topic_test.json` — bot / website / test engine साठी पूर्ण machine-readable test.

## MPSC OMR व scoring

1 मार्च 2026 पासून लागू objective-exam सूचनांनुसार प्रत्येक प्रश्नासाठी A–D पैकी उत्तर किंवा E (प्रश्न attempt न करण्यासाठी) नोंदवायचा आहे. 2 गुणांच्या Rajyaseva GS-I practice question साठी:
- बरोबर उत्तर: +2
- चुकीचे उत्तर: −0.50
- अनेक पर्याय mark करणे: −0.50
- A–E पैकी एकही पर्याय mark न करणे: −0.50
- E (not attempted) निवडणे: 0

MPSC च्या प्रत्यक्ष OMR सूचनांनुसारच उत्तर नोंदवा. दुसऱ्या MPSC भरती/परीक्षेसाठी प्रश्नांचे गुण वेगळे असल्यास त्या परीक्षेच्या नवीन जाहिरातीतील marks-per-question नुसार penalty पुन्हा मोजावी.

## Automation contract

- Test JSON मधील `questions[].question_id` वापरून संबंधित topic च्या `practice_mcqs.json` मधील प्रश्न शोधा.
- Test सुरू असताना फक्त प्रश्न व A–D पर्याय दाखवा. योग्य उत्तर, answer आणि explanation submission/प्रश्न पूर्ण झाल्यानंतरच दाखवा.
- E हा content answer नसून "not attempted" response आहे; तो A–D options मध्ये मिसळू नका.
- प्रत्येक attempt मध्ये test_id, question_id, selected_option, response_status, score, timestamp नोंदवा.
- एकाच question_id ला वेगवेगळ्या tests मध्ये परवानगी आहे; पण त्याच attempt मध्ये duplicate question पाठवू नका.
- सर्व नवीन authored MCQs ला `author_created_practice_not_pyq` असेच label ठेवा. अधिकृत paper + final answer key verified नसलेला प्रश्न PYQ म्हणून पाठवू नका.

## मर्यादा

हे tests विद्यमान 8 विषयांच्या सराव प्रश्नांवर आधारित आहेत. PYQ नव्हेत आणि पूर्ण History syllabus कव्हर झाल्याचा दावा नाही. पुढील expansion मध्ये मध्ययुगीन भारत, मराठा इतिहास, आधुनिक भारत, महाराष्ट्राचा सामाजिक-सुधारक व स्वातंत्र्यलढा इतिहास जोडून नंतर पूर्ण History grand test बनवावा.
