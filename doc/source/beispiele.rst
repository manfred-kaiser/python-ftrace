**********
Beispiele
**********

Sys_Execve, Sys_Setuid und Sched_process_fork loggen
=====================================================

Das folgende Beispiel soll die einfachste Anwendung
der Library FTrace zeigen. Das Auftreten der SysCalls
Sys_Execve, Sys_Setuid und Sched_Process_Fork wird geloggt.

.. code:: python

  # -*- coding: utf-8 -*-
  import ftrace

  def main():
    ftrace = ftrace.FTrace()
    ftrace.tracer = ftrace.tracers.NopTracer()
    ftrace.reset()
    ftrace.setup()
    ftrace.tracer.syscalls = [
        ftrace.syscalls.Sys_Execve(),
        ftrace.syscalls.Sys_Setuid(),
        ftrace.syscalls.Sched_Process_Fork()
    ]

    try:
        for data in ftrace.get_output():
            print(data)
    except KeyboardInterrupt:
        print("\nstopping...")

    ftrace.reset()


  if __name__ == "__main__":
    main()


Ausgabe
-------

Bei Aufruf des Kommandos ``sudo ls``, sollte das Programm in etwa diese Ausgabe produzieren:

::

    {'caller_name': 'bash', 'caller_pid': 4588, 'timestamp': 6788.794592, 'kname': 'sched_process_fork', 'syscall': 'sched_process_fork', 'called_name': 'bash ', 'called_pid': 7291}
    {'caller_name': '<...>', 'caller_pid': 7291, 'timestamp': 6788.795131, 'kname': 'sys_execve_kprobe', 'syscall': 'SyS_execve', 'filename': '/usr/bin/sudo', 'argv': ['sudo', 'ls', '(fault)', '(fault)', '']}
    {'caller_name': 'sudo', 'caller_pid': 7291, 'timestamp': 6794.881823, 'kname': 'sys_setuid_kprobe', 'syscall': 'SyS_setuid', 'uid': 0}
    {'caller_name': 'sudo', 'caller_pid': 7291, 'timestamp': 6794.882534, 'kname': 'sched_process_fork', 'syscall': 'sched_process_fork', 'called_name': 'sudo ', 'called_pid': 7292}
    {'caller_name': 'sudo', 'caller_pid': 7292, 'timestamp': 6794.882801, 'kname': 'sys_execve_kprobe', 'syscall': 'SyS_execve', 'filename': '/bin/ls', 'argv': ['ls', '(fault)', '(fault)', '(fault)', '(fault)']}

Für Genauere Infos, wie diese Ausgabe zu interpretieren ist, siehe `sudo vs. su <./sudo_vs_su.html>`_

Execsnoop
=========

Das Perftool Execsnoop gibt die PID, PPID und den Namen jedes Programms an,
das aufgerufen wird. Mit der Library FTrace kann dieses Tool mit
Leichtigkeit nachgebildet werden:

.. code:: python

    # -*- coding: utf-8 -*-
    import ftrace

    def main():
        processes = {}

        ftrace = ftrace.FTrace()
        ftrace.tracer = ftrace.tracers.NopTracer()
        ftrace.reset()
        ftrace.setup()
        ftrace.tracer.syscalls = [
            ftrace.syscalls.Sys_Execve(),
            ftrace.syscalls.Sched_Process_Fork()
        ]

        print("pid  ppid: name")

        try:
            for data in ftrace.get_output():
                if (data is not None and data["kname"] == "sys_execve_kprobe"):
                    print("{} {}: {}".format(data["caller_pid"], processes[data["caller_pid"]] if (data["caller_pid"] in processes) else "----", data["filename"]))
                elif (data["kname"] == "sched_process_fork"):
                    processes[data["called_pid"]] = data["caller_pid"]
        except KeyboardInterrupt:
            print("\nstopping...")

        ftrace.reset()


    if __name__ == "__main__":
        main()


Ausgabe
--------

Eine mögliche Ausgabe könnte wie folgt aussehen:

.. code::

    pid  ppid: name
    7442 7221: /bin/ls
    7445 7443: /bin/bash
    7447 7446: /usr/bin/lesspipe
    7448 7447: /usr/bin/basename
    7450 7449: /usr/bin/dirname
    7452 7451: /usr/bin/dircolors
    7453 7445: /bin/ls

Ursprüngliche UID nach sudo herausfinden
========================================

Wenn wir den oberen Code leicht abändern,
ist es möglich, die "ursprüngliche" UID
des Prozesses herauszufinden.
Nehmen wir an, wir führen ``sudo ls`` mit der UID 1000 aus,
dann ist die UID von ls 0, aber die urspüngliche UID ist
nachwievor 1000.

Ein Schritt, der im obigen code noch nicht durchgeführt wird,
ist, das Verzeichnis /proc auszulesen, um anfangs Informationen
über alle Prozesse zu erhalten. Das hat mit ftrace nichts zu tun,
ist aber für das Beispiel nötig.

