# -*- coding: utf-8 -*-
"""PREREG型態全量（台股，單筆層）——【偵測器】（研究腳本層；⛔ 不是共用引擎）。
判準＝台股策略線「型態全量_單筆層登錄 seq1」（sha 4a90c43e04a0bef5，21904B）§二～§四；編號＝裁定線 seq173「PREREG型態全量」。
定義出處＝型態線附件 附件-型態知識庫全量_型態線_20260925-1910/（manifest 45 檔 sha256 已逐檔驗過）。

⛔⛔ 本支只產生事件日 T、型態第一根 first、方向 d、事前量（r10／r20／r60）、型態期間報酬（C_T ÷ 第 1 根前一日收盤 − 1）；
   ⛔ 不讀、不算任何 T 以後的價格或報酬（裁定 seq173 §一：跑報酬要等 seq2 四處修正進登錄）。
⛔ patterns_x.py（甲 轉折）、stop_fractal.py（乙 擺動點）只 import、不改。

範圍：96 個變體 ＝ K 棒 68 型（K01～K68，編號＝登錄 §三 #）＋ 價格結構 14 型拆 28 變體（S01～S28，登錄 §四）。

━━ 設計參數（登錄 §二／§四 逐字；出處：無外生出處 ⇒ 逐字標「設計參數」）━━
  K 棒：B̄、R̄ 取第 1 根之前 10 根；長 ≥1.5B̄；長日 ≥3B̄（筆記逐字「三倍」）；十字 R＞0 且 B≤0.1R；小＝非十字且 B≤0.5B̄；
        短影 ≤0.1R；≈ ⇔ |a−b| ≤ 0.2%×b；事前 r10（10 日）
  結構：甲 k＝3、同類間隔 ≥5、確認 t＋3（補齊版 §零）；乙 R＝5 嚴格、確認 t＋5（PREREGM）；離線 2%；平線 0.05%／日；
        跨度 120 日；突破窗 60 日；圓形 250／60／20 日、R² 0.6、中間三分之一
  筆記逐字：M 頭 3%／10%；三重底頂沿用 W 底 5%／10%；擴散 5 次／3 次；V 型 25%／10 日／一半／2 倍；平台 30%／25 日／25%

━━ ⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率之前寫在這裡；交件逐條列出；★＝兩種讀法擇一，〔 〕內是另一讀法）━━
 A1 幾何一律在【該股有效 K 棒序列】上數（第 i 根、前一日、10／20／60 日、轉折左右 k 根、120／60／250 日、1～60 日、10 日）
    （同 PREREGX X1、PREREGM M1、H2 R1）；T＋1、H、判定窗、合併 20 日、區段一律用【交易日曆】（在 researchPatAll_freq.py）。
 A2 K 棒的「第 1 根前一日」＝ 第 1 根的前一根有效 K 棒；r10 ＝ c[第1根−1] ÷ c[第1根−11] − 1；B̄、R̄ ＝ 第 1 根之前 10 根的平均
    （10 根任一根 OHLC 缺值 ⇒ 不成立）；多根型態的「長／小」全部用同一個 B̄（第 1 根之前）。
 A3 ★ B̄ ＝ 0 或 R̄ ＝ 0（前 10 根全是一字線）⇒ 全部 K 棒型態不成立〔另一讀法：照算 ⇒ 任何一根都「長」〕。
 A4 ★ r10 ＝ 0 或缺值 ⇒ 全部 K 棒型態不成立（登錄「r10＝0 ⇒ 不成立」；無明確方向型態的 d ＝ ±sign(r10) 在 r10＝0 時無定義）
    〔另一讀法：只有要求升／降的型態才因 r10＝0 不成立〕。
 A5 「無影」＝ 同一根原始價逐位相等（O＝H、C＝L 等）；★「U＞0」「D＞0」取成「非無上影／非無下影」（原始價）
    〔另一讀法：用還原價算 U＞0；同一天還原因子相同 ⇒ 數學上等價，本讀法只免浮點雜訊〕。
 A6 「≈」的 b ＝ 登錄記號右邊那個（C2≈C1 ⇒ |C2−C1| ≤ 0.2%×C1；O3≈C2 ⇒ ×C2；C2≈L1 ⇒ ×L1）。
 A7 型態期間報酬 ＝ c[T] ÷ c[first−1] − 1（K 棒：first＝第 1 根；結構：first＝下面 B 各條的第一點）；r20、r60 同式（20、60 根）。
 B1 甲（S1～S3）：PX.pivot_seq 原樣（還原收盤、k＝3、間隔 ≥5、確認 t＋3、平手取最早、間隔內較極端者取代）；
    同時只追一組；新轉折確認（序列變動）⇒ 舊組結束、新組在確認當根即判（同 X3）；
    ★「P1 到 T ≤ 60 日」含頭尾：T − P1 ＋ 1 ≤ 60（同 X4）。
 B2 S1 M 頭：V ＝ c[P1..P2] 最低；T ＝ 確認日起第一個 c ＜ C_V。r60 在 P1（c[P1−1]÷c[P1−61]−1）＞0。
    S2 三重底：兩兩差 ÷ 最低者 ＝ (max−min)÷min ≤ 5%；A ＝ max(c[L1..L2]) 與 max(c[L2..L3]) 較高者；(C_A − 最低底)÷最低底 ≥ 10%。
    S3 三重頂（S2 鏡像）★：(max−min)÷min（三個頂）≤ 5%〔另一讀法：÷ 最高者〕；V ＝ 兩個回檔低點較低者；(最高頂 − C_V)÷最高頂 ≥ 10%。
 B3 乙（S4～S21）：高點 ＝ SF.swing_lows(−還原high, 5)、低點 ＝ SF.swing_lows(還原low, 5)，第 s 根在 s＋5 收盤才確認。
    同一根 b：① 先用 b 開盤前的組判 b（過期／過交點／突破）② 再加入 b 收盤剛確認的轉折、重建組（舊組結束；同 PREREGM M3、M4）。
 B4 ★ 三角／楔形／擴散的轉折集合 ＝ 最新已確認轉折 s_last 往回 120 日內（s ≥ s_last − 119，含頭尾 120 日）的全部高點與全部低點
    （＝「最近連續已確認」、且「第一個轉折到最後一個 ≤ 120 日」）；上線 ＝ 這些高點（還原 high）對日序的最小平方線、下線同理（還原 low）；
    各需 ≥ 2 點；「線上」＝ |y − ŷ| ≤ 2% × ŷ〔另一讀法：只取落在線上的連續轉折再重配〕。
 B5 斜率分類用相對斜率 β ÷ ȳ（ȳ ＝ 該線各點 y 的平均）：上揚 ＞ 0.05%／日、下彎 ＜ −0.05%／日、平 ＝ |·| ≤ 0.05%／日；
    六類互斥：對稱（上下彎、下上揚）、上升三角（上平、下上揚）、下降三角（上下彎、下平）、上升楔形（皆上揚且 β_下 ＞ β_上）、
    下降楔形（皆下彎且 β_上 ＜ β_下）、擴散（上上揚、下下彎）；其他組合（皆平、同向但不收斂…）＝ 無型態。
    「兩線在未來相交」＝ 在重建那一根 b：ℓ_上(b) ＞ ℓ_下(b) 且 β_上 ＜ β_下（收斂類）；擴散只要求 ℓ_上(b) ＞ ℓ_下(b)。
    碰觸：三角／楔形 ＝ 上線上 ≥2、下線上 ≥2、合計 ≥5；擴散 ＝ 合計 ≥5 且其中一邊 ≥3（筆記逐字，不另要求每邊 ≥2 條「在線上」）。
    擴散頂／底 ＝ 集合第一個轉折的 r60 ＞0／＜0（＝0 或缺值 ⇒ 不成立）。
 B6 突破：可判 b ∈ [conf＋1, conf＋60]（conf ＝ 最後轉折確認日；同 PREREGM M2）；★ 向上 ＝ c[b] ＞ ℓ_上(b) 且 c[b−1] ≤ ℓ_上(b−1)、
    向下 ＝ c[b] ＜ ℓ_下(b) 且 c[b−1] ≥ ℓ_下(b−1)（「越過」＝ 由內而外，同 PREREGM M8；〔另一讀法：窗內第一個在線外的收盤〕）；
    ★ 收斂類過了交點（ℓ_上(b) ≤ ℓ_下(b)）⇒ 組結束、無事件〔另一讀法：交點後照判〕。
 B7 鑽石 ★：後段 ＝ 最近 2 個高點與最近 2 個低點中較早那一個起到最新轉折（其間全部轉折都算）；前段 ＝ 後段之前最近 2 個高點與
    2 個低點中較早那一個起、到後段前一個轉折；兩段各自配最小平方線（前段：上線上揚、下線下彎；後段：上線下彎、下線上揚，門檻同 B5）；
    first ＝ 前段第一個轉折，s_last − first ＋ 1 ≤ 120；後段在 conf 時 ℓ_上 ＞ ℓ_下；突破後段的線（同 B6）；頂／底照 first 的 r60。
    〔另一讀法：窮舉切點〕。登錄沒寫 2% 碰觸 ⇒ 鑽石不要求。
 B8 S22 圓形底：在每個 T：a ＝ [T−250, T−60] 最高收盤（平手取最早）；★「首次」＝ c[T] ＞ c[a] 且 c[a+1..T−1] 全部 ≤ c[a]；
    a～T−1 收盤對日序二次最小平方：γ ＞0、R² ≥0.6、頂點 −β/2γ ∈ [a＋(T−1−a)/3, a＋2(T−1−a)/3]；b ＝ c[a..T−1] 最低（平手取最早）；
    b−a ≥20、T−b ≥20；r60 在 a ＜0。first ＝ a。
 B9 S23／S24 圓形頂（鏡像）：a ＝ [T−250, T−60] 最低收盤；γ ＜0；b ＝ c[a..T−1] 最高；向上 ＝ c[T] ＞ c[b]（弧頂最高收盤）；
    向下 ＝ c[T] ＜ c[a]；★「先發生者為準」＝ 兩者都要求 c[a+1..T−1] 全部 ≥ c[a]（向下未先發生）；向上未先發生由 b 為 a..T−1
    最高自動成立；★ r60 在 a ＞0（S22「a 之前 r60＜0」的鏡像；登錄 S23 列沒逐字寫〔另一讀法：不要求〕）。
 B10 S25／S26 島型：b 全跳空（頂：H_b ＜ L_{b−1}）、量 v_b ＞ 前 20 根均量；a ∈ [b−60, b−1] 全跳空反向（頂：L_a ＞ H_{a−1}）；
    ★ 兩缺口區間重疊取閉區間（端點相等算重疊）；★ 多個 a 符合 ⇒ 取最近的 a（最小的島）；r60 在 a（頂 ＞0、底 ＜0）；first ＝ a。
 B11 S27 V 底：b ＝ c[b] ≤ c[b−19..b−1]（近 20 日最低收盤日，平手算）；前高 P ＝ max c[b−20..b−1]（first ＝ 其日，平手取最早）；
    (P − c_b)÷P ≥ 25%；v_b ≥ 2 × mean v[b−20..b−1]；T ＝ (b, b＋10] 內第一個 c ≥ c_b ＋ 0.5(P − c_b)；
    同一個 T 由多個 b 產生 ⇒ 取最近的 b。
 B12 S28 平台：盤整區 ＝ 以 T−1 結尾、max H ÷ min L − 1 ≤ 25% 的最長區間 [s, T−1]（長 ≥ 25）；c[T] ＞ 該區最高 H；
    c[s] ÷ min c[s−60..s−1] − 1 ≥ 30%；★ first ＝ 該 60 日最低收盤日（前段漲幅的起點；〔另一讀法：first ＝ s〕）。
 B13 所有比較遇缺值（還原 OHLC 或量）⇒ 不成立。
"""
from __future__ import annotations
import os
import sys
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns_x as PX       # noqa: E402  甲 轉折（只 import）
from backtest import stop_fractal as SF     # noqa: E402  乙 擺動點（只 import）

