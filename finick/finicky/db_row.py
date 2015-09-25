from __future__ import print_function
from __future__ import division  # py3 style. division promotes to floating point.
from __future__ import unicode_literals
from __future__ import absolute_import

from finicky.error import FinickError

import datetime


def AssertType_DbRow(o):
    rhs = DbRow.dummyinstance()
    incoming_type = str(type(o))
    if type(o) != type(rhs):
        raise FinickError(
            "AssertType_DbRow failed. DbRow was required, but instead we got: "
            + incoming_type)


def _fail_setter(self, value):
    raise FinickError(
        "The value you are trying to assign to in DbRow is read-only.")


def _get_the_monday_matching_a_given_date(date_obj):
    # http://stackoverflow.com/questions/5882405/get-date-from-iso-week-number-in-python
    week_of_year = (date_obj.isocalendar()[1])
    the_year = date_obj.year

    ret = datetime.datetime.strptime('%04d-%02d-1' % (the_year, week_of_year),
                                     '%Y-%W-%w')
    if datetime.date(the_year, 1, 4).isoweekday() > 4:
        ret -= datetime.timedelta(days=7)

    return ret


class DbRow(object):
    @classmethod
    def dummyinstance(cls):
        return cls(True)

    @classmethod
    def create_from_string(cls, string_to_parse, file_comment):
        return cls(False, string_to_parse, file_comment)

    @classmethod
    def create_from_gitting_tuple(cls, gitt_tuple):
        # our tuples come directly from git output. so there is never a file_comment
        return cls(False, '', '', gitt_tuple)

    @classmethod
    def _create_from_internal_map(cls, the_map):
        return cls(False, '', '', None, the_map)

    def _get_dateobj(self):
        # recall that __commit_datestr is formatted like so:
        #"1970-03-01_01:01:01"
        return datetime.datetime.strptime(self.__commit_datestr,
                                          "%Y-%m-%d_%H:%M:%S")

    def _get_monday(self):
        return _get_the_monday_matching_a_given_date(self._get_dateobj())

    def _get_my_string(self):
        return self._convert_rowtype_constant_to_string(self.row_type)

    def _get_cleancomment(self):
        rslt = self.__action_comment
        if rslt.startswith(self.ACTION_COMMENT_CHAR):
            rslt = rslt[1:]

        rslt = rslt.lstrip()

        return rslt

    def __init__(self,
                 is_dummy,
                 string_to_parse='',
                 file_comment='',
                 gitt_tuple=None,
                 internal_map=None):

        self.__creator = ''  # this variable is intended only for debugging/tracing

        self.__file_comment = file_comment
        self.__committer = ''
        self.__commit_hash = ''
        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = ''
        self.__rowtype = self.TYPE_ERRORTYPE
        self.__reviewer = ''
        # each todo ref will be the FIRST few chars of a hash. always length DbRow.SHORT_H_SIZE
        self.__todo_refs = []
        self.__action_comment = ''
        # at some point we might need more structure, like a forefront DATETIME object:
        self.__forefront_string = ''

        if gitt_tuple is not None:
            self.__creator = 'create_from_gitting_tuple'
            self._initialize_from_tuple(gitt_tuple)
        elif internal_map is not None:
            self.__creator = '_create_from_internal_map'
            self._initialize_from_map(internal_map)
        elif False == is_dummy:
            self.__creator = 'create_from_string'
            self._initialize_from_string(string_to_parse)

    # yapf: disable

    row_type     = property(lambda s : s.__rowtype,    _fail_setter)

    rtype_str    = property(   _get_my_string,         _fail_setter)

    commitdate   = property(   _get_dateobj,           _fail_setter)

    prior_monday = property(   _get_monday,            _fail_setter)

    """Note: user-code could still (inappropriately) modify ITEMS in todo_refs list. Please do not."""
    todo_refs    = property(lambda s : s.__todo_refs,  _fail_setter)

    committer    = property(lambda s : s.__committer,  _fail_setter)

    commithash   = property(lambda s : s.__commit_hash,_fail_setter)

    reviewer     = property(lambda s : s.__reviewer,   _fail_setter)

    cleancomment = property(   _get_cleancomment,      _fail_setter)

    comment      = property(lambda s : s.__action_comment, _fail_setter)

    # yapf: enable

    def _convert_rowtype_constant_to_string(self, rowtype_int):
        if rowtype_int == self.TYPE_OK:
            return 'OK'
        elif rowtype_int == self.TYPE_OOPS:
            return 'OOPS'
        elif rowtype_int == self.TYPE_WAIT:
            return 'WAIT'
        elif rowtype_int == self.TYPE_FIXD:
            return 'FIXD'
        elif rowtype_int == self.TYPE_TODO:
            return 'TODO'
        elif rowtype_int == self.TYPE_HIDE:
            return 'HIDE'
        elif rowtype_int == self.TYPE_NOW:
            return 'NOW'
        elif rowtype_int == self.TYPE_PLS:
            return 'PLS'
        elif rowtype_int == self.TYPE_RVRT:
            return 'RVRT'
        else:
            err = 'Invalid row type: ' + str(rowtype_int)
            raise FinickError(err)

    def _convert_string_to_rowtype_constant(self, rowtype_string, linetext):
        if rowtype_string == 'OK':
            return self.TYPE_OK
        elif rowtype_string == 'OOPS':
            return self.TYPE_OOPS
        elif rowtype_string == 'WAIT':
            return self.TYPE_WAIT
        elif rowtype_string == 'FIXD':
            return self.TYPE_FIXD
        elif rowtype_string == 'TODO':
            return self.TYPE_TODO
        elif rowtype_string == 'HIDE':
            return self.TYPE_HIDE
        elif rowtype_string == 'NOW':
            return self.TYPE_NOW
        elif rowtype_string == 'PLS':
            return self.TYPE_PLS
        elif rowtype_string == 'RVRT':
            return self.TYPE_RVRT
        else:
            err = 'Invalid row type: ' + rowtype_string + ', on row: [' + linetext + ']'
            raise FinickError(err)

    def assign_for_current_review_session(self, reviewer_email):
        """This function should always do 'the opposite' of cancel_assignment_for_current_review_session
        """
        self.__rowtype = self.TYPE_NOW
        self.__reviewer = reviewer_email

    def cancel_assignment_for_current_review_session(self):
        """This function should always do 'the opposite' of assign_for_current_review_session
        """
        self.__rowtype = self.TYPE_WAIT
        self.__reviewer = ''

    def _store_incoming_todo_refs(self, assignment_row, ref_checker_func):
        """This helper function plays a part in merging a completed assignment with a db_file row
        """
        # here we enforce that there is at least one valid todo-ref.
        # also, we make the todo-refs all be exactly the same length!
        # lastly, replace self.__todo_refs with these special-length strings.
        if len(assignment_row.todo_refs) < 1:
            raise FinickError(
                'Assignment row ' + assignment_row.commithash +
                ' is missing todo-refs (hashes referencing '
                'earlier commits).')

        for tr in assignment_row.todo_refs:
            if len(tr) < self.SHORT_H_SIZE:
                raise FinickError(
                    'Todo-ref ' + tr + ' on assignment row ' +
                    assignment_row.commithash + ' is not length-' + str(
                        self.SHORT_H_SIZE) + ' or longer.')

            # look up tr and make sure it refers to a KNOWN commit
            if False == ref_checker_func(tr[0:self.SHORT_H_SIZE]):
                raise FinickError(
                    'On assignment row ' + assignment_row.commithash +
                    ', invalid todo-ref: ' + tr)

        # clip to length SHORT_H_SIZE and assign using list comprehension:
        self.__todo_refs = [i[0:self.SHORT_H_SIZE]
                            for i in assignment_row.todo_refs]

    def throw_exception_if_bad_actioncomment(self):
        """This code is in a function (instead of coded in place) so that it can be used by db_row *and* db_file
        """
        if len(self.comment) < 3:
            raise FinickError(
                'Row ' + self.commithash + ' was marked type ' +
                self._convert_rowtype_constant_to_string(
                    self.row_type) + ' but it is missing a helpful comment!')

    def _choose_between_our_reviewer_string_and_ar(self, assignment_row):
        """Uses the incoming reviewer (from assignments file) if it is non-empty. Otherwise,
        we use self.__reviewer, which should trace back to whatever gitting._git_current_user_email
        returned back when assignments were GENERATED.
        """
        rslt_reviewer = assignment_row._DbRow__reviewer.rstrip().lstrip()
        if len(rslt_reviewer) == 0:
            rslt_reviewer = self.__reviewer

        return rslt_reviewer

    def _merge_TODO_private_helper(self, ar, incoming_reviewer):
        """This code is in a function (instead of coded in place) because we need it twice:
        we use it during the 'normal' merge, and also during the special-case logic for OOPS rows.
        """
        if not (ar.row_type == ar.TYPE_TODO or ar.row_type == ar.TYPE_PLS):
            raise FinickError(
                'Function misuse. Only call into here with a row of type TODO or PLS.')

        ar.throw_exception_if_bad_actioncomment()
        self.__rowtype = ar.row_type
        self.__reviewer = incoming_reviewer
        self.__action_comment = ar.comment

    def merge_OOPS_row(self, assignment_row, reverthash, reason_to_hide,
                       git_driver_email):
        # if reverthash is empty (''), then the revert failed. we create a TODO instead.
        # otherwise, mark our OOPS and also return the _NEW_ RVRT ROW.
        # Note: CALLING CODE EXPECTS A GUARANTEE that assignment_row.row_type will
        # end up set to TYPE_TODO if we failed to revert the OOPS.
        new_row = None

        incoming_reviewer = self._choose_between_our_reviewer_string_and_ar(
            assignment_row)

        if reverthash == '':
            # revert failed. make the OOPS a TODO instead.
            # IMPORTANT: the next line MUTATES the passed-in arg 'assignment_row'
            assignment_row._DbRow__rowtype = assignment_row.TYPE_TODO
            self._merge_TODO_private_helper(assignment_row, incoming_reviewer)
        else:
            self.__rowtype = self.TYPE_OOPS
            self.__reviewer = incoming_reviewer
            self.__action_comment = assignment_row.comment

            the_map = {
                '__committer': git_driver_email,
                '__commit_hash': reverthash,
                '__rowtype': self.TYPE_RVRT,
                '__reviewer': incoming_reviewer,
                '__todo_refs': [self.__commit_hash[0:self.SHORT_H_SIZE]],
                '__action_comment': reason_to_hide
            }

            new_row = DbRow._create_from_internal_map(the_map)

        return new_row

    def merge_with_completed_assignment_all_cases_except_OOPS(
        self, assignment_row, ref_checker_func):
        # if 'ar' is still in row_type 'NOW', then put it back to 'WAIT'
        # other valid values for ar type: OK, FIXD, TODO, PLS, OOPS.
        # (currently, this function explicitly refuses to handle OOPS)

        # optimistically assume we will do 1 row-count worth of work:
        work_count = 1  # (might drop to zero later)

        if self.__reviewer == '':
            print(
                'Warning: db disk file showed NO reviewer email for a row that was assigned.')

        if self.__reviewer != assignment_row._DbRow__reviewer:
            print(
                'Warning: the assignments file changed the reviewer email that was originally the assigned reviewer.')

        incoming_reviewer = self._choose_between_our_reviewer_string_and_ar(
            assignment_row)

        # for brevity:
        ar = assignment_row

        assignment_is_deferred = (
            ar.row_type == ar.TYPE_NOW or ar.row_type == ar.TYPE_WAIT)

        if ar.row_type == self.__rowtype:
            # row type not being changed, so do not count as work:
            work_count = 0
            if not assignment_is_deferred:
                print('Warning: while processing assignment ' +
                      self.__commit_hash +
                      ', db_file shows that this commit was ALREADY marked as '
                      + self._convert_rowtype_constant_to_string(ar.row_type))

        if assignment_is_deferred:
            work_count = 0
            self.cancel_assignment_for_current_review_session()

        elif ar.row_type == ar.TYPE_OK:
            self.__rowtype = self.TYPE_OK
            self.__reviewer = incoming_reviewer
            self.__action_comment = ar.comment

        elif ar.row_type == ar.TYPE_FIXD:
            # Note: FIXD rows are required to have at least one valid todo-ref
            self._store_incoming_todo_refs(ar, ref_checker_func)  # this might throw an exception
            self.__rowtype = self.TYPE_FIXD
            self.__reviewer = incoming_reviewer
            self.__action_comment = ar.comment

        elif ar.row_type == ar.TYPE_TODO or ar.row_type == ar.TYPE_PLS:
            self._merge_TODO_private_helper(ar, incoming_reviewer)

        elif ar.row_type == ar.TYPE_OOPS:
            raise FinickError(
                'You must not pass OOPS-typed assignments to this \'merge\' function.')

        else:
            raise FinickError(
                'Invalid completed assignment row type. (Needed NOW, WAIT, OK, FIXD, TODO, or PLS.)')

        return work_count

    def _initialize_from_string(self, string_to_parse):
        """
        jdoe@cedrus.com    f6cc7699fb362c2777c474f3416ce0abb2c083fe   HIDE  nobody                # this is a reversal of commit xxxxxx
        jdoe@cedrus.com    7b660c3a473225f49c73e51c7b8af61e139990a0   NOW
        jdoe@cedrus.com    2228add0186febf3471914c861b3b06fd0eb8dbc   FIXD  abc@cedrus.com  ecfb335633  # good fix for todo

        TYPE_HIDE HIDE is for things that were reversals, and for this:
        CommitStringMaintWithoutSession=Cedrus_Automated_Maintenance_Commit
        """

        row_parts = []

        try:
            CAR = 0
            CDR = 1

            # pass None to make all blobs of whitespace a single separator:
            car_cdr = string_to_parse.split(None, 1)
            row_parts.append(car_cdr[CAR])

            for _i_ in range(0, 5):
                car_cdr = car_cdr[CDR].split(None, 1)
                row_parts.append(car_cdr[CAR])
                if car_cdr[CDR].startswith(self.ACTION_COMMENT_CHAR):
                    row_parts.append(car_cdr[CDR])
                    break

        except IndexError:
            # we arrive here for lines that do not possess the maximum 7 columns
            pass

        len_of_row_parts = len(row_parts)

        if len_of_row_parts < 4 or len_of_row_parts > 7:
            err_str = 'Unable to parse columns in this row: [' + string_to_parse + ']'
            raise FinickError(err_str)

        self.__committer = row_parts[0]
        self.__commit_hash = row_parts[1]
        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = row_parts[2]
        self.__rowtype = self._convert_string_to_rowtype_constant(
            row_parts[3], string_to_parse)

        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if len_of_row_parts >= 5:
            self.__reviewer = row_parts[4]

        # each todo ref will be the FIRST few chars of a hash. always length SHORT_H_SIZE
        if len_of_row_parts >= 6:
            comma_sep = ','  # this is duplicated in write_to_diskfile

            # we now can have either 1 more value or 2.
            # if 2, then we have todo_refs and a comment.
            # if 1, then it could be EITHER todo_refs or a comment
            if len_of_row_parts == 7:
                self.__todo_refs = row_parts[5].split(comma_sep)
                self.__action_comment = row_parts[6]
            else:
                if row_parts[5].startswith(self.ACTION_COMMENT_CHAR):
                    self.__action_comment = row_parts[5]
                else:
                    self.__todo_refs = row_parts[5].split(comma_sep)

            # if the comma separated list also ENDED in a final comma, we a get a spurious extra item
            if len(self.__todo_refs) > 0 and self.__todo_refs[len(
                    self.__todo_refs) - 1] == '':
                self.__todo_refs.pop()

    def _initialize_from_tuple(self, gitt_tuple):
        # the tuple came from gitting.git_retrieve_history.
        # this is a 3-tuple with a oneline_gitlog string, then a bool, then a comment string.
        # the bool represents whether this row should be a HIDE row (excluded from being reviewed)

        # warning: knowledge about using '\b\ as the delim is duplicated in gitting.py
        COL_DELIM = '\b'
        wants_to_hide = gitt_tuple[1]
        action_comment_string = gitt_tuple[
            2
        ]  # at this point it should _NOT_ have ACTION_COMMENT_CHAR yet!

        c_hash, committer_eml, date_string, ignored_subject = gitt_tuple[0].split(
            COL_DELIM)

        self.__committer = committer_eml
        self.__commit_hash = c_hash
        if len(action_comment_string) > 0:
            self.__action_comment = self.ACTION_COMMENT_CHAR + ' ' + action_comment_string

        if wants_to_hide:
            self.__rowtype = self.TYPE_HIDE
        else:
            self.__rowtype = self.TYPE_WAIT

        # we expect 'date_string' to be in RFC2822 style
        # Tue, 2 Feb 2010 22:22:56 +0000

        shorter_d_str = date_string[:-6]  # strptime cannot handle the utc offset

        date_obj = datetime.datetime.strptime(shorter_d_str,
                                              "%a, %d %b %Y %H:%M:%S")  # %z")

        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        self.__commit_datestr = date_obj.strftime(
            "%Y-%m-%d_%H:%M:%S")  # format duplicated in _initialize_from_map

    def _initialize_from_map(self, internal_map):
        """
            the_map = {'__committer': git_driver_email,
                       '__commit_hash': reverthash,
                       '__rowtype': self.TYPE_RVRT,
                       '__reviewer': incoming_reviewer,
                       '__todo_refs':[self.__commit_hash[0:self.SHORT_H_SIZE]],
                       '__action_comment':reason_to_hide}
                       """
        # we have to handle our today's date
        self.__commit_datestr = datetime.datetime.now().strftime(
            "%Y-%m-%d_%H:%M:%S")  # format duplicated in _initialize_from_tuple

        self.__committer = internal_map['__committer']
        self.__commit_hash = internal_map['__commit_hash']
        self.__rowtype = internal_map['__rowtype']
        self.__reviewer = internal_map['__reviewer']
        self.__todo_refs = internal_map['__todo_refs']
        self.__action_comment = internal_map['__action_comment']

        if len(self.__action_comment) > 0:
            if False == self.__action_comment.startswith(
                self.ACTION_COMMENT_CHAR):
                self.__action_comment = self.ACTION_COMMENT_CHAR + ' ' + self.__action_comment

    def set_forefront_marker(self, forefront_marker_string):
        if self.__forefront_string != '':
            print(
                'Warning: setting forefront info on a DbRow that already had such info.')

        self.__forefront_string = forefront_marker_string

    def write_to_diskfile(self, the_file):
        # the_file is expected to be a TextIOBase (from io)

        EMAIL_COL_WIDTH = 27  # later this should be in the config
        TYPE_COL_WIDTH = 7

        if self.__file_comment != '':
            the_file.write(self.__file_comment + '\n')

        row_text = ''

        row_text += (self.__committer + ' ' +
                     (' ' * (EMAIL_COL_WIDTH - len(self.__committer) - 1)))

        row_text += (self.__commit_hash + '   ')

        # see comments in gitting.py about our timezone issues. again,
        # for now, date strings are just a 'courtesy', not hard data.
        row_text += (self.__commit_datestr + '   ')

        rowtype_str = self._convert_rowtype_constant_to_string(self.__rowtype)
        row_text += (rowtype_str + ' ' +
                     (' ' * (TYPE_COL_WIDTH - len(rowtype_str) - 1)))

        reviewer_output = self.__reviewer

        # next comes the reviewer. BUT:
        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if self.__action_comment != '':
            if self.__reviewer == '':
                # comment is nonempty but __reviewer was empty. fix that:
                reviewer_output = '..nobody..'

        row_text += (reviewer_output + ' ' +
                     (' ' * (EMAIL_COL_WIDTH - len(reviewer_output) - 1)))

        comma_sep = ','  # this is duplicated in _initialize_from_string

        # each todo ref will be the FIRST few chars of a hash. always length SHORT_H_SIZE
        # refs, with commas
        for tr in self.__todo_refs:
            row_text += (tr + comma_sep)  # we remove the final comma next!

        if len(self.__todo_refs) > 0:
            # remove the trailing comma:
            row_text = row_text.rstrip(comma_sep)
            row_text += ('   ')

        # note: in order to have a comment, we MUST have a reviewer! even if the reviewer is '..nobody..'
        if self.__action_comment != '':
            if not self.__action_comment.startswith(self.ACTION_COMMENT_CHAR):
                raise FinickError(
                    'We always expect ACTION_COMMENT_CHAR to have been prepended by now.')

        row_text += (self.__action_comment)

        # we could do more sanity checking here. make sure what we are
        # about to save parses back as something equal to self

        # end this row
        row_text = row_text.rstrip()
        the_file.write(row_text + '\n')

        if self.__forefront_string != '':
            the_file.write(self.__forefront_string + '\n')



