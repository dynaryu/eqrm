"""
 Title: analysis.py

  Author:  Peter Row, peter.row@ga.gov.au
           Duncan Gray, duncan.gray@ga.gov.au

  Description: The main program of EQRMA. Reads in .par files to do
  simulations. See README-getting-started.txt for information on how
  to use this module.

  Version: $Revision: 1666 $
  ModifiedBy: $Author: dgray $
  ModifiedDate: $Date: 2010-05-10 23:21:10 +1000 (Mon, 10 May 2010) $

  Copyright 2007 by Geoscience Australia
"""

import sys
import os
import time
import shutil
import copy
import datetime
import scipy

from scipy import where, allclose, newaxis, array, isfinite, zeros, asarray, \
     arange, reshape, exp

from eqrm_code.parse_in_parameters import  \
    ParameterSyntaxError, create_parameter_data, convert_THE_PARAM_T_to_py
from eqrm_code.event_set import Event_Set, Pseudo_Event_Set, Event_Activity, \
     Obsolete_Event_Activity, generate_synthetic_events_fault
from eqrm_code.ground_motion_calculator import \
     Multiple_ground_motion_calculator
from eqrm_code.regolith_amplification_model import get_soil_SA, \
     Regolith_amplification_model, load_site_class2vs30
from eqrm_code.source_model import source_model_from_xml, Source_Model
from eqrm_code.output_manager import save_motion, save_distances, save_sites, \
         save_event_set, save_hazard, save_structures, save_val, \
         save_ecloss, join_parallel_files, join_parallel_files_column, \
         save_damage, get_source_file_handle
from eqrm_code.util import reset_seed, determine_eqrm_path, \
     get_local_or_default, add_last_directory
from ground_motion_distribution import Distribution_Log_Normal
from eqrm_code.structures import Structures, build_par_file
from eqrm_code.exceedance_curves import do_collapse_logic_tree, hzd_do_value
from eqrm_code.sites import Sites, truncate_sites_for_test
from eqrm_code.damage_model import calc_total_loss
from eqrm_code.parallel import Parallel
from eqrm_code.ANUGA_utilities import log
from eqrm_code.get_version import get_version
from eqrm_code.bridges import Bridges
import eqrm_code.util as util
import eqrm_filesystem as eq_fs


# data columns expected in a BRIDGE data file
BridgeDataColumns = {'BID': int,
                     'LONGITUDE': float,
                     'LATITUDE': float,
                     'STRUCTURE_CLASSIFICATION': str,
                     'STRUCTURE_CATEGORY': str,
                     'SKEW': float,
                     'SPAN': int,
                     'SITE_CLASS': str}


