function harness_calc_annloss_deagg_btype(root_eqrm_dir)
% eg ('Q:\trunk_branches\trunk')

datadir = strcat(root_eqrm_dir, '\resources\data')
demodir = strcat(root_eqrm_dir, '\demo\output\prob_risk')

% parameters that eventually get passed to the function
outputdir = strcat(root_eqrm_dir, '\postprocessing')

cd(demodir) 
 % convert EQRM outputs to MATLAB binary files (x2) 
Convert_Py2Mat_Risk(demodir,'THE_PARAM_T.txt',datadir)

% example 5
[eqrm_param_T, ecloss_data,annloss_deagg_btype_T] = wrap_risk_plots(1, ...
    'calc_annloss_deagg_btype',demodir, ...
    [demodir,'/matlab_setdata.mat'],[demodir,'/newc_db_savedecloss.mat']);

end