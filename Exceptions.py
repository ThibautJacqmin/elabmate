# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 17:45:25 2025

@author: ThibautJacqmin
"""

class ElabException(Exception):
    """Base exception for ElabFTW integration."""
    pass

class DuplicateTitle(ElabException):
    def __init__(self, title: str):
        super().__init__(f"An experiment with title '{title}' already exists.")

class InvalidTemplate(ElabException):
    def __init__(self, name: str):
        super().__init__(f"Template named '{name}' not found.")

class InvalidTitle(ElabException):
    def __init__(self, title: str):
        super().__init__(f"{title} does not exist")

class InvalidID(ElabException):
    def __init__(self, ID: str):
        super().__init__(f"{ID} does not exist")

class InvalidTag(ElabException):
    def __init__(self, name: str):
        super().__init__(f"Tag '{name}' not found.")

class InvalidCategory(ElabException):
    def __init__(self, name: str):
        super().__init__(f"Category '{name}' not found.")

class InvalidStatus(ElabException):
    def __init__(self, name: str):
        super().__init__(f"Status '{name}' not found.")
        
class DeletedExperiment(ElabException):
    def __init__(self):
        super().__init__("Deleted experiment")        
