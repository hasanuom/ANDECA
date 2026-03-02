# -*- coding: utf-8 -*-
"""
Created on Fri Nov 29 15:18:12 2019

@author: h43191kb
"""


import numpy as np

class Transimpedance_StatisticsCalculation():

    def __init__(self, nfreq, nvarpoints):
        super().__init__()
        self.nfreq = nfreq
        self.nvarpoints = nvarpoints
        self.nvarpoints_cnt = 0
        self.display_str = ''
        self.varpoints = []
        self.covarresult = []
        self.mean = []

        for x in range(0, self.nfreq):
            self.varpoints.append([])
            self.covarresult.append([])
            self.mean.append([])

    def mean_calc(self, val):
        if type(val) is not np.array:
            val = np.asarray(val, dtype=np.float32)
        # print('mean:')
        # print(val)

        self.mean = np.mean(val, axis=0)

        return self.mean

    def variance_calc(self, val):
        if type(val) is not np.array:
            val = np.asarray(val, dtype=np.float32)

        self.v = np.var(val, axis=0)

        return self.v

    def covar_calc(self,  xval, yval):

        if type(xval) is not np.array:
            xval = np.asarray(xval, dtype=np.float32)

        if type(yval) is not np.array:
            yval = np.asarray(yval, dtype=np.float32)

        temp = np.array([xval, yval])
        self.covarresult = np.cov(temp, rowvar=True, bias=True)

        return self.covarresult

    def mean_calc(self, val):
        if type(val) is not np.array:
            val = np.asarray(val, dtype=np.float32)

        self.mean = np.mean(val, axis=0)

        return self.mean
