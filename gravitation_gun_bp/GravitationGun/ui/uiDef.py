# -*- coding: utf-8 -*-
import mod.client.extraClientApi as extraClientApi


class UIDef:
    GravitationGunSettings = "GravitationGunSettings"
    GravitationGunFunctions = "GravitationGunFunctions"


UIData = {
    UIDef.GravitationGunSettings: {
        "cls": "GravitationGun.ui.gravitationGunSettings.GravitationGunSettings",
        "screen": "gravitation_gun_settings.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    },
    UIDef.GravitationGunFunctions: {
        "cls": "GravitationGun.ui.gravitationGunFunctions.GravitationGunFunctions",
        "screen": "gravitation_gun_functions.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    }
}
