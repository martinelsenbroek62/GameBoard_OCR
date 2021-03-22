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
from parse_key_value import *

from model_cod import *
from aws_worker import AWSWorker
from func_cod import extract_stats_cod, StreamProcessorCOD

from kills_tracker import *



ALIVE_NO = 0
ALIVE_YES = 1
ALIVE_UNKNOWN = 2


# Debug setting: set it to True to take random screenshots
TAKE_RANDOM_SCREENSHOT = False


worker_uuid = str(uuid.uuid4())[:10]


SKIP_FRAMES = 1								# skip each X frames - set to 1 for no skip
CHECK_LEGEND_AND_ALIVE_EACH_X_FRAMES = 15	# must be a multiple of SKIP_FRAMES (unless SKIP_FRAMES is 0)  

assert SKIP_FRAMES >= 1
assert CHECK_LEGEND_AND_ALIVE_EACH_X_FRAMES > 0
assert (CHECK_LEGEND_AND_ALIVE_EACH_X_FRAMES % SKIP_FRAMES) == 0  


def _get_seconds(): return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
def _timestamp():
	milliseconds = int(time.time()*1000.0) % 1000.0  
	return _get_seconds()*1000.0 + milliseconds



class StreamPlayerTwitch:
	
	def __init__(self, url, game_type, job_id):
		self.is_alive = ALIVE_UNKNOWN
		self.count = 0
		self.pipe = sp.Popen("streamlink -O %s best | ./ffmpeg -hide_banner -loglevel panic -i pipe:0 -vf scale=1280:720 -an -sn -f image2pipe -vcodec rawvideo -pix_fmt bgr24 -" % url, shell=True, stdout = sp.PIPE, bufsize=10**8)
		self.n_fail = 0
		self.timestamp = _timestamp()
		self.n_fail = 0
		self.game_type = game_type
		self.job_id = job_id
		self.skip_n_frames = 20 #if game_type == "apex" else 2
		self.cod_processor = StreamProcessorCOD(self.job_id) if game_type == "cod" else None
		self.last_alive_time = time.time()
		
		self.last_lobby_check_time = 0
		self.lobby_detected = False
		self.lobby_detected_time = 0
		
		assert game_type in ["apex", "cod"] 
	

	# check each 10 seconds if lobby is detected (apex) 
	def check_for_lobby(self, img):
		tt = time.time()
		if tt - self.last_lobby_check_time < 10: return
		self.last_lobby_check_time = tt
		self.lobby_detected = recognize_lobby(img)
		if self.lobby_detected: 
			self.lobby_detected_time = tt
			
	# returns number of seconds since last lobby screen was detected (apex)
	def get_seconds_since_lobby_detected(self):
		return time.time() - self.lobby_detected_time


	def mark_as_alive(self):
		self.is_alive = ALIVE_YES
		self.last_alive_time = time.time()
	
	
	def get_frame_idx(self):
		return self.count
	

	def set_skip_frames(self, v):
		pass	# not needed for now


	def read_image(self):
		
		myProcessIsRunning = self.pipe.poll() is None  
		if not myProcessIsRunning:
			print("process is not running, something happened")
			self.n_fail = 101
			return None

		if self.is_done(): 
			return None
	
		# skip some frames
		for _ in range(self.skip_n_frames): 
			raw_image = self.pipe.stdout.read(1280*720*3)
			if raw_image is not None: break
			time.sleep(0.01)
			
		if raw_image is None:
			self.n_fail += 1
			return None
			
		self.count += 1
		self.timestamp = _timestamp()

		image = np.frombuffer(raw_image, dtype='uint8')
		
		if self.count % SKIP_FRAMES != 0: 
			return None

		try:
			image = image.reshape((720,1280,3))
		except:
			print("something wrong with the stream, restarting")
			self.n_fail = 101
			return None

		if self.game_type == "apex":
			
			_type = 1 if is_good_candidate_team_summary(image) else 2 if is_good_candidate_single_player(image) else 0 			 
	
			if self.count % CHECK_LEGEND_AND_ALIVE_EACH_X_FRAMES == 0: 
				if self.is_alive != ALIVE_NO and (check_if_spectating(image) or _type > 0): 
					self.is_alive = ALIVE_NO
					self.last_alive_time = time.time()
	
				if check_squads_left(image) or check_map_icon(image) or check_deathbox_close(image) or recognize_inventory_screen(image): 
					self.is_alive = ALIVE_YES
					self.last_alive_time = time.time()
				else:
					self.check_for_lobby(image)
					if self.lobby_detected:
						self.is_alive = ALIVE_NO	
						self.last_alive_time = time.time()
			
				
				# if last status is alive and we haven't seen an alive confirmation during the last 5 minutes
				# set it to uncertain (but not if we detected lobby during last 30 seconds)
				if self.is_alive == ALIVE_YES and time.time() - self.last_alive_time > 300: 				
					if self.get_seconds_since_lobby_detected() >= 30:
						self.is_alive = ALIVE_UNKNOWN
				
			if TAKE_RANDOM_SCREENSHOT:
				# DEBUG code: random screenshot each 500 frames
				if random.randint(0,1000) < 2:
					ts = _timestamp()
					fname_tmp = "tmp_%d.jpg" % ts
					fname_s3 = "screenshot_random_%d.jpg" % ts
					cv2.imwrite(fname_tmp, image)
					if s3_upload_file(fname_tmp, fname_s3):
						print("random screenshot: %s" % fname_s3)
					else:
						print("random screenshot: problem uploading file")								 
		 
			#if _type > 0:
			return image,_type

		elif self.game_type == "cod":
			ret = self.cod_processor.process_frame(image)
			if ret is None: return None
			big_image,n1,n2,n3 = ret
			return big_image, image, n1, n2, n3
		else:
			pass

		return None
		

	def is_done(self):
		return self.n_fail > 100		




