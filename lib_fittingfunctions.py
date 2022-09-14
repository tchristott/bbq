"""
Module containing functions for curve fitting.

For each mathematical function, there is a number of program functions:
    "fn" prefix: A program function that corresponds to the mathematical
                 function.
    "draw" prefix: A program function that uses the fn function to return
                   the results for the mathematical function for a list of
                   x values.
    "fit" prefix: A program function that performs the fitting of a dataset.
                  if suffixed, this denotes whether the fitting happens freely
                  (free) or with constraints (const), or whether only the
                  parameters get returned.

Functions:

    eq_linear
    eq_parabola
    eq_sigmoidal
    eq_logMM
    eq_logMM1stDerivative
    eq_thompson
    eq_krippendorff

    draw_any
    draw_linear
    draw_sigmoidal
    draw_logMM
    draw_thompson

    calculate_rsquare
    calculate_repcorr
    calculate_confidence

    fit_sigmoidal_free
    fit_sigmoidal_free_dataframe
    fit_sigmoidal_const
    draw_sigmoidal_fit_error
    fit_thompson
    fit_logMM_free


"""

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import curve_fit
from scipy.stats.distributions import t
# from scipy.interpolate import CubicSpline
from scipy.signal import savgol_filter
from math import isinf
import lib_datafunctions as df

#####  ###  #   #  ###  ##### #  ###  #   #  ####
#     #   # #   # #   #   #   # #   # ##  # #
###   #   # #   # #####   #   # #   # #####  ###
#     #  ## #   # #   #   #   # #   # #  ##     #
#####  ####  ###  #   #   #   #  ###  #   # ####

def eq_linear(x, m, c):
    """
    Function for linear equation

    Arguments:
        x -> float. Independent variable
        m -> float. Slope
        c -> float. Intercept
    """
    return (m * x) + c

def eq_parabola(x,a,b,c):
    return (a*x*x + b*x + c)

def eq_sigmoidal(x,ytop,ybot,h,i):
    """
    Function for sigmoidal dose response curve.
    
    Arguments:
        x -> float. concentration/dose
        ytop -> float. theoretical top of curve, ybot: theoretical bottom of curve (e.g. 100% and 0% inhibition)
        h -> float. Hill slope
        i -> float. inflection point
    """
    return ybot + (ytop - ybot)/(1 + (i/x)**h)

def eq_logMM(t, y0, b, t0):
    """
    Logarithmic approximation of Michaelis-Menten equation.

    Arguments:
        t -> float > 0 Timepoint
        y0 -> float. Baseline/Background signal.
        b -> float > 0. shape parameter
        t0 -> float. Scale of the curve.

    Reference: 
        Lu WP, Fei L. A logarithmic approximation to initial rates
        of enzyme reactions. Anal Biochem. 2003; 316(1):58-65
    """
    # needs to be np.log since math.log cannot deal with array
    return y0 + b * np.log(1 + t/t0)

def eq_logMM1stDerivative(t, y0, b, t0):
    """
    First derivative of log approximation of MIchaelis-Menten equation.

    Arguments:
        t -> float > 0 Timepoint
        y0 -> float. Baseline/Background signal.
        b -> float > 0. shape parameter
        t0 -> float. Scale of the curve.

    Reference: 
        Lu WP, Fei L. A logarithmic approximation to initial rates
        of enzyme reactions. Anal Biochem. 2003; 316(1):58-65
    """
    return b/(t0*(t/t0 + 1))

def eq_thompson(T,yf,mf,yu,mu,Tm,H):
    """
    Describes thermal unfolding of protein in a differential scanning
    fluorimetry assay.

    From Thompson et al https://www.sciencedirect.com/science/article/pii/S104620231100212X

    The equation gives really great results on really clean unfolding curves,
    not so much if the post transition plateu is missing for instance.

    Arguments:
        yf -> float. Intercept of pre-transition baseline (folded)
        mf -> float. Slope of pre-transition baseline
        yu -> float. Intercept of post-transition baseline
        mu -> float. Slope of post-transition baseline
        Tm -> float. Midpoint of transition
        H -> float. Enthalpy change for unfolding at Tm
    """
    return ((yf+(mf*T)) + (yu+(mu*T))*np.exp((H*((T-Tm)/Tm))/(8.3145*T)))/(1+np.exp((H*((T-Tm)/Tm)/(8.3145*T))))

