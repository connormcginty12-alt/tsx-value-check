import runpy
runpy.run_path("record_options.py", run_name="__main__")
import shutil, os
os.makedirs("research", exist_ok=True)
shutil.copy("data/options_coverage.csv", "research/options_coverage.csv")
