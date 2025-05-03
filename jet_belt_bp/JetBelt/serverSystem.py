# -*- coding: utf-8 -*-
import math
import time
from collections import deque

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from JetBelt import mathUtil
from JetBelt.const import INCOMPLETE_ITEM, AIR_BLOCK, PENETRABLE_BLOCK_TYPE
from JetBelt.dataManager import DataManager

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

        self.fallingProtectionDict = {}

    def ReleaseSkill(self, playerId, skill):
        if not self.IsWearing(playerId):
            return
        if skill == "brake":
            motionComp = CF.CreateActorMotion(playerId)
            motionComp.SetPlayerMotion((0, 0, 0))
            self.fallingProtectionDict[playerId] = time.time() + 3
        elif skill == "flash":
            blocks = serverApi.getEntitiesOrBlockFromRay(CF.CreateDimension(playerId).GetEntityDimensionId(),
                                                         CF.CreatePos(playerId).GetPos(),
                                                         serverApi.GetDirFromRot(
                                                             CF.CreateRot(playerId).GetRot()),
                                                         DataManager.Get(playerId, "func_flash_max_distance"),
                                                         True,
                                                         serverApi.GetMinecraftEnum().RayFilterType.OnlyBlocks)
            if blocks:
                for block in blocks:
                    if block['identifier'] in PENETRABLE_BLOCK_TYPE:
                        continue
                    blockPos = block["pos"]
                    CF.CreatePos(playerId).SetFootPos((blockPos[0], blockPos[1] + 1, blockPos[2]))
                    break
            else:
                CF.CreatePos(playerId).SetFootPos((Vector3(CF.CreatePos(playerId).GetFootPos()) + Vector3(
                    serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())) * DataManager.Get(playerId,
                                                                                                "func_flash_max_distance")).ToTuple())
                self.fallingProtectionDict[playerId] = time.time() + 3
                self.TakeDurability(playerId, DataManager.Get(playerId, "func_{}_durability_consumption".format(skill)))

    def Use(self, playerId, vector):
        if not self.IsWearing(playerId):
            return
        motionComp = CF.CreateActorMotion(playerId)
        playerDir = serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())
        jetDir = playerDir if abs(vector[0]) < 0.2 else mathUtil.rotate_direction(vector, playerDir)
        motionComp.SetPlayerMotion(
            (Vector3(jetDir).Normalized() * (DataManager.Get(playerId, "func_use_strength") + (
                0 if DataManager.Get(playerId, "func_switch_power_state") == "normal" else DataManager.Get(playerId,
                                                                                                           "func_boost_use_strength")))).ToTuple())
        self.fallingProtectionDict[playerId] = time.time() + 3
        self.TakeDurability(playerId, DataManager.Get(playerId, "func_use_durability_consumption") + (
            0 if DataManager.Get(playerId, "func_switch_power_state") == "normal" else DataManager.Get(playerId,
                                                                                                       "func_boost_use_durability_consumption")))
        # if not DataManager.Get(playerId, "usage_informed"):
        #     DataManager.Set(playerId, "usage_informed", True)
        #     CF.CreateMsg(playerId).NotifyOneMessage(playerId,
        #                                             "§6[引力枪模组] §f欢迎使用引力枪模组！你可以在聊天框发送§e“引力枪设置”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f。若有任何想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

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

    @Listen("DamageEvent")
    def PlayerDamaged(self, event):
        playerId = event['entityId']
        if event['cause'] != serverApi.GetMinecraftEnum().ActorDamageCause.Fall:
            return
        if CF.CreateEngineType(playerId).GetEngineTypeStr() != "minecraft:player":
            return
        if time.time() < self.fallingProtectionDict.get(playerId, 0):
            event['damage'] = 0
            print "保护"

    def IsWearing(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 2)
        return item and item['newItemName'] == 'orchiella:jet_belt'

    def TakeDurability(self, playerId, value):
        if value == 0: return
        if GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.ARMOR
        item = itemComp.GetPlayerItem(enum, 2)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 2, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 2)

    def SendTip(self, playerId, message, color):
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[动力推进器]")

    def GetEntityName(self, entityId):
        name = CF.CreateName(entityId).GetName()
        if name: return name
        return GC.GetChinese(
            "entity.{}.name".format(CF.CreateEngineType(entityId).GetEngineTypeStr().replace("minecraft:", ""))).encode(
            "utf-8")

    def GetBlockName(self, name, aux):
        return CF.CreateItem(levelId).GetItemBasicInfo(name, aux)['itemName']

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

    def CallAllClient(self, funcName, *args, **kwargs):
        self.BroadcastToAllClient('ServerEvent', DB.CreateEventData(funcName, args, kwargs))

    @Listen('ClientEvent', DB.ModName, 'ClientSystem')
    def OnGetClientEvent(self, args):
        getattr(self, args['funcName'])(*args.get('args', ()), **args.get('kwargs', {}))
