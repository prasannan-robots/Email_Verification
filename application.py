from verifier import Email_Verifier
import tkinter as tk
from tkinter import messagebox

class EmailVerifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Verifier")
        self.root.iconphoto(False, tk.PhotoImage(file='icon.png'))
        self.label_email = tk.Label(root, text="Enter an email address:")
        self.label_email.pack()

        self.entry_email = tk.Entry(root)
        self.entry_email.pack()

        
        self.Checkbutton_check_regex = tk.BooleanVar(value=True) 
        self.Checkbutton_check_regex_rfc = tk.BooleanVar(value=True)
        self.Checkbutton_check_domain = tk.BooleanVar(value=True)
        self.Checkbutton_verify_email = tk.BooleanVar(value=False)
        self.Button1 = tk.Checkbutton(root, text = "Strict Test", 
                      variable = self.Checkbutton_check_regex,
                       onvalue=True,
    offvalue=False,
                      height = 2,
                      width = 50)
        
        self.Button2 = tk.Checkbutton(root, text = "Test according to RFC guidelines",
                            variable = self.Checkbutton_check_regex_rfc,
                             onvalue=True,
    offvalue=False,
                            height = 2,
                            width = 50)
        
        self.Button3 = tk.Checkbutton(root, text = "Check whether the mail domain is available",
                            variable = self.Checkbutton_check_domain,
                            onvalue=True,
    offvalue=False,
                            height = 2,
                            width = 50)  
        self.Button4 = tk.Checkbutton(root, text = "Verify Email using smtplib",
                            variable = self.Checkbutton_verify_email,
                            onvalue=True,
    offvalue=False,
                            height = 2,
                            width = 50)  
            
          
        self.Button2.pack()  
        self.Button3.pack()
        self.Button1.pack()
        self.Button4.pack()

        self.button_check = tk.Button(root, text="Check", command=self.check_email)
        self.button_check.pack()

    def check_email(self):
        input_email = self.entry_email.get()
        email_verifier = Email_Verifier(input_email)
      
        # Check for simple regex
        if self.Checkbutton_check_regex.get():
            if not email_verifier.check_regex():
                messagebox.showinfo("Result", "Invalid email format (Strict Test).")
                return

        # Check with rfc rated regex
        if self.Checkbutton_check_regex_rfc.get():
            if not email_verifier.check_regex_rfc():
                messagebox.showinfo("Result", "Invalid email format (RFC rated regex check).")
                return

        # Check the domain
        if self.Checkbutton_check_domain.get():
            if not email_verifier.check_domain():
                messagebox.showinfo("Result", "Invalid domain in the email address.")
                return

        # # Verify the email address
        if self.Checkbutton_verify_email.get():
            try:
                output = email_verifier.verify_email()
            except Exception as e:
                messagebox.showinfo("Result", f"Error occurred in verify email {e}")
                return
            if not output:
                messagebox.showinfo("Result", "Email address could not be verified.")
                return

        messagebox.showinfo("Result", "Email address is valid and verified!")

if __name__ == "__main__":
    root = tk.Tk()
    app = EmailVerifierApp(root)
    root.mainloop()
