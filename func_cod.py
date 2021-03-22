# CallOfDuty parser functions - everything is here except model which is in model_cod

from const import *
from model_cod import *
from convert_img import *
from number_tracker import *

import numpy as np
import cv2,os,sys,time,random
from PIL import ImageFont, ImageDraw, Image

font_text = ImageFont.truetype("data_cod/fonts/Poppins-Regular.ttf", 16)


def resize_img(img, dx, dy):
	if img.shape[0] == dy and img.shape[1] == dx: return img
	img_pil = Image.fromarray(img)
	img_pil = img_pil.resize((dx, dy), Image.ANTIALIAS)
	img = np.array(img_pil)
	return img


def show(img):
	h,w = img.shape[:2]
	cv2.imshow("img", cv2.resize(img, (w*10,h*10)))
	cv2.waitKey(0)


def auto_canny(image, sigma=0.33):
	v = np.median(image)
	lower = int(max(0, (1.0 - sigma) * v))
	upper = int(min(255, (1.0 + sigma) * v))
	return cv2.Canny(image, lower, upper)



img1 = cv2.imread("data_cod/img_people.png")
img2 = cv2.imread("data_cod/img_man.png")
img3 = cv2.imread("data_cod/img_skull.png")
img_rank = cv2.imread("data_cod/rank.png")
img_spectating = cv2.imread("data_cod/spectating.png")
img_lobby_waiting = cv2.imread("data_cod/lobby_waiting.png")
img_you_placed = cv2.imread("data_cod/you_placed.png")
img_you_placed_corner = cv2.imread("data_cod/you_placed_corner1.png")
img_deployment_begin = cv2.imread("data_cod/deployment_will_begin.png")

img_warzone = cv2.imread("data_cod/warzone.png")
img_victory = cv2.imread("data_cod/victory.png")

assert(img1 is not None)
assert(img2 is not None)
assert(img3 is not None)
assert(img_rank is not None)
assert(img_victory is not None)
assert(img_warzone is not None)
assert(img_you_placed is not None)
assert(img_spectating is not None)
assert(img_lobby_waiting is not None)
assert(img_deployment_begin is not None)
assert(img_you_placed_corner is not None)

img1_canny = auto_canny(img1)
img2_canny = auto_canny(img2)
img3_canny = auto_canny(img3)

img_warzone_canny = auto_canny(img_warzone)
img_victory_canny = auto_canny(img_victory)




