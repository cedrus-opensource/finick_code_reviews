from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.parse_config import AssertType_FinickConfig
from finicky.error import FinickError

import smtplib


def send_the_sessionend_email(to_list, subject_line, email_body_text,
                              finick_config):

    AssertType_FinickConfig(finick_config)

    CC_LIST = [finick_config.reviewer]

    SERVER = finick_config.mailserver
    PORT = finick_config.mailport

    FROM = "team@acme.com"  # may end up in X-Google-Original-From
    TO = to_list

    SUBJECT = subject_line

    TEXT = email_body_text

    # Prepare actual message

    message = """\
From: %s
To: %s
CC: %s
Subject: %s

%s
    """ % (FROM, ", ".join(TO), ", ".join(CC_LIST), SUBJECT, TEXT)

    try:
        # class smtplib.SMTP([host[, port[, local_hostname[, timeout]]]])
        server = smtplib.SMTP(SERVER, PORT)

        server.ehlo()
        server.starttls()
        server.ehlo(
        )  # this line is apparently necessary on python 2.4 and 2.5, but not afterward.
        server.login(finick_config.maillogin, finick_config.mailpword)
        # important! you have to tell the server to send to the 'TO' list *and* the cc'ed folk:
        server.sendmail(FROM, TO + CC_LIST, message)
        server.quit()

    except:
        print('smtp stuff failed')
