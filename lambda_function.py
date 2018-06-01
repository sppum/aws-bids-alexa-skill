"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

from __future__ import print_function
from bs4 import BeautifulSoup
import requests
from xhtml2pdf import pisa
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from operator import itemgetter
import boto3
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

response = requests.get('https://aws.amazon.com/products/').text

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to the Alexa skill for the bids team. " \
                    "Please ask me to email you a service description"
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Please ask me to email you a service description"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Alexa Skill for the bid team. " 
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_user_info(access_token):
    #print access_token
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

def sendServiceDescription(event, intent, session):
    """ Emails a service description to a user.
    """

    card_title = intent['name']
    session_attributes = {}
    should_end_session = True

    if 'service' in intent['slots']:
        service_name = intent['slots']['service']['value']
        emailProfile = get_user_info(event['session']['user']['accessToken'])['email']
        service = findService(service_name)
        createPdf(service['serviceUrl'])
        resultResponse = sendEmail(service['serviceName'], emailProfile)
        speech_output = "I'm emailing you a service description for  " + \
                        service_name
        reprompt_text = "You can ask me to email you a service description by saying, " \
                        "email me a service description for workspaces"
    else:
        speech_output = "I'm not sure which service you want. " \
                        "Please try again."
        reprompt_text = "I'm not sure which service you want. " \
                        "You can ask me to email you a service description by saying, " \
                        "email me a service description for workspaces"
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(event, intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "emailServiceDescription":
        return sendServiceDescription(event, intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here

def getServiceList():
    soup = BeautifulSoup(response, "html.parser")
    serviceList = []
    for service in soup.find_all(class_="lb-content-item"):
        serviceUrl = service.a['href']
        serviceName = service.a.contents[0]
        serviceList.append({'serviceName': serviceName, 'serviceUrl': 'https://aws.amazon.com' + serviceUrl })
    return serviceList

def getServiceDescription(serviceUrl):
    response = requests.get(serviceUrl).text
    soup = BeautifulSoup(response, "html.parser")
    return soup.find("div", {"id": "aws-page-content"})

def createPdf(serviceUrl):
    outputFilename = "/tmp/service_description.pdf"
    resultFile = open(outputFilename, "w+b")
    pisa.CreatePDF(getServiceDescription(serviceUrl).encode('utf-8'), resultFile)
    resultFile.close()

def findService(serviceName):
    confidenceList = []
    serviceList = getServiceList()
    for service in serviceList:
        service.update({'ratio': fuzz.ratio(service, serviceName)})
        confidenceList.append(service)
    sortedConfidenceList = sorted(confidenceList, key=itemgetter('ratio'), reverse=True)
    return sortedConfidenceList[0]

def verifyEmail(email):
    client = boto3.client('ses')
    response = client.list_verified_email_addresses()
    if email in response['VerifiedEmailAddresses']:
        return None
    else:
        response = client.verify_email_address(
            EmailAddress=email,
        )
        return True

def sendEmail(serviceName, emailAddress):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) == None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Test'
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        msg.preamble = 'Multipart message.\n'

        part = MIMEText('Here is the service description for ' + serviceName)
        msg.attach(part)

        part = MIMEApplication(open('/tmp/service_description.pdf', 'rb').read())
        part.add_header('Content-Disposition', 'attachment', filename='service_description.pdf')
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            }
            , Source=msg['From'])
        print(result)
        return "I'm emailing you a service description for" +  serviceName
    else:
        return "Please go to your mail and verify your email address so we can email you the service description"

# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])
    print(event)

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event, event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

