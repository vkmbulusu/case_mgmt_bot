import sqlite3
import json
from openai import OpenAI
from datetime import datetime, timedelta
import random

# OpenRouter Configuration - Updated for Streamlit
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Initialize client variable
client = None

# Available models on OpenRouter
MODELS = {
    "fast": "anthropic/claude-3-haiku",
    "balanced": "openai/gpt-3.5-turbo", 
    "smart": "anthropic/claude-3-sonnet",
    "premium": "openai/gpt-4-turbo"
}

class QuickSupportBot:
    def __init__(self, model_tier="balanced", api_key=None):
        global client
        
        if api_key:
            client = OpenAI(
                api_key=api_key,
                base_url=OPENROUTER_BASE_URL,
            )
        
        self.db_path = 'support_demo.db'
        self.model = MODELS[model_tier]
        self.setup_database()
        self.populate_test_data()
    
    def setup_database(self):
        """Create database and tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cases table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                seller_id INTEGER NOT NULL,
                seller_name TEXT NOT NULL,
                specialist_id TEXT NOT NULL,
                specialist_name TEXT NOT NULL,
                marketplace TEXT NOT NULL,
                case_source TEXT NOT NULL,
                case_status TEXT NOT NULL,
                workstream TEXT NOT NULL,
                listing_start_date TEXT,
                listing_completion_date TEXT,
                issue_type TEXT NOT NULL,
                complexity TEXT NOT NULL,
                priority TEXT NOT NULL,
                api_supported TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                seller_type TEXT NOT NULL,
                feedback_received INTEGER NOT NULL,
                csat_score REAL,
                notes TEXT,
                last_sub_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Updates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                note TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sub_status TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def populate_test_data(self):
        """Add sample data for testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM cases")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Sample test data
        test_cases = [
            {
                'case_id': 'CASE-0001',
                'seller_id': 12345,
                'seller_name': 'TechCorp Solutions',
                'specialist_id': 'SPEC001',
                'specialist_name': 'Alice Johnson',
                'marketplace': 'Amazon',
                'case_source': 'Email',
                'case_status': 'Open',
                'workstream': 'Integration',
                'listing_start_date': '2024-01-15',
                'listing_completion_date': '',
                'issue_type': 'API Authentication',
                'complexity': 'Medium',
                'priority': 'High',
                'api_supported': 'Product API',
                'integration_type': 'REST API',
                'seller_type': 'SMB',
                'feedback_received': 0,
                'csat_score': None,
                'notes': 'Seller having trouble with API key authentication',
                'last_sub_status': 'Waiting for Information'
            },
            {
                'case_id': 'CASE-0002',
                'seller_id': 67890,
                'seller_name': 'Global Retailers Inc',
                'specialist_id': 'SPEC002',
                'specialist_name': 'Bob Smith',
                'marketplace': 'eBay',
                'case_source': 'Phone',
                'case_status': 'In Progress',
                'workstream': 'Troubleshooting',
                'listing_start_date': '2024-01-10',
                'listing_completion_date': '2024-01-20',
                'issue_type': 'Data Sync Issues',
                'complexity': 'High',
                'priority': 'Urgent',
                'api_supported': 'Inventory API',
                'integration_type': 'Webhook',
                'seller_type': 'Enterprise',
                'feedback_received': 1,
                'csat_score': 4.5,
                'notes': 'Inventory not syncing properly, causing oversells',
                'last_sub_status': 'Under Investigation'
            },
            {
                'case_id': 'CASE-0003',
                'seller_id': 11111,
                'seller_name': 'StartupXYZ',
                'specialist_id': 'SPEC001',
                'specialist_name': 'Alice Johnson',
                'marketplace': 'Shopify',
                'case_source': 'Chat',
                'case_status': 'Resolved',
                'workstream': 'Onboarding',
                'listing_start_date': '2024-01-05',
                'listing_completion_date': '2024-01-12',
                'issue_type': 'Integration Setup',
                'complexity': 'Low',
                'priority': 'Medium',
                'api_supported': 'Orders API',
                'integration_type': 'GraphQL',
                'seller_type': 'Individual',
                'feedback_received': 1,
                'csat_score': 5.0,
                'notes': 'Successfully completed onboarding process',
                'last_sub_status': 'Completed'
            }
        ]
        
        # Insert test cases
        for case in test_cases:
            columns = ', '.join(case.keys())
            placeholders = ', '.join(['?' for _ in case])
            cursor.execute(f"INSERT INTO cases ({columns}) VALUES ({placeholders})", list(case.values()))
        
        # Add some test updates
        test_updates = [
            ('CASE-0001', 'Seller provided API credentials for testing', 'Alice Johnson', 'Testing Solution'),
            ('CASE-0001', 'API key validated successfully', 'Alice Johnson', 'Ready for Review'),
            ('CASE-0002', 'Identified webhook timeout issue', 'Bob Smith', 'Under Investigation'),
            ('CASE-0002', 'Implementing retry mechanism', 'Bob Smith', 'Testing Solution'),
            ('CASE-0003', 'Onboarding completed successfully', 'Alice Johnson', 'Completed')
        ]
        
        for case_id, note, updated_by, sub_status in test_updates:
            cursor.execute('''
                INSERT INTO updates (case_id, note, updated_by, timestamp, sub_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (case_id, note, updated_by, datetime.now().isoformat(), sub_status))
        
        conn.commit()
        conn.close()
    
    def extract_with_openrouter(self, text, context="general"):
        """Extract information using OpenRouter API with new OpenAI client"""
        if context == "create_case":
            prompt = f"""
            Extract case information from this text: "{text}"
            
            Return ONLY a JSON object with these fields (use null for missing):
            {{
                "seller_name": "company or seller name",
                "marketplace": "Amazon/eBay/Shopify/Walmart/Other",
                "issue_type": "brief description of the issue",
                "priority": "Low/Medium/High/Urgent",
                "api_supported": "Product API/Inventory API/Orders API/Payment API/General API",
                "notes": "detailed description of the issue"
            }}
            
            Examples:
            - If "Product API" is mentioned, use "Product API"
            - If "Inventory API" is mentioned, use "Inventory API"  
            - If no specific API mentioned, use "General API"
            - Priority should be one of: Low, Medium, High, Urgent
            
            Return JSON only:
            """
        elif context == "update_case":
            prompt = f"""
            Extract update information from: "{text}"
            
            Return ONLY a JSON object:
            {{
                "case_id": "case ID mentioned (like CASE-0001)",
                "note": "what happened or what was done",
                "sub_status": "current status if mentioned"
            }}
            
            Return JSON only:
            """
        else:
            prompt = f"""
            Analyze this text and determine the intent. Return ONLY one word:
            
            Text: "{text}"
            
            Return exactly one of these words: create, update, query
            
            - "create" if this is about a new issue or case
            - "update" if this is about updating an existing case
            - "query" if this is asking for information about a case
            """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at extracting structured data from API integration support conversations. Always return valid, clean responses."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300,
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "API Support Bot"
                }
            )
            
            result = response.choices[0].message.content.strip()
            
            if context in ["create_case", "update_case"]:
                # Clean JSON response
                if result.startswith('```json'):
                    result = result[7:-3]
                elif result.startswith('```'):
                    result = result[3:-3]
                
                parsed = json.loads(result)
                return parsed
            else:
                return result.lower().strip()
                
        except json.JSONDecodeError as e:
            return {"error": f"Could not parse AI response: {e}"}
        except Exception as e:
            return {"error": str(e)}
    
    def process_message(self, user_id, message):
        """Process user input"""
        # Determine intent
        intent = self.extract_with_openrouter(message)
        
        if "create" in intent:
            return self.create_case(message)
        elif "update" in intent:
            return self.update_case(message)
        elif "query" in intent:
            return self.query_case(message)
        else:
            return "❓ I'm not sure what you want to do. Try:\n- 'New case for [seller] on [marketplace]'\n- 'Update case [ID]: [description]'\n- 'Show case [ID]'"
    
    def create_case(self, message):
        """Create new case"""
        data = self.extract_with_openrouter(message, "create_case")
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        # Generate case ID
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cases")
        count = cursor.fetchone()[0]
        case_id = f"CASE-{count + 1:04d}"
        
        # Ensure all required fields have values with proper defaults
        def safe_get(field, default):
            value = data.get(field, default)
            return value if value and str(value).strip() else default
        
        # Create case with extracted data and safe defaults
        case_data = {
            'case_id': case_id,
            'seller_id': random.randint(10000, 99999),
            'seller_name': safe_get('seller_name', 'Unknown Seller'),
            'specialist_id': 'SPEC001',
            'specialist_name': 'Demo Specialist',
            'marketplace': safe_get('marketplace', 'Other'),
            'case_source': 'Chat Bot',
            'case_status': 'Open',
            'workstream': 'Integration',
            'listing_start_date': datetime.now().strftime('%Y-%m-%d'),
            'listing_completion_date': '',
            'issue_type': safe_get('issue_type', 'General Issue'),
            'complexity': 'Medium',
            'priority': safe_get('priority', 'Medium'),
            'api_supported': safe_get('api_supported', 'General API'),
            'integration_type': 'REST API',
            'seller_type': 'SMB',
            'feedback_received': 0,
            'csat_score': None,
            'notes': safe_get('notes', ''),
            'last_sub_status': 'New',
            'created_at': datetime.now().isoformat()
        }
        
        try:
            columns = ', '.join(case_data.keys())
            placeholders = ', '.join(['?' for _ in case_data])
            cursor.execute(f"INSERT INTO cases ({columns}) VALUES ({placeholders})", list(case_data.values()))
            conn.commit()
            conn.close()
            
            return f"""✅ **Case Created!**
            
**Case ID:** {case_id}
**Seller:** {case_data['seller_name']}
**Marketplace:** {case_data['marketplace']}
**Issue:** {case_data['issue_type']}
**Priority:** {case_data['priority']}
**API:** {case_data['api_supported']}

You can update this case by referencing: {case_id}"""
            
        except Exception as e:
            conn.close()
            return f"❌ Database error: {e}"
    
    def update_case(self, message):
        """Update existing case"""
        data = self.extract_with_openrouter(message, "update_case")
        
        if "error" in data:
            return f"❌ Error: {data['error']}"
        
        case_id = data.get('case_id')
        if not case_id:
            return "❌ Please specify a case ID (e.g., CASE-0001)"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if case exists
        cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,))
        if not cursor.fetchone():
            conn.close()
            return f"❌ Case {case_id} not found"
        
        # Add update
        try:
            cursor.execute('''
                INSERT INTO updates (case_id, note, updated_by, timestamp, sub_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                case_id,
                data.get('note', 'Update recorded'),
                'Demo User',
                datetime.now().isoformat(),
                data.get('sub_status', '')
            ))
            
            # Update last_sub_status if provided
            if data.get('sub_status'):
                cursor.execute(
                    "UPDATE cases SET last_sub_status = ? WHERE case_id = ?",
                    (data['sub_status'], case_id)
                )
            
            conn.commit()
            conn.close()
            
            return f"✅ **Case {case_id} Updated!**\n\n**Note:** {data.get('note', 'Update recorded')}\n**Status:** {data.get('sub_status', 'No status change')}"
            
        except Exception as e:
            conn.close()
            return f"❌ Error updating case: {e}"
    
    def query_case(self, message):
        """Query case information"""
        # Extract case ID from message
        words = message.upper().split()
        case_id = None
        for word in words:
            if word.startswith('CASE-'):
                case_id = word
                break
        
        if not case_id:
            return "❌ Please specify a case ID (e.g., 'show case CASE-0001')"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get case info
        cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        case = cursor.fetchone()
        
        if not case:
            conn.close()
            return f"❌ Case {case_id} not found"
        
        # Get case column names
        columns = [description[0] for description in cursor.description]
        case_dict = dict(zip(columns, case))
        
        # Get recent updates
        cursor.execute('''
            SELECT note, updated_by, timestamp, sub_status 
            FROM updates 
            WHERE case_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 3
        ''', (case_id,))
        updates = cursor.fetchall()
        conn.close()
        
        # Format response
        updates_text = ""
        if updates:
            updates_text = "\n\n**Recent Updates:**"
            for note, updated_by, timestamp, sub_status in updates:
                date = timestamp.split('T')[0]
                updates_text += f"\n• {date}: {note}"
        
        return f"""📋 **Case {case_id}**

**Seller:** {case_dict['seller_name']} (ID: {case_dict['seller_id']})
**Marketplace:** {case_dict['marketplace']}
**Issue:** {case_dict['issue_type']}
**Priority:** {case_dict['priority']} | **Status:** {case_dict['case_status']}
**API:** {case_dict['api_supported']}
**Specialist:** {case_dict['specialist_name']}

**Notes:** {case_dict.get('notes', 'None')}
**Sub-status:** {case_dict.get('last_sub_status', 'None')}{updates_text}"""
    
    def show_all_cases(self):
        """Show summary of all cases"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT case_id, seller_name, marketplace, case_status, priority, issue_type
            FROM cases 
            ORDER BY case_id
        ''')
        cases = cursor.fetchall()
        conn.close()
        
        if not cases:
            return "No cases found."
        
        result = "📊 **All Cases:**\n\n"
        for case_id, seller, marketplace, status, priority, issue in cases:
            result += f"**{case_id}** - {seller} ({marketplace}) - {status} - {priority} - {issue}\n"
        
        return result
    
    def change_model(self, tier):
        """Change the AI model being used"""
        if tier in MODELS:
            self.model = MODELS[tier]
            return f"✅ Switched to {tier} model: {self.model}"
        else:
            return f"❌ Invalid tier. Available: {', '.join(MODELS.keys())}"
