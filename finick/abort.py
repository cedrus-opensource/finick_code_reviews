#!/usr/bin/env python



def abort_session():
    # config integrity check. (older than the open-session commit)
    # are we on the right branch?
    # is a session in progress?
    # does a git whoami succeed?

    # reviews file integrity check.
    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info

    # assignments file should be empty

    # commit and push the abort message
