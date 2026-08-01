from collections import OrderedDict
from socket import AF_INET, AF_INET6, inet_ntop
from struct import unpack_from
from typing import TypedDict

# Recursive type alias for bencoded values
BDecodedValue = OrderedDict[bytes, "BDecodedValue"] | list["BDecodedValue"] | int | bytes | None


class PeerInfo(TypedDict):
    IP: str
    port: int


# Response type after bdecode processes and transforms the data
BDecodeResponse = dict[str, BDecodedValue | str | list[PeerInfo]]

TOK_DICT: bytes = b"d"
TOK_LIST: bytes = b"l"
TOK_INT: bytes = b"i"
TOK_END: bytes = b"e"
TOK_STR_SEP: bytes = b":"


def bdecode(data: bytes) -> BDecodeResponse:
    bdecoded_response = Decoder(data).decode()
    response: BDecodeResponse = {}
    if not isinstance(bdecoded_response, OrderedDict):
        raise RuntimeError("Could not extract the bencoded dict, probably invalid format")
    for key, value in bdecoded_response.items():
        response[key.decode()] = value

    if "peers" in response:
        peers_value = response["peers"]
        if isinstance(peers_value, bytes):
            response["peers"] = decode_binary_peers_list(peers_value, 0, AF_INET)

    if "peers6" in response:
        peers6_value = response["peers6"]
        if isinstance(peers6_value, bytes):
            response["peers6"] = decode_binary_peers_list(peers6_value, 0, AF_INET6)

    if "external ip" in response:
        external_ip = response["external ip"]
        if isinstance(external_ip, bytes):
            external_ip_length = len(external_ip)
            if external_ip_length == 4:
                response["external ip"] = inet_ntop(AF_INET, external_ip)
            elif external_ip_length == 16:
                response["external ip"] = inet_ntop(AF_INET6, external_ip)
            else:
                raise RuntimeError("Invalid external IP size")

    for key, value in response.items():
        if isinstance(value, bytes):
            response[key] = value.decode()

    return response


def decode_binary_peers_list(buf: bytes, offset: int, ip_family: int) -> list[PeerInfo]:
    peers: list[PeerInfo] = []
    peer_length = 6 if ip_family == AF_INET else 18
    binary_response = memoryview(buf)
    while offset != len(buf):
        if len(buf) < offset + peer_length:
            return peers
        ip_address = bytes(binary_response[offset : offset + peer_length - 2])
        ip_str = inet_ntop(ip_family, ip_address)
        offset += peer_length - 2
        port = unpack_from("!H", buf, offset)[0]
        offset += 2
        peers.append({"IP": ip_str, "port": port})
    return peers


class Decoder:
    def __init__(self, data: bytes) -> None:
        self.index = 0
        self.data = data

    def decode(self) -> BDecodedValue:
        # decode the bencoded data
        c = self.peek()  # get the next character
        if c is None:
            raise EOFError()
        elif c == TOK_DICT:
            self.read(1)  # read the token
            return self.decode_dict()
        elif c == TOK_LIST:
            self.read(1)  # read the token
            return self.decode_list()
        elif c == TOK_INT:
            self.read(1)  # read the token
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
                raise RuntimeError("Dict key must be bytes in bencoded data")
            item = self.decode()  # decode the item
            result[key] = item  # add the key item pair to the dict
        self.read(1)  # read the end token
        return result

    # decodes bencoded data into a Python list
    def decode_list(self) -> list[BDecodedValue]:
        result: list[BDecodedValue] = []
        while self.data[self.index : self.index + 1] != TOK_END:
            item = self.decode()  # decode an item
            result.append(item)  # add to the list
        self.read(1)  # read the end token
        return result

    # decode bencoded data into a Python int
    def decode_int(self) -> int:
        return int(self.read_until(TOK_END))  # read until the end token

    # decode the bencoded data into a Python string
    def decode_str(self) -> bytes:
        length = int(self.read_until(TOK_STR_SEP))  # get the length of str
        return self.read(length)  # read that length
