import os
from pathlib import Path


def longest_common_suffix(s1, s2):
    if not isinstance(s1, str):
        s1 = str(s1)
    if not isinstance(s2, str):
        s2 = str(s2)
    if not s1 or not s2:
        return ""
    min_len = min(len(s1), len(s2))
    count = 0
    for i in range(1, min_len + 1):
        if s1[-i] == s2[-i]:
            count += 1
        else:
            break
    return s1[-count:] if count else ""


def split_path(filepath):
    path = os.path.dirname(filepath)  # 获取路径部分
    filename_ = os.path.basename(filepath)  # 获取文件名部分
    filename = os.path.splitext(filename_)[0]  # 去掉文件后缀
    suffix = os.path.splitext(filename_)[1]  # 获取文件后缀
    return path, filename, suffix
