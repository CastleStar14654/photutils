# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module defines background classes to estimate a scalar background
and background rms from an array (which may be masked) of any dimension.
These classes were designed as part of an object-oriented interface for
the tools in the PSF subpackage.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from distutils.version import LooseVersion
import abc
import numpy as np
import warnings
from astropy.extern import six
from astropy.utils.misc import InheritDocstrings
from astropy.utils.exceptions import AstropyUserWarning
from astropy.stats import sigma_clip, mad_std
from ..extern.biweight_stats import biweight_location, biweight_midvariance

import astropy
if LooseVersion(astropy.__version__) < LooseVersion('1.1'):
    ASTROPY_LT_1P1 = True
else:
    ASTROPY_LT_1P1 = False


__all__ = ['SigmaClip', 'BackgroundBase', 'BackgroundRMSBase',
           'MeanBackground', 'MedianBackground', 'ModeEstimatorBackground',
           'MMMBackground', 'SExtractorBackground',
           'BiweightLocationBackground', 'StdBackgroundRMS',
           'MADStdBackgroundRMS', 'BiweightMidvarianceBackgroundRMS']


class _ABCMetaAndInheritDocstrings(InheritDocstrings, abc.ABCMeta):
    pass


class SigmaClip(object):
    """
    Mixin class to perform sigma clipping for Background and Background
    RMS classes.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.
    """

    def __init__(self, sigclip=True, sigma=3, sigma_lower=None,
                 sigma_upper=None, iters=5):

        self.sigclip = sigclip
        self.sigma = sigma
        self.sigma_lower = sigma_lower
        self.sigma_upper = sigma_upper
        self.iters = iters

    def sigma_clip(self, data, axis=None):
        if not self.sigclip:
            return data

        if ASTROPY_LT_1P1:
            warnings.warn('sigma_lower and sigma_upper will be ignored '
                          'because they are not supported astropy < 1.1',
                          AstropyUserWarning)
            return sigma_clip(data, sig=self.sigma, axis=axis,
                              iters=self.iters, cenfunc=np.ma.median,
                              varfunc=np.ma.var)
        else:
            return sigma_clip(data, sigma=self.sigma,
                              sigma_lower=self.sigma_lower,
                              sigma_upper=self.sigma_upper, axis=axis,
                              iters=self.iters, cenfunc=np.ma.median,
                              stdfunc=np.std)


@six.add_metaclass(_ABCMetaAndInheritDocstrings)
class BackgroundBase(object):
    """
    Base class for classes that estimate scalar background values.
    """

    def __call__(self, data, axis=None):
        return self.calc_background(data, axis=axis)

    @abc.abstractmethod
    def calc_background(self, data, axis=None):
        """
        Calculate the background value.

        Parameters
        ----------
        data : array_like or `~numpy.ma.MaskedArray`
            The array for which to calculate the background value.
        axis : int or `None`, optional
            The array axis along which the background is calculated.  If
            `None`, then the entire array is used.

        Returns
        -------
        result : float
            The calculated background value.
        """


@six.add_metaclass(_ABCMetaAndInheritDocstrings)
class BackgroundRMSBase(object):
    """
    Base class for classes that estimate scalar background rms values.
    """

    def __call__(self, data, axis=None):
        return self.calc_background_rms(data, axis=axis)

    @abc.abstractmethod
    def calc_background_rms(self, data, axis=None):
        """
        Calculate the background rms value.

        Parameters
        ----------
        data : array_like or `~numpy.ma.MaskedArray`
            The array for which to calculate the background rms value.
        axis : int or `None`, optional
            The array axis along which the background rms is calculated.
            If `None`, then the entire array is used.

        Returns
        -------
        result : float
            The calculated background rms value.
        """


