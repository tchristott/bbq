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
from lib_custombuttons import CustomBitmapButton, IconTabButton

# Import libraries for GUI
import os
import wx
import wx.xrc

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton
from matplotlib.figure import Figure

# Import other libraries
import pandas as pd
import numpy as np
import threading
from datetime import datetime

##############################################################################
##                                                                          ##
##    ##   #####  ######  ######          #####   ##       ####   ######    ##
##    ##  ##      ##      ##  ##          ##  ##  ##      ##  ##    ##      ##
##    ##  ##      #####   ##  ##  ######  #####   ##      ##  ##    ##      ##
##    ##  ##          ##  ##  ##          ##      ##      ##  ##    ##      ##
##    ##   ####   #####   ######          ##      ######   ####     ##      ##
##                                                                          ##
##############################################################################

class CurvePlotPanel(wx.Panel):
    """
        Custom class using wxPython class wx.Panel.
        This holds the plot of datapoints and fitted curve.
        It also included all the functions required to make it an interactive plot, namely
        
        1.    Draw
            Draws the actual plot. Is used everytime data from a new sample is displayed or changes have been made

        2.    CustomToolTip
            Shows a custom "tooltip" that is really a wx.Dialog in disguise as I have not found a way to make the
            Matplotlib tooltips and wxPython play together at all.

        3.    Update
            Sort of a middle man function. It itself is given the entire dataframe for a particular sample and it
            decides which part it hands off to the draw function based on what should be shown (raw data, normalised
            data + free fit, or normalised data + constrained fit)

        4.    OnClick
            Uses the "picker" event to exclude or include datapoints in the fit.

        5.    PlotToClipboard
            self explanatory: Hands the image to the clipboard.

        6.    PlotToPNG
            self explanatory: Saves plot as png.
    
    """

    def __init__(self,parent,PanelSize,tabname,summaryplot = False):
        wx.Panel.__init__(self, parent,size=wx.Size(PanelSize))
        self.tabname = tabname
        self.Top = 1-30/PanelSize[1]
        self.Bottom = 1-(30/PanelSize[1])-(350/PanelSize[1])
        self.figure = Figure(figsize=(PanelSize[0]/100,PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.Confidence = False
        self.Input = None
        self.PlateIndex = None
        self.SampleIndex = None
        self.SummaryPlot = summaryplot
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,virtualonly=False):
        self.SampleID = self.Input["SampleID"]
        # Convert dose to micromoles
        self.DoseMicromolar = df.moles_to_micromoles(self.Input["Concentrations"])
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.11, right=0.99, top=self.Top , bottom=self.Bottom)
        # Actual Plot
        if self.Input["Show"] == 0:
            str_Show = "Raw"
            str_Fit = ""
        elif self.Input["Show"] == 1:
            str_Show = "Norm"
            str_Fit = "Free"
        elif self.Input["Show"] == 2:
            str_Show = "Norm"
            str_Fit = "Const"
        # Get in/excluded points into a list w/o nan, using the dataframe column with nan values produced a runtime warning with current numpy version (date:2022-05-04)!
        lst_IncludedDose, lst_IncludedResponse, lst_IncludedSEM, lst_ExcludedDose, lst_ExcludedResponse, lst_ExcludedSEM = self.IncludeExclude(self.DoseMicromolar, self.Input[str_Show], self.Input[str_Show+"SEM"], self.Input[str_Show+"Excluded"])
        self.dic_Doses = {"Data":lst_IncludedDose,"Excluded":lst_ExcludedDose}
        if len(lst_IncludedDose) > 0:
            self.ax.errorbar(lst_IncludedDose, lst_IncludedResponse, yerr=lst_IncludedSEM, fmt="none", color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.ax.scatter(lst_IncludedDose, lst_IncludedResponse, marker="o", label="Data", color=cs.TMBlue_Hex, picker=5)
        if len(lst_ExcludedDose) > 0:
            self.ax.errorbar(lst_ExcludedDose, lst_ExcludedResponse, yerr=lst_ExcludedSEM, fmt="none", color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.ax.scatter(lst_ExcludedDose, lst_ExcludedResponse, marker="o", label="Excluded", color=cs.WhiteHex, picker=5, edgecolors=cs.TMBlue_Hex, linewidths=0.8)
        if self.Input["DoFit"+str_Fit] == True:
            self.ax.plot(self.DoseMicromolar, self.Input[str_Show+"Fit"+str_Fit], label="Fit", color=cs.TMRose_Hex)
            if self.Confidence == True:
                lst_FitUpper, lst_FitLower = ff.draw_sigmoidal_fit_error(self.Input["Concentrations"],
                    self.Input[str_Show+"Fit"+str_Fit+"Pars"], self.Input[str_Show+"Fit"+str_Fit+"CI"]) # Plot 95%CI of fit
                self.ax.fill_between(self.DoseMicromolar, lst_FitUpper, lst_FitLower, color="red", alpha=0.15)
        self.ax.set_title(self.SampleID)
        self.ax.set_xlabel("Concentration (" + chr(181) +"M)")
        self.ax.set_xscale("log")
        # Set Y axis label and scale according to what's being displayed
        if str_Show == "Norm":
            self.normalised = True
            self.ax.set_ylabel("Per-cent inhibition")
            self.ax.set_ylim([-20,120])
            self.ax.axhline(y=0, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=0
            self.ax.axhline(y=100, xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line at y=100
            self.ax.ticklabel_format(axis="y", style="plain")
        else:
            self.normalised = False
            self.ax.set_ylabel("Signal in AU")
            self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
        self.ax.legend()
        # Test if the summary graph needs to be redrawn, too.
        # Does not apply if the plot is just used virtually for exporting of image file
        if virtualonly == False:
            for i in range(len(self.tabname.plt_MultiPlot.IDs)):
                if self.tabname.plt_MultiPlot.IDs[i] == self.SampleID:
                    self.tabname.plt_MultiPlot.Dose[i] = self.DoseMicromolar
                    self.tabname.plt_MultiPlot.RawPoints[i] = self.Input["Raw"]
                    self.tabname.plt_MultiPlot.RawFit[i] = self.Input["RawFit"]
                    self.tabname.plt_MultiPlot.NormPoints[i] = self.Input["Norm"]
                    if str_Fit == "":
                        self.tabname.plt_MultiPlot.NormFit[i] = self.Input["NormFit"+"Free"]
                    else:
                        self.tabname.plt_MultiPlot.NormFit[i] = self.Input["NormFit"+str_Fit]
                    self.tabname.plt_MultiPlot.Normalised = self.tabname.MultiPlotNormalised()
                    self.tabname.plt_MultiPlot.Draw()
                    break
            # Bind/connect events
            self.canvas.mpl_connect("pick_event", self.ClickOnPoint)
            self.canvas.mpl_connect("button_press_event", self.RightClick)
            self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
            self.canvas.mpl_connect("axes_leave_event", self.DestroyToolTip)
            self.canvas.mpl_connect("figure_leave_event", self.DestroyToolTip)
            self.Bind(wx.EVT_KILL_FOCUS, self.DestroyToolTip)
        # Draw the plot!
        self.canvas.draw()

    def DestroyToolTip(self, event):
        try: self.tltp.Destroy()
        except: None

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
              wx.Dialog dlg_ToolTip gets called. Before each call, the function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within range of a datapoint, the function will also try to
              destroy the dialog. This way, it is ensured that the dialog gets always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            try: self.tltp.Destroy()
            except: None
            # Get coordinates on plot
            x, y = event.xdata, event.ydata
            # Get current sample and retrieve its dataseries
            str_SampleID = self.SampleID
            # Find index of current sample:
            bol_Found = False
            lst_YLimits = self.ax.get_ylim()
            within = (lst_YLimits[1] - lst_YLimits[0])/100 * 2
            if self.normalised == True:
                str_YData = "Norm"
                str_Unit = " " + chr(37)
            else:
                str_YData = "Raw"
                str_Unit = ""
            for i in range(len(self.Input.loc["Concentrations"])):
                # For the x axis (log scale), we have to adjust relative
                if x >= (self.Input.Concentrations[i]*1000000*0.9) and x <= (self.Input.Concentrations[i]*1000000*1.1):
                    # for the y axis, we have to adjust absolute
                    if y >= (self.Input.loc[str_YData][i] - within) and y <= (self.Input.loc[str_YData][i] + within):
                        str_Tooltip = "x: " + str(self.Input.Concentrations[i]) + " M\ny: " + str(self.Input.loc[str_YData][i]) + str_Unit
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        self.SetFocus()
                        break
    
    # Function for clicking on points
    def ClickOnPoint(self, event):
        """
        This function takes the "pick_event" from the matplotlib plot and uses that to exclude or include datapoints in the curve fit.
        - The ID of the sample is saved as a property of the plot
        - Datapoint gets retrieved from the event
        """
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get selected datapoint:
        # Get index of point in picked series
        idx_Picked = event.ind[0]
        # Get picked series:
        flt_PickedConc =  self.dic_Doses[event.artist.get_label()][idx_Picked]
        # Find concentration, if matches, get index of datapoint:
        for idx in range(len(self.DoseMicromolar)):
            if self.DoseMicromolar[idx] == flt_PickedConc:
                idx_datapoint = idx
            
        # Get current sample and retrieve its dataseries

        # exclude datapoint:
        # 1. First write value into lst_RawExcluded/lst_NormExcluded, write np.nan into lst_Raw/lst_Norm
        if np.isnan(self.Input["Raw"][idx_datapoint]) == False:
            # First check if there are enough datapoints left to perform a fit
            counter = 0
            for i in range(len(self.Input["Raw"])):
                if np.isnan(self.Input["Raw"][i]) == False:
                    counter += 1
            if counter > 5:
                # Selected datapoint IS NOT excluded -> copy it into excluded series and set value in data series to nan
                self.Input["RawExcluded"][idx_datapoint] = self.Input["Raw"][idx_datapoint]
                self.Input["Raw"][idx_datapoint] = np.nan
                self.Input["NormExcluded"][idx_datapoint] = self.Input["Norm"][idx_datapoint]
                self.Input["Norm"][idx_datapoint] = np.nan
            else:
                wx.MessageBox("You are trying to remove too many points. Attempting to fit with less than five points will not produce a reliable fit.",
                    "Not enough points left",
                    wx.OK|wx.ICON_INFORMATION)
        else:
            # Selected datapoint IS excluded -> copy it back into data series and set value in excluded series to nan
            self.Input["Raw"][idx_datapoint] = self.Input["RawExcluded"][idx_datapoint]
            self.Input["RawExcluded"][idx_datapoint] = np.nan
            self.Input["Norm"][idx_datapoint] = self.Input["NormExcluded"][idx_datapoint]
            self.Input["NormExcluded"][idx_datapoint] = np.nan
        
        # Check whether a re-fit is required:
        self.Input.at["DoFit"] = df.get_DoFit(self.Input["Norm"],self.Input["NormSEM"])
            
        if self.Input["DoFit"] == True:
            # 3. Re-fit
            self.Input.at["RawFit"], self.Input.at["RawFitPars"], self.Input.at["RawFitCI"], self.Input.at["RawFitErrors"], self.Input.at["RawFitR2"], self.Input.at["DoRawFit"] = ff.fit_sigmoidal_free(self.Input["Concentrations"], self.Input["Raw"])  # only function for constrained needs SEM
            self.Input.at["NormFitFree"], self.Input.at["NormFitFreePars"], self.Input.at["NormFitFreeCI"], self.Input.at["NormFitFreeErrors"], self.Input.at["NormFitFreeR2"], self.Input.at["DoRawFree"] = ff.fit_sigmoidal_free(self.Input["Concentrations"], self.Input["Norm"])
            self.Input.at["NormFitConst"], self.Input.at["NormFitConstPars"], self.Input.at["NormFitConstCI"], self.Input.at["NormFitConstErrors"], self.Input.at["NormFitConstR2"], self.Input.at["DoRawConst"] = ff.fit_sigmoidal_const(self.Input["Concentrations"], self.Input["Norm"], self.Input["NormSEM"])
            if self.Input["DoFitFree"] == False and self.Input["DoFitConst"] == False:
                self.Input.at["DoFit"] = False
        else:
            self.Input.at["RawFit"] = df.set_to_nan(len(self.Input["RawFit"]))
            self.Input.at["RawFitPars"] = df.set_to_nan(4)
            self.Input.at["RawFitR2"] = np.nan
            
            self.Input.at["NormFitFree"] = df.set_to_nan(len(self.Input["NormFitFree"]))
            self.Input.at["NormFitFreePars"] = df.set_to_nan(4)
            self.Input.at["NormFitFreeR2"] = np.nan

            self.Input.at["NormFitConst"] = df.set_to_nan(len(self.Input["NormFitConst"]))
            self.Input.at["NormFitConstPars"] = df.set_to_nan(4)
            self.Input.at["NormFitConstR2"] = np.nan

            self.Input.at["NormFitFreeCI"], self.Input.at["NormFitConstCI"], self.Input["RawFitCI"] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
            self.Input.at["NormFitFreeErrors"], self.Input.at["NormFitConstErrors"], self.Input["RawFitErrors"] = df.set_to_nan(4), df.set_to_nan(4), df.set_to_nan(4)
        
        # Redraw graph
        self.Draw()
        # 2. Push dfr_Sample back to CompleteContainer
        self.tabname.dfr_AssayData.at[self.PlateIndex,"ProcessedDataFrame"].loc[self.SampleIndex] = self.Input
        self.tabname.UpdateDetails(self.Input, self.Input["Show"])
        self.tabname.UpdateSampleReporting(None)

    def IncludeExclude(self, lst_Dose, lst_Response, lst_SEM, lst_ResponseExcluded):

        lst_ResponseAll = []
        for idx in range(len(lst_Response)):
            if not pd.isna(lst_Response[idx]) == True:
                lst_ResponseAll.append(lst_Response[idx])
            else:
                lst_ResponseAll.append(lst_ResponseExcluded[idx])

        lst_DoseIncluded = []
        lst_ResponseIncluded = []
        lst_SEMIncluded = []
        lst_DoseExcluded = []
        lst_ResponseExcluded = []
        lst_SEMExcluded = []
        for point in range(len(lst_Response)):
            if not pd.isna(lst_Response[point]) == True:
                lst_DoseIncluded.append(lst_Dose[point])
                lst_ResponseIncluded.append(lst_ResponseAll[point])
                lst_SEMIncluded.append(lst_SEM[point])
            else:
                lst_DoseExcluded.append(lst_Dose[point])
                lst_ResponseExcluded.append(lst_ResponseAll[point])
                lst_SEMExcluded.append(lst_SEM[point])

        return lst_DoseIncluded, lst_ResponseIncluded, lst_SEMIncluded, lst_DoseExcluded, lst_ResponseExcluded, lst_SEMExcluded    

    def PlotToClipboard(self,event):
        cp.shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        cp.shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        pd.DataFrame({"Concentration[uM]":self.Input["Concentrations"],"NormalisedMean":self.Input["Norm"],"NormalisedSEM":self.Input["NormSEM"],
            "FreeFit":self.Input["NormFitFree"],"ConstrainedFit":self.Input["NormFitConst"]}).to_clipboard(header=True, index=False)

########################################################################################
##                                                                                    ##
##    ##    ##  ##  ##  ##      ######  ##          #####   ##       ####   ######    ##
##    ###  ###  ##  ##  ##        ##    ##          ##  ##  ##      ##  ##    ##      ##
##    ########  ##  ##  ##        ##    ##  ######  #####   ##      ##  ##    ##      ##
##    ## ## ##  ##  ##  ##        ##    ##          ##      ##      ##  ##    ##      ##
##    ##    ##   ####   ######    ##    ##          ##      ######   ####     ##      ##
##                                                                                    ##
########################################################################################

class DoseMultiPlotPanel(wx.Panel):
    """
    Custom panel based on matplotlib and wx.Panel to display multiple
    plots on the same graph with UI control outside this panel.
    """
    def __init__(self,parent,PanelSize,tabname,summaryplot = False):
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
        # Store up to 8 data sets in the instance
        self.Dose = [[],[],[],[],[],[],[],[]]
        self.IDs = ["","","","","","","",""]
        self.RawPoints = [[],[],[],[],[],[],[],[]]
        self.RawSEM = [[],[],[],[],[],[],[],[]]
        self.RawExcluded = [[],[],[],[],[],[],[],[]]
        self.RawFit = [[],[],[],[],[],[],[],[]]
        self.NormPoints = [[],[],[],[],[],[],[],[]]
        self.NormSEM = [[],[],[],[],[],[],[],[]]
        self.NormExcluded = [[],[],[],[],[],[],[],[]]
        self.NormFit = [[],[],[],[],[],[],[],[]]
        self.Preview = True
        self.PreviewDose = []
        self.PreviewID = ""
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
        self.Colours = [cs.TMIndigo_RGBA, cs.TMBlue_RGBA, cs.TMCyan_RGBA, cs.TMTeal_RGBA,
                        cs.TMGreen_RGBA, cs.TMOlive_RGBA, cs.TMSand_RGBA, cs.TMRose_RGBA,
                        cs.TMWine_RGBA, cs.TMPurple_RGBA]
        self.Normalised = True
        self.SummaryPlot = summaryplot
        self.SetSizer(self.szr_Canvas)
        self.Fit()

    def Draw(self):
        """
        Sets properties of actual matplotlb from class attributes
        and then (re)draws the plot.
        """
        self.Freeze()
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left = 0.11, 
                                    right = 0.99,
                                    top = self.Top,
                                    bottom = self.Bottom)
        # Actual Plot: Normalisation useful for comparison graph!
        if self.Normalised == True:
            self.ax.set_ylabel("Per-cent inhibition")
            self.ax.set_ylim([-20,120])
            # Horizontal lines at y=0 and y=100
            self.ax.axhline(y = 0, xmin = 0, xmax = 1, linestyle = "--",
                            color = "grey", linewidth = 0.5)
            self.ax.axhline(y = 100, xmin = 0, xmax = 1, linestyle = "--",
                            color="grey", linewidth=0.5)
            self.ax.ticklabel_format(axis="y", style="plain")
            for i in range(len(self.IDs)):
                if self.IDs[i] != "":
                    lst_IncludedDose, lst_IncludedResponse, lst_IncludedSEM, lst_ExcludedDose, lst_ExcludedResponse, lst_ExcludedSEM = self.IncludeExclude(self.Dose[i], self.NormPoints[i], self.NormSEM[i], self.NormExcluded[i])
                    self.ax.scatter(lst_IncludedDose, lst_IncludedResponse,
                                    label = self.IDs[i], marker = "o", color = self.Colours[i])
                    if self.ErrorBars == True:
                        self.ax.errorbar(lst_IncludedDose, lst_IncludedResponse,
                                         yerr = lst_IncludedSEM, fmt = "none",
                                         color = self.Colours[i], elinewidth = 0.3,
                                         capsize = 2)
                    if self.ExcludedPoints == True and len(lst_ExcludedResponse) > 0:
                        self.ax.scatter(lst_ExcludedDose, lst_ExcludedResponse,
                                        marker = "o", color = "#FFFFFF",
                                        edgecolors = self.Colours[i], linewidths = 0.8)
                        if self.ErrorBars == True:
                            self.ax.errorbar(lst_ExcludedDose, lst_ExcludedResponse,
                                             yerr = lst_ExcludedSEM, fmt = "none",
                                             color = self.Colours[i], elinewidth = 0.3,
                                             capsize=2)
                    self.ax.plot(self.Dose[i], self.NormFit[i], color=self.Colours[i])
            if self.Preview == True and not self.PreviewID in self.IDs:
                lst_PrevDoseInc, lst_PrevRespInc, lst_PrevSEMInc, lst_PrevDoseExcl, lst_PrevRespExcl, lst_PrevSEMExcl = self.IncludeExclude(self.PreviewDose, self.PreviewNormPoints, self.PreviewNormSEM, self.PreviewNormExcluded)
                self.ax.scatter(lst_PrevDoseInc, lst_PrevRespInc,
                                label = self.PreviewID, marker = "o",
                                color = cs.TMPaleGrey_RGBA)
                if self.ErrorBars == True:
                    self.ax.errorbar(lst_PrevDoseInc, lst_PrevRespInc,
                                     yerr = lst_PrevSEMInc, fmt = "none",
                                     color = cs.TMPaleGrey_RGBA,
                                     elinewidth = 0.3, capsize = 2)
                if self.ExcludedPoints == True and len(lst_PrevDoseInc) > 0:
                    self.ax.scatter(lst_PrevDoseExcl, lst_PrevRespExcl, marker = "o",
                                    color = "#FFFFFF", edgecolors = cs.TMPaleGrey_RGBA,
                                    linewidths = 0.8)
                    if self.ErrorBars == True:
                        self.ax.errorbar(lst_PrevDoseExcl, lst_PrevRespExcl, yerr=lst_PrevSEMExcl, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                self.ax.plot(self.PreviewDose, self.PreviewNormFit, color=cs.TMPaleGrey_RGBA)
        else:
            for i in range(len(self.IDs)):
                self.ax.set_ylabel("Signal in AU")
                self.ax.ticklabel_format(axis = "y", style = "scientific",
                                         scilimits = (-1,1))
                if self.IDs[i] != "":
                    lst_InclDose, lst_InclRes, lst_InclSEM, lst_ExclDose, lst_ExclResp, lst_ExclSEM = self.IncludeExclude(self.Dose[i], self.RawPoints[i], self.RawSEM[i], self.RawExcluded[i])
                    self.ax.scatter(lst_InclDose, lst_InclRes,
                                    label = self.IDs[i], marker = "o",
                                    color = self.Colours[i])
                    if self.ErrorBars == True:
                        self.ax.errorbar(lst_InclDose, lst_InclRes, yerr = lst_InclSEM,
                                         fmt = "none", color = self.Colours[i],
                                         elinewidth = 0.3, capsize = 2)
                    if self.ExcludedPoints == True and df.any_nonnan(self.RawExcluded[i]) == True:
                        self.ax.scatter(lst_ExclDose, lst_ExclResp,
                                        marker = "o", color = "#FFFFFF",
                                        edgecolors = self.Colours[i], linewidths = 0.8)
                        if self.ErrorBars == True:
                            self.ax.errorbar(lst_ExclDose, lst_ExclResp,
                                             yerr = lst_ExclSEM, fmt = "none",
                                             color = self.Colours[i], elinewidth = 0.3,
                                             capsize = 2)
                    self.ax.plot(self.Dose[i], self.RawFit[i], color=self.Colours[i])
            if self.Preview == True and not self.PreviewID in self.IDs:
                if self.Preview == True and not self.PreviewID in self.IDs:
                    lst_PreviewDoseIncluded, lst_PreviewResponseIncluded, lst_PreviewSEMIncluded, lst_PreviewDoseExcluded, lst_PreviewResponseExcluded, lst_PreviewSEMExcluded = self.IncludeExclude(self.PreviewDose, self.PreviewRawPoints, self.PreviewRawSEM, self.PreviewRawExcluded)
                    self.ax.scatter(lst_PreviewDoseIncluded, lst_PreviewResponseIncluded,
                                    label=self.PreviewID, marker="o", color=cs.TMPaleGrey_RGBA)
                    if self.ErrorBars == True:
                        self.ax.errorbar(lst_PreviewDoseIncluded, lst_PreviewResponseIncluded,
                                         yerr = lst_PreviewSEMIncluded, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                    if self.ExcludedPoints == True and len(lst_PreviewDoseIncluded) > 0:
                        self.ax.scatter(lst_PreviewDoseExcluded, lst_PreviewResponseExcluded, marker="o", color="#FFFFFF", edgecolors=cs.TMPaleGrey_RGBA, linewidths=0.8)
                        if self.ErrorBars == True:
                            self.ax.errorbar(lst_PreviewDoseExcluded, lst_PreviewResponseExcluded, yerr=lst_PreviewSEMExcluded, fmt="none", color=cs.TMPaleGrey_RGBA, elinewidth=0.3, capsize=2)
                self.ax.plot(self.PreviewDose, self.PreviewRawFit, color=cs.TMPaleGrey_RGBA)

        self.ax.set_xlabel("Concentration (" + chr(181) +"M)")
        self.ax.set_xscale("log")
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
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("axes_leave_event", self.DestroyToolTip)
        self.canvas.draw()
        self.Thaw()

    def IncludeExclude(self, doses, response, sem, response_excl):

        # Ensure we have a list of ALL responses, included or excluded
        response_all = []
        for idx in range(len(response)):
            if not pd.isna(response[idx]) == True:
                response_all.append(response[idx])
            else:
                response_all.append(response_excl[idx])

        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for point in range(len(response)):
            if not pd.isna(response[point]) == True:
                dose_incl.append(doses[point])
                resp_incl.append(response_all[point])
                sem_incl.append(sem[point])
            else:
                dose_excl.append(doses[point])
                resp_excl.append(response_all[point])
                sem_excl.append(sem[point])

        return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl   


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
    """
    Small dialog window to change source concentration of samples
    to recalculate assay concentrations (e.g. if liquid handler
    only accepts one source concentration and actual concentrations
    have to be recalculated)
    """

    def __init__(self, parent, str_CurrentConc):
        wx.Dialog.__init__ (self, parent, id = wx.ID_ANY,
                            title = u"Change source concentration",
                            pos = wx.DefaultPosition,
                            size = wx.DefaultSize,
                            style = wx.STAY_ON_TOP)
        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.parent = parent

        self.szr_Main = wx.BoxSizer(wx.VERTICAL)

        self.szr_Concentration = wx.BoxSizer(wx.HORIZONTAL)

        self.lbl_Concentration = wx.StaticText(self, label = u"Source concentration:")
        self.lbl_Concentration.Wrap(-1)
        self.szr_Concentration.Add(self.lbl_Concentration, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.txt_Concentration = wx.TextCtrl(self, size = wx.Size(50,-1),
                                             style = wx.TE_NO_VSCROLL|wx.TE_PROCESS_ENTER)
        self.txt_Concentration.SetValue(str_CurrentConc)
        self.szr_Concentration.Add(self.txt_Concentration, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.lbl_Unit = wx.StaticText(self, label = u"mM")
        self.lbl_Unit.Wrap(-1)
        self.szr_Concentration.Add(self.lbl_Unit, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.szr_Main.Add(self.szr_Concentration, 1, wx.EXPAND, 5)

        self.szr_Buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.btn_Cancel = wx.Button(self, label = u"Cancel")
        self.szr_Buttons.Add(self.btn_Cancel, 0, wx.ALL, 5)

        self.btn_Update = wx.Button(self, label = u"Update")
        self.szr_Buttons.Add(self.btn_Update, 0, wx.ALL, 5)

        self.szr_Main.Add(self.szr_Buttons, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(self.szr_Main)
        self.Layout()
        self.szr_Main.Fit(self)

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
        """
        Event handler. Removes any input other than numerical and
        periods.
        """
        str_Text = self.txt_Concentration.GetValue()
        str_LastChar = str_Text[-1::]
        int_LenText = len(str_Text)
        if len(str_LastChar) != 0:
            if str_LastChar.isalpha() == True and str_LastChar != ".":
                str_Text = str_Text[0:int_LenText-1]
                self.txt_Concentration.write(str_Text)
                
    def OnCancel(self,event):
        """
        Event handler. Sets parent object's str_NewConc to None
        and closes dialog and returns False.
        """
        self.parent.str_NewConc = None
        self.EndModal(False)
        self.Destroy()

    def OnUpdate(self,event):
        """
        Event handler. Updates parent object with new stock
        concentration and returns True to trigger recalculation
        of assay concentrations.
        """
        str_NewConc = self.txt_Concentration.GetValue()
        if str_NewConc.find(".",0,len(str_NewConc)) == -1:
            str_NewConc = str_NewConc + ".0"
        self.parent.str_NewConc = str_NewConc
        self.EndModal(True)
        self.Destroy()

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
        wx.Panel.__init__ (self, parent.sbk_WorkArea,
                           id = wx.ID_ANY,
                           pos = wx.DefaultPosition,
                           size = wx.Size(1000,750),
                           style = wx.TAB_TRAVERSAL,
                           name = "pnl_Project")

        self.SetBackgroundColour(cs.BgUltraLight)
        clr_Tabs = cs.BgUltraLight
        clr_Panels = cs.BgLight
        clr_TextBoxes = cs.BgUltraLight

        self.parent = parent

        # Initialise instance wide variables with default values
        self.Title = u"Dose response/IC50 project"
        self.Index = None
        self.int_Samples = np.nan
        self.str_AssayCategory = "dose_response"
        self.str_Shorthand = "EPDR"
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

        self.str_NewConc = None

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
        #  # ###  ###  #  #   #      ###  ####   #   #  # # #### ###  ###################

        lst_AssayTypes = [u"HTRF", u"AlphaScreen", u"TAMRA FP", u"ADP-Glo",
                          u"AMP-Glo", u"UDP-Glo", u"UMP-Glo"]
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
          #   #  # #  # #  # ###  #    #### #  # #   ###  #  #   #   #  # ###############

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
        #  # ####   #   # ####   # # #      #    #### #  #   #   #### ###  ##############

        self.tab_Review = tab.Review(self.tabs_Analysis.sbk_Notebook, tabname = self,
                                     assaycategory = self.str_Shorthand,
                                     plots = ["Heat Map"], sidebar = [""])
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

        # Sample List
        self.szr_SampleList = wx.BoxSizer(wx.VERTICAL)
        self.lbl_SelectSample = wx.StaticText(self.tab_Results, label = u"Select a sample")
        self.lbl_SelectSample.Wrap(-1)
        self.szr_SampleList.Add(self.lbl_SelectSample, 0, wx.ALL, 5)
        self.lbc_Samples = wx.ListCtrl(self.tab_Results, size = wx.Size(330,-1),
                                       style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.lbc_Samples.SetBackgroundColour(clr_TextBoxes)
        self.lbc_Samples.InsertColumn(0,"Plate")
        self.lbc_Samples.SetColumnWidth(0,40)
        self.lbc_Samples.InsertColumn(1,"SampleID")
        self.lbc_Samples.SetColumnWidth(1,90)
        self.lbc_Samples.InsertColumn(2,"SrcConc[mM]")
        self.lbc_Samples.SetColumnWidth(2,90)
        self.lbc_Samples.InsertColumn(3,"IC50")
        self.lbc_Samples.SetColumnWidth(3,35)
        self.lbc_Samples.InsertColumn(4,"")
        self.lbc_Samples.SetColumnWidth(4,20)
        self.lbc_Samples.InsertColumn(5,"")
        self.lbc_Samples.SetColumnWidth(5,35)
        self.szr_SampleList.Add(self.lbc_Samples, 1, wx.ALL|wx.EXPAND, 5)
        # Button to export results table
        self.btn_ExportResultsTable = CustomBitmapButton(self.tab_Results,
                                                         type = u"ExportToFile",
                                                         index = 5,
                                                         size = (104,25))
        self.szr_SampleList.Add(self.btn_ExportResultsTable, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.bSizer12.Add(self.szr_SampleList, 0, wx.EXPAND, 5)

        # Sizer for plot and plot export buttons
        self.szr_SimpleBook = wx.BoxSizer(wx.VERTICAL)
        self.szr_SimpleBookTabs = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_IndividualPlot = IconTabButton(self.tab_Results, u"Individual Plot", 0, self.AssayPath)
        self.btn_IndividualPlot.IsCurrent(True)
        self.szr_SimpleBookTabs.Add(self.btn_IndividualPlot, 0, wx.ALL,0)
        self.szr_SimpleBookTabs.Add((5,0), 0, wx.ALL,0)
        self.btn_SummaryPlot = IconTabButton(self.tab_Results, u"Summary Plot", 1, self.AssayPath)
        self.btn_SummaryPlot.IsEnabled(True)
        self.szr_SimpleBookTabs.Add(self.btn_SummaryPlot, 0, wx.ALL, 0)
        self.dic_PlotTabButtons = {0:self.btn_IndividualPlot,1:self.btn_SummaryPlot}
        self.szr_SimpleBook.Add(self.szr_SimpleBookTabs, 0, wx.ALL, 0)
        self.sbk_ResultPlots = wx.Simplebook(self.tab_Results, size = wx.Size(900,550))
        self.btn_IndividualPlot.Notebook = self.sbk_ResultPlots
        self.btn_IndividualPlot.Group = self.dic_PlotTabButtons
        self.btn_SummaryPlot.Notebook = self.sbk_ResultPlots
        self.btn_SummaryPlot.Group = self.dic_PlotTabButtons

        # First page in simplebook: Resultsplot =========================================
        self.pnl_IndividualPlot = wx.Panel(self.sbk_ResultPlots, size = wx.Size(900,550),
                                           style = wx.TAB_TRAVERSAL)
        self.pnl_IndividualPlot.SetBackgroundColour(clr_Tabs)
        self.szr_Plot = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_PlotActual = wx.BoxSizer(wx.VERTICAL)
        self.plt_DoseResponse = cp.CurvePlotPanel(self.pnl_IndividualPlot, (600,450), self)
        self.szr_PlotActual.Add(self.plt_DoseResponse, 0, wx.ALL, 5)
        self.szr_ExportPlotImage = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_FigToClipboard = CustomBitmapButton(self.pnl_IndividualPlot,
                                                     type = u"Clipboard",
                                                     index = 0,
                                                     size = (130,25))
        self.szr_ExportPlotImage.Add(self.btn_FigToClipboard, 0, wx.ALL, 5)
        self.btn_SaveFig = CustomBitmapButton(self.pnl_IndividualPlot,
                                              type = u"ExportToFile",
                                              index = 0,
                                              size = (104,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveFig, 0, wx.ALL, 5)
        self.btn_SaveAll = CustomBitmapButton(self.pnl_IndividualPlot,
                                              type = u"ExportAll",
                                              index = 0,
                                              size = (100,25))
        self.szr_ExportPlotImage.Add(self.btn_SaveAll, 0, wx.ALL, 5)
        self.szr_PlotActual.Add(self.szr_ExportPlotImage, 0, wx.ALL,5)
        self.szr_Plot.Add(self.szr_PlotActual, 0, wx.ALL)
        # Sizer beside plot
        self.szr_PlotDetails = wx.BoxSizer(wx.VERTICAL)
        # Select what to show
        self.szr_Res_Display = wx.BoxSizer(wx.VERTICAL)
        self.szr_Res_Display.Add((0, 30), 1, wx.EXPAND, 5)
        self.lbl_Display = wx.StaticText(self.pnl_IndividualPlot, label = u"Show")
        self.lbl_Display.Wrap(-1)
        self.szr_Res_Display.Add(self.lbl_Display, 0, wx.ALL, 5)
        self.rad_Res_NormFree = wx.RadioButton(self.pnl_IndividualPlot,
                                               label = u"Normalised data (free fit)",
                                               style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormFree, 0, wx.ALL, 5)
        self.rad_Res_NormConst = wx.RadioButton(self.pnl_IndividualPlot, 
                                                label = u"Normalised data (constrained fit)",
                                                style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_NormConst, 0, wx.ALL, 5)
        self.rad_Res_Raw = wx.RadioButton(self.pnl_IndividualPlot,
                                          label = u"Raw signal",
                                          style = wx.RB_SINGLE)
        self.szr_Res_Display.Add(self.rad_Res_Raw, 0, wx.ALL, 5)
        self.chk_Confidence = wx.CheckBox(self.pnl_IndividualPlot, 
                                          label = u"Show confidence interval")
        self.szr_Res_Display.Add(self.chk_Confidence, 0, wx.ALL, 5)
        self.m_staticline101 = wx.StaticLine(self.pnl_IndividualPlot,
                                             style = wx.LI_HORIZONTAL)
        self.szr_Res_Display.Add(self.m_staticline101, 0, wx.EXPAND|wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Res_Display, 0, wx.EXPAND, 5)
        # Details (fit plot? Parameters?)
        self.szr_Details = wx.BoxSizer(wx.VERTICAL)
        self.szr_Fit = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_Fit = wx.CheckBox(self.pnl_IndividualPlot, label= u"Fit this data")
        self.szr_Fit.Add(self.chk_Fit,0,wx.ALL,0)
        self.btn_FitToolTip = CustomBitmapButton(self.pnl_IndividualPlot,
                                                 type = u"InfoUltraLight",
                                                 index = 0,
                                                 size = (15,15),
                                                 tooltip=u"How is the curve fit calculated?")
        self.btn_FitToolTip.ImagePath = os.path.join(self.parent.str_OtherPath,
                                                     "SigmoidalDoseResponseToolTip.png")
        self.szr_Fit.Add(self.btn_FitToolTip,0,wx.ALL,0)
        self.szr_Details.Add(self.szr_Fit, 0, wx.ALL, 5)
        self.szr_Parameters = wx.FlexGridSizer(6, 2, 0, 0)
        # Parameters
        self.lbl_ICLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"IC50:")
        self.lbl_ICLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_ICLabel, 0, wx.ALL, 5)
        self.lbl_IC = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_IC.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_IC, 0, wx.ALL, 5)
        # Slope
        self.lbl_SlopeLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Slope:")
        self.lbl_SlopeLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_SlopeLabel, 0, wx.ALL, 5)
        self.lbl_Slope = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Slope.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Slope, 0, wx.ALL, 5)
        # Top
        self.lbl_TopLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Top:")
        self.lbl_TopLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_TopLabel, 0, wx.ALL, 5)
        self.lbl_Top = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Top.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Top, 0, wx.ALL, 5)
        # Bottom
        self.lbl_BottomLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Bottom:")
        self.lbl_BottomLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_BottomLabel, 0, wx.ALL, 5)
        self.lbl_Bottom = wx.StaticText(self.pnl_IndividualPlot,label = u"TBA")
        self.lbl_Bottom.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Bottom, 0, wx.ALL, 5)
        # Span
        self.lbl_SpanLabel = wx.StaticText(self.pnl_IndividualPlot, label = u"Span:")
        self.lbl_SpanLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_SpanLabel, 0, wx.ALL, 5)
        self.lbl_Span = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_Span.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_Span, 0, wx.ALL, 5)
        # RSquare
        self.lbl_RSquareLabel = wx.StaticText(self.pnl_IndividualPlot,
                                              label = u"R" + chr(178) + u":")
        self.lbl_RSquareLabel.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_RSquareLabel, 0, wx.ALL, 5)
        self.lbl_RSquare = wx.StaticText(self.pnl_IndividualPlot, label = u"TBA")
        self.lbl_RSquare.Wrap(-1)
        self.szr_Parameters.Add(self.lbl_RSquare, 0, wx.ALL, 5)
        self.szr_Details.Add(self.szr_Parameters, 0, wx.ALL, 5)
        # Separator line
        self.m_staticline14 = wx.StaticLine(self.pnl_IndividualPlot,
                                            style = wx.LI_HORIZONTAL)
        self.szr_Details.Add(self.m_staticline14, 0, wx.EXPAND |wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_Details, 0, wx.EXPAND, 5)
        # Sizer with buttons for copying/exporting 
        self.szr_CopyCurveParameters = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_CopyCurveParameters = CustomBitmapButton(self.pnl_IndividualPlot,
                                                          type = u"Clipboard",
                                                          index = 0,
                                                          size = (130,25))
        self.szr_CopyCurveParameters.Add(self.btn_CopyCurveParameters, 0, wx.ALL, 5)
        self.szr_PlotDetails.Add(self.szr_CopyCurveParameters, 1, wx.ALIGN_RIGHT, 5)
        # Finish first page
        self.szr_Plot.Add(self.szr_PlotDetails, 0, wx.EXPAND, 5)
        self.pnl_IndividualPlot.SetSizer(self.szr_Plot)
        self.pnl_IndividualPlot.Layout()
        self.szr_Plot.Fit(self.pnl_IndividualPlot)
        self.sbk_ResultPlots.AddPage(self.pnl_IndividualPlot, u"Individual Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # ===============================================================================
        
        # Second page in sbk_ResultPlots: Multiplot =====================================
        self.pnl_MultiPlotPanel = wx.Panel(self.sbk_ResultPlots, size = wx.Size(900,550),
                                           style = wx.TAB_TRAVERSAL)
        self.pnl_MultiPlotPanel.SetBackgroundColour(clr_Tabs)
        self.szr_MultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.plt_MultiPlot = DoseMultiPlotPanel(self.pnl_MultiPlotPanel,
                                                PanelSize = (600,550),
                                                tabname = self,
                                                summaryplot=True)
        self.szr_MultiPlot.Add(self.plt_MultiPlot, 0, wx.ALL, 5)
        # Sizer beside plot
        self.szr_MultiPlotRight =  wx.BoxSizer(wx.VERTICAL)
        self.szr_MultiPlotRight.Add((0, 30), 0, wx.ALL, 0)
        # Select what to show
        self.szr_MultiPlotShow = wx.FlexGridSizer(4, 2, 0, 0)
        self.lbl_MultiPlotShow = wx.StaticText(self.pnl_MultiPlotPanel, label = u"Show")
        self.lbl_MultiPlotShow.Wrap(-1)
        self.szr_MultiPlotShow.Add(self.lbl_MultiPlotShow, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.rad_MultiPlotNorm = wx.RadioButton(self.pnl_MultiPlotPanel,
                                                label = u"Normalised data",
                                                style = wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotNorm, 0, wx.ALL, 5)
        self.chk_ErrorBars = wx.CheckBox(self.pnl_MultiPlotPanel, label = u"Error bars")
        self.szr_MultiPlotShow.Add(self.chk_ErrorBars, 0, wx.ALL, 5)
        self.rad_MultiPlotRaw = wx.RadioButton(self.pnl_MultiPlotPanel,
                                               label = u"Raw signal",
                                               style = wx.RB_SINGLE)
        self.szr_MultiPlotShow.Add(self.rad_MultiPlotRaw, 0, wx.ALL, 5)
        self.chk_ExcludedPoints = wx.CheckBox(self.pnl_MultiPlotPanel, 
                                              label = u"Excluded points")
        self.szr_MultiPlotShow.Add(self.chk_ExcludedPoints, 0, wx.ALL, 5)
        self.szr_MultiPlotShow.Add((-1,-1), 0, wx.ALL, 5)
        self.chk_PreviewPlot = wx.CheckBox(self.pnl_MultiPlotPanel,
                                           label = u"Preview selected sample")
        self.chk_PreviewPlot.SetValue(True) 
        self.szr_MultiPlotShow.Add(self.chk_PreviewPlot, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotShow, 0, wx.EXPAND, 5)
        # Separator line
        self.lin_MultiPlotShow = wx.StaticLine(self.pnl_MultiPlotPanel, 
                                               style = wx.LI_HORIZONTAL)
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
        self.lbl_Column1 = wx.StaticText(self.pnl_MultiPlotPanel,
                                         label = u"Sample ID/Name")
        self.lbl_Column1.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column1, 0, wx.ALL, 3)
        self.lbl_Column2 = wx.StaticText(self.pnl_MultiPlotPanel, label = u"Colour")
        self.lbl_Column2.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column2, 0, wx.ALL, 3)
        self.lbl_Column3 = wx.StaticText(self.pnl_MultiPlotPanel, label = u" ")
        self.lbl_Column3.Wrap(-1)
        self.szr_MultiPlotList.Add(self.lbl_Column3, 0, wx.ALL, 3)
        self.lbl_Comlumn4 = wx.StaticText(self.pnl_MultiPlotPanel, label = u" ")
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
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]] = wx.StaticText(
                                                                self.pnl_MultiPlotPanel,
                                                                label = u"no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Wrap(-1)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]].Enable(False)
            self.szr_MultiPlotList.Add(self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[i]],
                                       0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 3)
            # BitmapCombo
            self.lst_BitmapCombos.append("self.bmc_Sample" + str(i))
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]] = wx.adv.BitmapComboBox(
                                                                self.pnl_MultiPlotPanel,
                                                                value = u"Combo!",
                                                                size = wx.Size(100,25),
                                                                choices = self.lst_ColourOptions,
                                                                style = wx.CB_READONLY)
            for j in range(len(self.lst_ColourBitmaps)):
                self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetItemBitmap(j,self.lst_ColourBitmaps[j])
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].SetSelection(i)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Index = i
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Enable(False)
            self.dic_BitmapCombos[self.lst_BitmapCombos[i]].Bind(wx.EVT_COMBOBOX,
                                                                 self.ColourSelect)
            self.szr_MultiPlotList.Add(self.dic_BitmapCombos[self.lst_BitmapCombos[i]], 0, wx.ALL, 3)
            # "Add" button
            self.lst_AddButtons.append("self.btn_Add" + str(i))
            self.dic_AddButtons[self.lst_AddButtons[i]] = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                                             type = u"Plus",
                                                                             index = 0,
                                                                             size = (25,25))
            self.dic_AddButtons[self.lst_AddButtons[i]].Index = i
            self.dic_AddButtons[self.lst_AddButtons[i]].Bind(wx.EVT_BUTTON, self.AddGraph)
            self.szr_MultiPlotList.Add(self.dic_AddButtons[self.lst_AddButtons[i]], 0, wx.ALL, 3)
            # "Remove" button
            self.lst_RemoveButtons.append("self.btn_Add" + str(i))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]] = CustomBitmapButton(
                                                                    self.pnl_MultiPlotPanel,
                                                                    type = u"Minus",
                                                                    index = 0,
                                                                    size = (25,25))
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Index = i
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[i]].Bind(wx.EVT_BUTTON,
                                                                   self.RemoveGraph)
            self.szr_MultiPlotList.Add(self.dic_RemoveButtons[self.lst_RemoveButtons[i]], 0, wx.ALL, 3)
        self.szr_MultiPlotRight.Add(self.szr_MultiPlotList, 0, wx.ALL, 5)
        # Separator line
        self.lin_MultiPlotRight = wx.StaticLine(self.pnl_MultiPlotPanel,
                                                style = wx.LI_HORIZONTAL)
        self.szr_MultiPlotRight.Add(self.lin_MultiPlotRight, 0, wx.EXPAND|wx.ALL, 5)
        # Export
        self.szr_ExportMultiPlot = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_SummaryPlotToClipboard = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                             type = u"Clipboard",
                                                             index = 0,
                                                             size = (130,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToClipboard, 0, wx.ALL, 5)
        self.btn_SummaryPlotToPNG = CustomBitmapButton(self.pnl_MultiPlotPanel,
                                                       type = u"ExportToFile",
                                                       index = 0,
                                                       size = (104,25))
        self.szr_ExportMultiPlot.Add(self.btn_SummaryPlotToPNG, 0, wx.ALL, 5)
        self.szr_MultiPlotRight.Add(self.szr_ExportMultiPlot, 0, wx.ALL, 0)
        self.szr_MultiPlot.Add(self.szr_MultiPlotRight, 0, wx.EXPAND, 5)
        self.pnl_MultiPlotPanel.SetSizer(self.szr_MultiPlot)
        self.pnl_MultiPlotPanel.Layout()
        self.szr_MultiPlot.Fit(self.pnl_MultiPlotPanel)
        self.sbk_ResultPlots.AddPage(self.pnl_MultiPlotPanel, u"Summary Plot",True)
        self.sbk_ResultPlots.SetSelection(0)
        # ===============================================================================

        self.szr_SimpleBook.Add(self.sbk_ResultPlots, 0, wx.EXPAND, 5)        
        self.bSizer12.Add(self.szr_SimpleBook, 0, wx.ALL, 5)
        self.szr_Results.Add(self.bSizer12, 1, wx.EXPAND, 5)
        
        # Finalise
        self.tab_Results.SetSizer(self.szr_Results)
        self.tab_Results.Layout()
        self.szr_Results.Fit(self.tab_Results)
        self.tabs_Analysis.AddPage(self.tab_Results, u"Results", False)

        #### #    #  #   ###  #     ##  #####  ###
        #    #    ## #   #  # #    #  #   #   #
        ###  #    # ##   ###  #    #  #   #    ##
        #    #    #  #   #    #    #  #   #      #
        #### #### #  #   #    ####  ##    #   ###  ######################################
        
        self.tab_ELNPlots = tab.ELNPlots(self.tabs_Analysis.sbk_Notebook,
                                         tabname = self, shorthand = self.str_Shorthand)
        self.tabs_Analysis.AddPage(self.tab_ELNPlots, u"Plots for ELN", False)

        #### #  # ###   ##  ###  #####
        #    #  # #  # #  # #  #   #
        ##    ##  ###  #  # ###    #
        #    #  # #    #  # #  #   #
        #### #  # #     ##  #  #   # ####################################################

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
        self.lst_Headers_ASHTRF_New = ["Experiment Type","Purification ID","Target ID","Protein Concentration (uM)","Peptide ID","Global Compound ID",
            "Peptide Concentration (uM)","Solvent","Solvent Concentration (%)","Buffer","Compound Incubation Time (mins)","Peptide Incubation Time (mins)",
            "Bead Incubation Time (mins)","Incubation Temperatures (C)","LogIC50 (relative to 1M)","LogIC50 error","IC50","Curve Fit: Upper 95% ConfLimit",
            "Curve Fit: Lower 95% ConfLimit","Curve Fit: Hill Slope","Curve (Obsolete)","Curve Fit: Bottom","Curve Fit: Top","R2","Data Quality","Comments on Curve Fit",
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
            "Compound Concentration 16 Error (%)","No Protein Control Activity","No Protein Control Error","No Peptide Control Activity","No Peptide Control Error",
            "Z'","Z' Robust","Solvent/Control","Buffer/Control","Experiment Date","ELN ID","Comments","Date record created","Creator of record" ]
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
        self.tab_Export = tab.ExportToDatabase(self.tabs_Analysis.sbk_Notebook, self)
        self.tabs_Analysis.AddPage(self.tab_Export, u"Export results to Database", False)


        #################################################################################

        self.szr_Tabs.Add(self.tabs_Analysis, 1, wx.EXPAND|wx.ALL, 0)
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
        ###  # #  # ###  # #  #  ##  ####################################################

        # Highest level events:
        self.tabs_Analysis.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

        # Results Tab
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.EditSourceConcentration)
        self.lbc_Samples.Bind(wx.EVT_LIST_ITEM_SELECTED, self.ShowCurve)
        self.btn_ExportResultsTable.Bind(wx.EVT_BUTTON, self.ExportResultsTable)
        self.chk_Confidence.Bind(wx.EVT_CHECKBOX, self.ShowConfidence)
        self.chk_Fit.Bind(wx.EVT_CHECKBOX, self.ToggleFit)
        self.btn_FitToolTip.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.rad_Res_Raw.Bind(wx.EVT_RADIOBUTTON, self.RadRaw)
        self.rad_Res_NormConst.Bind(wx.EVT_RADIOBUTTON, self.RadNormConst)
        self.rad_Res_NormFree.Bind(wx.EVT_RADIOBUTTON, self.RadNormFree)
        self.btn_FigToClipboard.Bind(wx.EVT_BUTTON, self.plt_DoseResponse.PlotToClipboard)
        self.btn_SaveFig.Bind(wx.EVT_BUTTON, self.plt_DoseResponse.PlotToPNG)
        self.btn_SaveAll.Bind(wx.EVT_BUTTON, self.AllPlotsToPNG)
        self.btn_CopyCurveParameters.Bind(wx.EVT_BUTTON, self.CopyCurveParameters)
        self.rad_MultiPlotNorm.Bind(wx.EVT_RADIOBUTTON, self.MultiRadNorm)
        self.rad_MultiPlotRaw.Bind(wx.EVT_RADIOBUTTON, self.MultiRadRaw)
        self.chk_ErrorBars.Bind(wx.EVT_CHECKBOX, self.ShowErrorBars)
        self.chk_ExcludedPoints.Bind(wx.EVT_CHECKBOX, self.ShowExcludedPoints)
        self.chk_PreviewPlot.Bind(wx.EVT_CHECKBOX, self.TogglePreviewPlot)
        self.btn_SummaryPlotToClipboard.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToClipboard)
        self.btn_SummaryPlotToPNG.Bind(wx.EVT_BUTTON, self.plt_MultiPlot.PlotToPNG)

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
                self.bol_ReviewsDrawn = self.tab_Review.Populate()
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
        """
        Gets called by main window to populate all tabs after loading a file.

        Arguments:
            dfr_LoadedDetails -> pandas dataframe. Contains all metadata/assay details
            lst_LoadedBoolean -> list of boolean values.
            dfr_Loaded -> pandas dataframe. Contains assay data (raw data and results)
            lst_Paths -> list of file paths
        """
        self.dfr_AssayData = dfr_Loaded

        ## Backwards compatibility for references:
        #for plate in range(self.dfr_AssayData.shape[0]):
        #    if len(self.dfr_AssayData.loc[plate,"References"]) < 8:
        #        self.dfr_AssayData.loc[plate,"References"].append("N/A, reanalyse data")
        #        self.dfr_AssayData.loc[plate,"References"].append("N/A, reanalyse data")

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
            Date = self.dfr_Details.loc["Date","Value"]
            Date = wx.DateTime.FromDMY(int(Date[8:10]), int(Date[5:7]), int(Date[:4]))
            self.tab_Details.DatePicker.SetValue(Date)
        except:
            self.dfr_Details.at["Date","Value"] = Date

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
            self.bol_ReviewsDrawn = self.tab_Review.Populate()
        self.bol_TransferLoaded = lst_LoadedBoolean[9]
        self.bol_GlobalLayout = lst_LoadedBoolean[10]
        self.bol_PlateID = lst_LoadedBoolean[11]
        self.bol_PlateMapPopulated = lst_LoadedBoolean[12]
        # And of course this has been previously saved since
        # we are loading it from a file
        self.bol_PreviouslySaved = True

        # Populate transfer/data file tab
        for idx_Plate in self.dfr_AssayData.index:
            self.tab_Files.lbc_Transfer.InsertItem(i,self.dfr_AssayData.iloc[idx_Plate,0])
            self.tab_Files.lbc_Transfer.SetItem(i,1,str(self.dfr_AssayData.iloc[idx_Plate,2]))
            self.tab_Files.lbc_Transfer.SetItem(i,2,self.dfr_AssayData.iloc[idx_Plate,3])
        # If files have been moved, the original file paths saved
        # in the bbq file are no longer up to date!
        try:
            lst_DataFiles = os.listdir(lst_Paths[1])
        except:
            lst_DataFiles = []
            lst_Paths[0] = "Path not found"
            lst_Paths[1] = "Path not found"
        self.str_DataPath = lst_Paths[1]
        # Go through directory, get each file with correct extension,
        # compare to list already assigned. If not assigned, add to
        # tab_Files.lbc_Data
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
        self.dfr_Layout = pd.DataFrame(index=range(len(dfr_Loaded)),
                                       columns=["PlateID","ProteinNumerical",
                                                "PurificationID","Concentration",
                                                "WellType"])
        for idx_Plate in self.dfr_Layout.index:
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
        self.str_AssayCategory = "dose_response"
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
                                                      "EPDR",
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
                    self.tab_Export.grd_Database.SetCellValue(idx_List,0,self.str_AssayType + " IC50")
                    self.tab_Export.grd_Database.SetCellValue(idx_List,1,self.str_Purification)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,2,str(float(self.int_ProteinConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,3,self.str_PeptideID)
                    # omitted
                    self.tab_Export.grd_Database.SetCellValue(idx_List,5,str(float(self.int_PeptideConc)/1000))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,6,self.str_Solvent)
                    self.tab_Export.grd_Database.SetCellValue(idx_List,7,str(self.int_SolventPercent))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,8,self.str_Buffer)
                    # dfr_Database
                    self.dfr_Database.iloc[idx_List,0] = self.str_AssayType + " IC50"
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
        dfr_Heatmap = pd.DataFrame(columns=["Well","SampleID","Value"],
                                   index=range(int_PlateFormat))
        for i in range(int_PlateFormat):
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
                    well = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Locations"][conc][rep]
                    sample = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
                    #print(str(well) + ": " + sample)
                    dfr_Heatmap.loc[int(well),"SampleID"] = sample
        return dfr_Heatmap

    def PlateQualityToClipboard(self, event):
        """
        Event handler. Writes all the plate quality measures
        into a dataframe to save clipboard.
        """
        idx_Plate = self.tab_Review.dic_Plots["Heat Map"].PlateIndex
        pd.DataFrame({"BufferMean":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0],2)],
            "BufferSEM":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferSEM",0],2)],
            "SolventMean":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0],2)],
            "SolventSEM":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0],2)],
            "ControlMean":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ControlSEM":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlSEM",0],2)],
            "BufferToControl":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0]/self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "SolventToControl":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0]/self.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ZPrimeMean":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",0],3)],
            "ZPrimeMedian":[round(self.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMedian",0],3)]}).to_clipboard(header=True, index=False)
    
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
        for idx_Plate in self.dfr_AssayData.index:
            for idx_Sample in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].index:
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"] != "Control":
                    idx_List += 1
                    self.lbc_Samples.InsertItem(idx_List,str(idx_Plate+1))
                    self.lbc_Samples.SetItem(idx_List,1,self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"])
                    self.lbc_Samples.SetItem(idx_List,2,(str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SourceConcentration"])*1000)))
                    if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFitFree"] == True:
                        self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreePars"][3],2)))
                        self.lbc_Samples.SetItem(idx_List,4,chr(177))
                        self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreeCI"][3],2)))
                    else:
                        self.lbc_Samples.SetItem(idx_List,3,"ND")
                        self.lbc_Samples.SetItem(idx_List,4,"")
                        self.lbc_Samples.SetItem(idx_List,5,"")
        self.plt_DoseResponse.Input = self.dfr_AssayData.iloc[0,5].loc[0]
        self.plt_DoseResponse.PlateIndex = 0
        self.plt_DoseResponse.SampleIndex = 0
        self.rad_Res_NormFree.SetValue(True)
        self.rad_Res_NormConst.SetValue(False)
        self.rad_Res_Raw.SetValue(False)
        if self.dfr_AssayData.iloc[0,5].loc[0,"DoFitFree"] == True:
            self.chk_Fit.SetValue(True)
        else:
            self.chk_Fit.SetValue(False)
        self.lbc_Samples.Select(0) # This will trigger the drawing of the plo

        # Multiplot
        self.plt_MultiPlot.IDs[0] = self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"]
        self.plt_MultiPlot.Dose[0] = df.moles_to_micromoles(self.dfr_AssayData.iloc[0,5].loc[0,"Concentrations"])
        self.plt_MultiPlot.RawPoints[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Raw"]
        self.plt_MultiPlot.RawSEM[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawSEM"]
        self.plt_MultiPlot.RawExcluded[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawExcluded"]
        self.plt_MultiPlot.RawFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"RawFit"]
        self.plt_MultiPlot.NormPoints[0] = self.dfr_AssayData.iloc[0,5].loc[0,"Norm"]
        self.plt_MultiPlot.NormSEM[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormSEM"]
        self.plt_MultiPlot.NormExcluded[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormExcluded"]
        if self.dfr_AssayData.iloc[0,5].loc[0,"Show"] == 1:
            self.rad_MultiPlotNorm.SetValue(True)
            self.plt_MultiPlot.NormFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormFitFree"]
        else:
            self.rad_MultiPlotNorm.SetValue(False)
            self.plt_MultiPlot.NormFit[0] = self.dfr_AssayData.iloc[0,5].loc[0,"NormFitConst"]
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].SetLabel(self.dfr_AssayData.iloc[0,5].loc[0,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[0]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[0]].Enable(True)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].SetSelection(0)
        self.dic_BitmapCombos[self.lst_BitmapCombos[0]].Enable(True)
        self.chk_ErrorBars.Value = True
        self.chk_ExcludedPoints.Value = True
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()
        self.bol_ResultsDrawn = True

    def ShowConfidence(self, event):
        """
        Event handler. Toggle display of confidence intervals on graph.
        """
        self.plt_DoseResponse.Confidence = self.chk_Confidence.GetValue()
        self.plt_DoseResponse.Draw()

    def ToggleFit(self,event):
        """
        Event handler. Change whether currently displayed should be fitted or not
        """
        # get indices
        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] = self.chk_Fit.GetValue()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFitFree"] = self.chk_Fit.GetValue()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFitConst"] = self.chk_Fit.GetValue()
        if self.chk_Fit.GetValue() == False:
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFitPars"] = df.set_to_nan(4)
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFitFreePars"] = df.set_to_nan(4)
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"RawFit"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"]))
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample,"NormFitFree"] = df.set_to_nan(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"]))
        else:
            self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_sigmoidal(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
            self.lbc_Samples.SetItem(idx,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreePars"][3],2)))
            self.lbc_Samples.SetItem(idx,4,chr(177))
            self.lbc_Samples.SetItem(idx,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreeCI"][3],2)))
        else:
            self.lbc_Samples.SetItem(idx,3,"ND")
            self.lbc_Samples.SetItem(idx,4,"")
            self.lbc_Samples.SetItem(idx,5,"")
        self.plt_DoseResponse.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
        self.plt_DoseResponse.PlateIndex = idx_Plate
        self.plt_DoseResponse.SampleIndex = idx_Sample
        self.plt_DoseResponse.Draw()
        self.UpdateDetails(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample], self.IntShow())
        self.UpdateSampleReporting("event")

    def ShowCurve(self,event):
        """
        Event handler. Show/Update the displayed curve based on selection on ListCtr.
        """
        self.Freeze()
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        if self.sbk_ResultPlots.GetSelection() == 0:
            int_Show = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"]
            if int_Show == 0:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(False)
                self.rad_Res_Raw.SetValue(True)
                str_DoFit = "DoFitRaw"
            elif int_Show == 1:
                self.rad_Res_NormFree.SetValue(True)
                self.rad_Res_NormConst.SetValue(False)
                self.rad_Res_Raw.SetValue(False)
                str_DoFit = "DoFitFree"
            elif int_Show == 2:
                self.rad_Res_NormFree.SetValue(False)
                self.rad_Res_NormConst.SetValue(True)
                self.rad_Res_Raw.SetValue(False)
                str_DoFit = "DoFitConst"
            self.plt_DoseResponse.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
            self.plt_DoseResponse.PlateIndex = idx_Plate
            self.plt_DoseResponse.SampleIndex = idx_Sample
            self.plt_DoseResponse.Draw()
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_DoFit] == True:
                self.chk_Fit.SetValue(True)
            else:
                self.chk_Fit.SetValue(False)
            self.UpdateDetails(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample], int_Show)
            self.UpdateSampleReporting(None)

        # Add Preview to multiplot
        self.plt_MultiPlot.PreviewID = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
        self.plt_MultiPlot.PreviewDose = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
        self.plt_MultiPlot.PreviewRawPoints = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Raw"]
        self.plt_MultiPlot.PreviewRawSEM = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawSEM"]
        self.plt_MultiPlot.PreviewRawExcluded = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawExcluded"]
        self.plt_MultiPlot.PreviewRawFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"]
        self.plt_MultiPlot.PreviewNormPoints = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"]
        self.plt_MultiPlot.PreviewNormSEM = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"]
        self.plt_MultiPlot.PreviewNormExcluded = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormExcluded"]
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] == 1:
            self.plt_MultiPlot.PreviewNormFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFree"]
        else:
            self.plt_MultiPlot.PreviewNormFit = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitConst"]
        self.plt_MultiPlot.Draw()
        self.Thaw()

    def UpdateDetails(self, dfr_Input, int_Show):
        """
        Updates details of sample shown next to plot.

        Arguments:
            dfr_Input -> pandas dataframe. All data for the selected sample
            int_Show -> integer. Which dataset to show:
                        0: Raw data, free fit
                        1: Normalised data, free fit
                        2: Normalised data, constrained fit.
        """
        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_RSquareKeyword = "RawFitR2"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_RSquareKeyword = "NormFitFreeR2"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_RSquareKeyword = "NormFitConstR2"
        if dfr_Input[str_DoFit] == True:
            str_IC50 = df.write_IC50(dfr_Input[str_Pars][3], dfr_Input[str_DoFit],dfr_Input[str_Confidence][3])
            if dfr_Input[str_Pars][1] < -20:
                str_BottomWarning = chr(9888) + " outside range"
            else:
                str_BottomWarning = ""
            str_YBot = str(round(dfr_Input[str_Pars][1],2)) + " " + str_BottomWarning
            if dfr_Input[str_Pars][0] > 120:
                str_TopWarning = chr(9888) + " outside range"
            else:
                str_TopWarning = ""
            str_YTop = str(round(dfr_Input[str_Pars][0],2)) + " " + str_TopWarning
            flt_Span = round(dfr_Input[str_Pars][0]-dfr_Input[str_Pars][1],1)
            if flt_Span > 120:
                str_SpanWarning = chr(9888) + " outside range"
            else:
                str_SpanWarning = ""
            str_Span = str(str(flt_Span) + str_SpanWarning)
            str_Hill = str(round(dfr_Input[str_Pars][2],2))
            str_RSquare = str(round(dfr_Input[str_RSquareKeyword],3))
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
        self.Thaw()

    def CopyCurveParameters(self, event):
        """
        Event handler. Copies parameters of currently displayed
        curve to clipboard.
        """
        if self.plt_DoseResponse.Input["Show"] == 0:
            str_Type = "Raw data free fit"
            str_RawOrNorm = "Raw"
            str_FreeOrConstrained = ""
        elif self.plt_DoseResponse.Input["Show"] == 1:
            str_Type = "Normalised data free fit"
            str_RawOrNorm = "Norm"
            str_FreeOrConstrained = "Free"
        elif self.plt_DoseResponse.Input["Show"] == 2:
            str_Type = "Normalised data constrained fit"
            str_RawOrNorm = "Norm"
            str_FreeOrConstrained = "Const"
        flt_Top = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][0],2)
        flt_Bottom = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][1],2)
        flt_IC50 = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][3],3)
        flt_Slope = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][2],2)
        flt_RSquare = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"R2"],3)
        flt_Span = round(self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][0]-self.plt_DoseResponse.Input[str_RawOrNorm+"Fit"+str_FreeOrConstrained+"Pars"][1],2)
        pd.DataFrame(index=["Fit","IC50(uM)","Hill Slope","Top","Bottom","Span","RSquare"],
                     data=[str_Type,flt_IC50,flt_Slope,flt_Top,flt_Bottom,flt_Span,flt_RSquare],
                     columns=["Value"]).to_clipboard()

    def UpdateSampleReporting(self, event):
        """
        Updates what gets reported in lbc_Samples and lbc_Database.
        Only fitting results of normalised data will be reported.
        """
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        int_Show = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"]
        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
        # Update lists
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_DoFit] == True:
            self.lbc_Samples.SetItem(idx_List,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3],2)))
            self.lbc_Samples.SetItem(idx_List,4,chr(177))
            self.lbc_Samples.SetItem(idx_List,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3],2)))
        if not "activity" in self.str_AssayCategory:
            self.UpdateDatabaseTable(idx_List, idx_Sample, idx_Plate, int_Show)
        else:
            self.UpdateDatabaseTableActivity(idx_List, idx_Sample, idx_Plate, int_Show)
        
    def UpdateDatabaseTable(self, idx_List, idx_Sample, idx_Plate, int_Show):
        """
        Updates database table at the speciied position with the specified parameters.

        Arguments:
            idx_List -> integer. Position of the entry in the results table.
            idx_Sample -> integer. Dataframe index of the sample.
            idx_Plate -> integer. Dataframe index of the plate the sample is on
            int_show -> integer. Determines which parameters will be shown
                        0: raw data fit
                        1: normalised, free fit
                        2: normalised, constrained fit
        """

        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_R2 = "RawFitR2"
            str_Errors = "RawFitErrors"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_R2 = "NormFitFreeR2"
            str_Errors = "NormFitFreeErrors"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_R2 = "NormFitConstR2"
            str_Errors = "NormFitConstErrors"

        if self.bol_ExportPopulated == True:
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_DoFit] == True:
                # LIST
                self.tab_Export.grd_Database.SetCellValue(idx_List,13,str(np.log10(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])/1000000))) # log IC50
                self.tab_Export.grd_Database.SetCellValue(idx_List,14,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Errors][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,15,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])) # IC50 in uM
                self.tab_Export.grd_Database.SetCellValue(idx_List,16,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] +
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,17,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] -
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,18,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][2]))) # Hill slope
                # omitted
                self.tab_Export.grd_Database.SetCellValue(idx_List,20,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][1]))) # Bottom of curve
                self.tab_Export.grd_Database.SetCellValue(idx_List,21,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][0]))) # Top of curve
                self.tab_Export.grd_Database.SetCellValue(idx_List,22,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_R2])) # Rsquared
                self.tab_Export.grd_Database.SetCellValue(idx_List,25,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(idx_List,26,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(idx_List,27+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,28+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,29+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[idx_List,13] = np.log10(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])/1000000) # log IC50
                self.dfr_Database.iloc[idx_List,14] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Errors][3]
                self.dfr_Database.iloc[idx_List,15] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] # IC50 in uM
                self.dfr_Database.iloc[idx_List,16] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]
                self.dfr_Database.iloc[idx_List,17] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] - self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]
                self.dfr_Database.iloc[idx_List,18] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][2]) # Hill slope
                # omitted
                self.dfr_Database.iloc[idx_List,20] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][1]) # Bottom of curve
                self.dfr_Database.iloc[idx_List,21] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][0]) # Top of curve
                self.dfr_Database.iloc[idx_List,22] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_R2] # Rsquared
                self.dfr_Database.iloc[idx_List,25] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[idx_List,26] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Plate,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[idx_List,27+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[idx_List,28+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]
                    self.dfr_Database.iloc[idx_List,29+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]
            else:
                # LIST
                self.lbc_Samples.SetItem(idx_List,3,"ND")
                self.lbc_Samples.SetItem(idx_List,4,"")
                self.lbc_Samples.SetItem(idx_List,5,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,13,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,14,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,15,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,16,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,17,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,18,"")
                # omitted
                self.tab_Export.grd_Database.SetCellValue(idx_List,20,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,21,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,22,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,25,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(idx_List,26,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(idx_List,27+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,28+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,29+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[idx_List,13] = np.nan # log IC50
                self.dfr_Database.iloc[idx_List,14] = np.nan
                self.dfr_Database.iloc[idx_List,15] = np.nan # IC50 in uM
                self.dfr_Database.iloc[idx_List,16] = np.nan
                self.dfr_Database.iloc[idx_List,17] = np.nan
                self.dfr_Database.iloc[idx_List,18] = np.nan # Hill slope
                # omitted
                self.dfr_Database.iloc[idx_List,20] = np.nan # Bottom of curve
                self.dfr_Database.iloc[idx_List,21] = np.nan # Top of curve
                self.dfr_Database.iloc[idx_List,22] = np.nan # Rsquared
                self.dfr_Database.iloc[idx_List,25] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[idx_List,26] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[idx_List,27+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[idx_List,28+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]
                    self.dfr_Database.iloc[idx_List,29+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]
        self.bol_ELNPlotsDrawn = False

    def UpdateDatabaseTableActivity(self, idx_List, idx_Sample, idx_Plate, int_Show):
        """
        Updates database table at the speciied position with the specified parameters.

        Arguments:
            idx_List -> integer. Position of the entry in the results table.
            idx_Sample -> integer. Dataframe index of the sample.
            idx_Plate -> integer. Dataframe index of the plate the sample is on
            int_show -> integer. Determines which parameters will be shown
                        0: raw data fit
                        1: normalised, free fit
                        2: normalised, constrained fit
        """

        if int_Show == 0:
            str_Pars = "RawFitPars"
            str_DoFit = "DoFitRaw"
            str_Confidence = "RawFitCI"
            str_R2 = "RawFitR2"
            str_Errors = "RawFitErrors"
        elif int_Show == 1:
            str_Pars = "NormFitFreePars"
            str_DoFit = "DoFitFree"
            str_Confidence = "NormFitFreeCI"
            str_R2 = "NormFitFreeR2"
            str_Errors = "NormFitFreeErrors"
        elif int_Show == 2:
            str_Pars = "NormFitConstPars"
            str_DoFit = "DoFitConst"
            str_Confidence = "NormFitConstCI"
            str_R2 = "NormFitConstR2"
            str_Errors = "NormFitConstErrors"

        if self.bol_ExportPopulated == True:
            if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_DoFit] == True:
                # LIST
                self.tab_Export.grd_Database.SetCellValue(idx_List,22,str(np.log10(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])/1000000))) # log IC50
                self.tab_Export.grd_Database.SetCellValue(idx_List,23,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Errors][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,24,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])) # IC50 in uM
                self.tab_Export.grd_Database.SetCellValue(idx_List,25,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] +
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,26,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] -
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]))
                self.tab_Export.grd_Database.SetCellValue(idx_List,27,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][2]))) # Hill slope
                self.tab_Export.grd_Database.SetCellValue(idx_List,28,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][1]))) # Bottom of curve
                self.tab_Export.grd_Database.SetCellValue(idx_List,29,str(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][0]))) # Top of curve
                self.tab_Export.grd_Database.SetCellValue(idx_List,30,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_R2])) # Rsquared
                self.tab_Export.grd_Database.SetCellValue(idx_List,16,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(idx_List,17,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(idx_List,32+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,33+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,34+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[idx_List,22] = np.log10(float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3])/1000000) # log IC50
                self.dfr_Database.iloc[idx_List,23] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Errors][3]
                self.dfr_Database.iloc[idx_List,24] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] # IC50 in uM
                self.dfr_Database.iloc[idx_List,25] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] + self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]
                self.dfr_Database.iloc[idx_List,26] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][3] - self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Confidence][3]
                self.dfr_Database.iloc[idx_List,27] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][2]) # Hill slope
                self.dfr_Database.iloc[idx_List,28] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][1]) # Bottom of curve
                self.dfr_Database.iloc[idx_List,29] = float(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_Pars][0]) # Top of curve
                self.dfr_Database.iloc[idx_List,30] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,str_R2] # Rsquared
                self.dfr_Database.iloc[idx_List,16] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[idx_List,17] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Plate,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[idx_List,32+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[idx_List,33+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]
                    self.dfr_Database.iloc[idx_List,34+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]
            else:
                # LIST
                self.lbc_Samples.SetItem(idx_List,3,"ND")
                self.lbc_Samples.SetItem(idx_List,4,"")
                self.lbc_Samples.SetItem(idx_List,5,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,22,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,23,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,24,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,25,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,26,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,27,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,28,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,29,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,30,"")
                self.tab_Export.grd_Database.SetCellValue(idx_List,16,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0])) # enzyme reference
                self.tab_Export.grd_Database.SetCellValue(idx_List,17,str(self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0])) # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.tab_Export.grd_Database.SetCellValue(idx_List,32+intColumnOffset,str(lstConcentrations[j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,33+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]))
                    self.tab_Export.grd_Database.SetCellValue(idx_List,34+intColumnOffset,str(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]))
                # dfr_Database
                self.dfr_Database.iloc[idx_List,22] = np.nan # log IC50
                self.dfr_Database.iloc[idx_List,23] = np.nan
                self.dfr_Database.iloc[idx_List,24] = np.nan # IC50 in uM
                self.dfr_Database.iloc[idx_List,25] = np.nan
                self.dfr_Database.iloc[idx_List,26] = np.nan
                self.dfr_Database.iloc[idx_List,27] = np.nan # Hill slope
                self.dfr_Database.iloc[idx_List,28] = np.nan # Bottom of curve
                self.dfr_Database.iloc[idx_List,29] = np.nan # Top of curve
                self.dfr_Database.iloc[idx_List,30] = np.nan # Rsquared
                self.dfr_Database.iloc[idx_List,16] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0] # enzyme reference
                self.dfr_Database.iloc[idx_List,17] = self.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0] # enzyme reference error
                lstConcentrations = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
                for j in range(len(lstConcentrations)):
                    intColumnOffset = (j)*3
                    self.dfr_Database.iloc[idx_List,32+intColumnOffset] = lstConcentrations[j]
                    self.dfr_Database.iloc[idx_List,33+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"][j]
                    self.dfr_Database.iloc[idx_List,34+intColumnOffset] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"][j]
            self.bol_ELNPlotsDrawn = False

    def EditSourceConcentration(self,event):
        """
        Event handler. Gets called from the source concentration
        edit dialog.
        """
        idx_Focus = self.lbc_Samples.GetFocusedItem()
        str_OldConc = self.lbc_Samples.GetItemText(idx_Focus,2)
        dlg_ChangeSourceConc = dlg_SourceChange(self,str_OldConc)
        bol_Update = dlg_ChangeSourceConc.ShowModal()
        dlg_ChangeSourceConc.Destroy()
        if self.str_NewConc == None:
            return None
        if bol_Update == True:
            if self.str_NewConc != str_OldConc:
                # Get which plate it is
                idx_Plate = int(self.lbc_Samples.GetItemText(idx_Focus,0))-1 # Human plate numbering vs computer indexing!
                # Get which sample it is
                str_Sample = self.lbc_Samples.GetItemText(idx_Focus,1)
                dfr_Plate = self.dfr_AssayData.iloc[idx_Plate,5]
                idx_Sample = dfr_Plate[dfr_Plate["SampleID"] == str_Sample].index.tolist()
                idx_Sample = idx_Sample[0] # above function returns list, but there will always be only one result
                self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SourceConcentration"] = float(self.str_NewConc)/1000
                for conc in range(len(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])):
                    self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][conc] = df.change_concentrations(float(str_OldConc),float(self.str_NewConc),
                        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"][conc],
                        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"AssayVolume"])
                if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                    self.dfr_AssayData.iloc[idx_Plate,5].at[idx_Sample] = df.recalculate_fit_sigmoidal(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample])
                self.plt_DoseResponse.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
                self.plt_DoseResponse.PlateIndex = idx_Plate
                self.plt_DoseResponse.SampleIndex = idx_Sample
                self.plt_DoseResponse.Draw()
                self.lbc_Samples.SetItem(idx_Focus,2,self.str_NewConc)
                if self.IntShow() == 2:
                    if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                        self.lbc_Samples.SetItem(idx_Focus,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitFreePars"][3],2)))
                        self.lbc_Samples.SetItem(idx_Focus,4,chr(177))
                        self.lbc_Samples.SetItem(idx_Focus,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFitFreeCI"][3],2)))
                    else:
                        self.lbc_Samples.SetItem(idx_Focus,3,"ND")
                        self.lbc_Samples.SetItem(idx_Focus,4,"")
                        self.lbc_Samples.SetItem(idx_Focus,5,"")
                else:
                    if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"DoFit"] == True:
                        self.lbc_Samples.SetItem(idx_Focus,3,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreePars"][3],2)))
                        self.lbc_Samples.SetItem(idx_Focus,4,chr(177))
                        self.lbc_Samples.SetItem(idx_Focus,5,str(round(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFreeCI"][3],2)))
                    else:
                        self.lbc_Samples.SetItem(idx_Focus,3,"ND")
                        self.lbc_Samples.SetItem(idx_Focus,4,"")
                        self.lbc_Samples.SetItem(idx_Focus,5,"")
                self.UpdateDetails(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample],self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"])
                self.UpdateSampleReporting(None)
        self.str_NewConc = None

    def ExportResultsTable(self,event):
        """
        Event handler. Copies results table to clipboard.
        """
        dfr_ResultsTable = pd.DataFrame(columns=["Plate","SampleID",
                                                 "SourceConcentration[mM]",
                                                 "TopConcentration[uM]",
                                                 "IC50[uM]"],
                                        index=range(self.lbc_Samples.GetItemCount()))
        count = 0
        for idx_Plate in self.dfr_AssayData.index:
            for idx_Sample in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].index:
                dfr_ResultsTable.loc[count,"Plate"] = idx_Plate+1
                dfr_ResultsTable.loc[count,"SampleID"] = self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SampleID"]
                dfr_ResultsTable.loc[count,"SourceConcentration[mM]"] = float(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"SourceConcentration"]) * 1000
                dfr_ResultsTable.loc[count,"TopConcentration[uM]"] = float(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"Concentrations"][0]) * 1000000
                dfr_ResultsTable.loc[count,"IC50[uM]"] = float(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].loc[idx_Sample,"NormFitFreePars"][3]) * 1000000
                count += 1
        # Export as csv:
        fdlg = wx.FileDialog(self,
                             message = "Save summary table as as",
                             wildcard="Comma separated files (*.csv)|*.csv",
                             style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        if fdlg.ShowModal() == wx.ID_OK:
            str_SavePath = fdlg.GetPath()
            # Check if str_SavePath ends in .png. If so, remove
            if str_SavePath[-1:-4] == ".csv":
                str_SavePath = str_SavePath[:len(str_SavePath)]
            dfr_ResultsTable.to_csv(str_SavePath)

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
        idx_Plate = int(self.lbc_Samples.GetItemText(idx_SampleList,0))-1 # Human plate numbering vs computer indexing!
        # get index on plate of selected sample
        dfr_Sample = self.dfr_AssayData.iloc[idx_Plate,5]
        idx_SampleDataFrame = dfr_Sample[dfr_Sample["SampleID"] == self.lbc_Samples.GetItemText(idx_SampleList,1)].index.tolist()
        idx_SampleDataFrame = idx_SampleDataFrame[0] # above function returns list, but there will always be only one result
        return idx_SampleList, idx_SampleDataFrame, idx_Plate

    def IntShow(self):
        """
        Determines which dataset to show and returns corresponding
        integer:
            0: Raw data, free fit
            1: Normalised data, free fit
            2: Normalised data, constrained fit
        """
        if self.rad_Res_NormFree.Value == True:
            return 1
        elif self.rad_Res_NormConst.Value == True:
            return 2
        else:
            return 0

    def RadRaw(self, event):
        """
        Event handler for selecting rad_Res_Raw
        radio button.
        """
        self.rad_Res_Raw.SetValue(True)
        self.rad_Res_NormFree.SetValue(False)
        self.rad_Res_NormConst.SetValue(False)

        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = self.IntShow()

        self.ShowCurve(event)

    def RadNormFree(self, event):
        """
        Event handler for selecting rad_Res_NormFree
        radio button.
        """
        self.rad_Res_Raw.SetValue(False)
        self.rad_Res_NormFree.SetValue(True)
        self.rad_Res_NormConst.SetValue(False)

        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = self.IntShow()

        self.ShowCurve(event)

    def RadNormConst(self, event):
        """
        Event handler for selecting rad_Res_NormConst
        radio button.
        """
        self.rad_Res_Raw.SetValue(False)
        self.rad_Res_NormFree.SetValue(False)
        self.rad_Res_NormConst.SetValue(True)

        idx,idx_Sample,idx_Plate = self.GetPlotIndices()
        self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] = self.IntShow()

        self.ShowCurve(event)

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
        for idx_Plate in self.dfr_AssayData.index:
            int_Samples += len(self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"])
        count = 0
        for idx_Plate in self.dfr_AssayData.index:
            for idx_Sample in self.dfr_AssayData.loc[idx_Plate,"ProcessedDataFrame"].index:
                count += 1
                #DO STUFF TO MAKE PLOT
                tempplot = cp.CurvePlotPanel(self.tab_Results, (600,450), self)
                tempplot.Input = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample]
                tempplot.Draw()
                sampleid = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
                savepath = os.path.join(str_SaveDirPath, sampleid + ".png")
                tempplot.figure.savefig(savepath, dpi=None, facecolor="w", edgecolor="w",
                                        orientation="portrait", format=None,
                                        transparent=False, bbox_inches=None,
                                        pad_inches=0.1)
                tempplot.Destroy()
                self.dlg_PlotsProgress.gauge.SetValue((count/int_Samples)*200)
        self.Thaw()
        self.dlg_PlotsProgress.Destroy()
    
    def ShowErrorBars(self, event):
        """
        Event handler. Toggles error bars on plot.
        """
        self.plt_MultiPlot.ErrorBars = self.chk_ErrorBars.Value
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()

    def ShowExcludedPoints(self, event):
        """
        Event handler. Toggles excluded points on plot.
        """
        self.plt_MultiPlot.ExcludedPoints = self.chk_ExcludedPoints.Value
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()
    
    def TogglePreviewPlot(self, event):
        """
        Event handler. Toggles preview of currently selected
        sample on multiplot.
        """
        self.plt_MultiPlot.Preview = self.chk_PreviewPlot.GetValue()
        self.plt_MultiPlot.Draw()

    def MultiPlotNormalised(self):
        """
        Event handlers. Switches between displaying raw data and
        normalised data on multiplot.
        """
        if self.rad_MultiPlotRaw.GetValue() == True:
            return False
        else:
            return True

    def ColourSelect(self, event):
        """
        Event handler. Changes colour of graph on multiplot.
        """
        idx_Colour = event.GetEventObject().GetSelection()
        self.plt_MultiPlot.Colours[event.GetEventObject().Index] = self.plt_MultiPlot.ColourChoices[idx_Colour]
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
        self.plt_MultiPlot.Draw()

    def AddGraph(self, event):
        """
        Event handler. Adds selected graph to multiplot.
        """
        idx_List,idx_Sample,idx_Plate = self.GetPlotIndices()
        idx_Graph = event.GetEventObject().Index
        self.plt_MultiPlot.IDs[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"]
        self.plt_MultiPlot.Dose[idx_Graph] = df.moles_to_micromoles(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Concentrations"])
        self.plt_MultiPlot.RawPoints[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Raw"]
        self.plt_MultiPlot.RawSEM[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawSEM"]
        self.plt_MultiPlot.RawExcluded[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawExcluded"]
        self.plt_MultiPlot.RawFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"RawFit"]
        self.plt_MultiPlot.NormPoints[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Norm"]
        self.plt_MultiPlot.NormSEM[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormSEM"]
        self.plt_MultiPlot.NormExcluded[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormExcluded"]
        if self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"Show"] == 1:
            self.plt_MultiPlot.NormFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitFree"]
        else:
            self.plt_MultiPlot.NormFit[idx_Graph] = self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"NormFitConst"]
        self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(True)
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel(self.dfr_AssayData.iloc[idx_Plate,5].loc[idx_Sample,"SampleID"])
        self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(True)
        self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(True)
        self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
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
            self.plt_MultiPlot.RawPoints[idx_Graph] = []
            self.plt_MultiPlot.RawFit[idx_Graph] = []
            self.plt_MultiPlot.NormPoints[idx_Graph] = []
            self.plt_MultiPlot.NormFit[idx_Graph] = []
            self.dic_BitmapCombos[self.lst_BitmapCombos[idx_Graph]].Enable(False)
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].SetLabel("no sample")
            self.dic_MultiPlotLabels[self.lst_MultiPlotLabels[idx_Graph]].Enable(False)
            self.dic_RemoveButtons[self.lst_RemoveButtons[idx_Graph]].Enable(False)
            self.plt_MultiPlot.Normalised = self.MultiPlotNormalised()
            self.plt_MultiPlot.Draw()
        else:
            wx.MessageBox(message = "Cannot remove this graph.\n"
                                    + "At least one graph must be displayed.",
                          caption = "No can do",
                          style = wx.OK|wx.ICON_INFORMATION)

    def MultiRadNorm(self, event):
        """
        Event handler for selecting rad_MultiPlotNorm
        radio button.
        """
        if self.rad_MultiPlotNorm.GetValue() == True:
            self.rad_MultiPlotRaw.SetValue(False)
        else:
            self.rad_MultiPlotRaw.SetValue(True)
        self.plt_MultiPlot.Normalised = True
        self.plt_MultiPlot.Draw()

    def MultiRadRaw(self, event):
        """
        Event handler for selecting rad_MultiPlotRaw
        radio button.
        """
        if self.rad_MultiPlotRaw.GetValue() == True:
            self.rad_MultiPlotNorm.SetValue(False)
        else:
            self.rad_MultiPlotNorm.SetValue(True)
        self.plt_MultiPlot.Normalised = False
        self.plt_MultiPlot.Draw()

    def FitToolTip(self, event):
        """
        Event handler. Displays explanatory note for
        sigmoidal dose response fitting.
        """
        try: self.dlg_InfoToolTip.Destroy()
        except: None
        self.dlg_InfoToolTip = dlg_InfoToolTip(self,
                                               self.parent.str_OtherPath,
                                               "SigmoidalDoseResponseToolTip.png")
        self.dlg_InfoToolTip.Show()


