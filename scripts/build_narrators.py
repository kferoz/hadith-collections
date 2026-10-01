#!/usr/bin/env python3
"""
build_narrators.py — build the app's chronological narrator index.

WHAT THIS PRODUCES
  app/narrators.json: the people who narrate the hadith in app/hadith.json,
  clustered across spelling variants, ordered by death year, each carrying how
  many narrations they contribute and in which collections.

TWO KINDS OF FACT, DELIBERATELY KEPT APART
  Counts, collections and topics are DERIVED from this repository's own graded
  dataset. They are exact and reproducible.

  Death years, generation, birthplace and the Arabic name are BIOGRAPHICAL and
  come from an external narrator dataset (see SOURCE below). They are matched by
  name, so a match can be wrong in a way a count cannot. Every biographical
  field in the output carries `bio_source`, and the app labels it as such.

SOURCE
  src/kaggle_rawis.csv inside github.com/R3GENESI5/Itqan — a community narrator
  dataset of 24,326 entries with English and Arabic names, generation labels and
  Hijri/Gregorian death years. Only ~16% carry a usable numeric death year, and
  it is NOT a classical rijal work: treat it as a finding aid, not an authority.
  Itqan also ships Arabic profiles keyed to the classical books (Taqrib,
  Tahdhib al-Kamal, Siyar, Ibn Sa'd); those are better sourced but Arabic-only,
  so they are not used here.

USAGE
  python3 scripts/build_narrators.py --rawis /path/to/kaggle_rawis.csv
  python3 scripts/build_narrators.py --rawis ... --report   # matching detail
"""

import argparse, csv, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(10 ** 7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'app', 'hadith.json')
OUT = os.path.join(ROOT, 'app', 'narrators.json')

# Translator boilerplate wrapped around a name. Order matters: longest first.
STRIP = [
    r'^it (?:was|has been) (?:narrated|reported|related)\s+(?:on the authority of|from|that|by)?\s*',
    r'^it is (?:narrated|reported|related)\s+(?:on the authority of|from|that|by)?\s*',
    r'^(?:this )?(?:hadith|tradition) (?:has been|is) (?:narrated|reported|transmitted)\s+(?:on the authority of|from|by)?\s*',
    r'^narrated\s+', r'^reported\s+by\s+', r'^on the authority of\s+', r'^from\s+',
    r'^that\s+',
]
# Trailing verbiage after the name.
# Trailing verbiage after the name. Two traps here, both found the hard way:
# "Said" is the name Sa'id as often as the verb ("Abu Said al-Khudri"), and
# "As-" is the Arabic article, not the word "as" ("Abu As-Samh"). Both once
# reduced a name to a bare "abu", which then merged into the largest abu-cluster
# and filed Abu Sa'id al-Khudri's narrations under Abu Hurayra.
TAIL = [
    r'\s+(?:reported|narrated|says|stated|related|transmitted|mentioned)\b.*$',
    r'\s+said\b.*$',
    r'\s+(?:that|who)\b.*$',
    r'\s*\bthe (?:wife|daughter|son|freed slave|mawla|client) of\b.*$',
]
# A name that reduces to one of these carries no identity of its own.
DEGENERATE = {'abu', 'abi', 'ibn', 'bint', 'al', 'abd', 'umm', 'ab', 'the', 'a'}
HONOURIFIC = [
    r'\(\s*ﷺ\s*\)', r'\(\s*saw\s*\)', r'\(\s*pbuh\s*\)',
    r'\(\s*رضى? الله عنه[ا|م]?\s*\)', r'\(\s*may allah[^)]*\)',
    r'\bmay allah be pleased with (?:him|her|them)\b',
    r'\bradi\s*allahu\s*anh[ua]?\b', r'\bummul?\s+mu.?mini?n\b',
    r'\bal-?ansar[iy]\b', r'\bra\b',
]

def strip_marks(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))

def clean_name(raw):
    """Pull a bare personal name out of a narrator field."""
    s = (raw or '').strip()
    s = re.sub(r'\([^)]*\)', lambda m: '' if re.search(
        r'ﷺ|saw|pbuh|الله|allah|may ', m.group(0), re.I) else m.group(0), s)
    s = s.lower()
    for p in HONOURIFIC: s = re.sub(p, ' ', s, flags=re.I)
    prev = None
    while prev != s:                       # boilerplate can nest
        prev = s
        for p in STRIP: s = re.sub(p, '', s, flags=re.I).strip()
    # Protect name particles from the tail-stripper before it runs.
    s = re.sub(r"\b(abu|abi|ibn|bint|umm)\s+(sa['\u2019`]?[iy]?[de]+|as[- ])",
               lambda m: m.group(1) + '\x00' + m.group(2), s, flags=re.I)
    for p in TAIL: s = re.sub(p, '', s, flags=re.I)
    s = s.replace('\x00', ' ')
    s = s.strip(" :,.;'\"-–—()")
    toks = [t for t in re.split(r'[\s-]+', s) if t]
    if not toks or all(t in DEGENERATE for t in toks):
        return ''
    return s

