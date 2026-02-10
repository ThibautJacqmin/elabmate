# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 18:05:23 2025

@author: ThibautJacqmin
"""

from datetime import datetime, timezone
from pathlib import Path

from elabmate import ElabClient

# Step 0: Generate an API key in ElabFTW and fill `elab_server.conf`.
# You can also pass an absolute path instead of this default.
path_to_conf_file = 'C:/Users/ThibautJacqmin/Documents/Lkb/Elab API key'
CONFIG_PATH = path_to_conf_file + '/elab_server.conf'

# Step 1: Initialize API client
client = ElabClient(CONFIG_PATH)

# Step 2: Create a new experiment with a unique title
title = f"API demo {datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
exp = client.create_experiment(title=title)
# Or load an existing one:
# exp = client.load_experiment(title="My existing experiment")

print(f"Created experiment ID={exp.ID}, title={exp.title}")

# Step 3: Update main fields
exp.main_text = "Once upon a time..."
exp.add_step("Prepare sample and acquire data.")
exp.add_comment("Created via ElabClient example script.")

# Step 4: Tags
exp.add_tag("api-demo")
print("Tags after add:", exp.tags)
exp.remove_tag("api-demo")
print("Tags after remove:", exp.tags)

# Step 5: Set category/status from existing values
categories = client.category_dict
if categories:
    exp.category = next(iter(categories))
    print("Category:", exp.category)

statuses = client.status_dict
if statuses:
    exp.status = next(iter(statuses))
    print("Status:", exp.status)

# Step 6: Upload, replace, then download a file
source = Path("example_attachment.txt")
source.write_text("first version", encoding="utf-8")
exp.upload_file(str(source), comment="example upload")

source.write_text("second version", encoding="utf-8")
exp.upload_file(str(source), comment="example replace")

meta = exp.get_file(source.name)
if meta is not None:
    download_target = Path("example_attachment_downloaded.txt")
    exp.download_file(file_id=meta["id"], destination=download_target)
    print(f"Downloaded to: {download_target}")

# Step 7: List files
for info in exp.list_files():
    print(f'{info["real_name"]} (id={info["id"]}, size={info["filesize"]})')

print(f"Done. Experiment URL ID: {exp.ID}")

