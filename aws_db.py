import re
import sys
import time
import boto3
import datetime
import aws_url
from aws_config import *
from parse_key_value import *
from boto3.dynamodb.conditions import Key, Attr


# helper functions
def is_int(s): return re.match(r"[-+]?\d+$", s) is not None
def get_seconds(): return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()


session = boto3.session.Session(aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=AWS_REGION)
client = session.client('dynamodb')


def _is_valid_key(k):
	if k.startswith("SquadRank"): return True
	if k.startswith("TotalXP"): return True
	if k.startswith("Playing with"): return True
	if k.startswith("Damage Done"): return True
	if k.startswith("Kill"): return True
	if k.startswith("Revive"): return True
	if k.startswith("Respawn"): return True
	if k.startswith("Top "): return True
	if k.startswith("Champion"): return True
	if k.startswith("Won"): return True
	if k.startswith("First Kill"): return True
	if k.startswith("Earn"): return True
	return False	


def _adjust_key(k):
	# for some keywords we removed the starting paranthesis, but we need it in order to parse the right number into database
	# so we add the paranthesis again here!
	_keywords = ["Damage Done"]
	for keyword in _keywords:
		if k.startswith(keyword) and not (k.startswith(keyword+" (") or k.startswith(keyword+"(")):
			k = k.replace(keyword, keyword+" (") 
			print("--", k) 
	
	if k.find("(") >= 0: k = k.split("(")[0]
	k = k.strip().replace(" ","")
	return k


def _extract_number(s):
	s = s.replace("xll","x11").replace("xl","x1")
	n = 0
	for ch in s:
		if ord(ch) >= ord("0") and ord(ch) <= ord("9"):
			n = n*10+int(ch)
	return n
	


# returns a list of all screens
def get_screens(job_id):
	job_id = str(job_id)
	ll = []
	for screen_id in range(1000):
		id = job_id + "_" + str(screen_id)
		response = client.get_item(TableName='jobs_screens_raw', Key={'Id':{"S":id}})
		if not ('Item' in response): break
		
		# normalize the item
		item = response['Item']
		for key in item:
			for x in item[key]:
				item[key] = item[key][x]
				break
		
		ll += [item]
	print(len(ll))
	return ll


def add_screen_raw(job_id, screen_id, fname, fname_original, timestamp, frame_id, kv_output, is_false_positive, are_stats_correct, is_missing, fname2):
	job_id = str(job_id)
	id = job_id + "_" + str(screen_id)
	item = {
		'Id': {'S': id},
		'JobId': {'S': job_id},
		'ScreenId': {'N': str(screen_id)},
		'Timestamp': {'S': timestamp},
		'FrameId': {'S': str(frame_id)},
		'ScreenS3Url': {'S': fname},
		'ScreenS3UrlOriginal': {'S': fname_original},
		'KVOutput': {'S': kv_output},
		'IsFalsePositive': {'S': str(is_false_positive)},
		'AreStatsCorrect': {'S': str(are_stats_correct)},
		'IsMissing': {'S': str(is_missing)},
		'Fname2': {'S': str(fname2)}
	}
	response = client.put_item(TableName='jobs_screens_raw', Item=item)









def _insert_kv_output_into_jobs_screens(job_id, screen_id, timestamp, stream_url, player_name, character, fname, fname_original, kv_output):
	kv_list = parse_key_value_to_list(kv_output)
	for ii,x in enumerate(kv_list):
		k,v,str_orig = x 
		if not _is_valid_key(k): continue
		if v == "" or v is None or not is_int(v): continue
		v = int(v) 
		k = _adjust_key(k) 

		if k in ["DamageDone","Kills"]:
			str2 = str_orig
			pos = str2.find("=>")
			if pos > 0: str2 = str2[:pos]
			v = _extract_number(str2)
			print("Fixed field [%s] to [%d] (original string: [%s])" % (k, v, str_orig))
			
		print("[%s] = [%d]" % (k,v)) 

		item_id = str(job_id) + "_" + str(screen_id) + "_" + str(ii)
		item = {
			'Id': {'S': item_id},
			'JobId': {'S': str(job_id)},
			'ScreenId': {'N': str(screen_id)},
			'Game': {'S': "apex"},
			'Timestamp': {'S': timestamp},
			'StreamUrl': {'S': stream_url},
			'ScreenS3Url': {'S': fname},
			'ScreenS3UrlOriginal': {'S': fname_original},
			'PlayerName': {'S': player_name},
			'StatName': {'S': k},
			'StatValue': {'N': "%d" % v},
			'StatOriginalString': {'S': str_orig},
			'Imported': {'BOOL': False},
			'importDocId': {'S': "  "},
			'matchGroupId': {'S': "  "},
			'character': {'S': character}
		}
		response = client.put_item(TableName='jobs_screens', Item=item)

		response = client.get_item(TableName='jobs_screens', Key={'Id':{"S":item_id}})
		if not ('Item' in response): 
			print("Failed to put jobs_screens entry: [%s]=%d" % (k,v))
		item = response['Item']
		print("jobs_screens entry check: [%s]=[%s]" % (item['StatName']['S'],item['StatValue']['N'])) 




