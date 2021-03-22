import time, os, sys

# run worker in an infinte loop, just in the unlikely case the main script crashes 
while True:
	os.system("python3 stream_jobs.py")
	time.sleep(1)