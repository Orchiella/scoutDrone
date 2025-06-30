# -*- coding: utf-8 -*-
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
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

    def ModTick(self):
        pass

    def ReleaseSkill(self, playerId, skill):
        if not self.IsEquipped(playerId):
            return

    revvingStateDict = {}

    def UpdateRevState(self, playerId, state):
        self.revvingStateDict[playerId] = state

    def Attack(self):
        pass

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
