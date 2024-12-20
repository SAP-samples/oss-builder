#! /usr/local/bin/python3

import sys
import subprocess
import os

args = sys.argv[1:]
# create the folder result if it does not exist yet
if not os.path.exists('/result'):
    os.makedirs('/result')

new_command = ['codeql', 'database', 'create', '/home/db', '--language=cpp',
               '--command', ' '.join(args)]
p = subprocess.run(new_command, capture_output=True, text=True)
print('stdout:')
print(p.stdout)
print('stderr:')
print(p.stderr)
p = subprocess.run(['ls', '/home/db',], capture_output=True, text=True)
print('stdout:')
print(p.stdout)
print('stderr:')
print(p.stderr)
# move the database to the result folder
p = subprocess.run(['mv', '/home/db', '/result/asdf'], capture_output=True,
                   text=True)
print('stdout:')
print(p.stdout)
print('stderr:')
print(p.stderr)

p = subprocess.run(['ls', '/result'], capture_output=True, text=True)
print('stdout:')
print(p.stdout)
print('stderr:')
print(p.stderr)
