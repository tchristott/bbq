# Library of custom(ised) plot classes that include added functionality for the userinterface.

# Import libraries for plotting
import matplotlib
matplotlib.use("WXAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.figure import Figure
from matplotlib.backend_bases import MouseButton
from matplotlib import patches

# Import for copying to clipboard
from PIL import Image

import lib_datafunctions as df
import lib_platefunctions as pf
import lib_fittingfunctions as ff
import lib_messageboxes as msg
import lib_tooltip as tt
import lib_colourscheme as cs
import lib_custombuttons as btn

import pandas as pd
import numpy as np
import os

import wx
from wx.core import SetCursor

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
        It also included all the functions required to make
        it an interactive plot, namely
        
        Methods
            Draw. Draws the actual plot. Is used everytime data
            from a new sample is displayed or changes have been made

        CustomToolTip
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
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.ax = self.figure.add_subplot()
        self.Confidence = False
        self.Input = None
        self.PlateIndex = None
        self.SampleIndex = None
        self.SummaryPlot = summaryplot
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,virtualonly=False):
        """
        Draws the plot.

        Arguments:
            virtualonly -> boolean. Set to True if the plot is only
                           drawn "virtually" to be written to PGNG
                           or copied to clipboard.
        """
        self.SampleID = self.Input["SampleID"]
        # Convert dose to micromoles
        self.dose = df.moles_to_micromoles(self.Input["Concentrations"])
        self.figure.clear() # clear and re-draw function
        self.ax = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.11, right=0.99,
                                    top=self.Top , bottom=self.Bottom)
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
        # Get in/excluded points into a list w/o nan, using the dataframe
        # column with nan values produced a runtime warning with current
        # numpy version (date:2022-05-04)!
        plotting  = self.IncludeExclude(str_Show)
        self.dic_Doses = {"Data":plotting["dose_incl"],"Excluded":plotting["dose_excl"]}
        if len(plotting["dose_incl"]) > 0:
            self.ax.errorbar(plotting["dose_incl"], plotting["resp_incl"],
                             yerr=plotting["sem_incl"], fmt="none",
                             color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.ax.scatter(plotting["dose_incl"], plotting["resp_incl"],
                            marker="o", label="Data",
                            color=cs.TMBlue_Hex, picker=5)
        if len(plotting["dose_excl"]) > 0:
            self.ax.errorbar(plotting["dose_excl"], plotting["resp_excl"],
                             yerr=plotting["sem_excl"], fmt="none",
                             color=cs.TMBlue_Hex, elinewidth=0.3, capsize=2)
            self.ax.scatter(plotting["dose_excl"], plotting["resp_excl"],
                            marker="o", label="Excluded",
                            color=cs.WhiteHex, picker=5, edgecolors=cs.TMBlue_Hex,
                            linewidths=0.8)
        if self.Input["DoFit"+str_Fit] == True:
            self.ax.plot(self.dose, self.Input[str_Show+"Fit"+str_Fit],
                         label="Fit", color=cs.TMRose_Hex)
            if self.Confidence == True:
                upper, lower = ff.draw_sigmoidal_fit_error(self.Input["Concentrations"],
                    self.Input[str_Show+"Fit"+str_Fit+"Pars"],
                    self.Input[str_Show+"Fit"+str_Fit+"CI"]) # Plot 95%CI of fit
                self.ax.fill_between(self.dose, upper, lower, color="red", alpha=0.15)
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
                    self.tabname.plt_MultiPlot.Dose[i] = self.dose
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
            self.tabname.PopupMenu(PlotContextMenu(self))

    def CustomToolTip(self, event):
        """
        Custom function I wrote to get tool tips working with matplotlib
        backend plots in wxPython.
        The way this works is as follows:
            - x and y coordinates of the mouse get handed to the function
              from a "motion_notify_event" from the plot.
            - The function pulls the plot data from the global dataframe
              (by looking up the sample ID)
            - Coordinates get then compared to the x and y coordinates
              of the graph (for loop going through the datapoints).
            - If the mouse coordinates are within a certain range of a
              datapoint (remember to take scale of axes into account),
              wx.Dialog dlg_ToolTip gets called. Before each call, the
              function will try to destry it (the neccessary "except:"
              just goes to None). If the mouse coordinates are not within
              range of a datapoint, the function will also try to destroy
              the dialog. This way, it is ensured that the dialog gets
              always closed when the mouse moves away from a
              datapoint.
        """
        if event.inaxes:
            try: self.tltp.Destroy()
            except: None
            # Get coordinates on plot
            x, y = event.xdata, event.ydata
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
                if (x >= (self.Input.Concentrations[i]*1000000*0.9) and
                    x <= (self.Input.Concentrations[i]*1000000*1.1)):
                    # for the y axis, we have to adjust absolute
                    if (y >= (self.Input.loc[str_YData][i] - within) and
                        y <= (self.Input.loc[str_YData][i] + within)):
                        str_Tooltip = ("x: "
                                      + str(self.Input.Concentrations[i])
                                      + " M\ny: " + str(self.Input.loc[str_YData][i])
                                      + str_Unit)
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        self.SetFocus()
                        break
    
    # Function for clicking on points
    def ClickOnPoint(self, event):
        """
        Event handler.
        Includes or excludes the selected datapoint from the fit.
        """
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get selected datapoint:
        # Get index of point in picked series
        idx_Picked = event.ind[0]
        # Get picked series (included or excluded)
        flt_PickedConc =  self.dic_Doses[event.artist.get_label()][idx_Picked]
        # Find concentration, if matches, get index of datapoint:
        for idx in range(len(self.dose)):
            if self.dose[idx] == flt_PickedConc:
                idx_datapoint = idx
            
        # Get current sample and retrieve its dataseries

        # exclude datapoint:
        # 1. First write value into lst_RawExcluded/lst_NormExcluded, write
        # np.nan into lst_Raw/lst_Norm
        if np.isnan(self.Input["Raw"][idx_datapoint]) == False:
            # First check if there are enough datapoints left to perform a fit
            counter = 0
            for i in range(len(self.Input["Raw"])):
                if np.isnan(self.Input["Raw"][i]) == False:
                    counter += 1
            if counter > 5:
                # Selected datapoint IS NOT excluded -> copy it into excluded
                # series and set value in data series to nan
                self.Input["RawExcluded"][idx_datapoint] = self.Input["Raw"][idx_datapoint]
                self.Input["Raw"][idx_datapoint] = np.nan
                self.Input["NormExcluded"][idx_datapoint] = self.Input["Norm"][idx_datapoint]
                self.Input["Norm"][idx_datapoint] = np.nan
            else:
                wx.MessageBox("You are trying to remove too many points."
                              + "Attempting to fit with less than five points"
                              + " will not produce a reliable fit.",
                              caption = "Not enough points left",
                              style = wx.OK|wx.ICON_INFORMATION)
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

    def IncludeExclude(self, str_Show):
        """
        Prepares value lists for plotting that are free of np.nan
        values.
        """
        # Ensure we have a list of ALL responses, included or excluded
        response_all = []
        for idx in range(len(self.Input[str_Show])):
            if not pd.isna(self.Input[str_Show][idx]) == True:
                response_all.append(self.Input[str_Show][idx])
            else:
                response_all.append(self.Input[str_Show+"Excluded"][idx])

        # Prepare lists that only contain excluded or included
        # points, no np.nan values.
        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for point in range(len(self.Input[str_Show])):
            if not pd.isna(self.Input[str_Show][point]) == True:
                dose_incl.append(self.dose[point])
                resp_incl.append(response_all[point])
                sem_incl.append(self.Input[str_Show+"SEM"][point])
            else:
                dose_excl.append(self.dose[point])
                resp_excl.append(response_all[point])
                sem_excl.append(self.Input[str_Show+"SEM"][point])

        #return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl

        return {"dose_incl":dose_incl, "resp_incl":resp_incl, "sem_incl":sem_incl,
                "dose_excl":dose_excl, "resp_excl":resp_excl, "sem_excl":sem_excl}

    def PlotToClipboard(self,event):
        """
        Event handler.
        Calls shared function to copy plot image to clipboard.
        """
        shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        """
        Event handler.
        Calls shared function to copy plot image to clipboard.
        """
        shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        """
        Event handler.
        Writes plotted data to pandas dataframe and from there
        to clipboard.
        """
        pd.DataFrame({"Concentration[uM]":self.Input["Concentrations"],
                      "NormalisedMean":self.Input["Norm"],
                      "NormalisedSEM":self.Input["NormSEM"],
                      "FreeFit":self.Input["NormFitFree"],
                      "ConstrainedFit":self.Input["NormFitConst"]}
                      ).to_clipboard(header=True, index=False)


############################################################################
##                                                                        ##
##    ##  ##  ######   ####   ######          ##    ##   ####   #####     ##
##    ##  ##  ##      ##  ##    ##            ########  ##  ##  ##  ##    ##
##    ######  ######  ######    ##    ######  ## ## ##  ######  #####     ##
##    ##  ##  ##      ##  ##    ##            ##    ##  ##  ##  ##        ##
##    ##  ##  ######  ##  ##    ##            ##    ##  ##  ##  ##        ##
##                                                                        ##
############################################################################

class HeatmapPanel(wx.Panel):
    def __init__(self, parent, size, tabname, title = u"Plate Raw Data",
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = u"Replicate 1", ylabel = u"Value", detailplot = False,
                 summaryplot = False, buttons = False):
        wx.Panel.__init__(self, parent,size=size)#wx.Size(600,450))
        self.Tabname = tabname
        self.detailplot = detailplot
        self.YLabel = ylabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.05, right=0.9, top=0.85 , bottom=0.05)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = title
        self.TitlePosition = titlepos
        self.TitleFontSize = titlefontsize
        self.Cycle = 0
        self.PlateIndex = 0
        self.PairedHeatmaps = []
        self.SummaryPlot = summaryplot
        self.Data = None
        self.vmax = None
        self.vmin = None

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.PlotToClipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.PlotToPNG)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        # Data Quality
        self.szr_DataQuality = wx.BoxSizer(wx.VERTICAL)
        self.szr_DataQuality.Add((0, 35), 0, wx.EXPAND, 5)
        self.szr_Wells = wx.FlexGridSizer(8,3,0,0)
        self.lbl_DisplayPlot = wx.StaticText(self, wx.ID_ANY, u"Plate details:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DisplayPlot, 0, wx.ALL, 5)
        self.lbl_SEM = wx.StaticText(self, wx.ID_ANY, chr(177)+u"SEM", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SEM, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BufferWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Buffer only wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWellsLabel, 0, wx.ALL, 5)
        self.lbl_BufferWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BufferWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_SolventWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Solvent wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWellsLabel, 0, wx.ALL, 5)
        self.lbl_SolventWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_SolventWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ControlWellsLabel = wx.StaticText(self, wx.ID_ANY, u"Control compound wells: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWellsLabel, 0, wx.ALL, 5)
        self.lbl_ControlWells = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ControlWells, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_BCLabel = wx.StaticText(self, wx.ID_ANY, u"Buffer to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BCLabel, 0, wx.ALL, 5)
        self.lbl_BC = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_BC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_DCLabel = wx.StaticText(self, wx.ID_ANY, u"Solvent to control: ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DCLabel, 0, wx.ALL, 5)
        self.lbl_DC = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_DC, 0, wx.ALL, 5)
        self.szr_Wells.Add((-1,-1), 0, wx.ALL, 5)
        self.lbl_ZPrimeMeanLabel = wx.StaticText(self, wx.ID_ANY, u"Z"+chr(39)+u" (mean): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMeanLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMean = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMean, 0, wx.ALL, 5)
        self.btn_ZPrimeMean = btn.InfoButton(self, u"UltraLight", tooltip=u"How is Z' calculated?")
        self.btn_ZPrimeMean.ImagePath = os.path.join(self.Tabname.parent.str_OtherPath, "ZPrimeMeanToolTip.png")
        self.btn_ZPrimeMean.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.szr_Wells.Add(self.btn_ZPrimeMean, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedianLabel = wx.StaticText(self, wx.ID_ANY, u"Z"+chr(39)+u" (median): ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedianLabel, 0, wx.ALL, 5)
        self.lbl_ZPrimeMedian = wx.StaticText(self, wx.ID_ANY, u"TBA", wx.DefaultPosition, wx.DefaultSize, 0)
        self.szr_Wells.Add(self.lbl_ZPrimeMedian, 0, wx.ALL, 5)
        self.btn_ZPrimeMedian = btn.InfoButton(self, u"UltraLight", tooltip=u"How is Z'(median) calculated?")
        self.btn_ZPrimeMedian.ImagePath = os.path.join(self.Tabname.parent.str_OtherPath, "ZPrimeMedianToolTip.png")
        self.btn_ZPrimeMedian.Bind(wx.EVT_BUTTON, tt.CallInfoToolTip)
        self.szr_Wells.Add(self.btn_ZPrimeMedian, 0, wx.ALL, 5)
        self.szr_DataQuality.Add(self.szr_Wells,0,wx.ALL,0)
        self.lin_BelowDetails = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.szr_DataQuality.Add(self.lin_BelowDetails, 0, wx.EXPAND|wx.ALL, 5)
        self.btn_PlateQualityToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
        self.szr_DataQuality.Add(self.btn_PlateQualityToClipboard, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
    
        self.btn_PlateQualityToClipboard.Bind(wx.EVT_BUTTON, self.PlateQualityToClipboard)

        self.szr_Surround.Add(self.szr_DataQuality, 0, wx.ALL, 0)

        
        self.SetSizer(self.szr_Surround)
        self.Fit()

    def Draw(self):
        """
        "Value" is whatever gets shown. Can be raw data, Tm, deltaTm, reaction rate, etc.
        """
        self.figure.clear()
        self.axes = self.figure.add_subplot()

        # Title, axes, grid
        self.axes.set_title(self.Title, fontsize=self.TitleFontSize, y=self.TitlePosition)
        self.axes.grid(which="minor", color="black", linestyle="-", linewidth=1)
        # Rows and columns
        self.Plateformat = len(self.Data["Value"]) # Save plateformat as property of plot
        self.int_Rows = pf.plate_rows(self.Plateformat)
        self.int_Columns = pf.plate_columns(self.Plateformat)
        self.lst_Rows = []
        for r in range(self.int_Rows):
            if r < 26:
                self.lst_Rows.append(chr(65+r))
            else:
                self.lst_Rows.append("A" + chr(65+(r-25)))
        self.lst_Major_X = range(self.int_Columns)
        self.lst_Major_Y = range(self.int_Rows)
        self.lst_Columns = range(1,self.int_Columns+1)
        
        if self.Plateformat <= 96:
            self.int_FontSize = 8
        elif self.Plateformat == 384:
            self.int_FontSize = 5
        elif self.Plateformat == 1536:
            self.int_FontSize = 3

        self.SampleIDs = self.Data["SampleID"].tolist()
        # Transpose plate data into format required for heatmap:
        self.PlateData = df.make_list(self.int_Rows,[])
        lst_PlateData = self.Data["Value"].tolist()
        for row in range(self.int_Rows):
            self.PlateData[row] = lst_PlateData[row*self.int_Columns:(row+1)*self.int_Columns]
        # Determine vmax and vmin for heatbar, if not given:
        if self.vmax == None:
            self.vmax = np.nanmax(lst_PlateData)
        if self.vmin == None:
            self.vmin = np.nanmin(lst_PlateData)
        # create heatmap
        im = self.axes.imshow(self.PlateData, cmap="PuOr", picker=True, vmax=self.vmax, vmin=self.vmin)

        # X axis (numbers)
        self.axes.set_xticks(self.lst_Major_X) # Major ticks
        self.axes.set_xticks(self.minor_ticks(self.lst_Major_X), minor=True) # Minor ticks
        self.axes.set_xticklabels(self.lst_Columns)
        self.axes.tick_params(axis="x", labelsize=self.int_FontSize)
        # Y axis (letters)
        self.axes.set_yticks(self.lst_Major_Y) # Major ticks
        self.axes.set_yticks(self.minor_ticks(self.lst_Major_Y), minor=True) # Minor ticks
        self.axes.set_yticklabels(self.lst_Rows)
        self.axes.tick_params(axis="y", labelsize=self.int_FontSize)
        self.axes.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
        self.axes.tick_params(which="minor", bottom=False, left=False)

        # Colour bar
        # Change size of colorbar: https://matplotlib.org/mpl_toolkits/axes_grid/users/overview.html#axesdivider
        divider = make_axes_locatable(self.axes)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cbar = self.axes.figure.colorbar(im, cax=cax)
        cbar.ax.set_ylabel(self.YLabel, rotation=-90, va="bottom")
        cbar.ax.tick_params(labelsize=8)
        # Add event handlers
        self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("axes_leave_event", self.DestroyToolTip)
        self.canvas.mpl_connect("figure_leave_event", self.DestroyToolTip)
        self.Bind(wx.EVT_KILL_FOCUS, self.DestroyToolTip)
        if self.detailplot == True:    
            self.canvas.mpl_connect("pick_event", self.OnClick)
        self.canvas.draw()
        self.Backup = self.canvas.copy_from_bbox(self.figure.bbox)
        self.dic_Highlights = {}
        self.dic_WellMarker = {}

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.Tabname.PopupMenu(PlotContextMenu(self))

    def DestroyToolTip(self, event):
        try: self.tltp.Destroy()
        except: None
        for i in range(self.int_Highlights):
            try: self.dic_Highlights[i].remove
            except: None
        for heatmap in self.PairedHeatmaps:
            for i in range(len(heatmap.dic_Highlights)):
                try: heatmap.dic_Highlights[i].remove()
                except: None
            heatmap.canvas.blit()
            heatmap.canvas.restore_region(heatmap.Backup)

        self.canvas.blit()
        self.canvas.restore_region(self.Backup)

        if len(self.dic_WellMarker) > 0:
            for i in range(len(self.dic_WellMarker)):
                self.axes.add_patch(self.dic_WellMarker[i])
                self.axes.draw_artist(self.dic_WellMarker[i])

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
        # Destroy previous tooltip and highlight
        self.dic_Highlights = {}
        self.int_Highlights = 0
        self.DestroyToolTip(None)
        if event.inaxes:
            # Get coordinates on plot
            int_Columns = pf.plate_columns(self.Plateformat)
            int_Rows = pf.plate_rows(self.Plateformat)
            x, y = int(round(event.xdata,0)), int(round(event.ydata,0))
            if x < int_Columns and y < int_Rows:
                idx_Well = x + (int_Columns * y)
                str_Tooltip = pf.index_to_well(idx_Well+1, self.Plateformat) # index_to_well takes the well index to base 1, not 0!
                if self.SampleIDs[idx_Well] != "" and pd.isna(self.SampleIDs[idx_Well]) == False:
                    str_Sample = self.SampleIDs[idx_Well]
                    if len(str_Sample) > 40:
                        str_Sample = str_Sample[:40] + "..."
                    str_Tooltip += ": " + self.SampleIDs[idx_Well]
                if hasattr(self.Tabname, "dfr_Layout") == True:
                    str_WellType = self.Tabname.dfr_Layout.loc[0,"WellType"][idx_Well]
                    if str_WellType == "s":
                        str_Tooltip += " (Sample)"
                    elif str_WellType == "r":
                        str_Tooltip += " (Solvent reference)"
                    elif str_WellType == "c":
                        str_Tooltip += " (Control compound: " + self.Tabname.dfr_Layout.loc[0,"ControlID"][idx_Well] + ")"
                    else:
                        str_Tooltip += ""
                self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                self.tltp.Show()

                lst_Wells = []
                self.int_Highlights = 0
                if self.SampleIDs[idx_Well] != "":
                    for sample in range(len(self.SampleIDs)):
                        if self.SampleIDs[sample] == self.SampleIDs[idx_Well]:
                            lst_Wells.append(pf.index_to_row_col(sample,int_Rows,int_Columns))
                            self.int_Highlights += 1
                # Highlight well(s):
                # Ensure the original well is always on the list, even if there are no sample IDs
                tpl_Well = pf.index_to_row_col(idx_Well,int_Rows,int_Columns)
                if not tpl_Well in lst_Wells:
                    lst_Wells.append(tpl_Well)
                    self.int_Highlights += 1
                for i in range(self.int_Highlights):
                    self.dic_Highlights[i] = patches.Rectangle((lst_Wells[i][1]-0.5,lst_Wells[i][0]-0.5),1,1,ec="white",fill=False)
                    self.axes.add_patch(self.dic_Highlights[i])
                    self.axes.draw_artist(self.dic_Highlights[i])
                self.canvas.blit()
                # Add wells on paired heatmaps:
                for heatmap in self.PairedHeatmaps:
                    heatmap.dic_Highlights = {}
                    for i in range(self.int_Highlights):
                        heatmap.dic_Highlights[i] = patches.Rectangle((lst_Wells[i][1]-0.5,lst_Wells[i][0]-0.5),1,1,ec="white",fill=False)
                        heatmap.axes.add_patch(heatmap.dic_Highlights[i])
                        heatmap.axes.draw_artist(heatmap.dic_Highlights[i])
                    heatmap.canvas.blit()

                self.SetFocus()

    def OnClick(self, event):
        if self.detailplot == True:
            x = int(round(event.mouseevent.xdata,0))
            y = int(round(event.mouseevent.ydata,0))
            self.Tabname.UpdateDetailPlot(self.Tabname, x, y)
            try:
                self.dic_WellMarker[0].remove()
                self.canvas.blit()
                self.canvas.restore_region(self.Backup)
            except:
                None
            self.dic_WellMarker = {}
            self.dic_WellMarker[0] = patches.Rectangle((x-0.5,y-0.5),1,1,ec="yellow",fill=False,linewidth=1)
            self.axes.add_patch(self.dic_WellMarker[0])
            self.axes.draw_artist(self.dic_WellMarker[0])
            self.canvas.blit()

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        shared_PlotToPNG(self)
    
    def minor_ticks(self, lst_Major):
        lst_Minor = []
        for i in range(len(lst_Major)):
            lst_Minor.append(lst_Major[i] + 0.5)
        return lst_Minor

    def DataToClipboard(self, event):
        dfr_Clipboard = pd.DataFrame(columns=self.lst_Columns, index=self.lst_Rows)
        for row in range(len(self.PlateData)):
            for col in range(len(self.PlateData[row])):
                dfr_Clipboard.iloc[row,col] = self.PlateData[row][col]
        dfr_Clipboard.to_clipboard(header=True, index=True)

    def PlateQualityToClipboard(self, event):
        idx_Plate = self.PlateIndex
        pd.DataFrame({"BufferMean":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0],2)],
            "BufferSEM":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferSEM",0],2)],
            "SolventMean":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0],2)],
            "SolventSEM":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventSEM",0],2)],
            "ControlMean":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ControlSEM":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlSEM",0],2)],
            "BufferToControl":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["BufferMean",0]/self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "SolventToControl":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["SolventMean",0]/self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ControlMean",0],2)],
            "ZPrimeMean":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMean",0],3)],
            "ZPrimeMedian":[round(self.Tabname.dfr_AssayData.loc[idx_Plate,"References"].loc["ZPrimeMedian",0],3)]}).to_clipboard(header=True, index=False)

