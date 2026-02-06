# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 15:31:59 2025

@author: ThibautJacqmin
"""

from Exceptions import InvalidStatus, InvalidCategory, InvalidTag, DeletedExperiment

class Experiment:
    # Enfin ajouter le lock

    def __init__(self,
                 api,
                 ID: int = None,  # use ID instead of id (python built in function)
                 **kwargs):
        self.api = api
        self.ID = ID

    def _load(self):
        if self.ID is None:
            raise DeletedExperiment()
        exp = self.api.experiments.get_experiment(self.ID)
        return exp.to_dict()

    def _sync(self, updates: dict):
        self.api.experiments.patch_experiment(self.ID, body=updates)
        self._load()
        
    def add_file(self, file_path: str, comment: str = "Uploaded via API"):
        self.api.uploads.post_upload("experiments", self.ID, file=file_path, comment=comment)
        self._load()

    def get_files(self):
        return self.api.uploads.read_uploads("experiments", self.ID)
    
    def add_step(self, text: str):
        self.api.steps.post_step("experiments", self.ID, body={"body": text})
        self._load()

    def add_comment(self, text: str):
        self.api.comments.post_entity_comments("experiments", self.ID, body={"comment": text})
        self._load()

    def add_tag(self, tag: str):
        self.api.tags.post_tag("experiments", self.ID, body={"tag": tag})
        self._load()

    def remove_tag(self, tag_name: str):
        for tag in self.tags:
            if tag == tag_name:
                self.clear_tags()  # fallback: clear all, no selective delete supported
                return
        raise InvalidTag(tag_name)

    def has_tag(self, tag_name: str) -> bool:
        return any(tag.tag == tag_name for tag in self.tags)

    def clear_tags(self):
        self.api.tags.delete_tag("experiments", id=self.ID)      

    @property
    def _data(self):
        return self._load()

    @property
    def title(self):
        return self._data["title"]

    @title.setter
    def title(self, value: str):
        self._sync({"title": value})
        
    @property
    def category(self):
        return self._data["category_title"]
    
    @category.setter
    def category(self, category_name: str):
        for name, cid in self.api.category_dict.items():
            if name == category_name:
                self._sync({"category": cid})
                return
        raise InvalidCategory(category_name)

    @property
    def tags(self):
        tags = self._data['tags']
        if tags is not None:
            return tags.split('|')
    
    @property
    def steps(self):
        steps = [data['body'] for data in self._data['steps']]
        return steps if steps is not None else None
    
    @property
    def comments(self):
        return [data['comment'] for data in self._data['comments']]

    @property
    def main_text(self):
        return self._data["body"]

    @main_text.setter
    def main_text(self, value: str):
        self._sync({"body": value})
        
    @property
    def status(self):
        return self._data["status_title"]
    
    @status.setter
    def status(self, status_name: str):
        if status_name in self.api.status_dict:
            self._sync({'status': self.api.status_dict[status_name]})
        else:
            raise InvalidStatus(status_name)

    @property
    def creation_date(self):
        return self._data["created_at"]

    @property
    def last_modification(self):
        return self._data["modified_at"]
    
    def __repr__(self):
        return f"""Experiment title: {self.title}
    ID: {self.ID}
    category: {self.category}
    creation date: {self.creation_date}"""


