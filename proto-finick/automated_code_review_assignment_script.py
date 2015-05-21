#!/usr/bin/env python

"""
The 'real' copy of this script is on ServerAB at:

    /Users/cruisecontrol/automated_code_review_assignment_script.py

It is scheduled to run via the Mac scheduler 'launchd'.
The launchd config is on ServerAB at:

    /Library/LaunchDaemons/com.cedrus.dev.codereviews.plist

Command to change the schedule:

    # Weekday 0 (zero) is sunday. 1 = monday, and so on.
    sudo defaults write /Library/LaunchDaemons/com.cedrus.dev.codereviews StartCalendarInterval -dict Hour -int 16 Minute -int 36 Weekday -int 4

For this task, I also set RunAtLoad to true, which allows us to FORCE
the task to run if you do this:

    sudo launchctl  unload  com.cedrus.dev.codereviews.plist
    sudo launchctl  load    com.cedrus.dev.codereviews.plist
"""

"""
 ========== README README README ==========

 ==== HOW TO MAKE THIS SCRIPT WORK FOR YOU:

 1. either use python 2.7 or else make updates to this script to make it work in py 3.

 2. edit the string stored in variable: how_to_call_git (line 56)

 3. edit the list of repositories in variable: repo_dirs (line 76)

 4. edit your team member info (names and emails) in variable: emails_of_devs (line 112)

 5. edit your SMTP login on the line containing 'server.login' (line 420)

"""

import subprocess
import smtplib
import random
import datetime
import time
from pprint import pprint

# We assume the last day of the review period is TODAY.  However, you
# may hand-edit this to use something else as the end date, like so:
# datetime.date( 2010, 10, 30 )
end_of_time_period_under_review = datetime.date.today()

history_days_length = 7

how_to_call_git = '/usr/local/bin/git'

# Nice-to-have: this could be changed to be based on a per-developer
# setting, where some devs read more lines than others.  This is lines
# PER REPO. multiply by repo-count for actual assignment size.
max_lines_changed_assignable = 100

# the 'info string' contains the summary count of affected
# lines-of-code, and the author, and part of the commit notes
truncation_length_of_extra_info_string = 100

"""
This script will assume that when we 'cd' into the directory,
everything is 'just ready-to-go', and we will NOT do anything like
'git pull origin master' or 'git checkout _____' before proceeding
with the log-analysis work.

friendly_name needs to be unique. (really, so do the dirs, or else
what's the point?)
"""
repo_dirs = [
    { 'friendly_name': 'ProjectAB', 'abs_location': '/hudson/jobs/A-Release-FullBuild_Mac/workspace/label_exp/ServerAB/SLP' },
    { 'friendly_name': 'ProjectAB-otherbranch', 'abs_location': '/hudson/jobs/Special_Branch-Debug-FullBuild_Mac/workspace/label_exp/ServerAB/S' },
    { 'friendly_name': 'utils',   'abs_location': '/hudson/jobs/C-Release-FullBuild_Mac/workspace/label_exp/ServerAB/CDB' },
    { 'friendly_name': 'mediasupport', 'abs_location': '/hudson/jobs/D-Release-FullBuild_Mac/workspace/label_exp/ServerAB/LL' },
    ]

"""
The following map exists so that you can assign a 'friendly_name'
value to a repo (or more specifically: to a branch-repo combination)
where the 'friendly_name' does _NOT_ match the github name shown in
the github url.  You only need to create a mapping in
'name_mapped_to_url_name' if the friendly_name is a MISMATCH to the
url name.

By 'github name' I mean what appears here with the name 'utils':
https://github.com/acme/utils/commit/b065b50

See function 'get_url_for_diff_of_commit' for full details.
"""
name_mapped_to_url_name = {
    'ProjectAB-otherbranch': 'ProjectAB',
    }

# there may well be TAB CHARS in these strings. LEAVE THEM AS IS!
# these must match the git output exactly
exclusion_patterns = [
    '1	1	utils',
    '1	1	other_submodule',
    '1	1	mediasupport', # exclude simple submodule updates
    ]


# for now we are really just matching on the FIRST FOUR LETTERS, so
# that we don't have to worry about mistakes in the gitconfig file
# that yield: 'alice@.(none)' , 'alice@.ACME.LOCAL' , etc
emails_of_devs = [
    ['alice@acme.com','Alice'],
    ['bob@acme.com','Bob'],
    ['eve@acme.com','Eve'],
    ]


