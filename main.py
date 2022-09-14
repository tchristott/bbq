"""
Main module for BBQ.

Classes:
    frm_Main
    BBQ

Functions:
    main

"""

#####################################################################################################################################################
# The following code taken from the wxPython Wiki:                                                    ###############################################
# https://wiki.wxpython.org/How%20to%20create%20a%20splash%20screen%20while%20loading%20%28Phoenix%29 ###############################################
#####################################################################################################################################################

import importlib
import multiprocessing
import os
import sys
import wx
import wx.lib.agw.advancedsplash as AS

SHOW_SPLASH = True

# Test to see if we need to show a splash screen.
# If the splash is enabled (and we are not the application fork),
# then show a splash screen and relaunch the same application
# except as the application fork.

if __name__ == "__main__":
    AppFN = sys.argv[0]
    if SHOW_SPLASH and (len(sys.argv) == 1) and AppFN.endswith(".exe"):
        App = wx.App()

        # Get the Path of the splash screen
        real_path = os.path.realpath(__file__)

        frame = AS.AdvancedSplash(None,
                                  bitmap = wx.Bitmap(os.path.dirname(real_path) + r"\other\splash.png",wx.BITMAP_TYPE_PNG),
                                  timeout = 5000,
                                  agwStyle = AS.AS_TIMEOUT|AS.AS_CENTER_ON_PARENT|AS.AS_SHADOW_BITMAP,
                                  shadowcolour = wx.RED)

        os.spawnl(os.P_NOWAIT,
                  AppFN,
                  '"%s"' % AppFN.replace('"', r'\"'),
                  "NO_SPLASH")

        App.MainLoop()
        sys.exit()

#########################################################################################
# BBQ actual starts here ################################################################
#########################################################################################

import numpy as np
import pandas as pd
import zipfile as zf
from pathlib import Path
import os
import shutil
import threading
import datetime
import csv

import warnings

import wx
import wx.adv
import wx.xrc

# required to open bbq_manual.pdf -> via system's standard PDF viewer
import subprocess

# Import my custom libraries
import lib_messageboxes as msg
import lib_colourscheme as cs
from lib_datafunctions import import_string_to_list
import lib_progressdialog as prog
from lib_custombuttons import CustomBitmapButton
# Import panels for notebook
import lib_tools as tools
import panel_Home as Home


####################################################################################
##                                                                                ##
##    ##    ##   ####   ##  ##  ##    ######  #####    ####   ##    ##  ######    ##
##    ###  ###  ##  ##  ##  ### ##    ##      ##  ##  ##  ##  ###  ###  ##        ##
##    ########  ######  ##  ######    ####    #####   ######  ########  ####      ##
##    ## ## ##  ##  ##  ##  ## ###    ##      ##  ##  ##  ##  ## ## ##  ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ##      ##  ##  ##  ##  ##    ##  ######    ##
##                                                                                ##
####################################################################################

