#!/usr/bin/env python3
"""
dorar_fetch.py — fetch graded hadith from Dorar.net (الدرر السنية), or attach
grades to hadith you already have.

RUN THIS ON AN UNRESTRICTED NETWORK. Dorar is blocked inside the Claude
sandbox (x-deny-reason: host_not_allowed), so this script is untested against
the live service — it is written from the documented API shape and defends
against schema drift. Verify the first few results by eye before trusting a
large run.

WHY DORAR: it is the best open grading source available. Each record carries
the grade AND the scholar who gave it (المحدث), across far more collections
than the Nine Books. Grades differ between scholars, and Dorar preserves that
rather than flattening it.

INSTALL
    pip install requests

USAGE
    # 1. Search by keyword, save graded results
    python3 dorar_fetch.py --search "الصلاة" --pages 5 --out salah.csv

    # 2. Grade a file you already have (the useful mode)
    python3 dorar_fetch.py --grade-file kabir.csv --text-col arabic_text \\
                           --out kabir_graded.csv

    # 3. Only keep authentic
    python3 dorar_fetch.py --search "الزكاة" --pages 3 --sahih-only --out z.csv

BE CONSIDERATE
    Dorar is a free scholarly service. Default rate limit is 1 req/sec.
    Do not lower --delay below 0.5. For ~90k hadith expect ~24h; run in
    batches with --start/--limit and keep the cache file between runs.
"""

import argparse, csv, json, os, re, sys, time, unicodedata

try:
    import requests
except ImportError:
    sys.exit('pip install requests')

# Community API proxy for dorar.net. If it is down, set --base to another
# mirror; the parsing below only assumes a JSON body with a "data" list.
DEFAULT_BASE = 'https://dorar-hadith-api.vercel.app/api/v1'
CACHE_PATH = 'dorar_cache.json'

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'hadith-research-script/1.0'})


# ------------------------------------------------------------------ arabic
def strip_diacritics(t):
    return re.sub(r'[\u064B-\u0652\u0640\u0670\u0653-\u0655]', '', t or '')

def normalise(t):
    t = strip_diacritics(unicodedata.normalize('NFKC', t or ''))
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'[ىي]', 'ي', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'[ؤئ]', 'و', t)
    t = re.sub(r'[^\u0621-\u064A ]', ' ', t)
    return ' '.join(t.split())

STOP = set(('حدثنا حدثني اخبرنا اخبرني انبانا قال قالت قالوا عن بن ابن ابي ابو ثنا نا '
            'سمعت رضي الله عنه عنها عنهم وسلم عليه صلي رسول النبي ان اني انه وقال وعن '
            'يا ما لا من في علي الي هذا هذه ذلك كان كانت وهو وهي ثم قد وقد به له').split())

def tokens(t):
    return set(w for w in normalise(t).split() if w not in STOP and len(w) > 2)


def classify(grade_ar):
    """Map Dorar's Arabic verdict onto coarse buckets."""
    g = normalise(grade_ar)
    if not g:                                    return 'Ungraded'
    if 'موضوع' in g or 'مكذوب' in g:              return "Mawdu' (fabricated)"
    if 'باطل' in g:                               return "Batil (false)"
    if 'لا اصل له' in g:                          return 'No basis'
    if 'ضعيف' in g or 'منكر' in g or 'شاذ' in g:   return "Da'if (weak)"
    if 'حسن' in g and 'صحيح' in g:                return 'Hasan Sahih'
    if 'حسن' in g:                                return 'Hasan (good)'
    if 'صحيح' in g or 'ثابت' in g:                return 'Sahih (authentic)'
    if 'اسناده جيد' in g or 'جيد' in g:           return 'Jayyid (good chain)'
    return 'Other: ' + grade_ar[:40]


# ------------------------------------------------------------------ network
def get_json(url, params=None, retries=4, delay=1.0):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 429:                       # rate limited
                wait = delay * (2 ** attempt) + 5
                print(f'  429 — backing off {wait:.0f}s', file=sys.stderr)
                time.sleep(wait); continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f'  ! {e}', file=sys.stderr)
                return None
            time.sleep(delay * (2 ** attempt))
    return None


def parse_records(payload):
    """Dorar wraps results in {'data': [...]}. Field names have changed across
    versions, so accept several spellings and skip anything unrecognisable."""
    if not payload: return []
    data = payload.get('data') if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        data = data.get('hadiths') or data.get('results') or []
    if not isinstance(data, list): return []
    out = []
    for d in data:
        if not isinstance(d, dict): continue
        text  = d.get('hadith') or d.get('text') or ''
        grade = d.get('grade') or d.get('degree') or ''
        if not text: continue
        out.append({
            'text':      ' '.join(str(text).split()),
            'narrator':  d.get('rawi') or d.get('narrator') or '',
            'scholar':   d.get('mohdith') or d.get('muhaddith') or '',
            'book':      d.get('book') or d.get('source') or '',
            'number':    d.get('numberOrPage') or d.get('number') or '',
            'grade_ar':  str(grade),
            'grade':     classify(str(grade)),
            'explain':   d.get('explainGrade') or '',
            'takhrij':   d.get('takhrij') or '',
        })
    return out