delimiter_between_hash_and_email = '$'

reviews_email_header = """
Things to remember:

No two people are reviewing the same code.

No one is reviewing his/her own code.

Each list is in reverse chronological order.

We all are assigned roughly the same amount of actual changes.
(That could be a long list of brief commits, or a brief list of long commits.)

If you have no assignments in any given repo, it could be that:
a. there wasn't much activity in that repo during this review period,
or b. all of the activity in that repo was your own.
"""

reviews_email_footer = ''




ymd_date = end_of_time_period_under_review.strftime("%y%m%d")
date_based_seed_for_reproducibility = int(ymd_date)

random.seed( date_based_seed_for_reproducibility )

period_span = datetime.timedelta(days=history_days_length)
start_of_time_period_under_review = end_of_time_period_under_review - period_span

commit_hierarchy = {}
total_assignments = {}


def get_url_for_diff_of_commit( the_hash, repo_name ):

    repo_url_name = repo_name
    if name_mapped_to_url_name.has_key( repo_name ):
        repo_url_name = name_mapped_to_url_name[ repo_name ]

    return 'https://github.com/acme/' + repo_url_name + '/commit/' + the_hash


def populate_hashes_into_hierarchy( repo_name, massive_string ):

    curr_line = massive_string
    while len(curr_line) > 0:

        #partition returns a 3-tuple containing the part before the
        #separator, the separator itself, and the part after
        curr_line, separator, rest_lines = curr_line.partition('\n')

        if len(curr_line) > 0:
            comm_hash, dev_email, date_string = curr_line.split( delimiter_between_hash_and_email )

            # we expect the date string to be in RFC2822 style
            # Tue, 2 Feb 2010 22:22:56 +0000

            shorter_d_str = date_string[:-6] # strptime cannot handle the utc offset

            date_obj = datetime.datetime.strptime(shorter_d_str, "%a, %d %b %Y %H:%M:%S" ) # %z")

            try:
                commit_hierarchy[ repo_name ][dev_email] += [ [comm_hash, date_string, date_obj] ]
            except:
                commit_hierarchy[ repo_name ][dev_email] = [ [comm_hash, date_string, date_obj] ]

        curr_line = rest_lines



def retrieve_all_recent_hashes( repo_name, abs_path ):

    commit_hierarchy[ repo_name ] = {}

    before_clause = ' --before=\"' + end_of_time_period_under_review.strftime(  "%Y-%m-%d 23:59:59") + '\" '
    since_clause =  ' --since=\"'  + start_of_time_period_under_review.strftime("%Y-%m-%d 23:59:59") + '\" '
    date_format = ' --date=local ' #--date=iso '

    command_line_string = [how_to_call_git + ' log ' + date_format + before_clause + since_clause +
                           ' --pretty=format:\"%H' +
                           delimiter_between_hash_and_email +
                           '%ae' +
                           delimiter_between_hash_and_email +
                           '%aD\"' # must use %aD to guarantee parsing by strptime
                           ]

    git_log_output = ''

    try:
        """
        On Unix, with shell=True: If args is a string, it specifies the
        command string to execute through the shell. This means that the
        string must be formatted exactly as it would be when typed at the
        shell prompt. This includes, for example, quoting or backslash
        escaping filenames with spaces in them.

        when we set 'shell=True', then the command is one long string.  if
        we use 'shell=False', then command_string should be =
        ['git','log','-5'], or something similar
        """
        git_log_process = subprocess.Popen(
            command_line_string,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=abs_path
            )

        git_log_output, git_log_errors = git_log_process.communicate()

        if len(git_log_errors) > 0:
            print 'error during calls to git log:'
            print git_log_errors
        else:
            print datetime.date.today().strftime("%Y-%m-%d") + ' no git error in \'' + str(abs_path) + '\''

    except:
        print 'Failed to use \'git log\' to retrieve the most recent commits from \'' + str(abs_path) + '\''

    populate_hashes_into_hierarchy( repo_name, git_log_output )



