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


##############################
# Responses
##############################


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

def push_sns(event):
    snsTopic = os.environ.get('SNS_TOPIC')
    print('###############################################')
    print(snsTopic)
    sns = boto3.client('sns')
    response = sns.publish(
        TopicArn=snsTopic,
        Message=json.dumps(event)
    )


##############################
# Custom Intents
##############################

def emailServiceDescription(event, context):
    dialog_state = event['request']['dialogState']

    if dialog_state in ("STARTED", "IN_PROGRESS"):
        return continue_dialog()

    elif dialog_state == "COMPLETED":
        if 'service' in intent['slots']:
            service_name = intent['slots']['service']['value']
            push_sns(event)
            return statement("emailServiceDescription", "I'll let U CAS know now and they will email you confirmation of the decisions within the next 24 hours.")
        else:
            return statement("emailServiceDescription", "Please tell me which service you would like to get the service description for.")

    else:
        return statement("emailServiceDescription", "No dialog")


##############################
# Required Intents
##############################


def cancel_intent():
    return statement("CancelIntent", "You want to cancel")	#don't use CancelIntent as title it causes code reference error during certification 


def help_intent():
    return statement("CancelIntent", "You want help")		#same here don't use CancelIntent


def stop_intent():
    return statement("StopIntent", "You want to stop")		#here also don't use StopIntent


##############################
# On Launch
##############################


def on_launch(event, context):
    return statement("title", "body")


##############################
# Routing
##############################


def intent_router(event, context):
    intent = event['request']['intent']['name']

    # Custom Intents

    if intent == "emailServiceDescription":
        return emailServiceDescription(event, context)

    # Required Intents

    if intent == "AMAZON.CancelIntent":
        return cancel_intent()

    if intent == "AMAZON.HelpIntent":
        return help_intent()

    if intent == "AMAZON.StopIntent":
        return stop_intent()


##############################
# Program Entry
##############################


def lambda_handler(event, context):
    print('egg')
    print(event)
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event, context)

    elif event['request']['type'] == "IntentRequest":
        return intent_router(event, context)
