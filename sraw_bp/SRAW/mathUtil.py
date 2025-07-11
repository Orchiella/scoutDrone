# coding=utf-8
import math
import time

from SRAW.config import mod_name
from SRAW.const import PENETRABLE_BLOCK_TYPE


def set_transition_molang_vars(QC, animation_cache, now_state, now_state_start_time, next_state):
    t_now = time.time()
    t_anim = t_now - now_state_start_time  # 不管是不是过渡动画都需要

    next_anim = animation_cache.get(next_state)
    if next_anim is None:
        return
    next_bones = next_anim["bones"]

    is_transition = now_state == "transition"

    for perspective, bone_map in [
        ("1st", {
            "right": "{}_right_offset".format(mod_name),
            "left": "{}_left_offset".format(mod_name),
            "item": mod_name
        }),
        # ("3rd", ...) 如有需要可以开启
    ]:
        for bone_key, anim_bone in bone_map.items():
            next_bone = next_bones.get(anim_bone, {})
            for attr in ["rotation", "position"]:
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

                        interp = val_s + (val_e - val_s) * t_anim # 简单线性插值
                        value.append(interp)

                else:
                    # ===== 普通动画，查动画帧表并插值 =====
                    now_anim = animation_cache.get(now_state)
                    if now_anim is None:
                        return
                    now_length = now_anim["length"]
                    now_bones = now_anim["bones"]
                    is_static = now_length == 0.0
                    t_anim = 0.0 if is_static else t_anim % now_length

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
                    var_s = "query.mod.{}_trans_{}_{}_{}_s_{}".format(
                        mod_name, perspective, bone_key, attr[:3], coord)
                    QC.Set(var_s, value[i])
                    #print "s: {} {}".format(var_s, value[i])

                # ===== 设置 molang 终止值（目标动画的 0.0 帧）=====
                end_val = next_bone.get(attr, {}).get("0.0", [0.0, 0.0, 0.0])
                for i, coord in enumerate("xyz"):
                    var_e = "query.mod.{}_trans_{}_{}_{}_e_{}".format(
                        mod_name, perspective, bone_key, attr[:3], coord)
                    QC.Set(var_e, end_val[i])
                    #print "e: {} {}".format(var_e, end_val[i])


def CalculateProjectileImpact(launchPos, launchDir, launchVel, blockInfoComp, dimId,gravity=-0.05):
    """
    计算抛射物落点坐标
    :param launchPos: 发射位置 (x, y, z)
    :param launchDir: 发射方向 (单位向量 dx, dy, dz)
    :param launchVel: 发射速度 (标量)
    :param levelId: 世界ID
    :param playerId: 玩家ID
    :return: 落点坐标 (x, y, z) 或 None（未击中）
    """

    # 常量定义
    TIME_STEP = 0.1  # 时间步长 (tick)
    MAX_TICKS = 500  # 最大模拟时间 (100 ticks)

    # 初始速度分量
    vx = launchDir[0] * launchVel
    vy = launchDir[1] * launchVel
    vz = launchDir[2] * launchVel

    # 当前时间位置
    t = 0.0
    current_pos = list(launchPos)

    # 三维DDA算法辅助函数
    def dda_raycast(start, end):
        # 计算方向向量和长度
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-6:
            return None

        # 初始化步进参数
        step_size = 0.2  # 保守步长 (小于1个方块)
        steps = int(math.ceil(length / step_size))
        if steps == 0:
            return None

        dir_x = dx / length * step_size
        dir_y = dy / length * step_size
        dir_z = dz / length * step_size

        # 从起点开始检测
        x, y, z = start
        prev_block = None
        for i in range(steps + 1):
            # 计算当前方块坐标
            block_x = int(math.floor(x))
            block_y = int(math.floor(y))
            block_z = int(math.floor(z))
            current_block = (block_x, block_y, block_z)

            # 只在新方块时检查
            if current_block != prev_block:
                # 获取方块类型
                block_info = blockInfoComp.GetBlockNew(current_block, dimId)
                if block_info['name'] not in PENETRABLE_BLOCK_TYPE:
                    # 计算精确命中点
                    hit_x, hit_y, hit_z = x, y, z

                    # 如果不在第一步，使用二分法精确定位
                    if i > 0:
                        prev_x = x - dir_x
                        prev_y = y - dir_y
                        prev_z = z - dir_z

                        low, high = 0.0, 1.0
                        while high - low > 0.01:  # 1%精度
                            mid = (low + high) / 2.0
                            test_x = prev_x + mid * dir_x
                            test_y = prev_y + mid * dir_y
                            test_z = prev_z + mid * dir_z

                            test_block = (
                                int(math.floor(test_x)),
                                int(math.floor(test_y)),
                                int(math.floor(test_z))
                            )

                            if test_block == current_block:
                                hit_x, hit_y, hit_z = test_x, test_y, test_z
                                high = mid
                            else:
                                low = mid

                    return (hit_x, hit_y, hit_z)

            prev_block = current_block
            x += dir_x
            y += dir_y
            z += dir_z

        return None

    # 主模拟循环
    for _ in range(int(MAX_TICKS / TIME_STEP)):
        t += TIME_STEP

        # 计算下一位置 (抛物线运动)
        next_x = launchPos[0] + vx * t
        next_y = launchPos[1] + vy * t + 0.5 * gravity * t ** 2
        next_z = launchPos[2] + vz * t
        next_pos = (next_x, next_y, next_z)

        # 检测从当前位置到下一位置的轨迹
        hit_pos = dda_raycast(current_pos, next_pos)
        if hit_pos:
            return hit_pos

        # 检查是否低于世界底部
        if next_y < 0:
            return (next_x, 0, next_z)

        # 更新当前位置
        current_pos = next_pos

    return None  # 未击中任何方块