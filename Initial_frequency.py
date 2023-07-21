import pandas as pd
import numpy as np

import yaml
from yaml.loader import SafeLoader

pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.precision', 2)



def ini_freq(passengerarrivalDN,alightrateDN,distanceDN,cob,dob,hrinperiod,frequencydefault,direction):
    link_occup = pd.DataFrame(index=passengerarrivalDN.index, columns=passengerarrivalDN.columns)
    pass_alightingDN = pd.DataFrame(index=passengerarrivalDN.index, columns=passengerarrivalDN.columns)
    # ------------------------------------------------------------
    # passenger load
    # ---------------------------------------------------------------
    for i in range(0, len(passengerarrivalDN.index)):
        for j in range(0, len(passengerarrivalDN.columns)):
            if j == 0:
                link_occup.iloc[i, j] = 0
                pass_alightingDN.iloc[i, j] = 0
            else:
                x = passengerarrivalDN.iloc[[i], 0:j].sum(axis=1,
                                                          skipna=True).values  # total boarding till stop j-1
                y = pass_alightingDN.iloc[[i], 0:j].sum(axis=1, skipna=True).values
                x = x[0]
                y = y[0]
                link_occup.iloc[i, j] = x - y
                pass_alightingDN.iloc[i, j] = np.ceil(
                    link_occup.iloc[i, j] * alightrateDN.iloc[i, j])

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    # Point check
    # -------------------------------------------------------------------------------------------------------------------------------------------------------

    L_DN = distanceDN.sum(axis=1, skipna=True).values

    L_DN = np.ceil(float(np.asarray(L_DN)))

    max_pass_periodDN = link_occup.max(axis=1, skipna=False)

    freqDN1 = (np.ceil(max_pass_periodDN / (cob * hrinperiod)))

    freqDN1[freqDN1 < frequencydefault] = frequencydefault

    headwayDN1 = (1 / freqDN1) * 60
    infreqDN1 = pd.DataFrame({'Time Period': freqDN1.index, 'Initial Frequency': freqDN1.values,
                              'Initial Headway': headwayDN1.values}).set_index('Time Period')

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    # 1.1.2 FREQUENCY CALCULATION 2  (based on load profile across stops)  DOWN DIRECTION
    # -------------------------------------------------------------------------------------------------------------------------------------------------------

    passengerkilometerDN = link_occup.mul(distanceDN.values, axis=1)

    asasDN = np.ceil(passengerkilometerDN.sum(axis=1, skipna=True))

    passkmDN = passengerkilometerDN / (dob * L_DN * hrinperiod)
    passkmDN = np.ceil(passkmDN.sum(axis=1, skipna=True))

    maxcapDN = max_pass_periodDN / (cob * hrinperiod)
    maxcapDN = np.ceil(maxcapDN)

    freqDN_ride = pd.DataFrame(
        {'Time Period': freqDN1.index, 'passenger kilometer': passkmDN.values, 'Maximum Capacity': maxcapDN,
         'Default Frequency': frequencydefault}).set_index('Time Period')

    freqDN2 = freqDN_ride.max(axis=1, skipna=False)

    headwayDN2 = (1 / freqDN2) * (60)
    infreqDN2 = pd.DataFrame({'Time Period': freqDN2.index, 'Initial Frequency2': freqDN2.values,
                              'Initial Headway2': headwayDN2.values}).set_index('Time Period')

    print(f'\n----------------------------------------------------------------------------\n'
          f'Frequency and Headway determined by Ride Check Method in is :',direction,
          f'\n----------------------------------------------------------------------------\n', infreqDN2)  # FINAL PRINT

    return(freqDN2)

#-------------------------------------------------------------------------------









