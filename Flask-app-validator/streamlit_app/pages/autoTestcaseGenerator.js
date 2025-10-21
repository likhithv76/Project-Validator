import fs from "fs";
import path from "path";
import { TestcaseGenerator } from "./testcaseGenerator.js";

// NOTE: This parser-based generator is disabled when TEST_CASE_GENERATOR_METHOD=AI
// The Gemini AI generator in gemini_generator.py will be used instead

/**
 * Generate Playwright actions and validation rules from HTML elements
 * @param {Array} elements - Parsed HTML elements from analysis
 * @returns {Object} - { actions: [], validate: [] }
 */
function generatePlaywrightActionsFromElements(elements = []) {
  const actions = [];
  const validationTexts = [];
  const passwordFields = [];
  
  elements.forEach(el => {
    const tag = el.tag?.toLowerCase();
    const cls = el.class || "";
    const selector_value = cls?.split(" ")[0] || null;

    if (tag === "input") {
      const type = el.attributes?.type || "text";
      const action = {
        selector_type: "class",
        selector_value,
        input_variants: []
      };

      // Default variants based on field type
      if (type === "password" || cls.includes("password")) {
        passwordFields.push(cls);
        
        if (cls.includes("confirm") || cls.includes("repeat")) {
          // Confirm password field - use matching variants
          action.input_variants = [
            "Password123!",
            "Mismatch123",
            "Strong@Pass123"
          ];
          validationTexts.push("Passwords must match");
        } else {
          // Regular password field
          action.input_variants = [
            "12345",
            "password",
            "Password123!",
            "Weakpass",
            "Strong@Pass123"
          ];
          validationTexts.push("Password too short");
          validationTexts.push("Add special characters");
        }
      } 
      else if (type === "email" || cls.includes("email")) {
        action.input_variants = [
          "test@example.com",
          "invalid_email",
          "user@domain",
          "test@",
          "user@domain.com"
        ];
        validationTexts.push("Invalid email format");
        validationTexts.push("Email is required");
      } 
      else if (type === "text" || cls.includes("username") || cls.includes("name")) {
        action.input_variants = [
          "user123",
          "u",
          "verylongusername_exceeding_limit",
          "test_user",
          "admin"
        ];
        validationTexts.push("Username too short");
        validationTexts.push("Username already exists");
      }
      else if (type === "number" || cls.includes("age") || cls.includes("phone")) {
        action.input_variants = [
          "25",
          "abc",
          "1234567890",
          "-5"
        ];
        validationTexts.push("Invalid number format");
      }
      else {
        action.input_variants = ["sample", "test", "example"];
      }

      actions.push(action);
    }

    if (tag === "button" || el.attributes?.type === "submit") {
      actions.push({
        selector_type: "class",
        selector_value,
        click: true
      });
    }
  });

  // Add default validation checks
  const validate = [
    { "type": "text_present", "value": "successful" },
    { "type": "text_present", "value": "Registration successful" },
    { "type": "text_present", "value": "Login successful" },
    ...validationTexts.map(v => ({ "type": "text_present", "value": v }))
  ];

  // Add URL redirect validation for common flows
  if (elements.some(el => el.class?.includes("register"))) {
    validate.push({ "type": "url_redirect", "value": "/login" });
  }
  if (elements.some(el => el.class?.includes("login"))) {
    validate.push({ "type": "url_redirect", "value": "/dashboard" });
  }

  return { actions, validate };
}

