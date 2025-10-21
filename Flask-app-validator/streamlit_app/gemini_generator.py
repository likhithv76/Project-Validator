import os
import json
import subprocess
import google.generativeai as genai
from pathlib import Path
from typing import Dict, List, Any

class GeminiTestCaseGenerator:
    def __init__(self):
        self.load_config()
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def load_config(self):
        possible_env_paths = [
            Path(".env"),
            Path(__file__).parent.parent / ".env",
            Path.cwd() / ".env",
        ]
        
        env_file = None
        for path in possible_env_paths:
            if path.exists():
                env_file = path
                break
                
        if env_file:
            with open(env_file, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value

        self.generation_method = os.getenv("TEST_CASE_GENERATOR_METHOD", "AI")
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.parser_fallback = os.getenv("PARSER_FALLBACK_ENABLED", "true").lower() == "true"

# Generate project JSON

    def generate_project_json_with_ai(self, project_dir: str, project_meta: Dict = None) -> Dict:
        if not self.model:
            raise ValueError("Gemini AI not configured. Please set GEMINI_API_KEY in environment variables.")

        try:
            project_analysis = self._analyze_project_structure(project_dir)

            prompt = self._create_generation_prompt(project_analysis, project_meta)

            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception:
                response = self.model.generate_content(prompt)
            project_json = self._parse_ai_response(response.text, project_meta)

            return project_json

        except Exception as e:
            print(f"[GeminiTestCaseGenerator] AI generation failed: {e}")
            if self.parser_fallback:
                print("Falling back to parser-based generation...")
                return self._fallback_to_parser(project_dir, project_meta)
            else:
                raise e

# Analyze project structure
    def _analyze_project_structure(self, project_dir: str) -> Dict:
        analysis = {"files": [], "html_files": [], "python_files": [], "static_files": []}

        for root, _, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_dir)
                analysis["files"].append(rel_path)

                if file.endswith(".html"):
                    analysis["html_files"].append(rel_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            analysis[f"{rel_path}_content"] = f.read()[:2000]
                    except Exception:
                        pass
                elif file.endswith(".py"):
                    analysis["python_files"].append(rel_path)
                elif file.endswith((".css", ".js")):
                    analysis["static_files"].append(rel_path)

        return analysis

# Create generation prompt
    def _create_generation_prompt(self, analysis: Dict, project_meta: Dict = None) -> str:
        project_name = project_meta.get("project", "New Project") if project_meta else "New Project"
        description = project_meta.get("description", "Description of the project") if project_meta else "Description of the project"

        html_files = ", ".join(analysis["html_files"]) or "None"
        python_files = ", ".join(analysis["python_files"]) or "None"

        prompt = f"""
You are an expert in automated test design and Flask web application validation.

Analyze the provided project structure and generate a **realistic, progressive task-based JSON configuration**.
Each task represents a stage of the student's work — from setup verification to functional page testing.

---

### Project Context
Project Name: {project_name}
Project Description: {description}

### Project File Structure
```
app.py
|
templates/
     |
      base.html
      index.html
      about.html
      contact.html
|
static/
     |
      css/
      js/
|
requirements.txt
```

### Sample HTML Content
"""
        for html_file in analysis["html_files"][:3]:
            key = f"{html_file}_content"
            if key in analysis:
                prompt += f"\n#### {html_file}\n{analysis[key]}\n"

        prompt += """
---

### Task Design Strategy

1. **Task 1: Project Setup Verification**
   - **Description**: "Set up your Flask project with the basic file structure including app.py, templates folder, and static folder"
   - **Required Files**: Include ALL essential files: `["app.py", "templates/", "static/", "requirements.txt"]`
   - Points: 5–10 based on complexity.
   - No UI test actions.
   - Validation rules: use "structure" type for file existence checks.

2. **Feature Tasks (Task 2+)**
   - Create one task per functional HTML page or major Python module.
   - Tasks must progress logically (login → register → dashboard → database integration).
   - **CRITICAL**: Each task description must tell students WHAT TO BUILD, not what to validate
   - **Required Files**: Include ALL necessary files for each task (HTML templates, Python files, CSS, JS)
   - For each HTML file containing forms:
     - Identify all input fields.
     - Map inputs to UI test actions.
     - Include both valid and invalid inputs (blank, too short, invalid email, weak password, etc.)
   - For each route in `app.py`:
     - Link HTML templates to Flask routes automatically.
   - Points:
     - Simple form (1–2 inputs): 10 points total.
     - Moderate form (3–5 inputs): 15 points.
     - Complex page (6+ inputs, multiple validations): 20–25 points.
     - Backend / database logic validation: 25–30 points.

3. **Description Guidelines (CRITICAL)**
   - **Project Description**: Brief overview of what the project is about (for students)
   - **Task Description**: ALWAYS write clear, actionable instructions for students on what they need to do
   - **NEVER** write descriptions about validation or testing - only what students should build
   - **Examples of GOOD task descriptions:**
     - "Create a home page that displays a welcome message and navigation menu"
     - "Build a login form with username and password fields that validates user input"
     - "Implement a contact form with name, email, and message fields that submits to /contact"
     - "Create an about page that displays project information and features"
     - "Add a dashboard page that shows user information after login"
   - **Examples of BAD task descriptions:**
     - "Validate that the login form has proper error handling"
     - "Test the contact form submission functionality"
     - "Ensure the home page loads correctly"
     - "Check that all required fields are present"

4. **Scoring Constraints (CRITICAL)**
   - **Total project score**: 70–100 points across all tasks
   - **Static validations**: 40–60% of total points
   - **UI test validations**: 40–60% of total points
   - **Each task's points**: Reflect individual difficulty (5-25 points per task)
   - **Unlock conditions**: `min_score` represents CUMULATIVE score from previous tasks
   - **Progressive unlocking**: 
     - Task 1: `min_score: 0` (no prerequisites)
     - Task 2: `min_score: 5-10` (cumulative from Task 1)
     - Task 3: `min_score: 10-20` (cumulative from Tasks 1+2)
     - Task 4: `min_score: 15-30` (cumulative from Tasks 1+2+3)
     - Task 5: `min_score: 20-40` (cumulative from Tasks 1+2+3+4)
   - **CRITICAL**: `min_score` = cumulative points needed from PREVIOUS tasks, NOT current task points!
   - **Example**: If Task 1=10pts, Task 2=15pts, then Task 3 needs `min_score: 10-20` (from Tasks 1+2)

5. **UI Test Rules (STRICT)**
   - Use simple selectors only:
     - `"selector_type"` ∈ ["id", "name", "class"]
     - `"selector_value"` should be direct, not CSS-chained (e.g., use `"login_button"`, not `"button.login_button"`).
   - Allowed action types:
     - `input_variants` for text fields.
     - `click` for buttons.
   - Example:
     ```json
     {"selector_type": "name", "selector_value": "username", "input_variants": ["", "test_user"]}
     {"selector_type": "type", "selector_value": "submit", "click": true}
     ```
   - Validation example with tag constraints:
     ```json
     {"type": "text_present", "value": "Login Successful", "tag": "h2"}
     {"type": "text_present", "value": "Invalid credentials", "tag": "div"}
     {"type": "text_present", "value": "Email is required", "tag": "label"}
     ```
   - Do not use `navigate` or `css` selectors.
   - Each form field must have at least one positive and one negative input test.

6. **Validation Rules (STRICT)**
   - For static validation rules, use these types:
     - `"structure"` for file existence checks (use "checks" array)
     - `"html"` for HTML content validation (MUST include "file" field)
     - `"requirements"` for package dependencies
     - `"database"` for database validation
     - `"security"` for security features
     - `"runtime"` for Flask route validation
   - **CRITICAL**: HTML validation rules MUST include:
     - `"type": "html"`
     - `"file": "path/to/file.html"` (REQUIRED)
     - `"mustHaveElements": [...]` (optional)
     - `"mustHaveContent": [...]` (optional)
     - `"mustHaveClasses": [...]` (optional)
     - `"points": number`
   - **Examples**:
     ```json
     // Structure validation (for file existence)
     {"type": "structure", "points": 10, "checks": ["app.py exists", "templates folder exists"]}
     
     // HTML validation (for content)
     {"type": "html", "file": "templates/index.html", "mustHaveElements": ["h1", "nav"], "mustHaveContent": ["Welcome"], "points": 15}
     ```
   - For UI test validation, use these types:
     - `"text_present"` for text content validation
     - `"url_redirect"` for URL redirection validation
     - `"status_code"` for HTTP status validation
     - `"tag"` (optional) for text_present: specify HTML tag where text should appear
   - Include at least one success and one failure validation per task.

7. **UI Test Constraints**
   - Verify:
     - Empty form submissions produce error messages.
     - Invalid formats (e.g., wrong email) are caught.
     - Successful submission redirects to the next route or shows success text.
   - Routes should be inferred from Flask conventions (e.g., `/login`, `/register`, `/dashboard`).

8. **Return Format**
   - Return only valid JSON.
   - Each field must have commas between keys.
   - The JSON must follow this schema:
     {
       "project": "Simple Flask Web App",
       "description": "A basic Flask application with home, about, and contact pages",
  "tasks": [
    {
      "id": 1,
           "name": "Project Setup",
           "description": "Set up your Flask project with the basic file structure including app.py, templates folder, and static folder",
           "required_files": ["app.py", "templates/", "static/", "requirements.txt"],
      "validation_rules": {
        "type": "structure",
        "points": 10,
        "checks": ["app.py exists", "templates folder exists", "static folder exists"]
      },
           "playwright_test": {
             "route": "/",
             "actions": [],
             "validate": [
               {"type": "status_code", "value": 200}
             ],
             "points": 5
           },
      "unlock_condition": {"min_score": 0, "required_tasks": []}
    },
    {
      "id": 2,
           "name": "Home Page",
           "description": "Create a home page that displays a welcome message and navigation menu with links to About and Contact pages",
           "required_files": ["templates/index.html", "templates/base.html", "app.py"],
      "validation_rules": {
        "type": "html",
             "file": "templates/index.html",
             "mustHaveElements": ["h1", "nav", "a"],
             "mustHaveContent": ["Welcome", "Home", "About", "Contact"],
        "points": 15
      },
      "playwright_test": {
             "route": "/",
        "actions": [
               {"selector_type": "class", "selector_value": "nav-link", "click": true}
        ],
        "validate": [
               {"type": "text_present", "value": "Welcome", "tag": "h1"},
          {"type": "status_code", "value": 200}
        ],
             "points": 10
      },
      "unlock_condition": {"min_score": 10, "required_tasks": [1]}
    }
  ]
}
   - No extra commentary or Markdown fences.
   - Ensure JSON is syntactically valid.
   - **REMEMBER**: All task descriptions must be instructions for students, NOT validation descriptions!
   - **CRITICAL ERROR TO AVOID**: Never use `"checks"` array with `"type": "html"` - this causes validation errors!
     - Wrong: `{"type": "html", "checks": ["file exists"]}`
     - Correct: `{"type": "structure", "checks": ["file exists"]}` OR `{"type": "html", "file": "path.html", "mustHaveElements": [...]}`
   - **NEVER create empty validation rules**: `"validation_rules": {}` will cause "Unknown rule type" errors
   - **Every task MUST have proper validation rules** - use structure for file checks, html for content validation
   - **SCORING IS CRITICAL**: Ensure `min_score` ≤ total possible points for each task!
     - Wrong: Task with 20 points but `min_score: 50`
     - Correct: Task with 20 points and `min_score: 10-15`
"""
        return prompt

# Parse AI response
    def _parse_ai_response(self, text: str, project_meta: Dict = None) -> Dict:
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        # Try to find complete JSON object
        json_start = text.find('{')
        if json_start != -1:
            # Find the matching closing brace
            brace_count = 0
            json_end = -1
            for i, char in enumerate(text[json_start:], json_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i
                        break
            
            if json_end != -1:
                text = text[json_start:json_end + 1]
            else:
                # If no complete JSON found, try to find the best partial match
                json_end = text.rfind('}')
                if json_end != -1 and json_end > json_start:
                    text = text[json_start:json_end + 1]
        
        text = text.replace('\n"', ',\n"')
        text = text.replace('{\n,', '{\n')
        text = text.replace('[\n,', '[\n')
        text = text.replace('}\n"', '},\n"')
        text = text.replace(']\n"', '],\n"')
        
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict) or "tasks" not in parsed:
                raise ValueError("Invalid JSON structure: missing 'tasks' key")
            
            # Validate task structure and fix common issues
            for task in parsed.get("tasks", []):
                validation_rules = task.get("validation_rules", {})
                
                # Handle case where validation_rules is a list instead of dict
                if isinstance(validation_rules, list):
                    if len(validation_rules) > 0:
                        # Use the first rule if it's a list
                        validation_rules = validation_rules[0]
                    else:
                        validation_rules = {}
                    task["validation_rules"] = validation_rules
                
                # Fix empty validation rules
                if not validation_rules or validation_rules == {}:
                    # Create a basic structure validation rule
                    task["validation_rules"] = {
                        "type": "structure",
                        "points": 10,
                        "checks": ["Required files exist"]
                    }
                
                # Fix incorrect type with checks array
                elif isinstance(validation_rules, dict) and validation_rules.get("type") == "html" and "checks" in validation_rules:
                    validation_rules["type"] = "structure"
                    print(f"[GeminiTestCaseGenerator] Fixed task {task.get('id', '?')}: Changed 'html' to 'structure' for checks array")
                
                # Fix unrealistic scoring requirements
                unlock_condition = task.get("unlock_condition", {})
                if isinstance(unlock_condition, dict):
                    min_score = unlock_condition.get("min_score", 0)
                    validation_points = validation_rules.get("points", 0) if isinstance(validation_rules, dict) else 0
                    ui_test = task.get("playwright_test", {})
                    ui_points = ui_test.get("points", 0) if isinstance(ui_test, dict) else 0
                    total_possible_points = validation_points + ui_points
                    
                    # Calculate reasonable min_score based on task progression
                    task_id = task.get("id", 1)
                    if task_id == 1:
                        # Task 1: No prerequisites
                        reasonable_min_score = 0
                    elif task_id == 2:
                        # Task 2: After Task 1 (5-10 points)
                        reasonable_min_score = min(10, max(5, int(total_possible_points * 0.3)))
                    elif task_id == 3:
                        # Task 3: After Task 2 (10-20 points)
                        reasonable_min_score = min(20, max(10, int(total_possible_points * 0.4)))
                    elif task_id == 4:
                        # Task 4: After Task 3 (15-30 points)
                        reasonable_min_score = min(30, max(15, int(total_possible_points * 0.5)))
                    else:
                        # Task 5+: After previous tasks (20-40 points)
                        reasonable_min_score = min(40, max(20, int(total_possible_points * 0.6)))
                    
                    # Ensure min_score doesn't exceed total possible points
                    reasonable_min_score = min(reasonable_min_score, total_possible_points)
                    
                    # If min_score is unrealistic, fix it
                    if min_score > total_possible_points or min_score > reasonable_min_score * 1.5:
                        unlock_condition["min_score"] = reasonable_min_score
                        print(f"[GeminiTestCaseGenerator] Fixed task {task_id}: Adjusted min_score from {min_score} to {reasonable_min_score} (total possible: {total_possible_points})")
                    
                    # Also fix points if they seem unrealistic
                    if total_possible_points > 50:  # Single task shouldn't have more than 50 points
                        if isinstance(validation_rules, dict) and validation_rules.get("points", 0) > 25:
                            validation_rules["points"] = 25
                            print(f"[GeminiTestCaseGenerator] Fixed task {task_id}: Reduced validation points to 25")
                        if isinstance(ui_test, dict) and ui_test.get("points", 0) > 25:
                            ui_test["points"] = 25
                            print(f"[GeminiTestCaseGenerator] Fixed task {task_id}: Reduced UI test points to 25")
            
            return parsed
        except json.JSONDecodeError as e:
            print(f"[GeminiTestCaseGenerator] JSON parsing failed: {e}")
            print(f"[GeminiTestCaseGenerator] Raw response: {text[:500]}...")
            
            # Try to create a minimal valid JSON as fallback
            print(f"[GeminiTestCaseGenerator] Creating fallback JSON structure...")
            fallback_json = {
                "project": "New Project",
                "description": "Auto-generated project (fallback due to parsing error)",
                "tasks": [
                    {
                        "id": 1,
                        "name": "Project Setup",
                        "description": "Set up the basic project structure",
                        "required_files": ["app.py", "requirements.txt"],
                        "validation_rules": {
                            "type": "structure",
                            "points": 10,
                            "checks": ["app.py exists", "requirements.txt exists"]
                        },
                        "playwright_test": None,
                        "unlock_condition": {"min_score": 0, "required_tasks": []}
                    }
                ]
            }
            return fallback_json

# Fallback to parser if gemini generation fails
    def _fallback_to_parser(self, project_dir: str, project_meta: Dict = None) -> Dict:
        node_script = Path(__file__).parent / "pages" / "autoTestcaseGenerator.js"
        
        try:
            if not node_script.exists():
                raise FileNotFoundError(f"Node.js parser not found: {node_script}")
            
            result = subprocess.run(
                ["node", str(node_script), project_dir],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Node.js parser failed: {result.stderr}")
            
            project_file = Path(project_dir) / "project_tasks.json"
            if not project_file.exists():
                raise FileNotFoundError("Parser did not generate project_tasks.json")
            
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            return project_data
            
        except Exception as e:
            print(f"[GeminiTestCaseGenerator] Parser fallback failed: {e}")
            return {
                "project": project_meta.get("project", "New Project") if project_meta else "New Project",
                "description": project_meta.get("description", "Description of the project") if project_meta else "Description of the project",
                "tasks": []
            }

    # ======================= HELPERS =======================

    def is_ai_enabled(self) -> bool:
        return self.generation_method == "AI" and self.model is not None

    def get_generation_method(self) -> str:
        return self.generation_method
