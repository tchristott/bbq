"""
Library of functions to handle mircotiter plate based data

Functions:
    plate_type_string
    plate_columns
    plate_rows
    col_row_to_index
    index_to_row_col
    index_to_well
    write_well_list
    well_to_index
    well_to_index_96
    well_to_index_384
    well_to_index_1536
    pherastar_well
    pherastar_plate
    GridFormat
    sortable_well
    sortable_well_96
    sortable_well_384
    sortable_well_1536
    well_z
    well_z_1
    well_z_2
    well_z_3
    well_z_4
    invert_well
    iswell

"""

from math import ceil

def plate_type_string(plate: str):
    """
    Returns the plate type (integer) based on finding the number of
    wells in a string.
    Example: "Proxiplate_384PS"-> 384
    """
    if "1536" in plate:
        return 1536
    elif "384" in plate:
        return 384
    elif "96" in plate:
        return 96
    else:
        return False
    # elif "48" in strPlateType:
    #    return 48

def plate_columns(w: int):
    """
    Returns number of columns on a given plate with w wells as integer.
    Returns false if argument is not a recognised plate format.
    """
    if w == 48:
        return 6
    elif w == 96:
        return 12
    elif w == 384:
        return 24
    elif w == 1536:
        return 48

def plate_rows(w: int):
    """
    Returns number of rows on a given plate with w wells as integer.
    Returns false if argument is not a recognised plate format.
    """
    # Pick number of rows
    if w == 48:
        return 4
    elif w == 96:
        return 8
    elif w == 384:
        return 16
    elif w == 1536:
        return 32
    else:
        return False

def col_row_to_index(row, col, pf):
    return row * plate_columns(pf) + col

def index_to_row_col(int_Index, int_Rows, int_Columns):
    int_Index += 1
    row = ceil(int_Index/int_Columns)
    col = int(int_Index-((row-1)*int_Columns))
    return row-1, col-1

def index_to_well(ind: int, pf: int):
    """
    Convert a well index to a text coordinate.

    Examples: 0 -> A01; 383 -> P24

    Arguments:
        ind -> integer. Index of well
        pf -> integer. Plate format, i.e. total number of wells on plate.

    Returns well as string.
    """
    pcols = plate_columns(pf)
    mcols = ceil(ind / pcols)
    cols = str(pcols - (mcols * pcols - ind))
    # Ensure the coordinates can be sorted properly, i.e. the string
    # "A1" becomes "A01" so that "A10" comes after "A09" and not "A1"
    # when sorting.
    if len(cols) == 1: 
        cols = "0" + cols
    # Return the well
    if mcols <= 26: # Alphabet has 26 letters you plonker!
        return chr(64 + mcols) + cols
    else:
        return "A" + chr(64 + mcols - 26) + cols

def write_well_list(pf: int):
    """
    Returns a list of all well coordinates in format "A01"
    on a plate of a given format.

    Arguments:
        pf -> integer. Plate format, i.e. total number of
              wells on plate.
    """
    wells = []
    for i in range(pf):
        wells.append(index_to_well(i+1,pf))
    return wells

def well_to_index(well: str, pf: int):
    """
    Converts well coordinate into index.
    
    Example: A01 -> 0

    Arguments:
        well -> string. Coordinate to be converted
        pf -> integer. Plate format, i.e. total number of wells on plate
    """
    # preceding is the number of preceding wells before the current row, based
    # on the letter part of the coordinate. in row A (ASCII 65), there are
    # 0 preceding rows. In row B, there is one preceding row, times 12/24/48
    # wells, depending on the plate type.
    pcols = plate_columns(pf)
    if pf != 1536:
        preceding = (ord(well[0:1]) - 65) * pcols
        int_Well =  preceding + int(well[1:])
    else:
        # First check whether it is in the PheraStar format or the ECHO format.
        # ASCII code for lower case letters starts with at 97 with "a"
        if not well[0:1]== "a":
            # Check if second character is a 0
            if well[1:2] == "0":
                cols = ord(well[0:1]) - 65
                int_Well = cols * pcols + int(well[2:])
            else:
                cols = 26 + (ord(well[1:2]) - 65)
                int_Well =  cols * pcols + int(well[3:])
        else:
            cols = ord(well[0:1]) - 96 + 25
            int_Well =  cols * pcols + int(well[2:])
    # indexing starts at 0.
    return int_Well - 1

def well_to_index_96(well: str):
    """
    Wrapper function of well_to_index() for 96 well plates
    """
    return well_to_index(well, 96)

def well_to_index_384(well: str):
    """
    Wrapper function of well_to_index() for 384 well plates
    """
    return well_to_index(well, 384)

def well_to_index_1536(well: str):
    """
    Wrapper function of well_to_index() for 1536 well plates
    """
    return well_to_index(well, 1536)