.. code:: python

    # -*- coding: utf-8 -*-
    import ftrace
    import os
    import subprocess
    import re

    class ProcessTreeBuilder(object):
        _process_dict = {} # {pid: process_instance}

        _regex_process = re.compile(r"\d+")
        _regex_name = re.compile(r"Name:\\t(.+?)\\n")
        _regex_pid = re.compile(r"\\nPid:\\t(\d+?)\\n")
        _regex_ppid = re.compile(r"\\nPPid:\\t(\d+?)\\n")
        _regex_uid = re.compile(r"\\nUid:\\t(\d+)\\t\d+\\t\d+\\t\d+\\n")

        def __init__(self):
            for process in os.listdir("/proc"):
                if (self._regex_process.match(process)):
                    with open(os.path.join("/proc", process, "status"), "rb") as f:
                        status = str(f.read())

                        name = self._regex_name.search(status).group(1)
                        pid = int(self._regex_pid.search(status).group(1))
                        ppid = int(self._regex_ppid.search(status).group(1))
                        uid = int(self._regex_uid.search(status).group(1))

                        p = Process(pid, ppid, uid, name)
                        self._process_dict.update({pid: p})

        def fork(self, ppid, cpid):
            if (not ppid in self._process_dict):
                print("unknown process {}".format(ppid))
                return

            self._process_dict[cpid] = Process(cpid, ppid, self._process_dict[ppid].uid, self._process_dict[ppid].name)
        def execve(self, pid, name):
            if (not pid in self._process_dict):
                print("unknown process {}".format(pid))
                return

            self._process_dict[pid].name_list.append(name)

        def setuid(self, pid, uid):
            if (not pid in self._process_dict):
                print("unknown process {}".format(pid))
                return

            self._process_dict[pid].uid_list.append(uid)

        def get_last_nonroot_uid(self, pid):
            if (not pid in self._process_dict):
                print("unknown process {}".format(pid))
                return

            p = self._process_dict[pid]

            while (p.pid > 1):
                for uid in p.uid_list[::-1]:
                    if (uid != 0):
                        return uid

                p = self._process_dict[p.ppid]

            return False

        def get_process(self, pid):
            if (not pid in self._process_dict):
                print("unknown process {}".format(pid))
                return

            return self._process_dict[pid]

    class Process(object):
        def __init__(self, pid, ppid, uid, name):
            self.pid = pid
            self.ppid = ppid
            self.uid_list = [uid]
            self.name_list = [name]

        @property
        def uid(self):
            return self.uid_list[-1]

        @property
        def name(self):
            return self.name_list[-1]


    def main():
        ptb = ProcessTreeBuilder()

        ftrace = ftrace.FTrace()
        ftrace.tracer = ftrace.tracers.NopTracer()
        ftrace.reset()
        ftrace.setup()
        ftrace.tracer.syscalls = [
            ftrace.syscalls.Sys_Execve(),
            ftrace.syscalls.Sys_Setuid(),
            ftrace.syscalls.Sched_Process_Fork()
        ]

        try:
            for data in ftrace.get_output():
                if (data["kname"] == "sys_execve_kprobe"):
                    ptb.execve(data["caller_pid"], data["filename"])

                    print("{}: original uid {}".format(data["filename"], ptb.get_process(data["caller_pid"]).uid))
                elif (data["kname"] == "sched_process_fork"):
                    ptb.fork(data["caller_pid"], data["called_pid"])
                elif (data["kname"] == "sys_setuid"):
                    ptb.setuid(data["caller_pid"], data["uid"])
        except KeyboardInterrupt:
            print("\nstopping...")

        ftrace.reset()


    if __name__ == "__main__":
        main()

Ausgabe
-------

Wenn unser Benutzer die UID 1000 hat, erhalten wir
auf das Aufrufen von ``sudo ls`` hin folgende Ausgabe:

.. code::

    /usr/bin/sudo: original uid 1000
    /bin/ls: original uid 1000


Ausführung von Programmen abbrechen
===================================

.. code:: python

  # -*- coding: utf-8 -*-
  import ftrace
  import os

  def main():
        ftrace = ftrace.FTrace()
        ftrace.tracer = ftrace.tracers.NopTracer()
        ftrace.reset()
        ftrace.setup()
        ftrace.tracer.syscalls = [
            ftrace.syscalls.Sys_Execve(),
            ftrace.syscalls.Sys_Setuid(),
            ftrace.syscalls.Sched_Process_Fork()
        ]

        try:
            for data in ftrace.get_output():
                if (data["kname"] == "sys_execve_kprobe"):
                    if (data["filename"] in ["/bin/ls", "/usr/bin/vim"]):
                        os.kill(data["caller_pid"], 9)
        except KeyboardInterrupt:
            print("\nstopping...")

        ftrace.reset()


  if __name__ == "__main__":
        main()


Ausgabe
-------

Nachdem wir unser Programm gestartet haben, sollte es nicht mehr möglich sein,
die Kommandi ``ls`` oder ``vim`` auszuführen.

::

    benutzer@computer:~$ ls
    Killed
    benutzer@computer:~$ vim
    Killed
