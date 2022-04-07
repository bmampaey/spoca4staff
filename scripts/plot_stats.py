#!/usr/bin/env python3
import logging
import argparse
import string
import json
import glob
import copy
import collections
import pandas

HTML_TEMPLATE = string.Template('''
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
		<!-- Amcharts 4 library -->
		<script src="https://cdn.amcharts.com/lib/4/core.js"></script>
		<script src="https://cdn.amcharts.com/lib/4/charts.js"></script>
		<title>${column}</title>
</head>

<body>
	<div id="chart" style="width: 100%; height: 500px;"></div>
	<script type="text/javascript">
		am4core.createFromConfig(${chart_config}, "chart");
	</script>
</body>
</html>
''')

COLORS = ['black', 'red', 'green', 'blue']

CHART_CONFIG = {
	'type': 'XYChart',
	'titles': [
		{
			'text': '',
			'fontSize': 16,
			'fontWeight': 600
		}
	],
	'xAxes': [
		{
			'type': 'DateAxis',
			'id': 'xAxis1',
			'title': {
				'text': '(UTC)'
			},
			'tooltipDateFormat': 'dd MMM yyyy\n\u2007HH:mm:ss',
			'baseInterval': {
				'timeUnit': 'second',
				'count': 1
			},
			'dateFormats': {
				'second': 'HH:mm:ss',
				'minute': 'HH:mm:ss',
				'hour': 'HH:mm:ss',
				'day': 'dd MMM YYYY',
				'month': 'MMM YYYY',
				'year': 'YYYY'
			},
			'periodChangeDateFormats': {
				'second': 'HH:mm:ss',
				'minute': 'HH:mm:ss',
				'hour': 'dd MMM YYYY',
				'day': 'MMM YYYY',
				'month': 'YYYY',
				'year': 'YYYY'
			},
			'renderer': {
				'labels': {
					'location': 0.001
				}
			}
		}
	],
	'yAxes': [
		{
			'type': 'ValueAxis',
			'cursorTooltipEnabled': False
		}
	],
	'series': [],
	'dateFormatter': {
		'inputDateFormat': 'i',
		'dateFormat': 'dd MMM yyyy\u2007HH:mm:ss',
		'utc': True
	},
	'fontSize': 12,
	'cursor': {
		'behavior': 'zoomX',
		'lineY': {
			'disabled': True
		}
	},
	'scrollbarX': {
		'type': 'Scrollbar',
		'startGrip': {
			'scale': 0.7
		},
		'endGrip': {
			'scale': 0.7
		}
	},
	'scrollbarY': {
		'type': 'Scrollbar',
		'startGrip': {
			'scale': 0.7
		},
		'endGrip': {
			'scale': 0.7
		}
	},
	'legend': {},
	'data': []
}

SERIES_CONFIG = {
	'type': 'LineSeries',
	'name': '',
	'dataFields': {
		'dateX': 'timestamp',
		'valueY': ''
	},
	'tooltipText': '{valueY}',
	'stroke': ''
}

def get_series_filenames(series_list):
	series_filenames = collections.defaultdict(list)
	for series_name, glob_pattern in series_list:
		series_filenames[series_name].extend(glob.iglob(glob_pattern, recursive=True))
	return series_filenames

def get_series_dataframes(series_filenames, time_column, stats_type = None):
	series_dataframes = dict()
	for series_name, filenames in series_filenames.items():
		dataframe = pandas.concat(pandas.read_csv(filename, index_col = time_column, parse_dates = True) for filename in filenames)
		if stats_type:
			dataframe = dataframe.loc[dataframe['Type'] == stats_type]
		dataframe['timestamp'] = pandas.to_numeric(dataframe.index)/1000000
		dataframe.sort_index(inplace=True)
		series_dataframes[series_name] = dataframe
	return series_dataframes

def get_columns(series_dataframes, columns = None):
	dataframes_columns = set()
	
	for dataframe in series_dataframes.values():
		dataframes_columns.update(dataframe.columns)
	
	if columns is not None:
		dataframes_columns.intersection_update(columns)
	
	return dataframes_columns

def get_data(dataframe, column):
	dataframe = dataframe.get(['timestamp', column])
	dataframe = dataframe.dropna()
	return dataframe.to_dict('records')

def get_chart_config(series_dataframes, column, stats_type):
	
	chart_config = copy.deepcopy(CHART_CONFIG)
	chart_config['titles'][0]['text'] = '%s %s' % (column, stats_type or '')
	
	for (series_name, dataframe), color in zip(series_dataframes.items(), COLORS):
		series_config = copy.deepcopy(SERIES_CONFIG)
		series_config['name'] = series_name
		series_config['stroke'] = color
		series_config['data'] = get_data(dataframe, column)
		series_config['dataFields']['valueY'] = column
		chart_config['series'].append(series_config)
	
	return chart_config

# Start point of the script
if __name__ == '__main__':
	
	# Get the arguments
	parser = argparse.ArgumentParser(description = 'Generate HTML files with plots from csv files')
	parser.add_argument('--verbose', '-v', choices = ['DEBUG', 'INFO', 'ERROR'], default = 'INFO', help = 'Set the logging level (default is INFO)')
	parser.add_argument('--series', '-s', nargs = 2, metavar = ('SERIES-NAME', 'CSV-FILE'), action = 'append', required = True, help = 'The name of the series and a glob of CSV files')
	parser.add_argument('--column', '-c', action = 'append', help = 'The columns to plot; Can be specified multiple times for more than 1 column; If not specified, all columns will be plotted')
	parser.add_argument('--time-column', '-t', required = True, help = 'The name of the column containing the time index')
	parser.add_argument('--stats-type', help = 'For staff stats, filter by type')
	args = parser.parse_args()
	
	# Setup the logging
	logging.basicConfig(level = getattr(logging, args.verbose), format = '%(asctime)s %(levelname)-8s: %(message)s')
	
	series_filenames = get_series_filenames(args.series)
	series_dataframes = get_series_dataframes(series_filenames, args.time_column, args.stats_type)
	columns = get_columns(series_dataframes, args.column)
	for column in columns:
		chart_config = get_chart_config(series_dataframes, column, args.stats_type)
		with open('%s.html' % column, 'wt') as file:
			file.write(HTML_TEMPLATE.substitute(chart_config = json.dumps(chart_config, indent = 2), column = column))
