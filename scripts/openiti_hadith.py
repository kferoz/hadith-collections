#!/usr/bin/env python3
"""
openiti_hadith.py — pull classical Arabic hadith collections from the OpenITI
corpus on GitHub, filter to Prophet-attributed (marfu') reports, deduplicate,
and assign topics.

WHY THIS EXISTS
  Collections beyond the Nine Books (Tabarani, Ibn Hibban, Bayhaqi, Ibn Abi
  Shayba, al-Hakim, ...) are not in any of the ready-made hadith JSON datasets.
  They ARE in OpenITI, a scholarly corpus of classical Arabic texts hosted on
  GitHub — reachable even from restricted networks that allow only github.com.

USAGE
  python3 openiti_hadith.py --list 0375AH              # what's in a repo
  python3 openiti_hadith.py --list 0375AH --grep Tabarani
  python3 openiti_hadith.py --extract 0375AH --work MucjamKabir --out kabir
  python3 openiti_hadith.py --batch                    # all preset collections

REPOS ARE NAMED BY AUTHOR DEATH DATE, rounded up to a 25-year bucket:
  Ibn Abi Shayba d.235  -> 0250AH        Ibn Khuzayma d.311 -> 0325AH
  Abd ar-Razzaq d.211   -> 0225AH        Ibn Hibban   d.354 -> 0375AH
  Ibn Rahwayh   d.238   -> 0250AH        Tabarani     d.360 -> 0375AH
  al-Bazzar     d.292   -> 0300AH        Daraqutni    d.385 -> 0400AH
  Abu Ya'la     d.307   -> 0325AH        al-Hakim     d.405 -> 0425AH
  Tayalisi      d.204   -> 0225AH        al-Bayhaqi   d.458 -> 0475AH

NOTE ON GRADES: OpenITI gives you the TEXT, not authenticity gradings.
Nothing here grades hadith. See the companion notes on Dorar for that.
"""

import argparse, io, json, os, re, sys, urllib.request, zipfile
from collections import Counter, defaultdict

CACHE = os.path.expanduser('~/.openiti_cache')
os.makedirs(CACHE, exist_ok=True)

# Collections worth pulling: (repo, work-id fragment, English title, died AH)
PRESETS = [
    # (repo, path-fragment that pins BOTH author and work, English title, died AH)
    ('0225AH', 'CabdRazzaqSancani.Musannaf', "Musannaf Abd ar-Razzaq",       211),
    ('0225AH', 'Tayalisi.Musnad',           "Musnad at-Tayalisi",           204),
    ('0225AH', 'Shafici.Musnad',            "Musnad ash-Shafi'i",           204),
    ('0250AH', 'IbnAbiShayba.Musannaf',     "Musannaf Ibn Abi Shayba",      235),
    ('0250AH', 'IbnMansurKhurasani.Sunan',   "Sunan Sa'id ibn Mansur",       227),
    ('0300AH', 'Bazzar.BahrZakhkhar',       "Musnad al-Bazzar (al-Bahr az-Zakhkhar)", 292),
    ('0325AH', 'AbuYaclaMawsili.Musnad',     "Musnad Abu Ya'la",             307),
    ('0325AH', 'IbnKhuzaymaNaysaburi.Sahih', "Sahih Ibn Khuzayma",           311),
    ('0375AH', 'Tabarani.MucjamKabir',      "al-Mu'jam al-Kabir",           360),
    ('0375AH', 'Tabarani.MucjamAwsat',      "al-Mu'jam al-Awsat",           360),
    ('0375AH', 'Tabarani.MucjamSaghir',     "al-Mu'jam as-Saghir",          360),
    ('0400AH', 'Daraqutni.Sunan',           "Sunan ad-Daraqutni",           385),
    ('0425AH', 'HakimNaysaburi.Mustadrak',   "al-Mustadrak ala as-Sahihayn", 405),
    ('0475AH', 'Bayhaqi.SunanKubra',        "as-Sunan al-Kubra (Bayhaqi)",  458),
    ('0475AH', 'Bayhaqi.ShucabIman',        "Shu'ab al-Iman",               458),
]