def main(parameter_handle,
         use_determ_seed=True,
         compress_output=False,
         eqrm_dir=None,
         is_parallel=True):
    """Script to run eqrm program.

    The parameters are defined by the parameter_handle.
    If is either a file name, dictionary of the parameters or
    an object with the parameters as attributes.
    See new_param_list.pdf in Documentation for details on the parameters.

    If use_determ_seed is True, then a hardwired seed is used
    (so that results can be replicated). If use_determ_seed is
    False, then the random seeds are reset based on time.

    If compress_output == True (True, 1, etc), output will be
    in the form output_file.txt.gz - a gzip file containing
    output_file.txt

    eqrm_dir: The directory which 'eqrm_code' and 'resources' reside.
    """
    t0 = time.clock()


    # Let's work-out the eqrm dir
    if eqrm_dir is None:
        eqrm_dir = determine_eqrm_path(__file__)

    # Get an object that holds all the parameters in parameter_handle.
    # Note that arrays and floating point numbers will be converted,
    # everthing else will be a string.
    try:
        THE_PARAM_T=create_parameter_data(parameter_handle,
                                          default_input_dir=
                                              os.path.join(eqrm_dir,
                                                   eq_fs.Resources_Data_Path),
                                          use_determ_seed=use_determ_seed,
                                          compress_output=compress_output,
                                          eqrm_dir=eqrm_dir,
                                          is_parallel=is_parallel)
    except ParameterSyntaxError, e:
        print 'File parameter error:', e
        import sys
        sys.exit(1)
        # FIXME throw error to catch

    del use_determ_seed
    del compress_output
    del eqrm_dir
    del is_parallel
    
     # Reset random seeds if required
    # If use_determ_seed is True, then use a hardwired seed.
    # If use_determ_seed is False, set random seeds based on time.
    reset_seed(THE_PARAM_T.use_determ_seed)

    # Setting up parallelisation
    parallel = Parallel(THE_PARAM_T.is_parallel)

    # Make the output dir, if it is not present
    add_last_directory(THE_PARAM_T.output_dir)

    # copy input parameter file to output directory.
    if isinstance(parameter_handle, str) and parameter_handle[-3:] == '.py':
        shutil.copyfile(parameter_handle,
                        THE_PARAM_T.output_dir+'THE_PARAM_T.py')
    else:
        para_instance = copy.deepcopy(THE_PARAM_T)
        convert_THE_PARAM_T_to_py(
            os.path.join(THE_PARAM_T.output_dir, 'THE_PARAM_T.txt'),
            para_instance)

    # Set up the logging
    # Use defaults.
    #log.console_logging_level = log.INFO
    #log.file_logging_level = log.DEBUG
    log_filename = os.path.join(THE_PARAM_T.output_dir,
                                'log' + parallel.file_tag + '.txt')
    log.log_filename = log_filename
    log.remove_log_file()
    log.set_log_file(log_filename)
    log.debug('host name: ' + str(parallel.node))
    version, date, modified = get_version()
    log.debug('SVN version: ' + str(version))
    log.debug('SVN date: ' + str(date))
    log.debug('SVN modified: ' + str(modified))
    log.debug('Memory: Initial')
    log.resource_usage()

    if THE_PARAM_T.is_scenario is True:
        # generate a scenario event set
        event_set = Event_Set.create_scenario_events(
            rupture_centroid_lat=[THE_PARAM_T.scenario_latitude],
            rupture_centroid_lon=[THE_PARAM_T.scenario_longitude],
            azimuth=[THE_PARAM_T.scenario_azimuth],
            dip=[THE_PARAM_T.scenario_dip],
            Mw=[THE_PARAM_T.scenario_magnitude],
            depth=[THE_PARAM_T.scenario_depth],
            fault_width=THE_PARAM_T.max_width,
            scenario_number_of_events=THE_PARAM_T.scenario_number_of_events)
        # Other rupture parameters are calculated by event_set object.
        # trace start is calculated from centroid and azimuth.
        # Rupture area, length, and width are calculated from Mw
        # using Wells and Coppersmith 94 (modified so rupture
        # width is less than fault_width).
        if THE_PARAM_T.atten_spawn_bins is not None:
            num_spawning = THE_PARAM_T.atten_spawn_bins
        else:
            num_spawning = 1
        event_activity = Event_Activity(len(event_set))
        event_activity.set_scenario_event_activity()
        event_set.scenario_setup()
        source_model = Source_Model.create_scenario_source_model(
            len(event_set))
        source_model.set_attenuation(THE_PARAM_T.atten_models,
                                          THE_PARAM_T.atten_model_weights)
    else:
        # (i.e. is_scenario is False) generate a probablistic event set
        # (using THE_PARAM_T.source_filename)
 # Once the event control file is 'fully operational'
        # remove the try.
        try:
            fid_event_types = get_source_file_handle(THE_PARAM_T,
                                                 source_file_type='event_type')
        except IOError:
            fid_event_types = None
        try:
            fid_sourcepolys = get_source_file_handle(THE_PARAM_T, 
                                                     source_file_type='zone')
        except IOError:
            fid_sourcepolys = None
      
        # tell event set which source models to calculate activity with
        if fid_sourcepolys is not None:
            source_model_zone = source_model_from_xml(
                fid_sourcepolys.name,
                THE_PARAM_T.prob_min_mag_cutoff)

       
            if fid_event_types is not None:
                source_model_zone.add_event_type_atts_to_sources(fid_event_types)
                # This is a hack, until
                # gm splitting is working
                THE_PARAM_T['atten_models'] = source_model_zone[0].atten_models
                THE_PARAM_T['atten_model_weights'] = \
                    source_model_zone[0].atten_model_weights
            
            if THE_PARAM_T.atten_models is not None and \
                THE_PARAM_T.atten_model_weights is not None:
                source_model_zone.set_attenuation(THE_PARAM_T.atten_models,
                                           THE_PARAM_T.atten_model_weights)
            log.debug('Memory: source_model_zone created')
            log.resource_usage()

            # Generating the event set (i.e. a synthetic event catalogue)
            #  - see manual for details
            # FIXME DSG-DSG
            #generate_synthetic_events and Obsolete_Source_Models seem too 
            # connected.
            # They both need fid_sourcepolys and prob_min_mag_cutoff.
            # Yet can these values be different?
            event_set = Event_Set.generate_synthetic_events(
                fid_genpolys=fid_sourcepolys,
                prob_min_mag_cutoff=
                THE_PARAM_T.prob_min_mag_cutoff,
                prob_number_of_events_in_zones=\
                THE_PARAM_T.prob_number_of_events_in_zones)

            log.debug('Memory: event_set_zone created')
            log.resource_usage()

        
        
        #generate event set and source_models for the fault sources
        
        try:
            fid_sourcefaults = get_source_file_handle(THE_PARAM_T, 
                                                 source_file_type='fault')
        except IOError:
            fid_sourcefaults = None
            log.debug('No fault source XML file found')
        if (fid_event_types is not None) and (fid_sourcefaults is not None):
            (event_set_fault,source_model_fault)\
                                    =_fault(
                                    fid_sourcefaults, 
                                    fid_event_types,
                                    THE_PARAM_T.prob_min_mag_cutoff, 
                                    THE_PARAM_T.prob_number_of_events_in_faults)
            
         
        # add the two event sets and source models together

        source_model = source_model_zone
        
        # event activity is calculated here and the event_set are subsampled.
        num_spawning = 1
        event_activity = Event_Activity(len(event_set))
        source_model.calculate_recurrence(
            event_set,
            event_activity)

        log.debug('Memory: event activity has been calculated')
        log.resource_usage()
        
    

    msg = 'Event set created. Number of events=' + str(len(event_set.depth))
    log.info(msg)
    log.debug('Memory: Event Set created')
    log.resource_usage()

    # load all data into a 'sites' object
    # if we have bridge data, 'have_bridge_data' will be True
    (sites, have_bridge_data) = load_data(THE_PARAM_T)

    # if required, 'thin' sites for testing
    all_sites = truncate_sites_for_test(THE_PARAM_T.use_site_indexes, sites,
                                        THE_PARAM_T.site_indexes)

    del sites
    num_sites = len(all_sites)

    log.info('Sites set created. Number of sites=' + str(num_sites))
    log.debug('Memory: Sites created')
    log.resource_usage()

    pseudo_event_set = Pseudo_Event_Set.split_logic_tree(
        event_set,
        THE_PARAM_T.atten_models,
        THE_PARAM_T.atten_model_weights)

    num_events = len(event_set)
    num_psudo_events = len(THE_PARAM_T.atten_models) * num_events * \
                       num_spawning
    
    msg = ('Pseudo event set created. Number of pseudo_events=' +
           str(num_psudo_events))
    log.debug(msg)
    log.debug('Memory: Pseudo Event Set created')
    log.resource_usage()
    ground_motion_distribution = Distribution_Log_Normal(
        THE_PARAM_T.atten_variability_method,
        THE_PARAM_T.atten_spawn_bins)
    event_activity.spawn(ground_motion_distribution.spawn_weights)
    
    # Initialise the ground motion object
    # Tasks here include
    #  - interpolation of coefficients to periods of interest
    ground_motion_calc = Multiple_ground_motion_calculator(
        THE_PARAM_T.atten_models,
        periods=THE_PARAM_T.atten_periods,
        model_weights=THE_PARAM_T.atten_model_weights)


    # load in soil amplifications factors
    # searches input_dir then defaultdir
    if THE_PARAM_T.use_amplification is True:
        amp_distribution = Distribution_Log_Normal(
            THE_PARAM_T.amp_variability_method)
    
        amp_factor_file = THE_PARAM_T.site_tag + '_par_ampfactors.xml'
        amp_factor_file = get_local_or_default(amp_factor_file,
                                               THE_PARAM_T.default_input_dir,
                                               THE_PARAM_T.input_dir)
        soil_amplification_model = \
            Regolith_amplification_model.from_xml(
            amp_factor_file.name,
            distribution_instance= None)
    else:
        soil_amplification_model = None
        amp_distribution = None

    # This is where info should be given to all the subprocesses.
    # But what info is there?
    # Also, let's do some timings.
    time_taken_pre_site_loop = (time.clock()-t0)

    #print 'STARTING loop over sites'
    # parallelising over the site loop.
    parallel.calc_lo_hi(num_sites)
    all_sites = all_sites[parallel.lo:parallel.hi]
    array_size = parallel.hi - parallel.lo   # block_size
    msg = ('blocking over sites if running in parallel. block_size=' +
           str(array_size))
    log.debug(msg)

    msg = 'Number of atten_periods=' + str(len(THE_PARAM_T.atten_periods))
    log.debug(msg)

    if THE_PARAM_T.use_amplification is True:
        msg = 'Number of SA_surfaces=2'
    else:
        msg = 'Number of SA_surfaces=1'
    log.debug(msg)

    # initialise some matrices.  These matrices have a site dimension and
    # are filled while looping over sites.  Wether they are needed or
    # not often depends on what is being saved.
    if THE_PARAM_T.save_hazard_map is True:
        bedrock_hazard = zeros((array_size, len(THE_PARAM_T.atten_periods),
                                len(THE_PARAM_T.return_periods)),
                               dtype=float)
        
    else:
        bedrock_hazard = None
        
    if THE_PARAM_T.save_hazard_map is True and \
           THE_PARAM_T.use_amplification is True:
        soil_hazard = zeros((array_size, len(THE_PARAM_T.atten_periods),
                             len(THE_PARAM_T.return_periods)),
                            dtype=float)
    else:
        soil_hazard = None     
    log.debug('Memory: hazard_map array created')
    log.resource_usage() 
    if THE_PARAM_T.save_motion is True:
        bedrock_SA_all = zeros((array_size, num_events * num_spawning,
                                len(THE_PARAM_T.atten_periods)),
                               dtype=float)        
    else:
        bedrock_SA_all = None
        
    if THE_PARAM_T.save_motion is True and \
           THE_PARAM_T.use_amplification is True:
        soil_SA_all = zeros((array_size, num_events * num_spawning,
                             len(THE_PARAM_T.atten_periods)),
                            dtype=float)
    else:
        soil_SA_all = None        
    log.debug('Memory: save_motion array created')
    log.resource_usage()


    if THE_PARAM_T.save_total_financial_loss is True:
        total_building_loss = zeros((array_size, num_psudo_events),
                                    dtype=float)
    if THE_PARAM_T.save_building_loss is True:
        building_loss = zeros((array_size, num_psudo_events),
                              dtype=float)
    if THE_PARAM_T.save_contents_loss is True:
        contents_loss = zeros((array_size, num_psudo_events),
                              dtype=float)
    if (THE_PARAM_T.save_prob_structural_damage is True and
        num_psudo_events == 1 and THE_PARAM_T.run_type == "risk"):
        # total_structure_damage, given as a non-cumulative
        # probability. The axis are  sites, model_generated_psudo_events,
        # damage_states
        # (the damage_states are slight, moderate, extensive and complete.
        # subtract all of these from 1 to get the prob of no damage.)
        total_structure_damage = zeros((array_size, 4), dtype=float)

    # create result array to save 'days to complete' data
    # need to store 'fp' days + state field
    
    if THE_PARAM_T.bridges_functional_percentages is not None and \
           have_bridge_data:
        saved_days_to_complete = zeros((
            array_size, num_psudo_events,
            len(THE_PARAM_T.bridges_functional_percentages)))

    log.debug('Memory: Created all data collection arrays.')
    log.resource_usage()

    # get indices of SA periods 0.3 and 1.0, if we have bridge data
    if have_bridge_data:
        bridge_SA_indices = \
                util.find_bridge_sa_indices(THE_PARAM_T.atten_periods)
    else:
        bridge_SA_indices = None

    # check that when we have bridge data, there is only one event
    if have_bridge_data and num_psudo_events > 1:
        msg = 'Input data includes bridges, but number of events > 1?'
        raise RuntimeError(msg)

    for i in range(array_size):
        msg = 'do site ' + str(i+1) + ' of ' + str(num_sites)
        log.info(msg)
        rel_i = i #- parallel.lo

        sites = all_sites[i:i+1] # take site i

        # note if you take sites[i], it will collapse the dimension

        # By not collapsing sites, and making the assignment
        # sites=all_sites[i:i+1], the code will work with a single site
        # at a time, without multiple reference to the loop variable 'i'.

        # This also means that the code below will deal with a vectorized
        # sites without any modification.
        # To remove loop over sites, just disable the loop
        # and remove the 'sites=all_sites[i:i+1]'.
        # and change NUM_SITES_PER_SITE_LOOP
        # CAUTIONS:
        #  1.  this will run out of memory if sites*events is large.
        #  2.  this has not been tested recently
        
        soil_SA, bedrock_SA = calc_and_save_SA(
            THE_PARAM_T,
            sites,
            event_set,
            bedrock_SA_all,
            soil_SA_all,
            bedrock_hazard,
            soil_hazard,
            ground_motion_calc,
            soil_amplification_model,
            i,
            rel_i,
            ground_motion_distribution,
            amp_distribution,
            event_activity)

        # calculate damage
        if THE_PARAM_T.run_type == "risk":
            #print 'STARTING building damage calculations'
            # Decide which SA to use
            if soil_SA is not None:
                SA = soil_SA
            else:
                SA = bedrock_SA

        
            # smooth SA (function of periods) using a weighted
            # running 3-point smoother
            if THE_PARAM_T.atten_smooth_spectral_acceleration is True:
                SA[:,:,1:-2] = (0.25*SA[:,:,0:-3] +
                                0.50*SA[:,:,1:-2] +
                                0.25*SA[:,:,2:-1])


            (total_loss, damage,
               days_to_complete) = calc_total_loss(sites, SA, THE_PARAM_T,
                                                   pseudo_event_set.Mw,
                                                   bridge_SA_indices)
            assert isfinite(total_loss[0]).all()

            # I think it's called total loss since it is summed over
            # all of the events.
            # break loss tuple into components
            # structure_loss = structural loss
            # nsd_loss = non-structural drift sensitive loss
            # accel_loss = non-structural acceleration  sensitive loss
            # con_loss = contents loss
            (structure_loss, nsd_loss, accel_loss, con_loss) = total_loss

            # putting economic loss values into a big array
            # (number of buildings versus number of events)
            # Note that this matrix is transposed before saving
            # (i.e. to number of events versus number of buildings)
            if THE_PARAM_T.save_total_financial_loss is True:
                total_building_loss[rel_i,:] = (structure_loss + nsd_loss +
                                                accel_loss + con_loss)[0,:]
            if THE_PARAM_T.save_building_loss is True:
                building_loss[rel_i,:] = (structure_loss + nsd_loss +
                                          accel_loss)[0,:]
            if THE_PARAM_T.save_contents_loss is True:
                contents_loss[rel_i,:] = con_loss[0,:]

            if (THE_PARAM_T.save_prob_structural_damage is True and
                    num_psudo_events == 1):
                # This is not cumulative
                total_structure_damage[rel_i,:] = damage.structure_state

            # accumulate days to complete           
            if THE_PARAM_T.bridges_functional_percentages is not None and have_bridge_data:
                saved_days_to_complete[rel_i,:,:] = days_to_complete

            #print 'ENDING building damage calculations'
        # ENDED BUILDING DAMAGE
    # --------------------------------------------------------------
    # THIS IS THE END OF THE LOOP OVER SITES

    log.debug('Memory: Ended looping over sites')
    log.resource_usage()

    row_files_that_parallel_splits = []
    column_files_that_parallel_splits = []

    loop_time = (time.clock() - t0)
    time_taken_site_loop = loop_time - time_taken_pre_site_loop
    time_pre_site_loop_fraction = time_taken_pre_site_loop/loop_time

    msg = "time_pre_site_loop_fraction " + str(time_pre_site_loop_fraction)
    log.info(msg)
    msg = "loop_time (excluding file saving) " + \
           str(datetime.timedelta(seconds=loop_time)) + " hr:min:sec"
    log.info(msg)

    #print "time_taken_pre_site_loop", time_taken_pre_site_loop
    #print "time_taken_site_loop", time_taken_site_loop

    # SAVE HAZARD
    if THE_PARAM_T.save_hazard_map is True and parallel.lo != parallel.hi:
        files = save_hazard('bedrock_SA', THE_PARAM_T, hazard=bedrock_hazard,
                            sites=all_sites,
                            compress=THE_PARAM_T.compress_output,
                            parallel_tag=parallel.file_tag,
                            write_title=(parallel.rank == False))
        row_files_that_parallel_splits.extend(files)

        if soil_hazard is not None:
            files = save_hazard('soil_SA', THE_PARAM_T, hazard=soil_hazard,
                                compress=THE_PARAM_T.compress_output,
                                parallel_tag=parallel.file_tag,
                                write_title=(parallel.rank == False))
            row_files_that_parallel_splits.extend(files)

    # Save Ground Motion
    if THE_PARAM_T.save_motion is True and parallel.lo != parallel.hi:
        file = save_sites(THE_PARAM_T.output_dir, THE_PARAM_T.site_tag,
                          sites=all_sites,
                          compress=THE_PARAM_T.compress_output,
                          parallel_tag=parallel.file_tag,
                          write_title=(parallel.rank == False))
        row_files_that_parallel_splits.append(file)

        files = save_motion('bedrock_SA', THE_PARAM_T,motion=bedrock_SA_all,
                            compress=THE_PARAM_T.compress_output,
                            parallel_tag=parallel.file_tag,
                            write_title=(parallel.rank == False))
        row_files_that_parallel_splits.extend(files)

        if soil_SA_all is not None:
            files = save_motion('soil_SA',THE_PARAM_T,motion=soil_SA_all,
                               compress=THE_PARAM_T.compress_output,
                               parallel_tag=parallel.file_tag,
                               write_title=(parallel.rank == False))
            row_files_that_parallel_splits.extend(files)


    # Save damage information
    if (THE_PARAM_T.save_prob_structural_damage is True and
            num_psudo_events == 1 and
            THE_PARAM_T.run_type == 'risk' and
            parallel.lo != parallel.hi):
        # No sites were investigated.
        file = save_damage(THE_PARAM_T.output_dir, THE_PARAM_T.site_tag,
                           'structural', total_structure_damage,
                           all_sites.attributes['BID'],
                           compress=THE_PARAM_T.compress_output,
                           parallel_tag=parallel.file_tag,
                           write_title=(parallel.rank == False))
        row_files_that_parallel_splits.append(file)

    if ((THE_PARAM_T.save_motion is True or
                 THE_PARAM_T.save_total_financial_loss is True or
                 THE_PARAM_T.save_building_loss is True or
                 THE_PARAM_T.save_contents_loss is True) and
            parallel.lo != parallel.hi):
        files = save_distances(THE_PARAM_T, sites=all_sites,
                               event_set=event_set,
                               compress=THE_PARAM_T.compress_output,
                               parallel_tag=parallel.file_tag)
        column_files_that_parallel_splits.extend(files)

    # Save economic loss
    if ((THE_PARAM_T.save_total_financial_loss is True or
                 THE_PARAM_T.save_building_loss is True or
                 THE_PARAM_T.save_contents_loss is True) and
            parallel.lo != parallel.hi):
        file = save_structures(THE_PARAM_T, all_sites,
                               compress=THE_PARAM_T.compress_output,
                               parallel_tag=parallel.file_tag,
                               write_title=(parallel.rank == False))
        row_files_that_parallel_splits.append(file)

    if (THE_PARAM_T.save_total_financial_loss is True and
            parallel.lo != parallel.hi):
        # The do_collapse_logic_tree here will
        # have to be changed to take into account
        # the different atten weigths for each source.
        # No sites were investigated.
        #print "analysis total_building_loss",total_building_loss
        (new_total_building_loss, _, _) = \
                do_collapse_logic_tree(total_building_loss[:,:,newaxis],
                                       pseudo_event_set.index,
                                       pseudo_event_set.attenuation_weights,
                                       THE_PARAM_T)

        #print "analysis new_total_building_loss", new_total_building_loss
        # collapse out fake periods axis
        new_total_building_loss = new_total_building_loss[:,:,0]
        file = save_ecloss('_total_building',THE_PARAM_T,
                           new_total_building_loss, all_sites,
                           compress=THE_PARAM_T.compress_output,
                           parallel_tag=parallel.file_tag)
        column_files_that_parallel_splits.append(file)

        file = save_val(THE_PARAM_T,
                        sum(all_sites.cost_breakdown( \
                           ci=THE_PARAM_T.loss_regional_cost_index_multiplier)),
                        '_bval',
                        compress=THE_PARAM_T.compress_output,
                        parallel_tag=parallel.file_tag)
        row_files_that_parallel_splits.append(file)

    if THE_PARAM_T.save_building_loss is True and parallel.lo != parallel.hi:
        (new_building_loss, _, _) = \
            do_collapse_logic_tree(building_loss[:,:,newaxis],
                                   pseudo_event_set.index,
                                   pseudo_event_set.attenuation_weights,
                                   THE_PARAM_T)

         # collapse out fake periods axis
        new_building_loss = new_building_loss[:,:,0]
        file = save_ecloss('_building', THE_PARAM_T, new_building_loss,
                           all_sites, compress=THE_PARAM_T.compress_output,
                           parallel_tag=parallel.file_tag)
        column_files_that_parallel_splits.append(file)

