# -*- coding: utf-8 -*-

from ftrace.parsers import SysCallParser
from ftrace.syscalls import SysCall
import logging


class Tracer(object):
    '''
    Tracer ist die Parent-Klasse aller Tracer.
    Jede Tracer-Klasse soll einen Tracer des Kernelfeatures FTrace representieren.

    Um einen Tracer im Kernelfeature zu setzen, ist es notwendig dessen Namen
    in /sys/kernel/debug/tracing/current_tracer zu schreiben.
    Da sich der Name eines Tracers dieser Library aus dem Namen der Klasse ergibt,
    muss der Klassenname beim Implementieren neuer Tracer einem Bestimmten Schema folgen.
    Siehe Property 'name'

    In Zukunft könnten folgende andere tracer implementiert werden:

    * Hwlat
    * Blk
    * Mmiotrace
    * Function_Graph
    * Wakeup_Dl
    * Wakeup_Rt
    * Wakeup
    * Function

    (/sys/kernel/debug/tracing/available_tracers)
    '''
    parser = None
    '''
    Die Eigenschaft parser muss eine Instanz einer Subklasse von Parser sein.
    Momentan ist nur der SyscallParser vorhanden.
    '''
    _setup = False

    def setup(self):
        self._setup = True

    def reset(self):
        self._setup = False

    @property
    def name(self):
        '''
        Die Property 'name' soll den Namen des Tracers zurückliefern, so wie er für die
        Verwendung im Kernelfeature benötigt wird.
        Der Name ergibt sich aus dem Klassennamen.

        Beispiel:
        Das Kernelfeature stellt einen tracer 'nop' zur verfügung.
        => Eine Tracer-Klasse, die diesen (Kernelfeature-)Tracer repäsentieren soll,
        muss NopTracer oder Nop_Tracer heißen (case-insensitive und underscore optional).
        '''
        return self.__class__.__name__.lower().split("tracer")[0].split("_")[0]


class NopTracer(Tracer):
    '''
    Der NopTracer stellt den Tracer 'nop' des Kernelfeatures nach.
    Mit ihm ist es möglich, SysCalls zu tracen.

    Welche SysCalls getracet werden sollen, wird durch die Property 'syscalls' definiert.
    Siehe Property 'syscalls'
    '''
    def __init__(self):
        logging.debug("initialising NopTracer")

        self._all_syscalls = {syscall().kname: syscall() for syscall in SysCall.__subclasses__()}  # {kname: instance}
        self._enabled_syscalls = []  # list of knames
        self.parser = SysCallParser(self._all_syscalls)

        logging.debug("initialised NopTracer")

    def setup(self):
        if (self._setup):
            return

        logging.debug("setting up NopTracer")

        for syscall in self._all_syscalls.values():
            syscall.registered = True
        for kname, syscall in self._all_syscalls.items():
            syscall.enabled = (kname in self._enabled_syscalls)

        self._setup = True

        logging.debug("NopTracer set up")

    def reset(self):
        if (not self._setup):
            return

        logging.debug("resetting NopTracer")

        for syscall in self._all_syscalls.values():
            syscall.enabled = False
        for syscall in self._all_syscalls.values():
            syscall.registered = False

        self._setup = False

        logging.debug("NopTracer reset")

    @property
    def syscalls(self):
        '''
        Die Property 'syscalls' stellt die enableten SysCalls dar.
        Beim Setzen wird auf jeden Fall der neue Wert gespeichert
        und, sollte der Tracer aufgesetzt sein - id est, alle zur
        Verfügung stehenden SysCalls sind registriert -, werden die
        gewählten SysCalls auch enablet.
        Ist der Tracer noch nicht aufgesetzt würde das enablen eines
        SysCalls zu einem Fehler führen.
        '''
        return self._enabled_syscalls

    @syscalls.setter
    def syscalls(self, val):
        logging.debug("setting NopTracer.syscalls")

        if (not isinstance(val, list)):
            raise TypeError("list expected, {} given".format(type(val)))

        self._enabled_syscalls = []
        for syscall in val:
            if (not isinstance(syscall, SysCall)):
                raise TypeError("SysCall expected, {} given".format(type(syscall)))
            self._enabled_syscalls.append(syscall.kname)

        if (self._setup):
            for kname, syscall in self._all_syscalls.items():
                syscall.enabled = (kname in self._enabled_syscalls)
