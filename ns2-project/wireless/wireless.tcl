# =====================================================================
#  MO HINH MANG KHONG DAY (Wireless ad-hoc / MANET) - NS2 2.35
#  20 node di dong trong vung 800m x 800m, IEEE 802.11, dinh tuyen AODV
#  Luu luong: 4 luong CBR/UDP + 1 luong FTP/TCP
#
#  Cach chay:  ns wireless.tcl [ten_tham_so gia_tri] ...
#  VD:         ns wireless.tcl
#              ns wireless.tcl rp DSDV rate 11Mb ifqlen 100 out ../demo_out/wl_x
#  Chay xong tu xuat: <out>.txt (bang ket qua), <out>.html (bao cao + bieu do),
#                     <out>.nam (animation), <out>.tr (trace) ...
# =====================================================================

array set opt {
    chan      Channel/WirelessChannel
    prop      Propagation/TwoRayGround
    netif     Phy/WirelessPhy
    mac       Mac/802_11
    ifq       Queue/DropTail/PriQueue
    ll        LL
    ant       Antenna/OmniAntenna
    ifqlen    50
    nn        20
    rp        AODV
    x         800
    y         800
    rate      2Mb
    basic     1Mb
    rts       0
    range     250
    pktsize   512
    cbr_int   0.05
    stop      100.0
    scen      scen-20n-800
    nam       1
    report    1
    out       ../demo_out/wireless
}
foreach {k v} $argv {
    if {![info exists opt($k)]} { puts "Tham so khong hop le: $k"; exit 1 }
    set opt($k) $v
}
if {$opt(rp) == "DSR"} { set opt(ifq) CMUPriQueue }
puts "== WIRELESS: [array get opt]"
set HERE [file dirname [file normalize [info script]]]
file mkdir [file dirname $opt(out)]

# ---------------- Tang MAC / PHY ------------------------------------
Mac/802_11 set dataRate_  $opt(rate)
Mac/802_11 set basicRate_ $opt(basic)
# rts=1: bat RTS/CTS cho moi goi; rts=0: tat (nguong > kich thuoc goi)
if {$opt(rts)} { Mac/802_11 set RTSThreshold_ 0 } else { Mac/802_11 set RTSThreshold_ 3000 }
# Ban kinh phu song: tinh nguong thu RXThresh_ cho TwoRayGround
# (914MHz, Pt=0.28183815W, ht=hr=1.5m) -> 250m ~ 3.652e-10
set Pt 0.28183815
set ht 1.5
set d  $opt(range)
Phy/WirelessPhy set Pt_ $Pt
Phy/WirelessPhy set freq_ 914e+6
Phy/WirelessPhy set RXThresh_ [expr $Pt * $ht*$ht * $ht*$ht / pow($d,4)]
Phy/WirelessPhy set CSThresh_ [expr $Pt * $ht*$ht * $ht*$ht / pow($d*2.2,4)]

set ns_ [new Simulator]
set tf [open $opt(out).tr w]
$ns_ trace-all $tf
if {$opt(nam)} {
    set nf [open $opt(out).nam w]
    $ns_ namtrace-all-wireless $nf $opt(x) $opt(y)
}

set topo [new Topography]
$topo load_flatgrid $opt(x) $opt(y)
set god_ [create-god $opt(nn)]
set chan_1 [new $opt(chan)]

$ns_ node-config -adhocRouting $opt(rp) \
    -llType $opt(ll) -macType $opt(mac) \
    -ifqType $opt(ifq) -ifqLen $opt(ifqlen) \
    -antType $opt(ant) -propType $opt(prop) \
    -phyType $opt(netif) -channel $chan_1 \
    -topoInstance $topo \
    -agentTrace ON -routerTrace ON -macTrace OFF -movementTrace OFF

for {set i 0} {$i < $opt(nn)} {incr i} {
    set node_($i) [$ns_ node]
    $node_($i) random-motion 0
}
# Vi tri ban dau + chuyen dong (sinh bang setdest)
source $opt(scen)
for {set i 0} {$i < $opt(nn)} {incr i} { $ns_ initial_node_pos $node_($i) 30 }

# ---------------- Luu luong -----------------------------------------
# 4 luong CBR/UDP: goi 512B, moi 0.05s (~82 kbps/luong)
set pairs {{0 10} {2 12} {4 14} {6 16}}
set k 0
foreach p $pairs {
    set s [lindex $p 0]; set d [lindex $p 1]
    set udp($k) [new Agent/UDP]
    $udp($k) set fid_ [expr $k+1]
    $ns_ attach-agent $node_($s) $udp($k)
    set null($k) [new Agent/Null]
    $ns_ attach-agent $node_($d) $null($k)
    $ns_ connect $udp($k) $null($k)
    set cbr($k) [new Application/Traffic/CBR]
    $cbr($k) set packetSize_ $opt(pktsize)
    $cbr($k) set interval_ $opt(cbr_int)
    $cbr($k) attach-agent $udp($k)
    $ns_ at [expr 5.0 + $k] "$cbr($k) start"
    $ns_ at [expr $opt(stop) - 5.0] "$cbr($k) stop"
    incr k
}
# 1 luong TCP/FTP: node 8 -> node 18
set tcp [new Agent/TCP/Newreno]
$tcp set fid_ 5
$tcp set packetSize_ $opt(pktsize)
$ns_ attach-agent $node_(8) $tcp
set sink [new Agent/TCPSink]
$ns_ attach-agent $node_(18) $sink
$ns_ connect $tcp $sink
set ftp [new Application/FTP]
$ftp attach-agent $tcp
$ns_ at 10.0 "$ftp start"
$ns_ at [expr $opt(stop) - 5.0] "$ftp stop"

# ---------------- Ket thuc ------------------------------------------
for {set i 0} {$i < $opt(nn)} {incr i} { $ns_ at $opt(stop) "$node_($i) reset" }
$ns_ at [expr $opt(stop) + 0.01] "finish"
proc finish {} {
    global ns_ tf opt HERE
    $ns_ flush-trace
    close $tf
    if {$opt(nam)} { global nf; close $nf }
    # Phan tich trace -> xuat file ket qua (.txt, .html, .json, _thr.csv)
    if {$opt(report)} {
        catch {exec python3 $HERE/../analysis/report.py wireless $opt(out) \
               --params [array get opt] >@ stdout 2>@ stderr}
    }
    exit 0
}
$ns_ run
