W = 640
# Цвета: тёмная схема Material Design 3, seed — зелёный. Имена как в спецификации MD3.
C = dict(
    surface_c="#1b201b",       # surface container: фон карточек
    surface_ch="#252a25",      # surface container high: вложенные блоки
    on_surface="#e0e4dd", on_variant="#c1c9bf", outline_v="#414941",
    primary="#b6f1b8", primary_c="#245031", on_primary_c="#c9f5cb",
    secondary_c="#3b4b3d", on_secondary_c="#d2e8d3",
)
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
       f".v{{font-size:22px;font-weight:500;fill:{C['primary']}}}")
GREENS = ["#b6f1b8", "#8ec993", "#679f6e", "#8b938a", "#575f57"]
ICONS = {
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "repo": '<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
    "ext": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "star": '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.9L12 17.8 5.8 21.1 7 14.2 2 9.3l6.9-1z"/>',
    "pen": '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>',
    "ban": '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
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

def tonal_button(right, y, label):        # MD3 filled tonal button: высота 40, полная скруглённость
    bw = 24 + tw(label) + 8 + 18 + 16
    x = right - bw
    return (f'<rect x="{x}" y="{y}" width="{bw}" height="40" rx="20" fill="{C["secondary_c"]}"/>'
            f'<text class="ll" x="{x + 24}" y="{y + 25}" fill="{C["on_secondary_c"]}">{esc(label)}</text>'
            + ico("ext", x + bw - 34, y + 11, 18, C["on_secondary_c"]))

def leading(name, x, y):                  # круглая иконка слева, как в MD3 list item
    return (f'<circle cx="{x + 20}" cy="{y + 20}" r="20" fill="{C["primary_c"]}"/>'
            + ico(name, x + 10, y + 10, 20, C["on_primary_c"]))

# ───────────────────────────── Карточки ─────────────────────────────
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
    # строка «Вайбкод»: список с иконкой слева и статус-чипом справа, без переключателя
    body += card(W - 32, 56, 16, C["surface_ch"], 16, 160)
    body += leading("pen", 28, 168)
    body += f'<text class="tm" x="84" y="184">{esc(VIBE[0])}</text><text class="bm" x="84" y="203">{esc(VIBE[1])}</text>'
    cw = 12 + 18 + 8 + tw(VIBE[2]) + 16
    cx = W - 32 - cw
    body += (f'<rect x="{cx}" y="172" width="{cw}" height="32" rx="16" fill="{C["secondary_c"]}"/>'
             + ico("ban", cx + 12, 181, 14, C["on_secondary_c"])
             + f'<text class="ll" x="{cx + 12 + 14 + 8}" y="193" fill="{C["on_secondary_c"]}">{esc(VIBE[2])}</text>')
    return svg(W, h, body, f"{OWNER}: {BIO} Вайбкод выключен")

def caption(text):
    return svg(W, 30, f'<text class="tl" x="4" y="21">{esc(text)}</text>', text)

def link_card(it):
    h = 72
    body = (card(W, h) + leading(it["icon"], 16, 16) + f'<text class="tm" x="72" y="34">{esc(it["title"])}</text>'
            f'<text class="bm" x="72" y="54">{esc(it["sub"])}</text>' + tonal_button(W - 16, 16, it["btn"]))
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
            f'<text class="bm" x="72" y="54">{esc(desc)}</text>' + meta + tonal_button(W - 16, 28, "Открыть"))
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
    ph = max(len(rows) * 64, 16 + 8 + 12 + len(langs) * 32 + 8)
    rh = ph / len(rows)
    body = (f'<text class="tl" x="4" y="21">Статистика</text><text class="tl" x="{cw + gap + 4}" y="21">Языки</text>'
            f'<g transform="translate(0 {top})">{card(cw, ph, 20)}')
    for i, (t, s, v) in enumerate(rows):
        y = i * rh
        if i: body += f'<line x1="16" x2="{cw - 16}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C["outline_v"]}"/>'
        mid = y + rh / 2
        body += (f'<text class="tm" x="16" y="{mid - 2:.1f}">{esc(t)}</text><text class="bm" x="16" y="{mid + 16:.1f}">{esc(s)}</text>'
                 f'<text class="v" x="{cw - 16}" y="{mid + 7:.1f}" text-anchor="end">{esc(v)}</text>')
    bw, seg_gap = cw - 32, 2
    body += f'</g><g transform="translate({cw + gap} {top})">{card(cw, ph, 20)}'
    x = 16.0                              # сегментированная полоса: скруглённые сегменты с зазором 2px
    for i, (_, p) in enumerate(langs):
        w = max(p / 100 * bw - seg_gap, 3)
        body += f'<rect x="{x:.1f}" y="16" width="{w:.1f}" height="8" rx="4" fill="{GREENS[i]}"/>'
        x += w + seg_gap
    for i, (k, p) in enumerate(langs):
        y = 36 + 12 + i * 32 + 12
        body += (f'<circle cx="22" cy="{y - 4}" r="4" fill="{GREENS[i]}"/><text class="tl" x="36" y="{y}" style="fill:{C["on_surface"]}">{esc(k)}</text>'
                 f'<text class="bm" x="{cw - 16}" y="{y}" text-anchor="end">{"<1" if p < 1 else f"{p:.0f}"}%</text>')
    body += '</g>'
    alt = (f'{d["repos"]} репозиториев'
           + (f', {fmt(d["commits"])} коммитов' if d.get("commits") is not None else "")
           + ". Языки: " + ", ".join(f"{k} {p:.0f}%" for k, p in langs))
    return svg(W, top + ph + 2, body, alt), alt
