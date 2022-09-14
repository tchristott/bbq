"""
Range of custom button classes based on wx.Panel.

Classes:
    AnalysisTabButton
    AssayTabButton
    MiniTabButton
    IconTabButton
    CustomBitmapButton
    TinyXButton
    InfoButton
    AssayButton

"""

import wx
import os
import lib_colourscheme as cs

class AnalysisTabButton(wx.Panel):

    """
    Custom class based on wx.Panel:

    Uses wx.Panel and wx.StaticText to create a tab button for the
    different analysis step tabs (e.g. "Assay Details", "Transfer
    and Data Files", "Results")
    """

    def __init__(self, parent, changetabowner, label, index):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. parent object in gui
            changetabowner ->
            label -> string. Label to display on button.
            index -> iteger. Index of button on button bar.
        """
        # To properly dimension the button we need to know how big the text is going to be, then add a few pixels to it.
        # Get size: https://stackoverflow.com/questions/14269880/the-right-way-to-find-the-size-of-text-in-wxpython
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString)
        dc = wx.ScreenDC()
        dc.SetFont(font)
        wide, tall = dc.GetTextExtent(label)
        wide += 15

        # Initialise the panel
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(wide,30),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        # Set properties
        self.Index = int(index)
        self.parent = parent
        self.changetabowner = changetabowner
        self.Label = label
        self.bol_Enabled = True
        self.Current = False
        self.FontSize = 10
        self.Highlit = False
        self.MouseOnText = False
        # Assign colours to properties
        self.ButtonBackgroundStandard = cs.BgMediumDark
        self.ButtonBackgroundCurrent = cs.BtnLightGrey
        self.ButtonBackgroundMouseOver = cs.BtnCurrent
        self.ButtonBackgroundButtonPressed = cs.BtnFocus
        self.FontColourEnabled = cs.White
        self.FontColourDisabled = cs.Black

        # Construct the actual button
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(wide,30),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Label = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Label = wx.StaticText(self.pnl_Button, label =  self.Label)
        self.lbl_Label.SetFont(wx.Font(self.FontSize,
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = wx.FONTWEIGHT_NORMAL,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        self.szr_Label.Add(self.lbl_Label, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        self.pnl_Button.SetSizer(self.szr_Label)
        self.pnl_Button.Layout()
        self.szr_Label.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button, 0, wx.ALL, 0)
        self.SetSizer(self.szr_Outside)
        self.Layout()
        self.szr_Outside.Fit(self)
        self.Layout()

        # Bind eventhandlers
        self.pnl_Button.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.lbl_Label.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)

        self.pnl_Button.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)
        self.lbl_Label.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)

        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_Label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_Label.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def IsCurrent(self, bol_Current):
        """
        Sets "Current" status of the button and changes background and
        font colour accordingly. A current button cannot be clicked and
        will not change colour when the mouse cursor moves over it.

        Arguments:
            bol_Current -> boolean. Is tab currently selected.
        """
        self.Current = bol_Current
        if self.Current == True:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundCurrent)
            weight = wx.FONTWEIGHT_BOLD
            self.lbl_Label.SetForegroundColour(self.FontColourDisabled)
            self.Current = True
        else:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
            weight = wx.FONTWEIGHT_NORMAL
            if self.bol_Enabled == True:
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
            else:
                self.lbl_Label.SetForegroundColour(self.FontColourDisabled)
        self.lbl_Label.SetFont(wx.Font(self.FontSize,
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = weight,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.Highlit = False
        self.Layout()
        self.Refresh()

    def IsEnabled(self, bol_Enabled):
        """
        Sets "enabled" status of the button and changes background
        and font colour accordingly. "bol_Enabled" is used as "Enabled"
        is already used by wxpython for all widgets.
        Arguments:
            bol_Enabled -> boolean. Enablement state of button.
        """
        self.bol_Enabled = bol_Enabled
        if self.bol_Enabled == True:
            if self.Current == False:
                self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
                self.Refresh()
        else:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
            self.lbl_Label.SetForegroundColour(self.FontColourDisabled)
            self.Refresh()

    def OnMouseOver(self, event):
        """
        Event handler for mouse cursor moving onto elements
        of the button. Changes appearance of button.
        """
        if self.Highlit == False:
            if self.bol_Enabled == True:
                if self.Current == False:
                    self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundMouseOver)
                    self.Refresh()
                    self.Highlit = True
            # Turn highlighting off for any other highlit button
            # (there should only be one, i.e. the previously highlit one)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].bol_Enabled == True:
                    if (not self.Group[key_Button].Current == True and
                        not self.Group[key_Button].Label == self.Label):
                        self.Group[key_Button].pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                        self.Group[key_Button].Refresh()
                        self.Group[key_Button].Highlit = False
        # If the EventObject is lbl_Label, we need to record this
        # for the OnMouseOff event handler.
        str_EventObject = str(type(event.GetEventObject()))
        if "StaticText" in str_EventObject:
            self.MouseOnText = True

    def OnMouseOff(self, event):
        """
        Event handler for mouse leaving the element.
        """
        # The static label (lbl_Label) cannot be set to be transparent for
        # the mouse, so we need to make sure that the button's background
        # colour does not revert to standard when the mouse moves from
        # pnl_Button to lbl_Label. We achieve this by checking what the
        # EventObject is. If it is the static text, we only set MouseOnText
        # to false. If it is the panel, we check whether MouseOnText is false.
        # Only then do we change the colour.
        if self.Current == False:
            str_EventObject = str(type(event.GetEventObject()))
            if "StaticText" in str_EventObject:
                self.MouseOnText = False
            elif "Panel" in str_EventObject:
                if self.MouseOnText == False:
                    self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                    self.Refresh()
                    self.Highlit = False

    def OnLeftDown(self, event):
        """
        Event handler for pressing of left mouse button
        """
        if self.bol_Enabled == True and self.Current == False:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundButtonPressed)
            self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler for fifting of left mouse button.
        """
        # If button is enabled, and not current, and the
        # notebook page with the same index as the button is
        # allowed to be selected, the notebook page will be
        # selected. The button's state is set to current and
        # all other buttons' states are set to not current.

        if self.bol_Enabled == True and self.Current == False:
            if self.changetabowner.ChangeTab(self) == True:
                self.IsCurrent(True)
                self.Notebook.SetSelection(self.Index)
                for key_Button in self.Group.keys():
                    if self.Group[key_Button].Index != self.Index:
                        self.Group[key_Button].IsCurrent(False)
                        self.Group[key_Button].Highlit = False

