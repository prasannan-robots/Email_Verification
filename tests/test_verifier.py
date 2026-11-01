import os
import sys
from types import SimpleNamespace

import dns.resolver
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from verifier import Email_Verifier  # noqa: E402
from verifier import email as mod  # noqa: E402


@pytest.mark.parametrize("address", ["John@Gmail.com", "me+news@gmail.com", "a.b-c@sub.example.co.in", "x_y@example.org"])
def test_strict_accepts_common_valid_addresses(address):
    assert Email_Verifier(address).check_regex()


@pytest.mark.parametrize("address", ["plainaddress", "a@b", "a..b@example.com", ".a@example.com", "a@-example.com", "a b@example.com", ""])
def test_strict_rejects_invalid(address):
    assert not Email_Verifier(address).check_regex()


def test_rfc_allows_quoted_local_part():
    assert Email_Verifier('"john doe"@example.com').check_regex_rfc()
    assert not Email_Verifier("john@@example.com").check_regex_rfc()


def mx(*pairs):
    return [SimpleNamespace(preference=p, exchange=h) for p, h in pairs]


def test_picks_lowest_preference_mx(monkeypatch):
    monkeypatch.setattr(dns.resolver, "resolve", lambda d, t, lifetime=None: mx((20, "backup.mx."), (5, "primary.mx.")))
    v = Email_Verifier("a@example.com")
    assert v.check_domain() and v.mxRecord == "primary.mx"


def test_dns_errors_are_handled(monkeypatch):
    def boom(domain, rtype, lifetime=None):
        raise dns.resolver.LifetimeTimeout(timeout=1, errors=[])
    monkeypatch.setattr(dns.resolver, "resolve", boom)
    v = Email_Verifier("a@example.com")
    assert v.check_domain() is False and "DNS lookup failed" in v.last_reason


def test_implicit_mx_falls_back_to_a_record(monkeypatch):
    def resolve(domain, rtype, lifetime=None):
        if rtype == "MX":
            raise dns.resolver.NoAnswer()
        return ["93.184.216.34"]
    monkeypatch.setattr(dns.resolver, "resolve", resolve)
    v = Email_Verifier("a@example.com")
    assert v.check_domain() and v.mxRecord == "example.com"


class FakeSMTP:
    accepted = set()
    connect_error = None

    def __init__(self, timeout=None):
        self.sender = None

    def connect(self, host, port):
        if FakeSMTP.connect_error:
            raise FakeSMTP.connect_error

    def ehlo_or_helo_if_needed(self):
        pass

    def mail(self, sender):
        assert sender is not None  # None used to break every SMTP check
        self.sender = sender

    def rcpt(self, address):
        return (250 if address in FakeSMTP.accepted or "*" in FakeSMTP.accepted else 550), b""

    def quit(self):
        pass


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setattr(mod.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(dns.resolver, "resolve", lambda d, t, lifetime=None: mx((10, "mx.example.com.")))
    FakeSMTP.accepted, FakeSMTP.connect_error = set(), None
    return FakeSMTP


def test_smtp_verification_without_domain_check_or_sender(smtp):
    smtp.accepted = {"real@example.com"}
    assert Email_Verifier("real@example.com").verify_email() is True
    assert Email_Verifier("nobody@example.com").verify_email() is False


def test_catch_all_domains_are_unknown(smtp):
    smtp.accepted = {"*"}
    v = Email_Verifier("anything@example.com")
    assert v.verify_email() is None and "catch-all" in v.last_reason


def test_blocked_port_25_is_unknown_not_invalid(smtp):
    smtp.connect_error = TimeoutError("timed out")
    v = Email_Verifier("real@example.com")
    assert v.verify_email() is None and "port 25" in v.last_reason
