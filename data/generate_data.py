import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta, date

fake = Faker()

# CHANGED: Faker 40.23.0 has a confirmed bug where relative date strings
# (e.g. start_date="-24m", end_date="-1m") collapse to today's date on
# every call instead of producing a spread. Fix: compute explicit date
# objects in Python and pass those to fake.date_between instead of strings.
TODAY = date.today()

# --- Config ---
N_REPS = 20
N_DEALS = 5000
N_MONTHS = 18
DB_PATH = "data/finance_sales.db"

REGIONS = ["North", "South", "East", "West"]
TEAMS = ["Enterprise", "SMB", "Mid-Market"]
STAGES = ["Prospecting", "Qualified", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
STAGE_WEIGHTS = [0.15, 0.20, 0.20, 0.15, 0.20, 0.10]
EXPENSE_CATEGORIES = ["Salaries", "Marketing", "Travel", "Software", "Operations"]
DEPARTMENTS = ["Sales", "Marketing", "Engineering", "Finance", "HR"]

PRODUCTS = [
    (1, "Analytics Pro",    "SaaS",     1200,  0.75),
    (2, "Data Pipeline",    "SaaS",     2500,  0.70),
    (3, "BI Dashboard",     "SaaS",      800,  0.80),
    (4, "Implementation",   "Services", 5000,  0.40),
    (5, "Training Package", "Services", 2000,  0.50),
    (6, "Data Appliance",   "Hardware", 8000,  0.35),
]

# --- Helpers ---
def get_quarter(date_obj) -> str:
    q = (date_obj.month - 1) // 3 + 1
    return f"{date_obj.year}-Q{q}"

def get_period(date_obj) -> str:
    return date_obj.strftime("%Y-%m")

# --- Generators ---
def generate_reps():
    reps = []
    for i in range(1, N_REPS + 1):
        region    = random.choice(REGIONS)
        team      = random.choice(TEAMS)
        quota     = random.choice([800000, 1000000, 1200000, 1500000, 2000000])
        # CHANGED: explicit date objects instead of "-3y"/"-6m" strings
        hire_start = TODAY - timedelta(days=1095)  # ~3 years
        hire_end   = TODAY - timedelta(days=180)   # ~6 months
        hire_date = fake.date_between(start_date=hire_start, end_date=hire_end)
        reps.append((i, fake.name(), region, team, quota, str(hire_date)))
    return reps

def generate_deals(reps):
    deals = []
    for i in range(1, N_DEALS + 1):
        rep                        = random.choice(reps)
        rep_id, _, region, _, _, _ = rep
        stage      = random.choices(STAGES, weights=STAGE_WEIGHTS)[0]
        product_id = random.randint(1, len(PRODUCTS))
        base_price = PRODUCTS[product_id - 1][3]
        deal_value = round(base_price * random.uniform(0.8, 3.0) * random.randint(1, 10), 2)
        # CHANGED: explicit date objects instead of "-24m"/"-1m" strings.
        # This is the actual fix for the bug — string ranges were silently
        # collapsing to today's date on every call in Faker 40.23.0.
        created_start = TODAY - timedelta(days=730)  # ~24 months
        created_end   = TODAY - timedelta(days=30)   # ~1 month
        created    = fake.date_between(start_date=created_start, end_date=created_end)
        close      = created + timedelta(days=random.randint(14, 120))
        quarter    = get_quarter(close)
        deals.append((
            i, rep_id, fake.company(), stage, deal_value,
            str(close), str(created), quarter, product_id, region
        ))
    return deals

def generate_revenue(deals):
    periods_by_region_product = {}
    for deal in deals:
        region     = deal[9]
        product_id = deal[8]
        period     = deal[5][:7]
        quarter    = deal[7]
        key        = (period, quarter, region, product_id)
        if key not in periods_by_region_product:
            periods_by_region_product[key] = []
        periods_by_region_product[key].append(deal[4])

    revenue = []
    rev_id  = 1
    for (period, quarter, region, product_id), values in periods_by_region_product.items():
        base           = sum(values)
        actual_revenue = round(base * random.uniform(0.85, 1.15), 2)
        target_revenue = round(base * random.uniform(0.80, 1.20), 2)
        actual_units   = random.randint(5, 80)
        target_units   = random.randint(5, 80)
        revenue.append((
            rev_id, period, quarter, region, product_id,
            actual_revenue, target_revenue, actual_units, target_units
        ))
        rev_id += 1
    return revenue

def generate_expenses(deals):
    periods = list(set(d[5][:7] for d in deals))

    expenses = []
    exp_id   = 1
    for period in sorted(periods):
        year, month = int(period[:4]), int(period[5:7])
        q           = (month - 1) // 3 + 1
        quarter     = f"{year}-Q{q}"
        for cat in EXPENSE_CATEGORIES:
            for dept in DEPARTMENTS:
                budget = round(random.uniform(5000, 50000), 2)
                actual = round(budget * random.uniform(0.75, 1.25), 2)
                expenses.append((exp_id, period, quarter, cat, dept, actual, budget))
                exp_id += 1
    return expenses

# --- Write to SQLite ---
def write_db(reps, deals, revenue, expenses):
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    c.executescript("""
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS reps;
        DROP TABLE IF EXISTS deals;
        DROP TABLE IF EXISTS revenue;
        DROP TABLE IF EXISTS expenses;

        CREATE TABLE products (
            product_id  INTEGER PRIMARY KEY,
            name        TEXT,
            category    TEXT,
            unit_price  REAL,
            margin_pct  REAL
        );
        CREATE TABLE reps (
            rep_id      INTEGER PRIMARY KEY,
            name        TEXT,
            region      TEXT,
            team        TEXT,
            quota       REAL,
            hire_date   DATE
        );
        CREATE TABLE deals (
            deal_id         INTEGER PRIMARY KEY,
            rep_id          INTEGER REFERENCES reps(rep_id),
            company_name    TEXT,
            stage           TEXT,
            deal_value      REAL,
            close_date      DATE,
            created_date    DATE,
            quarter         TEXT,
            product_id      INTEGER REFERENCES products(product_id),
            region          TEXT
        );
        CREATE TABLE revenue (
            revenue_id      INTEGER PRIMARY KEY,
            period          TEXT,
            quarter         TEXT,
            region          TEXT,
            product_id      INTEGER REFERENCES products(product_id),
            actual_revenue  REAL,
            target_revenue  REAL,
            actual_units    INTEGER,
            target_units    INTEGER
        );
        CREATE TABLE expenses (
            expense_id      INTEGER PRIMARY KEY,
            period          TEXT,
            quarter         TEXT,
            category        TEXT,
            department      TEXT,
            actual_amount   REAL,
            budget_amount   REAL
        );
    """)

    c.executemany("INSERT INTO products VALUES (?,?,?,?,?)",    PRODUCTS)
    c.executemany("INSERT INTO reps     VALUES (?,?,?,?,?,?)",  reps)
    c.executemany("INSERT INTO deals    VALUES (?,?,?,?,?,?,?,?,?,?)", deals)
    c.executemany("INSERT INTO revenue  VALUES (?,?,?,?,?,?,?,?,?)",  revenue)
    c.executemany("INSERT INTO expenses VALUES (?,?,?,?,?,?,?)", expenses)

    conn.commit()
    conn.close()

    print(f"DB written to {DB_PATH}")
    print(f"Products : {len(PRODUCTS)}")
    print(f"Reps     : {len(reps)}")
    print(f"Deals    : {len(deals)}")
    print(f"Revenue  : {len(revenue)}")
    print(f"Expenses : {len(expenses)}")

if __name__ == "__main__":
    reps     = generate_reps()
    deals    = generate_deals(reps)
    revenue  = generate_revenue(deals)
    expenses = generate_expenses(deals)
    write_db(reps, deals, revenue, expenses)