def search(term, pages, base, delay, sahih_only=False):
    rows = []
    for p in range(1, pages + 1):
        print(f'  page {p}/{pages} …', file=sys.stderr)
        payload = get_json(f'{base}/site/hadith/search',
                           {'value': term, 'page': p}, delay=delay)
        recs = parse_records(payload)
        if not recs:
            print('  (no more results)', file=sys.stderr); break
        rows.extend(recs)
        time.sleep(delay)
    if sahih_only:
        rows = [r for r in rows if r['grade'].startswith(('Sahih', 'Hasan'))]
    return rows


# ------------------------------------------------------------------ grading
def load_cache():
    if os.path.exists(CACHE_PATH):
        try: return json.load(open(CACHE_PATH, encoding='utf-8'))
        except Exception: pass
    return {}

def save_cache(c):
    json.dump(c, open(CACHE_PATH, 'w', encoding='utf-8'), ensure_ascii=False)


def grade_file(path, text_col, out, base, delay, start=0, limit=None):
    """For each row, query Dorar with a distinctive phrase and keep the
    best text match. Caches by phrase so reruns are cheap."""
    with open(path, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if text_col not in (rows[0] if rows else {}):
        sys.exit(f'column "{text_col}" not found. Available: {list(rows[0].keys())}')

    rows = rows[start:start + limit] if limit else rows[start:]
    cache = load_cache()
    print(f'grading {len(rows)} rows (cache has {len(cache)})', file=sys.stderr)

    for i, row in enumerate(rows):
        text = row.get(text_col, '')
        ts = tokens(text)
        if len(ts) < 4:
            row['dorar_grade'] = 'too short to match'; continue

        # a distinctive middle slice makes a better query than the isnad-heavy opening
        words = normalise(text).split()
        phrase = ' '.join(words[len(words)//3: len(words)//3 + 7]) or ' '.join(words[:7])

        if phrase in cache:
            recs = cache[phrase]
        else:
            recs = parse_records(get_json(f'{base}/site/hadith/search',
                                          {'value': phrase}, delay=delay)) or []
            cache[phrase] = recs
            time.sleep(delay)
            if i % 25 == 0: save_cache(cache)

        best, score = None, 0.0
        for r in recs:
            o = tokens(r['text'])
            if not o: continue
            inter = len(ts & o)
            if not inter: continue
            jac = inter / len(ts | o)
            cov = inter / min(len(ts), len(o))
            s = max(jac, cov * 0.9)
            if s > score: score, best = s, r

        if best and score >= 0.45:
            row['dorar_grade']       = best['grade']
            row['dorar_grade_ar']    = best['grade_ar']
            row['dorar_scholar']     = best['scholar']
            row['dorar_book']        = best['book']
            row['dorar_match_score'] = f'{score:.2f}'
        else:
            row['dorar_grade'] = 'no confident match'
            row['dorar_match_score'] = f'{score:.2f}'

        if (i + 1) % 50 == 0:
            print(f'  {i+1}/{len(rows)}', file=sys.stderr)

    save_cache(cache)
    cols = list(rows[0].keys())
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)

    from collections import Counter
    c = Counter(r.get('dorar_grade', '?') for r in rows)
    print('\n== grades ==', file=sys.stderr)
    for k, v in c.most_common(): print(f'  {v:6d}  {k}', file=sys.stderr)
    print(f'wrote {out}', file=sys.stderr)


def write_csv(rows, out):
    if not rows: print('nothing to write', file=sys.stderr); return
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    from collections import Counter
    c = Counter(r['grade'] for r in rows)
    print(f'\nwrote {len(rows)} rows -> {out}', file=sys.stderr)
    for k, v in c.most_common(): print(f'  {v:6d}  {k}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--search', help='Arabic search term')
    ap.add_argument('--pages', type=int, default=3)
    ap.add_argument('--sahih-only', action='store_true')
    ap.add_argument('--grade-file', help='CSV of hadith to attach grades to')
    ap.add_argument('--text-col', default='arabic_text')
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--out', default='dorar_out.csv')
    ap.add_argument('--base', default=DEFAULT_BASE)
    ap.add_argument('--delay', type=float, default=1.0,
                    help='seconds between requests; do not go below 0.5')
    a = ap.parse_args()

    if a.delay < 0.5:
        sys.exit('--delay below 0.5s is inconsiderate to a free service; aborting.')

    if a.search:
        write_csv(search(a.search, a.pages, a.base, a.delay, a.sahih_only), a.out)
    elif a.grade_file:
        grade_file(a.grade_file, a.text_col, a.out, a.base, a.delay, a.start, a.limit)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
