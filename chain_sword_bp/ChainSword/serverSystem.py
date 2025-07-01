# -*- coding: utf-8 -*-
import math
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ChainSword import mathUtil
from ChainSword.const import SPECIAL_ENTITIES
from ChainSword.dataManager import DataManager

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

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)
        GC.AddRepeatedTimer(0.05, self.ModTick)

    lightBlockPoses = {}

    def ModTick(self):
        for playerId in serverApi.GetPlayerList():
            if playerId in self.lightBlockPoses:
                CF.CreateBlockInfo(levelId).SetBlockNew(self.lightBlockPoses[playerId],
                                                        {"name": "minecraft:air", "aux": 0}, 0,
                                                        CF.CreateDimension(playerId).GetEntityDimensionId())
            if not self.IsEquipped(playerId):
                continue
            if self.revvingStateDict.get(playerId, False):
                if time.time() > self.revDamageCoolDownDict.get(playerId, 0):
                    isDamage = self.SectorAttack(playerId, DataManager.Get(playerId, "rev_damage"),
                                                 DataManager.Get(playerId, "rev_angle") / 2.0,
                                                 DataManager.Get(playerId, "rev_radius"),
                                                 0.3)
                    if isDamage:
                        self.TakeDurability(playerId, DataManager.Get(playerId, "rev_durability_consumption"))
                    self.revDamageCoolDownDict[playerId] = time.time() + DataManager.Get(playerId,
                                                                                         "rev_interval") / 1000.0
            if DataManager.Get(playerId, "light_enabled"):
                dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
                playerPos = Vector3(CF.CreatePos(playerId).GetFootPos())
                blockComp = CF.CreateBlockInfo(levelId)
                blockPos = (int(math.ceil(playerPos[0])), int(math.ceil(playerPos[1])), int(math.ceil(playerPos[2])))
                posFound = None
                for pos in mathUtil.GetSurroundingPoses(blockPos):
                    if blockComp.GetBlockNew(pos, dimId)['name'] == "minecraft:air":
                        posFound = pos
                        break
                if posFound:
                    blockComp.SetBlockNew(posFound, {"name": "minecraft:light_block", "aux": 7}, 0,
                                          dimId)
                    self.lightBlockPoses[playerId] = posFound
                else:
                    if playerId in self.lightBlockPoses:
                        del self.lightBlockPoses[playerId]

    @Listen
    def DelServerPlayerEvent(self, event):
        playerId = event['id']
        if playerId in self.lightBlockPoses:
            CF.CreateBlockInfo(levelId).SetBlockNew(self.lightBlockPoses[playerId],
                                                    {"name": "minecraft:air", "aux": 0}, 0,
                                                    CF.CreateDimension(playerId).GetEntityDimensionId())

    revvingStateDict = {}

    revDamageCoolDownDict = {}

    def UpdateRevState(self, playerId, state):
        self.revvingStateDict[playerId] = state

    @Listen
    def OnCarriedNewItemChangedServerEvent(self, event):
        self.CallClient(event['playerId'], "OnCarriedNewItemChangedClientEvent", event)

    def Attack(self, playerId):
        if not self.IsEquipped(playerId):
            return
        formatText = "rev_" if self.revvingStateDict.get(playerId, False) else ""
        isDamage = self.SectorAttack(playerId, DataManager.Get(playerId, "{}slash_damage".format(formatText)),
                                     DataManager.Get(playerId, "{}slash_angle".format(formatText)) / 2.0,
                                     DataManager.Get(playerId, "{}slash_radius".format(formatText)),
                                     DataManager.Get(playerId, "{}slash_knock".format(formatText)) / 2.0)
        if isDamage:
            self.TakeDurability(playerId,
                                DataManager.Get(playerId, "{}slash_durability_consumption".format(formatText)))

    attackDict = {}

    def SectorAttack(self, player_id, damage, semi_angle, radius, knock):
        entities = CF.CreateGame(player_id).GetEntitiesAround(player_id, int(math.ceil(radius)), {})
        player_pos = Vector3(CF.CreatePos(player_id).GetFootPos())
        if self.IsRidingHorse(player_id):
            player_pos - Vector3(0, 1, 0)
        isDamaged = False
        for entity_id in entities:
            if entity_id == player_id:
                continue
            if CF.CreateEngineType(entity_id).GetEngineTypeStr() in SPECIAL_ENTITIES:
                continue
            owner_id = CF.CreateTame(entity_id).GetOwnerId()
            if owner_id and owner_id == player_id:
                continue
            entity_pos = CF.CreatePos(entity_id).GetFootPos()
            relative_pos = Vector3(entity_pos) - player_pos
            if relative_pos.Length() > radius:
                continue
            relative_pos.Set(relative_pos.x, 0, relative_pos.z)
            forward_vector = Vector3(serverApi.GetDirFromRot(CF.CreateRot(player_id).GetRot()))
            forward_vector.Set(forward_vector.x, 0, forward_vector.z)
            angle = math.degrees(math.acos(Vector3.Dot(relative_pos.Normalized(), forward_vector.Normalized())))
            if angle > semi_angle:
                continue
            self.attackDict[entity_id] = (
                damage, ((relative_pos * knock) + Vector3(0, 0.2, 0)).ToTuple() if knock != 0 else (0, 0, 0))
            CF.CreatePlayer(player_id).PlayerAttackEntity(entity_id)
            del self.attackDict[entity_id]
            isDamaged = True
        return isDamaged

    def IsRidingHorse(self, player_id):
        entity_ridden = CF.CreateRide(player_id).GetEntityRider()
        return entity_ridden != "-1" and CF.CreateEngineType(
            entity_ridden).GetEngineTypeStr() == "minecraft:horse"

    @Listen
    def DamageEvent(self, event):
        entityId = event["entityId"]
        if entityId in self.attackDict:
            event['damage'] = self.attackDict[entityId][0]
            event['knock'] = False
            CF.CreateActorMotion(entityId).SetMotion(self.attackDict[entityId][1])

    def IsEquipped(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == 'orchiella:chain_sword'

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
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[重型链锯剑]")

    def SyncRebuild(self, playerId):
        otherPlayers = serverApi.GetPlayerList()
        otherPlayers.remove(playerId)
        blinkList = []
        if self.IsEquipped(playerId):
            blinkList.append("equip")
        for otherPlayerId in otherPlayers:
            self.CallClient(otherPlayerId, "Rebuild", playerId, blinkList)
            otherBlinkList = []
            if self.IsEquipped(otherPlayerId):
                otherBlinkList.append("equip")
            self.CallClient(playerId, "Rebuild", otherPlayerId, blinkList)

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
        if message == "链锯剑设置" or message == "1":
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
