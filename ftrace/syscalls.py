# -*- coding: utf-8 -*-

import os.path
from enum import Enum
from collections import OrderedDict

from ftrace.filehelper import PWDFile
from ftrace.syscallparam import SysCallParam
from ftrace.parsers import StandardSysCallParser, SchedProcessForkParser, IPAdressParser


class REGISTERS(Enum):
    '''
    Diese Enum wird dazu verwendet, die Register für die KProbes zu definieren.
    Die Register in der KProbe haben die selbe Reihenfolge, wie in diesem Enum.
    Da sich der Name des Registers der Kprobe direkt aus dem namen des entsprechenden Wertes im
    Enum ergibt, ist eine korrekte Definition dieses Enums zwingend erforderlich.
    Sollten mehr Parameter ausgelesen werden wollen als es Register gibt, müssen
    weitere Register definiert werden.
    '''
    di = 0
    si = 1
    dx = 2

    def get_name(self):
        return "%{}".format(self.name)


class SysCall(object):
    '''
    SysCall ist die Parent-Klasse aller SysCalls, wie Sys_Execve oder Sys_Ptace.
    Ein SysCall kann registriert und enablet sein.
    Um einen SysCall zu en/disablen muss er registriert sein, andernfalls kommt
    es zu einem Fehler
    '''

    _WORKINGDIR = "/sys/kernel/debug/tracing"

    STANDARD_FIELDS = OrderedDict([  # shall not be included in kprobe but are needed to parse information about syscall
        ("caller_name", SysCallParam.string_t),
        ("caller_pid", SysCallParam.pid_t),
        ("timestamp", SysCallParam.float_t),
        ("kname", SysCallParam.string_t),
        ("syscall", SysCallParam.string_t)
    ])
    '''
    STANDARD_FIELDS werden vom Kernelfeature FTRace ausgegeben, ohne sie als eigene
    Parameter definiert zu haben. Daher werden sie seperat behandelt.
    '''
    ARGCOUNT = 3
    '''
    ARGCOUNT gibt an, wie viele Parameter in einer Liste enthalten sein sollen,
    falls in den Paramtern Listen entalten sind.
    Durch diese Art der Implementierung ist es möglich, für jeden SysCall
    eine bestimmte Anzahl an Listenelementen zu setzen und diese auch im
    laufenden Betrieb zu ändern.

    Beispiel:
    ein Parameter ist wie folgt definiert:
    ("mein_parameter", SysCallParam.string_list_t)
    und ARGCOUNT = 3,
    dann werden 3 strings aus dieser Liste ausgelesen
    und im Ausgabe-Dictionary dargestellt als:
    {..., "mein_parameter": ["string1", "string2", "string3", ...], ...}.
    '''
    PARSER = StandardSysCallParser()
    '''
    Der PARSER ist die Klasse, die
    verwendet werden soll, um einen bestimmten SysCall zu parsen.
    Es stehen momentan folgende Parser zur Verfügung:

    * StandardSysCallParser
    * SchedProcessForkParser
    * IPAdressParser

    Standardmäßig wird der StandardSysCallParser verwendet.
    Ausnahmen sind z.B.:

    * sched_processfork
      weil es sich dabei nicht um einen SysCall handelt und ihre Logzeile anders aufgebaut ist als
      die eines normalen SysCalls
    * sys_connect und sys_accept
      weil für das Parsen einer IP-Adresse viele Informationen aus einem einzigen Register
      ausgelesen werden müssen, die aber unterschiedliche Datentypen aufweisen und deshalb nicht
      mit einer Liste ausgelensen können werden. Außerdem müssen diese Daten danach noch
      verarbeitet werden.
    '''

    PARAMS = OrderedDict([])
    '''
    PARAMS sind die Parameter eines SysCalls (ohne die StandardFields).
    Sie werden in der Form ``(Name, Typ)`` angegeben.
    Z.B.:

    .. code:: python

        PARAMS = OrderedDict([
            ("filename", SysCallParam.string_t),
            ("argv", SysCallParam.string_list_t)
        ])

    Die Typen sind in `SysCallParam <#module-ftrace.syscallparam>`_ definiert, oder ``None``.

    '''

    def __init__(self):
        self._file_set_kprobes = PWDFile(os.path.join(self._WORKINGDIR, "kprobe_events"))
        self._file_enable_kprobe = PWDFile(os.path.join(self._WORKINGDIR, "events/kprobes", self.kname, "enable"))

    @property
    def kprobe(self):
        '''
        Die Property 'kprobe' ist ein String, der die gesamte Kprobe eines SysCalls enthält.
        Sie setzt sich zusammen aus dem KName, dem SysCall-Namen und allen Argumenten/Parametern.
        '''
        args = ""

        if (self.PARAMS):
            for param_name, param_typ, reg in zip(self.PARAMS.keys(), self.PARAMS.values(), REGISTERS):
                if (param_typ):
                    args = " ".join([args, param_typ.get_kprobe_arg(reg, self.ARGCOUNT)])

        return "p:kprobes/{} {} {}".format(self.kname, self.syscall, args)

    @property
    def syscall(self):
        '''
        Die Property 'syscall' gibt den Namen des SysCalls zurück.
        Dieser wird durch den Klassennamen ermittelt,
        daher ist der Klassenname nicht "frei wählbar".
        '''
        return self.__class__.__name__.lower()

    @property
    def kname(self):
        '''
        Der KName ist der eindeutige Name einer Kprobe.
        Er ergibt sich aus dem Namen des SysCalls und "_kprobe".
        z.B.: sys_execve -> "sys_execve_kprobe"
        '''
        return "{}_kprobe".format(self.syscall)

    @property
    def valid_params(self):  # wie hieß dieses zeug dass sich den rückgabewert von funktionen merkt?
        '''
        Die Property 'valid_params' gibt alle Parameter des SysCalls zurück,
        die nicht None sind, ohne die STANDARD_FIELDS
        und dient eher der Convenience.
        '''
        return OrderedDict([(k, v) for k, v in self.PARAMS.items() if v])

    @property
    def registered(self):
        '''
        Die Property 'registered' gibt an, ob ein SysCall registriert ist.
        Bei Setzen auf False ist zu beachten, dass der SysCall nicht enablet sein darf,
        ansonsten kommt es zu einem Fehler.

        Ein SysCall ist genau dann registriert, wenn seine KProbe in
        /sys/kernel/debug/tracing/kprobe_events geschrieben ist.
        '''
        return self._file_set_kprobes.check_for_kprobe(self.kname)

    @registered.setter
    def registered(self, val):
        if (not val and self.enabled):
            raise ValueError("Setting registered to false is only possible if enabled is false")

        with open("/sys/kernel/debug/tracing/kprobe_events"):  # why is this file not used?
            self._file_set_kprobes.write("{}{}".format(self._file_set_kprobes.read(), (self.kprobe if val else "-:kprobes/{}".format(self.kname))))  # "appends" string by writing whole file again, using writing mode 'a' did not work, check for better solution

    @property
    def enabled(self):
        '''
        Die Property 'enabled' gibt an, ob ein SysCall enablet ist.
        Bei Setzen auf True ist zu beachten, dass der SysCall registriert sein muss,
        ansonsten kommt es zu einem Fehler.

        Ein SysCall ist genau dann enablet, wenn in
        /sys/kernel/debug/tracing/events/kprobes/SYSCALLNAME/enabled der Wert '1' steht.
        '''
        return self._file_enable_kprobe.read_bool()

    @enabled.setter
    def enabled(self, val):
        if self.registered:
            self._file_enable_kprobe.write(val)
        else:
            raise ValueError("Can't enable/disable a kpobe that is not registered")


