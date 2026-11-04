# -*- coding: utf-8 -*-
"""台股合理價機械版——「穩定溢價本益比 35」變體：正式跑（報酬只當描述；判語事先固定）。

登錄：產業 seq82（pw1 sha f79e37d619c9fb0f）；發號：裁定 seq495 §一；正式跑：裁定 seq496 §一（「可帶 --formal --ruling seq496 跑」）。
頻率表與乾跑：backtest/researchTWStablePE35_freq.py → backtest/resultsStablePE35/freq/（commit 11e4264dc4）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchTWStablePE35_formal.py --formal --ruling seq496
    （⛔ 沒帶 --formal --ruling seq496 一律拒跑）

程式重用（⛔ 不改原版檔、⛔ 不寫第二份報酬實作）：
  - 單筆 1 年／3 年報酬：原版 bt.py 原跑輸出 twfv_recheck/orig/detail.csv 的 ret_1y／ret_3y（還原價、出場日沒成交用最後成交價、
    硬斷點落在窗內 ⇒ NaN；bt.py L139–146、L206–219）。bt.py 是頂層腳本（import 會整份重跑並覆寫 orig/），⇒ 讀它的原跑輸出，
    開跑先驗 bt.py／value.py sha256（researchTWCheapTrend_fv.verify_orig）。
  - 原版各組每評估日平均、大盤（加權報酬指數）1 年／3 年：原版輸出 orig/groups.csv 的 r1_*／r3_*／r1_大盤／r3_大盤／diff1／diff3。
    本檔用 detail.csv 照 bt.py L229–236 的同一取平均（pass_q＝1、該組 ret 非空者平均）重算原版各組，須與 groups.csv 相同（自檢；容差 1e-12，浮點尾差）。
  - 變體分組：頻率表輸出 resultsStablePE35/freq/tw_stable_rows.csv（只列穩定溢價或分組有變者；其餘列變體＝原版，
    freq 一致性檢查「變體只改穩定溢價者」0 筆）。本檔先重跑 freq 確認 0 不一致再跑。
  - 按進場年分群 bootstrap：bt.py 的 cluster_ci 在頂層腳本內不可 import；台股主格依裁定 seq496 不算平均也不算 CI，
    描述欄也只報平均與評估日數（不報 CI）⇒ 本檔不需要 bootstrap。

══════════ 判語與讀法（看任何報酬前寫死；⛔ 不因數字改）══════════
"""
import os, sys, json, argparse, datetime
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from researchTWCheapTrend_fv import verify_orig  # noqa: E402

# ── 事先固定（seq496 §一：判語事先固定「還沒測（依構造）」）──
FIXED_VERDICT = '還沒測（依構造）'
RULING_REQUIRED = 'seq496'
REG = '產業 seq82 pw1 f79e37d619c9fb0f'
RULINGS = '發號 裁定 seq495 §一；正式跑 裁定 seq496 §一'
NI_BOUND = -0.05     # seq82 §三 不劣於界線（CI 下緣 > −5 個百分點）——只寫在結果裡，⛔ 不用它下判語
# 裁定 seq496 §一「結果句必寫」（逐字）
SENTENCES_SEQ496 = [
    '台股只有 1 檔、3 筆，⛔ 不算任何平均意義，只列逐筆方向（不列個股報酬金額外的推論）。',
    '美股 49 筆、15 檔、17 個評估日；原屬「接近」20、「偏貴」29。',
    '不劣於界線 −5 個百分點；沒通過也只寫「測不出（不能說不劣）」，但本件已依構造還沒測，判語不看數字。',
]
READINGS_TW = [
    '判語：還沒測（依構造）——重新分類組 3 筆 < 20、出現評估日 3 < 8、進場年群數 2 < 24（〈四十九〉；seq495／seq496）。報酬數字不影響判語。',
    '主格（seq82 §三，持有 1 年）：逐筆「重新分類組該筆 1 年報酬 − 同日原版可買組平均」；依 seq496 只列逐筆方向（正／負）與筆數，⛔ 不報平均、不報 CI、不做推論。',
    '單筆報酬＝原版 detail.csv 的 ret_1y／ret_3y（硬斷點落在窗內 ⇒ 不可算，不列方向）；同日原版可買組平均＝原版 groups.csv 的 r1_可買／r3_可買。',
    '描述（不判）：穩定溢價家數（freq）；原版與變體各自「可買 − 偏貴」（每評估日兩組都有報酬者取差，再對評估日平均，同 bt.py diff1）；重新分類組 vs 大盤（逐筆方向）；3 年持有（逐筆方向＋可買−偏貴平均）。',
    '方向：差 > 0 記「正」、< 0 記「負」、＝0 記「零」；不可算記「不可算」。',
]
SNAP_COMMIT = '8e5d22eb306895d15bd93643284330983c57a823'
ORIG = os.path.join(HERE, 'twfv_recheck', 'orig')
FREQ = os.path.join(HERE, 'resultsStablePE35', 'freq')
OUT = os.path.join(HERE, 'resultsStablePE35', 'formal')
GROUPS = ('可買', '接近', '偏貴')


