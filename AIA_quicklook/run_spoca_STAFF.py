#!/usr/bin/env python3
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
from spoca_job import segmentation, get_STAFF_stats
import pyfits
import test_quality

# Directory where the prepped AIA files are located
aia_file_pattern = "/data/SDO/public/AIA_quicklook/{wavelength:04d}/{date.year:04d}/{date.month:02d}/{date.day:02d}/H{date.hour:02d}00/AIA.{date.year:04d}{date.month:02d}{date.day:02d}_{date.hour:02d}*.{wavelength:04d}.*.fits"

# The date of the first data to process
start_date = datetime(2015,10,16,12,00,00)

# Path to the spoca_ar classification program
spoca_ar_bin = "/home/staff/SPoCA/bin2/classification.x"

# Path to the config of spoca_ar classification program
spoca_ar_config = "/data/STAFF/AIA_quicklook/AIA_AR.segmentation.config"

# Wavelengths for spoca_ar
spoca_ar_wavelengths = [171, 193]

# Directory to output the CH maps
ARmaps_directory = "/data/STAFF/AIA_quicklook/AR_segmentation/"

# Path to the spoca_ch classification program
spoca_ch_bin = "/home/staff/SPoCA/bin1/classification.x"

# Path to the config of spoca_ch classification program
spoca_ch_config = "/data/STAFF/AIA_quicklook/AIA_CH.segmentation.config"

# Wavelengths for spoca_ch
spoca_ch_wavelengths = [193]

# Directory to output the AR maps
CHmaps_directory = "/data/STAFF/AIA_quicklook/CH_segmentation/"

# Path to the get_STAFF_stats program
get_STAFF_stats_bin = "/home/staff/SPoCA/bin/get_STAFF_stats.x"

# Path to the config of get_STAFF_stats program
get_STAFF_stats_config = "/data/STAFF/AIA_quicklook/get_AIA_STAFF_stats.config"

# Wavelengths for get_STAFF_stats
get_STAFF_stats_wavelengths = [171, 193]

# Directory to output the STAFF stats results
stats_directory = "/data/STAFF/AIA_quicklook/spoca_stats"

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
	except Exception as why:
		log.critical("Could not send mail %s to smtp server %s: %s", msg.as_string(), smtp_server, str(why))

def quality_ok(filepath):
	header = pyfits.open(filepath)[0].header
	if 'QUALITY' in header:
		return header['QUALITY'] & test_quality.nok_bits == 0
	else:
		log.warning("Missing quality keyword for file %s", filepath)
		return False

def setup_spoca(spoca_bin, configfile, output_dir):
	
	class segmentation_instance(segmentation):
		pass
	
	segmentation_instance.set_parameters(configfile, output_dir)
	segmentation_instance.bin = spoca_bin
	ok, reason = segmentation_instance.test_parameters()
	if ok:
		log.info("Spoca parameters in file %s seem ok", configfile)
		log.debug(reason)
	else:
		log.warn("Spoca parameters in file %s could be wrong", configfile)
		log.warn(reason)
	
	return segmentation_instance


