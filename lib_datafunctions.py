# Library of functions to process transfer data from liquid handlers and raw data from plate readers.
# Functions to readout data from raw data files from devices are in separate library.

# Import libraries
import numpy as np
from numpy.core.fromnumeric import mean
import pandas as pd
from multiprocessing import Pool

# Import my own libraries
import lib_platefunctions as pf
import lib_resultreadouts as ro
import lib_fittingfunctions as ff
import lib_messageboxes as msg

########################################################################################################
##                                                                                                    ##
##    ######  #####    ####   ##  ##   #####  ######  ######  #####     ######  ##  ##      ######    ##
##      ##    ##  ##  ##  ##  ### ##  ##      ##      ##      ##  ##    ##      ##  ##      ##        ##
##      ##    #####   ######  ######   ####   ####    ####    #####     ####    ##  ##      ####      ##
##      ##    ##  ##  ##  ##  ## ###      ##  ##      ##      ##  ##    ##      ##  ##      ##        ##
##      ##    ##  ##  ##  ##  ##  ##  #####   ##      ######  ##  ##    ##      ##  ######  ######    ##
##                                                                                                    ##
########################################################################################################

def create_transfer_frame(str_TransferFile):
	"""
	Reads transfer file into data frame and trims it down to neccessary lines
	
	!NOTE!: If the transfer file comes straight from the Echo, the delimiting will end after each line is over. What would be empty cells
	is not delimited. Example:
	First line is: Run ID,3360
	To capture all columns, the first line should be: Run ID,3360,,,,,,,,,,,,,,,,,,,
	This will trip up pd.read_csv, so we have to find the header row first byt loading only the first column and searching for the keyword.
	"""
	# Open transfer file and find header row and exceptions (if any)
	dfr_Temp = pd.read_csv(str_TransferFile, sep=",", usecols=[0], header=None, index_col=False, engine="python")
	int_Exceptions = dfr_Temp.index[dfr_Temp[0] == "[EXCEPTIONS]"].tolist()
	int_HeaderRow = dfr_Temp.index[dfr_Temp[0] == "[DETAILS]"].tolist()
	# Check whether the Details keyword has been found:
	if not int_HeaderRow:
		return None
	# create exceptions dataframe
	if int_Exceptions:
		int_Exceptions = int_Exceptions[0] + 1
		int_Length = int_HeaderRow[0] - int_Exceptions - 2
		dfr_Exceptions = pd.read_csv(str_TransferFile, sep=",", header=int_Exceptions, index_col=False, engine="python")
		dfr_Exceptions = dfr_Exceptions.iloc[0:int_Length]
		dfr_Exceptions.columns = dfr_Exceptions.columns.str.replace(" ", "")
		dfr_Exceptions = dfr_Exceptions[["DestinationPlateName","DestinationWell"]]
	else:
		dfr_Exceptions = pd.DataFrame(columns=["DestinationPlateName","DestinationWell"])
	# Adjust header row for offset:
	int_HeaderRow = int_HeaderRow[0] + 1
	# Now open transfer file properly:
	dfr_TransferFile = pd.read_csv(str_TransferFile, sep=",", header=int_HeaderRow, index_col=False, engine="python")
	# Clean up headers
	dfr_TransferFile.columns = dfr_TransferFile.columns.str.replace(" ", "")
	# Keep only relevant columns -> This will drop the first two columns that hold the appendix data (Instrument name, serial number, etc)
	# Sort by DestinationConcentration -> Ensures that all points will be in the correct order and there are no weird gaps when drawing the fit
	# Drop rows that are empty -> This will be where TransferVolume is "NaN"
	dfr_TransferFile = dfr_TransferFile[["SourceConcentration","DestinationPlateName","DestinationPlateBarcode","DestinationPlateType","DestinationWell",
		"SampleID","SampleName","DestinationConcentration","TransferVolume","ActualVolume","SourcePlateName"]].sort_values(["DestinationPlateName","SampleID","DestinationConcentration"],
		ascending=[True,True,False]).dropna(subset=["TransferVolume"])
	# Make wells sortable -> Relegated to a later point
	return dfr_TransferFile, dfr_Exceptions

def get_destination_plates(dfr_ProcTra):
	# Creates and returns an array or dataframe with the DestinationPlateName, DestinationPlateBarcode and number of wells
	dfr_DestPlat = dfr_ProcTra[["DestinationPlateName", "DestinationPlateBarcode",
		"DestinationPlateType"]].sort_values(by=["DestinationPlateName"]).drop_duplicates(subset=["DestinationPlateName"],
		keep="first", ignore_index=True)
	# Get plate type
	dfr_DestPlat.DestinationPlateType = dfr_DestPlat.DestinationPlateType.apply(pf.plate_type_string)
	# Return result
	return dfr_DestPlat

def get_samples(dfr_ProcessedTransfer,str_CurrentPlate,int_PlateFormat):
	"""
	Get sample locations and concentrations from processed transfer file and write into data frame/
	first column (after index) sample ID
	second column: list lists of locations
	third column: list of concentrations
	"""
	# Get list of samples, drop duplicates, drop emtpies, reset index
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[dfr_ProcessedTransfer["DestinationPlateName"]==str_CurrentPlate]
	dfr_Samples = dfr_ProcessedTransfer[["DestinationPlateName","SampleID","SourceConcentration"]].drop_duplicates(subset=["SampleID"], keep="first",
		ignore_index=True).dropna().reset_index(drop=True)
	dfr_Samples = dfr_Samples.drop(dfr_Samples.index[dfr_Samples["SampleID"]=="Control"]).reset_index(drop=True)
	dfr_Samples.insert(2,"Locations","")
	dfr_Samples.insert(3,"Concentrations","")
	dfr_Samples.insert(4,"TransferVolumes","")
	# Convert wells
	if int_PlateFormat == 96:
		lst_WellsIndex = dfr_ProcessedTransfer.DestinationWell.apply(pf.sortable_well_96).apply(pf.well_to_index_96).tolist()
	elif int_PlateFormat == 384:
		lst_WellsIndex = dfr_ProcessedTransfer.DestinationWell.apply(pf.sortable_well_384).apply(pf.well_to_index_384).tolist()
	elif int_PlateFormat == 1536:
		lst_WellsIndex = dfr_ProcessedTransfer.DestinationWell.apply(pf.sortable_well_1536).apply(pf.well_to_index_1536).tolist()
	dfr_ProcessedTransfer.insert(3,"WellsIndex",lst_WellsIndex) # Column position three is chosen randomly.
	# Create columns for Locations and Concentration, write placeholders, change data type to enable holding lists
	for smpl in range(dfr_Samples.shape[0]):
		dfCurrent = dfr_ProcessedTransfer[dfr_ProcessedTransfer.SampleID == dfr_Samples.loc[smpl, "SampleID"]]
		dfr_Samples.at[smpl,"Locations"] = dfCurrent.WellsIndex.reset_index(drop=True)
		dfr_Samples.at[smpl,"Concentrations"] = dfCurrent.DestinationConcentration.reset_index(drop=True)
		dfr_Samples.at[smpl,"TransferVolumes"] = dfCurrent.TransferVolume.reset_index(drop=True)
	return dfr_Samples

def get_samples_lightcycler(str_CurrentPlate,dfr_RawData,int_PlateFormat):
	dfr_Samples = pd.DataFrame(columns=["DestinationPlateName","SampleID","SourceConcentration","Locations","Concentrations","TransferVolumes"],
		index=range(len(dfr_RawData)))
	for i in range(len(dfr_Samples)):
		dfr_Samples.at[i,"DestinationPlateName"] = str_CurrentPlate
		dfr_Samples.at[i,"SampleID"] = dfr_RawData.loc[i,"Name"]
		dfr_Samples.at[i,"SourceConcentration"] = "NA"
		dfr_Samples.at[i,"Locations"] = [pf.well_to_index(dfr_RawData.loc[i,"Well"],int_PlateFormat)] # List with one element!
		dfr_Samples.at[i,"Concentrations"] = ["NA"]
		dfr_Samples.at[i,"TransferVolumes"] = ["NA"]
	return dfr_Samples

def get_samples_wellonly(str_CurrentPlate,dfr_RawData,int_PlateFormat):
	dfr_Samples = pd.DataFrame(columns=["DestinationPlateName","SampleID","SourceConcentration","Locations","Concentrations","TransferVolumes"],
		index=range(len(dfr_RawData)))
	for i in range(len(dfr_Samples)):
		dfr_Samples.at[i,"DestinationPlateName"] = str_CurrentPlate
		dfr_Samples.at[i,"SampleID"] = dfr_RawData.loc[i,"Well"]
		dfr_Samples.at[i,"SourceConcentration"] = "NA"
		dfr_Samples.at[i,"Locations"] = [pf.well_to_index(dfr_RawData.loc[i,"Well"],int_PlateFormat)] # List with one element!
		dfr_Samples.at[i,"Concentrations"] = ["NA"]
		dfr_Samples.at[i,"TransferVolumes"] = ["NA"]
	return dfr_Samples

