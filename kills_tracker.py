import os
import cv2
import numpy as np
import time, datetime


_DEBUG = False
_SKIP_FRAMES = 5			# number of frames to skip, >= 1
_N_KILL_CONFIRMATIONS = 5	# need this many consecutive kill numbers 
							# in order to confirm that the kill number we recognized it correct  


assert _SKIP_FRAMES >= 1
assert _N_KILL_CONFIRMATIONS >= 1 


# load number templates for solo/ranked kills
_dict_kills_ranked = {}
_dict_kills_solo = {}

for i in range(10):
	_dict_kills_ranked[i] = cv2.imread("data_apex/digits/ranked/%02d.png" % i, 0)
	assert _dict_kills_ranked[i] is not None

for i in range(30):
	_dict_kills_solo[i] = cv2.imread("data_apex/digits/solo/%02d.png" % i, 0)
	assert _dict_kills_solo[i] is not None



def _get_seconds(): return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
def _timestamp():
	milliseconds = int(time.time()*1000.0) % 1000.0  
	return _get_seconds()*1000.0 + milliseconds



class KillsTrackerApex:

	def __init__(self):
		self.lastImg = None
		self.frameCounter = 0
		self.skull_icon = cv2.imread("data_apex/skull_icon.png")
		self.skull_icon_red = cv2.imread("data_apex/skull_icon_red.png")
		self.skull_icon_crown = cv2.imread("data_apex/skull_icon_crown.png")
		assert self.skull_icon is not None
		assert self.skull_icon_red is not None
		assert self.skull_icon_crown is not None
		
		# we keep track between consecutive frames of last kill number identified
		# and for how many frames
		self.last_kill_number = -1
		self.kill_number_confirmations = 0

		self.kills = -1
		self.lastImgRaw = None
		

	# Finds optimal threshold number for ranked kills in order to get best recognition on the image
	#
	# @TODO: we can improve this by keeping only numbers that are likely after the first pass
	#  	but this might produce errors in the long run, although is faster
	#
	def _find_optimal_threshold_for_ranked_kills(self, kills_number):
		h,w = kills_number.shape	
		dict_nr = _dict_kills_ranked
	
		ll = []
		n_pixels = h*w
		for threshold in [220, 210, 190, 170, 150, 130, 120, 90]:
			img = kills_number.copy()
			img[img<threshold] = 0 
			n_zero = n_pixels-cv2.countNonZero(img)
			p_zero = n_zero*1.0/n_pixels
			
			# if we have < 75% black pixels - threshold is not good
			if p_zero < 0.75: break
			
			for nr in [0,1,2,3,4,5,6,7,8,9]:		
				template = dict_nr[nr]
				v = self._check_img(img, template, False)
				if v is None: continue
				maxVal1, maxVal2 = v[:2]
				if maxVal1 >= 0.80 and maxVal2 >= 0.80:
					ll += [(nr, maxVal2, threshold)]
	
		ll.sort(key=lambda x:x[1], reverse=True)
		threshold = ll[0][2] if ll != [] else 150
		return threshold 


	# check if skull icon for kills is present on screen
	# returns kills number (if skull icon found)+ isRanked (boolean) or None  
	def check_for_kills_icon(self, img):
		for x1,y1,x2,y2,isRanked in [(1030,26,1085,55,False),(1088,57,1130,88,True)]:
			subimg = img[y1:y2,x1:x2]
			 
			for ii in [self.skull_icon, self.skull_icon_red, self.skull_icon_crown]:
				dy,dx = ii.shape[:2]
				result = cv2.matchTemplate(subimg, ii, cv2.TM_CCORR_NORMED)
				_, maxVal1, _, maxLoc1 = cv2.minMaxLoc(result)
				result = cv2.matchTemplate(subimg, ii, cv2.TM_CCOEFF_NORMED)
				_, maxVal2, _, maxLoc2 = cv2.minMaxLoc(result)
				
				ok = (maxVal1 >= 0.85 and maxVal2 >= 0.75) or (maxVal1 >= 0.75 and maxVal2 >= 0.80) 
				if not ok: ok = (maxVal1 >= 0.90 and maxVal2 >= 0.68) or (maxVal1 >= 0.70 and maxVal2 >= 0.85) 
				if ok:
					x,y = maxLoc2
					x += x1+18
					y += y1+3
					return img[y:y+15,x:x+20], isRanked
		return None 	


	# convert image to black and white grey
	def convert(self, img):
		assert img is not None
		img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		#img[img>=180] = 255
		#img[img<180] = 0
		#img = cv2.bitwise_not(img)
		return img


	# temporary function used by _find_kills 
	def _check_img(self, img, template, _debug=False):
		result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, maxLoc1 = cv2.minMaxLoc(result)
		if maxVal1 < 0.70: return None
		
		h,w = template.shape[:2]
		x,y = maxLoc1
		img2 = img[y:y+h, x:x+w]
	
		result = cv2.matchTemplate(img2, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, maxLoc2 = cv2.minMaxLoc(result)
	
		if _debug: print("%.2f %.2f (%d)" % (maxVal1, maxVal2, maxLoc1[0]), end="")
	
		if maxVal2 < 0.63: return None
		return (maxVal1, maxVal2, maxLoc1[0])
	


	# internal function
	# returns kills_ranked number identified
	# if no number identified: returns -1
	# else the highest probable kills_ranked number
	def _find_kills(self, kills_number, is_ranked=True, debug=False):
	
		#@TODO: find threshold for kills number
		threshold = self._find_optimal_threshold_for_ranked_kills(kills_number) if is_ranked else 170 
		kills_number[kills_number<threshold] = 0
	
		h,w = kills_number.shape	
		img = np.zeros((25,34), dtype=np.uint8)
		img[4:4+h, 5:5+w] = kills_number
	
		one_identified = False
		two_identified = False
		
		dict_nr = _dict_kills_ranked if is_ranked else _dict_kills_solo
	
		ll = []
		for nr in range(10 if is_ranked else 29):
			template = dict_nr[nr]
		
			# after numbers 0..9: sort the list and keep only top 2 best choices
			if nr == 10:
				for x in ll:
					if x[0] == 1 and x[1]>=0.75 and x[2]>=0.70: one_identified = True
					elif x[0] == 2 and x[1]>=0.75 and x[2]>=0.70: two_identified = True
				if len(ll) >= 2:
					ll.sort(key=lambda x:x[2], reverse=True)
					ll=ll[:2]
					ll.sort(key=lambda x:x[2], reverse=True)
		
			if nr >= 10 and nr < 20 and (not one_identified): continue	# if we didn't identify digit 1 there is no point in checking out numbers 10..19
			if nr >= 20 and nr < 30 and (not two_identified): continue	# if we didn't identify digit 2 there is no point in checking out numbers 20..29
			
			if debug: print(nr, "=> ", end = "")
			v = self._check_img(img if nr >= 10 or is_ranked else img[:,:14], template, debug)
			if debug: print()
			
			if v is None: continue
			if nr==1 and v[2] >= 10: continue	# sometimes it might mis-identify digit 1 somewhere in the middle of the image
			ll += [(nr, v[0], v[1])]
			
			# remove 0-9 from the list if a number between 10..29 is found plausible
			if nr >= 10 and nr < 30: ll = [v for v in ll if v[0] >= 10] 
		
		if len(ll) == 0: return -1
		if len(ll) == 1: return ll[0][0]
		
		# first sort ll by maxVal2 desc, keep top 2 elements
		ll.sort(key=lambda x:x[2], reverse=True)
		ll=ll[:2]
		
		# next sort by maxVal1 desc, keep top element
		ll.sort(key=lambda x:x[2], reverse=True)
		return ll[0][0]


	# returns kills number if it changed, -1 otherwise
	def check_if_kills_number_changed(self, img0):
	
		self.frameCounter += 1
		if (self.frameCounter % _SKIP_FRAMES) != 0: return -1
	
		v = self.check_for_kills_icon(img0)
		if v is None: return -1
		img, isRanked = v

		imgRaw = img.copy()
		img = self.convert(img)
		kills_number_changed = False

		nr = self._find_kills(img, isRanked, _DEBUG)
		
		kills_number_changed = (nr >= 0 and nr != self.kills)
		
		if kills_number_changed:
			kills_number_changed = False
			if nr != self.last_kill_number:
				self.kill_number_confirmations = 0
			else:
				self.kill_number_confirmations += 1
				if self.kill_number_confirmations >= _N_KILL_CONFIRMATIONS:  				 
					self.kills = nr
					kills_number_changed = True
			self.last_kill_number = nr
		 
			if _DEBUG:
				cv2.imwrite("kills_%d.png" % _timestamp(), imgRaw) 


		self.lastImg = img
		self.lastImgRaw = imgRaw
		return self.kills if kills_number_changed else -1				    	
				



	
	



if __name__ == "__main__":

	_DEBUG = False
	_SKIP_FRAMES = 1

	from utils import *
	
	kills_tracker = KillsTrackerApex() 		


	for folder, isRanked in [("data/kills_ranked_test/",True),("data/kills_solo_test/",False)]:
		print("[%s]" % ("Ranked" if isRanked else "Solo"))
		for root, dirs, files in os.walk(folder, topdown=False):
			for name in files:
				fname = os.path.join(root, name)
				if not (fname.endswith(".jpg") or fname.endswith(".png")): continue
				img = cv2.imread(fname) 
				assert img is not None
				
				kills_tracker.kills = -1
				nr = kills_tracker.check_if_kills_number_changed(img)
				print(fname, nr)
		
