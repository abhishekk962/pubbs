import pandas as pd
import numpy as np
import yaml
from yaml.loader import SafeLoader

def main():
    with open('parameters.yml') as f:
        data = yaml.load(f, Loader=SafeLoader)

    globals().update(data)

    dob= seatcap*min_c_lvl
    cob= int (seatcap*max_c_lvl)
    
    #Dwell time calculations
    stop_characteristics=pd.read_csv(r'Function files\Input files\stop wise data.csv')
    d_coef= pd.read_csv(r'Function files\Input files\stop  OLS coefficient.csv').set_index('Attributes')

if __name__ == "__main__":
    main()


def dwell_time (j ,deptime,boarding,alighting,link_occup):
    if j == 0 or j == len(stop_characteristics.index) - 1:
        dwellingtime = 0
    else:
        if deptime >= 8 or deptime > 11:
            dwellingtime = stop_characteristics.loc[j, 'Before Intersection'] * d_coef.loc[
                'Coef', 'Before Intersection'] + \
                           stop_characteristics.loc[j, 'Far from Intersection'] * d_coef.loc[
                               'Coef', 'Far from Intersection'] + \
                           stop_characteristics.loc[j, 'Commercial (sqm)'] * d_coef.loc['Coef', 'Commercial (sqm)'] + \
                           stop_characteristics.loc[j, 'Transport hub (sqm)'] * d_coef.loc[
                               'Coef', 'Transport hub (sqm)'] + \
                           stop_characteristics.loc[j, 'Bus Bay'] * d_coef.loc['Coef', 'Bus Bay']
            dwellingtime = dwellingtime + d_coef.loc['Coef', 'Const'] + (
                    boarding * d_coef.loc['Coef', 'No. of Boarding']) + (
                                   alighting * d_coef.loc['Coef', 'No. of Alighting']) + (
                                   link_occup * d_coef.loc['Coef', 'Occupancy Level'])
            dwellingtime1 = ((dwellingtime + d_coef.loc['Coef', 'Morning Peak']) / 60).round(3)

        else:
            dwellingtime = stop_characteristics.loc[j, 'Before Intersection'] * d_coef.loc[
                'Coef', 'Before Intersection'] + \
                           stop_characteristics.loc[j, 'Far from Intersection'] * d_coef.loc[
                               'Coef', 'Far from Intersection'] + \
                           stop_characteristics.loc[j, 'Commercial (sqm)'] * d_coef.loc['Coef', 'Commercial (sqm)'] + \
                           stop_characteristics.loc[j, 'Transport hub (sqm)'] * d_coef.loc[
                               'Coef', 'Transport hub (sqm)'] + \
                           stop_characteristics.loc[j, 'Bus Bay'] * d_coef.loc['Coef', 'Bus Bay']
            dwellingtime = dwellingtime + d_coef.loc['Coef', 'Const'] + (
                    boarding * d_coef.loc['Coef', 'No. of Boarding']) + (
                                   alighting * d_coef.loc['Coef', 'No. of Alighting']) + (
                                   link_occup * d_coef.loc['Coef', 'Occupancy Level'])
            dwellingtime1 = (dwellingtime / 60).round(3)

        if dwellingtime1 >= min_dwell/60:
            dwellingtime= dwellingtime1
        else:
            dwellingtime = min_dwell/60

    return (dwellingtime)

#waiting time variable cost calculations
def wcost(headway, costunit_waitingtime):
    if headway  <= 10:
        cw_cost = costunit_waitingtime * (1)
    elif headway <= 15:
        cw_cost = costunit_waitingtime * (1 + 0.05 * 0.05)
    elif headway<= 20:
        cw_cost = costunit_waitingtime * (1 + 0.1 * 0.1)
    elif headway  <= 25:
        cw_cost = costunit_waitingtime * (1 + 0.15 * 0.15)
    else:
        cw_cost= costunit_waitingtime * (1 + 0.20 * 0.20)

    return (cw_cost)


