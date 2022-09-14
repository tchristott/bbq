# Import my own libraries
from operator import truediv
from re import U
import lib_datafunctions as df
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_customplots as cp
import lib_platefunctions as pf
import lib_tabs as tab
import lib_platelayoutmenus as plm
import lib_tooltip as tt
from lib_progressdialog import GenericProgress
from lib_custombuttons import CustomBitmapButton, IconTabButton
from lib_fittingfunctions import draw_linear

# Import libraries for GUI
import wx
import wx.xrc
import wx.grid
import wx.adv
import wx.dataview

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import patches

# Import other libraries
import os
import pandas as pd
import numpy as np
import threading
from time import perf_counter
from datetime import datetime
from itertools import product


##########################################################################
##                                                                      ##
##    ##  ##  ##  ##  ##  ######    ##    ##  ######  ##  ##  ##  ##    ##
##    ##  ##  ### ##  ##    ##      ###  ###  ##      ### ##  ##  ##    ##
##    ##  ##  ######  ##    ##      ########  ####    ######  ##  ##    ##
##    ##  ##  ## ###  ##    ##      ## ## ##  ##      ## ###  ##  ##    ##
##     ####   ##  ##  ##    ##      ##    ##  ######  ##  ##   ####     ##
##                                                                      ##
##########################################################################

class UnitMenu(wx.Menu):
    def __init__(self, parent, row):
        super(UnitMenu, self).__init__()
        """
        Context menu to assign concentration unit
        """

        self.parent = parent
        
        self.mi_Molar = wx.MenuItem(self, wx.ID_ANY, u"M", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_Molar)
        self.Bind(wx.EVT_MENU, lambda event: self.Molarity(event, row, u"M"), self.mi_Molar)

        self.mi_Millimolar = wx.MenuItem(self, wx.ID_ANY, u"mM", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_Millimolar)
        self.Bind(wx.EVT_MENU, lambda event: self.Molarity(event, row, u"mM"), self.mi_Millimolar)

        self.mi_Micromolar = wx.MenuItem(self, wx.ID_ANY, u"uM", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_Micromolar)
        self.Bind(wx.EVT_MENU, lambda event: self.Molarity(event, row, u"uM"), self.mi_Micromolar)

        self.mi_Nanomolar = wx.MenuItem(self, wx.ID_ANY, u"nM", wx.EmptyString, wx.ITEM_NORMAL)
        self.Append(self.mi_Nanomolar)
        self.Bind(wx.EVT_MENU, lambda event: self.Molarity(event, row, u"nM"), self.mi_Nanomolar)
    
    def Molarity(self, event, row, unit):
        self.parent.grd_ConcentrationList.SetCellValue(row,1,unit)
        event.Skip()
        self.parent.UpdateDatastructure(None)


##############################################################################################
##                                                                                          ##
##     #####   ####   ##    ##  #####   ##      ######    #####   ##       ####   ######    ##
##    ##      ##  ##  ###  ###  ##  ##  ##      ##        ##  ##  ##      ##  ##    ##      ##
##     ####   ######  ########  #####   ##      ####      #####   ##      ##  ##    ##      ##
##        ##  ##  ##  ## ## ##  ##      ##      ##        ##      ##      ##  ##    ##      ##
##    #####   ##  ##  ##    ##  ##      ######  ######    ##      ######   ####     ##      ##
##                                                                                          ##
##############################################################################################

