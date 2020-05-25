# -*- coding: utf-8 -*-

import os
import logging
from sys import version_info

from ftrace.tracers import Tracer
from ftrace.filehelper import PWDFile
from ftrace.exceptions import RootRequiredException, WriteFileException, VersionException


class FTrace(object):
    '''
    Für etwaige Informationen zur Benutzung, siehe `contetents/struktur <../struktur.html>`_

    Zum Debuggen einfach

    .. code:: python

      import logging
      logging.basicConfig(level=logging.DEBUG)

    einfügen.
    '''
    tracer = None

    _setup = False

    _WORKINGDIR = "/sys/kernel/debug/tracing"
    _file_enable_ftrace = PWDFile("/proc/sys/kernel/ftrace_enabled")
    _file_activate_ftrace = PWDFile(os.path.join(_WORKINGDIR, "tracing_on"))
    _file_current_tracer = PWDFile(os.path.join(_WORKINGDIR, "current_tracer"))
    _file_trace = PWDFile(os.path.join(_WORKINGDIR, "trace"))
    _file_pipe = PWDFile(os.path.join(_WORKINGDIR, "trace_pipe"))
    _file_set_kprobes = PWDFile(os.path.join(_WORKINGDIR, "kprobe_events"))
    _file_enable_all_kprobes = PWDFile(os.path.join(_WORKINGDIR, "events/kprobes/enable"))

    def __init__(self):
        logging.debug("initialising FTrace")

        if (os.geteuid() != 0):
            raise RootRequiredException()

        if (version_info < (3, 0)):
            raise VersionException("Python-version must be at least 3")

        logging.debug("initialised FTrace")

    def reset(self):
        '''
        Schematischer Ablauf:

        * Wenn Tracer gesetzt ist, resette ihn
        * aktiviere Kernelfeature FTrace
        * enable Kernelfeature FTrace
        * leere Ausagabe-File
        * disable alle KProbes (alle auf einmal, nicht einzeln)
        * entferne alle KProbes
        * enable wieder alle KProbes zusammen, sonst ist es später nicht mehr möglich sie einzeln zu enablen
        '''
        logging.debug("resetting FTrace")
        try:
            if (isinstance(self.tracer, Tracer)):
                self.tracer.reset()

            self._file_activate_ftrace.write(False)
            self._file_enable_ftrace.write(False)
            self._file_trace.write("")
            if (self._file_enable_all_kprobes.exists()):
                self._file_enable_all_kprobes.write(False)
            self._file_set_kprobes.write("")
            if (self._file_enable_all_kprobes.exists()):
                self._file_enable_all_kprobes.write(True)

            self._setup = False
        except WriteFileException:
            raise

        logging.debug("FTrace reset")

    def setup(self):
        '''
        Schematischer Ablauf:

        * überprüft, ob Tracer gesetzt ist
        * setzt current_tracer im Kernelfeature FTrace
        * enabled Kernelfeature FTrace
        * aktiviert Kernelfeature FTrace
        * duchläuft setup von Tracer
        '''

        logging.debug("setting up FTrace")

        if (not isinstance(self.tracer, Tracer)):
            raise ValueError("FTrace.tracer must be instance of (subclass of) Tracer, {} given".format(type(self.tracer)))

        self._file_current_tracer.write(self.tracer.name)
        self._file_enable_ftrace.write(True)
        self._file_activate_ftrace.write(True)
        self.tracer.setup()

        self._setup = True

        logging.debug("FTrace set up")

    def get_output(self):
        '''
        Liest die Pipe des Kernelfeatures FTrace aus, parst die eraltenen Zeilen
        und gibt das Ergebnis in Form eines Generators zurück.
        '''
        logging.debug("reading pipe of FTrace")
        with open('/sys/kernel/debug/tracing/trace_pipe', 'rb') as trace_pipe:
            while True:
                line = trace_pipe.readline()
                if not line:
                    continue

                yield self.tracer.parser.parse(line)
