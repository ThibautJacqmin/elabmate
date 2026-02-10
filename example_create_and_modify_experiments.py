# -*- coding: utf-8 -*-
"""Minimal end-to-end example for the elabmate client.

This script demonstrates how to connect to eLabFTW, create or load an
experiment, update metadata, and manage attachments.

@author Thibaut Jacqmin
"""

from datetime import datetime, timezone
from pathlib import Path

from elabmate import ElabClient

# Step 0: Generate an API key in eLabFTW and fill `elab_server.conf`.
# You can also pass an absolute path instead of this default path.
# Keep API keys private and avoid committing the config file to git.
path_to_conf_file = 'C:/Users/ThibautJacqmin/Documents/Lkb/Elab API key'
CONFIG_PATH = path_to_conf_file + '/elab_server.conf'

# Step 1: Initialize API client.
client = ElabClient(CONFIG_PATH)

# Step 2: Create a new experiment with a unique title.
title = f"elabmate demo"
exp = client.create_experiment(title=title)
# Or load an existing one:
# exp = client.load_experiment(title="My existing experiment")

# See how you can easily retrieve the experiment ID and title :
print(f"Created experiment ID={exp.ID}, title={exp.title}")

# Step 3: Update main fields.
exp.main_text = "Once upon a time..."
exp.add_step("Prepare sample and acquire data.")
exp.add_comment("Created via ElabClient example script.")

# Step 4: Add/remove tags.
exp.add_tag("api-demo")
print("Tags after add:", exp.tags)
exp.remove_tag("api-demo")
print("Tags after remove:", exp.tags)

# Step 5: Set category/status from existing values (the category must exist)
# Here as an example we pick up the first existing category
categories = client.category_dict
if categories:
    exp.category = next(iter(categories))
    print("Category:", exp.category)
# Or if you know "Simulations" is an existing category, just set: exp.category = "Simulations"

# Same story for statuses:
statuses = client.status_dict
if statuses:
    exp.status = next(iter(statuses))
    print("Status:", exp.status)
# Or if you know "In Progress" is an existing status, just set: exp.status = "In Progress"

# Step 6: Upload, replace, then download a file.
# First let us generate a dummy file as an example of attachment:
source = Path("example_attachment.txt")
source.write_text("first version", encoding="utf-8")
# Then upload it to the experiment, with a comment:
exp.upload_file(str(source), comment="example upload")
# Then update the file (it will not be duplicated, if you keep the same name):
source.write_text("second version", encoding="utf-8")
exp.upload_file(str(source), comment="example replace")

# An now you can download a file from eLabFTW like that:
meta = exp.get_file(source.name)
if meta is not None:
    download_target = Path("example_attachment_downloaded.txt")
    exp.download_file(file_id=meta["id"], destination=download_target)
    print(f"Downloaded to: {download_target}")

# Step 7: List remote attachments of an experiment:
for info in exp.list_files():
    print(f'{info["real_name"]} (id={info["id"]}, size={info["filesize"]})')

print(f"Done. Experiment URL ID: {exp.ID}")

