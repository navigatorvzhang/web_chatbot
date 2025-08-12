# To run the webapp:
# 1. Make sure you have Flask and flask_cors installed (`pip install flask flask-cors openai`)
# 2. Run: python chatbot.py --server
# 3. The server will start at http://localhost:5000
# 4. POST requests can be sent to http://localhost:5000/chat with JSON payload {"message": "...", "context": ...}

# agentic

import openai
from datetime import datetime
import os
import glob
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import shutil
import sys
import argparse

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if not client.api_key:
    raise ValueError("❌ OPENAI_API_KEY environment variable not set")

app = Flask(__name__)
CORS(app, resources={
    r"/*": {  # Allow all routes
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

PROFILE_DIR = 'user_profiles'
CONFIG_FILE = 'chat_config.json'

def is_init_mode():
    """Check if running in initialization mode"""
    return '--init' in sys.argv

def is_command_mode():
    """Check if running in any command mode (init or chat)"""
    return '--init' in sys.argv or '--chat' in sys.argv

def debug_print(*args, **kwargs):
    """Only print debug info when not in command mode, or redirect to stderr"""
    if is_command_mode():
        # Write debug info to stderr instead of stdout
        print(*args, file=sys.stderr, **kwargs)
    else:
        print(*args, **kwargs)

def extract_user_profile(history_files, existing_profile=None):
    """Extract user preferences and update existing profile"""
    debug_print("\n" + "="*50)
    debug_print("EXTRACTING USER PROFILE")
    debug_print("="*50)
    debug_print(f"Input History Length: {len(history_files) if isinstance(history_files, str) else 0}")
    debug_print(f"Existing Profile: {json.dumps(existing_profile, indent=2) if existing_profile else 'None'}")
    
    if not history_files:
        return existing_profile or create_empty_profile()

    if existing_profile:
        # Prompt for updating existing profile
        system_content = f"""Analyze this conversation and update the user profile. 
Existing profile to maintain and extend:
{json.dumps(existing_profile, indent=2)}

Guidelines:
- STRICTLY maintain all items from the existing profile
- Only add new information if it has high confidence
- Use existing category names when possible
- Create new categories only for distinctly new information
"""
    else:
        # Prompt for creating new profile
        system_content = """Analyze the conversation and extract key information in these categories:

1. Personal Information (Highest Priority):
   - Name and preferred names/nicknames
   - Time zone or location mentions
   - Role or occupation
   - Native language/preferred languages
   - Important dates or events mentioned
   - Family or close relationships (if mentioned)
   - Health or well-being mentions (if relevant)
   - Any other personal identifiers (e.g., age, social accounts)

2. User's Interests and Preferences (High Priority):
   - Personal interests, hobbies, likes/dislikes
   - Professional interests
   - Learning goals and aspirations
   - Preferred tools and technologies

3. Communication Style (High Priority):
   - Writing style (formal/casual)
   - Preferred response length
   - Language patterns
   - Question-asking patterns

4. Common Topics Discussed (Medium Priority):
   - Frequently discussed subjects
   - Recurring questions or concerns
   - Project themes
   - Areas of focus

5. Technical Skill Level (Medium Priority):
   - Programming languages known
   - Tools and frameworks used
   - Experience level indicators
   - Learning patterns

Guidelines:
- Create meaningful category names that reflect content importance
- Category names should be snake_case and descriptive
- Keep maximum 10 items per category
- Only include clearly stated information
- Assign confidence levels based on clarity and repetition
"""

    system_content += """
Return format:
{
    "personal_info": [{"item": "...", "category": "...", "confidence": "high/medium/low"}],
    "interests_preferences": [{"item": "...", "category": "...", "confidence": "high/medium/low"}],
    "communication_style": [{"item": "...", "category": "...", "confidence": "high/medium/low"}],
    "common_topics": [{"item": "...", "category": "...", "confidence": "high/medium/low"}],
    "technical_skills": [{"item": "...", "category": "...", "confidence": "high/medium/low"}]
}"""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": history_files}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        content = response.choices[0].message.content
        debug_print("\nPROFILE UPDATE RESPONSE:")
        debug_print("-"*30)
        debug_print(json.dumps(json.loads(content), indent=2))
        debug_print("-"*30 + "\n")
        
        updated_profile = json.loads(content)
        return updated_profile
        
    except Exception as e:
        print(f"\nERROR updating profile: {str(e)}")
        return existing_profile or create_empty_profile()

def create_empty_profile():
    """Create an empty profile with correct structure"""
    return {
        "personal_info": [{"item": "", "category": "", "confidence": ""}],
        "interests_preferences": [{"item": "", "category": "", "confidence": ""}],
        "communication_style": [{"item": "", "category": "", "confidence": ""}],
        "common_topics": [{"item": "", "category": "", "confidence": ""}],
        "technical_skills": [{"item": "", "category": "", "confidence": ""}]
    }

def load_chat_history():
    if not os.path.exists('chat_history'):
        return None
    
    # Get only the most recent chat file
    files = sorted(glob.glob('chat_history/*.txt'), reverse=True)
    if not files:
        return None
    
    latest_file = files[0]
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Extract profile from the latest chat content
        user_profile = extract_user_profile(content)
    
    return {
        'user_profile': user_profile,
        'history_files': [latest_file]
    }

def save_message(file, role, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file.write(f"\n[{timestamp}] {role}:\n{content}\n")
    file.flush()

def save_chat_config(profile_data, chat_file):
    """Save chat configuration to user profiles directory"""
    os.makedirs(PROFILE_DIR, exist_ok=True)
    config_path = os.path.join(PROFILE_DIR, CONFIG_FILE)
    config = {
        'profile': profile_data,
        'chat_file': chat_file,
        'last_updated': datetime.now().isoformat()
    }
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

def load_chat_config():
    """Load chat configuration from user profiles directory"""
    config_path = os.path.join(PROFILE_DIR, CONFIG_FILE)
    debug_print("\n=== Loading Chat Config ===")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            debug_print(f"Loaded config: {json.dumps(config, indent=2)}")
            return config
    debug_print("No existing config found")
    return None

@app.route('/init', methods=['GET'])
def init_session():
    """Initialize chat session with user profile"""
    try:
        # Get ALL recent chat files for comprehensive profile building
        files = sorted(glob.glob('chat_history/*.txt'), reverse=True)
        combined_history = ""
        
        # Load existing profile from config if available
        existing_profile = None
        config = load_chat_config()
        if config and 'profile' in config:
            existing_profile = config['profile']
            debug_print("Using existing profile as base for update")
        
        if files:
            # Include ALL chat history for better profile extraction
            for file in files[:5]:  # Use up to 5 most recent files
                debug_print(f"Including chat history from: {file}")
                with open(file, 'r', encoding='utf-8') as f:
                    combined_history += f.read() + "\n=== NEXT CONVERSATION ===\n"
        
        # Extract profile from ALL history, using existing profile as base
        user_profile = extract_user_profile(combined_history, existing_profile)
        
        # Create new chat file with updated profile
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_chat_file = f"chat_history/chat_{timestamp}.txt"
        
        if not os.path.exists('chat_history'):
            os.makedirs('chat_history')
            
        with open(new_chat_file, 'w', encoding='utf-8') as f:
            save_message(f, "System", f"""=== NEW CHAT SESSION ===
Extracted User Profile:
{json.dumps(user_profile, indent=2)}
=== BEGIN CONVERSATION ===""")
        
        # Save configuration with updated profile
        save_chat_config(user_profile, new_chat_file)
        
        return jsonify({
            'status': 'success',
            'profile': user_profile,
            'chat_file': new_chat_file
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def extract_latest_profile():
    """Extract the latest profile from config file first, then fallback to chat history"""
    debug_print("Loading profile from config file...")
    
    # First try to get profile from config file
    config_path = os.path.join(PROFILE_DIR, CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'profile' in config:
                    debug_print("Successfully loaded profile from config file")
                    return config['profile']
        except Exception as e:
            debug_print(f"Error loading profile from config: {str(e)}")
    
    debug_print("No valid profile found in config, checking chat history...")
    
    # Fallback to chat history files if config doesn't have profile
    files = sorted(glob.glob('chat_history/*.txt'), reverse=True)[:1]
    
    if not files:
        debug_print("No chat history files found")
        return create_empty_profile()
    
    with open(files[0], 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Try to extract profile section from chat file
    try:
        parts = content.split("=== NEW CHAT SESSION ===")
        if len(parts) > 1:
            profile_parts = parts[1].split("=== BEGIN CONVERSATION ===")
            if len(profile_parts) > 0:
                profile_section = profile_parts[0].strip()
                # Extract the JSON part
                try:
                    profile_json = json.loads(profile_section.strip())
                    debug_print("Successfully extracted profile from chat history")
                    return profile_json
                except:
                    debug_print("Failed to parse profile JSON from chat history")
    except Exception as e:
        debug_print(f"Error extracting profile: {str(e)}")
    
    return create_empty_profile()

def get_chat_response(user_input, context=None):
    """Handle chat messages with existing profile"""
    try:
        debug_print("\n" + "="*50)
        debug_print("CHAT RESPONSE REQUEST")
        debug_print("="*50)
        debug_print(f"User Input: {user_input}")
        debug_print(f"Context: {json.dumps(context, indent=2) if context else 'None'}")
        
        messages = []
        context = context or {}
        
        # Extract the latest user profile from chat history
        latest_profile = extract_latest_profile()
        debug_print("Using latest profile for personalization:")
        debug_print(json.dumps(latest_profile, indent=2))
        
        # Always add the latest profile as the first system message
        messages.append({
            "role": "system",
            "content": f"Use this user profile for personalized responses: {json.dumps(latest_profile, indent=2)}"
        })
        
        # Load user profile from chat file with better error handling
        chat_file = context.get('chat_file')
        if not chat_file or not os.path.exists(chat_file):
            # Get chat file from config if not in context
            config = load_chat_config()
            if config:
                chat_file = config['chat_file']
        
        # Add existing conversation context
        if 'messages' in context:
            # Skip the first message if it's a system message (we already added latest profile)
            if context['messages'] and context['messages'][0]['role'] == 'system':
                messages.extend(context['messages'][1:])
            else:
                messages.extend(context['messages'])
        
        messages.append({"role": "user", "content": user_input})
        
        # Ensure chat_history directory exists
        os.makedirs('chat_history', exist_ok=True)
        
        # Get chat file from context or create new one
        chat_file = chat_file or f"chat_history/chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(chat_file, 'a', encoding='utf-8') as f:
            save_message(f, "User", user_input)
            
            debug_print("\nSending to OpenAI:")
            debug_print("-"*30)
            debug_print(json.dumps(messages, indent=2))
            debug_print("-"*30)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            
            assistant_response = response.choices[0].message.content
            debug_print("\nAssistant Response:")
            debug_print("-"*30)
            debug_print(assistant_response)
            debug_print("-"*30 + "\n")
            
            save_message(f, "Assistant", assistant_response)
            
            messages.append({"role": "assistant", "content": assistant_response})
            
            return {
                'response': assistant_response,
                'context': {'messages': messages, 'chat_file': chat_file}
            }
            
    except Exception as e:
        debug_print(f"Error in get_chat_response: {str(e)}")
        return {
            'response': None,
            'error': {
                'message': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
        }
    
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_input = data.get('message', '')
    context = data.get('context', None)
    
    result = get_chat_response(user_input, context)
    return jsonify(result)

def init_standalone():
    """Run initialization without Flask server"""
    try:
        # Get ALL recent chat files for comprehensive profile building
        files = sorted(glob.glob('chat_history/*.txt'), reverse=True)
        combined_history = ""
        
        # Load existing profile from config if available
        existing_profile = None
        config = load_chat_config()
        if config and 'profile' in config:
            existing_profile = config['profile']
        
        if files:
            # Include ALL chat history for better profile extraction
            for file in files[:2]:  # Use up to 5 most recent files
                with open(file, 'r', encoding='utf-8') as f:
                    combined_history += f.read() + "\n=== NEXT CONVERSATION ===\n"
        
        # Extract profile from ALL history, using existing profile as base
        user_profile = extract_user_profile(combined_history, existing_profile)
        
        # Create new chat file with updated profile
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_chat_file = f"chat_history/chat_{timestamp}.txt"
        
        if not os.path.exists('chat_history'):
            os.makedirs('chat_history')
            
        with open(new_chat_file, 'w', encoding='utf-8') as f:
            save_message(f, "System", f"""=== NEW CHAT SESSION ===
Extracted User Profile:
{json.dumps(user_profile, indent=2)}
=== BEGIN CONVERSATION ===""")
        
        # Save configuration with updated profile
        save_chat_config(user_profile, new_chat_file)
        
        return {
            'status': 'success',
            'profile': user_profile,
            'chat_file': new_chat_file
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_true', help='Initialize chat session')
    parser.add_argument('--chat', action='store_true', help='Process chat message')
    parser.add_argument('input_json', nargs='?', default=None, help='Input JSON string for chat')
    
    # Parse known args only to avoid errors with JSON string
    args, unknown = parser.parse_known_args()

    if args.init:
        try:
            # Use standalone function instead of Flask route
            result = init_standalone()
            # Output clean JSON
            sys.stdout.write(json.dumps(result))
            if result['status'] == 'error':
                sys.exit(1)
            else:
                sys.exit(0)
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            sys.stdout.write(json.dumps(error_response))
            sys.exit(1)
    elif args.chat:
        # Process chat message from command line
        try:
            # Get the JSON data either from input_json or unknown args
            if args.input_json:
                input_data = args.input_json
            elif unknown and len(unknown) > 0:
                input_data = unknown[0]
            else:
                raise ValueError("No chat input data provided")
                
            chat_data = json.loads(input_data)
            result = get_chat_response(
                chat_data.get('message', ''),
                chat_data.get('context', None)
            )
            # Clean output - only print the JSON result
            print(json.dumps(result))
            sys.exit(0)
        except Exception as e:
            error_response = {
                'error': {
                    'message': str(e),
                    'type': type(e).__name__
                }
            }
            print(json.dumps(error_response))
            sys.exit(1)
    else:
        app.run(host='0.0.0.0', port=5001, debug=True)