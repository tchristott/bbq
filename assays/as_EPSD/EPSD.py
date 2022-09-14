# Import my own libraries
import lib_customplots as cp
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_tabs as tab
import lib_platefunctions as pf

# Import libraries for GUI
import wx
import wx.xrc

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")

# Import other libraries
import pandas as pd
import numpy as np
from datetime import datetime
import os


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

    def __init__(self, parent):
        wx.Panel.__init__ (self,
                           parent.sbk_WorkArea,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.Size(1000,750),
                           style = wx.EmptyString,
                           name = "pnl_Project")

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Tabs = cs.BgUltraLight
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent

        # Initialise instance wide variables with default values
        self.Title = u"Single concentration screen"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "single_dose"
        self.str_Shorthand = "EPSD"
        self.AssayPath = os.path.dirname(os.path.realpath(__file__))
        self.bol_AssayDetailsCompleted = False
        self.bol_AssayDetailsChanged = False
        self.bol_LayoutDefined = False
        self.bol_TransferLoaded = False
        self.bol_DataFilesAssigned = False
        self.bol_DataFilesUpdated = False
        self.bol_DataAnalysed = False
        self.bol_ReviewsDrawn = False
        self.bol_ResultsDrawn = False
        self.bol_ELNPlotsDrawn = False
        self.bol_ExportPopulated = False
        self.bol_PreviouslySaved = False
        self.bol_GlobalLayout = True
        self.bol_PlateID = False
        self.bol_PlateMapPopulated = False
        self.dfr_Details = pd.DataFrame()
        self.str_DatafileExtension = ".xls"
        self.str_SaveFilePath = ""
        self.str_DataPath = ""
        self.str_TransferPath = ""
        self.SampleSource = "echo"
        self.Device = "pherastar"

        self.dfr_Layout = pd.DataFrame()

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

        lst_AssayTypes = [ u"HTRF", u"AlphaScreen", u"TAMRA FP", u"ADP-Glo", u"AMP-Glo", u"UDP-Glo", u"UMP-Glo" ]
        self.tab_Details = tab.AssayDetailsGeneric(self.tabs_Analysis.sbk_Notebook,
                                                   tabname = self,
                                                   assaytypes = lst_AssayTypes,
                                                   date = True,
                                                   ELN = True)
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", True)

        ##### ###   ##  #  #  ### #### #### ###    # ###   ##  #####  ##
          #   #  # #  # ## # #    #    #    #  #   # #  # #  #   #   #  #
          #   ###  #### # ##  ##  ###  ###  ###   #  #  # ####   #   ####
          #   #  # #  # #  #    # #    #    #  # #   #  # #  #   #   #  #
          #   #  # #  # #  # ###  #    #### #  # #   ###  #  #   #   #  # #####################################################################################

        self.tab_Files = tab.FileSelection(self.tabs_Analysis.sbk_Notebook,
                                           tabname = self,
                                           data = u"*.xls",
                                           normalise = True,
                                           layouts = False)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Transfer and Data Files", True)

        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  ##############

        self.tab_Review = tab.Review(self.tabs_Analysis.sbk_Notebook, 
                                     tabname = self,
                                     assaycategory = self.str_Shorthand,
                                     plots = ["Heat Map", "Scatter Plot"],
                                     sidebar = [""])
        self.tabs_Analysis.AddPage(self.tab_Review, u"Review Plates", False)

        ###  ####  ### #  # #  #####  ###
        #  # #    #    #  # #    #   #
        ###  ###   ##  #  # #    #    ##
        #  # #       # #  # #    #      #
        #  # #### ###   ##  #### #   ###  ###############################################

        # Start Building
        self.tab_Results = wx.Panel(self.tabs_Analysis.sbk_Notebook,
                                    style = wx.TAB_TRAVERSAL)
        self.tab_Results.SetBackgroundColour(clr_Tabs)
        self.szr_Results = wx.BoxSizer(wx.VERTICAL)

        self.bSizer12 = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot Panel
        self.pnl_SummaryPlot = cp.ScatterPlotPanel(parent = self.tab_Results,
                                                   size = wx.Size(900,450),
                                                   tabname = self,
                                                   title = u"Summary Plot",
                                                   xlabel = u"Samples",
                                                   ylabel = u"Per-cent inhibition",
                                                   buttons = True,
                                                   threshold = 60,
                                                   lines = [0,100],
                                                   limits = [-20,120])
        self.szr_Plot.Add(self.pnl_SummaryPlot, 0, wx.ALL, 5)
        self.bSizer12.Add(self.szr_Plot, 0, 0, 5)
        self.szr_Results.Add(self.bSizer12, 0, wx.EXPAND, 5)
        
        # Finalise
        self.tab_Results.SetSizer(self.szr_Results)
        self.tab_Results.Layout()
        self.szr_Results.Fit(self.tab_Results)
        self.tabs_Analysis.AddPage(self.tab_Results, u"Summary", False)


        #### #  # ###   ##  ###  #####
        #    #  # #  # #  # #  #   #
        ##    ##  ###  #  # ###    #
        #    #  # #    #  # #  #   #
        #### #  # #     ##  #  #   # ##########################################################################################################################

        self.lst_Headers_ASHTRF = ["Experiment Type","Purification ID","Protein Concentration (uM)","Peptide ID","Global Compound ID",
            "Peptide Concentration (uM)","Solvent","Solvent Concentration (%)","Buffer","Compound Incubation Time (min)","Peptide Incubation Time (min)",
            "Bead Incubation Time (min)","Incubation Temperatures (°C)","Log IC50","Standard Error in Log IC50","IC50 (uM)","IC50 Upper 95% CI","IC50 Lower 95% CI",
            "Hill Slope","Curve","Bottom for curve fitting","Top for curve fitting","R²","Data Quality","Comments on curve classification and definitions",
            "Enzyme Reference","Enzyme Reference Error","Compound Concentration 1 (uM)","Compound Concentration 1 Inhibition (%)","Compound Concentration 1 Error (%)",
            "Compound Concentration 2 (uM)","Compound Concentration 2 Inhibition (%)","Compound Concentration 2 Error (%)","Compound Concentration 3 (uM)",
            "Compound Concentration 3 Inhibition (%)","Compound Concentration 3 Error (%)","Compound Concentration 4 (uM)","Compound Concentration 4 Inhibition (%)",
            "Compound Concentration 4 Error (%)","Compound Concentration 5 (uM)","Compound Concentration 5 Inhibition (%)","Compound Concentration 5 Error (%)",
            "Compound Concentration 6 (uM)","Compound Concentration 6 Inhibition (%)","Compound Concentration 6 Error (%)","Compound Concentration 7 (uM)",
            "Compound Concentration 7 Inhibition (%)","Compound Concentration 7 Error (%)","Compound Concentration 8 (uM)","Compound Concentration 8 Inhibition (%)",
            "Compound Concentration 8 Error (%)","Compound Concentration 9 (uM)","Compound Concentration 9 Inhibition (%)","Compound Concentration 9 Error (%)",
            "Compound Concentration 10 (uM)","Compound Concentration 10 Inhibition (%)","Compound Concentration 10 Error (%)","Compound Concentration 11 (uM)",
            "Compound Concentration 11 Inhibition (%)","Compound Concentration 11 Error (%)","Compound Concentration 12 (uM)","Compound Concentration 12 Inhibition (%)",
            "Compound Concentration 12 Error (%)","Compound Concentration 13 (uM)","Compound Concentration 13 Inhibition (%)","Compound Concentration 13 Error (%)",
            "Compound Concentration 14 (uM)","Compound Concentration 14 Inhibition (%)","Compound Concentration 14 Error (%)","Compound Concentration 15 (uM)",
            "Compound Concentration 15 Inhibition (%)","Compound Concentration 15 Error (%)","Compound Concentration 16 (uM)","Compound Concentration 16 Inhibition (%)",
            "Compound Concentration 16 Error (%)","No Protein Control","No Protein Control Error","No Peptide Control Activity","No Peptide Control Error",
            "ZPrime","ZPrimeRobust","Solvent/Control","Buffer/Control","DateOfExperiment","ELN Experiment ID","Comments"]
        self.lst_Headers_ActAssay = ["ActAssay Type","Purification ID","ActAssay Enzyme Concentration (nM)","Substrate 1","SGC Global Compound ID (Batch) (ActAssay Substrate Compound)",
            "ActAssay Substrate Concentration (uM)","Substrate 2","SGC Global Compound ID 2 (Batch)","ActAssay Substrate 2 Concentration (uM)","Solvent","Solvent Concentration(%)",
            "Buffer","Assay Time (mins)","Reagent 1 Time","Reagent 2 Time","ActAssay Incubation Temperature (C)","Enzyme Reference","Enzyme Reference Error (%)","No Protein Control",
            "No Protein Control Error","Solvent Control Inhibition 1 (%)","SGC Global Compound ID (Batch) (ActAssay Inhibitor Compound)","Log IC50","Standard Error Log IC50","ActAssay IC50 (uM)",
            "Curve Fit Upper 95%","Curve Fit Lower 95%","Hill Slope","Curve Bottom","Curve Top","r2","Curve Comments",
            "Compound Concentration 1(M)","Compound Concentration 1 Inhibition (%)","Compound Concentration 1 Error (%)",
            "Compound Concentration 2(M)","Compound Concentration 2 Inhibition (%)","Compound Concentration 2 Error (%)",
            "Compound Concentration 3(M)","Compound Concentration 3 Inhibition (%)","Compound Concentration 3 Error (%)",
            "Compound Concentration 4(M)","Compound Concentration 4 Inhibition (%)","Compound Concentration 4 Error (%)",
            "Compound Concentration 5(M)","Compound Concentration 5 Inhibition (%)","Compound Concentration 5 Error (%)",
            "Compound Concentration 6(M)","Compound Concentration 6 Inhibition (%)","Compound Concentration 6 Error (%)",
            "Compound Concentration 7(M)","Compound Concentration 7 Inhibition (%)","Compound Concentration 7 Error (%)",
            "Compound Concentration 8(M)","Compound Concentration 8 Inhibition (%)","Compound Concentration 8 Error (%)",
            "Compound Concentration 9(M)","Compound Concentration 9 Inhibition (%)","Compound Concentration 9 Error (%)",
            "Compound Concentration 10(M)","Compound Concentration 10 Inhibition (%)","Compound Concentration 10 Error (%)",
            "Compound Concentration 11(M)","Compound Concentration 11 Inhibition (%)","Compound Concentration 11 Error (%)",
            "Compound Concentration 12(M)","Compound Concentration 12 Inhibition (%)","Compound Concentration 12 Error (%)",
            "Compound Concentration 13(M)","Compound Concentration 13 Inhibition (%)","Compound Concentration 13 Error (%)",
            "Compound Concentration 14(M)","Compound Concentration 14 Inhibition (%)","Compound Concentration 14 Error (%)",
            "Compound Concentration 15(M)","Compound Concentration 15 Inhibition (%)","Compound Concentration 15 Error (%)",
            "Compound Concentration 16(M)","Compound Concentration 16 Inhibition (%)","Compound Concentration 16 Error (%)",
            "ActAssay ELN Reference","ActAssay Comments","Date ActAssay Record Created","Creator of ActAssay Record"]
        self.lst_Headers = self.lst_Headers_ASHTRF
        self.tab_Export = tab.ExportToDatabase(self.tabs_Analysis.sbk_Notebook, self)
        self.tabs_Analysis.AddPage(self.tab_Export, u"Export results to Database", False)

        ##########################################################################################################

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
        ###  # #  # ###  # #  #  ##  #############################################################################

        # Highest level events:
        self.tabs_Analysis.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)


    def __del__(self):
        pass

    ##    ##  ######  ######  ##  ##   ####   #####    #####
    ###  ###  ##        ##    ##  ##  ##  ##  ##  ##  ##
    ########  ####      ##    ######  ##  ##  ##  ##   ####
    ## ## ##  ##        ##    ##  ##  ##  ##  ##  ##      ##
    ##    ##  ######    ##    ##  ##   ####   #####   #####

    def ChangeTab(self, btn_Caller):
        """
        Gets called by tab buttons to see if we're allowd to change tabs.
        """
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
        Event handler. Gets called when tabs in the SimpleBook change.
        Checks whether the tabs need populating.
        """
        int_NewTab = self.tabs_Analysis.GetSelection()
        if int_NewTab == 2:
            # going to review tab
            if self.bol_ReviewsDrawn == False:
                self.bol_ResultsDrawn = self.tab_Review.Populate()
        elif int_NewTab == 3:
            # going to results tab
            if self.bol_ResultsDrawn == False:
                self.PopulateResultsTab()
        elif int_NewTab == 4:
            # going to export tab
            if self.bol_ExportPopulated == False:
                self.bol_ExportPopulated = self.tab_Export.Populate()

    def PopulateFromFile(self, dfr_LoadedDetails, lst_LoadedBoolean, dfr_Loaded, lst_Paths):
        """
        Gets called by main window to populate all tabs after loading a file.

        Arguments:
            dfr_LoadedDetails -> pandas dataframe. Contains all metadata/assay details
            lst_LoadedBoolean -> list of boolean values.
            dfr_Loaded -> pandas dataframe. Contains assay data (raw data and results)
            lst_Paths -> list of file paths
        """
        self.dfr_AssayData = dfr_Loaded

        # Assay Details
        self.dfr_Details = dfr_LoadedDetails
        self.str_AssayType = self.dfr_Details.loc["AssayType","Value"]
        for i in range(self.tab_Details.lbx_AssayType.GetCount()):
            if self.dfr_Details.loc["AssayType","Value"] == self.tab_Details.lbx_AssayType.GetString(i):
                self.tab_Details.lbx_AssayType.SetSelection(i)
                break
        self.tab_Details.txt_PurificationID.SetValue(self.dfr_Details.loc["PurificationID","Value"])
        self.tab_Details.txt_ProteinConc.SetValue(str(self.dfr_Details.loc["ProteinConcentration","Value"]))
        self.tab_Details.txt_Solvent.SetValue(self.dfr_Details.loc["Solvent","Value"])
        self.tab_Details.txt_Percent.SetValue(str(self.dfr_Details.loc["SolventConcentration","Value"]))
        self.tab_Details.txt_Buffer.SetValue(self.dfr_Details.loc["Buffer","Value"])
        self.tab_Details.txt_ELN.SetValue(self.dfr_Details.loc["ELN","Value"])
        # self.str_AssayVolume = str(self.dfr_Details.loc["AssayType","Value"]) # in nL
        self.str_DatafileExtension = self.dfr_Details.loc["DataFileExtension","Value"]
        self.SampleSource = self.dfr_Details.loc["SampleSource","Value"]
        # Backwards compatibility wild older save files that do not have newer additions in the assay details:
        try:
            self.Device = self.dfr_Details.loc["Device","Value"]
        except:
            self.Device = "pherastar"
            self.dfr_Details.at["Device","Value"] = self.Device
        try:
            self.Date = self.dfr_Details.loc["Date","Value"]
            self.Date = wx.DateTime.FromDMY(int(self.Date[8:10]), int(self.Date[5:7]), int(self.Date[:4]))
            self.tab_Details.DatePicker.SetValue(self.Date)
        except:
            self.dfr_Details.at["Date","Value"] = self.Date

        # Update boolean variables
        self.bol_AssayDetailsChanged = False # lst_LoadedBoolean[0]
        self.bol_AssayDetailsCompleted = lst_LoadedBoolean[1]
        self.bol_DataFilesAssigned = lst_LoadedBoolean[2]
        self.bol_DataFilesUpdated = False # lst_LoadedBoolean[3]
        self.bol_DataAnalysed = lst_LoadedBoolean[4]
        self.bol_ELNPlotsDrawn = lst_LoadedBoolean[5]
        if self.bol_ELNPlotsDrawn == True:  # Does not apply to single shots, but we will leave it in in case I want to unify the different functions into one
            self.tab_ELNPlots.PopulatePlotsTab()
        self.bol_ExportPopulated = lst_LoadedBoolean[6]
        if self.bol_ExportPopulated == True:
            self.tab_Export.Populate(noreturn = True)
        self.bol_ResultsDrawn = lst_LoadedBoolean[7]
        if self.bol_ResultsDrawn == True:
            self.PopulateResultsTab()
        self.bol_ReviewsDrawn = lst_LoadedBoolean[8]
        if self.bol_ReviewsDrawn == True:
            self.tab_Review.Populate(noreturn = True)
        self.bol_TransferLoaded = lst_LoadedBoolean[9]
        self.bol_GlobalLayout = lst_LoadedBoolean[10]
        self.bol_PlateID = lst_LoadedBoolean[11]
        self.bol_PlateMapPopulated = lst_LoadedBoolean[12]
        # And of course this has been previously saved since we are loading it from a file
        self.bol_PreviouslySaved = True

        # Populate transfer/data file tab
        for i in range(len(self.dfr_AssayData)):
            self.tab_Files.lbc_Transfer.InsertItem(i,self.dfr_AssayData.iloc[i,0])
            self.tab_Files.lbc_Transfer.SetItem(i,1,str(self.dfr_AssayData.iloc[i,2]))
            self.tab_Files.lbc_Transfer.SetItem(i,2,self.dfr_AssayData.iloc[i,3])
        #lst_DataFiles = os.listdir(lst_Paths[1])
        # Select correct file extension:
        #str_Extension = ".xls"
        # Go through directory, get each file with correct extension, compary to list already assigned. If not assigned, add to lbc_Data
        #for i in range(len(lst_DataFiles)):
        #    if lst_DataFiles[i].find(str_Extension) != -1:
        #        bol_Found = False
        #        for j in range(self.lbc_Transfer.GetItemCount()):
        #            if str(lst_DataFiles[i]) == self.lbc_Transfer.GetItemText(j,2):
        #                bol_Found = True
        #                break
        #        if bol_Found == False:
        #            self.tab_Files.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
        # Add paths to filepickers
        self.tab_Files.fpk_Transfer.SetPath(lst_Paths[0])
        self.tab_Files.fpk_Data.SetPath(lst_Paths[1])
        self.str_DataPath = lst_Paths[1]

        # recreate single dfr_Layout
        self.dfr_Layout = pd.DataFrame(index=range(len(dfr_Loaded)),
                                       columns=["PlateID","ProteinNumerical",
                                                "PurificationID","Concentration",
                                                "WellType"])
        for idx_Plate in range(len(self.dfr_Layout)):
            self.dfr_Layout.at[idx_Plate,"PlateID"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"PlateID"]
            self.dfr_Layout.at[idx_Plate,"ProteinNumerical"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"ProteinNumerical"]
            self.dfr_Layout.at[idx_Plate,"PurificationID"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"PurificationID"]
            self.dfr_Layout.at[idx_Plate,"Concentration"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"Concentration"]
            self.dfr_Layout.at[idx_Plate,"WellType"] = dfr_Loaded.loc[idx_Plate,"Layout"].loc[0,"WellType"]
        self.bol_LayoutDefined = True

        self.tabs_Analysis.EnableAll(True)

    def ProcessData(self, dlg_Progress):
        """
        This is purely a wrapper function. Some modules might straight up
        call the default ProcessData() from lib_tabs, others might need
        their own.
        """
        tab.ProcessData(self, dlg_Progress)

    ####  ##### #####  ###  # #      ####
    #   # #       #   #   # # #     #
    #   # ###     #   ##### # #      ###
    #   # #       #   #   # # #         #
    ####  #####   #   #   # # ##### ####
    
    def SaveAssayDetails(self, bol_FromTabChange = False):
        """
        Saves assay details to dataframe. If the saving is triggered by
        a tab change, and the data has already been analysed, the user
        is asked if they want to re-analyse the data.

        Arguments:
            bol_TabChange -> boolean. Set to False if function is 
                             not called from a tab change in the
                             notbeook.
        """
        # Write values of fields into variables for later use
        self.str_AssayType = self.tab_Details.lbx_AssayType.GetString(self.tab_Details.lbx_AssayType.GetSelection())
        self.str_AssayCategory = "single_dose"
        if self.tab_Details.chk_Activity.Value == True:
            self.str_AssayCategory = self.str_AssayCategory + "_activity"
        self.str_DatafileExtension = ".xls"
        self.str_Purification = self.tab_Details.txt_PurificationID.GetLineText(0)
        self.int_ProteinConc = self.tab_Details.txt_ProteinConc.GetLineText(0)
        self.str_PeptideID = self.tab_Details.txt_PeptideID.GetLineText(0)
        self.int_PeptideConc = self.tab_Details.txt_PeptideConc.GetLineText(0)
        self.str_Solvent = self.tab_Details.txt_Solvent.GetLineText(0)
        self.int_SolventPercent = self.tab_Details.txt_Percent.GetLineText(0)
        # Get buffer, needs special consideration since TextCtrl is multiline
        int_Lines = self.tab_Details.txt_Buffer.GetNumberOfLines()
        self.str_Buffer = ""
        for i in range(int_Lines):
            self.str_Buffer = self.str_Buffer + self.tab_Details.txt_Buffer.GetLineText(i)
        self.str_ELN = self.tab_Details.txt_ELN.GetLineText(0)
        self.str_AssayVolume= str(20 * 1000) # convert to nL
        self.SampleSource = "echo"
        self.Date = self.tab_Details.DatePicker.GetValue()
        self.Date = str(self.Date.GetYear()) + "-" + str(self.Date.GetMonth()+1) + "-" + str(self.Date.GetDay()) # GetMonth is indexed from zero!!!!!
        self.Date = datetime.strptime(self.Date,"%Y-%m-%d").strftime("%Y-%m-%d")
        # Include checks so that user does not leave things empty
        dfr_Details_New = pd.DataFrame(data={"Value":[self.str_AssayType,
                                                      self.str_AssayCategory,
                                                      "EPSD",
                                                      self.str_Purification,
                                                      self.int_ProteinConc,
                                                      self.str_PeptideID,
                                                      self.int_PeptideConc,
                                                      self.str_Solvent,
                                                      self.int_SolventPercent,
                                                      self.str_Buffer,
                                                      self.str_ELN,
                                                      self.str_AssayVolume,
                                                      self.str_DatafileExtension,
                                                      self.SampleSource,
                                                      self.Device,
                                                      self.Date]},
                                       index=["AssayType",
                                              "AssayCategory",
                                              "Shorthand",
                                              "PurificationID",
                                              "ProteinConcentration",
                                              "PeptideID",
                                              "PeptideConcentration",
                                              "Solvent",
                                              "SolventConcentration",
                                              "Buffer",
                                              "ELN",
                                              "AssayVolume",
                                              "DataFileExtension",
                                              "SampleSource",
                                              "Device",
                                              "Date"])

        # check whether details have been changed and if so, update variables:
        if self.bol_AssayDetailsCompleted == True:
            int_CheckSum = 0
            for i in range(dfr_Details_New.shape[0]):
                if dfr_Details_New.iloc[i,0]!= self.dfr_Details.iloc[i,0]:
                    int_CheckSum += 1
            if int_CheckSum != 0:
                self.dfr_Details = dfr_Details_New
                self.bol_AssayDetailsChanged = True
        
        # Check that all fields have been filled out
        int_CheckSum = 0
        for i in range(dfr_Details_New.shape[0]):
            if dfr_Details_New.iloc[i,0] == "":
                int_CheckSum += 1
        if int_CheckSum == 0:
            self.dfr_Details = dfr_Details_New
            bol_Details = True
        else:
            bol_Details = False

        if self.str_AssayCategory.find("activity") != -1 or self.str_AssayType.find("Glo") != -1:
            self.lst_Headers = self.lst_Headers_ActAssay

        if bol_Details == True:
            self.bol_AssayDetailsCompleted = True
            # Update details in dfr_Database and export tab, if applicable
            if self.bol_ExportPopulated == True:
                for idx_List in range(self.tab_Export.grd_Database.GetNumberRows()):
                    # lbc_Database
                    self.tab_Export.grd_Database.SetCellValue(idx_List,0,self.str_AssayType)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,1,self.str_Purification)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,2,str(float(self.int_ProteinConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,3,self.str_PeptideID)
                    # omitted
                    self.tab_Export.grd_Database.SetCellValue(idx_List,5,str(float(self.int_PeptideConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,6,self.str_Solvent)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,7,str(self.int_SolventPercent))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,8,self.str_Buffer)
                    # dfr_Database
                    self.dfr_Database.iloc[idx_List,0] = self.str_AssayType
                    self.dfr_Database.iloc[idx_List,1] = self.str_Purification
                    self.dfr_Database.iloc[idx_List,2] = float(self.int_ProteinConc)/1000
                    self.dfr_Database.iloc[idx_List,3] = self.str_PeptideID
                    # omitted
                    self.dfr_Database.iloc[idx_List,5] = float(self.int_PeptideConc)/1000
                    self.dfr_Database.iloc[idx_List,6] = self.str_Solvent
                    self.dfr_Database.iloc[idx_List,7] = self.int_SolventPercent
                    self.dfr_Database.iloc[idx_List,8] = self.str_Buffer
        else:
            msg.IncompleteDetails()
            self.tabs_Analysis.SetSelection(0)

        # Data already analysed but assay details changed? Offer user chance to re-analyse
        if bol_FromTabChange == True:
            if self.bol_DataAnalysed == True and self.bol_AssayDetailsChanged == True:
                if msg.QueryReanalysis() == True:
                    self.parent.AnalyseData()

    
    ####  ##### #   # # ##### #     #
    #   # #     #   # # #     #     #
    ####  ###   #   # # ###   #     #
    #   # #      # #  # #     #  #  #
    #   # #####   #   # ####   ## ##

    def PrepareHeatMap(self, idx_Plate):
        """
        Prepares dataframe for heatmap plot on review tab.

        Arguments:
            idx_Plate -> integer. Datframe index of plate to be displayed
                         on plot.
        """
        int_PlateFormat = len(self.dfr_AssayData.loc[idx_Plate,"RawDataFrame"])
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        for i in range(len(dfr_Heatmap)):
            dfr_Heatmap.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Heatmap.loc[i,"Value"] = self.dfr_AssayData.loc[idx_Plate,"RawDataFrame"].iloc[i,1]
            if self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "b":
                dfr_Heatmap.loc[i,"SampleID"] = "Buffer"
            elif self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "r":
                dfr_Heatmap.loc[i,"SampleID"] = "Control"
            elif self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "d":
                dfr_Heatmap.loc[i,"SampleID"] = "Solvent"
            else:
                dfr_Heatmap.loc[i,"SampleID"] = ""
        # This is the bottleneck
        for idx_Sample in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].index:
            for conc in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Locations"])):
                for rep in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Locations"][conc])):
                    dfr_Heatmap.loc[int(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Locations"][conc][rep]),"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
        return dfr_Heatmap

    def PrepareScatterPlot(self, idx_Plate):
        """
        Prepares dataframe for scatter plot on review tab.

        Arguments:
            idx_Plate -> integer. Datframe index of plate to be displayed
                         on plot.
        """
        lst_SampleIDs = []
        lst_Value = []
        lst_ValueSEM = []
        lst_Concentrations = []
        for idx_Sample in range(len(self.dfr_AssayData.iloc[idx_Plate,5])):
            # There for single dose screens there should obviously only be one concentration
            lst_SampleIDs.append(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"])
            lst_Value.append(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][0])
            lst_ValueSEM.append(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][0])
            lst_Concentrations.append(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][0])
        return pd.DataFrame(data={"SampleID":lst_SampleIDs,
                                  "Value":lst_Value,
                                  "ValueSEM":lst_ValueSEM,
                                  "Concentration":lst_Concentrations})

    ####  #####  #### #    # #     #####  ####
    #   # #     #     #    # #       #   #
    ####  ###    ###  #    # #       #    ###
    #   # #         # #    # #       #       #
    #   # ##### ####   ####  #####   #   ####

    def PopulateResultsTab(self):
        """
        Populates Results tab with results of analysis.
        """
        dfr_Summary = pd.DataFrame(columns=["SampleID","Value","ValueSEM","Concentration"])
        for idx_Plate in range(len(self.dfr_AssayData)):
            for idx_Sample in range(len(self.dfr_AssayData.iloc[idx_Plate,5])):
                lst_Concentrations = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"]
                dfr_SampleReturn = pd.DataFrame(columns=["SampleID","Value","ValueSEM","Concentration"],index=range(len(lst_Concentrations)))
                for conc in range(len(lst_Concentrations)):
                    dfr_SampleReturn.loc[conc,"SampleID"] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
                    dfr_SampleReturn.loc[conc,"Value"] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][conc]
                    dfr_SampleReturn.loc[conc,"ValueSEM"] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][conc]
                    dfr_SampleReturn.loc[conc,"Concentration"] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][conc]
                dfr_Summary = pd.concat([dfr_Summary, dfr_SampleReturn])
        dfr_Summary = dfr_Summary.reset_index()
        self.pnl_SummaryPlot.Input = dfr_Summary
        self.pnl_SummaryPlot.Draw()
        self.bol_ResultsDrawn = True
