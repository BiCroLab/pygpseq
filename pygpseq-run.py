#!/usr/bin/python
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# 
# Author: Gabriele Girelli
# Email: gigi.ga90@gmail.com
# Version: 1.0.0
# Description: script to interface with the pygpseq package.
# ------------------------------------------------------------------------------



# DEPENDENCIES =================================================================

import argparse
import numpy as np
import os
import pandas as pd
import pygpseq as gp
import sys

# PARAMETERS ===================================================================

# Add script description
parser = argparse.ArgumentParser(
	description = """Run pygpseq-based analysis."""
)

# Positional parameters
parser.add_argument('inDir', type = str, nargs = 1,
	help = """Path to input directory, containing single-condition directories
	with TIF files.""")
parser.add_argument('outDir', type = str, nargs = 1,
	help = """Path to output directory, must be different from the input
	directory.""")

# Optional parameters
parser.add_argument('--skip', type = str, nargs = '*',
	help = """Space-separated phases to be skipped.
	Use -- after the last one.""",
	choices = ['inst', 'seg', 'an', 'box', 'plot', 'report'])
parser.add_argument('-l', '--logpath', type = str, nargs = 1,
	help = """Path to log file. By default: outDir/log""", metavar = 'log')
parser.add_argument('-a', '--aspect', type = float, nargs = 3,
	help = """Physical size of Z, Y and X voxel sides.
	Default: 300.0 216.6 216.6""",
	metavar = ('Z', 'Y', 'X'), default = [300., 216.6, 216.6])
parser.add_argument('-d', '--dna-channels', type = str, nargs = '+',
	help = """Space-separated names of DNA staining channels.
	Use -- after the last one.""",
	default = ['dapi'], metavar = 'dna_name')
parser.add_argument('-s', '--sig-channels', type = str, nargs = '+',
	help = """Space-separated names of GPSeq signal channels.
	Use -- after the last one.""",
	default = ['cy5', 'tmr'], metavar = 'sig_name')
parser.add_argument('-z', '--min-z', type = float, nargs = 1,
	help = """If lower than 1, minimum fraction of stack, if higher than 1,
	minimum number of slices to be occupied by a nucleus""",
	default = [.25], metavar = 'min_z')
parser.add_argument('--seg-type', type = str, nargs = 1,
	help = """Segmentation type. Default: 3d""",
	choices = ['sum_proj', 'max_proj', '3d'], default = ['3d'])
parser.add_argument('--an-type', type = str, nargs = 1,
	help = """Analysis type. Default: mid""",
	choices = ['sum_proj', 'max_proj', '3d', 'mid'],
	default = ['mid'])
parser.add_argument('--mid-type', type = str, nargs = 1,
	help = """Method for mid-section selection.""",
	choices = ['central', 'largest', 'maxIsum'],
	default = ['largest'])
parser.add_argument('--nuclear-sel', type = str, nargs = '*',
	help = """Space-separated features for nuclear selection.
	Use -- after the last one. Default: flat_size sumI""",
	choices = ['size', 'surf', 'shape', 'sumI', 'meanI', 'flat_size'],
	default = ['flat_size', 'sumI'])
parser.add_argument('--description', type = str, nargs = '*',
	help = """Space separated condition:description couples.
	'condition' are the name of condition folders.
	'description' are descriptive labels used in plots instead of folder names.
	Use -- after the last one.""")
parser.add_argument('-t', '--threads', metavar = 'ncores', type = int,
	nargs = 1, default = [1],
	help = """Number of threads to be used for parallelization. Increasing the
	number of threads might increase the required amount of RAM.""")
parser.add_argument('--note', type = str, nargs = 1,
	help = """Dataset/Analysis description. Use double quotes.""")
regexp = "^(?P<channel_name>[^/]*)\.(?P<channel_id>channel[0-9]+)"
regexp += "\.(?P<series_id>series[0-9]+)(?P<ext>(_cmle)?\.tif)$"
parser.add_argument('--regexp', type = str, nargs = 1,
	help = """Advanced. Regular expression to identify tif images.""",
	default = [regexp])

# Flag parameters
parser.add_argument('-r', '--rescale-deconvolved', action = 'store_const',
	help = """Perform rescaling of deconvolved images. Requires Huygens
	Professional v4.5 log file for an image to be rescaled.""",
	const = True, default = False)
parser.add_argument('-n', '--normalize-distance', action = 'store_const',
	help = """Perform distance normalization. Necessary to compare nuclei
	with different radius.""",
	const = True, default = False)
parser.add_argument('-u', '--DEBUG-MODE', action = 'store_const',
	help = """Debugging mode.""",
	const = True, default = False)