class frm_Main (wx.Frame):

    """
    Main application window.
    Based on wx.Frame class
    """

    def __init__(self, parent):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
        """
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = u"BBQ",
                           pos = wx.DefaultPosition, size = wx.Size(1380,768),
                           style = wx.TAB_TRAVERSAL|wx.RESIZE_BORDER)

        # Delete BBQ's temp directory if for any reason BBQ was previously
        # exited incorrectly and it still exists.
        self.DeleteBBQTempDirectory()

        # Set default colours
        self.clr_Dark = cs.BgUltraDark
        self.clr_Medium = cs.BgMediumDark
        self.clr_HeaderText = cs.White

        # Set useful paths (locations of image files)
        #real_path = os.path.realpath(__file__)
        self.dir_Path = os.path.dirname(os.path.realpath(__file__))
        self.str_ButtonPath = self.dir_Path + r"\buttons"
        self.str_MenuButtonPath = self.str_ButtonPath + r"\sidebar"
        self.str_TitleButtonsPath = self.str_ButtonPath + r"\titlebar"
        self.str_OtherPath = self.dir_Path + r"\other"

        # Set Application Icon and Taskbar Icon
        self.BBQIcon = wx.Icon(self.dir_Path + r"\bbq.ico", wx.BITMAP_TYPE_ANY)
        self.SetIcon(self.BBQIcon)
        self.icn_Taskbar = wx.adv.TaskBarIcon()
        self.icn_Taskbar.SetIcon(self.BBQIcon,
                                 tooltip="BBQ - Biochemical and Biophysical assay data analysis")

        # Find all assays:
        self.dfr_Assays, self.dic_AssayModules = self.FindAssays()

        self.ProjectTab = None
        
        # Required for window dragging:
        # Functions for window dragging taken from wxPython documentation:
        # https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
        self.delta = wx.Point(0,0)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        # Unused other than for window size changing by dragging bottom right corner
        self.m_statusBar1 = self.CreateStatusBar(1, wx.STB_SIZEGRIP, wx.ID_ANY)

        self.szr_Main = wx.BoxSizer(wx.HORIZONTAL)


         #### # ####  #####   ####   ###  ####    #   # ##### #   # #   #
        #     # #   # #       #   # #   # #   #   ## ## #     ##  # #   #
         ###  # #   # ###     ####  ##### ####    ##### ###   ##### #   #
            # # #   # #       #   # #   # #   #   # # # #     #  ## #   #
        ####  # ####  #####   ####  #   # #   #   #   # ##### #   #  ###  ###############

        self.pnl_Menu = wx.Panel(self)
        self.pnl_Menu.SetForegroundColour(self.clr_HeaderText)
        self.pnl_Menu.SetBackgroundColour(self.clr_Dark)
        self.szr_Menu = wx.BoxSizer(wx.VERTICAL)
        self.szr_Menu.Add((0, 150), 0, wx.EXPAND, 0)
        self.dic_SidebarButtonGroup = {}
        self.dic_Tabnames = {}
        # Home Button
        self.btn_Home = CustomBitmapButton(self.pnl_Menu,
                                           type = u"Home",
                                           index = 0,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Home"] = self.btn_Home
        self.btn_Home.IsCurrent(True)
        # NO PARENTHESES WHEN ASSIGNING FUNCTION THAT IS TO BE CALLED AS MEMBER OF DICTIONARY.
        self.dic_Tabnames["Home"] = self.HomeText
        self.szr_Menu.Add(self.btn_Home, 0, wx.ALL, 0)
        # New Button
        self.btn_New = CustomBitmapButton(self.pnl_Menu,
                                          type = u"New",
                                          index = 1,
                                          size = (150,50),
                                          pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["New"] = self.btn_New
        self.dic_Tabnames["New"] = u"New Project"
        self.szr_Menu.Add(self.btn_New, 0, wx.ALL, 0)
        # Open Button
        self.btn_Open = CustomBitmapButton(self.pnl_Menu,
                                           type = u"Open",
                                           index = 2,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Open"] = self.btn_Open
        self.szr_Menu.Add(self.btn_Open, 0, wx.ALL, 0)
        # ToolsButton
        self.btn_Tools = CustomBitmapButton(self.pnl_Menu,
                                            type = u"Tools",
                                            index = 3,
                                            size = (150,50),
                                            pathaddendum = u"sidebar")
        self.dic_SidebarButtonGroup["Tools"] = self.btn_Tools
        self.dic_Tabnames["Tools"] = u"Tools"
        self.szr_Menu.Add(self.btn_Tools, 0, wx.ALL, 0)
        # Divider
        self.m_staticline5 = wx.StaticLine(self.pnl_Menu, style = wx.LI_HORIZONTAL)
        self.szr_Menu.Add(self.m_staticline5, 0, wx.EXPAND |wx.ALL, 5)
        # Btn Current
        self.btn_Current = CustomBitmapButton(self.pnl_Menu,
                                              type = u"Current",
                                              index = 4,
                                              size = (150,50),
                                              pathaddendum = u"sidebar")
        self.btn_Current.Enable(False)
        self.dic_SidebarButtonGroup["Current"] = self.btn_Current
        # NO PARENTHESES WHEN ASSIGNING FUNCTION THAT IS TO BE CALLED AS MEMBER OF DICTIONARY.
        self.dic_Tabnames["Current"] = self.WriteProjectTabTitle
        self.szr_Menu.Add(self.btn_Current, 0, wx.ALL, 0)
        self.szr_Menu.Add((150,-1), -1, wx.ALL,0)
        # Help
        self.btn_Help = CustomBitmapButton(self.pnl_Menu,
                                           type = u"Help",
                                           index = 5,
                                           size = (150,50),
                                           pathaddendum = u"sidebar")
        self.btn_Help.Enable(True)
        self.szr_Menu.Add(self.btn_Help, 0, wx.ALL, 0)
        # Version
        self.lbl_Version = wx.StaticText(self.pnl_Menu,
                                         label = u"Build: 1.1.0"
                                         + "\n2022-09-14"
                                         + "\n20:27 GMT")
        self.szr_Menu.Add(self.lbl_Version, 0, wx.EXPAND, 0)
        self.pnl_Menu.SetSizer(self.szr_Menu)
        self.pnl_Menu.Layout()
        self.szr_Menu.Fit(self.pnl_Menu)
        self.szr_Main.Add(self.pnl_Menu, 0, wx.EXPAND |wx.ALL, 0)
        # END OF SIDE BAR MENU ##########################################################

        # WorkPane
        self.szr_WorkPane = wx.BoxSizer(wx.VERTICAL)

        ##### # ##### #     #####  ####   ###  ####
          #   #   #   #     #      #   # #   # #   #
          #   #   #   #     ###    ####  ##### ####
          #   #   #   #     #      #   # #   # #   #
          #   #   #   ##### #####  ####  #   # #   # ####################################

        self.szr_Titlebar = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_Titlebar = wx.Panel(self)
        self.pnl_Titlebar.SetBackgroundColour(cs.BgMediumDark)
        self.szr_InsideTitleBar = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_TitleBarText = wx.Panel(self.pnl_Titlebar)
        self.szr_TitleBarText = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_TitleBarText = wx.StaticText(self.pnl_Titlebar, label = wx.EmptyString)
        self.lbl_TitleBarText.Wrap(-1)
        self.szr_TitleBarText.Add(self.lbl_TitleBarText, 1, wx.ALL, 5)
        self.pnl_TitleBarText.SetSizer(self.szr_TitleBarText)
        self.pnl_TitleBarText.Layout()
        self.szr_InsideTitleBar.Add(self.pnl_TitleBarText, 1, wx.ALL, 0)
        # btn_Minimise
        self.btn_Minimise = wx.BitmapButton(self.pnl_Titlebar,
                                            style = wx.BU_AUTODRAW|wx.BORDER_NONE)
        self.btn_Minimise.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                              + r"\btn_minimise.png",
                                              wx.BITMAP_TYPE_ANY))
        self.btn_Minimise.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                     + r"\btn_minimise_pressed.png",
                                                     wx.BITMAP_TYPE_ANY))
        self.btn_Minimise.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                     + r"\btn_minimise_mouseover.png",
                                                     wx.BITMAP_TYPE_ANY))
        self.btn_Minimise.SetMaxSize(wx.Size(46,34))
        self.szr_InsideTitleBar.Add(self.btn_Minimise, 0, wx.ALL, 0)
        # btn_Cascade
        self.btn_Cascade = wx.BitmapButton(self.pnl_Titlebar,
                                           style = wx.BU_AUTODRAW|wx.BORDER_NONE)
        self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                             + r"\btn_cascade.png",
                                             wx.BITMAP_TYPE_ANY))
        self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                    + r"\btn_cascade_pressed.png",
                                                    wx.BITMAP_TYPE_ANY))
        self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                    + r"\btn_cascade_mouseover.png",
                                                    wx.BITMAP_TYPE_ANY))
        self.btn_Cascade.SetMaxSize(wx.Size(46,34))
        self.szr_InsideTitleBar.Add(self.btn_Cascade, 0, wx.ALL, 0)
        # btn_Close
        self.btn_Close = wx.BitmapButton(self.pnl_Titlebar,
                                         style = wx.BU_AUTODRAW|wx.BORDER_NONE)
        self.btn_Close.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                           + r"\btn_close.png",
                                           wx.BITMAP_TYPE_ANY))
        self.btn_Close.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                  + r"\btn_close_pressed.png",
                                                  wx.BITMAP_TYPE_ANY))
        self.btn_Close.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                  + r"\btn_close_mouseover.png",
                                                  wx.BITMAP_TYPE_ANY))
        self.btn_Close.SetMaxSize(wx.Size(46,34))
        self.szr_InsideTitleBar.Add(self.btn_Close, 0, wx.ALL, 0)
        self.pnl_Titlebar.SetSizer(self.szr_InsideTitleBar)
        self.pnl_Titlebar.Layout()
        self.szr_InsideTitleBar.Fit(self.pnl_Titlebar)
        self.szr_Titlebar.Add(self.pnl_Titlebar, 1, wx.EXPAND |wx.ALL, 0)
        self.szr_WorkPane.Add(self.szr_Titlebar, 0, wx.EXPAND, 0)
        # END OF TITLE BAR ##############################################################

        #   # #####  ###  ####  ##### ####   ####
        #   # #     #   # #   # #     #   # #
        ##### ###   ##### #   # ###   ####   ###
        #   # #     #   # #   # #     #   #     #
        #   # ##### #   # ####  ##### #   # ####  #######################################
        #
        # Full name of assay or other title (e.g. "Tools" tab, "Settings" tab
        # (once implemented)) will be shown
        #
        self.szr_Header = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Header = wx.Panel(self, size = wx.Size(-1,70))
        self.pnl_Header.SetBackgroundColour(self.clr_Medium)
        self.pnl_Header.SetForegroundColour(self.clr_HeaderText)
        self.szr_Banner = wx.BoxSizer(wx.VERTICAL)
        self.szr_Banner.Add((0, -1), 0, wx.EXPAND, 5)
        self.lbl_Banner = wx.StaticText(self.pnl_Header, label = self.HomeText())
        self.lbl_Banner.Wrap(-1)
        self.lbl_Banner.SetFont(wx.Font(25, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                        wx.FONTWEIGHT_NORMAL, False, wx.EmptyString))
        self.szr_Banner.Add(self.lbl_Banner, 0, wx.ALL, 15)
        self.pnl_Header.SetSizer(self.szr_Banner)
        self.pnl_Header.Layout()
        self.szr_Banner.Fit(self.pnl_Header)
        self.szr_Header.Add(self.pnl_Header, 1, wx.EXPAND, 0)
        self.szr_WorkPane.Add(self.szr_Header, 0, wx.EXPAND, 0)
        # END OF HEADER #################################################################

        #####  ###  ####   ####
          #   #   # #   # #
          #   ##### ####   ###
          #   #   # #   #     #
          #   #   # ####  ####  #########################################################

        self.szr_Book = wx.BoxSizer(wx.VERTICAL)
        self.sbk_WorkArea = wx.Simplebook(self)
        # Dictionary to hole page indices
        self.dic_WorkAreaPageIndices = {}

        self.str_Assays = os.path.join(self.dir_Path,"assays.csv")
        self.str_Pinned = os.path.join(Path.home(),"bbq_pinned.csv")
        if os.path.isfile(self.str_Pinned) == True:
            csv_Pinned = list(csv.reader(open(self.str_Pinned,"r")))
            for assay in self.dfr_Assays.index:
                if assay in csv_Pinned[0]:
                    self.dfr_Assays.loc[assay,"Pinned"] = True
                else:
                    self.dfr_Assays.loc[assay,"Pinned"] = False

        # "Home" Tab ####################################################################
        self.sbk_WorkArea.AddPage(page = Home.HomeScreen(self.sbk_WorkArea, self),
                                  text = u"Home")
        self.dic_WorkAreaPageIndices["Home"] = self.sbk_WorkArea.GetPageCount() - 1
        self.tab_Home = self.sbk_WorkArea.GetChildren()[0]

        # "New Project" tab #############################################################
        self.sbk_WorkArea.AddPage(page = Home.pnl_Projects(self.sbk_WorkArea, self),
                                  text = u"New")
        self.dic_WorkAreaPageIndices["New"] = self.sbk_WorkArea.GetPageCount() - 1

        # "Tools" tab ###################################################################
        self.pnl_Tools = wx.Panel(self.sbk_WorkArea)
        self.pnl_Tools.SetBackgroundColour(self.clr_Medium)
        self.pnl_Tools.SetForegroundColour(self.clr_HeaderText)
        self.szr_Tools = wx.BoxSizer(wx.VERTICAL)
        self.sbk_Tools = wx.Simplebook(self.pnl_Tools, size = wx.Size(-1,-1))
        self.szr_Tools.Add(self.sbk_Tools, 1, wx.EXPAND, 10)
        # Sub-tab for the buttons
        self.pnl_ToolSelection = wx.Panel(self.sbk_Tools)
        self.pnl_ToolSelection.SetBackgroundColour(self.clr_Medium)
        self.pnl_ToolSelection.SetForegroundColour(self.clr_HeaderText)
        self.szr_ToolSelection = wx.BoxSizer(wx.VERTICAL)
        self.szr_ToolsTransferFile = wx.BoxSizer(wx.VERTICAL)
        self.btn_CreateTransferFile = CustomBitmapButton(self.pnl_ToolSelection,
                                                         type = u"CreateTransfer",
                                                         index = 0,
                                                         size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_CreateTransferFile, 0, wx.ALL, 5)
        self.btn_TransferFileProcessor = CustomBitmapButton(self.pnl_ToolSelection,
                                                            type = u"ProcessTransfer",
                                                            index = 0,
                                                            size = (260,50))
        self.szr_ToolsTransferFile.Add(self.btn_TransferFileProcessor, 0, wx.ALL, 5)
        self.szr_ToolSelection.Add(self.szr_ToolsTransferFile, 0, wx.ALL, 5)
        self.pnl_ToolSelection.SetSizer(self.szr_ToolSelection)
        self.pnl_ToolSelection.Layout()
        self.szr_ToolSelection.Fit(self.pnl_ToolSelection)
        self.sbk_Tools.ShowNewPage(self.pnl_ToolSelection)
        self.sbk_Tools.SetSelection(0)
        self.ActiveTool = None
        self.pnl_Tools.SetSizer(self.szr_Tools)
        self.pnl_Tools.Layout()
        self.szr_Tools.Fit(self.pnl_Tools)
        self.sbk_WorkArea.AddPage(page = self.pnl_Tools,
                                  text = u"Tools")
        self.dic_WorkAreaPageIndices["Tools"] = self.sbk_WorkArea.GetPageCount() - 1

        # Add notebook to szr_WorkPane
        self.szr_Book.Add(self.sbk_WorkArea, 1, wx.EXPAND|wx.ALL, 0)
        self.szr_WorkPane.Add(self.szr_Book, 1, wx.EXPAND, 0)

        self.szr_Main.Add(self.szr_WorkPane, 1, wx.EXPAND, 5)

        self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["Home"])

        # Finalising
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.Centre(wx.BOTH)


        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #   
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ####################################################

        # Title bar
        self.btn_Close.Bind(wx.EVT_BUTTON, self.OnBtnClose)
        self.btn_Minimise.Bind(wx.EVT_BUTTON, self.OnBtnMinimise)
        self.btn_Cascade.Bind(wx.EVT_BUTTON, self.OnBtnCascade)
        self.pnl_TitleBarText.Bind(wx.EVT_LEFT_DCLICK, self.OnBtnCascade)

        # Side Panel Menu
        self.btn_Home.Bind(wx.EVT_BUTTON, self.OnSidebarButton)
        self.btn_New.Bind(wx.EVT_BUTTON, self.OnSidebarButton)
        self.btn_Open.Bind(wx.EVT_BUTTON, self.OnBtnOpen)
        self.btn_Tools.Bind(wx.EVT_BUTTON, self.OnSidebarButton)
        self.btn_Current.Bind(wx.EVT_BUTTON, self.OnSidebarButton)
        self.btn_Help.Bind(wx.EVT_BUTTON, self.OnBtnHelp)

        # Tools Tab
        self.btn_CreateTransferFile.Bind(wx.EVT_BUTTON, self.ToolTransferFileMaker)
        self.btn_TransferFileProcessor.Bind(wx.EVT_BUTTON, self.ToolTransferFileProcessor)

        # New Project buttons
        # Dynamically bound

        # Closing
        self.Bind(wx.EVT_CLOSE, self.OnBtnClose)

        self.Show()

    def __del__(self):
        pass

    ##### #   # ##### #   # #####    #   #  ###  #   # ####  #     ##### ####   ####
    #     #   # #     ##  #   #      #   # #   # ##  # #   # #     #     #   # #
    ###   #   # ###   #####   #      ##### ##### ##### #   # #     ###   ####   ###
    #      # #  #     #  ##   #      #   # #   # #  ## #   # #     #     #   #     #
    #####   #   ##### #   #   #      #   # #   # #   # ####  ##### ##### #   # ####  ####

    def OnBtnClose(self, event):
        """
        Event handler.
        Performs checks before closing program, then deletes
        temp directory, then closes program.
        """
        if self.sbk_WorkArea.GetPageCount() > 3:
            # If more than four pages are in simplebook, then
            # an analysis is open/in progress.
            bol_AllowCancel = msg.QueryCloseProgram()
        else:
            bol_AllowCancel = True
        if bol_AllowCancel == True:
            # Clean up, then exit
            self.DeleteBBQTempDirectory()
            self.icn_Taskbar.RemoveIcon()
            wx.Exit()

    def OnBtnMinimise(self, event):
        """
        Event handler. Minimises window
        """
        self.Iconize(True)

    def OnBtnCascade(self,event):
        """
        Event handler.  Toggles between maximised and cascading window.
        Image files for button get changed to reflect this. Follows
        standard Windows design.
        """
        if self.IsMaximized() == False:
            # Change button
            self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                 + r"\btn_cascade.png",
                                                 wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_cascade_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            # Maximize
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)
            self.Maximize(True)
            self.SetWindowStyle(wx.RESIZE_BORDER)
            # Unbind functions for window dragging
            self.pnl_TitleBarText.Unbind(wx.EVT_LEFT_DOWN)
            self.Unbind(wx.EVT_LEFT_UP)
            self.Unbind(wx.EVT_MOTION)
        else:
            # Change button
            self.btn_Cascade.SetBitmap(wx.Bitmap(self.str_TitleButtonsPath
                                                 + r"\btn_maximize.png",
                                                 wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapPressed(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_maximize_pressed.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.btn_Cascade.SetBitmapCurrent(wx.Bitmap(self.str_TitleButtonsPath
                                                        + r"\btn_maximize_mouseover.png",
                                                        wx.BITMAP_TYPE_ANY))
            self.SetWindowStyle(wx.TAB_TRAVERSAL)
            self.Maximize(False)
            # Bind functions for window dragging:
            self.pnl_TitleBarText.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
            self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
            self.Bind(wx.EVT_MOTION, self.OnMouseMove)

    # The following three function are taken from a tutorial on the wxPython Wiki:
    # https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def OnMouseMove(self, event):
        """
        Event handler to drag the window.
        """
        if event.Dragging() and event.LeftIsDown():
            x,y = self.ClientToScreen(event.GetPosition())
            newPos = (x - self.delta[0], y - self.delta[1])
            self.Move(newPos)

    def OnLeftDown(self, event):
        """
        Event handler to capture mouse and get window position for
        window dragging.
        """
        # Important change from tutorial code: Added offset for dx.
        # It is not the whole frame that has the function bound to it,
        # only the pnl_TitleBarText. Since the menu panel next to it 
        # s 150px wide, this offset needs to be accounted for.
        self.CaptureMouse()
        x, y = self.ClientToScreen(event.GetPosition())
        originx, originy = self.GetPosition()
        dx = x - originx + 150 # Offset for menu panel width.
        dy = y - originy
        self.delta = [dx, dy]

    def OnLeftUp(self, event):
        """
        Releases capture if left mouse button is released.
        """
        if self.HasCapture():
            self.ReleaseMouse()
    
    def OnSidebarButton(self, event, Type = None):
        """
        Event handler.
        Changes selection of sbk_WorkArea simplebood, deactivates
        all other buttons in sidebar menu, and Disables/Enables button
        for current project, if there is one.

        Arguments:
            event -> wx event.
            Type -> string. Optional. If function is not called from
                    an event, provide the type of button ("Home",
                    "New", etc.) the pressing of which is simulated.
        """

        # Dictionary dic_SidebarButtonGroup must be populated with all
        # buttons on the sidebar menu. 
        # Dictionary dic_Tabnames must be populated with the names to be displayed.
        # Type is included as keyword argument in case you might want to use
        # this function other than as an event handler.
        
        if Type == None:
            Type = event.GetEventObject().Type
        self.sbk_WorkArea.ChangeSelection(self.dic_WorkAreaPageIndices[Type])
        # There might be a method or a string in the dictionary:
        try: self.lbl_Banner.SetLabel(self.dic_Tabnames[Type]())
        except: self.lbl_Banner.SetLabel(self.dic_Tabnames[Type])
        self.sbk_WorkArea.Update()
        for button in self.dic_SidebarButtonGroup.keys():
            if not self.dic_SidebarButtonGroup[button].Type == Type:
                self.dic_SidebarButtonGroup[button].IsCurrent(False)
            else:
                self.dic_SidebarButtonGroup[button].IsCurrent(True)
        if not self.ProjectTab == None:
            self.btn_Current.Enable(True)
        else:
            self.btn_Current.Enable(False)

    def OnBtnOpen(self, event):
        """
        Event handler for opening a saved project.
        """
        if self.ActiveProject() == True:
            return None
        with wx.FileDialog(self, "Open BBQ file", wildcard="BBQ files (*.bbq)|*.bbq",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return None     # the user changed their mind
            # Proceed loading the file chosen by the user
            self.Open(fileDialog.GetPath(), fileDialog.GetFilename())

    def OnBtnHelp(self, event):
        """
        Event handler to display user manual.
        """
        pdfpath = os.path.join(self.dir_Path, "bbq_manual.pdf")
        subprocess.Popen([pdfpath], shell=True)

    def ToolTransferFileMaker(self, event):
        """
        Event handler to launch tool Transfer File Maker
        """
        self.sbk_Tools.ShowNewPage(tools.panel_TransferFileMaker(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Transfer file maker")

    def ToolTransferFileProcessor(self, event):
        """
        Event handler to launch tool Transfer File Processor
        """
        self.sbk_Tools.ShowNewPage(tools.panel_TransferFileProcessor(self.sbk_Tools, self))
        self.ActiveTool = self.sbk_Tools.GetPageCount()-1
        self.sbk_Tools.SetSelection(self.ActiveTool)
        self.lbl_Banner.SetLabel("Process a transfer file")

    def CloseActiveTool(self, event):
        """
        Event handler. Closes currently active tool.
        """
        self.sbk_Tools.SetSelection(0)
        pages = self.sbk_Tools.GetChildren()
        panel = pages[self.ActiveTool]
        del(panel)
        self.ActiveTool = None
        self.lbl_Banner.SetLabel("Tools")

    def Cancel(self, event):
        """
        Cancels a project by deleting the corresponding project tab.
        """
        self.Freeze()
        if msg.QueryDiscardChanges() == True:
            self.ProjectTab.ButtonBar.EnableButtons(False)
            self.sbk_WorkArea.DeletePage(self.ProjectTab.Index)
            self.ProjectTab = None
            self.OnSidebarButton(None, Type="Home")
            self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["Home"])
        self.Thaw()

    # END OF EVENT HANDLERS #############################################################

    def HomeText(self):
        """
        Sets the welcome text on top of the home panel based on the time of day.
        """
        #return "Good morning"
        hour = int(str(datetime.datetime.now())[10:13])
        if hour < 7:
            return "It's a bit early, isn't it?"
        elif hour >= 7 and hour < 12:
            return "Good morning"
        elif hour >= 12 and hour < 13:
            return "Lunchtime?"
        elif hour >= 13 and hour < 17:
            return "Good afternoon"
        elif hour >= 17 and hour < 20:
            return "Good evening"
        elif hour >= 20:
            return "It's a bit late, isn't it?"

    def WriteProjectTabTitle(self):
        """
        Returns title of project tab.
        """
        if not self.ProjectTab == None:
            return self.ProjectTab.Title
        else:
            return "Fnord"

    def AnalyseData(self, event = None, tabname = None):
        """
        Freezes the main window and creates the progress dialog.
        Then calls the ProcessData() function of the current project
        panel as a new thread. The ProcessData() function unfreezes
        the main window once the analysis is complete.
        """
        if tabname == None:
            ProjectTab = event.GetEventObject().parent.Tabname
        else:
            ProjectTab = tabname
        self.Freeze()
        self.dlg_Progress = prog.ProgressDialog(self)
        self.dlg_Progress.Show()
        self.dlg_Progress.btn_Close.Enable(False)
        self.thd_Analysis = threading.Thread(target=ProjectTab.ProcessData,
                                             args=(self.dlg_Progress,),
                                             daemon=True)
        self.thd_Analysis.start()

    def DeleteBBQTempDirectory(self):
        """
        Checks whether the temporary directory exists.
        If so, it gets deleted so that we're not running
        into problems with it existing and being unable to
        be overwritten later.
        """
        # Check whether temporary directory exists. if so, delete it.
        str_TempDir = os.path.join(Path.home(),"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)

     ###  ####  ##### #   #    ###  #   # ####     ####  ###  #   # #####
    #   # #   # #     ##  #   #   # ##  # #   #   #     #   # #   # #
    #   # ####  ###   #####   ##### ##### #   #    ###  ##### #   # ###
    #   # #     #     #  ##   #   # #  ## #   #       # #   #  # #  #
     ###  #     ##### #   #   #   # #   # ####    ####  #   #   #   ##### ###############

    def Open(self, str_FilePath, str_FileName):
        """
        Opens saved project.

        Arguments:
            str_FilePath -> string. Full path of project file.
            str_FileName -> string. File name only of project file.
        """
        # Extracts bbq archive into temporary directory and reads each file to
        # import into dataframe.
        # Based on the assay specified in the bbq archive, a new appropriate project is opened and the
        # loaded dataframe is handed to the PopulateFromFile() function of the analyis panel.
        self.Freeze()
        # Check whether temporary directory exists. if so, delete and make fresh
        str_TempDir = os.path.join(Path.home(),"bbqtempdir")
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
        else:
            # Extract saved file to temporary directory
            with zf.ZipFile(str_FilePath, "r") as zip:
                zip.extractall(str_TempDir)
            # Read details.csv
            dfr_Details = pd.read_csv(str_TempDir + r"\details.csv", sep = ",",
                                      header=0, index_col=0, engine="python")
            # Ensure backwards compatibility by making sure that all things are string
            for i in range(len(dfr_Details)):
                if type(dfr_Details.iloc[i,0]) != str:
                    if pd.isna(dfr_Details.iloc[i,0]) == True:
                        dfr_Details.iloc[i,0] = "NA"
            if dfr_Details.iloc[0,0] == "nanoDSF":
                str_WellsOrCapillaries = "Capillaries"
            else:
                str_WellsOrCapillaries = "Wells"
            # Read boolean.csv
            dfr_Boolean = pd.read_csv(str_TempDir + r"\boolean.csv", sep=",",
                                      header=0, index_col=0, engine="python")
            # Read in meta.csv. Find better name for file
            dfr_Meta = pd.read_csv(str_TempDir + r"\meta.csv", sep=",",
                                   header=0, index_col=0, engine="python")
            # Read paths.csv -> Contains references to file locations
            dfr_Paths = pd.read_csv(str_TempDir + r"\paths.csv", sep=",",
                                    header=0, index_col=0, engine="python")
            # Create new dataframe to hold raw and analysed data with meta data from dfr_Meta
            lst_DataframeHeaders = ["DestinationPlateName","Samples",
                                    str_WellsOrCapillaries,"DataFileName","RawDataFrame",
                                    "ProcessedDataFrame", "Layout","References"]
            dfr_Loaded = pd.DataFrame(index=range(len(dfr_Meta)),columns=lst_DataframeHeaders)
            # Go through each plate in the dataframe
            for i in range(len(dfr_Meta)):
                # Load first fields into loaded dataframe
                dfr_Loaded.at[i,"DestinationPlateName"] = dfr_Meta.loc[i,"DestinationPlateName"]
                dfr_Loaded.at[i,str_WellsOrCapillaries] = dfr_Meta.loc[i,str_WellsOrCapillaries]
                dfr_Loaded.at[i,"DataFileName"] = dfr_Meta.loc[i,"DataFileName"]
                str_Subdirectory = str_TempDir + chr(92) + dfr_Meta.iloc[i,0] # Unicode 92 is back slash
                # read samples
                dfr_Samples = pd.read_csv(str_Subdirectory + r"\samples.csv", sep=",",
                                          header=0, index_col=0, engine="python")
                for j in dfr_Samples.columns:
                    if type(dfr_Samples.loc[0,j]) == str:
                        dfr_Samples[j] = dfr_Samples[j].apply(import_string_to_list)
                dfr_Loaded.at[i,"Samples"] = dfr_Samples
                # read in rawdata.csv. Do per plate
                dfr_RawData = pd.read_csv(str_Subdirectory + r"\rawdata.csv", sep=",",
                                          header=0, index_col=0, engine="python")
                for j in dfr_RawData.columns:
                    if type(dfr_RawData.loc[0,j]) == str:
                        dfr_RawData[j] = dfr_RawData[j].apply(import_string_to_list)
                dfr_Loaded.at[i,"RawDataFrame"] = dfr_RawData
                # Read in processed data file/frame
                dfr_Processed = pd.read_csv(str_Subdirectory + r"\processed.csv", sep=",",
                                            header=0, index_col=0, engine="python")
                for k in dfr_Processed.columns:
                    if type(dfr_Processed.loc[0,k]) == str:
                        dfr_Processed[k] = dfr_Processed[k].apply(import_string_to_list)
                dfr_Loaded.at[i,"ProcessedDataFrame"] = dfr_Processed
                # Read in references (i.e. samples that are used to normalise
                # data against, e.g. solvent/buffer only for background/signal
                # baseline or known inhibitors that give 100% effect). Assumes
                # ONE each of solvent reference, buffer reference, control compound.
                dfr_References = pd.read_csv(str_Subdirectory + r"\references.csv", sep=",",
                                             header=0, index_col=0, engine="python")
                # Backwards compatiblity: was previously a list, so indices and
                # column names need updating:
                if dfr_References.columns[0] == "0":
                    dfr_References = dfr_References.rename(columns={"0":0})
                if dfr_References.columns[0] == "References":
                    dfr_References_Convert = pd.DataFrame(columns=[0],
                                                          index=["SolventMean",
                                                                 "SolventMedian",
                                                                 "SolventSEM",
                                                                 "SolventSTDEV",
                                                                 "SolventMAD",
                                                                 "BufferMean",
                                                                 "BufferMedian",
                                                                 "BufferSEM",
                                                                 "BufferSTDEV",
                                                                 "BufferMAD",
                                                                 "ControlMean",
                                                                 "ControlMedian",
                                                                 "ControlSEM",
                                                                 "ControlSTDEV",
                                                                 "ControlMAD",
                                                                 "ZPrimeMean",
                                                                 "ZPrimeMeadian"])
                    # Solvent reference
                    dfr_References_Convert.at["SolventMean",0] = dfr_References.iloc[0,0]
                    dfr_References_Convert.at["SolventMedian",0] = np.nan
                    dfr_References_Convert.at["SolventSEM",0] = dfr_References.iloc[1,0]
                    dfr_References_Convert.at["SolventSTDEV",0] = np.nan
                    dfr_References_Convert.at["SolventMAD",0] = np.nan
                    # Buffer reference
                    dfr_References_Convert.at["BufferMean",0] = dfr_References.iloc[4,0]
                    dfr_References_Convert.at["BufferMedian",0] = np.nan
                    dfr_References_Convert.at["BufferSEM",0] = dfr_References.iloc[5,0]
                    dfr_References_Convert.at["BufferSTDEV",0] = np.nan
                    dfr_References_Convert.at["BufferMAD",0] = np.nan
                    # Control compound
                    dfr_References_Convert.at["ControlMean",0] = dfr_References.iloc[2,0]
                    dfr_References_Convert.at["ControlMedian",0] = np.nan
                    dfr_References_Convert.at["ControlSEM",0] = dfr_References.iloc[3,0]
                    dfr_References_Convert.at["ControlSTDEV",0] = np.nan
                    dfr_References_Convert.at["ControlMAD",0] = np.nan
                    # Quality metrics
                    dfr_References_Convert.at["ZPrimeMean",0] = dfr_References.iloc[6,0]
                    dfr_References_Convert.at["ZPrimeMedian",0] = dfr_References.iloc[7,0]
                    # Overwrite
                    dfr_References = dfr_References_Convert
                dfr_Loaded.at[i,"References"] = dfr_References
                # Read in layout
                dfr_Layout = pd.read_csv(str_Subdirectory + r"\layout.csv", sep=",", 
                                         header=0, index_col=0, engine="python")
                for k in dfr_Layout.columns:
                    if type(dfr_Layout.loc[0,k]) == str:
                        dfr_Layout[k] = dfr_Layout[k].apply(import_string_to_list)
                dfr_Loaded.at[i,"Layout"] = dfr_Layout
            # Remove all the temporary files
            shutil.rmtree(str_TempDir)
            # Ensure backwards compatibility for details. Previously, was
            # just a list, from version 1.0.8 onwards a full dataframe
            if dfr_Details.index[0] == 0: # we are dealing with the old list style!
                dfr_Details.set_index(pd.Index(["AssayType","AssayCategory","PurificationID",
                                                "ProteinConcentration","PeptideID",
                                                "PeptideConcentration","Solvent",
                                                "SolventConcentration","Buffer","ELN",
                                                "AssayVolume","DataFileExtension",
                                                "SampleSource","Device","Date"]),
                                                inplace=True)
                dfr_Details = dfr_Details.rename(columns={"AssayDetails":"Value"})
                if dfr_Details.iloc[1,0] == "single_dose":
                    dfr_Details.loc["Shorthand","Value"] = "EPSD"
                elif dfr_Details.iloc[1,0] == "dose_response":
                    dfr_Details.loc["Shorthand","Value"] = "EPDR"
                elif dfr_Details.iloc[1,0] == "dose_response_time_course":
                    dfr_Details.loc["Shorthand","Value"] = "DRTC"
                elif dfr_Details.iloc[1,0] == "thermal_shift":
                    if dfr_Details.iloc[0,0] == "nanoDSF":
                        dfr_Details.loc["Shorthand","Value"] = "NDSF"
                    else:
                        dfr_Details.loc["Shorthand","Value"] = "DSF"
                elif dfr_Details.iloc[1,0] == "rate":
                    dfr_Details.loc["Shorthand","Value"] = "RATE"
            # start new project based on dfr_Details.loc["Shorthand","Value"] (was =lst_Details[0])
            self.StartNewProject(None, dfr_Details.loc["Shorthand","Value"])
            # Hand over loaded data to populate tab
            self.ProjectTab.PopulateFromFile(dfr_Details,
                                             dfr_Boolean.BooleanVariables.tolist(),
                                             dfr_Loaded,
                                             dfr_Paths.Path.tolist())
            # Display file name on header
            self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(str_FilePath)
            # Update py files:
            int_Slash = str(str_FilePath).rfind(chr(92))+1
            str_FileName = str_FilePath[int_Slash:]
            self.tab_Home.UpdateRecent(str_FilePath,
                                       str_FileName,
                                       dfr_Details.loc["AssayCategory","Value"],
                                       dfr_Details.loc["Shorthand","Value"])
            self.Thaw()

    def SaveFileAs(self, event):
        """
        Wrapper function for SaveFile() with 'saveas'argument provided
        as True.
        """
        self.SaveFile(saveas=True)

    def SaveFile(self, event = None, tabname = None, saveas = False):
        """
        Saves current project to .bbq archive.

        Arguments:
            event -> wx event
            tabname -> string. part of wx app that holds the actual
                       project data.
            saveas -> boolean. Sets behaviour to typical "save as"
                      option, i.e. prompting user to select new
                      location and file name.
        """
        
        if tabname == None:
            tabname = self.ProjectTab
        # Make sure an analysis has been performed and the dataframe has been constructed properly
        if len(tabname.dfr_AssayData) > 0:
            # Check if the project has been saved previously or "save as" has been selected.
            # If so, show file dialog:
            if tabname.bol_PreviouslySaved == False or saveas == True:
                with wx.FileDialog(tabname, "Save project file",
                                   wildcard = "BBQ files (*.bbq)|*.bbq",
                                   style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT) as fileDialog:
                    # Exit via returning nothing if the user changed their mind
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        return
                    str_SaveFilePath = fileDialog.GetPath()
                    # Prevent duplication of file extension
                    if str_SaveFilePath.find(".bbq") == -1:
                        str_SaveFilePath = str_SaveFilePath + ".bbq"
                    # Update file path property
                    tabname.str_SaveFilePath = str_SaveFilePath
                    # Get file name:
                    str_FileName = fileDialog.GetFilename()
                    if str_FileName.find(".bbq") == -1:
                        str_FileName = str_FileName + ".bbq"
            else:
                str_FileName = tabname.str_SaveFilePath
                int_Slash = str(str_FileName).rfind(chr(92))+1
                str_FileName = str_FileName[int_Slash:]
            # Make sure assay detail variables are updated
            tabname.SaveAssayDetails(bol_FromTabChange = False)
            # Prep boolean variables as list to hand over
            lst_Boolean = [tabname.bol_AssayDetailsChanged, tabname.bol_AssayDetailsCompleted,
                           tabname.bol_DataFilesAssigned, tabname.bol_DataFilesUpdated,
                           tabname.bol_DataAnalysed, tabname.bol_ELNPlotsDrawn,
                           tabname.bol_ExportPopulated, tabname.bol_ResultsDrawn,
                           tabname.bol_ReviewsDrawn, tabname.bol_TransferLoaded,
                           tabname.bol_GlobalLayout, tabname.bol_PlateID,
                           tabname.bol_PlateMapPopulated]
            # Prep file paths to hand over
            dfr_Paths = pd.DataFrame([tabname.str_TransferPath,tabname.str_DataPath],
                                     columns=["Path"])
            # Hand everything over
            saved = self.WriteToArchive(tabname.str_SaveFilePath, 
                                        tabname.dfr_AssayData,
                                        tabname.dfr_Details,
                                        lst_Boolean,
                                        dfr_Paths)
            if saved == True:
                self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(tabname.str_SaveFilePath)
                # Let the program know that the file has been saved previously
                # -> Affects behaviour of "Save" button.
                tabname.bol_PreviouslySaved = True
                # Add file to recent files list
                self.tab_Home.UpdateRecent(tabname.str_SaveFilePath,
                                           str_FileName,
                                           tabname.str_AssayCategory,
                                           tabname.str_Shorthand)
                msg.SaveSuccess()
            else:
                msg.SavePermissionDenied()
        else:
            msg.SaveErrorNoAnalysis()

    def WriteToArchive(self, str_SaveFilePath, dfr_AssayData,
                       dfr_Details, lst_Boolean, dfr_Paths):
        """
        Writes the dataframes and lists into csv files and
        packages them into a zip archive.
        
        Arguments:
            str_SaveFilePath -> string. path of saved file
            dfr_AssayData -> pandas dataframe holding all assay data
            dfr_Details -> pandas dataframe. Meta data of experiment
            lst_Boolean -> list. Boolean variables defining the
                           state/behaviour of the project (e.g. has a
                           certain tab been populated, has the file
                           been saved before...)
            dfr_Paths -> pandas dataframe. Paths of all files provided
                         by the user.

        Returns True on succesful save.
        """
        # Separated from main  saving function to simplify code for human readability.
        
        try:
            zip_BBQ = zf.ZipFile(str_SaveFilePath, "w")
        except:
            return False

        str_TempDir = os.path.join(Path.home(),"bbqtempdir")
        # Check whether temporary directory exists. if so, delete and make fresh
        if os.path.isdir(str_TempDir) == True:
            shutil.rmtree(str_TempDir)
            os.mkdir(str_TempDir)
        else:
            os.mkdir(str_TempDir)
        # Paths
        dfr_Paths.to_csv(str_TempDir + r"\paths.csv")
        # .write(name_of_file_to_write, arcname=name_to_give_file_in_archive, other arguments)
        # file names contain path. for arcname, use relative paths inside archive.
        zip_BBQ.write(str_TempDir + r"\paths.csv", arcname="paths.csv")
        # Assay details
        dfr_Details.to_csv(str_TempDir + r"\details.csv")
        zip_BBQ.write(str_TempDir + r"\details.csv", arcname="details.csv")
        # Boolean status variables
        dfr_Boolean = pd.DataFrame(lst_Boolean,columns=["BooleanVariables"])
        dfr_Boolean.to_csv(str_TempDir + r"\boolean.csv")
        zip_BBQ.write(str_TempDir + r"\boolean.csv", arcname="boolean.csv")
        # Make dataframe with fields of dataframe that do not hold other dataframes
        if dfr_Details.loc["AssayType","Value"] == "nanoDSF":
            str_WellsOrCapillaries = "Capillaries"
        else:
            str_WellsOrCapillaries = "Wells"
        dfr_Meta = dfr_AssayData[["DestinationPlateName",
                                          str_WellsOrCapillaries,
                                          "DataFileName"]]
        dfr_Meta.to_csv(str_TempDir + r"\meta.csv")
        zip_BBQ.write(str_TempDir + r"\meta.csv", arcname="meta.csv")
        # Save all the fields that hold dataframes in separate folders
        # (one folder per plate/set of capillaries)
        for i in range(len(dfr_AssayData)):
            str_Subdirectory = os.path.join(str_TempDir,
                                            dfr_AssayData.loc[i,"DestinationPlateName"])
            os.mkdir(str_Subdirectory)
            str_Subdirectory_relative = dfr_AssayData.loc[i,"DestinationPlateName"] + chr(92)
            # Samples
            dfr_AssayData.loc[i,"Samples"].to_csv(str_Subdirectory + r"\samples.csv")
            zip_BBQ.write(str_Subdirectory + r"\samples.csv",
                          arcname=str_Subdirectory_relative+"samples.csv")
            # Raw data
            dfr_AssayData.loc[i,"RawDataFrame"].to_csv(str_Subdirectory + r"\rawdata.csv")
            zip_BBQ.write(str_Subdirectory + r"\rawdata.csv",
                          arcname=str_Subdirectory_relative+"rawdata.csv")
            # Processed data
            dfr_AssayData.loc[i,"ProcessedDataFrame"].to_csv(str_Subdirectory + r"\processed.csv")
            zip_BBQ.write(str_Subdirectory + r"\processed.csv",
                          arcname=str_Subdirectory_relative+"processed.csv")
            # Plate layouts
            dfr_Layout = dfr_AssayData.loc[i,"Layout"]
            dfr_Layout.to_csv(str_Subdirectory + r"\layout.csv")
            zip_BBQ.write(str_Subdirectory + r"\layout.csv",
                          arcname=str_Subdirectory_relative+"layout.csv")
            # List of reference wells
            dfr_AssayData.loc[i,"References"].to_csv(str_Subdirectory + r"\references.csv")
            zip_BBQ.write(str_Subdirectory + r"\references.csv",
                          arcname=str_Subdirectory_relative+"references.csv")
        zip_BBQ.close()
        # Remove all the temporary files
        shutil.rmtree(str_TempDir)
        return True

    def FindAssays(self):
        """
        Scans assay directory and lists all valid assay workflow definitions.
        Returns:
            - pandas dataframe with metadata for assay, index is assay
              shorthand codes:
                    - full assay name
                    - assay subdirectory
                    - categories in assay (if subcategories exist)
                    - is assay pinned to faviourites.
            - dictionaries referencing assay workflow's .py file.
        """
        # Initialise lists
        lst_AssayDirectories = []
        lst_Shorthand = []
        lst_FullName = []
        lst_Categories = []
        lst_Pinned = []
        # Initialise dictionary to hold assay modules
        dic_AssayModules = {}
        # Read all elements in assay path and check which ones are files
        for element in os.listdir(os.path.join(self.dir_Path,"assays")):
            if "as_" in element:
                str_Subdirectory = os.path.join(self.dir_Path,"assays",element)
                if os.path.isdir(str_Subdirectory) == True:
                    if os.path.exists(os.path.join(str_Subdirectory,"assay.csv")) == True:
                        csv_Assay = list(csv.reader(open(os.path.join(str_Subdirectory,
                                                                      "assay.csv"),"r")))
                        lst_AssayDirectories.append(str_Subdirectory)
                        str_Shorthand = csv_Assay[0][1]
                        lst_Shorthand.append(str_Shorthand) # Shorthand is in row 0
                        lst_FullName.append(csv_Assay[1][1]) # Full name is in row 1
                        lst_Categories.append(csv_Assay[2][1:]) # Categories are in row 2
                        lst_Pinned.append(False)
                        # Import assay module
                        dic_AssayModules[str_Shorthand] = importlib.import_module(
                                                                        u"assays.as_"
                                                                        + str_Shorthand
                                                                        + "."
                                                                        + str_Shorthand)
        
        dfr_Assays = pd.DataFrame(index=lst_Shorthand,
                                  data={"FullName":lst_FullName,
                                        "Subdirectory":lst_AssayDirectories,
                                        "Categories":lst_Categories,
                                        "Pinned":lst_Pinned})

        return dfr_Assays, dic_AssayModules

    # New Analyses
    def ActiveProject(self):
        """
        Performs check to see if there is an active project before
        starting a new one. Prompts user to confirm cancelling the
        project, if there is one,

        Returns True if there is a project.
        """
        if not self.ProjectTab == None:
            message = wx.MessageBox(
                    "You cannot start a new project before closing the current one. "
                    + "Do you want to close it?",
                    caption = "No can do!",
                    style = wx.YES_NO|wx.ICON_WARNING)
            # User clicked "Yes" -> message returns 2
            if message == 2:
                self.Freeze()
                # Double check by asking the user if they want to discard any changes
                if msg.QueryDiscardChanges() == True:
                    # Delete corresponding page in simplebook and re-set buttons
                    self.ProjectTab.ButtonBar.EnableButtons(False)
                    self.sbk_WorkArea.DeletePage(self.ProjectTab.Index)
                    self.ProjectTab = None
                    self.OnBtnNew(None)
                    self.sbk_WorkArea.SetSelection(self.dic_WorkAreaPageIndices["NewProject"])
                    bol_Cancelled = True
                else:
                    bol_Cancelled = False
            # User clicked "No" -> message returns 8
            elif message == 8:
                bol_Cancelled = False
            if bol_Cancelled == True:
                return False
            else:
                return True
        else:
            return False

    def StartNewProject(self, event, shorthand = None):
        """
        Starts a new Assay project.
        
        Arguments:
            event -> wx event. If called as an event handler,
                     button will have the assay type as shorthand
                     assigned to it's Type property.
            shorthand -> string. If not called as an event handler,
                         provide shorthand code for assay type here.
        """
        if shorthand == None:
            shorthand = event.GetEventObject().Type
        self.sbk_WorkArea.Update()
        if self.ActiveProject() == False:
            self.Freeze()
            self.sbk_WorkArea.ShowNewPage(self.dic_AssayModules[shorthand].pnl_Project(self))
            self.dic_WorkAreaPageIndices["Current"] = self.sbk_WorkArea.GetPageCount() - 1
            self.lbl_Banner.SetLabel(shorthand)
            self.ProjectTab = self.sbk_WorkArea.GetChildren()[self.dic_WorkAreaPageIndices["Current"]]
            self.ProjectTab.Index = self.dic_WorkAreaPageIndices["Current"]
            self.ProjectTab.ButtonBar.lbl_Filename.SetLabel(u"(No filename, yet)")
            self.ProjectTab.ButtonBar.EnableButtons(True)
            self.btn_Current.Enable()
            self.OnSidebarButton(None, Type = "Current")
            self.Thaw()

##################################################################
##                                                              ##
##    ##    ##   ####   ##  ##  ##     ####   #####   #####     ##
##    ###  ###  ##  ##  ##  ### ##    ##  ##  ##  ##  ##  ##    ##
##    ########  ######  ##  ######    ######  #####   #####     ##
##    ## ## ##  ##  ##  ##  ## ###    ##  ##  ##      ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ##  ##  ##      ##        ##
##                                                              ##
##################################################################

class BBQ(wx.App):
    """
    Main app
    """

    def OnInit(self):

        self.SetAppName("BBQ")
        self.frame = frm_Main(None)
        self.frame.Show(True)
        self.frame.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)
        self.frame.Maximize(True)
        self.frame.SetWindowStyle(wx.RESIZE_BORDER)

        return True

##########################################################################
##                                                                      ##
##    ##    ##   ####   ##  ##  ##    ##       ####    ####   #####     ##
##    ###  ###  ##  ##  ##  ### ##    ##      ##  ##  ##  ##  ##  ##    ##
##    ########  ######  ##  ######    ##      ##  ##  ##  ##  #####     ##
##    ## ## ##  ##  ##  ##  ## ###    ##      ##  ##  ##  ##  ##        ##
##    ##    ##  ##  ##  ##  ##  ##    ######   ####    ####   ##        ##
##                                                                      ##
##########################################################################

def main():
    app = BBQ(False)
    app.MainLoop()

if __name__ == "__main__":
    # Uncomment the following line to catch user warnings as errors
    # for debugging purposes
    #warnings.simplefilter('error', "SettingWithCopyWarning")
    multiprocessing.freeze_support() # this line is required to stop the issue
                                     # where the multiprocessing just opens several
                                     # instances of frozen executable without doing
                                     # anything with the processes.
    main()