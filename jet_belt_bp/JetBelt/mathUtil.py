# coding=utf-8
import math
import random


def Length(vec):
    return math.sqrt(pow(vec[0], 2) + pow(vec[1], 2) + pow(vec[2], 2))


import math

import math

import math

def normalize(v):
    length = math.sqrt(sum(x**2 for x in v))
    if length == 0:
        return [0.0, 0.0, 0.0]
    return [x / length for x in v]

def cross(a, b):
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]

def dot(a, b):
    return sum(i*j for i, j in zip(a, b))

def rotate_direction(joystick, dir):
    left, up = joystick[0], joystick[1]
    if left == 0 and up == 0:
        return dir

    angle = math.atan2(left, up)

    # Step 1: compute correct rotation axis
    up_y = [0.0, 1.0, 0.0]
    dir_norm = normalize(dir)

    temp = cross(up_y, dir_norm)         # 水平面内、与 dir 垂直
    axis = cross(dir_norm, temp)         # 满足你要求的旋转轴
    axis = normalize(axis)

    # Step 2: apply Rodrigues formula
    vx, vy, vz = dir
    kx, ky, kz = axis

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    one_minus_cos = 1 - cos_a

    k_dot_v = kx * vx + ky * vy + kz * vz
    cross_kv = cross(axis, dir)

    rx = vx * cos_a + cross_kv[0] * sin_a + kx * k_dot_v * one_minus_cos
    ry = vy * cos_a + cross_kv[1] * sin_a + ky * k_dot_v * one_minus_cos
    rz = vz * cos_a + cross_kv[2] * sin_a + kz * k_dot_v * one_minus_cos
    return (rx, ry, rz)





def generate_circle_points(center, radius, n):
    """
    在二维圆内随机生成均匀分布的 n 个点，y 分量保持不变。

    参数:
    center - 中心坐标 (x, y, z)
    radius - 圆的半径
    n - 要生成的点的数量

    返回:
    包含 n 个坐标的列表，每个元素是 (x, y, z) 格式的元组，其中 y 始终等于输入的 center[1]
    """
    points = []
    for _ in range(n):
        # 随机角度
        theta = 2 * math.pi * random.random()
        # 随机半径（平方根确保均匀分布）
        r = math.sqrt(random.random()) * radius

        x = center[0] + r * math.cos(theta)
        z = center[2] + r * math.sin(theta)

        points.append((x, center[1], z))

    return points