def eq_krippendorf(t, IC50, S, KM, KI, kinact):
    """
    Equation for determining KI and Kinact from IC50 values.
    
    See Krippendorf et al, DOI:10.1177/1087057109336751

    Arguments:
        t -> timepoints
        IC50 -> measured IC50 values
        S -> substrate concentration
        KM -> 
        KI
        kinact
    """

    return (((1+(S/KM))*KI)/(((kinact*(IC50/((KI*(1+(S/KM)))+IC50)))*t)/((2-((kinact*(IC50/((KI*(1+(S/KM)))+IC50)))*t))-(2*np.exp((((-1)*kinact)*(IC50/((KI*(1+(S/KM)))+IC50)))*t)))))


####  ####   ###  #     # # #   #  ####
#   # #   # #   # #     # # ##  # #
#   # ####  ##### #  #  # # ##### #  ##
#   # #   # #   # #  #  # # #  ## #   #
####  #   # #   #  ## ##  # #   #  ####

def draw_any(func,xdata,pars):
    """
    Calculates ydata for any equation given xdata and
    values for equation's parameters

    Arguments:
        func -> function to use
        xdata -> list of numbers. Independent variable
        pars -> list of floats. Values for parameters
    """
    ydata = []
    for x in xdata:
        if pd.isna(x) == False:
            try:
                ydata.append(func(x, *pars))
            except OverflowError:
                ydata.append(np.nan)
        else:
            ydata.append(np.nan)
    return ydata

def draw_linear(xdata,pars):
    """
    Wrapper function for draw_any. Draws linear fit.

    Arguments:
        xdata -> list of numbers. Independent variable
        pars -> list of floats. Values for parameters
    """
    return draw_any(eq_linear,xdata,pars)

def draw_sigmoidal(doses, pars):
    """
    Wrapper function of draw_any.
    Draws sigmoidal dose response curve for given
    doses and parameters. Returns responses as
    list.

    Arguments:
        doses -> list of floats. Concentrations in Molar.
        pars -> list of floats. Values for sigmoidal dose response
                curve's parameters.
    """
    return draw_any(eq_sigmoidal,df.moles_to_micromoles(doses),pars)

def draw_logMM(time, pars):
    """
    Wrapper function of draw_any.
    Draws logarithmic approximation of MM kinetic

    Arguments:
        time -> list of floats. Timepoints
        pars -> list of floats. Values for sigmoidal dose response
                curve's parameters.
    """
    return draw_any(eq_logMM,time,pars)

def draw_thompson(temp, pars):
    """
    Wrapper function of draw_any.
    Draws thermal unfolding curve follong Thompson equation (eq_thompson)

    Arguments:
        temp -> list of floats. Temperature
        pars -> list of floats. Values for sigmoidal dose response
                curve's parameters.
    """
    return draw_any(eq_thompson,temp,pars)


####   ###  #####  ###     ###  #   #  ###  #     # ##### #   #
#   # #   #   #   #   #   #   # #   # #   # #     #   #   #   #
#   # #####   #   #####   #   # #   # ##### #     #   #    # #
#   # #   #   #   #   #   #  ## #   # #   # #     #   #     #
####  #   #   #   #   #    ####  ###  #   # ##### #   #     #

def calculate_rsquare(data,fit):
    """
    Calculates R square value for given dataset and fit.

    Arguments:
        data -> list of numbers. Datapoints
        fit -> list of numbers. Fit to be assessed for quality.

    Returns
        Rsquare as float.

    R square is calculated as follows:

    Rsquare = 1 - ((residual sum of squares)/(total sum of squares))
            = 1 - ((Sum(Yi - Yi,fit)^2)/(Sum(Yi - Ymean)^2))

    Where Yi is the measured response at datapoint i, Yi,fit is the
    result of the fit at i and Ymean is the mean of all datapoints.
    """

    # remove any errant np.nan values from data
    data_trim = []
    fit_trim = []
    for i in range(len(fit)):
        if np.isnan(data[i]) == False:
            data_trim.append(data[i])
            fit_trim.append(fit[i])

    mean = sum(data_trim)/len(data_trim)
    RSS = 0 # residual sum of squares
    TSS = 0 # total sum of squares
    for i in range(len(data_trim)):
        RSS += ((data_trim[i]-fit_trim[i])**2)
        TSS += ((data_trim[i]-mean)**2)
    return round(float(1 - (RSS/TSS)),4)