class MeanBackground(BackgroundBase, SigmaClip):
    """
    Class to calculate the background in an array as the (sigma-clipped)
    mean.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import MeanBackground
    >>> data = np.arange(100)
    >>> bkg = MeanBackground(sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def calc_background(self, data, axis=None):

        return np.ma.mean(self.sigma_clip(data, axis=axis), axis=axis)


class MedianBackground(BackgroundBase, SigmaClip):
    """
    Class to calculate the background in an array as the (sigma-clipped)
    median.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import MedianBackground
    >>> data = np.arange(100)
    >>> bkg = MedianBackground(sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def calc_background(self, data, axis=None):

        return np.ma.median(self.sigma_clip(data, axis=axis), axis=axis)


class ModeEstimatorBackground(BackgroundBase, SigmaClip):
    """
    Class to calculate the background in an array using a mode estimator
    of the form ``(median_factor * median) - (mean_factor * mean)``.

    Parameters
    ----------
    median_factor : float, optional
        The multiplicative factor for the data median.  Defaults to 3.
    mean_factor : float, optional
        The multiplicative factor for the data mean.  Defaults to 2.
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import ModeEstimatorBackground
    >>> data = np.arange(100)
    >>> bkg = ModeEstimatorBackground(median_factor=3., mean_factor=2.,
    ...                               sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def __init__(self, median_factor=3., mean_factor=2., **kwargs):

        super(ModeEstimatorBackground, self).__init__(**kwargs)
        self.median_factor = median_factor
        self.mean_factor = mean_factor

    def calc_background(self, data, axis=None):

        data = self.sigma_clip(data, axis=axis)
        return ((self.median_factor * np.ma.median(data, axis=axis)) -
                (self.mean_factor * np.ma.mean(data, axis=axis)))


class MMMBackground(ModeEstimatorBackground, SigmaClip):
    """
    Class to calculate the background in an array using the DAOPHOT MMM
    algorithm.

    The background is calculated using a mode estimator of the form
    ``(3 * median) - (2 * mean)``.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import MMMBackground
    >>> data = np.arange(100)
    >>> bkg = MMMBackground(sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def __init__(self, **kwargs):

        kwargs['median_factor'] = 3.
        kwargs['mean_factor'] = 2.
        super(MMMBackground, self).__init__(**kwargs)


class SExtractorBackground(BackgroundBase, SigmaClip):
    """
    Class to calculate the background in an array using the
    SExtractor algorithm.

    The background is calculated using a mode estimator of the form
    ``(2.5 * median) - (1.5 * mean)``.

    If ``(mean - median) / std > 0.3`` then the median is used instead.
    Despite what the `SExtractor`_ User's Manual says, this is the
    method it *always* uses.

    .. _SExtractor: http://www.astromatic.net/software/sextractor

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import SExtractorBackground
    >>> data = np.arange(100)
    >>> bkg = SExtractorBackground(sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def calc_background(self, data, axis=None):

        data = self.sigma_clip(data, axis=axis)

        # Use .item() to make the median a scalar for numpy 1.10.
        # Even when fixed in numpy, this needs to remain for
        # compatibility with numpy 1.10 (until no longer supported).
        # https://github.com/numpy/numpy/pull/7635
        _median = np.ma.median(data, axis=axis).item()
        _mean = np.ma.mean(data, axis=axis)
        _std = np.ma.std(data, axis=axis)

        if _std == 0:
            return _mean

        if (np.abs(_mean - _median) / _std) < 0.3:
            return (2.5 * _median) - (1.5 * _mean)
        else:
            return _median


class BiweightLocationBackground(BackgroundBase, SigmaClip):
    """
    Class to calculate the background in an array using the biweight
    location.

    Parameters
    ----------
    c : float, optional
        Tuning constant for the biweight estimator.  Default value is
        6.0.
    M : float, optional
        Initial guess for the biweight location.  Default value is
        `None`.
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import BiweightLocationBackground
    >>> data = np.arange(100)
    >>> bkg = BiweightLocationBackground(sigma=3.)

    The background value can be calculated by using the
    ``.calc_background()`` method, e.g.:

    >>> bkg_value = bkg.calc_background(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5

    Alternatively, the background value can be calculated by calling the
    class instance as a function, e.g.:

    >>> bkg_value = bkg(data)
    >>> print(bkg_value)    # doctest: +FLOAT_CMP
    49.5
    """

    def __init__(self, c=6, M=None, **kwargs):

        super(BiweightLocationBackground, self).__init__(**kwargs)
        self.c = c
        self.M = M

    def calc_background(self, data, axis=None):

        return biweight_location(self.sigma_clip(data, axis=axis), c=self.c,
                                 M=self.M, axis=axis)


class StdBackgroundRMS(BackgroundRMSBase, SigmaClip):
    """
    Class to calculate the background rms in an array as the
    (sigma-clipped) standard deviation.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import StdBackgroundRMS
    >>> data = np.arange(100)
    >>> bkgrms = StdBackgroundRMS(sigma=3.)

    The background rms value can be calculated by using the
    ``.calc_background_rms()`` method, e.g.:

    >>> bkgrms_value = bkgrms.calc_background_rms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    28.866070047722118

    Alternatively, the background rms value can be calculated by calling
    the class instance as a function, e.g.:

    >>> bkgrms_value = bkgrms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    28.866070047722118
    """

    def calc_background_rms(self, data, axis=None):

        return np.ma.std(self.sigma_clip(data, axis=axis), axis=axis)


class MADStdBackgroundRMS(BackgroundRMSBase, SigmaClip):
    """
    Class to calculate the background rms in an array as using the
    `median absolute deviation (MAD)
    <http://en.wikipedia.org/wiki/Median_absolute_deviation>`_.

    The standard deviation estimator is given by:

    .. math::

        \\sigma \\approx \\frac{{\\textrm{{MAD}}}}{{\Phi^{{-1}}(3/4)}}
            \\approx 1.4826 \ \\textrm{{MAD}}

    where :math:`\Phi^{{-1}}(P)` is the normal inverse cumulative
    distribution function evaluated at probability :math:`P = 3/4`.

    Parameters
    ----------
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import MADStdBackgroundRMS
    >>> data = np.arange(100)
    >>> bkgrms = MADStdBackgroundRMS(sigma=3.)

    The background rms value can be calculated by using the
    ``.calc_background_rms()`` method, e.g.:

    >>> bkgrms_value = bkgrms.calc_background_rms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    37.065055462640053

    Alternatively, the background rms value can be calculated by calling
    the class instance as a function, e.g.:

    >>> bkgrms_value = bkgrms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    37.065055462640053
    """

    def calc_background_rms(self, data, axis=None):

        return mad_std(self.sigma_clip(data, axis=axis), axis=axis)


class BiweightMidvarianceBackgroundRMS(BackgroundRMSBase, SigmaClip):
    """
    Class to calculate the background rms in an array as the
    (sigma-clipped) biweight midvariance.

    Parameters
    ----------
    c : float, optional
        Tuning constant for the biweight estimator.  Default value is
        9.0.
    M : float, optional
        Initial guess for the biweight location.  Default value is
        `None`.
    sigma : float, optional
        The number of standard deviations to use for both the lower and
        upper clipping limit. These limits are overridden by
        ``sigma_lower`` and ``sigma_upper``, if input. Defaults to 3.
    sigma_lower : float or `None`, optional
        The number of standard deviations to use as the lower bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    sigma_upper : float or `None`, optional
        The number of standard deviations to use as the upper bound for
        the clipping limit. If `None` then the value of ``sigma`` is
        used. Defaults to `None`.
    iters : int or `None`, optional
        The number of iterations to perform sigma clipping, or `None` to
        clip until convergence is achieved (i.e., continue until the
        last iteration clips nothing). Defaults to 5.

    Examples
    --------
    >>> from photutils import BiweightMidvarianceBackgroundRMS
    >>> data = np.arange(100)
    >>> bkgrms = BiweightMidvarianceBackgroundRMS(sigma=3.)

    The background rms value can be calculated by using the
    ``.calc_background_rms()`` method, e.g.:

    >>> bkgrms_value = bkgrms.calc_background_rms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    30.094338485893392

    Alternatively, the background rms value can be calculated by calling
    the class instance as a function, e.g.:

    >>> bkgrms_value = bkgrms(data)
    >>> print(bkgrms_value)    # doctest: +FLOAT_CMP
    30.094338485893392
    """

    def __init__(self, c=9.0, M=None, **kwargs):

        super(BiweightMidvarianceBackgroundRMS, self).__init__(**kwargs)
        self.c = c
        self.M = M

    def calc_background_rms(self, data, axis=None):

        return biweight_midvariance(self.sigma_clip(data, axis=axis),
                                    c=self.c, M=self.M, axis=axis)
