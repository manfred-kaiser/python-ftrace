# -*- coding: utf-8 -*-

import os.path
import logging

from ftrace.exceptions import WriteFileException, ReadFileException


class PWDFile(object):
    '''
    Diese Klasse soll die Handhabung von Files erleichtern.
    Beim Instanzieren wird der Pfad einer Datei übergeben.
    '''
    def __init__(self, npath):
        self.path = npath

    def edit(self, val, writing_mode):
        '''
        Editiert ein File mit bestimmtem Modus und Wert.
        Der Wert kann bool, string oder eine Liste von Strings sein.
        '''
        logging.debug("editing file {} with mode '{}': {}".format(self.path, writing_mode, val))

        txt = ""
        if (isinstance(val, bool)):
            txt = ("1" if val else "0")
        elif (isinstance(val, str)):
            txt = val
        elif (isinstance(val, list)):
            for element in val:
                txt += str(val)
        else:
            raise WriteFileException("Unable to write to " + self.path + " -> Value must be boolean , string or list of strings" + type(val) + " given")

        try:
            with open(self.path, writing_mode) as f:
                f.write(txt)
        except FileNotFoundError:
            raise
        except Exception:
            raise WriteFileException("Unable to write to {} with mode \"{}\"-> Value: {}".format(self.path, writing_mode, val))

    def write(self, val):
        '''
        Schreib in ein File (Modus 'w').
        Siehe edit()
        '''
        self.edit(val, "w")

    def append(self, val):
        '''
        Hängt an ein File an (Modus 'a').
        Siehe edit()
        '''
        self.edit(val, "a")

    def read_bool(self):
        '''
        Liest ein File aus und gibt in Abhängigkeit vom Inhalt True oder False zurück.
        Die erlaubten Werte sind:

        * true, 1, yes
        * false, 0, no
        '''
        try:
            with open(self.path, "r") as f:
                val = f.read().strip().lower()

                if (val in ["true", "1", "yes"]):
                    return True
                elif (val in ["false", "0", "no"]):
                    return False
                else:
                    raise ValueError("read_bool(): couldn't convert \"{}\" into bool".format(val))
        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except Exception:
            raise ReadFileException("Unable to read {}".format(self.path))

    def check_for_kprobe(self, kname):
        '''
        Überprüft, ob eine KProbe in einem file enthalten ist, indem
        nach dem KName gesucht wird.
        '''
        try:
            with open(self.path, "r") as f:
                val = f.read()
                return kname in val
        except FileNotFoundError:
            raise
        except Exception:
            raise ReadFileException("Unable to read {}".format(self.path))

    def read(self):
        '''
        Liest den Inhalt einer Datei aus (Modus 'r')
        und gibt diesen zurück.
        '''
        try:
            with open(self.path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise
        except Exception:
            raise ReadFileException("Unable to read {}".format(self.path))

    def exists(self):
        '''
        Überprüft, ob ein File existiert (und ein File ist).
        '''
        return os.path.isfile(self.path)