def calculate_repcorr(rep1, rep2):
    """
    Calculates replicate correlation for two given data sets.

    Arguments:
        rep1 -> list of floats. Replicate dataset 1
        rep2 -> list of floats. Replicate dataset 2

    Returns:
        m -> float. Slope of linear fit
        c -> float. Offset of linear fit
        Rsquare -> float. R square value of linear fit to
                   datasets (rep1 xdata, rep2 ydata)
        Pearson -> float. Pearson's correlation coefficient.
    """
    # Trim any errant np.nan values:
    rep1_trimmed = []
    rep2_trimmed = []
    for i in range(len(rep1)):
        if pd.isna(rep1[i]) == False and pd.isna(rep2[i]) == False:
            rep1_trimmed.append(rep1[i])
            rep2_trimmed.append(rep2[i])
    # Sort along "x" axis
    dfr_Temp = pd.DataFrame(data={"rep1":rep1_trimmed,"rep2":rep2_trimmed}).sort_values(by=["rep1"],ascending=[True])

    # Perform linear fit
    pars, covar = curve_fit(eq_linear, dfr_Temp["rep1"], dfr_Temp["rep2"])
    # get values for linear fit
    linfit = draw_linear(dfr_Temp["rep1"], pars)
    # Calculate R square and Pearson's correlation coefficient
    Rsquare = calculate_rsquare(dfr_Temp["rep1"],linfit)
    pearson = round(dfr_Temp.corr().loc["rep1","rep2"],4)

    return pars[0], pars[1], Rsquare, pearson

def calculate_confidence(n,pars,covar):
    """
    Calculates 95% conficende interval for parameters
    based on covariance values.

    Arguments:
        n -> integer. Number of paramters in equation
        pars -> list of floats. Values for parameters.
        covar -> list of floats. Covariances for each parameter
    """
    # http://kitchingroup.cheme.cmu.edu/blog/2013/02/12/Nonlinear-curve-fitting-with-parameter-confidence-intervals/

    confidence = []
    p = len(pars)

    alpha = 0.05 # 95% confidence interval = 100*(1-alpha)

    # number of degrees of freedom
    dof = max(0, n - p) 

    # student-t value for the dof and confidence level
    tval = t.ppf(1.0-alpha/2., dof) 

    for i, p, flt_Variance in zip(range(n), pars, np.diag(covar)):
        if isinf(flt_Variance) == False:
            sigma = flt_Variance**0.5
            plusminus = sigma*tval
            confidence.append(plusminus)
        else:
            confidence.append(np.nan)
    
    return confidence

