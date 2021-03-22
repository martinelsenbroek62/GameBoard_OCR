import os,sys,time
import cv2
import numpy as np
from recognize import *
from streamlink import *

import threading
from queue import Queue
from threading import Thread

# _DEBUG = True if I do internal debugging tests, for production code should be False
_DEBUG = False	
_last_msec = [0]	# used when debugging, ignore for now

def _timestamp(): return int(time.time()*1000.0)


def _help():
	print("Usage: %s <stream url or local filename> <alias>" % sys.argv[0])
	print("where: ")
	print("   <stream url> is a twitch.tv stream (must start with http)")
	print("   <local filename> is a mp4 local file")
	print("   <alias> is the alias to use for the file to be stored on AWS S3")
	print("      files will be names as alias_<ts> where ts is a system timestamp")
	print("output:")
	print("   for each successful summary read:")
	print("   <S3_filename> <json returned by AWS textract>")
	print("make sure you have in aws_config.py the following defined:")
	print("  ACCESS_KEY = '...'")
	print("  SECRET_KEY = '...'")



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
				alias, image, frame_idx = val
	
				ts = _timestamp()
				fname_tmp = "tmp_%d.jpg" % ts
				fname_s3 = "%s_%d.jpg" % (alias, ts)
				cv2.imwrite(fname_tmp, image)
				
				if _DEBUG:
					video_msec = _last_msec[0]
					n_sec = int(video_msec/1000.0)					
					#n_sec = frame_idx//30
					
					txt = "%d => %d:%02d" % (frame_idx, n_sec//60, n_sec%60)
					print(txt)
					with open("data/capture/frames.txt","a+t") as fp:
						fp.write(txt+"\n") 

					fname = "data/capture/frame_%06d.jpg" % frame_idx
					cv2.imwrite(fname, image)
				else:
					if s3_upload_file(fname_tmp, fname_s3):
						json = textract(fname_s3)
						if json:
							print(fname_s3, json[:50])
						else:
							print("cannot textract %d" % frame_idx)
					else:
						print("cannot upload %d" % frame_idx)
				os.unlink(fname_tmp)

			time.sleep(0.01)







class StreamPlayerFile:
	
	def __init__(self, fname):
		self.count = 0
		self.vidcap = cv2.VideoCapture(fname)
		self.n_fail = 0
	

	def get_frame_idx(self):
		return self.count
	

	def read_image(self):
		#self.vidcap.set(cv2.CAP_PROP_POS_FRAMES, self.count)
		success,image = self.vidcap.read()
		self.count += 1
		if success:
			self.n_fail = 0
			_type = 1 if is_good_candidate_team_summary(image) else 2 if is_good_candidate_single_player(image) else 0 			 
			if _type > 0:
				if _DEBUG:
					_last_msec[0] = self.vidcap.get(cv2.CAP_PROP_POS_MSEC) 
				return image,_type
		else:
			self.n_fail += 1
		return None
		

	def is_done(self):
		return self.n_fail > 100		



class StreamPlayerTwitch:
	def __init__(self, url):
		session = Streamlink()
		streams = session.resolve_url(url).streams()
		
		session.set_option("hls-live-edge", 1)
		session.set_option("hls-segment-threads", 2)
	
		if _DEBUG: print(streams.keys())

		# choose 720p if possible, good enough for everything and saves bandwidth 
		stream_str = 'best'
		for x in streams:
			if x.startswith('720p'):
				stream_str = x
				break
		self.stream = streams[stream_str]  
		
		#self.stream = streams['best']
		#self.stream = streams['480p']
		#self.stream = streams['720p60']
		#self.stream = streams['1080p60']

		self.count = 0
		self.n_fail = 0

		# FPS = 1/X
		# X = desired FPS
		self.FPS = 1/30
		self.FPS_MS = int(self.FPS * 1000)
		
		self.start()

		
	def start(self):
		fname = "test.mpg"
		self.vid_file = open(fname,"wb")
		
		# dump from the stream into an mpg file -- get a buffer going
		self.fd = self.stream.open()
		print("Buffering...")
		for i in range(2*1024):
			new_bytes = self.fd.read(1024)
			self.vid_file.write(new_bytes)

		self.frame = None
		self.status = False
		self.capture = cv2.VideoCapture(fname)
		self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

		self.status, self.frame = self.capture.read()
		video_sec = self.capture.get(cv2.CAP_PROP_POS_MSEC)/1000.0
		self.start_time = time.time() + video_sec


	def update(self):
		if self.capture.isOpened():
			self.status, self.frame = self.capture.read()
			


	def get_frame_idx(self):
		return self.count
	

	def stop(self):
		self.capture.release()
		self.vid_file.close()
		self.fd.close()
		


	def read_image(self):
		n_total = 0
		for _ in range(2):
			new_bytes = self.fd.read(1024*8)
			self.vid_file.write(new_bytes)
			n_total += len(new_bytes)
		if n_total < 8*1024: return

		# play the video until it catches up with current time
		real_sec = time.time() - self.start_time
		video_sec = self.capture.get(cv2.CAP_PROP_POS_MSEC)/1000.0
		if video_sec > real_sec - 0.5: return None

		self.update()
		video_sec = self.capture.get(cv2.CAP_PROP_POS_MSEC)/1000.0
		while video_sec < real_sec - 2.0:  
			self.update()
			video_sec = self.capture.get(cv2.CAP_PROP_POS_MSEC)/1000.0
	
		success,image = self.status, self.frame
		self.count += 1
		if success:
			self.n_fail = 0 

			# uncomment those two lines to render the stream to screen
			if _DEBUG:
				cv2.imshow('frame', self.frame)
				cv2.waitKey(self.FPS_MS)
				
			_type = 1 if is_good_candidate_team_summary(image) else 2 if is_good_candidate_single_player(image) else 0 			 
			if _type > 0:
				return image, _type
		else:
			self.n_fail += 1

		# restart once in a while
		if self.count % 3000 == 0 and self.count > 0 and not _DEBUG:
			self.stop()
			self.start()

		return None
		

	def is_done(self):
		return self.n_fail > 100		



if __name__ == "__main__":
	
	if len(sys.argv) != 3:
		_help()
		sys.exit(0)
	
	fname = sys.argv[1]
	alias = sys.argv[2]

	from aws_textract import *
	
	q_in = Queue()
	aws_worker = AWSWorker(q_in)
	aws_worker.start()

	# we keep track of last image and frame_idx where we identified a valid summary
	# this is because we want to delay the recognition with a number of frames
	# due to the fact that when summary appears there is a delay until all relevant
	# info is printed and we want to send only one summary to the AWS textract
	# in order to minimize bandwidth/costs
	last_good_image = None
	last_good_frame_idx = 0
	last_good_image_type = 0		# we also remember last good image type - 1 for single player stats / 2 for team / 0 none
	last_team_summary_is_good = False

	# we assume everything starting with http is URL, everything else is file
	stream = StreamPlayerTwitch(fname) if fname.lower().startswith("http") else StreamPlayerFile(fname) 

	def send_last_good_image_to_aws(last_good_image, last_good_frame_idx):
		print("====> sending %d" % last_good_frame_idx)
		aws_worker.queue.put((alias, last_good_image, last_good_frame_idx))

	while not stream.is_done():
		ret = stream.read_image()
		current_image, current_type = None, 0
		if ret is not None:
			current_image, current_type = ret
			
			# if we switched from team summary to player summary -> emit last good image
			if current_type > 0 and last_good_image_type > 0 and current_type != last_good_image_type:
				send_last_good_image_to_aws(last_good_image, last_good_frame_idx)
				last_team_summary_is_good = False

			# if we are dealing with team summary: 
			# replace current image only if we didn't find a better one
			replace = True
			if current_type == 1:
				is_best = is_best_team_summary(current_image)
				if (last_team_summary_is_good) and (not is_best): replace = False
				if is_best: 
					last_team_summary_is_good = True 
			
			if replace:
				last_good_image = current_image
				last_good_image_type = current_type
				last_good_frame_idx = stream.get_frame_idx()
		  
		if stream.get_frame_idx() > last_good_frame_idx + 150:
			if last_good_image is not None:
				if last_good_frame_idx > 0:
					send_last_good_image_to_aws(last_good_image, last_good_frame_idx)								
					last_good_image = None
					last_good_frame_idx = 0
					last_good_image_type = 0
					last_team_summary_is_good = False
					
	time.sleep(120) 
