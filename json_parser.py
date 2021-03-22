def extract_team_info(ss):
	x_coord = [0.0600,0.3700,0.6900]
	
	y_kills = 0.3700
	y_damage = 0.4400
	y_survival = 0.5107
	y_revive = 0.5815
	y_respawn = 0.6520 

	name =  ["","",""]
	kills = ["","",""]
	damage = ["","",""]
	survival = ["","",""]
	revive = ["","",""]
	respawn = ["","",""]

	rank, n_kills = "??","??"
	y_eliminated = 0.1190

	dd = eval(ss)
	ll = []
	for block in dd['Blocks']:
		if block['BlockType'] != "WORD": continue
		ll += [block['Text']]

		txt = block['Text']
		x,y = block['Geometry']['BoundingBox']['Left'],block['Geometry']['BoundingBox']['Top']
		w,h = block['Geometry']['BoundingBox']['Width'],block['Geometry']['BoundingBox']['Height']
		
		if txt.startswith("ELIMINATED"): y_eliminated = y
		
		if _is_around_y(y,y_eliminated) and x >= 0.50:
			while txt != "" and not (txt[:1] in ["0","1","2","3","4","5","6","7","8","9"]):
				txt = txt[1:]
			while txt != "" and not (txt[-1:] in ["0","1","2","3","4","5","6","7","8","9"]):
				txt = txt[:-1]
			if txt != "":
				if x <= 0.85: rank = txt
				else: n_kills = txt 
		
		def _check(y, y0, list):
			if _is_around_y(y, y0):
				for i in range(3):
					if x >= x_coord[i]-0.0085 and x <= x_coord[i]+0.20:
						list[i] += " "+txt if list[i] != "" else txt

		_check(y, 0.2662, name)
		_check(y, y_kills, kills)
		_check(y, y_damage, damage)
		_check(y, y_survival, survival)
		_check(y, y_revive, revive)
		_check(y, y_respawn, respawn)
		
	for i in range(3):
		damage[i] = damage[i].split(" ")[0]	# remove name from damage
	
	stat = ["","",""]
	for i in range(3):
		stat[i] = "%s,%s,%s,%s,%s,%s" % (name[i], kills[i], damage[i], survival[i], revive[i], respawn[i])
	
	result = "\n".join(stat)
	result = "Squad Placed: %s Total Kills: %s\n%s" % (rank, n_kills, result)
	return result



# parses squad rank, returns 1-20 or "??" if cannot parse it
def _parse_squad_rank(str):
	while str != "" and not (str[:1] in ["0","1","2","3","4","5","6","7","8","9"]):
		str = str[1:]  	
	 
	for x in [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,1,2]:
		if str.startswith("%d"%x):
			return "%d" % x
	return "??"
	                    
#Top 0.12015412002801895 0.21582403779029846
#Time 0.11954347789287567 0.2533118724822998
#Kills 0.12076995521783829 0.29005149006843567
#Damage 0.12054388225078583 0.327394038438797
#Revive 0.12046191841363907 0.36444219946861267
#Respawn 0.1207270398736 0.40174853801727295

# Killed 0.32213813066482544 0.21556363999843597
# Kill 0.3218054473400116 0.2528636157512665
# Playing 0.32188159227371216 0.2897409498691559

# x: .1195 -> .2700 => delta 
# y: .2158, .2533, .2900, .3273, .3644, .4017


x_coord = [0.1195,0.3218] 
y_coord = [0.2158,0.2533,0.2900,0.3273,0.3644,0.4017]
 

def _is_around(x,y,x0,y0):
	threshold = 0.0085
	return abs(x-x0) < threshold and abs(y-y0) < threshold		


def _is_around_y(y,y0):
	threshold = 0.0085
	return abs(y-y0) < threshold		



dict = {}

# exp: 0.4375-0.05 0.5160 width: 0.0775

def extract_player_info(ss):
	squad_pos,kills = "",""
	
	
	dict = {}
	
	total_xp = ""

	dd = eval(ss)
	ll = []
	for block in dd['Blocks']:
		if block['BlockType'] != "WORD": continue
		ll += [block['Text']]
		
		txt = block['Text']
		x,y = block['Geometry']['BoundingBox']['Left'],block['Geometry']['BoundingBox']['Top']
		w,h = block['Geometry']['BoundingBox']['Width'],block['Geometry']['BoundingBox']['Height']
		
		#if txt.find("3,781") >= 0: print(txt, x, y, w)
		#if _is_around(x,y,0.2837, 0.2205): print(txt, x, y)
		
		#txt_list = "Top,Time,Kills,Damage,Revive,Respawn".split(",")
		#txt_list = "Killed,Kill,Playing".split(",")
		
		#for xx in txt_list:			
		#	if txt.find(xx) >= 0: 
		#		print(txt, x, y)
		
		if _is_around_y(y,.5160):
			if x >= .4375-0.0500 and x <= .4375+.0975:
				total_xp = txt
		
		for y0 in y_coord:
			if not _is_around_y(y,y0): continue
			for x0 in x_coord:
				key = (x0,y0)
				if x >= x0-0.0085 and x <= x0+.1505+.0085: 
					if not key in dict: dict[key] = ["",""]
					dict[key][0] += " " + txt
					
				if x >= x0+.1597-.0100 and x <= x0+.1900:
					if not key in dict: dict[key] = ["",""]
					dict[key][1] += " " + txt
					
	lst = [(_key[0],_key[1],dict[_key]) for _key in dict]
	lst.sort(key=lambda x: x[0]*1000+x[1])
	lst = [v for x,y,v in lst]
	
	str = " ".join(ll)
	ss = str.find("MATCH SUMMARY")	
	squad_rank = _parse_squad_rank(str[ss+14:ss+21]) if ss >= 0 else "??"
	
	result = "SquadRank: %s TotalXP: %s" % (squad_rank, total_xp)
	for x,y in lst: result += "\n%s => %s" % (x,y)
	return result



if __name__ == "__main__":

	import os, cv2
	import numpy as np
	
	dd = {}

	if True:
		for root, dirs, files in os.walk("data/single", topdown=False):
		#for root, dirs, files in os.walk("data/bad", topdown=False):
			for name in files:
				fname = os.path.join(root, name)
				if not fname.endswith(".txt"): continue
				ss = open(fname,"rt").read()
				#print(name+" --> ", end='')
				v = extract_player_info(ss)
				#print(v)
				
				key = name[:-4]
				dd[key] = v
				#print(fname, key)
				 
	print("dict_kv_output = ", repr(dd))

	if False:
		#fname = "data/single/1027_1585305661789.txt"
		fname = "data/single/3_1585339543132.txt"
		ss = open(fname,"rt").read() 
		v = extract_player_info(ss)
		#print(v)
 

	#fname = "data/single/1028_1585308471283.jpg"	 
	#img = cv2.imread(fname)
	#img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	#img_canny = cv2.Canny(img_gray, 50, 200)
	

