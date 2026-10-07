# -*- coding: utf-8 -*-
"""USREG-A4 G15（裁定 seq319 Q8）：GICS sub-industry 名稱 ⇒ industry group 對照表（執行者依 GICS 官方結構手寫；寫死於 2026-10-07 11:54（台北））。

原則（⭐ 看任何 A4 報酬前寫死）：
  ① B3（Wikipedia 歷史版）的 sub-industry 欄名稱各版不一（有時填的是 industry 名，如 Banks、Media、Software、IT Services）⇒ 名稱正規化
     （小寫、& 與 and 同、去多餘空白、REITS＝REITs）後查表；industry 名也直接對到它所屬的 group（GICS 一個 industry 只屬一個 group）。
  ② 對到「當時那一版 GICS」裡該名稱所屬的 industry group；沿用至今的 group 一律用 2023-03 版名稱：
     Retailing ⇒ Consumer Discretionary Distribution & Retail；Food & Staples Retailing ⇒ Consumer Staples Distribution & Retail；
     Diversified Financials ⇒ Financial Services；Media（2018 前在 Consumer Discretionary）⇒ Media & Entertainment；
     Real Estate（2016～2023 單一 group）依 sub-industry 分到 2023 的 Equity REITs／Real Estate Management & Development。
  ③ 同名在不同版本屬不同 group 者用 B3 的 sector 欄分辨：Data Processing & Outsourced Services（IT ⇒ Software & Services〔2023 前〕；
     Industrials ⇒ Commercial & Professional Services〔2023 起〕）。
     2023 前的 Thrifts & Mortgage Finance 屬 Banks（當時）；Internet Software & Services、Home Entertainment Software（2018 前）屬 Software & Services（當時）。
  ④ 對不到（空白、TBD、破壞文字、不是 GICS 名）⇒ None（計入「對不上」）。sector 欄與名稱矛盾（例 Financials｜Specialty Retail）⇒ 照名稱。
GICS 2023 的 25 個 industry group：見 IG25。
"""
from __future__ import annotations

import re

IG25 = ("Energy", "Materials", "Capital Goods", "Commercial & Professional Services", "Transportation",
        "Automobiles & Components", "Consumer Durables & Apparel", "Consumer Services", "Consumer Discretionary Distribution & Retail",
        "Consumer Staples Distribution & Retail", "Food, Beverage & Tobacco", "Household & Personal Products",
        "Health Care Equipment & Services", "Pharmaceuticals, Biotechnology & Life Sciences",
        "Banks", "Financial Services", "Insurance",
        "Software & Services", "Technology Hardware & Equipment", "Semiconductors & Semiconductor Equipment",
        "Telecommunication Services", "Media & Entertainment", "Utilities",
        "Equity Real Estate Investment Trusts (REITs)", "Real Estate Management & Development")

_E, _M, _CG, _CPS, _TR = IG25[0:5]
_AUTO, _CDA, _CSV, _CDR = IG25[5:9]
_CSR, _FBT, _HPP = IG25[9:12]
_HCE, _PBL = IG25[12:14]
_BNK, _FS, _INS = IG25[14:17]
_SW, _HW, _SEMI = IG25[17:20]
_TEL, _MED, _UTL = IG25[20:23]
_REIT, _REM = IG25[23:25]

