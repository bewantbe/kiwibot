"""
KiwiBot - A Python Feishu Bot
"""

__title__ = 'KiwiBot'
__author__ = 'EddyXiao'
__license__ = 'MIT'
__version__ = '0.2.0'

# Import main components for easier access
from .kiwi_larkoapi_bot import main_ai_assistant

# Configure package-level logger
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
