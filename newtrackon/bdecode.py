from collections import OrderedDict

# Recursive type alias for bencoded values
BDecodedValue = OrderedDict[bytes, "BDecodedValue"] | list["BDecodedValue"] | int | bytes | None


TOK_DICT: bytes = b"d"
TOK_LIST: bytes = b"l"
TOK_INT: bytes = b"i"
TOK_END: bytes = b"e"
TOK_STR_SEP: bytes = b":"


def bdecode(data: bytes) -> BDecodedValue:
    """Decode a bencoded value, preserving strings and dictionary keys as bytes."""
    return Decoder(data).decode()


class Decoder:
    def __init__(self, data: bytes) -> None:
        self.index: int = 0
        self.data: bytes = data

    def decode(self) -> BDecodedValue:
        # decode the bencoded data
        c = self.peek()  # get the next character
        if c is None:
            raise EOFError()
        elif c == TOK_DICT:
            _ = self.read(1)  # read the token
            return self.decode_dict()
        elif c == TOK_LIST:
            _ = self.read(1)  # read the token
            return self.decode_list()
        elif c == TOK_INT:
            _ = self.read(1)  # read the token
            return self.decode_int()
        elif c in b"0123456789":  # the number indicates start of str (tells len(str))
            return self.decode_str()
        elif c == TOK_END:
            return None
        else:
            raise RuntimeError("Could not bdecode data, probably invalid format")

    # get the next byte
    def peek(self) -> bytes | None:
        if self.index + 1 >= len(self.data):  # index is passed the end of the data
            return None
        return self.data[self.index : self.index + 1]

    # read the data for the length
    def read(self, length: int) -> bytes:
        if self.index + length > len(self.data):
            raise RuntimeError()
        result = self.data[self.index : self.index + length]
        self.index += length
        return result

    # read until the first occurence of the token
    def read_until(self, token: bytes) -> bytes:
        # get the index of the token starting from where last left off
        loc = self.data.find(token, self.index)
        if loc == -1:  # token not found
            raise RuntimeError()
        # token found, loc is the index of it
        result = self.data[self.index : loc]
        self.index = loc + 1  # move index to just past loc read up to
        return result

    # decodes bencoded data into a Python OrderedDict
    def decode_dict(self) -> OrderedDict[bytes, BDecodedValue]:
        result: OrderedDict[bytes, BDecodedValue] = OrderedDict()
        while self.data[self.index : self.index + 1] != TOK_END:
            key = self.decode()  # decode the key
            if not isinstance(key, bytes):
                raise TypeError("Dict key must be bytes in bencoded data")
            item = self.decode()  # decode the item
            result[key] = item  # add the key item pair to the dict
        _ = self.read(1)  # read the end token
        return result

    # decodes bencoded data into a Python list
    def decode_list(self) -> list[BDecodedValue]:
        result: list[BDecodedValue] = []
        while self.data[self.index : self.index + 1] != TOK_END:
            item = self.decode()  # decode an item
            result.append(item)  # add to the list
        _ = self.read(1)  # read the end token
        return result

    # decode bencoded data into a Python int
    def decode_int(self) -> int:
        encoded = self.read_until(TOK_END)
        if encoded.startswith(b"-0") or (len(encoded) > 1 and encoded.startswith(b"0")):
            raise RuntimeError("Invalid bencoded integer: leading zero or negative zero")
        return int(encoded)

    # decode the bencoded data into a Python string
    def decode_str(self) -> bytes:
        length = int(self.read_until(TOK_STR_SEP))  # get the length of str
        return self.read(length)  # read that length
