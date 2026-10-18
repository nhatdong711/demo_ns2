#!/usr/bin/env python3
"""Xuat ket qua sau moi lan chay ns (duoc goi tu proc finish trong file .tcl).
Tu <out>.tr (+ <out>.queue neu co) sinh ra:
  <out>.txt       bang ket qua (doc bang: cat / mo bang trinh soan thao)
  <out>.json      ket qua dang JSON (dung cho analysis/compare.py)
  <out>_thr.csv   thong luong theo thoi gian (moi 1s)
  <out>.html      bao cao: tham so + bang + bieu do thong luong (+ hang doi)
Dung:  report.py wired|wireless <out> [--names 1=A,2=B] [--params "k v k v ..."]
"""
import argparse, contextlib, html, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402

SKIP = {"out", "ragent", "pos", "rt_port", "cc", "report"}
COLORS = ["#1f6feb", "#d1242f", "#1a7f37", "#bf8700", "#8250df", "#0a7ea4"]


def svg_lines(title, xlabel, ylabel, xs, series, w=760, h=300):
    """Bieu do duong don gian bang SVG (khong can matplotlib)."""
    if not xs or not series:
        return ""
    pl, pr, pt, pb = 60, 150, 30, 40
    ymax = max((max(v) for _, v in series if v), default=1) or 1
    xmax = max(xs) or 1
    X = lambda x: pl + (w - pl - pr) * x / xmax
    Y = lambda y: h - pb - (h - pt - pb) * y / (ymax * 1.05)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px">',
           f'<text x="{w/2 - pr/2}" y="18" text-anchor="middle" font-weight="bold">{html.escape(title)}</text>']
    for i in range(6):  # luoi ngang + nhan truc y
        yv = ymax * 1.05 * i / 5
        out.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(yv):.1f}" y2="{Y(yv):.1f}" stroke="#ddd"/>'
                   f'<text x="{pl-6}" y="{Y(yv)+4:.1f}" text-anchor="end" font-size="11">{yv:.0f}</text>')
    for i in range(6):
        xv = xmax * i / 5
        out.append(f'<text x="{X(xv):.1f}" y="{h-pb+16}" text-anchor="middle" font-size="11">{xv:.0f}</text>')
    out.append(f'<line x1="{pl}" x2="{w-pr}" y1="{h-pb}" y2="{h-pb}" stroke="#333"/>'
               f'<line x1="{pl}" x2="{pl}" y1="{pt}" y2="{h-pb}" stroke="#333"/>'
               f'<text x="{(pl+w-pr)/2}" y="{h-6}" text-anchor="middle" font-size="12">{xlabel}</text>'
               f'<text x="14" y="{h/2}" text-anchor="middle" font-size="12" transform="rotate(-90 14 {h/2})">{ylabel}</text>')
    for k, (name, ys) in enumerate(series):
        c = COLORS[k % len(COLORS)]
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in zip(xs, ys))
        out.append(f'<polyline fill="none" stroke="{c}" stroke-width="1.8" points="{pts}"/>'
                   f'<rect x="{w-pr+12}" y="{pt+k*20}" width="14" height="4" fill="{c}"/>'
                   f'<text x="{w-pr+32}" y="{pt+k*20+6}" font-size="12">{html.escape(name)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["wired", "wireless"])
    ap.add_argument("out")
    ap.add_argument("--names")
    ap.add_argument("--params", default="")
    a = ap.parse_args()
    tr = a.out + ".tr"

    if a.kind == "wired":
        s, r, d = analyze.parse_wired(tr); names = None
    else:
        s, r, d, names = analyze.parse_wireless(tr)
    if a.names:
        names = {int(k): v for k, v in (x.split("=") for x in a.names.split(","))}
    res, series = analyze.stats(s, r, d, names)

    # 1) Bang ket qua .txt (dong thoi in ra man hinh)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        analyze.print_table(res, f"KET QUA: {os.path.basename(a.out)}")
    table = buf.getvalue()
    print(table, end="")
    p = a.params.split()
    params = dict(zip(p[::2], p[1::2]))
    with open(a.out + ".txt", "w") as f:
        f.write("THAM SO: " + " ".join(f"{k}={v}" for k, v in params.items() if k not in SKIP) + "\n\n")
        f.write(table)

    # 2) JSON + CSV
    json.dump({str(k): v for k, v in res.items()}, open(a.out + ".json", "w"), indent=1)
    fids = sorted(k for k in res if k != "all")
    nb = max(series) + 1 if series else 0
    xs = list(range(nb))
    thr = [(res[fid]["name"], [series[b][fid] * 8 / 1000 for b in xs]) for fid in fids]
    with open(a.out + "_thr.csv", "w") as f:
        f.write("t," + ",".join(n for n, _ in thr) + "\n")
        for b in xs:
            f.write(f"{b}," + ",".join(f"{v[b]:.1f}" for _, v in thr) + "\n")

    # 3) Bao cao HTML
    charts = [svg_lines("Thong luong theo thoi gian", "Thoi gian (s)", "kbps", xs, thr)]
    qpath = a.out + ".queue"
    if os.path.exists(qpath):  # wired: do dai hang doi nut co chai (cot 5 = so goi)
        qt, ql = [], []
        for line in open(qpath):
            f = line.split()
            if len(f) >= 5:
                qt.append(float(f[0])); ql.append(float(f[4]))
        charts.append(svg_lines("Do dai hang doi nut co chai R1->R2", "Thoi gian (s)", "goi", qt, [("Queue", ql)]))

    head = ["Luong", "Gui", "Nhan", "Mat", "PDR %", "Thong luong (kbps)", "Delay TB (ms)", "Delay max (ms)", "Jitter (ms)"]
    rows = "".join(
        f"<tr{' class=tot' if k == 'all' else ''}><td>{html.escape(v['name'])}</td><td>{v['sent']}</td><td>{v['recv']}</td>"
        f"<td>{v['lost']}</td><td>{v['pdr']:.2f}</td><td>{v['thr_kbps']:.1f}</td><td>{v['delay_ms']:.2f}</td>"
        f"<td>{v['delay_max_ms']:.2f}</td><td>{v['jitter_ms']:.2f}</td></tr>" for k, v in res.items())
    prm = " ".join(f"<code>{html.escape(k)}={html.escape(v)}</code>" for k, v in params.items() if k not in SKIP)
    title = f"{'Mang co day' if a.kind == 'wired' else 'Mang khong day'} - {os.path.basename(a.out)}"
    with open(a.out + ".html", "w") as f:
        f.write(f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:20px auto;padding:0 16px;background:#fff;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:right}}
td:first-child,th:first-child{{text-align:left}}th{{background:#f0f0f0}}tr.tot{{font-weight:bold;background:#fafae0}}
code{{background:#f3f3f3;padding:1px 4px;margin:2px;display:inline-block}}</style></head><body>
<h2>{html.escape(title)}</h2><p><b>Tham so:</b> {prm}</p>
<table><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr>{rows}</table>
{''.join(f'<div style="margin-top:24px">{c}</div>' for c in charts if c)}
</body></html>""")

    # 4) Liet ke file da tao
    print("\nCAC FILE DA TAO:")
    for ext, desc in ((".txt", "bang ket qua"), (".html", "bao cao + bieu do (mo bang trinh duyet)"),
                      (".nam", "animation (mo bang: nam <file>)"), (".tr", "file trace goc"),
                      (".queue", "theo doi hang doi"), (".json", "ket qua JSON"), ("_thr.csv", "thong luong theo thoi gian")):
        fp = a.out + ext
        if os.path.exists(fp):
            print(f"  {os.path.relpath(fp):<40} {desc}")


if __name__ == "__main__":
    main()
