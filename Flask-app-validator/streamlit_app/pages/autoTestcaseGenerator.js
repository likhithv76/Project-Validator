import fs from "fs";
import path from "path";
import { TestcaseGenerator } from "./testcaseGenerator.js";

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