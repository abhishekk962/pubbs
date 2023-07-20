# import csv
# import numpy as np
# import time
# import datetime
# import io
# from flask_session import Session
import yaml
from io import BytesIO, StringIO
import base64
import pymysqlpool
import pymysql
import secrets
import pandas as pd
import numpy as np
import numpy
from flask import Flask, render_template, make_response,request, Response, session, redirect, jsonify,url_for,send_file
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from datetime import datetime
import utm
import geopy.distance

import os
import re
import zipfile
import webbrowser
from threading import Timer
from yaml.loader import SafeLoader
import gc
import matplotlib.pyplot as plt



app = Flask(__name__)
app.json.sort_keys = False
app.secret_key = os.urandom(24)
socketio = SocketIO(app,logger=True, engineio_logger=True)

# Connect to phpMyAdmin Database
connpool = pymysqlpool.ConnectionPool(host="103.21.58.10",
                       user="pubbsm8z",
                       password="Matrix__111",
                       database="pubbsm8z_uba",
                       port = 3306,
                       size=10
                       )
conn = connpool.get_connection()
conn1 = connpool.get_connection()
conn2 = connpool.get_connection()
conn3 = connpool.get_connection()
conn_ = connpool.get_connection()
conn4 = connpool.get_connection()

def df2b(df):
            b = df.to_csv(index=False).encode('utf-8')
            return b

def b2df(b):
    df = pd.read_csv(BytesIO(bytes(b,'utf-8')))
    return df


def input_dict(passengerarrival,distance,timeperiod,link_traveltime,alightrate,fare,od_files_list):
    '''Returns the inputs as a named dictionary'''
    dict = {
        'passengerarrival': passengerarrival,
        'distance': distance,
        'timeperiod': timeperiod,
        'link_traveltime': link_traveltime,
        'alightrate': alightrate,
        'fare': fare,
        'files':od_files_list
    }
    return dict



def cost_oned (passengerarrival,distance,frequency,timeperiod,link_traveltime,alightrate,fare, files,direcn,purpose):
    tot_dis = distance.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
    tot_dis = np.ceil(float(np.asarray(tot_dis)))

    # FIXED COST  DIRECTION per trip

    fuelcostrunning = (fuelprice * tot_dis / kmperliter).round(-2).round(0)
    maintenancecost = (tot_dis * busmaintenance).round(0)
    vehdepreciation = ((buscost / buslifecycle) * tot_dis).round(0)
    crewcost = (crewperbus * creqincome / (2 * cr_trip * cr_day))

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    # 1. Departure time calculation
    # -------------------------------------------------------------------------------------------------------------------------------------------------------

    time_period= timeperiod.copy()
    print("time_period",time_period)
    print("frequency",frequency)
    time_period['frequency'] = np.ceil(frequency)
    time_period['Headway_in_hours'] = (1 / (frequency)).round(2)


    departuretime = pd.DataFrame()
    headway1 = pd.DataFrame()
    for ind, col in time_period.iterrows():
        if ind == 0:
            for f in range(0, int(time_period.iloc[ind, 1])):
                departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + ((f * time_period.iloc[ind, 2]))}])], ignore_index=True)
                headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)
        else:
            for f in range(0, int(time_period.iloc[ind, 1])):
                if f == 0:
                    headway_avg = (time_period.iloc[ind, 2] + time_period.iloc[ind - 1, 2]) / 2
                    temp_departure = departuretime.iloc[-1, 0] + headway_avg
                    departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': temp_departure}])], ignore_index=True)
                    headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': headway_avg * 60}, ])], ignore_index=True)
                else:
                    departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + (f * time_period.iloc[ind, 2])}])], ignore_index=True)
                    headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)


    # del temp_departure
    # del headway_avg


    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    #  2. Simulation of full day bus services
    # -------------------------------------------------------------------------------------------------------------------------------------------------------


    arrivalrate = passengerarrival / (hrinperiod * 60)
    # linktravel time, arrival rate, alighting rate  per trip
    link_travel_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    arrivalrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    alightrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    files_tr = [0] * len(departuretime.index)
    ind = -1
    time_period.index = time_period.index + 1
    for i in range(0, len(arrivalrate.index)):
        for m in range(0, int(time_period.iloc[i, 1])):
            ind = ind + 1
            for j in range(0, len(alightrate.columns)):
                link_travel_tr.iloc[ind, j] = link_traveltime.iloc[i, j]
                arrivalrate_tr.iloc[ind, j] = arrivalrate.iloc[i, j]
                alightrate_tr.iloc[ind, j] = alightrate.iloc[i, j]
                files_tr[ind] = files[i]

    p_arrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    p_waiting = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    p_alight = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    p_board = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    link_occp = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    waitingtime_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    cost_waitingtime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    p_cantboard = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    p_lost = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    d_time = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    stoparrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    headway= pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    traveltime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    load_fact = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
    invehtime = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
    cost_inveh = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    p_sit = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    p_stand = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    revenue= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
    p_cantboard_1= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    p_cantboard_2= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    p_cantboard_0 = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    despatch = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
    # Calculation of passenger arrival, number of boarding, number alighting, link occupancy, dwell time,passenger lost, passenger cannot board, waiting time, in vehicle travel time etc.
    # trip wise calculation for each stop

    for ind in range(0, len(departuretime.index)):
        for j in range(0, len(alightrate.columns)):
            # Travel time from stop j-1 to stop j and Arrival time of bus(ind) at stop j ---------------------

            if j == 0:
                traveltime.iloc[ind, j] = 0

                stoparrival.iloc[ind, j] = departuretime.iloc[ind, 0]-(headway1.iloc[ind, 0]/60)


            else:
                # TRAVEL TIME FROM STOP J-1 TO J = DWELL TIME AT STOP J-1 + LINK RUNNING TIME (J-1,J)
                traveltime.iloc[ind, j] = ((d_time.iloc[ind, j - 1] + link_travel_tr.iloc[ind, j]) / 60).round(4)
                stoparrival.iloc[ind, j] = stoparrival.iloc[ind, j - 1] + traveltime.iloc[ind, j]

            # Headway Calculations of stop j --------------------------------------------------------------
            #headway1= despatch headway

            if j == 0 or ind == 0:

                headway.iloc[ind, j] = headway1.iloc[ind, 0]
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

            p_arrival.iloc[ind, j] = np.ceil(arrivalrate_tr.iloc[ind, j] * headway.iloc[ind, j] )

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

            #  link occupancy/on board passenger of bus(ind) at stop j (Passenger on board j-1 to j)------------------------

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
            if j==0:
                d_time.iloc[ind, j]=headway1.iloc[ind, 0]

            else:
                d_time.iloc[ind, j] = dwell_time(j, departuretime.iloc[ind, 0], p_board.iloc[ind, j], p_alight.iloc[ind, j], load_fact.iloc[ind, j])
            # default holding--------------------------------------------------------------------
            if ind == 0 or j == (len(alightrate.columns) - 1):
                d_holding = 0
            else:
                # stopariival for the next stop
                traveltime_tr = ((d_time.iloc[ind, j] + link_travel_tr.iloc[ind, j + 1]) / 60).round(4)
                stoparrival_nxt = stoparrival.iloc[ind, j] + traveltime_tr
                headway_temp = (stoparrival_nxt - stoparrival.iloc[ind - 1, j + 1]) * 60
                if headway_temp < headway1.iloc[ind, 0] / 4:
                    d_holding = headway1.iloc[ind, 0] / 4 + abs(headway_temp)
                    d_time.iloc[ind, j] = d_time.iloc[ind, j] + d_holding
                else:
                    d_holding = 0

            # Despatch time at stop j for bus ind ------------------------------------------------------------------------
            if j==0:
                despatch.iloc[ind, j]=departuretime.iloc[ind,0]
            else:
                despatch.iloc[ind, j] = stoparrival.iloc[ind, j] + (d_time.iloc[ind, j] / 60)

            # Revenue calculations
            if type(files_tr[ind]) is pd.DataFrame:
                df = files_tr[ind]
            else:
                print(type(files_tr[ind]))
                df = pd.read_csv(files_tr[ind], index_col='Stops').fillna(0)
            for k in range(0, len(alightrate.columns)):
                rev = p_board.iloc[ind, j] * df.iloc[j, k] * fare.iloc[j, k]
                revenue.iloc[ind, j] = revenue.iloc[ind, j] + rev

        #---------------------------------------------------------------------
        if purpose=='GA':
            # CONSTRAINTS - TRIP WISE
            # 1.Mimimum Passenger per trip
            p_per_trip = p_arrival.iloc[ind, :].sum()
            if p_per_trip < min_ppp:

                return (0, 0, 0, 0, 0, 0, 0, 0, 0)
            else:
                pass

            # 2.Maximum percentage of passenger lost per trip(PPLPT) = 10 %
            passlosttr = p_lost.iloc[ind, :].sum()
            ppl_pt = (passlosttr / p_per_trip) * 100
            if ppl_pt > max_pplpt:

                return (0, 0, 0, 0, 0, 0, 0, 0, 0)
            else:
                pass

            # 3. Minimum revenue per trip(RVPT)
            revenue_pt = revenue.iloc[ind, :].sum()
            if revenue_pt < min_rvpt:

                return (0, 0, 0, 0, 0, 0, 0, 0, 0)
            else:
                pass

            # 4. Maximum Operation cost per trip
            tot_dwell = d_time.iloc[ind, :].sum()
            fuelcostdwell = tot_dwell * (fuelprice / 60 * kmperliter2)
            fixedcost = fuelcostrunning + fuelcostdwell + maintenancecost + vehdepreciation + crewcost
            # OPERATION COST PER TRIP=  FIXED COST PER TRIP + PASSENGER LOST PENALTY
            operation_cpt = fixedcost + (passlosttr * penalty)
            if operation_cpt > max_opc:

                return (0, 0, 0, 0, 0, 0, 0, 0, 0)
            else:
                pass
        else:
            pass

    # Total travel time hourly
    travel_time_tot = traveltime.sum(axis=1)
    #coverting arrival time to clock time
    stoparrivalclock= stoparrival.copy()

    for ind in range(0, len(stoparrival.index)):
        for j in range(0, len(stoparrival.columns)):
            stoparrivalclock.iloc[ind, j] = np.floor(stoparrival.iloc[ind, j]) + (
                        (stoparrival.iloc[ind, j] - (np.floor(stoparrival.iloc[ind, j]))) / 100 * 60).round(2)

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



    sum_revenue=revenue.sum(axis=1)
    sum_revenue=sum_revenue.sum()
    # TOTAL COST
    t_cost = int(Tot_cost.sum())


    if purpose=='GA':
        pass
    else:

        Totcost_waiting = Tot_trcost_waiting.sum()
        Totcost_inveh = Tot_trcost_inveh.sum()
        Totpasslost = Tot_trpasslost.sum()

        total_trips = frequency.sum()
        totalkilometrerun = total_trips * tot_dis
        fuelcostday= (fuelcostrunning* total_trips)+ fuelcostdwelling.sum()

        # user cost
        cuser = Tot_trcost_waiting + Tot_trcost_inveh + (Tot_trpasslost * c_cantboard)
        cuser = cuser.sum()
        # operator cost
        coperator = (Tot_trpasslost * penalty) + fixed_cost
        coperator = coperator.sum()

        if direcn == 'DN':

            categories = [
                'Total waiting time cost (₹)',
                'Total cost of in vehicle time (₹)',
                'Total passenger lost',
                'User Cost (₹)',
                'Operator Penalty Cost for passenger lost (₹)',
                'Vehcile Kilometre-run (Km)',
                'Cost of fuel (₹)',
                'Cost of vehicle maintenance (₹)',
                'Vehicle depreciation cost (₹)',
                'Crew cost (₹)',
                'Operator Cost for bus operation (₹)',
                'Total cost in down direction (₹)',
            ]

            values = [
                np.ceil(Totcost_waiting),
                np.ceil(Totcost_inveh),
                Totpasslost,
                cuser.round(0),
                (Totpasslost) * (penalty),
                totalkilometrerun,
                np.ceil(fuelcostday),
                maintenancecost*total_trips,
                vehdepreciation * total_trips,
                crewcost * total_trips,
                np.ceil(coperator),
                t_cost
            ]

            final_costs = pd.DataFrame({'Category': categories, 'Values': values})

            if purpose == 'optmised frequency':
                files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                conn = connpool.get_connection()
                c = conn.cursor()
                c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN'")
                conn.commit()
                sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','DN', {','.join(['%s' for n in columns[1:-4]])})"
                c.execute(sql,(tuple([df2b(n) for n in files])))
                conn.commit()
            else:
                pass

        else:

            categories = [
                'Total waiting time cost (₹)',
                'Total cost of in vehicle time (₹)',
                'Total passenger lost',
                'User Cost (₹)',
                'Operator Penalty Cost for passenger lost (₹)',
                'Vehcile Kilometre-run (Km)',
                'Cost of fuel (₹)',
                'Cost of vehicle maintenance (₹)',
                'Vehicle depreciation cost (₹)',
                'Crew cost (₹)',
                'Operator Cost for bus operation (₹)',
                'Total cost in down direction (₹)',
            ]

            values = [
                np.ceil(Totcost_waiting),
                np.ceil(Totcost_inveh),
                Totpasslost,
                cuser.round(0),
                (Totpasslost) * (penalty),
                totalkilometrerun,
                np.ceil(fuelcostday),
                maintenancecost*total_trips,
                vehdepreciation * total_trips,
                crewcost * total_trips,
                np.ceil(coperator),
                t_cost
            ]

            final_costs = pd.DataFrame({'Category': categories, 'Values': values})
            
            if purpose == 'optmised frequency':
                files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                conn = connpool.get_connection()
                c = conn.cursor()
                c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP'")
                conn.commit()
                sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','UP', {','.join(['%s' for n in columns[1:-4]])})"
                c.execute(sql,(tuple([df2b(n) for n in files])))
                conn.commit()
            else:
                pass



    del ind
    del Tot_d_time
    del Tot_trpasslost
    del Tot_trcost_inveh
    del Tot_trcost_waiting
    # del cw_cost
    # del residual
    # del time_period
    gc.collect()


    return (despatch,sum_revenue,fixed_cost,t_cost,departuretime,headway,p_lost, travel_time_tot,stoparrival)

def overallcost(frequencyDN,frequencyUP,purpose,input_dict_UP,input_dict_DN):
    #1. input files down direction
    #--------------------------------------------------------
    passengerarrivalDN = input_dict_DN['passengerarrival']
    distanceDN = input_dict_DN['distance']
    timeperiodDN = input_dict_DN['timeperiod']
    link_traveltimeDN = input_dict_DN['link_traveltime']
    alightrateDN = input_dict_DN['alightrate']
    fareDN = input_dict_DN['fare']
    filesDN = input_dict_DN['files']

    # input files up direction
    passengerarrivalUP = input_dict_UP['passengerarrival']
    distanceUP = input_dict_UP['distance']
    timeperiodUP = input_dict_UP['timeperiod']
    link_traveltimeUP = input_dict_UP['link_traveltime']
    alightrateUP = input_dict_UP['alightrate']
    fareUP = input_dict_UP['fare']
    filesUP = input_dict_UP['files']

    #  Total Distance depot ot depot (down direction)
    L_DN = distanceDN.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
    L_DN = np.ceil(float(np.asarray(L_DN)))

    #  Total Distance depot ot depot (UP direction)
    L_UP = distanceUP.sum(axis=1, skipna=True).values
    L_UP = np.ceil(float(np.asarray(L_UP)))

    # ------------------------------------------
    #2. DOWN DIRECTION
    # ------------------------------------------
    direcn = 'DN'
    despatchDN, revenueDN, fixed_costDN, cost_DN, departuretimeDN, headwayDN, pass_lost_tr_DN, travel_time_totDN, stoparrivalDN = cost_oned(
        passengerarrivalDN, distanceDN, frequencyDN, timeperiodDN, link_traveltimeDN, alightrateDN, fareDN, filesDN,direcn,purpose)

    if revenueDN ==0 and cost_DN==0:
        return (999999999)
    else:
        pass


    # ------------------------------------------
    #3. UP DIRECTION
    # ------------------------------------------
    direcn = 'UP'
    despatchUP, revenueUP, fixed_costUP, cost_UP, departuretimeUP, headwayUP, pass_lost_tr_UP, travel_time_totUP, stoparrivalUP = cost_oned(
        passengerarrivalUP, distanceUP, frequencyUP, timeperiodUP, link_traveltimeUP, alightrateUP, fareUP, filesUP,direcn,purpose)
    if revenueUP ==0 and cost_UP==0:
        return (999999999)
    else:
        pass

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    #4. Terminal and Vehicle Scheduling
    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    from terminal_vehicle_schedule import schedule
    timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1,veh_sch2,veh_schedule = schedule(slack,travel_time_totDN,departuretimeDN,departuretimeUP, travel_time_totUP,'',lay_overtime)

    overallcost = cost_DN + cost_UP


    num_tripsDN = len(departuretimeDN.index)
    num_tripsUP = len(departuretimeUP.index)
    # number of passengers served within the entire day of service
    p_arrivalDN = passengerarrivalDN.sum(axis=1)
    p_arrivalDN = p_arrivalDN.sum()
    p_arrivalUP = passengerarrivalUP.sum(axis=1)
    p_arrivalUP = p_arrivalUP.sum()

    p_arrival = p_arrivalUP + p_arrivalDN

    # total passenger lost
    passlostDN = pass_lost_tr_DN.sum(axis=1)
    passlostDN = passlostDN.sum()
    passlostUP = pass_lost_tr_UP.sum(axis=1)
    passlostUP = passlostUP.sum()
    passlost = passlostDN + passlostUP

    # fixed cost
    fixed_costDN = fixed_costDN.sum()
    fixed_costUP = fixed_costUP.sum()

    # total operator cost for full service
    OperatorCostDN = fixed_costDN + (passlostDN * penalty)
    OperatorCostUP = fixed_costUP + (passlostDN * penalty)
    OperatorCost = OperatorCostDN + OperatorCostUP

    #service level parameters
    # 1. Maximum operation cost per passenger (OPPP)
    oppp = OperatorCost / p_arrival
    # 2. Minimum passenger per vehicle-kilometer (PPVK)
    veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
    ppvk = p_arrival / veh_km
    # 3.	Minimum passenger per trip (PPT)
    # total number of passenger in down direction/ total number of trips in down direction
    pptDN = p_arrivalDN / num_tripsDN
    pptUP = p_arrivalUP / num_tripsUP
    # 4. Max operation cost per trip OCPP
    ocpp_DN = OperatorCostDN / num_tripsDN
    ocpp_UP = OperatorCostUP / num_tripsUP
    # 5. Maximum percentage of passenger lost (PPL) =10%
    ppl_DN = (passlostDN / p_arrivalDN) * 100
    ppl_UP = (passlostUP / p_arrivalUP) * 100
    # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
    revenue = revenueDN + revenueUP
    crr = revenue / OperatorCost

    #5. CONSTRAINTS
    #-----------------------------------------------------

    if purpose == 'GA':


        # 1. Maximum operation cost per passenger (OPPP)
        oppp = OperatorCost / p_arrival

        if oppp > max_oppp:

            return (999999999)
        else:
            pass

        # 2. Minimum passenger per vehicle-kilometer (PPVK)
        veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
        ppvk = p_arrival / veh_km

        if ppvk < min_ppvk:

            return (999999999)
        else:
            pass

        # 3.	Minimum passenger per trip (PPT)
        # total number of passenger in down direction/ total number of trips in down direction
        pptDN = p_arrivalDN / num_tripsDN
        pptUP = p_arrivalUP / num_tripsUP

        if pptDN < min_ppt or pptUP < min_ppt:


            return (999999999)
        else:
            pass

        # 4. Max operation cost per trip OCPP
        ocpp_DN = OperatorCostDN / num_tripsDN
        ocpp_UP = OperatorCostUP / num_tripsUP

        if ocpp_DN > max_ocpp or ocpp_UP > max_ocpp:

            return (999999999)
        else:
            pass



        # 5. Maximum percentage of passenger lost (PPL) =10%

        ppl_DN = (passlostDN / p_arrivalDN) * 100
        ppl_UP = (passlostUP / p_arrivalUP) * 100

        if ppl_DN > max_ppl or ppl_UP > max_ppl:

            return (999999999)
        else:
            pass

        # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
        revenue = revenueDN + revenueUP
        crr = revenue / OperatorCost
        if crr < min_crr:

            return (999999999)
        else:
            pass

    else:

        categories = [
            'Operation cost per passenger (OPPP)',
            'Passenger per vehicle-kilometer (PPVK)',
            'Passenger per trip T1 to T2(PPT)',
            'Passenger per trip T2 to T1(PPT)',
            'Operation cost per trip T1 to T2',
            'Operation cost per trip T2 to T1',
            'Percentage of passenger lost T1 to T2',
            'Percentage of passenger lost T2 to T1',
            'Cost recovery ratio (total earnings for full day operation/ operational cost)'
        ]

        values = [
            oppp.round(2),
            ppvk.round(2),
            pptDN.round(2),
            pptUP.round(2),
            ocpp_DN.round(2),
            ocpp_UP.round(2),
            ppl_DN.round(2),
            ppl_UP.round(2),
            crr
        ]

        service_params = pd.DataFrame({'Category': categories, 'Values': values})

        columns = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']
        files = [service_params,timetable,veh_schedule,veh_sch2,veh_sch1]

        conn = connpool.get_connection()
        c = conn.cursor()
        sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='UP';"
        c.execute(sql,(tuple([df2b(n) for n in files])))
        sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='DN';"
        c.execute(sql,(tuple([df2b(n) for n in files])))
        conn.commit()

        

    del frequencyDN
    del frequencyUP
    del passengerarrivalDN
    del distanceDN

    del link_traveltimeDN
    del alightrateDN
    del passengerarrivalUP
    del distanceUP

    del link_traveltimeUP
    del alightrateUP

    gc.collect()

    return (overallcost)

def odalight(files):
    od1 = files[0]

    boarding = pd.DataFrame(index=np.arange(0), columns=od1.columns)
    alighting = pd.DataFrame(index=np.arange(0), columns=od1.columns)
    od_rate= pd.DataFrame(index=od1.index, columns=od1.columns)
    for filename in files:
        df = filename
        list_1 = df.sum(axis=0)  # alighting
        list_2 = df.sum(axis=1)  # boarding
        boarding.loc[len(boarding.index)] = list_2
        alighting.loc[len(alighting.index)] = list_1
        for i in range (0,len(od1.index)):
            for j in range (0,len(od1.columns)):
                #alighting rate w.r.t boarding
                od_rate.iloc[i,j]= df.iloc[i,j]/list_2[i]

    boarding.index = boarding.index + 1
    alighting.index = alighting.index + 1

    alighting_rate = pd.DataFrame(index=alighting.index, columns=alighting.columns)

    for i in range(0, len((alighting.index))):
        for j in range(0, len(alighting.columns)):
            if j == 0:
                alighting_rate.iloc[i, j] = 0
            else:
                # sum of boarding till stop j-1
                x = boarding.iloc[[i], 0:j].sum(axis=1, skipna=True).values
                # sum of alighting till stop j-1
                y = alighting.iloc[[i], 0:j].sum(axis=1, skipna=True).values
                x = x[0]
                y = y[0]
                # on_board passengers
                link_load = x - y
                if link_load == 0:
                    alighting_rate.iloc[i, j] = 0
                else:
                    alighting_rate.iloc[i, j] = (alighting.iloc[i, j] / link_load).round(2)

    alighting_rate.index.name='Alighting Rate'

    return(boarding,alighting,alighting_rate)

