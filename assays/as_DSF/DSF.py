# Import my own libraries

import lib_datafunctions as df
import lib_customplots as cp
import lib_platefunctions as pf
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_tabs as tab
import lib_platelayoutmenus as plm
import lib_customplots as cp
import lib_tooltip as tt
from lib_progressdialog import GenericProgress
from lib_custombuttons import IconTabButton, CustomBitmapButton

# Import libraries for GUI
import wx
import wx.xrc
import wx.grid
import wx.adv

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure

# Import other libraries
import os
import pandas as pd
import numpy as np
import threading
from datetime import datetime


##########################################################################
##                                                                      ##
##    #####    #####  ######          #####   ##       ####   ######    ##
##    ##  ##  ##      ##              ##  ##  ##      ##  ##    ##      ##
##    ##  ##   ####   #####   ######  #####   ##      ##  ##    ##      ##
##    ##  ##      ##  ##              ##      ##      ##  ##    ##      ##
##    #####   #####   ##              ##      ######   ####     ##      ##
##                                                                      ##
##########################################################################

class DSFPlotPanel(wx.Panel):
    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Canvas = wx.BoxSizer(wx.VERTICAL)
        self.szr_Canvas.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.12, right=0.99, top=self.Top, bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.SetSizer(self.szr_Canvas)
        self.Input = None
        self.Tm = None
        self.Normalised = False
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.SampleID = self.Input["SampleID"]
        self.figure.clear() # clear and re-draw function
        self.fluo, self.deri = self.figure.subplots(nrows=2,ncols=1, sharex=True, gridspec_kw={"height_ratios":[3,1],"hspace":0.0})
        # Actual Plot
        if self.Normalised == False:
            self.Tm = self.Input["RawInflections"][0]
                        # Do not really need to normalise, but might be useful for comparison.
            # Take out the test for "DoFit"
            self.fluo.plot(self.Input["Temp"], self.Input["Fluo"], label="Raw fluorescence", color="#872154")
            self.fluo.set_ylabel("Fluorescence signal in AU")
            self.deri.plot(self.Input["Temp"], self.Input["RawDeriv"], label="Derivative", color="#ddcc77")
        else:
            self.Tm = self.Input["NormInflections"][0]
            self.fluo.plot(self.Input["Temp"], self.Input["Norm"], label="Normalised fluorescence", color="#872154")
            self.fluo.set_ylabel("Normalised Fluorescence")
            self.fluo.set_ylim([-0.1,1.1])
            self.deri.plot(self.Input["Temp"], self.Input["NormDeriv"], label="Derivative", color="#ddcc77")
        self.fluo.axvline(self.Tm,0,1,linestyle="--",linewidth=1.0,color="grey")
        self.deri.axvline(self.Tm,0,1,linestyle="--",linewidth=1.0,color="grey")
        self.deri.set_ylabel("Derivative")
        self.deri.set_xlabel("Temperature (" + chr(176) + "C)") # degree symbol!
        self.fluo.set_title(self.SampleID)
        #self.fluo.legend()
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.draw()
        self.Thaw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        if self.Normalised == False:
            pd.DataFrame(data={"Temperature":self.Input["Temp"],"RawFluorescence":self.Input["Fluo"],
                "Derivative":self.Input["RawDeriv"]}).to_clipboard(header=True, index=False)
        else:
            pd.DataFrame(data={"Temperature":self.Input["Temp"],"NormalisedFluorescence":self.Input["Norm"],
                "Derivative":self.Input["NormDeriv"]}).to_clipboard(header=True, index=False)

class DSFDetailPlot(wx.Panel):
    def __init__(self, parent, PanelSize):
        wx.Panel.__init__(self, parent, size=wx.Size(PanelSize))
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100) #figsze=(5,4.5)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Canvas = wx.BoxSizer(wx.VERTICAL)
        self.szr_Canvas.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Canvas)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.23, right=0.9, top=0.89 , bottom=0.21)
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self, str_Well, str_SampleID, lst_Temp, lst_Fluo, lst_Fit, bol_DoFit):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        if self.canvas:
            self.canvas.Destroy()
            self.canvas = FigureCanvas(self, -1, self.figure)
            self.szr_Canvas = wx.BoxSizer(wx.VERTICAL)
            self.szr_Canvas.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
            self.SetSizer(self.szr_Canvas)
            self.Fit()
            self.ax = self.figure.add_subplot()
            #self.figure.subplots_adjust(left=0.23, right=0.9, top=0.89 , bottom=0.21)
            #self.figure.set_facecolor(cs.BgUltraLightHex)
        # Actual Plot
        self.ax.plot(lst_Temp, lst_Fluo, label="Fluorescence", color="#872154")
        if bol_DoFit == True:
            self.ax.plot(lst_Temp, lst_Fit, label="Fit", color="#ddcc77")
        self.ax.set_title(str_Well + ": " + str_SampleID)
        self.ax.title.set_size(8)
        self.ax.tick_params(axis="x", labelsize=8)
        self.ax.tick_params(axis="y", labelsize=8)
        self.ax.set_xlabel("Temperature (" + chr(176) + "C)") # degree symbol!
        self.ax.set_xticks([30,40,50,60,70,80,90])
        self.ax.xaxis.label.set_size(8)
        self.ax.set_ylabel("Fluorescence (AU)")
        self.ax.yaxis.label.set_size(8)
        self.Thaw()

########################################################################################
##                                                                                    ##
##    ##    ##  ##  ##  ##      ######  ##          #####   ##       ####   ######    ##
##    ###  ###  ##  ##  ##        ##    ##          ##  ##  ##      ##  ##    ##      ##
##    ########  ##  ##  ##        ##    ##  ######  #####   ##      ##  ##    ##      ##
##    ## ## ##  ##  ##  ##        ##    ##          ##      ##      ##  ##    ##      ##
##    ##    ##   ####   ######    ##    ##          ##      ######   ####     ##      ##
##                                                                                    ##
########################################################################################

