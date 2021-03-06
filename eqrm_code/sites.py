"""
 Title: sites.py

  Author:  Peter Row, peter.row@ga.gov.au

  Description: Create a data structure to handle site data e.g.
  latitude, longitude and other attributes.

  Version: $Revision: 1716 $
  ModifiedBy: $Author: rwilson $
  ModifiedDate: $Date: 2010-06-18 13:58:01 +1000 (Fri, 18 Jun 2010) $

  Copyright 2007 by Geoscience Australia
"""

######
# A Sites object has three attributes:
#     .latitude    a vector of latitude values, one per site
#     .longitude   a vector of longitude values, one per site
#     .attributes  a dictionary of attributes names, each keying to
#                  a vector of attribute values
#
# Each vector is the same length as all the others and site 'i' values
# are latitude[i], longitude[i], attribute1[i], attribute2[i], ...
######


import copy
import os
from scipy import array, asarray
#import numpy as np
import scipy as np

from eqrm_code.distances import Distances
from eqrm_code.distance_functions import As_The_Cockey_Flies
from eqrm_code.csv_interface import csv_to_arrays
from eqrm_code.projections import azimuthal_orthographic as projection
from eqrm_code import file_store

from eqrm_code.ANUGA_utilities import log


class Sites(file_store.File_Store):

    """An object to hold site data."""

    def __init__(self, latitude, longitude, **attributes):
        """Create a Sites object to handle multiple site data.

        latitude    latitude of sites (vector)
        longitude   longitude of sites (vector)
        attributes  dictionary of site attributes (vectors of data)
        """
        super(Sites, self).__init__('sites')

        self.latitude = asarray(latitude)
        self.longitude = asarray(longitude)
        self.attributes = attributes
        self.vulnerability_set = None

        assert(len(self.latitude) == len(self.longitude))
        for key in self.attributes:
            assert(len(self.latitude) == len(self.attributes[key]))

    def __del__(self):
        super(Sites, self).__del__()

    # PROPERTIES #
    # Define getters and setters for each attribute to exercise the
    # file-based data structure
    latitude = property(lambda self: self._get_file_array('latitude'),
                        lambda self, value: self._set_file_array('latitude', value))

    longitude = property(lambda self: self._get_file_array('longitude'),
                         lambda self, value: self._set_file_array('longitude', value))
    # END PROPERTIES #

    def save(self, dir=None):
        """
        Save the ndarray objects to the specified directory
        """
        self._save(dir)

    @classmethod
    def load(cls, load_dir):
        """
        Return an Sites object from the .npy files stored in the specified
        directory.
        Note: Attributes are not set by this method.
        """
        # An empty sites object
        sites = cls(latitude=[], longitude=[])
        # Set lat/lon vectors by load_dir
        sites._load(load_dir)
        return sites

    @classmethod
    def from_csv(cls, file, **attribute_conversions):
        """Construct Site instance from csv file.

        file                   open file handle for site data
        attribute_conversions  dictionary defining required data from file and
                               format of the data
        use:
            X = Sites.from_csv('blg_wr.csv', PEOPLE=float,
                               WALLS=str, ROOF_TYPE=str)
        or:
            d = {'PEOPLE': float, 'WALLS': str, 'ROOF_TYPE': str}
            X = Sites.from_csv('blg_wr.csv', **d)
        """

        # force lat & lon - required attributes
        attribute_conversions["LATITUDE"] = float
        attribute_conversions["LONGITUDE"] = float

        # remove VS30 if exists - we'll deal with this later
        if attribute_conversions.get('VS30') is not None:
            attribute_conversions.pop('VS30')

        # read in data from file
        sites_dict = csv_to_arrays(file, **attribute_conversions)

        # remove lat&lon from attributes dictionary
        latitude = sites_dict.pop("LATITUDE")
        longitude = sites_dict.pop("LONGITUDE")

        # copy remaining attributes - don't need user changes reflected
        attributes = copy.copy(sites_dict)

        # now lets do VS30
        try:
            attribute_conversions['VS30'] = float
            sites_dict = csv_to_arrays(file, **attribute_conversions)
            attributes['Vs30'] = sites_dict['VS30']
        except:
            # If not present in the file, analysis will add the mapping based
            # on site class
            pass

        # call class constructor
        return cls(latitude, longitude, **attributes)

    def __len__(self):
        """Make len() return number of sites."""

        return int(self.latitude.shape[0])

    def __getitem__(self, key):
        """Allow indexing/slicing of Sites object - return new Sites object."""

        if isinstance(key, int):
            key = [key]
        attributes = {}
        for k in self.attributes.keys():
            attributes[k] = self.attributes[k][key]

        sites = Sites(self.latitude[key], self.longitude[key], **attributes)

        if self.vulnerability_set is not None:
            sites.vulnerability_set = self.vulnerability_set

        return sites

    def __repr__(self):
        return ('Sites:\n'
                'number of sites:%r\n'
                '            lat:%r\n'
                '           long:%r\n'
                '     attributes:%r\n'
                % (len(self), self.latitude, self.longitude, self.attributes))

    def __str__(self):
        return ('Sites:\n'
                'number of sites:%s\n'
                '            lat:%s\n'
                '           long:%s\n'
                % (len(self), self.latitude, self.longitude))

    def set_Vs30(self, site_class2Vs30):
        """Given a mapping from site_class to Vs30, calculate the Vs30 values
        for all of the sites.

        site_class2Vs30    dictionary of 'site_class' and 'Vs30' keys
        """
        # Calculate a Vs30 value
        Vs30_list = []
        for site_class in self.attributes['SITE_CLASS']:
            try:
                Vs30_list.append(site_class2Vs30[site_class])
            except KeyError:
                # FIXME The site class 2 Vs30 mapping does not cover all
                # site classes.
                raise KeyError
        self.attributes['Vs30'] = array(Vs30_list)

    def validate_vulnerability_set(self):
        msg = 'validate_vulnerability_set is not supported for this site object'
        raise RuntimeError(msg)

    # FIXME consider moving to event set
    def distances_from_event_set(self, event_set, event_set_trace_starts=True):
        """
        The distance from self.sites to event_set.centroids.
        A big array-like object.
        """

        if event_set_trace_starts:
            return Distances(self.latitude,
                             self.longitude,
                             event_set.rupture_centroid_lat,
                             event_set.rupture_centroid_lon,
                             event_set.length,
                             event_set.azimuth,
                             event_set.width,
                             event_set.dip,
                             event_set.depth,
                             event_set.depth_to_top,
                             projection,
                             trace_start_lat=event_set.trace_start_lat,
                             trace_start_lon=event_set.trace_start_lon,
                             rupture_centroid_x=event_set.rupture_centroid_x,
                             rupture_centroid_y=event_set.rupture_centroid_y)
        else:
            return Distances(self.latitude,
                             self.longitude,
                             event_set.rupture_centroids_lat,
                             event_set.rupture_centroids_lon,
                             event_set.lengths,
                             event_set.azimuths,
                             event_set.widths,
                             event_set.dips,
                             event_set.depths,
                             event_set.depths_to_top,
                             projection)

    def closest_site(self, lat, lon):
        """Return the index of the closest site to the given lat and lon"""
        distances = As_The_Cockey_Flies(
            lat,
            lon,
            self.latitude,
            self.longitude)
        return distances.argmin()


def load_sites(parallel, load_dir):
    """
    Load the site object from file in load_dir
    """
    log.info('P%s: Loading site from %s' % (parallel.rank, load_dir))

    sites = Sites.load(load_dir)

    return sites


def truncate_sites_for_test(use_site_indexes, sites, site_indexes):
    """Sample sites (for testing).

    use_site_indexes  id True, do sampling, else return unchanged sites
    sites             is a Sites object
    site_indexes      is an array of indexes

    If 'use_site_indexes' is False, just return 'sites' unchanged.
    """

    if use_site_indexes is True:
        return sites[site_indexes - 1]  # -1 offset to match matlab

    return sites
