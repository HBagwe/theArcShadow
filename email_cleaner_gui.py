import getpass
import imaplib
import re
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, scrolledtext

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def parse_selectable_folders(mail):
    """
    Fetches all selectable folders (mailboxes) from the Gmail account.
    Filters out non-selectable parent containers (marked with \\Noselect).
    """
    status, raw_folders = mail.list()
    if status != "OK":
        return []

    pattern = re.compile(r'\((?P<flags>.*?)\)\s+"(?P<delimiter>.*?)"\s+(?P<name>.+)')
    folders = []

    for item in raw_folders:
        decoded = item.decode("utf-8", errors="ignore")
        match = pattern.match(decoded)
        if match:
            flags = match.group("flags")
            name = match.group("name").strip(' "')
            if "\\Noselect" not in flags:
                folders.append(name)
        else:
            parts = decoded.split(' "/" ')
            if len(parts) == 2:
                name = parts[1].strip(' "')
                folders.append(name)

    return folders


class EmailCleanerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gmail Folder Email Cleaner")
        self.root.geometry("700x750")
        self.root.minsize(640, 680)

        self.mail = None
        self.folders = []
        self.is_connected = False
        self.is_busy = False
        self.selected_folder_count = None

        self._configure_styles()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # General styling
        style.configure("Title.TLabel", font=("Helvetica", 16, "bold"), foreground="#1a73e8")
        style.configure("Subtitle.TLabel", font=("Helvetica", 10), foreground="#5f6368")
        style.configure("Header.TLabelframe.Label", font=("Helvetica", 11, "bold"), foreground="#202124")
        style.configure("Danger.TButton", font=("Helvetica", 11, "bold"), foreground="#c5221f")
        style.configure("Primary.TButton", font=("Helvetica", 11, "bold"), foreground="#1a73e8")
        style.configure("Status.TLabel", font=("Helvetica", 10), foreground="#3c4043")

    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding="15")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Gmail Folder Email Cleaner", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header_frame,
            text="Clean unwanted emails folder-by-folder securely using your Gmail App Password.",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # 1. Credentials Frame
        cred_frame = ttk.LabelFrame(main_container, text="1. Account Credentials", padding="12")
        cred_frame.pack(fill=tk.X, pady=(0, 10))

        # Email row
        ttk.Label(cred_frame, text="Gmail Address:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=4)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(cred_frame, textvariable=self.email_var, width=35)
        self.email_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=4)

        # Password row
        ttk.Label(cred_frame, text="App Password:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=4)
        self.pass_var = tk.StringVar()
        self.pass_entry = ttk.Entry(cred_frame, textvariable=self.pass_var, show="•", width=35)
        self.pass_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=4)

        self.show_pass_var = tk.BooleanVar(value=False)
        self.show_pass_btn = ttk.Checkbutton(
            cred_frame, text="Show", variable=self.show_pass_var, command=self._toggle_password_visibility
        )
        self.show_pass_btn.grid(row=1, column=2, sticky=tk.W, padx=5, pady=4)

        # Help note
        note_text = "Note: Requires a 16-character App Password (generate at Google Account > Security > App Passwords)."
        ttk.Label(cred_frame, text=note_text, font=("Helvetica", 9), foreground="#70757a", wraplength=550).grid(
            row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(2, 6)
        )

        # Connect / Disconnect Buttons
        btn_row = ttk.Frame(cred_frame)
        btn_row.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(4, 0))

        self.connect_btn = ttk.Button(
            btn_row, text="Connect & Fetch Folders", style="Primary.TButton", command=self.handle_connect
        )
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.disconnect_btn = ttk.Button(
            btn_row, text="Disconnect", command=self.handle_disconnect, state=tk.DISABLED
        )
        self.disconnect_btn.pack(side=tk.LEFT)

        # 2. Folder Operations Frame
        self.folder_frame = ttk.LabelFrame(main_container, text="2. Folder Management", padding="12")
        self.folder_frame.pack(fill=tk.X, pady=(0, 10))

        # Folder selector row
        folder_select_row = ttk.Frame(self.folder_frame)
        folder_select_row.pack(fill=tk.X, pady=4)

        ttk.Label(folder_select_row, text="Select Folder:").pack(side=tk.LEFT, padx=(0, 8))
        self.folder_var = tk.StringVar()
        self.folder_dropdown = ttk.Combobox(
            folder_select_row, textvariable=self.folder_var, state="disabled", width=36
        )
        self.folder_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        self.folder_dropdown.bind("<<ComboboxSelected>>", self.on_folder_selected)

        self.refresh_btn = ttk.Button(
            folder_select_row, text="↻ Refresh List", command=self.handle_refresh_folders, state=tk.DISABLED
        )
        self.refresh_btn.pack(side=tk.LEFT)

        # Folder Info Row
        self.folder_info_var = tk.StringVar(value="Connect your account to view available folders.")
        self.folder_info_label = ttk.Label(self.folder_frame, textvariable=self.folder_info_var, style="Status.TLabel")
        self.folder_info_label.pack(anchor=tk.W, pady=(4, 8))

        # Action Buttons row
        action_btn_row = ttk.Frame(self.folder_frame)
        action_btn_row.pack(fill=tk.X, pady=4)

        self.check_count_btn = ttk.Button(
            action_btn_row, text="🔍 Check Email Count", command=self.handle_check_count, state=tk.DISABLED
        )
        self.check_count_btn.pack(side=tk.LEFT, padx=(0, 12))

        self.delete_btn = ttk.Button(
            action_btn_row,
            text="🗑 Delete All Emails in Selected Folder",
            style="Danger.TButton",
            command=self.handle_delete_emails,
            state=tk.DISABLED,
        )
        self.delete_btn.pack(side=tk.LEFT)

        # 3. Activity Log & Progress Frame
        log_frame = ttk.LabelFrame(main_container, text="3. Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(log_frame, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=("Courier", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_config("INFO", foreground="#1a73e8")
        self.log_text.tag_config("SUCCESS", foreground="#1e8e3e")
        self.log_text.tag_config("WARNING", foreground="#f29900")
        self.log_text.tag_config("ERROR", foreground="#d93025")
        self.log_text.tag_config("TIMESTAMP", foreground="#80868b")

        # Bottom Bar
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Ready. Enter credentials and click 'Connect & Fetch Folders'.")
        ttk.Label(bottom_frame, textvariable=self.status_var, font=("Helvetica", 9, "italic")).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )

        ttk.Button(bottom_frame, text="Clear Log", command=self.clear_log).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(bottom_frame, text="Exit", command=self.on_close).pack(side=tk.RIGHT)

        self.log("Welcome to Gmail Folder Email Cleaner.", "INFO")
        self.log("Enter your credentials above to begin.", "INFO")

    def _toggle_password_visibility(self):
        if self.show_pass_var.get():
            self.pass_entry.config(show="")
            self.show_pass_btn.config(text="Hide")
        else:
            self.pass_entry.config(show="•")
            self.show_pass_btn.config(text="Show")

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("[%H:%M:%S] ")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, timestamp, "TIMESTAMP")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_busy(self, busy, status_msg=""):
        self.is_busy = busy
        if busy:
            self.progress_bar.start(10)
            if status_msg:
                self.status_var.set(status_msg)
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.check_count_btn.config(state=tk.DISABLED)
            self.delete_btn.config(state=tk.DISABLED)
            self.refresh_btn.config(state=tk.DISABLED)
            self.folder_dropdown.config(state="disabled")
        else:
            self.progress_bar.stop()
            if status_msg:
                self.status_var.set(status_msg)
            if self.is_connected:
                self.disconnect_btn.config(state=tk.NORMAL)
                self.refresh_btn.config(state=tk.NORMAL)
                self.folder_dropdown.config(state="readonly")
                if self.folder_var.get():
                    self.check_count_btn.config(state=tk.NORMAL)
                    self.delete_btn.config(state=tk.NORMAL)
            else:
                self.connect_btn.config(state=tk.NORMAL)
                self.disconnect_btn.config(state=tk.DISABLED)
                self.check_count_btn.config(state=tk.DISABLED)
                self.delete_btn.config(state=tk.DISABLED)
                self.refresh_btn.config(state=tk.DISABLED)
                self.folder_dropdown.config(state="disabled")

    def handle_connect(self):
        email_address = self.email_var.get().strip()
        app_password = self.pass_var.get().strip().replace(" ", "")

        if not email_address or "@" not in email_address:
            messagebox.showerror("Invalid Input", "Please enter a valid Gmail address.")
            return

        if not app_password:
            messagebox.showerror("Invalid Input", "Please enter your 16-character Gmail App Password.")
            return

        self._set_busy(True, "Connecting to Gmail...")
        self.log(f"Connecting to {IMAP_SERVER}...", "INFO")

        def worker():
            try:
                mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
                self.root.after(0, lambda: self.log("Authenticating...", "INFO"))
                mail.login(email_address, app_password)

                self.mail = mail
                self.is_connected = True
                self.root.after(0, lambda: self.log("Login successful!", "SUCCESS"))

                # Fetch folders
                self.root.after(0, lambda: self.log("Fetching available folders...", "INFO"))
                folders = parse_selectable_folders(self.mail)

                def on_success():
                    self.folders = folders
                    self.folder_dropdown["values"] = self.folders
                    self.email_entry.config(state=tk.DISABLED)
                    self.pass_entry.config(state=tk.DISABLED)
                    self.show_pass_btn.config(state=tk.DISABLED)
                    self._set_busy(False, f"Connected as {email_address}")

                    if self.folders:
                        self.folder_var.set(self.folders[0])
                        self.on_folder_selected()
                        self.log(f"Found {len(self.folders)} selectable folders.", "SUCCESS")
                    else:
                        self.folder_info_var.set("No selectable folders found.")
                        self.log("No selectable folders found.", "WARNING")

                self.root.after(0, on_success)

            except imaplib.IMAP4.error as e:
                err_msg = str(e)
                def on_imap_err():
                    self._set_busy(False, "Authentication failed.")
                    self.log(f"IMAP Error: {err_msg}", "ERROR")
                    messagebox.showerror(
                        "Login Failed",
                        f"Could not log in to Gmail:\n{err_msg}\n\n"
                        "Tips:\n"
                        "1. Ensure 2-Step Verification is turned on.\n"
                        "2. Use a generated 16-character App Password.\n"
                        "3. Verify IMAP is enabled in Gmail settings.",
                    )
                self.root.after(0, on_imap_err)
            except Exception as e:
                err_msg = str(e)
                def on_general_err():
                    self._set_busy(False, "Connection error.")
                    self.log(f"Connection Error: {err_msg}", "ERROR")
                    messagebox.showerror("Error", f"Failed to connect:\n{err_msg}")
                self.root.after(0, on_general_err)

        threading.Thread(target=worker, daemon=True).start()

    def handle_disconnect(self):
        if not self.is_connected:
            return

        self._set_busy(True, "Disconnecting...")
        self.log("Disconnecting from Gmail...", "INFO")

        def worker():
            if self.mail:
                try:
                    self.mail.close()
                except Exception:
                    pass
                try:
                    self.mail.logout()
                except Exception:
                    pass
                self.mail = None

            def on_done():
                self.is_connected = False
                self.folders = []
                self.folder_dropdown["values"] = []
                self.folder_var.set("")
                self.selected_folder_count = None
                self.folder_info_var.set("Connect your account to view available folders.")
                self.email_entry.config(state=tk.NORMAL)
                self.pass_entry.config(state=tk.NORMAL)
                self.show_pass_btn.config(state=tk.NORMAL)
                self._set_busy(False, "Disconnected.")
                self.log("Disconnected successfully.", "INFO")

            self.root.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def handle_refresh_folders(self):
        if not self.is_connected or not self.mail:
            return

        self._set_busy(True, "Refreshing folders...")
        self.log("Refreshing folder list...", "INFO")

        def worker():
            try:
                folders = parse_selectable_folders(self.mail)
                def on_done():
                    self.folders = folders
                    self.folder_dropdown["values"] = self.folders
                    self._set_busy(False, "Folders refreshed.")
                    self.log(f"Refreshed: {len(self.folders)} folders available.", "SUCCESS")
                    if self.folders and not self.folder_var.get():
                        self.folder_var.set(self.folders[0])
                        self.on_folder_selected()
                self.root.after(0, on_done)
            except Exception as e:
                err_msg = str(e)
                def on_err():
                    self._set_busy(False, "Failed to refresh folders.")
                    self.log(f"Error refreshing folders: {err_msg}", "ERROR")
                self.root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def on_folder_selected(self, event=None):
        selected_folder = self.folder_var.get()
        if not selected_folder:
            return

        self.selected_folder_count = None
        self.folder_info_var.set(f"Selected folder: '{selected_folder}' — Click 'Check Email Count' to inspect.")
        self.check_count_btn.config(state=tk.NORMAL)
        self.delete_btn.config(state=tk.NORMAL)

    def handle_check_count(self):
        selected_folder = self.folder_var.get()
        if not selected_folder or not self.mail:
            return

        self._set_busy(True, f"Checking '{selected_folder}'...")
        self.log(f"Inspecting folder '{selected_folder}'...", "INFO")

        def worker():
            try:
                status, _ = self.mail.select(f'"{selected_folder}"')
                if status != "OK":
                    raise RuntimeError(f"Could not select folder '{selected_folder}'.")

                status, search_data = self.mail.search(None, "ALL")
                if status != "OK":
                    raise RuntimeError("Failed to retrieve messages.")

                message_ids = search_data[0].split()
                count = len(message_ids)

                try:
                    self.mail.close()
                except Exception:
                    pass

                def on_done():
                    self.selected_folder_count = count
                    self.folder_info_var.set(f"Folder '{selected_folder}' contains {count} email(s).")
                    self.log(f"Folder '{selected_folder}' contains {count} email(s).", "INFO")
                    self._set_busy(False, "Ready.")
                self.root.after(0, on_done)

            except Exception as e:
                err_msg = str(e)
                def on_err():
                    self._set_busy(False, "Error checking folder.")
                    self.log(f"Error: {err_msg}", "ERROR")
                    messagebox.showerror("Error", err_msg)
                self.root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def handle_delete_emails(self):
        selected_folder = self.folder_var.get()
        if not selected_folder or not self.mail:
            messagebox.showwarning("No Folder Selected", "Please select a folder first.")
            return

        self._set_busy(True, f"Preparing deletion for '{selected_folder}'...")

        def worker():
            try:
                status, _ = self.mail.select(f'"{selected_folder}"')
                if status != "OK":
                    raise RuntimeError(f"Could not select folder '{selected_folder}'.")

                status, search_data = self.mail.search(None, "ALL")
                if status != "OK":
                    raise RuntimeError("Failed to retrieve messages.")

                message_ids = search_data[0].split()
                count = len(message_ids)

                def prompt_confirmation():
                    if count == 0:
                        self._set_busy(False, "Folder is empty.")
                        self.log(f"The folder '{selected_folder}' is already empty! Nothing to delete.", "WARNING")
                        self._prompt_next_action(
                            f"The folder '{selected_folder}' is already empty!\n\n"
                            "Do you want to delete any other folder, or exit?"
                        )
                        return

                    confirm = messagebox.askyesno(
                        "Confirm Permanent Deletion",
                        f"WARNING: Are you sure you want to permanently delete ALL {count} email(s) from '{selected_folder}'?\n\n"
                        "This operation CANNOT be undone.",
                        icon="warning",
                    )

                    if not confirm:
                        self.log(f"Deletion cancelled for '{selected_folder}'. No emails were deleted.", "WARNING")
                        try:
                            self.mail.close()
                        except Exception:
                            pass
                        self._set_busy(False, "Operation cancelled.")
                        self._prompt_next_action("Operation was cancelled.\n\nDo you want to delete any other folder, or exit?")
                        return

                    # Proceed with deletion in background
                    self._execute_deletion(selected_folder, message_ids, count)

                self.root.after(0, prompt_confirmation)

            except Exception as e:
                err_msg = str(e)
                def on_err():
                    self._set_busy(False, "Error reading folder.")
                    self.log(f"Error: {err_msg}", "ERROR")
                    messagebox.showerror("Error", err_msg)
                self.root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def _execute_deletion(self, folder_name, message_ids, count):
        self._set_busy(True, f"Deleting {count} email(s) from '{folder_name}'...")
        self.log(f"Marking {count} emails for deletion in '{folder_name}'...", "INFO")

        def worker():
            try:
                id_batch = b",".join(message_ids)
                self.mail.store(id_batch.decode("ascii"), "+FLAGS", "\\Deleted")

                self.root.after(0, lambda: self.log(f"Expunging '{folder_name}'...", "INFO"))
                self.mail.expunge()

                try:
                    self.mail.close()
                except Exception:
                    pass

                def on_success():
                    self._set_busy(False, "Deletion complete.")
                    self.log(f"Success! Successfully deleted {count} email(s) from '{folder_name}'.", "SUCCESS")
                    self.folder_info_var.set(f"Folder '{folder_name}' is now empty (deleted {count} emails).")

                    # Ask user if they want to delete any other folder or exit
                    self._prompt_next_action(
                        f"Successfully deleted {count} email(s) from '{folder_name}'!\n\n"
                        "Do you want to delete any other folder, or exit?"
                    )

                self.root.after(0, on_success)

            except Exception as e:
                err_msg = str(e)
                def on_err():
                    self._set_busy(False, "Error deleting emails.")
                    self.log(f"Error during deletion: {err_msg}", "ERROR")
                    messagebox.showerror("Deletion Error", f"Failed to delete emails:\n{err_msg}")
                self.root.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def _prompt_next_action(self, question_text):
        """
        Asks user if they want to delete another folder or exit.
        Yes -> stays in the app and focuses folder selection.
        No -> disconnects and exits cleanly.
        """
        answer = messagebox.askyesno(
            "Next Operation",
            f"{question_text}\n\n• Click 'Yes' to choose another folder.\n• Click 'No' to exit the application.",
        )
        if answer:
            self.folder_dropdown.focus_set()
            self.status_var.set("Select another folder from the dropdown to continue.")
        else:
            self.on_close()

    def on_close(self):
        if self.is_connected and self.mail:
            try:
                self.mail.close()
            except Exception:
                pass
            try:
                self.mail.logout()
            except Exception:
                pass
            self.mail = None
        self.root.destroy()


def main():
    root = tk.Tk()
    app = EmailCleanerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
