"""
Contains all necessary classes and functions for the application's
home screen

Classes:
    FileList
    FileEntry
    FileEntryContextMenu
    ChangePinnedAssay
    HomeScreen
    pnl_Projects

"""

# Import my own libraries
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_custombuttons as btn

# Import libraries for GUI
import wx
import wx.xrc

# Import other libraries
import pandas as pd
import numpy as np
import os
from pathlib import Path
import datetime

####################################################################
##                                                                ##
##    ######  ##  ##      ######    ##      ##   #####  ######    ##
##    ##      ##  ##      ##        ##      ##  ##        ##      ##
##    ####    ##  ##      ####      ##      ##   ####     ##      ##
##    ##      ##  ##      ##        ##      ##      ##    ##      ##
##    ##      ##  ######  ######    ######  ##  #####     ##      ##
##                                                                ##
####################################################################

class FileList(wx.ScrolledWindow):
    """
    List of most recent files to be displayed on home screen.
    Derived from class wx.ScrolledWindow.
    """
    def __init__(self, parent):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
        """
        wx.ScrolledWindow.__init__ (self, parent = parent, id = wx.ID_ANY,
                                    pos = wx.DefaultPosition, size = wx.Size(910,331),
                                    style = wx.TAB_TRAVERSAL|wx.VSCROLL, name = wx.EmptyString)
        self.parent = parent
        self.SetMinSize(wx.Size(910,331))
        self.SetScrollRate(5, 5)
        self.SetBackgroundColour(cs.BgMediumDark)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Line = wx.Panel(self, size = wx.Size(890,1), style = wx.TAB_TRAVERSAL)
        self.pnl_Line.SetBackgroundColour(cs.White)
        self.szr_Surround.Add(self.pnl_Line,0,wx.ALL,0)
        self.SetSizer(self.szr_Surround)
        self.family = {}

    def AddFileEntry(self, index, lst_Recent):
        """
        Adds entry to file list.

        Arguments:
            index -> int. Index of the item to be added
            lst_Recent -> list of arguments to be used with file entry.
        """
        self.family[index] = FileEntry(self, index = index,
                                       FileName = lst_Recent[0],
                                       FilePath = lst_Recent[3],
                                       FileDate = lst_Recent[4],
                                       Shorthand = lst_Recent[2])
        self.szr_Surround.Add(self.family[index],0,wx.ALL,0)
        self.Layout()

    def DeleteAllItems(self):
        """
        Removes all file entries from list.
        """
        for entry in self.family:
            self.family[entry].Destroy()
        self.family = {}
        self.Layout()

class FileEntry(wx.Panel):
    """
    Entry for file list.
    """
    def __init__(self, parent, index, FileName, FilePath, FileDate, Shorthand):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            index -> integer. Index of this entry in the file list
            FileName -> string. Actual file name
            FilePath -> string. Full path
            FileDate -> string. Date file was last accessed by BBQ
            Shorthand -> string. Shorthand assay identifier
        """
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.Size(890,66),
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.parent = parent
        self.index = index
        self.FileName = FileName
        self.FilePath = FilePath
        self.FileDate = FileDate
        
        # Find assay icon:
        try:
            self.AssayIcon = os.path.join(self.parent.parent.MainFrame.dfr_Assays.loc[Shorthand,"Subdirectory"],
                             "icn_" + Shorthand + ".png")
        except:
            # No category default, PHDR = PlaceHolDeR
            self.AssayIcon = self.parent.parent.MainFrame.dir_Path + r"\other\icn_PHDR.png"

        # Start building the entry:
        self.szr_Outside = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Button = wx.Panel(self, size = wx.Size(890,65), style = wx.TAB_TRAVERSAL)
        self.pnl_Button.SetBackgroundColour(cs.BgDark)
        self.szr_Inside = wx.BoxSizer(wx.HORIZONTAL)
        self.bmp_Icon = wx.StaticBitmap(self, bitmap = wx.Bitmap(self.AssayIcon,
                                                                 wx.BITMAP_TYPE_ANY))
        self.bmp_Icon.SetBackgroundColour(cs.BgDark)
        self.szr_Inside.Add(self.bmp_Icon, 0, wx.ALL, 5)
        self.szr_Properties = wx.BoxSizer(wx.VERTICAL)
        self.szr_Properties.Add((800,5),0,wx.ALL,0)
        self.szr_TopHalf = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_FileName = wx.StaticText(self, label = self.FileName, size = wx.Size(685,-1))
        self.lbl_FileName.SetFont(wx.Font(14, family = wx.FONTFAMILY_DEFAULT,
                                              style = wx.FONTSTYLE_NORMAL,
                                              weight = wx.FONTWEIGHT_NORMAL,
                                              underline = False,
                                              faceName = wx.EmptyString))
        self.szr_TopHalf.Add(self.lbl_FileName,0,wx.ALL,2)
        self.lbl_FileDate = wx.StaticText(self, label = u"Last edited: "
                                          + self.FileDate[0:10],
                                          size = wx.Size(141,-1))
        self.szr_TopHalf.Add(self.lbl_FileDate,0,wx.ALL,2)
        self.szr_Properties.Add(self.szr_TopHalf,0,wx.ALL,2)
        self.lbl_FilePath = wx.StaticText(self, label = self.FilePath)
        self.szr_Properties.Add(self.lbl_FilePath,0,wx.ALL,2)
        self.szr_Inside.Add(self.szr_Properties,0,wx.ALL,0)
        self.pnl_Button.SetSizer(self.szr_Inside)
        self.pnl_Button.Layout()
        self.szr_Inside.Fit(self.pnl_Button)
        self.szr_Outside.Add(self.pnl_Button,0,wx.ALL,0)
        self.pnl_Line = wx.Panel(self, size = wx.Size(895,1), style = wx.TAB_TRAVERSAL)
        self.pnl_Line.SetBackgroundColour(cs.White)
        self.szr_Outside.Add(self.pnl_Line,0,wx.ALL,0)
        self.SetSizer(self.szr_Outside)
        self.Layout()

        ####  # #   # ####  # #   #  ####
        #   # # ##  # #   # # ##  # #  
        ####  # ##### #   # # ##### #  ##
        #   # # #  ## #   # # #  ## #   #
        ####  # #   # ####  # #   #  ###  ###############################################

        self.pnl_Button.Bind(wx.EVT_ENTER_WINDOW, self.Highlight)

        self.pnl_Button.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_FileName.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_FilePath.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_FileDate.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.pnl_Button.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_FileName.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_FilePath.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.lbl_FileDate.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.pnl_Button.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.lbl_FileName.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.lbl_FilePath.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.lbl_FileDate.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

        self.pnl_Button.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.lbl_FileName.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.lbl_FilePath.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.lbl_FileDate.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

    def Highlight(self, event):
        """
        Event handler on mouse over. Sets visual appearance
        to 'highlighted'.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgDark)
        self.lbl_FileName.SetBackgroundColour(cs.BgDark)
        self.lbl_FilePath.SetBackgroundColour(cs.BgDark)
        self.lbl_FileDate.SetBackgroundColour(cs.BgDark)
        self.Refresh()
        for i in range(len(self.parent.family)):
            if not self.parent.family[i].index == self.index:
                self.parent.family[i].Standard(None)

    def Standard(self, event):
        """
        Event handler on mouse leaving. Sets visual appearance
        to 'standard'.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgMediumDark)
        self.lbl_FileName.SetBackgroundColour(cs.BgMediumDark)
        self.lbl_FilePath.SetBackgroundColour(cs.BgMediumDark)
        self.lbl_FileDate.SetBackgroundColour(cs.BgMediumDark)
        self.Refresh()

    def OnLeftDown(self, event):
        """
        Event handler to change appearance on left mouse down.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgUltraDark)
        self.lbl_FileName.SetBackgroundColour(cs.BgUltraDark)
        self.lbl_FilePath.SetBackgroundColour(cs.BgUltraDark)
        self.lbl_FileDate.SetBackgroundColour(cs.BgUltraDark)
        self.Refresh()

    def OnLeftUp(self, event):
        """
        Event handler to change appearance on left mouse up.
        """
        self.pnl_Button.SetBackgroundColour(cs.BgDark)
        self.lbl_FileName.SetBackgroundColour(cs.BgDark)
        self.lbl_FilePath.SetBackgroundColour(cs.BgDark)
        self.lbl_FileDate.SetBackgroundColour(cs.BgDark)
        self.Refresh()
        self.parent.parent.MainFrame.Open(self.FilePath, self.FileName)

    def OnRightDown(self, event):
        """
        Event handler for right mouse down. Passes.
        """
        pass
    
    def OnRightUp(self, event):
        """
        Event handler for right mouse up. Opens context menu.
        """
        self.PopupMenu(FileEntryContextMenu(self, event))

########################################################################################################
##                                                                                                    ##
##     #####   ####   ##  ##  ######  ######  ##  ##  ######      ##    ##  ######  ##  ##  ##  ##    ##
##    ##      ##  ##  ### ##    ##    ##       ####     ##        ###  ###  ##      ### ##  ##  ##    ##
##    ##      ##  ##  ######    ##    ####      ##      ##        ########  ####    ######  ##  ##    ##
##    ##      ##  ##  ## ###    ##    ##       ####     ##        ## ## ##  ##      ## ###  ##  ##    ##
##     #####   ####   ##  ##    ##    ######  ##  ##    ##        ##    ##  ######  ##  ##   ####     ##
##                                                                                                    ##
########################################################################################################

class FileEntryContextMenu(wx.Menu):
    """
    Context menu to open file or remove file entry
    """
    def __init__(self, parent, rightclick):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            rightclick -> wx event.
        """
        super(FileEntryContextMenu, self).__init__()

        self.parent = parent

        self.mi_OpenEntry = wx.MenuItem(self, id = wx.ID_ANY, text = u"Open")
        #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
        self.Append(self.mi_OpenEntry)
        self.Bind(wx.EVT_MENU, self.OnMiOpenEntry, self.mi_OpenEntry)

        self.mi_PathToClipboard = wx.MenuItem(self, id = wx.ID_ANY,
                                              text = u"Copy path to clipboard")
        #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
        self.Append(self.mi_PathToClipboard)
        self.Bind(wx.EVT_MENU, self.OnMiPathToClipboard, self.mi_PathToClipboard)

        self.mi_RemoveEntry = wx.MenuItem(self, id = wx.ID_ANY,
                                          text = u"Remove from list")
        #self.mi_TransferKeyword.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
        self.Append(self.mi_RemoveEntry)
        self.Bind(wx.EVT_MENU, self.OnMiRemoveEntry, self.mi_RemoveEntry)

    def OnMiOpenEntry(self, event):
        """
        Event handler: Calls parent object's (i.e. file entry)
        OnLeftUp() function.
        """
        self.parent.OnLeftUp(None)

    def OnMiPathToClipboard(self, event):
        """
        Event object. Copies parent object's (i.e. file entry)
        FilePath property to clipboard.
        """
        # Hand to clipboard
        self.obj_Text = wx.TextDataObject()
        self.obj_Text.SetText(self.parent.FilePath)
        if wx.TheClipboard.Open():
            wx.TheClipboard.Clear()
            wx.TheClipboard.SetData(self.obj_Text)
            wx.TheClipboard.Close()
        else:
            msg.ClipboardError()

    def OnMiRemoveEntry(self, event):
        """
        Event handler. Calls top level instance's function to remove
        the clicked on file entry.
        """
        self.parent.parent.parent.RemoveRecent(self.parent.FilePath)
        
