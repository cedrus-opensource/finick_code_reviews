#!/usr/bin/env python

from __future__ import print_function  # if you want to: print ( 'what', 'is', 'this' )
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.api import (
    prelaunch_checklist_open, _, finick_db_integrity_check_open,
    finick_preopen_session, finick_open_session,
    finick_close_session_nothing_to_review, finick_create_charts)
from finicky.gitting import git_establish_session_readiness_start
from finicky.error import FinickError

import os


def start_session():

    finick_config = prelaunch_checklist_open(os.path.basename(__file__))

    if False == finick_config.is_ok:
        raise FinickError("unable to parse the config/ini file")

    # can we pull/merge all from origin?
    if True != git_establish_session_readiness_start(finick_config):
        raise FinickError("unable to establish git readiness")

    db_handle = finick_db_integrity_check_open(finick_config)

    if None != db_handle:
        # return value is a RowPrinterForSessionStart
        assignments = finick_preopen_session(finick_config, db_handle)

        # if you do not like seeing your reminders when running --draw-charts, then
        # you might feel inclined to move this line (delete it from here).
        # however, that might break using the '-t' flag (to print someone else's todos),
        # and/or it might at a minimum break being able to use -t with --draw-charts at the same time.
        # you have been advised.
        assignments.print_reminders()

        if finick_config.opt_charts:
            finick_create_charts(finick_config, db_handle)
            # we flush db back to disk, because we want on-disk content to match what got charted
            finick_close_session_nothing_to_review(finick_config, db_handle)
        elif finick_config.opt_onlytodos:
            pass  # running with '-t' flag. print todos (print_reminders called above), then done!
        else:

            if assignments.nothing_to_review():
                # if there are no assignments for whoami, then we are done! (we can still commit changes to DB file)
                finick_close_session_nothing_to_review(finick_config,
                                                       db_handle)
            else:
                assignments.print_assignments()
                finick_open_session(finick_config, db_handle)


start_session()

#print ( _('test of gettext translation') )
