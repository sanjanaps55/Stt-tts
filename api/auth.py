from .database import get_supabase

def is_valid_api_key(key: str) -> bool:
    if key == "playground-key":
        return True
        
    supabase = get_supabase()
    response = supabase.table("api_keys").select("id").eq("api_key", key).execute()
    is_valid = len(response.data) > 0
    
    return is_valid

def get_key_owner(key: str) -> str:
    if key == "playground-key":
        return "playground_user"
        
    supabase = get_supabase()
    response = supabase.table("api_keys").select("owner").eq("api_key", key).execute()
    owner = "unknown"
    if len(response.data) > 0:
        row = response.data[0]
        if isinstance(row, dict) and "owner" in row:
            owner = str(row["owner"])
            
    return owner

def generate_new_key() -> str:
    import secrets
    return "sk-" + secrets.token_hex(16)

def add_new_key(owner: str) -> str:
    key = generate_new_key()
    supabase = get_supabase()
    supabase.table("api_keys").insert({"api_key": key, "owner": owner}).execute()
    return key

def get_keys_for_owner(owner: str) -> list[str]:
    supabase = get_supabase()
    response = supabase.table("api_keys").select("api_key").eq("owner", owner).execute()
    return [row["api_key"] for row in response.data]
