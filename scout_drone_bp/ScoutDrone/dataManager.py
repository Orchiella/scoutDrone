# coding=utf-8

import mod.server.extraServerApi as serverApi

from ScoutDrone.config import mod_name

levelId = serverApi.GetLevelId()

DEFAULT_PLAYER_SETTINGS = [
    ("sight_bead_enabled", {"description": "§f准星", "type": "bool", "default": True}),
    ("sound_enabled", {"description": "§f播放音效", "type": "bool", "default": True}),
    ("particle_enabled", {"description": "§f打击粒子", "type": "bool", "default": True}),
    ("damage", {"description": "§f基础伤害", "type": "int", "range": (0, 1000), "default": 16}),
    ("power", {"description": "§f基础初速", "type": "int", "range": (1, 10), "default": 7}),
    ("infinite_ammo", {"description": "§f生存模式下也不消耗箭矢", "type": "bool", "default": False}),
    ("infinite_durability", {"description": "§f生存模式下也不消耗耐久", "type": "bool", "default": False}),
    ("aim_shoot", {"description": "§f瞄射自动举镜", "type": "bool", "default": True}),
    ("hold_to_shoot", {"description": "§f长按屏幕射击", "type": "bool", "default": True}),
    ("lightning_num", {"description": "§f闪电道数", "type": "int", "range": (1, 10), "default": 3}),
    ("explode_radius", {"description": "§f爆炸半径", "type": "int", "range": (0, 20), "default": 5}),
    ("fire_semi_length", {"description": "§f火焰阵边长", "type": "int", "range": (1, 20), "default": 5}),
    ("explode_break", {"description": "§f爆炸破坏地形", "type": "bool", "default": True}),
    ("func_aim_auto",
     {"description": "§6[瞄准按钮]§f射击后恢复开镜", "type": "bool", "default": False}),
    ("func_reload_auto",
     {"description": "§6[装填按钮]§f射击后自动使用", "type": "bool", "default": True}),
    ("func_aim_auto_hold_breath",
     {"description": "§6[屏息按钮]§f举镜后自动屏息", "type": "bool", "default": True}),
]

DEFAULT_PLAYER_DATA = {
    "func_aim_pos": (-140, -36), "func_aim_size": 40, "func_aim_visible": True,
    "func_shoot_pos": (5, -10), "func_shoot_size": 50, "func_shoot_visible": True,
    "func_aim_shoot_pos": (-100, 35), "func_aim_shoot_size": 50, "func_aim_shoot_visible": True,
    "func_reload_pos": (-160, 40), "func_reload_size": 40, "func_reload_visible": True,
    "func_inspect_pos": (52, -60), "func_inspect_size": 40, "func_inspect_visible": True,
    "func_deploy_pos": (165, -60), "func_deploy_size": 40, "func_deploy_visible": True,
    "func_settings_pos": (62, -94), "func_settings_size": 20, "func_settings_visible": True,
    "func_hold_breath_pos": (-140, -90), "func_hold_breath_size": 40, "func_hold_breath_visible": True,
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
