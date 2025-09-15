# coding=utf-8

import mod.server.extraServerApi as serverApi

from ScoutDrone.config import mod_name

levelId = serverApi.GetLevelId()

DEFAULT_PLAYER_SETTINGS = [
    ("sound_enabled", {"description": "§f音效", "type": "bool", "default": True}),
    ("shake", {"description": "§f镜头摇晃§7(觉得晕可以关掉)", "type": "bool", "default": True}),
    ("green_intense", {"description": "§f滤镜强度百分比", "type": "int", "range": (0, 100), "default": 30}),
    ("charge_no_consume", {"description": "§f生存模式下充电不消耗红石粉", "type": "bool", "default": False}),
    ("infinite_durability", {"description": "§f生存模式下也无限耐久", "type": "bool", "default": False}),
    ("infinite_battery", {"description": "§f生存模式下也不需充电", "type": "bool", "default": False}),
    ("speed_up_amplifier", {"description": "§f加速倍率", "type": "int", "range": (2, 10), "default": 3}),
    ("speed_up_cost", {"description": "§f加速消耗电量", "type": "int", "range": (0, 1000), "default": 4}),
    ("scan_cost", {"description": "§f扫描消耗电量", "type": "int", "range": (0, 1000), "default": 8}),
    ("mark_cost", {"description": "§f标记消耗电量", "type": "int", "range": (0, 1000), "default": 2}),
    ("load1_cost", {"description": "§f引力钩爪消耗电量", "type": "int", "range": (0, 1000), "default": 10}),
    ("load3_cost", {"description": "§f投放诱饵消耗电量", "type": "int", "range": (0, 1000), "default": 10}),
    ("load3_duration", {"description": "§f诱饵持续时长", "type": "int", "range": (0, 1000), "default": 10}),
    ("load3_radius", {"description": "§f诱饵作用半径", "type": "int", "range": (0, 100), "default": 15}),
    ("explode_cost", {"description": "§f自爆消耗耐久", "type": "int", "range": (0, 1000), "default": 50}),
    ("explode_damage_percentage", {"description": "§f自爆伤害缩放百分比", "type": "int", "range": (0, 1000), "default": 100}),
    ("explode_radius", {"description": "§f自爆半径", "type": "int", "range": (0, 20), "default": 5}),
    ("explode_break", {"description": "§f自爆破坏方块", "type": "bool", "default": True}),
    ("explode_fire", {"description": "§f自爆引发火焰§7(需开启上一项)", "type": "bool", "default": True}),
]

DEFAULT_PLAYER_DATA = {
    "func_shoot_pos": (-60, 30), "func_shoot_size": 50,
    "func_sight_pos": (-38, 30), "func_sight_size": 50,
    "func_inspect_pos": (52, -60), "func_inspect_size": 40,
    "func_deploy_pos": (145, -60), "func_deploy_size": 40,
    "func_settings_pos": (62, -94), "func_settings_size": 20,
    "func_recover_pos": (-65, -40), "func_recover_size": 40,
    "func_control_pos": (-110, -40), "func_control_size": 40,
    "func_function_pos": (-20, -40), "func_function_size": 40,
    "func_scan_pos": (-110, -95), "func_scan_size": 40,
    "func_mark_pos": (-65, -95), "func_mark_size": 40,
    "func_explode_pos": (-20, -95), "func_explode_size": 40,
    "func_charge_pos": (-130,30), "func_charge_size": 40,
    "usage_informed": False,
    "update_tip_0": False
}


class DataManager(object):
    private_keys = {setting[0] for setting in DEFAULT_PLAYER_SETTINGS if "private" in setting[1]}

    default_world_settings = {"owner": None, "auto_gain_permission": False, "sync_owner_settings": False,
                              "permitted_players": []}

    cache = None
    data_comp = None
    KEY_NAME = mod_name + "_addon"

    def __init__(self):
        DataManager.data_comp = serverApi.GetEngineCompFactory().CreateExtraData(serverApi.GetLevelId())
        DataManager.cache = {}
        DataManager.world_cache = {}

    @classmethod
    def Check(cls, playerId):
        if not playerId: playerId = levelId
        if cls.cache and playerId in cls.cache:
            return
        all_players_data = DataManager.data_comp.GetWholeExtraData()[cls.KEY_NAME]

        need_change_data_in_file = False
        player_valid_data = all_players_data[playerId] if playerId in all_players_data else {}
        # 漏什么加什么
        if playerId != levelId:
            for key, settings in DEFAULT_PLAYER_SETTINGS:
                if key not in player_valid_data:
                    player_valid_data[key] = settings['default']
                    need_change_data_in_file = True
            for key, value in DEFAULT_PLAYER_DATA.items():
                if key not in player_valid_data:
                    player_valid_data[key] = value
                    need_change_data_in_file = True
        else:
            for key, default in cls.default_world_settings.items():
                if key not in player_valid_data:
                    player_valid_data[key] = default
                    need_change_data_in_file = True

        cls.cache[playerId] = player_valid_data
        if need_change_data_in_file:
            newDict = DataManager.data_comp.GetWholeExtraData()[cls.KEY_NAME]
            newDict[playerId] = player_valid_data
            DataManager.data_comp.SetExtraData(cls.KEY_NAME, newDict)

    # 测试用
    @classmethod
    def Reset(cls, playerId):
        default_data = {}
        for key, settings in DEFAULT_PLAYER_SETTINGS:
            default_data[key] = settings['default']
        for key, value in DEFAULT_PLAYER_DATA.items():
            default_data[key] = value
        cls.cache[playerId] = default_data
        newDict = DataManager.data_comp.GetWholeExtraData()[cls.KEY_NAME]
        newDict[playerId] = default_data
        DataManager.data_comp.SetExtraData(cls.KEY_NAME, newDict)

    # screen.py无法直接调用此方法
    @classmethod
    def Set(cls, playerId, key, value):
        if not playerId: playerId = levelId
        cls.cache[playerId][key] = value
        newDict = DataManager.data_comp.GetWholeExtraData()[cls.KEY_NAME]
        newDict[playerId][key] = value
        DataManager.data_comp.SetExtraData(cls.KEY_NAME, newDict)

    @classmethod
    def Get(cls, playerId, key):
        if not playerId:
            return cls.cache[levelId][key]
        else:
            if cls.cache[levelId]["sync_owner_settings"] and not cls.IsPrivateKey(key):
                playerId = cls.cache[levelId]['owner']
            return cls.cache[playerId][key]

    @classmethod
    def IsPrivateKey(cls, key):
        return key in DEFAULT_PLAYER_DATA or key in cls.private_keys
