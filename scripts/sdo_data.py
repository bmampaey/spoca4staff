#!/usr/bin/env python3
import logging
import argparse
from datetime import datetime
from glob import glob
from astropy.io import fits


__all__ = ['SdoData']

class SdoData:
	'''Helper to find good quality SDO/AIA and SDO/HMI data'''
	
	# Definition of the bits in the FITS header QUALITY keyword
	QUALITY_BITS = {
		0	: 'FLAT_REC == MISSING (Flatfield data not available)',
		1	: 'ORB_REC == MISSING (Orbit data not available)',
		2	: 'ASD_REC == MISSING (Ancillary Science Data not available)',
		3	: 'MPO_REC == MISSING (Master pointing data not available)',
		4	: 'RSUN_LF == MISSING or X0_LF == MISSING or Y0_LF == MISSING (HMI Limb fit not acceptable)',
		5	: '',
		6	: '',
		7	: '',
		8	: 'MISSVALS > 0',
		9	: 'MISSVALS > 0.01*TOTVALS',
		10	: 'MISSVALS > 0.05*TOTVALS',
		11	: 'MISSVALS > 0.25*TOTVALS',
		12	: 'ACS_MODE != "SCIENCE" (Spacecraft not in science pointing mode)',
		13	: 'ACS_ECLP == "YES" (Spacecraft eclipse flag set)',
		14	: 'ACS_SUNP == "NO" (Spacecraft sun presence flag not set)',
		15	: 'ACS_SAFE == "YES" (Spacecraft safemode flag set)',
		16	: 'IMG_TYPE == "DARK" (Dark image)',
		17	: 'HWLTNSET == "OPEN" or AISTATE == "OPEN" (HMI ISS loop open or  AIA ISS loop Open)',
		18	: '(FID >= 1 and FID <= 9999) or (AIFTSID >= 0xC000)  (HMI Calibration Image or AIA Calibration Image)',
		19	: 'HCFTID == 17 (HMI CAL mode image)',
		20	: '(AIFCPS <= -20 or AIFCPS >= 100) (AIA focus out of range)',
		21	: 'AIAGP6 != 0 (AIA register flag)',
		22	: '',
		23	: '',
		24	: '',
		25	: '',
		26	: '',
		27	: '',
		28	: '',
		29	: '',
		30	: 'Quicklook image',
		31	: 'Image not available'
	}
	
	# Default name for the QUALITY keyword (SDO FITS files have also a QUALITY0 keyword)
	QUALITY_KEYWORD = 'QUALITY'
	
	# Default quality bits that can be ignored
	IGNORE_QUALITY_BITS = [0, 1, 2, 3, 4, 8]
	
	# Default HDU of the FITS file that contains the QUALITY keyword
	# Typically SDO data is tiled compressed, so the keywords are in the second HDU
	HDU = 1
	
	# File pattern for AIA FITS files that can be formated with a date and a wavelength
	# File pattern for HMI FITS files that can be formated with a date
	def __init__(self, aia_file_pattern = None, hmi_file_pattern = None, ignore_quality_bits = None, hdu = None, quality_keyword = None):
		self.aia_file_pattern = aia_file_pattern
		self.hmi_file_pattern = hmi_file_pattern
		self.ignore_quality_bits = self.IGNORE_QUALITY_BITS if ignore_quality_bits is None else ignore_quality_bits
		self.hdu = self.HDU if hdu is None else hdu
		self.quality_keyword = self.QUALITY_KEYWORD if quality_keyword is None else quality_keyword
		self._aia_file_cache = dict()
		self._hmi_file_cache = dict()
	
	def get_AIA_file(self, date, wavelength):
		'''Return the path to a AIA FITS file for the specified date and wavelength'''
		if (date, wavelength) not in self._aia_file_cache:
			self._aia_file_cache[(date, wavelength)] = self.get_good_quality_file(self.aia_file_pattern.format(date=date, wavelength=wavelength))
		return self._aia_file_cache[(date, wavelength)]
	
	def get_HMI_file(self, date):
		'''Return the path to a HMI FITS file for the specified date'''
		if date not in self._hmi_file_cache:
			self._hmi_file_cache[date] = self.get_good_quality_file(self.hmi_file_pattern.format(date=date))
		return self._hmi_file_cache[date]
	
	def get_good_quality_file(self, file_pattern):
		'''Return the first file that matches the file_pattern and has a good quality'''
		
		for file_path in sorted(glob(file_pattern)):
			
			# Get the quality of the file
			quality = self.get_quality(file_path)
			
			# Set the ignored quality bits to 0
			for bit in self.ignore_quality_bits:
				quality &= ~(1<<bit)
			
			# A quality of 0 means no defect
			if quality == 0:
				return file_path
			else:
				logging.debug('Skipping file %s with bad quality: %s', file_path, self.get_quality_errors(quality))
	
	def get_quality(self, file_path):
		'''Return the value of the quality keyword of the file'''
		
		with fits.open(file_path) as hdus:
			return hdus[self.hdu].header[self.quality_keyword]
	
	@classmethod
	def get_quality_errors(cls, quality):
		'''Return the set of errors corresponding to the bits set in the quality value'''
		errors = set()
		for bit, msg in cls.QUALITY_BITS.items():
			if quality & (1 << bit):
				errors.add(msg or 'Unknown error')
		return errors

# Start point of the script
if __name__ == '__main__':
	
	# Default value for the aia-file-pattern argument valid for the spoca.oma.be server
	AIA_FILE_PATTERN = '/data/SDO/public/AIA_HMI_1h_synoptic/aia.lev1/{wavelength:04d}/{date.year:04d}/{date.month:02d}/{date.day:02d}/AIA.{date.year:04d}{date.month:02d}{date.day:02d}_{date.hour:02d}*.{wavelength:04d}.*.fits'
	
	parser = argparse.ArgumentParser(description='Prints AIA FITS files for the specified date and wavelength')
	parser.add_argument('date', type = datetime.fromisoformat, help = 'A date in ISO format')
	parser.add_argument('wavelength', type = int, help = 'An AIA wavelength in Ångström')
	parser.add_argument('--aia-file-pattern', '-A', metavar = 'FILE PATTERN', default = AIA_FILE_PATTERN, help='A file pattern for AIA FITS files that can be formated with a date and a wavelength')
	parser.add_argument('--ignore-quality-bits', '-I', metavar = 'QUALITY BIT NUMBER', type = int, action='append', help='The quality bits that can be ignored')
	parser.add_argument('--hdu', '-H', type = int, help='The HDU number that contains the quality keyword')
	parser.add_argument('--quality-keyword', '-K', metavar = 'KEYWORD', help='The name of the quality keyword')
	
	args = parser.parse_args()
	
	sdo_data = SdoData(aia_file_pattern = args.aia_file_pattern, ignore_quality_bits = args.ignore_quality_bits, hdu = args.hdu, quality_keyword = args.quality_keyword)
	
	aia_file = sdo_data.get_AIA_file(args.date, args.wavelength)
	
	if aia_file:
		print(aia_file)
	else:
		print('No file found!')