def get_references(dfr_ProcessedTransfer,dfr_Exceptions,str_TransferEntry,str_RawDataFile,dfr_RawData):
	"""
	Extracts locations of reference wells (control compound, no-addition and solvent-only wells) and calculates mean, standard error,
	standard deviation, median and median absolute deviation for each.
	"""
	int_PlateFormat = len(dfr_RawData)
	# Extracts location of controls and references from processed transfer file
	# Create dfr_Layout first
	dfr_Layout = pd.DataFrame(index=[0],columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
	dfr_Layout.at[0,"PlateID"] = "X999A"
	dfr_Layout.at[0,"ProteinNumerical"] = make_list(int_PlateFormat,"1")
	dfr_Layout.at[0,"PurificationID"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"Concentration"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"WellType"] = make_list(int_PlateFormat,"s")
	# Rename some columns to make things easier, get only columns and rows we need
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["DestinationPlateName"]==str_TransferEntry)]
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[["DestinationPlateName","SampleID","SampleName","DestinationWell"]].rename(columns={"DestinationWell":"Well"})
	dfr_Exceptions = dfr_Exceptions[(dfr_Exceptions["DestinationPlateName"]==str_TransferEntry)]
	# Adjust wells to sortable wells
	dfr_ProcessedTransfer.loc[:,"Well"] = dfr_ProcessedTransfer.loc[:,"Well"].apply(lambda x: pf.sortable_well(x, int_PlateFormat))
	dfr_RawData.loc[:,"Well"] = dfr_RawData.loc[:,"Well"].apply(lambda x: pf.sortable_well(x, int_PlateFormat))
	dfr_Exceptions.loc[:,"DestinationWell"] = dfr_Exceptions.loc[:,"DestinationWell"].apply(lambda x: pf.sortable_well(x, int_PlateFormat))
	# Create a dataframe that will eventually hold Five columns: Well, Reading, Control, Transfer, Buffer, Solvent.
	dfr_References = dfr_RawData.rename(columns={str_RawDataFile:"Reading"})
	# Get list of exceptions and transfers -> make them sortable later for efficiency!
	lst_Exceptions = dfr_Exceptions["DestinationWell"].tolist()
	lst_TransferWells = dfr_ProcessedTransfer["Well"].unique()
	# Get control values (e.g. 100% inhibition)
	dfr_Controls = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleName"] == "Control")]
	dfr_Controls = dfr_Controls[["Well","SampleName"]].rename(columns={"SampleName":"Control"})
	# Merge controls into reference dataframe
	dfr_References = pd.merge(dfr_References, dfr_Controls, on=["Well"], how="left")
	# get all "buffer" wells, e.g. w/o any addition into them from transfer file
	dfr_Transfers = pd.DataFrame(list(zip(lst_TransferWells,lst_TransferWells)),columns={"Well","Transfer"})
	# Merge all transfers into reference dataframe
	dfr_References = pd.merge(dfr_References, dfr_Transfers, on=["Well"], how="left")
	# no transfer at all means buffer
	for i in range(dfr_References.shape[0]):
		if pd.isna(dfr_References.loc[i,"Transfer"]) == True and pd.isna(dfr_References.loc[i,"Reading"]) == False:
			dfr_References.loc[i,"Buffer"] = "YES"
		else:
			dfr_References.loc[i,"Buffer"] = np.nan
	# Solvent wells have a transfer but no sample
	#dfr_Solvent = dfr_ProcessedTransfer[["SampleID","Well"]]
	dfr_Samples = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == False)]
	# Get entries in transfer file with no sample -> Solvent transfer. Could be backfills!
	dfr_Solvent = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == True)].reset_index(drop=True)
	# Figure out which Solvent transfers are not backfills and drop these from the dataframe
	lst_Backfills = []
	for well in range(len(dfr_Solvent)):
		if dfr_Solvent.loc[well,"Well"] in dfr_Samples.values:
			lst_Backfills.append(well)
	dfr_Solvent = dfr_Solvent[["Well"]].drop(lst_Backfills).reset_index(drop=True)
	if len(dfr_Solvent) > 0:
		dfr_Solvent.loc[dfr_Solvent["Well"].isnull() == False,"Solvent"] = "YES"
		# Merge to dfr_References
		dfr_References = pd.merge(dfr_References, dfr_Solvent, on=["Well"], how="left")
	else:
		dfr_References["Solvent"] = make_list(len(dfr_References),np.nan)
	# Write readings into appropriate columns
	lst_Buffer = []
	for i in range(len(dfr_References)):
		if not dfr_References.loc[i,"Well"] in lst_Exceptions:
			# Write control value, delete Solvent value if there is a control
			if dfr_References.loc[i,"Control"] == "Control":
				dfr_References.loc[i,"Control"] = dfr_References.loc[i,"Reading"]
				dfr_References.loc[i,"Solvent"] = np.nan
				dfr_References.loc[i,"Buffer"] = np.nan
			# Write Solvent value. Must not be a control, must have transfer. SampleID = Nan has already been tested
			elif dfr_References.loc[i,"Control"] != "Control" and dfr_References.loc[i,"Solvent"] == "YES":
				dfr_References.loc[i,"Solvent"] = dfr_References.loc[i,"Reading"]
				dfr_References.loc[i,"Control"] = np.nan
				dfr_References.loc[i,"Buffer"] = np.nan
						# Write buffer value
			elif dfr_References.loc[i,"Buffer"] == "YES":
					lst_Buffer.append(dfr_References.loc[i,"Well"])
					dfr_References.loc[i,"Buffer"] = dfr_References.loc[i,"Reading"]
		else:
			dfr_References.loc[i,"Control"] = np.nan
			dfr_References.loc[i,"Solvent"] = np.nan
			dfr_References.loc[i,"Buffer"] = np.nan
	# Calculate parameters:
	flt_Solvent_Mean, flt_Solvent_SEM, flt_Solvent_STDEV = dfr_References["Solvent"].mean(), dfr_References["Solvent"].sem(), dfr_References["Solvent"].std()
	flt_Solvent_Median, flt_Solvent_MAD = dfr_References["Solvent"].median(), MedianAbsoluteDeviation(dfr_References["Solvent"])
	flt_Control_Mean, flt_Control_SEM, flt_Control_STDEV = dfr_References["Control"].mean(), dfr_References["Control"].sem(), dfr_References["Control"].std()
	flt_Control_Median, flt_Control_MAD = dfr_References["Control"].median(), MedianAbsoluteDeviation(dfr_References["Control"])
	flt_Buffer_Mean, flt_Buffer_SEM, flt_Buffer_STDEV = dfr_References["Buffer"].mean(), dfr_References["Buffer"].sem(), dfr_References["Buffer"].std()
	flt_Buffer_Median, flt_Buffer_MAD = dfr_References["Buffer"].median(), MedianAbsoluteDeviation(dfr_References["Buffer"])
	# If there is a control compound, give out a ZPrime. Choose Solvent or Buffer
	if pd.isna(flt_Control_Mean) == False:
		if pd.isna(flt_Solvent_Mean) == False:
			flt_ZPrime_Mean = 1 - (3 * (flt_Solvent_STDEV + flt_Control_STDEV) / abs(flt_Solvent_Mean - flt_Control_Mean))
			flt_ZPrime_Median = 1 - (3 * (flt_Solvent_MAD + flt_Control_MAD) / abs(flt_Solvent_Median - flt_Control_Median))
		else:
			flt_ZPrime_Mean = 1 - (3 * (flt_Buffer_STDEV + flt_Control_STDEV) / abs(flt_Buffer_Mean - flt_Control_Mean))
			flt_ZPrime_Median = 1 - (3 * (flt_Buffer_MAD + flt_Control_MAD) / abs(flt_Buffer_Median - flt_Control_Median))
	else:
		flt_ZPrime_Mean = np.nan
		flt_ZPrime_Median = np.nan
	
	lst_References = [flt_Solvent_Mean, flt_Solvent_SEM, flt_Control_Mean, flt_Control_SEM, flt_Buffer_Mean, flt_Buffer_SEM, flt_ZPrime_Mean, flt_ZPrime_Median]
	# Write it all into dfr_Layout:
	for i in range(int_PlateFormat):
		if pd.isna(dfr_References.loc[i,"Control"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "r"
		elif pd.isna(dfr_References.loc[i,"Solvent"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "d"
		elif pd.isna(dfr_References.loc[i,"Buffer"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "b"

	dfr_References_Return = pd.DataFrame(columns=[0],index=["SolventMean","SolventMedian","SolventSEM","SolventSTDEV","SolventMAD",
		"BufferMean","BufferMedian","BufferSEM","BufferSTDEV","BufferMAD",
		"ControlMean","ControlMedian","ControlSEM","ControlSTDEV","ControlMAD",
		"ZPrimeMean","ZPrimeMedian"])
	dfr_References_Return.at["SolventMean",0] = flt_Solvent_Mean
	dfr_References_Return.at["SolventMedian",0] = flt_Solvent_Median
	dfr_References_Return.at["SolventSEM",0] = flt_Solvent_SEM
	dfr_References_Return.at["SolventSTDEV",0] = flt_Solvent_STDEV
	dfr_References_Return.at["SolventMAD",0] = flt_Solvent_MAD

	dfr_References_Return.at["ControlMean",0] = flt_Control_Mean
	dfr_References_Return.at["ControlMedian",0] = flt_Control_Median
	dfr_References_Return.at["ControlSEM",0] = flt_Control_SEM
	dfr_References_Return.at["ControlSTDEV",0] = flt_Control_STDEV
	dfr_References_Return.at["ControlMAD",0] = flt_Control_MAD

	dfr_References_Return.at["BufferMean",0] = flt_Buffer_Mean
	dfr_References_Return.at["BufferMedian",0] = flt_Buffer_Median
	dfr_References_Return.at["BufferSEM",0] = flt_Buffer_SEM
	dfr_References_Return.at["BufferSTDEV",0] = flt_Buffer_STDEV
	dfr_References_Return.at["BufferMAD",0] = flt_Buffer_MAD

	dfr_References_Return.at["ZPrimeMean",0] = flt_ZPrime_Mean
	dfr_References_Return.at["ZPrimeMedian",0] = flt_ZPrime_Median

	return dfr_References_Return, dfr_Layout

def get_layout(dfr_ProcessedTransfer,str_TransferEntry,str_RawDataFile,dfr_RawData):
	int_PlateFormat = len(dfr_RawData)
	# Extracts location of controls and references from processed transfer file
	# Create dfr_Layout first
	dfr_Layout = pd.DataFrame(index=[0],columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
	dfr_Layout.at[0,"PlateID"] = "X999A"
	dfr_Layout.at[0,"ProteinNumerical"] = make_list(int_PlateFormat,"1")
	dfr_Layout.at[0,"PurificationID"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"Concentration"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"WellType"] = make_list(int_PlateFormat,"s")
	# Rename some columns to make things easier, get only columns and rows we need
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["DestinationPlateName"]==str_TransferEntry)]
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[["DestinationPlateName","SampleID","SampleName","DestinationWell"]].rename(columns={"DestinationWell":"Well"})
	# Create a dataframe that will eventually hold Five columns: Well, Reading, Control, Transfer, Buffer, Solvent.
	dfr_References = dfr_RawData.rename(columns={str_RawDataFile:"Reading"})
	# Get control values (e.g. 100% inhibition)
	dfr_Controls = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleName"] == "Control")]
	dfr_Controls = dfr_Controls[["Well","SampleName"]].rename(columns={"SampleName":"Control"})
	# Merge controls into reference dataframe
	dfr_References = pd.merge(dfr_References, dfr_Controls, on=["Well"], how="left")
	# get all "buffer" wells, e.g. w/o any addition into them from transfer file
	lst_TransferWells = dfr_ProcessedTransfer["Well"].unique()
	dfr_Transfers = pd.DataFrame(list(zip(lst_TransferWells,lst_TransferWells)),columns={"Well","Transfer"})
	# Merge all transfers into reference dataframe
	dfr_References = pd.merge(dfr_References, dfr_Transfers, on=["Well"], how="left")
	# no transfer means buffer
	dfr_References.loc[dfr_References["Transfer"].isnull(),"Buffer"] = True
	# Solvent wells have a transfer but no sample
	#dfr_Solvent = dfr_ProcessedTransfer[["SampleID","Well"]]
	dfr_Samples = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == False)]
	# Get entries in transfer file with no sample -> Solvent transfer. Could be backfills!
	dfr_Solvent = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == True)].reset_index(drop=True)
	# Figure out which Solvent transfers are not backfills and drop these from the dataframe
	lst_Backfills = []
	for well in range(len(dfr_Solvent)):
		if dfr_Solvent.loc[well,"Well"] in dfr_Samples.values:
			lst_Backfills.append(well)
	dfr_Solvent = dfr_Solvent[["Well"]].drop(lst_Backfills).reset_index(drop=True)
	if len(dfr_Solvent) > 0:
		dfr_Solvent.loc[dfr_Solvent["Well"].isnull() == False,"Solvent"] = True
		# Merge to dfr_References
		dfr_References = pd.merge(dfr_References, dfr_Solvent, on=["Well"], how="left")
	else:
		dfr_References["Solvent"] = make_list(len(dfr_References),np.nan)
	# Write readings into appropriate columns
	for i in range(len(dfr_References)):
		# Write control value, delete Solvent value if there is a control
		if dfr_References.loc[i,"Control"] == "Control":
			dfr_References.loc[i,"Control"] = True
			dfr_References.loc[i,"Solvent"] = False
			dfr_References.loc[i,"Buffer"] = False
		# Write buffer value
		if dfr_References.loc[i,"Buffer"] == True:
			dfr_References.loc[i,"Control"] = False
			dfr_References.loc[i,"Solvent"] = False
		# Write Solvent value. Must not be a control, must have transfer. SampleID = Nan has already been tested
		if dfr_References.loc[i,"Control"] != "Control" and dfr_References.iloc[i,5] == "YES":
			dfr_References.loc[i,"Solvent"] = True
			dfr_References.loc[i,"Control"] = False
			dfr_References.loc[i,"Buffer"] = False

	# Write it all into dfr_Layout:
	for i in range(int_PlateFormat):
		if dfr_References.loc[i,"Control"] == True:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "r"
		elif dfr_References.loc[i,"Solvent"] == True:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "d"
		elif dfr_References.loc[i,"Buffer"] == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "b"

	return dfr_Layout

def get_references_DRTC(dfr_ProcessedTransfer,str_TransferEntry,str_RawDataFile,dfr_RawData):
	int_Cycles = len(dfr_RawData)
	int_PlateFormat = dfr_RawData.shape[0]
	# Extracts location of controls and references from processed transfer file
	# Create dfr_Layout first and fill with default values
	dfr_Layout = pd.DataFrame(index=[0],columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
	dfr_Layout.at[0,"PlateID"] = "X999A"
	dfr_Layout.at[0,"ProteinNumerical"] = make_list(int_PlateFormat,"1")
	dfr_Layout.at[0,"PurificationID"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"Concentration"] = make_list(int_PlateFormat,"")
	dfr_Layout.at[0,"WellType"] = make_list(int_PlateFormat,"s")
	# Make well list to merge with data frame
	lst_Wells = []
	for well in range(int_PlateFormat):
		lst_Wells.append(pf.index_to_well(well+1,int_PlateFormat))
	dfr_Wells = pd.DataFrame(list(lst_Wells),columns=["Well"])
	# Rename some columns to make things easier, get only columns and rows we need
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["DestinationPlateName"]==str_TransferEntry)]
	dfr_ProcessedTransfer = dfr_ProcessedTransfer[["DestinationPlateName","SampleID","DestinationWell"]].rename(columns={"DestinationWell":"Well"})
	# Get Controls
	dfr_Controls = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"] == "Control")]
	dfr_Controls = dfr_Controls[["Well","SampleID"]].rename(columns={"SampleID":"Control"})
	dfr_References = pd.merge(dfr_Wells, dfr_Controls, on=["Well"], how="left")
	# get all "buffer" wells, e.g. w/o any addition into them from transfer file
	lst_TransferWells = dfr_ProcessedTransfer["Well"].unique()
	dfr_Transfers = pd.DataFrame(list(zip(lst_TransferWells,lst_TransferWells)),columns={"Well","Transfer"})
	# Merge all transfers into reference dataframe
	dfr_References = pd.merge(dfr_References, dfr_Transfers, on=["Well"], how="left")
	# no transfer means buffer
	dfr_References.loc[dfr_References["Transfer"].isnull(),"Buffer"] = True
	# Solvent wells have a transfer but no sample
	dfr_Samples = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == False)]
	# Get entries in transfer file with no sample -> Solvent transfer. Could be backfills!
	dfr_Solvent = dfr_ProcessedTransfer[(dfr_ProcessedTransfer["SampleID"].isnull() == True)].reset_index(drop=True)
	# Figure out which Solvent transfers are not backfills and drop these from the dataframe
	lst_Backfills = []
	for well in range(len(dfr_Solvent)):
		if dfr_Solvent.loc[well,"Well"] in dfr_Samples.values:
			#lst_Backfills.append(pf.well_to_index(dfr_Solvent.loc[well,"Well"],int_PlateFormat))
			lst_Backfills.append(dfr_Solvent.index[well])
	dfr_Solvent = dfr_Solvent[["Well"]].drop(lst_Backfills).reset_index(drop=True)
	if len(dfr_Solvent) > 0:
		dfr_Solvent.loc[dfr_Solvent["Well"].isnull() == False,"Solvent"] = True
		# Merge to dfr_References
		dfr_References = pd.merge(dfr_References, dfr_Solvent, on=["Well"], how="left")
	else:
		dfr_References["Solvent"] = make_list(dfr_References.shape[0],False)

	# Initialise mini-dataframes
	dfr_Solvent_Values = pd.DataFrame(columns=dfr_RawData.columns.values.tolist(),index=range(dfr_References.shape[0]))
	dfr_Buffer_Values = pd.DataFrame(columns=dfr_RawData.columns.values.tolist(),index=range(dfr_References.shape[0]))
	dfr_Control_Values = pd.DataFrame(columns=dfr_RawData.columns.values.tolist(),index=range(dfr_References.shape[0]))
	dfr_References_Return = pd.DataFrame(columns=dfr_RawData.columns.values.tolist(),index=["SolventMean","SolventMedian","SolventSEM","SolventSTDEV","SolventMAD",
		"BufferMean","BufferMedian","BufferSEM","BufferSTDEV","BufferMAD",
		"ControlMean","ControlMedian","ControlSEM","ControlSTDEV","ControlMAD",
		"ZPrimeMean","ZPrimeMedian"])

	# Double check all the True+False values
	for well in dfr_References.index.values:
		if dfr_References.loc[well,"Control"] == "Control":
			dfr_References.loc[well,"Control"] = True
			dfr_References.loc[well,"Solvent"] = False
			dfr_References.loc[well,"Buffer"] = False
			dfr_Control_Values.at[well] = dfr_RawData.loc[well]
		elif dfr_References.loc[well,"Buffer"] == True:
			dfr_References.loc[well,"Control"] = False
			dfr_References.loc[well,"Solvent"] = False
			dfr_Buffer_Values.at[well] = dfr_RawData.loc[well]
		elif dfr_References.loc[well,"Solvent"] == True:
			dfr_References.loc[well,"Control"] = False
			dfr_References.loc[well,"Buffer"] = False
			dfr_Solvent_Values.at[well] = dfr_RawData.loc[well]

	for cycle in dfr_RawData.columns.values:
		if any_nonnan(dfr_Solvent_Values.loc[:,cycle]) == True:
			dfr_References_Return.at["SolventMean",cycle] = dfr_Solvent_Values.loc[:,cycle].mean()
			dfr_References_Return.at["SolventMedian",cycle] = dfr_Solvent_Values.loc[:,cycle].median()
			dfr_References_Return.at["SolventSEM",cycle] = dfr_Solvent_Values.loc[:,cycle].sem()
			dfr_References_Return.at["SolventSTDEV",cycle] = dfr_Solvent_Values.loc[:,cycle].std()
			dfr_References_Return.at["SolventMAD",cycle] = MedianAbsoluteDeviation(dfr_Solvent_Values[cycle])

		if any_nonnan(dfr_Control_Values.loc[:,cycle]) == True:
			dfr_References_Return.at["ControlMean",cycle] = dfr_Control_Values.loc[:,cycle].mean()
			dfr_References_Return.at["ControlMedian",cycle] = dfr_Control_Values.loc[:,cycle].median()
			dfr_References_Return.at["ControlSEM",cycle] = dfr_Control_Values.loc[:,cycle].sem()
			dfr_References_Return.at["ControlSTDEV",cycle] = dfr_Control_Values.loc[:,cycle].std()
			dfr_References_Return.at["ControlMAD",cycle] = MedianAbsoluteDeviation(dfr_Control_Values[cycle])

		if any_nonnan(dfr_Buffer_Values.loc[:,cycle]) == True:
			dfr_References_Return.at["BufferMean",cycle] = dfr_Buffer_Values.loc[:,cycle].mean()
			dfr_References_Return.at["BufferMedian",cycle] = dfr_Buffer_Values.loc[:,cycle].median()
			dfr_References_Return.at["BufferSEM",cycle] = dfr_Buffer_Values.loc[:,cycle].sem()
			dfr_References_Return.at["BufferSTDEV",cycle] = dfr_Buffer_Values.loc[:,cycle].std()
			dfr_References_Return.at["BufferMAD",cycle] = MedianAbsoluteDeviation(dfr_Buffer_Values[cycle])
		# If there is a control compound, give out a ZPrime. Choose Solvent or Buffer
		# ZPrime = 1 - (3 * (flt_Solvent_STDEV + flt_Control_STDEV) / abs(flt_Solvent_Mean - flt_Control_Mean))
		if pd.isna(dfr_References_Return.loc["ControlMean",cycle]) == False:
			if pd.isna(dfr_References_Return.loc["SolventMean",cycle]) == False:
				# ZPrime = 1 - (3 * (flt_Solvent_STDEV + flt_Control_STDEV) / abs(flt_Solvent_Mean - flt_Control_Mean))
				dfr_References_Return.at["ZPrimeMean",cycle] = 1 - (3 * (dfr_References_Return.loc["SolventSTDEV",cycle] + dfr_References_Return.loc["ControlSTDEV",cycle]) / abs(dfr_References_Return.loc["SolventMean",cycle] - dfr_References_Return.loc["ControlMean",cycle]))
				dfr_References_Return.at["ZPrimeMedian",cycle] = 1 - (3 * (dfr_References_Return.loc["SolventMAD",cycle] + dfr_References_Return.loc["ControlMAD",cycle]) / abs(dfr_References_Return.loc["SolventMedian",cycle] - dfr_References_Return.loc["ControlMedian",cycle]))
			else:
				dfr_References_Return.at["ZPrimeMean",cycle] = 1 - (3 * (dfr_References_Return.loc["BufferSTDEV",cycle] + dfr_References_Return.loc["ControlSTDEV",cycle]) / abs(dfr_References_Return.loc["BufferMean",cycle] - dfr_References_Return.loc["ControlMean",cycle]))
				dfr_References_Return.at["ZPrimeMedian",cycle] = 1 - (3 * (dfr_References_Return.loc["BufferMAD",cycle] + dfr_References_Return.loc["ControlMAD",cycle]) / abs(dfr_References_Return.loc["BufferMedian",cycle] - dfr_References_Return.loc["ControlMedian",cycle]))
		else:
			dfr_References_Return.at["ZPrimeMean",cycle] = np.nan
			dfr_References_Return.at["ZPrimeMedian",cycle] = np.nan
		
	for i in range(int_PlateFormat):
		if pd.isna(dfr_References.loc[i,"Control"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "r"
		elif pd.isna(dfr_References.loc[i,"Solvent"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "d"
		elif pd.isna(dfr_References.loc[i,"Buffer"]) == False:
			dfr_Layout.loc[0,"WellType"][pf.well_to_index(dfr_References.loc[i,"Well"],int_PlateFormat)] = "b"

	return dfr_References_Return, dfr_Layout

##########################################################
##                                                      ##
##     #####  ##  ##   ####   #####   ######  #####     ##
##    ##      ##  ##  ##  ##  ##  ##  ##      ##  ##    ##
##     ####   ######  ######  #####   ####    ##  ##    ##
##        ##  ##  ##  ##  ##  ##  ##  ##      ##  ##    ##
##    #####   ##  ##  ##  ##  ##  ##  ######  #####     ##
##                                                      ##
##########################################################

def get_CompleteContainer(dfr_PlateAssignment,str_DataPath,dfr_TransferFile, dfr_Exceptions,dfr_Layout,dfr_Details,dlg_Progress):
	str_AssayName = dfr_Details.loc["AssayType","Value"]
	str_AssayCategory = dfr_Details.loc["AssayCategory","Value"]
	str_AssayVolume = dfr_Details.loc["AssayVolume","Value"]
	str_SampleSource = dfr_Details.loc["SampleSource","Value"]
	str_Device = dfr_Details.loc["Device","Value"]
	# Assay category is broad: single_dose, IC50 (or dose response), DSF_384...
	# Count how many rows we need:
	intRows = 0
	for i in range(dfr_PlateAssignment.shape[0]):
		if dfr_PlateAssignment.loc[i,"DataFile"] != "":
			intRows += 1
	dlg_Progress.lbx_Log.InsertItems(["Assay category: " + str_AssayCategory], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
	dfr_Container = pd.DataFrame(columns=["DestinationPlateName","Samples","Wells","DataFileName",
		"RawDataFrame","ProcessedDataFrame","Layout","References"], index=range(intRows))
	# Iterate through the dfr_PlateAssignment frame
	for i in range(dfr_PlateAssignment.shape[0]):
		if dfr_PlateAssignment.loc[i,"DataFile"] != "":
			dfr_Container.loc[i,"DestinationPlateName"] = dfr_PlateAssignment.loc[i,"TransferEntry"]
			dlg_Progress.lbx_Log.InsertItems(["Processing plate " + str(i+1) + ": " + str(dfr_Container.loc[i,"DestinationPlateName"])], dlg_Progress.lbx_Log.Count)
			dlg_Progress.lbx_Log.InsertItems(["==============================================================="], dlg_Progress.lbx_Log.Count)
			dfr_Container.loc[i,"Wells"] = int(dfr_PlateAssignment.loc[i,"Wells"])
			dfr_Container.loc[i,"DataFileName"] = dfr_PlateAssignment.loc[i,"DataFile"]
			# Get raw data
			dlg_Progress.lbx_Log.InsertItems(["Read raw data file: " + dfr_Container.loc[i,"DataFileName"]], dlg_Progress.lbx_Log.Count)
			if str_AssayCategory == "dose_response_time_course":
				if str_Device == "pherastar":
					dfr_Container.at[i,"RawDataFrame"] = ro.get_bmg_DRTC_readout(str_DataPath + chr(92) + dfr_Container.loc[i,"DataFileName"])
				elif str_Device == "flipr":
					dfr_Container.at[i,"RawDataFrame"] = ro.get_FLIPR_DRTC_readout(str_DataPath + chr(92) + dfr_Container.loc[i,"DataFileName"])
				else:
					return None
			elif str_AssayCategory.find("dose_response") != -1:
				dfr_Container.at[i,"RawDataFrame"] = ro.get_bmg_plate_readout(str_DataPath,dfr_Container.loc[i,"DataFileName"],
					dfr_Container.loc[i,"Wells"],str_AssayName)
			elif str_AssayCategory.find("single_dose") != -1:
				# All plates will be the same plate type!
				dfrRawData = ro.get_bmg_list_readout(str_DataPath, int(dfr_PlateAssignment.loc[0,"Wells"]))
				dfr_Container.at[i,"RawDataFrame"] = dfrRawData[["Well",dfr_Container.loc[i,"DataFileName"]]]
			elif str_AssayCategory == "thermal_shift":
				if str_AssayName == "DSF_MX_96":
					dfr_Container.at[i,"RawDataFrame"] = ro.get_mxp_readout(str_DataPath + chr(92) + dfr_Container.loc[i,"DataFileName"], 24) # last argument is NOT number of wells but starting temperature!
				elif str_AssayName == "DSF_LC_96":
					dfr_Container.at[i,"RawDataFrame"] = ro.get_lightcycler_readout(str_DataPath + chr(92) + dfr_Container.loc[i,"DataFileName"], 96)
				elif str_AssayName == "DSF_LC_384":
					dfr_Container.at[i,"RawDataFrame"] = ro.get_lightcycler_readout(str_DataPath + chr(92) + dfr_Container.loc[i,"DataFileName"], 384)
			elif str_AssayCategory == "rate":
				dfr_Container.at[i,"RawDataFrame"] = ro.get_bmg_timecourse_readout(str_DataPath + dfr_Container.loc[i,"DataFileName"])
			# Test whether a correct file was loaded:
			if dfr_Container.loc[i,"RawDataFrame"] is None: # == False:
				msg.FileNotData("self")
				return None
			# Get samples
			if str_SampleSource == "echo":
				dlg_Progress.lbx_Log.InsertItems(["Extract sample IDs from transfer file"], dlg_Progress.lbx_Log.Count)
				dfr_Container.at[i,"Samples"] = get_samples(dfr_TransferFile,dfr_Container.loc[i,"DestinationPlateName"],dfr_Container.loc[i,"Wells"])
			elif str_SampleSource == "lightcycler":
				dlg_Progress.lbx_Log.InsertItems(["Extract sample IDs from raw data file"], dlg_Progress.lbx_Log.Count)
				dfr_Container.at[i,"Samples"] = get_samples_lightcycler(dfr_Container.loc[i,"DestinationPlateName"],dfr_Container.at[i,"RawDataFrame"],len(dfr_Layout.loc[i,"ProteinNumerical"]))
			elif str_SampleSource == "well":
				dfr_Container.at[i,"Samples"] = get_samples_wellonly(dfr_Container.loc[i,"DestinationPlateName"],dfr_Container.at[i,"RawDataFrame"],len(dfr_Layout.loc[i,"ProteinNumerical"]))
			if str_AssayCategory == "thermal_shift":
				# References get handled differently here
				if len(dfr_Layout) > 1:
					idx_Layout = i
				else:
					idx_Layout = 0
				# This is totally more complicated than it needs to be, but seems to be the only way this works. Shrug.
				dfr_Container.at[i,"Layout"] = pd.DataFrame(index=[0],columns=["PlateID","ProteinNumerical","PurificationID","Concentration","WellType"])
				dfr_Container.loc[i,"Layout"].at[0,"PlateID"] = dfr_Layout.loc[idx_Layout,"PlateID"]
				dfr_Container.loc[i,"Layout"].at[0,"ProteinNumerical"] = dfr_Layout.loc[idx_Layout,"ProteinNumerical"]
				dfr_Container.loc[i,"Layout"].at[0,"PurificationID"] = dfr_Layout.loc[idx_Layout,"PurificationID"]
				dfr_Container.loc[i,"Layout"].at[0,"Concentration"] = dfr_Layout.loc[idx_Layout,"Concentration"]
				dfr_Container.loc[i,"Layout"].at[0,"WellType"] = dfr_Layout.loc[idx_Layout,"WellType"]
				# Create dataframe for data processing
				dfr_Container.at[i,"ProcessedDataFrame"], dfr_Container.at[i,"References"] = create_dataframe_DSF(dfr_Container.at[i,"RawDataFrame"],
					dfr_Container.loc[i,"Samples"], dfr_Layout.loc[idx_Layout], dlg_Progress)
			elif str_AssayCategory.find("rate") != -1:
				# References get handled differently here
				dfr_Container.at[i,"Layout"] = get_layout(dfr_TransferFile,dfr_Container.loc[i,"DestinationPlateName"],
					dfr_Container.loc[i,"DataFileName"],dfr_Container.loc[i,"RawDataFrame"])
				# Create dataframe for data processing
				dfr_Container.at[i,"ProcessedDataFrame"], dfr_Container.at[i,"References"] = create_dataframe_rate(dfr_Container.at[i,"RawDataFrame"],
					dfr_Container.loc[i,"Samples"],dfr_Container.loc[i,"References"],dlg_Progress)
			elif str_AssayCategory == "dose_response_time_course":
				# Get References
				dfr_Container.at[i,"References"], dfr_Container.at[i,"Layout"] = get_references_DRTC(dfr_TransferFile,dfr_Container.loc[i,"DestinationPlateName"],
					dfr_Container.loc[i,"DataFileName"],dfr_Container.loc[i,"RawDataFrame"])
				dfr_Container.at[i,"ProcessedDataFrame"] = create_dataframe_DRTC_MP(dfr_Container.at[i,"RawDataFrame"],
					dfr_Container.loc[i,"Samples"],dfr_Container.loc[i,"References"],str_AssayVolume,dlg_Progress)
			else:
				# Endpoint assays
				# Get controls and references
				dfr_Container.at[i,"References"], dfr_Container.at[i,"Layout"] = get_references(dfr_TransferFile, dfr_Exceptions,dfr_Container.loc[i,"DestinationPlateName"],
					dfr_Container.loc[i,"DataFileName"],dfr_Container.loc[i,"RawDataFrame"])
				if pd.isna(dfr_Container.loc[i,"References"].loc["SolventMean",0]) == True:
					dlg_Progress.lbx_Log.InsertItems(["Note: No Solvent wells"], dlg_Progress.lbx_Log.Count)
				if pd.isna(dfr_Container.loc[i,"References"].loc["ControlMean",0]) == True:
					dlg_Progress.lbx_Log.InsertItems(["Note: No control wells"], dlg_Progress.lbx_Log.Count)
				if pd.isna(dfr_Container.loc[i,"References"].loc["BufferMean",0]) == True:
					dlg_Progress.lbx_Log.InsertItems(["Note: No buffer wells"], dlg_Progress.lbx_Log.Count)
				# Create dataframe for data processing
				if str_AssayCategory.find("dose_response") != -1:
					dfr_Container.at[i,"ProcessedDataFrame"] = create_dataframe_EPDR(dfr_Container.at[i,"RawDataFrame"],
						dfr_Container.loc[i,"Samples"],dfr_Container.loc[i,"References"],str_AssayName,str_AssayVolume,dlg_Progress)
				elif str_AssayCategory.find("single_dose") != -1:
					dfr_Container.at[i,"ProcessedDataFrame"] = create_dataframe_EPSD(dfr_Container.at[i,"RawDataFrame"],
						dfr_Container.loc[i,"Samples"],dfr_Container.loc[i,"References"],str_AssayName,str_AssayVolume,dlg_Progress)
			dlg_Progress.lbx_Log.InsertItems(["Plate "+ str(i+1) + " completed"], dlg_Progress.lbx_Log.Count)
			dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)

	return dfr_Container

def ProgressGauge(current,total):
	int_Length = 20
	int_Full = int(round(current/total * int_Length,0))
	int_Blank = int_Length - int_Full
	str_Full = chr(9646)
	str_Blank = chr(9647)
	str_Gauge = "[" + int_Full*str_Full + int_Blank*str_Blank + "]"
	return str_Gauge

def Mean_SEM_STDEV(lst_Values):
	"""
	Calculates Mean, Standard Error of Mean and STandard DEViation for a list of values.
	Previously used my own function and doing it manually. But why do that if numpy can do it faster?
	"""
	if any_nonnan(lst_Values) == True:
		flt_Mean = round(np.nanmean(lst_Values),2)
		flt_STDEV= np.std(lst_Values, ddof=1)
		flt_SEM = flt_STDEV / np.sqrt(np.size(lst_Values))
		return flt_Mean, flt_SEM, flt_STDEV
	else:
		return np.nan, np.nan, np.nan

def Mean_SEM_STDEV_ListList(lstlstRawData):
	"""
	Helper function to calculate Mean, SEM and STDEV in a list of lists (e.g. for a series of concentrations with replicate values at each point)
	"""
	lst_Mean = []
	lst_STDEV = []
	lst_SEM = []
	
	for lst_Elem in lstlstRawData:
		Mean, SEM, STDEV = Mean_SEM_STDEV(lst_Elem)
		lst_Mean.append(Mean)
		lst_SEM.append(SEM)
		lst_STDEV.append(STDEV)

	return lst_Mean, lst_SEM, lst_STDEV

def MedianAbsoluteDeviation(input):
	if any_nonnan(input) == True:
		median = input.median()
		input = abs(input-median)
		MedAbDev = input.median()
		return MedAbDev
	return np.nan

def MAD_list(input):
	"""
	Calculates mean absolute deviation for a list of values.
	Returns np.nan if there are no numeric values in the list.
	"""
	if any_nonnan(input) == True:
		median = np.nanmedian(input)
		input = abs(input-median)
		return np.nanmedian(input)
	else:
		return np.nan

def moles_to_micromoles(lst_Conc):
	"""
	Turns moles/molar into micromoles/micromolar
	"""
	# initialise list
	lst_ConcMicro = []
	for i in range(len(lst_Conc)):
		# Convert to micromoles/ar
		concentration = float(lst_Conc[i])*1000000
		# cut off beyond 5th decimal
		concentration = int(concentration*100000)/100000
		# add to list
		lst_ConcMicro.append(concentration)
	# remove dummy element from list
	return lst_ConcMicro

def make_list(n,item):
	"""
	Makes a list of n idential elements
	"""
	lst = []
	for i in range(n):
		lst.append(item)
	return lst

def set_to_nan(count):
	return make_list(count, np.nan)

def any_nonnan(lst_Values):
	"""
	Tests a list to see if there are _any_ elements that are NOT nan.
	Previous version actually went through the whole list and counted the non-nan values. Returned True when the count was > 0.
	For the purposes of this function, we can just return True as soon as we encounter a value that is not nan.
	"""
	for item in lst_Values:
		# Return True as soon as a non-nan value is encountered
		if np.isnan(item) == False:
			return True
	# If there are only nan values, we get to this point and return False
	return False

def import_string_to_list(str_Input):
	"""
	Convert strings of this format "['1.1','2.2','3.3']" into actual lists.
	Also takes into accound possibility of lists of lists.
	"""
	if type(str_Input) == str and str_Input.find("[") != -1 and str_Input.find("]") != -1 and str_Input.find("Destination") == -1: # str_Input.find(",") != -1:
		# Determine the list separator
		if str_Input.find(",") != -1:
			str_Separator = ", "
		else:
			str_Separator = " "
		lst_Converted = []
		# Make sure we can handle lists of lists
		# If we are dealing with a simple list, there will only be one pair of square brackets
		if str_Input.count("[") == 1:
			# Truncate string by first and last (i.e. [ and ]) and split by str_Separator
			lst_Parsed = list(str_Input[1:int(len(str_Input)-1)].split(str_Separator))
			for i in range(len(lst_Parsed)):
				# This is included because in IC50 curves I use "found"as keyword for concentrations with replicates
				if lst_Parsed[i].find("found") != -1:
					lst_Converted.append(lst_Parsed[i])
				elif len(lst_Parsed[i]) > 0:
					# Take care of single quotes surrounding strings: If single quotes, we are working with actual lists of strings, not numbers stored as strings.
					if lst_Parsed[i].find("'") == -1:
						if lst_Parsed[i] == "True":
							lst_Converted.append(True)
						elif lst_Parsed[i] == "False":
							lst_Converted.append(False)
						else:
							lst_Converted.append(float(lst_Parsed[i]))
					else:
						lst_Converted.append(lst_Parsed[i][1:(len(lst_Parsed[i])-1)])
		else:
			# Nowe we deal with lists of lists
			# Remove square brackets at outside of string
			str_ListOfLists = str_Input[1:int(len(str_Input)-1)]
			# Variable to keep track of which level we are on:
			lst_Toplevel = []
			str_Temp = ""
			open = False
			for i in range(len(str_ListOfLists)):
				#if i > 0 and i < (len(str_ListOfLists)-1): #Second condition needs adjusting to account for base 0 of indexing in pyton.
				if open == True:
					str_Temp = str_Temp + str_ListOfLists[i]
				if str_ListOfLists[i] == "[":
					open = True
				elif str_ListOfLists[i] == "]":
					open = False
				if open == False and str_Temp != "":
					if str_Temp.find(",") != -1:
						str_Separator = ", "
					else:
						str_Separator = " "
					lst_Append = list(str_Temp[0:int(len(str_Temp)-1)].split(str_Separator))
					lst_Converted.append([])
					for j in range(len(lst_Append)):
						if lst_Append[j] != "''":
							lst_Converted[len(lst_Converted)-1].append(lst_Append[j])
					str_Temp = ""
			# Convert to numbers, of possible
			for i in range(len(lst_Converted)):
				for j in range(len(lst_Converted[i])):
					try:
						lst_Converted[i][j] = int(lst_Converted[i][j])
					except:
						try: lst_Converted[i][j] = float(lst_Converted[i][j])
						except: None
	else:
		return str_Input
	return lst_Converted

def get_csv_columns(str_TransferFile):
	# This works, but is super slow. Leave here for posterity
	file = open(str_TransferFile)
	int_MaxColumns = 0
	int_MaxRows = 0

	bol_FoundStart = False
	lst_Test = []
	# Iterate through the csv file
	for row in file.readlines():
		# First check: See if we have found the start:
		if bol_FoundStart == True:
			pd.read_csv(file, sep=",", header=0, index_col=False, engine="python")
			# Second check: Stop if we are in the last line!
			if row.find("Instrument Name") != -1:
				# If this is found, it means that we have reached the end of the transfer data
				break
			else:
				lst_Test.append(row.split(","))
				int_Columns = len(lst_Test[-1]) #length of last item in list
				if int_Columns > int_MaxColumns:
					int_MaxColumns = int_Columns
				int_MaxRows += 1
		else:
			if row.find("[DETAILS]") != -1:
				bol_FoundStart = True

	# create the dataframe
	dfr_TransferFile = pd.DataFrame(columns=range(int_MaxColumns),index=range(int_MaxRows))
	for i in range(int_MaxRows):
		for j in range(len(lst_Test[i])):
			dfr_TransferFile.iloc[i,j] = lst_Test[i][j]

	return int_MaxColumns

def string_or_na(value):
	if pd.isna(value) == True or value == "":
		return "NA"
	elif type(value) != str:
		return str(value)
	else:
		return value

def change_concentrations(flt_OldStock,flt_NewStock,lst_Concentrations,str_AssayVolume):
	# Changes concentrations based on new stock concentration and transfer volumes
	flt_AssayVolume = float(str_AssayVolume)
	# AssayConc = (TransferVolume*StockConc)/AssayVolume
	#for i in range(len(lstConcentrations)):
		#TransferVolume = (float(lstConcentrations[i])/fltOldStock) * fltAssayVolume
		# There were issues when writing the new list concentrations into the dataframe due to rounding errors (sometimes there were many zeros followed by a nonzero,
		# for example after changing a source concentration and then chaning it back to the original value  2.24E-5 would turn into 0.00022400000000000002, with
		# pandas unable to write the new list over the old). Solution was rounding off the offending digits.
		#flt_NewConc = round(((TransferVolume*fltNewStock)/fltAssayVolume)*100000000000,0)/100000000000
		#lstNewConc.append(flt_NewConc)
	TransferVolume = (float(lst_Concentrations)/flt_OldStock) * flt_AssayVolume
	flt_NewConc = round(((TransferVolume*flt_NewStock)/flt_AssayVolume)*100000000000,0)/100000000000
	return flt_NewConc

def nearest(list, item, index=False):
	# https://www.geeksforgeeks.org/python-find-closest-number-to-k-in-given-list/
	if any_nonnan(list) == True:
		list = np.asarray(list)
		list_nonan = list[np.logical_not(np.isnan(list))]
		idx = (np.abs(list_nonan - item)).argmin()
		if index == False:
			return list_nonan[idx]
		else:
			return idx
	else:
		return np.nan

def Normalise(lst_Readings,str_AssayType,dfr_References):
	flt_Solvent = dfr_References.loc["SolventMean",0]
	flt_Control = dfr_References.loc["ControlMean",0]
	flt_Buffer = dfr_References.loc["BufferMean",0]
	lstNorm = []
	# Check if there are controls:
	if pd.isna(flt_Control) == True:
		flt_Control = 0
	# Check which reference to use
	if pd.isna(flt_Solvent) == True:
		flt_Reference = flt_Buffer - flt_Control
	else:
		flt_Reference = flt_Solvent - flt_Control
	# run check for assay type str_AssayType was saved in lst_Details[0]
	if str_AssayType == "HTRF":
		# for HTRF
		for i in range(len(lst_Readings)):
			lstNorm.append(round(100 * (1-((lst_Readings[i] - flt_Control)/flt_Reference)),2))
	elif str_AssayType == "TAMRA FP":
		flt_Control = flt_Control - flt_Reference
		for i in range(len(lst_Readings)):
			lstNorm.append(round(100 * ((lst_Readings[i] - flt_Reference) / flt_Control),2)) # lstNorm.append(round(100 * (((lstRaw[i] - flt_Reference) / (flt_Control))),2))
	elif str_AssayType == "AlphaScreen" or str_AssayType.find("Glo") != -1:
		for i in range(len(lst_Readings)):
			lstNorm.append(round(100 * (1 - ((lst_Readings[i] - flt_Control) / flt_Reference)),2))
	return lstNorm

##########################################
##                                      ##
##    ######  #####   #####   #####     ##
##    ##      ##  ##  ##  ##  ##  ##    ##
##    ####    #####   ##  ##  #####     ##
##    ##      ##      ##  ##  ##  ##    ##
##    ######  ##      #####   ##  ##    ##
##                                      ##
##########################################

def create_dataframe_EPDR(dfr_RawData, dfr_Samples, dfr_References, str_AssayType, str_AssayVolume, dlg_Progress):
	"""
	This function is for endpoint protein-peptide interaction/displacement assays such as HTRF, AlphaScreen or endpoint assays of enzymatic
	reactions such as the "Glo" family of assays.
	Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
	and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
	to calculate values based on the assay type.
	"""
	# Get number of samples:
	int_Samples = len(dfr_Samples)
	# Create new dataframe
	lst_Columns = ["DestinationPlateName","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData",
		"Raw","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
		"Norm","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoFitFree",
		"NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoFitConst",
		"Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
	fltAssayVolume = float(str_AssayVolume)
	# Check each concentration if it occurs more than once, then write it into a new list and add the corresponding locations
	# to a list and add that list to a list. Once finished, overwrite columns Locations and Concentration with the new list.
	# dfr_Samples must have been sorted for Concentration for this to work properly.
	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)
	for smpl in range(int_Samples):
		# Pull list of concentrations for current sample
		lstConc = dfr_Samples.loc[smpl,"Concentrations"]
		lstLoc = dfr_Samples.loc[smpl,"Locations"]
		#lstRaw = dfr_Processed.loc[i, "RawData"]
		# Create list of lists:
		lstlstConc = [] # list of lists for concentrations
		lstlstLoc = [] # list of lists for locations
		lstlstRaw = [] # list of lists for raw data
		lstRawExcluded = [] # list of excluded values
		lstNormExcluded = []
		# Go through list of concentrations
		for conc in range(len(lstConc)):
			lstConcTemp = []
			lstRawTemp = []
			lstLocTemp = []
			# Check to only use unique concentrations
			if lstConc[conc] != "found":
				# assign current conc/loc to temporary lists
				lstConcTemp = lstConc[conc] # simple list
				lstLocTemp = [lstLoc[conc]] # list of lists, one concentration can be in many locations
				lstRawTemp = [dfr_RawData.iloc[lstLoc[conc],1]]
				for k in range(conc+1,len(lstConc)):
					if lstConc[conc] == lstConc[k]:
						lstConc[k] = "found" # flag concentrations that are not unique
						lstLocTemp.append(lstLoc[k])
						lstRawTemp.append(dfr_RawData.iloc[lstLoc[k],1])
				# append temporary list to list of lists
				lstlstConc.append(lstConcTemp)
				lstlstLoc.append(lstLocTemp)
				lstlstRaw.append(lstRawTemp)
				# Create excluded list, initialised with np.nan in the first instance
				lstRawExcluded.append(np.nan)
				lstNormExcluded.append(np.nan)
		# Assign list of lists to dataframe
		dfr_Processed.loc[smpl,"DestinationPlateName"] = dfr_Samples.loc[smpl,"DestinationPlateName"]
		dfr_Processed.loc[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
		dfr_Processed.loc[smpl,"SourceConcentration"] = dfr_Samples.loc[smpl,"SourceConcentration"]
		dfr_Processed.loc[smpl,"Concentrations"] = lstlstConc
		dfr_Processed.loc[smpl,"AssayVolume"] = fltAssayVolume
		dfr_Processed.loc[smpl,"Locations"] = lstlstLoc
		dfr_Processed.loc[smpl,"RawData"] = lstlstRaw
		dfr_Processed.loc[smpl,"Raw"], dfr_Processed.loc[smpl,"RawSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstRaw)
		dfr_Processed.loc[smpl,"RawExcluded"] = lstRawExcluded

		# Normalisation needs to happen before datafitting is attempted
		lstlstNorm = []
		for j in range(len(lstlstRaw)):
			lstlstNorm.append(Normalise(lstlstRaw[j], str_AssayType, dfr_References))
		dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstNorm)
		dfr_Processed.loc[smpl,"NormExcluded"] = lstNormExcluded

		# Fitting criteria
		# Exclude points where the NormSEM is > 20%
		for j in range(len(dfr_Processed.loc[smpl,"Raw"])):
			if dfr_Processed.loc[smpl,"NormSEM"][j] > 20:
				dfr_Processed.loc[smpl,"RawExcluded"][j] = dfr_Processed.loc[smpl,"Raw"][j]
				dfr_Processed.loc[smpl,"Raw"][j] = np.nan
				dfr_Processed.loc[smpl,"NormExcluded"][j] = dfr_Processed.loc[smpl,"Norm"][j]
				dfr_Processed.loc[smpl,"Norm"][j] = np.nan
			else:
				dfr_Processed.loc[smpl,"RawExcluded"][j] = np.nan
				dfr_Processed.loc[smpl,"NormExcluded"][j] = np.nan
		# Criteria for fit:
		dfr_Processed.loc[smpl,"DoFit"] = get_DoFit(dfr_Processed.loc[smpl,"Norm"],dfr_Processed.loc[smpl,"NormSEM"])
		# Perform fit -> Check if fitting criteria are met in the first instance
		if dfr_Processed.loc[smpl,"DoFit"] == True:
			dfr_Processed.loc[smpl,"RawFit"], dfr_Processed.loc[smpl,"RawFitPars"], dfr_Processed.loc[smpl,"RawFitCI"], dfr_Processed.loc[smpl,"RawFitErrors"], dfr_Processed.loc[smpl,"RawFitR2"], dfr_Processed.loc[smpl,"DoFitRaw"] = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Raw"])
			dfr_Processed.loc[smpl,"NormFitFree"], dfr_Processed.loc[smpl,"NormFitFreePars"], dfr_Processed.loc[smpl,"NormFitFreeCI"], dfr_Processed.loc[smpl,"NormFitFreeErrors"], dfr_Processed.loc[smpl,"NormFitFreeR2"], dfr_Processed.loc[smpl,"DoFitFree"] = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Norm"])
			# Constrained fit needs SEM for fit
			dfr_Processed.loc[smpl,"NormFitConst"], dfr_Processed.loc[smpl,"NormFitConstPars"], dfr_Processed.loc[smpl,"NormFitConstCI"], dfr_Processed.loc[smpl,"NormFitConstErrors"], dfr_Processed.loc[smpl,"NormFitConstR2"], dfr_Processed.loc[smpl,"DoFitConst"] = ff.fit_sigmoidal_const(dfr_Processed.loc[smpl,"Concentrations"], dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"])
			# If both the free and constrained fit fail, set check variable to False
			if dfr_Processed.loc[smpl,"DoFitFree"] == False and dfr_Processed.loc[smpl,"DoFitConst"] == False:
				dfr_Processed.loc[smpl,"DoFit"] = False
		else:
			dfr_Processed.loc[smpl,"RawFit"], dfr_Processed.loc[smpl,"RawFitPars"] = set_to_nan(len(dfr_Processed.loc[smpl,"Raw"])), set_to_nan(4)
			dfr_Processed.loc[smpl,"RawFitCI"], dfr_Processed.loc[smpl,"RawFitErrors"] = set_to_nan(4), set_to_nan(4)
			dfr_Processed.loc[smpl,"RawFitR2"] = np.nan
			dfr_Processed.loc[smpl,"DoFitRaw"] = False
			dfr_Processed.loc[smpl,"NormFitFree"],dfr_Processed.loc[smpl,"NormFitFreePars"] = set_to_nan(len(dfr_Processed.loc[smpl,"Raw"])), set_to_nan(4)
			dfr_Processed.loc[smpl,"NormFitFreeCI"], dfr_Processed.loc[smpl,"NormFitFreeErrors"] = set_to_nan(4), set_to_nan(4)
			dfr_Processed.loc[smpl,"NormFitFreeR2"] = np.nan
			dfr_Processed.loc[smpl,"DoFitFree"] = False
			dfr_Processed.loc[smpl,"NormFitConst"],dfr_Processed.loc[smpl,"NormFitConstPars"] = set_to_nan(len(dfr_Processed.loc[smpl,"Raw"])), set_to_nan(4)
			dfr_Processed.loc[smpl,"NormFitConstCI"], dfr_Processed.loc[smpl,"NormFitConstErrors"] = set_to_nan(4), set_to_nan(4)
			dfr_Processed.loc[smpl,"NormFitConstR2"] = np.nan
			dfr_Processed.loc[smpl,"DoFitConst"] = False

		dfr_Processed.loc[smpl,"Show"] = 1
		dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(smpl+1,int_Samples) + " " + str(smpl+1) + " out of " + str(int_Samples) + " samples.")

	# Return
	return dfr_Processed

def create_Database_frame_EPDR(dfr_Details,lstHeaders,dfr_PlateData,dfr_References):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):
		if dfr_PlateData.loc[i,"SampleID"] != "Control":
			dfr_Partial.iloc[i,0] = dfr_Details.loc["AssayType","Value"] + " IC50" # Assay type
			dfr_Partial.iloc[i,1] = dfr_Details.loc["PurificationID","Value"] # Purification ID
			dfr_Partial.iloc[i,2] = float(dfr_Details.loc["ProteinConcentration","Value"])/1000 # protein concentration in uM. Form is in nM.
			dfr_Partial.iloc[i,3] = dfr_Details.loc["PeptideID","Value"] # PeptideID
			dfr_Partial.iloc[i,4] = dfr_PlateData.loc[i,"SampleID"] # Sample ID/Global Compound ID
			dfr_Partial.iloc[i,5] = float(dfr_Details.loc["PeptideConcentration","Value"])/1000 # peptide concentration in uM. Form is in nM.
			dfr_Partial.iloc[i,6] = dfr_Details.loc["Solvent","Value"] # solvent
			dfr_Partial.iloc[i,7] = dfr_Details.loc["SolventConcentration","Value"] # solvent concentration in %
			dfr_Partial.iloc[i,8] = dfr_Details.loc["Buffer","Value"] # Buffer
			# dfr_Partial.iloc[i,9] = # compound incubation time
			# dfr_Partial.iloc[i,10] = # peptide incubation time
			# dfr_Partial.iloc[i,11] = # bead incubation time
			dfr_Partial.iloc[i,12] = 22 # incubation temperature
			if dfr_PlateData.loc[i,"DoFit"] == True:
				if dfr_PlateData.loc[i,"Show"] == 0:
					str_Pars = "RawFitPars"
					str_CI = "RawFitCI"
					str_Errors = "RawFitErrors"
					str_RSquare = "RawFitR2"
				elif dfr_PlateData.loc[i,"Show"] == 1:
					str_Pars = "NormFitFreePars"
					str_CI = "NormFitFreeCI"
					str_Errors = "NormFitFreeErrors"
					str_RSquare = "NormFitFreeR2"
				elif dfr_PlateData.loc[i,"Show"] == 2:
					str_Pars = "NormFitConstPars"
					str_CI = "NormFitConstCI"
					str_Errors = "NormFitConstErrors"
					str_RSquare = "NormFitConstR2"
				dfr_Partial.iloc[i,13] = np.log10(float(dfr_PlateData.loc[i,str_Pars][3])/1000000)# log10 IC50. IC50 is stored in uM!
				dfr_Partial.iloc[i,14] = dfr_PlateData.loc[i,str_Errors][3]
				dfr_Partial.iloc[i,15] = float(dfr_PlateData.loc[i,str_Pars][3]) # IC50 in uM
				dfr_Partial.iloc[i,16] = dfr_PlateData.loc[i,str_Pars][3] + dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.iloc[i,17] = dfr_PlateData.loc[i,str_Pars][3] - dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.iloc[i,18] = float(dfr_PlateData.loc[i,str_Pars][2]) # Hill slope
				# dfr_Partial.iloc[i,19] = # curve
				dfr_Partial.iloc[i,20] = float(dfr_PlateData.loc[i,str_Pars][1]) # bottom of curve fit
				dfr_Partial.iloc[i,21] = float(dfr_PlateData.loc[i,str_Pars][0]) # top of curve fit
				dfr_Partial.iloc[i,22] = dfr_PlateData.loc[i,str_RSquare]# R square value
				# dfr_Partial.iloc[i,23] = # data quality
				dfr_Partial.iloc[i,24] = "Free fit"# comments on curve classification and definitions
			else:
				dfr_Partial.iloc[i,13] = np.nan
				dfr_Partial.iloc[i,14] = np.nan
				dfr_Partial.iloc[i,15] = np.nan
				dfr_Partial.iloc[i,16] = np.nan
				dfr_Partial.iloc[i,17] = np.nan
				dfr_Partial.iloc[i,18] = np.nan
				# dfr_Partial.iloc[i,19] = # curve
				dfr_Partial.iloc[i,20] = np.nan
				dfr_Partial.iloc[i,21] = np.nan
				dfr_Partial.iloc[i,22] = np.nan
				# dfr_Partial.iloc[i,23] = # data quality
				dfr_Partial.iloc[i,24] = "not fitted" # comments on curve classification and definitions
			dfr_Partial.iloc[i,25] = dfr_References.loc["SolventMean",0] # enzyme reference
			dfr_Partial.iloc[i,26] = dfr_References.loc["SolventSEM",0] # enzyme reference error
			lstConcentrations = moles_to_micromoles(dfr_PlateData.loc[i,"Concentrations"])
			for j in range(len(lstConcentrations)):
				intColumnOffset = (j)*3
				dfr_Partial.iloc[i,27+intColumnOffset] = lstConcentrations[j]
				dfr_Partial.iloc[i,28+intColumnOffset] = dfr_PlateData.loc[i,"Norm"][j]
				dfr_Partial.iloc[i,29+intColumnOffset] = dfr_PlateData.loc[i,"NormSEM"][j]
			try: 
				dfr_Partial.iloc[i,79] = round(dfr_References.loc["ZPrimeMean",0],3) # ZPrime
			except:
				dfr_Partial.iloc[i,79] = ""
			try:
				dfr_Partial.iloc[i,80] = round(dfr_References.loc["ZPrimeMedian",0],3) # ZPrimeRobust
			except:
				dfr_Partial.iloc[i,80] = ""
			try:
				dfr_Partial.iloc[i,81] = round(dfr_References.loc["SolventMean",0]/dfr_References.loc["ControlMean",0],3) # Solvent/Control
			except:
				dfr_Partial.iloc[i,81] = ""
			try:
				dfr_Partial.iloc[i,82] = round(dfr_References.loc["BufferMean",0]/dfr_References.loc["ControlMean",0],3) # Buffer/Control
			except:
				dfr_Partial.iloc[i,82] = ""
			dfr_Partial.iloc[i,83] = dfr_Details.loc["Date","Value"] # Date of Experiment
			dfr_Partial.iloc[i,84] = dfr_Details.loc["ELN","Value"] # ELN Page
			dfr_Partial.iloc[i,85] = ""
	
	return dfr_Partial

def create_Database_frame_EPDR_New(dfr_Details,lstHeaders,dfr_PlateData,dfr_References):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):
		if dfr_PlateData.loc[i,"SampleID"] != "Control":
			dfr_Partial.loc[i,"Experiment Type"] = dfr_Details.loc["AssayType","Value"] + " IC50"
			dfr_Partial.loc[i,"Purification ID"] = dfr_Details.loc["PurificationID","Value"] # Purification ID
			# Target ID
			dfr_Partial.loc[i,"Protein Concentration (uM)"] = float(dfr_Details.loc["ProteinConcentration","Value"])/1000 # Assay details form is in nM.
			dfr_Partial.loc[i,"Peptide ID"] = dfr_Details.loc["PeptideID","Value"]
			dfr_Partial.loc[i,"Compound ID"] = dfr_PlateData.loc[i,"SampleID"]
			dfr_Partial.loc[i,"Peptide Concentration (uM)"] = float(dfr_Details.loc["PeptideConcentration","Value"])/1000 # Assay details form is in nM.
			dfr_Partial.loc[i,"Solvent"] = dfr_Details.loc["Solvent","Value"]
			dfr_Partial.loc[i,"Solvent Concentration (%)"] = dfr_Details.loc["SolventConcentration","Value"]
			dfr_Partial.loc[i,"Buffer"] = dfr_Details.loc["Buffer","Value"]
			# dfr_Partial.loc[i,"Compound Incubation Time (mins)"]
			# dfr_Partial.loc[i,"Peptide Incubation Time (mins)"]
			# dfr_Partial.loc[i,"Bead Incubation Time (mins)"]
			dfr_Partial.loc[i,"Incubation Temperatures (C)"] = 22
			if dfr_PlateData.loc[i,"DoFit"] == True:
				if dfr_PlateData.loc[i,"Show"] == 0:
					str_Pars = "RawFitPars"
					str_CI = "RawFitCI"
					str_Errors = "RawFitErrors"
					str_RSquare = "RawFitR2"
				elif dfr_PlateData.loc[i,"Show"] == 1:
					str_Pars = "NormFitFreePars"
					str_CI = "NormFitFreeCI"
					str_Errors = "NormFitFreeErrors"
					str_RSquare = "NormFitFreeR2"
				elif dfr_PlateData.loc[i,"Show"] == 2:
					str_Pars = "NormFitConstPars"
					str_CI = "NormFitConstCI"
					str_Errors = "NormFitConstErrors"
					str_RSquare = "NormFitConstR2"
				dfr_Partial.loc[i,"LogIC50 (relative to 1M)"] = np.log10(float(dfr_PlateData.loc[i,str_Pars][3])/1000000)# log10 IC50. IC50 is stored in uM!
				dfr_Partial.loc[i,"LogIC50 error"] = dfr_PlateData.loc[i,str_Errors][3]
				dfr_Partial.loc[i,"IC50"] = float(dfr_PlateData.loc[i,str_Pars][3]) # IC50 in uM
				dfr_Partial.loc[i,"Curve Fit: Upper 95% ConfLimit"] = dfr_PlateData.loc[i,str_Pars][3] + dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.loc[i,"Curve Fit: Lower 95% ConfLimit"] = dfr_PlateData.loc[i,str_Pars][3] - dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.loc[i,"Curve Fit: Hill Slope"] = float(dfr_PlateData.loc[i,str_Pars][2]) # Hill slope
				# dfr_Partial.loc[i,"Curve (Obsolete)"] = # curve
				dfr_Partial.loc[i,"Curve Fit: Bottom"] = float(dfr_PlateData.loc[i,str_Pars][1])
				dfr_Partial.loc[i,"Curve Fit: Top"] = float(dfr_PlateData.loc[i,str_Pars][0])
				dfr_Partial.loc[i,"R2"] = dfr_PlateData.loc[i,str_RSquare]
				# dfr_Partial.loc[i,"Data Quality"] = # data quality
				dfr_Partial.iloc[i,24] = "Free fit"# comments on curve classification and definitions
			else:
				dfr_Partial.iloc[i,13] = np.nan
				dfr_Partial.iloc[i,14] = np.nan
				dfr_Partial.iloc[i,15] = np.nan
				dfr_Partial.iloc[i,16] = np.nan
				dfr_Partial.iloc[i,17] = np.nan
				dfr_Partial.iloc[i,18] = np.nan
				# dfr_Partial.iloc[i,19] = # curve
				dfr_Partial.iloc[i,20] = np.nan
				dfr_Partial.iloc[i,21] = np.nan
				dfr_Partial.iloc[i,22] = np.nan
				# dfr_Partial.iloc[i,23] = # data quality
				dfr_Partial.iloc[i,24] = "not fitted" # comments on curve classification and definitions
			dfr_Partial.iloc[i,25] = dfr_References.loc["SolventMean",0] # enzyme reference
			dfr_Partial.iloc[i,26] = dfr_References.loc["SolventSEM",0] # enzyme reference error
			lstConcentrations = moles_to_micromoles(dfr_PlateData.loc[i,"Concentrations"])
			for j in range(len(lstConcentrations)):
				intColumnOffset = (j)*3
				dfr_Partial.iloc[i,27+intColumnOffset] = lstConcentrations[j]
				dfr_Partial.iloc[i,28+intColumnOffset] = dfr_PlateData.loc[i,"Norm"][j]
				dfr_Partial.iloc[i,29+intColumnOffset] = dfr_PlateData.loc[i,"NormSEM"][j]
			try: 
				dfr_Partial.iloc[i,79] = round(dfr_References.loc["ZPrimeMean",0],3) # ZPrime
			except:
				dfr_Partial.iloc[i,79] = ""
			try:
				dfr_Partial.iloc[i,80] = round(dfr_References.loc["ZPrimeMedian",0],3) # ZPrimeRobust
			except:
				dfr_Partial.iloc[i,80] = ""
			try:
				dfr_Partial.iloc[i,81] = round(dfr_References.loc["SolventMean",0]/dfr_References.loc["ControlMean",0],3) # Solvent/Control
			except:
				dfr_Partial.iloc[i,81] = ""
			try:
				dfr_Partial.iloc[i,82] = round(dfr_References.loc["BufferMean",0]/dfr_References.loc["ControlMean",0],3) # Buffer/Control
			except:
				dfr_Partial.iloc[i,82] = ""
			dfr_Partial.iloc[i,83] = dfr_Details.loc["Date","Value"] # Date of Experiment
			dfr_Partial.iloc[i,84] = dfr_Details.loc["ELN","Value"] # ELN Page
			dfr_Partial.iloc[i,85] = ""
	
	return dfr_Partial

def get_DoFit(lst_Data,lst_Error):
	'''
	Tests a set of normalised datapoints on whether to perform a sigmoidal fit.
	Criteria for fit:
	- More than five datapoints with standard error of mean < 20%
	- Maximum datapoint >= 60% \_ensure the IC50 is actually within the range)
	- Minimum datapoint <= 40% /
	'''
	count = 0
	for error in lst_Error:
		if error < 20:
			count += 1
			# As soon as we have enough datapoints, check whether the other conditions apply:
			if count > 5:
				if np.nanmax(lst_Data) >= 60 and np.nanmin(lst_Data) <= 40:
					return True
				else:
					return False

def recalculate_fit_sigmoidal(dfr_Input):

	lst_Dose = dfr_Input["Concentrations"] # -> DO not convert to uM, yet, the fitting algorithm will do this for you
	lst_Raw = dfr_Input["Raw"]
	lst_Norm = dfr_Input["Norm"]
	lst_NormSEM = dfr_Input["NormSEM"]

	lst_DoseTrim = []
	lst_RawTrim = []
	lst_NormTrim = []
	lst_NormSEMTrim = []
	for i in range(len(lst_Raw)):
		if np.isnan(lst_Raw[i]) == False:
			lst_DoseTrim.append(lst_Dose[i])
			lst_RawTrim.append(lst_Raw[i])
			lst_NormTrim.append(lst_Norm[i])
			lst_NormSEMTrim.append(lst_NormSEM[i])
	# 3. Re-fit
	lst_RawFitPars, lst_RawFitCI, lst_RawFitErrors = ff.fit_sigmoidal_free(lst_DoseTrim, lst_RawTrim, parsonly = True, skiptrim = True)
	lst_NormFitPars, lst_NormFitFreeCI, lst_NormFitFreeErrors = ff.fit_sigmoidal_free(lst_DoseTrim, lst_NormTrim, parsonly = True, skiptrim = True)
	lst_NormFitConstPars, lst_NormFitConstCI, lst_NormFitConstErrors = ff.fit_sigmoidal_const(lst_DoseTrim, lst_NormTrim, lst_NormSEMTrim, parsonly = True, skiptrim = True)
	for i in range(len(lst_RawFitPars)):
		dfr_Input["RawFitPars"][i] = lst_RawFitPars[i]
		dfr_Input["RawFitCI"][i] = lst_RawFitCI[i]
		dfr_Input["RawFitErrors"][i] = lst_RawFitErrors[i]

		dfr_Input["NormFitFreePars"][i] = lst_NormFitPars[i]
		dfr_Input["NormFitFreeCI"][i] = lst_NormFitFreeCI[i]
		dfr_Input["NormFitFreeErrors"][i] = lst_NormFitFreeErrors[i]

		dfr_Input["NormFitConstPars"][i] = lst_NormFitConstPars[i]
		dfr_Input["NormFitConstCI"][i] = lst_NormFitConstCI[i]
		dfr_Input["NormFitConstErrors"][i] = lst_NormFitConstErrors[i]

	# 1. Push changes back to dfr_Sample
	lst_RawFit = ff.draw_sigmoidal(lst_Dose,lst_RawFitPars)
	lst_NormFitFree = ff.draw_sigmoidal(lst_Dose,lst_NormFitPars)
	lst_NormFitConst = ff.draw_sigmoidal(lst_Dose,lst_NormFitConstPars)
	for i in range(len(lst_RawFit)):
		dfr_Input["RawFit"][i] = lst_RawFit[i]
		dfr_Input["NormFitFree"][i] = lst_NormFitFree[i]
		dfr_Input["NormFitConst"][i] = lst_NormFitConst[i]
	
	dfr_Input.at["RawFitR2"] = ff.calculate_rsquare(dfr_Input["Raw"],dfr_Input["RawFit"])
	dfr_Input.at["NormFitFreeR2"] = ff.calculate_rsquare(dfr_Input["Norm"],dfr_Input["NormFitFree"])
	dfr_Input.at["NormFitConstR2"] = ff.calculate_rsquare(dfr_Input["Norm"],dfr_Input["NormFitConst"])

	# 2. Push dfr_Sample back to CompleteContainer
	return dfr_Input

def write_IC50(flt_IC50,bol_DoFit,flt_Confidence):
	
	# Cannot do a direct type check as the curve fit returns numpy.float64.
	# When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
	if bol_DoFit == False or str(type(flt_IC50)).find("float") == -1: # actually calculated values seem to be numpy.float64?
		return "N.D."
	else:
		flt_IC50 = flt_IC50 / 1000000 # IC50 gets handed to this function in micromolar -> turn back to molar
		flt_PlusMinus = flt_Confidence  / 1000000 
		if (flt_IC50) * 1000 <= 500 and flt_IC50 * 1000000 > 500:
			return str(round(flt_IC50 * 1000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000, 1)) + " mM"
		elif flt_IC50 * 1000000 <= 500 and flt_IC50 * 1000000000 > 500:
			return str(round(flt_IC50 * 1000000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000000, 1)) + " " + chr(181) + "M"
		elif flt_IC50 * 1000000000 <= 500 and flt_IC50 * 1000000000000 > 500:
			return str(round(flt_IC50 * 1000000000, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus * 1000000000, 1)) + " nM"
		else:
			return str(flt_IC50) + " M"

##########################################
##                                      ##
##    ######  #####    #####  #####     ##
##    ##      ##  ##  ##      ##  ##    ##
##    ####    #####    ####   ##  ##    ##
##    ##      ##          ##  ##  ##    ##
##    ######  ##      #####   #####     ##
##                                      ##
##########################################

def create_dataframe_EPSD(dfr_RawData, dfr_Samples, dfr_References, str_AssayType, str_AssayVolume, dlg_Progress):
	"""
	This function is for endpoint protein-peptide interaction/displacement assays such as HTRF, AlphaScreen or endpoint assays of enzymatic
	reactions such as the "Glo" family of assays.
	Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
	and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
	to calculate values based on the assay type.
	"""
	# Get number of samples:
	int_Samples = len(dfr_Samples)
	# Create new dataframe
	lst_Columns = ["DestinationPlateName","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData",
		"Raw","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
		"Norm","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoFitFree",
		"NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoFitConst",
		"Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
	fltAssayVolume = float(str_AssayVolume)
	# Check each concentration if it occurs more than once, then write it into a new list and add the corresponding locations
	# to a list and add that list to a list. Once finished, overwrite columns Locations and Concentration with the new list.
	# dfr_Samples must have been sorted for Concentration for this to work properly.
	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)
	for smpl in range(int_Samples):
		# Pull list of concentrations for current sample
		lstConc = dfr_Samples.loc[smpl,"Concentrations"]
		lstLoc = dfr_Samples.loc[smpl,"Locations"]
		#lstRaw = dfr_Processed.loc[i, "RawData"]
		# Create list of lists:
		lstlstConc = [] # list of lists for concentrations
		lstlstLoc = [] # list of lists for locations
		lstlstRaw = [] # list of lists for raw data
		lstRawExcluded = [] # list of excluded values
		lstNormExcluded = []
		# Go through list of concentrations
		for conc in range(len(lstConc)):
			lstConcTemp = []
			lstRawTemp = []
			lstLocTemp = []
			# Check to only use unique concentrations
			if lstConc[conc] != "found":
				# assign current conc/loc to temporary lists
				lstConcTemp = lstConc[conc] # simple list
				lstLocTemp = [lstLoc[conc]] # list of lists, one concentration can be in many locations
				lstRawTemp = [dfr_RawData.iloc[lstLoc[conc],1]]
				for k in range(conc+1,len(lstConc)):
					if lstConc[conc] == lstConc[k]:
						lstConc[k] = "found" # flag concentrations that are not unique
						lstLocTemp.append(lstLoc[k])
						lstRawTemp.append(dfr_RawData.iloc[lstLoc[k],1])
				# append temporary list to list of lists
				lstlstConc.append(lstConcTemp)
				lstlstLoc.append(lstLocTemp)
				lstlstRaw.append(lstRawTemp)
				# Create excluded list, initialised with np.nan in the first instance
				lstRawExcluded.append(np.nan)
				lstNormExcluded.append(np.nan)
		# Assign list of lists to dataframe
		dfr_Processed.loc[smpl,"DestinationPlateName"] = dfr_Samples.loc[smpl,"DestinationPlateName"]
		dfr_Processed.loc[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
		dfr_Processed.loc[smpl,"SourceConcentration"] = dfr_Samples.loc[smpl,"SourceConcentration"]
		dfr_Processed.loc[smpl,"Concentrations"] = lstlstConc
		dfr_Processed.loc[smpl,"AssayVolume"] = fltAssayVolume
		dfr_Processed.loc[smpl,"Locations"] = lstlstLoc
		dfr_Processed.loc[smpl,"RawData"] = lstlstRaw
		dfr_Processed.loc[smpl,"Raw"], dfr_Processed.loc[smpl,"RawSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstRaw)
		dfr_Processed.loc[smpl,"RawExcluded"] = lstRawExcluded

		# Normalisation needs to happen before datafitting is attempted
		lstlstNorm = []
		for j in range(len(lstlstRaw)):
			lstlstNorm.append(Normalise(lstlstRaw[j], str_AssayType, dfr_References))
		dfr_Processed.loc[smpl,"Norm"], dfr_Processed.loc[smpl,"NormSEM"], fnord = Mean_SEM_STDEV_ListList(lstlstNorm)
		dfr_Processed.loc[smpl,"NormExcluded"] = lstNormExcluded

		dfr_Processed.loc[smpl,"Show"] = 1
		dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(smpl+1,int_Samples) + " " + str(smpl+1) + " out of " + str(int_Samples) + " samples.")
	# Return
	return dfr_Processed

def create_Database_frame_EPSD(dfr_Details,lstHeaders,dfr_PlateData,dfr_References):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_PlateReturn = pd.DataFrame(columns=lstHeaders)
	# Go through dfr_PlateData and write into dfPatial
	for smpl in range(len(dfr_PlateData)):
		if dfr_PlateData.loc[smpl,"SampleID"] != "Control":
			lstConcentrations = moles_to_micromoles(dfr_PlateData.loc[smpl,"Concentrations"])
			dfr_CompoundReturn = pd.DataFrame(columns=lstHeaders,index=range(len(lstConcentrations)))
			for conc in range(len(lstConcentrations)):
				dfr_CompoundReturn.iloc[conc,0] = dfr_Details.loc["AssayType","Value"] # Assay type
				dfr_CompoundReturn.iloc[conc,1] = dfr_Details.loc["PurificationID","Value"] # Purification ID
				dfr_CompoundReturn.iloc[conc,2] = float(dfr_Details.loc["ProteinConcentration","Value"])/1000 # protein concentration in uM. Form is in nM.
				dfr_CompoundReturn.iloc[conc,3] = dfr_Details.loc["PeptideID","Value"] # PeptideID
				dfr_CompoundReturn.iloc[conc,4] = dfr_PlateData.loc[smpl,"SampleID"] # Sample ID/Global Compound ID
				dfr_CompoundReturn.iloc[conc,5] = float(dfr_Details.loc["PeptideConcentration","Value"])/1000 # peptide concentration in uM. Form is in nM.
				dfr_CompoundReturn.iloc[conc,6] = dfr_Details.loc["Solvent","Value"] # solvent
				dfr_CompoundReturn.iloc[conc,7] = dfr_Details.loc["SolventConcentration","Value"] # solvent concentration in %
				dfr_CompoundReturn.iloc[conc,8] = dfr_Details.loc["Buffer","Value"] # Buffer
				# dfr_CompoundReturn.iloc[conc,9] = # compound incubation time
				# dfr_CompoundReturn.iloc[conc,10] = # peptide incubation time
				# dfr_CompoundReturn.iloc[conc,11] = # bead incubation time
				dfr_CompoundReturn.iloc[conc,12] = 22 # incubation temperature
				dfr_CompoundReturn.iloc[conc,25] = dfr_References.loc["SolventMean",0] # enzyme reference
				dfr_CompoundReturn.iloc[conc,26] = dfr_References.loc["SolventSEM",0] # enzyme reference error
				try: 
					dfr_CompoundReturn.iloc[conc,79] = round(dfr_References.loc["ZPrimeMean",0],3) # ZPrime
				except:
					dfr_CompoundReturn.iloc[conc,79] = ""
				try:
					dfr_CompoundReturn.iloc[conc,80] = round(dfr_References.loc["ZPrimeMedian",0],3) # ZPrimeRobust
				except:
					dfr_CompoundReturn.iloc[conc,80] = ""
				try:
					dfr_CompoundReturn.iloc[conc,81] = round(dfr_References.loc["SolventMean",0]/dfr_References.loc["ControlMean",0],3) # Solvent/Control
				except:
					dfr_CompoundReturn.iloc[conc,81] = ""
				try:
					dfr_CompoundReturn.iloc[conc,82] = round(dfr_References.loc["BufferMean",0]/dfr_References.loc["ControlMean",0],3) # Buffer/Control
				except:
					dfr_CompoundReturn.iloc[conc,82] = ""
				dfr_CompoundReturn.iloc[conc,83] = dfr_Details.loc["Date","Value"] # Date of Experiment
				dfr_CompoundReturn.iloc[conc,84] = dfr_Details.loc["ELN","Value"] # ELN Page
				dfr_CompoundReturn.iloc[conc,85] = ""
			dfr_PlateReturn = pd.concat([dfr_PlateReturn, dfr_CompoundReturn])
	
	return dfr_PlateReturn.reset_index()

def create_Database_frame_ActAssay(dfr_Details,lstHeaders,dfr_PlateData,lst_References,boolDoseResponse):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	if boolDoseResponse == True:
		str_AssayType = dfr_Details.loc["AssayType","Value"] + " IC50"
	else:
		str_AssayType = dfr_Details.loc["AssayType","Value"]
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):
		if dfr_PlateData.loc[i,"SampleID"] != "Control":
			dfr_Partial.iloc[i,0] = str_AssayType
			dfr_Partial.iloc[i, 1] = dfr_Details.loc["PurificationID","Value"] # Purification ID
			dfr_Partial.iloc[i, 2] = float(dfr_Details.loc["ProteinConcentration","Value"])/1000 # protein concentration in uM. Form is in nM.
			dfr_Partial.iloc[i, 3] = "Substrate 1"
			dfr_Partial.iloc[i, 4] = dfr_Details.loc["PeptideID","Value"] # PeptideID
			dfr_Partial.iloc[i, 5] = float(dfr_Details.loc["PeptideConcentration","Value"])/1000 # peptide concentration in uM. Form is in nM.
			dfr_Partial.iloc[i, 6] = "Substrate 2"
			dfr_Partial.iloc[i, 7] = "SGC Global Compound ID 2 (Batch)"
			dfr_Partial.iloc[i, 8] = "ActAssay Substrate 2 Concentration (uM)"
			dfr_Partial.iloc[i, 9] = dfr_Details.loc["Solvent","Value"] # solvent
			dfr_Partial.iloc[i, 10] = dfr_Details.loc["SolventConcentration","Value"] # solvent concentration in %
			dfr_Partial.iloc[i, 11] = dfr_Details.loc["Buffer","Value"] # Buffer
			dfr_Partial.iloc[i, 12] = "Assay Time (mins)"
			dfr_Partial.iloc[i, 13] = "Reagent 1 Time"
			dfr_Partial.iloc[i, 14] = "Reagent 2 Time"
			dfr_Partial.iloc[i, 15] = "ActAssay Incubation Temperature (C)"
			dfr_Partial.iloc[i, 16] = "Enzyme Reference"
			dfr_Partial.iloc[i, 17] = "Enzyme Reference Error (%)"
			dfr_Partial.iloc[i, 18] = "No Protein Control"
			dfr_Partial.iloc[i, 19] = "No Protein Control Error"
			dfr_Partial.iloc[i, 20] = "Solvent Control Inhibition 1 (%)"
			dfr_Partial.iloc[i, 21] = dfr_PlateData.loc[i,"SampleID"] # Sample ID/Global Compound ID
			if boolDoseResponse == True:
				if dfr_PlateData.loc[i,"DoFit"] == True:
					if dfr_PlateData.loc[i,"Show"] == 0:
						str_Pars = "RawFitPars"
						str_CI = "RawFitCI"
						str_Errors = "RawFitErrors"
						str_RSquare = "RawFitR2"
					elif dfr_PlateData.loc[i,"Show"] == 1:
						str_Pars = "NormFitFreePars"
						str_CI = "NormFitFreeCI"
						str_Errors = "NormFitFreeErrors"
						str_RSquare = "NormFitFreeR2"
					elif dfr_PlateData.loc[i,"Show"] == 2:
						str_Pars = "NormFitConstPars"
						str_CI = "NormFitConstCI"
						str_Errors = "NormFitConstErrors"
						str_RSquare = "NormFitConstR2"
				dfr_Partial.iloc[i, 22] = np.log10(float(dfr_PlateData.loc[i,str_Pars][3])/1000000)# log10 IC50. IC50 is stored in uM!
				dfr_Partial.iloc[i, 23] = "Standard Error Log IC50"
				dfr_Partial.iloc[i, 24] = float(dfr_PlateData.loc[i,str_Pars][3]) # IC50 in uM
				dfr_Partial.iloc[i, 25] = dfr_PlateData.loc[i,str_Pars][3] + dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.iloc[i, 26] = dfr_PlateData.loc[i,str_Pars][3] - dfr_PlateData.loc[i,str_CI][3]
				dfr_Partial.iloc[i, 27] = float(dfr_PlateData.loc[i,str_Pars][2]) # Hill slope
				dfr_Partial.iloc[i, 28] = float(dfr_PlateData.loc[i,str_Pars][1]) # bottom of curve fit
				dfr_Partial.iloc[i, 29] = float(dfr_PlateData.loc[i,str_Pars][0]) # top of curve fit
				dfr_Partial.iloc[i, 30] = dfr_PlateData.loc[i,str_RSquare]# R square value
				dfr_Partial.iloc[i, 31] = "Curve Comments"
				lst_Concentrations = moles_to_micromoles(dfr_PlateData.loc[i,"Concentrations"])
				for j in range(len(lst_Concentrations)):
					intColumnOffset = (j)*3
					dfr_Partial.iloc[i, 32 + intColumnOffset] = lst_Concentrations[j]
					dfr_Partial.iloc[i, 33 + intColumnOffset] = dfr_PlateData.loc[i,"Norm"][j]
					dfr_Partial.iloc[i, 34 + intColumnOffset] = dfr_PlateData.loc[i,"NormSEM"][j]
				dfr_Partial.iloc[i, 80]  = dfr_Details.loc["ELN","Value"] # ELN Page
				dfr_Partial.iloc[i, 81] = "no comment" #"ActAssay Comments"
				#dfr_Partial.iloc[i, 85] = "Date ActAssay Record Created"
				#dfr_Partial.iloc[i, 86] = "Creator of ActAssay Record"

	return dfr_Partial


##########################################
##                                      ##
##    #####   #####   ######   #####    ##
##    ##  ##  ##  ##    ##    ##        ##
##    ##  ##  #####     ##    ##        ##
##    ##  ##  ##  ##    ##    ##        ##
##    #####   ##  ##    ##     #####    ##
##                                      ##
##########################################

def create_dataframe_DRTC_MP(dfr_RawData, dfr_Samples, dfr_References, str_AssayVolume, dlg_Progress):
	"""
	This function is for endpoint protein-peptide interaction/displacement assays such as HTRF, AlphaScreen or endpoint assays of enzymatic
	reactions such as the "Glo" family of assays.
	Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
	and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
	to calculate values based on the assay type.
	"""
	# Get number of samples:
	int_Samples = dfr_Samples.shape[0]
	# Create new dataframe
	lst_Columns = ["DestinationPlateName","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData","Time",
		"RawMean","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
		"NormMean","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoNormFitFree",
		"NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoNormFitConst",
		"Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns)
	fltAssayVolume = float(str_AssayVolume)
	# Check each concentration if it occurs more than once, then write it into a new list and add the corresponding locations
	# to a list and add that list to a list. Once finished, overwrite columns Locations and Concentration with the new list.
	# dfr_Samples must have been sorted for Concentration for this to work properly.
	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)

	#baseline = 20 # 20s initial baseline for testing purposes

	lst_Input = []
	for smpl in range(int_Samples):
		lst_Item = []
		lst_Item.append(smpl)
		lst_Item.append(dfr_Samples)
		lst_Item.append(dfr_RawData)
		lst_Item.append(dfr_References)
		lst_Input.append(lst_Item)
	#cur = 0
	with Pool(5) as p:
		dfr_Processed = dfr_Processed.append(p.map(SampleProcessing_DRTC_MP, lst_Input))
		#dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(cur+1,int_Samples) + " " + str(cur+1) + " out of " + str(int_Samples) + " samples.")
	for smpl in range(int_Samples):
		dfr_Processed["AssayVolume"] = fltAssayVolume
		
	# Return
	return dfr_Processed

def SampleProcessing_DRTC_MP(lst_Input):

	smpl = lst_Input[0]
	dfr_Samples = lst_Input[1]
	dfr_RawData = lst_Input[2]
	dfr_References = lst_Input[3]

	lst_Columns = ["DestinationPlateName","SampleID","Locations","Concentrations","SourceConcentration","AssayVolume","RawData","Time",
		"RawMean","RawSEM","RawExcluded","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors","DoFitRaw",
		"NormMean","NormSEM","NormExcluded","NormFitFree","NormFitFreePars","NormFitFreeCI","NormFitFreeR2","NormFitFreeErrors","DoNormFitFree",
		"NormFitConst","NormFitConstPars","NormFitConstCI","NormFitConstR2","NormFitConstErrors","DoNormFitConst",
		"Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(dfr_Samples.shape[0]))

	# Pull list of concentrations for current sample
	lstConc = dfr_Samples.loc[smpl,"Concentrations"]
	lstLoc = dfr_Samples.loc[smpl,"Locations"]
	# Create list of lists:
	lstlstConc = [] # list of lists for concentrations
	lstlstLoc = [] # list of lists for locations
	# Go through list of concentrations
	for conc in range(len(lstConc)):
		lstConcTemp = []
		lstLocTemp = []
		# Check to only use unique concentrations
		if lstConc[conc] != "found":
			# assign current conc/loc to temporary lists
			lstConcTemp = lstConc[conc] # simple list
			lstLocTemp = [lstLoc[conc]] # list of lists, one concentration can be in many locations
			for k in range(conc+1,len(lstConc)):
				if lstConc[conc] == lstConc[k]:
					lstConc[k] = "found" # flag concentrations that are not unique
					lstLocTemp.append(lstLoc[k])
			# append temporary list to list of lists
			lstlstConc.append(lstConcTemp)
			lstlstLoc.append(lstLocTemp)
	# Assign list of lists to dataframe
	dfr_Processed.loc[smpl,"DestinationPlateName"] = dfr_Samples.loc[smpl,"DestinationPlateName"]
	dfr_Processed.loc[smpl,"SampleID"] = dfr_Samples.loc[smpl,"SampleID"]
	dfr_Processed.loc[smpl,"SourceConcentration"] = dfr_Samples.loc[smpl,"SourceConcentration"]
	dfr_Processed.at[smpl,"Concentrations"] = lstlstConc
	dfr_Processed.at[smpl,"Locations"] = lstlstLoc
	dfr_Processed.at[smpl,"Time"] = dfr_RawData.columns.values.tolist()
	lst_CycleColumns = ["RawData", "RawMean","RawSEM","RawExcluded","RawFit","NormMean","NormSEM","NormExcluded","NormFitFree","NormFitConst","NormFitConstPars"]
	for column in lst_CycleColumns:
		dfr_Processed.at[smpl,column] = pd.DataFrame(index=dfr_Processed.loc[smpl,"Concentrations"],columns=dfr_RawData.columns.values.tolist())
	lst_ParameterColumns = ["RawFitPars","RawFitCI","RawFitErrors","NormFitFreePars","NormFitFreeCI","NormFitFreeErrors","NormFitConstPars","NormFitConstCI","NormFitConstErrors"]
	for column in lst_ParameterColumns:
		dfr_Processed.at[smpl,column] = pd.DataFrame(index=["Top","Bottom","Slope","Inflection"],columns=dfr_RawData.columns.values.tolist())
	lst_OutstandingColumns = ["DoFitRaw","RawFitR2","DoNormFitFree","NormFitFreeR2","NormFitConstR2","DoNormFitConst","DoFit","Show"]
	for column in lst_OutstandingColumns:
		dfr_Processed.at[smpl,column] = pd.DataFrame(index=["Value"],columns=dfr_RawData.columns.values.tolist())
	#dfr_Processed.at[smpl,"Baseline"] = pd.DataFrame(index=dfr_Processed.loc[smpl,"Concentrations"],columns=["Baseline"])

	# Arrange and average raw data so that we can subtract baseline
	for cycle in range(len(dfr_Processed.loc[smpl,"Time"])):
		# Normalisation
		timestamp = dfr_Processed.loc[smpl,"Time"][cycle]
		for conc in range(len(lstlstConc)):
			dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle] = []
			for rep in range(len(dfr_Processed.loc[smpl,"Locations"][conc])):
				dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle].append(dfr_RawData.iloc[dfr_Processed.loc[smpl,"Locations"][conc][rep],cycle])
				dfr_Processed.loc[smpl,"RawMean"].iloc[conc,cycle] = np.mean(dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle])
			dfr_Processed.loc[smpl,"RawSEM"].iloc[conc,cycle] = np.std(dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle], ddof = 1) / np.sqrt(np.size(dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle]))
			if pd.isna(dfr_References.loc["SolventMean",timestamp]) == False:
				str_Reference = "SolventMean"
			else:
				str_Reference = "BufferMean"
			dfr_Processed.loc[smpl,"NormMean"].iloc[conc,cycle], dfr_Processed.loc[smpl,"NormSEM"].iloc[conc,cycle] = Normalise_DRTC(dfr_Processed.loc[smpl,"RawData"].iloc[conc,cycle],
				dfr_References.loc[str_Reference,timestamp], dfr_References.loc["ControlMean",timestamp])
		# Curve fitting
		#sigmoidal_fit, lst_Parameters, lst_Confidence, lst_STDERR, RSquare, success = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"Concentrations",dfr_Processed.loc[smpl,"RawMean"][cycle])
		# Free fit, free
		lst_FitResults = []
		#lst_FitResults = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"RawMean"].index.values.tolist(),dfr_Processed.loc[smpl,"RawMean"].loc[:,timestamp].tolist())
		#dfr_Processed.loc[smpl,"RawFit"].loc[:,timestamp] = lst_FitResults[0]
		#dfr_Processed.loc[smpl,"RawFitPars"].loc[:,timestamp] = lst_FitResults[1]
		#dfr_Processed.loc[smpl,"RawFitCI"].loc[:,timestamp] = lst_FitResults[2]
		#dfr_Processed.loc[smpl,"RawFitErrors"].loc[:,timestamp] = lst_FitResults[3]
		#dfr_Processed.loc[smpl,"RawFitR2"].at["Value",timestamp] = lst_FitResults[4]
		#dfr_Processed.loc[smpl,"DoFitRaw"].at["Value",timestamp] = lst_FitResults[5]
		# Normalised fit, free
		lst_FitResults = []
		lst_FitResults = ff.fit_sigmoidal_free(dfr_Processed.loc[smpl,"NormMean"].index.values.tolist(),dfr_Processed.loc[smpl,"NormMean"].loc[:,timestamp].tolist())
		dfr_Processed.loc[smpl,"NormFitFree"].loc[:,timestamp] = lst_FitResults[0]
		dfr_Processed.loc[smpl,"NormFitFreePars"].loc[:,timestamp] = lst_FitResults[1]
		dfr_Processed.loc[smpl,"NormFitFreeCI"].loc[:,timestamp] = lst_FitResults[2]
		dfr_Processed.loc[smpl,"NormFitFreeErrors"].loc[:,timestamp] = lst_FitResults[3]
		dfr_Processed.loc[smpl,"NormFitFreeR2"].at["Value",timestamp] = lst_FitResults[4]
		dfr_Processed.loc[smpl,"DoNormFitFree"].at["Value",timestamp] = lst_FitResults[5]
		# Normalised fit, constrained
		lst_FitResults = []
		lst_FitResults = ff.fit_sigmoidal_const(dfr_Processed.loc[smpl,"NormMean"].index.values.tolist(),dfr_Processed.loc[smpl,"NormMean"].loc[:,timestamp].tolist(),
			dfr_Processed.loc[smpl,"NormSEM"].loc[:,timestamp].tolist())
		dfr_Processed.loc[smpl,"NormFitConst"].loc[:,timestamp] = lst_FitResults[0]
		dfr_Processed.loc[smpl,"NormFitConstPars"].loc[:,timestamp] = lst_FitResults[1]
		dfr_Processed.loc[smpl,"NormFitConstCI"].loc[:,timestamp] = lst_FitResults[2]
		dfr_Processed.loc[smpl,"NormFitConstErrors"].loc[:,timestamp] = lst_FitResults[3]
		dfr_Processed.loc[smpl,"NormFitConstR2"].at["Value",timestamp] = lst_FitResults[4]
		dfr_Processed.loc[smpl,"DoNormFitConst"].at["Value",timestamp] = lst_FitResults[5]
		lst_FitResults = []

		dfr_Processed.loc[smpl,"Show"].at["Value",timestamp] = 1

	# Return
	return dfr_Processed.loc[smpl]

