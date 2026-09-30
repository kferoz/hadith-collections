# CLAUDE.md — Hadith Reference App

Project memory for Claude Code. Read this before doing anything. It encodes
decisions and bugs that cost real debugging time; ignoring it means repeating
them.

---

## What this project is

A browsable, filterable reference app over the classical Sunni hadith corpus.
Hadith are indexed by **practical life topics** (Parents, Marriage, Charity,
Hellfire, Trade…) rather than the compilers' original chapter arrangements, so
a user can ask "what did the Prophet ﷺ say about neighbours" and get an answer
across collections.

**This is a religious text project. Accuracy outranks completeness, and
completeness outranks polish.** A missing hadith is a gap; a fabricated or
misattributed one is a serious harm. When unsure, omit and say so.

---

## Non-negotiable rules

1. **NEVER write hadith text from memory.** Not one. At any scale, recalled
   hadith produce invented reference numbers and garbled wording that *look*
   authoritative. All text comes from a dataset, always. If a dataset lacks
   something, the answer is "not available", not a reconstruction.
2. **Marfūʿ only** — what the Prophet ﷺ said, did, ordered, or approved.
   Companion opinions (mawqūf), Successor statements (maqṭūʿ), and compiler
   chapter commentary get filtered out.
3. **Never present ungraded material as authentic.** Only Bukhārī and Muslim are
   sound throughout. Everything else needs an explicit grade or an explicit
   "UNGRADED" marker. Ungraded ≠ authentic.
4. **Never silently drop data.** Deduplication merges and records the merge
   (`also_at`, `merged_dups`); it does not delete.
5. **State limits plainly in the UI**, not just in code comments. Users act on
   this material.

---

## Current state

**Tier 1 — English, graded (20,603 unique)**

| Collection | Compiler | d.AH | Unique | Grades |
|---|---|---|---|---|
| Ṣaḥīḥ al-Bukhārī | al-Bukhārī | 256 | 4,364 | 4,347 ṣaḥīḥ |
| Ṣaḥīḥ Muslim | Muslim | 261 | 3,794 | 3,752 ṣaḥīḥ |
| Sunan Abī Dāwūd | Abū Dāwūd | 275 | 3,017 | mixed |
| Sunan Ibn Mājah | Ibn Mājah | 273 | 2,867 | mixed, 21 mawḍūʿ |
| Sunan an-Nasāʾī | an-Nasāʾī | 303 | 2,795 | mixed |
| Jāmiʿ at-Tirmidhī | at-Tirmidhī | 279 | 2,475 | mixed |
| al-Muwaṭṭaʾ | Mālik | 179 | 664 | UNGRADED |
| Musnad Aḥmad (partial) | Aḥmad | 241 | 627 | UNGRADED |

**Tier 2 — Arabic only, ungraded (92,855 unique)**
15 collections from OpenITI: Ṭabarānī (Kabīr 17,150 / Awsaṭ 8,855 / Ṣaghīr
1,156), Bayhaqī (Sunan Kubrā 14,832 / Shuʿab 6,408), Bazzār 8,965, Ibn Abī
Shayba 7,462, Ḥākim 6,636, Abū Yaʿlā 6,341, ʿAbd ar-Razzāq 4,197, Dāraquṭnī
3,465, Ibn Khuzayma 2,876, Ṭayālisī 2,681, Shāfiʿī 1,202, Saʿīd b. Manṣūr 629.

Plus full Musnad Aḥmad (19,091) and Dārimī (1,982) in Arabic from a separate
source.

**Tier 1 and Tier 2 must never be blended into one undifferentiated list.**

---

## Data sources

| Source | Reach | Gives |
|---|---|---|
| `AhmedBaset/hadith-json` | GitHub | 9 books, Arabic + English JSON |
| `ShathaTm/LK-Hadith-Corpus` | GitHub | **grades** (`English_Grade`) for the 6 canonical |
| `abdelrahmaan/Hadith-Data-Sets` | GitHub | Arabic 9 books, **full Musnad Aḥmad (26k)** |
| `OpenITI/*AH` (224 repos) | GitHub | everything beyond the Nine, Arabic |
| Dorar.net | **blocked in sandbox** | best grading source, names the scholar |

