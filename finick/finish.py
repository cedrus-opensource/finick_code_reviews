#!/usr/bin/env python

from finicky.basics import prelaunch_checklist_close

import os


"""
there is a possibility that the resulting 'forefront' will not be a commit that
produces a working build (on all platforms) when checked out.
We need a contingency plan on the ZERO branch for when that happens.
In that case the tagged zero-forefront should not advance.
"""

def finish_session():

    prelaunch_checklist_close( os.path.basename(__file__) )

    # reviews file integrity check.
    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info

    # assignments file integrity check.

    # handle reverts.
    # merge assignment results into reviews DB file
    # mark ##__forefront__## position in reviews file

    # assignments file should be empty

    # commit session-end message
    # push all to origin reviews branch
    # push whatever possible to zero branch
    # send email (email to remind todo items. todo items past certain date?)


finish_session()
