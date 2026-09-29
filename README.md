# Hadith Collections

A machine-readable index of the classical Sunni hadith corpus — **134,531 distinct
Prophet-attributed narrations** across 24 collections, tagged by practical life
topic (Parents, Marriage, Charity, Trade, Hellfire…) rather than by the
compilers' original chapter arrangements.

---

## ⚠️ Read this before using the data

**The three tiers are not equivalent, and must not be treated as one dataset.**

| Tier | Records | Language | Authenticity |
|---|---|---|---|
| 1 — Canonical, graded | 20,603 | English | Graded per narration |
| 2a — Aḥmad & Dārimī | 21,073 | Arabic | **UNGRADED** |
| 2b — Wider corpus (OpenITI) | 92,855 | Arabic | **UNGRADED** |

- **Ungraded means unverified, not authentic.** Only Ṣaḥīḥ al-Bukhārī and Ṣaḥīḥ
  Muslim are sound throughout — that is what *Ṣaḥīḥ* in their titles claims.
  al-Muʿjam al-Kabīr, as-Sunan al-Kubrā, the Muṣannafāt and the Masānīd contain
  weak (*ḍaʿīf*) material **by design**; their compilers gathered widely and left
  grading to others.
- **Grades in Tier 1 are al-Albānī's**, as recorded in the LK corpus. Other
  scholars grade differently. This is one respected opinion, not a consensus.
- **Topic tags are keyword-assigned.** They are a browsing aid, not a scholarly
  classification. A narration may sit under a topic it only touches in passing.
- **Reference numbers follow the source datasets and differ from sunnah.com's**
  (7,277 vs 7,563 for Bukhārī — the two count combined narrations differently).
  Never cite them as sunnah.com references. Each record carries a
  `verify_phrase` for a wording-based sunnah.com search, which is
  numbering-independent.
- **For anything you intend to act on**, check the Arabic and consult someone
  trained in the sciences of hadith. An index is a finding aid, not a substitute
  for that.

---

## What is included

### Tier 1 — `data/english-graded/` (20,603)

Arabic + English, every narration carrying a grade.

| Collection | Compiler | d. AH | Unique | Notes |
|---|---|---|---|---|
| Ṣaḥīḥ al-Bukhārī | al-Bukhārī | 256 | 4,364 | 4,347 ṣaḥīḥ |
| Ṣaḥīḥ Muslim | Muslim b. al-Ḥajjāj | 261 | 3,794 | 3,752 ṣaḥīḥ |
| Sunan Abī Dāwūd | Abū Dāwūd | 275 | 3,017 | mixed |
| Sunan Ibn Mājah | Ibn Mājah | 273 | 2,867 | mixed; **21 mawḍūʿ** |
| Sunan an-Nasāʾī | an-Nasāʾī | 303 | 2,795 | mixed |
| Jāmiʿ at-Tirmidhī | at-Tirmidhī | 279 | 2,475 | mixed |
| al-Muwaṭṭaʾ | Mālik b. Anas | 179 | 664 | ungraded |
| Musnad Aḥmad *(5% fragment)* | Aḥmad b. Ḥanbal | 241 | 627 | ungraded — see Tier 2a |

### Tier 2a — `data/arabic-ungraded/` (21,073)

- **Musnad Aḥmad**, complete — 19,091 (the Tier 1 entry is a 5% fragment)
- **Sunan ad-Dārimī** — 1,982 (no English translation found anywhere)

### Tier 2b — `data/openiti/` (92,855)