def sortable_well(well: str, pf: int):
    """
    Turns any well coordinate into a alphabetically sortable one.
    
    Example: "A1" -> "A01"
    For 1536 well plates: add another "0" and also ensure that wells
    beyond "Z048" start with "AA01", not "a01"

    Arguments:
        well -> string. Well to be converted
        pf -> integer. Plate format, i.e. number of wells.

    Returns converted coordinate as string.
    """
    if pf != 1536:
        if len(well) == 2:
            well = well[0:1] + "0" + well[1:]
    else:
        # check whether we are dealing with lower case lettering:
        if ord(well[0:1]) > 96 and ord(well[0:1]) < 103:
            well = "A" + chr(ord(well[0:1])-32) + well[1:]
        # add "0"s to get string length to four characters
        if len(well) == 2:
            well = well[0:1] + "00" + well[1:]
        elif len(well) == 3:
            if ord(well[1:2]) > 57: # Unicode 57 is Character "9"
                well = well[0:2] + "0" + well[1:]
            else:
                well = well[0:1] + "0" + well[2:]
    return well

def sortable_well_96(well: str):
    """
    Wrapper function of sortable_well() for 96 well plates.
    """
    return sortable_well(well, 96)

def sortable_well_384(well: str):
    """
    Wrapper function of sortable_well() for 384 well plates.
    """
    return sortable_well(well, 384)

def sortable_well_1536(well: str):
    """
    Wrapper function of sortable_well() for 1536 well plates.
    """
    return sortable_well(well, 1536)

# Get plate format from dimensions of plate grid
def GridFormat(grd_Plate):
    if grd_Plate.GetNumberCols() == 12:
        return 96
    elif grd_Plate.GetNumberCols() == 24:
        return 384
    elif grd_Plate.GetNumberCols() == 48:
        return 1536

# Plate reader specific functions:
def pherastar_well(well: str):
    """
    Parses the string with the plate name and well as used in
    list based PheraStar output files, e.g.
    "Destination Plate 1: A01" and returns the well coordinates
    as string.

    Argument:
        well -> string. Contains the well to be extracted.
    """
    colon = well.find(":", 0, len(well))+2
    return well[colon:len(well)]

def pherastar_plate(well: str):
    """
    Parses the string with the plate name and well as used in
    list based PheraStar output files, e.g.
    "Destination Plate 1: A01" and returns the plate name as
    string.

    Argument:
        well -> string. Contains the well to be extracted.
    """
    colon = well.find(":", 0, len(well))
    return well[0:colon]

def well_z(well: str, quadrant: int):
    """
    Converts a well on a 96 well plate into a well on a 384 well plate.

    Use to translate coordinates when combining contents of up to four
    96 well plates into one 384 well plate. Merging patterns for
    quadrants is Q1-Q2-Q4-Q3 (clockwise).

    Example: P1_A01->A01, P2_A01->A02, P3_A01->B01, P4_A01->B02

    Arguments:
        well -> string. Coordinate of source well.
        quadrant -> integer. Target quadrant.

    Returns translated coordinate as string.
    """

    # Convert to number coordinates:
    row = ord(well[0:1])-64
    col = int(well[:len(well)-1])
    # Move number coordinates:
    if quadrant == 1:
        row = row * 2 - 1
        col = col * 2 - 1
    elif quadrant == 2:
        row = row * 2 - 1
        col = col * 2
    elif quadrant == 3:
        row = row * 2
        col = col * 2 - 1
    elif quadrant == 4:
        row = row * 2
        col = col * 2
    # Convert col to string and return
    if col < 10:
        return chr(row+64) + "0" + str(col)
    else:
        return chr(row+64) + str(col)

def well_z_1(well: str):
    """
    Wrapper function of well_z to target first quadrant
    """
    return well_z(well, 1)

def well_z_2(well: str):
    """
    Wrapper function of well_z to target second quadrant
    """
    return well_z(well, 2)

def well_z_3(well: str):
    """
    Wrapper function of well_z to target third quadrant
    """
    return well_z(well, 3)

def well_z_4(well: str):
    """
    Wrapper function of well_z to target fourth quadrant
    """
    return well_z(well, 4)

def invert_well(ind: int, pf: int):
    """
    Flips the index of a well 180 degrees

    Useful in case a plate has been rotated 180 degrees at any step
    and the data is "upside down"

    Arguments:
        ind -> integer. Index of well on plate.
        pf -> integer. Plate format, i.e. total number of wells on plate.
    """
    # Get rows and cols on plate
    pcols = plate_columns(pf)
    prows = plate_rows(pf)
    # Get current row/column coordinates
    rows = ceil(ind / pcols)
    cols = (pcols - (rows * pcols - int))
    # Invert
    cols = pcols - cols + 1
    rows = prows - rows + 1
    # Return results
    return (rows - 1) * pcols + cols

def iswell(well: str):
    """
    Tests whether a string is a valid well coordinate.

    Arguments:
        well -> string. String to be evaluated.

    Returns True if true.
    """
    try:
        well = well_to_index_96(well)
        return True
    except:
        try:
            well = well_to_index_384(well)
            return True
        except:
            try:
                well = well_to_index_1536(well)
                return True
            except:
                return False