# Spelling variants that are the same person. Applied to the match key only;
# the display name keeps the dataset's own wording.
SUBS = [
    (r'[`‘’ʻʼʾʿ\'’]', ''),
    (r'\bbinti?\b', 'bint'), (r'\bbn\b', 'ibn'), (r'\bbin\b', 'ibn'),
    (r'\bb\.\s*', 'ibn '), (r'\babi\b', 'abu'), (r'\babee\b', 'abu'),
    (r'\babdul\s*', 'abd al'), (r'\babdur\s*', 'abd al'), (r'\babdir\s*', 'abd al'),
    (r'\bubaidullah\b', 'ubayd allah'), (r'\bubaydullah\b', 'ubayd allah'),
    (r'\babdullah\b', 'abd allah'), (r'\babdallah\b', 'abd allah'),
    (r'hurai?rah?\b', 'hurayra'), (r'hurayrah\b', 'hurayra'),
    (r'\baishah?\b', 'aisha'), (r'\bayesha\b', 'aisha'),
    (r'\bumar\b', 'umar'), (r'\bomar\b', 'umar'),
    (r'\buthmaan\b', 'uthman'), (r'\baffaan\b', 'affan'),
    (r'\bkhattaab\b', 'khattab'), (r'\bmaalik\b', 'malik'),
    (r'\bjaabir\b', 'jabir'), (r'\banas\b', 'anas'),
    (r'\bsaeed\b', 'said'), (r'\bsaad\b', 'sad'), (r'\bsa d\b', 'sad'),
    (r'\bmuhammed\b', 'muhammad'), (r'\bmohammad\b', 'muhammad'),
    (r'\bal\s+', 'al'), (r'\bal-', 'al'), (r'\bel-', 'al'),
    (r'\babu([a-z]{3,})\b', r'abu \1'),
    (r'\bibn([a-z]{3,})\b', r'ibn \1'),
    (r'[^a-z ]', ' '),
]

def key(name):
    s = strip_marks(name.lower())
    for pat, rep in SUBS: s = re.sub(pat, rep, s)
    return ' '.join(s.split())