def fit_sigmoidal_free(doses, responses, parsonly = False, skiptrim = False):
    """
    Fits sigmoidal dose response curve to the provided
    dataset without constraints. Uses scipy.optimize.curve_fit
    for the heavy lifting.

    Arguments:
        doses -> list of floats. Concentrations in Molar.
        responses -> list of floats.
        parsonly -> boolean. If true, does not return fit, success, Rsquare
        skiptrim -> boolean. If True, does not adjust doeses from molar to
                    micromolar.

    Returns:
        fit -> list of floats. Fitted curve
        pars => list of floats. Values for curve's parameters.
        confidence -> list of floats. Values for 95% confidence
                      intervals for parameters.
        stderr -> list of floats. Values for standar error of fit
                  for each parameter.
        Rsquare -> R square value for curve fit.
        success -> boolean. True if a succesful fit was achieved.
    """
    # trim any stray np.nan from response.
    if skiptrim == False:
        resp_trim = []
        doses_trim = []
        for i in range(len(responses)):
            if np.isnan(responses[i]) == False:
                resp_trim.append(responses[i])
                doses_trim.append(doses[i])
    else:
        resp_trim = responses
        doses_trim = doses
    # Convert units:
    doses_trim = df.moles_to_micromoles(doses_trim)
    # Perform curve_fit with scipy:
    try:
        pars, covar = curve_fit(eq_sigmoidal,
                                doses_trim,
                                resp_trim)
        confidence = calculate_confidence(len(doses_trim),
                                          pars,
                                          covar)
        stderr = np.sqrt(np.diagonal(covar))
        if parsonly == False:
            fit = draw_any(eq_sigmoidal,df.moles_to_micromoles(doses), pars)
            Rsquare = calculate_rsquare(responses,fit)
        else:
            fit = []
            Rsquare = np.nan
        success = True
    except RuntimeError:
        pars = df.set_to_nan(4)
        confidence = df.set_to_nan(4)
        stderr = df.set_to_nan(4)
        fit = df.set_to_nan(len(doses))
        Rsquare = np.nan
        success = False
    except ValueError:
        pars = df.set_to_nan(4)
        confidence = df.set_to_nan(4)
        stderr = df.set_to_nan(4)
        fit = df.set_to_nan(len(doses))
        Rsquare = np.nan
        success = False

    if parsonly == False:
        return fit, pars, confidence, stderr, Rsquare, success
    else:
        return pars, confidence, stderr

def fit_sigmoidal_free_dataframe(doses, responses, parsonly = False, skiptrim = False):

    """
    DO NOT USE
    This is a work in progress. At present, the issue that the dataframe would
    need a "success" returned but the fitting function does not return one
    when parsonly == True.
    """

    if parsonly == False:
        fit, pars, confidence, stderr, Rsquare, success = fit_sigmoidal_free(doses,
                                                                             responses,
                                                                             parsonly,
                                                                             skiptrim)
    else:
        pars, confidence, stderr, success = fit_sigmoidal_free(doses,
                                                      responses,
                                                      parsonly,
                                                      skiptrim)
        Rsquare = np.nan
    

    # Order of parameters: ytop, ybot, h: Hill slope, i: inflection point
    dfr_Return = pd.DataFrame({"Fit":[fit],
                               "Top":pars[0],
                               "Bottom":pars[1],
                               "Slope":pars[2],
                               "Inflection":pars[3],
                               "Span":pars[0] - pars[1],
                               "TopCI":confidence[0],
                               "BottomCI":confidence[1],
                               "SlopeCI":confidence[2],
                               "InflectionCI":confidence[3],
                               "TopSTDERR":stderr[0],
                               "BottomSTDERR":stderr[1],
                               "SlopeSTDERR":stderr[2],
                               "InflectionSTDERR":stderr[3],
                               "RSquare":Rsquare,
                               "DoFit":success})

    return dfr_Return

