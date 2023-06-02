import csv
import pandas as pd
import numpy as np
from flask import Flask, render_template, make_response,request, Response, session, redirect, jsonify
import os
import re
import datetime
import io
from io import BytesIO
import pymysql
import yaml
from flask import send_file  
from flask_session import Session
import time
import secrets
 
app = Flask(__name__)

app.secret_key = os.urandom(24)

# Connect to phpMyAdmin Database
conn = pymysql.connect(host="103.21.58.10",
                       user="pubbsm8z",
                       password="Matrix__111",
                       database="pubbsm8z_uba",
                       port = 3306
                       )

# LOGGING IN ======================================================================================================================================

# Create a User Login and Register Page
@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if 'email' in session:
        return render_template('only_busroute.html')
    else:
        return render_template('login1.html', message = message)
    
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' in session:
        return render_template('only_busroute.html')
    else:
        return redirect('/login')
    
@app.route('/loggedin', methods = ['GET', 'POST'])
def loggedin():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
        user = c.fetchone()
        if user:
            session['email'] = user[1]
            session['password'] = user[2]
            message = 'Logged in successfully !'
            return redirect('/home')
        else:
            message = 'Please enter correct email / password !'
        return render_template('login1.html', message = message)

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
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE email = % s', (email, ))
        account = c.fetchone()
        if account:
            message = 'Account already exists !'
            return render_template('register1.html', message = message)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address !'
            return render_template('register1.html', message = message)
        elif not name or not password or not email:
            message = 'Please fill out the form !'
            return render_template('register1.html', message = message)
        else:
            c.execute('INSERT INTO user (name, email, password) VALUES (% s, % s, % s)', (name, email, password, ))
            conn.commit()
            message = 'You have successfully registered ! Please Login'
            return render_template('register1.html', message = message)

# DATA ENTRY================================================================================================================

@app.route('/bus-route', methods=['GET', 'POST'])
def busroute():
    if request.method == "POST":
        if 'periods' not in session:
            session['periods'] = int(request.form['Number_of_service_periods'])
        if 'route' not in session:
                session['route'] = request.form['Bus_route_name']

        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS T_PARAMETERS (Operator TEXT,Route TEXT,A VARCHAR(50), B VARCHAR(50), frequencydefault FLOAT, seatcap FLOAT, \
                  min_c_lvl FLOAT, max_c_lvl FLOAT, max_wait FLOAT, bus_left FLOAT, min_dwell FLOAT, slack FLOAT, lay_overtime FLOAT, \
                  buscost FLOAT, buslifecycle FLOAT, crewperbus FLOAT, creqincome FLOAT, cr_trip FLOAT, cr_day FLOAT, \
                  busmaintenance FLOAT, fuelprice FLOAT, kmperliter FLOAT, kmperliter2 FLOAT, c_cantboard FLOAT, c_waittime FLOAT, \
                  c_invehtime FLOAT, penalty FLOAT, hrinperiod FLOAT, ser_period FLOAT, dead_todepot_t1 FLOAT, dead_todepot_t2 FLOAT, \
                  layover_depot FLOAT, start_ser FLOAT, end_ser FLOAT, shift FLOAT, max_ideal FLOAT, sol_per_pop FLOAT, \
                  num_generations FLOAT, max_oppp FLOAT, min_ppvk FLOAT, min_ppt FLOAT, max_ocpp FLOAT, max_fleet FLOAT, \
                  max_ppl FLOAT, min_crr FLOAT, min_ppp FLOAT, max_pplpt FLOAT, min_rvpt FLOAT, max_opc FLOAT);")
        conn.commit()
        
        c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
        record = c.fetchall()
        if not record:
            c.execute(f"INSERT INTO T_PARAMETERS (Operator,Route) VALUES ('{session['email']}','{session['route']}')")
            conn.commit()

        return render_template('only_busroute.html', message="Bus Route info was saved")
    return render_template('only_busroute.html', message="")

@app.route('/stops', methods=['GET', 'POST'])
def stop_details():
    return render_template('only_stops.html', message="")

@app.route('/build-route', methods=['GET', 'POST'])
def route_details():
    return render_template('only_route.html', message="")

