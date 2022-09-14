# Import my own libraries
import lib_datafunctions as df
import lib_customplots as cp
import lib_platefunctions as pf
import lib_colourscheme as cs
import lib_messageboxes as msg
import lib_tabs as tab
from lib_progressdialog import GenericProgress
from lib_custombuttons import CustomBitmapButton

# Import libraries for GUI
import wx
import wx.xrc
import wx.grid
from wx.core import SetCursor

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


##############################################################################################################
##                                                                                                          ##
##    #####   ######   ####    #####  ######  ##   ####   ##  ##          #####   ##       ####   ######    ##
##    ##  ##  ##      ##  ##  ##        ##    ##  ##  ##  ### ##          ##  ##  ##      ##  ##    ##      ##
##    #####   ####    ######  ##        ##    ##  ##  ##  ## ###  ######  #####   ##      ##  ##    ##      ##
##    ##  ##  ##      ##  ##  ##        ##    ##  ##  ##  ##  ##          ##      ##      ##  ##    ##      ##
##    ##  ##  #####   ##  ##   #####    ##    ##   ####   ##  ##          ##      ######   ####     ##      ##
##                                                                                                          ##
##############################################################################################################

class ReactionPlotPanel(wx.Panel):
    def __init__(self, parent, PanelSize, tabname):
        wx.Panel.__init__(self, parent, size=wx.Size(PanelSize))
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
        self.PlateIndex = None
        self.SampleIndex = None
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

    def Draw(self): #str_SampleID, lst_Time, lst_Signal, lst_Fit, lst_Linear, int_Show):
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=self.Left, right=self.Right, top=self.Top, bottom=self.Bottom)
        # Actual Plot
        if self.Input.loc["Show"] == 0:
            self.ax.plot(self.Input.loc["Time"], self.thousands(self.Input.loc["Signal"]), label="Raw signal", color="#872154",pickradius=5)
            #self.ax.plot(lst_Time, lst_Fit, label="Logarithmic fit", color="#ddcc77")
            if self.Input.loc["DoFit"] == True:
                self.ax.plot(self.Input.loc["LinFitTime"], self.thousands(self.Input.loc["LinFit"]), label="Linear fit", color="#ddcc77")
        else:
            self.ax.plot(self.Input.loc["Time"], self.Input.loc["Norm"], label="Normalised signal", color="#872154",pickradius=5)
            #self.ax.plot(lst_Time, lst_Fit, label="Logarithmic fit", color="#ddcc77")
            if self.Input.loc["DoFit"] == True:
                self.ax.plot(self.Input.loc["LinFitTime"], self.Input.loc["LinFit"], label="Linear fit", color="#ddcc77")
        self.ax.set_title(self.Input.loc["SampleID"])
        self.ax.set_xlabel("Time (s)")
        # Set Y axis label and scale according to what's being displayed
        if self.Input.loc["Show"] == 0:
            self.ax.set_ylabel("Signal in A.U. (x1000)")
        else:
            self.ax.set_ylabel("Normalised Signal")
            self.ax.set_ylim([-0.1,1.1])
        self.ax.legend()
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
        # Bind/connect events
        self.canvas.mpl_connect("button_press_event", self.OnClick)
        self.canvas.mpl_connect("button_release_event", self.OnRelease)
        self.canvas.mpl_connect("figure_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("axes_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("motion_notify_event", self.DragZoomFrame)
        self.Bind(wx.EVT_KILL_FOCUS, self.LeaveFigure)
        self.canvas.draw()

    def OnClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))
        elif event.button is MouseButton.LEFT:
            if self.Zooming == True:
                self.StartZooming(event)
            elif self.tabname.chk_ManualBoundaries.GetValue() == True:
                idx_Datapoint = df.nearest(self.Input["Time"],event.xdata, True)
                self.PopupMenu(ctx_LinearBoundaries(self.tabname, idx_Datapoint))
            else:
                return None

    def OnRelease(self, event):
        if self.Zooming == True:
            cp.EndZoomingButtonLift(event)

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

    def PlotToClipboard(self, event):
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

    def thousands(self, lst_Input):
        lst_Return = []
        for x in lst_Input:
            lst_Return.append(x/1000)
        return lst_Return

