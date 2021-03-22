import os
import cv2
import numpy as np


apex_legend_folder = "data_apex/legends/"
names = ["Bloodhound","Gibraltar","Lifeline","Pathfinder","Wraith","Bangalore","Caustic","Mirage","Octane","Wattson","Crypto","Revenant","Loba"]
dict_apex_legend = {}
for name in names:
	img = cv2.imread(apex_legend_folder+name+".png")
	assert img is not None
	dict_apex_legend[name] = img


inventory = cv2.imread("data_apex/inventory.png") 
squad = cv2.imread("data_apex/squad.png") 
legend = cv2.imread("data_apex/legend.png") 
assert inventory is not None
assert squad is not None
assert legend is not None


globe = cv2.imread("data_apex/globe.png") 
settings = cv2.imread("data_apex/settings.png") 
assert globe is not None
assert settings is not None

map1 = cv2.imread("map.png")
map2 = cv2.imread("map2.png")
map3 = cv2.imread("map3.png")
spectate1 = cv2.imread("spectate1.png")
spectate2 = cv2.imread("spectate2.png")
spectate3 = cv2.imread("spectate3.png")
squads_left = cv2.imread("squads_left.png")
deathbox_close = cv2.imread("deathbox_close.png")

assert map1 is not None
assert map2 is not None
assert map3 is not None
assert spectate1 is not None
assert spectate2 is not None
assert spectate3 is not None
assert squads_left is not None
assert deathbox_close is not None


corner = cv2.imread("corner.png")
corner2 = cv2.imread("corner2.png")
summary = cv2.imread("summary.png")
template = cv2.imread("template.png") 
playing_w_friends = cv2.imread("playing_w_friends.png") 

corner3 = cv2.imread("corner3.png")
corner3_gray = cv2.cvtColor(corner3, cv2.COLOR_BGR2GRAY)
corner3_canny = cv2.Canny(corner3_gray, 50, 200)

continue_template  = cv2.imread("continue.png")  
continue_gray = cv2.cvtColor(continue_template, cv2.COLOR_BGR2GRAY)
continue_canny = cv2.Canny(continue_gray, 50, 200)


white_low = np.array([170,170,170], np.uint8)
white_high = np.array([255,255,255], np.uint8)

gray_low = np.array([40,40,40], np.uint8)
gray_high = np.array([99,99,99], np.uint8)

lightgreen1_low = np.array([220,220,180], np.uint8)
lightgreen1_high = np.array([255,255,215], np.uint8)

lightgreen2_low = np.array([170,170,130], np.uint8)
lightgreen2_high = np.array([205,205,145], np.uint8)

red_low = np.array([8,15,219], np.uint8)
red_high = np.array([48,90,255], np.uint8)





# for lobby detection we must match both the globe icon and the settings icon with high enough accuracy
def recognize_lobby(img0):
	for template,x1,x2 in [(globe,1042,1149),(settings,629,1274)]:
		img = img0[629:700, x1:x2]

		result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, _ = cv2.minMaxLoc(result)
		if maxVal1 < 0.85: return False

		result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)
		if maxVal2 <= 0.70: return False

	return True



# returns true if inventory screen is detected (one of inventory/squad/legend icons is in the right place)
def recognize_inventory_screen(img0):
	for template,x1,x2 in [(inventory,482,615),(squad,618,736),(legend,744,893)]:
		img = img0[6:55, x1:x2]
		
		result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, _ = cv2.minMaxLoc(result)
		if maxVal1 < 0.85: continue

		result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)
		if maxVal2 >= 0.80: return True
		
	return False





# returns apex legend name if recognized or "Unknown"
def recognize_apex_legend_name(img):
	x1,y1,x2,y2 = 67,637,100,684
	img = img[y1-20:y2+20,x1-20:x2+20]
	
	ll = []
	for name in dict_apex_legend:
		template = dict_apex_legend[name]

		result = cv2.matchTemplate(img, template, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, _ = cv2.minMaxLoc(result)
		if maxVal1 < 0.85: continue

		result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)
		if maxVal2 < 0.80: continue

		ll += [(name, maxVal1, maxVal2)]
		
	if ll == []: return "Unknown"
	ll.sort(key=lambda x:x[2], reverse=True)
	return ll[0][0]


