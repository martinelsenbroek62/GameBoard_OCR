import time,datetime
import boto3
from aws_config import *

import pytz
_pacific = pytz.timezone("US/Pacific")
def get_seconds(): return _pacific.utcoffset(datetime.datetime.now()).total_seconds() 

_session = boto3.session.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=AWS_REGION)
_sqs = _session.resource('sqs')
_queue = _sqs.get_queue_by_name(QueueName="status")


# send a status message to the queue
def send_status(checking_stream, last_frame_time, last_summary_time):
	seconds = get_seconds()
	msg = "%d|%s|%s|%.2f" % (checking_stream, last_frame_time, last_summary_time, seconds)
	#print("sending stats %s" % msg) 
	#!!! disabled for now
	#_queue.send_message(MessageBody=msg)
