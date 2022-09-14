"""
Contains standardised pages for assay workflows.

Classes:

    ButtonBar
    AssayStepsNotebook
    AssayDetailsGeneric
    CustomFilePicker
    FileSelection
    Review
    ELNPlots
    ExportToDatabase (CMD specific)
    PlateMapForDatabase (CMD specific)

Functions:

    OnKeyPressGrid
    ProcessData
    SingleSelection
    GetGridSelection

"""

# My own libraries
from xmlrpc.client import boolean
import lib_colourscheme as cs
import lib_transferdragndrop as tdnd
import lib_messageboxes as msg
import lib_datafunctions as df
from lib_resultreadouts import get_bmg_list_namesonly
import lib_customplots as cp
from  lib_progressdialog import GenericProgress
import lib_custombuttons as btn
import lib_platefunctions as pf
import lib_tooltip as tt

import wx
import os
import pandas as pd
import math
import threading
import numpy as np
import openpyxl
from openpyxl import load_workbook
from datetime import datetime
from time import perf_counter

####################################################################################
##                                                                                ##
##    #####   ##  ##  ######  ######   ####   ##  ##    #####    ####   #####     ##
##    ##  ##  ##  ##    ##      ##    ##  ##  ### ##    ##  ##  ##  ##  ##  ##    ##
##    #####   ##  ##    ##      ##    ##  ##  ######    #####   ######  #####     ##
##    ##  ##  ##  ##    ##      ##    ##  ##  ## ###    ##  ##  ##  ##  ##  ##    ##
##    #####    ####     ##      ##     ####   ##  ##    #####   ##  ##  ##  ##    ##
##                                                                                ##
####################################################################################

