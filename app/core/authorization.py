from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy.orm import Session
from app.models.auth import User
from fastapi import HTTPException
import json
import logging

logger = logging.getLogger(__name__)

class Resource(str, Enum):
    CHAT = "chat"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    FILE = "file"
    USER = "user"
    SYSTEM = "system"

class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MODERATE = "moderate"
    ADMIN = "admin"

class Role(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class RBACPolicy:
    # Default role policies
    DEFAULT_POLICIES = {
        Role.USER: {
            Resource.CHAT: [Action.CREATE, Action.READ],
            Resource.CONVERSATION: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE],
            Resource.MESSAGE: [Action.CREATE, Action.READ],
            Resource.FILE: [Action.CREATE, Action.READ, Action.DELETE],
            Resource.USER: [Action.READ]
        },
        Role.MODERATOR: {
            Resource.CHAT: [Action.CREATE, Action.READ, Action.MODERATE],
            Resource.CONVERSATION: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.MODERATE],
            Resource.MESSAGE: [Action.CREATE, Action.READ, Action.DELETE, Action.MODERATE],
            Resource.FILE: [Action.CREATE, Action.READ, Action.DELETE, Action.MODERATE],
            Resource.USER: [Action.READ]
        },
        Role.ADMIN: {
            Resource.CHAT: [Action.CREATE, Action.READ, Action.MODERATE, Action.ADMIN],
            Resource.CONVERSATION: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.MODERATE, Action.ADMIN],
            Resource.MESSAGE: [Action.CREATE, Action.READ, Action.DELETE, Action.MODERATE, Action.ADMIN],
            Resource.FILE: [Action.CREATE, Action.READ, Action.DELETE, Action.MODERATE, Action.ADMIN],
            Resource.USER: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.SYSTEM: [Action.READ, Action.UPDATE, Action.ADMIN]
        }
    }

    def __init__(self, db: Session):
        self.db = db
        self.policies = self.DEFAULT_POLICIES.copy()

    def load_custom_policies(self):
        """Load custom policies from database"""
        try:
            # Load custom policies from database table
            # This would override or extend default policies
            pass
        except Exception as e:
            logger.error(f"Error loading custom policies: {e}")

    def check_permission(
        self,
        user: User,
        resource: Resource,
        action: Action,
        resource_owner_id: Optional[int] = None
    ) -> bool:
        """Check if user has permission to perform action on resource"""
        
        # Super admin bypass
        if user.role == Role.ADMIN and action == Action.ADMIN:
            return True

        # Get allowed actions for user's role and resource
        allowed_actions = self.policies.get(user.role, {}).get(resource, [])
        
        # Check if action is allowed
        if action not in allowed_actions:
            return False

        # Resource ownership check
        if resource_owner_id is not None:
            if resource_owner_id != user.id and user.role == Role.USER:
                return False

        return True

    def audit_action(
        self,
        user: User,
        resource: Resource,
        action: Action,
        success: bool,
        details: Dict[str, Any] = None
    ):
        """Record an audit log entry for an action"""
        from app.models.audit import AuditLog
        
        audit_entry = AuditLog(
            user_id=user.id,
            resource=resource.value,
            action=action.value,
            success=success,
            details=json.dumps(details or {})
        )
        
        self.db.add(audit_entry)
        self.db.commit()

class RBACMiddleware:
    def __init__(self, rbac: RBACPolicy):
        self.rbac = rbac

    async def __call__(self, request, call_next):
        try:
            # Get current user from request state
            user = request.state.user
            
            # Get resource and action from request path and method
            resource = self._get_resource_from_path(request.url.path)
            action = self._get_action_from_method(request.method)
            
            # Check permission
            if not self.rbac.check_permission(user, resource, action):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            # Continue with request
            response = await call_next(request)
            
            # Audit successful action
            self.rbac.audit_action(user, resource, action, True)
            
            return response
            
        except HTTPException as he:
            # Audit failed action
            if user:
                self.rbac.audit_action(user, resource, action, False, 
                                     {"error": str(he.detail)})
            raise he
        except Exception as e:
            logger.error(f"RBAC error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _get_resource_from_path(self, path: str) -> Resource:
        """Map URL path to resource type"""
        path_map = {
            "/chat": Resource.CHAT,
            "/conversations": Resource.CONVERSATION,
            "/messages": Resource.MESSAGE,
            "/files": Resource.FILE,
            "/users": Resource.USER,
            "/system": Resource.SYSTEM
        }
        
        for prefix, resource in path_map.items():
            if path.startswith(prefix):
                return resource
        return Resource.SYSTEM

    def _get_action_from_method(self, method: str) -> Action:
        """Map HTTP method to action type"""
        method_map = {
            "GET": Action.READ,
            "POST": Action.CREATE,
            "PUT": Action.UPDATE,
            "PATCH": Action.UPDATE,
            "DELETE": Action.DELETE
        }
        return method_map.get(method, Action.READ)

# Initialize RBAC
def init_rbac(db: Session) -> RBACPolicy:
    rbac = RBACPolicy(db)
    rbac.load_custom_policies()
    return rbac