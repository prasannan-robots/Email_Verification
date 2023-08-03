import re
import dns.resolver
import smtplib

class Email_Verifier:
    def __init__(self,input_email,from_address=None):
        self.input_email = input_email
        self.from_address = from_address

    # Checks for simple regex
    def check_regex(self,input_email=None):
        if input_email == None:
            input_email = self.input_email
        regex = '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,})$'
        match = re.match(regex, input_email)
        if match == None:
            return False
        else:
            return True
    
    # Checks with rfc rated regex
    def check_regex_rfc(self,input_email=None):
        if input_email == None:
            input_email = self.input_email
        pattern = r'^(?!\.)(""([^""\r\\]|\\[""\r\\])*""|' \
              r'([-a-z0-9!#$%&\'*+/=?^_`{|}~]|(?<!\.)\.)*)(?<!\.)' \
              r'@[a-z0-9][\w\.-]*[a-z0-9]\.[a-z][a-z\.]*[a-z]$'

        regex = re.compile(pattern, re.IGNORECASE)
        match = regex.match(input_email)
        if match is None:
            return False
        else:
            return True
        
    def check_domain(self,input_email=None):
        if input_email == None:
            input_email = self.input_email

        domain = input_email.rsplit("@")[-1]
        try:
            records = dns.resolver.resolve(domain, 'MX')
            mxRecord = records[0].exchange
            mxRecord = str(mxRecord)
            
            self.mxRecord = mxRecord
            return True
        except dns.resolver.NXDOMAIN:
            return False
        
    def verify_email(self,from_address=None, input_email=None):
        if from_address == None:
            from_address = self.from_address
        if input_email == None:
            input_email = self.input_email
        try:
            server = smtplib.SMTP(timeout=10)  # Set a timeout for the connection
            server.set_debuglevel(0)

            # SMTP Conversation
            server.connect(self.mxRecord)
            server.helo(server.local_hostname)
            server.mail(from_address)
            code, message = server.rcpt(str(input_email))
            server.quit()

            if code == 250:
                return True
            else:
                return False
        except smtplib.SMTPConnectError as e:
            print(f"Failed to connect to the mail server: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            print(f"Disconnected from the mail server unexpectedly: {e}")
            return False
        except smtplib.SMTPException as e:
            print(f"Error occurred during the SMTP conversation: {e}")
            return False

            

