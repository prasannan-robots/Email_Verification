"""Email address checks: syntax, mail domain (DNS) and SMTP mailbox probe."""

import re
import smtplib
import socket
import uuid

import dns.exception
import dns.resolver

# Practical syntax check: letters (any case), digits and the common
# punctuation used in real addresses, including plus-addressing.
STRICT_PATTERN = re.compile(
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*\.[a-z]{2,}$",
    re.IGNORECASE,
)

RFC_PATTERN = re.compile(
    r'^(?!\.)("([^"\r\\]|\\["\r\\])*"|'
    r"([-a-z0-9!#$%&'*+/=?^_`{|}~]|(?<!\.)\.)*)(?<!\.)"
    r"@[a-z0-9][\w\.-]*[a-z0-9]\.[a-z][a-z\.]*[a-z]$",
    re.IGNORECASE,
)


class Email_Verifier:
    def __init__(self, input_email, from_address=None, timeout=10):
        self.input_email = (input_email or "").strip()
        # Empty sender = the SMTP null reverse-path "<>", which servers accept
        # for probes; the old default (None) made every SMTP check fail.
        self.from_address = from_address or ""
        self.timeout = timeout
        self.mxRecord = None
        # Human-readable reason for the most recent failed/unknown check.
        self.last_reason = ""

    @property
    def domain(self):
        return self.input_email.rsplit("@", 1)[-1].lower() if "@" in self.input_email else ""

    def check_regex(self, input_email=None):
        """Practical syntax check (case-insensitive, allows +tags)."""
        email = (input_email if input_email is not None else self.input_email).strip()
        return len(email) <= 254 and STRICT_PATTERN.match(email) is not None

    def check_regex_rfc(self, input_email=None):
        """Looser check following RFC 5322 (quoted local parts etc.)."""
        email = (input_email if input_email is not None else self.input_email).strip()
        return len(email) <= 254 and RFC_PATTERN.match(email) is not None

    def mail_hosts(self, domain=None):
        """Mail servers for the domain, best (lowest preference) first.

        Falls back to the domain itself when it has no MX but has an address
        record (the "implicit MX" rule in RFC 5321).
        """
        domain = domain or self.domain
        if not domain:
            self.last_reason = "No domain in the address."
            return []
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=self.timeout)
            records = sorted(answers, key=lambda r: r.preference)
            hosts = [str(r.exchange).rstrip(".") for r in records if str(r.exchange) not in ("", ".")]
            if hosts:
                return hosts
            self.last_reason = f"{domain} does not accept email (null MX)."
            return []
        except dns.resolver.NXDOMAIN:
            self.last_reason = f"{domain} does not exist."
            return []
        except dns.resolver.NoAnswer:
            for record_type in ("A", "AAAA"):
                try:
                    dns.resolver.resolve(domain, record_type, lifetime=self.timeout)
                    return [domain]
                except dns.exception.DNSException:
                    continue
            self.last_reason = f"{domain} has no mail server."
            return []
        except dns.exception.DNSException as error:  # timeouts, no nameservers...
            self.last_reason = f"DNS lookup failed for {domain}: {error.__class__.__name__}."
            return []

    def check_domain(self, input_email=None):
        """True if the address's domain can receive mail."""
        if input_email is not None:
            self.input_email = input_email.strip()
        hosts = self.mail_hosts()
        self.mxRecord = hosts[0] if hosts else None
        return bool(hosts)

    def _rcpt(self, host, address):
        server = smtplib.SMTP(timeout=self.timeout)
        try:
            server.connect(host, 25)
            server.ehlo_or_helo_if_needed()
            server.mail(self.from_address)
            code, _ = server.rcpt(address)
            return code
        finally:
            try:
                server.quit()
            except smtplib.SMTPException:
                pass

    def verify_email(self, from_address=None, input_email=None):
        """Asks the domain's mail server whether the mailbox exists.

        Returns True (accepted), False (rejected) or None (can't tell: the
        server accepts every address, or it couldn't be reached - outbound
        port 25 is blocked on many home and cloud networks).
        """
        if from_address is not None:
            self.from_address = from_address
        if input_email is not None:
            self.input_email = input_email.strip()
        if not self.mxRecord and not self.check_domain():
            return False
        try:
            code = self._rcpt(self.mxRecord, self.input_email)
            if code != 250 and code != 251:
                self.last_reason = f"The mail server rejected this address (code {code})."
                return False
            # A server that also accepts a random address accepts everything.
            fake = f"no-such-user-{uuid.uuid4().hex[:12]}@{self.domain}"
            if self._rcpt(self.mxRecord, fake) in (250, 251):
                self.last_reason = "The domain accepts every address (catch-all), so the mailbox can't be confirmed."
                return None
            return True
        except (OSError, socket.timeout, smtplib.SMTPException) as error:
            self.last_reason = (
                f"Couldn't talk to {self.mxRecord} on port 25 ({error.__class__.__name__}). "
                "Many networks block outbound port 25."
            )
            return None