def fit_sigmoidal_const(doses, responses, sem,parsonly = False, skiptrim = False):
    """
    Fits sigmoidal dose response curve to the provided
    dataset WITH constraints. Dataset HAS to be normalised
    to 0% - 100%. Constraints are:
        - Bottom between -20% and 20%
        - Top between 80% - 120%
    
    Uses scipy.optimize.curve_fit
    for the heavy lifting.

    Arguments:
        doses -> list of floats. Concentrations in Molar.
        responses -> list of floats.
        sem -> list of floats. Standard errors of mean for each
               datapoint
        parsonly -> boolean. If true, does not return fit, success, Rsquare
        skiptrim -> boolean. If True, does not adjust doeses from molar to
                    micromolar.

    Returns:
        fit -> list of floats. Fitted curve
        pars => list of floats. Values for curve's parameters.
        confidence -> list of floats. Values for 95% confidence
                      intervals for parameters.
        stderr -> list of floats. Values for standar error of fit
                  for each parameter.
        Rsquare -> R square value for curve fit.
        success -> boolean. True if a succesful fit was achieved.
    """
    # remove any stray np.nan from response
    if skiptrim == False:
        resp_trim = []
        doses_trim = []
        sem_trim = []
        for i in range(len(responses)):
            if np.isnan(responses[i]) == False:
                resp_trim.append(responses[i])
                doses_trim.append(doses[i])
                sem_trim.append(sem[i])
    else:
        resp_trim = responses
        doses_trim = doses
        sem_trim = sem
    # Convert units:
    doses_trim = df.moles_to_micromoles(doses_trim)
    # set values that are 0 to an arbitrary small value. At some point
    # downstream, scipy curve_fit tries to divide by sigma.
    # If sigma is 0... error!
    for i in range(len(sem_trim)):
        if sem_trim[i] == 0:
            sem_trim[i] = 0.01
    # Order of parameters: ytop, ybot, h: Hill slope, i: inflection point
    # Perform constrained curve_fit with scipy, for normalised data only
    # 120 > ytop > 80
    # 20 > ybot > -20
    # Perform curve_fit with scipy:
    try:
        pars, covar = curve_fit(eq_sigmoidal,
                                doses_trim,
                                resp_trim,
                                sigma=sem_trim,
                                absolute_sigma=True,
                                bounds=([90,-10,-np.inf,-np.inf],
                                        [110,10,np.inf,np.inf]))
        confidence = calculate_confidence(len(doses_trim),pars,covar)
        stderr = np.sqrt(np.diagonal(covar))
        if parsonly == False:
            fit = draw_any(eq_sigmoidal,df.moles_to_micromoles(doses), pars)
            Rsquare = calculate_rsquare(responses,fit)
        else:
            fit = []
            Rsquare = np.nan
        success = True
    except RuntimeError:
        pars = df.set_to_nan(4)
        confidence = df.set_to_nan(4)
        stderr = df.set_to_nan(4)
        fit = df.set_to_nan(len(doses))
        Rsquare = np.nan
        success = False
    except ValueError:
        pars = df.set_to_nan(4)
        confidence = df.set_to_nan(4)
        stderr = df.set_to_nan(4)
        fit = df.set_to_nan(len(doses))
        Rsquare = np.nan
        success = False

    if parsonly == False:
        return fit, pars, confidence, stderr, Rsquare, success
    else:
        return pars, confidence, stderr

def draw_sigmoidal_fit_error(doses, pars, stderr):
    """
    This function draws the area that covers the 95%
    confidence intervals for all parameters.

    Arguments:
        doses -> list of floats.
        pars -> list of floats. Values for the parameters
        stderr -> list of floats. standard error of the fit
                  for each parameter.
    """
    # parameters for IC50 in order: ytop,ybot,h,i

    rng_Datapoints = range(len(doses))
    
    upper = draw_any(eq_sigmoidal,df.moles_to_micromoles(doses),pars)
    lower = draw_any(eq_sigmoidal,df.moles_to_micromoles(doses),pars)
    
    lst_Combinations = [[1,1,1,1], #1
        [1,-1,1,1], #2
        [1,-1,-1,1], #3
        [1,-1,-1,-1], #4
        [1,1,1,-1], #5
        [1,1,-1,-1], #6
        [1,1,-1,1], #7
        [1,1,1,-1], #8
        [-1,1,1,1], #9
        [-1,-1,1,1], #10
        [-1,-1,-1,1], #11
        [-1,-1,-1,1], #12
        [-1,1,1,-1], #13
        [-1,1,-1,-1], #14
        [-1,1,-1,1], #15
        [-1,1,-1,-1]] #16

    # Go through possible combinations:
    for i in range(16):
        lst_Temp = draw_any(eq_sigmoidal,
                            df.moles_to_micromoles(doses),
                            [pars[0]+(stderr[0]*lst_Combinations[i][0]),
                             pars[1]+(stderr[1]*lst_Combinations[i][1]),
                             pars[2]+(stderr[2]*lst_Combinations[i][2]),
                             pars[3]+(stderr[3]*lst_Combinations[i][3])])
        # Compare and assign the highest/lowest values
        for k in rng_Datapoints:
            if lst_Temp[k] > upper[k]:
                upper[k] = lst_Temp[k]
            if lst_Temp[k] < lower[k]:
                lower[k] = lst_Temp[k]

    return upper, lower
    