# ── 設計參數（K 棒）
NB, LONG, LONGDAY, DOJI, SMALL, SHORT, APPROX, PRE_N = 10, 1.5, 3.0, 0.1, 0.5, 0.1, 0.002, 10
# ── 設計參數／筆記逐字（結構）
A_K, A_GAP, A_WIN = PX.K, PX.GAP, 60
M_EQ, M_DEPTH = 0.03, 0.10
T_EQ, T_BOUNCE = 0.05, 0.10
B_R, LINE_TOL, FLAT, SPAN, LIFE = 5, 0.02, 0.0005, 120, 60
BR_TOTAL, BR_SIDE = 5, 3
RD_BACK, RD_MIN, RD_DIST, RD_R2 = 250, 60, 20, 0.6
IS_MAX, IS_VOL = 60, 20
V_LB, V_DROP, V_VOL, V_WIN, V_HALF = 20, 0.25, 2.0, 10, 0.5
PF_RISE, PF_MINLEN, PF_RANGE, PF_LB = 0.30, 25, 0.25, 60
R60 = 60

# ═════════════ 變體表 ═════════════
# (編號, 型態名, 根數, 事前, d, 健檢總表列名)；d：+1／−1，或 "續"（＝sign(r10)）、"反"（＝−sign(r10)）
K_TABLE = [
    (1, "三隻烏鴉", 3, "升", -1, "三隻烏鴉"), (2, "昏星", 3, "升", -1, "昏星"),
    (3, "倒鎚（兩根）", 2, "降", -1, "倒鎚"), (4, "相同低點", 2, "降", -1, "相同低點"),
    (5, "跳空雙黑線", 2, "降", -1, "跳空雙黑線"), (6, "空頭Breakaway", 5, "升", -1, "空頭Breakaway（缺口收復）"),
    (7, "晨星", 3, "降", 1, "晨星"), (8, "貫穿線", 2, "降", 1, "貫穿線"),
    (9, "三明治線", 3, "降", -1, "三明治線"), (10, "Thrusting", 2, "降", 1, "Thrusting"),
    (11, "空頭會合線", 2, "升", 1, "空頭會合線"), (12, "In Neck", 2, "降", -1, "In Neck"),
    (13, "多頭會合線", 2, "降", 1, "多頭會合線"), (14, "長黑日", 1, "無", "續", "長黑日"),
    (15, "歸巢鴿", 2, "降", -1, "歸巢鴿"), (16, "烏雲蓋頂", 2, "升", -1, "烏雲蓋頂"),
    (17, "十字晨星", 3, "降", 1, "十字晨星"), (18, "十字昏星", 3, "升", -1, "十字昏星"),
    (19, "胃部之上", 2, "降", 1, "胃部之上"), (20, "紅三兵", 3, "降", 1, "紅三兵"),
    (21, "On Neck", 2, "降", -1, "On Neck"), (22, "力車夫", 1, "無", "續", "力車夫"),
    (23, "多頭分離線", 2, "升", 1, "多頭分離線"), (24, "長腳十字", 1, "無", "續", "長腳十字"),
    (25, "多頭母子線", 2, "降", 1, "多頭母子線"), (26, "空頭分離線", 2, "降", -1, "空頭分離線"),
    (27, "收盤黑色光頭光腳", 1, "無", "續", "收盤黑色光頭光腳"), (28, "平頭底部", 2, "降", -1, "平頭底部"),
    (29, "多頭Breakaway", 5, "降", 1, "多頭Breakaway（缺口收復）"), (30, "多久里線", 1, "降", 1, "多久里線"),
    (31, "最後吞噬底", 2, "降", -1, "最後吞噬底"), (32, "看漲十字星", 2, "降", -1, "看漲十字星"),
    (33, "多頭母子十字", 2, "降", -1, "多頭母子十字"), (34, "看跌十字星", 2, "升", 1, "看跌十字星"),
    (35, "長白日", 1, "無", "續", "長白日"), (36, "上漲受阻", 3, "升", 1, "上漲受阻"),
    (37, "黑色光頭光腳", 1, "無", "續", "黑色光頭光腳"), (38, "開盤黑色光頭光腳", 1, "無", "續", "開盤黑色光頭光腳"),
    (39, "胃部之下", 2, "升", -1, "胃部之下"), (40, "短黑蠟燭", 1, "無", "反", "短黑蠟燭"),
    (41, "高浪線", 1, "無", "反", "高浪線"), (42, "白色蠟燭", 1, "無", "續", "白色蠟燭"),
    (43, "白色紡錘線", 1, "無", "反", "白色紡錘線"), (44, "收盤白色光頭光腳", 1, "無", "續", "收盤白色光頭光腳"),
    (45, "白色光頭光腳", 1, "無", "續", "白色光頭光腳"), (46, "空頭母子線", 2, "升", 1, "空頭母子線"),
    (47, "黑色紡錘線", 1, "無", "反", "黑色紡錘線"), (48, "開盤白色光頭光腳", 1, "無", "續", "開盤白色光頭光腳"),
    (49, "墓碑十字", 1, "升", -1, "墓碑十字"), (50, "南方十字", 1, "降", 1, "南方十字"),
    (51, "最後吞噬頂", 2, "升", 1, "最後吞噬頂"), (52, "空頭母子十字", 2, "升", 1, "空頭母子十字"),
    (53, "平頭頂部", 2, "升", 1, "平頭頂部"), (54, "黑色蠟燭", 1, "無", "續", "黑色蠟燭"),
    (55, "北方十字", 1, "升", 1, "北方十字"), (56, "多頭吞噬", 2, "降", 1, "多頭吞噬"),
    (57, "短白蠟燭", 1, "無", "反", "短白蠟燭"), (58, "吊人", 1, "升", 1, "吊人"),
    (59, "向下跳空十字", 1, "降", 1, "向下跳空十字"), (60, "下跌三法", 5, "降", -1, "下跌三法"),
    (61, "空頭吞噬", 2, "升", -1, "空頭吞噬"), (62, "向上跳空十字", 1, "升", -1, "向上跳空十字"),
    (63, "停頓型態", 3, "升", 1, "停頓型態"), (64, "上升三法", 5, "升", 1, "上升三法"),
    (65, "看漲反沖線", 2, "降", 1, "看漲反沖線"), (66, "崩潰十字星", 3, "升", -1, "崩潰十字星"),
    (67, "蜻蜓十字", 1, "降", 1, "蜻蜓十字"), (68, "看跌反沖線", 2, "升", -1, "看跌反沖線"),
]
# (編號, 變體名, d, 族, 出處型態名〔還沒測的型態表〕)
S_TABLE = [
    (1, "M頭", -1, "甲", "M頭"), (2, "三重底", 1, "甲", "三重底"), (3, "三重頂", -1, "甲", "三重頂"),
    (4, "對稱三角_向上", 1, "乙", "三角收斂"), (5, "對稱三角_向下", -1, "乙", "三角收斂"),
    (6, "上升三角_向上", 1, "乙", "三角收斂"), (7, "上升三角_向下", -1, "乙", "三角收斂"),
    (8, "下降三角_向上", 1, "乙", "三角收斂"), (9, "下降三角_向下", -1, "乙", "三角收斂"),
    (10, "上升楔形_向上", 1, "乙", "楔形"), (11, "上升楔形_向下", -1, "乙", "楔形"),
    (12, "下降楔形_向上", 1, "乙", "楔形"), (13, "下降楔形_向下", -1, "乙", "楔形"),
    (14, "擴散頂_向上", 1, "乙", "擴散頂"), (15, "擴散頂_向下", -1, "乙", "擴散頂"),
    (16, "擴散底_向上", 1, "乙", "擴散底"), (17, "擴散底_向下", -1, "乙", "擴散底"),
    (18, "鑽石頂_向上", 1, "乙", "鑽石頂"), (19, "鑽石頂_向下", -1, "乙", "鑽石頂"),
    (20, "鑽石底_向上", 1, "乙", "鑽石底"), (21, "鑽石底_向下", -1, "乙", "鑽石底"),
    (22, "圓形底", 1, "圓", "圓形底"), (23, "圓形頂_向上", 1, "圓", "圓形頂"), (24, "圓形頂_向下", -1, "圓", "圓形頂"),
    (25, "島型頂", -1, "島", "島型反轉"), (26, "島型底", 1, "島", "島型反轉"),
    (27, "V型反轉", 1, "V", "V型反轉"), (28, "平台整理", 1, "平", "平台整理"),
]