# yapf: disable

DbRow.ACTION_COMMENT_CHAR = property(lambda s: '#', _fail_setter)

# SHORT_H_SIZE means "short HASH size". We always store the todo-ref hashes in the same specific size string.
# we rely heavily on knowing they are length 10. (rely on this fact for string equality testing)
DbRow.SHORT_H_SIZE   = property(lambda s:  10,   _fail_setter)

DbRow.TYPE_ERRORTYPE = property(lambda s:  -1,   _fail_setter)
DbRow.TYPE_OK        = property(lambda s:   1,   _fail_setter)  # reviewer approved/accepted the commit
DbRow.TYPE_OOPS      = property(lambda s:   2,   _fail_setter)  # reviewer rejected the commit
DbRow.TYPE_WAIT      = property(lambda s:   3,   _fail_setter)  # not yet reviewed. awaiting review.
DbRow.TYPE_FIXD      = property(lambda s:   4,   _fail_setter)  # means both approval and the commit closes a PLS ('please' request) or a TODO
DbRow.TYPE_TODO      = property(lambda s:   5,   _fail_setter)  # reviewer defers the commit, contingent upon further items being addressed
DbRow.TYPE_HIDE      = property(lambda s:   6,   _fail_setter)  # a commit that is 'null' for reviewing purposes. hidden/excluded from the process.
DbRow.TYPE_NOW       = property(lambda s:   7,   _fail_setter)  # assigned for review during the current active session
DbRow.TYPE_PLS       = property(lambda s:   8,   _fail_setter)  # (short for 'please'). like todo, only we accept the commit, but with further requests for later.
DbRow.TYPE_RVRT      = property(lambda s:   9,   _fail_setter)  # a revert/reversal that is accepted and addresses a prior OOPS

# yapf: enable
