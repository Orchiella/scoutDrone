# -*- coding: utf-8 -*-
import math
import time
from collections import OrderedDict

import mod.client.extraClientApi as clientApi

from ScoutDrone import mathUtil, DeployHelper
from ScoutDrone.config import ModName, mod_name
from ScoutDrone.const import WHITE_COLOR, ATTRIBUTE_TYPE
from ScoutDrone.dataManager import DEFAULT_PLAYER_DATA

ScreenNode = clientApi.GetScreenNodeCls()
CF = clientApi.GetEngineCompFactory()
WHEEL_NUM = 6
CONFIRM_TIME = 0.6
DEPLOYMENT = OrderedDict(
    {"tail": {"name": "尾翼",
              "deployment": [
                  {"name": "原装款"},
                  {"name": "流线款", "defense": -0.2, "speed": 0.25, "firm": -0.3}]},
     "rotor": {"name": "风扇",
               "deployment": [
                   {"name": "原装款"},
                   {"name": "高功率款", "defense": 0.4, "speed": 0.25, "firm": -0.3}]},
     "load": {"name": "下挂",
              "deployment": [
                  {"name": "不下挂"},
                  {"name": "引力钩爪", "speed": -0.2},
                  {"name": "强探照灯", "speed": -0.1},
                  {"name": "诱饵投放器", "speed": -0.1}]},
     "sight": {"name": "放大器",
               "deployment": [
                   {"name": "原装款", "value": 0.8},
                   {"name": "普通放大器", "value": 0.5, "firm": -0.1},
                   {"name": "改良放大器", "value": 0.3, "firm": -0.2, "defense": -0.1},
                   {"name": "专业放大器", "value": 0.1, "firm": -0.3, "defense": -0.15}],
               },
     "battery": {"name": "电池",
                 "deployment": [
                     {"name": "原装电池"},
                     {"name": "轻型电池", "speed": 0.2, "battery": -20},
                     {"name": "大容量电池", "speed": -0.2, "battery:": 50, "firm": -0.1, "defense": -0.1},
                     {"name": "超大容量电池", "speed": -0.4, "battery:": 100, "firm": -0.2, "defense": -0.2},
                     {"name": "特殊能源电池", "speed": 0.3, "battery:": 30, "firm": -0.4}]
                 }
     })


def GetAttributeValue(attribute, content):
    result = ATTRIBUTE_TYPE[attribute]['default']
    for typeName, typeDef in DEPLOYMENT.items():
        result += typeDef['deployment'][DeployHelper.Get(content, typeName)].get(attribute, 0)
    return result


