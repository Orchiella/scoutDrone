# coding=utf-8
import math
import time

from mod.common.utils.mcmath import Vector3, Matrix

from ScoutDrone.config import mod_name
from ScoutDrone.const import  TRANSITION_DURATION


def GetFixOffset(rate):
    return 7.5 * (min(rate, 1.6) - 1.6)


def GetTransitionMolangDict(QC, animation_cache, now_state, now_state_start_time, next_state):
    t_now = time.time()
    t_anim_global = t_now - now_state_start_time  # 不管是不是过渡动画都需要

    is_transition = now_state == "transition"

    varDict = {}
    for perspective, bone_map in [
        ("1st", {
            "right": "rightArm",
            "left": "leftArm",
            "item": mod_name
        }),
        ("3rd", {
            "right": "rightArm",
            "left": "leftArm",
            "item": mod_name
        }),
    ]:
        next_anim = animation_cache.get(perspective + "_" + next_state, None)
        if not next_anim:
            continue
        next_bones = next_anim["bones"]
        for bone_key, anim_bone in bone_map.items():
            next_bone = next_bones.get(anim_bone, {})
            for attr in ["rotation", "position"]:
                if now_state_start_time != 0:
                    if is_transition:

                        # ===== 当前是 transition 动画，从 molang 中插值 =====
                        value = []
                        for coord in "xyz":
                            var_s = "query.mod.{}_trans_{}_{}_{}_s_{}".format(
                                mod_name, perspective, bone_key, attr[:3], coord)
                            var_e = "query.mod.{}_trans_{}_{}_{}_e_{}".format(
                                mod_name, perspective, bone_key, attr[:3], coord)

                            val_s = QC.Get(var_s)
                            val_e = QC.Get(var_e)
                            interp = val_s + (val_e - val_s) * min(1, t_anim_global / (
                                    TRANSITION_DURATION))  # 简单线性插值
                            value.append(interp)

                    else:
                        # ===== 普通动画，查动画帧表并插值 =====
                        now_anim = animation_cache.get(perspective + "_" + now_state, None)
                        if not now_anim:
                            continue
                        now_length = now_anim["length"]
                        is_static = now_length == 0.0
                        t_anim = t_anim_global
                        if is_static:
                            t_anim = 0.0
                        else:
                            if now_anim['loop'] == "hold_on_last_frame":
                                t_anim = min(t_anim, now_length)
                            else:
                                t_anim = (t_anim ) % now_length
                        now_bones = now_anim["bones"]

                        now_bone = now_bones.get(anim_bone, {})
                        now_frames = now_bone[attr] if attr in now_bone and now_bone[attr] else {"0.0": [0.0, 0.0, 0.0]}
                        sorted_keys = sorted(now_frames.keys(), key=lambda x: float(x))

                        if is_static or len(sorted_keys) == 1:
                            value = now_frames[sorted_keys[0]]
                        else:
                            for i in range(len(sorted_keys) - 1):
                                t0_str, t1_str = sorted_keys[i], sorted_keys[i + 1]
                                t0, t1 = float(t0_str), float(t1_str)
                                if t0 <= t_anim <= t1:
                                    v0, v1 = now_frames[t0_str], now_frames[t1_str]
                                    t = (t_anim - t0) / (t1 - t0)
                                    value = [v0[j] + (v1[j] - v0[j]) * t for j in range(3)]
                                    break
                            else:
                                value = now_frames[sorted_keys[-1]]

                    # ===== 设置 molang 起始值 =====
                    for i, coord in enumerate("xyz"):
                        var_s = "trans_{}_{}_{}_s_{}".format(
                            perspective, bone_key, attr[:3], coord)
                        varDict[var_s] = value[i]
                        # print "s: {} {}".format(var_s, value[i])

                # ===== 设置 molang 终止值（目标动画的 0.0 帧）=====
                end_val = next_bone.get(attr, {}).get("0.0", [0.0, 0.0, 0.0])
                for i, coord in enumerate("xyz"):
                    var_e = "trans_{}_{}_{}_e_{}".format(
                        perspective, bone_key, attr[:3], coord)
                    varDict[var_e] = end_val[i]
                    # print "e: {} {}".format(var_e, end_val[i])
                    if now_state_start_time == 0:
                        var_s = "trans_{}_{}_{}_s_{}".format(
                            perspective, bone_key, attr[:3], coord)
                        varDict[var_s] = end_val[i]

    return varDict



def get_scale_by_distance(player_pos, frame_pos):
    dist = (Vector3(frame_pos) - Vector3(player_pos)).Length()
    if dist < 25:
        return dist / 10.0
    return max(1, 2.5 - (dist - 25) / 10)


def GetDirection(motion):
    vx, vy, vz = motion
    if vx == 0 and vz == 0:
        return "无水平方向"

    # 计算水平角度，以正北为0度，顺时针为正方向
    angle_rad = math.atan2(vx, -vz)  # 注意：Minecraft中z轴朝南，x轴朝东
    angle_deg = int(round(math.degrees(angle_rad))) % 360

    # 判断是否是正方向
    if angle_deg % 90 == 0:
        directions = {
            0: "正北",
            90: "正东",
            180: "正南",
            270: "正西"
        }
        return directions[angle_deg]
    else:
        # 判断象限
        if 0 < angle_deg < 90:
            return "北偏东%d°" % angle_deg
        elif 90 < angle_deg < 180:
            return "南偏东%d°" % (180 - angle_deg)
        elif 180 < angle_deg < 270:
            return "南偏西%d°" % (angle_deg - 180)
        else:
            return "北偏西%d°" % (360 - angle_deg)


def GetSurroundingPoses(centerPos):
    poses = []
    for dy in [2, 1, 0, -1, -2]:
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                # 排除自身坐标
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                poses.append((centerPos[0] + dx, centerPos[1] + dy, centerPos[2] + dz))
    return poses


def GetDistance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2)
