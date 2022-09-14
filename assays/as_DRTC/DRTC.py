# Import my own libraries
import lib_platefunctions as pf
import lib_datafunctions as df
import lib_fittingfunctions as ff
import lib_customplots as cp
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_tabs as tab
import lib_tooltip as tt
from lib_progressdialog import GenericProgress
from lib_custombuttons import IconTabButton, CustomBitmapButton

# Import libraries for GUI
import wx
import wx.xrc
import wx.grid
import wx.adv
from wx.core import SetCursor

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure
import matplotlib.ticker as mtick

# Import other libraries
import os
import pandas as pd
import numpy as np
import threading
from datetime import datetime


####################################################################################
##                                                                                ##
##     #####  #####    ####   ##  ##  #####     #####   ##       ####   ######    ##
##    ##      ##  ##  ##  ##  ##  ##  ##  ##    ##  ##  ##      ##  ##    ##      ##
##    ##  ##  #####   ##  ##  ##  ##  #####     #####   ##      ##  ##    ##      ##
##    ##  ##  ##  ##  ##  ##  ##  ##  ##        ##      ##      ##  ##    ##      ##
##     #####  ##  ##   ####    ####   ##        ##      ######   ####     ##      ##
##                                                                                ##
####################################################################################

class ProgressCurves(wx.Panel):

    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        titleheight = 30
        plotheight = 350
        plotwidth = 530
        leftaxiswidth = 60
        self.Top = 1-titleheight/PanelSize[1]
        self.Bottom = 1-(titleheight/PanelSize[1])-(plotheight/PanelSize[1])
        self.Right = 1-(PanelSize[0]-plotwidth-leftaxiswidth)/PanelSize[0]
        self.Left = 1-((PanelSize[0]-plotwidth-leftaxiswidth)/PanelSize[0])-(plotwidth/PanelSize[0])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.ShowMarker = True
        self.Picked = 0
        self.PlateIndex = None
        self.SampleIndex = None
        self.Confidence = False
        self.Input = None
        self.figure.set_facecolor(cs.BgUltraLightHex)
        
        # Parameters/properties for zooming in on plot:
        self.Zooming = False
        self.Zoomed = False
        self.OriginalXLimits = None
        self.OriginalYLimits = None
        self.ZoomStartX = 0
        self.ZoomStartY = 0
        self.ZoomEndX = 0
        self.ZoomEndY = 0
        self.ZoomFrame = None

        self.Colours = cs.TM_Hex_List + cs.TM_Hex_List
        self.Markers = ["o","o","o","o","o","o","o","o","o","o","v","v","v","v","v","v","v","v","v","v"]
        self.Exclude = [False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False]
        self.Linestyles = ["solid","solid","solid","solid","solid","solid","solid","solid","solid","solid",
            "dotted","dotted","dotted","dotted","dotted","dotted","dotted","dotted","dotted","dotted"]

    def Draw(self):
        self.SampleID = self.Input["SampleID"]
        # Convert dose to micromoles
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=self.Left, right=self.Right, top=self.Top , bottom=self.Bottom)
        for conc in range(len(self.Input["Concentrations"])):
            if self.Exclude[conc] == False:
                self.ax.plot(self.Input["Time"], self.Input["RawMean"].iloc[conc].apply(self.thousands), label=self.Input["Concentrations"][conc]*1000000,
                    color=self.Colours[conc], linestyle=self.Linestyles[conc])
            else:
                self.ax.plot(self.Input["Time"], self.Input["RawMean"].iloc[conc].apply(self.thousands), label=self.Input["Concentrations"][conc]*1000000,
                    color=cs.BgMediumHex, linestyle=self.Linestyles[conc])
        self.ax.xaxis.set_pickradius(50)
        self.ax.yaxis.set_pickradius(50)
        self.ax.set_title(self.SampleID)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Signal in A.U. (x1000)")
        if self.ax.get_ylim()[1] < 10:
            self.ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f")) # Formats y axis tick marks this way: 1.0
        else:
            self.ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f")) # Formats y axis tick marks this way: 1 || Number.decimalplaces floatingpoint
        #self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
        if self.ShowMarker == True and self.Picked != None:
            self.ax.axvline(self.Picked,0,1,linestyle="--",linewidth=1.0,color="grey")
        # Set the axe limits if you've zoomed in
        if self.Zoomed == True:
            if self.ZoomStartX > self.ZoomEndX:
                leftlimit = self.ZoomEndX
                rightlimit = self.ZoomStartX
            else:
                leftlimit = self.ZoomStartX
                rightlimit = self.ZoomEndX
            if self.ZoomStartY > self.ZoomEndY:
                bottomlimit = self.ZoomEndY
                toplimit = self.ZoomStartY
            else:
                bottomlimit = self.ZoomStartY
                toplimit = self.ZoomEndY
            self.ax.set_xlim(left=leftlimit, right=rightlimit)
            self.ax.set_ylim(bottom=bottomlimit, top=toplimit)
        handles, labels = self.ax.get_legend_handles_labels()
        for conc in range(len(labels)):
            if float(labels[conc]) < 0:
                labels[conc] = str(round(float(labels[conc]),3))
            elif float(labels[conc]) < 10:
                labels[conc] = str(round(float(labels[conc]),2))
            elif float(labels[conc]) < 100:
                labels[conc] = str(round(float(labels[conc]),0))
        self.legend = self.ax.legend(reversed(handles), reversed(labels), title="Conc.("+chr(181)+"M)", bbox_to_anchor=(1.19,1.02), loc="upper right", ncol=1, framealpha=1.0, fancybox=False, edgecolor="black")
        # Set picker for legend lines
        for legline in self.legend.get_lines():
            legline.set_picker(5)  # 5 pts tolerance
        self.canvas.mpl_connect("button_press_event", self.OnClick)
        self.canvas.mpl_connect("button_release_event", self.OnRelease)
        self.canvas.mpl_connect("figure_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("axes_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("motion_notify_event", self.DragZoomFrame)
        self.canvas.mpl_connect("pick_event", self.OnPick)
        self.Bind(wx.EVT_KILL_FOCUS, self.LeaveFigure)
        self.canvas.draw()

    def OnClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))
        elif event.button is MouseButton.LEFT: # and event.inaxes:
            if self.Zooming == True:
                cp.StartZooming(self, event)
            else:
                picked = round(event.xdata,2)
                if picked >= self.Input["Time"][0] and picked <= self.Input["Time"][-1]:
                    self.Picked = df.nearest(self.Input["Time"],picked)
                    self.Draw()
                    self.tabname.plt_IndividualCycle.Cycle = self.Picked
                    self.tabname.plt_IndividualCycle.Draw()
                    self.tabname.UpdateIndividualCycleDetails(self.PlateIndex, self.SampleIndex, self.Picked)
                    self.tabname.plt_IndividualIC50AgainstTime.Picked = self.Picked
                    self.tabname.plt_IndividualIC50AgainstTime.Draw()

    def OnRelease(self, event):
        if self.Zooming == True:
            cp.EndZoomingButtonLift(self, event)

    def OnPick(self, event):
        self.tabname.parent.Freeze()
        #print(event.artist.get_label())
        flt_Conc = float(event.artist.get_label())/1000000
        for idx_Conc in range(len(self.Input["Concentrations"])):
            if self.Input["Concentrations"][idx_Conc] == flt_Conc:
                self.Exclude[idx_Conc] = not self.Exclude[idx_Conc]
                self.dlg_ReFittingProgress = GenericProgress(self, "Re-fitting")
                self.dlg_ReFittingProgress.Show()
                count = 0
                for flt_Cycle in self.Input["Time"]:
                    if np.isnan(self.Input["NormMean"].loc[flt_Conc,flt_Cycle]) == False:
                        # First check if there are enough datapoints left to perform a fit
                        # Selected datapoint IS NOT excluded -> copy it into excluded series and set value in data series to nan
                        self.Input["RawExcluded"].at[flt_Conc,flt_Cycle] = self.Input["RawMean"].loc[flt_Conc,flt_Cycle]
                        self.Input["RawMean"].at[flt_Conc,flt_Cycle] = np.nan
                        self.Input["NormExcluded"].at[flt_Conc,flt_Cycle] = self.Input["NormMean"].loc[flt_Conc,flt_Cycle]
                        self.Input["NormMean"].at[flt_Conc,flt_Cycle] = np.nan
                    else:
                        # Selected datapoint IS excluded -> copy it back into data series and set value in excluded series to nan
                        self.Input["RawMean"].at[flt_Conc,flt_Cycle] = self.Input["RawExcluded"].loc[flt_Conc,flt_Cycle]
                        self.Input["RawExcluded"].at[flt_Conc,flt_Cycle] = np.nan
                        self.Input["NormMean"].at[flt_Conc,flt_Cycle] = self.Input["NormExcluded"].loc[flt_Conc,flt_Cycle]
                        self.Input["NormExcluded"].at[flt_Conc,flt_Cycle] = np.nan
                    
                    self.Input["DoFit"].at["Value",flt_Cycle] = df.get_DoFit(self.Input["NormMean"].loc[:,flt_Cycle].tolist(),self.Input["NormSEM"].loc[:,flt_Cycle].tolist())
            
                    if self.Input["DoFit"].at["Value",flt_Cycle] == True:
                    # 3. Re-fit
                        lst_FitResults = ff.sigmoidal_free(self.Input["Concentrations"], self.Input["NormMean"].loc[:,flt_Cycle].tolist())  # only function for constrained needs SEM
                        self.Input.at["NormFitFree"].loc[:,flt_Cycle] = lst_FitResults[0]
                        self.Input.at["NormFitFreePars"].loc[:,flt_Cycle] = lst_FitResults[1]
                        self.Input.at["NormFitFreeCI"].loc[:,flt_Cycle] = lst_FitResults[2]
                        self.Input.at["NormFitFreeErrors"].loc[:,flt_Cycle] = lst_FitResults[3]
                        self.Input.loc["NormFitFreeR2"].at["Value",flt_Cycle] = lst_FitResults[4]
                        self.Input.loc["DoNormFitFree"].at["Value",flt_Cycle] = lst_FitResults[5]
                        lst_FitResults = ff.sigmoidal_constrained(self.Input["Concentrations"], self.Input["NormMean"].loc[:,flt_Cycle].tolist(), self.Input["NormSEM"].loc[:,flt_Cycle].tolist())  # only function for constrained needs SEM
                        self.Input.at["NormFitConst"].loc[:,flt_Cycle] = lst_FitResults[0]
                        self.Input.at["NormFitConstPars"].loc[:,flt_Cycle] = lst_FitResults[1]
                        self.Input.at["NormFitConstCI"].loc[:,flt_Cycle] = lst_FitResults[2]
                        self.Input.at["NormFitConstErrors"].loc[:,flt_Cycle] = lst_FitResults[3]
                        self.Input.loc["NormFitConstR2"].at["Value",flt_Cycle] = lst_FitResults[4]
                        self.Input.loc["DoNormFitConst"].at["Value",flt_Cycle] = lst_FitResults[5]

                    else:
                        self.Input.at["RawFit"].loc[:,flt_Cycle] = df.set_to_nan(len(self.Input["RawFit"].loc[:,flt_Cycle]))
                        self.Input.at["RawFitPars"].loc[:,flt_Cycle] = df.set_to_nan(4)
                        self.Input.at["RawFitR2"].loc[:,flt_Cycle] = np.nan

                        self.Input.at["NormFitFree"].loc[:,flt_Cycle] = df.set_to_nan(len(self.Input["NormFitFree"].loc[:,flt_Cycle]))
                        self.Input.at["NormFitFreePars"].loc[:,flt_Cycle] = df.set_to_nan(4)
                        self.Input.at["NormFitFreeR2"].loc[:,flt_Cycle] = np.nan

                        self.Input.at["NormFitConst"].loc[:,flt_Cycle] = df.set_to_nan(len(self.Input["NormFitConst"].loc[:,flt_Cycle]))
                        self.Input.at["NormFitConstPars"].loc[:,flt_Cycle] = df.set_to_nan(4)
                        self.Input.at["NormFitConstR2"].loc[:,flt_Cycle] = np.nan

                        self.Input.at["NormFitFreeCI"].loc[:,flt_Cycle], self.Input.at["NormFitConstCI"].loc[:,flt_Cycle], self.Input["RawFitCI"].loc[:,flt_Cycle] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
                        self.Input.at["NormFitFreeErrors"].loc[:,flt_Cycle], self.Input.at["NormFitConstErrors"].loc[:,flt_Cycle], self.Input["RawFitErrors"].loc[:,flt_Cycle] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
                    count += 1
                    self.dlg_ReFittingProgress.gauge.SetValue((count/len(self.Input["Time"]))*200)

        self.tabname.dfr_AssayData.loc[self.PlateIndex,"ProcessedDataFrame"].at[self.SampleIndex] = self.Input
        self.tabname.plt_IndividualCycle.Input = self.tabname.dfr_AssayData.loc[self.PlateIndex,"ProcessedDataFrame"].loc[self.SampleIndex]
        self.tabname.plt_IndividualCycle.Draw()
        self.tabname.plt_IndividualIC50AgainstTime.Input = self.tabname.dfr_AssayData.iloc[self.PlateIndex,5].loc[self.SampleIndex]
        self.tabname.plt_IndividualCycle.Draw()
        self.Draw()
        self.tabname.parent.Thaw()
        self.dlg_ReFittingProgress.Destroy()

    def SetZoomingTrue(self, event):
        self.Zooming = True

    def StartZooming(self, event):
        cp.StartZooming(self, event)

    def EndZoomingButtonLift(self, event):
        cp.EndZoomingButtonLift(self, event)
    
    def ResetZoom(self, event):
        cp.ResetZoom(self, event)

    def LeaveFigure(self, event):
        cp.LeaveFigure(self, event)

    def DragZoomFrame(self, event):
        cp.DragZoomFrame(self, event)

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)
    
    def DataToClipboard(self, event):
        data = {}
        for conc in self.Input["RawMean"].index.values.tolist():
            data[conc] = self.Input["RawMean"].loc[conc,:]
        pd.DataFrame(data=data,index=self.Input["Time"]).to_clipboard(header=True, index=True)

    def thousands(self, x):
        return x / 1000

class ZoomFrame(wx.Dialog):
    def __init__(self, parent, position = None, size = wx.Size(1,1)):
        wx.Dialog.__init__ (self, parent, id = wx.ID_ANY, title = u"Tooltip", pos=wx.DefaultPosition, size = size, style = wx.STAY_ON_TOP)
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetBackgroundColour(cs.White)
        self.parent = parent
        if position == None:
            self.Position = self.parent.ZoomFrameOrigin
        else:
            self.Position = position
        self.Size = size
        self.SetTransparent(75)
        self.szr_Main = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Main = wx.StaticText(self, wx.ID_ANY, u"LABEL", wx.DefaultPosition, self.Size, 0)
        self.szr_Main.Add(self.lbl_Main,0,wx.ALL,0)
        self.SetSizer(self.szr_Main)
        self.Layout()
        self.szr_Main.Fit(self)

        self.SetPosition(self.Position)

    def __del__(self):
        pass

    def Redraw(self, position, size):
        self.Position = position
        self.Size = size
        self.SetSize(self.Size)
        self.SetPosition(self.Position)
        self.Layout()


############################################################################
##                                                                        ##
##     ####   ##  ##  ######     #####  ##  ##   #####  ##      ######    ##
##    ##  ##  ### ##  ##        ##      ##  ##  ##      ##      ##        ##
##    ##  ##  ######  ####      ##       ####   ##      ##      ####      ##
##    ##  ##  ## ###  ##        ##        ##    ##      ##      ##        ##
##     ####   ##  ##  ######     #####    ##     #####  ######  ######    ##
##                                                                        ##
############################################################################

