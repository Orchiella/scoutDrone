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
from ScoutDrone.ui.scoutDroneFunctions import DEPLOYMENT, GetAttributeValue
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
        self.frameDataDict = {"frame": [], "fake_player": {}}
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
        self.addonDisabled = False

    shaking = False
    stopShakingTime = 0
    stopShakingRoll = 0

    @Listen("OnScriptTickClient")
    def Move(self):
        if not self.isControlling:
            return
        # 获取摇杆输入
        inputVec = CF.CreateActorMotion(PID).GetInputVector()
        inputRight, inputUp = -inputVec[0], inputVec[1]
        cameraRot = CC.GetCameraRotation()
        if abs(inputRight) < 1e-5 and abs(inputUp) < 1e-5:
            idleShake = 2
            self.CallServer("SetMotion", PID, None)
            if self.GetData("shake"):
                if self.shaking:
                    roll = cameraRot[2] * 0.95
                    CC.SetCameraRotation(
                        (cameraRot[0], cameraRot[1], roll))
                    if abs(roll) < idleShake:
                        self.shaking = False
                        self.stopShakingTime = time.time()
                        self.stopShakingRoll = roll
                else:
                    if self.stopShakingRoll >= 0:
                        phi = math.pi - math.asin(self.stopShakingRoll / idleShake)
                    else:
                        phi = math.asin(self.stopShakingRoll / idleShake)
                    CC.SetCameraRotation((cameraRot[0], cameraRot[1], idleShake * math.sin(
                        3 * (time.time() - self.stopShakingTime - 1 / 30.0) + phi)))
            return
        amplifier = math.sqrt(inputUp ** 2 + inputRight ** 2)
        if self.GetData("shake"):
            CC.SetCameraRotation((cameraRot[0], cameraRot[1], min(12, max(-12, cameraRot[2] - inputRight * amplifier))))
            self.shaking = True
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
        self.CallServer("SetMotion", PID, outputTransformed, amplifier)

    @Listen
    def AddPlayerCreatedClientEvent(self, event):
        if event['playerId'] == PID: return
        self.CallServer("SyncRebuild", PID, event['playerId'])

    # 主手物品变化
    def OnCarriedNewItemChangedClientEvent(self, event):
        if not self.functionsScreen:
            return
        oldItem = event['oldItemDict']
        newItem = event['newItemDict']
        isOldDrone = oldItem and oldItem['newItemName'] in DRONE_LAUNCHER_TYPE
        isNewDrone = newItem and newItem['newItemName'] in DRONE_LAUNCHER_TYPE
        if isOldDrone and isNewDrone and oldItem['newItemName'] == newItem['newItemName'] and (
                DeployHelper.Get(oldItem['extraId'], 'uuid') == DeployHelper.Get(newItem['extraId'], 'uuid')):
            # 内部变化
            pass
        else:
            if isOldDrone:
                self.Equip(False)
            if isNewDrone:
                self.Equip(True, newItem['extraId'])

    # 物品栏切换，会快上述事件一步，提前收起装备，可能会多余，但一定不会出问题。。
    @Listen
    def OnItemSlotButtonClickedEvent(self, event):
        slotBefore = CF.CreateItem(PID).GetSlotId()
        slotNow = event['slotIndex']
        if slotBefore == slotNow or clientApi.GetTopUI() != "hud_screen":
            return
        itemComp = CF.CreateItem(PID)
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
            if not self.isControlling:
                clientApi.HideCrossHairGUI(False)
            PVC.SetToggleOption(clientApi.GetMinecraftEnum().OptionId.VIEW_BOBBING, self.initViewBobbing)
        GC.AddTimer(0.1, self.functionsScreen.RefreshButtonVisibility)

    @Listen
    def OnLocalPlayerActionClientEvent(self, event):
        if not self.GetEquipment():
            return
        if self.nowState == "inspect" or self.nowState == "shoot" or self.nowState == "charge" or self.nowState == "equip":
            return
        action = event['actionType']
        if action == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.SwitchState("run")
        elif action == clientApi.GetMinecraftEnum().PlayerActionType.StartSneaking:
            self.SwitchState("sneak")
        elif action == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting or action == clientApi.GetMinecraftEnum().PlayerActionType.StopSneaking:
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
            self.SyncVarToServer("transition", 0)
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

    def BackIdle(self, isIdleTransition=False, isRunTransition=True):
        if PC.isSprinting():
            self.SwitchState("run", isRunTransition)
        else:
            self.SwitchState("idle", isIdleTransition)

    def AddTask(self, timeNode, func, isTransition=False):
        if isinstance(timeNode, str):
            timeNode = self.animationCache["1st_" + timeNode]["length"]
        self.tasks.append(
            (time.time() + timeNode + (TRANSITION_DURATION if isTransition else 0), func))

    droneData = {}
    droneIdleMusicId = None

    def UpdateDroneData(self, droneData):
        if droneData is None:
            self.functionsScreen.droneInfoCtrl.SetVisible(False)
            self.droneData = {}
            if self.GetData("sound_enabled"):
                AC.StopCustomMusicById(self.droneIdleMusicId, 1)
                self.droneIdleMusicId = None
            return
        for key, value in droneData.items():
            self.droneData[key] = value
        if "entityId" in droneData:
            self.functionsScreen.controlPanelBatteryWarningCtrl.SetVisible(False)
            self.functionsScreen.droneInfoHealthCtrl.SetValue(1)
            self.functionsScreen.droneInfoBatteryCtrl.SetValue(1)
            self.functionsScreen.droneInfoNameCtrl.SetText("{}的侦查无人机".format(CF.CreateName(PID).GetName()))
            self.functionsScreen.droneInfoCtrl.SetVisible(True)
        if "health" in droneData:
            self.functionsScreen.droneInfoHealthCtrl.SetValue(
                droneData['health'] / CF.CreateAttr(self.droneData['entityId']).GetAttrMaxValue(
                    clientApi.GetMinecraftEnum().AttrType.HEALTH))
        if "battery" in droneData:
            barValue = droneData['battery'] / float(GetAttributeValue("battery", self.droneData['extraId']))
            self.functionsScreen.droneInfoBatteryCtrl.SetValue(barValue)
            self.functionsScreen.controlPanelBatteryWarningCtrl.SetVisible(barValue < 0.2)
        if "fakePlayerId" in droneData:
            if droneData['fakePlayerId']:
                self.functionsScreen.droneInfoModelCtrl.RenderEntity({
                    "entity_id": droneData['fakePlayerId'],
                    "scale": 0.3,
                    "init_rot_y": -30,
                    "init_rot_x": 10})
            else:
                self.functionsScreen.droneInfoModelCtrl.RenderEntity({
                    "entity_id": self.droneData['entityId'],
                    "scale": 1.0,
                    "init_rot_y": -30,
                    "init_rot_x": 10})
        if "sight" in droneData:
            PVC.SetPlayerFovScale(droneData['sight'])
        if "control_panel" in droneData:
            self.functionsScreen.controlPanelLeftCtrl.SetText(droneData['control_panel'][0])
            self.functionsScreen.controlPanelRightCtrl.SetText(droneData['control_panel'][1])

    def SetAlwaysShowName(self, entityId):
        CF.CreateName(entityId).SetAlwaysShowName(True)

    isControlling = False

    def SwitchControl(self, boolean):
        if self.droneData:
            self.isControlling = boolean
        if boolean:
            PVC.LockPerspective(0)
            clientApi.HideSlotBarGui(True)
            clientApi.HideExpGui(True)
            clientApi.HideHorseHealthGui(True)
            clientApi.HideHealthGui(True)
            clientApi.HideHungerGui(True)
            clientApi.HideArmorGui(True)
            clientApi.HideCrossHairGUI(True)
            if self.droneData:
                OC.SetCanAttack(False)
                OC.SetCanOpenInv(False)
                PPC.SetColorAdjustmentTint(self.GetData("green_intense") / 100.0, (0, 255, 0))
                self.UpdateVar("controlling", 1, self.droneData['entityId'])
                self.SyncVarToServer("controlling", 1)
                self.functionsScreen.controlPanelLeftCtrl.SetText("")
                self.functionsScreen.controlPanelRightCtrl.SetText("")
                if self.GetData("sound_enabled"):
                    if self.droneIdleMusicId:
                        AC.StopCustomMusicById(self.droneIdleMusicId, 0)
                        self.droneIdleMusicId = None

                    def play():
                        self.droneIdleMusicId = AC.PlayCustomMusic(
                            "orchiella:" + DB.mod_name + "_idle", (0, 0, 0), 1, 1, True, self.droneData['entityId'])

                    GC.AddTimer(0.2, play)
                if self.GetData("ui_enabled"):
                    self.functionsScreen.controlPanelCtrl.SetVisible(True)
                else:
                    self.functionsScreen.droneInfoCtrl.SetVisible(False)
            else:
                OC.SetCanAll(False)
                clientApi.HideMoveGui(True)
        else:
            PVC.LockPerspective(-1)
            clientApi.HideSlotBarGui(False)
            clientApi.HideExpGui(False)
            clientApi.HideHorseHealthGui(False)
            clientApi.HideHealthGui(False)
            clientApi.HideHungerGui(False)
            clientApi.HideArmorGui(False)
            clientApi.HideCrossHairGUI(False)
            if self.droneData:
                OC.SetCanAttack(True)
                OC.SetCanOpenInv(True)
                PPC.SetColorAdjustmentTint(0, (0, 255, 0))
                self.UpdateVar("controlling", 0, self.droneData['entityId'])
                self.SyncVarToServer("controlling", 0)
                self.functionsScreen.droneInfoCtrl.SetVisible(True)
                if self.GetData("ui_enabled"):
                    self.functionsScreen.controlPanelCtrl.SetVisible(False)
            else:
                OC.SetCanAll(True)
                clientApi.HideMoveGui(False)
        self.functionsScreen.RefreshButtonVisibility()
        CC.SetCameraRotation((0, 0, 0))
        PVC.SetPlayerFovScale(1)

    @Listen
    def ClientJumpButtonPressDownEvent(self, event):
        if self.isControlling:
            event['continueJump'] = False
            self.CallServer("SpeedUp", PID)

    def SwitchState(self, _state, isTransition=True):
        if self.nowState == _state:
            return False
        varDict = None
        if self.tasks:
            self.tasks = []
        if _state == "equip":
            self.AddTask(0.92, self.BackIdle)
            self.AddTask(0.92, self.CheckBatteryWhenEquipped)
            self.AddTask(0.15, lambda: self.PlaySound("equip"))
        elif _state == "inspect":
            self.AddTask(_state, self.BackIdle, isTransition)
            self.AddTask(5.16, lambda: self.PlaySound("shoot"))
        elif _state == "shoot":
            self.AddTask(_state, lambda: self.CallServer("Shoot", PID), isTransition)
            self.AddTask(0.16, lambda: self.PlaySound("shoot"))
        elif _state == "charge":
            self.PlaySound("charge")
            for i in range(10):
                self.AddTask(i * 1, lambda: self.CallServer("ConsumeToCharge", PID))
        elif _state == "edit_button":
            self.AddTask(_state, self.functionsScreen.StartEditing)
        elif _state == "deployed":
            for attr in ("rot", "pos"):
                for i, coord in enumerate(("x", "y", "z")):
                    QC.Set('query.mod.{}_deployed_{}_{}'.format(DB.mod_name, attr, coord),
                           ANIM_DATA['1st_deploy_{}'.format(self.functionsScreen.nowDrill)]['bones'][
                               'drone'][
                               'position' if attr == 'pos' else 'rotation']['0.0'][i])
            self.CallServer("Deploy", PID, self.functionsScreen.nowDrill, self.functionsScreen.index)
            self.AddTask(_state, lambda: self.BackIdle(True))
            varDict = GetTransitionMolangDict(QC, self.animationCache,
                                              "deploy_{}".format(self.functionsScreen.nowDrill),
                                              self.nowAnimationStartTime,
                                              "deploy_{}".format(self.functionsScreen.nowDrill))
        elif self.nowState == "edit_button":
            self.nowState = "transition"
            self.functionsScreen.EndEditing()
        elif self.nowState == "deployed":
            varDict = GetTransitionMolangDict(QC, self.animationCache,
                                              "deploy_{}".format(self.functionsScreen.nowDrill),
                                              self.nowAnimationStartTime, _state)

        if varDict is None:
            varDict = GetTransitionMolangDict(QC, self.animationCache, self.nowState,
                                              self.nowAnimationStartTime if isTransition else 0, _state)
        self.SyncVarDictToServer(varDict)
        for state in STATES:
            self.SyncVarToServer(state, 1 if state == _state else 0)
        if self.nowState == "transition":
            self.SyncVarToServer("re_transition", 1)
            GC.AddTimer(0.05, self.SyncVarToServer, "re_transition", 0)
        else:
            self.beforeState = self.nowState

        self.SyncVarToServer("transition", 1)
        self.nowAnimationStartTime = time.time()
        self.targetState = _state
        self.nowState = "transition"
        self.transitionFinishTime = self.nowAnimationStartTime + (
            TRANSITION_DURATION if isTransition else 0)
        return True

    def CheckBatteryWhenEquipped(self):
        launcherItem = self.GetEquipment()
        if launcherItem['durability'] <= 0:
            self.functionsScreen.SendTip("无耐久！请换一台", "c")
            return False
        batteryValue = DeployHelper.Get(launcherItem['extraId'], "batteryValue") if self.ShouldTakeBattery(
        ) else (GetAttributeValue("battery", launcherItem['extraId']))
        if batteryValue > 10:
            self.functionsScreen.SendTip("无人机已就绪", "a", 2, False)
        else:
            self.functionsScreen.SendTip("这台无人机几乎没电了！", "c", 2, False)

    def RefreshDeployment(self, content):
        varDict = {"deployment_" + deployType: DeployHelper.Get(content, deployType) for deployType in
                   DEPLOYMENT.keys()}
        self.SyncVarDictToServer(varDict)
        batteryValue = int(DeployHelper.Get(content, "batteryValue"))
        batteryColor = "f"
        if batteryValue < 10:
            batteryColor = "c"
        elif batteryValue < 20:
            batteryColor = "e"
        self.functionsScreen.chargeButtonLabelCtrl.SetText(
            "充电\n(§{}{}§f/{})".format(batteryColor, batteryValue,
                                        int(GetAttributeValue("battery", content))))

    recoverCd = 0

    def ClickButton(self, function):
        launcherItem = self.GetEquipment()
        if launcherItem and self.nowState == "equip" or self.nowState == "shoot":
            return False
        if function == "shoot":
            if self.droneData:
                self.functionsScreen.SendTip("请先收回上一架", "c")
                return False
            if launcherItem['durability'] <= 0:
                self.functionsScreen.SendTip("这台无人机已经没有耐久度了！", "c")
                return False
            batteryValue = DeployHelper.Get(launcherItem['extraId'], "batteryValue") if self.ShouldTakeBattery(
            ) else (GetAttributeValue("battery", launcherItem['extraId']))
            if batteryValue < 10:
                self.functionsScreen.SendTip("电量太少，请先补充！", "c")
                return False
            self.SwitchState("shoot", self.nowState != "idle")
            self.recoverCd = time.time() + ANIM_DATA['1st_shoot']['length'] + 1
            return True
        elif function == "recover":
            if time.time() < self.recoverCd:
                self.functionsScreen.SendTip("刚升空，不要回收这么快", "c")
                return False
            self.CallServer("Recover", PID)
            return True
        elif (function == "inspect" or function == "charge") and not self.isControlling:
            if self.nowState == function or self.targetState == function:
                self.BackIdle(True)
            else:
                self.SwitchState(function)
            return True
        elif function == "control":
            self.CallServer("Control", PID)
            return True
        elif function == "function" and self.isControlling:
            loadType = DeployHelper.Get(self.droneData['extraId'], "load")
            if loadType <= 0:
                return False
            extraData = {}
            if loadType == 1:
                targetId = self.SelectEntity(self.FilterHook)
                if not targetId:
                    self.functionsScreen.SendTip("准星需靠近一个有效的实体", "c")
                    return False
                extraData = {"targetId": targetId}
            self.CallServer("Function", PID, extraData)
            return True
        elif function == "scan" and self.isControlling:
            self.CallServer("Scan", PID)
            return True
        elif function == "mark" and self.isControlling:
            targetId = self.SelectEntity(self.FilterSpecialEntity)
            if not targetId:
                self.functionsScreen.SendTip("准星需靠近一个目标", "c")
                return False
            self.CallServer("Mark", PID, targetId)
            return True
        elif function == "explode":
            self.CallServer("Explode", PID)
            return True
        elif function == "sight":
            self.CallServer("Sight", PID)
            return True

    def ShouldTakeBattery(self):
        return not self.GetData("infinite_battery") and GC.GetPlayerGameType(
            PID) != clientApi.GetMinecraftEnum().GameType.Creative

    def FilterSpecialEntity(self, entityId):
        boxSize = CF.CreateCollisionBox(entityId).GetSize()
        return boxSize[0] != 0.25 and boxSize[1] != 0.25

    def FilterHook(self, entityId):
        return CF.CreateEngineType(entityId).GetEngineTypeStr() != "orchiella:scout_drone_fake_player"

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
            ("drop_yaw", 0, 0),
            ("controlling", 0, 0)}
                .union({("deployment_" + deploymentType, 0, 0) for deploymentType in DEPLOYMENT})):
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, varName), levelDefValue)
            QC.Set('query.mod.{}_{}'.format(DB.mod_name, varName), playerDefValue)
        self.Rebuild(PID)
        self.animationCache = ANIM_DATA

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
        actorComp.AddPlayerAnimation(prefix + "invisibility", "animation." + DB.mod_name + ".invisibility")
        actorComp.AddPlayerScriptAnimate(prefix + "invisibility", "q.mod." + prefix + "controlling")
        if CF.CreateEngineType(CF.CreateRide(playerId).GetEntityRider()).GetEngineTypeStr() in DRONE_TYPE:
            self.UpdateVar("controlling", 1, playerId)
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
        if clientApi.GetTopUI() != "hud_screen":
            return
        key = int(event['key'])
        if key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_Y:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "inspect"}})
        if key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_F:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "function"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_R:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "recover"}})
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "charge"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_C:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "control"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_G:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "explode"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_V:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "scan"}})
        elif key == clientApi.GetMinecraftEnum().KeyBoardType.KEY_X:
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "mark"}})

    @Listen
    def LeftClickBeforeClientEvent(self, event):
        if clientApi.GetPlatform() != 0: return
        if self.GetEquipment():
            event['cancel'] = True
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "shoot"}})

    @Listen
    def RightClickBeforeClientEvent(self, event):
        if clientApi.GetPlatform() != 0: return
        if self.isControlling:
            event['cancel'] = True
            self.functionsScreen.ClickButton({"AddTouchEventParams": {"func": "sight"}})

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
        if self.GetEquipment() or self.isControlling:
            event['cancel'] = True

    @Listen
    def StartDestroyBlockClientEvent(self, event):
        if self.GetEquipment() or self.isControlling:
            event['cancel'] = True

    def BlinkVar(self, key):
        self.SyncVarToServer(key, 1)
        GC.AddTimer(0.05, self.SyncVarToServer, key, 0)

    def SyncVarToServer(self, key, value):
        self.UpdateVar(key, value, PID)  # 我发现这里的PID参数不能去除，否则会是-1，不知道为何
        self.CallServer("SyncVarToClients", PID, key, value)

    def SyncVarDictToServer(self, varDict):
        self.UpdateVarDict(varDict, PID)
        self.CallServer("SyncVarDictToClients", PID, varDict)

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
                     "height": extraData.get("height", 0), "scale": extraData.get("scale", 1),
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
        if (frameData['duration'] >= 0 and time.time() - frameData['startTime'] >= frameData["duration"]) or (
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
            scale = frameData['scale']
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
        #AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)
        AC.PlayCustomUIMusic("orchiella:" + DB.mod_name + "_" + soundName, 1, 1, False)

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
        item = CF.CreateItem(PID).GetCarriedItem()
        if item and item['newItemName'] in DRONE_LAUNCHER_TYPE:
            self.Equip(True, item['extraId'])

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