def sign(x):
    if x is None or not np.isfinite(x):
        return '不可算'
    return '正' if x > 0 else ('負' if x < 0 else '零')


def group_means(det, gcol, rcol):
    """bt.py L229–236 同一取平均：pass_q＝1、該組、ret 非空者平均（全空 ⇒ NaN）。→ {date: {組: mean}}。"""
    q = det[det.pass_q == 1]
    out = {}
    for E, d in q.groupby('date', sort=True):
        out[E] = {}
        for g in GROUPS:
            x = d.loc[d[gcol] == g, rcol]
            out[E][g] = x.mean() if x.notna().any() else np.nan
    return out


def diff_avg(gm, dates):
    v = [gm[E]['可買'] - gm[E]['偏貴'] for E in dates if E in gm]
    v = [x for x in v if np.isfinite(x)]
    return (float(np.mean(v)) if v else None), len(v)


# ═════════════ 共用輸出（台股、美股兩支正式跑都寫同一份 result.json／結果.md）═════════════
def taipei_now():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')


def write_merged(key, res):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, 'result.json')
    R = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    R['登錄'] = REG; R['裁定'] = RULINGS; R['判語（事先固定）'] = FIXED_VERDICT
    R['裁定seq496結果句（逐字）'] = SENTENCES_SEQ496
    R[key] = res
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))
    with open(os.path.join(OUT, '結果.md'), 'w', encoding='utf-8') as f:
        f.write(render_md(R))


def pp(x, nd=2):
    return '—' if x is None else f'{x * 100:+.{nd}f}pp'


def pc(x, nd=2):
    return '—' if x is None else f'{x * 100:+.{nd}f}%'