class AssayTabButton(wx.Panel):
    """
    Custom class based on wx.Panel:

    Uses wx.Panel and wx.StaticText to create a tab button
    for different simplebook type notebooks.
    """
    def __init__(self, parent, label, index):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object in gui.
            label -> string. Label to be displayed on button
            index -> integer. Index of button in its group.
        """
        # To properly dimension the button we need to know how big the text is going to be, then add a few pixels to it.
        # Get size: https://stackoverflow.com/questions/14269880/the-right-way-to-find-the-size-of-text-in-wxpython
        font = wx.Font(10, family = wx.FONTFAMILY_DEFAULT,
                           style = wx.FONTSTYLE_NORMAL,
                           weight = wx.FONTWEIGHT_BOLD,
                           underline = False,
                           faceName = wx.EmptyString)
        dc = wx.ScreenDC()
        dc.SetFont(font)
        wide, tall = dc.GetTextExtent(label)
        wide += 15
        # Initialise wx.Panel
        wx.Panel.__init__ (self, parent = parent,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.Size(wide,30),
                           style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)
        # Set properties
        self.Index = int(index)
        self.parent = parent
        self.Label = label
        self.bol_Enabled = True
        self.Current = False
        self.FontSize = 10
        self.Highlit = False
        self.MouseOnText = False
        # Assign colours to properties
        self.ButtonBackgroundStandard = cs.BgMediumDark
        self.ButtonBackgroundCurrent = cs.BtnLightGrey
        self.ButtonBackgroundMouseOver = cs.BtnCurrent
        self.ButtonBackgroundButtonPressed = cs.BtnFocus
        self.FontColourEnabled = cs.White
        self.FontColourDisabled = cs.Black

        # Construct the button:
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(wide,30),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Label = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Label = wx.StaticText(self.pnl_Button, label = self.Label)
        self.lbl_Label.SetFont(wx.Font(self.FontSize,
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = wx.FONTWEIGHT_NORMAL,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        self.szr_Label.Add(self.lbl_Label, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        self.pnl_Bar = wx.Panel(self.pnl_Button, wx.ID_ANY, wx.DefaultPosition, size = wx.Size(wide-5,2), style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Label.Add(self.pnl_Bar, 1, wx.ALIGN_CENTER|wx.ALL, 0)
        self.pnl_Button.SetSizer(self.szr_Label)
        self.pnl_Button.Layout()
        self.szr_Label.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button, 0, wx.ALL, 0)
        self.SetSizer(self.szr_Outside)
        self.Layout()
        self.szr_Outside.Fit(self)
        self.Layout()

        # Bind event handlers
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.pnl_Button.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.lbl_Label.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)

        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)
        self.pnl_Button.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)
        self.lbl_Label.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.pnl_Bar.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_Label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.pnl_Bar.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_Label.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def IsCurrent(self, bol_Current):
        """
        Sets "Current" status of the button.
        
        Changes appaerance and behaviour: A current button cannot
        be clicked and will not change colour when the mouse cursor 
        moves over it.
        """
        self.Current = bol_Current
        if self.Current == True:
            self.pnl_Bar.SetBackgroundColour(cs.White)
            self.lbl_Label.SetFont(wx.Font(self.FontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString))
            self.Current = True
        else:
            self.pnl_Bar.SetBackgroundColour(cs.BgMediumDark)
            self.lbl_Label.SetFont(wx.Font(self.FontSize, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, wx.EmptyString))
            self.Current = False
        self.Highlit = False
        self.Layout()
        self.Refresh()

    def IsEnabled(self, bol_Enabled):
        """
        Sets "enabled" status of the button and changes appearance.

        Arguments:
            bol_Enabled -> boolean. Enablement status of button.
        """
        self.bol_Enabled = bol_Enabled
        if self.bol_Enabled == True:
            if self.Current == False:
                self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        else:
            self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
            self.lbl_Label.SetForegroundColour(self.FontColourDisabled)

    def OnMouseOver(self, event):
        """
        Event handler for mouse cursor moving onto elements of the button.
        Changes appearance.
        """
        if self.Highlit == False:
            if self.bol_Enabled == True:
                if self.Current == False:
                    self.pnl_Bar.SetBackgroundColour(cs.BgLight)
                    self.Refresh()
                    self.Highlit = True
            # Turn highlighting off for any other highlit button
            # (there should only be one, i.e. the previously highlit one)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].bol_Enabled == True:
                    if not self.Group[key_Button].Current == True and not self.Group[key_Button].Label == self.Label:
                        self.Group[key_Button].pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                        self.Group[key_Button].Refresh()
                        self.Group[key_Button].Highlit = False
        # If the EventObject is lbl_Label, we need to record this for the OnMouseOff event handler.
        str_EventObject = str(type(event.GetEventObject()))
        if "StaticText" in str_EventObject:
            self.MouseOnText = True

    def OnMouseOff(self, event):
        """
        Event handler for mouse leaving the element.
        """
        if self.Current == False:
            str_EventObject = str(type(event.GetEventObject()))
            if "StaticText" in str_EventObject:
                self.MouseOnText = False
            elif "Panel" in str_EventObject:
                if self.MouseOnText == False:
                    self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                    self.Refresh()
                    self.Highlit = False

    def OnLeftDown(self, event):
        """
        Event handler for pressing of left mouse button.
        """
        if self.bol_Enabled == True and self.Current == False:
            self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler for fifting of left mouse button.
        """
        if self.bol_Enabled == True and self.Current == False:
            self.IsCurrent(True)
            self.Notebook.SetSelection(self.Index)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].Index != self.Index:
                    self.Group[key_Button].IsCurrent(False)
                    self.Group[key_Button].Highlit = False