def get_dataset_of_other_devs( dev_to_exclude ):

    other_devs_dataset = []
    total_commit_qty = 0

    # populate 'other_devs_dataset' with committers that ARE NOT the self-same 'developer_doing_reviews'
    for dev_email in commit_hierarchy[ repo_dir['friendly_name'] ].keys():

        #  we will actually just match on the FIRST FOUR LETTERS of the email
        if dev_email[0:4].lower() != dev_to_exclude[0:4].lower():
            list_of_hashes_per_dev = commit_hierarchy[ repo_dir['friendly_name'] ][dev_email]
            other_devs_dataset += [ { 'dev_id' : dev_email, 'quantity' : len(list_of_hashes_per_dev), 'end_roulette_section' : 0 } ]
            total_commit_qty += len(list_of_hashes_per_dev)

    if len(other_devs_dataset) > 0:

        # using the roulette wheel selection algorithm
        # http://geneticalgorithms.ai-depot.com/Tutorial/Overview.html

        section_edge = 0
        for d in other_devs_dataset:
            proportion = d[ 'quantity' ] / (total_commit_qty*1.0)
            section_edge += proportion
            d[ 'end_roulette_section' ] = section_edge

        other_devs_dataset[ len(other_devs_dataset) - 1 ][ 'end_roulette_section' ] = 1

    return other_devs_dataset


def do_random_roulette_spin_and_choose_one_hash( devs_dataset ):

    # we have to always ensure there is an end that equals 1.
    # we could 'lose' the end because we periodically REMOVE items
    # from the devs_dataset list.
    # this makes the actual math of our roulette wheel a little funky, but prevents a failure to select something during a 'spin'.
    devs_dataset[ len(devs_dataset) - 1 ][ 'end_roulette_section' ] = 1    # in case we removed anyone from devs_dataset

    spin = random.random()

    chosen_dev = ''
    chosen_dev_i = -1
    for d in devs_dataset:
        chosen_dev_i += 1
        if d[ 'end_roulette_section' ] > spin:
            chosen_dev = d[ 'dev_id' ]
            break

    rand_int = random.randint( 0, len(commit_hierarchy[ repo_dir['friendly_name'] ][ chosen_dev ]) - 1 )

    hash_date_pair = commit_hierarchy[ repo_dir['friendly_name'] ][ chosen_dev ][rand_int]

    # remove this commit. either we will use it or we will deem it unfit, but either way get rid of it
    del commit_hierarchy[ repo_dir['friendly_name'] ][ chosen_dev ][rand_int]

    if len( commit_hierarchy[ repo_dir['friendly_name'] ][ chosen_dev ] ) < 1:
        del commit_hierarchy[ repo_dir['friendly_name'] ][ chosen_dev ]
        del devs_dataset[ chosen_dev_i ]

    return hash_date_pair


def analyze_change_set( change_set ):

    affected_lines_count = 0

    curr_line = change_set
    while len(curr_line) > 0:

        #partition returns a 3-tuple containing the part before the
        #separator, the separator itself, and the part after
        curr_line, separator, rest_lines = curr_line.partition('\n')

        if len(curr_line) > 0 and (not (curr_line in exclusion_patterns)):

            tokens = curr_line.split()
            affected_lines_count += int(tokens[0])
            affected_lines_count += int(tokens[1])

        curr_line = rest_lines

    return affected_lines_count


def calculate_per_repo_per_dev_assignments( dev_name, repo_name, repo_path ):

    results_to_review = []
    size_of_changeset = 0

    other_devers = get_dataset_of_other_devs( dev_name )

    while len(other_devers) > 0:

        if size_of_changeset >= max_lines_changed_assignable:
            break

        hash_date_pair = do_random_roulette_spin_and_choose_one_hash( other_devers )

        command_line_string = [how_to_call_git + ' log -1 --numstat ' + hash_date_pair[0] + ' | grep \'^[0-9]\' ']

        git_log_process = subprocess.Popen(
            command_line_string,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=repo_path
            )

        # NOTE: i thought that i was having a performance problem due
        # to either the internals of the python subprocess module
        # (which has been written about as slow-performing) or due to
        # something about my own algorithms in this script.  I did
        # some testing, and I found out that actually some calls to
        # 'git' JUST TAKE A LONG TIME. Even if you run the same git
        # command yourself at a bash prompt.
        git_log_output, git_log_errors = git_log_process.communicate()

        changes = analyze_change_set( git_log_output )

        if changes > 0:

            extra_info = ['Affected lines: ' + str(changes) ]

            git_log_process = subprocess.Popen(
                how_to_call_git + ' log -1 --pretty=format:"%an: %s" ' + hash_date_pair[0],
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=repo_path
                )

            output, error_output = git_log_process.communicate()
            extra_info += [ output[0:truncation_length_of_extra_info_string] ]
            if len(output) > truncation_length_of_extra_info_string:
                extra_info[ len(extra_info) - 1 ] += '...'

            results_to_review += [ [ hash_date_pair[0], extra_info, hash_date_pair[1], hash_date_pair[2]  ] ]
            size_of_changeset += changes

    return results_to_review



