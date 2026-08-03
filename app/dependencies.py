from fastapi import Header, HTTPException, status

def get_current_user(
    x_user_id: str = Header(..., description="User Identifier"),
    x_user_role: str = Header(..., description="User Role (admin or customer)")
):
    if x_user_role not in ("admin", "customer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role must be either 'admin' or 'customer'."
        )
    return {"id": x_user_id, "role": x_user_role}
