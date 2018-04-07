"""This module handles the log translation functionality of the heybrochecklog package."""

import re
from collections import OrderedDict

from heybrochecklog import UnrecognizedException
from heybrochecklog.analyze import analyze_log
from heybrochecklog.shared import get_log_contents, open_json
from heybrochecklog.logfile import LogFile

# Lines which should be regexed instead of `x in y`.
REGEXES = [
    ['russian', 1309]
]


def translate_log(log_file):
    """Initialize and capture all logs."""
    contents = get_log_contents(log_file)
    log = LogFile(contents)
    return translate_wrapper(log)


def translate_log_from_contents(contents):
    """Translate a log file given its contents."""
    log = LogFile(contents.split('\n'))
    try:
        return translate_wrapper(log)
    except UnicodeDecodeError:
        return {'unrecognized': 'Could not decode log'}


def translate_wrapper(log):
    """Translate log given log file."""
    try:
        analyze_log(log)
    except UnrecognizedException as exception:
        return {
            'unrecognized': exception,
            'log': ''.join(log.full_contents)
        }

    if log.language == 'english':
        return {
            'unrecognized': False,
            'language': 'english',
            'log': ''.join(log.full_contents)
        }

    return sub_english(log)


def sub_english(log):
    """Translate the log file and return a dict of info and log."""
    english = open_json('eac', 'english.json')['translation']
    foreign = open_json('eac', '{}.json'.format(log.language))['translation']

    # Sort foreign lines from longest to shortest
    foreign = OrderedDict(sorted(foreign.items(), key=lambda t: len(t[1]), reverse=True))

    # Compile all the regex now instead of repeating.
    for key, value in foreign.items():
        if [log.language, key] not in REGEXES:  # Some are regex and shouldn't be escaped.
            value = re.escape(value)
        foreign[key] = re.compile(value)

    # Iterate through each line and find/replace each string.
    new_log = []
    for line in log.full_contents:
        if not line:  # No use wasting time here.
            new_log.append('')
        else:
            for key, regex in foreign.items():
                if regex.search(line):
                    line = regex.sub(english[key], line)
            new_log.append(line)

    re_space_settings(new_log)
    new_log = ''.join(new_log)

    return {
        'unrecognized': False,
        'language': log.language,
        'log': new_log
    }


def re_space_settings(log):
    """Fix the spacing in the rip settings block."""
    spacings = [24, 44, 32]  # Number of characters before colons in each block of settings.
    end_of_blocks = ['Make use of C2 pointers', 'Gap handling']  # Last setting in blocks.
    index = 0

    for i, line in enumerate(log):
        if re.match('Used drive', line):
            continue  # Ignore that line

        result = re.search(r'^([A-Z][A-Za-z0-9- ]+[a-z]) +:(.*)$', line)
        if result:
            word = result.group(1)
            spaces = spacings[index] - len(word)
            log[i] = word + ' ' * spaces + ':' + result.group(2) + '\n'

            if word in end_of_blocks:
                index += 1

        if re.match('TOC', line):  # No need to continue after settings are done.
            return
