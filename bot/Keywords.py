exit_commands = 'quit', 'exit', 'stop', 'no that is it', 'pause'

column_aliases = {
    "ri_app_password": ["password", "ri password", "app password", "ri app pass", "riapp password", "riapp pass"],
    "ri_app_username": ["riappusername", "ri app user", "ri application username", "username"],
    "ipad_number": ["Trupad number", "trupad number", "ipad", "ipad number", ],
    "system_model": ["ipad system model", "ipad model", "ipad generation", "generation", "ipad sys number"],
    "account_number": ["account number", "account num", "acc number", "acc num", "ac number", "ac num"],
    "sensor_serial": ["sensor serial number", "sensor number", "sensor serial", "sens number", "sens serial", "sen serial", "sen numb", "sensor"],
    "serial_number": ["serial number", "ipad serial number", "ipad serial", "iPad serial number"],
    "email": ["email", "electronicmail"],
    "email_password": ["email password"],
    "last_scan": ["last scan", "last scan date", "scan last"],
    "street": ["street"],
    "city": ["city"],
    "zip_code": ["zip code", "zip"],
    "tm": ["tm", "territory manager"],
    "jane_comments": ["jane comments", "jane notes", "notes from jane"],
    "fitter": ["fitter"],
    "phone": ["phone number", "phone"],
    "arlin": ["arlin"],
    "country": ["country"],
    "ri_2024": ["ri 2024"],
    "ri_2025": ["ri 2025"],
    "email_password": ["email password", "password for email", "email pass"],
    "app_version": ["app version", "app vers"],
    "ios_version": ["ios version", "ios", "ipad version"],
    "returning_equipment": ["old equipment", "returned equipment"],
    "notes": ["Notes", "notes", "account notes", "Account notes",]
}

credential_terms = [
    "password",
    "username",
    "login",
    "email",
    "sign in"
    "ipad"
]

column_to_names = {
    "account_number": "Account Number",
    "arlin": "Arlin",
    "ri_app_username": "App Username",
    "ri_app_password": "App Password",
    "email": "iPad Email Address",
    "email_password": "iPad Email Password",
    "system_model": "iPad System Model",
    "serial_number": "iPad Serial Number",
    "ios_version": "iOS Version",
    "app_version": "RI App Version",
    "sensor_serial": "Sensor Serial Number",
    "last_scan": "Last Scan",
    "ri_2024": "RI 2024",
    "ri_2025": "RI 2025",
    "tm": "TM",
    "street": "Street",
    "city": "City",
    "state": "State",
    "zip_code": "Zip Code",
    "country": "Country",
    "phone": "Phone Number",
    "fitter": "Fitter",
    "notes": "Notes",
    "jane_notes": "Jane Notes"
}

display_order = [
    "account_number",
    "arlin",
    "ipad_number"
    "ri_app_username",
    "ri_app_password",
    "email",
    "email_password",
    "system_model",
    "serial_number",
    "ios_version",
    "app_version",
    "sensor_serial",
    "last_scan",
    "ri_2024",
    "ri_2025",
    "tm",
    "street",
    "city",
    "state",
    "zip_code",
    "country",
    "phone",
    "fitter",
    "notes",
    "jane_notes"
]
scan_intents = {
    "predict": ["predict", "predict scans for", "scan predict for", "future scans", "future scan counts", "projected scan counts for", "projected scan count"],
    "history": ["history for", "history", "past scans", "previous scans", "previous scan count", "past", "last scans", "history of scans"],
    "count": ["how many", "count", "total", "number of"]
}

allowed_update_columns = {
    "notes",
    "jane_notes",
    "sensor_serial",
    "ipad_number",
    "ri_app_username",
    "ri_app_password",
    "system_model",
    "serial_number",
    "app_version",
    "ios_version"
}

trouble_shooting_triggers = {
    "known troubleshooting",
    "known issues",
    "what can you troubleshoot",
    "list troubleshooting",
    "troubleshooting topics"
}

scan_entry_triggers = {
    "scan entry",
    "add scan",
    "enter scan",
}

inventory_triggers = {
    "inventory tracker",
    "in house inventory",
    "available ipads",
    "inventory",
    "inventory manager"
}