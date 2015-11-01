"""Suspicious str.strip calls."""
__revision__ = 1

''.strip('yo')
''.strip()

''.strip('http://')  # [bad-str-strip-call]
''.lstrip('http://')  # [bad-str-strip-call]
b''.rstrip('http://')  # [bad-str-strip-call]
