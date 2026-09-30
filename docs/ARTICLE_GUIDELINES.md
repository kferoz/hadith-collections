# Article Guidelines

Rules for every article in `articles/`. Article one — *The Life of the Prophet ﷺ*
— was built to these. Future topics follow them unless the list below changes.

---

## The rules as given

1. **Multiple sub-articles with headlines.** Each article is a series of
   chapters; each chapter carries two or three headed sections.
2. **Plain English.** Write for someone with no background in the subject.
   Short sentences. No jargon without a plain-language gloss beside it.
3. **20–30 lines per sub-article.** Measured as rendered lines including any
   narration quoted inside the section, not source lines.
4. **As many articles as the topic needs.** Chapter count follows the material,
   not a target.
5. **High-quality UI/UX, readable at any age.** See *Design* below.
6. **Authentic narrations only**, none disputed by reputable scholars.
7. **Written to be read like a novel.** Narrative pull, not a lecture.
8. **Every narration carries its reference.**
9. These guidelines govern future topics; additions get added here.

---

## How rule 6 is actually enforced

This is the rule most easily broken by accident, so it is enforced mechanically
rather than by care alone.

**An article source never contains hadith text.** It contains a reference:

```json
{"ref": ["bukhari", 4457]}
{"ref": ["bukhari", 3074], "from": "Then fifty prayers", "to": "Final Order"}
```

`scripts/build_articles.py` resolves each reference against `app/hadith.json`
and writes the text, book, grade and collection from the dataset. A reference
that does not resolve, or resolves to something not graded Ṣaḥīḥ, **fails the
build**. An excerpt whose `from`/`to` markers are not present in the real text
also fails. So a quotation can be shortened but never invented, and a citation
can never drift from the words it claims to carry.

**This is not a theoretical safeguard.** On the first draft of the sīra series,
six of eight reference numbers were written from recall. Every one pointed at an
unrelated narration — Bukhārī 3653 to a hadith about Khadīja, 1846 to one about
fasting before Ramadan. The prose read fine and the citations were wrong. The
verification pass caught all six, and the reference-only design now makes that
class of error impossible rather than merely detected.

Write prose freely. Never write a hadith.

### What "authentic" covers, and what it does not

The build accepts only narrations graded Ṣaḥīḥ in this repository's dataset —
al-Albānī's gradings by way of the LK corpus. That satisfies "authentic". It
does **not** satisfy "not disputed by any reputable scholar", which no dataset
encodes; grading differs between scholars and always has. Prefer Bukhārī and
Muslim, whose authenticity is agreed collection-wide, and treat a narration
found only in the Sunan as needing a stronger reason to be used.

---

## Honesty about gaps

**Say what the record does not contain.** The familiar biography draws heavily
on *sīra* literature — Ibn Isḥāq, Ibn Hishām — which gathered widely and left
the sifting to others. Much of it never passed through hadith criticism at all.

So the birth year, the wet-nurse, the monk who recognised the boy, the head bowed
to the saddle entering Makkah: all absent from the authentic collections, all
omitted or explicitly flagged in article one rather than quietly told as fact.

An article that is honest about its silences is more trustworthy than one that
fills them. When a well-known episode has to be left out, a sentence saying so —
and saying why — is better than an unexplained gap.

---

## Voice (rule 7)

Narrative, not devotional and not academic. What earns the reader's attention:

- **Open on a concrete moment**, not a thesis. A man walking up a hill with food
  his wife packed. Three hundred men counting a thousand opposite them.
- **Let the detail do the work.** Aisha chewing a tooth-stick soft for a dying
  man says more than any adjective.
- **Point at what is strange.** The first revelation scene has a man saying
  *I can't* three times and being physically overwhelmed. That is not how an
  invented story goes, and saying so out loud is more interesting than reverence.
- **Short paragraphs.** Two to four sentences. White space is pacing.
- **Trust the reader.** No moral tacked on the end of a section.
- **Keep the frame honest.** Preserve the failures — Uḥud was lost because
  archers disobeyed a direct order, and that is in the most rigorous collections
  with names attached. The tradition kept its own defeats; the article should
  too.

---

## Design

The reader inherits the library app's system, so the two read as one product:

- **Type first.** Body text 19px Literata, line-height 1.8, measure about 68
  characters. Every `font-size` written `calc(Npx * var(--fs))` so the TEXT A/A
  control scales the page from 0.92× to 1.42×. Tap targets ≥42px.
- **Gradients** (lapis → jade → gold leaf, from manuscript illumination) on the
  header, section rules, chapter markers and narration cards. **Never behind
  running text.**
- **Narration cards** are visually distinct from prose — gradient wash, jade
  edge, italic — and always carry collection, number, book, grade badge and a
  wording-based verify link.
- **Chapter rail** with era labels, plus previous/next at the foot of each
  chapter. Both themes. No localStorage.

---

## Adding a topic

1. Search the dataset for what the authentic record actually supports:
   `python3 -c "import json;D=json.load(open('app/hadith.json'))..."` — do this
   **before** outlining, so the chapter structure follows the evidence rather
   than a story you already have in mind.
2. Write `articles/<slug>.src.json`: chapters → sections → `paras` + `hadith`
   refs. Prose in `paras`, `*word*` for emphasis.
3. `python3 scripts/build_articles.py --check` until it passes.
4. `python3 scripts/build_articles.py` to write the published JSON.
5. Add the article to the reader's list and commit both source and build.

If a chapter cannot be supported by authentic narrations, that is a finding
about the sources, not a problem to write around.