############################################################################################################
##                                                                                                        ##
##     #####  ##  ##   ####   ##  ##   #####  ######     ####    #####   #####   ####   ##  ##   #####    ##
##    ##      ##  ##  ##  ##  ### ##  ##      ##        ##  ##  ##      ##      ##  ##  ##  ##  ##        ##
##    ##      ######  ######  ######  ##  ##  ####      ######   ####    ####   ######   ####    ####     ##
##    ##      ##  ##  ##  ##  ## ###  ##  ##  ##        ##  ##      ##      ##  ##  ##    ##        ##    ##
##     #####  ##  ##  ##  ##  ##  ##   #####  ######    ##  ##  #####   #####   ##  ##    ##    #####     ##
##                                                                                                        ##
############################################################################################################

class ChangePinnedAssays(wx.Dialog):
    """
    Dialog window to change the pinned assays.
    """

    def __init__(self, parent):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
        """
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = wx.EmptyString,
                           pos = wx.DefaultPosition, size = wx.Size(438,245),
                           style = wx.TAB_TRAVERSAL)

        self.SetBackgroundColour(cs.BgMedium)

        self.parent = parent
        self.PinnedAssayHaver = self.parent.MainFrame
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)

        # TITLE BAR #####################################################################
        self.pnl_TitleBar = wx.Panel(self)
        self.pnl_TitleBar.SetBackgroundColour(cs.BgUltraDark)
        self.pnl_TitleBar.SetForegroundColour(cs.White)
        self.szr_TitleBar = wx.BoxSizer(wx.HORIZONTAL)
        self.bmp_Pin = wx.StaticBitmap(self.pnl_TitleBar,
                                       bitmap = wx.Bitmap(self.PinnedAssayHaver.str_OtherPath
                                       + r"\pin.png", wx.BITMAP_TYPE_ANY),
                                       size = wx.Size(25,25))
        self.szr_TitleBar.Add(self.bmp_Pin,0,wx.ALL,0)
        self.lbl_Title = wx.StaticText(self.pnl_TitleBar, label = u"Pin assays")
        self.lbl_Title.Wrap(-1)
        self.szr_TitleBar.Add(self.lbl_Title, 0, wx.ALL, 5)
        self.szr_TitleBar.Add((0,0), 1, wx.EXPAND, 5)
        self.btn_X = btn.CustomBitmapButton(self.pnl_TitleBar, type = u"small_x",
                                            index = 0,
                                            size = (25,25),
                                            pathaddendum = u"titlebar")
        self.btn_X.Bind(wx.EVT_BUTTON, self.Cancel)
        self.szr_TitleBar.Add(self.btn_X,0,wx.ALL,0)
        self.pnl_TitleBar.SetSizer(self.szr_TitleBar)
        self.pnl_TitleBar.Layout()
        self.szr_Surround.Add(self.pnl_TitleBar, 0, wx.EXPAND, 5)

        # ASSAY LISTS ###################################################################
        self.szr_PinThoseAssays = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PinThoseAssays.Add((5,0),0,wx.EXPAND,0)
        self.szr_AllAssays = wx.BoxSizer(wx.VERTICAL)
        self.szr_AllAssays.Add((0,5),0,wx.EXPAND,0)
        self.lbl_PinnedAssays = wx.StaticText(self, label =  u"Pinned assays")
        self.szr_AllAssays.Add(self.lbl_PinnedAssays, 0, wx.ALL, 0)
        lbx_PinnedAssaysChoices = []
        lbx_AllAssaysChoices = []
        for assay in self.PinnedAssayHaver.dfr_Assays.index:
            str_Assay = self.PinnedAssayHaver.dfr_Assays.loc[assay,"FullName"]
            if self.PinnedAssayHaver.dfr_Assays.loc[assay,"Pinned"] == True:
                lbx_PinnedAssaysChoices.append(str_Assay)
            else:
                lbx_AllAssaysChoices.append(str_Assay)
        self.lbx_PinnedAssays = wx.ListBox(self, size = wx.Size(192,64),
                                           choices = lbx_PinnedAssaysChoices)
        self.lbx_PinnedAssays.SetBackgroundColour(cs.BgLight)
        self.szr_AllAssays.Add(self.lbx_PinnedAssays, 0, wx.ALL, 0)
        self.szr_PinThoseAssays.Add(self.szr_AllAssays, 0, wx.EXPAND, 5)
        self.szr_Assignment = wx.BoxSizer(wx.VERTICAL)
        self.szr_Assignment.Add((0,23),0,wx.EXPAND,0)
        self.btn_Add = btn.CustomBitmapButton(self, type = u"ArrowLeft",
                                              index = 0,
                                              size = (40,25))
        self.btn_Add.Bind(wx.EVT_BUTTON, self.AddAssay)
        self.szr_Assignment.Add(self.btn_Add, 0, wx.ALL, 2)
        self.btn_Remove = btn.CustomBitmapButton(self, type = u"ArrowRight",
                                                 index = 1,
                                                 size = (40,25))
        self.btn_Remove.Bind(wx.EVT_BUTTON, self.RemoveAssay)
        self.szr_Assignment.Add(self.btn_Remove, 0, wx.ALL, 2)
        self.szr_PinThoseAssays.Add(self.szr_Assignment, 0, wx.EXPAND, 5)
        self.szr_AllAssays = wx.BoxSizer(wx.VERTICAL)
        self.szr_AllAssays.Add((0,5),0,wx.EXPAND,0)
        self.lbl_AllAssays = wx.StaticText(self, label = u"All assays")
        self.szr_AllAssays.Add(self.lbl_AllAssays, 0, wx.ALL, 0)
        self.lbx_AllAssays = wx.ListBox(self, size = wx.Size(192,128),
                                        choices = lbx_AllAssaysChoices)
        self.lbx_AllAssays.SetBackgroundColour(cs.BgLight)
        self.szr_AllAssays.Add(self.lbx_AllAssays, 0, wx.ALL, 0)
        self.szr_PinThoseAssays.Add(self.szr_AllAssays, 0, wx.EXPAND, 5)
        self.szr_Surround.Add(self.szr_PinThoseAssays, 0, wx.EXPAND, 5)

        # Dividing line #################################################################
        self.line = wx.Panel(self, size= wx.Size(-1,1))
        self.line.SetBackgroundColour(cs.BgUltraDark)
        self.szr_Surround.Add(self.line, 0, wx.EXPAND|wx.ALL, 5)

        # Button bar at bottom
        self.szr_ButtonBar = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ButtonBar.Add((0, 0), 1, wx.EXPAND, 5)
        self.btn_Apply = btn.CustomBitmapButton(self, type = u"ApplyAndClose",
                                                index = 0,
                                                size = (100,30))
        self.btn_Apply.Bind(wx.EVT_BUTTON, self.UpdatePinnedAssays)
        self.szr_ButtonBar.Add(self.btn_Apply, 0, wx.ALL, 5)
        self.btn_Cancel = btn.CustomBitmapButton(self, type = u"Cancel",
                                                 index = 0,
                                                 size = (100,30))
        self.btn_Cancel.Bind(wx.EVT_BUTTON, self.Cancel)
        self.szr_ButtonBar.Add(self.btn_Cancel, 0, wx.ALL, 5)
        self.szr_Surround.Add(self.szr_ButtonBar, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(self.szr_Surround)
        self.Layout()

        self.Centre(wx.BOTH)

        # Required for window dragging:
        self.delta = wx.Point(0,0)
        self.pnl_TitleBar.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.lbl_Title.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.bmp_Pin.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.dragging = False

    def __del__(self):
        pass

    # The following three function are taken from a tutorial on the
    # wxPython Wiki: https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def OnMouseMove(self, event):
        """
        Event handler for window dragging on mouse movement.
        """
        if self.dragging == True:
            if event.Dragging() and event.LeftIsDown():
                x,y = self.ClientToScreen(event.GetPosition())
                newPos = (x - self.delta[0], y - self.delta[1])
                self.Move(newPos)

    def OnLeftDown(self, event):
        """
        Event handler to capture mouse and get positional offset for
        mouse movement.
        """
        self.CaptureMouse()
        x, y = self.ClientToScreen(event.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx
        dy = y - originy
        self.delta = [dx, dy]
        self.dragging = True

    def OnLeftUp(self, event):
        """
        Event handler to release mouse and end window dragging.
        """
        if self.HasCapture():
            self.ReleaseMouse()
        self.dragging = False

    def AddAssay(self, event):
        """
        Adds selected assay to the list of pinned assays.
        """
        event.Skip()
        if self.lbx_PinnedAssays.GetCount() < 4 and self.lbx_AllAssays.GetSelection() >= 0:
            int_Selected = self.lbx_AllAssays.GetSelection()
            self.lbx_PinnedAssays.Insert(self.lbx_AllAssays.GetString(int_Selected),
                                         self.lbx_PinnedAssays.GetCount())
            self.lbx_AllAssays.Delete(int_Selected)

    def RemoveAssay(self, event):
        """
        Removes selected assay to the list of pinned assays.
        """
        event.Skip()
        if self.lbx_PinnedAssays.GetSelection() >= 0:
            int_Selected = self.lbx_PinnedAssays.GetSelection()
            self.lbx_AllAssays.Insert(self.lbx_PinnedAssays.GetString(int_Selected),
                                      self.lbx_AllAssays.GetCount())
            self.lbx_PinnedAssays.Delete(int_Selected)

    def UpdatePinnedAssays(self, event):
        """
        Updates list of pinned assays
        """
        event.Skip()
        # Get list of pinned assays
        lst_PinnedAssays = []
        for pin in range(self.lbx_PinnedAssays.GetCount()):
            lst_PinnedAssays.append(self.lbx_PinnedAssays.GetString(pin))
        # Update dataframe and prepare list for export
        lst_PinnedShorthands = []
        for assay in self.PinnedAssayHaver.dfr_Assays.index:
            if self.PinnedAssayHaver.dfr_Assays.loc[assay,"FullName"] in lst_PinnedAssays:
                self.PinnedAssayHaver.dfr_Assays.loc[assay,"Pinned"] = True
                lst_PinnedShorthands.append(assay)
            else:
                self.PinnedAssayHaver.dfr_Assays.loc[assay,"Pinned"] = False
        # Save list to csv:
        np.savetxt(self.PinnedAssayHaver.str_Pinned, [lst_PinnedShorthands], delimiter=",", fmt ='% s')
        # Pin assays:
        self.parent.PinAssays()
        self.parent.Update()
        self.parent.Layout()
        self.EndModal(True)

    def Cancel(self, event):
        """
        Event handler. Closes window.
        """
        event.Skip()
        self.EndModal(True)


############################################################################
##                                                                        ##
##    #####   ##  ##  ##              ##  ##   ####   ##    ##  ######    ##
##    ##  ##  ### ##  ##              ##  ##  ##  ##  ###  ###  ##        ##
##    #####   ## ###  ##              ######  ##  ##  ########  ####      ##
##    ##      ##  ##  ##              ##  ##  ##  ##  ## ## ##  ##        ##
##    ##      ##  ##  ######  ######  ##  ##   ####   ##    ##  ######    ##
##                                                                        ##
############################################################################

class HomeScreen (wx.Panel):
    """
    App's home screen. Based on wx.Panel
    """

    def __init__(self, parent, mainframe):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            mainframe -> wx.Frame. App's main frame.
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.Size(1000,750), style = wx.TAB_TRAVERSAL,
                           name = u"HomeScreen")

        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.parent = parent
        self.MainFrame = mainframe

        # Initialise instance wide variables with default values
        self.Title = u"Home"
        self.Index = None
        self.Assays = pd.DataFrame()

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)

        self.szr_PinnedAssays = wx.BoxSizer(wx.VERTICAL)
        self.szr_PinnedAssaysLabel = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PinnedAssaysLabel.Add((40,-1),0,wx.ALL,0)
        self.lbl_PinnedAssays = wx.StaticText(self, label = u"Pinned assays",
                                              size = wx.Size(-1,40))
        self.lbl_PinnedAssays.SetFont(wx.Font(14, family = wx.FONTFAMILY_DEFAULT,
                                              style = wx.FONTSTYLE_NORMAL,
                                              weight = wx.FONTWEIGHT_BOLD,
                                              underline = False,
                                              faceName = wx.EmptyString))
        self.szr_PinnedAssaysLabel.Add(self.lbl_PinnedAssays, 0, wx.ALL, 0)
        self.szr_PinnedAssaysLabel.Add((5,-1),0,wx.ALL,0)
        self.btn_PinnedAssays = btn.CustomBitmapButton(self, u"Pin", 0, (25,25))
        self.btn_PinnedAssays.Bind(wx.EVT_BUTTON, self.ChangePinnedAssays)
        self.szr_PinnedAssaysLabel.Add(self.btn_PinnedAssays, 0, wx.ALL, 0)
        self.szr_PinnedAssays.Add(self.szr_PinnedAssaysLabel, 0, wx.ALL, 0)
        self.szr_PinnedAssaysScrolledWindow = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PinnedAssaysScrolledWindow.Add((40,-1),0,wx.ALL,0)
        self.pnl_PinnedAssays = wx.ScrolledWindow(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(910,182), wx.TAB_TRAVERSAL|wx.HSCROLL)
        self.pnl_PinnedAssays.SetMinSize(wx.Size(910,182))
        self.pnl_PinnedAssays.SetScrollRate(5, 5)
        self.szr_AssayButtons = wx.BoxSizer(wx.HORIZONTAL)
        # Add assay buttons
        self.dic_Pinned = {}
        self.PinAssays()

        self.pnl_PinnedAssays.SetSizer(self.szr_AssayButtons)
        self.pnl_PinnedAssays.Layout()
        self.szr_AssayButtons.Fit(self.pnl_PinnedAssays)
        self.szr_PinnedAssaysScrolledWindow.Add(self.pnl_PinnedAssays,0,wx.ALL,0)
        self.szr_PinnedAssays.Add(self.szr_PinnedAssaysScrolledWindow, 0, wx.ALL, 0)
        self.szr_Surround.Add(self.szr_PinnedAssays,0,wx.ALL,0)

        self.szr_Surround.Add((10,10),0,wx.ALL,0)

        self.szr_RecentFiles = wx.FlexGridSizer(2,2,0,0)
        self.szr_RecentFiles.Add((40,-1),0,wx.ALL,0)
        self.lbl_RecentFiles = wx.StaticText(self, label = u" Recent projects")
        self.lbl_RecentFiles.SetFont(wx.Font(14, family = wx.FONTFAMILY_DEFAULT,
                                             style = wx.FONTSTYLE_NORMAL,
                                             weight = wx.FONTWEIGHT_BOLD,
                                             underline = False,
                                             faceName = wx.EmptyString))
        self.szr_RecentFiles.Add(self.lbl_RecentFiles, 0, wx.ALL, 5)
        self.szr_RecentFiles.Add((40,-1),0,wx.ALL,0)
        self.pnl_FileList = FileList(self)
        self.szr_RecentFiles.Add(self.pnl_FileList, 0, wx.ALL|wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_RecentFiles,0,wx.ALL,0)

        self.CheckForRecentFiles()

        self.SetSizer(self.szr_Surround)
        self.Layout()
        self.szr_Surround.Fit(self)

    def __del__(self):
        pass
    
    def CheckForRecentFiles(self):
        """
        Checks whether the "recent projects" .csv exists.
        If not, a new one gets created.
        """
        self.pnl_FileList.DeleteAllItems()
        str_RecentPath = os.path.join(Path.home(),"bbq_recent.csv")
        if not os.path.isfile(str_RecentPath) == True:
            dfr_Recent = pd.DataFrame(columns=["FileName","AssayCategory",
                                               "Shorthand","FullPath","DateTime"],
                                               index=[0,1,2,3,4,5,6,7,8,9])
            dfr_Recent.to_csv(str_RecentPath)
        else:
            dfr_Recent = pd.read_csv(str_RecentPath, sep=",", header=0,
                                     index_col=0, engine="python").sort_values(
                                     by=["DateTime"],ascending=False)
            idx_List = 0
            for idx_File in range(len(dfr_Recent)):
                # First, check there is an entry:
                if pd.isna(dfr_Recent.loc[idx_File,"FileName"]) == False:
                    # Second, check the entry is still valid:
                    if os.path.isfile(dfr_Recent.loc[idx_File,"FullPath"]) == True:
                        self.pnl_FileList.AddFileEntry(idx_List,dfr_Recent.loc[idx_File].tolist())
                        idx_List += 1
                    else:
                        dfr_Recent.loc[idx_File,"FileName"] = np.nan
                        dfr_Recent.loc[idx_File,"AssayCategory"] = np.nan
                        dfr_Recent.loc[idx_File,"Shorthand"] = np.nan
                        dfr_Recent.loc[idx_File,"FullPath"] = np.nan
                        dfr_Recent.loc[idx_File,"DateTime"] = np.nan
        if len(self.pnl_FileList.family) > 0:
            self.pnl_FileList.family[0].Highlight(None)
        self.Layout()

    def UpdateRecent(self, str_FilePath, str_FileName, str_AssayCategory, str_Shorthand):
        """
        Updates csv file in user's home directory that holds
        list of most recelty opened files.

        Arguments:
            str_FilePath -> string. Complete path to the file.
            str_FileName -> string. File name to be displayed.
            str_AssayCategory -> string. Long form assay category.
            str_Shorthand -> string. Shorthand code for the assay.

        """
        str_RecentPath = os.path.join(Path.home(),"bbq_recent.csv")
        if not os.path.isfile(str_RecentPath) == True:
            dfr_Recent = pd.DataFrame(columns=["FileName","AssayCategory",
                                               "Shorthand","FullPath","DateTime"]
                                               ,index=[0,1,2,3,4,5,6,7,8,9])
            dfr_Recent.loc[0,"FileName"] = str_FileName
            dfr_Recent.loc[0,"AssayCategory"] = str_AssayCategory
            dfr_Recent.loc[0,"Shorthand"] = str_Shorthand
            dfr_Recent.loc[0,"FullPath"] = str_FilePath
            dfr_Recent.loc[0,"DateTime"] = str(datetime.datetime.now())
            dfr_Recent.to_csv(str_RecentPath)
        else:
            dfr_Recent = pd.read_csv(str_RecentPath, sep=",", header=0, index_col=0,
                                     engine="python").sort_values(by=["DateTime"],
                                     ascending=False,ignore_index=True)
            # See if this file had been added before. If so, update DateTime and save again.
            bol_AlreadyThere = False
            for idx_File in range(len(dfr_Recent)):
                # First, check there is an entry:
                if pd.isna(dfr_Recent.loc[idx_File,"FileName"]) == False:
                    # Check if the file is still there
                    if os.path.isfile(dfr_Recent.loc[idx_File,"FullPath"]) == True:
                        # Second, compare entry to new file. If found, update
                        if dfr_Recent.loc[idx_File,"FullPath"] == str_FilePath:
                            dfr_Recent.loc[idx_File,"DateTime"] = str(datetime.datetime.now())
                            bol_AlreadyThere = True
                    else: # if the entry is gone, overwrite!
                        dfr_Recent.iloc[idx_File,0] = np.nan
                        dfr_Recent.iloc[idx_File,1] = np.nan
                        dfr_Recent.iloc[idx_File,2] = np.nan
                        dfr_Recent.iloc[idx_File,3] = np.nan
                        dfr_Recent.iloc[idx_File,4] = np.nan
            if bol_AlreadyThere == False:
                # Write new file into the last row of the dataframe (oldest file),
                # then re-sort.
                dfr_Recent.iloc[-1,0] = str_FileName
                dfr_Recent.iloc[-1,1] = str_AssayCategory
                dfr_Recent.iloc[-1,2] = str_Shorthand
                dfr_Recent.iloc[-1,3] = str_FilePath
                dfr_Recent.iloc[-1,4] = str(datetime.datetime.now())
            # Re-sort by last edit ("DateTime")
            dfr_Recent = dfr_Recent.sort_values(by=["DateTime"],ascending=False,
                                                ignore_index=True)
            dfr_Recent.to_csv(str_RecentPath)
        self.CheckForRecentFiles()

    def RemoveRecent(self, str_FilePath):
        """
        Updates csv file in user's home directory that holds list of
        most recelty opened files

        Arguments:
            str_FilePath -> string. Complete path of the file to be
                            removed from the "recent files" list.

        """
        self.Freeze()
        str_RecentPath = os.path.join(Path.home(),"bbq_recent.csv")
        if not os.path.isfile(str_RecentPath) == True:
            print("Fnord")
        else:
            dfr_Recent = pd.read_csv(str_RecentPath, sep=",", header=0, index_col=0,
                                     engine="python").sort_values(by=["DateTime"],
                                     ascending=False,ignore_index=True)
            # Find the entry by file path
            bol_AlreadyThere = False
            for idx_File in range(len(dfr_Recent)):
                if str_FilePath == dfr_Recent.loc[idx_File,"FullPath"]:
                    # Overwrite!
                    dfr_Recent.iloc[idx_File,0] = np.nan
                    dfr_Recent.iloc[idx_File,1] = np.nan
                    dfr_Recent.iloc[idx_File,2] = np.nan
                    dfr_Recent.iloc[idx_File,3] = np.nan
                    dfr_Recent.iloc[idx_File,4] = np.nan
            # Re-sort by last edit ("DateTime")
            dfr_Recent = dfr_Recent.sort_values(by=["DateTime"],ascending=False,
                                                ignore_index=True)
            dfr_Recent.to_csv(str_RecentPath)
        self.CheckForRecentFiles()
        self.Thaw()

    def ChangePinnedAssays(self, event):
        """
        Event handler. Launches dialog to change pinned assays.
        """
        self.dlg_ChangePinnedAssays = ChangePinnedAssays(self)
        self.dlg_ChangePinnedAssays.ShowModal()

    def PinAssays(self):
        """
        Adds all assays referenced in main frame's dataframe dfr_Assays
        to the pinned assays list on the home screen.
        """
        # Clear up any buttons that may be there already:
        if len(self.dic_Pinned) > 0:
            for button in self.dic_Pinned:
                self.dic_Pinned[button].Destroy()
            self.dic_Pinned.clear()
        # Add new buttons:
        for assay in self.MainFrame.dfr_Assays.index:
            if self.MainFrame.dfr_Assays.loc[assay,"Pinned"] == True:
                self.dic_Pinned[assay] = btn.AssayButton(
                                        parent = self.pnl_PinnedAssays,
                                        assaypath = self.MainFrame.dfr_Assays.loc[assay,"Subdirectory"],
                                        shorthand = assay,
                                        index = len(self.dic_Pinned),
                                        label = self.MainFrame.dfr_Assays.loc[assay,"FullName"],
                                        mainframe = self.MainFrame,
										group = self.dic_Pinned)
                self.szr_AssayButtons.Add(self.dic_Pinned[assay], 0, wx.ALL, 2)

##########################################################################################################
##                                                                                                      ##
##    #####   ##  ##  ##              #####   #####    ####   ######  ######   #####  ######   #####    ##
##    ##  ##  ### ##  ##              ##  ##  ##  ##  ##  ##      ##  ##      ##        ##    ##        ##
##    #####   ######  ##              #####   #####   ##  ##      ##  ####    ##        ##     ####     ##
##    ##      ## ###  ##              ##  ##  ##  ##  ##  ##  ##  ##  ##      ##        ##        ##    ##
##    ##      ##  ##  ######  ######  ##  ##  ##  ##   ####    ####   ######   #####    ##    #####     ##
##                                                                                                      ##
##########################################################################################################

class pnl_Projects (wx.Panel):
    """
    Panel showing all assay types available to start a new project.
    Based on wx.Panel
    """

    def __init__(self, parent, mainframe):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            mainframe -> wx.Frame. app's main frame.
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.Size(1000,750), style = wx.TAB_TRAVERSAL,
                           name = u"pnl_Projects")

        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.parent = parent
        self.MainFrame = mainframe

        self.szr_New = wx.BoxSizer(wx.VERTICAL)
        self.szr_AssayCategroryTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_AssayCategroryTabs.Add((20,30))
        self.btn_AllAssays = btn.AssayTabButton(self, u"All Assays", 0)
        self.btn_AllAssays.IsCurrent(True)
        self.btn_AllAssays.IsEnabled(True)
        self.szr_AssayCategroryTabs.Add(self.btn_AllAssays, 0, wx.EXPAND, 0)
        self.btn_PlateBased = btn.AssayTabButton(self, u"Plate-based Assays", 1)
        self.btn_PlateBased.IsEnabled(True)
        self.szr_AssayCategroryTabs.Add(self.btn_PlateBased, 0, wx.EXPAND, 0)
        self.btn_OtherAssays = btn.AssayTabButton(self, u"Other Assays", 2)
        self.btn_OtherAssays.IsEnabled(True)
        self.szr_AssayCategroryTabs.Add(self.btn_OtherAssays, 0, wx.EXPAND, 0)
        self.szr_New.Add(self.szr_AssayCategroryTabs, 0, wx.EXPAND, 5)
        self.sbk_AssayCategories = wx.Simplebook(self)
        self.dic_AssayTabButtons = {0:self.btn_AllAssays,
                                    1:self.btn_PlateBased,
                                    2:self.btn_OtherAssays}
        for idx_Button in range(len(self.dic_AssayTabButtons)):
            self.dic_AssayTabButtons[idx_Button].Group = self.dic_AssayTabButtons
            self.dic_AssayTabButtons[idx_Button].Notebook = self.sbk_AssayCategories
        # "All assays" ##################################################################
        self.pnl_AllAssays = wx.Panel(self.sbk_AssayCategories, style = wx.TAB_TRAVERSAL)
        self.pnl_AllAssays.SetBackgroundColour(cs.BgMediumDark)
        self.pnl_AllAssays.SetForegroundColour(cs.White)
        self.szr_AllAssays = wx.BoxSizer(wx.VERTICAL)
        self.szr_AAEndpoint = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_AAEndpoint.Add((20,0), 0, wx.ALL, 5)
        # Buttons added later
        self.szr_AllAssays.Add(self.szr_AAEndpoint, 0, wx.ALL, 5)
        self.szr_AAContinuous = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_AAContinuous.Add((20,0), 0, wx.ALL, 5)
        # Buttons added later
        self.szr_AllAssays.Add(self.szr_AAContinuous, 0, wx.ALL, 5)
        self.pnl_AllAssays.SetSizer(self.szr_AllAssays)
        self.pnl_AllAssays.Layout()
        self.szr_AllAssays.Fit(self.pnl_AllAssays)
        self.sbk_AssayCategories.AddPage(self.pnl_AllAssays, text = u"AllAssays")
        # "Plate based assays" category #################################################
        self.pnl_PlateBased = wx.Panel(self.sbk_AssayCategories, style = wx.TAB_TRAVERSAL)
        self.pnl_PlateBased.SetBackgroundColour(cs.BgMediumDark)
        self.pnl_PlateBased.SetForegroundColour(cs.White)
        self.szr_PlateBased = wx.BoxSizer(wx.VERTICAL)
        self.szr_PBEndpoint = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PBEndpoint.Add((20,0), 0, wx.ALL, 5)
        # Buttons added later
        self.szr_PlateBased.Add(self.szr_PBEndpoint, 0, wx.ALL, 5)
        self.szr_PBContinuous = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PBContinuous.Add((20,0), 0, wx.ALL, 5)
        # Buttons added later
        self.szr_PlateBased.Add(self.szr_PBContinuous, 0, wx.ALL, 5)
        self.pnl_PlateBased.SetSizer(self.szr_PlateBased)
        self.pnl_PlateBased.Layout()
        self.szr_PlateBased.Fit(self.pnl_PlateBased)
        self.sbk_AssayCategories.AddPage(self.pnl_PlateBased, text = u"Plate based assays")
        # Other assays ##################################################################
        self.pnl_OtherAssays = wx.Panel(self.sbk_AssayCategories, style = wx.TAB_TRAVERSAL)
        self.pnl_OtherAssays.SetBackgroundColour(cs.BgMediumDark)
        self.pnl_OtherAssays.SetForegroundColour(cs.White)
        self.szr_OtherAssays = wx.BoxSizer(wx.VERTICAL)
        self.szr_OAContinuous = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_OAContinuous.Add((20,0), 0, wx.ALL, 5)
        # Buttons added later
        self.szr_OtherAssays.Add(self.szr_OAContinuous, 0, wx.ALL, 5)
        self.pnl_OtherAssays.SetSizer(self.szr_OtherAssays)
        self.pnl_OtherAssays.Layout()
        self.szr_OtherAssays.Fit(self.pnl_OtherAssays)
        self.sbk_AssayCategories.AddPage(self.pnl_OtherAssays, text = u"Other assays")
        # Add assay buttons #############################################################
        int_ButtonIndex = 0
        self.dic_AssayButtons = {}
        for assay in self.MainFrame.dfr_Assays.index:
            # All assays tab
            self.dic_AssayButtons[int_ButtonIndex] = btn.AssayButton(
                                        parent = self.pnl_AllAssays,
                                        assaypath = self.MainFrame.dfr_Assays.loc[assay,
                                        "Subdirectory"],
                                        shorthand = assay,
                                        index = len(self.dic_AssayButtons),
                                        label = self.MainFrame.dfr_Assays.loc[assay,"FullName"],
                                        mainframe = self.MainFrame,
                                        group = self.dic_AssayButtons)
            if "Endpoint" in self.MainFrame.dfr_Assays.loc[assay,"Categories"]:
                self.szr_AAEndpoint.Add(self.dic_AssayButtons[int_ButtonIndex], 1,
                                        wx.EXPAND|wx.ALL, 2)
            else:
                self.szr_AAContinuous.Add(self.dic_AssayButtons[int_ButtonIndex], 0,
                                          wx.ALL, 2)
            # Plate based
            if "Plate" in self.MainFrame.dfr_Assays.loc[assay,"Categories"]:
                int_ButtonIndex += 1
                self.dic_AssayButtons[int_ButtonIndex] = btn.AssayButton(
                                        parent = self.pnl_PlateBased,
                                        assaypath = self.MainFrame.dfr_Assays.loc[assay,
                                        "Subdirectory"],
                                        shorthand = assay,
                                        index = len(self.dic_AssayButtons),
                                        label = self.MainFrame.dfr_Assays.loc[assay,"FullName"],
                                        mainframe = self.MainFrame,
                                        group = self.dic_AssayButtons)
                if "Endpoint" in self.MainFrame.dfr_Assays.loc[assay,"Categories"]:
                    self.szr_PBEndpoint.Add(self.dic_AssayButtons[int_ButtonIndex], 0,
                                            wx.ALL, 2)
                else:
                    self.szr_PBContinuous.Add(self.dic_AssayButtons[int_ButtonIndex], 0,
                                              wx.ALL, 2)
            # Other:
            else:
                int_ButtonIndex += 1
                self.dic_AssayButtons[int_ButtonIndex] = btn.AssayButton(
                                        parent = self.pnl_OtherAssays,
                                        assaypath = self.MainFrame.dfr_Assays.loc[assay,
                                        "Subdirectory"],
                                        shorthand = assay,
                                        index = len(self.dic_AssayButtons),
                                        label = self.MainFrame.dfr_Assays.loc[assay,"FullName"],
                                        mainframe = self.MainFrame,
                                        group = self.dic_AssayButtons)
                self.szr_OAContinuous.Add(self.dic_AssayButtons[int_ButtonIndex], 0,
                                          wx.ALL, 2)
            int_ButtonIndex += 1
        self.szr_New.Add(self.sbk_AssayCategories, 0, wx.ALL, 5)
        self.SetSizer(self.szr_New)
        self.Layout()
        self.szr_New.Fit(self)
