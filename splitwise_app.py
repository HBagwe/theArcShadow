"""
SplitExpense - Smart Expense Tracker & Settlement Desktop Application
=====================================================================
Features:
- Vibrant, Redefined Modern Multi-Color UI (Dark Mode with Indigo, Cyan, Emerald, Rose, Amber, Purple, Coral accents)
- Sleek KPI Metrics Cards with individual color-coded glowing left accent bars and badge pills
- Groups & Members Management (with Phone, Email, UPI/Payment handles)
- Expense creation with Multiple Split & Allocation Modes:
  * 🎯 Paid for One Person (Full Amount: +Amount to Payer, -Amount to Borrower)
  * 👥 Paid for Others (Full Amount split among others, Payer excluded from share)
  * 🍕 Shared Equally (Payer included in split)
  * ₹ Exact Custom Amounts (Specify exact deductions per member)
  * % Percentages (%) & ⚖ Shares
- Live Balance Impact Preview (+Added to Payer, -Subtracted from Members)
- Detailed Member Account Ledger (Every rupee added & subtracted)
- Color-coded Treeview rows (Emerald for positive, Rose for debtors, Slate for settled)
- Debt Simplification Algorithm (Min Cash Flow)
- Settlements & Payment Recording
- Automated & 1-Click WhatsApp and SMS Reminders with Direct Payment Deep Links (UPI, etc.)
- Optional Automated Twilio API Integration for Background SMS & WhatsApp
- SQLite Persistence
"""

import base64
import json
import os
import re
import sqlite3
import sys
import threading
import tkinter as tk
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splitwise_data.db")

# ============================================================================
# 1. DATABASE & STORAGE LAYER
# ============================================================================

class Database:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Members table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                name TEXT NOT NULL,\
                phone TEXT DEFAULT '',\
                email TEXT DEFAULT '',\
                upi_id TEXT DEFAULT '',\
                payment_notes TEXT DEFAULT '',\
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\
            )\
            """)

            # Groups table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                name TEXT NOT NULL,\
                description TEXT DEFAULT '',\
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\
            )\
            """)

            # Group membership
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (\
                group_id INTEGER,\
                member_id INTEGER,\
                PRIMARY KEY (group_id, member_id),\
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,\
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE\
            )\
            """)

            # Expenses table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                group_id INTEGER,\
                description TEXT NOT NULL,\
                amount REAL NOT NULL,\
                payer_id INTEGER NOT NULL,\
                split_type TEXT NOT NULL,\
                category TEXT DEFAULT 'General',\
                date TEXT NOT NULL,\
                notes TEXT DEFAULT '',\
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,\
                FOREIGN KEY (payer_id) REFERENCES members(id) ON DELETE CASCADE\
            )\
            """)

            # Expense splits table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                expense_id INTEGER NOT NULL,\
                member_id INTEGER NOT NULL,\
                amount_owed REAL NOT NULL,\
                FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,\
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE\
            )\
            """)

            # Settlements table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settlements (\
                id INTEGER PRIMARY KEY AUTOINCREMENT,\
                group_id INTEGER,\
                from_member_id INTEGER NOT NULL,\
                to_member_id INTEGER NOT NULL,\
                amount REAL NOT NULL,\
                payment_mode TEXT DEFAULT 'Cash/UPI',\
                date TEXT NOT NULL,\
                notes TEXT DEFAULT '',\
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,\
                FOREIGN KEY (from_member_id) REFERENCES members(id) ON DELETE CASCADE,\
                FOREIGN KEY (to_member_id) REFERENCES members(id) ON DELETE CASCADE\
            )\
            """)

            # Key-value settings table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (\
                key TEXT PRIMARY KEY,\
                value TEXT NOT NULL\
            )\
            """)

            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('currency', '₹')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('twilio_sid', '')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('twilio_token', '')")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('twilio_phone', '')")

            cursor.execute("SELECT COUNT(*) as cnt FROM groups")
            if cursor.fetchone()["cnt"] == 0:
                self._seed_sample_data(cursor)

            conn.commit()

    def _seed_sample_data(self, cursor):
        cursor.execute("INSERT INTO members (name, phone, email, upi_id, payment_notes) VALUES ('Alice Sharma', '+919876543210', 'alice@example.com', 'alice@okaxis', 'GPay / PhonePe')")
        m1 = cursor.lastrowid
        cursor.execute("INSERT INTO members (name, phone, email, upi_id, payment_notes) VALUES ('Bob Verma', '+919876543211', 'bob@example.com', 'bob@oksbi', 'Paytm / UPI')")
        m2 = cursor.lastrowid
        cursor.execute("INSERT INTO members (name, phone, email, upi_id, payment_notes) VALUES ('Charlie Patel', '+919876543212', 'charlie@example.com', 'charlie@icici', 'Net Banking / UPI')")
        m3 = cursor.lastrowid

        cursor.execute("INSERT INTO groups (name, description) VALUES ('Weekend Trip', 'Shared travel and food expenses')")
        g1 = cursor.lastrowid

        for g in [g1]:
            cursor.execute("INSERT INTO group_members (group_id, member_id) VALUES (?, ?)", (g, m1))
            cursor.execute("INSERT INTO group_members (group_id, member_id) VALUES (?, ?)", (g, m2))
            cursor.execute("INSERT INTO group_members (group_id, member_id) VALUES (?, ?)", (g, m3))


# ============================================================================
# 2. CORE ENGINE & DEBT SIMPLIFICATION
# ============================================================================

class SplitwiseEngine:
    def __init__(self, db: Database):
        self.db = db

    def get_setting(self, key, default=""):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_members(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members ORDER BY name ASC")
            return [dict(r) for r in cursor.fetchall()]

    def get_member(self, member_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def add_member(self, name, phone, email, upi_id, notes=""):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO members (name, phone, email, upi_id, payment_notes) VALUES (?, ?, ?, ?, ?)",
                (name, phone, email, upi_id, notes),
            )
            conn.commit()
            return cursor.lastrowid

    def update_member(self, member_id, name, phone, email, upi_id, notes=""):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE members SET name = ?, phone = ?, email = ?, upi_id = ?, payment_notes = ? WHERE id = ?",
                (name, phone, email, upi_id, notes, member_id),
            )
            conn.commit()

    def delete_member(self, member_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
            conn.commit()

    def get_groups(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups ORDER BY name ASC")
            return [dict(r) for r in cursor.fetchall()]

    def add_group(self, name, description, member_ids=None):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO groups (name, description) VALUES (?, ?)", (name, description))
            group_id = cursor.lastrowid
            if member_ids:
                for mid in member_ids:
                    cursor.execute("INSERT OR IGNORE INTO group_members (group_id, member_id) VALUES (?, ?)", (group_id, mid))
            conn.commit()
            return group_id

    def get_group_members(self, group_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.* FROM members m
                JOIN group_members gm ON m.id = gm.member_id
                WHERE gm.group_id = ?
                ORDER BY m.name ASC
            """, (group_id,))
            return [dict(r) for r in cursor.fetchall()]

    def set_group_members(self, group_id, member_ids):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
            for mid in member_ids:
                cursor.execute("INSERT INTO group_members (group_id, member_id) VALUES (?, ?)", (group_id, mid))
            conn.commit()

    def add_expense(self, group_id, description, amount, payer_id, split_type, splits, category="General", date=None, notes=""):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (group_id, description, amount, payer_id, split_type, category, date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (group_id, description, amount, payer_id, split_type, category, date, notes))
            expense_id = cursor.lastrowid

            for member_id, owed in splits:
                cursor.execute("""
                    INSERT INTO expense_splits (expense_id, member_id, amount_owed)
                    VALUES (?, ?, ?)
                """, (expense_id, member_id, owed))

            conn.commit()
            return expense_id

    def delete_expense(self, expense_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()

    def get_expenses(self, group_id=None):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT e.*, m.name as payer_name, g.name as group_name
                FROM expenses e
                LEFT JOIN members m ON e.payer_id = m.id
                LEFT JOIN groups g ON e.group_id = g.id
            """
            params = []
            if group_id:
                query += " WHERE e.group_id = ?"
                params.append(group_id)
            query += " ORDER BY e.date DESC, e.id DESC"
            cursor.execute(query, params)
            expenses = [dict(r) for r in cursor.fetchall()]

            for exp in expenses:
                cursor.execute("""
                    SELECT es.*, m.name as member_name
                    FROM expense_splits es
                    JOIN members m ON es.member_id = m.id
                    WHERE es.expense_id = ?
                """, (exp["id"],))
                exp["splits"] = [dict(s) for s in cursor.fetchall()]

            return expenses

    def record_settlement(self, group_id, from_member_id, to_member_id, amount, payment_mode="Cash/UPI", date=None, notes=""):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settlements (group_id, from_member_id, to_member_id, amount, payment_mode, date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (group_id, from_member_id, to_member_id, amount, payment_mode, date, notes))
            settlement_id = cursor.lastrowid
            conn.commit()
            return settlement_id

    def get_settlements(self, group_id=None):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT s.*, m1.name as from_name, m2.name as to_name, g.name as group_name
                FROM settlements s
                JOIN members m1 ON s.from_member_id = m1.id
                JOIN members m2 ON s.to_member_id = m2.id
                LEFT JOIN groups g ON s.group_id = g.id
            """
            params = []
            if group_id:
                query += " WHERE s.group_id = ?"
                params.append(group_id)
            query += " ORDER BY s.date DESC, s.id DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    # ------------------------------------------------------------------------
    # Net Balances Calculation (Added & Subtracted)
    # ------------------------------------------------------------------------
    def calculate_balances(self, group_id=None):
        members = self.get_group_members(group_id) if group_id else self.get_members()
        paid_map = {m["id"]: 0.0 for m in members}
        owed_map = {m["id"]: 0.0 for m in members}
        settled_paid_map = {m["id"]: 0.0 for m in members}
        settled_recv_map = {m["id"]: 0.0 for m in members}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Total paid by each member (Added +)
            q1 = "SELECT payer_id, SUM(amount) as total_paid FROM expenses"
            p1 = []
            if group_id:
                q1 += " WHERE group_id = ?"
                p1.append(group_id)
            q1 += " GROUP BY payer_id"
            cursor.execute(q1, p1)
            for row in cursor.fetchall():
                pid = row["payer_id"]
                paid_map[pid] = paid_map.get(pid, 0.0) + (row["total_paid"] or 0.0)

            # 2. Total owed by each member (Subtracted -)
            q2 = """
                SELECT es.member_id, SUM(es.amount_owed) as total_owed
                FROM expense_splits es
                JOIN expenses e ON es.expense_id = e.id
            """
            p2 = []
            if group_id:
                q2 += " WHERE e.group_id = ?"
                p2.append(group_id)
            q2 += " GROUP BY es.member_id"
            cursor.execute(q2, p2)
            for row in cursor.fetchall():
                mid = row["member_id"]
                owed_map[mid] = owed_map.get(mid, 0.0) + (row["total_owed"] or 0.0)

            # 3. Settlements
            q3 = "SELECT from_member_id, to_member_id, amount FROM settlements"
            p3 = []
            if group_id:
                q3 += " WHERE group_id = ?"
                p3.append(group_id)
            cursor.execute(q3, p3)
            for row in cursor.fetchall():
                f_id = row["from_member_id"]
                t_id = row["to_member_id"]
                amt = row["amount"] or 0.0
                settled_paid_map[f_id] = settled_paid_map.get(f_id, 0.0) + amt
                settled_recv_map[t_id] = settled_recv_map.get(t_id, 0.0) + amt

        all_members_dict = {m["id"]: m for m in self.get_members()}
        result = []
        for mid in set(list(paid_map.keys()) + list(owed_map.keys())):
            m_obj = all_members_dict.get(mid)
            if not m_obj:
                continue

            paid = paid_map.get(mid, 0.0)
            owed = owed_map.get(mid, 0.0)
            s_paid = settled_paid_map.get(mid, 0.0)
            s_recv = settled_recv_map.get(mid, 0.0)

            net = (paid + s_paid) - (owed + s_recv)

            result.append({
                "member_id": mid,
                "name": m_obj["name"],
                "phone": m_obj["phone"],
                "email": m_obj["email"],
                "upi_id": m_obj["upi_id"],
                "payment_notes": m_obj.get("payment_notes", ""),
                "total_paid": round(paid, 2),
                "total_owed": round(owed, 2),
                "settled_paid": round(s_paid, 2),
                "settled_recv": round(s_recv, 2),
                "net_balance": round(net, 2)
            })

        result.sort(key=lambda x: x["net_balance"], reverse=True)
        return result

    def get_member_ledger(self, member_id, group_id=None):
        ledger = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Paid expenses (Added +)
            q1 = """
                SELECT e.id, e.date, e.description, e.amount, e.category, g.name as group_name
                FROM expenses e
                LEFT JOIN groups g ON e.group_id = g.id
                WHERE e.payer_id = ?
            """
            p1 = [member_id]
            if group_id:
                q1 += " AND e.group_id = ?"
                p1.append(group_id)
            cursor.execute(q1, p1)
            for r in cursor.fetchall():
                ledger.append({
                    "date": r["date"],
                    "type": "PAID_EXPENSE",
                    "description": f"Paid for: {r['description']} ({r['category']})",
                    "added": r["amount"],
                    "subtracted": 0.0,
                    "net_change": +r["amount"],
                    "notes": f"Group: {r['group_name'] or 'General'}"
                })

            # 2. Owed expense shares (Subtracted -)
            q2 = """
                SELECT es.amount_owed, e.date, e.description, m.name as payer_name, g.name as group_name
                FROM expense_splits es
                JOIN expenses e ON es.expense_id = e.id
                JOIN members m ON e.payer_id = m.id
                LEFT JOIN groups g ON e.group_id = g.id
                WHERE es.member_id = ?
            """
            p2 = [member_id]
            if group_id:
                q2 += " AND e.group_id = ?"
                p2.append(group_id)
            cursor.execute(q2, p2)
            for r in cursor.fetchall():
                ledger.append({
                    "date": r["date"],
                    "type": "EXPENSE_SHARE",
                    "description": f"Share for: {r['description']} (paid by {r['payer_name']})",
                    "added": 0.0,
                    "subtracted": r["amount_owed"],
                    "net_change": -r["amount_owed"],
                    "notes": f"Group: {r['group_name'] or 'General'}"
                })

            # 3. Settlements paid
            q3 = """
                SELECT s.date, s.amount, s.payment_mode, m.name as to_name
                FROM settlements s
                JOIN members m ON s.to_member_id = m.id
                WHERE s.from_member_id = ?
            """
            p3 = [member_id]
            if group_id:
                q3 += " AND s.group_id = ?"
                p3.append(group_id)
            cursor.execute(q3, p3)
            for r in cursor.fetchall():
                ledger.append({
                    "date": r["date"],
                    "type": "SETTLEMENT_PAID",
                    "description": f"Settlement paid to {r['to_name']} ({r['payment_mode']})",
                    "added": r["amount"],
                    "subtracted": 0.0,
                    "net_change": +r["amount"],
                    "notes": "Settled debt"
                })

            # 4. Settlements received
            q4 = """
                SELECT s.date, s.amount, s.payment_mode, m.name as from_name
                FROM settlements s
                JOIN members m ON s.from_member_id = m.id
                WHERE s.to_member_id = ?
            """
            p4 = [member_id]
            if group_id:
                q4 += " AND s.group_id = ?"
                p4.append(group_id)
            cursor.execute(q4, p4)
            for r in cursor.fetchall():
                ledger.append({
                    "date": r["date"],
                    "type": "SETTLEMENT_RECEIVED",
                    "description": f"Settlement received from {r['from_name']} ({r['payment_mode']})",
                    "added": 0.0,
                    "subtracted": r["amount"],
                    "net_change": -r["amount"],
                    "notes": "Received payment"
                })

        ledger.sort(key=lambda x: x["date"], reverse=True)
        return ledger

    def simplify_debts(self, group_id=None):
        balances_list = self.calculate_balances(group_id)
        debtors = []
        creditors = []
        member_map = {m["member_id"]: m for m in balances_list}

        for b in balances_list:
            net = b["net_balance"]
            if net < -0.01:
                debtors.append([b["member_id"], b["name"], -net])
            elif net > 0.01:
                creditors.append([b["member_id"], b["name"], net])

        transactions = []
        i = 0
        j = 0

        while i < len(debtors) and j < len(creditors):
            debtor_id, debtor_name, debit = debtors[i]
            creditor_id, creditor_name, credit = creditors[j]

            settle_amount = round(min(debit, credit), 2)

            if settle_amount > 0.01:
                creditor_info = member_map.get(creditor_id, {})
                debtor_info = member_map.get(debtor_id, {})
                transactions.append({
                    "from_id": debtor_id,
                    "from_name": debtor_name,
                    "from_phone": debtor_info.get("phone", ""),
                    "to_id": creditor_id,
                    "to_name": creditor_name,
                    "to_phone": creditor_info.get("phone", ""),
                    "to_upi": creditor_info.get("upi_id", ""),
                    "to_notes": creditor_info.get("payment_notes", ""),
                    "amount": settle_amount,
                })

            debtors[i][2] -= settle_amount
            creditors[j][2] -= settle_amount

            if debtors[i][2] <= 0.01:
                i += 1
            if creditors[j][2] <= 0.01:
                j += 1

        return transactions


# ============================================================================
# 3. NOTIFICATION DISPATCHER (WHATSAPP, SMS, TWILIO)
# ============================================================================

class NotificationService:
    def __init__(self, engine: SplitwiseEngine):
        self.engine = engine

    def generate_settlement_message(self, from_name, to_name, amount, currency="₹", to_upi="", to_notes=""):
        msg = (
            f"👋 Hi {from_name}!\n\n"
            f"This is a friendly reminder from SplitExpense.\n"
            f"Your current outstanding balance to {to_name} is: {currency}{amount:.2f}.\n\n"
        )
        if to_upi:
            msg += f"💳 Pay via UPI ID: {to_upi}\n"
            msg += f"🔗 Direct UPI Link: upi://pay?pa={to_upi}&pn={urllib.parse.quote(to_name)}&am={amount:.2f}&cu=INR\n"
        if to_notes:
            msg += f"📝 Note: {to_notes}\n"

        msg += "\nPlease settle this when convenient. Thank you!"
        return msg

    def generate_expense_alert_message(self, member_name, payer_name, description, owed_amount, total_amount, currency="₹", to_upi=""):
        msg = (
            f"📢 SplitExpense Alert\n\n"
            f"Hi {member_name},\n"
            f"An expense '{description}' of total {currency}{total_amount:.2f} was paid by {payer_name}.\n"
            f"Your allocated share is: {currency}{owed_amount:.2f}.\n\n"
        )
        if to_upi:
            msg += f"💳 Pay to UPI: {to_upi}\n"
        msg += "Thank you!"
        return msg

    def open_whatsapp(self, phone, message):
        cleaned_phone = re.sub(r"[^\d+]", "", phone)
        if len(cleaned_phone) == 10 and not cleaned_phone.startswith("+"):
            cleaned_phone = "91" + cleaned_phone
        elif cleaned_phone.startswith("+"):
            cleaned_phone = cleaned_phone[1:]

        encoded_text = urllib.parse.quote(message)
        url = f"https://wa.me/{cleaned_phone}?text={encoded_text}"
        webbrowser.open(url)
        return True

    def open_sms(self, phone, message):
        cleaned_phone = re.sub(r"[^\d+]", "", phone)
        encoded_text = urllib.parse.quote(message)
        url = f"sms:{cleaned_phone}&body={encoded_text}"
        webbrowser.open(url)
        return True

    def send_via_twilio(self, phone, message, is_whatsapp=False):
        sid = self.engine.get_setting("twilio_sid").strip()
        token = self.engine.get_setting("twilio_token").strip()
        from_phone = self.engine.get_setting("twilio_phone").strip()

        if not sid or not token or not from_phone:
            return False, "Twilio credentials are not configured in Settings."

        to_number = phone
        from_number = from_phone
        if is_whatsapp:
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            if not from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{from_number}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = urllib.parse.urlencode({"To": to_number, "From": from_number, "Body": message}).encode("utf-8")

        auth_str = f"{sid}:{token}"
        auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Basic {auth_bytes}")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                return True, f"Sent successfully! SID: {res_body.get('sid')}"
        except urllib.error.HTTPError as e:
            err_content = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_content)
                return False, f"Twilio Error: {err_json.get('message', err_content)}"
            except Exception:
                return False, f"Twilio HTTP Error {e.code}: {err_content}"
        except Exception as e:
            return False, f"Network Error: {str(e)}"


