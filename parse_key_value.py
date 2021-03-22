# given a summary parsed => extract key/value to a list of key/value pairs
def parse_key_value_to_list(txt):
	kv_list = []

	for s in txt.split("\n"):
		s0 = s
		
		if s.find("SquadRank:") >= 0 and s.find("TotalXP:") > 0:
			s = s.strip()
		
			xp = s.split("TotalXP:")[1].replace(",","").strip()
			squad_rank = s.split("TotalXP:")[0].split("SquadRank:")[1].strip()
			#print(s, squad_rank, xp)
			#print("[%s]" % s)
			if squad_rank.isdigit() and squad_rank != '': kv_list += [("SquadRank", squad_rank, s0)]   
			if xp.isdigit() and xp != '': kv_list += [("TotalXP", xp, s0)]
		else:	
			s = s.replace("] =>", ") =>")
			s = s.replace("(xl", "(x1")
			s = s.replace("(,", "(1")
			s = s.replace("(xD", "(x1")
			s = s.replace(" [", " (")
			if s.find("(") < 0: s = s.replace(" 0", " (1")
			s = s.replace("K1ll", "Kill")
			s = s.replace("Damge", "Damage")
			s = s.replace("Kil ", "Kill ")
			s = s.replace("Champian", "Champion")
			s = s.replace("Kilis", "Kills")
			s = s.replace("namane none n", "Damage Done")
			ll = s.split(" => ")
			if len(ll) != 2: continue
			k,v = ll
			k = k.strip()
			v = v.strip()
			if v.startswith("+"): v = v[1:]
			if k.find("(") > 0 and k.find(")") < 0:
				k += ")"
			if len(k) < 10: continue
			if v in ["","-","--","---"]: v = "0"
			kv_list += [(k,v, s0)]
		
	return kv_list
	

# given a summary parsed => extract key/value
# then add at the end under the label [RAW] the original text 
def parse_key_value(txt):
	kv_list = parse_key_value_to_list(txt)
	txt = ("\n".join(["%s=%s" % (k,v) for k,v,_ in kv_list])) + "\n\n[RAW]\n" + txt
	return txt
