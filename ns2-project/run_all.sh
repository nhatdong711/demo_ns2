#!/bin/sh
# Chay toan bo do an: 2 kich ban co so (co trace + nam) va quet tham so.
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "[1] Mang co day - kich ban co so";   (cd wired    && ns wired.tcl    nam 1 out ../results/wired_base >/dev/null 2>&1)
echo "[2] Mang khong day - kich ban co so"; (cd wireless && ns wireless.tcl nam 1 out ../results/wl_base   >/dev/null 2>&1)
python3 analysis/analyze.py wired    results/wired_base.tr --names 1=TCP-FTP,2=CBR-Video,3=CBR-VoIP \
        --json results/wired_base.json --series results/wired_base_thr.csv
python3 analysis/analyze.py wireless results/wl_base.tr --json results/wl_base.json --series results/wl_base_thr.csv
echo "[3] Quet tham so (cai tien hieu nang)"
python3 analysis/run_experiments.py
