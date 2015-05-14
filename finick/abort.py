#!/usr/bin/env python

from finicky.basics import prelaunch_checklist_close
from finicky.db_file import db_integrity_check_close

import os


def abort_session():

    prelaunch_checklist_close( os.path.basename(__file__) )

    # is a session in progress?

    # reviews file integrity check.
    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info

    # assignments file should be empty

    # commit and push the abort message


abort_session()

