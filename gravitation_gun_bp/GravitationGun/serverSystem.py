# -*- coding: utf-8 -*-
import math
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from GravitationGun import mathUtil
from GravitationGun.const import SPECIAL_ENTITIES, INCOMPLETE_ITEM, AIR_BLOCK
from GravitationGun.dataManager import DataManager

CF = serverApi.GetEngineCompFactory()
levelId = serverApi.GetLevelId()
GC = CF.CreateGame(levelId)
eventList = []


def Listen(funcOrStr=None, EN=serverApi.GetEngineNamespace(), ESN=serverApi.GetEngineSystemName(), priority=0):
    def binder(func):
        eventList.append((EN, ESN, funcOrStr if isinstance(funcOrStr, str) else func.__name__, func, priority))
        return func

    return binder(funcOrStr) if callable(funcOrStr) else binder


def GetEntityData(entityId, keyName):
    return CF.CreateExtraData(entityId).GetExtraData("gravitation_gun_" + keyName)


def RemoveEntityData(entityId, keyName):
    if GetEntityData(entityId, keyName):
        del CF.CreateExtraData(entityId).GetWholeExtraData()["gravitation_gun_" + keyName]


def SetEntityData(entityId, keyName, value):
    CF.CreateExtraData(entityId).SetExtraData("gravitation_gun_" + keyName, value)


