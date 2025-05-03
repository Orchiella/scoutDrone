# -*- coding: utf-8 -*-
import mod.client.extraClientApi as extraClientApi

from JetBelt.config import ModName, modName, mod_name


class UIDef:
    Settings = ModName + "Settings"
    Functions = ModName + "Functions"


UIData = {
    UIDef.Settings: {
        "cls": "{}.ui.{}Settings.{}Settings".format(ModName, modName, ModName),
        "screen": mod_name + "_settings.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    },
    UIDef.Functions: {
        "cls": "{}.ui.{}Functions.{}Functions".format(ModName, modName, ModName),
        "screen": mod_name + "_functions.main",
        "layer": extraClientApi.GetMinecraftEnum().UiBaseLayer.Desk,
        "isHud": 1
    }
}
