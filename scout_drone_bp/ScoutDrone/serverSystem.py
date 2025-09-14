# -*- coding: utf-8 -*-
import math
import random
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ScoutDrone import mathUtil, DeployHelper
from ScoutDrone.const import AIR_BLOCK, INCOMPLETE_ITEM_DICT, DRONE_TYPE, DRONE_LAUNCHER_TYPE, ORIGINAL_SPEED, \
    CUSTOM_TIPS, ATTRIBUTE_TYPE
from ScoutDrone.dataManager import DataManager, DEFAULT_PLAYER_SETTINGS
from ScoutDrone.mathUtil import GetSurroundingPoses, GetDistance, GetDirection
from ScoutDrone.ui.scoutDroneFunctions import GetAttributeValue, DEPLOYMENT

CF = serverApi.GetEngineCompFactory()
levelId = serverApi.GetLevelId()
GC = CF.CreateGame(levelId)
eventList = []


def Listen(funcOrStr=None, EN=serverApi.GetEngineNamespace(), ESN=serverApi.GetEngineSystemName(), priority=0):
    def binder(func):
        eventList.append((EN, ESN, funcOrStr if isinstance(funcOrStr, str) else func.__name__, func, priority))
        return func

    return binder(funcOrStr) if callable(funcOrStr) else binder


