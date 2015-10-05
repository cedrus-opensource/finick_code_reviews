from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.db_row import AssertType_DbRow, DbRow
from finicky.parse_config import AssertType_FinickConfig
import finicky.email
from finicky.error import FinickError

import datetime
from io import open
import os


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
                  self.__finick_config.get_todos_file_fullname_fullpath(
                  ) + ' (so the file was not created).')

        else:
            t_list = []
            p_list = []
            t_list_hf = []  # 'hf' means there is a 'hopeful FIXD' awaiting review
            p_list_hf = []  # 'hf' means there is a 'hopeful FIXD' awaiting review

            # in the RowPrinterForSessionStart ctor, we asserted AssertType_DbRow on all in __todoslist
            for i in self.__todoslist:
                is_hopefix = False
                try:
                    if True == i.has_pending_hopefix:
                        is_hopefix = True
                except AttributeError:
                    raise FinickError(
                        'Code assumption violated. Something should have put a has_pending_hopefix attribute on this row by now.')

                if i.row_type == i.TYPE_TODO:
                    if is_hopefix:
                        t_list_hf.append(i)
                    else:
                        t_list.append(i)
                elif i.row_type == i.TYPE_PLS:
                    if is_hopefix:
                        p_list_hf.append(i)
                    else:
                        p_list.append(i)
                else:
                    raise FinickError(
                        'Unknown row type in list of reminders. Expected only TODO or PLS.')

            hf_tag_str = '[hope-fixed]'
            o = ''
            # using a 'contrived' if-test so that the 'print's all line up
            if True:
                o += '\n\n'
                o += '    ---- Your Friendly Reminders: ----\n\n'
                o += '        (Note: \'' + hf_tag_str + '\' means a proposed fix has already been committed, but awaits review.)\n\n'

            if len(t_list) > 0:
                o += '    Must Fix:\n\n'

            for t in t_list:
                o += '      commit ' + t.commithash + ', ' + t.comment + '\n'

            for t in t_list_hf:
                o += '      ' + hf_tag_str + ' commit ' + t.commithash + ', ' + t.comment + '\n'

            if len(t_list) > 0:
                o += '\n'
                o += '    Requested kindly:\n\n'

            for p in p_list:
                o += '      commit ' + p.commithash + ', ' + p.comment + '\n'

            for p in p_list_hf:
                o += '      ' + hf_tag_str + ' commit ' + p.commithash + ', ' + p.comment + '\n'

            # using a 'contrived' if-test so that the 'print's all line up
            if True:
                o += '\n'

            todos_file = self.__finick_config.get_todos_file_fullname_fullpath(
            )

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


def _dec_emptystring_if_list_is_empty(F):
    def wrapper(*args):
        # args[0] will be the RowPrinterSessionEndSummary 'self'
        # args[1] is the list of notes
        if len(args[1]) < 1:
            return ''
        else:
            return F(*args)

    return wrapper