def Normalise_DRTC(lst_RawData, reference, control):

	lst_Norm = []
	for rawdata in lst_RawData:
		lst_Norm.append((1-((rawdata - control)/(reference - control)))*100)
	Mean = np.mean(lst_Norm)
	SEM = np.std(lst_Norm, ddof = 1) / np.sqrt(np.size(lst_Norm))

	return Mean, SEM

def recalculate_DRTC_MP(dfr_Input, flt_Cycle):
	dfr_Input["DoFit"].at["Value",flt_Cycle] = get_DoFit(dfr_Input["NormMean"].loc[:,flt_Cycle].tolist(),dfr_Input["NormSEM"].loc[:,flt_Cycle].tolist())
			
	if dfr_Input["DoFit"].at["Value",flt_Cycle] == True:
		# 3. Re-fit
		lst_FitResults = ff.fit_sigmoidal_free(dfr_Input["Concentrations"], dfr_Input["NormMean"].loc[:,flt_Cycle].tolist())  # only function for constrained needs SEM
		dfr_Input.at["NormFitFree"].loc[:,flt_Cycle] = lst_FitResults[0]
		dfr_Input.at["NormFitFreePars"].loc[:,flt_Cycle] = lst_FitResults[1]
		dfr_Input.at["NormFitFreeCI"].loc[:,flt_Cycle] = lst_FitResults[2]
		dfr_Input.at["NormFitFreeErrors"].loc[:,flt_Cycle] = lst_FitResults[3]
		dfr_Input.loc["NormFitFreeR2"].at["Value",flt_Cycle] = lst_FitResults[4]
		dfr_Input.loc["DoNormFitFree"].at["Value",flt_Cycle] = lst_FitResults[5]
		lst_FitResults = ff.fit_sigmoidal_const(dfr_Input["Concentrations"], dfr_Input["NormMean"].loc[:,flt_Cycle].tolist(), dfr_Input["NormSEM"].loc[:,flt_Cycle].tolist())  # only function for constrained needs SEM
		dfr_Input.at["NormFitConst"].loc[:,flt_Cycle] = lst_FitResults[0]
		dfr_Input.at["NormFitConstPars"].loc[:,flt_Cycle] = lst_FitResults[1]
		dfr_Input.at["NormFitConstCI"].loc[:,flt_Cycle] = lst_FitResults[2]
		dfr_Input.at["NormFitConstErrors"].loc[:,flt_Cycle] = lst_FitResults[3]
		dfr_Input.loc["NormFitConstR2"].at["Value",flt_Cycle] = lst_FitResults[4]
		dfr_Input.loc["DoNormFitConst"].at["Value",flt_Cycle] = lst_FitResults[5]

	else:
		dfr_Input.at["RawFit"].loc[:,flt_Cycle] = set_to_nan(len(dfr_Input["RawFit"].loc[:,flt_Cycle]))
		dfr_Input.at["RawFitPars"].loc[:,flt_Cycle] = set_to_nan(4)
		dfr_Input.at["RawFitR2"].loc[:,flt_Cycle] = np.nan
			
		dfr_Input.at["NormFitFree"].loc[:,flt_Cycle] = set_to_nan(len(dfr_Input["NormFitFree"].loc[:,flt_Cycle]))
		dfr_Input.at["NormFitFreePars"].loc[:,flt_Cycle] = set_to_nan(4)
		dfr_Input.at["NormFitFreeR2"].loc[:,flt_Cycle] = np.nan

		dfr_Input.at["NormFitConst"].loc[:,flt_Cycle] = set_to_nan(len(dfr_Input["NormFitConst"].loc[:,flt_Cycle]))
		dfr_Input.at["NormFitConstPars"].loc[:,flt_Cycle] = set_to_nan(4)
		dfr_Input.at["NormFitConstR2"].loc[:,flt_Cycle] = np.nan

		dfr_Input.at["NormFitFreeCI"].loc[:,flt_Cycle], dfr_Input.at["NormFitConstCI"].loc[:,flt_Cycle], dfr_Input["RawFitCI"].loc[:,flt_Cycle] = set_to_nan(4), set_to_nan(4), set_to_nan(4)
		dfr_Input.at["NormFitFreeErrors"].loc[:,flt_Cycle], dfr_Input.at["NormFitConstErrors"].loc[:,flt_Cycle], dfr_Input["RawFitErrors"].loc[:,flt_Cycle] = set_to_nan(4), set_to_nan(4), set_to_nan(4)
	return dfr_Input

