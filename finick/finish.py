#!/usr/bin/env python

"""
there is a possibility that the resulting 'forefront' will not be a commit that
produces a working build (on all platforms) when checked out.
We need a contingency plan on the ZERO branch for when that happens.
In that case the tagged zero-forefront should not advance.
"""

def finish_session():
    # config integrity check. (older than the open-session commit)
    # are we on the right branch?
    # is a session in progress?
    # does a git whoami succeed?

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


