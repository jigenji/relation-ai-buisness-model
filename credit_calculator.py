#!/usr/bin/env python3
"""
relation AI クレジット算出公式

使い方:
  # 単体計算
  python3 credit_calculator.py --time 10
  python3 credit_calculator.py --time 60 --ai-cost 15.0
  python3 credit_calculator.py --time 10 --ai-cost 3.4 --verbose

  # 一括計算（JSON）
  python3 credit_calculator.py --batch features.json
"""

import math
import json
import argparse

# ===========================================================================
# 定数
# ===========================================================================
FTE_HOURLY_COST = 2865          # CS担当の時給（¥5,500,000 / 240日 / 8h）
BASE_MINUTES_PER_CREDIT = 3.0  # 1クレジットの基準 = 人間3分の作業価値

# プラン別クレジット単価（月額 ÷ 含有クレジット）
PLAN_CREDIT_PRICES = {
    "Growth":          {"price": 46, "extra": 25, "capture_rate": 0.20},
    "Scale":           {"price": 40, "extra": 22, "capture_rate": 0.25},
    "Enterprise":      {"price": 39, "extra": 18, "capture_rate": 0.30},
    "Enterprise Plus": {"price": 46, "extra": 15, "capture_rate": 0.35},
}


# ===========================================================================
# 公式
# ===========================================================================

def calc_credits(time_saved_minutes: float, ai_cost_jpy: float = 0) -> int:
    """
    ┌─────────────────────────────────────────────────┐
    │                                                 │
    │  クレジット = max(                               │
    │      max(1, round(削減時間 / 3)),               │
    │      ceil(AI原価 / 15)   ← コスト回収下限       │
    │  )                                              │
    │                                                 │
    │  削減時間: その機能で削減される人間の作業時間(分)  │
    │  AI原価:   その機能1回のAPIコスト(円)            │
    │  3:        基準値 = 3分/クレジット               │
    │  15:       最低クレジット単価(円) = Ent Plus超過  │
    │                                                 │
    └─────────────────────────────────────────────────┘
    """
    # ① 価値ベース: 削減時間 ÷ 3分
    value_credits = max(1, round(time_saved_minutes / BASE_MINUTES_PER_CREDIT))

    # ② コスト回収下限: AI原価が高い場合に赤字にならないガード
    cost_floor = math.ceil(ai_cost_jpy / 15) if ai_cost_jpy > 0 else 0

    return max(value_credits, cost_floor)


def calc_pricing(credits: int, time_saved_minutes: float, ai_cost_jpy: float = 0):
    """クレジット数からプラン別の売上・利益を算出"""
    human_value = time_saved_minutes / 60 * FTE_HOURLY_COST
    results = {}
    for plan, p in PLAN_CREDIT_PRICES.items():
        revenue = credits * p["price"]
        revenue_extra = credits * p["extra"]
        margin = revenue - ai_cost_jpy
        margin_extra = revenue_extra - ai_cost_jpy
        results[plan] = {
            "revenue_included": revenue,
            "revenue_extra": revenue_extra,
            "margin_included": margin,
            "margin_extra": margin_extra,
            "margin_pct": margin / revenue * 100 if revenue > 0 else 0,
            "vs_human": revenue / human_value * 100 if human_value > 0 else 0,
            "vs_human_extra": revenue_extra / human_value * 100 if human_value > 0 else 0,
        }
    return results, human_value


# ===========================================================================
# CLI
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="relation AI クレジット算出公式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  %(prog)s --time 10                  # 10分削減する機能
  %(prog)s --time 60 --ai-cost 15.0   # 60分削減、AI原価¥15の機能
  %(prog)s --time 5 --verbose          # 詳細表示
        """)
    parser.add_argument("--time", "-t", type=float, required=False,
                        help="削減時間（分）")
    parser.add_argument("--ai-cost", "-c", type=float, default=0,
                        help="AI原価（円/回）。省略時は0")
    parser.add_argument("--batch", "-b", type=str, default=None,
                        help="JSON一括計算ファイルパス")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="詳細表示")
    args = parser.parse_args()

    if args.batch:
        run_batch(args.batch)
        return

    T = args.time
    AI = args.ai_cost
    credits = calc_credits(T, AI)
    pricing, human_value = calc_pricing(credits, T, AI)

    print()
    print("=" * 60)
    print(f"  削減時間:  {T:.1f} 分")
    print(f"  AI原価:    ¥{AI:.1f}")
    print(f"  人件費換算: ¥{human_value:,.0f}")
    print(f"  ─────────────────────────────")
    print(f"  → クレジット消費:  {credits} cr")
    print("=" * 60)

    if args.verbose:
        print()
        print("  公式:")
        print(f"    価値ベース = max(1, round({T} / {BASE_MINUTES_PER_CREDIT})) = {max(1, round(T / BASE_MINUTES_PER_CREDIT))}")
        if AI > 0:
            print(f"    コスト下限 = ceil({AI} / 15) = {math.ceil(AI / 15)}")
        print(f"    クレジット = max(価値ベース, コスト下限) = {credits}")

    print()
    print(f"  {'プラン':<18} {'含有cr単価':>9} {'超過cr単価':>9} {'人件費比':>7}")
    print(f"  {'─'*50}")
    for plan, r in pricing.items():
        print(f"  {plan:<18} ¥{r['revenue_included']:>7,} ¥{r['revenue_extra']:>7,} {r['vs_human']:.0f}%")

    print()
    if AI > 0:
        print(f"  粗利率（含有cr単価ベース）:")
        for plan, r in pricing.items():
            print(f"    {plan}: {r['margin_pct']:.1f}%")
        print()

    # 判定
    best_extra_pct = min(r["vs_human_extra"] for r in pricing.values())
    if best_extra_pct > 50:
        print(f"  ⚠ 人件費比が高い（最低{best_extra_pct:.0f}%）。クレジット数を下げるか要検討")
    elif best_extra_pct < 10:
        print(f"  ⚠ 人件費比が低い（最低{best_extra_pct:.0f}%）。クレジット数を上げる余地あり")
    else:
        print(f"  ✓ 人件費比 {best_extra_pct:.0f}% — 顧客にとって納得感のある価格帯")


def run_batch(filepath):
    """
    JSONファイルから複数機能を一括計算

    JSONフォーマット:
    [
      {"name": "AI自動返信（標準）", "time": 10, "ai_cost": 3.4},
      {"name": "ナレッジ記事生成",   "time": 60, "ai_cost": 15.0},
      ...
    ]
    """
    with open(filepath, "r") as f:
        features = json.load(f)

    print()
    print("=" * 72)
    print("  機能一覧 クレジット算出結果")
    print("=" * 72)
    print()
    header = f"  {'機能名':<24} {'削減時間':>6} {'AI原価':>7} {'cr':>4} {'人件費換算':>8} {'Ent単価':>8}"
    print(header)
    print(f"  {'─'*66}")

    total_credits = 0
    for feat in features:
        name = feat["name"]
        t = feat["time"]
        ai = feat.get("ai_cost", 0)
        cr = calc_credits(t, ai)
        human = t / 60 * FTE_HOURLY_COST
        ent_price = cr * PLAN_CREDIT_PRICES["Enterprise"]["extra"]
        total_credits += cr
        print(f"  {name:<24} {t:>5.0f}分 ¥{ai:>6.1f} {cr:>3} cr ¥{human:>7,.0f} ¥{ent_price:>6,}")

    print(f"  {'─'*66}")
    print(f"  {'合計':<24} {'':>6} {'':>7} {total_credits:>3} cr")
    print()


if __name__ == "__main__":
    main()
