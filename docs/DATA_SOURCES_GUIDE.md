# Getting Hadith Data Through Allowed Channels

Your sandbox permits only **github.com, PyPI, and npm** (plus their CDNs). That
turned out to be far less limiting than it first appeared. Here is the full map
of what works, what doesn't, and why.

---

## 1. The key insight: OpenITI

I initially told you the ~25 collections beyond the Nine Books were
unavailable. **That was wrong**, and the correction matters more than anything
else in this document.

[**OpenITI**](https://github.com/OpenITI) (Open Islamic Texts Initiative) is a
scholarly digitisation project — Aga Khan University, University of Vienna, and
others — hosting **thousands of classical Arabic works on GitHub**. Because it's
on GitHub, it's reachable from your restricted network.

**Repos are named by author death date**, rounded up to a 25-year bucket:

| Compiler | Died | Repo |
|---|---|---|
| Abd ar-Razzaq, at-Tayalisi, ash-Shafi'i | 204–211 | `0225AH` |
| Ibn Abi Shayba, Sa'id ibn Mansur | 227–235 | `0250AH` |
| al-Bazzar | 292 | `0300AH` |
| Abu Ya'la, Ibn Khuzayma | 307–311 | `0325AH` |
| Ibn Hibban, at-Tabarani | 354–360 | `0375AH` |
| ad-Daraqutni | 385 | `0400AH` |
| al-Hakim | 405 | `0425AH` |
| al-Bayhaqi | 458 | `0475AH` |

Download any repo without authentication:

```bash
curl -L -o 0375AH.zip \
  https://codeload.github.com/OpenITI/0375AH/zip/refs/heads/master
```

Each is 50–150 MB. There are 224 repos in the org, including Persian (`PER…`)
buckets.

### The OpenITI file format

Plain text with a metadata header, then body markup:

```
######OpenITI#
#META# 010.AuthorNAME :: سليمان بن أحمد ... الطبراني
#META# 020.BookTITLE  :: المعجم الكبير
#META#Header#End#

# 4 حدثنا أحمد بن المعلى الدمشقي ثنا هشام بن خالد
~~ثنا ضمرة بن ربيعة عن الليث بن سعد قال ...
```

- `# N ` opens hadith number N
- `~~` continues the previous line (a line-wrap marker, not content)
- `PageV01P052` / `ms0002` are page and manuscript milestones — strip them
- `###` marks sections in *some* editions

**Two traps I hit, which cost real accuracy:**

1. **Multiple editions per work, with different markup.** For al-Mu'jam
   al-Kabir, the *largest* file (14.19 MB) yielded only **4** parseable hadith
   because it uses `###` sections; a smaller file (12.96 MB) yielded **21,586**
   with `# N` numbering. Never pick an edition by file size — parse candidates
   and score them by how many entries they actually yield. `openiti_hadith.py`
   does this.

2. **Work-name fragments match the wrong author.** Searching `0250AH` for
   `Musnad` returned *Musnad Ahmad* (26k hadith) under the label "Ibn Rahwayh"
   (~4k expected). Always pin the author: `IbnAbiShayba.Musannaf`, not
   `Musannaf`. Note transliterations are non-obvious — `CabdRazzaqSancani`,
   `AbuYaclaMawsili`, `HakimNaysaburi` (`c` = ʿayn, `C` capitalised).

### Using the script

```bash
# See what a repo contains
python3 openiti_hadith.py --list 0375AH
python3 openiti_hadith.py --list 0375AH --grep Tabarani

# Extract one work
python3 openiti_hadith.py --extract 0375AH --work Tabarani.MucjamKabir --out kabir

# Extract all 15 preset collections (~1 hour, ~600 MB downloaded)
python3 openiti_hadith.py --batch
```

Downloads cache in `~/.openiti_cache/`, so reruns are fast. Output is one CSV
and one JSON per collection, with the same marfūʿ filter, fuzzy dedupe, and
topic tagging as your existing eight books.

### Not found in OpenITI

Ishaq ibn Rahwayh and al-Humaydi's Musnads aren't in the corpus. Ibn Hibban is
present as an author (`0354IbnHibbanBusti`) but only for *Majruhin*, *Thiqat*,
*Mashahir* — his **Sahih is absent**, likely because the surviving recension is
Ibn Balban's rearrangement, catalogued separately.

---

## 2. What else is on GitHub

| Repo | Contents |
|---|---|
| `AhmedBaset/hadith-json` | 9 books + thematic, Arabic **and English**, structured JSON |
| `ShathaTm/LK-Hadith-Corpus` | 6 canonical books with **`English_Grade` columns** — your grading source |
| `abdelrahmaan/Hadith-Data-Sets` | 9 books Arabic, with and without tashkil; **full Musnad Ahmad (26k)** |
| `mhashim6/Open-Hadith-Data` | 9 books Arabic, diacritised and plain |
| `fawazahmed0/hadith-api` | multi-language, multi-grade; served via jsDelivr CDN |

**The jsDelivr trick** — npm and GitHub CDNs serve raw files, so an "API" hosted
there is reachable even when the API's own domain isn't:

```bash
curl https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json
```

If `cdn.jsdelivr.net` is blocked, `raw.githubusercontent.com` is on your
allowlist and serves the same files.

---

## 3. PyPI and npm

Useful **tools**, not data:

```bash
pip install openiti      # official OpenITI corpus utilities
pip install pyarabic     # Arabic normalisation, diacritic stripping, tokenising
pip install camel-tools  # morphological analysis — better topic matching than my
                         # crude 5-char prefix heuristic
```

`camel-tools` is the upgrade path for topic classification. My current approach
compares word prefixes, which is why "ṣalāh" (prayer) initially matched the
blessing formula *ṣallā llāhu ʿalayhi wa-sallam* in nearly every isnad and
inflated the Prayer topic to 13,307 hits. Proper lemmatisation fixes that class
of error at the root.

---

## 4. Dorar — for when you're off this network

[Dorar.net](https://dorar.net) is the single best grading source: hundreds of
thousands of hadith, each with the **grade and the grading scholar named**,
spanning far more collections than the Nine. It's blocked here
(`x-deny-reason: host_not_allowed`), so run `dorar_fetch.py` on an unrestricted
machine.

```bash
python3 dorar_fetch.py --search "الصلاة" --pages 5 --out salah.csv
python3 dorar_fetch.py --grade-file my_hadiths.csv --text-col arabic_text --out graded.csv
```

The second mode is the valuable one: it takes your **existing ungraded Arabic
collections** and looks up a grade for each by matching text — the same join I
did with the LK corpus, but against a much larger and multi-scholar source.

**Be considerate:** the script rate-limits to ~1 request/second by default.
Dorar is a free scholarly service; don't hammer it. For 92,855 hadith, a full
grading pass takes roughly a day of wall-clock time. Run it in batches.

---

## 5. Honest limits

- **OpenITI gives text, not grades.** Nothing in section 1 grades anything. All
  92,855 narrations are **ungraded** — treat them as unverified until you run a
  grading pass. This matters especially for Ṭabarānī and Bayhaqī, which contain
  substantial weak material by design.
- **Topic tags are keyword-based** and weaker in Arabic than English, since I
  have no morphological analyser in that pipeline. Browse with them; don't rely
  on them.
- **Sequence numbers are positional** within the parsed edition, not the
  standard printed numbering of each work. Different editions number
  differently. Use them as internal IDs only.
- **Edition variance is real.** Two editions of the same work can differ in
  hadith count, ordering, and inclusion. The script notes which source file it
  used in `source_file`.
- **Criterion #4 from your original list** — that no early scholar raised
  concern — remains unencodable in any dataset I've found. It requires reading
  the commentarial tradition, not filtering a column.