class ServerSystem(serverApi.GetServerSystemCls()):
    def __init__(self, namespace, systemName):
        super(ServerSystem, self).__init__(namespace, systemName)
        for EN, ESN, eventName, callback, priority in eventList:
            self.ListenForEvent(EN, ESN, eventName, self, callback, priority)

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)
        serverApi.AddEntityTickEventWhiteList('orchiella:gravitation_trap_entity')

        self.lockCache = {}
        GC.AddRepeatedTimer(0.25, self.SearchForLocking)

    def ReleaseSkill(self, playerId, skill):
        handType = self.IsHoldingGun(playerId)
        if not handType:
            return
        if skill == "sector":
            if DataManager.Get(playerId, "func_switch_target_state") == "entity":
                for i in range(10):
                    GC.AddTimer(0.1 * i, self.MultipleAttracting, playerId,
                                self.SectorChoose(playerId, DataManager.Get(playerId, "func_sector_angle") / 2,
                                                  DataManager.Get(playerId, "func_sector_radius")))
            else:
                pass
        elif skill == "trap":
            footPos = CF.CreatePos(playerId).GetFootPos()
            bombId = CF.CreateProjectile(levelId).CreateProjectileEntity(playerId, "orchiella:gravitation_trap_entity",
                                                                         {
                                                                             "power": 1,
                                                                             'position': (
                                                                                 footPos[0], footPos[1] + 1.4,
                                                                                 footPos[2]),
                                                                             'direction': serverApi.GetDirFromRot(
                                                                                 CF.CreateRot(playerId).GetRot())})
            SetEntityData(bombId, "launcher", playerId)
            SetEntityData(bombId, "destroyTime", time.time() + DataManager.Get(playerId, "func_trap_duration"))
        elif skill == "frozen":
            entityId = self.lockCache[playerId]
            if not isinstance(entityId, str):
                return
            if CF.CreateEngineType(
                    entityId).GetEngineTypeStr() != "minecraft:player" and entityId not in self.frozenEntities:
                CF.CreateActorMotion(entityId).SetMotion((0, 0, 0))
                CF.CreateControlAi(entityId).SetBlockControlAi(False, True)
                self.frozenEntities.add(entityId)
                self.CallClients(GC.GetEntitiesAround(entityId, 60, {"any_of": [
                    {
                        "subject": "other",
                        "test": "is_family",
                        "value": "player"
                    }]}), 'UpdateEffectTime', entityId,
                                 DataManager.Get(playerId, 'func_frozen_duration'), 'frozen',
                                 0.5 * CF.CreateCollisionBox(entityId).GetSize()[1], 2.3)
                GC.AddTimer(DataManager.Get(playerId, "func_frozen_duration"), self.RemoveFrozenEntity, entityId)
        self.TakeDurability(playerId, handType,
                            DataManager.Get(playerId, "func_{}_durability_consumption".format(skill)))

    frozenEntities = set()

    def RemoveFrozenEntity(self, entityId):
        if entityId in self.frozenEntities:
            self.frozenEntities.remove(entityId)
            CF.CreateControlAi(entityId).SetBlockControlAi(True, False)

    def Use(self, playerId):
        handType = self.IsHoldingGun(playerId)
        if not handType:
            return
        if playerId not in self.lockCache:
            return
        if not self.lockCache[playerId]:
            return
        if DataManager.Get(playerId, "func_switch_target_state") == "entity" and isinstance(self.lockCache[playerId],
                                                                                            str):
            for i in range(10):
                GC.AddTimer(0.1 * i, self.Attracting, playerId, self.lockCache[playerId])
            self.TakeDurability(playerId, handType, DataManager.Get(playerId, "func_use_entity_durability_consumption"))
        elif DataManager.Get(playerId, "func_switch_target_state") == "block" and isinstance(self.lockCache[playerId],
                                                                                             tuple):
            pos, dimId = self.lockCache[playerId], CF.CreateDimension(playerId).GetEntityDimensionId()
            block = CF.CreateBlockInfo(levelId).GetBlockNew(pos, dimId)
            CF.CreateBlockInfo(levelId).SetBlockNew(pos, AIR_BLOCK, 0, dimId)
            itemId = self.CreateEngineItemEntity(
                dict(INCOMPLETE_ITEM, newItemName=block['name'], itemName=block['name'], newAuxValue=block['aux'],
                     auxValue=block['aux']), dimId, pos)
            for i in range(10):
                GC.AddTimer(0.1 * i, self.Attracting, playerId, itemId)
            self.TakeDurability(playerId, handType, DataManager.Get(playerId, "func_use_block_durability_consumption"))
        # if not DataManager.Get(playerId, "usage_informed"):
        #     DataManager.Set(playerId, "usage_informed", True)
        #     CF.CreateMsg(playerId).NotifyOneMessage(playerId,
        #                                             "§d[治疗枪模组] §f欢迎使用治疗枪模组！你可以在聊天框发送§e“治疗枪设置”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f。若有任何想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

    def Attracting(self, playerId, entityId, ensureGravitation=False):
        entityPos = CF.CreatePos(entityId).GetFootPos()
        if not entityPos:  # 说明实体死亡
            return
        playerPos = CF.CreatePos(playerId).GetFootPos()
        isGravitation = ensureGravitation or DataManager.Get(playerId, "func_switch_force_state") == "gravitation"
        if entityId in self.frozenEntities and isGravitation:
            CF.CreatePos(entityId).SetPos(playerPos)
        else:
            relativePos = Vector3(playerPos) - Vector3(entityPos)
            motion = (relativePos.Normalized() * (1.2 if relativePos.Length() < 15 else 2)
                      * (1 if isGravitation else -1)).ToTuple()
            if relativePos.Length() < 3:
                if relativePos.Length() < 1.5:
                    motion = (0, motion[1], 0)
            elif playerPos[1] > entityPos[1]:
                motion = (motion[0], motion[1] + 0.15, motion[2])
            if CF.CreateEngineType(entityId).GetEngineTypeStr() == "minecraft:player":
                CF.CreateActorMotion(entityId).SetPlayerMotion(motion)
            else:
                CF.CreateActorMotion(entityId).SetMotion(motion)

    def MultipleAttracting(self, playerId, entities):
        for entityId in entities:
            self.Attracting(playerId, entityId)

    def SectorChoose(self, playerId, includedAngle, radius):
        entities = GC.GetEntitiesAround(playerId, int(math.ceil(radius)), {})
        playerPos = Vector3(CF.CreatePos(playerId).GetFootPos())
        result = {}
        for entityId in entities:
            if entityId == playerId:
                continue
            if CF.CreateEngineType(entityId).GetEngineTypeStr() in SPECIAL_ENTITIES:
                continue
            ownerId = CF.CreateTame(entityId).GetOwnerId()
            if ownerId and ownerId == playerId:
                continue
            entityPos = CF.CreatePos(entityId).GetFootPos()
            relativePos = Vector3(entityPos) - playerPos
            if relativePos.Length() > radius:
                continue
            relativePos.Set(relativePos.x, 0, relativePos.z)
            forwardVec = Vector3(serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot()))
            forwardVec.Set(forwardVec.x, 0, forwardVec.z)
            angle = math.degrees(math.acos(Vector3.Dot(relativePos.Normalized(), forwardVec.Normalized())))
            if angle > includedAngle:
                continue
            result[entityId] = relativePos
        return result

    @Listen
    def EntityTickServerEvent(self, event):
        entityId = event["entityId"]
        if CF.CreateEngineType(entityId).GetEngineTypeStr() == "orchiella:gravitation_trap_entity":
            if time.time() > GetEntityData(entityId, "destroyTime"):
                self.DestroyEntity(entityId)
                return
            launcherId = GetEntityData(entityId, "launcher")
            for nearEntityId in GC.GetEntitiesAround(entityId, DataManager.Get(launcherId, "func_trap_radius"),
                                                     {}):
                if CF.CreateEngineType(nearEntityId).GetEngineTypeStr() in SPECIAL_ENTITIES:
                    continue
                elif CF.CreateEngineType(nearEntityId).GetEngineTypeStr() == "minecraft:player":
                    if not DataManager.Get(launcherId, "func_trap_affect_other_players"):
                        continue
                self.Attracting(entityId, nearEntityId, True)

    def SearchForLocking(self):
        for playerId in serverApi.GetPlayerList():
            if self.IsHoldingGun(playerId):
                if DataManager.Get(playerId, "func_switch_target_state") == "entity":
                    rot = CF.CreateRot(playerId).GetRot()
                    sightVec = Vector3(serverApi.GetDirFromRot(rot))
                    minAngle = -999
                    playerPos = CF.CreatePos(playerId).GetPos()
                    targetId = None
                    for entityId in GC.GetEntitiesAround(playerId, 60, {}):
                        if playerId == entityId:
                            continue
                        if CF.CreateEngineType(entityId).GetEngineTypeStr() in SPECIAL_ENTITIES:
                            continue
                        if not GC.CanSee(playerId, entityId, 100.0, True, 180.0, 180.0):
                            continue
                        entityPos = mathUtil.GetEntityBodyLocation(entityId)
                        relativeVec = Vector3(
                            entityPos[0] - playerPos[0], entityPos[1] - (playerPos[1]),
                            entityPos[2] - playerPos[2])
                        angle = math.acos(relativeVec * sightVec / (relativeVec.Length() * sightVec.Length()))
                        if angle > 0.4:
                            continue
                        if minAngle == -999 or angle < minAngle:
                            minAngle = angle
                            targetId = entityId
                    if targetId:
                        self.lockCache[playerId] = targetId
                        self.CallClient(playerId, "UpdateEffectTime", targetId, 0.5, "lock",
                                        0.5 * CF.CreateCollisionBox(targetId).GetSize()[1])
                        self.CallClient(playerId, "functionsScreen.UpdateLock", targetId)
                        continue
                elif DataManager.Get(playerId, "func_switch_target_state") == "block":
                    blocks = serverApi.getEntitiesOrBlockFromRay(CF.CreateDimension(playerId).GetEntityDimensionId(),
                                                                 CF.CreatePos(playerId).GetPos(),
                                                                 serverApi.GetDirFromRot(
                                                                     CF.CreateRot(playerId).GetRot()), 16, False,
                                                                 serverApi.GetMinecraftEnum().RayFilterType.OnlyBlocks)
                    if blocks:
                        self.lockCache[playerId] = blocks[0]["pos"]
                        self.CallClient(playerId, "functionsScreen.UpdateLock", blocks[0]["pos"])
                        continue
            if self.lockCache.get(playerId, None):
                del self.lockCache[playerId]
                self.CallClient(playerId, "functionsScreen.UpdateLock", None)

    @Listen
    def ProjectileDoHitEffectEvent(self, event):
        entityId = event['id']
        if CF.CreateEngineType(entityId).GetEngineTypeStr() == "orchiella:gravitation_trap_entity":
            if event['hitTargetType'] == "ENTITY":
                event['cancel'] = True
                return
            launcherId = GetEntityData(entityId, "launcher")
            self.CallClients(GC.GetEntitiesAround(entityId, 60, {"any_of": [
                {
                    "subject": "other",
                    "test": "is_family",
                    "value": "player"
                }]}), 'UpdateEffectTime', entityId,
                             DataManager.Get(launcherId, 'func_trap_duration'), 'attracting', 1.5)

    @Listen("DamageEvent")
    def EntityDamaged(self, event):
        entityId = event['entityId']
        if entityId in self.frozenEntities:
            event['damage'] = 0
            event['knock'] = False

    def IsHoldingGun(self, playerId):
        comp = CF.CreateItem(playerId)
        mainHandItem = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        offHandItem = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.OFFHAND)
        if mainHandItem and mainHandItem['newItemName'] == 'orchiella:gravitation_gun':
            return 1
        elif offHandItem and offHandItem['newItemName'] == 'orchiella:gravitation_gun':
            return 2
        return 0

    def TakeDurability(self, playerId, handType, value):
        if value == 0: return
        if GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        handEnum = serverApi.GetMinecraftEnum().ItemPosType.CARRIED if handType == 1 else serverApi.GetMinecraftEnum().ItemPosType.OFFHAND
        if itemComp.GetPlayerItem(handEnum)['durability'] > value:
            itemComp.SetItemDurability(handEnum, 0, itemComp.GetPlayerItem(handEnum)['durability'] - value)
        else:
            itemComp.SetEntityItem(handEnum, None)

    def SendTip(self, playerId, message, color):
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[引力枪]")

    def SyncVarToClients(self, playerId, key, value):
        self.CallClients(CF.CreatePlayer(playerId).GetRelevantPlayer([playerId]), "UpdateVar", key, value, playerId)

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
        if message == "引力枪设置" or message == "1":
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
                        DataManager.default_player_settings)

    def CallClient(self, playerId, funcName, *args, **kwargs):
        self.NotifyToClient(playerId, 'ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    def CallClients(self, players, funcName, *args, **kwargs):
        if not players: return
        for playerId in players:
            self.CallClient(playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.BroadcastToAllClient('ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    @Listen('ClientEvent', DB.ModName, 'ClientSystem')
    def OnGetClientEvent(self, args):
        getattr(self, args['funcName'])(*args.get('args', ()), **args.get('kwargs', {}))
