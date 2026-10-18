# HƯỚNG DẪN DEMO ĐỒ ÁN MÔ PHỎNG MẠNG NS2

> Tài liệu dùng khi demo trực tiếp trước giảng viên. Mọi lệnh dưới đây đã được chạy thử
> và các bảng số liệu là **kết quả thật** (ngày 18/10/2026). Vì mô phỏng dùng file kịch bản
> di chuyển cố định nên chạy lại sẽ ra **đúng các con số này**.

---

## ⚡ Tóm tắt lệnh demo (copy theo thứ tự)

Mở **2 tab terminal**: tab A đứng ở `wired/`, tab B đứng ở `wireless/`. Mọi lệnh dưới đây
chạy tại chỗ, không cần `cd` qua lại. Mỗi lệnh `ns` chạy xong **tự in bảng kết quả** và
xuất file vào `demo_out/`.

```bash
# ---------- Tab A ----------
cd ~/Projects/ns2-project/wired
pkill nam                                             # dọn NAM cũ

# Bước 1: mạng có dây
ns wired.tcl stop 20 out ../demo_out/b1
nam ../demo_out/b1.nam &
xdg-open ../demo_out/b1.html

# Bước 2: so sánh có dây (cơ sở vs đề xuất B)
ns wired.tcl nam 0 out ../demo_out/b2_coso
ns wired.tcl nam 0 bw 2Mb qtype SFQ qlim 20 out ../demo_out/b2_dexuat
python3 ../analysis/compare.py "Co so=../demo_out/b2_coso.json" "De xuat B=../demo_out/b2_dexuat.json" --flows

# ---------- Tab B ----------
cd ~/Projects/ns2-project/wireless

# Bước 3: mạng không dây
ns wireless.tcl out ../demo_out/b3
nam ../demo_out/b3.nam &
xdg-open ../demo_out/b3.html

# Bước 4: so sánh không dây (cơ sở vs đề xuất A)
ns wireless.tcl nam 0 out ../demo_out/b4_coso
ns wireless.tcl nam 0 rate 11Mb range 350 out ../demo_out/b4_dexuat
python3 ../analysis/compare.py "Co so=../demo_out/b4_coso.json" "De xuat A=../demo_out/b4_dexuat.json" --flows

# Bước 5: so sánh định tuyến
for rp in AODV DSDV DSR; do ns wireless.tcl nam 0 rp $rp out ../demo_out/b5_$rp; done
python3 ../analysis/compare.py "AODV=../demo_out/b5_AODV.json" "DSDV=../demo_out/b5_DSDV.json" "DSR=../demo_out/b5_DSR.json" --flows
```

Chi tiết từng bước (kết quả mẫu + ý chính để thuyết trình) ở các mục bên dưới.

---

## Mục lục

