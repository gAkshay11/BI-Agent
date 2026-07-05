import sqlite3

DB_PATH = "data/finance_sales.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def run(label, sql):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    c.execute(sql)
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    print("  " + " | ".join(cols))
    print("  " + "-" * 50)
    for row in rows:
        print("  " + " | ".join(str(v) for v in row))

# 1. Row counts
run("1. Row Counts", """
    SELECT 'products' as tbl, COUNT(*) as count FROM products UNION ALL
    SELECT 'reps',    COUNT(*) FROM reps    UNION ALL
    SELECT 'deals',   COUNT(*) FROM deals   UNION ALL
    SELECT 'revenue', COUNT(*) FROM revenue UNION ALL
    SELECT 'expenses',COUNT(*) FROM expenses
""")

# 2. Stage distribution
run("2. Stage Distribution", """
    SELECT stage, COUNT(*) as count, ROUND(SUM(deal_value),2) as total_value
    FROM deals GROUP BY stage ORDER BY count DESC
""")

# 3. Revenue vs target by region
run("3. Revenue vs Target by Region", """
    SELECT region, ROUND(SUM(actual_revenue),2) as actual,
           ROUND(SUM(target_revenue),2) as target,
           ROUND(SUM(actual_revenue)/SUM(target_revenue)*100,1) as attainment_pct
    FROM revenue GROUP BY region
""")

# 4. Top 5 reps by closed won
run("4. Top 5 Reps by Closed Won", """
    SELECT r.name, r.region, ROUND(SUM(d.deal_value),2) as closed_value
    FROM deals d JOIN reps r ON d.rep_id = r.rep_id
    WHERE d.stage = 'Closed Won'
    GROUP BY r.rep_id ORDER BY closed_value DESC LIMIT 5
""")

# 5. Budget variance by category
run("5. Budget Variance by Category", """
    SELECT category, ROUND(SUM(actual_amount),2) as actual,
           ROUND(SUM(budget_amount),2) as budget,
           ROUND((SUM(actual_amount)-SUM(budget_amount))/SUM(budget_amount)*100,1) as variance_pct
    FROM expenses GROUP BY category
""")

# 6. Monthly revenue trend
run("6. Monthly Revenue Trend", """
    SELECT period, ROUND(SUM(actual_revenue),2) as revenue
    FROM revenue GROUP BY period ORDER BY period
""")

# 7. Win rate by team
run("7. Win Rate by Team", """
    SELECT r.team,
           COUNT(CASE WHEN d.stage = 'Closed Won' THEN 1 END) as won,
           COUNT(*) as total,
           ROUND(COUNT(CASE WHEN d.stage='Closed Won' THEN 1 END)*100.0/COUNT(*),1) as win_rate
    FROM deals d JOIN reps r ON d.rep_id = r.rep_id
    GROUP BY r.team
""")

# 8. Product margin analysis
run("8. Product Margin Analysis", """
    SELECT p.name, p.category, p.margin_pct,
           COUNT(d.deal_id) as deals, ROUND(SUM(d.deal_value),2) as revenue
    FROM products p LEFT JOIN deals d ON p.product_id = d.product_id
    GROUP BY p.product_id
""")

# 9. Quota attainment by rep
run("9. Quota Attainment by Rep", """
    SELECT r.name, r.quota,
           ROUND(SUM(CASE WHEN d.stage='Closed Won' THEN d.deal_value ELSE 0 END),2) as attained,
           ROUND(SUM(CASE WHEN d.stage='Closed Won' THEN d.deal_value ELSE 0 END)/r.quota*100,1) as pct
    FROM reps r LEFT JOIN deals d ON r.rep_id = d.rep_id
    GROUP BY r.rep_id ORDER BY pct DESC
""")

# 10. Over-budget departments
run("10. Over-Budget Departments", """
    SELECT department, ROUND(SUM(actual_amount),2) as actual,
           ROUND(SUM(budget_amount),2) as budget,
           ROUND(SUM(actual_amount)-SUM(budget_amount),2) as overage
    FROM expenses GROUP BY department HAVING actual > budget ORDER BY overage DESC
""")

# 11. Revenue vs Expenses by Quarter — FIXED to aggregate before joining,
# removing the cartesian-product bug from the original 5-table join
# (which multiplied every deal row by every expense row sharing a quarter).
run("11. Revenue vs Expenses by Quarter", """
    SELECT rev.quarter,
           ROUND(rev.total_revenue, 2) AS total_revenue,
           ROUND(exp.total_expenses, 2) AS total_expenses
    FROM (SELECT quarter, SUM(actual_revenue) AS total_revenue FROM revenue GROUP BY quarter) rev
    JOIN (SELECT quarter, SUM(actual_amount) AS total_expenses FROM expenses GROUP BY quarter) exp
    ON rev.quarter = exp.quarter
    ORDER BY rev.quarter
""")

conn.close()
print("\n✅ All queries complete.")