OpenITI repos are named by author death date rounded up to 25 years:
ʿAbd ar-Razzāq d.211 → `0225AH`, Ibn Abī Shayba d.235 → `0250AH`,
Bazzār d.292 → `0300AH`, Abū Yaʿlā/Ibn Khuzayma → `0325AH`,
Ṭabarānī/Ibn Ḥibbān → `0375AH`, Dāraquṭnī → `0400AH`, Ḥākim → `0425AH`,
Bayhaqī → `0475AH`.

---

## Bugs already found — do not reintroduce

These each silently produced plausible-looking wrong output. That is the
dangerous failure mode here: nothing crashes, the numbers just lie.

1. **Narrator vs text field.** Sahih Muslim stores much of the narration in the
   `narrator` field, not `text`. Filtering on `text` alone yielded 2,552 marfūʿ
   (34%) vs Bukhārī's 74%. **Always check `narrator + ' ' + text`.** The gap in
   yield between collections was the only clue.

2. **Arabic diacritics.** Musnad Aḥmad is fully voweled; matching undiacritised
   Prophet-markers returned **zero**. Bukhārī is mixed and lost ~84 silently.
   **Strip `[\u064B-\u0652\u0640\u0670]` before any Arabic comparison.**

3. **Edition choice by file size.** For al-Muʿjam al-Kabīr, the *largest* file
   (14.19 MB) parsed to **4** hadith — wrong markup dialect. A smaller file
   (12.96 MB) gave **21,586**. **Score candidate editions by parsed entry
   count, never by bytes.**

4. **Generic work-name matching.** `--work Musnad` in `0250AH` returned *Musnad
   Aḥmad* (26k) labelled as Ibn Rāhwayh (~4k expected). **Pin the author:**
   `IbnAbiShayba.Musannaf`. Transliterations are non-obvious —
   `CabdRazzaqSancani`, `AbuYaclaMawsili`, `HakimNaysaburi` (`c` = ʿayn).

5. **Blessing formula poisoning topics.** *ṣallā llāhu ʿalayhi wa-sallam*
   appears in nearly every isnād and matched the "prayer" keyword, inflating
   Prayer to 13,307 hits. **Strip the blessing before topic tokenisation.**
   After the fix: 1,289.

6. **English-based cross-collection matching.** Bukhārī and Muslim use different
   translators, so matching agreed-upon (*muttafaq ʿalayh*) hadith on English
   found 64. **Matching on Arabic found 1,231** — a 20× difference. Cross-source
   text matching must use Arabic.

7. **Over-eager topic assignment.** First pass gave 5.7 topics/hadith, with
   "Animals" catching 1,748 because a camel appeared in passing. Weight keyword
   density and use the compiler's own book title as a prior. Target ~1.5–2.0.

---

## Established methods

**Marfūʿ filter:** require a Prophet-marker in the Arabic (diacritic-stripped)
AND a speech/action verb attached to the Prophet in `narrator + text` AND, for
OpenITI, an isnād cue (`ḥaddathanā`, `akhbaranā`, `ʿan`…) to exclude prefaces
and indices.

**Deduplication:** fuzzy token-overlap on content words with isnād boilerplate
removed. Merge when `jaccard ≥ 0.48` OR (`coverage ≥ 0.72` AND `jaccard ≥ 0.35`).
Tighter thresholds were tested and rejected — over-merging deletes real content,
and showing a near-duplicate is the cheaper error.

**Grade join:** LK Corpus and the main dataset number hadith incompatibly, so
join by **wording similarity**, not reference number. Achieved 98.6–99.9%.
*Self-validation:* Bukhārī and Muslim must come back ~100% ṣaḥīḥ. If weak grades
leak into those two, the matching is broken — this check catches it immediately.

**Reference numbers** follow the source dataset and **differ from sunnah.com**
(7,277 vs 7,563 for Bukhārī — the two count combined narrations differently).
Never present them as sunnah.com references. Each record carries a
`verify_phrase` for a wording-based sunnah.com search, which is
numbering-independent.

---

## Known gaps

