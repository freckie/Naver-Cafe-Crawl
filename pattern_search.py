import re

_pat_dict = {
    '\\': '\\\\',
    '^': '\^',
    '$': '\$',
    '.': '\.',
    '|': '\|',
    '[': '\[',
    ']': '\]',
    '(': '\(',
    ')': '\)',
    '{': '\{',
    '}': '\}',
    '?': '\?',
    '*': '\*',
    '+': '\+',
    ' ': ' ?'
}

def pat_transform(pat):
    for it in _pat_dict:
        pat = pat.replace(it, _pat_dict[it])
    return pat

def pat_find(pat, data):
    r = re.compile(pat, re.IGNORECASE)
    return r.search(data).group()

def pat_check(pat_list, data):
    no_space_data = data.replace(' ', '')
    for pat in pat_list:
        r = re.compile(pat, re.IGNORECASE)
        if r.search(no_space_data):
            return True
    return False