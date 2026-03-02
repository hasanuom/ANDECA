import sys
import unittest
import numpy as np
import numpy.testing as nt
sys.path.append("C:/Users/h43191kb/gitlab/md_gui/md_gui")

import md_data_handle


class test_mdserial(unittest.TestCase):

    def setUp(self):
        self.sr_len=4
        self.n_harmonics=3
        self.mdh = md_data_handle.MdDataHandle(n_harmonics=self.n_harmonics, sr_len=self.sr_len)
        print("setting up")

    def tearDown(self):
        try:
            del self.mdh
        except:
            print("error")

    def test_class_init(self):

        inst = md_data_handle.MdDataHandle(sr_len=4)
        inst.hello()

    def test_class_data_init(self):

        inst = md_data_handle.MdDataHandle(n_harmonics= 3, sr_len=4)
        inst.print_data()

    def test_update_series_enable(self):
        sr_len=4
        n_harmonics=3

        names= ['bobo', 'alice', 'steve', 'stevo']
        inst = md_data_handle.MdDataHandle(n_harmonics=n_harmonics, sr_len=sr_len)
        enables = [False] * n_harmonics
        #print(enables)
        
        enables[0] = True
        enables[2] = True
        #print(enables)
        inst.update_series_enables(enables, names)

    def test_update_data_1(self):

        names= ['bobo', 'alice', 'steve', 'stevo']
        enables = [False] * n_harmonics
        
        enables[0] = True
        enables[2] = True
        #print(enables)
        self.mdh.update_series_enables(enables, names)
        data_x = [1] * n_harmonics
        data_y = [3] * n_harmonics
        self.mdh.update_data(data_x, data_y)


    def test_update_data_1(self):
        names= ['bobo', 'alice', 'steve', 'stevo']
        enables = [False] * self.n_harmonics

        
        enables[0] = True
        enables[2] = True

        #print(enables)
        self.mdh.update_series_enables(enables, names)
        data_x = [1] * self.n_harmonics
        data_y = [3] * self.n_harmonics
        self.mdh.update_data(data_x, data_y)


    def test_update_data_2(self):
        names= ['bobo', 'alice', 'steve', 'stevo']
        enables = [False] * self.n_harmonics

        enables[0] = True
        enables[2] = True

        data_x=[]
        data_y=[]

        #print(enables)
        self.mdh.update_series_enables(enables, names)
        for i in range(2): # enables
            for k in range(10):
                data_x = [k+1] * 2
                data_y = [(k+1)*2]  * 2
                self.mdh.update_data(data_x, data_y)




    
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