def vid_k(n):
    return "K{:02d}".format(n)


def vid_s(n):
    return "S{:02d}".format(n)


VARIANTS = ([{"vid": vid_k(n), "name": nm, "k": k, "pre": pre, "d": d, "fam": "K", "hc": hc} for n, nm, k, pre, d, hc in K_TABLE]
            + [{"vid": vid_s(n), "name": nm, "k": None, "pre": None, "d": d, "fam": fam, "src": src} for n, nm, d, fam, src in S_TABLE])
VID = [v["vid"] for v in VARIANTS]
VMAP = {v["vid"]: v for v in VARIANTS}
_SNAME = {nm: vid_s(n) for n, nm, *_ in S_TABLE}
assert len(VARIANTS) == 96 and len(set(VID)) == 96


# ═════════════ 小工具 ═════════════
def _sh(x, s):
    """out[j] ＝ x[j−s]（s ≥ 0）；前 s 個填 NaN／False。"""
    if s == 0:
        return x
    out = np.empty_like(x)
    out[:s] = False if x.dtype == bool else np.nan
    out[s:] = x[:-s]
    return out


def _winmean(x, n):
    """m[t] ＝ mean(x[t−n..t−1])（每窗獨立計算、不用累加和 ⇒ 前綴不變、無浮點漂移）；窗內有 NaN ⇒ NaN。"""
    out = np.full(len(x), np.nan)
    if len(x) > n:
        W = np.lib.stride_tricks.sliding_window_view(x, n)[:len(x) - n]
        out[n:] = W.mean(axis=1)
    return out


