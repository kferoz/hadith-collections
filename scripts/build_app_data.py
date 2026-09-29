#!/usr/bin/env python3
"""
build_app_data.py — build the browsable app's data file from the committed
per-collection JSON in data/english-graded/.

WHY THIS EXISTS
  app/index.html is a 23 KB shell that fetches app/hadith.json at runtime,
  rather than a single 14 MB file with the data inlined. The shell paints
  immediately instead of parsing 13.7 MB of JavaScript first. This script
  regenerates that data file, so the app's data always traces back to the
  committed per-collection sources rather than drifting from them.

USAGE
    python3 scripts/build_app_data.py                # writes app/hadith.json
    python3 scripts/build_app_data.py --standalone   # also writes a single-file
                                                     # build for file:// use

NOTE ON file://
  Browsers refuse fetch() over file://, so double-clicking app/index.html shows
  a load error. Serve the folder instead:

      python3 -m http.server 8000     # then open http://localhost:8000/app/

  Or pass --standalone for a single self-contained HTML file that opens
  directly with no server. That build is deliberately NOT committed: it would
  duplicate 13.7 MB already in the repo.

FIELD NAMES
  The app uses short keys to keep the payload small. The mapping is:
    s  collection slug      x  hadith text
    n  reference number     t  topics
    b  book / chapter       g  authenticity grade
    nr narrator             also  merged duplicate references
    q  verify phrase (wording-based sunnah.com search)
"""

import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'english-graded')
APP = os.path.join(ROOT, 'app')

# Order matters: it is the order of the app's collection dropdown.
ORDER = ['bukhari', 'muslim', 'abudawud', 'tirmidhi', 'nasai', 'ibnmajah',
         'malik', 'ahmed']


def build():
    out = []
    for slug in ORDER:
        path = os.path.join(SRC, slug + '.json')
        if not os.path.exists(path):
            sys.exit(f'missing source: {path}')
        doc = json.load(open(path, encoding='utf-8'))
        for h in doc['hadiths']:
            out.append({
                's': slug,
                'n': h['ref_no'],
                'b': h['book'],
                'nr': h['narrator'],
                'x': h['text'],
                't': h['topics'],
                'g': h.get('grade', 'No grading source'),
                'also': h.get('also_at', [])[:3],
                'q': h.get('verify_phrase', ''),
            })
        print(f'  {slug:10s} {len(doc["hadiths"]):6d}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--standalone', action='store_true',
                    help='also write app/hadith_library_standalone.html '
                         '(single file, opens without a server; not committed)')
    a = ap.parse_args()

    print('reading data/english-graded/ …')
    records = build()

    os.makedirs(APP, exist_ok=True)
    data_path = os.path.join(APP, 'hadith.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\nwrote {data_path}  '
          f'({len(records):,} records, {os.path.getsize(data_path)/1048576:.2f} MB)')

    # sanity: the grade join self-check that catches a broken pipeline
    sahih = sum(1 for r in records if r['g'].startswith('Sahih'))
    bad_in_sahihayn = [r for r in records
                       if r['s'] in ('bukhari', 'muslim')
                       and ("Da'if" in r['g'] or r['g'].startswith('Mawdu'))]
    print(f'  sahih overall: {sahih:,}')
    print(f'  weak/fabricated inside Bukhari or Muslim: {len(bad_in_sahihayn)} '
          f'(must be 0)')
    if bad_in_sahihayn:
        sys.exit('FAIL: the grade join is broken — see CLAUDE.md, "Grade join".')

    if a.standalone:
        shell = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
        inline = shell.replace(
            "fetch('hadith.json').then(r=>{\n  if(!r.ok) throw new Error('HTTP '+r.status);\n  return r.json();\n}).then(data=>{",
            'Promise.resolve(window.__HADITH__).then(data=>{')
        if 'window.__HADITH__' not in inline:
            sys.exit('could not inline: the fetch block in app/index.html changed; '
                     'update this script to match.')
        doc = ('<!doctype html><html><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1,'
               'viewport-fit=cover">'
               '<style>:root{color-scheme:light}body{margin:0}'
               'img{max-width:100%}[hidden]{display:none!important}</style>'
               '<script>window.__HADITH__=' +
               json.dumps(records, ensure_ascii=False, separators=(',', ':')) +
               '</scr' + 'ipt></head><body>' + inline + '</body></html>')
        sa = os.path.join(APP, 'hadith_library_standalone.html')
        open(sa, 'w', encoding='utf-8').write(doc)
        print(f'wrote {sa}  ({os.path.getsize(sa)/1048576:.2f} MB, not committed)')


if __name__ == '__main__':
    main()
