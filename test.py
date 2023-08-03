from verifier import Email_Verifier

verifier = Email_Verifier('prasannanatarajan3595@gmail.com')
print(verifier.check_regex())
print(verifier.check_regex_rfc())