class CurvePlotPanel(wx.Panel):

    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(175/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.Confidence = False
        self.Cycle = 0
        self.Input = None
        self.Dose = None
        self.Response = None
        self.ErrorBars = None
        self.SampleID = None
        self.PlateIndex = None
        self.SampleIndex = None
        self.Normalised = True
        self.LabelSize = 8
        self.figure.set_facecolor(cs.BgLightHex)
        
        self.Colours = cs.TM_Hex_List + cs.TM_Hex_List
        self.Markers = ["o","o","o","o","o","o","o","o","o","o","v","v","v","v","v","v","v","v","v","v"]

    def Draw(self):
        # Convert dose to micromoles
        self.Dose = self.Input["Concentrations"]
        self.DoseMicromolar = df.moles_to_micromoles(self.Dose)
        self.Response = self.Input["NormMean"].loc[:,self.Cycle].tolist()
        self.ErrorBars = self.Input["NormSEM"].loc[:,self.Cycle].tolist()
        self.Excluded = self.Input["NormExcluded"].loc[:,self.Cycle].tolist()
        if self.Input["Show"].loc["Value",self.Cycle] == 1:
            self.NormFit = self.Input["NormFitFree"].loc[:,self.Cycle]
        else:
            self.NormFit = self.Input["NormFitConst"].loc[:,self.Cycle]
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.18, right=0.99, top=self.Top , bottom=self.Bottom)
        # Actual Plot
        if self.Dose != None:
            # Matplotlib does not support multiple markers in one series! Make multiple series.
            for conc in range(len(self.DoseMicromolar)):
                if pd.isna(self.Response[conc]) == False:
                    if self.ErrorBars != None:
                        self.ax.errorbar(self.DoseMicromolar[conc], self.Response[conc], yerr=self.ErrorBars[conc], fmt="none", color=self.Colours[conc], elinewidth=0.3, capsize=2)
                    self.ax.scatter(self.DoseMicromolar[conc], self.Response[conc], marker=self.Markers[conc], color=self.Colours[conc], picker=5, s=20)
                if pd.isna(self.Excluded[conc]) == False:
                    if self.ErrorBars != None:
                        self.ax.errorbar(self.DoseMicromolar[conc], self.Excluded[conc], yerr=self.ErrorBars[conc], fmt="none", color=self.Colours[conc], elinewidth=0.3, capsize=2)
                    self.ax.scatter(self.DoseMicromolar[conc], self.Excluded[conc], marker=self.Markers[conc], color=cs.WhiteHex, picker=5, s=20, edgecolors=self.Colours[conc], linewidths=0.8)            
            if type(self.NormFit) != None:
                self.ax.plot(self.DoseMicromolar, self.NormFit, color=cs.BgUltraDarkHex)
        self.ax.set_title(self.Input["SampleID"] + " (" + str(self.Cycle) + "s)")
        self.ax.axes.title.set_size(10)
        self.ax.set_xlabel("Concentration (" + chr(181) +"M)")
        self.ax.set_xscale("log")
        self.ax.xaxis.label.set_size(self.LabelSize)
        self.ax.tick_params(axis="x", labelsize=self.LabelSize)
        if self.Normalised == True:
            if self.ax.get_ylim()[1] < 120:
                self.ax.set_ylim(top=120)
            if self.ax.get_ylim()[0] > -20:
                self.ax.set_ylim(bottom=-20)
            self.ax.set_ylabel("Per-cent inhibition")
            #self.ax.set_ylim([-20,120])
            self.ax.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
            self.ax.axhline(y=100, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=100
            self.ax.ticklabel_format(axis="y", style="plain")
        else:
            self.ax.set_ylabel("Signal in A.U. (x1000)")
            #self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
        #self.ax.legend()
        self.ax.yaxis.label.set_size(self.LabelSize)
        if self.ax.get_ylim()[1] < 10:
            self.ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f")) # Formats y axis tick marks this way: 1.00
        else:
            self.ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.1f")) # Formats y axis tick marks this way: 1.0 || Number.decimalplaces floatingpoint
        self.ax.tick_params(axis="y", labelsize=self.LabelSize)
        # Bind/connect events
        self.canvas.mpl_connect("pick_event", self.PickPoint)
        self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.Bind(wx.EVT_KILL_FOCUS, self.DestroyToolTip)
        # Draw the plot!
        self.canvas.draw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def CustomToolTip(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib backend plots in wxPython.
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destroy it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            # First things first: destroy tooltip if it exists
            try: self.tltp.Destroy()
            except: None
            # Get coordinates on plot
            hover_x, hover_y = event.xdata, event.ydata

            lst_YLimits = self.ax.get_ylim()
            within = (lst_YLimits[1] - lst_YLimits[0])/100 * 2
            if self.Normalised == True:
                str_Unit = " " + chr(37) # per-cent sign
            else:
                str_Unit = ""
            # find nearest concentration to mouse position:
            conc = df.nearest(self.DoseMicromolar,hover_x)
            conc_M = conc/1000000
            if pd.isna(conc) == True:
                return None
            # find nearest response and excluded to mouse position:
            resp = df.nearest(self.Response,hover_y)
            if df.any_nonnan(self.Excluded) == True:
                excl = df.nearest(self.Excluded,hover_y)
            else:
                excl = None
            str_Tooltip = None
            # For the x axis (log scale), we have to adjust relative
            if hover_x >= (conc*0.9) and hover_x <= (conc*1.1):
                # Convert back to molar
                if pd.isna(self.Input["NormMean"].loc[conc_M,self.Cycle]) == False:
                    if hover_y >= (self.Input["NormMean"].loc[conc_M,self.Cycle] - within) and hover_y <= (self.Input["NormMean"].loc[conc_M,self.Cycle] + within):
                        str_Tooltip = "x: " + str(conc) + " " + chr(181) +"M\ny: " + str(round(resp,2)) + str_Unit
                elif pd.isna(self.Input["NormExcluded"].loc[conc_M,self.Cycle]) == False:
                    if hover_y >= (self.Input["NormExcluded"].loc[conc_M,self.Cycle] - within) and hover_y <= (self.Input["NormExcluded"].loc[conc_M,self.Cycle] + within):
                        str_Tooltip = "x: " + str(conc) + " " + chr(181) +"M\ny: " + str(round(excl,2)) + str_Unit
                if not str_Tooltip == None:
                    self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                    self.tltp.Show()
                    self.SetFocus()

    def DestroyToolTip(self, event):
        try: self.tltp.Destroy()
        except: None
    
    # Function for clicking on points
    def PickPoint(self, event):
        """
        This function takes the "pick_event" from the matplotlib plot and uses that to exclude or include datapoints in the curve fit.
        - The ID of the sample is saved as a property of the plot
        - Datapoint gets retrieved from the event
        """
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get selected datapoint:
        # We need have a series for each datapoint to allow for the use of markers for each datapoint.
        picked_conc = df.nearest(self.Dose,event.mouseevent.xdata/1000000) # from micromolar to molar
        # exclude datapoint:
        # 1. First write value into lst_RawExcluded/lst_NormExcluded, write np.nan into lst_Raw/lst_Norm
        if np.isnan(self.Input["NormMean"].loc[picked_conc,self.Cycle]) == False:
            # First check if there are enough datapoints left to perform a fit
            counter = 0
            for datapoint in self.Input["NormMean"].loc[:,self.Cycle].tolist():
                if np.isnan(datapoint) == False:
                    counter += 1
            if counter > 5:
                # Selected datapoint IS NOT excluded -> copy it into excluded series and set value in data series to nan
                self.Input["RawExcluded"].at[picked_conc,self.Cycle] = self.Input["RawMean"].loc[picked_conc,self.Cycle]
                self.Input["RawMean"].at[picked_conc,self.Cycle] = np.nan
                self.Input["NormExcluded"].at[picked_conc,self.Cycle] = self.Input["NormMean"].loc[picked_conc,self.Cycle]
                self.Input["NormMean"].at[picked_conc,self.Cycle] = np.nan
            else:
                wx.MessageBox("You are trying to remove too many points. Attempting to fit with less than five points will not produce a reliable fit.",
                    "Not enough points left",
                    wx.OK|wx.ICON_INFORMATION)
        else:
            # Selected datapoint IS excluded -> copy it back into data series and set value in excluded series to nan
            self.Input["RawMean"].at[picked_conc,self.Cycle] = self.Input["RawExcluded"].loc[picked_conc,self.Cycle]
            self.Input["RawExcluded"].at[picked_conc,self.Cycle] = np.nan
            self.Input["NormMean"].at[picked_conc,self.Cycle] = self.Input["NormExcluded"].loc[picked_conc,self.Cycle]
            self.Input["NormExcluded"].at[picked_conc,self.Cycle] = np.nan
        
        # Check whether a re-fit is required:
        self.Input["DoFit"].at["Value",self.Cycle] = df.get_DoFit(self.Input["NormMean"].loc[:,self.Cycle].tolist(),self.Input["NormSEM"].loc[:,self.Cycle].tolist())
            
        if self.Input["DoFit"].at["Value",self.Cycle] == True:
            # 3. Re-fit
            lst_FitResults = ff.sigmoidal_free(self.Input["Concentrations"], self.Input["NormMean"].loc[:,self.Cycle].tolist())  # only function for constrained needs SEM
            self.Input.at["NormFitFree"].loc[:,self.Cycle] = lst_FitResults[0]
            self.Input.at["NormFitFreePars"].loc[:,self.Cycle] = lst_FitResults[1]
            self.Input.at["NormFitFreeCI"].loc[:,self.Cycle] = lst_FitResults[2]
            self.Input.at["NormFitFreeErrors"].loc[:,self.Cycle] = lst_FitResults[3]
            self.Input.loc["NormFitFreeR2"].at["Value",self.Cycle] = lst_FitResults[4]
            self.Input.loc["DoNormFitFree"].at["Value",self.Cycle] = lst_FitResults[5]
            lst_FitResults = ff.sigmoidal_constrained(self.Input["Concentrations"], self.Input["NormMean"].loc[:,self.Cycle].tolist(), self.Input["NormSEM"].loc[:,self.Cycle].tolist())  # only function for constrained needs SEM
            self.Input.at["NormFitConst"].loc[:,self.Cycle] = lst_FitResults[0]
            self.Input.at["NormFitConstPars"].loc[:,self.Cycle] = lst_FitResults[1]
            self.Input.at["NormFitConstCI"].loc[:,self.Cycle] = lst_FitResults[2]
            self.Input.at["NormFitConstErrors"].loc[:,self.Cycle] = lst_FitResults[3]
            self.Input.loc["NormFitConstR2"].at["Value",self.Cycle] = lst_FitResults[4]
            self.Input.loc["DoNormFitConst"].at["Value",self.Cycle] = lst_FitResults[5]

        else:
            self.Input.at["RawFit"].loc[:,self.Cycle] = df.set_to_nan(len(self.Input["RawFit"].loc[:,self.Cycle]))
            self.Input.at["RawFitPars"].loc[:,self.Cycle] = df.set_to_nan(4)
            self.Input.at["RawFitR2"].loc[:,self.Cycle] = np.nan
            
            self.Input.at["NormFitFree"].loc[:,self.Cycle] = df.set_to_nan(len(self.Input["NormFitFree"].loc[:,self.Cycle]))
            self.Input.at["NormFitFreePars"].loc[:,self.Cycle] = df.set_to_nan(4)
            self.Input.at["NormFitFreeR2"].loc[:,self.Cycle] = np.nan

            self.Input.at["NormFitConst"].loc[:,self.Cycle] = df.set_to_nan(len(self.Input["NormFitConst"].loc[:,self.Cycle]))
            self.Input.at["NormFitConstPars"].loc[:,self.Cycle] = df.set_to_nan(4)
            self.Input.at["NormFitConstR2"].loc[:,self.Cycle] = np.nan

            self.Input.at["NormFitFreeCI"].loc[:,self.Cycle], self.Input.at["NormFitConstCI"].loc[:,self.Cycle], self.Input["RawFitCI"].loc[:,self.Cycle] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
            self.Input.at["NormFitFreeErrors"].loc[:,self.Cycle], self.Input.at["NormFitConstErrors"].loc[:,self.Cycle], self.Input["RawFitErrors"].loc[:,self.Cycle] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
        
        # Redraw graph
        self.Draw()
        # 2. Push dfr_Sample back to CompleteContainer and also update all the other plots
        self.tabname.dfr_AssayData.at[self.PlateIndex,"ProcessedDataFrame"].loc[self.SampleIndex] = self.Input
        self.tabname.UpdateIndividualCycleDetails(self.PlateIndex, self.SampleIndex, self.Cycle)

        self.tabname.plt_ProgressCurves.Input = self.tabname.dfr_AssayData.iloc[self.PlateIndex,5].loc[self.SampleIndex]
        self.tabname.plt_ProgressCurves.Draw()
        self.tabname.plt_IndividualIC50AgainstTime.Input = self.tabname.dfr_AssayData.iloc[self.PlateIndex,5].loc[self.SampleIndex]
        self.tabname.plt_IndividualIC50AgainstTime.Draw()
        #self.tabname.UpdateSampleReporting(None)

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        pd.DataFrame({"Concentration[uM]":self.DoseMicromolar,"Response":self.Response,"SEM":self.ErrorBars,"Fit":self.NormFit}).to_clipboard(header=True, index=False)

################################################################################
##                                                                            ##
##    ##   #####  ######    ##  ##   #####    ######  ##  ##    ##  ######    ##
##    ##  ##      ##        ##  ##  ##          ##    ##  ###  ###  ##        ##
##    ##  ##      #####     ##  ##   ####       ##    ##  ########  ####      ##
##    ##  ##          ##     ####       ##      ##    ##  ## ## ##  ##        ##
##    ##   #####  #####       ##    #####       ##    ##  ##    ##  ######    ##
##                                                                            ##
################################################################################

class IndividualIC50AgainstTimePlotPanel(wx.Panel):

    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        titleheight = 30
        plotheight = 350
        plotwidth = 530
        leftaxiswidth = 60
        self.Top = 1-titleheight/PanelSize[1]
        self.Bottom = 1-(titleheight/PanelSize[1])-(plotheight/PanelSize[1])
        self.Right = 1-(PanelSize[0]-plotwidth-leftaxiswidth)/PanelSize[0]
        self.Left = 1-((PanelSize[0]-plotwidth-leftaxiswidth)/PanelSize[0])-(plotwidth/PanelSize[0])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.Confidence = False
        self.Input = None
        self.ShowMarker = True
        self.Picked = 0
        self.SampleIndex = None
        self.PlateIndex = None
        self.Normalised = True
        self.FitType = "Free"
        self.figure.set_facecolor(cs.BgUltraLightHex)

        # Parameters/properties for zooming in on plot:
        self.Zooming = False
        self.Zoomed = False
        self.OriginalXLimits = None
        self.OriginalYLimits = None
        self.ZoomStartX = 0
        self.ZoomStartY = 0
        self.ZoomEndX = 0
        self.ZoomEndY = 0
        self.ZoomFrame = None

        self.Colours = cs.TM_Hex_List + cs.TM_Hex_List + cs.TM_Hex_List

    def Draw(self):
        # Convert dose to micromoles
        #self.Input = self.tabname.dfr_AssayData.loc[0,"ProcessedDataFrame"]
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=self.Left, right=self.Right, top=self.Top , bottom=self.Bottom)
        # Actual Plot
        self.SampleID = self.Input.SampleID
        if self.Normalised == True:
            self.str_Show = "Norm"
        else:
            self.str_Show = "Raw"
        self.lst_IC50s = []
        self.lst_Errors = []
        self.lst_CIUpper = []
        self.lst_CILower = []
        self.lst_CIs = []
        for cycle in self.Input["Time"]:
            if self.Input["Show"].loc["Value",cycle] == 1:
                str_FitType = "Free"
            else:
                str_FitType = "Const"
            self.lst_IC50s.append(self.Input[self.str_Show+"Fit"+str_FitType+"Pars"][cycle][3])
            self.lst_Errors.append(self.Input[self.str_Show+"Fit"+str_FitType+"Errors"][cycle][3])
            self.lst_CIUpper.append(self.Input[self.str_Show+"Fit"+str_FitType+"Pars"][cycle][3] + self.Input[self.str_Show+"Fit"+str_FitType+"CI"][cycle][3])
            self.lst_CILower.append(self.Input[self.str_Show+"Fit"+str_FitType+"Pars"][cycle][3] - self.Input[self.str_Show+"Fit"+str_FitType+"CI"][cycle][3])
            self.lst_CIs.append(self.Input[self.str_Show+"Fit"+str_FitType+"CI"][cycle][3])
        #self.ax.scatter(self.Input["Time"], lst_IC50s, marker="o",label="Data", color=self.Colours[0], picker=5,s=5)
        self.ax.plot(self.Input["Time"], self.lst_IC50s, label="Data", color=self.Colours[0])
        # Make YLimits independent from error bars!
        self.YLimitsNoError = self.ax.get_ylim()
        self.ax.fill_between(self.Input["Time"], self.lst_CIUpper, self.lst_CILower, color="red", alpha=0.15)
        #self.ax.errorbar(self.Input["Time"], lst_IC50s, yerr=lst_Errors,fmt="none", color=self.Colours[0], elinewidth=0.3, capsize=2)
        self.YLimitsWithError = self.ax.get_ylim()
        if self.YLimitsWithError[1] > self.YLimitsNoError[1] * 1.2:
            self.ax.set_ylim(top=self.YLimitsNoError[1] * 1.2)
        if self.YLimitsWithError[0] < self.YLimitsNoError[0] and self.YLimitsWithError[0] > 0:
            self.ax.set_ylim(bottom=self.YLimitsNoError[0] * 0.5)
        elif self.YLimitsWithError[0] < self.YLimitsNoError[0] and self.YLimitsWithError[0] < 0 and self.YLimitsNoError[0] < 0:
            self.ax.set_ylim(bottom=self.YLimitsNoError[0] * 1.2)
        elif self.YLimitsWithError[0] < self.YLimitsNoError[0] and self.YLimitsWithError[0] < 0 and self.YLimitsNoError[0] > 0:
            self.ax.set_ylim(bottom=self.YLimitsNoError[0])
        self.ax.set_title(self.SampleID)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("IC50 ("+chr(181)+"M)")

        if self.ShowMarker == True and self.Picked != None:
            self.ax.axvline(self.Picked,0,1,linestyle="--",linewidth=1.0,color="grey")
        # Set the axe limits if you've zoomed in
        if self.Zoomed == True:
            if self.ZoomStartX > self.ZoomEndX:
                leftlimit = self.ZoomEndX
                rightlimit = self.ZoomStartX
            else:
                leftlimit = self.ZoomStartX
                rightlimit = self.ZoomEndX
            if self.ZoomStartY > self.ZoomEndY:
                bottomlimit = self.ZoomEndY
                toplimit = self.ZoomStartY
            else:
                bottomlimit = self.ZoomStartY
                toplimit = self.ZoomEndY
            self.ax.set_xlim(left=leftlimit, right=rightlimit)
            self.ax.set_ylim(bottom=bottomlimit, top=toplimit)
        self.canvas.mpl_connect("button_press_event", self.OnClick)
        self.canvas.mpl_connect("button_release_event", self.OnRelease)
        self.canvas.mpl_connect("figure_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("motion_notify_event", self.DragZoomFrame)
        self.canvas.draw()

    def OnClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self, event.xdata, event.ydata))
        elif event.button is MouseButton.LEFT:
            if self.Zooming == True:
                self.StartZooming(event)
            else:
                picked = round(event.xdata,2)
                if picked >= self.Input["Time"][0] and picked <= self.Input["Time"][-1]:
                    self.Picked = df.nearest(self.Input["Time"],picked)
                    self.Draw()
                    self.tabname.plt_IndividualCycle.Cycle = self.Picked
                    self.tabname.plt_IndividualCycle.Draw()
                    self.tabname.UpdateIndividualCycleDetails(self.PlateIndex, self.SampleIndex, self.Picked)
                    self.tabname.plt_ProgressCurves.Picked = self.Picked
                    self.tabname.plt_ProgressCurves.Draw()

    def OnRelease(self, event):
        if self.Zooming == True:
            self.EndZoomingButtonLift(event)

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        pd.DataFrame(data={"IC50":self.lst_IC50s,"FitError":self.lst_Errors,"ConfidenceInterval":self.lst_CIs},index=self.Input["Time"]).to_clipboard(header=True, index=True)

    def SetZoomingTrue(self, event):
        self.Zooming = True
        print("fnord zooming true")

    def StartZooming(Plot, event):
        SetCursor(wx.Cursor(wx.CURSOR_MAGNIFIER))
        try:
            Plot.ZoomFrame.Destroy()
            Plot.ZoomFrame = None
        except:
            None
        Plot.Zoomed = False
        Plot.ZoomStartX = round(event.xdata,0)
        Plot.ZoomStartY = round(event.ydata,0)
        Plot.OriginalXLimits = Plot.ax.get_xlim()
        Plot.OriginalYLimits = Plot.ax.get_ylim()
        Plot.ZoomFrameOrigin = wx.Point(wx.GetMousePosition()[0]+2,wx.GetMousePosition()[1]+2)
        Plot.ZoomFrame = ZoomFrame(Plot)
        Plot.ZoomFrame.Show()

    def EndZoomingButtonLift(Plot, event):
        SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        Plot.ZoomEndX = round(event.xdata,0)
        Plot.ZoomEndY = round(event.ydata,0)
        Plot.Zooming = False
        Plot.Zoomed = True
        try:
            Plot.ZoomFrame.Destroy()
            Plot.ZoomFrame = None
        except:
            None
        Plot.Draw()
        print("fnord zooming false")

    def ResetZoom(Plot, event):
        try:
            Plot.ZoomFrame.Destroy()
            Plot.ZoomFrame = None
        except:
            None
        Plot.Zooming = False
        Plot.Zoomed = False
        Plot.Draw()
        print("fnord zooming false")

    def LeaveFigure(Plot, event):
        SetCursor(wx.Cursor(wx.CURSOR_ARROW))
        if Plot.Zooming == True:
            Plot.Zooming = False 
            try:
                if not event.xdata == None:
                    Plot.ZoomEndX = round(event.xdata,0)
                if not event.ydata == None:
                    Plot.ZoomEndY = round(event.ydata,0)
                Plot.Zoomed = True
                Plot.ZoomFrame.Destroy()
                Plot.ZoomFrame = None
                Plot.Draw()
            except:
                None
            print("fnord zooming false")
        
    def DragZoomFrame(Plot, event):
        if Plot.Zooming == True and hasattr(Plot.ZoomFrame, "Position") == True:
            mouseposition = wx.GetMousePosition()
            size_x = abs(mouseposition[0] - Plot.ZoomFrameOrigin[0]) - 2
            size_y = abs(mouseposition[1] - Plot.ZoomFrameOrigin[1]) - 2
            new_size = wx.Size(size_x, size_y)
            if mouseposition[0] < Plot.ZoomFrameOrigin[0]:
                new_x = mouseposition[0] + 2
            else:
                new_x = Plot.ZoomFrameOrigin[0] - 2
            if mouseposition[1] < Plot.ZoomFrameOrigin[1]:
                new_y = mouseposition[1] + 2
            else:
                new_y = Plot.ZoomFrameOrigin[1] - 2
            new_position = wx.Point(new_x, new_y)
            Plot.ZoomFrame.Redraw(new_position, new_size)
            Plot.SetFocus()