##################################
##                              ##
##    #####    #####  ######    ##
##    ##  ##  ##      ##        ##
##    ##  ##   ####   ####      ##
##    ##  ##      ##  ##        ##
##    #####   #####   ##        ##
##                              ##
##################################

def create_dataframe_DSF(dfr_RawData, dfr_Samples, dfr_Layout, dlg_Progress):
	"""
	Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
	and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
	to calculate values based on the assay type.
	"""

	int_PlateFormat = len(dfr_RawData)

	# This function is called per plate, so there will only be one plate name
	str_PlateName = dfr_Samples.loc[0,"DestinationPlateName"]

	lst_SampleIDs = []
	lst_SampleIDs = set_to_nan(384)
	int_Samples = 0
	for i in range(len(dfr_Samples)):
		for j in range(len(dfr_Samples.loc[i,"Locations"])):
			lst_SampleIDs[dfr_Samples.loc[i,"Locations"][j]] = dfr_Samples.loc[i,"SampleID"]
			if pd.isna(lst_SampleIDs[dfr_Samples.loc[i,"Locations"][j]]) == False:
				int_Samples += 1
	# Create new dataframe
	lst_Columns = ["DestinationPlateName","SampleID","Protein","Concentration","Well","Temp","Fluo","Initial",
		"RawDeriv","RawInflections","RawSlopes","Norm","NormDeriv","NormInflections","NormSlopes","NormDTm","Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
	#flt_AssayVolume = float(str_AssayVolume)
	k = -1
	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)
	for i in range(len(lst_SampleIDs)):

		if type(lst_SampleIDs[i]) == str:
			k += 1 #k is set to -1 above, so this will set k = 0 in the first instance.
			# Assign list of lists to dataframe
			dfr_Processed.loc[k,"DestinationPlateName"] = str_PlateName
			dfr_Processed.loc[k,"SampleID"] = lst_SampleIDs[i]
			dfr_Processed.loc[k,"Well"] = dfr_RawData.loc[k,"Well"]
			dfr_Processed.at[k,"Temp"] = dfr_RawData.loc[k,"Temp"]
			dfr_Processed.at[k,"Fluo"] = dfr_RawData.loc[k,"Fluo"]
			dfr_Processed.at[k,"Protein"] = dfr_Layout["PurificationID"][k]
			dfr_Processed.at[k,"Concentration"] = dfr_Layout["Concentration"][k]

			# Normalisation needs to happen before datafitting is attempted
			flt_FluoMin = np.nanmin(dfr_Processed.loc[k,"Fluo"])
			flt_FluoMax = np.nanmax(dfr_Processed.loc[k,"Fluo"]) - flt_FluoMin
			lst_Norm = []
			for j in range(len(dfr_Processed.loc[k,"Fluo"])):
				lst_Norm.append((dfr_Processed.loc[k,"Fluo"][j]-flt_FluoMin)/flt_FluoMax)
			dfr_Processed.at[k,"Norm"] = lst_Norm
			# Get initial fluorescence (average of normalised over first 10 degrees)
			flt_Initial = 0
			for j in range(10):
				flt_Initial = flt_Initial + dfr_Processed.loc[k,"Norm"][j]
			flt_Initial = flt_Initial / 10
			if flt_Initial < 0.3:
				dfr_Processed.loc[k,"Initial"] = 0
			if flt_Initial >= 0.3 and flt_Initial < 0.5:
				dfr_Processed.loc[k,"Initial"] = 1
			elif flt_Initial > 0.5:
				dfr_Processed.loc[k,"Initial"] = 2
			
			# Fitting criteria
			# Criteria for fit:
			dfr_Processed.loc[k,"DoFit"] = True

			# Find boundaries for fit!
			# 1. Find maximum and local minimum before maximum (Tm can only lie between those two!)
			#flt_RawMax = np.max(dfr_Processed.loc[k,"Fluo"])
			#flt_TmUpper = dfr_Processed.loc[k,"Temp"][len(dfr_Processed.loc[k,"Fluo"]) -1]
			#for i in range(len(dfr_Processed.loc[k,"Fluo"])):
			#	if dfr_Processed.loc[k,"Fluo"][i] == flt_RawMax:
			#		flt_TmUpper = dfr_Processed.loc[k,"Temp"][i] + 273.15
			#		break
			#lst_BeforeMax = []
			#for i in range(len(dfr_Processed.loc[k,"Fluo"])):
			#	if dfr_Processed.loc[k,"Fluo"][i] < flt_RawMax:
			#		lst_BeforeMax.append(dfr_Processed.loc[k,"Fluo"][i])
			#	else:
			#		break
			#flt_RawMin = np.min(lst_BeforeMax)
			#for i in range(len(lst_BeforeMax)):
			#	if dfr_Processed.loc[k,"Fluo"][i] == flt_RawMin:
			#		flt_TmLower = dfr_Processed.loc[k,"Temp"][i] + 273.15
			#		break

			# Perform fit -> Check if fitting criteria are met in the first instance
			if dfr_Processed.loc[k,"DoFit"] == True:
				# Do The Fits
				dfr_Processed.at[k,"RawDeriv"], dfr_Processed.at[k,"RawInflections"], dfr_Processed.at[k,"RawSlopes"] = ff.derivative(dfr_Processed.loc[k,"Temp"],dfr_Processed.loc[k,"Fluo"],0,1,"max")
				dfr_Processed.at[k,"NormDeriv"], dfr_Processed.at[k,"NormInflections"], dfr_Processed.at[k,"NormSlopes"] = ff.derivative(dfr_Processed.loc[k,"Temp"],dfr_Processed.loc[k,"Norm"],0,1,"max")

			dfr_Processed.loc[k,"Show"] = 0
			dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Samples) + " " + str(k+1) + " out of " + str(int_Samples) + " samples.")
	# Calculate DTms:
	# Make dataframe to calculate average Tm of references
	lst_Proteins = list(set(dfr_Layout.loc["PurificationID"]))
	dfr_References = pd.DataFrame(columns=["TmSum","n","AverageTm"], index=(range(len(lst_Proteins))))
	# Need to initialise these with 0 to make the += work later.
	for i in range(len(lst_Proteins)):
		dfr_References.at[i,"TmSum"] = 0
		dfr_References.at[i,"n"] = 0
		dfr_References.at[i,"AverageTm"] = 0
	# Sum up Tms of references
	for i in range(len(dfr_Processed)):
		idx_Well = pf.well_to_index(dfr_Processed.loc[i,"Well"], int_PlateFormat)
		if dfr_Layout["WellType"][idx_Well] == "r":
			dfr_References.at[int(dfr_Layout["ProteinNumerical"][idx_Well])-1,"TmSum"] += dfr_Processed.loc[idx_Well,"NormInflections"][0]
			dfr_References.at[int(dfr_Layout["ProteinNumerical"][idx_Well])-1,"n"] += 1
	# Average Tms of references
	for i in range(len(dfr_References)):
		if dfr_References.loc[i,"n"] > 0:
			dfr_References.at[i,"AverageTm"] = round(dfr_References.loc[i,"TmSum"]/dfr_References.loc[i,"n"],2)
			# get DTms of samples
			for j in range(len(dfr_Processed)):
				idx_Well = pf.well_to_index(dfr_Processed.loc[j,"Well"], int_PlateFormat)
				dfr_Processed.at[j,"NormDTm"] = round(dfr_Processed.loc[j,"NormInflections"][0] - dfr_References.loc[int(dfr_Layout["ProteinNumerical"][idx_Well])-1,"AverageTm"],2)
		else:
			dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, "No reference wells have been defined for protein " + lst_Proteins[i] + ". Only melting temperatures, not Tm shifts, were calculated.")

	return dfr_Processed, dfr_References

