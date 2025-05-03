# -*- coding: utf-8 -*-
import time

import mod.client.extraClientApi as clientApi

from JetBelt import mathUtil
from JetBelt.config import ModName, mod_name

ScreenNode = clientApi.GetScreenNodeCls()
PID = clientApi.GetLocalPlayerId()
CF = clientApi.GetEngineCompFactory()


class JetBeltFunctions(ScreenNode):
    ViewBinder = clientApi.GetViewBinderCls()

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.client = clientApi.GetSystem(ModName, "ClientSystem")
        self.player_id = clientApi.GetLocalPlayerId()
        self.panel_ctrl = None
        self.tick = 0
        self.dragging_mode = False
        self.dragging_pos_offset = None
        self.initialized = False
        self.clicking_func = None

        self.func_def = {
            "use": {"name": "§{color}喷气({rem}/{max})", "type": "shoot"},
            "flash": {"name": "§{color}闪现{cd}", "type": "skill"},
            "brake": {"name": "§{color}制动{cd}", "type": "skill",
                      "condition": lambda: mathUtil.Length(CF.CreateActorMotion(PID).GetMotion()) > 0.2},
            "fear": {"name": "§{color}震慑{cd}", "type": "skill"},
            "switch_power": {"name": "功率:{state}", "type": "switch",
                             "candidates": [("normal", {"name": "§a常规"}),
                                            ("boost", {"name": "§c增强"})]}
        }
        self.use_cd = {func_key: 0 for func_key, func_def in self.func_def.items() if
                       func_def['type'] == 'skill' or func_def['type'] == 'shoot'}
        self.bullet_rec = {func_key: 0 for func_key, func_def in self.func_def.items() if
                           func_def['type'] == 'shoot'}
        self.state_rec = {func_key: self.GetData("func_{}_state".format(func_key)) for func_key, func_def in
                          self.func_def.items() if func_def['type'] == 'switch'}
        self.func_btn_ctrls = {}
        self.func_label_ctrls = {}

        self.last_click = None
        self.last_move_time = 0  # 拖动模式下，开始停留在某个位置的时间戳，更新当且仅当Update检测到拖动位置变化，这样可以检测是否长期没有拖动以便强行断触，防止目前在PC端发现的莫名其妙进入拖动模式出不来的偶然事件

    def Update(self):
        if not self.initialized:
            return
        for func_key, func_def in self.func_def.items():
            label_ctrl = self.func_label_ctrls[func_key]
            if func_def['type'] == 'shoot':
                bullet_capacity = self.GetData("func_{}_capacity".format(func_key))
                if self.bullet_rec[func_key] > bullet_capacity:
                    self.bullet_rec[func_key] = bullet_capacity
                bullet_left = bullet_capacity - self.bullet_rec[func_key]
                if bullet_left < bullet_capacity:
                    if time.time() > self.use_cd[func_key]:
                        self.bullet_rec[func_key] -= 1
                        self.use_cd[func_key] = time.time() + self.GetData("func_{}_cd".format(func_key))
                bullet_consumption = 1 + (
                    0 if self.state_rec["switch_power"] == "normal" else self.GetData(
                        "func_boost_use_energy_consumption"))
                label_ctrl.SetText(
                    func_def['name'].format(color="f" if self.bullet_rec["use"] + bullet_consumption <= bullet_capacity else "8",
                                            rem=(bullet_capacity - self.bullet_rec[func_key]), max=bullet_capacity))
            elif func_def['type'] == 'skill':
                leftTime = self.use_cd[func_key] - time.time()
                isConditionMet = "condition" not in func_def or func_def['condition']()
                if leftTime > 0.2:
                    label_ctrl.SetText(func_def['name'].format(color="e" if isConditionMet else "8",
                                                               cd="({}s)".format(round(leftTime, 1))))
                else:
                    label_ctrl.SetText(func_def['name'].format(color="f" if isConditionMet else "8", cd=""))
        if self.client.IsWearing():
            self.SetScreenVisible(True)
        else:
            self.SetScreenVisible(False)
            return
        if self.clicking_func:
            if self.tick != 0 and time.time() - self.tick > 0.5 and not self.dragging_mode:
                # 进入拖拽模式
                dragging_skill_ctrl = self.func_btn_ctrls[self.clicking_func]
                btn_pos, click_pos = dragging_skill_ctrl.GetPosition(), clientApi.GetTouchPos()
                offset_x, offset_y = btn_pos[0] - click_pos[0], btn_pos[1] - click_pos[1]
                self.dragging_pos_offset = (offset_x, offset_y)
                btn_size = dragging_skill_ctrl.GetSize()
                if click_pos == (0.0, 0.0) or offset_x > 0 or -offset_x > btn_size[0] or offset_y > 0 or -offset_y > \
                        btn_size[1]:
                    # 太快了系统没反应过来
                    return
                self.dragging_mode = True
                self.SetIsHud(False)

                self.last_click = clientApi.GetTouchPos()
                self.last_move_time = time.time()
            if self.dragging_mode and clientApi.GetTouchPos() != (0.0, 0.0):
                # 拖拽时实时更新位置
                click_pos, offset = clientApi.GetTouchPos(), self.dragging_pos_offset
                self.func_btn_ctrls[self.clicking_func].SetPosition(
                    (click_pos[0] + offset[0], click_pos[1] + offset[1]))
                if self.last_click != click_pos:
                    self.last_move_time = time.time()
                    self.last_click = click_pos
            if time.time() - self.last_move_time > 5 or clientApi.GetTouchPos() == (0.0, 0.0):
                # 停留超过5秒，强行断触并保存
                self.dragging_mode = False
                self.SetIsHud(True)
                self.SetData("func_{}_pos".format(self.clicking_func),
                             self.func_btn_ctrls[self.clicking_func].GetPosition())

    def Create(self):
        self.Display(False)

    def Display(self, show):
        if show:
            if not self.initialized:
                template_btn_path = "/template"
                for func_key, func_def in self.func_def.items():
                    self.Clone(template_btn_path, "/", func_key)
                    btn_ctrl = self.GetBaseUIControl("/" + func_key).asButton()
                    btn_ctrl.SetButtonTouchDownCallback(self.on_click_down)
                    btn_ctrl.SetButtonTouchUpCallback(self.on_click_up)
                    btn_ctrl.AddTouchEventParams({'func_key': func_key})
                    btn_ctrl.SetPosition(self.GetData("func_{}_pos".format(func_key)))
                    self.func_btn_ctrls[func_key] = btn_ctrl

                    label_ctrl = self.GetBaseUIControl("/" + func_key + "/label").asLabel()
                    if func_def['type'] == 'shoot':
                        label_ctrl.SetText(
                            func_def['name'].format(color="8",
                                                    rem=self.GetData("func_{}_capacity".format(func_key)),
                                                    max=self.GetData("func_{}_capacity".format(func_key))))
                    elif func_def['type'] == 'skill':
                        label_ctrl.SetText(func_def['name'].format(color="f", cd=""))
                    elif func_def['type'] == 'switch':
                        label_ctrl.SetText(
                            func_def['name'].format(state=tuple(
                                info['name'] for state, info in func_def['candidates'] if
                                state == self.state_rec[func_key])[0]))
                    self.func_label_ctrls[func_key] = label_ctrl

                    self.GetBaseUIControl("/" + func_key + "/default").asImage().SetSprite(
                        "textures/ui/" + mod_name + "/" + func_key)
                    self.GetBaseUIControl("/" + func_key + "/hover").asImage().SetSprite(
                        "textures/ui/" + mod_name + "/" + func_key)
                    self.GetBaseUIControl("/" + func_key + "/pressed").asImage().SetSprite(
                        "textures/ui/" + mod_name + "n/" + func_key)
                self.GetBaseUIControl(template_btn_path).SetVisible(False)

                self.initialized = True
            self.SetScreenVisible(show)

    def on_click_down(self, args):
        self.tick = time.time()
        self.clicking_func = args['AddTouchEventParams']['func_key']

    def on_click_up(self, args):
        self.tick = 0
        if self.dragging_mode:
            self.dragging_mode = False
            self.SetIsHud(True)
            self.SetData("func_{}_pos".format(self.clicking_func),
                         self.func_btn_ctrls[self.clicking_func].GetPosition())
        else:
            func_def = self.func_def[self.clicking_func]
            if func_def['type'] == 'skill':
                if "condition" in func_def and not func_def['condition']():
                    return
                if time.time() < self.use_cd[self.clicking_func]:
                    return
                self.use_cd[self.clicking_func] = time.time() + self.GetData("func_{}_cd".format(self.clicking_func))
                self.client.ReleaseSkill(self.clicking_func)
            elif func_def['type'] == 'shoot':
                bullet_capacity = self.GetData("func_{}_capacity".format(self.clicking_func))
                bullet_consumption = 1 + (
                    0 if self.state_rec["switch_power"] == "normal" else self.GetData(
                        "func_boost_use_energy_consumption"))
                if self.bullet_rec[self.clicking_func] + bullet_consumption > bullet_capacity:
                    return
                if self.bullet_rec[self.clicking_func] == 0:
                    self.use_cd[self.clicking_func] = time.time() + self.GetData(
                        "func_{}_cd".format(self.clicking_func))
                self.bullet_rec[self.clicking_func] += bullet_consumption
                self.func_label_ctrls[self.clicking_func].SetText(
                    func_def['name'].format(
                        color="f" if 1 else "8",
                        rem=(bullet_capacity - self.bullet_rec[self.clicking_func]),
                        max=bullet_capacity))
                self.client.Use(CF.CreateActorMotion(PID).GetInputVector())
            elif func_def['type'] == 'switch':
                now_i = -1
                valid_candidate_indexes_before, valid_candidate_indexes_after = [], []
                for i in range(len(func_def['candidates'])):
                    candidate_name, candidate_info = func_def['candidates'][i][0], func_def['candidates'][i][1]
                    if self.state_rec[self.clicking_func] == candidate_name:
                        now_i = i
                    else:
                        if "settings_key" not in candidate_info or self.GetData(candidate_info['settings_key']):
                            if now_i == -1:
                                valid_candidate_indexes_before.append(i)
                            else:
                                valid_candidate_indexes_after.append(i)
                valid_candidate_indexes_after.extend(valid_candidate_indexes_before)
                if valid_candidate_indexes_after:
                    state_key, state_info = func_def['candidates'][valid_candidate_indexes_after[0]]
                    self.state_rec[self.clicking_func] = state_key
                    self.func_label_ctrls[self.clicking_func].SetText(func_def['name'].format(
                        state=state_info['name']))
                    self.SetData("func_{}_state".format(self.clicking_func), state_key)
        self.clicking_func = None

    def GetState(self, func_key):
        return self.state_rec[func_key]

    def GetData(self, key):
        return self.client.GetData(key)

    def SetData(self, key, value):
        self.client.SetData(key, value)
        self.client.CallServer("SetData", 0, PID, key, value)
