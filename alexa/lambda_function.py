import boto3
import os
import json
import requests
import datetime

##############################
# Builders
##############################


def build_PlainSpeech(body):
    speech = {}
    speech['type'] = 'PlainText'
    speech['text'] = body
    return speech


def build_response(message, session_attributes={}):
    response = {}
    response['version'] = '1.0'
    response['sessionAttributes'] = session_attributes
    response['response'] = message
    return response


def build_SimpleCard(title, body):
    card = {}
    card['type'] = 'Simple'
    card['title'] = title
    card['content'] = body
    return card


def build_LinkAccount(body):
    card = {}
    card['title'] = 'Link Account'
    card['type'] = 'LinkAccount'
    return card

##############################
# Responses
##############################


def linkaccount(title, body):
    speechlet = {}
    speechlet['outputSpeech'] = build_PlainSpeech(body)
    speechlet['card'] = build_LinkAccount(body)
    speechlet['shouldEndSession'] = True
    return build_response(speechlet)


def conversation(title, body, session_attributes):
    speechlet = {}
    speechlet['outputSpeech'] = build_PlainSpeech(body)
    speechlet['card'] = build_SimpleCard(title, body)
    speechlet['shouldEndSession'] = False
    return build_response(speechlet, session_attributes=session_attributes)


def statement(title, body):
    speechlet = {}
    speechlet['outputSpeech'] = build_PlainSpeech(body)
    speechlet['card'] = build_SimpleCard(title, body)
    speechlet['shouldEndSession'] = True
    return build_response(speechlet)


def continue_dialog():
    message = {}
    message['shouldEndSession'] = False
    message['directives'] = [{'type': 'Dialog.Delegate'}]
    return build_response(message)


##############################
# Custom Methods
##############################

def push_sns(event, snsTopic):
    sns = boto3.client('sns')
    response = sns.publish(
        TopicArn=snsTopic,
        Message=json.dumps(event)
    )
    return response


def verifyEmail(email):
    client = boto3.client('ses')
    response = client.list_verified_email_addresses()
    if email in response['VerifiedEmailAddresses']:
        return True
    else:
        response = client.verify_email_address(
            EmailAddress=email,
        )
        return None


def get_user_info(access_token):
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

##############################
# Custom Intents
##############################


def getNotes(event, context):

    dynamoDBTable = os.environ.get('DYNAMODB_NOTES_TABLE')
    emailAddress = get_user_info(event['context']['System']['user']['accessToken'])['email']
    date = str(datetime.date.today())

    client = boto3.client('dynamodb')

    response = client.query(
        ExpressionAttributeValues={
            ':v1': {
                'S': emailAddress,
            },
        },
        KeyConditionExpression='UserEmail = :v1',
        TableName=dynamoDBTable,
    )
    
    if response['Items'] != []:
        todaysNotes = response['Items'][0]['notes']['M'][date]
        notes = ''
        count = 1
        for key in todaysNotes['L']:
            notes = notes + str(count) + '' + key['S'] + '. '
            count = count + 1
        return statement('takeNote', 'Here are your notes. ' + notes)
    else:
        return statement('takeNote', 'You do not have any notes.')    

def takeNote(event, context):

    dialog_state = event['request']['dialogState']

    if dialog_state in ("STARTED", "IN_PROGRESS"):
        return continue_dialog()

    elif dialog_state == "COMPLETED":
        dynamoDBTable = os.environ.get('DYNAMODB_NOTES_TABLE')
        emailAddress = get_user_info(event['context']['System']['user']['accessToken'])['email']
        date = str(datetime.date.today())
        new_note = event['request']['intent']['slots']['notes']['value']
    
        client = boto3.client('dynamodb')
    
        response = client.query(
            ExpressionAttributeValues={
                ':v1': {
                    'S': emailAddress,
                },
            },
            KeyConditionExpression='UserEmail = :v1',
            TableName=dynamoDBTable,
        )
    
        if response['Items'] != []:
            todaysNotes = response['Items'][0]['notes']['M']
            for key, value in todaysNotes.items():
                if key == date:
                   response['Items'][0]['notes']['M'][date]['L'].append({'S': new_note})
                   newNote = response['Items'][0]
                   response = client.put_item(
                       Item=newNote,
                       TableName=dynamoDBTable,
                   )
                   print(response)
                else:
                    response = client.put_item(
                        Item={'UserEmail': {'S': emailAddress}, 'notes': {'M': {date: {'L': [{'S': new_note}]}}}},
                        TableName=dynamoDBTable,
                    )
                    print(response)
        else:
            response = client.put_item(
                Item={'UserEmail': {'S': emailAddress}, 'notes': {'M': {date: {'L': [{'S': new_note}]}}}},
                TableName=dynamoDBTable,
            )
        return statement('takeNote', 'I have recorded ' + new_note + ". I'll email you a summary at 5pm")
    