#         file = save_val(THE_PARAM_T,sum( \
#             all_sites.cost_breakdown(
# ci=THE_PARAM_T.loss_regional_cost_index_multiplier)[:-1]),
#                         '_bval',
#                         compress=THE_PARAM_T.compress_output,
#                         parallel_tag=parallel.file_tag)
#         row_files_that_parallel_splits.append(file)

    if THE_PARAM_T.save_contents_loss is True and parallel.lo != parallel.hi:
        (new_contents_loss, _, _) = \
            do_collapse_logic_tree(contents_loss[:,:,newaxis],
                                   pseudo_event_set.index,
                                   pseudo_event_set.attenuation_weights,
                                   THE_PARAM_T)

        # collapse out fake  axis
        new_contents_loss = new_contents_loss[:,:,0]
        file = save_ecloss('_contents', THE_PARAM_T,new_contents_loss,
                           all_sites, compress=THE_PARAM_T.compress_output,
                           parallel_tag=parallel.file_tag)
        column_files_that_parallel_splits.append(file)

#        file = save_val(THE_PARAM_T,sum( \
#             all_sites.cost_breakdown(
# ci=THE_PARAM_T.loss_regional_cost_index_multiplier)[-1:]), '_cval',
#                   compress=THE_PARAM_T.compress_output,
#                         parallel_tag=parallel.file_tag)
#         row_files_that_parallel_splits.append(file)

