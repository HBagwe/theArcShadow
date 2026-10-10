"""
WhatsApp Bot Webhook Server for SplitExpense
============================================
Allows adding expenses and checking balances directly via WhatsApp.

Features:
- Pure standard library Python (no third-party pip dependencies required, zero setup friction).
- Twilio & Meta WhatsApp Webhook compatible (handles x-www-form-urlencoded & JSON payloads).
- Connects directly to existing SplitExpense SQLite database (splitwise_data.db).
- Matches incoming WhatsApp sender's phone number with registered members automatically.
- Intelligent Natural Language / Keyword Parser:
    * "Dinner 1200"                     -> Adds expense paid by sender, split among all group members.
    * "Lunch 450 paid by Alice"         -> Specifies payer explicitly.
    * "Taxi 600 for Bob, Charlie"       -> Splits only between specific members.
    * "Coffee 150 paid by Bob for Alice"-> Exact payer & borrower.
    * "balance" or "bal"                -> Returns personal balance & who to pay / receive from.
    * "summary" or "debts"              -> Returns full simplified settlement plan.
    * "help"                            -> Displays list of available commands.
- Interactive Simulator Mode: test WhatsApp commands right in your terminal without any server setup!

Usage:
  1. Test locally:
     python3 whatsapp_bot.py --test

  2. Run Webhook Server:
     python3 whatsapp_bot.py --port 8080
"""

import argparse
import html
import http.server
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime

# Import database and engine from existing SplitExpense application
try:
    from splitwise_app import Database, SplitwiseEngine, DB_FILE
except ImportError:
    # Fallback to local file path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from splitwise_app import Database, SplitwiseEngine, DB_FILE