@app.route('/stop-char', methods=['GET', 'POST'])
def stop_char():
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
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
            c = conn.cursor()
            query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,\
                    Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN,Before_Int BOOLEAN, \
                    Far_From_Int BOOLEAN, Commercial FLOAT, Transport_Hub FLOAT, Bus_bay BOOLEAN,Stop_rad FLOAT, PRIMARY KEY (id));"
            c.execute(query)
            conn.commit()

            c = conn.cursor()
            for n in range(len(stops)):
                c.execute(f"UPDATE T_STOPS_INFO SET Before_Int = {before_int[n]}, Far_From_Int = {far_from_int[n]} , Commercial = \
                        '{commercial[n]}' , Transport_Hub = '{transport_hub[n]}' , Bus_bay = {bus_bay[n]} , Stop_rad = '{stop_rad[n]}'\
                         WHERE id = '{stop_ids[n]}';")
                conn.commit()
            return render_template('only_stopchar.html',stops=stops, stop_ids=stop_ids, message="Data was Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor()
            c.execute(f"SELECT s.Before_Int,s.Far_From_Int,s.Commercial,s.Transport_Hub,s.Bus_bay,s.Stop_rad FROM T_STOPS_INFO AS s INNER JOIN T_ROUTE_INFO AS r ON (s.id = r.Stop_id) WHERE s.id IN {tuple(stop_ids)} ORDER BY r.Stop_Num")
            data= c.fetchall()
            # return str(data)
            return render_template('only_stopchar.html',stops=stops, stop_ids=stop_ids, message="Data was updated from DB", data=data)

    return render_template('only_stopchar.html',stops=stops,stop_ids=stop_ids, message="")


@app.route('/table', methods=['GET', 'POST'])
def table_details():
    c = conn.cursor()
    c.execute(f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_Num INT,Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, UP_Dist FLOAT, DN_Dist FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN);")
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    if stops_list and 'periods' in session:
        message=None
        return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), message=message)
    elif stops_list:
        message = "Enter Route Information First"
        return render_template('only_table.html', stops_list=stops_list, rows=0, message=message)
    elif 'periods' in session:
        message = "Enter Stops Information First"
        return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), message=message)
    else:
        message = "Enter Route and Stops Information First"
        return render_template('only_table.html', stops_list=[], rows=0, message=message)

@app.route('/ols', methods=['GET', 'POST'])
def ols_details():
    if request.method == "POST":
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"CREATE TABLE IF NOT EXISTS T_OLS_COEFF (Operator TEXT,Route TEXT,Const FLOAT,No_of_Boarding FLOAT, No_of_Alighting FLOAT, Occupancy_Level FLOAT, Morning_Peak FLOAT, Before_Intersection FLOAT,Far_from_Intersection FLOAT,Commercial FLOAT,Transport_hub FLOAT,Bus_Bay FLOAT);")
            conn.commit()

            c.execute(f"DELETE FROM T_OLS_COEFF WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            c.execute(f"INSERT INTO T_OLS_COEFF (Operator,Route,Const,No_of_Boarding,No_of_Alighting,Occupancy_Level,Morning_Peak,Before_Intersection,Far_from_Intersection,Commercial,Transport_hub,Bus_Bay) VALUES ('{session['email']}','{session['route']}','{request.form['Const']}','{request.form['No_of_Boarding']}','{request.form['No_of_Alighting']}','{request.form['Occupancy_Level']}','{request.form['Morning_Peak']}','{request.form['Before_Intersection']}','{request.form['Far_from_Intersection']}','{request.form['Commercial']}','{request.form['Transport_hub']}','{request.form['Bus_Bay']}')")
            conn.commit()
            return render_template('only_ols.html', message="Data was Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_OLS_COEFF WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_ols.html', message="Data was Retrieved", data=data[0])
    else:
        return render_template('only_ols.html', message="")

@app.route('/scheduling', methods=['GET', 'POST'])
def scheduling_details():
    if request.method == "POST":
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET dead_todepot_t1 = '{request.form['dead_todepot_t1']}', dead_todepot_t2 = '{request.form['dead_todepot_t2']}', layover_depot = '{request.form['layover_depot']}', start_ser = '{request.form['start_ser']}', end_ser = '{request.form['end_ser']}', shift = '{request.form['shift']}', max_ideal = '{request.form['max_ideal']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_scheduling.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_scheduling.html', message="Saved",data=data[0])
    else:
        return render_template('only_scheduling.html', message="")

@app.route('/constraints', methods=['GET', 'POST'])
def constraints_details():
    if request.method == "POST":
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET max_oppp = '{request.form['max_oppp']}', min_ppvk = '{request.form['min_ppvk']}', min_ppt = '{request.form['min_ppt']}', max_ocpp = '{request.form['max_ocpp']}', max_fleet = '{request.form['max_fleet']}', max_ppl = '{request.form['max_ppl']}', min_crr = '{request.form['min_crr']}', min_ppp = '{request.form['min_ppp']}', max_pplpt = '{request.form['max_pplpt']}', min_rvpt = '{request.form['min_rvpt']}', max_opc = '{request.form['max_opc']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_constraints.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_constraints.html', message="Saved",data=data[0])
    else:
        return render_template('only_constraints.html', message="")

