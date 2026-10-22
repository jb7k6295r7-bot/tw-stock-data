# -*- coding: utf-8 -*-
"""被公開收購（E1）／經營權變動（E2，v1c 定版）／私募（E3）事件表（重大訊息主旨分類）⇒ takeover_events.csv

    python3 curated/takeover_events/build.py [--ref origin/main] [--sample 50]

依據：裁定 seq441；登錄 台股策略線 seq1 sha42899d489f9e0683（被公開收購、經營權變動、私募引進策略投資人，宣告後股價，事件層描述）。
來源：公開庫 `data/mops/news/<年>.csv`（MOPS 重大訊息主旨，1999 起全市場，含已下市）；只收 market ∈ {sii, otc}。
⚠ news 的 market 是「現在（或下市前）的市場別」，不是發布當時的市場 ⇒ 上市櫃之前（興櫃、未上市）發的重訊也會收進來；回測接價格時自然掉（無價），筆數會偏多一點。
⛔ 只用主旨；內文（應募人身分、收購價格、持股比例）讀不到 ⇒ 「策略性投資人」只能靠主旨，絕大多數私募主旨不寫應募人身分（見 E3）。

## 共同（2026-10-22 寫死）
主旨先去掉所有空白。同一代號、同一 class 的主事件，30 個日曆天內只留第一則；first12m＝1 表示前 365 天內同代號同 class 沒有主事件（登錄 §二「同公司 12 個月內同類只取第一次」用這欄篩）。

## E1 被公開收購（本公司是被收購方）
被收購方的公告型（任一命中）：
  T1 公開收購本(公司|行)　T2 接獲…公開收購（80 字內）　T3 申報及公告之公開收購申報書
  T4 公開收購 且 審議委員會／審議結果　T5 公開收購之回應
  T6 公開收購＋本公司簡稱（主旨裡「公開收購」後 6 字內出現自己的簡稱，例「遨睿公開收購國巨說明」）
排除（不是本公司被收購）：子公司｜孫公司｜轉投資｜被投資｜母公司｜應賣｜參與｜參加；T2 另排除 核准｜同意（主管機關核准收購方）。
後續公告（followup=1，⛔ 不是首次宣告，事件研究只用 followup=0）：
  期間屆滿｜屆滿｜成就｜最低收購數量｜延長｜更正｜補充｜補正｜修正｜更新｜修訂｜收購對價｜匯入｜專戶｜截止｜變更｜停止｜撤銷｜撤回｜不繼續｜終止｜提高｜調整｜交割｜解任｜股權變動｜失敗｜未達；含「結果」但不含「審議」。
  後續公告不去重、照列，供追蹤；主事件 30 日去重只在 followup=0 之間做。
outcome（主事件後 0～150 天，被收購方本身或任何公司主旨含「公開收購」＋被收購方簡稱）：
  fail＝未成就｜未達最低｜未達預定｜停止公開收購｜終止公開收購｜撤銷｜不成就｜失敗；否則 success＝條件(均)?已?成就｜已達最低收購數量；都沒有＝空白（仍在進行或主旨查無）。
acq_date：主事件前 30 天～當天，別的代號主旨含「公開收購」且 12 字內出現被收購方簡稱、且非後續公告的最早一則（收購方先發公告的日子）；查無＝空白。
⭐ v2（同日人工核對第一輪 50 則：45 則對＝90%；錯 5 則）：
  排除加 澄清｜媒體（2345 2008-08「澄清媒體報導宏瞻是否繼續公開收購」）；後續公告加 核准｜未通過（1735、8291「投審會核准…公開收購」、2327「投審會未通過」）；
  T4 的「審議委員會」不可前接「投資」（經濟部投資審議委員會≠公開收購審議委員會）；比對前先刪掉「…」引號內文字（8081 致新引述類比科公告而誤收）。
  fail 加 未通過｜不予核准。
⭐ v3（第二輪另抽 50 則：49 則對＝98%；錯 3438 2019-01-08「回應108年1月4日致新…公告對於公開收購本公司案之說明內容」＝同一案的攻防）：
  後續公告加 回應＋數字（回應某日公告）。⚠ 已知殘留：同一案超過 30 天的其他攻防說明仍可能當主事件，first12m=0 可濾掉。

## E3 私募（股權）董事會決議；strategic_subj 子旗標
主事件：含「私募」且含 決議｜擬以私募｜擬辦理私募｜通過.{0,6}私募，且含 普通股｜現金增資｜現增｜增資｜新股｜特別股｜有價證券｜存託憑證。
排除：公司債｜轉換債｜子公司｜孫公司｜轉投資｜被投資｜參與｜認購｜取得｜處分｜基金｜應募｜
  定價｜訂價｜價格｜基準日｜繳款｜收足｜完成｜變更登記｜不繼續｜不再｜不予｜不辦理｜撤銷｜撤回｜取消｜失效｜延長｜屆滿｜屆期｜
  更正｜補正｜補充｜修正｜修訂｜變更｜資金運用｜交付｜申報｜專區｜上市｜上櫃｜補辦｜追認｜分次｜剩餘｜尚餘；
  股東(常|臨時)?會(決議|通過) 而主旨沒有「董事會」（股東會通過是同一案的第二步，不是首次宣告）。
instrument：pref＝特別股；sec＝只寫有價證券（可能含私募可轉債）；dr＝存託憑證；其餘 common。
strategic_subj＝1：主旨含 策略性?投資人｜策略(性)?(合作)?夥伴｜策略股東｜引進.{0,20}(投資人|股東)。⚠ 全期只有個位數則，主旨不寫應募人身分是常態。
with_reduction：同代號、主事件前後 30 個日曆天內（含同主旨）有減資主旨（含「減資」；排除 子公司｜孫公司｜轉投資｜被投資｜庫藏｜註銷｜收回｜限制員工）＝1。
  reduction_gap＝最近一則減資主旨距事件幾天（負＝在前；±180 天內，否則空白）；reduction_type＝最近那則：loss（彌補虧損）／cash（現金減資、退還股款）／other。
⭐ v2（第一輪 50 則：46 則對＝92%；錯 6015「訂定…私募增資準日」、1536「公開申購或詢價圈購或私募三種擇一」、3701「決議召開…股東常會」、2375「決議停止辦理…私募」）：
  排除加 準日｜訂定｜召開｜停止｜暫停｜終止｜擇一｜或私募｜或以私募｜私募或｜私募.{0,4}或｜或國內現金增資｜或公開（私募與公募擇一的不算）；
  主事件條件的標的詞加 策略性?投資人｜引進（1795、6558「董事會決議私募引進策略投資人…」原本因主旨沒有「普通股」而漏收）。
⭐ v3（第二輪另抽 50 則：48 則對＝96%；錯 8077「私募特別股全面強制換發為普通股」、2408「決議投資美光私募普通股」＝投資別人）：
  排除加 換發｜轉換｜投資(?!人)。⚠ 已知殘留：「私募…股數減少」這類修改案仍會收（例 6199 2014-10-01）；大型金控／聯電每年「得視營運需求辦理私募有價證券」的授權案照收（是真決議，但多半沒發）。
⭐ v4（裁定 seq457；裁定文稱「E3 v2」＝定版後第二版）：私募明細表（curated/placement_detail）對照時找到的誤收——
  2891「代加拿大子行公告」×2、2002「代中龍公司公告」＝子公司私募；8415「收購正道…私募普通股」＝認購他公司私募；
  3085「不在繼續辦理」錯字；6443、5531「收回私募甲種特別股辦理減資註銷」；2882「…擬將發行股數由3億股提高為4.2億」＝修改股數。
  排除加（E3_EXC4）：代[^，,。]{0,15}公告｜收購.{0,30}私募｜收回私募｜註銷｜不在繼續｜提高｜股數由。
  ⚠ 實際少 9 列（3,021→3,012）：多出 2891 2010-08-26「代加拿大子行公告…私募現金增資加幣2,999,988元」，同型（子公司私募），待裁定確認。

## E2 經營權變動（⭐ 裁定 seq443 §四：採 v1 系列正式產出，併入 takeover_events.csv，class=E2；下列 B～E 只留在候選檔）
共同排除：子公司｜孫公司｜轉投資｜被投資｜母公司｜澄清｜報導｜報載｜媒體｜傳聞｜更正｜補充｜補正｜修正｜代（後面不是 取得人／表人／理；例「富邦金控代富邦證券(香港)公告」）。
  A 股權型：369(條)?(之|-)8 且含 本公司｜接獲（⭐ v1b：原本寫 369.{0,3}8，誤配營收數字「369,834仟元」，抽核後改）；或 取得本公司.{0,30}(三分之一|二分之一|過半|股份總數)；或 本公司股東.{0,30}超過.{0,20}三分之一；
            或 經營權.{0,2}(異動|變動|移轉|易主|移交) ；或 入主本公司。
  B 大股東申報型：證(券)?交(易)?法第?43條之1（代取得人公告，取得 >10%）。
  C 董事會非例行改組：三分之一以上董事｜董事變動(已)?達(1/3|三分之一) 且含 臨時會｜解任｜辭任｜辭職｜改派｜提前；或 臨時會.{0,30}全面改選｜全面改選.{0,20}臨時會｜提前改選。
  D 董事會改組（含例行）：三分之一以上董事｜董事變動(已)?達(1/3|三分之一)（不論常會、任期屆滿）。
  E 內部人大量轉讓：持股轉讓.{0,30}(二分之一|1/2).{0,10}(當然|自然)?解任。
  候選版本：e2_v1＝A；e2_v2＝A∪B∪C；e2_v3＝A∪B∪C∪D∪E。⛔ 單純「董事長異動」不在任何版本（例行換人居多）。
  after_e1＝1：同代號前 180 天內有 E1 主事件（被公開收購之後的股權／董事變動）。
  去重：同代號、同版本 30 個日曆天內只留第一則。
  ⭐ 正式 E2＝規則 A（v1b，seq443 核定），每筆 followup=0；first12m＝前 365 天同代號無 E2 主事件；overlap_e1＝同代號前後 60 個日曆天內有 E1 主事件（主表剔除、另報含重疊版用）。
  ⭐ v1c（seq443 要求的隨機 50 則核對後修；第一輪 v1b：對 33／疑 13／錯 4）：錯的是 3432「本公司股東常會改選…超過三分之一董事變動」誤配「本公司股東…超過…三分之一」、
    8455、3702「本公司依 369 條之 8 通知已取得〔別家〕…」＝收購方自己的通知、4729「持有股份低於三分之一」＝持股降到門檻下 ⇒
    「本公司股東」那條改成 本公司股東「…」持股…超過…三分之一；A 另排除 通知已取得(?!本公司)｜低於｜減少｜降低。v1b 76 筆 → v1c 71 筆（只少了這 5 筆）。
    「疑」＝只寫「依 369 條之 8 公告股權變動事宜」、沒寫取得或減少（13/50），要內文才能確認。
  候選三版（e2_v1／v2／v3）只在給 --e2-candidates 路徑時輸出，不放 curated 目錄。
輸出欄：date, time, stock_id, name, market, class, followup, first12m, outcome, acq_date, with_reduction, reduction_gap, reduction_type,
        strategic_subj, instrument, overlap_e1（E2 才有）, subject, serial
"""
import argparse, csv, datetime, io, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "takeover_events.csv")
OUT_E2 = os.path.join(HERE, "e2_candidates.csv")

