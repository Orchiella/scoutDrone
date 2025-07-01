# -*- coding: utf-8 -*-
import random
import time

import mod.client.extraClientApi as clientApi

import config as DB
from ChainSword.ui import uiMgr
from ChainSword.ui.uiDef import UIDef

CF = clientApi.GetEngineCompFactory()
PID = clientApi.GetLocalPlayerId()
levelId = clientApi.GetLevelId()
PC = CF.CreateParticleSystem(None)
AC = CF.CreateCustomAudio(levelId)
GC = CF.CreateGame(levelId)
QC = CF.CreateQueryVariable(PID)
CC = CF.CreateCamera(PID)
eventList = []


def Listen(funcOrStr, EN=clientApi.GetEngineNamespace(), ESN=clientApi.GetEngineSystemName(), priority=0):
    def binder(func):
        if callable(funcOrStr):
            eventList.append((EN, ESN, func.__name__, func, priority))
        else:
            if isinstance(funcOrStr, tuple):
                for funcStr in funcOrStr: eventList.append((EN, ESN, funcStr, func, priority))
            else:
                eventList.append((EN, ESN, funcOrStr, func, priority))
        return func

    return binder(funcOrStr) if callable(funcOrStr) else binder


class ClientSystem(clientApi.GetClientSystemCls()):
    def __init__(self, namespace, systemName):
        super(ClientSystem, self).__init__(namespace, systemName)
        for EN, ESN, eventName, callback, priority in eventList:
            self.ListenForEvent(EN, ESN, eventName, self, callback, priority)

        self.uiMgr = uiMgr.UIMgr()
        self.settingsScreen = None
        self.functionsScreen = None
        self.settings = {}
        self.frameDataDict = {"eb_lightning": [], "eb_frame": []}
        GC.AddRepeatedTimer(0.05, self.UpdateFrame)
        GC.AddRepeatedTimer(0.5, self.TestVar)

        self.isRevving = False

    def TestVar(self):
        # 动态修改测试
        pass
        for key, value in {
            "1st_l_idle_pos_x": -4, "1st_l_idle_pos_y": -8, "1st_l_idle_pos_z": 16,
            "1st_l_idle_rot_x": 80, "1st_l_idle_rot_y": 42, "1st_l_idle_rot_z": 13,
            "1st_l_run_rot_offset_x": -40, "1st_l_run_rot_offset_y": 0, "1st_l_run_rot_offset_z": 0,
            "1st_l_run_pos_offset_x": 0, "1st_l_run_pos_offset_y": -1, "1st_l_run_pos_offset_z": 0,
            "1st_l_rev_rot_offset_x": -13, "1st_l_rev_rot_offset_y": 14, "1st_l_rev_rot_offset_z": -5,
            "1st_l_rev_pos_offset_x": 5, "1st_l_rev_pos_offset_y": -3, "1st_l_rev_pos_offset_z": -4,

            "1st_r_idle_pos_x": 14, "1st_r_idle_pos_y": -6, "1st_r_idle_pos_z": 11,
            "1st_r_idle_rot_x": 90, "1st_r_idle_rot_y": 11, "1st_r_idle_rot_z": -190,
            "1st_r_run_rot_offset_x": 40, "1st_r_run_rot_offset_y": 0, "1st_r_run_rot_offset_z": 0,
            "1st_r_run_pos_offset_x": 0, "1st_r_run_pos_offset_y": 0, "1st_r_run_pos_offset_z": 0,
            "1st_r_rev_rot_offset_x": 45, "1st_r_rev_rot_offset_y": 0, "1st_r_rev_rot_offset_z": 0,
            "1st_r_rev_pos_offset_x": -0.2, "1st_r_rev_pos_offset_y": -3.6, "1st_r_rev_pos_offset_z": 4,

            "1st_teeth_rev_rot_offset_z": -10,
        }.items():
            QC.Set('query.mod.{}_{}'.format(DB.mod_name, key), value)

    revAvailableTime = 0
    revSlashAvailableTime = 0
    revFinished = False
    animLengthDict = {"equip": 0.6667, "run_enter": 0.1, "run_exit": 0.2, "rev_slash": 1, "rev_enter": 0.7,
                      "rev_exit": 0.3, "slash": 0.8}

    def UpdateRevAvailableTime(self, second):
        if time.time() > self.revAvailableTime:
            self.revAvailableTime = time.time() + second

    @Listen
    def OnScriptTickClient(self):
        if self.revSlashAvailableTime != 0 and time.time() > self.revSlashAvailableTime:
            if not self.revFinished:
                self.revFinished = True
                self.UpdateRevState(True)

    # 其实是从服务端传过来的，服务端版本的这个事件会帮我们忽略耐久变化的情况
    def OnCarriedNewItemChangedClientEvent(self, event):
        item = event["newItemDict"]
        if not item:
            return
        if item['newItemName'] == "orchiella:chain_sword":
            self.BlinkVar("equip")
            self.UpdateRevAvailableTime(self.animLengthDict["equip"])
            self.PlaySound("equip")
        else:
            self.revAvailableTime = 0
            self.UpdateRevState(False)

    # 切换疾跑事件，其实有专门的原生molang表达式可以判断，但为了管理，由模组来控制
    @Listen("OnLocalPlayerActionClientEvent")
    def OnSwitchSprint(self, event):
        if not self.IsEquipped():
            return
        if event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StartSprinting:
            self.BlinkVar("run_enter")
            self.UpdateRevAvailableTime(self.animLengthDict["run_enter"])
        elif event['actionType'] == clientApi.GetMinecraftEnum().PlayerActionType.StopSprinting:
            self.BlinkVar("run_exit")
            self.UpdateRevAvailableTime(self.animLengthDict["run_exit"])

    @Listen(("LeftClickBeforeClientEvent", "TapBeforeClientEvent"))
    def LeftClick(self, event):
        if not self.IsEquipped():
            return
        event['cancel'] = True
        if time.time() < self.revAvailableTime:
            return
        if self.isRevving:
            self.BlinkVar("rev_slash")
            self.CallServer("Attack", 0.4, PID)
            self.UpdateRevAvailableTime(self.animLengthDict["rev_slash"])
        else:
            self.BlinkVar("slash" if int(time.time()) % 2 == 1 else "slash2")
            self.CallServer("Attack", 0.375, PID)
            self.UpdateRevAvailableTime(self.animLengthDict["slash"])
        sound = "slash{}".format(random.randint(3, 5))
        print sound
        self.PlaySound(sound)

    revvingSoundId = None

    def UpdateRevState(self, state):
        self.isRevving = state
        self.CallServer("UpdateRevState", 0, PID, state)
        if state:
            self.revvingSoundId = AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_revving", (0, 0, 0), 1, 1, True,
                                                     PID)
        else:
            if self.revvingSoundId:
                AC.StopCustomMusicById(self.revvingSoundId)
                self.revvingSoundId = None

    def SyncVarToServer(self, delay, key, value):
        if delay == 0:
            self.UpdateVar(key, value, PID)
        else:
            GC.AddTimer(delay, self.UpdateVar, key, value, PID)
        self.CallServer("SyncVarToClients", delay, PID, key, value)

    def UpdateVar(self, key, value, playerId=PID):
        CF.CreateQueryVariable(playerId).Set("query.mod." + DB.mod_name + "_" + key, value)

    # 让变量闪烁一次，用于通知状态转换
    def BlinkVar(self, key, playerId=PID):
        if playerId == PID:
            self.SyncVarToServer(0, key, 1.0)
            self.SyncVarToServer(0.05, key, 0.0)  # 如果不延迟一点，闪烁不会被检测到
        else:
            self.UpdateVar(key, 1.0, playerId)
            GC.AddTimer(0.05, self.UpdateVar, key, 0.0, playerId)

    def ReleaseSkill(self, skill):
        if not self.IsEquipped():
            return
        if self.revAvailableTime > time.time():
            return
        if skill == "rev":
            if not self.revFinished:
                if self.revSlashAvailableTime == 0:
                    self.BlinkVar("rev_enter")
                    self.revSlashAvailableTime = time.time() + self.animLengthDict["rev_enter"]
                    self.PlaySound("toggle")
            else:
                self.BlinkVar("rev_exit")
                self.UpdateRevAvailableTime(self.animLengthDict["rev_exit"])
                self.revSlashAvailableTime = 0
                self.revFinished = False
                self.UpdateRevState(False)
            return
        self.CallServer("ReleaseSkill", 0, PID, skill)

    def SyncSoundToServer(self, delay, soundName):
        if delay == 0:
            self.PlaySound(soundName)
        else:
            GC.AddTimer(delay, self.PlaySound, soundName)
        self.CallServer("SyncSoundToClients", delay, PID, soundName)

    def PlaySound(self, soundName):
        if not self.GetData("sound_enabled"):
            return
        AC.PlayCustomMusic("orchiella:" + DB.mod_name + "_" + soundName, (0, 0, 0), 1, 1, False, PID)

    @Listen
    def OnLocalPlayerStopLoading(self, args):
        self.CallServer("LoadData", 0, PID)
        levelQC = CF.CreateQueryVariable(levelId)
        for key, value in {"slash": 0, "slash2": 0, "run_enter": 0, "run_exit": 0,
                           "equip": 0, "rev_enter": 0, "rev_exit": 0, "rev_slash": 0,
                           "1st_l_idle_pos_x": -3, "1st_l_idle_pos_y": -5, "1st_l_idle_pos_z": 8,
                           "1st_l_idle_rot_x": 87, "1st_l_idle_rot_y": 0, "1st_l_idle_rot_z": -132,
                           "1st_l_run_rot_offset_x": 0, "1st_l_run_rot_offset_y": 17, "1st_l_run_rot_offset_z": 34,
                           "1st_l_run_pos_offset_x": -4, "1st_l_run_pos_offset_y": -2, "1st_l_run_pos_offset_z": 0,
                           "1st_l_rev_rot_offset_x": -6, "1st_l_rev_rot_offset_y": 13, "1st_l_rev_rot_offset_z": -26,
                           "1st_l_rev_pos_offset_x": 1.7, "1st_l_rev_pos_offset_y": 0.1, "1st_l_rev_pos_offset_z": 1.4,

                           "1st_r_idle_pos_x": -3, "1st_r_idle_pos_y": -5, "1st_r_idle_pos_z": 8,
                           "1st_r_idle_rot_x": 87, "1st_r_idle_rot_y": 0, "1st_r_idle_rot_z": -132,
                           "1st_r_run_rot_offset_x": 0, "1st_r_run_rot_offset_y": 17, "1st_r_run_rot_offset_z": 34,
                           "1st_r_run_pos_offset_x": -4, "1st_r_run_pos_offset_y": -2, "1st_r_run_pos_offset_z": 0,
                           "1st_r_rev_rot_offset_x": -6, "1st_r_rev_rot_offset_y": 13, "1st_r_rev_rot_offset_z": -26,
                           "1st_r_rev_pos_offset_x": 1.7, "1st_r_rev_pos_offset_y": 0.1, "1st_r_rev_pos_offset_z": 1.4,

                           "1st_teeth_rev_rot_offset_z": -20,
                           }.items():
            levelQC.Register('query.mod.{}_{}'.format(DB.mod_name, key), value)
            QC.Set('query.mod.{}_{}'.format(DB.mod_name, key), value)
        self.Rebuild(PID)

        def equip():
            if self.IsEquipped():
                self.BlinkVar("equip")
                self.UpdateRevAvailableTime(self.animLengthDict["equip"])
            self.CallServer("SyncRebuild", 0, PID)

        GC.AddTimer(1, equip)

    def Rebuild(self, playerId, blinkList=None, varDict=None):
        actorComp = CF.CreateActorRender(playerId)
        prefix = DB.mod_name + "_"
        actorComp.AddPlayerGeometry(prefix + "arm", "geometry.chain_sword_arm")
        actorComp.AddPlayerRenderController("controller.render.chain_sword_arm",
                                            "v.is_first_person && query.get_equipped_item_full_name('main_hand') == 'orchiella:chain_sword'")
        actorComp.AddPlayerAnimation(prefix + "1st_equip", "animation.chain_sword.1st_equip")
        actorComp.AddPlayerAnimation(prefix + "1st_idle", "animation.chain_sword.1st_idle")
        actorComp.AddPlayerAnimation(prefix + "1st_slash", "animation.chain_sword.1st_slash")
        actorComp.AddPlayerAnimation(prefix + "1st_slash2", "animation.chain_sword.1st_slash2")
        actorComp.AddPlayerAnimation(prefix + "1st_run_enter", "animation.chain_sword.1st_run_enter")
        actorComp.AddPlayerAnimation(prefix + "1st_run", "animation.chain_sword.1st_run")
        actorComp.AddPlayerAnimation(prefix + "1st_run_exit", "animation.chain_sword.1st_run_exit")
        actorComp.AddPlayerAnimation(prefix + "1st_rev_enter", "animation.chain_sword.1st_rev_enter")
        actorComp.AddPlayerAnimation(prefix + "1st_rev", "animation.chain_sword.1st_rev")
        actorComp.AddPlayerAnimation(prefix + "1st_rev_slash", "animation.chain_sword.1st_rev_slash")
        actorComp.AddPlayerAnimation(prefix + "1st_rev_exit", "animation.chain_sword.1st_rev_exit")
        actorComp.AddPlayerAnimation(prefix + "default", "animation.chain_sword.default")
        actorComp.AddPlayerAnimation(prefix + "3rd_idle", "animation.chain_sword.3rd_idle")
        actorComp.AddPlayerAnimation(prefix + "3rd_slash", "animation.chain_sword.3rd_slash")
        actorComp.AddPlayerAnimation(prefix + "3rd_slash2", "animation.chain_sword.3rd_slash2")
        actorComp.AddPlayerAnimation(prefix + "3rd_equip", "animation.chain_sword.3rd_equip")
        actorComp.AddPlayerAnimation(prefix + "3rd_rev", "animation.chain_sword.3rd_rev")
        actorComp.AddPlayerAnimation(prefix + "3rd_rev_slash", "animation.chain_sword.3rd_rev_slash")

        actorComp.AddPlayerAnimationController(prefix + "arm_controller", "controller.animation.chain_sword.general")
        actorComp.AddPlayerScriptAnimate(prefix + "arm_controller",
                                         "query.get_equipped_item_full_name('main_hand') == 'orchiella:chain_sword'")
        if blinkList:
            for var in blinkList:
                self.BlinkVar(var, playerId)

        if varDict:
            playerQueryComp = CF.CreateQueryVariable(playerId)
            for key, value in varDict.items():
                playerQueryComp.Set("query.mod." + DB.mod_name + "_" + key, value)

        actorComp.RebuildPlayerRender()

    def IsEquipped(self):
        item = CF.CreateItem(PID).GetPlayerItem(clientApi.GetMinecraftEnum().ItemPosType.CARRIED)
        return item and item['newItemName'] == "orchiella:chain_sword"

    @Listen
    def UiInitFinished(self, args):
        self.uiMgr.Init(self)
        self.settingsScreen = self.uiMgr.GetUI(UIDef.Settings)
        self.functionsScreen = self.uiMgr.GetUI(UIDef.Functions)
        self.functionsScreen.Display(True)

    def PlayParticle(self, particleName, poses, varDict=None):
        if isinstance(poses, tuple):
            poses = {poses}
        prefix = "orchiella:" + DB.mod_name + "_"
        for pos in poses:
            parId = PC.Create(prefix + particleName, pos)
            if varDict:
                for key, value in varDict.items():
                    PC.SetVariable(parId, "variable." + key, value)

    def BindParticle(self, effectName, entityId, locator="locator"):
        parId = PC.Create("orchiella:" + effectName)
        PC.BindEntity(parId, entityId, locator, (0, 0, 0), (0, 0, 0))

    def AppendFrame(self, entityId, frameType, duration, height, scale=0.2):
        frameTypeId = self.CreateEngineSfxFromEditor("effects/" + frameType + ".json")
        frameAniTransComp = CF.CreateFrameAniTrans(frameTypeId)
        frameAniControlComp = CF.CreateFrameAniControl(frameTypeId)
        frameAniTransComp.SetScale((scale, scale, scale))
        frameAniControlComp.Play()
        self.frameDataDict[frameType].append(
            {"effect": frameType, "time": time.time() + duration,
             "entityId": entityId, "height": height,
             "aniTransComp": frameAniTransComp, "aniControlComp": frameAniControlComp})

    def DelFrame(self, entityId, frameType):
        for frameData in self.frameDataDict[frameType]:
            if frameData["entityId"] == entityId:
                frameData["aniControlComp"].Stop()
                self.frameDataDict[frameType].remove(frameData)
                return

    def UpdateFrame(self):
        if not self.frameDataDict: return  # 尚未加载序列帧
        for frameType in self.frameDataDict:
            frameDataList = self.frameDataDict[frameType]
            if not frameDataList: continue
            frameDataToRemove = []
            for i, frameData in enumerate(frameDataList):
                pos = CF.CreatePos(frameData["entityId"]).GetFootPos()
                if not pos:
                    frameData["aniControlComp"].Stop()
                    frameDataToRemove.append(i)  # 箭被销毁或被击中实体死亡，则直接清除
                    continue
                nowTime = time.time()
                if nowTime >= frameData["time"]:
                    # 若序列帧已过期，则清理该序列帧
                    frameData["aniControlComp"].Stop()
                    frameDataToRemove.append(i)
                else:
                    # 若序列帧未过期，则更新位置
                    aniTransComp = frameData["aniTransComp"]
                    aniTransComp.SetPos((pos[0], pos[1] + frameData["height"] / 2, pos[2]))
            for index in reversed(frameDataToRemove):
                del frameDataList[index]  # 倒序删除，避免索引错误

    @Listen('ServerEvent', DB.ModName, 'ServerSystem')
    def OnGetServerEvent(self, args):
        funcName = args['funcName']
        if "." not in funcName:
            getattr(self, funcName)(*args.get('args', ()), **args.get('kwargs', {}))
        else:
            if not getattr(self, funcName.split(".")[0]):
                return
            getattr(getattr(self, funcName.split(".")[0]), funcName.split(".")[1])(*args.get('args', ()),
                                                                                   **args.get('kwargs', {}))

    @Listen
    def OnKeyPressInGame(self, event):
        if not self.functionsScreen:
            return
        if event['isDown'] != '1':
            return
        key = event['key']
        offset = clientApi.GetMinecraftEnum().KeyBoardType.KEY_A - 1
        for func_key in self.functionsScreen.func_def.keys():
            if self.GetData("func_{}_key".format(func_key)) and key == str(
                    self.GetData("func_{}_key".format(func_key)) + offset):
                self.functionsScreen.on_click_down({'AddTouchEventParams': {'func_key': func_key}})
                self.functionsScreen.on_click_up({})

    def CallServer(self, funcName, delay, *args, **kwargs):
        if delay == 0:
            self.NotifyToServer('ClientEvent', DB.CreateEventData(funcName, args, kwargs))
        else:
            GC.AddTimer(delay, self.NotifyToServer, 'ClientEvent',
                        DB.CreateEventData(funcName, args, kwargs))

    def CallClient(self, playerId, funcName, *args, **kwargs):
        if playerId == PID: return getattr(self, funcName)(*args, **kwargs)
        self.CallServer('CallClient', playerId, funcName, *args, **kwargs)

    def CallAllClient(self, funcName, *args, **kwargs):
        self.CallServer('CallAllClient', funcName, *args, **kwargs)

    def GetData(self, key):
        return self.settings[key]

    def SetData(self, key, value):
        self.settings[key] = value
        s1, s2 = "func_{}_enabled", "func_{}_size"
        for func_key in self.functionsScreen.func_def.keys():
            if key == s1.format(func_key):
                self.functionsScreen.SetBtnVisible(func_key, value)
                break
            elif key == s2.format(func_key):
                self.functionsScreen.SetBtnSize(func_key, value)
                break

    def LoadData(self, settings):
        self.settings = settings
