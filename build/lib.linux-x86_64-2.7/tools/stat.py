# -*- coding: utf-8 -*-

""" Functions for the management of statistical operations """

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .. import const
from . import vector as vt

def get_fwhm(xs, ys):
	""" Calculate FWHM of highest peak in the distribution. """

	# CHECK PARAMS =============================================================

	# Must have the same length
	if len(xs) != len(ys):
		return(None)

	if 1 == len(ys):
		return([xs[0] - 1, xs[0] + 1])

	# GET FWHM =================================================================

	# Identify highest peak
	xmaxi = ys.tolist().index(max(ys))

	# Get FWHM range [left] ----------------------------------------------------
	
	# Get absolute difference to HM value
	x1 = abs(ys[range(xmaxi)] - max(ys) / 2)

	# Get threshold based on average distance of consecutive points
	thr = np.max(abs(np.diff(x1)))
	# Select values close to the HM (based on threshold and absolut difference)
	selected = [i for i in range(len(x1)) if x1[i] <= thr]

	# Select left boundary
	if 0 == len(selected):
		x1 = xs[range(xmaxi)][x1.tolist().index(min(x1))]
	else:
		x1 = xs[range(xmaxi)][max(selected)]

	# Get FWHM range [right] ---------------------------------------------------

	# Get absolute difference to HM value
	x2 = abs(ys[range(xmaxi + 1, len(ys))] - max(ys) / 2)

	# Get threshold based on average distance of consecutive points
	thr = np.max(abs(np.diff(x2)))

	# Select values close to the HM (based on threshold and absolut difference)
	selected = [i for i in range(len(x2)) if x2[i] <= thr]

	# Select right boundary
	if 0 == len(selected):
		x2 = xs[range(xmaxi + 1, len(xs))][x2.tolist().index(min(x2))]
	else:
		x2 = xs[range(xmaxi + 1, len(xs))][min(selected)]

	# Output
	return([x1, x2])

def calc_density(data, **kwargs):
	"""
	Calculate the Gaussian KDE of the provided data series.
	
	@param:
	 - sigma <float> standard deviation used for covariance calculation (opt)
	 - nbins <int> #steps for the density curve calculation (opt, def: 1000)
	"""

	# Default values
	if not 'sigma' in kwargs.keys():
		sigma = .2
	else:
		sigma = kwargs['sigma']

	if not 'nbins' in kwargs.keys():
		nbins = 1000
	else:
		nbins = kwargs['nbins']

	# If only one nucleus was found
	if 1 == len(data):
		f = eval('lambda x: 1 if x == ' + str(data[0]) + ' else 0')
		f = np.vectorize(f)
		return({
			'x' : np.array([data[0]]),
			'y' : np.array([1]),
			'f' : f
		})

	# Prepare density function
	density = stats.gaussian_kde(data)

	# Re-compute covariance
	density.covariance_factor = lambda : sigma
	density._compute_covariance()

	# Output
	out = {}
	out['x'] = np.linspace(min(data), max(data), nbins)
	out['f'] = density
	out['y'] = density(out['x'])
	return(out)

def smooth_sparse_gaussian(x, y, nbins = None, sigma = None,
	rescale_sigma = None, **kwargs):
	"""
	Produce a smooth approximation of sparse data.
	Basically a smoothened binned distribution.

	@param:
	 - x <numeric> x coordinates
	 - y <numeric> y coordinates
	 - nbins <int> curve precision (opt, def: 200)
	 - sigma <float> smoothing factor (opt, def: 0.01)
	 - rescale_sigma <boole> whether to multiply sigma to max(x)
	"""

	if None == nbins:
		nbins = 200
	if None == sigma:
		sigma = .01
	if None == rescale_sigma:
		rescale_sigma = True

	if rescale_sigma:
		sigma *= max(x)

	# Bin data
	data = binned_profile(x, y, nbins)

	# Prepare output
	out = {
		'x' : data['breaks'].tolist(),
		'n' : data['n'].tolist()
	}

	# Smoothen profiles
	for field in ['mean', 'median', 'mode', 'std']:
		out[field + '_raw'] = data[field]
		out[field] = smooth_gaussian(data['breaks'],
			data[field], sigma, nbins)

	# Output
	return(out)

