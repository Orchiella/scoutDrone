# coding=utf-8

import mod.server.extraServerApi as serverApi

from ElectricBow.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("arrow_shock_number", {"description": "§f电箭放能次数", "type": "int", "range": (1,30), "default": 6}),
        ("arrow_shock_interval", {"description": "§f电箭放能间隔 §7(单位:毫秒)", "type": "int", "range": (100,10000), "default": 800}),
        ("arrow_shock_radius", {"description": "§f放能伤害半径", "type": "int", "range": (1,10), "default": 2}),
        ("arrow_shock_damage", {"description": "§f放能单次伤害", "type": "int", "range": (1,100), "default": 8}),
        ("arrow_shock_sound_enabled", {"description": "§f开启电箭伤害音效", "type": "bool", "default": True}),
        ("arrow_shock_self_protection", {"description": "§f防止误伤自己", "type": "bool", "default": True}),
        ("arrow_shock_other_protection", {"description": "§f防止误伤其他玩家 §7(PVP建议关闭)", "type": "bool", "default": True}),

        ("func_sensing_enabled", {"description": "§e[电磁感应]§f显示按钮", "type": "bool", "default": True}),
        ("func_sensing_size", {"description": "§e[电磁感应]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30,200), "default": 100}),
        ("func_sensing_key", {"description": "§e[电磁感应]§fPC版绑定键 0即无 1-26即A-Z键", "type":"int", "range": (0, 26), "default": 0}),
        ("func_sensing_cd", {"description": "§e[电磁感应]§f冷却秒数", "type": "int", "range": (1, 60), "default": 6}),
        ("func_sensing_radius", {"description": "§e[电磁感应]§f作用半径", "type": "int", "range": (1, 100), "default": 60}),
        ("func_sensing_duration", {"description": "§e[电磁感应]§f标记秒数", "type": "int", "range": (1, 60), "default": 3}),
        ("func_sensing_max", {"description": "§e[电磁感应]§f最大标记数量", "type": "int", "range": (1, 100), "default": 50}),

        ("func_release_enabled", {"description": "§b[电能爆发]§f显示按钮", "type": "bool", "default": True}),
        ("func_release_size",{"description": "§b[电能爆发]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30, 200),"default": 100}),
        ("func_release_key",{"description": "§b[电能爆发]§fPC版绑定键 0即无 1-26即A-Z键", "type": "int", "range": (0, 26), "default": 0}),
        ("func_release_cd", {"description": "§b[电能爆发]§f冷却秒数", "type": "int", "range": (1, 60), "default": 6}),
        ("func_release_damage_percentage",{"description": "§b[电能爆发]§f伤害缩放 §7(单位:百分比)", "type": "int", "range": (30, 300), "default": 150}),
    ]

    default_player_data = {"func_sensing_pos": (275, 33), "func_release_pos": (335, 33),
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