_MAP = {
    # Energy
    "coal & consumable fuels": _E, "energy equipment & services": _E, "integrated oil & gas": _E, "oil & gas drilling": _E,
    "oil & gas equipment & services": _E, "oil & gas exploration & production": _E, "oil & gas refining & marketing": _E,
    "oil & gas refining & marketing & transportation": _E, "oil & gas storage & transportation": _E, "oil, gas & consumable fuels": _E,
    "energy": _E,
    # Materials
    "aluminum": _M, "chemicals": _M, "commodity chemicals": _M, "construction materials": _M, "containers & packaging": _M, "copper": _M,
    "diversified chemicals": _M, "diversified metals & mining": _M, "fertilizers & agricultural chemicals": _M, "forest products": _M, "gold": _M,
    "industrial gases": _M, "metal & glass containers": _M, "metal, glass & plastic containers": _M, "metals & mining": _M,
    "paper & forest products": _M, "paper & plastic packaging products & materials": _M, "paper packaging": _M, "paper products": _M,
    "precious metals & minerals": _M, "silver": _M, "specialty chemicals": _M, "specialty chemical": _M, "specialty bust chemicals": _M,
    "steel": _M, "wood": _M, "materials": _M,
    # Industrials — Capital Goods
    "aerospace & defense": _CG, "agricultural & farm machinery": _CG, "building products": _CG, "building products, including water valves": _CG,
    "capital goods": _CG, "construction & engineering": _CG, "construction & farm equipment & heavy trucks": _CG,
    "construction & farm machinery & heavy trucks": _CG, "construction machinery & heavy transportation equipment": _CG,
    "construction machinery & heavy trucks": _CG, "electrical components & equipment": _CG, "electrical equipment": _CG,
    "heavy electrical equipment": _CG, "industrial conglomerates": _CG, "industrial machinery": _CG,
    "industrial machinery & supplies & components": _CG, "machinery": _CG, "trading companies & distributors": _CG,
    # Industrials — Commercial & Professional Services
    "commercial printing": _CPS, "commercial services & supplies": _CPS, "diversified commercial services": _CPS,
    "diversified support services": _CPS, "environmental & facilities services": _CPS, "environmental services": _CPS,
    "diversified facilities & environmental": _CPS, "human resource & employment services": _CPS, "human resources & employment services": _CPS,
    "office services & supplies": _CPS, "research & consulting services": _CPS, "security & alarm services": _CPS,
    "professional services": _CPS, "data processing services": None,   # 由 sector 分辨（見 ig_of）
    # Industrials — Transportation
    "air freight & logistics": _TR, "airlines": _TR, "passenger airlines": _TR, "cargo ground transportation": _TR, "marine": _TR,
    "marine transportation": _TR, "passenger ground transportation": _TR, "rail transportation": _TR, "railroads": _TR, "road & rail": _TR,
    "trucking": _TR, "ground transportation": _TR, "transportation infrastructure": _TR,
    # Consumer Discretionary
    "auto components": _AUTO, "auto parts & equipment": _AUTO, "automotive parts & equipment": _AUTO, "automobile manufacturers": _AUTO,
    "motorcycle manufacturers": _AUTO, "tires & rubber": _AUTO, "automobiles": _AUTO,
    "apparel, accessories & luxury goods": _CDA, "footwear": _CDA, "textiles, apparel & luxury goods": _CDA, "textiles": _CDA,
    "home furnishings": _CDA, "household appliances": _CDA, "household durables": _CDA, "housewares & specialties": _CDA,
    "homebuilding": _CDA, "leisure products": _CDA, "consumer electronics": _CDA,
    "casinos & gaming": _CSV, "hotels, resorts & cruise lines": _CSV, "hotels, restaurants & leisure": _CSV, "leisure facilities": _CSV,
    "restaurants": _CSV, "education services": _CSV, "specialized consumer services": _CSV, "diversified consumer services": _CSV,
    "apparel retail": _CDR, "automotive retail": _CDR, "broadline retail": _CDR, "computer & electronics retail": _CDR,
    "department stores": _CDR, "general merchandise stores": _CDR, "home improvement retail": _CDR, "homefurnishing retail": _CDR,
    "internet & direct marketing retail": _CDR, "internet retail": _CDR, "multiline retail": _CDR, "other specialty retail": _CDR,
    "specialty retail": _CDR, "specialty stores": _CDR, "distributors": _CDR,
    # Consumer Staples
    "consumer staples merchandise retail": _CSR, "drug retail": _CSR, "food & staples retailing": _CSR, "food distributors": _CSR,
    "food retail": _CSR, "hypermarkets & super centers": _CSR,
    "agricultural products": _FBT, "agricultural products & services": _FBT, "beverages": _FBT, "brewers": _FBT, "distillers & vintners": _FBT,
    "food products": _FBT, "packaged foods & meats": _FBT, "soft drinks": _FBT, "soft drinks & non-alcoholic beverages": _FBT, "tobacco": _FBT,
    "household products": _HPP, "personal care products": _HPP, "personal products": _HPP,
    # Health Care
    "health care distribution & services": _HCE, "health care distributors": _HCE, "health care distributors & services": _HCE,
    "health care equipment": _HCE, "health care equipment & sales": _HCE, "health care equipment & services": _HCE,
    "health care equipment & supplies": _HCE, "health care facilities": _HCE, "health care providers & services": _HCE,
    "health care services": _HCE, "health care supplies": _HCE, "health care technology": _HCE, "healthcare technology": _HCE,
    "managed health care": _HCE,
    "biotechnology": _PBL, "pharmaceuticals": _PBL, "life sciences tool & equipment": _PBL, "life sciences tools & service": _PBL,
    "life sciences tools & services": _PBL,
    # Financials
    "banks": _BNK, "diversified banks": _BNK, "regional banks": _BNK, "thrifts & mortgage finance": _BNK,
    "asset management & custody banks": _FS, "capital markets": _FS, "consumer finance": _FS, "diversified financial services": _FS,
    "financial exchanges & data": _FS, "financial services": _FS, "investment banking & brokerage": _FS, "mortgage reits": _FS,
    "multi-sector holdings": _FS, "specialized finance": _FS, "transaction & payment processing services": _FS,
    "commercial & residential mortgage finance": _FS, "diversified financials": _FS,
    "insurance": _INS, "insurance brokers": _INS, "life & health insurance": _INS, "multi-line insurance": _INS,
    "property & casualty insurance": _INS, "reinsurance": _INS,
    # Information Technology
    "application software": _SW, "systems software": _SW, "software": _SW, "it consulting & other services": _SW,
    "it consulting & outsourced services": _SW, "it consulting & services": _SW, "it services": _SW, "internet services & infrastructure": _SW,
    "internet software & services": _SW, "home entertainment software": _SW, "data processing & outsources services": _SW,
    "communications equipment": _HW, "computer hardware": _HW, "computer storage & peripherals": _HW, "electronic components": _HW,
    "electronic equipment & instruments": _HW, "electronic equipment manufacturers": _HW, "electronic equipment, instruments & components": _HW,
    "electronic manufacturing services": _HW, "networking equipment": _HW, "office electronics": _HW, "technology distributors": _HW,
    "technology hardware, storage & peripherals": _HW, "telecommunications equipment": _HW,
    "semiconductor equipment": _SEMI, "semiconductor materials & equipment": _SEMI, "semiconductors": _SEMI,
    # Communication Services
    "alternative carriers": _TEL, "integrated telecommunication services": _TEL, "integrated telecommunications services": _TEL,
    "wireless telecommunication services": _TEL, "diversified telecommunication services": _TEL,
    "advertising": _MED, "broadcasting": _MED, "broadcasting & cable tv": _MED, "cable & satellite": _MED, "interactive home entertainment": _MED,
    "interactive media & services": _MED, "movies & entertainment": _MED, "publishing": _MED, "media": _MED, "entertainment": _MED,
    # Utilities
    "electric utilities": _UTL, "gas utilities": _UTL, "independent power producers & energy traders": _UTL, "multi-utilities": _UTL,
    "multiutilities": _UTL, "renewable electricity": _UTL, "water utilities": _UTL,
    # Real Estate
    "data center reits": _REIT, "diversified reits": _REIT, "health care reits": _REIT, "hotel & resort reits": _REIT, "hotel & resorts reits": _REIT,
    "industrial reits": _REIT, "multi-family residential reits": _REIT, "office reits": _REIT, "other specialized reits": _REIT, "reits": _REIT,
    "residential reits": _REIT, "retail reits": _REIT, "self-storage reits": _REIT, "single-family residential reits": _REIT,
    "specialized reits": _REIT, "specialty reits": _REIT, "telecom tower reits": _REIT, "timber reits": _REIT, "equity reits": _REIT,
    "diversified real estate activities": _REM, "real estate services": _REM, "real estate development": _REM,
    "real estate operating companies": _REM, "real estate management & development": _REM,
}


def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower().replace(" and ", " & ")
    s = re.sub(r"\s+", " ", s)
    return s


def ig_of(sector, sub):
    """(B3 sector, B3 sub-industry) ⇒ industry group（2023 名稱）或 None。"""
    k = norm(sub)
    if not k or k == "tbd":
        return None
    if k in ("data processing & outsourced services", "data processing services"):
        sec = norm(sector)
        if sec == "industrials":
            return _CPS
        if sec == "information technology":
            return _SW
        return None
    return _MAP.get(k)
