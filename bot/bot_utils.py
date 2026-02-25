import re
from rapidfuzz import fuzz
import nltk
import numpy as np
import pandas as pd
from nltk.stem import WordNetLemmatizer
import sys
from bot.Keywords import column_aliases, credential_terms, scan_intents, trouble_shooting_triggers, inventory_triggers, column_to_names, display_order
from datetime import datetime

nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# ======= Lematizer function ========#
lemmatizer = WordNetLemmatizer()



def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    
    text = re.sub(r"[^\w\s'&\-\.]", "", text)

    return text

def clean_text_tfidf(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    
    text = re.sub(r"[^\w\s'&\-\.]", "", text)
    
    return text

# Helper for safe prints
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        pass

def load_excel_files(trouble_path, customer_path):
    # Loading excelsheet
    try:
        df_trouble = pd.read_excel(trouble_path)
        df_customer_info = pd.read_excel(customer_path)
        return df_trouble, df_customer_info
    except FileNotFoundError as e:
        safe_print("Error: One or more Excel files could not be found.")
        safe_print(e)
        sys.exit(1)

def is_retailer_info_question(user_input):
    text = user_input.lower()

    for aliases in column_aliases.values():
        for alias in aliases:
            if alias.lower() in text:
                return True
    if "all info" in text or "everything" in text:
        return True
    
    return False
    

def is_parcel_shipper_request(text):
    text = text.lower()
    triggers = [
        "make a parcel shipper",
        "create parcel shipper",
        "generate parcel",
        "make parcel",
        "parcel shipper for",
        "create shipping form"
    ]
    return any(t in text for t in triggers) 

def detect_multiple_updates(user_input):
    updates = {}
    text = user_input.lower()

    for column, aliases in column_aliases.items():
        for alias in aliases:
            pattern = rf"{alias}\s*(?:to|is)\s*([^,]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                updates[column] = match.group(1).strip()
    return updates

def append_note(existing_notes, new_note, author="Bot"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp} | {author}] {new_note}"

    if existing_notes:
        return existing_notes.strip() + "\n" + entry
    else:
        return entry
    
def is_note_addition(user_input):
    text = user_input.lower()
    note_phrases = [
        "add note",
        "add jane note",
        "add jane notes",
        "note for",
        "jane note"
    ]

    return any(phrase in text for phrase in note_phrases)

def extract_months(text, default=12):
    text = text.lower()
    match = re.search(r"(\d+)\s*(month|months|mo)", text)
    if match:
        return int(match.group(1))
    if "next month" in text:
        return 1
    if "year" in text or "annual" in text:
        return 12
    if "quater" in text:
        return 3

def extract_retailer(text):
    text = text.lower().strip()
    text = re.sub(r'\b(predict|forecast|future|projection|scan|scans|history|past|previous)\b', '', text)
    text = re.sub(r'\b(for|of|the)\b', '', text)
    text = re.sub(r'\d+\s*(month|months|mo)s?', '', text)

    # Clean extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text.title()

def detect_scan_intent(text):
    text = text.lower()
    for intent, keywords in scan_intents.items():
        if any(k in text for k in keywords):
            return intent
    return None

def extract_time_mode(text):
    text = text.lower()

    if "full" in text or "all" in text:
        return "full"
    
    if "this year" in text:
        return "this_year"
    
    if "last month" in text:
        return ("last_n", 1)
    
    if "last" in text and "month" in text:
        n = extract_months(text)
        return ("last_n", n)
    
    if "months ago" in text:
        n = extract_months(text)
        return ("n_ago", n)
    
    return None

def extract_requested_field(user_input):
    text = user_input.lower()
    for col, keywords in column_aliases.items():
        if any(k in text for k in keywords):
            return col
    return None

def is_troubleshooting_list_request(text):
    text = text.lower()
    return any(t in text for t in trouble_shooting_triggers)

def is_inventory_request(text):
    text = text.lower().strip()
    return any(t in text for t in inventory_triggers)

def format_retailer_row(data: dict, display_order: list[str]) -> list[str]:
    lines = []

    hidden_fields = {
        "id",
        "retailer"
    }

    def add_line(col, val):
        if pd.notna(val) and str(val).strip():
            label = col.replace("_", " ").title()
            lines.append(f"{label}: {val}")

    for col in display_order:
        if col in data and col not in hidden_fields:
            add_line(col, data.get(col))

    remaining_cols = sorted(
        set(data.keys()) - set(display_order) - hidden_fields
    )

    for col in remaining_cols:
        add_line(col, data.get(col))

    return lines


