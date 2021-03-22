# Summary extractor from streams/video files

## Files

* stream_jobs.py: main program, will use latest job with Status='Started', end expired jobs, start new ones when available 
* stream_mp4.py: standalone script to play a stream or a video file, call it without params to see syntax
* recognize.py: code that does template matching over an image to check if it is a valid summary or not
* aws_textract.py: the code for AWS interactions with S3/textract
* aws_config.py: this is not included, you must create it as described below with your access/secret keys
* aws_db.py: all functions to interact with DynamoDb 
* aws_url.py: simple function to generate an image url for an image uploaded to a S3 bucket
* json_parser.py: a very basic json parser for the textract text
* aws_status.py: code to send status messages via a SQS queue


## Dependencies and installation

AWS-wise: needs the following:
* ec2 instance where to install all the code
* dynamoDb resource access with a table 'jobs' created
* must have a SQS queue created named 'status'

python dependencies:

* sudo yum install python37 (might not be necessary)
* sudo pip3 install pytz
* sudo pip3 install boto3
* sudo pip3 install numpy
* sudo pip3 install opencv-python-headless
* sudo pip3 install streamlink

 
streamlink module takes care of twitch/mixer streaming
boto3 is used for AWS communication

**Copy** aws_config_sample.py to **aws_config.py** that edit it with your access/secret/bucket name/region

## Usage

sudo python3 stream_jobs.py 

What it does:
* monitors the database for open stream jobs
* if one is marked as 'Started' will monitor the stream
* it will extract summary screens, upload them to s3 bucket, textract and do a summary parsing of textract 
* found screen data is entered in the database so the scoreboard-gui project can read them from there
* each 10 seconds it will check if the current project is stopped - if it is then it will start looking for the next job active
* also will check if any stream ran more than the allocated time interval