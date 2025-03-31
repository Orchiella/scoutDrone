# -*- coding: utf-8 -*-
import time

import mod.client.extraClientApi as clientApi

import config as DB
from HealGun.ui import uiMgr
from HealGun.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
parComp = CF.CreateParticleSystem(None)
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
        self.is_attacking = False

        self.uiMgr = uiMgr.UIMgr()
        self.settingsScreen = None
        self.settings = {}

        self.frameDict = {}
        self.effectedEntities = {"lock": {}}
        for effect in self.effectedEntities:
            frameEntityId = self.CreateEngineSfxFromEditor("effects/heal_gun_" + effect + ".json")
            frameAniTransComp = CF.CreateFrameAniTrans(frameEntityId)
            frameAniCtrlComp = CF.CreateFrameAniControl(frameEntityId)
            frameAniCtrlComp.SetLoop(True)
            self.frameDict[effect] = {
                "id": frameEntityId,
                "ani_trans_comp": frameAniTransComp,
                "ani_control_comp": frameAniCtrlComp}
        GC.AddRepeatedTimer(0.1, self.ShowEffect)

    def UpdateEffectTime(self, targetId, duration, effectName, height, extraHeight=0):
        effectData = self.effectedEntities[effectName]
        if effectData and effectData["entity"] == targetId:
            effectData["time"] = time.time() + duration
        else:
            frameAniControl = self.frameDict[effectName]["ani_control_comp"]
            newData = {"effect": effectName,
                       "time": time.time() + duration,
                       "entity": targetId,
                       "height": height,
                       "extra_height": extraHeight,
                       "frame_entity_id": self.frameDict[effectName]["id"],
                       "frame_ani_trans": self.frameDict[effectName]["ani_trans_comp"],
                       "frame_ani_control": frameAniControl}
            self.effectedEntities[effectName] = newData
            frameAniControl.Play()

    def ShowEffect(self):
        if not self.effectedEntities:
            return
        for effect in self.effectedEntities:
            effectData = self.effectedEntities[effect]
            if not effectData:
                continue
            now_time = time.time()
            pos = CF.CreatePos(effectData["entity"]).GetPos()
            if now_time >= effectData["time"] or pos is None:
                self.frameDict[effect]["ani_control_comp"].Stop()
                self.effectedEntities[effect] = {}
            else:
                frame_ani_trans_comp = self.frameDict[effect]["ani_trans_comp"]
                extra_height = effectData["extra_height"]
                frame_ani_trans_comp.SetPos(
                    (pos[0], pos[1] + effectData["height"] * (
                        0.5 if extra_height == 0.0 else extra_height), pos[2]))

    def PlayParticle(self, particleName, pos, varDict=None):
        parId = parComp.Create("heal_gun:" + particleName, pos)
        if varDict:
            for key, value in varDict.items():
                parComp.SetVariable(parId, "variable." + key, value)

    @Listen(("LeftClickBeforeClientEvent", "TapBeforeClientEvent"))
    def LeftClick(self, event):
        self.Click(event)

    @Listen(("HoldBeforeClientEvent", "RightClickBeforeClientEvent"))
    def RightClick(self, event):
        self.Click(event)

    def Click(self, event):
        if not self.IsHoldingGun():
            return
        # 暂时没想到怎么互动

    def ReleaseSkill(self, skill):
        if not self.IsHoldingGun():
            return
        if self.is_attacking:
            return
        if skill == "self_heal":
            self.CallServer("ReleaseSkill", 0, PID, skill)
        elif skill == "launch_bomb":
            self.CallServer("ReleaseSkill", 0, PID, skill)

    def Shoot(self, bulletType):
        if not self.IsHoldingGun():
            return
        self.UpdateVar("heal_gun_attacking", 1)
        self.CallServer("Shoot", 0, PID, bulletType)
        GC.AddTimer(0.3, self.UpdateVar, "heal_gun_attacking", 0)

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("q.mod." + key, value)
        if key == "heal_gun_attacking" and playerId == PID:
            self.is_attacking = True if value == 1.0 else False

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        queryComp = CF.CreateQueryVariable(clientApi.GetLevelId())
        queryComp.Register('query.mod.heal_gun_attacking', 0.0)

        queryComp = CF.CreateQueryVariable(PID)
        queryComp.Set('query.mod.heal_gun_attacking', 0.0)

        actorComp = CF.CreateActorRender(PID)
        actorComp.AddPlayerAnimation('heal_gun_third_hold_arm', 'animation.heal_gun.third_hold_arm')
        actorComp.AddPlayerAnimationIntoState('root', 'third_person', 'heal_gun_third_hold_arm',
                                              "q.get_equipped_item_full_name('main_hand') == 'orchiella:heal_gun' ||"
                                              "q.get_equipped_item_full_name('off_hand') == 'orchiella:heal_gun'")
        actorComp.RebuildPlayerRender()

        self.CallServer("LoadData", 0, PID)

    def IsHoldingGun(self):
        return (CF.CreateItem(PID).GetCarriedItem() and CF.CreateItem(PID).GetCarriedItem()[
            'newItemName'] == 'orchiella:heal_gun') or (
                CF.CreateItem(PID).GetOffhandItem() and CF.CreateItem(PID).GetOffhandItem()[
            'newItemName'] == 'orchiella:heal_gun')

    @Listen
    def UiInitFinished(self, args):
        self.uiMgr.Init(self)
        self.settingsScreen = self.uiMgr.GetUI(UIDef.HealGunSettings)
        self.uiMgr.GetUI(UIDef.HealGunFunctions).Display(True)

    @Listen('ServerEvent', DB.ModName, 'ServerSystem')
    def OnGetServerEvent(self, args):
        funcName = args['funcName']
        if not funcName.startswith("!"):
            getattr(self, funcName)(*args.get('args', ()), **args.get('kwargs', {}))
        else:
            getattr(self.settingsScreen, funcName[1:])(*args.get('args', ()), **args.get('kwargs', {}))

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

    def LoadData(self, settings):
        self.settings = settings
