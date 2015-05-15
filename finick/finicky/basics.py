
from __future__ import print_function
from __future__ import division # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

import finicky.parse_config
from finicky.error import FinickError

import glob
import gettext
import locale

# Set up message catalog access.
# Python-3.4.3//Tools/i18n/pygettext.py finick/finicky/*py *py finick/*py # to generate pot
# The hard-coded path is lame. This is a version 0.0 kind of thing.
# make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding locale folder
_t = gettext.translation('finick_code_review', './finick/locale', ['en_US']) #, fallback=True)
try:
    # for older python 2:
    _ = _t.ugettext
except AttributeError:
    _ = _t.gettext
"""
i probably will want to end up using the INSTALL-based way to get _, from here:
http://www.wefearchange.org/2012/06/the-right-way-to-internationalize-your.html
"""


def prelaunch_checklist_open( calling_filename ):
    return _prelaunch_checklist( calling_filename, True )

def prelaunch_checklist_close( calling_filename ):
    return _prelaunch_checklist( calling_filename, False )

def _prelaunch_checklist( calling_filename, is_session_starting ):

    # make sure this is called as finick/start.py (use os.sep). this way we can count on CWD for finding config
    # config integrity check. (older than start of session to prevent mid-session reconfig).
    # are we on the right branch? (check this when False==is_session_starting. on start we will check out the branch)
    # do a git-whoami and make sure we have an email

    all_cwd_inis = glob.glob('*ini')

    if len(all_cwd_inis) != 1:
        # eventually we will allow the INI file to be passed as an argument
        raise FinickError("you must have exactly one (and only one) ini file in the CWD")

    return finicky.parse_config.FinickConfig( all_cwd_inis[0] )