1. [Tổng quan đồ án](#1-tổng-quan-đồ-án)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Chuẩn bị trước buổi demo](#3-chuẩn-bị-trước-buổi-demo)
4. [Bước 1 – Mạng có dây (cơ sở) + NAM](#bước-1--mạng-có-dây-cơ-sở--nam)
5. [Bước 2 – So sánh có dây: cơ sở vs đề xuất B](#bước-2--so-sánh-có-dây-cơ-sở-vs-đề-xuất-b)
6. [Bước 3 – Mạng không dây (cơ sở) + NAM](#bước-3--mạng-không-dây-cơ-sở--nam)
7. [Bước 4 – So sánh không dây: cơ sở vs đề xuất A](#bước-4--so-sánh-không-dây-cơ-sở-vs-đề-xuất-a)
8. [Bước 5 – So sánh AODV / DSDV / DSR](#bước-5--so-sánh-aodv--dsdv--dsr)
9. [Bước 6 – Phương án dự phòng](#bước-6--phương-án-dự-phòng)
10. [Chạy kịch bản tùy ý khi giảng viên yêu cầu](#chạy-kịch-bản-tùy-ý-khi-giảng-viên-yêu-cầu)
11. [Câu hỏi thường gặp & cách trả lời](#câu-hỏi-thường-gặp--cách-trả-lời)
12. [Xử lý sự cố](#xử-lý-sự-cố)
13. [Cách nhanh: dùng menu `demo.sh`](#cách-nhanh-dùng-menu-demosh)

---

## 1. Tổng quan đồ án

Đồ án gồm **2 mô hình mạng** mô phỏng bằng NS2 (2.35):

### Mạng có dây – topo "dumbbell" (8 node) – `wired/wired.tcl`

```
  n0 (FTP/TCP)   --\                            /-- n5 (TCPSink)
  n1 (CBR Video) ---- R1 (n3) ======== R2 (n4) ---- n6 (Null)
  n2 (CBR VoIP)  --/       nút cổ chai          \-- n7 (Null)
```

| Thành phần | Cấu hình cơ sở |
|---|---|
| Link truy nhập | 10Mb / 2ms / DropTail |
| **Link cổ chai R1–R2** | **1.5Mb / 20ms / DropTail, queue = 10 gói** |
| Luồng 1 – TCP-FTP (xanh dương) | TCP Tahoe, window 20, gói 1000 byte |
| Luồng 2 – CBR-Video (đỏ) | UDP, 1 Mb/s |
| Luồng 3 – CBR-VoIP (xanh lá) | UDP, gói 160 byte mỗi 20ms (64 kbps) |

→ Tổng tải ≈ 1.06 Mb/s UDP + TCP "tham lam" > 1.5Mb ⇒ **cổ chai bị nghẽn**.

### Mạng không dây – MANET (20 node) – `wireless/wireless.tcl`

| Thành phần | Cấu hình cơ sở |
|---|---|
| Vùng | 800m × 800m, 20 node di động (file `scen-20n-800`) |
| MAC / PHY | IEEE 802.11, data rate 2Mb, basic rate 1Mb, RTS/CTS tắt |
| Tầm phủ | 250m, mô hình truyền sóng TwoRayGround |
| Định tuyến | **AODV** |
| Hàng đợi | DropTail/PriQueue, 50 gói |
| Lưu lượng | 4 luồng CBR/UDP (512 byte / 0.05s ≈ 82 kbps): 0→10, 2→12, 4→14, 6→16 + 1 luồng FTP/TCP 8→18 |
| Thời gian | 100s |

### Các chỉ số đánh giá (do `analysis/analyze.py` tính từ file trace)

| Cột | Ý nghĩa |
|---|---|
| Gui / Nhan / Mat | Số gói gửi / nhận / mất |
| PDR% | Packet Delivery Ratio = Nhận / Gửi × 100 |
| Thr(kbps) | Throughput = byte nhận × 8 / thời gian hoạt động của luồng |
| Delay(ms) | Độ trễ đầu-cuối trung bình |
| MaxD(ms) | Độ trễ lớn nhất |
| Jitter(ms) | Trung bình độ chênh lệch trễ giữa 2 gói liên tiếp |

---

## 2. Cấu trúc thư mục

```
ns2-project/
├── wired/wired.tcl            # Script mô phỏng mạng có dây
├── wireless/wireless.tcl      # Script mô phỏng mạng không dây
├── wireless/scen-20n-800      # Kịch bản di chuyển 20 node, vùng 800x800
├── wireless/scen-20n-500      # Kịch bản di chuyển 20 node, vùng 500x500
├── analysis/analyze.py        # Phân tích file .tr -> bảng kết quả
├── analysis/report.py         # Tự chạy khi .tcl kết thúc: xuất .txt/.html/.json
├── analysis/compare.py        # So sánh nhiều lần chạy cạnh nhau
├── analysis/run_experiments.py# Quét tham số, lưu results/summary.json
├── demo.sh                    # Menu demo tương tác
├── run_all.sh                 # Chạy toàn bộ đồ án
├── results/                   # Kết quả chính thức (đã chạy sẵn)
├── demo_out/                  # Kết quả sinh ra trong lúc demo
└── report/Bao_cao_NS2.pdf     # Báo cáo
```

### Chạy file `.tcl` xong là có sẵn file kết quả để xem

Mỗi lần chạy `ns wired.tcl` / `ns wireless.tcl`, script **tự phân tích** và in bảng kết quả ra
màn hình, đồng thời xuất các file sau vào `demo_out/` (tên file theo tham số `out`):

| File | Nội dung | Cách xem |
|---|---|---|
| `<tên>.txt` | Tham số + bảng kết quả | `cat demo_out/<tên>.txt` |
| `<tên>.html` | Báo cáo: tham số, bảng, **biểu đồ thông lượng** (+ biểu đồ hàng đợi với mạng có dây) | `xdg-open demo_out/<tên>.html` |
| `<tên>.nam` | Animation | `nam demo_out/<tên>.nam &` |
| `<tên>.tr` | File trace gốc | `less demo_out/<tên>.tr` |
| `<tên>.queue` | Theo dõi hàng đợi nút cổ chai (chỉ có dây) | |
| `<tên>.json`, `<tên>_thr.csv` | Kết quả dạng máy đọc (dùng cho so sánh) | |

Mặc định: `ns wired.tcl` → `demo_out/wired.*`, `ns wireless.tcl` → `demo_out/wireless.*`.
Đặt tên khác bằng `out ../demo_out/<tên>`. Không muốn sinh file `.nam` thì thêm `nam 0`.
(Đường dẫn `../demo_out/...` vì lệnh chạy từ trong `wired/` hoặc `wireless/`.)

So sánh nhiều lần chạy cạnh nhau:
```bash
python3 ../analysis/compare.py "Tên A=../demo_out/a.json" "Tên B=../demo_out/b.json" --flows
```
(dấu `*` đánh dấu giá trị tốt nhất của mỗi chỉ số; cột "Thay doi" là % thay đổi B so với A)

---

## 3. Chuẩn bị trước buổi demo

**Làm trước 1 ngày / trước giờ demo:**

```bash
cd ~/Projects/ns2-project
which ns nam python3          # kiểm tra đủ 3 công cụ
chmod +x demo.sh run_all.sh
./run_all.sh                  # chạy toàn bộ -> results/ (để có kết quả dự phòng)
mkdir -p demo_out
```

**Checklist:**
- [ ] Đã chạy `run_all.sh` thành công, có `results/wired_base.nam`, `results/wl_base.nam`
- [ ] Mở thử NAM 1 lần để chắc chắn hiển thị được
- [ ] Đóng hết cửa sổ NAM cũ trước khi vào demo (`pkill nam`)
- [ ] Mở sẵn 2 tab terminal: tab A `cd ~/Projects/ns2-project/wired`, tab B `cd ~/Projects/ns2-project/wireless`
- [ ] Mở thử 1 file `.html` để chắc chắn trình duyệt hiển thị biểu đồ đúng
- [ ] Mở sẵn `report/Bao_cao_NS2.pdf`
- [ ] Phóng to font terminal để giảng viên nhìn rõ

> ⚠ **Quy tắc quan trọng:** lệnh `ns` phải chạy **bên trong** thư mục `wired/` hoặc
> `wireless/` (script wireless đọc file `scen-20n-*` theo đường dẫn tương đối).
> Các lệnh `compare.py`, `xdg-open`, `nam` trong các bước cũng chạy luôn tại đó (đường dẫn `../`).

> ℹ Khi chạy `ns` sẽ thấy cảnh báo *"ns found the right version of tclsh in /bin/tclsh8.6 but
> it doesn't seem to be there anymore..."* — **bỏ qua**, không ảnh hưởng kết quả.

---

## Bước 1 – Mạng có dây (cơ sở) + NAM

**Mục tiêu:** cho thấy topo, các luồng và hiện tượng nghẽn ở nút cổ chai.

```bash
cd ~/Projects/ns2-project/wired
ns wired.tcl stop 20 out ../demo_out/b1      # chạy 20s -> in bảng + xuất file
nam ../demo_out/b1.nam &                     # animation: bấm Play
xdg-open ../demo_out/b1.html                 # bảng + biểu đồ thông lượng, hàng đợi
```

**Dòng cấu hình in ra** (chỉ vào để giải thích tham số):
```
== WIRED: ... qlim 10 qtype DropTail ... stop 20 video 1Mb ... bw 1.5Mb ... delay 20ms ... tcp Agent/TCP
```

**Kết quả:**

| Luồng | Gửi | Nhận | Mất | PDR% | Thr (kbps) | Delay (ms) | MaxD (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|---|---|
| TCP-FTP | 1132 | 1064 | 68 | 93.99 | 465.4 | 54.77 | 81.11 | 4.66 |
| CBR-Video | 2251 | 2225 | 26 | 98.84 | 987.4 | 54.34 | 73.78 | 3.11 |
| CBR-VoIP | 901 | 898 | 3 | 99.67 | 63.8 | 49.88 | 68.72 | 5.46 |
| **TỔNG** | 4284 | 4187 | 97 | 97.74 | **1462.5** | 53.49 | 81.11 | 4.01 |

**Thuyết trình:**
- Tổng throughput **1462.5 kbps ≈ 1.5Mb** → link cổ chai bị dùng gần hết công suất.
- **TCP chịu thiệt nhiều nhất** (mất 68 gói, PDR 94%, chỉ được ~465 kbps): CBR/UDP không có
  cơ chế điều khiển nghẽn nên cứ gửi đều, còn TCP gặp mất gói thì **giảm cửa sổ** → bị lấn băng thông.
- Delay ≈ 50ms = 20ms trễ truyền link cổ chai + ~4ms link truy nhập + **thời gian chờ trong hàng đợi**.

**Trên NAM:** bấm **Play**, kéo thanh **Step** để chỉnh tốc độ.
- Xanh dương = TCP, đỏ = Video, xanh lá = VoIP.
- Chỉ vào hàng đợi tại **R1 (n3, hình vuông)**: gói xếp hàng và **gói rơi xuống = bị drop**.
- Lúc đầu TCP gửi ít (slow-start) rồi tăng dần, đến khi mất gói thì tụt lại.

---

## Bước 2 – So sánh có dây: cơ sở vs đề xuất B

**Mục tiêu:** chứng minh cấu hình đề xuất cải thiện hiệu năng.
Đề xuất B: **băng thông 2Mb + hàng đợi SFQ + queue 20**.

```bash
# (vẫn ở wired/)
ns wired.tcl nam 0 out ../demo_out/b2_coso
ns wired.tcl nam 0 bw 2Mb qtype SFQ qlim 20 out ../demo_out/b2_dexuat
python3 ../analysis/compare.py "Co so=../demo_out/b2_coso.json" "De xuat B=../demo_out/b2_dexuat.json" --flows
xdg-open ../demo_out/b2_coso.html; xdg-open ../demo_out/b2_dexuat.html   # (tùy chọn) so 2 biểu đồ hàng đợi
```

**Kết quả cơ sở (1.5Mb, DropTail, q10, 60s):**

| Luồng | Gửi | Nhận | Mất | PDR% | Thr (kbps) | Delay (ms) | MaxD (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|---|---|
| TCP-FTP | 3475 | 3270 | 205 | 94.10 | 460.9 | 54.94 | 81.11 | 4.62 |
| CBR-Video | 7250 | 7149 | 101 | 98.61 | 985.7 | 54.28 | 74.77 | 3.15 |
| CBR-VoIP | 2900 | 2879 | 21 | 99.28 | 63.5 | 49.89 | 68.72 | 5.32 |
| **TỔNG** | 13625 | 13298 | 327 | 97.60 | 1492.4 | 53.49 | 81.11 | 3.98 |

**Kết quả đề xuất B (2Mb, SFQ, q20, 60s):**

| Luồng | Gửi | Nhận | Mất | PDR% | Thr (kbps) | Delay (ms) | MaxD (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|---|---|
| TCP-FTP | 6658 | 6578 | 80 | 98.80 | 927.0 | 84.82 | 136.10 | 2.02 |
| CBR-Video | 7250 | 7250 | 0 | 100.00 | 999.4 | 64.07 | 99.84 | 0.88 |
| CBR-VoIP | 2900 | 2900 | 0 | 100.00 | 64.0 | 34.30 | 37.18 | 1.87 |
| **TỔNG** | 16808 | 16728 | 80 | 99.52 | 1972.4 | 67.07 | 136.10 | 1.50 |

**Bảng so sánh để trình bày:**

| Chỉ số | Cơ sở | Đề xuất B | Nhận xét |
|---|---|---|---|
| Tổng throughput | 1492.4 kbps | **1972.4 kbps** | +32% |
| Tổng gói mất | 327 | **80** | −76% |
| PDR tổng | 97.60% | **99.52%** | |
| Throughput TCP | 460.9 kbps | **927.0 kbps** | ×2 |
| Mất gói Video / VoIP | 101 / 21 | **0 / 0** | |
| Jitter tổng | 3.98 ms | **1.50 ms** | giảm ~2.7 lần |
| Delay VoIP | 49.89 ms | **34.30 ms** | tốt hơn |
| Delay TCP / Video | 54.9 / 54.3 ms | 84.8 / 64.1 ms | **tăng** (đánh đổi) |

**Thuyết trình:**
- **Tăng băng thông 2Mb:** đủ chỗ cho cả UDP (~1.06Mb) lẫn TCP → TCP tăng gấp đôi.
- **SFQ (Stochastic Fair Queuing):** băm mỗi luồng vào một hàng con riêng, phục vụ
  **xoay vòng (round-robin)** → luồng nhỏ như VoIP không phải chờ sau các gói 1000 byte
  của Video/TCP ⇒ delay VoIP giảm, jitter giảm mạnh; các luồng được chia **công bằng** hơn.
- **qlim 20:** hàng đợi dài hơn hấp thụ được burst → ít drop.
- **Đánh đổi (nên chủ động nói):** delay TCP & Video tăng vì hàng đợi dài gấp đôi
  (hiện tượng *bufferbloat*). Nếu ưu tiên độ trễ có thể dùng **Đề xuất C (3Mb, DRR, q15)**
  — có trong phần quét tham số (`results/summary.json`).

---

## Bước 3 – Mạng không dây (cơ sở) + NAM

**Mục tiêu:** cho thấy MANET 20 node di chuyển, định tuyến AODV, hiệu năng thấp hơn mạng có dây.

```bash
cd ~/Projects/ns2-project/wireless
ns wireless.tcl out ../demo_out/b3           # ~0.5 giây là xong 100s mô phỏng
nam ../demo_out/b3.nam &
xdg-open ../demo_out/b3.html
```

ns sẽ in thêm vài dòng như `num_nodes is set 20`, `distCST_ = 550.0` — bình thường
(550m là bán kính phát hiện sóng mang – carrier sense, lớn hơn tầm nhận 250m).

**Kết quả:**

| Luồng | Gửi | Nhận | Mất | PDR% | Thr (kbps) | Delay (ms) | MaxD (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|---|---|
| CBR 0→10 | 1801 | 1280 | 521 | 71.07 | 84.9 | 116.17 | 3179.99 | 45.77 |
| CBR 2→12 | 1781 | 1781 | 0 | 100.00 | 82.0 | 9.96 | 175.13 | 6.23 |
| CBR 4→14 | 1761 | 527 | 1234 | 29.93 | 36.1 | 279.26 | 3219.52 | 129.47 |
| CBR 6→16 | 1741 | 258 | 1483 | 14.82 | 19.8 | 237.60 | 3184.97 | 101.23 |
| TCP 8→18 | 899 | 855 | 44 | 95.11 | 51.2 | 184.99 | 11535.00 | 66.28 |
| **TỔNG** | 7983 | 4701 | 3282 | **58.89** | 219.2 | 113.39 | 11535.00 | 46.92 |

**Thuyết trình:**
- **PDR chỉ ~59%** so với ~97% của mạng có dây. Nguyên nhân:
  1. Node **di chuyển** → đường đi bị đứt, phải tìm route lại.
  2. Tầm phủ **250m** trong vùng 800m → phải đi **nhiều hop**, mỗi hop là một cơ hội mất gói.
  3. 5 luồng **tranh chấp chung một kênh** 802.11 tốc độ 2Mb (kênh vô tuyến chia sẻ, có xung đột/collision).
- **Chênh lệch giữa các luồng rất lớn:** 2→12 đạt 100% (delay 10ms – có thể 2 node ở gần nhau,
  ít hop) trong khi 6→16 chỉ 15% → đặc trưng của MANET: phụ thuộc vị trí và chuyển động.
- **MaxD lên tới 3–11 giây:** AODV là giao thức **theo yêu cầu (reactive)** — khi chưa có route,
  gói được **giữ trong buffer** chờ quá trình Route Request/Reply hoàn tất.
- TCP (8→18) PDR cao (95%) nhưng gửi ít gói vì TCP tự giảm tốc khi gặp mất gói.

**Trên NAM:** bấm **Play** → thấy các node di chuyển, vòng tròn sóng phát ra khi truyền,
các gói AODV (RREQ broadcast) lan ra khắp mạng khi tìm đường.

---

## Bước 4 – So sánh không dây: cơ sở vs đề xuất A

Đề xuất A: **data rate 11Mb + tầm phủ 350m**.

```bash
# (vẫn ở wireless/)
ns wireless.tcl nam 0 out ../demo_out/b4_coso
ns wireless.tcl nam 0 rate 11Mb range 350 out ../demo_out/b4_dexuat
python3 ../analysis/compare.py "Co so=../demo_out/b4_coso.json" "De xuat A=../demo_out/b4_dexuat.json" --flows
```

Kết quả cơ sở giống hệt Bước 3. **Kết quả đề xuất A:**

| Luồng | Gửi | Nhận | Mất | PDR% | Thr (kbps) | Delay (ms) | MaxD (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|---|---|
| CBR 0→10 | 1801 | 1796 | 5 | 99.72 | 78.6 | 214.17 | 6445.58 | 25.75 |
| CBR 2→12 | 1781 | 1781 | 0 | 100.00 | 81.9 | 12.80 | 87.56 | 4.56 |
| CBR 4→14 | 1761 | 1755 | 6 | 99.66 | 81.7 | 150.98 | 3430.28 | 58.08 |
| CBR 6→16 | 1741 | 1613 | 128 | 92.65 | 76.0 | 457.40 | 4365.48 | 25.63 |
| TCP 8→18 | 14203 | 14187 | 16 | 99.89 | 754.8 | 61.97 | 2043.58 | 4.95 |
| **TỔNG** | 21287 | 21132 | 155 | **99.27** | **973.0** | 108.33 | 6445.58 | 12.67 |

**Bảng so sánh:**

| Chỉ số | Cơ sở (2Mb, 250m) | Đề xuất A (11Mb, 350m) | Nhận xét |
|---|---|---|---|
| PDR tổng | 58.89% | **99.27%** | +40 điểm % |
| Gói mất | 3282 | **155** | −95% |
| Throughput tổng | 219.2 kbps | **973.0 kbps** | ×4.4 |
| Throughput TCP | 51.2 kbps | **754.8 kbps** | ×14.7 |
| Jitter tổng | 46.92 ms | **12.67 ms** | |
| PDR luồng tệ nhất | 14.82% (6→16) | **92.65%** | |
| Delay trung bình | 113.39 ms | 108.33 ms | gần như không đổi |

**Thuyết trình:**
- **Rate 11Mb:** mỗi gói chiếm kênh ít thời gian hơn ~5 lần → kênh rảnh hơn, ít xung đột,
  hàng đợi ít tràn. TCP tận dụng ngay phần dung lượng dư → gửi gấp ~16 lần số gói.
- **Tầm phủ 350m:** ít hop hơn, liên kết bền hơn khi node di chuyển → ít đứt route.
- Delay trung bình gần như không giảm vì **nhiều gói trước kia bị mất nay được giao**
  (kể cả những gói phải chờ tìm route lâu) — tức là ta đang đo trên tập gói lớn hơn.
- Lưu ý thực tế: tăng tầm phủ = tăng công suất phát → tốn năng lượng và tăng nhiễu.

---

## Bước 5 – So sánh AODV / DSDV / DSR

```bash
# (vẫn ở wireless/)
for rp in AODV DSDV DSR; do ns wireless.tcl nam 0 rp $rp out ../demo_out/b5_$rp; done
python3 ../analysis/compare.py "AODV=../demo_out/b5_AODV.json" "DSDV=../demo_out/b5_DSDV.json" "DSR=../demo_out/b5_DSR.json" --flows
```

(Script tự đổi hàng đợi sang `CMUPriQueue` khi chọn DSR — yêu cầu bắt buộc của DSR trong NS2.)

**Tóm tắt kết quả (dòng TỔNG):**

| Giao thức | Loại | PDR% | Nhận / Gửi | Thr (kbps) | Delay TB (ms) | Jitter (ms) |
|---|---|---|---|---|---|---|
| **AODV** | Reactive (theo yêu cầu) | 58.89 | 4701 / 7983 | 219.2 | 113.39 | 46.92 |
| **DSDV** | Proactive (bảng định tuyến) | **30.71** | 2177 / 7089 | 100.2 | **12.24** | **8.33** |
| **DSR** | Reactive (định tuyến nguồn) | **63.90** | 4964 / 7768 | **225.8** | 234.22 | 166.20 |

**Chi tiết từng luồng – PDR%:**

| Luồng | AODV | DSDV | DSR |
|---|---|---|---|
| CBR 0→10 | 71.07 | 3.83 | 81.84 |
| CBR 2→12 | 100.00 | 100.00 | 100.00 |
| CBR 4→14 | 29.93 | 16.58 | 36.68 |
| CBR 6→16 | 14.82 | 2.01 | 23.43 |
| TCP 8→18 | 95.11 | **0.00** (chỉ gửi 5 gói) | 95.76 |

**Thuyết trình:**
- **DSDV (proactive):** mọi node định kỳ trao đổi bảng định tuyến. Khi topo thay đổi nhanh,
  bảng **cập nhật không kịp** → nhiều gói bị drop vì "không có route" ⇒ **PDR thấp nhất (31%)**.
  Bù lại, gói nào đi được thì đi ngay, không phải chờ tìm đường ⇒ **delay thấp nhất (12ms)**.
  Luồng TCP 8→18 gần như không thiết lập được (gửi 5 gói SYN/retransmit, nhận 0).
- **AODV (reactive):** chỉ tìm đường khi cần (RREQ/RREP), thích nghi tốt với di chuyển
  ⇒ PDR cao hơn DSDV nhiều, nhưng delay cao do phải chờ tìm route.
- **DSR (reactive, source routing):** gói mang toàn bộ đường đi, có **route cache** nhiều đường dự phòng
  ⇒ **PDR cao nhất (64%)**. Nhưng cache có thể chứa route **cũ/hỏng** → gói đi sai rồi phải
  tìm lại ⇒ **delay và jitter cao nhất** (234ms, 166ms).
- **Kết luận:** với mạng di động, giao thức reactive (AODV, DSR) phù hợp hơn proactive (DSDV).

---

## Bước 6 – Phương án dự phòng

Nếu lúc demo `ns` bị lỗi hoặc máy chậm, mở ngay kết quả đã chạy sẵn:

```bash
nam ~/Projects/ns2-project/results/wired_base.nam &
nam ~/Projects/ns2-project/results/wl_base.nam &
cat ~/Projects/ns2-project/results/wired_base.txt     # bảng kết quả có sẵn (nếu đã chạy run_all.sh bản mới)
cat ~/Projects/ns2-project/results/wl_base.txt
```

Kết quả quét tham số toàn bộ nằm ở `results/summary.json` (do `run_experiments.py` sinh ra).

---

## Chạy kịch bản tùy ý khi giảng viên yêu cầu

Cú pháp chung: `ns <script>.tcl <tên_tham_số> <giá_trị> ... out ../demo_out/<tên>` → bảng in ra màn hình + file `.txt/.html/.nam` trong `demo_out/`.

### Tham số mạng có dây (`wired.tcl`)

| Tham số | Mặc định | Ví dụ giá trị |
|---|---|---|
| `bw` | 1.5Mb | 1Mb, 2Mb, 3Mb, 5Mb |
| `delay` | 20ms | 10ms, 50ms |
| `qlim` | 10 | 5, 20, 50, 100 |
| `qtype` | DropTail | RED, SFQ, DRR, FQ |
| `tcp` | Agent/TCP | Agent/TCP/Reno, Agent/TCP/Newreno, Agent/TCP/Vegas |
| `window` | 20 | 64 |
| `pktsize` | 1000 | 512, 1500 |
| `video` | 1Mb | 500Kb, 1.5Mb |
| `voip_int` / `voip_size` | 0.02 / 160 | |
| `acc_bw` / `acc_delay` | 10Mb / 2ms | |
| `stop` | 60.0 | 20 |
| `nam` | 1 | 0 (không sinh file .nam) |
| `report` | 1 | 0 (không xuất .txt/.html) |
| `out` | ../demo_out/wired | ../demo_out/<tên> |

### Tham số mạng không dây (`wireless.tcl`)

| Tham số | Mặc định | Ví dụ giá trị |
|---|---|---|
| `rp` | AODV | DSDV, DSR |
| `rate` | 2Mb | 1Mb, 5.5Mb, 11Mb |
| `range` | 250 | 350, 450 (mét) |
| `ifqlen` | 50 | 10, 25, 100, 200 |
| `cbr_int` | 0.05 | 0.2, 0.1, 0.025 (càng nhỏ tải càng nặng) |
| `rts` | 0 | 1 (bật RTS/CTS) |
| `x` `y` `scen` | 800 800 scen-20n-800 | 500 500 scen-20n-500 (**đổi cả 3 cùng lúc**) |
| `stop` | 100.0 | |
| `nam` | 1 | 0 |
| `report` | 1 | 0 |
| `out` | ../demo_out/wireless | ../demo_out/<tên> |

### Ví dụ

```bash
# Có dây: thử RED, băng thông 3Mb, queue 30
cd ~/Projects/ns2-project/wired
ns wired.tcl bw 3Mb qtype RED qlim 30 out ../demo_out/thu1    # bảng in ra luôn
xdg-open ../demo_out/thu1.html

# Có dây: so sánh TCP Vegas
cd ~/Projects/ns2-project/wired
ns wired.tcl tcp Agent/TCP/Vegas window 64 out ../demo_out/wired_vegas

# Không dây: vùng nhỏ 500x500 (mật độ node dày hơn)
cd ~/Projects/ns2-project/wireless
ns wireless.tcl x 500 y 500 scen scen-20n-500 out ../demo_out/wl_500

# Không dây: tải nặng gấp đôi + bật RTS/CTS
ns wireless.tcl cbr_int 0.025 rts 1 out ../demo_out/wl_heavy
```

Gõ sai tên tham số, script sẽ báo `Tham so khong hop le: <tên>` và dừng.

---

## Câu hỏi thường gặp & cách trả lời

**H: Tại sao throughput TỔNG không bằng tổng throughput các luồng?**
Đ: Throughput mỗi luồng = byte nhận / *thời gian hoạt động của luồng đó* (từ gói đầu đến gói cuối
nhận được). Dòng TỔNG chia cho khoảng thời gian từ gói đầu tiên đến gói cuối cùng *của tất cả luồng*.
Hai mẫu số khác nhau nên không cộng trực tiếp được (xem `analysis/analyze.py`, dòng 87–107).
Ví dụ rõ nhất: DSDV luồng 4→14 chỉ nhận 292 gói nhưng throughput hiện 82.2 kbps vì luồng chỉ
"sống" trong khoảng thời gian ngắn.

**H: Tại sao UDP lấn át TCP?**
Đ: UDP/CBR gửi tốc độ cố định bất kể mạng; TCP có điều khiển nghẽn (AIMD) – mất gói thì giảm
cửa sổ một nửa (hoặc về 1 với Tahoe). Khi tranh chấp, TCP luôn nhường.

**H: SFQ khác DropTail thế nào?**
Đ: DropTail: một hàng FIFO duy nhất, đầy thì bỏ gói mới đến. SFQ: chia nhiều hàng con theo hàm băm
của luồng, phục vụ xoay vòng → công bằng giữa các luồng, luồng nhỏ không bị luồng lớn chèn ép.

**H: Tại sao không chỉ tăng băng thông mà phải đổi cả hàng đợi?**
Đ: Tăng băng thông giải quyết *dung lượng*, còn hàng đợi quyết định *chia sẻ công bằng* và *độ trễ*.
Phần quét tham số (nhóm `bw` và `qtype` trong `run_experiments.py`) cho thấy tác động riêng của từng yếu tố.

**H: Kết quả có ngẫu nhiên không? Chạy lại có giống không?**
Đ: Mạng có dây hoàn toàn tất định. Mạng không dây dùng file kịch bản di chuyển cố định
(`scen-20n-800`) nên chạy lại cho **đúng kết quả cũ** – đảm bảo so sánh công bằng giữa các cấu hình.

**H: distCST_ = 550 là gì?**
Đ: Carrier Sense Threshold – khoảng cách mà node còn "nghe thấy" kênh đang bận (không giải mã được gói).
Lớn hơn tầm nhận (250m) → gây ra hiện tượng exposed/hidden terminal.

**H: Hạn chế của mô phỏng?**
Đ: Mô hình truyền sóng TwoRayGround lý tưởng (không fading, không vật cản); một kịch bản di chuyển duy nhất;
NS2 đã cũ (2.35), không mô phỏng được 802.11n/ac.

---

## Xử lý sự cố

| Hiện tượng | Nguyên nhân / Cách xử lý |
|---|---|
| Cảnh báo `tclsh8.6 ... doesn't seem to be there anymore` | Bỏ qua, không ảnh hưởng |
| `couldn't open "scen-20n-800"` | Đang chạy `ns` sai thư mục → `cd wireless` trước |
| `Tham so khong hop le: xxx` | Gõ sai tên tham số, xem bảng tham số ở trên |
| `Chua co file ... .json` khi chạy compare | Chưa chạy lệnh `ns ... out` tương ứng, hoặc gõ sai tên/đường dẫn (nhớ `../demo_out/`) |
| `xdg-open` không mở được | Mở trình duyệt rồi kéo thả file `.html` vào, hoặc `firefox ../demo_out/<tên>.html &` |
| Gõ `nam ...` nhưng **không thấy cửa sổ mới** | NAM chỉ chạy **một tiến trình**: file mới được mở thành cửa sổ con trong NAM đang chạy. Tìm cửa sổ `nam: <tên file>`. Nên đóng NAM cũ trước khi mở file mới |
| Mở nhiều lần cùng 1 file NAM | Mỗi lần gọi `nam` tạo thêm 1 cửa sổ – đóng bớt cửa sổ trùng |
| NAM wireless không thấy gì | Bấm Play; nếu node quá nhỏ dùng nút zoom (+) |
| DSR báo lỗi hàng đợi | Script đã tự chuyển sang `CMUPriQueue`; nếu sửa tay `ifq` thì đừng dùng PriQueue với DSR |
| Máy chậm / ns treo | Giảm `stop` (vd `stop 20`), hoặc dùng Bước 6 (kết quả có sẵn) |

---

## Cách nhanh: dùng menu `demo.sh`

Nếu không muốn gõ từng lệnh, menu tự động làm đúng các bước trên:

```bash
cd ~/Projects/ns2-project
./demo.sh
```

| Chọn | Tương ứng |
|---|---|
| 1 | Bước 1 (có dây + NAM) |
| 2 | Bước 3 (không dây + NAM) |
| 3 | Bước 2 (so sánh có dây) |
| 4 | Bước 4 (so sánh không dây) |
| 5 | Bước 5 (AODV/DSDV/DSR) |
| 6 | Bước 6 (mở NAM có sẵn) |

Chạy một kịch bản tùy ý qua script (tự phân tích + mở NAM):

```bash
./demo.sh wired bw 3Mb qtype RED qlim 30
./demo.sh wireless rp DSDV rate 11Mb
NONAM=1 ./demo.sh wired tcp Agent/TCP/Vegas    # không mở NAM, chỉ in bảng
```

> Lưu ý: `demo.sh` ẩn toàn bộ output của `ns` — nếu có lỗi chỉ thấy `ns loi!`.
> Khi đó chạy lệnh `ns` bằng tay (như các bước trên) để xem thông báo lỗi chi tiết.

---

### Thứ tự demo gợi ý (~15 phút)

1. Giới thiệu topo 2 mạng (mục 1) – 2 phút
2. Bước 1 + NAM có dây – 3 phút
3. Bước 2 so sánh có dây – 2 phút
4. Bước 3 + NAM không dây – 3 phút
5. Bước 4 so sánh không dây – 2 phút
6. Bước 5 so sánh định tuyến – 2 phút
7. Kết luận + mở báo cáo PDF – 1 phút
