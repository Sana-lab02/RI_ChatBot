import sqlite3
import pandas as pd


CUSTOMER_EXCEL = '/Users/phood/Template/Sheet.xlsx'
TROUBLE_EXCEL = '/Users/phood/Documents/Troubleshootingchat.xlsx'
DB_PATH = 'retailers.db'

df = pd.read_excel(CUSTOMER_EXCEL)

conn = sqlite3.connect("retailers.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    retailer TEXT NOT NULL,
    scan_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (retailer) REFERENCES retailers(retailer)
    );
""")

df_customers = pd.read_excel(CUSTOMER_EXCEL)

# Clean column names
df_customers.columns = (
    df_customers.columns
  # replace spaces with underscore
    .str.strip()
    .str.replace(":", "")    # remove colons
)

print("DEBUG COLUMN NAMES:", df_customers.columns.tolist())


rename_map = {
    "account #": "account_number",
    "retailer": "retailer",
    "last scan": "last_scan",
    "street": "street",
    "city": "city",
    "zip code": "zip_code",
    "state": "state",
    "country": "country",
    "tm": "tm",
    "fitter": "fitter",
    "phone": "phone",
    "email": "email",
    "ri 2024": "ri_2024",
    "ri 2025": "ri_2025",
    "jane notes": "jane_notes",
    "arlin": "arlin",
    "#": "ipad_number",
    "email password": "email_password",
    "ri app username": "ri_app_username",
    "ri app password": "ri_app_password",
    "app version": "app_version",
    "ios version": "ios_version",
    "serial number": "serial_number",
    "ipad model": "system_model",
    "sensor serial #": "sensor_serial",
    "jane comments": "jane_notes"
}

money_cols = ["ri_2024", "ri_2025"]

for col in money_cols:
    if col in df_customers.columns:
        df_customers[col] = (
            df_customers[col]
            .astype(str)
            .str.replace(r"[$,]", "", regex=True)
            .replace("nan", None)
            .astype(float)
        )

# Drop junk Excel columns like 'Unnamed: 26'
df_customers = df_customers.loc[:, ~df_customers.columns.str.contains("^Unnamed")]

df_customers = df_customers.rename(columns=rename_map)

df_customers['account_number'] = df_customers['account_number'].astype(str).str.replace('.0$', '', regex=True)

df_customers = df_customers.where(pd.notnull(df_customers), None)

df_customers = df_customers.drop_duplicates(subset=['retailer'])


cursor.execute("DROP TABLE IF EXISTS retailers")
               
               

cursor.execute("""
CREATE TABLE retailers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    arlin TEXT,
    ipad_number TEXT,
    email TEXT,
    email_password TEXT,
    ri_app_username TEXT,
    ri_app_password TEXT,
    retailer TEXT UNIQUE NOT NULL,
    account_number TEXT,
    ri_2024 REAL,
    ri_2025 REAL,
    app_version TEXT,
    ios_version TEXT,
    serial_number TEXT,
    system_model TEXT,
    sensor_serial TEXT,
    jane_notes TEXT,
    street TEXT,
    city TEXT,
    zip_code TEXT,
    state TEXT,
    country TEXT,
    tm TEXT,
    phone TEXT,
    fitter TEXT,
    last_scan TEXT,
    jane_comments TEXT, 
    returning_equipment TEXT,
    equipment_updated_at TEXT                         
);
""")              

df_customers["retailer"] = (
    df_customers["retailer"]
    .astype(str)
    .str.strip()
)
df_customers.to_sql("retailers", conn, if_exists="append", index=False)
print("Success: Excel imported into retailers.db")

df_trouble = pd.read_excel(TROUBLE_EXCEL)

df_trouble.columns = df_trouble.columns.str.strip()

cursor.execute("DROP TABLE IF EXISTS troubleshooting")

cursor.execute("""
CREATE TABLE troubleshooting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
)
""")

df_trouble.to_sql("troubleshooting", conn, if_exists="append", index=False)
print(f"imported{len(df_trouble)} troubleshooting entries")

conn.commit()
conn.close()

print("SUCCESS: Both customer and troubleshooting imported into db")