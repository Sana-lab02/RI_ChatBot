import pandas as pd
import sqlite3

# -----------------------------
# CONFIG
# -----------------------------
DB_PATH = "retailers.db"   # <-- your actual DB path
EXCEL_PATH = "/Users/phood/downloads/company_with_dates.xlsx"  # <-- your Excel file

# -----------------------------
# CONNECT
# -----------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -----------------------------
# LOAD EXCEL
# -----------------------------
df = pd.read_excel(EXCEL_PATH)

# Rename to match expectations
df = df.rename(columns={
    "company_clean": "retailer",
    "date_list": "date_list"
})

df = df.dropna(subset=["retailer", "date_list"])

# Normalize retailer
df["retailer"] = df["retailer"].str.strip()

# -----------------------------
# EXPAND DATE LIST
# -----------------------------
df_expanded = (
    df.assign(scan_date=df["date_list"].str.split(r",\s*"))
      .explode("scan_date")
)

df_expanded["scan_date"] = pd.to_datetime(
    df_expanded["scan_date"], errors="coerce"
).dt.date

df_expanded = df_expanded.dropna(subset=["scan_date"])

print(f"📊 Rows to insert: {len(df_expanded)}")

# -----------------------------
# OPTIONAL: DUPLICATE CHECK
# -----------------------------
cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_scan
    ON scan_events (retailer, scan_date)
""")

# -----------------------------
# INSERT
# -----------------------------
inserted = 0
skipped = 0

for _, row in df_expanded.iterrows():
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO scan_events (retailer, scan_date) VALUES (?, ?)",
            (row["retailer"], row["scan_date"])
        )
        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    except Exception as e:
        print("❌ Error:", e)

conn.commit()
conn.close()

print(f"✅ Inserted: {inserted}")
print(f"⚠️ Skipped duplicates: {skipped}")
