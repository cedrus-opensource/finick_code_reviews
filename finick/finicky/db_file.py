
from __future__ import print_function
from __future__ import division # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.gitting
from finicky.error import FinickError
from finicky.basics import _

import os
from io import open

def db_integrity_check_open( finick_config ):

    _db_integrity_check( finick_config, False )

def db_integrity_check_close( finick_config ):

    # reviews file should now be properly upgraded already.
    # last line in DB file should be file version info
    _db_integrity_check( finick_config, True )


def _db_integrity_check( finick_config, session_is_closing ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )

    # before we check the content of the file, we should check whether it is known (committed) to git

    expected_db = finick_config.confdir + os.sep + finick_config.configname + '.txt'

    try:
        with open( expected_db, encoding='utf-8' ) as f:
            for line in f:
                print ( _('someline') )

    except:
        configfile = finick_config.confdir + os.sep + finick_config.configname
        err_msg = 'Missing or unreadable DB file. (Create an empty file for first use.) '
        err_msg += 'While using config \''+ configfile +'\', you must have the DB file \''+ expected_db +'\''
        raise FinickError( err_msg )



def db_open_session( finick_config ):

    finicky.parse_config.AssertType_FinickConfig( finick_config )

    # if we are starting one session, there must not be any other session in progress (even from other INI file) [job of git_establish_session_readiness]

    # upgrade file format if needed.
    # purge older, completed data
    # add new stuff to forward end of file (last line should always be file version info).

    # generate assignments for this session.
    # emit a reminder message about todo items
    # if there are no assignments for whoami, then we are done! (we can still commit changes to DB file)

