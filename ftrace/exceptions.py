# -*- coding: utf-8 -*-

class PWDException(Exception):
    def __init__(self, msg=""):
        if (len(msg) > 0):
            print(self.__class__.__name__ + ": " + msg)
        else:
            print(self.__class__.__name__)


class RootRequiredException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


class WriteFileException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


class ReadFileException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


class ReadPipeException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


class ProcessNotFoundException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)


class VersionException(Exception):
    def __init__(self, msg=""):
        super().__init__(msg)
