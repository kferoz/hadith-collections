#!/usr/bin/env python3
"""
build_articles.py — resolve article sources into published article JSON.

WHY THIS EXISTS
  Articles quote hadith. Writing those quotations by hand is exactly the failure
  CLAUDE.md rule 1 warns about: on the first draft of the sira series, six of
  eight reference numbers were written from recall and pointed at unrelated
  narrations — the text looked plausible, the citation was wrong.

  So an article source never contains hadith text. It contains a reference:

      {"ref": ["bukhari", 4457]}                      whole narration
      {"ref": ["bukhari", 3074], "from": "Then fifty", "to": "Final Order"}

  This script resolves every reference against app/hadith.json — the same
  graded dataset the library app uses — and writes the text, book, grade and
  collection name from the source of truth. A reference that does not resolve,
  or that resolves to something not graded authentic, fails the build loudly
  rather than shipping.

USAGE
    python3 scripts/build_articles.py            # build all *.src.json
    python3 scripts/build_articles.py --check    # verify only, write nothing
"""

import argparse, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'app', 'hadith.json')
ARTICLES = os.path.join(ROOT, 'articles')

NAMES = {
    'bukhari': 'Sahih al-Bukhari', 'muslim': 'Sahih Muslim',
    'abudawud': 'Sunan Abi Dawud', 'tirmidhi': "Jami' at-Tirmidhi",
    'nasai': "Sunan an-Nasa'i", 'ibnmajah': 'Sunan Ibn Majah',
    'malik': 'Muwatta Malik', 'ahmed': 'Musnad Ahmad',
}


def load_index():
    if not os.path.exists(DATA):
        sys.exit(f'missing {DATA} — run scripts/build_app_data.py first')
    return {(r['s'], r['n']): r for r in json.load(open(DATA, encoding='utf-8'))}


def resolve(ref, idx, where, errors):
    """Turn {"ref": [slug, number], "from":…, "to":…} into a published block."""
    slug, num = ref['ref']
    rec = idx.get((slug, num))
    if rec is None:
        errors.append(f'{where}: {slug} no.{num} is not in the dataset')
        return None

    # Rule 6 of the article guidelines: authentic only.
    if not rec['g'].startswith('Sahih'):
        errors.append(f'{where}: {slug} no.{num} is graded "{rec["g"]}", not Sahih')
        return None

    text = ' '.join(rec['x'].split())

    # Optional excerpt. Both markers must exist in the real text, so a quote
    # can be shortened but never invented.
    a, b = ref.get('from'), ref.get('to')
    if a or b:
        i = text.find(a) if a else 0
        if a and i < 0:
            errors.append(f'{where}: {slug} no.{num} has no passage starting "{a}"')
            return None
        j = text.find(b, i) if b else len(text)
        if b and j < 0:
            errors.append(f'{where}: {slug} no.{num} has no passage ending "{b}"')
            return None
        j = j + len(b) if b else len(text)
        excerpt = text[i:j]
        text = ('…' if i > 0 else '') + excerpt + ('…' if j < len(text) else '')

    return {
        'text': text,
        'src': NAMES.get(slug, slug),
        'slug': slug,
        'n': num,
        'book': rec['b'],
        'grade': rec['g'],
        'verify': rec.get('q', ''),
    }


def build(path, idx, check_only):
    doc = json.load(open(path, encoding='utf-8'))
    errors, count = [], 0
    for ch in doc.get('chapters', []):
        for sec in ch.get('sections', []):
            out = []
            for ref in sec.get('hadith', []):
                where = f'ch{ch["n"]} "{ch["title"]}" / {sec["heading"][:28]}'
                block = resolve(ref, idx, where, errors)
                if block:
                    out.append(block)
                    count += 1
            sec['hadith'] = out

    name = os.path.basename(path).replace('.src.json', '.json')
    if errors:
        print(f'  {name}: {len(errors)} PROBLEM(S)')
        for e in errors:
            print(f'    ✗ {e}')
        return False, count

    if not check_only:
        json.dump(doc, open(os.path.join(ARTICLES, name), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    chapters = len(doc.get('chapters', []))
    sections = sum(len(c.get('sections', [])) for c in doc.get('chapters', []))
    print(f'  {name}: {chapters} chapters, {sections} sections, '
          f'{count} narrations — all verified authentic')
    return True, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='verify references without writing output')
    a = ap.parse_args()

    idx = load_index()
    print(f'dataset: {len(idx):,} graded narrations')
    srcs = sorted(glob.glob(os.path.join(ARTICLES, '*.src.json')))
    if not srcs:
        sys.exit(f'no *.src.json found in {ARTICLES}')

    allok, total = True, 0
    for s in srcs:
        ok, n = build(s, idx, a.check)
        allok &= ok
        total += n

    print(f'\n{total} narrations resolved across {len(srcs)} article(s)')
    if not allok:
        sys.exit('BUILD FAILED — fix the references above. No article quotes a '
                 'narration this script could not verify.')


if __name__ == '__main__':
    main()