def emailServiceDescription(event, context):
    print('############################')
    snsTopic = os.environ.get('SNS_EMAIL_TOPIC')
        
    dialog_state = event['request']['dialogState']

    if dialog_state in ('STARTED', 'IN_PROGRESS'):
        return continue_dialog()

    elif dialog_state == 'COMPLETED':
        if 'service' in event['request']['intent']['slots']:
            service_name = event['request']['intent']['slots']['service']['value']
            messageid = push_sns(event, snsTopic)
            return statement('emailServiceDescription',
                             "I'm emailing you the service description for "
                             + service_name)
            push_sns(event, snsTopic)
            return statement("emailServiceDescription", "I'm emailing you the service description for " + service_name)
        else:
            return statement('emailServiceDescription',
                             'Please tell me which service you would like to get the service description for.')

    else:
        return statement('emailServiceDescription', 'No dialog')


def emailComplianceReport(event, context):
        
    snsTopic = os.environ.get('SNS_COMPLIANCE_TOPIC')
    dialog_state = event['request']['dialogState']

    if dialog_state in ("STARTED", "IN_PROGRESS"):
        return continue_dialog()

    elif dialog_state == "COMPLETED":
        if 'compliance' in event['request']['intent']['slots']:
            compliance_name = event['request']['intent']['slots']['compliance']['value']
            push_sns(event, snsTopic)
            return statement("emailComplianceReport", "I'm emailing you the compliance report for " + compliance_name)
        else:
            return statement("emailComplianceReport", "Please tell me which service you would like to get the compliance report for.")

    else:
        return statement("emailServiceDescription", "No dialog")


##############################
# Required Intents
##############################


def cancel_intent():
    return statement('CancelIntent', 'You want to cancel')
    # don't use CancelIntent as title it causes code reference error during certification


def help_intent():
    return statement('CancelIntent', 'You want help')
    # Same here don't use CancelIntent


def stop_intent():
    return statement('StopIntent', 'You want to stop')
    # Here also don't use StopIntent


##############################
# On Launch
##############################


def on_launch(event, context):
    return statement('title', 'body')


##############################
# Routing
##############################


def intent_router(event, context):
    intent = event['request']['intent']['name']

    # Custom Intents

    if intent == 'emailServiceDescription':
        return emailServiceDescription(event, context)
    if intent == 'emailComplianceReport':
        return emailComplianceReport(event, context)
    if intent == 'takeNote':
        return takeNote(event, context)
    if intent == 'getNotes':
        return getNotes(event, context)
        
    # Required Intents

    if intent == 'AMAZON.CancelIntent':
        return cancel_intent()

    if intent == 'AMAZON.HelpIntent':
        return help_intent()

    if intent == 'AMAZON.StopIntent':
        return stop_intent()


##############################
# Program Entry
##############################


def lambda_handler(event, context):
    print(event)
    try:
        emailAddress = get_user_info(event['context']['System']['user']['accessToken'])['email']
        if not verifyEmail(emailAddress):
            return statement('EmailNotVerified',
                             'Please check your email to verify your email address before we can send you any details.')		#here also don't use StopIntent

    except Exception as err:
        return linkaccount('NotLinked',
                         'Your user details are not available at this time.  Have you completed account linking via the Alexa app?')		#here also don't use StopIntent if event['request']['type'] == "LaunchRequest":
        return on_launch(event, context)

    if event['request']['type'] == 'IntentRequest':
        return intent_router(event, context)




