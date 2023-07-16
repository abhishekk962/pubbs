import pandas as pd
import numpy as np
import yaml
from yaml.loader import SafeLoader
import gc

from Cost_fn_submodules import dwell_time,wcost



def main():
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.precision', 2)



    with open('parameters.yml') as f:
        data = yaml.load(f, Loader=SafeLoader)

    globals().update(data)

    dob= seatcap*min_c_lvl
    cob= int (seatcap*max_c_lvl)

if __name__ == "__main__":
    main()


def cost_holding(h_bus_in,direc,delayed_bus_in,purpose):
    h_bus=h_bus_in.copy()
    delayed_bus=delayed_bus_in.copy()
    if direc == 'DN':
        distance = pd.read_csv(r'Function files\Input files\distanceDN.csv').set_index('Distance')

        link_travel_tr= pd.read_csv(r'Function files\Input_files_holding\link_travel_trDN.csv')
        arrivalrate_tr= pd.read_csv(r'Function files\Input_files_holding\arrivalrate_trDN.csv')
        alightrate_tr= pd.read_csv(r'Function files\Input_files_holding\alightrate_trDN.csv')

        headway1= pd.read_csv(r'Function files\Input_files_holding\HeadwayDN.csv')
        departuretime= pd.read_csv(r'Function files\Input_files_holding\departuretimeDN.csv')

        p_arrival= pd.read_csv(r'Function files\Input_files_holding\p_arrivalDN.csv')
        p_waiting= pd.read_csv(r'Function files\Input_files_holding\p_waitingDN.csv')
        p_alight= pd.read_csv(r'Function files\Input_files_holding\p_alightDN.csv')
        p_board= pd.read_csv(r'Function files\Input_files_holding\p_boardDN.csv')
        link_occp= pd.read_csv(r'Function files\Input_files_holding\link_occpDN.csv')
        waitingtime_tr= pd.read_csv(r'Function files\Input_files_holding\waitingtimeDN.csv')
        cost_waitingtime= pd.read_csv(r'Function files\Input_files_holding\cost_waitingtimeDN.csv')
        p_cantboard= pd.read_csv(r'Function files\Input_files_holding\p_cantboardDN.csv')
        p_lost= pd.read_csv(r'Function files\Input_files_holding\ p_lostDN.csv')
        d_time= pd.read_csv(r'Function files\Input_files_holding\d_timeDN.csv')
        stoparrival= pd.read_csv(r'Function files\Input_files_holding\stoparrivalDN.csv')
        headway= pd.read_csv(r'Function files\Input_files_holding\headway_StopDN.csv')
        traveltime= pd.read_csv(r'Function files\Input_files_holding\traveltimeDN.csv')
        load_fact= pd.read_csv(r'Function files\Input_files_holding\load_factDN.csv')
        invehtime= pd.read_csv(r'Function files\Input_files_holding\invehtimeDN.csv')
        cost_inveh= pd.read_csv(r'Function files\Input_files_holding\cost_invehDN.csv')
        p_sit= pd.read_csv(r'Function files\Input_files_holding\p_sitDN.csv')
        p_stand= pd.read_csv(r'Function files\Input_files_holding\ p_standDN.csv')
        revenue= pd.read_csv(r'Function files\Input_files_holding\revenueDN.csv')
        p_cantboard_1= pd.read_csv(r'Function files\Input_files_holding\ p_cantboard_1DN.csv')
        p_cantboard_2= pd.read_csv(r'Function files\Input_files_holding\p_cantboard_2DN.csv')
        p_cantboard_0= pd.read_csv(r'Function files\Input_files_holding\p_cantboard_0DN.csv')
        despatch= pd.read_csv(r'Function files\Input_files_holding\despatchDN.csv')



    else:
        distance = pd.read_csv(r'Function files\Input files\distanceUP.csv').set_index('Distance')

        link_travel_tr= pd.read_csv(r'Function files\Input_files_holding\link_travel_trUP.csv')
        arrivalrate_tr= pd.read_csv(r'Function files\Input_files_holding\arrivalrate_trUP.csv')
        alightrate_tr= pd.read_csv(r'Function files\Input_files_holding\alightrate_trUP.csv')

        headway1= pd.read_csv(r'Function files\Input_files_holding\HeadwayUP.csv')
        departuretime= pd.read_csv(r'Function files\Input_files_holding\departuretimeUP.csv')

        p_arrival= pd.read_csv(r'Function files\Input_files_holding\p_arrivalUP.csv')
        p_waiting= pd.read_csv(r'Function files\Input_files_holding\p_waitingUP.csv')
        p_alight= pd.read_csv(r'Function files\Input_files_holding\p_alightUP.csv')
        p_board= pd.read_csv(r'Function files\Input_files_holding\p_boardUP.csv')
        link_occp= pd.read_csv(r'Function files\Input_files_holding\link_occpUP.csv')
        waitingtime_tr= pd.read_csv(r'Function files\Input_files_holding\waitingtimeUP.csv')
        cost_waitingtime= pd.read_csv(r'Function files\Input_files_holding\cost_waitingtimeUP.csv')
        p_cantboard= pd.read_csv(r'Function files\Input_files_holding\p_cantboardUP.csv')
        p_lost= pd.read_csv(r'Function files\Input_files_holding\ p_lostUP.csv')
        d_time= pd.read_csv(r'Function files\Input_files_holding\d_timeUP.csv')
        stoparrival= pd.read_csv(r'Function files\Input_files_holding\stoparrivalUP.csv')
        headway= pd.read_csv(r'Function files\Input_files_holding\headway_StopUP.csv')
        traveltime= pd.read_csv(r'Function files\Input_files_holding\traveltimeUP.csv')
        load_fact= pd.read_csv(r'Function files\Input_files_holding\load_factUP.csv')
        invehtime= pd.read_csv(r'Function files\Input_files_holding\invehtimeUP.csv')
        cost_inveh= pd.read_csv(r'Function files\Input_files_holding\cost_invehUP.csv')
        p_sit= pd.read_csv(r'Function files\Input_files_holding\p_sitUP.csv')
        p_stand= pd.read_csv(r'Function files\Input_files_holding\ p_standUP.csv')
        revenue= pd.read_csv(r'Function files\Input_files_holding\revenueUP.csv')
        p_cantboard_1= pd.read_csv(r'Function files\Input_files_holding\ p_cantboard_1UP.csv')
        p_cantboard_2= pd.read_csv(r'Function files\Input_files_holding\p_cantboard_2UP.csv')
        p_cantboard_0= pd.read_csv(r'Function files\Input_files_holding\p_cantboard_0UP.csv')
        despatch= pd.read_csv(r'Function files\Input_files_holding\despatchUP.csv')

    tot_dis = distance.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
    tot_dis = np.ceil(float(np.asarray(tot_dis)))

    # FIXED COST  DIRECTION per trip

    fuelcostrunning = (fuelprice * tot_dis / kmperliter).round(-2).round(0)
    maintenancecost = (tot_dis * busmaintenance).round(0)
    vehdepreciation = ((buscost / buslifecycle) * tot_dis).round(0)
    crewcost = (crewperbus * creqincome / (2 * cr_trip * cr_day))

    #Stop arrival

    trip_no= delayed_bus[0]
    stop_no= delayed_bus[1]

    stoparrival.iloc[trip_no,stop_no]= delayed_bus[3]

    delayed_bus[3]=0
    h_bus.loc[len(h_bus.index)] = delayed_bus
    h_bus = h_bus.sort_values(by=['trip_no']).reset_index(drop=True)



    # Calculation of passenger arrival, number of boarding, number alighting, link occupancy, dwell time,passenger lost, passenger cannot board, waiting time, in vehicle travel time etc.
    # trip wise calculation for each stop


    for ind in range(0, len(departuretime.index)):
        for j in range(0, len(alightrate_tr.columns)):
            if ind< h_bus.loc[0, 'trip_no']:
                pass
            else:
                #calculating stop arrival time for buses on route after the control point
                if ind>= h_bus.loc[0, 'trip_no'] and ind <= h_bus.loc[len(h_bus.index)-1, 'trip_no']:
                    for k in range(0, len(h_bus.index)):
                        if ind == h_bus.loc[k, 'trip_no'] and j >= h_bus.loc[k, 'ctrl_stops']:
                            if ind == h_bus.loc[k, 'trip_no'] and j > h_bus.loc[k, 'ctrl_stops']:
                                # TRAVEL TIME FROM STOP J-1 TO J = DWELL TIME AT STOP J-1 + LINK RUNNING TIME (J-1,J)
                                traveltime.iloc[ind, j] = ((d_time.iloc[ind, j - 1] + link_travel_tr.iloc[ind, j]) / 60).round(4)
                                stoparrival.iloc[ind, j] = stoparrival.iloc[ind, j - 1] + traveltime.iloc[ind, j]
                                break
                            else:
                                pass
                            break
                        else:
                            pass


                else:
                    if j == 0:
                        traveltime.iloc[ind, j] = 0
                        stoparrival.iloc[ind, j] = departuretime.iloc[ind, 0]

                    else:
                        # TRAVEL TIME FROM STOP J-1 TO J = DWELL TIME AT STOP J-1 + LINK RUNNING TIME (J-1,J)
                        traveltime.iloc[ind, j] = ((d_time.iloc[ind, j - 1] + link_travel_tr.iloc[ind, j]) / 60).round(4)
                        stoparrival.iloc[ind, j] = stoparrival.iloc[ind, j - 1] + traveltime.iloc[ind, j]

                #----------------------------------------------------------------
                # Headway Calculations of stop j --------------------------------------------------------------

                if j == 0 or ind == 0:

                    headway.iloc[ind, j] = headway1.iloc[ind, 0]
                    #  headway1 = Headway at the departure
                    # headway= stopwise headway
                else:
                    headway.iloc[ind, j] = abs(stoparrival.iloc[ind, j] - stoparrival.iloc[ind - 1, j]) * 60

                # Passenger lost due to minimum waiting time ---------------------------------------------------------
                if bus_left == 1:
                    p_lost_waiting = 0
                elif bus_left == 2:
                    if ind == 0:
                        p_cantboard_1.iloc[ind, j] = 0
                        p_lost_waiting = 0
                    else:
                        p_cantboard_1.iloc[ind, j] = p_cantboard.iloc[ind - 1, j]
                        if stoparrival.iloc[ind, j] - stoparrival.iloc[ind - 1, j] > max_wait:
                            p_lost_waiting = p_cantboard_1.iloc[ind, j]
                            p_cantboard_1.iloc[ind, j] = 0
                        else:
                            p_lost_waiting = 0
                else:
                    if ind == 0:
                        p_cantboard_1.iloc[ind, j] = 0
                        p_cantboard_2.iloc[ind, j] = 0
                    else:
                        p_cantboard_2.iloc[ind, j] = p_cantboard_1.iloc[ind - 1, j]
                        p_cantboard_1.iloc[ind, j] = p_cantboard_0.iloc[ind - 1, j]

                    # waitting time check

                    if ind == 0:
                        p_lost_waiting = 0
                    elif ind == 1:
                        if stoparrival.iloc[ind, j] - stoparrival.iloc[ind - 1, j] > max_wait:
                            p_lost_waiting = p_cantboard_1.iloc[ind, j]
                            p_cantboard_1.iloc[ind, j] = 0
                        else:
                            p_lost_waiting = 0
                    else:
                        if stoparrival.iloc[ind, j] - stoparrival.iloc[ind - 1, j] > max_wait:
                            p_lost_waiting = p_cantboard_2.iloc[ind, j] + p_cantboard_1.iloc[ind, j]
                            p_cantboard_1.iloc[ind, j] = 0
                            p_cantboard_2.iloc[ind, j] = 0
                        elif stoparrival.iloc[ind, j] - stoparrival.iloc[ind - 2, j] > max_wait:
                            p_lost_waiting = p_cantboard_2.iloc[ind, j]
                            p_cantboard_2.iloc[ind, j] = 0
                        else:
                            p_lost_waiting = 0

                # Passenger arrival and passenger waiting------------------------------------------------

                p_arrival.iloc[ind, j] = np.ceil(arrivalrate_tr.iloc[ind, j] * headway.iloc[ind, j])

                # waiting time and cost calculation------------------------------------------------------------
                if bus_left == 1:
                    waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j])
                    waitingtime_0 = 0.5 * headway.iloc[ind, j]
                    cw_cost = wcost(waitingtime_0, c_waittime)
                    cost_waitingtime.iloc[ind, j] = np.ceil(waitingtime_tr.iloc[ind, j] * cw_cost)
                elif bus_left == 2:
                    if ind == 0:
                        waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j])
                        waitingtime_0 = 0.5 * headway.iloc[ind, j]
                        cw_cost = wcost(waitingtime_0, c_waittime)
                        cost_waitingtime.iloc[ind, j] = np.ceil(waitingtime_tr.iloc[ind, j] * cw_cost)
                    else:
                        waitingtime_0 = 0.5 * headway.iloc[ind, j]
                        waitingtime_1 = 0.5 * headway.iloc[ind - 1, j] + headway.iloc[ind, j]
                        waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j]) + (p_cantboard.iloc[ind - 1, j] * headway.iloc[ind, j])
                        cost_waitingtime.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_0, c_waittime)) + (p_cantboard_1.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_1, c_waittime))
                else:
                    if ind == 0:
                        waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j])
                        waitingtime_0 = 0.5 * headway.iloc[ind, j]
                        cw_cost = wcost(waitingtime_0, c_waittime)
                        cost_waitingtime.iloc[ind, j] = np.ceil(waitingtime_tr.iloc[ind, j] * cw_cost)
                    elif ind == 1:
                        waitingtime_0 = 0.5 * headway.iloc[ind, j]
                        waitingtime_1 = 0.5 * headway.iloc[ind - 1, j] + headway.iloc[ind, j]
                        waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j]) + (p_cantboard.iloc[ind - 1, j] * headway.iloc[ind, j])
                        cost_waitingtime.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_0, c_waittime)) + (p_cantboard_1.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_1, c_waittime))

                    else:
                        waitingtime_0 = 0.5 * headway.iloc[ind, j]
                        waitingtime_1 = 0.5 * headway.iloc[ind - 1, j] + headway.iloc[ind, j]
                        waitingtime_2 = 0.5 * headway.iloc[ind - 2, j] + headway.iloc[ind - 1, j] + headway.iloc[ind, j]

                        waitingtime_tr.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j]) + (p_cantboard.iloc[ind - 1, j] * headway.iloc[ind, j])
                        cost_waitingtime.iloc[ind, j] = 0.5 * (p_arrival.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_0, c_waittime)) + (p_cantboard_1.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_1, c_waittime)) + (
                                p_cantboard_2.iloc[ind, j] * headway.iloc[ind, j] * wcost(waitingtime_2, c_waittime))

                #  link occupancy of bus(ind) at stop j (Passenger on board j-1 to j)------------------------

                if j == 0:
                    # on_board passenger
                    link_occp.iloc[ind, j] = 0

                else:
                    x = p_board.iloc[[ind], 0:j].sum(axis=1, skipna=True).values
                    y = p_alight.iloc[[ind], 0:j].sum(axis=1, skipna=True).values
                    x = x[0]  # total passenger boarded till j-1
                    y = y[0]  # total passenger alighted till j-1
                    # on_board passenger for link j-1 to j
                    link_occp.iloc[ind, j] = x - y

                load_fact.iloc[ind, j] = (link_occp.iloc[ind, j] / seatcap)

                # number passengers sitting and standing for jth link (stop j-1 to  stop j)----------

                if link_occp.iloc[ind, j] <= seatcap:
                    p_sit.iloc[ind, j] = link_occp.iloc[ind, j]
                    p_stand.iloc[ind, j] = 0
                else:
                    p_sit.iloc[ind, j] = seatcap
                    p_stand.iloc[ind, j] = link_occp.iloc[ind, j] - p_sit.iloc[ind, j]

                # Invehicle time of bus(ind) at stop j--------------------------------------------

                invehtime.iloc[ind, j] = link_occp.iloc[ind, j] * traveltime.iloc[ind, j]

                if load_fact.iloc[ind, j] <= 1:
                    cost_inveh.iloc[ind, j] = p_sit.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .35)
                elif load_fact.iloc[ind, j] > 1 and load_fact.iloc[ind, j] <= 1.25:
                    cost_inveh.iloc[ind, j] = (p_sit.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .35)) + (p_stand.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .3))

                elif load_fact.iloc[ind, j] > 1.25 and load_fact.iloc[ind, j] <= 1.5:
                    cost_inveh.iloc[ind, j] = (p_sit.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .35)) + (p_stand.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .2))

                elif load_fact.iloc[ind, j] > 1.5 and load_fact.iloc[ind, j] < 1.75:
                    cost_inveh.iloc[ind, j] = (p_sit.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .35)) + (p_stand.iloc[ind, j] * traveltime.iloc[ind, j] * 60 * (c_invehtime - .1))

                else:
                    cost_inveh.iloc[ind, j] = (link_occp.iloc[ind, j] * traveltime.iloc[ind, j] * c_invehtime)

                # Passenger boarding , alighting, passenger cannot board and passenger lost due to overcrowding------------------------------------------------

                p_alight.iloc[ind, j] = np.ceil(link_occp.iloc[ind, j] * alightrate_tr.iloc[ind, j])
                residual = cob - link_occp.iloc[ind, j] + p_alight.iloc[ind, j]

                if bus_left == 1:
                    if p_arrival.iloc[ind, j] <= residual:
                        p_board.iloc[ind, j] = p_arrival.iloc[ind, j]
                    else:
                        p_board.iloc[ind, j] = residual

                    # Passenger lost at stop j due to overcrowding
                    p_lost_boarding = p_arrival.iloc[ind, j] - p_board.iloc[ind, j]
                    # passenger Cant board bus (ind) at stop j
                    p_cantboard.iloc[ind, j] = 0
                elif bus_left == 2:
                    if p_cantboard_1.iloc[ind, j] <= residual:
                        p_board_1 = p_cantboard_1.iloc[ind, j]
                        residual = residual - p_board_1
                        if p_arrival.iloc[ind, j] <= residual:
                            p_board_0 = p_arrival.iloc[ind, j]
                        else:
                            p_board_0 = residual
                    else:
                        p_board_1 = residual
                        p_board_0 = 0

                    p_cantboard_0.iloc[ind, j] = p_arrival.iloc[ind, j] - p_board_0
                    p_cantboard_1.iloc[ind, j] = p_cantboard_1.iloc[ind, j] - p_board_1

                    p_board.iloc[ind, j] = p_board_0 + p_board_1
                    # passenger Cant board bus (ind) at stop j------------------------
                    p_cantboard.iloc[ind, j] = p_cantboard_0.iloc[ind, j]
                    # Passenger lost at stop j due to overcrowding -----------------
                    p_lost_boarding = p_cantboard_1.iloc[ind, j]

                else:
                    if p_cantboard_2.iloc[ind, j] <= residual:
                        p_board_2 = p_cantboard_2.iloc[ind, j]
                        residual = residual - p_board_2
                        if p_cantboard_1.iloc[ind, j] <= residual:
                            p_board_1 = p_cantboard_1.iloc[ind, j]
                            residual = residual - p_board_1
                            if p_arrival.iloc[ind, j] <= residual:
                                p_board_0 = p_arrival.iloc[ind, j]
                            else:
                                p_board_0 = residual
                        else:
                            p_board_1 = residual
                            p_board_0 = 0
                    else:
                        p_board_2 = residual
                        p_board_1 = 0
                        p_board_0 = 0

                    p_cantboard_0.iloc[ind, j] = p_arrival.iloc[ind, j] - p_board_0
                    p_cantboard_1.iloc[ind, j] = p_cantboard_1.iloc[ind, j] - p_board_1
                    p_cantboard_2.iloc[ind, j] = p_cantboard_2.iloc[ind, j] - p_board_2

                    p_board.iloc[ind, j] = p_board_0 + p_board_1 + p_board_2
                    # passenger Cant board bus (ind) at stop j------------------------------------------------------------------------
                    p_cantboard.iloc[ind, j] = p_cantboard_0.iloc[ind, j] + p_cantboard_1.iloc[ind, j]
                    # Passenger lost at stop j due to overcrowding -----------------------------------------------------------------------
                    p_lost_boarding = p_cantboard_2.iloc[ind, j]

                # Total passenger lost
                p_lost.iloc[ind, j] = p_lost_waiting + p_lost_boarding

                # Dwelling time of bus(ind) at stop j------------------------------------------------
                d_time.iloc[ind, j] = dwell_time(j, departuretime.iloc[ind, 0], p_board.iloc[ind, j], p_alight.iloc[ind, j], load_fact.iloc[ind, j])



                # holding---------------------------------------------------------------------------

                if stoparrival.iloc[ind, j]+d_time.iloc[ind, j]/60 <  despatch.iloc[ind, j]:
                    default_holding=  (despatch.iloc[ind, j]- d_time.iloc[ind, j]/60-stoparrival.iloc[ind, j])*60
                else:
                    default_holding=0
                if ind>= h_bus.loc[0, 'trip_no'] and ind <= h_bus.loc[len(h_bus.index)-1, 'trip_no']:
                    for k in range(0, len(h_bus.index)):
                        if ind == h_bus.loc[k, 'trip_no'] and j == h_bus.loc[k, 'ctrl_stops']:
                            dyn_holding = h_bus.loc[k, 'holding']
                            break
                        else:
                            dyn_holding=0
                else:
                    dyn_holding=0

                d_time.iloc[ind, j]= d_time.iloc[ind, j]+default_holding+ dyn_holding

                # Despatch time at stop j for bus ind ------------------------------------------------------------------------
                despatch.iloc[ind, j] = stoparrival.iloc[ind, j] + (d_time.iloc[ind, j]/60).round(2)

                # No overtaking ------------------------------------------------------------------------


                if ind == 0 or j==len(alightrate_tr.columns)-1:
                    d_holding = 0
                else:

                    headway_temp=(despatch.iloc[ind,j]-despatch.iloc[ind-1,j])*60
                    #if headway is less than 0 i.e the bus ind+1 is overtaking
                    if headway_temp <= 0:

                        d_holding= abs(headway_temp)
                        d_time.iloc[ind, j]=d_time.iloc[ind, j]+ d_holding
                        despatch.iloc[ind, j] = despatch.iloc[ind, j]+ d_holding/60
                        link_travel_tr.iloc[ind, j + 1]= link_travel_tr.iloc[ind-1, j + 1]
                    else:
                        d_holding = 0

                # ---------------------------------------------------------------------



    # Calculation of total cost
    # tripwise total waiting time cost
    Tot_trcost_waiting = cost_waitingtime.sum(axis=1)

    # tripwise total in vehicle travel time cost
    Tot_trcost_inveh = cost_inveh.sum(axis=1)

    # tripwise total passenger lost
    Tot_trpasslost = p_lost.sum(axis=1)

    # tripwise total dwelling time
    Tot_d_time = d_time.sum(axis=1)

    fuelcostdwelling = Tot_d_time * (fuelprice / 60 * kmperliter2)

    # FIXED COST CALCULATION FOR EACH TRIP
    fixed_cost = fuelcostdwelling.copy()
    for i in range(0, len(fuelcostdwelling.index)):
        fixed_cost.iloc[i] = fuelcostdwelling.iloc[i] + fuelcostrunning + maintenancecost + vehdepreciation + crewcost

    Tot_cost = Tot_trcost_waiting + Tot_trcost_inveh + (
            Tot_trpasslost * (penalty + c_cantboard)) + fixed_cost


    # TOTAL COST
    t_cost = int(Tot_cost.sum())

    if purpose =='GA':
        return (t_cost)
    elif purpose =='Optimised holding':

        #Export files
        if direc == 'DN':

            p_arrival .to_csv(r'Function files\Input_files_holding\p_arrivalDN.csv',index=False)
            p_waiting .to_csv(r'Function files\Input_files_holding\p_waitingDN.csv' ,index=False)
            p_alight .to_csv(r'Function files\Input_files_holding\p_alightDN.csv' ,index=False)
            p_board .to_csv(r'Function files\Input_files_holding\p_boardDN.csv',index=False)
            link_occp .to_csv(r'Function files\Input_files_holding\ link_occpDN.csv',index=False)
            waitingtime_tr .to_csv(r'Function files\Input_files_holding\waitingtimeDN.csv' ,index=False)
            cost_waitingtime .to_csv(r'Function files\Input_files_holding\cost_waitingtimeDN.csv' ,index=False)
            p_cantboard .to_csv(r'Function files\Input_files_holding\p_cantboardDN.csv' ,index=False)
            p_lost .to_csv(r'Function files\Input_files_holding\ p_lostDN.csv' ,index=False)
            d_time .to_csv(r'Function files\Input_files_holding\d_timeDN.csv' ,index=False)
            stoparrival .to_csv(r'Function files\Input_files_holding\stoparrivalDN.csv' ,index=False)
            headway .to_csv(r'Function files\Input_files_holding\headway_StopDN.csv' ,index=False)
            traveltime .to_csv(r'Function files\Input_files_holding\traveltimeDN.csv' ,index=False)
            load_fact .to_csv(r'Function files\Input_files_holding\load_factDN.csv' ,index=False)
            invehtime .to_csv(r'Function files\Input_files_holding\invehtimeDN.csv' ,index=False)
            cost_inveh .to_csv(r'Function files\Input_files_holding\cost_invehDN.csv' ,index=False)
            p_sit .to_csv(r'Function files\Input_files_holding\p_sitDN.csv' ,index=False)
            p_stand .to_csv(r'Function files\Input_files_holding\ p_standDN.csv' ,index=False)
            revenue .to_csv(r'Function files\Input_files_holding\revenueDN.csv' ,index=False)
            p_cantboard_1 .to_csv(r'Function files\Input_files_holding\ p_cantboard_1DN.csv' ,index=False)
            p_cantboard_2 .to_csv(r'Function files\Input_files_holding\p_cantboard_2DN.csv' ,index=False)
            p_cantboard_0 .to_csv(r'Function files\Input_files_holding\p_cantboard_0DN.csv' ,index=False)
            despatch .to_csv(r'Function files\Input_files_holding\despatchDN.csv' ,index=False)



        else:

            p_arrival .to_csv(r'Function files\Input_files_holding\p_arrivalUP.csv' ,index=False)
            p_waiting .to_csv(r'Function files\Input_files_holding\p_waitingUP.csv' ,index=False)
            p_alight .to_csv(r'Function files\Input_files_holding\p_alightUP.csv' ,index=False)
            p_board .to_csv(r'Function files\Input_files_holding\p_boardUP.csv' ,index=False)
            link_occp .to_csv(r'Function files\Input_files_holding\link_occpUP.csv' ,index=False)
            waitingtime_tr .to_csv(r'Function files\Input_files_holding\waitingtimeUP.csv' ,index=False)
            cost_waitingtime .to_csv(r'Function files\Input_files_holding\cost_waitingtimeUP.csv' ,index=False)
            p_cantboard .to_csv(r'Function files\Input_files_holding\p_cantboardUP.csv' ,index=False)
            p_lost .to_csv(r'Function files\Input_files_holding\ p_lostUP.csv' ,index=False)
            d_time .to_csv(r'Function files\Input_files_holding\d_timeUP.csv' ,index=False)
            stoparrival .to_csv(r'Function files\Input_files_holding\stoparrivalUP.csv' ,index=False)
            headway .to_csv(r'Function files\Input_files_holding\headway_StopUP.csv' ,index=False)
            traveltime .to_csv(r'Function files\Input_files_holding\traveltimeUP.csv' ,index=False)
            load_fact .to_csv(r'Function files\Input_files_holding\load_factUP.csv' ,index=False)
            invehtime .to_csv(r'Function files\Input_files_holding\invehtimeUP.csv' ,index=False)
            cost_inveh .to_csv(r'Function files\Input_files_holding\cost_invehUP.csv' ,index=False)
            p_sit .to_csv(r'Function files\Input_files_holding\p_sitUP.csv' ,index=False)
            p_stand .to_csv(r'Function files\Input_files_holding\ p_standUP.csv' ,index=False)
            revenue .to_csv(r'Function files\Input_files_holding\revenueUP.csv' ,index=False)
            p_cantboard_1 .to_csv(r'Function files\Input_files_holding\ p_cantboard_1UP.csv' ,index=False)
            p_cantboard_2 .to_csv(r'Function files\Input_files_holding\p_cantboard_2UP.csv' ,index=False)
            p_cantboard_0 .to_csv(r'Function files\Input_files_holding\p_cantboard_0UP.csv' ,index=False)
            despatch .to_csv(r'Function files\Input_files_holding\despatchUP.csv' ,index=False)

        return(despatch,stoparrival,t_cost)
    else:
        return (despatch, stoparrival,t_cost)


