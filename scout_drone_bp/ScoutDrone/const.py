# coding=utf-8
STATES_WITHOUT_3RD = {"inspect", "run", "charge", "deploy_tail", "deploy_rotor", "deploy_sight", "deploy_load",
                      "deploy_battery", "deployed", "edit_button"}
STATES = {"transition", "re_transition", "idle", "shoot", "equip"} | STATES_WITHOUT_3RD
AIR_BLOCK = {"name": "minecraft:air", "aux": 0}
FIRE_BLOCK = {"name": "minecraft:fire", "aux": 0}
DRONE_TYPE = set("orchiella:scout_drone" + bow_type for bow_type in {""})
DRONE_LAUNCHER_TYPE = {droneType + "_launcher" for droneType in DRONE_TYPE}
ORIGINAL_SPEED = 0.7
ATTRIBUTE_TYPE = {"defense": {"default": 1, "max": 2},
                  "speed": {"default": 1, "max": 2},
                  "battery": {"default": 100, "max": 200},
                  "firm": {"default": 1, "max": 2}}
INCOMPLETE_ITEM_DICT = {'count': 1, 'enchantData': [],
                        'itemId': -1, 'customTips': '', 'extraId': '', 'newAuxValue': 0, 'modEnchantData': [],
                        'modId': '', 'modItemId': '', 'auxValue': 0,
                        'showInHand': True}
WHITE_COLOR = (1.0, 1.0, 1.0)
ORANGE_COLOR = (1.0, 0.502, 0.0)
TRANSITION_DURATION = 0.15
CUSTOM_TIPS = ('§6侦查无人机\n'
               '§f风扇种类: §7{}\n'
               '§f尾翼种类: §7{}\n'
               '§f下挂模块: §7{}\n'
               '§f放大瞄具: §7{}\n'
               '§f电池型号: §7{}\n'
               '§b电量剩余: {}§3/{}\n'
               '§a耐久剩余: {}§2/{}\n'
               '\n'
               '§5§o开发者蕙兰出品')
COUPONS = [
    dict(INCOMPLETE_ITEM_DICT, itemName="orchiella:scout_drone", newItemName="orchiella:scout_drone",
         extraId="battery:1,shelf:2,assist:1,string:2,sight:1", durability=1000)
]