# ---- E1 ----
E1_T = [re.compile(p) for p in (r"公開收購本(公司|行)", r"接獲.{0,80}公開收購", r"申報及公告之公開收購申報書",
                                 r"公開收購.*((?<!投資)審議委員會|審議結果)|((?<!投資)審議委員會|審議結果).*公開收購", r"公開收購之回應")]
E1_EXC = re.compile(r"子公司|孫公司|轉投資|被投資|母公司|應賣|參與|參加|澄清|媒體")
E1_T2_EXC = re.compile(r"核准|同意")
E1_FU = re.compile(r"期間屆滿|屆滿|成就|最低收購數量|延長|更正|補充|補正|修正|更新|修訂|收購對價|匯入|專戶|截止|變更|停止|撤銷|撤回|不繼續|終止|提高|調整|交割|解任|股權變動|失敗|未達|"
                   r"核准|未通過|回應\d")
E1_FAIL = re.compile(r"未成就|未達最低|未達預定|停止公開收購|終止公開收購|撤銷|不成就|失敗|未通過|不予核准")
QUOTE = re.compile(r"「[^」]*」")
E1_OK = re.compile(r"條件(均)?(已)?成就|已達最低收購數量")

# ---- E3 ----
E3_ACT = re.compile(r"決議|擬以私募|擬辦理私募|通過.{0,6}私募")
E3_INS = re.compile(r"普通股|現金增資|現增|增資|新股|特別股|有價證券|存託憑證|策略性?投資人|引進")
E3_EXC = re.compile(r"公司債|轉換債|子公司|孫公司|轉投資|被投資|參與|認購|取得|處分|基金|應募|定價|訂價|價格|基準日|繳款|收足|完成|變更登記|"
                    r"不繼續|不再|不予|不辦理|撤銷|撤回|取消|失效|延長|屆滿|屆期|更正|補正|補充|修正|修訂|變更|資金運用|交付|申報|專區|"
                    r"上市|上櫃|補辦|追認|分次|剩餘|尚餘|"
                    r"準日|訂定|召開|停止|暫停|終止|擇一|或私募|或以私募|私募或|私募.{0,4}或|或國內現金增資|或公開|"
                    r"換發|轉換|投資(?!人)")
