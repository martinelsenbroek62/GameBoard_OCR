import os
import json
import boto3
import logging
from aws_config import *
from botocore.exceptions import ClientError

_s3 = boto3.client("s3", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=AWS_REGION)


def create_presigned_url(object_name, expiration=3600):
	try:
		response = _s3.generate_presigned_url('get_object', Params={'Bucket': AWS_BUCKET,'Key': object_name}, ExpiresIn=expiration)
	except ClientError as e:
		logging.error(e)
		return None
	return response

