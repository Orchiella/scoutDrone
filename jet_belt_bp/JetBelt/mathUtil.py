# coding=utf-8
import math


def Length(vec):
    return math.sqrt(pow(vec[0], 2) + pow(vec[1], 2) + pow(vec[2], 2))


def rotate_direction(joystick, dir):
    left, up = joystick[0], joystick[1]

    # 如果摇杆没有移动，保持原方向
    if left == 0 and up == 0:
        return dir

    # 当前方向向量（xz 平面）
    dx, dz = dir[0], dir[2]

    # 计算摇杆给出的旋转角度（以 z+ 为0°，左为正方向）
    angle = math.atan2(left, up)  # 注意：以 z+ 为前，逆时针为正角度

    # 应用逆时针旋转
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    new_dx = dx * cos_a + dz * sin_a
    new_dz = -dx * sin_a + dz * cos_a

    return (new_dx, dir[1], new_dz)