@app.route('/data')
def get_data():
    conn1 = connpool.get_connection()
    c = conn1.cursor()
    c.execute(f"SELECT id,Stop_Name,Stop_Lat,Stop_Long FROM T_STOPS_INFO WHERE Operator = '{session['email']}'")
    stops_list= c.fetchall()
    data = []
    for n in stops_list:
        data.append({"id":n[0],"name": n[1], "lat": n[2], "lng": n[3]})
    return jsonify(data)

@app.route('/route-data', defaults={'route': None})
@app.route('/route-data/<route>')
def get_route_data(route):
    if route == None:
        route = session['route']
    conn1 = connpool.get_connection()
    c = conn1.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name,s.Stop_Lat,s.Stop_Long FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{route}' ORDER BY r.Stop_num")
    stops_list= c.fetchall()
    data = []
    for n in stops_list:
        data.append({"id":n[0],"name": n[1], "lat": n[2], "lng": n[3]})
    return jsonify(data)

@app.route('/status-display')
def get_status():
    conn2 = connpool.get_connection()
    query = f"SELECT `Route Details`,`Build Route`,`Stop Characteristics`,`Passenger Arrival`,`Fare`,`Travel Time`,`OD Data`,`OLS Details`,`Constraints`,`Service Details`,`GA Parameters`,`Scheduling Details`,`Scheduling Files`,`Bus Details` FROM T_STATUS WHERE Route = '{session['route']}' and Operator = '{session['email']}';"
    df = pd.read_sql(query, conn2)
    df = df.fillna(0)
    freq_value = df.iloc[:,:11].sum(axis=1)
    sched_value = df.iloc[:,11:].sum(axis=1)
    df.insert(11,'Frequency',freq_value)
    df.insert(15,'Scheduling',sched_value)
    df = df.fillna(0)
    if df.empty:
        data = {"Route Details":0,"Build Route":0,"Stop Characteristics":0,"Passenger Arrival":0,"Fare":0,"Travel Time":0,"OD Data":0,"OLS Details":0,"Constraints":0,"Service Details":0,"GA Parameters":0,"Frequency":0,"Scheduling Details":0,"Scheduling Files":0,"Bus Details":0}
        return jsonify(data)
    data = df.to_dict(orient='records')[0]
    return jsonify(data)

# LOGGING IN ======================================================================================================================================

# Create a User Login and Register Page
@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS T_USER (name TEXT,email VARCHAR(50), password VARCHAR(50))')
    message = ''
    if 'email' in session:
        return redirect(url_for('busroute'))
        return render_template('only_busroute.html')
    else:
        return render_template('login1.html', message = message)
    
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' in session:
        return redirect(url_for('busroute'))
        return render_template('only_busroute.html')
    else:
        return redirect('/login')
    
@app.route('/loggedin', methods = ['GET', 'POST'])
def loggedin():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM T_USER WHERE email = % s AND password = % s', (email, password, ))
        user = c.fetchone()
        if user:
            session['email'] = user[1]
            session['password'] = user[2]
            message = 'Logged in successfully !'
            return redirect('/home')
        else:
            message = 'Please enter correct email / password !'
        return render_template('login1.html', message = message)
    else:
        return redirect('/login')
    
@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('password', None)
    key_list = list(session.keys())
    for key in key_list:
        session.pop(key)
    return redirect('/home')

@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if 'email' in session:
        return render_template('index.html')
    else:
        return render_template('register1.html', message = message)

@app.route('/registered', methods =['GET', 'POST'])
def registered():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM T_USER WHERE email = % s', (email, ))
        account = c.fetchone()
        if account:
            message = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address !'
        elif not name or not password or not email:
            message = 'Please fill out the form !'
        else:
            c.execute('INSERT INTO T_USER (name, email, password) VALUES (% s, % s, % s)', (name, email, password, ))
            conn.commit()
            message = 'Registered Successfully! Please Login'
        return render_template('login1.html', message = message)
        # return render_template('register1.html', message = message)

@app.route('/sidebar/<section>', methods=['GET', 'POST'])
def sidebar(section):
    session['sidebar'] = section
    return section

# DATA ENTRY================================================================================================================

@app.route('/bus-route', methods=['GET', 'POST'])
def busroute():
    if request.method == "POST":
        session['periods'] = request.form['Number_of_service_periods']
        session['route'] = request.form['Bus_route_name']
        session['p_start'] = int(request.form['Bus_service_timings_From'][:2])
        session['p_end'] = int(request.form['Bus_service_timings_To'][:2])
        # if 'periods' not in session:
        #     session['periods'] = int(request.form['Number_of_service_periods'])
        # if 'route' not in session:
        #     session['route'] = request.form['Bus_route_name']
        # if 'p_start' not in session:
        #     session['p_start'] = int(request.form['Bus_service_timings_From'][:2])
        # if 'p_end' not in session:
        #     session['p_end'] = int(request.form['Bus_service_timings_To'][:2])

        columns = list(request.form.to_dict())

        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS T_ONLY_ROUTES (Operator TEXT,Bus_route_name TEXT,Terminal_1_origin TEXT,Terminal_2_destination TEXT,Bus_service_timings_From TEXT,Bus_service_timings_To TEXT,Number_of_service_periods TEXT)")
        c.execute(f"DELETE FROM T_ONLY_ROUTES WHERE Bus_route_name = '{session['route']}' and Operator = '{session['email']}'")
        c.execute(f"""INSERT INTO T_ONLY_ROUTES (Operator,{','.join([f'{n}' for n in columns])}) VALUES ('{session['email']}',{','.join([f'"{request.form.get(n)}"' for n in columns])})""")
        c.execute("CREATE TABLE IF NOT EXISTS T_PARAMETERS (Operator TEXT,Route TEXT,A VARCHAR(50), B VARCHAR(50), frequencydefault INT, seatcap INT, \
                  min_c_lvl FLOAT, max_c_lvl FLOAT, max_wait INT, bus_left INT, min_dwell INT, slack INT, lay_overtime INT, \
                  buscost INT, buslifecycle INT, crewperbus INT, creqincome INT, cr_trip INT, cr_day INT, \
                  busmaintenance INT, fuelprice INT, kmperliter INT, kmperliter2 INT, c_cantboard INT, c_waittime FLOAT, \
                  c_invehtime FLOAT, penalty INT, hrinperiod INT, ser_period INT, dead_todepot_t1 FLOAT, dead_todepot_t2 FLOAT, \
                  layover_depot INT, start_ser INT, end_ser INT, shift INT, max_ideal INT, sol_per_pop INT, \
                  num_generations INT, max_oppp INT, min_ppvk INT, min_ppt INT, max_ocpp INT, max_fleet INT, \
                  max_ppl INT, min_crr INT, min_ppp INT, max_pplpt INT, min_rvpt INT, max_opc INT);")
        conn.commit()
        
        c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
        record = c.fetchall()
        if not record:
            c.execute(f"INSERT INTO T_PARAMETERS (Operator,Route) VALUES ('{session['email']}','{session['route']}')")
            conn.commit()

        c.execute(f"CREATE TABLE IF NOT EXISTS T_STATUS (Operator TEXT, Route TEXT, `Route Details` FLOAT,`Build Route` FLOAT,`Stop Characteristics` FLOAT,`Passenger Arrival` FLOAT,`Fare` FLOAT,`Travel Time` FLOAT,`OD Data` FLOAT,`OLS Details` FLOAT,`Constraints` FLOAT,`Service Details` FLOAT,`GA Parameters` FLOAT,`Scheduling Details` FLOAT, `Scheduling Files` FLOAT, `Bus Details` FLOAT, `Depot Details` FLOAT)")
        c.execute(f"SELECT * FROM T_STATUS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
        data = c.fetchall()
        if not data:
            c.execute(f"INSERT INTO T_STATUS (Operator, Route,`Route Details`) VALUES ('{session['email']}','{session['route']}','1')")
        conn.commit()

        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
        data = c.fetchall()
        routes = [n[0] for n in data]

        return render_template('only_busroute.html', routes=routes, message="Bus Route info was saved", data=request.form.to_dict())
    
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS T_ONLY_ROUTES (Operator TEXT,Bus_route_name TEXT,Terminal_1_origin TEXT,Terminal_2_destination TEXT,Bus_service_timings_From TEXT,Bus_service_timings_To TEXT,Number_of_service_periods TEXT)")
    c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
    data = c.fetchall()
    routes = [n[0] for n in data]
    return render_template('only_busroute.html',routes=routes)

@app.route('/import-route', methods=['GET', 'POST'])
def import_route():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
    data = c.fetchall()
    routes = [n[0] for n in data]

    route_for_import = request.form['route_for_import']
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute(f"SELECT * FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}' AND Bus_route_name = '{route_for_import}'")
    data = c.fetchall()
    data=data[0]

    session['periods'] = data['Number_of_service_periods']
    session['route'] = data['Bus_route_name']
    session['p_start'] = int(data['Bus_service_timings_From'][:2])
    session['p_end'] = int(data['Bus_service_timings_To'][:2])

    return render_template('only_busroute.html', message="Route was imported", routes=routes, data=data)

@app.route('/clear-route', methods=['GET', 'POST'])
def clear_route():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
    data = c.fetchall()
    routes = [n[0] for n in data]

    session.pop('periods')
    session.pop('route')
    session.pop('p_start')
    session.pop('p_end')

    return render_template('only_busroute.html', message="You can fill new Route Information now",routes=routes)

@app.route('/stops', methods=['GET', 'POST'])
def stop_details():
    return render_template('only_stops.html')

@app.route('/build-route', methods=['GET', 'POST'])
def route_details():
    conn = connpool.get_connection()
    c = conn.cursor()
    # c.execute(f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id));") #,FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) )
    if request.method=='POST':
        return render_template('only_route.html')
    # c.execute(f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id));") #,FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) )
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    data= c.fetchall()
    stops = [n[1] for n in data]
    if stops:
        return render_template('only_route.html', message="Your existing route is shown below:", stops=stops)
    return render_template('only_route.html')

@app.route('/stop-char', methods=['GET', 'POST'])
def stop_char():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    data= c.fetchall()
    stop_ids = [n[0] for n in data]
    stops = [n[1] for n in data]
    # return str(stops)
    if request.method == "POST":
        if 'save' in request.form:
            # Form data
            data = request.form.to_dict()
            before_int = [True if f"{n}_before" in data else False for n in stop_ids]
            far_from_int = [True if f"{n}_far" in data else False for n in stop_ids]
            commercial = [data[n] for n in data if '_comm' in n]
            transport_hub = [data[n] for n in data if '_tran' in n]
            bus_bay = [True if f"{n}_busbay" in data else False for n in stop_ids]
            stop_rad = [data[n] for n in data if '_stoprad' in n]

            # Upload to Database
            conn = connpool.get_connection()
            c = conn.cursor()
            query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,\
                    Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN,Before_Int BOOLEAN, \
                    Far_From_Int BOOLEAN, Commercial FLOAT, Transport_Hub FLOAT, Bus_bay BOOLEAN,Stop_rad FLOAT, PRIMARY KEY (id));"
            c.execute(query)
            conn.commit()

            conn = connpool.get_connection()
            c = conn.cursor()
            for n in range(len(stops)):
                c.execute(f"UPDATE T_STOPS_INFO SET Before_Int = {before_int[n]}, Far_From_Int = {far_from_int[n]} , Commercial = \
                        '{commercial[n]}' , Transport_Hub = '{transport_hub[n]}' , Bus_bay = {bus_bay[n]} , Stop_rad = '{stop_rad[n]}'\
                         WHERE id = '{stop_ids[n]}';")
                conn.commit()
            c.execute(f"UPDATE T_STATUS SET `Stop Characteristics` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            conn = connpool.get_connection()
            c = conn.cursor()
            c.execute(f"SELECT s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay,s.Stop_rad FROM T_STOPS_INFO AS s INNER JOIN T_ROUTE_INFO AS r ON (s.id = r.Stop_id) WHERE s.id IN {tuple(stop_ids)} and r.Operator='{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
            data= c.fetchall()
            return render_template('only_stopchar.html',stops=stops, stop_ids=stop_ids, message="Data was Saved", data=data)
        elif 'getfromdb' in request.form:
            conn = connpool.get_connection()
            c = conn.cursor()
            c.execute(f"SELECT s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay,s.Stop_rad FROM T_STOPS_INFO AS s INNER JOIN T_ROUTE_INFO AS r ON (s.id = r.Stop_id) WHERE s.id IN {tuple(stop_ids)} and r.Operator='{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
            data= c.fetchall()
            # return str(data)
            return render_template('only_stopchar.html',stops=stops, stop_ids=stop_ids, message="Data was updated from DB", data=data)
    if stop_ids:
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay,s.Stop_rad FROM T_STOPS_INFO AS s INNER JOIN T_ROUTE_INFO AS r ON (s.id = r.Stop_id) WHERE s.id IN {tuple(stop_ids)} and r.Operator='{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
        data= c.fetchall()
        return render_template('only_stopchar.html',stops=stops,stop_ids=stop_ids, data=data)
    else:
        return render_template('only_stopchar.html',stops=stops,stop_ids=stop_ids, message="Build Route First", data=data)


# @app.route('/table', methods=['GET', 'POST'])
# def table_details():
#     conn = connpool.get_connection()
#     c = conn.cursor()
#     # c.execute(f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id));") #,PRIMARY KEY (id),FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) )
#     c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
#     stops= c.fetchall()
#     stops_list = [n[1] for n in stops]
#     periods=list(range(session['p_start'],session['p_end']))
#     if stops_list and 'periods' in session:
#         message=None
#         return render_template('only_table.html', stops_list=stops_list, rows=list(range(session['p_start'],session['p_end'])),periods=periods)
#     elif stops_list:
#         message = "Enter Route Information First"
#         return render_template('only_table.html', stops_list=stops_list, rows=0, message=message,periods=periods)
#     elif 'periods' in session:
#         message = "Enter Stops Information First"
#         return render_template('only_table.html', stops_list=stops_list, rows=list(range(session['p_start'],session['p_end'])), message=message,periods=periods)
#     else:
#         message = "Enter Route and Stops Information First"
#         return render_template('only_table.html', stops_list=[], rows=0, message=message,periods=periods)

@app.route('/table', methods=['GET', 'POST'])
def table_details():
    conn = connpool.get_connection()
    c = conn.cursor()
    # c.execute(f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id));") #,PRIMARY KEY (id),FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) )
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stops_list = [n[1] for n in stops]
    periods=list(range(session['p_start'],session['p_end']))
    if stops_list:
        message=None
        return render_template('only_table.html', stops_list=stops_list, rows=list(range(session['p_start'],session['p_end'])),periods=periods)
    else:
        message = "Build Route First"
        return render_template('only_table.html', message=message)

@app.route('/ols', methods=['GET', 'POST'])
def ols_details():
    if request.method == "POST":
        conn = connpool.get_connection()
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"CREATE TABLE IF NOT EXISTS T_OLS_COEFF (Operator TEXT,Route TEXT,Const FLOAT,No_of_Boarding FLOAT, No_of_Alighting FLOAT, Occupancy_Level FLOAT, Morning_Peak FLOAT, Before_Intersection FLOAT,Far_from_Intersection FLOAT,Commercial FLOAT,Transport_hub FLOAT,Bus_Bay FLOAT);")
            conn.commit()

            c.execute(f"DELETE FROM T_OLS_COEFF WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            c.execute(f"INSERT INTO T_OLS_COEFF (Operator,Route,Const,No_of_Boarding,No_of_Alighting,Occupancy_Level,Morning_Peak,Before_Intersection,Far_from_Intersection,Commercial,Transport_hub,Bus_Bay) VALUES ('{session['email']}','{session['route']}','{request.form['Const']}','{request.form['No_of_Boarding']}','{request.form['No_of_Alighting']}','{request.form['Occupancy_Level']}','{request.form['Morning_Peak']}','{request.form['Before_Intersection']}','{request.form['Far_from_Intersection']}','{request.form['Commercial']}','{request.form['Transport_hub']}','{request.form['Bus_Bay']}')")
            c.execute(f"UPDATE T_STATUS SET `OLS Details` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_ols.html', message="Data was Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_OLS_COEFF WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_ols.html', message="Data was Retrieved", data=data[0])
    else:
        return render_template('only_ols.html')

@app.route('/scheduling-details', methods=['GET', 'POST'])
def scheduling_details():
    if request.method == "POST":
        conn = connpool.get_connection()
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET dead_todepot_t1 = '{request.form['dead_todepot_t1']}', dead_todepot_t2 = '{request.form['dead_todepot_t2']}', layover_depot = '{request.form['layover_depot']}', start_ser = '{request.form['start_ser']}', end_ser = '{request.form['end_ser']}', shift = '{request.form['shift']}', max_ideal = '{request.form['max_ideal']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            c.execute(f"UPDATE T_STATUS SET `Scheduling Details` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_scheduling_details.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_scheduling_details.html', message="Retrieved",data=data[0])
    else:
        return render_template('only_scheduling_details.html')

@app.route('/constraints', methods=['GET', 'POST'])
def constraints_details():
    if request.method == "POST":
        conn = connpool.get_connection()
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET max_oppp = '{request.form['max_oppp']}', min_ppvk = '{request.form['min_ppvk']}', min_ppt = '{request.form['min_ppt']}', max_ocpp = '{request.form['max_ocpp']}', max_fleet = '{request.form['max_fleet']}', max_ppl = '{request.form['max_ppl']}', min_crr = '{request.form['min_crr']}', min_ppp = '{request.form['min_ppp']}', max_pplpt = '{request.form['max_pplpt']}', min_rvpt = '{request.form['min_rvpt']}', max_opc = '{request.form['max_opc']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            c.execute(f"UPDATE T_STATUS SET `Constraints` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_constraints.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_constraints.html', message="Retrieved",data=data[0])
    else:
        return render_template('only_constraints.html')

@app.route('/service', methods=['GET', 'POST'])
def service_details():
    if request.method == "POST":
        conn = connpool.get_connection()
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET A = '{request.form['A']}', B = '{request.form['B']}', frequencydefault = '{request.form['frequencydefault']}', seatcap = '{request.form['seatcap']}', min_c_lvl = '{request.form['min_c_lvl']}', max_c_lvl = '{request.form['max_c_lvl']}', max_wait = '{request.form['max_wait']}', bus_left = '{request.form['bus_left']}', min_dwell = '{request.form['min_dwell']}', slack = '{request.form['slack']}', lay_overtime = '{request.form['lay_overtime']}', buscost = '{request.form['buscost']}', buslifecycle = '{request.form['buslifecycle']}', crewperbus = '{request.form['crewperbus']}', creqincome = '{request.form['creqincome']}', cr_trip = '{request.form['cr_trip']}', cr_day = '{request.form['cr_day']}', busmaintenance = '{request.form['busmaintenance']}', fuelprice = '{request.form['fuelprice']}', kmperliter = '{request.form['kmperliter']}', kmperliter2 = '{request.form['kmperliter2']}', c_cantboard = '{request.form['c_cantboard']}', c_waittime = '{request.form['c_waittime']}', c_invehtime = '{request.form['c_invehtime']}', penalty = '{request.form['penalty']}', hrinperiod = '{request.form['hrinperiod']}', ser_period = '{request.form['ser_period']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            c.execute(f"UPDATE T_STATUS SET `Service Details` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_service.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_service.html', message="Retrieved",data=data[0])
    else:
        return render_template('only_service.html')

@app.route('/ga-params', methods=['GET', 'POST'])
def ga_params():
    if request.method == "POST":
        conn = connpool.get_connection()
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET sol_per_pop = '{request.form['sol_per_pop']}', num_generations = '{request.form['num_generations']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            c.execute(f"UPDATE T_STATUS SET `GA Parameters` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_gaparams.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_gaparams.html', message="Retrieved",data=data[0])
    else:
        return render_template('only_gaparams.html')

@app.route('/save-stops', methods=['POST'])
def save_stops():
    # A unique id for the current user and the current route
    uid = secrets.token_hex(12)
    
    # Form data
    stops = request.form.to_dict()
    stops_list = [stops[n] for n in stops if '_Name' in n]
    session['stops_list'] = stops_list
    latitudes = [stops[n] for n in stops if '_lat' in n]
    longitudes = [stops[n] for n in stops if '_lng' in n]
    is_dummy = [True if f"{n}_Dummy" in stops else False for n in stops_list]
    is_intersection = [True if f"{n}_Cong" in stops else False for n in stops_list]

    # Upload to Database
    conn = connpool.get_connection()
    c = conn.cursor()

    query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,\
            Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN,Before_Int BOOLEAN, \
            Far_From_Int BOOLEAN, Commercial FLOAT, Transport_Hub FLOAT, Bus_bay BOOLEAN,Stop_rad FLOAT, PRIMARY KEY (id));"
    c.execute(query)
    conn.commit()

    conn = connpool.get_connection()
    c = conn.cursor()
    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_STOPS_INFO (uid,Operator,Stop_Name,Stop_Lat,Stop_Long,Dummy,Cong_Int) VALUES \
                  ('{uid}','{session['email']}','{stops_list[n]}','{latitudes[n]}','{longitudes[n]}',{is_dummy[n]},\
                  {is_intersection[n]});")
        conn.commit()
    
    # conn = connpool.get_connection()
    # c = conn.cursor()
    # c.execute(f"DELETE FROM T_STOPS_INFO WHERE Route = '{session['route']}' and Operator = '{session['email']}' and uid != '{uid}';")
    # conn.commit()
    # return render_template('only_table.html', stops_list=session['stops_list'], rows=list(range(1,session['periods']+1)))
    return render_template('only_stops.html', message="Stops were saved. Now you can build the route.")