def render_md(R):
    L = ['# 穩定溢價本益比 35（台股＋美股合理價機械版變體）——正式跑（報酬只當描述）', '',
         f'- 登錄：{REG}；{RULINGS}（`--formal --ruling seq496`）。頻率表與乾跑見 `../freq/`。',
         f'- **判語（事先固定，⛔ 不因數字改）：台股、美股皆「{FIXED_VERDICT}」。**',
         '- 用語：本件不下任何方向性結論；數字只當描述，給使用者參考（seq82 §四：看板參數不動）。', '',
         '## 裁定 seq496 結果句（逐字）', '']
    L += [f'{i}. {s}' for i, s in enumerate(SENTENCES_SEQ496, 1)]
    L += ['']
    T = R.get('台股')
    if T:
        m = T['主格_1年']
        L += ['## 台股', '', f'- 資料 commit `{T["資料commit"]}`；原版 sha 驗過；freq 一致性 0 不一致（見下）。',
              f'- 判語：**{T["判語"]}**（{T["判語依據"]}）。', '',
              '### 主格（持有 1 年；只列逐筆方向，不報平均與 CI）', '',
              '| 評估日 | 代號 | 原版分組 | 重新分類組該筆 − 同日原版可買平均 |', '|---|---|---|---|']
        L += [f'| {r["評估日"]} | {r["代號"]} | {r["原版分組"]} | {r["方向"]} |' for r in m['逐筆']]
        L += ['', f'- 筆數：正 {m["正"]}、負 {m["負"]}、零 {m["零"]}、不可算 {m["不可算"]}（共 {m["筆數"]} 筆，1 檔）。⛔ 不做推論。', '']
        d = T['描述']
        s = d['穩定溢價家數']
        L += ['### 描述（不判）', '',
              f'- 穩定溢價家數／評估日（母體內）中位 {s["中位"]:g}、最少 {s["最少"]}、最大 {s["最大"]}（涉及 {s["涉及檔數"]} 檔；過品質門檻者中位 {s["過品質門檻_中位"]:g}）。',
              '', '| 可買 − 偏貴（評估日平均） | 1 年 | 評估日數 | 3 年 | 評估日數 |', '|---|---|---|---|---|']
        for k in ('原版', '變體'):
            a = d['可買減偏貴'][k]
            L += [f'| {k} | {pp(a["1年"])} | {a["1年評估日數"]} | {pp(a["3年"])} | {a["3年評估日數"]} |']
        L += ['', '| 評估日 | 重新分類組 vs 大盤 1 年 | 3 年：重新分類 − 原版可買 | 3 年：重新分類 vs 大盤 |', '|---|---|---|---|']
        L += [f'| {r["評估日"]} | {r["對大盤_1年"]} | {r["減原版可買_3年"]} | {r["對大盤_3年"]} |' for r in d['重新分類組逐筆方向_其他']]
        L += ['', f'- 自檢：{T["自檢"]["說明"]}', '']
    U = R.get('美股')
    if U:
        m = U['主格_1年']
        L += ['## 美股', '', f'- 資料 commit `{U["資料commit"]}`（私有庫；本檔只放彙總，逐筆在 `~/us_work/stablepe35/formal/`）。',
              f'- 判語：**{U["判語"]}**（{U["判語依據"]}）。', '',
              '### 主格（持有 1 年）：重新分類組平均 − 同日原版可買平均，對評估日平均', '',
              f'- 平均差 **{pp(m["平均差"])}**，按進場年分群 bootstrap 95% CI **[{pp(m["CI95"][0])}, {pp(m["CI95"][1])}]**；'
              f'有效評估日 {m["有效評估日數"]}、群數 {m["群數"]}（{", ".join(str(y) for y in m["進場年"])}）；重新分類組 1 年可算 {m["重新分類組1年可算筆數"]} 筆。',
              f'- 不劣於界線 −5 個百分點（seq82 §三：平均 ≥ 0 且 CI 下緣 > −5pp）：平均 ≥ 0 {"是" if m["界線對照_只描述"]["平均≥0"] else "否"}、'
              f'CI 下緣 > −5pp {"是" if m["界線對照_只描述"]["CI下緣>-5pp"] else "否"}——只描述；本件已依構造還沒測，判語不看數字。', '']
        d = U['描述']
        s = d['穩定溢價家數']
        L += ['### 描述（不判）', '',
              f'- 穩定溢價家數／評估日（母體內）中位 {s["中位"]:g}、最少 {s["最少"]}、最大 {s["最大"]}（涉及 {s["涉及檔數"]} 檔；有分組者中位 {s["有分組_中位"]:g}）。', '',
              '| 項目 | 1 年 平均 | 95% CI | 評估日數 | 3 年 平均 | 評估日數 |', '|---|---|---|---|---|---|']
        for k, a in d['表'].items():
            ci = a.get('1年CI95')
            cis = '—' if not ci or ci[0] is None else f'[{pp(ci[0])}, {pp(ci[1])}]'
            L += [f'| {k} | {pp(a["1年"])} | {cis} | {a["1年評估日數"]} | {pp(a["3年"])} | {a["3年評估日數"]} |']
        L += ['', f'- 自檢：{U["自檢"]["說明"]}', '']
    L += ['## 讀法（看任何報酬前寫死）', '']
    for k, rr in (('台股', READINGS_TW), ('美股', R.get('美股', {}).get('讀法', []))):
        if rr:
            L += [f'- {k}：'] + [f'  - {x}' for x in rr]
    L += ['', f'產出（台北時間）：{taipei_now()}', '', '描述，不是買賣建議', '']
    return '\n'.join(L)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--formal', action='store_true')
    ap.add_argument('--ruling', default=None)
    a = ap.parse_args()
    if not (a.formal and a.ruling == RULING_REQUIRED):
        print('⛔ 拒跑：正式跑要 --formal --ruling seq496（裁定 seq496 §一）。')
        sys.exit(2)
    # ── 判語與讀法先寫死（此時尚未讀任何報酬欄）──
    res = {'判語': FIXED_VERDICT, '讀法': READINGS_TW}

    vo = verify_orig(); assert all(v[1] for v in vo.values()), vo
    S = json.load(open(os.path.join(FREQ, 'tw_freq_summary.json'), encoding='utf-8'))
    assert S['資料commit'] == SNAP_COMMIT, S['資料commit']
    chk = S['一致性檢查']
    for k in ('母體只在本檔', '母體只在orig', '原版分組_fair_at_vs_orig_detail_不一致', '變體上限改回25_vs_原版分組_不一致',
              '變體上限改回25_vs_orig_detail_不一致', '變體只改穩定溢價者_非穩定溢價卻改組'):
        assert chk[k] == 0, (k, chk[k])
    trig = S['還沒測觸發（依構造）']
    assert any(trig.values())
    res['資料commit'] = SNAP_COMMIT
    res['判語依據'] = '依構造：' + '、'.join(k for k, v in trig.items() if v) + '（頻率表 seq495／seq496 已收下；報酬不影響判語）'

    # ── 讀原版輸出與變體分組 ──
    det = pd.read_csv(os.path.join(ORIG, 'detail.csv'), dtype={'date': str, 'stock_id': str, 'group': str})
    det['group'] = det['group'].fillna('')
    gcsv = pd.read_csv(os.path.join(ORIG, 'groups.csv'), dtype={'date': str}).set_index('date')
    st = pd.read_csv(os.path.join(FREQ, 'tw_stable_rows.csv'), dtype={'date': str, 'stock_id': str, 'group_orig': str, 'group_var': str})
    st[['group_orig', 'group_var']] = st[['group_orig', 'group_var']].fillna('')
    key = det.set_index(['date', 'stock_id'])
    chg = st[st.group_var != st.group_orig]
    assert (key.loc[list(zip(chg.date, chg.stock_id)), 'group'].values == chg.group_orig.values).all()
    det['group_var'] = det['group']
    gv = dict(zip(zip(chg.date, chg.stock_id), chg.group_var))
    det['group_var'] = [gv.get((d, s), g) for d, s, g in zip(det.date, det.stock_id, det.group)]
    det['reclass'] = (det.group_var == '可買') & (det.group != '可買')
    rc = det[det.reclass].sort_values(['date', 'stock_id'])
    assert len(rc) == int(st.reclass.sum()) == S['重新分類組']['總筆數'] == 3
    assert rc.stock_id.nunique() == 1

    # ── 自檢：原版各組平均（同 bt.py 取法）與 groups.csv 逐位相同 ──
    gm1o, gm3o = group_means(det, 'group', 'ret_1y'), group_means(det, 'group', 'ret_3y')
    nbad, maxdev = 0, 0.0          # 容差 1e-12（CSV 來回與加總順序的浮點尾差；實測最大 ~2e-15）
    for E in gcsv.index:
        for g in GROUPS:
            for gm, col in ((gm1o, f'r1_{g}'), (gm3o, f'r3_{g}')):
                a_, b_ = gm.get(E, {}).get(g, np.nan), gcsv.loc[E, col]
                if pd.isna(a_) or pd.isna(b_):
                    nbad += int(pd.isna(a_) != pd.isna(b_))
                else:
                    maxdev = max(maxdev, abs(a_ - b_)); nbad += int(abs(a_ - b_) > 1e-12)
    assert nbad == 0, nbad
    gm1v, gm3v = group_means(det, 'group_var', 'ret_1y'), group_means(det, 'group_var', 'ret_3y')
    dates = list(gcsv.index)

    # ── 主格：逐筆方向（⛔ 不報平均、不報 CI）──
    rows, rows2 = [], []
    for r in rc.itertuples(index=False):
        x1 = r.ret_1y - gcsv.loc[r.date, 'r1_可買'] if pd.notna(r.ret_1y) else np.nan
        rows.append({'評估日': r.date, '代號': r.stock_id, '原版分組': r.group, '方向': sign(x1)})
        rows2.append({'評估日': r.date, '代號': r.stock_id,
                      '對大盤_1年': sign(r.ret_1y - gcsv.loc[r.date, 'r1_大盤']),
                      '減原版可買_3年': sign(r.ret_3y - gcsv.loc[r.date, 'r3_可買']),
                      '對大盤_3年': sign(r.ret_3y - gcsv.loc[r.date, 'r3_大盤'])})
    cnt = {k: sum(1 for r in rows if r['方向'] == k) for k in ('正', '負', '零', '不可算')}
    res['主格_1年'] = dict(逐筆=rows, 筆數=len(rows), **cnt,
                         說明='依裁定 seq496：只列逐筆方向與筆數；⛔ 不報平均、不報 CI、不做推論。不劣於界線 −5 個百分點在台股不適用（不算平均）。')

    # ── 描述 ──
    o1, n_o1 = diff_avg(gm1o, dates); o3, n_o3 = diff_avg(gm3o, dates)
    v1, n_v1 = diff_avg(gm1v, dates); v3, n_v3 = diff_avg(gm3v, dates)
    assert n_o1 == int(gcsv.diff1.notna().sum()) and abs(o1 - gcsv.diff1.mean()) < 1e-12
    res['描述'] = {
        '穩定溢價家數': {'中位': S['穩定溢價家數_每評估日_中位_最少_最大'][0], '最少': S['穩定溢價家數_每評估日_中位_最少_最大'][1],
                     '最大': S['穩定溢價家數_每評估日_中位_最少_最大'][2], '涉及檔數': S['穩定溢價_涉及檔數'],
                     '過品質門檻_中位': S['穩定溢價且過品質門檻_中位_最少_最大'][0]},
        '可買減偏貴': {'原版': {'1年': o1, '1年評估日數': n_o1, '3年': o3, '3年評估日數': n_o3},
                    '變體': {'1年': v1, '1年評估日數': n_v1, '3年': v3, '3年評估日數': n_v3},
                    '說明': '每評估日「可買平均 − 偏貴平均」（兩組都有報酬者），再對評估日平均（同 bt.py diff1／diff3）。不報 CI（原版 cluster_ci 在頂層腳本內不可 import；描述不判）。'},
        '重新分類組逐筆方向_其他': rows2,
        '說明': '重新分類組 vs 大盤、3 年：只列逐筆方向（seq496）；大盤＝原版 groups.csv 的 r1_大盤／r3_大盤（加權報酬指數）。',
    }
    res['自檢'] = {'原版各組平均重算_vs_groups.csv_不一致': nbad, '原版各組平均重算_vs_groups.csv_最大絕對差': maxdev,'freq一致性檢查': {k: v for k, v in chk.items() if k != 'sha_orig'},
                 'sha_orig': chk['sha_orig'],
                 '說明': f'原版各組每評估日平均（1 年／3 年）照 bt.py 取法重算與 groups.csv {nbad} 不一致（容差 1e-12，最大差 {maxdev:.1e}）；原版可買−偏貴 1 年 {pp(o1)}（{n_o1} 日）＝原跑 −20.27pp；'
                       'freq 一致性（上限改回 25 vs 原版、vs orig/detail.csv、變體只改穩定溢價者）皆 0。'}
    write_merged('台股', res)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
