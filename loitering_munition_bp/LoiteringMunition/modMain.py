# -*- coding: utf-8 -*-
from mod.common.mod import Mod

from config import ModName
import mod.server.extraServerApi as serverApi
import mod.client.extraClientApi as clientApi


@Mod.Binding(name=ModName, version='0.0.1')
class Main(object):
    @Mod.InitServer()
    def ServerInit(self):
        serverApi.RegisterSystem(ModName, 'ServerSystem', ModName + '.serverSystem.ServerSystem')

    @Mod.DestroyServer()
    def ServerDestroy(self):
        pass

    @Mod.InitClient()
    def ClientInit(self):
        clientApi.RegisterSystem(ModName, 'ClientSystem', ModName + '.clientSystem.ClientSystem')

    @Mod.DestroyClient()
    def ClientDestroy(self):
        pass
