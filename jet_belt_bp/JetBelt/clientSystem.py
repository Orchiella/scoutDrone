# -*- coding: utf-8 -*-
import random
import time

import mod.client.extraClientApi as clientApi

import config as DB
from JetBelt.ui import uiMgr
from JetBelt.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
parComp = CF.CreateParticleSystem(None)
audioComp = CF.CreateCustomAudio(levelId)
GC = CF.CreateGame(levelId)
eventList = []


def Listen(funcOrStr, EN=clientApi.GetEngineNamespace(), ESN=clientApi.GetEngineSystemName(), priority=0):
    def binder(func):
        if callable(funcOrStr):
            eventList.append((EN, ESN, func.__name__, func, priority))
        else:
            if isinstance(funcOrStr, tuple):
                for funcStr in funcOrStr: eventList.append((EN, ESN, funcStr, func, priority))
            else:
                eventList.append((EN, ESN, funcOrStr, func, priority))
        return func

    return binder(funcOrStr) if callable(funcOrStr) else binder


class ClientSystem(clientApi.GetClientSystemCls()):
    def __init__(self, namespace, systemName):
        super(ClientSystem, self).__init__(namespace, systemName)
        for EN, ESN, eventName, callback, priority in eventList:
            self.ListenForEvent(EN, ESN, eventName, self, callback, priority)
        self.is_using = False

        self.uiMgr = uiMgr.UIMgr()
        self.settingsScreen = None
        self.functionsScreen = None
        self.settings = {}

    def PlayParticle(self, particleName, poses, varDict=None):
        if isinstance(poses, tuple):
            poses = {poses}
        prefix = "orchiella:" + DB.mod_name + "_"
        for pos in poses:
            parId = parComp.Create(prefix + particleName, pos)
            if varDict:
                for key, value in varDict.items():
                    parComp.SetVariable(parId, "variable." + key, value)

    def PlaySound(self, soundName):
        audioComp.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)

    def ReleaseSkill(self, skill):
        if not self.IsWearing():
            return
        self.CallServer("ReleaseSkill", 0, PID, skill)

    def Use(self, vector):
        if not self.IsWearing():
            return
        if self.GetData("func_use_sound_enabled"):
            self.PlaySound("jetting" + str(random.randint(1, 2)))
        self.UpdateVar("jetting", 1)
        self.CallServer("Use", 0, PID, vector)
        GC.AddTimer(0.3, self.UpdateVar, "jetting", 0)

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)
        if key == "jetting" and playerId == PID:
            self.is_using = True if value == 1.0 else False

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        self.CallServer("LoadData", 0, PID)
        queryComp = CF.CreateQueryVariable(clientApi.GetLevelId())
        queryComp.Register('query.mod.{}_jetting'.format(DB.mod_name), 0.0)
        queryComp = CF.CreateQueryVariable(PID)
        queryComp.Set('query.mod.{}_jetting'.format(DB.mod_name), 0.0)

    def IsWearing(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.ARMOR, 2)
        return item and item['newItemName'] == "orchiella:jet_belt"

    @Listen
    def UiInitFinished(self, args):
        self.uiMgr.Init(self)
        self.settingsScreen = self.uiMgr.GetUI(UIDef.Settings)
        self.functionsScreen = self.uiMgr.GetUI(UIDef.Functions)
        self.functionsScreen.Display(True)

    @Listen('ServerEvent', DB.ModName, 'ServerSystem')
    def OnGetServerEvent(self, args):
        funcName = args['funcName']
        if "." not in funcName:
            getattr(self, funcName)(*args.get('args', ()), **args.get('kwargs', {}))
        else:
            if not getattr(self, funcName.split(".")[0]):
                return
            getattr(getattr(self, funcName.split(".")[0]), funcName.split(".")[1])(*args.get('args', ()),
                                                                                   **args.get('kwargs', {}))

    def CallServer(self, funcName, delay, *args, **kwargs):
        if delay == 0:
            self.NotifyToServer('ClientEvent', DB.CreateEventData(funcName, args, kwargs))
        else:
            GC.AddTimer(delay, self.NotifyToServer, 'ClientEvent',
                        DB.CreateEventData(funcName, args, kwargs))

    def CallClient(self, playerId, funcName, *args, **kwargs):
        if playerId == PID: return getattr(self, funcName)(*args, **kwargs)
        self.CallServer('CallClient', playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.CallServer('CallAllClient', funcName, *args, **kwargs)

    def GetData(self, key):
        return self.settings[key]

    def SetData(self, key, value):
        self.settings[key] = value
        if key == 'func_use_size':
            self.functionsScreen.SetBtnSize("use", value)
        elif key == "func_flash_enabled":
            self.functionsScreen.SetBtnVisible("flash", value)
        elif key == "func_brake_enabled":
            self.functionsScreen.SetBtnVisible("brake", value)
        elif key == "func_fear_enabled":
            self.functionsScreen.SetBtnVisible("fear", value)
        elif key == "func_switch_power_enabled":
            self.functionsScreen.SetBtnVisible("switch_power", value)

    def LoadData(self, settings):
        self.settings = settings
