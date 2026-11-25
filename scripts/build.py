#!/usr/bin/env python3
"""Собирает профиль GitHub в стиле Material Design 3: SVG-карточки и блоки README.

  python scripts/build.py            боевой запуск, данные берутся из GitHub API
  python scripts/build.py --static   только статичные карточки, без сети
  python scripts/build.py --demo     выдуманные данные, для превью

Всё, что можно менять руками, лежит в блоке «Настройки» ниже.
"""
import html, json, math, os, re, sys, urllib.request
from datetime import date, timedelta
from pathlib import Path

OWNER = os.environ.get("OWNER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Pivozavr7"

# ───────────────────────────── Настройки ─────────────────────────────
BIO = "Не пишу руками на Rust и Zig"
STACK = ["Rust", "Zig", "Slint"]
VIBE = ("Не вайбкод", "Всё сам")                             # заголовок и подпись строки в баннере; справа три галочки
SITE = "https://pivozavr7.github.io"                         # куда ведёт баннер
LINKS = [                                                    # иконки: send, globe
    dict(icon="send",  title="Telegram", sub="t.me/pkowwww",        url="https://t.me/pkowwww"),
    dict(icon="globe", title="Сайт",     sub="pivozavr7.github.io", url=SITE),
]
REPO_LIMIT = 4        # сколько проектов показывать (берутся закреплённые, иначе недавние)
SNAKE = True          # карточка «активность»: календарь коммитов + змейка, ползающая только по занятым дням
BANNER_ALT = f"{OWNER}: {BIO}. {VIBE[0]}, {VIBE[1]}"
# ─────────────────────────────────────────────────────────────────────

W = 640
# Цвета: тёмная схема Material Design 3, seed — зелёный. Имена как в спецификации MD3.
C = dict(
    surface_c="#1b201b",       # surface container: фон карточек
    surface_ch="#252a25",      # surface container high: вложенные блоки
    on_surface="#e0e4dd", on_variant="#c1c9bf", outline_v="#414941",
    primary="#b6f1b8", on_primary="#0a3917", primary_c="#245031", on_primary_c="#c9f5cb",
    secondary_c="#3b4b3d", on_secondary_c="#d2e8d3",
)
DOTS = ["#252a25", "#245031", "#356b43", "#4f8c5b", "#6fb07a"]   # календарь: пусто + 4 уровня
FONT = "Roboto,'Google Sans','Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
# Типографика MD3: headline-large, body-large/medium, title-medium/small, label-large/medium
CSS = (f"text{{font-family:{FONT}}}"
       f".hl{{font-size:32px;font-weight:500;fill:{C['on_surface']}}}"
       f".bl{{font-size:16px;fill:{C['on_variant']};letter-spacing:.5px}}"
       f".tm{{font-size:16px;font-weight:500;fill:{C['on_surface']};letter-spacing:.15px}}"
       f".tl{{font-size:14px;font-weight:500;fill:{C['on_variant']};letter-spacing:.1px}}"
       f".bm{{font-size:14px;fill:{C['on_variant']};letter-spacing:.25px}}"
       f".lm{{font-size:12px;font-weight:500;fill:{C['on_variant']};letter-spacing:.5px}}"
       f".ll{{font-size:14px;font-weight:500;letter-spacing:.1px}}"
       f".mo{{font-size:10px;fill:{C['on_variant']};letter-spacing:.3px}}"
       f".v{{font-size:22px;font-weight:500;fill:{C['primary']}}}")
# Анимации: галочки «выскакивают» и дорисовываются по очереди, кольцо пульсирует.
# По умолчанию всё видимо, так что при prefers-reduced-motion остаётся статичная картинка.
CSS += ("@keyframes pop{0%{opacity:0;transform:scale(.4)}12%{opacity:1;transform:scale(1.18)}20%{transform:scale(1)}88%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(1)}}"
        "@keyframes draw{0%,6%{stroke-dashoffset:22}24%,88%{stroke-dashoffset:0}100%{stroke-dashoffset:22}}"
        "@keyframes ring{0%{opacity:.6;transform:scale(1)}70%,100%{opacity:0;transform:scale(1.5)}}"
        ".pop{transform-box:fill-box;transform-origin:center;animation:pop 5s cubic-bezier(.2,0,0,1) infinite backwards}"
        ".tick{stroke-dasharray:22;animation:draw 5s ease-out infinite backwards}"
        ".ring{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 2.5s ease-out infinite}"
        ".d1{animation-delay:.2s}.d2{animation-delay:.45s}.d3{animation-delay:.7s}"
        "@media (prefers-reduced-motion:reduce){.pop,.tick,.ring{animation:none}}")
GREENS = ["#b6f1b8", "#8ec993", "#679f6e", "#8b938a", "#575f57"]
SNAKE_BODY = ["#8ec993", "#679f6e", "#575f57"]                   # сегменты тела за головой
ICONS = {
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "repo": '<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
    "ext": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "star": '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21.1 7 14.2 2 9.3l6.9-1z"/>',
}
MONTHS = "янв фев мар апр мая июн июл авг сен окт ноя дек".split()

esc = lambda s: html.escape(str(s), quote=True)
fmt = lambda n: f"{int(n):,}".replace(",", "\u202f")
clip = lambda s, n: s if len(s) <= n else s[:n - 1].rstrip() + "…"
def ru_date(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]} {y}"

