# coding=utf-8

import mod.server.extraServerApi as serverApi

from LoiteringMunition.config import mod_name

levelId = serverApi.GetLevelId()


class DataManager(object):
    default_player_settings = [
        ("lock_button", {"description": "§f锁定功能按钮位置§7(不触发长按拖动)", "type": "bool", "default": False}),
        ("sight_bead_enabled", {"description": "§f显示辅助准星白点", "type": "bool", "default": True}),
        ("joystick_enabled", {"description": "§e使用摇杆控制方向§f(侧重真实但稍难)", "type": "bool", "default": False}),
        ("quick_shoot", {"description": "§9快捷发射§f(右键/长按开镜、左键/短按发射)", "type": "bool", "default": False}),
        ("protect_self",{"description": "§f防止炸伤自己", "type": "bool", "default": True}),
        ("fixed_damage_enabled",{"description": "§6启用爆炸固伤§7(如果发现爆炸伤害很低)", "type": "bool", "default": True}),
        ("fixed_damage", {"description": "§f基础爆炸固伤", "type": "int", "range": (1, 1000), "default": 40}),
        ("fixed_damage_random_factor",{"description": "§f爆炸固伤随机放缩 §7(单位：百分比)", "type": "int", "range": (0, 100), "default": 20}),
        ("fixed_damage_weakening_factor",{"description": "§f爆炸固伤随距离的衰减因子 §7(越大越显著)", "type": "int", "range": (0, 10), "default": 4}),
        ("explode_damage_percentage",{"description": "§f爆炸伤害缩放 §7(单位：百分比，需关闭固伤)", "type": "int", "range": (1, 1000),"default": 300}),
        ("explode_radius", {"description": "§f爆炸半径", "type": "int", "range": (1, 30), "default": 5}),
        ("explode_break_enabled", {"description": "§f爆炸破坏地形", "type": "bool", "default": True}),
        ("explode_fire_enabled", {"description": "§f爆炸起火 §7(需先开启上一项)", "type": "bool", "default": True}),
        ("sound_enabled", {"description": "§f播放音效", "type": "bool", "default": True}),
        ("velocity", {"description": "§f飞行速度", "type": "int", "range": (1, 20), "default": 5}),
        ("max_time",
         {"description": "§f最大飞行秒数 §7(超时自动爆炸)", "type": "int", "range": (1, 120), "default": 20}),
        ("turn_rate", {"description": "§f转向频率 §7(一般不用改)", "type": "int", "range": (1, 50), "default": 5}),
        ("waterproof_enabled", {"description": "§f防水 §7(接触液体不引发爆炸)", "type": "bool", "default": True}),
        ("durability_consumption",
         {"description": "§f消耗耐久 §7(可改为0)", "type": "int", "range": (0, 50), "default": 1}),
        ("aim_sign_size_percentage",
         {"description": "§f落点标志放缩", "type": "int", "range": (30, 200), "default": 100}),
        ("alerting_sign_size_percentage",
         {"description": "§f巡飞弹警示标志放缩", "type": "int", "range": (30, 200), "default": 100}),
        ("func_aim_enabled", {"description": "§b[瞄准按钮]§f显示", "type": "bool", "default": True}),
        ("func_aim_green_intense",
         {"description": "§b[瞄准按钮]§f滤镜强度 §7(单位：百分比)", "type": "int", "range": (0, 100), "default": 30}),
        ("func_aim_fov",
         {"description": "§b[瞄准按钮]§f视野 §7(放大/缩小取决于个人)", "type": "int", "range": (40, 110),
          "default": 50}),
        ("func_aim_key",
         {"description": "§b[瞄准按钮]§fPC键位 1-26即A-Z", "type": "int", "range": (0, 26), "default": 3}),
        ("func_aim_size",
         {"description": "§b[瞄准按钮]§f大小放缩 §7(单位：百分比)", "type": "int", "range": (30, 200), "default": 100,
          "private": True}),
        ("func_fire_enabled", {"description": "§6[开火按钮]§f显示", "type": "bool", "default": True}),
        ("func_fire_cd", {"description": "§6[开火按钮]§f冷却时间", "type": "int", "range": (0, 120), "default": 0}),
        ("func_fire_key",
         {"description": "§6[开火按钮]§fPC键位 1-26即A-Z", "type": "int", "range": (0, 26), "default": 6}),
        ("func_fire_size",
         {"description": "§6[开火按钮]§f大小放缩 §7(单位：百分比)", "type": "int", "range": (30, 200), "default": 100,
          "private": True}),
        ("func_explode_enabled", {"description": "§5[强制引爆按钮]§f显示", "type": "bool", "default": True}),
        ("func_explode_key",
         {"description": "§5[强制引爆按钮]§fPC键位 1-26即A-Z", "type": "int", "range": (0, 26), "default": 7}),
        ("func_explode_size",
         {"description": "§5[强制引爆按钮]§f大小放缩 §7(单位：百分比)", "type": "int", "range": (30, 200),
          "default": 100, "private": True}),
        ("func_speed_up_enabled", {"description": "§a[加速按钮]§f显示", "type": "bool", "default": True}),
        ("func_speed_up_percentage",
         {"description": "§a[加速按钮]§f影响百分比", "type": "int", "range": (0, 300), "default": 100}),
        ("func_speed_up_key",
         {"description": "§a[加速按钮]§fPC键位 1-26即A-Z", "type": "int", "range": (0, 26), "default": 22}),
        ("func_speed_up_size",
         {"description": "§a[加速按钮]§f大小放缩 §7(单位：百分比)", "type": "int", "range": (30, 200), "default": 100,
          "private": True}),
        ("func_inspect_enabled", {"description": "§e[检视按钮]§f显示", "type": "bool", "default": True}),
        ("func_inspect_key",
         {"description": "§e[检视按钮]§fPC键位 1-26即A-Z", "type": "int", "range": (0, 26), "default": 25}),
        ("func_inspect_size",
         {"description": "§e[检视按钮]§f大小放缩 §7(单位：百分比)", "type": "int", "range": (30, 200), "default": 100,
          "private": True}),
    ]

    default_player_data = {"func_aim_pos": (165, 33), "func_fire_pos": (215, 33), "func_explode_pos": (275, 33),
                           "func_inspect_pos": (335, 33),
                           "func_speed_up_pos": (335, 83),
                           "usage_informed": False}

    private_keys = {setting[0] for setting in default_player_settings if "private" in setting[1]}

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
            if cls.cache[levelId]["sync_owner_settings"] and not cls.IsPrivateKey(key):
                playerId = cls.cache[levelId]['owner']
            return cls.cache[playerId][key]

    @classmethod
    def IsPrivateKey(cls, key):
        return key in cls.default_player_data or key in cls.private_keys
