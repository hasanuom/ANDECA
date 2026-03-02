import pandas as pd
import matplotlib.pyplot as plt
from os import walk
import df_helper as dfh

import md_pcb_version

#pcb = md_pcb_version.MdPcbVersion.v4_w_head
#rx_gain = md_pcb_version.MdPcbVersion.rxv_adc2volts(pcb)

#folder = './SFR_saves'
#folder = './SFR_saves/2021-12-03'
#folder = './SFR_saves/2021-12-03_mod3'
#folder = './SFR_saves/2021-12-05_new_fw'
#folder = './SFR_saves/2021-12-07_end'
#folder = '../SFR_saves/2021-12-09_bcoil'
#folder = '../SFR_saves/2021-12-09_nresnet'
#folder = '../SFR_saves/2021-12-09_nresnet_cgnd'
#folder = '../FRA_saves/2021-12-15-AC_coupled'
# folder = '../FRA_saves/2022-01-26'
#folder = '../FRA_saves/2022-01-27_lab_tests/with-coil'
##
#folder = '../FRA_saves/2022-01-27_lab_tests/test_piece'
#folder = '../FRA_saves/2022-01-27_lab_tests/test_piece_renamed_for_plot'
#folder = '../FRA_saves/2022-04-24'
folder = '../FRA_saves/2022-04-25'


files = []
for (dirpath, dirnames, filenames) in walk(folder):
    files.extend(filenames)
    break


print(files)

df = None
for filename in files:
    print(filename)
    df = dfh.DF_Helper.load_data(df, folder, filename)

df['harmonic'] = df['harmonic'].astype(int) #  this might be complex and casting it to int may give a warning -  this does not matter
df['frequency'] = df['frequency'].astype(int)


dfh.DF_Helper.transimpedance(df)
#================================================================
# Plotting
#================================================================

fig1, (ax1, ax2) = plt.subplots(2,1, sharex=True)
dfh.DF_Helper.plot_magnitude(df, ax1, 'rxv', '--', title='Magnitude')
dfh.DF_Helper.plot_phase(df, ax2, 'rxv', '--')
ax1.legend()
ax2.legend()
fig1.suptitle("Receive(flux)")



fig2, (ax1, ax2) = plt.subplots(2,1, sharex=True)
dfh.DF_Helper.plot_magnitude(df, ax1, 'txi', '-', title='Magnitude')
dfh.DF_Helper.plot_phase(df, ax2, 'txi', '-')
ax1.legend()
ax2.legend()

fig2.suptitle("Transmit current", fontsize=16)


fig_t, ax_t = plt.subplots()
dfh.DF_Helper.plot_magnitude(df, ax_t, 'trans', '--',  title='Transimpedance')
plt.legend()

plt.show()


#=====================================================================
# To excel
#=====================================================================
df_str = df.astype(str)
# strip off the parenthesis
df_str = df_str.replace(to_replace='\(', value="", regex=True)
df_str = df_str.replace(to_replace='\)', value="", regex=True)

with pd.ExcelWriter('VNA_output.xlsx') as writer:
    df_str.to_excel(writer, sheet_name='rxv', columns=dfh.DF_Helper.df_column_search(df_str, ['harmonic', 'frequency', 'rxv']))
    df_str.to_excel(writer, sheet_name='txi', columns=dfh.DF_Helper.df_column_search(df_str, ['harmonic', 'frequency', 'txi']))
    df_str.to_excel(writer, sheet_name='trans', columns=dfh.DF_Helper.df_column_search(df_str, ['harmonic', 'frequency', 'transimpedance']))