def create_Database_frame_DSF(dfr_Details,lstHeaders,dfr_PlateData, dfr_Layout):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):

		dfr_Partial.iloc[i,0] = float(dfr_PlateData.loc[i,"Concentration"]) #float(dfr_Details.loc["ProteinConcentration","Value"]) # protein concentration in uM.
		dfr_Partial.iloc[i,1] = dfr_PlateData.loc[i,"Protein"] # dfr_Details.loc["PurificationID","Value"] # Purification ID
		if dfr_Layout.loc["PlateID"] == "NA":
			dfr_Partial.iloc[i,2] = dfr_PlateData.loc[i,"SampleID"] # PlateWellID
		else:
			dfr_Partial.iloc[i,2] = dfr_Layout.loc["PlateID"] + dfr_PlateData.loc[i,"Well"] # Sample ID/Global Compound ID # THIS WILL NEED TO BE CHANGED LATER
		dfr_Partial.iloc[i,3] = 100 # moles_to_micromoles(dfr_PlateData.loc[i,"Concentrations"])[0] # "1st compound concentration [" & Chr(181) & "M]"
		dfr_Partial.iloc[i,4] = "Buffer ID"
		dfr_Partial.iloc[i,5] = "2nd compound ID"
		dfr_Partial.iloc[i,6] = "2nd compound concentration" # [" & Chr(181) & "M]"
		dfr_Partial.iloc[i,7] = round(dfr_PlateData.loc[i,"RawInflections"][0],1) # Tm value, convert from K to C
		dfr_Partial.iloc[i,8] = dfr_PlateData.loc[i,"NormDTm"] # "Tm Shift" # [" & Chr(176) & "C]"
		dfr_Partial.iloc[i,9] = round(dfr_PlateData.loc[i,"RawSlopes"][0],1) #"slope at Tm" # [DI/" & Chr(176) & "C]"
		dfr_Partial.iloc[i,10] = dfr_Details.loc["ELN","Value"] # ELN Page
		dfr_Partial.iloc[i,11] = "No Comment"
	
	return dfr_Partial

