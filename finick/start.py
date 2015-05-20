#!/usr/bin/env python

from __future__ import print_function  # if you want to: print ( 'what', 'is', 'this' )
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.basics import prelaunch_checklist_open, _
from finicky.gitting import git_establish_session_readiness_start
from finicky.db_file import db_integrity_check_open, db_preopen_session, db_open_session, db_close_session_nothing_to_review
from finicky.error import FinickError

import os


def start_session():

    finick_config = prelaunch_checklist_open(os.path.basename(__file__))

    if False == finick_config.is_ok:
        raise FinickError("unable to parse the config/ini file")

    # can we pull/merge all from origin?
    if True != git_establish_session_readiness_start(finick_config):
        raise FinickError("unable to establish git readiness")

    db_handle = db_integrity_check_open(finick_config)

    if None != db_handle:
        # return value is a SessionRowPrinter
        assignments = db_preopen_session(finick_config, db_handle)

        assignments.print_reminders()

        if assignments.nothing_to_review():
            # if there are no assignments for whoami, then we are done! (we can still commit changes to DB file)
            db_close_session_nothing_to_review(finick_config, db_handle)
        else:
            assignments.print_assignments()
            db_open_session(finick_config, db_handle)


start_session()

#print ( _('test of gettext translation') )
