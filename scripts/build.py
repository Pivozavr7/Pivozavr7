#!/usr/bin/env python3
"""Собирает профиль GitHub в стиле Quadra: SVG-карточки и блоки README.

  python scripts/build.py            боевой запуск, данные берутся из GitHub API
  python scripts/build.py --static   только статичные карточки, без сети
  python scripts/build.py --demo     выдуманные данные, для превью

Всё, что можно менять руками, лежит в блоке «Настройки» ниже.
"""
import html, json, os, re, sys, urllib.request
from pathlib import Path

OWNER = os.environ.get("OWNER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Pivozavr7"

# ───────────────────────────── Настройки ─────────────────────────────
BIO = "Пишу на Rust и Zig. Всё сам."
STACK = ["Rust", "Zig", "Slint"]
VIBE = ("Вайбкод", "Всё пишу руками", "Выключен")          # заголовок, подпись, текст у переключателя
SITE = "https://pivozavr7.github.io"                         # куда ведёт баннер
LINKS = [                                                    # иконки: send, globe, repo
    dict(icon="send",  title="Telegram",        sub="t.me/pkowwww",            url="https://t.me/pkowwww", btn="Написать"),
    dict(icon="globe", title="Сайт",            sub="pivozavr7.github.io",     url=SITE,                   btn="Открыть"),
    dict(icon="repo",  title="Все репозитории", sub=f"github.com/{OWNER}",     url=f"https://github.com/{OWNER}?tab=repositories", btn="Смотреть"),
]
REPO_LIMIT = 4        # сколько проектов показывать (берутся закреплённые, иначе недавние)
# ─────────────────────────────────────────────────────────────────────

W = 640
C = dict(bg="#090c09", panel="#151815", line="#232723", btn="#242724", tile="#1d211d",
         text="#e9ece9", sub="#8f938f", cap="#7a7e7a", accent="#b6f1b8", off="#2a2d2a", offline="#454845")
FONT = "Inter,'Segoe UI',system-ui,-apple-system,Roboto,'Helvetica Neue',Arial,sans-serif"
CSS = ("text{font-family:%s}.t{font-size:15px;font-weight:600;fill:%s}.s{font-size:12.5px;fill:%s}"
       ".v{font-size:18px;font-weight:600;fill:%s}.b{font-size:13px;font-weight:500;fill:%s}"
       ".cap{font-size:13px;font-weight:500;fill:%s}.n{font-size:36px;font-weight:700;fill:%s}"
       ".c{font-size:12.5px;fill:#cfd3cf}") % (FONT, C["text"], C["sub"], C["text"], C["text"], C["cap"], C["text"])
GREENS = ["#b6f1b8", "#7fc383", "#4d8f55", "#8f938f", "#4a4d4a"]
ICONS = {
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "repo": '<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
    "ext": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
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
            f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')

def card(w, h, r=14):
    return f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="{C["panel"]}" stroke="{C["line"]}"/>'

def button(x, y, label):
    bw = int(len(label) * 7.6 + 50)
    x -= bw
    return (f'<rect x="{x}" y="{y}" width="{bw}" height="34" rx="9" fill="{C["btn"]}"/>'
            f'<text class="b" x="{x + 16}" y="{y + 22}">{esc(label)}</text>' + ico("ext", x + bw - 28, y + 10, 14, C["sub"]))

def tile(name):
    return f'<rect x="16" y="14" width="36" height="36" rx="10" fill="{C["tile"]}"/>' + ico(name, 24, 22, 20, C["accent"])

# ───────────────────────────── Карточки ─────────────────────────────
def banner():
    h = 236
    chips, x = "", 32
    for s in STACK:
        cw = int(len(s) * 7.4 + 26)
        chips += (f'<rect x="{x}" y="114" width="{cw}" height="28" rx="14" fill="{C["panel"]}" stroke="{C["offline"]}"/>'
                  f'<text class="c" x="{x + 13}" y="132">{esc(s)}</text>')
        x += cw + 8
    panel = (f'<rect x="24" y="158" width="{W - 48}" height="54" rx="12" fill="{C["panel"]}" stroke="{C["line"]}"/>'
             f'<text class="t" x="42" y="182">{esc(VIBE[0])}</text><text class="s" x="42" y="199">{esc(VIBE[1])}</text>'
             f'<text class="s" x="{W - 24 - 18 - 44 - 10}" y="190" text-anchor="end">{esc(VIBE[2])}</text>'
             f'<rect x="{W - 24 - 18 - 44}" y="171" width="44" height="24" rx="12" fill="{C["off"]}" stroke="{C["offline"]}"/>'
             f'<circle cx="{W - 24 - 18 - 44 + 12}" cy="183" r="8" fill="{C["sub"]}"/>')
    body = (f'<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="20" fill="{C["bg"]}" stroke="{C["accent"]}" stroke-width="2"/>'
            f'<text class="n" x="32" y="70">{esc(OWNER)}</text><text class="s" x="32" y="98" style="font-size:15px">{esc(BIO)}</text>'
            + chips + panel)
    return svg(W, h, body, f"{OWNER}: {BIO} Вайбкод выключен")

def caption(text):
    return svg(W, 30, f'<text class="cap" x="4" y="21">{esc(text)}</text>', text)

def link_card(it):
    h = 64
    body = (card(W, h) + tile(it["icon"]) + f'<text class="t" x="68" y="30">{esc(it["title"])}</text>'
            f'<text class="s" x="68" y="48">{esc(it["sub"])}</text>' + button(W - 16, 15, it["btn"]))
    return svg(W, h, body, f'{it["title"]}: {it["sub"]}')

def repo_card(r):
    h = 90
    desc = clip(r.get("desc") or "Без описания", 64)
    meta, x = "", 68
    if r.get("lang"):
        meta += f'<circle cx="{x + 4}" cy="70" r="4" fill="{C["accent"]}"/><text class="s" x="{x + 14}" y="74">{esc(r["lang"])}</text>'
        x += 14 + int(len(r["lang"]) * 7) + 18
    if r.get("stars"):
        meta += ico("star", x, 62, 13, C["sub"]) + f'<text class="s" x="{x + 19}" y="74">{fmt(r["stars"])}</text>'
        x += 19 + len(fmt(r["stars"])) * 7 + 18
    if r.get("pushed"):
        meta += f'<text class="s" x="{x}" y="74">обновлён {ru_date(r["pushed"])}</text>'
    body = (card(W, h) + tile("repo") + f'<text class="t" x="68" y="31">{esc(r["name"])}</text>'
            f'<text class="s" x="68" y="50">{esc(desc)}</text>' + meta + button(W - 16, 28, "Открыть"))
    return svg(W, h, body, f'Репозиторий {r["name"]}: {desc}')

def top_langs(d):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:5]
    tot = sum(v for _, v in items) or 1
    return [(k, v / tot * 100) for k, v in items]

def stats_svg(d):
    gap, top = 16, 30
    cw = (W - gap) // 2
    rows = [("Репозитории", "Публичные", fmt(d["repos"]))]
    if d.get("commits") is not None: rows.append(("Коммиты", "В основной ветке", fmt(d["commits"])))
    if d.get("stars"):     rows.append(("Звёзды", "Во всех репозиториях", fmt(d["stars"])))
    if d.get("prs"):       rows.append(("Pull request’ы", "Открытые вами", fmt(d["prs"])))
    if d.get("followers"): rows.append(("Подписчики", "На GitHub", fmt(d["followers"])))
    if d.get("pushed"):    rows.append(("Последний пуш", "В свои проекты", ru_date(d["pushed"])))
    langs = top_langs(d)
    ph = max(len(rows) * 60, 16 + 8 + 12 + len(langs) * 32 + 8)
    rh = ph / len(rows)
    body = (f'<text class="cap" x="4" y="21">Статистика</text><text class="cap" x="{cw + gap + 4}" y="21">Языки</text>'
            f'<g transform="translate(0 {top})">'
            f'<rect x=".5" y=".5" width="{cw - 1}" height="{ph - 1}" rx="14" fill="{C["panel"]}" stroke="{C["line"]}"/>')
    for i, (t, s, v) in enumerate(rows):
        y = i * rh
        if i: body += f'<line x1="16" x2="{cw - 16}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["line"]}"/>'
        mid = y + rh / 2
        body += (f'<text class="t" x="16" y="{mid - 2:.1f}">{esc(t)}</text><text class="s" x="16" y="{mid + 15:.1f}">{esc(s)}</text>'
                 f'<text class="v" x="{cw - 16}" y="{mid + 6:.1f}" text-anchor="end">{esc(v)}</text>')
    rx = cw + gap
    bw = cw - 32
    body += (f'</g><g transform="translate({rx} {top})"><rect x=".5" y=".5" width="{cw - 1}" height="{ph - 1}" rx="14" '
             f'fill="{C["panel"]}" stroke="{C["line"]}"/><clipPath id="bar"><rect x="16" y="16" width="{bw}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    x = 16.0
    for i, (_, p) in enumerate(langs):
        w = max(p / 100 * bw, 2)
        body += f'<rect x="{x:.1f}" y="16" width="{w:.1f}" height="8" fill="{GREENS[i]}"/>'
        x += w
    body += '</g>'
    for i, (k, p) in enumerate(langs):
        y = 36 + 12 + i * 32 + 12
        body += (f'<circle cx="22" cy="{y - 4}" r="4" fill="{GREENS[i]}"/><text class="t" x="36" y="{y}" style="font-weight:500">{esc(k)}</text>'
                 f'<text class="s" x="{cw - 16}" y="{y}" text-anchor="end">{"<1" if p < 1 else f"{p:.0f}"}%</text>')
    body += '</g>'
    alt = (f'{d["repos"]} репозиториев'
           + (f', {fmt(d["commits"])} коммитов' if d.get("commits") is not None else "")
           + ". Языки: " + ", ".join(f"{k} {p:.0f}%" for k, p in langs))
    return svg(W, top + ph + 2, body, alt), alt

# ───────────────────────────── Данные ─────────────────────────────
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

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
    by = {r["name"]: r for r in own}
    chosen = ([by[n] for n in pinned if n in by] or own)[:REPO_LIMIT]
    return dict(
        repos=user["public_repos"], followers=user["followers"], langs=langs,
        commits=safe(lambda: call(f"/search/commits?q=author:{OWNER}&per_page=1")["total_count"]),
        prs=safe(lambda: call(f"/search/issues?q=author:{OWNER}+type:pr&per_page=1")["total_count"], 0),
        stars=sum(r["stargazers_count"] for r in own),
        pushed=max((r["pushed_at"] for r in own), default=None),
        chosen=[dict(name=r["name"], desc=r["description"], lang=r["language"], stars=r["stargazers_count"], pushed=r["pushed_at"]) for r in chosen])

def demo():
    return dict(repos=4, followers=0, commits=109, prs=0, stars=0, pushed="2026-11-19T10:00:00Z",
                langs={"Slint": 34000, "Rust": 31000, "Zig": 27000, "Svelte": 6000, "C++": 2000},
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

def main():
    mode = "--demo" if "--demo" in sys.argv else "--static" if "--static" in sys.argv else "live"
    root = Path(os.environ.get("ROOT") or Path(__file__).resolve().parent.parent)
    out = root / "assets"; out.mkdir(exist_ok=True)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else TEMPLATE
    put = lambda name, s: (out / name).write_text(s, encoding="utf-8")

    put("banner.svg", banner())
    text = block(text, "BANNER", link(SITE, "assets/banner.svg", f"{OWNER}: {BIO} Вайбкод выключен"))

    put("cap-links.svg", caption("Связь"))
    parts = [f'<img src="assets/cap-links.svg" alt="Связь" width="{W}">']
    for i, it in enumerate(LINKS):
        put(f"link-{i}.svg", link_card(it))
        parts.append(link(it["url"], f"assets/link-{i}.svg", f'{it["title"]}: {it["sub"]}'))
    text = block(text, "LINKS", "\n".join(parts))

    if mode != "--static":
        d = demo() if mode == "--demo" else fetch()
        for f in out.glob("repo-*.svg"): f.unlink()
        parts = []
        if d["chosen"]:
            put("cap-projects.svg", caption("Проекты"))
            parts.append(f'<img src="assets/cap-projects.svg" alt="Проекты" width="{W}">')
            for i, r in enumerate(d["chosen"]):
                put(f"repo-{i}.svg", repo_card(r))
                parts.append(link(f"https://github.com/{OWNER}/{r['name']}", f"assets/repo-{i}.svg", f'{r["name"]}: {r.get("desc") or "без описания"}'))
        text = block(text, "REPOS", "\n".join(parts))
        s, alt = stats_svg(d)
        put("stats.svg", s)
        text = block(text, "STATS", link(f"https://github.com/{OWNER}?tab=repositories", "assets/stats.svg", alt))
    readme.write_text(text, encoding="utf-8")
    print("готово:", mode)

if __name__ == "__main__":
    main()