def fit_thompson(temp, fluo, guess, parsonly = False):
    """
    DO NOT USE, WORK IN PROGRESS

    Fits the output from a DSF experiment to Thompson et al's
    equation.

    Arguments:
        temp -> list of floats. Temperatures at measurements
        fluo -> list of floats. Fluorescence measurements
        guess -> list of floats. Initial guesses for parameters
        parsonly -> boolean. Whether to return parameters only.
    """
    # remove any stray np.nan
    temp_trim = []
    fluo_trim = []
    for i in range(len(fluo)):
        if np.isnan(fluo[i]) == False:
            # Convert temp to Kelvin
            temp_trim.append(temp[i]+273.15)
            fluo_trim.append(fluo[i])
    fluo_trim = savgol_filter(fluo, 51, 3)

    # Perform curve_fit with scipy:
    try:
        pars, covar = curve_fit(eq_thompson,
                                temp_trim,
                                fluo_trim,
                                p0=guess)#, bounds=constraints)
        confidence = calculate_confidence(len(temp_trim),pars,covar)
        stderr = np.sqrt(np.diagonal(covar))
        success = True
        if parsonly == True:
            return pars.tolist(), success
        else:
            return pars.tolist(), confidence, stderr.tolist(), success
    except RuntimeError:
        pars = df.set_to_nan(7)
        confidence = df.set_to_nan(7)
        stderr = df.set_to_nan(7)
        success = False
        if parsonly == True:
            return pars, success
        else:
            return pars, confidence, stderr, success


def thermal_shift(temp, fluo, constraints, guess, parameters_only):

    """
    Here we take the derivative of the raw data. We achieve this by fitting a parabola
    through point x and it's two neighbours.
    Since we know the equation for the parabola, we can then calculate the derivative of
    this at point x.
    user bubba on StackExchange:
    https://math.stackexchange.com/questions/304069/use-a-set-of-data-points-from-a-graph-to-find-a-derivative
    """
    # For high resolution data sets (i.e. thermal shifts with high sampling rate),
    # we might want to spread out the interpolation via parabola to make the code
    # run faster and remove a bit of noise.
    int_Sampling = int(np.ceil(len(temp)/100))
    #int_Sampling = 1
    #fluo = savgol_filter(fluo, 101, 3)

    lst_Derivative = []
    lst_TempFitting = []

    #temp = np.array(temp)
    #lst_TempFitting = np.array(temp+[temp[len(temp)-1]])
    #fluo = np.array(fluo+[fluo[len(fluo)-1]])

    #lst_Derivative = fluo[1:] - fluo[:-1]
    #lst_TempDifference = lst_TempFitting[1:] - lst_TempFitting[:-1]
    #for i in range(len(lst_Derivative)-1):
    #    lst_Derivative[i] = lst_Derivative[i]/lst_TempDifference[i]

    for i in range(0,len(temp),int_Sampling):
        if i > int_Sampling-1 and i < (len(temp)-int_Sampling):
            #lst_x = [temp[i-int_Sampling],temp[i],temp[i+int_Sampling]]
            #lst_y = [fluo[i-int_Sampling],fluo[i],fluo[i+int_Sampling]]
            lst_Parameters, fnord = curve_fit(eq_parabola,
                [temp[i-int_Sampling],temp[i],temp[i+int_Sampling]],
                [fluo[i-int_Sampling],fluo[i],fluo[i+int_Sampling]])
            lst_Derivative.append(2*lst_Parameters[0]*temp[i] + lst_Parameters[1])
            lst_TempFitting.append(temp[i])

    #lst_Before = []
    #lst_After = []
    #for i in range(int_Sampling):
    #    lst_Before.append(lst_Derivative[0])
    #    lst_After.append(lst_Derivative[len(lst_Derivative)-1])
    #lst_Derivative = lst_Before + lst_Derivative + lst_After

    # Apply Savitzky-Golay filter to smooth out derivative even further so that noise cannot obscure the true maximum.
    if len(lst_Derivative) > 100:
        lst_Derivative = savgol_filter(lst_Derivative, 99, 3)
    cs = scipy.interpolate.CubicSpline(lst_TempFitting, lst_Derivative)
    lst_DerivativeSpline = cs(temp)
    
    #lst_DerivativeSpline = []
    #lst_DerivativeSpline.append(lst_Derivative[0])
    #for i in range(len(lst_Derivative)):
    #    lst_DerivativeSpline.append(lst_Derivative[i])
    #lst_DerivativeSpline.append(lst_Derivative[len(lst_Derivative)-1])
    #lst_DerivativeSpline = [lst_Derivative[0]] + lst_Derivative + [lst_Derivative[len(lst_Derivative)-1]]
    #lst_DerivativeSpline = [lst_Derivative[0]] + lst_DerivativeSpline + [lst_Derivative[len(lst_Derivative)-1]]
    #lst_DerivativeSpline = [lst_Derivative[0]] + lst_DerivativeSpline + [lst_Derivative[len(lst_Derivative)-1]]

    flt_Max = np.max(lst_DerivativeSpline)
    for i in range(len(lst_DerivativeSpline)):
        if lst_DerivativeSpline[i] == flt_Max:
            flt_Tm = temp[i] # remember, we only calculate the derivative from the second to the second to last point.

    lst_ParsReturn = [lst_DerivativeSpline,0,0,0,flt_Tm+273.15,0] # add Kelvin offset since I do not want to change the other things down the line (e.g. df.draw_Tm()) until this problem is solved
    lst_OtherReturn = [0,0,0,0,0,0]

    return lst_ParsReturn, lst_OtherReturn, lst_OtherReturn, True

