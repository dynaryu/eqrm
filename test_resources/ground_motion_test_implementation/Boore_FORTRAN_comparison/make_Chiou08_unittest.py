#!/usr/bin/env python

"""A program to take the output from the FORTRAN program and make
unittest code for Chiou08."""

import sys
import re
import numpy
import math

# pattern string used to split fields seperated by 1 or more spaces
SpacesPatternString = ' +'

# generate 're' pattern for 'any number of spaces'
SpacesPattern = re.compile(SpacesPatternString)

if len(sys.argv) != 2:
    print('usage: %s <CTL_output>' % sys.argv[0])
    sys.exit(10)

CTL_data_file = sys.argv[1]


Num_CTL_headers = 6
CTL_fields = {'T': 0,    # field name, index
              'M': 1,
              'Az': 3,
              'Rjb': 4,
              'Rrup': 8,
              'Rx': 9,
              'Fhw': 13,
              'Rake': 14,
              'Dip': 16,
              'Ztor': 19,
              'Vs30': 21,
              'Z25': 26,
              'Sa': 45,
              'sigma': 50}


def rake_to_fault_type(rake):
    if -120.0 <= rake <= -60.0:
        return (1, 'normal')
    if 30.0 <= rake <= 150.0:
        return (0, 'reverse')
    return (2, 'strike slip')


def read_file(filename, num_headers, field_dict):
    """Read the python and return a list of values from the file."""

    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    # strip header lines
    lines = lines[num_headers:]

    # step through lines, picking up required fields
    result = []
    for line in lines:
        line = line.strip()
        if line:
            fields = SpacesPattern.split(line)
            for key in CTL_fields:
                exec_str = '%s = %s' % (key, fields[field_dict[key]])
                #                print('exec_str: %s' % exec_str)
                try:
                    exec(exec_str)
                except NameError:
                    print('exec_str=%s' % exec_str)
                    print('field index=%d' % field_dict[key])
                    sys.exit(0)
            result.append((T, M, Az, Rjb, Rrup, Rx, Fhw, Rake, Dip, Ztor, Vs30, Z25, Sa, sigma))

    return result