##################################################################
##                                                              ##
##     #####   #####   ####   ######  ######  ######  #####     ##
##    ##      ##      ##  ##    ##      ##    ##      ##  ##    ##
##     ####   ##      ######    ##      ##    ####    #####     ##
##        ##  ##      ##  ##    ##      ##    ##      ##  ##    ##
##    #####    #####  ##  ##    ##      ##    ######  ##  ##    ##
##                                                              ##
##################################################################

# built on https://stackoverflow.com/questions/10737459/embedding-a-matplotlib-figure-inside-a-wxpython-panel
class ScatterPlotPanel(wx.Panel):
    def __init__(self, parent, size, tabname, title,
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = "", ylabel = "", detailplot = False,
                 summaryplot = False, buttons = False,
                 threshold = 80, lines = [], limits = []):
        wx.Panel.__init__(self, parent,size=size)
        self.tabname = tabname
        self.detailplot = detailplot
        self.threshold = threshold
        self.lines = lines
        self.limits = limits
        self.YLabel = ylabel
        self.figure = Figure(figsize=(size[0]/100,size[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.axes = self.figure.add_subplot()
        self.figure.subplots_adjust(left=0.10, right=0.99, top=0.90 , bottom=0.15)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.Title = title

        # Arranging GUI elements
        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.szr_Plot = wx.BoxSizer(wx.VERTICAL)
        # Plot and buttons
        self.szr_Plot.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        if buttons == True:
            self.szr_ExportButtons = wx.BoxSizer(wx.HORIZONTAL)
            self.btn_ToClipboard = btn.CustomBitmapButton(self, u"Clipboard", 0, (130,25))
            self.btn_ToClipboard.Bind(wx.EVT_BUTTON, self.PlotToClipboard)
            self.szr_ExportButtons.Add(self.btn_ToClipboard, 0, wx.ALL, 5)
            self.btn_ToPNG = btn.CustomBitmapButton(self, u"ExportToFile", 0, (104,25))
            self.btn_ToPNG.Bind(wx.EVT_BUTTON, self.PlotToPNG)
            self.szr_ExportButtons.Add(self.btn_ToPNG, 0, wx.ALL, 5)
            self.szr_Plot.Add(self.szr_ExportButtons, 0, wx.EXPAND, 0)
        self.szr_Surround.Add(self.szr_Plot, 0, wx.ALL, 0)
        self.dfr_Input = None

    def Draw(self):
        # Initialise - some redundancy with init because this function is reused when re-drawing the graph for a new dtaset
        self.lst_SampleIDs = self.dfr_Input["SampleID"].tolist()
        self.int_Samples = len(self.lst_SampleIDs)
        self.lst_Value = self.dfr_Input["Value"].tolist()
        self.lst_ValueSEM = self.dfr_Input["ValueSEM"].tolist()
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.Title)
        # Need to process input for above and below threshold
        self.lst_BelowThreshold = []
        self.lst_AboveThreshold = []
        self.lst_Below_SEM = []
        self.lst_Above_SEM = []
        for i in range(self.int_Samples):
            if float(self.lst_Value[i]) > self.threshold:
                self.lst_AboveThreshold.append(self.lst_Value[i])
                self.lst_Above_SEM.append(self.lst_ValueSEM[i])
                self.lst_BelowThreshold.append(np.nan)
                self.lst_Below_SEM.append(np.nan)
            else:
                self.lst_AboveThreshold.append(np.nan)
                self.lst_Above_SEM.append(np.nan)
                self.lst_BelowThreshold.append(self.lst_Value[i])
                self.lst_Below_SEM.append(self.lst_ValueSEM[i])
        self.axes.set_xlabel("Compounds")
        self.axes.scatter(range(self.int_Samples), self.lst_AboveThreshold, marker="o", label="Above threshold", color="#aa4499", s=10, picker=3)
        self.axes.errorbar(range(self.int_Samples), self.lst_AboveThreshold, yerr=self.lst_Above_SEM, fmt="none", color="#aa4499", elinewidth=0.3, capsize=2)
        self.axes.scatter(range(self.int_Samples), self.lst_BelowThreshold, marker="o", label="Below threshold", color="#44b59a", s=10, picker=3)
        self.axes.errorbar(range(self.int_Samples), self.lst_BelowThreshold, yerr=self.lst_Below_SEM, fmt="none", color="#44b59a", elinewidth=0.3, capsize=2)
        if len(self.lines) > 0:
            self.axes.axhline(y=self.lines[0], xmin=0, xmax=1, linestyle="--", color="black", linewidth=0.5) # horizontal line
            self.axes.axhline(y=self.lines[1], xmin=0, xmax=1, linestyle="--", color="grey", linewidth=0.5) # horizontal line
        self.axes.set_ylabel(self.YLabel)
        if len(self.limits) > 0:
            self.axes.set_ylim(self.limits)
        self.axes.legend()
        # Connect event handlers
        self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("axes_leave_event", self.DestroyToolTip)
        self.canvas.mpl_connect("figure_leave_event", self.DestroyToolTip)
        self.Bind(wx.EVT_KILL_FOCUS, self.DestroyToolTip)
        if self.detailplot == True:
            self.canvas.mpl_connect("pick_event", self.OnClick)
        self.canvas.draw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        shared_PlotToPNG(self)

    def DestroyToolTip(self, event):
        try: self.tltp.Destroy()
        except: None

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
            evt_x, evt_y = event.xdata, event.ydata
            lst_XLimits = self.axes.get_xlim()
            within_x = (lst_XLimits[1] - lst_XLimits[0])/100 * 0.5
            lst_YLimits = self.axes.get_ylim()
            within_y = (lst_YLimits[1] - lst_YLimits[0])/100 * 1.5
            for x in range(self.int_Samples):
                # For the x axis (log scale), we have to adjust relative
                if evt_x >= (x - within_x) and evt_x <= (x + within_x) and pd.isna(self.lst_Value[x]) == False:
                    # for the y axis, we have to adjust absolute
                    y = round(self.lst_Value[x])
                    str_SampleID = self.lst_SampleIDs[x]
                    if evt_y >= (y - within_y) and evt_y <= (y + within_y):
                        try: self.tltp.Destroy()
                        except: None
                        str_Tooltip = str_SampleID + "\n%I: " + str(y)
                        self.tltp = tt.dlg_ToolTip(self, str_Tooltip)
                        self.tltp.Show()
                        break
                    else:
                        try: self.tltp.Destroy()
                        except: None
                else:
                    try: self.tltp.Destroy()
                    except: None

    def OnClick(self, event):
        # check if event gives valid result:
        N = len(event.ind)
        if not N: return True
        # Get plate and sample index:
        idx_Sample = event.ind[0]
        self.tabname.UpdateDetailPlot(0, 0, idx_Sample, self.Plateformat)

    def DataToClipboard(self, event):
        pd.DataFrame({"SampleIDs":self.lst_SampleIDs,
            "AboveThreshold":self.lst_AboveThreshold,
            "AboveSEM":self.lst_Above_SEM,
            "BelowThreshold":self.lst_BelowThreshold,
            "BelowSEM":self.lst_Below_SEM}).to_clipboard(header=True, index=False)

######################################################################################
##                                                                                  ##
##    #####   ######  #####   ##      ##   #####   ####   ######  ######   #####    ##
##    ##  ##  ##      ##  ##  ##      ##  ##      ##  ##    ##    ##      ##        ##
##    #####   ####    #####   ##      ##  ##      ######    ##    ####     ####     ##
##    ##  ##  ##      ##      ##      ##  ##      ##  ##    ##    ##          ##    ##
##    ##  ##  ######  ##      ######  ##   #####  ##  ##    ##    ######  #####     ##
##                                                                                  ##
######################################################################################

class ReplicateCorrelation(wx.Panel):
    """
    Plotting replicate corellation between two replicates.
    Replicate 1 on horizontal axis, replicate 2 on vertical axis.
    Also displays fit for replicate corellation and Rsquare value.
    """
    def __init__(self, parent, size, tabname, title = u"Replicate Corellation",
                 titlepos = 1.075, titlefontsize = 14,
                 xlabel = u"Replicate 1", ylabel = u"Replicate 2", detailplot = False,
                 summaryplot = False, buttons = False):
        self.tabname = tabname
        wx.Panel.__init__(self, parent,size=size)#=wx.Size(550,325))
        self.PanelSize = size
        self.Top = 1-30/size[1]
        self.Bottom = 1-(30/self.PanelSize[1])-(350/self.PanelSize[1])
        self.XLabel = xlabel
        self.YLabel = ylabel
        self.Title = title
        self.figure = Figure(figsize=(self.PanelSize[0]/100,self.PanelSize[1]/100),dpi=100)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(title)
        self.figure.subplots_adjust(left=0.10, right=0.99, top=self.Top , bottom=self.Bottom)
        self.figure.set_facecolor(cs.BgUltraLightHex)
        self.SampleIDs = []
        self.Replicate1 = []
        self.Replicate2 = []
        self.Extremes = []
        self.RSquare = None
        self.Pearson = None

    def Draw(self):
        # Initialise - some redundancy with init because this function is reused when
        # re-drawing the graph for a new dataset
        # If the canvas already exists, we are updating the plot. Therefore, the old needs
        # deleting.
        self.figure.clear()
        self.axes = self.figure.add_subplot()
        self.axes.set_title(self.Title)
        self.axes.scatter(self.Replicate1, self.Replicate2, marker="o", label="Replicates", color="#44b59a", s=10, picker=1)#, edgecolors ="black")
        self.axes.plot(self.Extremes, self.Fit, label="Replicate correlation (% solvent reference)")
        self.axes.set_xlabel(self.XLabel)
        self.axes.set_ylabel(self.YLabel)
        #self.axes.legend()
        if not self.RSquare == None:
            str_RSquare = u"R" + chr(178) + " = " + str(round(self.RSquare,4))
            self.axes.annotate(str_RSquare,
                xy=(0,0), xycoords="data", # datapoint that is annotated
                xytext=(440,30), textcoords="axes pixels") # position of annotation
        if not self.Pearson == None:
            str_Pearson = u"p = " + str(round(self.Pearson,4))
            self.axes.annotate(str_Pearson,
                xy=(0,0), xycoords="data", # datapoint that is annotated
                xytext=(440,10), textcoords="axes pixels") # position of annotation

        # Connect event handlers
        self.canvas.mpl_connect("pick_event", self.OnClick)
        self.canvas.mpl_connect("motion_notify_event", self.CustomToolTip)
        self.canvas.mpl_connect("button_press_event", self.RightClick)
        self.canvas.mpl_connect("figure_leave_event", self.LeaveFigure)
        self.canvas.mpl_connect("axes_leave_event", self.LeaveFigure)
        self.canvas.draw()

    def RightClick(self, event):
        if event.button is MouseButton.RIGHT:
            self.tabname.PopupMenu(PlotContextMenu(self))

    def LeaveFigure(self, event):
        try: self.tltp.Destroy()
        except: None

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
            idx_Plate = self.tabname.lbc_Conditions.GetFirstSelected()
            idx_XCondition = (self.tabname.lbc_Conditions.GetItemText(idx_Plate,0), self.tabname.lbc_Conditions.GetItemText(idx_Plate,1),"R1")
            idx_YCondition = (self.tabname.lbc_Conditions.GetItemText(idx_Plate,0), self.tabname.lbc_Conditions.GetItemText(idx_Plate,1),"R2")
            lst_YLimits = self.axes.get_ylim()
            lst_XLimits = self.axes.get_xlim()
            within_Y = (lst_YLimits[1] - lst_YLimits[0])/100 * 0.5
            within_X = (lst_XLimits[1] - lst_XLimits[0])/100 * 0.5
            int_PlateFormat = len(self.tabname.dfr_DataStructure.loc[idx_YCondition,"Normalised"]["Normalised"])
            for i in range(int_PlateFormat):
                # For the x axis (log scale), we have to adjust relative
                if x >= (self.Replicate1[i]-within_X) and x <= (self.Replicate1[i]+within_X):
                    # for the y axis, we have to adjust absolute
                    value = self.Replicate2[i]
                    str_SampleID = self.SampleIDs[i]
                    if len(str_SampleID) > 40:
                        str_SampleID = str_SampleID[:40] + "..."
                    str_Well = pf.index_to_well(i+1,int_PlateFormat) + ": " + str_SampleID
                    if y >= (value - within_Y) and y <= (value + within_Y):
                        try: self.tltp.Destroy()
                        except: None
                        self.tltp = tt.dlg_ToolTip(self, str_Well)
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
        if hasattr(self.tabname, "pnl_DetailPlot"):
            # Get global variables
            # check if event gives valid result:
            N = len(event.ind)
            if not N: return True
            # Get plate and sample index:
            idx_Sample = event.ind[0]
            idx_Plate = self.tabname.lbc_Plates.GetFirstSelected()
            # Draw fresh detail plot
            if hasattr(self.tabname, "pnl_DetailPlot"):
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
        shared_PlotToClipboard(self)

    def PlotToPNG(self,event):
        shared_PlotToPNG(self)

    def DataToClipboard(self, event):
        lst_Wells = []
        lst_SampleIDs = []
        lst_Replicate1 = []
        lst_Replicate2 = []
        for i in range(len(self.SampleIDs)):
            if pd.isna(self.Replicate1[i]) == False:
                lst_Wells.append(pf.index_to_well(i,len(self.SampleIDs)))
                lst_SampleIDs.append(self.SampleIDs[i])
                lst_Replicate1.append(self.Replicate1[i])
                lst_Replicate2.append(self.Replicate2[i])
        pd.DataFrame({"Well":lst_Wells,"SampleID":lst_SampleIDs,"Replicate 1 (% solvent reference)":lst_Replicate1,
            "Replicate 2 (% solvent reference)":lst_Replicate2}).to_clipboard(header=True, index=False)


######################################################################
##                                                                  ##
##    #####   ##       ####   ######   ####   #####   ##  #####     ##
##    ##  ##  ##      ##  ##    ##    ##      ##  ##  ##  ##  ##    ##
##    #####   ##      ##  ##    ##    ## ###  #####   ##  ##  ##    ##
##    ##      ##      ##  ##    ##    ##  ##  ##  ##  ##  ##  ##    ##
##    ##      ######   ####     ##     ####   ##  ##  ##  #####     ##
##                                                                  ##
######################################################################

class PlotGridEPDR(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(900,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_PlottingProgress):
        self.figure.clear()
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    if dfr_Input.loc[count,"Show"] == 0:
                        str_Y = "Averages"
                        str_YSEM = "RawSEM"
                        str_YExcluded = "RawExcluded"
                        str_FitY = "RawFit"
                        str_FitPars = "RawFitPars"
                        str_FitCI = "RawFitCI"
                        str_YLabel = "Signal in A.U."
                    elif dfr_Input.loc[count,"Show"] == 1:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitFree"
                        str_FitPars = "NormFitFreePars"
                        str_FitCI = "NormFitFreeCI"
                        str_YLabel = "Per-cent hinhibition"
                    else:
                        str_Y = "Norm"
                        str_YSEM = "NormSEM"
                        str_YExcluded = "NormExcluded"
                        str_FitY = "NormFitConst"
                        str_FitPars = "NormFitConstPars"
                        str_FitCI = "NormFitConstCI"
                        str_YLabel = "Per-cent hinhibition"
                    self.ax = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Dose = df.moles_to_micromoles(dfr_Input.loc[count,"Concentrations"])
                    dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl = self.IncludeExclude(lst_Dose, dfr_Input.loc[count,str_Y], dfr_Input.loc[count,str_Y+"SEM"],dfr_Input.loc[count,str_YExcluded])
                    if dfr_Input.loc[count,"DoFit"] == True:
                        self.ax.plot(lst_Dose, dfr_Input.loc[count,str_FitY], label="Fit", color=cs.TMRose_Hex)
                        str_IC50 = "IC50: " + df.write_IC50(dfr_Input.loc[count,str_FitPars][3],dfr_Input.loc[count,"DoFit"],dfr_Input.loc[count,str_FitCI][3])
                        self.ax.annotate(str_IC50, xy=(5, 95), xycoords="axes pixels", size=int_LabelSize)
                    if len(resp_incl) > 0:
                        self.ax.scatter(dose_incl, resp_incl, marker=".", label="Data", color=cs.TMBlue_Hex)
                        self.ax.errorbar(dose_incl, resp_incl, yerr=sem_incl, fmt="none", color=cs.TMBlue_Hex)
                    if len(resp_excl) > 0:
                        self.ax.scatter(dose_excl, resp_excl, marker=".", label="Excluded", color=cs.BgMediumHex)
                        try:
                            self.ax.errorbar(dose_excl, resp_excl, yerr=sem_excl, fmt="none", color=cs.BgMediumHex)
                        except:
                            print(dose_excl)
                            print(resp_excl)
                    # Sub plot title
                    self.ax.set_title(dfr_Input.loc[count,"SampleID"])
                    self.ax.axes.title.set_size(int_TitleSize)
                    # X Axis
                    self.ax.set_xlabel("Concentration [" + chr(181) +"M]")
                    self.ax.xaxis.label.set_size(int_LabelSize)
                    self.ax.set_xscale("log")
                    self.ax.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.ax.yaxis.label.set_size(int_LabelSize)
                    self.ax.set_ylabel(str_YLabel)
                    self.ax.tick_params(axis="y", labelsize=int_LabelSize)
                    self.ax.set_ylim([-20,120])
                    # Legend
                    #self.ax.legend(fontsize=int_LabelSize)
                    dlg_PlottingProgress.gauge.SetValue(int((count/int_Samples)*200))
                count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def IncludeExclude(self, dose, resp, sem, resp_excl):

        # Ensure we have a list of ALL responses, included or excluded
        resp_all = []
        for r in range(len(resp)):
            if not pd.isna(resp[r]) == True:
                resp_all.append(resp[r])
            else:
                resp_all.append(resp_excl[r])

        dose_incl = []
        resp_incl = []
        sem_incl = []
        dose_excl = []
        resp_excl = []
        sem_excl = []
        for r in range(len(resp)):
            if not pd.isna(resp[r]) == True:
                dose_incl.append(dose[r])
                resp_incl.append(resp_all[r])
                sem_incl.append(sem[r])
            else:
                dose_excl.append(dose[r])
                resp_excl.append(resp_all[r])
                sem_excl.append(sem[r])
        
        return dose_incl, resp_incl, sem_incl, dose_excl, resp_excl, sem_excl    

    def PlotToClipboard(self):#,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self):
        shared_PlotToPNG(self)

class PlotGridDSF(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1200,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_PlottingProgress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.ax = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Temp = dfr_Input.loc[count,"Temp"]
                    self.ax.plot(lst_Temp, dfr_Input.loc[count,"Norm"], label="Fluorescence", color="#872154")
                    #self.ax.plot(lst_Temp, dfr_Input.loc[count,"RawDeriv"], label="Fit", color="#ddcc77")
                    str_Tm = str(round(dfr_Input.loc[count,"NormInflections"][0],1)) + chr(176) + "C"
                    self.ax.annotate(str_Tm, xy=(5, 90), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.ax.set_title(dfr_Input.loc[count,"SampleID"])
                    self.ax.axes.title.set_size(int_TitleSize)
                    # X Axis
                    self.ax.set_xlabel("Temperature ("+ chr(176) + "C)")
                    self.ax.xaxis.label.set_size(int_LabelSize)
                    self.ax.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.ax.yaxis.label.set_size(int_LabelSize)
                    self.ax.set_ylabel("Norm. fluorescence")
                    self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.ax.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.ax.set_ylim([-20,120])
                    # Legend
                    #self.ax.legend(fontsize=int_LabelSize)
                    dlg_PlottingProgress.gauge.SetValue((count/int_Samples)*200)
                count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self):
        shared_PlotToPNG(self)

class PlotGridNDSF(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1100,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # can"t do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_PlottingProgress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.ax = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    lst_Temp = dfr_Input.loc[count,"Temp"]
                    #if dfr_Input.loc[count,"DoFit"] == True:
                    #self.ax.plot(lst_Temp, dfr_Input.loc[count,"Ratio"], label="Ratio", color="#872154")
                    lst_RatioDeriv = dfr_Input.loc[count,"RatioDeriv"][20:(len(lst_Temp)-20)]/np.max(dfr_Input.loc[count,"RatioDeriv"][20:(len(lst_Temp)-20)])
                    self.ax.plot(lst_Temp[20:(len(lst_Temp)-20)], lst_RatioDeriv, label="RatioDeriv", color=cs.TMBlue_Hex)
                    lst_TempDeriv = dfr_Input.loc[count,"ScatteringDeriv"][20:(len(lst_Temp)-20)]/np.max(dfr_Input.loc[count,"ScatteringDeriv"][20:(len(lst_Temp)-20)])
                    self.ax.plot(lst_Temp[20:(len(lst_Temp)-20)], lst_TempDeriv, label="ScatterDeriv", color=cs.TMRose_Hex)
                    str_Tm = str(round(dfr_Input.loc[count,"RatioInflections"][0],1)) + chr(176) + "C"
                    self.ax.annotate(str_Tm, xy=(2, 89), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.ax.set_title(dfr_Input.loc[count,"SampleID"])
                    self.ax.axes.title.set_size(10)
                    # X Axis
                    self.ax.set_xlabel("Temperature ("+ chr(176) + "C)")
                    self.ax.xaxis.label.set_size(int_LabelSize)
                    self.ax.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.ax.yaxis.label.set_size(int_LabelSize)
                    self.ax.set_ylabel("Normalised derivative")
                    self.ax.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.ax.set_ylim([-20,120])
                    # Legend
                    #self.ax.legend(fontsize=int_LabelSize)
                    try:
                        dlg_PlottingProgress.gauge.SetValue((count/int_Samples)*200)
                    except:
                        None
                count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self):
        shared_PlotToPNG(self)

class PlotGridRATE(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(1200,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # cannot do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_PlottingProgress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        count = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > count: # Check whether we"re still in the dataframe
                    self.ax = self.figure.add_subplot(int_GridHeight,int_GridWidth,count+1)
                    if dfr_Input.loc[count,"DoLinFit"] == True:
                        self.ax.plot(dfr_Input.loc[count,"Time"], dfr_Input.loc[count,"Signal"], label="Signal in A.U.", color="#872154")
                        self.ax.plot(dfr_Input.loc[count,"LinFitTime"], dfr_Input.loc[count,"LinFit"], label="Linear", color="#ddcc77")
                        str_Rate = str(round(dfr_Input.loc[count,"LinFitPars"][0],1)) + " 1/s"
                        self.ax.annotate(str_Rate, xy=(90, 10), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.ax.set_title(dfr_Input.loc[count,"SampleID"])
                    self.ax.axes.title.set_size(10)
                    # X Axis
                    self.ax.set_xlabel("Time (s)")
                    self.ax.xaxis.label.set_size(int_LabelSize)
                    self.ax.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.ax.yaxis.label.set_size(int_LabelSize)
                    self.ax.set_ylabel("Signal")
                    self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.ax.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.ax.set_ylim([-20,120])
                    # Legend
                    #self.ax.legend(fontsize=int_LabelSize)
                    dlg_PlottingProgress.gauge.SetValue((count/int_Samples)*200)
                count += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)

    def PlotToPNG(self):
        shared_PlotToPNG(self)

class PlotGridDRTC(wx.Panel):
    def __init__(self,parent,total_height_px,total_height_inch, int_dpi):
        wx.Panel.__init__(self, parent, size=wx.Size(900,total_height_px))
        self.figure = Figure(figsize=(9,total_height_inch),dpi=int_dpi) # cannot do tightlayout
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.szr_Surround = wx.BoxSizer(wx.VERTICAL)
        self.szr_Surround.Add(self.canvas, 0, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.szr_Surround)
        self.Fit()
        self.figure.set_facecolor(cs.BgUltraLightHex)

    def Draw(self,int_Samples,dfr_Input,strTitle,int_GridHeight,int_GridWidth,hspace_ratio,bottom_ratio,top_ratio,
            total_height_px,int_SuperTitleSize,supertitle_ratio,int_TitleSize,int_LabelSize,dlg_PlottingProgress):
        # dfr_Input is the processed dataframe for one plate.
        # Set "supertitle" for figure:
        self.figure.suptitle(strTitle,fontsize=int_SuperTitleSize,x=0.5,y=supertitle_ratio)
        smpl = 0
        for i in range(int_GridHeight):
            for j in range(int_GridWidth):
                if int_Samples > smpl: # Check whether we"re still in the dataframe
                    self.ax = self.figure.add_subplot(int_GridHeight,int_GridWidth,smpl+1)
                    lst_Time = []
                    lst_IC50s = []
                    lst_Errors = []
                    if dfr_Input.loc[smpl,"DoFit"] == True:
                        for cycle in range(len(dfr_Input.loc[smpl,"NormMean"])):
                            if dfr_Input.loc[smpl,"Show"][cycle] == 1:
                                str_Fit = "Free"
                            else:
                                str_Fit = "Const"
                            lst_IC50s.append(dfr_Input.loc[smpl,"NormFit"+str_Fit+"Pars"][cycle][3])
                            lst_Errors.append(dfr_Input.loc[smpl,"NormFit"+str_Fit+"Errors"][cycle][3])
                            lst_Time.append(dfr_Input.loc[smpl,"Time"][cycle])
                        self.ax.plot(lst_Time, lst_IC50s, label="IC50 in uM", color="#872154")
                        self.ax.errorbar(lst_Time, lst_IC50s, yerr=lst_Errors,fmt="none", color="#872154", elinewidth=0.3, capsize=2)
                        # self.ax.plot(dfr_Input.loc[smpl,"LinFitTime"], dfr_Input.loc[smpl,"LinFit"], label="Linear", color="#ddcc77")
                        # str_Kinetics = str(round(dfr_Input.loc[smpl,"LinFitPars"][0],1)) + " 1/s"
                        # self.ax.annotate(str_Kinetics, xy=(5, 98), xycoords="axes pixels", size=int_LabelSize)
                    # Sub plot title
                    self.ax.set_title(dfr_Input.loc[smpl,"SampleID"])
                    self.ax.axes.title.set_size(10)
                    # X Axis
                    self.ax.set_xlabel("Time (s)")
                    self.ax.xaxis.label.set_size(int_LabelSize)
                    self.ax.tick_params(axis="x", labelsize=int_LabelSize)
                    # Y Axis
                    self.ax.yaxis.label.set_size(int_LabelSize)
                    self.ax.set_ylabel("IC50 ("+chr(181)+"M)")
                    self.ax.set_ylim(bottom=0)
                    self.ax.set_xlim(left=-50)
                    #self.ax.ticklabel_format(axis="y", style="scientific", scilimits=(-1,1))
                    self.ax.tick_params(axis="y", labelsize=int_LabelSize)
                    #self.ax.set_ylim([-20,120])
                    # Legend
                    #self.ax.legend(fontsize=int_LabelSize)
                    dlg_PlottingProgress.gauge.SetValue((smpl/int_Samples)*200)
                smpl += 1
        self.figure.subplots_adjust(left=0.06, right=0.99, top=top_ratio , bottom=bottom_ratio, wspace=0.4, hspace=0.6)
        self.Fit()

    def PlotToClipboard(self,event):
        shared_PlotToClipboard(self)
        
    def PlotToPNG(self):
        shared_PlotToPNG(self)

########################################################################################################
##                                                                                                    ##
##     #####   ####   ##    ##  ##    ##   ####   ##  ##    ######  ##  ##  ##  ##   #####   #####    ##
##    ##      ##  ##  ###  ###  ###  ###  ##  ##  ### ##    ##      ##  ##  ### ##  ##      ##        ##
##    ##      ##  ##  ########  ########  ##  ##  ######    ####    ##  ##  ######  ##       ####     ##
##    ##      ##  ##  ## ## ##  ## ## ##  ##  ##  ## ###    ##      ##  ##  ## ###  ##          ##    ##
##     #####   ####   ##    ##  ##    ##   ####   ##  ##    ##       ####   ##  ##   #####  #####     ##
##                                                                                                    ##
########################################################################################################

def shared_PlotToClipboard(Plot):
    """
    Copy the plot to clipboard.

    The window gets frozen, the background colour changed to white, the canvas redrawn, saved into a wx.BitmapDataObject, 
    then the canvas redrawn with the original background colour, then the window is thawed again.
    After that, the BitmapDataObject is handed to the clipboard.
    """
    Plot.Freeze()
    Plot.figure.set_facecolor(cs.WhiteHex)
    Plot.canvas.draw()
    # Convert plot to PIL image object, then to wx.BitmapObject
    pil_Plot = Image.frombytes("RGB", Plot.canvas.get_width_height(), Plot.canvas.tostring_rgb())
    int_Width, int_Height = pil_Plot.size
    Plot.obj_Plot = wx.BitmapDataObject()
    Plot.obj_Plot.SetBitmap(wx.Bitmap.FromBuffer(int_Width, int_Height, pil_Plot.tobytes()))
    Plot.figure.set_facecolor(cs.BgUltraLightHex)
    Plot.canvas.draw()
    # Hand to clipboard
    if wx.TheClipboard.Open():
        wx.TheClipboard.Clear()
        wx.TheClipboard.SetData(Plot.obj_Plot)
        wx.TheClipboard.Close()
    else:
        msg.ClipboardError(Plot)
    Plot.Thaw()

def shared_PlotToPNG(Plot):
    """
    Saves graph as PNG file using matplotlib's built in methods.
    
    First, the user is asked to specify a path via wx.FileDialog.

    The window gets frozen, the background colour changed to white, the canvas redrawn, saved to the specified path, 
    then the canvas redrawn with the original background colour, then the window is thawed again.
    After that, the BitmapDataObject is handed to the clipboard.
    """
    dlg_PlatePlotPNG = wx.FileDialog(Plot, "Save plot as", wildcard="PNG files(*.png)|*.png", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

    if dlg_PlatePlotPNG.ShowModal() == wx.ID_OK:
        str_SavePath = dlg_PlatePlotPNG.GetPath()
        # Check if str_SavePath ends in .png. If so, remove
        if str_SavePath[-1:-4] == ".png":
            str_SavePath = str_SavePath[:len(str_SavePath)]
        Plot.Freeze()
        Plot.figure.set_facecolor(cs.WhiteHex)
        Plot.canvas.draw()
        Plot.figure.savefig(str_SavePath, dpi=None, facecolor="w", edgecolor="w", orientation="portrait", format=None,
            transparent=False, bbox_inches=None, pad_inches=0.1)
        Plot.figure.set_facecolor(cs.BgUltraLightHex)
        Plot.canvas.draw()
        Plot.Thaw()

def SetZoomingTrue(Plot, event):
	Plot.Zooming = True
	print("fnord")

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

def ResetZoom(Plot, event):
	try:
		Plot.ZoomFrame.Destroy()
		Plot.ZoomFrame = None
	except:
		None
	Plot.Zooming = False
	Plot.Zoomed = False
	Plot.Draw()

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


######################################################################################################
##                                                                                                  ##
##     #####   ####   ##  ##  ######  ######  ##  ##  ######    ##    ##  ######  ##  ##  ##  ##    ##
##    ##      ##  ##  ### ##    ##    ##      ##  ##    ##      ###  ###  ##      ### ##  ##  ##    ##
##    ##      ##  ##  ######    ##    ####     ####     ##      ########  ####    ######  ##  ##    ##
##    ##      ##  ##  ## ###    ##    ##      ##  ##    ##      ## ## ##  ##      ## ###  ##  ##    ##
##     #####   ####   ##  ##    ##    ######  ##  ##    ##      ##    ##  ######  ##  ##   ####     ##
##                                                                                                  ##
######################################################################################################

class PlotContextMenu(wx.Menu):
    def __init__(self, parent, mouse_x = None, mouse_y = None):
        super(PlotContextMenu, self).__init__()
        """
        Context menu to copy, export and copy the data of plots.
        """
        real_path = os.path.realpath(__file__)
        dir_path = os.path.dirname(real_path)
        str_MenuIconsPath = dir_path + r"\menuicons"

        self.parent = parent

        # Only show magnify/rest zoom options if appropriate
        if hasattr(self.parent, "Zooming") == True:
            self.mi_Magnify = wx.MenuItem(self, wx.ID_ANY, u"Zoom", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_Magnify.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\Zoom.ico"))
            self.Append(self.mi_Magnify)
            self.Bind(wx.EVT_MENU, self.parent.SetZoomingTrue, self.mi_Magnify)

            self.mi_ResetZoom = wx.MenuItem(self, wx.ID_ANY, u"Reset zoom", wx.EmptyString, wx.ITEM_NORMAL)
            self.mi_ResetZoom.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\UnZoom.ico"))
            self.Append(self.mi_ResetZoom)
            self.Bind(wx.EVT_MENU, self.parent.ResetZoom, self.mi_ResetZoom)

        if hasattr(self.parent, "ShowMarker") == True:
            self.mi_ShowMarker = wx.MenuItem(self, wx.ID_ANY, u"Show marker(s)", wx.EmptyString, wx.ITEM_NORMAL)
            if self.parent.ShowMarker == True:
                self.mi_ShowMarker.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxTicked.ico"))
            else:
                self.mi_ShowMarker.SetBitmap(wx.Bitmap(str_MenuIconsPath + r"\TickBoxUnTicked.ico"))
            self.Append(self.mi_ShowMarker)
            self.Bind(wx.EVT_MENU, self.ToggleMarker, self.mi_ShowMarker)

        if hasattr(self.parent, "Zooming") == True or hasattr(self.parent, "ShowMarker") == True:
            self.AppendSeparator()

        self.mi_Copy = wx.MenuItem(self, wx.ID_ANY, u"Copy plot image", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Copy.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyPlot.ico"))
        self.Append(self.mi_Copy)
        self.Bind(wx.EVT_MENU, self.parent.PlotToClipboard, self.mi_Copy)

        self.mi_Export = wx.MenuItem(self, wx.ID_ANY, u"Export plot image", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_Export.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\SaveAs.ico"))
        self.Append(self.mi_Export)
        self.Bind(wx.EVT_MENU, self.parent.PlotToPNG, self.mi_Export)
        
        self.mi_PlotData = wx.MenuItem(self, wx.ID_ANY, u"Copy plot data", wx.EmptyString, wx.ITEM_NORMAL)
        self.mi_PlotData.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyData.ico"))
        self.Append(self.mi_PlotData)
        self.Bind(wx.EVT_MENU, self.parent.DataToClipboard, self.mi_PlotData)

        if hasattr(self.parent, "SummaryPlot") == True:
            if self.parent.SummaryPlot == True:
                self.AppendSeparator()
                self.mi_ChangeTitle = wx.MenuItem(self, wx.ID_ANY, u"Change Title", wx.EmptyString, wx.ITEM_NORMAL)
                #self.mi_ChangeTitle.SetBitmap(wx.Bitmap(str_MenuIconsPath + u"\CopyData.ico"))
                self.Append(self.mi_ChangeTitle)
                self.Bind(wx.EVT_MENU, self.ChangeTitle, self.mi_ChangeTitle)

    def ChangeTitle(self, event):
        event.Skip()
        dlg_ChangeTitle = ChangeTitleDialog(self.parent)
        dlg_ChangeTitle.Show()
    
    def ToggleMarker(self, event):
        if self.parent.ShowMarker == True:
            self.parent.ShowMarker = False
        else:
            self.parent.ShowMarker = True
        self.parent.Draw()

########################################################################################
##                                                                                    ##
##    ######   ####    ####   ##    ##    ######  #####    ####   ##    ##  ######    ##
##       ##   ##  ##  ##  ##  ###  ###    ##      ##  ##  ##  ##  ###  ###  ##        ##
##      ##    ##  ##  ##  ##  ########    ####    #####   ######  ########  ####      ##
##     ##     ##  ##  ##  ##  ## ## ##    ##      ##  ##  ##  ##  ## ## ##  ##        ##
##    ######   ####    ####   ##    ##    ##      ##  ##  ##  ##  ##    ##  ######    ##
##                                                                                    ##
########################################################################################

class ZoomFrame(wx.Dialog):
    def __init__(self, parent, position = None, size = wx.Size(1,1)):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Tooltip", pos=wx.DefaultPosition, size = size, style = wx.STAY_ON_TOP)
        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
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

    def __del__( self ):
        pass

    def Redraw(self, position, size):
        self.Position = position
        self.Size = size
        self.SetSize(self.Size)
        self.SetPosition(self.Position)
        self.Layout()

################################################################################################
##                                                                                            ##
##     #####  ##  ##   ####   ##  ##   #####  ######    ######  ##  ######  ##      ######    ##
##    ##      ##  ##  ##  ##  ### ##  ##      ##          ##    ##    ##    ##      ##        ##
##    ##      ######  ######  ######  ## ###  ####        ##    ##    ##    ##      ####      ##
##    ##      ##  ##  ##  ##  ## ###  ##  ##  ##          ##    ##    ##    ##      ##        ##
##     #####  ##  ##  ##  ##  ##  ##   ####   ######      ##    ##    ##    ######  ######    ##
##                                                                                            ##
################################################################################################

class ChangeTitleDialog(wx.Dialog):
    def __init__(self, plot):
        wx.Dialog.__init__ (self, parent = plot, id = wx.ID_ANY, title = u"Tooltip", pos=wx.DefaultPosition, size = wx.Size(114,27), style = wx.STAY_ON_TOP)

        self.SetBackgroundColour(cs.White)
        self.Plot = plot

        self.szr_Surround = wx.BoxSizer(wx.HORIZONTAL)
        self.txt_Title = wx.TextCtrl(self, wx.ID_ANY, self.Plot.Title, wx.DefaultPosition, wx.Size(100,22), wx.TE_PROCESS_ENTER )
        self.szr_Surround.Add(self.txt_Title,0,wx.ALL,1)
        self.btn_TinyX = btn.TinyXButton(self)
        self.szr_Surround.Add(self.btn_TinyX, 0, wx.ALL, 1)

        self.SetSizer(self.szr_Surround)
        self.Layout()
        self.szr_Surround.Fit(self)

        self.Centre( wx.BOTH )
        MousePosition = wx.GetMousePosition()
        TooltipPosition = wx.Point(MousePosition[0] - self.GetSize()[0], MousePosition[1]) # (x,y)
        self.SetPosition(TooltipPosition)
        self.SetFocus()
        self.Bind(wx.EVT_KILL_FOCUS, self.End)
        self.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.btn_TinyX.Bind(wx.EVT_BUTTON, self.End)
        self.btn_TinyX.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.txt_Title.Bind(wx.EVT_KEY_DOWN, self.Escape)
        self.txt_Title.Bind(wx.EVT_TEXT_ENTER, self.UpdateTitle)

    def __del__( self ):
        pass

    def UpdateTitle(self, event):
        event.Skip()
        self.Plot.Title = self.txt_Title.GetLineText(0)
        self.Plot.Draw()
        self.Destroy()

    def End(self, event):
        self.Destroy()

    def Escape(self, event):
        event.Skip()
        if event.GetKeyCode() == 27:
            self.Destroy()
