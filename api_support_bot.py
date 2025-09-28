import sqlite3
import json
from openai import OpenAI
from datetime import datetime, timedelta
import random

# OpenRouter Configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
client = None

# Business Constants
MARKETPLACES = ["EU5", "EU", "3PX", "MENA", "AU", "SG", "NA", "JP", "ZA"]
CASE_SOURCES = ["ASTRO", "WINSTON"]
CASE_STATUSES = [
    "SUBMITTED",
    "AWAITING INFORMATION", 
    "CANCELLED",
    "ON-HOLD",
    "WIP",
    "COMPLETED",
]
WORKSTREAMS = [
    "PAID",
    "STRATEGIC_PRODUCT_SMART_CONNECT_EU",
    "DSR",
    "STRATEGIC_PRODUCT_SMART_CONNECT_MENA",
    "STRATEGIC_DEVELOPER_LUXURY_NA",
    "MIGRATION_M@UMP",
    "STRATEGIC_DSR",
    "STRATEGIC_DEVELOPER_LUXURY_EU",
    "F3",
    "LUXURY STORE",
    "STRATEGIC_PRODUCT_SMART_CONNECT_AU",
    "B2B",
    "STRATEGIC_PRODUCT_MFG",
    "BRAND_AGENCY",
    "DSR_3PD",
    "STRATEGIC_PRODUCT_SMART_CONNECT_AES_AU",
]
COMPLEXITIES = ["Easy", "Medium", "Hard"]
PRIORITIES = ["Low", "Medium", "High"]
SELLER_TYPES = ["NEW", "EXISTING"]
SUB_STATUSES = [
    "INT_START",
    "INT_WIP", 
    "ON_HOLD",
    "PMA_DRAF",
    "MAC",
    "PAA_DRAF",
    "AAC",
    "PMA",
    "PAA",
    "ASSIGNED",
    "KO_SENT",
    "PMA_FUP_1",
    "PMA_FUP_2",
    "PMA_FUP_3",
    "PAC",
    "CANCELLED",
    "Case_Created",
    "PMCA",
    "Note",
    "PMA_FUP_4",
    "SUPPORT",
    "HANDOVER",
]

