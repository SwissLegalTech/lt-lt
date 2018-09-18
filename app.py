#!/usr/bin/env python
# coding=utf-8
import os
import pandas as pd
from datetime import datetime, date, timedelta
from functools import wraps
from os import environ as env
from werkzeug.exceptions import HTTPException
import dominate.tags as html
from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from flask import request
from flask_sslify import SSLify
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode

import constants
from utils import delta, cnvt_date
from workalendar.europe import Switzerland

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

AUTH0_CALLBACK_URL = env.get(constants.AUTH0_CALLBACK_URL)
AUTH0_CLIENT_ID = env.get(constants.AUTH0_CLIENT_ID)
AUTH0_CLIENT_SECRET = env.get(constants.AUTH0_CLIENT_SECRET)
AUTH0_DOMAIN = env.get(constants.AUTH0_DOMAIN)
AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN if AUTH0_DOMAIN is not None else env.get(constants.AUTH0_BASE_URL)
AUTH0_AUDIENCE = env.get(constants.AUTH0_AUDIENCE, '')
if AUTH0_AUDIENCE is '':
    AUTH0_AUDIENCE = AUTH0_BASE_URL + '/userinfo'


app = Flask(__name__,
            static_url_path='/public',
            static_folder='./public')

app.secret_key = constants.SECRET_KEY
app.debug = False

# sslify = SSLify(app)


@app.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=repr(ex) + ": " + str(ex))
    response.status_code = (ex.code if isinstance(ex, HTTPException) else 500)
    return response


oauth = OAuth(app)


auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # return f(*args, **kwargs)
        if constants.PROFILE_KEY not in session:
            # Redirect to / home-page here if we don't want to send people straight to the sign-up page
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


# def ssl_required(f):
#     @wraps(f)
#     def decorated_view(*args, **kwargs):
#         if current_app.config.get("SSL"):
#             if request.is_secure:
#                 return f(*args, **kwargs)
#             else:
#                 return redirect(request.url.replace("http://", "https://"))
#         return f(*args, **kwargs)
#     return decorated_view

# Controllers API
@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)


# @app.route('/welcome')
# def welcome():
#     return render_template('dashboard.html',
#                            pageinfo={'log_name': 'LogIn',
#                                      'log_link': '/login',
#                                      'pic_display': 'block'},
#                            userinfo=session[constants.PROFILE_KEY])


@app.route('/')
def home():
    # check if user is already logged in
    if constants.PROFILE_KEY in session:
        return redirect('/dashboard')

    return render_template('dashboard.html',
                           pageinfo={'log_name': 'LogIn',
                                     'log_link': '/login',
                                     'pic_display': 'none'},
                           userinfo={'picture': ''})


# Here we're using the /callback route.
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    token = auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    # Store the token as a cookie
    response = redirect('/dashboard')
    # to set actual expiry, we need to provide that as a datetime ?# expires=token.get('expires_in')
    # https://stackoverflow.com/questions/26613435/python-flask-not-creating-cookie-when-setting-expiration
    # http://flask.pocoo.org/docs/1.0/api/#flask.Response.set_cookie
    # TODO: domain=.mydomain.com
    response.set_cookie('ltjwt',
                        value='{}'.format(token.get('id_token')),
                        max_age=token.get('expires_in'),
                        httponly=True,
                        secure=False)
    # response.set_cookie('ltjwt', value='{}'.format(token.get('id_token')), max_age=token.get('expires_in'))
    return response


@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


##################################
#      ALL APPS LINKED HERE      #


@app.route('/disclaimer')
def disclaimer():

    content = html.div(cls='app-wrapper')
    content.add(html.h1('Disclaimer', cls='serif'))

    content.add(html.div('''
        Die LAWYER TOOLS liefern keine rechtlich
        verbindlichen Ergebnisse und sind kein Ersatz für Ihre eigenen Berechnungen
        und Abklärungen. 
        '''))
    content.add(html.p())
    content.add(html.div('''
            LAWYER TOOLS unterstützen lediglich die eigenen und allein
            massgebenden Berechnungen und Abklärungen der fachkundigen Benutzer*innen.
            Wer sich nicht auf seine eigenen Abklärungen und Berechnungen, sondern auf
            diejenige der LAWYER TOOLS, verlässt, tut dies auf EIGENE GEFAHR und trägt
            für allfällige Schäden die alleinige Verantwortung.'''))
    content.add(html.p())
    content.add(html.div('''                
                Wer sich nicht auf seine eigenen Abklärungen und Berechnungen, sondern auf
                diejenige der LAWYER TOOLS, verlässt, tut dies auf EIGENE GEFAHR und trägt
                für allfällige Schäden die alleinige Verantwortung.'''))

    content.add(html.span('Im Übrigen gelten die'))
    content.add(html.span(html.a('AGBs', href='/agb')))

    return render_template('generic.html',
                           appinfo={'external_src': 'https://legaldrop.duckdns.org',  # https://drop.lawyer.tools
                                    'iframe_height': '1024',
                                    'iframe_width': '100%'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block',
                                     'content': content},
                           userinfo=session[constants.PROFILE_KEY])

