import os
from dotenv import load_dotenv

_base_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_base_dir)
load_dotenv(os.path.join(_project_root, ".env"))

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FACEBOOK_BASE_URL = os.getenv("FACEBOOK_BASE_URL")

# ClickUp settings used by agent tools
CLICK_UP_API_TOKEN = os.getenv("CLICK_UP_API_TOKEN")
CLICK_UP_BASE_URL = os.getenv("CLICK_UP_BASE_URL", "https://api.clickup.com/api/v2")
CLICKUP_LIST_ID = os.getenv("CLICKUP_LIST_ID")

# Supabase settings used by agent tools
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