class RowPrinterSessionEndSummary(object):
    def __init__(self, finick_config, summary_map, todos_map):
        self.__finick_config = finick_config
        self.__summary_map = summary_map
        self.__todos_map = todos_map
        # the reviewer could review work by many developers, which would result in *many* emails:
        self.__list_of_eml_msgs = []

        AssertType_FinickConfig(self.__finick_config)

        # for each key (key is a commit email address), we expect a list of db rows:
        for key, val in self.__summary_map.items():
            for r in val:
                AssertType_DbRow(r)

        # todos have same structure as summary_map: each key-email maps to a list of db rows:
        for key, val in self.__todos_map.items():
            for r in val:
                AssertType_DbRow(r)

    def _separator(self):
        return '____________________________________________________________\n'

    def _sub_separator(self):
        return '    ______________________________'

    def _oops_heading(self):
        return '\nOOPS\n\n    These were marked as OOPS and reverted:\n'

    def _todo_heading(self, prior_todo_qty, prior_pls_qty):
        rslt = '\nTODO & PLS\n\n    '
        rslt += '[Prior to the start of this review session, you had '
        rslt += str(prior_todo_qty) + ' prior open TODO(s) and '
        rslt += str(prior_pls_qty) + ' prior open PLS(s).]\n\n    '
        rslt += 'Newly marked as TODO/PLS:\n'
        return rslt

    def _fixd_heading(self):
        return '\nFIXD\n\n    Your fixes were approved in commits:\n'

    def _ok_heading_main(self):
        return '\nOK\n'

    def _ok_head_with(self):
        return '\n    Approved with comments:\n'

    def _ok_head_without(self):
        return '\n    Approved without comment:\n'

    def _get_subject(self, reviewer, count):
        return reviewer + ' reviewed ' + str(
            count) + ' of your commits [finick_code_reviews]'

    def _num_str(self, i):
        rslt = str(i) + '.'
        xtra = (3 - len(str(i))) * ' '
        return rslt + xtra

    def _do_one_note(self, i, note, label=''):
        if label == '':
            label = note.rtype_str
        # elsewhere in finick, size-10 hashes are a REQUIREMENT. here it is just a preference:
        rslt = '\n    ' + self._num_str(i) + ' ' + note.commithash[0:10]

        if len(note.todo_refs) > 0:
            rslt += '  (to address '
            for tref in note.todo_refs:
                # elsewhere in finick, size-10 hashes are a REQUIREMENT. here it is just a preference:
                rslt += tref[0:10] + ','
            rslt = rslt[:-1]  # remove final ','
            rslt += ')'

        if len(note.comment) > 0:
            rslt += '\n         ' + label + ': ' + note.cleancomment
        rslt += '\n'

        return rslt

    def _do_section_content(self, list_of_notes, start_i=0):
        # because of our decorator @_dec_emptystring_if_list_is_empty,
        # we should always be ok to count on a guarantee that list_of_notes is non-empty
        rslt = ''
        i = start_i
        for note in list_of_notes:
            i += 1
            rslt += self._do_one_note(i, note, 'Note')

        rslt += '\n'

        return rslt

    def _save_email_body_to_file(self, reviewer, eml_obj):
        basename = str(
            '' + datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S") +
            '_summarymail_by_' + reviewer + '_to_' + eml_obj.to_whom + '.txt')

        eml_txt_file = self.__finick_config.confdir + os.sep + basename

        # mode 'w' will TRUNCATE the file
        text_file = open(eml_txt_file, encoding='utf-8', mode='w')

        text_file.write(eml_obj.body)

        text_file.close()

        print('(Email saved to \'' + eml_txt_file + '\'.)\n')

    def _get_prior_todos_n_plsls(self, list_of_todos_plss):
        prior_t = 0
        prior_p = 0

        for each_todo in list_of_todos_plss:
            if each_todo.row_type == each_todo.TYPE_TODO:
                prior_t += 1
            elif each_todo.row_type == each_todo.TYPE_PLS:
                prior_p += 1

        return prior_t, prior_p

    @_dec_emptystring_if_list_is_empty
    def _get_oops_body_section(self, list_of_notes):
        rslt = self._separator() + self._oops_heading()
        rslt += self._do_section_content(list_of_notes)

        return rslt

    def _get_todos_body_section(self, list_of_todos, list_of_pls, todos):
        # we decidedly do _NOT_ want to use _dec_emptystring_if_list_is_empty on this func!
        # we cannot use the helper-decorator, due to CUSTOM logic for skipping the TODO/PLS section.

        prior_t, prior_p = self._get_prior_todos_n_plsls(todos)
        work_qty = prior_t + prior_p + len(list_of_todos) + len(list_of_pls)

        if work_qty < 1:
            return ''
        else:
            rslt = self._separator() + self._todo_heading(prior_t, prior_p)
            i = 0
            for tr in list_of_todos:
                i += 1
                rslt += self._do_one_note(i, tr)
            for pr in list_of_pls:
                i += 1
                rslt += self._do_one_note(i, pr)

            rslt += '\n'

        return rslt

    @_dec_emptystring_if_list_is_empty
    def _get_fixd_body_section(self, list_of_notes):
        rslt = self._separator() + self._fixd_heading()
        rslt += self._do_section_content(list_of_notes)

        return rslt

    @_dec_emptystring_if_list_is_empty
    def _get_ok_body_section(self, list_of_notes):
        rslt = self._separator() + self._ok_heading_main()

        notes_commented = []
        notes_uncommented = []

        for n in list_of_notes:
            if len(n.comment) > 0:
                notes_commented.append(n)
            else:
                notes_uncommented.append(n)

        if len(notes_commented) > 0:
            rslt += self._ok_head_with()
            rslt += self._do_section_content(notes_commented)

        if len(notes_uncommented) > 0:
            if len(notes_commented) > 0:
                rslt += self._sub_separator()
            rslt += self._ok_head_without()
            rslt += self._do_section_content(notes_uncommented,
                                             len(notes_commented))

        return rslt

    def _make_one_email_body(self, committer, list_of_notes, todos):
        class FreeFormStruct(object):
            pass

        eml = FreeFormStruct()
        eml.to_whom = committer
        eml.subject = self._get_subject(self.__finick_config.reviewer,
                                        len(list_of_notes))
        eml.body = '\n'

        r = DbRow.dummyinstance()
        notes_by_category = {}
        notes_by_category[r.TYPE_OOPS] = []
        notes_by_category[r.TYPE_TODO] = []
        notes_by_category[r.TYPE_PLS] = []
        notes_by_category[r.TYPE_FIXD] = []
        notes_by_category[r.TYPE_OK] = []

        # in the __init__ constructor, we already asserted that these are type DbRow:
        for drow in list_of_notes:
            notes_by_category[drow.row_type].append(drow)

        # Now build the actual body of the email:

        eml.body += self._get_oops_body_section(notes_by_category[r.TYPE_OOPS])

        eml.body += self._get_todos_body_section(
            notes_by_category[r.TYPE_TODO], notes_by_category[r.TYPE_PLS],
            todos)

        eml.body += self._get_fixd_body_section(notes_by_category[r.TYPE_FIXD])

        eml.body += self._get_ok_body_section(notes_by_category[r.TYPE_OK])

        self._save_email_body_to_file(self.__finick_config.reviewer, eml)
        self.__list_of_eml_msgs.append(eml)

    def prepare_email_messages(self):

        for committer_key, list_val in self.__summary_map.items():
            self._make_one_email_body(committer_key, list_val,
                                      self.__todos_map[committer_key])

    def send_prepared_email_messages(self):

        for e in self.__list_of_eml_msgs:
            finicky.email.send_the_sessionend_email(
                [e.to_whom], e.subject, e.body, self.__finick_config)
