import re

decimal_match = re.compile('\d')


def bdecode(data):
    '''Main function to decode bencoded data'''
    chunks = list(data)
    chunks.reverse()
    root = _dechunk(chunks)
    return root


def _dechunk(chunks):
    item = chunks.pop()

    if item == 'd':
        item = chunks.pop()
        hash = {}
        while item != 'e':
            chunks.append(item)
            key = _dechunk(chunks)
            hash[key] = _dechunk(chunks)
            item = chunks.pop()
        return hash
    elif item == 'l':
        item = chunks.pop()
        list = []
        while item != 'e':
            chunks.append(item)
            list.append(_dechunk(chunks))
            item = chunks.pop()
        return list
    elif item == 'i':
        item = chunks.pop()
        num = ''
        while item != 'e':
            num  += item
            item = chunks.pop()
        return int(num)
    elif decimal_match.search(item):
        num = ''
        while decimal_match.search(item):
            num += item
            item = chunks.pop()
        line = ''
        for i in range(int(num)):
            line += chunks.pop()
        return line
    raise ValueError("Invalid input!")
