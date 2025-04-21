SPECIAL_ENTITY_TYPE = set("minecraft:" + entity for entity in {
    "npc", "armor_stand", "tripod_camera", "falling_block", "moving_block", "xp_bottle",
    "xp_orb", "eye_of_ender_signal", "fireworks_rocket", "thrown_trident", "shulker_bullet", "fishing_hook",
    "chalkboard", "dragon_fireball", "arrow", "snowball", "egg", "painting",
    "fireball", "splash_potion", "ender_pearl", "leash_knot", "wither_skull", "wither_skull_dangerous",
    "lightning_bolt", "small_fireball", "area_effect_cloud",
    "chest_minecart", "command_block_minecart", "lingering_potion", "llama_spit",
    "evocation_fang"}) | set("orchiella:" + entity for entity in {
    "absorption_bomb", "remote_bomb", "remote_bomb_lightning", "remote_bomb_flame", "remote_bomb_quake",
    "heal_bomb_entity",
    "heal_bullet_entity", "speed_bullet_entity", "slow_bullet_entity", "poison_bullet_entity",
    "gravitation_trap_entity"})
PENETRABLE_BLOCK_TYPE = set("minecraft:" + block for block in {
    "flowing_water", "water", "flowing_lava", "lava", "end_portal", "portal", "fire"})
FORBIDDEN_BLOCK_TYPE = set("minecraft:" + block for block in {
    "bedrock", "barrier"})
INCOMPLETE_ITEM = {'count': 1, 'newAuxValue': 0, 'auxValue': 0,
                   'customTips': '', 'extraId': '', 'modEnchantData': [], 'modId': '',
                   'itemId': 0, 'modItemId': '', 'showInHand': True}
AIR_BLOCK = {'name': "minecraft:air", "aux": 0}