E3_SH = re.compile(r"股東(常|臨時)?會(決議|通過)")
# v4（裁定 seq457）：私募明細對照時發現的 8 列誤收
E3_EXC4 = re.compile(r"代[^，,。]{0,15}公告|收購.{0,30}私募|收回私募|註銷|不在繼續|提高|股數由")
E3_STRAT = re.compile(r"策略性?投資人|策略(性)?(合作)?夥伴|策略股東|引進.{0,20}(投資人|股東)")
RED = re.compile(r"減資")
RED_EXC = re.compile(r"子公司|孫公司|轉投資|被投資|庫藏|註銷|收回|限制員工")

# ---- E2 ----
E2_EXC = re.compile(r"子公司|孫公司|轉投資|被投資|母公司|澄清|報導|報載|媒體|傳聞|更正|補充|補正|修正|代(?!取得人|表人|理)")
E2_A = [re.compile(p) for p in (r"369(條)?(之|-)8.*(本公司|接獲)|(本公司|接獲).*369(條)?(之|-)8", r"取得本公司.{0,30}(三分之一|二分之一|過半|股份總數)",
                                 r"本公司股東「[^」]{1,40}」持股.{0,10}超過.{0,20}三分之一", r"經營權.{0,2}(異動|變動|移轉|易主|移交)", r"入主本公司")]
