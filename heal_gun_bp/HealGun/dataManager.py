# coding=utf-8

import mod.server.extraServerApi as serverApi

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("func_shoot_capacity", {"description": "§9[射击]§f子弹容量", "type": "int", "range": (1, 20), "default": 10}),
        ("func_shoot_cd", {"description": "§9[射击]§f每颗子弹恢复秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("heal_bullet_duration", {"description": "§d[治疗弹]§f效果秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("heal_bullet_amplifier", {"description": "§d[治疗弹]§f效果强度", "type": "int", "range": (1, 5), "default": 2}),
        ("speed_bullet_enabled", {"description": "§b[迅捷弹]§f启用", "type": "bool", "default": True}),
        ("speed_bullet_duration", {"description": "§b[迅捷弹]§f效果秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("speed_bullet_amplifier", {"description": "§b[迅捷弹]§f效果强度", "type": "int", "range": (1, 5), "default": 2}),
        ("slow_bullet_enabled", {"description": "§3[迟缓弹]§f启用", "type": "bool", "default": True}),
        ("slow_bullet_duration", {"description": "§3[迟缓弹]§f效果秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("slow_bullet_amplifier", {"description": "§3[迟缓弹]§f效果强度", "type": "int", "range": (1, 5), "default": 2}),
        ("poison_bullet_enabled", {"description": "§2[毒液弹]§f启用", "type": "bool", "default": True}),
        ("poison_bullet_duration", {"description": "§2[毒液弹]§f效果秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("poison_bullet_amplifier", {"description": "§2[毒液弹]§f效果强度", "type": "int", "range": (1, 5), "default": 2}),
        ("func_self_heal_cd", {"description": "§d[技能:治疗自我]§f冷却秒数", "type": "int", "range": (1, 60), "default": 10}),
        ("func_self_heal_duration", {"description": "§d[技能:治疗自我]§f效果秒数", "type": "int", "range": (1, 60), "default": 4}),
        ("func_self_heal_amplifier", {"description": "§d[技能:治疗自我]§f效果强度", "type": "int", "range": (1, 5), "default": 2}),
        ("func_launch_bomb_cd", {"description": "§b[技能:投放增益]§f冷却秒数", "type": "int", "range": (1, 60), "default": 20}),
        ("func_launch_bomb_radius", {"description": "§b[技能:投放增益]§f作用半径", "type": "int", "range": (1, 20), "default": 3}),
        ("func_launch_bomb_duration", {"description": "§b[技能:投放增益]§f维持秒数", "type": "int", "range": (1, 60), "default": 10}),
        ("func_launch_bomb_heal_amplifier", {"description": "§b[技能:投放增益]§f生命恢复效果强度", "type": "int", "range": (0, 5), "default": 2}),
        ("func_launch_bomb_speed_amplifier", {"description": "§b[技能:投放增益]§f速度提升效果强度", "type": "int", "range": (0, 5), "default": 2}),
        ("func_launch_bomb_jump_amplifier", {"description": "§b[技能:投放增益]§f跳跃提升效果强度", "type": "int", "range": (0, 5), "default": 0}),
        ("func_launch_bomb_strength_amplifier", {"description": "§b[技能:投放增益]§f力量提升效果强度", "type": "int", "range": (0, 5), "default": 0}),
    ]

    default_player_data = {"func_self_heal_pos": (275, 33), "func_launch_bomb_pos": (335, 33), "func_switch_bullet_pos": (290, 83),
                           "func_switch_tracking_pos": (350, 83), "func_shoot_pos": (400, 83),
                           "func_switch_tracking_state": "yes","func_switch_bullet_state": "heal"}

    default_world_settings = {"owner": None, "auto_gain_permission": False, "sync_owner_settings": False,
                              "permitted_players": []}

    cache = None
    data_comp = None
    KEY_NAME = "heal_gun_addon"

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