- **Ṣaḥīḥ Ibn Ḥibbān** — absent from OpenITI (present as author, but only
  *Majrūḥīn*, *Thiqāt*, *Mashāhīr*). The surviving recension is Ibn Balbān's
  rearrangement, catalogued separately.
- **Musnad Isḥāq ibn Rāhwayh, Musnad al-Ḥumaydī** — not in OpenITI.
- **Sunan ad-Dārimī** — Arabic only, no English anywhere found.
- **All 92,855 Tier 2 records are ungraded.** Run `dorar_fetch.py --grade-file`
  on an unrestricted network to fix this. It is the single highest-value
  remaining task.
- **Criterion "no early scholar raised concern"** is not encodable in any
  dataset found. It requires reading the commentarial tradition. Do not pretend
  a filter satisfies it.

---

## App conventions

`app/index.html` is a ~24 KB shell that **fetches `app/hadith.json` at runtime**.
It is deliberately not one self-contained file: inlining 13.7 MB of data made the
browser parse the whole payload before painting anything. Regenerate the data with
`python3 scripts/build_app_data.py`, which rebuilds it from `data/english-graded/`
so the app can never drift from the committed sources, and which re-runs the
Bukhārī/Muslim grade self-check on every build.

Because browsers refuse `fetch()` over `file://`, opening `app/index.html` straight
from disk shows a load error that explains the fix. Serve the repo
(`python3 -m http.server 8000`, then `/app/`), or build the single-file version
with `--standalone` — that one is gitignored, since it duplicates data already
committed.

No localStorage. The only external request is the Google Fonts stylesheet for
Literata and Outfit; both have full fallback stacks, so the page degrades cleanly
offline.

Topic rail grouped into 8 thematic groups; collection dropdown; grade filter
(All / Ṣaḥīḥ / +Ḥasan / Weak only). Paginate at 25 — rendering 20k cards at once
will hang the browser.

**Readability is a requirement, not a preference.** The audience spans all ages.
Hadith body text sits at 19px in Literata (a face designed for long-form reading)
at 1.78 line-height on a ~68-character measure, and a text-size control scales the
whole page from 0.92× to 1.42× through the `--fs` token — so every font-size is
written `calc(Npx * var(--fs))`. Tap targets are ≥42px. Do not shrink this scale.

Gradients (lapis → jade, with gold leaf) carry the visual identity: header bar,
section rules, the selected topic, and each card's left edge, where the gradient
also **encodes the grade** — jade for ṣaḥīḥ, gold for ḥasan or weak, grey for
ungraded. **No gradient ever sits behind body text**; reading surfaces stay solid
paper, or legibility is lost. Serif for hadith text, sans for UI chrome. Grade
badges are colour-coded and always visible; a user must never see a narration
without knowing its grade status.

---

## Articles (`articles/`)

Narrative long-form built on the dataset, read in `articles/index.html`.
**`docs/ARTICLE_GUIDELINES.md` is the governing document** — read it before
writing or editing any article.

The one thing to know before touching this: **article sources never contain
hadith text.** They contain references — `{"ref": ["bukhari", 4457]}`, with
optional `from`/`to` markers to excerpt — and `scripts/build_articles.py`
resolves them against `app/hadith.json`, writing text, book and grade from the
dataset. A reference that does not resolve, or resolves to anything not graded
Ṣaḥīḥ, fails the build.

This exists because of a real failure, not a hypothetical one: on the first
draft of the sīra series, **six of eight reference numbers were written from
recall and every one pointed at an unrelated narration.** The prose read fine;
the citations were wrong. Rule 1 caught it. The reference-only design now makes
that error impossible rather than merely detectable. Write prose freely; never
write a hadith.

Articles are also expected to **say what the authentic record does not contain**.
Most of the familiar biography comes from *sīra* literature that never passed
hadith criticism, so article one omits the wet-nurse, the monk, and the head
bowed to the saddle — and says why rather than leaving unexplained gaps.

---

## Tone when reporting results

Report what was actually built and what failed. If a collection came back with
an implausible count, say so and investigate rather than shipping the number.
Several findings in this project came from noticing a figure that looked wrong —
34% vs 74% yield, 4 hadith from a 14 MB file, 64 agreed-upon out of 8,000.
Treat implausible output as a bug until proven otherwise.
