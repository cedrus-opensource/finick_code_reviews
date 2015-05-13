#!/usr/bin/env python

from finicky.basics import prelaunch_checklist_open
from finicky.gitting import git_establish_session_readiness

import os





def start_session():

    # need to retrieve some kind of 'config object'
    finick_config = prelaunch_checklist_open( os.path.basename(__file__) )

    if False == finick_config.is_ok:
        raise Exception("unable to parse the config/ini file")


    # can we pull/merge all from origin?
    git_establish_session_readiness()

    # reviews file integrity check.
    # upgrade file format if needed.
    # purge older, completed data
    # add new stuff to forward end of file (last line should always be file version info).

    # generate assignments for this session.
    # emit a remind message about todo items
    # if there are no assignments for whoami, then we are done! (we can still commit changes to DB file)





start_session()

