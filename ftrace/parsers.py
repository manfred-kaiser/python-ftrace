# -*- coding: utf-8 -*-

import re
import logging

from ftrace.sockaddr import SockAddr


class Parser(object):
    def parse(self, line):
        '''
        Die Funtion 'parse' wird aufgerufen, sobald eine neue Logzeile vom Kernelfeature FTrace
        zur Verfügung steht, und ist dafür verantwortlich, die darin enthaltenen Informationen
        bereitzustellen.
        '''


class SysCallParser(Parser):
    _last_line = b""

    _REGEXKNAME = re.compile(r"^.*?\s\S.*-(?=\d+\s*)\d+\s*\[\d*\].*\s[0-9.]*:\s*(\w*):\s*")

    def __init__(self, syscall_dict):
        self.syscalls = syscall_dict  # {kname:  instance}

    def parse(self, line):
        '''
        Parst eine Logzeile des NopTracers und gibt ein dictionary zurück, das alle
        Parameter und STANDARD_FIELDS mit Werten enthält,
        z.B.:

        .. code:: python

          {
              'caller_name': '<...>',
              'caller_pid': '5010',
              'kname': 'sys_execve_kprobe',
              'syscall': 'SyS_execve',
              'filename': '/bin/ls',
              'argv': ['ls', '--color=auto', '(fault)', '(fault)', 'git merge dev/library']
          }

        Schematischer Ablauf:

        * Neue Zeile an variable 'last_line' anhängen
        * KName herausfinden
        * SysCall-Instanz mit passendem KName herausfinden
        * Aufruf der PARSING_FUNCTION des SysCalls (gibt entweder dictionary oder None zurück)
        * wenn Rückgabewert nicht None ist, dann last_line zurücksetzen und dictionary zurückgeben
        '''
        logging.debug("parsing new line {}".format(line))

        self._last_line += line
        kname = self._REGEXKNAME.match(str(self._last_line))

        if kname:
            kname = kname.group(1)

            if (kname not in self.syscalls):
                print("syscall unknown\nline: {}".format(line))
                return

            syscall = self.syscalls[kname]
            value_dict = syscall.PARSER.parse(syscall, self._last_line)
            if (value_dict):
                self._last_line = b""
                return value_dict


def _parse_standard_fields(syscall, line):
    '''
    Parst die STANDARD_FIELDS eines SysCalls
    '''
    _REGEXSYSCALLINFO = re.compile(r"^.*?\s(\S.*)-(?=\d+\s*)(\d+)\s*\[(\d*)\].*\s([0-9.]*):\s*(\w*):\s*\((.*?(?=\)))\)")
    matchsyscallinfo = _REGEXSYSCALLINFO.match(str(line))
    return [
        matchsyscallinfo.group(1),  # pname
        matchsyscallinfo.group(2),  # pid
        matchsyscallinfo.group(4),  # timestamp
        matchsyscallinfo.group(5),  # kname
        matchsyscallinfo.group(6).split("+")[0]  # syscall
    ]


def _fill_value_dict(parts, syscall):
    '''
    Nimmt die einzelnen Teile einer Logzeile und den passenden SysCall, und
    befüllt ein dictionary mit dessen Parametern und wandelt die Werte zum richtigen Typ um.
    '''
    vd = {}  # {name: wert richtigen typs}
    i = 0
    for param_name, param_type in dict(syscall.STANDARD_FIELDS, **syscall.valid_params).items():
        element = None
        if (not param_type.value.is_list):
            element = param_type.convert(parts[i])
            i += 1
        else:
            element = []
            for x in range(0, syscall.ARGCOUNT):
                element.append(param_type.convert(parts[i]))
                i += 1
        vd[param_name] = element
    return vd