def create_Database_frame_DSF_Platemap(dfr_Details, lstHeaders, dfr_PlateData, dfr_Layout):
		# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_PlateMap = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):

		dfr_PlateMap.iloc[i,0] = dfr_Layout.loc["PlateID"] #"PlateID"
		if dfr_Details.loc["AssayType","Value"] == "nanoDSF":
			dfr_PlateMap.iloc[i,1] = dfr_Layout.loc["PlateID"] + pf.index_to_well(dfr_PlateData.loc[i,"CapIndex"]+1,96) #"PlateWell ID"
		else:
			dfr_PlateMap.iloc[i,1] = dfr_Layout.loc["PlateID"] + dfr_PlateData.loc[i,"Well"] #"PlateWell ID"
		dfr_PlateMap.iloc[i,2] = "Plate Parent"
		dfr_PlateMap.iloc[i,3] = dfr_PlateData.loc[i,"SampleID"] # "SGC Global Compound ID"
		dfr_PlateMap.iloc[i,4] = "Well concentration(mM)"
		dfr_PlateMap.iloc[i,5] = "Neccesary additive"
		dfr_PlateMap.iloc[i,6] = "Plate well: plate active"
		dfr_PlateMap.iloc[i,7] = "Plate well purpose"
		dfr_PlateMap.iloc[i,8] = "Plate well comments"
	
	return dfr_PlateMap