class MiniTabButton(wx.Panel):

    """
    Custom class based on wx.Panel:

    Uses wx.Panel and wx.StaticText to create a tab button for the
    Tabs in a small simplebook for dialog boxes.
    """

    def __init__(self, parent, changetabowner, label, index):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. parent object in gui
            changetabowner ->
            label -> string. Label to display on button.
            index -> iteger. Index of button on button bar.
        """
        # To properly dimension the button we need to know how big the text is going to be, then add a few pixels to it.
        # Get size: https://stackoverflow.com/questions/14269880/the-right-way-to-find-the-size-of-text-in-wxpython
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString)
        dc = wx.ScreenDC()
        dc.SetFont(font)
        wide, tall = dc.GetTextExtent(label)
        wide += 15

        # Initialise the panel
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(wide,25),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        # Set properties
        self.Index = int(index)
        self.parent = parent
        self.changetabowner = changetabowner
        self.Label = label
        self.bol_Enabled = True
        self.Current = False
        self.FontSize = 10
        self.Highlit = False
        self.MouseOnText = False
        # Assign colours to properties
        self.ButtonBackgroundStandard = cs.BgMedium
        self.ButtonBackgroundCurrent = cs.BgLight
        self.ButtonBackgroundMouseOver = cs.BgUltraLight
        self.ButtonBackgroundButtonPressed = cs.BgLight
        self.FontColourEnabled = cs.BgUltraDark
        self.FontColourCurrent = cs.Black
        self.FontColourDisabled = cs.BgLight

        # Construct the actual button
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(wide,30),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Label = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Label = wx.StaticText(self.pnl_Button, label =  self.Label)
        self.lbl_Label.SetFont(wx.Font(self.FontSize,
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = wx.FONTWEIGHT_NORMAL,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        self.szr_Label.Add(self.lbl_Label, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        self.pnl_Button.SetSizer(self.szr_Label)
        self.pnl_Button.Layout()
        self.szr_Label.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button, 0, wx.ALL, 0)
        self.SetSizer(self.szr_Outside)
        self.Layout()
        self.szr_Outside.Fit(self)
        self.Layout()

        # Bind eventhandlers
        self.pnl_Button.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.lbl_Label.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)

        self.pnl_Button.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)
        self.lbl_Label.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOff)

        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_Label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_Label.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def IsCurrent(self, bol_Current):
        """
        Sets "Current" status of the button and changes background and
        font colour accordingly. A current button cannot be clicked and
        will not change colour when the mouse cursor moves over it.

        Arguments:
            bol_Current -> boolean. Is tab currently selected.
        """
        self.Current = bol_Current
        if self.Current == True:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundCurrent)
            weight = wx.FONTWEIGHT_BOLD
            self.lbl_Label.SetForegroundColour(self.FontColourCurrent)
            self.Current = True
        else:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
            weight = wx.FONTWEIGHT_NORMAL
            if self.bol_Enabled == True:
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
            else:
                self.lbl_Label.SetForegroundColour(self.FontColourDisabled)
        self.lbl_Label.SetFont(wx.Font(self.FontSize,
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = weight,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.Highlit = False
        self.Layout()
        self.Refresh()

    def IsEnabled(self, bol_Enabled):
        """
        Sets "enabled" status of the button and changes background
        and font colour accordingly. "bol_Enabled" is used as "Enabled"
        is already used by wxpython for all widgets.
        Arguments:
            bol_Enabled -> boolean. Enablement state of button.
        """
        self.bol_Enabled = bol_Enabled
        if self.bol_Enabled == True:
            if self.Current == False:
                self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
                self.Refresh()
        else:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
            self.lbl_Label.SetForegroundColour(self.FontColourDisabled)
            self.Refresh()

    def OnMouseOver(self, event):
        """
        Event handler for mouse cursor moving onto elements
        of the button. Changes appearance of button.
        """
        if self.Highlit == False:
            if self.bol_Enabled == True:
                if self.Current == False:
                    self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundMouseOver)
                    self.Refresh()
                    self.Highlit = True
            # Turn highlighting off for any other highlit button
            # (there should only be one, i.e. the previously highlit one)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].bol_Enabled == True:
                    if (not self.Group[key_Button].Current == True and
                        not self.Group[key_Button].Label == self.Label):
                        self.Group[key_Button].pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                        self.Group[key_Button].Refresh()
                        self.Group[key_Button].Highlit = False
        # If the EventObject is lbl_Label, we need to record this
        # for the OnMouseOff event handler.
        str_EventObject = str(type(event.GetEventObject()))
        if "StaticText" in str_EventObject:
            self.MouseOnText = True

    def OnMouseOff(self, event):
        """
        Event handler for mouse leaving the element.
        """
        # The static label (lbl_Label) cannot be set to be transparent for
        # the mouse, so we need to make sure that the button's background
        # colour does not revert to standard when the mouse moves from
        # pnl_Button to lbl_Label. We achieve this by checking what the
        # EventObject is. If it is the static text, we only set MouseOnText
        # to false. If it is the panel, we check whether MouseOnText is false.
        # Only then do we change the colour.
        if self.Current == False:
            str_EventObject = str(type(event.GetEventObject()))
            if "StaticText" in str_EventObject:
                self.MouseOnText = False
            elif "Panel" in str_EventObject:
                if self.MouseOnText == False:
                    self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
                    self.Refresh()
                    self.Highlit = False

    def OnLeftDown(self, event):
        """
        Event handler for pressing of left mouse button
        """
        if self.bol_Enabled == True and self.Current == False:
            self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundButtonPressed)
            self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler for fifting of left mouse button.
        """
        # If button is enabled, and not current, and the
        # notebook page with the same index as the button is
        # allowed to be selected, the notebook page will be
        # selected. The button's state is set to current and
        # all other buttons' states are set to not current.

        if self.bol_Enabled == True and self.Current == False:
            if self.changetabowner.ChangeTab(self) == True:
                self.IsCurrent(True)
                self.Notebook.SetSelection(self.Index)
                for key_Button in self.Group.keys():
                    if self.Group[key_Button].Index != self.Index:
                        self.Group[key_Button].IsCurrent(False)
                        self.Group[key_Button].Highlit = False

