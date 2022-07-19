#!/usr/bin/env python3

import logging
import argparse
import warnings
from datetime import datetime, timezone
import numpy
import scipy
from sunpy.map import Map
from aiapy.calibrate import fix_observer_location, update_pointing, normalize_exposure, register, correct_degradation
from astropy.io import fits

__all__ = ['calibrate_aia_map', 'calibrated_aia_fits_file']

def calibrate_aia_map(map):
	'''Take an AIA map, pass it through the calibration procedures of aiapy and update the map meta'''
	# Calibrate the data and update the metadata
	# See https://aiapy.readthedocs.io/en/latest/preparing_data.html
	# We do not apply the PSF correction
	map = update_pointing(map)
	map = fix_observer_location(map)
	map = register(map)
	map = correct_degradation(map)
	map = normalize_exposure(map)
	map.meta['LVL_NUM'] = 2.0
	map.meta['DATE'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
	map.meta['PIXLUNIT'] = 'DN/s'
	
	# Update data statistics
	map.meta['DATAMIN'] = numpy.nanmin(map.data)
	map.meta['DATAMAX'] = numpy.nanmax(map.data)
	map.meta['DATAMEAN'] = numpy.nanmean(map.data)
	map.meta['DATARMS'] = numpy.nanstd(map.data)
	map.meta['DATASKEW'] = scipy.stats.skew(map.data, axis = None, nan_policy = 'omit', bias = True)
	map.meta['DATAKURT'] = scipy.stats.kurtosis(map.data, axis = None, nan_policy = 'omit', bias = True)
	map.meta['DATAMEDN'], map.meta['DATAP01'], map.meta['DATAP10'],map.meta['DATAP25'],map.meta['DATAP75'],map.meta['DATAP90'], map.meta['DATAP95'], map.meta['DATAP98'], map.meta['DATAP99'] = numpy.nanpercentile(map.data, [50, 1, 10, 25, 75, 90, 95, 98, 99])
	
	# The register convert the data to float, so the BLANK keyword is invalid
	del map.meta['BLANK']
	
	# Remove DATACENT, it is not clear how it is computed
	del map.meta['DATACENT']
	
	# Add history (sunpy uses the newline as a separator for the HISTORY lines)
	history = map.meta.get('history', '')
	if history and not history.endswith('\n'):
		history += '\n'
	history += 'Level 1 image calibrated using the aiapy Python module:\nupdate_pointing, fix_observer_location, register,\ncorrect_degradation, normalize_exposure'
	map.meta['HISTORY'] = history
	
	return map

def calibrate_aia_fits_file(input_file, output_file, overwrite = False):
	'''Take a level 1 AIAI FITS file and write the calibrated level 2 FITS file'''
	map = Map(input_file)
	calibrated_map = calibrate_aia_map(map)
	calibrated_map.save(output_file, overwrite = overwrite, hdu_type = fits.CompImageHDU, checksum = True)

# Start point of the script
if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Calibrate an AIA FITS files from level 1 to level 2')
	parser.add_argument('input', metavar = 'INPUT-FITSFILE', help = 'The path to the level 1 file to calibrate')
	parser.add_argument('output', metavar = 'OUTPUT-FITSFILE', help = 'The path to the level 2 file to write')
	parser.add_argument('--overwrite', action = 'store_true', help = 'Overwrite the output file if it already exists')
	parser.add_argument('--verbose', '-v', choices = ['DEBUG', 'INFO', 'ERROR'], default = 'INFO', help='Set the logging level (default is INFO)')
	args = parser.parse_args()
	
	# Turn off the many warnings from sunpy and scipy
	if args.verbose != 'DEBUG':
		warnings.filterwarnings("ignore")
	
	# Setup the logging
	logging.basicConfig(level = getattr(logging, args.verbose), format = '%(asctime)s %(levelname)-8s: %(message)s')
	
	calibrate_aia_fits_file(args.input, args.output, overwrite = args.overwrite)
