# Prompt Playbook — Hadith App in Claude Code

> **Tip:** every prompt below is in a fenced code block, so GitHub, VS Code, and most
> markdown viewers give you a one-click copy button in the top-right corner of the block.
> For copy buttons everywhere, open `PROMPT_PLAYBOOK.html` in a browser instead.

Copy-paste prompts, in order. Each stage ends with a verifiable checkpoint, so
you catch a wrong turn before it compounds through the pipeline.

**Setup first:**
```bash
mkdir hadith-app && cd hadith-app
# put CLAUDE.md in this folder — Claude Code reads it automatically every session
claude
```

`CLAUDE.md` carries the constraints and the seven known bugs. Without it you
will rediscover them. With it, paste the prompts below as-is.

---

## Stage 0 — Ground rules

```text
Read CLAUDE.md before doing anything else. Confirm you understand the four
non-negotiable rules and the seven known bugs, then tell me in one paragraph
what this project is and what the single most dangerous failure mode is.

Do not write any code yet.
```

*Checkpoint:* it should name **hadith invented from memory** as the top risk.
If it doesn't, re-read CLAUDE.md together before continuing.

---

## Stage 1 — Acquire source data

```text
Download the hadith source datasets. Do not write hadith text from memory at
any point — everything comes from these files.

1. `AhmedBaset/hadith-json` — the nine books with Arabic and English, from
   `db/by_book/the_9_books/*.json`
2. `ShathaTm/LK-Hadith-Corpus` — authenticity grades, 335 CSVs across six books
3. `abdelrahmaan/Hadith-Data-Sets` — Arabic, including the complete Musnad
   Ahmad (~26k rows, vs the ~1.4k fragment in source 1)

Use codeload.github.com zip URLs rather than the GitHub API — the API
rate-limits fast and will stall you.

For each file report: total entries, English coverage %, Arabic coverage %,
and number of chapters. Flag anything where a count is far off the published
figure for that collection.
```

*Checkpoint:* Bukhārī ≈ 7,277 entries / 97 chapters. Musnad Aḥmad in source 1
is ~1,374 — that is a **5% fragment**, and Claude should flag it.

---

## Stage 2 — Build the filter pipeline

```text
Write `build.py`: a pipeline that takes one collection JSON and produces
deduplicated, topic-tagged, Prophet-attributed narrations.

**Marfū' filter.** Keep only narrations of what the Prophet ﷺ said, did,
ordered, or approved. Drop Companion opinions and compiler commentary.
Requirements: check `narrator + ' ' + text`, never `text` alone (Sahih Muslim
stores narration content in the narrator field — filtering on text alone
halves the yield). Strip Arabic diacritics `[\u064B-\u0652\u0640\u0670]`
before matching Prophet-markers (Musnad Ahmad is fully voweled and returns
zero otherwise).

**Deduplicate.** The same hadith recurs via different chains with slightly
different wording, so exact matching catches almost nothing. Use fuzzy token
overlap on content words with isnād boilerplate stripped: merge when
`jaccard >= 0.48` or (`coverage >= 0.72` and `jaccard >= 0.35`). Record merged
references in an `also` field — never delete them.

**Topics.** Assign from a scheme of ~65 practical life topics across 8 groups
(worship, family, character, sins, wealth/law, hereafter, daily life,
prophets). Weight keyword density and use the compiler's own book title as a
prior. Target 1.5–2.0 topics per hadith.

Run it on Bukhārī and Muslim and report the funnel: raw → marfū' → deduped,
plus topic distribution.
```

*Checkpoint:* Bukhārī ≈ 4,364 unique, Muslim ≈ 3,794. Topic average 1.5–2.0.
**If any single topic holds more than ~15% of a collection, the keywords are
too loose** — say so and have it retune.

---

## Stage 3 — Attach grades

```text
Join authenticity grades from the LK corpus onto the filtered data.

The two sources number hadith incompatibly, so **join by wording similarity,
not reference number**. Normalise grades into: Sahih, Hasan, Hasan Sahih,
Da'if, Mawdu', Ungraded.

Report match rate and grade distribution per collection.

**This join self-validates: Bukhārī and Muslim must come back ~100% ṣaḥīḥ.**
If weak grades appear in those two, the matching is broken — stop and fix it
before touching the other collections.
```

*Checkpoint:* match rate >98% everywhere. Bukhārī/Muslim ~100% ṣaḥīḥ. Ibn Mājah
should surface ~21 fabricated (mawḍūʿ) narrations — those are exactly what the
grading exists to catch.

---

## Stage 4 — Build the app

```text
Build a single self-contained HTML file. Data inlined as a JS const, no build
step, no external requests, no localStorage (unsupported in this context).

- Topic rail, grouped into the 8 thematic groups, with live counts
- Collection dropdown
- Grade filter: All / Ṣaḥīḥ / +Ḥasan / Weak only
- Full-text search across text, narrator, book, topics
- Paginate at 25 — rendering 20k cards at once hangs the browser
- Each card: narrator, hadith text, collection + book + number, colour-coded
  grade badge, topic tags (clickable), and a sunnah.com verify link built from
  a distinctive phrase

**Reference numbers differ from sunnah.com's** (7,277 vs 7,563 for Bukhārī —
the two count combined narrations differently). Never label them as
sunnah.com references; that is what the wording-based verify link is for.

An intro panel must state plainly: topics are keyword-assigned and are a
browsing aid not a scholarly classification; grades are one scholar's opinion
and others differ; ungraded collections are unverified, not authentic.

Serif for hadith body, sans for UI chrome. A user must never see a narration
without its grade status visible.
```

*Checkpoint:* open it. Switch to Ibn Mājah + "Weak only" — you should get
several hundred. Switch to Bukhārī + "Weak only" — you should get **zero**.

---

## Stage 5 — Extend to the wider corpus (Arabic)

```text
Extend beyond the Nine Books using OpenITI — 224 GitHub repos of classical
Arabic texts, named by author death date in 25-year buckets (Ṭabarānī d.360 →
`0375AH`, Bayhaqī d.458 → `0475AH`, Ibn Abī Shayba d.235 → `0250AH`).

Write `openiti_hadith.py` with `--list`, `--extract`, and `--batch` modes.
Pure stdlib, no pip dependencies.

Format notes: `#META#Header#End#` closes the header; `# N ` opens hadith N;
`~~` is a line-wrap marker; strip `PageV01P052` and `ms0002` milestones.
Some editions use `###` sections instead — support both dialects.

**Two traps.** (1) Never pick an edition by file size — for al-Muʿjam
al-Kabīr the largest file parses to 4 hadith while a smaller one gives 21,586.
Score candidates by parsed entry count. (2) Pin the author in work names —
a bare `Musnad` fragment in `0250AH` returns *Musnad Aḥmad* mislabelled as
Ibn Rāhwayh. Transliterations are non-obvious: `CabdRazzaqSancani`,
`AbuYaclaMawsili`, `HakimNaysaburi` (`c` = ʿayn).

For topic tagging, strip the blessing formula *ṣallā llāhu ʿalayhi wa-sallam*
before tokenising — it appears in nearly every isnād and will otherwise
inflate the prayer topic tenfold.

Extract these 15: ʿAbd ar-Razzāq, Ṭayālisī, Shāfiʿī, Ibn Abī Shayba, Saʿīd b.
Manṣūr, Bazzār (filed as `BahrZakhkhar`), Abū Yaʿlā, Ibn Khuzayma, Ṭabarānī
×3, Dāraquṭnī, Ḥākim, Bayhaqī ×2. Mark every output `UNGRADED`.
```

*Checkpoint:* ~92,855 unique. Ṭabarānī Kabīr ≈ 17,150, Bayhaqī Sunan Kubrā
≈ 14,832. **Any collection returning an implausible count is a bug, not a
finding** — al-Bazzār coming back as 142 when ~9,000 was expected is how the
author-pinning bug surfaced.

---

## Stage 6 — Merge tiers

```text
Add the Arabic collections to the app as a **separate tier**. They must never
blend into the same undifferentiated list as the English graded material —
one is verified and readable, the other is neither.

Add a tier switch (English graded / Arabic ungraded / both), RTL rendering for
Arabic cards, and a persistent visual marker on every ungraded card.

Keep the grade filter meaningful: selecting "Ṣaḥīḥ only" must exclude all
ungraded material rather than silently treating it as sound.
```

---

## Reusable prompts

**Grading the Arabic tier** (run outside a restricted network):
```text
Write a script that attaches Dorar.net grades to my ungraded Arabic CSVs by
text matching, capturing the grade AND the scholar who gave it. Cache results,
back off on HTTP 429, and rate-limit to 1 req/sec — Dorar is a free scholarly
service. Support resuming via `--start`/`--limit`.
```

**When a count looks wrong:**
```text
Collection X returned N narrations but the published figure is ~M. Do not
proceed. Diagnose whether this is a parsing failure, an edition problem, a
wrong-author match, or a genuine property of the filter, and show me the
evidence before changing anything.
```

**Adding topics:**
```text
Topic "X" has only N narrations, which suggests the keywords are too narrow
rather than the material being absent. Show me the current pattern, propose a
wider one, and report the before/after counts.
```

**Before shipping:**
```text
Audit the app against CLAUDE.md. For each of the four non-negotiable rules and
seven known bugs, show me the specific code that enforces or avoids it. List
anything unenforced.
```

---

## Things to push back on

If Claude Code offers any of these, decline:

- *"I'll add well-known hadith from memory to fill this topic"* — **no.** This
  is the failure mode the whole project is built to avoid.
- *"Tighter deduplication gets closer to the scholarly ~2,600 figure"* —
  over-merging deletes distinct narrations. A visible near-duplicate is the
  cheaper error.
- *"I'll mark ungraded collections as authentic since they're respected"* —
  ungraded means unverified. Ṭabarānī and Bayhaqī contain weak material by
  design.
- *"The reference numbers match sunnah.com"* — they don't, and spot-checking
  two or three that happen to align is not verification.
