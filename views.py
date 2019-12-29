# views.py
from flask import abort, jsonify, render_template, request, redirect, url_for, make_response
import uuid

from app import app
from werkzeug.utils import secure_filename
import os
import glob
import json
import ftputil
import requests
import credentials

ALLOWED_EXTENSIONS = set(['mgf', 'mzxml', 'mzml'])


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return '{"status" : "up"}'

@app.route('/', methods=['GET'])
def homepage():
    response = make_response(render_template('dashboard.html'))
    response.set_cookie('username', str(uuid.uuid4()))
    return response


@app.route('/submit', methods=['POST'])
def submit():
    TEST_MODE = False
    if "test" in request.form:
        TEST_MODE = True

    try:
        if len(request.form["peaks"]) < 2:
            raise Exception
    except:
        abort(400, "Peaks not entered")
    try:
        if len(request.form["precursormz"]) < 1:
            raise Exception
    except:
        abort(400, "Precursor not entered")

    if len(request.form["peaks"]) > 20000:
        abort(400, "Peaks are too long, must be less than 20K characters")

    username = credentials.USERNAME
    password = credentials.PASSWORD
    email = "nobody@ucsd.edu"
    dataset_filter = request.form["database"]

    analog_search = "0"
    if request.form["analogsearch"] == "Yes":
        analog_search = "1"

    if len(request.form.get("email", "")) > 2:
        email = request.form["email"]

    if len(request.form["login"]) > 2 and len(request.form["password"]) > 2:
        username = request.form["login"]
        password = request.form["password"]

    description = request.form.get(["description"], "GNPS MASST from Webform")

    if TEST_MODE:
        return "Test Passed"

    task_id = launch_GNPS_workflow(description, username, password, email, request.form["pmtolerance"], request.form["fragmenttolerance"], request.form["cosinescore"], request.form["matchedpeaks"], analog_search, request.form["precursormz"], request.form["peaks"], dataset_filter)

    if task_id is None or len(task_id) != 32:
        abort(500, "Task launch at GNPS Failed")

    return redirect("https://gnps.ucsd.edu/ProteoSAFe/status.jsp?task=%s" % (task_id))


def launch_GNPS_workflow(job_description, username, password, email, pm_tolerance, fragment_tolerance, score_threshold, matched_peaks, analog_search, precursor_mz, peaks_string, dataset_filter):
    invokeParameters = {}
    invokeParameters["workflow"] = "SEARCH_SINGLE_SPECTRUM"
    invokeParameters["protocol"] = "None"
    invokeParameters["desc"] = job_description
    invokeParameters["library_on_server"] = "d.speclibs;"

    #Search Parameters
    invokeParameters["tolerance.PM_tolerance"] = pm_tolerance
    invokeParameters["tolerance.Ion_tolerance"] = fragment_tolerance

    invokeParameters["ANALOG_SEARCH"] = analog_search
    invokeParameters["FIND_MATCHES_IN_PUBLIC_DATA"] = "1"
    invokeParameters["MAX_SHIFT_MASS"] = "100"
    invokeParameters["MIN_MATCHED_PEAKS"] = matched_peaks
    invokeParameters["SCORE_THRESHOLD"] = score_threshold
    invokeParameters["SEARCH_LIBQUALITY"] = "3"
    invokeParameters["SEARCH_RAW"] = "0"
    invokeParameters["TOP_K_RESULTS"] = "1"
    invokeParameters["DATABASES"] = dataset_filter

    #Filter Parameters
    invokeParameters["FILTER_LIBRARY"] = "1"
    invokeParameters["FILTER_PRECURSOR_WINDOW"] = "1"
    invokeParameters["FILTER_SNR_PEAK_INT"] = "0"
    invokeParameters["FILTER_STDDEV_PEAK_INT"] = "0"
    invokeParameters["MIN_PEAK_INT"] = "0"
    invokeParameters["WINDOW_FILTER"] = "1"

    #Spectrum
    invokeParameters["precursor_mz"] = precursor_mz
    invokeParameters["spectrum_string"] = peaks_string

    invokeParameters["email"] = email
    invokeParameters["uuid"] = "1DCE40F7-1211-0001-979D-15DAB2D0B500"

    task_id = invoke_workflow("gnps.ucsd.edu", invokeParameters, username, password)

    return task_id

def invoke_workflow(base_url, parameters, login, password):
    username = login
    password = password

    s = requests.Session()

    payload = {
        'user' : username,
        'password' : password,
        'login' : 'Sign in'
    }

    r = s.post('https://' + base_url + '/ProteoSAFe/user/login.jsp', data=payload, verify=False)
    r = s.post('https://' + base_url + '/ProteoSAFe/InvokeTools', data=parameters, verify=False)
    task_id = r.text

    print(r.text)

    if len(task_id) > 4 and len(task_id) < 60:
        print("Launched Task: : " + r.text)
        return task_id
    else:
        print(task_id)
        return None