#
# @app.route('/impressum')
# def impressum():
#
#     content = html.div(cls='app-wrapper')
#     content.add(html.h1('Impressum', cls='serif'))
#
#     content.add(html.div('''
#         Kommt bald...'''))
#
#     return render_template('generic.html',
#                            appinfo={'external_src': 'https://legaldrop.duckdns.org',  # https://drop.lawyer.tools
#                                     'iframe_height': '1024',
#                                     'iframe_width': '100%'},
#                            pageinfo={'log_name': 'LogOut',
#                                      'log_link': '/logout',
#                                      'pic_display': 'block',
#                                      'content': content},
#                            userinfo=session[constants.PROFILE_KEY])


@app.route('/agb')
def agb():

    content = html.div(cls='app-wrapper')
    content.add(html.h1('AGB', cls='serif'))

    content.add(html.a('Dokument hier herunterladen', href='/public/data/agb.docx'))

    return render_template('generic.html',
                           appinfo={'external_src': 'https://legaldrop.duckdns.org',  # https://drop.lawyer.tools
                                    'iframe_height': '1024',
                                    'iframe_width': '100%'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block',
                                     'content': content},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/contact')
def contact():

    content = html.div()
    content.add(html.h1('Hello', cls='h1 serif'))
    content.add(html.h1('Fellaw', cls='h1'))

    content.add(html.h2('Unsere Tools sind handgemacht. Lernen Sie uns kennen.', cls='h2'))
    content.add(html.h3('codefour gmbh', cls='h3'))
    content.add(html.p('Zentralstrasse 47', cls='p'))
    content.add(html.p('CH-8003 Zürich', cls='p'))
    content.add(html.a('info@codefour.ch', href="mailto:info@codefour.ch"))

    content.add(html.h4('Swissmade Code gepaart mit Anwalts-Know-How', cls='h4'))
    content.add(html.p('Unsere Expertisen aus Informatik und Juristik vereinen wir als Team mit der Plattform Lawyer Tools', cls='p'))

    content.add(html.h2('Wer wir sind', cls='h2'))

    with content:

        with html.div(cls='team-wrapper'):
            with html.a(cls='team-member-box w-inline-block'):

                    with html.div(cls='portrait-image'):
                        html.img(src='/public/images/portrait_simon.jpg', cls='image')
                    html.h4('Simon Schnetzler', cls='h4')
                    html.p('Lic. iur. ', cls='p')
            with html.a(cls='team-member-box w-inline-block'):

                    with html.div(cls='portrait-image'):
                        html.img(src='/public/images/portrait_gregor.jpg', cls='image')
                    html.h4('Gregor Münch', cls='h4')
                    html.p('Lic. iur. ', cls='p')
            with html.a(cls='team-member-box w-inline-block'):

                    with html.div(cls='portrait-image'):
                        html.img(src='/public/images/portrait_christoph.jpg', cls='image')
                    html.h4('Christoph Russ', cls='h4')
                    html.p('Dr. sc. ETH', cls='p')
            with html.a(cls='team-member-box w-inline-block'):

                    with html.div(cls='portrait-image'):
                        html.img(src='/public/images/portrait_christian.jpg', cls='image')
                    html.h4('Christian Wengert', cls='h4')
                    html.p('Dr. sc. ETH', cls='p')

    return render_template('generic.html',
                           appinfo={'external_src': 'https://legaldrop.duckdns.org',  # https://drop.lawyer.tools
                                    'iframe_height': '1024',
                                    'iframe_width': '100%'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block',
                                     'content': content},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/legaldrop')
@requires_auth
def legaldrop():
    content = html.iframe(src='https://legaldrop.lawyer.tools', height='600', width='100%', frameborder=0)

    return render_template('application.html',
                           appinfo={'title1': 'Legal',
                                    'title2': 'Drop',
                                    'short_text': 'Mit Legal Drop versenden Sie Ihre Daten End-zu-End verschlüsselt an Ihre Klienten.',
                                    'app_content': content,
                                    'more_title': 'Volle Sicherheit',
                                    'more_content': 'Senden Sie Dateien über einen sicheren, privaten und verschlüsselten Link, der automatisch abläuft, damit Ihre Daten nicht für immer im Internet bleiben.'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/datedelta')
@requires_auth
def datedelta():

    args = request.args
    start = args.get('start', '')
    end = args.get('end', '')

    result = delta(start, end)
    content = html.div(cls='form-block w-form')
    if result:

        with content:
            with html.div(cls='answer w-form'):
                html.div(f'Anzahl Tage zwischen diesen Daten: {result.days}', cls='h2 white')
                html.div()
                html.div(html.a('Neu berechnen', href='/datedelta', cls='white w--current button'),
                         cls='')

    else:

        form = content.add(html.form(action='/datedelta', method='GET'))
        with form.add(html.div()):
            html.label('Startdatum', fr='start', cls='formfield-title')
            html.input(name='start', type='date', value=start, cls='formfield-default w-input',
                       placeholder='2018-01-01')

        with form.add(html.div()):
            html.label('Enddatum', fr='end', cls='formfield-title')
            html.input(name='end', type='date', value=end, cls='formfield-default w-input',
                       placeholder='2018-01-18')

        with form.add(html.div()):
            html.input('Abschicken', type='submit', cls='button white w-button')

    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Date',
                                    'title2': 'Delta',
                                    'short_text': 'Datums Delta berechnet die Anzahl Tage zwischen zwei Daten.',
                                    'app_content': content,
                                    'more_title': 'Berechnungsformel',
                                    'more_content': 'Differenz zwischen zwei Daten - ohne Feiertage'},

                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/duedate')
@requires_auth
def duedate():

    content = html.div(cls='form-block w-form')
    

    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Due',
                                    'title2': 'Date',
                                    'short_text': 'Berechnen Sie Ihre Frist in Sekundenschnelle',
                                    'app_content': content,
                                    'more_title': 'Berechnungsformel',
                                    'more_content': 'Siehe die betreffenden Rechtsgrundlagen'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


path = os.path.join(os.path.dirname(__file__), 'data', 'Datensatz High Limits.xlsx')
SPEED_LIMITS = pd.read_excel(path, index_col=[0, 1])


@app.route('/speedlimits')
@requires_auth
def speedlimits():
    speed = request.args.get('speed', '')
    zone = request.args.get('zone', '')

    content = html.div(cls='form-block w-form')

    

    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Speed',
                                    'title2': 'Limits',
                                    'short_text': 'Was droht Ihrem Klienten bei einer Geschwindigkeitsübertretung',
                                    'app_content': content,
                                    'more_title': 'Methodik',
                                    'more_content': 'Siehe die einschlägigen Rechtsquellen'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/visiblearticle')
@requires_auth
def visiblearticle():
    content = html.iframe(src='https://va.lawyer.tools', height='1024', width='100%', frameborder=0)

    return render_template('application.html',
                           appinfo={'title1': 'Visible',
                                    'title2': 'Article',
                                    'short_text': 'Schnelle Popups von Gesetzestexten bei Ihrer Onlinerecherche',
                                    'app_content': content,
                                    'more_title': 'Verlinkte Rechtsquellen',
                                    'more_content': 'ARG, ATSG, AUG, BGG, BV, BVG, DBG, DSG, INDEX, KVG, MWSTG, OBV, OR, SCHKG, STGB, STPO, SVG, UVG, VRV, VTS, ZGB, ZPO'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY]
                           )


@app.route('/founderbot')
@requires_auth
def founderbot():
    content = html.iframe(src='https://gr.lawyer.tools', height='1024', width='100%', frameborder=0)

    return render_template('application.html',
                           appinfo={'title1': 'Founder',
                                    'title2': 'Bot',
                                    'short_text': 'Erstellen der kompletten Gründungsunterlagen mit wenigen Klicks. Bekannt vom Swisslegaltech Hackathon 2017!',
                                    'app_content': content,
                                    'more_title': 'Output',
                                    'more_content': 'Es werden die benötigten Gründungsunterlagen schnell und einfach mit Ihren Eingaben abgemischt'},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/flightdelay')
@requires_auth
def flightdelay():
    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Flight',
                                    'title2': 'Delay',
                                    'more_title': '',
                                    'more_content': ''},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/highdrive')
@requires_auth
def highdrive():
    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'High',
                                    'title2': 'Drive',
                                    'more_title': '',
                                    'more_content': ''},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/labourlaw')
@requires_auth
def labourlaw():
    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Labour',
                                    'title2': 'Law',
                                    'more_title': '',
                                    'more_content': ''},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/shabscanner')
@requires_auth
def shabscanner():
    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'SHAB',
                                    'title2': 'Scanner',
                                    'more_title': '',
                                    'more_content': ''},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])


@app.route('/watchdog')
@requires_auth
def watchdog():
    return render_template('application.html',
                           appinfo={'app_name': 'APP',
                                    'app_logo': 'LOGO',
                                    'title1': 'Watch',
                                    'title2': 'Dog',
                                    'more_title':'',
                                    'more_content': ''},
                           pageinfo={'log_name': 'LogOut',
                                     'log_link': '/logout',
                                     'pic_display': 'block'},
                           userinfo=session[constants.PROFILE_KEY])

#      ALL APPS LINKED HERE      #
##################################


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    # FORCE HTTPS if not localhost?!
    scheme = 'https' if 'localhost' not in request.host else request.scheme
    params = {'returnTo': url_for('home', _external=True, _scheme=scheme), 'client_id': AUTH0_CLIENT_ID}
    response = redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
    response.set_cookie('ltjwt', value='', expires=0)
    return response


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=env.get('PORT', 3000))
    app.run(host='0.0.0.0', port='3000')