def recalculate_fit_DSF(dfr_Input):

	lst_Norm = dfr_Input["Norm"]

	# 3. Re-fit
	lst_RawFitPars, fnord, fnord, success = ff.thermal_shift(dfr_Input["Temp"], dfr_Input["Fluo"], dfr_Input["RawFitConstraints"], dfr_Input["RawFitGuess"], True)
	lst_NormFitPars, fnord, fnord, success = ff.thermal_shift(dfr_Input["Temp"], dfr_Input["Norm"], dfr_Input["NormFitConstraints"], dfr_Input["NormFitGuess"], True)
	for i in range(len(lst_RawFitPars)):
		dfr_Input["RawFitPars"][i] = lst_RawFitPars[i]
		dfr_Input["NormFitPars"][i] = lst_NormFitPars[i]

	# 1. Push changes back to dfr_Sample
	lst_RawFit = ff.draw_thermal(dfr_Input["Temp"],dfr_Input["RawFitPars"])
	lst_NormFitFree = ff.draw_thermal(dfr_Input["Temp"],dfr_Input["NormFitPars"])
	for i in range(len(lst_RawFit)):
		dfr_Input["RawFit"][i] = lst_RawFit[i]
		dfr_Input["NormFit"][i] = lst_NormFitFree[i]
	dfr_Input["RawFitR2"] = ff.calculate_rsquare(dfr_Input["Fluo"],dfr_Input["RawFit"])

	# 2. Push dfr_Sample back to CompleteContainer
	return dfr_Input

def write_Tm(flt_Tm, bol_DoFit, flt_PlusMinus):
	# Cannot do a direct type check as the curve fit returns numpy.float64.
	# When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
	if bol_DoFit == False or str(type(flt_Tm)).find("float") == -1: # actually calculated values seem to be numpy.float64?
		return "N.D."
	else:
		# Convert Tm from K to C
		return str(round(flt_Tm-273.15, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus, 1)) + " " + chr(176) + "C"

def write_Enthalpy(flt_H, bol_DoFit, flt_PlusMinus):
	# Cannot do a direct type check as the curve fit returns numpy.float64.
	# When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
	if bol_DoFit == False or str(type(flt_H)).find("float") == -1: # actually calculated values seem to be numpy.float64?
		return "N.D."
	else:
		# Convert from J to kJ
		return str(round(flt_H/1000, 2)) + " " + chr(177) + " " + str(round(flt_PlusMinus/1000, 2)) + " kJ/mol"

##########################################################################
##                                                                      ##
##    ##  ##   ####   ##  ##   ####           #####    #####  ######    ##
##    ### ##  ##  ##  ### ##  ##  ##          ##  ##  ##      ##        ##
##    ######  ######  ######  ##  ##  ######  ##  ##   ####   ####      ##
##    ## ###  ##  ##  ## ###  ##  ##          ##  ##      ##  ##        ##
##    ##  ##  ##  ##  ##  ##   ####           #####   #####   ##        ##
##                                                                      ##
##########################################################################

def get_CompleteContainer_nanoDSF(str_DataPath,str_AssayCategory,bol_PlateID,dfr_Capillaries,dfr_Layout,dlg_Progress):
	dlg_Progress.lbx_Log.InsertItems(["Assay category: " + str_AssayCategory], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)

	dfr_Container = pd.DataFrame(columns=["DestinationPlateName","Samples","Capillaries","DataFileName",
		"RawDataFrame","ProcessedDataFrame","Layout","References"], index=range(1))

	for idx_Set in range(len(dfr_Container)):
		dlg_Progress.lbx_Log.InsertItems(["Processing capillary set " + str(idx_Set + 1)], dlg_Progress.lbx_Log.Count)
		dfr_Container.loc[idx_Set,"DestinationPlateName"] = "CapillarySet_" + str(idx_Set+1)
		dfr_Container.loc[idx_Set,"DataFileName"] = str_DataPath
		dfr_Container.at[idx_Set,"RawDataFrame"] = ro.get_prometheus_readout(str_DataPath)
		if dfr_Container.loc[idx_Set,"RawDataFrame"] is None: # == False:
			msg.FileNotData(None)
			return None
		dfr_Container.at[idx_Set,"Samples"] = pd.DataFrame({"CapillaryIndex":dfr_Container.loc[idx_Set,"RawDataFrame"]["CapIndex"].to_list(),
			"CapillaryName":dfr_Container.loc[idx_Set,"RawDataFrame"]["CapillaryName"].to_list()})
		dfr_Container.at[idx_Set,"Layout"] = dfr_Layout
		dfr_Container.at[idx_Set,"ProcessedDataFrame"], dfr_Container.at[idx_Set,"References"] = create_dataframe_nanoDSF(dfr_Container.loc[idx_Set,"RawDataFrame"],dfr_Capillaries,dfr_Layout.loc[idx_Set],dlg_Progress)

	return dfr_Container

def create_dataframe_nanoDSF(dfr_RawData, dfr_Capillaries, dfr_Layout, dlg_Progress):
	# dfr_RawData is dfr_Prometheus
	int_Samples = 0
	for cap in range(len(dfr_RawData)):
		if dfr_RawData.loc[cap,"CapillaryName"] != "no capillary":
			int_Samples += 1
	lst_Columns = ["CapillarySet","CapillaryName","SampleID","SampleConc","PurificationID","ProteinConc","Buffer","CapIndex","Temp",
		"Ratio","RatioDeriv","RatioInflections","RatioSlopes",
		"330nm","330nmDeriv","330nmInflections","330nmSlopes",
		"350nm","350nmDeriv","350nmInflections","350nmSlopes",
		"Scattering","ScatteringDeriv","ScatteringInflections","ScatteringSlopes",
		"NormDTm","Show","DoFit"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))

	dfr_Processed["CapillaryName"] = dfr_RawData["CapillaryName"]
	dfr_Processed["SampleID"] = dfr_Capillaries["SampleID"].apply(string_or_na)
	dfr_Processed["SampleConc"] = dfr_Capillaries["SampleConc"].apply(string_or_na)
	dfr_Processed["PurificationID"] = dfr_Capillaries["PurificationID"].apply(string_or_na)
	dfr_Processed["ProteinConc"] = dfr_Capillaries["ProteinConc"].apply(string_or_na)
	dfr_Processed["Buffer"] = dfr_Capillaries["Buffer"].apply(string_or_na)
	dfr_Processed["CapIndex"] = dfr_RawData["CapIndex"]
	dfr_Processed["Temp"] = dfr_RawData["Temp"]
	dfr_Processed["Ratio"] = dfr_RawData["Ratio"]
	dfr_Processed["330nm"] = dfr_RawData["330nm"]
	dfr_Processed["350nm"] = dfr_RawData["350nm"]
	dfr_Processed["Scattering"] = dfr_RawData["Scattering"]

	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)

	k = -1
	for cap in range(int_Samples):
		if dfr_RawData.loc[cap,"CapillaryName"] != "no capillary":
			k += 1
			dfr_Processed.at[cap,"RatioDeriv"],dfr_Processed.at[cap,"RatioInflections"],dfr_Processed.at[cap,"RatioSlopes"] = ff.derivative(dfr_RawData.loc[cap,"Temp"], dfr_RawData.loc[cap,"Ratio"],2,2,"both")
			dfr_Processed.at[cap,"330nmDeriv"],dfr_Processed.at[cap,"330nmInflections"],dfr_Processed.at[cap,"330nmSlopes"] = ff.derivative(dfr_RawData.loc[cap,"Temp"], dfr_RawData.loc[cap,"330nm"],2,2,"both")
			dfr_Processed.at[cap,"350nmDeriv"],dfr_Processed.at[cap,"350nmInflections"],dfr_Processed.at[cap,"350nmSlopes"] = ff.derivative(dfr_RawData.loc[cap,"Temp"], dfr_RawData.loc[cap,"350nm"],2,2,"both")
			dfr_Processed.at[cap,"ScatteringDeriv"],dfr_Processed.at[cap,"ScatteringInflections"],dfr_Processed.at[cap,"ScatteringSlopes"] = ff.derivative(dfr_RawData.loc[cap,"Temp"], dfr_RawData.loc[cap,"Scattering"],2,2,"both")
			dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Samples) + " " + str(k+1) + " out of " + str(int_Samples) + " samples.")

	# Calculate DTms:
	# Make dataframe to calculate average Tm of references
	lst_Proteins = list(set(dfr_Layout.loc["PurificationID"]))
	dfr_References = pd.DataFrame(columns=["TmSum","n","AverageTm"], index=(range(len(lst_Proteins))))
	# Since the protein assignment works differently here (at least at the moment), we will have to iterate through to assign the numerical:
	for idx_Capillary in range(len(dfr_Processed)):
		for prot in range(len(lst_Proteins)):
			if dfr_Layout.loc["PurificationID"][idx_Capillary] == lst_Proteins[prot]:
				dfr_Layout.loc["ProteinNumerical"][idx_Capillary] = prot+1
	# Need to initialise these with 0 to make the += work later.
	for i in range(len(lst_Proteins)):
		dfr_References.at[i,"TmSum"] = 0
		dfr_References.at[i,"n"] = 0
		dfr_References.at[i,"AverageTm"] = 0
	# Sum up Tms of references
	for idx_Capillary in range(len(dfr_Processed)):
		if dfr_Layout["WellType"][idx_Capillary] == "r":
			dfr_References.at[int(dfr_Layout["ProteinNumerical"][idx_Capillary])-1,"TmSum"] += dfr_Processed.loc[idx_Capillary,"RatioInflections"][0]
			dfr_References.at[int(dfr_Layout["ProteinNumerical"][idx_Capillary])-1,"n"] += 1
	# Average Tms of references
	for i in range(len(dfr_References)):
		if dfr_References.loc[i,"n"] > 0:
			dfr_References.at[i,"AverageTm"] = round(dfr_References.loc[i,"TmSum"]/dfr_References.loc[i,"n"],2)
			# get DTms of samples
			for idx_Capillary in range(len(dfr_Processed)):
				dfr_Processed.at[idx_Capillary,"NormDTm"] = round(dfr_Processed.loc[idx_Capillary,"RatioInflections"][0] - dfr_References.loc[int(dfr_Layout["ProteinNumerical"][idx_Capillary])-1,"AverageTm"],2)
		else:
			dlg_Progress.lbx_Log.InsertItems(["No reference capillaries have been defined for protein " + lst_Proteins[i] + ". Only melting temperatures, not Tm shifts, were calculated."],
				dlg_Progress.lbx_Log.Count)

	return dfr_Processed, dfr_References

def create_Database_frame_NanoDSF(dfr_Details,lstHeaders,dfr_PlateData,dfr_Layout):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):

		if dfr_PlateData.loc[i,"ProteinConc"] != "" and not type(dfr_PlateData.loc[i,"ProteinConc"]) == str:
			dfr_Partial.iloc[i,0] = float(dfr_PlateData.loc[i,"ProteinConc"]) # protein concentration in uM.
		else:
			dfr_Partial.iloc[i,0] = np.nan
		dfr_Partial.iloc[i,1] = dfr_PlateData.loc[i,"PurificationID"] # dfr_Details.loc["PurificationID","Value"] # Purification ID
		if dfr_Layout.loc["PlateID"] == "X999A":
			dfr_Partial.iloc[i,2] = dfr_PlateData.loc[i,"SampleID"] # PlateWellID
		else:
			dfr_Partial.iloc[i,2] = dfr_Layout.loc["PlateID"] + pf.index_to_well(dfr_PlateData.loc[i,"CapIndex"]+1,96) # PlateWellID
		if dfr_PlateData.loc[i,"SampleConc"] != "" and not type(dfr_PlateData.loc[i,"SampleConc"]) == str:
			dfr_Partial.iloc[i,3] = float(dfr_PlateData.loc[i,"SampleConc"]) # "1st compound concentration [" & Chr(181) & "M]"
		else:
			dfr_Partial.iloc[i,3] = np.nan
		dfr_Partial.iloc[i,4] = "Buffer ID"
		dfr_Partial.iloc[i,5] = "2nd compound ID"
		dfr_Partial.iloc[i,6] = "2nd compound concentration" # [" & Chr(181) & "M]"
		dfr_Partial.iloc[i,7] = round(dfr_PlateData.loc[i,"RatioInflections"][0],1) # Tm value, convert from K to C
		dfr_Partial.iloc[i,8] = dfr_PlateData.loc[i,"NormDTm"] # "Tm Shift" # [" & Chr(176) & "C]"
		dfr_Partial.iloc[i,9] = round(dfr_PlateData.loc[i,"RatioSlopes"][0],4) #"slope at Tm" # [DI/" & Chr(176) & "C]"
		dfr_Partial.iloc[i,10] = dfr_Details.loc["ELN","Value"] # ELN Page
		dfr_Partial.iloc[i,11] = "No Comment"
	
	return dfr_Partial

##########################################
##                                      ##
##    #####    ####   ######  ######    ##
##    ##  ##  ##  ##    ##    ##        ##
##    #####   ######    ##    ####      ##
##    ##  ##  ##  ##    ##    ##        ##
##    ##  ##  ##  ##    ##    ######    ##
##                                      ##
##########################################

def create_dataframe_rate(dfr_RawData, dfr_Samples, dfr_Layout, dlg_Progress):
	"""
		Takes re-arranged raw data arrays(well as index and first column, plate readings in the subsequent columns)
		and the array with sample IDs, locations and concentrations and creates the data dataframe that will be used
		to calculate values based on the assay type.
	"""
	# This function is called per plate, so there will only be one plate name
	str_PlateName = dfr_Samples.loc[0,"DestinationPlateName"]

	lst_SampleIDs = []
	lst_SampleIDs = set_to_nan(384)
	int_Samples = 0
	for i in range(len(dfr_Samples)):
		for j in range(len(dfr_Samples.loc[i,"Locations"])):
			lst_SampleIDs[dfr_Samples.loc[i,"Locations"][j]] = dfr_Samples.loc[i,"SampleID"]
			if pd.isna(lst_SampleIDs[dfr_Samples.loc[i,"Locations"][j]]) == False:
				int_Samples += 1
	# Create new dataframe
	lst_Columns = ["DestinationPlateName","SampleID","Well","Time","Signal","DoFit","ManualRate","RawFit","RawFitPars","RawFitCI","RawFitR2","RawFitErrors",
		"Norm","NormFit","NormFitPars","NormFitCI","NormFitR2","NormFitFreeErrors","NormDeriv","DoNormFit","LinStart","LinStop","LinFitTime","LinFit","LinFitPars",
		"LinFitCI","LinFitErrors","LinFitR2","DoLinFit","Show"]
	dfr_Processed = pd.DataFrame(columns=lst_Columns, index=range(int_Samples))
	#fltAssayVolume = float(str_AssayVolume)
	k = 0
	dlg_Progress.lbx_Log.InsertItems(["Number of samples to process: " + str(int_Samples)], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processed 0 out of " + str(int_Samples) + " samples"], dlg_Progress.lbx_Log.Count)
	for i in range(len(lst_SampleIDs)):

		if type(lst_SampleIDs[i]) == str:
			
			dfr_Processed.loc[k,"DestinationPlateName"] = str_PlateName
			dfr_Processed.loc[k,"SampleID"] = lst_SampleIDs[i]
			dfr_Processed.loc[k,"Well"] = dfr_RawData.loc[k,"Well"]
			dfr_Processed.at[k,"Time"] = dfr_RawData.loc[k,"Time"]
			dfr_Processed.at[k,"Signal"] = dfr_RawData.loc[k,"Signal"]
			dfr_Processed.loc[k,"Show"] = 0
			dfr_Processed.loc[k,"ManualRate"] = False

			# Normalisation needs to happen before datafitting is attempted
			flt_SignalMin = np.min(dfr_Processed.loc[k,"Signal"])
			flt_SignalMax = np.max(dfr_Processed.loc[k,"Signal"]) - flt_SignalMin
			lst_Norm = []
			for j in range(len(dfr_Processed.loc[k,"Signal"])):
				lst_Norm.append((dfr_Processed.loc[k,"Signal"][j]-flt_SignalMin)/flt_SignalMax)
			dfr_Processed.at[k,"Norm"] = lst_Norm
			
			# Fitting criteria
			# Criteria for fit:
			dfr_Processed.loc[k,"DoFit"] = True
			dfr_Processed.loc[k,"DoLogFit"] = True
			dfr_Processed.loc[k,"DoLinFit"] = True
			int_Len = len(dfr_Processed.loc[k,"Time"])
			# Perform fit -> Check if fitting criteria are met in the first instance
			if dfr_Processed.loc[k,"DoFit"] == True:
				# Do The Fits
				fit, dfr_Processed.at[k,"RawFitPars"], dfr_Processed.at[k,"RawFitCI"], dfr_Processed.at[k,"RawFitErrors"], rsquare, success_raw = ff.fit_logMM_free(dfr_Processed.loc[k,"Time"], dfr_Processed.loc[k,"Signal"])
				fit, dfr_Processed.at[k,"NormFitPars"], dfr_Processed.at[k,"NormFitCI"], dfr_Processed.at[k,"NormFitFreeErrors"], rsquare, success_norm = ff.fit_logMM_free(dfr_Processed.loc[k,"Time"], dfr_Processed.loc[k,"Norm"])
				# -> Now check if fits were successful
				if success_raw == True:
					dfr_Processed.at[k,"RawFit"] = ff.draw_logMM(dfr_Processed.loc[k,"Time"],dfr_Processed.loc[k,"RawFitPars"])
					dfr_Processed.at[k,"RawFitR2"] = ff.calculate_rsquare(dfr_Processed.loc[k,"Signal"],dfr_Processed.loc[k,"RawFit"])
					dfr_Processed.loc[k,"DoLogFit"] = True
				else:
					dfr_Processed.at[k,"RawFit"], dfr_Processed.at[k,"RawFitPars"] = set_to_nan(int_Len), set_to_nan(4)
					dfr_Processed.loc[k,"RawFitR2"] = np.nan
					dfr_Processed.loc[k,"DoLogFit"] = False
				if success_norm == True:
					dfr_Processed.at[k,"NormFit"] = ff.draw_logMM(dfr_Processed.loc[k,"Time"],dfr_Processed.loc[k,"NormFitPars"])
					dfr_Processed.at[k,"NormFitR2"] = ff.calculate_rsquare(dfr_Processed.loc[k,"Signal"],dfr_Processed.loc[k,"NormFit"])
					dfr_Processed.at[k,"LinFit"], dfr_Processed.at[k,"LinFitPars"], dfr_Processed.at[k,"NormDeriv"], dfr_Processed.at[k,"LinStart"], dfr_Processed.at[k,"LinStop"], dfr_Processed.at[k,"LinFitCI"], dfr_Processed.at[k,"LinFitErrors"], dfr_Processed.at[k,"LinFitTime"] = ff.linear_fit(dfr_Processed.loc[k,"Time"], dfr_Processed.loc[k,"Signal"], dfr_Processed.loc[k,"NormFitPars"], 0,int_Len,"auto")
					dfr_Processed.loc[k,"LinFitR2"] = np.nan #ff.calculate_rsquare(dfr_Processed.loc[k,"Norm"],dfr_Processed.loc[k,"LinFit"])
					dfr_Processed.loc[k,"DoLinFit"] = True
				else:
					dfr_Processed.at[k,"NormFit"], dfr_Processed.at[k,"LinFit"], dfr_Processed.at[k,"NormDeriv"] = set_to_nan(int_Len), set_to_nan(int_Len), set_to_nan(int_Len)
					dfr_Processed.at[k,"NormFitPars"] = set_to_nan(4)
					dfr_Processed.loc[k,"NormFitFitR2"] = np.nan
					dfr_Processed.at[k,"LinStart"] = np.nan
					dfr_Processed.at[k,"LinStop"] = np.nan
					dfr_Processed.loc[k,"LinFitPars"] = set_to_nan(2)
					dfr_Processed.loc[k,"LinFitCI"] = set_to_nan(2)
					dfr_Processed.loc[k,"LinFitErrors"] = set_to_nan(2)
					dfr_Processed.loc[k,"LinFitR2"] = np.nan
					dfr_Processed.loc[k,"DoLinFit"] = False
			else:
				dfr_Processed.at[k,"RawFit"], dfr_Processed.at[k,"RawFitPars"] = set_to_nan(len(dfr_Processed.loc[k,"Signal"])), set_to_nan(4)
				dfr_Processed.loc[k,"RawFitR2"] = np.nan
				dfr_Processed.at[k,"NormFit"], dfr_Processed.at[k,"NormFitPars"] = set_to_nan(len(dfr_Processed.loc[k,"Signal"])), set_to_nan(4)
				dfr_Processed.loc[k,"NormFitR2"] = np.nan
				dfr_Processed.loc[k,"LinFit"] = set_to_nan(len(dfr_Processed.loc[k,"Signal"]))
				dfr_Processed.loc[k,"LinFitPars"] = set_to_nan(2)
				dfr_Processed.loc[k,"LinFitR2"] = np.nan
			dfr_Processed.loc[k,"Show"] = 0
			dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Samples) + " " + str(k+1) + " out of " + str(int_Samples) + " samples.")
			k += 1

	# Placeholder
	dfr_References = pd.DataFrame(data={"Solvent":[1234],"Buffer":[1234],"Control":[1234]},index=["Plate1"])
	# Return
	return dfr_Processed, dfr_References

