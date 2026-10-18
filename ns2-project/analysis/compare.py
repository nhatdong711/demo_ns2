#!/usr/bin/env python3
"""So sanh nhieu ket qua (file .json do analyze.py --json sinh ra) canh nhau.
Dung:  python3 analysis/compare.py "Co so=a.json" "De xuat B=b.json" [--flows]
  - Bang 1: cac chi so dong TONG; dau * danh dau gia tri tot nhat.
  - --flows: them bang PDR% cua tung luong.
"""
import json, sys

# (khoa, ten hien thi, cao hon la tot hon?, so chu so thap phan)
METRICS = [("pdr", "PDR (%)", True, 2),
           ("thr_kbps", "Thong luong (kbps)", True, 1),
           ("lost", "So goi mat", False, 0),
           ("delay_ms", "Delay TB (ms)", False, 2),
           ("jitter_ms", "Jitter (ms)", False, 2)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flows = "--flows" in sys.argv
    runs = []
    for a in args:
        label, path = a.split("=", 1)
        try:
            runs.append((label, json.load(open(path))))
        except FileNotFoundError:
            sys.exit(f"Chua co file {path} -> chay ns voi 'out ...' tuong ung truoc.")
    w = max(12, *(len(l) + 2 for l, _ in runs))
    two = len(runs) == 2

    hdr = f"{'Chi so':<20}" + "".join(f"{l:>{w}}" for l, _ in runs) + (f"{'Thay doi':>12}" if two else "")
    print(hdr); print("-" * len(hdr))
    for key, name, higher, nd in METRICS:
        vals = [r["all"][key] for _, r in runs]
        best = max(vals) if higher else min(vals)
        row = f"{name:<20}"
        for v in vals:
            s = f"{v:.{nd}f}" + ("*" if v == best and len(set(vals)) > 1 else " ")
            row += f"{s:>{w}}"
        if two:
            a, b = vals
            row += f"{(b - a) / a * 100:>+11.1f}%" if a else f"{'':>12}"
        print(row)

    if flows:
        print()
        hdr = f"{'PDR% tung luong':<20}" + "".join(f"{l:>{w}}" for l, _ in runs)
        print(hdr); print("-" * len(hdr))
        for fid in [k for k in runs[0][1] if k != "all"]:
            row = f"{runs[0][1][fid]['name']:<20}"
            for _, r in runs:
                row += f"{r[fid]['pdr']:>{w}.2f}" if fid in r else f"{'-':>{w}}"
            print(row)


if __name__ == "__main__":
    main()
