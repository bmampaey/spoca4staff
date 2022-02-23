#!/usr/bin/env python
import os, sys
from collections import OrderedDict
import pickle
import subprocess
import logging
import smtplib
from email.mime.text import MIMEText
import argparse
import glob
import time
from datetime import datetime, timedelta
import pyfits
import numpy
import test_quality
from multiprocessing import Pool

# Directory where the prepped AIA files are located
aia_file_pattern = "/data/SDO/public/AIA_quicklook/{wavelength:04d}/{date.year:04d}/{date.month:02d}/{date.day:02d}/H{date.hour:02d}00/AIA.{date.year:04d}{date.month:02d}{date.day:02d}_{date.hour:02d}*.{wavelength:04d}.*.fits"

# The date of the first data to process
start_date = datetime(2017,7,14,0,0,0)

# Wavelengths
wavelengths = [94, 131, 171, 193, 211, 304, 335, 1600, 1700, 4500]

# Directory to output the stats results
stats_directory = "/data/STAFF/AIA_quicklook/images_stats"

# The cadence of the desired results
run_cadence = timedelta(hours = 6)

# The time that must be waited before processing data
run_delay = timedelta(days = 1)

# The maximal number of errors before someone must be emailed
max_number_errors = 5

# The emails of the people to warn in case of too many errors
#emails = ["cis.verbeeck@oma.be", "benjamin.mampaey@oma.be"]
emails = ["benjamin.mampaey@oma.be"]

# The smtp server to send the emails
smtp_server = 'smtp.oma.be'

def setup_logging(filename = None, quiet = False, verbose = False, debug = False):
	global logging
	if debug:
		logging.basicConfig(level = logging.DEBUG, format='%(levelname)-8s: %(message)s')
	elif verbose:
		logging.basicConfig(level = logging.INFO, format='%(levelname)-8s: %(message)s')
	else:
		logging.basicConfig(level = logging.CRITICAL, format='%(levelname)-8s: %(message)s')
	
	if quiet:
		logging.root.handlers[0].setLevel(logging.CRITICAL + 10)
	elif verbose:
		logging.root.handlers[0].setLevel(logging.INFO)
	else:
		logging.root.handlers[0].setLevel(logging.CRITICAL)
	
	if filename:
		import logging.handlers
		fh = logging.FileHandler(filename, delay=True)
		fh.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(funcName)-12s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
		if debug:
			fh.setLevel(logging.DEBUG)
		else:
			fh.setLevel(logging.INFO)
		
		logging.root.addHandler(fh)

def send_email(sender, adresses, subject, messages = []):
	
	mail_body = "\n".join(messages)
	msg = MIMEText(mail_body)
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = ';'.join(adresses)
	log.debug("Sending email: %s", msg.as_string())
	try:
		s = smtplib.SMTP(smtp_server)
		s.sendmail(sender, adresses, msg.as_string())
		s.quit()
	except Exception, why:
		log.critical("Could not send mail %s to smtp server %s: %s", msg.as_string(), smtp_server, str(why))

def quality_ok(filepath):
	header = pyfits.open(filepath)[0].header
	if 'QUALITY' in header:
		return header['QUALITY'] & test_quality.nok_bits == 0
	else:
		log.warning("Missing quality keyword for file %s", filepath)
		return False

def get_stats(filepath, radius_ratio = 1):
	
	try:
		
		stats = dict()
		
		hdu = pyfits.open(filepath)[0]
		
		# We need to divide by the expoure time
		exptime = float(hdu.header['EXPTIME'])
		solar_radius = hdu.header['RSUN_OBS'] / hdu.header['CDELT1']
		center_x = hdu.header['CRPIX1'] - 1
		center_y = hdu.header['CRPIX2'] - 1
		stats["DATE_OBS"] = hdu.header['T_OBS']
		stats["WAVELENGTH"] = hdu.header['WAVELNTH']
		
		# Remove the nan from the values
		all_pixels = numpy.ma.masked_invalid(hdu.data).compressed()
		
		# Compute stats about all pixels of the image
		stats['DATAMIN'] = "%.3f" % (numpy.min(all_pixels) / exptime)
		stats['DATAMAX'] = "%.3f" % (numpy.max(all_pixels) / exptime)
		stats['DATAMEAN'] = "%.3f" % (numpy.mean(all_pixels) / exptime)
		stats['DATARMS'] = "%.3f" % (numpy.std(all_pixels) / exptime)
		stats['DATATOTL'] = "%.3f" % (numpy.sum(all_pixels) / exptime)
		
		# compute all percentiles at once
		keywords = ['DATAP01', 'DATAP10', 'DATAP25', 'DATAMEDN', 'DATAP75', 'DATAP90', 'DATAP95', 'DATAP98', 'DATAP99']
		percentiles = numpy.percentile(all_pixels, [1,10,25,50,75,90,95,98,99], overwrite_input = True)
		for keyword, percentile in zip(keywords, percentiles):
			stats[keyword] = "%.3f" % (percentile / exptime)
		
		# Compute stats about all pixels of the solar disk
		if radius_ratio > 0:
			# We make the list of pixels on the solar disk
			x, y = numpy.mgrid[hdu.data.shape[0] - center_x : -center_x : -1,-center_y : hdu.data.shape[1] - center_y : 1]
			disk_pixels = numpy.ma.masked_invalid(numpy.ma.masked_array(hdu.data, mask = numpy.ma.masked_less_equal(x*x+y*y, solar_radius * solar_radius).mask)).compressed()
		
			stats['DISKMIN'] = "%.3f" % (numpy.min(disk_pixels) / exptime)
			stats['DISKMAX'] = "%.3f" % (numpy.max(disk_pixels) / exptime)
			stats['DISKMEAN'] = "%.3f" % (numpy.mean(disk_pixels) / exptime)
			stats['DISKRMS'] = "%.3f" % (numpy.std(disk_pixels) / exptime)
			stats['DISKTOTL'] = "%.3f" % (numpy.sum(disk_pixels) / exptime)
	
			# compute all percentiles at once
			keywords = ['DISKP01', 'DISKP10', 'DISKP25', 'DISKMEDN', 'DISKP75', 'DISKP90', 'DISKP95', 'DISKP98', 'DISKP99']
			percentiles = numpy.percentile(disk_pixels, [1,10,25,50,75,90,95,98,99], overwrite_input = True)
			for keyword, percentile in zip(keywords, percentiles):
				stats[keyword] = "%.3f" % (percentile / exptime)
		
		return stats
		
	except Exception, why:
		logging.error("Error computing stats for file %s: %s", filepath, why)
		return None

