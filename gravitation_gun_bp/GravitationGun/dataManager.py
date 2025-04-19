# coding=utf-8

import mod.server.extraServerApi as serverApi

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("func_use_capacity", {"description": "§9[使用]§f能量载量", "type": "int", "range": (1, 20), "default": 10}),
        ("func_use_cd", {"description": "§9[使用]§f每点能量填充秒数", "type": "int", "range": (1, 60), "default": 2}),
        ("func_use_entity_durability_consumption", {"description": "§9[使用]§f作用于实体时消耗的耐久", "type": "int", "range": (0, 100), "default": 1}),
        ("func_use_block_durability_consumption", {"description": "§9[使用]§f作用于方块时消耗的耐久", "type": "int", "range": (0, 100), "default": 1}),
        ("func_sector_cd", {"description": "§a[技能:范围使用]§f冷却秒数", "type": "int", "range": (1, 60), "default": 10}),
        ("func_sector_durability_consumption", {"description": "§a[技能:范围使用]§f消耗耐久", "type": "int", "range": (0, 100), "default": 3}),
        ("func_sector_angle", {"description": "§a[技能:范围使用]§f作用范围的扇形角度", "type": "int", "range": (30, 180), "default": 120}),
        ("func_sector_radius", {"description": "§a[技能:范围使用]§f作用范围的扇形半径", "type": "int", "range": (1, 30), "default": 8}),
        ("func_trap_cd", {"description": "§5[技能:引力陷阱]§f冷却秒数", "type": "int", "range": (1, 60), "default": 20}),
        ("func_trap_durability_consumption", {"description": "§5[技能:引力陷阱]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),
        ("func_trap_radius", {"description": "§5[技能:引力陷阱]§f作用半径", "type": "int", "range": (1, 30), "default": 8}),
        ("func_trap_duration", {"description": "§5[技能:引力陷阱]§f维持秒数", "type": "int", "range": (1, 60), "default": 5}),
        ("func_trap_affect_other_players", {"description": "§5[技能:引力陷阱]§f是否对其他玩家生效", "type": "bool", "default": False}),
        ("func_frozen_cd", {"description": "§b[技能:冰冻]§f冷却秒数", "type": "int", "range": (1, 60), "default": 20}),
        ("func_frozen_durability_consumption", {"description": "§b[技能:冰冻]§f消耗耐久", "type": "int", "range": (0, 100), "default": 10}),
        ("func_frozen_duration", {"description": "§b[技能:冰冻]§f冻结秒数", "type": "int", "range": (1, 60), "default": 5}),
    ]

    default_player_data = {"func_sector_pos": (215, 33),"func_trap_pos": (275, 33), "func_switch_force_pos": (335, 33),
                           "func_?_pos": (230, 83),"func_frozen_pos": (290, 83),"func_switch_target_pos": (350, 83), "func_use_pos": (300, 183),
                           "func_switch_force_state": "gravitation", "func_switch_target_state": "entity",
                           "usage_informed": False}

    default_world_settings = {"owner": None, "auto_gain_permission": False, "sync_owner_settings": False,
                              "permitted_players": []}

    cache = None
    data_comp = None
    KEY_NAME = "gravitation_gun_addon"

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
