# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 18:05:23 2025

@author: ThibautJacqmin
"""

from ElabClient import ElabClient

# Step 0: Generate an API key in ElabFTW, find the server address,
# fill elab_server.conf file and put it in path_to_conf_file

# Step 1: Initialize the API client (uses env vars API_KEY, API_HOST_URL)
path_to_conf_file = ''
client = ElabClient(path_to_conf_file + '/elab_server.conf')

# Step 2: Create a new experiment
exp = client.create_experiment(title='Random experiment') # First time you run the code
#exp = client.load_experiment(title='Experiment test') # Once experiment created you can just load it to modify it

print(exp)  # Should show experiment ID and title

# Step 3: Modify title and tags (auto-syncs to server)
exp.title = "Experiment test"
exp.add_tag("updated")
exp.remove_tag("updated")
exp.steps
exp.add_step("bla")
exp.main_text = "Once upon a time"
exp.add_file(r"", comment="initial dataset upload")
exp.add_comment("Les sanglots longs des violons de l'automne")
exp.category = "Dummy"
client.category_dict
# Step 5: List attached files
for f in exp.get_files():
    print(f"{f.real_name} (id={f.id})")



