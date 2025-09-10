# coding=utf-8

import mod.server.extraServerApi as serverApi

from ScoutDrone.config import mod_name

levelId = serverApi.GetLevelId()

DEFAULT_PLAYER_SETTINGS = [
    ("explode_radius", {"description": "§f爆炸半径", "type": "int", "range": (0, 20), "default": 5}),
]

DEFAULT_PLAYER_DATA = {
    "func_shoot_pos": (-60, 30), "func_shoot_size": 50,
    "func_inspect_pos": (52, -60), "func_inspect_size": 40,
    "func_deploy_pos": (145, -60), "func_deploy_size": 40,
    "func_settings_pos": (62, -94), "func_settings_size": 20,
    "func_recover_pos": (-65, -40), "func_recover_size": 40,
    "func_control_pos": (-110, -40), "func_control_size": 40,
    "func_function_pos": (-20, 7), "func_function_size": 40,
    "func_scan_pos": (52, -14), "func_scan_size": 40,
    "func_mark_pos": (97, -14), "func_mark_size": 40,
    "func_explode_pos": (-20, -40), "func_explode_size": 40,
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
