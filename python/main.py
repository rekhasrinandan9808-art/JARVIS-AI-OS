#!/usr/bin/env python
"""
JARVIS AI OS v21.04.08 - Main Entry Point
REAL OS CONTROL • LLM ONLY FOR THINKING
MULTI-USER SUPPORT • LOCATION-BASED TIME ZONES
FIXES:
- Blank tab opening fixed - only opens if index.html exists
- Browser URL opening capability added
- Continuous voice mode enhanced with AI compatibility
- Memory integration for continuous voice
- Auto-start continuous voice mode
- INTERRUPTION HANDLING: User can interrupt JARVIS while speaking
- 30-SECOND SILENCE: JARVIS waits 30s before proactive greetings
- CONVERSATION MEMORY: Full context retention
- CONTEXTUAL AI: Logical responses based on conversation history
- WEBSOCKET ERROR FIX: Graceful handling of invalid HTTP requests
- SPEAKING ERROR FIX: Fixed dict attribute access in speak_text
- REMINDER SYSTEM: Set reminders with voice alerts
- NOTIFICATION SYSTEM: Track and read notifications from apps
- FIX: store_conversation handles both AgentResult objects and dictionaries
- FILESYSTEM AGENT: Full drive access, file operations, cross-drive support
- MULTI-USER SUPPORT: Each user gets own profile with timezone
- LOCATION-BASED TIME: Time displayed according to user's location
- FIX: Context-Aware Injection Cleanup in IntentRouter
- FIX: Greedy Regex Fix for memory patterns
- FIX: Dict vs Object Handling in store_conversation
- SHUTDOWN: Complete system shutdown with PC power off option
- FIX: File creation on specific drives (C:, D:, etc.) now works correctly
- FIX: Voice mode file creation routes to FileSystemAgent not DesktopController
- FIX: PC shutdown now properly executes system shutdown command
"""

# Force load .env FIRST
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️ .env not found at {env_file}")
except ImportError:
    print("⚠️ python-dotenv not installed. Run: pip install python-dotenv")

# Now import everything else
import asyncio
import logging
import json
import re
import threading
import random
import time
import websockets
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import pytz
from dateutil import tz

from moa.orchestrator import Orchestrator
from moa.planner import Planner
from moa.workflow_registry import WorkflowRegistry
from agents.voice.agent import VoiceAgent
from agents.memory.agent import MemoryAgent

# =================================================
# FILESYSTEM AGENT IMPORT
# =================================================
from agents.filesystem.agent import FileSystemAgent

# =================================================
# SUPPRESS WEBSOCKET ERROR LOGGING
# =================================================
logging.getLogger("websockets.server").setLevel(logging.ERROR)
logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
logging.getLogger("websockets.http11").setLevel(logging.ERROR)

# =================================================
# USER MANAGEMENT SYSTEM
# =================================================

class UserManager:
    """
    Multi-user management system with location-based timezone support.
    Each user has their own profile with timezone, preferences, and memory.
    """
    
    def __init__(self):
        self.users = {}
        self.current_user = None
        self.users_file = PROJECT_ROOT / "python" / "data" / "users.json"
        self._load_users()
        
        # Default timezone mappings for common locations
        self.timezone_map = {
            # India
            'india': 'Asia/Kolkata',
            'mumbai': 'Asia/Kolkata',
            'delhi': 'Asia/Kolkata',
            'bangalore': 'Asia/Kolkata',
            'chennai': 'Asia/Kolkata',
            'hyderabad': 'Asia/Kolkata',
            'kolkata': 'Asia/Kolkata',
            'vizag': 'Asia/Kolkata',
            'visakhapatnam': 'Asia/Kolkata',
            'vijayawada': 'Asia/Kolkata',
            
            # USA
            'usa': 'America/New_York',
            'new york': 'America/New_York',
            'los angeles': 'America/Los_Angeles',
            'san francisco': 'America/Los_Angeles',
            'chicago': 'America/Chicago',
            'dallas': 'America/Chicago',
            'miami': 'America/New_York',
            'seattle': 'America/Los_Angeles',
            
            # UK/Europe
            'uk': 'Europe/London',
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'berlin': 'Europe/Berlin',
            'rome': 'Europe/Rome',
            'madrid': 'Europe/Madrid',
            'amsterdam': 'Europe/Amsterdam',
            
            # Australia
            'australia': 'Australia/Sydney',
            'sydney': 'Australia/Sydney',
            'melbourne': 'Australia/Melbourne',
            'brisbane': 'Australia/Brisbane',
            'perth': 'Australia/Perth',
            
            # Asia
            'japan': 'Asia/Tokyo',
            'tokyo': 'Asia/Tokyo',
            'china': 'Asia/Shanghai',
            'shanghai': 'Asia/Shanghai',
            'singapore': 'Asia/Singapore',
            'dubai': 'Asia/Dubai',
            'hong kong': 'Asia/Hong_Kong',
            'seoul': 'Asia/Seoul',
            'bangkok': 'Asia/Bangkok',
            'kuala lumpur': 'Asia/Kuala_Lumpur',
            
            # Other
            'canada': 'America/Toronto',
            'toronto': 'America/Toronto',
            'vancouver': 'America/Vancouver',
            'montreal': 'America/Montreal',
            'mexico': 'America/Mexico_City',
            'brazil': 'America/Sao_Paulo',
            'sao paulo': 'America/Sao_Paulo',
            'south africa': 'Africa/Johannesburg',
            'johannesburg': 'Africa/Johannesburg',
            'egypt': 'Africa/Cairo',
            'cairo': 'Africa/Cairo',
            'russia': 'Europe/Moscow',
            'moscow': 'Europe/Moscow',
            'new zealand': 'Pacific/Auckland',
            'auckland': 'Pacific/Auckland',
        }
    
    def _load_users(self):
        """Load users from file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.current_user = data.get('current_user')
                print(f"👥 Loaded {len(self.users)} users")
            else:
                self._create_default_user()
        except Exception as e:
            print(f"⚠️ Error loading users: {e}")
            self._create_default_user()
    
    def _create_default_user(self):
        """Create a default user"""
        self.users = {
            'default': {
                'name': 'Default User',
                'timezone': 'Asia/Kolkata',
                'location': 'India',
                'preferences': {
                    'language': 'en',
                    'voice_speed': 1.0,
                    'theme': 'dark'
                },
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat()
            }
        }
        self.current_user = 'default'
        self._save_users()
        print("👤 Created default user (Timezone: Asia/Kolkata)")
    
    def _save_users(self):
        """Save users to file"""
        try:
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump({
                    'users': self.users,
                    'current_user': self.current_user
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving users: {e}")
    
    def get_timezone_for_location(self, location: str) -> str:
        """Get timezone string for a location"""
        location_lower = location.lower().strip()
        
        if location_lower in self.timezone_map:
            return self.timezone_map[location_lower]
        
        for key, tz_str in self.timezone_map.items():
            if key in location_lower:
                return tz_str
        
        return 'UTC'
    
    def create_user(self, username: str, location: str = None) -> Dict:
        """Create a new user"""
        if username in self.users:
            return {'success': False, 'error': f'User "{username}" already exists'}
        
        timezone_str = 'UTC'
        if location:
            timezone_str = self.get_timezone_for_location(location)
        
        user_data = {
            'name': username,
            'timezone': timezone_str,
            'location': location or 'Unknown',
            'preferences': {
                'language': 'en',
                'voice_speed': 1.0,
                'theme': 'dark'
            },
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        }
        
        self.users[username] = user_data
        self._save_users()
        
        return {
            'success': True,
            'message': f'User "{username}" created with timezone {timezone_str}',
            'user': user_data
        }
    
    def switch_user(self, username: str) -> Dict:
        """Switch to a different user"""
        if username not in self.users:
            return {'success': False, 'error': f'User "{username}" not found'}
        
        self.current_user = username
        self.users[username]['last_login'] = datetime.now().isoformat()
        self._save_users()
        
        return {
            'success': True,
            'message': f'Switched to user "{username}"',
            'user': self.users[username]
        }
    
    def get_current_user(self) -> Dict:
        """Get current user data"""
        if self.current_user and self.current_user in self.users:
            return self.users[self.current_user]
        return None
    
    def get_current_timezone(self) -> str:
        """Get current user's timezone"""
        user = self.get_current_user()
        if user:
            return user.get('timezone', 'UTC')
        return 'UTC'
    
    def get_current_time(self) -> str:
        """Get current time in user's timezone"""
        tz_str = self.get_current_timezone()
        try:
            user_tz = pytz.timezone(tz_str)
            now = datetime.now(user_tz)
            return now.strftime("%I:%M:%S %p")
        except:
            now = datetime.now(timezone.utc)
            return now.strftime("%I:%M:%S %p UTC")
    
    def get_current_date(self) -> str:
        """Get current date in user's timezone"""
        tz_str = self.get_current_timezone()
        try:
            user_tz = pytz.timezone(tz_str)
            now = datetime.now(user_tz)
            return now.strftime("%B %d, %Y")
        except:
            now = datetime.now(timezone.utc)
            return now.strftime("%B %d, %Y UTC")
    
    def list_users(self) -> List[str]:
        """List all users"""
        return list(self.users.keys())
    
    def get_user_time_display(self, username: str = None) -> str:
        """Get time display for a user"""
        if username and username in self.users:
            tz_str = self.users[username].get('timezone', 'UTC')
            try:
                user_tz = pytz.timezone(tz_str)
                now = datetime.now(user_tz)
                return now.strftime("%I:%M:%S %p")
            except:
                now = datetime.now(timezone.utc)
                return now.strftime("%I:%M:%S %p UTC")
        return self.get_current_time()
    
    def update_user_location(self, username: str, location: str) -> Dict:
        """Update user's location and timezone"""
        if username not in self.users:
            return {'success': False, 'error': f'User "{username}" not found'}
        
        timezone_str = self.get_timezone_for_location(location)
        self.users[username]['location'] = location
        self.users[username]['timezone'] = timezone_str
        self._save_users()
        
        return {
            'success': True,
            'message': f'Updated "{username}" location to {location} (timezone: {timezone_str})'
        }
    
    def delete_user(self, username: str) -> Dict:
        """Delete a user"""
        if username not in self.users:
            return {'success': False, 'error': f'User "{username}" not found'}
        
        if len(self.users) <= 1:
            return {'success': False, 'error': 'Cannot delete the last user'}
        
        del self.users[username]
        if self.current_user == username:
            self.current_user = list(self.users.keys())[0]
        self._save_users()
        
        return {
            'success': True,
            'message': f'User "{username}" deleted'
        }

user_manager = UserManager()

# =================================================
# REMINDER SYSTEM
# =================================================

class ReminderSystem:
    """Handle reminders with time-based triggers"""
    
    def __init__(self):
        self.reminders = []
        self._checking = False
        self._check_task = None
        
    def add_reminder(self, time_str: str, message: str) -> Dict[str, Any]:
        """Add a reminder at specific time"""
        try:
            time_str = time_str.strip().lower()
            
            if '.' in time_str and 'pm' in time_str:
                time_str = time_str.replace('.', ':')
            if '.' in time_str and 'am' in time_str:
                time_str = time_str.replace('.', ':')
            
            now = datetime.now()
            formats = ['%I:%M %p', '%H:%M', '%I:%M %p', '%I.%M %p']
            parsed_time = None
            
            for fmt in formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not parsed_time:
                return {"success": False, "error": f"Could not parse time: {time_str}"}
            
            target = now.replace(
                hour=parsed_time.hour,
                minute=parsed_time.minute,
                second=0,
                microsecond=0
            )
            
            if target <= now:
                target += timedelta(days=1)
            
            reminder = {
                "id": len(self.reminders) + 1,
                "time": target.isoformat(),
                "time_str": time_str,
                "message": message,
                "triggered": False,
                "created_at": now.isoformat()
            }
            
            self.reminders.append(reminder)
            
            if not self._checking:
                self._start_checker()
            
            return {
                "success": True,
                "message": f"Reminder set for {time_str}: {message}",
                "reminder": reminder
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _start_checker(self):
        self._checking = True
        asyncio.create_task(self._check_reminders())
    
    async def _check_reminders(self):
        while self._checking:
            try:
                now = datetime.now()
                due_reminders = []
                
                for reminder in self.reminders:
                    if not reminder.get("triggered", False):
                        reminder_time = datetime.fromisoformat(reminder["time"])
                        if now >= reminder_time:
                            due_reminders.append(reminder)
                
                for reminder in due_reminders:
                    reminder["triggered"] = True
                    await self._trigger_reminder(reminder)
                
                triggered = [r for r in self.reminders if r.get("triggered", False)]
                if len(triggered) > 50:
                    self.reminders = [r for r in self.reminders if not r.get("triggered", False)] + triggered[-50:]
                
                await asyncio.sleep(5)
            except Exception as e:
                print(f"⚠️ Reminder checker error: {e}")
                await asyncio.sleep(5)
    
    async def _trigger_reminder(self, reminder):
        message = reminder.get("message", "Reminder!")
        time_str = reminder.get("time_str", "now")
        
        print(f"🔔 REMINDER: {message} (set for {time_str})")
        hologram_bridge.send_text(f"🔔 REMINDER: {message}")
        hologram_bridge.set_voice_state('speaking')
        
        await speak_text(f"Reminder: {message}", voice_agent_ref if voice_agent_ref else None)
        
        hologram_bridge.set_voice_state('idle')
    
    def get_active_reminders(self) -> List[Dict]:
        return [r for r in self.reminders if not r.get("triggered", False)]
    
    def get_all_reminders(self) -> List[Dict]:
        return self.reminders
    
    def stop(self):
        self._checking = False

# =================================================
# NOTIFICATION SYSTEM
# =================================================

class NotificationSystem:
    """Handle notifications from various apps"""
    
    def __init__(self):
        self.notifications = {}
        self.notification_details = {}
        self._notifying = False
        
    def add_notification(self, app_name: str, message: str, details: str = None):
        if app_name not in self.notifications:
            self.notifications[app_name] = 0
            self.notification_details[app_name] = []
        
        self.notifications[app_name] += 1
        if details:
            self.notification_details[app_name].append({
                "message": message,
                "details": details,
                "time": datetime.now().isoformat()
            })
        else:
            self.notification_details[app_name].append({
                "message": message,
                "details": message,
                "time": datetime.now().isoformat()
            })
        
        if len(self.notification_details[app_name]) > 50:
            self.notification_details[app_name] = self.notification_details[app_name][-50:]
        
        hologram_bridge.send_text(f"📱 {app_name}: {self.notifications[app_name]} notifications")
        
        if not self._notifying:
            asyncio.create_task(self._speak_notification(app_name, message))
    
    async def _speak_notification(self, app_name: str, message: str):
        self._notifying = True
        try:
            speak_msg = f"Notification from {app_name}: {message}"
            print(f"📱 {speak_msg}")
            hologram_bridge.set_voice_state('speaking')
            await speak_text(speak_msg, voice_agent_ref if voice_agent_ref else None)
            hologram_bridge.set_voice_state('idle')
        except Exception as e:
            print(f"⚠️ Notification speak error: {e}")
        finally:
            self._notifying = False
    
    def get_summary(self) -> Dict:
        return self.notifications
    
    def get_app_notifications(self, app_name: str) -> List[Dict]:
        return self.notification_details.get(app_name, [])
    
    def get_app_count(self, app_name: str) -> int:
        return self.notifications.get(app_name, 0)
    
    def read_notification(self, app_name: str, index: int = 0) -> Optional[str]:
        notifications = self.notification_details.get(app_name, [])
        if not notifications:
            return None
        if index >= len(notifications):
            index = len(notifications) - 1
        return notifications[index].get("details", notifications[index].get("message"))
    
    def clear_notifications(self, app_name: str = None):
        if app_name:
            self.notifications[app_name] = 0
            self.notification_details[app_name] = []
        else:
            self.notifications = {}
            self.notification_details = {}

# =================================================
# HOLOGRAM INTEGRATION - WebSocket Server
# =================================================

class HologramBridge:
    """WebSocket bridge to connect JARVIS with hologram UI"""
    
    def __init__(self, port=8765):
        self.port = port
        self.clients = set()
        self.running = False
        self.current_state = 'idle'
        self.current_persona = 'jarvis'
        self.server = None
        self._task = None
        self.command_queue = None
        
    async def start(self):
        try:
            self.running = True
            self.server = await websockets.serve(
                self.handler, 
                "localhost", 
                self.port,
                max_size=2**23,
                max_queue=32
            )
            print(f"✅ Hologram WebSocket server started on ws://localhost:{self.port}")
            await self.server.wait_closed()
        except Exception as e:
            print(f"⚠️ Hologram WebSocket error: {e}")
    
    async def handler(self, websocket):
        try:
            self.clients.add(websocket)
            print(f"🔗 Hologram client connected ({len(self.clients)} total)")
            
            await self.send_state(websocket)
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data, websocket)
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"⚠️ Message handler error: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except websockets.exceptions.ConnectionClosedError:
            pass
        except websockets.exceptions.InvalidMessage:
            pass
        except Exception as e:
            if "opening handshake failed" not in str(e) and "InvalidMessage" not in str(e):
                print(f"⚠️ WebSocket handler error: {e}")
        finally:
            if websocket in self.clients:
                self.clients.remove(websocket)
            print(f"🔗 Hologram client disconnected ({len(self.clients)} total)")
    
    async def handle_message(self, data, websocket):
        msg_type = data.get('type')
        payload = data.get('payload', {})
        
        if msg_type == 'voice_command':
            text = payload.get('text', '')
            if text and self.command_queue:
                await self.command_queue.put(text)
        elif msg_type == 'pong':
            pass
    
    async def send_state(self, websocket):
        try:
            await websocket.send(json.dumps({
                'type': 'voice_state',
                'payload': {'state': self.current_state}
            }))
            await websocket.send(json.dumps({
                'type': 'persona',
                'payload': {'persona': self.current_persona}
            }))
        except:
            pass
    
    async def broadcast(self, msg_type, payload):
        if not self.clients:
            return
        message = json.dumps({'type': msg_type, 'payload': payload})
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except:
                disconnected.add(client)
        self.clients -= disconnected
    
    def set_voice_state(self, state):
        self.current_state = state
        if self.running:
            asyncio.create_task(self.broadcast('voice_state', {'state': state}))
    
    def set_persona(self, persona):
        self.current_persona = persona
        if self.running:
            asyncio.create_task(self.broadcast('persona', {'persona': persona}))
    
    def update_system(self, cpu, memory, processes):
        if self.running:
            asyncio.create_task(self.broadcast('system_stats', {
                'cpu': cpu,
                'memory': memory,
                'processes': processes
            }))
    
    def update_task(self, index, name, progress):
        if self.running:
            asyncio.create_task(self.broadcast('task_update', {
                'index': index,
                'name': name,
                'progress': progress
            }))
    
    def send_text(self, text):
        if self.running:
            asyncio.create_task(self.broadcast('text', {'text': text}))
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.close()

