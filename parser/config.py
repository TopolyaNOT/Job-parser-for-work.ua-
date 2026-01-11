import os
from dotenv import load_dotenv
from fake_useragent import UserAgent

load_dotenv()


USER_AGENT = {"user-agent": UserAgent().random}

PAGE_URL = 'https://www.work.ua/jobs-kyiv-it-industry-it/'

PROCESSED_IDS_PATH = "checkpoints/done_ids.txt"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
IA_PROCCES = True

TEST_MODE = False
TEST_PAGES = 1