# -*- coding: utf-8 -*-
import time

import mod.client.extraClientApi as clientApi

import config as DB
from SRAW.const import STATES, ANIM_CACHE
from SRAW.mathUtil import set_transition_molang_vars
from SRAW.ui import uiMgr
from SRAW.ui.uiDef import UIDef

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
        self.frameDataDict = {"aim": {},"missile": {}}
        self.animationCache = {}
        GC.AddRepeatedTimer(0.05, self.UpdateFrame)
        GC.AddRepeatedTimer(0.05, self.CheckTransition)

    # 其实是从服务端传过来的，服务端版本的这个事件会帮我们忽略耐久变化的情况
    def OnCarriedNewItemChangedClientEvent(self, event):
        newItem = event["newItemDict"]
        if newItem and newItem['newItemName'] == "orchiella:sraw":
            self.PlaySound("equip")
            self.SyncVarToServer(0, "equip", 1)
            self.SyncVarToServer(0.05, "equip", 0)

    # 切换疾跑事件，其实有专门的原生molang表达式可以判断，但为了管理，由模组来控制
    @Listen("OnLocalPlayerActionClientEvent")
    def OnSwitchSprint(self, event):
        if not self.IsEquipped():
            return
        if event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.SwitchState("run")
        elif event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting:
            self.SwitchState("idle")

    @Listen(("LeftClickBeforeClientEvent", "TapBeforeClientEvent"))
    def LeftClick(self, event):
        if not self.IsEquipped():
            return
        event['cancel'] = True
        if self.nowState == "aim":
            self.CallServer("Shoot",0, PID)

    @Listen(("RightClickBeforeClientEvent", "HoldBeforeClientEvent"))
    def RightClick(self, event):
        if not self.IsEquipped():
            return
        event['cancel'] = True
        if self.nowState != "aim":
            self.SwitchState("aim")
            self.CallServer("UpdateAimState",0, PID, True)
        else:
            self.SwitchState("idle")
            self.CallServer("UpdateAimState",0, PID, False)

    nowState = "idle"
    transitionFinishTime = 0
    targetState = None
    nowAnimationStartTime = 0

    def CheckTransition(self):
        if self.transitionFinishTime != 0 and time.time() > self.transitionFinishTime:
            self.nowState = self.targetState
            self.transitionFinishTime = 0
            self.SyncVarToServer(0, "transition", 0)
            self.nowAnimationStartTime = time.time()

    def SwitchState(self, _state, isTransition=True):
        print self.nowState, _state
        for state in STATES:
            self.SyncVarToServer(0, state, 1 if state == _state else 0)
        if isTransition:
            set_transition_molang_vars(QC, self.animationCache, self.nowState, self.nowAnimationStartTime, _state)
            if self.nowState == "transition":
                self.SyncVarToServer(0, "re_transition", 1)
                self.SyncVarToServer(0.05, "re_transition", 0)
            self.SyncVarToServer(0, "transition", 1)
            self.nowAnimationStartTime = time.time()
            self.nowState = "transition"
            self.transitionFinishTime = self.nowAnimationStartTime + 0.5
            self.targetState = _state
        else:
            self.nowState = _state
        return True

    def ReleaseSkill(self, skill):
        if not self.IsEquipped():
            return
        if self.nowState == "equip":
            return
        self.CallServer("ReleaseSkill", 0, PID, skill)

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        self.CallServer("LoadData", 0, PID)
        levelQC = CF.CreateQueryVariable(levelId)
        for perspective in ("1st", "3rd"):
            for bone in ("item", "right", "left"):
                for attr in ("rot", "pos"):
                    for node in ("s", "e"):
                        for coord in ("x", "y", "z"):
                            levelQC.Register(
                                'query.mod.{}_trans_{}_{}_{}_{}_{}'.format(DB.mod_name, perspective, bone, attr, node,
                                                                           coord), 0)
        for state in STATES | {"re_transition"}:
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, state), 0)
        self.Rebuild(PID)

        self.animationCache = ANIM_CACHE

        def equip():
            if self.IsEquipped():
                pass
            self.CallServer("SyncRebuild", 0, PID)

        GC.AddTimer(1, equip)

    def Rebuild(self, playerId):
        actorComp = CF.CreateActorRender(playerId)
        prefix = DB.mod_name + "_"
        actorComp.AddPlayerGeometry(prefix + "arm", "geometry.{}_arm".format(DB.mod_name))
        actorComp.AddPlayerRenderController("controller.render.{}_arm".format(DB.mod_name),
                                            "v.is_first_person && query.get_equipped_item_full_name('main_hand') == 'orchiella:sraw'")
        for aniName in {"base"} | STATES:
            actorComp.AddPlayerAnimation(prefix + "1st_" + aniName, "animation." + DB.mod_name + ".1st_" + aniName)
            actorComp.AddPlayerAnimation(prefix + "3rd_" + aniName, "animation." + DB.mod_name + ".3rd_" + aniName)

        actorComp.AddPlayerAnimationController(prefix + "arm_controller", "controller.animation.sraw.general")
        actorComp.AddPlayerScriptAnimate(prefix + "arm_controller",
                                         "query.get_equipped_item_full_name('main_hand') == 'orchiella:sraw'")
        actorComp.AddPlayerScriptAnimate(prefix + "1st_base",
                                         "v.is_first_person && query.get_equipped_item_full_name('main_hand') == 'orchiella:sraw'")
        actorComp.AddPlayerScriptAnimate(prefix + "3rd_base",
                                         "!v.is_first_person && query.get_equipped_item_full_name('main_hand') == 'orchiella:sraw'")

        actorComp.RebuildPlayerRender()

    def IsEquipped(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == "orchiella:sraw"

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value, PID)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value, PID)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)

    def BindParticle(self, effectName, entityId, locator="locator"):
        parId = PC.Create("orchiella:" + effectName)
        PC.BindEntity(parId, entityId, locator, (0, 0, 0), (0, 0, 0))

    def AppendFrame(self, entityId, frameType, duration, height, heightAmplifier):
        if isinstance(self.frameDataDict[frameType], dict) and self.frameDataDict[frameType]:
            self.frameDataDict[frameType]['time'] = time.time() + duration
            self.frameDataDict[frameType]['entityId'] = entityId
            if isinstance(entityId, tuple):
                self.frameDataDict[frameType]["aniTransComp"].SetPos((
                    entityId[0],
                    entityId[1] + height * (
                        0.5 if heightAmplifier == 0.0 else heightAmplifier),
                    entityId[2]
                ))
            return
        frameTypeId = self.CreateEngineSfxFromEditor("effects/" + DB.mod_name + "_" + frameType + ".json")
        frameAniTransComp = CF.CreateFrameAniTrans(frameTypeId)
        frameAniControlComp = CF.CreateFrameAniControl(frameTypeId)
        scale = 0.25 * self.GetData("{}_sign_size_percentage".format(frameType)) / 100.0
        frameAniTransComp.SetScale((scale, scale, scale))
        frameAniControlComp.Play()
        frameData = {"time": time.time() + duration,
                     "entityId": entityId, "height": height, "heightAmplifier": heightAmplifier,
                     "aniTransComp": frameAniTransComp, "aniControlComp": frameAniControlComp}
        if isinstance(self.frameDataDict[frameType], list):
            self.frameDataDict[frameType].append(frameData)
        elif isinstance(self.frameDataDict[frameType], dict):
            self.frameDataDict[frameType] = frameData

    def UpdateFrame(self):
        if not self.frameDataDict: return  # 尚未加载序列帧
        for frameType in self.frameDataDict:
            if isinstance(self.frameDataDict[frameType], list):
                frameDataList = self.frameDataDict[frameType]
                if not frameDataList: continue
                frameDataToRemove = []
                for i, frameData in enumerate(frameDataList):
                    toDel = self.DealFrame(frameData)
                    if toDel:
                        frameDataToRemove.append(i)
                for index in reversed(frameDataToRemove):
                    del frameDataList[index]  # 倒序删除，避免索引错误
            elif isinstance(self.frameDataDict[frameType], dict):
                if not self.frameDataDict[frameType]: continue
                result = self.DealFrame(self.frameDataDict[frameType])
                if result:
                    self.frameDataDict[frameType] = {}

    def DealFrame(self, frameData):
        nowTime = time.time()
        isBindEntity = not isinstance(frameData["entityId"], tuple)
        pos = CF.CreatePos(frameData["entityId"]).GetFootPos() if isBindEntity else \
            frameData["entityId"]
        if nowTime >= frameData["time"] or not pos:
            # 若序列帧已过期，则清理该序列帧
            aniControlComp = frameData["aniControlComp"]
            aniControlComp.Stop()
            return True
        elif pos:
            # 若序列帧未过期，则更新位置
            aniTransComp = frameData["aniTransComp"]
            heightAmplifier = frameData["heightAmplifier"]
            aniTransComp.SetPos((
                pos[0],
                pos[1] + frameData["height"] * (
                    0.5 if heightAmplifier == 0.0 else heightAmplifier),
                pos[2]
            ))
        return False

    def SyncSoundToServer(self, delay, soundName):
        if delay == 0:
            self.PlaySound(soundName)
        else:
            GC.AddTimer(delay, self.PlaySound, soundName)
        self.CallServer("SyncSoundToClients", delay, PID, soundName)

    def PlaySound(self, soundName):
        if not self.GetData("sound_enabled"):
            return
        AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)

    def PlayParticle(self, particleName, poses, varDict=None):
        if isinstance(poses, tuple):
            poses = {poses}
        prefix = "orchiella:" + DB.mod_name + "_"
        for pos in poses:
            parId = PC.Create(prefix + particleName, pos)
            if varDict:
                for key, value in varDict.items():
                    PC.SetVariable(parId, "variable." + key, value)

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
                self.functionsScreen.SetBtnSize(func_key, value)
                break

    def LoadData(self, settings):
        self.settings = settings