class WhatsAppExpenseBot:
    def __init__(self, db: Database = None):
        self.db = db or Database()
        self.engine = SplitwiseEngine(self.db)
        self.currency = self.engine.get_setting("currency", "₹")

    def normalize_phone(self, phone: str) -> str:
        """Strip non-digits to match numbers reliably regardless of formatting."""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone)
        # Remove country code 91 if present for matching last 10 digits
        if len(digits) > 10:
            return digits[-10:]
        return digits

    def find_member_by_phone(self, phone_str: str):
        """Find registered member by incoming phone number."""
        target_norm = self.normalize_phone(phone_str)
        if not target_norm:
            return None

        for m in self.engine.get_members():
            m_norm = self.normalize_phone(m.get("phone", ""))
            if m_norm and (m_norm == target_norm or m_norm.endswith(target_norm) or target_norm.endswith(m_norm)):
                return m
        return None

    def find_member_by_name(self, name_str: str):
        """Find registered member by full name or first name (case-insensitive)."""
        target = name_str.strip().lower()
        if not target:
            return None

        members = self.engine.get_members()
        # 1. Exact match
        for m in members:
            if m["name"].lower() == target:
                return m

        # 2. First name prefix match
        for m in members:
            first_name = m["name"].lower().split()[0]
            if first_name == target:
                return m

        # 3. Substring match
        for m in members:
            if target in m["name"].lower():
                return m

        return None

    def process_message(self, sender_phone: str, text: str) -> str:
        """Parse incoming message and execute SplitExpense action."""
        cleaned_text = text.strip()
        if not cleaned_text:
            return "👋 Send 'help' to see how to add expenses or view balances."

        lower_text = cleaned_text.lower()

        # Command: Help
        if lower_text in ("help", "?", "commands", "menu"):
            return self._build_help_message()

        # Command: Personal Balance
        if lower_text in ("balance", "bal", "my balance", "status"):
            return self._build_balance_message(sender_phone)

        # Command: Group Debts / Summary
        if lower_text in ("summary", "debts", "plan", "settlements"):
            return self._build_summary_message()

        # Command: Add Expense
        return self._parse_and_add_expense(sender_phone, cleaned_text)

    def _build_help_message(self) -> str:
        return (
            "🤖 *SplitExpense WhatsApp Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Here is how you can use this bot:\n\n"
            "➕ *Add Expense:*\n"
            "• `Dinner 1200`\n"
            "  _(splits equally among all members)_\n"
            "• `Lunch 450 paid by Bob`\n"
            "  _(specify who paid)_\n"
            "• `Taxi 600 for Alice, Charlie`\n"
            "  _(splits only for specified members)_\n"
            "• `Coffee 150 paid by Bob for Alice`\n"
            "  _(one person paying for another)_\n\n"
            "📊 *Check Balances:*\n"
            "• `balance` - Check your net balance\n"
            "• `summary` - View simplified settlement plan\n"
            "• `help` - Show this guide"
        )

    def _build_balance_message(self, sender_phone: str) -> str:
        member = self.find_member_by_phone(sender_phone)
        balances = self.engine.calculate_balances()

        if not member:
            # If phone is not matched, display all balances summary
            lines = ["📊 *Current Member Balances:*", "━━━━━━━━━━━━━━━━━━━━"]
            for b in balances:
                net = b["net_balance"]
                sign = "+" if net > 0 else ""
                status = "🟢 gets back" if net > 0 else ("🔴 owes" if net < 0 else "⚪ settled")
                lines.append(f"• *{b['name']}*: {sign}{self.currency}{net:.2f} ({status})")
            lines.append("\n💡 Register your phone number in SplitExpense for personalized balance reports.")
            return "\n".join(lines)

        user_bal = next((b for b in balances if b["member_id"] == member["id"]), None)
        if not user_bal:
            return f"👋 Hi {member['name']}, you currently have no recorded transactions."

        net = user_bal["net_balance"]
        lines = [
            f"👤 *Account Balance for {member['name']}*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"• Total Paid (+): {self.currency}{user_bal['total_paid']:.2f}",
            f"• Total Share (-): {self.currency}{user_bal['total_owed']:.2f}",
        ]

        if abs(net) < 0.01:
            lines.append("• *Status:* ⚪ All settled up! 🎉")
        elif net > 0:
            lines.append(f"• *Status:* 🟢 You are owed *{self.currency}{net:.2f}* in total.")
        else:
            lines.append(f"• *Status:* 🔴 You owe *{self.currency}{-net:.2f}* in total.")

        # Show direct debts for this user from simplified plan
        plan = self.engine.simplify_debts()
        user_debts = [p for p in plan if p["from_id"] == member["id"]]
        user_credits = [p for p in plan if p["to_id"] == member["id"]]

        if user_debts:
            lines.append("\n👉 *You need to pay:*")
            for d in user_debts:
                upi_str = f" (UPI: {d['to_upi']})" if d.get("to_upi") else ""
                lines.append(f"  • Pay *{d['to_name']}*: {self.currency}{d['amount']:.2f}{upi_str}")

        if user_credits:
            lines.append("\n💰 *People who owe you:*")
            for c in user_credits:
                lines.append(f"  • *{c['from_name']}* owes you: {self.currency}{c['amount']:.2f}")

        return "\n".join(lines)

    def _build_summary_message(self) -> str:
        plan = self.engine.simplify_debts()
        expenses = self.engine.get_expenses()
        total_spent = sum(e["amount"] for e in expenses)

        lines = [
            "📋 *SplitExpense Group Summary*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"💰 *Total Group Spending:* {self.currency}{total_spent:,.2f}",
            f"🧾 *Total Expenses:* {len(expenses)}",
            "",
            "🤝 *Simplified Settlement Plan:*",
        ]

        if not plan:
            lines.append("🎉 All members are completely settled up!")
        else:
            for p in plan:
                lines.append(f"• *{p['from_name']}* ➔ *{p['to_name']}*: {self.currency}{p['amount']:.2f}")

        return "\n".join(lines)

    def _parse_and_add_expense(self, sender_phone: str, text: str) -> str:
        """Parse natural language expense formats."""
        all_members = self.engine.get_members()
        if not all_members:
            return "❌ No members found in SplitExpense. Please add members first."

        regex = (
            r"^(?P<desc>.+?)\s+"
            r"(?:₹|\$|€|£|rs\.?|inr)?\s*(?P<amount>\d+(?:\.\d{1,2})?)"
            r"(?:\s+paid\s+by\s+(?P<payer>[a-zA-Z0-9_\s]+?))?"
            r"(?:\s+for\s+(?P<members>[a-zA-Z0-9_,\s]+))?$"
        )

        match = re.search(regex, text, re.IGNORECASE)
        if not match:
            return (
                "❓ Could not parse expense format.\n\n"
                "Try sending:\n"
                "• `Dinner 1200`\n"
                "• `Lunch 450 paid by Bob`\n"
                "• `Taxi 600 for Alice, Charlie`\n"
                "• Or send `help` for more options."
            )

        desc = match.group("desc").strip()
        try:
            amount = float(match.group("amount"))
            if amount <= 0:
                return "❌ Amount must be greater than zero."
        except ValueError:
            return "❌ Invalid expense amount."

        raw_payer = match.group("payer")
        raw_members = match.group("members")

        # 1. Resolve Payer
        payer = None
        if raw_payer:
            payer = self.find_member_by_name(raw_payer.strip())
            if not payer:
                return f"❌ Could not find member named '{raw_payer.strip()}'. Check member directory."
        else:
            # Default to message sender if phone matches
            payer = self.find_member_by_phone(sender_phone)
            if not payer:
                payer = all_members[0]

        # 2. Resolve Participants
        participants = []
        if raw_members:
            names = [n.strip() for n in re.split(r"[,&]| and ", raw_members) if n.strip()]
            for n in names:
                m = self.find_member_by_name(n)
                if m:
                    if m not in participants:
                        participants.append(m)
                else:
                    return f"❌ Could not find participant named '{n}'. Check member directory."

            if not participants:
                return "❌ No valid participants found for this expense."
        else:
            participants = list(all_members)

        # 3. Calculate Splits
        num_splits = len(participants)
        base_share = round(amount / num_splits, 2)
        diff = round(amount - (base_share * num_splits), 2)

        splits = []
        for idx, m in enumerate(participants):
            owed = base_share + (diff if idx == 0 else 0.0)
            splits.append((m["id"], owed))

        # 4. Save into Database
        split_type = "EQUAL_EXCL" if (payer not in participants) else "EQUAL_INCL"
        date_str = datetime.now().strftime("%Y-%m-%d")

        exp_id = self.engine.add_expense(
            group_id=None,
            description=desc,
            amount=amount,
            payer_id=payer["id"],
            split_type=split_type,
            splits=splits,
            category="WhatsApp",
            date=date_str,
            notes=f"Added via WhatsApp from {sender_phone}"
        )

        # 5. Format Confirmation Reply
        lines = [
            "✅ *Expense Logged Successfully!*",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📝 *Description:* {desc}",
            f"💵 *Total Amount:* {self.currency}{amount:,.2f}",
            f"👤 *Paid By:* {payer['name']}",
            f"👥 *Split Between:* {', '.join([p['name'] for p in participants])}",
            f"💰 *Each Share:* ~{self.currency}{base_share:.2f}",
            "",
            "✨ Net balances updated instantly in SplitExpense!",
        ]
        return "\n".join(lines)


