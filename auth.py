import json
import secrets

keys_file = 'keys.json'

def load_keys()->dict:
    try:
        with open(keys_file,'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"api_key":"", "secret_key":""}
    
def is_valid_api_key(key:str)->bool:
    keys = load_keys()
    return key == keys.get("api_key")

def get_key_owner(key:str)->str:
    keys = load_keys()
    return keys.get(key,{}).get("owner","unknown")

def generate_new_key() -> str:
    return "sk-" + secrets.token_hex(16)
def add_new_key(owner:str)->str:
    key = generate_new_key()
    keys = load_keys()
    keys[key] = {"owner":owner}
    with open(keys_file,'w') as f:
        json.dump(keys,f)
    return key
