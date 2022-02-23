# Pipeline to generate statistics for the STAFF viewer

The pipeline segments SDO/AIA images into Coronal Hole, Active Region and Quiet Sun using the SPoCA suite, and compute statistics about these regions. The pipeline also computes raw statistics about the SDO/AIA images themselves. The statistics are written to CSV files that pulled by the STAFF viewer server to be ingested into it's database.

The following python scripts are used to run the pipeline:
 * __get_staff_stats.py__: Run the programs ch_segmentation.x, ar_segmentation.x, get_STAFF_stats.x from the SPoCA suite to create the CSV files containing the statistics about Coronal Hole, Active Region and Quiet Sun
 * __get_image_stats.py__: Compute statistics about the SDO/AIA images used by the get_staff_stats.py script and create CSV files.

The scripts accept ini configuration files that contain the parameters for the script:
 * __configs/AIA.quicklook.ini__: Parameters to run the script for on SDO/AIA quicklook level images
 * __configs/AIA.science.ini__: Parameters to run the script for on SDO/AIA science level prepped images

The following python scripts are tools for the pipeline:
 * __job.py__: Runs a program
 * __staff_jobs.py__: Runs the ch_segmentation.x, ar_segmentation.x, get_STAFF_stats.x programs with the proper arguments
 * __sdo_data.py__: Find good quality SDO data for running the segmentation

Configuration files for the programs of the SPoCA suite:
 * __configs/AIA.AR_segmentation.config__: Config file for the ar_segmentation.x program
 * __configs/AIA.CH_segmentation.config__: Config file for the ch_segmentation.x program
 * __scripts/AIA.get_STAFF_stats.config__: Config file for the get_STAFF_stats.x program

The executables of the SPoCA suite can be compiled using the following Make files:
 * __SPoCA/ar_segmentation.mk__: To compile SPoCA/bin/ar_segmentation.x
 * __SPoCA/ch_segmentation.mk__: To compile SPoCA/bin/ch_segmentation.x
 * __SPoCA/get_STAFF_stats.mk__: To compile SPoCA/bin/get_STAFF_stats.x

The source code of the SPoCA suite can be found at https://github.com/bmampaey/SPoCA, the version used is commit 902f3f7
