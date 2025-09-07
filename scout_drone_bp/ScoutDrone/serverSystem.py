# -*- coding: utf-8 -*-
import math
import random
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ScoutDrone import mathUtil
from ScoutDrone.const import AIR_BLOCK
from ScoutDrone.dataManager import DataManager
from ScoutDrone.mathUtil import GetSurroundingPoses, GetDistance

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

        serverApi.AddEntityTickEventWhiteList("orchiella:scout_drone")

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)

    stateDict = {}

    def UpdateState(self, playerId, state):
        stateBefore = self.stateDict.get(playerId, "idle")
        self.stateDict[playerId] = state
        if state == "aim" and stateBefore != "aim":
            playerMissileId = None
            for missileId in self.missileDict:
                if self.missileDict[missileId] == playerId:
                    playerMissileId = missileId
            if not playerMissileId:
                self.SendTip(playerId, "进入瞄准状态，准备发射", "a")
            else:
                SetEntityData(playerMissileId, "shootPos", CF.CreatePos(playerId).GetFootPos())
                CF.CreateRide(playerId).SetRiderRideEntity(playerId, playerMissileId)
                self.CallClient(playerId, "SwitchControl", True)
                self.SendTip(playerId, "现在可以继续控制", "e")
        elif state != "aim" and stateBefore == "aim":
            effects = CF.CreateEffect(playerId).GetAllEffects()
            if effects:
                for effect in effects:
                    if effect["effectName"] == "night_vision" and effect["duration"] <= 11:
                        CF.CreateEffect(playerId).RemoveEffectFromEntity("night_vision")
            if playerId in self.missileDict.values():
                rideComp = CF.CreateRide(playerId)
                if rideComp.IsEntityRiding() and CF.CreateEngineType(
                        rideComp.GetEntityRider()).GetEngineTypeStr() == "orchiella:loitering_munition":
                    # 如果切出aim状态还在骑，说明是主动退出控制的
                    rideComp.StopEntityRiding()

    @Listen
    def DelServerPlayerEvent(self, event):
        playerId = event['id']
        if self.IsEquipped(playerId):
            self.UpdateState(playerId, "idle")

    @Listen
    def DelServerPlayerEvent(self, event):
        playerId = event['id']
        for missileId in self.missileDict:
            if self.missileDict[missileId] == playerId:
                self.DestroyEntity(missileId)
                self.missileDict.pop(missileId)
        self.UpdateState(playerId, "idle")

    controlDict = {}

    def Shoot(self, playerId):
        if not self.IsEquipped(playerId):
            return
        if playerId in self.missileDict.values():
            self.SendTip(playerId, "你同时只能控制一枚巡飞弹。也可以强制引爆上一枚", "c")
            return
        if (GC.GetPlayerGameType(playerId) != serverApi.GetMinecraftEnum().GameType.Creative and
                DataManager.Get(playerId, "item_consumed")
                and self.TakeItems(playerId, {"orchiella:loitering_munition": 1})):
            self.SendTip(playerId, "巡飞弹道具已用尽！请补充", "c")
            return
        spawnPos = CF.CreatePos(playerId).GetPos()
        missileId = self.CreateEngineEntityByTypeStr("orchiella:loitering_munition", spawnPos, (0, 0),
                                                     CF.CreateDimension(playerId).GetEntityDimensionId())
        GC.OpenMobHitBlockDetection(missileId, 0.00001)
        CF.CreatePlayer(missileId).OpenPlayerHitMobDetection()

        self.missileDict[missileId] = playerId
        rot = CF.CreateRot(playerId).GetRot()
        direction = serverApi.GetDirFromRot(rot)
        SetEntityData(missileId, "shooter", playerId)
        SetEntityData(missileId, "shootPos", CF.CreatePos(playerId).GetFootPos())
        SetEntityData(missileId, "shootRot", rot)
        SetEntityData(missileId, "isFlying",
                      CF.CreateFly(playerId).IsPlayerFlying() and CF.CreateGame(playerId).GetPlayerGameType(
                          playerId) == serverApi.GetMinecraftEnum().GameType.Creative)
        SetEntityData(missileId, "shootTime", time.time())
        SetEntityData(missileId, "checkSpeedTime", time.time() + 1)
        SetEntityData(missileId, "turnTime", time.time() + 0.5)
        SetEntityData(missileId, "glowTime", time.time() + 0.2)
        SetEntityData(missileId, "glowPos", None)
        SetEntityData(missileId, "velocity", DataManager.Get(playerId, "velocity") / 4.0)
        SetEntityData(missileId, "distance", 0)
        SetEntityData(missileId, "distanceRecordTime", time.time() + 0.5)
        SetEntityData(missileId, "distanceRecordPos", spawnPos)
        SetEntityData(missileId, "explode", False)
        SetEntityData(missileId, "cruise", direction)
        otherPlayers = serverApi.GetPlayerList()
        otherPlayers.remove(playerId)
        self.CallClients(otherPlayers, "AppendFrame", missileId, "alerting",
                         DataManager.Get(playerId, "max_time"),
                         0)
        GC.AddTimer(0.2, self.CallClients, otherPlayers, "BindParticle", "loitering_munition_plume", missileId)
        GC.AddTimer(0.2, self.CallClient, playerId, "InitMissileAnimation", missileId)
        self.CallClients(serverApi.GetPlayerList(), "PlaySound", "fire")

        if self.stateDict.get(playerId, "idle") == "aim":
            self.CallClient(playerId, "SwitchControl", True)
            rideComp = CF.CreateRide(missileId)
            rideComp.SetRiderRideEntity(playerId, missileId)
            if DataManager.Get(playerId, "joystick_enabled"):
                self.SendTip(playerId, "发射成功，拖动摇杆来实时调整巡飞弹方向", "a")
            else:
                self.SendTip(playerId, "发射成功，移动准星来实时调整巡飞弹方向", "a")
        else:
            yOffset = Vector3(0, 1.4, 0)
            planeOffset = Vector3(0, 0, 0)
            if direction[0] != 0 or direction[2] != 0:  # 向右偏移
                planeOffset = Vector3.Cross(Vector3(direction), yOffset)
                planeOffset = planeOffset.Normalized() * 0.15
            CF.CreatePos(missileId).SetFootPos((Vector3(CF.CreatePos(playerId).GetFootPos()) + Vector3(
                direction) * 0.5 + yOffset + planeOffset).ToTuple())
            CF.CreateRot(missileId).SetRot(rot)
            CF.CreateActorMotion(missileId).SetMotion(
                (Vector3(direction) * GetEntityData(missileId, "velocity")).ToTuple())
            self.SendTip(playerId, "开始自动巡航，打开瞄准镜进入控制模式", "a")

        SetEntityData(missileId, "y", CF.CreatePos(missileId).GetFootPos()[1])

        self.TakeDurability(playerId, DataManager.Get(playerId, "durability_consumption"))
        if not DataManager.Get(playerId, "usage_informed"):
            DataManager.Set(playerId, "usage_informed", True)
            CF.CreateMsg(playerId).NotifyOneMessage(playerId,
                                                    "§e[巡飞弹] §f欢迎使用本模组！你可以在聊天框发送§e“巡飞弹设置”§f或其拼音缩写§e“xfdsz”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f。若有任何其他想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

    missileDict = {}

    @Listen
    def EntityTickServerEvent(self, event):
        missileId = event["entityId"]
        if CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:loitering_munition":
            return
        shooterId = GetEntityData(missileId, "shooter")
        if time.time() - GetEntityData(missileId, "shootTime") > DataManager.Get(shooterId, "max_time"):
            self.Explode(missileId)
            self.SendTip(shooterId, "电量耗尽！自动启动爆炸程序", "c")
            return
        if time.time() > GetEntityData(missileId, "distanceRecordTime"):
            nowPos = CF.CreatePos(missileId).GetFootPos()
            SetEntityData(missileId, "distanceRecordTime", time.time() + 0.2)
            SetEntityData(missileId, "distance", GetEntityData(missileId, "distance") + (
                    Vector3(nowPos) - Vector3(GetEntityData(missileId, "distanceRecordPos"))).Length())
            SetEntityData(missileId, "distanceRecordPos", nowPos)
            if self.stateDict.get(shooterId, "idle") == "aim":
                self.CallClient(shooterId, "functionsScreen.UpdateLock", missileId,
                                1 - (time.time() - GetEntityData(missileId, "shootTime")) / float(
                                    DataManager.Get(shooterId, "max_time")),
                                "\n巡航速率:{}单位\n水平方向:{}\n实时坐标:({},{},{})\n记录信息:{}米 {}秒".format(
                                    round(Vector3(CF.CreateActorMotion(missileId).GetMotion()).Length(), 1),
                                    mathUtil.get_direction(CF.CreateActorMotion(missileId).GetMotion()),
                                    int(math.floor(nowPos[0])), int(math.floor(nowPos[1])), int(math.floor(nowPos[2])),
                                    round(GetEntityData(missileId, "distance"), 1),
                                    round(time.time() - GetEntityData(missileId, "shootTime"), 1)
                                ))
            else:
                self.CallClient(shooterId, "functionsScreen.UpdateLock", None)
        if time.time() > GetEntityData(missileId, "checkSpeedTime"):
            SetEntityData(missileId, "checkSpeedTime", time.time() + 0.05)
            motionCamp = CF.CreateActorMotion(missileId)
            print Vector3(motionCamp.GetMotion()).Length()
            if Vector3(motionCamp.GetMotion()).Length() < GetEntityData(missileId, "velocity") * 0.7:
                print "速度明显减弱，判定为撞击"
                if CF.CreateRide(shooterId).GetEntityRider() != missileId:
                    pos = CF.CreatePos(missileId).GetPos()
                    self.SendTip(shooterId, "自动巡航过程时击中坐标({},{},{})".format(
                        int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2]))
                    ), "a")
                SetEntityData(missileId, "explodePos", CF.CreatePos(missileId).GetFootPos())
                self.Explode(missileId)
                return
        if time.time() > GetEntityData(missileId, "turnTime"):
            # SetEntityData(missileId, "turnTime", time.time() + 1 / DataManager.Get(shooterId, "turn_rate"))
            SetEntityData(missileId, "turnTime", 0.2)
            motionCamp = CF.CreateActorMotion(missileId)
            velocity = GetEntityData(missileId, "velocity")
            if GetEntityData(missileId, "velocityUp"):
                velocity *= 1 + DataManager.Get(shooterId, "func_speed_up_percentage") / 100.0
            if CF.CreateRide(shooterId).GetEntityRider() == missileId:
                direction = serverApi.GetDirFromRot(CF.CreateRot(shooterId).GetRot())
                SetEntityData(missileId, "cruise", direction)
            else:
                direction = GetEntityData(missileId, "cruise")
            motionCamp.SetMotion((Vector3(direction).Normalized() * velocity).ToTuple())
            CF.CreateRot(missileId).SetRot(serverApi.GetRotFromDir(direction))
            SetEntityData(missileId, "y", CF.CreatePos(missileId).GetFootPos()[1])

    def SpeedUp(self, playerId):
        for missileId in self.missileDict:
            if self.missileDict[missileId] == playerId:
                if GetEntityData(missileId, "velocityUp"):
                    self.SendTip(playerId, "已达到最大巡航速度！", "c")
                else:
                    SetEntityData(missileId, "velocityUp", True)
                    self.SendTip(playerId, "加速！", "a")
                return
        self.SendTip(playerId, "没有正在飞行的巡飞弹", "c")

    @Listen
    def OnMobHitBlockServerEvent(self, event):
        missileId = event["entityId"]
        if CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:loitering_munition":
            return
        # shooterId = GetEntityData(missileId, "shooter")
        # if time.time() - GetEntityData(missileId, "shootTime") < 0.5:
        #     self.SendTip(shooterId, "建议在空旷地带发射", "c")
        # if event['blockId'] == "minecraft:light_block" or event['blockId'] == "minecraft:air":
        #     event['cancel'] = True
        #     return
        # if event['blockId'] in LIQUID_TYPE and DataManager.Get(shooterId, "waterproof_enabled"):
        #     event['cancel'] = True
        #     return
        # if CF.CreateRide(shooterId).GetEntityRider() != missileId:
        #     pos = CF.CreatePos(missileId).GetPos()
        #     self.SendTip(shooterId, "自动巡航过程时击中坐标({},{},{})".format(
        #         int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2]))
        #     ), "a")
        # SetEntityData(missileId, "explodePos", (event['posX'], event['posY'] + 1, event['posZ']))
        # self.Explode(missileId)

    @Listen
    def OnMobHitMobServerEvent(self, event):
        missileId = event["mobId"]
        if CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:loitering_munition":
            return
        hitMobs = event["hittedMobList"]
        if not hitMobs:
            return
        shooterId = GetEntityData(missileId, "shooter")
        if not DataManager.Get(shooterId, "hit_mob_enabled"):
            return
        if shooterId in hitMobs and DataManager.Get(shooterId, "protect_self"):
            return
        if CF.CreateRide(shooterId).GetEntityRider() != missileId:
            self.SendTip(shooterId, "自动巡航过程时击中了{}".format(self.GetEntityName(hitMobs[0])), "a")
        pos = CF.CreatePos(hitMobs[0]).GetPos()
        SetEntityData(missileId, "explodePos", pos)
        self.Explode(missileId)

    def GetEntityName(self, entityId):
        name = CF.CreateName(entityId).GetName()
        if name: return name
        return GC.GetChinese(
            "entity.{}.name".format(CF.CreateEngineType(entityId).GetEngineTypeStr().replace("minecraft:", ""))).encode(
            "utf-8")

    protection = {}

    @Listen("DamageEvent")
    def PlayerDamaged(self, event):
        entityId = event['entityId']
        entityType = CF.CreateEngineType(entityId).GetEngineTypeStr()
        if entityType == "minecraft:player":
            isProtected = False
            if time.time() < self.protection.get(entityId, 0):
                isProtected = True
            else:
                rideEntity = CF.CreateRide(entityId).GetEntityRider()
                for missileId in self.missileDict:
                    if self.missileDict[missileId] == entityId:
                        if rideEntity == missileId:
                            isProtected = True
                        break
            if isProtected:
                event['damage'] = 0
                event['knock'] = False
        elif entityType == "orchiella:loitering_munition":
            if event['cause'] != serverApi.GetMinecraftEnum().ActorDamageCause.EntityExplosion:
                event['damage'] = 0
                event['knock'] = False

    def ExplodeByPlayerId(self, playerId):
        for missileId in self.missileDict:
            if self.missileDict[missileId] == playerId:
                self.Explode(missileId)
                self.SendTip(playerId, "远程引爆成功", "a")
                return
        self.SendTip(playerId, "没有正在飞行的巡飞弹", "c")

    @Listen
    def EntityStopRidingEvent(self, event):
        missileId = event["rideId"]
        shooterId = GetEntityData(missileId, "shooter")
        if event["id"] != shooterId:
            return
        backPos = GetEntityData(missileId, "shootPos")
        backRot = GetEntityData(missileId, "shootRot")
        GC.AddTimer(0.1, CF.CreatePos(shooterId).SetFootPos, backPos)  # 不延时传送会很卡，不知道为什么
        GC.AddTimer(0.12, CF.CreateRot(shooterId).SetRot, backRot)
        isFlyingBefore = GetEntityData(missileId, "isFlying")
        if isFlyingBefore:
            GC.AddTimer(0.15, CF.CreateFly(shooterId).ChangePlayerFlyState, True, True)

        def SetOnFire():
            CF.CreateAttr(shooterId).SetEntityOnFire(0)

        GC.AddTimer(0.15, SetOnFire)
        if self.stateDict.get(shooterId, "idle") == "aim":
            self.CallClient(shooterId, "SwitchState", "idle")
        if not GetEntityData(missileId, "explode"):
            self.SendTip(shooterId, "可以重新进入开镜状态以控制", "e")
        else:
            pos = CF.CreatePos(missileId).GetPos()
            self.SendTip(shooterId, "击中坐标({},{},{})".format(
                int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2]))
            ), "a")
        self.CallClient(shooterId, "SwitchControl", False)

    def Explode(self, missileId):
        dimId = CF.CreateDimension(missileId).GetEntityDimensionId()
        if GetEntityData(missileId, "glowPos"):
            CF.CreateBlockInfo(levelId).SetBlockNew(GetEntityData(missileId, "glowPos"), AIR_BLOCK, 0, dimId)
        SetEntityData(missileId, "explode", True)
        pos = GetEntityData(missileId, "explodePos", CF.CreatePos(missileId).GetFootPos())
        self.CallRelevantClients(missileId, "PlaySound", "explode")
        shooterId = GetEntityData(missileId, "shooter")
        CF.CreateRide(shooterId).StopEntityRiding()
        self.protection[shooterId] = time.time() + 3
        pos = (int(math.floor(pos[0])), int(math.floor(pos[1])), int(math.floor(pos[2])))
        blockComp = CF.CreateBlockInfo(levelId)
        if blockComp.GetBlockNew(pos, dimId)['name'] != "minecraft:air":
            for otherPos in GetSurroundingPoses(pos):
                if blockComp.GetBlockNew(otherPos, dimId)['name'] == "minecraft:air":
                    pos = otherPos
                    break
        self.isExploding = (shooterId, pos)
        CF.CreateExplosion(levelId).CreateExplosion(pos,
                                                    DataManager.Get(shooterId, "explode_radius"),
                                                    DataManager.Get(shooterId, "explode_fire_enabled"),
                                                    DataManager.Get(shooterId, "explode_break_enabled"), shooterId,
                                                    shooterId)
        self.isExploding = None
        del self.missileDict[missileId]
        self.DestroyEntity(missileId)
        self.CallClient(shooterId, "functionsScreen.UpdateLock", None)

    isExploding = None

    @Listen
    def DamageEvent(self, event):
        if not self.isExploding or event['cause'] != serverApi.GetMinecraftEnum().ActorDamageCause.EntityExplosion:
            return
        entityId = event['entityId']
        if CF.CreateEngineType(entityId).GetEngineTypeStr() in {"minecraft:item", "minecraft:xp_orb"}:
            event['damage'] = 0
            return
        shooterId = self.isExploding[0]
        if entityId == shooterId and DataManager.Get(shooterId, "protect_self"):
            event['damage'] = 0
            return
        if DataManager.Get(shooterId, "fixed_damage_enabled"):
            explodeCenter = self.isExploding[1]
            explodeRadius = DataManager.Get(shooterId, "explode_radius")
            damage = DataManager.Get(shooterId, "fixed_damage")
            weakeningFactor = DataManager.Get(shooterId, "fixed_damage_weakening_factor")
            distance = max(0, GetDistance(explodeCenter, CF.CreatePos(entityId).GetFootPos()) - 1.4)
            damage = damage * (1 - distance / (explodeRadius + distance) * (weakeningFactor / 10.0))
            randomFactor = random.randint(0, DataManager.Get(shooterId, "fixed_damage_random_factor"))
            damage = damage * (1 + random.randint(-randomFactor, randomFactor) / 100.0)
            event['damage'] = int(damage)
        else:
            event["damage"] = int(
                event["damage"] * DataManager.Get(shooterId, 'explode_damage_percentage') / 100.0)

    def IsEquipped(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == 'orchiella:loitering_munition_launcher'

    def TakeDurability(self, playerId, value):
        if value == 0 or GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.CARRIED
        item = itemComp.GetPlayerItem(enum, 0)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 0, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 0)

    def TakeItems(self, player_id, recipe):
        item_comp = CF.CreateItem(player_id)
        slots_to_remove = {}
        count_dict = {item_needed: 0 for item_needed in recipe}
        for slot in range(36):
            item = item_comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slot)
            if not item:
                continue
            item_name = item["newItemName"].replace("minecraft:", "")
            if item["auxValue"] == 0:
                if item_name not in recipe:
                    continue
            else:
                if item_name + ":" + str(item["auxValue"]) not in recipe:
                    continue
                item_name = item_name + ":" + str(item["auxValue"])
            if count_dict[item_name] >= recipe[item_name]:
                continue
            item_count = item["count"]
            if count_dict[item_name] + item_count >= recipe[item_name]:
                count_to_remove = recipe[item_name] - count_dict[item_name]
            else:
                count_to_remove = item_count
            slots_to_remove[slot] = count_to_remove
            count_dict[item_name] += count_to_remove
        if all(count_dict[item_needed] >= recipe[item_needed] for item_needed in recipe):
            for slot, count in slots_to_remove.items():
                item_comp.SetInvItemNum(slot,
                                        item_comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                                                                slot)["count"] - count)
            return {}
        else:
            return count_dict

    def SendTip(self, playerId, message, color):
        if playerId not in serverApi.GetPlayerList(): return
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[巡飞弹]")

    def SyncRebuild(self, playerId):
        otherPlayers = serverApi.GetPlayerList()
        otherPlayers.remove(playerId)
        state = "idle"
        if self.IsEquipped(playerId):
            state = self.stateDict.get(playerId, "idle")
        for otherPlayerId in otherPlayers:
            self.CallClient(otherPlayerId, "Rebuild", playerId, state)
            otherState = "idle"
            if self.IsEquipped(otherPlayerId):
                otherState = self.stateDict.get(otherPlayerId, "idle")
            self.CallClient(playerId, "Rebuild", otherPlayerId, otherState)

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

    @Listen
    def ServerChatEvent(self, args):
        message = args["message"]
        playerId = args["playerId"]
        if message == "巡飞弹设置" or message == "xfdsz":
            args["cancel"] = True
            ownerId = DataManager.Get(None, "owner")
            if playerId == ownerId:
                self.CallClient(playerId, "settingsScreen.Display", True)
            else:
                permittedPlayers = DataManager.Get(None, "permitted_players")
                if playerId in permittedPlayers:
                    self.CallClient(playerId, "settingsScreen.Display", True)
                else:
                    GC.SetOneTipMessage(playerId, "§c你没有权限打开设置，如有需要请联系房主")

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
        if playerId == DataManager.Get(None, "owner") and DataManager.Get(None,
                                                                          "sync_owner_settings") and not DataManager.IsPrivateKey(
            key):
            for onlinePlayer in serverApi.GetPlayerList():
                if playerId == onlinePlayer: continue
                self.CallClient(onlinePlayer, "SetData", key, value)

    def LoadData(self, playerId):
        ownerId = DataManager.Get(None, "owner")
        self.CallClient(playerId, "LoadData",
                        {key: DataManager.cache[ownerId][key] if
                        not DataManager.IsPrivateKey(key) else DataManager.cache[playerId][key] for key in
                         DataManager.cache[ownerId]}
                        if playerId == ownerId or DataManager.Get(None, "sync_owner_settings") else
                        DataManager.cache[playerId])

    def LoadDataForOthers(self):
        ownerId = DataManager.Get(None, "owner")
        for onlinePlayer in serverApi.GetPlayerList():
            if onlinePlayer == ownerId: continue
            self.LoadData(onlinePlayer)

    def InitializeUI(self, playerId):
        self.CallClient(playerId, "settingsScreen.InitializeUI",
                        playerId == DataManager.Get(None, "owner"),
                        DataManager.default_player_settings)

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