def create_Database_frame_rate(dfr_Details,lstHeaders,dfr_PlateData):
	# Filter out controls:
	dfr_PlateData = dfr_PlateData[dfr_PlateData["SampleID"] != "Control"]
	# Create partial Database frame
	dfr_Partial = pd.DataFrame(columns=lstHeaders,index=range(len(dfr_PlateData)))
	# Go through dfr_PlateData and write into dfPatial
	for i in range(len(dfr_PlateData)):

		dfr_Partial.iloc[i,0] = float(dfr_Details.loc["ProteinConcentration","Value"]) # protein concentration in uM.
		dfr_Partial.iloc[i,1] = dfr_Details.loc["PurificationID","Value"] # Purification ID
		dfr_Partial.iloc[i,2] = dfr_PlateData.loc[i,"SampleID"] # Sample ID/Global Compound ID # THIS WILL NEED TO BE CHANGED LATER
		dfr_Partial.iloc[i,3] = 100 # moles_to_micromoles(dfr_PlateData.loc[i,"Concentrations"])[0] # "1st compound concentration [" & Chr(181) & "M]"
		dfr_Partial.iloc[i,4] = "Buffer ID"
		dfr_Partial.iloc[i,5] = "2nd compound ID"
		dfr_Partial.iloc[i,6] = "2nd compound concentration" # [" & Chr(181) & "M]"
		dfr_Partial.iloc[i,7] = "rate" #round(dfr_PlateData.loc[i,"RawFitPars"][4]) # Tm value, convert from K to C
		dfr_Partial.iloc[i,8] = "Tm Shift" # [" & Chr(176) & "C]"
		dfr_Partial.iloc[i,9] = "slope at Tm" # [DI/" & Chr(176) & "C]"
		dfr_Partial.iloc[i,10] = dfr_Details.loc["ELN","Value"] # ELN Page
		dfr_Partial.iloc[i,11] = "No Comment"
	
	return dfr_Partial

def recalculate_fit_rate(dfr_Input):
	# Re-fit
	lst_LinFit, lst_LinFitPars, lst_Derivative, int_Start, int_Stop, dfr_Input.at["LinFitCI"], dfr_Input.at["LinFitErrors"], dfr_Input.at["LinFitTime"]  = ff.linear_fit(dfr_Input.loc["Time"], dfr_Input.loc["Signal"], dfr_Input.loc["NormFitPars"],
		dfr_Input.loc["LinStart"],dfr_Input.loc["LinStop"],"manual")
	# Update dfr_Input
	for i in range(len(lst_LinFitPars)):
		dfr_Input.loc["LinFitPars"][i] = lst_LinFitPars[i]
	dfr_Input.at["LinFit"] = lst_LinFit
	#for i in range(len(lst_LinFit)):
	#	dfr_Input.loc["LinFit"][i] = lst_LinFit[i]
	dfr_Input.loc["LinFitR2"] = ff.calculate_rsquare(dfr_Input.loc["Norm"],dfr_Input.loc["LinFit"])
	# LinStart and LinStop do not need to be assigned int_Start and int_Stop if they have been chosen manually.
	return dfr_Input

def write_Rate(flt_Rate, bol_DoFit, flt_PlusMinus):
	# Cannot do a direct type check as the curve fit returns numpy.float64.
	# When I read it in after saving the file it comes back as python native float and I have not figured out a sensible way to convert, yet.
	if bol_DoFit == False or str(type(flt_Rate)).find("float") == -1: # actually calculated values seem to be numpy.float64?
		return "N.D."
	else:
		return str(round(flt_Rate, 1)) + " " + chr(177) + " " + str(round(flt_PlusMinus, 1)) + " 1/s"


##########################################
##                                      ##
##     #####  #####    #####   #####    ##
##    ##      ##  ##  ##      ##        ##
##    ##      #####   ##       ####     ##
##    ##      ##  ##  ##          ##    ##
##     #####  #####    #####  #####     ##
##                                      ##
##########################################

def get_CompleteContainer_CBCS(dfr_DataStructure, dfr_Layout, dlg_Progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates, str_DataProcessor):

	#dfr_AssayData = pd.DataFrame(index=[0],columns=["Column"])

	#dfr_AssayData.at[0,"Column"] = create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_Progress, lst_Concentrations, lst_Conditions, lst_Replicates)
	# read raw data
	int_Plates = dfr_DataStructure.shape[0]
	dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Reading raw data files:"], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["0 out of " + str(int_Plates) + " files read."], dlg_Progress.lbx_Log.Count)
	k = 0
	for idx in dfr_DataStructure.index:
		dfr_DataStructure.at[idx,"RawData"] = ro.get_operetta_readout(dfr_DataStructure.loc[idx,"FilePath"], str_DataProcessor)
		dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Plates) + " " + str(k+1) + " out of " + str(int_Plates) + " files read.")
		k += 1

	return create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_Progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates)

def create_dataframe_CBCS(dfr_DataStructure, dfr_Layout, dlg_Progress, lst_Concentrations, lst_Conditions, str_ReferenceCondition, lst_Replicates):

	dfr_ReferenceLocations = CBCS_get_references(dfr_Layout)

	int_PlateFormat = dfr_DataStructure.loc[dfr_DataStructure.index[0],"RawData"].shape[0]

	# Normalise data and determine control values:
	int_Plates = dfr_DataStructure.shape[0]
	dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Normalising plates:"], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["0 out of " + str(int_Plates) + " plates normalised."], dlg_Progress.lbx_Log.Count)

	k = 0
	for idx in dfr_DataStructure.index:
		dfr_DataStructure.at[idx,"Normalised"], dfr_DataStructure.at[idx,"Controls"] = CBCS_normalise_plate(dfr_DataStructure.loc[idx,"RawData"], dfr_ReferenceLocations)
		dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Plates) + " " + str(k+1) + " out of " + str(int_Plates) + " plates normalised.")
		k += 1

	lst_ConcIndices = []
	lst_CondIndices = []
	for conc in lst_Concentrations:
		for cond in lst_Conditions:
			lst_ConcIndices.append(conc)
			lst_CondIndices.append(cond)
	lst_Indices = [lst_ConcIndices, lst_CondIndices]
	dfr_Processed = pd.DataFrame(index=lst_Indices,columns=["Data","PerCent","Controls","m","c","RSquare","Pearson"])

	# process normalised data
	int_Conditions = len(lst_CondIndices)
	k = 0
	dlg_Progress.lbx_Log.InsertItems([""], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["Processing conditions:"], dlg_Progress.lbx_Log.Count)
	dlg_Progress.lbx_Log.InsertItems(["0 out of " + str(int_Conditions) + " conditions processed."], dlg_Progress.lbx_Log.Count)
	for conc in lst_Concentrations:
		for cond in lst_Conditions:
			# Prepare empty lists:
			lst_RawMean = make_list(int_PlateFormat, np.nan)
			lst_NormMean = make_list(int_PlateFormat, np.nan)
			lst_NormMedian = make_list(int_PlateFormat, np.nan)
			lst_NormSTDEV = make_list(int_PlateFormat, np.nan)
			lst_NormMAD = make_list(int_PlateFormat, np.nan)
			lst_NormMeanPerCent = make_list(int_PlateFormat, np.nan)
			lst_ZScore = make_list(int_PlateFormat, np.nan)
			lst_DeltaZScore = make_list(int_PlateFormat, np.nan)

			# process wells:
			lst_SampleWells = []
			for well in range(int_PlateFormat):
				lst_RawValues = []
				lst_NormValues = []
				lst_PerCentValues = []
				for rep in lst_Replicates:
					idx = (conc,cond,rep)
					lst_RawValues.append(dfr_DataStructure.loc[idx,"RawData"].loc[well,"Readout"])
					lst_NormValues.append(dfr_DataStructure.loc[idx,"Normalised"].loc[well,"Normalised"])
					lst_PerCentValues.append(dfr_DataStructure.loc[idx,"Normalised"].loc[well,"PerCent"])
				# if there are only nan values, we don't need to write in the list
				if any_nonnan(lst_NormValues) == True:
					lst_RawMean[well] = np.nanmean(lst_RawValues)
					lst_NormMean[well] = np.nanmean(lst_NormValues)
					lst_NormMedian[well] = np.nanmedian(lst_NormValues)
					lst_NormSTDEV[well] = np.nanstd(lst_NormValues)
					lst_NormMAD[well] = MAD_list(lst_NormValues)
					lst_NormMeanPerCent[well] = np.nanmean(lst_PerCentValues)

			dfr_Processed.at[(conc,cond),"Data"] = pd.DataFrame(data={"RawMean":lst_RawMean,"NormMean":lst_NormMean,"NormMedian":lst_NormMedian,
				"NormSTDEV":lst_NormSTDEV,"NormMAD":lst_NormMAD,"ZScore":lst_ZScore,"DeltaZScore":lst_DeltaZScore,"NormMeanPerCent":lst_NormMeanPerCent})

			dfr_Processed.loc[(conc,cond),"m"], dfr_Processed.loc[(conc,cond),"c"], dfr_Processed.loc[(conc,cond),"RSquare"], dfr_Processed.loc[(conc,cond),"Pearson"] = ff.calculate_repcorr(dfr_DataStructure.loc[(conc,cond,"R1"),"Normalised"]["PerCent"],
				dfr_DataStructure.loc[(conc,cond,"R2"),"Normalised"]["PerCent"])

			dfr_Processed.at[(conc,cond),"Controls"] = CBCS_calculate_controls(lst_NormMean, dfr_ReferenceLocations)
			
			# Calculate ZScores
			pop_mean = dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormMean"]
			pop_stdev = dfr_Processed.loc[(conc,cond),"Controls"].loc["SamplePopulation","NormSTDEV"]
			# ZScore = ((value of sample i)-(mean of all samples))/(STDEV of population)
			for well in range(int_PlateFormat):
				dfr_Processed.at[(conc,cond),"Data"].loc[well,"ZScore"] = (lst_NormMean[well]-pop_mean)/pop_stdev

			dlg_Progress.lbx_Log.SetString(dlg_Progress.lbx_Log.Count - 1, ProgressGauge(k+1,int_Conditions) + " " + str(k+1) + " out of " + str(int_Conditions) + " conditions processed.")
			k += 1

	# get Delta Z Score:
	if not str_ReferenceCondition == None:
		for conc in lst_Concentrations:
			for cond in lst_Conditions:
				for well in range(int_PlateFormat):
					dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"] = dfr_Processed.loc[(conc,cond),"Data"].loc[well,"ZScore"] - dfr_Processed.loc[(conc,str_ReferenceCondition),"Data"].loc[well,"ZScore"]

	dfr_SampleInfo = pd.DataFrame(columns=["MaxDeltaZScore"],index=range(int_PlateFormat))

	# get largest change from
	for well in range(int_PlateFormat):
		for conc in lst_Concentrations:
			for cond in lst_Conditions:
				if pd.isna(dfr_SampleInfo.loc[well,"MaxDeltaZScore"]) == True:
					dfr_SampleInfo.loc[well,"MaxDeltaZScore"] = dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"]
				elif dfr_SampleInfo.loc[well,"MaxDeltaZScore"] > dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"]:
					dfr_SampleInfo.loc[well,"MaxDeltaZScore"] = dfr_Processed.loc[(conc,cond),"Data"].loc[well,"DeltaZScore"]

	return dfr_DataStructure, dfr_Processed, dfr_SampleInfo

def CBCS_normalise_plate(dfr_RawData, dfr_ReferenceLocations):

	# This function normalises the raw data and returns the normalised data for sample population and
	# the reference/control values (i.e. the mean, median, STDEV, MAD of each reference/control)

	int_PlateFormat = dfr_RawData.shape[0]
	#dfr_Normalised = pd.DataFrame(index=range(int_PlateFormat),columns=["Row","Column","Readout"])

	# list of controls to exclude them from normalisation
	lst_SampleLocations = []
	try:
		lst_SampleLocations.extend(dfr_ReferenceLocations.loc["SamplePopulation","Locations"])
	except:
		None
	try:
		lst_SampleLocations.extend(dfr_ReferenceLocations.loc["Solvent","Locations"])
	except:
		None

	# Prepare dataframe to return data

	dfr_Return = pd.DataFrame(index=range(int_PlateFormat),data={"PerCent":make_list(int_PlateFormat,np.nan),
	"Normalised":dfr_RawData["Readout"].tolist(),"Row":dfr_RawData["Row"].tolist(),"Column":dfr_RawData["Column"].tolist()})

	# get controls and solvent reference values
	dfr_Controls = CBCS_calculate_controls(dfr_RawData["Readout"], dfr_ReferenceLocations)

	# normalise as per-cent of solvent reference
	for well in range (int_PlateFormat):
		dfr_Return.loc[well,"PerCent"] = round(100 * dfr_RawData.loc[well,"Readout"]/dfr_Controls.loc["Solvent","NormMean"],2)

	# make dataframe for raw data that excludes all control compound wells:
	dfr_RawDataNoControls = dfr_RawData.filter(items=lst_SampleLocations, axis=0)

	# Normalise each well in a column against column median
	# Get each uniwue column and row
	columns = dfr_RawData["Column"].dropna().unique()
	rows = dfr_RawData["Row"].dropna().unique()

	normalise = True
	if normalise == True:
		# First: get median of each column -> save in dictionary with column as key
		lst_ColumnMedian = {}
		for col in columns:
			lst_ColumnMedian[col] = dfr_RawDataNoControls[dfr_RawDataNoControls["Column"]==col]["Readout"].median()
		# Second: normalise each well against the corresponding column's median
		for well in range(int_PlateFormat):
			if pd.isna(dfr_RawData.loc[well,"Column"]) == False:
				dfr_Return.loc[well,"Normalised"] = dfr_RawData.loc[well,"Readout"]/lst_ColumnMedian[dfr_RawData.loc[well,"Column"]]
		# Third: get median of each row after column normalisation, re-use dfr_RawDataNoControls -> save in dictionary with row as key
		lst_RowMedian = {}
		dfr_NormalisedByColumn = dfr_Return.filter(items=lst_SampleLocations, axis=0)
		for row in rows:
			lst_RowMedian[row] = dfr_NormalisedByColumn[dfr_NormalisedByColumn["Row"]==row]["Normalised"].median()
		# Fourth: normalise each well against the corresponding row's median
		for well in range(int_PlateFormat):
			if pd.isna(dfr_RawData.loc[well,"Row"]) == False:
				dfr_Return.loc[well,"Normalised"] = dfr_Return.loc[well,"Normalised"]/lst_RowMedian[dfr_Return.loc[well,"Row"]]

	return dfr_Return, dfr_Controls

def CBCS_get_references(dfr_Layout):
	
	lst_ControlNumericals = []
	lst_ControlIDs = []

	dfr_ReferenceLocations = pd.DataFrame(index=["Solvent","SamplePopulation"],columns=["Locations"])
	dfr_ReferenceLocations.at["Solvent","Locations"] = []
	dfr_ReferenceLocations.loc["SamplePopulation","Locations"] = []

	for i in range(len(dfr_Layout.loc[0,"WellType"])):
		if dfr_Layout.loc[0,"WellType"][i] == "r": # r = reference
			dfr_ReferenceLocations.loc["Solvent","Locations"].append(i)
		elif dfr_Layout.loc[0,"WellType"][i] == "s": # s = sample
			dfr_ReferenceLocations.loc["SamplePopulation","Locations"].append(i)

	for i in range(len(dfr_Layout.loc[0,"ControlNumerical"])):
		if not dfr_Layout.loc[0,"ControlNumerical"][i] == "":
			if not dfr_Layout.loc[0,"ControlNumerical"][i] in lst_ControlNumericals:
				lst_ControlNumericals.append(dfr_Layout.loc[0,"ControlNumerical"][i])
				lst_ControlIDs.append(dfr_Layout.loc[0,"ControlID"][i])
				dfr_ReferenceLocations.at[dfr_Layout.loc[0,"ControlID"][i],"Locations"] = []
				dfr_ReferenceLocations.loc[dfr_Layout.loc[0,"ControlID"][i],"Locations"].append(i)
			else:
				dfr_ReferenceLocations.loc[dfr_Layout.loc[0,"ControlID"][i],"Locations"].append(i)

	return dfr_ReferenceLocations

def CBCS_calculate_controls(lst_Data, dfr_ReferenceLocations):

	# Add new columns to dfr_ReferenceLocations and return it as dfr_Controls

	# go through each reference/control type
	for ref in dfr_ReferenceLocations.index:
		lst = []
		for idx_Well in dfr_ReferenceLocations.loc[ref,"Locations"]:
			lst.append(lst_Data[idx_Well])
		if any_nonnan(lst) == True:
			dfr_ReferenceLocations.loc[ref,"NormMean"] = np.nanmean(lst)
			dfr_ReferenceLocations.loc[ref,"NormMedian"] = np.nanmedian(lst)
			dfr_ReferenceLocations.loc[ref,"NormMAD"] = MAD_list(lst)
			dfr_ReferenceLocations.loc[ref,"NormSTDEV"] = np.nanstd(lst)
		else:
			dfr_ReferenceLocations.loc[ref,"NormMean"] = np.nan
			dfr_ReferenceLocations.loc[ref,"NormMedian"] = np.nan
			dfr_ReferenceLocations.loc[ref,"NormMAD"] = np.nan
			dfr_ReferenceLocations.loc[ref,"NormSTDEV"] = np.nan

	return dfr_ReferenceLocations