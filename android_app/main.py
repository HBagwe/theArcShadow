"""
Financial Flow & Wealth Stability Planner - Android Mobile Application
=======================================================================
Built with Kivy for Android deployment via Buildozer.
Features:
- Responsive Mobile Layout: Adaptive DPI/SP scaling, safe area padding for
  notches/status bars and gesture navigation across any aspect ratio (16:9, 18:9, 19.5:9, 20:9, 21:9).
- AMOLED Pitch Dark Theme (#000000 / #0A0A0F) with Ultra-Vivid Neon Accents.
- Local SQLite Database (financial_flow.db): Persists all profile incomes, multi-loans,
  credit cards, investments, term insurance, and living expenses across app restarts.
- Multi-Loan Engine: Home Loans, Top-Ups, EMIs, Principal, Rate %, Start Date,
  Amortization Tracking (Paid % vs Leftover Principal).
- Credit Card Engine: Limits, Monthly Bills, Utilization Gauges, Active Card EMIs,
  and Cash Flow Freedom Calendar.
- Savings & Investments: EPF, NPS, ULIP, SIP, FD/RD, Investment Start Date,
  Tenure-based Saving Velocity & Accumulated Corpus.
- Dedicated Term Insurance Section: Monthly Risk Premium, Sum Assured / Life Cover,
  10x-15x Income Multiplier Sufficiency Diagnostics & Family Debt Shield.
- Interactive What-If Simulator: Discretionary Spending Trim Slider with 5-year compounding.
- Action Roadmap (Priorities 1 to 5) & Full Text Report Export.
"""

import math
import os
import re
import sqlite3
from datetime import datetime

import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

kivy.require("2.0.0")

# Mobile Window Configuration (Prevent virtual keyboard covering inputs)
if Window:
    try:
        Window.softinput_mode = "below_target"
    except Exception:
        pass

# AMOLED Pitch Dark Palette (RGBA tuples in 0.0 - 1.0 range)
BG_BLACK = (0.000, 0.000, 0.000, 1)      # #000000 Pitch Black
BG_OBSIDIAN = (0.039, 0.039, 0.059, 1)   # #0A0A0F Deep Obsidian
CARD_DARK = (0.067, 0.067, 0.094, 1)     # #111118 Dark Slate Card
CONTAINER_DARK = (0.086, 0.086, 0.133, 1)# #161622 Inner Box Container
INPUT_DARK = (0.047, 0.047, 0.071, 1)    # #0C0C12 Input Field Dark
BORDER_COLOR = (0.153, 0.153, 0.220, 1)  # #272738 Border Lines

# Neon & Vivid Accents
NEON_CYAN = (0.000, 0.949, 0.996, 1)     # #00F2FE Electric Cyan
NEON_GREEN = (0.000, 0.961, 0.608, 1)    # #00F59B Emerald Neon Green
NEON_ROSE = (1.000, 0.000, 0.333, 1)     # #FF0055 Neon Rose
NEON_AMBER = (0.984, 0.749, 0.141, 1)    # #FBBF24 Amber / Gold
NEON_PURPLE = (0.659, 0.333, 0.969, 1)   # #A855F7 Cyber Violet
PRIMARY_BLUE = (0.220, 0.741, 0.973, 1)  # #38BDF8 Vivid Sky Blue
TEXT_WHITE = (1.000, 1.000, 1.000, 1)    # #FFFFFF Pure Crisp White
TEXT_MUTED = (0.580, 0.639, 0.722, 1)    # #94A3B8 Muted Slate Text


# ============================================================================
# DATE & AMORTIZATION HELPERS
# ============================================================================

def parse_month_year(text: str):
    if not text:
        return None
    s = text.strip()
    patterns = ["%Y-%m", "%m/%Y", "%m-%Y", "%Y/%m", "%b %Y", "%B %Y", "%Y"]
    for p in patterns:
        try:
            return datetime.strptime(s, p)
        except ValueError:
            pass
    m = re.search(r"(\d{4})[-/ ]?(\d{1,2})", s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), 1)
        except ValueError:
            pass
    m2 = re.search(r"(\d{1,2})[-/ ]?(\d{4})", s)
    if m2:
        try:
            return datetime(int(m2.group(2)), int(m2.group(1)), 1)
        except ValueError:
            pass
    return None


def calculate_amortization_leftover(principal: float, annual_rate: float, emi: float, start_date_str: str):
    dt = parse_month_year(start_date_str)
    if not dt or principal <= 0 or emi <= 0:
        return None

    now = datetime.now()
    months_elapsed = max(0, (now.year - dt.year) * 12 + (now.month - dt.month))
    monthly_rate = (annual_rate / 100.0) / 12.0

    if monthly_rate <= 0:
        balance = max(0.0, principal - (emi * months_elapsed))
    else:
        growth = (1 + monthly_rate) ** months_elapsed
        balance = principal * growth - emi * (growth - 1.0) / monthly_rate
        balance = max(0.0, balance)

    completed_pct = max(0.0, min(100.0, ((principal - balance) / principal) * 100.0))

    est_remaining_months = 0
    if balance > 0 and emi > 0:
        if monthly_rate <= 0:
            est_remaining_months = int(math.ceil(balance / emi))
        else:
            if balance * monthly_rate < emi:
                est_remaining_months = int(math.ceil(-math.log(1 - (balance * monthly_rate / emi)) / math.log(1 + monthly_rate)))
            else:
                est_remaining_months = 999

    return {
        "months_elapsed": months_elapsed,
        "balance": balance,
        "completed_pct": completed_pct,
        "remaining_months": est_remaining_months,
        "start_fmt": dt.strftime("%b %Y")
    }


# ============================================================================
# DATABASE ENGINE (SQLite)
# ============================================================================