def _rN(c, N):
    """r[t] ＝ c[t−1] ÷ c[t−1−N] − 1（t 為型態第一點）。"""
    out = np.full(len(c), np.nan)
    if len(c) > N + 1:
        with np.errstate(invalid="ignore", divide="ignore"):
            out[N + 1:] = c[N:-1] / c[:-(N + 1)] - 1.0
    return out


# ═════════════ K 棒 68 型 ═════════════
def kbar_feats(o, h, l, c, ro, rh, rl, rc):
    F = {}
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c) & np.isfinite(ro) & np.isfinite(rh) & np.isfinite(rl) & np.isfinite(rc)
        B = np.abs(c - o); R = h - l
        top = np.fmax(o, c); bot = np.fmin(o, c)
        F.update(O=o, H=h, L=l, C=c, B=B, R=R, top=top, bot=bot, U=h - top, D=bot - l, mid=(o + c) / 2.0,
                 wh=ok & (c > o), bk=ok & (c < o), doji=ok & (R > 0) & (B <= DOJI * R), ok=ok,
                 rOH=ok & (ro == rh), rOL=ok & (ro == rl), rCH=ok & (rc == rh), rCL=ok & (rc == rl),
                 rnoU=ok & (rh == np.fmax(ro, rc)), rnoD=ok & (rl == np.fmin(ro, rc)))
        Bn = np.where(ok, B, np.nan); Rn = np.where(ok, R, np.nan)
    F["Bm"] = _winmean(Bn, NB); F["Rm"] = _winmean(Rn, NB)
    F["r10"] = _rN(c, PRE_N)
    return F


