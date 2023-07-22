import pandas as pd
import numpy as np




def freq_range(passengerarrivalDN,alightrateDN,distanceDN,cob,dob,hrinperiod,frequencydefault):
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


    L_DN = distanceDN.sum(axis=1, skipna=True).values

    L_DN = np.ceil(float(np.asarray(L_DN)))

    max_pass_periodDN = link_occup.max(axis=1, skipna=False)




    freq_min= np.ceil(max_pass_periodDN/cob)
    freq_max= np.ceil(max_pass_periodDN/(dob))

    freqset=pd.DataFrame()



    return(freq_min,freq_max)
















