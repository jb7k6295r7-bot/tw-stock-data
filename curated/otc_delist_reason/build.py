# 上櫃終止上櫃原因（官方分類＝deListed 的 reason 參數）
import json, time, urllib.request, csv, io, subprocess
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
U = "https://www.tpex.org.tw/www/zh-tw/company/deListed?code=&date=ALL&reason={}&id=&response=json&paging-offset=0&paging-size=5000"
rows, fields = [], None
for k in range(0, 7):
    t = urllib.request.urlopen(urllib.request.Request(U.format(k), headers=UA), timeout=60).read().decode("utf-8")
    j = json.loads(t)
    tabs = j.get("tables") or []
    if not tabs:
        print("reason", k, "無 tables", t[:120]); time.sleep(3.5); continue
    tab = tabs[0]; d = tab.get("data") or []
    fields = tab.get("fields") or fields
    print("reason", k, "列", len(d), "total", tab.get("totalCount"), "fields", tab.get("fields"))
    for r in d:
        r = [str(x).strip() for x in r]
        rows.append((k, r))
    time.sleep(3.5)
LABEL = {0: "被合併", 1: "金控", 2: "轉上市", 3: "取消第二類股", 4: "拒絕往來", 5: "其他", 6: "管理股票"}
def ad(s):
    y, m, dd = s.split("-") if "-" in s else s.split("/")
    return "%04d-%02d-%02d" % (int(y) + 1911, int(m), int(dd))
out = io.open("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/193b1cf1-18d1-47b4-930d-299489e97dc9/scratchpad/odr/otc_delist_reason.csv", "w", encoding="utf-8", newline="")
w = csv.writer(out, lineterminator="\n")
w.writerow(["delist_date", "stock_id", "name", "reason_code", "reason_label", "rule_text"])
seen = set()
for k, r in sorted(rows, key=lambda x: (ad(x[1][2]), x[1][0])):
    key = (r[0], ad(r[2]))
    if key in seen:
        print("重複", key, k)
    seen.add(key)
    w.writerow([ad(r[2]), r[0], r[1], k, LABEL.get(k, "代碼%d" % k), r[3] if len(r) > 3 else ""])
out.close()
# 對庫內 delisted.csv 上櫃
txt = subprocess.run(["git", "-C", "/home/chemtim/tw-trial", "show", "origin/main:data/meta/delisted.csv"], capture_output=True, text=True).stdout
db = {(r["stock_id"], r["delist_date"]) for r in csv.DictReader(io.StringIO(txt)) if r["market"] == "tpex"}
print("官方列", len(seen), "庫內上櫃", len(db), "兩邊都有", len(seen & db), "只官方", len(seen - db), "只庫內", len(db - seen))
print("只庫內 例", sorted(db - seen)[:10]); print("只官方 例", sorted(seen - db)[:10])
