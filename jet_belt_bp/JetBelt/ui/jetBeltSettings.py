# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi

from JetBelt.config import ModName

CF = clientApi.GetEngineCompFactory()
levelId = clientApi.GetLevelId()
ScreenNode = clientApi.GetScreenNodeCls()
PID = clientApi.GetLocalPlayerId()


class JetBeltSettings(ScreenNode):
    ViewBinder = clientApi.GetViewBinderCls()

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.playerId = clientApi.GetLocalPlayerId()

        self.mScrollingTouchContent = "/panel/scroll_view/scroll_touch/scroll_view/panel/background_and_viewport/scrolling_view_port/scrolling_content"
        self.mScrollingMouseContent = "/panel/scroll_view/scroll_mouse/scroll_view/stack_panel/background_and_viewport/scrolling_view_port/scrolling_content"

        self.mPermissionScrollingTouchContent = "/permission/scroll_view/scroll_touch/scroll_view/panel/background_and_viewport/scrolling_view_port/scrolling_content"
        self.mPermissionScrollingMouseContent = "/permission/scroll_view/scroll_mouse/scroll_view/stack_panel/background_and_viewport/scrolling_view_port/scrolling_content"

        self.mPermissionButtonLabel1Ctrl = None
        self.mPermissionButtonLabel2Ctrl = None

        self.enterValue = 0
        self.enterMinValue = 0
        self.enterMaxValue = 0
        self.mIsInitialized = False
        self.client = clientApi.GetSystem(ModName, "ClientSystem")

    def Create(self):
        self.GetBaseUIControl("/permission").SetVisible(True)  # 要先显示，否则下面获取不到
        self.mPermissionButtonLabel1Ctrl = self.GetBaseUIControl("/permission/button1/button_label").asLabel()
        self.mPermissionButtonLabel2Ctrl = self.GetBaseUIControl("/permission/button2/button_label").asLabel()
        self.Display(False)

    def Display(self, show):
        self.SetScreenVisible(show)
        if show:
            if not self.mIsInitialized:
                self.client.CallServer("InitializeUI", 0, PID)
        self.SetIsHud(not show)
        clientApi.HideHudGUI(show)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickCloseButton(self, args):
        self.Display(False)
        clientApi.PopScreen()

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickCloseEnterButton(self, args):
        self.GetBaseUIControl("/enter").SetVisible(False)
        self.GetBaseUIControl("/panel").SetVisible(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickClosePermissionButton(self, args):
        self.GetBaseUIControl("/permission").SetVisible(False)
        self.GetBaseUIControl("/panel").SetVisible(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickNumberButton(self, args):
        path = args["ButtonPath"]
        num = int(self.GetBaseUIControl(path + "/button_label").asLabel().GetText())
        new_value = num + self.enterValue * 10
        if new_value > 1000:
            return
        self.enterValue = new_value
        self.GetBaseUIControl("/enter/sub_bg/value").asLabel().SetText(
            ("当前输入:" if self.enterMinValue <= new_value <= self.enterMaxValue else "§c数值不当：") + str(
                self.enterValue))

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickReverseButton(self, args):
        self.enterValue = 0 if self.enterValue < 10 else self.enterValue // 10
        self.GetBaseUIControl("/enter/sub_bg/value").asLabel().SetText(
            ("当前输入:" if self.enterMinValue <= self.enterValue <= self.enterMaxValue else "§c数值不当：") + str(
                self.enterValue))

    def OpenEnterPanel(self, args):
        if "AddTouchEventParams" in args:
            args = args["AddTouchEventParams"]
        self.enterValue, self.enterMinValue, self.enterMaxValue = self.GetData(args["key"]), args["min"], args[
            "max"]
        self.GetBaseUIControl("/enter/title").asLabel().SetText(
            "请输入{}~{}的整数".format(self.enterMinValue, self.enterMaxValue))
        self.GetBaseUIControl("/enter/sub_bg/value").asLabel().SetText("当前输入:{}".format(self.enterValue))
        confirmBtnCtrl = self.GetBaseUIControl("/enter/sub_bg/button_confirm").asButton()
        confirmBtnCtrl.SetButtonTouchUpCallback(args["confirmFunction"])
        confirmBtnCtrl.AddTouchEventParams({})
        self.GetBaseUIControl("/panel").SetVisible(False)
        self.GetBaseUIControl("/enter").SetVisible(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickPermissionButton1(self, args):
        if "是" in self.mPermissionButtonLabel1Ctrl.GetText():
            self.SetData("auto_gain_permission", False, True)
            self.mPermissionButtonLabel1Ctrl.SetText(self.mPermissionButtonLabel1Ctrl.GetText().replace("§2是", "§4否"))
        else:
            self.SetData("auto_gain_permission", True, True)
            self.mPermissionButtonLabel1Ctrl.SetText(self.mPermissionButtonLabel1Ctrl.GetText().replace("§4否", "§2是"))

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def OnClickPermissionButton2(self, args):
        if "是" in self.mPermissionButtonLabel2Ctrl.GetText():
            self.SetData("sync_owner_settings", False, True)
            self.mPermissionButtonLabel2Ctrl.SetText(self.mPermissionButtonLabel2Ctrl.GetText().replace("§2是", "§4否"))
        else:
            self.SetData("sync_owner_settings", True, True)
            self.mPermissionButtonLabel2Ctrl.SetText(self.mPermissionButtonLabel2Ctrl.GetText().replace("§4否", "§2是"))
        self.client.CallServer("LoadDataForOthers", 0)

    def OpenPermissionPanel(self, onlinePlayers, permittedPlayers, autoGainPermission, syncOwnerSettings):
        if autoGainPermission:
            self.mPermissionButtonLabel1Ctrl.SetText(self.mPermissionButtonLabel1Ctrl.GetText().replace("§4否", "§2是"))
        if syncOwnerSettings:
            self.mPermissionButtonLabel2Ctrl.SetText(self.mPermissionButtonLabel2Ctrl.GetText().replace("§4否", "§2是"))
        scrollingContent = self.mPermissionScrollingTouchContent if "scroll_touch" in self.GetChildrenName(
            "/permission/scroll_view") else self.mPermissionScrollingMouseContent
        templatePath = scrollingContent + "/default"
        templatePermissionCtrl = self.GetBaseUIControl(templatePath)
        templateSize = templatePermissionCtrl.GetSize()
        for childPath in self.GetAllChildrenPath(scrollingContent):
            if not childPath.startswith(templatePath):
                self.RemoveComponent(childPath, scrollingContent)
        index = 1
        templatePermissionCtrl.SetVisible(True)  # 重新复制就要要重新显示，否则获取size都是0
        for onlinePlayerId, onlinePlayerName in onlinePlayers.items():
            self.Clone(templatePath, scrollingContent, onlinePlayerId)
            settingPath = scrollingContent + "/" + onlinePlayerId
            self.GetBaseUIControl(settingPath + "/description").asLabel().SetText(onlinePlayerName)
            toggleControl = self.GetBaseUIControl(settingPath + "/toggle").asButton()

            def toggle(worldData, settingPath=settingPath):
                # 这是一个闭包，所以settingPath和key会变成最后一次遍历时定义的样子，不能直接调用，下同
                if worldData:
                    default_img = "textures/ui/toggle_off"
                    hover_img = "textures/ui/toggle_off_hover"
                else:
                    default_img = "textures/ui/toggle_on"
                    hover_img = "textures/ui/toggle_on_hover"
                self.GetBaseUIControl(settingPath + "/toggle/default").asImage().SetSprite(default_img)
                self.GetBaseUIControl(settingPath + "/toggle/hover").asImage().SetSprite(hover_img)
                self.GetBaseUIControl(settingPath + "/toggle/pressed").asImage().SetSprite(default_img)

            def toggleCallback(args, onlinePlayer=onlinePlayerId, settingPath=settingPath):
                isPermitted = onlinePlayer in permittedPlayers
                toggle(isPermitted, settingPath)
                if isPermitted:
                    permittedPlayers.remove(onlinePlayer)
                else:
                    permittedPlayers.append(onlinePlayer)
                self.SetData("permitted_players", permittedPlayers, True)

            toggle(onlinePlayerId not in permittedPlayers)  # 偷个懒，欺骗以呈现到真实数据的状态
            toggleControl.SetButtonTouchUpCallback(toggleCallback)
            toggleControl.AddTouchEventParams({})
            toggleControl.SetVisible(True)
            pos = (0, (templateSize[1] + 2) * (index - 1))
            settingControl = self.GetBaseUIControl(settingPath)
            settingControl.SetPosition(pos)
            index += 1
        index -= 1

        # 模板复制完成，隐藏模板开关并调节滚动区域尺寸
        templatePermissionCtrl.SetVisible(False)
        scrollingContentControl = self.GetBaseUIControl(scrollingContent)
        scrollingContentControl.SetSize(
            (scrollingContentControl.GetSize()[0], templateSize[1] * index + 2 * (index - 1)))

        self.GetBaseUIControl("/panel").SetVisible(False)
        self.GetBaseUIControl("/permission").SetVisible(True)

    # 首次加载UI所执行的内容
    def InitializeUI(self, isOwner, defaultSettings):
        scrollingContent = self.mScrollingTouchContent if "scroll_touch" in self.GetChildrenName(
            "/panel/scroll_view") else self.mScrollingMouseContent
        templatePath = scrollingContent + "/default"
        templateSettingCtrl = self.GetBaseUIControl(templatePath)
        templateSize = templateSettingCtrl.GetSize()
        templateSettingCtrl.GetChildByName('toggle').SetVisible(False)
        templateSettingCtrl.GetChildByName('edit_box').SetVisible(False)
        index = 1
        for key, setting in defaultSettings:
            self.Clone(templatePath, scrollingContent, key)
            settingPath = scrollingContent + "/" + key
            self.GetBaseUIControl(settingPath + "/description").asLabel().SetText(setting["description"])
            if setting["type"] == "bool":
                toggleControl = self.GetBaseUIControl(settingPath + "/toggle").asButton()

                def toggle(playerData, settingPath=settingPath):
                    # 这是一个闭包，所以settingPath和key会变成最后一次遍历时定义的样子，不能直接调用，下同
                    if playerData:
                        default_img = "textures/ui/toggle_off"
                        hover_img = "textures/ui/toggle_off_hover"
                    else:
                        default_img = "textures/ui/toggle_on"
                        hover_img = "textures/ui/toggle_on_hover"
                    self.GetBaseUIControl(settingPath + "/toggle/default").asImage().SetSprite(default_img)
                    self.GetBaseUIControl(settingPath + "/toggle/hover").asImage().SetSprite(hover_img)
                    self.GetBaseUIControl(settingPath + "/toggle/pressed").asImage().SetSprite(default_img)

                def toggleCallback(args, settingPath=settingPath, key=key):
                    toggle(self.GetData(key), settingPath)
                    self.SetData(key, not self.GetData(key))

                toggle(not self.GetData(key))  # 偷个懒，欺骗以呈现到真实数据的状态
                toggleControl.SetButtonTouchUpCallback(toggleCallback)
                toggleControl.AddTouchEventParams({})
                toggleControl.SetVisible(True)
            elif setting["type"] == "int":
                editBoxCtrl = self.GetBaseUIControl(settingPath + "/edit_box").asButton()
                self.GetBaseUIControl(settingPath + "/edit_box/button_label").asLabel().SetText(
                    str(self.GetData(key)))
                editBoxCtrl.SetButtonTouchUpCallback(self.OpenEnterPanel)

                def confirmBtnCallback(args, settingPath=settingPath, key=key):
                    if not self.enterMinValue <= self.enterValue <= self.enterMaxValue:
                        return
                    self.GetBaseUIControl(settingPath + "/edit_box/button_label").asLabel().SetText(
                        str(self.enterValue))
                    self.GetBaseUIControl(
                        settingPath + "/edit_box/button_label").asLabel().GetText()
                    self.SetData(key, self.enterValue)
                    self.GetBaseUIControl("/enter").SetVisible(False)
                    self.GetBaseUIControl("/panel").SetVisible(True)

                editBoxCtrl.AddTouchEventParams(
                    {"playerId": PID, "key": key, "min": setting['range'][0],
                     "max": setting['range'][1], "confirmFunction": confirmBtnCallback})
                self.GetBaseUIControl(settingPath + "/edit_box").SetVisible(True)

            pos = (0, (templateSize[1] + 2) * (index - 1))
            settingControl = self.GetBaseUIControl(settingPath)
            settingControl.SetPosition(pos)
            index += 1
        index -= 1

        # 模板复制完成，隐藏模板开关并调节滚动区域尺寸
        templateSettingCtrl.SetVisible(False)
        self.GetBaseUIControl("/enter").SetVisible(False)
        self.GetBaseUIControl("/permission").SetVisible(False)
        permissionButtonCtrl = self.GetBaseUIControl("/panel/permission_button").asButton()
        if not isOwner:
            permissionButtonCtrl.SetVisible(False)
        else:
            def TryToOpenPermissionPanel(args):
                clientApi.GetSystem(ModName, "ClientSystem").CallServer("OpenPermissionPanel", 0, PID)

            permissionButtonCtrl.SetButtonTouchUpCallback(TryToOpenPermissionPanel)
            permissionButtonCtrl.AddTouchEventParams()
        scrollingContentControl = self.GetBaseUIControl(scrollingContent)
        scrollingContentControl.SetSize(
            (scrollingContentControl.GetSize()[0], templateSize[1] * index + 2 * (index - 1)))

        # 确认初始化完毕
        self.mIsInitialized = True

    def GetData(self, key):
        return self.client.GetData(key)

    def SetData(self, key, value, isWorldData=False):
        if not isWorldData:
            self.client.SetData(key, value)
        self.client.CallServer("SetData", 0, levelId if isWorldData else PID, key, value)