#???
    # output "days to complete" data here
#???

    if parallel.rank == 0:		# No site component
        # So just get one process to write these files.
        save_event_set(THE_PARAM_T, pseudo_event_set,
                       pseudo_event_set.event_activity,
                       compress=THE_PARAM_T.compress_output)

    # delete big data structures here

    # parallel code.  Needed if # of processes is > # of structures
    calc_num_blocks = parallel.calc_num_blocks()

    # Now process 0 can stich some files together.
    if parallel.is_parallel and parallel.rank == 0:
        join_parallel_files(row_files_that_parallel_splits,
                            calc_num_blocks,
                            compress=THE_PARAM_T.compress_output)

        join_parallel_files_column(column_files_that_parallel_splits,
                                   calc_num_blocks,
                                   compress=THE_PARAM_T.compress_output)

    # Let's stop all the programs at the same time
    # Needed when scenarios are in series.
    # This was hanging nodes, when using mpirun
    real_time_taken_overall = (time.clock() - t0)
    msg = "On node %i, %s time_taken_overall %s hr:min:sec" % \
          (parallel.rank,
           parallel.node,
           str(datetime.timedelta(seconds=real_time_taken_overall)) )
    log.info(msg)
    del parallel
    log.debug('Memory: End')
    log.resource_usage()
    log.remove_file_handler()