# ---------------------------------------------------------------- download
def fetch_repo(repo):
    """Download an OpenITI death-date repo as a zip (cached).  ~50-150 MB each."""
    path = os.path.join(CACHE, f'{repo}.zip')
    if os.path.exists(path) and os.path.getsize(path) > 100000:
        return path
    for branch in ('master', 'main'):
        url = f'https://codeload.github.com/OpenITI/{repo}/zip/refs/heads/{branch}'
        try:
            print(f'  downloading {repo} ({branch}) …', file=sys.stderr)
            with urllib.request.urlopen(url, timeout=600) as r, open(path, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    f.write(chunk)
            if os.path.getsize(path) > 100000:
                return path
        except Exception as e:
            print(f'    {branch} failed: {e}', file=sys.stderr)
    raise SystemExit(f'could not download {repo}')


def list_works(repo, grep=None):
    z = zipfile.ZipFile(fetch_repo(repo))
    works = defaultdict(int)
    for n in z.namelist():
        p = n.split('/')
        if len(p) > 4 and not n.endswith(('/', '.yml', '.md')):
            works[(p[2], p[3])] += z.getinfo(n).file_size
    rows = sorted(works.items(), key=lambda kv: -kv[1])
    for (author, work), size in rows:
        if grep and grep.lower() not in work.lower() and grep.lower() not in author.lower():
            continue
        print(f'  {size/1048576:8.2f} MB  {author:32s} {work}')


# ---------------------------------------------------------------- parsing
META_END = '#META#Header#End#'

def read_meta(raw):
    meta = {}
    for line in raw.split('\n'):
        if line.startswith('#META#') and '::' in line:
            k, v = line.split('::', 1)
            meta[k.replace('#META#', '').strip()] = v.strip()
        if META_END in line: break
    return meta


def split_hadiths(body):
    """OpenITI texts come in two markup dialects depending on the source
    library.  '# N ' numbered entries (JK/Shia editions), or '### ' section
    markers (Shamela editions).  Try both, keep whichever yields more."""
    body = re.sub(r'\bPageV\d+P\d+\b', ' ', body)
    body = re.sub(r'\bms\d+\b', ' ', body)
    body = body.replace('~~', ' ')
    lines = body.split('\n')

    def by_numbered():
        out, cur, num = [], [], None
        for line in lines:
            m = re.match(r'^#\s*(\d+)\s+(.*)', line)
            if m:
                if cur: out.append((num, ' '.join(cur)))
                num, cur = int(m.group(1)), [m.group(2)]
            elif re.match(r'^#+\s*\|', line) or line.startswith('###'):
                if cur: out.append((num, ' '.join(cur)))
                cur, num = [], None
            elif cur:
                cur.append(line)
        if cur: out.append((num, ' '.join(cur)))
        return out

    def by_sections():
        out, cur, i = [], [], 0
        for line in lines:
            if line.startswith('###'):
                if cur: i += 1; out.append((i, ' '.join(cur)))
                cur = []
                rest = re.sub(r'^#+\s*\|*\s*', '', line)
                if rest.strip(): cur.append(rest)
            else:
                cur.append(line)
        if cur: out.append((i + 1, ' '.join(cur)))
        return out

    best = max(by_numbered(), by_sections(), key=len)
    return [(n, ' '.join(t.split())) for n, t in best if t and len(t.split()) > 5]


# ---------------------------------------------------------------- filtering
def dia(t):
    return re.sub(r'[\u064B-\u0652\u0640\u0670\u0653-\u0655]', '', t or '')

def norm(t):
    t = dia(t)
    t = re.sub(r'[إأآا]', 'ا', t); t = re.sub(r'[ىي]', 'ي', t)
    t = re.sub(r'ة', 'ه', t);      t = re.sub(r'ؤ', 'و', t); t = re.sub(r'ئ', 'ي', t)
    return t

PROPHET = [norm(x) for x in
           ['صلى الله عليه وسلم', 'رسول الله', 'النبي', 'نبي الله']]

ISNAD = set(('حدثنا حدثني اخبرنا اخبرني انبانا قال قالت قالوا عن بن ابن ابي ابو ثنا نا '
             'سمعت رضي الله عنه عنها عنهم وسلم عليه صلى رسول النبي ان اني انه وقال وعن '
             'يا ما لا من في على الي هذا هذه ذلك كان كانت وهو وهي ثم قد لقد وقد به له '
             'بها لها اليه فيه منه انا نحن هم هو هي التي الذي').split())

BLESSING = re.compile(norm('صلي الله عليه وسلم').replace(' ', r'\\s+'))

def content_tokens(t):
    t = BLESSING.sub(' ', norm(t))          # drop the ubiquitous blessing formula
    t = re.sub(r'[^\u0621-\u064A ]', ' ', t)
    return [w for w in t.split() if w not in ISNAD and len(w) > 2]

NARRATION_CUE = [norm(x) for x in
    ['حدثنا', 'حدثني', 'اخبرنا', 'اخبرني', 'انبانا', 'سمعت', 'ثنا', 'عن']]

def is_marfu(text):
    """Prophet-attributed AND shaped like a narration (has a chain cue).
    Without the second test, prefaces and indices that merely mention the
    Prophet get swept in."""
    n = norm(text)
    if not any(p in n for p in PROPHET):
        return False
    return any(c in n for c in NARRATION_CUE)


def dedupe(items):
    """Fuzzy near-duplicate merge on content tokens (same thresholds as the
    English pipeline: jaccard>=.48, or coverage>=.72 with jaccard>=.35)."""
    tk = [set(content_tokens(t)) for _, t in items]
    df = Counter()
    for s in tk: df.update(s)
    kept, ktok, idx = [], [], defaultdict(list)
    for i, (num, text) in enumerate(items):
        ts = tk[i]
        if len(ts) < 5: continue
        rare = sorted([w for w in ts if df[w] <= 500], key=lambda w: df[w])[:6]
        cand = set()
        for w in rare: cand.update(idx[w])
        dup = None
        for j in cand:
            o = ktok[j]; inter = len(ts & o)
            if not inter: continue
            jac = inter / len(ts | o); cov = inter / min(len(ts), len(o))
            if jac >= 0.48 or (cov >= 0.72 and jac >= 0.35):
                dup = j; break
        if dup is not None:
            kept[dup]['dups'] += 1
            continue
        kept.append({'n': num, 'ar': text, 'dups': 0}); ktok.append(ts)
        for w in rare: idx[w].append(len(kept) - 1)
    return kept, ktok


TOPICS_AR = {
 "Faith & Creed": "ايمان اسلام شهاده توحيد شرك كفر عقيده يؤمن امن",
 "Prayer (Salah)": "الصلاه ركعه ركعتين سجد سجود قبله تكبير مكتوبه صلاه",
 "Purity & Wudu": "وضوء توضا طهاره غسل تيمم نجس جنابه حيض استنجاء سواك",
 "Adhan & the Mosque": "اذان مؤذن مسجد اقامه بلال",
 "Quran & Recitation": "قران قرا يقرا سوره ايه تلاوه نزلت انزل وحي",
 "Dhikr & Supplication": "ذكر دعاء يدعو سبحان الحمد استغفار تسبيح اعوذ",
 "Zakah & Charity": "زكاه صدقه تصدق انفق نفقه صدقات",
 "Fasting & Ramadan": "صوم صام يصوم رمضان افطار سحور اعتكاف",
 "Hajj & Umrah": "حج عمره احرام طواف كعبه عرفه مني منسك تلبيه لبيك هدي",
 "Night & Voluntary Prayer": "وتر تهجد قيام الليل نافله تطوع ضحي",
 "Eid & Sacrifice": "عيد اضحي ذبح نحر اضحيه قربان",
 "Repentance & Forgiveness": "توبه تاب استغفر غفر مغفره رحمه عفا",
 "Parents": "والد والده الوالدين ابوه امه بر عقوق",
 "Marriage & Spouses": "نكاح تزوج زوج زوجه مهر صداق طلاق عده خلع",
 "Women": "امراه نساء المراه بنت جاريه",
 "Children & Upbringing": "ولد اولاد صبي غلام يتيم رضاع فطره عقيقه ختان",
 "Relatives & Kinship": "رحم القرابه قطيعه صله عم خال اخ اخت",
 "Neighbours": "جار جيران",
 "Orphans & the Weak": "يتيم مسكين فقير ضعيف سائل",
 "Servants & Freeing Slaves": "رقبه اعتق عتق مملوك خادم مكاتب",
 "Brotherhood & Friendship": "اخوه سلام مصافحه صاحب صديق الفه",
 "Guests & Hospitality": "ضيف ضيافه وليمه طعام دعوه",
 "Character & Manners": "خلق اخلاق ادب حسن معروف خير الناس",
 "Truthfulness & Lying": "صدق كذب كاذب غش خيانه امانه",
 "Anger & Patience": "غضب صبر حلم يصبر",
 "Humility & Pride": "تواضع كبر متكبر خيلاء عجب",
 "Speech & Backbiting": "غيبه نميمه لسان سب شتم لعن سكت صمت",
 "Envy & Suspicion": "حسد ظن تجسس بغض شحناء",
 "Mercy & Kindness": "رحم رحمه رفق لين شفقه",
 "Modesty & Dress": "حياء ستر حجاب عوره ثوب لباس حرير خاتم",
 "Major Sins": "كبائر اكبر الكبائر موبقات",
 "Adultery & Chastity": "زنا زني فاحشه عفه فجور",
 "Alcohol & Intoxicants": "خمر مسكر شرب نبيذ سكر",
 "Theft & Property": "سرق سارق سرقه غصب نهب مال",
 "Usury & Interest": "ربا الربا صرف",
 "Oppression & Injustice": "ظلم ظالم جور بغي عدوان",
 "Bloodshed & Murder": "قتل دم ديه قصاص دماء",
 "Magic & Superstition": "سحر ساحر كاهن تميمه طيره فال عين",
 "Trade & Business": "بيع باع اشتري تجاره سوق ربح كيل وزن شراء",
 "Debt & Loans": "دين قرض سلف رهن مفلس غريم",
 "Inheritance & Wills": "ميراث ورث فرائض وصيه وارث",
 "Justice & Judgement": "قضي قاضي حكم شهاده بينه حد حدود جلد رجم عقوبه",
 "Leadership & Governance": "امام امير خليفه ولاه طاعه بيعه راع رعيه سلطان",
 "Oaths & Vows": "يمين حلف قسم نذر كفاره",
 "Work & Livelihood": "عمل كسب اجر اجير رزق حرث زرع صناعه",
 "Death & Burial": "موت مات ميت جنازه قبر دفن كفن عزاء",
 "The Grave & Barzakh": "قبر عذاب القبر فتنه القبر ملكان",
 "Day of Judgement": "قيامه حساب ميزان اخره يوم القيامه بعث",
 "Paradise": "جنه الجنه فردوس حور نعيم",
 "Hellfire": "نار جهنم عذاب سعير جحيم",
 "Resurrection & Intercession": "شفاعه يشفع بعث حشر صراط حوض كوثر",
 "Signs of the End Times": "دجال الساعه اشراط فتنه ياجوج ماجوج المهدي",
 "Angels & the Unseen": "ملك ملائكه جبريل جن شيطان ابليس غيب",
 "Destiny & Decree": "قدر قضاء مقدور كتب الله لوح",
 "Trials & Illness": "بلاء مرض سقم وجع طاعون حمي ابتلي مصيبه",
 "Knowledge & Scholars": "علم عالم تعلم فقه طلب العلم جهل",
 "Prophets & Past Peoples": "موسي عيسي ابراهيم نوح ادم سليمان داود يوسف يونس فرعون بني اسرائيل",
 "Dreams & Visions": "رؤيا حلم منام تعبير",
 "Medicine & Healing": "دواء شفاء طب حجامه رقيه عسل كي",
 "Food & Drink": "طعام اكل شرب لحم خبز لبن تمر ماء ثمر",
 "Animals": "بعير ناقه فرس شاه غنم بقره كلب هره طير حمار ابل",
 "Travel & Migration": "سفر مسافر هجره ركب راحله قصر الصلاه",
 "Jihad & Battles": "جهاد غزو قتال سريه شهيد عدو سيف رمح غنيمه اسير",
 "Treaties & Non-Muslims": "يهود نصاري مشرك كافر منافق عهد ذمه جزيه اهل الكتاب",
 "Time, Days & Nights": "جمعه يوم ليله هلال شهر فجر مغرب سحر",
}
TOPIC_SETS = {k: set(v.split()) for k, v in TOPICS_AR.items()}

def assign_topics(tokset):
    sc = Counter()
    for name, kws in TOPIC_SETS.items():
        hits = 2 * len(tokset & kws)            # exact match weighs double
        for k in kws:                            # crude morphological match
            if len(k) >= 5:
                for w in tokset:
                    if w != k and len(w) >= 5 and (w.startswith(k[:5]) or k.startswith(w[:5])):
                        hits += 1; break
        if hits: sc[name] = hits
    strong = [t for t, s in sc.most_common() if s >= 4][:4]
    if not strong: strong = [t for t, s in sc.most_common(2) if s >= 2]
    if not strong: strong = [t for t, _ in sc.most_common(1)] or ['Other Narrations']
    return strong


# ---------------------------------------------------------------- extract
def extract(repo, work_frag, out_stub, title=None):
    z = zipfile.ZipFile(fetch_repo(repo))
    files = [n for n in z.namelist()
             if work_frag.lower() in n.lower()
             and not n.endswith(('/', '.yml', '.md', '.completed', '.inProgress'))]
    if not files:
        print(f'  !! no files matching "{work_frag}" in {repo}'); return None
    want = work_frag.split('.')[0].lower()
    files = [f for f in files if want in f.lower()]     # pin the author
    if not files:
        print(f'  !! "{work_frag}" matched nothing after author check'); return None
    # Editions differ in markup quality; score each by how many hadith-shaped
    # entries it actually yields, and keep the best.  (Picking by file size
    # alone silently selects unparseable editions.)
    best = (None, None, [], 0)
    for n in sorted(files, key=lambda x: -z.getinfo(x).file_size)[:6]:
        try:
            r = z.read(n).decode('utf-8', errors='replace')
        except Exception:
            continue
        it = split_hadiths(r.split(META_END)[-1])
        if len(it) > best[3]:
            best = (n, r, it, len(it))
    target, raw, items, _ = best
    if not target:
        print(f'  !! nothing parseable for "{work_frag}"'); return None
    meta = read_meta(raw)
    marfu = [(n, t) for n, t in items if is_marfu(t) and len(t) > 40]
    kept, ktok = dedupe(marfu)
    for i, r in enumerate(kept):
        r['t'] = assign_topics(ktok[i])

    rec = {
        'title_en': title or work_frag,
        'title_ar': meta.get('020.BookTITLE', ''),
        'author_ar': meta.get('010.AuthorNAME', ''),
        'died_AH': meta.get('011.AuthorDIED', ''),
        'source_file': os.path.basename(target),
        'openiti_repo': repo,
        'entries_parsed': len(items),
        'marfu': len(marfu),
        'unique': len(kept),
        'grades': 'NONE - OpenITI provides text only, no authenticity gradings',
        'hadiths': kept,
    }
    with open(f'{out_stub}.json', 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False)
    import csv
    with open(f'{out_stub}.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['collection', 'seq_no', 'grade', 'topics', 'arabic_text', 'merged_dups'])
        for r in kept:
            w.writerow([rec['title_en'], r['n'], 'UNGRADED',
                        '; '.join(r['t']), r['ar'], r['dups']])
    print(f"  {rec['title_en']:32s} parsed {len(items):6d} -> marfu {len(marfu):6d} -> unique {len(kept):6d}")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', metavar='REPO')
    ap.add_argument('--grep')
    ap.add_argument('--extract', metavar='REPO')
    ap.add_argument('--work')
    ap.add_argument('--out', default='out')
    ap.add_argument('--batch', action='store_true')
    a = ap.parse_args()

    if a.list:
        list_works(a.list, a.grep)
    elif a.extract:
        if not a.work: raise SystemExit('--extract needs --work')
        extract(a.extract, a.work, a.out)
    elif a.batch:
        os.makedirs('openiti_out', exist_ok=True)
        summary = []
        for repo, frag, title, died in PRESETS:
            print(f'== {title} ({repo}/{frag})')
            try:
                r = extract(repo, frag, f'openiti_out/{frag}_{died}', title)
                if r: summary.append((title, died, r['entries_parsed'], r['marfu'], r['unique']))
            except Exception as e:
                print(f'  !! {e}')
        print('\n== SUMMARY ==')
        for t, d, p, m, u in summary:
            print(f'  {t:32s} d.{d:<4} parsed {p:6d}  marfu {m:6d}  unique {u:6d}')
        print(f'  TOTAL unique: {sum(s[4] for s in summary)}')
    else:
        ap.print_help()

if __name__ == '__main__':
    main()