@app.route('/service', methods=['GET', 'POST'])
def service_details():
    if request.method == "POST":
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET A = '{request.form['A']}', B = '{request.form['B']}', frequencydefault = '{request.form['frequencydefault']}', seatcap = '{request.form['seatcap']}', min_c_lvl = '{request.form['min_c_lvl']}', max_c_lvl = '{request.form['max_c_lvl']}', max_wait = '{request.form['max_wait']}', bus_left = '{request.form['bus_left']}', min_dwell = '{request.form['min_dwell']}', slack = '{request.form['slack']}', lay_overtime = '{request.form['lay_overtime']}', buscost = '{request.form['buscost']}', buslifecycle = '{request.form['buslifecycle']}', crewperbus = '{request.form['crewperbus']}', creqincome = '{request.form['creqincome']}', cr_trip = '{request.form['cr_trip']}', cr_day = '{request.form['cr_day']}', busmaintenance = '{request.form['busmaintenance']}', fuelprice = '{request.form['fuelprice']}', kmperliter = '{request.form['kmperliter']}', kmperliter2 = '{request.form['kmperliter2']}', c_cantboard = '{request.form['c_cantboard']}', c_waittime = '{request.form['c_waittime']}', c_invehtime = '{request.form['c_invehtime']}', penalty = '{request.form['penalty']}', hrinperiod = '{request.form['hrinperiod']}', ser_period = '{request.form['ser_period']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_service.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_service.html', message="Saved",data=data[0])
    else:
        return render_template('only_service.html', message="")

@app.route('/ga-params', methods=['GET', 'POST'])
def ga_params():
    if request.method == "POST":
        if 'save' in request.form:
            c = conn.cursor()
            c.execute(f"UPDATE T_PARAMETERS SET sol_per_pop = '{request.form['sol_per_pop']}', num_generations = '{request.form['num_generations']}' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
            conn.commit()
            return render_template('only_gaparams.html', message="Saved")
        elif 'getfromdb' in request.form:
            c = conn.cursor(pymysql.cursors.DictCursor)
            c.execute(f"SELECT * FROM T_PARAMETERS WHERE Route = '{session['route']}' and Operator = '{session['email']}'")
            data = c.fetchall()
            return render_template('only_gaparams.html', message="Saved",data=data[0])
    else:
        return render_template('only_gaparams.html', message="")

# @app.route('/points', methods=['GET', 'POST'])
# def point_details():
#     return render_template('only_points.html', message="")

@app.route('/data')
def get_data():
    c = conn.cursor()
    c.execute(f"SELECT id,Stop_Name,Stop_Lat,Stop_Long FROM T_STOPS_INFO WHERE Operator = '{session['email']}'")
    stops_list= c.fetchall()
    data = []
    for n in stops_list:
        data.append({"id":n[0],"name": n[1], "lat": n[2], "lng": n[3]})
    # data = [
    #     {"name": "Point 1", "lat": 51.505, "lng": -0.09},
    #     {"name": "Point 2", "lat": 51.51, "lng": -0.1},
    #     {"name": "Point 3", "lat": 51.505, "lng": -0.11}
    # ]
    return jsonify(data)

# @app.route('/input-stops', methods=['GET', 'POST'])
# def input_stops():
#     if 'periods' not in session:
#         session['periods'] = int(request.form['Number_of_service_periods'])
#     if 'route' not in session:
#             session['route'] = request.form['Bus_route_name']
#     from_time = request.form['Bus_service_timings_From']
#     to_time = request.form['Bus_service_timings_To']
#     return render_template('only_stops.html')

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
    c = conn.cursor()

    query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,\
            Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN,Before_Int BOOLEAN, \
            Far_From_Int BOOLEAN, Commercial FLOAT, Transport_Hub FLOAT, Bus_bay BOOLEAN,Stop_rad FLOAT, PRIMARY KEY (id));"
    c.execute(query)
    conn.commit()

    c = conn.cursor()
    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_STOPS_INFO (uid,Operator,Stop_Name,Stop_Lat,Stop_Long,Dummy,Cong_Int) VALUES \
                  ('{uid}','{session['email']}','{stops_list[n]}','{latitudes[n]}','{longitudes[n]}',{is_dummy[n]},\
                  {is_intersection[n]});")
        conn.commit()

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
    c = conn.cursor()
    query = f"CREATE TABLE IF NOT EXISTS T_ROUTE_INFO (id INT NOT NULL AUTO_INCREMENT,uid VARCHAR(50),Operator TEXT,Route TEXT,Stop_Num INT,Stop_id INT,UP_Dist FLOAT, DN_Dist FLOAT,PRIMARY KEY (id),FOREIGN KEY (Stop_id) REFERENCES T_STOPS_INFO(id) );"
    c.execute(query)
    conn.commit()

    c = conn.cursor()
    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_ROUTE_INFO (uid,Operator,Route,Stop_Num,Stop_id,UP_Dist,DN_Dist) VALUES ('{uid}','{session['email']}','{session['route']}','{n+1}','{stop_ids[n]}','{up_distances[n]}','{dn_distances[n]}');")
        conn.commit()

    c = conn.cursor()
    c.execute(f"DELETE FROM T_ROUTE_INFO WHERE Route = '{session['route']}' and Operator = '{session['email']}' and uid != '{uid}';")
    conn.commit()
    return render_template('only_table.html', stops_list=session['stops_list'], rows=list(range(1,session['periods']+1)))

