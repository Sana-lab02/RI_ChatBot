def send_new_equipment(self, retailer_name, new_ipad=None, new_sensor=None):
        retailer_name = str(retailer_name).strip()
        conn = sqlite3.connect("retailers.db")
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA database_list;")
        print("DB FILE ACTUALLY USED:", cursor.fetchall())

        cursor.execute("PRAGMA table_info(retailers);")
        cols = cursor.fetchall()
        print("COLUMNS IN THIS FILE:", cols)


        cursor.execute("""
            SELECT ipad_number, sensor_serial, returning_equipment
            FROM retailers
            WHERE retailer LIKE ?
        """, (f"%{retailer_name}%",))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return f"Retailer '{retailer_name}' not found."
        
        old_ipad, old_sensor, existing_return = row

        moved = " / ".join(filter(None, [old_ipad, old_sensor]))
        combined_returning = " | ".join(filter(None, [existing_return, moved]))

        cursor.execute("""
            UPDATE retailers
            SET
                returning_equipment = ?,
                ipad_number = ?,
                sensor_serial = ?,
                equipment_updated_at = datetime('now')
            WHERE retailer LIKE ?
        """, (
            combined_returning,
            new_ipad or old_ipad,
            new_sensor or old_sensor,
            f"%{retailer_name}%"
        ))

        conn.commit()
        conn.close()

        self.refresh_customer_db()

        return f"Equipment for {retailer_name} updated. Old equipment moved to returning_equipment"