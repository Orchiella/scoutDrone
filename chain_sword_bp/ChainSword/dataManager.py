# coding=utf-8

import mod.server.extraServerApi as serverApi

from ChainSword.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("sound_enabled", {"description": "§f播放音效", "type": "bool", "default": True}),
        ("light_enabled", {"description": "§f移动光源(中强度)", "type": "bool", "default": True}),
        ("slash_damage", {"description": "§f未启动锯齿时，挥砍瞬时伤害", "type": "int", "range": (1,1000), "default": 5}),
        ("slash_knock", {"description": "§f未启动锯齿时，挥砍击退强度", "type": "int", "range": (0,10), "default": 2}),
        ("slash_radius", {"description": "§f未启动锯齿时，挥砍伤害距离", "type": "int", "range": (1,15), "default": 5}),
        ("slash_angle", {"description": "§f未启动锯齿时，挥砍范围夹角", "type": "int", "range": (30,180), "default": 90}),
        ("slash_durability_consumption", {"description": "§f未启动锯齿时，挥砍消耗耐久", "type": "int", "range": (0,100), "default": 1}),
        ("rev_damage", {"description": "§e锯齿持续伤害", "type": "int", "range": (1,1000), "default": 4}),
        ("rev_interval", {"description": "§e锯齿持续伤害的间隔 §7(单位:毫秒)", "type": "int", "range": (1,10000), "default": 600}),
        ("rev_radius", {"description": "§e锯齿持续伤害距离", "type": "int", "range": (1,15), "default": 5}),
        ("rev_angle", {"description": "§e锯齿持续伤害范围夹角", "type": "int", "range": (30,180), "default": 150}),
        ("rev_knock", {"description": "§e锯齿持续伤害的轻微击退效果", "type": "bool", "default": True}),
        ("rev_durability_consumption", {"description": "§e锯齿持续伤害消耗耐久", "type": "int", "range": (0,100), "default": 1}),
        ("rev_slash_damage", {"description": "§6启动锯齿后，挥砍瞬时伤害", "type": "int", "range": (1,1000), "default": 5}),
        ("rev_slash_knock", {"description": "§6启动锯齿后，挥砍击退强度", "type": "int", "range": (0,10), "default": 3}),
        ("rev_slash_radius", {"description": "§6启动锯齿后，挥砍伤害距离", "type": "int", "range": (1,15), "default": 5}),
        ("rev_slash_angle", {"description": "§6启动锯齿后，挥砍范围夹角", "type": "int", "range": (30,180), "default": 90}),
        ("rev_slash_durability_consumption", {"description": "§6启动锯齿后，挥砍消耗耐久", "type": "int", "range": (0,100), "default": 3}),

        ("func_rev_enabled", {"description": "§b[动力锯齿]§f显示按钮", "type": "bool", "default": True}),
        ("func_rev_size", {"description": "§b[动力锯齿]§f按钮大小缩放 §7(单位:百分比)", "type": "int", "range": (30,200), "default": 100}),
        ("func_rev_key", {"description": "§b[动力锯齿]§fPC绑定键 0即无 1-26即A-Z键", "type":"int", "range": (0, 26), "default": 0}),
        ("func_rev_cd", {"description": "§b[动力锯齿]§f切换冷却时长 §7(单位：毫秒)", "type": "int", "range": (1, 10000), "default": 800}),
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
