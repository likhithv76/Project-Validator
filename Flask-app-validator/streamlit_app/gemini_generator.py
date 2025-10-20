import os
import json
import google.generativeai as genai
from pathlib import Path
from typing import Dict, List, Any

class GeminiTestCaseGenerator:
    """
    Generates AI-driven task-based validation JSON for Flask or web projects using Gemini AI.
    Supports fallback to parser if AI generation fails.
    """

    def __init__(self):
        self.load_config()
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def load_config(self):
        """Load API keys and settings from environment or .env file"""
        # Try multiple possible locations for .env file
        possible_env_paths = [
            Path(".env"),  # Current directory
            Path(__file__).parent.parent / ".env",  # Project root from this file
            Path.cwd() / ".env",  # Current working directory
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

    # ======================= MAIN GENERATION =======================

    def generate_project_json_with_ai(self, project_dir: str, project_meta: Dict = None) -> Dict:
        """Generate complete project JSON using Gemini AI"""
        if not self.model:
            raise ValueError("Gemini AI not configured. Please set GEMINI_API_KEY in environment variables.")

        try:
            # Analyze folder and sample contents
            project_analysis = self._analyze_project_structure(project_dir)

            # Create AI prompt
            prompt = self._create_generation_prompt(project_analysis, project_meta)

            # Generate structured JSON with better formatting
            try:
                # Try with structured output if available (newer SDK versions)
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception:
                # Fallback to regular generation
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

    # ======================= PROJECT ANALYSIS =======================

    def _analyze_project_structure(self, project_dir: str) -> Dict:
        """Collect a structured overview of the project for the AI prompt"""
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

    # ======================= PROMPT CREATION =======================

    def _create_generation_prompt(self, analysis: Dict, project_meta: Dict = None) -> str:
        """Construct hierarchical prompt for Gemini AI"""
        project_name = project_meta.get("project", "New Project") if project_meta else "New Project"
        description = project_meta.get("description", "Auto-generated progressive validation project") if project_meta else "Auto-generated progressive validation project"

        html_files = ", ".join(analysis["html_files"]) or "None"
        python_files = ", ".join(analysis["python_files"]) or "None"

        prompt = f"""
You are an expert in creating structured task-based validation flows for Flask web applications.

Analyze the given project and generate a JSON configuration for a task-based validator.
Each task represents a stage in the student's progress.

### Project Details
Project Name: {project_name}
Description: {description}

### Project Structure
HTML Files: {html_files}
Python Files: {python_files}
Static Assets: {', '.join(analysis['static_files'])}

### HTML Samples
"""
        # Add sample HTML snippets
        for html_file in analysis["html_files"][:3]:
            key = f"{html_file}_content"
            if key in analysis:
                prompt += f"\n#### {html_file}\n{analysis[key]}\n"

        prompt += """
### Task Generation Rules
1. **Task 1** must verify the project structure and basic Flask setup:
   - Ensure `app.py` exists and defines Flask routes.
   - Validate folder structure (e.g., templates/, static/, instance/).
   - 5–10 points total.
   - No Playwright required for this task.

2. **Subsequent tasks** (Task 2+) must target actual project features:
   - Create one task per major HTML or feature file (login, register, dashboard, etc.).
   - Each task includes:
     - Description of its purpose.
     - `required_files` list.
     - `validation_rules` (elements, inputs, content).
     - `playwright_test` simulating real user actions.
   - For form pages, include positive and negative input variations (short passwords, invalid emails, etc.)
   - Add meaningful validations (success messages, redirects, etc.)
   - Each task 10–20 points.
   - Unlock conditions should follow progression (Task 2 unlocks after Task 1, etc.).

3. Return the final JSON in the following format ONLY:
{
  "project": "Project Name",
  "description": "Project Description",
  "tasks": [
    {
      "id": 1,
      "name": "Validate Project Structure",
      "description": "Check Flask setup and folder organization.",
      "required_files": ["app.py", "templates/", "static/"],
      "validation_rules": {
        "type": "structure",
        "points": 10,
        "checks": ["app.py exists", "templates folder exists", "static folder exists"]
      },
      "playwright_test": null,
      "unlock_condition": {"min_score": 0, "required_tasks": []}
    },
    {
      "id": 2,
      "name": "Login Page Validation",
      "description": "Validate login form fields and logic.",
      "required_files": ["templates/login.html"],
      "validation_rules": {
        "type": "html",
        "file": "templates/login.html",
        "mustHaveElements": ["form", "input", "button"],
        "mustHaveClasses": ["login_username", "login_password", "login_submit"],
        "points": 15
      },
      "playwright_test": {
        "route": "/login",
        "actions": [
          {"selector_type": "class", "selector_value": "login_username", "input_variants": ["", "test_user"]},
          {"selector_type": "class", "selector_value": "login_password", "input_variants": ["", "WrongPass123!"]},
          {"selector_type": "class", "selector_value": "login_submit", "click": true}
        ],
        "validate": [
          {"type": "text_present", "value": "Login successful"},
          {"type": "text_present", "value": "Invalid credentials"}
        ],
        "points": 15
      },
      "unlock_condition": {"min_score": 10, "required_tasks": [1]}
    }
  ]
}

### Return ONLY valid JSON with proper commas between all fields. No explanations, no markdown, no comments.
### Ensure every field is separated by commas and the JSON is syntactically correct.
"""
        return prompt

    # ======================= RESPONSE PARSING =======================

    def _parse_ai_response(self, text: str, project_meta: Dict = None) -> Dict:
        """Parse AI response into JSON with robust error handling"""
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        # Try to find JSON in the text
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start:json_end + 1]
        
        # Quick pre-sanitizer for common Gemini JSON formatting issues
        text = text.replace('\n"', ',\n"')           # put commas before quoted keys
        text = text.replace('{\n,', '{\n')           # clean stray commas
        text = text.replace('[\n,', '[\n')
        text = text.replace('}\n"', '},\n"')         # add commas before closing braces
        text = text.replace(']\n"', '],\n"')         # add commas before closing brackets
        
        try:
            parsed = json.loads(text)
            if not isinstance(parsed, dict) or "tasks" not in parsed:
                raise ValueError("Invalid JSON structure: missing 'tasks' key")
            return parsed
        except json.JSONDecodeError as e:
            print(f"[GeminiTestCaseGenerator] JSON parsing failed: {e}")
            print(f"[GeminiTestCaseGenerator] Raw response: {text[:500]}...")
            raise ValueError(f"Gemini response not valid JSON: {e}")

    # ======================= FALLBACK TO PARSER =======================

    def _fallback_to_parser(self, project_dir: str, project_meta: Dict = None) -> Dict:
        """Fallback method using Node.js parser"""
        # Define node_script outside try block to avoid scope issues
        node_script = Path(__file__).parent / "pages" / "autoTestcaseGenerator.js"
        
        try:
            if not node_script.exists():
                raise FileNotFoundError(f"Node.js parser not found: {node_script}")
            
            # Run the Node.js parser
            result = subprocess.run(
                ["node", str(node_script), project_dir],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Node.js parser failed: {result.stderr}")
            
            # Load the generated JSON
            project_file = Path(project_dir) / "project_tasks.json"
            if not project_file.exists():
                raise FileNotFoundError("Parser did not generate project_tasks.json")
            
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            return project_data
            
        except Exception as e:
            print(f"[GeminiTestCaseGenerator] Parser fallback failed: {e}")
            # Return a minimal fallback structure
            return {
                "project": project_meta.get("project", "New Project") if project_meta else "New Project",
                "description": project_meta.get("description", "Auto-generated project") if project_meta else "Auto-generated project",
                "tasks": []
            }

    # ======================= HELPERS =======================

    def is_ai_enabled(self) -> bool:
        return self.generation_method == "AI" and self.model is not None

    def get_generation_method(self) -> str:
        return self.generation_method
