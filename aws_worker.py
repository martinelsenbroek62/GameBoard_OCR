import cv2
import json
import uuid
import numpy as np
import subprocess as sp
import os,sys,time,datetime,random
import datetime

from recognize import *
import aws_db
from aws_status import send_status
from convert_img import *

import threading
from queue import Queue
from threading import Thread

from aws_textract import *
import json_parser as parser
from parse_key_value import *

from func_cod import extract_stats_cod, check_if_warzone_victory

worker_uuid = str(uuid.uuid4())[:10]


def _get_seconds(): return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
def _timestamp():
	milliseconds = int(time.time()*1000.0) % 1000.0  
	return _get_seconds()*1000.0 + milliseconds


worker_lock = threading.Lock()

# AWS worker thread
class AWSWorker(threading.Thread):
	def __init__(self, queue):
		threading.Thread.__init__(self, args=(), kwargs=None)
		self.queue = queue
		self.daemon = True


	def run(self):
		while True:	
			val = self.queue.get()
			if val is None: return		# None will quit thread

			with worker_lock:
				alias, image, image2, frame_idx, timestamp, game_type, n1, n2, n3, character = val
				image = image.copy()
				
				print("aws worker => game type [%s]" % game_type)
	
				if game_type == "apex":

					image_original = image.copy()

					if is_good_candidate_team_summary(image):
						if is_best_team_summary(image):
							enhance_position_team(image)
					else:
						enhance_position(image)
						
					# improve brigthness and contrast for the captured image
					# in order to get better text recognition
					#enhance_position(image)
					image = automatic_brightness_and_contrast(image)
	
					replace_damage_done(image)

					ts = _timestamp()
					fname_tmp = "tmp_%s_%d.jpg" % (alias,ts)
					fname_s3 = "%s_%d.jpg" % (alias, ts)
					fname_s3_original = "%s_%d_original.jpg" % (alias, ts)
					cv2.imwrite(fname_tmp, image)
					
					fname_tmp_original = "tmp_%s_%d_original.jpg" % (alias, ts)
					cv2.imwrite(fname_tmp_original, image_original)

					if s3_upload_file(fname_tmp, fname_s3) and s3_upload_file(fname_tmp_original, fname_s3_original):
						json = textract(fname_s3)
						if json:
							# add screen to job
							#n_sec = frame_idx//30
							n_sec = timestamp
							timestamp_str = "%d" % (timestamp//1000)
	
							v1 = parser.extract_team_info(json)
							v2 = parser.extract_player_info(json)
							kv_output = v2 if len(v2) > len(v1) else v1
							
							# parse key/value fields							
							kv_output = parse_key_value(kv_output)
	
							print(fname_s3, kv_output)
	
							is_ok = kv_output.find("Squad Placed: ?? Total Kills: ??") < 0
							
							if is_ok:
								job_id = alias
								aws_db.add_screen(job_id, fname_s3, fname_s3_original, timestamp_str, "%d" % frame_idx, kv_output, 0, 0, 0, character)
							else:
								print("not ok ... skipping")
						else:
							print("cannot textract %d" % frame_idx)
					else:
						print("cannot upload %d" % frame_idx)
	
					os.unlink(fname_tmp)
					os.unlink(fname_tmp_original)
					
				elif game_type == "cod":

					big_image = image
					stat_list = extract_stats_cod(big_image)

					print("[COD]")
					if check_if_warzone_victory(image2):
						print("  warzone victory, setting team place to #1")
						stat_list = [1, stat_list[1], stat_list[2]]
						n1 = 1 
					print("  stats: ", stat_list)

					kv_output = "NumberOfTeams=%d\nNumberOfPlayers=%d\nKills=%d" % (n1,n2,n3)
					kv_output += "\nNumberOfTeams2=%d\nNumberOfPlayers2=%d\nKills2=%d" % (stat_list[0], stat_list[1], stat_list[2])
				
					ts = timestamp+1
					fname2_tmp = "tmp_%d.jpg" % ts
					fname2_s3 = "%s_%d.jpg" % (alias, ts)
					cv2.imwrite(fname2_tmp, image2)

					ts = timestamp
					fname_tmp = "tmp_%d.jpg" % ts
					fname_s3 = "%s_%d.jpg" % (alias, ts)
					cv2.imwrite(fname_tmp, big_image)

					if s3_upload_file(fname_tmp, fname_s3) and s3_upload_file(fname2_tmp, fname2_s3):
						print(kv_output)
						job_id = alias
						timestamp_str = "%d" % (ts//1000)
						aws_db.add_screen_cod(job_id, fname_s3, fname2_s3, timestamp_str, "%d" % frame_idx, kv_output, 0, 0, 0)
					else:
						print("cannot upload %d" % frame_idx)
						
					os.unlink(fname_tmp)
					os.unlink(fname2_tmp)
					
				else:
					print("Unknown game type [%s]" % game_type)

			time.sleep(0.01)


