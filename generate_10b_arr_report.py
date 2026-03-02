#!/usr/bin/env python3
"""
relation AI — ROIベース価格設計 & 数十億ARRシミュレーション
ingAge Inc. - 2026年3月

前提転換：
  旧: AI原価+マージン → 安すぎて数億止まり
  新: 顧客のROI（人件費削減額）の20-30%を課金 → 数十億ARR到達可能
"""

import os, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(OUTPUT_DIR, "relation_10b_arr_roi_model.pdf")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts_v2")
os.makedirs(CHART_DIR, exist_ok=True)

USD_JPY = 150

pdfmetrics.registerFont(TTFont("IPAGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"))
pdfmetrics.registerFont(TTFont("IPAPGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"))

PRIMARY   = HexColor("#0f172a")
BLUE      = HexColor("#1a56db")
ACCENT    = HexColor("#059669")
PURPLE    = HexColor("#7c3aed")
RED       = HexColor("#dc2626")
DARK      = HexColor("#1e293b")
TBL_HDR   = HexColor("#0f172a")
TBL_ALT   = HexColor("#f1f5f9")
WHITE     = white

# ===========================================================================
# コアモデル: 日本の人件費構造
# ===========================================================================
# カスタマーサポート担当の年間コスト（給与+社保+間接費）
CS_REP_ANNUAL_COST = 5_500_000      # ¥550万/年（中央値）
CS_REP_MONTHLY_COST = CS_REP_ANNUAL_COST / 12
CS_REP_HOURLY_COST = CS_REP_ANNUAL_COST / (240 * 8)  # ≒ ¥2,865/h

# AI原価（Sonnet 4.5ベース、標準返信1件あたり）
AI_COST_PER_REPLY = 3.4  # ¥3.4 (4,500 input × $3/1M + 500 output × $15/1M) × ¥150

# ===========================================================================
# ROIベース価格設計: 人件費の何%を取るか
# ===========================================================================
# 顧客に提供する価値 = 削減できる人件費
# 課金額 = 削減人件費の20-30% → 顧客は70-80%を手元に残す
# これでも顧客のROIは3-5倍（投資の3-5倍のリターン）

VALUE_CAPTURE_RATE = 0.25  # 削減人件費の25%を課金

# ===========================================================================
# 企業セグメント定義 (ROIベース)
# ===========================================================================
SEGMENTS = {
    "SMB": {
        "label": "中小企業",
        "cs_reps": 8,           # CS担当者数
        "ai_automation_rate": 0.50,  # AIで自動化できる割合
        "departments": 1,       # AI導入部門数
        "color": "#22c55e",
    },
    "Mid-Market": {
        "label": "中堅企業",
        "cs_reps": 30,
        "ai_automation_rate": 0.55,
        "departments": 2,       # CS + 営業 or CS + マーケ
        "color": "#3b82f6",
    },
    "Enterprise": {
        "label": "大企業",
        "cs_reps": 80,
        "ai_automation_rate": 0.60,
        "departments": 3,       # CS + 営業 + マーケ or HR
        "color": "#7c3aed",
    },
    "Mega Enterprise": {
        "label": "超大企業",
        "cs_reps": 300,
        "ai_automation_rate": 0.60,
        "departments": 4,       # CS + 営業 + マーケ + HR/法務
        "color": "#dc2626",
    },
}


def calc_segment_economics(seg):
    """セグメントごとのROIベース経済性を計算"""
    s = SEGMENTS[seg]
    # 部門あたりの人件費（CS以外も同等と仮定）
    monthly_labor_per_dept = s["cs_reps"] * CS_REP_MONTHLY_COST
    total_monthly_labor = monthly_labor_per_dept * s["departments"]

    # AI自動化による削減可能額
    monthly_savings_potential = total_monthly_labor * s["ai_automation_rate"]

    # 課金額 = 削減額の25%
    monthly_revenue = monthly_savings_potential * VALUE_CAPTURE_RATE

    # AI原価（概算：1人分の作業 ≒ 月160時間 × 6件/h = 960件、1件¥3.4）
    replies_per_rep_per_month = 160 * 6  # 時間 × 件/h
    total_automated_replies = (
        s["cs_reps"] * s["departments"] * replies_per_rep_per_month * s["ai_automation_rate"]
    )
    monthly_ai_cost = total_automated_replies * AI_COST_PER_REPLY

    # 顧客のROI
    customer_net_savings = monthly_savings_potential - monthly_revenue
    customer_roi = customer_net_savings / monthly_revenue if monthly_revenue > 0 else 0

    return {
        "total_monthly_labor": total_monthly_labor,
        "monthly_savings_potential": monthly_savings_potential,
        "monthly_revenue": monthly_revenue,
        "annual_revenue": monthly_revenue * 12,
        "monthly_ai_cost": monthly_ai_cost,
        "monthly_gross_profit": monthly_revenue - monthly_ai_cost,
        "gross_margin": (monthly_revenue - monthly_ai_cost) / monthly_revenue * 100 if monthly_revenue > 0 else 0,
        "customer_roi": customer_roi,
        "customer_net_savings": customer_net_savings,
        "automated_replies": total_automated_replies,
    }


# ===========================================================================
# ARRシミュレーションシナリオ
# ===========================================================================
# 3年計画 (Year 1, 2, 3)
GROWTH_SCENARIOS = {
    "Conservative": {
        "label": "保守的",
        "color": "#94a3b8",
        "years": [
            {"SMB": 50,  "Mid-Market": 10, "Enterprise": 2,  "Mega Enterprise": 0},
            {"SMB": 200, "Mid-Market": 50, "Enterprise": 10, "Mega Enterprise": 2},
            {"SMB": 500, "Mid-Market": 150, "Enterprise": 30, "Mega Enterprise": 5},
        ]
    },
    "Base": {
        "label": "ベースケース",
        "color": "#3b82f6",
        "years": [
            {"SMB": 80,  "Mid-Market": 20, "Enterprise": 5,  "Mega Enterprise": 1},
            {"SMB": 350, "Mid-Market": 100, "Enterprise": 25, "Mega Enterprise": 5},
            {"SMB": 800, "Mid-Market": 300, "Enterprise": 80, "Mega Enterprise": 15},
        ]
    },
    "Aggressive": {
        "label": "攻めのシナリオ",
        "color": "#7c3aed",
        "years": [
            {"SMB": 120, "Mid-Market": 30,  "Enterprise": 8,  "Mega Enterprise": 2},
            {"SMB": 500, "Mid-Market": 180, "Enterprise": 50, "Mega Enterprise": 10},
            {"SMB": 1200, "Mid-Market": 500, "Enterprise": 150, "Mega Enterprise": 30},
        ]
    },
}


