import boto3

def get_api_key():
    """ Getting API keys from the AWS parameter store ssm(secret store manager)"""
    ssm = boto3.client("ssm", region_name="us-east-1")

    response= ssm.get_parameter(
        Name="LANGSMITH_API_KEY",
        WithDecryption=True
    )

    LANGSMITH_API_KEY= response["Parameter"]["Value"]

    return LANGSMITH_API_KEY