def write_code(cases):
    """For each case, write unittest code."""

    # set main code indent
    indent = ' ' * 8

    # write test file header
    print('''#!/usr/bin/env python

import unittest
from scipy import array, allclose
from eqrm_code.ground_motion_specification import Ground_motion_specification
from eqrm_code.ground_motion_interface import *

class Dist_Obj(object):
    def __init__(self, Rjb, Rrup, Rx):
        self.Rupture = Rrup
        self.Joyner_Boore = Rjb
        self.Horizontal = Rx

class Test_Chiou08(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Chiou08(self):''')

    print('%sc_tab = array([' % indent)
    print('''
#T (s) c2   c3    c4   c4a crb  chm cg3  c1      c1a     c1b    cn    cm     c5     c6     c7     c7a    c9     c9a     c10     cg1      cg2      phi1    phi2    phi3     phi4     phi5   phi6     phi7   phi8   tau1   tau2   sig1   sig2   sig3   sig4
[ 0.0, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.2687, 0.1000,-0.2550,2.996,4.1840,6.1600,0.4893,0.0512,0.0860,0.7900,1.5005,-0.3218,-0.00804,-0.00785,-0.4417,-0.1417,-0.007010,0.102151,0.2289,0.014996,580.0, 0.0700,0.3437,0.2637,0.4458,0.3459,0.8000,0.0663],
[0.010,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.2687, 0.1000,-0.2550,2.996,4.1840,6.1600,0.4893,0.0512,0.0860,0.7900,1.5005,-0.3218,-0.00804,-0.00785,-0.4417,-0.1417,-0.007010,0.102151,0.2289,0.014996,580.0, 0.0700,0.3437,0.2637,0.4458,0.3459,0.8000,0.0663],
[0.020,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.2515, 0.1000,-0.2550,3.292,4.1879,6.1580,0.4892,0.0512,0.0860,0.8129,1.5028,-0.3323,-0.00811,-0.00792,-0.4340,-0.1364,-0.007279,0.108360,0.2289,0.014996,580.0, 0.0699,0.3471,0.2671,0.4458,0.3459,0.8000,0.0663],
[0.030,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.1744, 0.1000,-0.2550,3.514,4.1556,6.1550,0.4890,0.0511,0.0860,0.8439,1.5071,-0.3394,-0.00839,-0.00819,-0.4177,-0.1403,-0.007354,0.119888,0.2289,0.014996,580.0, 0.0701,0.3603,0.2803,0.4535,0.3537,0.8000,0.0663],
[0.040,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.0671, 0.1000,-0.2550,3.563,4.1226,6.1508,0.4888,0.0508,0.0860,0.8740,1.5138,-0.3453,-0.00875,-0.00855,-0.4000,-0.1591,-0.006977,0.133641,0.2289,0.014996,579.9, 0.0702,0.3718,0.2918,0.4589,0.3592,0.8000,0.0663],
[0.050,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.9464, 0.1000,-0.2550,3.547,4.1011,6.1441,0.4884,0.0504,0.0860,0.8996,1.5230,-0.3502,-0.00912,-0.00891,-0.3903,-0.1862,-0.006467,0.148927,0.2290,0.014996,579.9, 0.0701,0.3848,0.3048,0.4630,0.3635,0.8000,0.0663],
[0.075,1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.7051, 0.1000,-0.2540,3.448,4.0860,6.1200,0.4872,0.0495,0.0860,0.9442,1.5597,-0.3579,-0.00973,-0.00950,-0.4040,-0.2538,-0.005734,0.190596,0.2292,0.014996,579.6, 0.0686,0.3878,0.3129,0.4702,0.3713,0.8000,0.0663],
[0.10, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.5747, 0.1000,-0.2530,3.312,4.1030,6.0850,0.4854,0.0489,0.0860,0.9677,1.6104,-0.3604,-0.00975,-0.00952,-0.4423,-0.2943,-0.005604,0.230662,0.2297,0.014996,579.2, 0.0646,0.3835,0.3152,0.4747,0.3769,0.8000,0.0663],
[0.15, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.5309, 0.1000,-0.2500,3.044,4.1717,5.9871,0.4808,0.0479,0.0860,0.9660,1.7549,-0.3565,-0.00883,-0.00862,-0.5162,-0.3113,-0.005845,0.266468,0.2326,0.014988,577.2, 0.0494,0.3719,0.3128,0.4798,0.3847,0.8000,0.0612],
[0.20, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.6352, 0.1000,-0.2449,2.831,4.2476,5.8699,0.4755,0.0471,0.0860,0.9334,1.9157,-0.3470,-0.00778,-0.00759,-0.5697,-0.2927,-0.006141,0.255253,0.2386,0.014964,573.9,-0.0019,0.3601,0.3076,0.4816,0.3902,0.8000,0.0530],
[0.25, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.7766, 0.1000,-0.2382,2.658,4.3184,5.7547,0.4706,0.0464,0.0860,0.8946,2.0709,-0.3379,-0.00688,-0.00671,-0.6109,-0.2662,-0.006439,0.231541,0.2497,0.014881,568.5,-0.0479,0.3522,0.3047,0.4815,0.3946,0.7999,0.0457],
[0.30, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-0.9278, 0.0999,-0.2313,2.505,4.3844,5.6527,0.4665,0.0458,0.0860,0.8590,2.2005,-0.3314,-0.00612,-0.00598,-0.6444,-0.2405,-0.006704,0.207277,0.2674,0.014639,560.5,-0.0756,0.3438,0.3005,0.4801,0.3981,0.7997,0.0398],
[0.40, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.2176, 0.0997,-0.2146,2.261,4.4979,5.4997,0.4607,0.0445,0.0850,0.8019,2.3886,-0.3256,-0.00498,-0.00486,-0.6931,-0.1975,-0.007125,0.165464,0.3120,0.013493,540.0,-0.0960,0.3351,0.2984,0.4758,0.4036,0.7988,0.0312],
[0.50, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.4695, 0.0991,-0.1972,2.087,4.5881,5.4029,0.4571,0.0429,0.0830,0.7578,2.5000,-0.3189,-0.00420,-0.00410,-0.7246,-0.1633,-0.007435,0.133828,0.3610,0.011133,512.9,-0.0998,0.3353,0.3036,0.4710,0.4079,0.7966,0.0255],
[0.75, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-1.9278, 0.0936,-0.1620,1.812,4.7571,5.2900,0.4531,0.0387,0.0690,0.6788,2.6224,-0.2702,-0.00308,-0.00301,-0.7708,-0.1028,-0.008120,0.085153,0.4353,0.006739,441.9,-0.0765,0.3429,0.3205,0.4621,0.4157,0.7792,0.0175],
[1.0,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-2.2453, 0.0766,-0.1400,1.648,4.8820,5.2480,0.4517,0.0350,0.0450,0.6196,2.6690,-0.2059,-0.00246,-0.00241,-0.7990,-0.0699,-0.008444,0.058595,0.4629,0.005749,391.8,-0.0412,0.3577,0.3419,0.4581,0.4213,0.7504,0.0133],
[1.5,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-2.7307, 0.0022,-0.1184,1.511,5.0697,5.2194,0.4507,0.0280,0.0134,0.5101,2.6985,-0.0852,-0.00180,-0.00176,-0.8382,-0.0425,-0.007707,0.031787,0.4756,0.005544,348.1, 0.0140,0.3769,0.3703,0.4493,0.4213,0.7136,0.0090],
[2.0,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-3.1413,-0.0591,-0.1100,1.470,5.2173,5.2099,0.4504,0.0213,0.0040,0.3917,2.7085, 0.0160,-0.00147,-0.00143,-0.8663,-0.0302,-0.004792,0.019716,0.4785,0.005521,332.5, 0.0544,0.4023,0.4023,0.4459,0.4213,0.7035,0.0068],
[3.0,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-3.7413,-0.0931,-0.1040,1.456,5.4385,5.2040,0.4501,0.0106,0.0010,0.1244,2.7145, 0.1876,-0.00117,-0.00115,-0.9032,-0.0129,-0.001828,0.009643,0.4796,0.005517,324.1, 0.1232,0.4406,0.4406,0.4433,0.4213,0.7006,0.0045],
[4.0,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-4.1814,-0.0982,-0.1020,1.465,5.5977,5.2020,0.4501,0.0041,0.0000,0.0086,2.7164, 0.3378,-0.00107,-0.00104,-0.9231,-0.0016,-0.001523,0.005379,0.4799,0.005517,321.7, 0.1859,0.4784,0.4784,0.4424,0.4213,0.7001,0.0034],
[5.0,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-4.5187,-0.0994,-0.1010,1.478,5.7276,5.2010,0.4500,0.0010,0.0000,0.0000,2.7172, 0.4579,-0.00102,-0.00099,-0.9222, 0.0000,-0.001440,0.003223,0.4799,0.005517,320.9, 0.2295,0.5074,0.5074,0.4420,0.4213,0.7000,0.0027],
[7.5,  1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-5.1224,-0.0999,-0.1010,1.498,5.9891,5.2000,0.4500,0.0000,0.0000,0.0000,2.7177, 0.7514,-0.00096,-0.00094,-0.8346, 0.0000,-0.001369,0.001134,0.4800,0.005517,320.3, 0.2660,0.5328,0.5328,0.4416,0.4213,0.7000,0.0018],
[10.0, 1.06,3.45,-2.1,-0.5,50.0,3.0,4.0,-5.5872,-0.1000,-0.1000,1.502,6.1930,5.2000,0.4500,0.0000,0.0000,0.0000,2.7180, 1.1856,-0.00094,-0.00091,-0.7332, 0.0000,-0.001361,0.000515,0.4800,0.005517,320.1, 0.2682,0.5542,0.5542,0.4414,0.4213,0.7000,0.0014],
])''')
    print('')
 
    print('%s# generate coefficients for varying periods ' % indent)
    print('%sc_dict = {} ' % indent)
    print("%speriods = [('0.01', 1), ('0.20', 9), ('1.00', 15), ('3.00', 18)]" % indent)
    print('%sfor (T, i) in periods:' % indent)
    print('%s    c = array(c_tab[i][1:30])' % indent)
    print('%s    c.shape = (-1, 1, 1, 1)' % indent)
    print('%s    c_dict[T] = c' % indent)
    print('')
    print('%s# generate sigma coefficients for varying periods' % indent)
    print('%ss_dict = {}' % indent)
    print("%speriods = [('0.01', 1), ('0.20', 9), ('1.00', 15), ('3.00', 18)]" % indent)
    print('%sfor (T, i) in periods:' % indent)
    print('%s    s = array(c_tab[i][30:])' % indent)
    print('%s    s.shape = (-1, 1, 1, 1)' % indent)
    print('%s    s_dict[T] = s' % indent)
    print('')

    # now write body of tests
    print('%s# now run all tests' % indent)
    print("%smodel_name = 'Chiou08'" % indent)
    print('%smodel = Ground_motion_specification(model_name)' % indent)
    print('')

    print('%satol = 4.0E-5' % indent)
    print('%srtol = 2.0E-5' % indent)
    print('')

    for (i, case) in enumerate(cases):
        (T, M, Az, Rjb, Rrup, Rx, Fhw, Rake, Dip, Ztor, Vs30, Z25, Sa, sigma) = case

        log_Sa = math.log(Sa)

        # convert Rake value to fault_type
        (fault_type, fault_name) = rake_to_fault_type(Rake)

        print('%s# test %d: rake=%f, fault_type=%d (%s)' % (indent, i, Rake, fault_type, fault_name))
        print('%s# T=%.2f, M=%.1f, Rjb=%.1f, Rrup=%.1f, Rx=%.1f, Vs30=%.1f' % (indent, T, M, Rjb, Rrup, Rx, Vs30))
        print('%speriods = array([[[%f]]])' % (indent, T))
        print('%sdist_obj = Dist_Obj(array([[%f]]), array([[%f]]), array([[%f]]))' % (indent, Rjb, Rrup, Rx))
        print('%sDip = array([[[%f]]])' % (indent, Dip))
        print('%sZtor = array([[[%f]]])' % (indent, Ztor))
        print('%sM = array([[[%f]]])' % (indent, M))
        print('%sVs30 = array([%f])' % (indent, Vs30))
        print('%sfault_type = array([[[%d]]])' % (indent, fault_type))
        print('%sFhw = array([[%d]])' % (indent, Fhw))
        print("%scoefficient = c_dict['%.2f']" % (indent, T))
        print("%ssigma_coefficient = s_dict['%.2f']" % (indent, T))
        print('%s(log_mean, sigma) = model.distribution(periods=periods, depth_to_top=Ztor, dip=Dip, fault_type=fault_type, mag=M, dist_object=dist_obj, Vs30=Vs30,\n'
              '%s   Fhw=Fhw, coefficient=coefficient, sigma_coefficient=sigma_coefficient)'
              % (indent, indent))
        print("%smsg1 = 'log_mean: T=%.2f, M=%.1f, Rjb=%.1f, Rrup=%.1f, dip=%.1f, Ztor=%.1f, Vs30=%.1f: got=%%s, expected=[[[%f]]]' %% str(log_mean)"
              % (indent, T, M, Rjb, Rrup, Dip, Ztor, Vs30, log_Sa))
        print("%smsg2 = 'abs_delta=%%f, rel_delta=%%f' %% (abs(log_mean-%f), abs((log_mean-%f)/log_mean))" % (indent, log_Sa, log_Sa))
        print("%sself.failUnless(allclose(log_mean, array([[[%f]]]), atol=atol, rtol=rtol), msg1+'\\n'+msg2)" % (indent, log_Sa))
        print("%smsg1 = 'sigma: T=%.2f, M=%.1f, Rjb=%.1f, Rrup=%.1f, Vs30=%.1f: got=%%s, expected=[[[%f]]]' %% str(sigma)" % (indent, T, M, Rjb, Rrup, Vs30, sigma))
        print("%smsg2 = 'abs_delta=%%f, rel_delta=%%f' %% (abs(sigma-%f), abs((sigma-%f)/sigma))" % (indent, sigma, sigma))
        print("%sself.failUnless(allclose(sigma, array([[[%f]]]), atol=atol, rtol=rtol), msg1+'\\n'+msg2)" % (indent, sigma))
        print('')

    # write file footer
    print('''################################################################################

if __name__ == "__main__":
    suite = unittest.makeSuite(Test_Chiou08, 'test')
    runner = unittest.TextTestRunner()
    runner.run(suite)''')


ctl_data = read_file(CTL_data_file, Num_CTL_headers, CTL_fields)

write_code(ctl_data)