################################################################################
# these are subfunctions
################################################################################

# TODO remove the distribution that's put into ground_motion_calc
# pass in event_activity

def calc_and_save_SA(THE_PARAM_T,
                     sites,
                     event_set,
                     bedrock_SA_all,
                     soil_SA_all,
                     bedrock_hazard,
                     soil_hazard,
                     ground_motion_calc,
                     soil_amplification_model,
                     site_index,
                     rel_site_index,
                     ground_motion_distribution,
                     amp_distribution,
                     event_activity):
    if True: # turn this into the ground-motion splitting loop
        # evaluate the mean and sigma from the attenuation models at the
        # site of interest note that this is not the RSA that is used
        # - it comes later based on sampling mu and sigma
        # note that we also compute the distance between source and site here
        results = ground_motion_calc.distribution(
            event_set=event_set,
            sites=sites)
        _ , log_mean_extend_GM, log_sigma_extend_GM = results 
        # *_extend_GM has shape of (GM_model, sites, events, periods)
        
        # evaluate the RSA
        # that is desired (i.e. chosen in parameter_handle)
        (_, bedrock_SA, _) = \
                        ground_motion_distribution.sample_for_eqrm(
            log_mean_extend_GM, log_sigma_extend_GM)
        
        soil_SA = None
        #print 'ENDING Calculating attenuation'

        # Setup for amplification  model
        # handles interpolation to periods of interest
        # finds the mean and sigma (i.e. PDF) based on bedrock PGA and
        # Moment magnitude (if amps are a function of these)
        if THE_PARAM_T.use_amplification is True:
            soil_SA = get_soil_SA(bedrock_SA,
                                  sites.attributes['SITE_CLASS'],
                                  event_set.Mw, THE_PARAM_T.atten_periods,
                                  soil_amplification_model,
                                  amp_distribution, ground_motion_calc)
                
            # Amplification factor cutoffs
            # Applies a minimum and maxium acceptable amplification factor
            # re-scale SAsoil if Ampfactor falls ouside acceptable
            # ampfactor bounds
            if THE_PARAM_T.amp_variability_method is not None:
                soil_SA = amp_rescale(
                    THE_PARAM_T.amp_min_factor,
                    THE_PARAM_T.amp_max_factor,
                    soil_SA,
                    bedrock_SA)

            # PGA cutoff
            assert isfinite(soil_SA).all()
            soil_SA = cutoff_pga(soil_SA,
                                    THE_PARAM_T.atten_pga_scaling_cutoff)
            
            # qa on ampfactors
            #if int(THE_PARAM_T.qa_switch_ampfactors)>=1:
                #print 'ENDING Calculating soil amplification'
                #print

        else: 		# THE_PARAM_T.use_amplification
            #if int(THE_PARAM_T.qa_switch_ampfactors)>=1:
            #    print 'No soil amplification'
            #    print
            soil_SA = None
        bedrock_SA = cutoff_pga(bedrock_SA,
                                   THE_PARAM_T.atten_pga_scaling_cutoff)
        
        bedrock_SA, soil_SA = apply_threshold_distance(
            sites,
            THE_PARAM_T.atten_threshold_distance,
            THE_PARAM_T.use_amplification, event_set,
            bedrock_SA, soil_SA)
        
        # collapse  multiple attenuation models 
        if (THE_PARAM_T.save_motion is True or
            THE_PARAM_T.save_hazard_map is True):           
            (collapsed_bedrock_SA, _, _) = do_collapse_logic_tree(
                bedrock_SA,
                [1],
                THE_PARAM_T.atten_model_weights,
                THE_PARAM_T)
            
            if soil_SA is not None:               
                (collapsed_soil_SA, _, _) = do_collapse_logic_tree(
                    soil_SA, [1],
                    THE_PARAM_T.atten_model_weights,
                    THE_PARAM_T)


        # saving RSA - only generally done for Ground Motion Simulation
        # (not for probabilistic hazard or if doing risk/secnario loss)
        if THE_PARAM_T.save_motion is True:
            # Put into arrays
            # combining the site and spawning dimensions
            assert collapsed_bedrock_SA.shape[1] == 1 # only one site
            coll_fold_bedrock_SA = collapsed_bedrock_SA.reshape(
                (-1, len(THE_PARAM_T.atten_periods)))
            bedrock_SA_all[rel_site_index] = coll_fold_bedrock_SA
            if soil_SA is not None:
                coll_fold_soil_SA = collapsed_soil_SA.reshape(
                    (-1, len(THE_PARAM_T.atten_periods)))
                soil_SA_all[rel_site_index] = coll_fold_soil_SA

        # Compute hazard if desired
        if THE_PARAM_T.save_hazard_map is True:
            event_act_d_events = event_activity.event_activity.reshape(-1)
            assert collapsed_bedrock_SA.shape[1] == 1 # only one site
            for j in range(len(THE_PARAM_T.atten_periods)):
                # Get these two arrays to be vectors.
                # The sites and spawning dimensions are flattened
                # into the events dimension.
                if collapsed_bedrock_SA.ndim == 3:
                    bedrock_SA_events = collapsed_bedrock_SA[:,:,j].reshape(
                        1,-1)
                else: # assuming 4 dimensions
                    bedrock_SA_events = collapsed_bedrock_SA[:,:,:,j].reshape(
                        1,-1)
                bedrock_hazard[site_index,j] = \
                        hzd_do_value(bedrock_SA_events,
                                     event_act_d_events,
                                     1.0/array(THE_PARAM_T.return_periods))
                if soil_SA is not None:
                    if collapsed_bedrock_SA.ndim == 3:
                        soil_SA_events = collapsed_soil_SA[:,:,j].reshape((-1))
                    else: # assuming 4 dimensions
                        soil_SA_events = collapsed_soil_SA[:,:,:,j].reshape(
                            (-1))
                    soil_hazard[site_index,j] = \
                        hzd_do_value(soil_SA_events,
                                     event_act_d_events,
                                     1.0/array(THE_PARAM_T.return_periods))
                    
        # End the Ground motion splitting loop
        # Build the SA, soil, if we did it.  If not, Bedrock.

        # Change dimensions.  Put the ground motion model dimension
        # and spawning dimension into the event dimension
        # for the risk calculations
        # Assume the SA's have
        # 3 or more dimensions; with ground motion model being the
        # third last dimension e.g.
        # (ground motion model, site, events, periods)
        # (spawn, ground motion model, site, events, periods)
        last_4_dims = bedrock_SA.shape[-4:]
        num_gmm = last_4_dims[0]
        num_sites = last_4_dims[1]
        num_events = last_4_dims[2]
        num_periods = last_4_dims[3]
        if bedrock_SA.ndim == 4:
            event_overloaded = num_events * num_gmm
        else:  # assume 5 dimensions
            num_spawn = bedrock_SA.shape[0]
            event_overloaded = num_events * num_gmm * num_spawn
        if soil_SA is not None:
            soil_SA = reshape(soil_SA, (num_sites,
                                        event_overloaded,
                                        num_periods))  
        bedrock_SA = reshape(bedrock_SA, (num_sites,
                                          event_overloaded,
                                          num_periods ))  
        
        return soil_SA, bedrock_SA

