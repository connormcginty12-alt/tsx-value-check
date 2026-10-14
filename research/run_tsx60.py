import os, runpy, shutil
os.chdir('.'); runpy.run_path('update_tsx60.py', run_name='__main__')
if os.path.exists('tsx60_members.csv'): shutil.copy('tsx60_members.csv', 'research/tsx60_members.csv')
