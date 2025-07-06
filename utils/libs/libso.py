import ctypes
import inspect
from functools import wraps
from typing import get_type_hints

# Python 类型到 ctypes 的映射
type_map = {
    int: ctypes.c_int,
    float: ctypes.c_double,
    str: ctypes.c_char_p,  # 注意：需传入 bytes
    bool: ctypes.c_bool,
    None: None,
}


def libso(lib_and_func: str):
    lib_path, c_func_name = lib_and_func.split("->")

    def decorator(py_func):
        sig = inspect.signature(py_func)
        hints = get_type_hints(py_func)

        # 加载共享库
        clib = ctypes.CDLL(lib_path)

        # 获取 C 函数
        c_func = getattr(clib, c_func_name)

        # 参数类型
        argtypes = [type_map[hints[param.name]] for param in sig.parameters.values()]
        c_func.argtypes = argtypes

        # 返回类型
        ret_type = type_map.get(hints.get("return", None), ctypes.c_void_p)
        c_func.restype = ret_type

        @wraps(py_func)
        def wrapper(*args):
            # 预处理字符串参数（转为 bytes）
            conv_args = [arg.encode() if isinstance(arg, str) else arg for arg in args]
            return c_func(*conv_args)

        return wrapper

    return decorator
