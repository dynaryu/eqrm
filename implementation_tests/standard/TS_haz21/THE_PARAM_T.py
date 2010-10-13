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
run_type = "hazard" 
is_scenario = False
max_width = 15
site_tag = "newc" 
return_periods = [140., 200., 600.]
input_dir = r".\implementation_tests\input/" 
output_dir = r".\implementation_tests\current\TS_haz21/" 
use_site_indexes = True
site_indexes = [2997, 2657, 3004, 3500]

# Scenario input

# Probabilistic input
prob_min_mag_cutoff = 4.5
prob_number_of_events_in_zones = [0, 0, 0, 0, 0, 2]

# Attenuation
atten_models = ['mean_10_sigma_1']
atten_model_weights = [1]
atten_collapse_Sa_of_atten_models = True
atten_variability_method = None
atten_periods = [0.0, 1.0526,  2.0]
atten_override_RSA_shape = None
atten_cutoff_max_spectral_displacement = False
atten_pga_scaling_cutoff = 999999
atten_smooth_spectral_acceleration = None
atten_spawn_bins = 2

# Amplification
use_amplification = None
amp_variability_method = None

# Buildings

# Capacity Spectrum Method

# Loss

# Save
save_hazard_map = True
save_total_financial_loss = False
save_building_loss = False
save_contents_loss = False
save_motion = False
save_prob_structural_damage = None

# If this file is executed the simulation will start.
# Delete all variables that are not EQRM parameters variables. 
if __name__ == '__main__':
    from eqrm_code.analysis import main
    main(locals())