# ============================================================================
# HTTP WEBHOOK REQUEST HANDLER (Pure Python Standard Library)
# ============================================================================

class WhatsAppWebhookHandler(http.server.BaseHTTPRequestHandler):
    bot = WhatsAppExpenseBot()

    def do_GET(self):
        """Health check & verification endpoint."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        # Meta WhatsApp Webhook Verification Support (hub.challenge)
        if "hub.challenge" in params:
            challenge = params["hub.challenge"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
            return

        # Simple HTML info page
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head><title>SplitExpense WhatsApp Webhook</title></head>
        <body style="font-family: sans-serif; background: #0B0F19; color: #F8FAFC; padding: 40px;">
            <h1 style="color: #38BDF8;">⚡ SplitExpense WhatsApp Webhook Server</h1>
            <p style="color: #10B981;">● Status: <strong>Online & Listening</strong></p>
            <p>Database: <code>{DB_FILE}</code></p>
            <hr style="border: 1px solid #253347;">
            <p>Send a POST request to <code>/whatsapp-webhook</code> from Twilio or Meta WhatsApp Cloud API.</p>
        </body>
        </html>
        """
        self.wfile.write(html_page.encode("utf-8"))

    def do_POST(self):
        """Receive incoming message from Twilio or Meta WhatsApp API."""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        sender_phone = ""
        message_body = ""

        # Twilio WhatsApp Webhook Format (application/x-www-form-urlencoded)
        if "x-www-form-urlencoded" in content_type:
            data = urllib.parse.parse_qs(body)
            sender_phone = data.get("From", [""])[0].replace("whatsapp:", "")
            message_body = data.get("Body", [""])[0]

        # Meta WhatsApp Cloud API Format (application/json)
        elif "json" in content_type:
            try:
                data = json.loads(body)
                entry = data.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                messages = value.get("messages", [])
                if messages:
                    msg = messages[0]
                    sender_phone = msg.get("from", "")
                    message_body = msg.get("text", {}).get("body", "")
            except Exception as e:
                print(f"[Webhook Error] JSON parse failure: {e}")

        print(f"\n[Incoming WhatsApp] From: '{sender_phone}' | Message: '{message_body}'")

        # Process via Bot Engine
        reply_text = self.bot.process_message(sender_phone, message_body)

        # Build Twilio TwiML XML Response
        escaped_reply = html.escape(reply_text)
        twiml_response = (
            f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            f"<Response>\n"
            f"    <Message>{escaped_reply}</Message>\n"
            f"</Response>"
        )

        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.end_headers()
        self.wfile.write(twiml_response.encode("utf-8"))


