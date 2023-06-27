# import csv
# import numpy as np
# import time
# import datetime
# import io
# from flask_session import Session
import yaml
from io import BytesIO, StringIO
import pymysqlpool
import pymysql
import secrets
import pandas as pd
import numpy as np
from flask import Flask, render_template, make_response,request, Response, session, redirect, jsonify,url_for,send_file
from flask_socketio import SocketIO, send, emit, join_room, leave_room

import os
import re
import zipfile
import webbrowser
from threading import Timer
from yaml.loader import SafeLoader

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
                       size=3
                       )
conn = connpool.get_connection()
conn1 = connpool.get_connection()
conn2 = connpool.get_connection()


def odalight(files):
    od1 = files[1]

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

@app.route('/route-data')
def get_route_data():
    conn1 = connpool.get_connection()
    c = conn1.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name,s.Stop_Lat,s.Stop_Long FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops_list= c.fetchall()
    data = []
    for n in stops_list:
        data.append({"id":n[0],"name": n[1], "lat": n[2], "lng": n[3]})
    return jsonify(data)

@app.route('/status-display')
def get_status():
    conn2 = connpool.get_connection()
    query = f"SELECT `Route Details`,`Build Route`,`Stop Characteristics`,`Passenger Arrival`,`Fare`,`Travel Time`,`OD Data`,`OLS Details`,`Constraints`,`Service Details`,`GA Parameters`,`Scheduling Details`,`Scheduling Files`,`Bus Details`,`Depot Details` FROM T_STATUS WHERE Route = '{session['route']}' and Operator = '{session['email']}';"
    df = pd.read_sql(query, conn2)
    df = df.fillna(0)
    freq_value = df.iloc[:,:11].sum(axis=1)
    sched_value = df.iloc[:,11:].sum(axis=1)
    df.insert(11,'Frequency',freq_value)
    df.insert(16,'Scheduling',sched_value)
    df = df.fillna(0)
    if df.empty:
        data = {"Route Details":0,"Build Route":0,"Stop Characteristics":0,"Passenger Arrival":0,"Fare":0,"Travel Time":0,"OD Data":0,"OLS Details":0,"Constraints":0,"Service Details":0,"GA Parameters":0,"Frequency":0,"Scheduling Details":0,"Scheduling Files":0,"Bus Details":0,"Depot Details":0}
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
        return render_template('only_stopchar.html',stops=stops,stop_ids=stop_ids, message="Fill or Update Details", data=data)
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
    # return render_template('only_table.html', stops_list=session['stops_list'], rows=list(range(session['p_start'],session['p_end'])),periods=list(range(session['p_start'],session['p_end'])))
    return redirect('/build-route')

