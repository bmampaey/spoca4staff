#!/usr/bin/env python3
import argparse
import subprocess
import logging

__all__ = ['Job', 'JobError']

class Job:
	'''Class to run an executable'''

	def __init__(self, executable, positional_parameters = [], optional_parameters = {}):
		self.executable = executable
		self.positional_parameters = list(positional_parameters)
		self.optional_parameters = dict(optional_parameters)
	
	def get_command(self, positional_parameters = None, optional_parameters = None):
		'''Return the command and the parameters'''
		
		# Merge init positional parameters and given positional parameters
		if positional_parameters:
			positional_parameters = self.positional_parameters + positional_parameters
		else:
			positional_parameters = self.positional_parameters
		
		# Merge init optional parameters and passed optional parameters
		if optional_parameters:
			# Passed optional_parameters take precedence over init optional parameters
			optional_parameters = { **self.optional_parameters, **optional_parameters }
		else:
			optional_parameters = self.optional_parameters
		
		# Create the command
		command = [self.executable]
		
		# Add optional parameters
		for key, value in optional_parameters.items():
			command.append('--' + key)
			if value is not None:
				command.append(value)
		
		# Add positional parameters
		command.extend(positional_parameters)
		
		return [ str(c) for c in command ]
	
	def execute(self, input = None, positional_parameters = None, optional_parameters = None):
		'''Run the executable with specified input and additional parameters, and return the exit code, output and error'''
		
		command = self.get_command(positional_parameters, optional_parameters)
		
		logging.debug('Executing job %s', ' '.join(command))
		
		process = subprocess.run(command, input = input, stdout = subprocess.PIPE, stderr = subprocess.PIPE, encoding = 'utf8')
		
		return process.returncode, process.stdout, process.stderr
	
	def __str__(self):
		return ' '.join(self.get_command())


class JobError(Exception):
	def __init__(self, executable = None, exit_code = None, output = None, error = None, message = None, **extra):
		self.executable = executable
		self.exit_code = exit_code
		self.output = output
		self.error = error
		self.message = message
		self.extra = extra
	
	def __str__(self):
		message = ''
		if self.message is not None:
			message += self.message.format(exit_code = self.exit_code, output = self.output, error = self.error, executable = self.executable, **self.extra)
		else:
			if self.executable:
				message += 'Error executing {executable}:'.format(executable = self.executable)
			else:
				message += 'Error:'
			if self.exit_code is not None:
				message += '\Exit code: {exit_code}'.format(exit_code = self.exit_code)
			if self.error:
				message += '\nError: {error}'.format(error = self.error)
			if self.output:
				message += '\nOutput: {output}'.format(output = self.output)
			if self.extra:
				message += '\nExtra info: {extra}'.format(extra = self.extra)
		
		return message


# Start point of the script
if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description = 'Run executable as a job', prefix_chars = '@')
	parser.add_argument('executable', help = 'The path to the executable')
	parser.add_argument('parameters', metavar = 'PARAM', nargs = '*', help = 'Any additional parameter')
	
	args = parser.parse_args()
	
	job = Job(args.executable, positional_parameters = args.parameters)
	
	print(job)
	
	result = job.execute()
	
	print('Exit code: %s\nOutput:\n%s\nError:\n%s' % result)
	