class Sys_Execve(SysCall):
    PARAMS = OrderedDict([
        ("filename", SysCallParam.string_t),
        ("argv", SysCallParam.string_list_t)
    ])
    ARGCOUNT = 5


class Sched_Process_Fork(SysCall):
    '''
    Sched_process_fork ist kein SysCall, aber es ist möglich, sie so weit zu abstrahieren,
    dass man so tun kann, als ob sie einer wäre. Deshalb stellt sie eine starke Ausnahme dar
    und es ist nötig, einige Funktionen der Parent-Klasse SysCall zu überschreiben.
    '''
    PARSER = SchedProcessForkParser()
    PARAMS = OrderedDict([
        ("called_name", SysCallParam.string_t),
        ("called_pid", SysCallParam.pid_t)
    ])

    def __init__(self):
        super().__init__()
        self._file_enable_kprobe = PWDFile("/sys/kernel/debug/tracing/events/sched/sched_process_fork/enable")

    @property
    def kname(self):
        return "sched_process_fork"

    @property
    def kprobe(self):
        return ""

    @property
    def registered(self):
        return True

    @registered.setter
    def registered(self, val):
        pass


class Sys_Setuid(SysCall):
    PARAMS = OrderedDict([
        ("uid", SysCallParam.uid_t)
    ])