export async function generateProjectJSON(dir, projectMeta = {}) {
  const {
    project = "New Project",
    description = "Auto-generated progressive validation project"
  } = projectMeta;

  const generator = new TestcaseGenerator();
  const files = await generator.loadFilesFromDirectory(dir);
  const results = await generator.generateFromFiles(files);

  const projectFile = path.join(dir, "project_tasks.json");
  let existing = null;

  try {
    if (fs.existsSync(projectFile)) {
      existing = JSON.parse(await fs.promises.readFile(projectFile, "utf-8"));
      console.log("Merging with existing project JSON...");
    }
  } catch (err) {
    console.warn("Error loading existing JSON:", err.message);
  }

  const base = existing || { project, description, tasks: [] };
  let taskId = base.tasks.length + 1;

  // Add a top-level Structure task once per project to validate basic layout
  try {
    const allPaths = Object.keys(files || {});
    const hasTemplatesDir = allPaths.some(p => p.replace(/\\/g, "/").startsWith("templates/"));
    const hasStaticDir = allPaths.some(p => p.replace(/\\/g, "/").startsWith("static/"));
    const hasAppPy = allPaths.some(p => p.endsWith("app.py"));
    const hasBaseHtml = allPaths.some(p => p.replace(/\\/g, "/").endsWith("templates/base.html"));

    const structureChecks = [];
    const structurePaths = [];
    // Always include a few canonical checks; the validator can infer from strings
    structureChecks.push("app.py exists");
    structureChecks.push("templates folder exists");
    structureChecks.push("static folder exists");
    structureChecks.push("templates/base.html exists");

    structurePaths.push("app.py");
    structurePaths.push("templates/");
    structurePaths.push("static/");
    structurePaths.push("templates/base.html");

    const structureTask = {
      id: taskId++,
      name: "Validate Project Structure",
      description: "Check for essential Flask files and directories.",
      required_files: ["app.py", "templates/", "static/", "templates/base.html"],
      validation_rules: {
        type: "structure",
        points: 10,
        checks: structureChecks,
        paths: structurePaths
      },
      playwright_test: null,
      unlock_condition: { min_score: 0, required_tasks: [] }
    };

    // Only add if a similar structure task isn't already present
    const hasExistingStructure = base.tasks.some(t => (t.validation_rules && t.validation_rules.type) === "structure");
    if (!hasExistingStructure) {
      base.tasks.push(structureTask);
    }
  } catch (e) {
    console.warn("Failed to add structure task:", e?.message || e);
  }

  for (const [filename, fileData] of Object.entries(results.Code_Validation)) {
    const ext = path.extname(filename).substring(1);
    const shortName = path.basename(filename, path.extname(filename));

    const newTask = {
      id: taskId++,
      name: `${shortName} Validation`,
      description: `Auto-generated validation for ${filename}`,
      required_files: [filename],
      validation_rules: {
        type: ext,
        file: filename,
        points: 10,
        generatedTests: fileData.structure || [],
        analysis: fileData.analysis || {},
      },
      playwright_test: {
        route: `/${shortName}`,
        actions: [],
        validate: [],
        points: 10
      },
      unlock_condition: { min_score: 0, required_tasks: [] }
    };

    // 🔥 Auto-generate Playwright actions from HTML elements
    if (ext === "html" && fileData.analysis?.elements?.length) {
      const { actions, validate } = generatePlaywrightActionsFromElements(fileData.analysis.elements);
      newTask.playwright_test.actions = actions;
      newTask.playwright_test.validate = validate;
      
      // Increase points for HTML tasks with forms
      const formCount = fileData.analysis.elements.filter(el => el.tag?.toLowerCase() === 'form').length;
      const inputCount = fileData.analysis.elements.filter(el => el.tag?.toLowerCase() === 'input').length;
      if (formCount > 0 || inputCount > 0) {
        newTask.playwright_test.points = Math.min(20, 10 + (formCount * 3) + (inputCount * 2));
        newTask.validation_rules.points = Math.min(20, 10 + (formCount * 3) + (inputCount * 2));
      }
      
      console.log(`🎭 Generated ${actions.length} Playwright actions for ${filename}`);
    }

    base.tasks.push(newTask);
  }

  await fs.promises.writeFile(projectFile, JSON.stringify(base, null, 2), "utf-8");
  console.log(`✅ Updated project JSON: ${projectFile}`);
  return base;
}

// Main execution when run directly
if (process.argv[1] && process.argv[1].endsWith('autoTestcaseGenerator.js')) {
  const projectDir = process.argv[2];
  if (!projectDir) {
    console.error("Usage: node autoTestcaseGenerator.js <project_directory>");
    process.exit(1);
  }
  
  console.log(`Starting testcase generation for: ${projectDir}`);
  
  generateProjectJSON(projectDir)
    .then(result => {
      console.log("✅ Project JSON generation completed successfully!");
      console.log(`Generated ${result.tasks.length} tasks`);
    })
    .catch(error => {
      console.error("❌ Error generating project JSON:", error);
      process.exit(1);
    });
}