def apply_threshold_distance(sites,
                             atten_threshold_distance,
                             use_amplification,
                             event_set,
                             bedrock_SA,
                             soil_SA):
    
        # re-compute the source-site distances
        # (NEEDED because this is not returned from bedrock_SA_pdf)
        # Identify sites which are greater than
        # THE_PARAM_T.atten_threshold_distance from an event
        # (NO GM computed for these sites)
        # This is not necessarily recomputing, since the
        # distance method used previously may not be Joyner_Boore.
        # But does this need to be Joyner_Boore?
        # FIXME do this earlier, and reduce the distribution calcs to do.
    distances = sites.distances_from_event_set(event_set). \
                distance('Joyner_Boore')
    # distances.shape = (site, event)
    Haznull = where(distances > atten_threshold_distance)
    if bedrock_SA.ndim == 3:
        if use_amplification is True:
            bedrock_SA[Haznull[0], Haznull[1],:] = 0
            soil_SA[Haznull[0], Haznull[1],:] = 0
        else:
            bedrock_SA[Haznull[0], Haznull[1],:] = 0
    elif bedrock_SA.ndim == 4:
        if use_amplification is True:
            bedrock_SA[:,Haznull[0], Haznull[1],:] = 0
            soil_SA[:,Haznull[0], Haznull[1],:] = 0
        else:
            bedrock_SA[:,Haznull[0], Haznull[1],:] = 0
    elif bedrock_SA.ndim == 5:
        if use_amplification is True:
            bedrock_SA[:,:,Haznull[0], Haznull[1],:] = 0
            soil_SA[:,:,Haznull[0], Haznull[1],:] = 0
        else:
            bedrock_SA[:,:,Haznull[0], Haznull[1],:] = 0
        
        
    return bedrock_SA, soil_SA