class FinancialDatabase:
    """Manages offline local persistence of all financial planner records."""

    def __init__(self, db_path="financial_flow.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Profile & Expense Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    currency TEXT DEFAULT '₹',
                    his_income REAL DEFAULT 0,
                    wife_income REAL DEFAULT 0,
                    other_income REAL DEFAULT 0,
                    rent REAL DEFAULT 0,
                    inv_start_date TEXT DEFAULT '',
                    epf REAL DEFAULT 0,
                    nps REAL DEFAULT 0,
                    ulip REAL DEFAULT 0,
                    sip REAL DEFAULT 0,
                    fd REAL DEFAULT 0,
                    inv_other REAL DEFAULT 0,
                    term_premium REAL DEFAULT 0,
                    term_sum_assured REAL DEFAULT 0,
                    term_tenure TEXT DEFAULT '',
                    term_nominee TEXT DEFAULT '',
                    elec REAL DEFAULT 0,
                    water_gas REAL DEFAULT 0,
                    internet REAL DEFAULT 0,
                    mobile REAL DEFAULT 0,
                    groceries REAL DEFAULT 0,
                    healthcare REAL DEFAULT 0,
                    commute REAL DEFAULT 0,
                    education REAL DEFAULT 0,
                    dining REAL DEFAULT 0,
                    leisure REAL DEFAULT 0,
                    updated_at TEXT
                )
            """)

            # 2. Loans Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    description TEXT,
                    principal REAL DEFAULT 0,
                    rate REAL DEFAULT 0,
                    start_date TEXT DEFAULT '',
                    emi REAL DEFAULT 0
                )
            """)

            # 3. Credit Cards Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS credit_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    credit_limit REAL DEFAULT 0,
                    bill REAL DEFAULT 0,
                    spend_type TEXT DEFAULT 'Consistent Regular Spends',
                    emi_amount REAL DEFAULT 0,
                    start_date TEXT DEFAULT '',
                    end_date TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def load_data(self):
        """Loads profile, loans, and credit cards from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profile WHERE id = 1")
            prof_row = cursor.fetchone()

            cursor.execute("SELECT * FROM loans ORDER BY id ASC")
            loan_rows = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM credit_cards ORDER BY id ASC")
            card_rows = [dict(r) for r in cursor.fetchall()]

            profile_data = dict(prof_row) if prof_row else None
            return profile_data, loan_rows, card_rows

    def save_data(self, profile_data: dict, loans: list, cards: list):
        """Saves current state to SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO profile (
                    id, currency, his_income, wife_income, other_income, rent,
                    inv_start_date, epf, nps, ulip, sip, fd, inv_other,
                    term_premium, term_sum_assured, term_tenure, term_nominee,
                    elec, water_gas, internet, mobile,
                    groceries, healthcare, commute, education,
                    dining, leisure, updated_at
                ) VALUES (
                    1, :currency, :his_income, :wife_income, :other_income, :rent,
                    :inv_start_date, :epf, :nps, :ulip, :sip, :fd, :inv_other,
                    :term_premium, :term_sum_assured, :term_tenure, :term_nominee,
                    :elec, :water_gas, :internet, :mobile,
                    :groceries, :healthcare, :commute, :education,
                    :dining, :leisure, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    currency = excluded.currency,
                    his_income = excluded.his_income,
                    wife_income = excluded.wife_income,
                    other_income = excluded.other_income,
                    rent = excluded.rent,
                    inv_start_date = excluded.inv_start_date,
                    epf = excluded.epf,
                    nps = excluded.nps,
                    ulip = excluded.ulip,
                    sip = excluded.sip,
                    fd = excluded.fd,
                    inv_other = excluded.inv_other,
                    term_premium = excluded.term_premium,
                    term_sum_assured = excluded.term_sum_assured,
                    term_tenure = excluded.term_tenure,
                    term_nominee = excluded.term_nominee,
                    elec = excluded.elec,
                    water_gas = excluded.water_gas,
                    internet = excluded.internet,
                    mobile = excluded.mobile,
                    groceries = excluded.groceries,
                    healthcare = excluded.healthcare,
                    commute = excluded.commute,
                    education = excluded.education,
                    dining = excluded.dining,
                    leisure = excluded.leisure,
                    updated_at = excluded.updated_at
            """, {**profile_data, "updated_at": now_str})

            # Replace loans
            cursor.execute("DELETE FROM loans")
            for l in loans:
                cursor.execute("""
                    INSERT INTO loans (category, description, principal, rate, start_date, emi)
                    VALUES (:category, :description, :principal, :rate, :start_date, :emi)
                """, l)

            # Replace cards
            cursor.execute("DELETE FROM credit_cards")
            for c in cards:
                cursor.execute("""
                    INSERT INTO credit_cards (name, credit_limit, bill, spend_type, emi_amount, start_date, end_date)
                    VALUES (:name, :credit_limit, :bill, :spend_type, :emi_amount, :start_date, :end_date)
                """, c)

            conn.commit()

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM profile")
            cursor.execute("DELETE FROM loans")
            cursor.execute("DELETE FROM credit_cards")
            conn.commit()


# ============================================================================
# CUSTOM UI WIDGETS (RESPONSIVE & PITCH DARK)
# ============================================================================

class DarkCard(BoxLayout):
    """High-contrast rounded mobile card."""
    def __init__(self, bg_color=CARD_DARK, border_color=BORDER_COLOR, corner_radius=dp(10), **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.corner_radius = corner_radius
        self.padding = kwargs.get("padding", [dp(12), dp(10), dp(12), dp(10)])
        self.spacing = kwargs.get("spacing", dp(6))
        self.orientation = kwargs.get("orientation", "vertical")
        self.size_hint_x = kwargs.get("size_hint_x", 1.0)
        self.size_hint_y = kwargs.get("size_hint_y", None)

        with self.canvas.before:
            self.col_bg = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.corner_radius])
            self.col_border = Color(*self.border_color)
            self.line = Line(rounded_rectangle=[self.pos[0], self.pos[1], self.size[0], self.size[1], self.corner_radius], width=dp(1))

        self.bind(pos=self._update_shape, size=self._update_shape)

    def _update_shape(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.line.rounded_rectangle = [self.pos[0], self.pos[1], self.size[0], self.size[1], self.corner_radius]


class StyledTextInput(TextInput):
    """High-contrast mobile text input with crisp white text & cyan cursor."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = INPUT_DARK
        self.foreground_color = TEXT_WHITE
        self.cursor_color = NEON_CYAN
        self.cursor_width = dp(2)
        self.padding = [dp(10), dp(8), dp(10), dp(8)]
        self.font_size = sp(13)
        self.multiline = False
        self.write_tab = False
        self.size_hint_y = None
        self.height = dp(38)

        with self.canvas.after:
            self.border_color_inst = Color(*BORDER_COLOR)
            self.border_line = Line(rounded_rectangle=[self.pos[0], self.pos[1], self.size[0], self.size[1], dp(6)], width=dp(1))

        self.bind(pos=self._update_border, size=self._update_border)

    def _update_border(self, *args):
        self.border_line.rounded_rectangle = [self.pos[0], self.pos[1], self.size[0], self.size[1], dp(6)]


class FieldBox(BoxLayout):
    """Clean stacked label + description + input field."""
    def __init__(self, title: str, subtitle: str = "", accent_color=TEXT_WHITE, input_type="text", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.spacing = dp(2)

        lbl_row = BoxLayout(size_hint_y=None, height=dp(18), orientation="horizontal")
        lbl = Label(text=title, font_size=sp(11), bold=True, color=accent_color, halign="left", valign="middle", size_hint_x=1)
        lbl.bind(size=lbl.setter("text_size"))
        lbl_row.add_widget(lbl)
        self.add_widget(lbl_row)

        if subtitle:
            sub = Label(text=subtitle, font_size=sp(8.5), color=TEXT_MUTED, halign="left", valign="middle", size_hint_y=None, height=dp(14))
            sub.bind(size=sub.setter("text_size"))
            self.add_widget(sub)

        self.input = StyledTextInput()
        if input_type == "numeric":
            self.input.input_type = "number"
        self.add_widget(self.input)

        total_h = dp(18) + (dp(14) if subtitle else dp(0)) + dp(38) + dp(4)
        self.height = total_h

    def get_text(self):
        return self.input.text.strip()

    def set_text(self, text):
        self.input.text = str(text) if text is not None else ""


# ============================================================================
# MAIN APPLICATION SCREEN MANAGER
# ============================================================================

class FinancialFlowMobileApp(App):
    def build(self):
        self.title = "Financial Flow & Wealth Planner"
        self.db = FinancialDatabase(self._get_db_path())

        self.currency = "₹"
        self.loan_cards_data = []
        self.credit_cards_data = []
        self.latest_report_text = ""
        self.last_calc = None

        # Root Window Container with Pitch Black AMOLED Background
        root = BoxLayout(orientation="vertical", spacing=0)
        with root.canvas.before:
            Color(*BG_BLACK)
            self.root_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self.root_rect, 'pos', root.pos),
                  size=lambda *_: setattr(self.root_rect, 'size', root.size))

        # Top Header Bar (Safe area for Android notches and status bars)
        header = self._build_header_bar()
        root.add_widget(header)

        # Tab Navigation Bar
        tab_bar = self._build_tab_bar()
        root.add_widget(tab_bar)

        # ScreenManager for Screens
        self.sm = ScreenManager()
        self.screen_incomes = Screen(name="incomes")
        self.screen_cards = Screen(name="cards")
        self.screen_savings = Screen(name="savings")
        self.screen_expenses = Screen(name="expenses")
        self.screen_dashboard = Screen(name="dashboard")
        self.screen_simulator = Screen(name="simulator")

        self._build_screen_incomes()
        self._build_screen_cards()
        self._build_screen_savings()
        self._build_screen_expenses()
        self._build_screen_dashboard()
        self._build_screen_simulator()

        self.sm.add_widget(self.screen_incomes)
        self.sm.add_widget(self.screen_cards)
        self.sm.add_widget(self.screen_savings)
        self.sm.add_widget(self.screen_expenses)
        self.sm.add_widget(self.screen_dashboard)
        self.sm.add_widget(self.screen_simulator)

        root.add_widget(self.sm)

        # Load saved data from database if exists
        self._load_from_database()

        return root

    def _get_db_path(self):
        try:
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            return os.path.join(activity.getFilesDir().getAbsolutePath(), "financial_flow.db")
        except Exception:
            return "financial_flow.db"

    # --- TOP HEADER BAR ---
    def _build_header_bar(self):
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(58), padding=[dp(12), dp(6), dp(12), dp(4)], spacing=dp(2))
        with header.canvas.before:
            Color(*BG_OBSIDIAN)
            self.header_bg = Rectangle(pos=header.pos, size=header.size)
            Color(*BORDER_COLOR)
            self.header_line = Line(points=[header.pos[0], header.pos[1], header.pos[0] + header.size[0], header.pos[1]], width=dp(1))

        header.bind(pos=lambda *_: setattr(self.header_bg, 'pos', header.pos) or setattr(self.header_line, 'points', [header.pos[0], header.pos[1], header.pos[0] + header.size[0], header.pos[1]]),
                    size=lambda *_: setattr(self.header_bg, 'size', header.size) or setattr(self.header_line, 'points', [header.pos[0], header.pos[1], header.pos[0] + header.size[0], header.pos[1]]))

        top_r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(6))

        title = Label(text="⚡ FINANCIAL FLOW & WEALTH", font_size=sp(13), bold=True, color=NEON_CYAN, halign="left", valign="middle")
        title.bind(size=title.setter("text_size"))
        top_r.add_widget(title)

        # Currency Spinner
        self.cur_spinner = Spinner(
            text="₹",
            values=("₹", "$", "€", "£", "AED"),
            size_hint=(None, None),
            size=(dp(55), dp(26)),
            background_color=CONTAINER_DARK,
            color=NEON_AMBER,
            font_size=sp(11),
            bold=True
        )
        self.cur_spinner.bind(text=self._on_currency_changed)
        top_r.add_widget(self.cur_spinner)

        # Quick Save button
        btn_save = Button(
            text="💾 Save",
            size_hint=(None, None),
            size=(dp(60), dp(26)),
            background_color=CONTAINER_DARK,
            color=NEON_GREEN,
            font_size=sp(10),
            bold=True
        )
        btn_save.bind(on_release=lambda *_: self.save_to_database(notify=True))
        top_r.add_widget(btn_save)

        # Calculate Flow button
        btn_calc = Button(
            text="⚡ Calc",
            size_hint=(None, None),
            size=(dp(60), dp(26)),
            background_color=CONTAINER_DARK,
            color=NEON_CYAN,
            font_size=sp(10),
            bold=True
        )
        btn_calc.bind(on_release=lambda *_: self.calculate_and_switch())
        top_r.add_widget(btn_calc)

        header.add_widget(top_r)

        sub_lbl = Label(text="Multi-Loans • Credit Cards • EPF/SIP • Term Life Shield", font_size=sp(8.5), color=TEXT_MUTED, halign="left", valign="middle", size_hint_y=None, height=dp(16))
        sub_lbl.bind(size=sub_lbl.setter("text_size"))
        header.add_widget(sub_lbl)

        return header

    def _on_currency_changed(self, spinner, text):
        self.currency = text

    # --- TOP TAB BAR ---
    def _build_tab_bar(self):
        tab_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36), padding=[dp(4), dp(2), dp(4), dp(2)], spacing=dp(3))
        with tab_bar.canvas.before:
            Color(*BG_OBSIDIAN)
            self.tab_bg = Rectangle(pos=tab_bar.pos, size=tab_bar.size)
        tab_bar.bind(pos=lambda *_: setattr(self.tab_bg, 'pos', tab_bar.pos),
                     size=lambda *_: setattr(self.tab_bg, 'size', tab_bar.size))

        self.tab_buttons = {}
        tabs = [
            ("incomes", "🏠 Loans"),
            ("cards", "💳 Cards"),
            ("savings", "💰 Invest"),
            ("expenses", "⚡ Living"),
            ("dashboard", "📊 Analytics"),
            ("simulator", "🔮 What-If")
        ]

        for sname, title in tabs:
            btn = Button(
                text=title,
                font_size=sp(9.5),
                bold=True,
                background_normal="",
                background_color=CONTAINER_DARK if sname == "incomes" else BG_BLACK,
                color=NEON_CYAN if sname == "incomes" else TEXT_MUTED
            )
            btn.bind(on_release=lambda _, name=sname: self._switch_tab(name))
            self.tab_buttons[sname] = btn
            tab_bar.add_widget(btn)

        return tab_bar

    def _switch_tab(self, screen_name):
        self.sm.current = screen_name
        for sname, btn in self.tab_buttons.items():
            if sname == screen_name:
                btn.background_color = CONTAINER_DARK
                btn.color = NEON_CYAN
            else:
                btn.background_color = BG_BLACK
                btn.color = TEXT_MUTED

    # ========================================================================
    # SCREEN 1: INCOMES & LOANS AMORTIZATION
    # ========================================================================
    def _build_screen_incomes(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(16)], spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))

        # Inflow Card
        c1 = DarkCard()
        lbl1 = Label(text="HOUSEHOLD MONTHLY INFLOWS", font_size=sp(12), bold=True, color=NEON_GREEN, size_hint_y=None, height=dp(20), halign="left")
        lbl1.bind(size=lbl1.setter("text_size"))
        c1.add_widget(lbl1)

        self.f_his_income = FieldBox("Your Monthly Net Income *", "Net salary or business earnings", NEON_CYAN, "numeric")
        self.f_wife_income = FieldBox("Wife's Monthly Net Income *", "Net take-home earnings (or 0)", NEON_CYAN, "numeric")
        self.f_other_income = FieldBox("Additional Inflows", "Rent, dividends, passive yield", NEON_CYAN, "numeric")
        c1.add_widget(self.f_his_income)
        c1.add_widget(self.f_wife_income)
        c1.add_widget(self.f_other_income)
        c1.height = dp(20) + self.f_his_income.height + self.f_wife_income.height + self.f_other_income.height + dp(30)
        content.add_widget(c1)

        # Residential Rent
        c_rent = DarkCard()
        self.f_rent = FieldBox("Residential Rent (if renting)", "Monthly rental outgo", NEON_AMBER, "numeric")
        c_rent.add_widget(self.f_rent)
        c_rent.height = self.f_rent.height + dp(24)
        content.add_widget(c_rent)

        # Multi-Loan Section
        c_loans_head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        lbl_l = Label(text="MORTGAGES & TOP-UP LOANS", font_size=sp(12), bold=True, color=NEON_AMBER, halign="left", valign="middle")
        lbl_l.bind(size=lbl_l.setter("text_size"))
        c_loans_head.add_widget(lbl_l)

        btn_add_loan = Button(
            text="+ Add Loan",
            size_hint=(None, None),
            size=(dp(85), dp(26)),
            background_color=CONTAINER_DARK,
            color=NEON_AMBER,
            font_size=sp(10),
            bold=True
        )
        btn_add_loan.bind(on_release=lambda *_: self._add_loan_ui())
        c_loans_head.add_widget(btn_add_loan)
        content.add_widget(c_loans_head)

        self.loans_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.loans_container.bind(minimum_height=self.loans_container.setter("height"))
        content.add_widget(self.loans_container)

        sv.add_widget(content)
        self.screen_incomes.add_widget(sv)

    def _add_loan_ui(self, data=None):
        card = DarkCard(bg_color=CONTAINER_DARK)

        # Header row: Category Spinner + Remove
        top_r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=dp(4))
        cat_sp = Spinner(
            text=data.get("category", "Primary Home Loan") if data else "Primary Home Loan",
            values=("Primary Home Loan", "Home Loan Top-Up", "2nd Home / Plot Loan", "Renovation Loan", "Vehicle / Car Loan", "Personal Loan", "Education Loan"),
            size_hint_x=0.75,
            background_color=INPUT_DARK,
            color=NEON_CYAN,
            font_size=sp(10),
            bold=True
        )
        top_r.add_widget(cat_sp)

        btn_del = Button(
            text="✕ Del",
            size_hint=(None, None),
            size=(dp(55), dp(28)),
            background_color=INPUT_DARK,
            color=NEON_ROSE,
            font_size=sp(10),
            bold=True
        )
        top_r.add_widget(btn_del)
        card.add_widget(top_r)

        # Fields: Desc, Principal, Rate, Start Date, EMI
        f_desc = FieldBox("Description / Lender", "e.g. SBI Maxgain, HDFC Top-up")
        f_princ = FieldBox("Total Sanctioned Principal", "Total borrowed amount", NEON_CYAN, "numeric")
        f_rate = FieldBox("Interest Rate % p.a.", "e.g. 8.5", NEON_AMBER, "numeric")
        f_start = FieldBox("Start Date (YYYY-MM)", "e.g. 2021-06", NEON_GREEN)
        f_emi = FieldBox("Monthly EMI *", "Monthly debit", NEON_ROSE, "numeric")

        if data:
            f_desc.set_text(data.get("description", ""))
            f_princ.set_text(data.get("principal", ""))
            f_rate.set_text(data.get("rate", ""))
            f_start.set_text(data.get("start_date", ""))
            f_emi.set_text(data.get("emi", ""))

        card.add_widget(f_desc)
        card.add_widget(f_princ)
        card.add_widget(f_rate)
        card.add_widget(f_start)
        card.add_widget(f_emi)

        card.height = dp(30) + f_desc.height + f_princ.height + f_rate.height + f_start.height + f_emi.height + dp(40)

        entry_obj = {
            "widget": card,
            "cat": cat_sp,
            "desc": f_desc,
            "principal": f_princ,
            "rate": f_rate,
            "start_date": f_start,
            "emi": f_emi
        }

        def _remove_card(*_):
            if len(self.loan_cards_data) > 1:
                self.loans_container.remove_widget(card)
                self.loan_cards_data.remove(entry_obj)

        btn_del.bind(on_release=_remove_card)
        self.loan_cards_data.append(entry_obj)
        self.loans_container.add_widget(card)

    # ========================================================================
    # SCREEN 2: CREDIT CARDS (LIMITS, EMIs & UTILIZATION)
    # ========================================================================
    def _build_screen_cards(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(16)], spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))

        head_r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30))
        lbl_c = Label(text="CREDIT CARDS: LIMITS & ACTIVE EMIs", font_size=sp(12), bold=True, color=NEON_ROSE, halign="left", valign="middle")
        lbl_c.bind(size=lbl_c.setter("text_size"))
        head_r.add_widget(lbl_c)

        btn_add_card = Button(
            text="+ Add Card",
            size_hint=(None, None),
            size=(dp(85), dp(26)),
            background_color=CONTAINER_DARK,
            color=NEON_ROSE,
            font_size=sp(10),
            bold=True
        )
        btn_add_card.bind(on_release=lambda *_: self._add_card_ui())
        head_r.add_widget(btn_add_card)
        content.add_widget(head_r)

        self.cards_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.cards_container.bind(minimum_height=self.cards_container.setter("height"))
        content.add_widget(self.cards_container)

        sv.add_widget(content)
        self.screen_cards.add_widget(sv)

    def _add_card_ui(self, data=None):
        card = DarkCard(bg_color=CONTAINER_DARK)

        top_r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=dp(4))
        lbl_card_title = Label(text="💳 Credit Card", font_size=sp(11), bold=True, color=NEON_CYAN, halign="left", valign="middle", size_hint_x=0.75)
        lbl_card_title.bind(size=lbl_card_title.setter("text_size"))
        top_r.add_widget(lbl_card_title)

        btn_del = Button(
            text="✕ Del",
            size_hint=(None, None),
            size=(dp(55), dp(28)),
            background_color=INPUT_DARK,
            color=NEON_ROSE,
            font_size=sp(10),
            bold=True
        )
        top_r.add_widget(btn_del)
        card.add_widget(top_r)

        f_name = FieldBox("Card Name / Bank *", "e.g. HDFC Regalia, ICICI Amazon, Amex")
        f_limit = FieldBox("Credit Limit", "Total sanctioned limit", NEON_CYAN, "numeric")
        f_bill = FieldBox("Monthly Bill *", "Current statement debit", NEON_ROSE, "numeric")

        type_sp = Spinner(
            text=data.get("spend_type", "Consistent Regular Spends") if data else "Consistent Regular Spends",
            values=("Consistent Regular Spends", "Includes Active Card EMIs"),
            size_hint_y=None,
            height=dp(32),
            background_color=INPUT_DARK,
            color=NEON_AMBER,
            font_size=sp(10),
            bold=True
        )

        f_emi_amt = FieldBox("EMI Component Amount", "Amount of bill that is installment EMI", NEON_ROSE, "numeric")
        f_sdate = FieldBox("EMI Start Date", "YYYY-MM")
        f_edate = FieldBox("EMI Freedom Date", "YYYY-MM (When EMI completes)")

        if data:
            f_name.set_text(data.get("name", ""))
            f_limit.set_text(data.get("credit_limit", ""))
            f_bill.set_text(data.get("bill", ""))
            f_emi_amt.set_text(data.get("emi_amount", ""))
            f_sdate.set_text(data.get("start_date", ""))
            f_edate.set_text(data.get("end_date", ""))

        card.add_widget(f_name)
        card.add_widget(f_limit)
        card.add_widget(f_bill)
        card.add_widget(type_sp)
        card.add_widget(f_emi_amt)
        card.add_widget(f_sdate)
        card.add_widget(f_edate)

        card.height = dp(30) + f_name.height + f_limit.height + f_bill.height + dp(32) + f_emi_amt.height + f_sdate.height + f_edate.height + dp(40)

        entry_obj = {
            "widget": card,
            "name": f_name,
            "limit": f_limit,
            "bill": f_bill,
            "spend_type": type_sp,
            "emi_amount": f_emi_amt,
            "start_date": f_sdate,
            "end_date": f_edate
        }

        def _remove_card(*_):
            if len(self.credit_cards_data) > 1:
                self.cards_container.remove_widget(card)
                self.credit_cards_data.remove(entry_obj)

        btn_del.bind(on_release=_remove_card)
        self.credit_cards_data.append(entry_obj)
        self.cards_container.add_widget(card)

    # ========================================================================
    # SCREEN 3: SAVINGS, INVESTMENTS & TERM INSURANCE
    # ========================================================================
    def _build_screen_savings(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(16)], spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))

        # 1. Wealth & Retirement Investments
        c_inv = DarkCard()
        lbl_inv = Label(text="COMMITTED SAVINGS & RETIREMENT", font_size=sp(12), bold=True, color=NEON_PURPLE, size_hint_y=None, height=dp(20), halign="left")
        lbl_inv.bind(size=lbl_inv.setter("text_size"))
        c_inv.add_widget(lbl_inv)

        self.f_epf = FieldBox("EPF Monthly Deposit", "Employee & employer portion", NEON_PURPLE, "numeric")
        self.f_nps = FieldBox("NPS Monthly Contribution", "National Pension System", NEON_PURPLE, "numeric")
        self.f_ulip = FieldBox("ULIP / Endowment Investment", "Investment insurance plans", NEON_PURPLE, "numeric")
        self.f_sip = FieldBox("Mutual Fund / Equity SIPs", "Systematic index/stock plans", NEON_CYAN, "numeric")
        self.f_fd = FieldBox("Fixed / Recurring Deposits", "Bank FDs / RDs", NEON_PURPLE, "numeric")
        self.f_inv_other = FieldBox("Other (PPF, SGB Gold, Real Estate)", "Other structured savings", NEON_PURPLE, "numeric")

        c_inv.add_widget(self.f_epf)
        c_inv.add_widget(self.f_nps)
        c_inv.add_widget(self.f_ulip)
        c_inv.add_widget(self.f_sip)
        c_inv.add_widget(self.f_fd)
        c_inv.add_widget(self.f_inv_other)

        c_inv.height = dp(20) + self.f_epf.height + self.f_nps.height + self.f_ulip.height + self.f_sip.height + self.f_fd.height + self.f_inv_other.height + dp(40)
        content.add_widget(c_inv)

        # 2. Dedicated Term Insurance Section
        c_term = DarkCard(bg_color=CONTAINER_DARK)
        lbl_term = Label(text="☂️ TERM INSURANCE & RISK PROTECTION", font_size=sp(12), bold=True, color=PRIMARY_BLUE, size_hint_y=None, height=dp(20), halign="left")
        lbl_term.bind(size=lbl_term.setter("text_size"))
        c_term.add_widget(lbl_term)

        lbl_term_sub = Label(
            text="Pure life risk cover. Recommended cover is 10x-15x annual income plus outstanding liabilities.",
            font_size=sp(8.5), color=TEXT_MUTED, halign="left", size_hint_y=None, height=dp(24)
        )
        lbl_term_sub.bind(size=lbl_term_sub.setter("text_size"))
        c_term.add_widget(lbl_term_sub)

        self.f_term_prem = FieldBox("Term Premium (Monthly Equivalent)", "Monthly outgo (or annual ÷ 12)", PRIMARY_BLUE, "numeric")
        self.f_term_sum = FieldBox("Total Term Sum Assured / Life Cover", "e.g. 10000000 for 1 Cr, 20000000 for 2 Cr", NEON_CYAN, "numeric")
        self.f_term_tenure = FieldBox("Covered Till Age / Maturity Year", "e.g. Till Age 65 or Year 2055", NEON_AMBER)
        self.f_term_nominee = FieldBox("Insured Person(s) / Policy Name", "e.g. HDFC Life Click 2 Protect (Self)", TEXT_MUTED)

        c_term.add_widget(self.f_term_prem)
        c_term.add_widget(self.f_term_sum)
        c_term.add_widget(self.f_term_tenure)
        c_term.add_widget(self.f_term_nominee)

        c_term.height = dp(20) + dp(24) + self.f_term_prem.height + self.f_term_sum.height + self.f_term_tenure.height + self.f_term_nominee.height + dp(40)
        content.add_widget(c_term)

        # 3. Investment Start Date
        c_start = DarkCard()
        lbl_st = Label(text="INVESTMENT START DATE & DISCIPLINE", font_size=sp(11), bold=True, color=NEON_GREEN, size_hint_y=None, height=dp(18), halign="left")
        lbl_st.bind(size=lbl_st.setter("text_size"))
        c_start.add_widget(lbl_st)

        self.f_inv_start_date = FieldBox("When did you start investing? (YYYY-MM)", "e.g. 2021-04. Computes longevity & corpus", NEON_GREEN)
        c_start.add_widget(self.f_inv_start_date)
        c_start.height = dp(18) + self.f_inv_start_date.height + dp(24)
        content.add_widget(c_start)

        sv.add_widget(content)
        self.screen_savings.add_widget(sv)

    # ========================================================================
    # SCREEN 4: UTILITIES & LIVING EXPENSES
    # ========================================================================
    def _build_screen_expenses(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(16)], spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))

        # Utilities
        c_u = DarkCard()
        lbl_u = Label(text="UTILITY BILL BREAKDOWN", font_size=sp(12), bold=True, color=NEON_CYAN, size_hint_y=None, height=dp(20), halign="left")
        lbl_u.bind(size=lbl_u.setter("text_size"))
        c_u.add_widget(lbl_u)

        self.f_elec = FieldBox("Electricity Bill", "Monthly power", NEON_CYAN, "numeric")
        self.f_water_gas = FieldBox("Water & Gas / LPG", "Piped gas, cylinders, water", NEON_CYAN, "numeric")
        self.f_internet = FieldBox("Broadband & Wi-Fi", "Home fiber connection", NEON_CYAN, "numeric")
        self.f_mobile = FieldBox("Mobile Recharges & DTH", "Phone & streaming plans", NEON_CYAN, "numeric")

        c_u.add_widget(self.f_elec)
        c_u.add_widget(self.f_water_gas)
        c_u.add_widget(self.f_internet)
        c_u.add_widget(self.f_mobile)
        c_u.height = dp(20) + self.f_elec.height + self.f_water_gas.height + self.f_internet.height + self.f_mobile.height + dp(30)
        content.add_widget(c_u)

        # Essential Needs
        c_n = DarkCard()
        lbl_n = Label(text="ESSENTIAL LIVING NEEDS", font_size=sp(12), bold=True, color=NEON_GREEN, size_hint_y=None, height=dp(20), halign="left")
        lbl_n.bind(size=lbl_n.setter("text_size"))
        c_n.add_widget(lbl_n)

        self.f_groceries = FieldBox("Groceries & Food Supplies", "Supermarket food, dairy, vegetables", NEON_GREEN, "numeric")
        self.f_healthcare = FieldBox("Healthcare & Medicines", "Doctor fees, pharmacy, medical tests", NEON_GREEN, "numeric")
        self.f_commute = FieldBox("Fuel & Commute", "Petrol, metro, bus, parking", NEON_GREEN, "numeric")
        self.f_education = FieldBox("Education & Childcare", "School fees, tuition, dependent support", NEON_GREEN, "numeric")

        c_n.add_widget(self.f_groceries)
        c_n.add_widget(self.f_healthcare)
        c_n.add_widget(self.f_commute)
        c_n.add_widget(self.f_education)
        c_n.height = dp(20) + self.f_groceries.height + self.f_healthcare.height + self.f_commute.height + self.f_education.height + dp(30)
        content.add_widget(c_n)

        # Discretionary Wants
        c_w = DarkCard()
        lbl_w = Label(text="DISCRETIONARY WANTS & LIFESTYLE", font_size=sp(12), bold=True, color=NEON_ROSE, size_hint_y=None, height=dp(20), halign="left")
        lbl_w.bind(size=lbl_w.setter("text_size"))
        c_w.add_widget(lbl_w)

        self.f_dining = FieldBox("Dining Out & Food Apps", "Restaurants, takeout, cafes", NEON_ROSE, "numeric")
        self.f_leisure = FieldBox("Entertainment, OTT & Shopping", "Movies, Netflix, gadgets, hobbies", NEON_ROSE, "numeric")

        c_w.add_widget(self.f_dining)
        c_w.add_widget(self.f_leisure)
        c_w.height = dp(20) + self.f_dining.height + self.f_leisure.height + dp(30)
        content.add_widget(c_w)

        sv.add_widget(content)
        self.screen_expenses.add_widget(sv)

    # ========================================================================
    # SCREEN 5: DIAGNOSTICS & ANALYTICS DASHBOARD
    # ========================================================================
    def _build_screen_dashboard(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.dash_content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(20)], spacing=dp(8))
        self.dash_content.bind(minimum_height=self.dash_content.setter("height"))

        # Health Score Banner
        self.card_score = DarkCard(bg_color=CONTAINER_DARK)
        self.lbl_score_grade = Label(text="READY FOR ANALYSIS", font_size=sp(13), bold=True, color=NEON_CYAN, size_hint_y=None, height=dp(22), halign="left")
        self.lbl_score_grade.bind(size=self.lbl_score_grade.setter("text_size"))
        self.lbl_score_summary = Label(text="Enter your figures and tap '⚡ Calc' in the top bar.", font_size=sp(9.5), color=TEXT_MUTED, size_hint_y=None, height=dp(18), halign="left")
        self.lbl_score_summary.bind(size=self.lbl_score_summary.setter("text_size"))

        self.card_score.add_widget(self.lbl_score_grade)
        self.card_score.add_widget(self.lbl_score_summary)
        self.card_score.height = dp(60)
        self.dash_content.add_widget(self.card_score)

        # Primary KPI Tiles Grid (2x2 Grid)
        kpi_grid = GridLayout(cols=2, size_hint_y=None, height=dp(130), spacing=dp(6))

        self.kpi_inflow_card, self.lbl_kpi_inflow = self._create_kpi_widget("Combined Inflow", "--", NEON_GREEN)
        self.kpi_outflow_card, self.lbl_kpi_outflow = self._create_kpi_widget("Total Outflow", "--", NEON_ROSE)
        self.kpi_surplus_card, self.lbl_kpi_surplus = self._create_kpi_widget("Net Monthly Surplus", "--", NEON_CYAN)
        self.kpi_dti_card, self.lbl_kpi_dti = self._create_kpi_widget("Total DTI Ratio", "--", NEON_AMBER)

        kpi_grid.add_widget(self.kpi_inflow_card)
        kpi_grid.add_widget(self.kpi_outflow_card)
        kpi_grid.add_widget(self.kpi_surplus_card)
        kpi_grid.add_widget(self.kpi_dti_card)
        self.dash_content.add_widget(kpi_grid)

        # Saving & Burden Ratio Badges
        c_ratios = DarkCard()
        self.lbl_save_ratio = Label(text="• Committed Invest: --  |  Total Saving Ratio: --%", font_size=sp(9.5), bold=True, color=NEON_CYAN, size_hint_y=None, height=dp(18), halign="left")
        self.lbl_save_ratio.bind(size=self.lbl_save_ratio.setter("text_size"))
        self.lbl_hl_burden = Label(text="• Mortgage & Top-Up Burden: --% (Safe: < 28%)", font_size=sp(9.5), bold=True, color=TEXT_MUTED, size_hint_y=None, height=dp(18), halign="left")
        self.lbl_hl_burden.bind(size=self.lbl_hl_burden.setter("text_size"))

        c_ratios.add_widget(self.lbl_save_ratio)
        c_ratios.add_widget(self.lbl_hl_burden)
        c_ratios.height = dp(56)
        self.dash_content.add_widget(c_ratios)

        # Visual Cash Flow Bar
        c_bar = DarkCard()
        lbl_bar = Label(text="CASH FLOW DISTRIBUTION BAR", font_size=sp(10), bold=True, color=TEXT_MUTED, size_hint_y=None, height=dp(16), halign="left")
        lbl_bar.bind(size=lbl_bar.setter("text_size"))
        c_bar.add_widget(lbl_bar)

        self.bar_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(14), spacing=dp(2))
        c_bar.add_widget(self.bar_layout)
        c_bar.height = dp(50)
        self.dash_content.add_widget(c_bar)

        # Dynamic Results Container (Roadmap, Amortization, CC Freedom, Term Cover, Report)
        self.results_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.results_container.bind(minimum_height=self.results_container.setter("height"))
        self.dash_content.add_widget(self.results_container)

        sv.add_widget(self.dash_content)
        self.screen_dashboard.add_widget(sv)

    def _create_kpi_widget(self, title: str, val: str, color):
        card = DarkCard(bg_color=CONTAINER_DARK, padding=[dp(8), dp(6), dp(8), dp(6)], spacing=dp(2))
        lbl_t = Label(text=title, font_size=sp(8.5), bold=True, color=TEXT_MUTED, size_hint_y=None, height=dp(14), halign="left")
        lbl_t.bind(size=lbl_t.setter("text_size"))
        lbl_v = Label(text=val, font_size=sp(13), bold=True, color=color, size_hint_y=None, height=dp(24), halign="left")
        lbl_v.bind(size=lbl_v.setter("text_size"))
        card.add_widget(lbl_t)
        card.add_widget(lbl_v)
        card.height = dp(58)
        return card, lbl_v

    # ========================================================================
    # SCREEN 6: INTERACTIVE WHAT-IF SIMULATOR
    # ========================================================================
    def _build_screen_simulator(self):
        sv = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(12), dp(8), dp(12), dp(20)], spacing=dp(8))
        content.bind(minimum_height=content.setter("height"))

        c_sim = DarkCard()
        lbl_s = Label(text="🔮 INTERACTIVE WHAT-IF OPTIMIZER", font_size=sp(12), bold=True, color=NEON_CYAN, size_hint_y=None, height=dp(20), halign="left")
        lbl_s.bind(size=lbl_s.setter("text_size"))
        c_sim.add_widget(lbl_s)

        sub_s = Label(text="Simulate how trimming discretionary spendings accelerates your Top-Up payoff & wealth compounding.", font_size=sp(8.5), color=TEXT_MUTED, size_hint_y=None, height=dp(24), halign="left")
        sub_s.bind(size=sub_s.setter("text_size"))
        c_sim.add_widget(sub_s)

        self.lbl_slider_val = Label(text="Discretionary Spending Trim: 0%", font_size=sp(10), bold=True, color=NEON_AMBER, size_hint_y=None, height=dp(18), halign="left")
        self.lbl_slider_val.bind(size=self.lbl_slider_val.setter("text_size"))
        c_sim.add_widget(self.lbl_slider_val)

        self.sim_slider = Slider(min=0, max=50, value=0, step=1, size_hint_y=None, height=dp(36))
        self.sim_slider.bind(value=self._on_sim_slider)
        c_sim.add_widget(self.sim_slider)

        self.sim_result_lbl = Label(
            text="Tap '⚡ Calc' first to unlock interactive simulation insights.",
            font_size=sp(9.5), color=TEXT_WHITE, halign="left", valign="top", size_hint_y=None, height=dp(160)
        )
        self.sim_result_lbl.bind(size=self.sim_result_lbl.setter("text_size"))
        c_sim.add_widget(self.sim_result_lbl)

        c_sim.height = dp(20) + dp(24) + dp(18) + dp(36) + dp(160) + dp(30)
        content.add_widget(c_sim)

        sv.add_widget(content)
        self.screen_simulator.add_widget(sv)

    def _on_sim_slider(self, slider, val):
        pct = int(val)
        self.lbl_slider_val.text = f"Discretionary Spending Trim: {pct}%"
        if not self.last_calc:
            return

        cur = self.currency
        wants = self.last_calc["total_wants"]
        monthly_freed = wants * (pct / 100.0)
        new_surplus = self.last_calc["net_savings"] + monthly_freed
        savings_5yr = new_surplus * 12 * 5
        compounded_5yr = 0
        monthly_r = 0.10 / 12.0
        for _ in range(60):
            compounded_5yr = (compounded_5yr + new_surplus) * (1 + monthly_r)

        txt = (
            f"💡 Simulation Insights ({pct}% Discretionary Trim):\n\n"
            f"• Monthly Cash Flow Freed: +{cur}{monthly_freed:,.2f}/mo\n"
            f"• New Monthly Surplus: {cur}{new_surplus:,.2f}/mo\n"
            f"• 5-Year Cumulative Principal Saved: {cur}{savings_5yr:,.2f}\n"
            f"• 5-Year Compounded Wealth (at 10% SIP return): {cur}{compounded_5yr:,.2f}\n\n"
            f"Strategic Impact:\n"
            f"Channeling {cur}{monthly_freed:,.2f}/mo directly into your Home Loan Top-Up principal slashes years of high-interest amortization!"
        )
        self.sim_result_lbl.text = txt

    # ========================================================================
    # CALCULATION & DIAGNOSTIC ENGINE
    # ========================================================================
    def calculate_and_switch(self):
        success = self.calculate_flow()
        if success:
            self._switch_tab("dashboard")

    def _parse_val(self, field_box: FieldBox, name: str, required: bool = False) -> float:
        text = field_box.get_text()
        if not text:
            if required:
                raise ValueError(f"'{name}' is required.")
            return 0.0
        cleaned = text.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")
        try:
            val = float(cleaned)
        except ValueError:
            raise ValueError(f"Invalid numeric value in '{name}'.")
        if val < 0:
            raise ValueError(f"'{name}' cannot be negative.")
        return val

    def calculate_flow(self) -> bool:
        cur = self.currency

        try:
            his_inc = self._parse_val(self.f_his_income, "Your Monthly Income", required=True)
            wife_inc = self._parse_val(self.f_wife_income, "Wife's Monthly Income", required=True)
            other_inc = self._parse_val(self.f_other_income, "Additional Inflows")
            total_income = his_inc + wife_inc + other_inc

            if total_income <= 0:
                self._show_alert("Validation Error", "Combined income must be greater than zero.")
                return False

            rent_val = self._parse_val(self.f_rent, "Residential Rent")

            # Parse Loans
            home_loans_total = 0.0
            topup_loans_total = 0.0
            other_loans_total = 0.0
            itemized_loans = []

            for r in self.loan_cards_data:
                cat = r["cat"].text.strip()
                desc = r["desc"].get_text()
                emi_str = r["emi"].get_text()
                amt_str = r["principal"].get_text()
                rate_str = r["rate"].get_text()
                date_str = r["start_date"].get_text()

                if not emi_str and not desc and not amt_str:
                    continue

                emi_val = float(emi_str.replace(",", "")) if emi_str else 0.0
                total_loan_amt = float(amt_str.replace(",", "")) if amt_str else 0.0
                rate_val = float(rate_str.replace("%", "").replace(",", "")) if rate_str else 0.0

                label = f"{cat} ({desc})" if desc else cat
                amort_info = calculate_amortization_leftover(total_loan_amt, rate_val, emi_val, date_str)

                itemized_loans.append({
                    "cat": cat,
                    "label": label,
                    "emi": emi_val,
                    "total_amt": total_loan_amt,
                    "rate": rate_val,
                    "start_date": date_str,
                    "amort": amort_info
                })

                if "Top-Up" in cat:
                    topup_loans_total += emi_val
                elif "Home Loan" in cat or "Plot" in cat or "Renovation" in cat:
                    home_loans_total += emi_val
                else:
                    other_loans_total += emi_val

            total_mortgages_and_topups = home_loans_total + topup_loans_total
            total_loans_liabilities = total_mortgages_and_topups + other_loans_total + rent_val

            # Parse Credit Cards
            itemized_cards = []
            total_cc_bills = 0.0
            total_cc_limits = 0.0
            total_cc_emis = 0.0

            for idx, r in enumerate(self.credit_cards_data, start=1):
                name = r["name"].get_text()
                lim_str = r["limit"].get_text()
                bill_str = r["bill"].get_text()
                btype = r["spend_type"].text.strip()
                emi_str = r["emi_amount"].get_text()
                sdate = r["start_date"].get_text()
                edate = r["end_date"].get_text()

                if not name and not bill_str and not lim_str:
                    continue

                bill_val = float(bill_str.replace(",", "")) if bill_str else 0.0
                lim_val = float(lim_str.replace(",", "")) if lim_str else 0.0
                emi_val = float(emi_str.replace(",", "")) if emi_str else 0.0

                c_label = name if name else f"Credit Card {idx}"
                util_pct = (bill_val / lim_val * 100.0) if lim_val > 0 else 0.0

                itemized_cards.append({
                    "name": c_label,
                    "bill": bill_val,
                    "limit": lim_val,
                    "util_pct": util_pct,
                    "btype": btype,
                    "emi": emi_val,
                    "start_date": sdate,
                    "end_date": edate
                })
                total_cc_bills += bill_val
                total_cc_limits += lim_val
                total_cc_emis += emi_val

            overall_cc_util = (total_cc_bills / total_cc_limits * 100.0) if total_cc_limits > 0 else 0.0

            # Parse Investments & Term Insurance
            epf = self._parse_val(self.f_epf, "EPF Deposit")
            nps = self._parse_val(self.f_nps, "NPS Contribution")
            ulip = self._parse_val(self.f_ulip, "ULIP / Insurance")
            sip = self._parse_val(self.f_sip, "Equity / Mutual Fund SIPs")
            fd = self._parse_val(self.f_fd, "Fixed Deposits")
            inv_other = self._parse_val(self.f_inv_other, "Other Investments")
            inv_start_str = self.f_inv_start_date.get_text()

            term_premium = self._parse_val(self.f_term_prem, "Term Insurance Premium")
            term_sum_assured = self._parse_val(self.f_term_sum, "Term Sum Assured")
            term_tenure_str = self.f_term_tenure.get_text()
            term_policy_name = self.f_term_nominee.get_text()

            total_committed_investments = epf + nps + ulip + sip + fd + inv_other + term_premium

            annual_income = total_income * 12
            recommended_cover = max(annual_income * 12, annual_income * 10 + total_mortgages_and_topups * 12)
            cover_multiple = (term_sum_assured / annual_income) if annual_income > 0 else 0.0

            inv_dt = parse_month_year(inv_start_str)
            now = datetime.now()
            invest_months_elapsed = max(0, (now.year - inv_dt.year) * 12 + (now.month - inv_dt.month)) if inv_dt else 0

            # Parse Utilities & Living
            elec = self._parse_val(self.f_elec, "Electricity Bill")
            water_gas = self._parse_val(self.f_water_gas, "Water & Gas")
            internet = self._parse_val(self.f_internet, "Broadband")
            mobile = self._parse_val(self.f_mobile, "Mobile")
            total_utilities = elec + water_gas + internet + mobile

            groceries = self._parse_val(self.f_groceries, "Groceries")
            healthcare = self._parse_val(self.f_healthcare, "Healthcare")
            commute = self._parse_val(self.f_commute, "Commute")
            education = self._parse_val(self.f_education, "Education")
            total_needs = groceries + healthcare + commute + education

            dining = self._parse_val(self.f_dining, "Dining Out")
            leisure = self._parse_val(self.f_leisure, "Entertainment")
            total_wants = dining + leisure

        except ValueError as err:
            self._show_alert("Validation Error", str(err))
            return False

        # Compute Aggregates & Ratios
        total_outflow = total_loans_liabilities + total_cc_bills + total_committed_investments + total_utilities + total_needs + total_wants
        net_disposable_surplus = total_income - total_outflow

        committed_saving_ratio = (total_committed_investments / total_income) * 100.0
        total_combined_saving_ratio = ((total_committed_investments + max(net_disposable_surplus, 0.0)) / total_income) * 100.0

        total_debt_payments = total_mortgages_and_topups + other_loans_total + total_cc_bills
        dti_ratio = (total_debt_payments / total_income) * 100.0
        hl_burden_ratio = (total_mortgages_and_topups / total_income) * 100.0
        total_mandatory_survival = total_mortgages_and_topups + rent_val + total_utilities + total_needs

        self.last_calc = {
            "total_income": total_income,
            "total_outflow": total_outflow,
            "net_savings": net_disposable_surplus,
            "total_wants": total_wants
        }

        # Health Score (0 - 100)
        health_score = 100
        if net_disposable_surplus < 0:
            health_score -= 35
        elif total_combined_saving_ratio < 20:
            health_score -= 15

        if dti_ratio > 45:
            health_score -= 25
        elif dti_ratio > 35:
            health_score -= 15

        if hl_burden_ratio > 35:
            health_score -= 15

        if overall_cc_util > 40:
            health_score -= 15

        if term_sum_assured == 0 and (total_mortgages_and_topups > 0 or total_income > 50000):
            health_score -= 5

        health_score = max(min(health_score, 100), 10)

        # Update KPI UI
        self.lbl_kpi_inflow.text = f"{cur}{total_income:,.0f}"
        self.lbl_kpi_outflow.text = f"{cur}{total_outflow:,.0f}"

        if net_disposable_surplus >= 0:
            self.lbl_kpi_surplus.text = f"+{cur}{net_disposable_surplus:,.0f}"
            self.lbl_kpi_surplus.color = NEON_GREEN
        else:
            self.lbl_kpi_surplus.text = f"-{cur}{abs(net_disposable_surplus):,.0f}"
            self.lbl_kpi_surplus.color = NEON_ROSE

        self.lbl_kpi_dti.text = f"{dti_ratio:.1f}%"
        self.lbl_kpi_dti.color = NEON_GREEN if dti_ratio <= 35 else (NEON_AMBER if dti_ratio <= 45 else NEON_ROSE)

        self.lbl_save_ratio.text = f"• Committed Invest: {cur}{total_committed_investments:,.0f} ({committed_saving_ratio:.1f}%) | Total Save: {total_combined_saving_ratio:.1f}%"
        self.lbl_hl_burden.text = f"• Mortgage & Top-Up Burden: {hl_burden_ratio:.1f}% of income (Safe: < 28%)"
        self.lbl_hl_burden.color = NEON_AMBER if hl_burden_ratio > 28 else TEXT_MUTED

        if health_score >= 80:
            self.lbl_score_grade.text = f"GRADE A  ({health_score}/100) - SOLID FLOW"
            self.lbl_score_grade.color = NEON_GREEN
            self.lbl_score_summary.text = "High wealth velocity & disciplined compounding leverage."
        elif health_score >= 60:
            self.lbl_score_grade.text = f"GRADE B  ({health_score}/100) - STABLE MARGIN"
            self.lbl_score_grade.color = NEON_CYAN
            self.lbl_score_summary.text = "Consistent savings. Target paying off top-ups and keeping card util < 30%."
        elif health_score >= 40:
            self.lbl_score_grade.text = f"GRADE C  ({health_score}/100) - VULNERABLE"
            self.lbl_score_grade.color = NEON_AMBER
            self.lbl_score_summary.text = "Elevated debt or high EMIs. Sudden shocks could trigger deficits."
        else:
            self.lbl_score_grade.text = f"GRADE D  ({health_score}/100) - CRITICAL DEFICIT"
            self.lbl_score_grade.color = NEON_ROSE
            self.lbl_score_summary.text = "Outflows exceed income! Freeze discretionary spendings immediately."

        # Update Visual Cash Flow Bar
        self._render_flow_bar(total_income, [
            (total_mortgages_and_topups, (0.388, 0.400, 0.945, 1)),
            (total_cc_bills, NEON_ROSE),
            (total_committed_investments, NEON_GREEN),
            (total_utilities, NEON_CYAN),
            (total_needs, NEON_AMBER),
            (total_wants, (0.925, 0.282, 0.600, 1)),
            (max(net_disposable_surplus, 0), (0.063, 0.725, 0.506, 1))
        ])

        # Populate Result Cards
        self._populate_results_view(
            cur, total_income, his_inc, wife_inc, other_inc,
            itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
            itemized_cards, total_cc_bills, total_cc_limits, overall_cc_util, total_cc_emis,
            epf, nps, ulip, sip, fd, inv_other, total_committed_investments,
            invest_months_elapsed, inv_start_str, committed_saving_ratio, total_combined_saving_ratio,
            term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover,
            total_utilities, total_needs, total_wants, total_mandatory_survival,
            total_outflow, net_disposable_surplus, dti_ratio, health_score
        )

        # Trigger Simulator initial render
        self._on_sim_slider(self.sim_slider, self.sim_slider.value)

        # Auto-save to SQLite Database so progress is never lost
        self.save_to_database(notify=False)

        return True

    def _render_flow_bar(self, total_income, segments):
        self.bar_layout.clear_widgets()
        total_alloc = sum(s[0] for s in segments)
        base = max(total_alloc, total_income, 1.0)

        for amt, col in segments:
            if amt <= 0:
                continue
            ratio = amt / base
            box = BoxLayout(size_hint_x=ratio)
            with box.canvas.before:
                Color(*col)
                rect = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(2)])
            box.bind(pos=lambda _, b=box, r=rect: setattr(r, 'pos', b.pos),
                     size=lambda _, b=box, r=rect: setattr(r, 'size', b.size))
            self.bar_layout.add_widget(box)

    def _populate_results_view(
        self, cur, total_income, his_inc, wife_inc, other_inc,
        itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
        itemized_cards, total_cc_bills, total_cc_limits, overall_cc_util, total_cc_emis,
        epf, nps, ulip, sip, fd, inv_other, total_committed,
        invest_months, inv_start_str, committed_ratio, total_saving_ratio,
        term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover,
        total_utilities, total_needs, total_wants, total_mandatory_survival,
        total_outflow, net_surplus, dti_ratio, health_score
    ):
        self.results_container.clear_widgets()

        # 1. Action Roadmap Card
        c_road = DarkCard()
        lbl_r_head = Label(text="🎯 STRATEGIC ACTION ROADMAP", font_size=sp(12), bold=True, color=NEON_CYAN, size_hint_y=None, height=dp(20), halign="left")
        lbl_r_head.bind(size=lbl_r_head.setter("text_size"))
        c_road.add_widget(lbl_r_head)

        # Bullets
        bullets = []
        if total_cc_bills > 0:
            bullets.append(f"• Priority 1: Clear credit cards ({cur}{total_cc_bills:,.0f}) in full to eliminate 36-42% interest bleed.")
        if topup_loans_total > 0:
            bullets.append(f"• Priority 2: Accelerate Top-Up prepayments ({cur}{topup_loans_total:,.0f}/mo) to cut high-interest amortization.")
        bullets.append(f"• Priority 3: Emergency Runway target: {cur}{(total_mandatory_survival * 6):,.0f} (6 months survival floor).")
        if net_surplus > 0:
            bullets.append(f"• Priority 4: Channel 70% of surplus ({cur}{(net_surplus * 0.7):,.0f}/mo) to increase index SIPs.")

        # Term Insurance Bullet
        if term_sum_assured <= 0:
            bullets.append(f"• Priority 5: ⚠️ CRITICAL GAP: No Term Insurance! Recommend {cur}{recommended_cover:,.0f} (~12x income) to protect dependents.")
        elif cover_multiple >= 10.0:
            bullets.append(f"• Priority 5: ✅ Robust Term Shield: {cur}{term_sum_assured:,.0f} ({cover_multiple:.1f}x income) adequately insulates your family.")
        else:
            bullets.append(f"• Priority 5: ⚠️ Under-Insured: Cover of {cur}{term_sum_assured:,.0f} ({cover_multiple:.1f}x income) is below benchmark ({cur}{recommended_cover:,.0f}).")

        lbl_b = Label(text="\n\n".join(bullets), font_size=sp(9), color=TEXT_WHITE, halign="left", valign="top", size_hint_y=None, height=dp(len(bullets) * 36))
        lbl_b.bind(size=lbl_b.setter("text_size"))
        c_road.add_widget(lbl_b)
        c_road.height = dp(24) + lbl_b.height + dp(24)
        self.results_container.add_widget(c_road)

        # 2. Term Insurance Dedicated Card
        c_term_diag = DarkCard(bg_color=CONTAINER_DARK)
        lbl_td = Label(text="☂️ LIFE PROTECTION & SUM ASSURED SHIELD", font_size=sp(11), bold=True, color=PRIMARY_BLUE, size_hint_y=None, height=dp(20), halign="left")
        lbl_td.bind(size=lbl_td.setter("text_size"))
        c_term_diag.add_widget(lbl_td)

        if term_sum_assured > 0:
            td_txt = (
                f"• Active Sum Assured: {cur}{term_sum_assured:,.0f} ({cover_multiple:.1f}x annual income)\n"
                f"• Monthly Risk Outflow: {cur}{term_premium:,.0f}/mo\n"
                f"• Recommended Benchmark: {cur}{recommended_cover:,.0f} (10x-15x income + loans)\n"
                f"• Policy: {term_policy_name or 'Pure Term Plan'} ({term_tenure_str or 'Not specified'})"
            )
        else:
            td_txt = (
                f"• No pure term life insurance entered.\n"
                f"• Recommended Minimum Shield: {cur}{recommended_cover:,.0f} (~12x annual income) to clear mortgages in tragedy."
            )

        lbl_td_content = Label(text=td_txt, font_size=sp(9), color=TEXT_WHITE, halign="left", valign="top", size_hint_y=None, height=dp(70))
        lbl_td_content.bind(size=lbl_td_content.setter("text_size"))
        c_term_diag.add_widget(lbl_td_content)
        c_term_diag.height = dp(20) + dp(70) + dp(20)
        self.results_container.add_widget(c_term_diag)

        # 3. Loan Amortization Tracker
        if itemized_loans:
            c_amort = DarkCard()
            lbl_am = Label(text="🏠 LOAN AMORTIZATION & PROGRESS", font_size=sp(11), bold=True, color=NEON_AMBER, size_hint_y=None, height=dp(20), halign="left")
            lbl_am.bind(size=lbl_am.setter("text_size"))
            c_amort.add_widget(lbl_am)

            am_lines = []
            for it in itemized_loans:
                am = it["amort"]
                if am:
                    am_lines.append(f"• {it['label']}: EMI {cur}{it['emi']:,.0f} | Paid: {am['completed_pct']:.1f}% | Left: {cur}{am['balance']:,.0f} (~{am['remaining_months']//12}y {am['remaining_months']%12}m left)")
                else:
                    am_lines.append(f"• {it['label']}: EMI {cur}{it['emi']:,.0f}")

            lbl_am_c = Label(text="\n\n".join(am_lines), font_size=sp(8.5), color=TEXT_WHITE, halign="left", valign="top", size_hint_y=None, height=dp(len(am_lines) * 32))
            lbl_am_c.bind(size=lbl_am_c.setter("text_size"))
            c_amort.add_widget(lbl_am_c)
            c_amort.height = dp(20) + lbl_am_c.height + dp(20)
            self.results_container.add_widget(c_amort)

        # 4. Credit Card Freedom Calendar
        if itemized_cards:
            c_cc = DarkCard()
            lbl_cc = Label(text="💳 CARDS UTILIZATION & FREEDOM DATES", font_size=sp(11), bold=True, color=NEON_ROSE, size_hint_y=None, height=dp(20), halign="left")
            lbl_cc.bind(size=lbl_cc.setter("text_size"))
            c_cc.add_widget(lbl_cc)

            cc_lines = [f"Overall Card Utilization: {overall_cc_util:.1f}% (Healthy: < 30%)"]
            for c in itemized_cards:
                emi_s = f" | Active EMI: {cur}{c['emi']:,.0f} (Ends: {c['end_date']})" if c['emi'] > 0 else ""
                cc_lines.append(f"• {c['name']}: Bill {cur}{c['bill']:,.0f} / Limit {cur}{c['limit']:,.0f} ({c['util_pct']:.1f}% util){emi_s}")

            lbl_cc_c = Label(text="\n\n".join(cc_lines), font_size=sp(8.5), color=TEXT_WHITE, halign="left", valign="top", size_hint_y=None, height=dp(len(cc_lines) * 28))
            lbl_cc_c.bind(size=lbl_cc_c.setter("text_size"))
            c_cc.add_widget(lbl_cc_c)
            c_cc.height = dp(20) + lbl_cc_c.height + dp(20)
            self.results_container.add_widget(c_cc)

    # ========================================================================
    # DATABASE PERSISTENCE (SAVE / LOAD / RESET)
    # ========================================================================
    def save_to_database(self, notify: bool = True):
        try:
            profile_dict = {
                "currency": self.cur_spinner.text,
                "his_income": float(self.f_his_income.get_text() or 0),
                "wife_income": float(self.f_wife_income.get_text() or 0),
                "other_income": float(self.f_other_income.get_text() or 0),
                "rent": float(self.f_rent.get_text() or 0),
                "inv_start_date": self.f_inv_start_date.get_text(),
                "epf": float(self.f_epf.get_text() or 0),
                "nps": float(self.f_nps.get_text() or 0),
                "ulip": float(self.f_ulip.get_text() or 0),
                "sip": float(self.f_sip.get_text() or 0),
                "fd": float(self.f_fd.get_text() or 0),
                "inv_other": float(self.f_inv_other.get_text() or 0),
                "term_premium": float(self.f_term_prem.get_text() or 0),
                "term_sum_assured": float(self.f_term_sum.get_text() or 0),
                "term_tenure": self.f_term_tenure.get_text(),
                "term_nominee": self.f_term_nominee.get_text(),
                "elec": float(self.f_elec.get_text() or 0),
                "water_gas": float(self.f_water_gas.get_text() or 0),
                "internet": float(self.f_internet.get_text() or 0),
                "mobile": float(self.f_mobile.get_text() or 0),
                "groceries": float(self.f_groceries.get_text() or 0),
                "healthcare": float(self.f_healthcare.get_text() or 0),
                "commute": float(self.f_commute.get_text() or 0),
                "education": float(self.f_education.get_text() or 0),
                "dining": float(self.f_dining.get_text() or 0),
                "leisure": float(self.f_leisure.get_text() or 0),
            }

            loans_list = []
            for r in self.loan_cards_data:
                loans_list.append({
                    "category": r["cat"].text,
                    "description": r["desc"].get_text(),
                    "principal": float(r["principal"].get_text() or 0),
                    "rate": float(r["rate"].get_text() or 0),
                    "start_date": r["start_date"].get_text(),
                    "emi": float(r["emi"].get_text() or 0),
                })

            cards_list = []
            for r in self.credit_cards_data:
                cards_list.append({
                    "name": r["name"].get_text(),
                    "credit_limit": float(r["limit"].get_text() or 0),
                    "bill": float(r["bill"].get_text() or 0),
                    "spend_type": r["spend_type"].text,
                    "emi_amount": float(r["emi_amount"].get_text() or 0),
                    "start_date": r["start_date"].get_text(),
                    "end_date": r["end_date"].get_text(),
                })

            self.db.save_data(profile_dict, loans_list, cards_list)
            if notify:
                self._show_alert("Saved", "Your financial profile has been saved to SQLite successfully!")
        except Exception as e:
            if notify:
                self._show_alert("Save Error", str(e))

    def _load_from_database(self):
        prof, loans, cards = self.db.load_data()

        if prof:
            self.cur_spinner.text = prof.get("currency", "₹")
            self.currency = self.cur_spinner.text

            def _s(val):
                return "" if (val is None or val == 0) else f"{val:g}"

            self.f_his_income.set_text(_s(prof.get("his_income")))
            self.f_wife_income.set_text(_s(prof.get("wife_income")))
            self.f_other_income.set_text(_s(prof.get("other_income")))
            self.f_rent.set_text(_s(prof.get("rent")))

            self.f_epf.set_text(_s(prof.get("epf")))
            self.f_nps.set_text(_s(prof.get("nps")))
            self.f_ulip.set_text(_s(prof.get("ulip")))
            self.f_sip.set_text(_s(prof.get("sip")))
            self.f_fd.set_text(_s(prof.get("fd")))
            self.f_inv_other.set_text(_s(prof.get("inv_other")))
            self.f_inv_start_date.set_text(prof.get("inv_start_date") or "")

            self.f_term_prem.set_text(_s(prof.get("term_premium")))
            self.f_term_sum.set_text(_s(prof.get("term_sum_assured")))
            self.f_term_tenure.set_text(prof.get("term_tenure") or "")
            self.f_term_nominee.set_text(prof.get("term_nominee") or "")

            self.f_elec.set_text(_s(prof.get("elec")))
            self.f_water_gas.set_text(_s(prof.get("water_gas")))
            self.f_internet.set_text(_s(prof.get("internet")))
            self.f_mobile.set_text(_s(prof.get("mobile")))

            self.f_groceries.set_text(_s(prof.get("groceries")))
            self.f_healthcare.set_text(_s(prof.get("healthcare")))
            self.f_commute.set_text(_s(prof.get("commute")))
            self.f_education.set_text(_s(prof.get("education")))

            self.f_dining.set_text(_s(prof.get("dining")))
            self.f_leisure.set_text(_s(prof.get("leisure")))

        # Loans
        if loans:
            for l in loans:
                self._add_loan_ui(l)
        else:
            self._add_loan_ui({"category": "Primary Home Loan"})
            self._add_loan_ui({"category": "Home Loan Top-Up"})

        # Credit Cards
        if cards:
            for c in cards:
                self._add_card_ui(c)
        else:
            self._add_card_ui()
            self._add_card_ui()

    def _show_alert(self, title: str, message: str):
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        lbl = Label(text=message, font_size=sp(11), color=TEXT_WHITE, halign="center", valign="middle")
        lbl.bind(size=lbl.setter("text_size"))
        content.add_widget(lbl)

        btn = Button(
            text="OK",
            size_hint=(1, None),
            height=dp(36),
            background_color=CONTAINER_DARK,
            color=NEON_CYAN,
            font_size=sp(11),
            bold=True
        )
        content.add_widget(btn)

        popup = Popup(
            title=title,
            title_color=NEON_CYAN,
            title_size=sp(12),
            content=content,
            size_hint=(0.85, 0.35),
            auto_dismiss=True
        )
        btn.bind(on_release=popup.dismiss)
        popup.open()


if __name__ == "__main__":
    FinancialFlowMobileApp().run()
