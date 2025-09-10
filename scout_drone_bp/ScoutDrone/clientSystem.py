# -*- coding: utf-8 -*-
import math
import time

import mod.client.extraClientApi as clientApi
from mod.common.utils.mcmath import Vector3, Matrix

import config as DB
from ScoutDrone import mathUtil, DeployHelper
from ScoutDrone.animData import ANIM_DATA
from ScoutDrone.const import STATES, TRANSITION_DURATION, STATES_WITHOUT_3RD, DRONE_TYPE, DRONE_LAUNCHER_TYPE
from ScoutDrone.mathUtil import GetTransitionMolangDict, GetFixOffset
from ScoutDrone.ui import uiMgr
from ScoutDrone.ui.scoutDroneFunctions import DEPLOYMENT
from ScoutDrone.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
PC = CF.CreatePlayer(PID)
ParC = CF.CreateParticleSystem(None)
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
        self.frameDataDict = {"frame": []}
        self.animationCache = {}

        self.frameRGB = {
            clientApi.GetMinecraftEnum().EntityType.Monster: (0.8, 0.1, 0.1),  # 暗红色，表示敌意
            clientApi.GetMinecraftEnum().EntityType.Animal: (0, 1, 0),  # 动物绿色
            clientApi.GetMinecraftEnum().EntityType.Ambient: (0.6, 0.6, 0.6),  # 中性灰，环境生物
            clientApi.GetMinecraftEnum().EntityType.Projectile: (1.0, 0.6, 0.0),  # 橙色，高速危险
            clientApi.GetMinecraftEnum().EntityType.AbstractArrow: (1.0, 0.6, 0.0),  # 橙色，和抛射物一样
            clientApi.GetMinecraftEnum().EntityType.WaterAnimal: (0.2, 0.6, 0.9),  # 海蓝色，表示水生
            clientApi.GetMinecraftEnum().EntityType.VillagerBase: (0.6, 0.4, 0.2),  # 棕褐色，贴合村民穿着
            clientApi.GetMinecraftEnum().EntityType.Player: (0.2, 0.4, 1.0),  # 亮蓝色，高度辨识
        }

        self.initViewBobbing = False
        self.initSmoothLighting = False
        self.addonDisabled = False

    @Listen("OnScriptTickClient")
    def Move(self):
        if not self.isControlling:
            return
        # 获取摇杆输入
        inputVec = CF.CreateActorMotion(PID).GetInputVector()
        inputRight, inputUp = -inputVec[0], inputVec[1]
        if abs(inputRight) < 1e-5 and abs(inputUp) < 1e-5:
            nowMotion = CF.CreateActorMotion(CF.CreateRide(PID).GetEntityRider()).GetMotion()
            if nowMotion and Vector3(nowMotion).Length() != 0:
                self.CallServer("SetMotion", PID, None)
            return
        currentDir = Vector3(clientApi.GetDirFromRot(RC.GetRot()))
        if abs(currentDir[1]) != 1:
            currentDirRight = Vector3.Cross(currentDir, Vector3(0, 1, 0))
        else:
            currentDirRight = Vector3(
                clientApi.GetDirFromRot((RC.GetRot()[0], RC.GetRot()[1] + math.radians(90))))
        currentDirUp = Vector3.Cross(currentDirRight, currentDir)

        transitionMatrix = Matrix.Create(
            [list(currentDir.ToTuple()), list(currentDirUp.ToTuple()),
             list(currentDirRight.ToTuple())]).Transpose()
        outputTransformed = transitionMatrix * Matrix.Create([[inputUp, 0, inputRight]]).Transpose()
        outputTransformed = (outputTransformed[0, 0], outputTransformed[1, 0], outputTransformed[2, 0])
        self.CallServer("SetMotion", PID, outputTransformed)

    @Listen
    def AddPlayerCreatedClientEvent(self, event):
        if event['playerId'] == PID: return
        self.CallServer("SyncRebuild", PID, event['playerId'])

    # 背包物品变化
    @Listen
    def InventoryItemChangedClientEvent(self, event):
        print event
        if event['playerId'] != PID or event['slot'] != CF.CreateItem(PID).GetSlotId():
            return
        oldItemName = event['oldItemDict']['newItemName']
        newItemName = event['newItemDict']['newItemName']
        if oldItemName == "minecraft:air" and newItemName in DRONE_LAUNCHER_TYPE:
            self.Equip(True, event['newItemDict']['extraId'])
        elif newItemName == "minecraft:air" and oldItemName in DRONE_LAUNCHER_TYPE:
            self.Equip(False)

    slotNow = -1

    @Listen("OnScriptTickClient")
    # 物品栏切换，现在改用定时器判断
    def SwitchSlot(self):
        slotBefore = self.slotNow
        slotNow = CF.CreateItem(PID).GetSlotId()
        if slotBefore == slotNow:
            return
        self.slotNow = slotNow
        itemComp = CF.CreateItem(PID)
        if slotNow > 8: return
        oldItem = itemComp.GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.INVENTORY, slotBefore)
        newItem = itemComp.GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.INVENTORY, slotNow)
        if oldItem and oldItem['newItemName'] in DRONE_LAUNCHER_TYPE:
            self.Equip(False)
        if newItem and newItem['newItemName'] in DRONE_LAUNCHER_TYPE:
            self.Equip(True, newItem['extraId'])

    def Equip(self, boolean, extraId=None):
        if boolean:
            self.RefreshDeployment(extraId)
            self.SwitchState("equip", False)
            clientApi.HideCrossHairGUI(True)
            PVC.SetToggleOption(clientApi.GetMinecraftEnum().OptionId.VIEW_BOBBING, True)
        else:
            self.SwitchState("idle", False)
            clientApi.HideCrossHairGUI(False)
            PVC.SetToggleOption(clientApi.GetMinecraftEnum().OptionId.VIEW_BOBBING, self.initViewBobbing)
            PVC.SetToggleOption(clientApi.GetMinecraftEnum().OptionId.SMOOTH_LIGHTING, self.initSmoothLighting)
        GC.AddTimer(0.1, self.functionsScreen.RefreshButtonVisibility)

    @Listen
    def OnLocalPlayerActionClientEvent(self, event):
        if not self.GetEquipment():
            return
        if self.nowState == "inspect" or self.nowState == "shoot":
            return
        action = event['actionType']
        if action == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.SwitchState("run")
        elif action == clientApi.GetMinecraftEnum().PlayerActionType.StartSneaking:
            self.SwitchState("sneak")
        elif action == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting or action == clientApi.GetMinecraftEnum().PlayerActionType.StopSneaking:
            if self.nowState != "aim":
                self.BackIdle(True)

    nowState = "idle"
    beforeState = "idle"
    transitionFinishTime = 0
    targetState = None
    nowAnimationStartTime = 0
    tasks = []
    screenRate = 0

    @Listen("OnScriptTickClient")
    def CheckTransition(self):
        if not self.functionsScreen or not self.functionsScreen.initialized: return
        if self.transitionFinishTime != 0 and time.time() > self.transitionFinishTime:
            self.nowState = self.targetState
            self.transitionFinishTime = 0
            self.SyncVarToServer(0, "transition", 0)
            self.nowAnimationStartTime = time.time()
            self.beforeState = None
            self.targetState = None
        if self.tasks:
            taskId = id(self.tasks)
            for i in range(len(self.tasks) - 1, -1, -1):
                taskData = self.tasks[i]
                timeKey, task = taskData
                if time.time() > timeKey:
                    task()
                    if id(self.tasks) != taskId:
                        # task()可能会使得self.tasks原本的内容被重新赋值，如切换状态，那么就没必要继续遍历了
                        break
                    del self.tasks[i]
        width, height = GC.GetScreenSize()
        nowScreenRate = width / float(height)
        if self.screenRate != nowScreenRate:
            self.screenRate = nowScreenRate
            self.UpdateVar("fix_offset_x", GetFixOffset(nowScreenRate))
            self.functionsScreen.LoadButtons()

    def BackIdle(self, isIdleTransition=False, isRunTransition=True, isSneakTransition=True):
        if PC.isSneaking():
            self.SwitchState("sneak", isSneakTransition)
        else:
            if PC.isSprinting():
                self.SwitchState("run", isRunTransition)
            else:
                self.SwitchState("idle", isIdleTransition)

    def AddTask(self, timeNode, func, isTransition=False):
        if isinstance(timeNode, str):
            timeNode = self.animationCache["1st_" + timeNode]["length"]
        self.tasks.append(
            (time.time() + timeNode + (TRANSITION_DURATION if isTransition else 0) - 0.05, func))

    droneData = {}

    def SetDroneData(self, droneData):
        self.droneData = droneData

    isControlling = False

    def SwitchControl(self, boolean):
        self.isControlling = boolean
        if boolean:
            PVC.LockPerspective(0)
            clientApi.HideSlotBarGui(True)
            clientApi.HideExpGui(True)
            clientApi.HideHorseHealthGui(True)
            clientApi.HideHealthGui(True)
            clientApi.HideHungerGui(True)
            clientApi.HideArmorGui(True)
        else:
            PVC.LockPerspective(-1)
            clientApi.HideSlotBarGui(False)
            clientApi.HideExpGui(False)
            clientApi.HideHorseHealthGui(False)
            clientApi.HideHealthGui(False)
            clientApi.HideHungerGui(False)
            clientApi.HideArmorGui(False)
            clientApi.HideMoveGui(False)
        self.functionsScreen.RefreshButtonVisibility()

    def SwitchState(self, _state, isTransition=True):
        if 1:
            return
        if self.nowState == _state:
            return False
        varDict = None
        if self.tasks:
            self.tasks = []
        elif _state == "equip":
            self.AddTask(_state, self.BackIdle)
        elif _state == "inspect":
            self.AddTask(_state, self.BackIdle, isTransition)
        elif _state == "edit_button":
            self.AddTask(_state, self.functionsScreen.StartEditing)
        elif _state == "deployed":
            for attr in ("rot", "pos"):
                for i, coord in enumerate(("x", "y", "z")):
                    QC.Set('query.mod.{}_deployed_{}_{}'.format(DB.mod_name, attr, coord),
                           ANIM_DATA['1st_deploy_{}'.format(self.functionsScreen.nowDrill)]['bones'][
                               'scout_drone_launcher'][
                               'position' if attr == 'pos' else 'rotation']['0.0'][i])
            self.CallServer("Deploy", PID, self.functionsScreen.nowDrill, self.functionsScreen.index)
            self.AddTask(_state, lambda: self.BackIdle(True))
            varDict = GetTransitionMolangDict(QC, self.animationCache,
                                              "deploy_{}".format(self.functionsScreen.nowDrill),
                                              self.nowAnimationStartTime,
                                              "deploy_{}".format(self.functionsScreen.nowDrill))
        elif self.nowState == "edit_button":
            self.functionsScreen.EndEditing()
        elif self.nowState == "deployed":
            varDict = GetTransitionMolangDict(QC, self.animationCache,
                                              "deploy_{}".format(self.functionsScreen.nowDrill),
                                              self.nowAnimationStartTime, _state)

        if varDict is None:
            varDict = GetTransitionMolangDict(QC, self.animationCache, self.nowState,
                                              self.nowAnimationStartTime if isTransition else 0, _state)
        self.SyncVarDictToServer(0, varDict)
        for state in STATES:
            self.SyncVarToServer(0, state, 1 if state == _state else 0)
        if self.nowState == "transition":
            self.SyncVarToServer(0, "re_transition", 1)
            self.SyncVarToServer(0.05, "re_transition", 0)
        else:
            self.beforeState = self.nowState

        self.SyncVarToServer(0, "transition", 1)
        self.nowAnimationStartTime = time.time()
        self.targetState = _state
        self.nowState = "transition"
        self.transitionFinishTime = self.nowAnimationStartTime + (
            TRANSITION_DURATION if isTransition else 0)
        return True

    def RefreshDeployment(self, content):
        varDict = {"deployment_" + deployType: DeployHelper.Get(content, deployType) for deployType in
                   DEPLOYMENT.keys()}
        self.SyncVarDictToServer(0, varDict)
        if DeployHelper.Get(content, "torch") > 0:
            PVC.SetToggleOption(clientApi.GetMinecraftEnum().OptionId.SMOOTH_LIGHTING, True)

    def ClickButton(self, function):
        launcherItem = self.GetEquipment()
        # if not launcherItem:
        #     return False
        # if self.nowState == "equip" or self.nowState == "shoot":
        #     return False
        if function == "shoot":
            self.SwitchState("shoot", self.nowState != "idle")
            self.CallServer("Shoot", PID)
            return True
        elif function == "recover":
            self.CallServer("Recover", PID)
            return True
        elif function == "inspect" and not self.isControlling:
            self.SwitchState("inspect", self.nowState != "idle")
            return True
        elif function == "control":
            self.CallServer("Control", PID)
            return True
        elif function == "function" and self.isControlling:
            self.CallServer("Function", PID)
            return True
        elif function == "scan" and self.isControlling:
            self.CallServer("Scan", PID)
            return True
        elif function == "mark" and self.isControlling:
            targetId = self.SelectEntity(self.FilterSpecialEntity)
            if not targetId:
                self.functionsScreen.SendTip("未检测到目标", "c")
                return False
            self.CallServer("Mark", PID, targetId)
            return True
        elif function == "explode":
            self.CallServer("Explode", PID)
            return True

    def FilterSpecialEntity(self, entityId):
        boxSize = CF.CreateCollisionBox(entityId).GetSize()
        return boxSize[0] != 0.25 and boxSize[1] != 0.25

    def SelectEntity(self, filterFunc=None):
        rot = CF.CreateRot(PID).GetRot()
        sightVec = clientApi.GetDirFromRot(rot)
        minAngle = -999
        playerPos = CC.GetPosition()
        targetId = None
        for entityId in GC.GetEntitiesAround(PID, 60, {}):
            if PID == entityId:
                continue
            if CF.CreateRide(PID).GetEntityRider() == entityId:
                continue
            if filterFunc and not filterFunc(entityId):
                continue
            if not GC.CanSee(PID, entityId, 60, True, 180.0, 180.0):
                continue
            entityPos = CF.CreatePos(entityId).GetFootPos()
            relativePos = (
                entityPos[0] - playerPos[0],
                entityPos[1] - playerPos[1] + CF.CreateCollisionBox(entityId).GetSize()[1] * 0.5,
                entityPos[2] - playerPos[2])
            angle = math.acos(max(-1.0, min(1.0, (
                    relativePos[0] * sightVec[0] + relativePos[1] * sightVec[1] + relativePos[2] * sightVec[2]) /
                                            (math.sqrt(
                                                relativePos[0] ** 2 + relativePos[1] ** 2 + relativePos[2] ** 2) *
                                             math.sqrt(
                                                 sightVec[0] ** 2 + sightVec[1] ** 2 + sightVec[2] ** 2))))) \
                if (math.sqrt(relativePos[0] ** 2 + relativePos[1] ** 2 + relativePos[2] ** 2) * math.sqrt(
                sightVec[0] ** 2 + sightVec[1] ** 2 + sightVec[2] ** 2)) != 0 else 0.0
            print angle
            if angle > 0.15: continue
            if minAngle == -999 or angle < minAngle:
                minAngle = angle
                targetId = entityId
        return targetId

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        PPC.SetEnableColorAdjustment(True)
        self.CallServer("LoadData", PID)
        levelQC = CF.CreateQueryVariable(levelId)
        for perspective in ("1st", "3rd"):
            for bone in ("item", "right", "left"):
                for attr in ("rot", "pos"):
                    for node in ("s", "e"):
                        for coord in ("x", "y", "z"):
                            levelQC.Register(
                                'query.mod.{}_trans_{}_{}_{}_{}_{}'.format(DB.mod_name, perspective, bone, attr, node,
                                                                           coord), 0)
        for state in STATES:
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, state), 0)
        for attr in ("rot", "pos"):
            for coord in ("x", "y", "z"):
                levelQC.Register('query.mod.{}_deployed_{}_{}'.format(DB.mod_name, attr, coord), 0)
        width, height = GC.GetScreenSize()
        for varName, playerDefValue, levelDefValue in ({
            ("fix_offset_x", GetFixOffset(width / float(height)), 0),
            ("fix_offset_z", -0.5 if CF.CreateActorRender(PID).GetModelStyle() == 'slim' else 0, 0),
            ("speed_amplifier", 1, 1),
            ("drop_yaw", 0, 0)}
                .union({("deployment_" + deploymentType, 0, 0) for deploymentType in DEPLOYMENT})):
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, varName), levelDefValue)
            QC.Set('query.mod.{}_{}'.format(DB.mod_name, varName), playerDefValue)
        self.Rebuild(PID)
        self.animationCache = ANIM_DATA

        def equip():
            if self.GetEquipment():
                self.slotNow = -1

        GC.AddTimer(0.5, equip)

    def Rebuild(self, playerId=PID, state=None):
        actorComp = CF.CreateActorRender(playerId)
        prefix = DB.mod_name + "_"
        itemCondition = " or ".join(
            "query.get_equipped_item_full_name('main_hand') == '{}'".format(droneType) for droneType in
            DRONE_LAUNCHER_TYPE)
        actorComp.AddPlayerGeometry(prefix + "launcher_arm", "geometry." + prefix + "launcher_arm")
        actorComp.AddPlayerRenderController("controller.render." + prefix + "launcher_arm",
                                            "v.is_first_person && " + itemCondition)
        for aniName in STATES - {"re_transition"}:
            actorComp.AddPlayerAnimation(prefix + "1st_" + aniName,
                                         "animation." + DB.mod_name + "_launcher.1st_" + aniName)
            if aniName not in STATES_WITHOUT_3RD:
                actorComp.AddPlayerAnimation(prefix + "3rd_" + aniName,
                                             "animation." + DB.mod_name + "_launcher.3rd_" + aniName)

        actorComp.AddPlayerAnimationController(prefix + "arm_controller",
                                               "controller.animation." + DB.mod_name + "_launcher.general")
        actorComp.AddPlayerScriptAnimate(prefix + "arm_controller", itemCondition)
        actorComp.AddPlayerAnimation(prefix + "deployment", "animation." + DB.mod_name + ".deployment")
        actorComp.AddPlayerScriptAnimate(prefix + "deployment", itemCondition)
        actorComp.RebuildPlayerRender()

        if state:
            for _state in STATES:
                # 这里仍需要完善
                self.UpdateVar(_state, 1 if _state == state else 0, playerId)

    def GetEquipment(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item if item and item['newItemName'] in DRONE_LAUNCHER_TYPE else None

    @Listen
    def OnKeyPressInGame(self, event):
        if not self.functionsScreen:
            return
        if event['isDown'] != '1':
            return
        key = int(event['key'])
        if key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_Y:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "inspect"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_R:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "recover"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_C:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "control"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_V:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "explode"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_G:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "scan"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_X:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "mark"}})

    @Listen
    def LeftClickBeforeClientEvent(self, event):
        if clientApi.GetPlatform() != 0: return
        if not self.GetEquipment(): return
        event['cancel'] = True
        self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "shoot"}})

    @Listen
    def GetEntityByCoordEvent(self, event):
        if not self.functionsScreen.initialized: return
        if not self.GetEquipment(): return
        touchPos = clientApi.GetTouchPos()
        if self.nowState == "edit_button":
            self.functionsScreen.ClickOutButtonWhileEditing(touchPos)

    @Listen
    def GetEntityByCoordReleaseClientEvent(self, event):
        if not self.functionsScreen.initialized: return
        if not self.GetEquipment(): return
        self.functionsScreen.ClickUpDeploy()

    @Listen
    def PlayerTryDestroyBlockClientEvent(self, event):
        if self.GetEquipment():
            event['cancel'] = True

    @Listen
    def StartDestroyBlockClientEvent(self, event):
        if self.GetEquipment():
            event['cancel'] = True

    def BlinkVar(self, key):
        self.SyncVarToServer(0, key, 1)
        self.SyncVarToServer(0.05, key, 0)

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value, PID)  # 我发现这里的PID参数不能去除，否则会是-1，不知道为何
            self.CallServer("SyncVarToClients", PID, key, value)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value, PID)
            GC.AddTimer(delay, self.CallServer, "SyncVarToClients", PID, key, value)

    def SyncVarDictToServer(self, delay, varDict):
        if delay == 0:
            self.UpdateVarDict(varDict, PID)
            self.CallServer("SyncVarDictToClients", PID, varDict)
        else:
            GC.AddTimer(delay, self.UpdateVarDict, varDict, PID)
            GC.AddTimer(delay, self.CallServer, "SyncVarDictToClients", PID, varDict)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)

    def UpdateVarDict(self, varDict, playerId=PID):
        playerQC = CF.CreateQueryVariable(playerId)
        for key, value in varDict.items():
            playerQC.Set("query.mod." + DB.mod_name + "_" + key, value)

    @Listen
    def UnLoadClientAddonScriptsBefore(self, event):
        self.addonDisabled = True
        for frameData in self.frameDataDict.values():
            if isinstance(frameData, dict):
                if frameData:
                    self.DestroyEntity(frameData['frameId'])
            else:
                for singleFrameData in frameData:
                    singleFrameData["aniControlComp"].Stop()
                    self.DestroyEntity(singleFrameData['frameId'])

    def AppendFrame(self, entityId, frameType, duration, extraData=None):
        if self.addonDisabled: return
        if not extraData: extraData = {}
        if isinstance(self.frameDataDict[frameType], dict) and self.frameDataDict[frameType]:
            self.frameDataDict[frameType]['startTime'] = time.time()
            self.frameDataDict[frameType]['duration'] = duration
            self.frameDataDict[frameType]['entityId'] = entityId
            if isinstance(entityId, tuple):
                self.frameDataDict[frameType]["aniTransComp"].SetPos(
                    (entityId[0], entityId[1] + extraData.get("height", 0) * 0.5, entityId[2]))
            return
        frameId = self.CreateEngineSfxFromEditor("effects/" + DB.mod_name + "_" + frameType + ".json")
        frameAniTransComp = CF.CreateFrameAniTrans(frameId)
        if "scale" in extraData:
            frameAniTransComp.SetScale((extraData["scale"], extraData["scale"], extraData["scale"]))
        frameAniControlComp = CF.CreateFrameAniControl(frameId)
        if "color" in extraData:
            frameAniControlComp.SetMixColor((extraData['color'][0], extraData['color'][1], extraData['color'][2], 255))
        frameAniControlComp.Play()
        frameData = {"startTime": time.time(), "duration": duration, "entityId": entityId,
                     "height": extraData.get("height", 0),
                     "aniTransComp": frameAniTransComp, "aniControlComp": frameAniControlComp,
                     "frameId": frameId}
        if isinstance(self.frameDataDict[frameType], list):
            self.frameDataDict[frameType].append(frameData)
        elif isinstance(self.frameDataDict[frameType], dict):
            self.frameDataDict[frameType] = frameData

    @Listen("OnScriptTickClient")
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
        isBindEntity = not isinstance(frameData["entityId"], tuple)
        pos = CF.CreatePos(frameData["entityId"]).GetFootPos() if isBindEntity else \
            frameData["entityId"]
        if time.time() - frameData['startTime'] >= frameData["duration"] or (
                not pos and time.time() - frameData['startTime'] >= 0.5) or (not isBindEntity and not pos):
            # 若序列帧已过期则清理该序列帧，若绑定实体死亡则先隐藏，10秒后还是不对再清理
            if not pos and time.time() - frameData['startTime'] < 10:
                aniTransComp = frameData["aniTransComp"]
                aniTransComp.SetScale((0, 0, 0))
                return False
            aniControlComp = frameData["aniControlComp"]
            aniControlComp.Stop()
            self.DestroyEntity(frameData["frameId"])
            return True
        elif pos:
            # 若序列帧未过期，则更新位置
            aniTransComp = frameData["aniTransComp"]
            scale = 1
            aniTransComp.SetScale((scale, scale, scale))
            aniTransComp.SetPos((
                pos[0],
                pos[1] + frameData["height"],
                pos[2]
            ))
        return False

    def PlaySound(self, soundName):
        if not self.GetData("sound_enabled"):
            return
        AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)

    def PlayParticle(self, particleName, poses, varDict=None):
        if not self.GetData("particle_enabled"):
            return
        if isinstance(poses, tuple):
            poses = {poses}
        prefix = "orchiella:" + DB.mod_name + "_"
        for pos in poses:
            parId = ParC.Create(prefix + particleName, pos)
            if varDict:
                for key, value in varDict.items():
                    ParC.SetVariable(parId, "variable." + key, value)

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

    def CallServer(self, funcName, *args, **kwargs):
        self.NotifyToServer('ClientEvent', DB.CreateEventData(funcName, args, kwargs))

    def CallClient(self, playerId, funcName, *args, **kwargs):
        if playerId == PID: return getattr(self, funcName)(*args, **kwargs)
        self.CallServer('CallClient', playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.CallServer('CallAllClient', funcName, *args, **kwargs)

    def GetData(self, key, default=None):
        return self.settings.get(key, default)

    def SetData(self, key, value):
        self.settings[key] = value

    def LoadData(self, settings):
        self.settings = settings
