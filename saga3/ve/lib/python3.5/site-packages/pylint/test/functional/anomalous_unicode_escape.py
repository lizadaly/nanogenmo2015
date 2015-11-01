# pylint:disable=W0105, W0511, C0121
"""Test for backslash escapes in byte vs unicode strings"""

# Would be valid in Unicode, but probably not what you want otherwise
BAD_UNICODE = b'\u0042'  # [anomalous-unicode-escape-in-string]
BAD_LONG_UNICODE = b'\U00000042'  # [anomalous-unicode-escape-in-string]
# +1:[anomalous-unicode-escape-in-string]
BAD_NAMED_UNICODE = b'\N{GREEK SMALL LETTER ALPHA}'

GOOD_UNICODE = '\u0042'
GOOD_LONG_UNICODE = '\U00000042'
GOOD_NAMED_UNICODE = '\N{GREEK SMALL LETTER ALPHA}'


# Valid raw strings
RAW_BACKSLASHES = r'raw'
RAW_UNICODE = r"\u0062\n"

# In a comment you can have whatever you want: \ \\ \n \m
# even things that look like bad strings: "C:\Program Files"