def add_screen(job_id, fname, fname_original, timestamp, frame_id, kv_output, is_false_positive, are_stats_correct, is_missing, character):
	job_id = str(job_id)
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	item = response['Item']
	
	list_screens = get_screens(job_id)
	screen_id = len(list_screens)
	
	add_screen_raw(job_id, screen_id, fname, fname_original, timestamp, frame_id, kv_output, is_false_positive, are_stats_correct, is_missing, "-")

    #
	# add screen info to the jobs_screens table
	#

	timestamp = timestamp.split(":")[0] if timestamp.find(":") > 0 else timestamp	# for some reasons we get timestamps as X:Y need just the X part
	kv_output = kv_output.split("[RAW]")[-1]
	
	stream_url = item['stream']['S']
	player_name = item['handle']['S']

	_insert_kv_output_into_jobs_screens(job_id, screen_id, timestamp, stream_url, player_name, character, fname, fname_original, kv_output)



def add_screen_cod(job_id, fname, fname2, timestamp, frame_id, kv_output, is_false_positive, are_stats_correct, is_missing):
	job_id = str(job_id)
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	item = response['Item']
	
	list_screens = get_screens(job_id)
	screen_id = len(list_screens)
	
	add_screen_raw(job_id, screen_id, fname, fname2, timestamp, frame_id, kv_output, is_false_positive, are_stats_correct, is_missing, fname2)
	

    #
	# add screen info to the jobs_screens table
	#

	#fname = ... we already have this
	timestamp = timestamp.split(":")[0] if timestamp.find(":") > 0 else timestamp	# for some reasons we get timestamps as X:Y need just the X part
	
	stream_url = item['stream']['S']
	player_name = item['handle']['S']

	ii = -1
	for str_orig in kv_output.split("\n"):
		k,v = str_orig.split("=")
		ii += 1
		
		print("kv: %s=%s" % (k,v))

		v = int(v) 
		k = _adjust_key(k) 
		item_id = str(job_id) + "_" + str(screen_id) + "_" + str(ii)
		item = {
			'Id': {'S': item_id},
			'JobId': {'S': str(job_id)},
			'ScreenId': {'N': "%d"%screen_id},
			'Game': {'S': "cod"},
			'Timestamp': {'S': timestamp},
			'StreamUrl': {'S': stream_url},
			'ScreenS3Url': {'S': fname},
			'PlayerName': {'S': player_name},
			'StatName': {'S': k},
			'StatValue': {'N': "%d" % v},
			'StatOriginalString': {'S': str_orig},
			'Imported': {'BOOL': False},
			'importDocId': {'S': "  "},
			'matchGroupId': {'S': "  "},
			'character': {'S': character}
		}
		response = client.put_item(TableName='jobs_screens', Item=item)




		




def _compute_job_minutes_diff(item):
	d1_ts = int(item['date']['S']) 
	d2_ts = get_seconds()
	minutes_diff = (d2_ts-d1_ts)/60
	return minutes_diff


def _stop_job(item):
	job_id = item['id']['S'] 
	if job_id == "0": return 	# skip job 0 which is status

	print("Stop job: %s" % job_id)
	
	status = get_job_status(job_id)
	if not status.startswith('Started'): return
	set_job_status(job_id, "Done")

	item['end_date']['S'] = "%.0f" % get_seconds() #datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	client.put_item(TableName='jobs', Item=item)
	

def stop_job(job_id):
	job_id = str(job_id)
	if job_id == "0": return False
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		_stop_job(item)
		return True
	return False
		 

def stop_all_jobs():
	response = client.scan(TableName='jobs_active')
	for item in response['Items']:
		job_id = item['id']['S'] 
		stop_job(job_id)
		