def _kcond(num, g, Bm, Rm):
    """登錄 §三 機器條件（g(名, i)：第 i 根；i＝0 ⇒ 第 1 根前一日）。"""
    B = lambda i: g("B", i)
    lng = lambda i: g("B", i) >= LONG * Bm
    lday = lambda i: g("B", i) >= LONGDAY * Bm
    sml = lambda i: (~g("doji", i)) & (g("B", i) <= SMALL * Bm) & g("ok", i)
    wh = lambda i: g("wh", i)
    bk = lambda i: g("bk", i)
    dj = lambda i: g("doji", i)
    O = lambda i: g("O", i); H = lambda i: g("H", i); L = lambda i: g("L", i); C = lambda i: g("C", i)
    U = lambda i: g("U", i); D = lambda i: g("D", i); Rg = lambda i: g("R", i)
    top = lambda i: g("top", i); bot = lambda i: g("bot", i); mid = lambda i: g("mid", i)
    apx = lambda a, b: np.abs(a - b) <= APPROX * b
    inb = lambda x, i: (x >= bot(i)) & (x <= top(i))
    noU = lambda i: g("rnoU", i); noD = lambda i: g("rnoD", i)
    posU = lambda i: g("ok", i) & ~g("rnoU", i); posD = lambda i: g("ok", i) & ~g("rnoD", i)
    fn = {
        1: lambda: bk(1) & lng(1) & bk(2) & lng(2) & bk(3) & lng(3) & (D(1) <= SHORT * Rg(1)) & (D(2) <= SHORT * Rg(2)) & (D(3) <= SHORT * Rg(3))
        & (C(1) > C(2)) & (C(2) > C(3)) & inb(O(2), 1) & inb(O(3), 2),
        2: lambda: wh(1) & lng(1) & sml(2) & (bot(2) > top(1)) & bk(3) & (top(3) < bot(2)) & (C(3) <= mid(1)),
        3: lambda: bk(1) & lng(1) & (D(1) <= SHORT * Rg(1)) & sml(2) & (U(2) >= 2 * B(2)) & (D(2) <= SHORT * Rg(2)) & (O(2) < C(1)),
        4: lambda: bk(1) & bk(2) & apx(C(2), C(1)),
        5: lambda: bk(1) & (H(1) < L(0)) & g("ok", 0) & bk(2) & (H(2) < H(1)),
        6: lambda: wh(1) & lng(1) & wh(2) & (bot(2) > top(1)) & (C(3) > C(2)) & (C(4) > C(3)) & bk(5) & lng(5) & (top(1) < C(5)) & (C(5) < bot(2)),
        7: lambda: bk(1) & lng(1) & sml(2) & (top(2) < bot(1)) & wh(3) & (bot(3) > top(2)) & (C(3) >= mid(1)),
        8: lambda: bk(1) & lng(1) & wh(2) & (O(2) < L(1)) & (mid(1) < C(2)) & (C(2) < O(1)),
        9: lambda: bk(1) & wh(2) & (C(2) > C(1)) & bk(3) & apx(C(3), C(1)),
        10: lambda: bk(1) & lng(1) & wh(2) & (O(2) < L(1)) & (C(1) + 0.1 * B(1) < C(2)) & (C(2) < mid(1)),
        11: lambda: wh(1) & lng(1) & bk(2) & lng(2) & apx(C(2), C(1)),
        12: lambda: bk(1) & lng(1) & wh(2) & (O(2) < L(1)) & (C(1) <= C(2)) & (C(2) <= C(1) + 0.1 * B(1)),
        13: lambda: bk(1) & lng(1) & wh(2) & lng(2) & apx(C(2), C(1)),
        14: lambda: bk(1) & lday(1) & (U(1) < B(1)) & (D(1) < B(1)),
        15: lambda: bk(1) & lng(1) & bk(2) & ~lng(2) & (top(2) <= top(1)) & (bot(2) >= bot(1)),
        16: lambda: wh(1) & lng(1) & bk(2) & (O(2) > H(1)) & (O(1) < C(2)) & (C(2) < mid(1)),
        17: lambda: bk(1) & lng(1) & dj(2) & (top(2) < bot(1)) & wh(3) & lng(3) & (bot(3) > top(2)),
        18: lambda: wh(1) & lng(1) & dj(2) & (bot(2) > top(1)) & (bot(2) > top(3)) & bk(3) & lng(3) & (C(3) <= mid(1)),
        19: lambda: bk(1) & wh(2) & (O(2) >= mid(1)) & (C(2) >= mid(1)),
        20: lambda: wh(1) & lng(1) & wh(2) & lng(2) & wh(3) & lng(3) & (U(1) <= SHORT * Rg(1)) & (U(2) <= SHORT * Rg(2)) & (U(3) <= SHORT * Rg(3))
        & (C(1) < C(2)) & (C(2) < C(3)) & inb(O(2), 1) & inb(O(3), 2),
        21: lambda: bk(1) & lng(1) & wh(2) & (O(2) < L(1)) & apx(C(2), L(1)),
        22: lambda: _ll(g, Rm) & (np.abs(mid(1) - (H(1) + L(1)) / 2.0) <= 0.1 * Rg(1)),
        23: lambda: bk(1) & lng(1) & wh(2) & lng(2) & apx(O(2), O(1)),
        24: lambda: _ll(g, Rm),
        25: lambda: bk(1) & lng(1) & wh(2) & (top(2) <= top(1)) & (bot(2) >= bot(1)) & (B(2) < B(1)),
        26: lambda: wh(1) & lng(1) & bk(2) & lng(2) & apx(O(2), O(1)),
        27: lambda: bk(1) & lng(1) & g("rCL", 1) & posU(1),
        28: lambda: g("ok", 1) & g("ok", 2) & apx(L(2), L(1)),
        29: lambda: bk(1) & lng(1) & bk(2) & (top(2) < bot(1)) & (C(3) < C(2)) & (C(4) < C(3)) & wh(5) & lng(5) & (top(2) < C(5)) & (C(5) < bot(1)),
        30: lambda: sml(1) & (D(1) >= 3 * B(1)) & (U(1) <= SHORT * Rg(1)),
        31: lambda: wh(1) & bk(2) & (top(2) >= top(1)) & (bot(2) <= bot(1)),
        32: lambda: bk(1) & lng(1) & dj(2) & (top(2) < bot(1)),
        33: lambda: wh(1) & lng(1) & dj(2) & (H(2) <= H(1)) & (L(2) >= L(1)),
        34: lambda: wh(1) & lng(1) & dj(2) & (bot(2) > top(1)),
        35: lambda: wh(1) & lday(1) & (U(1) < B(1)) & (D(1) < B(1)),
        36: lambda: wh(1) & wh(2) & wh(3) & inb(O(2), 1) & inb(O(3), 2) & (U(1) < U(2)) & (U(2) < U(3)),
        37: lambda: bk(1) & g("rOH", 1) & g("rCL", 1),
        38: lambda: bk(1) & lng(1) & g("rOH", 1) & posD(1),
        39: lambda: wh(1) & lng(1) & bk(2) & (O(2) <= mid(1)) & (C(2) <= mid(1)),
        40: lambda: bk(1) & sml(1) & (U(1) < B(1)) & (D(1) < B(1)),
        41: lambda: sml(1) & (U(1) >= 3 * B(1)) & (D(1) >= 3 * B(1)),
        42: lambda: wh(1) & (B(1) > SMALL * Bm) & (B(1) < LONG * Bm) & (U(1) < B(1)) & (D(1) < B(1)),
        43: lambda: wh(1) & sml(1) & (U(1) > B(1)) & (D(1) > B(1)),
        44: lambda: wh(1) & lng(1) & g("rCH", 1) & posD(1),
        45: lambda: wh(1) & g("rOL", 1) & g("rCH", 1),
        46: lambda: wh(1) & lng(1) & bk(2) & (top(2) <= top(1)) & (bot(2) >= bot(1)) & (B(2) < B(1)),
        47: lambda: bk(1) & sml(1) & (U(1) > B(1)) & (D(1) > B(1)),
        48: lambda: wh(1) & lng(1) & g("rOL", 1) & posU(1),
        49: lambda: dj(1) & (D(1) <= SHORT * Rg(1)),
        50: lambda: dj(1),
        51: lambda: bk(1) & wh(2) & (top(2) >= top(1)) & (bot(2) <= bot(1)),
        52: lambda: wh(1) & lng(1) & dj(2) & (H(2) <= H(1)) & (L(2) >= L(1)),
        53: lambda: g("ok", 1) & g("ok", 2) & apx(H(2), H(1)),
        54: lambda: bk(1) & (B(1) > SMALL * Bm) & (B(1) < LONG * Bm) & (U(1) < B(1)) & (D(1) < B(1)),
        55: lambda: dj(1),
        56: lambda: bk(1) & wh(2) & (top(2) >= top(1)) & (bot(2) <= bot(1)) & (B(2) > B(1)),
        57: lambda: wh(1) & sml(1) & (U(1) < B(1)) & (D(1) < B(1)),
        58: lambda: g("ok", 1) & ~dj(1) & (D(1) >= 2 * B(1)) & (U(1) <= SHORT * Rg(1)),
        59: lambda: dj(1) & g("ok", 0) & (H(1) < L(0)),
        60: lambda: bk(1) & lng(1) & sml(2) & sml(3) & sml(4) & (L(1) <= C(2)) & (C(2) <= H(1)) & (L(1) <= C(3)) & (C(3) <= H(1))
        & (L(1) <= C(4)) & (C(4) <= H(1)) & (C(2) < C(3)) & (C(3) < C(4)) & bk(5) & lng(5) & (C(5) < C(1)),
        61: lambda: wh(1) & bk(2) & (top(2) >= top(1)) & (bot(2) <= bot(1)) & (B(2) > B(1)),
        62: lambda: dj(1) & g("ok", 0) & (L(1) > H(0)),
        63: lambda: wh(1) & lng(1) & wh(2) & lng(2) & wh(3) & sml(3) & apx(O(3), C(2)),
        64: lambda: wh(1) & lng(1) & sml(2) & sml(3) & sml(4) & (L(1) <= C(2)) & (C(2) <= H(1)) & (L(1) <= C(3)) & (C(3) <= H(1))
        & (L(1) <= C(4)) & (C(4) <= H(1)) & (C(2) > C(3)) & (C(3) > C(4)) & wh(5) & lng(5) & (C(5) > C(1)),
        65: lambda: bk(1) & g("rOH", 1) & g("rCL", 1) & wh(2) & g("rOL", 2) & g("rCH", 2) & (L(2) > H(1)),
        66: lambda: wh(1) & dj(2) & (H(2) < L(1)) & bk(3) & (H(3) < L(2)),
        67: lambda: dj(1) & (U(1) <= SHORT * Rg(1)),
        68: lambda: wh(1) & g("rOL", 1) & g("rCH", 1) & bk(2) & g("rOH", 2) & g("rCL", 2) & (H(2) < L(1)),
    }[num]
    return fn()


def _ll(g, Rm):
    """#24 長腳十字：十字、R ≥ 1.5R̄、U ≥ 0.25R、D ≥ 0.25R。"""
    R = g("R", 1)
    return g("doji", 1) & (R >= LONG * Rm) & (g("U", 1) >= 0.25 * R) & (g("D", 1) >= 0.25 * R)