class IconTabButton(wx.BitmapButton):
    """
    Custom class based on wx.Panel:

    Uses wx.Panel and wx.StaticText to create a tab button for different simplebook type notebooks.
    """
    def __init__(self, parent, label, index, path = None):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object in gui.
            label -> string. Label to be displayed on button
            index -> integer. Index of button in its group.
            path -> string. Path where image file is located.
        """
        # To properly dimension the button we need to know how big the text is going to be,
        # then add a few pixels to it for space around the
        # text (15) and between text and image (5), and the image size itself (16) -> 36
        # Get size: https://stackoverflow.com/questions/14269880/the-right-way-to-find-the-size-of-text-in-wxpython
        font = wx.Font(10, family = wx.FONTFAMILY_DEFAULT, 
                       style = wx.FONTSTYLE_NORMAL,
                       weight = wx.FONTWEIGHT_BOLD,
                       underline = False,
                       faceName = wx.EmptyString)
        dc = wx.ScreenDC()
        dc.SetFont(font)
        wide, tall = dc.GetTextExtent(label)
        if not path == None: 
            wide += 36
        else:
            wide += 15
        # Initialise wx.Panel
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(wide,30),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        # Set properties
        self.Path = path
        self.Index = int(index)
        self.parent = parent
        self.Label = label
        self.bol_Enabled = True
        self.Current = False
        self.FontSize = 10
        self.Highlit = False
        self.MouseOnText = False
        # Assign colours to properties
        self.ButtonBackgroundStandard = cs.BtnLightGrey
        self.ButtonBackgroundCurrent = cs.BtnLightGrey
        self.ButtonBackgroundMouseOver = cs.BtnCurrent
        self.ButtonBackgroundButtonPressed = cs.BtnFocus
        self.FontColourEnabled = cs.Black
        self.FontColourDisabled = cs.White

        # Construct the button:
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(wide,30),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Button = wx.BoxSizer(wx.VERTICAL)
        self.szr_Label = wx.BoxSizer(wx.HORIZONTAL)
        # Only add image if a path is specified
        if not self.Path == None:
            self.ImagePath = os.path.join(self.Path, "tab_" + self.Label.replace(" ", "") + ".png")
            self.bmp_Logo = wx.StaticBitmap(self.pnl_Button,
                                            bitmap = wx.Bitmap(self.ImagePath, wx.BITMAP_TYPE_ANY),
                                            size = wx.Size(16,16))
            self.szr_Label.Add(self.bmp_Logo, 0, wx.ALL, 0)
            self.szr_Label.Add((5,5),1,wx.ALL,0)
        self.lbl_Label = wx.StaticText(self.pnl_Button, label = self.Label)
        self.lbl_Label.SetFont(wx.Font(self.FontSize, family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = wx.FONTWEIGHT_NORMAL,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        self.szr_Label.Add(self.lbl_Label, 0, wx.ALL, 0)
        self.szr_Button.Add(self.szr_Label, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.pnl_Bar = wx.Panel(self.pnl_Button, size = wx.Size(wide-5,2),
                                style = wx.TAB_TRAVERSAL)
        self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
        self.szr_Button.Add(self.pnl_Bar, 1, wx.ALIGN_CENTER|wx.ALL, 0)
        self.pnl_Button.SetSizer(self.szr_Button)
        self.pnl_Button.Layout()
        self.szr_Label.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button, 0, wx.ALL, 0)
        self.SetSizer(self.szr_Outside)
        self.Layout()
        self.szr_Outside.Fit(self)
        self.Layout()

        # Bind event handlers
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.pnl_Bar.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_Label.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.pnl_Bar.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_Label.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def IsCurrent(self, bol_Current):
        """
        Sets "Current" status of the button and changes appearance and
        behaviour.

        Arguments:
            bol_Current -> boolean. Is button's notebook tab currently
                            selected?
        """
        self.Current = bol_Current
        if self.Current == True:
            self.pnl_Bar.SetBackgroundColour(cs.BgMediumDark)
            weight = wx.FONTWEIGHT_BOLD
            self.Current = True
        else:
            self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
            weight = wx.FONTWEIGHT_NORMAL
            self.Current = False
        self.lbl_Label.SetFont(wx.Font(self.FontSize, 
                                       family = wx.FONTFAMILY_DEFAULT,
                                       style = wx.FONTSTYLE_NORMAL,
                                       weight = weight,
                                       underline = False,
                                       faceName = wx.EmptyString))
        self.Highlit = False
        self.pnl_Button.Layout()
        self.Layout()
        self.Refresh()

    def IsEnabled(self, bol_Enabled):
        """
        Sets "enabled" status of the button and changes appearance.
        """
        self.bol_Enabled = bol_Enabled
        if self.bol_Enabled == True:
            if self.Current == False:
                self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                self.lbl_Label.SetForegroundColour(self.FontColourEnabled)
        else:
            self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
            self.lbl_Label.SetForegroundColour(self.FontColourDisabled)

    def OnMouseOver(self, event):
        """
        Event handler for mouse cursor moving onto elements of the button.
        """
        if self.Highlit == False:
            if self.bol_Enabled == True:
                if self.Current == False:
                    self.pnl_Bar.SetBackgroundColour(cs.BgMediumDark)
                    self.Refresh()
                    self.Highlit = True
            # Turn highlighting off for any other highlit button (there should
            # only be one, i.e. the previously highlit one)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].bol_Enabled == True:
                    if (not self.Group[key_Button].Current == True and
                        not self.Group[key_Button].Label == self.Label):
                        self.Group[key_Button].pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                        self.Group[key_Button].Refresh()
                        self.Group[key_Button].Highlit = False
        # If the EventObject is lbl_Label, we need to record this for
        # the OnMouseOff event handler.
        str_EventObject = str(type(event.GetEventObject()))
        if "StaticText" in str_EventObject:
            self.MouseOnText = True

    def OnMouseOff(self, event):
        """
        Event handler for mouse leaving the element.
        """
        if self.Current == False:
            str_EventObject = str(type(event.GetEventObject()))
            if "StaticText" in str_EventObject:
                self.MouseOnText = False
            elif "Panel" in str_EventObject:
                if self.MouseOnText == False:
                    self.pnl_Bar.SetBackgroundColour(self.ButtonBackgroundStandard)
                    self.Refresh()
                    self.Highlit = False

    def OnLeftDown(self, event):
        """
        Event handler for pressing of left mouse button.
        """
        if self.bol_Enabled == True and self.Current == False:
            self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler for fifting of left mouse button.
        """
        if self.bol_Enabled == True and self.Current == False:
            self.IsCurrent(True)
            self.Notebook.SetSelection(self.Index)
            for key_Button in self.Group.keys():
                if self.Group[key_Button].Index != self.Index:
                    self.Group[key_Button].IsCurrent(False)
                    self.Group[key_Button].Highlit = False