# Parse arguments
args = parser.parse_args()

# FUNCTION =====================================================================

def ask(q):
	"""Asks for confirmation. Aborts otherwise.

	Args:
		q (string): question.
	"""

	answer = ''
	while not answer.lower() in ['y', 'n']:
		print("%s %s" % (q, "(y/n)"))
		answer = raw_input()

		if 'n' == answer.lower():
			sys.exit("Aborted.\n")
		elif not 'y' == answer.lower():
			print("Please, answer 'y' or 'n'.\n")


# RUN ==========================================================================

# Create pyGPSeq analyzer instance
gpi = gp.Main(ncores = args.threads[0])

# Steps to be skipped
dskip = {
	'inst' : 1,
	'seg' : 2,
	'an' : 3,
	'box' : 3.5,
	'plot' : 4,
	'report' : 5
}
if not None is args.skip:
	gpi.skip = [dskip[e] for e in args.skip]

# Channel names
gpi.sig_names = tuple(args.sig_channels)
gpi.dna_names = tuple(args.dna_channels)

# Data directory
gpi.basedir = args.inDir[0]

# Output directory
gpi.outdir = args.outDir[0]

# Segmentation type for nuclear identification
dseg = {
	'sum_proj' : 0,
	'max_proj' : 1,
	'3d' : 2
}
gpi.seg_type = dseg[args.seg_type[0]]

# Single-nucleus analysis type
dan = {
	'sum_proj' : 0,
	'max_proj' : 1,
	'3d' : 2,
	'mid' : 3
}
gpi.an_type = dan[args.an_type[0]]

# Middle-section selection method
dmid = {
'central' : 0,
'largest' : 1,
'maxIsum' : 2
}
gpi.mid_type = dmid[args.mid_type[0]]

# Voxel aspect proportions (or sizes, ZYX)
gpi.aspect = tuple(args.aspect)

# Minimum percentage of stack to be occupied by a cell
gpi.min_z_size = args.min_z[0]

# Nuclear selection
dnsel = {
	'size' : 0,
	'surf' : 1,
	'shape' : 2,
	'sumI' : 3,
	'meanI' : 4,
	'flat_size' : 5
}
gpi.nsf = tuple([dnsel[e] for e in args.nuclear_sel])

# Regular expression to identify image files
gpi.reg = args.regexp[0]

# Where to save the run log
if None is args.logpath:
	gpi.logpath = args.outDir[0] + '/' + gpi.gen_log_name()
else:
	gpi.logpath = args.logpath[0]

# Perform deconvolved image rescaling?
gpi.rescale_deconvolved = args.rescale_deconvolved

# Normalize distance?
gpi.normalize_distance = args.normalize_distance

# Better condition naming
if not None is args.description:
	for descr in args.description:
		c, d = descr.split(':')
		gpi.cdescr[c] = d
readable_cdescr = [str(k) + ' => ' + str(v) for (k,v) in gpi.cdescr.items()]
if 0 == len(readable_cdescr):
	readable_cdescr = ["*NONE*"]

# Notes
if not None is args.note:
	gpi.notes = args.note[0]

# Debugging mode
gpi.debugging = args.DEBUG_MODE

# Show current settings
os.system('clear')
print("""
---------- SETTING:  VALUE ----------

   Input directory:  """+gpi.basedir+"""
  Output directory:  """+gpi.outdir+"""
          Log file:  """+gpi.logpath+"""
  
     Skipped steps:  """+str(args.skip)+"""
  
      DNA channels:  """+str(gpi.dna_names)+"""
   Signal channels:  """+str(gpi.sig_names)+"""

      Segmentation:  """+args.seg_type[0]+"""
          Analysis:  """+args.an_type[0]+"""
    Middle section:  """+args.mid_type[0]+"""

Voxel aspect (ZYX):  """+str(gpi.aspect)+"""
 Minimum Z portion:  """+str(gpi.min_z_size)+"""

  Condition descr.:  """+"\n                     ".join(readable_cdescr)+"""

           Threads:  """+str(gpi.ncores)+"""
              Note:  """+gpi.notes+"""

            Regexp: """+gpi.reg+"""

   Rescale deconv.:  """+str(gpi.rescale_deconvolved)+"""
   Normalize dist.:  """+str(gpi.normalize_distance)+"""
         Debug mod:  """+str(gpi.debugging)+"""

""")

# Ask for confirmation
ask('Confirm settings and proceed.')
sys.exit()
# Start the analysis
gpi = gpi.run()

# End --------------------------------------------------------------------------

################################################################################
