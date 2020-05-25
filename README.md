# Python ftrace Library

`ftrace` is a python library to read ftrace data from the Linux Kernel.

At this time it is only compatible with Kernel Version <=4!

```Diese Bibliothek wurde im Rahmen der Diplomarbeit "Proaktive Erkennung von Angriffen auf Endgeräte anhand von Debugging-Informationenvon Systemcalls des Linux Kernels" von Toifl überarbeitet und als Open Source zur Verfügung gestellt.```


## Installation

`pip install ftrace`


## Example

When a new process is created the name, pid and parent pid will be printed.

```python
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
```
