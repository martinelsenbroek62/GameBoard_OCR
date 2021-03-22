import os, cv2
import numpy as np



_dmg_done1 = cv2.imread("data_apex/damage_done1.png")
_dmg_done1b = cv2.imread("data_apex/damage_done1b.png")
_dmg_done2 = cv2.imread("data_apex/damage_done2.png")
_dmg_done2b = cv2.imread("data_apex/damage_done2b.png")

assert _dmg_done1 is not None
assert _dmg_done1b is not None
assert _dmg_done2 is not None
assert _dmg_done2b is not None

_dmg_done1b = _dmg_done1b[:,:90]
_dmg_done2b = _dmg_done2b[:,:89]
	


# replaces the Squad # ... square text - filters out everything but the red text and changes it color to white
# this is for better text recognition
# does not return anything, replace is is place
def enhance_position(img):
	h,w = img.shape[:2]
	dx = w/1920.
	dy = h/1080.
	y0,y1,x0,x1 = int(7*dy),int(128*dy),int(1400*dx),int(1674*dx)

	img1 = img[y0:y1, x0:x1]
	red_low = np.array([0,0,200], np.uint8)
	red_high = np.array([60,110,255], np.uint8)
	lc = np.array(red_low, np.uint8) 
	uc = np.array(red_high, np.uint8)
	mask = cv2.inRange(img1, lc, uc)
	mask3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)  
	img[y0:y1, x0:x1] = mask3




def enhance_position_team(img):
	h,w = img.shape[:2]
	dx = w/1920.
	dy = h/1080.
	y0,y1,x0,x1 = int(70*dy),int(198*dy),int(1360*dx),int(1893*dx)
	img1 = img[y0:y1, x0:x1]
	yellow_low = np.array([0,140,180], np.uint8)
	yellow_high = np.array([100,255,255], np.uint8)
	lc = np.array(yellow_low, np.uint8) 
	uc = np.array(yellow_high, np.uint8)
	mask = cv2.inRange(img1, lc, uc)
	mask3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)  
	img[y0:y1, x0:x1] = mask3

	# whitening player names - disabled at the moment, not sure it is better ...
	if False:	
		white_low = np.array([120,120,120], np.uint8)
		white_high = np.array([255,255,255], np.uint8)
		lc = np.array(white_low, np.uint8) 
		uc = np.array(white_high, np.uint8)
	
		for x0,y0,x1,y1 in [(121,274,342,324),(723,274,938,324),(1320,274,1537,324)]:
			y0,y1,x0,x1 = int(y0*dy),int(y1*dy),int(x0*dx),int(x1*dx)
			img1 = img[y0:y1, x0:x1]
			mask = cv2.inRange(img1, lc, uc)
			mask3 = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)  
			img[y0:y1, x0:x1] = mask3






# detects the "Damage Done (" line and replaces paranthesis by blank space
# this is because sometimes (1 is detected as 0
# line is replaced in place
def replace_damage_done(img0):

	img = img0[0:394,0:679]

	# find which of the two templates matches best
	ll = []
	for template,idx in [(_dmg_done1,0), (_dmg_done2,1)]:
		result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, maxLoc1 = cv2.minMaxLoc(result)
		x,y = maxLoc1
		img2 = img[y:y+template.shape[0], x:x+template.shape[1]]
		result = cv2.matchTemplate(img2, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)
		
		if maxVal1 >= 0.70 and maxVal2 >= 0.70:
			ll += [(idx,maxVal1,maxVal2,x,y,template)]

	# if nothing identified - nothing to do
	if len(ll) == 0: return
	
	# else pick best match and replace image with paranthesis erased
	ll.sort(key=lambda x:x[1], reverse=True)
	idx,_,_,x,y,_ = ll[0]  
	
	template = _dmg_done1b if idx==0 else _dmg_done2b
	h,w = template.shape[:2]
	img0[y:y+h,x:x+w] = template



# Automatic brightness and contrast optimization with optional histogram clipping
def automatic_brightness_and_contrast(image, clip_hist_percent=1):
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	
	# Calculate grayscale histogram
	hist = cv2.calcHist([gray],[0],None,[256],[0,256])
	hist_size = len(hist)
	
	# Calculate cumulative distribution from the histogram
	accumulator = []
	accumulator.append(float(hist[0]))
	for index in range(1, hist_size):
		accumulator.append(accumulator[index -1] + float(hist[index]))
		
	# Locate points to clip
	maximum = accumulator[-1]
	clip_hist_percent *= (maximum/100.0)
	clip_hist_percent /= 2.0
	
	# Locate left cut
	minimum_gray = 0
	while accumulator[minimum_gray] < clip_hist_percent:
		minimum_gray += 1

	# Locate right cut
	maximum_gray = hist_size -1
	while accumulator[maximum_gray] >= (maximum - clip_hist_percent):
		maximum_gray -= 1

	# Calculate alpha and beta values
	alpha = 255 / (maximum_gray - minimum_gray)
	beta = -minimum_gray * alpha
	
	auto_result = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
	return auto_result 


if __name__ == "__main__":

	for root, dirs, files in os.walk(".", topdown=False):
		for name in files:
			fname = os.path.join(root, name)
			if not (fname.endswith(".jpg") or fname.endswith(".png")): continue
			print(name)
			img = cv2.imread(fname)
			img = automatic_brightness_and_contrast(img)
			cv2.imwrite(fname, img)
			 
			