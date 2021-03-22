scoreTranslationTable = {'Kills': 1/50, 'Damage Done': 4, 'winMultiplier': 1}
def translate(l):
	if l in ' +,-.':
		return ''
	if l in '1|l}{][':
		return '1';
	if l in 'z':
		return '2'
	if l in 'em':
		return '3'
	if l in 'ha':
		return '4'
	if l in 's':
		return '5'
	if l in 'bg':
		return '6'
	if l in 'tj':
		return '7'
	if l in 'x':
		return '8'
	if l in 'g':
		return '9'
	if l in 'o':
		return '0'
	return l

def parse(data):
	try:
		converting = []
		parsed_data = []
		data = data.splitlines()
		print(data)
		for stat in data:
			print('epic')
			try:
				parsed_stat = stat.split(' => ');
				if 'SquadRank' in parsed_stat[0]:
					print('squad rank epicly')
					parsed_stat = parsed_stat[0].split(' ');
					print(parsed_stat)
					parsed_stat[0] = 'SquadRank'
	
				converting += parsed_stat[1];
				endValue = ''
				for i in range(0,len(converting)):
					endValue += translate(converting[i])
				print(endValue)
				parsed_stat[1] = int(endValue)
				if "Kills" in parsed_stat[0]:
					parsed_stat[0] = 'Kills'
					parsed_stat[1] = parsed_stat[1] * scoreTranslationTable['Kills'];
				if "Damage Done" in parsed_stat[0]:
					parsed_stat[0] = 'Damage Done'
					parsed_stat[1] = parsed_stat[1] * scoreTranslationTable['Damage Done'];
				if "SquadRank" in parsed_stat[0]:
					parsed_stat[0] = 'SquadRank'
					parsed_stat[1] = int(parsed_stat[1])
					print('going through ifs')
					if parsed_stat[1] == 1:
						parsed_stat[1] = 100
					elif parsed_stat[1] < 5:
						parsed_stat[1] = 50
					elif parsed_stat[1] <= 10:
						parsed_stat[1] = 20
					else:
						parsed_stat[1] = 0
	
				converting = []
			except:
				converting = []
				parsed_stat[1] = 0
			parsed_data.append({parsed_stat[0]: parsed_stat[1]})
		return parsed_data;
	except:
		return [{'Kills': 0, "Damage": 0, "SquadRank": 0}]