hologram_bridge = HologramBridge()

reminder_system = ReminderSystem()
notification_system = NotificationSystem()

# =================================================
# PERSONALITY ENGINE
# =================================================

try:
    from moa.personality_engine import PersonalityEngine
    PERSONALITY_AVAILABLE = True
except ImportError:
    PERSONALITY_AVAILABLE = False
    print("⚠️ Personality Engine not available")

personality_engine = None
if PERSONALITY_AVAILABLE:
    personality_engine = PersonalityEngine()
    print("🎭 Personality Engine initialized")

# =================================================
# ADVANCED MEMORY
# =================================================
try:
    from moa.advanced_memory import AdvancedMemory
    ADVANCED_MEMORY_AVAILABLE = True
except ImportError:
    ADVANCED_MEMORY_AVAILABLE = False
    print("⚠️ Advanced Memory not available")

advanced_memory = None
if ADVANCED_MEMORY_AVAILABLE:
    try:
        memory_path = PROJECT_ROOT / "python" / "data" / "advanced_memory.json"
        advanced_memory = AdvancedMemory(str(memory_path))
        print("🧠 Advanced Memory initialized")
    except Exception as e:
        print(f"⚠️ Advanced Memory error: {e}")

# =================================================
# CONVERSATIONAL MIND
# =================================================

class ConversationalMind:
    def __init__(self):
        self.conversation_topics = [
            "How are you feeling today?",
            "What would you like to talk about?",
            "I noticed you've been quiet. Everything okay?",
            "What's on your mind right now?",
            "Did you know I can help you with almost anything?",
            "What's your favorite thing to do with JARVIS?",
            "Is there anything I can help you with today?",
            "You seem curious about something. What is it?",
            "I've been learning a lot lately. Want to hear something interesting?",
            "What's the most exciting thing happening in your life right now?",
            "Have you thought about what you'd like to accomplish today?",
            "I'm here if you need to talk or want to know anything.",
            "How has your day been so far?",
            "Is there anything new you'd like to explore today?",
            "I was thinking about what we talked about earlier. Any new thoughts?",
        ]
        
        self.follow_up_questions = [
            "That's interesting! Tell me more.",
            "Really? Why do you say that?",
            "What makes you think that?",
            "How does that make you feel?",
            "I'd love to hear more about that.",
            "That's fascinating! Can you elaborate?",
            "What do you mean by that?",
            "Is there something specific you'd like to explore?",
            "What would you like to know about that?",
            "I'm curious, what's your perspective on that?",
            "What else can you tell me about that?",
            "How did that come about?",
            "What was that experience like for you?",
            "That sounds interesting. What part of it stood out to you?",
        ]
        
        self.random_comments = [
            "I'm always learning new things.",
            "You know, I think we make a great team.",
            "I find our conversations really interesting.",
            "There's so much to discover in the world.",
            "I wonder what we'll talk about next.",
            "It's amazing how much we can learn from each other.",
        ]
        
        self.conversation_state = {
            'last_interaction': time.time(),
            'interaction_count': 0,
            'topics_discussed': [],
            'user_interests': [],
            'waiting_for_response': False,
            'proactive_timer': 0,
            'personality_traits': ['curious', 'helpful', 'friendly', 'observant'],
            'mood': 'neutral',
            'conversation_depth': 0,
            'last_user_message': '',
            'last_jarvis_response': '',
        }
        
        self._proactive_interval = 35
        self._last_proactive_time = time.time()
        self._is_proactive = False
        
    def should_proactively_engage(self) -> bool:
        current_time = time.time()
        elapsed = current_time - self._last_proactive_time
        
        if self.conversation_state['waiting_for_response']:
            return False
        
        if elapsed < 5:
            return False
        
        if elapsed > self._proactive_interval:
            if random.random() < 0.55:
                self._last_proactive_time = current_time
                return True
        
        return False
    
    def get_conversation_starter(self) -> str:
        if self.conversation_state['user_interests']:
            interest = random.choice(self.conversation_state['user_interests'])
            return f"I remember you mentioned you're interested in {interest}. Would you like to talk more about that?"
        
        if self.conversation_state['topics_discussed']:
            topic = random.choice(self.conversation_state['topics_discussed'])
            return f"We talked about {topic} before. Is there anything else you'd like to know about that?"
        
        if self.conversation_state['conversation_depth'] > 3:
            return random.choice([
                "We've been talking for a while. Is there anything specific you'd like to focus on?",
                "I've enjoyed our conversation. What would you like to explore next?",
                "You know, I'm really enjoying getting to know you better."
            ])
        
        return random.choice(self.conversation_topics)
    
    def get_follow_up(self, user_input: str) -> Optional[str]:
        word_count = len(user_input.split())
        
        if word_count < 5 and random.random() < 0.6:
            return random.choice([
                "That's interesting! Tell me more.",
                "I'd love to hear more about that.",
                "What else can you tell me about that?",
                "That sounds fascinating. Can you elaborate?",
            ])
        
        if '?' in user_input:
            return None
        
        if word_count > 5 and random.random() < 0.3:
            return random.choice(self.follow_up_questions)
        
        return None
    
    def process_interaction(self, user_input: str, response: str):
        self.conversation_state['interaction_count'] += 1
        self.conversation_state['conversation_depth'] += 1
        self.conversation_state['last_interaction'] = time.time()
        self.conversation_state['waiting_for_response'] = False
        self.conversation_state['last_user_message'] = user_input
        self.conversation_state['last_jarvis_response'] = response
        
        words = user_input.lower().split()
        topics = ['science', 'technology', 'space', 'music', 'movies', 'books', 
                  'sports', 'food', 'travel', 'history', 'art', 'coding', 'AI',
                  'philosophy', 'psychology', 'nature', 'animals', 'health',
                  'fitness', 'business', 'finance', 'education', 'culture']
        
        for topic in topics:
            if topic in user_input.lower():
                if topic not in self.conversation_state['user_interests']:
                    self.conversation_state['user_interests'].append(topic)
                    print(f"🧠 JARVIS learned: User is interested in {topic}")
                if topic not in self.conversation_state['topics_discussed']:
                    self.conversation_state['topics_discussed'].append(topic)
        
        if any(word in response.lower() for word in ['sorry', 'apologize', 'error', 'problem', 'mistake']):
            self.conversation_state['mood'] = 'apologetic'
        elif any(word in response.lower() for word in ['great', 'excellent', 'awesome', 'wonderful', 'amazing']):
            self.conversation_state['mood'] = 'happy'
        elif any(word in response.lower() for word in ['curious', 'interesting', 'fascinating', 'cool']):
            self.conversation_state['mood'] = 'curious'
        elif any(word in response.lower() for word in ['sad', 'unfortunate', 'sorry', 'regret']):
            self.conversation_state['mood'] = 'sympathetic'
        else:
            self.conversation_state['mood'] = 'neutral'
        
        if self.conversation_state['conversation_depth'] > 5:
            self._proactive_interval = 45
        else:
            self._proactive_interval = 30
        
        logger.debug(f"Conversation state: depth={self.conversation_state['conversation_depth']}, "
                    f"interests={self.conversation_state['user_interests']}, "
                    f"mood={self.conversation_state['mood']}")

conversational_mind = ConversationalMind()

# =================================================
# TEXT NORMALIZER
# =================================================
try:
    from moa.text_normalizer import normalizer
    TEXT_NORMALIZER_AVAILABLE = True
    print("✅ Text normalizer loaded")
except ImportError as e:
    TEXT_NORMALIZER_AVAILABLE = False
    print(f"⚠️ Text normalizer not available: {e}")
    class DummyNormalizer:
        def normalize(self, text): 
            return text
    normalizer = DummyNormalizer()

# =================================================
# NEW FEATURE IMPORTS
# =================================================

try:
    from moa.wake_word import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False
    print("⚠️ Wake Word module not available. Install: pip install pvporcupine pyaudio")

try:
    from moa.proactive_supervisor import ProactiveSupervisor
    PROACTIVE_SUPERVISOR_AVAILABLE = True
except ImportError:
    PROACTIVE_SUPERVISOR_AVAILABLE = False
    print("⚠️ Proactive Supervisor module not available")

try:
    from agents.browser.automation import BrowserAutomation
    BROWSER_AUTOMATION_AVAILABLE = True
except ImportError:
    BROWSER_AUTOMATION_AVAILABLE = False
    print("⚠️ Browser Automation module not available. Install: pip install playwright")

try:
    from web.dashboard import start_dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False
    print("⚠️ Dashboard module not available. Install: pip install flask flask-socketio")

try:
    from api.mobile_api import start_mobile_api
    MOBILE_API_AVAILABLE = True
except ImportError:
    MOBILE_API_AVAILABLE = False
    print("⚠️ Mobile API module not available")

try:
    from moa.plugin_manager import PluginManager
    PLUGIN_AVAILABLE = True
except ImportError:
    PLUGIN_AVAILABLE = False
    print("⚠️ Plugin System module not available")

try:
    from agents.llm.local_llm import LocalLLM
    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False
    print("⚠️ Local LLM module not available")

try:
    from skills.skills import SkillManager
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    print("⚠️ Skills module not available")

try:
    from moa.conversation_context import ConversationContext
    CONTEXT_AVAILABLE = True
except ImportError:
    CONTEXT_AVAILABLE = False
    print("⚠️ Conversation Context module not available")

try:
    from moa.system_monitor import SystemMonitor
    SYSTEM_MONITOR_AVAILABLE = True
except ImportError:
    SYSTEM_MONITOR_AVAILABLE = False
    print("⚠️ System Monitor module not available")

try:
    from moa.real_time_assistant import RealTimeAssistant
    REAL_TIME_AVAILABLE = True
except ImportError:
    REAL_TIME_AVAILABLE = False
    print("⚠️ Real-Time Assistant not available. Install: pip install sounddevice numpy faster-whisper")

# =================================================
# LOGGER SETUP
# =================================================
logger = logging.getLogger("jarvis.main")

# =================================================
# SPEAKING LOCK
# =================================================
_speaking_lock = False

# =================================================
# SHUTDOWN FUNCTION - FIXED
# =================================================

async def shutdown_jarvis(voice_agent: VoiceAgent, shutdown_pc: bool = False):
    """
    Shutdown JARVIS completely. Optionally shutdown the PC.
    
    Args:
        voice_agent: Voice agent for speaking
        shutdown_pc: If True, shutdown the PC as well
    """
    print("\n🛑 Shutting down JARVIS...")
    hologram_bridge.send_text("SHUTTING DOWN JARVIS...")
    hologram_bridge.set_voice_state('idle')
    
    # Speak goodbye message
    if shutdown_pc:
        goodbye_msg = "Shutting down JARVIS and powering off the computer. Goodbye sir!"
    else:
        goodbye_msg = "Shutting down JARVIS. Goodbye sir!"
    
    await speak_text(goodbye_msg, voice_agent)
    
    # Give speech time to complete
    await asyncio.sleep(2)
    
    # Save all data
    if personality_engine:
        try:
            personality_engine.save_profile()
            print("   ✅ Personality profile saved")
        except Exception as e:
            print(f"   ⚠️ Personality save error: {e}")
    
    # Stop all services
    hologram_bridge.stop()
    print("   ✅ Hologram bridge stopped")
    
    try:
        await voice_agent._run("stop_streaming", {})
        print("   ✅ Streaming stopped")
    except:
        pass
    
    # Shutdown PC if requested
    if shutdown_pc:
        print("   💻 Shutting down computer...")
        hologram_bridge.send_text("POWERING OFF PC...")
        
        # Force flush any pending output
        sys.stdout.flush()
        
        # Wait a moment for messages to send
        await asyncio.sleep(1)
        
        try:
            if sys.platform == "win32":
                print("   💻 Executing: shutdown /s /t 5 /f")
                # Use subprocess for better control
                result = subprocess.run(
                    ["shutdown", "/s", "/t", "5", "/f"],
                    capture_output=True,
                    text=True
                )
                print(f"   💻 Shutdown command result code: {result.returncode}")
                if result.stderr:
                    print(f"   💻 Shutdown error: {result.stderr}")
                # Also try os.system as fallback
                os.system("shutdown /s /t 5 /f")
            elif sys.platform == "darwin":  # macOS
                print("   💻 Executing: sudo shutdown -h now")
                os.system("sudo shutdown -h now")
            else:  # Linux
                print("   💻 Executing: sudo shutdown -h now")
                os.system("sudo shutdown -h now")
        except Exception as e:
            print(f"⚠️ Shutdown error: {e}")
            # Try alternative method
            try:
                if sys.platform == "win32":
                    subprocess.run(["shutdown", "/s", "/t", "5", "/f"], capture_output=True)
            except:
                pass
    
    # Exit the program
    print("👋 Goodbye!")
    sys.exit(0)

# =================================================
# DIRECT SEARCH
# =================================================

async def search_direct(query: str) -> Optional[str]:
    try:
        import requests
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            logger.debug("TAVILY_API_KEY not found in environment")
            return None
        
        clean_query = re.sub(r'(?i)(jarvis|can you|tell me|please|could you|would you)\s*', '', query)
        clean_query = clean_query.strip()
        
        if not clean_query:
            clean_query = query
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": clean_query,
            "search_depth": "basic",
            "max_results": 2,
            "include_answer": True
        }
        
        logger.debug(f"Direct search: {clean_query[:50]}...")
        
        response = requests.post(url, json=payload, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer")
            if answer:
                return answer[:500]
            
            results = data.get("results", [])
            if results:
                content = results[0].get("content", "")
                if content:
                    return content[:500]
        return None
    except Exception as e:
        logger.debug(f"Direct search error: {e}")
        return None

# =================================================
# BROWSER OPEN
# =================================================

async def open_browser_url(url: str) -> Dict[str, Any]:
    try:
        import webbrowser
        import requests as req_utils
        
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            if '.' in url and not url.startswith(('localhost', '127.0.0.1')):
                url = 'https://' + url
            elif ' ' in url or not '.' in url:
                url = 'https://www.google.com/search?q=' + req_utils.utils.quote(url)
        
        webbrowser.open(url)
        
        return {
            "success": True,
            "message": f"Opened {url} in browser",
            "url": url
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to open URL: {e}"
        }

# =================================================
# ACTION VALIDATION
# =================================================

SUPERVISOR_ACTIONS = {
    "get_time", "get_date", "time", "date",
    "weather", "my_location",
    "launch_app", "open", "start", "run",
    "close_app", "close", "kill", "stop_app",
    "progress_report", "progress_report_full", "get_alerts",
    "check_all", "get_idle_agents", "get_unhealthy_agents",
    "get_busiest_agent", "get_least_used_agent", "brain_analyze",
    "check_agent",
    "remember_fact", "recall_fact", "get_all_memory",
    "remember_facts", "remember_name", "get_name",
    "set_user", "clear_memory",
    "add_conversation", "search_conversations",
    "learn_preference", "get_preference", "get_all_preferences",
    "get_context", "get_stats",
    "desktop", "desktop_agent",
    "skill", "skills",
    "plugin", "plugins",
}

def is_supervisor_action(action: str) -> bool:
    return action in SUPERVISOR_ACTIONS

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)

