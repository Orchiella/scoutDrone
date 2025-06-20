# -*- coding: utf-8 -*-
import random
import time

import mod.client.extraClientApi as clientApi

import config as DB
from HelmetNight.ui import uiMgr
from HelmetNight.ui.uiDef import UIDef

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
        self.frameDataDict = {"hn_frame": []}
        GC.AddRepeatedTimer(0.05, self.UpdateFrame)

    def AppendFrame(self, entityId, frameType, duration, height, color):
        frameTypeId = self.CreateEngineSfxFromEditor("effects/" + frameType + ".json")
        frameAniTransComp = CF.CreateFrameAniTrans(frameTypeId)
        frameAniControlComp = CF.CreateFrameAniControl(frameTypeId)
        scale = 0.6 * height
        frameAniTransComp.SetScale((scale, scale, 0))
        frameAniControlComp.SetMixColor((color[0], color[1], color[2], 255))
        frameAniControlComp.Play()
        self.frameDataDict[frameType].append(
            {"effect": frameType, "time": time.time() + duration,
             "entityId": entityId, "height": height,
             "aniTransComp": frameAniTransComp, "aniControlComp": frameAniControlComp})

    def UpdateFrame(self):
        if not self.frameDataDict: return  # 尚未加载序列帧
        for frameType in self.frameDataDict:
            frameDataList = self.frameDataDict[frameType]
            if not frameDataList: continue
            frameDataToRemove = []
            for i, frameData in enumerate(frameDataList):
                nowTime = time.time()
                pos = CF.CreatePos(frameData["entityId"]).GetFootPos()
                if nowTime >= frameData["time"]:
                    # 若序列帧已过期，则清理该序列帧
                    aniControlComp = frameData["aniControlComp"]
                    aniControlComp.Stop()
                    frameDataToRemove.append(i)
                elif pos:
                    # 若序列帧未过期，则更新位置
                    aniTransComp = frameData["aniTransComp"]
                    aniTransComp.SetPos((pos[0], pos[1] + frameData["height"] / 2, pos[2]))
            for index in reversed(frameDataToRemove):
                del frameDataList[index]  # 倒序删除，避免索引错误

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

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)
        if key == "lighting" and playerId == PID:
            self.is_using = True if value == 1.0 else False

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        self.CallServer("LoadData", 0, PID)
        queryComp = CF.CreateQueryVariable(clientApi.GetLevelId())
        queryComp.Register('query.mod.{}_lighting'.format(DB.mod_name), 0.0)
        queryComp = CF.CreateQueryVariable(PID)
        queryComp.Set('query.mod.{}_lighting'.format(DB.mod_name), 0.0)

    def IsWearing(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.ARMOR, 0)
        return item and item['newItemName'] == "orchiella:helmet_night"

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

    @Listen
    def OnKeyPressInGame(self, event):
        if event['isDown'] != '1':
            return
        key = event['key']
        offset = clientApi.GetMinecraftEnum().KeyBoardType.KEY_A - 1
        for func_key in self.functionsScreen.func_def.keys():
            if self.GetData("func_{}_key".format(func_key)) and key == str(
                    self.GetData("func_{}_key".format(func_key)) + offset):
                self.functionsScreen.on_click_down({'AddTouchEventParams': {'func_key': func_key}})
                self.functionsScreen.on_click_up({})

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
        s1, s2 = "func_{}_enabled", "func_{}_size"
        for func_key in self.functionsScreen.func_def.keys():
            if key == s1.format(func_key):
                self.functionsScreen.SetBtnVisible(func_key, value)
                break
            elif key == s2.format(func_key):
                self.functionsScreen.SetBtnSize(func_key, value)
                break

    def LoadData(self, settings):
        self.settings = settings
