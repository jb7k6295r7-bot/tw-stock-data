# -*- coding: utf-8 -*-
"""run_c3s_month.sh 各支 py 的共用設定：固定用 10/17 版程式 f56133f55a（worktree ~/c3s_f561）、世界檔指到本期工作夾、記錄時間全程同一個。
⛔ 只在本行程內改「讀檔／寫檔位置」與「記錄時間」，不改任何選股、規則程式（檔案一行未動）。"""
import hashlib
import os
import sys

F561 = os.path.expanduser("~/c3s_f561")
REPO = os.path.expanduser("~/tw-p17")
OLD_REV = "f56133f55a"
NEW_REV = "e71b5bc77e"


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def setup(world_dir, root):
    """⇒ (A4, K)。須在任何 backtest import 之前呼叫。"""
    if os.path.realpath(os.environ.get("US_DATA_ROOT_A2", "")) != os.path.realpath(root):
        raise SystemExit(f"US_DATA_ROOT_A2 須等於 --root（{root}）")
    sys.path.insert(0, F561)
    import backtest
    bp = os.path.realpath(list(backtest.__path__)[0])
    if bp != os.path.realpath(os.path.join(F561, "backtest")):
        raise SystemExit(f"backtest 套件不是 f56133f55a worktree：{bp}")
    from backtest import researchUSA4 as A4
    A4.WORK = world_dir                       # 只讀／寫本期世界檔（⛔ 不碰共用 ~/us_work/a4/world.npz）
    from backtest import researchUSC as K
    ts = os.environ.get("C3S_RUN_TS")
    if ts:
        K.now_tpe = lambda: ts                # 全程同一個記錄時間（舊版、新版換股單「記錄時間」欄才會一致）
    return A4, K


def patch_forward_now(*mods):
    ts = os.environ.get("C3S_RUN_TS")
    if ts:
        for m in mods:
            m.now_tpe = lambda: ts