E2_A_EXC = re.compile(r"通知已取得(?!本公司)|低於|減少|降低")  # seq443 核對後（v1c）：收購方自己的通知、持股降到門檻以下
E2_B = re.compile(r"證(券)?交(易)?法第?43條之1")
E2_BOARD = re.compile(r"三分之一以上董事|董事變動(已)?達(1/3|三分之一)")
E2_C_CTX = re.compile(r"臨時會|解任|辭任|辭職|改派|提前")
E2_C2 = re.compile(r"臨時會.{0,30}全面改選|全面改選.{0,20}臨時會|提前改選")
E2_E = re.compile(r"持股轉讓.{0,30}(二分之一|1/2).{0,10}解任")


def short(name):
    return re.sub(r"[\*＊]|-KY|-創|KY$", "", name or "").strip()


def e1_type(s, name):
    s = QUOTE.sub("", s)  # v2：引號內是轉述別人的公告（例 8081 引述類比科「…公開收購本公司…」），不算
    if E1_EXC.search(s):
        return None
    hit = False
    for i, p in enumerate(E1_T):
        if p.search(s):
            if i == 1 and E1_T2_EXC.search(s):
                continue
            hit = True
            break
    nm = short(name)
    if not hit and len(nm) >= 2 and re.search("公開收購.{0,6}" + re.escape(nm), s):
        hit = True
    if not hit:
        return None
    fu = bool(E1_FU.search(s)) or ("結果" in s and "審議" not in s)
    return int(fu)


def e3_type(s):
    if "私募" not in s or not E3_ACT.search(s) or not E3_INS.search(s) or E3_EXC.search(s) or E3_EXC4.search(s):
        return None
    if E3_SH.search(s) and "董事會" not in s:
        return None
    ins = "pref" if "特別股" in s else ("dr" if "存託憑證" in s else
                                       ("sec" if "有價證券" in s and not re.search(r"普通股|現金增資|現增|增資|新股", s) else "common"))
    return ins, int(bool(E3_STRAT.search(s)))