@app.route('/save-route', methods=['POST'])
def save_route():
    # A unique id for the current user and the current route
    uid = secrets.token_hex(12)
    
    # Form data
    stops = request.form.to_dict()
    stops_list = [stops[n] for n in stops if '_Name' in n]
    session['stops_list'] = stops_list
    up_distances = [stops[n] for n in stops if '_UP' in n]
    dn_distances = [stops[n] for n in stops if '_DN' in n]
    stop_ids = [stops[n] for n in stops if '_ID' in n]

    # Upload to Database
    conn = connpool.get_connection()
    c = conn.cursor()
    query = f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id));" # ,FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) )
    c.execute(query)
    conn.commit()

    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_ROUTE_INFO (uid,Operator,Route,Stop_num,Stop_id,UP_Dist,DN_Dist) VALUES ('{uid}','{session['email']}','{session['route']}','{n+1}','{stop_ids[n]}','{up_distances[n]}','{dn_distances[n]}');")
        conn.commit()
    
    c.execute(f"UPDATE T_STATUS SET `Build Route` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
    conn.commit()

    c.execute(f"DELETE FROM T_ROUTE_INFO WHERE Route = '{session['route']}' and Operator = '{session['email']}' and uid != '{uid}';")
    conn.commit()

    for n in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN","T_Fare_DN","T_Fare_UP","T_OD"]:
        c.execute(f"DELETE FROM {n} WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
    c.execute(f"UPDATE T_STATUS SET `Stop Characteristics` = 0,`Passenger Arrival` = '0',`Fare` = '0',`Travel Time` = '0',`OD Data` = '0' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
    conn.commit()

    # return render_template('only_table.html', stops_list=session['stops_list'], rows=list(range(session['p_start'],session['p_end'])),periods=list(range(session['p_start'],session['p_end'])))
    return redirect('/build-route')

@app.route('/table-selected', methods=['GET', 'POST'])
def table_selected():
    conn_ = connpool.get_connection()
    c = conn_.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    conn_.close()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    table = request.form["db_table"]

    rows = []
    if "DN" in table:
        stop_ids.reverse()
        stops_list.reverse()
    if "OD" in table:
        rows=stop_ids
        rowheader=stops_list
    elif table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
        rowheader = rows
    elif table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids
        rowheader=stops_list
    return render_template('only_table.html', rowheader=rowheader, stop_ids=stop_ids, stops_list=stops_list, rows=rows, selected_table=table,periods=list(range(session['p_start'],session['p_end'])))


@app.route('/table-filled', methods=['GET', 'POST'])
def table_filled():
    # Get filled data
    data = request.form.to_dict()
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    # Upload to Database
    c = conn.cursor()
    db_table = request.form['selected_table']
    
    # c.execute(f"DROP TABLE IF EXISTS {db_table}")
    # query = f"CREATE TABLE IF NOT EXISTS {db_table} (Operator TEXT,Route TEXT,Rows TEXT,{','.join([f'`Stop {n+1}` FLOAT' for n in range(30)])});"
    table = request.form["selected_table"]

    if "DN" in db_table:
        stop_ids.reverse()
        stops_list.reverse()

    if "OD" in db_table:
        rows=stop_ids
        rowheader=stops_list
        query = f"CREATE TABLE IF NOT EXISTS T_OD (Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,Direction TEXT,Period INT,{','.join([f'`Stop_{n+1}` FLOAT' for n in range(30)])});"
        c.execute(query)
        c.execute(f"DELETE FROM T_OD WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = '{db_table[3:5]}' and Period = '{db_table[6:8]}';")
        for s in stop_ids:
            row = [data[f"{s}_{r}"] for r in stop_ids]
            query = f"INSERT INTO T_OD (Operator,Route,Stop_num,Stop_id,Direction,Period,{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])}) VALUES ('{session['email']}','{session['route']}','{stop_ids.index(s)+1}','{s}','{db_table[3:5]}','{db_table[6:8]}',{','.join(['%s' for n in range(len(rows))])});"
            c.execute(query, tuple(row))
            # c.execute(f"INSERT INTO {db_table} (Operator,Route,Stop_num,Stop_id,{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])}) VALUES ('{session['email']}','{session['route']}','{stop_ids.index(s)+1}','{s}','{','.join(row)}');")
        
        c.execute(f"SELECT * FROM T_OD WHERE Route = '{session['route']}' and Operator = '{session['email']}' GROUP BY Direction,Period")
        od_filled = c.fetchall()
        od_filled = len(od_filled)
        c.execute(f"SELECT Bus_service_timings_To,Bus_service_timings_From FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}' AND Bus_route_name = '{session['route']}'")
        data = c.fetchall()
        data=data[0]
        od_total = 2*(abs(int(data[0][:2]) - int(data[1][:2])))
        c.execute(f"UPDATE T_STATUS SET `OD Data` = '{od_filled/od_total}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        conn.commit()

    elif db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
        rowheader = rows
        query = f"CREATE TABLE IF NOT EXISTS {db_table} (Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,{','.join([f'`{n}` FLOAT' for n in range(24)])});"
        c.execute(query)
        c.execute(f"DELETE FROM {db_table} WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        for s in stop_ids:
            query = f"INSERT INTO {db_table} (Operator,Route,Stop_num,Stop_id,{','.join([f'`{n}`' for n in rows])}) VALUES ('{session['email']}','{session['route']}','{stop_ids.index(s)}','{s}',{','.join(['%s' for n in range(len(rows))])});"
            print(query)
            row = []
            for r in rows:
                row.append(float(data[f"{s}_{r}"]))
                print(row, f"{s}_{r}")
            print(query)
            c.execute(query, tuple(row))
            conn.commit()
            row = []
        arrival = 0
        travel = 0
        for n in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
            c.execute(f"CREATE TABLE IF NOT EXISTS {n} (Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,{','.join([f'`{n}` FLOAT' for n in range(24)])});")
            c.execute(f"SELECT * FROM {n} WHERE Operator = '{session['email']}' AND Route = '{session['route']}'")
            data = c.fetchall()
            if data and "Arrival" in n:
                arrival += 0.5
            if data and "Time" in n:
                travel += 0.5
        c.execute(f"UPDATE T_STATUS SET `Passenger Arrival` = '{arrival}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        c.execute(f"UPDATE T_STATUS SET `Travel Time` = '{travel}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        conn.commit()
    
    elif db_table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids
        rowheader=stops_list
        query = f"CREATE TABLE IF NOT EXISTS {db_table} (Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,{','.join([f'`Stop_{n+1}` FLOAT' for n in range(30)])});"
        c.execute(query)
        c.execute(f"DELETE FROM {db_table} WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        for s in stop_ids:
            row = [data[f"{s}_{r}"] for r in stop_ids]
            query = f"INSERT INTO {db_table} (Operator,Route,Stop_num,Stop_id,{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])}) VALUES ('{session['email']}','{session['route']}','{stop_ids.index(s)+1}','{s}',{','.join(['%s' for n in range(len(rows))])});"
            c.execute(query, tuple(row))
            # c.execute(f"INSERT INTO {db_table} (Operator,Route,Stop_num,Stop_id,{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])}) VALUES ('{session['email']}','{session['route']}','{stop_ids.index(s)+1}','{s}','{','.join(row)}');")
        conn.commit()

        fare = 0
        for n in ["T_Fare_DN","T_Fare_UP"]:
            c.execute(f"CREATE TABLE IF NOT EXISTS {n} (Operator TEXT,Route TEXT,Stop_num INT,Stop_id INT,{','.join([f'`Stop_{n+1}` FLOAT' for n in range(30)])});")
            c.execute(f"SELECT * FROM {n} WHERE Operator = '{session['email']}' AND Route = '{session['route']}'")
            data = c.fetchall()
            if data:
                fare += 0.5
        c.execute(f"UPDATE T_STATUS SET `Fare` = '{fare}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        conn.commit()
    conn.close()
    return render_template('only_table.html', message="Data was Saved", rowheader=rowheader, stop_ids=stop_ids, stops_list=stops_list, rows=rows, selected_table=table,periods=list(range(session['p_start'],session['p_end'])))
    

# new
@app.route('/retrieve-data', methods=['GET', 'POST'])
def retrieve_data():
    # Retrieve from Database
    db_table = request.form['selected_table']
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]

    if "DN" in db_table:
        stop_ids.reverse()
        stops_list.reverse()

    if "OD" in db_table:
        rows=stop_ids
        rowheader=stops_list
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])} FROM T_OD WHERE Operator = '{session['email']}' and Route='{session['route']}' and Direction='{db_table[3:5]}' and Period='{db_table[6:8]}' ORDER BY Stop_num")
        db_data= c.fetchall()

    elif db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
        rowheader = rows
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT {','.join([f'`{n}`' for n in rows])} FROM {db_table} WHERE Operator = '{session['email']}' and Route='{session['route']}' ORDER BY Stop_num")
        db_data= c.fetchall()

    elif db_table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids
        rowheader=stops_list
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT{','.join([f'`Stop_{n+1}`' for n in range(len(stop_ids))])} FROM {db_table} WHERE Operator = '{session['email']}' and Route='{session['route']}' ORDER BY Stop_num")
        db_data= c.fetchall()
    
    # if len(db_data[0]) != len(range(session['p_start'],session['p_end'])):
    #     return "The specified number of periods don't match the data from the database. Please check and try again."
    # if len(db_data) != len(stops_list):
    #     return "The specified number of stops don't match the data from the database. Please check and try again."
    return render_template('only_table.html', message="Data was Retrieved", rowheader=rowheader, stop_ids=stop_ids, stops_list=stops_list, rows=rows, db_data=db_data,selected_table=db_table,periods=list(range(session['p_start'],session['p_end'])))

# new
@app.route('/clear-table', methods=['GET', 'POST'])
def clear_table():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    db_table = request.form['selected_table']

    if "DN" in db_table:
        stop_ids.reverse()
        stops_list.reverse()

    if "OD" in db_table:
        rows=stop_ids
        rowheader=stops_list
    elif db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
        rowheader = rows
    elif db_table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids
        rowheader=stops_list
    return render_template('only_table.html', message="Table was Cleared", rowheader=rowheader, stop_ids=stop_ids, stops_list=stops_list, rows=rows, selected_table=db_table,periods=list(range(session['p_start'],session['p_end'])))

# new
@app.route('/upload-csv-data', methods=['GET', 'POST'])
def upload_csv_data():
    # Get stops list
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    db_table = request.form['selected_table']

    if "DN" in db_table:
        stop_ids.reverse()
        stops_list.reverse()

    if "OD" in db_table:
        rows=stop_ids
        rowheader=stops_list
    elif db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
        rowheader = rows
    elif db_table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids
        rowheader=stops_list

    csvdata = request.files['csvfile'].read()
    csvdata = pd.read_csv(BytesIO(csvdata))
    print(csvdata)
    csvdata = csvdata.iloc[:,1:]
    csvdata = csvdata.transpose()
    csvdata = list(csvdata.itertuples(index=False, name=None))
    # if len(csvdata) != session['periods']:
    #     return "The specified number of periods don't match the csv data uploaded. Please check and try again."
    # if len(csvdata[0]) != len(stops_list):
    #     return "The specified number of stops don't match the csv data uploaded. Please check and try again."
    return render_template('only_table.html', message="Data filled from CSV", rowheader=rowheader, stop_ids=stop_ids, stops_list=stops_list, rows=rows, selected_table=db_table,db_data=csvdata,periods=list(range(session['p_start'],session['p_end'])))

# new
@app.route('/download-csv-data', methods=['GET', 'POST'])
def download_csv_data():
    # Retrieve from Database
    data = request.form.to_dict()

    # Get stops list
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    db_table = request.form['selected_table']

    if "DN" in db_table:
        stop_ids.reverse()
        stops_list.reverse()

    if "OD" in db_table:
        rows=stop_ids
    elif db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=list(range(session['p_start'],session['p_end']))
    elif db_table in ["T_Fare_DN","T_Fare_UP"]:
        rows=stop_ids

    # Write csv
    csv = ""
    csv += ',' + ','.join(stops_list) + '\n'
    for i,r in enumerate(rows):
        row = []
        for s in stop_ids:
            row.append(float(data[f"{s}_{r}"]))
        row = ','.join([str(n) for n in row])
        csv += str(stops_list[i])+ ',' + row + '\n'

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=myplot.csv"})

@app.route('/scheduling',methods=['GET','POST'])
def scheduling():
    if request.method == "POST":
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"CREATE TABLE IF NOT EXISTS T_SCHEDULING_FILES (Operator TEXT, Route TEXT,{','.join([f'{n} TEXT' for n in request.files.keys()])})")
        c.execute(f"DELETE FROM T_SCHEDULING_FILES WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        query = f"INSERT INTO T_SCHEDULING_FILES (Operator,Route,{','.join(list(request.files.keys()))}) VALUES ('{session['email']}','{session['route']}',{','.join(['%s' for n in request.files.keys()])})"
        c.execute(f"UPDATE T_STATUS SET `Scheduling Files` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        c.execute(query,tuple([request.files[n].read() for n in request.files.keys()]))
        conn.commit()
        return render_template('only_scheduling.html', message='Files Uploaded')
        # return str(request.files.keys())
    return render_template('only_scheduling.html')

@app.route('/buses',methods=['GET','POST'])
def buses():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT max_fleet from T_PARAMETERS WHERE Operator = '{session['email']}' and Route = '{session['route']}'")
    buses = c.fetchone()
    if buses[0] is None:
        buses = 0
    else:
        buses = int(buses[0])
    if not buses:
        message = "Enter Constraints Information First"
        return render_template('only_buses.html',buses=0,message=message)
    if request.method == "POST":
        depot = request.form['depot']
        buslist = list(request.form.values())[1:]
        conn = connpool.get_connection()
        c = conn.cursor()
        # c.execute(f"DROP TABLE IF EXISTS T_BUSES")
        c.execute(f"CREATE TABLE IF NOT EXISTS T_BUSES (Operator TEXT, Route TEXT, Depot TEXT, Bus TEXT, Driver TEXT, Conductor TEXT, Image MEDIUMBLOB);")
        c.execute(f"DELETE FROM T_BUSES WHERE Operator = '{session['email']}' and Depot='{depot}'")
        for i,bus in enumerate(buslist):
            if bus == "":
                bus = f"Bus {i+1}"
            c.execute(f"INSERT INTO T_BUSES (Operator, Depot, Bus) VALUES ('{session['email']}','{depot}','{bus}')")
        c.execute(f"UPDATE T_STATUS SET `Bus Details` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        conn.commit()
        c.execute(f"SELECT Bus FROM T_BUSES WHERE Operator = '{session['email']}' and Depot='{depot}'")
        busnames = c.fetchall()
        busnames = [n[0] for n in busnames]
        return render_template('only_buses.html',buses=buses,message="Saved",busnames=busnames,depot=depot)
    return render_template('only_buses.html',buses=buses)

@app.route('/assign-buses',methods=['GET','POST'])
def assign_buses():
    conn = connpool.get_connection()
    c = conn.cursor()
    data = request.form.to_dict()
    depot = request.form['depot']
    buses = [data[n] for n in data if 'bus' in n]
    drivers = [data[n] for n in data if 'driver' in n]
    conductors = [data[n] for n in data if 'conductor' in n]
    c.execute(f"DELETE FROM T_BUSES WHERE Operator = '{session['email']}' and Route='{session['route']}'")
    conn.commit()
    for i,bus in enumerate(buses):
        c.execute(f"INSERT INTO T_BUSES (Operator, Route, Depot, Bus, Driver, Conductor) VALUES ('{session['email']}','{session['route']}','{depot}','{bus}','{drivers[i]}','{conductors[i]}')")
        conn.commit()

    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS T_ONLY_ROUTES (Operator TEXT,Bus_route_name TEXT,Terminal_1_origin TEXT,Terminal_2_destination TEXT,Bus_service_timings_From TEXT,Bus_service_timings_To TEXT,Number_of_service_periods TEXT)")
    c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
    data = c.fetchall()
    routes = [n[0] for n in data]

    c.execute(f"SELECT DISTINCT Depot FROM T_BUSES WHERE Operator = '{session['email']}'")
    data = c.fetchall()
    depots = list([n[0] for n in data])

    return render_template('run_scheduling.html',routes=routes,depots=depots, message='Buses were assigned. Please rerun to see changes')
    return redirect('/scheduling-run/Choose')

@app.route('/frequency', methods=['GET', 'POST'])
def frequency():
    # Get stops list
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    stop_dict = {n:stops_list[stop_ids.index(n)] for n in stop_ids}

    tables = ["T_OLS_COEFF","T_ROUTE_INFO","T_OD","T_Fare_DN","T_Fare_UP","T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zipf:
        for n in tables:
            query = f"SELECT * FROM {n} WHERE Operator = '{session['email']}' and Route='{session['route']}'"
            df = pd.read_sql(query, conn)
            df.dropna(axis=1,inplace=True)
            if not df.empty:
                if n == "T_OD":
                    df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                    df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)            
                    all_od = df.groupby(['Direction','Period'])
                    up_od_list=[]
                    dn_od_list=[]
                    for id,od in all_od:
                        od.drop(columns=['Direction','Period'],inplace=True)
                        od.columns = ['Stops'] + list(od.Stop_id)
                        name = f"OD {id[1]}"
                        print(name)
                        print("================================start========================================")
                        print(od)
                        print("==================================end======================================")
                        dirn = 'up' if id[0] == "UP" else "down"
                        zipf.writestr(f"OD_{dirn}/{name}.csv",od.to_csv(index=False))
                        od.set_index('Stops',inplace=True)
                        if dirn == 'up':
                            up_od_list.append(od)
                        elif dirn == 'down':
                            dn_od_list.append(od)
                    boardingUP,alightingUP,alighting_rateUP= odalight(up_od_list)
                    boardingDN,alightingDN,alighting_rateDN= odalight(dn_od_list)
                    zipf.writestr(f"alighting_rateUP.csv",alighting_rateUP.to_csv(index=False))
                    print("alighting_rateUP")
                    print("================================start========================================")
                    print(alighting_rateUP)
                    print("==================================end======================================")
                    zipf.writestr(f"alighting_rateDN.csv",alighting_rateDN.to_csv(index=False))
                    print("alighting_rateDN")
                    print("================================start========================================")
                    print(alighting_rateDN)
                    print("==================================end======================================")          
                elif n in ["T_Fare_DN","T_Fare_UP"]:
                    df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                    df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                    df.columns = ['Stops'] + list(df.Stop_id)
                    print(n)
                    print("================================start========================================")
                    print(df)
                    print("==================================end======================================")
                    zipf.writestr(f"{n}.csv",df.to_csv(index=False))
                elif n in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
                    df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                    df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                    df = df.set_index(['Stop_id'])
                    df = df.transpose()
                    df = df.reset_index()
                    name = 'Passenger arrival' if 'Arrival' in n else 'Travel Time'
                    df = df.rename({'index':name}, axis='columns') 
                    print(n)
                    print("================================start========================================")
                    print(df)
                    print("==================================end======================================")
                    zipf.writestr(f"{n}.csv",df.to_csv(index=False))
                elif n == "T_ROUTE_INFO":
                    df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                    df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                    df.drop(columns=['id','uid'],inplace=True)
                    up_df = df.drop(columns=['UP_Dist'])
                    dn_df = df.drop(columns=['DN_Dist'])
                    up_df.columns = ['Distance','Distance (Km)']
                    dn_df.columns = ['Distance','Distance (Km)']
                    up_df = up_df.transpose()
                    dn_df = dn_df.transpose()
                    zipf.writestr(f"distanceUP.csv",up_df.to_csv(header=False))
                    zipf.writestr(f"distanceDN.csv",dn_df.to_csv(header=False))
                    print(n)
                    print("================================start========================================")
                    print(up_df)
                    print("==================================end======================================")
                elif n == "T_OLS_COEFF":
                    df.drop(columns=['Operator','Route'],inplace=True)
                    df.index = ['Coef']
                    df = df.rename_axis('Attributes')
                    print(n)
                    print("================================start========================================")
                    print(df)
                    print("==================================end======================================")
                    zipf.writestr(f"{n}.csv",df.to_csv())
        query = f"SELECT s.Stop_Name,s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num"
        df = pd.read_sql(query, conn)
        df = df.rename({'Stop_Name':"Stops"}, axis='columns') 
        print("T_ROUTE_INFO")
        print("================================start========================================")
        print(df)
        print("==================================end======================================")
        zipf.writestr(f"stop wise data.csv",df.to_csv(index=False))

        query = f"SELECT Bus_service_timings_From,Bus_service_timings_To FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}' and Bus_route_name='{session['route']}'"
        df = pd.read_sql(query, conn)
        start_time = int(df.iloc[0,0][:2])
        end_time = int(df.iloc[0,1][:2])
        time_period = "Time\n" + "\n".join([f"{n}00" for n in range(start_time,end_time)])
        zipf.writestr(f"tmeperiodUP.csv",time_period)
        zipf.writestr(f"tmeperiodDN.csv",time_period)

        query = f"SELECT * FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{session['route']}'"
        df = pd.read_sql(query, conn)
        ymlfile = yaml.dump(df.to_dict(orient='records')[0],default_flow_style=None)
        zipf.writestr(f"parameters.yml",ymlfile)

        
    memory_file.seek(0)
    return send_file(memory_file, download_name='Freq_Input.zip', as_attachment=True)    

@app.route('/scheduling-run/<method>', methods=['GET', 'POST'])
def scheduling_run(method):
    conn = connpool.get_connection()
    if method == "Choose":
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS T_ONLY_ROUTES (Operator TEXT,Bus_route_name TEXT,Terminal_1_origin TEXT,Terminal_2_destination TEXT,Bus_service_timings_From TEXT,Bus_service_timings_To TEXT,Number_of_service_periods TEXT)")
        c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
        data = c.fetchall()
        routes = [n[0] for n in data]

        c.execute(f"SELECT DISTINCT Depot FROM T_BUSES WHERE Operator = '{session['email']}'")
        data = c.fetchall()
        depots = list([n[0] for n in data])

        return render_template('run_scheduling.html',routes=routes,depots=depots)
    else:
        depot = request.form['depot']

        query = f"SELECT * FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{session['route']}'"
        df = pd.read_sql(query, conn)
        ymlfile = yaml.dump(df.to_dict(orient='records')[0],default_flow_style=None)
        

        # with open(ymlfile,'r') as f:
        data = yaml.load(ymlfile, Loader=SafeLoader)

        globals().update(data)

        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT departuretime,travel_time_tot,stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'DN';")
        dn_files = c.fetchone()

        departuretimeDN = b2df(dn_files[0])
        terminalarrivalDN = b2df(dn_files[2])
        terminalarrivalDN = terminalarrivalDN.iloc[:, 0]
        travel_time_totDN = b2df(dn_files[1])

        c.execute(f"SELECT departuretime,travel_time_tot,stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'UP';")
        up_files = c.fetchone()

        departuretimeUP = b2df(up_files[0])
        terminalarrivalUP = b2df(up_files[2])
        terminalarrivalUP = terminalarrivalUP.iloc[:, 0]
        travel_time_totUP = b2df(up_files[1])

        # c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        # files = c.fetchone()

        # departuretimeDN = pd.read_csv(StringIO(files[2]))
        # departuretimeUP = pd.read_csv(StringIO(files[3]))
        # terminalarrivalDN = pd.read_csv(StringIO(files[4]))
        # terminalarrivalDN = terminalarrivalDN.iloc[:, 0]
        # terminalarrivalUP = pd.read_csv(StringIO(files[5]))
        # terminalarrivalUP = terminalarrivalUP.iloc[:, 0]
        # travel_time_totDN = pd.read_csv(StringIO(files[6]))
        # travel_time_totUP = pd.read_csv(StringIO(files[7]))

        if method == 'Multiline':
            r1_dtimeDN = b2df(dn_files[0])
            r1_dtimeUP = b2df(up_files[0])
            r1_tarrivalDN = b2df(dn_files[2])
            r1_tarrivalDN = r1_tarrivalDN.iloc[:, 0]
            r1_tarrivalUP = b2df(up_files[2])
            r1_tarrivalUP = r1_tarrivalUP.iloc[:, 0]
            r1_ttDN = b2df(dn_files[1])
            r1_ttUP = b2df(up_files[1])

            query = f"SELECT A,B,dead_todepot_t1,dead_todepot_t2 FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route = '{session['route']}'"
            c.execute(query)
            d1 = c.fetchone()
            data.update(A1=d1[0],B1=d1[1],dead_todepot_r1t1=d1[2],dead_todepot_r1t2=d1[3])

            query = f"SELECT A,B,dead_todepot_t1,dead_todepot_t2 FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{request.form['second_route']}'"
            c.execute(query)
            d2 = c.fetchone()
            data.update(A2=d2[0],B2=d2[1],dead_todepot_r2t1=d2[2],dead_todepot_r2t2=d2[3])

            c.execute(f"SELECT departuretime,travel_time_tot,stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{request.form['second_route']}' and Operator = '{session['email']}' and Direction = 'DN';")
            dn_files = c.fetchone()

            c.execute(f"SELECT departuretime,travel_time_tot,stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{request.form['second_route']}' and Operator = '{session['email']}' and Direction = 'UP';")
            up_files = c.fetchone()

            # c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{request.form['second_route']}' and Operator = '{session['email']}';")
            # files = c.fetchone()

            r2_dtimeDN = b2df(dn_files[0])
            r2_dtimeUP = b2df(up_files[0])
            r2_tarrivalDN = b2df(dn_files[2])
            r2_tarrivalDN = r2_tarrivalDN.iloc[:, 0]
            r2_tarrivalUP = b2df(up_files[2])
            r2_tarrivalUP = r2_tarrivalUP.iloc[:, 0]
            r2_ttDN = b2df(dn_files[1])
            r2_ttUP = b2df(up_files[1])

            from multiline_scheduling_model2 import main_schedule

            for i in range(0,10):
                print(r1_ttDN)
                r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet = main_schedule(r1_ttDN, r1_ttUP, r1_dtimeDN, r1_dtimeUP, r1_tarrivalDN,r1_tarrivalUP,r2_ttDN, r2_ttUP, r2_dtimeDN, r2_dtimeUP, r2_tarrivalDN,r2_tarrivalUP,data)
                tot_ideal_time = b_lst['Ideal time'].sum()
                if i == 0:
                    min_ideal = tot_ideal_time
                    min_data = r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet
                else:
                    if min_ideal > tot_ideal_time:
                        min_ideal = tot_ideal_time
                        min_data = r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet
            r1_timetable, r2_timetable, crew, bus_details, reuse_buses, veh_schedule, fig,fleet = min_data

        if method == 'FIFO':
            from Timetable_FIFO import schedule
            fleet,depot_tt,crew,timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details, fig, reuse_buses, tot_ideal_time, vehicleschedule = schedule(
            travel_time_totDN, departuretimeDN, departuretimeUP, travel_time_totUP,
            terminalarrivalDN, terminalarrivalUP, data)

        elif method == 'LIFO':
            from Timetable_LIFO import schedule
            purpose = 'ghghj'
            fleet,depot_tt,crew,timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details, fig, reuse_buses, tot_ideal_time, vehicleschedule = schedule(
            travel_time_totDN, departuretimeDN, departuretimeUP, travel_time_totUP, purpose,
            terminalarrivalDN, terminalarrivalUP, data)

        elif method == 'Random':
            from Timetable_Random import schedule
            purpose = 'ghghj'
            for i in range(0,10):
                laydf1,departure_DN,departure_UP,fleet, depot_tt, crew, timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details,  reuse_buses, tot_ideal_time,vehicleschedule = schedule(
                    travel_time_totDN, departuretimeDN, departuretimeUP, travel_time_totUP, purpose,terminalarrivalDN, terminalarrivalUP, data)
                if i == 0:
                    min_ideal = tot_ideal_time
                    min_data = laydf1,departure_DN,departure_UP,fleet, depot_tt, crew, timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details,  reuse_buses, tot_ideal_time,vehicleschedule
                else:
                    if min_ideal > tot_ideal_time:
                        min_ideal = tot_ideal_time
                        min_data = laydf1,departure_DN,departure_UP,fleet, depot_tt, crew, timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details,  reuse_buses, tot_ideal_time,vehicleschedule
            laydf1,departure_DN,departure_UP,fleet, depot_tt, crew, timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details,  reuse_buses, tot_ideal_time,vehicleschedule = min_data
        
        # Ading file names to output files
        veh_schedule.reset_index(inplace=True)
        veh_schedule.title = f'vehicle_schedule_{method}'
        crew.title = f'crew_scheduling_{method}'
        bus_details.title = f'Bus_utility_details_{method}'
        reuse_buses.title = f'Reuse_{method}'
        fleet.title = f'fleet_shift_details_{method}'

        for n in range(len(crew['buses to be dispatched '])):
            crew['buses to be dispatched '][n] = str(crew['buses to be dispatched '][n])

        print(type(crew['buses to be dispatched '][0]),"svddddddddddddddddddddddddddddddddddddddddddddddd")

        # Renaming buses
        try:
            busnames=b_lst['bus_name'].to_list()
        except:
            busnames=bus_details['bus_name'].to_list()
        c.execute(f"SELECT Bus FROM T_BUSES WHERE Operator = '{session['email']}' and Depot ='{depot}'")
        data = c.fetchall()
        buses = [n[0] for n in data]
        busname_map = {n: buses[i] for i,n in enumerate(busnames)}
        

        files = [veh_schedule,crew,bus_details,reuse_buses,fleet]

        c.execute(f"CREATE TABLE IF NOT EXISTS T_SCHEDULING_OUTPUT (Operator TEXT, Route TEXT, Schedule TEXT)")
        conn.commit()

        sche_out = BytesIO()
        with zipfile.ZipFile(sche_out, 'w') as sche_zip:
            sche_zip.writestr(f'vehicle_schedule_{method}.csv',veh_schedule.to_csv(index=False))
            sche_zip.writestr(f'crew_scheduling_{method}.csv', crew.to_csv(index=False))
            sche_zip.writestr(f'Bus_utility_details_{method}.csv', bus_details.to_csv(index=False))
            sche_zip.writestr(f'Reuse_{method}.csv', reuse_buses.to_csv(index=False))
            sche_zip.writestr(f'fleet_shift_details_{method}.csv', fleet.to_csv(index=False))
            if method == 'Multiline':
                r1_timetable.replace(regex=busname_map,inplace=True)
                c.execute(f"DELETE FROM T_SCHEDULING_OUTPUT WHERE Operator = '{session['email']}' AND Route = '{session['route']}'")
                sql = "INSERT INTO T_SCHEDULING_OUTPUT (Operator, Route, Schedule) VALUES (%s,%s,%s)"
                c.execute(sql,(session['email'],session['route'], df2b(r1_timetable)))
                r2_timetable.replace(regex=busname_map,inplace=True)
                c.execute(f"DELETE FROM T_SCHEDULING_OUTPUT WHERE Operator = '{session['email']}' AND Route = '{request.form['second_route']}'")
                sql = "INSERT INTO T_SCHEDULING_OUTPUT (Operator, Route, Schedule) VALUES (%s,%s,%s)"
                c.execute(sql,(session['email'],session['route'], df2b(r2_timetable)))
                conn.commit()
                r1_timetable.title = f'Time_Table_1_{method}'
                r2_timetable.title = f'Time_Table_2_{method}'
                files += [r1_timetable,r2_timetable]
                sche_zip.writestr(f'Time_Table_1_{method}.csv', r1_timetable.to_csv(index=False))
                sche_zip.writestr(f'Time_Table_2_{method}.csv', r2_timetable.to_csv(index=False))
                for i in range(0, len(b_lst.index)):
                    df3 = veh_schedule[(veh_schedule['bus_name'] == b_lst.iloc[i, 0])].copy()
                    df3.reset_index(drop=True, inplace=True)
                    name = b_lst.iloc[i, 0]
                    sche_zip.writestr(f'vehicleschedule/{name}.csv', df3.to_csv())
                    df3.title = busname_map[name]
                    files.append(df3)
            else:
                timetable.replace(regex=busname_map,inplace=True)
                c.execute(f"DELETE FROM T_SCHEDULING_OUTPUT WHERE Operator = '{session['email']}' AND Route = '{session['route']}'")
                sql = "INSERT INTO T_SCHEDULING_OUTPUT (Operator, Route, Schedule) VALUES (%s,%s,%s)"
                c.execute(sql,(session['email'],session['route'], df2b(timetable)))
                conn.commit()
                timetable.title = f'Time_Table_{method}'
                depot_tt.title = f'depot_shift_details_{method}'
                files += [timetable,depot_tt]
                sche_zip.writestr(f'Time_Table_{method}.csv', timetable.to_csv(index=False))
                sche_zip.writestr(f'depot_shift_details_{method}.csv', depot_tt.to_csv(index=False))
                for n in vehicleschedule:
                    n.title = busname_map[n.title]
                    sche_zip.writestr(f'vehicleschedule/{n.title}.csv', n.to_csv())
                    files.append(n)
            if method != 'Random':
                buf = BytesIO()
                print(type(fig))
                print(fig)
                fig.savefig(buf,format='pdf',dpi=300)
                encoded_img_data = base64.b64encode(buf.getvalue())
                sche_zip.writestr(f'vehicle_schedule_visual_{method}.pdf',buf.getvalue())
            elif method == 'Random':
                print(type(fig))
                print(fig)
                from Timetable_Random import vehiclesched
                fig=vehiclesched(departuretimeDN,departuretimeUP,timetable,depot_tt,laydf1)
                buf = BytesIO()
                fig.savefig(buf,format='pdf',dpi=300)
                encoded_img_data = base64.b64encode(buf.getvalue())
                sche_zip.writestr(f'vehicle_schedule_visual_{method}.pdf',buf.getvalue())
        if method != 'Multiline':
            print(timetable.to_string())
            print(f'\nNo. of Bus required at Terminal1 Depot :', busreq_at_Terminal1,
                    '\nNo. of Bus required at Terminal2 Depot:', busreq_at_Terminal2,
                    '\n\nNo. of Bus reutilized from Pool at Terminal1 :', poolsize_at_Terminal1,
                    "\nNo. of Bus reutilized from Pool at Terminal2 :", poolsize_at_Terminal2)
            print('\n Total ideal time in hours:', tot_ideal_time.round(0))
            print('Crew Requirement hourly: \n', crew)
            total_crew=crew ['Crew'].sum()
            print('\n Total crew required:', total_crew)
            print(veh_schedule.head(5))
        else:
            busreq_at_r1t1 = r1_timetable['Fleet T1'].sum()
            busreq_at_r1t2 = r1_timetable['Fleet T2'].sum()
            busreq_at_r2t1 = r2_timetable['Fleet T1'].sum()
            busreq_at_r2t2 = r2_timetable['Fleet T2'].sum()
            tot_ideal_time = b_lst['Ideal time'].sum() - r_bus['Idl_Duration'].sum()
            print('fleet size:', busreq_at_r1t1 + busreq_at_r1t2 + busreq_at_r2t1 + busreq_at_r2t2)
            print('\n Total ideal time in hours:', tot_ideal_time.round(0))
        
        
        # FOR DOWNLOADING FILE
        # sche_out.seek(0)
        # return send_file(sche_out, download_name=f'{method} Output.zip', as_attachment=True)

        for df in files:
            df.replace(regex=busname_map,inplace=True)
    
        csvfiles = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in files]
        busnames=bus_details['bus_name'].to_list()

        return render_template('scheduling_output.html', csvfiles=csvfiles, img_data=encoded_img_data.decode('utf-8'), busnames=busnames,depot=depot)


@app.route('/livelocation', methods=['GET', 'POST'])
def livelocation():
    return render_template('live_location.html')

@app.route('/sendlocation')
def sendlocation():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    room = request.args.get('room')
    data = jsonify({"latitude": latitude,"longitude": longitude})
    socketio.emit('receivedlocation',{"latitude": latitude,"longitude": longitude})
    return "Successfully sent"

@socketio.on('connect')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('join')
def on_join(data):
    global room
    room = data['room']
    join_room(room)
    emit('joined room', data)

@socketio.on('location')
def show_location(data):
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"CREATE TABLE IF NOT EXISTS T_PINGS (Operator TEXT, Route TEXT, Bus TEXT, Latitude FLOAT, Longitude FLOAT, Timestamp TIMESTAMP)")
    c.execute(f"INSERT INTO T_PINGS (Operator, Route, Bus, Latitude, Longitude) VALUES ('{session['email']}','{session['route']}','{data['bus']}','{data['latitude']}','{data['longitude']}')")
    conn.commit()
    c.execute(f"SELECT * FROM T_PINGS;")
    result = c.fetchall()
    print(result[0][4])
    print(type(result[0][4]))
    emit('receivedlocation',data,room=room)
    print(str(data))

@app.route('/gpslocation', methods=['POST'])
def gpslocation():
    # Connect to the MySQL database
    conn3 = connpool.get_connection(pre_ping=True)
    c = conn3.cursor()

    try:
        c.execute(f"CREATE TABLE IF NOT EXISTS T_PINGS (Operator TEXT, Route TEXT, Bus TEXT, Latitude FLOAT, Longitude FLOAT, Timestamp TIMESTAMP)")
        c.execute(f"INSERT INTO T_PINGS (Operator, Route, Bus, Latitude, Longitude) VALUES ('{session['email']}','{session['route']}','{request.json['bus']}','{request.json['latitude']}','{request.json['longitude']}')")
        conn3.commit()
        return 'Location uploaded successfully'

    except Exception as e:
        print('Error uploading location:', str(e))
        conn3.rollback()
        return 'Location upload failed'

    finally:
        # Close the database connection
        c.close()
        conn3.close()

@app.route('/get-pings', defaults={'route': None})
@app.route('/get-pings/<route>')
def get_pings(route):
    if route == None:
        route = session['route']
    conn1 = connpool.get_connection()
    c = conn1.cursor()
    c.execute(f"SELECT DISTINCT Bus FROM T_PINGS WHERE Operator = '{session['email']}' and Route='{route}' and Timestamp > now() - interval 1 hour")
    result= c.fetchall()
    buses = [n[0] for n in result]
    busdata = {}
    for i_bus,bus in enumerate(buses):
        c.execute(f"SELECT Latitude, Longitude, Timestamp FROM T_PINGS WHERE Operator = '{session['email']}' and Route='{route}' and Bus = '{bus}' ORDER BY Timestamp Desc LIMIT 3")
        result= c.fetchall()
        try:
            timediff = result[0][2]-result[1][2]
            latest_coord = [result[2][0],result[2][1]]
            previous_coord = [result[1][0],result[1][1]]
            distance = geopy.distance.distance(latest_coord, previous_coord).m
            speed = round((distance/timediff.total_seconds())*18/5)
            timediff = timediff.total_seconds()
        except:
            timediff = 0
            speed = 0
        data = []
        for res in result:
            data.append({"latitude": res[0],"longitude": res[1],"Speed" :speed,"Timediff": timediff})

        c.execute(f"SELECT s.id,s.Stop_Name,s.Stop_Lat,s.Stop_Long,s.Stop_rad FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
        stops= c.fetchall()
        stop_ids = [n[0] for n in stops]
        stops_list = [n[1] for n in stops]
        stops_coord = [[n[2],n[3]] for n in stops]
        stops_rad = [n[4] for n in stops]

        c.execute(f"SELECT stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'DN';")
        files = c.fetchone()
        stoparrivalDN = b2df(files[1])

        c.execute(f"SELECT stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'UP';")
        files = c.fetchone()
        stoparrivalUP = b2df(files[1])

        # c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        # files = c.fetchone()

        # stoparrivalDN = pd.read_csv(StringIO(files[4]))
        # stoparrivalUP = pd.read_csv(StringIO(files[5]))

        c.execute(f"SELECT Schedule from T_SCHEDULING_OUTPUT Where Operator='{session['email']}' and Route='{session['route']}'")
        schedule=b2df(c.fetchone()[0])
        try:
            trip_no = schedule.loc[(schedule['bus_name1'] == bus) & (schedule['Dep/Arrival T1'] == 'Departure'),'Dep T1'].values[0]
        except:
            continue
        trip_no = int(trip_no)
        
        arrival_times = stoparrivalUP.iloc[trip_no-1,:].to_list()
        arrival_times = [f"{int(n)}".zfill(2) + ":" + f"{round((n-int(n))*60)}".zfill(2) for n in arrival_times]
        data.append({"arrival_times": tuple(arrival_times)})
        # print(data,"===============================================================================")

        for i,_ in enumerate(stops_coord):
            distance = geopy.distance.distance(latest_coord, stops_coord[i]).m
            if distance < stops_rad[i]:
                print(stoparrivalUP.iloc[i_bus,i])
                c.execute(f"CREATE TABLE IF NOT EXISTS T_ACTUAL_ARRIVAL (Operator TEXT,Route TEXT,Bus TEXT, {','.join([f'`Stop_{n+1}` FLOAT' for n in range(30)])});")
                c.execute(f"SELECT * FROM T_ACTUAL_ARRIVAL WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Bus ='{bus}'")
                res = c.fetchall()
                if not res:
                    c.execute(f"INSERT INTO T_ACTUAL_ARRIVAL (Operator,Route,Bus) VALUES ('{session['email']}','{session['route']}','{bus}');")
                c.execute(f"SELECT `Stop_{i+1}` FROM T_ACTUAL_ARRIVAL WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Bus ='{bus}'")
                res = c.fetchall()
                print(res)
                if res[0][0] == None:
                    c.execute(f"UPDATE T_ACTUAL_ARRIVAL SET `Stop_{i+1}` = '{datetime.now().hour + datetime.now().minute/60}' WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Bus ='{bus}'")
                print(f"{bus} Arrived `Stop_{i+1}`")
                conn1.commit()

                # # holding
                # stop_no = i-1
                # scheduled_arrival = stoparrivalUP.iloc[trip_no-1,stop_no-1]
                # actual_arrival = datetime.now().hour + datetime.now().minute/60

                # print(actual_arrival,scheduled_arrival)
                # if actual_arrival>scheduled_arrival:
                #     delay = actual_arrival-scheduled_arrival

                #     holding_table = holding_process_run(delay,trip_no,stop_no,'UP')
                #     if holding_table:
                #         holding_table.set_index()
                #         holding_table.set_index('bus_name',inplace=True)
                #         busdata['holding'] = holding_table.to_json(orient='index')
                
        busdata[f'{bus}'] = data
    conn1.close()
    return jsonify(busdata)

@app.route('/holding-data')
def holding_data():
    conn = connpool.get_connection()
    c = conn.cursor()

    c.execute(f"SELECT DISTINCT Bus FROM T_PINGS WHERE Operator = '{session['email']}' and Route='{session['route']}' and Timestamp > now() - interval 1 hour")
    result= c.fetchall()
    buses = [n[0] for n in result]
    busdata = {}
    for i_bus,bus in enumerate(buses):
        c.execute(f"SELECT Latitude, Longitude, Timestamp FROM T_PINGS WHERE Operator = '{session['email']}' and Route='{session['route']}' and Bus = '{bus}' ORDER BY Timestamp Desc LIMIT 3")
        result= c.fetchall()
        timediff = result[0][2]-result[1][2]
        latest_coord = [result[2][0],result[2][1]]

        c.execute(f"SELECT s.id,s.Stop_Name,s.Stop_Lat,s.Stop_Long,s.Stop_rad FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
        stops= c.fetchall()
        stop_ids = [n[0] for n in stops]
        stops_list = [n[1] for n in stops]
        stops_coord = [[n[2],n[3]] for n in stops]
        stops_rad = [n[4] for n in stops]

        c.execute(f"SELECT stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'DN';")
        files = c.fetchone()
        stoparrivalDN = b2df(files[1])

        c.execute(f"SELECT stoparrival FROM T_INPUT_FILES_HOLDING WHERE Route = '{session['route']}' and Operator = '{session['email']}' and Direction = 'UP';")
        files = c.fetchone()
        stoparrivalUP = b2df(files[1])

        # c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        # files = c.fetchone()

        # stoparrivalDN = pd.read_csv(StringIO(files[4]))
        # stoparrivalUP = pd.read_csv(StringIO(files[5]))

        c.execute(f"SELECT Schedule from T_SCHEDULING_OUTPUT Where Operator='{session['email']}' and Route='{session['route']}'")
        schedule=b2df(c.fetchone()[0])
        try:
            trip_no = schedule.loc[(schedule['bus_name1'] == bus) & (schedule['Dep/Arrival T1'] == 'Departure'),'Dep T1'].values[0]
        except:
            continue
        trip_no = int(trip_no)
        
        arrival_times = stoparrivalUP.iloc[trip_no-1,:].to_list()
        arrival_times = [f"{int(n)}".zfill(2) + ":" + f"{round((n-int(n))*60)}".zfill(2) for n in arrival_times]
        # print(data,"===============================================================================")

        for i,_ in enumerate(stops_coord):
            distance = geopy.distance.distance(latest_coord, stops_coord[i]).m
            if distance < stops_rad[i]:
                print(stoparrivalUP.iloc[i_bus,i])

                # holding
                stop_no = i-1
                scheduled_arrival = stoparrivalUP.iloc[trip_no-1,stop_no+1]
                actual_arrival = datetime.now().hour + datetime.now().minute/60

                print(actual_arrival,scheduled_arrival)
                if actual_arrival>scheduled_arrival:
                    delay = (actual_arrival-scheduled_arrival)*100
                    print(delay,"acssssssssssssssssssssssssssssssssssssssssssssssssssssss",
                          f"{int(actual_arrival)}".zfill(2) + ":" + f"{round((actual_arrival-int(actual_arrival))*60)}".zfill(2),
                          f"{int(scheduled_arrival)}".zfill(2) + ":" + f"{round((scheduled_arrival-int(scheduled_arrival))*60)}".zfill(2))

                    holding_table = holding_process_run(delay,trip_no,stop_no,'UP')
                    try:
                        busdata = []
                        holding_table.set_index()
                        holding_table.set_index('bus_name',inplace=True)
                        busdata['holding'] = holding_table.to_json(orient='index')
                        return jsonify(busdata)
                    except:
                        return "None"
    return "checked"

@app.route('/driver')
def driver():
    driver = session['email']
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT Bus, Route FROM T_BUSES WHERE Driver = '{driver}';")
    try:
        data = c.fetchall()
        bus = data[0][0]
        route = data[0][1]

        session['route'] = route
    except:
        return render_template('driver.html', message=f"Hello {driver} Your are not assigned any bus.")

    return render_template('driver.html', bus=bus, message=f"Hello {driver} Your are assigned Bus: {bus} and Route: {route}")

@app.route('/uploadimage', methods=['POST'])
def uploadimage():
    driver = session['email']
    # Get the image data from the request
    image_data = request.json['image']

    # Decode the base64 image data
    image_bytes = base64.b64decode(image_data.split(',')[1])

    # Connect to the MySQL database
    conn1 = connpool.get_connection()
    c = conn1.cursor()

    try:
        # Insert the image into the database
        sql = "UPDATE T_BUSES SET Image = %s WHERE Driver = %s"
        c.execute(sql, (image_bytes,driver))

        # Commit the changes to the database
        conn1.commit()
        return 'Image uploaded successfully'

    except Exception as e:
        print('Error uploading image:', str(e))
        conn1.rollback()
        return 'Image upload failed'

    finally:
        # Close the database connection
        c.close()
        conn1.close()

@app.route('/images')
def get_images():
    # Connect to the MySQL database
    conn2 = connpool.get_connection()
    c = conn2.cursor()

    try:
        # Retrieve the image data from the database
        c.execute(f"SELECT DISTINCT Bus FROM T_PINGS WHERE Operator = '{session['email']}' and Route='{session['route']}' and Timestamp > now() - interval 1 hour")
        result= c.fetchall()
        buses = [n[0] for n in result]
        tuple_buses = str(tuple(buses)).replace(',)',')')
        c.execute(f"SELECT Bus, Image FROM T_BUSES WHERE Bus IN {tuple_buses} and Operator = '{session['email']}' and Route='{session['route']}'")
        # c.execute(f"SELECT Bus, Image FROM T_BUSES WHERE Bus = '{buses[0]}'")
        results = c.fetchall()

        # Create a list to store the base64-encoded image data
        image_data_dict = {}
        for result in results:
            bus = result[0]
            image_data = result[1]
            if image_data != None:
                image_data_base64 = base64.b64encode(image_data).decode('utf-8')
                image_data_dict[bus] = image_data_base64

        # Return the image data as a JSON response
        return jsonify(image_data_dict)

    except Exception as e:
        print('Error retrieving images:', str(e))
        return 'Error retrieving images'

    finally:
        # Close the database connection
        c.close()
        conn2.close()

def all_input_data():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
    stop_ids = [n[0] for n in stops]
    stops_list = [n[1] for n in stops]
    stop_dict = {n:stops_list[stop_ids.index(n)] for n in stop_ids}

    tables = ["T_OLS_COEFF","T_ROUTE_INFO","T_OD","T_Fare_DN","T_Fare_UP","T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]
    for n in tables:
        query = f"SELECT * FROM {n} WHERE Operator = '{session['email']}' and Route='{session['route']}'"
        df = pd.read_sql(query, conn)
        df.dropna(axis=1,inplace=True)
        if not df.empty:
            if n == "T_OD":
                df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)            
                all_od = df.groupby(['Direction','Period'])
                up_od_list=[]
                dn_od_list=[]
                for id,od in all_od:
                    od.drop(columns=['Direction','Period'],inplace=True)
                    od.columns = ['Stops'] + list(od.Stop_id)
                    name = f"OD {id[1]}"

                    dirn = 'up' if id[0] == "UP" else "down"
                    od.set_index('Stops',inplace=True)
                    if dirn == 'up':
                        up_od_list.append(od)
                    elif dirn == 'down':
                        dn_od_list.append(od)
                boardingUP,alightingUP,alighting_rateUP= odalight(up_od_list)
                boardingDN,alightingDN,alighting_rateDN= odalight(dn_od_list)
            
            elif n in ["T_Fare_DN","T_Fare_UP"]:
                df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                df.columns = ['Stops'] + list(df.Stop_id)
                if n == "T_Fare_UP":
                    fareUP = df.set_index('Stops')
                if n == "T_Fare_DN":
                    fareDN = df.set_index('Stops')

            elif n in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
                df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                df = df.set_index(['Stop_id'])
                df = df.transpose()
                df = df.reset_index()
                name = 'Passenger arrival' if 'Arrival' in n else 'Travel Time'
                df = df.rename({'index':name}, axis='columns')
                df.drop
                if n == "T_Passenger_Arrival_UP":
                    passengerarrivalUP = df.set_index('Passenger arrival')
                if n == "T_Passenger_Arrival_DN":
                    passengerarrivalDN = df.set_index('Passenger arrival')
                if n == "T_TravelTimeDN_ANN":
                    traveltimeUP = df.set_index('Travel Time')
                if n == "T_TraveTimeUP_ANN":
                    traveltimeDN = df.set_index('Travel Time')

            elif n == "T_ROUTE_INFO":
                df.drop(columns=['Operator','Route','Stop_num'],inplace=True)
                df.Stop_id = df.Stop_id.replace(to_replace=stop_dict)   
                df.drop(columns=['id','uid'],inplace=True)
                up_df = df.drop(columns=['UP_Dist'])
                dn_df = df.drop(columns=['DN_Dist'])
                up_df.columns = ['Distance','Distance (Km)']
                dn_df.columns = ['Distance','Distance (Km)']
                up_df = up_df.transpose()
                dn_df = dn_df.transpose()
                up_df.columns = up_df.iloc[0]
                up_df = up_df[1:]
                dn_df.columns = dn_df.iloc[0]
                dn_df = dn_df[1:]
                distanceUP = up_df
                distanceDN = dn_df

            elif n == "T_OLS_COEFF":
                df.drop(columns=['Operator','Route'],inplace=True)
                df.index = ['Coef']
                df = df.rename_axis('Attributes')
                df.columns = ['Const', 'No. of Boarding', 'No. of Alighting', 'Occupancy Level','Morning Peak', 'Before Intersection', 'Far from Intersection','Commercial (sqm)', 'Transport hub (sqm)', 'Bus Bay']
                d_coef = df

    query = f"SELECT s.Stop_Name,s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num"
    df = pd.read_sql(query, conn)
    df = df.rename({'Stop_Name':"Stops"}, axis='columns')
    df.columns = ['Stops','Before Intersection','Far from Intersection','Commercial (sqm)','Transport hub (sqm)','Bus Bay']
    stop_characteristics = df

    query = f"SELECT Bus_service_timings_From,Bus_service_timings_To FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}' and Bus_route_name='{session['route']}'"
    df = pd.read_sql(query, conn)
    start_time = int(df.iloc[0,0][:2])
    end_time = int(df.iloc[0,1][:2])
    time_period = {"Time" : [n*100 for n in range(start_time,end_time)]}
    tmeperiodUP = pd.DataFrame(time_period)
    tmeperiodDN = pd.DataFrame(time_period)

    input_dict_UP = input_dict(passengerarrivalUP,distanceUP,tmeperiodUP,traveltimeUP,alighting_rateUP,fareUP,up_od_list)
    input_dict_DN = input_dict(passengerarrivalDN,distanceDN,tmeperiodDN,traveltimeDN,alighting_rateDN,fareDN,dn_od_list)

    query = f"SELECT * FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{session['route']}'"
    df = pd.read_sql(query, conn)
    ymlfile = yaml.dump(df.to_dict(orient='records')[0],default_flow_style=None)

    return input_dict_UP, input_dict_DN, stop_characteristics, d_coef, ymlfile

def holding_process_run(delay,trip_no,stop_no,drctn):

    def cal_pop_fitness(pop,delayed_bus,h_bus,drctn,sol_per_pop):
        # Calculating the fitness value of each solution in the current population.
        # The fitness function calulates the sum of products between each input and its corresponding weight.

        cost_tbl=[0]*sol_per_pop
        for i in range (0,sol_per_pop):
            purpose='GA'
            delay_bus_cp= delayed_bus.copy()
            h_bus_cp=h_bus.copy()
            hold= pop[i,:]
            h_bus_cp['holding'] = hold
            cost_tbl[i]= cost_holding(h_bus_cp,drctn,delay_bus_cp,purpose)


        fitness=np.array(cost_tbl)
        return fitness

    def select_mating_pool(pop, fitness, num_parents):
        # Selecting the best individuals in the current generation as parents for producing the offspring of the next generation.
        parents = numpy.empty((num_parents, pop.shape[1]))
        for parent_num in range(num_parents):
            max_fitness_idx = numpy.where(fitness == numpy.min(fitness))
            max_fitness_idx = max_fitness_idx[0][0]
            parents[parent_num, :] = pop[max_fitness_idx, :]
            fitness[max_fitness_idx] = 999999999
        return parents

    def crossover(parents, offspring_size):
        offspring = numpy.empty(offspring_size)
        # The point at which crossover takes place between two parents. Usually, it is at the center.
        crossover_point = numpy.uint8(offspring_size[1]/2)

        for k in range(offspring_size[0]):
            # Index of the first parent to mate.
            parent1_idx = k%parents.shape[0]
            # Index of the second parent to mate.
            parent2_idx = (k+1)%parents.shape[0]
            offspring[k, 0:crossover_point] = parents[parent1_idx, 0:crossover_point]
            offspring[k, crossover_point:] = parents[parent2_idx, crossover_point:]
        return offspring

    def mutation(offspring_crossover,range_h, num_mutations=1):
        mutations_counter = numpy.uint8(offspring_crossover.shape[1] / num_mutations)
        # Mutation changes a number of genes as defined by the num_mutations argument. The changes are random.
        for idx in range(offspring_crossover.shape[0]):
            random_position= numpy.random.randint(0,len( range_h), int(len( range_h)/2))
            for i in range(0,len(random_position) ):
                random_value = numpy.random.randint(range_h.iloc[random_position[i],1 ],range_h.iloc[random_position[i],1 ] +1 , 1)
                offspring_crossover[idx,random_position[i] ] = random_value


        return offspring_crossover
    
    def cost_holding(h_bus_in,direc,delayed_bus_in,purpose):
        h_bus=h_bus_in.copy()
        delayed_bus=delayed_bus_in.copy()
        if direc == 'DN':

            distance = input_dict_DN['distance']
            link_travel_tr= b2df(dn_data['link_travel_tr'])
            arrivalrate_tr= b2df(dn_data['arrivalrate_tr'])
            alightrate_tr= b2df(dn_data['alightrate_tr'])
            headway1= b2df(dn_data['headway1'])
            departuretime= b2df(dn_data['departuretime'])
            p_arrival= b2df(dn_data['p_arrival'])
            p_waiting= b2df(dn_data['p_waiting'])
            p_alight= b2df(dn_data['p_alight'])
            p_board= b2df(dn_data['p_board'])
            link_occp= b2df(dn_data['link_occp'])
            waitingtime_tr= b2df(dn_data['waitingtime_tr'])
            cost_waitingtime= b2df(dn_data['cost_waitingtime'])
            p_cantboard= b2df(dn_data['p_cantboard'])
            p_lost= b2df(dn_data['p_lost'])
            d_time= b2df(dn_data['d_time'])
            stoparrival= b2df(dn_data['stoparrival'])
            headway= b2df(dn_data['headway'])
            traveltime= b2df(dn_data['traveltime'])
            load_fact= b2df(dn_data['load_fact'])
            invehtime= b2df(dn_data['invehtime'])
            cost_inveh= b2df(dn_data['cost_inveh'])
            p_sit= b2df(dn_data['p_sit'])
            p_stand= b2df(dn_data['p_stand'])
            revenue= b2df(dn_data['revenue'])
            p_cantboard_1= b2df(dn_data['p_cantboard_1'])
            p_cantboard_2= b2df(dn_data['p_cantboard_2'])
            p_cantboard_0= b2df(dn_data['p_cantboard_0'])
            despatch= b2df(dn_data['despatch'])



        else:

            distance = input_dict_UP['distance']
            link_travel_tr= b2df(up_data['link_travel_tr'])
            arrivalrate_tr= b2df(up_data['arrivalrate_tr'])
            alightrate_tr= b2df(up_data['alightrate_tr'])
            headway1= b2df(up_data['headway1'])
            departuretime= b2df(up_data['departuretime'])
            p_arrival= b2df(up_data['p_arrival'])
            p_waiting= b2df(up_data['p_waiting'])
            p_alight= b2df(up_data['p_alight'])
            p_board= b2df(up_data['p_board'])
            link_occp= b2df(up_data['link_occp'])
            waitingtime_tr= b2df(up_data['waitingtime_tr'])
            cost_waitingtime= b2df(up_data['cost_waitingtime'])
            p_cantboard= b2df(up_data['p_cantboard'])
            p_lost= b2df(up_data['p_lost'])
            d_time= b2df(up_data['d_time'])
            stoparrival= b2df(up_data['stoparrival'])
            headway= b2df(up_data['headway'])
            traveltime= b2df(up_data['traveltime'])
            load_fact= b2df(up_data['load_fact'])
            invehtime= b2df(up_data['invehtime'])
            cost_inveh= b2df(up_data['cost_inveh'])
            p_sit= b2df(up_data['p_sit'])
            p_stand= b2df(up_data['p_stand'])
            revenue= b2df(up_data['revenue'])
            p_cantboard_1= b2df(up_data['p_cantboard_1'])
            p_cantboard_2= b2df(up_data['p_cantboard_2'])
            p_cantboard_0= b2df(up_data['p_cantboard_0'])
            despatch= b2df(up_data['despatch'])

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
            conn4 = connpool.get_connection()
            c = conn4.cursor()
            files = [p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

            columns = ['p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch']

            #Export files
            if direc == 'DN':
                c = conn4.cursor(pymysql.cursors.DictCursor)
                c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='DN';")
                row = c.fetchone()

                for i,n in enumerate(columns):
                    row[columns[i]] = df2b(files[i])
                
                # c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING_2 WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='DN';")
                # sql = f"INSERT INTO T_INPUT_FILES_HOLDING_2 ({','.join([f'`{n}`' for n in row])}) VALUES ({','.join(['%s' for n in row])})"

                # c.execute(sql,tuple([row[n] for n in row]))
                conn4.commit()

            else:
                c = conn4.cursor(pymysql.cursors.DictCursor)
                c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='UP';")
                row = c.fetchone()

                for i,n in enumerate(columns):
                    row[columns[i]] = df2b(files[i])
                
                # c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING_2 WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='UP';")
                # sql = f"INSERT INTO T_INPUT_FILES_HOLDING_2 ({','.join([f'`{n}`' for n in row])}) VALUES ({','.join(['%s' for n in row])})"

                # c.execute(sql,tuple([row[n] for n in row]))
                conn4.commit()

            return(despatch,stoparrival,t_cost)
        else:
            return (despatch, stoparrival,t_cost)
    
    def st_chart(stoparrival,despatch,distance ):
        distance_origin = distance.copy()
        for i in range(0, len(distance.columns)):
            x = distance.iloc[[0], 0:i].sum(axis=1, skipna=True).values
            x = x[0]
            distance_origin.iloc[0, i] = x + distance.iloc[0, i]

        trip_st = 6
        trip_end = 11


        fig = plt.figure(figsize=(29, 21), dpi=300)
        axes = fig.add_axes([0.05, 0.05, .95, .95])
        axes.set_xlabel('Time',fontsize=20)

        axes.set_ylabel('Distance from terminal 1',fontsize=20)
        axes.set_title('Space Time diagram',fontsize=25)
        timedata_arrival = pd.DataFrame(columns=['Time', 'distance', 'trip_no'])
        for i in range(0, len(stoparrival.index)):
            timedata_arrival = pd.DataFrame(columns=['Time', 'distance', 'trip_no'])
            for j in range(0, len(stoparrival.columns)):
                list_1 = [stoparrival.iloc[i, j], distance_origin.iloc[0, j], i]
                timedata_arrival.loc[len(timedata_arrival.index)] = list_1
                list_2 = [despatch.iloc[i, j], distance_origin.iloc[0, j], i]
                timedata_arrival.loc[len(timedata_arrival.index)] = list_2
            x = timedata_arrival['Time']
            y = timedata_arrival['distance']
            name = str(stoparrival.index[i])
            axes.plot(x, y, label=name)


        return(fig)
    
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

    
    conn4 = connpool.get_connection()
    c = conn4.cursor(pymysql.cursors.DictCursor)
    columns = ['Operator','Route','Direction','service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

    c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING_2 (Operator TEXT, Route TEXT, Direction TEXT, Timestamp TIMESTAMP,{','.join([f'`{n}` TEXT' for n in columns[3:]])})")
    c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING_2 WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP' and DATE(Timestamp) != CURDATE();")

    c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN' and DATE(Timestamp) = CURDATE();")
    dn_data = c.fetchone()
    if not dn_data:
        c = conn4.cursor()
        c.execute(f"SELECT {','.join([f'`{n}`' for n in columns])} FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN'")
        data = c.fetchone()
        sql = f"INSERT INTO T_INPUT_FILES_HOLDING_2 ({','.join([f'`{n}`' for n in columns])}) VALUES ({','.join(['%s' for n in columns])})"
        c.execute(sql,data)
        conn4.commit()

        c = conn4.cursor(pymysql.cursors.DictCursor)
        c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN' and DATE(Timestamp) = CURDATE();")
        dn_data = c.fetchone()

    c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP' and DATE(Timestamp) = CURDATE();")
    up_data = c.fetchone()
    if not up_data:
        c = conn4.cursor()
        c.execute(f"SELECT {','.join([f'`{n}`' for n in columns])} FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP'")
        data = c.fetchone()
        sql = f"INSERT INTO T_INPUT_FILES_HOLDING_2 ({','.join([f'`{n}`' for n in columns])}) VALUES ({','.join(['%s' for n in columns])})"
        c.execute(sql,data)
        conn4.commit()
        
        c = conn4.cursor(pymysql.cursors.DictCursor)
        c.execute(f"SELECT * FROM T_INPUT_FILES_HOLDING_2 WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP' and DATE(Timestamp) = CURDATE();")
        up_data = c.fetchone()

    input_dict_UP, input_dict_DN, stop_characteristics, d_coef, ymlfile = all_input_data()

    passengerarrivalDN = input_dict_DN['passengerarrival']
    distanceDN = input_dict_DN['distance']
    timeperiodDN = input_dict_DN['timeperiod']
    link_traveltimeDN = input_dict_DN['link_traveltime']
    alighting_rateDN = input_dict_DN['alightrate']
    fareDN = input_dict_DN['fare']
    filesDN = input_dict_DN['files']


    # input files up direction
    passengerarrivalUP = input_dict_UP['passengerarrival']
    distanceUP = input_dict_UP['distance']
    timeperiodUP = input_dict_UP['timeperiod']
    link_traveltimeUP = input_dict_UP['link_traveltime']
    alighting_rateUP = input_dict_UP['alightrate']
    fareUP = input_dict_UP['fare']
    filesUP = input_dict_UP['files']

    data = yaml.load(ymlfile, Loader=SafeLoader)
    globals().update(data)

    dob= seatcap*min_c_lvl
    cob= int (seatcap*max_c_lvl)

    #1. INTRODUCTION OF DELAY
    #--------------------------------------------
    #Input Parameters
    # delay=10
    # trip_no=10
    # stop_no=6
    # drctn= 'DN'                      #direction 'DN'/'UP'

    control_pnts='immediate upstream stops'
    #control_pnts='inputs'        #specific control points
    #ctrlpnts_input= control_pnts

    #optimisation inputs
    sol_per_pop = 4
    num_generations = 1
    # ACTUAL ARRIVAL TIME = EXPECTED ARRIVAL + DELAY
    #---------------------------------------
    # #INPUT FILES

    #INPUT FILES
    holding= pd.DataFrame(data={0:[0,0,0,0],0.1:[0,0,0,0],0.2:[0,0,0,0],0:[0,0,0,0]})
    # holding=pd.read_csv(r'Function files\Input_files_holding\holding_process.csv ')
    if drctn== 'DN':
        veh_sch = b2df(dn_data['veh_schedule'])
        veh_sch.drop(0, inplace= True)
        dep_t1 = b2df(dn_data['veh_sch1'])
        dep_t2 = b2df(dn_data['veh_sch2'])
        despatch = b2df(dn_data['despatch'])
        despatch_idl = b2df(dn_data['despatch'])
        headway = b2df(dn_data['headway1'])
        stoparrival = b2df(dn_data['stoparrival'])
        stoparrival_idl = b2df(dn_data['stoparrival'])
        distance = input_dict_DN['distance']
        print(headway,stoparrival_idl)

    else:
        veh_sch = b2df(up_data['veh_schedule'])
        veh_sch.drop(0, inplace= True)
        dep_t1 = b2df(up_data['veh_sch1'])
        dep_t2 = b2df(up_data['veh_sch2'])
        despatch = b2df(up_data['despatch'])
        despatch_idl = b2df(up_data['despatch'])
        headway = b2df(up_data['headway1'])
        stoparrival = b2df(up_data['stoparrival'])
        stoparrival_idl = b2df(up_data['stoparrival'])
        distance = input_dict_UP['distance']
        print(headway,stoparrival_idl)

    files = [stoparrival,headway,despatch]



    stops= stoparrival.columns

    stoparrival.iloc[trip_no, stop_no]= stoparrival.iloc[trip_no, stop_no] + delay/60

    # 3.  Simulation of bus line and immediate upstreams stops----------------------------------------------------------------------
    # --------------------------------------------------------------------------


    bus_line = pd.DataFrame(index=np.arange(0), columns=['trip_no', 'ctrl_stops'])

    for i in range(0, len(stoparrival.index)):
        if i < trip_no:
            for j in range(0, len(stoparrival.columns) - 1):
                if stoparrival.iloc[i, j] >= (stoparrival.iloc[trip_no, stop_no]):
                    bus_line.loc[len(bus_line.index)] = [i, j]
                    break
                else:
                    pass
        elif i == trip_no:
            pass
        elif i > trip_no and stoparrival.iloc[i, 0] <= (stoparrival.iloc[trip_no, stop_no]):
            for j in range(0, len(stoparrival.columns)):
                if stoparrival.iloc[i, j] > (stoparrival.iloc[trip_no, stop_no]):
                    bus_line.loc[len(bus_line.index)] = [i, j]
                    break
                else:
                    pass
        else:
            break

    print('number of buses on route:', len(bus_line.index))
    bus_line['bus_name'] = ""

    for i in range(0, (len(bus_line.index))):
        bus_line.loc[i, 'bus_name'] = dep_t1.loc[bus_line.loc[i, 'trip_no'], 'bus_name']

    delayed_bus = [trip_no, stop_no, dep_t1.loc[trip_no, 'bus_name'], stoparrival.iloc[trip_no, stop_no]]

    #---------------------------------------------------------------------------------------------
    # With delay No HOLDING
    #---------------------------------------------------------------------------------------------

    delay_bus_cp = delayed_bus.copy()
    h_bus_cp = bus_line.copy()
    hold = [0]*len(h_bus_cp.index)
    h_bus_cp['holding'] = hold
    purpose='No holding'
    despatch, stoparrival,cost = cost_holding(h_bus_cp, drctn, delayed_bus, purpose)
    h_bus_cp.loc[len(h_bus_cp.index)] = delayed_bus
    h_bus_cp = h_bus_cp.sort_values(by=['trip_no']).reset_index(drop=True)
    h_bus_cp.drop(['holding'], axis=1, inplace=True)
    print('Buses on route and immediate upstream stops: \n',h_bus_cp.rename({'ctrl_stops':'Immediate upstream stops'}, axis=1))

    print('Cost of operations if no holding for ',drctn,'direction:\t',cost)


    st_trip= h_bus_cp.loc[0,'trip_no']
    end_trip = h_bus_cp.loc[len(h_bus_cp.index)-1, 'trip_no']+1

    #plotting space time chart for no delay no0 holding(ideal) condition
    #-----------------------------------------------------------------------------
    stoparrival_idl = stoparrival_idl.iloc[st_trip:end_trip, :]
    despatch_idl= despatch_idl.iloc[st_trip:end_trip, :]
    # fig1 = st_chart(stoparrival_idl, despatch_idl, distance)
    # fig1.legend(fontsize=20)
    # path = r'Function files\Output holding optimisation'
    # isExist = os.path.exists(path)
    # if not isExist:
    #     # Create a new directory because it does not exist
    #     os.makedirs(path)

    # fig1.savefig(r'Function files\Output holding optimisation\ideal_scenario.pdf', dpi=300)
    #-----------------------------------------------------------------------------
    #plotting space time chart for no holding condition
    #-----------------------------------------------------------------------------
    stoparrival_prnt = stoparrival.iloc[st_trip:end_trip, :]
    despatch_prnt = despatch.iloc[st_trip:end_trip, :]
    # fig2 = st_chart(stoparrival_prnt, despatch_prnt, distance)
    # fig2.legend(fontsize=20)
    # fig2.savefig(r'Function files\Output holding optimisation\with_delay_no_holding.pdf', dpi=300)


    #-----------------------------------------------------------------------------
    #2. CHECK DELAY
    #-----------------------------------------------------------------------------

    #check the  headway for the next bus is within the threshold
    headway_test= (stoparrival.iloc[trip_no+1, stop_no] - stoparrival.iloc[trip_no, stop_no])*60


    if headway_test >= (headway.iloc[trip_no+1,0]/4):
        print('\n no holding required')
    else:
        print('Headway deviation is beyond the threshold')
        print('\n Holding action initiated')

        #1. Control points

        if control_pnts=='immediate upstream stops':
            h_bus=bus_line

        else:
            # control points are as inputs
            h_bus_ctrlinput = pd.DataFrame(index=np.arange(0), columns=['trip_no', 'ctrl_stops'])

            for i in range(0, len(stoparrival.index)):
                if i < trip_no:
                    for j in range(0, len(stoparrival.columns) - 1):
                        if stoparrival.iloc[i, j] >= (stoparrival.iloc[trip_no, stop_no]):
                            for m in range(0, len(control_pnts)):
                                if j <= control_pnts[m]:
                                    k = control_pnts[m]
                                    break
                                else:
                                    pass
                            h_bus_ctrlinput.loc[len(h_bus_ctrlinput.index)] = [i, k]
                            break
                        else:
                            pass
                elif i == trip_no:
                    pass
                elif i > trip_no and stoparrival.iloc[i, 0] <= (stoparrival.iloc[trip_no, stop_no]):
                    for j in range(0, len(stoparrival.columns)):
                        if stoparrival.iloc[i, j] > (stoparrival.iloc[trip_no, stop_no]):
                            for m in range(0, len(control_pnts)):
                                if j <= control_pnts[m]:
                                    k = control_pnts[m]
                                    break
                                else:
                                    pass

                            h_bus_ctrlinput.loc[len(h_bus_ctrlinput.index)] = [i, k]
                            break
                        else:
                            pass
                else:
                    break
            h_bus_ctrlinput['bus_name'] = ""
            for i in range(0, (len(h_bus_ctrlinput.index))):
                h_bus_ctrlinput.loc[i, 'bus_name'] = dep_t1.loc[h_bus_ctrlinput.loc[i, 'trip_no'], 'bus_name']

            h_bus= h_bus_ctrlinput



        # 2. CALCULATION OF HOLDING RANGE-----------------------------------------------------------------------------------


        print ('Buses to be holded and control points: \n ',h_bus)

        range_h=pd.DataFrame()

        range_h['bus_name']= h_bus['bus_name']
        range_h['arrival_dest']=""
        range_h['next_dispatch'] = ""
        range_h['min holding']=0
        range_h['Max holding']=""

        #.1 = departure time @terminal 1
        #.2 = destination terminal
        #.3 = arrival time @ destination terminal


        for i in range(0,len(range_h.index)):
            for j in range (0,len(dep_t1.index)):
                arrivalDest= dep_t1.loc[h_bus.loc[i,'trip_no'],'Arrival_Time']

                for k in range(0,len(dep_t2.index)):
                    if dep_t2.loc[k,'bus_name']== dep_t1.loc[h_bus.loc[i,'trip_no'],'bus_name'] and dep_t2.loc[k,'Departure_time']>arrivalDest:
                        nextdep= dep_t2.loc[k,'Departure_time']
                        break
                    else:
                        pass
                range_h.loc[i,'arrival_dest']=arrivalDest
                range_h.loc[i,'next_dispatch']=nextdep
                range_h.loc[i,'Max holding']=((nextdep- arrivalDest)*60-lay_overtime).round(2)
        range_h.drop(['arrival_dest','next_dispatch'], axis=1, inplace=True)
        delayed_bus = [trip_no, stop_no, dep_t1.loc[trip_no, 'bus_name'], stoparrival.iloc[trip_no, stop_no]]
        print('Holding range for optimisation: \n',range_h )
        #hold=[0,0,0,0,0,0,0,0]
        #h_bus['holding'] = hold
        #cost= cost_holding(h_bus,drctn,delayed_bus)
        #print(cost)




        # 5. OPTIMISATION = genetic algorithm------------------------------------------------------------------------


        num_weights = len(range_h.index)

        num_parents_mating = int(sol_per_pop / 2)
        pop_size = (sol_per_pop, num_weights)
        new_populationDN = np.random.randint(low=range_h.iloc[:, 1], high=range_h.iloc[:, 2] + 1, size=pop_size)
        print("\nInitial population  : ", new_populationDN)
        # Measuring the fitness of each chromosome in the population.
        # pass h_bus in fitness fn if the control points are immediate upstream stop.
        # pass h_bus_ctrlinput fitness fn if the control points are specific input points.

        fitness = cal_pop_fitness(new_populationDN, delayed_bus, h_bus, drctn, sol_per_pop)
        print('cost for initial pop', fitness)

        for generation in range(num_generations):
            print("\nGeneration : ", generation)
            # Selecting the best parents in the population for mating.
            parents = select_mating_pool(new_populationDN, fitness, num_parents_mating)

            # Generating next generation using crossover.
            offspring_crossover = crossover(parents, offspring_size=(pop_size[0] - parents.shape[0], num_weights))

            # Adding some variations to the offspring using mutation.
            offspring_mutation = mutation(offspring_crossover, range_h)

            # Creating the new population based on the parents and offspring.
            new_populationDN[0:parents.shape[0], :] = parents
            new_populationDN[parents.shape[0]:, :] = offspring_mutation
            # The best result in the current iteration.
            fitness = cal_pop_fitness(new_populationDN, delayed_bus, h_bus, drctn, sol_per_pop)

            print('Cost of new population:', generation, 'Generation', fitness)

        print('Final frequency population :', new_populationDN)
        print('Fitness of population', fitness)

        final_pop = pd.DataFrame(new_populationDN)
        final_pop['Overallcost'] = fitness

        min_cost_idx = final_pop[['Overallcost']].idxmin()
        min_cost_idx = min_cost_idx.iloc[0]

        final_pop.drop('Overallcost', axis=1, inplace=True)
        hold = final_pop.iloc[min_cost_idx, :]

        h_bus['holding'] = hold.values

        # path = r'Function files\Output holding optimisation'
        # isExist = os.path.exists(path)
        # if not isExist:
        #     # Create a new directory because it does not exist
        #     os.makedirs(path)


        purpose = 'Optimised holding'
        despatch, stoparrival,cost = cost_holding(h_bus, drctn, delayed_bus, purpose)

        holding.loc[len(holding.index), 0] = holding.iloc[len(holding.index) - 1, 0] + 1
        print(holding)
        # holding.to_csv(r'Function files\Input_files_holding\holding_process.csv ', index=False)
        k = holding.iloc[len(holding.index) - 1, 0]
        name = 'optimised holding' + str(k)
        # h_bus.to_csv(r'Function files\Output holding optimisation\{}.csv '.format(name), index=False)


        # plotting space time chart for no holding condition

        stoparrival_prnt=stoparrival.iloc[st_trip:end_trip, :]
        despatch_prnt= despatch.iloc[st_trip:end_trip, :]
        fig3 = st_chart(stoparrival_prnt, despatch_prnt, distance)
        fig3.legend(fontsize=20)
        # fig3.savefig(r'Function files\Output holding optimisation\with_optimised_holding.pdf', dpi=300)

        stoparrivalclock = stoparrival.copy()
        despatchclock=despatch.copy()
        for ind in range(0, len(stoparrival.index)):
            for j in range(0, len(stoparrival.columns)):
                stoparrivalclock.iloc[ind, j] = np.floor(stoparrival.iloc[ind, j]) + (
                            (stoparrival.iloc[ind, j] - (np.floor(stoparrival.iloc[ind, j]))) / 100 * 60).round(2)
                despatchclock.iloc[ind, j] = np.floor(despatchclock.iloc[ind, j]) + (
                        (despatchclock.iloc[ind, j] - (np.floor(despatchclock.iloc[ind, j]))) / 100 * 60).round(2)




        for i in range(0,len(h_bus.index)):
            ctrl_stop=h_bus.loc[i,'ctrl_stops']
            trp_no= h_bus.loc[i,'trip_no']
            h_bus.loc[i,'ctrl_stops']= stops[ctrl_stop]
            print('Hold the bus:', h_bus.loc[i, 'bus_name'], '\t at control point:', h_bus.loc[i, 'ctrl_stops'], '\t for', h_bus.loc[i, 'holding'], 'Minutes','\t The new despatch time:', despatch.iloc[trp_no,ctrl_stop])

        print(h_bus)
        print('New despatch time and arrival time are updated')
        return h_bus
    print('End of the holding process')


@app.route('/initial-frequency', methods=['GET','POST'])
def initial_frequency():
    conn = connpool.get_connection()
    c = conn.cursor()

    input_dict_UP, input_dict_DN, stop_characteristics, d_coef, ymlfile = all_input_data()

    passengerarrivalDN = input_dict_DN['passengerarrival']
    distanceDN = input_dict_DN['distance']
    timeperiodDN = input_dict_DN['timeperiod']
    link_traveltimeDN = input_dict_DN['link_traveltime']
    alighting_rateDN = input_dict_DN['alightrate']
    fareDN = input_dict_DN['fare']
    filesDN = input_dict_DN['files']
    

    # input files up direction
    passengerarrivalUP = input_dict_UP['passengerarrival']
    distanceUP = input_dict_UP['distance']
    timeperiodUP = input_dict_UP['timeperiod']
    link_traveltimeUP = input_dict_UP['link_traveltime']
    alighting_rateUP = input_dict_UP['alightrate']
    fareUP = input_dict_UP['fare']
    filesUP = input_dict_UP['files']

    data = yaml.load(ymlfile, Loader=SafeLoader)

    globals().update(data)

    dob= seatcap*min_c_lvl
    cob= int(seatcap*max_c_lvl)

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
        
    def cost_oned (passengerarrival,distance,frequency,timeperiod,link_traveltime,alightrate,fare, files,direcn,purpose):
        tot_dis = distance.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
        tot_dis = np.ceil(float(np.asarray(tot_dis)))

        # FIXED COST  DIRECTION per trip

        fuelcostrunning = (fuelprice * tot_dis / kmperliter).round(-2).round(0)
        maintenancecost = (tot_dis * busmaintenance).round(0)
        vehdepreciation = ((buscost / buslifecycle) * tot_dis).round(0)
        crewcost = (crewperbus * creqincome / (2 * cr_trip * cr_day))

        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        # 1. Departure time calculation
        # -------------------------------------------------------------------------------------------------------------------------------------------------------

        time_period= timeperiod.copy()
        print("time_period",time_period)
        print("frequency",frequency)
        time_period['frequency'] = np.ceil(frequency)
        time_period['Headway_in_hours'] = (1 / (frequency)).round(2)


        departuretime = pd.DataFrame()
        headway1 = pd.DataFrame()
        for ind, col in time_period.iterrows():
            if ind == 0:
                for f in range(0, int(time_period.iloc[ind, 1])):
                    departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + ((f * time_period.iloc[ind, 2]))}])], ignore_index=True)
                    headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)
            else:
                for f in range(0, int(time_period.iloc[ind, 1])):
                    if f == 0:
                        headway_avg = (time_period.iloc[ind, 2] + time_period.iloc[ind - 1, 2]) / 2
                        temp_departure = departuretime.iloc[-1, 0] + headway_avg
                        departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': temp_departure}])], ignore_index=True)
                        headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': headway_avg * 60}, ])], ignore_index=True)
                    else:
                        departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + (f * time_period.iloc[ind, 2])}])], ignore_index=True)
                        headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)


        # del temp_departure
        # del headway_avg


        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        #  2. Simulation of full day bus services
        # -------------------------------------------------------------------------------------------------------------------------------------------------------


        arrivalrate = passengerarrival / (hrinperiod * 60)
        # linktravel time, arrival rate, alighting rate  per trip
        link_travel_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        arrivalrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        alightrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        files_tr = [0] * len(departuretime.index)
        ind = -1
        time_period.index = time_period.index + 1
        for i in range(0, len(arrivalrate.index)):
            for m in range(0, int(time_period.iloc[i, 1])):
                ind = ind + 1
                for j in range(0, len(alightrate.columns)):
                    link_travel_tr.iloc[ind, j] = link_traveltime.iloc[i, j]
                    arrivalrate_tr.iloc[ind, j] = arrivalrate.iloc[i, j]
                    alightrate_tr.iloc[ind, j] = alightrate.iloc[i, j]
                    files_tr[ind] = files[i]

        p_arrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_waiting = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_alight = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_board = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        link_occp = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        waitingtime_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        cost_waitingtime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_cantboard = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_lost = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        d_time = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        stoparrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        headway= pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        traveltime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        load_fact = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        invehtime = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
        cost_inveh = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_sit = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_stand = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        revenue= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
        p_cantboard_1= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_cantboard_2= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_cantboard_0 = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        despatch = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        # Calculation of passenger arrival, number of boarding, number alighting, link occupancy, dwell time,passenger lost, passenger cannot board, waiting time, in vehicle travel time etc.
        # trip wise calculation for each stop

        for ind in range(0, len(departuretime.index)):
            for j in range(0, len(alightrate.columns)):
                # Travel time from stop j-1 to stop j and Arrival time of bus(ind) at stop j ---------------------

                if j == 0:
                    traveltime.iloc[ind, j] = 0

                    stoparrival.iloc[ind, j] = departuretime.iloc[ind, 0]-(headway1.iloc[ind, 0]/60)


                else:
                    # TRAVEL TIME FROM STOP J-1 TO J = DWELL TIME AT STOP J-1 + LINK RUNNING TIME (J-1,J)
                    traveltime.iloc[ind, j] = ((d_time.iloc[ind, j - 1] + link_travel_tr.iloc[ind, j]) / 60).round(4)
                    stoparrival.iloc[ind, j] = stoparrival.iloc[ind, j - 1] + traveltime.iloc[ind, j]

                # Headway Calculations of stop j --------------------------------------------------------------
                #headway1= despatch headway

                if j == 0 or ind == 0:

                    headway.iloc[ind, j] = headway1.iloc[ind, 0]
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

                p_arrival.iloc[ind, j] = np.ceil(arrivalrate_tr.iloc[ind, j] * headway.iloc[ind, j] )

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

                #  link occupancy/on board passenger of bus(ind) at stop j (Passenger on board j-1 to j)------------------------

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
                if j==0:
                    d_time.iloc[ind, j]=headway1.iloc[ind, 0]

                else:
                    d_time.iloc[ind, j] = dwell_time(j, departuretime.iloc[ind, 0], p_board.iloc[ind, j], p_alight.iloc[ind, j], load_fact.iloc[ind, j])
                # default holding--------------------------------------------------------------------
                if ind == 0 or j == (len(alightrate.columns) - 1):
                    d_holding = 0
                else:
                    # stopariival for the next stop
                    traveltime_tr = ((d_time.iloc[ind, j] + link_travel_tr.iloc[ind, j + 1]) / 60).round(4)
                    stoparrival_nxt = stoparrival.iloc[ind, j] + traveltime_tr
                    headway_temp = (stoparrival_nxt - stoparrival.iloc[ind - 1, j + 1]) * 60
                    if headway_temp < headway1.iloc[ind, 0] / 4:
                        d_holding = headway1.iloc[ind, 0] / 4 + abs(headway_temp)
                        d_time.iloc[ind, j] = d_time.iloc[ind, j] + d_holding
                    else:
                        d_holding = 0

                # Despatch time at stop j for bus ind ------------------------------------------------------------------------
                if j==0:
                    despatch.iloc[ind, j]=departuretime.iloc[ind,0]
                else:
                    despatch.iloc[ind, j] = stoparrival.iloc[ind, j] + (d_time.iloc[ind, j] / 60)

                # Revenue calculations
                if type(files_tr[ind]) is pd.DataFrame:
                    df = files_tr[ind]
                else:
                    print(type(files_tr[ind]))
                    df = pd.read_csv(files_tr[ind], index_col='Stops').fillna(0)
                for k in range(0, len(alightrate.columns)):
                    rev = p_board.iloc[ind, j] * df.iloc[j, k] * fare.iloc[j, k]
                    revenue.iloc[ind, j] = revenue.iloc[ind, j] + rev

            #---------------------------------------------------------------------
            if purpose=='GA':
                # CONSTRAINTS - TRIP WISE
                # 1.Mimimum Passenger per trip
                p_per_trip = p_arrival.iloc[ind, :].sum()
                if p_per_trip < min_ppp:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 2.Maximum percentage of passenger lost per trip(PPLPT) = 10 %
                passlosttr = p_lost.iloc[ind, :].sum()
                ppl_pt = (passlosttr / p_per_trip) * 100
                if ppl_pt > max_pplpt:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 3. Minimum revenue per trip(RVPT)
                revenue_pt = revenue.iloc[ind, :].sum()
                if revenue_pt < min_rvpt:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 4. Maximum Operation cost per trip
                tot_dwell = d_time.iloc[ind, :].sum()
                fuelcostdwell = tot_dwell * (fuelprice / 60 * kmperliter2)
                fixedcost = fuelcostrunning + fuelcostdwell + maintenancecost + vehdepreciation + crewcost
                # OPERATION COST PER TRIP=  FIXED COST PER TRIP + PASSENGER LOST PENALTY
                operation_cpt = fixedcost + (passlosttr * penalty)
                if operation_cpt > max_opc:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass
            else:
                pass

        # Total travel time hourly
        travel_time_tot = traveltime.sum(axis=1)
        #coverting arrival time to clock time
        stoparrivalclock= stoparrival.copy()

        for ind in range(0, len(stoparrival.index)):
            for j in range(0, len(stoparrival.columns)):
                stoparrivalclock.iloc[ind, j] = np.floor(stoparrival.iloc[ind, j]) + (
                            (stoparrival.iloc[ind, j] - (np.floor(stoparrival.iloc[ind, j]))) / 100 * 60).round(2)

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



        sum_revenue=revenue.sum(axis=1)
        sum_revenue=sum_revenue.sum()
        # TOTAL COST
        t_cost = int(Tot_cost.sum())


        if purpose=='GA':
            pass
        else:

            Totcost_waiting = Tot_trcost_waiting.sum()
            Totcost_inveh = Tot_trcost_inveh.sum()
            Totpasslost = Tot_trpasslost.sum()

            total_trips = frequency.sum()
            totalkilometrerun = total_trips * tot_dis
            fuelcostday= (fuelcostrunning* total_trips)+ fuelcostdwelling.sum()

            # user cost
            cuser = Tot_trcost_waiting + Tot_trcost_inveh + (Tot_trpasslost * c_cantboard)
            cuser = cuser.sum()
            # operator cost
            coperator = (Tot_trpasslost * penalty) + fixed_cost
            coperator = coperator.sum()

            if direcn == 'DN':

                categories = [
                    'Total waiting time cost (₹)',
                    'Total cost of in vehicle time (₹)',
                    'Total passenger lost',
                    'User Cost (₹)',
                    'Operator Penalty Cost for passenger lost (₹)',
                    'Vehcile Kilometre-run (Km)',
                    'Cost of fuel (₹)',
                    'Cost of vehicle maintenance (₹)',
                    'Vehicle depreciation cost (₹)',
                    'Crew cost (₹)',
                    'Operator Cost for bus operation (₹)',
                    'Total cost in down direction (₹)',
                ]

                values = [
                    np.ceil(Totcost_waiting),
                    np.ceil(Totcost_inveh),
                    Totpasslost,
                    cuser.round(0),
                    (Totpasslost) * (penalty),
                    totalkilometrerun,
                    np.ceil(fuelcostday),
                    maintenancecost*total_trips,
                    vehdepreciation * total_trips,
                    crewcost * total_trips,
                    np.ceil(coperator),
                    t_cost
                ]

                final_costs = pd.DataFrame({'Category': categories, 'Values': values})

                if purpose == 'optmised frequency':
                    files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                    columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                    conn = connpool.get_connection()
                    c = conn.cursor()
                    c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                    c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN'")
                    conn.commit()
                    sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','DN', {','.join(['%s' for n in columns[1:-4]])})"
                    c.execute(sql,(tuple([df2b(n) for n in files])))
                    conn.commit()
                else:
                    pass

            else:

                categories = [
                    'Total waiting time cost (₹)',
                    'Total cost of in vehicle time (₹)',
                    'Total passenger lost',
                    'User Cost (₹)',
                    'Operator Penalty Cost for passenger lost (₹)',
                    'Vehcile Kilometre-run (Km)',
                    'Cost of fuel (₹)',
                    'Cost of vehicle maintenance (₹)',
                    'Vehicle depreciation cost (₹)',
                    'Crew cost (₹)',
                    'Operator Cost for bus operation (₹)',
                    'Total cost in down direction (₹)',
                ]

                values = [
                    np.ceil(Totcost_waiting),
                    np.ceil(Totcost_inveh),
                    Totpasslost,
                    cuser.round(0),
                    (Totpasslost) * (penalty),
                    totalkilometrerun,
                    np.ceil(fuelcostday),
                    maintenancecost*total_trips,
                    vehdepreciation * total_trips,
                    crewcost * total_trips,
                    np.ceil(coperator),
                    t_cost
                ]

                final_costs = pd.DataFrame({'Category': categories, 'Values': values})
                
                if purpose == 'optmised frequency':
                    files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                    columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                    conn = connpool.get_connection()
                    c = conn.cursor()
                    c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                    c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP'")
                    conn.commit()
                    sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','UP', {','.join(['%s' for n in columns[1:-4]])})"
                    c.execute(sql,(tuple([df2b(n) for n in files])))
                    conn.commit()
                else:
                    pass



        del ind
        del Tot_d_time
        del Tot_trpasslost
        del Tot_trcost_inveh
        del Tot_trcost_waiting
        # del cw_cost
        # del residual
        # del time_period
        gc.collect()


        return (despatch,sum_revenue,fixed_cost,t_cost,departuretime,headway,p_lost, travel_time_tot,stoparrival)

    def overallcost(frequencyDN,frequencyUP,purpose,input_dict_UP,input_dict_DN):
        #1. input files down direction
        #--------------------------------------------------------
        passengerarrivalDN = input_dict_DN['passengerarrival']
        distanceDN = input_dict_DN['distance']
        timeperiodDN = input_dict_DN['timeperiod']
        link_traveltimeDN = input_dict_DN['link_traveltime']
        alightrateDN = input_dict_DN['alightrate']
        fareDN = input_dict_DN['fare']
        filesDN = input_dict_DN['files']

        # input files up direction
        passengerarrivalUP = input_dict_UP['passengerarrival']
        distanceUP = input_dict_UP['distance']
        timeperiodUP = input_dict_UP['timeperiod']
        link_traveltimeUP = input_dict_UP['link_traveltime']
        alightrateUP = input_dict_UP['alightrate']
        fareUP = input_dict_UP['fare']
        filesUP = input_dict_UP['files']

        #  Total Distance depot ot depot (down direction)
        L_DN = distanceDN.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
        L_DN = np.ceil(float(np.asarray(L_DN)))

        #  Total Distance depot ot depot (UP direction)
        L_UP = distanceUP.sum(axis=1, skipna=True).values
        L_UP = np.ceil(float(np.asarray(L_UP)))

        # ------------------------------------------
        #2. DOWN DIRECTION
        # ------------------------------------------
        direcn = 'DN'
        despatchDN, revenueDN, fixed_costDN, cost_DN, departuretimeDN, headwayDN, pass_lost_tr_DN, travel_time_totDN, stoparrivalDN = cost_oned(
            passengerarrivalDN, distanceDN, frequencyDN, timeperiodDN, link_traveltimeDN, alightrateDN, fareDN, filesDN,direcn,purpose)

        if revenueDN ==0 and cost_DN==0:
            return (999999999)
        else:
            pass


        # ------------------------------------------
        #3. UP DIRECTION
        # ------------------------------------------
        direcn = 'UP'
        despatchUP, revenueUP, fixed_costUP, cost_UP, departuretimeUP, headwayUP, pass_lost_tr_UP, travel_time_totUP, stoparrivalUP = cost_oned(
            passengerarrivalUP, distanceUP, frequencyUP, timeperiodUP, link_traveltimeUP, alightrateUP, fareUP, filesUP,direcn,purpose)
        if revenueUP ==0 and cost_UP==0:
            return (999999999)
        else:
            pass

        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        #4. Terminal and Vehicle Scheduling
        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        from terminal_vehicle_schedule import schedule
        timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1,veh_sch2,veh_schedule = schedule(slack,travel_time_totDN,departuretimeDN,departuretimeUP, travel_time_totUP,'',lay_overtime)

        overallcost = cost_DN + cost_UP


        num_tripsDN = len(departuretimeDN.index)
        num_tripsUP = len(departuretimeUP.index)
        # number of passengers served within the entire day of service
        p_arrivalDN = passengerarrivalDN.sum(axis=1)
        p_arrivalDN = p_arrivalDN.sum()
        p_arrivalUP = passengerarrivalUP.sum(axis=1)
        p_arrivalUP = p_arrivalUP.sum()

        p_arrival = p_arrivalUP + p_arrivalDN

        # total passenger lost
        passlostDN = pass_lost_tr_DN.sum(axis=1)
        passlostDN = passlostDN.sum()
        passlostUP = pass_lost_tr_UP.sum(axis=1)
        passlostUP = passlostUP.sum()
        passlost = passlostDN + passlostUP

        # fixed cost
        fixed_costDN = fixed_costDN.sum()
        fixed_costUP = fixed_costUP.sum()

        # total operator cost for full service
        OperatorCostDN = fixed_costDN + (passlostDN * penalty)
        OperatorCostUP = fixed_costUP + (passlostDN * penalty)
        OperatorCost = OperatorCostDN + OperatorCostUP

        #service level parameters
        # 1. Maximum operation cost per passenger (OPPP)
        oppp = OperatorCost / p_arrival
        # 2. Minimum passenger per vehicle-kilometer (PPVK)
        veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
        ppvk = p_arrival / veh_km
        # 3.	Minimum passenger per trip (PPT)
        # total number of passenger in down direction/ total number of trips in down direction
        pptDN = p_arrivalDN / num_tripsDN
        pptUP = p_arrivalUP / num_tripsUP
        # 4. Max operation cost per trip OCPP
        ocpp_DN = OperatorCostDN / num_tripsDN
        ocpp_UP = OperatorCostUP / num_tripsUP
        # 5. Maximum percentage of passenger lost (PPL) =10%
        ppl_DN = (passlostDN / p_arrivalDN) * 100
        ppl_UP = (passlostUP / p_arrivalUP) * 100
        # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
        revenue = revenueDN + revenueUP
        crr = revenue / OperatorCost

        #5. CONSTRAINTS
        #-----------------------------------------------------

        if purpose == 'GA':


            # 1. Maximum operation cost per passenger (OPPP)
            oppp = OperatorCost / p_arrival

            if oppp > max_oppp:

                return (999999999)
            else:
                pass

            # 2. Minimum passenger per vehicle-kilometer (PPVK)
            veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
            ppvk = p_arrival / veh_km

            if ppvk < min_ppvk:

                return (999999999)
            else:
                pass

            # 3.	Minimum passenger per trip (PPT)
            # total number of passenger in down direction/ total number of trips in down direction
            pptDN = p_arrivalDN / num_tripsDN
            pptUP = p_arrivalUP / num_tripsUP

            if pptDN < min_ppt or pptUP < min_ppt:


                return (999999999)
            else:
                pass

            # 4. Max operation cost per trip OCPP
            ocpp_DN = OperatorCostDN / num_tripsDN
            ocpp_UP = OperatorCostUP / num_tripsUP

            if ocpp_DN > max_ocpp or ocpp_UP > max_ocpp:

                return (999999999)
            else:
                pass



            # 5. Maximum percentage of passenger lost (PPL) =10%

            ppl_DN = (passlostDN / p_arrivalDN) * 100
            ppl_UP = (passlostUP / p_arrivalUP) * 100

            if ppl_DN > max_ppl or ppl_UP > max_ppl:

                return (999999999)
            else:
                pass

            # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
            revenue = revenueDN + revenueUP
            crr = revenue / OperatorCost
            if crr < min_crr:

                return (999999999)
            else:
                pass

        else:

            categories = [
                'Operation cost per passenger (OPPP)',
                'Passenger per vehicle-kilometer (PPVK)',
                'Passenger per trip T1 to T2(PPT)',
                'Passenger per trip T2 to T1(PPT)',
                'Operation cost per trip T1 to T2',
                'Operation cost per trip T2 to T1',
                'Percentage of passenger lost T1 to T2',
                'Percentage of passenger lost T2 to T1',
                'Cost recovery ratio (total earnings for full day operation/ operational cost)'
            ]

            values = [
                oppp.round(2),
                ppvk.round(2),
                pptDN.round(2),
                pptUP.round(2),
                ocpp_DN.round(2),
                ocpp_UP.round(2),
                ppl_DN.round(2),
                ppl_UP.round(2),
                crr
            ]

            service_params = pd.DataFrame({'Category': categories, 'Values': values})

            columns = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']
            files = [service_params,timetable,veh_schedule,veh_sch2,veh_sch1]

            conn = connpool.get_connection()
            c = conn.cursor()
            sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='UP';"
            c.execute(sql,(tuple([df2b(n) for n in files])))
            sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='DN';"
            c.execute(sql,(tuple([df2b(n) for n in files])))
            conn.commit()

            

        del frequencyDN
        del frequencyUP
        del passengerarrivalDN
        del distanceDN

        del link_traveltimeDN
        del alightrateDN
        del passengerarrivalUP
        del distanceUP

        del link_traveltimeUP
        del alightrateUP

        gc.collect()

        return (overallcost)


    if request.method == 'POST':
        conn = connpool.get_connection()
        c = conn.cursor()

        data = request.form.to_dict()
        freqUP = [data[n] for n in data if 'UP' in n]
        freqDN = [data[n] for n in data if 'DN' in n]

        query = f"SELECT Bus_service_timings_From,Bus_service_timings_To FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}' and Bus_route_name='{session['route']}'"
        df = pd.read_sql(query, conn)
        start_time = int(df.iloc[0,0][:2])
        end_time = int(df.iloc[0,1][:2])
        periods = [n for n in range(start_time,end_time)]

        print(periods,freqDN,freqUP)

        frequencyDN = pd.DataFrame({'Period': periods, 'Frequency': freqDN}) 
        frequencyUP = pd.DataFrame({'Period': periods, 'Frequency': freqUP}) 

        # c.execute('DROP TABLE IF EXISTS T_FREQUENCY')
        c.execute('CREATE TABLE IF NOT EXISTS T_FREQUENCY (Operator TEXT, Route TEXT, Type TEXT, frequencyUP TEXT, frequencyDN TEXT)')
        c.execute(f"DELETE FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
        conn.commit()
        sql = "INSERT INTO T_FREQUENCY (Operator, Route, Type, frequencyUP, frequencyDN) VALUES (%s, %s, %s, %s, %s)"
        c.execute(sql,(session['email'],session['route'],'Initial',df2b(frequencyUP),df2b(frequencyDN)))
        conn.commit()

        c.execute(f"SELECT frequencyUP,frequencyDN FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
        data = c.fetchone()
        frequencyUP = b2df(data[0])
        frequencyDN = b2df(data[1])

        frequencyDN.title = 'frequencyDN'
        frequencyUP.title = 'frequencyUP'

        files = [frequencyUP,frequencyDN]
        
        csvfiles = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in files]

        ppse='optmised frequency'
        overall_custom = overallcost(frequencyDN['Frequency'],frequencyUP['Frequency'],ppse,input_dict_UP,input_dict_DN)

        heading = f"Total Cost Using Custom Frequency ₹{overall_custom}\n"
        
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT Direction,final_costs FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' ORDER BY Direction")
        data = c.fetchall()
        final_cost_up = b2df(data[1][1])
        final_cost_up.title = data[1][0]
        final_cost_dn = b2df(data[0][1])
        final_cost_dn.title = data[0][0]
        costs = [final_cost_up, final_cost_dn]

        other_outputs = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']

        c.execute(f"SELECT {','.join(other_outputs)} from T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}'")
        other_files = c.fetchone()
        other_files = [b2df(n) for n in other_files]
        for i,n in enumerate(other_files):
            n.title = other_outputs[i]
        
        all_files = costs + other_files

        outputs = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in all_files]

        return render_template('freq_output.html', csvfiles=csvfiles, outputs=outputs, heading=heading)

    if request.method == 'GET':

        from Initial_frequency import ini_freq

        distanceDN.iloc[0,5] = 5
        distanceUP.iloc[0,5] = 5

        frequencyDN = ini_freq(passengerarrivalDN,alighting_rateDN,distanceDN,cob,dob,hrinperiod,frequencydefault,'DN')
        frequencyUP = ini_freq(passengerarrivalUP,alighting_rateUP,distanceUP,cob,dob,hrinperiod,frequencydefault,'UP')

        print(frequencyDN)

        frequencyDN = frequencyDN.to_frame()
        frequencyUP = frequencyUP.to_frame()

        frequencyDN.reset_index(inplace=True)
        frequencyUP.reset_index(inplace=True)

        frequencyDN.columns = ['Period', 'Frequency']
        frequencyUP.columns = ['Period', 'Frequency']

        # c.execute('DROP TABLE IF EXISTS T_FREQUENCY')
        c.execute('CREATE TABLE IF NOT EXISTS T_FREQUENCY (Operator TEXT, Route TEXT, Type TEXT, frequencyUP TEXT, frequencyDN TEXT)')
        c.execute(f"DELETE FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
        conn.commit()
        sql = "INSERT INTO T_FREQUENCY (Operator, Route, Type, frequencyUP, frequencyDN) VALUES (%s, %s, %s, %s, %s)"
        c.execute(sql,(session['email'],session['route'],'Initial',df2b(frequencyUP),df2b(frequencyDN)))
        conn.commit()

        c.execute(f"SELECT frequencyUP,frequencyDN FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
        data = c.fetchone()
        frequencyUP = b2df(data[0])
        frequencyDN = b2df(data[1])

        frequencyDN.title = 'frequencyDN'
        frequencyUP.title = 'frequencyUP'

        files = [frequencyUP,frequencyDN]
        
        csvfiles = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in files]

        ppse='optmised frequency'
        overall_initial = overallcost(frequencyDN['Frequency'],frequencyUP['Frequency'],ppse,input_dict_UP,input_dict_DN)

        heading = f"Total Cost Using Initial Frequency ₹{overall_initial}\n"
        
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT Direction,final_costs FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' ORDER BY Direction")
        data = c.fetchall()
        print(data)
        final_cost_up = b2df(data[1][1])
        final_cost_up.title = data[1][0]
        final_cost_dn = b2df(data[0][1])
        final_cost_dn.title = data[0][0]
        costs = [final_cost_up, final_cost_dn]

        other_outputs = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']

        c.execute(f"SELECT {','.join(other_outputs)} from T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}'")
        other_files = c.fetchone()
        other_files = [b2df(n) for n in other_files]
        for i,n in enumerate(other_files):
            n.title = other_outputs[i]
        
        all_files = costs + other_files

        outputs = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in all_files]

        return render_template('freq_output.html', csvfiles=csvfiles, outputs=outputs,heading=heading)

