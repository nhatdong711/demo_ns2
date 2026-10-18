#!/bin/bash
# =====================================================================
#  DEMO NS2 - chay truc tiep truoc lop / giang vien
#
#  ./demo.sh                 -> menu tuong tac
#  ./demo.sh wired   [tham_so gia_tri ...]   -> chay 1 kich ban co day tuy y
#  ./demo.sh wireless [tham_so gia_tri ...]  -> chay 1 kich ban khong day tuy y
#     VD: ./demo.sh wired bw 3Mb qtype RED qlim 30
#         ./demo.sh wireless rp DSDV rate 11Mb
#  Them NONAM=1 truoc lenh de khong mo NAM (chi in bang ket qua).
# =====================================================================
cd "$(dirname "$0")"
OUT=demo_out
mkdir -p "$OUT"

B=$'\e[1m'; C=$'\e[36m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[0m'

banner() { echo; echo "${B}${C}=== $* ===${R}"; }

# run_case <wired|wireless> <ten_file> <mo_nam 0/1> [tham so ...]
run_case() {
    local kind=$1 name=$2 nam=$3; shift 3
    local dir script names
    if [ "$kind" = wired ]; then
        dir=wired; script=wired.tcl; names="--names 1=TCP-FTP,2=CBR-Video,3=CBR-VoIP"
    else
        dir=wireless; script=wireless.tcl; names=""
    fi
    echo "${Y}\$ ns $script $* ${R}"
    (cd "$dir" && ns "$script" nam "$nam" "$@" out "../$OUT/$name" >/dev/null 2>&1) || { echo "ns loi!"; return 1; }
    python3 analysis/analyze.py "$kind" "$OUT/$name.tr" $names | tail -n +2
    if [ "$nam" = 1 ] && [ -z "$NONAM" ]; then
        echo "${G}-> Mo NAM (bam Play, keo thanh Step de tang/giam toc do)...${R}"
        nam "$OUT/$name.nam" >/dev/null 2>&1 &
    fi
}

compare() {
    local kind=$1 label=$2; shift 2
    banner "$kind: CO SO"
    run_case "$kind" "${kind}_base" 0 stop "$STOP"
    banner "$kind: $label"
    run_case "$kind" "${kind}_tuned" 0 stop "$STOP" "$@"
}

pause() { echo; read -rp "Nhan Enter de tiep tuc..." _; }

# ---------- Che do dong lenh: chay kich ban tuy y ----------
if [ $# -gt 0 ]; then
    kind=$1; shift
    case $kind in wired|wireless) ;; *) echo "Dung: $0 [wired|wireless] [tham_so gia_tri ...]"; exit 1;; esac
    banner "$kind: $*"
    run_case "$kind" "${kind}_custom" 1 "$@"
    exit
fi

# ---------- Menu ----------
while true; do
    cat <<EOF

${B}${C}========== DEMO MO PHONG MANG NS2 ==========${R}
  1) Mang CO DAY (dumbbell, 8 node)     - chay + mo NAM
  2) Mang KHONG DAY (MANET 20 node AODV) - chay + mo NAM
  3) So sanh CO DAY:   co so  vs  de xuat (2Mb, SFQ, q20)
  4) So sanh KHONG DAY: co so vs de xuat (11Mb, R=350m)
  5) So sanh giao thuc dinh tuyen AODV / DSDV / DSR
  6) Mo lai NAM tu ket qua co san (results/, khong can chay lai)
  0) Thoat
EOF
    read -rp "Chon: " ch
    case $ch in
        1) banner "Mang co day - kich ban co so (20s)"
           run_case wired wired_demo 1 stop 20; pause ;;
        2) banner "Mang khong day - kich ban co so (100s)"
           run_case wireless wl_demo 1; pause ;;
        3) STOP=60  compare wired    "DE XUAT B (bw 2Mb, SFQ, qlim 20)" bw 2Mb qtype SFQ qlim 20; pause ;;
        4) STOP=100 compare wireless "DE XUAT A (rate 11Mb, range 350m)" rate 11Mb range 350; pause ;;
        5) for rp in AODV DSDV DSR; do
               banner "Wireless - $rp"; run_case wireless "wl_$rp" 0 rp $rp
           done; pause ;;
        6) select f in results/*.nam; do [ -n "$f" ] && { nam "$f" >/dev/null 2>&1 & }; break; done ;;
        0|q) exit ;;
        *) echo "Lua chon khong hop le" ;;
    esac
done