def get_item_from_jobs_table(job_id):
	job_id = str(job_id)
	if job_id == "0": return None
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		return item
	return None
		
		


def mark_job_active_as_online(job_id, state):
	job_id = str(job_id)
	if job_id == "0": return False
	response = client.get_item(TableName='jobs_active', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		item["online"] = {"BOOL": state}
		client.put_item(TableName='jobs_active', Item=item)
		return True
	return False



# set job is_alive field
# flag must be:
#	0: definitely not alive
#	1: definitely alive
#	2: uncertain
def set_alive_flag(job_id, flag):
	assert flag in [0,1,2]
	
	print("changing set_alive_flag: job [%s] is_alive: [%d]" % (job_id, flag))
	
	job_id = str(job_id)
	if job_id == "0": return False
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		item["is_alive"] = {"S": "%d" % flag}
		client.put_item(TableName='jobs', Item=item)
		return True
	return False






def stop_expired_jobs():
	response = client.scan(TableName='jobs_active')
	for item in response['Items']:
		job_id = item['id']['S']
		if job_id == "0": continue
		status = get_job_status(job_id)
		if not status.startswith('Started'): continue

		item2 = get_item_from_jobs_table(job_id)
		if item2 is None: continue

		minutes = int(item2['minutes']['S'])
		minutes_diff = _compute_job_minutes_diff(item2)
		#print("[stop expired jobs] job: %s ---> minutes_diff: %d" % (item['id']['S'], minutes_diff))
		if minutes_diff >= minutes:
			stop_job(job_id) 



def set_status(is_streaming, last_frame_time, last_summary_time):	
	response = client.put_item(
	    TableName='jobs',
	    Item={
	    	'id': {'S': '0'},
	        'date': {'S': "%.2f" % get_seconds()},
	        'is_streaming': {'S': '%d' % is_streaming},
	        'last_frame_time': {'S': last_frame_time},
	        'last_screen_time': {'S': last_summary_time}
	    }
	)





# returns: is_started, is_streaming, last_frame_time, last_summary_time
def get_status():
	response = client.get_item(TableName='jobs', Key={'id':{"S":"0"}})
	is_started = 0
	is_streaming = 0
	last_frame_time = "-"
	last_screen_time = "-"
	if 'Item' in response:
		item = response['Item']
		
		ss = get_seconds()
		print(ss, float(item['date']['S']), ss - float(item['date']['S']))
		
		seconds = get_seconds()- float(item['date']['S'])
		is_started = 1 if (seconds < 60) else 0 # if we don't have a sign in the last 60 seconds consider the client stopped
		if is_started == 1:
			is_streaming = 1 if item["is_streaming"]["S"] != "0" else 0
			last_frame_time = item["last_frame_time"]["S"]
			last_screen_time = item["last_screen_time"]["S"] 
	
	return (is_started, is_streaming, last_frame_time, last_screen_time)
		
	



# returns url for given job_id or None if no such job 
def get_job_stream_url(job_id):
	job_id = str(job_id)
	if job_id == "0": return None
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:
		item = response['Item']
		return item['stream']['S']
	return None



# returns game type for given job or None if no such job 
def get_job_game_type(job_id):
	job_id = str(job_id)
	if job_id == "0": return None
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:
		item = response['Item']
		return item['game']['S']
	return None



# move jobs with status='Done' from table jobs_active to jobs_done
def copy_done_jobs(): 
	response = client.scan(TableName='jobs_active')
	ll = []
	
	delete_list = []
	for item in response['Items']:
		id = item['id']['S']
		if id == "0": continue	# skip job 0 which is status
		status = item['status']['S'] 
		if status == "Done":
			delete_list += [item['id']]
			client.put_item(TableName='jobs_done', Item=item)
			
	for id in delete_list:
		client.delete_item(Key={'id':id}, TableName='jobs_active')
	


def get_job_status(job_id):
	job_id = str(job_id)
	if job_id == "0": return ""

	# look for job status in table jobs_active, then in table jobs_done
	for table_name in ['jobs_active', 'jobs_done']:
		response = client.get_item(TableName=table_name, Key={'id':{"S":job_id}})
		if 'Item' in response:
			item = response['Item']
			return item['status']['S']
	return "Done"	# assume it's done if we can't find it in either table


# search job in table jobs_active, change its status
# if status=='Done' move the item from jobs_active to jobs_done
def set_job_status(job_id, new_status):
	job_id = str(job_id)
	if job_id == "0": return False

	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:
		item = response['Item']
		item['status'] = {"S":new_status}	
		client.put_item(TableName='jobs', Item=item)

	response = client.get_item(TableName='jobs_active', Key={'id':{"S":job_id}})
	if 'Item' in response:
		item = response['Item']
		item['status']['S'] = new_status
		item['last_update'] = {'S':'%.2f' % get_seconds()}		# also update last_update field when changing job status!
		
		if new_status == "Done":
			client.put_item(TableName='jobs_done', Item=item)
			client.delete_item(Key={'id':item['id']}, TableName='jobs_active')
		else:
			client.put_item(TableName='jobs_active', Item=item)
		return True
	return False



def get_unprocessed_jobs():
	resp = client.scan(TableName='jobs_active')
	id_list = []
	for item in resp['Items']:
		id = item['id']['S']
		if id == "0": continue				# skip job 0 which is status
		status = item['status']['S']
		if status == 'Done': continue       # skip finished items
		
		#print("job: %d status: [%s] %d" % (id, status, status.startswith("Started")))
		
		if status.startswith("Started"):
			last_update = float(item['last_update']['S']) if 'last_update' in item else 0
			dt = get_seconds() - last_update
			print("[get_unprocessed_jobs] job: %s last_update: %d dt: %d" % (id,last_update, dt))
			if dt > 3*60:
				# make sure this item is not marked as online when it's not
				if "online" in item:
					if item["online"]["BOOL"] == True:
						mark_job_active_as_online(id, False)
				id_list += [id]
		else:
			id_list += [id] 
	return id_list



# returns last_update (utc seconds) or -1 if job_id does not exists
def get_last_update(job_id):
	job_id = str(job_id)
	if job_id == "0": return -1
	for table_name in ["jobs_active","jobs_done"]:
		response = client.get_item(TableName=table_name, Key={'id':{"S":job_id}})
		if 'Item' in response:
			item = response['Item']
			try: return float(item['last_update']['S'])
			except: pass
	return -1



# for given job_id - set last_update field to number of UTC clock seconds
# returns True if successful, False otherwise 
def set_last_update(job_id):
	job_id = str(job_id)
	if job_id == "0": return False
	for table_name in ["jobs_active","jobs_done"]:
		response = client.get_item(TableName=table_name, Key={'id':{"S":job_id}})
		if 'Item' in response:
			item = response['Item']
			item['last_update'] = {'S':'%.2f' % get_seconds()}
			client.put_item(TableName=table_name, Item=item)
			
			print("[set_last_update] job_id: %s" % str(job_id))
			sys.stdout.flush()
			return True 
	return False


def set_legend_name(job_id, name):
	job_id = str(job_id)
	print("set_legend_name %s [%s]" % (job_id, name))
	if job_id == "0": return False
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		item['character'] = {'S': "%s" % name} 
		client.put_item(TableName='jobs', Item=item)
	

def get_legend_name(job_id):
	job_id = str(job_id)
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		if 'character' in item: 
			return item['character']['S']
	return ""



def add_kill(job_id, timestamp, character, kill_nr):

	job_id = str(job_id)
	timestamp = str(timestamp)

	print("[%s] add kill" % job_id)

	# get tournamentid squadid streamurl screenid from table jobs
	tournamentId = " "
	squadId = " "
	streamUrl = " "
	
	response = client.get_item(TableName='jobs', Key={'id':{"S":job_id}})
	if 'Item' in response:	
		item = response['Item']
		if 'tournamentId' in item: tournamentId = item['tournamentId']['S'] 
		if 'squadId' in item: squadId = item['squadId']['S'] 
		if 'stream' in item: streamUrl = item['stream']['S'] 


	id = job_id + "_" + timestamp
	item = {
		'Id': {'S': id},
		'JobId': {'S': job_id},
		'Timestamp': {'S': timestamp},
		'Character': {'S': character},
		'TournamentId': {'S': tournamentId},
		'SquadId': {'S': squadId},
		'StreamUrl': {'S': streamUrl},
		'Kills': {'S': "%d" % kill_nr}
	}
	response = client.put_item(TableName='jobs_kills', Item=item)




if __name__ == "__main__":
	k = "Kills"
	str2 = "Kills (xl] =>  +50"	
	pos = str2.find("=>")
	if pos > 0: str2 = str2[:pos]
	print(str2)
	v = _extract_number(str2)
	print("Fixed field [%s] to [%d] (original string: [])" % (k, v)) 
	