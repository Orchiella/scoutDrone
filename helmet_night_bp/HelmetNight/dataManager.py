# coding=utf-8

import mod.server.extraServerApi as serverApi

from HelmetNight.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("func_sensing_enabled", {"description": "§6[感应]§f显示按钮", "type": "bool", "default": True}),
        ("func_sensing_size", {"description": "§6[感应]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30,200), "default": 100}),
        ("func_sensing_key", {"description": "§6[感应]§fPC版绑定键 0即无 1-26即A-Z键", "type":"int", "range": (0, 26), "default": 0}),
        ("func_sensing_cd", {"description": "§6[感应]§f冷却秒数", "type": "int", "range": (1, 60), "default": 6}),
        ("func_sensing_durability_consumption", {"description": "§6[感应]§f消耗耐久", "type": "int", "range": (0, 100), "default": 3}),
        ("func_sensing_radius", {"description": "§6[感应]§f作用半径", "type": "int", "range": (1, 100), "default": 60}),
        ("func_sensing_duration", {"description": "§6[感应]§f标记秒数", "type": "int", "range": (1, 60), "default": 3}),
        ("func_sensing_max", {"description": "§6[感应]§f最大标记数量", "type": "int", "range": (1, 100), "default": 50}),

        ("func_invisibility_enabled", {"description": "§b[匿迹]§f显示按钮", "type": "bool", "default": True}),
        ("func_invisibility_size",{"description": "§b[匿迹]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30, 200), "default": 100}),
        ("func_invisibility_key",{"description": "§b[匿迹]§fPC版绑定键 0即无 1-26即A-Z键", "type": "int", "range": (0, 26), "default": 0}),
        ("func_invisibility_cd", {"description": "§b[匿迹]§f冷却秒数", "type": "int", "range": (1, 60), "default": 10}),
        ("func_invisibility_durability_consumption",{"description": "§b[匿迹]§f消耗耐久", "type": "int", "range": (0, 100), "default": 5}),
        ("func_invisibility_radius",{"description": "§b[匿迹]§f作用半径", "type": "int", "range": (1, 100), "default": 30}),
        ("func_invisibility_duration",{"description": "§b[匿迹]§f生效持续秒数", "type": "int", "range": (1, 60), "default": 5}),

        ("func_night_vision_enabled", {"description": "§5[夜视]§f显示按钮", "type": "bool", "default": True}),
        ("func_night_vision_size",{"description": "§5[夜视]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30, 200), "default": 100}),
        ("func_night_vision_key",{"description": "§5[夜视]§fPC版绑定键 0即无 1-26即A-Z键", "type": "int", "range": (0, 26), "default": 0}),
        ("func_night_vision_durability_consumption",{"description": "§5[夜视]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),

        ("func_light_enabled", {"description": "§e[探照]§f显示按钮", "type": "bool", "default": True}),
        ("func_light_size",{"description": "§e[探照]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30, 200), "default": 100}),
        ("func_light_key",{"description": "§e[探照]§fPC版绑定键 0即无 1-26即A-Z键", "type": "int", "range": (0, 26), "default": 0}),
        ("func_light_durability_consumption",{"description": "§e[探照]§f消耗耐久", "type": "int", "range": (0, 100), "default": 5}),
        ("func_light_distance",{"description": "§e[探照]§f最大探照距离", "type": "int", "range": (0, 100), "default": 60}),
    ]

    default_player_data = {"func_sensing_pos": (275, 33), "func_invisibility_pos": (335, 33),
                           "func_night_vision_pos": (290, 83),"func_light_pos": (350, 83),
                           "func_night_vision_state": "off", "func_light_state": "off",
                           "usage_informed": False}

    default_world_settings = {"owner": None, "auto_gain_permission": False, "sync_owner_settings": False,
                              "permitted_players": []}

    cache = None
    data_comp = None
    KEY_NAME = mod_name+"_addon"

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
            for key, settings in cls.default_player_settings:
                if key not in player_valid_data:
                    player_valid_data[key] = settings['default']
                    need_change_data_in_file = True
            for key, value in cls.default_player_data.items():
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
        for key, settings in cls.default_player_settings:
            default_data[key] = settings['default']
        for key, value in cls.default_player_data.items():
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
            if cls.cache[levelId]["sync_owner_settings"]:
                playerId = cls.cache[levelId]['owner']
            return cls.cache[playerId][key]