def e2_rules(s):
    if E2_EXC.search(s):
        return set()
    r = set()
    if any(p.search(s) for p in E2_A) and not E2_A_EXC.search(s):
        r.add("A")
    if E2_B.search(s):
        r.add("B")
    if (E2_BOARD.search(s) and E2_C_CTX.search(s)) or E2_C2.search(s):
        r.add("C")
    if E2_BOARD.search(s):
        r.add("D")
    if E2_E.search(s):
        r.add("E")
    return r


def dedup(rows, key, days=30):
    rows = sorted(rows, key=lambda r: (key(r), r["date"], r.get("time", "")))
    out, last = [], {}
    for r in rows:
        k = key(r)
        d = datetime.date.fromisoformat(r["date"])
        if k in last and (d - last[k]).days <= days:
            continue
        last[k] = d
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--resample", action="store_true")
    ap.add_argument("--e2-candidates", default="", help="E2 候選三版輸出路徑（不給就不寫）")
    a = ap.parse_args()
    files = subprocess.run(["git", "-C", REPO, "ls-tree", "--name-only", a.ref, "data/mops/news/"],
                           capture_output=True, text=True).stdout.split()
    allrows = []
    for f in sorted(x for x in files if re.search(r"/\d{4}\.csv$", x)):
        t = subprocess.run(["git", "-C", REPO, "show", f"{a.ref}:{f}"], capture_output=True, text=True).stdout
        for r in csv.DictReader(io.StringIO(t)):
            if r.get("market") not in ("sii", "otc"):
                continue
            r["s"] = re.sub(r"\s+", "", r.get("subject", ""))
            allrows.append(r)
    allrows.sort(key=lambda r: (r["date"], r.get("time", ""), r["stock_id"]))
    D = lambda r: datetime.date.fromisoformat(r["date"])
    tko = [r for r in allrows if "公開收購" in r["s"]]
    red_by = {}
    for r in allrows:
        if RED.search(r["s"]) and not RED_EXC.search(r["s"]):
            red_by.setdefault(r["stock_id"], []).append(r)

    e1, e1fu, e3, e2 = [], [], [], []
    for r in allrows:
        s = r["s"]
        t = e1_type(s, r.get("name"))
        if t is not None:
            (e1fu if t else e1).append(dict(r, cls="E1", followup=t))
        t3 = e3_type(s)
        if t3:
            e3.append(dict(r, cls="E3", followup=0, instrument=t3[0], strategic_subj=t3[1]))
        rr = e2_rules(s)
        if rr:
            e2.append(dict(r, rules="".join(sorted(rr))))

    e1 = dedup(e1, lambda r: r["stock_id"])
    e3 = dedup(e3, lambda r: r["stock_id"])
    # first12m
    for lst in (e1, e3):
        last = {}
        for r in sorted(lst, key=lambda r: (r["date"], r.get("time", ""))):
            d = D(r); k = r["stock_id"]
            r["first12m"] = int(not (k in last and (d - last[k]).days <= 365))
            last[k] = d
    # E1 outcome / acq_date
    for r in e1:
        d0 = D(r); nm = short(r.get("name")); sid = r["stock_id"]
        win = [x for x in tko if 0 <= (D(x) - d0).days <= 150 and
               (x["stock_id"] == sid or (len(nm) >= 2 and nm in x["s"]))]
        fail = any(E1_FAIL.search(x["s"]) for x in win)
        ok = any(E1_OK.search(x["s"]) and not E1_FAIL.search(x["s"]) for x in win)
        r["outcome"] = "fail" if fail else ("success" if ok else "")
        pre = [x for x in tko if x["stock_id"] != sid and 0 <= (d0 - D(x)).days <= 30 and len(nm) >= 2
               and re.search("公開收購.{0,12}" + re.escape(nm), x["s"]) and not E1_FU.search(x["s"])]
        r["acq_date"] = min((x["date"] for x in pre), default="")
    for r in e1fu:
        r["first12m"] = ""; r["outcome"] = ""; r["acq_date"] = ""
    # E3 reduction
    for r in e3:
        d0 = D(r); best = None
        for x in red_by.get(r["stock_id"], []):
            g = (D(x) - d0).days
            if abs(g) <= 180 and (best is None or abs(g) < abs(best[0])):
                best = (g, x)
        if RED.search(r["s"]):
            best = (0, r)
        if best:
            r["reduction_gap"] = best[0]
            r["with_reduction"] = int(abs(best[0]) <= 30)
            xs = best[1]["s"]
            r["reduction_type"] = "loss" if "彌補虧損" in xs else ("cash" if re.search(r"現金減資|退還股款", xs) else "other")
        else:
            r["reduction_gap"] = ""; r["with_reduction"] = 0; r["reduction_type"] = ""

    # E2 正式（v1b＝規則 A；裁定 seq443）
    e1_dates = {}
    for r in e1:
        e1_dates.setdefault(r["stock_id"], []).append(D(r))
    e2m = dedup([dict(x, cls="E2", followup=0) for x in e2 if "A" in x["rules"]], lambda r: r["stock_id"])
    last = {}
    for r in sorted(e2m, key=lambda r: (r["date"], r.get("time", ""))):
        d = D(r); k = r["stock_id"]
        r["first12m"] = int(not (k in last and (d - last[k]).days <= 365))
        last[k] = d
        r["overlap_e1"] = int(any(abs((d - x).days) <= 60 for x in e1_dates.get(k, [])))

    out = e1 + e1fu + e3 + e2m
    out.sort(key=lambda r: (r["date"], r.get("time", ""), r["stock_id"], r["cls"]))
    hdr = ["date", "time", "stock_id", "name", "market", "class", "followup", "first12m", "outcome", "acq_date",
           "with_reduction", "reduction_gap", "reduction_type", "strategic_subj", "instrument", "overlap_e1", "subject", "serial"]
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(hdr)
        for r in out:
            w.writerow([r["date"], r.get("time", ""), r["stock_id"], r.get("name", ""), r["market"], r["cls"], r["followup"],
                        r.get("first12m", ""), r.get("outcome", ""), r.get("acq_date", ""), r.get("with_reduction", ""),
                        r.get("reduction_gap", ""), r.get("reduction_type", ""), r.get("strategic_subj", ""),
                        r.get("instrument", ""), r.get("overlap_e1", ""), r["subject"], r.get("serial", "")])

    # E2 候選三版（只在給 --e2-candidates 路徑時輸出；seq443 後不放 curated 目錄）
    e1_by = {}
    for r in e1:
        e1_by.setdefault(r["stock_id"], []).append(D(r))
    vers = {"e2_v1": set("A"), "e2_v2": set("ABC"), "e2_v3": set("ABCDE")}
    keep = {}
    for v, rs in vers.items():
        for r in dedup([x for x in e2 if set(x["rules"]) & rs], lambda r: r["stock_id"]):
            keep.setdefault(r.get("serial", "") + r["date"] + r["stock_id"], [r, set()])[1].add(v)
    e2o = sorted(keep.values(), key=lambda t: (t[0]["date"], t[0].get("time", ""), t[0]["stock_id"]))
    with (io.open(a.e2_candidates, "w", encoding="utf-8", newline="") if a.e2_candidates else io.StringIO()) as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "time", "stock_id", "name", "market", "rules", "e2_v1", "e2_v2", "e2_v3", "after_e1", "subject", "serial"])
        for r, vs in e2o:
            ae = int(any(0 <= (D(r) - d).days <= 180 for d in e1_by.get(r["stock_id"], [])))
            w.writerow([r["date"], r.get("time", ""), r["stock_id"], r.get("name", ""), r["market"], r["rules"],
                        int("e2_v1" in vs), int("e2_v2" in vs), int("e2_v3" in vs), ae, r["subject"], r.get("serial", "")])

    # samples
    def write_sample(path, items, cols):
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(cols + ["subject", "manual"])
            for r in sorted(items, key=lambda r: (r["cls"], r["date"])):
                w.writerow([r.get(c, "") for c in cols] + [r["subject"], ""])
    # 抽樣檔是人工核對的紀錄：已存在就不覆寫（--resample 才重抽）。第一輪＝sample50.csv（v1 規則下抽）；
    # 第二輪＝sample50_r2.csv（當時規則下、seed+1、排除第一輪已核過的主旨）；E2＝e2_sample30.csv（seed+2，每版 30）。
    cols = ["date", "stock_id", "cls", "outcome", "acq_date", "with_reduction", "strategic_subj", "instrument"]
    p1, p2, pe2 = (os.path.join(HERE, x) for x in ("sample50.csv", "sample50_r2.csv", "e2_sample30.csv"))
    if a.resample or not os.path.exists(p1):
        random.seed(a.seed)
        write_sample(p1, random.sample(e1, min(a.sample, len(e1))) + random.sample(e3, min(a.sample, len(e3))), cols)
    seen = {(r["date"], r["stock_id"], r["subject"]) for r in csv.DictReader(io.open(p1, encoding="utf-8"))}
    if a.resample or not os.path.exists(p2):
        random.seed(a.seed + 1)
        q1 = [x for x in e1 if (x["date"], x["stock_id"], x["subject"]) not in seen]
        q3 = [x for x in e3 if (x["date"], x["stock_id"], x["subject"]) not in seen]
        write_sample(p2, random.sample(q1, min(a.sample, len(q1))) + random.sample(q3, min(a.sample, len(q3))), cols)
    if a.resample or not os.path.exists(pe2):
        random.seed(a.seed + 2)
        e2s = []
        for v in ("e2_v1", "e2_v2", "e2_v3"):
            pool = [dict(t[0], cls=v) for t in e2o if v in t[1]]
            e2s += random.sample(pool, min(30, len(pool)))
        write_sample(pe2, e2s, ["date", "stock_id", "cls", "rules"])
    pe2f = os.path.join(HERE, "sample50_e2.csv")
    if a.resample or not os.path.exists(pe2f):
        random.seed(a.seed + 3)
        write_sample(pe2f, random.sample(e2m, min(a.sample, len(e2m))), ["date", "stock_id", "cls", "first12m", "overlap_e1"])
    print(f"E2 主事件（v1c）{len(e2m)}（first12m {sum(r['first12m'] for r in e2m)}；overlap_e1 {sum(r['overlap_e1'] for r in e2m)}；"
          f"first12m 且不重疊 {sum(r['first12m'] and not r['overlap_e1'] for r in e2m)}）")

    # summary
    by = {}
    for r in e1 + e3:
        by.setdefault((r["date"][:4], r["cls"]), 0); by[(r["date"][:4], r["cls"])] += 1
    print(f"E1 主事件 {len(e1)}（first12m {sum(r['first12m'] for r in e1)}；success {sum(r['outcome']=='success' for r in e1)}、"
          f"fail {sum(r['outcome']=='fail' for r in e1)}、空白 {sum(r['outcome']=='' for r in e1)}；acq_date 有 {sum(bool(r['acq_date']) for r in e1)}）｜E1 後續 {len(e1fu)}")
    print(f"E3 主事件 {len(e3)}（first12m {sum(r['first12m'] for r in e3)}；with_reduction {sum(r['with_reduction'] for r in e3)}；"
          f"strategic_subj {sum(r['strategic_subj'] for r in e3)}；instrument " +
          " ".join(f"{k}:{sum(r['instrument']==k for r in e3)}" for k in ("common", "pref", "sec", "dr")) + "）")
    print("逐年 E1/E3：" + " ".join(f"{y}:{by.get((y,'E1'),0)}/{by.get((y,'E3'),0)}" for y in sorted({k[0] for k in by})))
    for v in vers:
        n = sum(1 for t in e2o if v in t[1])
        print(f"{v}: {n}（after_e1 另見檔）")
    e1d = {}
    for r in e1:
        e1d.setdefault(r["stock_id"], []).append(D(r))
    orph = [r for r in e1fu if not any(0 <= (D(r) - d).days <= 150 for d in e1d.get(r["stock_id"], []))]
    print(f"E1 孤兒後續公告（前 150 天無主事件，疑漏首次宣告）{len(orph)} 則、{len({r['stock_id'] for r in orph})} 檔")
    for r in orph:
        print("  orphan", r["date"], r["stock_id"], r.get("name", ""), r["s"][:70])
    print("E2 各規則命中（去重前）："+ " ".join(f"{c}:{sum(c in x['rules'] for x in e2)}" for c in "ABCDE"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
