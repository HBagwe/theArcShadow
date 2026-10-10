#!/usr/bin/env python3
"""
Household Financial Flow & Future Wealth Stability Planner
Advanced Financial Intelligence System - Cyber Dark Edition:
- Pitch Black GUI Theme (#000000 / #0a0a0f) with Ultra-Vivid Neon Colors & High-Contrast Typography.
- Fixed Text Box Styling: High-contrast white text (#ffffff) with glowing cyan cursor (#00f2fe)
  to ensure 100% visibility regardless of macOS system appearance mode.
- Multi-Loan Engine: Home Loans, Top-Ups with Total Sanctioned Amount, Interest Rate,
  Start Date, Amortization Tracking (Completed % vs Leftover Balance).
- Credit Card Engine: Real-time vector card thumbnail rendering, Credit Limit,
  Utilization % Gauge, Consistency / EMI Split, EMI Start/End Dates, and Cash-Flow Freedom Calendar.
- Savings & Investments Engine: EPF, NPS, ULIP, SIP, FD/RD, Investment Start Date,
  Tenure-based Saving Ratio, and Long-Term Compounding Analytics.
- Dedicated Term Insurance Section: Premium Outflows, Total Sum Assured / Life Cover,
  10x-15x Income Multiplier Sufficiency Diagnostics, and Family Debt Insulation Shield.
- Utilities, Essential Living Needs, and Discretionary Lifestyle Outflows.
- 50/30/20 Rule, DTI, Home Loan Burden, Emergency Runway, Interactive What-If Simulator,
  and Exportable Financial Reports.
- STRICTLY ZERO DEFAULT VALUES IN INPUT FIELDS.
"""

import math
import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ---------------- UTILITY & DATE PARSING HELPERS ----------------

def parse_month_year(text: str):
    """Parses various date/month-year formats into a datetime object."""
    if not text:
        return None
    s = text.strip()
    patterns = ["%Y-%m", "%m/%Y", "%m-%Y", "%Y/%m", "%b %Y", "%B %Y", "%Y"]
    for p in patterns:
        try:
            return datetime.strptime(s, p)
        except ValueError:
            pass

    # Regex fallback for YYYY-MM or MM-YYYY
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
    """
    Calculates completed months, leftover balance, and percentage completed
    using standard loan amortization formula.
    """
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


# ---------------- VECTOR CREDIT CARD GRAPHICS ----------------

def detect_card_brand(name: str):
    """Detects bank and payment network from card name."""
    s = name.lower().strip()
    if not s:
        return {"brand": "EMPTY", "bg": "#12121a", "accent": "#3f3f5a", "title": "CARD", "chip": "#e2e8f0", "network": ""}

    if "hdfc" in s:
        return {"brand": "HDFC", "bg": "#081d38", "accent": "#0056b3", "title": "HDFC BANK", "chip": "#f59e0b", "network": "REGALIA" if "regalia" in s else ("MILLENNIA" if "millennia" in s else "HDFC")}
    if "icici" in s:
        return {"brand": "ICICI", "bg": "#5c0e0e", "accent": "#b91c1c", "title": "ICICI BANK", "chip": "#f59e0b", "network": "AMAZON" if "amazon" in s else "ICICI"}
    if "sbi" in s:
        return {"brand": "SBI", "bg": "#024a75", "accent": "#0284c7", "title": "SBI CARD", "chip": "#facc15", "network": "SIMPLY" if "simply" in s else "SBI"}
    if "axis" in s:
        return {"brand": "AXIS", "bg": "#580f2d", "accent": "#9d174d", "title": "AXIS BANK", "chip": "#e2e8f0", "network": "MAGNUS" if "magnus" in s else "AXIS"}
    if "kotak" in s:
        return {"brand": "KOTAK", "bg": "#7f1212", "accent": "#dc2626", "title": "KOTAK", "chip": "#facc15", "network": "KOTAK"}
    if "amex" in s or "american express" in s:
        return {"brand": "AMEX", "bg": "#1e293b", "accent": "#00f2fe", "title": "AMEX", "chip": "#cbd5e1", "network": "PLATINUM" if "plat" in s else "CENTURION"}
    if "citi" in s:
        return {"brand": "CITI", "bg": "#00284e", "accent": "#0284c7", "title": "CITI", "chip": "#f59e0b", "network": "CITI"}
    if "chase" in s:
        return {"brand": "CHASE", "bg": "#0b5286", "accent": "#0284c7", "title": "CHASE", "chip": "#e2e8f0", "network": "SAPPHIRE" if "sapph" in s else "CHASE"}
    if "rupay" in s:
        return {"brand": "RUPAY", "bg": "#034d38", "accent": "#10b981", "title": "RuPay", "chip": "#facc15", "network": "RUPAY"}
    if "visa" in s:
        return {"brand": "VISA", "bg": "#142866", "accent": "#3b82f6", "title": "VISA", "chip": "#facc15", "network": "VISA"}
    if "mastercard" in s or "master" in s:
        return {"brand": "MASTERCARD", "bg": "#18181b", "accent": "#ea580c", "title": "MASTER", "chip": "#facc15", "network": "MC"}
    if "discover" in s:
        return {"brand": "DISCOVER", "bg": "#7c2d12", "accent": "#ea580c", "title": "DISCOVER", "chip": "#e2e8f0", "network": "DISCOVER"}
    if "apple" in s:
        return {"brand": "APPLE", "bg": "#27272a", "accent": "#94a3b8", "title": "APPLE CARD", "chip": "#475569", "network": "APPLE"}

    return {"brand": "GENERIC", "bg": "#1e1e2d", "accent": "#64748b", "title": s[:10].upper(), "chip": "#f59e0b", "network": "CARD"}