# AI Models
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
        """Create database and tables with updated schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need to add the new column
        cursor.execute("PRAGMA table_info(cases)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'amazon_case_id' not in columns:
            # Drop and recreate table with new schema
            cursor.execute("DROP TABLE IF EXISTS cases")
            cursor.execute("DROP TABLE IF EXISTS updates")
        
        # Cases table with updated schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                amazon_case_id TEXT,
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        # Sample test data with new schema
        test_cases = [
            {
                'case_id': 'CASE-0001',
                'amazon_case_id': 'AMZ-12345678',
                'seller_id': 12345,
                'seller_name': 'TechCorp Solutions',
                'specialist_id': 'SPEC001',
                'specialist_name': 'Alice Johnson',
                'marketplace': 'EU',
                'case_source': 'ASTRO',
                'case_status': 'WIP',
                'workstream': 'STRATEGIC_PRODUCT_SMART_CONNECT_EU',
                'listing_start_date': '2024-01-15',
                'listing_completion_date': '',
                'issue_type': 'API Authentication',
                'complexity': 'Medium',
                'priority': 'High',
                'api_supported': 'Product API',
                'integration_type': 'REST API',
                'seller_type': 'EXISTING',
                'feedback_received': 0,
                'csat_score': None,
                'notes': 'Seller having trouble with API key authentication',
                'last_sub_status': 'INT_WIP',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            },
            {
                'case_id': 'CASE-0002',
                'amazon_case_id': 'AMZ-87654321',
                'seller_id': 67890,
                'seller_name': 'Global Retailers Inc',
                'specialist_id': 'SPEC002',
                'specialist_name': 'Bob Smith',
                'marketplace': 'NA',
                'case_source': 'WINSTON',
                'case_status': 'ON-HOLD',
                'workstream': 'DSR',
                'listing_start_date': '2024-01-10',
                'listing_completion_date': '2024-01-20',
                'issue_type': 'Data Sync Issues',
                'complexity': 'Hard',
                'priority': 'High',
                'api_supported': 'Inventory API',
                'integration_type': 'Webhook',
                'seller_type': 'EXISTING',
                'feedback_received': 1,
                'csat_score': 4.5,
                'notes': 'Inventory not syncing properly, causing oversells',
                'last_sub_status': 'ON_HOLD',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ]
        
        # Insert test cases
        for case in test_cases:
            columns = ', '.join(case.keys())
            placeholders = ', '.join(['?' for _ in case])
            cursor.execute(f"INSERT INTO cases ({columns}) VALUES ({placeholders})", list(case.values()))
        
        # Add some test updates
        test_updates = [
            ('CASE-0001', 'Seller provided API credentials for testing', 'Alice Johnson', 'INT_WIP'),
            ('CASE-0001', 'API key validated successfully', 'Alice Johnson', 'PMA'),
            ('CASE-0002', 'Identified webhook timeout issue', 'Bob Smith', 'ON_HOLD'),
        ]
        
        for case_id, note, updated_by, sub_status in test_updates:
            cursor.execute('''
                INSERT INTO updates (case_id, note, updated_by, timestamp, sub_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (case_id, note, updated_by, datetime.now().isoformat(), sub_status))
        
        conn.commit()
        conn.close()
    
    def extract_case_info(self, text):
        """Extract case information from text"""
        prompt = f"""
        Extract case information from this text: "{text}"
        
        Return ONLY a JSON object with these fields (use null for missing):
        {{
            "seller_name": "company or seller name",
            "amazon_case_id": "Amazon case ID if mentioned (like AMZ-12345678)",
            "marketplace": "one of: {', '.join(MARKETPLACES)}",
            "case_source": "one of: {', '.join(CASE_SOURCES)}",
            "workstream": "one of: {', '.join(WORKSTREAMS)}",
            "issue_type": "brief description of the issue",
            "complexity": "one of: {', '.join(COMPLEXITIES)}",
            "priority": "one of: {', '.join(PRIORITIES)}",
            "seller_type": "one of: {', '.join(SELLER_TYPES)}",
            "api_supported": "Product API/Inventory API/Orders API/Payment API/General API",
            "notes": "detailed description of the issue"
        }}
        
        Return JSON only:
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at extracting structured data from API integration support conversations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=400,
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "API Support Bot"
                }
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if result.startswith('```json'):
                result = result[7:-3]
            elif result.startswith('```'):
                result = result[3:-3]
            
            return json.loads(result)
                
        except Exception as e:
            return {"error": str(e)}
    
    def extract_update_info(self, text):
        """Extract update information from text"""
        prompt = f"""
        Extract update information from: "{text}"
        
        Return ONLY a JSON object:
        {{
            "case_id": "case ID mentioned (like CASE-0001)",
            "note": "what happened or what was done",
            "sub_status": "one of: {', '.join(SUB_STATUSES)}"
        }}
        
        Return JSON only:
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at extracting case update information."
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
            
            if result.startswith('```json'):
                result = result[7:-3]
            elif result.startswith('```'):
                result = result[3:-3]
            
            return json.loads(result)
                
        except Exception as e:
            return {"error": str(e)}
    
    def determine_intent(self, text):
        """Determine user intent"""
        prompt = f"""
        Analyze this text and determine the intent:
        
        Text: "{text}"
        
        Return exactly one of these words: create, update, query
        
        - "create" if this is about a new issue or case
        - "update" if this is about updating an existing case
        - "query" if this is asking for information about a case
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50,
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "API Support Bot"
                }
            )
            
            return response.choices[0].message.content.strip().lower()
                
        except Exception as e:
            return "error"
    
    def create_case_from_data(self, case_data):
        """Create case in database from provided data"""
        # Generate case ID
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cases")
        count = cursor.fetchone()[0]
        case_id = f"CASE-{count + 1:04d}"
        
        # Prepare case data with defaults
        final_case_data = {
            'case_id': case_id,
            'amazon_case_id': case_data.get('amazon_case_id', ''),
            'seller_id': random.randint(10000, 99999),
            'seller_name': case_data.get('seller_name', 'Unknown Seller'),
            'specialist_id': 'SPEC001',
            'specialist_name': 'Demo Specialist',
            'marketplace': case_data.get('marketplace', 'EU'),
            'case_source': case_data.get('case_source', 'ASTRO'),
            'case_status': 'SUBMITTED',
            'workstream': case_data.get('workstream', 'DSR'),
            'listing_start_date': datetime.now().strftime('%Y-%m-%d'),
            'listing_completion_date': '',
            'issue_type': case_data.get('issue_type', 'General Issue'),
            'complexity': case_data.get('complexity', 'Medium'),
            'priority': case_data.get('priority', 'Medium'),
            'api_supported': case_data.get('api_supported', 'General API'),
            'integration_type': 'REST API',
            'seller_type': case_data.get('seller_type', 'EXISTING'),
            'feedback_received': 0,
            'csat_score': None,
            'notes': case_data.get('notes', ''),
            'last_sub_status': 'Case_Created',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        try:
            columns = ', '.join(final_case_data.keys())
            placeholders = ', '.join(['?' for _ in final_case_data])
            cursor.execute(f"INSERT INTO cases ({columns}) VALUES ({placeholders})", list(final_case_data.values()))
            
            # Add initial update
            cursor.execute('''
                INSERT INTO updates (case_id, note, updated_by, timestamp, sub_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                case_id,
                'Case created from chat interface',
                'System',
                datetime.now().isoformat(),
                'Case_Created'
            ))
            
            conn.commit()
            conn.close()
            
            return case_id, final_case_data
            
        except Exception as e:
            conn.close()
            raise Exception(f"Database error: {e}")
    
    def update_case_status(self, case_id, note, sub_status, updated_by="System"):
        """Update case with new substatus"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if case exists
        cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,))
        if not cursor.fetchone():
            conn.close()
            return False, f"Case {case_id} not found"
        
        try:
            # Add update record
            cursor.execute('''
                INSERT INTO updates (case_id, note, updated_by, timestamp, sub_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                case_id,
                note,
                updated_by,
                datetime.now().isoformat(),
                sub_status
            ))
            
            # Update case with latest substatus and map to case status
            status_mapping = {
                'Case_Created': 'SUBMITTED',
                'INT_START': 'WIP',
                'INT_WIP': 'WIP',
                'ON_HOLD': 'ON-HOLD',
                'CANCELLED': 'CANCELLED',
                'HANDOVER': 'COMPLETED',
                'SUPPORT': 'WIP',
                'Note': 'WIP'
            }
            
            new_case_status = status_mapping.get(sub_status, 'WIP')
            
            cursor.execute('''
                UPDATE cases 
                SET last_sub_status = ?, case_status = ?, updated_at = ?
                WHERE case_id = ?
            ''', (sub_status, new_case_status, datetime.now().isoformat(), case_id))
            
            conn.commit()
            conn.close()
            
            return True, f"Case {case_id} updated successfully"
            
        except Exception as e:
            conn.close()
            return False, f"Error updating case: {e}"
    
    def query_case(self, case_id):
        """Get case details"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get case info
        cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
        case = cursor.fetchone()
        
        if not case:
            conn.close()
            return None, "Case not found"
        
        # Get case column names
        columns = [description[0] for description in cursor.description]
        case_dict = dict(zip(columns, case))
        
        # Get recent updates
        cursor.execute('''
            SELECT note, updated_by, timestamp, sub_status 
            FROM updates 
            WHERE case_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''', (case_id,))
        updates = cursor.fetchall()
        conn.close()
        
        return case_dict, updates
    
    def show_all_cases(self):
        """Show summary of all cases"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT case_id, seller_name, marketplace, case_status, priority, issue_type, last_sub_status
            FROM cases 
            ORDER BY updated_at DESC
        ''')
        cases = cursor.fetchall()
        conn.close()
        
        return cases
    
    def change_model(self, tier):
        """Change the AI model being used"""
        if tier in MODELS:
            self.model = MODELS[tier]
            return f"✅ Switched to {tier} model: {self.model}"
        else:
            return f"❌ Invalid tier. Available: {', '.join(MODELS.keys())}"

    # Legacy methods for backward compatibility
    def process_message(self, user_id, message):
        """Process user input - legacy method for compatibility"""
        intent = self.determine_intent(message)
        
        if "create" in intent:
            # Extract information for case creation
            extracted_data = self.extract_case_info(message)
            
            if "error" not in extracted_data:
                # For legacy compatibility, create case directly
                try:
                    case_id, created_case = self.create_case_from_data(extracted_data)
                    
                    return f"""✅ **Case Created!**
                    
**Case ID:** {case_id}
**Seller:** {created_case['seller_name']}
**Marketplace:** {created_case['marketplace']}
**Issue:** {created_case['issue_type']}
**Priority:** {created_case['priority']}
**API:** {created_case['api_supported']}

You can update this case by referencing: {case_id}"""
                except Exception as e:
                    return f"❌ Error creating case: {e}"
            else:
                return f"❌ Error extracting information: {extracted_data['error']}"
        
        elif "update" in intent:
            # Extract update information
            update_data = self.extract_update_info(message)
            
            if "error" not in update_data and update_data.get('case_id'):
                success, message = self.update_case_status(
                    update_data['case_id'],
                    update_data.get('note', 'Update from chat'),
                    update_data.get('sub_status', 'Note'),
                    'Chat User'
                )
                
                if success:
                    return f"✅ **{message}**\n\n**Note:** {update_data.get('note', 'Update recorded')}\n**Sub-status:** {update_data.get('sub_status', 'Note')}"
                else:
                    return f"❌ {message}"
            else:
                return "❌ Please specify a valid case ID and update details."
        
        elif "query" in intent:
            # Extract case ID from message
            words = message.upper().split()
            case_id = None
            for word in words:
                if word.startswith('CASE-'):
                    case_id = word
                    break
            
            if case_id:
                case_dict, updates = self.query_case(case_id)
                
                if case_dict:
                    updates_text = ""
                    if updates:
                        updates_text = "\n\n**Recent Updates:**"
                        for note, updated_by, timestamp, sub_status in updates:
                            date = timestamp.split('T')[0]
                            updates_text += f"\n• {date}: {note} ({sub_status})"
                    
                    return f"""📋 **Case {case_id}**

**Seller:** {case_dict['seller_name']} (ID: {case_dict['seller_id']})
**Amazon Case ID:** {case_dict.get('amazon_case_id', 'Not provided')}
**Marketplace:** {case_dict['marketplace']}
**Issue:** {case_dict['issue_type']}
**Priority:** {case_dict['priority']} | **Status:** {case_dict['case_status']}
**Sub-status:** {case_dict.get('last_sub_status', 'None')}
**API:** {case_dict['api_supported']}
**Workstream:** {case_dict['workstream']}
**Specialist:** {case_dict['specialist_name']}

**Notes:** {case_dict.get('notes', 'None')}{updates_text}"""
                else:
                    return f"❌ Case {case_id} not found"
            else:
                return "❌ Please specify a case ID (e.g., 'show case CASE-0001')"
        
        else:
            return """❓ I'm not sure what you want to do. Try:
- 'New case for [seller] on [marketplace]'
- 'Update CASE-0001: [description]'  
- 'Show case CASE-0001'"""