class ServerSystem(serverApi.GetServerSystemCls()):
    def __init__(self, namespace, systemName):
        super(ServerSystem, self).__init__(namespace, systemName)
        for EN, ESN, eventName, callback, priority in eventList:
            self.ListenForEvent(EN, ESN, eventName, self, callback, priority)

        for droneType in DRONE_TYPE:
            serverApi.AddEntityTickEventWhiteList(droneType)
        serverApi.AddEntityTickEventWhiteList("orchiella:scout_drone_fake_player")
        serverApi.AddEntityTickEventWhiteList("orchiella:scout_drone_bait")

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)

        self.frameRGB = {
            serverApi.GetMinecraftEnum().EntityType.Monster: (0.8, 0.1, 0.1),  # 暗红色，表示敌意
            serverApi.GetMinecraftEnum().EntityType.Animal: (0, 1, 0),  # 动物绿色
            serverApi.GetMinecraftEnum().EntityType.Ambient: (0.6, 0.6, 0.6),  # 中性灰，环境生物
            serverApi.GetMinecraftEnum().EntityType.Projectile: (1.0, 0.6, 0.0),  # 橙色，高速危险
            serverApi.GetMinecraftEnum().EntityType.AbstractArrow: (1.0, 0.6, 0.0),  # 橙色，和抛射物一样
            serverApi.GetMinecraftEnum().EntityType.WaterAnimal: (0.2, 0.6, 0.9),  # 海蓝色，表示水生
            serverApi.GetMinecraftEnum().EntityType.VillagerBase: (0.6, 0.4, 0.2),  # 棕褐色，贴合村民穿着
            serverApi.GetMinecraftEnum().EntityType.Player: (0.2, 0.4, 1.0),  # 亮蓝色，高度辨识
        }

    motionReceptionTimeDict = {}

    def SetMotion(self, playerId, direction, amplifier=1):
        if playerId not in self.droneDict:
            return
        droneId = self.droneDict[playerId]['entityId']
        if CF.CreateRide(playerId).GetEntityRider() != droneId:
            return
        originalMotion = CF.CreateActorMotion(droneId).GetMotion()
        if direction:
            speed = ORIGINAL_SPEED * GetAttributeValue("speed", self.droneDict[playerId]['extraId'])
            if speed < Vector3(originalMotion).Length():
                return
            motion = (Vector3(direction).Normalized() * amplifier * speed).ToTuple()
        else:
            motion = (Vector3(originalMotion) * 0.96).ToTuple()
        CF.CreateActorMotion(droneId).SetMotion(motion)
        CF.CreateRot(droneId).SetRot(serverApi.GetRotFromDir(motion))

    droneDict = {}

    @Listen
    def EntityTickServerEvent(self, event):
        entityId = event["entityId"]
        if CF.CreateEngineType(entityId).GetEngineTypeStr() in DRONE_TYPE:
            shooterId = GetEntityData(entityId, "shooter")
            if shooterId not in self.droneDict:
                self.DestroyEntity(entityId)
                return
            if time.time() - GetEntityData(entityId, "batteryConsumeTime") >= 1:
                battery = GetEntityData(entityId, "battery")
                if battery <= 0:
                    self.Recover(shooterId)
                    self.SendTip(shooterId, "无人机电量耗尽", "c")
                    return
                self.CallClient(shooterId, "UpdateDroneData", {"battery": battery - 1})
                SetEntityData(entityId, "battery", battery - 1)
                SetEntityData(entityId, "batteryConsumeTime", time.time())
            if CF.CreateRide(shooterId).GetEntityRider() == entityId:
                CF.CreateEffect(shooterId).AddEffectToEntity("night_vision", 11, 0, False)
            lastPos = self.droneDict[shooterId]['pos']
            self.droneDict[shooterId]['pos'] = CF.CreatePos(entityId).GetFootPos()
            moveDist = GetDistance(lastPos, CF.CreatePos(entityId).GetFootPos()) + GetEntityData(entityId, "moveDist",
                                                                                                 0)
            SetEntityData(entityId, "moveDist", moveDist)
            motion = CF.CreateActorMotion(entityId).GetMotion()
            self.CallClient(shooterId, "UpdateDroneData", {"control_panel": (
                "当前速度：{}单位\n水平方向：{}".format(round(Vector3(motion).Length(), 1), GetDirection(motion)),
                "遥控距离：{}米\n飞行路程：{}米".format(
                    round(GetDistance(CF.CreatePos(entityId).GetFootPos(), GetEntityData(entityId, "shootPos")), 1),
                    round(moveDist, 1)))})
        elif CF.CreateEngineType(entityId).GetEngineTypeStr() == "orchiella:scout_drone_fake_player":
            shooterId = GetEntityData(entityId, "shooter")
            if shooterId not in self.droneDict:
                self.DestroyEntity(entityId)
                return
        elif CF.CreateEngineType(entityId).GetEngineTypeStr() == "orchiella:scout_drone_bait":
            if time.time() > GetEntityData(entityId, "dieTime"):
                self.DestroyEntity(entityId)
                return
            shooterId = GetEntityData(entityId, "shooter")
            for nearEntityId in GC.GetEntitiesAround(entityId, DataManager.Get(shooterId, "load3_radius"), {}):
                CF.CreateAction(nearEntityId).SetAttackTarget(entityId)

    def Deploy(self, playerId, key, value):
        equipment = self.GetEquipment(playerId)
        if not equipment:
            return
        self.UpdateDeploy(playerId, equipment, key, value)

    def Shoot(self, playerId):
        launcherItem = self.GetEquipment(playerId)
        if not launcherItem:
            return
        if playerId in self.droneDict:
            self.SendTip(playerId, "请先收回上一架", "c")
            return
        batteryValue = DeployHelper.Get(launcherItem['extraId'], "batteryValue") if self.ShouldTakeBattery(
            playerId) else (GetAttributeValue("battery", launcherItem['extraId']))
        if batteryValue < 10:
            self.SendTip(playerId, "电量太少，请先补充！", "c")
            return
        spawnPos = CF.CreatePos(playerId).GetFootPos()
        blockInfoComp = CF.CreateBlockInfo(levelId)
        dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
        direction = serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())
        directionLength = math.sqrt(direction[0] ** 2 + direction[2] ** 2)
        x, z = (direction[0] / directionLength, direction[2] / directionLength)
        for y in range(5, 1, -1):
            pos = (
                int(math.floor(spawnPos[0] + x)), int(math.floor(spawnPos[1] + y)),
                int(math.floor(spawnPos[2] + z)))
            if blockInfoComp.GetBlockNew(pos, dimId)['name'] == "minecraft:air":
                spawnPos = (spawnPos[0] + x, spawnPos[1] + y, spawnPos[2] + z)
                break
        droneId = self.CreateEngineEntityByTypeStr("orchiella:scout_drone", spawnPos, CF.CreateRot(playerId).GetRot(),
                                                   dimId)
        CF.CreateItem(playerId).SetInvItemNum(CF.CreateItem(playerId).GetSelectSlotId(), 0)
        droneData = {"entityId": droneId,
                     "extraId": launcherItem['extraId'],
                     "durability": launcherItem['durability'],
                     "initDurability": launcherItem['durability'],
                     "battery": batteryValue,
                     "pos": spawnPos}
        self.droneDict[playerId] = droneData
        battery = GetAttributeValue("battery", launcherItem['extraId'])
        self.CallClient(playerId, "UpdateDroneData", {
            "entityId": droneData['entityId'],
            "extraId": droneData['extraId']})
        self.CallClient(playerId, "functionsScreen.RefreshButtonVisibility")
        SetEntityData(droneId, "shooter", playerId)
        SetEntityData(droneId, "shootTime", time.time())
        SetEntityData(droneId, "battery", battery)
        SetEntityData(droneId, "batteryConsumeTime", time.time())
        CF.CreateName(droneId).SetName("侦查无人机")
        self.SendTip(playerId, "无人机升空", "a")
        self.Control(playerId)

    def ConsumeToCharge(self, playerId):
        takeNum = self.TakeItems(playerId, "minecraft:redstone", 1)
        if takeNum <= 0:
            self.CallClient(playerId, "BackIdle")
            self.SendTip(playerId, "需要红石粉", "c")
            return
        for j in range(5):
            GC.AddTimer((j + 1) * 0.2, self.Charge, playerId)

    def Charge(self, playerId):
        equipment = self.GetEquipment(playerId)
        if not equipment:
            return
        batteryValue = DeployHelper.Get(equipment['extraId'], "batteryValue")
        maxBatteryValue = GetAttributeValue("battery", equipment['extraId'])
        newBatteryValue = min(maxBatteryValue, batteryValue + 5)
        self.UpdateDeploy(playerId, equipment, "batteryValue", newBatteryValue)
        if newBatteryValue >= maxBatteryValue:
            self.CallClient(playerId, "BackIdle")
            self.SendTip(playerId, "电量已充满", "a")
            return
        self.SendTip(playerId, "正在充电{}".format("..." if time.time() % 1 > 0.5 else ".."), "7", 1)

    def Recover(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        CF.CreateRide(playerId).StopEntityRiding()
        droneId = droneData['entityId']
        self.DestroyEntity(droneId)
        del self.droneDict[playerId]
        self.CallClient(playerId, "UpdateDroneData", None)
        battery = GetEntityData(droneId, "battery")
        durability = droneData['durability'] if self.ShouldTakeDurability(playerId) else droneData['initDurability']
        extraId = DeployHelper.Set(droneData['extraId'], "batteryValue", battery)
        CF.CreateItem(levelId).SpawnItemToPlayerInv(
            dict(INCOMPLETE_ITEM_DICT, newItemName='orchiella:scout_drone_launcher',
                 itemName='orchiella:scout_drone_launcher',
                 durability=durability,
                 customTips=self.GetCustomTips({"extraId": extraId, "durability": durability}),
                 extraId=extraId), playerId)
        cost = droneData['initDurability'] - durability
        if cost != 0:
            realCost = int(cost * (ATTRIBUTE_TYPE['firm']['max'] - GetAttributeValue("firm", droneData['extraId'])))
            self.SendTip(playerId, "无人机已回收，使用了§6{}§a点耐久".format(realCost), "a")
            if cost > realCost:
                CF.CreateMsg(levelId).NotifyOneMessage(playerId,
                                                       "坚固属性为你节约了{}点耐久".format(cost - realCost))
        else:
            self.SendTip(playerId, "无人机已回收，未消耗耐久", "a")
        self.CallClient(playerId, "functionsScreen.RefreshButtonVisibility")

    switchControlCdDict = {}

    def Control(self, playerId):
        if playerId not in self.droneDict:
            return
        if time.time() < self.switchControlCdDict.get(playerId, 0):
            self.SendTip(playerId, "请不要频繁切换控制", "c")
            return
        self.switchControlCdDict[playerId] = time.time() + 2
        droneData = self.droneDict[playerId]
        rideComp = CF.CreateRide(playerId)
        if rideComp.GetEntityRider() == droneData['entityId']:
            rideComp.StopEntityRiding()
            self.CallClient(playerId, "PlaySound", "quit_control")
        else:
            droneId = droneData['entityId']
            SetEntityData(droneId, "shootPos", CF.CreatePos(playerId).GetFootPos())
            SetEntityData(droneId, "shootRot", CF.CreateRot(playerId).GetRot())
            isFlying = CF.CreateFly(playerId).IsPlayerFlying() and CF.CreateGame(playerId).GetPlayerGameType(
                playerId) == serverApi.GetMinecraftEnum().GameType.Creative
            SetEntityData(droneId, "isFlying", isFlying)
            fakePlayerId = self.CreateEngineEntityByTypeStr("orchiella:scout_drone_fake_player",
                                                            CF.CreatePos(playerId).GetFootPos(),
                                                            CF.CreateRot(playerId).GetRot(),
                                                            CF.CreateDimension(playerId).GetEntityDimensionId())
            self.droneDict[playerId]['fakePlayerId'] = fakePlayerId
            GC.AddTimer(0.1, self.CallClient, playerId, "UpdateDroneData", {"fakePlayerId": fakePlayerId})
            SetEntityData(fakePlayerId, "shooter", playerId)
            CF.CreateName(fakePlayerId).SetName("{}§a(正在操控无人机)".format(CF.CreateName(playerId).GetName()))
            GC.AddTimer(0.1, self.CallClients, serverApi.GetPlayerList(), "SetAlwaysShowName", fakePlayerId)
            self.CallClient(playerId, "AppendFrame", fakePlayerId, "fake_player", -1, {"height": 0.8, "scale": 0.8})
            CF.CreatePos(playerId).SetFootPos(droneData['pos'])
            rideComp.SetRiderRideEntity(playerId, droneData['entityId'])
            self.CallClient(playerId, "PlaySound", "enter_control")

    # 禁止交互，只允许通过按钮上下
    @Listen
    def PlayerInteractServerEvent(self, event):
        droneId = event['victimId']
        if CF.CreateEngineType(droneId).GetEngineTypeStr() in DRONE_TYPE:
            event['cancel'] = True

    @Listen
    def EntityStartRidingEvent(self, event):
        playerId = event["id"]
        droneId = event['rideId']
        if playerId not in self.droneDict or self.droneDict[playerId]['entityId'] != droneId:
            return
        controlRot = GetEntityData(droneId, "controlRot")
        if controlRot:
            CF.CreateRot(playerId).SetRot(controlRot)
        self.CallClient(playerId, "SwitchControl", True)
        self.SendTip(playerId, "进入控制状态", "a")

    @Listen
    def EntityStopRidingEvent(self, event):
        droneId = event["rideId"]
        shooterId = None
        for playerId, droneData in self.droneDict.items():
            if droneData['entityId'] == droneId:
                shooterId = playerId
                break
        if event["id"] != shooterId:
            return
        SetEntityData(droneId, "controlRot", CF.CreateRot(shooterId).GetRot())
        fakePlayerId = self.droneDict[shooterId]['fakePlayerId']
        if GC.IsEntityAlive(fakePlayerId):
            backPos = CF.CreatePos(fakePlayerId).GetFootPos()
        else:
            backPos = GetEntityData(droneId, "shootPos")
        backRot = GetEntityData(droneId, "shootRot")
        self.DestroyEntity(fakePlayerId)
        self.CallClient(shooterId, "UpdateDroneData", {"fakePlayerId": None})
        GC.AddTimer(0.1, CF.CreatePos(shooterId).SetFootPos, backPos)  # 不延时传送会很卡，不知道为什么
        GC.AddTimer(0.12, CF.CreateRot(shooterId).SetRot, backRot)
        isFlyingBefore = GetEntityData(droneId, "isFlying")
        if isFlyingBefore:
            GC.AddTimer(0.15, CF.CreateFly(shooterId).ChangePlayerFlyState, True, True)
        GC.AddTimer(0.15, CF.CreateAttr(shooterId).SetEntityOnFire, 0)
        if event['entityIsBeingDestroyed']:
            del self.droneDict[shooterId]
            self.CallClient(shooterId, "UpdateDroneData", None)
            self.SendTip(shooterId, "无人机被击毁", "c")
        else:
            self.SendTip(shooterId, "退出控制状态", "7")
        self.CallClient(shooterId, "SwitchControl", False)

        effects = CF.CreateEffect(shooterId).GetAllEffects()
        if effects:
            for effect in effects:
                if effect["effectName"] == "night_vision" and effect["duration"] <= 11:
                    CF.CreateEffect(shooterId).RemoveEffectFromEntity("night_vision")
        CF.CreateActorMotion(droneId).SetMotion((0, 0, 0))

    def Function(self, playerId, extraData):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        loadType = DeployHelper.Get(droneData['extraId'], "load")
        if loadType == 1:
            cost = DataManager.Get(playerId, "load1_cost")
            nowBattery = GetEntityData(droneId, "battery")
            if nowBattery < cost:
                self.SendTip(playerId, "电量值不足以使用引力钩爪", "c")
                return
            SetEntityData(droneId, "battery", nowBattery - cost)
            targetId = extraData['targetId']
            playerPos = CF.CreatePos(playerId).GetFootPos()
            targetPos = CF.CreatePos(targetId).GetPos()
            motion = ((Vector3(playerPos) + Vector3(0, 0.5, 0) - Vector3(targetPos)).Normalized() * 1.3).ToTuple()
            if CF.CreateEngineType(targetId).GetEngineTypeStr() == "minecraft:player":
                CF.CreateActorMotion(targetId).SetPlayerMotion(motion)
            else:
                CF.CreateActorMotion(targetId).SetMotion(motion)
            self.SendTip(playerId, "引力生成！", "a")
        elif loadType == 3:
            cost = DataManager.Get(playerId, "load1_cost")
            nowBattery = GetEntityData(droneData['entityId'], "battery")
            if nowBattery < cost:
                self.SendTip(playerId, "电量值不足以释放诱饵", "c")
                return
            SetEntityData(droneId, "battery", nowBattery - cost)
            baitId = self.CreateEngineEntityByTypeStr("orchiella:scout_drone_bait", CF.CreatePos(playerId).GetFootPos(),
                                                      (0, 0),
                                                      CF.CreateDimension(playerId).GetEntityDimensionId())
            SetEntityData(baitId, "dieTime", time.time() + DataManager.Get(playerId, "load3_duration"))
            SetEntityData(baitId, "shooter", playerId)
            CF.CreateName(baitId).SetName("诱饵")
            self.SendTip(playerId, "诱饵释放！", "a")

    def Scan(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        if CF.CreateRide(playerId).GetEntityRider() != droneId:
            return
        cost = DataManager.Get(playerId, "scan_cost")
        nowBattery = GetEntityData(droneId, "battery")
        if nowBattery < cost:
            self.SendTip(playerId, "电量值不足以使用扫描技能", "c")
            return
        SetEntityData(droneId, "battery", nowBattery - cost)
        self.CallClient(playerId, "UpdateDroneData", {"battery": nowBattery - cost})
        num = 0
        for entityId in GC.GetEntitiesAround(playerId, 80, {}):
            if entityId == playerId:
                continue
            if CF.CreateRide(playerId).GetEntityRider() == entityId:
                continue
            boxSize = CF.CreateCollisionBox(entityId).GetSize()
            if boxSize[0] == 0.25 and boxSize[1] == 0.25:
                continue
            if CF.CreateEngineType(
                    entityId).GetEngineTypeStr() == "orchiella:scout_drone_fake_player" and GetEntityData(entityId,
                                                                                                          "shooter") == playerId:
                continue
            color = (1, 1, 1)
            for entityType, frameColor in self.frameRGB.items():
                if CF.CreateEngineType(entityId).GetEngineType() & entityType == entityType:
                    color = frameColor
                    break
            self.CallClient(playerId, "AppendFrame", entityId, "frame", 10,
                            {"height": CF.CreateCollisionBox(entityId).GetSize()[1] / 2.0,
                             "scale": CF.CreateCollisionBox(entityId).GetSize()[1] * 0.6,
                             "color": color})
            num += 1
        if num > 0:
            self.SendTip(playerId, "扫描并标记了§e{}§f个目标".format(num), "f", 3)
        else:
            self.SendTip(playerId, "没有扫描到目标", "e", 2)
        self.CallClient(playerId, "PlaySound", "scan")

    def Mark(self, playerId, targetId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        if CF.CreateRide(playerId).GetEntityRider() != droneId:
            return
        cost = DataManager.Get(playerId, "mark_cost")
        nowBattery = GetEntityData(droneId, "battery")
        if nowBattery < cost:
            self.SendTip(playerId, "电量值不足以使用标记功能", "c")
            return
        SetEntityData(droneId, "battery", nowBattery - cost)
        self.CallClient(playerId, "UpdateDroneData", {"battery": nowBattery - cost})
        color = (1, 1, 1)
        for entityType, frameColor in self.frameRGB.items():
            if CF.CreateEngineType(targetId).GetEngineType() & entityType == entityType:
                color = frameColor
                break
        self.CallClient(playerId, "AppendFrame", targetId, "frame", 30,
                        {"height": CF.CreateCollisionBox(targetId).GetSize()[1] / 2.0,
                         "scale": CF.CreateCollisionBox(targetId).GetSize()[1] * 0.6,
                         "color": color})
        self.SendTip(playerId, "标记了§e{}§f({}米)".format(self.GetEntityName(targetId),
                                                           round(GetDistance(CF.CreatePos(playerId).GetPos(),
                                                                             CF.CreatePos(targetId).GetPos()))), "f", 1)
        self.CallClient(playerId, "PlaySound", "mark")

    def Explode(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        cost = DataManager.Get(playerId, "explode_cost")
        if droneData['durability'] < cost and self.ShouldTakeDurability(playerId):
            self.SendTip(playerId, "耐久值不足以使用自爆技能", "c")
            return
        self.droneDict[playerId]['durability'] -= cost
        pos = CF.CreatePos(droneId).GetPos()
        if playerId in self.lightBlockPosesDict:
            lightBlockPoses = self.lightBlockPosesDict[playerId]
            blockInfoComp = CF.CreateBlockInfo(levelId)
            dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
            for lightBlockPos in lightBlockPoses:
                blockInfoComp.SetBlockNew(lightBlockPos, AIR_BLOCK, 0, dimId)
            del self.lightBlockPosesDict[playerId]
        self.explosionData = {"shooter": playerId, "pos": pos}
        CF.CreateExplosion(levelId).CreateExplosion(pos,
                                                    DataManager.Get(playerId, "explode_radius"),
                                                    DataManager.Get(playerId, "explode_fire"),
                                                    DataManager.Get(playerId, "explode_break"), playerId,
                                                    playerId)
        self.explosionData = None
        self.Recover(playerId)
        self.SendTip(playerId, "无人机自爆成功", "a")

    def Sight(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        if droneData.get('sight', 1) == 1:
            sightDef = DEPLOYMENT['sight']['deployment'][DeployHelper.Get(droneData['extraId'], "sight")]
            sightValue = sightDef['value']
            sightName = sightDef['name']
            self.SendTip(playerId, "放大器：{}".format(sightName), "f", 1)
        else:
            sightValue = 1
        self.droneDict[playerId]['sight'] = sightValue
        self.CallClient(playerId, "UpdateDroneData", {"sight": sightValue})
        self.CallClient(playerId, "PlaySound", "aim")

    def SpeedUp(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        cost = DataManager.Get(playerId, "speed_up_cost")
        nowBattery = GetEntityData(droneId, "battery")
        if nowBattery < cost:
            self.SendTip(playerId, "电量值不足以使用加速功能", "c")
            return
        SetEntityData(droneId, "battery", nowBattery - cost)
        self.CallClient(playerId, "UpdateDroneData", {"battery": nowBattery - cost})
        pitch = CF.CreateRot(playerId).GetRot()[0]
        if pitch < -45:
            self.SendTip(playerId, "仰角过高，请先放平", "c")
            return
        self.droneDict[playerId]['durability'] -= cost
        droneId = droneData['entityId']
        speed = (ORIGINAL_SPEED * GetAttributeValue("speed", self.droneDict[playerId]['extraId'])) * DataManager.Get(
            playerId, "speed_up_amplifier")
        CF.CreateActorMotion(droneId).SetMotion(
            (Vector3(serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())).Normalized() * speed).ToTuple())
        self.SendTip(playerId, "加速！", "a")
        self.CallClient(playerId, "PlaySound", "speed_up{}".format(random.randint(0, 1)))

    lightBlockPosesDict = {}

    @Listen
    def DelServerPlayerEvent(self, event):
        playerId = event['id']
        if playerId in self.lightBlockPosesDict:
            lightBlockPoses = self.lightBlockPosesDict[playerId]
            blockInfoComp = CF.CreateBlockInfo(levelId)
            dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
            for lightBlockPos in lightBlockPoses:
                blockInfoComp.SetBlockNew(lightBlockPos, AIR_BLOCK, 0, dimId)
            del self.lightBlockPosesDict[playerId]

    @Listen("OnScriptTickServer")
    def Torch(self):
        for playerId in serverApi.GetPlayerList():
            dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
            blockInfoComp = CF.CreateBlockInfo(levelId)
            if playerId in self.lightBlockPosesDict:
                lightBlockPoses = self.lightBlockPosesDict[playerId]
                for lightBlockPos in lightBlockPoses:
                    blockInfoComp.SetBlockNew(lightBlockPos, AIR_BLOCK, 0, dimId)
                del self.lightBlockPosesDict[playerId]
            if playerId not in self.droneDict:
                continue
            droneData = self.droneDict[playerId]
            if CF.CreateRide(playerId).GetEntityRider() != droneData['entityId']:
                continue
            if DeployHelper.Get(self.droneDict[playerId]['extraId'], "load") != 2:
                continue
            playerPos = Vector3(CF.CreatePos(playerId).GetPos())
            playerDir = Vector3(serverApi.GetDirFromRot(CF.CreateRot(droneData['entityId']).GetRot()))
            lightPoses = []
            for i in range(30):
                blockPos = (playerPos + playerDir * i).ToTuple()
                blockPos = (int(math.floor(blockPos[0])), int(math.floor(blockPos[1])), int(math.floor(blockPos[2])))
                if blockInfoComp.GetBlockNew(blockPos, dimId)['name'] == "minecraft:air":
                    lightPoses.append(blockPos)
            maxBrightness = 15
            lightPosNum = len(lightPoses)
            for i, lightPos in enumerate(lightPoses):
                if i == lightPosNum - 1:
                    brightness = maxBrightness
                else:
                    brightness = int(i / float(lightPosNum) * maxBrightness * 0.3)
                blockInfoComp.SetBlockNew(lightPos, {"name": "light_block", 'aux': brightness}, 0,
                                          dimId)
            self.lightBlockPosesDict[playerId] = lightPoses

    explosionData = None

    @Listen("DamageEvent")
    def DamagedByExplosion(self, event):
        if not self.explosionData or event['cause'] != serverApi.GetMinecraftEnum().ActorDamageCause.EntityExplosion:
            return
        entityId = event['entityId']
        if CF.CreateEngineType(entityId).GetEngineTypeStr() in {"minecraft:item", "minecraft:xp_orb"}:
            event['damage'] = 0
            return
        shooterId = self.explosionData['shooter']
        event["damage"] = int(
            event["damage"] * DataManager.Get(shooterId, 'explode_damage_percentage') / 100.0)

    @Listen("DamageEvent")
    def PlayerDamaged(self, event):
        playerId = event['entityId']
        if CF.CreateEngineType(playerId).GetEngineTypeStr() == "minecraft:player":
            droneId = CF.CreateRide(playerId).GetEntityRider()
            if playerId in self.droneDict and droneId == self.droneDict[playerId]['entityId']:
                CF.CreateHurt(droneId).Hurt(event['damage'], event['cause'], event['srcId'], None)
                event['damage'] = 0
                event['knock'] = False

    @Listen("DamageEvent")
    def FakePlayerDamaged(self, event):
        fakePlayerId = event['entityId']
        if CF.CreateEngineType(fakePlayerId).GetEngineTypeStr() == "orchiella:scout_drone_fake_player":
            shooterId = GetEntityData(fakePlayerId, "shooter")
            if GC.GetPlayerGameType(shooterId) == serverApi.GetMinecraftEnum().GameType.Creative:
                event['damage'] = 0
                event['knock'] = False
                return
            self.Control(shooterId)
            self.SendTip(shooterId, "本体受到伤害，控制中断", "c")
            CF.CreateHurt(shooterId).Hurt(event['damage'], event['cause'], event['srcId'], None)
            event['damage'] = 1

    @Listen("DamageEvent")
    def DroneDamaged(self, event):
        droneId = event['entityId']
        if CF.CreateEngineType(droneId).GetEngineTypeStr() in DRONE_TYPE:
            shooterId = GetEntityData(droneId, "shooter")
            damage = event['damage']
            realDamage = int(damage * (2 - GetAttributeValue("defense", self.droneDict[shooterId]['extraId'])))
            event['damage'] = realDamage
            event['knock'] = False
            self.CallClient(shooterId, "UpdateDroneData", {
                "health": CF.CreateAttr(droneId).GetAttrValue(
                    serverApi.GetMinecraftEnum().AttrType.HEALTH) - realDamage})

    @Listen("MobDieEvent")
    def DroneDie(self, event):
        droneId = event['id']
        if CF.CreateEngineType(droneId).GetEngineTypeStr() in DRONE_TYPE:
            shooterId = GetEntityData(droneId, "shooter")
            self.Recover(shooterId)
            self.SendTip(shooterId, "无人机被击落，已自动回收", "c")

    @Listen("DamageEvent")
    def BaitDamaged(self, event):
        baitId = event['entityId']
        if CF.CreateEngineType(baitId).GetEngineTypeStr() != "orchiella:scout_drone_bait":
            return
        event['knock'] = False

    @Listen
    def EntityRemoveEvent(self, event):
        self.Recover(event['id'])

    def GetEntityName(self, entityId):
        name = CF.CreateName(entityId).GetName()
        if name: return name
        return GC.GetChinese(
            "entity.{}.name".format(CF.CreateEngineType(entityId).GetEngineTypeStr().replace("minecraft:", ""))).encode(
            "utf-8")

    def GetEquipment(self, playerId):
        item = CF.CreateItem(playerId).GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item if item and item['newItemName'] in DRONE_LAUNCHER_TYPE else None

    def GetCustomTips(self, equipment):
        extraId = equipment['extraId']
        return CUSTOM_TIPS.format(
            DEPLOYMENT["rotor"]['deployment'][DeployHelper.Get(extraId, "rotor")]['name'],
            DEPLOYMENT["tail"]['deployment'][DeployHelper.Get(extraId, "tail")]['name'],
            DEPLOYMENT["load"]['deployment'][DeployHelper.Get(extraId, "load")]['name'],
            DEPLOYMENT["sight"]['deployment'][DeployHelper.Get(extraId, "sight")]['name'],
            DEPLOYMENT["battery"]['deployment'][DeployHelper.Get(extraId, "battery")]['name'],
            int(DeployHelper.Get(extraId, "batteryValue")),
            int(GetAttributeValue("battery", extraId)),
            equipment['durability'],
            1000
        )

    def UpdateDeploy(self, playerId, equipment, key, value):
        newExtraId = DeployHelper.Set(equipment['extraId'], key, value)
        CF.CreateItem(playerId).ChangePlayerItemTipsAndExtraId(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                                                               CF.CreateItem(playerId).GetSelectSlotId(),
                                                               self.GetCustomTips(equipment),
                                                               newExtraId)
        self.CallClient(playerId, "RefreshDeployment", newExtraId)

    def ShouldTakeDurability(self, playerId):
        return not DataManager.Get(playerId, "infinite_durability") and GC.GetPlayerGameType(
            playerId) != serverApi.GetMinecraftEnum().GameType.Creative

    def ShouldTakeBattery(self, playerId):
        return not DataManager.Get(playerId, "infinite_battery") and GC.GetPlayerGameType(
            playerId) != serverApi.GetMinecraftEnum().GameType.Creative

    def TakeDurability(self, playerId, value):
        if value == 0 or GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.CARRIED
        item = itemComp.GetPlayerItem(enum, 0)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 0, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 0)

    def TakeItems(self, playerId, itemName, maxNum):
        if GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative or DataManager.Get(playerId,
                                                                                                               "charge_no_consume"):
            return maxNum
        itemComp = CF.CreateItem(playerId)
        takenNum = 0
        slotsToTake = {}
        for slot in range(36):
            if takenNum >= maxNum:
                break
            item = itemComp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slot)
            if not item or item['newItemName'] != itemName:
                continue
            item_count = item["count"]
            if takenNum + item_count >= maxNum:
                countToTake = maxNum - takenNum
            else:
                countToTake = item_count
            takenNum += countToTake
            slotsToTake[slot] = countToTake
        for slot, count in slotsToTake.items():
            itemComp.SetInvItemNum(slot,
                                   itemComp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                                                          slot)["count"] - count)
        return takenNum

    def SyncRebuild(self, playerId):
        otherPlayers = serverApi.GetPlayerList()
        otherPlayers.remove(playerId)
        for otherPlayerId in otherPlayers:
            self.CallClient(otherPlayerId, "Rebuild", playerId)
            self.CallClient(playerId, "Rebuild", otherPlayerId)

    def SyncVarToClients(self, playerId, key, value, exceptSelf=True):
        self.CallClients(CF.CreatePlayer(playerId).GetRelevantPlayer([playerId] if exceptSelf else None), "UpdateVar",
                         key, value, playerId)

    def SyncVarDictToClients(self, playerId, varDict):
        self.CallClients(CF.CreatePlayer(playerId).GetRelevantPlayer([playerId]), "UpdateVarDict", varDict, playerId)

    def SyncSoundToClients(self, playerId, soundName):
        self.CallClients(CF.CreatePlayer(playerId).GetRelevantPlayer([playerId]), "PlaySound", soundName)

    @Listen
    def AddServerPlayerEvent(self, args):
        playerId = args["id"]
        DataManager.Check(playerId)
        if not DataManager.Get(None, "owner"):
            DataManager.Set(None, "owner", playerId)
        permittedPlayers = DataManager.Get(None, "permitted_players")
        if DataManager.Get(None, "auto_gain_permission") and playerId not in permittedPlayers:
            permittedPlayers.append(playerId)
            DataManager.Set(None, "permitted_players", permittedPlayers)

    def SendTip(self, playerId, tip, color, duration=2.0, cover=True):
        self.CallClient(playerId, "functionsScreen.SendTip", tip, color, duration, cover)

    def TryToOpenSettings(self, playerId):
        ownerId = DataManager.Get(None, "owner")
        if playerId == ownerId:
            self.CallClient(playerId, "settingsScreen.Display", True)
        else:
            permittedPlayers = DataManager.Get(None, "permitted_players")
            if playerId in permittedPlayers:
                self.CallClient(playerId, "settingsScreen.Display", True)
            else:
                GC.SetOneTipMessage(playerId, "§c你没有权限打开设置，如有需要请联系房主")

    @Listen
    def ServerChatEvent(self, args):
        message = args["message"]
        playerId = args["playerId"]
        if message == "侦查无人机设置":
            args["cancel"] = True
            self.TryToOpenSettings(playerId)

    def OpenPermissionPanel(self, playerId):
        self.CallClient(playerId, "settingsScreen.OpenPermissionPanel",
                        {onlinePlayerId: CF.CreateName(onlinePlayerId).GetName() for onlinePlayerId in
                         serverApi.GetPlayerList() if onlinePlayerId != playerId},
                        DataManager.Get(None, "permitted_players"),
                        DataManager.Get(None, "auto_gain_permission"),
                        DataManager.Get(None, "sync_owner_settings"))
        # 这里就获取名字是因为在客户端层面未必获取得到

    def SetData(self, playerId, key, value):
        DataManager.Set(playerId, key, value)
        if playerId == DataManager.Get(None, "owner") and DataManager.Get(None, "sync_owner_settings"):
            ownerSettings = DataManager.cache[playerId]
            for onlinePlayer in serverApi.GetPlayerList():
                if playerId == onlinePlayer: continue
                self.CallClient(onlinePlayer, "LoadData", ownerSettings)

    def LoadData(self, playerId):
        ownerId = DataManager.Get(None, "owner")
        self.CallClient(playerId, "LoadData",
                        DataManager.cache[ownerId]
                        if playerId == ownerId or DataManager.Get(None, "sync_owner_settings") else
                        DataManager.cache[playerId])

    def LoadDataForOthers(self):
        ownerId = DataManager.Get(None, "owner")
        ownerSettings = DataManager.cache[ownerId]
        isSyncOwnerSettings = DataManager.Get(None, "sync_owner_settings")
        for onlinePlayer in serverApi.GetPlayerList():
            if onlinePlayer == ownerId: continue
            self.CallClient(onlinePlayer, "LoadData",
                            ownerSettings if isSyncOwnerSettings else DataManager.cache[onlinePlayer])

    def InitializeUI(self, playerId):
        self.CallClient(playerId, "settingsScreen.InitializeUI",
                        playerId == DataManager.Get(None, "owner"),
                        DEFAULT_PLAYER_SETTINGS)

    def CallClient(self, playerId, funcName, *args, **kwargs):
        self.NotifyToClient(playerId, 'ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    def CallClients(self, players, funcName, *args, **kwargs):
        if not players: return
        for playerId in players:
            self.CallClient(playerId, funcName, *args, **kwargs)

    def CallRelevantClients(self, entityId, funcName, *args, **kwargs):
        players = CF.CreatePlayer(entityId).GetRelevantPlayer()
        if not players: return
        for playerId in players:
            self.CallClient(playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.BroadcastToAllClient('ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    @Listen('ClientEvent', DB.ModName, 'ClientSystem')
    def OnGetClientEvent(self, args):
        getattr(self, args['funcName'])(*args.get('args', ()), **args.get('kwargs', {}))


def GetEntityData(entityId, key, default=None):
    result = CF.CreateExtraData(entityId).GetExtraData(DB.mod_name + "_" + key)
    return result if result is not None else default


def RemoveEntityData(entityId, key):
    if GetEntityData(entityId, key):
        del CF.CreateExtraData(entityId).GetWholeExtraData()[DB.mod_name + "_" + key]


def SetEntityData(entityId, key, value):
    CF.CreateExtraData(entityId).SetExtraData(DB.mod_name + "_" + key, value)
