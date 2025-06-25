# -*- coding: utf-8 -*-
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ElectricBow.const import SPECIAL_ENTITIES
from ElectricBow.dataManager import DataManager

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

        serverApi.AddEntityTickEventWhiteList("orchiella:electric_arrow")

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)
        GC.AddRepeatedTimer(0.05, self.ModTick)

    hitEntities = []

    def ModTick(self):
        if not self.hitEntities:
            return
        entityToDel = []
        for hitEntity in self.hitEntities:
            shockNumber = GetEntityData(hitEntity, "shock_number")
            if shockNumber == 0 or not CF.CreatePos(hitEntity):
                entityToDel.append(hitEntity)
                continue
            shooter = GetEntityData(hitEntity, "shooter")
            if time.time() - GetEntityData(hitEntity, "shock_timestamp") < GetEntityData(hitEntity, "shock_interval"):
                continue
            damage = (GetEntityData(hitEntity, "shock_number")) * DataManager.Get(shooter, "arrow_shock_damage")
            CF.CreateHurt(hitEntity).Hurt(int(damage),
                                          serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack,
                                          None, None,
                                          False)
            SetEntityData(hitEntity, "shock_number", shockNumber - 1)
            SetEntityData(hitEntity, "shock_timestamp", time.time())
            if DataManager.Get(shooter, "arrow_shock_sound_enabled"):
                self.CallClient(shooter, "PlaySound", "hit")
        for hitEntity in entityToDel:
            self.hitEntities.remove(hitEntity)

    def ReleaseSkill(self, playerId, skill):
        if not self.IsEquipped(playerId):
            return
        if skill == "sensing":
            sensedEntities = set()
            for entityId in GC.GetEntitiesAround(playerId, 100, {}):
                if not GetEntityData(entityId, "shooter") or GetEntityData(entityId, "shooter") != playerId:
                    continue
                for nearEntity in GC.GetEntitiesAround(entityId, DataManager.Get(playerId, "func_sensing_radius"), {}):
                    if nearEntity == playerId:
                        continue
                    if CF.CreateEngineType(nearEntity).GetEngineTypeStr() in SPECIAL_ENTITIES:
                        continue
                    sensedEntities.add(nearEntity)
            for sensedEntity in sensedEntities:
                self.CallClient(playerId, "AppendFrame", sensedEntity, "eb_frame",
                                DataManager.Get(playerId, "func_sensing_duration"),
                                CF.CreateCollisionBox(sensedEntity).GetSize()[1],
                                CF.CreateCollisionBox(sensedEntity).GetSize()[1] * 0.6)
        elif skill == "release":
            i = 0
            for entityId in GC.GetEntitiesAround(playerId, 100, {}):
                shooter = GetEntityData(entityId, "shooter")
                if not shooter or GetEntityData(entityId, "shooter") != playerId:
                    continue
                if shooter != playerId:
                    continue
                shockNumber = GetEntityData(entityId, "shock_number")
                damage = (shockNumber * DataManager.Get(playerId, "arrow_shock_damage") *
                          (DataManager.Get(playerId, "func_release_damage_percentage")) / 100.0)
                for nearEntity in GC.GetEntitiesAround(entityId, DataManager.Get(playerId, "arrow_shock_radius"), {}):
                    if nearEntity == playerId:
                        if DataManager.Get(playerId, "arrow_shock_self_protection"):
                            continue
                    elif CF.CreateEngineType(nearEntity).GetEngineTypeStr() == "minecraft:player":
                        if DataManager.Get(playerId, "arrow_shock_other_protection"):
                            continue
                    CF.CreateHurt(nearEntity).Hurt(int(damage),
                                                   serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack,
                                                   None, None,
                                                   False)
                if CF.CreateEngineType(entityId) == "orchiella:electric_arrow":
                    self.DestroyEntity(entityId)
                else:
                    SetEntityData(entityId, "shock_number", 0)
                    self.CallClients(CF.CreatePlayer(entityId).GetRelevantPlayer(), "DelFrame", entityId,
                                     "eb_lightning")
                i += 1
            if i > 0:
                self.CallClient(playerId, "PlaySound", "release")

    def Shoot(self, playerId):
        if not self.IsEquipped(playerId):
            return
        footPos = CF.CreatePos(playerId).GetFootPos()
        direction = serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())
        yOffset = Vector3(0, 1.4, 0)
        planeOffset = Vector3(0, 0, 0)
        if direction[0] != 0 or direction[2] != 0:  # 向右偏移
            planeOffset = Vector3.Cross(Vector3(direction), yOffset)
            planeOffset = planeOffset.Normalized() * 0.15
        arrowId = CF.CreateProjectile(levelId).CreateProjectileEntity(playerId,
                                                                      "orchiella:electric_arrow",
                                                                      {
                                                                          "power": 10,
                                                                          'position': (Vector3(footPos) + Vector3(
                                                                              direction) * 0.5 + yOffset + planeOffset).ToTuple(),
                                                                          'direction': direction})
        SetEntityData(arrowId, "shooter", playerId)
        SetEntityData(arrowId, "hit", False)
        SetEntityData(arrowId, "shock_number", DataManager.Get(playerId, "arrow_shock_number"))
        SetEntityData(arrowId, "shock_interval", DataManager.Get(playerId, "arrow_shock_interval") / 1000.0)
        self.TakeDurability(playerId, 1)
        if not DataManager.Get(playerId, "usage_informed"):
            DataManager.Set(playerId, "usage_informed", True)
            CF.CreateMsg(playerId).NotifyOneMessage(playerId,
                                                    "§d[治疗枪模组] §f欢迎使用治疗枪模组！你可以在聊天框发送§e“治疗枪设置”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f。若有任何想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

    @Listen
    def EntityTickServerEvent(self, event):
        arrowId = event["entityId"]
        if CF.CreateEngineType(arrowId).GetEngineTypeStr() != "orchiella:electric_arrow":
            return
        if not GetEntityData(arrowId, "hit"):
            return
        shockNumber = GetEntityData(arrowId, "shock_number")
        if shockNumber <= 0:
            self.DestroyEntity(arrowId)
            return
        shooter = GetEntityData(arrowId, "shooter")
        if time.time() - GetEntityData(arrowId, "shock_timestamp") > GetEntityData(arrowId, "shock_interval"):
            SetEntityData(arrowId, "shock_number", shockNumber - 1)
            SetEntityData(arrowId, "shock_timestamp", time.time())
            i = 0
            for nearEntity in GC.GetEntitiesAround(arrowId, DataManager.Get(shooter, "arrow_shock_radius"), {}):
                if nearEntity == shooter:
                    if DataManager.Get(shooter, "arrow_shock_self_protection"):
                        continue
                elif CF.CreateEngineType(nearEntity).GetEngineTypeStr() == "minecraft:player":
                    if DataManager.Get(shooter, "arrow_shock_other_protection"):
                        continue
                success = CF.CreateHurt(nearEntity).Hurt(DataManager.Get(shooter, "arrow_shock_damage"),
                                                         serverApi.GetMinecraftEnum().ActorDamageCause.Projectile, None,
                                                         None,
                                                         False)
                if success:
                    i += 1
            if i > 0:
                if DataManager.Get(shooter, "arrow_shock_sound_enabled"):
                    self.CallClient(shooter, "PlaySound", "hit")

    @Listen
    def ProjectileDoHitEffectEvent(self, event):
        arrowId = event["id"]
        if CF.CreateEngineType(arrowId).GetEngineTypeStr() != "orchiella:electric_arrow":
            return
        if GetEntityData(arrowId, "hit"):
            return
        SetEntityData(arrowId, "hit", True)
        if event["hitTargetType"] == "ENTITY":
            targetId = event["targetId"]
            shooter = GetEntityData(arrowId, "shooter")
            if targetId == shooter:
                if DataManager.Get(shooter, "arrow_shock_self_protection"):
                    event['cancel'] = True
                    return
            elif CF.CreateEngineType(targetId).GetEngineTypeStr() == "minecraft:player":
                if DataManager.Get(shooter, "arrow_shock_other_protection"):
                    event['cancel'] = True
                    return
            elif CF.CreateEngineType(targetId).GetEngineTypeStr() in SPECIAL_ENTITIES:
                event['cancel'] = True
                return
            SetEntityData(targetId, "shock_timestamp", 0)  # 确保一打中就开始电
            SetEntityData(targetId, "shooter", shooter)
            SetEntityData(targetId, "shock_number", GetEntityData(arrowId, "shock_number"))
            SetEntityData(targetId, "shock_interval", GetEntityData(arrowId, "shock_interval"))
            self.CallClients(CF.CreatePlayer(arrowId).GetRelevantPlayer(), "AppendFrame", targetId,
                             "eb_lightning",
                             GetEntityData(arrowId, "shock_interval") * GetEntityData(arrowId, "shock_number"),
                             CF.CreateCollisionBox(targetId).GetSize()[1])
            self.hitEntities.append(targetId)
            self.DestroyEntity(arrowId)
        else:
            SetEntityData(arrowId, "shock_timestamp", time.time())
            GC.AddTimer(0.5, self.CallClients, CF.CreatePlayer(arrowId).GetRelevantPlayer(), "AppendFrame", arrowId,
                        "eb_lightning",
                        GetEntityData(arrowId, "shock_interval") * GetEntityData(arrowId, "shock_number"),
                        0.1)
            GC.AddTimer(0.5, self.CallClients, CF.CreatePlayer(arrowId).GetRelevantPlayer(), "BindParticle",
                        "electric_effect_emissive",
                        arrowId)

    def IsEquipped(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == 'orchiella:electric_bow'

    def TakeDurability(self, playerId, value):
        if GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.CARRIED
        item = itemComp.GetPlayerItem(enum, 0)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 0, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 0)

    def SendTip(self, playerId, message, color):
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[夜间战术头盔]")

    def SyncVarToClients(self, playerId, key, value):
        self.CallClients(CF.CreatePlayer(playerId).GetRelevantPlayer([playerId]), "UpdateVar", key, value, playerId)

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
        if message == "1":
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

    def CallRelevantClients(self, centerPlayerId, funcName, *args, **kwargs):
        for playerId in CF.CreatePlayer(centerPlayerId).GetRelevantPlayer():
            self.CallClient(playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.BroadcastToAllClient('ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    @Listen('ClientEvent', DB.ModName, 'ClientSystem')
    def OnGetClientEvent(self, args):
        getattr(self, args['funcName'])(*args.get('args', ()), **args.get('kwargs', {}))


def GetEntityData(entityId, key):
    return CF.CreateExtraData(entityId).GetExtraData(DB.mod_name + "_" + key)


def RemoveEntityData(entityId, key):
    if GetEntityData(entityId, key):
        del CF.CreateExtraData(entityId).GetWholeExtraData()[DB.mod_name + "_" + key]


def SetEntityData(entityId, key, value):
    CF.CreateExtraData(entityId).SetExtraData(DB.mod_name + "_" + key, value)