def amp_rescale(amp_min_factor, amp_max_factor, soil_SA, bedrock_SA):
    if amp_min_factor is not None:
        too_low = (soil_SA/bedrock_SA) < amp_min_factor
        soil_SA[where(too_low)] = (amp_min_factor *
                                   bedrock_SA[where(too_low)])
    if amp_max_factor is not None:
        too_high = (soil_SA/bedrock_SA) > amp_max_factor
        soil_SA[where(too_high)] = (amp_max_factor*
                                    bedrock_SA[where(too_high)])
    return soil_SA


# handles the pga_cutoff
def cutoff_pga(ground_motion, max_pga):
    if max_pga is None:
        return ground_motion
    
    # Doing ground_motion[:,:,0:1] gets the first values of
    # the last dimension,
    # but does not drop a dimension in the return value.
    # ground_motion[:,:,0] would drop a dimension.
    assert isfinite(ground_motion).all()
    if ground_motion.ndim == 4:
        too_high = ground_motion[:,:,:,0:1] > max_pga
        scaling_factor = where(too_high, max_pga/ground_motion[:,:,:,0:1], 1.0)
    elif ground_motion.ndim == 5:
        too_high = ground_motion[:,:,:,:,0:1] > max_pga
        scaling_factor = where(
            too_high, max_pga/ground_motion[:,:,:,:,0:1], 1.0)
    ground_motion *= scaling_factor
    assert isfinite(ground_motion).all()
    return ground_motion