class ButtonBar(wx.Panel):

    """
    Button bar: Save, Save As, Cancel, Analyse Data
    """

    def __init__(self, tabname, id = wx.ID_ANY, pos = wx.DefaultPosition,
                 size = wx.DefaultSize, style = wx.TAB_TRAVERSAL, name = wx.EmptyString):
        """
        Initialises class attributes.
        
        Arguments:
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent = tabname, id = id,
                           pos = pos, size = size, style = style, name = "ButtonBar")

        self.Tabname = tabname
        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)
        self.szr_HeaderProject = wx.BoxSizer(wx.VERTICAL)
        # Banner with title
        self.szr_Banner = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Banner.Add((20, 0), 0, wx.EXPAND, 0)
        self.szr_BannerLabel = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Filename = wx.StaticText(self, label = u"[Filename goes here]")
        self.szr_BannerLabel.Add(self.lbl_Filename, 0, wx.ALL, 0)
        self.szr_Banner.Add(self.szr_BannerLabel, 1, wx.EXPAND, 0)
        self.szr_HeaderProject.Add(self.szr_Banner, 1, wx.EXPAND, 0)
        self.szr_HeaderProject.Add((0,5),0,wx.ALL,0)
        # Menu bar #####################################################################
        # Save + save as
        self.szr_ProjectMenuBar = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_ProjectMenuBar.Add((20, 30), 0, wx.EXPAND, 0)
        self.btn_HeaderSave = btn.CustomBitmapButton(self, "Save", 1, (100,30),
                                                     tooltip="Save the current project")
        self.btn_HeaderSave.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSave, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderSaveAs = btn.CustomBitmapButton(self, "SaveAs", 1, (100,30))
        self.btn_HeaderSaveAs.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderSaveAs, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        # Cancel
        self.sep_LineSeparator_01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition,
                                                  wx.Size(-1,30), wx.LI_VERTICAL)
        self.szr_ProjectMenuBar.Add(self.sep_LineSeparator_01, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderCancel = btn.CustomBitmapButton(self, "Cancel", 1, (100,30),
                                                       tooltip="Cancel the current project")
        self.btn_HeaderCancel.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderCancel, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        # Run analysis
        self.sep_LineSeparator_02 = wx.StaticLine(self, size = wx.Size(-1,30),
                                                  style = wx.LI_VERTICAL)
        self.szr_ProjectMenuBar.Add(self.sep_LineSeparator_02, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_ProjectMenuBar.Add((3,0), 0, wx.ALL, 0)
        self.btn_HeaderAnalyse = btn.CustomBitmapButton(self,
                                                        type = u"AnalyseData",
                                                        index = 1,
                                                        size = (150,30),
                                                        tooltip = u"Analyse the data in the current project")
        self.btn_HeaderAnalyse.Enable(False)
        self.szr_ProjectMenuBar.Add(self.btn_HeaderAnalyse, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_HeaderProject.Add(self.szr_ProjectMenuBar, 0, wx.EXPAND, 0)
        self.szr_HeaderProject.Add((0,15),0,wx.ALL,0)
        self.SetSizer(self.szr_HeaderProject)
        self.Layout()
        self.szr_HeaderProject.Fit(self)
        
        # Connect event handlers
        self.btn_HeaderSave.Bind(wx.EVT_BUTTON, self.Tabname.parent.SaveFile)
        self.btn_HeaderSaveAs.Bind(wx.EVT_BUTTON, self.Tabname.parent.SaveFileAs)
        self.btn_HeaderCancel.Bind(wx.EVT_BUTTON, self.Tabname.parent.Cancel)
        self.btn_HeaderAnalyse.Bind(wx.EVT_BUTTON, self.Tabname.parent.AnalyseData)

    def EnableButtons(self, bol_Enable):
        """
        Enables/Disables the buttons
        """
        self.btn_HeaderSave.Enable(bol_Enable)
        self.btn_HeaderSaveAs.Enable(bol_Enable)
        self.btn_HeaderCancel.Enable(bol_Enable)
        self.btn_HeaderAnalyse.Enable(bol_Enable)


##########################################################################
##                                                                      ##
##    ##  ##   ####   ######  ######  #####    ## #    ####   ##  ##    ##
##    ### ##  ##  ##    ##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##
##    ######  ##  ##    ##    #####   #####   ##  ##  ##  ##  #####     ##
##    ##  ##  ##  ##    ##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##
##    ##  ##   ####     ##    ######  #####    ####    ####   ##  ##    ##
##                                                                      ##
##########################################################################
    
class AssayStepsNotebook(wx.Panel):
    """
    Creates a fancier looking notebook with bitmap buttons for tab buttons
    and a simplebook w/o native tab buttons.
    """
    def __init__(self, parent, size = wx.DefaultSize):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            size -> wx.Size type.
        """
        wx.Panel.__init__ (self, parent = parent, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = size,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.parent = parent # Required. This will be used by the btn.AnalysisTabButton 
                             # instances to call ChangeTab() from the project tab
        self.SetBackgroundColour(cs.BgMediumDark)
        self.SetForegroundColour(cs.White)

        self.lst_ButtonNames = []
        self.lst_ButtonIndices = []
        self.lst_Enabled = []
        self.dic_Buttons = {}

        self.szr_Notebook = wx.BoxSizer(wx.VERTICAL)

        self.pnl_TabButtons = wx.Panel(self, size =  wx.Size(-1,30),
                                       style = wx.TAB_TRAVERSAL)
        self.pnl_TabButtons.SetBackgroundColour(cs.BgMediumDark)
        self.pnl_TabButtons.SetForegroundColour(cs.White)
        self.szr_TabButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_TabButtons.SetSizer(self.szr_TabButtons)
        self.szr_TabButtons.Fit(self)
        self.szr_Notebook.Add(self.pnl_TabButtons, 0, wx.ALL, 0)

        self.sbk_Notebook = wx.Simplebook(self, size = wx.Size(-1,-1))
        self.szr_Notebook.Add(self.sbk_Notebook, 1, wx.EXPAND|wx.ALL, 0)

        self.SetSizer(self.szr_Notebook)
        self.Layout()
        self.szr_Notebook.Fit(self)

    def EnableAll(self, bol_Enabled):
        """
        Enables/Disables all buttons on this button bar based on
        argument.

        Arguments:
            bol_Enabled -> Values is handed to each button's "IsEnabled"
                            function.
        """
        for key in self.dic_Buttons.keys():
            self.dic_Buttons[key].IsEnabled(bol_Enabled)

    def EnablePlateMap(self, bol_PlateMap):
        """
        Enables/Disables "Plate Map" button, if present

        Arguments:
            bol_Enabled -> Values is handed to each button's "IsEnabled"
                            function.

        """
        if "Plate Map" in self.dic_Buttons.keys():
            self.dic_Buttons["Plate Map"].IsEnabled(bol_PlateMap)
    
    def AddPage(self, pnl_Page, str_Name, bol_Enabled = True, bol_Selected = False):
        """
        Adds a new page to the notebook and corresponding button.
        
        Arguments:
            pnl_Page -> the wx.Panel to add as a new page
            str_Name -> string, name of the panel
            bol_Enabled -> boolean, sets the enabled attribute of
                            the page
            bol_Selected -> boolean, selects (or not) the page
        """
        # Add page to notebook:
        self.sbk_Notebook.AddPage(pnl_Page, str_Name, bol_Selected)
        # Add button:
        int_Index = len(self.lst_ButtonIndices)
        self.lst_ButtonNames.append(str_Name)
        self.lst_ButtonIndices.append(int_Index)
        self.lst_Enabled.append(bol_Enabled)
        self.dic_Buttons[str_Name] = btn.AnalysisTabButton(self.pnl_TabButtons, self.parent, str_Name, int_Index)
        self.dic_Buttons[str_Name].IsEnabled(self.lst_Enabled[int_Index])
        self.dic_Buttons[str_Name].Group = self.dic_Buttons
        self.dic_Buttons[str_Name].Notebook = self.sbk_Notebook
        self.szr_TabButtons.Add(self.dic_Buttons[str_Name], 0, wx.ALL, 0)
        self.pnl_TabButtons.Layout()
        self.pnl_TabButtons.Refresh()
        self.szr_TabButtons.Fit(self.pnl_TabButtons)
        self.szr_Notebook.Fit(self)
        self.szr_Notebook.Layout()
        self.Layout()
        self.Refresh()

    def SetSelection(self, int_Index):
        """
        Selects page at specified index and sets corresponding button.s
        current state to True

        Arguments:
            int_Index -> integer
        """
        self.sbk_Notebook.SetSelection(int_Index)
        self.dic_Buttons[self.lst_ButtonNames[int_Index]].IsCurrent(True)
    
    def GetSelection(self):
        """
        Returns index of currently selected page as integer.
        """
        return self.sbk_Notebook.GetSelection()

    def GetPageCount(self):
        """
        Returns page cound ot notebook as integer.
        """
        return self.sbk_Notebook.GetPageCount()

########################################################################################################
##                                                                                                    ##
##     ####    #####   #####   ####   ##  ##    #####   ######  ######   ####   ##  ##       #####    ##
##    ##  ##  ##      ##      ##  ##  ##  ##    ##  ##  ##        ##    ##  ##  ##  ##      ##        ##
##    ######   ####    ####   ######   ####     ##  ##  ####      ##    ######  ##  ##       ####     ##
##    ##  ##      ##      ##  ##  ##    ##      ##  ##  ##        ##    ##  ##  ##  ##          ##    ##
##    ##  ##  #####   #####   ##  ##    ##      #####   ######    ##    ##  ##  ##  ######  #####     ##
##                                                                                                    ##
########################################################################################################

class AssayDetailsGeneric(wx.Panel):
    """
    Generic tab for assay details, class derived from wx.Panel
    """

    def __init__(self, notebook, tabname, assaytypes = [], date = True, ELN = True):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building.In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            assaytypes -> list of assay types (strings) possible within
                          this project. Some assay types might require
                          different operations on the data (e.g normalisation)
            date -> boolean. If True, field to enter date of experiment
                    will be displayed.
            ELN -> boolean. If True, field to enter ELN (Electronic Lab
                   Notebook) page reference will be displayed.
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname
        self.lst_AssayTypes = assaytypes
        self.Date = date
        self.ELN = ELN

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.szr_Assay = wx.BoxSizer(wx.VERTICAL)
        self.szr_Details = wx.BoxSizer(wx.HORIZONTAL)

        if len(self.lst_AssayTypes) > 0:
            # Assay Type
            self.szr_AssayType = wx.BoxSizer(wx.VERTICAL)
            self.pnl_AssayType = wx.Panel(self, size = wx.Size(160,-1),
                                          style = wx.TAB_TRAVERSAL)
            self.pnl_AssayType.SetBackgroundColour(clr_Panels)
            self.szr_AssayList = wx.BoxSizer(wx.VERTICAL)
            self.lbl_AssayType = wx.StaticText(self.pnl_AssayType, label = u"Assay type")
            self.lbl_AssayType.Wrap(-1)
            self.szr_AssayList.Add(self.lbl_AssayType, 0, wx.ALL, 5)
            self.lbx_AssayType = wx.ListBox(self.pnl_AssayType, size = wx.Size(150,-1),
                                            choices = self.lst_AssayTypes)
            self.lbx_AssayType.SetBackgroundColour(clr_TextBoxes)
            self.szr_AssayList.Add(self.lbx_AssayType, 1, wx.ALL, 5)
            self.lbx_AssayType.SetSelection(0)
            self.chk_Activity = wx.CheckBox(self.pnl_AssayType, label = u"Activity Assay")
            self.chk_Activity.Bind(wx.EVT_CHECKBOX, self.ActivityAssay)
            self.szr_AssayList.Add(self.chk_Activity, 0, wx.ALL, 5)
            self.pnl_AssayType.SetSizer(self.szr_AssayList)
            self.pnl_AssayType.Layout()
            self.szr_AssayType.Add(self.pnl_AssayType, 1, wx.ALL, 5)
            self.szr_Details.Add(self.szr_AssayType, 0, wx.EXPAND, 5)
        
        # Protein and Peptide
        self.szr_ProtPep = wx.BoxSizer(wx.VERTICAL)
        #Protein
        self.pnl_Protein = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_Protein.SetBackgroundColour(clr_Panels)
        self.szr_Protein = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Protein = wx.StaticText(self.pnl_Protein, label = u"Protein/Enzyme")
        self.lbl_Protein.Wrap(-1)
        self.szr_Protein.Add(self.lbl_Protein, 0, wx.ALL, 5)
        self.szr_PurificationID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PurificationID = wx.StaticText(self.pnl_Protein, label = u"Purification ID",
                                                size = wx.Size(130,-1), style = 1)
        self.lbl_PurificationID.Wrap(-1)
        self.szr_PurificationID.Add(self.lbl_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_PurificationID = wx.TextCtrl(self.pnl_Protein, value = u"ALBBTA-p001",
                                              size = wx.Size(100,-1), style = 1)
        self.txt_PurificationID.SetMaxSize(wx.Size(-1,-1))
        self.txt_PurificationID.SetBackgroundColour(clr_TextBoxes)
        self.szr_PurificationID.Add(self.txt_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.btn_Lookup_PurificationID = wx.Button(self.pnl_Protein, label = u"?",
                                                   size = wx.Size(23,23),
                                                   style = 1)
        self.btn_Lookup_PurificationID.SetMaxSize(wx.Size(23,23))
        self.szr_PurificationID.Add(self.btn_Lookup_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Protein.Add(self.szr_PurificationID, 1, wx.EXPAND, 5)
        self.szr_ProteinConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_ProtConc = wx.StaticText(self.pnl_Protein, label = u"Protein concentration",
                                          size = wx.Size(180,-1))
        self.lbl_ProtConc.Wrap(-1)
        self.szr_ProteinConc.Add(self.lbl_ProtConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ProteinConc = wx.TextCtrl(self.pnl_Protein, value = u"20", size = wx.Size(50,-1))
        self.txt_ProteinConc.SetMaxSize(wx.Size(50,-1))
        self.txt_ProteinConc.SetBackgroundColour(clr_TextBoxes)
        self.szr_ProteinConc.Add(self.txt_ProteinConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM1 = wx.StaticText(self.pnl_Protein, label = u"nM", size = wx.Size(25,-1))
        self.lbl_nM1.Wrap(-1)
        self.szr_ProteinConc.Add(self.lbl_nM1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Protein.Add(self.szr_ProteinConc, 1, wx.EXPAND, 5)
        self.pnl_Protein.SetSizer(self.szr_Protein)
        self.pnl_Protein.Layout()
        self.szr_Protein.Fit(self.pnl_Protein)
        self.szr_ProtPep.Add(self.pnl_Protein, 1, wx.EXPAND|wx.ALL, 5)
        # Peptide/Substrate 1
        self.pnl_Peptide = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_Peptide.SetBackgroundColour(clr_Panels)
        self.szr_Peptide = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Peptide = wx.StaticText(self.pnl_Peptide, label = u"Peptide")
        self.lbl_Peptide.Wrap(-1)
        self.szr_Peptide.Add(self.lbl_Peptide, 0, wx.ALL, 5)
        self.szr_PeptideID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PeptideID = wx.StaticText(self.pnl_Peptide, label = u"Peptide ID",
                                           size = wx.Size(130,-1))
        self.lbl_PeptideID.Wrap(-1)
        self.szr_PeptideID.Add(self.lbl_PeptideID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_PeptideID = wx.TextCtrl(self.pnl_Peptide, value =  u"EP000001a",
                                         size = wx.Size(100,-1))
        self.txt_PeptideID.SetMaxSize(wx.Size(100,-1))
        self.txt_PeptideID.SetBackgroundColour(clr_TextBoxes)
        self.szr_PeptideID.Add(self.txt_PeptideID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.btn_Lookup_Peptide = wx.Button(self.pnl_Peptide, label = u"?", 
                                            size = wx.Size(25,25))
        self.szr_PeptideID.Add(self.btn_Lookup_Peptide, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Peptide.Add(self.szr_PeptideID, 1, wx.EXPAND, 5)
        self.szr_PeptideConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PeptideConc = wx.StaticText(self.pnl_Peptide, label = u"Peptide concentration",
                                             size = wx.Size(180,-1))
        self.lbl_PeptideConc.Wrap(-1)
        self.szr_PeptideConc.Add(self.lbl_PeptideConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_PeptideConc = wx.TextCtrl(self.pnl_Peptide, value = u"20",
                                           size = wx.Size(50,-1))
        self.txt_PeptideConc.SetMaxSize(wx.Size(50,-1))
        self.txt_PeptideConc.SetBackgroundColour(clr_TextBoxes)
        self.szr_PeptideConc.Add(self.txt_PeptideConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM2 = wx.StaticText(self.pnl_Peptide, label = u"nM",
                                     size = wx.Size(25,-1))
        self.lbl_nM2.Wrap(-1)
        self.szr_PeptideConc.Add(self.lbl_nM2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Peptide.Add(self.szr_PeptideConc, 1, wx.EXPAND, 5)
        self.pnl_Peptide.SetSizer(self.szr_Peptide)
        self.pnl_Peptide.Layout()
        self.szr_Peptide.Fit(self.pnl_Peptide)
        self.szr_ProtPep.Add(self.pnl_Peptide, 1, wx.EXPAND |wx.ALL, 5)
        # Substrate 2
        self.pnl_Substrate2 = wx.Panel(self, style = wx.TAB_TRAVERSAL)
        self.pnl_Substrate2.SetBackgroundColour(clr_Panels)
        self.szr_Substrate2 = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Substrate2 = wx.StaticText(self.pnl_Substrate2, label = u"Substrate 2")
        self.lbl_Substrate2.Wrap(-1)
        self.szr_Substrate2.Add(self.lbl_Substrate2, 0, wx.ALL, 5)
        self.szr_Substrate2ID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Substrate2ID = wx.StaticText(self.pnl_Substrate2, label = u"Substrate 2 ID",
                                              size = wx.Size(130,-1))
        self.lbl_Substrate2ID.Wrap(-1)
        self.szr_Substrate2ID.Add(self.lbl_Substrate2ID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Substrate2ID = wx.TextCtrl(self.pnl_Substrate2, value = u"EP000001a",
                                            size = wx.Size(100,-1))
        self.txt_Substrate2ID.SetMaxSize(wx.Size(100,-1))
        self.txt_Substrate2ID.SetBackgroundColour(clr_TextBoxes)
        self.szr_Substrate2ID.Add(self.txt_Substrate2ID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.btn_Lookup_Substrate2 = wx.Button(self.pnl_Substrate2, label = u"?",
                                               size = wx.Size(25,25))
        self.szr_Substrate2ID.Add(self.btn_Lookup_Substrate2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Substrate2.Add(self.szr_Substrate2ID, 1, wx.EXPAND, 5)
        self.szr_Substrate2Conc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Substrate2Conc = wx.StaticText(self.pnl_Substrate2, 
                                                label = u"Susbstrate 2 concentration",
                                                size = wx.Size(180,-1))
        self.lbl_Substrate2Conc.Wrap(-1)
        self.szr_Substrate2Conc.Add(self.lbl_Substrate2Conc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Substrate2Conc = wx.TextCtrl(self.pnl_Substrate2, value = u"20",
                                              size = wx.Size(50,-1))
        self.txt_Substrate2Conc.SetMaxSize(wx.Size(50,-1))
        self.txt_Substrate2Conc.SetBackgroundColour(clr_TextBoxes)
        self.szr_Substrate2Conc.Add(self.txt_Substrate2Conc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM3 = wx.StaticText(self.pnl_Substrate2, label = u"nM",
                                     size = wx.Size(25,-1))
        self.lbl_nM3.Wrap(-1)
        self.szr_Substrate2Conc.Add(self.lbl_nM3, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Substrate2.Add(self.szr_Substrate2Conc, 1, wx.EXPAND, 5)
        self.pnl_Substrate2.SetSizer(self.szr_Substrate2)
        self.pnl_Substrate2.Layout()
        self.szr_Substrate2.Fit(self.pnl_Substrate2)
        self.szr_ProtPep.Add(self.pnl_Substrate2, 1, wx.EXPAND |wx.ALL, 5)
        self.szr_Details.Add(self.szr_ProtPep, 0, wx.EXPAND, 5)

        # Right panel: ELN Page, Buffer, Solvent
        self.szr_RightPanel = wx.BoxSizer(wx.VERTICAL)
        # Date of experiment
        if self.Date == True:
            self.pnl_Date = wx.Panel(self, size = wx.Size(220,-1),
                                     style = wx.TAB_TRAVERSAL)
            self.pnl_Date.SetBackgroundColour(clr_Panels)
            self.pnl_Date.SetMaxSize(wx.Size(220,-1))
            self.szr_Date = wx.BoxSizer(wx.HORIZONTAL)
            self.lbl_Date = wx.StaticText(self.pnl_Date, label = u"Date of experiment")
            self.lbl_Date.Wrap(-1)
            self.szr_Date.Add(self.lbl_Date, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.DatePicker = wx.adv.DatePickerCtrl(self.pnl_Date,
                                                    style = wx.adv.DP_DEFAULT|wx.adv.DP_DROPDOWN)
            self.DatePicker.SetNullText(u"N/A")
            self.DatePicker.SetBackgroundColour(clr_TextBoxes)
            self.szr_Date.Add(self.DatePicker, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.pnl_Date.SetSizer(self.szr_Date)
            self.pnl_Date.Layout()
            self.szr_Date.Fit(self.pnl_Date)
            self.szr_RightPanel.Add(self.pnl_Date, 0, wx.EXPAND |wx.ALL, 5)
        # ELN
        if self.ELN == True:
            self.pnl_ELN = wx.Panel(self, size = wx.Size(220,-1),
                                    style = wx.TAB_TRAVERSAL)
            self.pnl_ELN.SetBackgroundColour(clr_Panels)
            self.pnl_ELN.SetMaxSize(wx.Size(220,-1))
            self.szr_ELNPage = wx.BoxSizer(wx.HORIZONTAL)
            self.lbl_ELN = wx.StaticText(self.pnl_ELN, label = u"ELN Page")
            self.lbl_ELN.Wrap(-1)
            self.szr_ELNPage.Add(self.lbl_ELN, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.txt_ELN = wx.TextCtrl(self.pnl_ELN, value = u"PAGE21-12345")
            self.txt_ELN.SetBackgroundColour(clr_TextBoxes)
            self.szr_ELNPage.Add(self.txt_ELN, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
            self.pnl_ELN.SetSizer(self.szr_ELNPage)
            self.pnl_ELN.Layout()
            self.szr_ELNPage.Fit(self.pnl_ELN)
            self.szr_RightPanel.Add(self.pnl_ELN, 0, wx.EXPAND |wx.ALL, 5)
        # Buffer
        self.pnl_Buffer = wx.Panel(self, size = wx.Size(220,-1),
                                   style = wx.TAB_TRAVERSAL)
        self.pnl_Buffer.SetBackgroundColour(clr_Panels)
        self.pnl_Buffer.SetMaxSize(wx.Size(220,-1))
        self.szr_Buffer = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Buffer = wx.StaticText(self.pnl_Buffer, label = u"Buffer",
                                        size = wx.Size(50,-1))
        self.lbl_Buffer.Wrap(-1)
        self.szr_Buffer.Add(self.lbl_Buffer, 0, wx.ALL, 5)
        self.txt_Buffer = wx.TextCtrl(self.pnl_Buffer,
                                      value = u"20 mM HEPES. 20 mM NaCl, 0.05% TWEEN-20, 0.05%BSA, pH7.0",
                                      size = wx.Size(210,54),
                                      style = wx.TE_MULTILINE|wx.TE_BESTWRAP)
        self.txt_Buffer.SetMaxSize(wx.Size(200,54))
        self.txt_Buffer.SetBackgroundColour(clr_TextBoxes)
        self.szr_Buffer.Add(self.txt_Buffer, 0, wx.ALL, 5)
        self.pnl_Buffer.SetSizer(self.szr_Buffer)
        self.pnl_Buffer.Layout()
        self.szr_Buffer.Fit(self.pnl_Buffer)
        self.szr_RightPanel.Add(self.pnl_Buffer, 0, wx.ALL, 5)
        # Solvent
        self.pnl_Solvent = wx.Panel(self, size = wx.Size(220,-1),
                                    style = wx.TAB_TRAVERSAL)
        self.pnl_Solvent.SetBackgroundColour(clr_Panels)
        self.pnl_Solvent.SetMaxSize(wx.Size(220,-1))
        self.szr_Solvent = wx.BoxSizer(wx.VERTICAL)
        self.szr_SolventName = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Solvent = wx.StaticText(self.pnl_Solvent, label = u"Compound solvent",
                                         size = wx.Size(115,-1))
        self.lbl_Solvent.Wrap(-1)
        self.szr_SolventName.Add(self.lbl_Solvent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Solvent = wx.TextCtrl(self.pnl_Solvent, value = u"DMSO",
                                       size = wx.Size(85,-1))
        self.txt_Solvent.SetMaxSize(wx.Size(85,-1))
        self.txt_Solvent.SetBackgroundColour(clr_TextBoxes)
        self.szr_SolventName.Add(self.txt_Solvent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Solvent.Add(self.szr_SolventName, 1, wx.EXPAND, 5)
        self.szr_SolventConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_SolvConc = wx.StaticText(self.pnl_Solvent, label = u"Concentration (v/v)",
                                          size = wx.Size(110,-1))
        self.lbl_SolvConc.Wrap(-1)
        self.szr_SolventConc.Add(self.lbl_SolvConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Percent = wx.TextCtrl(self.pnl_Solvent, value = u"0.5",
                                       size =  wx.Size(35,-1))
        self.txt_Percent.SetMaxSize(wx.Size(35,-1))
        self.txt_Percent.SetBackgroundColour(clr_TextBoxes)
        self.szr_SolventConc.Add(self.txt_Percent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Percent = wx.StaticText(self.pnl_Solvent, label = u"%",
                                         size = wx.Size(15,-1))
        self.lbl_Percent.Wrap(-1)
        self.szr_SolventConc.Add(self.lbl_Percent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Solvent.Add(self.szr_SolventConc, 1, wx.EXPAND, 5)
        self.pnl_Solvent.SetSizer(self.szr_Solvent)
        self.pnl_Solvent.Layout()
        self.szr_RightPanel.Add(self.pnl_Solvent, 0, wx.ALL|wx.EXPAND, 5)
        self.szr_Details.Add(self.szr_RightPanel, 0, wx.EXPAND, 5)
        # Finalise
        self.szr_Assay.Add(self.szr_Details, 0, wx.EXPAND, 20)
        self.SetSizer(self.szr_Assay)
        self.Layout()
        self.szr_Assay.Fit(self)

        self.lbl_Substrate2.Enable(False)
        self.lbl_Substrate2ID.Enable(False)
        self.txt_Substrate2ID.Enable(False)
        self.btn_Lookup_Substrate2.Enable(False)
        self.lbl_Substrate2Conc.Enable(False)
        self.txt_Substrate2Conc.Enable(False)
        self.lbl_nM3.Enable(False)

    def ActivityAssay(self, event):
        """
        Makes changes to GUI for activity assays (hides
        additional text fields to enter substrate ID) and
        changes column headers for export table.
        """
        if self.chk_Activity.GetValue() == True:
            self.pnl_Substrate2.Show()
            #self.Layout()
        else:
            self.pnl_Substrate2.Hide()
            #self.Layout()
        self.lbl_Substrate2.Enable(self.chk_Activity.Value)
        self.lbl_Substrate2ID.Enable(self.chk_Activity.Value)
        self.txt_Substrate2ID.Enable(self.chk_Activity.Value)
        self.btn_Lookup_Substrate2.Enable(self.chk_Activity.Value)
        self.lbl_Substrate2Conc.Enable(self.chk_Activity.Value)
        self.txt_Substrate2Conc.Enable(self.chk_Activity.Value)
        self.lbl_nM3.Enable(self.chk_Activity.Value)
        if self.chk_Activity.Value == True:
            self.Tabname.lst_Headers = self.Tabname.lst_Headers_ActAssay
            self.lbl_Peptide.Label = "Substrate 1"
            self.lbl_PeptideID.Label = "Substrate 1 ID" 
            self.lbl_PeptideConc.Label = "Substrate 1 concentration"
        else:
            self.Tabname.lst_Headers = self.Tabname.lst_Headers_ASHTRF
            self.lbl_Peptide.Label = "Peptide"
            self.lbl_PeptideID.Label = "Peptide ID" 
            self.lbl_PeptideConc.Label = "Peptide concentration"

##############################################
##                                          ##
##    ######  ##  ##      #######  #####    ##
##    ##      ##  ##      ##      ##        ##
##    #####   ##  ##      ####     ####     ##
##    ##      ##  ##      ##          ##    ##
##    ##      ##  ######  ######  #####     ##
##                                          ##
##############################################

class CustomFilePicker(wx.Panel):
    """
    File or directory picker. Custom implementation to keep appearance
    consistent with BBQ GUI.
    """
    def __init__(self, parent, windowtitle, wildcard, size):
        """
        Initialises class attributes.
        
        Arguments:
            parent -> parent object for wxPython GUI building.
            windowtitle -> string. Window title for file/dir dialog
            wildcard -> string. Wildcard for file dialog
            size -> tupel of integers. Overal size of widget
        """
        wx.Panel.__init__ (self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition,
                           size = wx.DefaultSize, style = wx.TAB_TRAVERSAL,
                           name = wx.EmptyString)
        self.parent = parent
        self.WindowTitle = windowtitle
        self.wildcard = wildcard
        self.Type = "file"

        self.Function = None

        self.szr_FilePicker = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_FilePicker = wx.TextCtrl(self, value = wx.EmptyString,
                                          size = wx.Size(size[0]-33,-1))
        self.szr_FilePicker.Add(self.txt_FilePicker, 0, wx.ALL, 0)
        self.szr_FilePicker.Add((3,-1),0,wx.EXPAND,0)
        self.btn_FilePicker = btn.CustomBitmapButton(self, "Browse", 1, (30,25))
        self.szr_FilePicker.Add(self.btn_FilePicker, 0, wx.ALL, 0)
        self.SetSizer(self.szr_FilePicker)
        self.szr_FilePicker.Fit(self)
        self.Layout()

        self.btn_FilePicker.Bind(wx.EVT_BUTTON, self.Action)

    def Action(self, event):
        """
        Event handler to pick correct event based on whether files
        or directory are to be opened.
        """
        if self.Type == "file":
            self.PickFile()
        elif self.Type == "directory":
            self.PickDirectory()

    def PickFile(self):
        """
        Open file dialog and write picked path into text field and
        do something with the path if a function is specified.
        """
        with wx.FileDialog(self, self.WindowTitle, wildcard=self.wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            self.txt_FilePicker.SetValue(fileDialog.GetPath())
            if not self.Function == None:
                self.Function(fileDialog.GetPath())

    def PickDirectory(self):
        """
        Open dir dialog and write picked path into text field and
        do something with the path if a function is specified.
        """
        with wx.DirDialog(self, self.WindowTitle,
            style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST) as directoryDialog:

            if directoryDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            self.txt_FilePicker.SetValue(directoryDialog.GetPath())
            if not self.Function == None:
                self.Function(directoryDialog.GetPath())

    def Bind(self, function):
        """
        Assigns function
        """
        self.Function = function

    def SetPath(self, str_Path):
        """
        Set path displayed in text box
        """
        if not type(str_Path) == str:
            str_Path = str(str_Path)
        self.txt_FilePicker.SetValue(str_Path)

class FileSelection(wx.Panel):
    """
    File selection tab. Derived from wx.Panel
    """

    def __init__(self, notebook, tabname, data, normalise, layouts):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            data -> string. Either "directory" or file type in format
                    "*.extension"
            normalise -> boolean. If true, display option to load reference
                         plate to normalise each plate against. Currently
                         not used.
            layouts -> boolean. If true, show option to define individual
                       layouts for each plate.
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.szr_Files = wx.BoxSizer(wx.VERTICAL)

        # 2. File assignment lists
        self.szr_Assignment = wx.FlexGridSizer(2,3,0,0)
        # 2.1 Transfer Files
        self.pnl_Transfer = wx.Panel(self, size = wx.Size(460,-1),
                                     style = wx.TAB_TRAVERSAL)
        self.pnl_Transfer.SetBackgroundColour(clr_Panels)
        self.pnl_Transfer.SetMaxSize(wx.Size(460,-1))
        self.szr_Transfer = wx.BoxSizer(wx.VERTICAL)
        # Show in case of "echo"
        self.pnl_Echo = wx.Panel(self.pnl_Transfer, size = wx.Size(460,-1),
                                 style = wx.TAB_TRAVERSAL)
        self.szr_Echo = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Transfer = wx.StaticText(self.pnl_Echo, label = u"Select a transfer file:",
                                          size = wx.Size(450,20))
        self.lbl_Transfer.Wrap(-1)
        self.szr_Echo.Add(self.lbl_Transfer, 0, wx.ALL, 5)
        self.fpk_Transfer = CustomFilePicker(self.pnl_Echo,
                                             windowtitle = u"Select a transfer file",
                                             wildcard = u"*.csv",
                                             size = (450,-1))
        self.szr_Echo.Add(self.fpk_Transfer, 0, wx.ALL, 5)
        self.fpk_Transfer.Bind(self.ReadTransferFile)
        self.pnl_Echo.SetSizer(self.szr_Echo)
        self.pnl_Echo.Layout()
        self.szr_Echo.Fit(self.pnl_Echo)
        self.szr_Transfer.Add(self.pnl_Echo, 0, wx.ALL, 0)
        # Show in case of "lightcycler" or "well"
        self.pnl_Plates = wx.Panel(self.pnl_Transfer, size = wx.Size(460,70),
                                   style = wx.TAB_TRAVERSAL)
        self.szr_Plates = wx.BoxSizer(wx.VERTICAL)
        # Add Plate
        self.pnl_AddDestination = wx.Panel(self.pnl_Plates, size = wx.Size(450,25),
                                           style = wx.TAB_TRAVERSAL)
        self.szr_AddDestination = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_AddDestination = wx.StaticText(self.pnl_AddDestination,
                                                label = u"Add a plate to analyse:",
                                                size = wx.Size(-1,25))
        self.szr_AddDestination.Add(self.lbl_AddDestination, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_AddDestination.Add((-1,25), 1, wx.EXPAND, 0)
        self.txt_AddDestination = wx.TextCtrl(self.pnl_AddDestination, 
                                              value = u"Plate 1",
                                              size = wx.Size(120,25))
        self.szr_AddDestination.Add(self.txt_AddDestination, 0, wx.EXPAND, 0)
        self.szr_AddDestination.Add((5,25), 0, wx.EXPAND, 0)
        if self.Tabname.str_AssayCategory == "thermal_shift":
            lst_PlateFormat = [ u"96", u"384", u"1536" ]
        else:
            lst_PlateFormat = [ u"384", u"1536", u"96" ]
        self.cho_PlateFormat = wx.Choice(self.pnl_AddDestination, choices = lst_PlateFormat)
        self.cho_PlateFormat.SetSelection(0)
        self.szr_AddDestination.Add(self.cho_PlateFormat, 0, wx.EXPAND, 0)
        self.szr_AddDestination.Add((5,25), 0, wx.EXPAND, 0)
        self.btn_AddDestination = btn.CustomBitmapButton(self.pnl_AddDestination, u"Plus", 0, (25,25))
        self.szr_AddDestination.Add(self.btn_AddDestination, 0, wx.EXPAND, 0)
        self.pnl_AddDestination.SetSizer(self.szr_AddDestination)
        self.pnl_AddDestination.Layout()
        self.szr_Plates.Add(self.pnl_AddDestination, 0, wx.ALL, 5)
        # Remove plate
        self.pnl_RemoveDestination = wx.Panel(self.pnl_Plates, size = wx.Size(450,25),
                                              style = wx.TAB_TRAVERSAL)
        self.szr_RemoveDestination = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_RemoveDestination.Add((-1,25), 1, wx.EXPAND, 0)
        self.lbl_RemoveDestination = wx.StaticText(self.pnl_RemoveDestination,
                                                   label = u"Remove selected plate(s)",
                                                   size = wx.Size(-1,25))
        self.szr_RemoveDestination.Add(self.lbl_RemoveDestination, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 0)
        self.szr_RemoveDestination.Add((5,25), 0, wx.ALL, 0)
        self.btn_RemoveDestination = btn.CustomBitmapButton(self.pnl_RemoveDestination, u"Minus", 0, (25,25))
        self.szr_RemoveDestination.Add(self.btn_RemoveDestination, 0, wx.EXPAND, 5)
        self.pnl_RemoveDestination.SetSizer(self.szr_RemoveDestination)
        self.pnl_RemoveDestination.Layout()
        self.szr_RemoveDestination.Fit(self.pnl_RemoveDestination)
        self.szr_Plates.Add(self.pnl_RemoveDestination, 0, wx.ALL, 5)
        # Add to panel and fit
        self.pnl_Plates.SetSizer(self.szr_Plates)
        self.pnl_Plates.Layout()
        self.szr_Plates.Fit(self.pnl_Plates)
        self.szr_Transfer.Add(self.pnl_Plates, 0, wx.ALL, 0)
        self.lbc_Transfer = tdnd.MyDropTarget(self.pnl_Transfer, size = wx.Size(450,300),
                                            style = wx.LC_REPORT,
                                            name = u"TransferFileEntries",
                                            instance = self)
        self.lbc_Transfer.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Transfer.InsertColumn(0,"Destination Plate Name")
        self.lbc_Transfer.SetColumnWidth(0, 150)
        self.lbc_Transfer.InsertColumn(1,"Wells")
        self.lbc_Transfer.SetColumnWidth(1, 50)
        self.lbc_Transfer.InsertColumn(2,"Raw Data Plate")
        self.lbc_Transfer.SetColumnWidth(2, 250)
        self.szr_Transfer.Add(self.lbc_Transfer, 0, wx.ALL, 5)
        self.pnl_Transfer.SetSizer(self.szr_Transfer)
        self.pnl_Transfer.Layout()
        self.szr_Assignment.Add(self.pnl_Transfer, 1, wx.ALL, 5)
        # 2.2 Assignment Buttons
        self.szr_AssignButtons = wx.BoxSizer(wx.VERTICAL)
        self.szr_AssignButtons.Add((0, 120), 0, wx.EXPAND, 5)
        self.lbl_Assign = wx.StaticText(self, label = u"Assign")
        self.lbl_Assign.Wrap(-1)
        self.szr_AssignButtons.Add(self.lbl_Assign, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.btn_Assign = btn.CustomBitmapButton(self, "ArrowLeft", 1, (40,25))
        self.btn_Assign.Bind(wx.EVT_BUTTON, self.AssignPlate)
        self.szr_AssignButtons.Add(self.btn_Assign, 0, wx.ALL, 5)
        self.btn_Remove = btn.CustomBitmapButton(self, "ArrowRight", 1, (40,25))
        self.szr_AssignButtons.Add(self.btn_Remove, 0, wx.ALL, 5)
        self.lbl_Remove = wx.StaticText(self, label = u"Remove")
        self.lbl_Remove.Wrap(-1)
        self.szr_AssignButtons.Add(self.lbl_Remove, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.szr_Assignment.Add(self.szr_AssignButtons, 0, wx.EXPAND, 5)
        # 2.3 Data Files
        self.pnl_Data = wx.Panel(self, size = wx.Size(460,-1), 
                                 style = wx.TAB_TRAVERSAL)
        self.pnl_Data.SetBackgroundColour(clr_Panels)
        self.pnl_Data.SetMaxSize(wx.Size(460,-1))
        self.szr_Data = wx.BoxSizer(wx.VERTICAL)
        if data == "directory":
            str_RawDataLabel = "Select the directory with the raw data:"
            str_RawDataTitle = "Select a folder"
            str_PickerType = "directory"
        else:
            str_RawDataLabel = "Select a raw data file:"
            str_RawDataTitle = "Select a file"
            str_PickerType = "file"
        self.lbl_RawData = wx.StaticText(self.pnl_Data, label = str_RawDataLabel,
                                         size = wx.Size(450,20))
        self.szr_Data.Add(self.lbl_RawData, 0, wx.ALL, 5)
        self.pnl_Spacer = wx.Panel(self.pnl_Data, size = wx.Size(460,5),
                                   style = wx.TAB_TRAVERSAL)
        self.szr_Data.Add(self.pnl_Spacer, 0, wx.ALL, 0)
        self.fpk_Data = CustomFilePicker(self.pnl_Data, str_RawDataTitle, data, (450,-1))
        self.fpk_Data.Type = str_PickerType
        self.szr_Data.Add(self.fpk_Data, 0, wx.ALL, 5)
        self.lbc_Data = tdnd.MyDragList(self.pnl_Data,
                                      size = wx.Size(450,300),
                                      style = wx.LC_REPORT)
        self.lbc_Data.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Data.InsertColumn(0,"Data Plate Name")
        self.lbc_Data.SetColumnWidth(0, 250)
        self.lbc_Data.InsertColumn(1,"Wells")
        self.lbc_Data.SetColumnWidth(1, 50)
        self.szr_Data.Add(self.lbc_Data, 0, wx.ALL, 5)
        self.pnl_Data.SetSizer(self.szr_Data)
        self.pnl_Data.Layout()
        self.szr_Assignment.Add(self.pnl_Data, 0, wx.ALL, 5)

        # 3. Normalisation
        #if normalise == True:
        #    self.pnl_Normalise = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(460,-1), wx.TAB_TRAVERSAL)
        #    self.pnl_Normalise.SetBackgroundColour(clr_Panels)
        #    self.pnl_Normalise.SetMaxSize(wx.Size(460,-1))
        #    self.szr_Normalise = wx.BoxSizer(wx.VERTICAL)
        #    self.chk_Normalise = wx.CheckBox(self.pnl_Normalise, wx.ID_ANY,  u"Normalise plates against a reference plate (e.g. Solvent only)", wx.DefaultPosition, wx.DefaultSize, 0)
        #    self.chk_Normalise.SetValue(False)
        #    self.szr_Normalise.Add(self.chk_Normalise, 0, wx.ALL, 5)
        #    self.fpk_Normalise = CustomFilePicker(self.pnl_Normalise, u"Select a file", u"*.*", (450,-1))
        #    self.szr_Normalise.Add(self.fpk_Normalise, 0, wx.ALL, 5)
        #    self.pnl_Normalise.SetSizer(self.szr_Normalise)
        #    self.pnl_Normalise.Layout()
        #    self.szr_Assignment.Add(self.pnl_Normalise, 0, wx.ALL, 5)
        # 4. Plate layouts
        if layouts == True:
            self.pnl_Layouts = wx.Panel(self, size = wx.Size(460,-1),
                                        style = wx.TAB_TRAVERSAL)
            self.pnl_Layouts.SetBackgroundColour(clr_Panels)
            self.pnl_Layouts.SetMaxSize(wx.Size(460,-1))
            self.szr_Layouts = wx.BoxSizer(wx.VERTICAL)
            self.btn_EditLayouts = btn.CustomBitmapButton(self.pnl_Layouts, "EditIndividualPlateLayouts", 0, (186,25))
            self.szr_Layouts.Add(self.btn_EditLayouts, 0, wx.ALIGN_RIGHT|wx.ALL, 0)
            self.btn_EditLayouts.Enable(False)
            self.pnl_Layouts.SetSizer(self.szr_Layouts)
            self.pnl_Layouts.Layout()
            self.szr_Assignment.Add(self.pnl_Layouts, 0, wx.ALL, 5)
        # Finalise

        self.szr_Assignment.Add((-1,-1), 0, wx.EXPAND, 5)
        self.szr_Assignment.Add((-1,-1), 0, wx.EXPAND, 5)

        self.szr_Files.Add(self.szr_Assignment, 0, wx.EXPAND, 5)
        self.SetSizer(self.szr_Files)
        self.Layout()

        # Bindings
        self.lbc_Transfer.Bind(tdnd.EVT_TRANSFER_UPDATE, self.OnUpdateTransfer)
        self.fpk_Data.Bind(self.GatherDataFiles)
        self.btn_Remove.Bind(wx.EVT_BUTTON, self.RemovePlate)
        self.btn_AddDestination.Bind(wx.EVT_BUTTON, self.AddPlate)
        self.btn_RemoveDestination.Bind(wx.EVT_BUTTON, self.DeletePlate)

        if self.Tabname.SampleSource == "echo":
            self.pnl_Echo.Show()
            self.lbl_RawData.SetSize(450,-1)
            self.pnl_Plates.Hide()
            self.pnl_Spacer.Hide()
            self.Layout()

    # 2.1 Load transfer file, get list of plates, write into list box
    def ReadTransferFile(self, str_TransferFile):
        """
        Get list of destination plate entries in transfer file and populate
        list control with them.

        Arguments:
            str_TransferFile -> string
        """
        # Write transfer path (full path with with file name) into variable
        self.Tabname.str_TransferPath = str_TransferFile
        # use path with transfer functions to extract destination plates
        self.Tabname.dfr_TransferFile, self.Tabname.dfr_Exceptions = df.create_transfer_frame(str_TransferFile)
        # Include check to see if transfer file was processed correctly
        if self.Tabname.dfr_TransferFile is None:
            msg.FileErrorNotTransfer()
            return None
        # If the dataframe is not None, we continue:
        dfr_DestinationPlates = df.get_destination_plates(self.Tabname.dfr_TransferFile)
        # Clear list before inserting new items
        self.lbc_Transfer.DeleteAllItems()
        for i in range(len(dfr_DestinationPlates)):
            if dfr_DestinationPlates.iloc[i,0].find("Intermediate") == -1:
                # Write DestinationPlateName
                self.lbc_Transfer.InsertItem(i,str(dfr_DestinationPlates.iloc[i,0]))
                # Write number of wells
                self.lbc_Transfer.SetItem(i,1,str(dfr_DestinationPlates.iloc[i,2]))
                # write empty string tinto third column
                self.lbc_Transfer.SetItem(i,2,"")
        if self.Tabname.str_AssayCategory != "single_dose":
            # Write .xls files from same directory into tab_Files.lbc_Data list
            self.lbc_Data.DeleteAllItems()
            # Write transfer path (full path with with file name) into variable; chr(92) is "\"
            self.Tabname.str_DataPath = self.Tabname.str_TransferPath[0:self.Tabname.str_TransferPath.rfind(chr(92))+1]
            lst_DataFiles = os.listdir(self.Tabname.str_DataPath)
            # Select correct file extension:
            for i in range(len(lst_DataFiles)):
                if lst_DataFiles[i].find(self.Tabname.str_DatafileExtension) != -1: #and lst_DataFiles[i].find(".xlsx") == -1: # I am going to have to trust the 
                    self.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
            self.fpk_Data.SetPath(self.Tabname.str_DataPath)
        self.Tabname.bol_TransferLoaded = True
    
    def CreateEmptyTransferFrame(self):
        """
        Creates enpty transfer dataframe when actual transfer file has ben
        loaded.
        """
        self.Tabname.str_TransferPath = None
        self.Tabname.dfr_TransferFile = pd.DataFrame(columns=["SourceConcentration",
                                                     "DestinationPlateName",
                                                     "DestinationPlateBarcode",
                                                     "DestinationPlateType",
                                                     "DestinationWell",
                                                     "SampleID",
                                                     "SampleName",
                                                     "DestinationConcentration",
                                                     "TransferVolume",
                                                     "ActualVolume"])
        

    def GatherDataFiles(self, str_DataPath):
        """
        Get list of data files and populate list control with them.

        Arguments:
            str_DataPath -> string
        """
        # Clear list
        self.lbc_Data.DeleteAllItems()
        # Write transfer path (full path with with file name) into variable
        self.Tabname.str_DataPath = str_DataPath
        # Populate list depending on assaz category. Only for single dose do we have
        # multiple plates per data file.
        if self.Tabname.str_AssayCategory != "single_dose":
            lst_DataFiles = os.listdir(self.Tabname.str_DataPath)
            for i in range(len(lst_DataFiles)):
                if lst_DataFiles[i].find(self.Tabname.str_DatafileExtension) != -1:
                    self.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
        else:
            lst_Plates = get_bmg_list_namesonly(self.Tabname.str_DataPath)
            if len(lst_Plates) == 0:
                msg.FileNotData()
            else:
                for i in range(len(lst_Plates)):
                    self.lbc_Data.InsertItem(i,str(lst_Plates[i]))

    def OnUpdateTransfer(self,event):
        """
        Event handler. Gets called when transfer file is updated. 
        Calls self.UpdatePlateAssignment and updates data file entries
        in lbc_Data with entries from transfer file.
        """
        self.Tabname.bol_DataFilesAssigned = event.set_bool
        self.Tabname.bol_DataFilesUpdated = event.set_bool
        self.UpdatePlateAssignment()
        if len(event.return_items) > 0:
            for i in range(len(event.return_items)):
                self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,event.return_items[i])
            self.lbc_Data.ReSort()

    def AssignPlate(self, event):
        """
        Event handler. Gets called when user assigns entry from data file
        list to transfer file entry. Assigned entry/ies from data file
        list is/are removed.
        """
        # Create lists to handle things:
        lst_Transfer_Selected = []
        lst_Data_Selected = []
        lst_Data_Return = []
        lst_Data_Delete = []
        # Count selected items in Transfer file list and write indices into list:
        for i in range(self.lbc_Transfer.ItemCount):
            if self.lbc_Transfer.IsSelected(i) == True:
                lst_Transfer_Selected.append(i)
        # Count selected items in Data file list and write indices into list:
        for i in range(self.lbc_Data.ItemCount):
            if self.lbc_Data.IsSelected(i) == True:
                lst_Data_Selected.append(i)
        # Assign data files:
        int_Data = len(lst_Data_Selected)
        int_Transfer = len(lst_Transfer_Selected)
        if int_Data > 0 and int_Transfer > 0:
            for i in range(int_Transfer):
                # Make sure we do not run out of selected data files:
                if i < int_Data:
                    # Check if a data file had been assigned previously
                    if self.lbc_Transfer.GetItemText(i,2) != "":
                        lst_Data_Return.append(self.lbc_Transfer.GetItemText(i,2))
                    # Write data file in there
                    self.lbc_Transfer.SetItem(lst_Transfer_Selected[i],2,
                                              self.lbc_Data.GetItemText(lst_Data_Selected[i],0))
                    # Catch which items we want to delete from the data file list.
                    # If there are more data files selected than transfer file entries,
                    # these will not be added to this list and thus not be deleted from
                    # the data list.
                    lst_Data_Delete.append(lst_Data_Selected[i])
                    # update global change tracking variables
                    self.Tabname.bol_DataFilesAssigned = True
                    self.Tabname.bol_DataFilesUpdated = True
        # Delete items that have been assigned:
        if len(lst_Data_Delete) > 0:
            # Go from the end of the list so as to not change the indices when deleting items:
            for i in range(len(lst_Data_Delete),0,-1):
                self.lbc_Data.DeleteItem(lst_Data_Delete[i-1])
        # Return any items:
        if len(lst_Data_Return) > 0:
            for i in range(len(lst_Data_Return)):
                self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,lst_Data_Return[i])
            self.lbc_Data.ReSort()

    def RemovePlate(self, event):
        """
        Event handler. Gets called when user removes data file entry from
        transfer file entry. Removed data file entry/ies get relisted on
        raw data file list control.
        """
        int_Selected = self.lbc_Transfer.GetSelectedItemCount()
        if int_Selected > 0:
            int_idx_Transfer = self.lbc_Transfer.GetFirstSelected()
            if int_idx_Transfer != -1:
                if self.lbc_Transfer.GetItemText(int_idx_Transfer,2) != "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(int_idx_Transfer,2))
                    self.lbc_Transfer.SetItem(int_idx_Transfer,2,"")
                    self.lbc_Data.ReSort()
                    self.Tabname.bol_DataFilesAssigned = False
        if int_Selected > 1:
            for i in range(int_Selected-1):
                if self.lbc_Transfer.GetNextSelected(i) and self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(i),2) != "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(i),2))
                    self.lbc_Transfer.SetItem(self.lbc_Transfer.GetNextSelected(i),2,"")
                    self.lbc_Data.ReSort()
                    self.Tabname.bol_DataFilesAssigned = False
        # Check if any data files remain assigned to destination plate entries
        # and set tracking varibles
        for i in range(self.lbc_Transfer.GetItemCount()-1):
            if self.lbc_Transfer.GetItem(i,2) != "":
                self.Tabname.bol_DataFilesAssigned = True
                self.Tabname.bol_DataFilesUpdated = True

    def UpdatePlateAssignment(self):
        """
        Updates plate assignment dataframe with entries from transfer file
        list control.
        """
        # count how many assigned plates there are
        count = 0
        for i in range(self.lbc_Transfer.GetItemCount()):
            if self.lbc_Transfer.GetItemText(i,2) != "":
                count += 1
        self.Tabname.bol_DataFilesAssigned = False
        # Initialise plate assignment dataframe
        if count > 0:
            self.Tabname.dfr_PlateAssignment = pd.DataFrame(columns=["TransferEntry",
                                                            "DataFile","Wells"],
                                                            index=range(count))
            j = 0
            for i in range(self.lbc_Transfer.GetItemCount()):
                if self.lbc_Transfer.GetItemText(i,2) != "":
                    self.Tabname.dfr_PlateAssignment.loc[j,"TransferEntry"] = self.lbc_Transfer.GetItemText(i,0)
                    self.Tabname.dfr_PlateAssignment.loc[j,"Wells"] = self.lbc_Transfer.GetItemText(i,1)
                    self.Tabname.dfr_PlateAssignment.loc[j,"DataFile"] = self.lbc_Transfer.GetItemText(i,2)
                    self.Tabname.bol_DataFilesAssigned = True
                    j += 1
        else:
            return None
        if self.Tabname.bol_LayoutDefined == False:
            self.CreatePlateLayout()
    
    def CreatePlateLayout(self):
        """
        Creates a plate layout dataframe with metadata for each well
        of the plate. Meta data is taken from TxtCtrls
        """
        self.Tabname.dfr_Layout = pd.DataFrame(index=range(self.Tabname.dfr_PlateAssignment.shape[0]),
                                               columns=["PlateID","ProteinNumerical","PurificationID",
                                                        "Concentration","WellType"])
        for idx_Plate in self.Tabname.dfr_Layout.index:
            int_PlateFormat = int(self.Tabname.dfr_PlateAssignment.loc[idx_Plate,"Wells"])
            self.Tabname.dfr_Layout.at[idx_Plate,"PlateID"] = "X999A"
            self.Tabname.dfr_Layout.at[idx_Plate,"ProteinNumerical"] = df.make_list(int_PlateFormat,0)
            self.Tabname.dfr_Layout.at[idx_Plate,"PurificationID"] = df.make_list(int_PlateFormat,self.Tabname.str_Purification)
            self.Tabname.dfr_Layout.at[idx_Plate,"Concentration"] = df.make_list(int_PlateFormat,self.Tabname.int_ProteinConc)
            self.Tabname.dfr_Layout.at[idx_Plate,"WellType"] = df.make_list(int_PlateFormat,"Sample")
        self.Tabname.bol_LayoutDefined = True
    
    def SwitchSampleSource(self):
        """
        Writes data file entries in transfer listctrl back to data file
        listctrl and clears transfer lstctrl. Displays appropriate fields
        for selected sample source.
        """
        if self.lbc_Transfer.GetItemCount() > 0:
            for idx_List in range(self.lbc_Transfer.GetItemCount()):
                if self.lbc_Transfer.GetItemText(idx_List,2) != "":
                    self.lbc_Data.InsertItem(self.lbc_Data.GetItemCount()+1,
                                             self.lbc_Transfer.GetItemText(idx_List,2))
            self.lbc_Transfer.DeleteAllItems()
        if self.Tabname.SampleSource == "echo":
            self.pnl_Echo.Show()
            self.pnl_Plates.Hide()
            self.pnl_Spacer.Hide()
            self.Layout()
        elif self.Tabname.SampleSource == "lightcycler":
            self.pnl_Echo.Hide()
            self.pnl_Plates.Show()
            self.pnl_Spacer.Show()
            self.Layout()
        elif self.Tabname.SampleSource == "well":
            self.pnl_Echo.Hide()
            self.pnl_Plates.Show()
            self.pnl_Spacer.Show()
            self.Layout()

    def AddPlate(self,event):
        """
        Adds entry to Transfer File dataframe if a new raw data
        entry is assigned to a transfer entry.
        """
        # Get text for DestinationPlateName:
        int_PlateFormat = int(self.cho_PlateFormat.GetString(self.cho_PlateFormat.GetSelection()))
        str_DestinationPlateName = self.txt_AddDestination.GetValue()
        # Check if it's already been added:
        if self.lbc_Transfer.GetItemCount() > 0:
            for idx_List in range(self.lbc_Transfer.GetItemCount()):
                if self.lbc_Transfer.GetItemText(idx_List,1) != str(int_PlateFormat):
                    msg.PlateFormatsDoNotMatch()
                    return None
                if self.lbc_Transfer.GetItemText(idx_List,0) == str_DestinationPlateName:
                    msg.ItemAlradyExists("Destination Plate")
                    return None
        # Check if we have a transfer data frame. If not, make one
        if not hasattr(self.Tabname, "dfr_TransferFile"):
            self.CreateEmptyTransferFrame()
        dfr_Add = pd.DataFrame(columns=["SourceConcentration","DestinationPlateName",
                                        "DestinationPlateBarcode","DestinationPlateType",
                                        "DestinationWell","SampleID","SampleName",
                                        "DestinationConcentration","TransferVolume",
                                        "ActualVolume"], index=range(int_PlateFormat))
        # Write values into dafarame -> Use dummy values
        for i in range(int_PlateFormat):
            dfr_Add.loc[i,"SourceConcentration"] = 50 # Dummy value
            dfr_Add.loc[i,"DestinationPlateName"] = str_DestinationPlateName
            dfr_Add.loc[i,"DestinationPlateBarcode"] = "Dummy"
            dfr_Add.loc[i,"DestinationPlateType"] = "PCR_" + str(int_PlateFormat)
            dfr_Add.loc[i,"DestinationWell"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"SampleID"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"SampleName"] = pf.index_to_well(i,int_PlateFormat)
            dfr_Add.loc[i,"DestinationConcentration"] = 5
            dfr_Add.loc[i,"TransferVolume"] = 20 # Dummy value
            dfr_Add.loc[i,"ActualVolume"] = 20 # Dummy value
        # Combine/concatenate dataframes
        self.Tabname.dfr_TransferFile = pd.concat([self.Tabname.dfr_TransferFile, dfr_Add],
                                                  ignore_index=False)
        self.lbc_Transfer.InsertItem(self.lbc_Transfer.GetItemCount()+1,str_DestinationPlateName)
        self.lbc_Transfer.SetItem(self.lbc_Transfer.GetItemCount()-1,1,str(int_PlateFormat))
        if self.lbc_Transfer.GetItemCount() > 0:
            self.btn_RemoveDestination.Enable(True)
        if len(self.Tabname.dfr_TransferFile) > 0:
            self.Tabname.bol_TransferLoaded = True
        else:
            self.Tabname.bol_TransferLoaded = False

    def DeletePlate(self, event):
        """
        Removes entries in TransferFile dataframe is raw data entry is
        removed from transfer file ListCtrl.
        """
        int_Selected = self.lbc_Transfer.GetSelectedItemCount()
        if int_Selected > 0:
            str_DestinationPlate = self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetFirstSelected(), 0)
            self.Tabname.dfr_TransferFile = self.Tabname.dfr_TransferFile.drop(self.Tabname.dfr_TransferFile.index[self.Tabname.dfr_TransferFile["DestinationPlateName"]==str_DestinationPlate])
            self.lbc_Transfer.DeleteItem(self.lbc_Transfer.GetFirstSelected())
        if int_Selected > 1:
            for i in range(int_Selected - 1):
                str_DestinationPlate = self.lbc_Transfer.GetItemText(self.lbc_Transfer.GetNextSelected(0), 0)
                self.Tabname.dfr_TransferFile = self.Tabname.dfr_TransferFile.drop(self.Tabname.dfr_TransferFile.index[self.Tabname.dfr_TransferFile["DestinationPlateName"]==str_DestinationPlate])
                self.lbc_Transfer.DeleteItem(self.lbc_Transfer.GetNextSelected(0))
        if self.lbc_Transfer.GetItemCount() == 0:
            self.btn_RemoveDestination.Enable(False)
        if len(self.Tabname.dfr_TransferFile) > 0:
            self.Tabname.bol_TransferLoaded = True
        else:
            self.Tabname.bol_TransferLoaded = False

##########################################################
##                                                      ##
##    #####   ######  ##  ##  ##  ######  ##  ##  ##    ##
##    ##  ##  ##      ##  ##  ##  ##      ##  ##  ##    ##
##    #####   ####    ##  ##  ##  ####    ##  ##  ##    ##
##    ##  ##  ##       ####   ##  ##       ########     ##
##    ##  ##  ######    ##    ##  ######    ##  ##      ##
##                                                      ##
##########################################################

class Review(wx.Panel):

    """
    Panel to review plate data. Available plots: Heatmap (for raw data),
    Replicate correlation (scatter plot), Scatter plot (for simple data
    processing, e.g. single concentration screen)
    """

    def __init__(self, notebook, tabname, assaycategory, plots = [], xlabels = [],
                 ylabels= [], sidebar = []):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            assaycategory -> short hand of the assay
            plots -> list of the plots to be displayed
            xlabels -> list x-axis labels for the plots
            ylabels -> list of y-axis labels for the plots
            sidebar -> list of parameters to be displayed on the plots'
                       sidebar
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname
        self.Assaycategory = assaycategory

        self.SetBackgroundColour(cs.BgUltraLight)

        self.dic_PlotOptions = {"Heat Map": cp.HeatmapPanel,
                                "Replicate Correlation": cp.ReplicateCorrelation,
                                "Scatter Plot": cp.ScatterPlotPanel}
        self.dic_PlotUpdateFunctions = {"Heat Map": self.UpdateHeatMap,
                                        "Replicate Correlation": self.UpdateReplicateCorrelation,
                                        "Scatter Plot": self.UpdateScatterPlot}
        self.dic_Plots = {}
        self.dic_TabButtons = {}
        self.lst_Plots = plots

        # Start Building
        self.szr_ReviewVertical = wx.BoxSizer(wx.VERTICAL)

        self.szr_ReviewHorizontal = wx.BoxSizer(wx.HORIZONTAL)

        # List Control - Plates
        self.lbc_Plates = wx.ListCtrl(self, size = wx.Size(310,-1),
                                      style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Plates.SetBackgroundColour(cs.BgUltraLight)
        self.lbc_Plates.InsertColumn(0, "Plate")
        self.lbc_Plates.SetColumnWidth(0,40)
        self.lbc_Plates.InsertColumn(1,"Transfer file entry")
        self.lbc_Plates.SetColumnWidth(1, 120)
        self.lbc_Plates.InsertColumn(2,"Data file name")
        self.lbc_Plates.SetColumnWidth(2, 120)
        self.szr_ReviewHorizontal.Add(self.lbc_Plates, 0, wx.ALL|wx.EXPAND, 5)


        # Plot panel ###################################################################
        self.szr_Plots = wx.BoxSizer(wx.VERTICAL)
        # Create simplebook before adding it to its sizer so that it can be added as
        # .Notebook for IconTabButtons:
        self.sbk_Plots = wx.Simplebook(self, size = wx.Size(900,600))
        self.sbk_Plots.SetBackgroundColour(cs.BgUltraLight)
        self.szr_TabButtons = wx.BoxSizer(wx.HORIZONTAL)
        idx_Button = 0
        for plot in self.lst_Plots:
            self.dic_TabButtons[plot] = btn.IconTabButton(parent = self,
                                                          label = plot,
                                                          index = idx_Button,
                                                          path = self.Tabname.AssayPath)
            self.dic_TabButtons[plot].Group = self.dic_TabButtons
            self.dic_TabButtons[plot].Notebook = self.sbk_Plots
            self.dic_TabButtons[plot].IsEnabled(True)
            self.szr_TabButtons.Add(self.dic_TabButtons[plot], 0, wx.ALL, 0)
            self.dic_Plots[plot] = self.dic_PlotOptions[plot](parent = self.sbk_Plots,
                                                             size = wx.Size(600,400),
                                                             tabname = self.Tabname,
                                                             title = plot,
                                                             buttons = True)
            self.sbk_Plots.AddPage(self.dic_Plots[plot], plot, False)
            idx_Button += 1
        self.dic_TabButtons[self.lst_Plots[0]].IsCurrent(True)
        self.szr_Plots.Add(self.szr_TabButtons, 0, wx.ALL, 0)
        self.szr_Plots.Add(self.sbk_Plots, 0, wx.ALL, 0)

        self.szr_ReviewHorizontal.Add(self.szr_Plots, 0, wx.ALL, 5)
        self.szr_ReviewVertical.Add(self.szr_ReviewHorizontal, 0, wx.ALL, 5)

        self.SetSizer(self.szr_ReviewVertical)
        self.szr_ReviewVertical.Fit(self)
        self.Layout()

        # Binding
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdatePlots)

    def Populate(self, noreturn = False):
        """
        Tries to populate the list control for the first time.

        Arguments:
            noreturn -> boolean. optional. Determines whether
                        to return success of populating as
                        boolean
        
        Returns:
            Boolean result of populating the tab.
        """
        try:
            self.lbc_Plates.DeleteAllItems()
            for i in range(self.Tabname.dfr_AssayData.shape[0]):
                self.lbc_Plates.InsertItem(i,str(i+1))
                self.lbc_Plates.SetItem(i,1,
                        str(self.Tabname.dfr_AssayData.loc[i,"DestinationPlateName"]))
                self.lbc_Plates.SetItem(i,2,
                        str(self.Tabname.dfr_AssayData.loc[i,"DataFileName"]))
            # This will call UpdatePlots as it is bound to the selection event of the list
            self.lbc_Plates.Select(0)
            self.lbc_Plates.SetFocus()
            if noreturn == False:
                return True
        except:
            if noreturn == False:
                return False

    def UpdatePlots(self, event):
        """
        Event handler.
        General function to update the plots after clicking on an entry in lbc_Plates.
        Calls functions to update individual plots as required.

        Returns: -
        """
        # Get current selection
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        if idx_Plate == -1:
            idx_Plate = 0
        # Check which plots are present and update accordingly
        for plot in self.lst_Plots:
            self.dic_PlotUpdateFunctions[plot](idx_Plate)

    def UpdateHeatMap(self, idx_Plate):
        """
        Calls function in higher instance to prepare data for the plot.
        Also updates side panel with data quality metrics

        Arguments:
            idx_Plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Heat Map"].PlateIndex = idx_Plate
        self.dic_Plots["Heat Map"].Data = self.Tabname.PrepareHeatMap(idx_Plate)
        self.dic_Plots["Heat Map"].Title = self.Tabname.dfr_AssayData.iloc[idx_Plate,0]
        self.dic_Plots["Heat Map"].Draw()

        # Update plate details in plot's sidebar (Solvent, buffer and control well mean values):
        if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0]) == False:
            self.dic_Plots["Heat Map"].lbl_BufferWells.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0],2)) + " " + chr(177) + " " + str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferSEM",0],2)))
        else:
            self.dic_Plots["Heat Map"].lbl_BufferWells.SetLabel(u"N/A")
        if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0]) == False:
            self.dic_Plots["Heat Map"].lbl_SolventWells.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0],2)) + " " + chr(177) + " " + str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0],2)))
        else:
            self.dic_Plots["Heat Map"].lbl_SolventWells.SetLabel(u"N/A")
        if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0]) == False:
            self.dic_Plots["Heat Map"].lbl_ControlWells.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)) + " " + chr(177) + " " + str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlSEM",0],2)))
        else:
            self.dic_Plots["Heat Map"].lbl_ControlWells.SetLabel(u"N/A")
        if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",0]) == False:
            try:
                self.dic_Plots["Heat Map"].lbl_ZPrimeMean.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",0],3)))
                self.dic_Plots["Heat Map"].lbl_ZPrimeMedian.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMedian",0],3)))
            except:
                # If the above doesn't work, it's text in these! (i.e. "N/A")
                self.dic_Plots["Heat Map"].lbl_ZPrimeMean.SetLabel(str(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",0]))
                self.dic_Plots["Heat Map"].lbl_ZPrimeMedian.SetLabel(str(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMedian",0]))
            if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0]) == False:
                self.dic_Plots["Heat Map"].lbl_BC.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0]/self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)))
            else:
                self.dic_Plots["Heat Map"].lbl_BC.SetLabel(u"N/A")
            if pd.isna(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0]) == False:
                self.dic_Plots["Heat Map"].lbl_DC.SetLabel(str(round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0]/self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)))
            else:
                self.dic_Plots["Heat Map"].lbl_DC.SetLabel(u"N/A")
        else:
            self.dic_Plots["Heat Map"].lbl_ZPrimeMean.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_ZPrimeMedian.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_BC.SetLabel(u"N/A")
            self.dic_Plots["Heat Map"].lbl_DC.SetLabel(u"N/A")

    def UpdateReplicateCorrelation(self, idx_Plate):
        """
        Calls function in higher instance to prepare data for the plot.

        Arguments:
            idx_Plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Replicate Correlation"].dfr_Input = self.Tabname.PrepareScatterPlot(idx_Plate)
        self.dic_Plots["Replicate Correlation"].Draw()

    def UpdateScatterPlot(self, idx_Plate):
        """
        Calls function in higher instance to prepare data for the plot.

        Arguments:
            idx_Plate -> integer type, index of the plate that has its data
                         represented by the heatmap.

        Returns: -
        """
        self.dic_Plots["Scatter Plot"].dfr_Input = self.Tabname.PrepareScatterPlot(idx_Plate)
        self.dic_Plots["Scatter Plot"].Draw()


##################################################
##                                              ##
##    #####   ##       ####   ######   #####    ##
##    ##  ##  ##      ##  ##    ##    ##        ##
##    #####   ##      ##  ##    ##     ####     ##
##    ##      ##      ##  ##    ##        ##    ##
##    ##      ######   ####     ##    #####     ##
##                                              ##
##################################################

class ELNPlots(wx.Panel):
    """
    Panel containing all plots for a page. Serves as summary figure for
    ELN page.
    """

    def __init__(self, notebook, tabname, shorthand):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
            shorthand -> string. Determines type of plot to use
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname
        self.shorthand = shorthand

        self.SetBackgroundColour(cs.BgUltraLight)
        self.szr_ELNPlots = wx.BoxSizer(wx.VERTICAL)

        # Sizer to keep Scrolled Window
        self.szr_ELNPlots_Scroll = wx.BoxSizer(wx.VERTICAL)
        self.pnl_ELNPlots_Scroll = wx.ScrolledWindow(self, style = wx.HSCROLL|wx.VSCROLL)
        self.pnl_ELNPlots_Scroll.SetScrollRate(5, 5)

        self.szr_ELNPlots_Scroll.Add(self.pnl_ELNPlots_Scroll, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_ELNPlots.Add(self.szr_ELNPlots_Scroll, 1, wx.EXPAND, 5)

        # Finalise
        self.SetSizer(self.szr_ELNPlots)
        self.Layout()
        # Fitting happens later.

    def PopulatePlotsTab(self, completecontainer):
        """
        Populates the tab with data from self.Tabname.dfr_AssayData

        Arguments:
            completecontainer -> pandas dataframe. Contains all assay data.
        """
        #Cleanup if drawn before:
        for each in self.pnl_ELNPlots_Scroll.GetChildren():
            if each:
                each.Destroy()
        # Create lists and dictionaries to hold button/sizer/plot names and objects:
        int_Plates = len(completecontainer)
        self.lst_FigureNames = []
        lst_ClipNames = []
        lst_PNGNames = []
        lst_SzrNames = []
        lst_LineNames = []
        self.dic_Figures = {}
        self.dic_Clip = {}
        self.dic_PNG = {}
        self.dic_BtnSzrs = {}
        self.dic_Lines = {}
        for i in range(int_Plates):
            self.lst_FigureNames.append("fig_Plate_" + str(i+1))
            lst_ClipNames.append("btn_Clipboard_" + str(i+1))
            lst_PNGNames.append("btn_PNG_" + str(i+1))
            lst_SzrNames.append("szr_Plots_Btns_" + str(i+1))
            lst_LineNames.append("line_ELNPlots_" + str(i+1))
        # Create sizer in scroll window:
        self.szr_ELNPlots_Scroll = wx.BoxSizer(wx.VERTICAL)
        # Dimensions for plot: distance to top edge, height of subplots, distance between subplots in y direction:
        # Defaults:
        int_GridWidth = 4
        int_LabelSize = 8
        int_TitleSize = 10
        int_SuperTitleSize = 16
        distance_top_px = 90
        distance_supertitle_top_px = 20
        subplot_height_px = 90 #90
        subplot_distance_px = 92
        distance_bottom_px = 70
        dpi = 100
        # Change based on assay:
        if self.shorthand in ["NDSF","DSF","RATE"]:
            int_GridWidth = 6 # was 4
            int_LabelSize = 6
            int_TitleSize = 10
            int_SuperTitleSize = 16
            subplot_height_px = 70

        self.dlg_PlotsProgress = GenericProgress(self, "Plotting samples")
        self.dlg_PlotsProgress.Show()

        count = 0
        for i in range(len(self.lst_FigureNames)):
            # Get Dimensions based on number of subplots:
            self.Tabname.int_Samples = len(completecontainer.loc[count,"ProcessedDataFrame"])
            int_GridHeight = int(math.ceil(self.Tabname.int_Samples/int_GridWidth))
            # Get absolute dimensions:
            total_height_px = distance_top_px + (int_GridHeight * subplot_height_px) + ((int_GridHeight - 1) * subplot_distance_px) + distance_bottom_px
            total_height_inch = total_height_px / dpi
            # Get relative dimesnions:
            hspace_ratio = subplot_height_px / total_height_px
            bottom_ratio = distance_bottom_px / total_height_px    
            top_ratio = 1 - (distance_top_px / total_height_px)
            supertitle_ratio = 1 - (distance_supertitle_top_px / total_height_px)
            # Create panel:
            self.dic_PlotType = {"EPDR":cp.PlotGridEPDR,"DSF":cp.PlotGridDSF,
                                 "NDSF":cp.PlotGridNDSF,"RATE":cp.PlotGridRATE,
                                 "DRTC":cp.PlotGridDRTC}
            self.dic_Figures[self.lst_FigureNames[i]] = self.dic_PlotType[self.shorthand](
                    self.pnl_ELNPlots_Scroll, total_height_px, total_height_inch, dpi)
            self.dic_Figures[self.lst_FigureNames[i]].Draw(self.Tabname.int_Samples,completecontainer.loc[count,"ProcessedDataFrame"],
                completecontainer.loc[count,"DestinationPlateName"],int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,
                top_ratio,total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,self.dlg_PlotsProgress)
            # Add panel to Plots sizer
            self.szr_ELNPlots_Scroll.Add(self.dic_Figures[self.lst_FigureNames[i]], 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
            # Create and add l
            self.dic_Lines[lst_LineNames[i]] = wx.StaticLine(self.pnl_ELNPlots_Scroll, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
            self.szr_ELNPlots_Scroll.Add(self.dic_Lines[lst_LineNames[i]], 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
            # Create button bar sizer
            self.dic_BtnSzrs[lst_SzrNames[i]] = wx.BoxSizer(wx.HORIZONTAL)
            # Create clipboard button, bind command, add to button bar sizer
            self.dic_Clip[lst_ClipNames[i]] = btn.CustomBitmapButton(self.pnl_ELNPlots_Scroll, u"Clipboard", 5, (130,25))
            self.dic_Clip[lst_ClipNames[i]].myname = str(i) # add name to pass index on to function
            self.dic_Clip[lst_ClipNames[i]].Bind(wx.EVT_BUTTON, self.PanelPlotToClipboard)
            self.dic_BtnSzrs[lst_SzrNames[i]].Add(self.dic_Clip[lst_ClipNames[i]], 0, wx.ALL, 5)
            # Create PNG button, bind command, add to button bar sizer
            self.dic_PNG[lst_PNGNames[i]] = btn.CustomBitmapButton(self.pnl_ELNPlots_Scroll, u"ExportToFile", 5, (104,25))
            self.dic_PNG[lst_PNGNames[i]].myname = str(i) # add name to pass index on to function
            self.dic_PNG[lst_PNGNames[i]].Bind(wx.EVT_BUTTON, self.PanelPlotToPNG)
            self.dic_BtnSzrs[lst_SzrNames[i]].Add(self.dic_PNG[lst_PNGNames[i]], 0, wx.ALL, 5)
            # Add button bar sizer to plots sizer
            self.szr_ELNPlots_Scroll.Add(self.dic_BtnSzrs[lst_SzrNames[i]], 0, wx.ALIGN_RIGHT, 5)

            count += 1

        self.pnl_ELNPlots_Scroll.SetSizer(self.szr_ELNPlots_Scroll)
        self.szr_ELNPlots_Scroll.Fit(self.pnl_ELNPlots_Scroll)
        #self.pnl_ELNPlots.Layout()
        self.Layout()
        self.Tabname.bol_ELNPlotsDrawn = True
        self.dlg_PlotsProgress.Destroy()

    # 5.2 Copy a plot to the clipboard
    def PanelPlotToClipboard(self,event):
        """
        Event handler. Calls plot's PlotToClipboard function.
        """
        self.dic_Figures[self.lst_FigureNames[int(event.GetEventObject().myname)]].PlotToClipboard()

    # 5.3 Save a plot as a PNG file 
    def PanelPlotToPNG(self,event):
        """
        Event handler. Calls plot's PlotToPNG function.
        """
        self.dic_Figures[self.lst_FigureNames[int(event.GetEventObject().myname)]].PlotToPNG()


##########################################################################
##                                                                      ##
##    #####    ####   ######   ####   #####    ####    #####  ######    ##
##    ##  ##  ##  ##    ##    ##  ##  ##  ##  ##  ##  ##      ##        ##
##    ##  ##  ######    ##    ######  #####   ######   ####   ####      ##
##    ##  ##  ##  ##    ##    ##  ##  ##  ##  ##  ##      ##  ##        ##
##    #####   ##  ##    ##    ##  ##  #####   ##  ##  #####   ######    ##
##                                                                      ##
##########################################################################

class ExportToDatabase(wx.Panel):
    """
    Panel with a wx.grid.Grid. Contains experimental data formatted for upload
    to database.
    """

    def __init__(self, notebook, tabname):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent=notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)

        # Start Building
        self.szr_Export = wx.BoxSizer(wx.VERTICAL)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)

        # Gridl - Database
        self.grd_Database = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Grid.Add(self.grd_Database, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_Grid.Fit(self.grd_Database)
        self.szr_Export.Add(self.szr_Grid, 1, wx.EXPAND, 5)

        # Button Bar
        self.szr_Export_ButtonBar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Export_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_DotmaticsClipboard = btn.CustomBitmapButton(self, "ClipboardDotmatics", 0, (230,25))
        self.btn_DotmaticsClipboard.Bind(wx.EVT_BUTTON, self.DotmaticsToClipboard)
        self.szr_Export_Buttons.Add(self.btn_DotmaticsClipboard, 0, wx.ALL, 5)
        self.btn_Clipboard = btn.CustomBitmapButton(self, "Clipboard", 0, (130,25))
        self.btn_Clipboard.Bind(wx.EVT_BUTTON, self.CopyToClipboard)
        self.szr_Export_Buttons.Add(self.btn_Clipboard, 0, wx.ALL, 5)
        self.btn_Export = btn.CustomBitmapButton(self, "ExportToFile", 0, (104,25))
        self.btn_Export.Bind(wx.EVT_BUTTON, self.ExportToCSV)
        self.szr_Export_Buttons.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_Export_ButtonBar.Add(self.szr_Export_Buttons, 0, wx.ALIGN_RIGHT, 5)
        self.szr_Export.Add(self.szr_Export_ButtonBar, 0, wx.EXPAND, 5)

        # Finalise
        self.SetSizer(self.szr_Export)
        self.Layout()

        # Binding
        self.grd_Database.Bind(wx.EVT_KEY_DOWN, OnKeyPressGrid)
        self.grd_Database.Bind(wx.grid.EVT_GRID_SELECT_CELL, SingleSelection)
        self.grd_Database.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenCopyOnlyContextMenu)

    def Populate(self, noreturn = False):
        """
        Populates Export tab. Calls thread to do this so that progress
        bar dialog can be updated from within the thread.
        """
        self.dlg_DatabaseProgress = GenericProgress(self, "Populating Table")
        self.dlg_DatabaseProgress.Show()
        thd_PopulateDatabase = threading.Thread(target=self.Populate_thread, args=(), daemon=True)
        thd_PopulateDatabase.start()
        if noreturn == False:
            return True

    def Populate_thread(self):
        """
        Thread for populating the export tab.
        """
        self.Tabname.dfr_Database = pd.DataFrame(columns=self.Tabname.lst_Headers)
        # Create Database dataframe in sections for each plate and append
        for i in range(len(self.Tabname.dfr_AssayData)):
            if self.Tabname.str_AssayCategory.find("dose_response") != -1:
                bol_DoseResponse = True
                if self.Tabname.str_AssayCategory.find("activity") != -1:
                    dfr_Partial = df.create_Database_frame_EPDR_ActAssay(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_AssayData.loc[i,"References"],bol_DoseResponse)    
                else:
                    dfr_Partial = df.create_Database_frame_EPDR(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_AssayData.loc[i,"References"])
            elif self.Tabname.str_AssayCategory == "single_dose":
                bol_DoseResponse = False
                if self.Tabname.str_AssayCategory.find("activity") != -1:
                    dfr_Partial = df.create_Database_frame_EPSD_ActAssay(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_AssayData.loc[i,"References"],bol_DoseResponse)    
                else:
                    dfr_Partial = df.create_Database_frame_EPSD(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_AssayData.loc[i,"References"])
            elif self.Tabname.str_AssayCategory == "rate":
                dfr_Partial = df.create_Database_frame_rate(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5])
            elif self.Tabname.str_AssayCategory == "thermal_shift":
                if self.Tabname.str_AssayType == "nanoDSF":
                    dfr_Partial = df.create_Database_frame_NanoDSF(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_Layout.loc[i])
                else:
                    dfr_Partial = df.create_Database_frame_DSF(self.Tabname.dfr_Details,self.Tabname.lst_Headers,self.Tabname.dfr_AssayData.iloc[i,5],
                        self.Tabname.dfr_Layout.loc[i])
            frames = [self.Tabname.dfr_Database, dfr_Partial]
            self.Tabname.dfr_Database = pd.concat(frames, ignore_index=False)

        # Create grid:
        self.int_Samples = len(self.Tabname.dfr_Database)
        self.Freeze()

        if self.grd_Database.GetNumberRows() > 0:
            self.grd_Database.DeleteRows(0, self.grd_Database.GetNumberRows())
            self.grd_Database.AppendRows(self.int_Samples, True)
        else:
            self.grd_Database.CreateGrid(self.int_Samples, len(self.Tabname.lst_Headers))
            # Grid
            self.grd_Database.EnableEditing(False)
            self.grd_Database.EnableGridLines(True)
            self.grd_Database.EnableDragGridSize(False)
            self.grd_Database.SetMargins(0, 0)
            # Columns
            self.grd_Database.AutoSizeColumns()
            self.grd_Database.EnableDragColMove(False)
            self.grd_Database.EnableDragColSize(True)
            self.grd_Database.SetColLabelSize(20)
            for i in range(len(self.Tabname.lst_Headers)):
                self.grd_Database.SetColLabelValue(i,self.Tabname.lst_Headers[i])
            self.grd_Database.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            # Rows
            self.grd_Database.EnableDragRowSize(True)
            self.grd_Database.SetRowLabelSize(30)
            self.grd_Database.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            # Label Appearance
            # Cell Defaults
            self.grd_Database.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
            self.grd_Database.SetGridLineColour(cs.BgMediumDark)
            self.grd_Database.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        # Populate grid:
        for idx_Sample in range(self.grd_Database.GetNumberRows()):
            # colouring just takes too long for long data sets. But this is how you would do it.
            #if idx_Sample % 2 == 0:
            #    clr_Background = cs.BgLight
            #else:
            #    clr_Background = cs.BgUltraLight
            for col in range(self.grd_Database.GetNumberCols()):
                self.grd_Database.SetCellValue(idx_Sample,col,str(self.Tabname.dfr_Database.iloc[idx_Sample,col]))
                #self.grd_Database.SetCellBackgroundColour(idx_Sample,col,clr_Background)
            if hasattr(self, "dlg_DatabaseProgress") == True:
                self.dlg_DatabaseProgress.gauge.SetValue(int((idx_Sample/self.int_Samples)*200))

        self.grd_Database.AutoSizeColumns()
        self.Thaw()
        if hasattr(self, "dlg_DatabaseProgress") == True:
            self.dlg_DatabaseProgress.Destroy()
        self.Tabname.bol_ExportPopulated = True

    def ExportToCSV(self, event):
        """
        Event handler. Exports data in dfr_Database to csv.
        """
        fdlg = wx.FileDialog(self, "Save results as", wildcard="Comma separated files (*.csv)|*.csv", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                self.Tabname.dfr_Database.to_csv(str_SavePath)
            except PermissionError:
                msg.SavePermissionDenied()

    def CopyToClipboard(self, event):
        """
        Event handler. copies data in dfr_Database to clipboard.
        """
        self.Tabname.dfr_Database.to_clipboard(header=None, index=False)

    def Clear(self):
        """
        Clears the entire grid.
        """
        self.grd_Database.ClearGrid()

    def OpenCopyOnlyContextMenu(self, event):
        """
        Event handler: launcehs context menu after right click on grid.
        """
        self.PopupMenu(CopyOnlyContextMenu(event, event.GetEventObject()))

    def DotmaticsToClipboard(self, event):
        """
        Event handler. Special case to prepare data for clipboard for
        specific customer.
        """

        Date = datetime.now()

        lst_Minima = []
        lst_Maxima = []
        lst_pEC50 = []
        lst_Span = []
        lst_ZPrimeMean = []
        lst_ZPrimeRobust = []
        lst_BufferToControl = []
        lst_DmsoToControl = []
        lst_Concentration = []
        lst_Empty = []
        lst_Comment = []
        lst_Validation = []
        lst_Date = []
        for smpl in range(self.Tabname.dfr_Database.shape[0]):
            lst_Inhibitions = [self.Tabname.dfr_Database.iloc[smpl,28],self.Tabname.dfr_Database.iloc[smpl,31],self.Tabname.dfr_Database.iloc[smpl,34],self.Tabname.dfr_Database.iloc[smpl,37],
            self.Tabname.dfr_Database.iloc[smpl,40],self.Tabname.dfr_Database.iloc[smpl,43],self.Tabname.dfr_Database.iloc[smpl,46],self.Tabname.dfr_Database.iloc[smpl,49],
            self.Tabname.dfr_Database.iloc[smpl,52],self.Tabname.dfr_Database.iloc[smpl,55],self.Tabname.dfr_Database.iloc[smpl,58],self.Tabname.dfr_Database.iloc[smpl,61],
            self.Tabname.dfr_Database.iloc[smpl,64],self.Tabname.dfr_Database.iloc[smpl,67],self.Tabname.dfr_Database.iloc[smpl,70],self.Tabname.dfr_Database.iloc[smpl,73]]
            lst_Minima.append(np.nanmin(lst_Inhibitions))
            lst_Maxima.append(np.nanmax(lst_Inhibitions))
            lst_pEC50.append((-1)*self.Tabname.dfr_Database.iloc[smpl,13])
            lst_Span.append(self.Tabname.dfr_Database.iloc[smpl,21] - self.Tabname.dfr_Database.iloc[smpl,20])
            lst_Concentration.append(self.Tabname.dfr_Database.iloc[smpl,27])
            lst_ZPrimeMean.append(self.Tabname.dfr_Database.iloc[smpl,79])
            lst_ZPrimeRobust.append(self.Tabname.dfr_Database.iloc[smpl,80])
            lst_BufferToControl.append(self.Tabname.dfr_Database.iloc[smpl,81])
            lst_DmsoToControl.append(self.Tabname.dfr_Database.iloc[smpl,82])
            lst_Empty.append("")
            if lst_Maxima[smpl] >= 80:
                lst_Comment.append("ACTMax >= 80%")
                lst_Validation.append("A")
            elif lst_Maxima[smpl] >= 50:
                lst_Comment.append("50% =< ACTMax < 80%")
                lst_Validation.append("A")
            else:
                lst_Comment.append("ACTMax < 50%")
                lst_Validation.append("NA")
            lst_Date.append(Date)

        df = pd.DataFrame(data={"Global Compound ID":self.Tabname.dfr_Database.iloc[:,4],"Purification ID":self.Tabname.dfr_Database.iloc[:,1],
            "Compound comments":lst_Concentration,"":lst_Empty,"Result_ID":lst_Empty,"Evotec Compound ID":lst_Empty,"Evotec Batch ID":lst_Empty,"Validation":lst_Validation,
            "ACTMin":lst_Minima,"ACTMax":lst_Maxima,"Operator":lst_Empty,"EC50":self.Tabname.dfr_Database.iloc[:,15],"CI-Lower":self.Tabname.dfr_Database.iloc[:,17],
            "CI-Upper":self.Tabname.dfr_Database.iloc[:,16],"Operator negative":lst_Empty,"pEC50":lst_pEC50,"Bottom":self.Tabname.dfr_Database.iloc[:,20],
            "Top":self.Tabname.dfr_Database.iloc[:,21],"Hill Slope":self.Tabname.dfr_Database.iloc[:,18],"Span":lst_Span,"R2":self.Tabname.dfr_Database.iloc[:,22],"Comment":lst_Comment,
            "ZPrime":lst_ZPrimeMean,"ZPrimeRobust":lst_ZPrimeRobust,"BufferToControl":lst_BufferToControl,"DMSOToControl":lst_DmsoToControl,"DateOfReport":lst_Date})#.to_clipboard()

        fdlg = wx.FileDialog(self, "Save results as", wildcard="Excel files (*.xlsx)|*.xlsx", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            str_SaveDir = fdlg.GetDirectory()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-5] == ".xlsx":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                df.to_excel(str_SavePath)
                bol_SaveSuccesful = True
            except PermissionError:
                msg.SavePermissionDenied()
                bol_SaveSuccesful = False
                return None
        else:
            return None

        if bol_SaveSuccesful == True:
            wbk_Export = load_workbook(str_SavePath)
            wks_Export = wbk_Export.active
            lst_Columns = df.columns.to_list()
            for cell in range(len(lst_Columns)):
                int_Letters = len(lst_Columns[cell])
                if cell < 25: # Account for +1 offset!
                    str_Column = chr(cell+65+1)
                else:
                    str_Column = "A" + chr(cell+65-26+1)
                if int_Letters > 0:
                    wks_Export.column_dimensions[str_Column].width = int_Letters*1.23
            # Column with dose response plot: Automatically get last column, regardless of how many columns there are:
            int_PlotColumn = len(lst_Columns)
            if int_PlotColumn < 24: # Account for +1 offset!
                str_PlotColumn = chr(int_PlotColumn+65+1)
            else:
                str_PlotColumn = "A" + chr(int_PlotColumn+65-26+1)
            if self.Tabname.str_AssayCategory == "dose_response":
                self.dlg_DotmaticsProgress = GenericProgress(self, "Preparing Dotmatics export")
                self.dlg_DotmaticsProgress.Show()
                self.int_Samples = len(self.Tabname.dfr_Database)
                self.Freeze()
                wks_Export.column_dimensions[str_PlotColumn].width = 84
                # Draw the plots
                int_XLRow = 2 # starts on second row
                count = 1
                lst_Temppaths = []
                for idx_Plate in range(len(self.Tabname.dfr_AssayData)):
                    for idx_Sample in range(len(self.Tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                        # Export plot to temporary file
                        tempplot = cp.CurvePlotPanel(self, (600,450), self)
                        tempplot.Input = self.Tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
                        tempplot.Draw(virtualonly=True)
                        str_SamplePlot = str(count) + ".png"
                        str_Temppath = os.path.join(str_SaveDir,str_SamplePlot)
                        lst_Temppaths.append(str_Temppath)
                        # I had explored the idea of just writing the file into a PIL.Image object, but that threw an error. The below should work fast enough.
                        tempplot.figure.savefig(str_Temppath, dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None,
                            transparent=False, bbox_inches=None, pad_inches=0.1)
                        opxl_Plot_ImageObject = openpyxl.drawing.image.Image(str_Temppath)
                        wks_Export.add_image(opxl_Plot_ImageObject,str_PlotColumn+str(int_XLRow))
                        # Destroy tempplot and delete tempplot.png
                        tempplot.Destroy()
                        wks_Export.row_dimensions[int_XLRow].height = 340
                        int_XLRow += 1
                        count += 1
                        self.dlg_DotmaticsProgress.gauge.SetValue((count/self.int_Samples)*200)
                wbk_Export.save(str_SavePath)
                # Deleting temp files. Deleting temp files just after they've been handed to add_image() or after saving the spreadsheet didn't quite work.
                # They need to be present so that the save function can find them.
                for i in range(len(lst_Temppaths)):
                    if os.path.exists(lst_Temppaths[i]):
                        os.remove(lst_Temppaths[i])
                self.Thaw()
                self.dlg_DotmaticsProgress.Destroy()


################################################################################
##                                                                            ##
##    #####   ##       ####   ######  ######      ##    ##   ####   #####     ##
##    ##  ##  ##      ##  ##    ##    ##          ###  ###  ##  ##  ##  ##    ##
##    #####   ##      ######    ##    ####        ########  ######  #####     ##
##    ##      ##      ##  ##    ##    ##          ## ## ##  ##  ##  ##        ##
##    ##      ######  ##  ##    ##    ######      ##    ##  ##  ##  ##        ##
##                                                                            ##
################################################################################

class PlateMapForDatabase(wx.Panel):
    """
    Panel containing a table (Wx.grid.Grid) for the map of the assay plate.
    """
    def __init__(self, notebook, tabname):
        """
        Initialises class attributes.
        
        Arguments:
            notebook -> parent object for wxPython GUI building. In this
                        case, the notebook that this panel will reside in.
            tabname -> gets assigned to self.Tabname. Reference to the
                       pnl_Project instance above this object (contains
                       any functions that might need to be called, objects
                       controlled, etc).
        """
        wx.Panel.__init__ (self, parent = notebook, id = wx.ID_ANY,
                           pos = wx.DefaultPosition, size = wx.DefaultSize,
                           style = wx.TAB_TRAVERSAL, name = wx.EmptyString)

        self.Tabname = tabname

        self.SetBackgroundColour(cs.BgUltraLight)

        # Start Building
        self.szr_Export = wx.BoxSizer(wx.VERTICAL)
        self.szr_Grid = wx.BoxSizer(wx.VERTICAL)

        # Prepare grid to populate later
        self.grd_PlateMap = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Grid.Add(self.grd_PlateMap, 1, wx.ALL|wx.EXPAND, 5)
        self.szr_Grid.Fit(self.grd_PlateMap)
        self.szr_Export.Add(self.szr_Grid, 1, wx.EXPAND, 5)

        # Button Bar
        self.szr_Export_ButtonBar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Export_Buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_Clipboard = btn.CustomBitmapButton(self, "Clipboard", 0, (130,25))
        self.btn_Clipboard.Bind(wx.EVT_BUTTON, self.CopyToClipboard)
        self.szr_Export_Buttons.Add(self.btn_Clipboard, 0, wx.ALL, 5)
        self.btn_Export = btn.CustomBitmapButton(self, "ExportToFile", 0, (104,25))
        self.btn_Export.Bind(wx.EVT_BUTTON, self.ExportToCSV)
        self.szr_Export_Buttons.Add(self.btn_Export, 0, wx.ALL, 5)
        self.szr_Export_ButtonBar.Add(self.szr_Export_Buttons, 0, wx.ALIGN_RIGHT, 5)
        self.szr_Export.Add(self.szr_Export_ButtonBar, 0, wx.EXPAND, 5)

        # Finalise
        self.SetSizer(self.szr_Export)
        self.Layout()

        # Binding
        self.grd_PlateMap.Bind(wx.EVT_KEY_DOWN, OnKeyPressGrid)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_SELECT_CELL, SingleSelection)
        self.grd_PlateMap.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenCopyOnlyContextMenu)

    def ExportToCSV(self, event):
        """
        Event handler. Exports data in dfr_DatabasePlateMap to csv.
        """
        fdlg = wx.FileDialog(self, "Save results as", wildcard="Comma separated files (*.csv)|*.csv", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .csv. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            try:
                self.Tabname.dfr_DatabasePlateMap.to_csv(str_SavePath)
            except PermissionError:
                msg.SavePermissionDenied()

    def CopyToClipboard(self, event):
        """
        Event handler. copies data in dfr_DatabasePlateMap to clipboard.
        """
        self.Tabname.dfr_DatabasePlateMap.to_clipboard(header=None, index=False)

    def PopulatePlateMapTab(self):
        """
        Populates tab from dataframe(s) in higher instance.
        Does this via running a second function in a thread to enable
        a progress bar dialog.
        """
        self.dlg_PlateMapProgress = GenericProgress(self, "Populating Table")
        self.dlg_PlateMapProgress.Show()
        thd_PopulatePlateMap = threading.Thread(target=self.PopulatePlateMapTab_thread, args=(), daemon=True)
        thd_PopulatePlateMap.start()

    def PopulatePlateMapTab_thread(self):
        """
        Gathers data from dataframe(s) to populate the grid/table on
        this panel.
        """
        self.Tabname.dfr_DatabasePlateMap = pd.DataFrame(columns=self.Tabname.lst_PlateMapHeaders)
        # Create Database dataframe in sections for each plate and append
        for i in range(len(self.Tabname.dfr_AssayData)):
            dfr_Partial = df.create_Database_frame_DSF_Platemap(self.Tabname.dfr_Details,self.Tabname.lst_PlateMapHeaders,
                self.Tabname.dfr_AssayData.iloc[i,5],self.Tabname.dfr_Layout.loc[i])
            frames = [self.Tabname.dfr_DatabasePlateMap, dfr_Partial]
            self.Tabname.dfr_DatabasePlateMap = pd.concat(frames, ignore_index=False)

        # Create grid:
        self.int_Samples = len(self.Tabname.dfr_DatabasePlateMap)
        self.Freeze()
        #self.grd_PlateMap = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # Grid
        self.grd_PlateMap.CreateGrid(self.int_Samples, len(self.Tabname.lst_PlateMapHeaders))
        self.grd_PlateMap.EnableEditing(False)
        self.grd_PlateMap.EnableGridLines(True)
        self.grd_PlateMap.EnableDragGridSize(False)
        self.grd_PlateMap.SetMargins(0, 0)
        # Columns
        self.grd_PlateMap.AutoSizeColumns()
        self.grd_PlateMap.EnableDragColMove(False)
        self.grd_PlateMap.EnableDragColSize(True)
        self.grd_PlateMap.SetColLabelSize(20)
        for i in range(len(self.Tabname.lst_PlateMapHeaders)):
            self.grd_PlateMap.SetColLabelValue(i,self.Tabname.lst_PlateMapHeaders[i])
        self.grd_PlateMap.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        self.grd_PlateMap.EnableDragRowSize(True)
        self.grd_PlateMap.SetRowLabelSize(30)
        self.grd_PlateMap.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Label Appearance
        # Cell Defaults
        self.grd_PlateMap.SetDefaultCellAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP)
        self.grd_PlateMap.SetGridLineColour(cs.BgMediumDark)
        self.grd_PlateMap.SetDefaultCellBackgroundColour(cs.BgUltraLight)
        # Populate grid:
        for idx_Sample in range(self.grd_PlateMap.GetNumberRows()):
            for col in range(self.grd_PlateMap.GetNumberCols()):
                self.grd_PlateMap.SetCellValue(idx_Sample,col,str(self.Tabname.dfr_DatabasePlateMap.iloc[idx_Sample,col]))
            self.dlg_PlateMapProgress.gauge.SetValue((idx_Sample/self.int_Samples)*200)

        self.grd_PlateMap.AutoSizeColumns()
        self.Thaw()
        self.dlg_PlateMapProgress.Destroy()
        self.Tabname.bol_PlateMapPopulated = True

    def Clear(self):
        """
        Clears the entire grid.
        """
        self.grd_PlateMap.Clear()

    def OpenCopyOnlyContextMenu(self, event):
        """
        Event handler. Opens context menu after right click on grid.
        """
        self.PopupMenu(CopyOnlyContextMenu(event, event.GetEventObject()))

###########################


class CopyOnlyContextMenu(wx.Menu):
    """
    Context menu to copy from the event generating  grid.
    """
    def __init__(self, rightclick, grid):
        super(CopyOnlyContextMenu, self).__init__()

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.Grid = grid
        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, self.Copy, self.mi_Copy)

    def Copy(self, event):
        """
        Event handler. Gets list of selected cells and copies the
        contents to clipboard.
        """
        lst_Selection = GetGridSelection(self.Grid)
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.Grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)


################################################################################################################################
##                                                                                                                            ##
##     #####  ##  ##   ####   #####   ######  #####     ######  ##  ##  ##  ##   #####  ######  ##   ####   ##  ##   #####    ##
##    ##      ##  ##  ##  ##  ##  ##  ##      ##  ##    ##      ##  ##  ### ##  ##        ##    ##  ##  ##  ### ##  ##        ##
##     ####   ######  ######  #####   ####    ##  ##    ####    ##  ##  ######  ##        ##    ##  ##  ##  ######   ####     ##
##        ##  ##  ##  ##  ##  ##  ##  ##      ##  ##    ##      ##  ##  ## ###  ##        ##    ##  ##  ##  ## ###      ##    ##
##    #####   ##  ##  ##  ##  ##  ##  ######  #####     ##       ####   ##  ##   #####    ##    ##   ####   ##  ##  #####     ##
##                                                                                                                            ##
################################################################################################################################

def OnKeyPressGrid(event):
    # based on first answer here:
    # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
    # by user Sinan Çetinkaya
    """
    Handles all key press events for the grids in this module.
    """
    # Ctrl+C or Ctrl+Insert
    obj_Grid = event.GetEventObject()
    if event.ControlDown() and event.GetKeyCode() in [67, 322]:
        lst_Selection = GetGridSelection(obj_Grid)
        if len(lst_Selection) == 0:
            lst_Selection = [[obj_Grid.SingleSelection[0], obj_Grid.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = obj_Grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    # Ctrl+A
    elif event.ControlDown() and event.GetKeyCode() == 65:
        obj_Grid.SelectAll()
    else:
        event.Skip()

def SingleSelection(event):
    """
    Event handlder.
    Sets SingleSelection property of cell (not standard in wx)
    to clicked cell to ensure it is part of the selection even
    if nothing else is selected.
    """
    event.GetEventObject().SingleSelection = (event.GetRow(), event.GetCol())

def GetGridSelection(obj_Grid):
    """
    Collects all selected cells of a grid as a list of coordinates.

    Arguments:
        obj_Grid -> wx.grid.Grid. The grid containing the selected cells.

    Returns:
        lst_Selection -> list. List of coordinates of selected cells.
    """
    # Selections are treated as blocks of selected cells
    lst_TopLeftBlock = obj_Grid.GetSelectionBlockTopLeft()
    lst_BotRightBlock = obj_Grid.GetSelectionBlockBottomRight()
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

def ProcessData(ProjectTab, dlg_Progress):
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
    ProjectTab.int_Samples = 0
    ProjectTab.SaveAssayDetails(bol_FromTabChange=False)
    dlg_Progress.lbx_Log.InsertItems(["Assay details saved"], dlg_Progress.lbx_Log.Count)
    
    # Perform sequence of checks before beginning processing
    if ProjectTab.bol_TransferLoaded == False:
        dlg_Progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.NoTransferLoaded()
        return None
    if ProjectTab.bol_LayoutDefined == False:
        dlg_Progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.NoLayoutDefined()
        return None
    if ProjectTab.bol_DataFilesAssigned == False:
        dlg_Progress.Destroy()
        ProjectTab.parent.Thaw()
        msg.NoDataFileAssigned()
        return None

    # Build dataframe that holds everything
    dlg_Progress.lbx_Log.InsertItems(["Start creating complete container dataframe"], dlg_Progress.lbx_Log.Count)
    ProjectTab.dfr_AssayData = df.get_CompleteContainer(ProjectTab.dfr_PlateAssignment,ProjectTab.str_DataPath,ProjectTab.dfr_TransferFile,ProjectTab.dfr_Exceptions,
        ProjectTab.dfr_Layout,ProjectTab.dfr_Details,dlg_Progress)

    # Catch any errors in processing -> df.get_CompleteContainer() returns None on any errors:
    if ProjectTab.dfr_AssayData is None:
        dlg_Progress.lbx_Log.InsertItems(["==============================================================="], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems(["DATA PROCESSING CANCELLED"], dlg_Progress.lbx_Log.Count)
        dlg_Progress.btn_X.Enable(True)
        dlg_Progress.btn_Close.Enable(True)
        return None

    # Re-set bool variables in case an analysis has been performed previously
    ProjectTab.bol_DataAnalysed = False
    ProjectTab.bol_ReviewsDrawn = False
    ProjectTab.bol_ResultsDrawn = False
    ProjectTab.bol_ELNPlotsDrawn = False
    ProjectTab.bol_ExportPopulated = False

    # Clear all lists, fields, grids, plots to populate with (new) results
    if hasattr(ProjectTab, "tab_Review"):
        ProjectTab.tab_Review.lbc_Plates.DeleteAllItems()
    if hasattr(ProjectTab, "lbc_Samples"):
        ProjectTab.lbc_Samples.DeleteAllItems()
    if hasattr(ProjectTab, "tab_Export"):
        try: ProjectTab.tab_Export.Clear()
        except: None

    # Populate tabs if existing and enable buttons:
    if hasattr(ProjectTab, "tab_Review") == True:
        dlg_Progress.lbx_Log.InsertItems(["Populating 'Review plates' tab"], dlg_Progress.lbx_Log.Count)
        ProjectTab.tab_Review.Populate(noreturn = True)
        if hasattr(ProjectTab, "lbc_Plates") == True:
            ProjectTab.lbc_Plates.Select(0)
        ProjectTab.bol_ReviewsDrawn = True
    if hasattr(ProjectTab, "tab_Results") == True:
        dlg_Progress.lbx_Log.InsertItems(["Populating 'Results' tab"], dlg_Progress.lbx_Log.Count)
        ProjectTab.PopulateResultsTab()
        ProjectTab.bol_ResultsDrawn = True
    ProjectTab.tabs_Analysis.EnableAll(True)
    ProjectTab.tabs_Analysis.EnablePlateMap(ProjectTab.bol_PlateID)

    # Final entries in progress dialog:
    dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
    dlg_Progress.lbx_Log.InsertItems(["==============================================================="], dlg_Progress.lbx_Log.Count)
    dlg_Progress.lbx_Log.InsertItems(["Data processing completed"], dlg_Progress.lbx_Log.Count)
    dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
    str_Duration = str(round(perf_counter()-time_start,0))
    dlg_Progress.lbx_Log.InsertItems(["Time elapsed: " + str_Duration + "s"], dlg_Progress.lbx_Log.Count)

    # Pop up notification if neither main window nor progress dialog are active window:
    if ProjectTab.parent.IsActive() == False and dlg_Progress.IsActive() == False:
        try:
            # This should only work on Windows
            ProjectTab.parent.icn_Taskbar.ShowBalloon(title="BBQ",text="Analysis completed!",msec=1000)
        except:
            msg_Popup = wx.adv.NotificationMessage(title="BBQ", message="Analysis completed!")
            try: msg_Popup.SetIcon(ProjectTab.parent.BBQIcon)
            except: None
            msg_Popup.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    
    # Finish up
    ProjectTab.bol_DataAnalysed = True
    dlg_Progress.btn_X.Enable(True)
    dlg_Progress.btn_Close.Enable(True)