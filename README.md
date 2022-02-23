# Pipeline to segment SDO/AIA images into Coronal Hole, Active Region and Quiet Sun and submit statistics to the STAFF viewer DB

The following python scripts are used to run the pipeline:
 * __run_spoca_STAFF.py__: Daemon that runs the SPoCA executables and generate the csv files with the CH, AR and QS statistics
 * __get_images_stats.py__: Daemon that extract statistics about SDO/AIA images and generate the csv files with the statistics

The following python scripts are tools for the pipeline:
 * __plot_STAFF_stats.py__: Read the csv statistic files and make timeline plots
 * __test_quality.py__: Test the quality of a SDO/AIA FITS file
 * __spoca_job.py__: Runs a SPoCA executable

All scripts contain at their top environment parameters to properly run without the need to specify them manually when executed.

Configuration files for the programs of the SPoCA suite:
 * __AIA_AR.segmentation.config__: Config file for the classification.x program
 * __AIA_CH.segmentation.config__: Config file for the classification.x program
 * __get_AIA_STAFF_stats.config__: Config file for the get_AIA_STAFF_stats.x program