class SamplePlot(wx.Panel):
    def __init__(self, parent, PanelSize, str_YLabel, tabname):
        self.tabname = tabname
        wx.Panel.__init__(self, parent,size=PanelSize)#=wx.Size(550,325))
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(300/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.axes = self.figure.add_subplot()
        self.axes.set_title("Destination Plate [X]")
        self.figure.subplots_adjust(left=0.15, right=0.75, top=self.Top , bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = None
        self.YLabel = "Delta Z score"
        self.Input = None
        self.Concentrations = []
        self.Conditions = []
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Highlight = None

    def Draw(self):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        # If the canvas already exists, we are updating the plot. Therefore, the old needs deleting.
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.Title)
        self.Labels = self.Input.index.tolist()
        self.Concentrations = self.Input.columns.to_list()
        #self.XAxisValues = range(len(self.XAxisLabels))
        
        for i in range(len(self.Input.index)):
            alpha = 1
            if self.Highlight != None:
                if not self.Highlight == self.Input.index[i]:
                    alpha = 0.2
            self.axes.plot(self.Concentrations, self.Input.loc[self.Input.index[i]].to_list(), label=self.Labels[i][1:], color=self.Colours[i], marker="o", alpha=alpha)
        self.axes.set_xlabel("Compound concentration (log M)")
        self.axes.set_xscale("log")
        self.axes.set_ylabel(self.YLabel)
        self.Legend = self.axes.legend(bbox_to_anchor=(1.025, 1), loc='upper left', borderaxespad=0.)
        # Connect event handlers
        #self.canvas.mpl_connect("pick_event", self.OnClick)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("motion_notify_event", self.MouseOver)
        self.canvas.mpl_connect("axes_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("figure_leave_event", self.LeaveFigure)
        self.canvas.draw()
        if self.Highlight == None:
            self.Backup = self.canvas.copy_from_bbox(self.figure.bbox)

    def MouseOver(self, event):
        if self.Legend.get_window_extent().contains(event.x, event.y):
            for text in self.Legend.get_texts():
                if text.get_window_extent().contains(event.x, event.y):
                    self.Highlight = "_"+str(text.get_text())
                    self.Draw()
                    break
        else:
            self.Highlight = None
            self.canvas.blit()
            self.canvas.restore_region(self.Backup)
            self.Draw()

    def LeaveFigure(self, event):
        self.Highlight = None
        self.canvas.blit()
        self.canvas.restore_region(self.Backup)

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        self.Input.to_clipboard(header=True, index=True)

##############################################################################################
##                                                                                          ##
##    #####   ##  ##  ##               ####   ##  ##  ##      ##  ##   #####  ##   #####    ##
##    ##  ##  ### ##  ##              ##  ##  ### ##  ##      ##  ##  ##      ##  ##        ##
##    #####   ## ###  ##              ######  ## ###  ##       ####    ####   ##   ####     ##
##    ##      ##  ##  ##              ##  ##  ##  ##  ##        ##        ##  ##      ##    ##
##    ##      ##  ##  ######  ######  ##  ##  ##  ##  ######    ##    #####   ##  #####     ##
##                                                                                          ##
##############################################################################################

class pnl_Project (wx.Panel):

    def __init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size(1000,750), style = wx.TAB_TRAVERSAL, name = wx.EmptyString):
        wx.Panel.__init__ (self, parent.sbk_WorkArea, id = id, pos = pos, size = size, style = style, name = "pnl_Project")

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent

        # Initialise instance wide variables with default values
        self.Title = u"Cell based compound screen"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "cell_based"
        self.str_Shorthand = "CBCS"
        self.AssayPath = os.path.dirname(os.path.realpath(__file__))
        self.bol_AssayDetailsCompleted = False
        self.bol_AssayDetailsChanged = False
        self.bol_LayoutDefined = False
        self.bol_TransferLoaded = True # There are no transfer files used here!
        self.bol_DataFilesAssigned = False
        self.bol_DataFilesUpdated = False
        self.bol_DataAnalysed = False
        self.bol_ReviewsDrawn = False
        self.bol_ResultsDrawn = False
        self.bol_ELNPlotsDrawn = False
        self.bol_ExportPopulated = False
        self.bol_PreviouslySaved = False
        self.bol_GlobalLayout = True
        self.bol_PlateID = True
        self.bol_PlateMapPopulated = False
        self.lst_Details = []
        self.str_DatafileExtension = ".xlsx"
        self.str_SaveFilePath = ""
        self.str_DataPath = ""
        self.str_TransferPath = ""
        self.SampleSource = "echo"
        self.Device = "operetta"
        self.DataProcessor = "Columbus"
        self.int_PlateFormat = 384

        self.dfr_Layout = pd.DataFrame()

        self.lst_AllowedUnits = ["M", "mM", "uM", "nM"]
        self.lst_UnitConversion = {"M":1,"mM":1000,"uM":1000000,"nM":1000000000}

        self.szr_Main = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Tabs = wx.BoxSizer(wx.VERTICAL)
        # Button bar for saving, etc
        self.ButtonBar = tab.ButtonBar(self)
        self.szr_Tabs.Add(self.ButtonBar,0,wx.EXPAND,0)
        
        self.tabs_Analysis = tab.AssayStepsNotebook(self, size = wx.Size(1000,750))

         ##   ###  ###  ##  #   #    ###  #### #####  ##  # #     ###
        #  # #    #    #  # #   #    #  # #      #   #  # # #    #
        ####  ##   ##  ####  # #     #  # ###    #   #### # #     ##
        #  #    #    # #  #   #      #  # #      #   #  # # #       #
        #  # ###  ###  #  #   #      ###  ####   #   #  # # #### ###  #########################################################################################

        # Start Building
        self.tab_Details = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.tab_Details.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Assay = wx.BoxSizer(wx.VERTICAL)


        self.szr_Details = wx.BoxSizer(wx.HORIZONTAL)
        # Sizer One
        self.szr_One = wx.BoxSizer(wx.VERTICAL)
        # Concentration List
        self.pnl_ConcentrationList = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_ConcentrationList.SetBackgroundColour(cs.BgLight)
        self.szr_ConcentrationList = wx.BoxSizer(wx.VERTICAL)
        self.szr_TitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ConcentrationList = wx.StaticText(self.pnl_ConcentrationList, wx.ID_ANY,
            u"1. Concentrations:\nTo add a new concentration, press \"Add\" and enter value and unit.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_ConcentrationList.Wrap(180)
        self.szr_TitleAndList.Add(self.lbl_ConcentrationList, 0, wx.ALL, 5)
        self.grd_ConcentrationList = wx.grid.Grid(self.pnl_ConcentrationList, wx.ID_ANY, wx.DefaultPosition, wx.Size(175,130), 0)
        # Grid
        self.grd_ConcentrationList.CreateGrid(1, 2)
        self.grd_ConcentrationList.EnableEditing(True)
        self.grd_ConcentrationList.EnableGridLines(True)
        self.grd_ConcentrationList.EnableDragGridSize(False)
        self.grd_ConcentrationList.SetMargins(0, 0)
        # Columns
        self.grd_ConcentrationList.SetColSize(0, 95)
        self.grd_ConcentrationList.SetColLabelValue(0, "Concentration")
        self.grd_ConcentrationList.SetColSize(1, 35)
        self.grd_ConcentrationList.SetColLabelValue(1, "Unit")
        self.grd_ConcentrationList.EnableDragColMove(False)
        self.grd_ConcentrationList.EnableDragColSize(False)
        self.grd_ConcentrationList.SetColLabelSize(20)
        self.grd_ConcentrationList.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_ConcentrationList.EnableDragRowSize(False)
        self.grd_ConcentrationList.SetRowLabelSize(25)
        self.grd_ConcentrationList.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_ConcentrationList.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_ConcentrationList.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        self.szr_TitleAndList.Add(self.grd_ConcentrationList, 0, wx.ALL, 5)
        self.szr_ConcentrationList.Add(self.szr_TitleAndList, 0, wx.EXPAND, 5)
        self.szr_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Buttons.Add((0, 0), 1, wx.EXPAND, 5)
        self.btn_AddConcentration = CustomBitmapButton(self.pnl_ConcentrationList, u"Add", 0, (75,30))
        self.szr_Buttons.Add(self.btn_AddConcentration, 0, wx.ALL, 5)
        self.btn_RemoveConcentration = CustomBitmapButton(self.pnl_ConcentrationList, u"Remove", 0, (90,30))
        self.szr_Buttons.Add(self.btn_RemoveConcentration, 0, wx.ALL, 5)
        self.szr_ConcentrationList.Add(self.szr_Buttons, 0, wx.EXPAND, 5)
        self.pnl_ConcentrationList.SetSizer(self.szr_ConcentrationList)
        self.pnl_ConcentrationList.Layout()
        self.szr_ConcentrationList.Fit(self.pnl_ConcentrationList)
        self.szr_One.Add(self.pnl_ConcentrationList, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_One, 0, wx.EXPAND, 5)

        # TESTING DEFAULTS
        self.grd_ConcentrationList.InsertRows(0,3)
        self.grd_ConcentrationList.SetCellValue(0,0,"3")
        self.grd_ConcentrationList.SetCellValue(0,1,"uM")
        self.grd_ConcentrationList.SetCellValue(1,0,"0.3")
        self.grd_ConcentrationList.SetCellValue(1,1,"uM")
        self.grd_ConcentrationList.SetCellValue(2,0,"30")
        self.grd_ConcentrationList.SetCellValue(2,1,"nM")
        self.grd_ConcentrationList.SetCellValue(3,0,"3")
        self.grd_ConcentrationList.SetCellValue(3,1,"nM")

        # Sizer Two
        self.szr_Two = wx.BoxSizer(wx.VERTICAL)
        # Condition List
        self.pnl_ConditionList = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_ConditionList.SetBackgroundColour(cs.BgLight)
        self.szr_ConditionList = wx.BoxSizer(wx.VERTICAL)
        self.szr_TitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ConditionList = wx.StaticText(self.pnl_ConditionList, wx.ID_ANY,
            u"2. Conditions:\nTo add a new concentration, press \"Add\" and enter description and abbreviation.", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_ConditionList.Wrap(230)
        self.szr_TitleAndList.Add(self.lbl_ConditionList, 0, wx.ALL, 5)
        self.grd_ConditionList = wx.grid.Grid(self.pnl_ConditionList, wx.ID_ANY, wx.DefaultPosition, wx.Size(225,130), 0)
        # Grid
        self.grd_ConditionList.CreateGrid(1, 2)
        self.grd_ConditionList.EnableEditing(True)
        self.grd_ConditionList.EnableGridLines(True)
        self.grd_ConditionList.EnableDragGridSize(False)
        self.grd_ConditionList.SetMargins(0, 0)
        # Columns
        self.grd_ConditionList.SetColSize(0, 145)
        self.grd_ConditionList.SetColLabelValue(0, "Full description")
        self.grd_ConditionList.SetColSize(1, 35)
        self.grd_ConditionList.SetColLabelValue(1, "Abbr.")
        self.grd_ConditionList.EnableDragColMove(False)
        self.grd_ConditionList.EnableDragColSize(False)
        self.grd_ConditionList.SetColLabelSize(20)
        self.grd_ConditionList.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_ConditionList.EnableDragRowSize(False)
        self.grd_ConditionList.SetRowLabelSize(25)
        self.grd_ConditionList.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_ConditionList.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_ConditionList.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        self.szr_TitleAndList.Add(self.grd_ConditionList, 0, wx.ALL, 5)
        self.szr_ConditionList.Add(self.szr_TitleAndList, 0, wx.EXPAND, 5)
        self.szr_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Buttons.Add((0, 0), 1, wx.EXPAND, 5)
        self.btn_AddCondition = CustomBitmapButton(self.pnl_ConditionList, u"Add", 0, (75,30))
        self.szr_Buttons.Add(self.btn_AddCondition, 0, wx.ALL, 5)
        self.btn_RemoveCondition = CustomBitmapButton(self.pnl_ConditionList, u"Remove", 0, (90,30))
        self.szr_Buttons.Add(self.btn_RemoveCondition, 0, wx.ALL, 5)
        self.szr_ConditionList.Add(self.szr_Buttons, 0, wx.EXPAND, 5)
        self.pnl_ConditionList.SetSizer(self.szr_ConditionList)
        self.pnl_ConditionList.Layout()
        self.szr_ConditionList.Fit(self.pnl_ConditionList)
        self.szr_Two.Add(self.pnl_ConditionList, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_Two, 0, wx.EXPAND, 5)

        # TESTING DEFAULTS
        self.grd_ConditionList.InsertRows(0,2)
        self.grd_ConditionList.SetCellValue(0,0,"Compount treatment")
        self.grd_ConditionList.SetCellValue(0,1,"T")
        self.grd_ConditionList.SetCellValue(1,0,"Irradiation")
        self.grd_ConditionList.SetCellValue(1,1,"IR")
        self.grd_ConditionList.SetCellValue(2,0,"Hypoxia")
        self.grd_ConditionList.SetCellValue(2,1,"H")


        # Sizer Three
        self.szr_Three = wx.BoxSizer(wx.VERTICAL)
        # Replicates
        self.pnl_Replicates = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Replicates.SetBackgroundColour(cs.BgLight)
        self.szr_Replicates = wx.BoxSizer(wx.VERTICAL)
        self.szr_ReplicatesTitle = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Replicates = wx.StaticText(self.pnl_Replicates, wx.ID_ANY,
            u"3. Replicates:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Replicates.Wrap(230)
        self.szr_ReplicatesTitle.Add(self.lbl_Replicates, 0, wx.ALL, 5)
        self.txt_Replicates = wx.TextCtrl(self.pnl_Replicates, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(30,-1), wx.TE_PROCESS_ENTER)
        self.txt_Replicates.SetValue("2")
        self.szr_ReplicatesTitle.Add(self.txt_Replicates, 0, wx.ALL, 5)
        self.szr_Replicates.Add(self.szr_ReplicatesTitle, 0, wx.ALL, 5)
        self.pnl_Replicates.SetSizer(self.szr_Replicates)
        self.pnl_Replicates.Layout()
        self.szr_Replicates.Fit(self.pnl_Replicates)
        self.szr_Three.Add(self.pnl_Replicates, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_Three, 0, wx.EXPAND, 5)
        
        self.szr_PlateLayoutWrapper = wx.BoxSizer(wx.VERTICAL)
        # Plate Layouts
        self.pnl_PlateLayout = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_PlateLayout.SetBackgroundColour(cs.BgLight)
        self.szr_PlateLayout = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateLayoutTitle = wx.BoxSizer(wx.VERTICAL)
        self.lbl_PlateLayout = wx.StaticText(self.pnl_PlateLayout, wx.ID_ANY,
            u"4. Plate layout:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_PlateLayout.Wrap(230)
        self.szr_PlateLayoutTitle.Add(self.lbl_PlateLayout, 0, wx.ALL, 5)
        self.btn_EditPlateLayout = CustomBitmapButton(self.pnl_PlateLayout, u"EditPlateLayout", 0, (125,25))
        self.szr_PlateLayoutTitle.Add(self.btn_EditPlateLayout, 0, wx.ALL, 5)
        self.szr_PlateLayout.Add(self.szr_PlateLayoutTitle, 0, wx.ALL, 5)
        self.pnl_PlateLayout.SetSizer(self.szr_PlateLayout)
        self.pnl_PlateLayout.Layout()
        self.szr_PlateLayout.Fit(self.pnl_PlateLayout)
        self.szr_PlateLayoutWrapper.Add(self.pnl_PlateLayout, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_PlateLayoutWrapper, 0, wx.EXPAND, 5)

        self.szr_Right = wx.BoxSizer(wx.VERTICAL)
        # Date of experiment
        self.pnl_Date = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(210,-1), wx.TAB_TRAVERSAL)
        self.pnl_Date.SetBackgroundColour(clr_Panels)
        self.pnl_Date.SetMaxSize(wx.Size(210,-1))
        self.szr_Date = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Date = wx.StaticText(self.pnl_Date, wx.ID_ANY, u"Date of experiment", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Date.Wrap(-1)
        self.szr_Date.Add(self.lbl_Date, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.DatePicker = wx.adv.DatePickerCtrl(self.pnl_Date, wx.ID_ANY, wx.DefaultDateTime, wx.DefaultPosition, wx.DefaultSize, wx.adv.DP_DEFAULT|wx.adv.DP_DROPDOWN)
        self.DatePicker.SetNullText(u"N/A")
        self.DatePicker.SetBackgroundColour(clr_TextBoxes)
        self.szr_Date.Add(self.DatePicker, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pnl_Date.SetSizer(self.szr_Date)
        self.pnl_Date.Layout()
        self.szr_Date.Fit(self.pnl_Date)
        self.szr_Right.Add(self.pnl_Date, 0, wx.EXPAND|wx.ALL, 5)

        self.szr_Details.Add(self.szr_Right, 0, wx.EXPAND, 5)


        self.szr_Assay.Add(self.szr_Details, 0, wx.EXPAND, 5)

        # Finalise
        self.tab_Details.SetSizer(self.szr_Assay)
        self.tab_Details.Layout()
        self.szr_Assay.Fit(self.tab_Details)
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", True)

        #### # #    ####  ###
        #    # #    #    #
        ###  # #    ###   ##
        #    # #    #       #
        #    # #### #### ###  #################################################################################################################################

        # Start Building
        self.tab_Files = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.tab_Files.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Files = wx.BoxSizer(wx.HORIZONTAL)

        # Left Sizer
        self.szr_Left = wx.BoxSizer(wx.VERTICAL)
        # Columbus panel
        self.pnl_DataFiles = wx.Panel(self.tab_Files, wx.ID_ANY, wx.DefaultPosition, wx.Size(550,-1), wx.TAB_TRAVERSAL)
        self.pnl_DataFiles.SetBackgroundColour(clr_Panels)
        self.szr_DataFiles = wx.BoxSizer(wx.VERTICAL)
        self.lbl_DataFiles = wx.StaticText(self.pnl_DataFiles, wx.ID_ANY, u"Select the raw data directory:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DataFiles.Wrap(-1)
        self.szr_DataFiles.Add(self.lbl_DataFiles, 0, wx.ALL, 5)
        self.szr_FilePicker = wx.BoxSizer(wx.HORIZONTAL)
        self.dpk_Data = tab.CustomFilePicker(self.pnl_DataFiles, u"Select a directory", u"", (450,-1))
        self.dpk_Data.Type = "directory"
        self.szr_FilePicker.Add(self.dpk_Data, 0, wx.ALL, 5)
        self.cho_DataProcessor = wx.Choice(self.pnl_DataFiles, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, ["Columbus","Harmony"], 0)
        self.cho_DataProcessor.SetSelection(0)
        self.szr_FilePicker.Add(self.cho_DataProcessor, 0, wx.ALL, 5)
        self.szr_DataFiles.Add(self.szr_FilePicker, 0, wx.ALL, 0)
        self.pnl_DataFiles.SetSizer(self.szr_DataFiles)
        self.pnl_DataFiles.Layout()
        self.szr_DataFiles.Fit(self.pnl_DataFiles)
        self.szr_Left.Add(self.pnl_DataFiles, 0, wx.ALL, 5)
        # Data structure
        self.pnl_DataStructure = wx.Panel(self.tab_Files, wx.ID_ANY, wx.DefaultPosition, wx.Size(650,-1), wx.TAB_TRAVERSAL)
        self.pnl_DataStructure.SetBackgroundColour(cs.BgLight)
        self.szr_DataStructure = wx.BoxSizer(wx.VERTICAL)
        self.szr_DataStructureTitle = wx.BoxSizer(wx.VERTICAL)
        self.lbl_DataStructure = wx.StaticText(self.pnl_DataStructure, wx.ID_ANY,
            u"Structure preview:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DataStructure.Wrap(230)
        self.szr_DataStructureTitle.Add(self.lbl_DataStructure, 0, wx.ALL, 5)
        self.szr_DataStructure.Add(self.szr_DataStructureTitle, 0, wx.ALL, 5)
        #self.tree_DataStructure = wx.TreeCtrl(self.pnl_DataStructure, wx.ID_ANY, wx.DefaultPosition, wx.Size(650,400), wx.TR_DEFAULT_STYLE)
        self.tree_DataStructure = wx.dataview.TreeListCtrl(self.pnl_DataStructure, wx.ID_ANY, wx.DefaultPosition, wx.Size(650,-1), wx.dataview.TL_SINGLE , "Fnord")
        self.szr_DataStructure.Add(self.tree_DataStructure, 1, wx.ALL|wx.EXPAND, 5)
        self.pnl_DataStructure.SetSizer(self.szr_DataStructure)
        self.pnl_DataStructure.Layout()
        self.szr_DataStructure.Fit(self.pnl_DataStructure)
        self.szr_Left.Add(self.pnl_DataStructure, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_Files.Add(self.szr_Left, 0, wx.EXPAND, 5)

        # Finalise
        self.tab_Files.SetSizer(self.szr_Files)
        self.tab_Files.Layout()
        self.szr_Files.Fit(self.tab_Files)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Files", True)

        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  #######################################

        # Start Building
        self.pnl_Review = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Review.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Review = wx.BoxSizer(wx.VERTICAL)

        self.szr_ReviewPanel1 = wx.BoxSizer(wx.HORIZONTAL)

        # Condition List
        self.szr_ConditionList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectCondition = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Select a condition", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SelectCondition.Wrap(-1)
        self.szr_ConditionList.Add(self.lbl_SelectCondition, 0, wx.ALL, 5)
        self.lbc_Conditions = wx.ListCtrl(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.Size(200,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Conditions.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Conditions.InsertColumn(0,"Concentration")
        self.lbc_Conditions.SetColumnWidth(0,80)
        self.lbc_Conditions.InsertColumn(1,"Condition")
        self.lbc_Conditions.SetColumnWidth(1,80)

        self.szr_ConditionList.Add(self.lbc_Conditions, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_ReviewPanel1.Add(self.szr_ConditionList, 0, wx.EXPAND, 5)


        # Plot panel
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        # Tab buttons
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Heatmap = IconTabButton(self.pnl_Review, u"Heatmap", 0, self.AssayPath)
        self.btn_Heatmap.IsCurrent(True)
        self.szr_SimpleBookTabs.Add(self.btn_Heatmap, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_ReplicateCorrlation = IconTabButton(self.pnl_Review, u"Replicate Correlation", 1, self.AssayPath)
        self.btn_ReplicateCorrlation.IsEnabled(True)
        self.szr_SimpleBookTabs.Add(self.btn_ReplicateCorrlation, 0, wx.ALL,0)
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        self.dic_PlatePlotButtons = {0: self.btn_Heatmap, 1: self.btn_ReplicateCorrlation}
        self.btn_Heatmap.Group = self.dic_PlatePlotButtons
        self.btn_ReplicateCorrlation.Group = self.dic_PlatePlotButtons
        # Add simple book to hold the plots
        self.sbk_PlatePlots = wx.Simplebook(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.Size(800,600), 0)
        self.sbk_PlatePlots.SetBackgroundColour(cs.BgUltraLight)
        self.btn_Heatmap.Notebook = self.sbk_PlatePlots
        self.btn_ReplicateCorrlation.Notebook = self.sbk_PlatePlots

        # Add heatmap/grid to sbk_PlatePlots
        self.pnl_Heatmap = wx.Panel(self.sbk_PlatePlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.szr_Heatmap = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_HeatmapActual = wx.BoxSizer(wx.VERTICAL)
        self.plt_Heatmap = cp.HeatmapPanel(self.pnl_Heatmap, size = wx.Size(600,400),
                                           tabname = self, titlepos = 1.05) # True, "Normalised number of cells"
        self.szr_HeatmapActual.Add(self.plt_Heatmap, 0, wx.ALL, 0)
        self.szr_HeatmapReplicates = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_HeatmapRep1 = cp.HeatmapPanel(self.pnl_Heatmap, size = wx.Size(300,200),
                                               tabname = self, title = u"Replicate 1",
                                               titlefontsize = 10)
        self.szr_HeatmapReplicates.Add(self.plt_HeatmapRep1,0,wx.ALL,0)
        self.plt_HeatmapRep2 = cp.HeatmapPanel(self.pnl_Heatmap, size = wx.Size(300,200),
                                               tabname = self, title = u"Replicate 2",
                                               titlefontsize = 10)
        self.plt_HeatmapRep2.Title = "Replicate 2"
        self.szr_HeatmapReplicates.Add(self.plt_HeatmapRep2,0,wx.ALL,0)
        self.szr_HeatmapActual.Add(self.szr_HeatmapReplicates, 0, wx.ALL, 0)
        self.szr_Heatmap.Add(self.szr_HeatmapActual, 0, wx.ALL, 0)
        self.plt_Heatmap.PairedHeatmaps = [self.plt_HeatmapRep1,self.plt_HeatmapRep2]
        self.plt_HeatmapRep1.PairedHeatmaps = [self.plt_Heatmap,self.plt_HeatmapRep2]
        self.plt_HeatmapRep2.PairedHeatmaps = [self.plt_Heatmap,self.plt_HeatmapRep1]
        # Sizer for sidebar
        self.szr_Sidebar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Sidebar.Add((0, 35), 0, wx.EXPAND, 5)
        self.lbl_DisplayPlot = wx.StaticText(self.pnl_Heatmap, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DisplayPlot.Wrap(-1)
        self.szr_Sidebar.Add(self.lbl_DisplayPlot, 0, wx.ALL, 5)
        self.rad_ReviewRaw = wx.RadioButton(self.pnl_Heatmap, wx.ID_ANY, u"Raw readout", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.rad_ReviewRaw.SetValue(True)
        self.szr_Sidebar.Add(self.rad_ReviewRaw, 0, wx.ALL, 5)
        self.rad_ReviewNorm = wx.RadioButton(self.pnl_Heatmap, wx.ID_ANY, u"Normalised signal", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Sidebar.Add(self.rad_ReviewNorm, 0, wx.ALL, 5)
        self.rad_ReviewSolventNormalised = wx.RadioButton(self.pnl_Heatmap, wx.ID_ANY, u"Per-cent of solvent reference", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Sidebar.Add(self.rad_ReviewSolventNormalised, 0, wx.ALL, 5)
        self.szr_ZScore = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ReviewZScore = wx.RadioButton(self.pnl_Heatmap, wx.ID_ANY, u"Z score", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_ZScore.Add(self.rad_ReviewZScore, 0, wx.ALL, 0)
        self.btn_ZScoreToolTip = CustomBitmapButton(self.pnl_Heatmap, u"InfoUltraLight", 0, (15,15), tooltip=u"How is the Z score calculated?")
        self.btn_ZScoreToolTip.ImagePath = os.path.join(self.parent.str_OtherPath, "ZScoreToolTip.png")
        self.szr_ZScore.Add(self.btn_ZScoreToolTip, 0, wx.ALL, 0)
        self.szr_Sidebar.Add(self.szr_ZScore, 0, wx.ALL, 5)
        self.szr_DeltaZScore = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ReviewDeltaZScore = wx.RadioButton(self.pnl_Heatmap, wx.ID_ANY, u"Delta Z score", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_DeltaZScore.Add(self.rad_ReviewDeltaZScore, 0, wx.ALL, 0)
        self.dic_ReviewRadioButtons = {"Raw":self.rad_ReviewRaw,"Norm":self.rad_ReviewNorm,"PerCent":self.rad_ReviewSolventNormalised,
            "ZScore":self.rad_ReviewZScore,"DeltaZSore":self.rad_ReviewDeltaZScore}
        self.btn_DeltaZScoreToolTip = CustomBitmapButton(self.pnl_Heatmap, u"InfoUltraLight", 0, (15,15), tooltip=u"How is the Delta Z score calculated?")
        self.btn_DeltaZScoreToolTip.ImagePath = os.path.join(self.parent.str_OtherPath, "DeltaZScoreToolTip.png")
        self.szr_DeltaZScore.Add(self.btn_DeltaZScoreToolTip, 0, wx.ALL, 0)
        self.szr_Sidebar.Add(self.szr_DeltaZScore, 0, wx.ALL, 5)
        self.lbl_RSquare = wx.StaticText(self.pnl_Heatmap, wx.ID_ANY, u"R"+chr(178), wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_RSquare.Wrap(-1)
        self.szr_Sidebar.Add(self.lbl_RSquare, 0, wx.ALL, 5)
        self.lbl_Pearson = wx.StaticText(self.pnl_Heatmap, wx.ID_ANY, u"p", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Pearson.Wrap(-1)
        self.szr_Sidebar.Add(self.lbl_Pearson, 0, wx.ALL, 5)
        self.szr_Heatmap.Add(self.szr_Sidebar, 0, wx.ALL, 0)
        self.pnl_Heatmap.SetSizer(self.szr_Heatmap)
        self.pnl_Heatmap.Layout()
        self.szr_Heatmap.Fit(self.pnl_Heatmap)
        self.sbk_PlatePlots.AddPage(self.pnl_Heatmap, u"Heatmap", False)
        

        # Add scatter plot to sbk_PlatePlots
        self.pnl_ReplicateCorrelation = wx.Panel(self.sbk_PlatePlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.szr_ReplicateCorrelation = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_ReplicateCorrelation = cp.ReplicateCorrelation(parent = self.pnl_ReplicateCorrelation,
                                                       size = wx.Size(600,450),
                                                       tabname = self,
                                                       title = u"Replicate Correlation",
                                                       xlabel = u"Replicate 1 (% solvent reference)",
                                                       ylabel = u"Replicate 2 (% solvent reference)")
        self.szr_ReplicateCorrelation.Add(self.plt_ReplicateCorrelation, 0, wx.ALL, 0)
        self.pnl_ReplicateCorrelation.SetSizer(self.szr_ReplicateCorrelation)
        self.pnl_ReplicateCorrelation.Layout()
        self.szr_ReplicateCorrelation.Fit(self.pnl_ReplicateCorrelation)
        self.sbk_PlatePlots.AddPage(self.pnl_ReplicateCorrelation, u"ReplicateCorrelation", False)

        # Add notebook to sizer
        self.szr_SimpleBook.Add(self.sbk_PlatePlots, 0, 0, 5)
        
        self.szr_ReviewPanel1.Add(self.szr_SimpleBook, 1, wx.ALL, 5)
        
        self.szr_Review.Add(self.szr_ReviewPanel1, 1, wx.EXPAND, 5)
        
        # Finalise
        self.pnl_Review.SetSizer(self.szr_Review)
        self.pnl_Review.Layout()
        self.szr_Review.Fit(self.pnl_Review)
        self.tabs_Analysis.AddPage(self.pnl_Review, u"Review Plates", False)

        ###  ####  ### #  # #  #####  ###
        #  # #    #    #  # #    #   #
        ###  ###   ##  #  # #    #    ##
        #  # #       # #  # #    #      #
        #  # #### ###   ##  #### #   ###  #####################################################################################################################

        # Start Building
        self.pnl_Results = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Results.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Results = wx.BoxSizer(wx.HORIZONTAL)

        # Sample List
        self.szr_PlateMap = wx.BoxSizer(wx.VERTICAL)
        self.plt_PlateMap = cp.HeatmapPanel(self.pnl_Results,
                                            size = wx.Size(300,200),
                                            tabname = self, 
                                            title = u"Delta Z Score",
                                            titlefontsize=10,
                                            detailplot = True)
        self.plt_PlateMap.Title = "Max Delta Z Score of well across conditions"
        self.szr_PlateMap.Add(self.plt_PlateMap,0,wx.ALL,0)
        self.lbc_Samples = wx.ListCtrl(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(250,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Well")
        self.lbc_Samples.SetColumnWidth(0,50)
        self.lbc_Samples.InsertColumn(1,"SampleID")
        self.lbc_Samples.SetColumnWidth(1,100)
        self.lbc_Samples.InsertColumn(2,"max Delta Z")
        self.lbc_Samples.SetColumnWidth(2,90)

        self.szr_PlateMap.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)

        self.szr_Results.Add(self.szr_PlateMap, 0, wx.EXPAND, 5)

        self.szr_SamplePlot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_SamplePlot = SamplePlot(self.pnl_Results, wx.Size(650,400), "Sample", self)
        self.szr_SamplePlot.Add(self.plt_SamplePlot, 0, wx.ALL, 5)
        self.szr_SamplePlotOptions = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SamplePlotOptions = wx.StaticText(self.pnl_Results, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SamplePlotOptions.Wrap(-1)
        self.szr_SamplePlotOptions.Add(self.lbl_SamplePlotOptions, 0, wx.ALL, 5)
        self.rad_ResultsRaw = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Raw readout", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.rad_ResultsRaw.SetValue(True)
        self.szr_SamplePlotOptions.Add(self.rad_ResultsRaw, 0, wx.ALL, 5)
        self.rad_ResultsNorm = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Normalised signal", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_SamplePlotOptions.Add(self.rad_ResultsNorm, 0, wx.ALL, 5)
        self.rad_ResultsSolventNormalised = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Per-cent of solvent reference", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_SamplePlotOptions.Add(self.rad_ResultsSolventNormalised, 0, wx.ALL, 5)
        self.szr_ResultsZScore = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ResultsZScore = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Z score", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_ResultsZScore.Add(self.rad_ResultsZScore, 0, wx.ALL, 0)
        self.btn_ResultsZScoreToolTip = CustomBitmapButton(self.pnl_Results, u"InfoUltraLight", 0, (15,15), tooltip=u"How is the Z score calculated?")
        self.btn_ResultsZScoreToolTip.ImagePath = os.path.join(self.parent.str_OtherPath, "ZScoreToolTip.png")
        self.szr_ResultsZScore.Add(self.btn_ResultsZScoreToolTip, 0, wx.ALL, 0)
        self.szr_SamplePlotOptions.Add(self.szr_ResultsZScore, 0, wx.ALL, 5)
        self.szr_ResultsDeltaZScore = wx.BoxSizer(wx.HORIZONTAL)
        self.rad_ResultsDeltaZScore = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Delta Z score", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_ResultsDeltaZScore.Add(self.rad_ResultsDeltaZScore, 0, wx.ALL, 0)
        self.btn_ResultsDeltaZScoreToolTip = CustomBitmapButton(self.pnl_Results, u"InfoUltraLight", 0, (15,15), tooltip=u"How is the Delta Z score calculated?")
        self.btn_ResultsDeltaZScoreToolTip.ImagePath = os.path.join(self.parent.str_OtherPath, "DeltaZScoreToolTip.png")
        self.szr_ResultsDeltaZScore.Add(self.btn_ResultsDeltaZScoreToolTip, 0, wx.ALL, 0)
        self.szr_SamplePlotOptions.Add(self.szr_ResultsDeltaZScore, 0, wx.ALL, 5)
        self.dic_ResultsRadioButtons = {"Raw":self.rad_ResultsRaw,"Norm":self.rad_ResultsNorm,"PerCent":self.rad_ResultsSolventNormalised,
            "ZScore":self.rad_ResultsZScore,"DeltaZSore":self.rad_ResultsDeltaZScore}
        self.szr_SamplePlot.Add(self.szr_SamplePlotOptions, 0, wx.ALL, 5)

        self.szr_Results.Add(self.szr_SamplePlot, 0, wx.EXPAND, 5)
        
        # Finalise
        self.pnl_Results.SetSizer(self.szr_Results)
        self.pnl_Results.Layout()
        self.szr_Results.Fit(self.pnl_Results)
        self.tabs_Analysis.AddPage(self.pnl_Results, u"Results", False)

        #### #    #  #   ###  #     ##  #####  ###
        #    #    ## #   #  # #    #  #   #   #
        ###  #    # ##   ###  #    #  #   #    ##
        #    #    #  #   #    #    #  #   #      #
        #### #### #  #   #    ####  ##    #   ###  ############################################################################################################
        
        #self.tab_ELNPlots = tab.ELNPlots(self.tabs_Analysis.sbk_Notebook, tabname=self, assaycategory=self.str_AssayCategory)
        #self.tabs_Analysis.AddPage(self.tab_ELNPlots, u"Plots for ELN", False)

        #### #  # ###   ##  ###  #####
        #    #  # #  # #  # #  #   #
        ##    ##  ###  #  # ###    #
        #    #  # #    #  # #  #   #
        #### #  # #     ##  #  #   # ##########################################################################################################################

        self.lst_Headers = ["Protein  Concentration [" + chr(181) + "M]", "Purification ID", "Plate Well ID", "1st compound concentration [" + chr(181) + "M]",
                        "Buffer ID", "2nd compound ID", "2nd compound concentration [" + chr(181) + "M]", "Tm value [" + chr(176) + "C]",
                        "Tm Shift [" + chr(176) + "C]", "Slope at Tm [DI/" + chr(176) + "C]", "ELN ID", "Comments"]
        self.tab_Export = tab.ExportToDatabase(self.tabs_Analysis.sbk_Notebook, self)
        self.tabs_Analysis.AddPage(self.tab_Export, u"Export Results to Database", False)

        #######################################################################################################################################################

        self.szr_Tabs.Add(self.tabs_Analysis, 1, wx.EXPAND |wx.ALL, 0)
        self.szr_Main.Add(self.szr_Tabs, 1, wx.EXPAND, 5)
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.Centre(wx.BOTH)

        # Select first tab/index 0
        self.tabs_Analysis.SetSelection(0)

        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #  
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ##########################################################################################################################

        # Highest level events:
        self.tabs_Analysis.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        # Tab 1: Assay Details
        self.btn_AddConcentration.Bind(wx.EVT_BUTTON, self.AddConcentration)
        self.btn_RemoveConcentration.Bind(wx.EVT_BUTTON, self.RemoveConcentration)
        self.grd_ConcentrationList.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.ShowUnitMenu)
        self.grd_ConcentrationList.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.TestConcentration)
        self.btn_AddCondition.Bind(wx.EVT_BUTTON, self.AddCondition)
        self.btn_RemoveCondition.Bind(wx.EVT_BUTTON, self.RemoveCondition)
        self.grd_ConditionList.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.UpdateDatastructure)
        self.txt_Replicates.Bind(wx.EVT_TEXT, self.TestReplicates)
        self.txt_Replicates.Bind(wx.EVT_TEXT_ENTER, self.TestReplicates)
        self.btn_EditPlateLayout.Bind(wx.EVT_BUTTON, self.EditLayouts)
        
        # Tab 2: Transfer and Data Files
        self.dpk_Data.Bind(self.ReadDirectoryStructure)

        # Tab 3: Review
        self.lbc_Conditions.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowPlate)
        for radbtn in self.dic_ReviewRadioButtons.keys():
            self.dic_ReviewRadioButtons[radbtn].Bind(wx.EVT_RADIOBUTTON, self.UpdateReviewRadioButtons)
        self.btn_ZScoreToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.btn_DeltaZScoreToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)

        # Tab 4: Results
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowCurveList)
        #self.grd_Plate.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.ShowCurveGrid)
        for radbtn in self.dic_ResultsRadioButtons.keys():
            self.dic_ResultsRadioButtons[radbtn].Bind(wx.EVT_RADIOBUTTON, self.UpdateResultsRadioButtons)
        self.btn_ResultsZScoreToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.btn_ResultsDeltaZScoreToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)

        # Tab 5: ELN Plots

        # Tab 6: Export to Database

    def __del__(self):
        pass

    ############################################################################################################

     ######  ##         ##     #####   #####  ######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####
    ##       ##       ##  ##  ##      ##      ##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##
    ##       ##       ######   ####    ####   ######  ##  ##  ######  ##        ##    ##  ##  ##  ######   ####
    ##       ##       ##  ##      ##      ##  ##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##
     ######  #######  ##  ##  #####   #####   ##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####
    
    ############################################################################################################

    def ChangeTab(self, btn_Caller):
        int_OldTab = self.tabs_Analysis.GetSelection()
        int_NewTab = btn_Caller.Index
        if int_NewTab <= self.tabs_Analysis.GetPageCount(): 
            if int_OldTab == 0:
                self.SaveAssayDetails(bol_FromTabChange = True)
            # Assay details and files tabs are 0 and 1
            if int_NewTab > int_OldTab and int_NewTab > 1 and self.bol_DataAnalysed == False:
                msg.NoAnalysisPerformed()
                return False
            else:
                return True

    def OnTabChanged(self, event):
        """
        Gets called when tabs in the SimpleBook change.
        Performs checks (e.g. has an analysis been performed) before it lets the user see the page.
        """
        int_NewTab = self.tabs_Analysis.GetSelection()
        if int_NewTab == 2:
            # going to review tab
            if self.bol_ReviewsDrawn == False:
                self.PopulateReviewTab()
        elif int_NewTab == 3:
            # going to results tab    
            if self.bol_ResultsDrawn == False:
                self.PopulateResultsTab()
        elif int_NewTab == 4:
            # going to plots for ELN page tab
            if self.bol_ELNPlotsDrawn == False:
                self.tab_ELNPlots.PopulatePlotsTab()
        elif int_NewTab == 5:
            # going to results table for export tab
            if self.bol_ExportPopulated == False:
                self.bol_ExportPopulated = self.tab_Export.Populate()
        elif int_NewTab == 6:
            if self.bol_PlateMapPopulated == False:
                self.tab_PlateMap.PopulatePlateMapTab()

    def PopulateFromFile(self, lst_LoadedDetails, lst_LoadedBoolean, dfr_Loaded, lst_Paths):

        self.dfr_AssayData = dfr_Loaded

        self.str_DataPath = lst_Paths[1]
        self.str_TransferPath = lst_Paths[0]

        # Assay Details
        self.lst_Details = lst_LoadedDetails
        
        # No field for purification ID
        # No field for protein concentration
        self.txt_Solvent.SetValue(self.lst_Details[6])
        self.txt_Percent.SetValue(self.lst_Details[7])
        #self.txt_Buffer.SetValue(self.lst_Details[8]) # N/A for nanoDSF
        self.txt_ELN.SetValue(self.lst_Details[9])
        # str_AssayVolume = self.lst_Details[10] # in nL
        self.str_DatafileExtension = self.lst_Details[11]
        self.SampleSource = self.lst_Details[12]
        # Backwards compatibility wild older save files that do not have newer additions in the assay details:
        try:
            self.Device = self.lst_Details[13]
        except:
            self.Device = "operetta"
            self.lst_Details.append(self.Device)
        try:
            Date = self.lst_Details[14]
            Date = wx.DateTime.FromDMY(int(Date[8:10]), int(Date[5:7]), int(Date[:4]))
            self.tab_Details.DatePicker.SetValue(Date)
        except:
            self.lst_Details.append(None)
            
        self.dpk_Data.SetPath(self.str_DataPath)
        self.grd_Capillaries.AppendRows(len(dfr_Loaded.loc[0,"ProcessedDataFrame"]))
        for idx_Capillary in range(len(dfr_Loaded.loc[0,"ProcessedDataFrame"])):
            self.grd_Capillaries.SetCellValue(idx_Capillary,0,
                dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"CapillaryName"])
            self.grd_Capillaries.SetCellValue(idx_Capillary,1,
                dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"PurificationID"])
            self.grd_Capillaries.SetCellValue(idx_Capillary,2,
                str(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"ProteinConc"]))
            self.grd_Capillaries.SetCellValue(idx_Capillary,3,
                dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"SampleID"])
            self.grd_Capillaries.SetCellValue(idx_Capillary,4,
                str(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"SampleConc"]))
            self.grd_Capillaries.SetCellValue(idx_Capillary,5,
                dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"Buffer"])
            if dfr_Loaded.loc[0,"Layout"].loc[0,"WellType"][idx_Capillary] == "r":
                self.grd_Capillaries.SetCellValue(idx_Capillary,6,"Reference")
            elif dfr_Loaded.loc[0,"Layout"].loc[0,"WellType"][idx_Capillary] == "s":
                self.grd_Capillaries.SetCellValue(idx_Capillary,6,"Sample")
            if idx_Capillary % 2 == 0:
                for col in range(self.grd_Capillaries.GetNumberCols()):
                    self.grd_Capillaries.SetCellBackgroundColour(idx_Capillary,col,cs.BgUltraLight)
        self.szr_Capillaries.Layout()
        self.szr_Capillaries.Fit(self.grd_Capillaries)
        self.szr_Assay.Layout()

        # Update boolean variables
        self.bol_AssayDetailsChanged = False # lst_LoadedBoolean[0]
        self.bol_AssayDetailsCompleted = lst_LoadedBoolean[1]
        self.bol_DataFilesAssigned = lst_LoadedBoolean[2]
        self.bol_DataFilesUpdated = False # lst_LoadedBoolean[3]
        self.bol_DataAnalysed = lst_LoadedBoolean[4]
        self.bol_ELNPlotsDrawn = lst_LoadedBoolean[5]
        if self.bol_ELNPlotsDrawn == True:
            self.tab_ELNPlots.PopulatePlotsTab()
        self.bol_ExportPopulated = lst_LoadedBoolean[6]
        if self.bol_ExportPopulated == True:
            self.tab_Export.Populate(noreturn = True)
        self.bol_ResultsDrawn = lst_LoadedBoolean[7]
        if self.bol_ResultsDrawn == True:
            self.PopulateResultsTab()
        self.bol_ReviewsDrawn = lst_LoadedBoolean[8]
        self.bol_LayoutDefined = lst_LoadedBoolean[9]
        self.bol_GlobalLayout = lst_LoadedBoolean[10]
        self.bol_PlateID = lst_LoadedBoolean[11]
        self.bol_PlateMapPopulated = lst_LoadedBoolean[12]
        # And of course this has been previously saved since we are loading it from a file
        self.bol_PreviouslySaved = True

        # Populate transfer/data file tab

        # recreate single dfr_Layout
        self.dfr_Layout = pd.DataFrame(index=range(len(dfr_Loaded)), columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
        for idx_Plate in range(len(self.dfr_Layout)):
            self.dfr_Layout.at[idx_Plate,"PlateID"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"PlateID"]
            self.dfr_Layout.at[idx_Plate,"ProteinNumerical"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"ProteinNumerical"]
            self.dfr_Layout.at[idx_Plate,"PurificationID"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"PurificationID"]
            self.dfr_Layout.at[idx_Plate,"Concentration"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"Concentration"]
            self.dfr_Layout.at[idx_Plate,"WellType"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"WellType"]
        self.txt_PlateID = self.dfr_Layout.at[0,"PlateID"]
        self.txt_PlateID.Enable(lst_LoadedBoolean[11])
        self.tabs_Analysis.EnablePlateMap(lst_LoadedBoolean[11])
        self.bol_LayoutDefined = True
        
        self.tabs_Analysis.EnableAll(True)

    def ProcessData(self, dlg_Progress):
        """
        This function processes the data.
        First, assay details are saved to variables again (in case of updates).
        If the transfer file has been loaded, plates will be assigned (i.e. raw data files/entries matched with transfer file entries)
        Any previously displayed data will then be erased.
        Function get_CompleteContainer in the lib_datafiles(df) module then takes all the data and information to normalise data and
        perform the curve fitting. The returned dataframe (dfr_AssayData) contains all the data (raw data, analysed data,
        experimental meta data) and can be saved to file.
        """
        time_start = perf_counter()
        self.int_Samples = 0
        self.SaveAssayDetails(bol_FromTabChange = False)
        dlg_Progress.lbx_Log.InsertItems(["Assay details saved"], dlg_Progress.lbx_Log.Count)
        
        # Perform sequence of checks before beginning processing
        if self.bol_LayoutDefined == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoLayoutDefined()
            return None
        if self.bol_TransferLoaded == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoTransferLoaded()
            return None
        if self.bol_DataFilesAssigned == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoDataFileAssigned()
            return None

        # Build dataframe that holds everything
        dlg_Progress.lbx_Log.InsertItems(["Start creating complete container dataframe"], dlg_Progress.lbx_Log.Count)
        self.dfr_DataStructure, self.dfr_Processed, self.dfr_SampleInfo = df.get_CompleteContainer_CBCS(self.dfr_DataStructure, self.dfr_Layout, dlg_Progress,
            self.lst_Concentrations, self.lst_Conditions, self.str_ReferenceCondition, self.lst_Replicates, self.DataProcessor)

        # Catch any errors in processing -> df.get_CompleteContainer() returns None on any errors:
        if self.dfr_DataStructure is None:
            dlg_Progress.lbx_Log.InsertItems(["==============================================================="], dlg_Progress.lbx_Log.Count)
            dlg_Progress.lbx_Log.InsertItems(["DATA PROCESSING CANCELLED"], dlg_Progress.lbx_Log.Count)
            dlg_Progress.btn_X.Enable(True)
            dlg_Progress.btn_Close.Enable(True)
            return None

        # Re-set bool variables in case an analysis has been performed previously
        self.bol_DataAnalysed = False
        self.bol_ReviewsDrawn = False
        self.bol_ResultsDrawn = False
        self.bol_ELNPlotsDrawn = False
        self.bol_ExportPopulated = False

        # Clear all lists, fields, grids, plots to populate with (new) results
        if hasattr(self, "lbc_Plates"):
            self.lbc_Plates.DeleteAllItems()
        if hasattr(self, "lbc_Samples"):
            self.lbc_Samples.DeleteAllItems()
        if hasattr(self, "tab_Export"):
            self.tab_Export.Clear()

        # Populate tabs if existing and enable buttons:
        if hasattr(self, "tab_Review") == True:
            dlg_Progress.lbx_Log.InsertItems(["Populating 'Review Plates' tab"], dlg_Progress.lbx_Log.Count)
            self.PopulateReviewTab()
            if hasattr(self, "lbc_Plates") == True:
                self.lbc_Plates.Select(0)
            self.bol_ReviewsDrawn = True
        if hasattr(self, "tab_Results") == True:
            dlg_Progress.lbx_Log.InsertItems(["Populating 'Results' tab"], dlg_Progress.lbx_Log.Count)
            self.PopulateResultsTab()
            self.bol_ResultsDrawn = True
        self.tabs_Analysis.EnableAll(True)
        self.tabs_Analysis.EnablePlateMap(self.bol_PlateID)

        # Final entries in progress dialog:
        dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems(["==============================================================="], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems(["Data processing completed"], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
        str_Duration = str(round(perf_counter()-time_start,0))
        dlg_Progress.lbx_Log.InsertItems(["Time elapsed: " + str_Duration + "s"], dlg_Progress.lbx_Log.Count)

        # Pop up notification if neither main window nor progress dialog are active window:
        if self.parent.IsActive() == False and dlg_Progress.IsActive() == False:
            try:
                # This should only work on Windows
                self.parent.icn_Taskbar.ShowBalloon(title="BBQ",text="Analysis completed!",msec=1000)
            except:
                msg_Popup = wx.adv.NotificationMessage(title="BBQ", message="Analysis completed!")
                try: msg_Popup.SetIcon(self.parent.BBQIcon)
                except: None
                msg_Popup.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
        
        # Finish up
        self.bol_DataAnalysed = True
        dlg_Progress.btn_X.Enable(True)
        dlg_Progress.btn_Close.Enable(True)


    # 1. Functions for AssayDetails
    # ======================================================================================================
    #
    #  ######   ####   #####    ###      #####   ######  ######   ####   ##  ##       #####
    #    ##    ##  ##  ##  ##  ####      ##  ##  ##        ##    ##  ##  ##  ##      ##
    #    ##    ######  #####     ##  ##  ##  ##  ####      ##    ######  ##  ##       ####
    #    ##    ##  ##  ##  ##    ##      ##  ##  ##        ##    ##  ##  ##  ##          ##
    #    ##    ##  ##  #####     ##  ##  #####   ######    ##    ##  ##  ##  ######  #####
    #
    # ======================================================================================================
    
    # 1.2 Save the data from the form and save it into global list
    def SaveAssayDetails(self, bol_FromTabChange = False):
        # Write values of fields into variables for later use
        self.str_AssayType = "CBCS"
        self.str_AssayCategory = "cellular"
        self.str_Shirthand = "CBCS"
        self.str_DatafileExtension = ".txt"
        self.str_Purification = "DSF"
        self.int_ProteinConc = 0
        #str_Solvent = self.txt_Solvent.GetLineText(0)
        #int_SolventPercent = self.txt_Percent.GetLineText(0)
        #str_Buffer = ""
        #str_ELN = self.txt_ELN.GetLineText(0)
        #str_AssayVolume= str(20 * 1000) # convert to nL
        self.SampleSource = "NA"
        Date = self.DatePicker.GetValue()
        Date = str(Date.GetYear()) + "-" + str(Date.GetMonth()+1) + "-" + str(Date.GetDay()) # GetMonth is indexed from zero!!!!!
        Date = datetime.strptime(Date,"%Y-%m-%d").strftime("%Y-%m-%d")
        # Include checks so that user does not leave things empty
        #lst_Details_New = [self.str_AssayType, self.str_AssayCategory, str_Purification, "NA", "NA", "NA", 
        #    str_Solvent, int_SolventPercent, "NA", str_ELN, str_AssayVolume, self.str_DatafileExtension, "NA", self.Device, Date]
        #if self.bol_AssayDetailsCompleted == False:
        #    int_CheckSum = 0
        #    for i in range(len(lst_Details_New)):
        #        if lst_Details_New[i] == "":
        #            int_CheckSum += 1
        #    if int_CheckSum == 0:
        #        self.lst_Details = lst_Details_New
        #        bol_Details = True
        #    else:
        #        bol_Details = False
        #else:
        #    int_CheckSum = 0
        #    for i in range(len(lst_Details_New)):
        #        if lst_Details_New[i] != self.lst_Details[i]:
        #            int_CheckSum += 1
        #    if int_CheckSum != 0:
        #        self.lst_Details = lst_Details_New
        #        self.bol_AssayDetailsChanged = True
        #    bol_Details = True # needs to stay true for later check -> if new details assigned it will be true, if no new details assigned it will be true

        if not hasattr(self, "dfr_DataStructure") == True:
            self.UpdateDatastructure(None)
        
        # Data already analysed but assay details changed? Offer user chance to re-analyse
        if bol_FromTabChange == True:
            if self.bol_DataAnalysed == True and self.bol_AssayDetailsChanged == True:
                if msg.QueryReanalysis() == True:
                    self.parent.AnalyseData()



    def TestConcentration(self, event):
        row = event.GetRow()
        col = event.GetCol()
        if self.grd_ConcentrationList.GetCellValue(row, 1) in self.lst_AllowedUnits:
            self.UpdateDatastructure(None)
        else:
            print("Unit not allowed")

    def AddConcentration(self, event):
        int_Rows = self.grd_ConcentrationList.GetNumberRows()
        self.grd_ConcentrationList.InsertRows(int_Rows,1)
        self.grd_ConcentrationList.SetCellValue(int_Rows,0,"3")
        self.grd_ConcentrationList.SetCellValue(int_Rows,1,u"uM")
        self.UpdateDatastructure(None)

    def RemoveConcentration(self, event):
        lst_Selection = self.grd_ConcentrationList.GetSelectedRows()
        if len(lst_Selection) > 0:
            for i in reversed(range(len(lst_Selection))):
                if self.grd_ConcentrationList.GetNumberRows() > 1:
                    self.grd_ConcentrationList.DeleteRows(lst_Selection[i])
                else:
                    self.grd_ConcentrationList.SetCellValue(0,0,"")
                    self.grd_ConcentrationList.SetCellValue(0,1,"")
        self.UpdateDatastructure(None)
    
    def ShowUnitMenu(self, event):
        event.Skip()
        if event.GetCol() == 1:
            self.PopupMenu(UnitMenu(self, event.GetRow()))

    def AddCondition(self, event):
        int_Rows = self.grd_ConditionList.GetNumberRows()
        self.grd_ConditionList.InsertRows(int_Rows,1)
        self.grd_ConditionList.SetCellValue(int_Rows,0,u"Annoyed cells")
        self.grd_ConditionList.SetCellValue(int_Rows,1,u"AN")
        self.UpdateDatastructure(None)

    def RemoveCondition(self, event):
        lst_Selection = self.grd_ConditionList.GetSelectedRows()
        if len(lst_Selection) > 0:
            for i in reversed(range(len(lst_Selection))):
                if self.grd_ConditionList.GetNumberRows() > 1:
                    self.grd_ConditionList.DeleteRows(lst_Selection[i])
                else:
                    self.grd_ConditionList.SetCellValue(0,0,"")
                    self.grd_ConditionList.SetCellValue(0,1,"")
        self.UpdateDatastructure(None)

    def TestReplicates(self, event):
        try:
            replicates = int(self.txt_Replicates.GetLineText(0))
            self.UpdateDatastructure(None)
        except:
            print("that didn't work!")
    
    def UpdateDatastructure(self, event):

        self.tree_DataStructure.Concentrations = {}
        int_Concentrations = 0
        self.tree_DataStructure.Conditions = {}
        int_Conditions = 0
        self.tree_DataStructure.Replicates = {}
        int_Replicates = 0
        self.tree_DataStructure.DeleteAllItems()
        self.tree_DataStructure.AppendColumn("Condition")
        self.tree_DataStructure.AppendColumn("File")

        # Concentrations
        self.lst_Concentrations = []
        self.lst_ConcentrationsMolar = []
        for conc in range(self.grd_ConcentrationList.GetNumberRows()):
            if self.grd_ConcentrationList.GetCellValue(conc,0) != "" and self.grd_ConcentrationList.GetCellValue(conc,1) != "":
                self.lst_Concentrations.append(self.grd_ConcentrationList.GetCellValue(conc,0) + self.grd_ConcentrationList.GetCellValue(conc,1))
                self.lst_ConcentrationsMolar.append(float(self.grd_ConcentrationList.GetCellValue(conc,0))/self.lst_UnitConversion[self.grd_ConcentrationList.GetCellValue(conc,1)])
        if len(self.lst_Concentrations) == 0:
            return None

        # Conditions
        lst_Parameters = []
        for cond in range(self.grd_ConditionList.GetNumberRows()):
            if self.grd_ConditionList.GetCellValue(cond,0) != "" and self.grd_ConditionList.GetCellValue(cond,1) != "":
                lst_Parameters.append(self.grd_ConditionList.GetCellValue(cond,1))
        # Check there are any conditions:
        if len(lst_Parameters) == 0:
            return None
        # make list of all conditions
        lst_Prefixes = ["+", "-"]
        lst_Prefixcombinations = list(product(lst_Prefixes,repeat=len(lst_Parameters)))
        self.lst_Conditions = []
        self.str_ReferenceCondition = None
        for prefix in lst_Prefixcombinations:
            state = ""
            for par in range(len(lst_Parameters)):
                state += "_" + prefix[par] + lst_Parameters[par]
            # Set reference condition: check whether all are the same AND negative
            if prefix[0] == "-":
                result = all(element == prefix[0] for element in prefix)
                if result == True:
                    self.str_ReferenceCondition = state
            self.lst_Conditions.append(state)
        
        # Replicates:
        self.lst_Replicates = []
        for rep in range(int(self.txt_Replicates.GetLineText(0))):
            self.lst_Replicates.append("R"+str(rep+1))

        # Populate tree
        LevelConcentrations = []
        LevelConditions = []
        LevelReplicates = []

        for conc in range(len(self.lst_Concentrations)):
            self.tree_DataStructure.Concentrations[int_Concentrations] = self.tree_DataStructure.AppendItem(self.tree_DataStructure.GetRootItem(),self.lst_Concentrations[conc])
            for cond in range(len(self.lst_Conditions)):
                self.tree_DataStructure.Conditions[int_Conditions] = self.tree_DataStructure.AppendItem(self.tree_DataStructure.Concentrations[conc],self.lst_Conditions[cond])
                self.tree_DataStructure.Expand(self.tree_DataStructure.Conditions[int_Conditions])
                for rep in range(int(self.txt_Replicates.GetLineText(0))):
                    self.tree_DataStructure.Replicates[int_Replicates] = self.tree_DataStructure.AppendItem(self.tree_DataStructure.Conditions[int_Conditions],self.lst_Replicates[rep])
                    self.tree_DataStructure.Expand(self.tree_DataStructure.Replicates[int_Replicates])
                    LevelConcentrations.append(self.lst_Concentrations[conc])
                    LevelConditions.append(self.lst_Conditions[cond])
                    LevelReplicates.append(self.lst_Replicates[rep])
                    int_Replicates += 1
                int_Conditions += 1
            int_Concentrations += 1
        # add code to expand all here.

        # Create dataframe
        Indexing = [LevelConcentrations, LevelConditions, LevelReplicates]
        Columns = ["FilePath","RawData","Mean","Normalised","Controls","ReferenceCondition"]
        self.dfr_DataStructure = pd.DataFrame(index=Indexing,columns=Columns).sort_index()
        
    def ReadDirectoryStructure(self, str_DataPath):

        if not hasattr(self, "dfr_DataStructure") == True:
            return None

        self.str_DataPath = str_DataPath
        lst_AllTopLevel = os.listdir(self.str_DataPath)
        for i in range(len(lst_AllTopLevel)):
            lst_AllTopLevel[i] = os.path.join(self.str_DataPath, lst_AllTopLevel[i])

        self.DataProcessor = self.cho_DataProcessor.GetString(self.cho_DataProcessor.GetSelection())
        if self.DataProcessor == "Columbus":
            for toplvl in lst_AllTopLevel:
                for conc in self.lst_Concentrations:
                    # concentration needs _ in front, otherwise "0.3uM" and "3uM" will be recongised as the same!
                    testconcentration = u"_" + conc
                    if testconcentration in toplvl:
                        # find condition
                        for cond in self.lst_Conditions:
                            if cond in toplvl:
                                # find replicate:
                                for rep in self.lst_Replicates:
                                    if rep in toplvl:
                                        lst_Files = os.listdir(toplvl)
                                        for fil in lst_Files:
                                            if ".txt" in fil and "result" in fil:
                                                str_FilePath = os.path.join(toplvl,fil)
                                                print(str_FilePath)
                                                self.dfr_DataStructure.loc[(conc,cond,rep),"FilePath"] = str_FilePath
                                                #print(conc + " " + cond + " " + rep)
        elif self.DataProcessor == "Harmony":
            for toplvl in lst_AllTopLevel:
                for conc in self.lst_Concentrations:
                    # concentration needs _ in front, otherwise "0.3uM" and "3uM" will be recongised as the same!
                    testconcentration = u"_" + conc
                    if testconcentration in toplvl:
                        # find condition
                        for cond in self.lst_Conditions:
                            if cond in toplvl:
                                # find replicate:
                                for rep in self.lst_Replicates:
                                    if rep in toplvl:
                                        str_FilePath = os.path.join(toplvl,"Evaluation1","PlateResults.txt")
                                        self.dfr_DataStructure.loc[(conc,cond,rep),"FilePath"] = str_FilePath
                
        # update self.tree_DataStructure
        concentration = self.tree_DataStructure.GetFirstItem()
        while concentration.IsOk():
            conc = self.tree_DataStructure.GetItemText(concentration,0)
            condition = self.tree_DataStructure.GetFirstChild(concentration)
            while condition.IsOk():
                cond = self.tree_DataStructure.GetItemText(condition,0)
                replicate = self.tree_DataStructure.GetFirstChild(condition)
                while replicate.IsOk():
                    rep = self.tree_DataStructure.GetItemText(replicate,0)
                    self.tree_DataStructure.SetItemText(replicate, 1, self.dfr_DataStructure.loc[(conc,cond,rep),"FilePath"])
                    replicate = self.tree_DataStructure.GetNextSibling(replicate)
                condition = self.tree_DataStructure.GetNextSibling(condition)
            concentration = self.tree_DataStructure.GetNextSibling(concentration)


        #for i in range(3):
        #    item = self.tree_DataStructure.GetNextItem(item)
        #    print(self.tree_DataStructure.GetItemText(item,0))

        #print(self.tree_DataStructure.GetItemText(self.tree_DataStructure.GetFirstItem()))
        #print(self.lst_Concentrations)
        #print(self.lst_Conditions)
        #print(self.lst_Replicates)

        self.bol_DataFilesAssigned = True
        

    def EditCells(self, event):
        self.grd_Capillaries.ClearSelection()
        col = event.GetCol()
        if col > 0:
            self.grd_Capillaries.SetGridCursor(event.GetRow(),col)
            self.grd_Capillaries.EnableEditing(True)
        else:
            self.grd_Capillaries.EnableEditing(False)

    def OnKeyPress(self, event):
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya
        """
        Handles all key events.
        """
        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            self.GridCopy()

        # Ctrl+V
        elif event.ControlDown() and event.GetKeyCode() == 86:
            self.GridPaste(self.grd_Capillaries.SingleSelection[0], self.grd_Capillaries.SingleSelection[1])

        # DEL
        elif event.GetKeyCode() == 127:
            self.GridClear()

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            self.grd_Capillaries.SelectAll()

        # Ctrl+X
        elif event.ControlDown() and event.GetKeyCode() == 88:
            # Call delete method
            self.GridCut()

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and event.GetKeyCode() == 67) \
                or (event.ShiftDown() and event.GetKeyCode() == 322):
            self.GridPaste(self.grd_Capillaries.SingleSelection[0], self.grd_Capillaries.SingleSelection[1])

        else:
            event.Skip()

    def GetGridSelection(self):
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_Capillaries.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_Capillaries.GetSelectionBlockBottomRight()
        lst_Selection = []
        for i in range(len(lst_TopLeftBlock)):
            # Nuber of columns:
            int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1 # add 1 because if just one cell/column is selected, subtracting the coordinates will be 0!
            # Nuber of rows:
            int_Rows = lst_BotRightBlock[i][0] - lst_TopLeftBlock[i][0] + 1 # add 1 because if just one cell/row is selected, subtracting the coordinates will be 0!
            # Get all cells:
            for x in range(int_Columns):
                for y in range(int_Rows):
                    new = [lst_TopLeftBlock[i][0]+y,lst_TopLeftBlock[i][1]+x]
                    if lst_Selection.count(new) == 0:
                        lst_Selection.append(new)
        return lst_Selection

    def GridCopy(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0], self.grd_Capillaries.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_Capillaries.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0], self.grd_Capillaries.SingleSelection[1]]]
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_Capillaries.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grd_Capillaries.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0], self.grd_Capillaries.SingleSelection[1]]]
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grd_Capillaries.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GridPaste(self, row, col):
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grd_Capillaries.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def SingleSelection(self, event):
        self.grd_Capillaries.SingleSelection = (event.GetRow(), event.GetCol())

    def EditLayouts(self, event):
        """
        Launches dialog to edit plate layouts. Sends dfr_Layout back.
        """
        #self.dlg_Layout = plm.PlateLayoutCBCS(self, self.dfr_Layout, self.int_PlateFormat)
        self.dlg_Layout = plm.PlateLayout(self, plates = [],
                                          dfr_Layout = self.dfr_Layout, 
                                          wells = self.int_PlateFormat,
                                          multiples = False,
                                          plateids = self.bol_PlateID,
                                          proteins = False,
                                          references = True,
                                          controls = True,
                                          sampleids = True)
        self.dlg_Layout.ShowModal()
        self.dlg_Layout.Destroy()
        #else:
        #    wx.MessageBox("You have not imported any destination/assay plates, yet.\nImport plates and try again.",
        #        "No plates",
        #        wx.OK|wx.ICON_INFORMATION)

    # 2. Functions for TransferData
    # ======================================================================================================
    #
    #  ######   ####   #####    ####       ######  ##  ##      ######   #####
    #    ##    ##  ##  ##  ##      ##      ##      ##  ##      ##      ##
    #    ##    ######  #####     ###   ##  ####    ##  ##      ####     ####
    #    ##    ##  ##  ##  ##  ##          ##      ##  ##      ##          ##
    #    ##    ##  ##  #####   ######  ##  ##      ##  ######  ######  #####
    #
    # ======================================================================================================

    # 3. Functions for Review
    # ======================================================================================================
    #
    #  ######   ####   #####    ####       #####   ######  ##  ##  ##  ######  ##      ##
    #    ##    ##  ##  ##  ##      ##      ##  ##  ##      ##  ##  ##  ##      ##  ##  ##
    #    ##    ######  #####     ###   ##  #####   ####    ##  ##  ##  ####    ##  ##  ##
    #    ##    ##  ##  ##  ##      ##      ##  ##  ##       ####   ##  ##       ########
    #    ##    ##  ##  #####   #####   ##  ##  ##  ######    ##    ##  ######    ##  ##
    #
    # ======================================================================================================

    # 3.1 Populate the tab
    def PopulateReviewTab(self):
        self.lbc_Conditions.DeleteAllItems()
        # Iterate through plates
        idx_List = -1
        for idx in self.dfr_Processed.index:
            idx_List += 1
            self.lbc_Conditions.InsertItem(idx_List,idx[0])
            self.lbc_Conditions.SetItem(idx_List,1,idx[1])

        self.lbc_Conditions.Select(0)
        self.sbk_PlatePlots.SetSelection(0)
        self.bol_ReviewsDrawn = True

    def ShowPlate(self, event):
        if not event == None:
            event.Skip()
        idx_List, idx_Condition = self.GetPlateIndices()
        # Scatter plot: Replicate correlation
        self.UpdateReplicateCorrelation(idx_List, idx_Condition)
        self.lbl_RSquare.SetLabel(u"R"+chr(178)+ " = " + str(self.dfr_Processed.loc[idx_Condition,"RSquare"]))
        self.lbl_Pearson.SetLabel(u"p = " + str(self.dfr_Processed.loc[idx_Condition,"Pearson"]))
        # Heatmap
        self.UpdateHeatmap(idx_Condition, self.int_PlateFormat)

    def GetPlateIndices(self):
        idx_List = self.lbc_Conditions.GetFirstSelected()
        idx_Condition = (self.lbc_Conditions.GetItemText(idx_List,0), self.lbc_Conditions.GetItemText(idx_List,1))
        return idx_List, idx_Condition

    def ShowCorrelationTab(self, event):
        if not event == None:
            event.Skip()
        self.btn_ReplicateCorrlation.Activate()
        self.btn_Heatmap.Deactivate()
        self.sbk_PlatePlots.SetSelection(1)

    def UpdateReplicateCorrelation(self, idx_List, idx_Condition):
        
        self.plt_ReplicateCorrelation.Title = self.lbc_Conditions.GetItemText(idx_List,0) + self.lbc_Conditions.GetItemText(idx_List,1)
        self.plt_ReplicateCorrelation.SampleIDs = self.dfr_Layout.loc[0,"SampleID"]
        self.plt_ReplicateCorrelation.Replicate1 = self.dfr_DataStructure.loc[(self.lbc_Conditions.GetItemText(idx_List,0),
            self.lbc_Conditions.GetItemText(idx_List,1), "R1"),"Normalised"]["PerCent"]
        self.plt_ReplicateCorrelation.Replicate2 = self.dfr_DataStructure.loc[(self.lbc_Conditions.GetItemText(idx_List,0),
            self.lbc_Conditions.GetItemText(idx_List,1), "R2"),"Normalised"]["PerCent"]
        self.plt_ReplicateCorrelation.Extremes = np.linspace(0,np.max(self.dfr_Processed.loc[idx_Condition,"Data"]["NormMeanPerCent"]),2)
        self.plt_ReplicateCorrelation.Fit = draw_linear(self.plt_ReplicateCorrelation.Extremes, [self.dfr_Processed.loc[idx_Condition,"m"],self.dfr_Processed.loc[idx_Condition,"c"]])
        self.plt_ReplicateCorrelation.RSquare = self.dfr_Processed.loc[idx_Condition,"RSquare"]
        self.plt_ReplicateCorrelation.Pearson = self.dfr_Processed.loc[idx_Condition,"Pearson"]
        self.plt_ReplicateCorrelation.Draw()

    def ShowHeatmapTab(self, event):
        if not event == None:
            event.Skip()
        self.btn_ReplicateCorrlation.Deactivate()
        self.btn_Heatmap.Activate()
        self.sbk_PlatePlots.SetSelection(0)

    def UpdateHeatmap(self, idx_Condition, int_PlateFormat):
        self.Freeze()
        dfr_Mean = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        #flt_MeanMin = dfr_Mean.
        dfr_Rep1 = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        dfr_Rep2 = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        if self.rad_ReviewRaw.GetValue() == True:
            which_Processed = "RawMean"
            which_Structure = "RawData"
            which_Structure_Subframe = "Readout"
            self.plt_Heatmap.ylabel = "Mean of raw signal"
        elif self.rad_ReviewNorm.GetValue() == True:
            which_Processed = "NormMean"
            which_Structure = "Normalised"
            which_Structure_Subframe = "Normalised"
            self.plt_Heatmap.ylabel = "Mean of normalised signal"
        elif self.rad_ReviewSolventNormalised.GetValue() == True:
            which_Processed = "NormMeanPerCent"
            which_Structure = "Normalised"
            which_Structure_Subframe = "PerCent"
            self.plt_Heatmap.ylabel = "Per-cent of solvent control"
        elif self.rad_ReviewZScore.GetValue() == True:
            which_Processed = "ZScore"
            which_Structure = "Normalised"
            which_Structure_Subframe = "Normalised"
            self.plt_Heatmap.ylabel = "Z score"
        elif self.rad_ReviewDeltaZScore.GetValue() == True:
            which_Processed = "DeltaZScore"
            which_Structure = "Normalised"
            which_Structure_Subframe = "Normalised"
            self.plt_Heatmap.ylabel = "Delta Z score"
        for i in range(int_PlateFormat):
            #dfr_Mean.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Mean.loc[i,"SampleID"] = self.dfr_Layout.loc[0,"SampleID"][i]
            #dfr_Rep1.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Rep1.loc[i,"SampleID"] = self.dfr_Layout.loc[0,"SampleID"][i]
            #dfr_Rep2.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Rep2.loc[i,"SampleID"] = self.dfr_Layout.loc[0,"SampleID"][i]
        dfr_Mean["Value"] = self.dfr_Processed.loc[idx_Condition,"Data"][which_Processed]
        dfr_Rep1["Value"] = self.dfr_DataStructure.loc[(idx_Condition[0],idx_Condition[1],"R1"),which_Structure][which_Structure_Subframe]
        dfr_Rep2["Value"] = self.dfr_DataStructure.loc[(idx_Condition[0],idx_Condition[1],"R2"),which_Structure][which_Structure_Subframe]
        vmin = np.nanmin([dfr_Mean["Value"].min(),dfr_Rep1["Value"].min(),dfr_Rep2["Value"].min()])
        vmax = np.nanmax([dfr_Mean["Value"].max(),dfr_Rep1["Value"].max(),dfr_Rep2["Value"].max()])
        self.plt_Heatmap.Data = dfr_Mean
        self.plt_Heatmap.Title = idx_Condition[0]+idx_Condition[1]
        self.plt_Heatmap.vmax, self.plt_Heatmap.vmin = vmax, vmin
        self.plt_Heatmap.Draw()
        self.plt_HeatmapRep1.Data = dfr_Rep1
        self.plt_HeatmapRep1.vmax, self.plt_HeatmapRep1.vmin = vmax, vmin
        self.plt_HeatmapRep1.Draw()
        self.plt_HeatmapRep2.Data = dfr_Rep2
        self.plt_HeatmapRep2.vmax, self.plt_HeatmapRep2.vmin = vmax, vmin
        self.plt_HeatmapRep2.Draw()
        self.Thaw()

    def UpdateReviewRadioButtons(self, event):
        for radbtn in self.dic_ReviewRadioButtons.keys():
            self.dic_ReviewRadioButtons[radbtn].SetValue(False)
        event.GetEventObject().SetValue(True)
        idx_List, idx_Condition = self.GetPlateIndices()
        self.UpdateHeatmap(idx_Condition, self.int_PlateFormat)

    def ZScoreToolTip(self, event):
        try: self.dlg_InfoToolTip.Destroy()
        except: None
        self.dlg_InfoToolTip = tt.dlg_InfoToolTip(self, self.parent.str_OtherPath, "ZScoreToolTip.png")
        self.dlg_InfoToolTip.Show()

    def DeltaZScoreToolTip(self, event):
        try: self.dlg_InfoToolTip.Destroy()
        except: None
        self.dlg_InfoToolTip = tt.dlg_InfoToolTip(self, self.parent.str_OtherPath, "DeltaZScoreToolTip.png")
        self.dlg_InfoToolTip.Show()

    #4. Functions for Results
    # ======================================================================================================
    #
    #  ######   ####   #####   ##          #####   ######   #####  ##  ##  ##    ######   #####
    #    ##    ##  ##  ##  ##  ## ##       ##  ##  ##      ##      ##  ##  ##      ##    ##
    #    ##    ######  #####   ######  ##  #####   ####     ####   ##  ##  ##      ##     ####
    #    ##    ##  ##  ##  ##     ##       ##  ##  ##          ##  ##  ##  ##      ##        ##
    #    ##    ##  ##  #####      ##   ##  ##  ##  ######  #####    ####   ######  ##    #####
    #
    # ======================================================================================================

    # 4.1 Populate the tab
    def PopulateResultsTab(self):
        self.lbc_Samples.DeleteAllItems()
        dfr_List = self.dfr_SampleInfo.sort_values(by="MaxDeltaZScore",ascending=True)
        idx = -1
        for well in dfr_List.index.tolist():
            if self.dfr_Layout.loc[0,"WellType"][well] == "s":
                idx += 1
                self.lbc_Samples.InsertItem(idx,pf.index_to_well(well+1,self.int_PlateFormat))
                self.lbc_Samples.SetItem(idx,1,self.dfr_Layout.loc[0,"SampleID"][well])
                self.lbc_Samples.SetItem(idx,2,str(self.dfr_SampleInfo.loc[well,"MaxDeltaZScore"]))
            
        dfr_DeltaZ = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(self.dfr_SampleInfo.shape[0]))
        dfr_DeltaZ["Value"] = self.dfr_SampleInfo["MaxDeltaZScore"]
        dfr_DeltaZ["SampleID"] = self.dfr_Layout.loc[0,"SampleID"]
        self.plt_PlateMap.Data = dfr_DeltaZ
        self.plt_PlateMap.Title = "Max Delta Z score"
        self.plt_PlateMap.Draw()
        self.bol_ResultsDrawn = True

        self.lbc_Samples.Select(0)
        
    # 4.3 Show/Update the displayed curve based on selection on ListCtr
    def ShowCurvePlateMap(self,event):
        row, col = event.GetRow(),event.GetCol()
        idx_Well = col + (row)*pf.plate_columns(self.int_PlateFormat)
        str_Well = pf.index_to_well(idx_Well, self.int_PlateFormat)
        for i in range(self.lbc_Samples.ItemCount):
            if self.lbc_Samples.GetItemText(i,0) == str_Well:
                self.lbc_Samples.Select(i)
                break

    def ShowCurveList(self,event):
        if not event == None:
            event.Skip()
        idx_List = self.lbc_Samples.GetFirstSelected()
        str_Well = self.lbc_Samples.GetItemText(idx_List,0)
        str_Sample = self.dfr_Layout.loc[0,"SampleID"][pf.well_to_index(str_Well,self.int_PlateFormat)]
        if len(str_Sample) > 40:
            str_Sample = str_Sample[:40] + "..."
        idx_Well = pf.well_to_index(str_Well, self.int_PlateFormat)
        # Determine what to show:
        if self.rad_ResultsRaw.GetValue() == True:
            which = "RawMean"
            self.plt_SamplePlot.YLabel = "Mean of raw signal"
        elif self.rad_ResultsNorm.GetValue() == True:
            which = "NormMean"
            self.plt_SamplePlot.YLabel = "Mean of normalised signal"
        elif self.rad_ResultsSolventNormalised.GetValue() == True:
            which = "NormMeanPerCent"
            self.plt_SamplePlot.YLabel = "Per-cent of solvent control"
        elif self.rad_ResultsZScore.GetValue() == True:
            which = "ZScore"
            self.plt_SamplePlot.YLabel = "Z score"
        elif self.rad_ResultsDeltaZScore.GetValue() == True:
            which = "DeltaZScore"
            self.plt_SamplePlot.YLabel = "Delta Z score"
        # Pull data from dataframe
        dfr_Sample = pd.DataFrame(columns=self.lst_ConcentrationsMolar,index=self.lst_Conditions)
        for n in range(len(self.lst_Conditions)):
            cond = self.lst_Conditions[n]
            for c in range(len(self.lst_Concentrations)):
                conc = self.lst_Concentrations[c]
                dfr_Sample.iloc[n,c] = self.dfr_Processed.loc[(conc,cond),"Data"].loc[idx_Well,which]
        self.plt_SamplePlot.Input = dfr_Sample
        self.plt_SamplePlot.Title = str_Well + ": " + str_Sample
        self.plt_SamplePlot.Draw()
        # Show well marker on plate map
        try:
            self.plt_PlateMap.dic_WellMarker[0].remove()
            self.plt_PlateMap.canvas.blit()
            self.plt_PlateMap.canvas.restore_region(self.plt_PlateMap.Backup)
        except:
            None
        y, x = pf.index_to_row_col(idx_Well, pf.plate_rows(self.int_PlateFormat), pf.plate_columns(self.int_PlateFormat))
        self.plt_PlateMap.dic_WellMarker = {}
        self.plt_PlateMap.dic_WellMarker[0] = patches.Rectangle((x-0.5,y-0.5),1,1,ec="yellow",fill=False,linewidth=1)
        self.plt_PlateMap.axes.add_patch(self.plt_PlateMap.dic_WellMarker[0])
        self.plt_PlateMap.axes.draw_artist(self.plt_PlateMap.dic_WellMarker[0])
        self.plt_PlateMap.canvas.blit()

    def UpdateResultsRadioButtons(self, event):
        for radbtn in self.dic_ResultsRadioButtons.keys():
            self.dic_ResultsRadioButtons[radbtn].SetValue(False)
        event.GetEventObject().SetValue(True)
        self.ShowCurveList(None)

    def ExportResultsTable(self,event):
        print("fnord")

    # 4.6 Get the indices of the selected plot from the self.dfr_AssayData
    def GetPlotIndices(self):
        # Get list index of selected sample
        idx_SampleList = self.lbc_Samples.GetFirstSelected()
        # Get plate index
        idx_Plate = 0 # int(self.lbc_Samples.GetItemText(idx_SampleList,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.dfr_AssayData.iloc[idx_Plate,5]
        idx_SampleDataFrame = dfr_Sample[dfr_Sample["CapIndex"] == int(self.lbc_Samples.GetItemText(idx_SampleList,0))].index.tolist()
        idx_SampleDataFrame = idx_SampleDataFrame[0] # above function returns list, but there will always be only one result
        return idx_SampleList, idx_SampleDataFrame, idx_Plate
    
    def ClosePlotToolTip(self, event):
        """
        Since the plot tooltip is not a real tooltip, just a dialog box, we also needa workaround to close it when we do not need it anymore.
        This function will try to destroy the tooltip, if there is one. Otherwise, the tooltip will just stay like a dialog.
        """
        try: self.tltp.Destroy()
        except: None

    def UpdateDetailPlot(fnord, self, x, y):
        row = y
        col = x
        idx_Well = col + (row)*pf.plate_columns(self.int_PlateFormat)
        str_Well = pf.index_to_well(idx_Well+1, self.int_PlateFormat)
        for i in range(self.lbc_Samples.ItemCount):
            if self.lbc_Samples.GetItemText(i,0) == str_Well:
                self.lbc_Samples.Select(i)
                break
        #dfr_Sample = pd.DataFrame(columns=self.lst_Concentrations,index=self.lst_Conditions)
        #for cond in self.lst_Conditions:
        #    for conc in self.lst_Concentrations:
        #        dfr_Sample.loc[cond,conc] = self.dfr_Processed.loc[(conc,cond),"Data"].loc[idx_Well,"DeltaZScore"]
        #self.plt_SamplePlot.Input = dfr_Sample
        #self.plt_SamplePlot.Title = pf.index_to_well(idx_Well,self.int_PlateFormat)
        #self.plt_SamplePlot.Draw()

    # 5.Functions for the plots for ELN page tab
    # ======================================================================================================
    #
    #  ######   ####   #####   ######       #####  #####    ####   #####   ##  ##   #####
    #    ##    ##  ##  ##  ##  ##          ##      ##  ##  ##  ##  ##  ##  ##  ##  ##
    #    ##    ######  #####   #####   ##  ##  ##  #####   ######  #####   ######   ####
    #    ##    ##  ##  ##  ##      ##      ##  ##  ##  ##  ##  ##  ##      ##  ##      ##
    #    ##    ##  ##  #####   #####   ##   ####   ##  ##  ##  ##  ##      ##  ##  #####
    #
    # ======================================================================================================

    # 6. Functions for Export to Database 
    # ======================================================================================================
    #
    #  ######   ####   #####    #####       #####   #####   ####   #####    ####   #####
    #    ##    ##  ##  ##  ##  ##          ##      ##      ##  ##  ##  ##  ##  ##  ##  ##
    #    ##    ######  #####   #####   ##   ####   ##      ######  #####   ######  #####
    #    ##    ##  ##  ##  ##  ##  ##          ##  ##      ##  ##  ##  ##  ##  ##  ##  ##
    #    ##    ##  ##  #####    ####   ##  #####    #####  ##  ##  ##  ##  ##  ##  #####
    #
    # ======================================================================================================
