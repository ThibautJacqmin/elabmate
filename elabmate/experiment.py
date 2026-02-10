# -*- coding: utf-8 -*-
"""Experiment helper for the eLabFTW API.

This module defines :class:`ElabExperiment`, a convenience wrapper around
remote eLabFTW experiments and their attachments, tags, steps, and comments.

@author Thibaut Jacqmin
"""

from .exceptions import InvalidStatus, InvalidCategory, InvalidTag, DeletedExperiment
import hashlib
from pathlib import Path
from typing import Any, Optional

class ElabExperiment:
    """Represents a remote eLabFTW experiment with convenience helpers."""

    def __init__(self,
                 api,
                 ID: int = None,  # use ID instead of id (python built in function)
                 **kwargs):
        """Create an experiment wrapper bound to an API client.

        Args:
            api: An :class:`ElabClient` instance.
            ID: Experiment identifier on the server.
        """
        self.api = api
        self.ID = ID
        self._cache: Optional[dict[str, Any]] = None

    def _load(self):
        """Fetch the experiment data from the server and refresh cache."""
        if self.ID is None:
            raise DeletedExperiment()
        exp = self.api.experiments.get_experiment(self.ID)
        self._cache = exp.to_dict()
        return self._cache

    def refresh(self) -> dict[str, Any]:
        """Refresh and return the cached experiment data."""
        return self._load()

    def _sync(self, updates: dict):
        """Patch experiment attributes on the server and refresh cache."""
        self.api.experiments.patch_experiment(self.ID, body=updates)
        self._load()
        
    def add_file(self, file_path: str, comment: str = "Uploaded via API"):
        """Attach a file to the experiment via a simple upload."""
        self.api.uploads.post_upload("experiments", self.ID, file=file_path, comment=comment)
        self._load()

    def upload_file(
        self,
        file_path: str,
        comment: str = "Uploaded via API",
        *,
        replace_if_exists: bool = True,
        use_hash: bool = True,
        use_filesize_fallback: bool = False,
    ) -> None:
        """
        Unified user-facing upload method.

        Default behavior is idempotent: create if missing, replace if existing,
        and avoid transfer when content is unchanged.
        """
        if replace_if_exists:
            self.upsert_file(
                file_path=file_path,
                comment=comment,
                use_hash=use_hash,
                use_filesize_fallback=use_filesize_fallback,
            )
            return
        self.add_file(file_path=file_path, comment=comment)
        
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

    @staticmethod
    def _resolve_name_from_dict(values: dict[str, int], target_id: Any) -> Optional[str]:
        """Resolve an ID to its name using a {name: id} mapping."""
        if target_id is None:
            return None
        try:
            target = int(target_id)
        except (TypeError, ValueError):
            return None
        for name, value in values.items():
            try:
                if int(value) == target:
                    return name
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _resolve_existing_id(
        selection: str | int,
        values: dict[str, int],
        invalid_exc,
    ) -> int:
        """Resolve a name or ID to a valid ID or raise."""
        if isinstance(selection, int):
            if selection in values.values():
                return selection
            raise invalid_exc(str(selection))
        selected_id = values.get(selection)
        if selected_id is None:
            raise invalid_exc(selection)
        return int(selected_id)

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
        """Return the raw uploads list for this experiment."""
        return self.api.uploads.read_uploads("experiments", self.ID)

    def list_files(self) -> list[dict[str, Any]]:
        """Return normalized metadata for all experiment uploads."""
        files = []
        for upload in self.get_files() or []:
            upload_id = self._get_attr(upload, "id")
            real_name = self._get_attr(upload, "real_name")
            display_name = self._get_attr(upload, "name", real_name)
            files.append(
                {
                    "id": upload_id,
                    "name": display_name,
                    "real_name": real_name,
                    "filesize": self._get_attr(upload, "filesize"),
                    "hash": self._get_attr(upload, "hash"),
                    "hash_algorithm": self._get_attr(upload, "hash_algorithm"),
                    "created_at": self._get_attr(upload, "created_at"),
                    "raw": upload,
                }
            )
        return files

    def get_file(self, filename: str) -> Optional[dict[str, Any]]:
        """Find one attachment by file name (matches real_name or display name)."""
        for upload in self.list_files():
            if filename in {upload.get("name"), upload.get("real_name")}:
                return upload
        return None

    def download_file(self, file_id: int, destination: str | Path) -> Path:
        """Download one upload to a local destination path."""
        destination = Path(destination)
        payload = self.api.download_upload("experiments", self.ID, int(file_id))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        return destination
    
    def add_step(self, text: str):
        """Append a step to the experiment."""
        self.api.steps.post_step("experiments", self.ID, body={"body": text})
        self._load()

    def add_comment(self, text: str):
        """Append a comment to the experiment."""
        self.api.comments.post_entity_comments("experiments", self.ID, body={"comment": text})
        self._load()

    def add_tag(self, tag: str):
        """Attach a tag to the experiment."""
        self.api.tags.post_tag("experiments", self.ID, body={"tag": tag})
        self._load()

    def remove_tag(self, tag_name: str):
        """Remove a tag reference from the experiment."""
        tags_api = getattr(self.api, "tags", None)
        if tags_api is not None and hasattr(tags_api, "read_tags") and hasattr(tags_api, "patch_tag"):
            try:
                for tag in tags_api.read_tags("experiments", self.ID) or []:
                    if self._get_attr(tag, "tag") != tag_name:
                        continue
                    tag_id = self._get_attr(tag, "id")
                    if tag_id is None:
                        break
                    tags_api.patch_tag("experiments", self.ID, int(tag_id), body={"action": "unreference"})
                    self._load()
                    return
            except Exception:
                pass
        for tag in self.tags:
            if tag == tag_name:
                self.clear_tags()
                return
        raise InvalidTag(tag_name)

    def has_tag(self, tag_name: str) -> bool:
        """Return True if a tag is present on the experiment."""
        return tag_name in self.tags

    def clear_tags(self):
        """Remove all tags from the experiment."""
        self.api.tags.delete_tag("experiments", id=self.ID)
        self._load()

    @property
    def _data(self):
        """Internal cached experiment payload."""
        if self._cache is None:
            return self._load()
        return self._cache

    @property
    def title(self):
        """Experiment title (server-backed)."""
        return self._data.get("title")

    @title.setter
    def title(self, value: str):
        self._sync({"title": value})
        
    @property
    def category(self):
        """Experiment category name or ID (server-backed)."""
        category_title = self._data.get("category_title")
        if category_title:
            return category_title
        category_id = self._data.get("category")
        try:
            resolved = self._resolve_name_from_dict(self.api.category_dict, category_id)
        except Exception:
            resolved = None
        if resolved:
            return resolved
        return str(category_id) if category_id is not None else None
    
    @category.setter
    def category(self, category_name: str | int):
        category_id = self._resolve_existing_id(
            category_name,
            self.api.category_dict,
            InvalidCategory,
        )
        self._sync({"category": category_id})

    @property
    def tags(self):
        """Experiment tags as a list of strings."""
        tags = self._data.get("tags")
        if isinstance(tags, str):
            names = [value for value in tags.split("|") if value]
            if names:
                return names

        tags_api = getattr(self.api, "tags", None)
        if tags_api is None or not hasattr(tags_api, "read_tags"):
            return []
        try:
            remote_tags = tags_api.read_tags("experiments", self.ID)
        except Exception:
            return []
        names = []
        for tag in remote_tags or []:
            name = self._get_attr(tag, "tag")
            if name:
                names.append(name)
        return names
    
    @property
    def steps(self):
        """Experiment steps as a list of strings."""
        steps = self._data.get("steps")
        if steps is not None:
            return [self._get_attr(data, "body") for data in steps if self._get_attr(data, "body") is not None]
        steps_api = getattr(self.api, "steps", None)
        if steps_api is None or not hasattr(steps_api, "read_steps"):
            return []
        try:
            remote_steps = steps_api.read_steps("experiments", self.ID)
        except Exception:
            return []
        return [self._get_attr(data, "body") for data in remote_steps or [] if self._get_attr(data, "body") is not None]
    
    @property
    def comments(self):
        """Experiment comments as a list of strings."""
        comments = self._data.get("comments")
        if comments is not None:
            return [self._get_attr(data, "comment") for data in comments if self._get_attr(data, "comment") is not None]
        comments_api = getattr(self.api, "comments", None)
        if comments_api is None or not hasattr(comments_api, "read_entity_comments"):
            return []
        try:
            remote_comments = comments_api.read_entity_comments("experiments", self.ID)
        except Exception:
            return []
        return [
            self._get_attr(data, "comment")
            for data in remote_comments or []
            if self._get_attr(data, "comment") is not None
        ]

    @property
    def main_text(self):
        """Main body text of the experiment."""
        return self._data.get("body", "")

    @main_text.setter
    def main_text(self, value: str):
        self._sync({"body": value})

    @property
    def body(self):
        """Alias for :attr:`main_text`."""
        return self.main_text

    @body.setter
    def body(self, value: str):
        self.main_text = value
        
    @property
    def status(self):
        """Experiment status name or ID (server-backed)."""
        status_title = self._data.get("status_title")
        if status_title:
            return status_title
        status_id = self._data.get("status")
        try:
            resolved = self._resolve_name_from_dict(self.api.status_dict, status_id)
        except Exception:
            resolved = None
        if resolved:
            return resolved
        return str(status_id) if status_id is not None else None
    
    @status.setter
    def status(self, status_name: str | int):
        status_id = self._resolve_existing_id(
            status_name,
            self.api.status_dict,
            InvalidStatus,
        )
        self._sync({"status": status_id})

    @property
    def creation_date(self):
        """Creation timestamp for the experiment."""
        return self._data.get("created_at")

    @property
    def last_modification(self):
        """Last modification timestamp for the experiment."""
        return self._data.get("modified_at")
    
    def __repr__(self):
        """Return a compact human-readable representation."""
        return f"""Experiment title: {self.title}
    ID: {self.ID}
    category: {self.category}
    creation date: {self.creation_date}"""

