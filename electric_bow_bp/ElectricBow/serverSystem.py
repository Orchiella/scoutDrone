# -*- coding: utf-8 -*-
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from ElectricBow import mathUtil
from ElectricBow.const import PENETRABLE_BLOCK_TYPE
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

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)

        GC.AddRepeatedTimer(0.1, self.Timer)

    lightBlockPoses = {}
    nightVisionPlayers = set()

    def Timer(self):
        for playerId in serverApi.GetPlayerList():
            if DataManager.Get(playerId, "func_night_vision_state") == "on":
                if not self.IsEquipped(playerId):
                    continue
                CF.CreateEffect(playerId).AddEffectToEntity("night_vision", 11, 1, False)
                self.nightVisionPlayers.add(playerId)
            else:
                if playerId in self.nightVisionPlayers:
                    self.nightVisionPlayers.remove(playerId)
                    CF.CreateEffect(playerId).RemoveEffectFromEntity("night_vision")
            if playerId in self.lightBlockPoses:
                CF.CreateBlockInfo(levelId).SetBlockNew(self.lightBlockPoses[playerId],
                                                        {"name": "minecraft:air", "aux": 0}, 0,
                                                        CF.CreateDimension(playerId).GetEntityDimensionId())
            if DataManager.Get(playerId, "func_light_state") == "on":
                if not self.IsEquipped(playerId):
                    continue
                dimId = CF.CreateDimension(playerId).GetEntityDimensionId()
                blocks = serverApi.getEntitiesOrBlockFromRay(dimId,
                                                             CF.CreatePos(playerId).GetPos(),
                                                             serverApi.GetDirFromRot(
                                                                 CF.CreateRot(playerId).GetRot()),
                                                             DataManager.Get(playerId, "func_light_distance"),
                                                             True,
                                                             serverApi.GetMinecraftEnum().RayFilterType.OnlyBlocks)
                if blocks:
                    penetratedBlock = None
                    for block in blocks:
                        if block['identifier'] in PENETRABLE_BLOCK_TYPE:
                            continue
                        penetratedBlock = block
                        break
                    blockComp = CF.CreateBlockInfo(levelId)
                    if penetratedBlock:
                        blockPos = penetratedBlock["pos"]
                        for pos in mathUtil.GetSurroundingPoses(blockPos):
                            if blockComp.GetBlockNew(pos, dimId)['name'] == "minecraft:air":
                                blockComp.SetBlockNew(pos, {"name": "minecraft:light_block", "aux": 15}, 0,
                                                      dimId)
                                self.lightBlockPoses[playerId] = pos
                                break
                else:
                    if playerId in self.lightBlockPoses:
                        del self.lightBlockPoses[playerId]
        for data in reversed(self.ignoreAttack):
            if time.time() > data[2]:
                self.ignoreAttack.remove(data)
                continue
            entityId = data[0]
            playerId = data[1]
            if CF.CreateAction(entityId).GetAttackTarget() == playerId:
                CF.CreateAction(entityId).ResetAttackTarget()

    ignoreAttack = []

    def ReleaseSkill(self, playerId, skill):
        if not self.IsEquipped(playerId):
            return
        frameColors = {serverApi.GetMinecraftEnum().EntityType.Monster: (1, 0, 0),
                       serverApi.GetMinecraftEnum().EntityType.Player: (0, 0, 1)}
        if skill == "sensing":
            n = 0
            for nearEntity in GC.GetEntitiesAround(playerId, DataManager.Get(playerId, "func_sensing_radius"), {}):
                if nearEntity == playerId:
                    continue
                color = (1, 1, 1)
                for entityType, frameColor in frameColors.items():
                    if CF.CreateEngineType(nearEntity).GetEngineType() & entityType == entityType:
                        color = frameColor
                        break
                self.CallClient(playerId, "AppendFrame", nearEntity, "hn_frame",
                                DataManager.Get(playerId, "func_sensing_duration"),
                                CF.CreateCollisionBox(nearEntity).GetSize()[1], color)
                n += 1
                if n >= DataManager.Get(playerId, "func_sensing_max"):
                    break
        elif skill == "invisibility":
            for nearEntity in GC.GetEntitiesAround(playerId, DataManager.Get(playerId, "func_invisibility_radius"), {}):
                if nearEntity == playerId:
                    continue
                self.ignoreAttack.append(
                    (nearEntity, playerId, time.time() + DataManager.Get(playerId, "func_invisibility_duration")))
        self.TakeDurability(playerId, DataManager.Get(playerId, "func_{}_durability_consumption".format(skill)))
        if not DataManager.Get(playerId, "usage_informed"):
            DataManager.Set(playerId, "usage_informed", True)
            CF.CreateMsg(playerId).NotifyOneMessage(playerId,
                                                    "§6[夜视头盔模组] §f欢迎使用本模组！你可以在聊天框发送§e“夜视头盔设置”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f，或在设置面板中§e暂时隐藏§f掉。对于电脑版玩家，可以为各种功能§d绑定键位§f。若有任何想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

    def IsEquipped(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == 'orchiella:electric_bow'

    def TakeDurability(self, playerId, value):
        if GC.GetPlayerGameType(playerId) == serverApi.GetMinecraftEnum().GameType.Creative: return
        itemComp = CF.CreateItem(playerId)
        enum = serverApi.GetMinecraftEnum().ItemPosType.ARMOR
        item = itemComp.GetPlayerItem(enum, 0)
        if item['durability'] > value:
            itemComp.SetItemDurability(enum, 0, item['durability'] - value)
        else:
            itemComp.SetEntityItem(enum, None, 0)

    def SendTip(self, playerId, message, color):
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[夜间战术头盔]")

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
        if message == "夜视头盔设置":
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
