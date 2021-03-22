class NumberTracker:
	def __init__(self, mn, mx, delta_max, only_higher_values):
		self.list = []
		self.min = mn
		self.max = mx
		self.last_frame_id = -999
		self.current_value = -999
		self.delta_max = delta_max
		self.only_higher_values = only_higher_values
		

	def update(self, frame_id, nr):
		# reset kept numbers after 500 frames
		if frame_id - self.last_frame_id > 1500:
			self.current_value = -999
			self.list = []			

		# is the number plausible?
		if nr < self.min or nr > self.max: return
		
		# Disabled for now b/c we can have some situations where we have a lower value for nr_kills
		#if self.only_higher_values:
		#	if nr < self.current_value:
		#		return

		# safety check for kills - cannot jump up by 15+ 
		if self.only_higher_values and self.current_value >= 0:
			if nr > self.current_value+15:
				return

		# see if last digit 3 is actually 8
		if nr % 10 == 3:
			nr2 = (nr//10)*10+8
			if nr < self.current_value and nr < nr2 and nr2 <= self.current_value:
				nr = nr2 


		self.list = self.list[-50:] + [nr]

		# if number is only +/- 2 from current_value: instant replace
		if abs(nr-self.current_value) <= 2 and self.current_value > 0:
			if nr > self.current_value or (not self.only_higher_values):
				if len([x for x in self.list[-6:] if x == nr]) >= 5: 
					#if nr == 31: print("replace 1", nr, nr-self.current_value, nr > self.current_value, (not self.only_higher_values))
					self.current_value = nr
					return 

		# if a number appears too often: replace current number with it
		if len([x for x in self.list[-10:] if x == nr]) >= 5:
			if len([x for x in self.list[-5:] if x == nr]) >= 4:
				#if nr == 31: print("replace 2", self.list[-10:])
				self.current_value = nr
				return 


		if self.current_value >= 0:
			if abs(self.current_value-nr) > self.delta_max:
				return

		# if a number appears too often: replace current number with it
		if len([x for x in self.list[-10:] if x == nr]) >= 5: 
			if len([x for x in self.list[-4:] if x == nr]) >= 3:
				#if nr == 31: print("replace 3")
				self.current_value = nr
				return 
		

		
		# if we see the same number 3 times in a row then we assume it's a good value 
		self.last_frame_id = frame_id
		if len(self.list) >= 4 and self.list[-3]==nr and self.list[-2]==nr and self.list[-1]==nr:
			#if nr == 31: print("replace 4")
			self.current_value = nr
			return 





	def val(self):
		return self.current_value						


