#!/usr/bin/env python3
from pathlib import Path

from job import Job, JobError

__all__ = ['SegmentationJob', 'GetStaffStatsJob']

class SegmentationJob(Job):
	'''Job to execute the SPoCA classification executable to get a segmentation map'''
	
	def __init__(self, executable, config_file, centers_file):
		optional_parameters = {
			'config' : config_file,
			'centersFile' : centers_file
		}
		super().__init__(executable, optional_parameters = optional_parameters)
	
	def execute(self, aia_images, output_file):
		'''Execute the SPoCA classification on the specified AIA images'''
		
		optional_parameters = {
			'output': output_file
		}
		
		exit_code, output, error = super().execute(positional_parameters = aia_images, optional_parameters = optional_parameters)
		
		# Check if the job ran succesfully
		if exit_code != 0:
			raise JobError(self.executable, exit_code, output, error, aia_images = aia_images)
		
		# Check if the output file was actually created
		if not Path(output_file).is_file():
			raise JobError(self.executable, exit_code, output, error, message = 'Could not find output file {output_file}', output_file = output_file)


class GetStaffStatsJob(Job):
	'''Job to execute the classification SPoCA executable to get a STAFF statitics file'''
	
	def __init__(self, executable, config_file, output_directory):
		optional_parameters = {
			'config' : config_file,
			'output' : output_directory
		}
		super().__init__(executable, optional_parameters = optional_parameters)
	
	def execute(self, ar_segmentation_map, ch_segmentation_map, sun_images):
		'''Execute the SPoCA get_STAFF_stats on the specified AR and CH segmentation maps and extract the statistics for the specified images'''
		
		exit_code, output, error = super().execute(positional_parameters = [ar_segmentation_map, ch_segmentation_map] + sun_images)
		
		# Check if the job ran succesfully
		if exit_code != 0:
			raise JobError(self.executable, exit_code, output, error, ar_segmentation_map = ar_segmentation_map, ch_segmentation_map = ch_segmentation_map)
