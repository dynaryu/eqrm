"""
  EQRM parameter file

  All input files are first searched for in the input_dir, then in the
  resources/data directory, which is part of EQRM.

 All distances are in kilometers.
 Acceleration values are in g.
 Angles, latitude and longitude are in decimal degrees.

 If a field is not used, set the value to None.


"""

from eqrm_code.parse_in_parameters import eqrm_data_home, get_time_user
from os.path import join


# Operation Mode
run_type = "risk" 
is_deterministic = False
max_width = 15

# Deterministic input
determ_azimith = 340
determ_depth = 11.5
determ_latitude = -32.95
determ_longitude = 151.61
determ_magnitude = 5.6
determ_dip = 35
determ_number_of_events = 166

# Probabilistic input
prob_azimuth_in_zones = [180, 180, 180, 180, 180, 180]
prob_delta_azimuth_in_zones = [180, 180, 180, 180, 180, 180]
prob_min_mag_cutoff = 4.5
prob_number_of_mag_sample_bins = 15
prob_number_of_events_in_zones = [0, 0, 0, 0, 0, 1]
prob_dip_in_zones = [35, 35, 35, 35, 35, 35]

# Attenuation
atten_models = ['Toro_1997_midcontinent']
atten_model_weights = [1.0]
atten_aggregate_Sa_of_atten_models = False
atten_use_variability = True
atten_variability_method = 2
atten_periods = [0.0, 0.175, 0.3, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.1, 3.4]
atten_threshold_distance = 400
atten_use_rescale_curve_from_pga = False
atten_rescale_curve_from_pga = None
atten_cutoff_max_spectral_displacement = False
atten_pga_scaling_cutoff = 2
atten_smooth_spectral_acceleration = False
atten_log_sigma_eq_weight = 0

# Amplification
use_amplification = True
amp_use_variability = True
amp_variability_method = 2
amp_min_factor = 0.6
amp_max_factor = 10000

# Buildings
buildings_usage_classification = "HAZUS" 
buildings_set_damping_Be_to_5_percent = False

# Capacity Spectrum Method
csm_use_variability = True
csm_variability_method = 3
csm_standard_deviation = 0.3
csm_damping_regimes = 0
csm_damping_modify_Tav = True
csm_damping_use_smoothing = True
csm_use_hysteretic_damping = True
csm_hysteretic_damping = "Error" 
csm_SDcr_tolerance_percentage = 1
csm_damping_max_iterations = 7

# Loss
loss_min_pga = 0.05
loss_regional_cost_index_multiplier = 1.4516
loss_aus_contents = 0

# Save
save_hazard_map = False
save_total_financial_loss = True
save_building_loss = False
save_contents_loss = False
save_motion = False
save_prob_structural_damage = True

# General
site_tag = "newc" 
return_periods = [10, 50, 100, 200, 250, 474.56, 500, 974.78999999999996, 1000, 2474.9000000000001, 2500, 5000, 7500, 10000]
use_site_indexes = True
site_indexes = 3541
site_db_tag = "" 
input_dir = r".\implementation_tests\input/" 
output_dir = r".\implementation_tests\current\TS_risk61/" 

# If this file is executed the simulation will start.
# Delete all variables that are not EQRM parameters variables. 
if __name__ == '__main__':
    from eqrm_code.analysis import main
    main(locals())