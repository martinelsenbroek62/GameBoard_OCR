import os
import json
import boto3
import logging
from aws_config import *
from botocore.exceptions import ClientError


_s3 = boto3.client("s3", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=AWS_REGION)
_textract = boto3.client("textract", aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=AWS_REGION)

# uploads a file with given credentials, returns True if ok
# else returns False and error is logged
def s3_upload_file(fname, s3_fname):
	try:
		_s3.upload_file(Bucket = AWS_BUCKET, Filename=fname, Key=s3_fname)
	except ClientError as e:
		logging.error(e)
		return False
	except FileNotFoundError as e:
		logging.error("File %s not found" % fname)
		return False
	return True		


# returns json string if conversion successful else None
def textract(fname):
	try:
		response = _textract.analyze_document(Document={'S3Object': {'Bucket': AWS_BUCKET, 'Name': fname}}, FeatureTypes= ['TABLES'])
	except ClientError as e:
		logging.error(e)
		return None
	except Exception:
		logging.error("Error in textract")
		return None

	return json.dumps(response)



if __name__ == "__main__":
	for root, dirs, files in os.walk(".", topdown=False):
		for name in files:
			fname = os.path.join(root, name)
			if not fname.endswith(".jpg") or fname.endswith(".png"): continue
			if os.path.exists(name[:-4]+'.txt'): continue 
			print("upload",name)
			s3_upload_file(name, name)
			print("extract")
			json_str = textract(name)
			with open(name[:-4]+'.txt',"wt") as fp: 
				fp.write(json_str)
	
