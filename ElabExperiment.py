# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 15:31:59 2025

@author: ThibautJacqmin
"""

from Exceptions import InvalidStatus, InvalidCategory, InvalidTag, DeletedExperiment
import hashlib
from pathlib import Path
from typing import Any, Optional

class ElabExperiment:

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
        
    @staticmethod
    def _sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
        """Streamed sha256 to avoid loading big files in memory."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
        """Support both OpenAPI model objects (attrs) and dicts (keys)."""
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict):
            return obj.get(name, default)
        return default

    def _select_existing_upload(self, uploads: Any, real_name: str) -> Optional[Any]:
        """
        Pick the 'best' matching upload among duplicates:
        - match by real_name
        - if created_at exists, take the newest
        - else take the first match
        """
        matches = []
        for u in uploads or []:
            if self._get_attr(u, "real_name") == real_name:
                matches.append(u)
        if not matches:
            return None
        def key(u: Any) -> str:
            return self._get_attr(u, "created_at", "") or ""
        matches.sort(key=key, reverse=True)
        return matches[0]

    def upsert_file(
        self,
        file_path: str,
        comment: str = "Uploaded via API",
        *,
        use_hash: bool = True,
        use_filesize_fallback: bool = False,
    ) -> None:
        """
        Idempotent attachment:
        - If an upload with the same real_name exists and has same content -> do nothing (0 transfer)
        - Else replace existing upload (no duplication), or create if none exists.

        Notes:
        - Best case: server returns hash+hash_algorithm -> we can skip upload when identical.
        - If your server doesn't return hash, you may enable use_filesize_fallback (less safe).
        """
        file_path = str(file_path)
        real_name = Path(file_path).name
        local_size = Path(file_path).stat().st_size

        try:
            uploads = self.get_files()
        except Exception:
            uploads = None

        existing = self._select_existing_upload(uploads, real_name)
        if existing is None:
            # First time: create
            self.api.uploads.post_upload("experiments", self.ID, file=file_path, comment=comment)
            self._load()
            return

        existing_id = self._get_attr(existing, "id")
        server_hash = self._get_attr(existing, "hash")
        server_alg = (self._get_attr(existing, "hash_algorithm") or "").lower()
        server_size = self._get_attr(existing, "filesize")

        # Skip upload if identical
        if use_hash and server_hash and ("sha256" in server_alg or server_alg == ""):
            local_hash = self._sha256_file(file_path)
            if str(server_hash).lower() == local_hash.lower():
                return  # identical -> 0 transfer
        elif use_filesize_fallback and server_size is not None:
            # Optional: can avoid transfers when server doesn't expose hash,
            # but may miss changes with identical size.
            try:
                if int(server_size) == int(local_size):
                    return
            except Exception:
                pass

        # Replace existing upload (no duplication)
        if existing_id is None:
            # Worst case fallback: create new
            self.api.uploads.post_upload("experiments", self.ID, file=file_path, comment=comment)
            self._load()
            return

        # Official elabapi_python method for replace:
        # POST /experiments/{id}/uploads/{subid}
        self.api.uploads.post_upload_replace(
            "experiments",
            self.ID,
            int(existing_id),
            file=file_path,
            comment=comment,
       )
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


