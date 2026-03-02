# -*- coding: utf-8 -*-
"""
Created on Fri Nov 29 15:15:56 2019

@author: h43191kb
"""



import unittest
import numpy as np
import numpy.testing as nt

import transimpendance_analysis as ta


class test_mdserial(unittest.TestCase):

    def test_covar(self):
        nfreq = 3
        nvarpoints = 4

        datax=np.array([[2, 5,-5,],[2, 5,-5], [2, 5,-5], [3,-2, 1]])
        datay=np.array([[3,-2, 1], [2, 5,-5], [2, 5,-5], [3,-2, 1]])


        print(datax[0,:])
        print(datax[:,0])

        ta_inst = ta.Transimpedance_CovarianceCalculation(nfreq, nvarpoints)

        covar = ta_inst.covar_calc(datax, datay)

        print("\n")
        for i in range(0, nfreq):
            print("Covariance - Freq idx: " + str(i))
            print(covar[i])
            print("\n")

        # calculate variances for comparision

        for i in range(0, nfreq):
            # print("Variance - Freq idx: " + str(i))
            temp = datax[:,i]
            varx=np.var(temp)
            # print(varx)
            # print(np.cov(temp, temp, rowvar=True, bias=True))
            np.testing.assert_almost_equal(covar[i][0][0], varx, decimal=3)


    
    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()




import numpy as np