# ============================================================================
# CLI & SIMULATOR RUNNER
# ============================================================================

def run_server(port=8080):
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, WhatsAppWebhookHandler)
    print("=" * 65)
    print("⚡ SplitExpense WhatsApp Webhook Server")
    print(f"📡 Listening on: http://localhost:{port}/whatsapp-webhook")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server Stopped]")
        httpd.server_close()


def run_interactive_test():
    """Terminal simulator to test WhatsApp commands without any server."""
    bot = WhatsAppExpenseBot()
    print("=" * 65)
    print("🤖 SplitExpense WhatsApp Interactive Simulator")
    print("Type your message like a WhatsApp user! (Type 'exit' to quit)")
    print("Example: 'Dinner 1200' or 'Lunch 450 paid by Bob' or 'balance'")
    print("=" * 65)

    members = bot.engine.get_members()
    default_sender = members[0]["phone"] if members and members[0].get("phone") else "+919876543210"
    print(f"Simulating as Member: {members[0]['name'] if members else 'User'} ({default_sender})\n")

    while True:
        try:
            user_input = input("\n📱 You (WhatsApp): ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            response = bot.process_message(default_sender, user_input)
            print("\n🤖 Bot Reply:")
            print(response)
        except (KeyboardInterrupt, EOFError):
            break


def main():
    parser = argparse.ArgumentParser(description="SplitExpense WhatsApp Bot & Webhook Server")
    parser.add_argument("--test", action="store_true", help="Run interactive terminal simulator without webhook")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port for webhook (default: 8080)")
    args = parser.parse_args()

    if args.test:
        run_interactive_test()
    else:
        run_server(args.port)


if __name__ == "__main__":
    main()