def send_the_assignment_email( to_list, subject_line, email_body_text ):

    SERVER = "smtp.gmail.com"
    PORT = 587

    FROM = "team@acme.com"
    TO = to_list

    SUBJECT = subject_line

    TEXT = email_body_text

    # Prepare actual message

    message = """\
From: %s
To: %s
Subject: %s

%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    try:
        # class smtplib.SMTP([host[, port[, local_hostname[, timeout]]]])
        server = smtplib.SMTP(SERVER, PORT)

        server.ehlo()
        server.starttls()
        server.ehlo()   # this line is apparently necessary on python 2.4 and 2.5, but not afterward.
        server.login("some===email==goes==here@gmail.com", "Some_Password_You_Know")
        server.sendmail(FROM, TO, message)
        server.quit()

    except:
        print 'smtp stuff failed'


def key_hash_sort_helper_for_assignment_items( assignment_item ):

    # each assignment looks like:   [ hash,  [ extra lines ], date string, date OBJECT ]

    # for sorting by the commit date, we will simply use the
    # associated date object to calculate the unix 'ticks' timestamp
    # (epoch seconds).
    # learned from: http://stackoverflow.com/questions/2775864/python-datetime-to-unix-timestamp
    return time.mktime( assignment_item[3].timetuple() )



# our 'entry point' (as in 'int main') pretty much starts
# here. (although, yes, we did already call random.seed() earlier.)

for repo_dir in repo_dirs:

    retrieve_all_recent_hashes( repo_dir['friendly_name'], repo_dir['abs_location'] )


# nice-to-have: we could shuffle the list of developers before doling
# out the review assignments.  This way, from week-to-week if there
# are too few commits to accomodate everyone, we aren't always running
# out of commits on the SAME FIRST-IN-LINE developer each time, and
# 'starving' the same END-OF-LIST developers each time.
for developer_doing_reviews in emails_of_devs:

    # by repo name, a list of hash/notes items
    requests_to_be_reviewed = {}

    for repo_dir in repo_dirs:

        assignments = calculate_per_repo_per_dev_assignments(
            developer_doing_reviews[0], repo_dir['friendly_name'], repo_dir['abs_location'] )

        requests_to_be_reviewed[ repo_dir['friendly_name'] ] = sorted(
            assignments, key=key_hash_sort_helper_for_assignment_items, reverse=True)

    total_assignments[ developer_doing_reviews[0] ] = [ developer_doing_reviews, requests_to_be_reviewed ]



# first keys are email addresses
# when keying on email address, you then get val[0] and val[1]
# val[0] will match one of the entries in emails_of_devs
# val[1] is another dictionary
# next keys (keys of val[1]) are repo names
# lastly you get a list of hash/notes items

email_body = reviews_email_header
email_to_list = []

for each_dev, stored_item in total_assignments.iteritems():

    email_to_list += [ each_dev ]

    email_body += '\r\n\r\n\r\nCode to be reviewed by ' + stored_item[0][1] + ':\r\n\r\n'

    for repo_name, list_of_hashes in stored_item[1].iteritems():

        email_body += '\t' + repo_name + ':\r\n\r\n'

        if len(list_of_hashes) < 1:
            email_body += '\t\t(no assignments for review here)\r\n\r\n'

        hash_count = 0

        for hash_and_note in list_of_hashes:

            hash_count += 1
            email_body += str('\t\t' + str(hash_count) + '. ' + hash_and_note[0][0:8] + ' - ' +
                get_url_for_diff_of_commit(hash_and_note[0], repo_name) + '\r\n\r\n')

            email_body += '\t\t   ' + hash_and_note[2] + '\r\n\r\n'

            for info_line in hash_and_note[1]:
                email_body += '\t\t   ' + info_line + '\r\n\r\n'

    email_body += '\r\n' + reviews_email_footer


subject_text = str('Code Review Assignments from ' +
                   start_of_time_period_under_review.strftime("%Y-%m-%d") +
                   ' to ' +
                   end_of_time_period_under_review.strftime("%Y-%m-%d") )


send_the_assignment_email( email_to_list, subject_text, email_body )


