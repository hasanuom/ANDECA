
import unittest

import transimpendance_analysis


class TestTransimpedance_analysis(unittest.TestCase):
    '''
    def test_Transimpedance_analysis(self):
        x=[1,3,5]
        y=[-1,-2,3]
        npoint = len(x)
        nfreq=1

        tc = transimpendance_analysis.Transimpedance_CovarianceCalculation(nfreq, npoint)
        op = tc.covar_calc(x, y)
        print(op)
        self.assertEqual('rubbish', op)

    def test_Transimpedance_analysis_var(self):
        x=[1,3,5]
        y=[-1,-2,3]
        npoint = len(x)
        nfreq=1
        tc = transimpendance_analysis.Transimpedance_CovarianceCalculation(nfreq, npoint)
        
        op = tc.variance_calc(x)
        
        self.assertEqual(123, op)
    '''
    
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


    def test_Transimpedance_analysis_mean(self):
        x=[1,3,5]
        y=[-1,-2,3]
        npoint = len(x)
        nfreq=1
        tc = transimpendance_analysis.Transimpedance_CovarianceCalculation(nfreq, npoint)
        
        op = tc.mean_calc(x)
        
        self.assertEqual(123, op)


if __name__ == '__main__':
    unittest.main()