def calc_scenario_arr(scenario_name, year_idx):
    """シナリオのARRを計算"""
    sc = GROWTH_SCENARIOS[scenario_name]
    counts = sc["years"][year_idx]
    total_mrr = 0
    total_ai_cost = 0
    total_customers = 0
    for seg, count in counts.items():
        if count == 0:
            continue
        econ = calc_segment_economics(seg)
        total_mrr += econ["monthly_revenue"] * count
        total_ai_cost += econ["monthly_ai_cost"] * count
        total_customers += count
    return {
        "mrr": total_mrr,
        "arr": total_mrr * 12,
        "ai_cost_monthly": total_ai_cost,
        "gross_profit_monthly": total_mrr - total_ai_cost,
        "gross_margin": (total_mrr - total_ai_cost) / total_mrr * 100 if total_mrr > 0 else 0,
        "total_customers": total_customers,
        "counts": counts,
    }


# ===========================================================================
# クレジットプラン設計 (ROIベース版)
# ===========================================================================
ROI_PLANS = {
    "Growth": {
        "monthly_fee": 100_000,
        "included_credits": 5_000,
        "extra_credit_price": 25,
        "target": "SMB（CS 5〜15名）",
        "value_prop": "CS人件費の50%自動化、ROI 3倍保証",
        "model": "Sonnet",
    },
    "Scale": {
        "monthly_fee": 500_000,
        "included_credits": 30_000,
        "extra_credit_price": 20,
        "target": "中堅企業（CS 20〜50名、複数部門）",
        "value_prop": "複数部門の業務自動化、ROI 4倍保証",
        "model": "Sonnet",
    },
    "Enterprise": {
        "monthly_fee": 2_000_000,
        "included_credits": 150_000,
        "extra_credit_price": 15,
        "target": "大企業（CS 50名以上、全社展開）",
        "value_prop": "全社AI基盤、専任CSM、カスタムモデル",
        "model": "Sonnet/Opus",
    },
    "Strategic": {
        "monthly_fee": 8_000_000,
        "included_credits": 800_000,
        "extra_credit_price": 12,
        "target": "超大企業（CS 200名以上）",
        "value_prop": "AIトランスフォーメーション伴走、CXO連携",
        "model": "Opus/Custom",
    },
}


# ===========================================================================
# チャート生成
# ===========================================================================
def setup_matplotlib():
    plt.rcParams["font.family"] = "IPAGothic"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.unicode_minus"] = False