def load_data(THE_PARAM_T):
    """Load structure and bridge data into memory.

    THE_PARAM_T  a reference to the global THE_PARAM_T

    Returns a tuple (data, bridge_data) where:
        data         is a reference to a (possibly combined) structures+bridges
                     object
        bridge_data  is a boolean, True if bridge data was found
    """

    # assume there is no bridge data
    bridge_data = False

    if THE_PARAM_T.run_type == 'risk':
        # first, look for a BUILDING data file
        building_par_file = build_par_file(THE_PARAM_T.buildpars_flag)

        # Find location of site database (i.e. building database) and get FID
        site_file = ('sitedb_' + THE_PARAM_T.site_tag +
                     THE_PARAM_T.site_db_tag + '.csv')
        try:
            site_file = get_local_or_default(site_file,
                                             THE_PARAM_T.default_input_dir,
                                             THE_PARAM_T.input_dir)
        except IOError:
            site_file = None

        if site_file:
            # if indeed there is a BUILDING file
            sites = Structures.from_csv(
                site_file,
                building_parameters_table=building_par_file,
                default_input_dir=
                THE_PARAM_T.default_input_dir,
                input_dir=THE_PARAM_T.input_dir,
                eqrm_dir=THE_PARAM_T.eqrm_dir,
                buildings_usage_classification=
                THE_PARAM_T.buildings_usage_classification,
                use_refined_btypes=
                not THE_PARAM_T.hazus_btypes_flag,
                force_btype_flag=
                THE_PARAM_T.force_btype_flag,
                loss_aus_contents=
                THE_PARAM_T.loss_aus_contents)

            #FIXME do this after subsampling the sites
            # Hard wires the Demand Curve damping to 5%
            if THE_PARAM_T.buildings_set_damping_Be_to_5_percent is True:
                sites.building_parameters['damping_Be'] = 0.05 # + \
#                                      0*sites.building_parameters['damping_Be']
        else:
            sites = None

        # now look for BRIDGE data
        bridge_file = ('bridgedb_' + THE_PARAM_T.site_tag +
                       THE_PARAM_T.site_db_tag + '.csv')
        try:
            bridge_file = get_local_or_default(bridge_file,
                                               THE_PARAM_T.default_input_dir,
                                               THE_PARAM_T.input_dir)
        except IOError:
            bridge_file = None

        if bridge_file:
            bridge_data = True
            bridges = Bridges.from_csv(bridge_file, **BridgeDataColumns)

            if sites:
                new_sites = sites.join(bridges)
                sites = new_sites
                del new_sites
            else:
                sites = bridges
            del bridges

    elif THE_PARAM_T.run_type == "hazard":
        #raise RuntimeError('run_type "hazard" not yet modified for Bridges')

        # we are running hazard or ground motion scenarion (i.e. no damage)
        if THE_PARAM_T.grid_flag == 1:
            # grid is from a GIS output
            name = THE_PARAM_T.site_tag + '_par_site.csv'
        elif THE_PARAM_T.grid_flag == 2:
            # Grid is from the grid_generator.py script
            name = THE_PARAM_T.site_tag + '_par_site_uniform.csv'

        # find the location and FID for the grid file
        # i.e. searches input_dir then defaultdir
        name = get_local_or_default(name, THE_PARAM_T.default_input_dir,
                                    THE_PARAM_T.input_dir)
        sites = Sites.from_csv(name, SITE_CLASS=str)
    else:
        raise ValueError('Got bad value for THE_PARAM_T.run_type: %s'
                         % THE_PARAM_T.run_type)

    # check if we actually have some data to work with
    if sites is None:
        raise RuntimeError("Couldn't find BUILDING or BRIDGE data?")

    # Load the site_class 2 vs30 mapping, if it is needed
    if (THE_PARAM_T.use_amplification is False and
        (THE_PARAM_T.atten_models[0] == 'Boore_08')):
        amp_factor_file = 'site_class2vs30.csv'
        amp_factor_file = get_local_or_default(amp_factor_file,
                                               THE_PARAM_T.default_input_dir,
                                               THE_PARAM_T.input_dir)
        # Load vs30 mapping
        site_class2vs30 = load_site_class2vs30(amp_factor_file)
        # Use the mapping to add vs30 info to add vs30 info to structures
        sites.set_vs30(site_class2vs30)

    return (sites, bridge_data)

################################################################################

# this will run if eqrm_analysis.py is called from DOS prompt or double clicked
if __name__ == '__main__':
    from sys import argv
    if len(argv)>2:
        f=argv[1] # note argv[0] will be 'main.py'
        use_determ_seed=argv[2]
        if use_determ_seed is 'y':
            print 'RESETTING RANDOM SEED'
            use_determ_seed=True
        elif use_determ_seed is 'n':
            print 'NOT RESETTING RANDOM SEED'
            use_determ_seed=False
        else:
            raise 'Input seed parameter must be y or n'
        compress_output=False
        if len(argv)>3:
            compress_output=argv[3]
            if compress_output is 'y':
                print 'Compressing output'
                compress_output=True
            elif compress_output is 'n':
                print 'Not compressing output'
                compress_output=False
        main(f,use_determ_seed,compress_output=compress_output)
    else:
        assert len(argv)==1
        import profile
        profile.run("main('setdata.txt',True)",'fooprof')
        import pstats
        p = pstats.Stats('fooprof')
        p.sort_stats('cumulative').print_stats(10)
        p.sort_stats('cumulative').strip_dirs().print_callees( \
            'distribution_function')

        #main('setdata.txt',True)
