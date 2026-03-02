import pickle
import struct
import sys

import numpy as np
#from scipy import signal
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import filedialog as fd
import time
import pprint




def chunks(l, n):
	for i in range(0, len(l), n):
		yield l[i:i+n]

def reverse(l):
	for x in l:
		yield x[::-1]

def flatten(l):
	return [item for sublist in l for item in sublist]

def init_list_of_objects(size):
    list_of_objects = list()
    for i in range(0,size):
        list_of_objects.append( list() ) #different object reference each time
    return list_of_objects


if len(sys.argv) == 1:
	root = tk.Tk()
	root.withdraw()
	fname = fd.askopenfilename(initialdir="C:\\Users\\h43191kb\\SEMIS\\SEMIS_III\\FW")
	root.destroy()
else:
	fname = sys.argv[1]

data = []
 
with open(fname, "rb") as f:

	for line in f: 
		templine = line.split()
		nfreq=len(templine)/2
		temp = [float(i) for i in templine]
		chunk = list(chunks(temp, 1))
		pprint.pprint(chunk)

		if not data: #list is empty
			data = init_list_of_objects(len(temp))

		for k in range(0,len(temp)):

			data[k].extend(chunk[k])
		
		#chunk = list(chunks(data, 1))
		
		#pprint.pprint(data)
		#time.sleep(2)
	'''try:
		while True:
			data.append(f.readline())
	except EOFError:
		pass
'''
#gprdata = [x for x in data if type(x) == np.ndarray]
#arrS21 = np.array(gprdata)[:]
#print(data)


plt.figure()
plt.subplot(211)
plt.plot(data[2])
plt.subplot(212)
plt.plot(data[3])

'''
mddata = [x for x in data if type(x) == list]
mddata = [bytes(flatten(reverse(chunks(x, 2)))) for x in mddata]
mddata = [struct.unpack(f"{len(x)//4}f", x) for x in mddata] 
mddata = np.array(mddata)
mddata = mddata[:, ::2] + 1j * mddata[:, 1::2]

print(mddata.shape)
'''
'''
plt.figure()
plt.subplot(211)
plt.plot(mddata.real)
plt.subplot(212)
plt.plot(mddata.imag)

b, a = signal.butter(2, 0.0001, 'high')
mddataf = signal.filtfilt(b, a, mddata, axis = 0)

plt.figure()
plt.subplot(211)
plt.plot(mddataf.real)
plt.subplot(212)
plt.plot(mddataf.imag)


soil = np.mean(mddata[:10], axis = 0)
alpha = np.angle(soil)
mddata = mddata * np.exp(-1j * alpha)

plt.figure()
plt.title("Soil compensated")
plt.subplot(211)
plt.plot(mddata.real)
plt.subplot(212)
plt.plot(mddata.imag)

b, a = signal.butter(2, 0.0001, 'high')
mddata = signal.filtfilt(b, a, mddata, axis = 0)

plt.figure()
plt.subplot(211)
plt.plot(mddata.real)
plt.subplot(212)
plt.plot(mddata.imag)
'''
plt.show()

