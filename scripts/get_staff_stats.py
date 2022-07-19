#!/usr/bin/env python3
import logging
import argparse
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path

from sdo_data import SdoData
from staff_jobs import SegmentationJob, GetStaffStatsJob


def date_range(start, end, step):
	'''Equivalent to range for date'''
	date = start.replace()
	while date < end:
		yield date
		date += step

# Start point of the script
if __name__ == '__main__':
	
	# Get the arguments
	parser = argparse.ArgumentParser(description='Compute statistics about AR CH and QS from AIA FITS files for the STAFF viewer using the SPoCA software suite')
	parser.add_argument('--verbose', '-v', choices = ['DEBUG', 'INFO', 'ERROR'], default = 'INFO', help='Set the logging level (default is INFO)')
	parser.add_argument('--config-file', '-c', required = True, help = 'Path to the config file of the script')
	parser.add_argument('--start-date', '-s', required = True, type = datetime.fromisoformat, help = 'Start date of AIA files (ISO 8601 format)')
	parser.add_argument('--end-date', '-e', default = datetime.utcnow(), type = datetime.fromisoformat, help = 'End date of AIA files (ISO 8601 format)')
	parser.add_argument('--interval', '-i', default = 6, type = int, help = 'Number of hours between two results')
	
	args = parser.parse_args()
	
	# Setup the logging
	logging.basicConfig(level = getattr(logging, args.verbose), format = '%(asctime)s %(levelname)-8s: %(message)s')
	
	# Parse the script config file
	# To allow parsing list of wavelengths or quality bits
	# add a getter for list of int from comma separated values
	# (allows for random spaces e.g "1, 2,3  " will give [1,2,3])
	config = ConfigParser(converters={'intlist': lambda v: [int(i) for i in v.split(',')]})
	config.read(args.config_file)
		
	sdo_data = SdoData(
		aia_file_pattern = config.get('SDO_DATA', 'aia_file_pattern'),
		ignore_quality_bits = config.getintlist('SDO_DATA', 'ignore_quality_bits'),
		hdu = config.getint('SDO_DATA', 'hdu')
	)
	
	ar_segmentation = SegmentationJob(
		config.get('AR_SEGMENTATION', 'executable'),
		config.get('AR_SEGMENTATION', 'config_file'),
		config.get('AR_SEGMENTATION', 'centers_file')
	)
	
	ch_segmentation = SegmentationJob(
		config.get('CH_SEGMENTATION', 'executable'),
		config.get('CH_SEGMENTATION', 'config_file'),
		config.get('CH_SEGMENTATION', 'centers_file')
	)
	
	get_staff_stats = GetStaffStatsJob(
		config.get('STAFF_STATS', 'executable'),
		config.get('STAFF_STATS', 'config_file'),
		config.get('STAFF_STATS', 'output_directory')
	)
	
	for date in date_range(args.start_date, args.end_date, timedelta(hours=args.interval)):
		
		map_name = date.strftime('%Y%m%d_%H%M%S') + '.SegmentedMap.fits'
		
		# Execute the AR segmentation
		ar_segmentation_map = Path(config.get('AR_SEGMENTATION', 'output_directory'), map_name)
		
		aia_images = [sdo_data.get_AIA_file(date, wavelength) for wavelength in config.getintlist('AR_SEGMENTATION', 'wavelengths')]
		if None in aia_images:
			logging.warning('AIA image missing for creating AR segmentation map %s, skipping!', ar_segmentation_map)
			continue
		
		logging.info('Creating AR segmentation map %s', ar_segmentation_map)
		ar_segmentation.execute(aia_images, ar_segmentation_map)
		
		# Execute the CH segmentation
		ch_segmentation_map = Path(config.get('CH_SEGMENTATION', 'output_directory'), map_name)
		
		aia_images = [sdo_data.get_AIA_file(date, wavelength) for wavelength in config.getintlist('CH_SEGMENTATION', 'wavelengths')]
		if None in aia_images:
			logging.warning('AIA image missing for creating CH segmentation map %s, skipping!', ch_segmentation_map)
			continue
		
		logging.info('Creating CH segmentation map %s', ch_segmentation_map)
		ch_segmentation.execute(aia_images, ch_segmentation_map)
		
		# Execute get_staff_stats
		aia_images = [sdo_data.get_AIA_file(date, wavelength) for wavelength in config.getintlist('STAFF_STATS', 'wavelengths')]
		
		# Remove missing images
		aia_images = [aia_image for aia_image in aia_images if aia_image is not None]
		
		if not aia_images:
			logging.info('No AIA image found for computing STAFF statistics from maps %s and %s, skipping!', ar_segmentation_map, ch_segmentation_map)
			continue
		
		logging.info('Computing STAFF statistics from maps %s and %s', ar_segmentation_map, ch_segmentation_map)
		get_staff_stats.execute(ar_segmentation_map, ch_segmentation_map, aia_images)
