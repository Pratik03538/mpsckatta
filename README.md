# MPSC Katta

A focused workspace for MPSC Saral Seva study content. The first milestone is one subject and one topic only:

- Subject: History
- Topic ID: HIS-001
- Topic: प्रागैतिहासिक काळ
- Study flow: 25 min detailed notes + 5 min visual revision + 10 min PYQ + 10 min MCQ + 5 min quick recall

## Current approach (no API cost)

This starter project does **not** call the OpenAI or Gemini API. A ChatGPT Go subscription does not include API credits. Use ChatGPT in the browser to draft the Marathi notes from the prompt in `prompts/HIS-001_prompt.md`, then save the approved draft locally as:

`output/HIS-001/detailed_notes.md`

The project includes a small local helper to create the topic folders and check the notes file's structure and approximate length. These checks do not verify historical facts.

## PyCharm setup

1. Install Git for Windows and PyCharm.
2. In PyCharm, choose **Get from VCS**.
3. Repository URL: `https://github.com/Pratik03538/mpsckatta.git`
4. Choose a local directory and click **Clone**.
5. In the branch selector, check out `feature/his-001-topic-setup`.
6. Open the PyCharm Terminal and run:

   ```bash
   python main.py
   ```

If PyCharm cloned the repository before the working branch was created, fetch branches and then check out `feature/his-001-topic-setup`.

## First topic workflow

1. Read `prompts/HIS-001_prompt.md`.
2. Use the prompt in ChatGPT to prepare detailed, student-friendly Marathi notes.
3. Check dates, site names, archaeological interpretations and references against reliable source material.
4. Save the draft to `output/HIS-001/detailed_notes.md`.
5. Run `python main.py --check` to review approximate word count and required sections.
6. Do not publish until a human review is complete.

## Important accuracy rules

- AI-generated content is a draft, not automatically verified.
- Do not invent PYQs, answer keys, references, authors, page numbers or dates.
- Clearly distinguish established archaeological evidence from scholarly interpretations.
- Chronology can vary by region; do not present one date range as universal for the whole subcontinent.
- Free access to a book or website does not automatically grant permission to republish it. Respect source licences and copyright.

## Project scope

Only HIS-001 is in scope for this initial branch. Do not generate the remaining History topics or other subjects until this topic's quality is reviewed and accepted.
