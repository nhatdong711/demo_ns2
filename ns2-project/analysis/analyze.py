#!/usr/bin/env python3
"""Phan tich file trace NS2 (wired va wireless old-format).

Chi so tinh cho tung luong va tong:
  - Thong luong (kbps)      = tong byte nhan * 8 / (t_nhan_cuoi - t_nhan_dau)
  - Do tre E2E trung binh   = mean(t_nhan - t_gui) theo uid goi
  - Jitter (IPDV)           = mean |D_i - D_(i-1)| cua cac goi nhan lien tiep
  - PDR (%)                 = goi nhan / goi gui
  - Mat goi                 = goi gui - goi nhan
Dung:  analyze.py wired|wireless file.tr [--json out.json] [--series out.csv]
"""
import sys, json, re, argparse
from collections import defaultdict

DATA_TYPES = {"tcp", "cbr"}


def parse_wired(path):
    sent, recv, drops = {}, {}, defaultdict(int)
    for line in open(path):
        f = line.split()
        if len(f) < 12:
            continue
        ev, t, frm, to, ptype, size, fid = f[0], float(f[1]), f[2], f[3], f[4], int(f[5]), int(f[7])
        if ptype not in DATA_TYPES:
            continue
        src, dst, uid = f[8].split(".")[0], f[9].split(".")[0], int(f[11])
        if ev == "+" and frm == src and uid not in sent:
            sent[uid] = (fid, t, size)
        elif ev == "r" and to == dst:
            recv[uid] = (fid, t, size)
        elif ev == "d":
            drops[fid] += 1
    return sent, recv, drops


WL = re.compile(r"^([srfD]) (\S+) _(\d+)_ (\w+)\s+\S+ (\d+) (\w+) (\d+) .*?\[(\d+):\d+ (\d+):\d+")


def parse_wireless(path):
    sent, recv, drops = {}, {}, defaultdict(int)
    flows = {}
    uid_flow = {}
    for line in open(path):
        m = WL.match(line)
        if not m:
            continue
        ev, t, node, layer, uid, ptype, size, src, dst = m.groups()
        if ptype not in DATA_TYPES:
            continue
        t, uid, size = float(t), int(uid), int(size)
        key = (src, dst)
        if ev == "s" and layer == "AGT" and node == src:
            fid = flows.setdefault(key, len(flows) + 1)
            if uid not in sent:
                sent[uid] = (fid, t, size)
                uid_flow[uid] = fid
        elif ev == "r" and layer == "AGT" and node == dst and uid in sent:
            recv[uid] = (uid_flow[uid], t, sent[uid][2])
        elif ev == "D" and uid in uid_flow:
            drops[uid_flow[uid]] += 1
    names = {v: f"{k[0]}->{k[1]}" for k, v in flows.items()}
    return sent, recv, drops, names


def stats(sent, recv, drops, names=None, bin_s=1.0):
    per = defaultdict(lambda: {"sent": 0, "recv": 0, "bytes": 0, "delays": [], "t0": None, "t1": None})
    for uid, (fid, t, size) in sent.items():
        per[fid]["sent"] += 1
    series = defaultdict(lambda: defaultdict(int))
    for uid, (fid, t, size) in sorted(recv.items(), key=lambda kv: kv[1][1]):
        if uid not in sent:
            continue
        p = per[fid]
        p["recv"] += 1
        p["bytes"] += size
        p["delays"].append(t - sent[uid][1])
        p["t0"] = t if p["t0"] is None else p["t0"]
        p["t1"] = t
        series[int(t // bin_s)][fid] += size
    out = {}
    tot = {"sent": 0, "recv": 0, "bytes": 0, "delays": [], "jit": [], "t0": 1e18, "t1": 0, "drops": 0}
    for fid in sorted(per):
        p = per[fid]
        d = p["delays"]
        jit = [abs(d[i] - d[i - 1]) for i in range(1, len(d))]
        dur = (p["t1"] - p["t0"]) if p["recv"] > 1 else 0
        out[fid] = {
            "name": (names or {}).get(fid, f"flow{fid}"),
            "sent": p["sent"], "recv": p["recv"], "lost": p["sent"] - p["recv"],
            "drops": drops.get(fid, 0),
            "pdr": 100.0 * p["recv"] / p["sent"] if p["sent"] else 0,
            "thr_kbps": p["bytes"] * 8 / dur / 1000 if dur else 0,
            "delay_ms": 1000 * sum(d) / len(d) if d else 0,
            "delay_max_ms": 1000 * max(d) if d else 0,
            "jitter_ms": 1000 * sum(jit) / len(jit) if jit else 0,
        }
        tot["sent"] += p["sent"]; tot["recv"] += p["recv"]; tot["bytes"] += p["bytes"]
        tot["delays"] += d; tot["jit"] += jit; tot["drops"] += drops.get(fid, 0)
        if p["t0"] is not None:
            tot["t0"] = min(tot["t0"], p["t0"]); tot["t1"] = max(tot["t1"], p["t1"])
    dur = tot["t1"] - tot["t0"] if tot["recv"] > 1 else 0
    out["all"] = {
        "name": "TONG", "sent": tot["sent"], "recv": tot["recv"], "lost": tot["sent"] - tot["recv"],
        "drops": tot["drops"],
        "pdr": 100.0 * tot["recv"] / tot["sent"] if tot["sent"] else 0,
        "thr_kbps": tot["bytes"] * 8 / dur / 1000 if dur else 0,
        "delay_ms": 1000 * sum(tot["delays"]) / len(tot["delays"]) if tot["delays"] else 0,
        "delay_max_ms": 1000 * max(tot["delays"]) if tot["delays"] else 0,
        "jitter_ms": 1000 * sum(tot["jit"]) / len(tot["jit"]) if tot["jit"] else 0,
    }
    return out, series


def print_table(res, title=""):
    hdr = f"{'Luong':<10}{'Gui':>7}{'Nhan':>7}{'Mat':>6}{'PDR%':>8}{'Thr(kbps)':>11}{'Delay(ms)':>11}{'MaxD(ms)':>10}{'Jitter(ms)':>11}"
    print(title); print(hdr); print("-" * len(hdr))
    for k, r in res.items():
        print(f"{r['name']:<10}{r['sent']:>7}{r['recv']:>7}{r['lost']:>6}{r['pdr']:>8.2f}"
              f"{r['thr_kbps']:>11.1f}{r['delay_ms']:>11.2f}{r['delay_max_ms']:>10.2f}{r['jitter_ms']:>11.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["wired", "wireless"])
    ap.add_argument("trace")
    ap.add_argument("--json")
    ap.add_argument("--series")
    ap.add_argument("--names", help="VD: 1=TCP,2=Video,3=VoIP")
    a = ap.parse_args()
    if a.kind == "wired":
        s, r, d = parse_wired(a.trace); names = None
    else:
        s, r, d, names = parse_wireless(a.trace)
    if a.names:
        names = {int(k): v for k, v in (x.split("=") for x in a.names.split(","))}
    res, series = stats(s, r, d, names)
    print_table(res, a.trace)
    if a.json:
        json.dump({str(k): v for k, v in res.items()}, open(a.json, "w"), indent=1)
    if a.series:
        fids = sorted(k for k in res if k != "all")
        with open(a.series, "w") as fo:
            fo.write("t," + ",".join(res[f]["name"] for f in fids) + "\n")
            for b in range(0, max(series) + 1 if series else 0):
                fo.write(f"{b}," + ",".join(f"{series[b][f]*8/1000:.1f}" for f in fids) + "\n")


if __name__ == "__main__":
    main()
