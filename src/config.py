import os
from dotenv import load_dotenv

_base_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_base_dir)
load_dotenv(os.path.join(_project_root, ".env"))


# Meta settings
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FACEBOOK_BASE_URL = os.getenv("FACEBOOK_BASE_URL")

# Supabase settings used by agent tools
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# WhatsApp number of the owner (used for proactive reminders)
WA_NUMBER = os.getenv("WA_NUMBER")
