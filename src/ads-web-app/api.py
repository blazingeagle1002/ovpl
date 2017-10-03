from flask import Flask, redirect, url_for, session, request, jsonify,\
     render_template, current_app
from flask_oauthlib.client import OAuth
from flask import Blueprint
import requests
import json
from config import *
import re
import os

api = Blueprint('APIs', __name__)

oauth = OAuth()

google = oauth.remote_app(
    'google',
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    request_token_params={
        'scope': 'email', 'prompt': 'select_account'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@api.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        remote_url = request.url
        if remote_url.find("vlabs.ac.in") != -1:
            return redirect(APP_URL)
        elif remote_url.find("localhost") != -1:
            if 'current_user' in session:
                return render_template("index.html")
            return render_template("login.html")
        else:
            if ('current_user' in session) and ('google_token' in session):
                return render_template("index.html")
            return render_template("login.html")

    elif request.method == 'POST':
        lab_id = request.form.get("lab_id")
        lab_url = request.form.get("lab_src_url")
        tag = request.form.get("version")
        if tag == "":
            tag = "master"
        data = {'lab_id': lab_id, 'lab_src_url': lab_url, 'version': tag, \
                    'key' : ADS_SECRET_KEY, "current_user" : session.get('current_user')}
        current_app.logger.debug("lab_id = %s, lab_src_url=%s, "
                                     "version=%s, key=%s, "
                            %(lab_id, lab_url, tag, ADS_SECRET_KEY))

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        if(re.search('^[a-zA-Z0-9_-]+$', lab_id) is None):
            return render_template("index.html", message="Invalid Lab_id : " \
                                       + lab_id)

        if (re.search('^[a-zA-Z0-9_-]+$', tag) is None or tag == ""):
            return render_template("index.html", message="Invalid Tag : "\
                                       + tag)

        if (re.search("((git|ssh|http(s)?)|(git@[\w\.]+))(:(//)?)"\
                          "([\w\.@\:/\-~]+)((\.git)(/)|())?", lab_url) is None):
            return render_template("index.html", message="Invalid Git URL : "\
                                       + lab_url)

        try:
            os.environ['NO_PROXY']="localhost"
            r = requests.post(ADS_URL, data=json.dumps(data), headers=headers)
            if r.status_code == 200:
                if r.text == "Test failed: See log file for errors":
                    return render_template("index.html", \
                                            message="Something went wrong please"\
                                               "check log files in ADS server")
                else:
                    data['url'] = "http://" + r.text
                    return render_template("success.html", data=data)
            elif r.status_code == 401:
                current_app.logger.error("error code = %s" % str(r.status_code))
                return render_template("index.html", \
                                           message="Unauthorized Credentials")
            else:
                return render_template("index.html", message="Error : " \
                                           + str(r.status_code))
        except Exception as e:
            current_app.logger.error("error code = %s" % str(e))
            return render_template("index.html", message="Error : " + str(e))

@api.route('/login')
def login():
    return google.authorize(callback=url_for('APIs.authorized',\
                                                 _external=True))

@api.route('/logout')
def logout():
    session.pop('google_token', None)
    session.pop('current_user', None)
    session.pop('error', None)
    return redirect("/")

@api.route('/login/authorized')
def authorized():
    resp = google.authorized_response()
    if resp is None:
        return redirect("/")
    session['google_token'] = (resp['access_token'], '')
    user_info = google.get('userinfo')
    email = user_info.data['email']

    if email not in AUTHORIZED_USERS:
        session['error'] = "Unauthorized Email : "+email
    else:
        session['current_user'] = email
    return redirect("/")

@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')
