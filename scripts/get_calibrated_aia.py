#!/usr/bin/env python3

import sys
import logging
import argparse
import warnings
from datetime import datetime, timedelta
from pathlib import Path

from aia_calibration import calibrate_aia_fits_file
from sdo_data import SdoData

# Pattern that accepts a date and wavelength of where the AIA FITS files are located
INPUT_FILE_PATTERN = '/data/SDO/AIA_HMI_1h_synoptic/aia.lev1/{wavelength:04d}/{date.year:04d}/{date.month:02d}/{date.day:02d}/AIA.{date.year:04d}{date.month:02d}{date.day:02d}_{date.hour:02d}*.{wavelength:04d}.*.fits'
OUTPUT_FILE_PATTERN = '{wavelength:04d}/{date.year:04d}/{date.month:02d}/{date.day:02d}/'

def date_range(start, end, step):
	'''Equivalent to range for date'''
	date = start.replace()
	while date < end:
		yield date
		date += step

# Start point of the script
if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Write the calibrated AIA FITS files')
	parser.add_argument('--verbose', '-v', choices = ['DEBUG', 'INFO', 'ERROR'], default = 'INFO', help='Set the logging level (default is INFO)')
	parser.add_argument('--start-date', '-s', required = True, type = datetime.fromisoformat, help = 'Start date of AIA files (ISO 8601 format)')
	parser.add_argument('--end-date', '-e', default = datetime.utcnow(), type = datetime.fromisoformat, help = 'End date of AIA files (ISO 8601 format)')
	parser.add_argument('--interval', '-i', default = 6, type = int, help = 'Number of hours between two files')
	parser.add_argument('--wavelength', '-w', default = [171, 193], nargs = '+', type = int, help = 'The AIA wavelengths to process')
	parser.add_argument('--overwrite', action = 'store_true', help = 'Overwrite the output file if it already exists')
	parser.add_argument('--output-dir', '-o', default = '.', type = Path, help = 'The directory where to write the files')
	
	args = parser.parse_args()
	
	# Turn off the many warnings from sunpy and scipy
	if args.verbose != 'DEBUG':
		warnings.filterwarnings("ignore")
	
	# Setup the logging
	logging.basicConfig(level = getattr(logging, args.verbose), format = '%(asctime)s %(levelname)-8s: %(message)s')
	
	sdo_data = SdoData(
		aia_file_pattern = INPUT_FILE_PATTERN,
		ignore_quality_bits = []
	)
	
	if not args.output_dir.is_dir():
		logging.critical('%s is not a directory', args.output_dir)
		sys.exit(2)
	
	for date in date_range(args.start_date, args.end_date, timedelta(hours=args.interval)):
		for wavelength in args.wavelength:
			
			input_file = sdo_data.get_AIA_file(date, wavelength)
			
			if input_file is None:
				logging.info('No AIA file found for date %s and wavelength %s, skipping!', date, wavelength)
				continue
			
			output_directory = args.output_dir / OUTPUT_FILE_PATTERN.format(date = date, wavelength = wavelength)
			output_directory.mkdir(parents = True, exist_ok = True)
			output_file = output_directory / (Path(input_file).name.rsplit('.', 2)[0] + '.image_lev2.fits')
			
			if not args.overwrite and output_file.exists():
				logging.info('File %s exists already, skipping!', output_file)
				continue
			
			try:
				calibrate_aia_fits_file(input_file, str(output_file), overwrite = args.overwrite)
			except Exception as why:
				logging.error('Could not write calibrated file for file %s: %s', input_file, why)
			else:
				logging.info('Wrote calibrated file %s', output_file)