def check_if_valid_symbols(img):
	for (x,y,ii) in [(46,3,img1),(96,4,img2),(145,4,img3)]:
		dy,dx = ii.shape[:2] 
		result = cv2.matchTemplate(img[y:y+dy,x:x+dx], ii, cv2.TM_CCORR_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.75: return False 	
	
		result = cv2.matchTemplate(img[y:y+dy,x:x+dx], ii, cv2.TM_CCOEFF_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.60: return False
		
	return True 	


def check_if_valid_symbols2(img):
	for (x,y,ii) in [(0,3,img1),(50,4,img2),(99,4,img3)]:
		dy,dx = ii.shape[:2] 
		result = cv2.matchTemplate(img[y:y+dy,x:x+dx], ii, cv2.TM_CCORR_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.75: return False 	
	
		result = cv2.matchTemplate(img[y:y+dy,x:x+dx], ii, cv2.TM_CCOEFF_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.60: return False
		
	return True 	



def check_if_warzone_victory(image):
	for template,x0,y0,x1,y1 in [(img_warzone_canny,198,546,671,639),(img_victory_canny,662,546,1078,639)]:
		subimage = auto_canny(image[y0:y1, x0:x1])
		result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.50: return False

		result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.40: return False
	return True




def check_img_template_canny(subimage, template):
	result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	if maxVal < 0.58: return False

	result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	return maxVal > 0.45


def get_img_template_canny_pos(subimage, template):
	result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
	_, maxVal, _, maxLoc = cv2.minMaxLoc(result)
	if maxVal < 0.55: return False,None

	result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
	_, maxVal, _, maxLoc = cv2.minMaxLoc(result)
	if maxVal < 0.38: return False,None
	
	return True, maxLoc 



def check_if_lobby_waiting(image):
	for template,x0,y0,x1,y1 in [(img_lobby_waiting,541,106,716,128),(img_deployment_begin,558,104,747,131)]:
		template = auto_canny(template)
		subimage = auto_canny(image[y0:y1, x0:x1])
		
		result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.30: continue

		result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal > 0.20: return True
	return False



def check_if_spectating(image):
	subimage = image[495:530, 571:743]
	result = cv2.matchTemplate(auto_canny(subimage), auto_canny(img_spectating), cv2.TM_CCORR_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	if maxVal < 0.30: return False

	subimage = image[495:530, 571:743]
	result = cv2.matchTemplate(auto_canny(subimage), auto_canny(img_spectating), cv2.TM_CCOEFF_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	return maxVal > 0.20


def check_if_you_placed(image):
	for template,x0,y0,x1,y1 in [(img_you_placed,593,98,692,122),(img_you_placed_corner,555,235,605,268)]:
		template = auto_canny(template)
		subimage = auto_canny(image[y0:y1, x0:x1])
		
		result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.40: return False

		result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal, _, _ = cv2.minMaxLoc(result)
		if maxVal < 0.30: return False
		
	return True


def check_rank(image):
	template = auto_canny(img_rank)
	subimage = auto_canny(image[20:90, 1024:1255])
		
	result = cv2.matchTemplate(subimage, template, cv2.TM_CCORR_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	if maxVal < 0.50: return False

	result = cv2.matchTemplate(subimage, template, cv2.TM_CCOEFF_NORMED)
	_, maxVal, _, _ = cv2.minMaxLoc(result)
	return maxVal > 0.40




# returns: accuracy 0..1, (x,y)
def find_best_pos(img, template):
	if img is None: return 0.0,(0,0)
	if img.shape[0] < template.shape[0]: return 0.0,(0,0)
	if img.shape[1] < template.shape[1]: return 0.0,(0,0)

	res = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	return max_val, max_loc 



# a first method to determine coords of the 3 elements
def compute_coords_method1(img):
	threshold = 0.50

	img_canny = auto_canny(cv2.addWeighted(img, 4, cv2.blur(img, (14, 14)), -4, 128))
	
	_, acc1, _, maxLoc = cv2.minMaxLoc(cv2.matchTemplate(img_canny[:,:60], img1_canny, cv2.TM_CCORR_NORMED))
	x1,y1 = maxLoc
	if acc1 < threshold: return None

	_, acc2, _, maxLoc = cv2.minMaxLoc(cv2.matchTemplate(img_canny[:,30:], img2_canny, cv2.TM_CCORR_NORMED))
	if acc2 < threshold: return None
	x2,y2 = maxLoc
	x2 += 30

	_, acc3, _, maxLoc  = cv2.minMaxLoc(cv2.matchTemplate(img_canny[:,30:], img3_canny, cv2.TM_CCORR_NORMED))
	if acc3 < threshold: return None
	x3,y3 = maxLoc
	x3 += 30

	if x1 >= x2 or x2 >= x3: return None
	
	return x1,x2,x3,y1,y2,y3
	
	


def compute_coords_method2(img):
	threshold = 0.50

	acc1,pos1 = find_best_pos(img[:,:85],img1)		# xcoord for img1 can be max x=85 
	#acc1a,pos1a = find_best_pos(img[:,:20,:],img1)		# xcoord for img1 can be max x=85
	#acc1b,pos1b = find_best_pos(img[:,40:60,:],img1)		# xcoord for img1 can be max x=85
	#acc1,pos1 = (acc1a,pos1a) if (acc1a > acc1b) else (acc1b,pos1b)

	x1,y1 = pos1
	if acc1 < threshold: return None

	acc2,pos2 = find_best_pos(img[:,40:75,:] if x1 < 40 else img[:,80:106,:],img2) 
	x2,y2 = pos2
	x2 += 40 if x1 < 40 else 80
	if acc2 < threshold: return None

	acc3,pos3 = find_best_pos(img[:,x2+10:,:],img3)
	if acc3 < threshold: return None
	x3,y3 = pos3
	x3 += x2+10	

	return x1,x2,x3,y1,y2,y3



X0=1450
DX=300
Y0=100
DY=30

X0 = int(X0/1.5)
Y0 = int(Y0/1.5)
DX = int(DX/1.5)
DY = int(DY/1.5)




def extract_subimage(img):
	h,w = img.shape[:2]
	if h != 720 or w != 1280:
		img = resize_img(img, 1280, 720)
	
	img_canny = auto_canny(img[20:95, 900:1400])
	loc = []
	for template in [img1_canny, img3_canny]:
		is_present, location = get_img_template_canny_pos(img_canny, template)
		if not is_present: return None
		loc += [location]
	
	X0,Y0 = loc[0]
	X0 = 900+X0-46 
	Y0 = 20+Y0-3
	
	img = img[Y0:Y0+DY,X0:X0+DX].copy()

	#!!! note: check out if this is really necessary or if it can be optimized!
	#!!! note2: rarely this function crashes
	try: automatic_brightness_and_contrast(img)
	except: pass

	return img





def recognize_nr(img):
	# skip first 4 pixels...
	img = img[:,4:]

	img = cv2.addWeighted(img, 4, cv2.blur(img, (14, 14)), -4, 128)
	if N_CHANNELS == 1:
		img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	img = img/255.0

	nr = 0
	n_digits = 0
	while True:
		ll = []
		y0 = 0
		w = img.shape[1]

		#list_xy = [(x0,y0) for x0 in [0,2,3] for y0 in [1]]
		list_xy = [(x0,y0) for x0 in [2,0,1,3] for y0 in [0]]
		
		for x0,y0 in list_xy:
			if x0+5 > img.shape[1]: continue
			subimg = img[y0:y0+15,x0:x0+5]

			if subimg.shape[1] != 5: continue
			if subimg.shape[0] != 15: continue
			
			pred, conf = model_predict(subimg)
			ll += [(x0,pred,conf*100 + (1.0-x0/100.0))]
			#if conf >= 0.98: break
			#if conf >= 0.98 or (x0 in [0,1] and conf >= 0.90 and pred in [8,9,6]): break
			#if conf >= 0.98 or (x0 in [0,1] and conf >= 0.90 and pred in [4,5,6,7,8,9]): break
			if conf >= 0.999 or (x0 in [0,1] and conf >= 0.90 and pred in [4,5,6,7,8,9]): break
			
		ll.sort(key=lambda x:x[2], reverse=True)
	
		# special case: 1st digit 5, 2nd digit 6, xpos for 5 >= 2, xpos for 6 <= 2
		# choose 6 in this case and change its confidence to 0.90
		if len(ll) >= 2 and ll[0][1]==5 and ll[1][1]==6:
			if ll[1][2] >= 0.68:
				if ll[0][0] >= 2 and ll[1][0] <= 1:
					ll[0],ll[1] = ll[1],ll[0]
					ll[0] = (ll[0][0],ll[0][1],90.0)
				
		# if 1st digit is zero: return zero!
		if nr == 0 and ll != [] and ll[0][1] == 0:
			return 0

		if ll == []: break

		if len(ll) >= 2 and ll[0][1] in [0,1] and ll[0][2] < 90.0:
			ll = ll[1:] 

		conf = ll[0][2]
		if conf < 80.0: break
		
		digit = ll[0][1]
		if digit in [0,1] and conf < 96:	# 0/1 are the digits most easily recognized so we want high confidence!
			break 
		
		n_digits += 1
		nr = nr*10+digit
		dx = ll[0][0] + (7 if digit != 1 else 8)
		img = img[:, dx:]
		if img.shape[1] < 5: break
				
	return nr if n_digits >= 1 else -1






def extract(img):
	if img is None: return None
	v = compute_coords_method1(img)
	if v is None: 
		try: v = compute_coords_method2(img)
		except: pass     
	if v is None: return v
	x1,x2,x3,y1,y2,y3 = v
	
	if x1 > 35:
		x1,x2,x3,y1,y2,y3 = 46, 96, 145, 3, 4, 4
	
	y_min = min([y1,y2,y3])
	y_max = max([y1,y2,y3]) + 16
	y_max = min([y_max, img.shape[0]])

	i1 = img[y_min:y_max,x1+15:x2]
	i2 = img[y_min:y_max,x2+7:x3] #!!i2 = img[y_min:y_max,x2+10:x3]
	i3 = img[y_min:y_max,x3+11:]

	for ii in [i1,i2,i3]:
		if ii.shape[0] < 16: return None
		if ii.shape[1] < 20: return None
		 
	ll = []
	for ii in [i1,i2,i3]:
		nr = recognize_nr(ii)
		
		# small adjustment - sometimes it adds several trailing 1/0 to the end of the number
		while nr > 200 and (nr % 10) in [0,1]:
			nr = nr//10
		while nr > 300 and (nr % 10) in [3,4]:
			nr = nr//10
		
		ll += [nr]

	#return (ll, x1) if len(ll) == 3 and ll[0] > 0 and ll[1] > 0 else ([],x1)
	return (ll, x1)



def majority(ll0):
	if ll0 == []: return None
	dict_freq = {}
	for x in ll0:
		try: dict_freq[x] += 1
		except: dict_freq[x] = 1
	ll = [(x,dict_freq[x]) for x in dict_freq]
	ll.sort(key=lambda x:x[1], reverse=True)
	maxval = ll[0][0]
	return maxval		



def remove_outliers(ll0):	
	maxval = majority(ll0)
	return [x for x in ll0 if x >= maxval-3 and x <= maxval+2]	 



# given a 600x400 stats big image (returned by StreamProcessorCOD):
#	parses stats and returns them
def extract_stats_cod(big_image):
	ll = [[],[],[]]	
	for i in range(60):
		x = (i%3)*200
		y = (i//3)*20
		img = big_image[y:y+20,x:x+200] 
		v = extract(img)
		if v is not None and v[0] != []:
			if v[0][0] > 0: ll[0] += [v[0][0]]
			if v[0][1] > 0: ll[1] += [v[0][1]]
			if v[0][2] >= 0: ll[2] += [v[0][2]]
			
	for i in range(3):
		if len(ll[i]) < 5: return [0,0,0]

	# for all entries in ll[0] > middle_stat+5 (we cannot have more people than teams):
	# divide it by 10
	middle_stat = majority(remove_outliers(ll[1])[:7])
	for i,v in enumerate(ll[0]):
		while v >= middle_stat + 5:
			v = v//10
		if v > 0: ll[0][i] = v

	# if first_stat >= 6 and second_stat >= 6: 
	# for all entries in ll[1] < first_stat: remove them (we cannot have more teams than people)	
	first_stat = majority(remove_outliers(ll[0]))
	if first_stat >= 5:
		ll[1] = [x for x in ll[1] if x >= first_stat]
	
	# remove all entries in ll[0] > first_stat
	ll[0] = [x for x in ll[0] if x <= first_stat] 

	# for number of kills X: check out numbers on the left/right (if any)
	# and if they are equal to X//10 : X = X//10
	for i,v in enumerate(ll[2]):
		if i > 0 and ll[2][i-1] == v//10: v = v//10
		if i+1 < len(ll[2]) and ll[2][i+1] == v//10: v = v//10
		ll[2][i] = v 	

	stat_list = []
	for i in range(3):
		ll[i] = remove_outliers(ll[i])
		stat_list += [majority(ll[i][:7])]		
	return stat_list 


import datetime
from aws_textract import *

def _get_seconds(): return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).total_seconds()
def _timestamp():
	milliseconds = int(time.time()*1000.0) % 1000.0  
	return _get_seconds()*1000.0 + milliseconds



# helper class for COD
# keeps a queue of last 100 identified stats
# when game ending is detected: process_frame returns a big_image of size 600x400 - last 60 found scores
# (if >= 40 last scores were found) - else it returns None 
class StreamProcessorCOD():
	
	def __init__(self, job_id):
		print("init")
		self.count = 0
		self.job_id = job_id
		self.image_queue = []
		self.last_msg_time = time.time() 
		self.last_screenshot_time = time.time()
		self.last_time_we_prepared_big_image = time.time() 
		self.reset_trackers() 


	def reset_trackers(self):
		self.tracker1 = NumberTracker(1,150,5,False)
		self.tracker2 = NumberTracker(2,210,5,False)
		self.tracker3 = NumberTracker(0,50,3,True)
		

	def _upload_image(self, image, msg):
		ts = _timestamp()
		fname_tmp = "tmp_%s_%d.jpg" % (self.job_id, ts)
		fname_s3 = "%s_%d.jpg" % (self.job_id, ts)
		cv2.imwrite(fname_tmp, image)
		
		if s3_upload_file(fname_tmp, fname_s3):
			print("%s: %s" % (msg, fname_s3))
		else:
			print("cannot upload to s3")


	def process_frame(self, image):

		# take random screenshot each 15 seconds
		#if time.time()-self.last_screenshot_time > 15.0:
		#	self.last_screenshot_time = time.time()
		#	self._upload_image(image, "uploaded random screenshot as")
			
		if check_if_spectating(image):
			#print("Spectating, ignoring team info") 
			return None
		
		if check_if_lobby_waiting(image): 
			#print("lobby waiting detected") 
			self.image_queue = []
			self.reset_trackers() 
			return None
		
		if check_if_warzone_victory(image) or check_if_you_placed(image) or (check_rank(image) and len(self.image_queue) >= 10):
			if len(self.image_queue) < 25:
				if time.time()-self.last_msg_time >= 25.0 and time.time() - self.last_time_we_prepared_big_image >= 60*4 :
					print("You placed ... detected, not enough stats images - %d, need at least 40" % len(self.image_queue))
					self.last_msg_time = time.time()
					self._upload_image(image, "uploaded as")

				self.image_queue = []
				self.reset_trackers() 
				return None
		
			print("preparing big_image ...")
			self.last_time_we_prepared_big_image = time.time()
			
			big_image = np.zeros(shape = (20*20, 200*3,3), dtype=np.uint8)
			ll = self.image_queue[-60:]
			ll.reverse()
			for i,img in enumerate(ll):
				x = (i%3)*200
				y = (i//3)*20
				
				try:
					big_image[y:y+20,x:x+200] = img
				except:
					print("i: %d x: %d y: %d" % (i,x,y))
					print("img shape:", img.shape)
					print("big image shape:", big_image.shape)
					big_image[y:y+20,x:x+200] = img

			n1 = max(0,self.tracker1.val())
			n2 = max(0,self.tracker2.val())
			n3 = max(0,self.tracker3.val())
			print(">>> COD stats: %d %d %d" % (n1,n2,n3))

			self.image_queue = []
			self.reset_trackers() 
			return big_image,n1,n2,n3

		img = extract_subimage(image)
		if img is None: 
			return None
		
		if not (check_if_valid_symbols(img) or check_if_valid_symbols2(img)):
			return None
		
		# update trackers
		self.count += 1
		v = extract(img)
		if v is not None and v[0] != []:
			self.tracker1.last_frame_id = self.count
			self.tracker2.last_frame_id = self.count
			self.tracker3.last_frame_id = self.count
			n1,n2,n3 = v[0]
			
			# 2nd number must always be greater or equal to 1st number
			if n1 > 0:
				if n1 <= self.tracker2.val() or self.tracker2.val() < 0: 
					self.tracker1.update(self.count, n1)
			if n2 > 0:
				if n2 >= self.tracker1.val() or self.tracker1.val() < 0: 
					self.tracker2.update(self.count, n2)
			self.tracker3.update(self.count, n3)

		# sometimes we get images with lower size
		# we'll avoid those for now, check why we get those later!
		if img.shape[0] != 20 or img.shape[1] != 200: 	
			return None
		
		#img_canny = auto_canny(img)
		#for template in [img1_canny, img2_canny, img3_canny]:
		#	if not check_img_template_canny(img_canny, template):
		#		return None
		
		self.image_queue += [img]
		self.image_queue = self.image_queue[-100:]

		return None
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		