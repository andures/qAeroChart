# -*- coding: utf-8 -*-
"""
Profile Manager - Manages stored profile configurations in QGIS project
"""

from qgis.core import QgsProject
import json


class ProfileManager:
    """
    Manages profile configurations stored in the QGIS project.
    
    Profiles are stored as custom project variables with the prefix 'qaerochart_profile_'
    Each profile contains:
    - name: Display name (e.g., "MROC 09")
    - config: Full configuration dict (origin_point, runway, profile_points)
    - created: Timestamp
    - layers_visible: Whether layers are currently visible
    """
    
    PROFILE_PREFIX = "qaerochart_profile_"
    PROFILE_LIST_KEY = "qaerochart_profiles"
    
    def __init__(self):
        """Initialize profile manager."""
        self.project = QgsProject.instance()
    
    def get_all_profiles(self):
        """
        Get list of all saved profiles.
        
        Returns:
            list: List of profile metadata dicts [{'id': '...', 'name': '...', 'point_count': ...}, ...]
        """
        profile_list_json = self.project.readEntry("qAeroChart", self.PROFILE_LIST_KEY, "[]")[0]
        try:
            return json.loads(profile_list_json)
        except:
            return []
    
    def save_profile(self, profile_name, config):
        """
        Save a profile configuration to the project.
        
        Args:
            profile_name (str): Display name for the profile
            config (dict): Profile configuration
            
        Returns:
            str: Profile ID
        """
        import time
        
        # Generate unique profile ID
        profile_id = f"profile_{int(time.time() * 1000)}"
        
        # Save full config
        config_json = json.dumps(config)
        self.project.writeEntry("qAeroChart", f"{self.PROFILE_PREFIX}{profile_id}", config_json)
        
        # Get current profile list
        profiles = self.get_all_profiles()
        
        # Add new profile metadata
        profile_points = config.get('profile_points', [])
        runway = config.get('runway', {})
        
        profiles.append({
            'id': profile_id,
            'name': profile_name,
            'runway_direction': runway.get('direction', 'N/A'),
            'point_count': len(profile_points),
            'created': time.time()
        })
        
        # Save updated list
        self.project.writeEntry("qAeroChart", self.PROFILE_LIST_KEY, json.dumps(profiles))
        
        print(f"PLUGIN qAeroChart: Saved profile '{profile_name}' with ID {profile_id}")
        
        return profile_id
    
    def get_profile(self, profile_id):
        """
        Get a profile configuration by ID.
        
        Args:
            profile_id (str): Profile ID
            
        Returns:
            dict: Profile configuration or None
        """
        config_json = self.project.readEntry("qAeroChart", f"{self.PROFILE_PREFIX}{profile_id}", "")[0]
        
        if not config_json:
            return None
        
        try:
            return json.loads(config_json)
        except:
            return None
    
    def update_profile(self, profile_id, profile_name, config):
        """
        Update an existing profile.
        
        Args:
            profile_id (str): Profile ID
            profile_name (str): New display name
            config (dict): Updated configuration
            
        Returns:
            bool: True if successful
        """
        # Update config
        config_json = json.dumps(config)
        self.project.writeEntry("qAeroChart", f"{self.PROFILE_PREFIX}{profile_id}", config_json)
        
        # Update metadata in list
        profiles = self.get_all_profiles()
        profile_points = config.get('profile_points', [])
        runway = config.get('runway', {})
        
        for profile in profiles:
            if profile['id'] == profile_id:
                profile['name'] = profile_name
                profile['runway_direction'] = runway.get('direction', 'N/A')
                profile['point_count'] = len(profile_points)
                break
        
        self.project.writeEntry("qAeroChart", self.PROFILE_LIST_KEY, json.dumps(profiles))
        
        print(f"PLUGIN qAeroChart: Updated profile '{profile_name}'")
        
        return True
    
    def delete_profile(self, profile_id):
        """
        Delete a profile from the project.
        
        Args:
            profile_id (str): Profile ID
            
        Returns:
            bool: True if successful
        """
        # Remove config
        self.project.removeEntry("qAeroChart", f"{self.PROFILE_PREFIX}{profile_id}")
        
        # Remove from list
        profiles = self.get_all_profiles()
        profiles = [p for p in profiles if p['id'] != profile_id]
        self.project.writeEntry("qAeroChart", self.PROFILE_LIST_KEY, json.dumps(profiles))
        
        print(f"PLUGIN qAeroChart: Deleted profile {profile_id}")
        
        return True
    
    def get_profile_display_name(self, profile_metadata):
        """
        Generate a display name for the profile list.
        
        Args:
            profile_metadata (dict): Profile metadata
            
        Returns:
            str: Formatted display name
        """
        name = profile_metadata.get('name', 'Unnamed')
        runway = profile_metadata.get('runway_direction', 'N/A')
        points = profile_metadata.get('point_count', 0)
        
        return f"✈️ {name} ({runway}) - {points} points"
