PENETRABLE_BLOCK_TYPE = set("minecraft:" + block for block in {
    "flowing_water", "water", "flowing_lava", "lava", "end_portal", "portal", "fire",
    "tallgrass", "double_plant", "yellow_flower", "red_flower", "brown_mushroom", "red_mushroom",
    "torch","redstone_torch","vine","end_rod","standing_banner"})
INCOMPLETE_ITEM = {'count': 1, 'newAuxValue': 0, 'auxValue': 0,
                   'customTips': '', 'extraId': '', 'modEnchantData': [], 'modId': '',
                   'itemId': 0, 'modItemId': '', 'showInHand': True}
AIR_BLOCK = {'name': "minecraft:air", "aux": 0}