class CustomBitmapButton(wx.BitmapButton):
    """
    Wrapper class for wx.BitmapButton tp simplify creation.
    
    A base name and the location of the image files are given and the bitmaps
    for the wx.BitmapButton are generated dynamically.
    """
    def __init__(self, parent, type, index, size, pathaddendum = None, tooltip = None):
        wx.BitmapButton.__init__(self, parent = parent, id = wx.ID_ANY,
                                 bitmap = wx.NullBitmap, pos = wx.DefaultPosition,
                                 size = wx.Size(size[0],size[1]))
        self.Type = type
        self.Path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "buttons")
        if not pathaddendum == None:
            self.Path = os.path.join(self.Path, pathaddendum)
        self.Index = index
        self.parent = parent
        self.SetMinSize(wx.Size(size[0],size[1]))
        self.SetBitmap(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                 + r".png", wx.BITMAP_TYPE_ANY))
        self.SetBitmapCurrent(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                        + r"_current.png", wx.BITMAP_TYPE_ANY))
        self.SetBitmapDisabled(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                         + r"_disabled.png", wx.BITMAP_TYPE_ANY))
        self.SetBitmapFocus(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                      + r"_focus.png", wx.BITMAP_TYPE_ANY))
        self.SetBitmapPressed(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                        + r"_pressed.png", wx.BITMAP_TYPE_ANY))
        if not tooltip == None:
            self.SetToolTip(tooltip)

    def IsCurrent(self, bol_Current):
        if bol_Current == True:
            self.SetBitmapDisabled(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                             + r"_active.png", wx.BITMAP_TYPE_ANY))
        else:
            self.SetBitmapDisabled(wx.Bitmap(self.Path + r"\btn_" + self.Type
                                             + r"_disabled.png", wx.BITMAP_TYPE_ANY))
        self.Enable(not bol_Current)

