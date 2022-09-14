# Import my own libraries
import lib_datafunctions as df
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_customplots as cp
import lib_tabs as tab
import lib_tooltip as tt
from lib_progressdialog import GenericProgress
from lib_custombuttons import IconTabButton, CustomBitmapButton
from lib_resultreadouts import get_prometheus_capillaries

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
from time import perf_counter
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
        self.figure.subplots_adjust(left=0.12, right=0.8, top=self.Top, bottom=self.Bottom) # right is 0.99 w/o secondary axis
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.SetSizer(self.szr_Canvas)
        self.Fit()
        self.Ratio = 1
        self.ThreeThirty = 0
        self.ThreeFifty = 0
        self.Scattering = 0
        self.ShowInflections = True
        self.InflectionPoints = []
        self.Input = None

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.SampleID = self.Input.loc["CapillaryName"]
        self.fluo, self.deri = self.figure.subplots(nrows=2,ncols=1, sharex=True, gridspec_kw={"height_ratios":[3,1],"hspace":0.0})
        
        if self.Ratio == 1:
            self.fluo.plot(self.Input.loc["Temp"], self.Input.loc["Ratio"], label="Ratio", color="#882255")
            self.fluo.set_ylabel("Ratio 330nm/350nm")
            self.deri.plot(self.Input.loc["Temp"][20:(len(self.Input.loc["Temp"])-20)],
                self.Input.loc["RatioDeriv"][20:(len(self.Input.loc["RatioDeriv"])-20)], label="Derivative", color="#882255")
            if len(self.Input.loc["RatioInflections"]) > 0 and self.ShowInflections == True:
                for i in range(len(self.Input.loc["RatioInflections"])):
                    self.fluo.axvline(self.Input.loc["RatioInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#882255")
                    self.deri.axvline(self.Input.loc["RatioInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#882255")

        if self.ThreeThirty == 1 and self.Ratio == 0:
            self.fluo.plot(self.Input.loc["Temp"], self.Input.loc["330nm"], label="330nm", color="#332288")
            self.fluo.set_ylabel("Fluorescence signal in AU")
            self.deri.plot(self.Input.loc["Temp"][20:(len(self.Input.loc["Temp"])-20)],
                self.Input.loc["330nmDeriv"][20:(len(self.Input.loc["330nmDeriv"])-20)], label="Derivative", color="#332288")
            if len(self.Input.loc["330nmInflections"]) > 0 and self.ShowInflections == True:
                for i in range(len(self.Input.loc["330nmInflections"])):
                    self.fluo.axvline(self.Input.loc["330nmInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#332288")
                    self.deri.axvline(self.Input.loc["330nmInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#332288")

        if self.ThreeFifty == 1 and self.Ratio == 0:
            self.fluo.plot(self.Input.loc["Temp"], self.Input.loc["350nm"], label="350nm", color="#CC6677")
            self.fluo.set_ylabel("Fluorescence signal in AU")
            self.deri.plot(self.Input.loc["Temp"][20:(len(self.Input.loc["Temp"])-20)],
                self.Input.loc["350nmDeriv"][20:(len(self.Input.loc["350nmDeriv"])-20)], label="Derivative", color="#CC6677")
            if len(self.Input.loc["350nmInflections"]) > 0 and self.ShowInflections == True:
                for i in range(len(self.Input.loc["350nmInflections"])):
                    self.fluo.axvline(self.Input.loc["350nmInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#CC6677")
                    self.deri.axvline(self.Input.loc["350nmInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#CC6677")

        if self.Scattering == 1:
            # Test to see if conversion factor is needed for secondary axis, then calculate conversion factor
            self.ScatteringOnly = False
            self.min_scatter = min(self.Input.loc["Scattering"])
            self.max_scatter = max(self.Input.loc["Scattering"])
            self.min_fluo = 0
            if self.Ratio == 1:
                max_ratio = max(self.Input.loc["Ratio"])
                if self.max_scatter < max_ratio:
                    self.sec_axis_corr_fact = max_ratio/self.max_scatter
                else:
                    self.sec_axis_corr_fact = self.max_scatter/max_ratio
            elif self.ThreeFifty == 1 and self.ThreeThirty == 1:
                max_thirty = max(self.Input.loc["330nm"])
                min_thirty = min(self.Input.loc["330nm"])
                max_fifty = max(self.Input.loc["350nm"])
                min_fifty = min(self.Input.loc["350nm"])
                if max_thirty > max_fifty:
                    max_fluor = max_thirty
                else:
                    max_fluor = max_fifty
                if self.max_scatter < max_fluor:
                    self.sec_axis_corr_fact = self.max_scatter/max_fluor
                else:
                    self.sec_axis_corr_fact = max_fluor/self.max_scatter
                if min_thirty > min_fifty:
                    self.min_fluo = min_fifty
                else:
                    self.min_fluo = min_thirty
            elif self.ThreeFifty == 1 and self.ThreeThirty == 0:
                max_fifty = max(self.Input.loc["350nm"])
                if self.max_scatter < max_fifty:
                    self.sec_axis_corr_fact = self.max_scatter/max_fifty
                else:
                    self.sec_axis_corr_fact = max_fifty/self.max_scatter
                self.min_fluo = min(self.Input.loc["350nm"])
            elif self.ThreeFifty == 0 and self.ThreeThirty == 1:
                max_thirty = max(self.Input.loc["330nm"])
                if self.max_scatter < max_thirty:
                    self.sec_axis_corr_fact = self.max_scatter/(max_thirty-self.min_fluo)
                else:
                    self.sec_axis_corr_fact = (max_thirty-self.min_fluo)/self.max_scatter
                self.min_fluo = min(self.Input.loc["330nm"])
            else:
                self.sec_axis_corr_fact = 1
                self.min_fluo = 0
                self.ScatteringOnly = True
            # Apply conversion factor
            # Adjust scattering
            lst_AdjustedScattering = []
            for i in range(len(self.Input.loc["Scattering"])):
                lst_AdjustedScattering.append(self.Input.loc["Scattering"][i]/self.sec_axis_corr_fact)
            self.fluo.plot(self.Input.loc["Temp"], lst_AdjustedScattering, label="Scattering", color="#117733")
            # Adjust derivative
            lst_AdjustedScatteringDeriv = []
            for i in range(len(self.Input.loc["ScatteringDeriv"])):
                lst_AdjustedScatteringDeriv.append(self.Input.loc["ScatteringDeriv"][i]/self.sec_axis_corr_fact)
            self.deri.plot(self.Input.loc["Temp"][20:(len(self.Input.loc["Temp"])-20)],
                lst_AdjustedScatteringDeriv[20:(len(lst_AdjustedScatteringDeriv)-20)], label="Derivative", color="#117733")
            if len(self.Input.loc["ScatteringInflections"]) > 0 and self.ShowInflections == True:
                for i in range(len(self.Input.loc["ScatteringInflections"])):
                    self.fluo.axvline(self.Input.loc["ScatteringInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#117733")
                    self.deri.axvline(self.Input.loc["ScatteringInflections"][i],0,1,linestyle="--",linewidth=1.0,color="#117733")

            if self.ScatteringOnly == False:
                secax_y = self.fluo.secondary_yaxis("right", functions=(self.scattertofluorescence, self.fluorescencetoscatter))
                secax_y.set_ylabel(r"Scattering in AU")
                secax_y_deriv = self.deri.secondary_yaxis("right", functions=(self.scattertofluorescence, self.fluorescencetoscatter))
                secax_y_deriv.set_ylabel(r"Derivative")
            else:
                self.fluo.set_ylabel(r"Scattering in AU")
        # Determine whether there is a secondary axis and therefore the figure needs to be smaller
        if self.Scattering == 0:
            self.figure.subplots_adjust(left=0.12, right=0.99, top=self.Top , bottom=self.Bottom)
        else:
            if self.ScatteringOnly == True:
                self.figure.subplots_adjust(left=0.12, right=0.99, top=self.Top , bottom=self.Bottom)
            else:
                self.figure.subplots_adjust(left=0.12, right=0.9, top=self.Top , bottom=self.Bottom)

        self.deri.set_ylabel("Derivative")
        self.deri.set_xlabel("Temperature (" + chr(176) + "C)") # degree symbol!
        self.fluo.set_title(self.SampleID) # Sample ID
        self.fluo.legend()
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.draw()
        self.Thaw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def DataToClipboard(self, event):
        data = {}
        data["Temperture"] = self.Input.loc["Temp"]
        if self.Ratio == 1:
            data["Ratio"] = self.Input.loc["Ratio"]
            data["Ratio_Derivative"] = self.Input.loc["RatioDeriv"]
        elif self.ThreeThirty == 1:
            data["330nm"] = self.Input.loc["330nm"]
            data["330nm_Derivative"] = self.Input.loc["330nmDeriv"]
        elif self.ThreeFifty == 1:
            data["350nm"] = self.Input.loc["350nm"]
            data["350nm_Derivative"] = self.Input.loc["350nmDeriv"]
        elif self.Scattering == 1:
            data["Scattering"] = self.Input.loc["Scattering"]
            data["Scattering_Derivative"] = self.Input.loc["ScatteringDeriv"]
        pd.DataFrame(data=data).to_clipboard(header=True, index=False)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def scattertofluorescence(self, x):
        return x*self.sec_axis_corr_fact

    def fluorescencetoscatter(self, x):
        return x/self.sec_axis_corr_fact

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
        self.IDs = ["","","","","","","",""]
        self.CapIndices = ["","","","","","","",""]
        self.Temp = [[],[],[],[],[],[],[],[]]
        self.Ratio = [[],[],[],[],[],[],[],[]]
        self.RatioDeriv = [[],[],[],[],[],[],[],[]]
        self.RatioInflections = [[],[],[],[],[],[],[],[]]
        self.ThreeThirty = [[],[],[],[],[],[],[],[]]
        self.ThreeThirtyDeriv = [[],[],[],[],[],[],[],[]]
        self.ThreeThirtyInflections = [[],[],[],[],[],[],[],[]]
        self.ThreeFifty = [[],[],[],[],[],[],[],[]]
        self.ThreeFiftyDeriv = [[],[],[],[],[],[],[],[]]
        self.ThreeFiftyInflections = [[],[],[],[],[],[],[],[]]
        self.Scattering = [[],[],[],[],[],[],[],[]]
        self.ScatteringDeriv = [[],[],[],[],[],[],[],[]]
        self.ScatteringInflections = [[],[],[],[],[],[],[],[]]
        self.Display = 0
        self.Inflections = True
        self.Preview = True
        self.PreviewID = ""
        self.PreviewCapIndex = ""
        self.PreviewTemp = []
        self.PreviewRatio = []
        self.PreviewRatioDeriv = []
        self.PreviewRatioInflections = []
        self.PreviewThreeThirty = []
        self.PreviewThreeThirtyDeriv = []
        self.PreviewThreeThirtyInflections = []
        self.PreviewThreeFifty = []
        self.PreviewThreeFiftyDeriv = []
        self.PreviewThreeFiftyInflections = []
        self.PreviewScattering = []
        self.PreviewScatteringDeriv = []
        self.PreviewScatteringInflections = []
        self.ColourChoices = cs.TM_RGBA_List
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.SetSizer(self.szr_Canvas)
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.fluo, self.deri = self.figure.subplots(nrows=2,ncols=1, sharex=True, gridspec_kw={"height_ratios":[3,1],"hspace":0.0})
        if self.PreviewCapIndex in self.CapIndices:
            alreadythere = True
        else:
            alreadythere = False
        # Actual Plot: Normalisation useful for comparison graph!
        # Show Ratio
        if self.Display == 0:
            self.fluo.set_ylabel("Fluorescence signal in AU")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temp[i], self.Ratio[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temp[i][20:(len(self.Temp[i])-20)], self.RatioDeriv[i][20:(len(self.RatioDeriv[i])-20)], label=self.IDs[i], color=self.Colours[i])
                    if len(self.RatioInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.RatioInflections[i])):
                            self.fluo.axvline(self.RatioInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.RatioInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and alreadythere == False:
                self.fluo.plot(self.PreviewTemp, self.PreviewRatio, label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                self.deri.plot(self.PreviewTemp[20:(len(self.PreviewTemp)-20)], self.PreviewRatioDeriv[20:(len(self.PreviewRatioDeriv)-20)], label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                if len(self.PreviewRatioInflections) > 0 and self.Inflections == True:
                    for i in range(len(self.PreviewRatioInflections)):
                        self.fluo.axvline(self.PreviewRatioInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
                        self.deri.axvline(self.PreviewRatioInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
        # Show 330nm
        elif self.Display == 1:
            self.fluo.set_ylabel("Fluorescence signal in AU")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temp[i], self.ThreeThirty[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temp[i][20:(len(self.Temp[i])-20)], self.ThreeThirtyDeriv[i][20:(len(self.ThreeThirtyDeriv[i])-20)], label=self.IDs[i], color=self.Colours[i])
                    if len(self.ThreeThirtyInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.ThreeThirtyInflections[i])):
                            self.fluo.axvline(self.ThreeThirtyInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.ThreeThirtyInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and alreadythere == False:
                self.fluo.plot(self.PreviewTemp, self.PreviewThreeThirty, label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                self.deri.plot(self.PreviewTemp[20:(len(self.PreviewTemp)-20)], self.PreviewThreeThirtyDeriv[20:(len(self.PreviewThreeThirtyDeriv)-20)], label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                if len(self.PreviewThreeThirtyInflections) > 0 and self.Inflections == True:
                    for i in range(len(self.PreviewThreeThirtyInflections)):
                        self.fluo.axvline(self.PreviewThreeThirtyInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
                        self.deri.axvline(self.PreviewThreeThirtyInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
        # Show 350nm
        elif self.Display == 2:
            self.fluo.set_ylabel("Fluorescence signal in AU")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temp[i], self.ThreeFifty[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temp[i][20:(len(self.Temp[i])-20)], self.ThreeFiftyDeriv[i][20:(len(self.ThreeFiftyDeriv[i])-20)], label=self.IDs[i], color=self.Colours[i])
                    if len(self.ThreeFiftyInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.ThreeFiftyInflections[i])):
                            self.fluo.axvline(self.ThreeFiftyInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.ThreeFiftyInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and alreadythere == False:
                self.fluo.plot(self.PreviewTemp, self.PreviewThreeFifty, label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                self.deri.plot(self.PreviewTemp[20:(len(self.PreviewTemp)-20)], self.PreviewThreeFiftyDeriv[20:(len(self.PreviewThreeFiftyDeriv)-20)], label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                if len(self.PreviewThreeFiftyInflections) > 0 and self.Inflections == True:
                    for i in range(len(self.PreviewThreeFiftyInflections)):
                        self.fluo.axvline(self.PreviewThreeFiftyInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
                        self.deri.axvline(self.PreviewThreeFiftyInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
        # Show Scattering
        elif self.Display == 3:
            self.fluo.set_ylabel("Light scattering in AU")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.fluo.plot(self.Temp[i], self.Scattering[i], label=self.IDs[i], color=self.Colours[i])
                    self.deri.plot(self.Temp[i][20:(len(self.Temp[i])-20)], self.ScatteringDeriv[i][20:(len(self.ScatteringDeriv[i])-20)], label=self.IDs[i], color=self.Colours[i])
                    if len(self.ScatteringInflections[i]) > 0 and self.Inflections == True:
                        for j in range(len(self.ScatteringInflections[i])):
                            self.fluo.axvline(self.ScatteringInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
                            self.deri.axvline(self.ScatteringInflections[i][j],0,1,linestyle="--",linewidth=1.0,color=self.Colours[i])
            if self.Preview == True and alreadythere == False:
                self.fluo.plot(self.PreviewTemp, self.PreviewScattering, label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                self.deri.plot(self.PreviewTemp[20:(len(self.PreviewTemp)-20)], self.PreviewScatteringDeriv[20:(len(self.PreviewScatteringDeriv)-20)], label=self.PreviewID, color=cs.TMPaleGrey_Hex)
                if len(self.PreviewScatteringInflections) > 0 and self.Inflections == True:
                    for i in range(len(self.PreviewScatteringInflections)):
                        self.fluo.axvline(self.PreviewScatteringInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)
                        self.deri.axvline(self.PreviewScatteringInflections[i],0,1,linestyle="--",linewidth=1.0,color=cs.TMPaleGrey_Hex)

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
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.draw()
        self.Thaw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def DataToClipboard(self, event):
        data = {}
        if self.Display == 0:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Temp"] = self.Temp[i]
                    data[self.IDs[i]+"_Ratio"] = self.Ratio[i]
                    data[self.IDs[i]+"_Derivative"] = self.RatioDeriv[i]
        elif self.Display == 1:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Temp"] = self.Temp[i]
                    data[self.IDs[i]+"_330nm"] = self.ThreeThirty[i]
                    data[self.IDs[i]+"_Derivative"] = self.ThreeThirtyDeriv[i]
        elif self.Display == 2:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Temp"] = self.Temp[i]
                    data[self.IDs[i]+"_350nm"] = self.ThreeFifty[i]
                    data[self.IDs[i]+"_Derivative"] = self.ThreeFiftyDeriv[i]
        elif self.Display == 3:
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    data[self.IDs[i]+"_Temp"] = self.Temp[i]
                    data[self.IDs[i]+"_Scattering"] = self.Scattering[i]
                    data[self.IDs[i]+"_Derivative"] = self.ScatteringDeriv[i]
        pd.DataFrame(data=data).to_clipboard(header=True, index=False)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

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

    def Draw(self,df_rawdata,str_Plate):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        # If the canvas already exists, we are updating the plot. Therefore, the old needs deleting.
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(str_Plate)
        # Categorise the inflection points based on initial fluorescence
        lst_Index =[]
        lst_LowInitial = []
        lst_MediumInitial = []
        lst_HighInitial = []
        for i in range(len(df_rawdata)):
            lst_Index.append(i)
            if df_rawdata.loc[i,"Initial"] == 0:
                lst_LowInitial.append(df_rawdata.Tm[i])
                lst_MediumInitial.append(np.nan)
                lst_HighInitial.append(np.nan)
            elif df_rawdata.loc[i,"Initial"] == 1:
                lst_LowInitial.append(np.nan)
                lst_MediumInitial.append(df_rawdata.Tm[i])
                lst_HighInitial.append(np.nan)
            elif df_rawdata.loc[i,"Initial"] == 2:
                lst_LowInitial.append(np.nan)
                lst_MediumInitial.append(np.nan)
                lst_HighInitial.append(df_rawdata.Tm[i])
            else:
                lst_LowInitial.append(np.nan)
                lst_MediumInitial.append(np.nan)
                lst_HighInitial.append(np.nan)
        self.axes.set_xlabel("Compounds")
        self.axes.scatter(lst_Index, lst_LowInitial, marker="o", label="Low initial fluorescence", color="#44b59a", s=10, picker=1)#, edgecolors ="black")
        self.axes.scatter(lst_Index, lst_MediumInitial, marker="o", label="Medium initial fluorescence", color="#cc640a", s=10, picker=1)#, edgecolors ="black")
        self.axes.scatter(lst_Index, lst_HighInitial, marker="o", label="High initial fluorescence", color="#aa4499", s=10, picker=1)#, edgecolors ="black")
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
            for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                # For the x axis (log scale), we have to adjust relative
                if x >= (i-2) and x <= (i+2):
                    # for the y axis, we have to adjust absolute
                    Tm = round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"RatioInflections"][0],1)
                    str_SampleID = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
                    str_Well = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"]
                    str_DTm = str(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"NormDTm"])
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

    def PlotToClipboard(self, event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

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
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"],
                    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        # Write fresh label
        self.tabname.lbl_DetailsTm.SetLabel("Tm: " + str(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawInflections"][0]))
        # Update tick box
        self.tabname.chk_DetailFit.SetValue(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])

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
    def __init__(self, parent, rightclick):
        super(GridContextMenu, self).__init__()
        """
        Context menu to cut, copy, paste, clear and fill down from capillaries grid.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.parent = parent
        self.grid = rightclick.GetEventObject()

        if col == 6:
            self.mi_Sample = wx.MenuItem(self, wx.ID_ANY, u"Sample capillary", wx.EmptyString, wx.ITEM_NORMAL)
            self.Append(self.mi_Sample)
            self.Bind(wx.EVT_MENU, lambda event: self.Sample(event,  row, col), self.mi_Sample)

            self.mi_Reference = wx.MenuItem(self, wx.ID_ANY, u"Reference capillary", wx.EmptyString, wx.ITEM_NORMAL)
            self.Append(self.mi_Reference)
            self.Bind(wx.EVT_MENU, lambda event: self.Reference(event,  row, col), self.mi_Reference)

            self.AppendSeparator()

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

    def Sample(self, event, row, col):
        self.grid.SetCellValue(row, col, "Sample")

    def Reference(self, event, row, col):
        self.grid.SetCellValue(row, col, "Reference")

    def FillDown(self, event, row, col):
        filler = self.grid.GetCellValue(row,col)
        for i in range(row,self.grid.GetNumberRows(),1):
            self.grid.SetCellValue(i, col, filler)

    def Copy(self, event, row, col):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def Cut(self, event, row, col):
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)

    def Paste(self, event, row, col):
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grid.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def Clear(self, event, row, col):
        self.grid.SetCellValue(row, col, "")
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) > 0:
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grid.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GetGridSelection(self):
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
        clr_Tabs = cs.BgUltraLight

        self.parent = parent

        # Initialise instance wide variables with default values
        self.Title = "nano Differential Scanning Fluorimetry"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "thermal_shift"
        self.str_Shorthand = "NDSF"
        self.AssayPath = os.path.dirname(os.path.realpath(__file__))
        self.bol_AssayDetailsCompleted = False
        self.bol_AssayDetailsChanged = False
        self.bol_LayoutDefined = True # There is no plate layout for this assay
        self.bol_TransferLoaded = True # There are no transfer files! Set to true to pass check in ProcessData()
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
        self.str_DatafileExtension = ".xlsx"
        self.str_SaveFilePath = ""
        self.str_DataPath = ""
        self.str_TransferPath = ""
        self.Device = "prometheus"

        self.dfr_Layout = pd.DataFrame()
        self.dfr_Capillaries = pd.DataFrame()

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
        self.tab_Details.SetBackgroundColour(clr_Tabs)
        self.szr_Assay = wx.BoxSizer(wx.VERTICAL)


        self.szr_Details = wx.BoxSizer(wx.HORIZONTAL)
        # Left Sizer
        self.szr_Left = wx.BoxSizer(wx.VERTICAL)
        # Capillaries panel
        self.pnl_Capillaries = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(710,-1), wx.TAB_TRAVERSAL)
        self.pnl_Capillaries.SetBackgroundColour(clr_Panels)
        self.szr_Capillaries = wx.BoxSizer(wx.VERTICAL)
        self.szr_CapillariesTop = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_Capillaries = wx.StaticText(self.pnl_Capillaries, wx.ID_ANY, u"Capillaries", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Capillaries.Wrap(-1)
        self.szr_CapillariesTop.Add(self.lbl_Capillaries, 0, wx.ALL, 0)
        self.szr_CapillariesTop.Add((-1,-1))
        #self.chk_ExcludeEmpty = wx.CheckBox(self.pnl_Capillaries, wx.ID_ANY, u"Hide empty positions", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.szr_CapillariesTop.Add(self.chk_ExcludeEmpty, 0, wx.ALL, 0)

        self.szr_Capillaries.Add(self.szr_CapillariesTop, 0, wx.ALL, 5)
        self.szr_CapillariesFile = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_CapillariesFileName = wx.StaticText(self.pnl_Capillaries, wx.ID_ANY, u"Select a Prometheus raw data file:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_CapillariesFile.Add(self.lbl_CapillariesFileName, 0, wx.ALL, 0)
        self.szr_CapillariesFile.Add((10,-1))
        self.fpk_Data = tab.CustomFilePicker(self.pnl_Capillaries, u"Select a file", u"*.xlsx", (450,-1))
        self.szr_CapillariesFile.Add(self.fpk_Data, 0, wx.ALL, 0)
        self.szr_Capillaries.Add(self.szr_CapillariesFile, 0, wx.ALL, 5)
        self.grd_Capillaries = wx.grid.Grid(self.pnl_Capillaries, wx.ID_ANY, wx.DefaultPosition, wx.Size(710,-1), 0)
        self.grd_Capillaries.SetDefaultCellBackgroundColour(clr_Panels)
        # Grid
        self.grd_Capillaries.CreateGrid(0, 7)
        self.grd_Capillaries.EnableEditing(False)
        self.grd_Capillaries.EnableGridLines(True)
        self.grd_Capillaries.EnableDragGridSize(False)
        self.grd_Capillaries.SetMargins(0, 0)
        # Columns
        self.grd_Capillaries.SetColLabelValue(0, "Capillary name")
        self.grd_Capillaries.SetColSize(0,90)
        self.grd_Capillaries.SetColLabelValue(1, "Purification ID")
        self.grd_Capillaries.SetColSize(1,105)
        self.grd_Capillaries.SetColLabelValue(2, chr(181)+"M")
        self.grd_Capillaries.SetColSize(2,30)
        self.grd_Capillaries.SetColLabelValue(3, "Sample ID")
        self.grd_Capillaries.SetColSize(3,105)
        self.grd_Capillaries.SetColLabelValue(4, chr(181)+"M")
        self.grd_Capillaries.SetColSize(4,30)
        self.grd_Capillaries.SetColLabelValue(5, "Buffer")
        self.grd_Capillaries.SetColSize(5,200)
        self.grd_Capillaries.SetColLabelValue(6, "Sample/Reference")
        self.grd_Capillaries.SetColSize(6,115)
        self.grd_Capillaries.EnableDragColMove(False)
        self.grd_Capillaries.EnableDragColSize(False)
        self.grd_Capillaries.SetColLabelSize(19)
        self.grd_Capillaries.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Rows
        for row in range(self.grd_Capillaries.GetNumberRows()):
            self.grd_Capillaries.SetRowSize(row, 19)
            self.grd_Capillaries.SetRowLabelValue(row, str(row+1))
        self.grd_Capillaries.EnableDragColMove(False)
        self.grd_Capillaries.EnableDragRowSize(False)
        self.grd_Capillaries.SetRowLabelSize(19)
        self.grd_Capillaries.SetRowLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        # Cell Defaults
        self.grd_Capillaries.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        #self.grd_Capillaries.AutoSizeColumns()
        self.grd_Capillaries.SingleSelection = (0,0)

        self.szr_Capillaries.Add(self.grd_Capillaries, 0, wx.ALL, 5)
        self.pnl_Capillaries.SetSizer(self.szr_Capillaries)
        self.pnl_Capillaries.Layout()
        self.szr_Capillaries.Fit(self.pnl_Capillaries)
        self.szr_Left.Add(self.pnl_Capillaries, 0, wx.EXPAND|wx.ALL, 5)
        self.szr_Details.Add(self.szr_Left, 0, wx.EXPAND, 5)

        # Right Sizer
        self.szr_Right = wx.BoxSizer(wx.VERTICAL)
        # Date of experiment
        self.pnl_Date = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(225,-1), wx.TAB_TRAVERSAL)
        self.pnl_Date.SetBackgroundColour(clr_Panels)
        self.pnl_Date.SetMaxSize(wx.Size(225,-1))
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
        # ELN Panel
        self.pnl_ELN = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(225,-1), wx.TAB_TRAVERSAL)
        self.pnl_ELN.SetBackgroundColour(clr_Panels)
        self.pnl_ELN.SetMaxSize(wx.Size(225,-1))
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
        # Solvent Panel
        self.pnl_Solvent = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(225,-1), wx.TAB_TRAVERSAL)
        self.pnl_Solvent.SetBackgroundColour(clr_Panels)
        self.pnl_Solvent.SetMaxSize(wx.Size(225,-1))
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
        # Plate ID Panel
        self.pnl_PlateID = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(225,-1), wx.TAB_TRAVERSAL)
        self.pnl_PlateID.SetBackgroundColour(clr_Panels)
        self.pnl_PlateID.SetMaxSize(wx.Size(225,-1))
        self.szr_PlateID = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_PlateID = wx.CheckBox(self.pnl_PlateID, wx.ID_ANY, u"Use PlateID for database:", wx.DefaultPosition, wx.Size(-1,-1), 0)
        self.chk_PlateID.SetValue(self.bol_PlateID)
        self.szr_PlateID.Add(self.chk_PlateID, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_PlateID = wx.TextCtrl(self.pnl_PlateID, wx.ID_ANY, u"X999A", wx.DefaultPosition, wx.Size(60,-1), 0)
        self.txt_PlateID.SetBackgroundColour(clr_TextBoxes)
        self.szr_PlateID.Add(self.txt_PlateID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pnl_PlateID.SetSizer(self.szr_PlateID)
        self.pnl_PlateID.Layout()
        self.szr_PlateID.Fit(self.pnl_PlateID)
        self.szr_Right.Add(self.pnl_PlateID, 0, wx.EXPAND |wx.ALL, 5)
        ###
        self.szr_Details.Add(self.szr_Right, 0, wx.EXPAND, 5)
        self.szr_Assay.Add(self.szr_Details, 0, wx.EXPAND, 5)

        # Finalise
        self.tab_Details.SetSizer(self.szr_Assay)
        self.tab_Details.Layout()
        self.szr_Assay.Fit(self.tab_Details)
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", True)

        ###  ####  ### #  # #  #####  ###
        #  # #    #    #  # #    #   #
        ###  ###   ##  #  # #    #    ##
        #  # #       # #  # #    #      #
        #  # #### ###   ##  #### #   ###  #####################################################################################################################

        # Start Building
        self.pnl_Results = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Results.SetBackgroundColour(clr_Tabs)
        self.szr_Results = wx.BoxSizer(wx.VERTICAL)

        self.bSizer12 = wx.BoxSizer(wx.HORIZONTAL)

        # Sample List
        self.szr_SampleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectSample = wx.StaticText(self.pnl_Results, wx.ID_ANY, u"Select a sample", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SelectSample.Wrap(-1)
        self.szr_SampleList.Add(self.lbl_SelectSample, 0, wx.ALL, 5)
        self.lbc_Samples = wx.ListCtrl(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(350,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Capillary index")
        self.lbc_Samples.SetColumnWidth(0,80)
        self.lbc_Samples.InsertColumn(1,"Capillary name")
        self.lbc_Samples.SetColumnWidth(1,80)
        self.lbc_Samples.InsertColumn(2,"SampleID")
        self.lbc_Samples.SetColumnWidth(2,90)
        self.lbc_Samples.InsertColumn(3,"Inflection")
        self.lbc_Samples.SetColumnWidth(3,35)
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
        self.btn_SummaryPlot.Notebook = self.sbk_ResultPlots
        self.btn_SummaryPlot.Group = self.dic_PlotTabButtons

        # First page in simplebook: Resultsplot ===============================================================================================================
        self.pnl_IndividualPlot = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(800,470), wx.TAB_TRAVERSAL)
        self.szr_Plot = wx.BoxSizer(wx.HORIZONTAL)
        self.pnl_Plot = DSFPlotPanel(self.pnl_IndividualPlot,(600,470),self)
        self.szr_Plot.Add(self.pnl_Plot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_BesidePlot = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_IndiPlotShow = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Display = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Display.Wrap(-1)
        self.szr_IndiPlotShow.Add(self.lbl_Display, 0, wx.ALL, 5)
        self.chk_IndiPlotRatio = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Ratio", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_IndiPlotShow.Add(self.chk_IndiPlotRatio, 0, wx.ALL, 5)
        self.chk_IndiPlot330 = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"330nm", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_IndiPlotShow.Add(self.chk_IndiPlot330, 0, wx.ALL, 5)
        self.chk_IndiPlot350 = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"350nm", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_IndiPlotShow.Add(self.chk_IndiPlot350, 0, wx.ALL, 5)
        self.chk_IndiPlotScattering = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Scattering", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_IndiPlotShow.Add(self.chk_IndiPlotScattering, 0, wx.ALL, 5)
        self.chk_InflectionsIndividual = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Show inflection points", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_InflectionsIndividual.SetValue(True)
        self.szr_IndiPlotShow.Add(self.chk_InflectionsIndividual, 0, wx.ALL, 5)
        self.m_staticline101 = wx.StaticLine(self.pnl_IndividualPlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_IndiPlotShow.Add(self.m_staticline101, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_BesidePlot.Add(self.szr_IndiPlotShow, 0, wx.EXPAND, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Fit this data", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Details.Add(self.chk_Fit, 0, wx.ALL, 5)
        # Tm
        self.lbl_Tm = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Tm", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Tm.Wrap(-1)
        self.szr_Details.Add(self.lbl_Tm, 0, wx.ALL, 5)
        # Separator line
        self.m_staticline14 = wx.StaticLine(self.pnl_IndividualPlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_Details.Add(self.m_staticline14, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_BesidePlot.Add(self.szr_Details, 0, wx.EXPAND, 5)
        # Export plot
        self.szr_ExportPlot = wx.BoxSizer(wx.VERTICAL)
        self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot, u"Clipboard", 0, (130,25))
        self.szr_ExportPlot.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportToFile", 0, (104,25))
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
        self.plt_MultiPlotPanel = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(900,550), wx.TAB_TRAVERSAL)
        self.szr_MultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_MultiPlot = DSFMultiPlotPanel(self.plt_MultiPlotPanel,(600,550),self)
        self.szr_MultiPlot.Add(self.plt_MultiPlot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_MultiPlotRight =  wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_MultiPlotShow = wx.FlexGridSizer(5, 2, 0, 0)
        self.szr_MultiPlotShow.SetFlexibleDirection(wx.BOTH)
        self.szr_MultiPlotShow.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.lbl_MultiPlotShow = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_MultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((5,5), 0, wx.ALL, 5)
        self.rad_MultiPlotRatio = wx.RadioButton(self.plt_MultiPlotPanel, wx.ID_ANY, u"Ratio", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotRatio, 0, wx.ALL, 5)
        self.chk_InflectionsMulti = wx.CheckBox(self.plt_MultiPlotPanel, wx.ID_ANY, u"Show inflection points", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_InflectionsMulti.SetValue(True)
        self.szr_MultiPlotShow.Add(self.chk_InflectionsMulti, 0, wx.ALL, 5)
        self.rad_MultiPlot330nm = wx.RadioButton(self.plt_MultiPlotPanel, wx.ID_ANY, u"330nm", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlot330nm, 0, wx.ALL, 5)
        self.chk_PreviewPlot = wx.CheckBox(self.plt_MultiPlotPanel, wx.ID_ANY, u"Preview selected sample", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_PreviewPlot.SetValue(True) 
        self.szr_MultiPlotShow.Add(self.chk_PreviewPlot, 0, wx.ALL, 5)
        self.rad_MultiPlot350nm = wx.RadioButton(self.plt_MultiPlotPanel, wx.ID_ANY, u"350nm", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlot350nm, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((5,5), 0, wx.ALL, 5)
        self.rad_MultiPlotScattering = wx.RadioButton(self.plt_MultiPlotPanel, wx.ID_ANY, u"Scattering", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotScattering, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((5,5), 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotShow, 0, wx.EXPAND, 5)
        # Separator line
        self.lin_MultiPlotShow = wx.StaticLine(self.plt_MultiPlotPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
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
        self.lbl_Column1 = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u"Sample ID/Name", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column1.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column1, 0, wx.ALL, 3)
        self.lbl_Column2 = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u"Colour", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column2.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column2, 0, wx.ALL, 3)
        self.lbl_Column3 = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Column3.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column3, 0, wx.ALL, 3)
        self.lbl_Comlumn4 = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
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
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]] = wx.StaticText(self.plt_MultiPlotPanel, wx.ID_ANY, u"no sample", wx.DefaultPosition, wx.DefaultSize, 0)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Wrap(-1)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Enable(False)
            self.szr_MultiPlotList.Add(self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]], 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_BitmapCombos.append("self.bmc_Sample" + str(i))
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]] = wx.adv.BitmapComboBox(self.plt_MultiPlotPanel, wx.ID_ANY, u"Combo!", wx.DefaultPosition, wx.Size(100,25), self.lst_ColourOptions, wx.CB_READONLY)
            for j in range(len(self.lst_ColourBitmaps)):
                self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetItemBitmap(j,self.lst_ColourBitmaps[j])
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetSelection(i)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Index = i
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Enable(False)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Bind(wx.EVT_COMBOBOX, self.ColourSelect)
            self.szr_MultiPlotList.Add(self.dic_BitmapCombos[self.lst_BitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_AddButtons.append("self.btn_Add" + str(i))
            self.dic_AddButtons[self.lst_AddButtons[i]] = CustomBitmapButton(self.plt_MultiPlotPanel, u"Plus", 0, (25,25))
            self.dic_AddButtons[self.lst_AddButtons[i]].Index = i
            self.dic_AddButtons[self.lst_AddButtons[i]].Bind(wx.EVT_BUTTON, self.AddGraph)
            self.szr_MultiPlotList.Add(self.dic_AddButtons[self.lst_AddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_RemoveButtons.append("self.btn_Add" + str(i))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]] = CustomBitmapButton(self.plt_MultiPlotPanel, u"Minus", 0, (25,25))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Index = i
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Bind(wx.EVT_BUTTON, self.RemoveGraph)
            self.szr_MultiPlotList.Add(self.dic_RemoveButtons[self.lst_RemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_MultiPlotRight = wx.StaticLine(self.plt_MultiPlotPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export
        self.szr_ExportMultiPlot = wx.BoxSizer(wx.VERTICAL)
        self.btn_SummaryPlotToClipboard = CustomBitmapButton(self.plt_MultiPlotPanel, u"Clipboard", 0, (130,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_SummaryPlotToPNG = CustomBitmapButton(self.plt_MultiPlotPanel, u"ExportToFile", 0, (104,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_ExportMultiPlot, 0, wx.ALL, 5)
        ##########################################################################
        self.szr_MultiPlot.Add(self.szr_MultiPlotRight, 0, wx.EXPAND, 5)
        self.plt_MultiPlotPanel.SetSizer(self.szr_MultiPlot)
        self.plt_MultiPlotPanel.Layout()
        self.szr_MultiPlot.Fit(self.plt_MultiPlotPanel)
        self.sbk_ResultPlots.AddPage(self.plt_MultiPlotPanel, u"Summary Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # =====================================================================================================================================================

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
        self.tabs_Analysis.AddPage(self.tab_PlateMap, u"Export Plate Map to Database", False)

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
        self.fpk_Data.Bind(self.ReadPrometheusOutput)
        #self.chk_ExcludeEmpty.Bind(wx.EVT_CHECKBOX, self.HideEmptyPositions)
        self.chk_PlateID.Bind(wx.EVT_CHECKBOX, self.UsePlateID)
        self.grd_Capillaries.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.EditCells)
        self.grd_Capillaries.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OpenGridContextMenu)
        self.grd_Capillaries.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.SampleOrReference)
        self.grd_Capillaries.Bind(wx.EVT_KEY_DOWN, self.OnKeyPress)
        self.grd_Capillaries.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.SingleSelection)
        
        # Tab 2: Transfer and Data Files

        # Tab 3: Results
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowCurve)
        #self.lbc_Samples.Bind(wx.EVT_MOTION, self.MouseOver)
        self.lbc_Samples.Bind(wx.EVT_LEAVE_WINDOW, self.ClosePlotToolTip)
        self.btn_ExportResultsTable.Bind(wx.EVT_BUTTON, self.ExportResultsTable)
        self.chk_IndiPlotRatio.Bind(wx.EVT_CHECKBOX, self.IndiPlotRatio)
        self.chk_IndiPlot330.Bind(wx.EVT_CHECKBOX, self.IndiPlot330nm)
        self.chk_IndiPlot350.Bind(wx.EVT_CHECKBOX, self.IndiPlot350nm)
        self.chk_IndiPlotScattering.Bind(wx.EVT_CHECKBOX, self.IndiPlotScattering)
        self.chk_InflectionsIndividual.Bind(wx.EVT_CHECKBOX, self.ToggleInflectionsIndividual)
        self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.ToggleFit)
        self.chk_InflectionsMulti.Bind(wx.EVT_CHECKBOX, self.ToggleInflectionsMulti)
        self.rad_MultiPlotRatio.Bind(wx.EVT_RADIOBUTTON, self.MultiPlotRatio)
        self.rad_MultiPlot330nm.Bind(wx.EVT_RADIOBUTTON, self.MultiPlot330nm)
        self.rad_MultiPlot350nm.Bind(wx.EVT_RADIOBUTTON, self.MultiPlot350nm)
        self.rad_MultiPlotScattering.Bind(wx.EVT_RADIOBUTTON, self.MultiPlotScattering)
        self.chk_PreviewPlot.Bind(wx.EVT_CHECKBOX, self.TogglePreviewPlot)
        self.btn_FigToClipboard.Bind(wx.EVT_BUTTON, self.pnl_Plot.PlotToClipboard)
        self.btn_SaveFig.Bind(wx.EVT_BUTTON, self.pnl_Plot.PlotToPNG)
        self.btn_SaveAll.Bind(wx.EVT_BUTTON, self.AllPlotsToPNG)
        self.btn_SummaryPlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToClipboard)
        self.btn_SummaryPlotToPNG.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToPNG)
        
        # Tab 4: ELN Plots

        # Tab 5: Export to Database

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
        if int_NewTab == 1:
            # going to results tab
            if self.bol_ResultsDrawn == False:
                self.PopulateResultsTab()
        elif int_NewTab == 2:
            # going to plots for ELN page tab
            if self.bol_ELNPlotsDrawn == False:
                self.tab_ELNPlots.PopulatePlotsTab(self.dfr_AssayData)
        elif int_NewTab == 3:
            # going to export tab
            if self.bol_ExportPopulated == False:
                self.bol_ExportPopulated = self.tab_Export.Populate()
        elif int_NewTab == 4:
            # going to plate map tab
            if self.bol_PlateMapPopulated == False:
                self.tab_PlateMap.PopulatePlateMapTab()

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

        self.str_DataPath = lst_Paths[1]
        self.str_TransferPath = lst_Paths[0]

        # Assay Details
        self.dfr_Details = dfr_LoadedDetails
        self.str_AssayType = self.dfr_Details.loc["AssayType","Value"]
        
        # No field for purification ID
        # No field for protein concentration
        self.txt_Solvent.SetValue(self.dfr_Details.loc["Solvent","Value"])
        self.txt_Percent.SetValue(str(self.dfr_Details.loc["SolventConcentration","Value"]))
        #self.txt_Buffer.SetValue(self.self.dfr_Details.loc["Buffer","Value"]) # N/A for nanoDSF
        self.txt_ELN.SetValue(self.dfr_Details.loc["ELN","Value"])
        # str_AssayVolume = stre(self.dfr_Details.loc["Solvent","Value"]) # in nL
        self.str_DatafileExtension = self.dfr_Details.loc["DataFileExtension","Value"]
        # Backwards compatibility wild older save files that do not have newer additions in the assay details:
        try:
            self.Device = self.dfr_Details.loc["Device","Value"]
        except:
            self.Device = "prometheus"
            self.dfr_Details.loc["Device","Value"] = self.Device
        try:
            Date = self.dfr_Details.loc["Date","Value"]
            Date = wx.DateTime.FromDMY(int(Date[8:10]), int(Date[5:7]), int(Date[:4]))
            self.tab_Details.DatePicker.SetValue(Date)
        except:
            self.dfr_Details.loc["Date","Value"] = "NA"
        self.fpk_Data.SetPath(self.str_DataPath)
        self.dfr_Capillaries = pd.DataFrame(index=range(len(dfr_Loaded.loc[0,"ProcessedDataFrame"])),
                                            columns=["CapIndex","CapillaryName",
                                                     "PurificationID","ProteinConc",
                                                     "SampleID","SampleConc","Buffer",
                                                     "CapillaryType"])
        self.grd_Capillaries.AppendRows(len(dfr_Loaded.loc[0,"ProcessedDataFrame"]))
        for idx_Capillary in range(len(dfr_Loaded.loc[0,"ProcessedDataFrame"])):
            self.dfr_Capillaries.loc[idx_Capillary,"CapIndex"] = idx_Capillary
            self.grd_Capillaries.SetCellValue(idx_Capillary,0,
                dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"CapillaryName"])
            self.dfr_Capillaries.loc[idx_Capillary,"CapillaryName"] = self.grd_Capillaries.GetCellValue(idx_Capillary,0)
            self.grd_Capillaries.SetCellValue(idx_Capillary,1,
                df.string_or_na(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"PurificationID"]))
            self.dfr_Capillaries.loc[idx_Capillary,"PurificationID"] = self.grd_Capillaries.GetCellValue(idx_Capillary,1)
            self.grd_Capillaries.SetCellValue(idx_Capillary,2,
                df.string_or_na(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"ProteinConc"]))
            self.dfr_Capillaries.loc[idx_Capillary,"ProteinConc"] = self.grd_Capillaries.GetCellValue(idx_Capillary,2)
            self.grd_Capillaries.SetCellValue(idx_Capillary,3,
                df.string_or_na(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"SampleID"]))
            self.dfr_Capillaries.loc[idx_Capillary,"SampleID"] = self.grd_Capillaries.GetCellValue(idx_Capillary,3)
            self.grd_Capillaries.SetCellValue(idx_Capillary,4,
                df.string_or_na(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"SampleConc"]))
            self.dfr_Capillaries.loc[idx_Capillary,"SampleConc"] = self.grd_Capillaries.GetCellValue(idx_Capillary,4)
            self.grd_Capillaries.SetCellValue(idx_Capillary,5,
                df.string_or_na(dfr_Loaded.loc[0,"ProcessedDataFrame"].loc[idx_Capillary,"Buffer"]))
            self.dfr_Capillaries.loc[idx_Capillary,"Buffer"] = self.grd_Capillaries.GetCellValue(idx_Capillary,5)
            if dfr_Loaded.loc[0,"Layout"].loc[0,"WellType"][idx_Capillary] == "r":
                self.grd_Capillaries.SetCellValue(idx_Capillary,6,"Reference")
            elif dfr_Loaded.loc[0,"Layout"].loc[0,"WellType"][idx_Capillary] == "s":
                self.grd_Capillaries.SetCellValue(idx_Capillary,6,"Sample")
            self.dfr_Capillaries.loc[idx_Capillary,"CapillaryType"] = self.grd_Capillaries.GetCellValue(idx_Capillary,6)
            # Colour even rows differently:
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
            self.tab_ELNPlots.PopulatePlotsTab(self.dfr_AssayData)
        self.bol_ExportPopulated = lst_LoadedBoolean[6]
        if self.bol_ExportPopulated == True:
            self.tab_Export.Populate(noreturn = True)
        self.bol_ResultsDrawn = lst_LoadedBoolean[7]
        if self.bol_ResultsDrawn == True:
            self.PopulateResultsTab()
        self.bol_ReviewsDrawn = lst_LoadedBoolean[8]
        self.bol_TransferLoaded = lst_LoadedBoolean[9]
        self.bol_GlobalLayout = lst_LoadedBoolean[10]
        self.bol_PlateID = lst_LoadedBoolean[11]
        self.bol_PlateMapPopulated = lst_LoadedBoolean[12]
        # And of course this has been previously saved since we are loading it from a file
        self.bol_PreviouslySaved = True

        # Populate transfer/data file tab

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
        self.txt_PlateID.SetValue(self.dfr_Layout.at[0,"PlateID"])
        self.txt_PlateID.Enable(lst_LoadedBoolean[11])
        self.tabs_Analysis.EnablePlateMap(lst_LoadedBoolean[11])
        self.bol_LayoutDefined = True
        
        self.tabs_Analysis.EnableAll(True)

    def ProcessData(self, dlg_Progress):
        """
        This function processes the data.
        First, assay details are saved to variables again (in case of updates).
        If the transfer file has been loaded, plates will be assigned (i.e.
        raw data files/entries matched with transfer file entries)
        Any previously displayed data will then be erased.
        Function get_CompleteContainer in the lib_datafiles(df)
        module then takes all the data and information to normalise data and
        perform the curve fitting. The returned dataframe (dfr_AssayData)
        contains all the data (raw data, analysed data,
        experimental meta data) and can be saved to file.
        """
        time_start = perf_counter()
        self.int_Samples = 0
        self.SaveAssayDetails(bol_FromTabChange=False)
        dlg_Progress.lbx_Log.InsertItems(["Assay details saved"], dlg_Progress.lbx_Log.Count)

        # Perform sequence of checks before beginning processing
        if self.bol_TransferLoaded == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoTransferLoaded()
            return None
        if self.bol_LayoutDefined == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoLayoutDefined()
            return None
        if self.bol_DataFilesAssigned == False:
            dlg_Progress.Destroy()
            self.parent.Thaw()
            msg.NoDataFileAssigned()
            return None
            
        # Build dataframe that holds everything
        dlg_Progress.lbx_Log.InsertItems(["Start creating complete container dataframe"],
                                         dlg_Progress.lbx_Log.Count)
        self.dfr_AssayData = df.get_CompleteContainer_nanoDSF(self.str_DataPath,
                                                              self.dfr_Details.loc["AssayCategory","Value"],
                                                              self.bol_PlateID,
            self.dfr_Capillaries,self.dfr_Layout,dlg_Progress)

        # Catch any errors in processing -> df.get_CompleteContainer() returns None on any errors:
        if self.dfr_AssayData is None:
            dlg_Progress.lbx_Log.InsertItems(["==============================================================="],
                                             dlg_Progress.lbx_Log.Count)
            dlg_Progress.lbx_Log.InsertItems(["DATA PROCESSING CANCELLED"], dlg_Progress.lbx_Log.Count)
            dlg_Progress.btn_X.Enable(True)
            dlg_Progress.btn_Close.Enable(True)
            self.parent.Thaw()
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
            dlg_Progress.lbx_Log.InsertItems(["Populating 'Review plates' tab"],
                                             dlg_Progress.lbx_Log.Count)
            self.tab_Review.Populate(noreturn = True)
            if hasattr(self, "lbc_Plates") == True:
                self.lbc_Plates.Select(0)
            self.bol_ReviewsDrawn = True
        if hasattr(self, "tab_Results") == True:
            dlg_Progress.lbx_Log.InsertItems(["Populating 'Results' tab"],
                                             dlg_Progress.lbx_Log.Count)
            self.PopulateResultsTab()
            self.bol_ResultsDrawn = True
        self.tabs_Analysis.EnableAll(True)
        self.tabs_Analysis.EnablePlateMap(self.bol_PlateID)

        # Final entries in progress dialog:
        dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems(["==============================================================="],
                                         dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems(["Data processing completed"], dlg_Progress.lbx_Log.Count)
        dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
        str_Duration = str(round(perf_counter()-time_start,0))
        dlg_Progress.lbx_Log.InsertItems(["Time elapsed: " + str_Duration + "s"], dlg_Progress.lbx_Log.Count)

        # Pop up notification if neither main window nor progress dialog are active window:
        if self.parent.IsActive() == False and dlg_Progress.IsActive() == False:
            try:
                # This should only work on Windows
                self.parent.icn_Taskbar.ShowBalloon(title="BBQ",text="Analysis completed!",
                                                    msec=1000)
            except:
                msg_Popup = wx.adv.NotificationMessage(title="BBQ", message="Analysis completed!")
                try: msg_Popup.SetIcon(self.parent.BBQIcon)
                except: None
                msg_Popup.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
    
        # Finish up
        self.bol_DataAnalysed = True
        dlg_Progress.btn_X.Enable(True)
        dlg_Progress.btn_Close.Enable(True)

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
        self.str_AssayType = "nanoDSF"
        self.str_AssayCategory = "thermal_shift"
        self.str_DatafileExtension = ".xlsx"
        str_Purification = "DSF"
        int_ProteinConc = 0
        str_Solvent = self.txt_Solvent.GetLineText(0)
        int_SolventPercent = self.txt_Percent.GetLineText(0)
        str_Buffer = ""
        str_ELN = self.txt_ELN.GetLineText(0)
        str_AssayVolume= str(20 * 1000) # convert to nL
        str_PlateID = self.txt_PlateID.GetValue()
        Date = self.DatePicker.GetValue()
        Date = str(Date.GetYear()) + "-" + str(Date.GetMonth()+1) + "-" + str(Date.GetDay()) # GetMonth is indexed from zero!!!!!
        Date = datetime.strptime(Date,"%Y-%m-%d").strftime("%Y-%m-%d")
        # Include checks so that user does not leave things empty
        dfr_Details_New = pd.DataFrame(data={"Value":[self.str_AssayType,
                                                      self.str_AssayCategory,
                                                      "NDSF",
                                                      str_Purification,
                                                      str_Solvent,
                                                      int_SolventPercent,
                                                      str_ELN,
                                                      str_AssayVolume,
                                                      self.str_DatafileExtension,
                                                      self.Device,
                                                      Date]},
                                       index=["AssayType",
                                              "AssayCategory",
                                              "Shorthand",
                                              "PurificationID",
                                              "Solvent",
                                              "SolventConcentration",
                                              "ELN",
                                              "AssayVolume",
                                              "DataFileExtension",
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

        for row in range(self.grd_Capillaries.GetNumberRows()):
            for col in range(1,self.grd_Capillaries.GetNumberCols()):
                self.dfr_Capillaries.iloc[row,col+1] = self.grd_Capillaries.GetCellValue(row,col) # Offset between grid and dataframe!

        # Update Layout dataframe so that references and Tm values can be calculated
        if len(self.dfr_Layout) == 0:
            self.dfr_Layout = pd.DataFrame(index=range(1),
                                           columns=["PlateID","ProteinNumerical",
                                                    "PurificationID","Concentration",
                                                    "WellType"])
            self.dfr_Layout.at[0,"PlateID"] = self.txt_PlateID.GetValue()
            self.dfr_Layout.at[0,"ProteinNumerical"] = []
            self.dfr_Layout.at[0,"PurificationID"] = []
            self.dfr_Layout.at[0,"Concentration"] = []
            self.dfr_Layout.at[0,"WellType"] = []
            for row in range(self.grd_Capillaries.GetNumberRows()):
                self.dfr_Layout.loc[0,"ProteinNumerical"].append("")
                self.dfr_Layout.loc[0,"PurificationID"].append(df.string_or_na(self.grd_Capillaries.GetCellValue(row, 1)))
                self.dfr_Layout.loc[0,"Concentration"].append(df.string_or_na(self.grd_Capillaries.GetCellValue(row, 2)))
                if self.grd_Capillaries.GetCellValue(row, 6) == "Reference":
                    self.dfr_Layout.loc[0,"WellType"].append("r")
                elif self.grd_Capillaries.GetCellValue(row, 6) == "Sample":
                    self.dfr_Layout.loc[0,"WellType"].append("s")
                else:
                    self.dfr_Layout.loc[0,"WellType"].append("")
        else:
            self.dfr_Layout.at[0,"PlateID"] = self.txt_PlateID.GetValue()
            for row in range(self.grd_Capillaries.GetNumberRows()):
                self.dfr_Layout.loc[0,"PurificationID"][row] = df.string_or_na(self.grd_Capillaries.GetCellValue(row, 1))
                self.dfr_Layout.loc[0,"Concentration"][row] = df.string_or_na(self.grd_Capillaries.GetCellValue(row, 2))
                if self.grd_Capillaries.GetCellValue(row, 6) == "Reference":
                    self.dfr_Layout.loc[0,"WellType"][row] = "r"
                elif self.grd_Capillaries.GetCellValue(row, 6) == "Sample":
                    self.dfr_Layout.loc[0,"WellType"][row] = "s"
                else:
                    self.dfr_Layout.loc[0,"WellType"][row] = ""

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
    
    def ReadPrometheusOutput(self, str_DataPath):
        """
        Gets output from Prometheus.

        Arguments:
            str_DataPath -> string. Path of data file.
        """
        self.str_DataPath = str_DataPath
        self.dfr_Capillaries = get_prometheus_capillaries(self.str_DataPath)
        if self.dfr_Capillaries is None:
            self.fpk_Data.txt_FilePicker.SetValue("")
            msg.FileNotData()
            return None
        int_Capillaries = self.dfr_Capillaries.shape[0]
        int_Rows = self.grd_Capillaries.GetNumberRows()
        if int_Capillaries > int_Rows:
            int_Appendage = int_Capillaries - int_Rows
            self.grd_Capillaries.AppendRows(int_Appendage)
        for idx_Capillary in range(int_Capillaries):
            if pd.isna(self.dfr_Capillaries.loc[idx_Capillary,"CapillaryName"]) == False:
                self.grd_Capillaries.SetCellValue(idx_Capillary,0,self.dfr_Capillaries.loc[idx_Capillary,"CapillaryName"])
            else:
                self.grd_Capillaries.SetCellValue(idx_Capillary,0,"no capillary")
            if idx_Capillary % 2 == 0:
                for col in range(self.grd_Capillaries.GetNumberCols()):
                    self.grd_Capillaries.SetCellBackgroundColour(idx_Capillary,col,cs.BgUltraLight)
        self.szr_Capillaries.Layout()
        self.szr_Capillaries.Fit(self.grd_Capillaries)
        self.szr_Assay.Layout()
        self.bol_DataFilesAssigned = True

    def EditCells(self, event):
        """
        Event handler. Toggles EnableEditing state of grid.
        """
        self.grd_Capillaries.ClearSelection()
        col = event.GetCol()
        if col > 0:
            self.grd_Capillaries.SetGridCursor(event.GetRow(),col)
            self.grd_Capillaries.EnableEditing(True)
        else:
            self.grd_Capillaries.EnableEditing(False)

    def OpenGridContextMenu(self, event):
        """
        Event handler. Launches context menu for grid.
        """
        self.PopupMenu(GridContextMenu(self, event))

    def SampleOrReference(self, event):
        """
        Event handler.
        """
        if event.GetCol() == 6:
            if self.grd_Capillaries.GetCellValue(event.GetRow(), event.GetCol()) != "Sample":
                if self.grd_Capillaries.GetCellValue(event.GetRow(), event.GetCol()) != "Reference":
                    self.grd_Capillaries.SetCellValue(event.GetRow(), event.GetCol(), "")

    def OnKeyPress(self, event):
        """
        Event handler. Handles key press events for grid to provide "copy", "paste",
        "cut", "delete", "select all" keyboard commands.
        """
        # based on first answer here:
        # https://stackoverflow.com/questions/28509629/work-with-ctrl-c-and-ctrl-v-to-copy-and-paste-into-a-wx-grid-in-wxpython
        # by user Sinan Çetinkaya

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
            self.GridPaste(self.grd_Capillaries.SingleSelection[0],
                           self.grd_Capillaries.SingleSelection[1])

        else:
            event.Skip()

    def GetGridSelection(self):
        """
        Returns all list of coordinates of all currently selected cells on grid.
        """
        # Selections are treated as blocks of selected cells
        lst_TopLeftBlock = self.grd_Capillaries.GetSelectionBlockTopLeft()
        lst_BotRightBlock = self.grd_Capillaries.GetSelectionBlockBottomRight()
        lst_Selection = []
        for i in range(len(lst_TopLeftBlock)):
            # Nuber of columns (add 1 because if just one cell/column is selected,
            # subtracting the coordinates will be 0!)
            int_Columns = lst_BotRightBlock[i][1] - lst_TopLeftBlock[i][1] + 1 
            # Nuber of rows (add 1 because if just one cell/row is selected,
            # subtracting the coordinates will be 0!)
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
        Writes contents of currently selected cells to clipboard.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0],
                              self.grd_Capillaries.SingleSelection[1]]]
        dfr_Copy = pd.DataFrame()
        for i in range(len(lst_Selection)):
            dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_Capillaries.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
        dfr_Copy.to_clipboard(header=None, index=False)

    def GridCut(self):
        """
        Writes contents of currently selected cells to clipboard and then
        clears cells on grid.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0],
                              self.grd_Capillaries.SingleSelection[1]]]
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grd_Capillaries.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
                self.grd_Capillaries.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")
            dfr_Copy.to_clipboard(header=None, index=False)
    
    def GridClear(self):
        """
        Clears contents of currently selected cells on grid.
        """
        lst_Selection = self.GetGridSelection()
        if len(lst_Selection) == 0:
            lst_Selection = [[self.grd_Capillaries.SingleSelection[0],
                              self.grd_Capillaries.SingleSelection[1]]]
            for i in range(len(lst_Selection)):
                if lst_Selection[i][1] > 0:
                    self.grd_Capillaries.SetCellValue(lst_Selection[i][0],lst_Selection[i][1],"")

    def GridPaste(self, row, col):
        """
        Pastes contents of clipboard onto grid, starting from selected
        cell.
        """
        dfr_Paste = pd.read_clipboard(sep="\\t", header=None)
        int_Rows = len(dfr_Paste)
        int_Columns = len(dfr_Paste.columns)
        for i in range(int_Rows):
            for j in range(int_Columns):
                if j <= 5:
                    self.grd_Capillaries.SetCellValue(i+row,j+col,str(dfr_Paste.iloc[i,j]))

    def SingleSelection(self, event):
        """
        Event handler.
        Sets custom "SingleSelection" property of grid to
        capture clicked on cell to ensure it is part of selection.
        """
        self.grd_Capillaries.SingleSelection = (event.GetRow(), event.GetCol())

    def UsePlateID(self, event):
        """
        Event handler. Determines whether to use plate ID for this assay
        based on check box value.
        """
        self.bol_PlateID = self.chk_PlateID.GetValue()
        self.txt_PlateID.Enable(self.bol_PlateID)
        if self.bol_DataAnalysed == True:
            self.tabs_Analysis.EnablePlateMap(self.bol_PlateID)

    ####  #####  #### #    # #     #####  ####
    #   # #     #     #    # #       #   #
    ####  ###    ###  #    # #       #    ###
    #   # #         # #    # #       #       #
    #   # ##### ####   ####  #####   #   ####

    def PopulateResultsTab(self):
        """
        Populates Results tab with results of analysis.
        """
        self.lbc_Samples.DeleteAllItems()
        # Iterate through plates
        idx_List = -1
        for idx_Plate in range(len(self.dfr_AssayData)):
            for j in range(len(self.dfr_AssayData.iloc[idx_Plate,5].index)):
                idx_List += 1
                self.lbc_Samples.InsertItem(idx_List,df.string_or_na(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"CapIndex"]))
                self.lbc_Samples.SetItem(idx_List,1,df.string_or_na(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"CapillaryName"]))
                self.lbc_Samples.SetItem(idx_List,2,df.string_or_na(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"SampleID"]))
                self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[j,"RatioInflections"][0],1)))

        # Individual plot
        self.pnl_Plot.Input = self.dfr_AssayData.iloc[0,5].iloc[0]
        self.pnl_Plot.InflectionPoints = []
        self.pnl_Plot.Draw()
        self.chk_IndiPlotRatio.SetValue(True)

        # Multiplot
        self.plt_MultiPlot.Temp[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Temp"]
        self.plt_MultiPlot.IDs[0] = self.dfr_AssayData.iloc[0,5].loc[0,"CapillaryName"]
        self.plt_MultiPlot.CapIndices[0] = self.dfr_AssayData.iloc[0,5].loc[0,"CapIndex"]
        self.plt_MultiPlot.Ratio[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Ratio"]
        self.plt_MultiPlot.RatioDeriv[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RatioDeriv"]
        self.plt_MultiPlot.RatioInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RatioInflections"]
        self.plt_MultiPlot.ThreeThirty[0] = self.dfr_AssayData.iloc[0,5].loc[0,"330nm"]
        self.plt_MultiPlot.ThreeThirtyDeriv[0] = self.dfr_AssayData.iloc[0,5].loc[0,"330nmDeriv"]
        self.plt_MultiPlot.ThreeThirtyInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"330nmInflections"]
        self.plt_MultiPlot.ThreeFifty[0] = self.dfr_AssayData.iloc[0,5].loc[0,"350nm"]
        self.plt_MultiPlot.ThreeFiftyDeriv[0] = self.dfr_AssayData.iloc[0,5].loc[0,"350nmDeriv"]
        self.plt_MultiPlot.ThreeFiftyInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"350nmInflections"]
        self.plt_MultiPlot.Scattering[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Scattering"]
        self.plt_MultiPlot.ScatteringDeriv[0] = self.dfr_AssayData.iloc[0,5].loc[0,"ScatteringDeriv"]
        self.plt_MultiPlot.ScatteringInflections[0] = self.dfr_AssayData.iloc[0,5].loc[0,"ScatteringInflections"]
        self.plt_MultiPlot.Draw()
        self.rad_MultiPlotRatio.SetValue(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].SetLabel(self.plt_MultiPlot.IDs[0])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[0]].Enable(True)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].SetSelection(0)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].Enable(True)
        
        self.lbc_Samples.Select(0)
        self.bol_ResultsDrawn = True

    def ToggleFit(self,event):
        """
        Event handler. Decides whether or not to fit a dataset.
        """
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
                self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioInflections"][0],1)))

                self.lbc_Samples.SetItem(idx_List,4,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormDTm"],2)))
            else:
                self.lbc_Samples.SetItem(idx_List,3,"ND")
                #self.lbc_Samples.SetItem(idx_List,4,"")
                #self.lbc_Samples.SetItem(idx_List,5,"")
                self.lbc_Samples.SetItem(idx_List,4,"")
        else:
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioInflections"][0],1)))

                self.lbc_Samples.SetItem(idx_List,4,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormDTm"],2)))
            else:
                self.lbc_Samples.SetItem(idx_List,3,"ND")

                self.lbc_Samples.SetItem(idx_List,4,"")
        self.pnl_Plot.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
        self.pnl_Plot.InflectionPoints = []
        self.pnl_Plot.Draw()

    def IndiPlotRatio(self, event):
        """
        Event handler. Determine whether to show ratio of fluorescence
        of both wavelengths or flourescence at individual wavelength(s)
        on indivudual plot.
        """
        if self.chk_IndiPlotRatio.Value == True:
            self.pnl_Plot.Ratio = 1
            self.chk_IndiPlot330.SetValue(False)
            self.pnl_Plot.ThreeThirty = 0
            self.chk_IndiPlot350.SetValue(False)
            self.pnl_Plot.ThreeFifty = 0
        else:
            self.pnl_Plot.Ratio = 0
        self.pnl_Plot.Draw()

    def IndiPlot330nm(self, event):
        """
        Event handler. Toggle between showing and not showing fluorescence
        at 330 nm on indivudual plot.
        """
        if self.chk_IndiPlot330.Value == True:
            self.chk_IndiPlotRatio.SetValue(False)
            self.pnl_Plot.Ratio = 0
            self.pnl_Plot.ThreeThirty = 1
        else:
            self.pnl_Plot.ThreeThirty = 0
        self.pnl_Plot.Draw()

    def IndiPlot350nm(self, event):
        """
        Event handler. Toggle between showing and not showing fluorescence
        at 350 nm on indivudual plot.
        """
        if self.chk_IndiPlot350.Value == True:
            self.chk_IndiPlotRatio.SetValue(False)
            self.pnl_Plot.Ratio = 0
            self.pnl_Plot.ThreeFifty = 1
        else:
            self.pnl_Plot.ThreeFifty = 0
        self.pnl_Plot.Draw()

    def IndiPlotScattering(self, event):
        """
        Event handler. Toggle between showing and not showing light
        scattering on indivudual plot.
        """
        if self.chk_IndiPlotScattering.Value == True:
            self.pnl_Plot.Scattering = 1
        else:
            self.pnl_Plot.Scattering = 0
        self.pnl_Plot.Draw()

    def ToggleInflectionsIndividual(self, event):
        self.pnl_Plot.ShowInflections = self.chk_InflectionsIndividual.Value
        self.pnl_Plot.Draw()

    def ShowCurve(self,event):
        """
        Event handler. Show/Update the displayed curve based
        on selection on ListCtr.
        """
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.Freeze()
        if self.sbk_ResultPlots.GetSelection() == 0:
            self.pnl_Plot.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
            self.pnl_Plot.InflectionPoints = []
            self.pnl_Plot.Draw()
            self.lbl_Tm.SetLabel("Tm: "+ str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioInflections"][0],2)))

        # Add Preview to multiplot
        self.plt_MultiPlot.PreviewID = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapillaryName"]
        self.plt_MultiPlot.PreviewCapIndex = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapIndex"]
        self.plt_MultiPlot.PreviewTemp = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"]
        self.plt_MultiPlot.PreviewRatio = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Ratio"]
        self.plt_MultiPlot.PreviewRatioDeriv = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioDeriv"]
        self.plt_MultiPlot.PreviewRatioInflections = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioInflections"]
        self.plt_MultiPlot.PreviewThreeThirty = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nm"]
        self.plt_MultiPlot.PreviewThreeThirtyDeriv = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nmDeriv"]
        self.plt_MultiPlot.PreviewThreeThirtyInflections = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nmInflections"]
        self.plt_MultiPlot.PreviewThreeFifty = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nm"]
        self.plt_MultiPlot.PreviewThreeFiftyDeriv = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nmDeriv"]
        self.plt_MultiPlot.PreviewThreeFiftyInflections = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nmInflections"]
        self.plt_MultiPlot.PreviewScattering = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Scattering"]
        self.plt_MultiPlot.PreviewScatteringDeriv = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"ScatteringDeriv"]
        self.plt_MultiPlot.PreviewScatteringInflections = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"ScatteringInflections"]
        self.plt_MultiPlot.Draw()

        self.Thaw()

    def ExportResultsTable(self,event):
        """
        Event handler. Writes results table to pandas dataframe and
        writes it to clipboard.
        """
        dfr_ResultsTable = pd.DataFrame(columns=["Plate","Well","SampleID",
                                                 "SourceConcentration[mM]",
                                                 "TopConcentration[uM]","Tm[C]"],
                                        index=range(self.lbc_Samples.GetItemCount()))
        count = 0
        for i in range(len(self.dfr_AssayData)):
            for j in range(len(self.dfr_AssayData.loc[i,"ProcessedDataFrame"])):
                dfr_ResultsTable.loc[count,"Plate"] = i+1
                dfr_ResultsTable.loc[count,"Well"] = self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"Well"]
                dfr_ResultsTable.loc[count,"SampleID"] = self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"SampleID"]
                dfr_ResultsTable.loc[count,"TopConcentration[uM]"] = float(self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"Concentrations"][0]) * 1000000
                dfr_ResultsTable.loc[count,"Tm[C]"] = float(self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"FitPars"][5])
                count += 1
        # Export as csv:
        fdlg = wx.FileDialog(self, message = "Save summary table as as",
                             wildcard="Comma separated files (*.csv)|*.csv",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .png. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            dfr_ResultsTable.to_csv(str_SavePath)

    # 4.6 Get the indices of the selected plot from the self.dfr_AssayData
    def GetPlotIndices(self):
        """
        Gets the indices of the selected ploton lbc_Samples 
        iside of self.dfr_AssayData

        Returns:
            idx_SampleList -> integer. Index of selected sample
            idx_SampleDataFrame -> integer. Index in plate's subdataframe
            idx_Plate -> integer. Index of the plate's subdataframe
                         within self.dfr_AssayData
        """
        # Get list index of selected sample
        idx_SampleList = self.lbc_Samples.GetFirstSelected()
        # Get plate index
        idx_Plate = 0 # int(self.lbc_Samples.GetItemText(idx_SampleList,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.dfr_AssayData.iloc[idx_Plate,5]
        idx_SampleDataFrame = dfr_Sample[dfr_Sample["CapIndex"] == int(self.lbc_Samples.GetItemText(idx_SampleList,0))].index.tolist()
        idx_SampleDataFrame = idx_SampleDataFrame[0] # above function returns list, but there will always be only one result
        return idx_SampleList, idx_SampleDataFrame, idx_Plate

    def MouseOver(self, event):
        """
        Event handler for mouse over on list ctrl lbc_Samples.
        Shows tooltip with plot.
        """
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
            lst_Deriv = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"RawFit"]
            self.tltp = tt.plt_ToolTip(self, lst_X, lst_Y, lst_Deriv)
            self.tltp.Show()
            self.SetFocus()
        else:
            try: self.tltp.Destroy()
            except: None
    
    def ClosePlotToolTip(self, event):
        """
        Since the plot tooltip is not a real tooltip, just a dialog box,
        we also needa workaround to close it when we do not need it anymore.
        This function will try to destroy the tooltip, if there is one.
        Otherwise, the tooltip will just stay like a dialog.
        """
        try: self.tltp.Destroy()
        except: None

    def AllPlotsToPNG(self, event):
        """
        Event handler. Saves dose response curve plots for all
        samples as separate PNG files.
        """
        with wx.DirDialog(self,
                          message="Select a directory to save plots") as dlg_Directory:

            if dlg_Directory.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveDirPath = dlg_Directory.GetPath()
        # Pick directory here. If no directory picked, self.Thaw() and end function.
        self.dlg_PlotsProgress = GenericProgress(self, "Saving Plots")
        self.dlg_PlotsProgress.Show()
        thd_SavingPlots = threading.Thread(target=self.AllPlotsToPNG_thread,
                                           args=(str_SaveDirPath,),
                                           daemon=True)
        thd_SavingPlots.start()

    def AllPlotsToPNG_thread(self, str_SaveDirPath):
        """
        Thread to write all plots to PNG.
        """
        self.Freeze()
        int_Samples = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            int_Samples += len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])
        count = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            for idx_Sample in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                count += 1
                #DO STUFF TO MAKE PLOT
                tempplot = DSFPlotPanel(self.pnl_Results, (600,450), None)
                tempplot.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
                tempplot.Draw()
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] != "":
                    str_FileName = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
                else:
                    str_FileName = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapillaryName"]
                tempplot.figure.savefig(str_SaveDirPath + chr(92) + str_FileName + ".png",
                    dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None, transparent=False, bbox_inches=None, pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_PlotsProgress.gauge.SetValue((count/int_Samples)*200)
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()

    def ColourSelect(self, event):
        """
        Event handler. Changes colour of graph on multiplot.
        """
        idx_Combo = event.GetEventObject().GetSelection()
        self.plt_MultiPlot.Colours[event.GetEventObject().Index] = self.plt_MultiPlot.ColourChoices[idx_Combo]
        self.plt_MultiPlot.Draw()

    def AddGraph(self, event):
        """
        Event handler. Adds selected graph to multiplot.
        """
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        idx_Graph = event.GetEventObject().Index
        self.plt_MultiPlot.Temp[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Temp"]
        self.plt_MultiPlot.IDs[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapillaryName"]
        self.plt_MultiPlot.CapIndices[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapIndex"]
        self.plt_MultiPlot.Ratio[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Ratio"]
        self.plt_MultiPlot.RatioDeriv[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioDeriv"]
        self.plt_MultiPlot.RatioInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RatioInflections"]
        self.plt_MultiPlot.ThreeThirty[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nm"]
        self.plt_MultiPlot.ThreeThirtyDeriv[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nmDeriv"]
        self.plt_MultiPlot.ThreeThirtyInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"330nmInflections"]
        self.plt_MultiPlot.ThreeFifty[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nm"]
        self.plt_MultiPlot.ThreeFiftyDeriv[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nmDeriv"]
        self.plt_MultiPlot.ThreeFiftyInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"350nmInflections"]
        self.plt_MultiPlot.Scattering[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Scattering"]
        self.plt_MultiPlot.ScatteringDeriv[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"ScatteringDeriv"]
        self.plt_MultiPlot.ScatteringInflections[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"ScatteringInflections"]
        self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"CapillaryName"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(True)
        self.plt_MultiPlot.Draw()

    def RemoveGraph(self, event):
        """
        Event handler. Removes a graph from multiplot.
        """
        # First, test that at least one graph will remain on the plot:
        checksum = 0
        for i in range(len(self.plt_MultiPlot.IDs)):
            if self.plt_MultiPlot.IDs[i] != "":
                checksum += 1
        if checksum > 1:
            idx_Graph = event.GetEventObject().Index
            self.plt_MultiPlot.IDs[idx_Graph] = ""
            self.plt_MultiPlot.Temp[idx_Graph] = []
            self.plt_MultiPlot.Ratio[idx_Graph] = []
            self.plt_MultiPlot.RatioDeriv[idx_Graph] = []
            self.plt_MultiPlot.ThreeThirty[idx_Graph] = []
            self.plt_MultiPlot.ThreeThirtyDeriv[idx_Graph] = []
            self.plt_MultiPlot.ThreeFifty[idx_Graph] = []
            self.plt_MultiPlot.ThreeFiftyDeriv[idx_Graph] = []
            self.plt_MultiPlot.Scattering[idx_Graph] = []
            self.plt_MultiPlot.ScatteringDeriv[idx_Graph] = []
            self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(False)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel("no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(False)
            self.plt_MultiPlot.Draw()
        else:
            wx.MessageBox("Cannot remove this graph.\nAt least one graph must be displayed.",
                "No can do",
                wx.OK|wx.ICON_INFORMATION)

    def MultiPlotRatio(self, event):
        """
        Event handler. Shows fluorescence ratio on multiplot.
        """
        self.rad_MultiPlotRatio.SetValue(True)
        self.rad_MultiPlot330nm.SetValue(False)
        self.rad_MultiPlot350nm.SetValue(False)
        self.rad_MultiPlotScattering.SetValue(False)
        self.plt_MultiPlot.Display = 0
        self.plt_MultiPlot.Draw()

    def MultiPlot330nm(self, event):
        """
        Event handler. Shows fluorescence at 330nm on multiplot.
        """
        self.rad_MultiPlotRatio.SetValue(False)
        self.rad_MultiPlot330nm.SetValue(True)
        self.rad_MultiPlot350nm.SetValue(False)
        self.rad_MultiPlotScattering.SetValue(False)
        self.plt_MultiPlot.Display = 1
        self.plt_MultiPlot.Draw()

    def MultiPlot350nm(self, event):
        """
        Event handler. Shows fluorescence at 350nm on multiplot.
        """
        self.rad_MultiPlotRatio.SetValue(False)
        self.rad_MultiPlot330nm.SetValue(False)
        self.rad_MultiPlot350nm.SetValue(True)
        self.rad_MultiPlotScattering.SetValue(False)
        self.plt_MultiPlot.Display = 2
        self.plt_MultiPlot.Draw()

    def MultiPlotScattering(self, event):
        """
        Event handler. Shows light scattering on multiplot.
        """
        self.rad_MultiPlotRatio.SetValue(False)
        self.rad_MultiPlot330nm.SetValue(False)
        self.rad_MultiPlot350nm.SetValue(False)
        self.rad_MultiPlotScattering.SetValue(True)
        self.plt_MultiPlot.Display = 3
        self.plt_MultiPlot.Draw()

    def ToggleInflectionsMulti(self, event):
        """
        Event handler. Toggles display of inflection points on
        multiplot.
        """
        self.plt_MultiPlot.Inflections = self.chk_InflectionsMulti.Value
        self.plt_MultiPlot.Draw()

    def TogglePreviewPlot(self, event):
        """
        Event handler. Toggles preview of selected sample on
        multiplot.
        """
        self.plt_MultiPlot.Preview = self.chk_PreviewPlot.GetValue()
        self.plt_MultiPlot.Draw()
