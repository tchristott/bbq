"""
Contains plate layout and sample ID menu for analysis setup.

    Classes:
        PlateLayout
        PlateContextMenu
        SampleContextMenu

"""

import wx
import wx.xrc
import wx.grid
from os import path

import lib_colourscheme as cs
import lib_platefunctions as pf
from lib_datafunctions import make_list, import_string_to_list
from lib_custombuttons import CustomBitmapButton, MiniTabButton
import pandas as pd



class PlateLayout(wx.Dialog):
    """
    Window to define plate layouts: well types (sample, reference,
    control), sample IDs, proteins, plate IDs.
    
    If user closes window via "Apply and Close", a dataframe with
    plates as index and the following columns is saved to the parent
    object: "PlateID",
            "ProteinNumerical",
            "PurificationID",
            "ProteinConcentration",
            "ControlNumerical",
            "ControlID",
            "ControlConcentration"
            "WellType",
            "SampleID"

    Methods:
        __init__
        ChangeTab
        OnMouseMove
        OnLeftDown
        OnLeftUp
        AddProtein
        RemoveProtein
        AddControl
        RemoveControl
        Export
        Import
        ApplyAndClose
        Cancel
        ShowMenuPlate
        GetSelectionPlate
        OnMouseOverPlate
        PaintSample
        PaintControl
        PaintReference
        PaintBlank
        ClearPlate
        SetWellType
        WriteProtein
        WriteControl
        DetermineWellType
        DetermineWellColour
        UpdateDataframe
        Refresh
        UpdatePlateID
        ShowContextSamples
        GetSelectionSamples
        WellChangedSamples
        OnKeyPressSamples
        GetGridSelectionSamples
        GridCopy
        GridCut
        GridClear
        GridPaste
        SingleSelectionSamples

    """

    def __init__(self, parent, plates, dfr_Layout: pd.DataFrame, wells: int,
                 multiples = False, plateids = False, proteins = True,
                 references = True, controls = False, sampleids = False):
        """
        Initialises class attributes

        Arguments:
            parent -> parent object in GUI.
            plates -> list of plate names.
            dfr_Layout -> pandas dataframe. If a plate layout has
                          already been defined, the contents of
                          this dataframe will be displayed.
            multiples -> boolean. Whether this dialog is to set up
                         a single plate's layout or whether to
                         prepare multiple layouts.
            wells -> integer. Plate format in number of wells.
            plateid -> boolean. Whether plate IDs are used for
                       generating a platemap for the database.
                       Specific to our org.
            references -> boolean. Use reference wells.
            controls -> boolean. Use control compounds/wells.
        """

        self.bol_proteins = proteins
        self.bol_controls = controls
        self.bol_references = references
        self.bol_sampleids = sampleids
        # Variables for sizing of elements ##############################################
        self.plateformat = wells
        self.PlateID = plateids
        if self.plateformat == 96:
            int_CellSize = 31
            int_XSizeModifier = 0
            int_YSizeModifier = +7
            int_SampleIDX = 402
            int_SampleIDY = 310
        elif self.plateformat == 384:
            int_CellSize = 17
            int_XSizeModifier = 24
            int_YSizeModifier = 0
            int_SampleIDX = 430
            int_SampleIDY = 320
        elif self.plateformat == 1536:
            int_CellSize = 9
            int_XSizeModifier = +35
            int_YSizeModifier = +10
            int_SampleIDX = 440
            int_SampleIDY = 330
        if self.PlateID == True:
            int_PlateIDOffset = 0
        else:
            int_PlateIDOffset = -7
        if multiples == True:
            self.bol_MultiplePlates = True
            WindowSize = wx.Size(850 + int_XSizeModifier,
                                 445 + int_YSizeModifier + int_PlateIDOffset)
            int_Plates = len(plates)
        elif multiples == False:
            self.bol_MultiplePlates = False
            WindowSize = wx.Size(680 + int_XSizeModifier,
                                 445 + int_YSizeModifier + int_PlateIDOffset)
            int_Plates = 1

        # Initialise ####################################################################
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = wx.EmptyString,
                           pos = wx.DefaultPosition, size = WindowSize,
                           style = wx.TAB_TRAVERSAL)

        # Get the current directory and use that for the buttons
        real_path = path.realpath(__file__)
        dir_path = path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.szr_Frame = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Panel = wx.Panel(self)
        self.pnl_Panel.SetBackgroundColour(cs.BgMedium)

        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        # TITLE BAR #####################################################################
        self.pnl_TitleBar = wx.Panel(self.pnl_Panel)
        self.pnl_TitleBar.SetBackgroundColour(cs.BgUltraDark)
        self.pnl_TitleBar.SetForegroundColour(cs.White)
        self.szr_TitleBar = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Title = wx.StaticText(self.pnl_TitleBar, label= u"Define plate layout")
        self.lbl_Title.Wrap(-1)
        self.szr_TitleBar.Add( self.lbl_Title, 0, wx.ALL, 5 )
        self.szr_TitleBar.Add((0,0), 1, wx.EXPAND, 5)
        self.btn_X = CustomBitmapButton(self.pnl_TitleBar,
                                        type = "small_x",
                                        index = 0,
                                        size = (25,25),
                                        pathaddendum = u"titlebar")
        self.szr_TitleBar.Add(self.btn_X,0,wx.ALL,0)
        self.pnl_TitleBar.SetSizer(self.szr_TitleBar)
        self.pnl_TitleBar.Layout()
        self.szr_Surround.Add(self.pnl_TitleBar, 0, wx.EXPAND, 5)

        self.szr_Contents = wx.BoxSizer(wx.HORIZONTAL)

        if self.bol_MultiplePlates == True:
            self.pnl_PlateList = wx.Panel(self.pnl_Panel)
            self.pnl_PlateList.SetBackgroundColour(cs.BgLight)
            self.szr_PlateList = wx.BoxSizer(wx.VERTICAL)
            self.lbl_PlateList = wx.StaticText(self.pnl_PlateList, label = u"Plates:")
            self.lbl_PlateList.Wrap(-1)
            self.szr_PlateList.Add(self.lbl_PlateList, 0, wx.ALL, 5)
            self.lbx_PlateList = wx.ListBox(self.pnl_PlateList,
                                            size = wx.Size(150,280),
                                            choices = [])
            self.szr_PlateList.Add(self.lbx_PlateList, 1, wx.ALL, 5)
            self.pnl_PlateList.SetSizer(self.szr_PlateList)
            self.pnl_PlateList.Layout()
            self.szr_Contents.Add(self.pnl_PlateList, 1, wx.ALL, 5)
            self.lbx_PlateList.InsertItems(plates,0)
            self.lbx_PlateList.Select(0)
            self.lbx_PlateList.Bind(wx.EVT_LISTBOX, self.Refresh)

        # PLATE MAP GRID
        self.szr_LayoutAndSamples = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateNoteBookButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_PlateLayout = MiniTabButton(self.pnl_Panel,
                                             changetabowner = self,
                                             label = u"Plate Layout",
                                             index = 0)
        self.btn_PlateLayout.IsCurrent(True)
        self.btn_SampleIDs = MiniTabButton(self.pnl_Panel,
                                           changetabowner = self,
                                           label = u"Sample IDs",
                                           index = 1)
        self.btn_SampleIDs.IsEnabled(self.bol_sampleids)
        self.dic_PlateNoteBookButtons = {0:self.btn_PlateLayout,
                                         1:self.btn_SampleIDs}
        self.btn_PlateLayout.Group = self.dic_PlateNoteBookButtons
        self.btn_SampleIDs.Group = self.dic_PlateNoteBookButtons
        self.sbk_LayoutAndSamples = wx.Simplebook(self.pnl_Panel)
        self.btn_PlateLayout.Notebook = self.sbk_LayoutAndSamples
        self.btn_SampleIDs.Notebook = self.sbk_LayoutAndSamples
        self.szr_PlateNoteBookButtons.Add(self.btn_PlateLayout, 0, wx.ALL, 0)
        self.szr_PlateNoteBookButtons.Add(self.btn_SampleIDs, 0, wx.ALL, 0)
        self.szr_LayoutAndSamples.Add(self.szr_PlateNoteBookButtons, 0, wx.ALL, 0)

        # Simple book page: Plate Layout
        self.pnl_PlateMap = wx.Panel(self.sbk_LayoutAndSamples)
        self.pnl_PlateMap.SetBackgroundColour(cs.BgLight)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PlateMap = wx.StaticText(self.pnl_PlateMap, label = u"Plate map:")
        self.szr_PlateID.Add(self.lbl_PlateMap, 0, wx.ALL, 5)
        self.szr_PlateID.Add((-1,22), 1, wx.EXPAND, 5)
        if self.PlateID == True:
            self.lbl_PlateID = wx.StaticText(self.pnl_PlateMap,
                                             label = u"Plate ID:",
                                             size = wx.Size(-1,22))
            self.szr_PlateID.Add(self.lbl_PlateID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.txt_PlateID = wx.TextCtrl(self.pnl_PlateMap,
                                           value = u"X999A",
                                           size = wx.Size(55,22))
            self.txt_PlateID.SetBackgroundColour(cs.BgUltraLight)
            self.szr_PlateID.Add(self.txt_PlateID, 0, wx.ALL, 5)
        self.szr_Grid.Add(self.szr_PlateID, 1, wx.EXPAND, 0)
        self.grd_Plate = wx.grid.Grid(self.pnl_PlateMap)
        # Parameters for grid
        int_Columns = pf.plate_columns(self.plateformat)
        int_Rows = pf.plate_rows(self.plateformat)
        # Grid
        self.grd_Plate.CreateGrid(int_Rows, int_Columns)
        self.grd_Plate.EnableEditing(False)
        self.grd_Plate.EnableGridLines(True)
        self.grd_Plate.EnableDragGridSize(False)
        self.grd_Plate.SetMargins(0, 0)
        # Columns
        self.grd_Plate.SetColMinimalAcceptableWidth(int_CellSize)
        for i in range(int_Columns):
            self.grd_Plate.SetColSize(i, int_CellSize)
            self.grd_Plate.SetColLabelValue(i, str(i+1))
        self.grd_Plate.EnableDragColMove(False)
        self.grd_Plate.EnableDragColSize(False)
        self.grd_Plate.SetColLabelSize(int_CellSize)
        self.grd_Plate.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_Plate.SetRowMinimalAcceptableHeight(int_CellSize)
        for i in range(int_Rows):
            self.grd_Plate.SetRowSize(i, int_CellSize)
            self.grd_Plate.SetRowLabelValue(i, chr(65+i))
        self.grd_Plate.EnableDragRowSize(False)
        self.grd_Plate.SetRowLabelSize(int_CellSize)
        self.grd_Plate.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_Plate.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_Grid.Add(self.grd_Plate, 0, wx.ALL, 5)
        self.pnl_PlateMap.SetSizer(self.szr_Grid)
        self.sbk_LayoutAndSamples.AddPage(self.pnl_PlateMap, text = u"Plate Map",
                                          select = True)

        self.szr_LayoutAndSamples.Add(self.sbk_LayoutAndSamples, 0, wx.ALL, 0)

        # SimpleBook Page: Sample IDs
        self.pnl_SampleIDs = wx.Panel(self.sbk_LayoutAndSamples)
        self.pnl_SampleIDs.SetBackgroundColour(cs.BgLight)
        self.szr_SampleIDs = wx.BoxSizer(wx.VERTICAL)
        self.grd_SampleIDs = wx.grid.Grid(self.pnl_SampleIDs,
                                          size = wx.Size(int_SampleIDX,int_SampleIDY))
        # Parameters for grid
        int_CellSize = 20
        # Grid
        self.grd_SampleIDs.CreateGrid(self.plateformat, 2 )
        self.grd_SampleIDs.EnableEditing(True)
        self.grd_SampleIDs.EnableGridLines(True)
        self.grd_SampleIDs.EnableDragGridSize(False)
        self.grd_SampleIDs.SetMargins(0, 0)
        # Columns
        self.grd_SampleIDs.SetColMinimalAcceptableWidth(int_CellSize)
        self.grd_SampleIDs.SetColSize(0, 50)
        self.grd_SampleIDs.SetColLabelValue(0, "Well")
        self.grd_SampleIDs.SetColSize(1, int_SampleIDX - 100)
        self.grd_SampleIDs.SetColLabelValue(1, "Sample ID")
        self.grd_SampleIDs.EnableDragColMove(False)
        self.grd_SampleIDs.EnableDragColSize(False)
        self.grd_SampleIDs.SetColLabelSize(int_CellSize)
        self.grd_SampleIDs.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_SampleIDs.SetRowMinimalAcceptableHeight(int_CellSize)
        self.grd_SampleIDs.SingleSelection = (0,0)
        for i in range(self.plateformat):
            self.grd_SampleIDs.SetRowSize(i, int_CellSize)
            self.grd_SampleIDs.SetRowLabelValue(i, str(i+1))
        self.grd_SampleIDs.EnableDragRowSize(False)
        self.grd_SampleIDs.SetRowLabelSize(30)
        self.grd_SampleIDs.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_SampleIDs.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_SampleIDs.Add(self.grd_SampleIDs, 0, wx.ALL, 5)
        self.pnl_SampleIDs.SetSizer(self.szr_SampleIDs)
        self.pnl_SampleIDs.Layout()
        self.szr_SampleIDs.Fit(self.pnl_SampleIDs)
        self.sbk_LayoutAndSamples.AddPage(self.pnl_SampleIDs, text = u"Sample IDs",
                                          select = False)

        self.szr_Contents.Add(self.szr_LayoutAndSamples, 0, wx.ALL, 5)
        
        # Right Sizer ###################################################################
        self.szr_Right = wx.BoxSizer(wx.VERTICAL)
        
        self.szr_Definitions = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleButtons = wx.BoxSizer(wx.HORIZONTAL)
        # Define simplebook now, add elements to it and add it
        # to the dialog later.
        self.sbk_Definitions = wx.Simplebook(self.pnl_Panel,
                                             size = wx.Size(235,-1))
        self.dic_DefinitionsButtons = {}

        # Proteins
        self.btn_Proteins = MiniTabButton(self.pnl_Panel,
                                          changetabowner = self,
                                          label = u"Proteins",
                                          index = 0)
        self.dic_DefinitionsButtons["Proteins"] = self.btn_Proteins
        self.btn_Proteins.Notebook = self.sbk_Definitions
        self.btn_Proteins.Group = self.dic_DefinitionsButtons
        self.btn_Proteins.IsEnabled(self.bol_proteins)
        self.szr_SimpleButtons.Add(self.btn_Proteins, 0, wx.ALL, 0)
        # Prepare Protein list:
        self.pnl_ProteinList = wx.Panel(self.sbk_Definitions)
        self.pnl_ProteinList.SetBackgroundColour(cs.BgLight)
        self.szr_ProteinList = wx.BoxSizer(wx.VERTICAL)
        self.szr_TitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ProteinList = wx.StaticText(self.pnl_ProteinList, wx.ID_ANY,
                u"To add a new protein, select wells on the plate map to the left and press \"Add new.\"")
        self.lbl_ProteinList.Wrap(225)
        self.szr_TitleAndList.Add(self.lbl_ProteinList, 0, wx.ALL, 0)
        self.szr_TitleAndList.Add((-1,5), 0, wx.ALL, 0)
        self.grd_ProteinList = wx.grid.Grid(self.pnl_ProteinList, size = wx.Size(225,91))
        # Grid
        self.grd_ProteinList.CreateGrid(1, 2)
        self.grd_ProteinList.EnableEditing(True)
        self.grd_ProteinList.EnableGridLines(True)
        self.grd_ProteinList.EnableDragGridSize(False)
        self.grd_ProteinList.SetMargins(0, 0)
        # Columns
        self.grd_ProteinList.SetColSize(0, 135)
        self.grd_ProteinList.SetColLabelValue(0, "Purification ID")
        self.grd_ProteinList.SetColSize(1, 45)
        self.grd_ProteinList.SetColLabelValue(1, "[uM]")
        self.grd_ProteinList.EnableDragColMove(False)
        self.grd_ProteinList.EnableDragColSize(False)
        self.grd_ProteinList.SetColLabelSize(20)
        self.grd_ProteinList.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_ProteinList.EnableDragRowSize(False)
        self.grd_ProteinList.SetRowLabelSize(25)
        self.grd_ProteinList.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_ProteinList.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_ProteinList.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        self.szr_TitleAndList.Add(self.grd_ProteinList, 0, wx.ALL, 0)
        self.szr_ProteinList.Add(self.szr_TitleAndList, 0, wx.ALL, 5)
        # Buttons
        self.szr_ProteinButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ProteinButtons.Add((55, 0), 1, wx.ALL, 0)
        self.btn_AddProtein = CustomBitmapButton(self.pnl_ProteinList, u"Add", 0, (75,30))
        self.szr_ProteinButtons.Add(self.btn_AddProtein, 0, wx.ALL, 0)
        self.szr_ProteinButtons.Add((5, 0), 1, wx.EXPAND, 0)
        self.btn_RemoveProtein = CustomBitmapButton(self.pnl_ProteinList, u"Remove", 0, (90,30))
        self.szr_ProteinButtons.Add(self.btn_RemoveProtein, 0, wx.ALL, 0)
        self.szr_ProteinList.Add(self.szr_ProteinButtons, 0, wx.ALL, 5)
        self.pnl_ProteinList.SetSizer(self.szr_ProteinList)
        self.pnl_ProteinList.Layout()
        self.sbk_Definitions.AddPage(self.pnl_ProteinList, text = u"Proteins",
                                     select = True)
        # Controls
        self.btn_Controls = MiniTabButton(self.pnl_Panel,
                                          changetabowner = self,
                                          label = u"Controls",
                                          index = 1)
        self.dic_DefinitionsButtons["Controls"] = self.btn_Controls
        self.btn_Controls.IsEnabled(self.bol_controls)
        self.btn_Controls.Notebook = self.sbk_Definitions
        self.btn_Controls.Group = self.dic_DefinitionsButtons
        self.szr_SimpleButtons.Add(self.btn_Controls, 0, wx.ALL, 0)
        # Control List
        self.pnl_ControlList = wx.Panel( self.sbk_Definitions)
        self.pnl_ControlList.SetBackgroundColour(cs.BgLight)
        self.szr_ControlList = wx.BoxSizer(wx.VERTICAL)
        self.szr_TitleAndList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_ControlList = wx.StaticText(self.pnl_ControlList, wx.ID_ANY,
                u"To add a new control, select wells on the plate map to the left and press \"Add new.\"")
        self.lbl_ControlList.Wrap(225)
        self.szr_TitleAndList.Add(self.lbl_ControlList, 0, wx.ALL, 0)
        self.szr_TitleAndList.Add((-1,5), 0, wx.ALL, 0)
        self.grd_ControlList = wx.grid.Grid(self.pnl_ControlList, size = wx.Size(225,91))
        # Grid
        self.grd_ControlList.CreateGrid(1, 2)
        self.grd_ControlList.EnableEditing(True)
        self.grd_ControlList.EnableGridLines(True)
        self.grd_ControlList.EnableDragGridSize(False)
        self.grd_ControlList.SetMargins(0, 0)
        # Columns
        self.grd_ControlList.SetColSize(0, 135)
        self.grd_ControlList.SetColLabelValue(0, "Control compound")
        self.grd_ControlList.SetColSize(1, 45)
        self.grd_ControlList.SetColLabelValue(1, "[uM]")
        self.grd_ControlList.EnableDragColMove(False)
        self.grd_ControlList.EnableDragColSize(False)
        self.grd_ControlList.SetColLabelSize(20)
        self.grd_ControlList.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_ControlList.EnableDragRowSize(False)
        self.grd_ControlList.SetRowLabelSize(25)
        self.grd_ControlList.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_ControlList.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_ControlList.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        self.szr_TitleAndList.Add(self.grd_ControlList, 0, wx.ALL, 0)
        self.szr_ControlList.Add(self.szr_TitleAndList, 0, wx.ALL, 5)
        # Buttons
        self.szr_ControlButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ControlButtons.Add((55, 0), 1, wx.ALL, 0)
        self.btn_AddControl = CustomBitmapButton(self.pnl_ControlList, u"Add", 0, (75,30))
        self.szr_ControlButtons.Add(self.btn_AddControl, 0, wx.ALL, 0)
        self.szr_ControlButtons.Add((5, 0), 1, wx.ALL, 0)
        self.btn_RemoveControl = CustomBitmapButton(self.pnl_ControlList, u"Remove", 0, (90,30))
        self.szr_ControlButtons.Add(self.btn_RemoveControl, 0, wx.ALL, 0)
        self.szr_ControlList.Add(self.szr_ControlButtons, 0, wx.ALL, 5)
        self.pnl_ControlList.SetSizer(self.szr_ControlList)
        self.pnl_ControlList.Layout()
        self.sbk_Definitions.AddPage(self.pnl_ControlList, u"Controls", select = True)
        # Initialise the simplebook:
        if self.bol_controls == True:
            self.btn_Proteins.IsCurrent(False)
            self.btn_Controls.IsCurrent(True)
            self.sbk_Definitions.SetSelection(1)
        if self.bol_proteins == True:
            self.btn_Proteins.IsCurrent(True)
            self.btn_Controls.IsCurrent(False)
            self.sbk_Definitions.SetSelection(0)

        self.szr_Definitions.Add(self.szr_SimpleButtons, 0, wx.ALL, 0)
        self.szr_Definitions.Add(self.sbk_Definitions, 0, wx.ALL, 0)

        self.szr_Right.Add(self.szr_Definitions, 0, wx.ALL, 5)

        # Samples and References
        self.pnl_SamplesAndReferences = wx.Panel(self.pnl_Panel,
                                                 size = wx.Size(245,-1))
        self.pnl_SamplesAndReferences.SetBackgroundColour(cs.BgLight)
        self.szr_SamplesAndReferences = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SamplesAndReferences = wx.StaticText(self.pnl_SamplesAndReferences,
            label = u"Sample and reference wells:\n" 
            + u"To define sample and reference wells,\n"
            + u"select intended wells, right click, and select appropriate option.")
        self.lbl_SamplesAndReferences.Wrap(240)
        self.szr_SamplesAndReferences.Add(self.lbl_SamplesAndReferences, 0, wx.ALL, 5)
        self.szr_Legend = wx.BoxSizer(wx.HORIZONTAL)
        self.png_Sample = wx.StaticBitmap(self.pnl_SamplesAndReferences, 
                                          bitmap = wx.Bitmap(str_MenuIconsPath
                                                             + u"\GridSample.png",
                                                              wx.BITMAP_TYPE_ANY ))
        self.szr_Legend.Add(self.png_Sample, 0, wx.ALL, 0)
        self.lbl_Sample = wx.StaticText(self.pnl_SamplesAndReferences, 
                                        label = u" Sample  ")
        self.szr_Legend.Add(self.lbl_Sample, 0, wx.ALL, 0)
        if references == True:
            self.png_Reference = wx.StaticBitmap(self.pnl_SamplesAndReferences, 
                                                 bitmap = wx.Bitmap(str_MenuIconsPath
                                                                     + u"\GridReference.png",
                                                                     wx.BITMAP_TYPE_ANY ))
            self.szr_Legend.Add(self.png_Reference, 0, wx.ALL, 0)
            self.lbl_Reference = wx.StaticText(self.pnl_SamplesAndReferences,
                                               label = u" Reference  ")
            self.szr_Legend.Add(self.lbl_Reference, 0, wx.ALL, 0)
        if controls == True:
            self.png_Control = wx.StaticBitmap(self.pnl_SamplesAndReferences,
                                               bitmap = wx.Bitmap(str_MenuIconsPath
                                                                  + u"\GridControl.png",
                                                                  wx.BITMAP_TYPE_ANY ))
            self.szr_Legend.Add(self.png_Control, 0, wx.ALL, 0)
            self.lbl_Control = wx.StaticText(self.pnl_SamplesAndReferences,
                                             label = u" Control  ")
            self.szr_Legend.Add(self.lbl_Control, 0, wx.ALL, 0)
        self.szr_SamplesAndReferences.Add(self.szr_Legend, 0, wx.ALL, 5)
        self.pnl_SamplesAndReferences.SetSizer(self.szr_SamplesAndReferences)
        self.pnl_SamplesAndReferences.Layout()
        self.szr_Right.Add(self.pnl_SamplesAndReferences,0,wx.ALL,5)
        
        self.szr_Contents.Add(self.szr_Right, 0, wx.EXPAND, 5)
        self.szr_Surround.Add(self.szr_Contents, 0, wx.ALL, 0)

        
        # Dividing line #################################################################
        self.line = wx.StaticLine(self.pnl_Panel)
        self.szr_Surround.Add(self.line, 0, wx.EXPAND|wx.ALL, 5)

        # Button bar at bottom
        self.szr_ButtonBar = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Import = CustomBitmapButton(self.pnl_Panel, u"Import", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Import, 0, wx.ALL, 5)
        self.btn_Export = CustomBitmapButton(self.pnl_Panel, u"Export", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_ButtonBar.Add( ( 0, 0), 1, wx.EXPAND, 5 )
        self.btn_Apply = CustomBitmapButton(self.pnl_Panel, u"ApplyAndClose", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Apply, 0, wx.ALL, 5)
        self.btn_Cancel = CustomBitmapButton(self.pnl_Panel, u"Cancel", 0, (100,30))
        self.szr_ButtonBar.Add(self.btn_Cancel, 0, wx.ALL, 5)
        self.szr_Surround.Add(self.szr_ButtonBar, 0, wx.ALL|wx.EXPAND, 0)
    
        self.pnl_Panel.SetSizer(self.szr_Surround)
        self.pnl_Panel.Layout()
        self.szr_Frame.Add(self.pnl_Panel,0,wx.EXPAND,0)

        self.SetSizer( self.szr_Frame )
        self.Layout()
        self.Centre( wx.BOTH )

        # Populate:
        if len(dfr_Layout) == 0:
            self.dfr_Layout = pd.DataFrame(index=range(int_Plates),
                                           columns=["PlateID",
                                                    "ProteinNumerical",
                                                    "PurificationID",
                                                    "ProteinConcentration",
                                                    "ControlNumerical",
                                                    "ControlID",
                                                    "ControlConcentration",
                                                    "WellType",
                                                    "SampleID"])
            for plate in range(int_Plates):
                if self.PlateID == True:
                    self.dfr_Layout.loc[plate,"PlateID"] = self.txt_PlateID.GetValue()
                else:
                    self.dfr_Layout.loc[plate,"PlateID"] = "X999A"
                self.dfr_Layout.loc[plate,"ProteinNumerical"] = []
                self.dfr_Layout.loc[plate,"PurificationID"] = []
                self.dfr_Layout.loc[plate,"ProteinConcentration"] = []
                self.dfr_Layout.loc[plate,"ControlNumerical"] = []
                self.dfr_Layout.loc[plate,"ControlID"] = []
                self.dfr_Layout.loc[plate,"ControlConcentration"] = []
                self.dfr_Layout.loc[plate,"WellType"] = []
                self.dfr_Layout.loc[plate,"SampleID"] = []
        else:
            self.dfr_Layout = dfr_Layout
            self.Refresh(None)

        # Connect Events ################################################################
        self.grd_Plate.GetGridWindow().Bind(wx.EVT_MOTION, self.OnMouseOverPlate)
        self.grd_Plate.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.ShowMenuPlate)
        self.grd_SampleIDs.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.SingleSelectionSamples)
        self.grd_SampleIDs.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.ShowContextSamples)
        self.grd_SampleIDs.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressSamples)
        self.grd_SampleIDs.Bind( wx.grid.EVT_GRID_CELL_CHANGED, self.WellChangedSamples)
        self.grd_ProteinList.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.UpdateDataframe)
        self.btn_AddProtein.Bind(wx.EVT_BUTTON, self.AddProtein)
        self.btn_RemoveProtein.Bind(wx.EVT_BUTTON, self.RemoveProtein)
        self.grd_ControlList.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.UpdateDataframe)
        self.btn_AddControl.Bind(wx.EVT_BUTTON, self.AddControl)
        self.btn_RemoveControl.Bind(wx.EVT_BUTTON, self.RemoveControl)
        if self.PlateID == True:
            self.txt_PlateID.Bind(wx.EVT_TEXT, self.UpdatePlateID)
        self.btn_Import.Bind(wx.EVT_BUTTON, self.Import)
        self.btn_Export.Bind(wx.EVT_BUTTON, self.Export)
        self.btn_Apply.Bind(wx.EVT_BUTTON, lambda event: self.ApplyAndClose(parent, event))
        self.btn_Cancel.Bind(wx.EVT_BUTTON, self.Cancel)
        self.btn_X.Bind(wx.EVT_BUTTON, self.Cancel)

        # Required for window dragging:
        self.delta = wx.Point(0,0)
        self.pnl_TitleBar.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.dragging = False

    def __del__( self ):
        pass

    def ChangeTab(self, fnord):
        """
        Dummy function required when using MiniTabButtons.
        Would normally perform chekcs to see whether changing
        tabs would be allowed.
        """
        return True

    # The following three function are taken from a tutorial on the wxPython Wiki: https://wiki.wxpython.org/How%20to%20create%20a%20customized%20frame%20-%20Part%201%20%28Phoenix%29
    # They have been modified if and where appropriate.

    def OnMouseMove(self, event):
        """
        Changes position of window based on mouse movement
        if left mouse button is down on titlebar.
        """
        if self.dragging == True:
            if event.Dragging() and event.LeftIsDown():
                x,y = self.ClientToScreen(event.GetPosition())
                newPos = (x - self.delta[0], y - self.delta[1])
                self.Move(newPos)

    def OnLeftDown(self, event):
        """
        Initiates all required properties for window dragging.
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
        Releases mouse capture and resets property for window
        dragging.
        """
        if self.HasCapture():
            self.ReleaseMouse()
        self.dragging = False

    def AddProtein(self, event):
        """
        Adds a protein to the list and updates dataframe.
        Selecting wells on plate layout is required.
        """
        lst_Selection = self.GetSelectionPlate()
        if len(lst_Selection) > 0:
            int_Rows = self.grd_ProteinList.GetNumberRows()
            if self.grd_ProteinList.GetCellValue(0,0) != "" and self.grd_ProteinList.GetCellValue(0,0) != "":
                self.grd_ProteinList.AppendRows(1,True) # specify number of rows to add, not where to add them
                self.grd_ProteinList.SetCellValue(int_Rows,0,"PROTEIN" + str(int_Rows+1) + "A-p001")
                self.grd_ProteinList.SetCellValue(int_Rows,1,"10")
                for i in range(len(lst_Selection)):
                    self.grd_Plate.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],str(int_Rows+1))
            else:
                self.grd_ProteinList.SetCellValue(int_Rows-1,0,"PROTEIN1A-p001")
                self.grd_ProteinList.SetCellValue(int_Rows-1,1,"10")
                for i in range(len(lst_Selection)):
                    self.grd_Plate.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"1")
            self.UpdateDataframe(None)
        else:
            wx.MessageBox("You have not selected any wells, could not add any protein entries.\nSelect wells and try again.",
                "No wells", wx.OK|wx.ICON_INFORMATION)

    def RemoveProtein(self, event):
        """
        Removes selected protein from protein list and
        clears all corresponding wells on plate layout,
        updates dataframe.
        """
        lst_Selection = self.grd_ProteinList.GetSelectedRows()
        if len(lst_Selection) > 0:
            for i in reversed(range(len(lst_Selection))):
                if self.grd_ProteinList.GetNumberRows() > 1:
                    self.grd_ProteinList.DeleteRows(lst_Selection[i])
                else:
                    self.grd_ProteinList.SetCellValue(0,0,"")
                    self.grd_ProteinList.SetCellValue(0,1,"")
                for j in range(self.grd_Plate.GetNumberRows()):
                    for k in range(self.grd_Plate.GetNumberCols()):
                        if self.grd_Plate.GetCellValue(j,k) == str(lst_Selection[i]+1):
                            self.grd_Plate.SetCellValue(j,k,"")
                            self.grd_Plate.SetBackgroundColour(cs.White)
                        elif self.grd_Plate.GetCellValue(j,k) != "" and int(self.grd_Plate.GetCellValue(j,k)) > lst_Selection[i]+1:
                            self.grd_Plate.SetCellValue(j,k,str(int(self.grd_Plate.GetCellValue(j,k))-1))
            self.UpdateDataframe(None)

    def AddControl(self, event):
        """
        Adds a control to the list and updates dataframe.
        """
        int_Rows = self.grd_ControlList.GetNumberRows()
        if self.grd_ControlList.GetCellValue(0,0) != "" and self.grd_ControlList.GetCellValue(0,0) != "":
            self.grd_ControlList.AppendRows(1,True) # specify number of rows to add, not where to add them
            self.grd_ControlList.SetCellValue(int_Rows,0,"Control " + str(int_Rows+1))
            self.grd_ControlList.SetCellValue(int_Rows,1,"10")
        else:
            self.grd_ControlList.SetCellValue(int_Rows-1,0,"Control 1")
            self.grd_ControlList.SetCellValue(int_Rows-1,1,"10")
        lst_Selection = self.GetSelectionPlate()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                self.grd_Plate.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],str(int_Rows+1))
                self.PaintControl(None, None)
        self.UpdateDataframe(None)

    def RemoveControl(self, event):
        """
        Removes selected control from control list and
        clears all corresponding wells on plate layout,
        updates dataframe.
        """
        lst_Selection = self.grd_ControlList.GetSelectedRows()
        if len(lst_Selection) > 0:
            for i in reversed(range(len(lst_Selection))):
                if self.grd_ControlList.GetNumberRows() > 1:
                    self.grd_ControlList.DeleteRows(lst_Selection[i])
                else:
                    self.grd_ControlList.SetCellValue(0,0,"")
                    self.grd_ControlList.SetCellValue(0,1,"")
                for j in range(self.grd_Plate.GetNumberRows()):
                    for k in range(self.grd_Plate.GetNumberCols()):
                        if self.grd_Plate.GetCellValue(j,k) == str(lst_Selection[i]+1):
                            self.grd_Plate.SetCellValue(j,k,"")
                            self.grd_Plate.SetBackgroundColour(cs.White)
                        elif self.grd_Plate.GetCellValue(j,k) != "" and int(self.grd_Plate.GetCellValue(j,k)) > lst_Selection[i]+1:
                            self.grd_Plate.SetCellValue(j,k,str(int(self.grd_Plate.GetCellValue(j,k))-1))
            self.UpdateDataframe(None)

    def Export(self, event):
        """
        Exports layout dataframe to csv file with the file
        extension ".plf" (plate layout file)
        """
        with wx.FileDialog(self, "Export plate layout", wildcard="Plate layout files (*.plf)|*.plf",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveFilePath = fileDialog.GetPath()
            if str_SaveFilePath.find(".plf") == -1:
                str_SaveFilePath = str_SaveFilePath + ".plf"
            self.dfr_Layout.to_csv(str_SaveFilePath)

    def Import(self, event):
        """
        Imports a plate layout file. Reads contents to dataframe
        and updates all relevent widgets on dialog window.
        """
        with wx.FileDialog(self, "Open plate layout file", wildcard="Plate layout files (*.plf)|*.plf",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_FilePath = fileDialog.GetPath()
            self.dfr_Layout = pd.read_csv(str_FilePath, sep=",", header=0,
                                          index_col=0, engine="python")
            print(self.dfr_Layout.columns)
            # Lists are written as strings of the format "['1','1','1']". These strings need to be converted into lists again:
            for idx_Plate in self.dfr_Layout.index:
                for idx_Column in range(len(self.dfr_Layout.columns)):
                    if type(self.dfr_Layout.iloc[idx_Plate,idx_Column]) == str:
                        self.dfr_Layout.iloc[idx_Plate,idx_Column] = import_string_to_list(self.dfr_Layout.iloc[idx_Plate,idx_Column])
            # Check whether the file is of the correct format (compare list length in dfr_Layout with number of wells on grid)
            if len(self.dfr_Layout.iloc[0,1]) != self.plateformat:
                wx.MessageBox("The layout file you selected does not have the same plate format (number of wells) as the assay you have selected. Select a new file and try again.",
                    "Wrong plate format", wx.OK|wx.ICON_INFORMATION)
                return None # Easier to use this to skip all the rest of the function than to use if then else type wrapper around instructions.
            # Update sample IDs, create empty list if neccessary.
            if self.bol_sampleids == True:
                if not "SampleID" in self.dfr_Layout.columns:
                    lst_SampleIDs = []
                    for i in range(self.dfr_Layout.shape[0]):
                        lst_SampleIDs.append(make_list(len(self.dfr_Layout.iloc[i,1]), ""))
                    self.dfr_Layout = self.dfr_Layout.assign(SampleID = lst_SampleIDs)
            # Refresh display
            self.Refresh(None)

            if self.bol_MultiplePlates == False and len(self.dfr_Layout) > 1:
                wx.MessageBox("You have imported a file with layouts for two plates or more," + "\n" +
                    "but have selected a global layout for all plates." + "\n" + "\n" +
                    "The first layout in the layout file will be applied to all plates.", "Plate layouts reduced", wx.OK|wx.ICON_INFORMATION)
    
    def ApplyAndClose(self, parent, event):
        """
        Apply and close. Writes layout dataframe to parent
        object's layout dataframe and closes the window.

        Arguments:
            parent -> parent object in GUI.
            event -> wx event.

        """
        # Check whether there is a plate without reference wells:
        lst_PlatesWithoutReferences = []
        for idx_Plate in range(len(self.dfr_Layout)):
            bol_Reference = False
            for idx_Well in range(len(self.dfr_Layout.loc[idx_Plate,"WellType"])):
                if self.dfr_Layout.loc[idx_Plate,"WellType"][idx_Well] == "r":
                    bol_Reference = True
                    break
            if bol_Reference == False:
                lst_PlatesWithoutReferences.append(idx_Plate + 1)
        if len(lst_PlatesWithoutReferences) == 0:
            parent.dfr_Layout = self.dfr_Layout
            parent.bol_LayoutDefined = True
            self.EndModal(True)
        else:
            str_PlatesWithoutReferences = ""
            for i in range(len(lst_PlatesWithoutReferences)):
                if i < (len(lst_PlatesWithoutReferences) - 1):
                    str_Comma = ", "
                else:
                    str_Comma = ""
                str_PlatesWithoutReferences = str_PlatesWithoutReferences + str(lst_PlatesWithoutReferences[i]) + str_Comma
            dlg_Exit = wx.MessageDialog(None, "One or more plates have no reference wells:" + "\n" + 
                "Plate(s) " + str_PlatesWithoutReferences + "\n" + "\n" +
                "Data analysis is not possible without refrence wells.\n" + 
                "If you exit now, these plates cannot be analysed later (and might crash the program).\n" + 
                "Do you still want to exit?", "Missing reference wells", wx.YES_NO|wx.ICON_QUESTION)
            id_Exit = dlg_Exit.ShowModal()
            if id_Exit == wx.ID_YES:
                parent.dfr_Layout = self.dfr_Layout
                parent.bol_LayoutDefined = True
                self.EndModal(True)

    def Cancel(self, event):
        """
        Closes window without changing parent object's
        layout dataframe.
        """
        event.Skip()
        self.EndModal(True)

    def ShowMenuPlate(self, event):
        """
        Event handler to show context menu for plate layout
        grid.
        """
        event.Skip()

        row = event.GetRow()
        col = event.GetCol()
        type = self.DetermineWellType(self.grd_Plate.GetCellBackgroundColour(row,col),True)
        if col >= 0 and col < self.grd_Plate.GetNumberCols() and row >= 0 and row < self.grd_Plate.GetNumberRows():
            self.PopupMenu(PlateContextMenu(self, event, type))

    def GetSelectionPlate(self):
        """
        Returns list of coordinates of all selected wells on
        plate layout grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_Plate.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_Plate.GetSelectionBlockBottomRight()
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

    def OnMouseOverPlate(self, event):
        """
        Event handler. Calculates where the mouse is pointing
        and then set the tooltip dynamically.
        """
        # Use CalcUnscrolledPosition() to get the mouse position
        # within the entire grid including what is offscreen
        x, y = self.grd_Plate.CalcUnscrolledPosition(event.GetX(),event.GetY())
        coords = self.grd_Plate.XYToCell(x, y)
        # you only need these if you need the value in the cell
        row = coords[0]
        col = coords[1]
        # Get plate
        idx_Plate = 0
        if (
            col >= 0 and col < self.grd_Plate.GetNumberCols() and row >= 0 and
            row < self.grd_Plate.GetNumberRows()
            ):
            # Get well coordiante:
            str_Well = pf.sortable_well(chr(row+65)+str(col+1),self.plateformat)
            idx_Well = pf.well_to_index(str_Well, self.plateformat)
            str_Tooltip = str_Well + ": "
            # Get well type:
            welltype = self.DetermineWellType(self.grd_Plate.GetCellBackgroundColour(row,col),True)
            if not welltype == u"not assigned":
                # Add welltype to string:
                str_Tooltip += u"\n" + welltype
                if self.bol_proteins == True:
                    protein = self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][idx_Well]
                    if not protein == "":
                        protein = int(protein) -1
                        str_Tooltip += u"\n Protein: " + self.grd_ProteinList.GetCellValue(protein,0)
                # Get control ID:
                if self.bol_controls == True:
                    if welltype == "Control":
                        control = self.dfr_Layout.loc[idx_Plate,"ControlNumerical"][idx_Well]
                        if not control == "":
                            control = int(control) -1
                            str_Tooltip += ": " + self.grd_ControlList.GetCellValue(control,0)
                # Get sample ID:
                if self.bol_sampleids:
                    if welltype == "Sample":
                        sample = self.dfr_Layout.loc[idx_Plate,"SampleID"][idx_Well]
                        str_Tooltip += ": " + sample
            else:
                str_Tooltip += " Blank well"
            event.GetEventObject().SetToolTip(str_Tooltip)
        event.Skip()

    def PaintSample(self, event, rightclick):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates yellow and sets cell type to "Sample".
        """
        lst_Selection = self.GetSelectionPlate()
        if rightclick != None:
            lst_Selection.append(rightclick)
        self.SetWellType(lst_Selection,"yellow")#,"s")
        self.UpdateDataframe(None)

    def PaintControl(self, event, rightclick):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates blue and sets cell type to "Control".
        """
        lst_Selection = self.GetSelectionPlate()
        if rightclick != None:
            lst_Selection.append(rightclick)
        self.SetWellType(lst_Selection,"blue")#,"c")
        self.UpdateDataframe(None)

    def PaintReference(self, event, rightclick):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates red and sets cell type to "Reference".
        """
        lst_Selection = self.GetSelectionPlate()
        if rightclick != None:
            lst_Selection.append(rightclick)
        self.SetWellType(lst_Selection,"red")#,"r")
        self.UpdateDataframe(None)

    def PaintBlank( self, event, rightclick ):
        """
        Event handler.
        Paints selected grid cell(s) and grid cells at rightclick
        coordinates white and sets cell type to "not assigned".
        """
        lst_Selection = self.GetSelectionPlate()
        lst_Selection.append(rightclick)
        self.SetWellType(lst_Selection,"white","")
        self.UpdateDataframe(None)

    def ClearPlate(self, event):
        """
        Clears contents of entire plate layout.
        """
        lst_Selection = []
        for y in range(24):
            for x in range(16):
                lst_Selection.append([x,y])
        self.SetWellType(lst_Selection,"white","")
        self.UpdateDataframe(None)

    def SetWellType(self,selection,colour):
        """
        Changes background colour of selected cells and, if
        required, changes text colour for readability.
        """
        for i in range(len(selection)):
            self.grd_Plate.SetCellBackgroundColour(selection[i][0],selection[i][1],colour)
            if colour == "blue":
                self.grd_Plate.SetCellTextColour(selection[i][0],selection[i][1],"white")
            else:
                self.grd_Plate.SetCellTextColour(selection[i][0],selection[i][1],"black")
                self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],"")
        self.grd_Plate.ForceRefresh()
    
    def WriteProtein(self, event, rightclick, protein):
        """
        writes number corresponding to protein's position
        in list into selected and clicked-on cells.
        """
        selection = self.GetSelectionPlate()
        selection.append(rightclick)
        for i in range(len(selection)):
            self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],protein)
        self.UpdateDataframe(None)

    def WriteControl(self, event, rightclick, control):
        """
        writes number corresponding to control's position
        in list into selected and clicked-on cells.
        """
        selection = self.GetSelectionPlate()
        selection.append(rightclick)
        for i in range(len(selection)):
            self.grd_Plate.SetCellValue(selection[i][0],selection[i][1],control)
            self.grd_Plate.SetCellTextColour(selection[i][0],selection[i][1],"white")
        self.UpdateDataframe(None)

    def DetermineWellType(self, colour, long):
        """
        Takes background colour of cell and returns well type
        in short or long form.

        Arguments:
            colour -> list of RGBA values in integers.
            long -> boolean. Whether to return long or short
                    form well type, e.g. "Sample" or "s".
        """
        #if colour[0] == 255 and colour[1] == 255 and colour[2] == 255:
        #    # 255,255,255 = white
        #    str_WellType = "not assigned"
        if colour[0] == 255 and colour[1] == 255 and colour[2] == 0:
            # 255,255,0 = yellow
            if long == True:
                return "Sample"
            else:
                return "s"
        elif colour[0] == 255 and colour[1] == 0 and colour[2] == 0:
            # 255,0,0 = red
            if long == True:
                return "Reference well"
            else:
                return "r"
        elif colour[0] == 0 and colour[1] == 0 and colour[2] == 255:
            # 0,0,255 = blue
            if long == True:
                return "Control"
            else:
                return "c"
        else:
            if long == True:
                return "not assigned"
            else:
                return "na"

    def DetermineWellColour(self, type):
        """
        Takes the type of a well and returns the
        appropriate background colour for the cell/well.
        """
        if type == "r" or type == "Reference well":
            return "red"
        elif type == "s" or type == "Sample":
            return "yellow"
        elif type == "c" or type == "Control":
            return "blue"
        else:
            return "white"
    
    def UpdateDataframe(self, event):
        """
        Updates the plate dataframe with the current contents
        of the selected plate. Allows for dataframe expansion
        if there was previously only one entry (i.e. the user
        originally selected one layout for all plates but then
        later changed their mind)
        """
        # Get plate index
        if self.bol_MultiplePlates == True:
            idx_Plate = self.lbx_PlateList.GetSelection()
            # If neccessary, expand dataframe to reflect actual number of plates.
            wells = self.parent.plateformat
            if len(self.dfr_Layout) < self.lbx_PlateList.GetCount():
                int_Difference = self.lbx_PlateList.GetCount() - len(self.dfr_Layout)
                dfr_Addition = pd.DataFrame(index=range(int_Difference),
                                            columns=["PlateID",
                                                    "ProteinNumerical",
                                                    "PurificationID",
                                                    "ProteinConcentration",
                                                    "ControlNumerical",
                                                    "ControlID",
                                                    "ControlConcentration"
                                                    "WellType",
                                                    "SampleID"])
                for i in range(len(dfr_Addition)):
                    if self.PlateID == True:
                        dfr_Addition.loc[i,"PlateID"] = self.txt_PlateID.GetValue()
                    else:
                        dfr_Addition.loc[i,"PlateID"] = "X999A"
                    dfr_Addition.loc[i,"ProteinNumerical"] = make_list(wells,"")
                    dfr_Addition.loc[i,"PurificationID"] = make_list(wells,"")
                    dfr_Addition.loc[i,"ProteinConcentration"] = make_list(wells,"")
                    dfr_Addition.loc[i,"ControlNumerical"] = make_list(wells,"")
                    dfr_Addition.loc[i,"ControlID"] = make_list(wells,"")
                    dfr_Addition.loc[i,"ControlConcentration"] = make_list(wells,"")
                    dfr_Addition.loc[i,"WellType"] = make_list(wells,"")
                    dfr_Addition.loc[i,"SampleID"] = make_list(wells,"")
                self.dfr_Layout = self.dfr_Layout.append(dfr_Addition, ignore_index=True)
                wx.MessageBox("You have previously chosen to use one layout for all plates."
                              + "\nThe list of layouts has now been expanded."
                              + "\n\nCheck all plate entries to ensure correct layout.",
                              caption = "Layout expanded",
                              style = wx.OK|wx.ICON_INFORMATION)
        else:
            idx_Plate = 0

        # Update plate ID
        if self.PlateID == True:
            self.dfr_Layout.at[idx_Plate,"PlateID"] = self.txt_PlateID.GetValue()
        else:
            self.dfr_Layout.at[idx_Plate,"PlateID"] = "X999A"

        # Update well types
        lst_WellType = []
        for row in range(self.grd_Plate.GetNumberRows()):
            for col in range(self.grd_Plate.GetNumberCols()):
                lst_WellType.append(self.DetermineWellType(
                    self.grd_Plate.GetCellBackgroundColour(row,col),False))
        self.dfr_Layout.at[idx_Plate,"WellType"] = lst_WellType

        # Update proteins
        if self.bol_proteins == True:
            # Create lists and populate them based on grd_Plate and grd_ProteinList
            lst_PurificationIDs = []
            lst_ProtConcs = []
            lst_ProteinNumericals = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    numerical = self.grd_Plate.GetCellValue(row,col)
                    lst_ProteinNumericals.append(numerical)
                    if numerical != "":
                        lst_PurificationIDs.append(
                            self.grd_ProteinList.GetCellValue(int(numerical)-1,0))
                        lst_ProtConcs.append(
                            self.grd_ProteinList.GetCellValue(int(numerical)-1,1))
                    else:
                        lst_PurificationIDs.append("")
                        lst_ProtConcs.append("")
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[idx_Plate,"ProteinNumerical"] = lst_ProteinNumericals
            self.dfr_Layout.at[idx_Plate,"PurificationID"] = lst_PurificationIDs
            self.dfr_Layout.at[idx_Plate,"ProteinConcentration"] = lst_ProtConcs

        # Update controls
        if self.bol_controls == True:
            # Create lists and populate them based on grd_Plate and grd_ProteinList
            lst_ControlIDs = []
            lst_ControlNumericals = []
            lst_ControlConcs = []
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    numerical = self.grd_Plate.GetCellValue(row,col)
                    lst_ProteinNumericals.append(numerical)
                    if numerical != "":
                        lst_ControlIDs.append(
                            self.grd_ControlList.GetCellValue(int(numerical)-1,0))
                        lst_ControlConcs.append(
                            self.grd_ControlList.GetCellValue(int(numerical)-1,1))
                    else:
                        lst_ControlIDs.append("")
            # Write lists into dfr_Layout:
            self.dfr_Layout.at[idx_Plate,"ControlNumerical"] = lst_ControlNumericals
            self.dfr_Layout.at[idx_Plate,"ControlID"] = lst_ControlIDs
            self.dfr_Layout.at[idx_Plate,"ControlConcentration"] = lst_ControlConcs

        # Write sample IDs to layout
        if self.bol_sampleids == True:
            for lrow in range(self.grd_SampleIDs.GetNumberRows()):
                if self.grd_SampleIDs.GetCellValue(lrow,0) != "":
                    self.dfr_Layout.at[idx_Plate,"SampleID"][pf.well_to_index(self.grd_SampleIDs.GetCellValue(lrow,0), self.plateformat)] = self.grd_SampleIDs.GetCellValue(lrow,1)

    def Refresh(self, event):
        """
        Refreshes the dialog box with the information from dfr_Layout.
        """
        # Take into consideration that the user might have previously selected
        # to use one layout for all, so the dataframe may have a length of 1,
        # as it has been previously been created. Getting the index from the
        # seleted item in lbx_PlateList could create indexing errors.

        # Get plate index
        if self.bol_MultiplePlates == True and len(self.dfr_Layout) > 1:
            idx_Plate = self.lbx_PlateList.GetSelection()
        else:
            idx_Plate = 0

        # Update well colours/types:
        for row in range(self.grd_Plate.GetNumberRows()):
            for col in range(self.grd_Plate.GetNumberCols()):
                idx_Well = col + row*self.grd_Plate.GetNumberCols()
                self.grd_Plate.SetCellBackgroundColour(row,col,self.DetermineWellColour(self.dfr_Layout.loc[idx_Plate,"WellType"][idx_Well]))

        # Extract protein information from dfr_Layout
        if self.bol_proteins == True:
            if len(self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"]) > 0:
                lst_ProteinIndex = []
                lst_PurificationIDs = []
                lst_ProteinConcs = []
                # Find first well with ProteinNumerical on plate representation in dfr_Layout:
                for i in range(len(self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"])):
                    if self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][i] != "":
                        lst_ProteinIndex.append(self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][i]) # Remember, this is the numerical ID
                        lst_PurificationIDs.append(self.dfr_Layout.loc[idx_Plate,"PurificationID"][i])
                        lst_ProteinConcs.append(self.dfr_Layout.loc[idx_Plate,"ProteinConcentration"][i])
                        break
            # Find unique items. Could use a built in function, but I am not trusting it to not f up the order of elements on the three lists.
            # Also, this seems plenty fast enough for the small amount of data it is dealing with.
            idx_List = 0
            for i in range(len(self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"])):
                if self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][i] != "" and self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][i] != lst_ProteinIndex[idx_List]:
                    lst_ProteinIndex.append(self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][i])
                    lst_PurificationIDs.append(self.dfr_Layout.loc[idx_Plate,"PurificationID"][i])
                    lst_ProteinConcs.append(self.dfr_Layout.loc[idx_Plate,"ProteinConcentration"][i])
                    idx_List += 1
            # Write protein number into well
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    idx_Well = col + row*self.grd_Plate.GetNumberCols()
                    self.grd_Plate.SetCellValue(row,col,self.dfr_Layout.loc[idx_Plate,"ProteinNumerical"][idx_Well])
                    self.grd_Plate.SetCellBackgroundColour(row,col,self.DetermineWellColour(self.dfr_Layout.loc[idx_Plate,"WellType"][idx_Well]))
            # Updating ProteinList
            # Before repopulating, first delete all but the first entry and set this one to blank.
            if self.grd_ProteinList.GetNumberRows() > 1:
                self.grd_ProteinList.DeleteRows(1,self.grd_ProteinList.GetNumberRows()-1,True)
            if len(lst_PurificationIDs) > 1:
                self.grd_ProteinList.AppendRows(len(lst_PurificationIDs)-1,True)
                # Go through list, starting from 2nd item (index 1)
                for i in range(len(lst_PurificationIDs)-1):
                    self.grd_ProteinList.SetCellValue(i+1,0,lst_PurificationIDs[i+1])
                    self.grd_ProteinList.SetCellValue(i+1,1,lst_ProteinConcs[i+1])
            else:
                self.grd_ProteinList.SetCellValue(0,0,"")
                self.grd_ProteinList.SetCellValue(0,1,"")
        else:
            # Write nothing in plate wells but leave background colour
            # untouched!
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    idx_Well = col + row*self.grd_Plate.GetNumberCols()
                    self.grd_Plate.SetCellValue(row,col,"")
        
        # Update control list
        if self.bol_controls == True:
            # Before repopulating, first delete all but the first entry and set this one to blank.
            if self.grd_ControlList.GetNumberRows() > 1:
                self.grd_ControlList.DeleteRows(1,self.grd_ControlList.GetNumberRows()-1,True)
            self.grd_ControlList.SetCellValue(0,0,"")
            self.grd_ControlList.SetCellValue(0,1,"")
            # Extract Control information from dfr_Layout
            if len(self.dfr_Layout.loc[idx_Plate,"ControlNumerical"]) > 0:
                lst_ControlIndex = []
                lst_ControlIDs = []
                lst_ControlConcs = []
                for i in range(len(self.dfr_Layout.loc[idx_Plate,"ControlNumerical"])):
                    if self.dfr_Layout.loc[idx_Plate,"ControlNumerical"][i] != "":
                        if not self.dfr_Layout.loc[idx_Plate,"ControlNumerical"][i] in lst_ControlIndex:
                            lst_ControlIndex.append(self.dfr_Layout.loc[idx_Plate,"ControlNumerical"][i]) # Remember, this is the numerical ID
                            lst_ControlIDs.append(self.dfr_Layout.loc[idx_Plate,"ControlID"][i])
                            lst_ControlConcs.append(self.dfr_Layout.loc[idx_Plate,"ControlConcentration"][i])
            # Updating ControlList
            self.grd_ControlList.SetCellValue(0,0,lst_ControlIDs[0])
            self.grd_ControlList.SetCellValue(0,1,lst_ControlConcs[0])
            if len(lst_ControlIDs) > 1:
                self.grd_ControlList.AppendRows(len(lst_ControlIDs)-1,True)
                # Go through list, starting from 2nd item (index 1)
                for i in range(len(lst_ControlIDs)-1):
                    self.grd_ControlList.SetCellValue(i+1,0,lst_ControlIDs[i+1])
                    self.grd_ControlList.SetCellValue(i+1,1,lst_ControlConcs[i+1])

        # Force refresh of plate
        self.grd_Plate.ForceRefresh()

        # Update Plate ID field:
        if self.PlateID == True:
            self.txt_PlateID.SetValue(self.dfr_Layout.at[idx_Plate,"PlateID"])

        # Update sample IDs:
        if self.bol_sampleids == True:
            # Initialise with empty cells:
            for lrow in range(self.grd_SampleIDs.GetNumberRows()):
                self.grd_SampleIDs.SetCellValue(lrow,0,"")
                self.grd_SampleIDs.SetCellValue(lrow,1,"")
            # Update with entries from dataframe:
            if len(self.dfr_Layout.loc[idx_Plate,"SampleID"]) > 0:
                lrow = 0
                for sample in self.dfr_Layout.loc[idx_Plate,"SampleID"]:
                    if not sample == "":
                        self.grd_SampleIDs.SetCellValue(lrow,1,sample)
                        lrow += 1

    def UpdatePlateID(self, event):
        """
        Event handler. Updates plate ID after value in text control
        has been changed.
        """
        if self.bol_MultiplePlates == True:
            self.dfr_Layout.at[self.lbx_PlateList.GetSelection(),"PlateID"] = self.txt_PlateID.GetValue()
        else:
            self.dfr_Layout.at[0,"PlateID"] = self.txt_PlateID.GetValue()

    def ShowContextSamples( self, event ):
        """
        Event handler. Calls context menu for sample ID list.
        """
        event.Skip()
        self.PopupMenu(SampleContextMenu(self, event))

    def GetSelectionSamples(self):
        """
        Returns list of coordinates of all selected cells
        on sample ID grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_SampleIDs.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_SampleIDs.GetSelectionBlockBottomRight()
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
    
    def WellChangedSamples(self, event):
        """
        Event handler. Turns any well coordinate entered in cells
        in column 0 into sortable wells. Sets cell value to empty
        string if cell value is not convertable.
        """
        row = event.GetRow()
        col = event.GetCol()
        try:
            self.grd_SampleIDs.SetCellValue(row,col,pf.sortable_well(str(self.grd_SampleIDs.GetCellValue(row,col)),self.plateformat))
        except:
            self.grd_SampleIDs.SetCellValue(row,col,"")
        self.UpdateDataframe(None)

    def OnKeyPressSamples(self, event):
        """
        Event handler for key press events. Goves sample ID grid
        the behaviour windows users would expect, e.g. ctrl+c,
        ctrl+v, ctr+x etc will work.
        """
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya

        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            self.GridCopy()

        # Ctrl+V
        elif event.ControlDown() and event.GetKeyCode() == 86:
            self.GridPaste(self.grd_SampleIDs.SingleSelection[0],
                           self.grd_SampleIDs.SingleSelection[1])

        # DEL
        elif event.GetKeyCode() == 127:
            self.GridClear()

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            self.grd_SampleIDs.SelectAll()

        # Ctrl+X
        elif event.ControlDown() and event.GetKeyCode() == 88:
            # Call delete method
            self.GridCut()

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and event.GetKeyCode() == 67) \
                or (event.ShiftDown() and event.GetKeyCode() == 322):
            self.GridPaste(self.grd_SampleIDs.SingleSelection[0],
                           self.grd_SampleIDs.SingleSelection[1])

        else:
            event.Skip()

    def GetGridSelectionSamples(self):
        """
        Returns all selected cells in sample IDs grid as list of
        coordinates.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_SampleIDs.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_SampleIDs.GetSelectionBlockBottomRight()
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
        """
        Creates dataframe with contents of selected cells on Sample IDs grid
        and writes it to clipboard.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_SampleIDs.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        """
        Creates dataframe with contents of selected cells on Sample IDs grid,
        writes it to clipboard and then deletes cells' contens on grid.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_SampleIDs.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            self.grd_SampleIDs.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
        dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        """
        Clears contents of selected cells on sample IDs grid.
        """
        lst_Selection = self.GetGridSelectionSamples()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_SampleIDs.SingleSelection[0], self.grd_SampleIDs.SingleSelection[1]]]
        for i in range(len(lst_Selection)):
            if lst_Selection[i][1] > 0:
                self.grd_SampleIDs.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GridPaste(self, row, col):
        """
        Pastes contens of clipboard onto sample IDs grid, starting at
        specified coordinates.
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if pd.isna(dfr_Paste.iloc[i,j]) == False:
                    self.grd_SampleIDs.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))
                else:
                    self.grd_SampleIDs.SetCellValue(i+row,j+col,"")
        self.CheckWellAddressWholeColumn()
        self.UpdateDataframe(None)

    def SingleSelectionSamples(self, event):
        """
        Sets currently clicked on cell to grid's SingleSelection
        property to catch it as part of selected cells.
        """
        self.grd_SampleIDs.SingleSelection = (event.GetRow(), event.GetCol())

    def CheckWellAddressWholeColumn(self):
        """
        Tries to turn contents of each cell in column 0 of sample IDs
        grid into sortable well.
        """
        for row in range(self.grd_SampleIDs.GetNumberRows()):
            try:
                self.grd_SampleIDs.SetCellValue(row,0,pf.sortable_well(self.grd_SampleIDs.GetCellValue(row,0),self.plateformat))
            except:
                None

####  #      ####  ##### #####    #####  ####  #   # ##### ##### #   # #####   #   # ##### #   # #    #
#   # #     #    #   #   #       #      #    # ##  #   #   #      # #    #     ## ## #     ##  # #    #
####  #     ######   #   ###     #      #    # #####   #   ###     #     #     ##### ###   ##### #    #
#     #     #    #   #   #       #      #    # #  ##   #   #      # #    #     # # # #     #  ## #    #
#     ##### #    #   #   #####    #####  ####  #   #   #   ##### #   #   #     #   # ##### #   #  ####

class PlateContextMenu(wx.Menu):
    """
    Context menu to assign well type (sample or reference well; also clear assignment).
    This simply calls the functions of the dialog, which gets passed on as "parent" 

    Methods:
        SetToSamples
        SetToReference
        SetToControl
        SetToBlank
        SetProtein
    
    """
    def __init__(self, parent, rightclick, type):
        super(PlateContextMenu, self).__init__()
        """
        Initialises class attributes.

        Arguments:
            parent -> parent object in UI.
            rightclick -> wx mouse event.
            type -> type of well at clicked coordinates
        """
        lst_ClickedCoordinates = [rightclick.GetRow(), rightclick.GetCol()]
        # Get the current directory and use that for the buttons
        real_path = path.realpath(__file__)
        dir_path = path.dirname(real_path)
        self.str_MenuIconsPath = dir_path + r"\menuicons"

        self.parent = parent
        self.type = type

        self.men_WellType = wx.Menu()
        
        self.mi_Sample = wx.MenuItem(self, wx.ID_ANY, u"Sample", wx.EmptyString,
                                     wx.ITEM_NORMAL )
        self.mi_Sample.SetBitmap(wx.Bitmap(self.str_MenuIconsPath + u"\GridSample.png"))
        self.men_WellType.Append( self.mi_Sample )
        self.Bind(wx.EVT_MENU,
                  lambda event: self.SetToSample(event, lst_ClickedCoordinates),
                  self.mi_Sample)

        self.mi_Reference = wx.MenuItem(self, wx.ID_ANY, u"Reference", wx.EmptyString,
                                        wx.ITEM_NORMAL )
        self.mi_Reference.SetBitmap(wx.Bitmap(self.str_MenuIconsPath + u"\GridReference.png"))
        self.men_WellType.Append( self.mi_Reference )
        self.Bind(wx.EVT_MENU, lambda event: self.SetToReference(event, lst_ClickedCoordinates), self.mi_Reference)

        int_Controls = 0
        for i in range(self.parent.grd_ControlList.GetNumberRows()):
            if self.parent.grd_ControlList.GetCellValue(i,0) != "":
                int_Controls += 1
        if int_Controls > 0:
            self.men_Control = wx.Menu()
            dic_MenuItems = {}
            count = 1
            for i in range(int_Controls):
                if self.parent.grd_ControlList.GetCellValue(i,0) != "":
                    dic_MenuItems["pro_"+str(i+1)]  = wx.MenuItem(self, i+1, str(i+1) + ": " + self.parent.grd_ControlList.GetCellValue(i,0),
                        wx.EmptyString, wx.ITEM_NORMAL)
                    self.Bind(wx.EVT_MENU,
                              lambda event: self.SetToControl(event, lst_ClickedCoordinates),
                              id=count)
                    count += 1
                    self.men_Control.Append(dic_MenuItems["pro_"+str(i+1)])
            self.AppendSubMenu(self.men_Control, u"Control")

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString,
                                    wx.ITEM_NORMAL)
        self.men_WellType.Append(self.mi_Clear)
        self.Bind(wx.EVT_MENU,
                  lambda event: self.SetToBlank(event, lst_ClickedCoordinates),
                  self.mi_Clear)

        self.AppendSubMenu(self.men_WellType, u"Well type")

        int_Proteins = 0
        for prot in range(self.parent.grd_ProteinList.GetNumberRows()):
            if self.parent.grd_ProteinList.GetCellValue(prot,0) != "":
                int_Proteins += 1
        if int_Proteins > 0:
            self.men_Protein = wx.Menu()
            dic_MenuItems = {}
            count = 1
            for i in range(int_Proteins):
                if self.parent.grd_ProteinList.GetCellValue(i,0) != "":
                    dic_MenuItems["pro_"+str(i+1)]  = wx.MenuItem(self,i+1, str(i+1) + ": " + self.parent.grd_ProteinList.GetCellValue(i,0),
                        wx.EmptyString, wx.ITEM_NORMAL)
                    self.Bind(wx.EVT_MENU,
                              lambda event: self.SetProtein(event, lst_ClickedCoordinates),
                              id=count)
                    count += 1
                    self.men_Protein.Append(dic_MenuItems["pro_"+str(i+1)])
            self.AppendSubMenu(self.men_Protein, u"Protein")
    
    def SetToSample(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to sample.
        """
        self.parent.PaintSample(event, rightclick)

    def SetToReference(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to reference.
        """
        self.parent.PaintReference(event, rightclick)

    def SetToControl(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to control.
        """
        self.parent.PaintControl(event, rightclick)
        if self.parent.bol_proteins == False:
            self.parent.WriteControl(event, rightclick, str(event.GetId()))

    def SetToBlank(self, event, rightclick):
        """
        Event handler. Sets rightclicked well to blank/
        not assigned.
        """
        self.parent.PaintBlank(event, rightclick)

    def SetProtein(self, event, rightclick):
        """
        Event handler. Writes portein's numerical identified
        into grid cell.
        """
        self.parent.WriteProtein(event, rightclick, str(event.GetId()))

 ####   ####  #   # ####  #     #####  ####  ####  #   # ##### ##### #   # #####   #   # ##### #   # #   #
#      #    # ## ## #   # #     #     #     #    # ##  #   #   #      # #    #     ## ## #     ##  # #   #
 ####  ###### ##### ####  #     ###   #     #    # #####   #   ###     #     #     ##### ###   ##### #   #
     # #    # # # # #     #     #     #     #    # #  ##   #   #      # #    #     # # # #     #  ## #   #
 ####  #    # #   # #     ##### #####  ####  ####  #   #   #   ##### #   #   #     #   # ##### #   #  ###

class SampleContextMenu(wx.Menu):

    """
    Context menu to cut, copy, paste, clear and fill down from capillaries grid.

    Methods:
        FillDown
        Copy
        Cut
        Paste
        Clear
        GetGridSelection

    """

    def __init__(self, parent, rightclick):
        super(SampleContextMenu, self).__init__()
        """
        Initialises class attributes.

        Arguments:
            parent -> parent object in UI
            rightclick -> wx mouse event.
        """
        real_path = path.realpath(__file__)
        dir_path = path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.grid = rightclick.GetEventObject()

        self.parent = parent

        self.mi_Cut = wx.MenuItem(self, wx.ID_ANY, u"Cut", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Cut.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Cut.ico"))
        self.Append(self.mi_Cut)
        self.Bind(wx.EVT_MENU, lambda event: self.Cut(event,  row, col), self.mi_Cut)

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, lambda event: self.Copy(event,  row, col), self.mi_Copy)

        self.mi_Paste = wx.MenuItem(self, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Paste.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Paste.ico"))
        self.Append(self.mi_Paste)
        self.Bind(wx.EVT_MENU, lambda event: self.Paste(event,  row, col), self.mi_Paste)

        self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Clear.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
        self.Append(self.mi_Clear)
        self.Bind(wx.EVT_MENU, lambda event: self.Clear(event,  row, col), self.mi_Clear)

        self.AppendSeparator()

        self.mi_FillDown = wx.MenuItem(self, wx.ID_ANY, u"Fill down", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_FillDown.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\FillDown.ico"))
        self.Append(self.mi_FillDown)
        self.Bind(wx.EVT_MENU, lambda event: self.FillDown(event, row, col), self.mi_FillDown)

    def FillDown(self, event, row, col):
        """
        Event handler.
        Takes contents of clicked-on cell and fills all cells
        below on same column with same contents.
        """
        filler = self.grid.GetCellValue(row,col)
        for i in range(row,self.grid.GetNumberRows(),1):
            self.grid.SetCellValue(i, col, filler)

    def Copy(self, event, row, col):
        """
        Event handler.
        Takes contents of all selected cells, writes them to clipboard.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        """
        Event handler.
        Takes contents of all selected cells, writes them to clipboard,
        then clears selected cells on grid.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)

    def Paste(self, event, row, col):
        """
        Event handler.
        Writes contents of clipboard to grid, starting
        at clicked-on cell
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if pd.isna(dfr_Paste.iloc[i,j]) == False:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))
                else:
                    self.grid.SetCellValue(i+row,j+col,"")
        self.parent.CheckWellAddressWholeColumn()

    def Clear(self, event, row, col):
        """
        Event handler. Clears contents of all selected cells.
        """
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GetGridSelection(self):
        """
        Returns list of coordinates of all selected cells
        on the grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grid.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grid.GetSelectionBlockBottomRight()
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