import boto3
import logging
import os
import time
import unicodedata


logger = logging.getLogger()
logger.setLevel(logging.INFO)
kms_key_id = os.environ['KMS_KEY_ID']


def lambda_handler(event, context):

    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    print('---- Inside the lambda_handler ----')
    print('Secret arn:')
    print(arn)
    # Setup the client
    service_client = boto3.client('secretsmanager', endpoint_url=os.environ['SECRETS_MANAGER_ENDPOINT'])

    if step == "createSecret":
        create_secret(service_client, arn, token)

    elif step == "setSecret":
        set_secret(service_client, arn, token)

    elif step == "testSecret":
        test_secret(service_client, arn, token)

    elif step == "finishSecret":
        finish_secret(service_client, arn, token)

    else:
        raise ValueError("Invalid step parameter")


def create_secret(service_client, arn, token):
    print('------ Inside create_secret ------')
    mysecretresponse = service_client.describe_secret(SecretId=arn)
    # we need this unicode conversion because the tags are in unicode and we have back errors
    for tag in mysecretresponse['Tags']:
        if tag['Key'] == 'instanceid':
            instance = unicodedata.normalize('NFKD', tag['Value']).encode('ascii','ignore')

    print('working on instnaceid '+ str(instance))
    client = boto3.client('ssm')

    change_password = [
        "$password = (Get-SSMParameterValue -Name " + instance + " -WithDecryption $True).Parameters[0].Value",
        "$computers = Hostname",
        "$changeuser = \"Administrator\"",
        "Foreach($computer in $computers)",
        "	{",
        "     $user = [adsi]\"WinNT://$computer/$changeuser,user\"",
        "     $user.SetPassword($password)",
        "     $user.SetInfo()",
        "	}"
    ]

    try:
        # Generate a random password
        print('Generating new password')
        #I choose to have 12*3 = 36 charaters because it is working also in win 2019, with 18 works on win 2012 r
        #also I combined in this way from 3 to 1 because otherwise in win2019 was failing for password policy
        singlepasswordlengh=12
        excludechars='/@"\'\\'
        passwd1 = service_client.get_random_password(ExcludeCharacters=excludechars, PasswordLength=singlepasswordlengh, ExcludeNumbers=False, ExcludePunctuation=False, ExcludeUppercase=False, ExcludeLowercase=False, RequireEachIncludedType=True)
        passwd2 = service_client.get_random_password(ExcludeCharacters=excludechars, PasswordLength=singlepasswordlengh, ExcludeNumbers=False, ExcludePunctuation=False, ExcludeUppercase=False, ExcludeLowercase=False, RequireEachIncludedType=True)
        passwd3 = service_client.get_random_password(ExcludeCharacters=excludechars, PasswordLength=singlepasswordlengh, ExcludeNumbers=False, ExcludePunctuation=False, ExcludeUppercase=False, ExcludeLowercase=False, RequireEachIncludedType=True)
        passwd=passwd1['RandomPassword']+passwd2['RandomPassword']+passwd3['RandomPassword']
        # Put the secret
        print('Put the new password in a secret')
        secureString='{ \"Administrator\": \"'+ passwd +'\"\n }'
        service_client.put_secret_value(SecretId=arn,  ClientRequestToken=token, SecretString=secureString, VersionStages=['AWSCURRENT'])
        logger.info("createSecret: Successfully put secret for ARN %s and version %s." % (arn, token))

        #create a parameter store to pass the new generated password in a secure way
        print('Create a secure parameter')
        response = client.put_parameter(
            Name=instance,
            Description='tmp to pass in a secure way a password to a ec2 machine',
            Value=passwd,
            Type='SecureString',
            KeyId=kms_key_id,
            Overwrite=True,
        )

        print('Send command to change the password to the instance')
        response = client.send_command(InstanceIds=[instance],DocumentName='AWS-RunPowerShellScript', Parameters={ 'commands': change_password },)

        # Before delete the parameter we need to wait some seconds that the powershell will be executed
        # the above send_command is asyncronous
        print('sleepping')
        time.sleep(10)
        print('Delete parameter')
        response = client.delete_parameter(Name=instance)
        return True
    except Exception as e:
        print("Error")
        print(e)
        return False


def set_secret(service_client, arn, token):
    print('------ Inside set_secret ------')
    print('nothing to be done here left because secret manager needs to call this')
    return True


def test_secret(service_client, arn, token):
    print('------ Inside test_secret ------')
    print('nothing to be done here left because secret manager needs to call this')
    return True

def finish_secret(service_client, arn, token):
    print('------ Inside finish_secret ------')
    print('nothing to be done here left because secret manager needs to call this')
    return True