def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title><style>{CSS}</style>{body}</svg>\n')

def ico(name, x, y, size, color):
    return (f'<g transform="translate({x} {y}) scale({size / 24:.3f})" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')

def card(w, h, r=16, fill=None, x=0, y=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or C["surface_c"]}"/>'

def tw(s, per=7.6):                       # грубая оценка ширины текста 14px
    return int(len(s) * per)

def go(h):                                # стрелка «открыть»: карточка целиком кликабельна
    return ico("ext", W - 16 - 18, (h - 18) // 2, 18, C["outline_v"])

def leading(name, x, y):                  # круглая иконка слева, как в MD3 list item
    return (f'<circle cx="{x + 20}" cy="{y + 20}" r="20" fill="{C["primary_c"]}"/>'
            + ico(name, x + 10, y + 10, 20, C["on_primary_c"]))

# ───────────────────────────── Карточки ─────────────────────────────
def check_badge(cx, cy, r, cls):          # зелёный кружок с галочкой, анимированный
    return (f'<g class="pop {cls}"><circle cx="{cx}" cy="{cy}" r="{r}" fill="{C["primary"]}"/>'
            f'<path class="tick {cls}" d="M{cx - 5} {cy + .5}l3.4 3.5 7.1-7.5" fill="none" stroke="{C["on_primary"]}" '
            f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>')

def leading_check(x, y):                  # иконка слева: круг с пульсирующим кольцом и рисующейся галочкой
    return (f'<circle class="ring" cx="{x + 20}" cy="{y + 20}" r="20" fill="none" stroke="{C["primary"]}" stroke-width="2"/>'
            f'<circle cx="{x + 20}" cy="{y + 20}" r="20" fill="{C["primary_c"]}"/>'
            f'<g transform="translate({x + 10} {y + 10}) scale(.833)"><path class="tick" d="M5 12.5l4.5 4.5L19 7.5" fill="none" '
            f'stroke="{C["on_primary_c"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>')

def banner():
    h = 232
    body = card(W, h, 28)
    body += (f'<circle cx="{W - 60}" cy="60" r="28" fill="{C["primary_c"]}"/>'
             f'<text x="{W - 60}" y="71" text-anchor="middle" style="font-size:30px;font-weight:500" '
             f'fill="{C["on_primary_c"]}">{esc(OWNER[:1].upper())}</text>')
    body += f'<text class="hl" x="32" y="66">{esc(OWNER)}</text><text class="bl" x="32" y="94">{esc(BIO)}</text>'
    x = 32
    for s in STACK:                       # assist chips: высота 32, скругление 8, обводка outline-variant
        cw = tw(s) + 24
        body += (f'<rect x="{x + .5}" y="112.5" width="{cw - 1}" height="31" rx="8" fill="none" stroke="{C["outline_v"]}"/>'
                 f'<text class="ll" x="{x + 12}" y="133" fill="{C["on_surface"]}">{esc(s)}</text>')
        x += cw + 8
    # строка «Не вайбкод»: список с анимированной галочкой слева и тремя галочками справа
    body += card(W - 32, 56, 16, C["surface_ch"], 16, 160)
    body += leading_check(28, 168)
    body += f'<text class="tm" x="84" y="184">{esc(VIBE[0])}</text><text class="bm" x="84" y="203">{esc(VIBE[1])}</text>'
    for i, cls in enumerate(("d1", "d2", "d3")):
        body += check_badge(W - 28 - 12 - (2 - i) * 32, 188, 12, cls)
    return svg(W, h, body, BANNER_ALT)

def link_card(it):
    h = 72
    body = (card(W, h) + leading(it["icon"], 16, 16) + f'<text class="tm" x="72" y="34">{esc(it["title"])}</text>'
            f'<text class="bm" x="72" y="54">{esc(it["sub"])}</text>' + go(h))
    return svg(W, h, body, f'{it["title"]}: {it["sub"]}')

def repo_card(r):
    h = 96
    desc = clip(r.get("desc") or "Без описания", 58)
    meta, x = "", 72
    if r.get("lang"):
        meta += f'<circle cx="{x + 4}" cy="76" r="4" fill="{C["primary"]}"/><text class="lm" x="{x + 14}" y="80">{esc(r["lang"])}</text>'
        x += 14 + int(len(r["lang"]) * 7.2) + 18
    if r.get("stars"):
        meta += ico("star", x, 68, 13, C["on_variant"]) + f'<text class="lm" x="{x + 19}" y="80">{fmt(r["stars"])}</text>'
        x += 19 + len(fmt(r["stars"])) * 7 + 18
    if r.get("pushed"):
        meta += f'<text class="lm" x="{x}" y="80">обновлён {ru_date(r["pushed"])}</text>'
    body = (card(W, h) + leading("repo", 16, 16) + f'<text class="tm" x="72" y="34">{esc(r["name"])}</text>'
            f'<text class="bm" x="72" y="54">{esc(desc)}</text>' + meta + go(h))
    return svg(W, h, body, f'Репозиторий {r["name"]}: {desc}')

def top_langs(d):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:5]
    tot = sum(v for _, v in items) or 1
    return [(k, v / tot * 100) for k, v in items]

def stats_svg(d):
    gap = 16
    cw = (W - gap) // 2
    rows = [("Репозитории", fmt(d["repos"]), True)]
    if d.get("commits") is not None: rows.append(("Коммиты", fmt(d["commits"]), True))
    if d.get("stars"):     rows.append(("Звёзды", fmt(d["stars"]), True))
    if d.get("prs"):       rows.append(("Pull request’ы", fmt(d["prs"]), True))
    if d.get("followers"): rows.append(("Подписчики", fmt(d["followers"]), True))
    if d.get("pushed"):    rows.append(("Последний пуш", ru_date(d["pushed"]), False))  # дату пишем мельче
    langs = top_langs(d)
    ph = max(len(rows) * 52 + 16, 48 + len(langs) * 32)
    rh = (ph - 16) / len(rows)
    body = card(cw, ph, 20)
    for i, (t, v, big) in enumerate(rows):
        y = 8 + i * rh
        if i: body += f'<line x1="16" x2="{cw - 16}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["outline_v"]}"/>'
        mid = y + rh / 2
        vc = "v" if big else "tm"
        style = "" if big else f' style="fill:{C["primary"]}"'
        body += (f'<text class="tm" x="16" y="{mid + 5:.1f}">{esc(t)}</text>'
                 f'<text class="{vc}"{style} x="{cw - 16}" y="{mid + (7 if big else 5):.1f}" text-anchor="end">{esc(v)}</text>')
    bw, seg_gap = cw - 32, 2
    body += f'<g transform="translate({cw + gap} 0)">{card(cw, ph, 20)}'
    x = 16.0                              # сегментированная полоса: скруглённые сегменты с зазором 2px
    for i, (_, p) in enumerate(langs):
        w = max(p / 100 * bw - seg_gap, 3)
        body += f'<rect x="{x:.1f}" y="16" width="{w:.1f}" height="8" rx="4" fill="{GREENS[i]}"/>'
        x += w + seg_gap
    for i, (k, p) in enumerate(langs):
        y = 48 + i * 32
        body += (f'<circle cx="22" cy="{y - 4}" r="4" fill="{GREENS[i]}"/>'
                 f'<text class="tl" x="36" y="{y}" style="fill:{C["on_surface"]}">{esc(k)}</text>'
                 f'<text class="bm" x="{cw - 16}" y="{y}" text-anchor="end">{"&lt;1" if p < 1 else f"{p:.0f}"}%</text>')
    body += '</g>'
    alt = (f'{d["repos"]} репозиториев'
           + (f', {fmt(d["commits"])} коммитов' if d.get("commits") is not None else "")
           + ". Языки: " + ", ".join(f"{k} {p:.0f}%" for k, p in langs))
    return svg(W, ph + 2, body, alt), alt

# ─────────────────────── Змейка по коммитам ───────────────────────
def snake_svg(weeks):
    """Карточка «активность»: календарь коммитов, обрезанный до активного периода.

    Змейка ползёт строго по дням с коммитами, в хронологическом порядке,
    и съедает их. По пустым клеткам не ходит — их не видно в маршруте.
    """
    if not weeks: return None
    grid = [w["contributionDays"] for w in weeks]
    cols = len(grid)
    if not cols: return None
    act = [(c, r, grid[c][r]["contributionCount"]) for c in range(cols) for r in range(7)
           if grid[c][r]["contributionCount"]]
    if not act: return None

    # обрезаем сетку до активного периода (плюс немного контекста, минимум 12 недель)
    c0, c1 = act[0][0], act[-1][0]
    span = c1 - c0 + 1
    if span < 12 and cols > 12:
        c0 = max(0, min(c0 - (12 - span) // 2, cols - 12))
        c1 = c0 + 11
    else:
        c0, c1 = max(0, c0), min(c1, cols - 1)
    n = c1 - c0 + 1

    inner = W - 32
    gap = 3 if n <= 45 else 2
    cell = max(5, min(13, (inner - (n - 1) * gap) // n))
    gw = n * cell + (n - 1) * gap
    gh = 7 * cell + 6 * gap
    mtop = 14 if n >= 12 else 0                       # строка с названиями месяцев
    h = 16 + mtop + gh + 16
    x0 = 16 + (inner - gw) // 2
    y0 = 16 + mtop

    def px(c, r):
        return x0 + (c - c0) * (cell + gap), y0 + r * (cell + gap)

    lvl = lambda cnt: 1 if cnt <= 2 else 2 if cnt <= 5 else 3 if cnt <= 9 else 4

    # маршрут змейки: только занятые дни, хронологически; скорость равномерная по пути
    pts = [px(c, r) for c, r, _ in act]
    k = len(pts)
    dist = [0.0]
    for i in range(1, k):
        dist.append(dist[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    total = dist[-1] or 1.0
    dur = max(8000, min(16000, k * 800))              # мс на весь круг
    T = 95.0                                          # % времени на маршрут, дальше короткая пауза
    pct = [d / total * T for d in dist]
    speed = total / (dur * T / 100.0)                 # px за мс
    lag = min((cell + gap) / speed, dur * .4) if speed > 0 else dur * .1   # задержка сегмента тела

    css, body = "", card(W, h, 16)
    if mtop:                                          # подписи месяцев над первыми неделями месяца
        prev = grid[c0 - 1][0]["date"][5:7] if c0 > 0 else ""   # «обрезанный» месяц слева не подписываем
        last_lab = -10
        for c in range(c0, c1 + 1):
            m = grid[c][0]["date"][5:7]
            if m != prev:
                prev = m
                if c - last_lab >= 3:                 # подписи не должны наезжать друг на друга
                    last_lab = c
                    x, _ = px(c, 0)
                    body += f'<text class="mo" x="{x:.0f}" y="{y0 - 5}">{MONTHS[int(m) - 1]}</text>'

    i = 0
    for c in range(c0, c1 + 1):
        for r in range(7):
            cnt = grid[c][r]["contributionCount"]
            x, y = px(c, r)
            rad = max(1.5, cell * .22)
            if cnt:
                body += (f'<rect class="d e{i}" x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" '
                         f'rx="{rad:.1f}" fill="{DOTS[lvl(cnt)]}"/>')
                p = pct[i]
                css += (f".e{i}{{animation:e{i} {dur}ms linear infinite}}"
                        f"@keyframes e{i}{{0%,{p:.2f}%{{fill:{DOTS[lvl(cnt)]}}}"
                        f"{min(p + 2, 100):.2f}%,100%{{fill:{DOTS[0]}}}}}")   # съедена — потухла
                i += 1
            else:
                body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" '
                         f'rx="{rad:.1f}" fill="{DOTS[0]}"/>')

    # голова и тело: одни и те же ключевые кадры, тело просто запаздывает
    stops = "".join(f"{p:.2f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}"
                    for p, (x, y) in zip(pct, pts))
    stops += f"{T:.2f}%,100%{{transform:translate({pts[-1][0]:.1f}px,{pts[-1][1]:.1f}px)}}"
    css += f".sh{{animation:sh {dur}ms linear infinite}}@keyframes sh{{{stops}}}"
    rad = max(1.5, cell * .28)
    body += (f'<rect class="sh" x="0" y="0" width="{cell}" height="{cell}" rx="{rad:.1f}" '
             f'fill="{C["primary"]}" transform="translate({pts[0][0]:.1f} {pts[0][1]:.1f})"/>')
    for j, colr in enumerate(SNAKE_BODY[: max(0, min(3, k - 1))]):
        d = -round((j + 1) * lag)
        bx, by = pts[min(j + 1, k - 1)]              # статичная поза на случай reduced-motion
        body += (f'<rect class="sb" x="0" y="0" width="{cell}" height="{cell}" rx="{rad:.1f}" fill="{colr}" '
                 f'transform="translate({bx:.1f} {by:.1f})" style="animation:sh {dur}ms linear infinite;animation-delay:{d}ms"/>')
    css += "@media (prefers-reduced-motion:reduce){.sh,.sb,.d{animation:none!important}}"

    alt = f"Змейка ест коммиты за год: {k} дней с активностью"
    return svg(W, h, body + f'<style>{css}</style>', alt), alt

# ───────────────────────────── Данные ─────────────────────────────
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
CAL_QUERY = ("query($u:String!){user(login:$u){contributionsCollection{contributionCalendar"
             "{totalContributions weeks{contributionDays{date contributionCount}}}}}}")

def call(path, body=None):
    url = path if path.startswith("http") else "https://api.github.com" + path
    h = {"Accept": "application/vnd.github+json", "User-Agent": "profile-build"}
    if TOKEN: h["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def safe(fn, default=None):
    try: return fn()
    except Exception as e:
        print("warn:", e, file=sys.stderr); return default

def fetch():
    user = call(f"/users/{OWNER}")
    repos, page = [], 1
    while True:
        chunk = call(f"/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
        repos += chunk
        if len(chunk) < 100: break
        page += 1
    own = [r for r in repos if not r["fork"] and r["name"].lower() != OWNER.lower()]
    langs = {}
    for r in own:
        for k, v in (safe(lambda: call(f"/repos/{OWNER}/{r['name']}/languages"), {}) or {}).items():
            langs[k] = langs.get(k, 0) + v
    q = "query($u:String!){user(login:$u){pinnedItems(first:6,types:REPOSITORY){nodes{...on Repository{name}}}}}"
    pinned = safe(lambda: [n["name"] for n in call("/graphql", {"query": q, "variables": {"u": OWNER}})["data"]["user"]["pinnedItems"]["nodes"]], [])
    cal = safe(lambda: call("/graphql", {"query": CAL_QUERY, "variables": {"u": OWNER}})
               ["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"], [])
    by = {r["name"]: r for r in own}
    chosen = ([by[n] for n in pinned if n in by] or own)[:REPO_LIMIT]
    return dict(
        repos=user["public_repos"], followers=user["followers"], langs=langs, cal=cal or [],
        commits=safe(lambda: call(f"/search/commits?q=author:{OWNER}&per_page=1")["total_count"]),
        prs=safe(lambda: call(f"/search/issues?q=author:{OWNER}+type:pr&per_page=1")["total_count"], 0),
        stars=sum(r["stargazers_count"] for r in own),
        pushed=max((r["pushed_at"] for r in own), default=None),
        chosen=[dict(name=r["name"], desc=r["description"], lang=r["language"], stars=r["stargazers_count"], pushed=r["pushed_at"]) for r in chosen])

def demo_cal():
    today = date.today()
    d0 = today - timedelta(days=today.weekday() + 1 + 7 * 33)   # воскресенье, 34 недели назад
    weeks = []
    for w in range(34):
        days = []
        for r in range(7):
            i = w * 7 + r
            c = int(6 * abs(math.sin(i * .9)) * (0.2 if i % 11 == 0 else 1.0))
            days.append(dict(date=(d0 + timedelta(days=i)).isoformat(), contributionCount=c))
        weeks.append(dict(contributionDays=days))
    return weeks

def demo():
    return dict(repos=4, followers=0, commits=109, prs=0, stars=0, pushed="2026-11-19T10:00:00Z",
                langs={"Slint": 34000, "Rust": 31000, "Zig": 27000, "Svelte": 6000, "C++": 2000}, cal=demo_cal(),
                chosen=[dict(name="пример-проекта", desc="Так будет выглядеть описание вашего репозитория", lang="Rust", stars=3, pushed="2026-11-19T10:00:00Z"),
                        dict(name="ещё-один", desc=None, lang="Zig", stars=0, pushed="2026-11-12T10:00:00Z")])

# ───────────────────────────── Сборка ─────────────────────────────
TEMPLATE = """<div align="center">

<!-- BANNER:START -->
<!-- BANNER:END -->

<!-- REPOS:START -->
<!-- REPOS:END -->

<!-- STATS:START -->
<!-- STATS:END -->

<!-- SNAKE:START -->
<!-- SNAKE:END -->

<!-- LINKS:START -->
<!-- LINKS:END -->

</div>
"""

def link(href, src, alt):
    return f'<a href="{esc(href)}"><img src="{src}" alt="{esc(alt)}" width="{W}"></a>'

def block(text, name, content):
    pat = re.compile(rf"(<!-- {name}:START -->).*?(<!-- {name}:END -->)", re.S)
    if not pat.search(text): sys.exit(f"В README.md нет маркеров {name}")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}" if content else f"{m.group(1)}\n{m.group(2)}", text)

def ensure(text, name, before):            # добавляет маркеры секции, если их ещё нет
    if f"<!-- {name}:START -->" in text: return text
    b = f"<!-- {before}:START -->"
    return text.replace(b, f"<!-- {name}:START -->\n<!-- {name}:END -->\n\n{b}", 1)

def main():
    mode = "--demo" if "--demo" in sys.argv else "--static" if "--static" in sys.argv else "live"
    root = Path(os.environ.get("ROOT") or Path(__file__).resolve().parent.parent)
    out = root / "assets"; out.mkdir(exist_ok=True)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else TEMPLATE
    put = lambda name, s: (out / name).write_text(s, encoding="utf-8")
    d = demo() if mode == "--demo" else fetch() if mode != "--static" else None

    for f in out.glob("cap-*.svg"): f.unlink()          # заголовков секций больше нет
    (out / "snake-card.svg").unlink(missing_ok=True)    # и шапки со змейкой тоже

    put("banner.svg", banner())
    text = block(text, "BANNER", link(SITE, "assets/banner.svg", BANNER_ALT))

    if d:
        for f in out.glob("repo-*.svg"): f.unlink()
        parts = []
        for i, r in enumerate(d["chosen"]):
            put(f"repo-{i}.svg", repo_card(r))
            parts.append(link(f"https://github.com/{OWNER}/{r['name']}", f"assets/repo-{i}.svg",
                              f'{r["name"]}: {r.get("desc") or "без описания"}'))
        text = block(text, "REPOS", "\n".join(parts))
        s, alt = stats_svg(d)
        put("stats.svg", s)
        text = block(text, "STATS", link(f"https://github.com/{OWNER}?tab=repositories", "assets/stats.svg", alt))

    text = ensure(text, "SNAKE", "LINKS")
    if SNAKE and d:
        sn = snake_svg(d.get("cal") or [])
        if sn:
            put("snake.svg", sn[0])
            text = block(text, "SNAKE", f'<img src="assets/snake.svg" alt="{esc(sn[1])}" width="{W}">')
        else:
            text = block(text, "SNAKE", "")

    for f in out.glob("link-*.svg"): f.unlink()          # убираем карточки, которых больше нет в LINKS
    parts = []
    for i, it in enumerate(LINKS):
        put(f"link-{i}.svg", link_card(it))
        parts.append(link(it["url"], f"assets/link-{i}.svg", f'{it["title"]}: {it["sub"]}'))
    text = block(text, "LINKS", "\n".join(parts))

    readme.write_text(text, encoding="utf-8")
    print("готово:", mode)

if __name__ == "__main__":
    main()