class StandardSysCallParser(object):
    _REGEXARGS = re.compile(r"\sarg\d+=(.*?(?=\sarg\d+=|$|\\n'))")

    def parse(self, syscall, line):
        '''
        Diese Funktion parst gewöhnliche SysCalls.

        Schematischer Ablauf

        * parst zunächst nur die STANDARD_FIELDS
        * falls Argumente/Parameter gefunden werden konnten, werden diese angehängt
        * falls die Anzahl an Argumenten der erwarteten Anzahl entspricht, wird ein dictionary mit den Werten zurückgegeben
        '''
        parts = _parse_standard_fields(syscall, line)

        matchargs = self._REGEXARGS.findall(str(line))

        if matchargs:
            parts += matchargs

        expected_len = len(syscall.STANDARD_FIELDS) + sum((syscall.ARGCOUNT if param_typ.value.is_list else 1) for param_typ in syscall.valid_params.values())

        if (len(parts) == expected_len):
            last_arg = parts[-1]
            if not isinstance(list(syscall.valid_params.values())[-1].value.convert, str) or (
                (last_arg[0] == '"' and last_arg[-1] == '"') or (last_arg[0] == '(' and last_arg[-1] == ')')
            ):
                parts[len(syscall.STANDARD_FIELDS):] = [(v[1:-1] if (v[0] == '"' and v[-1] == '"') else v) for v in parts[len(syscall.STANDARD_FIELDS):]]  # unquote
                value_dict = _fill_value_dict(parts, syscall)
                return value_dict
        elif (len(parts) > expected_len):
            print("got more parts than expected")
            return


class SchedProcessForkParser(object):
    _REGEXFORK = re.compile(r"^.*?\s(\S.*)-(?=\d+\s*)(\d+)\s*\[(\d*)\].*\s([0-9.]*):\s*(sched_process_fork):\s*comm=(.*)\s*pid=(\d*)\s*child_comm=(.*)\s*child_pid=(\d*)")

    def parse(self, syscall, line):
        '''
        Diese Funktion ähnelt standard_syscall_parsing, aber ist auf sched_process_fork spezialisiert,
        da deren Logzeile einen etwas anderen Aufbau aufweist.
        '''
        matchfork = self._REGEXFORK.match(str(line))
        parts = [
            matchfork.group(1),  # pname
            matchfork.group(2),  # pid
            matchfork.group(4),  # timestamp
            matchfork.group(5),  # kname
            matchfork.group(5),  # syscall
            matchfork.group(8),  # name2
            matchfork.group(9)   # pid2
        ]

        return _fill_value_dict(parts, syscall)


class IPAdressParser(object):
    def parse(self, syscall, line):
        '''
        Diese Funktion ist dafür vorgesehen, aus den Informationen einer recht komplexen KProbe
        eine IP-Adresse und einen Port auszulesen.
        Die Parameter, die die Funktion beinhalten muss sind:

        .. code:: python

          ("info_family", "+4(%si):s32"),
          ("info_socktype", "+8(%si):s32"),
          ("info_ipv4", "+24(%si):u32"),
          ("info_ipv6_1", "+28(%si):u64"),
          ("info_ipv6_2", "+36(%si):u64"),
          ("info_port", "+22(%si):u16"),
          ("sock_ipv4", "+4(%si):u32"),
          ("sock_ipv6_1", "+8(%si):u64"),
          ("sock_ipv6_2", "+16(%si):u64"),
          ("sock_family", "+0(%si):s16"),
          ("sock_port", "+2(%si):u16")

        Das Rückgabe-Dictionary beinhaltet dann ein Element ``"addr": ("1.2.3.4", 5678)``

        '''
        parts = _parse_standard_fields(syscall, line)

        matchargs = self._REGEXARGS.findall(str(line))

        if matchargs:
            parts += [int(arg) for arg in matchargs]

        parts = {k: v for k, v in zip(list(syscall.STANDARD_FIELDS.keys()) + list(syscall.PARAMS.keys()), parts)}
        addr = SockAddr.convertToAddress(parts)

        value_dict = {k: v for k, v in zip(list(syscall.STANDARD_FIELDS.keys()) + ["adress"], list(parts.values())[:len(syscall.STANDARD_FIELDS)] + [addr])}
        return value_dict