class ScoutDroneFunctions(ScreenNode):
    ViewBinder = clientApi.GetViewBinderCls()

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.client = clientApi.GetSystem(ModName, "ClientSystem")
        self.initialized = False
        self.displaying = False
        self.functions = {
            'inspect': {
                'name': "检视",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.GetEquipment() and not self.client.isControlling},
            'shoot': {
                'name': "启动",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.GetEquipment()},
            'recover': {
                'name': "回收",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.droneData},
            'deploy': {
                'name': "改装",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.GetEquipment() and not self.client.isControlling},
            'control': {
                'name': "控制",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.droneData},
            'function': {
                'name': "下挂功能",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.isControlling and DeployHelper.Get(
                    self.client.droneData['extraId'], "load") > 0},
            'scan': {
                'name': "扫描",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.isControlling},
            'mark': {
                'name': "标记",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.isControlling},
            'explode': {
                'name': "自爆",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.isControlling},
            'sight': {
                'name': "放大",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.isControlling},
            'charge': {
                'name': "",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.GetEquipment()},
            'settings': {
                'name': "",
                "condition": lambda: self.client.nowState == "edit_button" or
                                     self.client.GetEquipment() and not self.client.isControlling}}

    def RefreshButtonVisibility(self):
        for functionName, functionDef in self.functions.items():
            self.GetBaseUIControl("/" + functionName).SetVisible(functionDef.get("condition", lambda: True)())

    touchX, touchY, editProgressValue = 0, 0, -1

    def Update(self):
        if not self.initialized or not self.displaying:
            return
        self.CheckSelect()
        if self.controlPanelBatteryWarningCtrl.GetVisible():
            self.controlPanelBatteryWarningCtrl.SetAlpha(0.5 * (1 + math.sin(5 * time.time())))
        if self.tipDisabledTime != 0 and time.time() > self.tipDisabledTime:
            self.tipLabelCtrl.SetText("")
        if self.client.nowState == "edit_button" and self.functionEditing:
            touchX, touchY = clientApi.GetTouchPos()
            if touchX != self.touchX or touchY != self.touchY:
                self.touchX, self.touchY = touchX, touchY
                ctrl = self.GetBaseUIControl("/" + self.functionEditing)
                size = self.editCache.get("func_{}_size".format(self.functionEditing), ctrl.GetSize()[0])
                screenX, screenY = CF.CreateGame(clientApi.GetLocalPlayerId()).GetScreenSize()
                if (0 <= touchX <= screenX and 0 <= touchY <= screenY and not
                self.IsInCtrl((touchX, touchY), self.GetBaseUIControl('/edit'))):
                    ctrlX, ctrlY = ctrl.GetGlobalPosition()
                    relativeX, relativeY = touchX - ctrlX - size / 2.0, touchY - ctrlY - size / 2.0
                    posX, posY = ctrl.GetPosition()
                    ctrl.SetPosition((posX + relativeX, posY + relativeY))

                    if ctrl.GetAnchorTo() == "left_middle":
                        parentX, parentY = 0, screenY / 2.0
                    else:
                        parentX, parentY = screenX, screenY / 2.0
                    self.editCache["func_{}_pos".format(self.functionEditing)] = (
                        posX + relativeX - parentX, posY + relativeY - parentY)
            editProgressValue = self.editSizeSlider.GetSliderValue()
            if editProgressValue != self.editProgressValue:
                self.editProgressValue = editProgressValue
                ctrl = self.GetBaseUIControl("/" + self.functionEditing)
                size = DEFAULT_PLAYER_DATA['func_{}_size'.format(self.functionEditing)] * mathUtil.GetSizeAmplifier(
                    editProgressValue)
                ctrl.SetSize((size, size), True)
                self.editCache["func_{}_size".format(self.functionEditing)] = size
            self.SendTip("当前选中§6[{}]".format(self.functions[self.functionEditing]['name']), "e", 0.2, False)

    def IsInCtrl(self, pos, ctrl):
        ctrlPos = ctrl.GetGlobalPosition()
        size = ctrl.GetSize()
        return ctrlPos[0] <= pos[0] <= ctrlPos[0] + size[0] and ctrlPos[1] <= pos[1] <= ctrlPos[1] + size[1]

    def ClickOutButtonWhileEditing(self, touchPos):
        if self.IsInCtrl(touchPos, self.GetBaseUIControl("/edit")):
            return
        for function in self.functions:
            ctrl = self.GetBaseUIControl("/" + function)
            size = ctrl.GetSize()[0]
            posX, posY = ctrl.GetGlobalPosition()
            if posX <= touchPos[0] <= posX + size and posY <= touchPos[1] <= posY + size:
                return
        self.functionEditing = None
        self.editSizeSlider.SetVisible(False)

    def Create(self):
        self.SetScreenVisible(False)

    isSelecting = False
    selectIndexTime = 0
    index = -1
    nowDrill = None

    def SetSelect(self, index=WHEEL_NUM):
        # index不填代表退出，index填负数代表不选
        self.deploySelectBaseCtrl.SetVisible(index < 0)
        self.deploySelectBarCtrl.SetVisible(0 <= index < len(DEPLOYMENT) and not self.nowDrill)
        for i in range(WHEEL_NUM):
            self.deploySelectCtrls[i].SetVisible(i == index)
            self.deployImgCtrls[i].SetVisible(self.isSelecting)
        self.deployAttributeCtrl.SetVisible(index < 0 or
                                            not self.nowDrill and 0 <= index < len(
            DEPLOYMENT) or self.nowDrill and 0 <= index < len(
            DEPLOYMENT[self.nowDrill]['deployment']))

        indexBefore = self.index
        if indexBefore != index:
            if index == -1 and not self.nowDrill:
                self.selectIndexTime = 0
            else:
                self.selectIndexTime = time.time()
            self.index = index
            if not self.nowDrill:
                if 0 <= index < len(DEPLOYMENT):
                    self.deployLabelCtrl.SetText(DEPLOYMENT.items()[index][1]['name'])
                    self.client.SwitchState("deploy_{}".format(DEPLOYMENT.items()[index][0]))
                else:
                    if len(DEPLOYMENT) <= index < WHEEL_NUM:
                        self.deployLabelCtrl.SetText("§7敬请期待")
                    elif index < 0:
                        self.deployLabelCtrl.SetText("§a请选择")
                    else:
                        self.deployLabelCtrl.SetText("§f改装")
                    self.client.SwitchState("idle")
            else:
                if 0 <= index < len(DEPLOYMENT[self.nowDrill]['deployment']):
                    self.deployLabelCtrl.SetText(DEPLOYMENT[self.nowDrill]['deployment'][index]['name'])
                    self.client.UpdateVar("deployment_{}".format(self.nowDrill), index)
                    self.RefreshAttribute(self.nowDrill, index)
                elif len(DEPLOYMENT[self.nowDrill]['deployment']) <= index < WHEEL_NUM:
                    self.deployLabelCtrl.SetText("§7敬请期待")
                    self.client.UpdateVar("deployment_{}".format(self.nowDrill),
                                          DeployHelper.Get(self.client.GetEquipment()['extraId'], self.nowDrill))
                elif index >= WHEEL_NUM:
                    self.deployLabelCtrl.SetText("§f改装")

    def CheckSelect(self):
        if not self.isSelecting: return
        btnSize = self.deployCtrl.GetSize()
        centerX, centerY = self.deployCtrl.GetGlobalPosition()[0] + btnSize[0] / 2.0, \
                           self.deployCtrl.GetGlobalPosition()[1] + btnSize[1] / 2.0
        touchX, touchY = clientApi.GetTouchPos()
        if pow(centerX - touchX, 2) + pow(centerY - touchY, 2) < pow(btnSize[0] / 2.0, 2):
            if self.nowDrill:
                self.ClickDownDeploy(None)
                self.client.RefreshDeployment(self.client.GetEquipment()['extraId'])
                self.RefreshAttribute()
            else:
                self.SetSelect(-1)
        else:
            if not self.nowDrill:
                if time.time() - self.selectIndexTime > CONFIRM_TIME and self.selectIndexTime != 0:
                    if self.index <= len(DEPLOYMENT):
                        self.nowDrill = DEPLOYMENT.items()[self.index][0]
                        for i in range(WHEEL_NUM):
                            if i < len(DEPLOYMENT[self.nowDrill]['deployment']):
                                self.deployImgCtrls[i].SetSprite(
                                    "textures/ui/{}/deploy/{}{}".format(mod_name, self.nowDrill, i))
                            else:
                                self.deployImgCtrls[i].SetSprite("textures/ui/icon_lock")
                    self.client.PlaySound("select_drill")
                    self.SetSelect(-1)
                    self.deployTipCtrl.SetText("§f沿着转盘外围拖动可选择\n触碰中心返回上一级")
                    return
                self.deploySelectBarCtrl.SetValue((time.time() - self.selectIndexTime) / CONFIRM_TIME)
            vec = (touchX - centerX, touchY - centerY)
            ref_angle = math.atan2(1, -1.732)
            vec_angle = math.atan2(-vec[1], vec[0])
            angle_diff = vec_angle - ref_angle
            if angle_diff < 0:
                angle_diff += 2 * math.pi
            angle_deg = math.degrees(angle_diff)
            index = int((360 - angle_deg) % 360 // 60)
            self.SetSelect(min(index, WHEEL_NUM - 1))

    def RefreshAttribute(self, previewDeploymentType=None, previewDeploymentIndex=None):
        originalContent = content = self.client.GetEquipment()['extraId']
        if previewDeploymentType:
            content = DeployHelper.Set(content, previewDeploymentType, previewDeploymentIndex)
        for attribute, value in ATTRIBUTE_TYPE.items():
            white = self.GetBaseUIControl("/deploy/attribute/{}/white".format(attribute)).asProgressBar()
            green = self.GetBaseUIControl("/deploy/attribute/{}/green".format(attribute)).asProgressBar()
            red = self.GetBaseUIControl("/deploy/attribute/{}/red".format(attribute)).asProgressBar()
            value = GetAttributeValue(attribute, originalContent)
            previewValue = GetAttributeValue(attribute, content)
            maxValue = float(ATTRIBUTE_TYPE[attribute]['max'])
            if not previewDeploymentType or value == previewValue:
                white.SetVisible(True)
                white.SetValue(value / maxValue)
                green.SetVisible(False)
                red.SetVisible(False)
            else:
                if value > previewValue:
                    white.SetVisible(True)
                    white.SetValue(previewValue / maxValue)
                    red.SetVisible(True)
                    red.SetValue(value / maxValue)
                    green.SetVisible(False)
                else:
                    white.SetVisible(True)
                    white.SetValue(value / maxValue)
                    green.SetVisible(True)
                    green.SetValue(previewValue / maxValue)
                    red.SetVisible(False)

    def SelectButtonWhileEditing(self, function):
        self.functionEditing = function
        if self.functionEditing == "deploy":
            self.editSizeSlider.SetVisible(False)
            return
        self.editSizeSlider.SetVisible(True)
        self.editVisibleToggle.SetVisible(True)
        self.editSizeSlider.SetSliderValue(
            mathUtil.GetSliderValueFromSize(
                self.editCache.get("func_{}_size".format(function), self.GetData("func_{}_size".format(function))),
                DEFAULT_PLAYER_DATA['func_{}_size'.format(function)]))

    def ClickButton(self, args):
        func = args['AddTouchEventParams']['func']
        if not self.GetBaseUIControl("/" + func).GetVisible():
            return
        if self.client.nowState == "edit_button":
            self.SelectButtonWhileEditing(func)
            return
        if self.isSelecting: return
        self.client.ClickButton(func)

    def ClickSettingsButton(self, args):
        if self.client.nowState == "edit_button":
            self.SelectButtonWhileEditing('settings')
            return
        self.updateTip.SetVisible(False)
        self.SetData("update_tip_{}".format(0), True)
        self.client.CallServer("TryToOpenSettings", clientApi.GetLocalPlayerId())

    def ClickDownDeploy(self, args):
        if self.client.nowState == "edit_button":
            self.SelectButtonWhileEditing('deploy')
            return
        self.isSelecting = True
        self.nowDrill = None
        self.RefreshAttribute()
        CF.CreateOperation(clientApi.GetLocalPlayerId()).SetCanDrag(False)
        self.SetSelect(-1)
        for i in range(WHEEL_NUM):
            if i < len(DEPLOYMENT):
                self.deployImgCtrls[i].SetSprite("textures/ui/{}/deploy/{}".format(mod_name, DEPLOYMENT.items()[i][0]))
            else:
                self.deployImgCtrls[i].SetSprite("textures/ui/icon_lock")
        self.deployTipCtrl.SetText("§f停留在指定的配件图标上")

    def ClickUpDeploy(self):
        if not self.isSelecting: return
        self.isSelecting = False
        if self.nowDrill:
            if self.index < len(DEPLOYMENT[self.nowDrill]['deployment']):
                if DeployHelper.Get(self.client.GetEquipment()['extraId'], self.nowDrill) == self.index:
                    self.SendTip("已经装上[{}]了".format(DEPLOYMENT[self.nowDrill]['deployment'][self.index]['name']),
                                 "e")
                    self.client.BackIdle(True)
                else:
                    self.client.PlaySound("deployed")
                    self.client.SwitchState("deployed", False)
            else:
                self.SendTip("这个配件尚不可用", "c")
                self.client.BackIdle(True)
        CF.CreateOperation(clientApi.GetLocalPlayerId()).SetCanDrag(True)
        self.SetSelect()
        self.deployTipCtrl.SetText("")

    deployCtrl = None
    deploySelectBarCtrl = None
    deployLabelCtrl = None
    deploySelectBaseCtrl = None
    deploySelectCtrls = []
    deployImgCtrls = []
    deployTipCtrl = None
    deployAttributeCtrl = None

    tipLabelCtrl = None
    tipDisabledTime = 0

    editSizeSlider = None

    droneInfoCtrl = None
    droneInfoNameCtrl = None
    droneInfoModelCtrl = None
    droneInfoHealthCtrl = None
    droneInfoBatteryCtrl = None

    controlPanelCtrl = None
    controlPanelLeftCtrl = None
    controlPanelRightCtrl = None
    controlPanelBatteryWarningCtrl = None

    chargeButtonLabelCtrl = None

    updateTip = None

    def Display(self, show):
        self.displaying = show
        if show:
            if not self.initialized:
                self.tipLabelCtrl = self.GetBaseUIControl("/info/tip").asLabel()

                for function in self.functions:
                    if "/{}/button_label".format(function) in self.GetAllChildrenPath("/{}".format(function)):
                        self.GetBaseUIControl("/{}".format(function)).asButton().SetButtonTouchDownCallback(
                            self.ClickButton)
                        self.GetBaseUIControl("/{}".format(function)).asButton().AddTouchEventParams(
                            {"func": function, "isSwallow": True})

                self.GetBaseUIControl("/settings").asButton().SetButtonTouchDownCallback(self.ClickSettingsButton)
                self.GetBaseUIControl("/settings").asButton().AddTouchEventParams({})

                self.deployCtrl = self.GetBaseUIControl("/deploy")
                self.GetBaseUIControl("/deploy/btn").asButton().SetButtonTouchDownCallback(self.ClickDownDeploy)
                self.GetBaseUIControl("/deploy/btn").asButton().AddTouchEventParams({})
                self.deployLabelCtrl = self.GetBaseUIControl("/deploy/btn/button_label").asLabel()
                self.deploySelectBarCtrl = self.GetBaseUIControl("/deploy/progress_bar").asProgressBar()
                self.deployTipCtrl = self.GetBaseUIControl("/deploy/tip").asLabel()

                self.editSizeSlider = self.GetBaseUIControl("/edit/size").asSlider()

                self.GetBaseUIControl("/edit").SetVisible(False)

                self.deploySelectBaseCtrl = self.GetBaseUIControl("/deploy/base")

                for i in range(WHEEL_NUM):
                    self.deploySelectCtrls.append(self.GetBaseUIControl("/deploy/select_" + str(i)))
                    self.deployImgCtrls.append(self.GetBaseUIControl("/deploy/img_" + str(i)).asImage())

                self.deployAttributeCtrl = self.GetBaseUIControl("/deploy/attribute")

                self.SetSelect()

                self.LoadButtons()
                self.RefreshButtonVisibility()

                self.updateTip = self.GetBaseUIControl("/settings/update_tip")
                self.updateTip.SetVisible(not self.GetData("update_tip_{}".format(0)))

                self.droneInfoCtrl = self.GetBaseUIControl("/drone_info")
                self.droneInfoCtrl.SetVisible(False)
                self.droneInfoNameCtrl = self.GetBaseUIControl("/drone_info/name").asLabel()
                self.droneInfoModelCtrl = self.GetBaseUIControl("/drone_info/model").asNeteasePaperDoll()
                self.droneInfoHealthCtrl = self.GetBaseUIControl("/drone_info/health").asProgressBar()
                self.droneInfoBatteryCtrl = self.GetBaseUIControl("/drone_info/battery").asProgressBar()

                self.controlPanelCtrl = self.GetBaseUIControl("/control_panel")
                self.controlPanelLeftCtrl = self.GetBaseUIControl("/control_panel/left").asLabel()
                self.controlPanelRightCtrl = self.GetBaseUIControl("/control_panel/right").asLabel()
                self.controlPanelBatteryWarningCtrl = self.GetBaseUIControl("/control_panel/battery_warning").asLabel()
                self.controlPanelCtrl.SetVisible(False)

                self.chargeButtonLabelCtrl = self.GetBaseUIControl("/charge/button_label").asLabel()

                self.initialized = True
        self.SetScreenVisible(show)

    def StartEditing(self):
        self.client.SwitchControl(False)
        self.GetBaseUIControl("/edit").SetVisible(True)
        for function in self.functions:
            ctrl = self.GetBaseUIControl('/' + function)
            ctrl.SetVisible(True)
        self.editSizeSlider.SetVisible(False)
        self.editVisibleToggle.SetVisible(False)

    def EndEditing(self):
        self.client.SwitchControl(True)
        self.functionEditing = None
        self.LoadButtons()
        self.editCache = {}
        self.GetBaseUIControl("/edit").SetVisible(False)
        self.client.RefreshDeployment(self.client.GetEquipment()['extraId'])

    functionEditing = None
    editCache = {}

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def ClickEditQuitButton(self, args):
        self.SendTip("放弃保存", "e")
        self.client.BackIdle(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def ClickEditSaveButton(self, args):
        for key, value in self.editCache.items():
            self.SetData(key, value)
        self.SendTip("保存成功！", "a")
        self.client.BackIdle(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def ClickEditResetButton(self, args):
        for key, value in DEFAULT_PLAYER_DATA.items():
            self.SetData(key, value)
        self.SendTip("已恢复默认！", "a")
        self.client.BackIdle(True)

    def LoadButtons(self):
        for function in self.functions:
            if "/{}/button_label".format(function) not in self.GetAllChildrenPath("/{}".format(function)):
                continue
            ctrl = self.GetBaseUIControl('/' + function)
            relativeX, relativeY = self.GetData('func_{}_pos'.format(function))
            screenX, screenY = CF.CreateGame(clientApi.GetLocalPlayerId()).GetScreenSize()
            size = self.GetData('func_{}_size'.format(function))
            if ctrl.GetAnchorTo() == "left_middle":
                parentX, parentY = 0, screenY / 2.0
            else:
                parentX, parentY = screenX - size, screenY / 2.0
            ctrl.SetPosition((parentX + relativeX, parentY + relativeY))
            ctrl.SetSize((size, size), True)
            labelCtrl = self.GetBaseUIControl('/' + function + "/button_label")
            if labelCtrl and self.functions[function]['name']:
                labelCtrl.asLabel().SetText(self.functions[function]['name'])

    def SendTip(self, tip, color, duration=2.0, cover=True):
        if not cover and self.tipLabelCtrl.GetText() and tip[:3] != self.tipLabelCtrl.GetText()[3:6]:
            return
        self.tipLabelCtrl.SetText("§" + color + tip)
        self.tipLabelCtrl.SetVisible(True)
        self.tipDisabledTime = time.time() + duration

    def GetData(self, key, default=None):
        return self.client.GetData(key, default)

    def SetData(self, key, value):
        self.client.SetData(key, value)
        self.client.CallServer("SetData", clientApi.GetLocalPlayerId(), key, value)