class TinyXButton(CustomBitmapButton):
    """
    Special case of CustomBitmaptButton: Tiny "x" button to close dialog windows.
    """
    def __init__(self, parent):
        self.dir_Path = os.path.dirname(os.path.realpath(__file__))
        CustomBitmapButton.__init__(self, parent = parent, type="tiny_x",
                                    index = 0, size = (13,13),
                                    pathaddendum = u"titlebar", tooltip="Close")

class InfoButton(CustomBitmapButton):
    """
    Special case of CustomBitmaptButton: "?" button for hints.
    """
    def __init__(self, parent, brightness, tooltip):
        self.dir_Path = os.path.dirname(os.path.realpath(__file__))
        CustomBitmapButton.__init__(self, parent = parent, type = "Info"+brightness,
                                    index = 0, size = (15,15),
                                    pathaddendum = None, tooltip = tooltip)

class AssayButton(wx.Panel):
    """
    Custom "button" for assay selection.

    Uses wx.Panel. wx.BoxSizer and wx.StaticBitmap to create a button-like element.
    """
    def __init__(self, parent, assaypath, shorthand, index, label, mainframe, group):
        """
        Arguments:
            parent -> wx object. Parent object in gui.
            path -> string. location of image file;
            shorthand -> string. Shorthand code of the assay.
            index -> integer. Index of the button in its group.
            label -> string. Label that will be displayed;
            mainframe -> wx object. Main wx.Frame of the application.
            group -> dictionary. Group of buttons this button belongs to.
        """
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(220,160),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)
        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.parent = parent
        self.Label = label
        self.Path = assaypath
        self.mainframe = mainframe
        self.Index = index
        self.Highlit = False
        self.shorthand = shorthand
        self.Group = group

        # Construct button
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(220,160), style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetForegroundColour(cs.White)
        self.szr_Button = wx.BoxSizer(wx.VERTICAL)
        self.szr_Button.Add((220,10),0,wx.ALL,0)
        self.bmp_Assay = wx.StaticBitmap(self.pnl_Button,
                                         bitmap = wx.Bitmap(self.Path + r"\button.png", wx.BITMAP_TYPE_ANY), 
                                         size = wx.Size(190,109))
        self.szr_Button.Add(self.bmp_Assay, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        self.lbl_AssayName = wx.StaticText(self.pnl_Button, label = self.Label, style = 5)
        self.lbl_AssayName.SetFont(wx.Font(10, family =wx.FONTFAMILY_DEFAULT,
                                           style = wx.FONTSTYLE_NORMAL,
                                           weight =wx.FONTWEIGHT_NORMAL,
                                           underline = False,
                                           faceName = wx.EmptyString))
        self.lbl_AssayName.Wrap(200)
        self.szr_Button.Add(self.lbl_AssayName, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 0)
        self.pnl_Button.SetSizer(self.szr_Button)
        self.pnl_Button.Layout()
        self.szr_Button.Fit(self.pnl_Button)

        self.szr_Outside.Add(self.pnl_Button, 0, wx.ALL, 0)
        self.SetSizer(self.szr_Outside)
        self.Layout()
        self.szr_Outside.Fit(self)

        # Binding event handlers
        self.pnl_Button.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.bmp_Assay.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        self.lbl_AssayName.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseOver)
        
        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.bmp_Assay.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_AssayName.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.bmp_Assay.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_AssayName.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

    def OnMouseOver(self, event):
        """
        Event handler for mouse over. Changes appearance.
        """
        if self.Highlit == False:
            self.pnl_Button.SetBackgroundColour(cs.BgDark)
            self.Refresh()
            for assay in self.Group.keys():
                if not self.Group[assay].shorthand == self.shorthand:
                    self.Group[assay].Standard()
            self.Highlit = True

    def Standard(self):
        """
        Resets appearance from highlighted (mouse over) to standard.
        """
        if self.Highlit == True:
            self.pnl_Button.SetBackgroundColour(cs.BgMediumDark)
            self.Highlit = False
            self.Refresh()

    def OnLeftDown(self, event):
        """
        Event handler for left mouse down. Changes appearance.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgUltraDark)
        self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler for left mouse up.
        Changes appearance, starts associated new project.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgDark)

        self.Refresh()
        self.mainframe.StartNewProject(None, self.shorthand)