# -*- coding: utf-8 -*-

import ipaddress
import struct
import socket
import logging


class SockAddr(object):
    '''
    Für diese Klasse ist leider keine Dokumentation verfügbar.
    '''

    @classmethod
    def convertToAddress(cls, syscall_infos):
        if syscall_infos["info_family"] in [2, 10] and syscall_infos["info_socktype"] in [1, 2, 3]:
            # addrinfo block
            address = cls.mem2addr(syscall_infos["info_family"], syscall_infos["info_ipv4"], syscall_infos["info_ipv6_1"], syscall_infos["info_ipv6_2"], syscall_infos["info_port"])
            return address
        elif syscall_infos["sock_family"] in [2, 10]:
            # sockaddr_in or sockaddr_in6 block
            address = cls.mem2addr(syscall_infos["sock_family"], syscall_infos["sock_ipv4"], syscall_infos["sock_ipv6_1"], syscall_infos["sock_ipv6_2"], syscall_infos["sock_port"])
            return address
        else:
            # Other
            return (None, None)
        return (None, None)

    @classmethod
    def mem2addr(cls, family, mem_ipv4, mem_ipv6_1, mem_ipv6_2, mem_port):
        address = None
        port = None

        if family == 2:
            address = cls.int2ipv4(mem_ipv4)
        elif family == 10:
            address = cls.int2ipv6(mem_ipv6_1, mem_ipv6_2)
        try:
            port = socket.htons(mem_port)
        except OverflowError:
            logging.error("")

        return (address, port)

    @classmethod
    def int2ipv4(cls, input):
        # big endian to little endian
        new_int = struct.unpack("<L", input.to_bytes((input.bit_length() + 7) // 8, 'big'))[0]
        return str(ipaddress.IPv4Address(new_int))

    @classmethod
    def int2ipv6(cls, input1, input2):
        def orderIPv6(input):
            array = [input[i:i + 8] for i in range(0, len(input), 8)]
            ret = ""
            for x in reversed(array):
                ret += x
            return ret

        bin_ipv6_1 = '{0:064b}'.format(input1)
        bin_ipv6_2 = '{0:064b}'.format(input2)
        part1 = orderIPv6(bin_ipv6_1)
        part2 = orderIPv6(bin_ipv6_2)
        conv_bin = str(part1) + str(part2)
        conv_int = int(conv_bin, 2)
        return str(ipaddress.IPv6Address(conv_int))
