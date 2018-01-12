import boto3
import hashlib
import json
import urllib.request
from botocore.exceptions import ClientError


# ##################################################
# ############## Documentation #####################
# ##################################################

# ##################################################
#  Credits:
# ##################################################
# Author: Josh Brown
# Created: 2017 - Q4
# Last Modified: 2017 - Q4
# Sources:
#   http://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_develop-rules_example-events.html
#
# This code was created to make a framework for capturing events from the Config service on AWS. The config service
# has many rules that are maintained by AWS. The problem with these rules is that we can't take action on them or
# white list objects that are known to be in a compliant state. One such example is that we have a couple buckets that
# we want to have world read capability. The config rule and code that AWS provides says that any bucket that can be
# read from the world is said to be non-compliant and shows that condition in the dashboard. There is no white listing
# capability at this time. Reporting to and from the dashboard is just the tip of the iceberg. If you want to take some
# kind of action on the resource you have to develop custom config rules. In this way you can create code that will
# catch events and perform actions upon the resource, but then there become a maintenance issue with this code and a
# lot of redundant code to support all the resource types that you might want to run code on. For these reasons I have
# decided to create this handler for all events selected through a single config rule and a switch function will allow
# me to take action by resource type. As an added bonus we can now put all the objects we care about into the same
# config dashboard rather than jumping from one to another.
# Just like with any code there are often items that the user should be able to change without going into the code. In
# this case I have put some items in as parameters to be supplied by the Config Rule that calls the lambda code. In thisqqqqqqq
#     This is a function I wrote to clean up the YAML noise of an invoking event so it can be sent in a email to a
#     human.
#     Input is a YAML string and return an HTML page that can be injected into an email.
#
#   *func_place_config_eval(varResourceType,varResourceId,varComplianceType,varAnnotation,\
#          varConfigurationItemCaptureTime,varResultToken)
#     This function puts the config evaluation into the dashboard for the Config Rules are of your AWS account.
#     Takes in a bunch of parameters and puts them into the table of the rule.
#
# *resourcetype_case_switcher(event) This is the big function that makes all the decisions. Ideally, this is the only
#     function that should have changes made to it. It takes in the event and searches for known AWS Resource types and
#     will run code based on what the business rules are. This is where you can decide to suppress emails or allow them,
#     delete instances for not having the correct tags, etc. At the bottom of the function and SES email is sent with
#     information about the event and any custom info the developer wants to include. It also call the config dashboard
#     function to update the dashboard with the results of the evaluation. Lastly, it returns the result to the
#     lambda_handler function for logging purposes.
#
#   *send_email(SENDER, RECIPIENT, AWS_REGION, SUBJECT="Enter Subject Here", HTMLINJECTION="Nothing")
#     Nothing too special here. This code is largely plagiarized from the Internet, but I adjusted it to use only HTML
#     instead of either text or HTML. It accepts standard info that you would expect and does print a success message in
#     the logs if gets a success return from the SES service.
#
#   *lambda_handler(event, context)
#     THis is the main handler for the config events. It doesn't do anything more that print some things that are
#     helpful for logging and calls the resourcetype_case_switcher function to process more in depth code about what we
#     want to do with the event.
#
# ##################################################


def human_clean_string_html(varString):
    varIndentPos = 1  # px indention amount to start.
    varIndentPosDelta = 1  # px indention amount to increment.
    varIndentType = ""  # Characters to use for the indention.
    varMaxIndentCount = 0  # Counting the deepest indent number to use for building the CSS to match.
    varPrettyString = ''  # Base string to build and return to the calling function.
    varPrettyStringStart = '<UL>'  # Concatenate to the front of the string.
    varPrettyStringEnd = '</UL>'  # Concatenate to the end of the string.
    varPrettyStringNewLine = '</UL><UL class="list'  # For each new line needed in the data.
    varPrettyStringNewAfterPadding = '">'  # Use after the varIndetPos to close the tag properly.
    varCSSString = '<style>'  # Used for building a css to past to the string that we send out.

    for varC in varString:
        if varC == "\"" or varC == "\\" or varC == "\/":
            pass
        elif varC == "{" or varC == "[":
            varIndentPos += varIndentPosDelta
            varMaxIndentCount += 1

            varPrettyString = varPrettyString + varPrettyStringNewLine + varIndentType + str(
                varIndentPos) + varPrettyStringNewAfterPadding + varC + varPrettyStringNewLine + varIndentType + str(
                varIndentPos) + varPrettyStringNewAfterPadding
        elif varC == "}" or varC == "]":
            varPrettyString = varPrettyString + varPrettyStringNewLine + varIndentType + str(
                varIndentPos) + varPrettyStringNewAfterPadding + varC + varPrettyStringNewLine + varIndentType + str(
                varIndentPos) + varPrettyStringNewAfterPadding
            varIndentPos -= varIndentPosDelta
        elif varC == ",":
            varPrettyString = varPrettyString + varPrettyStringNewLine + varIndentType + str(
                varIndentPos) + varPrettyStringNewAfterPadding
        else:
            varPrettyString = varPrettyString + varC

    for varInt in range(varMaxIndentCount):
        varCSSString = varCSSString + '.list' + str(varInt) + ' {margin-left:' + str(varInt) + 'em;} '
    varCSSString = varCSSString + '</style>'

    varPrettyString = '<html><head>' + varCSSString + '</head><body>' + varPrettyStringStart + varPrettyString + varPrettyStringEnd + '</body></html>'

    return varPrettyString