def run_spoca(spoca, fitsfiles, name):
	
	log.info("Running spoca on files %s", fitsfiles)
	spoca_command = [spoca.bin] + spoca.build_arguments(fitsfiles, name)
	spoca_process = subprocess.Popen(spoca_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, errors = spoca_process.communicate()
	if spoca_process.returncode == 0:
		log.debug("Sucessfully ran spoca command %s, output: %s, errors: %s", ' '.join(spoca_command), str(output), str(errors))
		return True
	else:
		log.error("Error running spoca command %s, output: %s, errors: %s", ' '.join(spoca_command), str(output), str(errors))
		return False

def run_get_STAFF_stats(get_STAFF_stats, ARmap, CHmap, fitsfiles):
	
	log.info("Running get_STAFF_stats on CHmap %s, ARmap %s, and files %s", CHmap, ARmap, fitsfiles)
	log.debug(" ".join([get_STAFF_stats.bin] + get_STAFF_stats.build_arguments(CHmap, ARmap, fitsfiles)))
	get_STAFF_stats_command = [get_STAFF_stats.bin] + get_STAFF_stats.build_arguments(CHmap, ARmap, fitsfiles)
	get_STAFF_stats_process = subprocess.Popen(get_STAFF_stats_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output, errors = get_STAFF_stats_process.communicate()
	if get_STAFF_stats_process.returncode == 0:
		log.debug("Sucessfully ran get_STAFF_stats command %s, output: %s, errors: %s", ' '.join(get_STAFF_stats_command), str(output), str(errors))
		return True
	else:
		log.error("Error running get_STAFF_stats command %s, output: %s, errors: %s", ' '.join(get_STAFF_stats_command), str(output), str(errors))
		return False

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
	except IOError as why:
		log.info("Could not open status file %s for restoring status: %s", status_filename, str(why))
	else:
		log.info("Restoring previous status from status file %s", status_filename)
		try:
			status = pickle.load(pickle_file)
			pickle_file.close()
			log.info("Status restored: %s", status)
		except Exception as why:
			log.critical("Could not restore status from file %s: %s", status_filename, str(why))
			sys.exit(2)
	
	# Parse the status
	if status:
		try:
			start_date = status['start_date']
		except ValueError as why:
			log.warning("Could not restore start_date from status, skipping")
	
	# Setup the spoca_ar segmentation parameters
	spoca_ar = setup_spoca(spoca_ar_bin, spoca_ar_config, ARmaps_directory)
	
	# Setup the spoca_ch segmentation parameters
	spoca_ch = setup_spoca(spoca_ch_bin, spoca_ch_config, CHmaps_directory)
	
	# Setup the get_STAFF_stats
	get_STAFF_stats.set_parameters(get_STAFF_stats_config, stats_directory)
	get_STAFF_stats.bin = get_STAFF_stats_bin
	ok, reason = get_STAFF_stats.test_parameters()
	if ok:
		log.info("get_STAFF_stats parameters in file %s seem ok", get_STAFF_stats_config)
		log.debug(reason)
	else:
		log.warn("get_STAFF_stats parameters in file %s could be wrong", get_STAFF_stats_config)
		log.warn(reason)
	
	# Make the list of all needed wavelengths
	wavelengths = sorted(list(set(spoca_ar_wavelengths + spoca_ch_wavelengths + get_STAFF_stats_wavelengths)))
	
	# Counter for the number of failure
	number_errors = 0
	
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
		
		# Check if we have all the files we need
		stop = not all(w in filepaths for w in wavelengths)
		if stop:
			log.warning("Missing some aia files for date %s. Not running spoca.", start_date)
		
		map_name = start_date.strftime('%Y%m%d_%H%M%S')
		
		# We run spoca for AR
		if not stop:
			stop = not run_spoca(spoca_ar, [filepaths[w] for w in spoca_ar_wavelengths], map_name)
		
		# We check if the ARmap exists
		if not stop:
			ARmap = os.path.join(ARmaps_directory, map_name+'.SegmentedMap.fits')
			if not os.path.exists(ARmap):
				log.error("Could not find ARmap %s", ARmap)
				stop = True
		
		# We run spoca for CH
		if not stop:
			stop = not run_spoca(spoca_ch, [filepaths[w] for w in spoca_ch_wavelengths], map_name)
		
		# We check if the CHmap exists
		if not stop:
			CHmap = os.path.join(CHmaps_directory, map_name+'.SegmentedMap.fits')
			if not os.path.exists(CHmap):
				log.error("Could not find CHmap %s", CHmap)
				stop = True
		
		# Run get_STAFF_stats
		if not stop:
			stop = not run_get_STAFF_stats(get_STAFF_stats, ARmap, CHmap, [filepaths[w] for w in get_STAFF_stats_wavelengths])
		
		# Check if there was an error
		if stop:
			# If stop is set there was an error, we increase the counter
			number_errors += 1
		else:
			# If stop is not set there was no error, we decrease the counter
			number_errors = max(number_errors - 1, 0)
		
		# If the number of errors is too high, tell someone
		if number_errors > max_number_errors:
			send_email(sender, emails, "Too many errors in %s" % script_name, ["There has been %d errors in the script %s" % (number_errors, script_name), "Please check the log file %s for reasons, and take any neccesary action" % log_filename])
			# We reset the counter to avoid sendinf too many emails
			number_errors = 0
		
		# We update the start_date for the next run
		start_date += run_cadence
		
		# We update the status
		status['start_date'] = start_date
		
		# We save the status
		try:
			pickle_file = open(status_filename, 'wb')
		except IOError as why:
			log.error("Could not open status file %s for saving status: %s", status_filename, str(why))
		else:
			log.debug("Saving status to status file %s", status_filename)
			try:
				pickle.dump(status, pickle_file, -1)
				pickle_file.close()
			except Exception as why:
				log.error("Could not save status from file %s: %s", status_filename, str(why))
			pickle_file.close()
