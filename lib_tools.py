"""
Contains classes and functions for the Tools tab.

Classes:

    GridContextMenu
    panel_TransferFileMaker
    panel_TransferFileProcessor

Functions:



"""

import lib_platefunctions as pf
from lib_custombuttons import CustomBitmapButton
from lib_tabs import CustomFilePicker
import lib_messageboxes as msg
import lib_colourscheme as cs

import wx
import wx.grid
import wx.xrc
import pandas as pd
import os

######################################################################################################
##                                                                                                  ##
##     #####   ####   ##  ##  ######  ######  ##  ##  ######    ##    ##  ######  ##  ##  ##  ##    ##
##    ##      ##  ##  ### ##    ##    ##      ##  ##    ##      ###  ###  ##      ### ##  ##  ##    ##
##    ##      ##  ##  ######    ##    ####     ####     ##      ########  ####    ######  ##  ##    ##
##    ##      ##  ##  ## ###    ##    ##      ##  ##    ##      ## ## ##  ##      ## ###  ##  ##    ##
##     #####   ####   ##  ##    ##    ######  ##  ##    ##      ##    ##  ######  ##  ##   ####     ##
##                                                                                                  ##
######################################################################################################

class GridContextMenu(wx.Menu):
    """
    Context menu to cut, copy, paste, clear and fill down from plate map grid.
    """
    def __init__(self, parent, grid, rightclick, cut, copy, paste, clear, filldown):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object; parent object
            grid -> wx object; the wx.grid.Grid
            rightclick -> wx event
            cut -> boolean; whether to show the cut option
            copy -> boolean; whether to show the copy option
            paste -> boolean; whether to show the paste option
            clear -> boolean; whether to show the clear option
            filldown -> boolean; whether to show the filldown option
        """
        super(GridContextMenu, self).__init__()
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.parent = parent
        self.grid = grid

        if cut == True:
            self.mi_Cut = wx.MenuItem(self, wx.ID_ANY, u"Cut", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Cut.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Cut.ico"))
            self.Append(self.mi_Cut)
            self.Bind(wx.EVT_MENU, lambda event: self.Cut(event,  row, col), self.mi_Cut)

        if copy == True:
            self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
            self.Append(self.mi_Copy)
            self.Bind(wx.EVT_MENU, lambda event: self.Copy(event,  row, col), self.mi_Copy)

        if paste == True:
            self.mi_Paste = wx.MenuItem(self, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Paste.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Paste.ico"))
            self.Append(self.mi_Paste)
            self.Bind(wx.EVT_MENU, lambda event: self.Paste(event,  row, col), self.mi_Paste)

        if clear == True:
            self.mi_Clear = wx.MenuItem(self, wx.ID_ANY, u"Clear", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Clear.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Clear.ico"))
            self.Append(self.mi_Clear)
            self.Bind(wx.EVT_MENU, lambda event: self.Clear(event,  row, col), self.mi_Clear)

        if filldown == True:
            self.AppendSeparator()
            if col == 0:
                self.mi_FillDownWells = wx.MenuItem(self, wx.ID_ANY, u"Fill down wells", wx.EmptyString, wx.ITEM_NORMAL)
                self.mi_FillDownWells.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\FillDownWells.ico"))
                self.Append(self.mi_FillDownWells)
                self.Bind(wx.EVT_MENU, lambda event: self.FillDownWells(event, row, col), self.mi_FillDownWells)
            else:
                self.mi_FillDown = wx.MenuItem(self, wx.ID_ANY, u"Fill down", wx.EmptyString, wx.ITEM_NORMAL)
                self.mi_FillDown.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\FillDown.ico"))
                self.Append(self.mi_FillDown)
                self.Bind(wx.EVT_MENU, lambda event: self.FillDown(event, row, col), self.mi_FillDown)

    def FillDown(self, event, row, col):
        """
        Fills all cells below clicked on cell with contents of
        clicked on cells.
        """
        filler = self.grid.GetCellValue(row,col)
        if filler == "":
            return None
        for i in range(row,self.grid.GetNumberRows(),1):
            self.grid.SetCellValue(i, col, filler)
        self.parent.UpdateTransferFile(self.parent)

    def FillDownWells(self, event, row, col):
        """
        Fills all cells below clicked on cell with well coordinates
        starting from coordinates in clicked on cell, if cell contains
        a valid well coordinate.
        """
        str_Well = self.grid.GetCellValue(row,col)
        if pf.iswell(str_Well) == False:
            return None
        if str_Well == "":
            return None
        int_PlateFormat = self.parent.dfr_TransferFile.loc[0,"PlateFormat"] #Can use first entry because it must always be the same
        self.grid.SetCellValue(row, col, pf.sortable_well(str_Well, int_PlateFormat))
        well = pf.well_to_index(str_Well, int_PlateFormat) + 2
        for i in range(row+1,self.grid.GetNumberRows(),1):
            if well > int_PlateFormat:
                return None
            self.grid.SetCellValue(i, col, pf.index_to_well(well, int_PlateFormat))
            well += 1
        self.parent.UpdateTransferFile(self.parent)

    def Copy(self, event, row, col):
        """
        Copies content of selected cell(s) to clipboard.
        """
        lst_Selection = self.GetGridSelection(self.grid)
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        """
        Copies content of selected cell(s) to clipboard,
        then clears cells.
        """
        lst_Selection = self.GetGridSelection(self.grid)
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)
            self.parent.UpdateTransferFile(self.parent)

    def Paste(self, event, row, col):
        """
        Writes contents of clipboard into grid starting from clicked on cell
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))
        self.parent.UpdateTransferFile(self.parent)
        #else:
        #    wx.MessageBox("You need to create a plate first before you can paste data.", "No can do", wx.OK|wx.ICON_INFORMATION)

    def Clear(self, event, row, col):
        """
        Clears selected cell(s)
        """
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection(self.grid)
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            self.parent.UpdateTransferFile(self.parent)

    def GetGridSelection(grid):
        """
        Returns list of selected cells in grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = grid.GetSelectionBlockTopLeft()
        lst_BotRightBlock = grid.GetSelectionBlockBottomRight()
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

######################################################################################################################
##                                                                                                                  ##
##    ######  #####    ####   ##  ##   #####  ######  ######  #####     ##    ##   ####   ##  ##  ######  #####     ##
##      ##    ##  ##  ##  ##  ### ##  ##      ##      ##      ##  ##    ###  ###  ##  ##  ##  ##  ##      ##  ##    ##
##      ##    #####   ######  ######   ####   ####    ####    #####     ########  ######  #####   ####    #####     ##
##      ##    ##  ##  ##  ##  ## ###      ##  ##      ##      ##  ##    ## ## ##  ##  ##  ##  ##  ##      ##  ##    ##
##      ##    ##  ##  ##  ##  ##  ##  #####   ##      ######  ##  ##    ##    ##  ##  ##  ##  ##  ######  ##  ##    ##
##                                                                                                                  ##
######################################################################################################################

class panel_TransferFileMaker (wx.Panel):
    """
    Tool to create a Echo liquid handler style transfer file, based
    on wx.Panel.
    """

    def __init__(self, parent, mainframe):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            mainframe -> wx Frame object. The main frame the program is
                         running in.
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.DefaultSize, style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)

        self.dfr_TransferFile = pd.DataFrame(columns=["PlateName","PlateMap","PlateFormat"])
        self.parent = parent
        self.mainframe = mainframe
        self.SetBackgroundColour(cs.BgMediumDark)

        self.szr_TransferFileMaker = wx.BoxSizer(wx.VERTICAL)

        self.szr_ReturnButton = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Return = CustomBitmapButton(self, u"ReturnToToolSelection", 0, (169,25))
        self.btn_Return.Bind(wx.EVT_BUTTON, self.mainframe.CloseActiveTool)
        self.szr_ReturnButton.Add(self.btn_Return, 0, wx.ALL, 5)
        self.szr_TransferFileMaker.Add(self.szr_ReturnButton, 0, wx.ALL, 5)

        self.szr_Panels = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_LeftPanel = wx.BoxSizer(wx.VERTICAL)
        # Plate List ####################################################################
        self.pnl_PlateList = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_PlateList.SetBackgroundColour(cs.BgLight)
        self.szr_PlateList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_AddPlate = wx.StaticText(self.pnl_PlateList, label = u"Add plate to file:")
        self.lbl_AddPlate.Wrap(-1)
        self.szr_PlateList.Add(self.lbl_AddPlate, 0, wx.ALL, 5)
        self.szr_AddPlate = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_AddPlate = wx.TextCtrl(self.pnl_PlateList, value = wx.EmptyString,
                                        size = wx.Size(193,25),
                                        style = wx.TE_PROCESS_ENTER)
        self.szr_AddPlate.Add(self.txt_AddPlate, 0, wx.ALL, 0)
        self.szr_AddPlate.Add((3,25), 0, wx.ALL, 0)
        lst_PlateFormat = [u"384", u"1536", u"96"]
        self.cho_PlateFormat = wx.Choice(self.pnl_PlateList, size = wx.Size(50,25),
                                         choices = lst_PlateFormat)
        self.cho_PlateFormat.SetSelection(0)
        self.szr_AddPlate.Add(self.cho_PlateFormat, 1, wx.ALL, 0)
        self.szr_AddPlate.Add((3,25), 0, wx.ALL, 0)
        self.btn_AddPlate = CustomBitmapButton(self.pnl_PlateList, u"Plus", 0, (25,25))
        self.szr_AddPlate.Add(self.btn_AddPlate, 0, wx.ALL, 0)
        self.szr_PlateList.Add(self.szr_AddPlate, 0, wx.ALL, 5)
        self.lbl_PlatesInFile = wx.StaticText(self.pnl_PlateList, 
                                              label = u"Plates currently in file:")
        self.lbl_PlatesInFile.Wrap(-1)
        self.szr_PlateList.Add(self.lbl_PlatesInFile, 0, wx.ALL, 5)
        self.lbc_Plates = wx.ListCtrl(self.pnl_PlateList, size = wx.Size(275,-1),
                                      style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Plates.InsertColumn(0, "#")
        self.lbc_Plates.SetColumnWidth(0,30)
        self.lbc_Plates.InsertColumn(1,"Plate Name")
        self.lbc_Plates.SetColumnWidth(1, 175)
        self.lbc_Plates.InsertColumn(2,"Wells")
        self.lbc_Plates.SetColumnWidth(2, 50)
        self.szr_PlateList.Add(self.lbc_Plates, 0, wx.ALL, 5)
        self.szr_RemoveButton = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_RemoveButton.Add((0, 0), 1, wx.EXPAND, 5)
        self.btn_Remove = CustomBitmapButton(self.pnl_PlateList, u"DeleteSelectedPlates", 0, (167,25))
        self.szr_RemoveButton.Add(self.btn_Remove, 0, wx.ALL, 5)
        self.szr_PlateList.Add(self.szr_RemoveButton, 1, wx.EXPAND, 5)
        self.pnl_PlateList.SetSizer(self.szr_PlateList)
        self.pnl_PlateList.Layout()
        self.szr_PlateList.Fit(self.pnl_PlateList)
        self.szr_LeftPanel.Add(self.pnl_PlateList, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_Panels.Add(self.szr_LeftPanel, 0, wx.EXPAND, 5)
        #################################################################################

        # Plate map #####################################################################
        self.pnl_PlateMap = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_PlateMap.SetBackgroundColour(cs.BgLight)
        self.szr_PlateMap = wx.BoxSizer(wx.VERTICAL)
        self.szr_PlateTitle = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PlateName = wx.StaticText(self.pnl_PlateMap,
                                           label = u"Plate: [No plates in list]",
                                           size = wx.Size(341,-1))
        self.lbl_PlateName.Wrap(-1)
        self.szr_PlateTitle.Add(self.lbl_PlateName, 0, wx.ALL, 5)
        self.btn_Clear = CustomBitmapButton(self.pnl_PlateMap, u"ClearPlate", 0, (94,25))
        self.szr_PlateTitle.Add(self.btn_Clear, 0, wx.ALL, 5)
        self.szr_PlateMap.Add(self.szr_PlateTitle, 0, wx.ALL, 0)
        # Grid ##########################################################################
        self.grd_PlateMap = wx.grid.Grid(self.pnl_PlateMap, size = wx.Size(445,-1))
        self.grd_PlateMap.CreateGrid(384, 5)
        self.grd_PlateMap.EnableEditing(True)
        self.grd_PlateMap.EnableGridLines(True)
        self.grd_PlateMap.EnableDragGridSize(False)
        self.grd_PlateMap.SetMargins(0, 0)
        # Columns
        self.grd_PlateMap.SetColLabelValue(0,"Well")
        self.grd_PlateMap.SetColSize(0, 40)
        self.grd_PlateMap.SetColLabelValue(1,"Sample ID")
        self.grd_PlateMap.SetColSize(1, 100)
        self.grd_PlateMap.SetColLabelValue(2, "Assay\nconcentration\n(" + chr(181) + "M)")
        self.grd_PlateMap.SetColSize(2, 85)
        self.grd_PlateMap.SetColLabelValue(3, "Transfer\nVolume\n(nl)")
        self.grd_PlateMap.SetColSize(3, 65)
        self.grd_PlateMap.SetColLabelValue(4, "Source\nconcentration\n(mM)")
        self.grd_PlateMap.SetColSize(4, 95)
        self.grd_PlateMap.EnableDragColMove(False)
        self.grd_PlateMap.EnableDragColSize(True)
        self.grd_PlateMap.SetColLabelSize(50)
        self.grd_PlateMap.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        #for i in range(384):
        #    self.grd_PlateMap.SetRowLabelValue(i, pf.index_to_well(i+1,384))
        self.grd_PlateMap.EnableDragRowSize(False)
        self.grd_PlateMap.SetRowLabelSize(40)
        self.grd_PlateMap.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_PlateMap.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.szr_PlateMap.Add(self.grd_PlateMap, 0, wx.ALL, 5)
        self.pnl_PlateMap.SetSizer(self.szr_PlateMap)
        self.pnl_PlateMap.Layout()
        self.szr_PlateMap.Fit(self.pnl_PlateMap)
        self.szr_Panels.Add(self.pnl_PlateMap, 0, wx.EXPAND |wx.ALL, 5)
        #################################################################################

        # Text Panel ####################################################################
        self.pnl_Infobox = wx.Panel(self, size = wx.Size(260,-1),
                                    style = wx.TAB_TRAVERSAL)
        self.pnl_Infobox.SetForegroundColour(cs.White)
        self.szr_Infobox = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Infobox1 = wx.StaticText(self.pnl_Infobox, 
                                          label = u"Create an Echo transfer file for " 
                                          + "analysing experimental data where samples "
                                          + "were not dispensed with an Echo acoustic "
                                          + "dispenser.")
        self.lbl_Infobox1.Wrap(250)
        self.szr_Infobox.Add(self.lbl_Infobox1, 0, wx.ALL, 5)
        self.lbl_Infobox2 = wx.StaticText(self.pnl_Infobox,
                                          label = u"Simply add the required number of "
                                          + "plates to the far left, then fill out each "
                                          + "plate's details in the middle panel.")
        self.lbl_Infobox2.Wrap(250)
        self.szr_Infobox.Add(self.lbl_Infobox2, 0, wx.ALL, 5)
        self.lbl_Infobox3 = wx.StaticText(self.pnl_Infobox,
                                          label = u"Once you are done, export the "
                                          + "transfer data as a .csv file.")
        self.lbl_Infobox3.Wrap(250)
        self.szr_Infobox.Add(self.lbl_Infobox3, 0, wx.ALL, 5)
        self.btn_Export = CustomBitmapButton(self.pnl_Infobox, u"ExportToFile", 0, (104,25))
        self.szr_Infobox.Add(self.btn_Export, 0, wx.ALL, 5)
        self.pnl_Infobox.SetSizer(self.szr_Infobox)
        self.pnl_Infobox.Layout()
        self.szr_Infobox.Fit(self.pnl_Infobox)
        self.szr_Panels.Add(self.pnl_Infobox, 0, wx.ALL, 5)

        self.szr_TransferFileMaker.Add(self.szr_Panels, 0, wx.ALL, 5)

        self.SetSizer(self.szr_TransferFileMaker)
        self.szr_TransferFileMaker.Fit(self)
        self.Layout()

        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #  
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ####################################################

        self.txt_AddPlate.Bind(wx.EVT_TEXT_ENTER, self.AddPlate)
        self.btn_AddPlate.Bind(wx.EVT_BUTTON, self.AddPlate)
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowPlateMap)
        self.btn_Remove.Bind(wx.EVT_BUTTON, self.RemovePlate)
        self.btn_Export.Bind(wx.EVT_BUTTON, self.ToCsv)

        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenGridContextMenu)
        self.grd_PlateMap.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.SingleSelection)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.UpdatePlate)

        self.btn_Clear.Bind(wx.EVT_BUTTON, self.ClearGrid)


    def __del__(self):
        pass

    def AddPlate(self, event):
        """
        Event handler. Adds a plate entry to the listctrl lbc_Plates,
        creates a dataframe dfr_CurrentPlate
        and extens the dataframe dfr_TransferFile
        """
        if self.txt_AddPlate.GetValue() != "":
            int_PlateFormat = int(self.cho_PlateFormat.GetString(self.cho_PlateFormat.GetSelection()))
            # Ensure we're not mixing plate formats!
            if len(self.dfr_TransferFile) > 0:
                if int_PlateFormat != self.dfr_TransferFile.loc[0,"PlateFormat"]:
                    msg.PlateFormatsDoNotMatch(None)
                    return None
            # Check size of grid
            if self.grd_PlateMap.GetNumberRows() != int_PlateFormat:
                if msg.QueryMismatch("plate formats", "plate map") == False:
                    return None
                if self.grd_PlateMap.GetNumberRows() > int_PlateFormat:
                    #print(self.grd_PlateMap.GetNumberRows())
                    self.grd_PlateMap.DeleteRows(int_PlateFormat, self.grd_PlateMap.GetNumberRows()-int_PlateFormat)
                elif self.grd_PlateMap.GetNumberRows() < int_PlateFormat:
                    self.grd_PlateMap.AppendRows(int_PlateFormat-self.grd_PlateMap.GetNumberRows())
            self.grd_PlateMap.ClearGrid()
            # Add plate to list
            self.lbc_Plates.InsertItem(self.lbc_Plates.GetItemCount(),str(self.lbc_Plates.GetItemCount()+1))
            self.lbc_Plates.SetItem(self.lbc_Plates.GetItemCount()-1,1,self.txt_AddPlate.GetValue())
            self.lbc_Plates.SetItem(self.lbc_Plates.GetItemCount()-1,2,str(int_PlateFormat))
            # Create dataframe
            dfr_CurrentPlate = pd.DataFrame(columns=["Well","SampleID","Concentration",
                                                     "TransferVolume","SourceConcentration"],
                                                     index=range(int_PlateFormat))
            for row in range(self.grd_PlateMap.GetNumberRows()):
                for col in range(self.grd_PlateMap.GetNumberCols()):
                    dfr_CurrentPlate.iloc[row,col] = self.grd_PlateMap.GetCellValue(row,col)
            self.dfr_TransferFile = self.dfr_TransferFile.append({"PlateName":self.txt_AddPlate.GetValue(),"PlateMap":dfr_CurrentPlate,
                "PlateFormat":int_PlateFormat}, ignore_index=True)
            self.lbc_Plates.Select(self.lbc_Plates.GetItemCount()-1)
            self.txt_AddPlate.SetValue("")

    def UpdatePlate(self, event):
        """
        Updates dataframe dfr_TransferFile at position of selected
        plate with contents of grid.
        """
        if self.lbc_Plates.GetItemCount() != 0 :
            self.dfr_TransferFile.iloc[self.lbc_Plates.GetFirstSelected(),1].iloc[event.GetRow(),
                event.GetCol()] = self.grd_PlateMap.GetCellValue(event.GetRow(),
                event.GetCol())
        else:
            wx.MessageBox("You have not created any plates, yet. "
                          + "Add a new plate on the left and then try again.",
                          caption = "No Plates, yet",
                          style = wx.OK|wx.ICON_INFORMATION)
            self.grd_PlateMap.SetCellValue(event.GetRow(), event.GetCol(),"")

    def RemovePlate(self, event):
        """
        Removes a plate from lbc_Plates, dfr_TransferFile.
        """
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        self.lbc_Plates.DeleteItem(idx_Plate)
        self.dfr_TransferFile = self.dfr_TransferFile.drop(index=idx_Plate).reset_index(drop=True)
        if self.lbc_Plates.GetItemCount() == 1:
            self.lbc_Plates.Select(0)
        elif self.lbc_Plates.GetItemCount() > 1:
            self.lbc_Plates.Select(idx_Plate)
        elif self.lbc_Plates.GetItemCount() == 0:
            self.grd_PlateMap.ClearGrid()
            self.lbl_PlateName.SetLabel("Plate: [No plates in list]")
        for i in range(self.lbc_Plates.GetItemCount()):
            self.lbc_Plates.SetItem(i,0,str(i+1))

    def ShowPlateMap(self, event):
        """
        Displays contents of selected plate on grid.
        """
        self.grd_PlateMap.ClearGrid()
        self.lbl_PlateName.SetLabel("Plate: "
                                    + self.lbc_Plates.GetItemText(self.lbc_Plates.GetFirstSelected(),1))
        for row in range(self.grd_PlateMap.GetNumberRows()):
            for col in range(self.grd_PlateMap.GetNumberCols()):
                self.grd_PlateMap.SetCellValue(row,col,
                                               self.dfr_TransferFile.iloc[self.lbc_Plates.GetFirstSelected(),1].iloc[row,col])

    def ToCsv(self, event):
        """
        Produces a Echo style transfer report from the dataframe
        dfr_TransferFile and saves it as a csv file.
        """
        lst_TFHeaders = ["Source Plate Name","Source Plate Barcode","Source Plate Type",
                         "Source Well","Source Concentration","Source Concentration Units",
                         "Destination Plate Name","Destination Plate Barcode","Destination Plate Type",
                         "Destination Well","Destination Concentration",
                         "Destination Concentration Units","Sample ID","Sample Name",
                         "Transfer Volume","Actual Volume","Current Fluid Volume","Fluid Composition",
                         "Fluid Units","Fluid Type","Transfer Status"]

        # Create a list of the lengths of the actual plates
        # (i.e. the actual entries in the dataframe within the dataframe)
        lst_PlateLengths = []
        for i in range(len(self.dfr_TransferFile)):
            k = 0
            for j in range(len(self.dfr_TransferFile.iloc[i,1])):
                if type(self.dfr_TransferFile.iloc[i,1].iloc[j,0]) == str:
                    if len(self.dfr_TransferFile.iloc[i,1].iloc[j,0]) > 0:
                        k += 1
            lst_PlateLengths.append(k)

        # Make dataframe for output to csv file
        int_Length = 4
        for i in range(len(lst_PlateLengths)):
            int_Length += lst_PlateLengths[i]
        dfr_Output = pd.DataFrame(columns=lst_TFHeaders,index=range(int_Length))
        dfr_Output.iloc[0,0] = "Run ID"
        dfr_Output.iloc[0,1] = "1234"
        dfr_Output.iloc[2,0] = "[DETAILS]"
        for i in range(len(lst_TFHeaders)):
            dfr_Output.iloc[3,i] = lst_TFHeaders[i]
        idx_Entries = 4
        for plate in range(len(self.dfr_TransferFile)):
            for well in range(len(self.dfr_TransferFile.iloc[plate,1])):
                if len(self.dfr_TransferFile.iloc[plate,1].iloc[well,0]) > 0:
                    dfr_Output.loc[idx_Entries,"Source Plate Name"] = "SourcePlate["+str(plate+1)+"]"
                    dfr_Output.loc[idx_Entries,"Destination Plate Name"] = self.dfr_TransferFile.loc[plate,"PlateName"]
                    dfr_Output.loc[idx_Entries,"Source Concentration"] = self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"SourceConcentration"]
                    dfr_Output.loc[idx_Entries,"Destination Plate Type"] = "384Wells" # DestinationPlateType
                    dfr_Output.loc[idx_Entries,"Destination Well"] = self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"Well"]
                    dfr_Output.loc[idx_Entries,"Destination Concentration"] = self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"Concentration"]
                    dfr_Output.loc[idx_Entries,"Sample ID"] = self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"SampleID"]
                    dfr_Output.loc[idx_Entries,"Sample Name"] = self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"SampleID"]
                    dfr_Output.loc[idx_Entries,"Transfer Volume"] =  self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"TransferVolume"]
                    dfr_Output.loc[idx_Entries,"Actual Volume"] =  self.dfr_TransferFile.loc[plate,"PlateMap"].loc[well,"TransferVolume"]

                    idx_Entries += 1

        # save it to csv:
        with wx.FileDialog(self, "Save Transfer file",
                           wildcard="CSV (comma delimited) (*.csv)|*.csv",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return     # the user changed their mind

                str_TransferFilePath = fileDialog.GetPath()
                dfr_Output.to_csv(str_TransferFilePath, index=False, header=False)

    def UpdateTransferFile(self, gridlocation):
        # Has the grid location/owner of the grid as argument so that it
        # can be used from elsewhere. Otherwise "self" would be the self
        # from where the function as called.
        int_GridColumns = gridlocation.grd_PlateMap.GetNumberCols()
        int_GridRows = gridlocation.grd_PlateMap.GetNumberRows()
        for row in range(int_GridRows):
            for col in range(int_GridColumns):
                gridlocation.dfr_TransferFile.iloc[gridlocation.lbc_Plates.GetFirstSelected(),1].iloc[row,col] = gridlocation.grd_PlateMap.GetCellValue(row,col)

    def ClearGrid(self, event):
        """
        Event handler. Clears the entire grid.
        """
        self.grd_PlateMap.ClearGrid()
        self.UpdateTransferFile(self)

    def OpenGridContextMenu(self, event):
        """
        Event handler. Opens context menu.
        """
        self.PopupMenu(GridContextMenu(self, grid = self.grd_PlateMap,
                                       rightclick = event,
                                       cut = True,
                                       copy = True,
                                       paste = True,
                                       clear = True,
                                       filldown = True))

    def OnKeyPress(self, event):
        """
        Event handler. Calls functions based on pressed keys to
        enable copying, pasting, cutting, deleting as user would
        be accustomed to from other Windows applications.
        """
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
            if self.lbc_Plates.GetItemCount() > 0:
                self.GridPaste(self.grd_PlateMap.SingleSelection[0],
                               self.grd_PlateMap.SingleSelection[1])
            else:
                wx.MessageBox("You need to create a plate first before you can paste data.",
                              caption = "No can do",
                              style = wx.OK|wx.ICON_INFORMATION)

        # DEL
        elif event.GetKeyCode() == 127:
            self.GridClear()

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            self.grd_PlateMap.SelectAll()

        # Ctrl+X
        elif event.ControlDown() and event.GetKeyCode() == 88:
            # Call delete method
            self.GridCut()

        # Ctrl+V or Shift + Insert
        elif (event.ControlDown() and event.GetKeyCode() == 67) \
                or (event.ShiftDown() and event.GetKeyCode() == 322):
            if self.lbc_Plates.GetItemCount() > 0:
                self.GridPaste(self.grd_PlateMap.SingleSelection[0],
                               self.grd_PlateMap.SingleSelection[1])
            else:
                wx.MessageBox("You need to create a plate first before you can paste data.",
                              caption = "No can do",
                              style = wx.OK|wx.ICON_INFORMATION)

        else:
            event.Skip()

    def GetGridSelection(self):
        """
        Returns list of all selected cells.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_PlateMap.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_PlateMap.GetSelectionBlockBottomRight()
        lst_Selection = []
        for i in range(len(lst_TopLeftBlock)):
            # Nuber of columns (add 1 because if just one cell/column is selected,
            # subtracting the coordinates will yield 0)
            int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1
            # Nuber of rows (add 1 because if just one cell/row is selected,
            # subtracting the coordinates will yield 0)
            int_Rows = lst_BotRightBlock[i][0] - lst_TopLeftBlock[i][0] + 1
            # Get all cells:
            for x in range(int_Columns):
                for y in range(int_Rows):
                    new = [lst_TopLeftBlock[i][0]+y,lst_TopLeftBlock[i][1]+x]
                    if lst_Selection.count(new) == 0:
                        lst_Selection.append(new)
        return lst_Selection

    def GridCopy(self):
        """
        Copies contents of selected cell(s) to clipboard
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_PlateMap.SingleSelection[0],
                              self.grd_PlateMap.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_PlateMap.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        """
        Copies contents of selected cell(s) to clipboard, then
        clears them.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_PlateMap.SingleSelection[0],
                              self.grd_PlateMap.SingleSelection[1]]]
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_PlateMap.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grd_PlateMap.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        """
        Clears contents of selected cells.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_PlateMap.SingleSelection[0],
                              self.grd_PlateMap.SingleSelection[1]]]
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grd_PlateMap.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GridPaste(self, cell_row, cell_col):
        """
        Paste contents of clipboard starting at selected cell(s)
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for row in range(int_Rows):
            for col in range(int_Columns):
                if col <= self.grd_PlateMap.GetNumberCols():
                    self.grd_PlateMap.SetCellValue(row+cell_row,col+cell_col,
                                                   str(dfr_Paste.iloc[row,col]))
        self.UpdateTransferFile(self)

    def SingleSelection(self, event):
        """
        Sets the custom .SingleSelection property of the grid
        to the clicked on cell's coordinates.
        """
        self.grd_PlateMap.SingleSelection = (event.GetRow(), event.GetCol())