def detect_kbars(o, h, l, c, ro, rh, rl, rc):
    """有效 K 棒序列 ⇒ {vid: {T, first, d, r10}}（索引＝有效 K 棒序號）。"""
    F = kbar_feats(o, h, l, c, ro, rh, rl, rc)
    n = len(c); out = {}
    cache = {}
    for num, nm, k, pre, d, _ in K_TABLE:
        def g(name, i, k=k):
            key = (name, k - i)
            if key not in cache:
                cache[key] = _sh(F[name], k - i)
            return cache[key]
        Bm = g("Bm", 1); Rm = g("Rm", 1); r10 = g("r10", 1)
        with np.errstate(invalid="ignore"):
            m = _kcond(num, g, Bm, Rm)
            okall = np.ones(n, bool)
            for i in range(1, k + 1):
                okall &= g("ok", i)
            m = m & okall & np.isfinite(Bm) & np.isfinite(Rm) & (Bm > 0) & (Rm > 0) & np.isfinite(r10) & (r10 != 0)
            if pre == "升":
                m &= r10 > 0
            elif pre == "降":
                m &= r10 < 0
        T = np.flatnonzero(m)
        rr = r10[T]
        if d == "續":
            dd = np.sign(rr)
        elif d == "反":
            dd = -np.sign(rr)
        else:
            dd = np.full(len(T), float(d))
        out[vid_k(num)] = {"T": T, "first": T - k + 1, "d": dd.astype(np.int8)}
    return out


# ═════════════ 價格結構：甲（S1～S3） ═════════════
def _turn_track(c, seq, need, mk, lag_ok=True):
    """同 PX.detect_turn 的 X3 順序：① 舊組判 b ② b 收盤剛確認的轉折 ⇒ 換組 ③ 新組當根即判。回 [(T, first)]。"""
    n = len(c); G = None; ev = []

    def judge(G, b):
        if b - G["first"] + 1 > A_WIN:
            return "expire"
        if G["up"]:
            return "trig" if c[b] > G["lv"] else None
        return "trig" if c[b] < G["lv"] else None

    for b in range(n):
        if G is not None:
            r = judge(G, b)
            if r == "trig":
                ev.append((b, G["first"])); G = None
            elif r == "expire":
                G = None
        tail = seq.get(b)
        if tail is not None:
            G = mk(tail) if len(tail) >= need else None
            if G is not None:
                r = judge(G, b)
                if r == "trig":
                    ev.append((b, G["first"])); G = None
                elif r == "expire":
                    G = None
    return ev


def detect_turns(c, r60, lag=None):
    hi = PX.pivot_seq(c, "H", lag=lag); lo = PX.pivot_seq(c, "L", lag=lag)

    def mk_m(tail):
        P1, P2 = tail[-2], tail[-1]
        if not (abs(c[P2] - c[P1]) / c[P1] <= M_EQ):
            return None
        cv = float(np.min(c[P1:P2 + 1]))
        if not ((c[P1] - cv) / c[P1] >= M_DEPTH):
            return None
        if not (r60[P1] > 0):
            return None
        return {"first": P1, "lv": cv, "up": False}

    def mk_tb(tail):
        L1, L2, L3 = tail[-3], tail[-2], tail[-1]
        v = c[[L1, L2, L3]]; mn = float(v.min())
        if not ((v.max() - mn) / mn <= T_EQ):
            return None
        cA = max(float(np.max(c[L1:L2 + 1])), float(np.max(c[L2:L3 + 1])))
        if not ((cA - mn) / mn >= T_BOUNCE):
            return None
        if not (r60[L1] < 0):
            return None
        return {"first": L1, "lv": cA, "up": True}

    def mk_tt(tail):
        P1, P2, P3 = tail[-3], tail[-2], tail[-1]
        v = c[[P1, P2, P3]]; mn = float(v.min()); mx = float(v.max())
        if not ((mx - mn) / mn <= T_EQ):
            return None
        cV = min(float(np.min(c[P1:P2 + 1])), float(np.min(c[P2:P3 + 1])))
        if not ((mx - cV) / mx >= T_BOUNCE):
            return None
        if not (r60[P1] > 0):
            return None
        return {"first": P1, "lv": cV, "up": False}

    return {vid_s(1): _turn_track(c, hi, 2, mk_m), vid_s(2): _turn_track(c, lo, 3, mk_tb), vid_s(3): _turn_track(c, hi, 3, mk_tt)}


# ═════════════ 價格結構：乙（S4～S21） ═════════════
def _fit(xs, ys):
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    xm = xs.mean(); ym = ys.mean(); dx = xs - xm
    sxx = float((dx * dx).sum())
    if sxx <= 0:
        return None
    beta = float((dx * (ys - ym)).sum()) / sxx
    alpha = ym - beta * xm
    yhat = alpha + beta * xs
    with np.errstate(invalid="ignore", divide="ignore"):
        on = int(np.sum(np.abs(ys - yhat) <= LINE_TOL * yhat))
    return {"a": alpha, "b": beta, "rel": beta / ym if ym != 0 else np.nan, "on": on}


def _cls(rel):
    if not np.isfinite(rel):
        return None
    return "up" if rel > FLAT else ("dn" if rel < -FLAT else "flat")


def _build_line(piv, b, r60):
    """B4／B5：回組或 None。piv ＝ 已確認轉折 [(s, kind, y)]，依 s 排序。"""
    s_last = piv[-1][0]
    S = [p for p in piv if p[0] >= s_last - (SPAN - 1)]
    Hs = [(s, y) for s, k, y in S if k == "H"]; Ls = [(s, y) for s, k, y in S if k == "L"]
    if len(Hs) < 2 or len(Ls) < 2:
        return None
    fu = _fit(*zip(*Hs)); fl = _fit(*zip(*Ls))
    if fu is None or fl is None:
        return None
    cu, cl = _cls(fu["rel"]), _cls(fl["rel"])
    typ = None
    if cu == "dn" and cl == "up":
        typ = "sym"
    elif cu == "flat" and cl == "up":
        typ = "asc"
    elif cu == "dn" and cl == "flat":
        typ = "desc"
    elif cu == "up" and cl == "up" and fl["b"] > fu["b"]:
        typ = "rw"
    elif cu == "dn" and cl == "dn" and fu["b"] < fl["b"]:
        typ = "fw"
    elif cu == "up" and cl == "dn":
        typ = "br"
    if typ is None:
        return None
    lu = fu["a"] + fu["b"] * b; ll = fl["a"] + fl["b"] * b
    if not lu > ll:
        return None
    first = S[0][0]
    if typ == "br":
        if not (fu["on"] + fl["on"] >= BR_TOTAL and max(fu["on"], fl["on"]) >= BR_SIDE):
            return None
        rr = r60[first]
        if rr > 0:
            typ = "brT"
        elif rr < 0:
            typ = "brB"
        else:
            return None
    else:
        if not (fu["b"] < fl["b"]):
            return None
        if not (fu["on"] >= 2 and fl["on"] >= 2 and fu["on"] + fl["on"] >= 5):
            return None
    return {"typ": typ, "fu": fu, "fl": fl, "conf": b, "first": first, "conv": typ not in ("brT", "brB")}