# check if spectating - definitely one way to determine player is dead or match is over
def check_if_spectating(img):
	x1,y1,x2,y2 = 420,6,605,68
	for ii in [spectate1, spectate2]:
		dy,dx = ii.shape[:2] 
		result = cv2.matchTemplate(img[y1:y2,x1:x2].copy(), ii, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, _ = cv2.minMaxLoc(result)
		result = cv2.matchTemplate(img[y1:y2,x1:x2].copy(), ii, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)
		if maxVal1 >= 0.78 and maxVal2 >= 0.60: return True 	
		if maxVal1 >= 0.70 and maxVal2 >= 0.70: return True 	
			
	return False 	


def check_map_icon(img):
	x1,y1,x2,y2 = 24,10,58,50
	img = img[y1:y2,x1:x2].copy()
	
	for map in [map1, map2, map3]:
		result = cv2.matchTemplate(img, map, cv2.TM_CCORR_NORMED)
		_, maxVal1, _, _ = cv2.minMaxLoc(result)
		result = cv2.matchTemplate(img, map, cv2.TM_CCOEFF_NORMED)
		_, maxVal2, _, _ = cv2.minMaxLoc(result)

		if maxVal1 >= 0.95 and maxVal2 >= 0.90: return True 	
		if maxVal1 >= 0.90 and maxVal2 >= 0.95: return True
		 	
	return False 	


def check_squads_left(img):
	x1,y1,x2,y2 = 1105,15,1234,70
	img = img[y1:y2,x1:x2].copy() 
	result = cv2.matchTemplate(img, squads_left, cv2.TM_CCORR_NORMED)
	_, maxVal1, _, _ = cv2.minMaxLoc(result)
	result = cv2.matchTemplate(img, squads_left, cv2.TM_CCOEFF_NORMED)
	_, maxVal2, _, _ = cv2.minMaxLoc(result)

	if maxVal1 >= 0.78 and maxVal2 >= 0.60: return True 	
	if maxVal1 >= 0.70 and maxVal2 >= 0.70: return True 	
	return False 	




def check_deathbox_close(img):
	x1,y1,x2,y2 = 367,636,446,669
	img = img[y1:y2,x1:x2].copy() 
	result = cv2.matchTemplate(img, deathbox_close, cv2.TM_CCORR_NORMED)
	_, maxVal1, _, _ = cv2.minMaxLoc(result)
	result = cv2.matchTemplate(img, deathbox_close, cv2.TM_CCOEFF_NORMED)
	_, maxVal2, _, _ = cv2.minMaxLoc(result)

	if maxVal1 >= 0.85 and maxVal2 >= 0.80: return True 	
	if maxVal1 >= 0.80 and maxVal2 >= 0.85: return True 	
	return False 	





# input: 1920x1080 rgb image
# output: True if it should be a good candidate, False otherwise
def check_if_it_is_good_image(img):
	template = img[796:870,1192:1222]
	gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
	n_over_150 = cv2.countNonZero(cv2.inRange(gray, 150, 255))
	if n_over_150 < 400: return False
	n_over_200 = cv2.countNonZero(cv2.inRange(gray, 200, 255))
	return n_over_200 >= 150


def count_colors(img, lower_color, upper_color):
	lc = np.array(lower_color, np.uint8) 
	uc = np.array(upper_color, np.uint8)
	mask = cv2.inRange(img, lc, uc)
	return cv2.countNonZero(mask)


# For an image to be a good candidate:
#	1) we must recognize the team score subimages at the right places
#	2) team stats must not be faded out so character recognition will work well 
def is_good_candidate_single_player(img):
	# x transform: from 0.1920 to 0..w
	# y transform: from 0,1080 to 0..h
	# img1 = img[36:84, 1078:1197]	# 119x48
	h,w = img.shape[:2]
	dx = w/1920.
	dy = h/1080.

	# template matching for "Square placed" box 
	#img1 = img[1:44, 1400:1700]	# 300x43
	y0,y1,x0,x1 = int(1*dy),int(44*dy),int(1400*dx),int(1700*dx)
	img1 = img[y0:y1, x0:x1]	
	img1 = cv2.resize(img1, (300,43))
	result = cv2.matchTemplate(img1, template, cv2.TM_CCORR_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
	#print(maxVal)
	#cv2.imwrite("tmp1.png", img1)
	if maxVal < 0.75: return False

	tH,tW = template.shape[:2]
	startX, startY = int(maxLoc[0]), int(maxLoc[1])
	endX, endY = int(maxLoc[0] + tW), int(maxLoc[1]+tH)

	# template matching for "Playing with friends" text 
	#img2 = img[315:340,620:787] # 167x25         
	y0,y1,x0,x1 = int(305*dy),int(370*dy),int(620*dx),int(787*dx)
	img1 = img[y0:y1, x0:x1]	
	img1 = cv2.resize(img1, (167,65))
	result = cv2.matchTemplate(img1, playing_w_friends, cv2.TM_CCORR_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
	if maxVal < 0.75: return False

   	# template matching for corner3.png image text 
	# because corner detection is difficult 
	# we convert corner/image to gray contour (canny)
	# and compare those
	#y0,y1,x0,x1 = int(846*dy),int(947*dy),int(1145*dx),int(1273*dx)
	y0,y1,x0,x1 = int(826*dy),int(947*dy),int(1145*dx),int(1273*dx)
	img1 = img[y0:y1, x0:x1]	
	img1 = cv2.resize(img1, (1273-1145,947-826))
	img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
	img1_canny = cv2.Canny(img1_gray, 50, 200)
	result = cv2.matchTemplate(img1_canny, corner3_canny, cv2.TM_CCORR_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
	if maxVal < 0.60: return False	# used to be 0.90 but I had to relax it for some low res videos

	# template matching for "continue" button 
	y0,y1,x0,x1 = int(933*dy),int(1046*dy),int(900*dx),int(1172*dx)
	img1 = img[y0:y1, x0:x1]	
	img1 = cv2.resize(img1, (272,113))
	img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
	img1_canny = cv2.Canny(img1_gray, 50, 200)
	result = cv2.matchTemplate(img1_canny, continue_canny, cv2.TM_CCORR_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
	#print(maxVal)
	#cv2.imwrite("tmp1.png", continue_canny)
	#cv2.imwrite("tmp2.png", img1_canny)
	return maxVal >= 0.45	# used to be 0.90 but I had to relax it for some low res videos


		


# for good candidata of team summary screen:
#	1) must have template matching with the top red Summary text
#	2) at least one of the three zones where player name is written 
#		must contain at least 500 white pixels	
def is_good_candidate_team_summary(img):
	# x transform: from 0.1920 to 0..w
	# y transform: from 0,1080 to 0..h
	# img1 = img[36:84, 1078:1197]	# 119x48
	h,w = img.shape[:2]
	dx = w/1920.
	dy = h/1080.
	y0,y1,x0,x1 = int(10*dy),int(100*dy),int(1068*dx),int(1207*dx)
	img1 = img[y0:y1, x0:x1]
	
	# resize summary and match it instead of the other way around
	summary_resized = cv2.resize(summary, (int(119*dx),int(48*dy)))	
	result = cv2.matchTemplate(img1, summary_resized, cv2.TM_CCOEFF_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
	if maxVal < 0.65: return False
	
	# for now we are interested in identifying the last team summary screen shown
	# even if it was not summary
	return True


def is_best_team_summary(img):
	# x transform: from 0.1920 to 0..w
	# y transform: from 0,1080 to 0..h
	# img1 = img[36:84, 1078:1197]	# 119x48
	h,w = img.shape[:2]
	dx = w/1920.
	dy = h/1080.
	y0,y1,x0,x1 = int(10*dy),int(100*dy),int(1068*dx),int(1207*dx)
	img1 = img[y0:y1, x0:x1]
	
	# resize summary and match it instead of the other way around
	summary_resized = cv2.resize(summary, (int(119*dx),int(48*dy)))	
	result = cv2.matchTemplate(img1, summary_resized, cv2.TM_CCOEFF_NORMED)
	minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)


	# the identified template must contain >80% of pixels red
	# disabled for now because we are looking for both red and gray summary
	tH,tW = summary_resized.shape[:2]
	startX, startY = int(maxLoc[0]), int(maxLoc[1])
	endX, endY = int(maxLoc[0] + tW), int(maxLoc[1]+tH)
	img1 = img1[startY:endY, startX:endX]
	n_red = count_colors(img1, red_low, red_high)
	if n_red < 0.10*tH*tW or n_red < 50: 
		return False
	
	# check for the white upper left corner for all 3 players
	# must be found for at least one of them
	if True:
		corner2_resized = cv2.resize(corner2, (int(112*dx), int(38*dy)))
		corner_found = False
		for _x0 in [98,685,1286]:
			y0,y1,x0,x1 = int(238*dy),int(292*dy),int(_x0*dx),int((_x0+160)*dx)
			img1 = img[y0:y1, x0:x1]
			result = cv2.matchTemplate(img1, corner2_resized, cv2.TM_CCOEFF_NORMED)
			minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(result)
			if maxVal > .80:
				corner_found = True
				break
		if not corner_found: return False
		
	if True:
		y0,y1 = int(292*dy),int(314*dy)
		for x in [132,730,1333]:
			x0,x1 = int(x*dx),int((x+172)*dx)
			subimg = img[y0:y1, x0:x1]	# 172x22
			subimg = cv2.resize(subimg, (172,22))
			n_white = count_colors(subimg, white_low, white_high)
			if n_white > 300 and n_white < 2000:
				return True

	return False

	

if __name__ == "__main__":
	if False:
		for root, dirs, files in os.walk("data/team", topdown=False):
			for name in files:
				fname = os.path.join(root, name)
				image = cv2.imread(fname)
				if image is None: continue
				#if is_good_candidate(image):
				if is_good_candidate_team_summary(image):
					print(fname, "[OK]")
				else: 
					print(fname, "[Fail]")
					 
	if False:
		for root, dirs, files in os.walk("data/single", topdown=False):
			for name in files:
				fname = os.path.join(root, name)
				image = cv2.imread(fname)
				if image is None: continue
				if is_good_candidate_single_player(image):
					print(fname, "[OK]")
				else: 
					print(fname, "[Fail]")
					 

	if False:
		for root, dirs, files in os.walk("data/selected/staycation", topdown=False):
			for name in files:
				fname = os.path.join(root, name)
				image = cv2.imread(fname)
				if image is None: continue
				#if is_good_candidate(image):
				if is_good_candidate_team_summary(image) or is_good_candidate_single_player(image):
					print(fname, "[OK]")
				else:       	
					print(fname, "[Fail]")
				#break


	#img = cv2.imread("data/frame139390.png")
	#img = cv2.resize(img, (633,356))
	#print(is_good_candidate_team_summary(img))
	
	#img = cv2.imread("test_frames3/good.png")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("test_frames3/bad.jpg")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("test_frames3/frame_001321.jpg")
	#img = cv2.imread("test_frames3/frame_006484.jpg")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("data/single/0/1.PNG")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("frames/frame005290.png")
	
	#img = cv2.imread("data/team/0/team 1.png")
	#img = cv2.imread("data/capture/frame_005310.jpg")
	#print(is_good_candidate_team_summary(img))

	#img = cv2.imread("test4/frame007972.png")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("test4/frame008010.png")
	#print(is_good_candidate_single_player(img))

	#img = cv2.imread("test4/frame016649.png")
	#print(is_good_candidate_single_player(img))
	
	img = cv2.imread("test4/frame061053.png")
	#img = cv2.imread("data/single/1/3.png")
	print(is_good_candidate_single_player(img))
	
	if False:
		img = cv2.imread("test_frames3/frame060420.png")
		print(is_good_candidate_team_summary(img))
		
		img1 = cv2.imread("test_frames3/frame068100.png")
		img2 = cv2.imread("test_frames3/frame075900.png")
		img3 = cv2.imread("test_frames3/frame068080.png")
		img4 = cv2.imread("test_frames3/frame006350.png")
		img5 = cv2.imread("test_frames3/frame075880.png")
		
		for img in [img1,img2,img3,img4,img5]:
			img = cv2.resize(img, (633,356))
			print(is_good_candidate_single_player(img))
	
