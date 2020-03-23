import flask, json, pdb

msg = {'X23':{'x':1, 'y':1}}
for key in msg:
    for value in msg[key]:
        print(key, value, msg[key][value])
