# -*- coding: utf-8 -*-

from enum import Enum
import platform


def cap_user_header(value_list):
    '''
    Noch nicht implementiert.
    Siehe SysCallParser.ip_adress_parsing()
    '''


class SysCallParam(Enum):
    '''
    Dieses Enum beinhaltet alle Typen, die SysCall-Parameter haben können.
    '''

    OFFSET = 8 if platform.architecture()[0] == '64bit' else 4

    class SysCallParamConfig():

        def __init__(self, func, format_string, is_list=False):
            self.convert = func
            self.format_string = format_string
            self.is_list = is_list

    uid_t = SysCallParamConfig(int, "{register}:u32")
    uid_list_t = SysCallParamConfig(int, "+{offset}({register}):u32", is_list=True)
    pid_t = SysCallParamConfig(int, "{register}:u32")
    gid_t = SysCallParamConfig(int, "{register}:u32")
    gid_list_t = SysCallParamConfig(int, "+{offset}({register}):u32", is_list=True)
    int_t = SysCallParamConfig(int, "{register}:s32")
    int_pointer_t = SysCallParamConfig(int, "+0({register}):u32")
    unsigned_int_t = SysCallParamConfig(int, "{register}:u32")
    float_t = SysCallParamConfig(float, "")  # used for standard_fields
    string_t = SysCallParamConfig(str, "+0({register}):string")  # char* / const char*
    string_list_t = SysCallParamConfig(str, "+0(+{offset}({register})):string", is_list=True)  # const char *const []
    long_t = SysCallParamConfig(int, "{register}:s64")
    unsigned_long_t = SysCallParamConfig(int, "{register}:u64")
    cap_user_header_t = SysCallParamConfig(cap_user_header, "{register}:u64")  # to implement cap_user_header i recommend writing a seperate parsing-function, like the one for ip adresses

    def convert(self, arg):
        '''
        Convertiert einen String in den angegebenen Typ mit der Funktion convert in SysCallParamconfig
        '''
        return self.value.convert(arg)

    def get_kprobe_arg(self, register, argcount=1):
        '''
        Liefert einen String zurück, der in die Kprobe eingebunden werden kann und einen Parameter darstellt.
        '''
        return " ".join([
            self.value.format_string.format(
                register=register.get_name(),
                offset=x * self.OFFSET.value
            ) for x in range(0, argcount if self.value.is_list else 1)
        ])
