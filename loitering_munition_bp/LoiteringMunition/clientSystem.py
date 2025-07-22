# -*- coding: utf-8 -*-
import math
import time

import mod.client.extraClientApi as clientApi
from mod.common.utils.mcmath import Vector3, Matrix

import config as DB
from LoiteringMunition import mathUtil
from LoiteringMunition.const import STATES, ANIM_CACHE, TRANSITION_DURATION
from LoiteringMunition.mathUtil import GetTransitionMolangDict
from LoiteringMunition.ui import uiMgr
from LoiteringMunition.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
PC = CF.CreateParticleSystem(None)
AC = CF.CreateCustomAudio(levelId)
GC = CF.CreateGame(levelId)
QC = CF.CreateQueryVariable(PID)
CC = CF.CreateCamera(PID)
OC = CF.CreateOperation(levelId)
PPC = CF.CreatePostProcess(levelId)
RC = CF.CreateRot(PID)
ARC = CF.CreateActorRender(levelId)
PVC = CF.CreatePlayerView(PID)
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
        self.frameDataDict = {"aim": {}, "alerting": []}
        self.animationCache = {}
        GC.AddRepeatedTimer(0.05, self.UpdateFrame)
        GC.AddRepeatedTimer(0.05, self.CheckTransition)

    @Listen
    def OnScriptTickClient(self):
        if not self.IsEquipped():
            return
        if not self.GetData("joystick_enabled"):
            return
        if self.nowState != 'aim':
            return
        missileId = CF.CreateRide(PID).GetEntityRider()
        if not missileId or CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:loitering_munition":
            return

        # 获取摇杆输入
        inputVec = CF.CreateActorMotion(PID).GetInputVector()
        inputRight, inputUp = -inputVec[0], inputVec[1]
        if abs(inputRight) < 1e-5 and abs(inputUp) < 1e-5:
            return

        currentDir = Vector3(clientApi.GetDirFromRot(RC.GetRot()))
        if abs(currentDir[1]) != 1:
            currentDirRight = Vector3.Cross(currentDir, Vector3(0, 1, 0))
        else:
            currentDirRight = Vector3(
                clientApi.GetDirFromRot((RC.GetRot()[0], RC.GetRot()[1] + math.radians(90))))
        currentDirUp = Vector3.Cross(currentDirRight, currentDir)

        transitionMatrix = Matrix.Create(
            [list(currentDir.ToTuple()), list(currentDirUp.ToTuple()), list(currentDirRight.ToTuple())]).Transpose()
        inputTransformed = transitionMatrix * Matrix.Create([[0, inputUp, inputRight]]).Transpose()
        inputTransformed = Vector3(inputTransformed[0, 0], inputTransformed[1, 0], inputTransformed[2, 0])

        newDir = ((currentDir + inputTransformed * 0.1).Normalized() * 100).ToTuple()
        cameraPos = CC.GetPosition()
        lookPos = (
            cameraPos[0] + newDir[0],
            cameraPos[1] + newDir[1],
            cameraPos[2] + newDir[2]
        )
        self.AppendFrame(lookPos, "aim", 1.1 / 30, 0)

        currentRot = clientApi.GetRotFromDir(currentDir.ToTuple())
        newRot = clientApi.GetRotFromDir(newDir)

        pitchStep = abs(math.radians(newRot[0]) - math.radians(currentRot[0])) * 30
        yawStep = abs(math.radians(newRot[1]) - math.radians(currentRot[1])) * 30

        # if abs(newRot[1]) > 20 or abs(currentRot[1]) > 20:
        #     RC.SetPlayerLookAtPos(lookPos, pitchStep * 1, yawStep * 1, True)
        #     print newRot[1], currentRot[1]
        # else:
        #     print "not", newRot
        #     RC.SetRot(newRot)
        RC.SetRot(newRot)

    # 其实是从服务端传过来的，服务端版本的这个事件会帮我们忽略耐久变化的情况
    def OnCarriedNewItemChangedClientEvent(self, event):
        newItem = event["newItemDict"]
        if newItem and newItem['newItemName'] == "orchiella:loitering_munition_launcher":
            self.SyncVarToServer(0, "equip", 1)
            self.SyncVarToServer(0.05, "equip", 0)
        else:
            self.SwitchState("idle", False)

    # 切换疾跑事件，其实有专门的原生molang表达式可以判断，但为了管理，由模组来控制
    @Listen("OnLocalPlayerActionClientEvent")
    def OnSwitchSprint(self, event):
        if not self.IsEquipped():
            return
        if event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.SwitchState("run")
        elif event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting:
            if self.nowState != "aim":
                self.SwitchState("idle")

    @Listen(("LeftClickBeforeClientEvent", "TapBeforeClientEvent"))
    def LeftClick(self, event):
        if not self.IsEquipped():
            return
        event['cancel'] = True
        if self.GetData("quick_shoot"):
            self.functionsScreen.on_click_down({'AddTouchEventParams': {'func_key': "fire"}})
            self.functionsScreen.on_click_up({})

    @Listen(("RightClickBeforeClientEvent", "HoldBeforeClientEvent"))
    def RightClick(self, event):
        if not self.IsEquipped():
            return
        event['cancel'] = True
        if self.GetData("quick_shoot"):
            self.functionsScreen.on_click_down({'AddTouchEventParams': {'func_key': "aim"}})
            self.functionsScreen.on_click_up({})

    nowState = "idle"
    beforeState = "idle"
    transitionFinishTime = 0
    targetState = None
    nowAnimationStartTime = 0
    fovBeforeAim = 60

    def CheckTransition(self):
        if self.transitionFinishTime != 0 and time.time() > self.transitionFinishTime:
            if self.beforeState != "aim" and self.targetState == "aim":
                self.PlaySound("aim")
                self.functionsScreen.GetBaseUIControl("/screen").SetVisible(True)
                self.fovBeforeAim = CC.GetFov()
                PPC.SetColorAdjustmentTint(self.GetData("func_aim_green_intense") / 100.0, (0, 255, 0))
                CC.SetFov(self.GetData("func_aim_fov"))
            self.nowState = self.targetState
            self.CallServer("UpdateState", 0, PID, self.targetState)
            self.transitionFinishTime = 0
            self.SyncVarToServer(0, "transition", 0)
            self.nowAnimationStartTime = time.time()
            self.beforeState = None
            self.targetState = None

    def SwitchState(self, _state, isTransition=True):
        if self.nowState == _state:
            return False
        for state in STATES:
            self.SyncVarToServer(0, state, 1 if state == _state else 0)

        if self.nowState == "aim" and _state != "aim":
            CC.SetFov(self.fovBeforeAim)
            if self.functionsScreen.GetBaseUIControl("/screen"):
                self.functionsScreen.GetBaseUIControl("/screen").SetVisible(False)
            PPC.SetColorAdjustmentTint(0, (0, 255, 0))
            OC.SetCanDrag(True)

        varDict = GetTransitionMolangDict(QC, self.animationCache, self.nowState, self.nowAnimationStartTime, _state)
        self.SyncVarDictToServer(0, varDict)
        if self.nowState == "transition":
            self.SyncVarToServer(0, "re_transition", 1)
            self.SyncVarToServer(0.05, "re_transition", 0)
        else:
            self.beforeState = self.nowState
        self.SyncVarToServer(0, "transition", 1)
        self.nowAnimationStartTime = time.time()
        self.targetState = _state
        self.nowState = "transition"
        self.CallServer("UpdateState", 0, PID, "transition")
        self.transitionFinishTime = self.nowAnimationStartTime + (TRANSITION_DURATION if isTransition else 0)
        return True

    isControlling = False

    def SwitchControl(self, boolean):
        self.isControlling = boolean
        if boolean:
            if self.GetData("joystick_enabled"):
                OC.SetCanDrag(False)
            else:
                clientApi.HideMoveGui(True)
            PVC.LockPerspective(0)
            clientApi.HideSlotBarGui(True)
            clientApi.HideExpGui(True)
            clientApi.HideHorseHealthGui(True)
            clientApi.HideHealthGui(True)
            clientApi.HideHungerGui(True)
            clientApi.HideArmorGui(True)
        else:
            OC.SetCanDrag(True)
            PVC.LockPerspective(-1)
            clientApi.HideSlotBarGui(False)
            clientApi.HideExpGui(False)
            clientApi.HideHorseHealthGui(False)
            clientApi.HideHealthGui(False)
            clientApi.HideHungerGui(False)
            clientApi.HideArmorGui(False)
            clientApi.HideMoveGui(False)
        self.SyncVarToServer(0, "invisibility", 1 if boolean else 0)

    def ReleaseSkill(self, skill):
        if not self.IsEquipped():
            return
        if self.nowState == "equip":
            return
        if skill == "aim":
            if self.nowState == skill or self.targetState == skill:
                self.SwitchState("idle")
            else:
                self.SwitchState(skill)
        elif skill == "inspect":
            if self.nowState == skill or self.targetState == skill:
                self.SwitchState("idle")
            else:
                self.SwitchState(skill, self.nowState != "idle")
        elif skill == "fire":
            self.CallServer("Shoot", 0, PID)
        elif skill == "explode":
            self.CallServer("ExplodeByPlayerId", 0, PID)
        elif skill == "speed_up":
            self.CallServer("SpeedUp", 0, PID)
            if self.isControlling:
                CC.SetFov(int(self.fovBeforeAim * 1.2))


    @Listen
    def UnLoadClientAddonScriptsBefore(self, event):
        self.SwitchState("idle", False)

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        PPC.SetEnableColorAdjustment(True)
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
        for state in STATES | {"re_transition", "invisibility"}:
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, state), 0)
        self.Rebuild(PID)
        self.animationCache = ANIM_CACHE

        def equip():
            if self.IsEquipped():
                pass
            self.CallServer("SyncRebuild", 0, PID)

        GC.AddTimer(1, equip)

    def Rebuild(self, playerId=PID, state=None):
        actorComp = CF.CreateActorRender(playerId)
        prefix = DB.mod_name + "_launcher_"
        actorComp.AddPlayerGeometry(prefix + "arm", "geometry." + prefix + "arm")
        actorComp.AddPlayerRenderController("controller.render." + prefix + "arm",
                                            "v.is_first_person && query.get_equipped_item_full_name('main_hand') == 'orchiella:loitering_munition_launcher'")
        for aniName in STATES - {"re_transition"}:
            actorComp.AddPlayerAnimation(prefix + "1st_" + aniName,
                                         "animation." + DB.mod_name + "_launcher" + ".1st_" + aniName)
            actorComp.AddPlayerAnimation(prefix + "3rd_" + aniName,
                                         "animation." + DB.mod_name + "_launcher" + ".3rd_" + aniName)

        actorComp.AddPlayerAnimationController(prefix + "arm_controller",
                                               "controller.animation." + DB.mod_name + "_launcher" + ".general")
        actorComp.AddPlayerScriptAnimate(prefix + "arm_controller",
                                         "query.get_equipped_item_full_name('main_hand') == 'orchiella:loitering_munition_launcher'")

        actorComp.AddPlayerAnimation(DB.mod_name + "_invisibility",
                                     "animation." + DB.mod_name + ".invisibility")
        actorComp.AddPlayerAnimationIntoState('root', 'third_person',
                                              DB.mod_name + "_invisibility",
                                              "query.mod." + DB.mod_name + "_invisibility")

        actorComp.RebuildPlayerRender()

        if state:
            for _state in STATES:
                self.UpdateVar(_state, 1 if _state == state else 0, playerId)

    def IsEquipped(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == "orchiella:loitering_munition_launcher"

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value, PID)  # 我发现这里的PID参数不能去除，否则会是-1，不知道为何
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value, PID)

        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def SyncVarDictToServer(self, delay, varDict):
        if delay == 0:
            self.UpdateVarDict(varDict, PID)
        else:
            GC.AddTimer(delay, self.UpdateVarDict, varDict, PID)
        self.CallServer("SyncVarDictToClients", delay, PID, varDict)

    def InitMissileAnimation(self, missileId):
        comp = CF.CreateActorRender(missileId)
        comp.AddAnimationToOneActor(missileId, DB.mod_name + "_invisibility",
                                    "animation." + DB.mod_name + ".invisibility")
        comp.AddScriptAnimateToOneActor(missileId, DB.mod_name + "_invisibility",
                                        "q.has_rider")
        comp.RebuildRenderForOneActor()

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)

    def UpdateVarDict(self, varDict, playerId=PID):
        QueryComp = CF.CreateQueryVariable(playerId)
        for key, value in varDict.items():
            QueryComp.Set("query.mod." + DB.mod_name + "_" + key, value)

    def BindParticle(self, effectName, entityId, locator="locator"):
        parId = PC.Create("orchiella:" + effectName)
        PC.BindEntity(parId, entityId, locator, (0, 0, 0), (0, 0, 0))

    def AppendFrame(self, entityId, frameType, duration, height):
        if isinstance(self.frameDataDict[frameType], dict) and self.frameDataDict[frameType]:
            self.frameDataDict[frameType]['time'] = time.time()
            self.frameDataDict[frameType]['duration'] = duration
            self.frameDataDict[frameType]['entityId'] = entityId
            if isinstance(entityId, tuple):
                self.frameDataDict[frameType]["aniTransComp"].SetPos(
                    (entityId[0], entityId[1] + height * 0.5, entityId[2]))
            return
        frameTypeId = self.CreateEngineSfxFromEditor("effects/" + DB.mod_name + "_" + frameType + ".json")
        frameAniTransComp = CF.CreateFrameAniTrans(frameTypeId)
        frameAniControlComp = CF.CreateFrameAniControl(frameTypeId)
        frameAniControlComp.Play()
        frameData = {"time": time.time(), "duration": duration, "entityId": entityId, "height": height,
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
                    toDel = self.DealFrame(frameType, frameData)
                    if toDel:
                        frameDataToRemove.append(i)
                for index in reversed(frameDataToRemove):
                    del frameDataList[index]  # 倒序删除，避免索引错误
            elif isinstance(self.frameDataDict[frameType], dict):
                if not self.frameDataDict[frameType]: continue
                result = self.DealFrame(frameType, self.frameDataDict[frameType])
                if result:
                    self.frameDataDict[frameType] = {}

    def DealFrame(self, frameType, frameData):
        isBindEntity = not isinstance(frameData["entityId"], tuple)
        pos = CF.CreatePos(frameData["entityId"]).GetFootPos() if isBindEntity else \
            frameData["entityId"]
        if time.time() - frameData['time'] >= frameData["duration"] or (
                not pos and time.time() - frameData['time'] >= 0.5):
            # 若序列帧已过期则清理该序列帧，若绑定实体死亡则先隐藏，10秒后还是不对再清理
            if not pos and time.time() - frameData['time'] < 10:
                aniTransComp = frameData["aniTransComp"]
                aniTransComp.SetScale((0, 0, 0))
                return False
            aniControlComp = frameData["aniControlComp"]
            aniControlComp.Stop()
            return True
        elif pos:
            # 若序列帧未过期，则更新位置
            aniTransComp = frameData["aniTransComp"]
            scale = 0.5 * self.GetData(
                "{}_sign_size_percentage".format(frameType)) / 100.0 * mathUtil.get_scale_by_distance(
                CF.CreatePos(PID).GetFootPos(), pos)
            aniTransComp.SetScale((scale, scale, scale))
            aniTransComp.SetPos((
                pos[0],
                pos[1] + frameData["height"],
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

    def GetData(self, key, default=None):
        return self.settings.get(key, default)

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
        if key == 'sight_bead_enabled':
            self.functionsScreen.GetBaseUIControl("/sight_bead").SetVisible(value)

    def LoadData(self, settings):
        self.settings = settings
