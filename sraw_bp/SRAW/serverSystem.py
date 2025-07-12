# -*- coding: utf-8 -*-
import math
import time

import mod.server.extraServerApi as serverApi
from mod.common.utils.mcmath import Vector3

import config as DB
from SRAW import mathUtil
from SRAW.const import SPECIAL_ENTITIES, PENETRABLE_BLOCK_TYPE
from SRAW.dataManager import DataManager

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

        serverApi.AddEntityTickEventWhiteList("orchiella:sraw_missile")

        dataComp = CF.CreateExtraData(levelId)
        if DataManager.KEY_NAME not in dataComp.GetWholeExtraData():
            dataComp.SetExtraData(DataManager.KEY_NAME, {})
        DataManager()
        DataManager.Check(None)
        GC.AddRepeatedTimer(0.2, self.ModTick)

    def ModTick(self):
        for playerId in serverApi.GetPlayerList():
            if playerId in self.aimPosDict:
                del self.aimPosDict[playerId]
            if not self.IsEquipped(playerId):
                continue
            if not self.aimStateDict.get(playerId, False):
                continue
            CF.CreateEffect(playerId).AddEffectToEntity("night_vision", 11, 1, False)
            blocks = serverApi.getEntitiesOrBlockFromRay(CF.CreateDimension(playerId).GetEntityDimensionId(),
                                                         CF.CreatePos(playerId).GetPos(),
                                                         serverApi.GetDirFromRot(
                                                             CF.CreateRot(playerId).GetRot()), 100,
                                                         True,
                                                         serverApi.GetMinecraftEnum().RayFilterType.OnlyBlocks)
            aimPos = None
            if blocks:
                penetratedBlock = None
                for block in blocks:
                    if block['identifier'] in PENETRABLE_BLOCK_TYPE:
                        continue
                    penetratedBlock = block
                    break
                if penetratedBlock:
                    aimPos = penetratedBlock["pos"]
            if not aimPos:
                continue
            self.CallClient(playerId, "AppendFrame", (aimPos[0], aimPos[1] + 0.2, aimPos[2]), "aim", 0.3, 0)
            self.aimPosDict[playerId] = aimPos

    aimStateDict = {}
    aimPosDict = {}

    def UpdateAimState(self, playerId, state):
        self.aimStateDict[playerId] = state
        if state:
            if playerId not in self.missileDict.values():
                self.SendTip(playerId, "现在可以发射", "a")
            else:
                self.SendTip(playerId, "现在可以继续控制", "e")
        else:
            effects = CF.CreateEffect(playerId).GetAllEffects()
            if effects:
                for effect in effects:
                    if effect["effectName"] == "night_vision" and effect["duration"] <= 11:
                        CF.CreateEffect(playerId).RemoveEffectFromEntity("night_vision")
            if playerId not in self.missileDict.values():
                self.SendTip(playerId, "已退出发射预备状态", "e")
            else:
                self.SendTip(playerId, "可以重新进入瞄准状态以控制", "e")

    @Listen
    def OnCarriedNewItemChangedServerEvent(self, event):
        self.CallClient(event['playerId'], "OnCarriedNewItemChangedClientEvent", event)

    def Shoot(self, playerId):
        if not self.IsEquipped(playerId):
            return
        if not self.aimStateDict.get(playerId, False):
            return
        if playerId in self.missileDict.values():
            self.SendTip(playerId, "你同时只能控制一枚线控导弹", "c")
            return
        takeItem = self.TakeItems(playerId, {"orchiella:sraw_missile": 1})
        if GC.GetPlayerGameType(playerId) != serverApi.GetMinecraftEnum().GameType.Creative and takeItem:
            self.SendTip(playerId, "导弹道具已用尽！请补充", "c")
            return
        footPos = CF.CreatePos(playerId).GetFootPos()
        direction = serverApi.GetDirFromRot(CF.CreateRot(playerId).GetRot())
        yOffset = Vector3(0, 1.4, 0)
        planeOffset = Vector3(0, 0, 0)
        if direction[0] != 0 or direction[2] != 0:  # 向右偏移
            planeOffset = Vector3.Cross(Vector3(direction), yOffset)
            planeOffset = planeOffset.Normalized() * 0.15
        shootPos = (Vector3(footPos) + Vector3(direction) * 0.5 + yOffset + planeOffset).ToTuple()
        missileId = CF.CreateProjectile(levelId).CreateProjectileEntity(playerId,
                                                                        "orchiella:sraw_missile",
                                                                        {
                                                                            "power": DataManager.Get(playerId,
                                                                                                     "velocity") / 4.0,
                                                                            "gravity": 0,
                                                                            'position': shootPos,
                                                                            'direction': direction})
        self.missileDict[missileId] = playerId
        SetEntityData(missileId, "shooter", playerId)
        SetEntityData(missileId, "shootTime", time.time())
        SetEntityData(missileId, "turnTime", time.time() + 0.5)
        SetEntityData(missileId, "distance", 0)
        SetEntityData(missileId, "distanceRecordTime", time.time() + 0.5)
        SetEntityData(missileId, "distanceRecordPos", shootPos)
        self.CallRelevantClients(playerId, "AppendFrame", missileId, "missile", DataManager.Get(playerId, "max_time"),
                                 0)
        self.CallRelevantClients(playerId, "BindParticle", "sraw_plume", missileId)
        self.CallRelevantClients(playerId, "PlaySound", "fire")
        self.TakeDurability(playerId, 1)
        self.SendTip(playerId, "发射成功，移动准星来实时调整导弹方向", "a")
        if not DataManager.Get(playerId, "usage_informed"):
            DataManager.Set(playerId, "usage_informed", True)
            CF.CreateMsg(playerId).NotifyOneMessage(playerId,
                                                    "§b[电击箭复合弓] §f欢迎使用本模组！你可以在聊天框发送§e“电箭设置”§f打开设置面板，自定义各种数值，定制你的使用体验。如果觉得按钮挡也可以§a长按拖动§f。若有任何想法建议或BUG反馈，欢迎进入§6995126773§f群交流")

    missileDict = {}

    @Listen
    def EntityTickServerEvent(self, event):
        missileId = event["entityId"]
        if CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:sraw_missile":
            return
        shooterId = GetEntityData(missileId, "shooter")
        if time.time() - GetEntityData(missileId, "shootTime") > DataManager.Get(shooterId, "max_time"):
            self.Explode(missileId)
            self.SendTip(shooterId, "飞行时间过久，自动启动爆炸程序", "c")
            return
        if time.time() > GetEntityData(missileId, "distanceRecordTime"):
            nowPos = CF.CreatePos(missileId).GetFootPos()
            SetEntityData(missileId, "distanceRecordTime", time.time() + 0.2)
            SetEntityData(missileId, "distance", GetEntityData(missileId, "distance") + (
                    Vector3(nowPos) - Vector3(GetEntityData(missileId, "distanceRecordPos"))).Length())
            SetEntityData(missileId, "distanceRecordPos", nowPos)
            if self.aimStateDict.get(shooterId, False):
                self.CallClient(shooterId, "functionsScreen.UpdateLock", missileId,
                                "线控导弹\n坐标:({},{},{})\n速率:{}单位\n记录:{}米,{}秒\n水平方向:{}".format(
                                    int(math.floor(nowPos[0])), int(math.floor(nowPos[1])), int(math.floor(nowPos[2])),
                                    round(Vector3(CF.CreateActorMotion(missileId).GetMotion()).Length(), 1),
                                    round(GetEntityData(missileId, "distance"), 1),
                                    round(time.time() - GetEntityData(missileId, "shootTime"), 1),
                                    mathUtil.get_direction(CF.CreateActorMotion(missileId).GetMotion())),
                                )
            else:
                self.CallClient(shooterId, "functionsScreen.UpdateLock", None)
        if time.time() > GetEntityData(missileId, "turnTime"):
            SetEntityData(missileId, "turnTime", time.time() + 1 / DataManager.Get(shooterId, "turn_rate"))
            motionCamp = CF.CreateActorMotion(missileId)
            velocity = DataManager.Get(shooterId, "velocity") / 4.0
            if self.aimStateDict.get(shooterId, False):
                nowPos = CF.CreatePos(missileId).GetFootPos()
                if shooterId in self.aimPosDict:
                    motionCamp.SetMotion(
                        ((Vector3(self.aimPosDict[shooterId]) - Vector3(nowPos)).Normalized() * velocity).ToTuple())
                else:
                    playerDir = serverApi.GetDirFromRot(CF.CreateRot(shooterId).GetRot())
                    relativeVec = (Vector3(nowPos) - Vector3(CF.CreatePos(shooterId).GetPos())).Normalized()
                    deltaVec = Vector3(playerDir) - relativeVec
                    if deltaVec.Length() < 0.1:
                        motionVec = relativeVec * velocity
                    else:
                        motionVec = deltaVec.Normalized() * velocity
                    motionCamp.SetMotion(motionVec.ToTuple())
            else:
                motionCamp.SetMotion((Vector3(motionCamp.GetMotion()).Normalized() * velocity).ToTuple())

    @Listen
    def ProjectileDoHitEffectEvent(self, event):
        missileId = event["id"]
        if CF.CreateEngineType(missileId).GetEngineTypeStr() != "orchiella:sraw_missile":
            return
        if time.time() - GetEntityData(missileId, "shootTime") < 1:
            event['cancel'] = True
        else:
            self.Explode(missileId)

    def ExplodeByPlayerId(self, playerId):
        for missileId in self.missileDict:
            if self.missileDict[missileId] == playerId:
                self.Explode(missileId)
                return

    def Explode(self, missileId):
        pos = CF.CreatePos(missileId).GetFootPos()
        shooterId = GetEntityData(missileId, "shooter")
        self.isExploding = shooterId
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
        if CF.CreateEngineType(event['entityId']).GetEngineTypeStr() in {"minecraft:item", "minecraft:xp_orb"}:
            event['damage'] = 0
            return
        event["damage"] = int(
            event["damage"] * DataManager.Get(self.isExploding, 'explode_damage_percentage') / 100.0)

    def IsEquipped(self, playerId):
        comp = CF.CreateItem(playerId)
        item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == 'orchiella:sraw'

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
        GC.SetOnePopupNotice(playerId, "§f" + message, "§" + color + "[线控导弹]")

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
        self.TakeDurability(playerId, 1)
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