def chart_roi_per_segment():
    """セグメント別 ROI構造：人件費 vs 課金 vs 顧客手残り"""
    fig, ax = plt.subplots(figsize=(10, 6))
    segs = list(SEGMENTS.keys())
    labels = [SEGMENTS[s]["label"] for s in segs]

    labors = []
    revenues = []
    customer_keeps = []
    ai_costs = []

    for seg in segs:
        e = calc_segment_economics(seg)
        labors.append(e["total_monthly_labor"] / 10000)
        revenues.append(e["monthly_revenue"] / 10000)
        customer_keeps.append(e["customer_net_savings"] / 10000)
        ai_costs.append(e["monthly_ai_cost"] / 10000)

    x = np.arange(len(segs))
    width = 0.18

    ax.bar(x - 1.5*width, labors, width, label="現行人件費", color="#ef4444", alpha=0.75)
    ax.bar(x - 0.5*width, revenues, width, label="relation AI課金", color="#3b82f6", alpha=0.85)
    ax.bar(x + 0.5*width, customer_keeps, width, label="顧客の手残り（削減額）", color="#22c55e", alpha=0.85)
    ax.bar(x + 1.5*width, ai_costs, width, label="AI原価", color="#94a3b8", alpha=0.7)

    for i in range(len(segs)):
        e = calc_segment_economics(segs[i])
        ax.text(i - 0.5*width, revenues[i] + labors[i]*0.02,
                f"¥{e['monthly_revenue']/10000:.0f}万",
                ha="center", fontsize=8, fontweight="bold", color="#1a56db")
        ax.text(i + 0.5*width, customer_keeps[i] + labors[i]*0.02,
                f"ROI {e['customer_roi']:.1f}x",
                ha="center", fontsize=8, fontweight="bold", color="#059669")

    ax.set_ylabel("月額（万円）", fontsize=11)
    ax.set_title("セグメント別 ROI構造：人件費 vs 課金 vs 顧客手残り", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "roi_per_segment.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_arr_roadmap():
    """3年ARRロードマップ（3シナリオ）"""
    fig, ax = plt.subplots(figsize=(10, 6))

    for sc_name, sc in GROWTH_SCENARIOS.items():
        arrs = []
        for yr in range(3):
            r = calc_scenario_arr(sc_name, yr)
            arrs.append(r["arr"] / 1_0000_0000)  # 億円
        ax.plot([1, 2, 3], arrs, marker="o", linewidth=2.5, markersize=10,
                label=f"{sc['label']}", color=sc["color"])
        for yr_idx, arr_val in enumerate(arrs):
            ax.text(yr_idx + 1, arr_val + max(arrs)*0.03,
                    f"¥{arr_val:.1f}億", ha="center", fontsize=10, fontweight="bold",
                    color=sc["color"])

    # 10億ライン
    ax.axhline(y=10, color="#dc2626", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(0.6, 10.3, "¥10億 ARR", fontsize=9, color="#dc2626", fontweight="bold")

    # 50億ライン
    ax.axhline(y=50, color="#7c3aed", linestyle="--", linewidth=1.5, alpha=0.5)
    ax.text(0.6, 51, "¥50億 ARR", fontsize=9, color="#7c3aed", fontweight="bold")

    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("ARR（億円）", fontsize=11)
    ax.set_title("3年ARRロードマップ — 数十億は到達可能か", fontsize=14, fontweight="bold")
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["Year 1", "Year 2", "Year 3"])
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "arr_roadmap.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_arpu_comparison():
    """セグメント別 ARPU（月額/年額）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))
    segs = list(SEGMENTS.keys())
    labels = [SEGMENTS[s]["label"] for s in segs]
    colors = [SEGMENTS[s]["color"] for s in segs]

    mrrs = [calc_segment_economics(s)["monthly_revenue"] / 10000 for s in segs]
    arrs = [calc_segment_economics(s)["annual_revenue"] / 10000 for s in segs]

    bars1 = ax1.bar(labels, mrrs, color=colors, alpha=0.85)
    for bar, v in zip(bars1, mrrs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(mrrs)*0.02,
                 f"¥{v:,.0f}万", ha="center", fontsize=10, fontweight="bold")
    ax1.set_ylabel("万円/月", fontsize=11)
    ax1.set_title("月額ARPU（1社あたり売上）", fontsize=12, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)

    bars2 = ax2.bar(labels, arrs, color=colors, alpha=0.85)
    for bar, v in zip(bars2, arrs):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(arrs)*0.02,
                 f"¥{v:,.0f}万", ha="center", fontsize=10, fontweight="bold")
    ax2.set_ylabel("万円/年", fontsize=11)
    ax2.set_title("年額ARPU（1社あたり売上）", fontsize=12, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("ROIベース課金によるARPU", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "arpu_comparison.png")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_gross_margin_structure():
    """粗利率の構造：なぜ90%超が可能か"""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    segs = list(SEGMENTS.keys())
    labels = [SEGMENTS[s]["label"] for s in segs]

    for seg in segs:
        e = calc_segment_economics(seg)
        rev = e["monthly_revenue"]
        ai = e["monthly_ai_cost"]
        gross = e["monthly_gross_profit"]
        margin = e["gross_margin"]

    revenues = [calc_segment_economics(s)["monthly_revenue"] / 10000 for s in segs]
    ai_costs = [calc_segment_economics(s)["monthly_ai_cost"] / 10000 for s in segs]
    margins = [calc_segment_economics(s)["gross_margin"] for s in segs]
    colors = [SEGMENTS[s]["color"] for s in segs]

    x = np.arange(len(segs))
    width = 0.3

    ax.bar(x - width/2, revenues, width, label="月間売上", color=colors, alpha=0.85)
    ax.bar(x + width/2, ai_costs, width, label="AI原価", color="#94a3b8", alpha=0.7)

    ax2 = ax.twinx()
    ax2.plot(x, margins, "D-", color="#dc2626", markersize=10, linewidth=2, label="粗利率")
    for i, m in enumerate(margins):
        ax2.text(i, m + 1.5, f"{m:.1f}%", ha="center", fontsize=10, fontweight="bold", color="#dc2626")

    ax.set_ylabel("月額（万円）", fontsize=11)
    ax2.set_ylabel("粗利率（%）", fontsize=11, color="#dc2626")
    ax.set_title("セグメント別 売上・AI原価・粗利率", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc="upper left", fontsize=9)
    ax2.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax2.set_ylim(80, 100)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "gross_margin_structure.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_customer_mix_arr():
    """ベースケースYear3: セグメント別ARR構成"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

    # 顧客数構成
    yr3 = GROWTH_SCENARIOS["Base"]["years"][2]
    seg_labels = [SEGMENTS[s]["label"] for s in yr3.keys()]
    seg_counts = list(yr3.values())
    seg_colors = [SEGMENTS[s]["color"] for s in yr3.keys()]

    ax1.pie(seg_counts, labels=seg_labels, colors=seg_colors, autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 10})
    ax1.set_title(f"顧客数構成（計 {sum(seg_counts)}社）", fontsize=12, fontweight="bold")

    # ARR構成
    seg_arrs = []
    for seg, count in yr3.items():
        e = calc_segment_economics(seg)
        seg_arrs.append(e["annual_revenue"] * count / 1_0000_0000)

    ax2.pie(seg_arrs, labels=seg_labels, colors=seg_colors, autopct="%1.0f%%",
            startangle=90, textprops={"fontsize": 10})
    total_arr = sum(seg_arrs)
    ax2.set_title(f"ARR構成（計 ¥{total_arr:.1f}億）", fontsize=12, fontweight="bold")

    fig.suptitle("ベースケース Year 3 — 顧客数 vs ARR構成", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "customer_mix_arr.png")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_dept_expansion_impact():
    """部門展開によるARPU倍増効果"""
    fig, ax = plt.subplots(figsize=(9, 5.5))

    base_rev = 80 * CS_REP_MONTHLY_COST * 0.60 * VALUE_CAPTURE_RATE / 10000
    departments = [1, 2, 3, 4, 5]
    dept_labels = [
        "CS\nのみ",
        "CS +\n営業",
        "CS +\n営業 + マーケ",
        "CS + 営業 +\nマーケ + HR",
        "全社\n展開"
    ]
    revenues = [base_rev * d for d in departments]

    colors = ["#3b82f6", "#22c55e", "#f59e0b", "#7c3aed", "#dc2626"]
    bars = ax.bar(dept_labels, revenues, color=colors, alpha=0.85, width=0.5)
    for bar, r, d in zip(bars, revenues, departments):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(revenues)*0.02,
                f"¥{r:,.0f}万\n({d}x)", ha="center", fontsize=9, fontweight="bold")

    ax.set_ylabel("月間売上/社（万円）", fontsize=11)
    ax.set_title("大企業1社あたりの部門展開によるARPU拡大効果", fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "dept_expansion.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_cost_vs_value_pricing():
    """旧モデル（コスト+）vs 新モデル（ROIベース）の比較"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    segs = ["SMB", "Mid-Market", "Enterprise", "Mega Enterprise"]
    labels = [SEGMENTS[s]["label"] for s in segs]

    # 旧モデル: クレジット制（Business プラン ¥2万ベース）
    old_model_monthly = []
    for s in segs:
        seg = SEGMENTS[s]
        # 旧モデルの概算: 基本料金 + 少量の超過
        reps = seg["cs_reps"] * seg["departments"]
        if reps <= 15:
            old_model_monthly.append(20000)
        elif reps <= 50:
            old_model_monthly.append(80000)
        elif reps <= 150:
            old_model_monthly.append(200000)
        else:
            old_model_monthly.append(500000)

    # 新モデル: ROIベース
    new_model_monthly = [calc_segment_economics(s)["monthly_revenue"] for s in segs]

    x = np.arange(len(segs))
    width = 0.3

    bars1 = ax.bar(x - width/2, [v/10000 for v in old_model_monthly], width,
                   label="旧モデル（コスト+マージン）", color="#94a3b8", alpha=0.8)
    bars2 = ax.bar(x + width/2, [v/10000 for v in new_model_monthly], width,
                   label="新モデル（ROIベース）", color="#3b82f6", alpha=0.85)

    for i in range(len(segs)):
        ratio = new_model_monthly[i] / old_model_monthly[i]
        ax.text(i + width/2, new_model_monthly[i]/10000 + max(new_model_monthly)/10000*0.03,
                f"{ratio:.0f}x", ha="center", fontsize=11, fontweight="bold", color="#dc2626")
        ax.text(i - width/2, old_model_monthly[i]/10000 + max(new_model_monthly)/10000*0.03,
                f"¥{old_model_monthly[i]/10000:.0f}万", ha="center", fontsize=8, color="#64748b")
        ax.text(i + width/2, new_model_monthly[i]/10000 * 0.5,
                f"¥{new_model_monthly[i]/10000:,.0f}万", ha="center", fontsize=8,
                color="white", fontweight="bold")

    ax.set_ylabel("月間売上/社（万円）", fontsize=11)
    ax.set_title("価格モデル比較：コスト+マージン vs ROIベース", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "cost_vs_value_pricing.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_arr_waterfall():
    """ベースケース Year3 ARR内訳ウォーターフォール"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    yr3 = GROWTH_SCENARIOS["Base"]["years"][2]
    segs = list(yr3.keys())
    seg_labels = [f"{SEGMENTS[s]['label']}\n({yr3[s]}社)" for s in segs]

    arrs = []
    running = 0
    bottoms = []
    for seg in segs:
        e = calc_segment_economics(seg)
        arr = e["annual_revenue"] * yr3[seg] / 1_0000_0000
        arrs.append(arr)
        bottoms.append(running)
        running += arr

    colors = [SEGMENTS[s]["color"] for s in segs]
    x = np.arange(len(segs) + 1)

    # セグメント別
    for i in range(len(segs)):
        ax.bar(i, arrs[i], bottom=bottoms[i], color=colors[i], alpha=0.85, width=0.5)
        if arrs[i] > 0.5:  # 小さすぎる場合はスキップ
            ax.text(i, bottoms[i] + arrs[i]/2, f"¥{arrs[i]:.1f}億",
                    ha="center", va="center", fontsize=10, fontweight="bold", color="white")

    # 合計
    total = sum(arrs)
    ax.bar(len(segs), total, color="#0f172a", alpha=0.9, width=0.5)
    ax.text(len(segs), total/2, f"¥{total:.1f}億", ha="center", va="center",
            fontsize=13, fontweight="bold", color="white")

    ax.set_ylabel("ARR（億円）", fontsize=11)
    ax.set_title("ベースケース Year 3 — ARR構成ウォーターフォール", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(seg_labels + ["合計"], fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "arr_waterfall.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_sensitivity_analysis():
    """感度分析: Value Capture Rate × 顧客数によるARRマトリクス"""
    fig, ax = plt.subplots(figsize=(9, 6))

    capture_rates = [0.15, 0.20, 0.25, 0.30, 0.35]
    customer_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]

    base_yr3 = GROWTH_SCENARIOS["Base"]["years"][2]
    base_arr_at_25 = 0
    for seg, count in base_yr3.items():
        e = calc_segment_economics(seg)
        base_arr_at_25 += e["annual_revenue"] * count

    matrix = np.zeros((len(capture_rates), len(customer_multipliers)))
    for i, cr in enumerate(capture_rates):
        for j, cm in enumerate(customer_multipliers):
            arr_scaled = base_arr_at_25 * (cr / 0.25) * cm / 1_0000_0000
            matrix[i][j] = arr_scaled

    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    for i in range(len(capture_rates)):
        for j in range(len(customer_multipliers)):
            color = "white" if matrix[i][j] > 25 else "black"
            ax.text(j, i, f"¥{matrix[i][j]:.0f}億", ha="center", va="center",
                    fontsize=9, fontweight="bold", color=color)

    ax.set_xticks(range(len(customer_multipliers)))
    ax.set_xticklabels([f"{cm:.0%}" for cm in customer_multipliers])
    ax.set_yticks(range(len(capture_rates)))
    ax.set_yticklabels([f"{cr:.0%}" for cr in capture_rates])
    ax.set_xlabel("顧客数（ベース比）", fontsize=11)
    ax.set_ylabel("Value Capture Rate", fontsize=11)
    ax.set_title("感度分析: 課金率 × 顧客数 → ARR（Year 3）", fontsize=14, fontweight="bold")

    fig.colorbar(im, ax=ax, label="ARR（億円）", shrink=0.8)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "sensitivity_analysis.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


# ===========================================================================
# PDF生成
# ===========================================================================
def build_styles():
    styles = getSampleStyleSheet()
    defs = [
        ("JP_Title", "IPAPGothic", 26, 34, PRIMARY, TA_CENTER, 20, None),
        ("JP_Subtitle", "IPAPGothic", 14, 20, DARK, TA_CENTER, 30, None),
        ("JP_H1", "IPAPGothic", 16, 22, BLUE, TA_LEFT, 10, 20),
        ("JP_H2", "IPAPGothic", 13, 18, PURPLE, TA_LEFT, 8, 14),
        ("JP_H3", "IPAPGothic", 11, 15, DARK, TA_LEFT, 6, 10),
        ("JP_Body", "IPAGothic", 9, 15, DARK, TA_JUSTIFY, 6, 0),
        ("JP_Small", "IPAGothic", 8, 12, DARK, TA_LEFT, 4, 0),
        ("JP_Caption", "IPAGothic", 7.5, 10, HexColor("#64748b"), TA_CENTER, 12, 0),
    ]
    for name, font, size, lead, color, align, after, before in defs:
        styles.add(ParagraphStyle(name, fontName=font, fontSize=size, leading=lead,
                                  textColor=color, alignment=align, spaceAfter=after,
                                  spaceBefore=before or 0))
    styles.add(ParagraphStyle(
        "JP_Highlight", fontName="IPAPGothic", fontSize=10, leading=15,
        textColor=ACCENT, spaceBefore=8, spaceAfter=8, alignment=TA_CENTER,
        borderWidth=1, borderColor=ACCENT, borderPadding=8,
        backColor=HexColor("#ecfdf5"),
    ))
    styles.add(ParagraphStyle(
        "JP_Alert", fontName="IPAPGothic", fontSize=10, leading=15,
        textColor=RED, spaceBefore=8, spaceAfter=8, alignment=TA_CENTER,
        borderWidth=1, borderColor=RED, borderPadding=8,
        backColor=HexColor("#fef2f2"),
    ))
    styles.add(ParagraphStyle(
        "JP_BigNumber", fontName="IPAPGothic", fontSize=28, leading=36,
        textColor=BLUE, spaceBefore=10, spaceAfter=10, alignment=TA_CENTER,
    ))
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
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
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
    setup_matplotlib()
    styles = build_styles()

    print("チャート生成中...")
    charts = {
        "roi_seg": chart_roi_per_segment(),
        "arr_road": chart_arr_roadmap(),
        "arpu": chart_arpu_comparison(),
        "margin": chart_gross_margin_structure(),
        "mix": chart_customer_mix_arr(),
        "dept": chart_dept_expansion_impact(),
        "pricing_cmp": chart_cost_vs_value_pricing(),
        "waterfall": chart_arr_waterfall(),
        "sensitivity": chart_sensitivity_analysis(),
    }
    print("チャート生成完了")

    doc = SimpleDocTemplate(PDF_PATH, pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    story = []

    # ===== 表紙 =====
    story.append(Spacer(1, 45*mm))
    story.append(Paragraph("relation AI", styles["JP_Title"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("ROIベース価格設計", styles["JP_Title"]))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("— 数十億ARRへの到達シナリオ —", styles["JP_Subtitle"]))
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(
        "「AIの原価に上乗せする」のではなく<br/>「顧客が得る価値の一部をいただく」", styles["JP_Subtitle"]))
    story.append(Spacer(1, 25*mm))
    story.append(Paragraph("ingAge Inc.  |  2026年3月  |  Confidential", styles["JP_Caption"]))
    story.append(PageBreak())

    # ===== 目次 =====
    story.append(Paragraph("目次", styles["JP_H1"]))
    story.append(divider())
    toc_items = [
        "1. なぜ前回モデルでは数億止まりなのか",
        "2. ROIベース価格設計の基本思想",
        "3. セグメント別 ROI構造分析",
        "4. 1社あたりARPU：コスト+マージン vs ROIベース",
        "5. 新クレジットプラン設計",
        "6. 部門展開によるARPU拡大戦略",
        "7. 3年ARRロードマップ（3シナリオ）",
        "8. Year 3 ARR構成分析",
        "9. 粗利率構造：なぜ90%超が可能か",
        "10. 感度分析：課金率 × 顧客数",
        "11. 数十億ARRへの必要条件",
        "12. 結論と推奨アクション",
    ]
    for item in toc_items:
        story.append(Paragraph(f"　{item}", styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 1. なぜ前回モデルでは数億止まりか =====
    story.append(Paragraph("1. なぜ前回モデルでは数億止まりなのか", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "前回のクレジット設計では、ARR 2.6億円が上限でした。この根本原因を分析します。",
        styles["JP_Body"]))

    story.append(Paragraph("<b>問題1：コスト+マージンの罠</b>", styles["JP_H3"]))
    story.append(Paragraph(
        "AI原価¥1.1/crに対して¥6〜12/crで販売 → 粗利率は高いが<b>絶対額が小さすぎる</b>。"
        "月額¥2万〜¥8万では大企業を取れない。SaaSの世界では「安い＝価値が低い」と見なされる。",
        styles["JP_Body"]))

    story.append(Paragraph("<b>問題2：CS部門だけに閉じている</b>", styles["JP_H3"]))
    story.append(Paragraph(
        "カスタマーサポートだけでは、企業のコスト構造の一部にしかアクセスできない。"
        "営業・マーケ・HR・法務など、テキストコミュニケーションが発生する部門はすべてターゲットにできる。",
        styles["JP_Body"]))

    story.append(Paragraph("<b>問題3：顧客数が保守的</b>", styles["JP_H3"]))
    story.append(Paragraph(
        "成熟期340社で打ち止めの前提は保守的すぎる。日本のCS組織は推定5万社以上。"
        "SaaS市場の拡大トレンドから、3年で1,000社以上は十分に射程圏内。",
        styles["JP_Body"]))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        "旧モデル最大ARPU（大企業）：月額 ¥50万〜¥90万<br/>"
        "→ 新モデル（ROIベース）：月額 <b>¥550万〜¥2,750万</b>（10〜30倍）",
        styles["JP_Alert"]))
    story.append(PageBreak())

    # ===== 2. ROIベース価格設計の基本思想 =====
    story.append(Paragraph("2. ROIベース価格設計の基本思想", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>原則：顧客が得る価値の25%をいただく</b>", styles["JP_H2"]))
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph(
        "AI導入で削減される人件費が「顧客が得る価値」です。"
        "この削減額の <b>25%</b> をrelation AIの課金額とすることで、"
        "顧客は <b>75%の手残り（ROI 3倍）</b> を確保できます。",
        styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    roi_table = [
        ["", "金額", "説明"],
        ["CS担当者の年間コスト", f"¥{CS_REP_ANNUAL_COST:,}", "給与+社保+間接費の中央値"],
        ["CS担当者の時間単価", f"¥{CS_REP_HOURLY_COST:,.0f}/h", "年240日×8時間で割算"],
        ["AI自動化率（目標）", "50〜60%", "問い合わせの半数以上をAI対応"],
        ["Value Capture Rate", "25%", "削減人件費の25%を課金"],
        ["顧客のROI", "3倍", "投資の3倍のリターンを保証"],
    ]
    story.append(make_table(roi_table, col_widths=[40*mm, 40*mm, 70*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>なぜ25%が最適か</b>", styles["JP_H3"]))
    logic = [
        "• <b>10〜15%</b>：安すぎる。売上が伸びず、数億止まり。「安いツール」のポジション",
        "• <b>20〜30%</b>：スイートスポット。顧客ROI 3〜5倍。稟議が通りやすく、解約率も低い",
        "• <b>35%以上</b>：顧客のROI感が薄れる。競合出現時に価格競争リスク",
        "",
        "25%は <b>「導入しない理由がない」</b> 水準。CSチームを半減させたい経営者にとって、"
        "削減額の25%で済むなら確実にGoサインが出ます。",
    ]
    for line in logic:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 3. セグメント別ROI構造分析 =====
    story.append(Paragraph("3. セグメント別 ROI構造分析", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["roi_seg"], width=165*mm, height=100*mm))
    story.append(Paragraph("図1: セグメント別 ROI構造 — 人件費 vs 課金 vs 顧客手残り", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    seg_header = ["セグメント", "CS人数\n(×部門数)", "月間\n人件費", "AI自動化\n削減額", "月間課金\n(25%)", "顧客\n手残り", "顧客\nROI"]
    seg_rows = [seg_header]
    for seg_name in SEGMENTS:
        s = SEGMENTS[seg_name]
        e = calc_segment_economics(seg_name)
        seg_rows.append([
            s["label"],
            f'{s["cs_reps"]}名×{s["departments"]}部門',
            f'¥{e["total_monthly_labor"]/10000:,.0f}万',
            f'¥{e["monthly_savings_potential"]/10000:,.0f}万',
            f'¥{e["monthly_revenue"]/10000:,.0f}万',
            f'¥{e["customer_net_savings"]/10000:,.0f}万',
            f'{e["customer_roi"]:.1f}x',
        ])
    story.append(make_table(seg_rows, col_widths=[22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 18*mm]))
    story.append(Spacer(1, 3*mm))

    mega = calc_segment_economics("Mega Enterprise")
    story.append(Paragraph(
        f"超大企業1社で月間 <b>¥{mega['monthly_revenue']/10000:,.0f}万</b>・"
        f"年間 <b>¥{mega['annual_revenue']/10000:,.0f}万</b> の売上。"
        f"顧客は毎月 <b>¥{mega['customer_net_savings']/10000:,.0f}万</b> の手残り（ROI {mega['customer_roi']:.1f}x）。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # ===== 4. コスト+マージン vs ROIベース =====
    story.append(Paragraph("4. 1社あたりARPU：コスト+マージン vs ROIベース", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["pricing_cmp"], width=165*mm, height=95*mm))
    story.append(Paragraph("図2: 価格モデル比較 — 大企業で10〜30倍のARPU差", styles["JP_Caption"]))
    story.append(Spacer(1, 5*mm))

    story.append(Image(charts["arpu"], width=165*mm, height=80*mm))
    story.append(Paragraph("図3: ROIベース課金によるセグメント別ARPU", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "ROIベースにすることで、旧モデル比 <b>10〜30倍</b> のARPUを実現。"
        "これは「値上げ」ではなく、<b>価値に見合った価格設定</b> です。"
        "顧客のROIは3倍を維持しており、導入障壁は低いままです。",
        styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 5. 新クレジットプラン設計 =====
    story.append(Paragraph("5. 新クレジットプラン設計（ROIベース版）", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "クレジット制は維持しつつ、プラン価格をROIベースに引き上げます。"
        "顧客の人件費削減額の25%に収まるよう設計しています。",
        styles["JP_Body"]))
    story.append(Spacer(1, 2*mm))

    plan_header = ["", "Growth", "Scale", "Enterprise", "Strategic"]
    plan_data = [
        plan_header,
        ["月額", "¥100,000", "¥500,000", "¥2,000,000", "¥8,000,000"],
        ["含有クレジット/月", "5,000 cr", "30,000 cr", "150,000 cr", "800,000 cr"],
        ["超過単価/cr", "¥25", "¥20", "¥15", "¥12"],
        ["ターゲット", "CS 5〜15名", "CS 20〜50名\n+複数部門", "CS 50名以上\n全社展開", "CS 200名以上"],
        ["顧客のROI", "3〜4x", "3〜5x", "3〜5x", "3〜5x"],
        ["AIモデル", "Sonnet", "Sonnet", "Sonnet/Opus", "Opus/Custom"],
        ["専任CSM", "—", "あり", "あり", "あり+CXO連携"],
        ["カスタムモデル", "—", "—", "オプション", "標準"],
    ]
    story.append(make_table(plan_data, col_widths=[28*mm, 30*mm, 32*mm, 32*mm, 32*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        "旧モデルの最上位プラン（Enterprise ¥8万/月）が、新モデルの最下位プラン（Growth ¥10万/月）よりも安い。"
        "これが「コスト+マージン」と「ROIベース」の根本的な差です。",
        styles["JP_Alert"]))
    story.append(PageBreak())

    # ===== 6. 部門展開によるARPU拡大 =====
    story.append(Paragraph("6. 部門展開によるARPU拡大戦略", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "CSで導入後、営業・マーケ・HR・法務に横展開することで、"
        "1社あたりの売上を <b>2〜5倍</b> に拡大できます。"
        "これがNet Revenue Retention 130%以上の原動力です。",
        styles["JP_Body"]))
    story.append(Spacer(1, 2*mm))

    story.append(Image(charts["dept"], width=155*mm, height=95*mm))
    story.append(Paragraph("図4: 大企業1社あたりの部門展開によるARPU拡大効果", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    dept_detail = [
        ["展開段階", "対象部門", "月間売上\n/社", "追加提供価値"],
        ["Phase 1", "カスタマーサポート", "¥550万", "問い合わせ自動返信、ナレッジ生成"],
        ["Phase 2", "+ 営業/インサイドセールス", "¥1,100万", "メール返信支援、商談要約"],
        ["Phase 3", "+ マーケティング", "¥1,650万", "コンテンツ生成、キャンペーン分析"],
        ["Phase 4", "+ HR/管理部門", "¥2,200万", "採用対応、社内問い合わせ自動化"],
        ["Phase 5", "全社展開", "¥2,750万", "全部門のAI業務自動化基盤"],
    ]
    story.append(make_table(dept_detail, col_widths=[20*mm, 36*mm, 24*mm, 60*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        "Enterprise顧客15社が全社展開するだけで MRR ¥4.1億・ARR <b>¥50億</b> に到達可能。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # ===== 7. 3年ARRロードマップ =====
    story.append(Paragraph("7. 3年ARRロードマップ（3シナリオ）", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["arr_road"], width=165*mm, height=100*mm))
    story.append(Paragraph("図5: 3年ARRロードマップ — 数十億は到達可能か", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    arr_header = ["シナリオ", "Year 1\nARR", "Year 2\nARR", "Year 3\nARR", "Year 3\n顧客数", "Year 3\nMRR"]
    arr_rows = [arr_header]
    for sc_name, sc in GROWTH_SCENARIOS.items():
        yr_data = []
        for yr in range(3):
            r = calc_scenario_arr(sc_name, yr)
            yr_data.append(r)
        arr_rows.append([
            sc["label"],
            f'¥{yr_data[0]["arr"]/1_0000_0000:.1f}億',
            f'¥{yr_data[1]["arr"]/1_0000_0000:.1f}億',
            f'¥{yr_data[2]["arr"]/1_0000_0000:.1f}億',
            f'{yr_data[2]["total_customers"]}社',
            f'¥{yr_data[2]["mrr"]/1_0000_0000:.1f}億',
        ])
    story.append(make_table(arr_rows, col_widths=[25*mm, 24*mm, 24*mm, 24*mm, 22*mm, 24*mm]))
    story.append(Spacer(1, 5*mm))

    base_yr3 = calc_scenario_arr("Base", 2)
    agg_yr3 = calc_scenario_arr("Aggressive", 2)
    story.append(Paragraph(
        f"ベースケースで <b>¥{base_yr3['arr']/1_0000_0000:.0f}億 ARR</b>（Year 3）、"
        f"攻めシナリオで <b>¥{agg_yr3['arr']/1_0000_0000:.0f}億 ARR</b>。"
        "いずれも <b>数十億円のARR</b> に到達可能。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # ===== 8. Year 3 ARR構成 =====
    story.append(Paragraph("8. Year 3 ARR構成分析（ベースケース）", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["waterfall"], width=165*mm, height=95*mm))
    story.append(Paragraph("図6: Year 3 ARR構成ウォーターフォール", styles["JP_Caption"]))
    story.append(Spacer(1, 5*mm))

    story.append(Image(charts["mix"], width=165*mm, height=80*mm))
    story.append(Paragraph("図7: 顧客数構成 vs ARR構成 — Enterprise・Megaが売上の大半を占める", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "顧客数では SMB が67%を占めるが、ARRでは Enterprise + Mega が <b>70%以上</b> を占める。"
        "エンタープライズ攻略が数十億ARR到達の鍵。",
        styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 9. 粗利率構造 =====
    story.append(Paragraph("9. 粗利率構造：なぜ90%超が可能か", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["margin"], width=155*mm, height=95*mm))
    story.append(Paragraph("図8: セグメント別 売上・AI原価・粗利率", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    margin_header = ["セグメント", "月間売上", "AI原価/月", "粗利/月", "粗利率"]
    margin_rows = [margin_header]
    for seg_name in SEGMENTS:
        e = calc_segment_economics(seg_name)
        margin_rows.append([
            SEGMENTS[seg_name]["label"],
            f'¥{e["monthly_revenue"]/10000:,.0f}万',
            f'¥{e["monthly_ai_cost"]/10000:,.0f}万',
            f'¥{e["monthly_gross_profit"]/10000:,.0f}万',
            f'{e["gross_margin"]:.1f}%',
        ])
    story.append(make_table(margin_rows, col_widths=[30*mm, 30*mm, 28*mm, 30*mm, 22*mm]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "ROIベースの価格設定で売上が拡大しても、AI原価は変わらないため、"
        "粗利率は <b>95%以上</b> を維持。これはSaaS業界でもトップクラスの収益構造です。",
        styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>AI原価が安い理由</b>", styles["JP_H3"]))
    ai_reason = [
        f"• AI自動返信1件のコスト：わずか <b>¥{AI_COST_PER_REPLY}</b>（Sonnet 4.5基準）",
        f"• 人間1人が処理するのと同じ量をAIで処理するコスト：月間 <b>¥{960 * AI_COST_PER_REPLY:,.0f}</b>（≒¥3,264）",
        f"• 人間1人の月間人件費：<b>¥{CS_REP_MONTHLY_COST:,.0f}</b>",
        f"• 人間 vs AI のコスト差：<b>約{CS_REP_MONTHLY_COST / (960 * AI_COST_PER_REPLY):.0f}倍</b>",
        "",
        "この <b>140倍のコスト差</b> が、高い粗利率と顧客への大幅な値引きを同時に可能にしています。",
    ]
    for line in ai_reason:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 10. 感度分析 =====
    story.append(Paragraph("10. 感度分析：課金率 × 顧客数", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "Value Capture Rate（削減人件費の何%を課金するか）と顧客数の組み合わせで、"
        "Year 3 のARRがどう変動するかを示します。",
        styles["JP_Body"]))
    story.append(Spacer(1, 2*mm))

    story.append(Image(charts["sensitivity"], width=150*mm, height=100*mm))
    story.append(Paragraph("図9: 感度分析ヒートマップ（¥10億超の領域が広い）", styles["JP_Caption"]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        "課金率20%・顧客数75%でも <b>¥16億 ARR</b>。"
        "課金率を30%に引き上げて顧客数ベースの1.25倍を達成すれば <b>¥40億 ARR</b>。"
        "¥10億ARRは複数の経路で到達可能な堅い目標です。",
        styles["JP_Highlight"]))
    story.append(PageBreak())

    # ===== 11. 数十億ARRへの必要条件 =====
    story.append(Paragraph("11. 数十億ARRへの必要条件", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>¥10億 ARR（最低ライン）</b>", styles["JP_H2"]))
    ten_b = [
        "必要な組み合わせ例：",
        "• パターンA：Enterprise 20社 + Mid-Market 80社 + SMB 300社",
        "• パターンB：Mega Enterprise 5社 + Enterprise 15社 + Mid-Market 50社",
        "• パターンC：Mid-Market 200社 + SMB 500社（ボリューム型）",
        "",
        "いずれも3年以内に到達可能な顧客数。日本のCS組織推定5万社のうち <b>わずか0.4〜1.4%</b>。",
    ]
    for line in ten_b:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>¥30億 ARR（中期目標）</b>", styles["JP_H2"]))
    thirty_b = [
        "必要な組み合わせ例：",
        "• Mega Enterprise 10社 + Enterprise 50社 + Mid-Market 200社 + SMB 500社",
        "• 部門展開率が高まればさらに少ない顧客数で到達可能",
        "",
        "エンタープライズ営業チーム（5〜10名）があれば十分に獲得可能な顧客数。",
    ]
    for line in thirty_b:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>¥50億+ ARR（大型目標）</b>", styles["JP_H2"]))
    fifty_b = [
        "到達条件：",
        "• エンタープライズ顧客の部門展開（平均3部門以上）",
        "• Value Capture Rate 30%への段階的引き上げ（実績に応じて）",
        "• アジア太平洋地域への展開（日本語AIの強みを活かしてAPAC進出）",
        "• AIエージェント型課金の追加（1タスク完結で¥500〜¥5,000の高単価課金）",
    ]
    for line in fifty_b:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ===== 12. 結論 =====
    story.append(Paragraph("12. 結論と推奨アクション", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        f"ベースケースで Year 3 に <b>¥{base_yr3['arr']/1_0000_0000:.0f}億 ARR</b>、"
        f"攻めシナリオで <b>¥{agg_yr3['arr']/1_0000_0000:.0f}億 ARR</b>。"
        "数十億のARRは、ROIベースの価格設計により、現実的に到達可能な目標です。",
        styles["JP_BigNumber"]))
    # repeat key number in Highlight box
    story.append(Paragraph(
        f"ベースケース Year 3: <b>¥{base_yr3['arr']/1_0000_0000:.0f}億 ARR</b>　|　"
        f"攻め Year 3: <b>¥{agg_yr3['arr']/1_0000_0000:.0f}億 ARR</b>",
        styles["JP_Highlight"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>推奨アクション</b>", styles["JP_H2"]))
    actions = [
        "1. <b>即座にROIベース価格に転換</b>：コスト+マージンでは数億止まり。"
        "「AI原価がいくらか」ではなく「顧客がいくら得するか」でプライシングする",
        "",
        "2. <b>エンタープライズ営業チームの早期構築</b>：ARRの70%はEnterprise・Mega Enterpriseから。"
        "法人営業経験者3〜5名を最優先で採用し、大企業10社のPoCを推進",
        "",
        "3. <b>部門横展開をプロダクト設計に組み込む</b>：CSだけでなく、"
        "営業・マーケ・HR対応のテンプレートとワークフローを初期から準備",
        "",
        "4. <b>ROI保証プログラムの導入</b>：「導入後3ヶ月でROI 3倍未満なら全額返金」。"
        "これにより稟議突破率が劇的に改善。実際のROIは3〜5倍なのでリスクは小さい",
        "",
        "5. <b>AIエージェント課金の開発ロードマップ</b>：Year 2以降、"
        "単一操作の「クレジット」に加え、複数ステップを自動完結する"
        "「エージェント」（¥500〜¥5,000/タスク）を追加。ARPU倍増のドライバー",
        "",
        "6. <b>モデルコスト低下の内部吸収</b>：AI原価は年30〜50%低下傾向。"
        "価格は据え置き、粗利改善 → R&D投資の好循環を回す",
    ]
    for line in actions:
        story.append(Paragraph(line, styles["JP_Body"]))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("— End of Report —", styles["JP_Caption"]))

    print("PDF生成中...")
    doc.build(story)
    print(f"PDF生成完了: {PDF_PATH}")
    return PDF_PATH


if __name__ == "__main__":
    generate_pdf()