@app.route('/optimisation')
def optimisation():
        
    def cal_pop_fitness(pop,sol_per_pop):
        # Calculating the fitness value of each solution in the current population.
        # The fitness function calulates the sum of products between each input and its corresponding weight.
        cost_tbl=[0]*sol_per_pop
        for i in range (0,sol_per_pop):
            purpose="GA"
            cost_tbl[i]= overallcost(pop[i,0:ser_period],pop[i,ser_period:],purpose,input_dict_UP,input_dict_DN)


        fitness=np.array(cost_tbl)
        return fitness

    def select_mating_pool(pop, fitness, num_parents):
        # Selecting the best individuals in the current generation as parents for producing the offspring of the next generation.
        parents = numpy.empty((num_parents, pop.shape[1]))
        for parent_num in range(num_parents):
            max_fitness_idx = numpy.where(fitness == numpy.min(fitness))
            max_fitness_idx = max_fitness_idx[0][0]
            parents[parent_num, :] = pop[max_fitness_idx, :]
            fitness[max_fitness_idx] = 999999999
        return parents

    def crossover(parents, offspring_size):
        offspring = numpy.empty(offspring_size)
        # The point at which crossover takes place between two parents. Usually, it is at the center.
        crossover_point = numpy.uint8(offspring_size[1]/2)

        for k in range(offspring_size[0]):
            # Index of the first parent to mate.
            parent1_idx = k%parents.shape[0]
            # Index of the second parent to mate.
            parent2_idx = (k+1)%parents.shape[0]
            offspring[k, 0:crossover_point] = parents[parent1_idx, 0:crossover_point]
            offspring[k, crossover_point:] = parents[parent2_idx, crossover_point:]
        return offspring

    def mutation(offspring_crossover,frequencycomb,num_mutations=1):
        mutations_counter = numpy.uint8(offspring_crossover.shape[1] / num_mutations)
        # Mutation changes a number of genes as defined by the num_mutations argument. the genes subjected to mutation are associated with the peak hour
        for idx in range(offspring_crossover.shape[0]):
            random_position= numpy.random.randint(0,len(frequencycomb.index), int(len( frequencycomb.index)/2))
            for i in range(0,len(random_position) ):
                random_value = numpy.random.randint(frequencycomb.iloc[random_position[i],0 ],frequencycomb.iloc[random_position[i],1 ] +1 , 1)
                offspring_crossover[idx,random_position[i] ] = random_value
        return offspring_crossover

    from freq_range import freq_range

    conn = connpool.get_connection()
    c = conn.cursor()

    input_dict_UP, input_dict_DN, stop_characteristics, d_coef, ymlfile = all_input_data()

    passengerarrivalDN = input_dict_DN['passengerarrival']
    distanceDN = input_dict_DN['distance']
    timeperiodDN = input_dict_DN['timeperiod']
    link_traveltimeDN = input_dict_DN['link_traveltime']
    alighting_rateDN = input_dict_DN['alightrate']
    fareDN = input_dict_DN['fare']
    filesDN = input_dict_DN['files']
    

    # input files up direction
    passengerarrivalUP = input_dict_UP['passengerarrival']
    distanceUP = input_dict_UP['distance']
    timeperiodUP = input_dict_UP['timeperiod']
    link_traveltimeUP = input_dict_UP['link_traveltime']
    alighting_rateUP = input_dict_UP['alightrate']
    fareUP = input_dict_UP['fare']
    filesUP = input_dict_UP['files']

    data = yaml.load(ymlfile, Loader=SafeLoader)

    globals().update(data)

    dob= seatcap*min_c_lvl
    cob= int(seatcap*max_c_lvl)

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

    def cost_oned (passengerarrival,distance,frequency,timeperiod,link_traveltime,alightrate,fare, files,direcn,purpose):
        tot_dis = distance.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
        tot_dis = np.ceil(float(np.asarray(tot_dis)))

        # FIXED COST  DIRECTION per trip

        fuelcostrunning = (fuelprice * tot_dis / kmperliter).round(-2).round(0)
        maintenancecost = (tot_dis * busmaintenance).round(0)
        vehdepreciation = ((buscost / buslifecycle) * tot_dis).round(0)
        crewcost = (crewperbus * creqincome / (2 * cr_trip * cr_day))

        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        # 1. Departure time calculation
        # -------------------------------------------------------------------------------------------------------------------------------------------------------

        time_period= timeperiod.copy()
        print("time_period",time_period)
        print("frequency",frequency)
        time_period['frequency'] = np.ceil(frequency)
        time_period['Headway_in_hours'] = (1 / (frequency)).round(2)


        departuretime = pd.DataFrame()
        headway1 = pd.DataFrame()
        for ind, col in time_period.iterrows():
            if ind == 0:
                for f in range(0, int(time_period.iloc[ind, 1])):
                    departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + ((f * time_period.iloc[ind, 2]))}])], ignore_index=True)
                    headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)
            else:
                for f in range(0, int(time_period.iloc[ind, 1])):
                    if f == 0:
                        headway_avg = (time_period.iloc[ind, 2] + time_period.iloc[ind - 1, 2]) / 2
                        temp_departure = departuretime.iloc[-1, 0] + headway_avg
                        departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': temp_departure}])], ignore_index=True)
                        headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': headway_avg * 60}, ])], ignore_index=True)
                    else:
                        departuretime = pd.concat([departuretime, pd.DataFrame.from_records([{'Departure': (time_period.iloc[ind, 0]) / 100 + (f * time_period.iloc[ind, 2])}])], ignore_index=True)
                        headway1 = pd.concat([headway1, pd.DataFrame.from_records([{'Headway': time_period.iloc[ind, 2] * 60}, ])], ignore_index=True)


        # del temp_departure
        # del headway_avg


        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        #  2. Simulation of full day bus services
        # -------------------------------------------------------------------------------------------------------------------------------------------------------


        arrivalrate = passengerarrival / (hrinperiod * 60)
        # linktravel time, arrival rate, alighting rate  per trip
        link_travel_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        arrivalrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        alightrate_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        files_tr = [0] * len(departuretime.index)
        ind = -1
        time_period.index = time_period.index + 1
        for i in range(0, len(arrivalrate.index)):
            for m in range(0, int(time_period.iloc[i, 1])):
                ind = ind + 1
                for j in range(0, len(alightrate.columns)):
                    link_travel_tr.iloc[ind, j] = link_traveltime.iloc[i, j]
                    arrivalrate_tr.iloc[ind, j] = arrivalrate.iloc[i, j]
                    alightrate_tr.iloc[ind, j] = alightrate.iloc[i, j]
                    files_tr[ind] = files[i]

        p_arrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_waiting = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_alight = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_board = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        link_occp = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        waitingtime_tr = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        cost_waitingtime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_cantboard = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        p_lost = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        d_time = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        stoparrival = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        headway= pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        traveltime = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        load_fact = pd.DataFrame(index=departuretime.index, columns=arrivalrate.columns)
        invehtime = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
        cost_inveh = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_sit = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_stand = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        revenue= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns).fillna(0)
        p_cantboard_1= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_cantboard_2= pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        p_cantboard_0 = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        despatch = pd.DataFrame(index=p_arrival.index, columns=arrivalrate.columns)
        # Calculation of passenger arrival, number of boarding, number alighting, link occupancy, dwell time,passenger lost, passenger cannot board, waiting time, in vehicle travel time etc.
        # trip wise calculation for each stop

        for ind in range(0, len(departuretime.index)):
            for j in range(0, len(alightrate.columns)):
                # Travel time from stop j-1 to stop j and Arrival time of bus(ind) at stop j ---------------------

                if j == 0:
                    traveltime.iloc[ind, j] = 0

                    stoparrival.iloc[ind, j] = departuretime.iloc[ind, 0]-(headway1.iloc[ind, 0]/60)


                else:
                    # TRAVEL TIME FROM STOP J-1 TO J = DWELL TIME AT STOP J-1 + LINK RUNNING TIME (J-1,J)
                    traveltime.iloc[ind, j] = ((d_time.iloc[ind, j - 1] + link_travel_tr.iloc[ind, j]) / 60).round(4)
                    stoparrival.iloc[ind, j] = stoparrival.iloc[ind, j - 1] + traveltime.iloc[ind, j]

                # Headway Calculations of stop j --------------------------------------------------------------
                #headway1= despatch headway

                if j == 0 or ind == 0:

                    headway.iloc[ind, j] = headway1.iloc[ind, 0]
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

                p_arrival.iloc[ind, j] = np.ceil(arrivalrate_tr.iloc[ind, j] * headway.iloc[ind, j] )

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

                #  link occupancy/on board passenger of bus(ind) at stop j (Passenger on board j-1 to j)------------------------

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
                if j==0:
                    d_time.iloc[ind, j]=headway1.iloc[ind, 0]

                else:
                    d_time.iloc[ind, j] = dwell_time(j, departuretime.iloc[ind, 0], p_board.iloc[ind, j], p_alight.iloc[ind, j], load_fact.iloc[ind, j])
                # default holding--------------------------------------------------------------------
                if ind == 0 or j == (len(alightrate.columns) - 1):
                    d_holding = 0
                else:
                    # stopariival for the next stop
                    traveltime_tr = ((d_time.iloc[ind, j] + link_travel_tr.iloc[ind, j + 1]) / 60).round(4)
                    stoparrival_nxt = stoparrival.iloc[ind, j] + traveltime_tr
                    headway_temp = (stoparrival_nxt - stoparrival.iloc[ind - 1, j + 1]) * 60
                    if headway_temp < headway1.iloc[ind, 0] / 4:
                        d_holding = headway1.iloc[ind, 0] / 4 + abs(headway_temp)
                        d_time.iloc[ind, j] = d_time.iloc[ind, j] + d_holding
                    else:
                        d_holding = 0

                # Despatch time at stop j for bus ind ------------------------------------------------------------------------
                if j==0:
                    despatch.iloc[ind, j]=departuretime.iloc[ind,0]
                else:
                    despatch.iloc[ind, j] = stoparrival.iloc[ind, j] + (d_time.iloc[ind, j] / 60)

                # Revenue calculations
                if type(files_tr[ind]) is pd.DataFrame:
                    df = files_tr[ind]
                else:
                    print(type(files_tr[ind]))
                    df = pd.read_csv(files_tr[ind], index_col='Stops').fillna(0)
                for k in range(0, len(alightrate.columns)):
                    rev = p_board.iloc[ind, j] * df.iloc[j, k] * fare.iloc[j, k]
                    revenue.iloc[ind, j] = revenue.iloc[ind, j] + rev

            #---------------------------------------------------------------------
            if purpose=='GA':
                # CONSTRAINTS - TRIP WISE
                # 1.Mimimum Passenger per trip
                p_per_trip = p_arrival.iloc[ind, :].sum()
                if p_per_trip < min_ppp:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 2.Maximum percentage of passenger lost per trip(PPLPT) = 10 %
                passlosttr = p_lost.iloc[ind, :].sum()
                ppl_pt = (passlosttr / p_per_trip) * 100
                if ppl_pt > max_pplpt:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 3. Minimum revenue per trip(RVPT)
                revenue_pt = revenue.iloc[ind, :].sum()
                if revenue_pt < min_rvpt:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass

                # 4. Maximum Operation cost per trip
                tot_dwell = d_time.iloc[ind, :].sum()
                fuelcostdwell = tot_dwell * (fuelprice / 60 * kmperliter2)
                fixedcost = fuelcostrunning + fuelcostdwell + maintenancecost + vehdepreciation + crewcost
                # OPERATION COST PER TRIP=  FIXED COST PER TRIP + PASSENGER LOST PENALTY
                operation_cpt = fixedcost + (passlosttr * penalty)
                if operation_cpt > max_opc:

                    return (0, 0, 0, 0, 0, 0, 0, 0, 0)
                else:
                    pass
            else:
                pass

        # Total travel time hourly
        travel_time_tot = traveltime.sum(axis=1)
        #coverting arrival time to clock time
        stoparrivalclock= stoparrival.copy()

        for ind in range(0, len(stoparrival.index)):
            for j in range(0, len(stoparrival.columns)):
                stoparrivalclock.iloc[ind, j] = np.floor(stoparrival.iloc[ind, j]) + (
                            (stoparrival.iloc[ind, j] - (np.floor(stoparrival.iloc[ind, j]))) / 100 * 60).round(2)

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



        sum_revenue=revenue.sum(axis=1)
        sum_revenue=sum_revenue.sum()
        # TOTAL COST
        t_cost = int(Tot_cost.sum())


        if purpose=='GA':
            pass
        else:

            Totcost_waiting = Tot_trcost_waiting.sum()
            Totcost_inveh = Tot_trcost_inveh.sum()
            Totpasslost = Tot_trpasslost.sum()

            total_trips = frequency.sum()
            totalkilometrerun = total_trips * tot_dis
            fuelcostday= (fuelcostrunning* total_trips)+ fuelcostdwelling.sum()

            # user cost
            cuser = Tot_trcost_waiting + Tot_trcost_inveh + (Tot_trpasslost * c_cantboard)
            cuser = cuser.sum()
            # operator cost
            coperator = (Tot_trpasslost * penalty) + fixed_cost
            coperator = coperator.sum()

            if direcn == 'DN':

                categories = [
                    'Total waiting time cost (₹)',
                    'Total cost of in vehicle time (₹)',
                    'Total passenger lost',
                    'User Cost (₹)',
                    'Operator Penalty Cost for passenger lost (₹)',
                    'Vehcile Kilometre-run (Km)',
                    'Cost of fuel (₹)',
                    'Cost of vehicle maintenance (₹)',
                    'Vehicle depreciation cost (₹)',
                    'Crew cost (₹)',
                    'Operator Cost for bus operation (₹)',
                    'Total cost in down direction (₹)',
                ]

                values = [
                    np.ceil(Totcost_waiting),
                    np.ceil(Totcost_inveh),
                    Totpasslost,
                    cuser.round(0),
                    (Totpasslost) * (penalty),
                    totalkilometrerun,
                    np.ceil(fuelcostday),
                    maintenancecost*total_trips,
                    vehdepreciation * total_trips,
                    crewcost * total_trips,
                    np.ceil(coperator),
                    t_cost
                ]

                final_costs = pd.DataFrame({'Category': categories, 'Values': values})

                if purpose == 'optmised frequency':
                    files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                    columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                    conn = connpool.get_connection()
                    c = conn.cursor()
                    c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                    c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'DN'")
                    conn.commit()
                    sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','DN', {','.join(['%s' for n in columns[1:-4]])})"
                    c.execute(sql,(tuple([df2b(n) for n in files])))
                    conn.commit()
                else:
                    pass

            else:

                categories = [
                    'Total waiting time cost (₹)',
                    'Total cost of in vehicle time (₹)',
                    'Total passenger lost',
                    'User Cost (₹)',
                    'Operator Penalty Cost for passenger lost (₹)',
                    'Vehcile Kilometre-run (Km)',
                    'Cost of fuel (₹)',
                    'Cost of vehicle maintenance (₹)',
                    'Vehicle depreciation cost (₹)',
                    'Crew cost (₹)',
                    'Operator Cost for bus operation (₹)',
                    'Total cost in down direction (₹)',
                ]

                values = [
                    np.ceil(Totcost_waiting),
                    np.ceil(Totcost_inveh),
                    Totpasslost,
                    cuser.round(0),
                    (Totpasslost) * (penalty),
                    totalkilometrerun,
                    np.ceil(fuelcostday),
                    maintenancecost*total_trips,
                    vehdepreciation * total_trips,
                    crewcost * total_trips,
                    np.ceil(coperator),
                    t_cost
                ]

                final_costs = pd.DataFrame({'Category': categories, 'Values': values})
                
                if purpose == 'optmised frequency':
                    files = [final_costs,link_travel_tr,arrivalrate_tr,alightrate_tr,travel_time_tot,headway1,departuretime,p_arrival,p_waiting,p_alight,p_board,link_occp,waitingtime_tr,cost_waitingtime,p_cantboard,p_lost,d_time,stoparrival,headway,traveltime,load_fact,invehtime,cost_inveh,p_sit,p_stand,revenue,p_cantboard_1,p_cantboard_2,p_cantboard_0,despatch]

                    columns = ['service_params','final_costs','link_travel_tr','arrivalrate_tr','alightrate_tr','travel_time_tot','headway1','departuretime','p_arrival','p_waiting','p_alight','p_board','link_occp','waitingtime_tr','cost_waitingtime','p_cantboard','p_lost','d_time','stoparrival','headway','traveltime','load_fact','invehtime','cost_inveh','p_sit','p_stand','revenue','p_cantboard_1','p_cantboard_2','p_cantboard_0','despatch','timetable','veh_schedule','veh_sch2','veh_sch1']

                    conn = connpool.get_connection()
                    c = conn.cursor()
                    c.execute(f"CREATE TABLE IF NOT EXISTS T_INPUT_FILES_HOLDING (Operator TEXT, Route TEXT, Direction TEXT, {','.join([f'`{n}` TEXT' for n in columns])})")
                    c.execute(f"DELETE FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Direction = 'UP'")
                    conn.commit()
                    sql = f"INSERT INTO T_INPUT_FILES_HOLDING (Operator, Route, Direction, {','.join([f'`{n}`' for n in columns[1:-4]])}) VALUES ('{session['email']}','{session['route']}','UP', {','.join(['%s' for n in columns[1:-4]])})"
                    c.execute(sql,(tuple([df2b(n) for n in files])))
                    conn.commit()
                else:
                    pass



        del ind
        del Tot_d_time
        del Tot_trpasslost
        del Tot_trcost_inveh
        del Tot_trcost_waiting
        # del cw_cost
        # del residual
        # del time_period
        gc.collect()


        return (despatch,sum_revenue,fixed_cost,t_cost,departuretime,headway,p_lost, travel_time_tot,stoparrival)

    def overallcost(frequencyDN,frequencyUP,purpose,input_dict_UP,input_dict_DN):
        #1. input files down direction
        #--------------------------------------------------------
        passengerarrivalDN = input_dict_DN['passengerarrival']
        distanceDN = input_dict_DN['distance']
        timeperiodDN = input_dict_DN['timeperiod']
        link_traveltimeDN = input_dict_DN['link_traveltime']
        alightrateDN = input_dict_DN['alightrate']
        fareDN = input_dict_DN['fare']
        filesDN = input_dict_DN['files']

        # input files up direction
        passengerarrivalUP = input_dict_UP['passengerarrival']
        distanceUP = input_dict_UP['distance']
        timeperiodUP = input_dict_UP['timeperiod']
        link_traveltimeUP = input_dict_UP['link_traveltime']
        alightrateUP = input_dict_UP['alightrate']
        fareUP = input_dict_UP['fare']
        filesUP = input_dict_UP['files']

        #  Total Distance depot ot depot (down direction)
        L_DN = distanceDN.sum(axis=1, skipna=True).values  # defined Total Distance depot ot depot
        L_DN = np.ceil(float(np.asarray(L_DN)))

        #  Total Distance depot ot depot (UP direction)
        L_UP = distanceUP.sum(axis=1, skipna=True).values
        L_UP = np.ceil(float(np.asarray(L_UP)))

        # ------------------------------------------
        #2. DOWN DIRECTION
        # ------------------------------------------
        direcn = 'DN'
        despatchDN, revenueDN, fixed_costDN, cost_DN, departuretimeDN, headwayDN, pass_lost_tr_DN, travel_time_totDN, stoparrivalDN = cost_oned(
            passengerarrivalDN, distanceDN, frequencyDN, timeperiodDN, link_traveltimeDN, alightrateDN, fareDN, filesDN,direcn,purpose)

        if revenueDN ==0 and cost_DN==0:
            return (999999999)
        else:
            pass


        # ------------------------------------------
        #3. UP DIRECTION
        # ------------------------------------------
        direcn = 'UP'
        despatchUP, revenueUP, fixed_costUP, cost_UP, departuretimeUP, headwayUP, pass_lost_tr_UP, travel_time_totUP, stoparrivalUP = cost_oned(
            passengerarrivalUP, distanceUP, frequencyUP, timeperiodUP, link_traveltimeUP, alightrateUP, fareUP, filesUP,direcn,purpose)
        if revenueUP ==0 and cost_UP==0:
            return (999999999)
        else:
            pass

        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        #4. Terminal and Vehicle Scheduling
        # -------------------------------------------------------------------------------------------------------------------------------------------------------
        from terminal_vehicle_schedule import schedule
        timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1,veh_sch2,veh_schedule = schedule(slack,travel_time_totDN,departuretimeDN,departuretimeUP, travel_time_totUP,'',lay_overtime)

        overallcost = cost_DN + cost_UP


        num_tripsDN = len(departuretimeDN.index)
        num_tripsUP = len(departuretimeUP.index)
        # number of passengers served within the entire day of service
        p_arrivalDN = passengerarrivalDN.sum(axis=1)
        p_arrivalDN = p_arrivalDN.sum()
        p_arrivalUP = passengerarrivalUP.sum(axis=1)
        p_arrivalUP = p_arrivalUP.sum()

        p_arrival = p_arrivalUP + p_arrivalDN

        # total passenger lost
        passlostDN = pass_lost_tr_DN.sum(axis=1)
        passlostDN = passlostDN.sum()
        passlostUP = pass_lost_tr_UP.sum(axis=1)
        passlostUP = passlostUP.sum()
        passlost = passlostDN + passlostUP

        # fixed cost
        fixed_costDN = fixed_costDN.sum()
        fixed_costUP = fixed_costUP.sum()

        # total operator cost for full service
        OperatorCostDN = fixed_costDN + (passlostDN * penalty)
        OperatorCostUP = fixed_costUP + (passlostDN * penalty)
        OperatorCost = OperatorCostDN + OperatorCostUP

        #service level parameters
        # 1. Maximum operation cost per passenger (OPPP)
        oppp = OperatorCost / p_arrival
        # 2. Minimum passenger per vehicle-kilometer (PPVK)
        veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
        ppvk = p_arrival / veh_km
        # 3.	Minimum passenger per trip (PPT)
        # total number of passenger in down direction/ total number of trips in down direction
        pptDN = p_arrivalDN / num_tripsDN
        pptUP = p_arrivalUP / num_tripsUP
        # 4. Max operation cost per trip OCPP
        ocpp_DN = OperatorCostDN / num_tripsDN
        ocpp_UP = OperatorCostUP / num_tripsUP
        # 5. Maximum percentage of passenger lost (PPL) =10%
        ppl_DN = (passlostDN / p_arrivalDN) * 100
        ppl_UP = (passlostUP / p_arrivalUP) * 100
        # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
        revenue = revenueDN + revenueUP
        crr = revenue / OperatorCost

        #5. CONSTRAINTS
        #-----------------------------------------------------

        if purpose == 'GA':


            # 1. Maximum operation cost per passenger (OPPP)
            oppp = OperatorCost / p_arrival

            if oppp > max_oppp:

                return (999999999)
            else:
                pass

            # 2. Minimum passenger per vehicle-kilometer (PPVK)
            veh_km = (num_tripsDN * L_DN) + (num_tripsUP * L_UP)  # total vehicle-km
            ppvk = p_arrival / veh_km

            if ppvk < min_ppvk:

                return (999999999)
            else:
                pass

            # 3.	Minimum passenger per trip (PPT)
            # total number of passenger in down direction/ total number of trips in down direction
            pptDN = p_arrivalDN / num_tripsDN
            pptUP = p_arrivalUP / num_tripsUP

            if pptDN < min_ppt or pptUP < min_ppt:


                return (999999999)
            else:
                pass

            # 4. Max operation cost per trip OCPP
            ocpp_DN = OperatorCostDN / num_tripsDN
            ocpp_UP = OperatorCostUP / num_tripsUP

            if ocpp_DN > max_ocpp or ocpp_UP > max_ocpp:

                return (999999999)
            else:
                pass



            # 5. Maximum percentage of passenger lost (PPL) =10%

            ppl_DN = (passlostDN / p_arrivalDN) * 100
            ppl_UP = (passlostUP / p_arrivalUP) * 100

            if ppl_DN > max_ppl or ppl_UP > max_ppl:

                return (999999999)
            else:
                pass

            # 7. Minimum cost recovery ratio (total earnings for full day operation/ operational cost)(CRR)
            revenue = revenueDN + revenueUP
            crr = revenue / OperatorCost
            if crr < min_crr:

                return (999999999)
            else:
                pass

        else:

            categories = [
                'Operation cost per passenger (OPPP)',
                'Passenger per vehicle-kilometer (PPVK)',
                'Passenger per trip T1 to T2(PPT)',
                'Passenger per trip T2 to T1(PPT)',
                'Operation cost per trip T1 to T2',
                'Operation cost per trip T2 to T1',
                'Percentage of passenger lost T1 to T2',
                'Percentage of passenger lost T2 to T1',
                'Cost recovery ratio (total earnings for full day operation/ operational cost)'
            ]

            values = [
                oppp.round(2),
                ppvk.round(2),
                pptDN.round(2),
                pptUP.round(2),
                ocpp_DN.round(2),
                ocpp_UP.round(2),
                ppl_DN.round(2),
                ppl_UP.round(2),
                crr
            ]

            service_params = pd.DataFrame({'Category': categories, 'Values': values})

            columns = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']
            files = [service_params,timetable,veh_schedule,veh_sch2,veh_sch1]

            conn = connpool.get_connection()
            c = conn.cursor()
            sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='UP';"
            c.execute(sql,(tuple([df2b(n) for n in files])))
            sql = f"UPDATE T_INPUT_FILES_HOLDING SET {','.join([f'`{n}` = %s' for n in columns])} WHERE Operator='{session['email']}' AND Route='{session['route']}' AND Direction='DN';"
            c.execute(sql,(tuple([df2b(n) for n in files])))
            conn.commit()

            

        del frequencyDN
        del frequencyUP
        del passengerarrivalDN
        del distanceDN

        del link_traveltimeDN
        del alightrateDN
        del passengerarrivalUP
        del distanceUP

        del link_traveltimeUP
        del alightrateUP

        gc.collect()

        return (overallcost)

    from Initial_frequency import ini_freq

    distanceDN.iloc[0,5] = 5
    distanceUP.iloc[0,5] = 5

    frequencyDN = ini_freq(passengerarrivalDN,alighting_rateDN,distanceDN,cob,dob,hrinperiod,frequencydefault,'DN')
    frequencyUP = ini_freq(passengerarrivalUP,alighting_rateUP,distanceUP,cob,dob,hrinperiod,frequencydefault,'UP')

    print(frequencyDN)

    frequencyDN = frequencyDN.to_frame()
    frequencyUP = frequencyUP.to_frame()

    frequencyDN.reset_index(inplace=True)
    frequencyUP.reset_index(inplace=True)

    frequencyDN.columns = ['Period', 'Frequency']
    frequencyUP.columns = ['Period', 'Frequency']

    # c.execute('DROP TABLE IF EXISTS T_FREQUENCY')
    c.execute('CREATE TABLE IF NOT EXISTS T_FREQUENCY (Operator TEXT, Route TEXT, Type TEXT, frequencyUP TEXT, frequencyDN TEXT)')
    c.execute(f"DELETE FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
    conn.commit()
    sql = "INSERT INTO T_FREQUENCY (Operator, Route, Type, frequencyUP, frequencyDN) VALUES (%s, %s, %s, %s, %s)"
    c.execute(sql,(session['email'],session['route'],'Initial',df2b(frequencyUP),df2b(frequencyDN)))
    conn.commit()

    c.execute(f"SELECT frequencyUP,frequencyDN FROM T_FREQUENCY WHERE Operator = '{session['email']}' and Route = '{session['route']}' and Type = 'Initial'")
    data = c.fetchone()
    frequencyUP = b2df(data[0])
    frequencyDN = b2df(data[1])

    frequencyDN.title = 'frequencyDN'
    frequencyUP.title = 'frequencyUP'

    files = [frequencyUP,frequencyDN]
    
    csvfiles = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in files]

    ppse='optmised frequency'
    overall_initial = overallcost(frequencyDN['Frequency'],frequencyUP['Frequency'],ppse,input_dict_UP,input_dict_DN)

    frequencyDN = frequencyDN['Frequency']
    frequencyUP = frequencyUP['Frequency']

    frequencyDN=frequencyDN.reset_index(drop=True)
    frequencyUP=frequencyUP.reset_index(drop=True)

    print(frequencyDN)

            
    #---------------------------------------------------------------------------------------------------
    #2. FREQUENCY RANGE SETTING
    #---------------------------------------------------------------------------------------------------
    frequencyDN_min, frequencyDN_max= freq_range(passengerarrivalDN,alighting_rateDN,distanceDN,cob,dob,hrinperiod,frequencydefault)
    frequencyUP_min, frequencyUP_max= freq_range (passengerarrivalUP,alighting_rateUP,distanceUP,cob,dob,hrinperiod,frequencydefault)

    frequencyDN= pd.DataFrame({'Time Period':frequencyDN_min.index, 'Frequency Min':frequencyDN_min, 'Frequency Max':frequencyDN_max}).set_index('Time Period')
    frequencyUP= pd.DataFrame({'Time Period':frequencyUP_min.index, 'Frequency Min':frequencyUP_min, 'Frequency Max':frequencyUP_max}).set_index('Time Period')

    frequencycomb=pd.concat([frequencyDN, frequencyUP],axis=0)
    frequencycomb.reset_index(inplace=True)
    frequencycomb.drop(columns=['Time Period'], inplace=True)
    print('FREQUENCY RANGE: \n')
    print(frequencycomb)

    # exit()


    #---------------------------------------------------------------------------------------------------
    # 3.0   O P T I M I Z A T I O N

    #-------------------------------------------------------------------------------------------------------------------------------------------------------
    # 4.1 GENETIC ALGORITHM MODE
    #-------------------------------------------------------------------------------------------------------------------------------------------------------
    #length of chromosome= number of decision variables = service hours X 2
    num_weights = ser_period*2
    #number of solutions per population

    num_parents_mating =int(sol_per_pop/2)       #sol_per_pop/2

    print("\n---------------------------------------------------------------------------\nInitiating Genetic Algorithm for", A ,"to", B ,"to Optimise Overall Cost(₹)\n---------------------------------------------------------------------------")

    # Defining the population size.
    pop_size = (sol_per_pop,num_weights) # The population will have sol_per_pop (chromosome) where each chromosome has num_weights (genes).
    #Creating the initial population.
    print(frequencycomb.iloc[:,0],frequencycomb.iloc[:,1]+1,pop_size,sep='--------------------------------------------')
    new_populationDN = np.random.randint(low=frequencycomb.iloc[:,0], high=frequencycomb.iloc[:,1]+1, size=pop_size)        ## NEED TO HAVE A SYNTAX THAT GENERATE MIN FREQUENCY AND MAX FREQUENCY INSTEAD LOW AND HIGH MANUAL INPUT

    print("\nInitial population  : ", new_populationDN)
    # Measuring the fitness of each chromosome in the population.
    fitness = cal_pop_fitness(new_populationDN,sol_per_pop)
    print('cost for initial pop', fitness)

    for generation in range(num_generations):
        print("\nGeneration : ", generation)
        # Selecting the best parents in the population for mating.
        parents = select_mating_pool(new_populationDN, fitness, num_parents_mating)

        # Generating next generation using crossover.
        offspring_crossover = crossover(parents, offspring_size=(pop_size[0]-parents.shape[0], num_weights))

        # Adding some variations to the offsrping using mutation.
        offspring_mutation = mutation(offspring_crossover,frequencycomb)

        # Creating the new population based on the parents and offspring.
        new_populationDN[0:parents.shape[0], :] = parents
        new_populationDN[parents.shape[0]:, :] = offspring_mutation
        # The best result in the current iteration.
        fitness = cal_pop_fitness(new_populationDN, sol_per_pop)

        print('Cost of new population:', generation,'Generation',fitness )



    print('Final frequency population :', new_populationDN)
    print('Fitness of populationm',fitness)

    #finding out the frequency sequence with minimum cost in the final population
    final_pop=pd.DataFrame(new_populationDN)
    final_pop['Overallcost']= fitness
    min_cost_idx=final_pop[['Overallcost']].idxmin()
    min_cost_idx=min_cost_idx.iloc[0]
    FrequencyDNO= final_pop.iloc[min_cost_idx,0:ser_period]
    FrequencyUPO= final_pop.iloc[min_cost_idx,ser_period:ser_period*2]
    optimised_cost=final_pop.iloc[min_cost_idx,ser_period*2]




    frequency_set=pd.DataFrame()

    frequency_set['Time Period from'] = timeperiodUP ['Time']
    frequency_set['Time Period from']=frequency_set['Time Period from']/100

    frequency_set['Optimised Frequency down']= FrequencyDNO.values
    frequency_set['Optimised headway down']= 60/frequency_set['Optimised Frequency down']
    frequency_set['Optimised Frequency up']= FrequencyUPO.values
    frequency_set['Optimised headway up']= 60/frequency_set['Optimised Frequency up']
    print('\n ------------------------------------------------------------------')
    print('Optimisation results:')
    print('\n ------------------------------------------------------------------')
    print('Optimised frequency for full day operations:\n',frequency_set.to_string())
    print('Optimised cost=', optimised_cost)
    # #exporting output files
    # path= r'Output GA'
    # isExist = os.path.exists(path)

    # if not isExist:
    #     # Create a new directory because it does not exist
    #     os.makedirs(path)


    # final_pop.to_csv(r'Output GA\Final_pop_fitness.csv')
    # frequency_set.to_csv(r'Output GA\Optimised frequency set.csv', index=False)
    # FrequencyDNO.to_csv(r'Output GA\OpFrequencyDN.csv', index=False)
    # FrequencyUPO.to_csv(r'Output GA\OpFrequencyUP.csv', index=False)

    frequencyDN=FrequencyDNO.to_numpy()
    frequencyUP=FrequencyUPO.to_numpy()
    ppse='optmised frequency'
    overall_opt= overallcost(frequencyDN,frequencyUP,ppse,input_dict_UP,input_dict_DN)
    print('\n overall cost for the operations using optimised frequency              :₹',overall_opt)
    print('\n overall cost for the operations using initial frequency              :₹',overall_initial)
    cost_reduction= 100-(overall_opt/overall_initial*100)
    print('\n cost of reduction using optimisation:  ', cost_reduction,'%')

    heading = f"Total Cost Using Optimised Frequency ₹{overall_opt} | "
    heading += f"Total Cost Using Initial Frequency ₹{overall_initial} | "
    heading += f"Reduction Using Optimisation {cost_reduction}%"
    
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT Direction,final_costs FROM T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}' ORDER BY Direction")
    data = c.fetchall()
    print(data)
    final_cost_up = b2df(data[1][1])
    final_cost_up.title = data[1][0]
    final_cost_dn = b2df(data[0][1])
    final_cost_dn.title = data[0][0]
    costs = [final_cost_up, final_cost_dn]

    other_outputs = ['service_params','timetable','veh_schedule','veh_sch2','veh_sch1']

    c.execute(f"SELECT {','.join(other_outputs)} from T_INPUT_FILES_HOLDING WHERE Operator = '{session['email']}' and Route = '{session['route']}'")
    other_files = c.fetchone()
    other_files = [b2df(n) for n in other_files]
    for i,n in enumerate(other_files):
        n.title = other_outputs[i]
    
    all_files = costs + other_files

    outputs = [list([n.title]) + list([tuple(n.columns)]) + list(n.itertuples(index=False, name=None)) for n in all_files]

    return render_template('freq_output.html', csvfiles=csvfiles, outputs=outputs,heading=heading)

def open_browser():
    webbrowser.open_new("http://localhost:8080/")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    socketio.run(app, host="0.0.0.0", port=8080)
    # app.run(debug=True)
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=8080) # http://localhost:8080/