@app.route('/table-selected', methods=['GET', 'POST'])
def table_selected():
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    table = request.form.get("db_table")
    if table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN", "T_Alighting_Rate_UP", "T_Alighting_Rate_DN"]:
        return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), selected_table=table)
    elif table in ["T_Fare_DN","T_Fare_UP","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        return render_template('only_table.html', stops_list=stops_list, rows=stops_list, selected_table=table)


@app.route('/table-filled', methods=['GET', 'POST'])
def table_filled():
    # Get filled data
    data = request.form.to_dict()
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    # Upload to Database
    c = conn.cursor()
    db_table = request.form['selected_table']
    c.execute(f"DROP TABLE IF EXISTS {db_table}")
    query = f"CREATE TABLE IF NOT EXISTS {db_table} (Operator TEXT,Route TEXT,Rows TEXT,{','.join([f'`Stop {n+1}` FLOAT' for n in range(30)])});"
    c.execute(query)
    c.execute(f"DELETE FROM {db_table} WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
    
    if db_table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN", "T_Alighting_Rate_UP", "T_Alighting_Rate_DN"]:
        rows=list(range(1,session['periods']+1))
    elif db_table in ["T_Fare_DN","T_Fare_UP","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        rows=stops_list
    
    for p in rows:
        query = f"INSERT INTO {db_table} (Operator,Route,Rows,{','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])}) VALUES ('{session['email']}','{session['route']}','{p}',{','.join(['%s' for n in range(len(stops_list))])});"
        print(query)
        row = []
        for s in stops_list:
            row.append(float(data[f"{s}_{p}"]))
            print(row, f"{s}_{p}")
        print(query)
        c.execute(query, tuple(row))
        conn.commit()
        row = []
    table = request.form.get("selected_table")
    if table in ["T_Passenger_Arrival_UP", "T_Passenger_Arrival_DN", "T_Alighting_Rate_UP", "T_Alighting_Rate_DN"]:
        return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), selected_table=table)
    elif table in ["T_Fare_DN","T_Fare_UP","T_TravelTimeDN_ANN","T_TraveTimeUP_ANN"]:
        return render_template('only_table.html', stops_list=stops_list, rows=stops_list, selected_table=table)
    # return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)),selected_table=request.form.get('selected_table'))

# new
@app.route('/clear-table', methods=['GET', 'POST'])
def clear_table():
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)),selected_table=request.form.get('selected_table'))

# new
@app.route('/retrieve-data', methods=['GET', 'POST'])
def retrieve_data():
    # Retrieve from Database
    db_table = request.form['selected_table']
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    c.execute(f"SELECT {','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])} FROM {db_table} WHERE Operator = '{session['email']}' and Route='{session['route']}' ORDER BY Rows")
    db_data= c.fetchall()
    if len(db_data) != session['periods']:
        return "The specified number of periods don't match the data from the database. Please check and try again."
    if len(db_data[0]) != len(stops_list):
        return "The specified number of stops don't match the data from the database. Please check and try again."
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), db_data=db_data,selected_table=request.form.get('selected_table'))

# new
@app.route('/upload-csv-data', methods=['GET', 'POST'])
def upload_csv_data():
    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))

    csvdata = request.files['csvfile'].read()
    csvdata = pd.read_csv(BytesIO(csvdata))
    csvdata = list(csvdata.itertuples(index=False, name=None))
    if len(csvdata) != session['periods']:
        return "The specified number of periods don't match the csv data uploaded. Please check and try again."
    if len(csvdata[0]) != len(stops_list):
        return "The specified number of stops don't match the csv data uploaded. Please check and try again."
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), db_data=csvdata,selected_table=request.form.get('selected_table'))

# new
@app.route('/download-csv-data', methods=['GET', 'POST'])
def download_csv_data():
    # Retrieve from Database
    data = request.form.to_dict()

    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))

    # Write csv
    csv = ""
    csv += ','.join(stops_list) + '\n'
    for p in range(session['periods']):
        row = []
        for s in stops_list:
            row.append(float(data[f"{s}_{p+1}"]))
        row = ','.join([str(n) for n in row])
        csv += row + '\n'

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=myplot.csv"})

if __name__ == '__main__':
    app.run(debug=True)
