from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import AssertType_DbRow
from finicky.parse_config import AssertType_FinickConfig
from finicky.error import FinickError

import datetime
from io import open


class RowPrinterForSessionStart(object):
    def __init__(self, finick_config, assignments, todos_n_pleases):
        self.__finick_config = finick_config
        self.__assignmentlist = assignments
        self.__todoslist = todos_n_pleases

        AssertType_FinickConfig(self.__finick_config)

        for a in self.__assignmentlist:
            AssertType_DbRow(a)

        for t in self.__todoslist:
            AssertType_DbRow(t)

    def nothing_to_review(self):
        return len(self.__assignmentlist) == 0

    def print_reminders(self):
        if len(self.__todoslist) <= 0:
            print('No TODOS created. There are ZERO reminders to print into ' +
                  self.__finick_config.get_todos_file_fullname_fullpath() +
                  ' (so the file was not created).')

        else:
            t_list = []
            p_list = []

            # in the RowPrinterForSessionStart ctor, we asserted AssertType_DbRow on all in __todoslist
            for i in self.__todoslist:
                if i.row_type == i.TYPE_TODO:
                    t_list.append(i)
                elif i.row_type == i.TYPE_PLS:
                    p_list.append(i)
                else:
                    raise FinickError(
                        'Unknown row type in list of reminders. Expected only TODO or PLS.')

            o = ''
            # using a 'contrived' if-test so that the 'print's all line up
            if True:
                o += '\n\n'
                o += '    ---- Your Friendly Reminders: ----\n\n'

            if len(t_list) > 0:
                o += '    Must Fix:\n\n'

            for t in t_list:
                ch = t.commithash
                cm = t.comment
                o += '      commit ' + t.commithash + ', ' + t.comment + '\n'

            if len(t_list) > 0:
                o += '\n'
                o += '    Requested kindly:\n\n'

            for p in p_list:
                ch = p.commithash
                cm = p.comment
                o += '      commit ' + p.commithash + ', ' + p.comment + '\n'

            # using a 'contrived' if-test so that the 'print's all line up
            if True:
                o += '\n'

            todos_file = self.__finick_config.get_todos_file_fullname_fullpath()

            # show the user the text right away (via the print function), and then also save to a file.
            print(o)
            print('(The above-listed TODO reminders have also been saved to \''
                  + todos_file + '\'.)\n')

            # mode 'w' will TRUNCATE the file
            text_file = open(todos_file, encoding='utf-8', mode='w')

            date_heading = '' + datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            text_file.write(date_heading)
            text_file.write(o)

            text_file.close()

    def print_assignments(self):
        assign_file = self.__finick_config.get_assign_file_fullname_fullpath()

        # mode 'w' will TRUNCATE the file
        text_file = open(assign_file, encoding='utf-8', mode='w')

        # in the RowPrinterForSessionStart ctor, we asserted AssertType_DbRow on all in __assignmentlist
        for r in self.__assignmentlist:
            r.write_to_diskfile(text_file)

        text_file.close()
