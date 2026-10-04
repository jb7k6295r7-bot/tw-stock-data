# 每日名單自動比對 GATE_V2 開／關（裁定 seq296 §一）：閘門

**時間**：2026-10-04 21:05～22:09（台北）｜在副本開發、閘門全過後才覆蓋 `backtest/daily_list.py`（+105／−9 行）、`backtest/run_daily_list.sh`（+3 行）｜⛔ 未 commit、未碰信箱（測試輸出夾 ~/ugwork/mb）

- **G2 一致時舊段落逐字相同**：兩個 sha 各驗一次，新程式產出的 daily_2026-10-02.md 都和舊程式逐位元相同。
  - main 687c9f3c3b：副本注入跑，sha256 4ac16e4c…。
  - main c2e0bf24ae：沙盒包裝第 6 步產出，對舊程式同 sha 產出。
  - 兩次的 log 都記「開關一致」，比對結果另存 gatev2_cmp_<資料日>.json。
- **G4 鎖、重跑、--final 照舊**（沙盒：~/dlsand，git clone --shared ＋ 本機 bare remote，包裝只把 REPO 換成沙盒）。依序測：
  1. 首次產檔。
  2. 立刻重跑 ⇒ 略過（sha 相同）。
  3. 鎖住時執行 ⇒ 略過：已有一個在跑。
  4. --final（假今天 2026-10-05）⇒ 預期資料日 10-02 的檔已在。
  5. fixture ⇒ 見下一項。
  6. 再 --force 不帶 fixture ⇒ 一致、MB 裡的差異檔被刪。
  - 退出碼全 0；沙盒 daily_run.log 見 g4_wrapper_log.txt。
- **fixture（模擬兩版不同）**：設 `DAILY_GV2_FAKE=3707`（新口徑下把 3707 當成資料日不在母體）再跑 --force。
  - 正式產出切成新口徑，檔頭第 4 行加了說明。
  - 寫出 gatev2_diff_2026-10-02.md，列出第一、二節「新口徑剔除：3707 漢磊」，第三、四節相同。
  - 包裝把差異檔複製到 MB；下一次一致時刪掉。
  - 檔案：fixture_daily_2026-10-02.md、fixture_gatev2_diff_2026-10-02.md。
- 代價：每次跑兩遍，約 11 分鐘（原本約 5 分鐘）。
