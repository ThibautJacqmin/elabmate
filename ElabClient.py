# -*- coding: utf-8 -*-
"""
Created on Wed Apr 16 15:29:35 2025

@author: ThibautJacqmin
"""

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import elabapi_python as ep
from functools import wraps
from Experiment import Experiment
from Exceptions import InvalidTemplate, InvalidTitle, InvalidID, DuplicateTitle

class ElabClient:
    def __init__(self, config_path: str = "elab_server.conf"):
        
        # Read and parse configuration file
        self.config = self._read_configuration_file(config_path)
        
        # API configuration
        self._api_configuration() 
        
        # Load useful API objects
        self.experiments = ep.ExperimentsApi(self.api_client)
        self.uploads = ep.UploadsApi(self.api_client)
        self.steps = ep.StepsApi(self.api_client)
        self.comments = ep.CommentsApi(self.api_client)
        self.categories = ep.ExperimentsCategoriesApi(self.api_client)
        self.statuses = ep.ExperimentsStatusApi(self.api_client)
        self.templates = ep.ExperimentsTemplatesApi(self.api_client)
        self.tags = ep.TagsApi(self.api_client)
                       
    
    def load_experiment(self, ID: int=None, title: str=None):
        # Loads Experiment object from ID or title
        if title is not None: 
            if self._has_title(title):
                ID = self.experiments_dict[title]
            else:
                raise InvalidTitle(title)                
        if ID is not None:
            if self._has_ID(ID):
                experiment = Experiment(self, ID=ID)
                experiment._load()
                return experiment
            else: 
                raise InvalidID(ID)  
  

    def experiment_creation_wrapper(func):
        @wraps(func)
        def wrapper(self, title: str, category: int = None, **kwargs):
            if self._has_title(title) and self.enforce_unique_titles:
                raise DuplicateTitle(title)
            headers = func(self, title=title, category=category, **kwargs)
            ID = int(headers['Location'].split("/")[-1])
            experiment = Experiment(self, ID)
            experiment._load()
            experiment.title = title
            if category is not None:
                experiment.category = category
            return experiment
        return wrapper

    
    @experiment_creation_wrapper
    def create_experiment(self, title: str, category: int = None):
        _, _, headers = self.experiments.post_experiment_with_http_info(body={"title": title})
        return headers

    @experiment_creation_wrapper
    def create_experiment_from_template(self, title: str, template_name: str, category: int = None):
        template_id = self._get_template_id(name=template_name)
        if template_id is None:
            raise InvalidTemplate
        _, _, headers = self.experiments.post_experiment_with_http_info(body={"template": template_id})
        return headers

    @property
    def experiments_dict(self) -> dict[str, int]:
        # This method returns a dictionnary containing titles as keys
        # and ids as values {title: id}
        self.experiments_list = self.experiments.read_experiments()
        return {exp.title: exp.id for exp in self.experiments_list}      
    
    @property
    def category_dict(self) -> dict[str: int]:
        # Returns all possible categories in a dictionary {category_name: category_id}
        cats = self.categories.read_team_experiments_categories("experiments")
        return {cat.title:cat.id for cat in cats}
    
    @property
    def status_dict(self) -> dict[str: int]:
        # Returns all possible statuses in a dictionary {status_name: status_id}
        return {s.title: s.id for s in self.statuses.read_team_experiments_status("experiments")}
    
    def _get_template_id(self, name: str) -> int:
        templates = self.templates.read_experiments_templates()
        for t in templates:
            if t.title == name:
                return t.id
        return None
    
    def _has_title(self, title: str) -> bool:
        # Checks if title already exists
        return title in self.experiments_dict
     
    def _has_ID(self, ID: str) -> bool:
        # Checks if ID already exists
        return ID in self.experiments_dict.values()
    
    def _api_configuration(self):
        # Configures the API
        self.configuration = ep.Configuration()
        self.configuration.host = self.config["API_HOST_URL"]
        self.configuration.api_key['api_key'] = self.config["API_KEY"]
        self.configuration.api_key_prefix['api_key'] = 'Authorization'
        self.configuration.verify_ssl = self.config['VERIFY_SSL'].lower() == "true"
        self.api_client = ep.ApiClient(self.configuration)
        self.api_client.set_default_header(header_name='Authorization', header_value=self.configuration.api_key['api_key'])
        self.enforce_unique_titles = self.config["UNIQUE_EXPERIMENTS_TITLES"].lower() == "true"
            
    @staticmethod
    def _read_configuration_file(config_path: str)-> dict[str, str]:
        # Reads and parse configuration file, returns dictionnary
        config = {}
        with open(config_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    config[key] = value
        return config
    





        
    


        
