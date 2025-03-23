# -*- coding: utf-8 -*-
import mod.client.extraClientApi as extraClientApi


class UIDef:
    HealGunSettings = "HealGunSettings"
    HealGunFunctions = "HealGunFunctions"


UIData = {
    UIDef.HealGunSettings: {
        "cls": "HealGun.ui.healGunSettings.HealGunSettings",
        "screen": "heal_gun_settings.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    },
    UIDef.HealGunFunctions: {
        "cls": "HealGun.ui.healGunFunctions.HealGunFunctions",
        "screen": "heal_gun_functions.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    }
}
