"""
Group management service for handling group operations.

This service manages:
- Group creation and management
- Group member management
- Group settings and metadata
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional
import sys
import os

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat_redis.redis_client import redis_client
from models.message import Group, GroupCreate, GroupUpdate


class GroupService:
    """
    Service class for group management using Redis.
    """
    
    def __init__(self):
        self.redis_client = redis_client
    
    def _generate_group_id(self, name: str, creator: str) -> str:
        """Generate unique group ID."""
        return f"group_{uuid.uuid4().hex[:8]}"
    
    def _generate_group_image(self, name: str) -> str:
        """Generate default group image URL."""
        return f"https://ui-avatars.com/api/?name={name}&background=6c5ce7&color=fff&size=150"
    
    async def create_group(self, group_data: GroupCreate) -> Optional[Group]:
        """
        Create a new group.
        
        Args:
            group_data: Group creation data
            
        Returns:
            Group: Created group object or None if failed
        """
        try:
            group_id = self._generate_group_id(group_data.name, group_data.created_by)
            
            group = Group(
                id=group_id,
                name=group_data.name,
                description=group_data.description,
                image_url=group_data.image_url or self._generate_group_image(group_data.name),
                created_by=group_data.created_by,
                created_at=datetime.utcnow(),
                members=[group_data.created_by],
                admins=[group_data.created_by]
            )
            
            # Store group in Redis
            group_key = f"group:{group_id}"
            group_json = group.model_dump_json()
            self.redis_client.set(group_key, group_json)
            
            # Add to groups list
            self.redis_client.sadd("groups:all", group_id)
            
            # Add user to group members
            self.redis_client.sadd(f"user:{group_data.created_by}:groups", group_id)
            
            return group
            
        except Exception as e:
            print(f"Error creating group: {e}")
            return None
    
    async def get_group(self, group_id: str) -> Optional[Group]:
        """
        Get group by ID.
        
        Args:
            group_id: Group ID to lookup
            
        Returns:
            Group: Group object if found, None if not found
        """
        try:
            group_key = f"group:{group_id}"
            group_json = self.redis_client.get(group_key)
            
            if not group_json:
                return None
            
            group_dict = json.loads(group_json)
            group_dict['created_at'] = datetime.fromisoformat(group_dict['created_at'])
            
            return Group(**group_dict)
            
        except Exception as e:
            print(f"Error getting group: {e}")
            return None
    
    async def update_group(self, group_id: str, update_data: GroupUpdate, updated_by: str) -> Optional[Group]:
        """
        Update group information.
        
        Args:
            group_id: Group ID to update
            update_data: Update data
            updated_by: Username of user making the update
            
        Returns:
            Group: Updated group object or None if failed
        """
        try:
            group = await self.get_group(group_id)
            if not group:
                return None
            
            # Check if user is admin
            if updated_by not in group.admins:
                return None
            
            # Update fields
            if update_data.name is not None:
                group.name = update_data.name
            if update_data.description is not None:
                group.description = update_data.description
            if update_data.image_url is not None:
                group.image_url = update_data.image_url
            
            # Save updated group
            group_key = f"group:{group_id}"
            group_json = group.model_dump_json()
            self.redis_client.set(group_key, group_json)
            
            return group
            
        except Exception as e:
            print(f"Error updating group: {e}")
            return None
    
    async def add_member(self, group_id: str, username: str, added_by: str) -> bool:
        """
        Add member to group.
        
        Args:
            group_id: Group ID
            username: Username to add
            added_by: Username of user adding the member
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            group = await self.get_group(group_id)
            if not group:
                return False
            
            # Check if user is admin
            if added_by not in group.admins:
                return False
            
            # Add member if not already in group
            if username not in group.members:
                group.members.append(username)
                
                # Save updated group
                group_key = f"group:{group_id}"
                group_json = group.model_dump_json()
                self.redis_client.set(group_key, group_json)
                
                # Add group to user's groups
                self.redis_client.sadd(f"user:{username}:groups", group_id)
            
            return True
            
        except Exception as e:
            print(f"Error adding member: {e}")
            return False
    
    async def remove_member(self, group_id: str, username: str, removed_by: str) -> bool:
        """
        Remove member from group.
        
        Args:
            group_id: Group ID
            username: Username to remove
            removed_by: Username of user removing the member
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            group = await self.get_group(group_id)
            if not group:
                return False
            
            # Check if user is admin or removing themselves
            if removed_by not in group.admins and removed_by != username:
                return False
            
            # Remove member
            if username in group.members:
                group.members.remove(username)
                
                # Remove from admins if they were admin
                if username in group.admins:
                    group.admins.remove(username)
                
                # Save updated group
                group_key = f"group:{group_id}"
                group_json = group.model_dump_json()
                self.redis_client.set(group_key, group_json)
                
                # Remove group from user's groups
                self.redis_client.srem(f"user:{username}:groups", group_id)
            
            return True
            
        except Exception as e:
            print(f"Error removing member: {e}")
            return False
    
    async def get_user_groups(self, username: str) -> List[Group]:
        """
        Get all groups for a user.
        
        Args:
            username: Username to get groups for
            
        Returns:
            List[Group]: List of groups user belongs to
        """
        try:
            group_ids = self.redis_client.smembers(f"user:{username}:groups")
            groups = []
            
            for group_id in group_ids:
                group = await self.get_group(group_id)
                if group:
                    groups.append(group)
            
            return groups
            
        except Exception as e:
            print(f"Error getting user groups: {e}")
            return []
    
    async def get_all_groups(self) -> List[Group]:
        """
        Get all groups.
        
        Returns:
            List[Group]: List of all groups
        """
        try:
            group_ids = self.redis_client.smembers("groups:all")
            groups = []
            
            for group_id in group_ids:
                group = await self.get_group(group_id)
                if group:
                    groups.append(group)
            
            return groups
            
        except Exception as e:
            print(f"Error getting all groups: {e}")
            return []


# Create global instance
group_service = GroupService()