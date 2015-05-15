#!/usr/bin/env python

from __future__ import print_function # if you want to: print ( 'what', 'is', 'this' )
from __future__ import division # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.basics import prelaunch_checklist_open, _
from finicky.gitting import git_establish_session_readiness
from finicky.db_file import db_integrity_check_open, db_open_session
from finicky.error import FinickError

import os





def start_session():

    # need to retrieve some kind of 'config object'
    finick_config = prelaunch_checklist_open( os.path.basename(__file__) )

    if False == finick_config.is_ok:
        raise FinickError("unable to parse the config/ini file")

    # can we pull/merge all from origin?
    if True != git_establish_session_readiness( finick_config ):
        raise FinickError("unable to establish git readiness")

    db_integrity_check_open( finick_config )

    db_open_session( finick_config )




start_session()

#print ( _('test of gettext translation') )