Fifteen collections beyond the Nine Books, extracted from
[OpenITI](https://github.com/OpenITI).

| Collection | Compiler | d. AH | Unique |
|---|---|---|---|
| al-Muʿjam al-Kabīr | aṭ-Ṭabarānī | 360 | 17,150 |
| as-Sunan al-Kubrā | al-Bayhaqī | 458 | 14,832 |
| al-Muʿjam al-Awsaṭ | aṭ-Ṭabarānī | 360 | 8,855 |
| Musnad al-Bazzār (*al-Baḥr az-Zakhkhār*) | al-Bazzār | 292 | 8,965 |
| Muṣannaf Ibn Abī Shayba | Ibn Abī Shayba | 235 | 7,462 |
| al-Mustadrak ʿalā aṣ-Ṣaḥīḥayn | al-Ḥākim an-Naysābūrī | 405 | 6,636 |
| Shuʿab al-Īmān | al-Bayhaqī | 458 | 6,408 |
| Musnad Abū Yaʿlā | Abū Yaʿlā al-Mawṣilī | 307 | 6,341 |
| Muṣannaf ʿAbd ar-Razzāq | ʿAbd ar-Razzāq aṣ-Ṣanʿānī | 211 | 4,197 |
| Sunan ad-Dāraquṭnī | ad-Dāraquṭnī | 385 | 3,465 |
| Ṣaḥīḥ Ibn Khuzayma | Ibn Khuzayma | 311 | 2,876 |
| Musnad aṭ-Ṭayālisī | Abū Dāwūd aṭ-Ṭayālisī | 204 | 2,681 |
| Musnad ash-Shāfiʿī | ash-Shāfiʿī | 204 | 1,202 |
| al-Muʿjam aṣ-Ṣaghīr | aṭ-Ṭabarānī | 360 | 1,156 |
| Sunan Saʿīd b. Manṣūr | Saʿīd b. Manṣūr | 227 | 629 |

---

## Layout

```
app/hadith_library.html     Browsable app — topic rail, grade filter, search
data/english-graded/        Tier 1, CSV + JSON
data/arabic-ungraded/       Tier 2a, CSV + JSON
data/openiti/               Tier 2b, CSV
scripts/openiti_hadith.py   Extract any OpenITI collection (pure stdlib)
scripts/dorar_fetch.py      Attach Dorar.net grades (run off a restricted network)
docs/DATA_SOURCES_GUIDE.md  Where the data comes from and how to get more
docs/PROMPT_PLAYBOOK.md     Staged prompts for rebuilding this in Claude Code
CLAUDE.md                   Project memory — constraints, methods, known bugs
COLLECTION_STATUS.csv       Every collection, built or unavailable, with reasons
```

CSV columns: `collection, ref_no, grade, book_chapter, narrator, hadith_text,
topics, also_narrated_at, verify_phrase` (Tier 1) and `collection, seq_no,
grade, topics, arabic_text, merged_duplicates` (Tier 2). CSVs are UTF-8 with
BOM so Excel renders Arabic correctly.

---

## How the data was built

1. **Marfūʿ filter.** Keep only what the Prophet ﷺ said, did, ordered, or
   approved. Companion opinions (*mawqūf*), Successor statements (*maqṭūʿ*) and
   compiler chapter commentary are screened out.
2. **Deduplicate.** The same hadith recurs through different chains with
   slightly different wording, so exact matching catches almost nothing. Fuzzy
   token overlap on content words with isnād boilerplate stripped: merge at
   `jaccard ≥ 0.48` or (`coverage ≥ 0.72` and `jaccard ≥ 0.35`). Merged
   references are **recorded, not deleted** (`also_narrated_at`).
3. **Grade join.** The grading corpus and the text corpus number hadith
   incompatibly, so the join is by **wording similarity**, not reference number.
   98.6–99.9% matched. *This self-validates:* Bukhārī and Muslim come back
   ~100% ṣaḥīḥ, which is how you know the matching held.
4. **Topic tagging.** ~65 topics in 8 groups, weighted by keyword density with
   the compiler's own book title as a prior.

**No hadith text in this repository was written from memory.** Every narration
comes from a cited dataset. See `CLAUDE.md` for why that rule is absolute, and
for the seven pipeline bugs found while building this — each one produced
plausible-looking wrong output rather than an error.

### Sources

| Source | Provides |
|---|---|
| [`AhmedBaset/hadith-json`](https://github.com/AhmedBaset/hadith-json) | Nine Books, Arabic + English |
| [`ShathaTm/LK-Hadith-Corpus`](https://github.com/ShathaTm/LK-Hadith-Corpus) | Authenticity grades (Leeds / King Saud University) |
| [`abdelrahmaan/Hadith-Data-Sets`](https://github.com/abdelrahmaan/Hadith-Data-Sets) | Arabic, incl. complete Musnad Aḥmad |
| [OpenITI](https://github.com/OpenITI) | Everything beyond the Nine Books |

---

## Known gaps

- **All 113,928 Tier 2 records are ungraded.** Running
  `scripts/dorar_fetch.py --grade-file` against Dorar.net is the highest-value
  remaining task; it captures the grade *and* the scholar who gave it.
- **Ṣaḥīḥ Ibn Ḥibbān** is absent from OpenITI. The surviving recension is Ibn
  Balbān's rearrangement, catalogued separately.
- **Musnad Isḥāq b. Rāhwayh** and **Musnad al-Ḥumaydī** are not in OpenITI.
- **"No early scholar raised concern"** — a criterion this project would like to
  enforce — is not encodable in any dataset found. It requires reading the
  commentarial tradition, not filtering a column. Nothing here pretends to
  satisfy it.

---

## Regenerating

```bash
python3 scripts/openiti_hadith.py --list 0375AH          # browse a repo
python3 scripts/openiti_hadith.py --extract 0375AH --work Tabarani.MucjamKabir --out kabir
python3 scripts/openiti_hadith.py --batch                # all 15 (~1h, ~814 MB cached)
```

Pure standard library, no dependencies. Downloads cache in `~/.openiti_cache/`,
so reruns are cheap and resumable.

---

## Licence and attribution

The hadith texts are classical works in the public domain. The compiled
datasets carry the licences of their upstream sources, linked above — check
those before redistribution. The extraction scripts and topic scheme in this
repository are offered freely; corrections to the data are welcome and valued.