def fit_logMM_free(lst_Time, lst_Signal, parsonly = False):
    """
    Performs fit with logarithmic approximation of Michaelis-Menten equation.

    Arguments:
        time -> list of floats. Timepoints of reaction
        signal -> list of floats. Measured signal.
        parsonly -> boolean. If True, fit, Rsquare and success will not
                    be returned.

    Returns:
        fit -> list of floats. Fitted curve
        pars => list of floats. Values for curve's parameters.
        confidence -> list of floats. Values for 95% confidence
                      intervals for parameters.
        stderr -> list of floats. Values for standar error of fit
                  for each parameter.
        Rsquare -> R square value for curve fit.
        success -> boolean. True if a succesful fit was achieved.
    """
    lst_Time_New = []
    lst_Signal_New = []
    for i in range(len(lst_Time)):
        if lst_Time[i] <= 500:
            lst_Time_New.append(lst_Time[i])
            lst_Signal_New.append(lst_Signal[i])
    lst_Time = lst_Time_New
    lst_Signal = lst_Signal_New

    try:
        pars, covar = curve_fit(eq_logMM, lst_Time, lst_Signal)#, p0=guess)#, bounds=grenzen)
        confidence = calculate_confidence(len(lst_Time),pars,covar)
        stderr = np.sqrt(np.diagonal(covar))
        if parsonly == False:
            fit = draw_any(eq_logMM, lst_Time, pars)
            Rsquare = calculate_rsquare(lst_Signal, fit)
        success = True
    except RuntimeError:
        pars = df.set_to_nan(2)
        confidence = df.set_to_nan(2)
        stderr = df.set_to_nan(2)
        fit = df.set_to_nan(len(lst_Time))
        Rsquare = np.nan
        success = False
    
    if parsonly == False:
        return fit, pars, confidence, stderr, Rsquare, success
    else:
        return pars, confidence, stderr

def draw_rate_deriv(lst_Time, lst_Pars):
    lst_Deriv = []
    for i in range(len(lst_Time)):
        lst_Deriv.append(eq_logMM1stDerivative(lst_Time[i], *lst_Pars))
    min_der = min(lst_Deriv)
    max_der = max(lst_Deriv) - min_der
    for i in range(len(lst_Deriv)):
        lst_Deriv[i] = (lst_Deriv[i]-min_der)/max_der
    return lst_Deriv