def binned_profile(x, y, nbins = None):
	"""
	Produce an approximation of sparse data by binning it.

	@param:
	 - x <numeric> x coordinates
	 - y <numeric> y coordinates
	 - nbins <int> curve precision (opt, def: 200)
	"""

	if None == nbins:
		nbins = 200

	# Check format
	y = np.array(y)

	# Bin breaks
	breaks = np.linspace(0, max(x), nbins)

	# Assign data to the bins
	assigned_bins = np.digitize(x, breaks)

	# Get mean and median for every bin
	data = np.zeros((len(breaks),),
		dtype = [('breaks', 'f'), ('mean', 'f'), ('median', 'f'), ('std', 'f'),
		('mode', 'f'), ('mean_raw', 'f'), ('median_raw', 'f'), ('std_raw', 'f'),
		('mode_raw', 'f'), ('n', 'f')])
	for bin_id in range(assigned_bins.max()):
		where = np.where(assigned_bins == bin_id)
		data['breaks'][bin_id] = breaks[bin_id]
		if 0 != where[0].shape[0]:
			data['mean'][bin_id] = np.mean(y[where])
			data['median'][bin_id] = np.median(y[where])
			data['mode'][bin_id] = binned_mode(y[where], nbins)
			data['std'][bin_id] = np.std(y[where])
			data['n'][bin_id] = len(y[where])
		else:
			data['mean'][bin_id] = np.nan
			data['median'][bin_id] = np.nan
			data['mode'][bin_id] = np.nan
			data['std'][bin_id] = np.nan
			data['n'][bin_id] = 0

	return(data)

def binned_mode(x, nbins):
	""" Returns the most occupied bin in the provided dataset. """

	if 0 == len(x):
		return(np.nan)

	# Bin breaks
	breaks = np.linspace(0, max(x), nbins)

	# Assign data to the bins
	assigned_bins = np.digitize(x, breaks)

	# Count bins occurrences
	occ = vt.uniquec(assigned_bins)
	counts = np.array([e[1] for e in occ])

	# Order counts
	ordered = np.argsort(counts).tolist()
	ordered.reverse()
	occ = [occ[i] for i in ordered]

	# Return mode
	return(breaks[occ[0][0] - 1])

def smooth_gaussian(x, y, sigma = None, nbins = None):
	"""
	Smoothen a curve.

	@param:
	 - x <numeric> x coordinates
	 - y <numeric> y coordinates
	 - nbins <int> curve precision (opt, def: 500)
	 - sigma <float> smoothing factor (opt, def: 0.01)
	"""

	if None == nbins:
		nbins = 500
	if None == sigma:
		sigma = .01

	# Evenly sampled domain
	xs = np.linspace(0, max(x), nbins)

	# Weighted moving average
	ynum = np.zeros(len(xs))
	ysum = np.zeros(len(xs))

	for i in [i for i in range(len(x)) if not np.isnan(y[i])]:
		norm = get_norm_pdf(x[i], sigma, xs)
		ynum += norm
		ysum += norm * y[i]

	return(ysum / ynum)

def get_norm_pdf(mu, sigma, x):
	return(1 / np.sqrt(2 * sigma**2 * np.pi) *
		np.exp(-(x - mu)**2 / (2 * sigma**2)))

def get_outliers(x, non = None, fig = None, close = None):
	"""
	Identifies the outliers in a data set.

	@param:
	 - x <np.array> data set
	 - non <boolean> whether to return outliers or non-outliers
	 - fig <plt.figure> for boxplot purposes
	 - close <boolean> whether to close the figure before return

	@return:
	 List of (non-)outlier indexes
	"""

	if None == non:
		non = False
	if None == fig:
		fig = plt.figure()
		ax = fig.gca()
	if None == close:
		close = False

	# If no dataset is provided
	if 0 == len(x):
		return([])

	# Identify outliers through boxplot
	bp = ax.boxplot(x)

	# Close figure
	if close:
		plt.close(tmp_fig)

	# Retrieve outliers
	outliers = []
	outliers.extend(bp['fliers'][0].get_data()[0].tolist())
	outliers.extend(bp['fliers'][0].get_data()[1].tolist())

	# Unique outliers
	outliers = set(outliers)

	# Output
	if not non:
		return([i for i in range(len(x)) if x[i] in outliers])
	else:
		return([i for i in range(len(x)) if not x[i] in outliers])

def r_to_size(r_interval, size_type):
	""" Convert radius interval to size (Area/Volume) interval. """
	if const.SEG_3D == size_type:
		o_interval = (4 / float(3)) * np.pi
		o_interval *= np.power(np.array(r_interval), 3)
	else:
		o_interval = np.pi * np.square(np.array(r_interval))
	return(o_interval)

def round_unicode(n, nsig):
	"""
	Round operation on unicode number in scientific notation.

	@param:
	 - n <unicode> number in scientific notation
	 - nsig <int> number of significant digits
	"""

	# Convert unicode to string
	n = str(n.replace(u'\u2212', '-'))

	# Split on the exponent
	if 'e' in n:
		n = n.split('e')
	else:
		n = [n]

	# Round the float part
	n[0] = str(round(float(n[0]), nsig))

	# Re-join with the exponent and return
	return(unicode('e'.join(n)))

def wilcox_sets(sets):
	""" Perform Wilcoxon-Mann-Whitney U test on the provided list of sets. """

	p_vals = np.zeros((len(sets) * (len(sets) - 1) / 2,),
		dtype = [('i', 'int'), ('j', 'int'), ('p', 'float')])

	c = 0
	for i in range(len(sets)):
		for j in range(i + 1, len(sets)):
			p = stats.mannwhitneyu(sets[i], sets[j], alternative = 'two-sided')
			p_vals[c] = [i, j, p]
			c += 1

	return(p_vals)
