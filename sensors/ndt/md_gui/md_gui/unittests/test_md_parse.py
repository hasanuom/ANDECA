
import sys
import unittest
import numpy as np
import numpy.testing as nt
sys.path.append("C:/Users/h43191kb/gitlab/md_gui/md_gui")

import parse_packet


class test_mdserial(unittest.TestCase):

    def test_bytes_to_float_vector_single(self):
        #byte_array = b'00409a44'
        byte_array = bytearray(b'\x01\x40\x9a\x44')
        #byte_array = bytearray(b'00409a44')
        print(byte_array)
        op = parse_packet.ParsePacket._bytes_to_float_vector(byte_array)
        self.assertAlmostEqual(1234.0, op[0], places=3)


    def test_bytes_to_float_vector_two(self):
       
        #byte_array = b'00409a44'
        byte_array = bytearray(b'\x01\x40\x9a\x44\x01\x40\x9a\x44')
        #byte_array = bytearray(b'00409a44')
        print(byte_array)
        op = parse_packet.ParsePacket._bytes_to_float_vector(byte_array)
        nt.assert_almost_equal(np.array([1234.0, 1234.0]), op, decimal=3)



    
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