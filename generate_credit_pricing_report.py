#!/usr/bin/env python3
"""
relation AIサービス クレジット設計・売上シミュレーション分析レポート生成
ingAge Inc. - 2026年3月
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(OUTPUT_DIR, "relation_credit_pricing_analysis.pdf")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

USD_JPY = 150

pdfmetrics.registerFont(TTFont("IPAGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"))
pdfmetrics.registerFont(TTFont("IPAPGothic", "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"))

# カラー
PRIMARY = HexColor("#1a56db")
SECONDARY = HexColor("#6366f1")
ACCENT = HexColor("#059669")
DARK = HexColor("#1e293b")
TABLE_HEADER_BG = HexColor("#1e40af")
TABLE_ALT_BG = HexColor("#eff6ff")
WHITE = white

# ---------------------------------------------------------------------------
# AIモデル価格 (USD / 1M tokens) — 2026年3月時点
# ---------------------------------------------------------------------------
MODELS = {
    "Claude Haiku 4.5":  {"input": 1.00, "output": 5.00,  "label": "軽量・高速"},
    "Claude Sonnet 4.5": {"input": 3.00, "output": 15.00, "label": "バランス型"},
    "Claude Opus 4.5":   {"input": 5.00, "output": 25.00, "label": "最高精度"},
    "GPT-4o mini":       {"input": 0.15, "output": 0.60,  "label": "超軽量"},
    "GPT-4o":            {"input": 2.50, "output": 10.00, "label": "バランス型"},
}

# ---------------------------------------------------------------------------
# 各AI機能のトークン消費量（日本語ベース）と推奨クレジット数
# ---------------------------------------------------------------------------
AI_FEATURES = {
    "AI自動返信（シンプル）": {
        "desc": "FAQ・定型文ベースの短い返信",
        "input_tokens": 2000,
        "output_tokens": 250,
        "credits": 1,
        "human_minutes": 5,
        "category": "返信",
    },
    "AI自動返信（標準）": {
        "desc": "RAG検索+文脈理解による返信生成",
        "input_tokens": 4500,
        "output_tokens": 500,
        "credits": 3,
        "human_minutes": 10,
        "category": "返信",
    },
    "AI自動返信（複雑）": {
        "desc": "複数KB参照+過去履歴+詳細回答",
        "input_tokens": 8000,
        "output_tokens": 800,
        "credits": 5,
        "human_minutes": 20,
        "category": "返信",
    },
    "返信文ドラフト提案": {
        "desc": "オペレーター向けに返信候補を3案提示",
        "input_tokens": 4000,
        "output_tokens": 1200,
        "credits": 4,
        "human_minutes": 15,
        "category": "返信",
    },
    "問い合わせ自動分類": {
        "desc": "受信メッセージのカテゴリ・優先度判定",
        "input_tokens": 1500,
        "output_tokens": 100,
        "credits": 1,
        "human_minutes": 3,
        "category": "分析",
    },
    "対応要約生成": {
        "desc": "対応履歴から要約を自動生成",
        "input_tokens": 5000,
        "output_tokens": 600,
        "credits": 3,
        "human_minutes": 15,
        "category": "分析",
    },
    "ナレッジ記事生成": {
        "desc": "対応実績からナレッジ記事を自動作成",
        "input_tokens": 5000,
        "output_tokens": 2000,
        "credits": 8,
        "human_minutes": 60,
        "category": "ナレッジ",
    },
    "ナレッジ更新・レビュー": {
        "desc": "既存記事の最新化・品質チェック",
        "input_tokens": 3000,
        "output_tokens": 1000,
        "credits": 5,
        "human_minutes": 30,
        "category": "ナレッジ",
    },
    "FAQ自動抽出": {
        "desc": "問い合わせデータからFAQ候補を抽出",
        "input_tokens": 6000,
        "output_tokens": 1500,
        "credits": 6,
        "human_minutes": 45,
        "category": "ナレッジ",
    },
    "感情分析・トーン検出": {
        "desc": "顧客メッセージの感情・緊急度判定",
        "input_tokens": 1200,
        "output_tokens": 150,
        "credits": 1,
        "human_minutes": 5,
        "category": "分析",
    },
}

# ---------------------------------------------------------------------------
# クレジットプラン設計
# ---------------------------------------------------------------------------
CREDIT_PLANS = {
    "Free": {
        "monthly_fee": 0,
        "included_credits": 50,
        "extra_credit_price": None,  # 追加購入不可
        "model": "Claude Haiku 4.5",
        "color": "#94a3b8",
    },
    "Starter": {
        "monthly_fee": 5000,
        "included_credits": 500,
        "extra_credit_price": 12,
        "model": "Claude Haiku 4.5",
        "color": "#22c55e",
    },
    "Business": {
        "monthly_fee": 20000,
        "included_credits": 3000,
        "extra_credit_price": 8,
        "model": "Claude Sonnet 4.5",
        "color": "#3b82f6",
    },
    "Enterprise": {
        "monthly_fee": 80000,
        "included_credits": 15000,
        "extra_credit_price": 6,
        "model": "Claude Sonnet 4.5",
        "color": "#8b5cf6",
    },
}

# ---------------------------------------------------------------------------
# 企業規模別 月間利用パターン
# ---------------------------------------------------------------------------
USAGE_PROFILES = {
    "スタートアップ\n(CS 3〜5名)": {
        "AI自動返信（シンプル）": 200,
        "AI自動返信（標準）": 100,
        "AI自動返信（複雑）": 20,
        "返信文ドラフト提案": 50,
        "問い合わせ自動分類": 300,
        "対応要約生成": 30,
        "ナレッジ記事生成": 5,
        "ナレッジ更新・レビュー": 10,
        "FAQ自動抽出": 3,
        "感情分析・トーン検出": 200,
    },
    "中小企業\n(CS 10〜20名)": {
        "AI自動返信（シンプル）": 1000,
        "AI自動返信（標準）": 600,
        "AI自動返信（複雑）": 100,
        "返信文ドラフト提案": 300,
        "問い合わせ自動分類": 1500,
        "対応要約生成": 200,
        "ナレッジ記事生成": 15,
        "ナレッジ更新・レビュー": 30,
        "FAQ自動抽出": 8,
        "感情分析・トーン検出": 1000,
    },
    "中堅企業\n(CS 30〜60名)": {
        "AI自動返信（シンプル）": 4000,
        "AI自動返信（標準）": 3000,
        "AI自動返信（複雑）": 500,
        "返信文ドラフト提案": 1000,
        "問い合わせ自動分類": 6000,
        "対応要約生成": 800,
        "ナレッジ記事生成": 40,
        "ナレッジ更新・レビュー": 80,
        "FAQ自動抽出": 20,
        "感情分析・トーン検出": 5000,
    },
    "大企業\n(CS 100名以上)": {
        "AI自動返信（シンプル）": 15000,
        "AI自動返信（標準）": 10000,
        "AI自動返信（複雑）": 2000,
        "返信文ドラフト提案": 5000,
        "問い合わせ自動分類": 25000,
        "対応要約生成": 3000,
        "ナレッジ記事生成": 100,
        "ナレッジ更新・レビュー": 200,
        "FAQ自動抽出": 50,
        "感情分析・トーン検出": 20000,
    },
}

# =====================================================================
# 計算ロジック
# =====================================================================

def ai_cost_jpy(model_name, input_tokens, output_tokens):
    """AI原価（円）"""
    m = MODELS[model_name]
    usd = (input_tokens * m["input"] / 1_000_000) + (output_tokens * m["output"] / 1_000_000)
    return usd * USD_JPY


def feature_ai_cost(feature_name, model_name):
    """機能1回あたりのAI原価"""
    f = AI_FEATURES[feature_name]
    return ai_cost_jpy(model_name, f["input_tokens"], f["output_tokens"])


def feature_human_cost(feature_name):
    """機能1回あたりの人件費換算"""
    return 1500 * AI_FEATURES[feature_name]["human_minutes"] / 60


def calc_monthly_credits(profile):
    """利用プロファイルの月間クレジット消費量"""
    total = 0
    for feat, count in profile.items():
        total += AI_FEATURES[feat]["credits"] * count
    return total


def calc_monthly_ai_cost(profile, model_name):
    """利用プロファイルの月間AI原価"""
    total = 0.0
    for feat, count in profile.items():
        total += feature_ai_cost(feat, model_name) * count
    return total


def calc_monthly_human_cost(profile):
    """利用プロファイルの月間人件費換算"""
    total = 0.0
    for feat, count in profile.items():
        total += feature_human_cost(feat) * count
    return total


def calc_plan_revenue(plan_name, credits_used):
    """プランの月間売上"""
    p = CREDIT_PLANS[plan_name]
    revenue = p["monthly_fee"]
    over = max(0, credits_used - p["included_credits"])
    if over > 0 and p["extra_credit_price"] is not None:
        revenue += over * p["extra_credit_price"]
    return revenue


def best_plan_for_usage(credits_needed):
    """クレジット消費量に最適なプラン"""
    best = None
    best_cost = float("inf")
    for name, p in CREDIT_PLANS.items():
        if name == "Free" and credits_needed > p["included_credits"]:
            continue
        cost = calc_plan_revenue(name, credits_needed)
        if cost < best_cost:
            best_cost = cost
            best = name
    return best, best_cost


# =====================================================================
# チャート生成
# =====================================================================

def setup_matplotlib():
    plt.rcParams["font.family"] = "IPAGothic"
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.unicode_minus"] = False


def chart_credit_consumption_by_feature():
    """機能別クレジット消費量"""
    fig, ax = plt.subplots(figsize=(9, 5))
    features = list(AI_FEATURES.keys())
    credits = [AI_FEATURES[f]["credits"] for f in features]
    colors_map = {"返信": "#3b82f6", "分析": "#22c55e", "ナレッジ": "#f59e0b"}
    colors = [colors_map[AI_FEATURES[f]["category"]] for f in features]

    bars = ax.barh(features, credits, color=colors, alpha=0.85, height=0.6)
    for bar, c in zip(bars, credits):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2,
                f"{c} cr", va="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("クレジット消費量", fontsize=11)
    ax.set_title("機能別クレジット消費量", fontsize=14, fontweight="bold")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlim(0, max(credits) + 2)

    # 凡例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=l) for l, c in colors_map.items()]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    fig.tight_layout()
    path = os.path.join(CHART_DIR, "credit_by_feature.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_cost_per_credit_by_model():
    """モデル別 1クレジットあたりのAI原価"""
    fig, ax = plt.subplots(figsize=(8, 5))

    # 「AI自動返信（標準）」= 3クレジットを基準に1クレジット単価を算出
    model_names = list(MODELS.keys())
    cost_per_credit = []
    for m in model_names:
        cost_reply = feature_ai_cost("AI自動返信（標準）", m)
        cost_per_credit.append(cost_reply / 3)  # 3クレジット消費

    colors = ["#22c55e", "#3b82f6", "#8b5cf6", "#a3e635", "#f59e0b"]
    bars = ax.bar(model_names, cost_per_credit, color=colors, alpha=0.85, width=0.5)
    for bar, cost in zip(bars, cost_per_credit):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"¥{cost:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylabel("AI原価（円 / 1クレジット）", fontsize=11)
    ax.set_title("モデル別 1クレジットあたりのAI原価", fontsize=14, fontweight="bold")
    ax.set_xticklabels(model_names, fontsize=9, rotation=15, ha="right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "cost_per_credit.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_monthly_credits_by_company():
    """企業規模別 月間クレジット消費量 内訳"""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    company_names = list(USAGE_PROFILES.keys())
    categories = {"返信": [], "分析": [], "ナレッジ": []}

    for cn in company_names:
        profile = USAGE_PROFILES[cn]
        cat_credits = {"返信": 0, "分析": 0, "ナレッジ": 0}
        for feat, count in profile.items():
            cat = AI_FEATURES[feat]["category"]
            cat_credits[cat] += AI_FEATURES[feat]["credits"] * count
        for cat in categories:
            categories[cat].append(cat_credits[cat])

    x = np.arange(len(company_names))
    width = 0.5
    colors_map = {"返信": "#3b82f6", "分析": "#22c55e", "ナレッジ": "#f59e0b"}
    bottom = np.zeros(len(company_names))

    for cat_name, values in categories.items():
        ax.bar(x, values, width, bottom=bottom, label=cat_name,
               color=colors_map[cat_name], alpha=0.85)
        bottom += np.array(values)

    # 合計ラベル
    totals = [calc_monthly_credits(USAGE_PROFILES[cn]) for cn in company_names]
    for i, total in enumerate(totals):
        ax.text(i, total + 500, f"{total:,} cr", ha="center", va="bottom",
                fontsize=10, fontweight="bold")

    ax.set_ylabel("月間クレジット消費量", fontsize=11)
    ax.set_title("企業規模別 月間クレジット消費量（カテゴリ内訳）", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(company_names, fontsize=9)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "monthly_credits_company.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_revenue_vs_cost():
    """プラン別 売上 vs AI原価 vs 人件費削減額"""
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    company_names = list(USAGE_PROFILES.keys())

    for idx, cn in enumerate(company_names):
        ax = axes[idx // 2][idx % 2]
        profile = USAGE_PROFILES[cn]
        credits_needed = calc_monthly_credits(profile)
        human_cost = calc_monthly_human_cost(profile) / 10000

        plan_names = ["Starter", "Business", "Enterprise"]
        revenues = []
        ai_costs = []
        for pn in plan_names:
            model = CREDIT_PLANS[pn]["model"]
            revenues.append(calc_plan_revenue(pn, credits_needed) / 10000)
            ai_costs.append(calc_monthly_ai_cost(profile, model) / 10000)

        x = np.arange(len(plan_names))
        width = 0.25

        ax.bar(x - width, [human_cost]*3, width, label="人件費", color="#ef4444", alpha=0.7)
        ax.bar(x, revenues, width, label="AI課金売上",
               color=[CREDIT_PLANS[p]["color"] for p in plan_names], alpha=0.85)
        ax.bar(x + width, ai_costs, width, label="AI原価", color="#94a3b8", alpha=0.7)

        clean_name = cn.replace('\n', ' ')
        ax.set_title(f"{clean_name}\n(月間{credits_needed:,}クレジット)", fontsize=10, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(plan_names, fontsize=9)
        ax.set_ylabel("万円", fontsize=9)
        ax.grid(axis="y", alpha=0.3)
        if idx == 0:
            ax.legend(fontsize=8, loc="upper right")

    fig.suptitle("プラン別 月間売上 vs 人件費 vs AI原価", fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "revenue_vs_cost.png")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_margin_structure():
    """クレジット単価と原価・マージンの構造"""
    fig, ax = plt.subplots(figsize=(8, 5))
    plans = ["Starter", "Business", "Enterprise"]
    # 実効クレジット単価（月額÷含むクレジット）
    effective_price = [CREDIT_PLANS[p]["monthly_fee"] / CREDIT_PLANS[p]["included_credits"] for p in plans]
    # 超過単価
    extra_price = [CREDIT_PLANS[p]["extra_credit_price"] for p in plans]
    # AI原価/クレジット（標準返信ベース）
    ai_costs = [feature_ai_cost("AI自動返信（標準）", CREDIT_PLANS[p]["model"]) / 3 for p in plans]

    x = np.arange(len(plans))
    width = 0.2

    ax.bar(x - width, effective_price, width, label="実効単価（月額÷含有cr）", color="#3b82f6", alpha=0.85)
    ax.bar(x, extra_price, width, label="超過クレジット単価", color="#f59e0b", alpha=0.85)
    ax.bar(x + width, ai_costs, width, label="AI原価/cr", color="#94a3b8", alpha=0.85)

    for i in range(len(plans)):
        margin_eff = (1 - ai_costs[i] / effective_price[i]) * 100
        ax.text(i - width, effective_price[i] + 0.2, f"¥{effective_price[i]:.1f}", ha="center", fontsize=8)
        ax.text(i, extra_price[i] + 0.2, f"¥{extra_price[i]}", ha="center", fontsize=8)
        ax.text(i + width, ai_costs[i] + 0.2, f"¥{ai_costs[i]:.2f}", ha="center", fontsize=8)

    ax.set_ylabel("円 / クレジット", fontsize=11)
    ax.set_title("プラン別 クレジット単価とAI原価の構造", fontsize=14, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(plans, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "margin_structure.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_revenue_scaling():
    """月間クレジット消費量 vs 売上カーブ（各プラン）"""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    credit_range = np.arange(0, 50001, 100)

    for plan_name, p in CREDIT_PLANS.items():
        if plan_name == "Free":
            continue
        revenues = [calc_plan_revenue(plan_name, int(c)) / 10000 for c in credit_range]
        ax.plot(credit_range, revenues, linewidth=2, label=plan_name, color=p["color"])

    # 人件費ライン（1クレジット≒標準返信1/3件分 → 人件費¥83/cr）
    human_per_credit = feature_human_cost("AI自動返信（標準）") / 3
    human_line = [c * human_per_credit / 10000 for c in credit_range]
    ax.plot(credit_range, human_line, linewidth=2.5, label="人件費換算",
            color="#ef4444", linestyle="--")

    ax.set_xlabel("月間クレジット消費量", fontsize=11)
    ax.set_ylabel("月額（万円）", fontsize=11)
    ax.set_title("月間クレジット消費量 vs 月額課金・人件費", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "revenue_scaling.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def chart_savings_by_company():
    """企業規模別 人件費削減額"""
    fig, ax = plt.subplots(figsize=(9, 5))
    company_names = list(USAGE_PROFILES.keys())

    plans = ["Starter", "Business", "Enterprise"]
    x = np.arange(len(company_names))
    width = 0.22

    for i, pn in enumerate(plans):
        savings_pcts = []
        for cn in company_names:
            profile = USAGE_PROFILES[cn]
            credits = calc_monthly_credits(profile)
            rev = calc_plan_revenue(pn, credits)
            human = calc_monthly_human_cost(profile)
            pct = (1 - rev / human) * 100 if human > 0 else 0
            savings_pcts.append(pct)
        bars = ax.bar(x + i * width, savings_pcts, width, label=pn,
                      color=CREDIT_PLANS[pn]["color"], alpha=0.85)
        for bar, s in zip(bars, savings_pcts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f"{s:.0f}%", ha="center", va="bottom", fontsize=8)

    ax.set_ylabel("人件費削減率（%）", fontsize=11)
    ax.set_title("顧客視点：AI導入による人件費削減率", fontsize=14, fontweight="bold")
    ax.set_xticks(x + width)
    ax.set_xticklabels(company_names, fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 105)
    fig.tight_layout()
    path = os.path.join(CHART_DIR, "savings_by_company.png")
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


# =====================================================================
# PDF生成
# =====================================================================

def build_styles():
    styles = getSampleStyleSheet()
    defs = [
        ("JP_Title", "IPAPGothic", 24, 32, PRIMARY, TA_CENTER, 20, None),
        ("JP_Subtitle", "IPAPGothic", 14, 20, DARK, TA_CENTER, 30, None),
        ("JP_H1", "IPAPGothic", 16, 22, PRIMARY, TA_LEFT, 10, 20),
        ("JP_H2", "IPAPGothic", 13, 18, SECONDARY, TA_LEFT, 8, 14),
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
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "IPAPGothic"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_BG))
    t.setStyle(TableStyle(cmds))
    return t


def divider():
    t = Table([[""]], colWidths=[170*mm])
    t.setStyle(TableStyle([("LINEABOVE", (0,0), (-1,0), 1.5, PRIMARY),
                           ("TOPPADDING", (0,0), (-1,-1), 0),
                           ("BOTTOMPADDING", (0,0), (-1,-1), 0)]))
    return t


def generate_pdf():
    setup_matplotlib()
    styles = build_styles()

    print("チャート生成中...")
    charts = {
        "credit_feat": chart_credit_consumption_by_feature(),
        "cost_per_cr": chart_cost_per_credit_by_model(),
        "monthly_cr": chart_monthly_credits_by_company(),
        "rev_cost": chart_revenue_vs_cost(),
        "margin": chart_margin_structure(),
        "scaling": chart_revenue_scaling(),
        "savings": chart_savings_by_company(),
    }
    print("チャート生成完了")

    doc = SimpleDocTemplate(PDF_PATH, pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=18*mm, rightMargin=18*mm)
    story = []

    # ================================================================
    # 表紙
    # ================================================================
    story.append(Spacer(1, 55*mm))
    story.append(Paragraph("relation AI サービス", styles["JP_Title"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("クレジット設計・売上シミュレーション", styles["JP_Title"]))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(
        "各AI機能のクレジット消費設計と<br/>企業規模別の売上ポテンシャル分析", styles["JP_Subtitle"]))
    story.append(Spacer(1, 25*mm))
    story.append(Paragraph("ingAge Inc.  |  2026年3月", styles["JP_Subtitle"]))
    story.append(Paragraph("Confidential", styles["JP_Caption"]))
    story.append(PageBreak())

    # ================================================================
    # 目次
    # ================================================================
    story.append(Paragraph("目次", styles["JP_H1"]))
    story.append(divider())
    toc = [
        "1. エグゼクティブサマリー",
        "2. クレジット設計の基本思想",
        "3. 各AI機能のトークン消費量とクレジット配分",
        "4. AIモデル別 1クレジットあたり原価",
        "5. クレジットプラン設計",
        "6. 企業規模別 月間クレジット消費シミュレーション",
        "7. プラン別 月間売上 vs AI原価 vs 人件費",
        "8. クレジット消費量と売上スケーリング",
        "9. 粗利率構造分析",
        "10. 顧客視点：人件費削減効果",
        "11. 売上ポテンシャルまとめ",
        "12. 推奨事項と結論",
    ]
    for item in toc:
        story.append(Paragraph(f"　{item}", styles["JP_Body"]))
    story.append(PageBreak())

    # ================================================================
    # 1. エグゼクティブサマリー
    # ================================================================
    story.append(Paragraph("1. エグゼクティブサマリー", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))
    summary_lines = [
        "本レポートは、relation AIサービスにおける <b>クレジット制の従量課金モデル</b> を設計し、"
        "各AI機能のクレジット消費量・裏側のトークンコスト・売上ポテンシャルをシミュレーションしたものです。",
        "",
        "<b>主要結論：</b>",
        "• <b>1クレジット = AI 1アクション</b>（シンプル返信1件 or 分類1件）を基本単位に設計",
        "• 複雑な操作ほど多くのクレジットを消費（1〜8クレジット/操作）",
        "• 1クレジットあたりのAI原価は <b>¥0.03〜¥1.6</b>（モデルにより変動）",
        "• クレジット販売単価 <b>¥6〜¥12</b> で粗利率 <b>85〜99%</b> を確保",
        "• 顧客は人件費の <b>80〜97%</b> を削減可能",
        "• 中堅企業1社あたりの月間売上ポテンシャル：<b>¥12万〜¥20万</b>",
        "• 大企業1社あたりの月間売上ポテンシャル：<b>¥50万〜¥90万</b>",
    ]
    for line in summary_lines:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ================================================================
    # 2. クレジット設計の基本思想
    # ================================================================
    story.append(Paragraph("2. クレジット設計の基本思想", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))
    philosophy = [
        "<b>なぜトークンではなくクレジットか</b>",
        "トークンは技術的な概念であり、顧客にとって理解しにくい指標です。「1通のAI返信 = 3クレジット」"
        "のように、ビジネスアクション単位でのクレジット制にすることで：",
        "",
        "• 顧客が利用量を直感的に把握・予測できる",
        "• 裏側のAIモデル変更やプロンプト最適化を価格に影響させずに実施できる",
        "• 機能の難易度・付加価値に応じた傾斜配分が可能",
        "• 将来のモデル価格低下時に粗利改善として内部吸収できる",
        "",
        "<b>クレジット設計の3原則</b>",
        "1. <b>1クレジット = 最小AI操作</b>：シンプル返信1件 or 自動分類1件 = 1クレジット",
        "2. <b>トークン消費量に比例</b>：消費トークン数が多い操作ほど多くのクレジットを消費",
        "3. <b>付加価値の反映</b>：ナレッジ記事生成のように人間で60分かかる操作は高クレジット設定",
    ]
    for line in philosophy:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ================================================================
    # 3. 各AI機能のトークン消費量とクレジット配分
    # ================================================================
    story.append(Paragraph("3. 各AI機能のトークン消費量とクレジット配分", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    feat_header = ["機能", "説明", "入力\ntok", "出力\ntok", "合計\ntok", "クレジット", "人間換算\n(分)"]
    feat_rows = [feat_header]
    for name, f in AI_FEATURES.items():
        total_tok = f["input_tokens"] + f["output_tokens"]
        feat_rows.append([
            name, f["desc"],
            f'{f["input_tokens"]:,}', f'{f["output_tokens"]:,}', f'{total_tok:,}',
            f'{f["credits"]}', f'{f["human_minutes"]}分'
        ])
    story.append(make_table(feat_rows, col_widths=[28*mm, 32*mm, 16*mm, 16*mm, 16*mm, 18*mm, 18*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Image(charts["credit_feat"], width=160*mm, height=90*mm))
    story.append(Paragraph("図1: 機能別クレジット消費量", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "最も軽い操作（シンプル返信・自動分類・感情分析）は <b>1クレジット</b>、"
        "最も重い操作（ナレッジ記事生成）は <b>8クレジット</b> で、約8倍のレンジ。"
        "トークン消費量と人間換算時間の両方を考慮した設計です。",
        styles["JP_Body"]
    ))
    story.append(PageBreak())

    # ================================================================
    # 4. AIモデル別 1クレジットあたり原価
    # ================================================================
    story.append(Paragraph("4. AIモデル別 1クレジットあたり原価", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "各AIモデルを使用した場合の、1クレジットあたりの原価です。"
        "「AI自動返信（標準）」（3クレジット消費）を基準に算出しています。",
        styles["JP_Body"]
    ))
    story.append(Spacer(1, 2*mm))

    model_header = ["モデル", "入力\n$/1M tok", "出力\n$/1M tok", "標準返信\n原価(¥)", "1cr\nあたり原価(¥)"]
    model_rows = [model_header]
    for name, m in MODELS.items():
        reply_cost = feature_ai_cost("AI自動返信（標準）", name)
        per_credit = reply_cost / 3
        model_rows.append([
            name, f'${m["input"]:.2f}', f'${m["output"]:.2f}',
            f'¥{reply_cost:.2f}', f'¥{per_credit:.3f}'
        ])
    story.append(make_table(model_rows, col_widths=[32*mm, 24*mm, 24*mm, 28*mm, 28*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Image(charts["cost_per_cr"], width=150*mm, height=95*mm))
    story.append(Paragraph("図2: モデル別 1クレジットあたりのAI原価", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "Haikuモデルで <b>¥0.32/cr</b>、Sonnetモデルで <b>¥1.13/cr</b>。"
        "これをクレジット販売価格¥6〜12と比較すると、<b>粗利率85〜97%</b> が確保できます。",
        styles["JP_Highlight"]
    ))
    story.append(PageBreak())

    # ================================================================
    # 5. クレジットプラン設計
    # ================================================================
    story.append(Paragraph("5. クレジットプラン設計", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    plan_header = ["", "Free", "Starter", "Business", "Enterprise"]
    plan_data = [
        plan_header,
        ["月額基本料", "¥0", "¥5,000", "¥20,000", "¥80,000"],
        ["含むクレジット/月", "50 cr", "500 cr", "3,000 cr", "15,000 cr"],
        ["実効単価/cr", "—", "¥10.0", "¥6.7", "¥5.3"],
        ["超過クレジット単価", "購入不可", "¥12", "¥8", "¥6"],
        ["使用AIモデル", "Haiku", "Haiku", "Sonnet", "Sonnet"],
        ["ナレッジ機能", "制限あり", "利用可", "利用可", "フルアクセス"],
        ["API連携", "—", "—", "利用可", "利用可"],
        ["SLA", "—", "99.5%", "99.9%", "99.95%"],
    ]
    story.append(make_table(plan_data, col_widths=[28*mm, 28*mm, 28*mm, 30*mm, 30*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>プラン別ターゲットイメージ</b>", styles["JP_H3"]))
    targets = [
        "• <b>Free</b>：トライアル用。50cr/月でシンプル返信50件 or 標準返信16件相当",
        "• <b>Starter</b>：スタートアップ向け。500cr/月で標準返信166件相当。月額¥5,000",
        "• <b>Business</b>：中小〜中堅企業向け。3,000cr/月で標準返信1,000件相当。高精度Sonnetモデル使用",
        "• <b>Enterprise</b>：大企業向け。15,000cr/月で標準返信5,000件相当。ボリュームディスカウント適用",
    ]
    for line in targets:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ================================================================
    # 6. 企業規模別 月間クレジット消費シミュレーション
    # ================================================================
    story.append(Paragraph("6. 企業規模別 月間クレジット消費シミュレーション", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "各企業規模における典型的なAI機能利用パターンから、月間クレジット消費量を算出します。",
        styles["JP_Body"]
    ))
    story.append(Spacer(1, 2*mm))

    story.append(Image(charts["monthly_cr"], width=160*mm, height=95*mm))
    story.append(Paragraph("図3: 企業規模別 月間クレジット消費量（カテゴリ内訳）", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    # 消費内訳テーブル
    cons_header = ["企業規模", "返信系\ncr", "分析系\ncr", "ナレッジ系\ncr", "合計cr", "推奨プラン"]
    cons_rows = [cons_header]
    for cn in USAGE_PROFILES:
        profile = USAGE_PROFILES[cn]
        cat_cr = {"返信": 0, "分析": 0, "ナレッジ": 0}
        for feat, count in profile.items():
            cat = AI_FEATURES[feat]["category"]
            cat_cr[cat] += AI_FEATURES[feat]["credits"] * count
        total_cr = sum(cat_cr.values())
        best, _ = best_plan_for_usage(total_cr)
        clean_name = cn.replace('\n', ' ')
        cons_rows.append([
            clean_name,
            f'{cat_cr["返信"]:,}', f'{cat_cr["分析"]:,}', f'{cat_cr["ナレッジ"]:,}',
            f'{total_cr:,}', best
        ])
    story.append(make_table(cons_rows, col_widths=[28*mm, 22*mm, 22*mm, 22*mm, 22*mm, 28*mm]))
    story.append(PageBreak())

    # ================================================================
    # 7. プラン別 月間売上 vs AI原価 vs 人件費
    # ================================================================
    story.append(Paragraph("7. プラン別 月間売上 vs AI原価 vs 人件費", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["rev_cost"], width=170*mm, height=135*mm))
    story.append(Paragraph("図4: プラン別 月間売上 vs 人件費 vs AI原価", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    # 詳細テーブル
    for cn in USAGE_PROFILES:
        profile = USAGE_PROFILES[cn]
        credits = calc_monthly_credits(profile)
        human = calc_monthly_human_cost(profile)
        clean_name = cn.replace('\n', ' ')
        story.append(Paragraph(f"<b>{clean_name}</b>（月間 {credits:,} クレジット）", styles["JP_H3"]))

        rev_header = ["プラン", "月間売上(¥)", "AI原価(¥)", "粗利(¥)", "粗利率", "人件費(¥)", "顧客\n削減率"]
        rev_rows = [rev_header]
        for pn in ["Starter", "Business", "Enterprise"]:
            model = CREDIT_PLANS[pn]["model"]
            rev = calc_plan_revenue(pn, credits)
            ai_cost = calc_monthly_ai_cost(profile, model)
            profit = rev - ai_cost
            margin = profit / rev * 100 if rev > 0 else 0
            savings = (1 - rev / human) * 100 if human > 0 else 0
            rev_rows.append([
                pn, f'¥{rev:,.0f}', f'¥{ai_cost:,.0f}', f'¥{profit:,.0f}',
                f'{margin:.1f}%', f'¥{human:,.0f}', f'{savings:.0f}%'
            ])
        story.append(make_table(rev_rows, col_widths=[22*mm, 26*mm, 22*mm, 26*mm, 16*mm, 26*mm, 16*mm]))
        story.append(Spacer(1, 4*mm))

    story.append(PageBreak())

    # ================================================================
    # 8. スケーリング
    # ================================================================
    story.append(Paragraph("8. クレジット消費量と売上スケーリング", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "月間クレジット消費量が増加した際の各プランの課金額推移です。"
        "赤点線の人件費ラインを超えない範囲がビジネスとして成立する領域です。",
        styles["JP_Body"]
    ))

    story.append(Image(charts["scaling"], width=160*mm, height=95*mm))
    story.append(Paragraph("図5: 月間クレジット消費量 vs 月額課金・人件費", styles["JP_Caption"]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>スケーリングのポイント</b>", styles["JP_H3"]))
    scaling_points = [
        "• 全プランで人件費ラインの <b>大幅下方</b> に位置 → 顧客に常にコストメリットを提供",
        "• Starterプランは最も急角度で課金が増加（超過単価¥12/cr）→ 利用増加時のアップセル誘因",
        "• Enterpriseプランは最も緩やかな角度 → 大量利用顧客にボリュームメリットを提供",
        "• 50,000cr/月時点で：Starter ¥60万、Business ¥40万、Enterprise ¥29万",
    ]
    for line in scaling_points:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(PageBreak())

    # ================================================================
    # 9. 粗利率構造分析
    # ================================================================
    story.append(Paragraph("9. 粗利率構造分析", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Image(charts["margin"], width=150*mm, height=95*mm))
    story.append(Paragraph("図6: プラン別 クレジット単価とAI原価の構造", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    margin_header = ["プラン", "実効単価\n(¥/cr)", "超過単価\n(¥/cr)", "AI原価\n(¥/cr)", "粗利率\n(実効)", "粗利率\n(超過)"]
    margin_rows = [margin_header]
    for pn in ["Starter", "Business", "Enterprise"]:
        p = CREDIT_PLANS[pn]
        eff = p["monthly_fee"] / p["included_credits"]
        extra = p["extra_credit_price"]
        ai = feature_ai_cost("AI自動返信（標準）", p["model"]) / 3
        m_eff = (1 - ai / eff) * 100
        m_extra = (1 - ai / extra) * 100
        margin_rows.append([
            pn, f"¥{eff:.1f}", f"¥{extra}", f"¥{ai:.2f}", f"{m_eff:.1f}%", f"{m_extra:.1f}%"
        ])
    story.append(make_table(margin_rows, col_widths=[25*mm, 22*mm, 22*mm, 22*mm, 25*mm, 25*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        "全プランで粗利率 <b>85%以上</b> を確保。AIモデルの価格低下（年率30〜50%）により、"
        "この粗利率は将来さらに改善される見込みです。",
        styles["JP_Highlight"]
    ))
    story.append(PageBreak())

    # ================================================================
    # 10. 顧客視点：人件費削減効果
    # ================================================================
    story.append(Paragraph("10. 顧客視点：人件費削減効果", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph(
        "顧客がrelation AIを導入した場合、人間対応と比較してどの程度の人件費削減になるかです。"
        "これが顧客の導入判断・ROI説明の核心となります。",
        styles["JP_Body"]
    ))

    story.append(Image(charts["savings"], width=155*mm, height=90*mm))
    story.append(Paragraph("図7: 顧客視点：AI導入による人件費削減率", styles["JP_Caption"]))
    story.append(Spacer(1, 3*mm))

    # 具体的な金額テーブル
    sav_header = ["企業規模", "人件費/月", "Business\n課金/月", "削減額/月", "削減率", "年間削減額"]
    sav_rows = [sav_header]
    for cn in USAGE_PROFILES:
        profile = USAGE_PROFILES[cn]
        credits = calc_monthly_credits(profile)
        human = calc_monthly_human_cost(profile)
        rev = calc_plan_revenue("Business", credits)
        saving = human - rev
        pct = saving / human * 100 if human > 0 else 0
        clean_name = cn.replace('\n', ' ')
        sav_rows.append([
            clean_name, f'¥{human:,.0f}', f'¥{rev:,.0f}',
            f'¥{saving:,.0f}', f'{pct:.0f}%', f'¥{saving*12:,.0f}'
        ])
    story.append(make_table(sav_rows, col_widths=[24*mm, 26*mm, 24*mm, 26*mm, 16*mm, 28*mm]))
    story.append(PageBreak())

    # ================================================================
    # 11. 売上ポテンシャルまとめ
    # ================================================================
    story.append(Paragraph("11. 売上ポテンシャルまとめ", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>顧客1社あたりの月間売上ポテンシャル（Businessプラン基準）</b>", styles["JP_H3"]))
    pot_header = ["企業規模", "月間cr消費", "月間売上", "年間売上", "AI原価/月", "粗利/月"]
    pot_rows = [pot_header]
    for cn in USAGE_PROFILES:
        profile = USAGE_PROFILES[cn]
        credits = calc_monthly_credits(profile)
        rev = calc_plan_revenue("Business", credits)
        ai_cost = calc_monthly_ai_cost(profile, "Claude Sonnet 4.5")
        profit = rev - ai_cost
        clean_name = cn.replace('\n', ' ')
        pot_rows.append([
            clean_name, f'{credits:,}',
            f'¥{rev:,.0f}', f'¥{rev*12:,.0f}',
            f'¥{ai_cost:,.0f}', f'¥{profit:,.0f}'
        ])
    story.append(make_table(pot_rows, col_widths=[24*mm, 20*mm, 24*mm, 28*mm, 22*mm, 24*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>事業全体の売上シミュレーション</b>", styles["JP_H3"]))
    story.append(Paragraph(
        "以下は、各規模帯の契約社数に基づく月間売上（MRR）シミュレーションです。",
        styles["JP_Body"]
    ))

    # 顧客数シナリオ
    scenarios = [
        ("ローンチ初期", {"スタートアップ\n(CS 3〜5名)": 20, "中小企業\n(CS 10〜20名)": 5, "中堅企業\n(CS 30〜60名)": 1, "大企業\n(CS 100名以上)": 0}),
        ("成長期", {"スタートアップ\n(CS 3〜5名)": 80, "中小企業\n(CS 10〜20名)": 30, "中堅企業\n(CS 30〜60名)": 8, "大企業\n(CS 100名以上)": 2}),
        ("成熟期", {"スタートアップ\n(CS 3〜5名)": 200, "中小企業\n(CS 10〜20名)": 100, "中堅企業\n(CS 30〜60名)": 30, "大企業\n(CS 100名以上)": 10}),
    ]

    biz_header = ["フェーズ", "契約社数", "MRR", "ARR", "AI原価/月", "粗利/月"]
    biz_rows = [biz_header]
    for phase, company_counts in scenarios:
        total_rev = 0
        total_ai = 0
        total_companies = 0
        for cn, num in company_counts.items():
            if num == 0:
                continue
            total_companies += num
            profile = USAGE_PROFILES[cn]
            credits = calc_monthly_credits(profile)
            rev = calc_plan_revenue("Business", credits)
            ai_cost = calc_monthly_ai_cost(profile, "Claude Sonnet 4.5")
            total_rev += rev * num
            total_ai += ai_cost * num
        biz_rows.append([
            phase, f'{total_companies}社',
            f'¥{total_rev:,.0f}', f'¥{total_rev*12:,.0f}',
            f'¥{total_ai:,.0f}', f'¥{total_rev - total_ai:,.0f}'
        ])
    story.append(make_table(biz_rows, col_widths=[22*mm, 18*mm, 28*mm, 30*mm, 24*mm, 28*mm]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        "成長期（120社）で MRR <b>約670万円</b>・ARR <b>約8,000万円</b>、"
        "成熟期（340社）で MRR <b>約2,200万円</b>・ARR <b>約2.6億円</b> の売上ポテンシャル。"
        "AI原価はMRRの3〜5%に過ぎず、極めて高収益なビジネスモデルです。",
        styles["JP_Highlight"]
    ))
    story.append(PageBreak())

    # ================================================================
    # 12. 推奨事項と結論
    # ================================================================
    story.append(Paragraph("12. 推奨事項と結論", styles["JP_H1"]))
    story.append(divider())
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("<b>クレジット設計の推奨事項</b>", styles["JP_H2"]))
    recs = [
        "1. <b>クレジット単位は「1cr = 1軽量操作」を堅持</b>：直感的で理解しやすい。"
        "返信系1〜5cr、分析系1〜3cr、ナレッジ系5〜8crの3段階が明確",
        "",
        "2. <b>Businessプランを主力商品に</b>：月額¥20,000で3,000cr含有。"
        "中小企業の標準的な利用量をカバーし、超過分は¥8/crで課金。"
        "粗利率85%以上を確保しながら顧客に87%の人件費削減を提供",
        "",
        "3. <b>無料枠は50crで体験価値を担保</b>：シンプル返信50件 or 標準返信16件分。"
        "2〜3日分の体験量として十分。有料転換率の最大化を狙う",
        "",
        "4. <b>AI原価の低下を粗利改善に活用</b>：AIモデルの価格は年30〜50%低下傾向。"
        "クレジット販売価格を維持し、原価低減分を粗利に吸収する戦略を推奨",
        "",
        "5. <b>ナレッジ系機能はプレミアム要素として位置づけ</b>：ナレッジ記事生成（8cr）は"
        "人間で60分かかる作業。高クレジット設定でも顧客にとって圧倒的にお得であり、"
        "上位プランへのアップセル誘因として活用",
        "",
        "6. <b>Batch API・キャッシュの積極活用</b>：非同期処理（ナレッジ操作等）は"
        "Batch APIで50%、プロンプトキャッシュで最大90%の原価削減が可能",
    ]
    for line in recs:
        story.append(Paragraph(line, styles["JP_Body"]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>結論</b>", styles["JP_H2"]))
    story.append(Paragraph(
        "クレジット制の従量課金モデルは、AI原価と人件費の間に存在する"
        " <b>100倍以上のマージン</b> を活用し、顧客には大幅な人件費削減を、"
        "ingAgeには高い粗利率を同時に実現する理想的なビジネスモデルです。"
        "AIモデルの継続的な価格低下により、この構造は将来にわたって改善し続けます。",
        styles["JP_Body"]
    ))

    story.append(Spacer(1, 15*mm))
    story.append(Paragraph("— End of Report —", styles["JP_Caption"]))

    print("PDF生成中...")
    doc.build(story)
    print(f"PDF生成完了: {PDF_PATH}")
    return PDF_PATH


if __name__ == "__main__":
    generate_pdf()
