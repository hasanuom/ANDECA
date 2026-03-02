

# bytes
print("-------- 8-bits --------------")
mod_val = 2**8
max_val = 2**8 -1
print('modulus = ' + str(mod_val))

x= [max_val] *20
s = sum(x)

checksum = s % mod_val
print ("sum  0x" + '%04X' % s)
print ("checksum   0x" + '%02X' % checksum)

comp =  (~checksum) & max_val
print (comp)
print ("~comp 0x" + '%02X' % comp)

twos =  (comp + 1) % mod_val

print("twos   0x" + '%02X' % twos)



final = (twos + s)  % mod_val

print('final   0x' + '%02X' % final)



# 16-bits
print("-------- 16-bits --------------")
mod_val = 2**16
max_val = 2**16 -1
print('modulus = ' + str(mod_val))

x= [max_val] *20
s = sum(x)

checksum = s % mod_val
print ("sum  0x" + '%08X' % s)
print ("checksum   0x" + '%04X' % checksum)

comp =  (~checksum) & max_val
print (comp)
print ("~comp 0x" + '%04X' % comp)

twos =  (comp + 1) % mod_val

print("twos   0x" + '%04X' % twos)



final = (twos + s)  % mod_val

print('final   0x' + '%04X' % final)