# coding=utf-8

import mod.server.extraServerApi as serverApi

from ChainSword.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("sight_bead_enabled", {"description": "§f显示准星 §7(若已有十字指针可关)", "type": "bool", "default": True}),
        ("arrow_shock_number", {"description": "§f电箭放能次数", "type": "int", "range": (1,30), "default": 5}),
        ("arrow_shock_interval", {"description": "§f电箭放能间隔 §7(单位:毫秒)", "type": "int", "range": (100,10000), "default": 800}),
        ("arrow_shock_radius", {"description": "§f放能伤害半径", "type": "int", "range": (1,10), "default": 4}),
        ("arrow_shock_damage", {"description": "§f放能单次伤害", "type": "int", "range": (1,100), "default": 8}),
        ("arrow_shock_sound_enabled", {"description": "§f开启电箭伤害音效", "type": "bool", "default": True}),
        ("arrow_shock_self_protection", {"description": "§f防止误伤自己", "type": "bool", "default": True}),
        ("arrow_shock_other_protection", {"description": "§f防止误伤其他玩家 §7(PVP建议关闭)", "type": "bool", "default": True}),

        ("func_rev_enabled", {"description": "§e[动力锯齿]§f显示按钮", "type": "bool", "default": True}),
        ("func_rev_size", {"description": "§e[动力锯齿]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30,200), "default": 100}),
        ("func_rev_key", {"description": "§e[动力锯齿]§fPC版绑定键 0即无 1-26即A-Z键", "type":"int", "range": (0, 26), "default": 0}),
        ("func_rev_cd", {"description": "§e[动力锯齿]§f切换冷却时长 §7(单位：毫秒)", "type": "int", "range": (1, 10000), "default": 800}),

        ("func_slash_enabled", {"description": "§b[挥砍/横握]§f显示按钮", "type": "bool", "default": True}),
        ("func_slash_size",{"description": "§b[挥砍/横握]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30, 200),"default": 100}),
        ("func_slash_key",{"description": "§b[挥砍/横握]§fPC版绑定键 0即无 1-26即A-Z键", "type": "int", "range": (0, 26), "default": 0}),
        ("func_slash_cd", {"description": "§b[挥砍/横握]§f冷却时长 §7(单位：毫秒)", "type": "int", "range": (1, 10000), "default": 500}),
    ]

    default_player_data = {"func_rev_pos": (275, 33), "func_slash_pos": (335, 33),
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