def linear_fit(lst_Time, lst_Signal, lst_NormFitPars, int_Start, int_Stop, str_auto):

    lst_Derivative = draw_rate_deriv(lst_Time, lst_NormFitPars)
    lst_Signal_Trim = []
    lst_Time_Trim = []
    if str_auto == "auto":
        # Force change in case of bad input
        int_Start = 0
        for i in range(len(lst_Derivative)):
            if lst_Derivative[i] >= 0.7:
                lst_Time_Trim.append(lst_Time[i])
                lst_Signal_Trim.append(lst_Signal[i])
            else:
                int_Stop = i
                break
    else:
        for i in range(int_Start,int_Stop):
            lst_Time_Trim.append(lst_Time[i])
            lst_Signal_Trim.append(lst_Signal[i])
    # Need at least two datapoints to fit a line:
    if len(lst_Signal_Trim) > 2:
        pars, covar = curve_fit(eq_linear, lst_Time_Trim, lst_Signal_Trim)
        lst_Confidence = calculate_confidence(len(lst_Time),pars,covar)
        lst_STDERR = np.sqrt(np.diagonal(covar))
        lst_Time = [float(x) for x in lst_Time]
        pars = [float(x) for x in pars]
        lst_LinFit = []
        for i in range(len(lst_Time)):
            lst_LinFit.append(pars[0]*lst_Time[i] + pars[1])
        lst_LinFitTime = []
        lst_LinFit_Trimmed = []
        max_signal = max(lst_Signal)
        for i in range(len(lst_Time)):
            if lst_LinFit[i] < max_signal:
                lst_LinFitTime.append(lst_Time[i])
                lst_LinFit_Trimmed.append(lst_LinFit[i])
        return lst_LinFit_Trimmed, pars, lst_Derivative, int_Start, int_Stop, lst_Confidence, lst_STDERR, lst_LinFitTime
    else:
        return df.set_to_nan(len(lst_Time)), df.set_to_nan(2), lst_Derivative, int_Start, int_Stop, df.set_to_nan(2), df.set_to_nan(2), df.set_to_nan(len(lst_Time))

def derivative(xdata, ydata, SavGolIn, SavGolOut, minmaxboth):
    """
    Determines derivative to a given dataset.

    Arguments:
        xdata -> list of floats. Data on x axis
        ydata -> list of floats. Data on y axis
        SavGolIn -> integer. How many times to apply Savitsky-Golay
                    filter to ydata. Max is 2.
        SavGolOut -> integer. How many times to apply SavGol filter
                     once derivative is calculated.
    """

    lst_Derivative = []
    lst_XFitting = []

    xdata = np.array(xdata)
    lst_XFitting = np.array(xdata+[xdata[len(xdata)-1]])
    ydata = np.array(ydata+[ydata[len(ydata)-1]])
    if SavGolIn > 0:
        ydata = savgol_filter(ydata, 31, 3)
        if SavGolIn > 1:
            ydata = savgol_filter(ydata, 31, 3)

    derivative = ydata[1:] - ydata[:-1]
    lst_XDifference = lst_XFitting[1:] - lst_XFitting[:-1]
    for i in range(len(derivative)-1):
        derivative[i] = derivative[i]/lst_XDifference[i]
    if SavGolOut > 0:
        derivative = savgol_filter(derivative,11,3)
        if SavGolOut > 1:
            derivative = savgol_filter(derivative,21,3)

    if minmaxboth == "max":
        flt_Extreme = np.nanmax(derivative[10:-10])
    if minmaxboth == "min":
        flt_Extreme = np.nanmin(derivative[10:-10])
    elif minmaxboth == "both":
        # Set further back for both. Both is used for nanoDSF.
        max = np.nanmax(derivative[20:-20])
        min = np.nanmin(derivative[20:-20])
        if abs(max) > abs(min):
            flt_Extreme = max
        else:
            flt_Extreme = min
    lst_Inflections = []
    lst_Slopes = []
    for i in range(len(derivative)):
        if derivative[i] == flt_Extreme:
            lst_Inflections.append(xdata[i]) # remember, we only calculate the derivative from the second to the second to last point.
            lst_Slopes.append(derivative[i])

    return derivative.tolist(), lst_Inflections, lst_Slopes





