#!/usr/bin/env python3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.colorbar as clb
import pandas as pandas
import os.path

headers = ['MinIntensity', 'MaxIntensity', 'TotalIntensity', 'Area_Raw']
headers2 = ["Median", "FillingFactor"]
time_index = "ObservationDate"

filenames = {
171 : "STAFF_stats_AIA_171.csv",
193 : "STAFF_stats_AIA_193.csv"
}


for (wavelength, filename) in filenames.items():
	# We parse the csv file
	csv = pandas.read_csv(filename, parse_dates = time_index, index_col = time_index)
	
	# We create sub csv for each type
	csvs = dict.fromkeys(csv["Type"].unique())
	for key in list(csvs.keys()):
		csvs[key] = csv[csv.Type == key]
	
	# We plot the AR_all vs AR_ondisc comparison
	figure, axes = plt.subplots(nrows=len(headers), sharex=True)
	for axe, header in zip(axes, headers):
		axe.scatter(csvs["AR_all"].index, csvs["AR_all"][header], label = "AR_all", color='blue', edgecolors = 'none', marker='.')
		axe.scatter(csvs["AR_ondisc"].index, csvs["AR_ondisc"][header], label = "AR_ondisc", color='red', edgecolors = 'none', marker='.')
		
		axe.set_title(header)
		axe.set_xlim('2010-01-01', '2014-01-01')
	
	# We make one legend for the whole figure
	handles, labels = axes[0].get_legend_handles_labels()
	figure.legend(handles, labels, loc = 'upper right')
	
	figure.suptitle("AR_all vs AR_ondisc STAFF stats on AIA {wavelength}A".format(wavelength = wavelength))
	figure.set_size_inches(16,9)
	figure.subplots_adjust(hspace=0.2, wspace=0.1)
	figure.savefig("AR_all_vs_AR_ondisc_STAFF_stats_AIA{wavelength}.png".format(wavelength = wavelength), bbox_inches='tight')
	
	print("Check that values are of OK for AR_all vs AR_ondisc ", wavelength)
	bads = csvs['AR_all'][csvs['AR_all']["MinIntensity"] > csvs['AR_ondisc']["MinIntensity"]].index
	print("Found following bad MinIntensity", bads)
	bads = csvs['AR_all'][csvs['AR_all']["MaxIntensity"] < csvs['AR_ondisc']["MaxIntensity"]].index
	print("Found following bad MaxIntensity", bads)
	bads = csvs['AR_all'][csvs['AR_all']["Area_Raw"] < csvs['AR_ondisc']["Area_Raw"]].index
	print("Found following bad Area_Raw", bads)
	bads = csvs['AR_all'][csvs['AR_all']["TotalIntensity"] < csvs['AR_ondisc']["TotalIntensity"]].index
	print("Found following bad TotalIntensity", bads)
	
	# We plot the CH_ondisc vs CH_central_meridian comparison
	figure, axes = plt.subplots(nrows=len(headers), sharex=True)
	for axe, header in zip(axes, headers):
		axe.scatter(csvs["CH_ondisc"].index, csvs["CH_ondisc"][header], label = "CH_ondisc", color='blue', edgecolors = 'none', marker='.')
		axe.scatter(csvs["CH_central_meridian"].index, csvs["CH_central_meridian"][header], label = "CH_central_meridian", color='red', edgecolors = 'none', marker='.')
		
		axe.set_title(header)
		axe.set_xlim('2010-01-01', '2014-01-01')
	
	# We make one legend for the whole figure
	handles, labels = axes[0].get_legend_handles_labels()
	figure.legend(handles, labels, loc = 'upper right')
	
	figure.suptitle("CH_ondisc vs CH_central_meridian STAFF stats on AIA {wavelength}A".format(wavelength = wavelength))
	figure.set_size_inches(16,9)
	figure.subplots_adjust(hspace=0.2, wspace=0.1)
	figure.savefig("CH_ondisc_vs_CH_central_meridian_STAFF_stats_AIA{wavelength}.png".format(wavelength = wavelength), bbox_inches='tight')
	
	print("Check that values are OK of for CH_ondisc vs CH_central_meridian", wavelength)
	bads = csvs['CH_ondisc'][csvs['CH_ondisc']["MinIntensity"] > csvs['CH_central_meridian']["MinIntensity"]].index
	print("Found following bad MinIntensity", bads)
	bads = csvs['CH_ondisc'][csvs['CH_ondisc']["MaxIntensity"] < csvs['CH_central_meridian']["MaxIntensity"]].index
	print("Found following bad MaxIntensity", bads)
	bads = csvs['CH_ondisc'][csvs['CH_ondisc']["Area_Raw"] < csvs['CH_central_meridian']["Area_Raw"]].index
	print("Found following bad Area_Raw", bads)
	bads = csvs['CH_ondisc'][csvs['CH_ondisc']["TotalIntensity"] < csvs['CH_central_meridian']["TotalIntensity"]].index
	print("Found following bad TotalIntensity", bads)
	
	# We plot the filling factors of CH_ondisc QS_ondisc and AR_ondisc
	figure, axes = plt.subplots(nrows=len(headers2), sharex=True)
	for axe, header in zip(axes, headers2):
		axe.scatter(csvs["CH_ondisc"].index, csvs["CH_ondisc"][header], label = "CH_ondisc", color='blue', edgecolors = 'none', marker='.')
		axe.scatter(csvs["AR_ondisc"].index, csvs["AR_ondisc"][header], label = "AR_ondisc", color='red', edgecolors = 'none', marker='.')
		axe.scatter(csvs["QS_ondisc"].index, csvs["QS_ondisc"][header], label = "QS_ondisc", color='green', edgecolors = 'none', marker='.')
		axe.set_title(header)
		axe.set_xlim('2010-01-01', '2014-01-01')
	
	# We make one legend for the whole figure
	handles, labels = axes[0].get_legend_handles_labels()
	figure.legend(handles, labels, loc = 'upper right')
	
	figure.suptitle("CH AR and QS on disc STAFF stats on AIA {wavelength}A".format(wavelength = wavelength))
	figure.set_size_inches(16,9)
	figure.subplots_adjust(hspace=0.2, wspace=0.1)
	figure.savefig("CH_AR_QS_ondisc_STAFF_stats_AIA{wavelength}.png".format(wavelength = wavelength), bbox_inches='tight')
	
	print("Check that filling factors are OK of for ", wavelength)
	bads = csvs['CH_ondisc'][csvs['CH_ondisc']["FillingFactor"] > 0.3].index
	print("Found following bad for AR", bads)
	bads = csvs['AR_ondisc'][csvs['AR_ondisc']["FillingFactor"] > 0.4].index
	print("Found following bad for CH", bads)
	bads = csvs['QS_ondisc'][csvs['QS_ondisc']["FillingFactor"] < 0.6].index
	print("Found following bad for QS", bads)