def _build_diamond(piv, b, r60):
    """B7：回組或 None。"""
    hpos = [i for i, p in enumerate(piv) if p[1] == "H"]; lpos = [i for i, p in enumerate(piv) if p[1] == "L"]
    if len(hpos) < 4 or len(lpos) < 4:
        return None
    k = min(hpos[-2], lpos[-2])
    hf = [i for i in hpos if i < k]; lf = [i for i in lpos if i < k]
    if len(hf) < 2 or len(lf) < 2:
        return None
    st = min(hf[-2], lf[-2])
    front, back = piv[st:k], piv[k:]
    first = front[0][0]
    if not (back[-1][0] - first + 1 <= SPAN):
        return None

    def two(seg):
        Hs = [(s, y) for s, kk, y in seg if kk == "H"]; Ls = [(s, y) for s, kk, y in seg if kk == "L"]
        return _fit(*zip(*Hs)), _fit(*zip(*Ls))
    fu1, fl1 = two(front); fu2, fl2 = two(back)
    if None in (fu1, fl1, fu2, fl2):
        return None
    if not (_cls(fu1["rel"]) == "up" and _cls(fl1["rel"]) == "dn" and _cls(fu2["rel"]) == "dn" and _cls(fl2["rel"]) == "up"):
        return None
    if not (fu2["a"] + fu2["b"] * b > fl2["a"] + fl2["b"] * b):
        return None
    rr = r60[first]
    typ = "dmT" if rr > 0 else ("dmB" if rr < 0 else None)
    if typ is None:
        return None
    return {"typ": typ, "fu": fu2, "fl": fl2, "conf": b, "first": first, "conv": True}


_LINE_VID = {("sym", 1): 4, ("sym", -1): 5, ("asc", 1): 6, ("asc", -1): 7, ("desc", 1): 8, ("desc", -1): 9,
             ("rw", 1): 10, ("rw", -1): 11, ("fw", 1): 12, ("fw", -1): 13, ("brT", 1): 14, ("brT", -1): 15,
             ("brB", 1): 16, ("brB", -1): 17, ("dmT", 1): 18, ("dmT", -1): 19, ("dmB", 1): 20, ("dmB", -1): 21}


def detect_lines(h, l, c, r60, lag=None):
    """乙 轉折 ⇒ 三角／楔形／擴散／鑽石 的突破事件 {vid: [(T, first)]}。lag：⛔ 正式＝R；≠R 只給 fixture 鑑別力測試。"""
    n = len(c); lag = B_R if lag is None else lag
    ph = np.flatnonzero(SF.swing_lows(-np.asarray(h, float), B_R))
    pl = np.flatnonzero(SF.swing_lows(np.asarray(l, float), B_R))
    conf_at = {}
    for s in ph:
        conf_at.setdefault(int(s) + lag, []).append((int(s), "H", float(h[s])))
    for s in pl:
        conf_at.setdefault(int(s) + lag, []).append((int(s), "L", float(l[s])))
    piv = []
    out = {vid_s(i): [] for i in range(4, 22)}
    G = [None, None]
    for b in range(n):
        for gi in (0, 1):                                 # B3 ①
            g = G[gi]
            if g is None:
                continue
            if b - g["conf"] > LIFE:
                G[gi] = None; continue
            if b < g["conf"] + 1:
                continue
            lu = g["fu"]["a"] + g["fu"]["b"] * b; ll = g["fl"]["a"] + g["fl"]["b"] * b
            if g["conv"] and not lu > ll:
                G[gi] = None; continue
            lu1 = g["fu"]["a"] + g["fu"]["b"] * (b - 1); ll1 = g["fl"]["a"] + g["fl"]["b"] * (b - 1)
            if c[b] > lu and c[b - 1] <= lu1:
                out[vid_s(_LINE_VID[(g["typ"], 1)])].append((b, g["first"])); G[gi] = None
            elif c[b] < ll and c[b - 1] >= ll1:
                out[vid_s(_LINE_VID[(g["typ"], -1)])].append((b, g["first"])); G[gi] = None
        new = conf_at.get(b)                              # B3 ②
        if new:
            piv.extend(new); piv.sort(key=lambda p: p[0])
            G[0] = _build_line(piv, b, r60)
            G[1] = _build_diamond(piv, b, r60)
    return out


