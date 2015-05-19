from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import DbRow
from finicky.error import FinickError


class SessionRowPrinter(object):
    def __init__(self, finick_config, assignments, todos_n_pleases):
        self.__finick_config = finick_config
        self.__assignmentlist = assignments
        self.__todoslist = todos_n_pleases
