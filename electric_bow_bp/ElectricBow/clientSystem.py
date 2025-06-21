# -*- coding: utf-8 -*-
import random
import time

import mod.client.extraClientApi as clientApi

import config as DB
from ElectricBow.ui import uiMgr
from ElectricBow.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
PC = CF.CreateParticleSystem(None)
AC = CF.CreateCustomAudio(levelId)
GC = CF.CreateGame(levelId)
QC = CF.CreateQueryVariable(PID)
CC = CF.CreateCamera(PID)
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

        self.uiMgr = uiMgr.UIMgr()
        self.settingsScreen = None
        self.functionsScreen = None
        self.settings = {}
        self.frameDataDict = {"eb_lightning": []}
        GC.AddRepeatedTimer(0.05, self.UpdateFrame)
        GC.AddRepeatedTimer(0.5, self.TestVar)

    def TestVar(self):
        for key, value in {"aim_rot_offset_x": -133, "aim_rot_offset_y": 61, "aim_rot_offset_z": 131,
                           "aim_pos_offset_x": 4.3, "aim_pos_offset_y": 3.1, "aim_pos_offset_z": -5.3,
                           "run_rot_offset_x": -17, "run_rot_offset_y": 52, "run_rot_offset_z": -17,
                           "run_pos_offset_x": 2.1, "run_pos_offset_y": 2, "run_pos_offset_z": 1.7}.items():
            QC.Set('query.mod.{}_{}'.format(DB.mn, key), value)

    @Listen
    def OnCarriedNewItemChangedClientEvent(self, event):
        item = event["itemDict"]
        if not item:
            return
        if item['newItemName'] == "orchiella:electric_bow":
            # CC.SetFov(60)
            self.BlinkVar("equip")
        else:
            if self.aimFinished or self.fovAnimating:
                # 如果在fov动画时或瞄准状态下切换了武器，则重置fov
                self.ResumeFov()

    # 切换疾跑事件，其实有专门的原生molang表达式可以判断，但为了管理，由模组来控制
    @Listen("OnLocalPlayerActionClientEvent")
    def OnSwitchSprint(self,event):
        if not self.IsEquipped():
            return
        if event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.BlinkVar("run_enter")
        elif event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting:
            self.BlinkVar("exit_enter")

    @Listen(("LeftClickBeforeClientEvent", "TapBeforeClientEvent"))
    def LeftClick(self, event):
        if self.IsEquipped():
            event['cancel'] = True

    @Listen(("HoldBeforeClientEvent", "RightClickBeforeClientEvent"))
    def OnEnterAim(self, event):
        if not self.IsEquipped():
            return
        print QC.GetMolangValue("q.all_animations_finished")
        if self.nowBlinkVar == self.nowBlinkVar:
            self.BlinkVar("aim_enter")
            self.fovBeforeAiming = CC.GetFov()
            self.tick = 0
            self.fovStart = self.fovBeforeAiming
            self.fovEnd = 40
            self.fovStep = -2
            self.fovAnimating = True

    def ResumeFov(self):
        self.tick = 0
        self.fovStart = CC.GetFov()
        self.fovEnd = self.fovBeforeAiming
        self.fovStep = 5
        self.fovAnimating = True
        self.aimFinished = False

    tick = 0
    fovAnimating = False
    aimFinished = False
    fovBeforeAiming = 0
    fovStart = 0
    fovEnd = 0
    fovStep = 0

    @Listen
    def OnScriptTickClient(self):
        if not self.fovAnimating:
            # 说明不在动画状态
            return
        if (self.fovStep > 0 and CC.GetFov() >= self.fovEnd) or \
                (self.fovStep <= 0 and CC.GetFov() <= self.fovEnd):
            # 达到目的
            self.fovAnimating = False
            if self.fovStep < 0:
                self.aimFinished = True
            return
        self.tick += 1
        CC.SetFov(self.fovStart + self.tick * self.fovStep)

    @Listen(("TapOrHoldReleaseClientEvent", "RightClickReleaseClientEvent"))
    def OnShoot(self, event):
        if not self.IsEquipped():
            return
        if not self.GetVar("shoot"):
            self.BlinkVar("shoot")
            self.ResumeFov()

    def ReleaseSkill(self, skill):
        if not self.IsEquipped():
            return
        self.CallServer("ReleaseSkill", 0, PID, skill)

    def GetVar(self, key):
        return QC.Get("query.mod." + DB.mn + "_" + key)

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value):
        QC.Set("query.mod." + DB.mn + "_" + key, value)

    nowBlinkVar = "default"  # 最近一次闪烁的变量，用于推测当前的动画阶段

    # 让变量闪烁一次，用于通知状态转换
    def BlinkVar(self, key):
        self.UpdateVar(key, 1.0)
        self.nowBlinkVar = "blink"
        GC.AddTimer(0.05, self.UpdateVar, key, 0.0)  # 如果不延迟一点，闪烁不会被检测到

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        self.CallServer("LoadData", 0, PID)
        levelQC = CF.CreateQueryVariable(levelId)
        for key, value in {"equip": 0, "aim_enter": 0, "shoot": 0,
                           "run_enter": 0, "run_exit": 0,
                           "idle_pos_x": 0, "idle_pos_y": -3, "idle_pos_z": -6,
                           "idle_rot_x": -14, "idle_rot_y": -97, "idle_rot_z": -13,
                           "aim_rot_offset_x": -133, "aim_rot_offset_y": 61, "aim_rot_offset_z": 131,
                           "aim_pos_offset_x": 4.3, "aim_pos_offset_y": 3.1, "aim_pos_offset_z": -5.3,
                           "run_rot_offset_x": -17, "run_rot_offset_y": 52, "run_rot_offset_z": -17,
                           "run_pos_offset_x": 2.1, "run_pos_offset_y": 2, "run_pos_offset_z": 1.7,
                           "hide_offset": 100}.items():
            levelQC.Register('query.mod.{}_{}'.format(DB.mn, key), value)
            QC.Set('query.mod.{}_{}'.format(DB.mod_name, key), value)

    def IsEquipped(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == "orchiella:electric_bow"

    @Listen
    def UiInitFinished(self, args):
        self.uiMgr.Init(self)
        self.settingsScreen = self.uiMgr.GetUI(UIDef.Settings)
        self.functionsScreen = self.uiMgr.GetUI(UIDef.Functions)
        self.functionsScreen.Display(True)

    def PlayParticle(self, particleName, poses, varDict=None):
        if isinstance(poses, tuple):
            poses = {poses}
        prefix = "orchiella:" + DB.mod_name + "_"
        for pos in poses:
            parId = PC.Create(prefix + particleName, pos)
            if varDict:
                for key, value in varDict.items():
                    PC.SetVariable(parId, "variable." + key, value)

    def PlaySound(self, soundName):
        AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)

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
        if not self.functionsScreen:
            return
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
                self.functions
