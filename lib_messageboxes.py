"""
Contains functions to display message boxes. Serves to make process easier.
Arguments for all functions are optional unless they are named.

Functions:

    NoAnalysisPerformed
    SaveErrorNoAnalysis
    SaveSuccess
    NoDataFileAssigned
    FileErrorNotTransfer
    FileNotData
    NoLayoutDefined
    NoTransferLoaded
    ClipboardError
    IncompleteDetails
    StartAndStopIdentical
    ItemAlreadyExists
    QueryMismatch
    QueryReanalysis
    QueryChangeSampleSource
    QueryDiscardChanges
    QueryCloseProgram
    SavePermissionDenied

"""

import wx

def NoAnalysisPerformed(*args):
    """
    Displays message box if user tries to display a page that
    requires a completed analysis without having completed one.
    """
    message = wx.MessageBox("Cannot display this page, no analysis has been performed.",
                            caption = "No can do",
                            style = wx.OK|wx.ICON_INFORMATION)

def SaveErrorNoAnalysis(*args):
    """
    Displays message box if user tries to save an analysis without
    having completed one.
    """
    message = wx.MessageBox("Cannot save project: No analysis was performed.",
                            caption = "Save Error",
                            style = wx.OK|wx.ICON_INFORMATION)

def SaveSuccess(*args):
    """
    Displays message box after project has been successfully saved.
    """
    message = wx.MessageBox("Project saved successfully.",
                            caption = "Save Success",
                            style = wx.OK|wx.ICON_INFORMATION)

def NoDataFileAssigned(*args):
    """
    Displays message box if user tries to perform analysis w/o having
    assigned data files.
    """
    message = wx.MessageBox("Cannot proceed: No data files assigned",
                            caption = "No data files assigned",
                            style = wx.OK|wx.ICON_INFORMATION)

def FileErrorNotTransfer(*args):
    """
    Displays message box if loaded file does not match expected file type.
    """
    message = wx.MessageBox("The file you loaded was not a correct transfer file",
                            caption = "File error",
                            style = wx.OK|wx.ICON_INFORMATION)

def FileNotData(*args):
    """
    Displays message box if loaded file does not match expected file type.
    """
    message = wx.MessageBox("The file you loaded was eiter:\n"
                            + "\ni. not a correct raw data file or"
                            + "\nii. not formatted correctly\n"
                            + "\nand therefore could not be parsed."
                            + "\nCheck the file and try again.",
                            caption = "File error",
                            style = wx.OK|wx.ICON_INFORMATION)

def NoLayoutDefined(*args):
    """
    Displays message box if user tries to perform analysis without a plate layout.
    """
    message = wx.MessageBox("You have not defined a plate layout. Cannot proceed with analysis.",
                            caption = "No layout defined",
                            style = wx.OK|wx.ICON_INFORMATION)

def NoTransferLoaded(*args):
    """
    Displays message box if user tries to perform analysis with missing files.
    """
    message = wx.MessageBox("Cannot proceed: No transfer file loaded",
                            caption = "No transfer file loaded",
                            style = wx.OK|wx.ICON_INFORMATION)

def ClipboardError(*args):
    """
    Displays message box on clipboard error.
    """
    message = wx.MessageBox("Could not open the clipboard. Please try again",
                            caption = "Clipboard Error",
                            style = wx.OK|wx.ICON_INFORMATION)

def IncompleteDetails(*args):
    """
    Displays message box if assay details are incomplete.
    """
    message = wx.MessageBox("One or more fields have not been filled out, please check",
                            caption = "Missing details",
                            style = wx.OK|wx.ICON_INFORMATION)

def StartAndStopIdentical(*args):
    """
    Displays message box if assay details are incomplete.
    """
    message = wx.MessageBox("Start and stop of interval are identical, pick another point!",
                            caption = "No can do",
                            style = wx.OK|wx.ICON_INFORMATION)

def ItemAlradyExists(item):
    """
    Displays message box notifying user item already exists.

    Arguuments:
        item -> string
    """
    message = wx.MessageBox("The " + item + " already exsists.",
                            caption = "Item already exists",
                            style = wx.OK|wx.ICON_INFORMATION)

def PlateFormatsDoNotMatch(*args):
    """
    Displays message box if plate formats within analysis do not match.
    """
    message = wx.MessageBox("The Plate format of the entry you want to create does not match the previous entries."
                            + "\nAll entries must be of the same format.",
                            caption = "Plate formats do not match",
                            style = wx.OK|wx.ICON_INFORMATION)

def QueryMismatch(criterion, item):
    """
    Displays message box asking user if they want to clear a mismatching item.

    Arguments:
        criterion -> string, the criterion by which things are compared
        item -> string; the mismatchin item(s).
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox("The " + criterion + " do no match. Do you want to clear the current " + item + "?",
                            caption = "Mismatch",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def QueryReanalysis(*args):
    """
    Displays message box asking user if they want to re-analyse data.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox("Assay details or transfer/data files have been changed." + 
                            " Do you want to re-analyse the data?",
                            caption = "Re-analyse data?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def QueryChangeSampleSource(*args):
    """
    Displays message box asking user to confirm sample source change.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox("You have already chosen a sample source and added or loaded destination plate entries."
                            + "\nIf you change the sample source, the current entries will be deleted."
                            + "\nDo you want to proceed?",
                            caption = "Change sample source?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def QueryDiscardChanges(*args):
    """
    Displays message box asking user to confirm discarding of unsaved
    data when closing project.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox("You may have unsaved data. Do you still want to close this project?",
                            caption = "Discard changes?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def QueryCloseProgram(*args):
    """
    Displays message box asking user to confirm discarding of unsaved
    data when closing program.
    
    Returns True if user confirms, False if not.
    """
    message = wx.MessageBox("You may have unsaved data. Do you still want to close the program?",
                            caption = "Discard changes?",
                            style = wx.YES_NO|wx.ICON_QUESTION)
    if message == 2:
        return True
    elif message == 8:
        return False

def SavePermissionDenied(*args):
    """
    Displays message box if file could not be saved due to insufficient
    permissions.
    """
    message = wx.MessageBox("Cannot save file. Please check that"
                            + "\n  i. you have permission to write in this directory"
                            + "\n  ii. the file you are trying to overwrite is not protected"
                            + "\n  iii. the file you are trying to overwrite is not in use by another program.",
                            caption = "Permission denied!",
                            style = wx.OK|wx.ICON_INFORMATION)