def draw_card_thumbnail(canvas: tk.Canvas, card_info: dict):
    """Draws a vivid mini credit card graphic on a 64x40 Tkinter canvas in pitch dark mode."""
    canvas.delete("all")
    w = 64
    h = 40
    bg = card_info["bg"]
    chip = card_info["chip"]
    title = card_info["title"]
    network = card_info["network"]

    canvas.create_rectangle(1, 1, w - 1, h - 1, fill=bg, outline="#00f2fe" if card_info["brand"] != "EMPTY" else "#272738", width=1)

    if card_info["brand"] == "EMPTY":
        canvas.create_rectangle(3, 3, w - 3, h - 3, outline="#3f3f5a", width=1, dash=(2, 2))
        canvas.create_text(w // 2, h // 2, text="+ CARD", fill="#64748b", font=("Helvetica", 7, "bold"))
        return

    # EMV Chip
    canvas.create_rectangle(6, 12, 16, 20, fill=chip, outline="#94a3b8", width=1)
    canvas.create_line(11, 12, 11, 20, fill="#78350f")

    # Contactless wave symbol
    canvas.create_arc(18, 12, 24, 20, start=30, extent=60, style=tk.ARC, outline="#ffffff", width=1)
    canvas.create_arc(20, 10, 28, 22, start=30, extent=60, style=tk.ARC, outline="#ffffff", width=1)

    # Card Bank Title
    canvas.create_text(6, 6, anchor="nw", text=title[:8], fill="#ffffff", font=("Helvetica", 6, "bold"))

    # Network Logo
    if card_info["brand"] == "MASTERCARD":
        canvas.create_oval(w - 20, h - 14, w - 10, h - 4, fill="#ef4444", outline="")
        canvas.create_oval(w - 15, h - 14, w - 5, h - 4, fill="#f97316", outline="")
    elif card_info["brand"] == "VISA":
        canvas.create_text(w - 5, h - 8, anchor="e", text="VISA", fill="#facc15", font=("Helvetica", 6, "bold"))
    elif card_info["brand"] == "RUPAY":
        canvas.create_text(w - 5, h - 8, anchor="e", text="RuPay", fill="#00f2fe", font=("Helvetica", 6, "bold"))
    elif card_info["brand"] == "AMEX":
        canvas.create_text(w - 5, h - 8, anchor="e", text="AMEX", fill="#00f2fe", font=("Helvetica", 6, "bold"))
    else:
        disp = network[:6] if network else title[:6]
        canvas.create_text(w - 5, h - 8, anchor="e", text=disp, fill="#ffffff", font=("Helvetica", 5, "bold"))


# ---------------- MAIN APPLICATION ----------------

class FinancialPlannerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Household Financial Flow & Future Wealth Stability Planner (Dark Mode)")
        self.root.geometry("1280x880")
        self.root.minsize(1080, 750)

        # Configure High-Contrast Dark Color Palette
        self._setup_dark_palette()

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self._configure_ttk_styles()

        self.loan_rows = []
        self.card_rows = []
        self.latest_report_text = ""
        self.last_calc_data = None

        self._build_ui()

    def _setup_dark_palette(self):
        # Pitch Dark Base Backgrounds
        self.bg_root = "#000000"          # Pure Pitch Black
        self.bg_panel = "#09090d"         # Deep Obsidian
        self.card_bg = "#111118"          # Pitch Dark Slate Card
        self.inner_box_bg = "#161622"      # High-contrast container for inner rows
        self.entry_bg = "#0c0c12"          # Ultra dark entry background
        self.entry_fg = "#ffffff"          # Crisp Pure White (100% visible!)
        self.entry_cursor = "#00f2fe"      # Neon Cyan Blinking Cursor
        self.entry_select_bg = "#2563eb"   # Electric Blue Selection

        # Vibrant Accent Colors
        self.neon_cyan = "#00f2fe"
        self.neon_green = "#00f59b"
        self.neon_rose = "#ff0055"
        self.neon_amber = "#fbbf24"
        self.neon_purple = "#a855f7"
        self.primary_blue = "#38bdf8"
        self.text_dark = "#ffffff"
        self.text_muted = "#94a3b8"
        self.border_color = "#272738"
        self.border_highlight = "#00f2fe"

    def _configure_ttk_styles(self):
        self.root.configure(bg=self.bg_root)

        # Option DB for combobox listbox popup
        self.root.option_add("*TCombobox*Listbox.background", "#161622")
        self.root.option_add("*TCombobox*Listbox.foreground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#2563eb")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

        self.style.configure(".", background=self.bg_root, foreground=self.text_dark, font=("Helvetica", 10))
        self.style.configure("TFrame", background=self.bg_root)

        # Notebook tabs styling
        self.style.configure("TNotebook", background=self.bg_root, borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background="#161622",
            foreground="#94a3b8",
            padding=[12, 6],
            font=("Helvetica", 9, "bold"),
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#1e1b4b"), ("active", "#2e2a72")],
            foreground=[("selected", "#00f2fe"), ("active", "#ffffff")]
        )

        # Combobox styling
        self.style.configure(
            "TCombobox",
            fieldbackground=self.entry_bg,
            background="#1e1e2d",
            foreground="#ffffff",
            darkcolor=self.border_color,
            lightcolor=self.border_color,
            arrowcolor="#00f2fe"
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.entry_bg)],
            foreground=[("readonly", "#ffffff")]
        )

        # Buttons
        self.style.configure(
            "Primary.TButton",
            font=("Helvetica", 10, "bold"),
            foreground="#000000",
            background=self.neon_cyan,
            padding=(16, 9),
            borderwidth=0
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", "#38bdf8"), ("pressed", "#0284c7")]
        )

        self.style.configure(
            "Secondary.TButton",
            font=("Helvetica", 10, "bold"),
            foreground="#ffffff",
            background="#272738",
            padding=(10, 6),
            borderwidth=0
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#3f3f5a"), ("pressed", "#161622")]
        )

        self.style.configure(
            "ActionSmall.TButton",
            font=("Helvetica", 8, "bold"),
            foreground="#00f2fe",
            background="#1e1e2d",
            padding=(8, 4),
            borderwidth=0
        )
        self.style.map(
            "ActionSmall.TButton",
            background=[("active", "#2563eb"), ("pressed", "#1d4ed8")],
            foreground=[("active", "#ffffff")]
        )

        self.style.configure("Vertical.TScrollbar", background="#1e1e2d", troughcolor="#09090d", bordercolor=self.border_color, arrowcolor="#00f2fe")

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_root, padx=12, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header Bar
        header = tk.Frame(main_frame, bg=self.bg_root)
        header.pack(fill=tk.X, pady=(0, 10))

        title_box = tk.Frame(header, bg=self.bg_root)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="⚡ HOUSEHOLD FINANCIAL FLOW & WEALTH PLANNER",
            font=("Helvetica", 16, "bold"),
            fg=self.neon_cyan,
            bg=self.bg_root
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Deep dark analytics: Loan amortization progress, credit cards, EPF/NPS/SIP saving velocity & Term Life protection shield.",
            font=("Helvetica", 9),
            fg=self.text_muted,
            bg=self.bg_root
        ).pack(anchor="w", pady=(1, 0))

        # Currency Selector
        top_ctrl = tk.Frame(header, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1, padx=8, pady=4)
        top_ctrl.pack(side=tk.RIGHT)

        tk.Label(top_ctrl, text="CURRENCY:", font=("Helvetica", 8, "bold"), fg=self.neon_amber, bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 4))
        self.currency_var = tk.StringVar(value="₹")
        for sym in ["₹", "$", "€", "£", "AED"]:
            tk.Radiobutton(
                top_ctrl, text=sym, variable=self.currency_var, value=sym,
                bg=self.card_bg, fg="#ffffff", selectcolor="#2563eb", activebackground=self.card_bg,
                activeforeground="#00f2fe", font=("Helvetica", 9, "bold")
            ).pack(side=tk.LEFT, padx=1)

        # Body Layout
        body = tk.Frame(main_frame, bg=self.bg_root)
        body.pack(fill=tk.BOTH, expand=True)

        # Left Column: Input Tabs
        left_col = tk.Frame(body, bg=self.bg_root, width=590)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        left_col.pack_propagate(False)

        # Right Column: Diagnostic Dashboard
        right_col = tk.Frame(body, bg=self.bg_root)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_input_pane(left_col)
        self._build_dashboard_pane(right_col)

    # ---------------- LEFT COLUMN: INPUT PANE ----------------
    def _build_input_pane(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Incomes & Loans
        tab_loans = tk.Frame(self.notebook, bg=self.card_bg)
        self.notebook.add(tab_loans, text="🏠 Incomes & Loans")
        self._build_tab_incomes_and_loans(tab_loans)

        # Tab 2: Credit Cards
        tab_cards = tk.Frame(self.notebook, bg=self.card_bg)
        self.notebook.add(tab_cards, text="💳 Credit Cards")
        self._build_tab_credit_cards(tab_cards)

        # Tab 3: Savings & Investments
        tab_savings = tk.Frame(self.notebook, bg=self.card_bg)
        self.notebook.add(tab_savings, text="💰 Savings & Invest")
        self._build_tab_savings_investments(tab_savings)

        # Tab 4: Utilities & Living Needs
        tab_living = tk.Frame(self.notebook, bg=self.card_bg)
        self.notebook.add(tab_living, text="⚡ Utilities & Living")
        self._build_tab_utilities_needs(tab_living)

        # Bottom Action Bar
        action_bar = tk.Frame(parent, bg=self.bg_root, pady=8)
        action_bar.pack(fill=tk.X)

        calc_btn = ttk.Button(
            action_bar,
            text="⚡ CALCULATE FLOW & RUN DIAGNOSTICS",
            style="Primary.TButton",
            command=self.calculate
        )
        calc_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        reset_btn = ttk.Button(
            action_bar,
            text="RESET ALL",
            style="Secondary.TButton",
            command=self.reset_all_fields
        )
        reset_btn.pack(side=tk.RIGHT)

    def _create_scroll_wrapper(self, parent):
        canvas = tk.Canvas(parent, bg=self.card_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=self.card_bg, padx=12, pady=10)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win, width=e.width)

        canvas.bind("<Configure>", _on_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return inner

    def _create_text_entry(self, parent, width: int = None) -> tk.Entry:
        """Creates a high-contrast entry box with crystal-clear white text and glowing cyan cursor."""
        entry = tk.Entry(
            parent,
            font=("Helvetica", 10, "bold"),
            bg=self.entry_bg,
            fg=self.entry_fg,
            insertbackground=self.entry_cursor,
            selectbackground=self.entry_select_bg,
            selectforeground="#ffffff",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self.border_color,
            highlightcolor=self.neon_cyan,
            width=width if width else 20
        )
        entry.delete(0, tk.END)  # Strictly no default values
        return entry

    def _create_input_field(self, parent, label: str, desc: str, required: bool = False, accent_color: str = None) -> tk.Entry:
        box = tk.Frame(parent, bg=self.card_bg)
        box.pack(fill=tk.X, pady=3)

        top_r = tk.Frame(box, bg=self.card_bg)
        top_r.pack(fill=tk.X)

        title_color = accent_color if accent_color else self.text_dark
        tk.Label(top_r, text=label, font=("Helvetica", 9, "bold"), fg=title_color, bg=self.card_bg).pack(side=tk.LEFT)
        if required:
            tk.Label(top_r, text=" *", font=("Helvetica", 9, "bold"), fg=self.neon_rose, bg=self.card_bg).pack(side=tk.LEFT)

        if desc:
            tk.Label(box, text=desc, font=("Helvetica", 8), fg=self.text_muted, bg=self.card_bg).pack(anchor="w", pady=(0, 2))

        entry = self._create_text_entry(box)
        entry.pack(fill=tk.X, ipady=3)
        return entry

    # ---------------- TAB 1: INCOMES & AMORTIZED LOANS ----------------
    def _build_tab_incomes_and_loans(self, parent):
        frame = self._create_scroll_wrapper(parent)

        tk.Label(frame, text="HOUSEHOLD MONTHLY INFLOWS", font=("Helvetica", 11, "bold"), fg=self.neon_green, bg=self.card_bg).pack(anchor="w", pady=(0, 2))

        self.entry_his_income = self._create_input_field(
            frame, "Your Monthly Net Income", "Net monthly take-home salary or professional earnings", required=True, accent_color=self.neon_cyan
        )
        self.entry_wife_income = self._create_input_field(
            frame, "Wife's Monthly Net Income", "Net monthly take-home earnings (enter 0 if single earner)", required=True, accent_color=self.neon_cyan
        )
        self.entry_other_income = self._create_input_field(
            frame, "Additional Household Inflows", "Rental yield, dividends, passive income, side gigs", accent_color=self.neon_cyan
        )

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=8)

        # Home Loans, Top-Ups & Liabilities with Amortization Details
        tk.Label(frame, text="HOME LOANS, TOP-UPS & LIABILITIES AMORTIZATION", font=("Helvetica", 11, "bold"), fg=self.neon_amber, bg=self.card_bg).pack(anchor="w")
        tk.Label(
            frame,
            text="Add loan principal, interest rate, and start date to compute completed % and leftover balance.",
            font=("Helvetica", 8),
            fg=self.text_muted,
            bg=self.card_bg
        ).pack(anchor="w", pady=(1, 4))

        self.loans_container = tk.Frame(frame, bg=self.card_bg)
        self.loans_container.pack(fill=tk.X, pady=2)

        # Start with 2 clean empty cards (Primary Home Loan, Top-Up Loan) - NO DEFAULTS
        self._add_loan_card("Primary Home Loan")
        self._add_loan_card("Home Loan Top-Up")

        l_btn_box = tk.Frame(frame, bg=self.card_bg)
        l_btn_box.pack(fill=tk.X, pady=6)

        add_hl_btn = ttk.Button(
            l_btn_box,
            text="+ Add Home / Top-Up Loan",
            style="ActionSmall.TButton",
            command=lambda: self._add_loan_card("Home Loan Top-Up")
        )
        add_hl_btn.pack(side=tk.LEFT, padx=(0, 6))

        add_other_loan_btn = ttk.Button(
            l_btn_box,
            text="+ Add Other Loan / EMI",
            style="ActionSmall.TButton",
            command=lambda: self._add_loan_card("Vehicle / Car Loan")
        )
        add_other_loan_btn.pack(side=tk.LEFT)

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=6)
        self.entry_house_rent = self._create_input_field(
            frame, "Residential Rent (if paying rent)", "Monthly rent for accommodation (if living in rented home)", accent_color=self.neon_amber
        )

    def _add_loan_card(self, default_cat: str):
        card = tk.Frame(self.loans_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=8, pady=6)
        card.pack(fill=tk.X, pady=3)

        # Top Row: Category + Description + Delete
        r1 = tk.Frame(card, bg=self.inner_box_bg)
        r1.pack(fill=tk.X, pady=(0, 4))

        cat_cb = ttk.Combobox(
            r1,
            values=[
                "Primary Home Loan",
                "Home Loan Top-Up",
                "2nd Home / Plot Loan",
                "Home Renovation Loan",
                "Vehicle / Car Loan",
                "Personal Loan",
                "Education Loan",
                "Other EMI / Liability"
            ],
            width=18,
            font=("Helvetica", 9, "bold"),
            state="readonly"
        )
        cat_cb.set(default_cat)
        cat_cb.pack(side=tk.LEFT)

        desc_entry = self._create_text_entry(r1)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        row_item = {
            "card": card,
            "cat": cat_cb,
            "desc": desc_entry,
        }

        def _remove_loan():
            if len(self.loan_rows) > 1:
                card.destroy()
                self.loan_rows.remove(row_item)

        del_btn = tk.Button(
            r1, text="✕", font=("Helvetica", 8, "bold"), fg=self.neon_rose, bg=self.inner_box_bg,
            activebackground=self.inner_box_bg, activeforeground="#ffffff", relief="flat", cursor="hand2", command=_remove_loan
        )
        del_btn.pack(side=tk.RIGHT)

        # Bottom Row: Total Loan Amount, Interest Rate, Start Date, Monthly EMI
        r2 = tk.Frame(card, bg=self.inner_box_bg)
        r2.pack(fill=tk.X)

        # Total Loan Amount
        b1 = tk.Frame(r2, bg=self.inner_box_bg)
        b1.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(b1, text="Total Loan Principal", font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")
        amt_entry = self._create_text_entry(b1, width=12)
        amt_entry.pack()

        # Interest Rate %
        b2 = tk.Frame(r2, bg=self.inner_box_bg)
        b2.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(b2, text="Rate % p.a.", font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")
        rate_entry = self._create_text_entry(b2, width=8)
        rate_entry.pack()

        # Start Date (YYYY-MM)
        b3 = tk.Frame(r2, bg=self.inner_box_bg)
        b3.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(b3, text="Start (YYYY-MM)", font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")
        date_entry = self._create_text_entry(b3, width=11)
        date_entry.pack()

        # Monthly EMI
        b4 = tk.Frame(r2, bg=self.inner_box_bg)
        b4.pack(side=tk.LEFT)
        tk.Label(b4, text="Monthly EMI", font=("Helvetica", 7, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg).pack(anchor="w")
        emi_entry = self._create_text_entry(b4, width=11)
        emi_entry.pack()

        row_item.update({
            "total_amt": amt_entry,
            "rate": rate_entry,
            "start_date": date_entry,
            "emi": emi_entry
        })
        self.loan_rows.append(row_item)

    # ---------------- TAB 2: CREDIT CARDS (LIMITS, EMIs & THUMBNAILS) ----------------
    def _build_tab_credit_cards(self, parent):
        frame = self._create_scroll_wrapper(parent)

        tk.Label(frame, text="CREDIT CARDS: LIMITS & ACTIVE EMIs", font=("Helvetica", 11, "bold"), fg=self.neon_rose, bg=self.card_bg).pack(anchor="w")
        tk.Label(
            frame,
            text="Type any card name to render live vector thumbnail. Specify credit limit & EMI start/end dates.",
            font=("Helvetica", 8),
            fg=self.text_muted,
            bg=self.card_bg
        ).pack(anchor="w", pady=(1, 6))

        self.cards_container = tk.Frame(frame, bg=self.card_bg)
        self.cards_container.pack(fill=tk.X, pady=2)

        # Start with 2 empty cards, NO DEFAULTS
        self._add_card_card()
        self._add_card_card()

        btn_row = tk.Frame(frame, bg=self.card_bg)
        btn_row.pack(fill=tk.X, pady=8)

        add_card_btn = ttk.Button(
            btn_row,
            text="+ Add Another Credit Card",
            style="ActionSmall.TButton",
            command=self._add_card_card
        )
        add_card_btn.pack(side=tk.LEFT)

    def _add_card_card(self):
        card = tk.Frame(self.cards_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=8, pady=6)
        card.pack(fill=tk.X, pady=3)

        # Row 1: Live Thumbnail + Name + Limit + Bill + Delete
        r1 = tk.Frame(card, bg=self.inner_box_bg)
        r1.pack(fill=tk.X, pady=(0, 4))

        thumb_canvas = tk.Canvas(r1, width=64, height=40, bg=self.inner_box_bg, highlightthickness=0)
        thumb_canvas.pack(side=tk.LEFT, padx=(0, 6))
        draw_card_thumbnail(thumb_canvas, detect_card_brand(""))

        name_box = tk.Frame(r1, bg=self.inner_box_bg)
        name_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        top_n = tk.Frame(name_box, bg=self.inner_box_bg)
        top_n.pack(fill=tk.X)
        tk.Label(top_n, text="Card Name / Bank", font=("Helvetica", 8, "bold"), fg=self.text_dark, bg=self.inner_box_bg).pack(side=tk.LEFT)
        badge_lbl = tk.Label(top_n, text="Awaiting input", font=("Helvetica", 7), fg=self.text_muted, bg=self.inner_box_bg)
        badge_lbl.pack(side=tk.RIGHT)

        name_entry = self._create_text_entry(name_box)
        name_entry.pack(fill=tk.X, ipady=2)

        # Credit Limit
        lim_box = tk.Frame(r1, bg=self.inner_box_bg)
        lim_box.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(lim_box, text="Credit Limit", font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")
        lim_entry = self._create_text_entry(lim_box, width=10)
        lim_entry.pack(ipady=2)

        # Monthly Bill
        bill_box = tk.Frame(r1, bg=self.inner_box_bg)
        bill_box.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(bill_box, text="Monthly Bill", font=("Helvetica", 7, "bold"), fg=self.neon_rose, bg=self.inner_box_bg).pack(anchor="w")
        bill_entry = self._create_text_entry(bill_box, width=10)
        bill_entry.pack(ipady=2)

        row_item = {
            "card": card,
            "canvas": thumb_canvas,
            "name": name_entry,
            "limit": lim_entry,
            "bill": bill_entry,
            "badge": badge_lbl
        }

        def _remove_card():
            if len(self.card_rows) > 1:
                card.destroy()
                self.card_rows.remove(row_item)

        del_btn = tk.Button(
            r1, text="✕", font=("Helvetica", 8, "bold"), fg=self.neon_rose, bg=self.inner_box_bg,
            activebackground=self.inner_box_bg, activeforeground="#ffffff", relief="flat", cursor="hand2", command=_remove_card
        )
        del_btn.pack(side=tk.RIGHT)

        # Row 2: Consistency / EMI Breakdown
        r2 = tk.Frame(card, bg=self.inner_box_bg)
        r2.pack(fill=tk.X, pady=(2, 0))

        type_cb = ttk.Combobox(
            r2,
            values=[
                "Consistent Regular Spends",
                "Includes Active Card EMIs"
            ],
            width=21,
            font=("Helvetica", 8, "bold"),
            state="readonly"
        )
        type_cb.set("Consistent Regular Spends")
        type_cb.pack(side=tk.LEFT, padx=(0, 4))

        # EMI amount
        emi_box = tk.Frame(r2, bg=self.inner_box_bg)
        emi_box.pack(side=tk.LEFT, padx=(0, 3))
        tk.Label(emi_box, text="EMI Part", font=("Helvetica", 7), fg=self.text_muted, bg=self.inner_box_bg).pack(side=tk.LEFT)
        emi_amt_entry = self._create_text_entry(emi_box, width=8)
        emi_amt_entry.pack(side=tk.LEFT, padx=2)

        # EMI Start Date
        sdate_box = tk.Frame(r2, bg=self.inner_box_bg)
        sdate_box.pack(side=tk.LEFT, padx=(0, 3))
        tk.Label(sdate_box, text="Start", font=("Helvetica", 7), fg=self.text_muted, bg=self.inner_box_bg).pack(side=tk.LEFT)
        sdate_entry = self._create_text_entry(sdate_box, width=8)
        sdate_entry.pack(side=tk.LEFT, padx=2)

        # EMI End Date
        edate_box = tk.Frame(r2, bg=self.inner_box_bg)
        edate_box.pack(side=tk.LEFT)
        tk.Label(edate_box, text="End", font=("Helvetica", 7), fg=self.text_muted, bg=self.inner_box_bg).pack(side=tk.LEFT)
        edate_entry = self._create_text_entry(edate_box, width=8)
        edate_entry.pack(side=tk.LEFT, padx=2)

        row_item.update({
            "type_cb": type_cb,
            "emi_amt": emi_amt_entry,
            "start_date": sdate_entry,
            "end_date": edate_entry
        })

        # Dynamic thumbnail keyrelease event
        def _on_name_change(e):
            txt = name_entry.get().strip()
            info = detect_card_brand(txt)
            draw_card_thumbnail(thumb_canvas, info)
            if info["brand"] == "EMPTY":
                badge_lbl.config(text="Awaiting input", fg=self.text_muted)
            else:
                badge_lbl.config(text=f"Detected: {info['title']}", fg=self.neon_cyan)

        name_entry.bind("<KeyRelease>", _on_name_change)
        self.card_rows.append(row_item)

    # ---------------- TAB 3: SAVINGS, INVESTMENTS & TERM INSURANCE ----------------
    def _build_tab_savings_investments(self, parent):
        frame = self._create_scroll_wrapper(parent)

        tk.Label(frame, text="COMMITTED SAVINGS & INVESTMENTS", font=("Helvetica", 11, "bold"), fg=self.neon_purple, bg=self.card_bg).pack(anchor="w")
        tk.Label(
            frame,
            text="Enter systematic contributions across EPF, NPS, ULIPs, SIPs, and FDs.\n"
                 "Investment start date calculates your saving velocity and accumulated corpus.",
            font=("Helvetica", 8),
            fg=self.text_muted,
            bg=self.card_bg,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(1, 6))

        # EPF
        self.entry_inv_epf = self._create_input_field(
            frame, "EPF Monthly Deposit (Employee Provident Fund)",
            "Mandatory monthly EPF retirement deduction (both employee & employer portion)", accent_color=self.neon_purple
        )
        # NPS
        self.entry_inv_nps = self._create_input_field(
            frame, "NPS Monthly Contribution (National Pension System)",
            "Tier-1 / Tier-2 pension annuity investment contributions", accent_color=self.neon_purple
        )
        # ULIP / Insurance
        self.entry_inv_ulip = self._create_input_field(
            frame, "ULIP / Investment-Linked Insurance",
            "Monthly/annual premium amortized towards ULIPs or endowment investment plans", accent_color=self.neon_purple
        )
        # SIP
        self.entry_inv_sip = self._create_input_field(
            frame, "Mutual Fund / Equity SIPs",
            "Systematic monthly investment plans into index funds, mutual funds, or equities", accent_color=self.neon_cyan
        )
        # FD / RD
        self.entry_inv_fd = self._create_input_field(
            frame, "Fixed Deposits (FD) / Recurring Deposits (RD)",
            "Regular allocations into bank fixed deposits or recurring deposits", accent_color=self.neon_purple
        )
        # PPF / Gold / Other
        self.entry_inv_other = self._create_input_field(
            frame, "Other Investments (PPF, SGB Gold, Real Estate SIP)",
            "Public Provident Fund, Sovereign Gold Bonds, or other structured savings", accent_color=self.neon_purple
        )

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=8)

        # ---------------- TERM INSURANCE SECTION ----------------
        tk.Label(frame, text="☂️ TERM INSURANCE & LIFE RISK PROTECTION", font=("Helvetica", 11, "bold"), fg=self.primary_blue, bg=self.card_bg).pack(anchor="w")
        tk.Label(
            frame,
            text="Pure risk term life protection ensuring debt clearance & family income replacement.\n"
                 "Recommended minimum sum assured is 10x - 15x annual income plus outstanding liabilities.",
            font=("Helvetica", 8),
            fg=self.text_muted,
            bg=self.card_bg,
            justify=tk.LEFT
        ).pack(anchor="w", pady=(1, 4))

        self.entry_term_premium = self._create_input_field(
            frame, "Term Insurance Premium (Monthly Equivalent)",
            "Monthly premium (or annual premium ÷ 12) for pure term life policies", accent_color=self.primary_blue
        )
        self.entry_term_sum_assured = self._create_input_field(
            frame, "Total Term Sum Assured / Life Cover",
            "Total death benefit across active term plans (e.g. 10000000 for 1 Cr, 20000000 for 2 Cr)", accent_color=self.neon_cyan
        )
        self.entry_term_tenure = self._create_input_field(
            frame, "Covered Till Age / Maturity Year",
            "e.g. Till Age 65 or Year 2055 (Optimal retirement age coverage)", accent_color=self.neon_amber
        )
        self.entry_term_nominee = self._create_input_field(
            frame, "Insured Person(s) / Policy Name",
            "e.g. HDFC Life Click 2 Protect (Self) / ICICI Pru iProtect (Both)", accent_color=self.text_muted
        )

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=8)

        # Investment Start Date
        tk.Label(frame, text="INVESTMENT START DATE & DISCIPLINE", font=("Helvetica", 10, "bold"), fg=self.neon_green, bg=self.card_bg).pack(anchor="w")
        self.entry_inv_start_date = self._create_input_field(
            frame, "When did you start regular investing? (YYYY-MM)",
            "e.g., 2021-04 or Jan 2022. Used to calculate consistency momentum & accumulated corpus.", accent_color=self.neon_green
        )

    # ---------------- TAB 4: UTILITIES & LIVING EXPENSES ----------------
    def _build_tab_utilities_needs(self, parent):
        frame = self._create_scroll_wrapper(parent)

        tk.Label(frame, text="UTILITY BILL BREAKDOWN", font=("Helvetica", 11, "bold"), fg=self.neon_cyan, bg=self.card_bg).pack(anchor="w")
        self.entry_util_elec = self._create_input_field(frame, "Electricity Bill", "Monthly home power & air conditioning charges")
        self.entry_util_water_gas = self._create_input_field(frame, "Water & Cooking Gas / LPG", "Piped natural gas, LPG cylinders, water supply maintenance")
        self.entry_util_internet = self._create_input_field(frame, "Broadband & Wi-Fi", "High-speed home fiber / internet bills")
        self.entry_util_mobile = self._create_input_field(frame, "Mobile Recharges & DTH", "Family phone connections & streaming TV")

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=6)

        tk.Label(frame, text="ESSENTIAL LIVING NEEDS & REQUIREMENTS", font=("Helvetica", 11, "bold"), fg=self.neon_green, bg=self.card_bg).pack(anchor="w")
        self.entry_need_groceries = self._create_input_field(frame, "Groceries & Household Supplies", "Supermarket food purchases, dairy, vegetables, household essentials")
        self.entry_need_healthcare = self._create_input_field(frame, "Healthcare & Medical Outflows", "Medicines, doctor fees, medical tests, health supplies")
        self.entry_need_commute = self._create_input_field(frame, "Fuel, Commute & Transport", "Petrol/diesel, metro, bus, cab fares, vehicle parking")
        self.entry_need_education = self._create_input_field(frame, "Education, Childcare & Dependents", "School/tuition fees, daycare, support for senior dependents")

        tk.Frame(frame, bg=self.border_color, height=1).pack(fill=tk.X, pady=6)

        tk.Label(frame, text="DISCRETIONARY LIFESTYLE OUTFLOWS (WANTS)", font=("Helvetica", 11, "bold"), fg="#ec4899", bg=self.card_bg).pack(anchor="w")
        self.entry_want_dining = self._create_input_field(frame, "Dining Out & Food Deliveries", "Restaurants, cafes, weekend takeout, food apps")
        self.entry_want_leisure = self._create_input_field(frame, "Entertainment, OTT & Shopping", "Movies, Netflix/Prime, apparel, gadgets, hobbies")

    # ---------------- RIGHT COLUMN: DASHBOARD PANE ----------------
    def _build_dashboard_pane(self, parent):
        card = tk.Frame(parent, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1, padx=12, pady=10)
        card.pack(fill=tk.BOTH, expand=True)

        # Top Bar
        top_bar = tk.Frame(card, bg=self.card_bg)
        top_bar.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top_bar, text="FINANCIAL DIAGNOSTICS & INTELLIGENCE", font=("Helvetica", 12, "bold"), fg=self.neon_cyan, bg=self.card_bg).pack(side=tk.LEFT)
        self.btn_export = ttk.Button(top_bar, text="💾 Export Report", style="ActionSmall.TButton", command=self.export_report)
        self.btn_export.pack(side=tk.RIGHT)

        # Overall Health Score Banner
        self.health_score_box = tk.Frame(card, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=6)
        self.health_score_box.pack(fill=tk.X, pady=(0, 6))

        self.lbl_score_grade = tk.Label(
            self.health_score_box, text="READY FOR ANALYSIS", font=("Helvetica", 10, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg
        )
        self.lbl_score_grade.pack(side=tk.LEFT)

        self.lbl_score_summary = tk.Label(
            self.health_score_box, text="Enter figures on the left and click 'Calculate Flow'.",
            font=("Helvetica", 8), fg=self.text_muted, bg=self.inner_box_bg
        )
        self.lbl_score_summary.pack(side=tk.RIGHT)

        # Primary KPI Tiles (Inflow, Outflow, Net Savings, DTI)
        kpi_row = tk.Frame(card, bg=self.card_bg)
        kpi_row.pack(fill=tk.X, pady=(0, 4))

        self.kpi_inflow = self._create_kpi_tile(kpi_row, "Combined Inflow", "--", self.neon_green, 0)
        self.kpi_outflow = self._create_kpi_tile(kpi_row, "Total Outflow", "--", self.neon_rose, 1)
        self.kpi_savings = self._create_kpi_tile(kpi_row, "Net Monthly Surplus", "--", self.neon_cyan, 2)
        self.kpi_dti = self._create_kpi_tile(kpi_row, "Total DTI Ratio", "--", self.neon_amber, 3)

        # Secondary KPI Row: Committed Investments, Total Saving Ratio, Home Loan & Top-Up Burden
        ratio_stat_row = tk.Frame(card, bg=self.card_bg)
        ratio_stat_row.pack(fill=tk.X, pady=(0, 4))

        self.lbl_spend_save = tk.Label(
            ratio_stat_row,
            text="Committed Invest: --  |  Total Saving Ratio: --%",
            font=("Helvetica", 8, "bold"),
            fg=self.text_dark,
            bg=self.card_bg
        )
        self.lbl_spend_save.pack(side=tk.LEFT)

        self.lbl_hl_burden = tk.Label(
            ratio_stat_row,
            text="Mortgage & Top-Up Burden: --%",
            font=("Helvetica", 8, "bold"),
            fg=self.text_muted,
            bg=self.card_bg
        )
        self.lbl_hl_burden.pack(side=tk.RIGHT)

        # Visual Cash Flow Bar
        tk.Label(card, text="Cash Flow Distribution:", font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.card_bg).pack(anchor="w")
        self.flow_canvas = tk.Canvas(card, height=14, bg="#161622", highlightthickness=0)
        self.flow_canvas.pack(fill=tk.X, pady=(0, 6))

        # Dashboard Tabs
        self.out_notebook = ttk.Notebook(card)
        self.out_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab A: 🎯 Action Roadmap
        tab_actions = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_actions, text="🎯 Action Roadmap")
        self._build_action_roadmap_view(tab_actions)

        # Tab B: 🏠 Loan Amortization & Payoff Tracker
        tab_amort = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_amort, text="🏠 Loan Amortization")
        self._build_amortization_view(tab_amort)

        # Tab C: 💳 Credit Card Utilization & Freedom Calendar
        tab_cc_intel = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_cc_intel, text="💳 Card Limits & EMIs")
        self._build_cc_intel_view(tab_cc_intel)

        # Tab D: 💰 Savings Portfolio & Consistency
        tab_savings_intel = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_savings_intel, text="💰 Wealth & Protection")
        self._build_savings_intel_view(tab_savings_intel)

        # Tab E: 🔮 What-If Simulator
        tab_sim = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_sim, text="🔮 What-If Sim")
        self._build_simulator_view(tab_sim)

        # Tab F: 📄 Full Report Text
        tab_text = tk.Frame(self.out_notebook, bg=self.card_bg)
        self.out_notebook.add(tab_text, text="📄 Full Report")
        self._build_full_report_view(tab_text)

    def _create_kpi_tile(self, parent, label: str, val: str, color: str, col: int) -> tk.Label:
        box = tk.Frame(parent, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=6, pady=4)
        box.grid(row=0, column=col, sticky="nsew", padx=2)
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(box, text=label, font=("Helvetica", 7, "bold"), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")
        v = tk.Label(box, text=val, font=("Helvetica", 11, "bold"), fg=color, bg=self.inner_box_bg)
        v.pack(anchor="w", pady=(1, 0))
        return v

    # --- TAB A: ACTION ROADMAP ---
    def _build_action_roadmap_view(self, parent):
        scrollable = self._create_scroll_wrapper(parent)
        self.roadmap_container = scrollable
        tk.Label(
            self.roadmap_container,
            text="Your strategic roadmap will appear here upon calculation, detailing:\n"
                 "• Credit Card High-APR Avalanche\n"
                 "• Top-Up and Home Loan Principal Payoff Velocity\n"
                 "• Emergency Survival Runway Milestones\n"
                 "• EPF/NPS/SIP Long-Term Compounding Engines\n"
                 "• Term Insurance & Pure Life Risk Shields",
            font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg, justify=tk.LEFT
        ).pack(anchor="w", pady=8)

    # --- TAB B: LOAN AMORTIZATION & PAYOFF VIEW ---
    def _build_amortization_view(self, parent):
        scrollable = self._create_scroll_wrapper(parent)
        self.amort_container = scrollable
        tk.Label(
            self.amort_container,
            text="Loan amortization diagnostics (Completed % vs Leftover Principal) will display here.",
            font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg
        ).pack(anchor="w", pady=8)

    # --- TAB C: CC UTILIZATION & EMI FREEDOM CALENDAR ---
    def _build_cc_intel_view(self, parent):
        scrollable = self._create_scroll_wrapper(parent)
        self.cc_intel_container = scrollable
        tk.Label(
            self.cc_intel_container,
            text="Credit card utilization gauges and active EMI payoff freedom dates will display here.",
            font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg
        ).pack(anchor="w", pady=8)

    # --- TAB D: SAVINGS PORTFOLIO & RATIOS ---
    def _build_savings_intel_view(self, parent):
        scrollable = self._create_scroll_wrapper(parent)
        self.savings_intel_container = scrollable
        tk.Label(
            self.savings_intel_container,
            text="EPF, NPS, ULIP, SIP, FD allocations, and Term Life Insurance sufficiency will display here.",
            font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg
        ).pack(anchor="w", pady=8)

    # --- TAB E: WHAT-IF SIMULATOR ---
    def _build_simulator_view(self, parent):
        container = tk.Frame(parent, bg=self.card_bg, padx=10, pady=8)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="INTERACTIVE 'WHAT-IF' CASH FLOW OPTIMIZER", font=("Helvetica", 10, "bold"), fg=self.neon_cyan, bg=self.card_bg).pack(anchor="w")
        tk.Label(container, text="Simulate how trimming discretionary spendings accelerates your Top-Up Loan payoff and wealth compounding.", font=("Helvetica", 8), fg=self.text_muted, bg=self.card_bg).pack(anchor="w", pady=(1, 6))

        s_box = tk.Frame(container, bg=self.card_bg)
        s_box.pack(fill=tk.X, pady=4)

        self.sim_slider_lbl = tk.Label(s_box, text="Discretionary Spending Trim: 0%", font=("Helvetica", 8, "bold"), fg=self.neon_amber, bg=self.card_bg)
        self.sim_slider_lbl.pack(anchor="w")

        self.sim_wants_slider = tk.Scale(
            s_box, from_=0, to=50, orient=tk.HORIZONTAL, bg=self.inner_box_bg, fg=self.neon_cyan,
            troughcolor="#09090d", activebackground=self.neon_cyan, highlightthickness=0, command=self._on_slider_change
        )
        self.sim_wants_slider.pack(fill=tk.X, pady=2)

        self.sim_result_card = tk.Frame(container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=10)
        self.sim_result_card.pack(fill=tk.BOTH, expand=True, pady=6)

        self.sim_result_txt = tk.Label(self.sim_result_card, text="Calculate flow first to unlock the interactive simulator.", font=("Helvetica", 8), fg=self.text_muted, bg=self.inner_box_bg, justify=tk.LEFT)
        self.sim_result_txt.pack(anchor="w")

    def _on_slider_change(self, val):
        pct = float(val)
        self.sim_slider_lbl.config(text=f"Discretionary Spending Trim: {pct:.0f}%")
        if not self.last_calc_data:
            return

        cur = self.currency_var.get()
        wants = self.last_calc_data["total_wants"]
        monthly_freed = wants * (pct / 100.0)
        new_surplus = self.last_calc_data["net_savings"] + monthly_freed
        savings_5yr = new_surplus * 12 * 5
        compounded_5yr = 0
        monthly_r = 0.10 / 12.0
        for _ in range(60):
            compounded_5yr = (compounded_5yr + new_surplus) * (1 + monthly_r)

        txt = (
            f"💡 Simulation Insights ({pct:.0f}% Discretionary Trim):\n\n"
            f"• Monthly Cash Flow Freed: +{cur}{monthly_freed:,.2f}/month\n"
            f"• New Monthly Surplus: {cur}{new_surplus:,.2f}/month\n"
            f"• 5-Year Cumulative Principal Saved: {cur}{savings_5yr:,.2f}\n"
            f"• 5-Year Compounded Wealth (at 10% SIP index return): {cur}{compounded_5yr:,.2f}\n\n"
            f"Strategic Impact:\n"
            f"Channeling {cur}{monthly_freed:,.2f}/mo directly into your Home Loan Top-Up principal eliminates high-interest amortization years in advance!"
        )
        self.sim_result_txt.config(text=txt, fg=self.text_dark)

    # --- TAB F: FULL REPORT VIEW ---
    def _build_full_report_view(self, parent):
        txt_frame = tk.Frame(parent, bg=self.card_bg)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(txt_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.full_report_text = tk.Text(
            txt_frame, wrap=tk.WORD, font=("Courier", 9), bg=self.entry_bg, fg=self.neon_green,
            insertbackground=self.entry_cursor, relief="flat", padx=10, pady=10, yscrollcommand=scrollbar.set
        )
        self.full_report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.full_report_text.yview)

    # ---------------- COMPUTATION ENGINE ----------------
    def _parse_val(self, entry: tk.Entry, field_name: str, required: bool = False) -> float:
        text = entry.get().strip()
        if not text:
            if required:
                raise ValueError(f"'{field_name}' is required. Please enter an amount (or 0 if none).")
            return 0.0

        cleaned = text.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")
        try:
            val = float(cleaned)
        except ValueError:
            raise ValueError(f"Invalid numeric value in '{field_name}'. Please enter digits.")
        if val < 0:
            raise ValueError(f"'{field_name}' cannot be negative.")
        return val

    def calculate(self):
        cur = self.currency_var.get()

        try:
            # 1. Incomes
            his_inc = self._parse_val(self.entry_his_income, "Your Monthly Income", required=True)
            wife_inc = self._parse_val(self.entry_wife_income, "Wife's Monthly Income", required=True)
            other_inc = self._parse_val(self.entry_other_income, "Additional Household Inflows")
            total_income = his_inc + wife_inc + other_inc

            if total_income <= 0:
                messagebox.showwarning("Inflow Required", "Combined household income must be greater than zero.")
                return

            # 2. Loans & Amortization
            home_loans_total = 0.0
            topup_loans_total = 0.0
            other_loans_total = 0.0
            itemized_loans = []

            for idx, r in enumerate(self.loan_rows, start=1):
                cat = r["cat"].get().strip()
                desc = r["desc"].get().strip()
                emi_str = r["emi"].get().strip()
                amt_str = r["total_amt"].get().strip()
                rate_str = r["rate"].get().strip()
                date_str = r["start_date"].get().strip()

                if not emi_str and not desc and not amt_str:
                    continue

                emi_val = float(emi_str.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")) if emi_str else 0.0
                total_loan_amt = float(amt_str.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")) if amt_str else 0.0
                rate_val = float(rate_str.replace("%", "").replace(",", "")) if rate_str else 0.0

                label = f"{cat} ({desc})" if desc else cat

                # Amortization calculation
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
            rent_val = self._parse_val(self.entry_house_rent, "House Rent")
            total_loans_liabilities = total_mortgages_and_topups + other_loans_total + rent_val

            # 3. Credit Cards with Limits & EMIs
            itemized_cards = []
            total_cc_bills = 0.0
            total_cc_limits = 0.0
            total_cc_emis = 0.0

            for idx, r in enumerate(self.card_rows, start=1):
                name = r["name"].get().strip()
                lim_str = r["limit"].get().strip()
                bill_str = r["bill"].get().strip()
                btype = r["type_cb"].get().strip()
                emi_str = r["emi_amt"].get().strip()
                sdate = r["start_date"].get().strip()
                edate = r["end_date"].get().strip()

                if not name and not bill_str and not lim_str:
                    continue

                bill_val = float(bill_str.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")) if bill_str else 0.0
                lim_val = float(lim_str.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")) if lim_str else 0.0
                emi_val = float(emi_str.replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")) if emi_str else 0.0

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

            # 4. Savings & Investments (EPF, NPS, ULIP, SIP, FD) + Term Insurance
            epf = self._parse_val(self.entry_inv_epf, "EPF Monthly Deposit")
            nps = self._parse_val(self.entry_inv_nps, "NPS Monthly Contribution")
            ulip = self._parse_val(self.entry_inv_ulip, "ULIP / Insurance Investment")
            sip = self._parse_val(self.entry_inv_sip, "Mutual Fund / Equity SIPs")
            fd = self._parse_val(self.entry_inv_fd, "Fixed Deposits / RD")
            inv_other = self._parse_val(self.entry_inv_other, "Other Investments")
            inv_start_str = self.entry_inv_start_date.get().strip()

            # Dedicated Term Insurance Outflow & Cover Analysis
            term_premium = self._parse_val(self.entry_term_premium, "Term Insurance Premium")
            term_sum_assured = self._parse_val(self.entry_term_sum_assured, "Term Sum Assured")
            term_tenure_str = self.entry_term_tenure.get().strip()
            term_policy_name = self.entry_term_nominee.get().strip()

            total_committed_investments = epf + nps + ulip + sip + fd + inv_other + term_premium

            annual_income = total_income * 12
            recommended_cover = max(annual_income * 12, annual_income * 10 + total_mortgages_and_topups * 12)
            cover_multiple = (term_sum_assured / annual_income) if annual_income > 0 else 0.0

            inv_dt = parse_month_year(inv_start_str)
            now = datetime.now()
            invest_months_elapsed = max(0, (now.year - inv_dt.year) * 12 + (now.month - inv_dt.month)) if inv_dt else 0

            # 5. Utilities
            elec = self._parse_val(self.entry_util_elec, "Electricity Bill")
            water_gas = self._parse_val(self.entry_util_water_gas, "Water & Cooking Gas")
            internet = self._parse_val(self.entry_util_internet, "Broadband & Wi-Fi")
            mobile = self._parse_val(self.entry_util_mobile, "Mobile & DTH")
            total_utilities = elec + water_gas + internet + mobile

            # 6. Essential Needs
            groceries = self._parse_val(self.entry_need_groceries, "Groceries & Supplies")
            healthcare = self._parse_val(self.entry_need_healthcare, "Healthcare & Medical")
            commute = self._parse_val(self.entry_need_commute, "Fuel & Commute")
            education = self._parse_val(self.entry_need_education, "Education & Childcare")
            total_needs = groceries + healthcare + commute + education

            # 7. Discretionary Wants
            dining = self._parse_val(self.entry_want_dining, "Dining Out")
            leisure = self._parse_val(self.entry_want_leisure, "Entertainment & Shopping")
            total_wants = dining + leisure

        except ValueError as err:
            messagebox.showwarning("Validation Error", str(err))
            return

        # Overall Totals & Ratios
        total_outflow = total_loans_liabilities + total_cc_bills + total_committed_investments + total_utilities + total_needs + total_wants
        net_disposable_surplus = total_income - total_outflow

        spending_ratio = ((total_outflow - total_committed_investments) / total_income) * 100.0
        committed_saving_ratio = (total_committed_investments / total_income) * 100.0
        total_combined_saving_ratio = ((total_committed_investments + max(net_disposable_surplus, 0.0)) / total_income) * 100.0

        total_debt_payments = total_mortgages_and_topups + other_loans_total + total_cc_bills
        dti_ratio = (total_debt_payments / total_income) * 100.0
        hl_burden_ratio = (total_mortgages_and_topups / total_income) * 100.0

        total_mandatory_survival = total_mortgages_and_topups + rent_val + total_utilities + total_needs

        # Cache for simulator
        self.last_calc_data = {
            "total_income": total_income,
            "total_outflow": total_outflow,
            "net_savings": net_disposable_surplus,
            "total_wants": total_wants,
            "cur": cur
        }

        # Update KPI Banner
        self.kpi_inflow.config(text=f"{cur}{total_income:,.2f}")
        self.kpi_outflow.config(text=f"{cur}{total_outflow:,.2f}")

        if net_disposable_surplus >= 0:
            self.kpi_savings.config(text=f"{cur}{net_disposable_surplus:,.2f}", fg=self.neon_green)
        else:
            self.kpi_savings.config(text=f"-{cur}{abs(net_disposable_surplus):,.2f}", fg=self.neon_rose)

        # DTI color
        if dti_ratio <= 35.0:
            self.kpi_dti.config(text=f"{dti_ratio:.1f}%", fg=self.neon_green)
        elif dti_ratio <= 45.0:
            self.kpi_dti.config(text=f"{dti_ratio:.1f}%", fg=self.neon_amber)
        else:
            self.kpi_dti.config(text=f"{dti_ratio:.1f}%", fg=self.neon_rose)

        self.lbl_spend_save.config(
            text=f"Committed Invest: {cur}{total_committed_investments:,.2f} ({committed_saving_ratio:.1f}%)  |  Total Saving Ratio: {total_combined_saving_ratio:.1f}%",
            fg=self.neon_cyan
        )
        self.lbl_hl_burden.config(
            text=f"Mortgage & Top-Up Burden: {hl_burden_ratio:.1f}% of income (Safe: < 28%)",
            fg=self.neon_amber if hl_burden_ratio > 28 else self.text_muted
        )

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
            health_score -= 5  # Unhedged family risk penalty

        health_score = max(min(health_score, 100), 10)

        if health_score >= 80:
            self.lbl_score_grade.config(text=f"GRADE A  ({health_score}/100) - SOLID CASH FLOW", fg=self.neon_green)
            self.lbl_score_summary.config(text="Excellent wealth velocity & disciplined investments. High compounding leverage.")
        elif health_score >= 60:
            self.lbl_score_grade.config(text=f"GRADE B  ({health_score}/100) - STABLE MARGIN", fg=self.neon_cyan)
            self.lbl_score_summary.config(text="Consistent savings. Prioritize paying off top-ups and keeping card utilization under 30%.")
        elif health_score >= 40:
            self.lbl_score_grade.config(text=f"GRADE C  ({health_score}/100) - VULNERABLE LEVERAGE", fg=self.neon_amber)
            self.lbl_score_summary.config(text="Elevated debt or high CC EMIs. Any sudden income shock could trigger deficit.")
        else:
            self.lbl_score_grade.config(text=f"GRADE D  ({health_score}/100) - CRITICAL DEFICIT / DEBT", fg=self.neon_rose)
            self.lbl_score_summary.config(text="Outflows exceed income. Freeze credit cards and non-essential spending immediately.")

        # Cash Flow Bar
        self._render_canvas_bar(self.flow_canvas, total_income, [
            ("Loans", total_mortgages_and_topups, "#6366f1"),
            ("Cards", total_cc_bills, "#f43f5e"),
            ("Investments", total_committed_investments, "#00f59b"),
            ("Utilities", total_utilities, "#00f2fe"),
            ("Needs", total_needs, "#fbbf24"),
            ("Wants", total_wants, "#ec4899"),
            ("Surplus", max(net_disposable_surplus, 0), "#10b981")
        ])

        # Render Dashboard Views
        self._render_roadmap_tab(
            cur, total_income, net_disposable_surplus, total_combined_saving_ratio,
            itemized_cards, total_cc_bills, total_cc_emis,
            itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
            total_committed_investments, total_mandatory_survival,
            term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
        )

        self._render_amortization_tab(cur, itemized_loans)
        self._render_cc_intel_tab(cur, itemized_cards, total_cc_limits, total_cc_bills, overall_cc_util)
        self._render_savings_intel_tab(
            cur, total_income, epf, nps, ulip, sip, fd, inv_other,
            total_committed_investments, committed_saving_ratio, total_combined_saving_ratio,
            invest_months_elapsed, inv_start_str, net_disposable_surplus,
            term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
        )

        self._on_slider_change(self.sim_wants_slider.get())

        # Full Report Text Generation
        self._generate_full_report_text(
            cur, total_income, his_inc, wife_inc, other_inc,
            itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
            itemized_cards, total_cc_bills, total_cc_limits, overall_cc_util, total_cc_emis,
            epf, nps, ulip, sip, fd, inv_other, total_committed_investments,
            invest_months_elapsed, committed_saving_ratio, total_combined_saving_ratio,
            total_utilities, total_needs, total_wants,
            total_outflow, net_disposable_surplus, dti_ratio, health_score,
            term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
        )

    def _render_canvas_bar(self, canvas: tk.Canvas, scale_total: float, segments: list):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return

        total_alloc = sum(s[1] for s in segments)
        base = max(total_alloc, scale_total, 1.0)

        cx = 0
        for name, amt, col in segments:
            if amt <= 0:
                continue
            seg_w = int((amt / base) * w)
            if seg_w <= 0:
                continue
            canvas.create_rectangle(cx, 0, cx + seg_w, h, fill=col, outline="")
            if seg_w > 48:
                canvas.create_text(cx + seg_w // 2, h // 2, text=name, fill="#ffffff", font=("Helvetica", 6, "bold"))
            cx += seg_w

    def _create_action_card(self, parent, icon: str, title: str, tag: str, tag_col: str, bullets: list):
        card = tk.Frame(parent, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=8)
        card.pack(fill=tk.X, pady=3)

        top_r = tk.Frame(card, bg=self.inner_box_bg)
        top_r.pack(fill=tk.X)

        tk.Label(top_r, text=f"{icon} {title}", font=("Helvetica", 9, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg).pack(side=tk.LEFT)
        badge = tk.Label(top_r, text=f" {tag} ", font=("Helvetica", 7, "bold"), fg="#ffffff", bg=tag_col, padx=4, pady=1)
        badge.pack(side=tk.RIGHT)

        for b in bullets:
            tk.Label(
                card, text=f"• {b}", font=("Helvetica", 8), fg="#cbd5e1", bg=self.inner_box_bg,
                justify=tk.LEFT, wraplength=480, anchor="w"
            ).pack(fill=tk.X, pady=1)

    # --- RENDER TAB A: ACTION ROADMAP ---
    def _render_roadmap_tab(
        self, cur, total_income, net_savings, saving_ratio,
        itemized_cards, total_cc_bills, total_cc_emis,
        itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
        total_committed_investments, total_mandatory_survival,
        term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
    ):
        for child in self.roadmap_container.winfo_children():
            child.destroy()

        # Priority 1: Credit Card High-APR Avalanche
        if total_cc_bills > 0:
            highest_card = max(itemized_cards, key=lambda x: x["bill"]) if itemized_cards else None
            bullets = [
                f"Total Credit Card Outflows: {cur}{total_cc_bills:,.2f}/month.",
                f"Immediate Payoff Target: '{highest_card['name']}' ({cur}{highest_card['bill']:,.2f}) carries highest exposure. Clear statement in full to prevent 36-42% interest bleed.",
            ]
            if total_cc_emis > 0:
                bullets.append(f"Active Card EMIs: {cur}{total_cc_emis:,.2f}/mo is locked in EMIs. Track your freedom calendar tab to reclaim this monthly cash flow.")
            bullets.append("Strict Credit Rule: Keep credit utilization below 30% of card limits to protect credit scores.")
            self._create_action_card(self.roadmap_container, "⚡", "Credit Card Debt Avalanche", "PRIORITY 1", self.neon_rose, bullets)
        else:
            bullets = ["No revolving credit card dues reported. Keep utilizing rewards cards with 100% monthly auto-debit payments."]
            self._create_action_card(self.roadmap_container, "✅", "Credit Card Hygiene", "OPTIMAL", self.neon_green, bullets)

        # Priority 2: Home Loans & Top-Up Prepayment Velocity
        if total_mortgages_and_topups > 0:
            bullets = [
                f"Combined Mortgage & Top-Up Outflow: {cur}{total_mortgages_and_topups:,.2f}/mo ({hl_burden_ratio:.1f}% of income).",
            ]
            if topup_loans_total > 0:
                bullets.append(
                    f"Top-Up Loan Prepayment Alert: You are servicing {cur}{topup_loans_total:,.2f}/mo in Top-Up EMIs. "
                    f"Top-up interest rates are typically 1-2% higher than standard home loans. Target extra savings into prepaying Top-Up principal first!"
                )
            if hl_burden_ratio > 35.0:
                bullets.append("Elevated Mortgage Burden: Mortgage obligations exceed safe 28% limits. Refrain from taking any new car or personal loans.")
            else:
                bullets.append("Controlled Mortgage Burden: Primary home loan is safely structured. Prepay 1 extra EMI per year to slash 5-7 years off your loan tenure.")
            self._create_action_card(self.roadmap_container, "🏠", "Home Loan & Top-Up Strategy", "PRIORITY 2", self.primary_blue, bullets)

        # Priority 3: Emergency Runway
        efund_3m = total_mandatory_survival * 3
        efund_6m = total_mandatory_survival * 6
        bullets = [
            f"Mandatory Monthly Survival Floor: {cur}{total_mandatory_survival:,.2f}/month.",
            f"3-Month Minimum Liquid Milestone: {cur}{efund_3m:,.2f}.",
            f"6-Month Full Safety Net Target: {cur}{efund_6m:,.2f}.",
            "Keep emergency reserves strictly in liquid sweep-in FDs or high-yield savings accounts."
        ]
        self._create_action_card(self.roadmap_container, "🛡️", "Emergency Liquid Runway", "SAFETY NET", self.neon_amber, bullets)

        # Priority 4: Wealth Compounding Engine
        bullets = [
            f"Committed Wealth Investments: {cur}{total_committed_investments:,.2f}/month.",
        ]
        if net_savings > 0:
            inv_70 = net_savings * 0.70
            contingency_30 = net_savings * 0.30
            bullets.extend([
                f"Additional Monthly Surplus Available: {cur}{net_savings:,.2f}.",
                f"Surplus Deployment: Channel 70% ({cur}{inv_70:,.2f}/mo) to increase index SIPs and 30% ({cur}{contingency_30:,.2f}/mo) to annual sinking funds (insurance/taxes)."
            ])
            self._create_action_card(self.roadmap_container, "📈", "Wealth Compounding & Surplus", "WEALTH ENGINE", self.neon_green, bullets)
        else:
            bullets.append(f"Monthly Deficit: -{cur}{abs(net_savings):,.2f}/month. Review non-essential expenses immediately to bring budget back to positive balance.")
            self._create_action_card(self.roadmap_container, "🚨", "Deficit Correction Required", "CRITICAL", self.neon_rose, bullets)

        # Priority 5: Family Protection & Term Insurance
        bullets = []
        if term_sum_assured <= 0:
            bullets.append(
                f"🚨 Critical Protection Gap: No Term Insurance reported! If an unforeseen tragedy occurs, your family must service "
                f"{cur}{total_mortgages_and_topups:,.2f}/mo in loan liabilities without primary income protection."
            )
            bullets.append(
                f"Recommended Pure Term Cover: At least {cur}{recommended_cover:,.2f} (~12x annual income) to fully clear mortgages & replace earning power."
            )
        elif cover_multiple >= 10.0:
            bullets.append(
                f"✅ Robust Term Cover: {cur}{term_sum_assured:,.2f} ({cover_multiple:.1f}x annual income) provides excellent financial insulation for your dependents."
            )
            if term_policy_name:
                bullets.append(f"Active Policy: {term_policy_name} (Covered till: {term_tenure_str or 'retirement'})")
            if term_premium > 0:
                bullets.append(f"Term Premium: {cur}{term_premium:,.2f}/month committed towards pure risk shield.")
        else:
            bullets.append(
                f"⚠️ Term Coverage Shortfall: Current cover of {cur}{term_sum_assured:,.2f} is only {cover_multiple:.1f}x annual income. "
                f"Recommended minimum cover is {cur}{recommended_cover:,.2f} (10x-15x income + loans)."
            )
            if term_policy_name:
                bullets.append(f"Active Policy: {term_policy_name} ({term_tenure_str})")
            bullets.append(f"Consider acquiring a top-up pure term plan to bridge the {cur}{(recommended_cover - term_sum_assured):,.2f} protection gap.")

        bullets.append("Health Shield: Maintain an independent family floater health policy (₹15L-₹25L / $50k+) separate from corporate employer cover.")

        tag_col = self.neon_green if cover_multiple >= 10.0 else (self.neon_amber if term_sum_assured > 0 else self.neon_rose)
        tag_txt = "ADEQUATELY SHIELDED" if cover_multiple >= 10.0 else ("COVERAGE GAP" if term_sum_assured > 0 else "NO TERM COVER")
        self._create_action_card(self.roadmap_container, "☂️", "Family Risk Shield Architecture", tag_txt, tag_col, bullets)

    # --- RENDER TAB B: LOAN AMORTIZATION ---
    def _render_amortization_tab(self, cur, itemized_loans):
        for child in self.amort_container.winfo_children():
            child.destroy()

        if not itemized_loans:
            tk.Label(self.amort_container, text="No loans or mortgages entered.", font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg).pack(pady=8)
            return

        tk.Label(self.amort_container, text="LOAN PAYOFF & AMORTIZATION PROGRESS:", font=("Helvetica", 10, "bold"), fg=self.neon_amber, bg=self.card_bg).pack(anchor="w", pady=(0, 6))

        for item in itemized_loans:
            card = tk.Frame(self.amort_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=8)
            card.pack(fill=tk.X, pady=4)

            # Top: Label + EMI
            top_r = tk.Frame(card, bg=self.inner_box_bg)
            top_r.pack(fill=tk.X)
            tk.Label(top_r, text=item["label"], font=("Helvetica", 9, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg).pack(side=tk.LEFT)
            tk.Label(top_r, text=f"EMI: {cur}{item['emi']:,.2f}/mo", font=("Helvetica", 9, "bold"), fg=self.neon_green, bg=self.inner_box_bg).pack(side=tk.RIGHT)

            amort = item["amort"]
            if amort:
                m_info = tk.Frame(card, bg=self.inner_box_bg)
                m_info.pack(fill=tk.X, pady=(2, 4))
                txt_left = f"Sanctioned: {cur}{item['total_amt']:,.2f}  |  Rate: {item['rate']}% p.a.  |  Started: {amort['start_fmt']} ({amort['months_elapsed']} mos paid)"
                tk.Label(m_info, text=txt_left, font=("Helvetica", 8), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w")

                # Visual Amortization Progress Bar
                p_bar = tk.Canvas(card, height=12, bg="#09090d", highlightthickness=0)
                p_bar.pack(fill=tk.X, pady=2)
                p_bar.update_idletasks()
                bw = p_bar.winfo_width() if p_bar.winfo_width() > 10 else 400
                fill_w = int((amort["completed_pct"] / 100.0) * bw)
                if fill_w > 0:
                    p_bar.create_rectangle(0, 0, fill_w, 12, fill=self.neon_green, outline="")

                # Bottom Stats: Leftover Principal & Est Remaining Months
                bot_r = tk.Frame(card, bg=self.inner_box_bg)
                bot_r.pack(fill=tk.X, pady=(2, 0))
                rem_str = f"~{amort['remaining_months'] // 12} yrs {amort['remaining_months'] % 12} mos left" if amort['remaining_months'] < 900 else "High interest"
                tk.Label(bot_r, text=f"✅ {amort['completed_pct']:.1f}% Paid Off", font=("Helvetica", 8, "bold"), fg=self.neon_green, bg=self.inner_box_bg).pack(side=tk.LEFT)
                tk.Label(bot_r, text=f"Leftover: {cur}{amort['balance']:,.2f} ({rem_str})", font=("Helvetica", 8, "bold"), fg=self.neon_rose, bg=self.inner_box_bg).pack(side=tk.RIGHT)
            else:
                tk.Label(card, text="Enter Total Principal, Interest Rate, and Start Date to calculate exact leftover balance.", font=("Helvetica", 8), fg=self.text_muted, bg=self.inner_box_bg).pack(anchor="w", pady=2)

    # --- RENDER TAB C: CC UTILIZATION & EMI CALENDAR ---
    def _render_cc_intel_tab(self, cur, itemized_cards, total_limits, total_bills, overall_util):
        for child in self.cc_intel_container.winfo_children():
            child.destroy()

        if not itemized_cards:
            tk.Label(self.cc_intel_container, text="No credit cards entered.", font=("Helvetica", 9), fg=self.text_muted, bg=self.card_bg).pack(pady=8)
            return

        # Overall Utilization Card
        top_c = tk.Frame(self.cc_intel_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=6)
        top_c.pack(fill=tk.X, pady=(0, 6))

        ucol = self.neon_green if overall_util <= 30 else (self.neon_amber if overall_util <= 50 else self.neon_rose)
        tk.Label(top_c, text=f"Total Credit Limit: {cur}{total_limits:,.2f}  |  Total Monthly Bill: {cur}{total_bills:,.2f}", font=("Helvetica", 9, "bold"), fg=self.text_dark, bg=self.inner_box_bg).pack(anchor="w")
        tk.Label(top_c, text=f"Overall Credit Utilization: {overall_util:.1f}% (Healthy Benchmark: < 30%)", font=("Helvetica", 9, "bold"), fg=ucol, bg=self.inner_box_bg).pack(anchor="w", pady=(1, 0))

        # Individual Cards
        tk.Label(self.cc_intel_container, text="CARD-BY-CARD LIMITS & FREEDOM CALENDAR:", font=("Helvetica", 9, "bold"), fg=self.neon_rose, bg=self.card_bg).pack(anchor="w", pady=(4, 4))

        for c in itemized_cards:
            card = tk.Frame(self.cc_intel_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=6)
            card.pack(fill=tk.X, pady=3)

            r1 = tk.Frame(card, bg=self.inner_box_bg)
            r1.pack(fill=tk.X)
            tk.Label(r1, text=c["name"], font=("Helvetica", 9, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg).pack(side=tk.LEFT)
            tk.Label(r1, text=f"Bill: {cur}{c['bill']:,.2f}", font=("Helvetica", 9, "bold"), fg=self.neon_rose, bg=self.inner_box_bg).pack(side=tk.RIGHT)

            r2 = tk.Frame(card, bg=self.inner_box_bg)
            r2.pack(fill=tk.X, pady=(1, 2))
            if c["limit"] > 0:
                uc = self.neon_green if c["util_pct"] <= 30 else (self.neon_amber if c["util_pct"] <= 50 else self.neon_rose)
                tk.Label(r2, text=f"Limit: {cur}{c['limit']:,.2f}  |  Utilization: {c['util_pct']:.1f}%", font=("Helvetica", 8, "bold"), fg=uc, bg=self.inner_box_bg).pack(side=tk.LEFT)
            else:
                tk.Label(r2, text="No limit specified", font=("Helvetica", 8), fg=self.text_muted, bg=self.inner_box_bg).pack(side=tk.LEFT)

            # EMI details
            if c["emi"] > 0:
                r3 = tk.Frame(card, bg="#271018", padx=6, pady=3)
                r3.pack(fill=tk.X, pady=(2, 0))
                tk.Label(r3, text=f"💳 Active EMI: {cur}{c['emi']:,.2f}/mo", font=("Helvetica", 8, "bold"), fg=self.neon_rose, bg="#271018").pack(side=tk.LEFT)
                dates_str = f"Tenure: {c['start_date']} ➔ {c['end_date']}" if (c['start_date'] or c['end_date']) else "Dates not specified"
                tk.Label(r3, text=f"Freedom Date: {dates_str}", font=("Helvetica", 8, "bold"), fg="#fca5a5", bg="#271018").pack(side=tk.RIGHT)

    # --- RENDER TAB D: SAVINGS PORTFOLIO & RATIOS ---
    def _render_savings_intel_tab(
        self, cur, total_income, epf, nps, ulip, sip, fd, inv_other,
        total_committed, committed_ratio, total_saving_ratio,
        invest_months, inv_start_str, net_surplus,
        term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
    ):
        for child in self.savings_intel_container.winfo_children():
            child.destroy()

        top_b = tk.Frame(self.savings_intel_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=8)
        top_b.pack(fill=tk.X, pady=(0, 6))

        tk.Label(top_b, text="DUAL SAVING RATIO DIAGNOSTICS:", font=("Helvetica", 10, "bold"), fg=self.neon_green, bg=self.inner_box_bg).pack(anchor="w")
        tk.Label(
            top_b,
            text=f"• Contractual / Committed Saving Ratio: {committed_ratio:.1f}% of income ({cur}{total_committed:,.2f}/mo)\n"
                 f"• Total Combined Saving Ratio (Committed + Surplus): {total_saving_ratio:.1f}% of income",
            font=("Helvetica", 8, "bold"), fg=self.neon_cyan, bg=self.inner_box_bg, justify=tk.LEFT
        ).pack(anchor="w", pady=(2, 0))

        if invest_months > 0:
            tenure_yr = invest_months // 12
            tenure_mo = invest_months % 12
            est_cumul_invested = total_committed * invest_months
            tk.Label(
                top_b,
                text=f"• Discipline Longevity: Regular investor for {tenure_yr} yrs {tenure_mo} mos (Started {inv_start_str}).\n"
                     f"• Estimated Cumulative Contributions: ~{cur}{est_cumul_invested:,.2f} invested to date!",
                font=("Helvetica", 8, "bold"), fg=self.neon_amber, bg=self.inner_box_bg, justify=tk.LEFT
            ).pack(anchor="w", pady=(3, 0))

        # Itemized breakdown table
        tk.Label(self.savings_intel_container, text="PORTFOLIO ASSET ALLOCATION BREAKDOWN:", font=("Helvetica", 9, "bold"), fg=self.neon_purple, bg=self.card_bg).pack(anchor="w", pady=(4, 4))

        allocations = [
            ("EPF (Employee Provident Fund)", epf, self.neon_green),
            ("NPS (National Pension System)", nps, "#2dd4bf"),
            ("ULIP / Insurance Plans", ulip, self.neon_amber),
            ("Equity / Mutual Fund SIPs", sip, self.neon_cyan),
            ("Fixed Deposits / Recurring Deposits", fd, self.neon_purple),
            ("Term Life Insurance Premium", term_premium, self.primary_blue),
            ("Other Investments (PPF/Gold)", inv_other, "#f43f5e")
        ]

        for label, amt, col in allocations:
            if amt <= 0:
                continue
            pct = (amt / total_income * 100.0) if total_income > 0 else 0.0
            row = tk.Frame(self.savings_intel_container, bg=self.card_bg, pady=2)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"• {label}", font=("Helvetica", 8), fg=self.text_dark, bg=self.card_bg, width=32, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=f"{cur}{amt:,.2f}", font=("Helvetica", 8, "bold"), fg=col, bg=self.card_bg, width=16, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=f"({pct:.1f}% of income)", font=("Helvetica", 8), fg=self.text_muted, bg=self.card_bg).pack(side=tk.LEFT)

        # Dedicated Term Insurance Risk Shield Card
        tk.Frame(self.savings_intel_container, bg=self.border_color, height=1).pack(fill=tk.X, pady=8)
        term_card = tk.Frame(self.savings_intel_container, bg=self.inner_box_bg, highlightbackground=self.border_color, highlightthickness=1, padx=10, pady=8)
        term_card.pack(fill=tk.X, pady=2)

        tc_top = tk.Frame(term_card, bg=self.inner_box_bg)
        tc_top.pack(fill=tk.X)
        tk.Label(tc_top, text="☂️ TERM INSURANCE & LIFE RISK PROTECTION", font=("Helvetica", 9, "bold"), fg=self.primary_blue, bg=self.inner_box_bg).pack(side=tk.LEFT)

        badge_col = self.neon_green if cover_multiple >= 10.0 else (self.neon_amber if term_sum_assured > 0 else self.neon_rose)
        badge_label = f" {cover_multiple:.1f}x ANNUAL INCOME " if term_sum_assured > 0 else " NO COVER REPORTED "
        tk.Label(tc_top, text=badge_label, font=("Helvetica", 7, "bold"), fg="#ffffff", bg=badge_col, padx=4, pady=1).pack(side=tk.RIGHT)

        if term_sum_assured > 0:
            p_desc = f"{term_policy_name} ({term_tenure_str})" if (term_policy_name or term_tenure_str) else "Active Pure Term Plan"
            tk.Label(
                term_card,
                text=f"• Active Life Cover (Sum Assured): {cur}{term_sum_assured:,.2f} ({cover_multiple:.1f}x annual income)\n"
                     f"• Monthly Risk Premium Outflow: {cur}{term_premium:,.2f}/mo\n"
                     f"• Benchmark Target: {cur}{recommended_cover:,.2f} (10x-15x income + liabilities)\n"
                     f"• Policy Details: {p_desc}",
                font=("Helvetica", 8), fg="#cbd5e1", bg=self.inner_box_bg, justify=tk.LEFT
            ).pack(anchor="w", pady=(3, 0))
        else:
            tk.Label(
                term_card,
                text=f"• No term insurance entered. Recommended life cover is {cur}{recommended_cover:,.2f} (~12x annual income) to protect dependents.",
                font=("Helvetica", 8), fg=self.neon_rose, bg=self.inner_box_bg, justify=tk.LEFT
            ).pack(anchor="w", pady=(3, 0))

    # --- FULL REPORT STRING GENERATION ---
    def _generate_full_report_text(
        self, cur, total_income, his_inc, wife_inc, other_inc,
        itemized_loans, home_loans_total, topup_loans_total, total_mortgages_and_topups, hl_burden_ratio,
        itemized_cards, total_cc_bills, total_cc_limits, overall_cc_util, total_cc_emis,
        epf, nps, ulip, sip, fd, inv_other, total_committed,
        invest_months, committed_ratio, total_saving_ratio,
        total_utilities, total_needs, total_wants,
        total_outflow, net_surplus, dti_ratio, health_score,
        term_premium, term_sum_assured, term_tenure_str, term_policy_name, cover_multiple, recommended_cover
    ):
        lines = [
            "==================================================================",
            "        HOUSEHOLD FINANCIAL FLOW & WEALTH STABILITY REPORT        ",
            f"        Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Health Score: {health_score}/100",
            "==================================================================\n",
            f"1. INFLOWS & INCOME:",
            f"   • Combined Income: {cur}{total_income:,.2f}",
            f"     - Your Income: {cur}{his_inc:,.2f} ({(his_inc/total_income)*100:.1f}%)",
            f"     - Wife's Income: {cur}{wife_inc:,.2f} ({(wife_inc/total_income)*100:.1f}%)",
        ]
        if other_inc > 0:
            lines.append(f"     - Additional Inflows: {cur}{other_inc:,.2f}")

        lines.extend([
            f"\n2. HOME LOANS & TOP-UP AMORTIZATION:",
            f"   • Combined Mortgages & Top-Ups: {cur}{total_mortgages_and_topups:,.2f}/mo ({hl_burden_ratio:.1f}% of income)",
            f"     - Primary Home Loans: {cur}{home_loans_total:,.2f}/mo",
            f"     - Top-Up Loans: {cur}{topup_loans_total:,.2f}/mo"
        ])
        for it in itemized_loans:
            amort = it["amort"]
            if amort:
                lines.append(f"     - {it['label']}: EMI {cur}{it['emi']:,.2f} | Paid: {amort['completed_pct']:.1f}% | Leftover: {cur}{amort['balance']:,.2f} (~{amort['remaining_months']} mos left)")
            else:
                lines.append(f"     - {it['label']}: EMI {cur}{it['emi']:,.2f}")

        lines.extend([
            f"\n3. CREDIT CARDS & ACTIVE EMIS:",
            f"   • Total Card Bill: {cur}{total_cc_bills:,.2f} | Total Limit: {cur}{total_cc_limits:,.2f} (Util: {overall_cc_util:.1f}%)"
        ])
        for c in itemized_cards:
            emi_txt = f" | EMI: {cur}{c['emi']:,.2f} (End: {c['end_date']})" if c['emi'] > 0 else ""
            lines.append(f"     - {c['name']}: Bill {cur}{c['bill']:,.2f} / Limit {cur}{c['limit']:,.2f} ({c['util_pct']:.1f}% util){emi_txt}")

        lines.extend([
            f"\n4. COMMITTED SAVINGS, INVESTMENTS & TERM INSURANCE:",
            f"   • Total Monthly Allocations: {cur}{total_committed:,.2f}/mo",
            f"     - EPF: {cur}{epf:,.2f} | NPS: {cur}{nps:,.2f} | ULIP: {cur}{ulip:,.2f}",
            f"     - Equity/SIPs: {cur}{sip:,.2f} | FD/RD: {cur}{fd:,.2f} | Other: {cur}{inv_other:,.2f}",
            f"     - Term Insurance Premium: {cur}{term_premium:,.2f}/mo",
            f"   • Term Insurance Sum Assured: {cur}{term_sum_assured:,.2f} ({cover_multiple:.1f}x annual income | Benchmark: {cur}{recommended_cover:,.2f})",
        ])
        if term_policy_name or term_tenure_str:
            lines.append(f"     - Policy: {term_policy_name or 'Pure Term'} (Covered: {term_tenure_str or 'N/A'})")
        lines.extend([
            f"   • Committed Saving Ratio: {committed_ratio:.1f}%",
            f"   • Total Combined Saving Ratio: {total_saving_ratio:.1f}%"
        ])
        if invest_months > 0:
            lines.append(f"   • Discipline History: Regular investor for {invest_months} months.")

        lines.extend([
            f"\n5. LIVING EXPENSES & CASH FLOW:",
            f"   • Utilities: {cur}{total_utilities:,.2f} | Needs: {cur}{total_needs:,.2f} | Wants: {cur}{total_wants:,.2f}",
            f"   • Total Monthly Outflow: {cur}{total_outflow:,.2f}",
            f"   • Net Monthly Surplus: {cur}{net_surplus:,.2f}",
            f"   • Debt-to-Income (DTI): {dti_ratio:.1f}% (Benchmark: < 35%)",
            f"\n6. ACTION ROADMAP:",
            f"   • Emergency Liquid Runway Target: {cur}{(total_mortgages_and_topups + total_utilities + total_needs)*6:,.2f} (6 months survival)",
            f"   • Top-Up Loan Priority: Target surplus to accelerate prepayments and eliminate high-interest amortization.",
            f"   • Life Protection Shield: Term cover of {cur}{term_sum_assured:,.2f} ({cover_multiple:.1f}x annual income vs recommended {cur}{recommended_cover:,.2f})."
        ])

        self.latest_report_text = "\n".join(lines)
        self.full_report_text.delete("1.0", tk.END)
        self.full_report_text.insert(tk.END, self.latest_report_text)

    def export_report(self):
        if not self.latest_report_text:
            messagebox.showinfo("Export Report", "Please calculate your financial flow first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("Markdown File", "*.md"), ("All Files", "*.*")],
            initialfile=f"financial_plan_{datetime.now().strftime('%Y%m%d')}.txt"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.latest_report_text)
                messagebox.showinfo("Report Exported", f"Report saved successfully:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save file: {e}")

    def reset_all_fields(self):
        """Resets all fields strictly with NO DEFAULT VALUES."""
        self.entry_his_income.delete(0, tk.END)
        self.entry_wife_income.delete(0, tk.END)
        self.entry_other_income.delete(0, tk.END)
        self.entry_house_rent.delete(0, tk.END)

        for r in self.loan_rows:
            r["desc"].delete(0, tk.END)
            r["total_amt"].delete(0, tk.END)
            r["rate"].delete(0, tk.END)
            r["start_date"].delete(0, tk.END)
            r["emi"].delete(0, tk.END)

        for r in self.card_rows:
            r["name"].delete(0, tk.END)
            r["limit"].delete(0, tk.END)
            r["bill"].delete(0, tk.END)
            r["emi_amt"].delete(0, tk.END)
            r["start_date"].delete(0, tk.END)
            r["end_date"].delete(0, tk.END)
            r["badge"].config(text="Awaiting input", fg=self.text_muted)
            draw_card_thumbnail(r["canvas"], detect_card_brand(""))

        self.entry_inv_epf.delete(0, tk.END)
        self.entry_inv_nps.delete(0, tk.END)
        self.entry_inv_ulip.delete(0, tk.END)
        self.entry_inv_sip.delete(0, tk.END)
        self.entry_inv_fd.delete(0, tk.END)
        self.entry_inv_other.delete(0, tk.END)
        self.entry_inv_start_date.delete(0, tk.END)

        self.entry_term_premium.delete(0, tk.END)
        self.entry_term_sum_assured.delete(0, tk.END)
        self.entry_term_tenure.delete(0, tk.END)
        self.entry_term_nominee.delete(0, tk.END)

        self.entry_util_elec.delete(0, tk.END)
        self.entry_util_water_gas.delete(0, tk.END)
        self.entry_util_internet.delete(0, tk.END)
        self.entry_util_mobile.delete(0, tk.END)
        self.entry_need_groceries.delete(0, tk.END)
        self.entry_need_healthcare.delete(0, tk.END)
        self.entry_need_commute.delete(0, tk.END)
        self.entry_need_education.delete(0, tk.END)
        self.entry_want_dining.delete(0, tk.END)
        self.entry_want_leisure.delete(0, tk.END)

        self.kpi_inflow.config(text="--", fg=self.neon_green)
        self.kpi_outflow.config(text="--", fg=self.neon_rose)
        self.kpi_savings.config(text="--", fg=self.neon_cyan)
        self.kpi_dti.config(text="--", fg=self.neon_amber)

        self.lbl_score_grade.config(text="READY FOR ANALYSIS", fg=self.neon_cyan)
        self.lbl_score_summary.config(text="Enter figures on the left and click 'Calculate Flow'.")
        self.lbl_spend_save.config(text="Committed Invest: --  |  Total Saving Ratio: --%", fg=self.text_dark)
        self.lbl_hl_burden.config(text="Mortgage & Top-Up Burden: --%", fg=self.text_muted)

        self.flow_canvas.delete("all")
        self.latest_report_text = ""
        self.last_calc_data = None
        self.full_report_text.delete("1.0", tk.END)


def main():
    root = tk.Tk()
    app = FinancialPlannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
