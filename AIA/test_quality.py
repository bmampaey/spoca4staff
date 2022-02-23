#!/usr/bin/python2.6
import os, os.path, sys
import pyfits
import glob
from datetime import datetime
import argparse

quality_bits = {
0	: "FLAT_REC == MISSING (Flatfield data not available)",
1	: "ORB_REC == MISSING (Orbit data not available)",
2	: "ASD_REC == MISSING (Ancillary Science Data not available)",
3	: "MPO_REC == MISSING (Master pointing data not available)",
4	: "RSUN_LF == MISSING or X0_LF == MISSING or Y0_LF == MISSING (HMI Limb fit not acceptable)",
5	: "",
6	: "",
7	: "",
8	: "MISSVALS > 0",
9	: "MISSVALS > 0.01*TOTVALS",
10	: "MISSVALS > 0.05*TOTVALS",
11	: "MISSVALS > 0.25*TOTVALS",
12	: "ACS_MODE != 'SCIENCE' (Spacecraft not in science pointing mode)",
13	: "ACS_ECLP == 'YES' (Spacecraft eclipse flag set)",
14	: "ACS_SUNP == 'NO' (Spacecraft sun presence flag not set)",
15	: "ACS_SAFE == 'YES' (Spacecraft safemode flag set)",
16	: "IMG_TYPE == 'DARK' (Dark image)",
17	: "HWLTNSET == 'OPEN' or AISTATE == 'OPEN' (HMI ISS loop open or  AIA ISS loop Open)",
18	: "(FID >= 1 and FID <= 9999) or (AIFTSID >= 0xC000)  (HMI Calibration Image or AIA Calibration Image)",
19	: "HCFTID == 17 (HMI CAL mode image)",
20	: "(AIFCPS <= -20 or AIFCPS >= 100) (AIA focus out of range)",
21	: "AIAGP6 != 0 (AIA register flag)",
22	: "",
23	: "",
24	: "",
25	: "",
26	: "",
27	: "",
28	: "",
29	: "",
30	: "Quicklook image",
31	: "Image not available"
}

ok_bits = {
0	: True,
1	: True,
2	: True,
3	: True,
4	: True,
5	: False,
6	: False,
7	: False,
8	: False,
9	: False,
10	: False,
11	: False,
12	: False,
13	: False,
14	: False,
15	: False,
16	: False,
17	: False,
18	: False,
19	: False,
20	: False,
21	: False,
22	: False,
23	: False,
24	: False,
25	: False,
26	: False,
27	: False,
28	: False,
29	: False,
30	: False,
31	: False
}

nok_bits = 0
for i, ok in ok_bits.iteritems():
	if not ok: nok_bits += 2**i

def get_quality_errors(quality):
	errors = []
	bitfield = [True if digit=='1' else False for digit in bin(quality)[2:]]
	for i, is_set in enumerate(reversed(bitfield)):
		if is_set:
			errors.append(quality_bits[i])

# Start point of the script
if __name__ == "__main__":
	
	parser = argparse.ArgumentParser(description='Test the quality of AIA fits files.')
	parser.add_argument('filename', nargs='+', help='The path to the fits files to test')
	
	for filename in args.filename:
		filepaths = glob.glob(filename)
		for filepath in filepaths:
			try:
				header = pyfits.open(filepath)[0].header
				if header['QUALITY'] == 0:
					print filepath, " is good quality"
				elif header['QUALITY'] & nok_bits == 0:
					print filepath, " is good quality, BUT: " + ";".join(get_quality_errors(header['QUALITY']))
				else:
					print filepath, " is bad quality: " + ";".join(get_quality_errors(header['QUALITY']))
			except Exception, why:
				print "Error reading quality for file ", filepath
