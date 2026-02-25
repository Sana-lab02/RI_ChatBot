from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import sqlite3

ALLOWED_TYPES = {"iPad", "Sensor"}
STATUS_IN_HOUSE = "inhouse"
STATUS_ASSIGNED = "assigned"
ALLWED_STATUSES = {STATUS_IN_HOUSE, STATUS_ASSIGNED}

class Device:
    id: int
    type: str
    number: Optional[str]
    serial_number: str
    model: Optional[str]
    ios_version: Optional[str]
    status: str
    last_updated: Optional[str]
    asset_tag: Optional[str]
    location: Optional[str]
    assigned_to: Optional[str]
    notes: Optional[str]

    def scan_code(self) -> str:
        return (self.asset_tag or self.number or self.serial_number or "").strip()
    
    def availability_label(self) -> str:
        if self.status == STATUS_IN_HOUSE:
            return "Avaliable"
        who = (self.assigned_to or "Unknown").strip()
        return f"Assigned to {who}"
    
class InventoryManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_indexes()


    def _ensure_indexes(self) -> None:
        cur = self.conn.cursor()
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_asset_tag ON inventory(asset_tag)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_type_serial ON inventory(type, serial_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status)")
        self.conn.commit()


    def normalize_statuses(self) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE inventory
            SET status = CASE
                WHEN status IS NULL OR TRIM(status) = '' THEN ?
                WHEN LOWER(status) IN ('in house','in_house','available','ready','in stock','instock') THEN ?
                WHEN LOWER(status) = 'assigned' THEN ?
                WHEN LOWER(status) = 'inhouse' THEN ?
                WHEN LOWER(status) = 'in-house' THEN ?
                ELSE ?
            END,
            last_updated = CURRENT_TIMESTAMP
            """,
            (
                STATUS_IN_HOUSE,
                STATUS_IN_HOUSE,
                STATUS_ASSIGNED,
                STATUS_IN_HOUSE,
                STATUS_IN_HOUSE,
                STATUS_ASSIGNED,
            ),
        )
        self.conn.commit()
        return cur.rowcount
    
    def get_summary_counts(self) -> Dict[str, Dict[str, int]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                type,
                SUM(CASE WHEN status = 'in_house' THEN 1 ELSE 0 END) AS available,
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) AS assigned,
                COUNT(*) AS total
            FROM inventory
            WHERE status != 'retired'
            GROUP BY type
            """
        )


        out: Dict[str, Dict[str, int]] = {}
        for row in cur.fetchall():
            # row might be tuple or sqlite3.Row depending on row_factory
            t = row[0]
            out[str(t)] = {
                "available": int(row[1] or 0),
                "assigned": int(row[2] or 0),
                "total": int(row[3] or 0),
            }
        # Ensure keys exist for common types
        for t in ["iPad", "Sensor"]:
            out.setdefault(t, {"available": 0, "assigned": 0, "total": 0})
        return out

    def list_ready_to_ship(self, limit: int = 50) -> List[Device]:
        """Devices with status='in_house'."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, type, number, serial_number, model, ios_version, status, last_updated,
                   asset_tag, location, assigned_to, notes
            FROM inventory
            WHERE status = ?
            ORDER BY type, id DESC
            LIMIT ?
            """,
            (STATUS_IN_HOUSE, int(limit)),
        )
        return [self._row_to_device(r) for r in cur.fetchall()]

    def lookup_device(self, code: str) -> Optional[Device]:
        """
        Lookup by scanned code. We match against:
        - asset_tag
        - number
        - serial_number
        """
        code = (code or "").strip()
        if not code:
            return None

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, type, number, serial_number, model, ios_version, status, last_updated,
                   asset_tag, location, assigned_to, notes
            FROM inventory
            WHERE asset_tag = ?
               OR number = ?
               OR serial_number = ?
            LIMIT 1
            """,
            (code, code, code),
        )
        row = cur.fetchone()
        return self._row_to_device(row) if row else None

    def check_out(self, code: str, assigned_to: str, location: Optional[str] = None, notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Mark device as assigned.
        """
        code = (code or "").strip()
        assigned_to = (assigned_to or "").strip()
        if not code or not assigned_to:
            return False, "Please scan a device and enter who it’s assigned to."

        dev = self.lookup_device(code)
        if not dev:
            return False, f"Device not found for code: {code}"

        if dev.status != STATUS_IN_HOUSE:
            return False, f"{dev.type} {dev.scan_code} is not in-house (currently: {dev.availability_label})."

        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE inventory
            SET status = ?,
                assigned_to = ?,
                location = COALESCE(?, location),
                notes = COALESCE(?, notes),
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (STATUS_ASSIGNED, assigned_to, location, notes, dev.id),
        )
        self.conn.commit()

        return True, f"✓ Checked out {dev.type} {dev.scan_code} to {assigned_to}."

    def check_in(self, code: str, location: str = "HQ", notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Mark device as in-house and clear assignment.
        """
        code = (code or "").strip()
        location = (location or "HQ").strip()
        if not code:
            return False, "Please scan a device."

        dev = self.lookup_device(code)
        if not dev:
            return False, f"Device not found for code: {code}"

        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE inventory
            SET status = ?,
                assigned_to = NULL,
                location = ?,
                notes = COALESCE(?, notes),
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (STATUS_IN_HOUSE, location, notes, dev.id),
        )
        self.conn.commit()

        return True, f"✓ Checked in {dev.type} {dev.scan_code}. Marked in_house at {location}."

    # ---------------------------
    # Session forms
    # ---------------------------

    def dashboard_form(self, is_admin: bool = False) -> Dict[str, Any]:
        """
        Returns a 'session form' payload similar to your add scan / update retailer forms.
        Frontend can render title, stats, and list.
        """
        summary = self.get_summary_counts()
        ready = self.list_ready_to_ship(limit=50)
        gen_breakdown = self.get_ipad_gen()

        # Flatten ready list into friendly lines for simple rendering
        items: List[str] = []
        for d in ready:
            parts = [d.type, d.scan_code]
            if d.model:
                parts.append(d.model)
            if d.location:
                parts.append(d.location)
            items.append(" • ".join([p for p in parts if p]))

        gen_items = []
        for g in gen_breakdown:
            gen_items.append(f"{g['model']} — {g['count']} available")

        if not gen_items:
            gen_items = ["No iPads currently in house"]

        buttons = [
                {"text": "Check Out", "action": "open_form", "target": "inventory_checkout"},
                {"text": "Check In", "action": "open_form", "target": "inventory_checkin"},
                {"text": "Refresh", "action": "submit"},
                {"text": "Exit", "action": "exit"},
            ]
        
        if is_admin:
            buttons.insert(0, {"text": "Remove Device", "action": "open_form", "target": "inventory_remove_device"})
            buttons.insert(0, {"text": "Add Device", "action": "open_form", "target": "inventory_add_device"})

        return {
            "type": "session form",
            "form_id": "inventory_dashboard",
            "title": "Inventory Dashboard",
            # keep stats simple so your frontend can display them easily
            "stats": {
                "iPads_in_house": summary.get("iPad", {}).get("available", 0),
                "Sensors_in_house": summary.get("Sensor", {}).get("available", 0),
                "iPads_total": summary.get("iPad", {}).get("total", 0),
                "Sensors_total": summary.get("Sensor", {}).get("total", 0),
            },
            "fields": [],  # dashboard doesn't need fields
            "sections": [
                {
                    "title": "iPad Generations Available",
                    "items": gen_items,
                },

                {
                    "title": "iPads Available",
                    "items": items if items else ["None currently marked as in house."],
                }
            ],
            "buttons": buttons,
            
        }

    def checkout_form(self) -> Dict[str, Any]:
        return {
            "type": "session form",
            "form_id": "inventory_checkout",
            "title": "Check Out Device",
            "fields": [
                {
                    "name": "code",
                    "type": "text",
                    "label": "Scan or enter device barcode",
                    "placeholder": "Scan now...",
                    "options": [],
                },
                {
                    "name": "assigned_to",
                    "type": "text",
                    "label": "Assigned to",
                    "placeholder": "Retailer or coworker name/email",
                    "options": [],
                },
                {
                    "name": "location",
                    "type": "text",
                    "label": "Location (optional)",
                    "placeholder": "HQ / Warehouse / etc",
                    "options": [],
                },
                {
                    "name": "notes",
                    "type": "text",
                    "label": "Notes (optional)",
                    "placeholder": "Any quick note",
                    "options": [],
                },
            ],
            "buttons": [
                {"text": "Check Out", "action": "submit"},
                {"text": "Cancel", "action": "exit"},
            ],
        }

    def checkin_form(self) -> Dict[str, Any]:
        return {
            "type": "session form",
            "form_id": "inventory_checkin",
            "title": "Check In Device",
            "fields": [
                {
                    "name": "code",
                    "type": "text",
                    "label": "Scan or enter device barcode",
                    "placeholder": "Scan now...",
                    "options": [],
                },
                {
                    "name": "location",
                    "type": "text",
                    "label": "Location",
                    "placeholder": "HQ",
                    "options": [],
                },
                {
                    "name": "notes",
                    "type": "text",
                    "label": "Notes (optional)",
                    "placeholder": "Any quick note",
                    "options": [],
                },
            ],
            "buttons": [
                {"text": "Check In", "action": "submit"},
                {"text": "Cancel", "action": "exit"},
            ],
        }

    def handle_form_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call this from your RetailBot.handle_form_submission when form_id matches inventory_*.
        Returns a response dict (usually {"text": "..."} or {"reply": <form>}).
        """
        form_id = payload.get("form_id")
        data = payload.get("data", {}) or {}

        if form_id == "inventory_dashboard":
            return {"reply": self.dashboard_form()}

        if form_id == "inventory_checkout":
            ok, msg = self.check_out(
                code=str(data.get("code", "")),
                assigned_to=str(data.get("assigned_to", "")),
                location=(str(data.get("location")) if data.get("location") is not None else None),
                notes=(str(data.get("notes")) if data.get("notes") is not None else None),
            )
            return {"text": msg, "reply": self.dashboard_form()} if ok else {"text": f"⚠ {msg}"}

        if form_id == "inventory_checkin":
            ok, msg = self.check_in(
                code=str(data.get("code", "")),
                location=str(data.get("location") or "HQ"),
                notes=(str(data.get("notes")) if data.get("notes") is not None else None),
            )
            return {"text": msg, "reply": self.dashboard_form()} if ok else {"text": f"⚠ {msg}"}

        return {"text": "Unknown inventory form submission."}
    

    def get_ipad_gen(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT model, COUNT(*) as count
            FROM inventory
            WHERE type = 'iPad'
                AND status = 'in_house'
            GROUP BY model
            ORDER BY count DESC
        """)

        rows = cur.fetchall()

        break_down = []
        for model, count in rows:
            label = model if model else "Unkown Gen"
            break_down.append({
                "model": label,
                "count": count
            })

        return break_down
        

    def _row_to_device(self, row: Any) -> Device:
        """
        Supports sqlite3.Row or tuple.
        """
        if row is None:
            raise ValueError("row is None")

        
        if hasattr(row, "keys"):
            return Device(
                id=int(row["id"]),
                type=str(row["type"]),
                number=row["number"],
                serial_number=str(row["serial_number"]),
                model=row["model"],
                ios_version=row["ios_version"],
                status=str(row["status"] or "").strip() or STATUS_IN_HOUSE,
                last_updated=str(row["last_updated"]) if row["last_updated"] is not None else None,
                asset_tag=row["asset_tag"],
                location=row["location"],
                assigned_to=row["assigned_to"],
                notes=row["notes"],
            )

       
        return Device(
            id=int(row[0]),
            type=str(row[1]),
            number=row[2],
            serial_number=str(row[3]),
            model=row[4],
            ios_version=row[5],
            status=str(row[6] or "").strip() or STATUS_IN_HOUSE,
            last_updated=str(row[7]) if row[7] is not None else None,
            asset_tag=row[8],
            location=row[9],
            assigned_to=row[10],
            notes=row[11],
        )

    def add_device_form(self) -> Dict[str, Any]:
        return {
            "type": "session form",
            "form_id": "inventory_add_device",
            "title": "Add Device to Inventory",
            "fields": [
                {"name": "type", "type": "dropdown", "label": "Type", "options": ["iPad", "Sensor"]},
                {"name": "asset_tag", "type": "text", "label": "Asset Tag (Barcode)", "placeholder": "Scan barcode / type tag", "options": []},
                {"name": "serial_number", "type": "text", "label": "Serial Number", "placeholder": "Scan or type serial", "options": []},
                {"name": "number", "type": "text", "label": "Device Number (optional)", "placeholder": "e.g. iPad-12", "options": []},
                {"name": "model", "type": "text", "label": "Model / Generation", "placeholder": "iPad 10th Gen", "options": []},
                {"name": "ios_version", "type": "text", "label": "iOS Version (optional)", "placeholder": "17.3", "options": []},
                {"name": "location", "type": "text", "label": "Location", "placeholder": "HQ", "options": []},
                {"name": "notes", "type": "text", "label": "Notes (optional)", "placeholder": "", "options": []},
            ],
            "buttons": [
                {"text": "Add Device", "action": "submit"},
                {"text": "Cancel", "action": "exit"},
            ],
        }

    def remove_device_form(self) -> Dict[str, Any]:
        return {
            "type": "session form",
            "form_id": "inventory_remove_device",
            "title": "Retire / Remove Device",
            "fields": [
                {
                    "name": "lookup",
                    "type": "text",
                    "label": "Asset Tag OR Serial Number",
                    "placeholder": "Scan barcode or type serial",
                    "options": []
                },
                {
                    "name": "reason",
                    "type": "text",
                    "label": "Reason (optional)",
                    "placeholder": "Upgraded / Broken / Lost",
                    "options": []
                }
            ],
            "buttons": [
                {"text": "Retire Device", "action": "submit"},
                {"text": "Cancel", "action": "exit"},
            ],
        }

    # ---------- HELPERS ----------

    def _find_device(self, lookup: str) -> Optional[sqlite3.Row]:
        lookup = (lookup or "").strip()
        if not lookup:
            return None

        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM inventory
            WHERE serial_number = ?
               OR asset_tag = ?
            """,
            (lookup, lookup),
        )
        return cur.fetchone()

    # ---------- ACTIONS ----------

    def add_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        dtype = (data.get("type") or "").strip()
        asset_tag = (data.get("asset_tag") or "").strip() or None
        serial = (data.get("serial_number") or "").strip()
        number = (data.get("number") or "").strip() or None
        model = (data.get("model") or "").strip() or None
        ios_version = (data.get("ios_version") or "").strip() or None
        location = (data.get("location") or "Jackson").strip()
        notes = (data.get("notes") or "").strip() or None

        if dtype not in ("iPad", "Sensor"):
            return {"text": "⚠ Type must be iPad or Sensor."}
        if not serial:
            return {"text": "⚠ Serial number is required."}

        # Check duplicates
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM inventory WHERE serial_number = ?", (serial,))
        if cur.fetchone():
            return {"text": "⚠ A device with that serial number already exists."}

        if asset_tag:
            cur.execute("SELECT id FROM inventory WHERE asset_tag = ?", (asset_tag,))
            if cur.fetchone():
                return {"text": "⚠ A device with that asset tag already exists."}

        
        status = "in_house"
        assigned_to = None

        try:
            cur.execute(
                """
                INSERT INTO inventory (type, number, serial_number, model, ios_version, status, last_updated, asset_tag, location, assigned_to, notes)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                """,
                (dtype, number, serial, model, ios_version, status, asset_tag, location, assigned_to, notes),
            )
            self.conn.commit()
        except Exception as e:
            return {"text": f"⚠ Failed to add device: {e}"}

        return {"text": f"✓ Added {dtype} ({asset_tag or serial})"}

    def retire_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lookup = (data.get("lookup") or "").strip()
        reason = (data.get("reason") or "").strip()

        if not lookup:
            return {"text": "⚠ Please scan or type an asset tag/serial."}

        row = self._find_device(lookup)
        if not row:
            return {"text": "❌ Device not found."}

        if (row["status"] or "").lower() == "assigned":
            return {"text": "❌ This device is assigned. Check it in first before retiring."}

        note_line = "Retired"
        if reason:
            note_line += f": {reason}"

        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE inventory
            SET status = 'retired',
                notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || char(10) || ?
                END,
                last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (note_line, note_line, row["id"]),
        )
        self.conn.commit()

        return {"text": f"✓ Retired {row['type']} ({row['asset_tag'] or row['serial_number']})"}

