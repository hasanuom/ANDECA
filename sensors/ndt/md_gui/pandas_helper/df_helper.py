import re

import numpy as np
import pandas as pd
from matplotlib import colors as mcolors


class DF_Helper:

    @staticmethod
    def load_data(df, folder, filename):

        m = re.search(r"\d", filename)
        id_str = filename[m.start()+1:-4]
        print(id_str)
        print(folder + filename)
        df_temp = pd.read_pickle(folder + '/' + filename)
        #df_temp.pop('harmonic')  # remove duplicate harmonic column
        df_temp = df_temp.rename(columns={"harmonic": "harmonic", "rxv": "rxv{:s}".format(id_str), "txi": "txi{:s}".format(id_str)})

        if df is not None:
            if "harmonic" in df.columns:
                df_temp.pop('harmonic')  # remove duplicate harmonic column
            df = df.join(df_temp)  # create new object
        else:
            df = df_temp
        df = df.T.drop_duplicates().T

        if len(DF_Helper.df_column_search(df, 'frequency')) == 0:
            df = DF_Helper.insert_frequency(df, 'harmonic', 1e6/1024)

        return df

    @staticmethod
    def insert_frequency(df, harmonic_str, harmonic_hz):
        idx = df.columns.get_loc(harmonic_str)
        h = np.abs(df[harmonic_str])
        h = h * harmonic_hz
        df.insert(idx+1, 'frequency', h)
        return df


    @staticmethod
    def transimpedance(df):
        #rxv = list(filter(lambda filt: filt[0:3] == "rxv", df.columns))
        rxv = DF_Helper.df_column_search(df, "rxv")
        txi = DF_Helper.df_column_search(df, "txi")
        #txi = list(filter(lambda filt: filt[0:3] == "txi", df.columns))

        #print(rxv)
        #print(txi)

        for count, s in enumerate(rxv):
            trans_str = 'trans' + s[3:]
            print(trans_str)
            v = df[rxv[count]].to_numpy()
            i = df[txi[count]].to_numpy()

            #df[trans_str] = np.abs(df[rxv[count]]) / np.abs(df[txi[count]])
            df[trans_str] = np.abs(v / i)

    @staticmethod
    def df_column_search_single(df: pd.DataFrame, pattern: str):
        length = len(pattern)
        return list(filter(lambda f: f[0:length] == pattern, df.columns))


    @staticmethod
    def df_column_search(df: pd.DataFrame, pattern_list: list):
        if type(pattern_list) is not list:
            pattern_list=[pattern_list]
        op = []
        for item in pattern_list:
            op += DF_Helper.df_column_search_single(df, item)

        print(op)
        return op


    @staticmethod
    def plot_magnitude(df, ax, start_str, linestyle, title: str = ''):
        colors = mcolors.TABLEAU_COLORS
        color_name = list(colors.values())
        s1 = list(filter(lambda filt: filt[0:len(start_str)] == start_str, df.columns))
        print(s1)

        h = np.real(df['harmonic'].to_numpy())
        for count, s in enumerate(s1):
            c = color_name[count % len(color_name)]

            ax.plot(h, np.abs(df[s]), label=s, linestyle=linestyle,color=c )

        ax.set_title(title)
        ax.grid(visible=True)

    @staticmethod
    def plot_phase(df, ax, start_str, linestyle):
        s1 = list(filter(lambda filt: filt[0:len(start_str)] == start_str, df.columns))
        print(s1)
        _unwrap = True

        h = np.real(df['harmonic'].to_numpy())
        for s in s1:
            ph= np.angle(df[s])
            if _unwrap:
                ph = np.unwrap(ph)

            # convert to degrees
            ph = np.rad2deg(ph)
            ax.plot(h, ph, label=s, linestyle=linestyle)
        ax.set_title('Phase')
        ax.grid(visible=True)
