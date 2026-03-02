#!/usr/bin/env python3
"""
relation AI — FTEベース × プログレッシブ課金モデル
「エンタープライズほど高くなる」設計で数十億ARRへ

前提:
  - 全部門プラットフォームではなく、CS/コミュニケーション領域で深く刺す
  - 大企業にとって3人分の人件費は端数 → 20〜60人分を堂々と課金
  - 企業規模が大きいほど Value Capture Rate を上げる（プログレッシブ）
  - FTE換算で説明する → 「50人分のコストで150人分の仕事をAIが処理」
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(OUTPUT_DIR, "relation_fte_pricing_model.pdf")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts_v3")
os.makedirs(CHART_DIR, exist_ok=True)

pdfmetrics.registerFont(TTFont("IPAGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"))
pdfmetrics.registerFont(TTFont("IPAPGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"))

BLUE   = HexColor("#1a56db")
PURPLE = HexColor("#7c3aed")
RED    = HexColor("#dc2626")
GREEN  = HexColor("#059669")
DARK   = HexColor("#0f172a")
GRAY   = HexColor("#64748b")
TBL_HDR = HexColor("#0f172a")
TBL_ALT = HexColor("#f1f5f9")

# ===========================================================================
# 人件費パラメータ
# ===========================================================================
FTE_ANNUAL  = 5_500_000          # CS担当1名 年間コスト（給与+社保+間接費）
FTE_MONTHLY = FTE_ANNUAL / 12    # ¥458,333/月
AI_COST_PER_REPLY = 3.4          # Sonnet 4.5 標準返信1件あたり原価(¥)
REPLIES_PER_FTE_MONTH = 960      # 1 FTE が月間に処理する件数 (8h×20d×6件/h)

# ===========================================================================
# プログレッシブ課金モデル
# エンタープライズほど Value Capture Rate が高い
# ===========================================================================
# 考え方:
#   - 大企業ほどAI導入の付加価値が高い（24/7対応、品質均一化、スケール対応、管理コスト削減）
#   - 大企業ほど価格感度が低い（3人分は端数、20人分でも「安い」）
#   - だからプログレッシブに課金率を上げる

TIERS = {
    "S": {
        "label": "Growth",
        "cs_reps_range": "5〜15名",
        "cs_reps_typical": 10,
        "ai_automation_rate": 0.50,
        "value_capture_rate": 0.20,      # 削減額の20%
        "color": "#22c55e",
    },
    "M": {
        "label": "Scale",
        "cs_reps_range": "15〜40名",
        "cs_reps_typical": 25,
        "ai_automation_rate": 0.55,
        "value_capture_rate": 0.25,      # 削減額の25%
        "color": "#3b82f6",
    },
    "L": {
        "label": "Enterprise",
        "cs_reps_range": "40〜120名",
        "cs_reps_typical": 70,
        "ai_automation_rate": 0.60,
        "value_capture_rate": 0.30,      # 削減額の30% ← ここがポイント
        "color": "#7c3aed",
    },
    "XL": {
        "label": "Enterprise Plus",
        "cs_reps_range": "120〜400名",
        "cs_reps_typical": 200,
        "ai_automation_rate": 0.60,
        "value_capture_rate": 0.35,      # 削減額の35% ← さらに高い
        "color": "#dc2626",
    },
}


def calc_tier(tier_key):
    """ティア経済性の計算"""
    t = TIERS[tier_key]
    reps = t["cs_reps_typical"]
    monthly_labor = reps * FTE_MONTHLY
    annual_labor = reps * FTE_ANNUAL

    # AI自動化による削減
    fte_replaced = reps * t["ai_automation_rate"]
    monthly_savings = fte_replaced * FTE_MONTHLY
    annual_savings = fte_replaced * FTE_ANNUAL

    # 課金額（プログレッシブ）
    monthly_charge = monthly_savings * t["value_capture_rate"]
    annual_charge = monthly_charge * 12
    charge_fte_equiv = monthly_charge / FTE_MONTHLY  # 何人分か

    # 顧客の手残り
    customer_keeps = monthly_savings - monthly_charge
    customer_roi = customer_keeps / monthly_charge

    # AI原価
    total_replies = fte_replaced * REPLIES_PER_FTE_MONTH
    monthly_ai_cost = total_replies * AI_COST_PER_REPLY
    gross_margin = (monthly_charge - monthly_ai_cost) / monthly_charge * 100

    return {
        "reps": reps,
        "monthly_labor": monthly_labor,
        "annual_labor": annual_labor,
        "fte_replaced": fte_replaced,
        "monthly_savings": monthly_savings,
        "monthly_charge": monthly_charge,
        "annual_charge": annual_charge,
        "charge_fte_equiv": charge_fte_equiv,
        "customer_keeps": customer_keeps,
        "customer_roi": customer_roi,
        "monthly_ai_cost": monthly_ai_cost,
        "gross_margin": gross_margin,
        "total_replies": total_replies,
    }


# ===========================================================================
# クレジットプラン設計（FTEベース版）
# ===========================================================================
CREDIT_PLANS = {
    "Growth": {
        "monthly_fee_fte": None,   # calc_tierから算出
        "tier": "S",
        "included_credits": 10_000,
        "extra_credit_price": 25,
        "features": "AI自動返信, 分類, 要約, ナレッジ基本",
        "support": "メール",
    },
    "Scale": {
        "monthly_fee_fte": None,
        "tier": "M",
        "included_credits": 40_000,
        "extra_credit_price": 22,
        "features": "+ 多言語, 高度なRAG, API連携",
        "support": "専任CSM",
    },
    "Enterprise": {
        "monthly_fee_fte": None,
        "tier": "L",
        "included_credits": 150_000,
        "extra_credit_price": 18,
        "features": "+ カスタムモデル, エージェント, 分析ダッシュボード",
        "support": "専任CSM + テクニカルSA",
    },
    "Enterprise Plus": {
        "monthly_fee_fte": None,
        "tier": "XL",
        "included_credits": 500_000,
        "extra_credit_price": 15,
        "features": "+ 専用インフラ, SLA 99.99%, オンサイト支援",
        "support": "専任チーム + CXO連携",
    },
}

# プラン月額をtierから設定
for plan_name, plan in CREDIT_PLANS.items():
    e = calc_tier(plan["tier"])
    plan["monthly_fee"] = round(e["monthly_charge"] / 10000) * 10000  # 万円単位に丸め
    plan["monthly_fee_fte"] = e["charge_fte_equiv"]


# ===========================================================================
# ARRシナリオ
# ===========================================================================
SCENARIOS = {
    "Conservative": {
        "label": "保守的",
        "color": "#94a3b8",
        "years": [
            {"S": 30,  "M": 8,   "L": 2,  "XL": 0},
            {"S": 120, "M": 35,  "L": 8,  "XL": 1},
            {"S": 300, "M": 100, "L": 25, "XL": 3},
        ]
    },
    "Base": {
        "label": "ベースケース",
        "color": "#3b82f6",
        "years": [
            {"S": 60,  "M": 15,  "L": 5,   "XL": 1},
            {"S": 250, "M": 70,  "L": 20,  "XL": 3},
            {"S": 600, "M": 200, "L": 60,  "XL": 10},
        ]
    },
    "Aggressive": {
        "label": "攻め",
        "color": "#7c3aed",
        "years": [
            {"S": 100, "M": 25,  "L": 8,   "XL": 2},
            {"S": 400, "M": 120, "L": 40,  "XL": 8},
            {"S": 1000, "M": 350, "L": 100, "XL": 20},
        ]
    },
}


def calc_scenario(name, year_idx):
    counts = SCENARIOS[name]["years"][year_idx]
    mrr = 0
    ai_cost = 0
    customers = 0
    seg_detail = {}
    for tier, count in counts.items():
        if count == 0:
            seg_detail[tier] = {"count": 0, "mrr": 0, "arr": 0}
            continue
        e = calc_tier(tier)
        tier_mrr = e["monthly_charge"] * count
        tier_ai = e["monthly_ai_cost"] * count
        mrr += tier_mrr
        ai_cost += tier_ai
        customers += count
        seg_detail[tier] = {"count": count, "mrr": tier_mrr, "arr": tier_mrr * 12}
    return {
        "mrr": mrr,
        "arr": mrr * 12,
        "ai_cost": ai_cost,
        "gross_profit": mrr - ai_cost,
        "gross_margin": (mrr - ai_cost) / mrr * 100 if mrr > 0 else 0,
        "customers": customers,
        "seg_detail": seg_detail,
    }


# ===========================================================================
# チャート
# ===========================================================================
def setup_mpl():
    plt.rcParams["font.family"] = "IPAGothic"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.unicode_minus"] = False


def chart_progressive_pricing():
    """プログレッシブ課金構造: 企業規模 vs FTE換算課金"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    tiers = list(TIERS.keys())
    labels = [TIERS[t]["label"] for t in tiers]
    colors = [TIERS[t]["color"] for t in tiers]
    reps = [TIERS[t]["cs_reps_typical"] for t in tiers]
    capture_rates = [TIERS[t]["value_capture_rate"] * 100 for t in tiers]

    # 左: CS人数 vs Value Capture Rate
    ax1.bar(labels, capture_rates, color=colors, alpha=0.85, width=0.5)
    for i, (cr, rep) in enumerate(zip(capture_rates, reps)):
        ax1.text(i, cr + 0.8, f"{cr:.0f}%", ha="center", fontsize=12, fontweight="bold")
        ax1.text(i, cr/2, f"CS {rep}名", ha="center", fontsize=9, color="white", fontweight="bold")
    ax1.set_ylabel("Value Capture Rate（%）", fontsize=11)
    ax1.set_title("プログレッシブ課金率\n（大企業ほど高い）", fontsize=13, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)
    ax1.set_ylim(0, 42)

    # 右: FTE換算の課金額
    fte_charges = [calc_tier(t)["charge_fte_equiv"] for t in tiers]
    fte_replaced = [calc_tier(t)["fte_replaced"] for t in tiers]

    x = np.arange(len(tiers))
    width = 0.3
    bars1 = ax2.bar(x - width/2, fte_replaced, width, label="AIが代替するFTE数",
                    color=[c for c in colors], alpha=0.4)
    bars2 = ax2.bar(x + width/2, fte_charges, width, label="課金額（FTE換算）",
                    color=colors, alpha=0.85)

    for i in range(len(tiers)):
        ax2.text(i - width/2, fte_replaced[i] + 1,
                 f"{fte_replaced[i]:.0f}人分",
                 ha="center", fontsize=9, fontweight="bold", color=TIERS[tiers[i]]["color"])
        ax2.text(i + width/2, fte_charges[i] + 1,
                 f"{fte_charges[i]:.0f}人分",
                 ha="center", fontsize=9, fontweight="bold")

    ax2.set_ylabel("FTE換算（人分）", fontsize=11)
    ax2.set_title("AI代替FTE数 vs 課金FTE数\n（差分 = 顧客の利益）", fontsize=13, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=10)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    path = os.path.join(CHART_DIR, "progressive_pricing.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_fte_waterfall():
    """Enterprise Plusの例: 200名のCS組織で何が起きるか"""
    fig, ax = plt.subplots(figsize=(10, 6))

    e = calc_tier("XL")
    labels = [
        "現行CS人件費\n(200名)",
        "AI自動化で\n削減される人件費",
        "relation AI\n課金額",
        "顧客の\n手残り利益",
    ]
    values = [
        e["monthly_labor"] / 10000,
        -e["monthly_savings"] / 10000,
        e["monthly_charge"] / 10000,
        e["customer_keeps"] / 10000,
    ]
    # ウォーターフォール
    cumulative = [values[0]]
    for i in range(1, len(values)):
        cumulative.append(cumulative[-1] + values[i])

    colors = ["#ef4444", "#f59e0b", "#3b82f6", "#22c55e"]
    bottoms = [0, values[0] + values[1], 0, 0]

    # バー
    bar_vals = [values[0], -values[1], values[2], values[3]]
    bar_bottoms = [0, values[0] + values[1], 0, 0]

    # 人件費全体
    ax.bar(0, values[0], color=colors[0], alpha=0.8, width=0.5)
    ax.text(0, values[0]/2, f"¥{values[0]:,.0f}万/月\n(200名分)",
            ha="center", va="center", fontsize=10, fontweight="bold", color="white")

    # 削減部分
    ax.bar(1, -values[1], bottom=values[0]+values[1], color=colors[1], alpha=0.8, width=0.5)
    ax.text(1, (values[0]+values[1]) + (-values[1])/2,
            f"▲¥{-values[1]:,.0f}万\n(120名分自動化)",
            ha="center", va="center", fontsize=10, fontweight="bold", color="white")

    # relation課金
    ax.bar(2, values[2], color=colors[2], alpha=0.85, width=0.5)
    ax.text(2, values[2]/2,
            f"¥{values[2]:,.0f}万/月\n({e['charge_fte_equiv']:.0f}人分)",
            ha="center", va="center", fontsize=11, fontweight="bold", color="white")

    # 顧客手残り
    ax.bar(3, values[3], color=colors[3], alpha=0.85, width=0.5)
    ax.text(3, values[3]/2,
            f"¥{values[3]:,.0f}万/月\n(顧客利益)\nROI {e['customer_roi']:.1f}x",
            ha="center", va="center", fontsize=10, fontweight="bold", color="white")

    ax.set_xticks(range(4))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("月額（万円）", fontsize=11)
    ax.set_title("Enterprise Plus (CS 200名)：お金の流れ", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "fte_waterfall.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_monthly_charge_comparison():
    """全ティアの月額課金比較 + 「3人分」ライン"""
    fig, ax = plt.subplots(figsize=(10, 6))
    tiers = list(TIERS.keys())
    labels = [f"{TIERS[t]['label']}\n(CS {TIERS[t]['cs_reps_typical']}名)" for t in tiers]
    colors = [TIERS[t]["color"] for t in tiers]
    charges = [calc_tier(t)["monthly_charge"] / 10000 for t in tiers]
    fte_equivs = [calc_tier(t)["charge_fte_equiv"] for t in tiers]

    bars = ax.bar(labels, charges, color=colors, alpha=0.85, width=0.5)
    for bar, ch, fte in zip(bars, charges, fte_equivs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(charges)*0.02,
                f"¥{ch:,.0f}万/月\n({fte:.0f}人分)",
                ha="center", fontsize=10, fontweight="bold")

    # 「3人分」ライン（旧モデル最大）
    three_fte = 3 * FTE_MONTHLY / 10000
    ax.axhline(y=three_fte, color="#ef4444", linestyle="--", linewidth=2, alpha=0.8)
    ax.text(len(tiers)-0.5, three_fte + max(charges)*0.015,
            f"← 旧モデル最大 = 3人分 (¥{three_fte:.0f}万)",
            fontsize=10, color="#ef4444", fontweight="bold")

    ax.set_ylabel("月額課金（万円）", fontsize=11)
    ax.set_title("ティア別 月額課金 — 「3人分は安すぎ」を解消", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "monthly_charge_comparison.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_arr_3year():
    """3年ARRロードマップ"""
    fig, ax = plt.subplots(figsize=(10, 6))

    for sc_name, sc in SCENARIOS.items():
        arrs = [calc_scenario(sc_name, yr)["arr"] / 1e8 for yr in range(3)]
        ax.plot([1, 2, 3], arrs, marker="o", linewidth=2.5, markersize=10,
                label=sc["label"], color=sc["color"])
        for yr, v in enumerate(arrs):
            ax.text(yr + 1, v + max(arrs)*0.03,
                    f"¥{v:.0f}億", ha="center", fontsize=10, fontweight="bold",
                    color=sc["color"])

    ax.axhline(y=10, color="#dc2626", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(0.55, 10.5, "¥10億 ARR", fontsize=9, color="#dc2626", fontweight="bold")
    ax.axhline(y=30, color="#7c3aed", linestyle="--", linewidth=1.5, alpha=0.5)
    ax.text(0.55, 31, "¥30億 ARR", fontsize=9, color="#7c3aed", fontweight="bold")
    ax.axhline(y=50, color="#059669", linestyle="--", linewidth=1.5, alpha=0.5)
    ax.text(0.55, 51.5, "¥50億 ARR", fontsize=9, color="#059669", fontweight="bold")

    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("ARR（億円）", fontsize=11)
    ax.set_title("3年ARRロードマップ — FTEベース×プログレッシブ課金", fontsize=14, fontweight="bold")
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["Year 1", "Year 2", "Year 3"])
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "arr_3year.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_arr_composition_yr3():
    """Year 3 ベースケース ARR構成"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

    yr3 = calc_scenario("Base", 2)
    tiers = list(TIERS.keys())

    # 顧客数
    counts = [yr3["seg_detail"][t]["count"] for t in tiers]
    labels = [TIERS[t]["label"] for t in tiers]
    colors = [TIERS[t]["color"] for t in tiers]

    ax1.pie(counts, labels=labels, colors=colors, autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 10})
    ax1.set_title(f"顧客数構成（計 {yr3['customers']}社）", fontsize=12, fontweight="bold")

    # ARR
    arrs = [yr3["seg_detail"][t]["arr"] / 1e8 for t in tiers]
    ax2.pie(arrs, labels=labels, colors=colors, autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 10})
    ax2.set_title(f"ARR構成（計 ¥{yr3['arr']/1e8:.0f}億）", fontsize=12, fontweight="bold")

    fig.suptitle("ベースケース Year 3 — 顧客数の7割はSMBだが、ARRの8割はEnterprise",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "arr_composition_yr3.png")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_customer_perspective():
    """顧客視点: FTE何人分で、何人分の仕事をAIに任せられるか"""
    fig, ax = plt.subplots(figsize=(10, 6))

    tiers = list(TIERS.keys())
    labels = [f"{TIERS[t]['label']}\n(CS {TIERS[t]['cs_reps_typical']}名)" for t in tiers]
    colors = [TIERS[t]["color"] for t in tiers]

    charge_ftes = [calc_tier(t)["charge_fte_equiv"] for t in tiers]
    replaced_ftes = [calc_tier(t)["fte_replaced"] for t in tiers]
    rois = [calc_tier(t)["customer_roi"] for t in tiers]

    x = np.arange(len(tiers))
    width = 0.3

    ax.bar(x - width/2, charge_ftes, width, label="支払い（FTE換算）",
           color=colors, alpha=0.5, edgecolor=colors, linewidth=2)
    ax.bar(x + width/2, replaced_ftes, width, label="AIが代替するFTE数",
           color=colors, alpha=0.85)

    for i in range(len(tiers)):
        ax.text(i - width/2, charge_ftes[i] + 1,
                f"{charge_ftes[i]:.0f}人分\n支払い",
                ha="center", fontsize=8, fontweight="bold")
        ax.text(i + width/2, replaced_ftes[i] + 1,
                f"{replaced_ftes[i]:.0f}人分\n代替",
                ha="center", fontsize=8, fontweight="bold")
        # ROI annotation
        mid_x = i
        mid_y = max(charge_ftes[i], replaced_ftes[i]) + 8
        ax.annotate(f"ROI {rois[i]:.1f}x",
                    xy=(mid_x, mid_y), fontsize=11, fontweight="bold",
                    ha="center", color=colors[i],
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor=colors[i], linewidth=2))

    ax.set_ylabel("FTE数（人分）", fontsize=11)
    ax.set_title("顧客から見た投資対効果：「○人分で○人分の仕事を自動化」", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "customer_perspective.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_sensitivity():
    """感度分析: Value Capture Rate × 顧客数倍率"""
    fig, ax = plt.subplots(figsize=(9, 6))

    # ベースケースYear3のARRを基準に
    base_arr = calc_scenario("Base", 2)["arr"]
    # 課金率の変動（現在20-35%のレンジ → 15-40%に拡張）
    rates_label = ["15%-30%", "20%-35%\n(ベース)", "25%-40%", "30%-45%"]
    rate_multipliers = [0.80, 1.0, 1.20, 1.40]
    cust_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]

    matrix = np.zeros((len(rate_multipliers), len(cust_multipliers)))
    for i, rm in enumerate(rate_multipliers):
        for j, cm in enumerate(cust_multipliers):
            matrix[i][j] = base_arr * rm * cm / 1e8

    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    for i in range(len(rate_multipliers)):
        for j in range(len(cust_multipliers)):
            color = "white" if matrix[i][j] > 30 else "black"
            ax.text(j, i, f"¥{matrix[i][j]:.0f}億", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=color)

    ax.set_xticks(range(len(cust_multipliers)))
    ax.set_xticklabels([f"{cm:.0%}" for cm in cust_multipliers])
    ax.set_yticks(range(len(rate_multipliers)))
    ax.set_yticklabels(rates_label)
    ax.set_xlabel("顧客数（ベース比）", fontsize=11)
    ax.set_ylabel("課金率レンジ", fontsize=11)
    ax.set_title("感度分析：課金率 × 顧客数 → Year 3 ARR", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label="ARR（億円）", shrink=0.8)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "sensitivity.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_why_enterprise_pays_more():
    """なぜエンタープライズは高くても買うのか — 付加価値の可視化"""
    fig, ax = plt.subplots(figsize=(10, 6))

    categories = [
        "FTE代替\n（直接コスト削減）",
        "24/7対応\n（夜間・休日カバー）",
        "品質均一化\n（応対バラつき排除）",
        "即時スケール\n（繁忙期対応）",
        "管理コスト削減\n（教育・採用・離職）",
        "データ・分析\n（改善サイクル加速）",
    ]

    # 各セグメントの付加価値スコア (0-10)
    smb_scores   = [8, 3, 5, 3, 3, 2]
    ent_scores   = [8, 9, 9, 8, 9, 7]

    x = np.arange(len(categories))
    width = 0.3

    ax.barh(x - width/2, smb_scores, width, label="SMB (Growth)",
            color="#22c55e", alpha=0.6)
    ax.barh(x + width/2, ent_scores, width, label="Enterprise Plus",
            color="#dc2626", alpha=0.85)

    ax.set_xlabel("価値の大きさ（10段階）", fontsize=11)
    ax.set_title("なぜ大企業は高くても買うのか — 付加価値が圧倒的に大きい",
                 fontsize=13, fontweight="bold")
    ax.set_yticks(x)
    ax.set_yticklabels(categories, fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(0, 11)
    ax.invert_yaxis()
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "why_enterprise_pays.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


# ===========================================================================
# PDF
# ===========================================================================
def build_styles():
    styles = getSampleStyleSheet()
    defs = [
        ("JP_Title", "IPAPGothic", 26, 34, DARK, TA_CENTER, 20, None),
        ("JP_Subtitle", "IPAPGothic", 13, 20, GRAY, TA_CENTER, 30, None),
        ("JP_H1", "IPAPGothic", 16, 22, BLUE, TA_LEFT, 10, 20),
        ("JP_H2", "IPAPGothic", 13, 18, PURPLE, TA_LEFT, 8, 14),
        ("JP_H3", "IPAPGothic", 11, 15, DARK, TA_LEFT, 6, 10),
        ("JP_Body", "IPAGothic", 9, 15, DARK, TA_JUSTIFY, 6, 0),
        ("JP_Caption", "IPAGothic", 7.5, 10, GRAY, TA_CENTER, 12, 0),
    ]
    for name, font, size, lead, color, align, after, before in defs:
        styles.add(ParagraphStyle(name, fontName=font, fontSize=size, leading=lead,
                                  textColor=color, alignment=align, spaceAfter=after,
                                  spaceBefore=before or 0))
    styles.add(ParagraphStyle(
        "JP_Highlight", fontName="IPAPGothic", fontSize=10, leading=15,
        textColor=GREEN, spaceBefore=8, spaceAfter=8, alignment=TA_CENTER,
        borderWidth=1, borderColor=GREEN, borderPadding=8,
        backColor=HexColor("#ecfdf5")))
    styles.add(ParagraphStyle(
        "JP_Alert", fontName="IPAPGothic", fontSize=10, leading=15,
        textColor=RED, spaceBefore=8, spaceAfter=8, alignment=TA_CENTER,
        borderWidth=1, borderColor=RED, borderPadding=8,
        backColor=HexColor("#fef2f2")))
    return styles


def make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "IPAGothic"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, 0), TBL_HDR),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "IPAPGothic"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), TBL_ALT))
    t.setStyle(TableStyle(cmds))
    return t


def divider():
    t = Table([[""]], colWidths=[170*mm])
    t.setStyle(TableStyle([("LINEABOVE", (0,0), (-1,0), 2, BLUE),
                           ("TOPPADDING", (0,0), (-1,-1), 0),
                           ("BOTTOMPADDING", (0,0), (-1,-1), 0)]))
    return t


def generate_pdf():
    setup_mpl()
    styles = build_styles()

    print("チャート生成中...")
    charts = {
        "progressive": chart_progressive_pricing(),
        "waterfall": chart_fte_waterfall(),
        "charge_cmp": chart_monthly_charge_comparison(),
        "arr_3y": chart_arr_3year(),
        "arr_comp": chart_arr_composition_yr3(),
        "cust_persp": chart_customer_perspective(),
        "sensitivity": chart_sensitivity(),
        "why_ent": chart_why_enterprise_pays_more(),
    }
    print("チャート生成完了")

    doc = SimpleDocTemplate(PDF_PATH, pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    story = []

    # === 表紙 ===
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("relation AI", styles["JP_Title"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("FTEベース × プログレッシブ課金モデル", styles["JP_Title"]))
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph("— エンタープライズほど高くなる設計で数十億ARRへ —", styles["JP_Subtitle"]))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(
        "「3人分の人件費？ 安い安い」<br/>"
        "→ なら20人分、50人分を堂々と課金する", styles["JP_Subtitle"]))
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph("ingAge Inc.  |  2026年3月  |  Confidential", styles["JP_Caption"]))
    story.append(PageBreak())

    # === 目次 ===
    story.append(Paragraph("目次", styles["JP_H1"]))
    story.append(divider())
    toc = [
        "1. 前回モデルの何が問題だったか",
        "2. FTEベース × プログレッシブ課金の設計思想",
        "3. ティア別 経済構造（全数値）",
        "4. なぜ大企業は高くても買うのか",
        "5. 顧客視点：「○人分で○人分の仕事を自動化」",
        "6. 新クレジットプラン設計",
        "7. 3年ARRロードマップ",
        "8. Year 3 ARR構成分析",
        "9. 感度分析",
        "10. 数十億ARRへの道筋と必要アクション",
    ]
    for item in toc:
        story.append(Paragraph(f"　{item}", styles["JP_Body"]))
    story.append(PageBreak())

    # === 1. 前回モデルの問題 ===
    story.append(Paragraph("1. 前回モデルの何が問題だったか", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "前回のROIベースモデル（V2）は方向性は正しかったが、2つの大きな問題がありました。",
        styles["JP_Body"]))

    story.append(Paragraph("<b>問題1：「全部門の業務自動化プラットフォーム」は差別化にならない</b>", styles["JP_H3"]))
    story.append(Paragraph(
        "2025〜2026年、あらゆるAIスタートアップが「全部門のAI化」を謳っています。"
        "relationの強みは <b>CS/顧客コミュニケーション領域</b> です。"
        "この領域で深く刺し、No.1ポジションを取ることが先決。"
        "横展開は後からでもできるが、ポジショニングが曖昧なまま広げると負けます。",
        styles["JP_Body"]))

    story.append(Paragraph("<b>問題2：大企業への課金が安すぎた</b>", styles["JP_H3"]))
    e_xl = calc_tier("XL")
    story.append(Paragraph(
        f"大企業（CS 200名）にとって「3人分の人件費 = 月¥{3*FTE_MONTHLY/10000:.0f}万」は<b>端数</b>です。"
        f"稟議すら不要なレベル。もっと取れる。実際、AI導入で <b>{e_xl['fte_replaced']:.0f}名分</b> "
        f"の業務が自動化されるなら、<b>{e_xl['charge_fte_equiv']:.0f}人分 "
        f"(¥{e_xl['monthly_charge']/10000:,.0f}万/月)</b> を課金しても安い。",
        styles["JP_Body"]))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "解決策：<b>エンタープライズほど課金率を上げる「プログレッシブ課金」</b><br/>"
        "CS/コミュニケーション特化で深く刺し、企業規模に応じて堂々と高く取る",
        styles["JP_Alert"]))
    story.append(PageBreak())

    # === 2. 設計思想 ===
    story.append(Paragraph("2. FTEベース × プログレッシブ課金の設計思想", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>原則：企業規模が大きいほど Value Capture Rate を上げる</b>", styles["JP_H2"]))
    story.append(Spacer(1, 2*mm))

    story.append(Image(charts["progressive"], width=170*mm, height=80*mm))
    story.append(Paragraph("図1: プログレッシブ課金構造 — 企業規模に応じて課金率UP", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>なぜプログレッシブが合理的か</b>", styles["JP_H3"]))
    reasons = [
        "• <b>大企業のAI付加価値は中小の数倍</b>：24/7対応、品質均一化、即時スケール、管理コスト削減",
        "• <b>大企業の価格感度は低い</b>：年間数百億の人件費に対し、数億の投資は「端数」",
        "• <b>大企業の稟議は「ROI」で通る</b>：ROI 1.8倍でも十分。3倍以上なら余裕",
        "• <b>大企業のスイッチングコストが高い</b>：一度導入すれば長期契約。LTV/CACが極めて高い",
    ]
    for r in reasons:
        story.append(Paragraph(r, styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    prog_table = [
        ["ティア", "CS規模", "課金率", "FTE換算\n課金", "代替FTE", "顧客ROI", "考え方"],
        ["Growth", "5〜15名", "20%", f"{calc_tier('S')['charge_fte_equiv']:.0f}人分",
         f"{calc_tier('S')['fte_replaced']:.0f}人分", f"{calc_tier('S')['customer_roi']:.1f}x",
         "導入障壁を低く"],
        ["Scale", "15〜40名", "25%", f"{calc_tier('M')['charge_fte_equiv']:.0f}人分",
         f"{calc_tier('M')['fte_replaced']:.0f}人分", f"{calc_tier('M')['customer_roi']:.1f}x",
         "成長企業の標準"],
        ["Enterprise", "40〜120名", "30%", f"{calc_tier('L')['charge_fte_equiv']:.0f}人分",
         f"{calc_tier('L')['fte_replaced']:.0f}人分", f"{calc_tier('L')['customer_roi']:.1f}x",
         "付加価値を反映"],
        ["Enterprise Plus", "120〜400名", "35%", f"{calc_tier('XL')['charge_fte_equiv']:.0f}人分",
         f"{calc_tier('XL')['fte_replaced']:.0f}人分", f"{calc_tier('XL')['customer_roi']:.1f}x",
         "フルバリュー課金"],
    ]
    story.append(make_table(prog_table, col_widths=[22*mm, 18*mm, 16*mm, 18*mm, 18*mm, 16*mm, 30*mm]))
    story.append(PageBreak())

    # === 3. ティア別経済構造 ===
    story.append(Paragraph("3. ティア別 経済構造（全数値）", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["charge_cmp"], width=165*mm, height=100*mm))
    story.append(Paragraph(
        "図2: ティア別月額課金 — 旧モデル「3人分」ラインとの比較", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    econ_header = ["", "Growth", "Scale", "Enterprise", "Ent. Plus"]
    econ_data = [econ_header]
    tier_keys = ["S", "M", "L", "XL"]
    econ_rows = [
        ("CS担当者数", [f'{TIERS[t]["cs_reps_typical"]}名' for t in tier_keys]),
        ("月間人件費", [f'¥{calc_tier(t)["monthly_labor"]/10000:,.0f}万' for t in tier_keys]),
        ("AI自動化率", [f'{TIERS[t]["ai_automation_rate"]:.0%}' for t in tier_keys]),
        ("代替FTE数", [f'{calc_tier(t)["fte_replaced"]:.0f}名分' for t in tier_keys]),
        ("削減可能額/月", [f'¥{calc_tier(t)["monthly_savings"]/10000:,.0f}万' for t in tier_keys]),
        ("課金率", [f'{TIERS[t]["value_capture_rate"]:.0%}' for t in tier_keys]),
        ("月額課金", [f'¥{calc_tier(t)["monthly_charge"]/10000:,.0f}万' for t in tier_keys]),
        ("FTE換算", [f'{calc_tier(t)["charge_fte_equiv"]:.0f}人分' for t in tier_keys]),
        ("年間課金", [f'¥{calc_tier(t)["annual_charge"]/10000:,.0f}万' for t in tier_keys]),
        ("顧客手残り/月", [f'¥{calc_tier(t)["customer_keeps"]/10000:,.0f}万' for t in tier_keys]),
        ("顧客ROI", [f'{calc_tier(t)["customer_roi"]:.1f}x' for t in tier_keys]),
        ("AI原価/月", [f'¥{calc_tier(t)["monthly_ai_cost"]/10000:,.1f}万' for t in tier_keys]),
        ("粗利率", [f'{calc_tier(t)["gross_margin"]:.1f}%' for t in tier_keys]),
    ]
    for label, vals in econ_rows:
        econ_data.append([label] + vals)
    story.append(make_table(econ_data, col_widths=[26*mm, 30*mm, 30*mm, 30*mm, 30*mm]))
    story.append(Spacer(1, 3*mm))

    e_l = calc_tier("L")
    story.append(Paragraph(
        f"Enterprise（CS 70名）：月額 <b>¥{e_l['monthly_charge']/10000:,.0f}万</b>"
        f"（{e_l['charge_fte_equiv']:.0f}人分）で {e_l['fte_replaced']:.0f}人分の仕事を自動化。"
        f"年間 <b>¥{e_l['annual_charge']/10000:,.0f}万</b>。粗利率 <b>{e_l['gross_margin']:.1f}%</b>。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # === Enterprise Plusウォーターフォール ===
    story.append(Paragraph("Enterprise Plus：お金の流れ", styles["JP_H2"]))
    story.append(Spacer(1, 2*mm))
    story.append(Image(charts["waterfall"], width=165*mm, height=100*mm))
    story.append(Paragraph(
        "図3: Enterprise Plus (CS 200名) のお金の流れ — 42人分の課金で120人分を自動化", styles["JP_Caption"]))
    story.append(PageBreak())

    # === 4. なぜ大企業は高くても買うのか ===
    story.append(Paragraph("4. なぜ大企業は高くても買うのか", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["why_ent"], width=165*mm, height=100*mm))
    story.append(Paragraph(
        "図4: 大企業にとってのAI導入価値 — FTE代替以外の付加価値が圧倒的", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "SMBにとってAI導入は「コスト削減ツール」。"
        "だから安くないと買わない（課金率20%が妥当）。",
        styles["JP_Body"]))
    story.append(Paragraph(
        "大企業にとってAI導入は <b>「事業変革のインフラ」</b>。"
        "以下の付加価値が加わるから、課金率35%でも「安い」と感じる：",
        styles["JP_Body"]))

    values = [
        "• <b>24/7/365対応</b>：夜間・休日もAIが対応。人間だとシフト3交代制が必要（＋2〜3倍の人件費）",
        "• <b>品質の完全均一化</b>：新人もベテランもAIが書けば同品質。教育コスト＆品質事故リスクを排除",
        "• <b>即時スケーラビリティ</b>：ブラックフライデー、障害発生時にAIは自動スケール。人間は採用に3ヶ月",
        "• <b>管理コスト削減</b>：採用・研修・評価・離職対応。CS 200名の管理コストは年間数億。AIなら不要",
        "• <b>多言語即時対応</b>：海外展開企業にとって、多言語CSチーム構築は年単位。AIなら即日",
        "• <b>データドリブン改善</b>：全対応データが構造化。CS品質のPDCA速度が10倍に",
    ]
    for v in values:
        story.append(Paragraph(v, styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "これらを総合すると、FTE代替だけで計算した価値の <b>2〜3倍</b> の価値がある。"
        "課金率35%は、真の価値の <b>12〜17%</b> に過ぎない。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # === 5. 顧客視点 ===
    story.append(Paragraph("5. 顧客視点：「○人分で○人分の仕事を自動化」", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "営業トークのコアメッセージ。技術的な話（トークン、モデル）は一切不要。"
        "FTE換算だけで伝える。",
        styles["JP_Body"]))

    story.append(Image(charts["cust_persp"], width=165*mm, height=100*mm))
    story.append(Paragraph(
        "図5: 顧客から見た投資対効果 — すべてのティアでROI 1.8〜4倍", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    pitch_table = [
        ["ティア", "営業トーク（ワンライナー）"],
        ["Growth\n(CS 10名)", f"「たった{calc_tier('S')['charge_fte_equiv']:.0f}人分のコストで"
         f"、CS {calc_tier('S')['fte_replaced']:.0f}名分の仕事をAIが24/7で処理します」"],
        ["Scale\n(CS 25名)", f"「{calc_tier('M')['charge_fte_equiv']:.0f}人分のコストで"
         f"、CS {calc_tier('M')['fte_replaced']:.0f}名分を自動化。"
         f"毎月¥{calc_tier('M')['customer_keeps']/10000:,.0f}万の削減効果です」"],
        ["Enterprise\n(CS 70名)", f"「{calc_tier('L')['charge_fte_equiv']:.0f}人分のコストで"
         f"、CS {calc_tier('L')['fte_replaced']:.0f}名分を自動化。"
         f"年間¥{calc_tier('L')['customer_keeps']*12/10000:,.0f}万のインパクトです」"],
        ["Ent. Plus\n(CS 200名)", f"「{calc_tier('XL')['charge_fte_equiv']:.0f}人分のコストで"
         f"、CS {calc_tier('XL')['fte_replaced']:.0f}名分を自動化。"
         f"年間¥{calc_tier('XL')['customer_keeps']*12/1e8:.1f}億のインパクトです」"],
    ]
    story.append(make_table(pitch_table, col_widths=[24*mm, 126*mm]))
    story.append(PageBreak())

    # === 6. クレジットプラン ===
    story.append(Paragraph("6. 新クレジットプラン設計", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "FTEベース課金の内部実装としてクレジット制を使います。"
        "顧客への説明は「FTE換算」、裏側のリソース管理は「クレジット」。",
        styles["JP_Body"]))

    plan_hdr = ["", "Growth", "Scale", "Enterprise", "Ent. Plus"]
    plan_rows = [plan_hdr]

    plan_items = [
        ("月額", [f'¥{CREDIT_PLANS[p]["monthly_fee"]:,}' for p in CREDIT_PLANS]),
        ("FTE換算", [f'{CREDIT_PLANS[p]["monthly_fee_fte"]:.0f}人分' for p in CREDIT_PLANS]),
        ("含有cr/月", [f'{CREDIT_PLANS[p]["included_credits"]:,}' for p in CREDIT_PLANS]),
        ("超過単価", [f'¥{CREDIT_PLANS[p]["extra_credit_price"]}' for p in CREDIT_PLANS]),
        ("主要機能", [CREDIT_PLANS[p]["features"] for p in CREDIT_PLANS]),
        ("サポート", [CREDIT_PLANS[p]["support"] for p in CREDIT_PLANS]),
    ]
    for label, vals in plan_items:
        plan_rows.append([label] + vals)
    story.append(make_table(plan_rows, col_widths=[20*mm, 32*mm, 32*mm, 32*mm, 32*mm]))
    story.append(PageBreak())

    # === 7. 3年ARR ===
    story.append(Paragraph("7. 3年ARRロードマップ", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["arr_3y"], width=165*mm, height=100*mm))
    story.append(Paragraph("図6: 3年ARRロードマップ", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    arr_hdr = ["シナリオ", "Year 1", "Year 2", "Year 3", "Year 3\n顧客数", "Year 3\nMRR"]
    arr_rows = [arr_hdr]
    for sc_name in SCENARIOS:
        data_by_yr = [calc_scenario(sc_name, yr) for yr in range(3)]
        arr_rows.append([
            SCENARIOS[sc_name]["label"],
            f'¥{data_by_yr[0]["arr"]/1e8:.0f}億',
            f'¥{data_by_yr[1]["arr"]/1e8:.0f}億',
            f'¥{data_by_yr[2]["arr"]/1e8:.0f}億',
            f'{data_by_yr[2]["customers"]}社',
            f'¥{data_by_yr[2]["mrr"]/1e8:.1f}億/月',
        ])
    story.append(make_table(arr_rows, col_widths=[24*mm, 24*mm, 24*mm, 24*mm, 22*mm, 26*mm]))
    story.append(Spacer(1, 3*mm))

    base_yr3 = calc_scenario("Base", 2)
    agg_yr3 = calc_scenario("Aggressive", 2)
    story.append(Paragraph(
        f"ベースケース Year 3: <b>¥{base_yr3['arr']/1e8:.0f}億 ARR</b>（{base_yr3['customers']}社）<br/>"
        f"攻めシナリオ Year 3: <b>¥{agg_yr3['arr']/1e8:.0f}億 ARR</b>（{agg_yr3['customers']}社）",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # === 8. Year 3 ARR構成 ===
    story.append(Paragraph("8. Year 3 ARR構成分析（ベースケース）", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["arr_comp"], width=165*mm, height=80*mm))
    story.append(Paragraph("図7: 顧客数の7割はSMBだが、ARRの8割はEnterprise", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    # ARR内訳テーブル
    comp_hdr = ["ティア", "顧客数", "構成比", "1社ARR", "セグメントARR", "構成比"]
    comp_rows = [comp_hdr]
    for tier in ["S", "M", "L", "XL"]:
        d = base_yr3["seg_detail"][tier]
        e = calc_tier(tier)
        pct_cust = d["count"] / base_yr3["customers"] * 100 if base_yr3["customers"] > 0 else 0
        pct_arr = d["arr"] / base_yr3["arr"] * 100 if base_yr3["arr"] > 0 else 0
        comp_rows.append([
            TIERS[tier]["label"],
            f'{d["count"]}社', f'{pct_cust:.0f}%',
            f'¥{e["annual_charge"]/10000:,.0f}万',
            f'¥{d["arr"]/1e8:.1f}億', f'{pct_arr:.0f}%',
        ])
    comp_rows.append([
        "合計", f'{base_yr3["customers"]}社', "100%", "—",
        f'¥{base_yr3["arr"]/1e8:.0f}億', "100%"
    ])
    story.append(make_table(comp_rows, col_widths=[24*mm, 18*mm, 18*mm, 26*mm, 26*mm, 18*mm]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "教訓：<b>顧客数を追うな。Enterprise・Enterprise Plusの獲得に全リソースを集中せよ。</b>"
        "SMBは低コストのセルフサーブで効率的に獲得。",
        styles["JP_Alert"]))
    story.append(PageBreak())

    # === 9. 感度分析 ===
    story.append(Paragraph("9. 感度分析", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["sensitivity"], width=155*mm, height=100*mm))
    story.append(Paragraph("図8: 感度分析ヒートマップ — ¥10億超の経路が多数", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "課金率を現行から20%下げても、顧客数が75%に留まっても、<b>¥13億 ARR</b> は確保できる。"
        "逆に課金率を上げて顧客数が伸びれば <b>¥50億超</b> も射程圏内。"
        "¥10億ARRは「達成できるか」ではなく「いつ達成するか」の問題。",
        styles["JP_Body"]))
    story.append(PageBreak())

    # === 10. 結論 ===
    story.append(Paragraph("10. 数十億ARRへの道筋と必要アクション", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        f"ベースケース Year 3: <b>¥{base_yr3['arr']/1e8:.0f}億 ARR</b>　|　"
        f"攻め Year 3: <b>¥{agg_yr3['arr']/1e8:.0f}億 ARR</b>",
        styles["JP_Highlight"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>なぜこのモデルで数十億に届くのか — 3つの構造的理由</b>", styles["JP_H2"]))
    structural = [
        "1. <b>プログレッシブ課金</b>：大企業ほど課金率が高い → エンタープライズ1社で年間¥数億。"
        "数社取るだけでARRが一気に積み上がる",
        "",
        "2. <b>FTEベースの価格説明</b>：「トークン」「クレジット」ではなく「○人分」。"
        "経営者が即座に理解でき、稟議が通る。人件費の20〜35%は「安い」",
        "",
        "3. <b>CS/コミュニケーション特化</b>：全部門プラットフォームではなく、"
        "CS領域で圧倒的No.1を取る。深い専門性が競合参入障壁になり、価格維持力につながる",
    ]
    for s in structural:
        story.append(Paragraph(s, styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>今すぐやるべき5つのアクション</b>", styles["JP_H2"]))
    actions = [
        "1. <b>Enterprise営業チームを最優先で構築</b>（3〜5名）："
        "ARRの8割はEnterprise以上から。SMBはセルフサーブ。営業リソースは100%上位に集中",
        "",
        "2. <b>PoC 5社を即座に開始</b>："
        f"CS 50名以上の企業5社でPoCを実施。月額¥{calc_tier('L')['monthly_charge']/10000:,.0f}万の"
        "価格感をバリデーション。ROI 2倍以上を実証する",
        "",
        "3. <b>「FTE換算」の営業資料を整備</b>："
        "技術資料ではなく「○人分で○人分自動化」のROIシミュレーター。"
        "顧客のCS人数を入れるだけで即座に見積もりが出るツール",
        "",
        "4. <b>ROI保証プログラム</b>："
        "「3ヶ月でROI 2倍未満なら全額返金」。実際のROIは2〜4倍なのでリスクは小さい。"
        "これで稟議突破率が劇的に上がる",
        "",
        "5. <b>Year 2以降のエージェント型課金を設計開始</b>："
        "単一操作のクレジットに加え、「問い合わせ→調査→回答→ナレッジ化」を"
        "一気通貫で完結するAIエージェント（¥500〜¥5,000/タスク）。ARPU倍増の次の一手",
    ]
    for a in actions:
        story.append(Paragraph(a, styles["JP_Body"]))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("— End of Report —", styles["JP_Caption"]))

    print("PDF生成中...")
    doc.build(story)
    print(f"PDF生成完了: {PDF_PATH}")


if __name__ == "__main__":
    generate_pdf()
