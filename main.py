import csv
import pandas as pd
import numpy as np
from flask import Flask, render_template, make_response,request, Response, session, redirect
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
        return render_template('only_project.html')
    else:
        return render_template('login1.html', message = message)
    

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('password', None)
    return redirect('/home')

@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if 'email' in session:
        return render_template('index.html')
    else:
        return render_template('register1.html', message = message)

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


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' in session:
        return render_template('only_project.html')
    else:
        return redirect('/login')

# DATA ENTRY================================================================================================================

@app.route('/', methods=['GET', 'POST'])
def create_project():
    if request.method == 'POST':
        if 'project' not in session:    
            session['project'] = request.form['Project_name']
    return render_template('only_project.html', message="Project Created Successfully")

@app.route('/route', methods=['GET', 'POST'])
def route_details():
    return render_template('only_route.html', message="")

@app.route('/stops', methods=['GET', 'POST'])
def stop_details():
    return render_template('only_stops.html', message="")

@app.route('/table', methods=['GET', 'POST'])
def table_details():
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
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

@app.route('/input-stops', methods=['GET', 'POST'])
def input_stops():
    if 'periods' not in session:
        session['periods'] = int(request.form['Number_of_service_periods'])
    return render_template('only_stops.html')

# new
@app.route('/save-stops', methods=['POST'])
def save_stops():
    # A unique id for the current user and the current project
    uid = secrets.token_hex(12)
    
    # Form data
    stops = request.form.to_dict()
    stops_list = [stops[n] for n in stops if '_Name' in n]
    session['stops_list'] = stops_list
    up_distances = [stops[n] for n in stops if '_UP' in n]
    dn_distances = [stops[n] for n in stops if '_DN' in n]
    latitudes = [stops[n] for n in stops if '_lat' in n]
    longitudes = [stops[n] for n in stops if '_lng' in n]
    is_dummy = [True if f"{n}_Dummy" in stops else False for n in stops_list]
    is_intersection = [True if f"{n}_Cong" in stops else False for n in stops_list]

    # # Upload to Database
    # c = conn.cursor()
    # query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (uid VARCHAR(50),User TEXT,Project TEXT,Stop_Num INT,Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, UP_Dist FLOAT, DN_Dist FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN);"
    # c.execute(query)
    # conn.commit()

    c = conn.cursor()
    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_STOPS_INFO (uid,User,Project,Stop_Num,Stop_Name,Stop_Lat,Stop_Long,UP_Dist,DN_Dist,Dummy,Cong_Int) VALUES ('{uid}','{session['email']}','{session['project']}','{n+1}','{stops_list[n]}','{latitudes[n]}','{longitudes[n]}','{up_distances[n]}','{dn_distances[n]}',{is_dummy[n]},{is_intersection[n]});")
        conn.commit()

    c = conn.cursor()
    c.execute(f"DELETE FROM T_STOPS_INFO WHERE Project = '{session['project']}' and User = '{session['email']}' and uid != '{uid}';")
    conn.commit()
    return render_template('only_table.html', stops_list=session['stops_list'], rows=list(range(1,session['periods']+1)))

@app.route('/table-selected', methods=['GET', 'POST'])
def table_selected():
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
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
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    # Upload to Database
    c = conn.cursor()
    db_table = request.form['selected_table']
    query = f"CREATE TABLE IF NOT EXISTS {db_table} (User TEXT,Project TEXT,Period INT,{','.join([f'`Stop {n+1}` FLOAT' for n in range(30)])});"
    c.execute(query)
    c.execute(f"DELETE FROM {db_table} WHERE Project = '{session['project']}' and User = '{session['email']}';")
    for p in range(session['periods']):
        query = f"INSERT INTO {db_table} (User,Project,Period,{','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])}) VALUES ('{session['email']}','{session['project']}','{p+1}',{','.join(['%s' for n in range(len(stops_list))])});"
        print(query)
        row = []
        for s in stops_list:
            row.append(float(data[f"{s}_{p+1}"]))
            print(row, f"{s}_{p+1}")
        print(query)
        c.execute(query, tuple(row))
        conn.commit()
        row = []

    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)))

# new
@app.route('/clear-table', methods=['GET', 'POST'])
def clear_table():
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)))

# new
@app.route('/retrieve-data', methods=['GET', 'POST'])
def retrieve_data():
    # Retrieve from Database
    db_table = request.form['db_table']
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    c.execute(f"SELECT {','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])} FROM {db_table} WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Period")
    db_data= c.fetchall()
    if len(db_data) != session['periods']:
        return "The specified number of periods don't match the data from the database. Please check and try again."
    if len(db_data[0]) != len(stops_list):
        return "The specified number of stops don't match the data from the database. Please check and try again."
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), db_data=db_data)

# new
@app.route('/upload-csv-data', methods=['GET', 'POST'])
def upload_csv_data():
    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))

    csvdata = request.files['csvfile'].read()
    csvdata = pd.read_csv(BytesIO(csvdata))
    csvdata = list(csvdata.itertuples(index=False, name=None))
    if len(csvdata) != session['periods']:
        return "The specified number of periods don't match the csv data uploaded. Please check and try again."
    if len(csvdata[0]) != len(stops_list):
        return "The specified number of stops don't match the csv data uploaded. Please check and try again."
    return render_template('only_table.html', stops_list=stops_list, rows=list(range(1,session['periods']+1)), db_data=csvdata)

# new
@app.route('/download-csv-data', methods=['GET', 'POST'])
def download_csv_data():
    # Retrieve from Database
    data = request.form.to_dict()

    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
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
