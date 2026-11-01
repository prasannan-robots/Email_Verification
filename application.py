"""Email Verifier - a small Tkinter app to check email addresses."""

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

from verifier import Email_Verifier

HERE = os.path.dirname(os.path.abspath(__file__))
BG, FG, MUTED, OK, BAD, WARN = "#0f1419", "#d7e1ea", "#7d8b99", "#3ddc84", "#ff6b6b", "#f4c95d"

CHECKS = [
    ("regex", "Strict format check", True),
    ("rfc", "Format according to RFC rules", True),
    ("domain", "Mail domain can receive email (DNS)", True),
    ("smtp", "Ask the mail server if the mailbox exists (SMTP)", False),
]


class EmailVerifierApp:
    def __init__(self, root):
        self.root = root
        self.results = queue.Queue()
        root.title("Email Verifier")
        root.configure(bg=BG)
        root.minsize(540, 560)
        try:
            root.iconphoto(False, tk.PhotoImage(file=os.path.join(HERE, "icon.png")))
        except tk.TclError:
            pass

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, fieldbackground="#1b232c", font=("Consolas", 11))
        style.configure("TCheckbutton", background=BG, foreground=FG)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("Accent.TButton", background="#2b7cff", foreground="white", padding=(16, 6))
        style.map("Accent.TButton", background=[("disabled", "#2a3440"), ("active", "#1f6ae0")])
        style.configure("Muted.TLabel", foreground=MUTED)

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Email Verifier", font=("Consolas", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Check an address before you send to it.", style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="Email address").pack(anchor="w")
        self.entry_email = ttk.Entry(frame, width=48)
        self.entry_email.pack(fill="x", pady=(2, 10))
        self.entry_email.bind("<Return>", lambda _e: self.check_email())
        self.entry_email.focus_set()

        self.options = {}
        for key, text, default in CHECKS:
            self.options[key] = tk.BooleanVar(value=default)
            ttk.Checkbutton(frame, text=text, variable=self.options[key]).pack(anchor="w", pady=1)

        ttk.Label(frame, text="Sender for the SMTP check (optional)", style="Muted.TLabel").pack(anchor="w", pady=(10, 0))
        self.entry_from = ttk.Entry(frame, width=48)
        self.entry_from.pack(fill="x", pady=(2, 12))

        self.button_check = ttk.Button(frame, text="Check", style="Accent.TButton", command=self.check_email)
        self.button_check.pack(anchor="w")

        self.output = tk.Text(frame, height=9, bg="#1b232c", fg=FG, relief="flat", wrap="word",
                              font=("Consolas", 11), padx=10, pady=8, highlightthickness=0)
        self.output.pack(fill="both", expand=True, pady=(14, 0))
        for tag, color in (("ok", OK), ("bad", BAD), ("warn", WARN), ("muted", MUTED)):
            self.output.tag_configure(tag, foreground=color)
        self.output.configure(state="disabled")

    def log(self, text, tag=None):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n", tag)
        self.output.see("end")
        self.output.configure(state="disabled")

    def check_email(self):
        email = self.entry_email.get().strip()
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        if not email:
            self.log("Enter an email address.", "warn")
            return
        options = {key: var.get() for key, var in self.options.items()}
        self.button_check.state(["disabled"])
        self.log(f"Checking {email} …", "muted")
        # DNS and SMTP can take several seconds: run them off the UI thread.
        threading.Thread(target=self._run_checks, args=(email, self.entry_from.get().strip(), options), daemon=True).start()
        self.root.after(100, self._poll)

    def _run_checks(self, email, sender, options):
        verifier = Email_Verifier(email, from_address=sender)
        steps = [
            ("regex", "Format (strict)", verifier.check_regex),
            ("rfc", "Format (RFC)", verifier.check_regex_rfc),
            ("domain", "Mail domain", verifier.check_domain),
            ("smtp", "Mailbox (SMTP)", verifier.verify_email),
        ]
        for key, label, check in steps:
            if not options[key]:
                continue
            verifier.last_reason = ""
            try:
                outcome = check()
            except Exception as error:  # never let a check kill the app
                outcome, verifier.last_reason = None, f"Unexpected error: {error}"
            self.results.put((label, outcome, verifier.last_reason))
            if outcome is False:
                break
        self.results.put(None)

    def _poll(self):
        try:
            while True:
                item = self.results.get_nowait()
                if item is None:
                    self.button_check.state(["!disabled"])
                    return
                label, outcome, reason = item
                if outcome is True:
                    self.log(f"✓ {label}", "ok")
                elif outcome is False:
                    self.log(f"✗ {label}" + (f": {reason}" if reason else ""), "bad")
                else:
                    self.log(f"? {label}: {reason}", "warn")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


if __name__ == "__main__":
    root = tk.Tk()
    EmailVerifierApp(root)
    root.mainloop()
