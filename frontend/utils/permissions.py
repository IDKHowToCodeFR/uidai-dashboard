def has_permission(permissions: list, required_permission: str) -> bool:
    if not permissions:
        return False
    return required_permission in permissions