if __name__ == "__main__":

	def main_function():
		status_str = "Started " + worker_uuid

		q_in = Queue()
		aws_worker = AWSWorker(q_in)
		aws_worker.start()
	
		last_frame_time = "-"
		last_summary_time = "-"
	
		while True:
			aws_db.stop_expired_jobs()

			job_list = aws_db.get_unprocessed_jobs()
			#job_list = [x for x in job_list if len(x)<=25]	# this is just for my tests, my job_id are small  
			
			print("unprocessed jobs: ", job_list)
			
			if job_list == []:
				print(" no active jobs, waiting")
				sys.stdout.flush()
				time.sleep(35)
				continue

			job_id = random.choice(job_list)
			game_type = aws_db.get_job_game_type(job_id)
			
			if not game_type in ["cod","apex"]:
				print("job %s - unsupported game type %s" % (str(job_id), str(game_type)))
				continue 

			print("trying to start job %s game_type: %s" % (str(job_id), game_type))
			aws_db.set_job_status(job_id, status_str)
				
			another_worker_took_the_job = False
			for _ in range(4):
				time.sleep(3)
				if aws_db.get_job_status(job_id) != status_str:
					print("other worker took the job, waiting")
					sys.stdout.flush()
					another_worker_took_the_job = True
					break
			
			if another_worker_took_the_job:
				time.sleep(15)
				continue
			
			print("all ok, starting streaming")
			sys.stdout.flush()
			stream_url = aws_db.get_job_stream_url(job_id)
			if stream_url is None:
				print("  error getting stream url")
				sys.stdout.flush()
				time.sleep(5)
				continue

			fname = stream_url
			alias = "%s" % str(job_id) 

			print("[Streaming job %s] %s \n" % (alias, stream_url))
			#aws_db.mark_job_active_as_online(job_id, True)
			send_status(1, "-", "-")
	
			# we keep track of last image and frame_idx where we identified a valid summary
			# this is because we want to delay the recognition with a number of frames
			# due to the fact that when summary appears there is a delay until all relevant
			# info is printed and we want to send only one summary to the AWS textract
			# in order to minimize bandwidth/costs
			last_good_image = None
			last_good_frame_idx = 0
			last_good_timestamp = 0
			last_good_image_type = 0		# we also remember last good image type - 1 for single player stats / 2 for team / 0 none
			last_good_image_time = 0	
			last_frame_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
	
			last_character = " "
	
			kills_tracker = KillsTrackerApex()

			# we assume we are dealing with a url
			try:
				stream = StreamPlayerTwitch(fname, game_type, alias)
			except Exception:
				print("  stream offline or some kind of error appeared, restarting job check\n")
				#aws_db.mark_job_active_as_online(job_id, False)
				send_status(0, last_frame_time, last_summary_time)
				time.sleep(20)
				continue 
		
			def send_last_good_image_to_aws_apex(last_good_image, last_good_frame_idx, last_good_timestamp):
				print("====> sending %d" % last_good_frame_idx)
				if is_good_candidate_single_player(last_good_image):
					aws_worker.queue.put((alias, last_good_image, None, last_good_frame_idx, last_good_timestamp, "apex", 0, 0, 0, last_character))
				else: 
					print("  not a good candidate")
							

			last_alive_status = ALIVE_UNKNOWN
			aws_db.set_alive_flag(job_id, stream.is_alive)

			# we remember last legend name identified and last time we checked for name
			# if name is Unknown check each 10 seconds for a change
			# if name is not Unknown check each 30 seconds for a change 
			last_legend_name = "Unknown"
			last_legend_check_time = 0
			
			# by default mark legend name as unknown
			aws_db.set_legend_name(job_id, " ") 

			# mark stream as online only after 5 seconds in order to avoid very fast online/offline changes
			stream_start_time = time.time()
			marked_as_online = False
			DT_CHECK_MARKED_AS_ONLINE = 5	# 5 seconds
			
			t0 = time.time()
			t00 = t0
			while not stream.is_done():
			
				# check marked_as_online
				if not marked_as_online:
					dt = time.time() - stream_start_time
					if dt >= DT_CHECK_MARKED_AS_ONLINE:
						print("marking job %s as online" % str(job_id))
						aws_db.mark_job_active_as_online(job_id, True)
						marked_as_online = True
			
				# if during last 180 seconds got an image: go into frame by frame mode
				dt = time.time() - last_good_image_time
				stream.set_skip_frames(dt >= 180.0)
	
				ret = stream.read_image()
				current_image, current_type = None, 0

				if ret is not None:
					if game_type == "apex":
						current_image, current_type = ret
						
						# check for legend name change
						tt = time.time()
						dt = tt-last_legend_check_time
						if dt >= 30 or (last_legend_name == "Unknown" and dt >= 10):
							last_legend_check_time = tt
							name = recognize_apex_legend_name(current_image)
							if name != last_legend_name:
								print("Found character: [%s] (previous [%s]" % (name, last_legend_name))
								if name != "Unknown" and len(name) >= 3:
									last_character = name
									last_legend_name = name
									aws_db.set_legend_name(job_id, name)
								
									# incidentally this also means the stream is alive
									stream.mark_as_alive()
								

						# check for kills number changed
						if current_image is not None:
							nr = kills_tracker.check_if_kills_number_changed(current_image)
							if nr >= 0:
								print("kills number changed to %d" % nr)
								aws_db.add_kill(job_id, _timestamp(), last_character, nr)


						# reset legend name somewhere between 90-120 seconds since lobby was last detected
						if last_character != " ":
							dt_lobby = stream.get_seconds_since_lobby_detected()
							if dt_lobby >= 90 and dt_lobby < 120 and stream.is_alive != ALIVE_YES:
								print("resetting legend name")
								last_character = " "
								aws_db.set_legend_name(job_id, " ")
								
					
						if current_type > 0: 
							last_summary_time = last_frame_time
							last_good_image_time = time.time()
							last_good_timestamp = stream.timestamp  
						
						# if we switched from team summary to player summary -> emit last good image
						if current_type > 0 and last_good_image_type > 0 and current_type != last_good_image_type:
							if aws_db.get_job_status(job_id) == status_str:
								if is_good_candidate_single_player(image):
									send_last_good_image_to_aws_apex(last_good_image, last_good_frame_idx, last_good_timestamp)
			
						# if we are dealing with team summary: 
						# replace current image only if we didn't find a better one
						if current_type == 1:
							if (current_image is not None) and (last_good_image is not None):
								if not is_best_team_summary(current_image):
									if is_best_team_summary(last_good_image):
										current_image = last_good_image   
						
						if current_type > 0:
							last_good_image = current_image
							last_good_image_type = current_type
							last_good_frame_idx = stream.get_frame_idx()
					
						# check is_alive status changes
						if last_alive_status != stream.is_alive:
							last_alive_status = stream.is_alive
							aws_db.set_alive_flag(job_id, stream.is_alive)

					elif game_type == "cod":
						current_image, image2, n1, n2, n3 = ret
						frame_idx = stream.get_frame_idx()
						print("====> sending %d" % frame_idx)

						# for keras we need to call a model_predict first before it is called from another thread
						# so we do this here ...
						character = " "
						model_predict(current_image[:15,:5])
						aws_worker.queue.put((alias, current_image, image2, frame_idx, stream.timestamp, "cod", n1, n2, n3, character))
					else:
						pass
									
				if game_type == "apex":

					#!!! debug
					#if random.randint(0,1000) <= 4:
					#	print("Random alive status check: last_alive_status: %d stream.is_alive: %d" % (last_alive_status, stream.is_alive))
					#	print("  squads_left: %d" % check_squads_left(current_image))
					#	print("  map_icon: %d" % check_map_icon(current_image))
					#	print("  deathbox_close: %d" % check_deathbox_close(current_image))
					#	print()
					

					if stream.get_frame_idx() > last_good_frame_idx + 150:
						if last_good_image is not None:
							if last_good_frame_idx > 0:
								if aws_db.get_job_status(job_id) == status_str:
									send_last_good_image_to_aws_apex(last_good_image, last_good_frame_idx, last_good_timestamp)								
									last_good_image = None
									last_good_frame_idx = 0
									last_good_image_type = 0
									stream.set_skip_frames(1)
														
							
				# housekeeping - stop timed out jobs and check if current job remains on top
				# do this check each 60 seconds
				t1 = time.time()
				dt = t1-t0
				if t1-t0 > 80:
					#print("checking",stream.count, stream.last_summary_frame_idx, stream.count - stream.last_summary_frame_idx)
					print("checking")
					print("   current_legend_name: [%s]" % aws_db.get_legend_name(job_id))
					sys.stdout.flush()
					t0 = t1
					aws_db.stop_expired_jobs()
			
				t1 = time.time()
				if t1-t00 > 90:	# each 90 seconds update status so no other worker will take this job
					if aws_db.get_job_status(job_id) != status_str:
						print("other worker took the job or stream time finished, waiting")
						dt = time.time() - stream_start_time
						if dt >= DT_CHECK_MARKED_AS_ONLINE:
							print("marking job %s as offline" % str(job_id))
							aws_db.mark_job_active_as_online(job_id, False)
						sys.stdout.flush()
						time.sleep(25)
						break

					print("updating status")
					sys.stdout.flush()
					aws_db.set_last_update(job_id)
					t00 = t1
										
				
			# at this point stream is done, start looking for new jobs
			#if stream.is_done():
			#	aws_db.stop_job(job_id)
			print("job %s is done" % str(job_id))
			sys.stdout.flush()
			time.sleep(5)


	main_function()						