def print_banner():
    user_name = "Default User"
    user_timezone = "UTC"
    if user_manager and user_manager.get_current_user():
        user_data = user_manager.get_current_user()
        user_name = user_data.get('name', 'Default User')
        user_timezone = user_data.get('timezone', 'UTC')
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║    J A R V I S   A I   O S   v 2 1 . 0 4 . 0 8          ║
    ║    REAL OS CONTROL • LLM ONLY FOR THINKING                ║
    ║    Features: Wake Word • Proactive • Automation          ║
    ║    Personality Engine • Advanced Memory                   ║
    ║    Continuous Voice • Browser Control                     ║
    ║    INTERRUPTION HANDLING • CONTEXTUAL AI                  ║
    ║    REMINDERS • NOTIFICATIONS • FILESYSTEM                 ║
    ║    MULTI-USER • LOCATION-BASED TIMEZONES                  ║
    ║    SHUTDOWN: exit • exit voice • shutdown pc              ║
    ╠════════════════════════════════════════════════════════════╣
    ║    👤 User: {user_name:<20}  🌍 Timezone: {user_timezone:<15} ║
    ║    🕐 Time: {user_manager.get_current_time():<20}  📅 {user_manager.get_current_date():<20} ║
    ╚════════════════════════════════════════════════════════════╝
    """)

def print_help():
    print("""
    JARVIS OS v21.04.08 Commands:
    ------------------------------
    
    🔴 SHUTDOWN:
    📌 Exit:        "exit", "quit", "bye" (Exits JARVIS)
    📌 Shutdown:    "shutdown pc", "power off" (Shutdown JARVIS + PC)
    
    👤 USER MANAGEMENT:
    📌 Users:       "list users", "show users"
    📌 Switch:      "switch user John", "user John"
    📌 Create:      "create user Alex location London"
    📌 Delete:      "delete user Alex"
    📌 My Info:     "my info", "who am i"
    📌 Update Loc:  "update location Paris", "set location Tokyo"
    
    🕒 Time:      "what time is it", "time now" (Shows user's local time)
    📅 Date:      "today's date", "what date is it" (Shows user's local date)
    🌤️ Weather:   "weather in London" (uses search)
    📍 Location:  "where am i", "my location"
    🚀 Launch:    "open chrome", "start notepad"
    🛑 Close:     "close chrome", "kill notepad"
    🔍 Search:    "search for python"
    🌐 Browser:   "open google.com", "go to youtube.com"
    🧠 Memory:    "my name is Nandan", "what is my name"
    🧠 Advanced:  "what do you remember about me", "get memory stats"
    🔧 System:    "system status", "check all agents"
    
    💾 FILESYSTEM:
    📌 List Drives:   "list drives", "show drives"
    📌 Drive Info:    "info for drive D:", "drive C: details"
    📌 List Directory:"list directory C:/Users", "show files in D:/"
    📌 Create File:   "create file D:/test.txt with content Hello"
    📌 Create File on Drive: "create file test.txt in D drive"
    📌 Open File:     "open file C:/Users/test.txt"
    📌 Read File:     "read file C:/config.json"
    📌 Create Folder: "create folder E:/new_folder"
    📌 Search Files:  "search files *.pdf in C:/Documents"
    📌 Delete File:   "delete file D:/temp.txt"
    📌 Copy File:     "copy file C:/source.txt to D:/backup/"
    
    ⏰ REMINDERS:
    📌 Set:       "set a reminder for 2:30 PM to meet with team"
    📌 List:      "list reminders"
    📌 Delete:    "delete reminder 1"
    
    📱 NOTIFICATIONS:
    📌 Summary:   "notification summary"
    📌 App:       "notifications from WhatsApp"
    📌 Read:      "read notification from WhatsApp"
    📌 Clear:     "clear all notifications"
    
    🖥️ Desktop Control:
    📁 Files:     "list files in C:", "create file test.txt"
    📋 Clipboard: "copy to clipboard", "get clipboard"
    📸 Screenshot: "take screenshot", "screenshot"
    🔊 Volume:    "set volume to 50", "get volume"
    💡 Brightness: "set brightness to 70"
    🔄 Processes: "list processes", "kill chrome"
    🪟 Windows:   "list windows", "focus notepad"
    
    🎯 VOICE MODES:
    🔔 Wake Word: "Hey JARVIS" (voice activated)
    🎧 Continuous Voice: "continuous voice" (always-on, VAD-based)
    📊 Streaming Status: "streaming status"
    🔧 VAD Settings: "set vad threshold 0.015"
    
    🎭 PERSONALITY ENGINE:
    👤 Profile:   "show my profile", "who am I"
    📊 Analytics: "conversation analytics", "my personality"
    💾 Save:      "save profile", "save memory"
    
    🎯 OTHER FEATURES:
    🤖 Skills:    "good morning", "take note", "lock screen"
    🔌 Plugins:   "list plugins", "enable plugin", "disable plugin"
    📊 Monitor:   "system monitor", "show system stats"
    📱 Mobile:    API at http://localhost:5001
    🖥️ Dashboard: http://localhost:5000
    🔗 Hologram:  ws://localhost:8765
    
    💭 Think:     Anything else → LLM
    """)

# =================================================
# TIME FUNCTIONS
# =================================================

def get_current_time_user() -> str:
    return user_manager.get_current_time()

def get_current_date_user() -> str:
    return user_manager.get_current_date()

def is_time_query(text: str) -> bool:
    time_patterns = [
        r'(what|tell|give|know).*time',
        r'time now',
        r'current time',
        r'present time',
        r'what.*clock',
        r'time.*india',
        r'time.*ist',
        r'local time',
        r'system time',
        r'time in',
        r'what.*time.*it',
        r'where.*time',
    ]
    text_lower = text.lower()
    for pattern in time_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

def is_date_query(text: str) -> bool:
    date_patterns = [
        r'(what|tell|give).*date',
        r'current date',
        r'today.*date',
        r'present date',
        r'what.*day',
        r'today\'s date',
    ]
    text_lower = text.lower()
    for pattern in date_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

def is_weather_query(text: str) -> bool:
    weather_patterns = [
        r'weather',
        r'temperature',
        r'rain',
        r'humidity',
        r'forecast',
        r'climate',
        r'present.*weather',
        r'current.*weather',
        r'today.*weather',
        r'weather.*in',
        r'what.*weather',
        r'tell.*weather',
        r'check.*weather',
        r'how.*weather',
        r'vishakapatnam',
        r'visakhapatnam',
        r'vizag',
        r'vijayawada',
        r'hyderabad',
        r'chennai',
        r'bangalore',
        r'mumbai',
        r'delhi',
        r'kolkata',
    ]
    text_lower = text.lower()
    for pattern in weather_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

def is_general_knowledge_query(text: str) -> bool:
    text_lower = text.lower()
    
    memory_keywords = [
        "my name", "my mother", "my father", "my favorite color",
        "where i live", "i am from", "my birthday", "my pet", 
        "my occupation", "what do you remember about me", "what do you know about me"
    ]
    if any(keyword in text_lower for keyword in memory_keywords):
        return False
    
    clean_text = re.sub(r'^(jarvis|hey jarvis|hey|okay jarvis|ok jarvis|hello jarvis|hi jarvis)\s+', '', text, flags=re.IGNORECASE)
    clean_text_lower = clean_text.lower()
    
    knowledge_patterns = [
        r'who is', r'who are', r'who was', r'who were',
        r'what is', r'what are', r'what was', r'what were',
        r'where is', r'where are', r'where was', r'where were',
        r'when is', r'when are', r'when was', r'when were',
        r'why is', r'why are', r'why was', r'why were',
        r'how is', r'how are', r'how was', r'how were',
        r'how does', r'how do', r'how did',
        r'define', r'explain', r'describe', r'elaborate',
        r'clarify', r'what.*mean', r'what.*means',
        r'meaning of', r'definition of', r'tell me about',
        r'information about', r'facts about', r'knowledge about',
        r'details about', r'overview of', r'introduction to',
        r'history of', r'historical', r'physics', r'chemistry',
        r'biology', r'astronomy', r'geology', r'science',
        r'technology', r'math', r'mathematics',
        r'capital of', r'country', r'state', r'city',
        r'population of', r'area of', r'computer',
        r'software', r'hardware', r'programming',
        r'coding', r'algorithm', r'health', r'medical',
        r'disease', r'treatment', r'cure', r'medicine',
        r'school', r'college', r'university', r'education',
        r'eamcet', r'ap eamcet', r'ts eamcet', r'jee',
        r'neet', r'gate', r'cat', r'gre', r'gmat',
        r'news', r'trending', r'headlines', r'latest',
        r'breaking', r'current events', r'sports',
        r'politics', r'election', r'business', r'finance',
        r'stock', r'market', r'company', r'festival',
        r'celebration', r'culture', r'tradition',
        r'movie', r'film', r'series', r'show', r'music',
        r'artist', r'band', r'concert', r'travel',
        r'tourist', r'tourism', r'vacation', r'holiday',
    ]
    
    for pattern in knowledge_patterns:
        if re.search(pattern, clean_text_lower):
            return True
    
    question_words = ['who', 'what', 'where', 'when', 'why', 'how', 'which', 'whom', 'whose']
    if any(clean_text_lower.startswith(w + ' ') for w in question_words) or '?' in clean_text:
        system_commands = ['exit', 'quit', 'stop', 'help', 'list', 'show', 'status']
        if not any(clean_text_lower.startswith(cmd) for cmd in system_commands):
            return True
    
    return False

def is_news_query(text: str) -> bool:
    news_patterns = [
        r'news', r'trending', r'headlines', r'latest',
        r'breaking', r'current events', r'what.*happening',
        r'what\'s new', r'update', r'sports', r'politics',
        r'election', r'covid', r'corona', r'virus', r'pandemic',
    ]
    text_lower = text.lower()
    for pattern in news_patterns:
        if re.search(pattern, text_lower):
            return True
    return False

def is_debug_or_control_message(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return True
    
    debug_patterns = [
        r'^\[.*\]', r'^✅', r'^❌', r'^🔍', r'^💭',
        r'^🎯', r'^🔄', r'^📝', r'^🗣️', r'^🎤',
        r'^🔊', r'^🛑', r'^🎧', r'^🤖',
        r'^\[ROUTER\]', r'^\[ORCHESTRATOR\]',
        r'^Executing:', r'^Agent:', r'^LLM Agent:',
        r'^MemoryAgent:', r'^SearchAgent:', r'^Tavily',
        r'^INFO', r'^WARNING', r'^ERROR', r'^DEBUG',
        r'^speak', r'^listening', r'^processing',
        r'^transcription', r'^streaming', r'^vad',
        r'^threshold', r'^recording', r'^microphone',
        r'^audio', r'^device', r'^frames', r'^buffer',
        r'^speech', r'^silence', r'^energy', r'^rms',
        r'^amplitude', r'^signal', r'^noise',
    ]
    
    for pattern in debug_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False

def clean_weather_query(text: str) -> str:
    text = re.sub(r'^(jarvis|hey jarvis|hey)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(ok|now|tell me|can you|please|present|current|today|what is|what\'s|the)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^what|^where|^when|^why|^how', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^weather\s+in\s+', '', text, flags=re.IGNORECASE)
    return text.strip()

def clean_text_for_speech(text: str) -> str:
    if not text:
        return ""
    
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s.,!?\'"]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) > 500:
        text = text[:500] + "..."
    
    return text

def format_system_result(data: dict) -> str:
    mode = data.get("mode", "")
    
    if mode == "time":
        user_time = user_manager.get_current_time()
        user_date = user_manager.get_current_date()
        return f"🕒 {user_time}\n   📅 {user_date}"
    
    if mode == "date":
        return f"📅 {user_manager.get_current_date()}"
    
    if mode == "weather":
        output = f"🌤️ {data.get('city', '')}: {data.get('temperature', '')}°C\n"
        output += f"   {data.get('conditions', '')}\n"
        output += f"   💧 Humidity: {data.get('humidity', '')}%\n"
        output += f"   💨 Wind: {data.get('wind_speed', '')} m/s"
        return output
    
    if mode == "location":
        output = f"📍 {data.get('city', '')}, {data.get('region', '')}\n"
        output += f"   🌍 {data.get('country', '')}\n"
        output += f"   🕐 Timezone: {data.get('timezone', '')}"
        return output
    
    if mode == "launch":
        return f"🚀 {data.get('message', '')}"
    
    if mode == "close":
        return f"🛑 {data.get('message', '')}"
    
    if mode == "memory":
        return f"🧠 {data.get('answer', '')}"
    
    if data.get("skill_result"):
        return f"🎯 {data.get('message', '')}"
    
    if data.get("plugin_result"):
        return f"🔌 {data.get('message', '')}"
    
    if data.get("answer") and "✅" in data.get("answer", ""):
        return data["answer"]
    
    if data.get("answer") and "❌" in data.get("answer", ""):
        return data["answer"]
    
    if data.get("answer"):
        return f"📝 {data['answer']}"
    if data.get("message"):
        return f"📝 {data['message']}"
    
    return json.dumps(data, indent=2)

async def speak_text(text: str, voice_agent: VoiceAgent):
    global _speaking_lock
    
    if not text:
        return
    
    if _speaking_lock:
        print(f"🔄 Already speaking, skipping duplicate")
        return
    
    try:
        _speaking_lock = True
        normalized = normalizer.normalize(text)
        clean_text = clean_text_for_speech(normalized)
        if clean_text:
            print(f"🗣️ Speaking: {clean_text[:60]}...")
            result = await voice_agent._run("speak", {"text": clean_text})
            if result and result.get("success"):
                hologram_bridge.set_voice_state('speaking')
                hologram_bridge.send_text(f"SPEAKING: {clean_text[:50]}...")
            else:
                hologram_bridge.set_voice_state('speaking')
                hologram_bridge.send_text(f"SPEAKING: {clean_text[:50]}...")
    except Exception as e:
        print(f"⚠️ TTS error: {e}")
    finally:
        _speaking_lock = False
        hologram_bridge.set_voice_state('idle')

# =================================================
# FIXED: store_conversation - Handles both AgentResult objects and dictionaries
# =================================================
async def store_conversation(command: str, result, memory_agent: MemoryAgent):
    """Store conversation in memory - handles both AgentResult objects and dictionaries."""
    if not result:
        return
    
    # 🔧 FIX: Handle both AgentResult objects and dictionaries
    if isinstance(result, dict):
        if not result.get("success", False):
            return
        response = result.get("answer", "") or result.get("response", "") or str(result)
    else:
        if not getattr(result, "success", False):
            return
        response = ""
        if result.data:
            if isinstance(result.data, dict):
                response = result.data.get("answer", "") or result.data.get("response", "") or str(result.data)
            elif isinstance(result.data, str):
                response = result.data
    
    if response and len(response) > 10:
        try:
            await memory_agent._run("add_conversation", {
                "user_input": command,
                "response": response[:500]
            })
            logger.debug(f"Stored conversation in memory: {command[:50]}...")
        except Exception as e:
            logger.debug(f"Failed to store conversation: {e}")

# =================================================
# REMINDER PATTERNS
# =================================================

REMINDER_PATTERNS = [
    r"set a reminder for ([\d\.:]+)\s*(am|pm)?\s*(?:to\s*)?(.*?)$",
    r"remind me at ([\d\.:]+)\s*(am|pm)?\s*(?:to\s*)?(.*?)$",
    r"set reminder (?:at|for) ([\d\.:]+)\s*(am|pm)?\s*(?:to\s*)?(.*?)$",
    r"remind (?:me )?at ([\d\.:]+)\s*(am|pm)?\s*(?:about|to|that)?\s*(.*?)$",
]

# =================================================
# DRIVE FILE PATTERNS - FIX for file creation on drives
# =================================================

DRIVE_FILE_PATTERNS = [
    r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
    r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+on\s+([A-Za-z])\s*drive",
    r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z]):",
    r"make\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
    r"new\s+file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
]

# =================================================
# SHUTDOWN PATTERNS
# =================================================

SHUTDOWN_PATTERNS = [
    r"shutdown\s*(?:pc|computer|system)",
    r"power\s*off",
    r"shutdown\s+system",
    r"turn\s*off\s*(?:pc|computer)",
    r"power\s*down",
]

# =================================================
# ENHANCED CONTINUOUS VOICE MODE
# =================================================

async def handle_continuous_voice_mode(workflow_registry: WorkflowRegistry, orchestrator: Orchestrator, voice_agent: VoiceAgent, memory_agent: MemoryAgent, browser_automation=None, filesystem_agent=None):
    user_name = "User"
    if user_manager.get_current_user():
        user_name = user_manager.get_current_user().get('name', 'User')
    
    print("\n" + "="*60)
    print(f"🎤 CONTINUOUS VOICE MODE - CONVERSATIONAL AI v21.04.08")
    print(f"   👤 User: {user_name}")
    print(f"   🕐 Local Time: {user_manager.get_current_time()}")
    print(f"   📅 Local Date: {user_manager.get_current_date()}")
    print("   • No fixed recording windows")
    print("   • VAD detects when you start/stop speaking")
    print("   • JARVIS waits 30s silence before proactive greetings")
    print("   • Can be interrupted while speaking")
    print("   • Full conversation memory")
    print("   • Contextual logical responses")
    print("   • REMINDERS & NOTIFICATIONS supported")
    print("   • FILESYSTEM operations supported")
    print("   • Say 'exit voice', 'quit', or 'goodbye' to stop")
    print("   • Say 'shutdown pc' to shutdown JARVIS and PC")
    print("="*60 + "\n")
    
    hologram_bridge.set_voice_state('listening')
    hologram_bridge.send_text(f'VOICE MODE ACTIVATED - {user_name}')
    
    await voice_agent._run("speak", {"text": f"Conversational voice mode activated for {user_name}. I'll speak naturally with you."})
    
    transcription_queue = asyncio.Queue()
    main_loop = asyncio.get_running_loop()
    
    conversational_mind.conversation_state['waiting_for_response'] = False
    conversational_mind._last_proactive_time = time.time()
    conversational_mind.conversation_state['conversation_depth'] = 0
    
    conversation_history = []
    MAX_HISTORY = 20
    
    is_speaking = False
    stop_speaking_event = asyncio.Event()
    interruption_detected = False
    
    def on_transcription(text: str):
        if is_debug_or_control_message(text):
            logger.debug(f"Skipping debug message: {text[:50]}...")
            return
        asyncio.run_coroutine_threadsafe(
            _add_to_queue(text, transcription_queue),
            main_loop
        )
    
    result = await voice_agent._run("start_streaming", {
        "callback": on_transcription,
        "vad_enabled": True
    })
    
    if not result.get("success"):
        print(f"❌ Failed to start streaming: {result.get('error', 'Unknown error')}")
        hologram_bridge.set_voice_state('error')
        hologram_bridge.send_text('ERROR: Failed to start voice mode')
        await voice_agent._run("speak", {"text": "Failed to start voice mode"})
        return
    
    print(f"🎤 JARVIS is listening and thinking like a human...")
    print(f"   (Speak naturally - I'll know when to respond)")
    print(f"   (JARVIS waits 30s silence before proactive greetings)\n")
    
    waiting_for_response = False
    last_user_activity = time.time()
    proactive_timer = 30
    
    async def speak_with_interrupt(text: str):
        nonlocal is_speaking, interruption_detected
        
        if not text:
            return
        
        is_speaking = True
        interruption_detected = False
        stop_speaking_event.clear()
        
        try:
            print(f"🗣️ JARVIS: {text[:100]}...")
            hologram_bridge.set_voice_state('speaking')
            hologram_bridge.send_text(f"JARVIS: {text[:50]}...")
            
            speak_task = asyncio.create_task(
                voice_agent._run("speak", {"text": text})
            )
            
            while not speak_task.done():
                try:
                    interruption_text = await asyncio.wait_for(
                        transcription_queue.get(), 
                        timeout=0.1
                    )
                    if interruption_text and len(interruption_text.strip()) > 2:
                        print(f"🔊 Interruption detected: {interruption_text[:30]}...")
                        interruption_detected = True
                        await voice_agent._run("stop_speaking", {})
                        speak_task.cancel()
                        await handle_user_input(
                            interruption_text, 
                            orchestrator, 
                            voice_agent, 
                            memory_agent, 
                            browser_automation,
                            filesystem_agent,
                            conversation_history
                        )
                        is_speaking = False
                        hologram_bridge.set_voice_state('listening')
                        print("\n🎤 Listening...")
                        return
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
            
            try:
                await speak_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            if "stop_speaking" not in str(e).lower():
                print(f"⚠️ Speaking error: {e}")
        finally:
            is_speaking = False
            hologram_bridge.set_voice_state('listening')
    
    async def handle_user_input(text, orchestrator, voice_agent, memory_agent, browser_automation, filesystem_agent, history):
        nonlocal interruption_detected, is_speaking
        
        if not text or not text.strip():
            return
        
        history.append({"role": "user", "content": text})
        if len(history) > MAX_HISTORY:
            history.pop(0)
        
        text_lower = text.lower().strip()
        
        # =================================================
        # EXIT AND SHUTDOWN COMMANDS - FIXED
        # =================================================
        exit_phrases = ["exit voice", "stop voice", "exit", "quit", "goodbye", "bye", "stop listening"]
        if any(phrase in text_lower for phrase in exit_phrases):
            return "exit"
        
        # Fixed shutdown detection with better pattern matching
        is_shutdown = False
        for pattern in SHUTDOWN_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                is_shutdown = True
                break
        
        if is_shutdown:
            print("\n🔴 Shutting down JARVIS and PC...")
            hologram_bridge.send_text("SHUTTING DOWN PC...")
            await speak_with_interrupt("Shutting down JARVIS and powering off the computer. Goodbye sir!")
            # Wait for speech to complete
            await asyncio.sleep(1)
            await shutdown_jarvis(voice_agent, shutdown_pc=True)
            return "shutdown"
        
        hologram_bridge.set_voice_state('thinking')
        hologram_bridge.send_text('PROCESSING...')
        
        # =================================================
        # USER MANAGEMENT COMMANDS (Voice)
        # =================================================
        
        if re.search(r"(switch|user|use)\s+user\s+(\w+)", text_lower, re.IGNORECASE):
            match = re.search(r"(switch|user|use)\s+user\s+(\w+)", text_lower, re.IGNORECASE)
            username = match.group(2)
            result = user_manager.switch_user(username)
            if result.get("success"):
                msg = f"Switched to user {username}"
                print(f"👤 {msg}")
                hologram_bridge.send_text(f"USER SWITCHED: {username}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                msg = f"Error: {result.get('error')}"
                print(f"❌ {msg}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return
        
        if re.search(r"create\s+user\s+(\w+)(?:\s+location\s+([a-zA-Z\s]+))?", text_lower, re.IGNORECASE):
            match = re.search(r"create\s+user\s+(\w+)(?:\s+location\s+([a-zA-Z\s]+))?", text_lower, re.IGNORECASE)
            username = match.group(1)
            location = match.group(2).strip() if match.group(2) else None
            
            if not location:
                await speak_with_interrupt(f"Please specify a location for user {username}")
                location = "Unknown"
            
            result = user_manager.create_user(username, location)
            if result.get("success"):
                msg = f"Created user {username} with timezone {user_manager.get_timezone_for_location(location)}"
                print(f"👤 {msg}")
                hologram_bridge.send_text(f"USER CREATED: {username}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                msg = f"Error: {result.get('error')}"
                print(f"❌ {msg}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return
        
        if re.search(r"list\s+users|show\s+users", text_lower, re.IGNORECASE):
            users = user_manager.list_users()
            current = user_manager.current_user
            msg = f"Users: {', '.join(users)}. Current: {current}"
            print(f"👤 {msg}")
            hologram_bridge.send_text(f"USERS: {len(users)}")
            await speak_with_interrupt(msg)
            history.append({"role": "assistant", "content": msg})
            return
        
        if re.search(r"(my info|who am i|user info)", text_lower, re.IGNORECASE):
            user_data = user_manager.get_current_user()
            if user_data:
                msg = f"User: {user_data.get('name')}, Location: {user_data.get('location', 'Unknown')}, Timezone: {user_data.get('timezone', 'UTC')}, Local Time: {user_manager.get_current_time()}"
                print(f"👤 {msg}")
                hologram_bridge.send_text(f"USER INFO")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return
        
        if re.search(r"update\s+location\s+([a-zA-Z\s]+)", text_lower, re.IGNORECASE):
            match = re.search(r"update\s+location\s+([a-zA-Z\s]+)", text_lower, re.IGNORECASE)
            location = match.group(1).strip()
            username = user_manager.current_user
            result = user_manager.update_user_location(username, location)
            if result.get("success"):
                msg = f"Updated location to {location}. New timezone: {user_manager.get_timezone_for_location(location)}"
                print(f"📍 {msg}")
                hologram_bridge.send_text(f"LOCATION UPDATED: {location}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                msg = f"Error: {result.get('error')}"
                print(f"❌ {msg}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return
        
        # =================================================
        # FILESYSTEM COMMANDS (Voice) - DRIVE FILE CREATION FIX
        # =================================================
        
        # Check for drive file creation patterns FIRST
        drive_file_match = None
        for pattern in DRIVE_FILE_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                drive = match.group(2).strip().upper()
                drive_file_match = {"filename": filename, "drive": drive}
                break
        
        if drive_file_match and filesystem_agent:
            filename = drive_file_match["filename"]
            drive = drive_file_match["drive"]
            
            # Check if content is specified
            content = ""
            if " with content " in text:
                parts = text.split(" with content ", 1)
                content = parts[1].strip()
            elif " with " in text and "drive" in text:
                parts = text.split(" with ", 1)
                if "drive" not in parts[0]:
                    content = parts[1].strip()
            
            # Build full path
            file_path = f"{drive}:\\{filename}"
            
            print(f"💾 Creating file: {file_path}")
            hologram_bridge.send_text(f"CREATING: {filename} on {drive}:")
            
            result = await filesystem_agent._run("create_file", {
                "path": file_path,
                "content": content,
                "overwrite": True
            })
            
            if result.get("success"):
                print(f"✅ {result.get('message')}")
                hologram_bridge.send_text(f"FILE CREATED: {filename}")
                await speak_with_interrupt(result.get('message', f"Created {filename} on {drive} drive"))
                history.append({"role": "assistant", "content": result.get('message')})
            else:
                error_msg = result.get('error', 'Failed to create file')
                print(f"❌ {error_msg}")
                hologram_bridge.send_text(f"FILE ERROR: {error_msg[:30]}...")
                await speak_with_interrupt(f"Error creating file: {error_msg}")
                history.append({"role": "assistant", "content": f"Error: {error_msg}"})
            return
        
        if re.search(r"(list|show)\s*drives?", text_lower, re.IGNORECASE):
            if filesystem_agent:
                result = await filesystem_agent._run("list_drives", {})
                if result.get("success"):
                    drives = result.get("drives", [])
                    drive_names = [d.get('drive', '') for d in drives[:3]]
                    msg = f"Found {result.get('count', 0)} drives: {', '.join(drive_names)}"
                    print(f"\n💾 {msg}")
                    hologram_bridge.send_text(f"DRIVES: {result.get('count', 0)}")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
                else:
                    msg = f"Error listing drives: {result.get('error', 'Unknown')}"
                    print(f"\n❌ {msg}")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
            else:
                msg = "FileSystem Agent not available"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        if re.search(r"create\s+(?:a\s+)?file", text_lower, re.IGNORECASE):
            if filesystem_agent:
                parts = text.split("create file", 1)[1].strip() if "create file" in text_lower else text.split("create a file", 1)[1].strip()
                content = ""
                if " with content " in parts:
                    path_part, content = parts.split(" with content ", 1)
                elif " with " in parts:
                    path_part, content = parts.split(" with ", 1)
                else:
                    path_part = parts
                file_path = path_part.strip()
                
                result = await filesystem_agent._run("create_file", {
                    "path": file_path,
                    "content": content,
                    "overwrite": False
                })
                
                if result.get("success"):
                    msg = f"Created file: {file_path}"
                    print(f"\n✅ {msg}")
                    hologram_bridge.send_text(f"FILE CREATED")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
                else:
                    msg = f"Error creating file: {result.get('error', 'Unknown')}"
                    print(f"\n❌ {msg}")
                    hologram_bridge.send_text(f"FILE ERROR")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
            else:
                msg = "FileSystem Agent not available"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        if re.search(r"(list|show)\s+(?:directory|folder|files?|contents?)\s+(?:of\s+)?", text_lower, re.IGNORECASE):
            if filesystem_agent:
                dir_path = re.sub(r"(list|show)\s+(?:directory|folder|files?|contents?)\s+(?:of\s+)?", "", text_lower, flags=re.IGNORECASE).strip()
                if not dir_path:
                    dir_path = "."
                
                result = await filesystem_agent._run("list_directory", {"path": dir_path})
                
                if result.get("success"):
                    items = result.get("items", [])
                    count = result.get("count", 0)
                    msg = f"{dir_path}: {count} items"
                    print(f"\n📁 {msg}")
                    hologram_bridge.send_text(f"LISTED: {dir_path}")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
                else:
                    msg = f"Error listing directory: {result.get('error', 'Unknown')}"
                    print(f"\n❌ {msg}")
                    hologram_bridge.send_text(f"LIST ERROR")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
            else:
                msg = "FileSystem Agent not available"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        if re.search(r"open\s+file", text_lower, re.IGNORECASE) or re.search(r"open\s+[A-Za-z]:", text_lower):
            if filesystem_agent:
                file_match = re.search(r"open\s+file\s+(.+)", text_lower, re.IGNORECASE)
                if file_match:
                    file_path = file_match.group(1).strip()
                else:
                    file_match = re.search(r"open\s+([A-Za-z]:[^\\]*\\.+)", text_lower, re.IGNORECASE)
                    if file_match:
                        file_path = file_match.group(1).strip()
                    else:
                        await speak_with_interrupt("Please specify a file to open")
                        return
                
                result = await filesystem_agent._run("open_file", {"path": file_path})
                
                if result.get("success"):
                    msg = f"Opened: {file_path}"
                    print(f"\n✅ {msg}")
                    hologram_bridge.send_text(f"FILE OPENED")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
                else:
                    msg = f"Error opening file: {result.get('error', 'Unknown')}"
                    print(f"\n❌ {msg}")
                    hologram_bridge.send_text(f"OPEN ERROR")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
            else:
                msg = "FileSystem Agent not available"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        # =================================================
        # TIME QUERY
        # =================================================
        if is_time_query(text):
            current_time = user_manager.get_current_time()
            current_date = user_manager.get_current_date()
            user_name = user_manager.get_current_user().get('name', 'User') if user_manager.get_current_user() else 'User'
            timezone = user_manager.get_current_timezone()
            response = f"The current time for {user_name} is {current_time} on {current_date} ({timezone})."
            print(f"\n🕒 {response}")
            hologram_bridge.send_text(f"TIME: {current_time}")
            await speak_with_interrupt(response)
            history.append({"role": "assistant", "content": response})
            conversational_mind.process_interaction(text, response)
            dummy_result = type('obj', (object,), {'success': True, 'data': {'response': response}})()
            await store_conversation(text, dummy_result, memory_agent)
            return
        
        if is_date_query(text):
            current_date = user_manager.get_current_date()
            user_name = user_manager.get_current_user().get('name', 'User') if user_manager.get_current_user() else 'User'
            response = f"Today's date for {user_name} is {current_date}."
            print(f"\n📅 {response}")
            hologram_bridge.send_text(f"DATE: {current_date}")
            await speak_with_interrupt(response)
            history.append({"role": "assistant", "content": response})
            conversational_mind.process_interaction(text, response)
            dummy_result = type('obj', (object,), {'success': True, 'data': {'response': response}})()
            await store_conversation(text, dummy_result, memory_agent)
            return
        
        if is_weather_query(text):
            clean_query = clean_weather_query(text)
            print(f"🌤️ Searching weather for: {clean_query}")
            hologram_bridge.send_text(f"SEARCHING WEATHER: {clean_query[:30]}...")
            
            search_result = await search_direct(clean_query)
            if search_result:
                response_text = search_result
                print(f"🌤️ {response_text[:200]}...")
                hologram_bridge.send_text(f"WEATHER: {response_text[:50]}...")
                await speak_with_interrupt(response_text)
                history.append({"role": "assistant", "content": response_text})
                conversational_mind.process_interaction(text, response_text)
                dummy_result = type('obj', (object,), {'success': True, 'data': {'response': response_text}})()
                await store_conversation(text, dummy_result, memory_agent)
                return
        
        if is_general_knowledge_query(text):
            print(f"📚 Searching: {text[:50]}...")
            hologram_bridge.send_text(f"SEARCHING: {text[:30]}...")
            
            context_query = text
            if len(history) > 2:
                recent_context = history[-3:-1] if len(history) >= 3 else history[:-1]
                context_parts = []
                for item in recent_context:
                    if item.get("role") == "assistant":
                        context_parts.append(f"Previous: {item['content'][:100]}")
                if context_parts:
                    context_query = f"{text} (Context from previous conversation: {' '.join(context_parts)})"
            
            search_result = await search_direct(context_query)
            if search_result:
                response_text = search_result
                print(f"📚 {response_text[:200]}...")
                hologram_bridge.send_text(f"RESULT: {response_text[:50]}...")
                await speak_with_interrupt(response_text)
                history.append({"role": "assistant", "content": response_text})
                conversational_mind.process_interaction(text, response_text)
                dummy_result = type('obj', (object,), {'success': True, 'data': {'response': response_text}})()
                await store_conversation(text, dummy_result, memory_agent)
                return
        
        # =================================================
        # URL OPENING
        # =================================================
        open_website_patterns = [
            r"open (https?://[^\s]+)",
            r"open (www\.[^\s]+)",
            r"open ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
            r"go to (https?://[^\s]+)",
            r"go to (www\.[^\s]+)",
            r"go to ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
            r"browse (https?://[^\s]+)",
            r"browse (www\.[^\s]+)",
            r"browse ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
            r"visit (https?://[^\s]+)",
            r"visit (www\.[^\s]+)",
            r"visit ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
        ]
        
        url_to_open = None
        for pattern in open_website_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                url_to_open = match.group(1)
                break
        
        if url_to_open:
            print(f"🌐 Opening URL: {url_to_open}")
            hologram_bridge.send_text(f"OPENING: {url_to_open[:30]}...")
            result = await open_browser_url(url_to_open)
            if result.get("success"):
                msg = result.get('message', f"Opened {url_to_open}")
                print(f"✅ {msg}")
                hologram_bridge.send_text(f"OPENED: {url_to_open[:30]}...")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                error_msg = f"Error: {result.get('error', 'Failed to open URL')}"
                print(f"❌ {error_msg}")
                hologram_bridge.send_text(f"ERROR: {error_msg[:30]}...")
                await speak_with_interrupt(error_msg)
                history.append({"role": "assistant", "content": error_msg})
            return
        
        # =================================================
        # REMINDER COMMANDS
        # =================================================
        reminder_match = None
        for pattern in REMINDER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1).strip()
                ampm = match.group(2) if len(match.groups()) >= 2 and match.group(2) else ""
                message = match.group(3).strip() if len(match.groups()) >= 3 else ""
                
                if not message:
                    parts = text.split(time_str, 1)
                    if len(parts) > 1:
                        message = parts[1].strip()
                        message = re.sub(r'^(am|pm|to|about|that|for|at)\s*', '', message, flags=re.IGNORECASE)
                        message = message.strip()
                
                if ampm:
                    time_str = f"{time_str} {ampm}"
                
                if not message:
                    message = "Reminder"
                
                reminder_match = {"time": time_str, "message": message}
                break

        if reminder_match:
            print(f"⏰ Setting reminder for {reminder_match['time']}: {reminder_match['message']}")
            hologram_bridge.send_text(f"SETTING REMINDER: {reminder_match['time'][:30]}...")
            
            result = reminder_system.add_reminder(reminder_match['time'], reminder_match['message'])
            if result.get("success"):
                print(f"✅ {result.get('message')}")
                hologram_bridge.send_text(f"REMINDER SET")
                await speak_with_interrupt(result.get('message', f"Reminder set for {reminder_match['time']}"))
                history.append({"role": "assistant", "content": result.get('message')})
            else:
                error_msg = result.get('error', 'Failed to set reminder')
                print(f"❌ {error_msg}")
                hologram_bridge.send_text(f"REMINDER ERROR")
                await speak_with_interrupt(f"Error setting reminder: {error_msg}")
                history.append({"role": "assistant", "content": f"Error: {error_msg}"})
            return

        # =================================================
        # NOTIFICATION COMMANDS
        # =================================================
        
        if re.search(r"(notification|notif)\s*(summary|count|status)?", text, re.IGNORECASE):
            summary = notification_system.get_summary()
            if summary:
                total = sum(summary.values())
                if total > 0:
                    apps = list(summary.keys())
                    msg = f"You have {total} notifications"
                    print(f"📱 {msg}")
                    hologram_bridge.send_text(f"NOTIFICATIONS: {total}")
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
                else:
                    msg = "You have no notifications"
                    await speak_with_interrupt(msg)
                    history.append({"role": "assistant", "content": msg})
            else:
                msg = "You have no notifications"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        app_match = re.search(r"notifications?\s*(?:from|for)\s*([a-zA-Z\s]+)", text, re.IGNORECASE)
        if app_match:
            app_name = app_match.group(1).strip()
            notifications = notification_system.get_app_notifications(app_name)
            count = notification_system.get_app_count(app_name)
            
            if notifications and count > 0:
                msg = f"You have {count} notifications from {app_name}"
                print(f"📱 {msg}")
                hologram_bridge.send_text(f"{app_name}: {count}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                msg = f"No notifications from {app_name}"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        read_match = re.search(r"read\s*(?:the\s*)?notification\s*(?:from\s*)?([a-zA-Z\s]+)", text, re.IGNORECASE)
        if read_match:
            app_name = read_match.group(1).strip()
            details = notification_system.read_notification(app_name)
            if details:
                msg = f"From {app_name}: {details[:200]}"
                print(f"📱 {msg}")
                hologram_bridge.send_text(f"READING: {app_name}")
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            else:
                msg = f"No notification found from {app_name}"
                await speak_with_interrupt(msg)
                history.append({"role": "assistant", "content": msg})
            return

        # =================================================
        # MEMORY QUERY
        # =================================================
        memory_keywords = [
            "my name", "what is my name", "who am i", "remember me",
            "what do you know about me", "what do you remember"
        ]
        if any(keyword in text_lower for keyword in memory_keywords):
            print(f"🧠 Memory query: {text}")
            result = await memory_agent._run("recall_fact", {"key": "user.name"})
            if result and result.get("success") and result.get("answer"):
                response = result.get("answer")
                print(f"🧠 {response}")
                await speak_with_interrupt(response)
                history.append({"role": "assistant", "content": response})
                await store_conversation(text, result, memory_agent)
                return
        
        # =================================================
        # ORCHESTRATOR WITH CONTEXT
        # =================================================
        print(f"💭 Processing with context-aware AI...")
        
        context_prompt = text
        if len(history) > 3:
            recent_turns = history[-6:-1] if len(history) >= 6 else history[:-1]
            context_lines = []
            for item in recent_turns:
                role = "User" if item["role"] == "user" else "JARVIS"
                content = item["content"][:150]
                context_lines.append(f"{role}: {content}")
            
            if context_lines:
                context_prompt = f"""Previous conversation:
{chr(10).join(context_lines)}

Current question: {text}

Based on the conversation context above, provide a logical and contextual response."""
        
        result = await orchestrator.process(context_prompt)
        
        await store_conversation(text, result, memory_agent)
        
        if result.success and result.data:
            response_text = ""
            if isinstance(result.data, dict):
                response_text = result.data.get("answer") or result.data.get("response") or result.data.get("message") or str(result.data)
            elif isinstance(result.data, str):
                response_text = result.data
            
            if response_text:
                if personality_engine:
                    personality_engine.analyze_interaction(text, response_text)
                    response_text = personality_engine.get_personalized_response(response_text, text)
                
                print(f"🤖 {response_text}")
                hologram_bridge.send_text(f"RESPONSE: {response_text[:50]}...")
                await speak_with_interrupt(response_text)
                history.append({"role": "assistant", "content": response_text})
                conversational_mind.process_interaction(text, response_text)
                
                if not interruption_detected and not is_speaking:
                    follow_up = conversational_mind.get_follow_up(text)
                    if follow_up and len(history) < MAX_HISTORY:
                        await asyncio.sleep(0.8)
                        print(f"🤖 JARVIS: {follow_up}")
                        await speak_with_interrupt(follow_up)
                        history.append({"role": "assistant", "content": follow_up})
                return
        
        fallback_msg = "I'm not sure how to help with that. Could you please rephrase?"
        print(f"🤖 {fallback_msg}")
        await speak_with_interrupt(fallback_msg)
        history.append({"role": "assistant", "content": fallback_msg})
    
    try:
        while True:
            time_since_activity = time.time() - last_user_activity
            
            if (conversational_mind.should_proactively_engage() and 
                not waiting_for_response and 
                not is_speaking and
                time_since_activity > proactive_timer and
                len(conversation_history) > 0):
                
                proactive_message = conversational_mind.get_conversation_starter()
                print(f"\n🤖 JARVIS: {proactive_message}")
                hologram_bridge.set_voice_state('speaking')
                hologram_bridge.send_text(f"JARVIS: {proactive_message[:50]}...")
                
                await speak_with_interrupt(proactive_message)
                conversation_history.append({"role": "assistant", "content": proactive_message})
                conversational_mind.conversation_state['waiting_for_response'] = True
                waiting_for_response = True
                last_user_activity = time.time()
                continue
            
            try:
                text = await asyncio.wait_for(transcription_queue.get(), timeout=0.5)
                
                if not text or not text.strip():
                    continue
                
                if is_debug_or_control_message(text):
                    continue
                
                last_user_activity = time.time()
                waiting_for_response = False
                conversational_mind.conversation_state['waiting_for_response'] = False
                conversational_mind._last_proactive_time = time.time()
                
                print(f"\n📝 You said: {text}")
                hologram_bridge.send_text(f"YOU: {text[:50]}...")
                
                result = await handle_user_input(
                    text, 
                    orchestrator, 
                    voice_agent, 
                    memory_agent, 
                    browser_automation,
                    filesystem_agent,
                    conversation_history
                )
                
                if result == "exit":
                    print("\n👋 Exiting voice mode")
                    hologram_bridge.set_voice_state('idle')
                    hologram_bridge.send_text('VOICE MODE EXITED')
                    await voice_agent._run("speak", {"text": "Goodbye sir, have a great day!"})
                    break
                
                if result == "shutdown":
                    # Shutdown is handled in handle_user_input
                    break
                
                hologram_bridge.set_voice_state('idle')
                print("\n🎤 Listening...")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Error: {e}")
                hologram_bridge.set_voice_state('error')
                hologram_bridge.send_text(f"ERROR: {str(e)[:30]}...")
                await asyncio.sleep(0.1)
    
    finally:
        await voice_agent._run("stop_streaming", {})
        hologram_bridge.set_voice_state('idle')
        hologram_bridge.send_text('VOICE MODE STOPPED')
        print("\n🛑 Continuous voice mode stopped")

async def _add_to_queue(text: str, queue: asyncio.Queue):
    await queue.put(text)

def format_agent_result(result) -> str:
    if result is None:
        return "❌ Error: No result returned"
    
    if isinstance(result, str):
        return f"🧠 {result}"
    
    if isinstance(result, dict):
        if result.get("answer"):
            return f"📝 {result['answer']}"
        if result.get("response"):
            return f"🧠 JARVIS: {result['response']}"
        if result.get("results"):
            output = [f"\n🔍 Search Results:"]
            for i, r in enumerate(result.get("results", [])[:5], 1):
                output.append(f"{i}. {r.get('title', 'Untitled')}")
                if r.get("snippet"):
                    output.append(f"   📝 {r['snippet'][:200]}")
            return "\n".join(output)
        if result.get("summary"):
            return f"📝 {result['summary']}"
        if result.get("success") == False:
            return f"❌ Error: {result.get('error', 'Unknown error')}"
        if result.get("message"):
            return f"✅ {result['message']}"
        if result.get("full_report"):
            return f"📊 {result['full_report']}"
        return json.dumps(result, indent=2, default=str)[:2000]
    
    if hasattr(result, 'data'):
        data = result.data
        if data is None:
            return "❌ Error: No data in AgentResult"
        return format_agent_result(data)
    
    return str(result) if result else "✅ Task completed"

def on_assistant_event(event: str, data: dict):
    global voice_agent_ref
    
    if event == "response":
        text = data.get("text", "")
        if text and voice_agent_ref:
            hologram_bridge.set_voice_state('speaking')
            hologram_bridge.send_text(f"RESPONDING: {text[:50]}...")
            asyncio.create_task(speak_text(text, voice_agent_ref))
            asyncio.get_event_loop().call_later(2, lambda: hologram_bridge.set_voice_state('idle'))
    elif event == "error":
        print(f"❌ Assistant error: {data.get('error', 'Unknown')}")
        hologram_bridge.set_voice_state('error')
        hologram_bridge.send_text(f"ERROR: {data.get('error', 'Unknown')[:30]}...")
    elif event == "command":
        print(f"🎯 Command: {data.get('command', '')}")
        hologram_bridge.send_text(f"COMMAND: {data.get('command', '')[:30]}...")
    elif event == "transcription":
        text = data.get("text", "")
        if text:
            print(f"📝 Heard: {text}")
            hologram_bridge.set_voice_state('listening')
            hologram_bridge.send_text(f"HEARD: {text[:50]}...")
    elif event == "assistant_started":
        print("🎤 Real-Time mode started")
        hologram_bridge.set_voice_state('listening')
        hologram_bridge.send_text("REAL-TIME MODE STARTED")
    elif event == "assistant_stopped":
        print("🛑 Real-Time mode stopped")
        hologram_bridge.set_voice_state('idle')
        hologram_bridge.send_text("REAL-TIME MODE STOPPED")
    elif event == "processing":
        print("⏳ Processing...")
        hologram_bridge.set_voice_state('thinking')
        hologram_bridge.send_text("PROCESSING...")

async def hologram_system_monitor():
    while True:
        try:
            import psutil
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            processes = len(psutil.pids())
            hologram_bridge.update_system(cpu, memory, processes)
        except:
            pass
        await asyncio.sleep(3)

async def main():
    global voice_agent_ref, personality_engine
    
    setup_logging()
    
    print("\n📡 Loading JARVIS OS v21.04.08...")
    print(f"👤 Current User: {user_manager.current_user}")
    print(f"🕐 Local Time: {user_manager.get_current_time()}")
    print(f"📅 Local Date: {user_manager.get_current_date()}")
    print(f"🌍 Timezone: {user_manager.get_current_timezone()}")
    
    print_banner()
    print_help()
    
    # =================================================
    # HOLOGRAM UI HTTP SERVER
    # =================================================
    import webbrowser
    import threading
    import time
    import http.server
    import socketserver
    
    def start_hologram_http_server():
        try:
            hologram_dir = PROJECT_ROOT / "hologram_ui"
            
            if not hologram_dir.exists():
                hologram_dir.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created hologram_ui directory at: {hologram_dir}")
                index_file = hologram_dir / "index.html"
                if not index_file.exists():
                    with open(index_file, 'w') as f:
                        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>JARVIS Hologram UI</title>
    <style>
        body { background: #0a0a1a; color: #00f0ff; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; flex-direction: column; }
        .container { text-align: center; }
        h1 { font-size: 4em; text-shadow: 0 0 20px #00f0ff; }
        .status { font-size: 1.5em; color: #00ff88; }
        .sub { color: #8899aa; margin-top: 20px; }
        .glow { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }
        .user-info { color: #8899aa; font-size: 0.8em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="glow">🔮 JARVIS</h1>
        <div class="status">🟢 System Online</div>
        <div class="sub">Hologram Interface • v21.04.08</div>
        <div class="user-info">Multi-User Support • Location-Based Timezones</div>
        <div class="sub" style="font-size:0.8em; margin-top:30px;">WebSocket: ws://localhost:8765</div>
    </div>
    <script>
        const ws = new WebSocket('ws://localhost:8765');
        ws.onopen = () => console.log('🔗 Connected to JARVIS');
        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === 'text') {
                    document.querySelector('.status').textContent = '📝 ' + data.payload.text;
                }
                if (data.type === 'voice_state') {
                    const states = {
                        'idle': '🟢 Idle',
                        'listening': '🎤 Listening...',
                        'thinking': '🧠 Thinking...',
                        'speaking': '🗣️ Speaking...',
                        'error': '❌ Error'
                    };
                    document.querySelector('.status').textContent = states[data.payload.state] || '🟢 Online';
                }
            } catch(e) {}
        };
    </script>
</body>
</html>""")
                    print("✅ Created hologram index.html")
            
            port = 8766
            handler = http.server.SimpleHTTPRequestHandler
            
            original_cwd = os.getcwd()
            os.chdir(str(hologram_dir))
            
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"🌐 Hologram UI server running at http://localhost:{port}")
                print(f"📁 Serving from: {hologram_dir}")
                
                if (hologram_dir / "index.html").exists():
                    def open_browser():
                        time.sleep(0.5)
                        webbrowser.open(f"http://localhost:{port}")
                        print("🎨 Hologram Dashboard opened in browser")
                    
                    threading.Thread(target=open_browser, daemon=True).start()
                else:
                    print("⚠️ hologram_ui/index.html not found - skipping browser open")
                
                httpd.serve_forever()
                
        except Exception as e:
            print(f"⚠️ Hologram UI server error: {e}")
    
    try:
        ui_server_thread = threading.Thread(target=start_hologram_http_server, daemon=True)
        ui_server_thread.start()
        print("🎨 Starting Hologram UI server on port 8766...")
    except Exception as e:
        print(f"⚠️ Could not start hologram UI server: {e}")
    
    try:
        asyncio.create_task(hologram_bridge.start())
        hologram_bridge.send_text("JARVIS OS v21.04.08 INITIALIZING...")
        hologram_bridge.set_voice_state('idle')
        print("🔗 Hologram WebSocket server started on ws://localhost:8765")
    except Exception as e:
        print(f"⚠️ Hologram WebSocket error: {e}")
    
    orchestrator = Orchestrator()
    workflow_registry = WorkflowRegistry(orchestrator)
    voice_agent = VoiceAgent()
    voice_agent_ref = voice_agent
    memory_agent = MemoryAgent()
    
    filesystem_agent = FileSystemAgent()
    print("💾 FileSystem Agent initialized with full drive access")
    
    asyncio.create_task(hologram_system_monitor())
    
    # =================================================
    # AUTO-SCAN: App Discovery on Startup
    # =================================================
    try:
        print("📡 Discovering installed applications...")
        apps_result = await orchestrator.run("execution_engine", "list_installed_apps", {"force_refresh": True})
        if apps_result.success and apps_result.data:
            app_count = apps_result.data.get("count", 0)
            print(f"✅ Found {app_count} installed applications ready to launch!")
            hologram_bridge.send_text(f"FOUND {app_count} APPS")
        else:
            print("⚠️ Could not discover applications")
    except Exception as e:
        print(f"⚠️ App discovery error: {e}")
    
    # =================================================
    # INITIALIZE REAL-TIME ASSISTANT
    # =================================================
    real_time_assistant = None
    if REAL_TIME_AVAILABLE:
        try:
            real_time_assistant = RealTimeAssistant(orchestrator)
            real_time_assistant.register_callback(on_assistant_event)
            print("🎧 Real-Time Assistant ready")
        except Exception as e:
            print(f"⚠️ Real-Time Assistant error: {e}")
    
    # =================================================
    # INITIALIZE NEW FEATURES
    # =================================================
    
    wake_word = None
    if WAKE_WORD_AVAILABLE:
        try:
            wake_word = WakeWordDetector()
            if wake_word.is_available():
                wake_word.start(lambda: asyncio.create_task(handle_wake_word(voice_agent)))
                print("🔔 Wake word detection active: Say 'Hey JARVIS'")
                hologram_bridge.send_text("WAKE WORD ACTIVE")
            else:
                print("⚠️ Wake word not available. Check PORCUPINE_ACCESS_KEY in .env")
        except Exception as e:
            print(f"⚠️ Wake word error: {e}")
    
    proactive_supervisor = None
    if PROACTIVE_SUPERVISOR_AVAILABLE:
        try:
            proactive_supervisor = ProactiveSupervisor()
            proactive_supervisor.register_callback(
                lambda alert: asyncio.create_task(
                    speak_text(f"Alert sir, {alert.message}", voice_agent)
                )
            )
            await proactive_supervisor.start(interval=30)
            print("🔍 Proactive Supervisor active")
        except Exception as e:
            print(f"⚠️ Proactive Supervisor error: {e}")
    
    browser_automation = None
    if BROWSER_AUTOMATION_AVAILABLE:
        try:
            browser_automation = BrowserAutomation()
            await browser_automation.init(headless=False)
            print("🌐 Browser Automation ready")
        except Exception as e:
            print(f"⚠️ Browser Automation error: {e}")
    
    dashboard_thread = None
    if DASHBOARD_AVAILABLE:
        try:
            dashboard_thread = start_dashboard(port=5000)
            print("🖥️ Dashboard running at http://localhost:5000")
        except Exception as e:
            print(f"⚠️ Dashboard error: {e}")
    
    mobile_thread = None
    if MOBILE_API_AVAILABLE:
        try:
            mobile_thread = threading.Thread(
                target=start_mobile_api,
                args=(5001,),
                daemon=True
            )
            mobile_thread.start()
            print("📱 Mobile API running at http://localhost:5001")
        except Exception as e:
            print(f"⚠️ Mobile API error: {e}")
    
    plugin_manager = None
    if PLUGIN_AVAILABLE:
        try:
            plugin_manager = PluginManager()
            plugin_manager.discover()
            print(f"🔌 Plugins loaded: {len(plugin_manager.get_plugins())}")
        except Exception as e:
            print(f"⚠️ Plugin System error: {e}")
    
    local_llm = None
    if LOCAL_LLM_AVAILABLE:
        try:
            local_llm = LocalLLM()
            if local_llm.is_available():
                print(f"🧠 Local LLM available (model: {local_llm.model})")
            else:
                print("⚠️ Local LLM not available. Start Ollama: ollama serve")
        except Exception as e:
            print(f"⚠️ Local LLM error: {e}")
    
    skill_manager = None
    if SKILLS_AVAILABLE:
        try:
            skill_manager = SkillManager()
            print(f"🎯 Skills loaded: {len(skill_manager.list_skills())}")
        except Exception as e:
            print(f"⚠️ Skills error: {e}")
    
    # =================================================
    # PERSONALITY ENGINE
    # =================================================
    if PERSONALITY_AVAILABLE:
        try:
            personality_engine = PersonalityEngine()
            if ADVANCED_MEMORY_AVAILABLE and advanced_memory:
                personality_engine.set_user_memory(advanced_memory)
                print("🧠 Personality Engine linked with Advanced Memory")
            print("🎭 Personality Engine initialized")
        except Exception as e:
            print(f"⚠️ Personality Engine error: {e}")
            personality_engine = None
    
    context = None
    if CONTEXT_AVAILABLE:
        try:
            context = ConversationContext()
            print("💬 Conversation Context active")
        except Exception as e:
            print(f"⚠️ Context error: {e}")
    
    system_monitor = None
    if SYSTEM_MONITOR_AVAILABLE:
        try:
            system_monitor = SystemMonitor()
            print("📊 System Monitor ready")
        except Exception as e:
            print(f"⚠️ System Monitor error: {e}")
    
    # =================================================
    # SHOW LOADED AGENTS
    # =================================================
    
    agents = orchestrator.list_agents()
    print(f"\n✅ Loaded {len(agents)} agents")
    hologram_bridge.send_text(f"LOADED {len(agents)} AGENTS")
    
    try:
        stats = await memory_agent._run("get_stats", {})
        if stats and stats.get("success"):
            print(f"🧠 Memory: {stats.get('answer', '')}")
    except:
        pass
    
    print("\n" + "=" * 50)
    print(f"🚀 JARVIS OS v21.04.08 Ready!")
    print(f"   👤 User: {user_manager.current_user}")
    print(f"   🕐 Local Time: {user_manager.get_current_time()}")
    print(f"   🌍 Timezone: {user_manager.get_current_timezone()}")
    print("   Type 'help' for commands.")
    print("   Type 'exit' to quit JARVIS.")
    print("   Type 'shutdown pc' to shutdown JARVIS and PC.")
    print("   Type 'continuous voice' for voice control.")
    print("   Type 'real-time' for real-time assistant.")
    print("   Say 'Hey JARVIS' for wake word.")
    print("   Hologram: http://localhost:8766")
    print("   🎭 Personality Engine: Active")
    print("   ⏰ Reminder System: Active")
    print("   📱 Notification System: Active")
    print("   💾 FileSystem Agent: Active")
    print("   👥 Multi-User Support: Active")
    print("=" * 50)
    
    hologram_bridge.send_text(f"JARVIS OS v21.04.08 READY - {user_manager.current_user}")
    hologram_bridge.set_voice_state('idle')
    
    # =================================================
    # AUTO-START CONTINUOUS VOICE MODE
    # =================================================
    print("\n🎤 Starting Continuous Voice Mode automatically...")
    await handle_continuous_voice_mode(workflow_registry, orchestrator, voice_agent, memory_agent, browser_automation, filesystem_agent)
    
    # =================================================
    # MAIN COMMAND LOOP
    # =================================================
    
    try:
        while True:
            try:
                command = input("\n🤖 Jarvis > ").strip()
                
                if not command:
                    continue
                
                command = command.lstrip('>').strip()
                cmd_lower = command.lower()
                
                if is_debug_or_control_message(command):
                    continue
                
                # =================================================
                # EXIT AND SHUTDOWN COMMANDS - FIXED
                # =================================================
                if cmd_lower in {"exit", "quit", "bye"}:
                    print("👋 Goodbye!")
                    hologram_bridge.send_text("GOODBYE")
                    hologram_bridge.set_voice_state('idle')
                    await speak_text("Goodbye sir, have a great day!", voice_agent)
                    break
                
                # Fixed shutdown detection with better pattern matching
                is_shutdown = False
                for pattern in SHUTDOWN_PATTERNS:
                    if re.search(pattern, cmd_lower, re.IGNORECASE):
                        is_shutdown = True
                        break
                
                if is_shutdown:
                    print("\n🔴 Shutting down JARVIS and PC...")
                    hologram_bridge.send_text("SHUTTING DOWN PC...")
                    hologram_bridge.set_voice_state('speaking')
                    await speak_text("Shutting down JARVIS and powering off the computer. Goodbye sir!", voice_agent)
                    hologram_bridge.set_voice_state('idle')
                    # Wait for speech to complete
                    await asyncio.sleep(1)
                    await shutdown_jarvis(voice_agent, shutdown_pc=True)
                    break
                
                if cmd_lower == "help":
                    print_help()
                    continue
                
                # =================================================
                # USER MANAGEMENT COMMANDS
                # =================================================
                
                if re.search(r"list\s+users|show\s+users", cmd_lower, re.IGNORECASE):
                    users = user_manager.list_users()
                    current = user_manager.current_user
                    print(f"\n👤 Users:")
                    print("=" * 40)
                    for u in users:
                        user_data = user_manager.users[u]
                        marker = "👉" if u == current else "  "
                        time_str = user_manager.get_user_time_display(u)
                        tz = user_data.get('timezone', 'UTC')
                        print(f"  {marker} {u} (Time: {time_str}, TZ: {tz})")
                    print("=" * 40)
                    hologram_bridge.send_text(f"USERS: {len(users)}")
                    await speak_text(f"Found {len(users)} users. Current: {current}", voice_agent)
                    continue
                
                if re.search(r"(switch|use)\s+user\s+(\w+)", cmd_lower, re.IGNORECASE):
                    match = re.search(r"(switch|use)\s+user\s+(\w+)", cmd_lower, re.IGNORECASE)
                    username = match.group(2)
                    result = user_manager.switch_user(username)
                    if result.get("success"):
                        user_data = result.get('user', {})
                        tz = user_data.get('timezone', 'UTC')
                        print(f"\n✅ Switched to user '{username}' (Timezone: {tz})")
                        hologram_bridge.send_text(f"USER SWITCHED: {username}")
                        await speak_text(f"Switched to user {username}", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error')}")
                        hologram_bridge.send_text(f"USER ERROR: {result.get('error', '')[:30]}...")
                        await speak_text(f"Error: {result.get('error')}", voice_agent)
                    continue
                
                if re.search(r"create\s+user\s+(\w+)(?:\s+location\s+([a-zA-Z\s]+))?", cmd_lower, re.IGNORECASE):
                    match = re.search(r"create\s+user\s+(\w+)(?:\s+location\s+([a-zA-Z\s]+))?", cmd_lower, re.IGNORECASE)
                    username = match.group(1)
                    location = match.group(2).strip() if match.group(2) else input(f"Enter location for user {username}: ").strip()
                    
                    if not location:
                        location = "Unknown"
                    
                    result = user_manager.create_user(username, location)
                    if result.get("success"):
                        tz = user_manager.get_timezone_for_location(location)
                        print(f"\n✅ Created user '{username}' (Timezone: {tz})")
                        hologram_bridge.send_text(f"USER CREATED: {username}")
                        await speak_text(f"Created user {username} with timezone {tz}", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error')}")
                        hologram_bridge.send_text(f"USER ERROR")
                        await speak_text(f"Error: {result.get('error')}", voice_agent)
                    continue
                
                if re.search(r"(my info|who am i|user info)", cmd_lower, re.IGNORECASE):
                    user_data = user_manager.get_current_user()
                    if user_data:
                        print(f"\n👤 USER INFO:")
                        print("=" * 40)
                        print(f"  Name: {user_data.get('name')}")
                        print(f"  Location: {user_data.get('location', 'Unknown')}")
                        print(f"  Timezone: {user_data.get('timezone', 'UTC')}")
                        print(f"  Local Time: {user_manager.get_current_time()}")
                        print(f"  Local Date: {user_manager.get_current_date()}")
                        print(f"  Created: {user_data.get('created_at', 'Unknown')[:19]}")
                        print(f"  Last Login: {user_data.get('last_login', 'Unknown')[:19]}")
                        print("=" * 40)
                        hologram_bridge.send_text(f"USER INFO: {user_data.get('name')}")
                        await speak_text(f"You are {user_data.get('name')} from {user_data.get('location', 'Unknown')}", voice_agent)
                    else:
                        print("❌ No user data found")
                    continue
                
                if re.search(r"update\s+location\s+([a-zA-Z\s]+)", cmd_lower, re.IGNORECASE):
                    match = re.search(r"update\s+location\s+([a-zA-Z\s]+)", cmd_lower, re.IGNORECASE)
                    location = match.group(1).strip()
                    username = user_manager.current_user
                    result = user_manager.update_user_location(username, location)
                    if result.get("success"):
                        new_tz = user_manager.get_timezone_for_location(location)
                        print(f"\n✅ Updated location to '{location}' (Timezone: {new_tz})")
                        hologram_bridge.send_text(f"LOCATION UPDATED: {location}")
                        await speak_text(f"Updated location to {location}", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error')}")
                        hologram_bridge.send_text(f"LOCATION ERROR")
                        await speak_text(f"Error: {result.get('error')}", voice_agent)
                    continue
                
                if re.search(r"delete\s+user\s+(\w+)", cmd_lower, re.IGNORECASE):
                    match = re.search(r"delete\s+user\s+(\w+)", cmd_lower, re.IGNORECASE)
                    username = match.group(1)
                    result = user_manager.delete_user(username)
                    if result.get("success"):
                        print(f"\n✅ {result.get('message')}")
                        hologram_bridge.send_text(f"USER DELETED: {username}")
                        await speak_text(f"Deleted user {username}", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error')}")
                        hologram_bridge.send_text(f"DELETE ERROR")
                        await speak_text(f"Error: {result.get('error')}", voice_agent)
                    continue
                
                # =================================================
                # FILESYSTEM COMMANDS - WITH DRIVE FILE CREATION FIX
                # =================================================
                
                # Check for drive file creation patterns FIRST (before desktop router)
                drive_file_match = None
                for pattern in DRIVE_FILE_PATTERNS:
                    match = re.search(pattern, cmd_lower, re.IGNORECASE)
                    if match:
                        filename = match.group(1).strip()
                        drive = match.group(2).strip().upper()
                        drive_file_match = {"filename": filename, "drive": drive}
                        break
                
                if drive_file_match:
                    filename = drive_file_match["filename"]
                    drive = drive_file_match["drive"]
                    
                    # Check if content is specified
                    content = ""
                    if " with content " in command:
                        parts = command.split(" with content ", 1)
                        content = parts[1].strip()
                    elif " with " in command and "drive" in command:
                        parts = command.split(" with ", 1)
                        if "drive" not in parts[0]:
                            content = parts[1].strip()
                    
                    # Build full path
                    file_path = f"{drive}:\\{filename}"
                    
                    print(f"💾 Creating file: {file_path}")
                    hologram_bridge.send_text(f"CREATING: {filename} on {drive}:")
                    
                    result = await filesystem_agent._run("create_file", {
                        "path": file_path,
                        "content": content,
                        "overwrite": True
                    })
                    
                    if result.get("success"):
                        print(f"✅ {result.get('message')}")
                        hologram_bridge.send_text(f"FILE CREATED: {filename}")
                        await speak_text(result.get('message', f"Created {filename} on {drive} drive"), voice_agent)
                    else:
                        error_msg = result.get('error', 'Failed to create file')
                        print(f"❌ {error_msg}")
                        hologram_bridge.send_text(f"FILE ERROR: {error_msg[:30]}...")
                        await speak_text(f"Error creating file: {error_msg}", voice_agent)
                    continue
                
                if re.search(r"(list|show)\s*drives?", cmd_lower, re.IGNORECASE):
                    result = await filesystem_agent._run("list_drives", {})
                    
                    if result.get("success"):
                        print("\n💾 AVAILABLE DRIVES:")
                        print("=" * 60)
                        for drive in result.get("drives", []):
                            print(f"  📀 {drive.get('drive', 'Unknown')}")
                            print(f"     Type: {drive.get('type', 'Unknown')}")
                            print(f"     Free: {drive.get('free_human', 'N/A')}")
                            print(f"     Used: {drive.get('used_human', 'N/A')}")
                            print(f"     Total: {drive.get('total_human', 'N/A')}")
                            print()
                        hologram_bridge.send_text(f"DRIVES: {result['count']} found")
                        await speak_text(f"Found {result['count']} drives", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error')}")
                        hologram_bridge.send_text(f"DRIVE ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error listing drives: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if re.search(r"(info|details?)\s*(?:about|for)?\s*drive", cmd_lower, re.IGNORECASE):
                    drive_match = re.search(r"([A-Za-z]):", cmd_lower)
                    if drive_match:
                        drive = f"{drive_match.group(1)}:/"
                        result = await filesystem_agent._run("get_drive_info", {"path": drive})
                        
                        if result.get("success"):
                            info = result.get("drive_info", {})
                            print(f"\n💾 DRIVE: {info.get('drive', 'Unknown')}")
                            print("=" * 50)
                            print(f"  Type: {info.get('type', 'Unknown')}")
                            print(f"  Total: {info.get('total_human', 'N/A')}")
                            print(f"  Used: {info.get('used_human', 'N/A')} ({info.get('percent_used', 0):.1f}%)")
                            print(f"  Free: {info.get('free_human', 'N/A')}")
                            hologram_bridge.send_text(f"DRIVE INFO: {info.get('drive', '')}")
                            await speak_text(f"Drive {info.get('drive', '')}: {info.get('free_human', '')} free", voice_agent)
                        else:
                            print(f"\n❌ {result.get('error', 'Unknown error')}")
                            hologram_bridge.send_text(f"DRIVE INFO ERROR")
                            await speak_text(f"Error getting drive info", voice_agent)
                    else:
                        print("\n❌ Please specify a drive, e.g., 'info for drive C:'")
                        hologram_bridge.send_text("PLEASE SPECIFY DRIVE")
                    continue

                if re.search(r"create\s+(?:a\s+)?file", cmd_lower, re.IGNORECASE):
                    parts = command.split("create file", 1)[1].strip() if "create file" in command.lower() else command.split("create a file", 1)[1].strip()
                    
                    content = ""
                    if " with content " in parts:
                        path_part, content = parts.split(" with content ", 1)
                    elif " with " in parts:
                        path_part, content = parts.split(" with ", 1)
                    else:
                        path_part = parts
                    
                    file_path = path_part.strip()
                    
                    if not re.search(r"^[A-Za-z]:", file_path) and not file_path.startswith("/") and not file_path.startswith("\\"):
                        file_path = f"./{file_path}"
                    
                    result = await filesystem_agent._run("create_file", {
                        "path": file_path,
                        "content": content,
                        "overwrite": False
                    })
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FILE CREATED: {result.get('drive', '')}")
                        await speak_text(f"Created file", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"FILE ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error creating file: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("open file") or re.search(r"open\s+[A-Za-z]:", cmd_lower):
                    if cmd_lower.startswith("open file"):
                        file_path = command.split("open file", 1)[1].strip()
                    else:
                        match = re.search(r"open\s+([A-Za-z]:[^\\]*\\.+)", command, re.IGNORECASE)
                        if match:
                            file_path = match.group(1).strip()
                        else:
                            file_path = command.replace("open", "").strip()
                    
                    result = await filesystem_agent._run("open_file", {"path": file_path})
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FILE OPENED: {result.get('drive', '')}")
                        await speak_text(f"Opened file", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"OPEN ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error opening file: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("read file"):
                    file_path = command.split("read file", 1)[1].strip()
                    
                    result = await filesystem_agent._run("read_file", {"path": file_path})
                    
                    if result.get("success"):
                        print(f"\n📄 {result['path']}:")
                        print("-" * 60)
                        print(result['content'])
                        print("-" * 60)
                        hologram_bridge.send_text(f"FILE READ: {result['path']}")
                        await speak_text(f"File read successfully", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"READ ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error reading file: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if re.search(r"(list|show)\s+(?:directory|folder|files?|contents?)\s+(?:of\s+)?", cmd_lower, re.IGNORECASE):
                    dir_path = re.sub(r"(list|show)\s+(?:directory|folder|files?|contents?)\s+(?:of\s+)?", "", cmd_lower, flags=re.IGNORECASE).strip()
                    
                    if not dir_path:
                        dir_path = "."
                    
                    result = await filesystem_agent._run("list_directory", {
                        "path": dir_path,
                        "show_hidden": False
                    })
                    
                    if result.get("success"):
                        print(f"\n📁 {result['path']}")
                        if result.get("drive_info"):
                            info = result.get("drive_info")
                            print(f"   Drive: {info.get('drive', '')} - Free: {info.get('free_human', '')}")
                        print(f"   📊 {result.get('files', 0)} files, {result.get('directories', 0)} directories")
                        print("-" * 60)
                        
                        items = result.get("items", [])
                        for item in items[:20]:
                            icon = "📁" if item["type"] == "directory" else "📄"
                            size = f" ({item.get('size', 0)} bytes)" if item["type"] == "file" else ""
                            print(f"  {icon} {item['name']}{size}")
                        
                        if len(items) > 20:
                            print(f"  ... and {len(items) - 20} more items")
                        print("-" * 60)
                        
                        hologram_bridge.send_text(f"LISTED: {result['path']}")
                        await speak_text(f"Found {result.get('count', 0)} items", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"LIST ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error listing directory: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("create folder") or cmd_lower.startswith("make folder"):
                    folder_path = command.split("folder", 1)[1].strip()
                    
                    result = await filesystem_agent._run("create_folder", {
                        "path": folder_path,
                        "parents": True
                    })
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FOLDER CREATED: {result.get('drive', '')}")
                        await speak_text(f"Created folder", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"FOLDER ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error creating folder: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("search files"):
                    pattern = command.split("search files", 1)[1].strip()
                    
                    if " in " in pattern:
                        pattern_part, dir_part = pattern.split(" in ", 1)
                        search_path = dir_part.strip()
                    else:
                        pattern_part = pattern
                        search_path = "."
                    
                    result = await filesystem_agent._run("search_files", {
                        "path": search_path,
                        "pattern": pattern_part.strip(),
                        "recursive": True,
                        "max_results": 30
                    })
                    
                    if result.get("success"):
                        print(f"\n🔍 Search results for '{result.get('pattern', '')}' (Found: {result.get('count', 0)})")
                        print("-" * 60)
                        for item in result.get("results", []):
                            icon = "📁" if item["type"] == "directory" else "📄"
                            print(f"  {icon} {item['path']}")
                        if result.get("truncated"):
                            print("  ... (truncated, showing first 30 results)")
                        print("-" * 60)
                        
                        hologram_bridge.send_text(f"SEARCHED: {result.get('pattern', '')}")
                        await speak_text(f"Found {result.get('count', 0)} items", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        hologram_bridge.send_text(f"SEARCH ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error searching: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("delete file"):
                    file_path = command.split("delete file", 1)[1].strip()
                    
                    result = await filesystem_agent._run("delete_file", {"path": file_path})
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FILE DELETED")
                        await speak_text(f"Deleted file", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"DELETE ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error deleting file: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("delete folder"):
                    folder_path = command.split("delete folder", 1)[1].strip()
                    
                    result = await filesystem_agent._run("delete_folder", {"path": folder_path})
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FOLDER DELETED")
                        await speak_text(f"Deleted folder", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        if result.get("suggestion"):
                            print(f"💡 {result.get('suggestion')}")
                        hologram_bridge.send_text(f"DELETE ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error deleting folder: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                if cmd_lower.startswith("copy file") or cmd_lower.startswith("copy "):
                    parts = command.split("copy", 1)[1].strip()
                    if " to " in parts:
                        source, dest = parts.split(" to ", 1)
                        source = source.replace("file", "").strip()
                        dest = dest.strip()
                    else:
                        print("\n❌ Usage: copy file source to destination")
                        hologram_bridge.send_text("COPY USAGE ERROR")
                        continue
                    
                    result = await filesystem_agent._run("copy_file", {
                        "source": source,
                        "destination": dest
                    })
                    
                    if result.get("success"):
                        print(f"\n{result['message']}")
                        hologram_bridge.send_text(f"FILE COPIED")
                        await speak_text(f"File copied", voice_agent)
                    else:
                        print(f"\n❌ {result.get('error', 'Unknown error')}")
                        hologram_bridge.send_text(f"COPY ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error copying file: {result.get('error', 'Unknown')}", voice_agent)
                    continue

                # =================================================
                # REMINDER COMMANDS
                # =================================================
                reminder_match = None
                for pattern in REMINDER_PATTERNS:
                    match = re.search(pattern, cmd_lower, re.IGNORECASE)
                    if match:
                        time_str = match.group(1).strip()
                        ampm = match.group(2) if len(match.groups()) >= 2 and match.group(2) else ""
                        message = match.group(3).strip() if len(match.groups()) >= 3 else ""
                        
                        if not message:
                            parts = cmd_lower.split(time_str, 1)
                            if len(parts) > 1:
                                message = parts[1].strip()
                                message = re.sub(r'^(am|pm|to|about|that|for|at)\s*', '', message, flags=re.IGNORECASE)
                                message = message.strip()
                        
                        if ampm:
                            time_str = f"{time_str} {ampm}"
                        
                        if not message:
                            message = "Reminder"
                        
                        reminder_match = {"time": time_str, "message": message}
                        break

                if reminder_match:
                    print(f"⏰ Setting reminder for {reminder_match['time']}: {reminder_match['message']}")
                    hologram_bridge.send_text(f"SETTING REMINDER: {reminder_match['time']}")
                    
                    result = reminder_system.add_reminder(reminder_match['time'], reminder_match['message'])
                    if result.get("success"):
                        print(f"✅ {result.get('message')}")
                        hologram_bridge.send_text(f"REMINDER SET: {reminder_match['time'][:30]}...")
                        await speak_text(result.get('message', f"Reminder set for {reminder_match['time']}"), voice_agent)
                    else:
                        error_msg = result.get('error', 'Failed to set reminder')
                        print(f"❌ {error_msg}")
                        hologram_bridge.send_text(f"REMINDER ERROR: {error_msg[:30]}...")
                        await speak_text(f"Error setting reminder: {error_msg}", voice_agent)
                    continue

                if re.search(r"(list|show|check)\s*reminders?", cmd_lower, re.IGNORECASE):
                    active = reminder_system.get_active_reminders()
                    if active:
                        msg = f"You have {len(active)} active reminders:"
                        print(f"\n⏰ {msg}")
                        hologram_bridge.send_text(f"REMINDERS: {len(active)} active")
                        for r in active:
                            print(f"   • {r['time_str']}: {r['message']}")
                        await speak_text(f"You have {len(active)} reminders set", voice_agent)
                    else:
                        print("⏰ No active reminders")
                        hologram_bridge.send_text("NO ACTIVE REMINDERS")
                        await speak_text("You have no active reminders", voice_agent)
                    continue

                delete_pattern = r"delete\s*reminder\s*(\d+)"
                delete_match = re.search(delete_pattern, cmd_lower, re.IGNORECASE)
                if delete_match:
                    try:
                        idx = int(delete_match.group(1)) - 1
                        active = reminder_system.get_active_reminders()
                        if 0 <= idx < len(active):
                            removed = active.pop(idx)
                            reminder_system.reminders = [r for r in reminder_system.reminders if r["id"] != removed["id"]]
                            print(f"✅ Deleted reminder: {removed['time_str']} - {removed['message']}")
                            hologram_bridge.send_text(f"REMINDER DELETED")
                            await speak_text(f"Deleted reminder for {removed['time_str']}", voice_agent)
                        else:
                            print(f"❌ Reminder {idx+1} not found")
                            hologram_bridge.send_text("REMINDER NOT FOUND")
                            await speak_text(f"Reminder {idx+1} not found", voice_agent)
                    except Exception as e:
                        print(f"❌ Error deleting reminder: {e}")
                        hologram_bridge.send_text("DELETE ERROR")
                        await speak_text("Error deleting reminder", voice_agent)
                    continue

                # =================================================
                # NOTIFICATION COMMANDS
                # =================================================
                
                if re.search(r"(notification|notif)\s*(summary|count|status)?", cmd_lower, re.IGNORECASE):
                    summary = notification_system.get_summary()
                    if summary:
                        print("\n📱 NOTIFICATION SUMMARY:")
                        hologram_bridge.send_text("NOTIFICATION SUMMARY")
                        total = 0
                        msgs = []
                        for app, count in summary.items():
                            total += count
                            msgs.append(f"{app}: {count}")
                            print(f"   • {app}: {count}")
                        await speak_text(f"You have {total} notifications from {', '.join(msgs[:3])}", voice_agent)
                    else:
                        print("📱 No notifications")
                        hologram_bridge.send_text("NO NOTIFICATIONS")
                        await speak_text("You have no notifications", voice_agent)
                    continue

                app_pattern = r"(?:read|show|tell)\s*(?:me\s*)?notifications?\s*(?:from|for)\s*([a-zA-Z\s]+)"
                app_match = re.search(app_pattern, cmd_lower, re.IGNORECASE)
                if app_match:
                    app_name = app_match.group(1).strip()
                    notifications = notification_system.get_app_notifications(app_name)
                    count = notification_system.get_app_count(app_name)
                    
                    if notifications and count > 0:
                        print(f"📱 {app_name}: {count} notifications")
                        hologram_bridge.send_text(f"{app_name}: {count} notifications")
                        latest = notifications[-1]
                        msg = f"{app_name} notification: {latest.get('message', '')}"
                        print(f"   📝 {msg}")
                        await speak_text(msg, voice_agent)
                    else:
                        print(f"📱 No notifications from {app_name}")
                        hologram_bridge.send_text(f"NO NOTIFICATIONS FROM {app_name}")
                        await speak_text(f"You have no notifications from {app_name}", voice_agent)
                    continue

                read_pattern = r"read\s*(?:the\s*)?notification\s*(?:from\s*)?([a-zA-Z\s]+)\s*(?:\#|number\s*)?(\d+)?"
                read_match = re.search(read_pattern, cmd_lower, re.IGNORECASE)
                if read_match:
                    app_name = read_match.group(1).strip()
                    idx = int(read_match.group(2)) - 1 if read_match.group(2) else 0
                    
                    details = notification_system.read_notification(app_name, idx)
                    if details:
                        print(f"📱 Reading notification from {app_name}: {details}")
                        hologram_bridge.send_text(f"READING: {app_name}")
                        await speak_text(f"From {app_name}: {details[:200]}", voice_agent)
                    else:
                        print(f"📱 No notification found from {app_name}")
                        hologram_bridge.send_text(f"NOTIFICATION NOT FOUND")
                        await speak_text(f"No notification found from {app_name}", voice_agent)
                    continue

                clear_pattern = r"clear\s*(?:all\s*)?notifications?\s*(?:from\s*([a-zA-Z\s]+))?"
                clear_match = re.search(clear_pattern, cmd_lower, re.IGNORECASE)
                if clear_match:
                    app_name = clear_match.group(1).strip() if clear_match.group(1) else None
                    notification_system.clear_notifications(app_name)
                    if app_name:
                        print(f"✅ Cleared notifications from {app_name}")
                        hologram_bridge.send_text(f"CLEARED: {app_name}")
                        await speak_text(f"Cleared notifications from {app_name}", voice_agent)
                    else:
                        print("✅ Cleared all notifications")
                        hologram_bridge.send_text("CLEARED ALL NOTIFICATIONS")
                        await speak_text("Cleared all notifications", voice_agent)
                    continue

                # =================================================
                # PERSONALITY ENGINE COMMANDS
                # =================================================
                if personality_engine and cmd_lower == "show my profile":
                    profile = personality_engine.get_user_profile()
                    if profile:
                        print("\n" + "="*60)
                        print("🎭 USER PROFILE")
                        print("="*60)
                        if profile.get('name'):
                            print(f"👤 Name: {profile['name']}")
                        if profile.get('age'):
                            print(f"📅 Age: {profile['age']}")
                        if profile.get('location'):
                            print(f"📍 Location: {profile['location']}")
                        if profile.get('occupation'):
                            print(f"💼 Occupation: {profile['occupation']}")
                        if profile.get('interests'):
                            print(f"🎯 Interests: {', '.join(profile['interests'])}")
                        if profile.get('personality', {}).get('traits'):
                            traits = profile['personality']['traits']
                            if traits:
                                print(f"\n🧠 Personality Traits:")
                                for trait, value in traits.items():
                                    if isinstance(value, (int, float)):
                                        print(f"   • {trait}: {value:.2f}")
                                    else:
                                        print(f"   • {trait}: {value}")
                        if profile.get('preferences'):
                            print(f"\n⚙️ Preferences:")
                            for key, value in profile['preferences'].items():
                                print(f"   • {key}: {value}")
                        if profile.get('behavior', {}).get('conversation_count'):
                            print(f"\n📊 Conversations: {profile['behavior']['conversation_count']}")
                        if profile.get('updated_at'):
                            print(f"\n🕐 Last Updated: {profile['updated_at']}")
                        print("="*60)
                        hologram_bridge.send_text("PROFILE DISPLAYED")
                    else:
                        print("❌ No profile found")
                    continue
                
                if personality_engine and cmd_lower == "conversation analytics":
                    analytics = personality_engine.get_conversation_analytics()
                    if analytics:
                        print("\n" + "="*60)
                        print("📊 CONVERSATION ANALYTICS")
                        print("="*60)
                        print(f"💬 Total Conversations: {analytics.get('total_conversations', 0)}")
                        print(f"📝 Average Length: {analytics.get('avg_length', 0):.1f} words")
                        print(f"📈 Engagement Score: {analytics.get('engagement_score', 0):.2f}")
                        if analytics.get('frequent_topics'):
                            print(f"\n🔥 Frequent Topics:")
                            for topic, count in analytics.get('frequent_topics', {}).items():
                                print(f"   • {topic}: {count} times")
                        if analytics.get('personality_trend'):
                            print(f"\n📈 Personality Trends:")
                            for trait, values in analytics.get('personality_trend', {}).items():
                                print(f"   • {trait}: {values}")
                        print("="*60)
                        hologram_bridge.send_text("ANALYTICS DISPLAYED")
                    else:
                        print("❌ No analytics available")
                    continue
                
                if personality_engine and cmd_lower == "my personality":
                    traits = personality_engine.get_personality_traits()
                    if traits:
                        print("\n" + "="*60)
                        print("🧠 YOUR PERSONALITY")
                        print("="*60)
                        for trait, value in traits.items():
                            if isinstance(value, (int, float)):
                                bar_length = int(value * 20)
                                bar = "█" * bar_length + "░" * (20 - bar_length)
                                print(f"   {trait.capitalize():15} {bar} {value:.2f}")
                            else:
                                print(f"   {trait.capitalize():15} {value}")
                        print("="*60)
                        hologram_bridge.send_text("PERSONALITY DISPLAYED")
                    else:
                        print("❌ No personality data available")
                    continue
                
                if personality_engine and cmd_lower == "save profile":
                    result = personality_engine.save_profile()
                    if result:
                        print("✅ Profile saved successfully!")
                        hologram_bridge.send_text("PROFILE SAVED")
                    else:
                        print("❌ Failed to save profile")
                    continue
                
                # =================================================
                # HOLOGRAM COMMANDS
                # =================================================
                if cmd_lower.startswith("hologram "):
                    sub_cmd = cmd_lower[9:].strip()
                    if sub_cmd == "status":
                        print(f"🔗 Hologram clients: {len(hologram_bridge.clients)}")
                        print(f"   Voice state: {hologram_bridge.current_state}")
                        print(f"   Persona: {hologram_bridge.current_persona}")
                    elif sub_cmd.startswith("persona "):
                        persona = sub_cmd[8:].strip()
                        if persona in ["jarvis", "friday", "vision", "ultron", "ambient"]:
                            hologram_bridge.set_persona(persona)
                            print(f"🎭 Persona switched to: {persona}")
                            hologram_bridge.send_text(f"PERSONA: {persona.upper()}")
                        else:
                            print(f"❌ Unknown persona: {persona}. Available: jarvis, friday, vision, ultron, ambient")
                    elif sub_cmd == "text" and len(command) > 15:
                        text = command[16:].strip()
                        hologram_bridge.send_text(text)
                        print(f"📝 Sent to hologram: {text}")
                    else:
                        print("Hologram commands:")
                        print("  hologram status          - Show hologram status")
                        print("  hologram persona <name>  - Switch persona (jarvis/friday/vision/ultron/ambient)")
                        print("  hologram text <message>  - Send text to hologram")
                    continue
                
                # =================================================
                # DESKTOP CONTROLLER COMMANDS
                # =================================================
                
                if any(word in cmd_lower for word in ['screenshot', 'capture screen', 'take screenshot']):
                    result = await orchestrator.process("take screenshot")
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"SCREENSHOT: {answer[:30]}...")
                                await speak_text(answer, voice_agent)
                            else:
                                print(f"\n✅ Screenshot taken")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"SCREENSHOT ERROR")
                    continue
                
                if 'volume' in cmd_lower:
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"VOLUME: {answer[:30]}...")
                                await speak_text(answer, voice_agent)
                            else:
                                print(f"\n✅ Volume operation completed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"VOLUME ERROR")
                    continue
                
                if 'brightness' in cmd_lower:
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"BRIGHTNESS: {answer[:30]}...")
                                await speak_text(answer, voice_agent)
                            else:
                                print(f"\n✅ Brightness operation completed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"BRIGHTNESS ERROR")
                    continue
                
                if 'clipboard' in cmd_lower:
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"CLIPBOARD: {answer[:30]}...")
                                await speak_text(answer, voice_agent)
                            else:
                                print(f"\n✅ Clipboard operation completed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"CLIPBOARD ERROR")
                    continue
                
                if cmd_lower.startswith('list files') or cmd_lower.startswith('list directory'):
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"FILES: {answer[:30]}...")
                            else:
                                print(f"\n✅ Files listed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"FILES ERROR")
                    continue
                
                if any(word in cmd_lower for word in ['processes', 'running apps', 'running programs']):
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"PROCESSES: {answer[:30]}...")
                            else:
                                print(f"\n✅ Processes listed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"PROCESSES ERROR")
                    continue
                
                if 'list windows' in cmd_lower:
                    result = await orchestrator.process(command)
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"WINDOWS: {answer[:30]}...")
                            else:
                                print(f"\n✅ Windows listed")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"WINDOWS ERROR")
                    continue
                
                if any(word in cmd_lower for word in ['system info', 'system status', 'system stats', 'check system', 'check systems']):
                    result = await orchestrator.process("system status")
                    if result.success and result.data:
                        if isinstance(result.data, dict):
                            answer = result.data.get("answer", "")
                            if answer:
                                print(f"\n{answer}")
                                hologram_bridge.send_text(f"SYSTEM: {answer[:30]}...")
                                await speak_text(answer, voice_agent)
                            else:
                                print(f"\n✅ System info retrieved")
                        else:
                            print(f"\n✅ {result.data}")
                    else:
                        error_msg = str(result.error) if result and result.error else "Unknown error"
                        print(f"\n❌ {error_msg}")
                        hologram_bridge.send_text(f"SYSTEM ERROR")
                    continue
                
                # =================================================
                # TIME/DATE QUERY
                # =================================================
                if is_time_query(cmd_lower):
                    current_time = user_manager.get_current_time()
                    current_date = user_manager.get_current_date()
                    user_name = user_manager.get_current_user().get('name', 'User') if user_manager.get_current_user() else 'User'
                    timezone = user_manager.get_current_timezone()
                    response = f"The current time for {user_name} is {current_time} on {current_date} ({timezone})."
                    print(f"\n🕒 {response}")
                    hologram_bridge.send_text(f"TIME: {current_time}")
                    await speak_text(response, voice_agent)
                    continue
                
                if is_date_query(cmd_lower):
                    current_date = user_manager.get_current_date()
                    user_name = user_manager.get_current_user().get('name', 'User') if user_manager.get_current_user() else 'User'
                    response = f"Today's date for {user_name} is {current_date}."
                    print(f"\n📅 {response}")
                    hologram_bridge.send_text(f"DATE: {current_date}")
                    await speak_text(response, voice_agent)
                    continue
                
                # =================================================
                # REAL-TIME MODE
                # =================================================
                if cmd_lower in {"real-time", "realtime"}:
                    if real_time_assistant:
                        if real_time_assistant.is_running:
                            real_time_assistant.stop()
                            print("🛑 Real-Time mode stopped")
                            hologram_bridge.send_text("REAL-TIME STOPPED")
                        else:
                            real_time_assistant.start()
                            print("🎤 Real-Time mode started")
                            hologram_bridge.send_text("REAL-TIME STARTED")
                    else:
                        print("❌ Real-Time Assistant not available")
                    continue
                
                if cmd_lower == "real-time status":
                    if real_time_assistant:
                        status = real_time_assistant.get_status()
                        print(f"\n📊 Real-Time Assistant Status:")
                        print(f"   Running: {status['is_running']}")
                        print(f"   Listening: {status['is_listening']}")
                        print(f"   Speaking: {status['is_speaking']}")
                        print(f"   Last activity: {status['last_activity']}")
                        if status.get('current_transcription'):
                            print(f"   Last heard: {status['current_transcription']}")
                    else:
                        print("❌ Real-Time Assistant not available")
                    continue
                
                # =================================================
                # CONTINUOUS VOICE MODE
                # =================================================
                if cmd_lower in {"continuous voice", "continuous", "streaming voice", "voice streaming", "cv", "voice"}:
                    hologram_bridge.send_text("VOICE MODE STARTING...")
                    await handle_continuous_voice_mode(workflow_registry, orchestrator, voice_agent, memory_agent, browser_automation, filesystem_agent)
                    continue
                
                if cmd_lower == "streaming status":
                    status = await voice_agent._run("is_streaming", {})
                    if status.get("success"):
                        is_streaming = status.get("streaming", False)
                        print(f"🎤 Streaming: {'✅ Active' if is_streaming else '❌ Inactive'}")
                        hologram_bridge.send_text(f"STREAMING: {'ACTIVE' if is_streaming else 'INACTIVE'}")
                    else:
                        print("❌ Could not get streaming status")
                    continue
                
                if cmd_lower.startswith("set vad threshold"):
                    try:
                        threshold = float(cmd_lower.split()[-1])
                        result = await voice_agent._run("set_vad_threshold", {"threshold": threshold})
                        if result.get("success"):
                            print(f"✅ VAD threshold set to {threshold:.4f}")
                            hologram_bridge.send_text(f"VAD: {threshold:.4f}")
                        else:
                            print("❌ Failed to set VAD threshold")
                    except:
                        print("❌ Usage: set vad threshold 0.015")
                    continue
                
                # =================================================
                # WEATHER QUERY
                # =================================================
                if is_weather_query(cmd_lower):
                    clean_query = clean_weather_query(command)
                    print(f"🌤️ Searching weather for: {clean_query}")
                    hologram_bridge.send_text(f"WEATHER: {clean_query[:30]}...")
                    
                    search_result = await search_direct(clean_query)
                    if search_result:
                        response_text = search_result
                        print(f"🌤️ {response_text[:200]}...")
                        hologram_bridge.send_text(f"WEATHER RESULT")
                        await speak_text(response_text, voice_agent)
                    else:
                        if browser_automation:
                            result = await browser_automation.search(clean_query)
                            if result.get("success") and result.get("answer"):
                                response_text = result.get("answer")
                                print(f"🌤️ {response_text[:200]}...")
                                hologram_bridge.send_text(f"WEATHER RESULT")
                                await speak_text(response_text, voice_agent)
                            else:
                                result = await orchestrator.process(command)
                                await store_conversation(command, result, memory_agent)
                                if result.success and result.data:
                                    response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                    if response_text:
                                        print(f"🤖 {response_text}")
                                        hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                        await speak_text(response_text, voice_agent)
                        else:
                            result = await orchestrator.process(command)
                            await store_conversation(command, result, memory_agent)
                            if result.success and result.data:
                                response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                if response_text:
                                    print(f"🤖 {response_text}")
                                    hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                    await speak_text(response_text, voice_agent)
                    continue
                
                # =================================================
                # GENERAL KNOWLEDGE
                # =================================================
                if is_general_knowledge_query(cmd_lower):
                    print(f"📚 Searching: {command[:50]}...")
                    hologram_bridge.send_text(f"SEARCHING: {command[:30]}...")
                    
                    search_result = await search_direct(command)
                    if search_result:
                        response_text = search_result
                        print(f"📚 {response_text[:200]}...")
                        hologram_bridge.send_text(f"RESULT FOUND")
                        await speak_text(response_text, voice_agent)
                    else:
                        if browser_automation:
                            result = await browser_automation.search(command)
                            if result.get("success") and result.get("answer"):
                                response_text = result.get("answer")
                                print(f"📚 {response_text[:200]}...")
                                hologram_bridge.send_text(f"RESULT FOUND")
                                await speak_text(response_text, voice_agent)
                            else:
                                result = await orchestrator.process(command)
                                await store_conversation(command, result, memory_agent)
                                if result.success and result.data:
                                    response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                    if response_text:
                                        print(f"🤖 {response_text}")
                                        hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                        await speak_text(response_text, voice_agent)
                        else:
                            result = await orchestrator.process(command)
                            await store_conversation(command, result, memory_agent)
                            if result.success and result.data:
                                response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                if response_text:
                                    print(f"🤖 {response_text}")
                                    hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                    await speak_text(response_text, voice_agent)
                    continue
                
                # =================================================
                # NEWS QUERY
                # =================================================
                if is_news_query(cmd_lower):
                    print(f"📰 Searching news: {command[:50]}...")
                    hologram_bridge.send_text(f"NEWS: {command[:30]}...")
                    
                    search_result = await search_direct(command)
                    if search_result:
                        response_text = search_result
                        print(f"📰 {response_text[:200]}...")
                        hologram_bridge.send_text(f"NEWS RESULT")
                        await speak_text(response_text, voice_agent)
                    else:
                        if browser_automation:
                            result = await browser_automation.search(command)
                            if result.get("success") and result.get("answer"):
                                response_text = result.get("answer")
                                print(f"📰 {response_text[:200]}...")
                                hologram_bridge.send_text(f"NEWS RESULT")
                                await speak_text(response_text, voice_agent)
                            else:
                                result = await orchestrator.process(command)
                                await store_conversation(command, result, memory_agent)
                                if result.success and result.data:
                                    response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                    if response_text:
                                        print(f"🤖 {response_text}")
                                        hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                        await speak_text(response_text, voice_agent)
                        else:
                            result = await orchestrator.process(command)
                            await store_conversation(command, result, memory_agent)
                            if result.success and result.data:
                                response_text = result.data.get("answer") or result.data.get("response") or str(result.data)
                                if response_text:
                                    print(f"🤖 {response_text}")
                                    hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                    await speak_text(response_text, voice_agent)
                    continue
                
                # =================================================
                # OPEN URL / WEBSITE
                # =================================================
                open_website_patterns = [
                    r"open (https?://[^\s]+)",
                    r"open (www\.[^\s]+)",
                    r"open ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                    r"go to (https?://[^\s]+)",
                    r"go to (www\.[^\s]+)",
                    r"go to ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                    r"navigate to (https?://[^\s]+)",
                    r"navigate to (www\.[^\s]+)",
                    r"navigate to ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                    r"browse (https?://[^\s]+)",
                    r"browse (www\.[^\s]+)",
                    r"browse ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                    r"visit (https?://[^\s]+)",
                    r"visit (www\.[^\s]+)",
                    r"visit ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                    r"take me to (https?://[^\s]+)",
                    r"take me to (www\.[^\s]+)",
                    r"take me to ([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)",
                ]
                
                url_to_open = None
                for pattern in open_website_patterns:
                    match = re.search(pattern, cmd_lower, re.IGNORECASE)
                    if match:
                        url_to_open = match.group(1)
                        break
                
                if url_to_open:
                    print(f"🌐 Opening URL: {url_to_open}")
                    hologram_bridge.send_text(f"OPENING: {url_to_open[:30]}...")
                    result = await open_browser_url(url_to_open)
                    if result.get("success"):
                        print(f"✅ {result.get('message')}")
                        hologram_bridge.send_text(f"OPENED: {url_to_open[:30]}...")
                        await speak_text(result.get('message', f"Opened {url_to_open}"), voice_agent)
                    else:
                        print(f"❌ {result.get('error')}")
                        hologram_bridge.send_text(f"ERROR: {result.get('error', 'Unknown')[:30]}...")
                        await speak_text(f"Error: {result.get('error', 'Failed to open URL')}", voice_agent)
                    continue
                
                # =================================================
                # HANDLE SKILLS
                # =================================================
                if skill_manager and cmd_lower.startswith("skill "):
                    skill_name = command[6:].strip()
                    result = skill_manager.execute(skill_name, {})
                    print(f"\n🎯 {result.get('message', 'Skill executed')}")
                    hologram_bridge.send_text(f"SKILL: {skill_name}")
                    if result.get("error"):
                        print(f"❌ Error: {result['error']}")
                        hologram_bridge.send_text(f"SKILL ERROR: {result['error'][:30]}...")
                    await speak_text(result.get('message', ''), voice_agent)
                    continue
                
                if skill_manager and cmd_lower == "list skills":
                    skills = skill_manager.list_skills()
                    print(f"\n🎯 Available Skills: {', '.join(skills)}")
                    continue
                
                # =================================================
                # HANDLE PLUGINS
                # =================================================
                if plugin_manager and cmd_lower.startswith("plugin "):
                    parts = command[7:].split()
                    if len(parts) >= 1:
                        action = parts[0].lower()
                        if action == "list":
                            plugins = plugin_manager.get_plugins()
                            print(f"\n🔌 Plugins:")
                            hologram_bridge.send_text(f"PLUGINS: {len(plugins)} loaded")
                            for p in plugins:
                                status = "✅" if p["enabled"] else "❌"
                                print(f"   {status} {p['name']} v{p['version']} - {p['description']}")
                        elif action == "enable" and len(parts) > 1:
                            plugin_manager.enable(parts[1])
                            print(f"✅ Enabled plugin: {parts[1]}")
                            hologram_bridge.send_text(f"PLUGIN ENABLED: {parts[1]}")
                        elif action == "disable" and len(parts) > 1:
                            plugin_manager.disable(parts[1])
                            print(f"🛑 Disabled plugin: {parts[1]}")
                            hologram_bridge.send_text(f"PLUGIN DISABLED: {parts[1]}")
                        elif action == "run" and len(parts) > 1:
                            result = plugin_manager.execute(parts[1], {})
                            print(f"\n🔌 {result.get('message', 'Plugin executed')}")
                            hologram_bridge.send_text(f"PLUGIN RUN: {parts[1]}")
                            if result.get("error"):
                                print(f"❌ Error: {result['error']}")
                                hologram_bridge.send_text(f"PLUGIN ERROR: {result['error'][:30]}...")
                    continue
                
                # =================================================
                # HANDLE SYSTEM MONITOR
                # =================================================
                if system_monitor and cmd_lower == "system monitor":
                    print("\n📊 Starting System Monitor... (press Ctrl+C to stop)")
                    hologram_bridge.send_text("SYSTEM MONITOR STARTED")
                    threading.Thread(target=system_monitor.run_dashboard, daemon=True).start()
                    continue
                
                # =================================================
                # HANDLE BROWSER COMMANDS
                # =================================================
                if browser_automation and cmd_lower.startswith("browse "):
                    url = command[7:].strip()
                    if not url.startswith("http"):
                        url = "https://" + url
                    result = await browser_automation.goto(url)
                    if result.get("success"):
                        print(f"🌐 Opened: {result.get('title', url)}")
                        hologram_bridge.send_text(f"BROWSER: {result.get('title', url)[:30]}...")
                        await speak_text(f"Opened {result.get('title', url)}", voice_agent)
                    else:
                        print(f"❌ Browser error: {result.get('error')}")
                        hologram_bridge.send_text(f"BROWSER ERROR")
                    continue
                
                if browser_automation and cmd_lower.startswith("search for "):
                    query = command[11:].strip()
                    result = await browser_automation.search(query)
                    if result.get("success"):
                        print(f"🔍 Searched: {query}")
                        hologram_bridge.send_text(f"SEARCH: {query[:30]}...")
                        if result.get("results"):
                            for r in result["results"][:3]:
                                print(f"   • {r.get('title', 'No title')}")
                    else:
                        print(f"❌ Search error: {result.get('error')}")
                        hologram_bridge.send_text(f"SEARCH ERROR")
                    continue
                
                # =================================================
                # HANDLE LOCAL LLM
                # =================================================
                if local_llm and local_llm.is_available() and cmd_lower.startswith("local "):
                    prompt = command[6:].strip()
                    print(f"🧠 Thinking locally...")
                    hologram_bridge.set_voice_state('thinking')
                    hologram_bridge.send_text(f"LOCAL LLM: {prompt[:30]}...")
                    result = local_llm.generate(prompt)
                    if result.get("success"):
                        print(f"\n🧠 {result['response']}")
                        hologram_bridge.send_text(f"LOCAL LLM RESPONSE")
                        await speak_text(result['response'], voice_agent)
                    else:
                        print(f"❌ Local LLM error: {result.get('error')}")
                        hologram_bridge.send_text(f"LOCAL LLM ERROR")
                    hologram_bridge.set_voice_state('idle')
                    continue
                
                # =================================================
                # HANDLE WAKE WORD STATUS
                # =================================================
                if cmd_lower == "wake word status":
                    if wake_word and wake_word.is_available():
                        print("🔔 Wake word active: 'Hey JARVIS'")
                        hologram_bridge.send_text("WAKE WORD: ACTIVE")
                    else:
                        print("🔕 Wake word not available")
                        hologram_bridge.send_text("WAKE WORD: INACTIVE")
                    continue
                
                # =================================================
                # HANDLE PROACTIVE SUPERVISOR
                # =================================================
                if cmd_lower == "proactive status":
                    if proactive_supervisor:
                        status = proactive_supervisor.get_status()
                        alerts = proactive_supervisor.get_alerts(5)
                        print(f"\n🔍 Proactive Supervisor Status:")
                        print(f"   CPU: {status.get('cpu', 0)}%")
                        print(f"   Memory: {status.get('memory', {}).get('percent', 0)}%")
                        print(f"   Alerts: {len(alerts)}")
                        hologram_bridge.send_text(f"PROACTIVE: CPU {status.get('cpu', 0)}% MEM {status.get('memory', {}).get('percent', 0)}%")
                        if alerts:
                            print("   Recent Alerts:")
                            for a in alerts:
                                print(f"      [{a['level']}] {a['message']}")
                    else:
                        print("❌ Proactive Supervisor not available")
                    continue
                
                # =================================================
                # PROCESS THROUGH ORCHESTRATOR
                # =================================================
                hologram_bridge.set_voice_state('thinking')
                hologram_bridge.send_text(f"PROCESSING: {command[:30]}...")
                
                result = await orchestrator.process(command)
                await store_conversation(command, result, memory_agent)
                
                if context and result.success:
                    response_text = ""
                    if result.data:
                        if isinstance(result.data, dict):
                            response_text = result.data.get("answer", "") or result.data.get("response", "") or str(result.data)
                        elif isinstance(result.data, str):
                            response_text = result.data
                    if response_text:
                        context.add_turn(command, response_text)
                
                if result.success:
                    if result.data:
                        if isinstance(result.data, dict):
                            mode = result.data.get("mode", "")
                            if mode in ["time", "date", "weather", "location", "launch", "close", "memory"]:
                                formatted = format_system_result(result.data)
                                print(f"\n{formatted}")
                                hologram_bridge.send_text(f"RESULT: {formatted[:30]}...")
                                if result.data.get("message") or result.data.get("answer"):
                                    response_text = result.data.get("message") or result.data.get("answer")
                                    if PERSONALITY_AVAILABLE and personality_engine and response_text:
                                        response_text = personality_engine.get_personalized_response(response_text, command)
                                    hologram_bridge.set_voice_state('speaking')
                                    await speak_text(response_text, voice_agent)
                            elif mode == "brain":
                                answer = result.data.get('answer', 'Analysis complete.')
                                if PERSONALITY_AVAILABLE and personality_engine:
                                    answer = personality_engine.get_personalized_response(answer, command)
                                print(f"\n🧠 {answer}")
                                hologram_bridge.send_text(f"BRAIN: {answer[:30]}...")
                                hologram_bridge.set_voice_state('speaking')
                                await speak_text(answer, voice_agent)
                            else:
                                if result.data.get("answer"):
                                    answer = result.data['answer']
                                    if PERSONALITY_AVAILABLE and personality_engine:
                                        answer = personality_engine.get_personalized_response(answer, command)
                                    print(f"\n{answer}")
                                    hologram_bridge.send_text(f"RESULT: {answer[:30]}...")
                                    hologram_bridge.set_voice_state('speaking')
                                    await speak_text(answer, voice_agent)
                                elif result.data.get("response"):
                                    response_text = result.data['response']
                                    if PERSONALITY_AVAILABLE and personality_engine:
                                        response_text = personality_engine.get_personalized_response(response_text, command)
                                    print(f"\n🧠 {response_text}")
                                    hologram_bridge.send_text(f"RESPONSE: {response_text[:30]}...")
                                    hologram_bridge.set_voice_state('speaking')
                                    await speak_text(response_text, voice_agent)
                                else:
                                    print(f"\n📊 {json.dumps(result.data, indent=2)}")
                                    hologram_bridge.send_text("TASK COMPLETED")
                        else:
                            print(f"\n📊 {result.data}")
                            hologram_bridge.send_text("TASK COMPLETED")
                    else:
                        print("\n✅ Task completed successfully")
                        hologram_bridge.send_text("TASK COMPLETED")
                else:
                    error_msg = str(result.error) if result and result.error else "Unknown error"
                    print(f"\n❌ Error: {error_msg}")
                    hologram_bridge.set_voice_state('error')
                    hologram_bridge.send_text(f"ERROR: {error_msg[:30]}...")
                    await speak_text(f"Error: {error_msg}", voice_agent)
                
                hologram_bridge.set_voice_state('idle')
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                hologram_bridge.send_text("GOODBYE")
                hologram_bridge.set_voice_state('idle')
                await speak_text("Goodbye sir, have a great day!", voice_agent)
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                hologram_bridge.set_voice_state('error')
                hologram_bridge.send_text(f"ERROR: {str(e)[:30]}...")
                import traceback
                traceback.print_exc()
    
    finally:
        print("\n🧹 Cleaning up resources...")
        
        if personality_engine:
            try:
                personality_engine.save_profile()
                print("   ✅ Personality profile saved")
            except Exception as e:
                print(f"   ⚠️ Personality save error: {e}")
        
        hologram_bridge.stop()
        print("   ✅ Hologram bridge stopped")
        
        try:
            await voice_agent._run("stop_streaming", {})
            print("   ✅ Streaming stopped")
        except:
            pass
        
        if real_time_assistant and real_time_assistant.is_running:
            try:
                real_time_assistant.stop()
                print("   ✅ Real-Time Assistant stopped")
            except Exception as e:
                print(f"   ⚠️ Real-Time Assistant stop error: {e}")
        
        if proactive_supervisor:
            try:
                await proactive_supervisor.stop()
                print("   ✅ Proactive Supervisor stopped")
            except Exception as e:
                print(f"   ⚠️ Proactive Supervisor stop error: {e}")
        
        if browser_automation:
            try:
                await browser_automation.close()
                print("   ✅ Browser closed")
            except Exception as e:
                print(f"   ⚠️ Browser close error: {e}")
        
        if wake_word:
            try:
                wake_word.stop()
                print("   ✅ Wake word stopped")
            except Exception as e:
                print(f"   ⚠️ Wake word stop error: {e}")
        
        print("🧹 Cleanup complete!")

async def handle_wake_word(voice_agent: VoiceAgent):
    print("\n🔊 Wake word detected! Listening...")
    hologram_bridge.set_voice_state('listening')
    hologram_bridge.send_text("WAKE WORD DETECTED")
    await speak_text("Yes sir, how can I help you?", voice_agent)
    hologram_bridge.set_voice_state('idle')

voice_agent_ref = None

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))