def func_place_config_eval(varResourceType, varResourceId, varComplianceType, varAnnotation,
                           varConfigurationItemCaptureTime, varResultToken):
    config = boto3.client("config")
    config.put_evaluations(
        Evaluations=[
            {
                "ComplianceResourceType": varResourceType,
                "ComplianceResourceId": varResourceId,
                "ComplianceType": varComplianceType,
                "Annotation": varAnnotation,
                "OrderingTimestamp": varConfigurationItemCaptureTime
            }
        ],
        ResultToken=varResultToken
    )
    return


def resourcetype_case_switcher(event):
    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])
    resourceType = configuration_item["resourceType"]
    varInvokingEvent = json.dumps(event["invokingEvent"])  # Dumps instead of loads to get a string version.

    varEmail_AllAlerts = rule_parameters[
        'Email_AllAlerts']  # Pull the Email_AllAlerts parameter from the config rule to set recipients.
    varEmail_SendingAccount = rule_parameters[
        'Email_SendingAccount']  # Pull the Email_SendingAccount parameter from the config rule that will contain an
    # authorized account in SES to send mail.
    AWS_REGION = rule_parameters['Email_SESRegion']  # Pull the SES region to send from using a config parameter.
    varConfigItemStatus = {1: "COMPLIANT", 2: "NON_COMPLIANT", 3: "NOT_APPLICABLE"}
    varReturnConfigItemStatus = varConfigItemStatus[
        2]  # Assume that the status is bad unless we've said that it's good for sure
    varSendOrNotToSendEmail = True
    varPlaceOrNotToPlaceConfigDashboardEntry = True

    result_token = "No token found."
    if "resultToken" in event:
        result_token = str(event["resultToken"])

    varInjectionString = human_clean_string_html(varInvokingEvent)
    HTMLINJECTION = varInjectionString  # Default body of the email to be sent.
    SUBJECT = "AWS Config Rule: " + event['configRuleName'] + ": "  # Default subject string for emails.
    varAnnotation = "No information."  # Default annotation for the Config dashboard.

    try:
        varChangeOrCompliance = json.loads(varInvokingEvent["configurationItemDiff"])
    except TypeError:
        varChangeOrCompliance = None
    except KeyError:
        varChangeOrCompliance = None
    else:
        varChangeOrCompliance = None

    if varChangeOrCompliance is None:  # Check to see if a change was made or if this is just a compliance check.
        SUBJECT = SUBJECT + 'Compliance Check: ' + resourceType
    else:
        SUBJECT = SUBJECT + 'Change Event' + resourceType

        # ----------------------------------------------------------------------------------------------
    if resourceType == 'AWS::EC2::Instance':
        varReturnConfigItemStatus = varConfigItemStatus[1]
        varAnnotation = "Testing compliance annotation field."

    # ----------------------------------------------------------------------------------------------
    elif resourceType == 'AWS::EC2::SecurityGroup':
        varReturnConfigItemStatus = varConfigItemStatus[1]
        varAnnotation = "Testing compliance annotation field."


    # ----------------------------------------------------------------------------------------------
    elif resourceType == 'AWS::S3::Bucket':
        varReturnConfigItemStatus = varConfigItemStatus[1]
        varAnnotation = "Testing compliance annotation field."

    # ----------------------------------------------------------------------------------------------
    else:
        varAnnotation = "Testing compliance annotation field."

    if varSendOrNotToSendEmail:
        send_email(varEmail_SendingAccount, varEmail_AllAlerts, AWS_REGION, SUBJECT, HTMLINJECTION)

    if varPlaceOrNotToPlaceConfigDashboardEntry:
        func_place_config_eval(resourceType, configuration_item["resourceId"], varReturnConfigItemStatus, varAnnotation,
                               configuration_item["configurationItemCaptureTime"], result_token)

    return varReturnConfigItemStatus


def send_email(SENDER, RECIPIENT, AWS_REGION, SUBJECT="Enter Subject Here", HTMLINJECTION="Nothing"):
    # Make sure the sender is verified in SES before use.
    # CONFIGURATION_SET = "ConfigSet"

    CHARSET = "UTF-8"

    # The email body for recipients with non-HTML email clients.
    # BODY_TEXT = (BODYINJECTIONTEXT)

    # The HTML body of the email.
    BODY_HTML = HTMLINJECTION

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=AWS_REGION)

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message=
            {
                'Body':
                    {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML,
                        }

                    },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['ResponseMetadata']['RequestId'])


def lambda_handler(event, context):
    print('[Starting Function lambda_handler]:')
    print('-' * 50)

    # Print all keys and values.
    for varKey, varValue in event.items():
        print("\t", varKey, ": ", varValue)

    print('-' * 50)

    invoking_event = json.loads(event["invokingEvent"])
    configuration_item = invoking_event["configurationItem"]
    rule_parameters = json.loads(event["ruleParameters"])

    print("Invoking Event: \n", invoking_event)
    print("Configuration Event: \n", configuration_item)
    print("Rule Parameters: \n", rule_parameters)
    print("Resource Type: \n", configuration_item["resourceType"])

    varResult = resourcetype_case_switcher(event)

    print('-' * 50)

    return varResult
