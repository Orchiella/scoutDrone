# coding=utf-8
from collections import defaultdict
import re


def Set(content, key, value):
    """
    更新或添加武器字段的值
    :param content: 原始字符串（如 "ammo:30,torch:2"）
    :param key: 字段名（如 "ammo"）
    :param value: 字段值（如 40）
    :return: 更新后的字符串（如 "ammo:40,torch:2"）
    """
    # 解析现有数据
    parsed = defaultdict(int)
    if content:
        for item in content.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                parsed[k] = int(v) if v.isdigit() else v  # 兼容数字和字符串

    # 更新字段
    parsed[key] = value

    # 重新序列化
    return ",".join("{}:{}".format(k, v) for k, v in parsed.iteritems())


def Get(content, key):
    """
    获取武器字段的值（不存在时返回0）
    :param content: 原始字符串（如 "ammo:30,torch:2"）
    :param key: 字段名（如 "ammo"）
    :return: 字段值（不存在则为0）
    """
    if not content:
        return 0

    for item in content.split(","):
        if ":" in item:
            k, v = item.split(":", 1)
            if k == key:
                return int(v) if v.isdigit() else v  # 兼容数字和字符串
    return 0
