# -*- coding: utf-8 -*-
import time

import mod.client.extraClientApi as clientApi

import config as DB
from GravitationGun.ui import uiMgr
from GravitationGun.ui.uiDef import UIDef

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
        self.functionsScreen = None
        self.settings = {}

        self.frameDict = {}  # 独一无二的特效的comp信息
        self.effectedEntities = {"lock": {}, "attracting": [], "frozen": []}
        for effect, effectData in self.effectedEntities.items():
            if isinstance(effectData, dict):
                frameEntityId = self.CreateEngineSfxFromEditor("effects/gravitation_gun_" + effect + ".json")
                frameAniTransComp = CF.CreateFrameAniTrans(frameEntityId)
                frameAniCtrlComp = CF.CreateFrameAniControl(frameEntityId)
                frameAniCtrlComp.SetLoop(True)
                self.frameDict[effect] = {
                    "frameEntityId": frameEntityId,
                    "aniTransComp": frameAniTransComp,
                    "aniControlComp": frameAniCtrlComp}
        GC.AddRepeatedTimer(0.1, self.ShowEffect)

    def UpdateEffectTime(self, targetId, duration, effectName, height, heightAmplifier=1,
                         randomFactors=(0.0, 0.0, 0.0)):
        effectData = self.effectedEntities[effectName]
        if isinstance(effectData, dict):
            if effectData and effectData["entityId"] == targetId:
                effectData["time"] = time.time() + duration
            else:
                frameAniControl = self.frameDict[effectName]["aniControlComp"]
                newData = {"effect": effectName,
                           "time": time.time() + duration,
                           "entityId": targetId,
                           "height": height,
                           "heightAmplifier": heightAmplifier,
                           "frameEntityId": self.frameDict[effectName]["frameEntityId"],
                           "aniTransComp": self.frameDict[effectName]["aniTransComp"],
                           "aniControlComp": frameAniControl}
                self.effectedEntities[effectName] = newData
                frameAniControl.Play()
        elif isinstance(effectData, list):
            frameEntityId = self.CreateEngineSfxFromEditor("effects/gravitation_gun_" + effectName + ".json")
            frameAniTransComp = CF.CreateFrameAniTrans(frameEntityId)
            frameAniControlComp = CF.CreateFrameAniControl(frameEntityId)
            scale = frameAniTransComp.GetScale()
            scaleAmplifier = 1
            frameAniTransComp.SetScale(
                (scale[0] * scaleAmplifier, scale[1] * scaleAmplifier, scale[2] * scaleAmplifier))
            frameAniControlComp.Play()
            self.effectedEntities[effectName].append({"effect": effectName,
                                                      "time": time.time() + duration,
                                                      "entityId": targetId,
                                                      "height": height,
                                                      "heightAmplifier": heightAmplifier,
                                                      "frameEntityId": frameEntityId,
                                                      "aniTransComp": frameAniTransComp,
                                                      "randomFactors": randomFactors,
                                                      "aniControlComp": frameAniControlComp})

    def ShowEffect(self):
        if not self.effectedEntities:
            return
        for effect in self.effectedEntities:
            effectData = self.effectedEntities[effect]
            if not effectData:
                continue
            if isinstance(effectData, dict):
                nowTime = time.time()
                pos = CF.CreatePos(effectData["entityId"]).GetFootPos()
                if nowTime >= effectData["time"] or pos is None:
                    self.frameDict[effect]["aniControlComp"].Stop()
                    self.effectedEntities[effect] = {}
                else:
                    aniTransComp = self.frameDict[effect]["aniTransComp"]
                    aniTransComp.SetPos(
                        (pos[0], pos[1] + effectData["height"] * effectData["heightAmplifier"], pos[2]))
            elif isinstance(effectData, list):
                frameDataToRemove = []
                for i, singleEffectData in enumerate(effectData):
                    nowTime = time.time()
                    pos = CF.CreatePos(singleEffectData["entityId"]).GetFootPos()
                    if nowTime >= singleEffectData["time"] or not pos:
                        # 若序列帧已过期，则清理该序列帧
                        aniControlComp = singleEffectData["aniControlComp"]
                        aniControlComp.Stop()
                        frameDataToRemove.append(i)
                    elif pos:
                        # 若序列帧未过期，则更新位置
                        aniTransComp = singleEffectData["aniTransComp"]
                        heightAmplifier = singleEffectData["heightAmplifier"]
                        randomFactors = singleEffectData["randomFactors"]
                        aniTransComp.SetPos((
                            pos[0] + randomFactors[0] * 0.2,
                            pos[1] + randomFactors[1] * 0.2 + singleEffectData["height"] * heightAmplifier,
                            pos[2] + randomFactors[2] * 0.2
                        ))
                for index in reversed(frameDataToRemove):
                    del effectData[index]  # 倒序删除，避免索引错误

    def PlayParticle(self, particleName, pos, varDict=None):
        parId = parComp.Create("gravitation_gun:" + particleName, pos)
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
        self.CallServer("ReleaseSkill", 0, PID, skill)

    def Use(self):
        if not self.IsHoldingGun():
            return
        self.UpdateVar("gravitation_gun_attacking", 1)
        self.CallServer("Use", 0, PID)
        GC.AddTimer(0.3, self.UpdateVar, "gravitation_gun_attacking", 0)

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("q.mod." + key, value)
        if key == "gravitation_gun_attacking" and playerId == PID:
            self.is_attacking = True if value == 1.0 else False

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        queryComp = CF.CreateQueryVariable(clientApi.GetLevelId())
        queryComp.Register('query.mod.gravitation_gun_attacking', 0.0)

        queryComp = CF.CreateQueryVariable(PID)
        queryComp.Set('query.mod.gravitation_gun_attacking', 0.0)

        actorComp = CF.CreateActorRender(PID)
        actorComp.AddPlayerAnimation('gravitation_gun_third_hold_arm', 'animation.gravitation_gun.third_hold_arm')
        actorComp.AddPlayerAnimationIntoState('root', 'third_person', 'gravitation_gun_third_hold_arm',
                                              "q.get_equipped_item_full_name('main_hand') == 'orchiella:gravitation_gun' ||"
                                              "q.get_equipped_item_full_name('off_hand') == 'orchiella:gravitation_gun'")
        actorComp.RebuildPlayerRender()

        self.CallServer("LoadData", 0, PID)

    def IsHoldingGun(self):
        return (CF.CreateItem(PID).GetCarriedItem() and CF.CreateItem(PID).GetCarriedItem()[
            'newItemName'] == 'orchiella:gravitation_gun') or (
                CF.CreateItem(PID).GetOffhandItem() and CF.CreateItem(PID).GetOffhandItem()[
            'newItemName'] == 'orchiella:gravitation_gun')

    @Listen
    def UiInitFinished(self, args):
        self.uiMgr.Init(self)
        self.settingsScreen = self.uiMgr.GetUI(UIDef.GravitationGunSettings)
        self.functionsScreen = self.uiMgr.GetUI(UIDef.GravitationGunFunctions)
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

    def LoadData(self, settings):
        self.settings = settings
