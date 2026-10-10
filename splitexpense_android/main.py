"""
SplitExpense Mobile - Android Application
=========================================
Built with Kivy for Android deployment via Buildozer.
Features:
- Standard Android Aspect Ratio & Adaptive DPI Scaling (dp/sp)
- Safe Area Padding for Android Status Bar & Gesture Navigation
- Dark Mode Mobile Ambience (#0F172A)
- Groups & Members Management
- Smart Allocation Modes (Full to One, Paid for Others, Shared Equally)
- True Added (+) and Subtracted (-) Net Balances
- Debt Simplification Algorithm (Min Cash Flow)
- 1-Tap WhatsApp, SMS, and UPI Payment Intent Triggers
- Local SQLite Database persistence
"""

import os
import re
import sqlite3
import urllib.parse
import webbrowser
from datetime import datetime

import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

kivy.require("2.0.0")

# Mobile Dark Palette
BG_DARK = (0.059, 0.090, 0.165, 1)      # #0F172A
CARD_DARK = (0.118, 0.161, 0.231, 1)    # #1E293B
INPUT_DARK = (0.043, 0.075, 0.169, 1)   # #0B132B
ACCENT_CYAN = (0.220, 0.741, 0.973, 1)  # #38BDF8
ACCENT_GREEN = (0.063, 0.725, 0.506, 1) # #10B981
ACCENT_ROSE = (0.957, 0.247, 0.369, 1)  # #F43F5E
ACCENT_AMBER = (0.961, 0.620, 0.043, 1) # #F59E0B
TEXT_WHITE = (0.973, 0.980, 0.988, 1)   # #F8FAFC
TEXT_MUTED = (0.580, 0.639, 0.722, 1)   # #94A3B8
BORDER_COLOR = (0.200, 0.255, 0.333, 1) # #334155

# ============================================================================
# DATABASE ENGINE
# ============================================================================

