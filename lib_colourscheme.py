"""
Contains colours for BBQ's colour scheme, including the colour
blind friendly "Tol Muted" colour scheme by Paul Tol
(https://personal.sron.nl/~pault/).


Colour names are: Indigo, Blue, Cyan, Teal, Green, Olive, Sand,
Rose, Wine, Purple, PaleGrey.

They are available as wx.Colour (RGB), RGBA and HEX, and list
objects containing all colours but PaleGrey.


The naming convention is as follows:
'TM[Colour]_[RGB or RGBA or HEX]'.
Example: TMIndigo_HEX

List naming is 'TM_[RGB, RGBA or HEX]_List' and the order is as
stated above.

There is also a list of images for choice box colour previews
in the same order: TM_ColourChoiceIcons_List.

"""

import wx
import os
from numpy import polyval

# Colours
White = wx.Colour(255,255,255)
WhiteHex = "#FFFFFF"
Black = wx.Colour(0,0,0)

# UI background colours
BgDark = wx.Colour(80,80,80)
BgUltraDark = wx.Colour(38,38,38) # Dark like MS Office dark theme
BgMediumDark = wx.Colour(102,102,102) # Medium like MS Office dark theme
BgMedium = wx.Colour(190,187,184)
BgLight = wx.Colour(212,212,212)
BgUltraLight = wx.Colour(240,240,240)
BgTextBoxes = wx.Colour(210,208,206)

BgDarkHex = "#666666"
BgUltraDarkHex = "#262626" # Dark like MS Office dark theme
BgMediumDarkHex = "#666666" # Medium like MS Office dark theme
BgMediumHex = "#B8b8B8"
BgLightHex = "#D4D4D4"
BgUltraLightHex = "#F0F0F0"
BgTextBoxesHex = "#D2D0CE"

# Buttons
BtnFocus = wx.Colour(119, 89, 69)
BtnCurrent = wx.Colour(234, 107, 20)
BtnGrey = BgMediumDark
BtnLightGrey = BgUltraLight

# Colour gradient
def PWO(x):
    # Could write this in the return line, but for ease of human readability,
    # I will keep it here. 
    # Colour gradient PuOr from MatPlotLib was dissected in 30 steps, RGB
    # values were fit to 6th order polynomial via numpy polyfit
    r = polyval([4.89752028e-11,-4.26384068e-10,4.54749066e-06,
                -1.56961908e-03,8.31898613e-02,3.12370061e+00,4.67784751e+01],x)
    g = polyval([-5.07245612e-09,1.44724221e-06,-1.25536472e-04,
                 1.98183010e-03,8.48437810e-02,3.81161894e+00,-6.36983317e-01],x)
    b = polyval([-2.52420430e-08,7.68807218e-06,-8.44314315e-04,
                 4.04431579e-02,-8.93766332e-01,1.22549074e+01,6.99768273e+01],x)
    return wx.Colour(r,g,b)

##################################
##                              ##
##    ######   ####   ##        ##
##      ##    ##  ##  ##        ##
##      ##    ##  ##  ##        ##
##      ##    ##  ##  ##        ##
##      ##     ####   ######    ##
##                              ##
##################################

# https://personal.sron.nl/~pault/
TMIndigo_RGB = wx.Colour(51,34,136)
TMBlue_RGB =  wx.Colour(68,119,170)
TMCyan_RGB = wx.Colour(136,204,238)
TMTeal_RGB = wx.Colour(68,180,153)
TMGreen_RGB = wx.Colour(17,119,51)
TMOlive_RGB = wx.Colour(153,153,51)
TMSand_RGB = wx.Colour(201,204,119)
TMRose_RGB = wx.Colour(204,102,119)
TMWine_RGB = wx.Colour(136,34,85)
TMPurple_RGB = wx.Colour(170,68,153)
TMPaleGrey_RGB = wx.Colour(221,221,221)
# TMPaleGrey left out
TM_RGB_List = [TMIndigo_RGB, TMBlue_RGB, TMCyan_RGB, TMTeal_RGB, TMGreen_RGB,
               TMOlive_RGB,  TMSand_RGB, TMRose_RGB, TMWine_RGB, TMPurple_RGB]

# in RGBA format colour values go from 0-1.
TMIndigo_RGBA = (0.2,0.133,0.533,1)
TMBlue_RGBA =  (0.267,0.467,0.667,1)
TMCyan_RGBA = (0.533,0.8,0.933,1)
TMTeal_RGBA = (0.267,0.706,0.6,1)
TMGreen_RGBA = (0.67,0.467,0.2,1)
TMOlive_RGBA = (0.6,0.6,0.2,1)
TMSand_RGBA = (0.78,0.8,0.467,1)
TMRose_RGBA = (0.8,0.4,0.467,1)
TMWine_RGBA = (0.533,0.133,0.333,1)
TMPurple_RGBA = (0.667,0.267,0.6,1)
TMPaleGrey_RGBA = (0.867,0.867,0.867,1)
# TMPaleGrey left out
TM_RGBA_List = [TMIndigo_RGBA, TMBlue_RGBA, TMCyan_RGBA, TMTeal_RGBA, TMGreen_RGBA,
                TMOlive_RGBA, TMSand_RGBA, TMRose_RGBA, TMWine_RGBA, TMPurple_RGBA]

TMIndigo_Hex = "#332288"
TMBlue_Hex = "#4477AA"
TMCyan_Hex = "#88CCEE"
TMTeal_Hex = "#44B499"
TMGreen_Hex = "#117733"
TMOlive_Hex = "#999933"
TMSand_Hex = "#DDCC77"
TMRose_Hex = "#CC6677"
TMWine_Hex = "#882255"
TMPurple_Hex = "#AA4499"
TMPaleGrey_Hex = "#DDDDDD"
# TMPaleGrey left out
TM_Hex_List = [TMIndigo_Hex, TMBlue_Hex, TMCyan_Hex, TMTeal_Hex, TMGreen_Hex,
               TMOlive_Hex, TMSand_Hex, TMRose_Hex, TMWine_Hex, TMPurple_Hex]

# Location of colour previou box image files
real_path = os.path.realpath(__file__)
ColourPath = os.path.dirname(real_path) + r"\colour_choices"
TM_ColourChoiceIcons_List = [ColourPath + r"\indigo.png",
                             ColourPath + r"\blue.png",
                             ColourPath + r"\cyan.png",
			                 ColourPath + r"\teal.png",
		 	                 ColourPath + r"\green.png",
			                 ColourPath + r"\olive.png",
                             ColourPath + r"\sand.png",
			                 ColourPath + r"\rose.png",
			                 ColourPath + r"\wine.png",
			                 ColourPath + r"\purple.png"]
