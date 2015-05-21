#!/usr/bin/env python

from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.api import (prelaunch_checklist_close,
                         finick_db_integrity_check_close,
                         finick_db_merge_with_completed_assignments)
from finicky.gitting import git_establish_session_readiness_end

import os
"""
there is a possibility that the resulting 'forefront' will not be a commit that
produces a working build (on all platforms) when checked out.
We need a contingency plan on the ZERO branch for when that happens.
In that case the tagged zero-forefront should not advance.
"""


def finish_session():

    finick_config = prelaunch_checklist_close(os.path.basename(__file__))

    if False == finick_config.is_ok:
        raise FinickError("unable to parse the config/ini file")

    # basic sanity checks for being in the right repo and right branch, etc:
    if True != git_establish_session_readiness_end(finick_config):
        raise FinickError("unable to establish git readiness")

    # is a session in progress?

    # reviews file integrity check.
    # reviews file should now be properly upgraded already.
    # first line in DB file should be file version info
    db_handle = finick_db_integrity_check_close(finick_config)

    if None != db_handle:
        # when the next call completes exception-free, it also closes the session:
        finick_db_merge_with_completed_assignments(finick_config, db_handle)


finish_session()