# Start point of the script
if __name__ == "__main__":
	
	script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
	
	# Default path for the log file
	log_filename = os.path.join('.', script_name+'.log')
	
	# Sender email address of the script
	sender = "%s@oma.be" % script_name
	
	# Default path for the status file
	status_filename = os.path.join('.', script_name+'_status.pickle')
	
	# Get the arguments
	parser = argparse.ArgumentParser(description='Run spoca on many fits files.')
	parser.add_argument('--debug', '-d', default=False, action='store_true', help='set the logging level to debug for the log file')
	parser.add_argument('--verbose', '-v', default=False, action='store_true', help='set the logging level to verbose at the screen')
	parser.add_argument('--log_filename', '-l', default=log_filename, help='set the file where to log')
	parser.add_argument('--status_filename', '-s', default=status_filename, help='set the file where to save the status')
	
	args = parser.parse_args()
	
	# Setup the logging
	setup_logging(filename = args.log_filename, quiet = False, verbose = args.verbose, debug = args.debug)
	
	# Create a logger
	log = logging.getLogger(script_name)
	
	# Set the status filename
	if args.status_filename:
		status_filename = args.status_filename
	
	# Restore the previous status if any 
	status = dict()
	try: 
		pickle_file = open(status_filename, 'rb')
	except IOError, why:
		log.info("Could not open status file %s for restoring status: %s", status_filename, str(why))
	else:
		log.info("Restoring previous status from status file %s", status_filename)
		try:
			status = pickle.load(pickle_file)
			pickle_file.close()
			log.info("Status restored: %s", status)
		except Exception, why:
			log.critical("Could not restore status from file %s: %s", status_filename, str(why))
			sys.exit(2)
	
	# Parse the status
	if status:
		try:
			start_date = status['start_date']
		except ValueError, why:
			log.warning("Could not restore start_date from status, skipping")
	
	
	# Counter for the number of failure
	number_errors = 0
	
	# We run the processes in parralel
	pool = Pool(processes = 2, maxtasksperchild = 10)
	
	# Start the big loop
	while(True):
		
		# We check if the files we need are already available or if we need to wait
		if datetime.now() <= start_date + run_delay :
			time_to_wait = run_delay - (datetime.now() - start_date)
			log.info("Waiting %s hours for data to be available", time_to_wait)
			seconds_to_wait = (time_to_wait.microseconds + (time_to_wait.seconds + time_to_wait.days * 24 * 3600) * 10**6) / 10**6
			if seconds_to_wait > 0:
				log.debug("Sleeping for %s seconds", seconds_to_wait)
				time.sleep(seconds_to_wait)
		
		# Select the files we need
		filepaths = OrderedDict()
		for wavelength in wavelengths:
			paths = glob.glob(aia_file_pattern.format(date=start_date, wavelength=wavelength))
			for path in sorted(paths):
				if quality_ok(path):
					filepaths[wavelength] = path
					break
				else:
					log.debug("Skipping file %s with bad quality", path)
		
		# Compute the stats
		stats = pool.map(get_stats, filepaths.values())
		
		# Write the stats to file
		for stat, filepath in zip(stats, filepaths.values()):
			stats_filename = os.path.join(stats_directory, os.path.splitext(os.path.basename(filepath))[0] + ".csv")
			if stat:
				headers = sorted(stat.keys())
				try:
					with open(stats_filename, "w") as stats_file:
						stats_file.write(",".join(headers) + "\n")
						stats_file.write(",".join([str(stat[h]) for h in headers]) + "\n")
					number_errors = max(number_errors - 1, 0)
					logging.info("Wrote stats to file %s", stats_filename)
				except Exception, why:
					logging.error("Could not write stats to files %s", stats_filename)
					number_errors += 1
			else:
				logging.error("Stats missing for file %s", filepath)
				number_errors += 1
		
		# If the number of errors is too high, tell someone
		if number_errors > max_number_errors:
			send_email(sender, emails, "Too many errors in %s" % script_name, ["There has been %d errors in the script %s" % (number_errors, script_name), "Please check the log file %s for reasons, and take any neccesary action" % log_filename])
			# We reset the counter to avoid sending too many emails
			number_errors = 0
		
		# We update the start_date for the next run
		start_date += run_cadence
		
		# We update the status
		status['start_date'] = start_date
		
		# We save the status
		try: 
			pickle_file = open(status_filename, 'wb')
		except IOError, why:
			log.error("Could not open status file %s for saving status: %s", status_filename, str(why))
		else:
			log.debug("Saving status to status file %s", status_filename)
			try:
				pickle.dump(status, pickle_file, -1)
				pickle_file.close()
			except Exception, why:
				log.error("Could not save status from file %s: %s", status_filename, str(why))
			pickle_file.close()
