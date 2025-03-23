SPECIAL_ENTITIES = set("minecraft:" + entity for entity in [
    "npc", "armor_stand", "tripod_camera", "item", "tnt", "falling_block", "moving_block", "xp_bottle",
    "xp_orb", "eye_of_ender_signal", "fireworks_rocket", "thrown_trident", "shulker_bullet", "fishing_hook",
    "chalkboard", "dragon_fireball", "arrow", "snowball", "egg", "painting",
    "fireball", "splash_potion", "ender_pearl", "leash_knot", "wither_skull", "wither_skull_dangerous",
    "boat", "lightning_bolt", "small_fireball", "area_effect_cloud",
    "chest_minecart", "command_block_minecart", "lingering_potion", "llama_spit",
    "evocation_fang"]) | set("orchiella:" + entity for entity in [
    "absorption_bomb", "remote_bomb", "remote_bomb_lightning", "remote_bomb_flame", "remote_bomb_quake",
    "heal_bomb_entity",
    "heal_bullet_entity", "slow_bullet_entity", "poison_bullet_entity"])
HOLDING_POS_FOR_PHONE = (-7.0, 11.5, -17.0)
HOLDING_POS_FOR_PAD = (-7.0, 10.5, -15.0)
BULLET_ENTITY_TYPE_DICT = {"orchiella:heal_bullet_entity": {"type": "heal", "effect": "regeneration"},
                           "orchiella:slow_bullet_entity": {"type": "slow", "effect": "slowness"},
                           "orchiella:poison_bullet_entity": {"type": "poison", "effect": "poison"}}
BULLET_COLOR_DICT = {"heal": (0.8, 0.4, 0.2), "slow": (0.4, 0.4, 0.6), "poison": (0.4, 1, 0)}
