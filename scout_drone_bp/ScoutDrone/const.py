STATES_WITHOUT_3RD = {"inspect", "deploy_tail", "deploy_rotor", "deploy_sight", "deploy_load",
                      "deploy_battery", "deployed", "edit_button"}
STATES = {"transition", "re_transition", "idle", "run", "shoot", "equip"} | STATES_WITHOUT_3RD
AIR_BLOCK = {"name": "minecraft:air", "aux": 0}
FIRE_BLOCK = {"name": "minecraft:fire", "aux": 0}
DRONE_TYPE = set("orchiella:scout_drone" + bow_type for bow_type in {""})
DRONE_LAUNCHER_TYPE = {droneType + "_launcher" for droneType in DRONE_TYPE}
ORIGINAL_SPEED = 0.7
ATTRIBUTE_TYPE = {"defense", "speed", "battery", "firm"}
INCOMPLETE_ITEM_DICT = {'count': 1, 'enchantData': [],
                        'itemId': -1, 'customTips': '', 'extraId': '', 'newAuxValue': 0, 'modEnchantData': [],
                        'modId': '', 'modItemId': '', 'auxValue': 0,
                        'showInHand': True}
WHITE_COLOR = (1.0, 1.0, 1.0)
ORANGE_COLOR = (1.0, 0.502, 0.0)
TRANSITION_DURATION = 0.15
