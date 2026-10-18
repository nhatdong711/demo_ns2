#!/usr/bin/env python3
"""Chay toan bo kich ban (co so + quet tham so) cho 2 mo hinh mang,
phan tich trace va luu ket qua vao results/summary.json.
Dung:  python3 analysis/run_experiments.py
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))
import analyze  # noqa: E402

RES = ROOT / "results"
RES.mkdir(exist_ok=True)
WIRED_NAMES = {1: "TCP-FTP", 2: "CBR-Video", 3: "CBR-VoIP"}
WL_NAMES = {1: "CBR 0->10", 2: "CBR 2->12", 3: "CBR 4->14", 4: "CBR 6->16", 5: "TCP 8->18"}

# (nhom, nhan, tham so)
WIRED = [("base", "Co so", {})]
WIRED += [("qlim", f"Queue={q}", {"qlim": q}) for q in (5, 10, 20, 50, 100)]
WIRED += [("bw", f"BW={b}", {"bw": b}) for b in ("1Mb", "1.5Mb", "2Mb", "3Mb", "5Mb")]
WIRED += [("qtype", f"{q}", {"qtype": q, "qlim": 20}) for q in ("DropTail", "RED", "SFQ", "DRR", "FQ")]
WIRED += [("tcp", f"{t.split('/')[-1]} w={w}", {"tcp": t, "window": w})
          for t in ("Agent/TCP", "Agent/TCP/Reno", "Agent/TCP/Newreno", "Agent/TCP/Vegas") for w in (20, 64)]
WIRED += [("tuned", "De xuat A (1.5Mb, DRR)", {"qtype": "DRR", "qlim": 10}),
          ("tuned", "De xuat B (2Mb, SFQ)", {"bw": "2Mb", "qtype": "SFQ", "qlim": 20}),
          ("tuned", "De xuat C (3Mb, DRR q15)", {"bw": "3Mb", "qtype": "DRR", "qlim": 15})]

WL = [("base", "Co so", {})]
WL += [("rp", r, {"rp": r}) for r in ("AODV", "DSDV", "DSR")]
WL += [("rate", f"{r}", {"rate": r}) for r in ("1Mb", "2Mb", "5.5Mb", "11Mb")]
WL += [("ifq", f"IFQ={q}", {"ifqlen": q}) for q in (10, 25, 50, 100, 200)]
WL += [("load", f"{round(512*8/i/1000)}kbps/luong", {"cbr_int": i}) for i in (0.2, 0.1, 0.05, 0.025)]
WL += [("range", f"R={r}m", {"range": r}) for r in (250, 350, 450)]
WL += [("area", f"{a}x{a}", {"x": a, "y": a, "scen": f"scen-20n-{a}"}) for a in (500, 800)]
WL += [("rts", "RTS/CTS " + ("bat" if r else "tat"), {"rts": r}) for r in (0, 1)]
WL += [("tuned", "De xuat A (11Mb, R=350m)", {"rate": "11Mb", "range": 350}),
       ("tuned", "De xuat B (11Mb, R=450m)", {"rate": "11Mb", "range": 450})]


def run(kind, idx, params):
    out = RES / f"{kind}_{idx:02d}"
    args = []
    for k, v in params.items():
        args += [k, str(v)]
    args += ["nam", "0", "report", "0", "out", str(out)]
    script = "wired.tcl" if kind == "wired" else "wireless.tcl"
    cwd = ROOT / ("wired" if kind == "wired" else "wireless")
    subprocess.run(["ns", script] + args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tr = f"{out}.tr"
    if kind == "wired":
        s, r, d = analyze.parse_wired(tr); names = WIRED_NAMES
    else:
        s, r, d, _ = analyze.parse_wireless(tr); names = WL_NAMES
    res, series = analyze.stats(s, r, d, names)
    os.remove(tr)  # trace lon, chi giu cho kich ban co so
    return res, series


def main():
    summary = {}
    for kind, table in (("wired", WIRED), ("wireless", WL)):
        summary[kind] = []
        for i, (grp, label, params) in enumerate(table):
            res, series = run(kind, i, params)
            fids = sorted(k for k in res if k != "all")
            ts = [[b] + [series[b][f] * 8 / 1000 for f in fids] for b in range(max(series) + 1)] if series else []
            summary[kind].append({"group": grp, "label": label, "params": params,
                                  "res": {str(k): v for k, v in res.items()}, "series": ts})
            a = res["all"]
            print(f"[{kind:8}] {grp:6} {label:22} thr={a['thr_kbps']:8.1f}kbps delay={a['delay_ms']:8.2f}ms "
                  f"jitter={a['jitter_ms']:7.2f}ms pdr={a['pdr']:6.2f}%", flush=True)
    json.dump(summary, open(RES / "summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
