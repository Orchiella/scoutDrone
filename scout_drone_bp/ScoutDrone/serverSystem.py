# -*- coding: utf-8 -*-
import math
import random
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ScoutDrone import mathUtil, DeployHelper
from ScoutDrone.const import AIR_BLOCK, INCOMPLETE_ITEM_DICT, DRONE_TYPE, DRONE_LAUNCHER_TYPE
from ScoutDrone.dataManager import DataManager, DEFAULT_PLAYER_SETTINGS
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

    def SetMotion(self, playerId, direction):
        if playerId not in self.droneDict:
            return
        droneId = self.droneDict[playerId]['entityId']
        if CF.CreateRide(playerId).GetEntityRider() != droneId:
            return
        if direction:
            motion = (Vector3(direction).Normalized() * 0.6).ToTuple()
        else:
            direction = Vector3(CF.CreateActorMotion(droneId).GetMotion())
            motion = (direction * 0.96).ToTuple()
        CF.CreateActorMotion(droneId).SetMotion(motion)
        CF.CreateRot(droneId).SetRot(serverApi.GetRotFromDir(motion))

    droneDict = {}

    def Shoot(self, playerId):
        launcherItem = self.GetEquipment(playerId)
        if not launcherItem:
            return
        if playerId in self.droneDict:
            self.Recover(playerId)
        spawnPos = CF.CreatePos(playerId).GetPos()
        droneId = self.CreateEngineEntityByTypeStr("orchiella:scout_drone", spawnPos, CF.CreateRot(playerId).GetRot(),
                                                   CF.CreateDimension(playerId).GetEntityDimensionId())
        CF.CreateItem(playerId).SetInvItemNum(CF.CreateItem(playerId).GetSelectSlotId(), 0)
        self.droneDict[playerId] = {"entityId": droneId,
                                    "extraId": launcherItem['extraId'],
                                    "durability": launcherItem['durability']}
        print launcherItem
        self.CallClient(playerId, "SetDroneData", self.droneDict[playerId])
        self.CallClient(playerId, "functionsScreen.RefreshButtonVisibility")
        SetEntityData(droneId, "shootTime", time.time())
        self.SendTip(playerId, "无人机升空", "a")
        self.Control(playerId)

    def Recover(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        CF.CreateRide(playerId).StopEntityRiding()
        self.DestroyEntity(droneData['entityId'])
        del self.droneDict[playerId]
        self.CallClient(playerId, "SetDroneData", {})
        CF.CreateItem(levelId).SpawnItemToPlayerInv(
            dict(INCOMPLETE_ITEM_DICT, newItemName='orchiella:scout_drone_launcher',
                 itemName='orchiella:scout_drone_launcher',
                 durability=droneData['durability']), playerId)
        self.SendTip(playerId, "无人机已回收", "a")

    def Control(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        rideComp = CF.CreateRide(playerId)
        if rideComp.GetEntityRider() == droneData['entityId']:
            rideComp.StopEntityRiding()
        else:
            droneId = droneData['entityId']
            SetEntityData(droneId, "shootPos", CF.CreatePos(playerId).GetFootPos())
            SetEntityData(droneId, "shootRot", CF.CreateRot(playerId).GetRot())
            SetEntityData(droneId, "isFlying",
                          CF.CreateFly(playerId).IsPlayerFlying() and CF.CreateGame(playerId).GetPlayerGameType(
                              playerId) == serverApi.GetMinecraftEnum().GameType.Creative)
            rideComp.SetRiderRideEntity(playerId, droneData['entityId'])

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
        backPos = GetEntityData(droneId, "shootPos")
        if backPos:
            backRot = GetEntityData(droneId, "shootRot")
            GC.AddTimer(0.1, CF.CreatePos(shooterId).SetFootPos, backPos)  # 不延时传送会很卡，不知道为什么
            GC.AddTimer(0.12, CF.CreateRot(shooterId).SetRot, backRot)
            isFlyingBefore = GetEntityData(droneId, "isFlying")
            if isFlyingBefore:
                GC.AddTimer(0.15, CF.CreateFly(shooterId).ChangePlayerFlyState, True, True)
            GC.AddTimer(0.15, CF.CreateAttr(shooterId).SetEntityOnFire, 0)
        if event['entityIsBeingDestroyed']:
            del self.droneDict[shooterId]
            self.CallClient(shooterId, "SetDroneData", {})
            self.SendTip(shooterId, "无人机被击毁", "c")
        else:
            self.SendTip(shooterId, "退出控制状态", "a")
        self.CallClient(shooterId, "SwitchControl", False)
        CF.CreateActorMotion(droneId).SetMotion((0, 0, 0))

    def Function(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        loadType = DeployHelper.Get(droneData['extraId'], "load")
        print loadType

    def Scan(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        if CF.CreateRide(playerId).GetEntityRider() != droneData['entityId']:
            return
        num = 0
        for entityId in GC.GetEntitiesAround(playerId, 80, {}):
            if entityId == playerId:
                continue
            if CF.CreateRide(playerId).GetEntityRider() == entityId:
                continue
            boxSize = CF.CreateCollisionBox(entityId).GetSize()
            if boxSize[0] == 0.25 and boxSize[1] == 0.25:
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

    def Mark(self, playerId, targetId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        if CF.CreateRide(playerId).GetEntityRider() != droneData['entityId']:
            return
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

    def Explode(self, playerId):
        if playerId not in self.droneDict:
            return
        droneData = self.droneDict[playerId]
        droneId = droneData['entityId']
        pos = CF.CreatePos(droneId).GetPos()
        self.explosionData = {"shooter": playerId, "pos": pos}
        CF.CreateExplosion(levelId).CreateExplosion(pos,
                                                    DataManager.Get(playerId, "explode_radius"),
                                                    DataManager.Get(playerId, "explode_fire_enabled"),
                                                    DataManager.Get(playerId, "explode_break_enabled"), playerId,
                                                    playerId)
        self.explosionData = None
        droneData['durability'] = max(0,
                                      droneData['durability'] - DataManager.Get(playerId, "explode_durability_cost"))
        self.Recover(playerId)
        self.SendTip(playerId, "无人机已自爆", "a")

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
                event['damage'] = 0
                event['knock'] = False

    @Listen("DamageEvent")
    def DroneDamaged(self, event):
        droneId = event['entityId']
        if CF.CreateEngineType(droneId).GetEngineTypeStr() in DRONE_TYPE:
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

    def TakeDurability(self, playerId, value):
        if value == 0 or GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.CARRIED
        item = itemComp.GetPlayerItem(enum, 0)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 0, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 0)

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