class DSFMultiPlotPanel(wx.Panel):
    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Canvas = wx.BoxSizer(wx.VERTICAL)
        self.szr_Canvas.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.12, right=0.99, top=self.Top , bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = "Summary Plot"
        # Store up to six data sets in the instance
        self.Temperature = []
        self.IDs = ["","","","","","","",""]
        self.Fluorescence = [[],[],[],[],[],[],[],[]]
        self.DerivFluo = [[],[],[],[],[],[],[],[]]
        self.RawInflections = [[],[],[],[],[],[],[],[]]
        self.Norm = [[],[],[],[],[],[],[],[]]
        self.DerivNorm = [[],[],[],[],[],[],[],[]]
        self.NormInflections = [[],[],[],[],[],[],[],[]]
        self.Preview = True
        self.PreviewTemperature = []
        self.PreviewID = ""
        self.PreviewFluorescence = []
        self.PreviewDerivFluo = []
        self.PreviewRawInflections = []
        self.PreviewNorm = []
        self.PreviewDerivNorm = []
        self.PreviewNormInflections = []
        self.Inflections = True
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.ColourChoices = cs.TM_RGBA_List
        self.Normalised = False
        self.SetSizer(self.szr_Canvas)
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.fluo, self.deri = self.figure.subplots(nrows=2,ncols=1, sharex=True, gridspec_kw={"height_ratios":[3,1],"hspace":0.0})
        # Actual Plot: Normalisation useful for comparison graph!
        if self.Normalised == False:
            self.fluo.set_ylabel("Fluorescence signal in AU")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temperature, self.Fluorescence[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temperature, self.DerivFluo[i], label=self.IDs[i], color=self.Colours[i])
                    if len(self.RawInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.RawInflections[i])):
                            self.fluo.axvline(self.RawInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.RawInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and not self.PreviewID in self.IDs:
                self.fluo.plot(self.PreviewTemperature, self.PreviewFluorescence, label=self.PreviewID, color=cs.TMPaleGrey_RGBA)
                self.deri.plot(self.PreviewTemperature, self.PreviewDerivFluo, label=self.PreviewID, color=cs.TMPaleGrey_RGBA)
                if len(self.PreviewRawInflections) > 0 and self.Inflections == True:
                    for j in range(len(self.PreviewRawInflections)):
                        self.fluo.axvline(self.PreviewRawInflections[j],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_RGBA)
                        self.deri.axvline(self.PreviewRawInflections[j],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_RGBA)
        else:
            self.fluo.set_ylabel("Normalised Fluorescence")
            self.fluo.set_ylim([-0.1,1.1])
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temperature, self.Norm[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temperature, self.DerivNorm[i], label=self.IDs[i], color=self.Colours[i])
                    if len(self.NormInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.NormInflections[i])):
                            self.fluo.axvline(self.NormInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.NormInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and not self.PreviewID in self.IDs:
                self.fluo.plot(self.PreviewTemperature, self.PreviewNorm, label=self.PreviewID, color=cs.TMPaleGrey_RGBA)
                self.deri.plot(self.PreviewTemperature, self.PreviewDerivNorm, label=self.PreviewID, color=cs.TMPaleGrey_RGBA)
                if len(self.PreviewNormInflections) > 0 and self.Inflections == True:
                    for j in range(len(self.PreviewNormInflections)):
                        self.fluo.axvline(self.PreviewNormInflections[j],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_RGBA)
                        self.deri.axvline(self.PreviewNormInflections[j],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_RGBA)

        self.deri.set_ylabel("Derivative")
        self.deri.set_xlabel("Temperature (" + chr(176) + "C)") # degree symbol!
        self.fluo.set_title(self.Title)
        # Adjust legend:
        graphs = 0
        for i in range(len(self.IDs)):
            if self.IDs[i] != "":
                graphs += 1
        if graphs <= 3:
            y_offset = -0.9
        elif graphs > 3 and graphs < 7:
            y_offset = -1.15
        else:
            y_offset = -1.4
        self.deri.legend(bbox_to_anchor=(0.5,y_offset), loc="lower center", ncol=3)
        self.canvas.draw()
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.Thaw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        data = {}
        data["Temperature"] = self.Temperature
        if self.Normalised == False:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Fluo"] = self.Fluorescence[i]
                    data[self.IDs[i]+"Derivative"] = self.DerivFluo[i]
        else:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Fluo"] = self.Norm[i]
                    data[self.IDs[i]+"Derivative"] = self.DerivNorm[i]
        pd.DataFrame(data=data).to_clipboard(header=True, index=False)

##########################################################################################################
##                                                                                                      ##
##     #####   #####   ####   ######  ######  ######  #####           #####   ##       ####   ######    ##
##    ##      ##      ##  ##    ##      ##    ##      ##  ##          ##  ##  ##      ##  ##    ##      ##
##     ####   ##      ######    ##      ##    ####    #####   ######  #####   ##      ##  ##    ##      ##
##        ##  ##      ##  ##    ##      ##    ##      ##  ##          ##      ##      ##  ##    ##      ##
##    #####    #####  ##  ##    ##      ##    ######  ##  ##          ##      ######   ####     ##      ##
##                                                                                                      ##
##########################################################################################################

# built on https://stackoverflow.com/questions/10737459/embedding-a-matplotlib-figure-inside-a-wxpython-panel
class ScatterPlot(wx.Panel):
    def __init__(self, parent, PanelSize, str_YLabel, tabname):
        self.tabname = tabname
        wx.Panel.__init__(self, parent,size=PanelSize)#=wx.Size(550,325))
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.ylabel = str_YLabel
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.axes = self.figure.add_subplot()
        self.axes.set_title("Destination Plate [X]")
        self.figure.subplots_adjust(left=0.10, right=0.99, top=self.Top , bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.PlateName = None
        self.Input = None

    def Draw(self):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        # If the canvas already exists, we are updating the plot. Therefore, the old needs deleting.
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.PlateName)
        # Categorise the inflection points based on initial fluorescence
        self.Index = []
        self.LowInitial = []
        self.MediumInitial = []
        self.HighInitial = []
        self.SampleIDs = []
        for i in range(len(self.Input)):
            self.Index.append(i)
            self.SampleIDs.append(self.Input.SampleID[i])
            if self.Input.loc[i,"Initial"] == 0:
                self.LowInitial.append(self.Input.Tm[i])
                self.MediumInitial.append(np.nan)
                self.HighInitial.append(np.nan)
            elif self.Input.loc[i,"Initial"] == 1:
                self.LowInitial.append(np.nan)
                self.MediumInitial.append(self.Input.Tm[i])
                self.HighInitial.append(np.nan)
            elif self.Input.loc[i,"Initial"] == 2:
                self.LowInitial.append(np.nan)
                self.MediumInitial.append(np.nan)
                self.HighInitial.append(self.Input.Tm[i])
            else:
                self.LowInitial.append(np.nan)
                self.MediumInitial.append(np.nan)
                self.HighInitial.append(np.nan)
        self.axes.set_xlabel("Compounds")
        self.axes.scatter(self.Index, self.LowInitial, marker="o", label="Low initial fluorescence", color="#44b59a", s=10, picker=1)#, edgecolors ="black")
        self.axes.scatter(self.Index, self.MediumInitial, marker="o", label="Medium initial fluorescence", color="#cc640a", s=10, picker=1)#, edgecolors ="black")
        self.axes.scatter(self.Index, self.HighInitial, marker="o", label="High initial fluorescence", color="#aa4499", s=10, picker=1)#, edgecolors ="black")
        self.axes.set_ylabel(self.ylabel)
        self.axes.set_ylim([15,90])
        self.axes.legend()
        # Connect event handlers
        self.canvas.mpl_connect("pick_event", self.OnClick)
        self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.draw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def CustomToolTip(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib backend plots in wxPython.
        First implementation in panel_Dose (dose response)
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            # Get coordinates on plot
            x, y = event.xdata, event.ydata
            idx_Plate = self.tabname.lbc_Plates.GetFirstSelected()
            lst_YLimits = self.axes.get_ylim()
            within = (lst_YLimits[1] - lst_YLimits[0])/100 * 2
            for i in range(len(self.tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                # For the x axis (log scale), we have to adjust relative
                if x >= (i-2) and x <= (i+2):
                    # for the y axis, we have to adjust absolute
                    Tm = self.tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"NormInflections"][0]
                    str_SampleID = self.tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
                    str_Well = self.tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"]
                    str_DTm = str(self.tabname.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"NormDTm"])
                    if y >= (Tm - within) and y <= (Tm + within):
                        try: self.tltp.Destroy()
                        except: None
                        str_Tooltip = str_Well + ": " + str_SampleID + "\nTm: " + str(Tm) + chr(176) + "C\n" + chr(8710) + "Tm: " + str_DTm + chr(176) + "C"
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        break
                    else:
                        try: self.tltp.Destroy()
                        except: None
                else:
                    try: self.tltp.Destroy()
                    except: None

    # For clicking on scatter plot
    def OnClick(self, event):
        # Get global variables
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get plate and sample index:
        idx_Sample = event.ind[0]
        idx_Plate = self.tabname.lbc_Plates.GetFirstSelected()
        # Draw fresh detail plot
        self.tabname.pnl_DetailPlot.Draw(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"],
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"],
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"],
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Fluo"], 
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawDeriv"],
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        # Write fresh label
        self.tabname.lbl_DetailsTm.SetLabel("Tm: " + str(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0]))
        # Update tick box
        self.tabname.chk_DetailFit.SetValue(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        lst_SampleIDs = []
        lst_Low = []
        lst_Medium = []
        lst_High = []
        for i in range(len(self.SampleIDs)):
            if pd.isna(self.SampleIDs[i]) == False:
                lst_SampleIDs.append(self.SampleIDs[i])
                lst_Low.append(self.LowInitial[i])
                lst_Medium.append(self.MediumInitial[i])
                lst_High.append(self.HighInitial[i])
        pd.DataFrame({"SampleIDs":lst_SampleIDs,"LowIniFluo":lst_Low,"MedIniFluo":lst_Medium,"HighIniFluo":lst_High}).to_clipboard(header=True, index=False)

##############################################################################################
##                                                                                          ##
##    ##       ####   ##  ##   ####   ##  ##  ######           #####  #####   ##  #####     ##
##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##            ##      ##  ##  ##  ##  ##    ##
##    ##      ######   ####   ##  ##  ##  ##    ##    ######  ## ###  #####   ##  ##  ##    ##
##    ##      ##  ##    ##    ##  ##  ##  ##    ##            ##  ##  ##  ##  ##  ##  ##    ##
##    ######  ##  ##    ##     ####    ####     ##             ####   ##  ##  ##  #####     ##
##                                                                                          ##
##############################################################################################

class PlateLayoutGrid (wx.Panel):

    def __init__(self, parent, int_PlateFormat, tabname):
        wx.Panel.__init__ (self, parent, size=wx.Size(830,350))

        self.tabname = tabname

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Grid = wx.BoxSizer(wx.HORIZONTAL)
        self.grd_Plate = wx.grid.Grid(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)

        int_Columns = pf.plate_columns(int_PlateFormat)
        int_Rows = pf.plate_rows(int_PlateFormat)

        # GRID THAT IS HEAT MAP
        # Grid
        self.grd_Plate.CreateGrid(int_Rows, int_Columns)
        self.grd_Plate.EnableEditing(False)
        self.grd_Plate.EnableGridLines(True)
        self.grd_Plate.EnableDragGridSize(False)
        self.grd_Plate.SetMargins(0, 0)
        # Columns
        for col in range(int_Columns):
            self.grd_Plate.SetColSize(col, 19)
            self.grd_Plate.SetColLabelValue(col, str(col+1))
        self.grd_Plate.EnableDragColMove(False)
        self.grd_Plate.EnableDragColSize(False)
        self.grd_Plate.SetColLabelSize(19)
        self.grd_Plate.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        for row in range(int_Rows):
            self.grd_Plate.SetRowSize(row, 19)
            self.grd_Plate.SetRowLabelValue(row, chr(65+row))
        self.grd_Plate.EnableDragColMove(False)
        self.grd_Plate.EnableDragRowSize(False)
        self.grd_Plate.SetRowLabelSize(19)
        self.grd_Plate.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Cell Defaults
        self.grd_Plate.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        self.szr_Grid.Add(self.grd_Plate, 0, wx.ALL, 0)

        # Finalise
        self.SetSizer(self.szr_Grid)
        self.Layout()
        self.Centre(wx.BOTH)

        # Connect Events
        self.grd_Plate.GetGridWindow().Bind(wx.EVT_MOTION, self.MouseOver)

    def __del__(self):
        pass

    def MouseOver(self, event):
        # https://stackoverflow.com/questions/20589686/tooltip-message-when-hovering-on-cell-with-mouse-in-wx-grid-wxpython
        """
        Method to calculate where the mouse is pointing and
        then set the tooltip dynamically.
        """
        idx_Plate = self.tabname.lbc_Plates.GetFirstSelected()
        dfr_Plate = self.dfr_AssayData.iloc[idx_Plate,5]

        int_Columns = self.grd_Plate.GetNumberCols()
        int_Rows = self.grd_Plate.GetNumberRows()

        if int_Columns == 12:
            int_PlateFormat = 96
        elif int_Columns == 24:
            int_PlateFormat = 384
        elif int_Columns == 48:
            int_PlateFormat = 1536
        else:
            int_PlateFormat = 48

        # Use CalcUnscrolledPosition() to get the mouse position
        # within the entire grid including what is offscreen
        x, y = self.grd_Plate.CalcUnscrolledPosition(event.GetX(),event.GetY())
        coords = self.grd_Plate.XYToCell(x, y)
        # you only need these if you need the value in the cell
        row = coords[0]
        col = coords[1]
        if col >= 0 and col < int_Columns and row >= 0 and row < int_Rows:
            idx_Well = (col+1) + (int_Columns)*(row)
            str_Well = pf.index_to_well(idx_Well,int_PlateFormat)
            idx_Sample = dfr_Plate[dfr_Plate["Well"] == str_Well].index
            if len(idx_Sample) > 0 and  idx_Sample[0] >= 0 and idx_Sample[0] <= (int_PlateFormat-1):
                idx_Sample = idx_Sample[0]
                str_Tm = "Tm: " + str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0])
                event.GetEventObject().SetToolTip(str_Well + ": " + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] + " - " + str_Tm)

    def Update(self, dfr_Layout):
        # Refresh plate map grid:
        if len(dfr_Layout.loc[0,"ProteinNumerical"]) > 0:
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    idx_Well = col + row*self.grd_Plate.GetNumberCols()
                    self.grd_Plate.SetCellValue(row,col,dfr_Layout.loc[0,"ProteinNumerical"][idx_Well])
                    self.grd_Plate.SetCellBackgroundColour(row,col,self.DetermineWellColour(dfr_Layout.loc[0,"WellType"][idx_Well]))
        else:
            for row in range(self.grd_Plate.GetNumberRows()):
                for col in range(self.grd_Plate.GetNumberCols()):
                    idx_Well = col + row*self.grd_Plate.GetNumberCols()
                    self.grd_Plate.SetCellValue(row,col,"")
                    self.grd_Plate.SetCellBackgroundColour(row,col,"white")
        self.Layout()

    def DetermineWellColour(self, str_WellType):
        """
        Takes the type of a well and returns the appropriate colour for painting.
        """
        if str_WellType == "r" or str_WellType == "Reference well":
            return "red"
        elif str_WellType == "s" or str_WellType == "Sample":
            return "yellow"
        else:
            return "white"

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
        self.Title = u"Differential Scanning Fluorimetry"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "thermal_shift"
        self.str_Shorthand = "DSF"
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
        self.bol_PlateID = True
        self.bol_PlateMapPopulated = False
        self.dfr_Details = pd.DataFrame()
        self.str_DatafileExtension = ".txt"
        self.str_SaveFilePath = ""
        self.str_DataPath = ""
        self.str_TransferPath = ""
        self.SampleSource = "echo"
        self.Device = "lightcycler"

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

        # Start Building
        self.tab_Details = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.tab_Details.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Assay = wx.BoxSizer(wx.VERTICAL)


        self.szr_Details = wx.BoxSizer(wx.HORIZONTAL)

        # Left Sizer
        self.szr_Left = wx.BoxSizer(wx.VERTICAL)
        # Assay Type Panel
        self.pnl_AssayType = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(160,-1), wx.TAB_TRAVERSAL)
        self.pnl_AssayType.SetBackgroundColour(clr_Panels)
        self.szr_AssayList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_AssayType = wx.StaticText(self.pnl_AssayType, wx.ID_ANY, u"Device and plate format:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_AssayType.Wrap(-1)
        self.szr_AssayList.Add(self.lbl_AssayType, 0, wx.ALL, 5)
        lbx_AssayTypeChoices = [ u"Roche Lightcycler (384 wells)", u"Roche Lightcycler (96 wells)", u"Agilent MX3005p (96 wells)" ]
        self.lbx_AssayType = wx.ListBox(self.pnl_AssayType, wx.ID_ANY, wx.DefaultPosition, wx.Size(220,100), lbx_AssayTypeChoices, 0)
        self.lbx_AssayType.SetBackgroundColour(clr_TextBoxes)
        self.szr_AssayList.Add(self.lbx_AssayType, 1, wx.ALL, 5)
        self.lbx_AssayType.SetSelection(0)
        self.pnl_AssayType.SetSizer(self.szr_AssayList)
        self.pnl_AssayType.Layout()
        self.szr_Left.Add(self.pnl_AssayType, 0, wx.EXPAND|wx.ALL, 5)
        # Sample IDs panel
        self.pnl_SampleIDs = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_SampleIDs.SetBackgroundColour(clr_Panels)
        self.szr_SampleIDs = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SampleIDs = wx.StaticText(self.pnl_SampleIDs, wx.ID_ANY, u"Obtain sample IDs:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SampleIDs.Wrap(-1)
        self.szr_SampleIDs.Add(self.lbl_SampleIDs, 0, wx.ALL, 5)
        self.rad_Transfer = wx.RadioButton(self.pnl_SampleIDs, wx.ID_ANY, u"from Echo transfer file", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_SampleIDs.Add(self.rad_Transfer, 0, wx.ALL, 5)
        self.rad_Transfer.SetValue(True)
        self.rad_DataFile = wx.RadioButton(self.pnl_SampleIDs, wx.ID_ANY, u"from Data file (Lightcycler)", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_SampleIDs.Add(self.rad_DataFile, 0, wx.ALL, 5)
        self.rad_WellOnly = wx.RadioButton(self.pnl_SampleIDs, wx.ID_ANY, u"use well designation only", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_SampleIDs.Add(self.rad_WellOnly, 0, wx.ALL, 5)
        self.pnl_SampleIDs.SetSizer(self.szr_SampleIDs)
        self.pnl_SampleIDs.Layout()
        self.szr_SampleIDs.Fit(self.pnl_SampleIDs)
        self.szr_Left.Add(self.pnl_SampleIDs, 0, wx.ALL|wx.EXPAND, 5)
        self.szr_Details.Add(self.szr_Left, 0, wx.EXPAND, 5)
        
        # Middle Sizer ########################################################################################################################################
        self.szr_Middle = wx.BoxSizer(wx.VERTICAL)
        # Layout panel
        self.pnl_Layout = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Layout.SetBackgroundColour(clr_Panels)
        self.szr_Layout = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Layout = wx.StaticText(self.pnl_Layout, wx.ID_ANY, u"Plate layout(s)", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Layout.Wrap(-1)
        self.szr_Layout.Add(self.lbl_Layout, 0, wx.ALL, 5)
        self.chk_PlateID = wx.CheckBox(self.pnl_Layout, wx.ID_ANY, u"Use PlateID for database", wx.DefaultPosition, wx.Size(-1,-1), 0)
        self.chk_PlateID.SetValue(self.bol_PlateID)
        self.szr_Layout.Add(self.chk_PlateID, 0, wx.ALL, 5)
        self.rad_Individual = wx.RadioButton(self.pnl_Layout, wx.ID_ANY, u"Individual layouts for each plate", wx.DefaultPosition,
            wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Layout.Add(self.rad_Individual, 0, wx.ALL, 5)
        self.szr_Individual = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Individual.Add((25,24), 0, wx.EXPAND, 5)
        self.lbl_Individual = wx.StaticText(self.pnl_Layout, wx.ID_ANY,
            u"If you select this option, you can specify layouts for each plate in the \"Transfer and Data Files\" tab",
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Individual.Wrap(240)
        self.szr_Individual.Add(self.lbl_Individual, 0, wx.EXPAND, 5)
        self.lbl_Individual.Enable(False)
        self.szr_Layout.Add(self.szr_Individual, 0, wx.EXPAND, 5)
        self.rad_OneForAll = wx.RadioButton(self.pnl_Layout, wx.ID_ANY, u"Same layout on all plates (e.g. large screen)", wx.DefaultPosition,
            wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Layout.Add(self.rad_OneForAll, 0, wx.ALL, 5)
        self.rad_OneForAll.SetValue(True)
        self.szr_OneForAll = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_OneForAll.Add((20,24), 0, wx.EXPAND, 5)
        self.btn_EditGlobalLayout = CustomBitmapButton(self.pnl_Layout, u"EditPlateLayout", 0, (125,25))
        self.szr_OneForAll.Add(self.btn_EditGlobalLayout, 0, wx.ALL, 0)
        self.szr_Layout.Add(self.szr_OneForAll, 0, wx.EXPAND, 5)
        self.szr_Layout.Add((-1,10), 0, wx.ALL, 0)
        self.pnl_Layout.SetSizer(self.szr_Layout)
        self.pnl_Layout.Layout()
        self.szr_Layout.Fit(self.pnl_Layout)
        self.szr_Middle.Add(self.pnl_Layout, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_Details.Add(self.szr_Middle, 0, wx.EXPAND, 5)

        # Right Sizer #########################################################################################################################################
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
        self.szr_Right.Add(self.pnl_Date, 0, wx.EXPAND |wx.ALL, 5)
        # ELN panel
        self.pnl_ELN = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_ELN.SetBackgroundColour(clr_Panels)
        self.pnl_ELN.SetMaxSize(wx.Size(210,-1))
        self.szr_ELNPage = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_ELN = wx.StaticText(self.pnl_ELN, wx.ID_ANY, u"ELN Page", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_ELN.Wrap(-1)
        self.szr_ELNPage.Add(self.lbl_ELN, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ELN = wx.TextCtrl(self.pnl_ELN, wx.ID_ANY, u"PAGE21-12345", wx.DefaultPosition, wx.DefaultSize, 0)
        self.txt_ELN.SetBackgroundColour(clr_TextBoxes)
        self.szr_ELNPage.Add(self.txt_ELN, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pnl_ELN.SetSizer(self.szr_ELNPage)
        self.pnl_ELN.Layout()
        self.szr_ELNPage.Fit(self.pnl_ELN)
        self.szr_Right.Add(self.pnl_ELN, 0, wx.EXPAND |wx.ALL, 5)
        # Buffer panel
        self.pnl_Buffer = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Buffer.SetBackgroundColour(clr_Panels)
        self.pnl_Buffer.SetMaxSize(wx.Size(210,-1))
        self.szr_Buffer = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Buffer = wx.StaticText(self.pnl_Buffer, wx.ID_ANY, u"Buffer", wx.DefaultPosition, wx.Size(50,-1), 0)
        self.lbl_Buffer.Wrap(-1)
        self.szr_Buffer.Add(self.lbl_Buffer, 0, wx.ALL, 5)
        self.txt_Buffer = wx.TextCtrl(self.pnl_Buffer, wx.ID_ANY, u"20 mM HEPES. 20 mM NaCl",
            wx.DefaultPosition, wx.Size(210,54), wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.txt_Buffer.SetBackgroundColour(clr_TextBoxes)
        self.txt_Buffer.SetMaxSize(wx.Size(210,27))
        self.szr_Buffer.Add(self.txt_Buffer, 0, wx.ALL, 5)
        self.pnl_Buffer.SetSizer(self.szr_Buffer)
        self.pnl_Buffer.Layout()
        self.szr_Buffer.Fit(self.pnl_Buffer)
        self.szr_Right.Add(self.pnl_Buffer, 0, wx.ALL, 5)
        # Solvent panel
        self.pnl_Solvent = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(250,-1), wx.TAB_TRAVERSAL)
        self.pnl_Solvent.SetBackgroundColour(clr_Panels)
        self.pnl_Solvent.SetMaxSize(wx.Size(210,-1))
        self.szr_Solvent = wx.BoxSizer(wx.VERTICAL)
        self.szr_SolventName = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Solvent = wx.StaticText(self.pnl_Solvent, wx.ID_ANY, u"Compound solvent", wx.DefaultPosition, wx.Size(130,-1), 0)
        self.lbl_Solvent.Wrap(-1)
        self.szr_SolventName.Add(self.lbl_Solvent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Solvent = wx.TextCtrl(self.pnl_Solvent, wx.ID_ANY, u"DMSO", wx.DefaultPosition, wx.Size(100,24), 0)
        self.txt_Solvent.SetMaxSize(wx.Size(100,24))
        self.txt_Solvent.SetBackgroundColour(clr_TextBoxes)
        self.szr_SolventName.Add(self.txt_Solvent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Solvent.Add(self.szr_SolventName, 1, wx.EXPAND, 5)
        self.szr_SolventConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_SolvConc = wx.StaticText(self.pnl_Solvent, wx.ID_ANY, u"Concentration", wx.DefaultPosition, wx.Size(100,-1), 0)
        self.lbl_SolvConc.Wrap(-1)
        self.szr_SolventConc.Add(self.lbl_SolvConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_Percent = wx.TextCtrl(self.pnl_Solvent, wx.ID_ANY, u"0.5", wx.DefaultPosition, wx.Size(35,24), 0)
        self.txt_Percent.SetMaxSize(wx.Size(35,24))
        self.txt_Percent.SetBackgroundColour(clr_TextBoxes)
        self.szr_SolventConc.Add(self.txt_Percent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_Percent = wx.StaticText(self.pnl_Solvent, wx.ID_ANY, u"% (v/v)", wx.DefaultPosition, wx.Size(-1,-1), 0)
        self.lbl_Percent.Wrap(-1)
        self.szr_SolventConc.Add(self.lbl_Percent, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Solvent.Add(self.szr_SolventConc, 1, wx.EXPAND, 5)
        self.pnl_Solvent.SetSizer(self.szr_Solvent)
        self.pnl_Solvent.Layout()
        self.szr_Right.Add(self.pnl_Solvent, 0, wx.ALL|wx.EXPAND, 5)
        #######################################################################################################################################################
        self.szr_Details.Add(self.szr_Right, 0, wx.EXPAND, 5)
        self.szr_Assay.Add(self.szr_Details, 0, wx.EXPAND, 5)

        # Finalise
        self.tab_Details.SetSizer(self.szr_Assay)
        self.tab_Details.Layout()
        self.szr_Assay.Fit(self.tab_Details)
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", True)


        ##### ###   ##  #  #  ### #### #### ###    # ###   ##  #####  ##
          #   #  # #  # ## # #    #    #    #  #   # #  # #  #   #   #  #
          #   ###  #### # ##  ##  ###  ###  ###   #  #  # ####   #   ####
          #   #  # #  # #  #    # #    #    #  # #   #  # #  #   #   #  #
          #   #  # #  # #  # ###  #    #### #  # #   ###  #  #   #   #  # #####################################################################################

        self.tab_Files = tab.FileSelection(self.tabs_Analysis.sbk_Notebook,
                                          tabname = self,
                                          data = u"directory",
                                          normalise = False,
                                          layouts=True)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Transfer and Data Files", True)


        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  ####################################################################################

        # Start Building
        self.pnl_Review = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Review.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Review = wx.BoxSizer(wx.VERTICAL)

        self.szr_Heatmap = wx.BoxSizer(wx.HORIZONTAL)

        # List Control - Plates
        self.lbc_Plates = wx.ListCtrl(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.Size(310,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Plates.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Plates.InsertColumn(0, "Plate")
        self.lbc_Plates.SetColumnWidth(0,40)
        self.lbc_Plates.InsertColumn(1,"Transfer file entry")
        self.lbc_Plates.SetColumnWidth(1, 120)
        self.lbc_Plates.InsertColumn(2,"Data file name")
        self.lbc_Plates.SetColumnWidth(2, 120)
        self.szr_Heatmap.Add(self.lbc_Plates, 0, wx.ALL|wx.EXPAND, 5)

        # Plot panel
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Add simple book to hold the plots
        self.sbk_PlatePlots = wx.Simplebook(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.Size(600,400), 0)
        self.sbk_PlatePlots.SetBackgroundColour(cs.BgUltraLight)
        # Add heatmap/grid to sbk_PlatePlots
        self.plt_Heatmap = cp.HeatmapPanel(self.sbk_PlatePlots,
                                           size = wx.Size(600,400),
                                           tabname =  self,
                                           title = "Melting temperature (" + chr(176) +"C)",
                                           buttons = True)
        self.plt_Heatmap.YLabel = "Melting temperature (" + chr(176) +"C)"
        self.sbk_PlatePlots.AddPage(self.plt_Heatmap, u"Heatmap", False)
        # Add plate layout plot so sbk_PlatePlots
        #self.pnl_PlateLayout = PlateLayoutGrid(self.sbk_PlatePlots, 384, self)
        #self.pnl_PlateLayout.Layout()
        #self.sbk_PlatePlots.AddPage(self.pnl_PlateLayout, u"Plate layout", False)
        # Add scatter plot to sbk_PlatePlots
        self.plt_ScatterPlot = ScatterPlot(self.sbk_PlatePlots, wx.Size(600,400), "Melting temperature (" + chr(176) +"C)", self)
        self.plt_ScatterPlot.Layout()
        self.sbk_PlatePlots.AddPage(self.plt_ScatterPlot, u"ScatterPlot", False)
        # Add notebook to sizer
        self.szr_Plot.Add(self.sbk_PlatePlots, 0, 0, 5)
        # Add Detailplot
        self.szr_ExportHeatMap = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_DetailPlot = DSFDetailPlot(self.pnl_Review,(220,180))
        self.szr_ExportHeatMap.Add(self.pnl_DetailPlot, 0, wx.ALL, 5)

        self.szr_DetailControls = wx.BoxSizer(wx.VERTICAL)
        self.szr_DetailControls.Add((-1,-1), 1, wx.EXPAND, 5)
        self.chk_DetailFit = wx.CheckBox(self.pnl_Review, wx.ID_ANY, u"Fit", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_DetailControls.Add(self.chk_DetailFit, 0, wx.ALL, 5)
        self.lbl_DetailsTm = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Tm: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DetailsTm.Wrap(-1)
        self.szr_DetailControls.Add(self.lbl_DetailsTm, 0, wx.ALL)
        self.szr_ExportHeatMap.Add(self.szr_DetailControls, 0, wx.ALIGN_LEFT, 6)
        self.szr_Plot.Add(self.szr_ExportHeatMap, 1, wx.ALL, 5)
        self.szr_Heatmap.Add(self.szr_Plot, 1, wx.ALL, 5)

        # Sizer for sidebar
        self.szr_Sidebar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Sidebar.Add((0, 35), 0, wx.EXPAND, 5)
        self.lbl_DisplayPlot = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DisplayPlot.Wrap(-1)
        self.szr_Sidebar.Add(self.lbl_DisplayPlot, 0, wx.ALL, 5)
        self.rad_Heatmap = wx.RadioButton(self.pnl_Review, wx.ID_ANY, u"Heatmap", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Sidebar.Add(self.rad_Heatmap, 0, wx.ALL, 5)
        self.rad_Heatmap.SetValue(True)
        #self.rad_PlateLayout = wx.RadioButton(self.pnl_Review, wx.ID_ANY, u"Plate layout", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        #self.szr_Sidebar.Add(self.rad_PlateLayout, 0, wx.ALL, 5)
        #self.rad_PlateLayout.SetValue(False)
        self.rad_ScatterPlot = wx.RadioButton(self.pnl_Review, wx.ID_ANY, u"Scatter plot", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Sidebar.Add(self.rad_ScatterPlot, 0, wx.ALL, 5)
        self.rad_ScatterPlot.SetValue(False)
        self.btn_MapToClipboard = CustomBitmapButton(self.pnl_Review, u"Clipboard", 0, (130,25))
        self.szr_Sidebar.Add(self.btn_MapToClipboard, 0, wx.ALL, 5)
        self.btn_SaveMap = CustomBitmapButton(self.pnl_Review, u"ExportToFile", 5, (104,25))
        self.szr_Sidebar.Add(self.btn_SaveMap, 0, wx.ALL, 5)
        self.szr_Heatmap.Add(self.szr_Sidebar, 1, wx.EXPAND, 5)

        self.szr_Review.Add(self.szr_Heatmap, 1, wx.ALIGN_LEFT, 5)

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
        self.szr_Results = wx.BoxSizer(wx.VERTICAL)

        self.bSizer12 = wx.BoxSizer(wx.HORIZONTAL)

        # Sample List
        self.szr_SampleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectSample = wx.StaticText(self.pnl_Results, wx.ID_ANY, u"Select a sample", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SelectSample.Wrap(-1)
        self.szr_SampleList.Add(self.lbl_SelectSample, 0, wx.ALL, 5)
        self.lbc_Samples = wx.ListCtrl(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(350,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Plate")
        self.lbc_Samples.SetColumnWidth(0,40)
        self.lbc_Samples.InsertColumn(1,"Well")
        self.lbc_Samples.SetColumnWidth(1,40)
        self.lbc_Samples.InsertColumn(2,"SampleID")
        self.lbc_Samples.SetColumnWidth(2,90)
        self.lbc_Samples.InsertColumn(3,"Tm")
        self.lbc_Samples.SetColumnWidth(3,35)
        #self.lbc_Samples.InsertColumn(4,"")
        #self.lbc_Samples.SetColumnWidth(4,20)
        #self.lbc_Samples.InsertColumn(5,"")
        #self.lbc_Samples.SetColumnWidth(5,35)
        self.lbc_Samples.InsertColumn(4,chr(8710)+"Tm")
        self.lbc_Samples.SetColumnWidth(4,40)
        self.szr_SampleList.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)
        # Button to export results table
        self.btn_ExportResultsTable = CustomBitmapButton(self.pnl_Results, u"ExportToFile", 0, (104,25))
        self.szr_SampleList.Add(self.btn_ExportResultsTable, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.bSizer12.Add(self.szr_SampleList, 0, wx.EXPAND, 5)

        # Sizer for plot and plot export buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IndividualPlot = IconTabButton(self.pnl_Results, u"Individual Plot", 0, self.AssayPath)
        self.btn_IndividualPlot.IsCurrent(True)
        self.szr_SimpleBookTabs.Add(self.btn_IndividualPlot, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_SummaryPlot = IconTabButton(self.pnl_Results, u"Summary Plot", 1, self.AssayPath)
        self.btn_SummaryPlot.IsEnabled(True)
        self.szr_SimpleBookTabs.Add(self.btn_SummaryPlot, 0, wx.ALL, 0)
        self.dic_PlotTabButtons = {0:self.btn_IndividualPlot,1:self.btn_SummaryPlot}
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        self.sbk_ResultPlots = wx.Simplebook(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(900,550), 0)
        self.btn_IndividualPlot.Notebook = self.sbk_ResultPlots
        self.btn_IndividualPlot.Group = self.dic_PlotTabButtons
        #self.btn_IndividualPlot.Bind(wx.EVT_BUTTON, self.btn_IndividualPlot.OpenTab)
        self.btn_SummaryPlot.Notebook = self.sbk_ResultPlots
        self.btn_SummaryPlot.Group = self.dic_PlotTabButtons
        #self.btn_SummaryPlot.Bind(wx.EVT_BUTTON, self.btn_SummaryPlot.OpenTab)

        # First page in simplebook: Resultsplot ===============================================================================================================
        self.pnl_IndividualPlot = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(800,470), wx.TAB_TRAVERSAL)
        self.szr_Plot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_ThermalUnfolding = DSFPlotPanel(self.pnl_IndividualPlot,(600,450),self)
        self.szr_Plot.Add(self.plt_ThermalUnfolding, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_BesidePlot = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_Res_Display = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Display = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Display.Wrap(-1)
        self.szr_Res_Display.Add(self.lbl_Display, 0, wx.ALL, 5)
        self.rad_Res_Raw = wx.RadioButton(self.pnl_IndividualPlot, wx.ID_ANY, u"Raw fluorescence", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_Raw, 0, wx.ALL, 5)
        self.rad_Res_Normalised = wx.RadioButton(self.pnl_IndividualPlot, wx.ID_ANY, u"Normalised fluorescence", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_Normalised, 0, wx.ALL, 5)
        self.m_staticline101 = wx.StaticLine(self.pnl_IndividualPlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_Res_Display.Add(self.m_staticline101, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_BesidePlot.Add(self.szr_Res_Display, 0, wx.EXPAND, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Determine Tm", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Details.Add(self.chk_Fit, 0, wx.ALL, 5)
        self.szr_FittingMethods = wx.FlexGridSizer(3,2,0,0)
        self.szr_FittingMethods.Add((10,5), 0, wx.ALL, 5)
        self.rad_Derivative = wx.RadioButton(self.pnl_IndividualPlot, wx.ID_ANY, u"by derivative", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_FittingMethods.Add(self.rad_Derivative, 0, wx.ALL, 5)
        self.szr_FittingMethods.Add((10,5), 0, wx.ALL, 5)
        self.rad_Boltzmann = wx.RadioButton(self.pnl_IndividualPlot, wx.ID_ANY, u"by Boltzmann", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_FittingMethods.Add(self.rad_Boltzmann, 0, wx.ALL, 5)
        self.szr_FittingMethods.Add((10,5), 0, wx.ALL, 5)
        self.rad_Thompson = wx.RadioButton(self.pnl_IndividualPlot, wx.ID_ANY, u"by Thompson", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_FittingMethods.Add(self.rad_Thompson, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_FittingMethods, 0, wx.ALL,0)
        # Tm
        self.lbl_Tm = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Tm", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Tm.Wrap(-1)
        self.szr_Details.Add(self.lbl_Tm, 0, wx.ALL, 5)
        # Enthalpy
        #self.lbl_Enthalpy = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"H", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.lbl_Enthalpy.Wrap(-1)
        #self.szr_Details.Add(self.lbl_Enthalpy, 0, wx.ALL, 5)
        # Separator line
        self.m_staticline14 = wx.StaticLine(self.pnl_IndividualPlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_Details.Add(self.m_staticline14, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_BesidePlot.Add(self.szr_Details, 0, wx.EXPAND, 5)
        # Export plot
        self.szr_ExportPlot = wx.BoxSizer(wx.VERTICAL)
        self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot, u"Clipboard", 0, (130,25))
        self.szr_ExportPlot.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportToFile", 5, (104,25))
        self.szr_ExportPlot.Add(self.btn_SaveFig, 0, wx.ALL, 5)
        self.btn_SaveAll = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportAll", 0, (100,25))
        self.szr_ExportPlot.Add(self.btn_SaveAll, 0, wx.ALL, 5)
        self.szr_BesidePlot.Add(self.szr_ExportPlot, 0, wx.EXPAND, 5)
        self.szr_Plot.Add(self.szr_BesidePlot, 0, wx.EXPAND, 5)
        # Finish first page
        self.pnl_IndividualPlot.SetSizer(self.szr_Plot)
        self.pnl_IndividualPlot.Layout()
        self.szr_Plot.Fit(self.pnl_IndividualPlot)
        self.sbk_ResultPlots.AddPage(self.pnl_IndividualPlot, u"Individual Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # =====================================================================================================================================================
        
        # Second page in sbx_ResultPlots: Multiplot ===========================================================================================================
        self.pnl_MultiPlotPanel = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(900,550), wx.TAB_TRAVERSAL)
        self.szr_MultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_MultiPlot = DSFMultiPlotPanel(self.pnl_MultiPlotPanel,(600,550),self)
        self.szr_MultiPlot.Add(self.plt_MultiPlot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_MultiPlotRight = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_MultiPlotShow = wx.BoxSizer(wx.VERTICAL)
        self.lbl_MultiPlotShow = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_MultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.rad_MultiPlotRaw = wx.RadioButton(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Raw fluorescence", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotRaw, 0, wx.ALL, 5)
        self.rad_MultiPlotNorm = wx.RadioButton(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Normalised fluorescence", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotNorm, 0, wx.ALL, 5)
        self.chk_InflectionsMulti = wx.CheckBox(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Show inflection points", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_InflectionsMulti.SetValue(True)
        self.szr_MultiPlotShow.Add(self.chk_InflectionsMulti, 0, wx.ALL, 5)
        self.chk_PreviewPlot = wx.CheckBox(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Preview selected sample", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_PreviewPlot.SetValue(True)
        self.szr_MultiPlotShow.Add(self.chk_PreviewPlot, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotShow, 0, wx.EXPAND, 5)
        # Separator line
        self.lin_MultiPlotShow = wx.StaticLine(self.pnl_MultiPlotPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotShow, 0, wx.EXPAND|wx.ALL, 5)
        # FlexGridSizer
        self.szr_MultiPlotList = wx.FlexGridSizer(9, 4, 0, 0)
        self.szr_MultiPlotList.SetFlexibleDirection(wx.BOTH)
        self.szr_MultiPlotList.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.lst_ColourOptions = cs.TM_Hex_List
        self.lst_ColourBitmaps = []
        for pic in cs.TM_ColourChoiceIcons_List:
            self.lst_ColourBitmaps.append(wx.Bitmap(pic, wx.BITMAP_TYPE_ANY))
        # Column labels
        self.lbl_Column1 = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Sample ID/Name", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column1.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column1, 0, wx.ALL, 3)
        self.lbl_Column2 = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Colour", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column2.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column2, 0, wx.ALL, 3)
        self.lbl_Column3 = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column3.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column3, 0, wx.ALL, 3)
        self.lbl_Comlumn4 = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Comlumn4.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Comlumn4, 0, wx.ALL, 3)
        # Fill up with 8 spaces for samples
        self.lst_MultiPlotLabels = []
        self.dic_MultiPlotLabels = {}
        self.lst_BitmapCombos = []
        self.dic_BitmapCombos = {}
        self.lst_AddButtons = []
        self.dic_AddButtons = {}
        self.lst_RemoveButtons = []
        self.dic_RemoveButtons = {}
        for i in range(8):
            #Label
            self.lst_MultiPlotLabels.append("self.lbl_Sample" + str(i))
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]] = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u"no sample", wx.DefaultPosition, wx.DefaultSize, 0)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Wrap(-1)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Enable(False)
            self.szr_MultiPlotList.Add(self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]], 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_BitmapCombos.append("self.bmc_Sample" + str(i))
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]] = wx.adv.BitmapComboBox(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Combo!", wx.DefaultPosition, wx.Size(100,25), self.lst_ColourOptions, wx.CB_READONLY)
            for j in range(len(self.lst_ColourBitmaps)):
                self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetItemBitmap(j,self.lst_ColourBitmaps[j])
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetSelection(i)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Index = i
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Enable(False)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Bind(wx.EVT_COMBOBOX, self.ColourSelect)
            self.szr_MultiPlotList.Add(self.dic_BitmapCombos[self.lst_BitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_AddButtons.append("self.btn_Add" + str(i))
            self.dic_AddButtons[self.lst_AddButtons[i]] = CustomBitmapButton(self.pnl_MultiPlotPanel, u"Plus", 0, (25,25))
            self.dic_AddButtons[self.lst_AddButtons[i]].Index = i
            self.dic_AddButtons[self.lst_AddButtons[i]].Bind(wx.EVT_BUTTON, self.AddGraph)
            self.szr_MultiPlotList.Add(self.dic_AddButtons[self.lst_AddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_RemoveButtons.append("self.btn_Add" + str(i))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]] = CustomBitmapButton(self.pnl_MultiPlotPanel, u"Minus", 0, (25,25))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Index = i
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Bind(wx.EVT_BUTTON, self.RemoveGraph)
            self.szr_MultiPlotList.Add(self.dic_RemoveButtons[self.lst_RemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_MultiPlotRight = wx.StaticLine(self.pnl_MultiPlotPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export ##########
        self.szr_ExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_SummaryPlotToClipboard = CustomBitmapButton(self.pnl_MultiPlotPanel, u"Clipboard", 0, (130,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_SummaryPlotToPNG = CustomBitmapButton(self.pnl_MultiPlotPanel, u"ExportToFile", 5, (104,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_ExportMultiPlot, 0, wx.ALL, 0)
        #######################################################################################################################################################
        self.szr_MultiPlot.Add(self.szr_MultiPlotRight, 0, wx.EXPAND, 5)
        self.pnl_MultiPlotPanel.SetSizer(self.szr_MultiPlot)
        self.pnl_MultiPlotPanel.Layout()
        self.szr_MultiPlot.Fit(self.pnl_MultiPlotPanel)
        self.sbk_ResultPlots.AddPage(self.pnl_MultiPlotPanel, u"Summary Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        #######################################################################################################################################################

        self.szr_SimpleBook.Add(self.sbk_ResultPlots, 0, wx.EXPAND, 5)        
        self.bSizer12.Add(self.szr_SimpleBook, 0, wx.ALL, 5)
        self.szr_Results.Add(self.bSizer12, 1, wx.EXPAND, 5)
        
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
        
        self.tab_ELNPlots = tab.ELNPlots(self.tabs_Analysis.sbk_Notebook, tabname=self, shorthand=self.str_Shorthand)
        self.tabs_Analysis.AddPage(self.tab_ELNPlots, u"Plots for ELN", False)

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

        ###  #     ##  ##### #### #   #  ##  ###
        #  # #    #  #   #   #    ## ## #  # #  #
        ###  #    ####   #   ###  # # # #### ###
        #    #    #  #   #   #    #   # #  # # 
        #    #### #  #   #   #### #   # #  # # ################################################################################################################

        self.lst_PlateMapHeaders = ["PlateID","PlateWellID","PlateParent","SGC Global Compound ID","Well concentration(mM)","Neccesary additive",
                        "Plate well: plate active","Plate well purpose","Plate well comments"]
        self.tab_PlateMap = tab.PlateMapForDatabase(self.tabs_Analysis.sbk_Notebook, self)
        self.tabs_Analysis.AddPage(self.tab_PlateMap, u"Plate Map", False)

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
        self.rad_Transfer.Bind(wx.EVT_RADIOBUTTON, self.RadTransfer)
        self.rad_DataFile.Bind(wx.EVT_RADIOBUTTON, self.RadDatafile)
        self.rad_WellOnly.Bind(wx.EVT_RADIOBUTTON, self.RadWellOnly)
        self.btn_EditGlobalLayout.Bind(wx.EVT_BUTTON, self.EditGlobalLayout)
        self.rad_OneForAll.Bind(wx.EVT_RADIOBUTTON, self.RadOneForAll)
        self.rad_Individual.Bind(wx.EVT_RADIOBUTTON, self.RadIndividual)
        self.chk_PlateID.Bind(wx.EVT_CHECKBOX, self.UsePlateID)

        # Tab 2: Transfer and Data Files
        self.tab_Files.btn_EditLayouts.Bind(wx.EVT_BUTTON, self.EditLayouts)

        # Tab 3: Review Plate
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdateReviewPlotPanel)
        self.rad_Heatmap.Bind(wx.EVT_RADIOBUTTON, self.RadHeatmap)
        #self.rad_PlateLayout.Bind(wx.EVT_RADIOBUTTON, self.RadPlateLayout)
        self.rad_ScatterPlot.Bind(wx.EVT_RADIOBUTTON, self.RadScatterplot)
        self.chk_DetailFit.Bind(wx.EVT_CHECKBOX, self.ToggleDetailFit)
        self.btn_MapToClipboard.Bind(wx.EVT_BUTTON, self.plt_Heatmap.PlotToClipboard)
        self.btn_SaveMap.Bind(wx.EVT_BUTTON, self.plt_Heatmap.PlotToPNG)

        # Tab 4: Results
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowCurve)
        self.lbc_Samples.Bind(wx.EVT_MOTION, self.MouseOver)
        self.lbc_Samples.Bind(wx.EVT_LEAVE_WINDOW, self.ClosePlotToolTip)
        self.btn_ExportResultsTable.Bind(wx.EVT_BUTTON, self.ExportResultsTable)
        #self.btn_IndividualPlot.Bind(wx.EVT_BUTTON, self.IndividualPlot)
        #self.btn_SummaryPlot.Bind(wx.EVT_BUTTON, self.MultiPlot)
        self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.ToggleFit)
        self.rad_Res_Normalised.Bind(wx.EVT_RADIOBUTTON, self.RadNormalised)
        self.rad_Res_Raw.Bind(wx.EVT_RADIOBUTTON, self.RadRaw)
        self.btn_FigToClipboard.Bind(wx.EVT_BUTTON, self.plt_ThermalUnfolding.PlotToClipboard)
        self.btn_SaveFig.Bind(wx.EVT_BUTTON, self.plt_ThermalUnfolding.PlotToPNG)
        self.btn_SaveAll.Bind(wx.EVT_BUTTON, self.AllPlotsToPNG)
        self.rad_MultiPlotNorm.Bind(wx.EVT_RADIOBUTTON, self.MultiRadNorm)
        self.rad_MultiPlotRaw.Bind(wx.EVT_RADIOBUTTON, self.MultiRadRaw)
        self.chk_InflectionsMulti.Bind(wx.EVT_CHECKBOX, self.ToggleInflectionsMulti)
        self.chk_PreviewPlot.Bind(wx.EVT_CHECKBOX, self.TogglePreviewPlot)
        self.btn_SummaryPlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToClipboard)
        self.btn_SummaryPlotToPNG.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToPNG)
        
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
                self.tab_ELNPlots.PopulatePlotsTab(self.dfr_AssayData)
        elif int_NewTab == 5:
            # going to export tab
            if self.bol_ExportPopulated == False:
                self.bol_ExportPopulated = self.tab_Export.Populate()
        elif int_NewTab == 6:
            # going to plate map tab
            if self.bol_PlateMapPopulated == False:
                self.tab_PlateMap.PopulatePlateMapTab()

    def PopulateFromFile(self, dfr_LoadedDetails, lst_LoadedBoolean, dfr_Loaded, lst_Paths):

        self.dfr_AssayData = dfr_Loaded

        # Assay Details
        self.dfr_Details = dfr_LoadedDetails
        self.str_AssayType = self.dfr_Details.loc["AssayType","Value"]
        for i in range(self.lbx_AssayType.GetCount()):
            if self.dfr_Details.loc["AssayType","Value"] == self.lbx_AssayType.GetString(i):
                self.lbx_AssayType.SetSelection(i)
                break
        # No field for purification ID
        # No field for protein concentration
        self.txt_Solvent.SetValue(self.dfr_Details.loc["Solvent","Value"])
        self.txt_Percent.SetValue(self.dfr_Details.loc["SolventConcentration","Value"])
        self.txt_Buffer.SetValue(self.dfr_Details.loc["Buffer","Value"])
        self.txt_ELN.SetValue(self.dfr_Details.loc["ELN","Value"])
        # str_AssayVolume = self.dfr_Details.loc["AssayType","Value"] # in nL
        self.str_DatafileExtension = self.dfr_Details.loc["DataFileExtension","Value"]
        self.chk_PlateID.Enable(lst_LoadedBoolean[11])
        self.tabs_Analysis.EnablePlateMap(lst_LoadedBoolean[11])
        self.SampleSource = self.dfr_Details.loc["SampleSource","Value"]
        # Backwards compatibility wild older save files that do not have newer additions in the assay details:
        try:
            self.Device = self.dfr_Details.loc["Device","Value"]
        except:
            self.Device = "lightcycler"
            self.dfr_Details.at["AssayType","Value"] = self.Device
        try:
            Date = self.dfr_Details.loc["Date","Value"]
            Date = wx.DateTime.FromDMY(int(Date[8:10]), int(Date[5:7]), int(Date[:4]))
            self.tab_Details.DatePicker.SetValue(Date)
        except:
            self.dfr_Details.at["Date","Value"] = "NA"

        # Update boolean variables
        self.bol_AssayDetailsChanged = False # lst_LoadedBoolean[0]
        self.bol_AssayDetailsCompleted = lst_LoadedBoolean[1]
        self.bol_DataFilesAssigned = lst_LoadedBoolean[2]
        self.bol_DataFilesUpdated = False # lst_LoadedBoolean[3]
        self.bol_DataAnalysed = lst_LoadedBoolean[4]
        self.bol_ELNPlotsDrawn = lst_LoadedBoolean[5]
        if self.bol_ELNPlotsDrawn == True:
            self.tab_ELNPlots.PopulatePlotsTab(self.dfr_AssayData)
        self.bol_ExportPopulated = lst_LoadedBoolean[6]
        if self.bol_ExportPopulated == True:
            self.tab_Export.Populate(noreturn = True)
        self.bol_ResultsDrawn = lst_LoadedBoolean[7]
        if self.bol_ResultsDrawn == True:
            self.PopulateResultsTab()
        self.bol_ReviewsDrawn = lst_LoadedBoolean[8]
        if self.bol_ReviewsDrawn == True:
            self.PopulateReviewTab()
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
        # If files have been moved, the original file paths saved in the bbq file are no longer up to date!
        try:
            lst_DataFiles = os.listdir(lst_Paths[1])
        except:
            lst_DataFiles = []
            lst_Paths[0] = "Path not found"
            lst_Paths[1] = "Path not found"
        self.str_DataPath = lst_Paths[1]
        # Go through directory, get each file with correct extension, compare to list already assigned. If not assigned, add to tab_Files.lbc_Data
        for i in range(len(lst_DataFiles)):
            if lst_DataFiles[i].find(self.str_DatafileExtension) != -1:
                bol_Found = False
                for j in range(self.tab_Files.lbc_Transfer.GetItemCount()):
                    if str(lst_DataFiles[i]) == self.tab_Files.lbc_Transfer.GetItemText(j,2):
                        bol_Found = True
                        break
                if bol_Found == False:
                    self.tab_Files.lbc_Data.InsertItem(i,str(lst_DataFiles[i]))
        # Add paths to filepickers
        self.tab_Files.fpk_Transfer.SetPath(lst_Paths[0])
        self.tab_Files.fpk_Data.SetPath(lst_Paths[1])

        # recreate single dfr_Layout
        self.dfr_Layout = pd.DataFrame(index=range(len(dfr_Loaded)), columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
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
        This is purely a wrapper function. Some modules might straight up call the default ProcessData() from lib_tabs, others might need their own.
        """
        tab.ProcessData(self, dlg_Progress)

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
        if self.lbx_AssayType.GetSelection() == 0:
            self.str_AssayType = "DSF_LC_384"
            self.str_DatafileExtension = ".txt"
            self.Device = "lightcycler"
        elif self.lbx_AssayType.GetSelection() == 1:
            self.str_AssayType = "DSF_LC_96"
            self.str_DatafileExtension = ".txt"
            self.Device = "lightcycler"
        elif self.lbx_AssayType.GetSelection() == 2:
            self.str_AssayType = "DSF_MX_96"
            self.str_DatafileExtension = ".xls"
            self.Device = "agilent"
        self.str_AssayCategory = "thermal_shift"
        str_Purification = "DSF"
        int_ProteinConc = 0
        str_Solvent = self.txt_Solvent.GetLineText(0)
        int_SolventPercent = self.txt_Percent.GetLineText(0)
        # Get buffer, needs special consideration since TextCtrl is multiline
        int_Lines = self.txt_Buffer.GetNumberOfLines()
        str_Buffer = ""
        for i in range(int_Lines):
            str_Buffer = str_Buffer + self.txt_Buffer.GetLineText(i)
        str_ELN = self.txt_ELN.GetLineText(0)
        str_AssayVolume= str(20 * 1000) # convert to nL
        Date = self.DatePicker.GetValue()
        Date = str(Date.GetYear()) + "-" + str(Date.GetMonth()+1) + "-" + str(Date.GetDay()) # GetMonth is indexed from zero!!!!!
        Date = datetime.strptime(Date,"%Y-%m-%d").strftime("%Y-%m-%d")
        # Include checks so that user does not leave things empty
        dfr_Details_New = pd.DataFrame(data={"Value":[self.str_AssayType, self.str_AssayCategory, "DSF", str_Purification, int_ProteinConc,
            str_Solvent, int_SolventPercent,str_Buffer, str_ELN, str_AssayVolume, self.str_DatafileExtension, self.SampleSource, self.Device, Date]},
            index=["AssayType","AssayCategory","Shorthand","PurificationID","ProteinConcentration","Solvent","SolventConcentration","Buffer",
            "ELN","AssayVolume","DataFileExtension","SampleSource","Device","Date"])

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

        if bol_Details == True:
            self.bol_AssayDetailsCompleted = True
            # Update details in dfr_Database and export tab, if applicable
            #if self.bol_ExportPopulated == True:
            #    for idx_List in range(self.tab_Export.grd_Database.GetNumberRows()):
            #        # lbc_Database
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,0,str_AssayType + " IC50")
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,1,str_Purification)
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,2,str(float(int_ProteinConc)/1000))
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,3,str_PeptideID)
            #        # omitted
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,5,str(float(int_PeptideConc)/1000))
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,6,str_Solvent)
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,7,str(int_SolventPercent))
            #        self.tab_Export.grd_Database.SetCellValue(idx_List,8,str_Buffer)
            #        # dfr_Database
            #        self.dfr_Database.iloc[idx_List,0] = str_AssayType + " IC50"
            #        self.dfr_Database.iloc[idx_List,1] = str_Purification
            #        self.dfr_Database.iloc[idx_List,2] = float(int_ProteinConc)/1000
            #        self.dfr_Database.iloc[idx_List,3] = str_PeptideID
            #        # omitted
            #        self.dfr_Database.iloc[idx_List,5] = float(int_PeptideConc)/1000
            #        self.dfr_Database.iloc[idx_List,6] = str_Solvent
            #        self.dfr_Database.iloc[idx_List,7] = int_SolventPercent
            #        self.dfr_Database.iloc[idx_List,8] = str_Buffer
        else:
            msg.IncompleteDetails()
            self.tabs_Analysis.SetSelection(0)

        # Data already analysed but assay details changed? Offer user chance to re-analyse
        if bol_FromTabChange == True:
            if self.bol_DataAnalysed == True and self.bol_AssayDetailsChanged == True:
                if msg.QueryReanalysis() == True:
                    self.parent.AnalyseData()
    
    def RadTransfer(self, event):
        if hasattr(self, "dfr_TransferFile"):
            if msg.QueryChangeSampleSource() == False:
                return None
        self.rad_Transfer.SetValue(True)
        self.rad_DataFile.SetValue(False)
        self.rad_WellOnly.SetValue(False)
        self.SampleSource = "echo"
        self.tab_Files.SwitchSampleSource()

    def RadDatafile(self, event):
        if hasattr(self, "dfr_TransferFile"):
            if msg.QueryChangeSampleSource() == False:
                return None
        self.rad_Transfer.SetValue(False)
        self.rad_DataFile.SetValue(True)
        self.rad_WellOnly.SetValue(False)
        self.SampleSource = "lightcycler"
        self.tab_Files.SwitchSampleSource()

    def RadWellOnly(self, event):
        if hasattr(self, "dfr_TransferFile"):
            if msg.QueryChangeSampleSource() == False:
                return None
        self.rad_Transfer.SetValue(False)
        self.rad_DataFile.SetValue(False)
        self.rad_WellOnly.SetValue(True)
        self.SampleSource = "well"
        self.dfr_Exceptions = None
        self.tab_Files.SwitchSampleSource()

    def RadOneForAll(self, event):
        self.bol_GlobalLayout = True
        # radio buttons:
        self.rad_OneForAll.SetValue(True)
        self.rad_Individual.SetValue(False)
        # labels and other stuff on same tab:
        self.lbl_Individual.Enable(False)
        self.btn_EditGlobalLayout.Enable(True)
        # labels and other stuff on files tab:
        self.tab_Files.btn_EditLayouts.Enable(False)

    def RadIndividual(self, event):
        self.bol_GlobalLayout = False
        # radio ruttons:
        self.rad_OneForAll.SetValue(False)
        self.rad_Individual.SetValue(True)
        # labels and other stuff on same tab:
        self.lbl_Individual.Enable(True)
        self.btn_EditGlobalLayout.Enable(False)
        # labels and other stuff on files tab:
        self.tab_Files.btn_EditLayouts.Enable(True)
    
    def UsePlateID(self, event):
        self.bol_PlateID = self.chk_PlateID.GetValue()
        for i in range(len(self.lst_TabButtonLabels)):
            if self.lst_TabButtonLabels[i] == "Plate Map":
                self.dic_TabButtons[i].IsEnabled(self.bol_PlateID)

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

    def EditGlobalLayout(self, event):
        """
        Launches dialog to edit plate layouts. Sends dfr_Layout back.
        """
        if self.lbx_AssayType.GetString(self.lbx_AssayType.GetSelection()).find("96") != -1:
            int_PlateFormat = 96
        else:
            int_PlateFormat = 384
        self.dlg_Layout = plm.PlateLayout(self, plates = [],
                                          dfr_Layout = self.dfr_Layout,
                                          wells = int_PlateFormat,
                                          multiples = False,
                                          plateids = self.bol_PlateID,
                                          references = True,
                                          controls = True,
                                          sampleids = False)
        self.dlg_Layout.ShowModal()
        self.dlg_Layout.Destroy()

    def EditLayouts(self, event):
        """
        Launches dialog to edit plate layouts. Sends dfr_Layout back.
        """
        if self.tab_Files.lbc_Transfer.GetItemCount() > 0:
            lst_Plates = []
            for i in range(self.tab_Files.lbc_Transfer.GetItemCount()):
                lst_Plates.append(self.tab_Files.lbc_Transfer.GetItemText(i,0))
            if self.dfr_Layout.shape[0] == 0:
                self.dfr_Layout = pd.DataFrame()
            if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
                int_PlateFormat = 96
            else:
                int_PlateFormat = 384
            self.dlg_Layout = plm.PlateLayout(self, plates = lst_Plates,
                                              dfr_Layout = self.dfr_Layout, 
                                              wells = int_PlateFormat,
                                              multiples = True,
                                              plateids = self.bol_PlateID,
                                              references = True,
                                              controls = False,
                                              sampleids = False)
            self.dlg_Layout.ShowModal()
            self.dlg_Layout.Destroy()
        else:
            wx.MessageBox("You have not imported any destination/assay plates, yet.\nImport plates and try again.",
                "No plates",
                wx.OK|wx.ICON_INFORMATION)


    # 3. Functions for Review
    # ======================================================================================================
    #
    #  ######   ####   #####    ####       #####   ##       ####   ######  ######   #####
    #    ##    ##  ##  ##  ##      ##      ##  ##  ##      ##  ##    ##    ##      ##
    #    ##    ######  #####     ###   ##  #####   ##      ######    ##    ####     ####
    #    ##    ##  ##  ##  ##      ##      ##      ##      ##  ##    ##    ##          ##
    #    ##    ##  ##  #####   #####   ##  ##      ######  ##  ##    ##    ######  #####
    #
    # ======================================================================================================

    # 3.1 Populate review tab (populate list control, draw first heatmap)
    def PopulateReviewTab(self):
        # Write item in list, clear list first:
        self.lbc_Plates.DeleteAllItems()
        for i in range(len(self.dfr_AssayData)):
            self.lbc_Plates.InsertItem(i,str(i+1))
            self.lbc_Plates.SetItem(i,1,str(self.dfr_AssayData.loc[i,"DestinationPlateName"]))
            self.lbc_Plates.SetItem(i,2,str(self.dfr_AssayData.loc[i,"DataFileName"]))
        self.lbc_Plates.Unbind(wx.EVT_LIST_ITEM_SELECTED)
        self.lbc_Plates.Select(0) # This will call UpdateReviewPlotPanel as it is bound to the selection event of the list
        self.lbc_Plates.SetFocus()
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdateReviewPlotPanel)
        self.bol_ReviewsDrawn = True

    # 3.2 Updating the plate panel
    def UpdateReviewPlotPanel(self,event):
        # Get current selection
        self.sbk_PlatePlots.Freeze()
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        if self.rad_Heatmap.GetValue() == True:
            which = 0
        else:
        #elif self.rad_PlateLayout.GetValue() == True:
            which = 1
        #else:
        #    which = 2
        # Get current plate format
        if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
            int_PlateFormat = 96
        else:
            int_PlateFormat = 384
        # Update scatter plot
        dfr_Scatter = pd.DataFrame(columns=["SampleID","Well","Tm","Initial"],index=range(int_PlateFormat))
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            k = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
            dfr_Scatter.loc[k,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
            dfr_Scatter.loc[k,"Well"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"]
            dfr_Scatter.loc[k,"Tm"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
            dfr_Scatter.loc[k,"Initial"] =self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Initial"]
        self.plt_ScatterPlot.Input = dfr_Scatter
        self.plt_ScatterPlot.PlateName = self.dfr_AssayData.iloc[idx_Plate,0]
        self.plt_ScatterPlot.Draw()
        # Update heatmap
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"RawDataFrame"])):
            dfr_Heatmap.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Heatmap.loc[i,"Value"] = np.nan
            dfr_Heatmap.loc[i,"SampleID"] = ""
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            idx_Well = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
            dfr_Heatmap.loc[idx_Well,"Value"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
            dfr_Heatmap.loc[idx_Well,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
        self.plt_Heatmap.Data = dfr_Heatmap
        self.plt_Heatmap.Title = self.dfr_AssayData.iloc[idx_Plate,0]
        self.plt_Heatmap.Draw()
        # Update detail plot
        self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Well"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"SampleID"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Temp"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Fluo"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"RawDeriv"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"DoFit"])
        self.lbl_DetailsTm.SetLabel("Tm: " + str(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"RawInflections"][0]) + chr(176) + "C")
        # Update the simplebook. I tried just running .Update(), that did not work.
        if which == 0:
            self.sbk_PlatePlots.SetSelection(1)
            self.sbk_PlatePlots.SetSelection(0)
        elif which == 1:
            self.sbk_PlatePlots.SetSelection(0)
            self.sbk_PlatePlots.SetSelection(1)
        #else:
        #    self.sbk_PlatePlots.SetSelection(0)
        #    self.sbk_PlatePlots.SetSelection(2)
        self.sbk_PlatePlots.Thaw()

    def RadHeatmap(self, event):
        self.rad_Heatmap.SetValue(True)
        self.rad_ScatterPlot.SetValue(False)
        #self.rad_PlateLayout.SetValue(False)
        self.TogglePlot(event)

    def RadScatterplot(self, event):
        self.rad_Heatmap.SetValue(False)
        self.rad_ScatterPlot.SetValue(True)
        #self.rad_PlateLayout.SetValue(False)
        self.TogglePlot(event)

    def RadPlateLayout(self, event):
        self.rad_Heatmap.SetValue(False)
        self.rad_ScatterPlot.SetValue(False)
        #self.rad_PlateLayout.SetValue(True)
        self.TogglePlot(event)

    def UpdateDetailPlot(self, tabname, col, row):

        if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
            int_PlateFormat = 96
        else:
            int_PlateFormat = 384
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        int_Columns = pf.plate_columns(int_PlateFormat)

        idx_Well = (col+1) + (int_Columns)*(row)
        str_Well = pf.index_to_well(idx_Well,int_PlateFormat)
        idx_Sample = self.dfr_AssayData.iloc[idx_Plate,5][self.dfr_AssayData.iloc[idx_Plate,5]["Well"] == str_Well].index
        idx_Sample = idx_Sample[0]
        self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Fluo"], 
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawDeriv"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        # Update tick box
        self.chk_DetailFit.SetValue(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        # Write fresh label
        self.lbl_DetailsTm.SetLabel("Tm: " + str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0]) + chr(176) + "C")

    # 3.3 Toggle between heatmap and scatter plot
    def TogglePlot(self,event):
        if self.rad_Heatmap.GetValue() == True:
            which = 0
        else:
        #elif self.rad_PlateLayout.GetValue() == True:
            which = 1
        #else:
        #    which = 2
        self.sbk_PlatePlots.SetSelection(which)
    
    def ToggleDetailFit(self, event):
        # Changes whether to fit data.
        self.sbk_PlatePlots.Freeze()
        if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
            int_PlateFormat = 96
        else:
            int_PlateFormat = 384
        # get indices
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        str_Title = str(self.pnl_DetailPlot.ax.title)
        int_Start = str_Title.find(chr(39))+1 # find ' starting from front of string, add one to get position after
        int_End = str_Title.rfind(chr(58)) # find : starting from rear of string
        str_Well = str_Title[int_Start:int_End] # take care of spaces before, and inverted commas around Sample ID
        idx_Sample = pf.well_to_index(str_Well, int_PlateFormat)
        if self.rad_Heatmap.GetValue() == True:
            which = 0
        else:
        #elif self.rad_PlateLayout.GetValue() == True:
            which = 1
        #else:
        #    which = 2
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] = self.chk_DetailFit.GetValue()
        self.lbl_DetailsTm.SetLabel("Tm: " + str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0]) + chr(176) + "C")
        # Update detail plot
        self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Fluo"], 
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawDeriv"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        # Update results tab
        for i in range(self.lbc_Samples.GetItemCount()):
            if self.lbc_Samples.GetItemText(i, col=0) == str(idx_Plate+1): # Plate number is written in list control, not index.
                if self.lbc_Samples.GetItemText(i, col=1) == str_Well:
                    if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                        self.lbc_Samples.SetItem(i,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0],2)))
                        #self.lbc_Samples.SetItem(i,4,chr(177))
                        self.lbc_Samples.SetItem(i,4,"")
                    else:
                        self.lbc_Samples.SetItem(i,3,"ND")
                        #self.lbc_Samples.SetItem(i,4,"")
                        self.lbc_Samples.SetItem(i,4,"")
                    if self.lbc_Samples.IsSelected(i) == True:
                        if self.rad_Res_Raw.Value == True:
                            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
                        else:
                            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
                        self.plt_ThermalUnfolding.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
                        self.plt_ThermalUnfolding.Draw()
                        self.chk_Fit.SetValue(self.chk_DetailFit.GetValue())
                    break
        # Update scatter plot
        dfr_Scatter = pd.DataFrame(columns=["SampleID","Well","Tm","Initial"],index=range(int_PlateFormat))
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            k = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
            dfr_Scatter.loc[k,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
            dfr_Scatter.loc[k,"Well"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"]
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"DoFit"] == True:
                dfr_Scatter.loc[k,"Tm"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
            else:
                dfr_Scatter.loc[k,"Tm"] = np.nan
            dfr_Scatter.loc[k,"Initial"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Initial"]
        self.plt_ScatterPlot.Input = dfr_Scatter
        self.plt_ScatterPlot.PlateName = self.dfr_AssayData.iloc[idx_Plate,0]
        self.plt_ScatterPlot.Draw()
        # Update heatmap
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        for i in range(int_PlateFormat):
            dfr_Heatmap.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Heatmap.loc[i,"Value"] = np.nan
            dfr_Heatmap.loc[i,"SampleID"] = ""
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            idx_Well = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"DoFit"] == True:
                dfr_Heatmap.loc[idx_Well,"Value"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
            else:
                dfr_Heatmap.loc[idx_Well,"Value"] = np.nan
            dfr_Heatmap.loc[idx_Well,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
        self.plt_Heatmap.Data = dfr_Heatmap
        self.Title = self.dfr_AssayData.iloc[idx_Plate,0]
        self.plt_Heatmap.Draw()
        # Update the simplebook. I tried just running .Update(), that did not work.
        if which == 0:
            self.sbk_PlatePlots.SetSelection(1)
            self.sbk_PlatePlots.SetSelection(0)
        elif which == 1:
            self.sbk_PlatePlots.SetSelection(0)
            self.sbk_PlatePlots.SetSelection(1)
        #else:
        #    self.sbk_PlatePlots.SetSelection(0)
        #    self.sbk_PlatePlots.SetSelection(2)
        self.sbk_PlatePlots.Thaw()


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
        # Iterate through plates
        idx_List = -1
        for idx_Plate in range(len(self.dfr_AssayData)):
            for j in range(len(self.dfr_AssayData.iloc[idx_Plate,5].index)):
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"SampleID"] != "Control":
                    idx_List += 1
                    self.lbc_Samples.InsertItem(idx_List,str(idx_Plate+1))
                    self.lbc_Samples.SetItem(idx_List,1,self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"Well"])
                    self.lbc_Samples.SetItem(idx_List,2,self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"SampleID"])
                    if self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"DoFit"] == True:
                        self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"RawInflections"][0],1)))
                        #self.lbc_Samples.SetItem(idx_List,4,chr(177))
                        #self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"RawFitCI"][4],2)))
                        self.lbc_Samples.SetItem(idx_List,4,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"NormDTm"],2)))
                    else:
                        self.lbc_Samples.SetItem(idx_List,3,"ND")
                        #self.lbc_Samples.SetItem(idx_List,4,"")
                        #self.lbc_Samples.SetItem(idx_List,5,"")
                        self.lbc_Samples.SetItem(idx_List,4,"")

        # Individual plot
        self.rad_Res_Raw.SetValue(True)
        self.lbl_Tm.SetLabel("Tm: "+ str(self.dfr_AssayData.iloc[0,5].loc[0,"RawInflections"][0]) + chr(176) + "C")
        self.plt_ThermalUnfolding.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[0]
        self.plt_ThermalUnfolding.Draw()
        self.chk_Fit.SetValue(self.dfr_AssayData.iloc[0,5].loc[0,"DoFit"])

        # Multiplot
        self.plt_MultiPlot.Temperature = self.dfr_AssayData.iloc[0,5].loc[0,"Temp"]
        self.plt_MultiPlot.IDs[0] = self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"]
        self.plt_MultiPlot.Fluorescence[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Fluo"]
        self.plt_MultiPlot.DerivFluo[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawDeriv"]
        self.plt_MultiPlot.RawInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawInflections"]
        self.plt_MultiPlot.Norm[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Norm"]
        self.plt_MultiPlot.DerivNorm[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormDeriv"]
        self.plt_MultiPlot.NormInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormInflections"]
        self.plt_MultiPlot.Inflections = True
        self.plt_MultiPlot.Normalised = False
        self.plt_MultiPlot.Draw()
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].SetLabel(self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[0]].Enable(True)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].SetSelection(0)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].Enable(True)
        self.rad_MultiPlotRaw.SetValue(True)
        self.lbc_Samples.Select(0)
        self.bol_ResultsDrawn = True

    # 4.2 Toggle fit -> change whether a dataset should be fitted or not
    def ToggleFit(self,event):
        # get plate format
        if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
            int_PlateFormat = 96
        elif self.dfr_Details.loc["AssayType","Value"].find("384") != -1:
            int_PlateFormat = 384
        # get indices
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        # Get value from check box
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] = self.chk_Fit.GetValue()
        
        # Decide whether to refit or set to nan // We are not getting rid of the "fit" since it is actually the derivative.
        #if self.chk_Fit.GetValue() == False:
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitPars"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitPars"]))
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitPars"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitPars"]))
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"]))
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"]))
        #else:
        #    self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].at[idx_Sample] = df.recalculate_fit_DSF(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
        
        # Check whether raw data or normalised data is shown, update accordingly
        # Redraw panel on results tab
        if self.rad_Res_Raw.Value == True:
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0],1)))
                #self.lbc_Samples.SetItem(idx_List,4,chr(177))
                #self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitCI"][4],2)))
                self.lbc_Samples.SetItem(idx_List,4,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormDTm"],2)))
            else:
                self.lbc_Samples.SetItem(idx_List,3,"ND")
                #self.lbc_Samples.SetItem(idx_List,4,"")
                #self.lbc_Samples.SetItem(idx_List,5,"")
                self.lbc_Samples.SetItem(idx_List,4,"")
        else:
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormInflections"][0],1)))
                #self.lbc_Samples.SetItem(idx_List,4,chr(177))
                #self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitCI"][4],2)))
                self.lbc_Samples.SetItem(idx_List,4,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormDTm"],2)))
            else:
                self.lbc_Samples.SetItem(idx_List,3,"ND")
                #self.lbc_Samples.SetItem(idx_List,4,"")
                #self.lbc_Samples.SetItem(idx_List,5,"")
                self.lbc_Samples.SetItem(idx_List,4,"")
        self.plt_ThermalUnfolding.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
        self.plt_ThermalUnfolding.Draw()
        # Check which plot is shown on plate review tab
        idx_Plate_Review = self.lbc_Plates.GetFirstSelected()
        str_Title = str(self.pnl_DetailPlot.ax.title)
        int_Start = str_Title.find(chr(39))+1 # find ' starting from front of string, add one to get position after
        int_End = str_Title.rfind(chr(58)) # find : starting from rear of string
        str_Well = str_Title[int_Start:int_End] # take care of spaces before, and inverted commas around Sample ID
        idx_Sample_Review = pf.well_to_index(str_Well, int_PlateFormat)
        # Update plate panel
        if idx_Plate == idx_Plate_Review:
            # Update scatter plot
            dfr_Scatter = pd.DataFrame(columns=["SampleID","Well","Tm","Initial"],index=range(int_PlateFormat))
            for i in range(len(self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"])):
                k = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
                dfr_Scatter.loc[k,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
                dfr_Scatter.loc[k,"Well"] = self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"Well"]
                if self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"DoFit"] == True:
                    dfr_Scatter.loc[k,"Tm"] = self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
                else:
                    dfr_Scatter.loc[k,"Tm"] = np.nan
                dfr_Scatter.loc[k,"Initial"] = self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"Initial"]
            self.plt_ScatterPlot.Input = dfr_Scatter
            self.plt_ScatterPlot.PlateName = self.dfr_AssayData.iloc[idx_Plate_Review,0]
            self.plt_ScatterPlot.Draw()
            # Update heatmap
            dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
            for i in range(int_PlateFormat):
                dfr_Heatmap.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
                dfr_Heatmap.loc[i,"Value"] = np.nan
                dfr_Heatmap.loc[i,"SampleID"] = ""
            for i in range(len(self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"])):
                idx_Well = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
                dfr_Heatmap.loc[idx_Well,"Value"] = self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"RawInflections"][0]
                dfr_Heatmap.loc[idx_Well,"SampleID"] = self.dfr_AssayData.loc[idx_Plate_Review,"ProcessedDataFrame"].loc[i,"SampleID"]
            self.plt_Heatmap.Data = dfr_Heatmap
            self.plt_Heatmap.Title = self.dfr_AssayData.iloc[idx_Plate_Review,0]
            self.plt_Heatmap.Draw()
        # Update detail plot:
        if idx_Sample == idx_Sample_Review:
            self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Fluo"], 
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawDeriv"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
            self.chk_DetailFit.SetValue(self.chk_Fit.GetValue())

    def RadNormalised(self, event):
        if self.rad_Res_Normalised.GetValue() == True:
            self.rad_Res_Raw.SetValue(False)
        else:
            self.rad_Res_Raw.SetValue(True)
        self.ShowCurve(event)

    def RadRaw(self, event):
        if self.rad_Res_Raw.GetValue() == True:
            self.rad_Res_Normalised.SetValue(False)
        else:
            self.rad_Res_Normalised.SetValue(True)
        self.ShowCurve(event)

    # 4.3 Show/Update the displayed curve based on selection on ListCtr
    def ShowCurve(self,event):
        self.Freeze()
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        if self.rad_Res_Raw.Value == True:
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
        else:
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
        self.chk_Fit.SetValue(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        self.plt_ThermalUnfolding.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
        self.plt_ThermalUnfolding.Draw()
        self.lbl_Tm.SetLabel("Tm: "+ str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormInflections"][0]) + chr(176) + "C")

        self.plt_MultiPlot.PreviewTemperature = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Temp"]
        self.plt_MultiPlot.PreviewID = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
        self.plt_MultiPlot.PreviewFluorescence = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Fluo"]
        self.plt_MultiPlot.PreviewDerivFluo = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"RawDeriv"]
        self.plt_MultiPlot.PreviewRawInflections = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"RawInflections"]
        self.plt_MultiPlot.PreviewNorm = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Norm"]
        self.plt_MultiPlot.PreviewDerivNorm = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormDeriv"]
        self.plt_MultiPlot.PreviewNormInflections = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormInflections"]
        self.plt_MultiPlot.Draw()

        self.Thaw()

    def ExportResultsTable(self,event):
        dfr_ResultsTable = pd.DataFrame(columns=["Plate","Well","SampleID","SourceConcentration[mM]","TopConcentration[uM]","Tm[C]"],index=range(self.lbc_Samples.GetItemCount()))
        count = 0
        for i in range(len(self.dfr_AssayData)):
            for j in range(len(self.dfr_AssayData.loc[i,"ProcessedDataFrame"])):
                dfr_ResultsTable.loc[count,"Plate"] = i+1
                dfr_ResultsTable.loc[count,"Well"] = self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"Well"]
                dfr_ResultsTable.loc[count,"SampleID"] = self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"SampleID"]
                dfr_ResultsTable.loc[count,"TopConcentration[uM]"] = float(self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"Concentrations"][0]) * 1000000
                dfr_ResultsTable.loc[count,"Tm[C]"] = float(self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"RawInflections"][0])
                count += 1
        # Export as csv:
        fdlg = wx.FileDialog(self, "Save summary table as as", wildcard="Comma separated files (*.csv)|*.csv", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .png. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            dfr_ResultsTable.to_csv(str_SavePath)

    # 4.6 Get the indices of the selected plot from the self.dfr_AssayData
    def GetPlotIndices(self):
        # Get list index of selected sample
        idx_SampleList = self.lbc_Samples.GetFirstSelected()
        # Get plate index
        idx_Plate = int(self.lbc_Samples.GetItemText(idx_SampleList,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.dfr_AssayData.iloc[idx_Plate,5]
        idx_SampleDataFrame = dfr_Sample[dfr_Sample["Well"] == self.lbc_Samples.GetItemText(idx_SampleList,1)].index.tolist()
        idx_SampleDataFrame = idx_SampleDataFrame[0] # above function returns list, but there will always be only one result
        return idx_SampleList, idx_SampleDataFrame, idx_Plate

    def MouseOver(self, event):
        x,y = event.GetX(), event.GetY()
        idx_ListItem, flags = self.lbc_Samples.HitTest((x,y))
        if idx_ListItem >= 0:
            # cannot use self.GetPlotIndices() as we are not looking up the selected item
            idx_Plate = int(self.lbc_Samples.GetItemText(idx_ListItem,0))-1 # Human plate numbering vs computer indexing!
            idx_Sample = self.dfr_AssayData.iloc[idx_Plate,5][self.dfr_AssayData.iloc[idx_Plate,5]["Well"] == self.lbc_Samples.GetItemText(idx_ListItem,1)].index.tolist()
            idx_Sample = idx_Sample[0] # above function returns list, but there will always be only one result
            try: self.tltp.Destroy()
            except: None
            lst_X = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Temp"]
            lst_Y = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Fluo"]
            lst_Deriv = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"RawDeriv"]
            self.tltp = tt.plt_ToolTip(self, lst_X, lst_Y, lst_Deriv)
            self.tltp.Show()
            self.SetFocus()
        else:
            try: self.tltp.Destroy()
            except: None
    
    def ClosePlotToolTip(self, event):
        """
        Since the plot tooltip is not a real tooltip, just a dialog box, we also needa workaround to close it when we don"t need it anymore.
        This function will try to destroy the tooltip, if there is one. Otherwise, the tooltip will just stay like a dialog.
        """
        try: self.tltp.Destroy()
        except: None

    def AllPlotsToPNG(self, event):
        with wx.DirDialog(self, message="Select a directory to save plots", defaultPath="",
            style=wx.DD_DEFAULT_STYLE, pos=wx.DefaultPosition, size=wx.DefaultSize) as dlg_Directory:

            if dlg_Directory.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveDirPath = dlg_Directory.GetPath()
        # Pick directory here. If no directory picked, self.Thaw() and end function.
        self.dlg_PlotsProgress = GenericProgress(self, "Saving Plots")
        self.dlg_PlotsProgress.Show()
        thd_SavingPlots = threading.Thread(target=self.AllPlotsToPNG_thread, args=(str_SaveDirPath,), daemon=True)
        thd_SavingPlots.start()

    def AllPlotsToPNG_thread(self, str_SaveDirPath):
        self.Freeze()
        int_Samples = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            int_Samples += len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])
        count = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            for idx_Sample in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                count += 1
                #DO STUFF TO MAKE PLOT
                tempplot = DSFPlotPanel(self.pnl_Results, (500,400),self)
                tempplot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample],self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0])

                tempplot.figure.savefig(str_SaveDirPath + chr(92) + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] + ".png",
                    dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None, transparent=False, bbox_inches=None, pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_PlotsProgress.gauge.SetValue((count/int_Samples)*200)
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()
    
    def TogglePreviewPlot(self, event):
        self.plt_MultiPlot.Preview = self.chk_PreviewPlot.GetValue()
        self.plt_MultiPlot.Draw()

    def MultiPlotNormalised(self):
        if self.rad_MultiPlotRaw.GetValue() == True:
            return False
        else:
            return True

    def ColourSelect(self, event):
        idx_Combo = event.GetEventObject().GetSelection()
        self.plt_MultiPlot.Colours[event.GetEventObject().Index] = self.plt_MultiPlot.ColourChoices[idx_Combo]
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()

    def AddGraph(self, event):
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        idx_Graph = event.GetEventObject().Index
        self.plt_MultiPlot.IDs[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
        self.plt_MultiPlot.Fluorescence[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Fluo"]
        self.plt_MultiPlot.DerivFluo[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawDeriv"]
        self.plt_MultiPlot.RawInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"]
        self.plt_MultiPlot.Norm[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"]
        self.plt_MultiPlot.DerivNorm[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormDeriv"]
        self.plt_MultiPlot.NormInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormInflections"]
        self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(True)
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()

    def RemoveGraph(self, event):
        # First, test that at least one graph will remain on the plot:
        checksum = 0
        for i in range(len(self.plt_MultiPlot.IDs)):
            if self.plt_MultiPlot.IDs[i] != "":
                checksum += 1
        if checksum > 1:
            idx_Graph = event.GetEventObject().Index
            self.plt_MultiPlot.IDs[idx_Graph] = ""
            self.plt_MultiPlot.Fluorescence[idx_Graph] = []
            self.plt_MultiPlot.DerivFluo[idx_Graph] = []
            self.plt_MultiPlot.Norm[idx_Graph] = []
            self.plt_MultiPlot.DerivNorm[idx_Graph] = []
            self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(False)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel("no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(False)
            self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
            self.plt_MultiPlot.Draw()
        else:
            wx.MessageBox("Cannot remove this graph.\nAt least one graph must be displayed.",
                "No can do",
                wx.OK|wx.ICON_INFORMATION)

    def MultiRadNorm(self, event):
        if self.rad_MultiPlotNorm.GetValue() == True:
            self.rad_MultiPlotRaw.SetValue(False)
            self.plt_MultiPlot.Normalised = True
        else:
            self.rad_MultiPlotRaw.SetValue(True)
            self.plt_MultiPlot.Normalised = False
        self.plt_MultiPlot.Draw()

    def MultiRadRaw(self, event):
        if self.rad_MultiPlotRaw.GetValue() == True:
            self.rad_MultiPlotNorm.SetValue(False)
            self.plt_MultiPlot.Normalised = False
        else:
            self.rad_MultiPlotNorm.SetValue(True)
            self.plt_MultiPlot.Normalised = True
        self.plt_MultiPlot.Draw()

    def ToggleInflectionsMulti(self, event):
        self.plt_MultiPlot.Inflections = self.chk_InflectionsMulti.Value
        if self.rad_MultiPlotRaw.GetValue() == True:
            self.plt.MultiPlot.Normalised = False
        else:
            self.plt_MultiPlot.Normalised = True
        self.plt_MultiPlot.Draw()