# coding=utf-8

import mod.server.extraServerApi as serverApi

from JetBelt.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("func_use_capacity", {"description": "§9[喷气]§f能量载量", "type": "int", "range": (1, 20), "default": 6}),
        ("func_use_cd", {"description": "§9[喷气]§f每点能量填充秒数", "type": "int", "range": (1, 60), "default": 2}),
        ("func_use_strength", {"description": "§9[喷气]§f推进力度", "type": "int", "range": (1, 5), "default": 3}),
        ("func_use_durability_consumption", {"description": "§9[喷气]§f消耗耐久", "type": "int", "range": (1, 60), "default": 1}),
        ("func_boost_use_strength", {"description": "§9[喷气]§f提高功率时额外的推进力度", "type": "int", "range": (1, 5), "default": 2}),
        ("func_boost_use_energy_consumption", {"description": "§9[喷气]§f提高功率时额外消耗的能量", "type": "int", "range": (1, 100), "default": 2}),
        ("func_boost_use_durability_consumption", {"description": "§9[喷气]§f提高功率时额外消耗的耐久", "type": "int", "range": (1, 60), "default": 1}),
        ("func_use_kill_to_resume", {"description": "§9[喷气]§f击杀生物后立即填充一次", "type": "bool", "default": True}),
        ("func_flash_cd", {"description": "§5[技能:闪现]§f冷却秒数", "type": "int", "range": (1, 60), "default": 10}),
        ("func_flash_max_distance", {"description": "§5[技能:闪现]§f最远距离", "type": "int", "range": (1, 100), "default": 30}),
        ("func_flash_durability_consumption", {"description": "§5[技能:闪现]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),
        ("func_brake_cd", {"description": "§b[技能:制动]§f冷却秒数", "type": "int", "range": (1, 60), "default": 12}),
        ("func_brake_durability_consumption", {"description": "§b[技能:制动]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),
        ("func_fear_cd", {"description": "§e[技能:震慑]§f冷却秒数", "type": "int", "range": (1, 60), "default": 12}),
        ("func_fear_radius", {"description": "§e[技能:震慑]§f半径", "type": "int", "range": (1, 20), "default": 8}),
        ("func_fear_strength", {"description": "§e[技能:震慑]§f力度", "type": "int", "range": (1, 5), "default": 4}),
        ("func_fear_durability_consumption", {"description": "§e[技能:震慑]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),
    ]

    default_player_data = {"func_flash_pos": (275, 33), "func_brake_pos": (335, 33),
                           "func_fear_pos": (290, 83),"func_switch_power_pos": (350, 83), "func_use_pos": (300, 183),
                           "func_switch_power_state": "normal",
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
