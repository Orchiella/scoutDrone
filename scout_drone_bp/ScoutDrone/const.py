STATES_WITHOUT_3RD = {"inspect", "deploy_tail", "deploy_rotor", "deploy_sight", "deploy_load",
                      "deploy_battery", "deployed", "edit_button"}
STATES = {"transition", "re_transition", "idle", "run", "shoot", "equip"} | STATES_WITHOUT_3RD
AIR_BLOCK = {"name": "minecraft:air", "aux": 0}
FIRE_BLOCK = {"name": "minecraft:fire", "aux": 0}
DRONE_TYPE = set("orchiella:scout_drone" + bow_type for bow_type in {""})
ATTRIBUTE_TYPE = {"defense", "speed", "battery", "firm"}
WHITE_COLOR = (1.0, 1.0, 1.0)
ORANGE_COLOR = (1.0, 0.502, 0.0)
TRANSITION_DURATION = 0.15
