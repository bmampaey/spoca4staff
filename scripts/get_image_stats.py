#!/usr/bin/env python3
import logging
import argparse
import numpy
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from astropy.io import fits

from sdo_data import SdoData

def date_range(start, end, step):
	'''Equivalent to range for date'''
	date = start.replace()
	while date < end:
		yield date
		date += step


def get_pixels_stats(pixels, prefix = ''):
	'''Return a dict of various statistics about pixel values'''
	stats = dict()
	
	# Remove the nan from the pixels
	pixels = numpy.ma.masked_invalid(pixels).compressed()
	
	stats[prefix + 'MIN'] = '%.3f' % numpy.min(pixels)
	stats[prefix + 'MAX'] = '%.3f' % numpy.max(pixels)
	stats[prefix + 'MEAN'] = '%.3f' % numpy.mean(pixels)
	stats[prefix + 'RMS'] = '%.3f' % numpy.std(pixels)
	stats[prefix + 'TOTL'] = '%.3f' % numpy.sum(pixels)
	
	# Compute all percentiles at once
	keys = ['P01', 'P10', 'P25', 'MEDN', 'P75', 'P90', 'P95', 'P98', 'P99']
	percentiles = numpy.percentile(pixels, [1,10,25,50,75,90,95,98,99], overwrite_input = True)
	for key, percentile in zip(keys, percentiles):
		stats[prefix + key] = '%.3f' % percentile
	
	return stats


def get_image_stats(filepath, hdu):
	'''Return a dict of various info and statistics about the image'''
	
	stats = dict()
	
	# Get the image and header from the FITS file
	with fits.open(filepath) as hdus:
		header = hdus[hdu].header
		image = hdus[hdu].data
	
	stats['DATE_OBS'] = header['T_OBS']
	stats['WAVELENGTH'] = header['WAVELNTH']
	
	# Normalise the image by the exposure time
	exposure_time = float(header['EXPTIME'])
	image /= exposure_time
	
	# Retrieve the statistics about the whole image
	stats.update(get_pixels_stats(image, prefix = 'DATA'))
	
	# Retrieve the statistics about the solar disk
	# We make the list of pixels on the solar disk
	solar_radius = header['RSUN_OBS'] / header['CDELT1']
	center_x = header['CRPIX1'] - 1
	center_y = header['CRPIX2'] - 1
	x, y = numpy.mgrid[image.shape[0] - center_x : - center_x : -1, - center_y : image.shape[1] - center_y : 1]
	disk_mask = numpy.ma.masked_less_equal(x*x+y*y, solar_radius * solar_radius)
	disk_image = numpy.ma.masked_array(image, disk_mask.mask)
	stats.update(get_pixels_stats(disk_image, prefix = 'DISK'))
	
	return stats


def write_image_stats(filepath, stats):
	'''Write a csv file with a dict of stats (legacy code)'''
	headers = sorted(stats.keys())
	with open(filepath, 'tw') as file:
		file.write(','.join(headers) + '\n')
		file.write(','.join([str(stats[header]) for header in headers]) + '\n')


if __name__ == '__main__':
	
	# Get the arguments
	parser = argparse.ArgumentParser(description='Compute images statistics from AIA FITS files for the STAFF viewer')
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
	
	hdu = config.getint('IMAGE_STATS', 'hdu')
	output_directory = Path(config.get('IMAGE_STATS', 'output_directory'))
	
	for date in date_range(args.start_date, args.end_date, timedelta(hours=args.interval)):
		
		# Get the aia images, if some are missing (== None), just ignore them
		# Compute the statistics and write them as csv
		aia_images = [sdo_data.get_AIA_file(date, wavelength) for wavelength in config.getintlist('IMAGE_STATS', 'wavelengths')]
		
		for aia_image in filter(bool, aia_images):
			
			logging.info('Computing statistics for image %s', aia_image)
			try:
				image_stats = get_image_stats(aia_image, hdu)
			except Exception as why:
				logging.error('Error computing statistics for image %s: %s', aia_image, why)
				continue
			
			csv_file = output_directory / Path(aia_image).with_suffix('.csv').name
			
			logging.info('Writing statistics for image %s to file %s', aia_image, csv_file)
			try:
				image_stats = write_image_stats(csv_file, image_stats)
			except Exception as why:
				logging.error('Error writing statistics for image %s to file %s: %s', aia_image, csv_file, why)
				continue