############################################################################################################################################
##                                                                                                                                        ##
##    #####   #####    ####    #####  ######   #####   #####    ######  #####    ####   ##  ##   #####  ######  ######  #####    #####    ##
##    ##  ##  ##  ##  ##  ##  ##      ##      ##      ##          ##    ##  ##  ##  ##  ### ##  ##      ##      ##      ##  ##  ##        ##
##    #####   #####   ##  ##  ##      ####     ####    ####       ##    #####   ######  ######   ####   ####    ####    #####    ####     ##
##    ##      ##  ##  ##  ##  ##      ##          ##      ##      ##    ##  ##  ##  ##  ## ###      ##  ##      ##      ##  ##      ##    ##
##    ##      ##  ##   ####    #####  ######  #####   #####       ##    ##  ##  ##  ##  ##  ##  #####   ##      ######  ##  ##  #####     ##
##                                                                                                                                        ##
############################################################################################################################################

class panel_TransferFileProcessor (wx.Panel):
    """
    Tool to extract columns and their values from Labcyte Echo style
    liquid handler transfer reports.
    """

    def __init__(self, parent, mainframe):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> wx object. Parent object of this panel.
            mainframe -> wx Frame object. The main frame the program is
                         running in.
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.DefaultSize, style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)

        self.parent = parent
        self.mainframe = mainframe
        self.SetBackgroundColour(cs.BgMediumDark)

        self.szr_TransferFileProcessor = wx.BoxSizer(wx.VERTICAL)

        self.szr_ReturnButton = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Return = CustomBitmapButton(self, u"ReturnToToolSelection", 0, (169,25))
        self.btn_Return.Bind(wx.EVT_BUTTON, self.mainframe.CloseActiveTool)
        self.szr_ReturnButton.Add(self.btn_Return, 0, wx.ALL, 5)
        self.szr_TransferFileProcessor.Add(self.szr_ReturnButton, 0, wx.ALL, 5)

        self.szr_Panels = wx.BoxSizer(wx.HORIZONTAL)

        # Right panel: Load transfer file ###############################################
        self.szr_LeftPanel = wx.BoxSizer(wx.VERTICAL)
        self.pnl_TransferFile = wx.Panel(self, size =  wx.Size(300,-1),
                                         style = wx.TAB_TRAVERSAL)
        self.pnl_TransferFile.SetBackgroundColour(cs.BgLight)
        self.szr_TransferFile = wx.BoxSizer(wx.VERTICAL)
        self.lbl_TransferFile = wx.StaticText(self.pnl_TransferFile,
                                              label = u"Load an Echo transfer file:",
                                              size = wx.Size(290,22))
        self.lbl_TransferFile.Wrap(-1)
        self.szr_TransferFile.Add(self.lbl_TransferFile, 0, wx.ALL, 5)
        self.fpk_TransferFile = CustomFilePicker(self.pnl_TransferFile,
                                                 windowtitle = u"Select a transfer file",
                                                 wildcard = u"*.csv",
                                                 size = (290,-1))
        self.szr_TransferFile.Add(self.fpk_TransferFile, 0, wx.ALL, 5)
        self.pnl_TransferFile.SetSizer(self.szr_TransferFile)
        self.pnl_TransferFile.Layout()
        self.szr_TransferFile.Fit(self.pnl_TransferFile)
        self.szr_LeftPanel.Add(self.pnl_TransferFile, 0, wx.ALL, 5)
        
        self.pnl_Plates = wx.Panel(self, size = wx.Size(300,-1),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Plates.SetBackgroundColour(cs.BgLight)
        self.szr_Plates = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Plates = wx.StaticText(self.pnl_Plates,
                                        label = u"Select one or more plates:",
                                        size = wx.Size(290,22))
        self.szr_Plates.Add(self.lbl_Plates, 0, wx.ALL, 5)
        lst_Plates = []
        self.ckl_Plates = wx.CheckListBox(self.pnl_Plates, size = wx.Size(290,-1),
                                          choices = lst_Plates)
        self.szr_Plates.Add(self.ckl_Plates, 0, wx.ALL, 5)
        self.btn_PlatesSelection = CustomBitmapButton(self.pnl_Plates, u"SelectAll", 0, (80,25))
        self.szr_Plates.Add(self.btn_PlatesSelection, 0, wx.ALL, 5)
        self.pnl_Plates.SetSizer(self.szr_Plates)
        self.pnl_Plates.Layout()
        self.szr_Plates.Fit(self.pnl_Plates)
        self.szr_LeftPanel.Add(self.pnl_Plates, 0, wx.ALL, 5)

        self.pnl_Columns = wx.Panel(self, size = wx.Size(300,-1),
                                    style = wx.TAB_TRAVERSAL)
        self.pnl_Columns.SetBackgroundColour(cs.BgLight)
        self.szr_Columns = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Columns = wx.StaticText(self.pnl_Columns,
                                         label = u"Select columns to extract:")
        self.szr_Columns.Add(self.lbl_Columns, 0, wx.ALL, 5)
        lst_Columns = []
        self.ckl_Columns = wx.CheckListBox(self.pnl_Columns, size = wx.Size(290,-1),
                                           choices = lst_Columns)
        self.szr_Columns.Add(self.ckl_Columns, 0, wx.ALL, 5)
        self.szr_ColumnsButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ColumnsSelection = CustomBitmapButton(self.pnl_Columns, u"SelectAll", 0, (80,25))
        self.szr_ColumnsButtons.Add(self.btn_ColumnsSelection, 0, wx.ALL, 5)
        self.szr_ColumnsButtons.Add((75,25), 0, wx.EXPAND, 5)
        self.btn_Columns = CustomBitmapButton(self.pnl_Columns, u"ExtractColumns", 0, (125,25))
        self.szr_ColumnsButtons.Add(self.btn_Columns, 0, wx.ALL, 5)
        self.szr_Columns.Add(self.szr_ColumnsButtons, 0, wx.ALL, 0)
        self.pnl_Columns.SetSizer(self.szr_Columns)
        self.pnl_Columns.Layout()
        self.szr_Columns.Fit(self.pnl_Columns)
        self.szr_LeftPanel.Add(self.pnl_Columns, 0, wx.ALL, 5)
        self.szr_Panels.Add(self.szr_LeftPanel, 0, wx.ALL, 0)

        # Draw the right panel ##########################################################
        self.szr_RightPanel = wx.BoxSizer(wx.VERTICAL)
        self.pnl_Extracted = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_Extracted.SetBackgroundColour(cs.BgLight)
        self.szr_Extracted = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Extracted = wx.StaticText(self.pnl_Extracted,
                                           label = u"Extracted data:",
                                           size = wx.Size(290,22))
        self.szr_Extracted.Add(self.lbl_Extracted, 0, wx.ALL, 5)
        self.grd_Extracted = wx.grid.Grid(self.pnl_Extracted)
        self.grd_Extracted.CreateGrid(0,0)
        self.grd_Extracted.EnableEditing(True)
        self.grd_Extracted.EnableGridLines(True)
        self.grd_Extracted.EnableDragGridSize(False)
        self.grd_Extracted.SetMargins(0, 0)
        self.grd_Extracted.EnableDragRowSize(False)
        self.grd_Extracted.SetRowLabelSize(40)
        self.grd_Extracted.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_Extracted.Add(self.grd_Extracted, 0, wx.ALL, 5)
        self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ExportButtons.Add((-1,25), 1, wx.EXPAND, 5)
        self.btn_Clipboard = CustomBitmapButton(self.pnl_Extracted, u"Clipboard", 0, (130,25))
        self.szr_ExportButtons.Add(self.btn_Clipboard, 0, wx.ALL, 5)
        self.btn_ExportToFile = CustomBitmapButton(self.pnl_Extracted, u"ExportToFile", 0, (104,25))
        self.szr_ExportButtons.Add(self.btn_ExportToFile, 0, wx.ALL, 5)
        self.szr_Extracted.Add(self.szr_ExportButtons, 1, wx.EXPAND, 5)
        self.pnl_Extracted.SetSizer(self.szr_Extracted)
        self.pnl_Extracted.Layout()
        self.szr_Extracted.Fit(self.pnl_Extracted)
        self.szr_RightPanel.Add(self.pnl_Extracted, 0, wx.ALL, 5)
        self.szr_Panels.Add(self.szr_RightPanel, 0, wx.ALL, 0)

        self.szr_TransferFileProcessor.Add(self.szr_Panels, 0, wx.ALL, 5)

        self.pnl_Plates.Hide()
        self.pnl_Columns.Hide()
        self.pnl_Extracted.Hide()

        self.SetSizer(self.szr_TransferFileProcessor)
        self.szr_TransferFileProcessor.Fit(self)
        self.Layout()

        ###  # #  # ###  # #  #  ###
        #  # # ## # #  # # ## # #  
        ###  # # ## #  # # # ## # ##
        #  # # #  # #  # # #  # #  #
        ###  # #  # ###  # #  #  ##  ####################################################
    
        self.fpk_TransferFile.Bind(self.ParseTransferFile)
        self.btn_Columns.Bind(wx.EVT_BUTTON, self.ExtractColumns)
        self.btn_ColumnsSelection.Bind(wx.EVT_BUTTON, self.ColumnsSelection)
        self.btn_PlatesSelection.Bind(wx.EVT_BUTTON, self.PlatesSelection)
        self.grd_Extracted.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        self.grd_Extracted.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenGridContextMenu)
        self.btn_Clipboard.Bind(wx.EVT_BUTTON, self.Clipboard)
        self.btn_ExportToFile.Bind(wx.EVT_BUTTON, self.Export)

        self.TransferLoaded = False
        self.ColumnsExtracted = False

    def ParseTransferFile(self, str_TransferFile):
        """
        Opens transfer file and extracts destination plate entries
        and column headers and populates checklists with them.
        Also writes entire contents into dataframe self.dfr_TransferFile
        for later use.
        """
        # Open transfer file and find header row
        dfr_Temp = pd.read_csv(str_TransferFile, sep=",", usecols=[0], header=None,
                               index_col=False, engine="python")
        int_HeaderRow = dfr_Temp.index[dfr_Temp[0] == "[DETAILS]"].tolist()
        # Check whether the keyword has been found:
        if not int_HeaderRow:
            return None
        # Adjust header row for offset:
        int_HeaderRow = int_HeaderRow[0] + 1
        # Now open transfer file properly:
        dfr_TransferFile = pd.read_csv(str_TransferFile, sep=",", header=int_HeaderRow,
                                       index_col=False, engine="python")
        # Clean up headers
        dfr_TransferFile.columns = dfr_TransferFile.columns.str.replace(" ", "")
        # Keep only relevant columns -> This will drop the first two columns
        # that hold the appendix data (Instrument name, serial number, etc)
        # Sort by DestinationConcentration -> Ensures that all points will
        # be in the correct order and there are no weird gaps when drawing the fit
        # Drop rows that are empty -> This will be where TransferVolume is "NaN"
        self.dfr_TransferFile = dfr_TransferFile[["SourceConcentration",
            "SourceConcentrationUnits","DestinationPlateName","DestinationPlateBarcode",
            "DestinationPlateType","DestinationWell", "SampleID","SampleName",
            "DestinationConcentration","DestinationConcentrationUnits","TransferVolume",
            "ActualVolume"]].sort_values(["DestinationPlateName","DestinationWell",
            "DestinationConcentration"],ascending=[True,True,False]).dropna(subset=[
            "TransferVolume","SampleID"]).reset_index(drop=True)

        self.dfr_Plates = self.dfr_TransferFile[["DestinationPlateName"]].sort_values(
            by=["DestinationPlateName"]).drop_duplicates(subset=["DestinationPlateName"],
            keep="first", ignore_index=True)
        lst_Plates = self.dfr_Plates.DestinationPlateName.tolist()
        if self.ckl_Plates.GetCount() > 0:
            for i in range(len(self.ckl_Plates.GetCount())):
                self.ckl_Plates.Delete(i)
        self.ckl_Plates.InsertItems(lst_Plates, 0)
        self.pnl_Plates.Show()

        lst_Columns = self.dfr_TransferFile.columns.values.tolist()
        if self.ckl_Columns.GetCount() > 0:
            for i in range(len(self.ckl_Columns.GetCount())):
                self.ckl_Columns.Delete(i)
        self.ckl_Columns.InsertItems(lst_Columns, 0)
        self.TransferLoaded = True
        self.pnl_Columns.Show()
        self.Layout()
    
    def PlatesSelection(self, event):
        """
        Selects/deselects all options in ckl_Plates
        and changes image of button.
        """
        if self.btn_PlatesSelection.Index == 0:
            self.btn_PlatesSelection.Index = 1
            self.btn_PlatesSelection.SetBitmap(wx.Bitmap(self.mainframe.str_ButtonPath
                                               + r"\btn_SelectNone.png"))
            self.btn_PlatesSelection.SetBitmapCurrent(wx.Bitmap(self.mainframe.str_ButtonPath
                                                      + r"\btn_SelectNone_current.png"))
            self.btn_PlatesSelection.SetBitmapDisabled(wx.Bitmap(self.mainframe.str_ButtonPath
                                                       + r"\btn_SelectNone_disabled.png"))
            self.btn_PlatesSelection.SetBitmapFocus(wx.Bitmap(self.mainframe.str_ButtonPath
                                                    + r"\btn_SelectNone_focus.png"))
            self.btn_PlatesSelection.SetBitmapPressed(wx.Bitmap(self.mainframe.str_ButtonPath
                                                      + r"\btn_SelectNone_pressed.png"))
            for row in range(self.ckl_Plates.GetCount()):
                 # Selects/deselects, depending on current state
                self.ckl_Plates.Check(row, True)
        else:
            self.btn_PlatesSelection.Index = 0
            self.btn_PlatesSelection.SetBitmap(wx.Bitmap(self.mainframe.str_ButtonPath
                                                         + r"\btn_SelectAll.png"))
            self.btn_PlatesSelection.SetBitmapCurrent(wx.Bitmap(self.mainframe.str_ButtonPath
                                                                + r"\btn_SelectAll_current.png"))
            self.btn_PlatesSelection.SetBitmapDisabled(wx.Bitmap(self.mainframe.str_ButtonPath
                                                                 + r"\btn_SelectAll_disabled.png"))
            self.btn_PlatesSelection.SetBitmapFocus(wx.Bitmap(self.mainframe.str_ButtonPath
                                                              + r"\btn_SelectAll_focus.png"))
            self.btn_PlatesSelection.SetBitmapPressed(wx.Bitmap(self.mainframe.str_ButtonPath
                                                                + r"\btn_SelectAll_pressed.png"))
            for row in range(self.ckl_Plates.GetCount()):
                self.ckl_Plates.Check(row, False) # Selects/deselects, depending on current state

    def ColumnsSelection(self, event):
        """
        Selects/deselects all options in ckl_Columns
        and changes image of button.
        """
        if self.btn_ColumnsSelection.Index == 0:
            self.btn_ColumnsSelection.Index = 1
            self.btn_ColumnsSelection.SetBitmap(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectNone.png"))
            self.btn_ColumnsSelection.SetBitmapCurrent(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectNone_current.png"))
            self.btn_ColumnsSelection.SetBitmapDisabled(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectNone_disabled.png"))
            self.btn_ColumnsSelection.SetBitmapFocus(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectNone_focus.png"))
            self.btn_ColumnsSelection.SetBitmapPressed(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectNone_pressed.png"))
            for row in range(self.ckl_Columns.GetCount()):
                self.ckl_Columns.Check(row, True) # Selects/deselects, depending on current state
        else:
            self.btn_ColumnsSelection.Index = 0
            self.btn_ColumnsSelection.SetBitmap(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectAll.png"))
            self.btn_ColumnsSelection.SetBitmapCurrent(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectAll_current.png"))
            self.btn_ColumnsSelection.SetBitmapDisabled(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectAll_disabled.png"))
            self.btn_ColumnsSelection.SetBitmapFocus(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectAll_focus.png"))
            self.btn_ColumnsSelection.SetBitmapPressed(wx.Bitmap(self.mainframe.str_ButtonPath + r"\btn_SelectAll_pressed.png"))
            for row in range(self.ckl_Columns.GetCount()):
                self.ckl_Columns.Check(row, False) # Selects/deselects, depending on current state

    def ExtractColumns(self, event):
        """
        Extracts requested columns from dataframe dfr_TransferFile
        and writes them into grid.
        """
        lst_Plates = self.ckl_Plates.GetCheckedStrings()
        dfr_TransferSubset = self.dfr_TransferFile[self.dfr_TransferFile["DestinationPlateName"].isin(lst_Plates)]
        
        lst_Columns = self.ckl_Columns.GetCheckedStrings()
        new_cols = len(lst_Columns)
        old_cols = self.grd_Extracted.GetNumberCols()
        new_rows = dfr_TransferSubset.shape[0]
        old_rows = self.grd_Extracted.GetNumberRows()

        self.grd_Extracted.ClearGrid()
        if old_cols < new_cols:
            self.grd_Extracted.AppendCols(new_cols-old_cols)
        elif old_cols > new_cols:
            self.grd_Extracted.DeleteCols(new_cols-1, old_cols-new_cols)
        if old_rows < new_rows:
            self.grd_Extracted.AppendRows(new_rows-old_rows)
        elif old_rows > new_rows:
            self.grd_Extracted.DeleteRows(new_rows-1, old_rows-new_rows)

        # Columns
        for col in range(len(lst_Columns)):
            self.grd_Extracted.SetColLabelValue(col,lst_Columns[col])

        for row in range(new_rows):
            for col in range(len(lst_Columns)):
                self.grd_Extracted.SetCellValue(row,col,str(dfr_TransferSubset.loc[row,lst_Columns[col]]))
        self.grd_Extracted.AutoSizeColumns()
        int_NewWidth = 30 + 25 #first 30 is width of row labels
        for col in range(self.grd_Extracted.GetNumberCols()):
            int_NewWidth += self.grd_Extracted.GetColSize(col) + 1
        #maximum available width:
        int_MaxWidth = self.Size[0]-315
        if int_NewWidth >= int_MaxWidth:
            int_NewWidth = int_MaxWidth
        # height of simplebook page, minus height of other elements, minus combined borders
        int_NewHeight = self.Size[1] - 145
        self.grd_Extracted.SetMinSize(wx.Size(int_NewWidth,int_NewHeight))
        self.grd_Extracted.Layout()

        self.ColumnsExtracted = True
        self.pnl_Extracted.Show()
        self.Layout()

    def OnKeyPress(self, event):
        """
        Event handler. Handles key presses to give user
        accustomed Windows application experience.
        """
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya
        """
        Handles all key events.
        """
        # Ctrl+C or Ctrl+Insert
        if event.ControlDown() and event.GetKeyCode() in [67, 322]:
            self.GridCopy()

        # Ctrl+A
        elif event.ControlDown() and event.GetKeyCode() == 65:
            self.grd_Extracted.SelectAll()

        else:
            event.Skip()

    def OpenGridContextMenu(self, event):
        """
        Opens context menu for grid
        """
        self.PopupMenu(GridContextMenu(self, grid = self.grd_Extracted,
                                       rightclick = event,
                                       copy = False,
                                       paste = True,
                                       cut = False,
                                       clear = False,
                                       filldown = False))

    def GridCopy(self):
        """
        Copies content(s) of selected cell(s) to clipboard.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Extracted.SingleSelection[0], self.grd_Extracted.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_Extracted.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GetGridSelection(self):
        """
        Returns list of all selected cells.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_Extracted.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_Extracted.GetSelectionBlockBottomRight()
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

    def GridToDataFrame(self):
        """
        Returns dataframe with contents of entire grid.
        """
        try: 
            rows = self.grd_Extracted.GetNumberRows()
            cols = self.grd_Extracted.GetNumberCols()
            lst_Columns = []
            for col in range(cols):
                lst_Columns.append(self.grd_Extracted.GetColLabelValue(col))
            dfr_Grid = pd.DataFrame(index=range(rows),columns=lst_Columns)
            for row in range(rows):
                for col in range(cols):
                    dfr_Grid.iloc[row,col] = self.grd_Extracted.GetCellValue(row,col)
            return dfr_Grid
        except:
            return None

    def Clipboard(self, event):
        """
        Copies contents of entire grid to clipboard.
        """
        dfr_Grid = self.GridToDataFrame()
        if hasattr(dfr_Grid, "shape") == True:
            dfr_Grid.to_clipboard(index=False)
    
    def Export(self, event):
        """
        Exports contents of entire grid to CSV file.
        """
        dfr_Grid = self.GridToDataFrame()
        if hasattr(dfr_Grid, "shape") == True:
            with wx.FileDialog(self, "Export to file",
                           wildcard="CSV (comma delimited) (*.csv)|*.csv",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL:
                    return     # the user changed their mind

                str_TransferFilePath = fileDialog.GetPath()
                dfr_Grid.to_csv(str_TransferFilePath, index=False)
