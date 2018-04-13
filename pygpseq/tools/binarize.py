# -*- coding: utf-8 -*-

'''
@author: Gabriele Girelli
@contact: gigi.ga90@gmail.com
@description: image binarization library.
'''

# DEPENDENCIES =================================================================

import math

import numpy as np
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu
from skimage.measure import label

from pygpseq import const

from pygpseq.tools import image as imt
from pygpseq.tools import io as iot
from pygpseq.tools import stat as stt
from pygpseq.tools import vector as vt

# CLASSES ======================================================================

class Binarize(iot.IOinterface):
    """Image binarization class.

    If the class has public attributes, they may be documented here
    in an ``Attributes`` section and follow the same formatting as a
    function's ``Args`` section. Alternatively, attributes may be documented
    inline with the attribute's declaration (see __init__ method below).

    Attributes:
      an_type (int): analysis type accordin to `pygpseq.const`.
      seg_type (int): segmentation type accordin to `pygpseq.const`.
      do_global_thr (bool): True to apply global threshol (Otsu).
      do_adaptive_thr (bool): True to apply local (adaptive) threshold.
      adp_neigh (int): neighbourhood square side for local thr.
      do_clear_borders (bool): True to remove objects touching the borders.
      do_clear_Z_borders (bool): True to remove objects touching Z borders.
      do_fill_holes (bool): True to fill holes (both 2D and 3D).
      radius_interval (tuple[float]): object radius interval.
      min_z_size (float): minimum Z (relative) size of the objects.
    """

    an_type = 0
    seg_type = 0
    do_global_thr = True
    do_adaptive_thr = True
    adp_neigh = 101
    do_clear_borders = True
    do_clear_Z_borders = False
    do_fill_holes = True
    radius_interval = (10., float('inf'))
    min_z_size = .25

    def __init__(self, **kwargs):
        """Initialize binarization settings all at once with kwargs.

        Args:
          **kwargs: arbitrary keyword arguments stored in the class.
        """
        super(Binarize, self).__init__()

        # Store provided kwargs in the current instance.
        excluded = ['logpath']
        for k in kwargs.keys():
            if not k == excluded: self[k] = kwargs[k]

    def __getitem__(self, key):
        """ Allow get item. """
        if key in dir(self): return(getattr(self, key))
        else: return(None)

    def __setattr__(self, name, value):
        """ Check the attribute and set it. """
        Binarize.check_attr(name, value)
        return(super(Binarize, self).__setattr__(name, value))

    def __setitem__(self, key, value):
        """ Allow set item. """
        if key in dir(self):
            self.__setattr__(key, value)
    
    def check_attr(name, value):
        """Run attribute assertions.

        Args:
          name (string): attribute name
          value: attribute value

        Returns:
          None: no assert error is triggered if the attribute checks out.
        """

        if name in ['do_global_thr', 'do_adaptive_thr', 'do_clear_borders',
            'do_clear_Z_borders', 'do_fill_holes']:
            # Require boolean
            assert_msg = 'boolean expected, got "%s".' % type(value)
            assert type(True) == type(value), assert_msg

        elif name == 'adp_neigh':
            # Require int
            assert_msg = 'int expected, got "%s".' % type(value)
            assert type(True) == type(value), assert_msg

        elif 'an_type' == name:
            # Check that it is one of the allowed constants
            an_types = [const.AN_SUM_PROJ, const.AN_MAX_PROJ,
                const.AN_3D, const.AN_MID]
            assert value in an_types, "got '%s', expected one of %s." % (
                str(value), str(an_types))

        elif 'seg_type' == name:
            # Check that it is one of the allowed constants
            seg_types = [const.SEG_SUM_PROJ, const.SEG_MAX_PROJ, const.SEG_3D]
            assert value in seg_types, "got '%s', expected one of %s." % (
                str(value), str(seg_types))
    
    def filter_obj_XY_size(self, mask):
        """Filter objects XY size.
        Uses self.radius_interval to filter the objects in the provided mask
        based on the selected segmentation type.

        Args:
          mask (np.array): binary image

        Returns:
          tuple: filtered binary image and log string
        """

        # Start logging
        log = ''
        log += self.printout('Filtering objects XY size...', 2)

        # From radius to size
        sinter = stt.r_to_size(self.radius_interval, self.seg_type)
        log += self.printout('Allowed size interval: [%.2f, %.2f] [%s]' % (
            sinter[0], sinter[1], imt.get_unit(mask.shape)), 3)

        # Identify objects XY size
        log += self.printout('Retrieving objects XY size...', 3)
        L = label(mask)
        xysizes = imt.get_objects_xysize(L)
        log += self.printout('Found %d objects.' % L.max(), 4)
        
        # Select objects to be discarded
        torm = np.logical_or(xysizes < sinter[0], xysizes > sinter[1])
        torm = [ii for ii, x in enumerate(torm) if x]
        log += self.printout('Discarding %d objects.' % len(torm), 3)

        # Remove objects outside of size interval
        mask = vt.rm_from_mask(L, torm)

        # Output
        return((mask, log))

    def filter_obj_Z_size(self, mask):
        """Filter objects Z size.
        Uses self.min_z_size to filter the objects in the provided mask.

        Args:
          mask (np.array): binary image

        Returns:
          tuple: filtered binary image and log string
        """

        # Start logging
        log = ''
        log += self.printout('Filtering objects Z size...', 2)

        # If not a stack, return the mask
        if 3 > len(mask.shape): return((mask, log))

        # Check provided conditions
        doFilterZsize = 0 != int(math.ceil(self.min_z_size))
        doFilterZsize = doFilterZsize and self.an_type == const.AN_3D
        if not doFilterZsize: return((mask, log))

        # From size to number of slices
        if self.min_z_size > 1:
            self.min_z_size = int(math.ceil(self.min_z_size))
        else:
            self.min_z_size = self.min_z_size * mask.shape[0]
            self.min_z_size = int(math.ceil(self.min_z_size))
        log += self.printout('Minimum %d slices.' % self.min_z_size, 3)

        # Identify objects Z size
        log += self.printout('Retrieving objects Z size...', 3)
        L = label(mask)
        log += self.printout('Found %d objects.' % L.max(), 4)
        
        # Select objects to be discarded
        torm = np.array(imt.get_objects_zsize(L)) < self.min_z_size
        torm = [ii for ii, x in enumerate(torm) if x]
        log += self.printout('Discarding %d objects.' % len(torm), 3)

        # Remove objects lower than minimum size
        mask = vt.rm_from_mask(L, torm)

        # Output
        return((mask, log))

    def run(self, im):
        """Binarize image with current instance settings.
        Perform, if requested, the following actions in this order:
        - Make Z projection
        - Apply global/local thresholds (and combine them)
        - Clear XY/Z borders
        Fill holes

        Args:
          im (np.array): image to be thresholded

        Returns:
          tuple: binarized image, Otsu's threshold value and log string
        """

        log = ''

        # If no threshold is requested, return the image
        if not self.do_global_thr and not self.do_adaptive_thr:
            log += self.printout('No threshold applied.', -1)
            return((im, log))

        # Make Z-projection ----------------------------------------------------
        if const.SEG_3D != self.seg_type and 2 != len(im.shape):
            log += self.printout('Generating Z-projection [%d]...' % (
                const.SEG_LABELS[self.seg_type],), 2)
            im = imt.mk_z_projection(im, self.seg_type)

        # Binarize images ------------------------------------------------------
        mask = []

        # Perform global threshold
        if self.do_global_thr:
            thr = threshold_otsu(im)
            log += self.printout('Thresholding image, global thr: %f' % thr, 2)
            mask.append(imt.binarize(im, thr))

        # Perform adaptive threshold
        if self.do_adaptive_thr and 1 < self.adp_neigh:
            msg = 'Applying adaptive threshold to neighbourhood: %d' % (
                self.adp_neigh,)
            log += self.printout(msg, 2)
            mask.append(imt.threshold_adaptive(im, self.adp_neigh))

        # Combine masks
        if len(mask) == 2: mask = np.logical_and(mask[0], mask[1])
        else: mask = mask[0]

        # Remove objects touching borders --------------------------------------
        if self.do_clear_borders:
            msg = 'Removing objects touching the image border...'
            log += self.printout(msg, 2)
            mask = imt.clear_borders2(label(mask), self.do_clear_Z_borders)
            mask = mask != 0
        
        # Fill holes -----------------------------------------------------------
        if self.do_fill_holes:
            log += self.printout('Filling holes...', 2)
            mask = ndi.binary_fill_holes(mask)

            # Single slice filling
            if 3 == len(mask.shape):
                for sliceid in range(mask.shape[0]):
                    slide = mask[sliceid, :, :]
                    mask[sliceid, :, :] = ndi.binary_fill_holes(slide)

        # Output ---------------------------------------------------------------
        return((mask, thr, log))

# END ==========================================================================

################################################################################
