import re
import requests
import json

from flask import Flask
from flask import render_template
from flask import url_for
from flask import request

from twilio import twiml
from twilio.util import TwilioCapability

# Declare and configure application
app = Flask(__name__, static_url_path='/static')
app.config.from_pyfile('local_settings.py')


# Voice Request URL
@app.route('/voice', methods=['GET', 'POST'])
def voice():
    response = twiml.Response()
    response.say("Congratulations! You deployed the Twilio Hackpack "
                 "for Heroku and Flask.")
    return str(response)


# SMS Request URL
@app.route('/sms', methods=['GET', 'POST'])
def sms():
    response = twiml.Response()
    body = request.form['Body']
    metro_final = ''
    output = 'Nothing was found.'
    if "everyblock" in body:
        textinput = body.replace('everyblock ','')
        metros = ['philly', 'denver', 'houston', 'boston', 'chicago']
        #find which metro it is in
        if textinput.isdigit():
            texttype = 'zipcodes'
            for metro in metros:
                everyblock_url = 'https://api.everyblock.com/content/%s/zipcodes'%metro
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
                return_data = json.loads(r.text)
                for i in return_data:
                    #print i
                    if textinput == i['name']:
                        #print textinput,'is in',metro
                        metro_final = metro
                        break
        else:
            texttype = 'neighborhoods'
            for metro in metros:
                everyblock_url = 'https://api.everyblock.com/content/%s/neighborhoods'%metro
                #print 'trying: ',everyblock_url
                r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
                return_data = json.loads(r.text)
                for i in return_data:
                    if textinput.title() == i['name']:
                        #print textinput,'is in',metro
                        metro_final = metro
                        textinput = textinput.replace(' ','-')
                        break
        #found the metro!
        if metro_final != '':
            everyblock_url = 'https://api.everyblock.com/content/%s/locations/%s/timeline/?schema=crime'%(metro_final, textinput)
            r = requests.get(everyblock_url, headers = {'Authorization' : 'Token fc51e71739c072154f4f8d58ed4f9ec0770aee76'})
            return_data = json.loads(r.text)
            count = 0
            output = ''
            for event in return_data['results']:
                date = event['pub_date']
                #date in good format
                date = date[5:7]+'/'+date[8:10]+'/'+date[2:4]
                #time: use dispatch time
                time = datetime.strptime(event['attributes']['dispatch_time'][:5], '%H:%M')
                time = time.strftime('%I:%M %p')
                output += event['title']+' on '+event['location_name']+' at '+date+', '+time+'. '
                count += 1
                if count == 2:
                    break
        output = str(output)
        response.sms(output)
    else:
        response.sms('Text "everyblock" and your zip code or town to get a feed!')
    return str(response)


# Twilio Client demo template
@app.route('/client')
def client():
    configuration_error = None
    for key in ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_APP_SID',
                'TWILIO_CALLER_ID'):
        if not app.config.get(key, None):
            configuration_error = "Missing from local_settings.py: " \
                                  "{0}".format(key)
            token = None

    if not configuration_error:
        capability = TwilioCapability(app.config['TWILIO_ACCOUNT_SID'],
                                      app.config['TWILIO_AUTH_TOKEN'])
        capability.allow_client_incoming("joey_ramone")
        capability.allow_client_outgoing(app.config['TWILIO_APP_SID'])
        token = capability.generate()
    params = {'token': token}
    return render_template('client.html', params=params,
                           configuration_error=configuration_error)


@app.route('/client/incoming', methods=['POST'])
def client_incoming():
    try:
        from_number = request.values.get('PhoneNumber', None)

        resp = twiml.Response()

        if not from_number:
            resp.say("Your app is missing a Phone Number. "
                     "Make a request with a Phone Number to make outgoing "
                     "calls with the Twilio hack pack.")
            return str(resp)

        if 'TWILIO_CALLER_ID' not in app.config:
            resp.say(
                "Your app is missing a Caller ID parameter. "
                "Please add a Caller ID to make outgoing calls with Twilio "
                "Client")
            return str(resp)

        with resp.dial(callerId=app.config['TWILIO_CALLER_ID']) as r:
            # If we have a number, and it looks like a phone number:
            if from_number and re.search('^[\d\(\)\- \+]+$', from_number):
                r.number(from_number)
            else:
                r.say("We couldn't find a phone number to dial. Make sure "
                      "you are sending a Phone Number when you make a "
                      "request with Twilio Client")

        return str(resp)

    except:
        resp = twiml.Response()
        resp.say("An error occurred. Check your debugger at twilio dot com "
                 "for more information.")
        return str(resp)


# Installation success page
@app.route('/')
def index():
    params = {
        'Voice Request URL': url_for('.voice', _external=True),
        'SMS Request URL': url_for('.sms', _external=True),
        'Client URL': url_for('.client', _external=True)}
    return render_template('index.html', params=params,
                           configuration_error=None)
