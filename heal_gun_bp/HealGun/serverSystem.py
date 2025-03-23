# -*- coding: utf-8 -*-
import math
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from HealGun import mathUtil
from HealGun.const import BULLET_ENTITY_TYPE_DICT, SPECIAL_ENTITIES, BULLET_COLOR_DICT
from HealGun.dataManager import DataManager

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
    return CF.CreateExtraData(entityId).GetExtraData("heal_gun_" + keyName)


def RemoveEntityData(entityId, keyName):
    if GetEntityData(entityId, keyName):
        del CF.CreateExtraData(entityId).GetWholeExtraData()["heal_gun_" + keyName]


def SetEntityData(entityId, keyName, value):
    CF.CreateExtraData(entityId).SetExtraData("heal_gun_" + keyName, value)


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
        serverApi.AddEntityTickEventWhiteList('orchiella:heal_bomb_entity')
        serverApi.AddEntityTickEventWhiteList('orchiella:heal_bullet_entity')
        serverApi.AddEntityTickEventWhiteList('orchiella:slow_bullet_entity')
        serverApi.AddEntityTickEventWhiteList('orchiella:poison_bullet_entity')

        self.lockCache = {}
        GC.AddRepeatedTimer(0.25, self.SearchForLocking)

    def ReleaseSkill(self, playerId, skill):
        if not self.IsHoldingGun(playerId):
            return
        if skill == "self_heal":
            CF.CreateEffect(playerId).AddEffectToEntity("regeneration",
                                                        DataManager.Get(playerId, "func_self_heal_duration"),
                                                        DataManager.Get(playerId, "func_self_heal_amplifier"), False)
        elif skill == "launch_bomb":
            footPos = CF.CreatePos(playerId).GetFootPos()
            bombId = CF.CreateProjectile(levelId).CreateProjectileEntity(playerId, "orchiella:heal_bomb_entity", {
                "power": 2,
                'position': (footPos[0], footPos[1] + 1.4, footPos[2]),
                'direction': serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())})
            SetEntityData(bombId, "launcher", playerId)
            SetEntityData(bombId, "destroyTime", time.time() + DataManager.Get(playerId, "func_launch_bomb_duration"))

    def Shoot(self, playerId, bulletType):
        if not self.IsHoldingGun(playerId):
            return
        footPos = CF.CreatePos(playerId).GetFootPos()
        bulletId = CF.CreateProjectile(levelId).CreateProjectileEntity(playerId,
                                                                       "orchiella:{}_bullet_entity".format(bulletType),
                                                                       {
                                                                           "power": 3,
                                                                           'position': (
                                                                               footPos[0], footPos[1] + 1.4,
                                                                               footPos[2]),
                                                                           'direction': serverApi.GetDirFromRot(
                                                                               CF.CreateRot(playerId).GetRot())})
        SetEntityData(bulletId, "shooter", playerId)
        targetId = self.lockCache.get(playerId, None)
        if targetId:
            SetEntityData(bulletId, "targetId", targetId)

    @Listen
    def ProjectileDoHitEffectEvent(self, event):
        projectileId = event["id"]
        bulletInfo = BULLET_ENTITY_TYPE_DICT.get(CF.CreateEngineType(projectileId).GetEngineTypeStr(), None)
        if not bulletInfo:
            return
        playerId = GetEntityData(projectileId, "shooter")
        bulletType = bulletInfo['type']
        if event['hitTargetType'] == "ENTITY":
            entityId = event["targetId"]
            CF.CreateEffect(entityId).AddEffectToEntity(
                bulletInfo['effect'],
                DataManager.Get(playerId, "{}_bullet_duration".format(bulletType)),
                DataManager.Get(playerId, "{}_bullet_amplifier".format(bulletType)), True)
        color = BULLET_COLOR_DICT[bulletType]
        self.CallClient(playerId, "PlayParticle", "heal_gun:bullet_hit", (event["x"], event["y"], event["z"]),
                        {"color_r": color[0], "color_g": color[1], "color_b": color[2]})
        self.DestroyEntity(projectileId)

    @Listen
    def EntityTickServerEvent(self, event):
        entityId = event["entityId"]
        if CF.CreateEngineType(entityId).GetEngineTypeStr() in BULLET_ENTITY_TYPE_DICT:
            targetId = GetEntityData(entityId, 'targetId')
            if targetId:
                entityPos = mathUtil.GetEntityBodyLocation(targetId)
                if entityPos:
                    # entityPos是None与否作为生物是否存在或生存的判据
                    relevantVec = Vector3(mathUtil.GetEntityBodyLocation(targetId)) - Vector3(
                        CF.CreatePos(entityId).GetPos())
                    if relevantVec.Length() > 0.5:
                        motionComp = CF.CreateActorMotion(entityId)
                        originalMotionLength = Vector3(motionComp.GetMotion()).Length()
                        newMotion = (relevantVec.Normalized() * originalMotionLength).ToTuple()
                        motionComp.SetMotion(newMotion)
                    else:
                        RemoveEntityData(entityId, "lockedEntity")
        elif CF.CreateEngineType(entityId).GetEngineTypeStr() == "orchiella:heal_bomb_entity":
            if time.time() > GetEntityData(entityId, "destroyTime"):
                self.DestroyEntity(entityId)
                return
            launcherId = GetEntityData(entityId, "launcher")
            for nearEntityId in GC.GetEntitiesAround(entityId, DataManager.Get(launcherId, "func_launch_bomb_radius"),
                                                     {}):
                if CF.CreateEngineType(nearEntityId).GetEngineTypeStr() in SPECIAL_ENTITIES:
                    continue
                effectComp = CF.CreateEffect(nearEntityId)
                if effectComp.HasEffect("regeneration"):
                    continue
                effectComp.AddEffectToEntity(
                    "regeneration", 1,
                    DataManager.Get(launcherId, "func_launch_bomb_amplifier"), True)

    def SearchForLocking(self):
        for playerId in serverApi.GetPlayerList():
            if self.IsHoldingGun(playerId) and DataManager.Get(playerId, "func_switch_tracking_state") == "yes":
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
                                    CF.CreateCollisionBox(targetId).GetSize()[1])
                    continue
            if self.lockCache.get(playerId, None):
                del self.lockCache[playerId]

    def IsHoldingGun(self, playerId):
        comp = CF.CreateItem(playerId)
        mainHandItem = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        offHandItem = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.OFFHAND)
        return (mainHandItem and mainHandItem['newItemName'] == 'orchiella:heal_gun') or (
                offHandItem and offHandItem['newItemName'] == 'orchiella:heal_gun')

    def SendTip(self, playerId, message, color):
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[治疗枪]")

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
        if message == "治疗枪设置" or message == "医疗枪设置" or message == "1":
            args["cancel"] = True
            ownerId = DataManager.Get(None, "owner")
            if playerId == ownerId:
                self.CallClient(playerId, "!Display", True)
            else:
                permittedPlayers = DataManager.Get(None, "permitted_players")
                if playerId in permittedPlayers:
                    self.CallClient(playerId, "!Display", True)
                else:
                    GC.SetOneTipMessage(playerId, "§c你没有权限打开设置，如有需要请联系房主")

    def OpenPermissionPanel(self, playerId):
        self.CallClient(playerId, "!OpenPermissionPanel",
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
        self.CallClient(playerId, "!InitializeUI",
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