# ═════════════ 價格結構：圓形（S22～S24） ═════════════
def _quad_ok(y, a, T, up):
    x = np.arange(a, T, dtype=float); xm = x.mean(); u = x - xm
    A = np.vstack([np.ones_like(u), u, u * u]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    g = coef[2]
    if not ((g > 0) if up else (g < 0)):
        return False
    yh = A @ coef
    sst = float(((y - y.mean()) ** 2).sum())
    if sst <= 0:
        return False
    r2 = 1.0 - float(((y - yh) ** 2).sum()) / sst
    if not r2 >= RD_R2:
        return False
    xv = -coef[1] / (2.0 * g) + xm
    L = T - 1 - a
    return a + L / 3.0 <= xv <= a + 2.0 * L / 3.0


def detect_round(c, r60):
    n = len(c); out = {vid_s(22): [], vid_s(23): [], vid_s(24): []}
    if n <= RD_BACK:
        return out
    Wn = RD_BACK - RD_MIN + 1
    Wv = np.lib.stride_tricks.sliding_window_view(c, Wn)      # 第 i 列 ＝ c[i : i+Wn] ⇒ T ＝ i + RD_BACK
    Ts = np.arange(RD_BACK, n)
    rows = Ts - RD_BACK
    amax = rows + np.argmax(Wv[rows], axis=1); amin = rows + np.argmin(Wv[rows], axis=1)
    for T, a in zip(Ts, amax):                               # S22
        if not c[T] > c[a]:
            continue
        seg = c[a:T]
        if seg[1:].size and np.max(seg[1:]) > c[a]:
            continue
        b = a + int(np.argmin(seg))
        if b - a < RD_DIST or T - b < RD_DIST or not (r60[a] < 0):
            continue
        if _quad_ok(seg, a, T, True):
            out[vid_s(22)].append((int(T), int(a)))
    for T, a in zip(Ts, amin):                               # S23／S24
        seg = c[a:T]
        up = c[T] > np.max(seg); dn = c[T] < c[a]
        if not (up or dn):
            continue
        if seg[1:].size and np.min(seg[1:]) < c[a]:
            continue
        b = a + int(np.argmax(seg))
        if b - a < RD_DIST or T - b < RD_DIST or not (r60[a] > 0):
            continue
        if _quad_ok(seg, a, T, False):
            out[vid_s(23 if up else 24)].append((int(T), int(a)))
    return out


# ═════════════ 價格結構：島型（S25～S26） ═════════════
def detect_island(h, l, v, r60):
    n = len(h); out = {vid_s(25): [], vid_s(26): []}
    vm = _winmean(v, IS_VOL)
    with np.errstate(invalid="ignore"):
        gu = np.zeros(n, bool); gd = np.zeros(n, bool)
        gu[1:] = l[1:] > h[:-1]; gd[1:] = h[1:] < l[:-1]
        volok = v > vm
    for b in np.flatnonzero((gd | gu) & volok):
        for top in (True, False):
            if top and not gd[b]:
                continue
            if (not top) and not gu[b]:
                continue
            for a in range(b - 1, max(0, b - IS_MAX) - 1, -1):
                if a < 1:
                    break
                if top:
                    if not gu[a]:
                        continue
                    ovl = (h[a - 1] <= l[b - 1]) and (h[b] <= l[a])      # [H_{a−1}, L_a] ∩ [H_b, L_{b−1}]
                    ok = ovl and r60[a] > 0
                else:
                    if not gd[a]:
                        continue
                    ovl = (h[a] <= l[b]) and (h[b - 1] <= l[a - 1])      # [H_a, L_{a−1}] ∩ [H_{b−1}, L_b]
                    ok = ovl and r60[a] < 0
                if ok:
                    out[vid_s(25 if top else 26)].append((int(b), int(a)))
                    break
    return out


# ═════════════ 價格結構：V 底（S27） ═════════════
def detect_v(c, v):
    n = len(c); out = {}
    vm = _winmean(v, V_LB)
    for b in range(V_LB, n):
        w = c[b - V_LB:b]
        if not np.all(np.isfinite(w)):
            continue
        if not c[b] <= np.min(c[b - (V_LB - 1):b]):
            continue
        P = float(np.max(w))
        if not ((P - c[b]) / P >= V_DROP):
            continue
        if not (np.isfinite(v[b]) and np.isfinite(vm[b]) and v[b] >= V_VOL * vm[b]):
            continue
        lvl = c[b] + V_HALF * (P - c[b])
        for T in range(b + 1, min(n, b + V_WIN + 1)):
            if c[T] >= lvl:
                out[T] = (int(T), int(b - V_LB + int(np.argmax(w))))     # 同一個 T ⇒ 後面的 b 覆蓋（取最近的 b）
                break
    return {vid_s(27): [out[t] for t in sorted(out)]}


# ═════════════ 價格結構：平台（S28） ═════════════
def detect_platform(h, l, c):
    n = len(c); ev = []
    if n <= PF_MINLEN + PF_LB:
        return {vid_s(28): ev}
    Hw = np.lib.stride_tricks.sliding_window_view(h, PF_MINLEN)[:n - PF_MINLEN]   # 第 i 列 ＝ [i, i+25) ⇒ T ＝ i+25
    Lw = np.lib.stride_tricks.sliding_window_view(l, PF_MINLEN)[:n - PF_MINLEN]
    with np.errstate(invalid="ignore", divide="ignore"):
        hx = Hw.max(axis=1); lx = Lw.min(axis=1)
        Ts = np.arange(PF_MINLEN, n)
        cand = (hx / lx - 1.0 <= PF_RANGE) & (c[Ts] > hx)
    for T in Ts[cand]:
        s = T - PF_MINLEN; mh = h[s:T].max(); ml = l[s:T].min()
        bad = False
        while s - 1 >= 0:
            if not (np.isfinite(h[s - 1]) and np.isfinite(l[s - 1])):
                bad = True; break                           # B13：延伸時遇缺值 ⇒ 不成立
            h2 = max(mh, h[s - 1]); l2 = min(ml, l[s - 1])
            if not (h2 / l2 - 1.0 <= PF_RANGE):
                break
            s -= 1; mh, ml = h2, l2
        if bad or not c[T] > mh:
            continue
        if s < PF_LB:
            continue
        pre = c[s - PF_LB:s]
        if not np.all(np.isfinite(pre)):
            continue
        j = int(np.argmin(pre))
        if c[s] / pre[j] - 1.0 >= PF_RISE:
            ev.append((int(T), int(s - PF_LB + j)))
    return {vid_s(28): ev}


# ═════════════ 全部 ═════════════
def detect_all(o, h, l, c, v, ro, rh, rl, rc, lag_a=None, lag_b=None):
    """有效 K 棒序列 ⇒ {vid: {T, first, d, r10, r20, r60, prd}}（numpy；依 T 排序；索引＝有效 K 棒序號）。
    lag_a／lag_b：⛔ 正式一律 None（＝3／5）；只給 fixture 的「確認提早一根」鑑別力測試用。"""
    o, h, l, c, v = (np.asarray(x, float) for x in (o, h, l, c, v))
    ro, rh, rl, rc = (np.asarray(x, float) for x in (ro, rh, rl, rc))
    r10, r20, r60 = _rN(c, PRE_N), _rN(c, 20), _rN(c, R60)
    K = detect_kbars(o, h, l, c, ro, rh, rl, rc)
    S = {}
    S.update(detect_turns(c, r60, lag=lag_a))
    S.update(detect_lines(h, l, c, r60, lag=lag_b))
    S.update(detect_round(c, r60))
    S.update(detect_island(h, l, v, r60))
    S.update(detect_v(c, v))
    S.update(detect_platform(h, l, c))
    out = {}
    for vid in VID:
        if vid in K:
            T, first, d = K[vid]["T"], K[vid]["first"], K[vid]["d"]
        else:
            ev, seen = [], set()
            for e in sorted(set(S[vid])):
                if e[0] not in seen:
                    seen.add(e[0]); ev.append(e)
            T = np.array([e[0] for e in ev], dtype=np.int64); first = np.array([e[1] for e in ev], dtype=np.int64)
            d = np.full(len(T), VMAP[vid]["d"], dtype=np.int8)
        with np.errstate(invalid="ignore", divide="ignore"):
            pv = np.where(first >= 1, c[np.maximum(first - 1, 0)], np.nan)
            prd = c[T] / pv - 1.0 if len(T) else np.zeros(0)
        out[vid] = {"T": np.asarray(T, np.int64), "first": np.asarray(first, np.int64), "d": np.asarray(d, np.int8),
                    "r10": r10[first] if len(T) else np.zeros(0), "r20": r20[first] if len(T) else np.zeros(0),
                    "r60": r60[first] if len(T) else np.zeros(0), "prd": prd}
    return out


def detect_calendar(o, h, l, c, v, ro, rh, rl, rc, **kw):
    """對齊交易日曆（洞＝NaN；有效 K 棒 ＝ 還原收盤非缺值）⇒ 同 detect_all，但 T／first 換成日曆位置。"""
    c = np.asarray(c, float)
    bars = np.flatnonzero(np.isfinite(c))
    sel = lambda x: np.asarray(x, float)[bars]
    r = detect_all(sel(o), sel(h), sel(l), c[bars], sel(v), sel(ro), sel(rh), sel(rl), sel(rc), **kw)
    for vid, e in r.items():
        e["T_bar"] = e["T"]
        e["T"] = bars[e["T"]] if len(e["T"]) else e["T"]
        e["first"] = bars[e["first"]] if len(e["first"]) else e["first"]
    return r
