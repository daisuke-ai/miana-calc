import os
import streamlit as st
from supabase import create_client, Client
import hashlib

# Supabase Initialization
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_API"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_cached_data(address_hash: str):
    try:
        response = supabase.table("api_cache").select("payload_json").eq("address_hash", address_hash).execute()
        if response.data and response.data[0]['payload_json']:
            return response.data[0]['payload_json']
    except Exception as e:
        print(f"Error checking Supabase cache: {e}")
    return None

def cache_data(address_hash: str, payload_json: dict):
    try:
        supabase.table("api_cache").insert({"address_hash": address_hash, "payload_json": payload_json}).execute()
        print(f"-> Data for {address_hash} cached in Supabase.")
    except Exception as e:
        print(f"Error caching data to Supabase: {e}") 