########################################################################################
##                                                                                    ##
##    ##    ##  ##  ##  ##      ######  ##          #####   ##       ####   ######    ##
##    ###  ###  ##  ##  ##        ##    ##          ##  ##  ##      ##  ##    ##      ##
##    ########  ##  ##  ##        ##    ##  ######  #####   ##      ##  ##    ##      ##
##    ## ## ##  ##  ##  ##        ##    ##          ##      ##      ##  ##    ##      ##
##    ##    ##   ####   ######    ##    ##          ##      ######   ####     ##      ##
##                                                                                    ##
########################################################################################

class SummaryIC50AgainstTime(wx.Panel):

    def __init__(self,parent,PanelSize,tabname):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.ax = self.figure.add_subplot()
        self.Confidence = False
        self.Input = None
        self.Title = "Summary Plot"
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.IDs = ["","","","","","","",""]
        self.Time = [[],[],[],[],[],[],[],[]]
        self.IC50s = [[],[],[],[],[],[],[],[]]
        self.ExcludedIC50s = [[],[],[],[],[],[],[],[]]
        self.Errors = [[],[],[],[],[],[],[],[]]
        self.IC50Fit = [[],[],[],[],[],[],[],[]]
        self.PreviewID = ""
        self.PreviewTime = []
        self.PreviewIC50s = []
        self.PreviewExcludedIC50s = []
        self.PreviewErrors = []
        self.PreviewIC50Fit = []
        self.ErrorBars = True
        self.ExcludedPoints = True
        self.ColourChoices = cs.TM_RGBA_List
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Preview = True
        self.Logscale = False
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.11, right=0.99, top=self.Top , bottom=self.Bottom)
        # Actual Plot
        for smpl in range(len(self.IDs)):
            if self.IDs[smpl] != "":
                self.ax.scatter(self.Time[smpl], self.IC50s[smpl], label=self.IDs[smpl], marker="o", color=self.Colours[smpl], s= 20)
                if self.ErrorBars == True:
                    self.ax.errorbar(self.Time[smpl], self.IC50s[smpl], yerr=self.Errors[smpl], fmt="none", color=self.Colours[smpl], elinewidth=0.3, capsize=2)
                if self.ExcludedPoints == True and df.any_nonnan(self.ExcludedIC50s[smpl]) == True:
                    self.ax.scatter(self.Time[smpl], self.ExcludedIC50s[smpl], marker="o", color="#FFFFFF", edgecolors=self.Colours[smpl], linewidths=0.8, s= 20)
                    if self.ErrorBars == True:
                        self.ax.errorbar(self.Time[smpl], self.ExcludedIC50s[smpl], yerr=self.Errors[smpl], fmt="none", color=self.Colours[smpl], elinewidth=0.3, capsize=2)
                #self.ax.plot(self.Time[smpl], self.IC50Fit[smpl], color=self.Colours[smpl])
        if self.Preview == True and not self.PreviewID in self.IDs:
            self.ax.scatter(self.PreviewTime, self.PreviewIC50s, label=self.PreviewID, marker="o", color=cs.TMPaleGrey_RGBA, s= 20)
            if self.ErrorBars == True:
                self.ax.errorbar(self.PreviewTime, self.PreviewIC50s, yerr=self.PreviewErrors, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
            if self.ExcludedPoints == True and df.any_nonnan(self.ExcludedIC50s[smpl]) == True:
                self.ax.scatter(self.PreviewTime, self.PreviewExcludedIC50s, marker="o", color="#FFFFFF", edgecolors=cs.TMPaleGrey_RGBA, linewidths=0.8, s= 20)
                if self.ErrorBars == True:
                    self.ax.errorbar(self.PreviewTime, self.PreviewExcludedIC50s, yerr=self.PreviewErrors, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
            #self.ax.plot(self.PreviewTime, self.PreviewIC50Fit, color=cs.TMPaleGrey_RGBA)
        self.ax.set_title(self.Title)
        self.ax.set_xlabel("Time (s)")
        self.ax.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
        self.ax.ticklabel_format(axis="y", style="plain")
        self.ax.set_ylabel("IC50 ("+chr(181)+"M)")
        if self.Logscale == True:
            self.ax.set_yscale("log")
            self.ax.set_ylim(bottom=0.001)
        self.ax.set_xlim(left=-50)
        #self.ax.set_ylim(bottom="-20")
        # Adjust legend:
        graphs = 0
        for i in range(len(self.IDs)):
            if self.IDs[i] != "":
                graphs += 1
        if graphs <= 3:
            y_offset = -0.25
        elif graphs > 3 and graphs < 7:
            y_offset = -0.305
        else:
            y_offset = -0.365
        self.ax.legend(bbox_to_anchor=(0.5,y_offset), loc="lower center", ncol=3)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.draw()
        self.Thaw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        print("TBD")

class DoseMultiPlotPanel(wx.Panel):
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
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = "Summary Plot"
        # Store up to 8 data sets in the instance - last slot is for preview plot!
        self.Dose = [[],[],[],[],[],[],[],[]]
        self.Timestamps = ["","","","","","","",""]
        self.RawPoints = [[],[],[],[],[],[],[],[]]
        self.RawSEM = [[],[],[],[],[],[],[],[]]
        self.RawExcluded = [[],[],[],[],[],[],[],[]]
        self.RawFit = [[],[],[],[],[],[],[],[]]
        self.NormPoints = [[],[],[],[],[],[],[],[]]
        self.NormSEM = [[],[],[],[],[],[],[],[]]
        self.NormExcluded = [[],[],[],[],[],[],[],[]]
        self.NormFit = [[],[],[],[],[],[],[],[]]
        self.PreviewDose = []
        self.PreviewTimeStamp = ""
        self.PreviewRawPoints = []
        self.PreviewRawSEM = []
        self.PreviewRawExcluded = []
        self.PreviewRawFit = []
        self.PreviewNormPoints = []
        self.PreviewNormSEM = []
        self.PreviewNormExcluded = []
        self.PreviewNormFit = []
        self.ErrorBars = True
        self.ExcludedPoints = True
        self.ColourChoices = cs.TM_RGBA_List
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Normalised = True
        self.Preview = True
        self.SetSizer(self.szr_Canvas)
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.11, right=0.99, top=self.Top , bottom=self.Bottom)
        # Actual Plot: Normalisation useful for comparison graph!
        if self.Normalised == True:
            self.ax.set_ylabel("Per-cent inhibition")
            #self.ax.set_ylim([-20,120])
            self.ax.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
            self.ax.axhline(y=100, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=100
            self.ax.ticklabel_format(axis="y", style="plain")
            for i in range(len(self.Timestamps)):
                if self.Timestamps[i] != "":
                    self.ax.scatter(self.Dose[i], self.NormPoints[i], label=self.Timestamps[i], marker="o", color=self.Colours[i])
                    if self.ErrorBars == True:
                        self.ax.errorbar(self.Dose[i], self.NormPoints[i], yerr=self.NormSEM[i], fmt="none", color=self.Colours[i], elinewidth=0.3, capsize=2)
                    if self.ExcludedPoints == True and df.any_nonnan(self.NormExcluded[i]) == True:
                        self.ax.scatter(self.Dose[i], self.NormExcluded[i], marker="o", color="#FFFFFF", edgecolors=self.Colours[i], linewidths=0.8)
                        if self.ErrorBars == True:
                            self.ax.errorbar(self.Dose[i], self.NormExcluded[i], yerr=self.NormSEM[i], fmt="none", color=self.Colours[i], elinewidth=0.3, capsize=2)
                    self.ax.plot(self.Dose[i], self.NormFit[i], color=self.Colours[i])
            if self.Preview == True and not self.PreviewTimestamp in self.Timestamps:
                self.ax.scatter(self.PreviewDose, self.PreviewNormPoints, label=self.PreviewTimestamp, marker="o", color=cs.TMPaleGrey_RGBA)
                if self.ErrorBars == True:
                    self.ax.errorbar(self.PreviewDose, self.PreviewNormPoints, yerr=self.PreviewNormSEM, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                if self.ExcludedPoints == True and df.any_nonnan(self.PreviewNormExcluded) == True:
                    self.ax.scatter(self.PreviewDose, self.PreviewNormExcluded, marker="o", color="#FFFFFF", edgecolors=cs.TMPaleGrey_RGBA, linewidths=0.8)
                    if self.ErrorBars == True:
                        self.ax.errorbar(self.PreviewDose, self.PreviewNormExcluded, yerr=self.PreviewNormSEM, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                self.ax.plot(self.PreviewDose, self.PreviewNormFit, color=cs.TMPaleGrey_RGBA)
        else:
            for i in range(len(self.Timestamps)):
                self.ax.set_ylabel("Signal in AU")
                self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                if self.Timestamps[i] != "":
                    self.ax.scatter(self.Dose[i], self.RawPoints[i], label=self.Timestamps[i], marker="o", color=self.Colours[i])
                    if self.ErrorBars == True:
                        self.ax.errorbar(self.Dose[i], self.RawPoints[i], yerr=self.RawSEM[i], fmt="none", color=self.Colours[i], elinewidth=0.3, capsize=2)
                    if self.ExcludedPoints == True and df.any_nonnan(self.RawExcluded[i]) == True:
                        self.ax.scatter(self.Dose[i], self.RawExcluded[i], marker="o", color="#FFFFFF", edgecolors=self.Colours[i], linewidths=0.8)
                        if self.ErrorBars == True:
                            self.ax.errorbar(self.Dose[i], self.RawExcluded[i], yerr=self.RawSEM[i], fmt="none", color=self.Colours[i], elinewidth=0.3, capsize=2)
                    self.ax.plot(self.Dose[i], self.RawFit[i], color=self.Colours[i])
            if self.Preview == True and not self.PreviewTimestamp in self.Timestamps:
                self.ax.scatter(self.PreviewDose, self.PreviewRawPoints, label=self.PreviewTimestamp, marker="o", color=cs.TMPaleGrey_RGBA)
                if self.ErrorBars == True:
                    self.ax.errorbar(self.PreviewDose, self.PreviewRawPoints, yerr=self.PreviewRawSEM, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                if self.ExcludedPoints == True and df.any_nonnan(self.PreviewRawExcluded) == True:
                    self.ax.scatter(self.PreviewDose, self.PreviewRawExcluded, marker="o", color="#FFFFFF", edgecolors=cs.TMPaleGrey_RGBA, linewidths=0.8)
                    if self.ErrorBars == True:
                        self.ax.errorbar(self.PreviewDose, self.PreviewRawExcluded, yerr=self.PreviewRawSEM, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                self.ax.plot(self.PreviewDose, self.PreviewRawFit, color=cs.TMPaleGrey_RGBA)

        if self.Normalised == True:
            if self.ax.get_ylim()[1] < 120:
                self.ax.set_ylim(top=120)
            if self.ax.get_ylim()[0] > -20:
                self.ax.set_ylim(bottom=-20)
            self.ax.set_ylabel("Per-cent inhibition")
            #self.ax.set_ylim([-20,120])
            self.ax.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
            self.ax.axhline(y=100, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=100
            self.ax.ticklabel_format(axis="y", style="plain")
        else:
            self.ax.set_ylabel("Signal in A.U. (x1000)")
            #self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))

        self.ax.set_xlabel("Concentration (" + chr(181) +"M)")
        self.ax.set_xscale("log")
        self.ax.set_title(self.Title)
        # Adjust legend:
        graphs = 0
        for i in range(len(self.Timestamps)):
            if self.Timestamps[i] != "":
                graphs += 1
        if graphs <= 3:
            y_offset = -0.25
        elif graphs > 3 and graphs < 7:
            y_offset = -0.305
        else:
            y_offset = -0.365
        self.ax.legend(bbox_to_anchor=(0.5,y_offset), loc="lower center", ncol=3)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("axes_leave_event", self.DestroyToolTip)
        self.canvas.draw()
        self.Thaw()

    def DestroyToolTip(self, event):
        try: self.tltp.Destroy()
        except: None

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        data = {}
        for i in range(len(self.IDs)):
            if self.IDs[i] != "":
                data[self.IDs[i]+"[uM]"] = self.Dose[i]
                data[self.IDs[i]+"_%Inhibition"] = self.NormPoints[i]
                data[self.IDs[i]+"SEM"] = self.NormSEM[i]
                data[self.IDs[i]+"FIT"] = self.NormFit[i]
        pd.DataFrame(data=data).to_clipboard(header=True, index=False)

#################################################################################
##                                                                             ##
##     #####  ##  ##    #####  ##      ######    ##      ##   #####  ######    ##
##    ##      ##  ##   ##      ##      ##        ##      ##  ##        ##      ##
##    ##       ####    ##      ##      ####      ##      ##   ####     ##      ##
##    ##        ##     ##      ##      ##        ##      ##      ##    ##      ##
##     #####    ##      #####  ######  ######    ######  ##  #####     ##      ##
##                                                                             ##
#################################################################################

class CycleList(wx.grid.Grid):

    """
    wx.grid.grid subclass with some custom methods for ease of use in this special applications.
    """

    def __init__(self,parent):
        wx.grid.Grid.__init__(self, parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.Cycles = 0
        self.CheckBoxColumn = 0
        self.ButtonColumn = 0

    def SetTimeStamp(self, cycle, label):
        self.SetCellValue(cycle,2,label)

    def SetIC50(self, cycle, label):
        self.SetCellValue(cycle,3,label)

    def SetError(self, cycle, label):
        self.SetCellValue(cycle,4,label)

    def SetRSquare(self, cycle, label):
        self.SetCellValue(cycle,5,label)

    def SetTop(self, cycle, label):
        self.SetCellValue(cycle,6,label)

    def SetBottom(self, cycle, label):
        self.SetCellValue(cycle,7,label)

    def SetSlope(self, cycle, label):
        self.SetCellValue(cycle,8,label)
    
    def SetCheckBoxValue(self, cycle, state):
        if state == True:
            self.SetCellValue(cycle,1,chr(63372)) # Unicode character 63372 is a tickmark in font "Segoe MDL2 Assets"
        else:
            self.SetCellValue(cycle,1,"")

    def GetCheckBoxValue(self, cycle):
        if self.GetCellValue(cycle,1) == chr(63372): # Unicode character 63372 is a tickmark in font "Segoe MDL2 Assets"
            return True
        else:
            return False

    def SetCheckBoxColumn(self, col):
        self.CheckBoxColumn = col

    def SetButtonColumn(self, col):
        self.ButtonColumn = col

    def MouseOverGrid(self, event):
        # https://stackoverflow.com/questions/20589686/tooltip-message-when-hovering-on-cell-with-mouse-in-wx-grid-wxpython
        '''
        Method to calculate where the mouse is pointing and
        then set the tooltip dynamically.
        '''
        # Use CalcUnscrolledPosition() to get the mouse position
        # within the
        # entire grid including what's offscreen
        x, y = self.CalcUnscrolledPosition(event.GetX(),event.GetY())
        coords = self.XYToCell(x, y)
        # you only need these if you need the value in the cell
        evt_row = coords[0]
        evt_col = coords[1]
        if evt_row > 0:
            # Check box column
            if not self.CheckBoxColumn == None:
                if evt_col == self.CheckBoxColumn:
                    event.GetEventObject().SetToolTip("Toggle cycle " + str(evt_row+2))
                else:
                    event.GetEventObject().SetToolTip("")
            # Button column
            if not self.ButtonColumn == None:
                if evt_col == self.ButtonColumn:
                    for row in range(1,self.GetNumberRows()):
                        self.SetCellBackgroundColour(row,self.ButtonColumn,cs.BgMediumDark)    
                    self.SetCellBackgroundColour(evt_row,self.ButtonColumn,wx.Colour(234,107,20))
                    self.ForceRefresh()
                    event.GetEventObject().SetToolTip("Inspect cycle " + str(evt_row+2))
                else:
                    event.GetEventObject().SetToolTip("")
            else:
                event.GetEventObject().SetToolTip("")
                for row in range(self.GetNumberRows()):
                    if self.GetCellBackgroundColour(row,self.ButtonColumn) != cs.BgMediumDark:
                        self.SetCellBackgroundColour(row,self.ButtonColumn,cs.BgMediumDark)
                        self.ForceRefresh()
        else:
            event.GetEventObject().SetToolTip("")

##########################################################################
##                                                                      ##
##     #####  #####    #####           #####   ####   ##  ##   #####    ##
##    ##      ##  ##  ##              ##      ##  ##  ### ##  ##        ##
##     ####   #####   ##              ##      ##  ##  ######  ##        ##
##        ##  ##  ##  ##              ##      ##  ##  ## ###  ##        ##
##    #####   ##  ##   #####  ######   #####   ####   ##  ##   #####    ##
##                                                                      ##
##########################################################################

class dlg_SourceChange (wx.Dialog):

    def __init__(self, parent, str_CurrentConc):
        wx.Dialog.__init__ (self, parent, id = wx.ID_ANY, title = u"Change source concentration", pos = wx.DefaultPosition, size = wx.DefaultSize, style = wx.STAY_ON_TOP)
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        szr_Main = wx.BoxSizer(wx.VERTICAL)

        bSizer51 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticText15 = wx.StaticText(self, wx.ID_ANY, u"Source concentration:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_staticText15.Wrap(-1)

        bSizer51.Add(self.m_staticText15, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.txt_Concentration = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(50,-1), wx.TE_NO_VSCROLL|wx.TE_PROCESS_ENTER)
        self.txt_Concentration.SetValue(str_CurrentConc)
        bSizer51.Add(self.txt_Concentration, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.m_staticText16 = wx.StaticText(self, wx.ID_ANY, u"mM", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_staticText16.Wrap(-1)

        bSizer51.Add(self.m_staticText16, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        szr_Main.Add(bSizer51, 1, wx.EXPAND, 5)

        szr_Buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_Cancel = wx.Button(self, wx.ID_ANY, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0)
        szr_Buttons.Add(self.btn_Cancel, 0, wx.ALL, 5)

        self.btn_Update = wx.Button(self, wx.ID_ANY, u"Update", wx.DefaultPosition, wx.DefaultSize, 0)
        szr_Buttons.Add(self.btn_Update, 0, wx.ALL, 5)

        szr_Main.Add(szr_Buttons, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szr_Main)
        self.Layout()
        szr_Main.Fit(self)

        self.Centre(wx.BOTH)
        self.SetPosition(wx.GetMousePosition())
        # Connect Events
        self.txt_Concentration.Bind(wx.EVT_TEXT, self.OnKeyTyped)
        self.btn_Cancel.Bind(wx.EVT_BUTTON, self.OnCancel)
        self.btn_Update.Bind(wx.EVT_BUTTON, self.OnUpdate)

    def __del__(self):
        pass

    # Virtual event handlers, overide them in your derived class
    def OnKeyTyped(self, event):
        str_Text = self.txt_Concentration.GetValue()
        str_LastChar = str_Text[-1::]
        int_LenText = len(str_Text)
        if len(str_LastChar) != 0:
            if str_LastChar.isalpha() == True and str_LastChar != ".":
                str_Text = str_Text[0:int_LenText-1]
                self.txt_Concentration.write(str_Text)
                
    def OnCancel(self,event):
        global str_NewConc
        str_NewConc = ""
        self.EndModal(False)
        self.Destroy()

    def OnUpdate(self,event):
        global str_NewConc
        str_NewConc = self.txt_Concentration.GetValue()
        if str_NewConc.find(".",0,len(str_NewConc)) == -1:
            str_NewConc = str_NewConc + ".0"
        self.EndModal(True)
        self.Destroy()

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
    def __init__(self, parent, grid, rightclick):
        super(GridContextMenu, self).__init__()
        """
        Context menu to cut, copy, paste, clear and fill down from plate map grid.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        row = rightclick.GetRow()
        col = rightclick.GetCol()

        self.parent = parent
        self.grid = grid

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Copy.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, lambda event: self.Copy(event,  row, col), self.mi_Copy)

    def Copy(self, event, row, col):
        lst_Selection = self.GetGridSelection(self.grid)
        if len(lst_Selection) > 0:
            dfr_Copy = pd.DataFrame()
            for i in range(len(lst_Selection)):
                dfr_Copy.at[lst_Selection[i][0],lst_Selection[i][1]] = self.grid.GetCellValue(lst_Selection[i][0],lst_Selection[i][1])
            dfr_Copy.to_clipboard(header=None, index=False)

    def GetGridSelection(self, grid):
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
        self.Title = u"Dose response time course/enzyme kinetics"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "dose_response_time_course"
        self.str_Shorthand = "DRTC"
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
        #  # ###  ###  #  #   #      ###  ####   #   #  # # #### ###  ############################################

        # Start Building
        self.tab_Details = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.tab_Details.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Assay = wx.BoxSizer(wx.VERTICAL)


        self.szr_Details = wx.BoxSizer(wx.HORIZONTAL)

        # Left Sizer
        self.szr_Left = wx.BoxSizer(wx.VERTICAL)
        # Assay Type Panel
        self.pnl_AssayType = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_AssayType.SetBackgroundColour(clr_Panels)
        self.szr_AssayList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_AssayType = wx.StaticText(self.pnl_AssayType, wx.ID_ANY, u"Device and plate format:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_AssayType.Wrap(-1)
        self.szr_AssayList.Add(self.lbl_AssayType, 0, wx.ALL, 5)
        lbx_AssayTypeChoices = [ u"Pherastar (384 wells)", u"FLIPR (384 wells)" ]
        self.lbx_AssayType = wx.ListBox(self.pnl_AssayType, wx.ID_ANY, wx.DefaultPosition, wx.Size(180,100), lbx_AssayTypeChoices, 0)
        self.lbx_AssayType.SetBackgroundColour(clr_TextBoxes)
        self.szr_AssayList.Add(self.lbx_AssayType, 1, wx.ALL, 5)
        self.lbx_AssayType.SetSelection(0)
        self.pnl_AssayType.SetSizer(self.szr_AssayList)
        self.pnl_AssayType.Layout()
        self.szr_Left.Add(self.pnl_AssayType, 0, wx.EXPAND|wx.ALL, 5)
        #self.pnl_Baseline = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        #self.pnl_Baseline.SetBackgroundColour(clr_Panels)
        #self.szr_Baseline = wx.BoxSizer(wx.VERTICAL)
        #self.chk_Baseline = wx.CheckBox(self.pnl_Baseline, wx.ID_ANY, u"Initial baseline subtraction", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.szr_Baseline.Add(self.chk_Baseline, 0, wx.ALL, 5)
        #self.szr_BaselineWindow = wx.BoxSizer(wx.HORIZONTAL)
        #self.lbl_Baseline = wx.StaticText(self.pnl_Baseline, wx.ID_ANY, u"Length of window: ", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.szr_BaselineWindow.Add(self.lbl_Baseline, 0, wx.ALL, 0)
        #self.txt_Baseline = wx.TextCtrl(self.pnl_Baseline, wx.ID_ANY, u"20", wx.DefaultPosition, wx.Size(25,-1), 1)
        #self.szr_BaselineWindow.Add(self.txt_Baseline, 0, wx.ALL, 0)
        #self.lbl_BaselineSeconds = wx.StaticText(self.pnl_Baseline, wx.ID_ANY, u" s", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.szr_BaselineWindow.Add(self.lbl_BaselineSeconds, 0, wx.ALL, 0)
        #self.szr_Baseline.Add(self.szr_BaselineWindow,0, wx.ALL, 5)
        #self.pnl_Baseline.SetSizer(self.szr_Baseline)
        #self.pnl_Baseline.Layout()
        #self.szr_Baseline.Fit(self.pnl_Baseline)
        #self.szr_Left.Add(self.pnl_Baseline, 0, wx.EXPAND|wx.ALL, 5)
        self.szr_Details.Add(self.szr_Left, 0, wx.EXPAND, 5)
        
        # Middle Sizer ########################################################################################################################################
        self.szr_Middle = wx.BoxSizer(wx.VERTICAL)
        #Protein
        self.pnl_Protein = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Protein.SetBackgroundColour(clr_Panels)
        self.szr_Protein = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Protein = wx.StaticText(self.pnl_Protein, wx.ID_ANY, u"Protein/Enzyme", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Protein.Wrap(-1)
        self.szr_Protein.Add(self.lbl_Protein, 0, wx.ALL, 5)
        self.szr_PurificationID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_PurificationID = wx.StaticText(self.pnl_Protein, wx.ID_ANY, u"Purification ID", wx.DefaultPosition, wx.Size(100,-1), 1)
        self.lbl_PurificationID.Wrap(-1)
        self.szr_PurificationID.Add(self.lbl_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_PurificationID = wx.TextCtrl(self.pnl_Protein, wx.ID_ANY, u"ALBBTA-p001", wx.DefaultPosition, wx.Size(100,-1), 1)
        self.txt_PurificationID.SetMaxSize(wx.Size(-1,-1))
        self.txt_PurificationID.SetBackgroundColour(clr_TextBoxes)
        self.szr_PurificationID.Add(self.txt_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.btn_Lookup_PurificationID = wx.Button(self.pnl_Protein, wx.ID_ANY, u"?", wx.DefaultPosition, wx.Size(23,23), 1)
        self.btn_Lookup_PurificationID.SetMaxSize(wx.Size(23,23))
        self.szr_PurificationID.Add(self.btn_Lookup_PurificationID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Protein.Add(self.szr_PurificationID, 0, wx.EXPAND, 5)
        self.szr_ProteinConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_ProtConc = wx.StaticText(self.pnl_Protein, wx.ID_ANY, u"Protein concentration", wx.DefaultPosition, wx.Size(170,-1), 0)
        self.lbl_ProtConc.Wrap(-1)
        self.szr_ProteinConc.Add(self.lbl_ProtConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_ProteinConc = wx.TextCtrl(self.pnl_Protein, wx.ID_ANY, u"20", wx.DefaultPosition, wx.Size(30,-1), 0)
        self.txt_ProteinConc.SetMaxSize(wx.Size(30,-1))
        self.txt_ProteinConc.SetBackgroundColour(clr_TextBoxes)
        self.szr_ProteinConc.Add(self.txt_ProteinConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM1 = wx.StaticText(self.pnl_Protein, wx.ID_ANY, u"nM", wx.DefaultPosition, wx.Size(25,-1), 0)
        self.lbl_nM1.Wrap(-1)
        self.szr_ProteinConc.Add(self.lbl_nM1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Protein.Add(self.szr_ProteinConc, 0, wx.EXPAND, 5)
        self.pnl_Protein.SetSizer(self.szr_Protein)
        self.pnl_Protein.Layout()
        self.szr_Protein.Fit(self.pnl_Protein)
        self.szr_Middle.Add(self.pnl_Protein, 0, wx.EXPAND|wx.ALL, 5)
        # Substrate 1
        self.pnl_Substrate = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Substrate.SetBackgroundColour(clr_Panels)
        self.szr_Substrate = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Substrate = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"Substrate", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Substrate.Wrap(-1)
        self.szr_Substrate.Add(self.lbl_Substrate, 0, wx.ALL, 5)
        self.szr_SubstrateID = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_SubstrateID = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"Substrate ID", wx.DefaultPosition, wx.Size(100,-1), 0)
        self.lbl_SubstrateID.Wrap(-1)
        self.szr_SubstrateID.Add(self.lbl_SubstrateID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubstrateID = wx.TextCtrl(self.pnl_Substrate, wx.ID_ANY, u"EP000001a", wx.DefaultPosition, wx.Size(100,-1), 0)
        self.txt_SubstrateID.SetMaxSize(wx.Size(100,-1))
        self.txt_SubstrateID.SetBackgroundColour(clr_TextBoxes)
        self.szr_SubstrateID.Add(self.txt_SubstrateID, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.btn_Lookup_Substrate = wx.Button(self.pnl_Substrate, wx.ID_ANY, u"?", wx.DefaultPosition, wx.Size(25,25), 0)
        self.szr_SubstrateID.Add(self.btn_Lookup_Substrate, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Substrate.Add(self.szr_SubstrateID, 1, wx.EXPAND, 5)
        self.szr_SubstrateConc = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_SubstrateConc = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"Substrate concentration", wx.DefaultPosition, wx.Size(170,-1), 0)
        self.lbl_SubstrateConc.Wrap(-1)
        self.szr_SubstrateConc.Add(self.lbl_SubstrateConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_SubstrateConc = wx.TextCtrl(self.pnl_Substrate, wx.ID_ANY, u"20", wx.DefaultPosition, wx.Size(30,-1), 0)
        self.txt_SubstrateConc.SetMaxSize(wx.Size(30,-1))
        self.txt_SubstrateConc.SetBackgroundColour(clr_TextBoxes)
        self.szr_SubstrateConc.Add(self.txt_SubstrateConc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM2 = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"nM", wx.DefaultPosition, wx.Size(25,-1), 0)
        self.lbl_nM2.Wrap(-1)
        self.szr_SubstrateConc.Add(self.lbl_nM2, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Substrate.Add(self.szr_SubstrateConc, 0, wx.EXPAND, 5)
        self.szr_KM = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_KM = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"KM", wx.DefaultPosition, wx.Size(170,-1), 0)
        self.lbl_KM.Wrap(-1)
        self.szr_KM.Add(self.lbl_KM, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.txt_KM = wx.TextCtrl(self.pnl_Substrate, wx.ID_ANY, u"20", wx.DefaultPosition, wx.Size(30,-1), 0)
        self.txt_KM.SetMaxSize(wx.Size(30,-1))
        self.txt_KM.SetBackgroundColour(clr_TextBoxes)
        self.szr_KM.Add(self.txt_KM, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.lbl_nM3 = wx.StaticText(self.pnl_Substrate, wx.ID_ANY, u"nM", wx.DefaultPosition, wx.Size(25,-1), 0)
        self.lbl_nM3.Wrap(-1)
        self.szr_KM.Add(self.lbl_nM3, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.szr_Substrate.Add(self.szr_KM, 0, wx.EXPAND, 5)
        self.pnl_Substrate.SetSizer(self.szr_Substrate)
        self.pnl_Substrate.Layout()
        self.szr_Substrate.Fit(self.pnl_Substrate)
        self.szr_Middle.Add(self.pnl_Substrate, 1, wx.EXPAND |wx.ALL, 5)
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
        self.pnl_ELN.SetMaxSize(wx.Size(250,-1))
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
        self.pnl_Buffer.SetMaxSize(wx.Size(250,-1))
        self.szr_Buffer = wx.BoxSizer(wx.VERTICAL)
        self.lbl_Buffer = wx.StaticText(self.pnl_Buffer, wx.ID_ANY, u"Buffer", wx.DefaultPosition, wx.Size(50,-1), 0)
        self.lbl_Buffer.Wrap(-1)
        self.szr_Buffer.Add(self.lbl_Buffer, 0, wx.ALL, 5)
        self.txt_Buffer = wx.TextCtrl(self.pnl_Buffer, wx.ID_ANY, u"20 mM HEPES. 20 mM NaCl",
            wx.DefaultPosition, wx.Size(360,54), wx.TE_MULTILINE|wx.TE_WORDWRAP)
        self.txt_Buffer.SetBackgroundColour(clr_TextBoxes)
        self.txt_Buffer.SetMaxSize(wx.Size(360,27))
        self.szr_Buffer.Add(self.txt_Buffer, 0, wx.ALL, 5)
        self.pnl_Buffer.SetSizer(self.szr_Buffer)
        self.pnl_Buffer.Layout()
        self.szr_Buffer.Fit(self.pnl_Buffer)
        self.szr_Right.Add(self.pnl_Buffer, 0, wx.ALL, 5)
        # Solvent panel
        self.pnl_Solvent = wx.Panel(self.tab_Details, wx.ID_ANY, wx.DefaultPosition, wx.Size(250,-1), wx.TAB_TRAVERSAL)
        self.pnl_Solvent.SetBackgroundColour(clr_Panels)
        self.pnl_Solvent.SetMaxSize(wx.Size(250,-1))
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
        self.tabs_Analysis.AddPage(self.tab_Details, u"Assay Details", False)

        ##### ###   ##  #  #  ### #### #### ###    # ###   ##  #####  ##
          #   #  # #  # ## # #    #    #    #  #   # #  # #  #   #   #  #
          #   ###  #### # ##  ##  ###  ###  ###   #  #  # ####   #   ####
          #   #  # #  # #  #    # #    #    #  # #   #  # #  #   #   #  #
          #   #  # #  # #  # ###  #    #### #  # #   ###  #  #   #   #  # ########################################

        self.tab_Files = tab.FileSelection(self.tabs_Analysis.sbk_Notebook,
                                           tabname=self,
                                           data=u"directory",
                                           normalise=True,
                                           layouts=False)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Transfer and Data Files", True)

        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  #######################################

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

        #self.pnl_ReviewCycleList = wx.Panel(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.Size(104,-1), wx.TAB_TRAVERSAL)
        #self.pnl_ReviewCycleList.SetBackgroundColour(clr_Panels)
        #self.szr_ReviewCycleList = wx.BoxSizer(wx.VERTICAL)
        #self.lbl_SelectCycle = wx.StaticText(self.pnl_ReviewCycleList, wx.ID_ANY, u"Select a cycle:", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.szr_ReviewCycleList.Add(self.lbl_SelectCycle, 0, wx.ALL, 5)
        ## Cycle grid
        #self.grd_ReviewCycleList = CycleList(self.pnl_ReviewCycleList)
        #self.grd_ReviewCycleList.CreateGrid(0, 3)
        #self.grd_ReviewCycleList.EnableEditing(False)
        #self.grd_ReviewCycleList.EnableGridLines(True)
        #self.grd_ReviewCycleList.EnableDragGridSize(False)
        #self.grd_ReviewCycleList.SetMargins(0, 0)
        ## Columns
        #self.grd_ReviewCycleList.SetColLabelValue(0, u"")
        #self.grd_ReviewCycleList.SetColSize(0,22)
        #self.grd_ReviewCycleList.SetColLabelValue(1, u"Time(s)")
        #self.grd_ReviewCycleList.SetColSize(1,50)
        #self.grd_ReviewCycleList.SetColLabelValue(2, u"")
        #self.grd_ReviewCycleList.SetColSize(2,22)
        #self.grd_ReviewCycleList.EnableDragColMove(False)
        #self.grd_ReviewCycleList.EnableDragColSize(False)
        #self.grd_ReviewCycleList.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        ## Rows: To be done later when populating
        #self.grd_ReviewCycleList.SetRowLabelSize(0)# was 22
        #self.grd_ReviewCycleList.SetColLabelSize(0)# was 22
        #self.grd_ReviewCycleList.EnableDragRowSize(False)
        ## Cell defaults:
        #self.grd_ReviewCycleList.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
        #self.grd_ReviewCycleList.SetCheckBoxColumn(None)
        #self.grd_ReviewCycleList.SetButtonColumn(2)
        #self.grd_ReviewCycleList.AppendRows(1)
        #self.grd_ReviewCycleList.SetCellValue(0,1,u"Time(s)")
        #self.szr_ReviewCycleList.Add(self.grd_ReviewCycleList, 0, wx.ALL, 5)
        #self.pnl_ReviewCycleList.SetSizer(self.szr_ReviewCycleList)
        #self.pnl_ReviewCycleList.Layout()
        #self.szr_ReviewCycleList.Fit(self.pnl_ReviewCycleList)
        #self.szr_Heatmap.Add(self.pnl_ReviewCycleList, 0, wx.ALL, 5)

        # Plot panel ##########################################################################################################################################
        self.szr_ProgressCurves = wx.BoxSizer(wx.VERTICAL)
        self.plt_Heatmap = cp.HeatmapPanel(self.pnl_Review, wx.Size(600,400), self, False,"Signal in A.U. (x1000)", titlefontsize=14)
        self.szr_ProgressCurves.Add(self.plt_Heatmap, 0, wx.ALL|wx.EXPAND, 5)
        self.sld_Heatmap = wx.Slider(self.pnl_Review, wx.ID_ANY, 50, 0, 100, wx.DefaultPosition, wx.Size(600,35), wx.SL_AUTOTICKS|wx.SL_HORIZONTAL|wx.SL_VALUE_LABEL)
        self.szr_ProgressCurves.Add(self.sld_Heatmap, 0, wx.ALL, 5)
        self.lbl_Slider = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Select cycle", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_ProgressCurves.Add(self.lbl_Slider, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.szr_Heatmap.Add(self.szr_ProgressCurves, 1, wx.EXPAND, 5)

        # Sizer for sidebar ###################################################################################################################################
        self.szr_Sidebar = wx.BoxSizer(wx.VERTICAL)
        self.szr_Sidebar.Add((0, 35), 0, wx.EXPAND, 5)
        # Plate details #######################################################################################################################################
        self.szr_Wells = wx.FlexGridSizer(8,3,0,0)
        self.lbl_DisplayPlot = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Plate details:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DisplayPlot, 0, wx.ALL, 5)
        self.lbl_SEM = wx.StaticText(self.pnl_Review, wx.ID_ANY, chr(177)+u"SEM", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SEM, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BufferWellsLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Buffer only wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWellsLabel, 0, wx.ALL, 5)
        self.lbl_BufferWells = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_SolventWellsLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Solvent wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWellsLabel, 0, wx.ALL, 5)
        self.lbl_SolventWells = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ControlWellsLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Control compound wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWellsLabel, 0, wx.ALL, 5)
        self.lbl_ControlWells = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BCLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Buffer to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BCLabel, 0, wx.ALL, 5)
        self.lbl_BC = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_DCLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Solvent to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DCLabel, 0, wx.ALL, 5)
        self.lbl_DC = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ZPrimeMeanLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Z"+chr(39)+u" (mean): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMeanLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMean = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMean, 0, wx.ALL, 5)
        self.btn_ZPrimeMean = CustomBitmapButton(self.pnl_Review, u"InfoUltraLight", 0, (15,15), tooltip=u"How is Z' calculated?")
        self.szr_Wells.Add(self.btn_ZPrimeMean, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedianLabel = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Z"+chr(39)+u" (median): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedianLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedian = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedian, 0, wx.ALL, 5)
        self.btn_ZPrimeMedian = CustomBitmapButton(self.pnl_Review, u"InfoUltraLight", 0, (15,15), tooltip=u"How is Z'(median) calculated?")
        self.szr_Wells.Add(self.btn_ZPrimeMedian, 0, wx.ALL, 5)
        self.szr_Sidebar.Add(self.szr_Wells,0,wx.ALL,0)
        self.lin_BelowDetails = wx.StaticLine(self.pnl_Review, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_Sidebar.Add(self.lin_BelowDetails, 0, wx.EXPAND|wx.ALL, 5)
        self.btn_PlateQualityToClipboard = CustomBitmapButton(self.pnl_Review, u"Clipboard", 0, (130,25))
        self.szr_Sidebar.Add(self.btn_PlateQualityToClipboard, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        # Buttons #############################################################################################################################################
        self.szr_ClipboardExportButtons = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_MapToClipboard = CustomBitmapButton(self.pnl_Review, u"Clipboard", 0, (130,25), tooltip=u"Copy heatmap to clipboard")
        self.szr_ClipboardExportButtons.Add(self.btn_MapToClipboard, 0, wx.ALL, 5)
        self.btn_SaveMap = CustomBitmapButton(self.pnl_Review, u"ExportToFile", 0, (104,25), tooltip=u"Export heatmap as a .PNG file")
        self.szr_ClipboardExportButtons.Add(self.btn_SaveMap, 0, wx.ALL, 5)
        #######################################################################################################################################################
        self.szr_Sidebar.Add(self.szr_ClipboardExportButtons, 0, wx.EXPAND, 0)
        self.szr_Heatmap.Add(self.szr_Sidebar, 0, wx.EXPAND, 5)
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
        #  # #### ###   ##  #### #   ###  ########################################################################

        # Start Building
        self.pnl_Results = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_Results.SetBackgroundColour(cs.BgUltraLight)
        self.szr_Results = wx.BoxSizer(wx.HORIZONTAL)

        #self.szr_ResultsSubdivisions = wx.BoxSizer(wx.HORIZONTAL)

        # Sample List
        self.pnl_SampleList = wx.Panel(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_SampleList.SetBackgroundColour(cs.BgMedium)
        self.szr_SampleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectSample = wx.StaticText(self.pnl_SampleList, wx.ID_ANY, u"Select a sample", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SelectSample.Wrap(-1)
        self.szr_SampleList.Add(self.lbl_SelectSample, 0, wx.ALL, 5)
        self.lbc_Samples = wx.ListCtrl(self.pnl_SampleList, wx.ID_ANY, wx.DefaultPosition, wx.Size(150,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Plate")
        self.lbc_Samples.SetColumnWidth(0,40)
        self.lbc_Samples.InsertColumn(1,"SampleID")
        self.lbc_Samples.SetColumnWidth(1,90)
        self.szr_SampleList.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)
        self.pnl_SampleList.SetSizer(self.szr_SampleList)
        self.pnl_SampleList.Layout()
        self.szr_SampleList.Fit(self.pnl_SampleList)
        self.szr_Results.Add(self.pnl_SampleList, 0, wx.EXPAND, 5)

        # Sizer for plot and plot export buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ProgressCurves = IconTabButton(self.pnl_Results, u"Progress Curves", 0, self.AssayPath)
        self.btn_ProgressCurves.Activate()
        self.szr_SimpleBookTabs.Add(self.btn_ProgressCurves, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_IC50sVsTime = IconTabButton(self.pnl_Results, u"IC50s Over Time", 1, self.AssayPath)
        self.szr_SimpleBookTabs.Add(self.btn_IC50sVsTime, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_DRSummaryPlot = IconTabButton(self.pnl_Results, u"Dose Response Summary Plot", 2, self.AssayPath)
        self.szr_SimpleBookTabs.Add(self.btn_DRSummaryPlot, 0, wx.ALL, 0)
        self.btn_IC50SummaryPlot = IconTabButton(self.pnl_Results, u"Summary Plot", 3, self.AssayPath)
        self.szr_SimpleBookTabs.Add(self.btn_IC50SummaryPlot, 0, wx.ALL, 0)
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        # Simple book has to be defined before assigning it to the buttons
        self.int_sbkWidth = 1070
        self.int_sbkHeight = 600
        self.sbk_ResultPlots = wx.Simplebook(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(self.int_sbkWidth,self.int_sbkHeight), 0)
        # Binding
        self.btn_ProgressCurves.Bind(wx.EVT_BUTTON, self.IndividualSampleTab_ProgressCurves)
        self.btn_IC50sVsTime.Bind(wx.EVT_BUTTON, self.IndividualSampleTab_IC50sVsTime)
        self.btn_DRSummaryPlot.Bind(wx.EVT_BUTTON, self.DRSummaryPlotTab)
        self.btn_IC50SummaryPlot.Bind(wx.EVT_BUTTON, self.IC50SummaryPlotTab)

        # First page in simplebook: Individual sample plots ===================================================================================================
        self.pnl_IndividualSamplePlots = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_IndividualSamplePlots.SetBackgroundColour(cs.BgUltraLight)
        self.szr_IndividualSamplePlots = wx.BoxSizer(wx.HORIZONTAL)
        self.sbk_IndividualSamplePlots = wx.Simplebook(self.pnl_IndividualSamplePlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(700,470), 0)
        # First Panel: Progress Curves =======================================================================================================================#
        self.pnl_ProgressCurves = wx.Panel(self.sbk_IndividualSamplePlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_ProgressCurves.SetBackgroundColour(cs.BgUltraLight)
        self.szr_ProgressCurves = wx.BoxSizer(wx.VERTICAL)
        self.plt_ProgressCurves = ProgressCurves(self.pnl_ProgressCurves, (690,425), self)
        self.szr_ProgressCurves.Add(self.plt_ProgressCurves, 0, wx.ALL, 5)
        # Sizer with buttons for copying/exporting 
        self.szr_ExportAllCylces = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_AllCyclesPlotToClipboard = CustomBitmapButton(self.pnl_ProgressCurves, "Clipboard", 0, (130,25), tooltip="Copy plot to clipboard")
        self.szr_ExportAllCylces.Add(self.btn_AllCyclesPlotToClipboard, 0, wx.ALL, 5)
        self.btn_AllCyclesPlotToFile = CustomBitmapButton(self.pnl_ProgressCurves, u"ExportToFile", 5, (104,25), tooltip="Export plot as .PNG file")
        self.szr_ExportAllCylces.Add(self.btn_AllCyclesPlotToFile, 0, wx.ALL, 5)
        self.btn_AllCyclesSaveAll = CustomBitmapButton(self.pnl_ProgressCurves, "ExportAll", 0, (100,25), tooltip="Export all plots as .PNG files")
        self.szr_ExportAllCylces.Add(self.btn_AllCyclesSaveAll, 0, wx.ALL, 5)
        self.szr_ProgressCurves.Add(self.szr_ExportAllCylces, 0, wx.ALIGN_LEFT, 5)
        self.pnl_ProgressCurves.SetSizer(self.szr_ProgressCurves)
        self.pnl_ProgressCurves.Layout()
        self.szr_ProgressCurves.Fit(self.pnl_ProgressCurves)
        self.sbk_IndividualSamplePlots.AddPage(self.pnl_ProgressCurves, u"ProgressCurves")
        # Second Panel: IC50vsTime ============================================================================================================================
        self.pnl_IC50vsTime = wx.Panel(self.sbk_IndividualSamplePlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_IC50vsTime.SetBackgroundColour(cs.BgUltraLight)
        self.szr_IC50vsTime = wx.BoxSizer(wx.VERTICAL)
        self.plt_IndividualIC50AgainstTime = IndividualIC50AgainstTimePlotPanel(self.pnl_IC50vsTime, (600,425), self)
        self.szr_IC50vsTime.Add(self.plt_IndividualIC50AgainstTime, 0, wx.ALL, 5)
        # Sizer with buttons for copying/exporting
        self.szr_ExportIC50sVsTime = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IC50sVsTimePlotToClipboard = CustomBitmapButton(self.pnl_IC50vsTime, "Clipboard", 0, (130,25),    tooltip="Copy plot to clipboard")
        self.szr_ExportIC50sVsTime.Add(self.btn_IC50sVsTimePlotToClipboard, 0, wx.ALL, 5)
        self.btn_IC50sVsTimePlotToFile = CustomBitmapButton(self.pnl_IC50vsTime, u"ExportToFile", 5, (104,25), tooltip="Export plot as .PNG file")
        self.szr_ExportIC50sVsTime.Add(self.btn_IC50sVsTimePlotToFile, 0, wx.ALL, 5)
        self.btn_IC50sVsTimeSaveAll = CustomBitmapButton(self.pnl_IC50vsTime, "ExportAll", 0, (100,25), tooltip="Export all plots as .PNG files")
        self.szr_ExportIC50sVsTime.Add(self.btn_IC50sVsTimeSaveAll, 0, wx.ALL, 5)
        self.szr_IC50vsTime.Add(self.szr_ExportIC50sVsTime, 0, wx.ALIGN_LEFT, 5)
        self.pnl_IC50vsTime.SetSizer(self.szr_IC50vsTime)
        self.pnl_IC50vsTime.Layout()
        self.szr_IC50vsTime.Fit(self.pnl_IC50vsTime)
        self.sbk_IndividualSamplePlots.AddPage(self.pnl_IC50vsTime, u"IC50sVsTime")
        # =====================================================================================================================================================
        self.szr_IndividualSamplePlots.Add(self.sbk_IndividualSamplePlots, 0, wx.ALL, 0)
        #self.szr_IndividualSamplePlots.Add((5,-1), 0, wx.ALL, 0)
        # Single cycle dose response plot
        self.pnl_IndividualCyclePlot = wx.Panel(self.pnl_IndividualSamplePlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_IndividualCyclePlot.SetBackgroundColour(clr_Panels)
        self.szr_IndividualCyclePlot = wx.BoxSizer(wx.VERTICAL)
        self.plt_IndividualCycle = CurvePlotPanel(self.pnl_IndividualCyclePlot, (325,250), self)
        self.szr_IndividualCyclePlot.Add(self.plt_IndividualCycle, 0, wx.ALL, 5)
        self.szr_BelowIndividualCyclePlot = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_Res_Display = wx.FlexGridSizer(2,3,0,0)
        self.szr_Res_Display.Add((20,0), 0, wx.ALL, 3)
        self.lbl_Display = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Res_Display.Add(self.lbl_Display, 0, wx.ALL, 3)
        self.rad_Res_NormFree = wx.RadioButton(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Normalised (free fit)", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormFree, 0, wx.ALL, 3)
        self.szr_Res_Display.Add((0,0), 0, wx.ALL, 3)
        self.szr_Res_Display.Add((0,0), 0, wx.ALL, 3)
        self.rad_Res_NormConst = wx.RadioButton(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Normalised (constrained fit)", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormConst, 0, wx.ALL, 3)
        self.m_staticline101 = wx.StaticLine(self.pnl_IndividualCyclePlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_BelowIndividualCyclePlot.Add(self.szr_Res_Display, 0, wx.EXPAND, 5)
        self.szr_BelowIndividualCyclePlot.Add(self.m_staticline101, 0, wx.EXPAND|wx.ALL, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.FlexGridSizer(6,3,0,0)
        self.szr_Fit = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Fit this data", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Fit.Add(self.chk_Fit,0,wx.ALL,0)
        self.btn_FitToolTip = CustomBitmapButton(self.pnl_IndividualCyclePlot, u"InfoLight", 0, (15,15), tooltip=u"How is the curve fit calculated?")
        self.btn_FitToolTip.ImagePath = os.path.join(self.parent.str_OtherPath, "SigmoidalDoseResponseToolTip.png")
        self.szr_Fit.Add(self.btn_FitToolTip,0,wx.ALL,0)
        self.szr_Details.Add(self.szr_Fit, 0, wx.ALL, 5)
        # Parameters
        self.lbl_ICLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"IC50:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_ICLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_ICLabel, 0, wx.ALL, 5)
        self.lbl_IC = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC.Wrap(-1)
        self.szr_Details.Add(self.lbl_IC, 0, wx.ALL, 5)
        # Slope
        self.szr_Details.Add((0,0), 0, wx.ALL, 5)
        self.lbl_SlopeLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Slope:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SlopeLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_SlopeLabel, 0, wx.ALL, 5)
        self.lbl_Slope = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Slope.Wrap(-1)
        self.szr_Details.Add(self.lbl_Slope, 0, wx.ALL, 5)
        # Top
        self.szr_Details.Add((0,0), 0, wx.ALL, 5)
        self.lbl_TopLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Top:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_TopLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_TopLabel, 0, wx.ALL, 5)
        self.lbl_Top = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Top.Wrap(-1)
        self.szr_Details.Add(self.lbl_Top, 0, wx.ALL, 5)
        # Bottom
        self.szr_Details.Add((0,0), 0, wx.ALL, 5)
        self.lbl_BottomLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Bottom:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_BottomLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_BottomLabel, 0, wx.ALL, 5)
        self.lbl_Bottom = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Bottom.Wrap(-1)
        self.szr_Details.Add(self.lbl_Bottom, 0, wx.ALL, 5)
        # Span
        self.szr_Details.Add((0,0), 0, wx.ALL, 5)
        self.lbl_SpanLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"Span:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SpanLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_SpanLabel, 0, wx.ALL, 5)
        self.lbl_Span = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_Span.Wrap(-1)
        self.szr_Details.Add(self.lbl_Span, 0, wx.ALL, 5)
        # RSquare
        self.szr_Details.Add((0,0), 0, wx.ALL, 5)
        str_RSquare = "R" + chr(178) + ":"
        self.lbl_RSquareLabel = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, str_RSquare, wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_RSquareLabel.Wrap(-1)
        self.szr_Details.Add(self.lbl_RSquareLabel, 0, wx.ALL, 5)
        self.lbl_RSquare = wx.StaticText(self.pnl_IndividualCyclePlot, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_RSquare.Wrap(-1)
        self.szr_Details.Add(self.lbl_RSquare, 0, wx.ALL, 5)
        self.szr_BelowIndividualCyclePlot.Add(self.szr_Details, 0, wx.EXPAND, 5)
        # Separator line
        self.m_staticline14 = wx.StaticLine(self.pnl_IndividualCyclePlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_BelowIndividualCyclePlot.Add(self.m_staticline14, 0, wx.EXPAND|wx.ALL, 5)
        # Sizer with buttons for copying/exporting 
        self.szr_ExportIndividualCycle = wx.BoxSizer(wx.VERTICAL)
        self.btn_IndividualPlotToClipboard = CustomBitmapButton(self.pnl_IndividualCyclePlot, u"Clipboard", 0, (130,25))
        self.szr_ExportIndividualCycle.Add(self.btn_IndividualPlotToClipboard, 0, wx.ALL, 5)
        self.szr_BelowIndividualCyclePlot.Add(self.szr_ExportIndividualCycle, 0, wx.ALIGN_LEFT, 5)
        # Finish first page
        self.szr_IndividualCyclePlot.Add(self.szr_BelowIndividualCyclePlot, 0, wx.ALL, 5)
        self.pnl_IndividualCyclePlot.SetSizer(self.szr_IndividualCyclePlot)
        self.pnl_IndividualCyclePlot.Layout()
        self.szr_IndividualCyclePlot.Fit(self.pnl_IndividualCyclePlot)
        self.szr_IndividualSamplePlots.Add(self.pnl_IndividualCyclePlot, 0, wx.ALL)
        self.pnl_IndividualSamplePlots.SetSizer(self.szr_IndividualSamplePlots)
        self.pnl_IndividualSamplePlots.Layout()
        self.szr_IndividualSamplePlots.Fit(self.pnl_IndividualSamplePlots)

        #======================================================================================================================================================
        self.sbk_ResultPlots.AddPage(self.pnl_IndividualSamplePlots, u"IndividualSamplePlots",True)


        # Third Page: Summary Plots ===========================================================================================================================
        self.pnl_DRSummaryPlotPage = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_DRSummaryPlotPage.SetBackgroundColour(cs.BgUltraLight)
        self.szr_DRSummaryPlotPage = wx.BoxSizer(wx.HORIZONTAL)
        # Cycle List
        self.szr_CycleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectCycle = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Select a cycle", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_SelectCycle.Wrap(-1)
        self.szr_CycleList.Add(self.lbl_SelectCycle, 0, wx.ALL, 5)
        self.lbc_Cycles = wx.ListCtrl(self.pnl_DRSummaryPlotPage, wx.ID_ANY, wx.DefaultPosition, wx.Size(125,500), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Cycles.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Cycles.InsertColumn(0,"Cycle")
        self.lbc_Cycles.SetColumnWidth(0,50)
        self.lbc_Cycles.InsertColumn(1,"Time(s)")
        self.lbc_Cycles.SetColumnWidth(1,55)
        self.szr_CycleList.Add(self.lbc_Cycles, 1, wx.ALL, 5)
        self.szr_DRSummaryPlotPage.Add(self.szr_CycleList, 0, wx.ALL, 5)
        #self.plt_SummaryPlot = CategoryPlotPanel(self.pnl_DRSummaryPlotPage, (450,450), self)
        #self.szr_DRSummaryPlotPage.Add(self.plt_SummaryPlot, 0, wx.ALL, 5)
        self.plt_DRCurveMultiplot = DoseMultiPlotPanel(self.pnl_DRSummaryPlotPage, (600,550), self)
        self.szr_DRSummaryPlotPage.Add(self.plt_DRCurveMultiplot, 0, wx.ALL, 5)
        self.szr_DRRightHandPanel = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_DRMultiPlotShow = wx.BoxSizer(wx.VERTICAL)
        self.lbl_MultiPlotShow = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_DRMultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.szr_DRMultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.chk_DRErrorBars = wx.CheckBox(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Error bars", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_DRErrorBars.SetValue(True)
        self.szr_DRMultiPlotShow.Add(self.chk_DRErrorBars, 0, wx.ALL, 5)
        self.chk_DRExcludedPoints = wx.CheckBox(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Excluded points", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_DRExcludedPoints.SetValue(True) 
        self.szr_DRMultiPlotShow.Add(self.chk_DRExcludedPoints, 0, wx.ALL, 5)
        self.chk_DRPreviewPlot = wx.CheckBox(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Preview selected plot", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_DRPreviewPlot.SetValue(True) 
        self.szr_DRMultiPlotShow.Add(self.chk_DRPreviewPlot, 0, wx.ALL, 5)
        self.szr_DRRightHandPanel.Add(self.szr_DRMultiPlotShow, 0, wx.EXPAND, 5)
        # FlexGridSizer
        self.szr_DRMultiPlotList = wx.FlexGridSizer(9, 4, 0, 0)
        self.szr_DRMultiPlotList.SetFlexibleDirection(wx.BOTH)
        self.szr_DRMultiPlotList.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.lst_DRColourOptions = cs.TM_Hex_List
        self.lst_DRColourBitmaps = []
        for pic in cs.TM_ColourChoiceIcons_List:
            self.lst_DRColourBitmaps.append(wx.Bitmap(pic, wx.BITMAP_TYPE_ANY))
        # Column labels
        self.lbl_DRColumn1 = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Sample ID/Name", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DRColumn1.Wrap(-1)
        self.szr_DRMultiPlotList.Add(self.lbl_DRColumn1, 0, wx.ALL, 3)
        self.lbl_DRColumn2 = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Colour", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DRColumn2.Wrap(-1)
        self.szr_DRMultiPlotList.Add(self.lbl_DRColumn2, 0, wx.ALL, 3)
        self.lbl_DRColumn3 = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DRColumn3.Wrap(-1)
        self.szr_DRMultiPlotList.Add(self.lbl_DRColumn3, 0, wx.ALL, 3)
        self.lbl_DRColumn4 = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DRColumn4.Wrap(-1)
        self.szr_DRMultiPlotList.Add(self.lbl_DRColumn4, 0, wx.ALL, 3)
        # Fill up with 8 spaces for samples
        self.lst_DRMultiPlotLabels = []
        self.dic_DRMultiPlotLabels = {}
        self.lst_DRBitmapCombos = []
        self.dic_DRBitmapCombos = {}
        self.lst_DRAddButtons = []
        self.dic_DRAddButtons = {}
        self.lst_DRRemoveButtons = []
        self.dic_DRRemoveButtons = {}
        for i in range(8):
            #Label
            self.lst_DRMultiPlotLabels.append("self.lbl_DRSample" + str(i))
            self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[i]] = wx.StaticText(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"no cycle", wx.DefaultPosition, wx.Size(100,-1), 0)
            self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[i]].Wrap(-1)
            self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[i]].Enable(False)
            self.szr_DRMultiPlotList.Add(self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[i]], 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_DRBitmapCombos.append("self.bmc_DRSample" + str(i))
            self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]] = wx.adv.BitmapComboBox(self.pnl_DRSummaryPlotPage, wx.ID_ANY, u"Combo!", wx.DefaultPosition, wx.Size(100,25), self.lst_DRColourOptions, wx.CB_READONLY)
            for j in range(len(self.lst_DRColourBitmaps)):
                self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]].SetItemBitmap(j,self.lst_DRColourBitmaps[j])
            self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]].SetSelection(i)
            self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]].Index = i
            self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]].Enable(False)
            self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]].Bind(wx.EVT_COMBOBOX, self.DRColourSelect)
            self.szr_DRMultiPlotList.Add(self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_DRAddButtons.append("self.btn_DRAdd" + str(i))
            self.dic_DRAddButtons[self.lst_DRAddButtons[i]] = CustomBitmapButton(self.pnl_DRSummaryPlotPage, u"Plus", 0, (25,25))
            self.dic_DRAddButtons[self.lst_DRAddButtons[i]].Index = i
            self.dic_DRAddButtons[self.lst_DRAddButtons[i]].Bind(wx.EVT_BUTTON, self.DRAddGraph)
            self.szr_DRMultiPlotList.Add(self.dic_DRAddButtons[self.lst_DRAddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_DRRemoveButtons.append("self.btn_DRRemove" + str(i))
            self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[i]] = CustomBitmapButton(self.pnl_DRSummaryPlotPage, u"Minus", 0, (25,25))
            self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[i]].Index = i
            self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[i]].Enable(False)
            self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[i]].Bind(wx.EVT_BUTTON, self.DRRemoveGraphButton)
            self.szr_DRMultiPlotList.Add(self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_DRRightHandPanel.Add(self.szr_DRMultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_DRMultiPlotRight = wx.StaticLine(self.pnl_DRSummaryPlotPage, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_DRRightHandPanel.Add(self.lin_DRMultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export
        self.szr_DRExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_DRSummaryPlotToClipboard = CustomBitmapButton(self.pnl_DRSummaryPlotPage, u"Clipboard", 0, (130,25))
        self.szr_DRExportMultiPlot.Add(self.btn_DRSummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_DRSummaryPlotToPNG = CustomBitmapButton(self.pnl_DRSummaryPlotPage, u"ExportToFile", 5, (104,25))
        self.szr_DRExportMultiPlot.Add(self.btn_DRSummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_DRRightHandPanel.Add(self.szr_DRExportMultiPlot, 0, wx.ALL, 0)
        self.szr_DRSummaryPlotPage.Add(self.szr_DRRightHandPanel,0,wx.ALL,5)

        self.pnl_DRSummaryPlotPage.SetSizer(self.szr_DRSummaryPlotPage)
        self.pnl_DRSummaryPlotPage.Layout()
        self.szr_DRSummaryPlotPage.Fit(self.pnl_DRSummaryPlotPage)
        self.sbk_ResultPlots.AddPage(self.pnl_DRSummaryPlotPage, u"DR per sample",True)
        # =====================================================================================================================================================

        # Fourth Page: IC50 Summary Plots =====================================================================================================================
        self.pnl_IC50SummaryPlotPage = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.pnl_IC50SummaryPlotPage.SetBackgroundColour(cs.BgUltraLight)
        self.szr_IC50SummaryPlotPage = wx.BoxSizer(wx.HORIZONTAL)
        
        self.plt_IC50Multiplot = SummaryIC50AgainstTime(self.pnl_IC50SummaryPlotPage, (600,550), self)
        self.szr_IC50SummaryPlotPage.Add(self.plt_IC50Multiplot, 0, wx.ALL, 5)
        self.szr_IC50RightHandPanel = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_IC50MultiPlotShow = wx.BoxSizer(wx.VERTICAL)
        self.lbl_IC50MultiPlotShow = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC50MultiPlotShow.Wrap(-1)
        self.szr_IC50MultiPlotShow.Add(self.lbl_IC50MultiPlotShow, 0, wx.ALL, 5)
        self.szr_IC50MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.chk_IC50ErrorBars = wx.CheckBox(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Error bars", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_IC50ErrorBars.SetValue(True)
        self.szr_IC50MultiPlotShow.Add(self.chk_IC50ErrorBars, 0, wx.ALL, 5)
        self.chk_IC50ExcludedPoints = wx.CheckBox(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Excluded points", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_IC50ExcludedPoints.SetValue(True) 
        self.szr_IC50MultiPlotShow.Add(self.chk_IC50ExcludedPoints, 0, wx.ALL, 5)
        self.chk_IC50PreviewPlot = wx.CheckBox(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Preview selected plot", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_IC50PreviewPlot.SetValue(True) 
        self.szr_IC50MultiPlotShow.Add(self.chk_IC50PreviewPlot, 0, wx.ALL, 5)
        self.chk_IC50Logscale = wx.CheckBox(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Log scale on Y axis", wx.DefaultPosition, wx.DefaultSize, 0)
        self.chk_IC50Logscale.SetValue(False) 
        self.szr_IC50MultiPlotShow.Add(self.chk_IC50Logscale, 0, wx.ALL, 5)
        self.szr_IC50RightHandPanel.Add(self.szr_IC50MultiPlotShow, 0, wx.EXPAND, 5)
        # FlexGridSizer
        self.szr_IC50MultiPlotList = wx.FlexGridSizer(9, 4, 0, 0)
        self.szr_IC50MultiPlotList.SetFlexibleDirection(wx.BOTH)
        self.szr_IC50MultiPlotList.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        self.lst_IC50ColourOptions = cs.TM_Hex_List
        self.lst_IC50ColourBitmaps = []
        for pic in cs.TM_ColourChoiceIcons_List:
            self.lst_IC50ColourBitmaps.append(wx.Bitmap(pic, wx.BITMAP_TYPE_ANY))
        # Column labels
        self.lbl_IC50Column1 = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Sample ID/Name", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC50Column1.Wrap(-1)
        self.szr_IC50MultiPlotList.Add(self.lbl_IC50Column1, 0, wx.ALL, 3)
        self.lbl_IC50Column2 = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Colour", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC50Column2.Wrap(-1)
        self.szr_IC50MultiPlotList.Add(self.lbl_IC50Column2, 0, wx.ALL, 3)
        self.lbl_IC50Column3 = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC50Column3.Wrap(-1)
        self.szr_IC50MultiPlotList.Add(self.lbl_IC50Column3, 0, wx.ALL, 3)
        self.lbl_IC50Column4 = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u" ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_IC50Column4.Wrap(-1)
        self.szr_IC50MultiPlotList.Add(self.lbl_IC50Column4, 0, wx.ALL, 3)
        # Fill up with 8 spaces for samples
        self.lst_IC50MultiPlotLabels = []
        self.dic_IC50MultiPlotLabels = {}
        self.lst_IC50BitmapCombos = []
        self.dic_IC50BitmapCombos = {}
        self.lst_IC50AddButtons = []
        self.dic_IC50AddButtons = {}
        self.lst_IC50RemoveButtons = []
        self.dic_IC50RemoveButtons = {}
        for i in range(8):
            #Label
            self.lst_IC50MultiPlotLabels.append("self.lbl_IC50Sample" + str(i))
            self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[i]] = wx.StaticText(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"no sample", wx.DefaultPosition, wx.Size(100,-1), 0)
            self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[i]].Wrap(-1)
            self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[i]].Enable(False)
            self.szr_IC50MultiPlotList.Add(self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[i]], 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_IC50BitmapCombos.append("self.bmc_IC50Sample" + str(i))
            self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]] = wx.adv.BitmapComboBox(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, u"Combo!", wx.DefaultPosition, wx.Size(100,25), self.lst_IC50ColourOptions, wx.CB_READONLY)
            for j in range(len(self.lst_IC50ColourBitmaps)):
                self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]].SetItemBitmap(j,self.lst_IC50ColourBitmaps[j])
            self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]].SetSelection(i)
            self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]].Index = i
            self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]].Enable(False)
            self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]].Bind(wx.EVT_COMBOBOX, self.IC50ColourSelect)
            self.szr_IC50MultiPlotList.Add(self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_IC50AddButtons.append("self.btn_IC50Add" + str(i))
            self.dic_IC50AddButtons[self.lst_IC50AddButtons[i]] = CustomBitmapButton(self.pnl_IC50SummaryPlotPage, u"Plus", 0, (25,25))
            self.dic_IC50AddButtons[self.lst_IC50AddButtons[i]].Index = i
            self.dic_IC50AddButtons[self.lst_IC50AddButtons[i]].Bind(wx.EVT_BUTTON, self.IC50AddGraph)
            self.szr_IC50MultiPlotList.Add(self.dic_IC50AddButtons[self.lst_IC50AddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_IC50RemoveButtons.append("self.btn_IC50Remove" + str(i))
            self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[i]] = CustomBitmapButton(self.pnl_IC50SummaryPlotPage, u"Minus", 0, (25,25))
            self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[i]].Index = i
            self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[i]].Enable(False)
            self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[i]].Bind(wx.EVT_BUTTON, self.IC50RemoveGraphButton)
            self.szr_IC50MultiPlotList.Add(self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_IC50RightHandPanel.Add(self.szr_IC50MultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_IC50MultiPlotRight = wx.StaticLine(self.pnl_IC50SummaryPlotPage, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_IC50RightHandPanel.Add(self.lin_IC50MultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export
        self.szr_IC50ExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IC50SummaryPlotToClipboard = CustomBitmapButton(self.pnl_IC50SummaryPlotPage, u"Clipboard", 0, (130,25))
        self.szr_IC50ExportMultiPlot.Add(self.btn_IC50SummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_IC50SummaryPlotToPNG = CustomBitmapButton(self.pnl_IC50SummaryPlotPage, u"ExportToFile", 5, (104,25))
        self.szr_IC50ExportMultiPlot.Add(self.btn_IC50SummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_IC50RightHandPanel.Add(self.szr_IC50ExportMultiPlot, 0, wx.ALL, 0)
        self.szr_IC50SummaryPlotPage.Add(self.szr_IC50RightHandPanel,0,wx.ALL,5)

        self.pnl_IC50SummaryPlotPage.SetSizer(self.szr_IC50SummaryPlotPage)
        self.pnl_IC50SummaryPlotPage.Layout()
        self.szr_IC50SummaryPlotPage.Fit(self.pnl_IC50SummaryPlotPage)
        self.sbk_ResultPlots.AddPage(self.pnl_IC50SummaryPlotPage, u"IC50sAllSamples",True)
        # =====================================================================================================================================================

        self.sbk_ResultPlots.SetSelection(0)
        # =====================================================================================================================================================

        self.szr_SimpleBook.Add(self.sbk_ResultPlots, 0, wx.EXPAND, 5)        
        self.szr_Results.Add(self.szr_SimpleBook, 0, wx.ALL, 5)
        
        # Finalise
        self.pnl_Results.SetSizer(self.szr_Results)
        self.pnl_Results.Layout()
        self.szr_Results.Fit(self.pnl_Results)
        self.tabs_Analysis.AddPage(self.pnl_Results, u"Results", False)

        #### #    #  #   ###  #     ##  #####  ###
        #    #    ## #   #  # #    #  #   #   #
        ###  #    # ##   ###  #    #  #   #    ##
        #    #    #  #   #    #    #  #   #      #
        #### #### #  #   #    ####  ##    #   ###  ###############################################################
        
        self.tab_ELNPlots = tab.ELNPlots(self.tabs_Analysis.sbk_Notebook, tabname=self, assaycategory=self.str_AssayCategory)
        self.tabs_Analysis.AddPage(self.tab_ELNPlots, u"Plots for ELN", False)

        #### #  # ###   ##  ###  #####
        #    #  # #  # #  # #  #   #
        ##    ##  ###  #  # ###    #
        #    #  # #    #  # #  #   #
        #### #  # #     ##  #  #   # #############################################################################

        self.lst_Headers_ASHTRF = ["Demethylase AlphaScreen Exp Type","Purification ID","Protein Concentration (uM)","Peptide ID","Global Compound ID",
            "Peptide Concentration (uM)","Solvent","Solvent Concentration (%)","Buffer","Compound Incubation Time (min)","Peptide Incubation Time (min)",
            "Bead Incubation Time (min)","Incubation Temperatures (°C)","Log IC50","Standard Error in Log IC50","IC50 (µM)","IC50 Upper 95% CI","IC50 Lower 95% CI",
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
            "Solvent Control 1 Inhibition %","Solvent Control 1 Inhibition Error %","Solvent Control 2 Inhibition %","Solvent Control 2 Inhibition Error %",
            "Solvent Control 3 Inhibition %","Solvent Control 3 Inhibition Error %","Solvent Control 4 Inhibition %","Solvent Control 4 Inhibition Error %",
            "Solvent Control 5 Inhibition %","Solvent Control 5 Inhibition Error %","Solvent Control 6 Inhibition %","Solvent Control 6 Inhibition Error %",
            "Solvent Control 7 Inhibition %","Solvent Control 7 Inhibition Error %","Solvent Control 8 Inhibition %","Solvent Control 8 Inhibition Error %",
            "Compound Concentration 1 Counter Screen Inhibition (%)","Compound Concentration 1 Counter Screen Inhibition Error (%)",
            "Compound Concentration 2 Counter Screen Inhibition (%)","Compound Concentration 2 Counter Screen Inhibition Error (%)",
            "Compound Concentration 3 Counter Screen Inhibition (%)","Compound Concentration 3 Counter Screen Inhibition Error (%)",
            "Compound Concentration 4 Counter Screen Inhibition (%)","Compound Concentration 4 Counter Screen Inhibition Error (%)",
            "Compound Concentration 5 Counter Screen Inhibition (%)","Compound Concentration 5 Counter Screen Inhibition Error (%)",
            "Compound Concentration 6 Counter Screen Inhibition (%)","Compound Concentration 6 Counter Screen Inhibition Error (%)",
            "Compound Concentration 7 Counter Screen Inhibition (%)","Compound Concentration 7 Counter Screen Inhibition Error (%)",
            "Compound Concentration 8 Counter Screen Inhibition (%)","Compound Concentration 8 Counter Screen Inhibition Error (%)","ELN Experiment ID","Comments"]
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
            "ActAssay ELN Reference","ActAssay Comments"]
        self.lst_Headers = self.lst_Headers_ASHTRF
        self.tab_Export = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
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

        # Tab 1: Assay Details
        

        # Tab 2: Transfer and Data Files

        # Tab 3: Review Plate
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdateReviewPlotPanel)
        self.btn_MapToClipboard.Bind(wx.EVT_BUTTON, self.plt_Heatmap.PlotToClipboard)
        self.btn_SaveMap.Bind(wx.EVT_BUTTON, self.plt_Heatmap.PlotToPNG)
        self.btn_ZPrimeMean.Bind(wx.EVT_BUTTON, self.ZPrimeMean)
        self.btn_ZPrimeMedian.Bind(wx.EVT_BUTTON, self.ZPrimeMedian)
        #self.grd_ReviewCycleList.GetGridWindow().Bind(wx.EVT_MOTION, self.grd_ReviewCycleList.MouseOverGrid)
        self.sld_Heatmap.Bind(wx.EVT_SLIDER, self.SliderAction)

        # Tab 4: Results
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.EditSourceConcentration)
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowProgressCurves)
        # Dose response curves group plot by sample
        # Individual dose response curves
        #self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.ToggleFit)
        self.rad_Res_NormConst.Bind(wx.EVT_RADIOBUTTON, self.RadNormConst)
        self.rad_Res_NormFree.Bind(wx.EVT_RADIOBUTTON, self.RadNormFree)
        self.btn_FitToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.btn_IndividualPlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_IndividualCycle.PlotToClipboard)
        # IC50s vs time plots
        self.btn_IC50sVsTimePlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_IndividualIC50AgainstTime.PlotToClipboard)
        self.btn_IC50sVsTimePlotToFile.Bind(wx.EVT_BUTTON, self.plt_IndividualIC50AgainstTime.PlotToPNG)
        self.btn_IC50sVsTimeSaveAll.Bind(wx.EVT_BUTTON, lambda event: self.AllPlotsToPNG(event, "IC50sVsTime"))
        # Summary plot
        self.lbc_Cycles.Bind(wx.EVT_LIST_ITEM_SELECTED, self.DRShowPreviewPlot)
        self.btn_DRSummaryPlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_DRCurveMultiplot.PlotToClipboard)
        self.btn_DRSummaryPlotToPNG.Bind(wx.EVT_BUTTON, self.plt_DRCurveMultiplot.PlotToPNG)
        self.chk_DRErrorBars.Bind(wx.EVT_CHECKBOX, self.DRShowErrorBars)
        self.chk_DRExcludedPoints.Bind(wx.EVT_CHECKBOX, self.DRShowExcludedPoints)
        self.chk_DRPreviewPlot.Bind(wx.EVT_CHECKBOX, self.DRTogglePreviewPlot)
        self.chk_IC50ErrorBars.Bind(wx.EVT_CHECKBOX, self.IC50ShowErrorBars)
        self.chk_IC50ExcludedPoints.Bind(wx.EVT_CHECKBOX, self.IC50ShowExcludedPoints)
        self.chk_IC50PreviewPlot.Bind(wx.EVT_CHECKBOX, self.IC50TogglePreviewPlot)
        self.chk_IC50Logscale.Bind(wx.EVT_CHECKBOX, self.IC50LogScale)

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
        #elif int_NewTab == 5:
            # going to results table for export tab
        #    if self.bol_ExportPopulated == False:
        #        self.tab_Export.PopulateExportTab()

    def PopulateFromFile(self, dfr_LoadedDetails, lst_LoadedBoolean, dfr_Loaded, lst_Paths):

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
        # str_AssayVolume = self.dfr_Details.loc["AssayVolume","Value"] # in nL
        self.str_DatafileExtension = self.dfr_Details.loc["DataFileExtension","Value"]
        self.SampleSource = self.dfr_Details.loc["SampleSource","Value"]
        # Backwards compatibility wild older save files that do not have newer additions in the assay details:
        try:
            self.Device = self.dfr_Details.loc["Device","Value"]
        except:
            self.Device = "pherastar"
            self.dfr_Details.at["Device","Value"] = self.Device
        try:
            Date = self.dfr_Details.loc["Date","Value"]
            Date = wx.DateTime.FromDMY(int(Date[8:10]), int(Date[5:7]), int(Date[:4]))
            self.tab_Details.DatePicker.SetValue(Date)
        except:
            self.dfr_Details.at["SampleSource","Value"] = "NA"

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
        self.str_AssayType = self.lbx_AssayType.GetString(self.lbx_AssayType.GetSelection())
        self.str_AssayCategory = "dose_response_time_course"
        if self.lbx_AssayType.GetString(self.lbx_AssayType.GetSelection()).find("FLIPR") != -1:
            self.Device = "flipr"
            self.str_DatafileExtension = ".seq"
            self.tab_Files.fpk_Data.wildcard = ".seq"
        else:
            self.Device = "pherastar"
            self.str_DatafileExtension = ".xls"
            self.tab_Files.fpk_Data.wildcard = ".xls"
        self.str_Purification = self.txt_PurificationID.GetLineText(0)
        self.int_ProteinConc = self.txt_ProteinConc.GetLineText(0)
        self.str_SubstrateID = self.txt_SubstrateID.GetLineText(0)
        self.int_SubstrateConc = self.txt_SubstrateConc.GetLineText(0)
        self.str_Solvent = self.txt_Solvent.GetLineText(0)
        self.int_SolventPercent = self.txt_Percent.GetLineText(0)
        self.flt_KM = self.txt_KM.GetLineText(0)
        # Get buffer, needs special consideration since TextCtrl is multiline
        int_Lines = self.txt_Buffer.GetNumberOfLines()
        self.str_Buffer = ""
        for i in range(int_Lines):
            self.str_Buffer = self.str_Buffer + self.txt_Buffer.GetLineText(i)
        self.str_ELN = self.txt_ELN.GetLineText(0)
        self.str_AssayVolume= str(20 * 1000) # convert to nL
        self.SampleSource = "echo"
        self.Date = self.DatePicker.GetValue()
        self.Date = str(self.Date.GetYear()) + "-" + str(self.Date.GetMonth()+1) + "-" + str(self.Date.GetDay()) # GetMonth is indexed from zero!!!!!
        self.Date = datetime.strptime(self.Date,"%Y-%m-%d").strftime("%Y-%m-%d")
        # Include checks so that user does not leave things empty
        dfr_Details_New = pd.DataFrame(data={"Value":[self.str_AssayType, self.str_AssayCategory, "DRTC", self.str_Purification, self.int_ProteinConc, self.str_SubstrateID,
            self.int_SubstrateConc, self.str_Solvent, self.int_SolventPercent, self.flt_KM, self.str_Buffer, self.str_ELN, self.str_AssayVolume, self.str_DatafileExtension, self.SampleSource, self.Device, self.Date]},
            index=["AssayType","AssayCategory","Shorthand","PurificationID","ProteinConcentration","SubstrateID","SubstrateConcentration","Solvent",
            "SolventConcentration","KM","Buffer","ELN","AssayVolume","DataFileExtension","SampleSource","Device","Date"])
        
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
                    self.tab_Export.grd_Database.SetCellValue(idx_List,0,self.str_AssayType + " IC50")
                    self.tab_Export.grd_Database.SetCellValue(idx_List,1,self.str_Purification)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,2,str(float(self.int_ProteinConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,3,self.str_SubstrateID)
                    # omitted
                    self.tab_Export.grd_Database.SetCellValue(idx_List,5,str(float(self.int_SubstrateConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,6,self.str_Solvent)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,7,str(self.int_SolventPercent))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,8,self.str_Buffer)
                    # dfr_Database
                    self.dfr_Database.iloc[idx_List,0] = self.str_AssayType + " IC50"
                    self.dfr_Database.iloc[idx_List,1] = self.str_Purification
                    self.dfr_Database.iloc[idx_List,2] = float(self.int_ProteinConc)/1000
                    self.dfr_Database.iloc[idx_List,3] = self.str_SubstrateID
                    # omitted
                    self.dfr_Database.iloc[idx_List,5] = float(self.int_SubstrateConc)/1000
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
        self.lbc_Plates.Select(0) # This will call UpdateReviewPlotPanel as it is bound to the selection event of the list
        self.lbc_Plates.SetFocus()

        self.sld_Heatmap.SetMin(0)
        self.sld_Heatmap.SetMax(len(self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"Time"])-1)
        self.sld_Heatmap.SetValue(0)
        self.sld_Heatmap.SetTick(self.sld_Heatmap.GetMin())
        self.sld_Heatmap.SetTick(self.sld_Heatmap.GetMax())

        #self.grd_ReviewCycleList.AutoSize()
        #self.grd_ReviewCycleList.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.ReviewCyclesGridLeftClick)
        self.pnl_Review.Layout()

        self.bol_ReviewsDrawn = True

    # 3.2 Updating the heatmap
    def UpdateReviewPlotPanel(self,event):
        # Get current selection
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        cycle = self.plt_Heatmap.Cycle
        int_PlateFormat = self.dfr_AssayData.loc[0,"RawDataFrame"].shape[0]
        self.plt_Heatmap.PlateIndex = idx_Plate
        timestamp = self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"][cycle]
        # Retrieve corresponding raw data
        # Upate heatmap
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        for i in range(len(dfr_Heatmap)):
            dfr_Heatmap.loc[i,"Value"] = self.dfr_AssayData.loc[idx_Plate,"RawDataFrame"].iloc[i,cycle]/1000
            if self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "b":
                dfr_Heatmap.loc[i,"SampleID"] = "Buffer"
            elif self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "r":
                dfr_Heatmap.loc[i,"SampleID"] = "Control"
            elif self.dfr_AssayData.loc[idx_Plate,"Layout"].loc[0,"WellType"][i] == "d":
                dfr_Heatmap.loc[i,"SampleID"] = "Solvent"
            else:
                dfr_Heatmap.loc[i,"SampleID"] = ""
        # This is the bottleneck
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            for j in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Locations"])):
                for k in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Locations"][j])):
                    dfr_Heatmap.loc[int(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Locations"][j][k]),"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
        str_HeatmapTitle = self.dfr_AssayData.iloc[idx_Plate,0] + " (cycle " + str(cycle) + ": " + str(timestamp) + "s)"
        self.plt_Heatmap.Data = dfr_Heatmap
        self.plt_Heatmap.Title = str_HeatmapTitle
        self.plt_Heatmap.Draw()
        # Update plate details (Solvent, buffer and control well mean values):
        if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",timestamp]) == False:
            self.lbl_BufferWells.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",timestamp],1)) + " " + chr(177) + " " + str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferSEM",timestamp],1)))
        else:
            self.lbl_BufferWells.SetLabel(u"N/A")
        if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",timestamp]) == False:
            self.lbl_SolventWells.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",timestamp],1)) + " " + chr(177) + " " + str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",timestamp],1)))
        else:
            self.lbl_SolventWells.SetLabel(u"N/A")
        if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",timestamp]) == False:
            self.lbl_ControlWells.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",timestamp],1)) + " " + chr(177) + " " + str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlSEM",timestamp],1)))
        else:
            self.lbl_ControlWells.SetLabel(u"N/A")
        if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",timestamp]) == False:
            try:
                self.lbl_ZPrimeMean.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",timestamp],3)))
                self.lbl_ZPrimeMedian.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMedian",timestamp],3)))
            except:
                # If the above doesn't work, it's text in these! (i.e. "N/A")
                self.lbl_ZPrimeMean.SetLabel(u"N/A")
                self.lbl_ZPrimeMedian.SetLabel(u"N/A")
            if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",timestamp]) == False:
                self.lbl_BC.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",timestamp]/self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",timestamp],2)))
            else:
                self.lbl_BC.SetLabel(u"N/A")
            if pd.isna(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",timestamp]) == False:
                self.lbl_DC.SetLabel(str(round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",timestamp]/self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",timestamp],2)))
            else:
                self.lbl_DC.SetLabel(u"N/A")
        else:
            self.lbl_ZPrimeMean.SetLabel(u"N/A")
            self.lbl_ZPrimeMedian.SetLabel(u"N/A")
            self.lbl_BC.SetLabel(u"N/A")
            self.lbl_DC.SetLabel(u"N/A")

    #def ReviewCyclesGridLeftClick(self, event):
    #    row = event.GetRow()
    #    col = event.GetCol()
    #    cycle = row - 1
    #    # Test for location: Last column/index 9 is "Button"
    #    if not self.grd_ReviewCycleList.ButtonColumn == None:
    #        if col == self.grd_ReviewCycleList.ButtonColumn:
    #            if cycle != self.plt_Heatmap.Cycle:
    #                self.plt_Heatmap.Cycle = cycle
    #                self.UpdateReviewPlotPanel(None)

    def SliderAction(self, event):
        cycle = int(self.sld_Heatmap.GetValue())
        if cycle != self.plt_Heatmap.Cycle:
            self.plt_Heatmap.Cycle = cycle
            self.UpdateReviewPlotPanel(None)
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
        self.Freeze()
        self.lbc_Samples.DeleteAllItems()
        # Iterate through plates
        idx = -1
        for i in range(len(self.dfr_AssayData)):
            for j in range(len(self.dfr_AssayData.iloc[i,5].index)):
                if self.dfr_AssayData.iloc[i,5].loc[j,"SampleID"] != "Control":
                    idx += 1
                    self.lbc_Samples.InsertItem(idx,str(i+1))
                    self.lbc_Samples.SetItem(idx,1,self.dfr_AssayData.iloc[i,5].loc[j,"SampleID"])

        self.plt_IndividualIC50AgainstTime.Normalised = True
        self.plt_IndividualIC50AgainstTime.FitType = "Const"

        self.lbc_Samples.Select(0) # This will call "ShowProgressCurves", which will update all plots specific to one individual sample

        # One sample DR vs Time summary plot
        self.lbc_Cycles.Select(0)
        cycle = self.lbc_Cycles.GetItemText(self.lbc_Cycles.GetFirstSelected(),0)
        timestamp = float(self.lbc_Cycles.GetItemText(self.lbc_Cycles.GetFirstSelected(),1))
        self.plt_DRCurveMultiplot.Timestamps[0] = timestamp
        self.plt_DRCurveMultiplot.Dose[0] = df.moles_to_micromoles(self.dfr_AssayData.iloc[0,5].loc[0,"Concentrations"])
        self.plt_DRCurveMultiplot.RawPoints[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawSEM[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawExcluded[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawExcluded"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawFit"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormPoints[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormSEM[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormExcluded[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormExcluded"].loc[:,timestamp].tolist()
        if self.dfr_AssayData.iloc[0,5].loc[0,"Show"].loc["Value",timestamp] == 1:
            self.plt_DRCurveMultiplot.NormFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormFitFree"].loc[:,timestamp]
        else:
            self.plt_DRCurveMultiplot.NormFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormFitConst"].loc[:,timestamp]
        self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[0]].Enable(True)
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[0]].SetLabel("Cycle " + cycle + ": " + str(timestamp))
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[0]].Enable(True)
        self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[0]].Enable(True)
        self.plt_DRCurveMultiplot.Draw()

        # Add first IC50vsTime curve to summary plot
        lst_IC50s = []
        lst_Errors = []
        lst_CIs = []
        for cycle in self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"Time"]:
            lst_IC50s.append(self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"NormFitFreePars"][cycle][3])
            lst_Errors.append(self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"NormFitFreeErrors"][cycle][3])
            lst_CIs.append(self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"NormFitFreeCI"][cycle][3])
        self.plt_IC50Multiplot.IDs[0] = self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"SampleID"]
        self.plt_IC50Multiplot.Time[0] = self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"Time"]
        self.plt_IC50Multiplot.IC50s[0] = lst_IC50s
        self.plt_IC50Multiplot.ExcludedIC50s[0] = []
        self.plt_IC50Multiplot.Errors[0] = 0
        self.plt_IC50Multiplot.IC50Fit[0] = []
        self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[0]].Enable(True)
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[0]].SetLabel(self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[0,"SampleID"])
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[0]].Enable(True)
        self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[0]].Enable(True)
        self.plt_IC50Multiplot.Draw()

        self.bol_ResultsDrawn = True
        self.Thaw()

    def IndividualSampleTab_ProgressCurves(self, event):
        if self.sbk_ResultPlots.GetSelection() != 0:
            self.sbk_ResultPlots.SetSelection(0)
        if self.sbk_IndividualSamplePlots.GetSelection() != 0:
            self.sbk_IndividualSamplePlots.SetSelection(0)
        self.btn_ProgressCurves.Activate()
        self.btn_IC50sVsTime.Deactivate()
        self.btn_DRSummaryPlot.Deactivate()
        self.btn_IC50SummaryPlot.Deactivate()

    def IndividualSampleTab_IC50sVsTime(self, event):
        if self.sbk_ResultPlots.GetSelection() != 0:
            self.sbk_ResultPlots.SetSelection(0)
        if self.sbk_IndividualSamplePlots.GetSelection() != 1:
            self.sbk_IndividualSamplePlots.SetSelection(1)
        self.btn_ProgressCurves.Deactivate()
        self.btn_IC50sVsTime.Activate()
        self.btn_DRSummaryPlot.Deactivate()
        self.btn_IC50SummaryPlot.Deactivate()

    def DRSummaryPlotTab(self, event):
        if self.sbk_ResultPlots.GetSelection() != 1:
            self.sbk_ResultPlots.SetSelection(1)
        self.btn_ProgressCurves.Deactivate()
        self.btn_IC50sVsTime.Deactivate()
        self.btn_DRSummaryPlot.Activate()
        self.btn_IC50SummaryPlot.Deactivate()

    def IC50SummaryPlotTab(self, event):
        if self.sbk_ResultPlots.GetSelection() != 2:
            self.sbk_ResultPlots.SetSelection(2)
        self.btn_ProgressCurves.Deactivate()
        self.btn_IC50sVsTime.Deactivate()
        self.btn_DRSummaryPlot.Deactivate()
        self.btn_IC50SummaryPlot.Activate()

    # 4.2 Toggle fit -> change whether a dataset should be fitted or not
    def ToggleFit(self,event):
        # get indices
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] = self.chk_Fit.GetValue()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFitFree"] = self.chk_Fit.GetValue()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFitConst"] = self.chk_Fit.GetValue()
        #if self.chk_Fit.GetValue() == False:
        #    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFitPars"] = df.set_to_nan(4)
        #    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFitFreePars"] = df.set_to_nan(4)
        #    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"]))
        #    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFitFree"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"]))
        #else:
        #    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_sigmoidal(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])

        self.plt_ProgressCurves.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        self.plt_ProgressCurves.PlateIndex = idx_Plate
        self.plt_ProgressCurves.SampleIndex = idx_Sample
        self.plt_ProgressCurves.Draw()
        self.UpdateDetails(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
        #self.UpdateSampleReporting("event")

    # 4.3 Show/Update the displayed curve based on selection on ListCtr
    def ShowProgressCurves(self,event):

        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()

        # Update progress curves
        self.plt_ProgressCurves.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        self.plt_ProgressCurves.PlateIndex = idx_Plate
        self.plt_ProgressCurves.SampleIndex = idx_Sample
        self.plt_ProgressCurves.Draw()
        #self.UpdateSampleReporting(None)


        self.plt_IndividualCycle.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        # If no timepoint has been picked, we want to populate the dose response curve plot with the zero timepoint
        if self.plt_ProgressCurves.Picked == None:
            self.plt_IndividualCycle.Cycle = self.plt_ProgressCurves.Input["Time"][0]
        else:
            self.plt_IndividualCycle.Cycle = self.plt_ProgressCurves.Picked
        self.plt_IndividualCycle.PlateIndex = self.plt_ProgressCurves.PlateIndex
        self.plt_IndividualCycle.SampleIndex = self.plt_ProgressCurves.SampleIndex
        self.plt_IndividualCycle.Draw()
        self.plt_IndividualIC50AgainstTime.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        self.plt_IndividualIC50AgainstTime.Normalised = True
        self.plt_IndividualIC50AgainstTime.FitType = "Const"
        self.plt_IndividualIC50AgainstTime.PlateIndex = idx_Plate
        self.plt_IndividualIC50AgainstTime.SampleIndex = idx_Sample
        self.plt_IndividualIC50AgainstTime.Draw()

        # Cycle listcontrol
        self.lbc_Cycles.DeleteAllItems()
        for cycle in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"])):
            self.lbc_Cycles.InsertItem(cycle,str(cycle))
            self.lbc_Cycles.SetItem(cycle,1,str(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"][cycle]))
        self.lbc_Cycles.Select(0)

        # DRCurveMultiPlot
        for idx_Plot in range(len(self.plt_DRCurveMultiplot.Timestamps)):
            if self.plt_DRCurveMultiplot.Timestamps[idx_Plot] != "":
                self.DRRemoveGraph(idx_Plot)
        self.DRShowPreviewPlot(None)

        # IC50vsTimeSummary
        #for idx_Plot in range(len(self.plt_IC50Multiplot.IDs)):
        #    if self.plt_IC50Multiplot.IDs[idx_Plot] != "":
        #        self.IC50RemoveGraph(idx_Plot)
        self.IC50ShowPreviewPlot(None)
    
    def UpdateDetails(self, idx_Plate, idx_Sample):
        self.lbc_Cycles.DeleteAllItems()
        for cycle in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormMean"])):
            row = cycle + 1
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"].loc["Value",cycle] == 1:
                str_Show = "Norm"
                str_Fit = "Free"
            else:
                str_Show = "Norm"
                str_Fit = "Const"
            self.lbc_Cycles.InsertItem(cycle,str(cycle))
            self.lbc_Cycles.SetItem(cycle,1,str(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"][cycle]))

    # 4.4 Updating the source concentration from dialog box
    def EditSourceConcentration(self,event):
        idx_Focus = self.lbc_Samples.GetFocusedItem()
        str_OldConc = self.lbc_Samples.GetItemText(idx_Focus,2)
        dlg_ChangeSourceConc = dlg_SourceChange(self,str_OldConc)
        bol_Update = dlg_ChangeSourceConc.ShowModal()
        dlg_ChangeSourceConc.Destroy()
        global str_NewConc
        if bol_Update == True:
            if str_NewConc != str_OldConc:
                # Get which plate it is
                idx_Plate = int(self.lbc_Samples.GetItemText(idx_Focus,0))-1 # Human plate numbering vs computer indexing!
                # Get which sample it is
                str_Sample = self.lbc_Samples.GetItemText(idx_Focus,1)
                dfr_Plate = self.dfr_AssayData.iloc[idx_Plate,5]
                idx_Sample = dfr_Plate[dfr_Plate["SampleID"] == str_Sample].index.tolist()
                idx_Sample = idx_Sample[0] # above function returns list, but there will always be only one result
                self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SourceConcentration"] = float(str_NewConc)/1000
                for i in range(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])):
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][i] = df.change_concentrations(float(str_OldConc),float(str_NewConc),
                        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][i],
                        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"AssayVolume"])
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_sigmoidal(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
                self.plt_ProgressCurves.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
                self.plt_ProgressCurves.PlateIndex = idx_Plate
                self.plt_ProgressCurves.SampleIndex = idx_Sample
                self.plt_ProgressCurves.Draw()
                self.lbc_Samples.SetItem(idx_Focus,2,str_NewConc)
                self.UpdateDetails(idx_Plate, idx_Sample)
                #self.UpdateSampleReporting(None)

    # 4.6 Get the indices of the selected plot from the self.dfr_AssayData
    def GetPlotIndices(self):
        # Get list index of selected sample
        idx_SampleList = self.lbc_Samples.GetFirstSelected()
        # Get plate index
        idx_Plate = int(self.lbc_Samples.GetItemText(idx_SampleList,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.dfr_AssayData.iloc[idx_Plate,5]
        idx_SampleDataFrame = dfr_Sample[dfr_Sample["SampleID"] == self.lbc_Samples.GetItemText(idx_SampleList,1)].index.tolist()
        idx_SampleDataFrame = idx_SampleDataFrame[0] # above function returns list, but there will always be only one result
        return idx_SampleList, idx_SampleDataFrame, idx_Plate

    def ShowGroupPlot(self, event):
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.UpdateDetails(idx_Plate, idx_Sample)
        self.ShowProgressCurves(event)

    def AllPlotsToPNG(self, event, plot):
        with wx.DirDialog(self, message="Select a directory to save plots", defaultPath="",
            style=wx.DD_DEFAULT_STYLE, pos=wx.DefaultPosition, size=wx.DefaultSize) as dlg_Directory:

            if dlg_Directory.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            str_SaveDirPath = dlg_Directory.GetPath()
        # Pick directory here. If no directory picked, self.Thaw() and end function.
        self.dlg_PlotsProgress = GenericProgress(self, "Saving Plots")
        self.dlg_PlotsProgress.Show()
        thd_SavingPlots = threading.Thread(target=self.AllPlotsToPNG_thread, args=(str_SaveDirPath,plot), daemon=True)
        thd_SavingPlots.start()

    def AllPlotsToPNG_thread(self, str_SaveDirPath,plot):
        self.Freeze()
        int_Samples = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            int_Samples += len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])
        count = 0
        for idx_Plate in range(len(self.dfr_AssayData)):
            for idx_Sample in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
                count += 1
                #DO STUFF TO MAKE PLOT
                if plot == "AllCycles":
                    tempplot = ProgressCurves(self.pnl_Results, (500,400), self)
                    str_PlotType = "_DR_curves"
                elif plot == "IC50sVsTime":
                    tempplot = IndividualIC50AgainstTimePlotPanel(self.pnl_Results, (500,400), self)
                    str_PlotType = "_IC50s"
                tempplot.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
                tempplot.Draw()
                tempplot.figure.savefig(str_SaveDirPath + chr(92) + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] + str_PlotType + ".png",
                    dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None, transparent=False, bbox_inches=None, pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_PlotsProgress.gauge.SetValue((count/int_Samples)*200)
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()

    def ShowConfidence(self, event):
        self.plt_IndividualCycle.Confidence = event.GetEventObject().GetValue()
        self.plt_IndividualCycle.Draw()
        
    def ShowIndividualCycle(self, idx_Plate, idx_Sample, cycle):
        dfr_Input = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample]
        self.plt_IndividualCycle.Cycle = cycle
        self.plt_IndividualCycle.PlateIndex = idx_Plate
        self.plt_IndividualCycle.SampleIndex = idx_Sample
        self.plt_IndividualCycle.Input = dfr_Input
        self.plt_IndividualCycle.Draw()

    def RadNormFree(self, event):
        self.rad_Res_NormFree.SetValue(True)
        self.rad_Res_NormConst.SetValue(False)

        idx_Plate = self.plt_ProgressCurves.PlateIndex
        idx_Sample = self.plt_ProgressCurves.SampleIndex
        timestamp = self.plt_IndividualCycle.Cycle
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"].loc["Value",timestamp] = self.IntShowIndiDR()
        
        self.plt_IndividualCycle.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR()
        self.plt_IndividualCycle.Draw()
        self.plt_ProgressCurves.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR() # Does not neccessitate redrawing as there are no changes to this plot!
        self.plt_IndividualIC50AgainstTime.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR()
        self.plt_IndividualIC50AgainstTime.Draw()
        self.UpdateIndividualCycleDetails(idx_Plate,idx_Sample,timestamp,False)

    def RadNormConst(self, event):
        self.rad_Res_NormFree.SetValue(False)
        self.rad_Res_NormConst.SetValue(True)

        idx_Plate = self.plt_ProgressCurves.PlateIndex
        idx_Sample = self.plt_ProgressCurves.SampleIndex
        timestamp = self.plt_IndividualCycle.Cycle
        self.plt_IndividualCycle.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR()
        self.plt_IndividualCycle.Draw()
        self.plt_ProgressCurves.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR() # Does not neccessitate redrawing as there are no changes to this plot!
        self.plt_IndividualIC50AgainstTime.Input["Show"].at["Value",timestamp] = self.IntShowIndiDR()
        self.plt_IndividualIC50AgainstTime.Draw()
        self.UpdateIndividualCycleDetails(idx_Plate,idx_Sample,timestamp,False)

    def IntShowIndiDR(self):
        if self.rad_Res_NormFree.Value == True:
            return 1
        elif self.rad_Res_NormConst.Value == True:
            return 2
        else:
            return 0

    def UpdateIndividualCycleDetails(self, idx_Plate, idx_Sample, timestamp, recursion=True):
        if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"].loc["Value",timestamp] == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_RSquareKeyword = "RawFitR2"
            if recursion == True:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(False)
        elif self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"].loc["Value",timestamp] == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoNormFitFree"
            str_Confidence = "NormFitFreeCI"
            str_RSquareKeyword = "NormFitFreeR2"
            if recursion == True:
                self.rad_Res_NormFree.SetValue(True)
                self.rad_Res_NormConst.SetValue(False)
        elif self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"] .loc["Value",timestamp]== 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoNormFitConst"
            str_Confidence = "NormFitConstCI"
            str_RSquareKeyword = "NormFitConstR2"
            if recursion == True:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(True)
        if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_DoFit].loc["Value",timestamp] == True:
            str_IC50 = df.write_IC50(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Inflection",timestamp],
                self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_DoFit].loc["Value",timestamp],
                self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Confidence].loc["Inflection",timestamp])
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Bottom",timestamp] < -20:
                str_BottomWarning = chr(9888) + " outside range"
            else:
                str_BottomWarning = ""
            str_YBot = str(round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Bottom",timestamp],2)) + " " + str_BottomWarning
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Top",timestamp] > 120:
                str_TopWarning = chr(9888) + " outside range"
            else:
                str_TopWarning = ""
            str_YTop = str(round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Top",timestamp],2)) + " " + str_TopWarning
            str_Span = str(round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Top",timestamp]-self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Bottom",timestamp],2))
            str_Hill = str(round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_Pars].loc["Slope",timestamp],2))
            str_RSquare = str(round(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,str_RSquareKeyword].loc["Value",timestamp],3))
            bol_Enable = True
        else:
            str_IC50 = "N.D."
            str_YBot = "N.D."
            str_YTop = "N.D."
            str_Span = "N.D."
            str_Hill = "N.D."
            str_RSquare = "N.D."
            bol_Enable = False
        self.Freeze()
        self.lbl_Bottom.SetLabel(str_YBot)
        self.lbl_Bottom.Enable(bol_Enable)
        self.lbl_Top.SetLabel(str_YTop)
        self.lbl_Top.Enable(bol_Enable)
        self.lbl_Span.SetLabel(str_Span)
        self.lbl_Span.Enable(bol_Enable)
        self.lbl_Slope.SetLabel(str_Hill)
        self.lbl_Slope.Enable(bol_Enable)
        self.lbl_IC.SetLabel(str_IC50)
        self.lbl_IC.Enable(bol_Enable)
        self.lbl_RSquare.SetLabel(str_RSquare)
        self.lbl_RSquare.Enable(bol_Enable)
        self.chk_Fit.SetValue(bol_Enable)
        self.Thaw()

    def DRShowErrorBars(self, event):
        self.plt_DRCurveMultiplot.ErrorBars = event.GetEventObject().GetValue()
        self.plt_DRCurveMultiplot.Draw()

    def DRShowExcludedPoints(self, event):
        self.plt_DRCurveMultiplot.ExcludedPoints = event.GetEventObject().GetValue()
        self.plt_DRCurveMultiplot.Draw()

    def DRTogglePreviewPlot(self, event):
        self.plt_DRCurveMultiplot.Preview = event.GetEventObject().GetValue()
        self.DRShowPreviewPlot(None)

    def DRShowPreviewPlot(self, event):
        # Adds preview plot. Will only be actually displayed if self.plt_DRCurveMultiPlot.Preview is set to True
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        timestamp = float(self.lbc_Cycles.GetItemText(self.lbc_Cycles.GetFirstSelected(),1))
        self.plt_DRCurveMultiplot.PreviewTimestamp = timestamp
        self.plt_DRCurveMultiplot.PreviewDose = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
        self.plt_DRCurveMultiplot.PreviewRawPoints = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewRawSEM = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewRawExcluded = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawExcluded"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewRawFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewNormPoints = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewNormSEM = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.PreviewNormExcluded = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormExcluded"].loc[:,timestamp].tolist()
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"].loc["Value",timestamp] == 1:
            self.plt_DRCurveMultiplot.PreviewNormFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFree"].loc[:,timestamp]
        else:
            self.plt_DRCurveMultiplot.PreviewNormFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitConst"].loc[:,timestamp]
        self.plt_DRCurveMultiplot.Draw()
        
    def DRColourSelect(self, event):
        idx_Combo = event.GetEventObject().GetSelection()
        self.plt_DRCurveMultiplot.Colours[event.GetEventObject().Index] = self.plt_DRCurveMultiplot.ColourChoices[idx_Combo]
        self.plt_DRCurveMultiplot.Draw()

    def DRAddGraph(self, event):
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        cycle = self.lbc_Cycles.GetItemText(self.lbc_Cycles.GetFirstSelected(),0)
        timestamp = float(self.lbc_Cycles.GetItemText(self.lbc_Cycles.GetFirstSelected(),1))
        idx_Graph = event.GetEventObject().Index
        self.plt_DRCurveMultiplot.Timestamps[idx_Graph] = timestamp
        self.plt_DRCurveMultiplot.Dose[idx_Graph] = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
        self.plt_DRCurveMultiplot.RawPoints[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawSEM[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawExcluded[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawExcluded"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.RawFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormPoints[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormMean"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormSEM[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"].loc[:,timestamp].tolist()
        self.plt_DRCurveMultiplot.NormExcluded[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormExcluded"].loc[:,timestamp].tolist()
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"].loc["Value",timestamp] == 1:
            self.plt_DRCurveMultiplot.NormFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFree"].loc[:,timestamp]
        else:
            self.plt_DRCurveMultiplot.NormFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitConst"].loc[:,timestamp]

        self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[idx_Graph]].Enable(True)
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[idx_Graph]].SetLabel("Cycle " + cycle + ": " + str(timestamp))
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[idx_Graph]].Enable(True)
        self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[idx_Graph]].Enable(True)
        self.plt_DRCurveMultiplot.Draw()

    def DRRemoveGraphButton(self, event):
        # First, test that at least one graph will remain on the plot:
        checksum = 0
        for i in range(len(self.plt_DRCurveMultiplot.Timestamps)):
            if self.plt_DRCurveMultiplot.Timestamps[i] != "":
                checksum += 1
        if checksum > 1:
            self.DRRemoveGraph(event.GetEventObject().Index)
        else:
            wx.MessageBox("Cannot remove this graph.\nAt least one graph must be displayed.",
                "No can do",
                wx.OK|wx.ICON_INFORMATION)

    def DRRemoveGraph(self, idx_Graph):
        self.plt_DRCurveMultiplot.Timestamps[idx_Graph] = ""
        self.plt_DRCurveMultiplot.Dose[idx_Graph] = []
        self.plt_DRCurveMultiplot.RawPoints[idx_Graph] = []
        self.plt_DRCurveMultiplot.RawSEM[idx_Graph] = []
        self.plt_DRCurveMultiplot.RawFit[idx_Graph] = []
        self.plt_DRCurveMultiplot.RawExcluded[idx_Graph] = []
        self.plt_DRCurveMultiplot.NormPoints[idx_Graph] = []
        self.plt_DRCurveMultiplot.NormSEM[idx_Graph] = []
        self.plt_DRCurveMultiplot.NormExcluded[idx_Graph] = []
        self.plt_DRCurveMultiplot.NormFit[idx_Graph] = []
        self.dic_DRBitmapCombos[self.lst_DRBitmapCombos[idx_Graph]].Enable(False)
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[idx_Graph]].SetLabel("no cycle")
        self.dic_DRMultiPlotLabels[self.lst_DRMultiPlotLabels[idx_Graph]].Enable(False)
        self.dic_DRRemoveButtons[self.lst_DRRemoveButtons[idx_Graph]].Enable(False)
        self.plt_DRCurveMultiplot.Draw()

    def IC50ShowErrorBars(self, event):
        self.plt_IC50Multiplot.ErrorBars = event.GetEventObject().GetValue()
        self.plt_IC50Multiplot.Draw()

    def IC50ShowExcludedPoints(self, event):
        self.plt_IC50Multiplot.ExcludedPoints = event.GetEventObject().GetValue()
        self.plt_IC50Multiplot.Draw()

    def IC50LogScale(self, event):
        self.plt_IC50Multiplot.Logscale = event.GetEventObject().GetValue()
        self.plt_IC50Multiplot.Draw()

    def IC50ColourSelect(self, event):
        idx_Combo = event.GetEventObject().GetSelection()
        self.plt_IC50Multiplot.Colours[event.GetEventObject().Index] = self.plt_IC50Multiplot.ColourChoices[idx_Combo]
        self.plt_IC50Multiplot.Draw()

    def IC50AddGraph(self, event):
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        idx_Graph = event.GetEventObject().Index
        lst_IC50s = []
        lst_Errors = []
        lst_CIs = []
        for cycle in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"]:
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"].loc["Value",cycle] == 1:
                str_FitType = "Free"
            else:
                str_FitType = "Const"
            lst_IC50s.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"Pars"][cycle][3])
            lst_Errors.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"Errors"][cycle][3])
            lst_CIs.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"CI"][cycle][3])
        self.plt_IC50Multiplot.IDs[idx_Graph] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
        self.plt_IC50Multiplot.Time[idx_Graph] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"]
        self.plt_IC50Multiplot.IC50s[idx_Graph] = lst_IC50s
        self.plt_IC50Multiplot.ExcludedIC50s[idx_Graph] = []
        self.plt_IC50Multiplot.Errors[idx_Graph] = lst_Errors
        self.plt_IC50Multiplot.IC50Fit[idx_Graph] = []

        self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[idx_Graph]].Enable(True)
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[idx_Graph]].SetLabel(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"])
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[idx_Graph]].Enable(True)
        self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[idx_Graph]].Enable(True)
        self.plt_IC50Multiplot.Draw()

    def IC50RemoveGraphButton(self, event):
        # First, test that at least one graph will remain on the plot:
        checksum = 0
        for i in range(len(self.plt_IC50Multiplot.IDs)):
            if self.plt_IC50Multiplot.IDs[i] != "":
                checksum += 1
        if checksum > 1:
            self.IC50RemoveGraph(event.GetEventObject().Index)
        else:
            wx.MessageBox("Cannot remove this graph.\nAt least one graph must be displayed.",
                "No can do",
                wx.OK|wx.ICON_INFORMATION)

    def IC50RemoveGraph(self, idx_Graph):
        self.plt_IC50Multiplot.IDs[idx_Graph] = ""
        self.plt_IC50Multiplot.Time[idx_Graph] = []
        self.plt_IC50Multiplot.IC50s[idx_Graph] = []
        self.plt_IC50Multiplot.ExcludedIC50s[idx_Graph] = []
        self.plt_IC50Multiplot.Errors[idx_Graph] = []
        self.plt_IC50Multiplot.IC50Fit[idx_Graph] = []
        self.dic_IC50BitmapCombos[self.lst_IC50BitmapCombos[idx_Graph]].Enable(False)
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[idx_Graph]].SetLabel("no sample")
        self.dic_IC50MultiPlotLabels[self.lst_IC50MultiPlotLabels[idx_Graph]].Enable(False)
        self.dic_IC50RemoveButtons[self.lst_IC50RemoveButtons[idx_Graph]].Enable(False)
        self.plt_IC50Multiplot.Draw()

    def IC50TogglePreviewPlot(self, event):
        self.plt_IC50Multiplot.Preview = event.GetEventObject().GetValue()
        self.IC50ShowPreviewPlot(None)

    def IC50ShowPreviewPlot(self, event):
        # Adds preview plot. Will only be displayed it self.plt_IC50MultiPlot.Preview is set to True.
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        lst_IC50s = []
        lst_Errors = []
        lst_CIs = []
        for cycle in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"]:
            if self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Show"].loc["Value",cycle] == 1:
                str_FitType = "Free"
            else:
                str_FitType = "Const"
            lst_IC50s.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"Pars"][cycle][3])
            lst_Errors.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"Errors"][cycle][3])
            lst_CIs.append(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFit"+str_FitType+"CI"][cycle][3])
        self.plt_IC50Multiplot.PreviewID = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
        self.plt_IC50Multiplot.PreviewTime = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Time"]
        self.plt_IC50Multiplot.PreviewIC50s = lst_IC50s
        #self.plt_IC50Multiplot.PreviewExcludedIC50s = []
        self.plt_IC50Multiplot.PreviewErrors = lst_Errors
        #self.plt_IC50Multiplot.PreviewIC50Fit = []
        self.plt_IC50Multiplot.Draw()

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