class ctx_LinearBoundaries(wx.Menu):
    def __init__(self, tabname, idx_Datapoint):

        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.tabname = tabname
        super(ctx_LinearBoundaries, self).__init__()

        self.mi_Start = wx.MenuItem(self, wx.ID_ANY, u"Start", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Start.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\LeftBorder.ico"))
        self.Append(self.mi_Start)
        self.Bind(wx.EVT_MENU, lambda event: self.SetToStart(event, idx_Datapoint), self.mi_Start)

        self.mi_Stop = wx.MenuItem(self, wx.ID_ANY, u"Stop", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Stop.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\RightBorder.ico"))
        self.Append(self.mi_Stop)
        self.Bind(wx.EVT_MENU, lambda event: self.SetToStop(event, idx_Datapoint), self.mi_Stop)

    def SetToStart(self, event, idx_Datapoint):
        self.tabname.Freeze()
        idx_ListControl,idx_Sample,idx_Plate = self.tabname.GetPlotIndices()
        dfr_Working = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        if idx_Datapoint != dfr_Working.loc["LinStop"]:
            if idx_Datapoint > dfr_Working.loc["LinStop"]:
                dfr_Working.loc["LinStart"] = dfr_Working.loc["LinStop"]
                dfr_Working.loc["LinStop"] = idx_Datapoint
            else:
                dfr_Working.loc["LinStart"] = idx_Datapoint
            self.tabname.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_rate(dfr_Working)
            #if self.listtabname_owner.rad_Res_Raw.Value == True:
            #    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
            #else:
            #    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
            self.tabname.lbc_Samples.SetItem(idx_ListControl,3,str(round(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],2)))
            self.tabname.lbc_Samples.SetItem(idx_ListControl,5,str(round(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitCI"][0],2)))
            self.tabname.plt_Reaction.SampleIndex = idx_Sample
            self.tabname.plt_Reaction.PlateIndex = idx_Plate
            self.tabname.plt_Reaction.Input = self.tabname.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
            self.tabname.plt_Reaction.Draw()
            self.tabname.txt_LinStart.SetValue(str(dfr_Working.loc["Time"][dfr_Working.loc["LinStart"]]))
            self.tabname.txt_LinStop.SetValue(str(dfr_Working.loc["Time"][dfr_Working.loc["LinStop"]]))
            if self.tabname.plt_Reaction.Input.loc["SampleID"] in self.tabname.plt_MultiPlot.IDs:
                idx_List,idx_Sample,idx_Plate = self.tabname.GetPlotIndices()
                idx_Graph = self.tabname.plt_MultiPlot.IDs.index(self.tabname.plt_Reaction.Input.loc["SampleID"])
                self.tabname.plt_MultiPlot.IDs[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
                self.tabname.plt_MultiPlot.SignalTime[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"]
                self.tabname.plt_MultiPlot.RawSignal[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Signal"]
                self.tabname.plt_MultiPlot.FitTime[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitTime"]
                self.tabname.plt_MultiPlot.RawFit[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFit"]
                self.tabname.plt_MultiPlot.Draw()
        else:
            msg.StartAndStopIdentical()
        self.tabname.Thaw()

    def SetToStop(self, event, idx_Datapoint):
        self.tabname.Freeze()
        idx_ListControl,idx_Sample,idx_Plate = self.tabname.GetPlotIndices()
        dfr_Working = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        if idx_Datapoint != dfr_Working.loc["LinStop"]:
            if idx_Datapoint < dfr_Working.loc["LinStart"]:
                dfr_Working.loc["LinStop"] = dfr_Working.loc["LinStart"]
                dfr_Working.loc["LinStart"] = idx_Datapoint
            else:
                dfr_Working.loc["LinStop"] = idx_Datapoint
            self.tabname.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_rate(dfr_Working)
            #if self.tabname.rad_Res_Raw.Value == True:
            #    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
            #else:
            #    self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
            self.tabname.lbc_Samples.SetItem(idx_ListControl,3,str(round(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],2)))
            self.tabname.lbc_Samples.SetItem(idx_ListControl,5,str(round(self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],2)))
            self.tabname.plt_Reaction.SampleIndex = idx_Sample
            self.tabname.plt_Reaction.PlateIndex = idx_Plate
            self.tabname.plt_Reaction.Input = self.tabname.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
            self.tabname.plt_Reaction.Draw()
            self.tabname.txt_LinStart.SetValue(str(dfr_Working.loc["Time"][dfr_Working.loc["LinStart"]]))
            self.tabname.txt_LinStop.SetValue(str(dfr_Working.loc["Time"][dfr_Working.loc["LinStop"]]))
            if self.tabname.plt_Reaction.Input.loc["SampleID"] in self.tabname.plt_MultiPlot.IDs:
                idx_List,idx_Sample,idx_Plate = self.tabname.GetPlotIndices()
                idx_Graph = self.tabname.plt_MultiPlot.IDs.index(self.tabname.plt_Reaction.Input.loc["SampleID"])
                self.tabname.plt_MultiPlot.IDs[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
                self.tabname.plt_MultiPlot.SignalTime[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"]
                self.tabname.plt_MultiPlot.RawSignal[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Signal"]
                self.tabname.plt_MultiPlot.FitTime[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitTime"]
                self.tabname.plt_MultiPlot.RawFit[idx_Graph] = self.tabname.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFit"]
                self.tabname.plt_MultiPlot.Draw()
        else:
            msg.StartAndStopIdentical()
        self.tabname.Thaw()

########################################################################################
##                                                                                    ##
##    ##    ##  ##  ##  ##      ######  ##          #####   ##       ####   ######    ##
##    ###  ###  ##  ##  ##        ##    ##          ##  ##  ##      ##  ##    ##      ##
##    ########  ##  ##  ##        ##    ##  ######  #####   ##      ##  ##    ##      ##
##    ## ## ##  ##  ##  ##        ##    ##          ##      ##      ##  ##    ##      ##
##    ##    ##   ####   ######    ##    ##          ##      ######   ####     ##      ##
##                                                                                    ##
########################################################################################

class ReactionMultiPlotPanel(wx.Panel):
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
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Canvas = wx.BoxSizer(wx.VERTICAL)
        self.szr_Canvas.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.ax = self.figure.add_subplot()
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = "Summary Plot"
        # Store up to 8 data sets in the instance
        self.IDs = ["","","","","","","",""]
        self.SignalTime = [[],[],[],[],[],[],[],[]]    
        self.RawSignal = [[],[],[],[],[],[],[],[]]
        self.RawFit = [[],[],[],[],[],[],[],[]]
        self.NormSignal = [[],[],[],[],[],[],[],[]]
        self.NormFit = [[],[],[],[],[],[],[],[]]
        self.FitTime = [[],[],[],[],[],[],[],[]]
        # Preview data set
        self.Preview = True
        self.PreviewID = ""
        self.PreviewSignalTime = []
        self.PreviewIDRawSignal = []
        self.PreviewIDRawFit = []
        self.PreviewIDNormSignal = []
        self.PreviewIDNormFit = []
        self.PreviewIDFitTime = []
        self.ColourChoices = cs.TM_RGBA_List
        self.ColourChoices = cs.TM_RGBA_List
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA, cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA, cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Normalised = False

        self.Zooming = False
        self.Zoomed = False
        self.OriginalXLimits = None
        self.OriginalYLimits = None
        self.ZoomStartX = 0
        self.ZoomStartY = 0
        self.ZoomEndX = 0
        self.ZoomEndY = 0
        self.ZoomFrame = None

        self.SetSizer(self.szr_Canvas)
        self.Fit()

    def Draw(self):
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=self.Left, right=self.Right, top=self.Top, bottom=self.Bottom)
        # Actual Plot: Normalisation useful for comparison graph!
        if self.Normalised == True:
            self.ax.set_ylabel("Normalised signal")
            self.ax.set_ylim([-0.1,1.1])
            self.ax.ticklabel_format(axis="y", style="plain")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    self.ax.plot(self.SignalTime[i], self.NormSignal[i], label=self.IDs[i], linestyle="solid", color=self.Colours[i])
                    self.ax.plot(self.FitTime[i], self.NormFit[i], linestyle="dotted", color=self.Colours[i])
        else:
            for i in range(len(self.IDs)):
                self.ax.set_ylabel("Signal in A.U. (x1000)")
                if self.IDs[i] != "":
                    self.ax.plot(self.SignalTime[i], self.thousands(self.RawSignal[i]), label=self.IDs[i], linestyle="solid", color=self.Colours[i])
                    self.ax.plot(self.FitTime[i], self.thousands(self.RawFit[i]), linestyle="dotted", color=self.Colours[i])

        self.ax.set_xlabel("Time (s)")
        self.ax.set_title(self.Title)
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
        # Bind/connect events
        self.canvas.mpl_connect("button_press_event", self.OnClick)
        self.canvas.mpl_connect("button_release_event", self.OnRelease)
        self.canvas.mpl_connect("figure_leave_event", lambda event: cp.LeaveFigure(event, self))
        self.canvas.mpl_connect("axes_leave_event", lambda event: cp.LeaveFigure(event, self))
        self.Bind(wx.EVT_KILL_FOCUS, lambda event: cp.LeaveFigure(event, self))
        self.canvas.mpl_connect("motion_notify_event", lambda event: cp.DragZoomFrame(event, self))
        self.canvas.draw()
        self.canvas.draw()
        self.Thaw()

    def OnClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(cp.PlotContextMenu(self))
        elif event.button is MouseButton.LEFT:
            if self.Zooming == True:
                self.StartZooming(event)
            else:
                return None

    def OnRelease(self, event):
        if self.Zooming == True:
            self.EndZoomingButtonLift(event)

    def thousands(self, lst_Input):
        lst_Return = []
        for x in lst_Input:
            lst_Return.append(x/1000)
        return lst_Return

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


##############################################################################################
##                                                                                          ##
##    #####   ######  ######   ####   ##  ##              #####   ##       ####   ######    ##
##    ##  ##  ##        ##    ##  ##  ##  ##              ##  ##  ##      ##  ##    ##      ##
##    ##  ##  ####      ##    ######  ##  ##      ######  #####   ##      ##  ##    ##      ##
##    ##  ##  ##        ##    ##  ##  ##  ##              ##      ##      ##  ##    ##      ##
##    #####   ######    ##    ##  ##  ##  ######          ##      ######   ####     ##      ##
##                                                                                          ##
##############################################################################################

class DSFDetailPlot(wx.Panel):
    def __init__(self,parent,PanelSize):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100) #figsze=(5,4.5)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.SampleIndex = None
        self.PlateIndex = None
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.23, right=0.9, top=0.89 , bottom=0.21)
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self, str_Well, str_SampleID, lst_Time, lst_Signal, lst_Fit, int_Show):
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.23, right=0.9, top=0.89 , bottom=0.21)
        # Actual plot
        self.ax.plot(lst_Time, self.thousands(lst_Signal), label="Signal", color="#872154")
        self.ax.plot(lst_Time, self.thousands(lst_Fit), label="Fit", color="#ddcc77")
        #self.ax.plot(lst_Time, lst_Deri, label="1st deriv fit", color="#FF0000")
        self.ax.set_title(str_Well + ": " + str_SampleID)
        self.ax.title.set_size(8)
        self.ax.tick_params(axis="x", labelsize=8)
        self.ax.tick_params(axis="y", labelsize=8)
        self.ax.set_xlabel("Time(s)")
        #self.ax.set_xticks([30,40,50,60,70,80,90])
        self.ax.xaxis.label.set_size(8)
        if int_Show == 0:
            self.ax.set_ylabel("Signal in A.U.")
        else:
            self.ax.set_ylabel("Normalised signal")
        self.ax.yaxis.label.set_size(8)
        # self.ax.legend()
        self.canvas.draw()

    def thousands(self, lst_Input):
        lst_Return = []
        for x in lst_Input:
            lst_Return.append(x/1000)
        return lst_Return

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
        self.Title = u"Enzyme kinetics/initial reaction rate"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "rate"
        self.str_Shorthand = "RATE"
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

        lst_AssayTypes = ["Fluorescence", "Luminescence"]
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
                                           data = u"directory",
                                           normalise=False,
                                           layouts=False)
        self.tabs_Analysis.AddPage(self.tab_Files, u"Transfer and Data Files", True)

        ###  #### #   # # #### #       #    ###  #     ##  ##### ####  ###
        #  # #    #   # # #    #       #    #  # #    #  #   #   #    #
        ###  ###  #   # # ###  #   #   #    ###  #    ####   #   ###   ##
        #  # #     # #  # #     # # # #     #    #    #  #   #   #       #
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  ####################################################################################

        # Start Building
        self.pnl_Review = wx.Panel(self.tabs_Analysis.sbk_Notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
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
        # Add heatmap/grid to sbk_PlatePlots
        self.plt_Heatmap = cp.HeatmapPanel(self.sbk_PlatePlots, wx.Size(600,400), self, True, u"Rate in 1/s")
        self.plt_Heatmap.Layout()
        self.sbk_PlatePlots.AddPage(self.plt_Heatmap, u"Platemap", False)
        self.sbk_PlatePlots.SetBackgroundColour(wx.Colour(102,102,102))
        # Add scatter plot to sbk_PlatePlots
        self.pnl_ScatterPlot = cp.ScatterPlotPanel(self.sbk_PlatePlots, self, wx.Size(600,400), True, 0, [], [], u"Rate in 1/s")
        self.pnl_ScatterPlot.Layout()
        self.sbk_PlatePlots.AddPage(self.pnl_ScatterPlot, u"ScatterPlot", False)
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
        self.lbl_DetailRate = wx.StaticText(self.pnl_Review, wx.ID_ANY, u"Rate: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_DetailRate.Wrap(-1)
        self.szr_DetailControls.Add(self.lbl_DetailRate, 0, wx.ALL)
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
        self.rad_ScatterPlot = wx.RadioButton(self.pnl_Review, wx.ID_ANY, u"Scatter plot", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_Sidebar.Add(self.rad_ScatterPlot, 0, wx.ALL, 5)
        self.rad_ScatterPlot.SetValue(False)
        self.btn_MapToClipboard = CustomBitmapButton(self.pnl_Review, u"Clipboard", 0, (130,25))
        self.szr_Sidebar.Add(self.btn_MapToClipboard, 0, wx.ALL, 5)
        self.btn_SaveMap = CustomBitmapButton(self.pnl_Review, u"ExportToFile", 0, (104,25))
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
        self.lbc_Samples = wx.ListCtrl(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(320,-1), wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Plate")
        self.lbc_Samples.SetColumnWidth(0,40)
        self.lbc_Samples.InsertColumn(1,"Well")
        self.lbc_Samples.SetColumnWidth(1,40)
        self.lbc_Samples.InsertColumn(2,"SampleID")
        self.lbc_Samples.SetColumnWidth(2,90)
        self.lbc_Samples.InsertColumn(3,"Rate")
        self.lbc_Samples.SetColumnWidth(3,45)
        self.lbc_Samples.InsertColumn(4,"")
        self.lbc_Samples.SetColumnWidth(4,20)
        self.lbc_Samples.InsertColumn(5,"")
        self.lbc_Samples.SetColumnWidth(5,45)
        self.szr_SampleList.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)
        # Button to export results table
        self.btn_ExportResultsTable = CustomBitmapButton(self.pnl_Results, u"ExportToFile", 0, (104,25))
        self.szr_SampleList.Add(self.btn_ExportResultsTable, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.bSizer12.Add(self.szr_SampleList, 0, wx.EXPAND, 5)

        # Sizer for plot and plot export buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IndividualPlot = IconTabButton(self.pnl_Results, u"Individual Plot", 0, self.AssayPath)
        self.btn_IndividualPlot.Activate()
        self.szr_SimpleBookTabs.Add(self.btn_IndividualPlot, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_SummaryPlot = IconTabButton(self.pnl_Results, u"Summary Plot", 1, self.AssayPath)
        self.szr_SimpleBookTabs.Add(self.btn_SummaryPlot, 0, wx.ALL, 0)
        self.dic_PlotTabButtons = {0:self.btn_IndividualPlot,1:self.btn_SummaryPlot}
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        self.sbk_ResultPlots = wx.Simplebook(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.Size(900,550), 0)
        self.btn_IndividualPlot.Notebook(self.sbk_ResultPlots)
        self.btn_IndividualPlot.ButtonGroup(self.dic_PlotTabButtons)
        self.btn_IndividualPlot.Bind(wx.EVT_BUTTON, self.btn_IndividualPlot.OpenTab)
        self.btn_SummaryPlot.Notebook(self.sbk_ResultPlots)
        self.btn_SummaryPlot.ButtonGroup(self.dic_PlotTabButtons)
        self.btn_SummaryPlot.Bind(wx.EVT_BUTTON, self.btn_SummaryPlot.OpenTab)

        # First page in simplebook: Resultsplot ===============================================================================================================
        self.pnl_IndividualPlot = wx.Panel(self.sbk_ResultPlots, wx.ID_ANY, wx.DefaultPosition, wx.Size(900,550), wx.TAB_TRAVERSAL)
        self.szr_Plot = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PlotActual = wx.BoxSizer(wx.VERTICAL)
        self.plt_Reaction = ReactionPlotPanel(self.pnl_IndividualPlot,(600,450), self)
        self.szr_PlotActual.Add(self.plt_Reaction, 0, wx.ALL, 5)
        self.szr_ExportPlotImage = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot, u"Clipboard", 0, (130,25))
        self.szr_ExportPlotImage.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportToFile", 5, (104,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveFig, 0, wx.ALL, 5)
        self.btn_SaveAll = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportAll", 0, (100,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveAll, 0, wx.ALL, 5)
        self.szr_PlotActual.Add(self.szr_ExportPlotImage, 0, wx.ALL,5)
        self.szr_Plot.Add(self.szr_PlotActual, 0, wx.ALL)
        # Sizer beside plot
        self.szr_PlotDetails = wx.BoxSizer(wx.VERTICAL)
        self.szr_Res_Display = wx.BoxSizer(wx.VERTICAL)
        self.szr_Res_Display.Add((0, 30), 1, wx.EXPAND, 5)
        # Select what to show
        #self.lbl_Display = wx.StaticText(self.pnl_Results, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.lbl_Display.Wrap(-1)
        #self.szr_Res_Display.Add(self.lbl_Display, 0, wx.ALL, 5)
        #self.rad_Res_Raw = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Raw data", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        #self.szr_Res_Display.Add(self.rad_Res_Raw, 0, wx.ALL, 5)
        #self.rad_Res_Normalised = wx.RadioButton(self.pnl_Results, wx.ID_ANY, u"Normalised data", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        #self.szr_Res_Display.Add(self.rad_Res_Normalised, 0, wx.ALL, 5)
        #self.m_staticline101 = wx.StaticLine(self.pnl_Results, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        #self.szr_Res_Display.Add(self.m_staticline101, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Res_Display, 0, wx.EXPAND, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Fit this data", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Details.Add(self.chk_Fit, 0, wx.ALL, 5)
        self.chk_ManualBoundaries = wx.CheckBox(self.pnl_IndividualPlot, wx.ID_ANY, u"Manually set linear fit interval", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Details.Add(self.chk_ManualBoundaries, 0, wx.ALL, 5)
        self.szr_BoundariesInfo = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_BoundariesInfo.Add((20,0), 0, 0, 5)
        self.lbl_BoundariesInfo = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Click on plot to select bounds of linear fit interval",
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_BoundariesInfo.Wrap(200)
        self.szr_BoundariesInfo.Add(self.lbl_BoundariesInfo, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_BoundariesInfo, 1, wx.EXPAND, 5)
        # LinStart parameter
        self.szr_LinStart = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_LinStart.Add((10, 0), 0, wx.ALL, 5)
        self.lbl_LinStart = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Start:", wx.DefaultPosition, wx.Size(35,-1), 0)
        self.lbl_LinStart.Wrap(-1)
        self.szr_LinStart.Add(self.lbl_LinStart, 0, wx.ALL, 0)
        self.txt_LinStart = wx.TextCtrl(self.pnl_IndividualPlot, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(45,-1), wx.TE_RIGHT)
        self.txt_LinStart.SetMaxLength(4)
        self.szr_LinStart.Add(self.txt_LinStart, 0, wx.ALL, 0)
        self.lbl_LinStartSec = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"s", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_LinStartSec.Wrap(-1)
        self.szr_LinStart.Add(self.lbl_LinStartSec, 0, wx.ALL, 0)
        self.szr_Details.Add(self.szr_LinStart, 0, wx.ALL, 5)
        # LinStop parameter
        self.szr_LinStop = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_LinStop.Add((10, 0), 0, wx.ALL, 5)
        self.lbl_LinStop = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"Stop:", wx.DefaultPosition, wx.Size(35,-1), 0)
        self.lbl_LinStop.Wrap(-1)
        self.szr_LinStop.Add(self.lbl_LinStop, 0, wx.ALL, 0)
        self.txt_LinStop = wx.TextCtrl(self.pnl_IndividualPlot, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(45,-1), wx.TE_RIGHT)
        self.txt_LinStop.SetMaxLength(4)
        self.szr_LinStop.Add(self.txt_LinStop, 0, wx.ALL, 0)
        self.lbl_LinStopSec = wx.StaticText(self.pnl_IndividualPlot, wx.ID_ANY, u"s", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_LinStopSec.Wrap(-1)
        self.szr_LinStop.Add(self.lbl_LinStopSec, 0, wx.ALL, 0)
        self.szr_Details.Add(self.szr_LinStop, 0, wx.ALL, 5)
        # Export buttons
        #self.m_staticline14 = wx.StaticLine(self.pnl_IndividualPlot, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        #self.szr_Details.Add(self.m_staticline14, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Details, 0, wx.EXPAND, 5)
        #self.szr_ExportPlot = wx.BoxSizer(wx.VERTICAL)
        #self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot, u"Clipboard", 0, (130,25))
        #self.szr_ExportPlot.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        #self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportToFile", 0, (104,25))
        #self.btn_SaveFig.SetMaxSize(wx.Size(175,-1))
        #self.szr_ExportPlot.Add(self.btn_SaveFig, 0, wx.ALL, 5)
        #self.btn_SaveAll = CustomBitmapButton(self.pnl_IndividualPlot, u"ExportAll", 0, (100,25))
        #self.szr_ExportPlot.Add(self.btn_SaveAll, 0, wx.ALL, 5)
        #self.szr_PlotDetails.Add(self.szr_ExportPlot, 0, wx.EXPAND, 5)
        self.szr_Plot.Add(self.szr_PlotDetails, 0, wx.EXPAND, 5)
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
        self.plt_MultiPlot = ReactionMultiPlotPanel(self.pnl_MultiPlotPanel,(600,550),self)
        self.szr_MultiPlot.Add(self.plt_MultiPlot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_MultiPlotRight =  wx.BoxSizer(wx.VERTICAL)
        self.szr_MultiPlotRight.Add((0, 30), 0, wx.ALL, 0)
        # Select what to show
        self.szr_MultiPlotShow = wx.FlexGridSizer(2, 2, 0, 0)
        self.lbl_MultiPlotShow = wx.StaticText(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Show", wx.DefaultPosition, wx.DefaultSize, 0)
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_MultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.rad_MultiPlotNorm = wx.RadioButton(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Normalised data", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotNorm, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.rad_MultiPlotRaw = wx.RadioButton(self.pnl_MultiPlotPanel, wx.ID_ANY, u"Raw signal", wx.DefaultPosition, wx.DefaultSize, wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotRaw, 0, wx.ALL, 5)
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
        # Export
        self.szr_ExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_SummaryPlotToClipboard = CustomBitmapButton(self.pnl_MultiPlotPanel, u"Clipboard", 0, (130,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_SummaryPlotToPNG = CustomBitmapButton(self.pnl_MultiPlotPanel, u"ExportToFile", 5, (104,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_ExportMultiPlot, 0, wx.ALL, 0)
        ##########################################################################
        self.szr_MultiPlot.Add(self.szr_MultiPlotRight, 0, wx.EXPAND, 5)
        self.pnl_MultiPlotPanel.SetSizer(self.szr_MultiPlot)
        self.pnl_MultiPlotPanel.Layout()
        self.szr_MultiPlot.Fit(self.pnl_MultiPlotPanel)
        self.sbk_ResultPlots.AddPage(self.pnl_MultiPlotPanel, u"Summary Plot",True)
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

        #self.lst_Headers = ["Protein  Concentration [" + chr(181) + "M]", "Purification ID", "Plate Well ID", "1st compound concentration [" + chr(181) + "M]",
        #    "Buffer ID", "2nd compound ID",    "2nd compound concentration [" + chr(181) + "M]", "Tm value [" + chr(176) + "C]", "Tm Shift [" + chr(176) + "C]",
        #    "Slope at Tm [DI/" + chr(176) + "C]", "ELN ID", "Comments"]
        #self.tab_Export = tab.ExportToDatabase(self.tabs_Analysis.sbk_Notebook, self)
        #self.tabs_Analysis.AddPage(self.tab_Export, u"Export results to Database", False)

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
        ###  # #  # ###  # #  #  ##  #############################################################################

        # Highest level events:
        self.tabs_Analysis.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        # Tab 2: Transfer and Data Files

        # Tab 3: Review Plate
        self.lbc_Plates.Bind(wx.EVT_LIST_ITEM_SELECTED, self.UpdateReviewPlotPanel)
        self.rad_Heatmap.Bind(wx.EVT_RADIOBUTTON, self.RadHeatmap)
        self.rad_ScatterPlot.Bind(wx.EVT_RADIOBUTTON, self.RadScatterplot)
        self.btn_MapToClipboard.Bind(wx.EVT_BUTTON, self.ReviewPlotToClipboard)
        self.btn_SaveMap.Bind(wx.EVT_BUTTON, self.ReviewPlotToPNG)

        # Tab 4: Results
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowCurve)
        self.btn_ExportResultsTable.Bind(wx.EVT_BUTTON, self.ExportResultsTable)
        self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.ToggleFit)
        #self.rad_Res_Normalised.Bind(wx.EVT_RADIOBUTTON, self.RadNormalised)
        #self.rad_Res_Raw.Bind(wx.EVT_RADIOBUTTON, self.RadRaw)
        self.btn_FigToClipboard.Bind(wx.EVT_BUTTON, self.plt_Reaction.PlotToClipboard)
        self.btn_SaveFig.Bind(wx.EVT_BUTTON, self.plt_Reaction.PlotToPNG)
        self.chk_ManualBoundaries.Bind(wx.EVT_CHECKBOX, self.ToggleAutoRate)
        self.btn_SaveAll.Bind(wx.EVT_BUTTON, self.AllPlotsToPNG)

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
        lst_DataFiles = os.listdir(lst_Paths[1])
        # If files have been moved, the original file paths saved in the bbq file are no longer up to date!
        try:
            lst_DataFiles = os.listdir(lst_Paths[1])
        except:
            lst_DataFiles = []
            lst_Paths[0] = "Path not found"
            lst_Paths[1] = "Path not found"
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
        self.str_AssayType = "enzymatic"
        self.str_AssayCategory = "rate"
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
        dfr_Details_New = pd.DataFrame(data={"Value":[self.str_AssayType, self.str_AssayCategory, "RATE", self.str_Purification, self.int_ProteinConc, self.str_PeptideID, self.int_PeptideConc,
            self.str_Solvent, self.int_SolventPercent, self.str_Buffer, self.str_ELN, self.str_AssayVolume, self.str_DatafileExtension, self.SampleSource, self.Device, self.Date]},
            index=["AssayType","AssayCategory","Shorthand","PurificationID","ProteinConcentration","PeptideID","PeptideConcentration","Solvent","SolventConcentration",
            "Buffer","ELN","AssayVolume","DataFileExtension","SampleSource","Device","Date"])

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
        #self.lbc_Plates.Select(0) # This will call UpdateReviewPlotPanel as it is bound to the selection event of the list
        self.lbc_Plates.SetFocus()
        self.bol_ReviewsDrawn = True

    # 3.2 Updating the heatmap
    def UpdateReviewPlotPanel(self,event):
        self.Freeze()
        # Get current selection
        idx_Plate = self.lbc_Plates.GetFirstSelected()
        if self.rad_Heatmap.GetValue() == True:
            which = 0
        else:
            which = 1
        # Get current plate format
        if self.dfr_Details.loc["AssayType","Value"].find("96") != -1:
            int_PlateFormat = 96
        else:
            int_PlateFormat = 384
        # Update heatmap
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],index=range(int_PlateFormat))
        for i in range(int_PlateFormat):
            dfr_Heatmap.loc[i,"Well"] = pf.index_to_well(i+1,int_PlateFormat)
            dfr_Heatmap.loc[i,"Value"] = np.nan
            dfr_Heatmap.loc[i,"SampleID"] = ""
        for i in range(len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])):
            idx_Well = pf.well_to_index(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"Well"],int_PlateFormat)
            dfr_Heatmap.loc[idx_Well,"Value"] = self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[i,"LinFitPars"][0]
            dfr_Heatmap.loc[idx_Well,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
        self.plt_Heatmap.Data = dfr_Heatmap
        self.plt_Heatmap.Title = self.dfr_AssayData.iloc[idx_Plate,0]
        self.plt_Heatmap.Draw()
        # Write dataframe to update scatter plot, then update scatter plot
        dfr_Scatter = pd.DataFrame(columns=["SampleID","Well","Value","ValueSEM"],index=range(len(self.dfr_AssayData.loc[0,"ProcessedDataFrame"])))
        for i in range(len(self.dfr_AssayData.loc[0,"ProcessedDataFrame"])):
            dfr_Scatter.at[i,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[i,"SampleID"]
            dfr_Scatter.at[i,"Well"] = self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[i,"Well"]
            dfr_Scatter.at[i,"Value"] = self.dfr_AssayData.loc[0,"ProcessedDataFrame"].loc[i,"LinFitPars"][0]
            dfr_Scatter.at[i,"ValueSEM"] = 0
        self.pnl_ScatterPlot.Draw(dfr_Scatter,self.dfr_AssayData.iloc[idx_Plate,0],int_PlateFormat)
        # Update detail plot
        self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Well"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"SampleID"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Signal"], 
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"RawFit"],
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"DoFit"])
        self.lbl_DetailRate.SetLabel("Rate: " + df.write_Rate(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"LinFitPars"][0],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"DoLinFit"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"LinFitCI"][0]))
        # Update the simplebook. I tried just running .Update(), that didn"t work.
        if which == 0:
            self.sbk_PlatePlots.SetSelection(1)
            self.sbk_PlatePlots.SetSelection(0)
        else:
            self.sbk_PlatePlots.SetSelection(0)
            self.sbk_PlatePlots.SetSelection(1)
        self.Thaw()

    def UpdateDetailPlot(self, col, row, idx_Sample, int_PlateFormat):
        """
        Takes input from function called by events in plot.
        Needs to be flexible since scatter plot and heatmap plot return different events and thus values:
            i. Scatter plot x axis returns the index in self.dfr_AssayData.iloc[idx_Plate,"ProcessedDataframe"].
                In this case col, row are set to 0.
            ii. Heatmap plot returns col,row coordinates on plate. In thise case idx_Sample is set to -1
        """

        idx_Plate = self.lbc_Plates.GetFirstSelected()

        if idx_Sample == -1:
            int_Columns = pf.plate_columns(int_PlateFormat)
            idx_Well = (col+1) + (int_Columns)*(row)
            str_Well = pf.index_to_well(idx_Well,int_PlateFormat)
            idx_Sample = self.dfr_AssayData.iloc[idx_Plate,5][self.dfr_AssayData.iloc[idx_Plate,5]["Well"] == str_Well].index
            if len(idx_Sample) > 0:
                idx_Sample = idx_Sample[0]
        
        self.pnl_DetailPlot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Signal"], 
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        self.chk_DetailFit.SetValue(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        self.lbl_DetailRate.SetLabel("V: " + df.write_Rate(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoLinFit"],
            self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitCI"][0]))

    # 3.3 Toggle between heatmap and scatter plot
    def TogglePlot(self,event):
        if self.rad_Heatmap.GetValue() == True:
            which = 0
        else:
            which = 1
        self.sbk_PlatePlots.SetSelection(which)

    def RadHeatmap(self, event):
        self.rad_Heatmap.SetValue(True)
        self.rad_ScatterPlot.SetValue(False)
        self.TogglePlot(event)

    def RadScatterplot(self, event):
        self.rad_Heatmap.SetValue(False)
        self.rad_ScatterPlot.SetValue(True)
        self.TogglePlot(event)
        
    # 3.4 Copy plot to clipboard
    def ReviewPlotToClipboard(self,event):
        self.pnl_PlatePlot.PlotToClipboard()

    # 3.5 Save plot to PNG
    def ReviewPlotToPNG(self,event):
        fdlg = wx.FileDialog(self, "Save plot as", wildcard="PNG files(*.png)|*.png", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .png. If so, remove
            if str_SavePath[-1:-4] == ".png":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            self.pnl_PlatePlot.figure.savefig(str_SavePath, dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None,
                transparent=False, bbox_inches=None, pad_inches=0.1)

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
            for idx_Sample in range(len(self.dfr_AssayData.iloc[idx_Plate,5].index)):
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] != "Control":
                    idx_List += 1
                    self.lbc_Samples.InsertItem(idx_List,str(idx_Plate+1))
                    self.lbc_Samples.SetItem(idx_List,1,self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Well"])
                    self.lbc_Samples.SetItem(idx_List,2,self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"])
                    self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],2)))
                    self.lbc_Samples.SetItem(idx_List,4,chr(177))
                    self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitCI"][0],2)))
        self.lbc_Samples.Select(0)
        self.lbc_Samples.SetFocus()

        # Summary graph
        self.plt_MultiPlot.IDs[0] = self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"] 
        self.plt_MultiPlot.SignalTime[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Time"]
        self.plt_MultiPlot.RawSignal[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Signal"]
        self.plt_MultiPlot.RawFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"LinFit"]
        self.plt_MultiPlot.FitTime[0] = self.dfr_AssayData.iloc[0,5].loc[0,"LinFitTime"]
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].Enable(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].SetLabel(self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[0]].Enable(True)
        self.plt_MultiPlot.Draw()

        self.rad_MultiPlotRaw.SetValue(True)
        self.rad_MultiPlotNorm.SetValue(False)

        self.bol_ResultsDrawn = True

    # 4.2 Toggle fit -> change whether a dataset should be fitted or not
    def ToggleFit(self,event):
        self.Freeze()
        # get indices
        idx_ListControl,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] = self.chk_Fit.GetValue()
        if self.chk_Fit.GetValue() == False:
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFitPars"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitPars"]))
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFitPars"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitPars"]))
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"]))
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"]))
            self.lbc_Samples.SetItem(idx_ListControl,3,"N.D.")
            self.lbc_Samples.SetItem(idx_ListControl,4,"")
            self.lbc_Samples.SetItem(idx_ListControl,5,"")
        else:
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_rate(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
            self.lbc_Samples.SetItem(idx_ListControl,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitPars"][0],2)))
            self.lbc_Samples.SetItem(idx_ListControl,4,chr(177))
            self.lbc_Samples.SetItem(idx_ListControl,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitCI"][0],2)))
        #if self.rad_Res_Raw.Value == True:
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
        #else:
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
        self.plt_Reaction.SampleIndex = idx_Sample
        self.plt_Reaction.PlateIndex = idx_Plate
        self.plt_Reaction.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
        self.plt_Reaction.Draw()
        self.txt_LinStart.SetValue(str(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"][self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinStart"]]))
        self.txt_LinStop.SetValue(str(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"][self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinStop"]]))
        self.Thaw()

    def ToggleAutoRate(self, event):
        self.Freeze()
        # Get Value:
        bol_ManualRate = self.chk_ManualBoundaries.GetValue()
        # Enable/Disable detail labels and textboxes:
        self.lbl_BoundariesInfo.Enable(bol_ManualRate)
        self.lbl_LinStart.Enable(bol_ManualRate)
        self.txt_LinStart.Enable(bol_ManualRate)
        self.lbl_LinStartSec.Enable(bol_ManualRate)
        self.lbl_LinStop.Enable(bol_ManualRate)
        self.txt_LinStop.Enable(bol_ManualRate)
        self.lbl_LinStopSec.Enable(bol_ManualRate)
        # Update dataframe:
        idx_ListControl,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"ManualRate"] = bol_ManualRate
        self.Thaw()

    def RadNormalised(self, event):
        if self.rad_Res_Normalised.GetValue() == True:
            self.rad_Res_Raw.SetValue(False)
        else:
            self.rad_Res_Raw.SetValue(True)
        self.ShowCurve(None)

    def RadRaw(self, event):
        if self.rad_Res_Raw.GetValue() == True:
            self.rad_Res_Normalised.SetValue(False)
        else:
            self.rad_Res_Normalised.SetValue(True)
        self.ShowCurve(None)

    # 4.3 Show/Update the displayed curve based on selection on ListCtr
    def ShowCurve(self,event):
        self.Freeze()
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.chk_Fit.SetValue(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"])
        #if self.rad_Res_Raw.Value == True:
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 0
        #else:
        #    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = 1
        self.plt_Reaction.SampleIndex = idx_Sample
        self.plt_Reaction.PlateIndex = idx_Plate
        self.plt_Reaction.Input = self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample]
        self.plt_Reaction.Draw()
        self.txt_LinStart.SetValue(str(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"][self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinStart"]]))
        self.txt_LinStop.SetValue(str(self.dfr_AssayData.iloc[idx_Plate,5].loc[0,"Time"][self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinStop"]]))

        # Get Value:
        bol_ManualRate = self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"ManualRate"]
        # Set tickbox
        self.chk_ManualBoundaries.SetValue(bol_ManualRate)
        # Enable/Disable detail labels and textboxes:
        self.lbl_BoundariesInfo.Enable(bol_ManualRate)
        self.lbl_LinStart.Enable(bol_ManualRate)
        self.txt_LinStart.Enable(bol_ManualRate)
        self.lbl_LinStartSec.Enable(bol_ManualRate)
        self.lbl_LinStop.Enable(bol_ManualRate)
        self.txt_LinStop.Enable(bol_ManualRate)
        self.lbl_LinStopSec.Enable(bol_ManualRate)
        
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
                dfr_ResultsTable.loc[count,"Tm[C]"] = float(self.dfr_AssayData.loc[i,"ProcessedDataFrame"].loc[j,"FitPars"][5])
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
                tempplot = ReactionPlotPanel(self.pnl_Results,(500,400), self)
                tempplot.Draw(self.dfr_AssayData.iloc[idx_Plate,5].iloc[idx_Sample])

                tempplot.figure.savefig(str_SaveDirPath + chr(92) + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] + ".png",
                    dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None, transparent=False, bbox_inches=None, pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_PlotsProgress.gauge.SetValue((count/int_Samples)*200)
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()

    def ColourSelect(self, event):
        idx_Combo = event.GetEventObject().GetSelection()
        self.plt_MultiPlot.Colours[event.GetEventObject().Index] = self.plt_MultiPlot.ColourChoices[idx_Combo]
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()

    def AddGraph(self, event):
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        idx_Graph = event.GetEventObject().Index
        self.plt_MultiPlot.IDs[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
        self.plt_MultiPlot.SignalTime[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Time"]
        self.plt_MultiPlot.RawSignal[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Signal"]
        self.plt_MultiPlot.FitTime[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFitTime"]
        self.plt_MultiPlot.RawFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"LinFit"]

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
            self.plt_MultiPlot.SignalTime[idx_Graph] = []
            self.plt_MultiPlot.RawSignal[idx_Graph] = []
            self.plt_MultiPlot.FitTime[idx_Graph] = []
            self.plt_MultiPlot.RawFit[idx_Graph] = []
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

    def MultiPlotNormalised(self):
        if self.rad_MultiPlotRaw.GetValue() == True:
            return False
        else:
            return True

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