@app.route('/table-selected', methods=['GET', 'POST'])
def table_selected():
    conn = connpool.get_connection()
    c = conn.cursor()
    c.execute(f"SELECT s.id,s.Stop_Name FROM T_ROUTE_INFO AS r INNER JOIN T_STOPS_INFO AS s ON (s.id = r.Stop_id) WHERE r.Operator = '{session['email']}' and r.Route='{session['route']}' ORDER BY r.Stop_num")
    stops= c.fetchall()
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
    conn = connpool.get_connection()
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
    csv += ','.join(stops_list) + '\n'
    for r in rows:
        row = []
        for s in stop_ids:
            row.append(float(data[f"{s}_{r}"]))
        row = ','.join([str(n) for n in row])
        csv += row + '\n'

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
        buslist = ','.join(request.form.values())
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"CREATE TABLE IF NOT EXISTS T_BUSES (Operator TEXT, Buses TEXT);")
        c.execute(f"DELETE FROM T_BUSES WHERE Operator = '{session['email']}'")
        c.execute(f"INSERT INTO T_BUSES (Operator, Buses) VALUES ('{session['email']}','{buslist}')")
        c.execute(f"UPDATE T_STATUS SET `Bus Details` = '1' WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        conn.commit()
        c.execute(f"SELECT BUSES FROM T_BUSES WHERE Operator = '{session['email']}'")
        busnames = c.fetchone()
        busnames = busnames[0].split(',')
        return render_template('only_buses.html',buses=buses,message="Saved",busnames=busnames)
    return render_template('only_buses.html',buses=buses)

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
    if method == "Choose":
        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS T_ONLY_ROUTES (Operator TEXT,Bus_route_name TEXT,Terminal_1_origin TEXT,Terminal_2_destination TEXT,Bus_service_timings_From TEXT,Bus_service_timings_To TEXT,Number_of_service_periods TEXT)")
        c.execute(f"SELECT DISTINCT Bus_route_name FROM T_ONLY_ROUTES WHERE Operator = '{session['email']}'")
        data = c.fetchall()
        routes = [n[0] for n in data]
        return render_template('run_scheduling.html',routes=routes)
    else:
        query = f"SELECT * FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{session['route']}'"
        df = pd.read_sql(query, conn)
        ymlfile = yaml.dump(df.to_dict(orient='records')[0],default_flow_style=None)
        

        # with open(ymlfile,'r') as f:
        data = yaml.load(ymlfile, Loader=SafeLoader)

        globals().update(data)

        conn = connpool.get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{session['route']}' and Operator = '{session['email']}';")
        files = c.fetchone()

        departuretimeDN = pd.read_csv(StringIO(files[2]))
        departuretimeUP = pd.read_csv(StringIO(files[3]))
        terminalarrivalDN = pd.read_csv(StringIO(files[4]))
        terminalarrivalDN = terminalarrivalDN.iloc[:, 0]
        terminalarrivalUP = pd.read_csv(StringIO(files[5]))
        terminalarrivalUP = terminalarrivalUP.iloc[:, 0]
        travel_time_totDN = pd.read_csv(StringIO(files[6]))
        travel_time_totUP = pd.read_csv(StringIO(files[7]))

        if method == 'Multiline':
            r1_dtimeDN = pd.read_csv(StringIO(files[2]))
            r1_dtimeUP = pd.read_csv(StringIO(files[3]))
            r1_tarrivalDN = pd.read_csv(StringIO(files[4]))
            r1_tarrivalDN = r1_tarrivalDN.iloc[:, 0]
            r1_tarrivalUP = pd.read_csv(StringIO(files[5]))
            r1_tarrivalUP = r1_tarrivalUP.iloc[:, 0]
            r1_ttDN = pd.read_csv(StringIO(files[6]))
            r1_ttUP = pd.read_csv(StringIO(files[7]))

            query = f"SELECT A,B,dead_todepot_t1,dead_todepot_t2 FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route = '{session['route']}'"
            c.execute(query)
            d1 = c.fetchone()
            data.update(A1=d1[0],B1=d1[1],dead_todepot_r1t1=d1[2],dead_todepot_r1t2=d1[3])

            query = f"SELECT A,B,dead_todepot_t1,dead_todepot_t2 FROM T_PARAMETERS WHERE Operator = '{session['email']}' and Route ='{request.form['second_route']}'"
            c.execute(query)
            d2 = c.fetchone()
            data.update(A2=d2[0],B2=d2[1],dead_todepot_r2t1=d2[2],dead_todepot_r2t2=d2[3])

            c.execute(f"SELECT * FROM T_SCHEDULING_FILES WHERE Route = '{request.form['second_route']}' and Operator = '{session['email']}';")
            files = c.fetchone()

            r2_dtimeDN = pd.read_csv(StringIO(files[2]))
            r2_dtimeUP = pd.read_csv(StringIO(files[3]))
            r2_tarrivalDN = pd.read_csv(StringIO(files[4]))
            r2_tarrivalDN = r2_tarrivalDN.iloc[:, 0]
            r2_tarrivalUP = pd.read_csv(StringIO(files[5]))
            r2_tarrivalUP = r2_tarrivalUP.iloc[:, 0]
            r2_ttDN = pd.read_csv(StringIO(files[6]))
            r2_ttUP = pd.read_csv(StringIO(files[7]))

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

        
        sche_out = BytesIO()
        with zipfile.ZipFile(sche_out, 'w') as sche_zip:
            sche_zip.writestr(f'vehicle_schedule_{method}.csv',veh_schedule.to_csv())
            sche_zip.writestr(f'crew_scheduling_{method}.csv', crew.to_csv(index=False))
            sche_zip.writestr(f'Bus_utility_details_{method}.csv', bus_details.to_csv(index=False))
            sche_zip.writestr(f'Reuse_{method}.csv', reuse_buses.to_csv(index=False))
            sche_zip.writestr(f'fleet_shift_details_{method}.csv', fleet.to_csv(index=False))
            if method == 'Multiline':
                sche_zip.writestr(f'Time_Table_1_{method}.csv', r1_timetable.to_csv(index=False))
                sche_zip.writestr(f'Time_Table_2_{method}.csv', r2_timetable.to_csv(index=False))
                for i in range(0, len(b_lst.index)):
                    df3 = veh_schedule[(veh_schedule['bus_name'] == b_lst.iloc[i, 0])].copy()
                    df3.reset_index(drop=True, inplace=True)
                    name = b_lst.iloc[i, 0]
                    sche_zip.writestr(f'vehicleschedule/{name}.csv', df3.to_csv())
            else:
                sche_zip.writestr(f'Time_Table_{method}.csv', timetable.to_csv(index=False))
                sche_zip.writestr(f'depot_shift_details_{method}.csv', depot_tt.to_csv(index=False))
                for n in vehicleschedule:
                    sche_zip.writestr(f'vehicleschedule/{n.title}.csv', n.to_csv())
            # if method != 'Random':
            #     buf = BytesIO()
            #     fig.savefig(buf,dpi=300)
            #     sche_zip.writestr(f'vehicle_schedule_visual_{method}.pdf',buf.getvalue())
            # elif method == 'Random':
            #     from Timetable_Random import vehiclesched
            #     fig=vehiclesched(departuretimeDN,departuretimeUP,timetable,depot_tt,laydf1)
            #     buf = BytesIO()
            #     fig.savefig(buf,dpi=300)
            #     sche_zip.writestr(f'vehicle_schedule_visual_{method}.pdf',buf.getvalue())
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

        sche_out.seek(0)
        return send_file(sche_out, download_name=f'{method} Output.zip', as_attachment=True)

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
    emit('receivedlocation',data,room=room)
    print(str(data))

def open_browser():
    webbrowser.open_new("http://localhost:8080/")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    socketio.run(app, host="0.0.0.0", port=8080)
    # app.run(debug=True)
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=8080) # http://localhost:8080/


