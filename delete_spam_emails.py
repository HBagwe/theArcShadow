import getpass
import imaplib
import re
import sys

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def get_available_folders(mail):
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
            # Exclude folders that cannot be selected directly (e.g., "[Gmail]" parent)
            if "\\Noselect" not in flags:
                folders.append(name)
        else:
            # Fallback parsing
            parts = decoded.split(' "/" ')
            if len(parts) == 2:
                name = parts[1].strip(' "')
                folders.append(name)

    return folders

def delete_emails_from_folder():
    """Terminal / CLI version of the email cleaner."""
    print("=" * 60)
    print("           Gmail Folder Email Cleaner (CLI Mode)")
    print("=" * 60)
    print("NOTE: Due to Google security policies, you must use an")
    print("      'App Password' rather than your regular password.")
    print("      Generate one at: https://myaccount.google.com/apppasswords")
    print("=" * 60)

    # 1. Ask user for Gmail address
    email_address = input("\nEnter your Gmail address: ").strip()
    if not email_address or "@" not in email_address:
        print("Error: Invalid email address.")
        sys.exit(1)

    # 2. Ask user for App Password securely (hidden input)
    app_password = getpass.getpass("Enter your 16-character Gmail App Password: ").strip().replace(" ", "")
    if not app_password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    mail = None
    try:
        print(f"\nConnecting to {IMAP_SERVER}...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

        print("Logging in...")
        mail.login(email_address, app_password)
        print("Login successful!")

        # 3. Retrieve available folders
        print("\nFetching available folders...")
        folders = get_available_folders(mail)
        if not folders:
            print("No selectable folders found.")
            return

        while True:
            print("\nAvailable Folders:")
            for idx, folder_name in enumerate(folders, start=1):
                print(f"  [{idx}] {folder_name}")

            # 4. Ask user which folder they want to clean
            while True:
                choice = input(f"\nSelect folder number (1-{len(folders)}) or enter folder name (or 'exit' to quit): ").strip()
                if choice.lower() in ("exit", "quit", "q"):
                    print("\nExiting. Thank you!")
                    return

                selected_folder = None
                if choice.isdigit():
                    folder_index = int(choice) - 1
                    if 0 <= folder_index < len(folders):
                        selected_folder = folders[folder_index]
                else:
                    for f in folders:
                        if f.lower() == choice.lower():
                            selected_folder = f
                            break

                if selected_folder:
                    break
                print("Invalid selection. Please choose a valid number, folder name, or 'exit'.")

            print(f"\nSelected folder: '{selected_folder}'")

            # 5. Select the chosen folder
            status, _ = mail.select(f'\"{selected_folder}\"')
            if status != "OK":
                print(f"Error: Could not select folder '{selected_folder}'.")
            else:
                # 6. Search for all emails in this folder
                status, search_data = mail.search(None, "ALL")
                if status != "OK":
                    print(f"Error searching for messages in '{selected_folder}'.")
                else:
                    message_ids = search_data[0].split()
                    total_messages = len(message_ids)

                    if total_messages == 0:
                        print(f"\nThe folder '{selected_folder}' is already empty! Nothing to delete.")
                    else:
                        print(f"\nFound {total_messages} email(s) in '{selected_folder}'.")

                        # 7. Confirmation prompt
                        confirm = input(
                            f"WARNING: Are you sure you want to permanently delete ALL {total_messages} email(s) from '{selected_folder}'? (y/N): "
                        ).strip().lower()

                        if confirm != "y":
                            print("Operation cancelled. No emails were deleted.")
                        else:
                            # 8. Mark messages as \\Deleted and expunge
                            print("Marking emails for deletion...")
                            id_batch = b",".join(message_ids)
                            mail.store(id_batch.decode("ascii"), "+FLAGS", "\\Deleted")

                            print("Expunging folder...")
                            mail.expunge()

                            print(f"\nSuccess! Successfully deleted {total_messages} email(s) from '{selected_folder}'.")

                # Close the mailbox so next selection starts clean
                try:
                    mail.close()
                except Exception:
                    pass

            # 9. Ask user if they want to delete any other folder or exit
            while True:
                next_action = input("\nDo you want to delete any other folder or exit? (y/n): ").strip().lower()
                if next_action in ("y", "yes"):
                    break
                elif next_action in ("n", "no", "exit", "quit", "q"):
                    print("\nExiting. Thank you!")
                    return
                else:
                    print("Invalid input. Please enter 'y' to delete another folder or 'n'/'exit' to exit.")

    except imaplib.IMAP4.error as e:
        print(f"\nIMAP Error: {e}")
        print("Tips:")
        print(" - Ensure 2-Step Verification is turned on on your Google account.")
        print(" - Verify you are using a generated 16-character App Password.")
        print(" - Ensure IMAP is enabled in Gmail Settings > 'Forwarding and POP/IMAP'.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if mail:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass


def main():
    if "--cli" in sys.argv:
        delete_emails_from_folder()
    else:
        try:
            from email_cleaner_gui import main as gui_main
            gui_main()
        except Exception as e:
            print(f"Notice: GUI could not be initialized ({e}). Falling back to CLI mode.\n")
            delete_emails_from_folder()


if __name__ == "__main__":
    main()