# ============================================================================
# 4. REDEFINED MODERN MULTI-COLOR UI (SPLITEXPENSE)
# ============================================================================

class SplitExpenseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SplitExpense • Smart Expense Tracking & Settlement Tool")
        self.root.geometry("1140x840")
        self.root.minsize(1000, 720)

        # --------------------------------------------------------------------
        # REDEFINED COLOR PALETTE - HARMONIOUS MULTI-COLOR VIBRANCY
        # --------------------------------------------------------------------
        # Foundations
        self.BG_MAIN = "#0B0F19"         # Deep Slate-Black canvas
        self.BG_SURFACE = "#151D2C"      # Primary Card / Panel surface
        self.BG_SURFACE_ALT = "#1A2436"  # Alternating / hover surface
        self.BG_INPUT = "#0C121E"        # Inset text input & dropdowns
        self.BORDER_COLOR = "#253347"    # Sleek border line
        self.BORDER_LIGHT = "#334560"    # Focused border line
        self.HEADER_BG = "#080C14"       # Top header banner background

        # Text Hierarchy
        self.TEXT_MAIN = "#F8FAFC"       # Crisp high-contrast white text
        self.TEXT_MUTED = "#8B9BB4"      # Secondary caption text
        self.TEXT_DIM = "#566885"        # Subdued hints

        # Vibrant Multi-Color Accents
        self.COLOR_INDIGO = "#6366F1"    # Royal Indigo / Accent
        self.COLOR_CYAN = "#06B6D4"      # Electric Cyan
        self.COLOR_SKY = "#38BDF8"       # Bright Sky Blue
        self.COLOR_EMERALD = "#10B981"   # Vibrant Emerald Green (Add / Positive)
        self.COLOR_ROSE = "#F43F5E"      # Bold Rose Pink/Red (Deduct / Owes)
        self.COLOR_AMBER = "#F59E0B"     # Warm Amber Orange (Settle / Warning)
        self.COLOR_PURPLE = "#A855F7"    # Radiant Violet / Purple
        self.COLOR_CORAL = "#FB923C"     # Vivid Coral Tangerine
        self.COLOR_TEAL = "#14B8A6"      # Deep Teal

        # Backward compatibility aliases
        self.ACCENT_CYAN = self.COLOR_SKY
        self.ACCENT_GREEN = self.COLOR_EMERALD
        self.ACCENT_ROSE = self.COLOR_ROSE
        self.ACCENT_AMBER = self.COLOR_AMBER

        self.db = Database()
        self.engine = SplitwiseEngine(self.db)
        self.notifier = NotificationService(self.engine)

        self.current_group_id = None
        self.currency = self.engine.get_setting("currency", "₹")

        self._configure_styles()
        self._build_main_ui()
        self.refresh_all()

    def _configure_styles(self):
        self.root.configure(bg=self.BG_MAIN)
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # General TTK defaults
        self.style.configure(".", font=("Helvetica", 10), background=self.BG_MAIN, foreground=self.TEXT_MAIN)

        # Containers
        self.style.configure("TFrame", background=self.BG_MAIN)
        self.style.configure("Surface.TFrame", background=self.BG_SURFACE)

        # LabelFrames
        self.style.configure(
            "TLabelframe",
            background=self.BG_SURFACE,
            foreground=self.TEXT_MAIN,
            bordercolor=self.BORDER_COLOR,
            lightcolor=self.BORDER_COLOR,
            darkcolor=self.BORDER_COLOR,
            borderwidth=1,
            relief="solid",
        )
        self.style.configure(
            "TLabelframe.Label",
            background=self.BG_SURFACE,
            foreground=self.COLOR_SKY,
            font=("Helvetica", 10, "bold"),
        )

        # Labels
        self.style.configure("TLabel", background=self.BG_SURFACE, foreground=self.TEXT_MAIN)
        self.style.configure("Muted.TLabel", background=self.BG_SURFACE, foreground=self.TEXT_MUTED, font=("Helvetica", 9))
        self.style.configure("Header.TLabel", background=self.HEADER_BG, foreground=self.TEXT_MAIN)

        # Multi-Color Notebook Navigation Tabs
        self.style.configure("TNotebook", background=self.BG_MAIN, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background=self.BG_SURFACE,
            foreground=self.TEXT_MUTED,
            font=("Helvetica", 10, "bold"),
            padding=[18, 9],
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", self.COLOR_INDIGO), ("active", "#1E2A40")],
            foreground=[("selected", "#FFFFFF"), ("active", self.TEXT_MAIN)],
        )

        # Treeview (Data Tables with Redefined Styling)
        self.style.configure(
            "Treeview",
            background=self.BG_SURFACE,
            foreground=self.TEXT_MAIN,
            fieldbackground=self.BG_SURFACE,
            borderwidth=0,
            rowheight=32,
            font=("Helvetica", 10),
        )
        self.style.configure(
            "Treeview.Heading",
            background="#121824",
            foreground=self.COLOR_SKY,
            relief="flat",
            font=("Helvetica", 10, "bold"),
            padding=[8, 7],
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#1A2436")],
            foreground=[("active", "#FFFFFF")],
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#2A3A54")],
            foreground=[("selected", "#FFFFFF")],
        )

        # Comboboxes
        self.style.configure(
            "TCombobox",
            fieldbackground=self.BG_INPUT,
            background=self.BORDER_COLOR,
            foreground=self.TEXT_MAIN,
            arrowcolor=self.COLOR_SKY,
            darkcolor=self.BORDER_COLOR,
            lightcolor=self.BORDER_COLOR,
            bordercolor=self.BORDER_COLOR,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.BG_INPUT), ("active", self.BG_INPUT)],
            foreground=[("readonly", self.TEXT_MAIN), ("active", self.TEXT_MAIN)],
        )

        # Entries
        self.style.configure(
            "TEntry",
            fieldbackground=self.BG_INPUT,
            foreground=self.TEXT_MAIN,
            insertcolor=self.TEXT_MAIN,
            bordercolor=self.BORDER_COLOR,
            lightcolor=self.BORDER_COLOR,
            darkcolor=self.BORDER_COLOR,
        )

        # Radiobuttons & Checkbuttons
        self.style.configure(
            "TRadiobutton",
            background=self.BG_SURFACE,
            foreground=self.TEXT_MAIN,
            indicatorcolor=self.BG_INPUT,
            focuscolor=self.COLOR_SKY,
        )
        self.style.map(
            "TRadiobutton",
            background=[("active", self.BG_SURFACE)],
            foreground=[("active", self.COLOR_SKY)],
            indicatorcolor=[("selected", self.COLOR_EMERALD)],
        )

        self.style.configure(
            "TCheckbutton",
            background=self.BG_SURFACE,
            foreground=self.TEXT_MAIN,
            indicatorcolor=self.BG_INPUT,
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", self.BG_SURFACE)],
            foreground=[("active", self.COLOR_SKY)],
            indicatorcolor=[("selected", self.COLOR_EMERALD)],
        )

        # Custom Redefined Multi-Color Action Buttons
        self.style.configure(
            "Primary.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_EMERALD,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Primary.TButton", background=[("active", "#059669")])

        self.style.configure(
            "Indigo.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_INDIGO,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Indigo.TButton", background=[("active", "#4F46E5")])

        self.style.configure(
            "Cyan.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_CYAN,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Cyan.TButton", background=[("active", "#0891B2")])

        self.style.configure(
            "Amber.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_AMBER,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Amber.TButton", background=[("active", "#D97706")])

        self.style.configure(
            "Purple.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_PURPLE,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Purple.TButton", background=[("active", "#9333EA")])

        self.style.configure(
            "Danger.TButton",
            font=("Helvetica", 10, "bold"),
            background=self.COLOR_ROSE,
            foreground="#FFFFFF",
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Danger.TButton", background=[("active", "#E11D48")])

        self.style.configure(
            "Secondary.TButton",
            font=("Helvetica", 10),
            background="#253347",
            foreground=self.TEXT_MAIN,
            borderwidth=0,
            padding=[12, 6],
        )
        self.style.map("Secondary.TButton", background=[("active", "#334560")])

    def _build_main_ui(self):
        # --------------------------------------------------------------------
        # 1. SLEEK MULTI-COLOR GRADIENT-ACCENTED HEADER
        # --------------------------------------------------------------------
        header = tk.Frame(self.root, bg=self.HEADER_BG, height=84, bd=0)
        header.pack(fill=tk.X, side=tk.TOP)

        # Multi-Color Top Glowing Accent Line
        glow_line = tk.Frame(header, height=3, bg=self.HEADER_BG)
        glow_line.pack(fill=tk.X, side=tk.TOP)
        colors_glow = [self.COLOR_CYAN, self.COLOR_INDIGO, self.COLOR_PURPLE, self.COLOR_EMERALD, self.COLOR_AMBER, self.COLOR_ROSE]
        for c in colors_glow:
            tk.Frame(glow_line, bg=c, height=3).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header_content = tk.Frame(header, bg=self.HEADER_BG)
        header_content.pack(fill=tk.BOTH, expand=True, padx=22, pady=10)

        title_frame = tk.Frame(header_content, bg=self.HEADER_BG)
        title_frame.pack(side=tk.LEFT)

        logo_title_row = tk.Frame(title_frame, bg=self.HEADER_BG)
        logo_title_row.pack(anchor=tk.W)

        tk.Label(logo_title_row, text="⚡ SplitExpense", font=("Helvetica", 20, "bold"), fg=self.COLOR_SKY, bg=self.HEADER_BG).pack(side=tk.LEFT)

        # Modern Rounded Badge Pills
        badge_pro = tk.Label(logo_title_row, text=" PRO ", font=("Helvetica", 8, "bold"), fg="#FFFFFF", bg=self.COLOR_INDIGO, padx=6, pady=1)
        badge_pro.pack(side=tk.LEFT, padx=6)

        badge_live = tk.Label(logo_title_row, text=" ● ACTIVE ", font=("Helvetica", 7, "bold"), fg=self.COLOR_EMERALD, bg="#0D281E", padx=6, pady=2)
        badge_live.pack(side=tk.LEFT, padx=2)

        tk.Label(
            title_frame,
            text="Intelligent Expense Splitting • Multi-Color Ambience • Real-Time Added & Subtracted Ledger",
            font=("Helvetica", 9),
            fg=self.TEXT_MUTED,
            bg=self.HEADER_BG,
        ).pack(anchor=tk.W, pady=(3, 0))

        # Right Active Group Selector with custom styling
        group_sel_frame = tk.Frame(header_content, bg=self.HEADER_BG)
        group_sel_frame.pack(side=tk.RIGHT, pady=6)

        tk.Label(group_sel_frame, text="Active Group:", font=("Helvetica", 10, "bold"), fg=self.COLOR_CYAN, bg=self.HEADER_BG).pack(side=tk.LEFT, padx=(0, 8))
        self.top_group_var = tk.StringVar(value="All Groups")
        self.top_group_combo = ttk.Combobox(group_sel_frame, textvariable=self.top_group_var, state="readonly", width=22)
        self.top_group_combo.pack(side=tk.LEFT)
        self.top_group_combo.bind("<<ComboboxSelected>>", self._on_top_group_changed)

        # --------------------------------------------------------------------
        # 2. MAIN TABBED NOTEBOOK
        # --------------------------------------------------------------------
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        self.tab_dashboard = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_dashboard, text="  📊 Dashboard & Balances  ")
        self._build_dashboard_tab()

        self.tab_add_expense = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_add_expense, text="  ➕ Add New Expense  ")
        self._build_add_expense_tab()

        self.tab_expenses = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_expenses, text="  📜 Expenses History  ")
        self._build_expenses_tab()

        self.tab_settlements = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_settlements, text="  💬 Settle Up & Reminders  ")
        self._build_settlements_tab()

        self.tab_members = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_members, text="  👥 Groups & Members  ")
        self._build_members_tab()

        self.tab_settings = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_settings, text="  ⚙️ Settings  ")
        self._build_settings_tab()

        # --------------------------------------------------------------------
        # 3. BOTTOM MULTI-COLOR STATUS BAR
        # --------------------------------------------------------------------
        status_container = tk.Frame(self.root, bg=self.HEADER_BG, height=28)
        status_container.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_bar = tk.Label(
            status_container,
            text="Ready • SplitExpense Multi-Color Engine Active",
            bd=0,
            anchor=tk.W,
            font=("Helvetica", 9),
            bg=self.HEADER_BG,
            fg=self.TEXT_MUTED,
            padx=14,
            pady=4,
        )
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Right status indicator
        tk.Label(
            status_container,
            text="● Engine Online",
            font=("Helvetica", 8, "bold"),
            bg=self.HEADER_BG,
            fg=self.COLOR_EMERALD,
            padx=14,
        ).pack(side=tk.RIGHT)

    # ========================================================================
    # TAB 1: DASHBOARD & DEBT SIMPLIFICATION
    # ========================================================================
    def _build_dashboard_tab(self):
        # 4 Enhanced Color-Coded KPI Cards
        kpi_frame = tk.Frame(self.tab_dashboard, bg=self.BG_MAIN)
        kpi_frame.pack(fill=tk.X, pady=(0, 12))

        self.kpi_total_spent = self._create_enhanced_kpi_card(
            kpi_frame, "Total Spent", f"{self.currency}0.00", self.COLOR_CYAN, "💰", "Group Total"
        )
        self.kpi_total_spent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.kpi_total_expenses = self._create_enhanced_kpi_card(
            kpi_frame, "Expenses Logged", "0", self.COLOR_PURPLE, "🧾", "Activity"
        )
        self.kpi_total_expenses.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.kpi_debts_count = self._create_enhanced_kpi_card(
            kpi_frame, "Pending Debts", "0", self.COLOR_AMBER, "⚖️", "Unsettled"
        )
        self.kpi_debts_count.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.kpi_members_count = self._create_enhanced_kpi_card(
            kpi_frame, "Active Members", "0", self.COLOR_EMERALD, "👥", "Directory"
        )
        self.kpi_members_count.pack(side=tk.LEFT, fill=tk.X, expand=True)

        split_frame = tk.Frame(self.tab_dashboard, bg=self.BG_MAIN)
        split_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Net Balances Card
        left_card = ttk.LabelFrame(split_frame, text=" Member Net Balances (Added & Subtracted Breakdown) ", padding=12)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns_bal = ("name", "paid", "owed", "settled", "balance", "status")
        self.tree_balances = ttk.Treeview(left_card, columns=columns_bal, show="headings", height=13)
        self.tree_balances.heading("name", text="Member")
        self.tree_balances.heading("paid", text="Total Paid (+)")
        self.tree_balances.heading("owed", text="Total Share (-)")
        self.tree_balances.heading("settled", text="Settled")
        self.tree_balances.heading("balance", text="Final Balance")
        self.tree_balances.heading("status", text="Status")

        self.tree_balances.column("name", width=130)
        self.tree_balances.column("paid", width=105, anchor=tk.E)
        self.tree_balances.column("owed", width=105, anchor=tk.E)
        self.tree_balances.column("settled", width=85, anchor=tk.E)
        self.tree_balances.column("balance", width=115, anchor=tk.E)
        self.tree_balances.column("status", width=120, anchor=tk.CENTER)

        # Configure color-coded tag appearances for balances table
        self.tree_balances.tag_configure("positive", foreground=self.COLOR_EMERALD)
        self.tree_balances.tag_configure("negative", foreground=self.COLOR_ROSE)
        self.tree_balances.tag_configure("settled", foreground=self.TEXT_MUTED)

        self.tree_balances.pack(fill=tk.BOTH, expand=True)

        bal_btn_row = tk.Frame(left_card, bg=self.BG_SURFACE)
        bal_btn_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(bal_btn_row, text="🔍 View Member Account Ledger", style="Indigo.TButton", command=self.handle_view_member_ledger).pack(side=tk.LEFT)

        # Right: Simplified Debts Card
        right_card = ttk.LabelFrame(split_frame, text=" Simplified Settlement Plan (Direct Pay Plan) ", padding=12)
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        columns_plan = ("from", "arrow", "to", "amount", "actions")
        self.tree_plan = ttk.Treeview(right_card, columns=columns_plan, show="headings", height=11)
        self.tree_plan.heading("from", text="Debtor (Owes)")
        self.tree_plan.heading("arrow", text="")
        self.tree_plan.heading("to", text="Creditor (Lender)")
        self.tree_plan.heading("amount", text="Amount")
        self.tree_plan.heading("actions", text="Status")

        self.tree_plan.column("from", width=125)
        self.tree_plan.column("arrow", width=32, anchor=tk.CENTER)
        self.tree_plan.column("to", width=125)
        self.tree_plan.column("amount", width=95, anchor=tk.E)
        self.tree_plan.column("actions", width=90, anchor=tk.CENTER)

        self.tree_plan.tag_configure("debt_row", foreground="#FCD34D")

        self.tree_plan.pack(fill=tk.BOTH, expand=True)

        plan_btn_frame = tk.Frame(right_card, bg=self.BG_SURFACE)
        plan_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(plan_btn_frame, text="💬 WhatsApp Reminder", style="Primary.TButton", command=self.handle_send_reminder_from_plan).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(plan_btn_frame, text="✓ Settle Debt", style="Amber.TButton", command=self.handle_record_settlement_from_plan).pack(side=tk.LEFT)

    def _create_enhanced_kpi_card(self, parent, title, value, accent_color, icon="", pill_text=""):
        # Modern Card with individual color accent stripe on left
        outer_card = tk.Frame(parent, bg=self.BORDER_COLOR, bd=0, padx=1, pady=1)

        card = tk.Frame(outer_card, bg=self.BG_SURFACE, bd=0)
        card.pack(fill=tk.BOTH, expand=True)

        # Left color bar
        left_bar = tk.Frame(card, bg=accent_color, width=4)
        left_bar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(card, bg=self.BG_SURFACE, padx=12, pady=10)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header Row
        top_row = tk.Frame(content, bg=self.BG_SURFACE)
        top_row.pack(fill=tk.X)

        tk.Label(top_row, text=f"{icon} {title}", font=("Helvetica", 9, "bold"), fg=self.TEXT_MUTED, bg=self.BG_SURFACE).pack(side=tk.LEFT)

        if pill_text:
            pill = tk.Label(top_row, text=f" {pill_text} ", font=("Helvetica", 7, "bold"), fg=accent_color, bg="#111B28", padx=4, pady=1)
            pill.pack(side=tk.RIGHT)

        val_lbl = tk.Label(content, text=value, font=("Helvetica", 16, "bold"), fg=accent_color, bg=self.BG_SURFACE)
        val_lbl.pack(anchor=tk.W, pady=(3, 0))

        outer_card.val_lbl = val_lbl
        return outer_card

    def _create_dark_kpi_card(self, parent, title, value, color, icon=""):
        return self._create_enhanced_kpi_card(parent, title, value, color, icon)

    def handle_view_member_ledger(self):
        selected = self.tree_balances.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a member from the table to view their account ledger.")
            return

        m_name = self.tree_balances.item(selected[0])["values"][0]
        member = None
        for m in self.engine.get_members():
            if m["name"] == m_name:
                member = m
                break
        if not member:
            return

        ledger = self.engine.get_member_ledger(member["id"], self.current_group_id)

        modal = tk.Toplevel(self.root)
        modal.title(f"Account Statement • {member['name']}")
        modal.geometry("780x500")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)

        header_frame = tk.Frame(modal, bg=self.HEADER_BG, padx=18, pady=14)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text=f"📊 Account Statement for {member['name']}", font=("Helvetica", 13, "bold"), fg=self.COLOR_SKY, bg=self.HEADER_BG).pack(anchor=tk.W)
        tk.Label(header_frame, text="Complete audit trail showing every transaction where amount was Added (+) or Subtracted (-)", font=("Helvetica", 9), fg=self.TEXT_MUTED, bg=self.HEADER_BG).pack(anchor=tk.W, pady=(2, 0))

        columns = ("date", "desc", "added", "subtracted", "net")
        tree = ttk.Treeview(modal, columns=columns, show="headings", height=12)
        tree.heading("date", text="Date")
        tree.heading("desc", text="Transaction Details")
        tree.heading("added", text="Added (+)")
        tree.heading("subtracted", text="Subtracted (-)")
        tree.heading("net", text="Net Impact")

        tree.column("date", width=95)
        tree.column("desc", width=340)
        tree.column("added", width=105, anchor=tk.E)
        tree.column("subtracted", width=105, anchor=tk.E)
        tree.column("net", width=105, anchor=tk.E)

        tree.tag_configure("pos_tx", foreground=self.COLOR_EMERALD)
        tree.tag_configure("neg_tx", foreground=self.COLOR_ROSE)

        for item in ledger:
            add_str = f"+{self.currency}{item['added']:.2f}" if item['added'] > 0 else "—"
            sub_str = f"-{self.currency}{item['subtracted']:.2f}" if item['subtracted'] > 0 else "—"
            net_sign = "+" if item['net_change'] > 0 else ""
            tag = "pos_tx" if item['net_change'] > 0 else "neg_tx"
            tree.insert("", tk.END, values=(
                item["date"],
                item["description"],
                add_str,
                sub_str,
                f"{net_sign}{self.currency}{item['net_change']:.2f}"
            ), tags=(tag,))

        tree.pack(fill=tk.BOTH, expand=True, padx=18, pady=10)
        ttk.Button(modal, text="Close Statement", style="Secondary.TButton", command=modal.destroy).pack(pady=(0, 14))

    # ========================================================================
    # TAB 2: ADD NEW EXPENSE (INTUITIVE ALLOCATION MODES)
    # ========================================================================
    def _build_add_expense_tab(self):
        container = ttk.Frame(self.tab_add_expense, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        # 1. Expense Details Card
        detail_card = ttk.LabelFrame(container, text=" 1. Expense Details ", padding=12)
        detail_card.pack(fill=tk.X, pady=(0, 10))

        row1 = tk.Frame(detail_card, bg=self.BG_SURFACE)
        row1.pack(fill=tk.X, pady=4)

        tk.Label(row1, text="Description *:", width=14, anchor=tk.W, fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        self.exp_desc_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.exp_desc_var, width=30).pack(side=tk.LEFT, padx=(0, 24))

        tk.Label(row1, text="Total Amount *:", width=14, anchor=tk.W, fg=self.COLOR_EMERALD, bg=self.BG_SURFACE, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        self.exp_amt_var = tk.StringVar()
        amt_entry = ttk.Entry(row1, textvariable=self.exp_amt_var, width=16)
        amt_entry.pack(side=tk.LEFT)
        amt_entry.bind("<KeyRelease>", lambda e: self._on_expense_input_change())

        row2 = tk.Frame(detail_card, bg=self.BG_SURFACE)
        row2.pack(fill=tk.X, pady=4)

        tk.Label(row2, text="Paid By *:", width=14, anchor=tk.W, fg=self.COLOR_SKY, bg=self.BG_SURFACE, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        self.exp_payer_var = tk.StringVar()
        self.exp_payer_combo = ttk.Combobox(row2, textvariable=self.exp_payer_var, state="readonly", width=28)
        self.exp_payer_combo.pack(side=tk.LEFT, padx=(0, 24))
        self.exp_payer_combo.bind("<<ComboboxSelected>>", lambda e: self._on_payer_changed())

        tk.Label(row2, text="Category:", width=14, anchor=tk.W, fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        self.exp_cat_var = tk.StringVar(value="Food & Dining")
        categories = ["Food & Dining", "Travel & Taxi", "Groceries", "Rent & Housing", "Utilities & Bills", "Entertainment", "Shopping", "Other"]
        ttk.Combobox(row2, textvariable=self.exp_cat_var, values=categories, state="readonly", width=16).pack(side=tk.LEFT)

        row3 = tk.Frame(detail_card, bg=self.BG_SURFACE)
        row3.pack(fill=tk.X, pady=4)

        tk.Label(row3, text="Group:", width=14, anchor=tk.W, fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        self.exp_group_var = tk.StringVar()
        self.exp_group_combo = ttk.Combobox(row3, textvariable=self.exp_group_var, state="readonly", width=28)
        self.exp_group_combo.pack(side=tk.LEFT, padx=(0, 24))
        self.exp_group_combo.bind("<<ComboboxSelected>>", self._on_expense_group_changed)

        tk.Label(row3, text="Date (YYYY-MM-DD):", width=14, anchor=tk.W, fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        self.exp_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(row3, textvariable=self.exp_date_var, width=16).pack(side=tk.LEFT)

        # 2. Allocation & Split Mode Card
        split_card = ttk.LabelFrame(container, text=" 2. How is this amount Added & Subtracted? ", padding=12)
        split_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        mode_frame = tk.Frame(split_card, bg=self.BG_SURFACE)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        tk.Label(mode_frame, text="Allocation Mode:", font=("Helvetica", 10, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).pack(side=tk.LEFT, padx=(0, 12))
        self.split_strategy_var = tk.StringVar(value="EQUAL_INCL")

        modes = [
            ("FULL_ONE", "🎯 Full to One Person"),
            ("EQUAL_EXCL", "👥 Paid for Others (Exclude Payer)"),
            ("EQUAL_INCL", "🍕 Shared (Include Payer)"),
            ("EXACT", "₹ Exact Amounts"),
            ("PERCENT", "% Percentages"),
            ("SHARES", "⚖ By Shares"),
        ]

        for code, label in modes:
            ttk.Radiobutton(mode_frame, text=label, value=code, variable=self.split_strategy_var, command=self._on_split_strategy_changed).pack(side=tk.LEFT, padx=6)

        # Dynamic Single Person Selector (shown only if FULL_ONE selected)
        self.single_person_frame = tk.Frame(split_card, bg=self.BG_SURFACE)
        tk.Label(self.single_person_frame, text="Who owes this full amount? (Borrower):", font=("Helvetica", 10, "bold"), fg=self.COLOR_ROSE, bg=self.BG_SURFACE).pack(side=tk.LEFT, padx=(0, 10))
        self.single_borrower_var = tk.StringVar()
        self.single_borrower_combo = ttk.Combobox(self.single_person_frame, textvariable=self.single_borrower_var, state="readonly", width=26)
        self.single_borrower_combo.pack(side=tk.LEFT)
        self.single_borrower_combo.bind("<<ComboboxSelected>>", lambda e: self._recalculate_splits())

        # Participant list with dynamic inputs based on mode
        self.split_table_frame = tk.Frame(split_card, bg=self.BG_SURFACE)
        self.split_table_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        # Live Balance Impact Box (Multi-Color Accent Card)
        self.impact_box = tk.Frame(split_card, bg="#0E1726", highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=14, pady=8)
        self.impact_box.pack(fill=tk.X, pady=(6, 0))

        self.impact_lbl_title = tk.Label(self.impact_box, text="💡 Live Balance Impact (Preview before saving):", font=("Helvetica", 9, "bold"), fg=self.COLOR_SKY, bg="#0E1726")
        self.impact_lbl_title.pack(anchor=tk.W)

        self.impact_lbl_details = tk.Label(self.impact_box, text="", font=("Helvetica", 9), fg="#E2E8F0", bg="#0E1726", justify=tk.LEFT)
        self.impact_lbl_details.pack(anchor=tk.W, pady=(2, 0))

        # Validation status
        self.split_calc_status = tk.Label(split_card, text="", font=("Helvetica", 9, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE)
        self.split_calc_status.pack(anchor=tk.W, pady=(6, 0))

        # Bottom Action Buttons
        btn_frame = tk.Frame(container, bg=self.BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        self.save_expense_btn = ttk.Button(btn_frame, text="💾 Save Expense & Notify Members", style="Primary.TButton", command=self.handle_save_expense)
        self.save_expense_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="Clear Form", style="Secondary.TButton", command=self.clear_add_expense_form).pack(side=tk.LEFT)

    def _on_payer_changed(self):
        self._update_borrower_combo_values()
        self._recalculate_splits()

    def _update_borrower_combo_values(self):
        payer_name = self.exp_payer_var.get()
        members = self._get_active_group_members()
        other_members = [m["name"] for m in members if m["name"] != payer_name]
        self.single_borrower_combo["values"] = other_members
        if other_members and not self.single_borrower_var.get():
            self.single_borrower_var.set(other_members[0])
        elif self.single_borrower_var.get() == payer_name and other_members:
            self.single_borrower_var.set(other_members[0])

    def _get_active_group_members(self):
        group_name = self.exp_group_var.get()
        group_id = None
        for g in self.engine.get_groups():
            if g["name"] == group_name:
                group_id = g["id"]
                break
        return self.engine.get_group_members(group_id) if group_id else self.engine.get_members()

    def _on_expense_group_changed(self, event=None):
        self._update_borrower_combo_values()
        self._populate_expense_participants()

    def _on_expense_input_change(self):
        self._recalculate_splits()

    def _on_split_strategy_changed(self):
        mode = self.split_strategy_var.get()
        if mode == "FULL_ONE":
            self.single_person_frame.pack(fill=tk.X, pady=(4, 8), before=self.split_table_frame)
            self.split_table_frame.pack_forget()
        else:
            self.single_person_frame.pack_forget()
            self.split_table_frame.pack(fill=tk.BOTH, expand=True, pady=4)
            self._update_participant_checkboxes_for_mode(mode)

        self._recalculate_splits()

    def _update_participant_checkboxes_for_mode(self, mode):
        payer_name = self.exp_payer_var.get()
        for r in getattr(self, "participant_rows", []):
            is_payer = (r["member"]["name"] == payer_name)
            if mode == "EQUAL_EXCL":
                r["included"].set(not is_payer)
            elif mode == "EQUAL_INCL":
                r["included"].set(True)

    def _populate_expense_participants(self):
        for widget in self.split_table_frame.winfo_children():
            widget.destroy()

        members = self._get_active_group_members()
        payer_name = self.exp_payer_var.get()
        mode = self.split_strategy_var.get()

        self.participant_rows = []

        h_frame = tk.Frame(self.split_table_frame, bg=self.BG_SURFACE)
        h_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(h_frame, text="Participates?", width=13, font=("Helvetica", 9, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Member Name", width=24, anchor=tk.W, font=("Helvetica", 9, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Input (₹ / % / sh)", width=18, font=("Helvetica", 9, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).pack(side=tk.LEFT)
        tk.Label(h_frame, text="Subtracted Amount", width=18, font=("Helvetica", 9, "bold"), fg=self.COLOR_ROSE, bg=self.BG_SURFACE).pack(side=tk.LEFT)

        canvas = tk.Canvas(self.split_table_frame, borderwidth=0, highlightthickness=0, height=135, bg=self.BG_SURFACE)
        scrollbar = ttk.Scrollbar(self.split_table_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.BG_SURFACE)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for m in members:
            r = tk.Frame(scrollable_frame, bg=self.BG_SURFACE)
            r.pack(fill=tk.X, pady=3)

            is_payer = (m["name"] == payer_name)
            initial_inc = True
            if mode == "EQUAL_EXCL" and is_payer:
                initial_inc = False

            inc_var = tk.BooleanVar(value=initial_inc)
            cb = ttk.Checkbutton(r, variable=inc_var, command=self._recalculate_splits)
            cb.pack(side=tk.LEFT, padx=(4, 12))

            name_tag = f"{m['name']} (Payer)" if is_payer else m["name"]
            tk.Label(r, text=name_tag, width=24, anchor=tk.W, fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)

            val_var = tk.StringVar(value="")
            entry = ttk.Entry(r, textvariable=val_var, width=14)
            entry.pack(side=tk.LEFT, padx=(0, 14))
            entry.bind("<KeyRelease>", lambda e: self._recalculate_splits())

            share_lbl = tk.Label(r, text=f"-{self.currency}0.00", width=18, fg=self.COLOR_ROSE, bg=self.BG_SURFACE, font=("Helvetica", 9, "bold"))
            share_lbl.pack(side=tk.LEFT)

            self.participant_rows.append({
                "member": m,
                "included": inc_var,
                "val_var": val_var,
                "entry": entry,
                "share_lbl": share_lbl,
                "calculated_amount": 0.0
            })

        self._recalculate_splits()

    def _recalculate_splits(self):
        try:
            total_amt = float(self.exp_amt_var.get().strip() or "0")
        except ValueError:
            total_amt = 0.0

        mode = self.split_strategy_var.get()
        payer_name = self.exp_payer_var.get()

        impact_lines = []

        if mode == "FULL_ONE":
            borrower_name = self.single_borrower_var.get()
            if not borrower_name or borrower_name == payer_name:
                self.split_calc_status.config(text="⚠ Select a borrower different from the payer.", fg=self.COLOR_ROSE)
                self.impact_lbl_details.config(text="")
                return

            self.split_calc_status.config(
                text=f"✓ Full amount {self.currency}{total_amt:.2f} is added to {payer_name} and subtracted from {borrower_name}.",
                fg=self.COLOR_EMERALD
            )
            impact_lines.append(f"• {payer_name} (Payer): +{self.currency}{total_amt:.2f} (Added to balance)")
            impact_lines.append(f"• {borrower_name} (Borrower): -{self.currency}{total_amt:.2f} (Subtracted from balance)")
            self.impact_lbl_details.config(text="\n".join(impact_lines))
            return

        included_rows = [r for r in getattr(self, "participant_rows", []) if r["included"].get()]

        if not included_rows:
            self.split_calc_status.config(text="⚠ Select at least one participant.", fg=self.COLOR_ROSE)
            self.impact_lbl_details.config(text="")
            return

        if mode in ("EQUAL_INCL", "EQUAL_EXCL"):
            count = len(included_rows)
            base_share = round(total_amt / count, 2)
            diff = round(total_amt - (base_share * count), 2)

            allocated_first = False
            for r in self.participant_rows:
                r["entry"].config(state="disabled")
                if r["included"].get():
                    owed = base_share + (diff if not allocated_first else 0.0)
                    allocated_first = True
                    r["calculated_amount"] = owed
                    r["share_lbl"].config(text=f"-{self.currency}{owed:.2f}")
                else:
                    r["calculated_amount"] = 0.0
                    r["share_lbl"].config(text=f"{self.currency}0.00")

            mode_desc = "including payer" if mode == "EQUAL_INCL" else "excluding payer"
            self.split_calc_status.config(
                text=f"✓ Split equally ({mode_desc}) among {count} members: ~{self.currency}{base_share:.2f} each. Total: {self.currency}{total_amt:.2f}",
                fg=self.COLOR_EMERALD
            )

        elif mode == "EXACT":
            sum_exact = 0.0
            for r in self.participant_rows:
                r["entry"].config(state="normal")
                if r["included"].get():
                    try:
                        amt = float(r["val_var"].get() or "0")
                    except ValueError:
                        amt = 0.0
                    r["calculated_amount"] = amt
                    r["share_lbl"].config(text=f"-{self.currency}{amt:.2f}")
                    sum_exact += amt
                else:
                    r["calculated_amount"] = 0.0
                    r["share_lbl"].config(text=f"{self.currency}0.00")

            diff = round(total_amt - sum_exact, 2)
            if abs(diff) < 0.01:
                self.split_calc_status.config(text=f"✓ Exact amounts sum correctly to {self.currency}{total_amt:.2f}", fg=self.COLOR_EMERALD)
            elif diff > 0:
                self.split_calc_status.config(text=f"⚠ Remaining to allocate: {self.currency}{diff:.2f}", fg=self.COLOR_AMBER)
            else:
                self.split_calc_status.config(text=f"⚠ Overallocated by: {self.currency}{-diff:.2f}", fg=self.COLOR_ROSE)

        elif mode == "PERCENT":
            sum_pct = 0.0
            for r in self.participant_rows:
                r["entry"].config(state="normal")
                if r["included"].get():
                    try:
                        pct = float(r["val_var"].get() or "0")
                    except ValueError:
                        pct = 0.0
                    amt = round(total_amt * (pct / 100.0), 2)
                    r["calculated_amount"] = amt
                    r["share_lbl"].config(text=f"-{self.currency}{amt:.2f} ({pct}%)")
                    sum_pct += pct
                else:
                    r["calculated_amount"] = 0.0
                    r["share_lbl"].config(text=f"{self.currency}0.00 (0%)")

            diff_pct = round(100.0 - sum_pct, 2)
            if abs(diff_pct) < 0.01:
                self.split_calc_status.config(text="✓ Percentages sum to 100%", fg=self.COLOR_EMERALD)
            elif diff_pct > 0:
                self.split_calc_status.config(text=f"⚠ Remaining % to allocate: {diff_pct:.1f}%", fg=self.COLOR_AMBER)
            else:
                self.split_calc_status.config(text=f"⚠ Total % exceeds 100% by {-diff_pct:.1f}%", fg=self.COLOR_ROSE)

        elif mode == "SHARES":
            total_shares = 0.0
            for r in self.participant_rows:
                r["entry"].config(state="normal")
                if r["included"].get():
                    try:
                        sh = float(r["val_var"].get() or "1")
                    except ValueError:
                        sh = 1.0
                    total_shares += sh

            if total_shares > 0:
                for r in self.participant_rows:
                    if r["included"].get():
                        try:
                            sh = float(r["val_var"].get() or "1")
                        except ValueError:
                            sh = 1.0
                        amt = round(total_amt * (sh / total_shares), 2)
                        r["calculated_amount"] = amt
                        r["share_lbl"].config(text=f"-{self.currency}{amt:.2f} ({sh} sh)")
                    else:
                        r["calculated_amount"] = 0.0
                        r["share_lbl"].config(text=f"{self.currency}0.00")

                self.split_calc_status.config(text=f"✓ Split proportionally by {total_shares} total shares", fg=self.COLOR_EMERALD)

        # Build live impact preview
        payer_share = 0.0
        for r in getattr(self, "participant_rows", []):
            if r["member"]["name"] == payer_name and r["included"].get():
                payer_share = r["calculated_amount"]

        net_payer = round(total_amt - payer_share, 2)
        impact_lines.append(f"• {payer_name} (Payer): Paid +{self.currency}{total_amt:.2f} | Share -{self.currency}{payer_share:.2f} ➔ Net Added: +{self.currency}{net_payer:.2f}")

        for r in getattr(self, "participant_rows", []):
            if r["member"]["name"] != payer_name and r["included"].get() and r["calculated_amount"] > 0:
                impact_lines.append(f"• {r['member']['name']}: Subtracted: -{self.currency}{r['calculated_amount']:.2f}")

        self.impact_lbl_details.config(text="\n".join(impact_lines))

    def handle_save_expense(self):
        desc = self.exp_desc_var.get().strip()
        amt_str = self.exp_amt_var.get().strip()
        payer_name = self.exp_payer_var.get()
        cat = self.exp_cat_var.get()
        date = self.exp_date_var.get().strip()
        group_name = self.exp_group_var.get()
        mode = self.split_strategy_var.get()

        if not desc:
            messagebox.showerror("Validation Error", "Please enter an expense description.")
            return

        try:
            total_amt = float(amt_str)
            if total_amt <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Please enter a valid positive expense amount.")
            return

        payer = None
        for m in self.engine.get_members():
            if m["name"] == payer_name:
                payer = m
                break
        if not payer:
            messagebox.showerror("Validation Error", "Please select who paid for this expense.")
            return

        group_id = None
        for g in self.engine.get_groups():
            if g["name"] == group_name:
                group_id = g["id"]
                break

        # Collect splits
        splits = []
        if mode == "FULL_ONE":
            borrower_name = self.single_borrower_var.get()
            borrower = None
            for m in self.engine.get_members():
                if m["name"] == borrower_name:
                    borrower = m
                    break
            if not borrower:
                messagebox.showerror("Validation Error", "Please select who owes this full amount.")
                return
            if borrower["id"] == payer["id"]:
                messagebox.showerror("Validation Error", "Payer and borrower cannot be the same member.")
                return

            splits.append((borrower["id"], total_amt))
            allocated_sum = total_amt
        else:
            allocated_sum = 0.0
            for r in getattr(self, "participant_rows", []):
                if r["included"].get():
                    owed = r["calculated_amount"]
                    splits.append((r["member"]["id"], owed))
                    allocated_sum += owed

            if not splits:
                messagebox.showerror("Validation Error", "Please select at least one participant.")
                return

            if abs(total_amt - allocated_sum) > 0.05:
                messagebox.showwarning(
                    "Split Sum Mismatch",
                    f"The allocated splits ({self.currency}{allocated_sum:.2f}) do not match the total amount ({self.currency}{total_amt:.2f}).\nPlease adjust the split values.",
                )
                return

        exp_id = self.engine.add_expense(group_id, desc, total_amt, payer["id"], mode, splits, cat, date)
        self.set_status(f"Expense '{desc}' saved successfully!")

        self.refresh_all()
        self._prompt_post_expense_notification(desc, total_amt, payer, splits)
        self.clear_add_expense_form()

    def _prompt_post_expense_notification(self, desc, total_amt, payer, splits):
        non_payer_splits = [(mid, amt) for mid, amt in splits if mid != payer["id"] and amt > 0.01]
        if not non_payer_splits:
            messagebox.showinfo("Expense Saved", f"Expense '{desc}' of {self.currency}{total_amt:.2f} logged successfully!")
            return

        ask_send = messagebox.askyesno(
            "Expense Saved • Notify Members?",
            f"Successfully logged '{desc}' ({self.currency}{total_amt:.2f})!\n\n"
            f"Would you like to send WhatsApp / SMS messages to the {len(non_payer_splits)} member(s) "
            "with their calculated share and lender's payment details?",
            icon="question",
        )

        if ask_send:
            self._open_multi_dispatch_modal(desc, total_amt, payer, non_payer_splits)

    def _open_multi_dispatch_modal(self, desc, total_amt, payer, non_payer_splits):
        modal = tk.Toplevel(self.root)
        modal.title("Send Expense Notifications • SplitExpense")
        modal.geometry("680x540")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)
        modal.grab_set()

        h_frame = tk.Frame(modal, bg=self.HEADER_BG, padx=18, pady=14)
        h_frame.pack(fill=tk.X)

        tk.Label(h_frame, text=f"📢 Send Share Notifications for '{desc}'", font=("Helvetica", 13, "bold"), fg=self.COLOR_SKY, bg=self.HEADER_BG).pack(anchor=tk.W)
        tk.Label(h_frame, text=f"Total: {self.currency}{total_amt:.2f} • Paid by: {payer['name']} (UPI: {payer.get('upi_id', 'N/A')})", font=("Helvetica", 10), fg=self.TEXT_MUTED, bg=self.HEADER_BG).pack(anchor=tk.W, pady=(2, 0))

        list_frame = tk.Frame(modal, bg=self.BG_MAIN, padx=18, pady=12)
        list_frame.pack(fill=tk.BOTH, expand=True)

        for mid, amt in non_payer_splits:
            m = self.engine.get_member(mid)
            if not m:
                continue

            card = tk.Frame(list_frame, bg=self.BG_SURFACE, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=14, pady=10)
            card.pack(fill=tk.X, pady=4)

            tk.Label(card, text=f"{m['name']} ({m.get('phone') or 'No phone'})", font=("Helvetica", 10, "bold"), fg=self.TEXT_MAIN, bg=self.BG_SURFACE).pack(side=tk.LEFT)
            tk.Label(card, text=f"Owes: {self.currency}{amt:.2f}", font=("Helvetica", 10, "bold"), fg=self.COLOR_ROSE, bg=self.BG_SURFACE).pack(side=tk.LEFT, padx=14)

            msg = self.notifier.generate_expense_alert_message(
                m["name"], payer["name"], desc, amt, total_amt, self.currency, payer.get("upi_id")
            )

            btn_box = tk.Frame(card, bg=self.BG_SURFACE)
            btn_box.pack(side=tk.RIGHT)

            wa_btn = ttk.Button(
                btn_box,
                text="💬 WhatsApp",
                style="Primary.TButton",
                command=lambda p=m.get("phone", ""), txt=msg: self._send_whatsapp_with_feedback(p, txt)
            )
            wa_btn.pack(side=tk.LEFT, padx=4)

            sms_btn = ttk.Button(
                btn_box,
                text="📱 SMS",
                style="Indigo.TButton",
                command=lambda p=m.get("phone", ""), txt=msg: self._send_sms_with_feedback(p, txt)
            )
            sms_btn.pack(side=tk.LEFT, padx=4)

        ttk.Button(modal, text="Done / Close", style="Secondary.TButton", command=modal.destroy).pack(pady=12)

    def clear_add_expense_form(self):
        self.exp_desc_var.set("")
        self.exp_amt_var.set("")
        self.exp_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self._populate_expense_participants()

    # ========================================================================
    # TAB 3: EXPENSES HISTORY
    # ========================================================================
    def _build_expenses_tab(self):
        top_bar = tk.Frame(self.tab_expenses, bg=self.BG_MAIN)
        top_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(top_bar, text="⟳ Refresh List", style="Secondary.TButton", command=self.refresh_expenses_table).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(top_bar, text="🗑 Delete Selected Expense", style="Danger.TButton", command=self.handle_delete_expense).pack(side=tk.LEFT)

        columns = ("id", "date", "desc", "cat", "group", "payer", "amt", "splits")
        self.tree_expenses = ttk.Treeview(self.tab_expenses, columns=columns, show="headings", height=15)
        self.tree_expenses.heading("id", text="ID")
        self.tree_expenses.heading("date", text="Date")
        self.tree_expenses.heading("desc", text="Description")
        self.tree_expenses.heading("cat", text="Category")
        self.tree_expenses.heading("group", text="Group")
        self.tree_expenses.heading("payer", text="Paid By (+Added)")
        self.tree_expenses.heading("amt", text="Total Amount")
        self.tree_expenses.heading("splits", text="Deductions (-Subtracted from)")

        self.tree_expenses.column("id", width=45, anchor=tk.CENTER)
        self.tree_expenses.column("date", width=100)
        self.tree_expenses.column("desc", width=180)
        self.tree_expenses.column("cat", width=115)
        self.tree_expenses.column("group", width=115)
        self.tree_expenses.column("payer", width=135)
        self.tree_expenses.column("amt", width=105, anchor=tk.E)
        self.tree_expenses.column("splits", width=260)

        # Alternating row tag colors
        self.tree_expenses.tag_configure("evenrow", background=self.BG_SURFACE)
        self.tree_expenses.tag_configure("oddrow", background=self.BG_SURFACE_ALT)

        scrollbar = ttk.Scrollbar(self.tab_expenses, orient=tk.VERTICAL, command=self.tree_expenses.yview)
        self.tree_expenses.configure(yscrollcommand=scrollbar.set)

        self.tree_expenses.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_expenses_table(self):
        for item in self.tree_expenses.get_children():
            self.tree_expenses.delete(item)

        expenses = self.engine.get_expenses(self.current_group_id)
        for idx, exp in enumerate(expenses):
            splits_summary = ", ".join([f"{s['member_name']}: -{self.currency}{s['amount_owed']:.0f}" for s in exp["splits"]])
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_expenses.insert(
                "",
                tk.END,
                values=(
                    exp["id"],
                    exp["date"],
                    exp["description"],
                    exp["category"],
                    exp.get("group_name") or "General",
                    f"{exp.get('payer_name')} (+{self.currency}{exp['amount']:.2f})",
                    f"{self.currency}{exp['amount']:.2f}",
                    splits_summary,
                ),
                tags=(tag,),
            )

    def handle_delete_expense(self):
        selected = self.tree_expenses.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an expense to delete.")
            return

        item = self.tree_expenses.item(selected[0])
        exp_id = item["values"][0]
        desc = item["values"][2]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete expense '{desc}'?\nThis will revert all added and subtracted amounts from members' balances."):
            self.engine.delete_expense(exp_id)
            self.set_status(f"Deleted expense #{exp_id}.")
            self.refresh_all()

    # ========================================================================
    # TAB 4: SETTLEMENTS & REMINDERS DISPATCHER
    # ========================================================================
    def _build_settlements_tab(self):
        top_frame = ttk.LabelFrame(self.tab_settlements, text=" Outstanding Simplified Debts & Reminders ", padding=12)
        top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        columns_debt = ("from", "from_phone", "to", "to_phone", "to_upi", "amount")
        self.tree_settle_debts = ttk.Treeview(top_frame, columns=columns_debt, show="headings", height=7)
        self.tree_settle_debts.heading("from", text="Debtor (Must Pay)")
        self.tree_settle_debts.heading("from_phone", text="Debtor Phone")
        self.tree_settle_debts.heading("to", text="Creditor (Lender)")
        self.tree_settle_debts.heading("to_phone", text="Creditor Phone")
        self.tree_settle_debts.heading("to_upi", text="Lender UPI / Handle")
        self.tree_settle_debts.heading("amount", text="Amount Owed")

        self.tree_settle_debts.column("from", width=145)
        self.tree_settle_debts.column("from_phone", width=115)
        self.tree_settle_debts.column("to", width=145)
        self.tree_settle_debts.column("to_phone", width=115)
        self.tree_settle_debts.column("to_upi", width=145)
        self.tree_settle_debts.column("amount", width=115, anchor=tk.E)

        self.tree_settle_debts.tag_configure("pending_debt", foreground="#FCD34D")

        self.tree_settle_debts.pack(fill=tk.BOTH, expand=True)

        debt_btn_bar = tk.Frame(top_frame, bg=self.BG_SURFACE)
        debt_btn_bar.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(debt_btn_bar, text="💬 Send WhatsApp Reminder", style="Primary.TButton", command=self.handle_send_whatsapp_reminder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(debt_btn_bar, text="📱 Send SMS / Text Reminder", style="Indigo.TButton", command=self.handle_send_sms_reminder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(debt_btn_bar, text="✓ Record Settlement / Payment", style="Amber.TButton", command=self.handle_record_settlement_dialog).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(debt_btn_bar, text="📋 Preview Reminder Message", style="Secondary.TButton", command=self.handle_preview_reminder_message).pack(side=tk.LEFT)

        bottom_frame = ttk.LabelFrame(self.tab_settlements, text=" Recorded Settlements History ", padding=12)
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        columns_settled = ("id", "date", "from", "to", "amount", "mode", "notes")
        self.tree_settle_history = ttk.Treeview(bottom_frame, columns=columns_settled, show="headings", height=6)
        self.tree_settle_history.heading("id", text="ID")
        self.tree_settle_history.heading("date", text="Date")
        self.tree_settle_history.heading("from", text="Paid By")
        self.tree_settle_history.heading("to", text="Paid To")
        self.tree_settle_history.heading("amount", text="Amount")
        self.tree_settle_history.heading("mode", text="Payment Mode")
        self.tree_settle_history.heading("notes", text="Notes")

        self.tree_settle_history.column("id", width=45)
        self.tree_settle_history.column("date", width=95)
        self.tree_settle_history.column("from", width=145)
        self.tree_settle_history.column("to", width=145)
        self.tree_settle_history.column("amount", width=105, anchor=tk.E)
        self.tree_settle_history.column("mode", width=115)
        self.tree_settle_history.column("notes", width=165)

        self.tree_settle_history.tag_configure("settled_ok", foreground=self.COLOR_EMERALD)

        self.tree_settle_history.pack(fill=tk.BOTH, expand=True)

    def refresh_settlements_tab(self):
        for item in self.tree_settle_debts.get_children():
            self.tree_settle_debts.delete(item)

        debts = self.engine.simplify_debts(self.current_group_id)
        for d in debts:
            self.tree_settle_debts.insert(
                "",
                tk.END,
                values=(
                    d["from_name"],
                    d["from_phone"],
                    d["to_name"],
                    d["to_phone"],
                    d["to_upi"],
                    f"{self.currency}{d['amount']:.2f}",
                ),
                tags=("pending_debt",),
            )

        for item in self.tree_settle_history.get_children():
            self.tree_settle_history.delete(item)

        settlements = self.engine.get_settlements(self.current_group_id)
        for s in settlements:
            self.tree_settle_history.insert(
                "",
                tk.END,
                values=(
                    s["id"],
                    s["date"],
                    s["from_name"],
                    s["to_name"],
                    f"{self.currency}{s['amount']:.2f}",
                    s["payment_mode"],
                    s["notes"],
                ),
                tags=("settled_ok",),
            )

    def _get_selected_debt(self):
        selected = self.tree_settle_debts.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a debt from the table first.")
            return None

        vals = self.tree_settle_debts.item(selected[0])["values"]
        from_name = vals[0]
        to_name = vals[2]
        amt_str = str(vals[5]).replace(self.currency, "").strip()
        amt = float(amt_str)

        debts = self.engine.simplify_debts(self.current_group_id)
        for d in debts:
            if d["from_name"] == from_name and d["to_name"] == to_name and abs(d["amount"] - amt) < 0.05:
                return d
        return None

    def handle_send_whatsapp_reminder(self):
        debt = self._get_selected_debt()
        if not debt:
            return

        if not debt.get("from_phone"):
            messagebox.showerror("Missing Phone", f"No phone number saved for {debt['from_name']}.\nPlease edit the member to add their phone number.")
            return

        msg = self.notifier.generate_settlement_message(
            debt["from_name"], debt["to_name"], debt["amount"], self.currency, debt.get("to_upi", ""), debt.get("to_notes", "")
        )
        self._send_whatsapp_with_feedback(debt["from_phone"], msg)

    def handle_send_sms_reminder(self):
        debt = self._get_selected_debt()
        if not debt:
            return

        if not debt.get("from_phone"):
            messagebox.showerror("Missing Phone", f"No phone number saved for {debt['from_name']}.\nPlease edit the member to add their phone number.")
            return

        msg = self.notifier.generate_settlement_message(
            debt["from_name"], debt["to_name"], debt["amount"], self.currency, debt.get("to_upi", ""), debt.get("to_notes", "")
        )
        self._send_sms_with_feedback(debt["from_phone"], msg)

    def _send_whatsapp_with_feedback(self, phone, message):
        if not phone:
            messagebox.showwarning("Missing Phone", "This member does not have a phone number saved.")
            return

        sid = self.engine.get_setting("twilio_sid").strip()
        if sid:
            ask_auto = messagebox.askyesno(
                "Twilio API Configured",
                "Twilio API credentials detected.\n\n"
                "• Click 'Yes' to send automatically in background via Twilio WhatsApp API.\n"
                "• Click 'No' to open in WhatsApp Web / Desktop app.",
            )
            if ask_auto:
                success, resp = self.notifier.send_via_twilio(phone, message, is_whatsapp=True)
                if success:
                    messagebox.showinfo("WhatsApp Sent", resp)
                    self.set_status("WhatsApp message sent via Twilio.")
                else:
                    messagebox.showerror("Twilio Dispatch Failed", resp)
                return

        self.notifier.open_whatsapp(phone, message)
        self.set_status(f"Opening WhatsApp chat for {phone}...")

    def _send_sms_with_feedback(self, phone, message):
        if not phone:
            messagebox.showwarning("Missing Phone", "This member does not have a phone number saved.")
            return

        sid = self.engine.get_setting("twilio_sid").strip()
        if sid:
            ask_auto = messagebox.askyesno(
                "Twilio API Configured",
                "Twilio API credentials detected.\n\n"
                "• Click 'Yes' to send automated SMS via Twilio API.\n"
                "• Click 'No' to open in your default Messages / SMS app.",
            )
            if ask_auto:
                success, resp = self.notifier.send_via_twilio(phone, message, is_whatsapp=False)
                if success:
                    messagebox.showinfo("SMS Sent", resp)
                    self.set_status("SMS sent via Twilio.")
                else:
                    messagebox.showerror("Twilio Dispatch Failed", resp)
                return

        self.notifier.open_sms(phone, message)
        self.set_status(f"Opening SMS composer for {phone}...")

    def handle_preview_reminder_message(self):
        debt = self._get_selected_debt()
        if not debt:
            return

        msg = self.notifier.generate_settlement_message(
            debt["from_name"], debt["to_name"], debt["amount"], self.currency, debt.get("to_upi", ""), debt.get("to_notes", "")
        )

        modal = tk.Toplevel(self.root)
        modal.title(f"Reminder Message Preview • {debt['from_name']}")
        modal.geometry("540x420")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)

        tk.Label(modal, text=f"Message Preview for {debt['from_name']}:", font=("Helvetica", 11, "bold"), fg=self.COLOR_SKY, bg=self.BG_MAIN).pack(anchor=tk.W, padx=16, pady=(14, 6))

        txt_box = scrolledtext.ScrolledText(modal, wrap=tk.WORD, height=12, bg=self.BG_INPUT, fg=self.TEXT_MAIN, insertbackground=self.TEXT_MAIN)
        txt_box.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        txt_box.insert(tk.END, msg)

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(msg)
            messagebox.showinfo("Copied", "Message copied to clipboard!")

        btn_row = tk.Frame(modal, bg=self.BG_MAIN)
        btn_row.pack(fill=tk.X, padx=16, pady=12)

        ttk.Button(btn_row, text="📋 Copy Message", style="Secondary.TButton", command=copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="💬 Send via WhatsApp", style="Primary.TButton", command=lambda: [modal.destroy(), self._send_whatsapp_with_feedback(debt.get('from_phone', ''), msg)]).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_row, text="Close", style="Secondary.TButton", command=modal.destroy).pack(side=tk.RIGHT)

    def handle_record_settlement_dialog(self):
        debt = self._get_selected_debt()
        self._open_settlement_modal(debt)

    def handle_send_reminder_from_plan(self):
        selected = self.tree_plan.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a settlement row from the plan table.")
            return

        vals = self.tree_plan.item(selected[0])["values"]
        from_name = vals[0]
        to_name = vals[2]
        debts = self.engine.simplify_debts(self.current_group_id)
        for d in debts:
            if d["from_name"] == from_name and d["to_name"] == to_name:
                msg = self.notifier.generate_settlement_message(
                    d["from_name"], d["to_name"], d["amount"], self.currency, d.get("to_upi", ""), d.get("to_notes", "")
                )
                self._send_whatsapp_with_feedback(d.get("from_phone", ""), msg)
                return

    def handle_record_settlement_from_plan(self):
        selected = self.tree_plan.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a settlement row from the plan table.")
            return

        vals = self.tree_plan.item(selected[0])["values"]
        from_name = vals[0]
        to_name = vals[2]
        debts = self.engine.simplify_debts(self.current_group_id)
        for d in debts:
            if d["from_name"] == from_name and d["to_name"] == to_name:
                self._open_settlement_modal(d)
                return

    def _open_settlement_modal(self, debt=None):
        modal = tk.Toplevel(self.root)
        modal.title("Record Payment / Settlement • SplitExpense")
        modal.geometry("480x400")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)
        modal.grab_set()

        members = self.engine.get_members()
        member_names = [m["name"] for m in members]

        tk.Label(modal, text="✓ Record Payment Settlement", font=("Helvetica", 13, "bold"), fg=self.COLOR_SKY, bg=self.BG_MAIN).pack(anchor=tk.W, padx=18, pady=(14, 10))

        form = tk.Frame(modal, bg=self.BG_SURFACE, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=16, pady=14)
        form.pack(fill=tk.BOTH, expand=True, padx=18)

        tk.Label(form, text="Paid By (Debtor):", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=0, column=0, sticky=tk.W, pady=6)
        from_var = tk.StringVar(value=debt["from_name"] if debt else (member_names[0] if member_names else ""))
        from_combo = ttk.Combobox(form, textvariable=from_var, values=member_names, state="readonly", width=22)
        from_combo.grid(row=0, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Paid To (Creditor):", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=1, column=0, sticky=tk.W, pady=6)
        to_var = tk.StringVar(value=debt["to_name"] if debt else (member_names[1] if len(member_names) > 1 else ""))
        to_combo = ttk.Combobox(form, textvariable=to_var, values=member_names, state="readonly", width=22)
        to_combo.grid(row=1, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Amount:", fg=self.COLOR_EMERALD, bg=self.BG_SURFACE, font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        amt_var = tk.StringVar(value=f"{debt['amount']:.2f}" if debt else "")
        ttk.Entry(form, textvariable=amt_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Payment Mode:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=3, column=0, sticky=tk.W, pady=6)
        mode_var = tk.StringVar(value="UPI / GPay")
        ttk.Combobox(form, textvariable=mode_var, values=["UPI / GPay", "PhonePe", "Paytm", "Cash", "Net Banking", "Other"], state="readonly", width=15).grid(row=3, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Date (YYYY-MM-DD):", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=4, column=0, sticky=tk.W, pady=6)
        date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(form, textvariable=date_var, width=15).grid(row=4, column=1, sticky=tk.W, pady=6)

        def save_settlement():
            f_name = from_var.get()
            t_name = to_var.get()
            if f_name == t_name:
                messagebox.showerror("Error", "Payer and receiver cannot be the same member.")
                return

            try:
                amt = float(amt_var.get())
                if amt <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid positive payment amount.")
                return

            m_map = {m["name"]: m["id"] for m in members}
            from_id = m_map.get(f_name)
            to_id = m_map.get(t_name)

            self.engine.record_settlement(self.current_group_id, from_id, to_id, amt, mode_var.get(), date_var.get())
            self.set_status(f"Settlement of {self.currency}{amt:.2f} from {f_name} to {t_name} recorded.")
            self.refresh_all()
            modal.destroy()
            messagebox.showinfo("Success", f"Recorded settlement of {self.currency}{amt:.2f} successfully!")

        btn_box = tk.Frame(modal, bg=self.BG_MAIN, padx=18, pady=14)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Save Settlement", style="Primary.TButton", command=save_settlement).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side=tk.LEFT)

    # ========================================================================
    # TAB 5: GROUPS & MEMBERS MANAGEMENT
    # ========================================================================
    def _build_members_tab(self):
        container = ttk.Frame(self.tab_members, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        left_col = ttk.LabelFrame(container, text=" Members Directory ", padding=12)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        mem_btn_bar = tk.Frame(left_col, bg=self.BG_SURFACE)
        mem_btn_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(mem_btn_bar, text="➕ Add Member", style="Primary.TButton", command=self.handle_add_member_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(mem_btn_bar, text="✏ Edit Member", style="Indigo.TButton", command=self.handle_edit_member_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(mem_btn_bar, text="🗑 Delete", style="Danger.TButton", command=self.handle_delete_member).pack(side=tk.LEFT)

        columns_m = ("id", "name", "phone", "email", "upi")
        self.tree_members = ttk.Treeview(left_col, columns=columns_m, show="headings", height=14)
        self.tree_members.heading("id", text="ID")
        self.tree_members.heading("name", text="Name")
        self.tree_members.heading("phone", text="Phone (for WhatsApp/SMS)")
        self.tree_members.heading("email", text="Email")
        self.tree_members.heading("upi", text="UPI ID / Handle")

        self.tree_members.column("id", width=40)
        self.tree_members.column("name", width=125)
        self.tree_members.column("phone", width=135)
        self.tree_members.column("email", width=125)
        self.tree_members.column("upi", width=115)

        self.tree_members.tag_configure("evenrow", background=self.BG_SURFACE)
        self.tree_members.tag_configure("oddrow", background=self.BG_SURFACE_ALT)

        self.tree_members.pack(fill=tk.BOTH, expand=True)

        right_col = ttk.LabelFrame(container, text=" Groups Management ", padding=12)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        grp_btn_bar = tk.Frame(right_col, bg=self.BG_SURFACE)
        grp_btn_bar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(grp_btn_bar, text="➕ Add Group", style="Purple.TButton", command=self.handle_add_group_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(grp_btn_bar, text="👥 Manage Group Members", style="Cyan.TButton", command=self.handle_manage_group_members_dialog).pack(side=tk.LEFT)

        columns_g = ("id", "name", "desc")
        self.tree_groups = ttk.Treeview(right_col, columns=columns_g, show="headings", height=14)
        self.tree_groups.heading("id", text="ID")
        self.tree_groups.heading("name", text="Group Name")
        self.tree_groups.heading("desc", text="Description")

        self.tree_groups.column("id", width=40)
        self.tree_groups.column("name", width=135)
        self.tree_groups.column("desc", width=185)

        self.tree_groups.tag_configure("evenrow", background=self.BG_SURFACE)
        self.tree_groups.tag_configure("oddrow", background=self.BG_SURFACE_ALT)

        self.tree_groups.pack(fill=tk.BOTH, expand=True)

    def refresh_members_tab(self):
        for item in self.tree_members.get_children():
            self.tree_members.delete(item)
        for idx, m in enumerate(self.engine.get_members()):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_members.insert("", tk.END, values=(m["id"], m["name"], m["phone"], m["email"], m["upi_id"]), tags=(tag,))

        for item in self.tree_groups.get_children():
            self.tree_groups.delete(item)
        for idx, g in enumerate(self.engine.get_groups()):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_groups.insert("", tk.END, values=(g["id"], g["name"], g["description"]), tags=(tag,))

    def handle_add_member_dialog(self):
        self._open_member_modal(None)

    def handle_edit_member_dialog(self):
        selected = self.tree_members.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a member to edit.")
            return
        mid = self.tree_members.item(selected[0])["values"][0]
        member = self.engine.get_member(mid)
        self._open_member_modal(member)

    def _open_member_modal(self, member=None):
        modal = tk.Toplevel(self.root)
        modal.title("Add New Member • SplitExpense" if not member else "Edit Member • SplitExpense")
        modal.geometry("480x420")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)
        modal.grab_set()

        form = tk.Frame(modal, bg=self.BG_SURFACE, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=18, pady=16)
        form.pack(fill=tk.BOTH, expand=True, padx=18, pady=(16, 10))

        tk.Label(form, text="Member Details", font=("Helvetica", 12, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 12))

        tk.Label(form, text="Full Name *:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=1, column=0, sticky=tk.W, pady=6)
        name_var = tk.StringVar(value=member["name"] if member else "")
        ttk.Entry(form, textvariable=name_var, width=28).grid(row=1, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Phone (with country code):", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=2, column=0, sticky=tk.W, pady=6)
        phone_var = tk.StringVar(value=member["phone"] if member else "+91")
        ttk.Entry(form, textvariable=phone_var, width=28).grid(row=2, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Email:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=3, column=0, sticky=tk.W, pady=6)
        email_var = tk.StringVar(value=member["email"] if member else "")
        ttk.Entry(form, textvariable=email_var, width=28).grid(row=3, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="UPI ID (for payments):", fg=self.COLOR_SKY, bg=self.BG_SURFACE, font=("Helvetica", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=6)
        upi_var = tk.StringVar(value=member["upi_id"] if member else "")
        ttk.Entry(form, textvariable=upi_var, width=28).grid(row=4, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Payment Notes / Handle:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=5, column=0, sticky=tk.W, pady=6)
        notes_var = tk.StringVar(value=member["payment_notes"] if member else "")
        ttk.Entry(form, textvariable=notes_var, width=28).grid(row=5, column=1, sticky=tk.W, pady=6)

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Name cannot be empty.")
                return

            phone = phone_var.get().strip()
            email = email_var.get().strip()
            upi = upi_var.get().strip()
            notes = notes_var.get().strip()

            if member:
                self.engine.update_member(member["id"], name, phone, email, upi, notes)
                self.set_status(f"Updated member '{name}'.")
            else:
                self.engine.add_member(name, phone, email, upi, notes)
                self.set_status(f"Added new member '{name}'.")

            self.refresh_all()
            modal.destroy()

        btn_box = tk.Frame(modal, bg=self.BG_MAIN, padx=18, pady=10)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Save Member", style="Primary.TButton", command=save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side=tk.LEFT)

    def handle_delete_member(self):
        selected = self.tree_members.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a member to delete.")
            return

        mid = self.tree_members.item(selected[0])["values"][0]
        name = self.tree_members.item(selected[0])["values"][1]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?\nThis will remove them from all groups and splits."):
            self.engine.delete_member(mid)
            self.set_status(f"Deleted member '{name}'.")
            self.refresh_all()

    def handle_add_group_dialog(self):
        modal = tk.Toplevel(self.root)
        modal.title("Add New Group • SplitExpense")
        modal.geometry("440x290")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)
        modal.grab_set()

        form = tk.Frame(modal, bg=self.BG_SURFACE, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=18, pady=16)
        form.pack(fill=tk.BOTH, expand=True, padx=18, pady=(16, 10))

        tk.Label(form, text="Create New Group", font=("Helvetica", 12, "bold"), fg=self.COLOR_SKY, bg=self.BG_SURFACE).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 12))

        tk.Label(form, text="Group Name *:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=1, column=0, sticky=tk.W, pady=6)
        name_var = tk.StringVar()
        ttk.Entry(form, textvariable=name_var, width=24).grid(row=1, column=1, sticky=tk.W, pady=6)

        tk.Label(form, text="Description:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=2, column=0, sticky=tk.W, pady=6)
        desc_var = tk.StringVar()
        ttk.Entry(form, textvariable=desc_var, width=24).grid(row=2, column=1, sticky=tk.W, pady=6)

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Group name cannot be empty.")
                return

            self.engine.add_group(name, desc_var.get().strip())
            self.set_status(f"Group '{name}' created.")
            self.refresh_all()
            modal.destroy()

        btn_box = tk.Frame(modal, bg=self.BG_MAIN, padx=18, pady=10)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Create Group", style="Primary.TButton", command=save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side=tk.LEFT)

    def handle_manage_group_members_dialog(self):
        selected = self.tree_groups.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a group first.")
            return

        gid = self.tree_groups.item(selected[0])["values"][0]
        gname = self.tree_groups.item(selected[0])["values"][1]

        modal = tk.Toplevel(self.root)
        modal.title(f"Manage Members • {gname}")
        modal.geometry("440x460")
        modal.configure(bg=self.BG_MAIN)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text=f"Members in '{gname}'", font=("Helvetica", 12, "bold"), fg=self.COLOR_SKY, bg=self.BG_MAIN).pack(anchor=tk.W, padx=18, pady=(14, 8))

        all_members = self.engine.get_members()
        current_members = {m["id"] for m in self.engine.get_group_members(gid)}

        frame = tk.Frame(modal, bg=self.BG_SURFACE, highlightbackground=self.BORDER_COLOR, highlightthickness=1, padx=16, pady=12)
        frame.pack(fill=tk.BOTH, expand=True, padx=18)

        check_vars = {}
        for m in all_members:
            var = tk.BooleanVar(value=m["id"] in current_members)
            check_vars[m["id"]] = var
            cb = ttk.Checkbutton(frame, text=f"{m['name']} ({m.get('phone', '')})", variable=var)
            cb.pack(anchor=tk.W, pady=4)

        def save():
            selected_ids = [mid for mid, v in check_vars.items() if v.get()]
            self.engine.set_group_members(gid, selected_ids)
            self.set_status(f"Updated members for group '{gname}'.")
            self.refresh_all()
            modal.destroy()

        btn_box = tk.Frame(modal, bg=self.BG_MAIN, padx=18, pady=12)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Save Group Members", style="Primary.TButton", command=save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_box, text="Cancel", style="Secondary.TButton", command=modal.destroy).pack(side=tk.LEFT)

    # ========================================================================
    # TAB 6: SETTINGS
    # ========================================================================
    def _build_settings_tab(self):
        container = ttk.Frame(self.tab_settings, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        pref_card = ttk.LabelFrame(container, text=" General Preferences ", padding=14)
        pref_card.pack(fill=tk.X, pady=(0, 14))

        tk.Label(pref_card, text="Currency Symbol:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.setting_curr_var = tk.StringVar(value=self.currency)
        curr_combo = ttk.Combobox(pref_card, textvariable=self.setting_curr_var, values=["₹", "$", "€", "£", "¥", "AED"], state="readonly", width=12)
        curr_combo.grid(row=0, column=1, sticky=tk.W, pady=6)

        twilio_card = ttk.LabelFrame(container, text=" Twilio API Settings (Optional - For Automated Background SMS / WhatsApp) ", padding=14)
        twilio_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(twilio_card, text="Account SID:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.twilio_sid_var = tk.StringVar(value=self.engine.get_setting("twilio_sid"))
        ttk.Entry(twilio_card, textvariable=self.twilio_sid_var, width=40).grid(row=0, column=1, sticky=tk.W, pady=6)

        tk.Label(twilio_card, text="Auth Token:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.twilio_token_var = tk.StringVar(value=self.engine.get_setting("twilio_token"))
        ttk.Entry(twilio_card, textvariable=self.twilio_token_var, show="•", width=40).grid(row=1, column=1, sticky=tk.W, pady=6)

        tk.Label(twilio_card, text="From Phone / WhatsApp:", fg=self.TEXT_MAIN, bg=self.BG_SURFACE).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.twilio_phone_var = tk.StringVar(value=self.engine.get_setting("twilio_phone"))
        ttk.Entry(twilio_card, textvariable=self.twilio_phone_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=6)

        note_twilio = (
            "Note: If Twilio is not configured, SplitExpense will automatically open your native WhatsApp "
            "(via Web/Desktop) or default SMS app with pre-filled recipient and message details without needing any API keys."
        )
        tk.Label(twilio_card, text=note_twilio, font=("Helvetica", 9), fg=self.TEXT_MUTED, bg=self.BG_SURFACE, wraplength=720, justify=tk.LEFT).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(8, 0)
        )

        ttk.Button(container, text="💾 Save Settings", style="Primary.TButton", command=self.handle_save_settings).pack(anchor=tk.W)

    def handle_save_settings(self):
        new_curr = self.setting_curr_var.get().strip()
        self.currency = new_curr
        self.engine.set_setting("currency", new_curr)
        self.engine.set_setting("twilio_sid", self.twilio_sid_var.get().strip())
        self.engine.set_setting("twilio_token", self.twilio_token_var.get().strip())
        self.engine.set_setting("twilio_phone", self.twilio_phone_var.get().strip())

        self.set_status("Settings saved successfully!")
        self.refresh_all()
        messagebox.showinfo("Saved", "Settings updated successfully!")

    # ========================================================================
    # DATA REFRESH & STATE MANAGEMENT
    # ========================================================================
    def _on_top_group_changed(self, event=None):
        selection = self.top_group_var.get()
        if selection == "All Groups":
            self.current_group_id = None
        else:
            for g in self.engine.get_groups():
                if g["name"] == selection:
                    self.current_group_id = g["id"]
                    break
        self.refresh_all()

    def refresh_all(self):
        groups = self.engine.get_groups()
        group_names = ["All Groups"] + [g["name"] for g in groups]
        self.top_group_combo["values"] = group_names
        if not self.top_group_var.get():
            self.top_group_var.set("All Groups")

        raw_grp_names = [g["name"] for g in groups]
        self.exp_group_combo["values"] = raw_grp_names
        if raw_grp_names and not self.exp_group_var.get():
            self.exp_group_var.set(raw_grp_names[0])

        members = self.engine.get_members()
        m_names = [m["name"] for m in members]
        self.exp_payer_combo["values"] = m_names
        if m_names and not self.exp_payer_var.get():
            self.exp_payer_var.set(m_names[0])

        self._update_borrower_combo_values()
        self._refresh_dashboard()
        self.refresh_expenses_table()
        self.refresh_settlements_tab()
        self.refresh_members_tab()

        if hasattr(self, "split_table_frame"):
            self._populate_expense_participants()

    def _refresh_dashboard(self):
        expenses = self.engine.get_expenses(self.current_group_id)
        total_spent = sum(e["amount"] for e in expenses)
        self.kpi_total_spent.val_lbl.config(text=f"{self.currency}{total_spent:,.2f}")
        self.kpi_total_expenses.val_lbl.config(text=str(len(expenses)))

        all_members = self.engine.get_group_members(self.current_group_id) if self.current_group_id else self.engine.get_members()
        self.kpi_members_count.val_lbl.config(text=str(len(all_members)))

        for item in self.tree_balances.get_children():
            self.tree_balances.delete(item)

        balances = self.engine.calculate_balances(self.current_group_id)
        for b in balances:
            net = b["net_balance"]
            sign = "+" if net > 0 else ""
            if net > 0.01:
                status_text = f"Gets back {self.currency}{net:,.2f}"
                tag = "positive"
            elif net < -0.01:
                status_text = f"Owes {self.currency}{-net:,.2f}"
                tag = "negative"
            else:
                status_text = "Settled Up"
                tag = "settled"

            settled_net = b["settled_paid"] - b["settled_recv"]
            settled_str = f"{self.currency}{settled_net:,.2f}" if abs(settled_net) > 0.01 else "—"

            self.tree_balances.insert(
                "",
                tk.END,
                values=(
                    b["name"],
                    f"+{self.currency}{b['total_paid']:,.2f}",
                    f"-{self.currency}{b['total_owed']:,.2f}",
                    settled_str,
                    f"{sign}{self.currency}{net:,.2f}",
                    status_text,
                ),
                tags=(tag,),
            )

        for item in self.tree_plan.get_children():
            self.tree_plan.delete(item)

        plan = self.engine.simplify_debts(self.current_group_id)
        self.kpi_debts_count.val_lbl.config(text=str(len(plan)))

        for p in plan:
            self.tree_plan.insert(
                "",
                tk.END,
                values=(
                    p["from_name"],
                    "➔",
                    p["to_name"],
                    f"{self.currency}{p['amount']:,.2f}",
                    "Pending",
                ),
                tags=("debt_row",),
            )

    def set_status(self, text):
        now = datetime.now().strftime("%H:%M:%S")
        self.status_bar.config(text=f"[{now}] {text}")


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

def main():
    root = tk.Tk()
    app = SplitExpenseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