def load_rawis(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    out = {}
    for r in rows:
        raw = (r.get('name') or '').strip()
        # "English Name ( عربي ( رضي الله عنه" — split on the first Arabic char
        m = re.search(r'[؀-ۿ]', raw)
        en = raw[:m.start()] if m else raw
        en = re.sub(r'\(\s*$', '', en).strip(' (')
        ar = ''
        if m:
            ar = raw[m.start():]
            ar = re.split(r'\(', ar)[0].strip()
        def val(c):
            v = (r.get(c) or '').strip()
            return '' if v in ('', '-', 'NA', 'nan', 'NaN', 'None') else v
        dh, dg = val('death_date_hijri'), val('death_date_gregorian')
        try: dh = int(float(dh)) if dh else None
        except ValueError: dh = None
        try: dg = int(float(dg)) if dg else None
        except ValueError: dg = None
        if dh is not None and not (0 <= dh <= 1400): dh = None
        rec = {'en': en, 'ar': ar, 'grade': val('grade'),
               'death_h': dh, 'death_g': dg,
               'birth_place': val('birth_place'), 'death_place': val('death_place'),
               'idx': val('scholar_indx')}
        k = key(en)
        if k:
            out.setdefault(k, []).append(rec)
    return out


# Generation labels in the source are terse; these are what the app shows.
GEN = [
    (r'comp\.|companion', 'Companion', 1),
    (r"taba'? tabi|succ\.", "Successor's successor", 3),
    (r"follower|tabi'", 'Successor', 2),
    (r'3rd century', '3rd century AH', 4),
    (r'4th century', '4th century AH', 5),
    (r'rasool allah', 'The Prophet', 0),
]
def generation(g):
    gl = (g or '').lower()
    for pat, label, rank in GEN:
        if re.search(pat, gl): return label, rank
    return 'Unplaced', 9


# A bare name is not a unique key in rijal — "'Abdullah bin 'Umar" names six
# different people in this source, and the famous Companion is not among them.
# So a biography is attached ONLY when it is unambiguous; otherwise the narrator
# ships with no dates rather than a stranger's. A wrong death year would corrupt
# the chronological ordering this section exists for, and would look right.
GENERIC = {'abd allah', 'abu', 'ibn', 'bint', 'muhammad', 'ali', 'umar', 'uthman',
           'anas', 'jabir', 'aisha', 'abd alrahman', 'said', 'sad', 'salim'}

def pick_bio(k, index):
    """Return (record, reason-if-refused).

    A cluster key is matched exactly, or as a prefix of exactly one biography
    key — translators write "Aisha" where the source writes "Aisha bint Abi
    Bakr". A prefix that fits several people is refused, not guessed."""
    cands = index.get(k, [])
    if not cands:
        pre = [bk for bk in index if bk.split()[:len(k.split())] == k.split()]
        if len(pre) == 1:
            cands = index[pre[0]]
        elif len(pre) > 1:
            return None, f'{len(pre)} people share this name form'
    if not cands:
        return None, 'not in the biography source'
    toks = [t for t in k.split() if t not in ('ibn', 'bint', 'al', 'abd')]
    if k in GENERIC or len(toks) < 2:
        return None, 'name too generic to identify one person'
    dated = [c for c in cands if c['death_h'] is not None]
    if not dated:
        return None, 'no candidate carries a death year'
    years = {c['death_h'] for c in dated}
    if len(years) > 1:
        return None, f'{len(dated)} candidates disagree on the death year'
    rec = dated[0]
    # Cross-check the death year against the generation the same source assigns.
    # Name matching in rijal is unreliable — spot checks turned up a Companion
    # dated to 190 AH and Ibn az-Zubayr (d.73) dated to 12 — so a year that
    # contradicts its own generation label is refused rather than shown.
    label, _ = generation(rec['grade'])
    lo, hi = {
        'Companion': (11, 110),
        'Successor': (60, 190),
        "Successor's successor": (110, 240),
        '3rd century AH': (190, 310),
        '4th century AH': (280, 410),
    }.get(label, (11, 320))
    if not (lo <= rec['death_h'] <= hi):
        return None, f"death {rec['death_h']} AH contradicts '{label}' ({lo}-{hi})"
    # A Companion dying within a few years of the Prophet cannot have transmitted
    # a large body of narrations; treat that as a mismatched person.
    if label == 'Companion' and rec['death_h'] < 20:
        return None, f"death {rec['death_h']} AH too early for a prolific narrator"
    return rec, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rawis', required=True)
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--min', type=int, default=3,
                    help='minimum narrations to include (default 3)')
    a = ap.parse_args()

    D = json.load(open(DATA, encoding='utf-8'))
    bio = load_rawis(a.rawis)
    print(f'dataset   : {len(D):,} narrations')
    print(f'bio source: {len(bio):,} distinct narrator keys')

    clusters = defaultdict(lambda: {'variants': Counter(), 'n': 0, 'raw': Counter(),
                                    'cols': Counter(), 'topics': Counter(),
                                    'grades': Counter(), 'refs': []})
    unnamed = 0
    for r in D:
        nm = clean_name(r.get('nr'))
        if not nm or len(nm) < 3: unnamed += 1; continue
        k = key(nm)
        if not k or len(k) < 3: unnamed += 1; continue
        c = clusters[k]
        c['variants'][nm] += 1
        c.setdefault('raw', Counter())[(r.get('nr') or '').strip()] += 1
        c['n'] += 1
        c['cols'][r['s']] += 1
        c['grades'][r['g']] += 1
        for t in r['t']: c['topics'][t] += 1
        if len(c['refs']) < 3: c['refs'].append([r['s'], r['n']])

    print(f'clusters  : {len(clusters):,} raw (from narrator fields; {unnamed:,} entries had none usable)')

    # "Anas" and "Anas ibn Malik" are one person split by translator habit.
    # Merge a short key into a longer one only when the longer one is the single
    # candidate that starts with it AND is clearly dominant, so an ambiguous
    # short form ("Jabir" with two plausible expansions) is left alone.
    keys = sorted(clusters, key=lambda k: -clusters[k]['n'])
    merged = 0
    for short in list(keys):
        if short not in clusters: continue
        st = short.split()
        if all(t in DEGENERATE for t in st): continue
        if len(st) > 3: continue
        # a longer key that either starts with this one ("anas" -> "anas ibn
        # malik") or ends with it ("ibn abbas" -> "abd allah ibn abbas")
        # Prefix merge is always safe ("anas" -> "anas ibn malik").
        # Suffix merge is only safe when the short form is itself relational
        # ("ibn abbas" -> "abd allah ibn abbas"); a bare name is NOT the same
        # person as the kunya built on it — Ayyub is not Abu Ayyub, and Bakr is
        # not Abu Bakr.
        relational = st[0] in ('ibn', 'bint')
        exp = [k for k in clusters
               if k != short and clusters[k]['n'] > 0 and len(k.split()) > len(st)
               and (k.split()[:len(st)] == st
                    or (relational and k.split()[-len(st):] == st))]
        if not exp: continue
        exp.sort(key=lambda k: -clusters[k]['n'])
        if len(exp) > 1:
            # Several expansions: merge only when one overwhelmingly dominates,
            # so "Anas" folds into "Anas ibn Malik" while "Abdullah" — which has
            # many comparable expansions — is left alone.
            if clusters[exp[0]]['n'] < 3 * clusters[exp[1]]['n']: continue
        long = exp[0]
        if clusters[long]['n'] < clusters[short]['n'] * 0.4: continue
        tgt, src = clusters[long], clusters[short]
        tgt['variants'].update(src['variants']); tgt['n'] += src['n']
        tgt['raw'].update(src.get('raw', Counter()))
        tgt['cols'].update(src['cols']); tgt['topics'].update(src['topics'])
        tgt['grades'].update(src['grades'])
        tgt['refs'] = (tgt['refs'] + src['refs'])[:3]
        del clusters[short]; merged += 1
    print(f'            {merged:,} short forms merged -> {len(clusters):,} people')

    out, matched, refusals = [], 0, Counter()
    for k, c in clusters.items():
        if c['n'] < a.min: continue
        disp = c['variants'].most_common(1)[0][0].title()
        b, why = pick_bio(k, bio)
        if b: matched += 1
        else: refusals[why] += 1
        gen, rank = generation(b['grade'] if b else '')
        out.append({
            'key': k,
            'name': (b['en'] if b and b['en'] else disp),
            'ar': b['ar'] if b else '',
            'n': c['n'],
            'cols': dict(c['cols'].most_common()),
            'topics': [t for t, _ in c['topics'].most_common(6)],
            'sahih': sum(v for g, v in c['grades'].items() if g.startswith('Sahih')),
            'death_h': b['death_h'] if b else None,
            'death_g': b['death_g'] if b else None,
            'gen': gen, 'rank': rank,
            'place': (b['birth_place'] if b else '') or (b['death_place'] if b else ''),
            'bio_source': 'kaggle_rawis' if b else None,
            'variants': [v for v, _ in c['variants'].most_common(4)],
            # every raw narrator string in this cluster, so the app can map a
            # hadith back to its person without re-implementing the normaliser
            'raw': [v for v, _ in c['raw'].most_common()],
        })

    # Chronological: known death year first, then by generation, then by volume.
    out.sort(key=lambda r: (0 if r['death_h'] is not None else 1,
                            r['death_h'] if r['death_h'] is not None else 0,
                            r['rank'], -r['n']))

    dated = sum(1 for r in out if r['death_h'] is not None)
    print(f'included  : {len(out):,} narrators with >= {a.min} narrations')
    print(f'  matched to a biography : {matched:,} ({100*matched/max(len(out),1):.1f}%)')
    print(f'  with a death year      : {dated:,} ({100*dated/max(len(out),1):.1f}%)')
    print(f'  narrations covered     : {sum(r["n"] for r in out):,} of {len(D):,}')

    if a.report:
        print('\nbiography refused for:')
        for why, n2 in refusals.most_common(): print(f'  {n2:5d}  {why}')
        print('\ntop 20 by volume:')
        for r in sorted(out, key=lambda x: -x['n'])[:20]:
            d = f"d.{r['death_h']}H" if r['death_h'] is not None else '—'
            print(f"  {r['n']:5d}  {d:9s} {r['gen']:22s} {r['name'][:46]}")

    json.dump({'narrators': out,
               'note': 'Counts, collections and topics are derived from this '
                       'repository\'s graded dataset and are exact. Death years, '
                       'generation and places come from an external community '
                       'narrator dataset matched by name, and are a finding aid '
                       'rather than an authority.',
               'bio_source': 'kaggle_rawis.csv (github.com/R3GENESI5/Itqan)'},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'\nwrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)')

if __name__ == '__main__':
    main()