class Sys_Exit(SysCall):
    PARAMS = OrderedDict([
        ("error_code", SysCallParam.int_t)
    ])


class Sys_Exit_Group(SysCall):
    PARAMS = OrderedDict([
        ("error_code", SysCallParam.int_t)
    ])


class Sys_Kill(SysCall):
    PARAMS = OrderedDict([
        ("pid", SysCallParam.pid_t),
        ("sig", SysCallParam.int_t)
    ])


class Sys_Ptrace(SysCall):
    PARAMS = OrderedDict([
        ("request", None),
        ("pid", SysCallParam.long_t),
        ("addr", None)
    ])


class Sys_Setreuid(SysCall):
    PARAMS = OrderedDict([
        ("ruid", SysCallParam.uid_t),
        ("euid", SysCallParam.uid_t)
    ])


class Sys_Connect(SysCall):
    '''
    Sys_Connect stellt insofern eine Ausnahme dar als die Parameter anders
    behandelt werden: Es werden zwar viele Parameter in PARAMS angegeben,
    diese sind aber nur dazu da, dass eine IP-Adresse und ein Port ermittelt
    werden können. In der Ausgabe steht nur noch:
    {..., "addr": ("1.2.3.4", 5678), ...}
    '''
    PARSER = IPAdressParser()
    PARAMS = OrderedDict([
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
    ])

    @property
    def kprobe(self):
        args = " ".join([arg for arg in self.PARAMS.values()])
        return "p:kprobes/{} {} {}".format(self.kname, self.syscall, args)


class Sys_Accept(SysCall):
    '''
    Siehe Sys_Connect
    '''
    PARSER = IPAdressParser()
    PARAMS = OrderedDict([
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
    ])

    @property
    def kprobe(self):
        args = " ".join([arg for arg in self.PARAMS.values()])
        return "p:kprobes/{} {} {}".format(self.kname, self.syscall, args)


class Sys_Setgid(SysCall):
    PARAMS = OrderedDict([
        ("gid", SysCallParam.gid_t)
    ])


class Sys_Personality(SysCall):
    PARAMS = OrderedDict([
        ("personality", SysCallParam.unsigned_int_t)
    ])


class Sys_Open(SysCall):
    PARAMS = OrderedDict([
        ("filename", SysCallParam.string_t),
        ("flags", SysCallParam.int_t),
        ("mode", SysCallParam.int_t)
    ])


class Sys_Close(SysCall):
    PARAMS = OrderedDict([
        ("fd", SysCallParam.unsigned_int_t)
    ])


class Sys_Umask(SysCall):
    PARAMS = OrderedDict([
        ("mask", SysCallParam.int_t)
    ])


class Sys_Tkill(SysCall):
    PARAMS = OrderedDict([
        ("pid", SysCallParam.pid_t),
        ("sig", SysCallParam.int_t)
    ])