class MobileDatabase:
    def __init__(self, db_path="splitexpense.db"):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                upi_id TEXT DEFAULT '',
                payment_notes TEXT DEFAULT ''
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT ''
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                member_id INTEGER,
                PRIMARY KEY (group_id, member_id),
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                payer_id INTEGER NOT NULL,
                split_type TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                date TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                amount_owed REAL NOT NULL,
                FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
            )
            """)
            c.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                from_member_id INTEGER NOT NULL,
                to_member_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_mode TEXT DEFAULT 'UPI',
                date TEXT NOT NULL
            )
            """)
            c.execute("SELECT COUNT(*) as cnt FROM members")
            if c.fetchone()["cnt"] == 0:
                self._seed(c)
            conn.commit()

    def _seed(self, c):
        c.execute("INSERT INTO members (name, phone, upi_id) VALUES ('Alice Sharma', '+919876543210', 'alice@okaxis')")
        m1 = c.lastrowid
        c.execute("INSERT INTO members (name, phone, upi_id) VALUES ('Bob Verma', '+919876543211', 'bob@oksbi')")
        m2 = c.lastrowid
        c.execute("INSERT INTO members (name, phone, upi_id) VALUES ('Charlie Patel', '+919876543212', 'charlie@icici')")
        m3 = c.lastrowid
        c.execute("INSERT INTO groups (name, description) VALUES ('Trip', 'Weekend getaway')")
        g1 = c.lastrowid
        for m in [m1, m2, m3]:
            c.execute("INSERT INTO group_members (group_id, member_id) VALUES (?, ?)", (g1, m))

    def get_members(self):
        with self.get_connection() as conn:
            return [dict(r) for r in conn.cursor().execute("SELECT * FROM members ORDER BY name ASC").fetchall()]

    def add_member(self, name, phone="", upi_id=""):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO members (name, phone, upi_id) VALUES (?, ?, ?)", (name, phone, upi_id))
            conn.commit()
            return c.lastrowid

    def get_groups(self):
        with self.get_connection() as conn:
            return [dict(r) for r in conn.cursor().execute("SELECT * FROM groups ORDER BY name ASC").fetchall()]

    def add_group(self, name):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO groups (name) VALUES (?)", (name,))
            conn.commit()
            return c.lastrowid

    def add_expense(self, group_id, desc, amount, payer_id, split_type, splits, date=None):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO expenses (group_id, description, amount, payer_id, split_type, date) VALUES (?, ?, ?, ?, ?, ?)",
                      (group_id, desc, amount, payer_id, split_type, date))
            exp_id = c.lastrowid
            for mid, owed in splits:
                c.execute("INSERT INTO expense_splits (expense_id, member_id, amount_owed) VALUES (?, ?, ?)", (exp_id, mid, owed))
            conn.commit()
            return exp_id

    def get_expenses(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            rows = c.execute("""
                SELECT e.*, m.name as payer_name FROM expenses e
                LEFT JOIN members m ON e.payer_id = m.id
                ORDER BY e.date DESC, e.id DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def delete_expense(self, exp_id):
        with self.get_connection() as conn:
            conn.cursor().execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
            conn.commit()

    def record_settlement(self, from_id, to_id, amount):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO settlements (from_member_id, to_member_id, amount, date) VALUES (?, ?, ?, ?)",
                      (from_id, to_id, amount, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

    def calculate_balances(self):
        members = self.get_members()
        paid_map = {m["id"]: 0.0 for m in members}
        owed_map = {m["id"]: 0.0 for m in members}
        settled_paid_map = {m["id"]: 0.0 for m in members}
        settled_recv_map = {m["id"]: 0.0 for m in members}

        with self.get_connection() as conn:
            c = conn.cursor()
            for r in c.execute("SELECT payer_id, SUM(amount) as s FROM expenses GROUP BY payer_id"):
                paid_map[r["payer_id"]] = r["s"] or 0.0
            for r in c.execute("SELECT member_id, SUM(amount_owed) as s FROM expense_splits GROUP BY member_id"):
                owed_map[r["member_id"]] = r["s"] or 0.0
            for r in c.execute("SELECT from_member_id, to_member_id, amount FROM settlements"):
                settled_paid_map[r["from_member_id"]] = settled_paid_map.get(r["from_member_id"], 0.0) + r["amount"]
                settled_recv_map[r["to_member_id"]] = settled_recv_map.get(r["to_member_id"], 0.0) + r["amount"]

        res = []
        for m in members:
            mid = m["id"]
            p = paid_map.get(mid, 0.0)
            o = owed_map.get(mid, 0.0)
            sp = settled_paid_map.get(mid, 0.0)
            sr = settled_recv_map.get(mid, 0.0)
            net = (p + sp) - (o + sr)
            res.append({
                "id": mid,
                "name": m["name"],
                "phone": m.get("phone", ""),
                "upi_id": m.get("upi_id", ""),
                "total_paid": round(p, 2),
                "total_owed": round(o, 2),
                "net": round(net, 2)
            })
        res.sort(key=lambda x: x["net"], reverse=True)
        return res

    def simplify_debts(self):
        balances = self.calculate_balances()
        debtors = [[b["id"], b["name"], b.get("phone",""), -b["net"]] for b in balances if b["net"] < -0.01]
        creditors = [[b["id"], b["name"], b.get("phone",""), b.get("upi_id",""), b["net"]] for b in balances if b["net"] > 0.01]

        txs = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            amt = round(min(debtors[i][3], creditors[j][4]), 2)
            if amt > 0.01:
                txs.append({
                    "from_id": debtors[i][0],
                    "from_name": debtors[i][1],
                    "from_phone": debtors[i][2],
                    "to_id": creditors[j][0],
                    "to_name": creditors[j][1],
                    "to_phone": creditors[j][2],
                    "to_upi": creditors[j][3],
                    "amount": amt
                })
            debtors[i][3] -= amt
            creditors[j][4] -= amt
            if debtors[i][3] <= 0.01:
                i += 1
            if creditors[j][4] <= 0.01:
                j += 1
        return txs


# ============================================================================
# UI COMPONENTS (DPI-SCALED FOR ANDROID)
# ============================================================================

class DarkButton(Button):
    def __init__(self, bg_col=ACCENT_GREEN, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = bg_col
        self.color = TEXT_WHITE
        self.bold = True
        self.font_size = sp(14)


class DarkCard(BoxLayout):
    def __init__(self, bg_col=CARD_DARK, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [dp(14), dp(12)]
        self.spacing = dp(6)
        with self.canvas.before:
            Color(*bg_col)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class ResponsiveLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self._update_text_width)

    def _update_text_width(self, *args):
        self.text_size = (self.width, None)


# ============================================================================
# SCREENS WITH STANDARDIZED MOBILE ASPECT RATIOS
# ============================================================================

class DashboardScreen(Screen):
    def __init__(self, db: MobileDatabase, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(8)], spacing=dp(10))

        # Header Card
        hdr = DarkCard(bg_col=CARD_DARK, size_hint_y=None, height=dp(70))
        lbl_title = ResponsiveLabel(text="⚡ SplitExpense", font_size=sp(20), bold=True, color=ACCENT_CYAN, halign="left", valign="middle")
        lbl_sub = ResponsiveLabel(text="Mobile Dark Ambience • True Added & Subtracted Balances", font_size=sp(11), color=TEXT_MUTED, halign="left", valign="middle")
        hdr.add_widget(lbl_title)
        hdr.add_widget(lbl_sub)
        root.add_widget(hdr)

        # Scrollable Viewport
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.content_layout = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter("height"))
        scroll.add_widget(self.content_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.content_layout.clear_widgets()

        balances = self.db.calculate_balances()
        debts = self.db.simplify_debts()
        expenses = self.db.get_expenses()

        total_spent = sum(e["amount"] for e in expenses)

        # KPI Summary Card
        kpi_card = DarkCard(size_hint_y=None, height=dp(96))
        kpi_card.add_widget(ResponsiveLabel(text="Total Group Spending", font_size=sp(12), color=TEXT_MUTED, halign="left"))
        kpi_card.add_widget(ResponsiveLabel(text=f"₹{total_spent:,.2f}", font_size=sp(24), bold=True, color=ACCENT_CYAN, halign="left"))
        kpi_card.add_widget(ResponsiveLabel(text=f"{len(expenses)} expenses logged • {len(debts)} pending settlements", font_size=sp(11), color=TEXT_MUTED, halign="left"))
        self.content_layout.add_widget(kpi_card)

        # Member Net Balances Header
        self.content_layout.add_widget(ResponsiveLabel(
            text="Member Net Balances", font_size=sp(15), bold=True, color=ACCENT_CYAN, size_hint_y=None, height=dp(30), halign="left"
        ))

        for b in balances:
            card = DarkCard(size_hint_y=None, height=dp(80))
            row = BoxLayout(orientation="horizontal", spacing=dp(8))
            info = BoxLayout(orientation="vertical", spacing=dp(2))
            info.add_widget(ResponsiveLabel(text=b["name"], font_size=sp(14), bold=True, color=TEXT_WHITE, halign="left"))
            info.add_widget(ResponsiveLabel(text=f"Paid: +₹{b['total_paid']:.0f}  |  Share: -₹{b['total_owed']:.0f}", font_size=sp(11), color=TEXT_MUTED, halign="left"))
            row.add_widget(info)

            net = b["net"]
            net_col = ACCENT_GREEN if net > 0 else (ACCENT_ROSE if net < 0 else TEXT_MUTED)
            sign = "+" if net > 0 else ""
            status = f"Gets back {sign}₹{net:.2f}" if net > 0 else (f"Owes ₹{-net:.2f}" if net < 0 else "Settled")
            row.add_widget(ResponsiveLabel(text=status, font_size=sp(13), bold=True, color=net_col, size_hint_x=0.48, halign="right", valign="middle"))

            card.add_widget(row)
            self.content_layout.add_widget(card)

        # Simplified Debts
        self.content_layout.add_widget(ResponsiveLabel(
            text="Simplified Settlements (Who Pays Whom)", font_size=sp(15), bold=True, color=ACCENT_AMBER, size_hint_y=None, height=dp(30), halign="left"
        ))

        if not debts:
            no_debt = DarkCard(size_hint_y=None, height=dp(48))
            no_debt.add_widget(ResponsiveLabel(text="✓ All balances are settled up!", color=ACCENT_GREEN, font_size=sp(13), halign="center"))
            self.content_layout.add_widget(no_debt)
        else:
            for d in debts:
                d_card = DarkCard(size_hint_y=None, height=dp(106))
                d_card.add_widget(ResponsiveLabel(
                    text=f"{d['from_name']}  ➔  {d['to_name']} : ₹{d['amount']:.2f}",
                    font_size=sp(14), bold=True, color=TEXT_WHITE, halign="left"
                ))

                btn_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))

                wa_btn = DarkButton(text="💬 WhatsApp", bg_col=ACCENT_GREEN)
                wa_btn.bind(on_release=lambda btn, debt=d: self.send_whatsapp_reminder(debt))
                btn_row.add_widget(wa_btn)

                if d.get("to_upi"):
                    upi_btn = DarkButton(text="💳 Pay UPI", bg_col=ACCENT_CYAN)
                    upi_btn.bind(on_release=lambda btn, debt=d: self.open_upi_pay(debt))
                    btn_row.add_widget(upi_btn)

                settle_btn = DarkButton(text="✓ Settle", bg_col=BORDER_COLOR)
                settle_btn.bind(on_release=lambda btn, debt=d: self.settle_debt(debt))
                btn_row.add_widget(settle_btn)

                d_card.add_widget(btn_row)
                self.content_layout.add_widget(d_card)

    def send_whatsapp_reminder(self, d):
        phone = d.get("from_phone", "")
        clean_phone = re.sub(r"[^\d+]", "", phone)
        if clean_phone.startswith("+"):
            clean_phone = clean_phone[1:]
        elif len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        msg = (
            f"👋 Hi {d['from_name']}!\n\n"
            f"Friendly reminder from SplitExpense.\n"
            f"Your current balance to {d['to_name']} is: ₹{d['amount']:.2f}.\n"
        )
        if d.get("to_upi"):
            msg += f"💳 Pay via UPI: {d['to_upi']}\n"
            msg += f"🔗 UPI Direct: upi://pay?pa={d['to_upi']}&pn={urllib.parse.quote(d['to_name'])}&am={d['amount']:.2f}&cu=INR\n"
        msg += "\nThank you!"

        url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
        webbrowser.open(url)

    def open_upi_pay(self, d):
        to_upi = d.get("to_upi")
        if to_upi:
            url = f"upi://pay?pa={to_upi}&pn={urllib.parse.quote(d['to_name'])}&am={d['amount']:.2f}&cu=INR"
            webbrowser.open(url)

    def settle_debt(self, d):
        self.db.record_settlement(d["from_id"], d["to_id"], d["amount"])
        self.refresh()


class AddExpenseScreen(Screen):
    def __init__(self, db: MobileDatabase, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(8)], spacing=dp(10))

        root.add_widget(ResponsiveLabel(
            text="➕ Add New Expense", font_size=sp(18), bold=True, color=ACCENT_CYAN, size_hint_y=None, height=dp(36), halign="left"
        ))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        scroll_content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter("height"))

        form = DarkCard(size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Description
        form.add_widget(ResponsiveLabel(text="Expense Description:", font_size=sp(12), color=TEXT_MUTED, size_hint_y=None, height=dp(22), halign="left"))
        self.desc_input = TextInput(hint_text="e.g. Dinner, Fuel, Groceries", multiline=False, size_hint_y=None, height=dp(42), font_size=sp(14), background_color=INPUT_DARK, foreground_color=TEXT_WHITE)
        form.add_widget(self.desc_input)

        # Amount
        form.add_widget(ResponsiveLabel(text="Total Amount (₹):", font_size=sp(12), color=TEXT_MUTED, size_hint_y=None, height=dp(22), halign="left"))
        self.amt_input = TextInput(hint_text="0.00", multiline=False, size_hint_y=None, height=dp(42), font_size=sp(14), input_filter="float", background_color=INPUT_DARK, foreground_color=TEXT_WHITE)
        form.add_widget(self.amt_input)

        # Paid By
        form.add_widget(ResponsiveLabel(text="Paid By:", font_size=sp(12), color=TEXT_MUTED, size_hint_y=None, height=dp(22), halign="left"))
        self.payer_spinner = Spinner(text="Select Payer", values=[], size_hint_y=None, height=dp(42), font_size=sp(14), background_color=BORDER_COLOR, color=TEXT_WHITE)
        form.add_widget(self.payer_spinner)

        # Allocation Mode
        form.add_widget(ResponsiveLabel(text="How is this split / allocated?", font_size=sp(12), color=TEXT_MUTED, size_hint_y=None, height=dp(22), halign="left"))
        self.mode_spinner = Spinner(
            text="🍕 Shared (Include Payer)",
            values=["🎯 Full Amount to One Person", "👥 Paid for Others (Exclude Payer)", "🍕 Shared (Include Payer)"],
            size_hint_y=None, height=dp(42), font_size=sp(13), background_color=BORDER_COLOR, color=TEXT_WHITE
        )
        form.add_widget(self.mode_spinner)

        # Target Borrower (for Full to One)
        form.add_widget(ResponsiveLabel(text="If Full Amount, select Borrower:", font_size=sp(12), color=TEXT_MUTED, size_hint_y=None, height=dp(22), halign="left"))
        self.borrower_spinner = Spinner(text="Select Borrower", values=[], size_hint_y=None, height=dp(42), font_size=sp(14), background_color=BORDER_COLOR, color=TEXT_WHITE)
        form.add_widget(self.borrower_spinner)

        scroll_content.add_widget(form)

        # Save Button
        save_btn = DarkButton(text="💾 Save Expense", bg_col=ACCENT_GREEN, size_hint_y=None, height=dp(50))
        save_btn.bind(on_release=self.save_expense)
        scroll_content.add_widget(save_btn)

        scroll.add_widget(scroll_content)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        members = self.db.get_members()
        names = [m["name"] for m in members]
        self.payer_spinner.values = names
        self.borrower_spinner.values = names
        if names:
            self.payer_spinner.text = names[0]
            if len(names) > 1:
                self.borrower_spinner.text = names[1]

    def save_expense(self, *args):
        desc = self.desc_input.text.strip()
        amt_str = self.amt_input.text.strip()
        payer_name = self.payer_spinner.text
        mode_text = self.mode_spinner.text
        borrower_name = self.borrower_spinner.text

        if not desc or not amt_str:
            return

        try:
            amt = float(amt_str)
            if amt <= 0:
                return
        except ValueError:
            return

        members = self.db.get_members()
        m_map = {m["name"]: m["id"] for m in members}
        payer_id = m_map.get(payer_name)

        splits = []
        if "Full Amount" in mode_text:
            borrower_id = m_map.get(borrower_name)
            if not borrower_id or borrower_id == payer_id:
                return
            splits.append((borrower_id, amt))
        elif "Paid for Others" in mode_text:
            others = [m["id"] for m in members if m["id"] != payer_id]
            if others:
                share = round(amt / len(others), 2)
                for oid in others:
                    splits.append((oid, share))
        else:
            share = round(amt / len(members), 2)
            for m in members:
                splits.append((m["id"], share))

        self.db.add_expense(None, desc, amt, payer_id, mode_text, splits)

        self.desc_input.text = ""
        self.amt_input.text = ""
        self.manager.current = "dashboard"


class ExpensesHistoryScreen(Screen):
    def __init__(self, db: MobileDatabase, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(8)], spacing=dp(10))
        root.add_widget(ResponsiveLabel(text="📜 Expenses History", font_size=sp(18), bold=True, color=ACCENT_CYAN, size_hint_y=None, height=dp(36), halign="left"))

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.list_layout = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        scroll.add_widget(self.list_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.list_layout.clear_widgets()
        expenses = self.db.get_expenses()

        if not expenses:
            c = DarkCard(size_hint_y=None, height=dp(50))
            c.add_widget(ResponsiveLabel(text="No expenses logged yet.", color=TEXT_MUTED, halign="center"))
            self.list_layout.add_widget(c)
            return

        for exp in expenses:
            card = DarkCard(size_hint_y=None, height=dp(80))
            row = BoxLayout(orientation="horizontal", spacing=dp(8))

            info = BoxLayout(orientation="vertical", spacing=dp(2))
            info.add_widget(ResponsiveLabel(text=f"{exp['description']} (₹{exp['amount']:.2f})", font_size=sp(14), bold=True, color=TEXT_WHITE, halign="left"))
            info.add_widget(ResponsiveLabel(text=f"Paid by {exp.get('payer_name','')} • {exp['date']}", font_size=sp(11), color=TEXT_MUTED, halign="left"))
            row.add_widget(info)

            del_btn = DarkButton(text="🗑 Delete", bg_col=ACCENT_ROSE, size_hint_x=0.32)
            del_btn.bind(on_release=lambda btn, eid=exp["id"]: self.delete_expense(eid))
            row.add_widget(del_btn)

            card.add_widget(row)
            self.list_layout.add_widget(card)

    def delete_expense(self, eid):
        self.db.delete_expense(eid)
        self.refresh()


class MembersScreen(Screen):
    def __init__(self, db: MobileDatabase, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(8)], spacing=dp(10))
        root.add_widget(ResponsiveLabel(text="👥 Members Directory", font_size=sp(18), bold=True, color=ACCENT_CYAN, size_hint_y=None, height=dp(36), halign="left"))

        # Add Member Form
        add_box = DarkCard(size_hint_y=None, height=dp(175))
        add_box.add_widget(ResponsiveLabel(text="Add New Member:", font_size=sp(12), bold=True, color=ACCENT_CYAN, halign="left"))

        self.name_input = TextInput(hint_text="Full Name", multiline=False, size_hint_y=None, height=dp(38), font_size=sp(13), background_color=INPUT_DARK, foreground_color=TEXT_WHITE)
        self.phone_input = TextInput(hint_text="Phone (e.g. +919876543210)", multiline=False, size_hint_y=None, height=dp(38), font_size=sp(13), background_color=INPUT_DARK, foreground_color=TEXT_WHITE)
        self.upi_input = TextInput(hint_text="UPI ID (e.g. name@okhdfc)", multiline=False, size_hint_y=None, height=dp(38), font_size=sp(13), background_color=INPUT_DARK, foreground_color=TEXT_WHITE)

        add_box.add_widget(self.name_input)
        add_box.add_widget(self.phone_input)
        add_box.add_widget(self.upi_input)

        add_btn = DarkButton(text="➕ Add Member", bg_col=ACCENT_GREEN, size_hint_y=None, height=dp(42))
        add_btn.bind(on_release=self.add_member)
        add_box.add_widget(add_btn)

        root.add_widget(add_box)

        # Members List
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.mem_layout = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.mem_layout.bind(minimum_height=self.mem_layout.setter("height"))
        scroll.add_widget(self.mem_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.mem_layout.clear_widgets()
        for m in self.db.get_members():
            c = DarkCard(size_hint_y=None, height=dp(60))
            c.add_widget(ResponsiveLabel(text=f"{m['name']}  ({m.get('phone') or 'No phone'})", font_size=sp(13), bold=True, color=TEXT_WHITE, halign="left"))
            c.add_widget(ResponsiveLabel(text=f"UPI: {m.get('upi_id') or 'None'}", font_size=sp(11), color=TEXT_MUTED, halign="left"))
            self.mem_layout.add_widget(c)

    def add_member(self, *args):
        name = self.name_input.text.strip()
        phone = self.phone_input.text.strip()
        upi = self.upi_input.text.strip()
        if name:
            self.db.add_member(name, phone, upi)
            self.name_input.text = ""
            self.phone_input.text = ""
            self.upi_input.text = ""
            self.refresh()


# ============================================================================
# MAIN APPLICATION (ADAPTIVE ANDROID LAYOUT)
# ============================================================================

class SplitExpenseMobileApp(App):
    def build(self):
        Window.clearcolor = BG_DARK
        self.title = "SplitExpense"

        db_path = os.path.join(self.user_data_dir, "splitexpense.db")
        self.db = MobileDatabase(db_path)

        # Standard Android layout container with safe-area spacing
        # dp(24) top padding protects the top status bar / notch
        # dp(12) bottom padding protects Android gesture pill / navigation bar
        main_box = BoxLayout(
            orientation="vertical",
            padding=[dp(8), dp(24), dp(8), dp(12)],
            spacing=dp(6)
        )

        # Screen Manager (fills dynamic height)
        self.sm = ScreenManager()
        self.sm.add_widget(DashboardScreen(self.db, name="dashboard"))
        self.sm.add_widget(AddExpenseScreen(self.db, name="add_expense"))
        self.sm.add_widget(ExpensesHistoryScreen(self.db, name="history"))
        self.sm.add_widget(MembersScreen(self.db, name="members"))
        main_box.add_widget(self.sm)

        # Bottom Android Navigation Bar (ergonomic touch target height: dp(56))
        nav = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(4))

        self.btn_dash = DarkButton(text="📊 Balances", bg_col=ACCENT_CYAN)
        self.btn_dash.bind(on_release=lambda b: self.switch_screen("dashboard"))
        nav.add_widget(self.btn_dash)

        self.btn_add = DarkButton(text="➕ Add", bg_col=CARD_DARK)
        self.btn_add.bind(on_release=lambda b: self.switch_screen("add_expense"))
        nav.add_widget(self.btn_add)

        self.btn_hist = DarkButton(text="📜 History", bg_col=CARD_DARK)
        self.btn_hist.bind(on_release=lambda b: self.switch_screen("history"))
        nav.add_widget(self.btn_hist)

        self.btn_mem = DarkButton(text="👥 Members", bg_col=CARD_DARK)
        self.btn_mem.bind(on_release=lambda b: self.switch_screen("members"))
        nav.add_widget(self.btn_mem)

        main_box.add_widget(nav)
        return main_box

    def switch_screen(self, screen_name):
        self.sm.current = screen_name
        # Highlight active tab
        for name, btn in [("dashboard", self.btn_dash), ("add_expense", self.btn_add), ("history", self.btn_hist), ("members", self.btn_mem)]:
            btn.background_color = ACCENT_CYAN if name == screen_name else CARD_DARK


if __name__ == "__main__":
    SplitExpenseMobileApp().run()
