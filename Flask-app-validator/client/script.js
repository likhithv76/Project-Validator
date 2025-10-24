// Flask Project Validator - Frontend JavaScript
// This replaces the Streamlit functionality with pure HTML/JS

class FlaskValidatorApp {
    constructor() {
        this.currentPage = 'home';
        this.currentProject = null;
        this.currentProjectData = null;
        this.studentProgress = null;
        this.apiBaseUrl = 'http://localhost:5000/api'; // Default to mock API server
        this.fileContents = {}; // Store file contents for preview
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadProjects();
        this.showPage('home');
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = e.target.closest('[data-page]').dataset.page;
                this.showPage(page);
            });
        });

        // Project selection change
        document.getElementById('projectSelect')?.addEventListener('change', (e) => {
            this.loadProjectData(e.target.value);
        });

        // Student ID change
        document.getElementById('studentId')?.addEventListener('change', (e) => {
            this.loadStudentProgress();
        });
    }

    // Page Navigation
    showPage(pageName) {
        // Hide all pages with proper cleanup
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
            page.style.display = 'none'; // Force hide
        });

        // Show selected page
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
            targetPage.style.display = 'block'; // Force show
            this.currentPage = pageName;
            
            // Update navigation
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            document.querySelector(`[data-page="${pageName}"]`)?.classList.add('active');

            // Load page-specific data
            if (pageName === 'student') {
                this.loadProjects();
            }
        }
    }

    // Loading and UI helpers
    showLoading(text = 'Processing...', subtext = 'Please wait while we process your request') {
        // Show loading in the code preview area instead of alerts
        this.showCodePreview(`<div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <h5>${text}</h5>
            <p class="text-muted">${subtext}</p>
        </div>`);
    }

    hideLoading() {
        // Clear loading from code preview
        this.showCodePreview('');
    }

    showCodePreview(content) {
        const previewContainer = document.getElementById('code-preview');
        if (previewContainer) {
            previewContainer.innerHTML = content;
        }
    }

    showAlert(message, type = 'info', duration = 5000) {
        const alertContainer = document.getElementById('alert-container');
        const alertId = 'alert-' + Date.now();
        
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHtml);
        
        // Auto-dismiss after duration
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }

    // Creator Portal Functions
    async uploadProject() {
        const fileInput = document.getElementById('projectZip');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showAlert('Please select a ZIP file to upload', 'warning');
            return;
        }

        this.showLoading('Uploading project...', 'Extracting and analyzing project structure');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBaseUrl}/upload-project`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.currentProject = result;
            
            this.displayFileTree(result.fileStructure);
            document.getElementById('project-analysis').style.display = 'block';
            
            this.showAlert('Project uploaded successfully!', 'success');
            
        } catch (error) {
            console.error('Upload error:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showAlert('API server not running. Using demo mode with mock data.', 'warning');
                this.loadDemoProject();
            } else {
                this.showAlert(`Upload failed: ${error.message}`, 'danger');
            }
        } finally {
            // Immediately hide the loading modal
            this.hideLoading();
        }
    }

    loadDemoProject() {
        // Clear previous file contents
        this.fileContents = {};
        
        // Load demo project data when API is not available
        this.currentProject = {
            id: 'demo-project',
            name: 'Demo Project',
            fileStructure: {
                'app.py': `from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)`,
                'requirements.txt': `Flask==2.3.3
Werkzeug==2.3.7`,
                'templates': {
                    'base.html': `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Flask App{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">Flask App</a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">Home</a>
                <a class="nav-link" href="/about">About</a>
                <a class="nav-link" href="/contact">Contact</a>
            </div>
        </div>
    </nav>
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
</body>
</html>`,
                    'index.html': `{% extends "base.html" %}

{% block title %}Home - Flask App{% endblock %}

{% block content %}
<div class="jumbotron">
    <h1 class="display-4">Welcome to Flask App</h1>
    <p class="lead">This is a simple Flask application with Bootstrap styling.</p>
    <hr class="my-4">
    <p>Click the buttons below to explore different pages.</p>
    <a class="btn btn-primary btn-lg" href="/about" role="button">Learn more</a>
</div>
{% endblock %}`,
                    'about.html': `{% extends "base.html" %}

{% block title %}About - Flask App{% endblock %}

{% block content %}
<h1>About Us</h1>
<p>This is a demo Flask application showcasing basic web development concepts.</p>
<p>Features include:</p>
<ul>
    <li>Flask routing</li>
    <li>Template inheritance</li>
    <li>Bootstrap styling</li>
    <li>Responsive design</li>
</ul>
{% endblock %}`,
                    'contact.html': `{% extends "base.html" %}

{% block title %}Contact - Flask App{% endblock %}

{% block content %}
<h1>Contact Us</h1>
<form>
    <div class="mb-3">
        <label for="name" class="form-label">Name</label>
        <input type="text" class="form-control" id="name" name="name">
    </div>
    <div class="mb-3">
        <label for="email" class="form-label">Email</label>
        <input type="email" class="form-control" id="email" name="email">
    </div>
    <div class="mb-3">
        <label for="message" class="form-label">Message</label>
        <textarea class="form-control" id="message" name="message" rows="3"></textarea>
    </div>
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
{% endblock %}`
                },
                'static': {
                    'css': {
                        'style.css': `/* Custom styles for Flask app */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.jumbotron {
    background-color: #f8f9fa;
    padding: 2rem 1rem;
    border-radius: 0.375rem;
}

.navbar-brand {
    font-weight: bold;
}

.form-control:focus {
    border-color: #007bff;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}`
                    },
                    'js': {
                        'script.js': `// Main JavaScript file for Flask app
document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask app loaded successfully');
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Form submitted! (This is a demo)');
        });
    });
});`
                    }
                }
            }
        };
        
        this.displayFileTree(this.currentProject.fileStructure);
        document.getElementById('project-analysis').style.display = 'block';
        
        // Automatically generate testcases for demo
        this.loadDemoTestcases();
    }

    displayFileTree(fileStructure) {
        const fileTreeContainer = document.getElementById('file-tree');
        fileTreeContainer.innerHTML = this.buildFileTreeHtml(fileStructure);
        
        // Reset scroll position
        fileTreeContainer.scrollTop = 0;
    }

    buildFileTreeHtml(structure, level = 0) {
        let html = '';
        const indent = '  '.repeat(level);
        
        for (const [name, content] of Object.entries(structure)) {
            if (typeof content === 'object' && content !== null) {
                // Directory
                html += `
                    <div class="file-tree-item directory" style="margin-left: ${level * 20}px">
                        <i class="bi bi-folder me-2"></i>
                        <span class="file-name">${name}</span>
                    </div>
                `;
                html += this.buildFileTreeHtml(content, level + 1);
            } else {
                // File - make it clickable
                const ext = name.split('.').pop().toLowerCase();
                const icon = this.getFileIcon(ext);
                const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
                
                // Store file content for preview
                this.fileContents[fileId] = {
                    name: name,
                    content: content
                };
                
                html += `
                    <div class="file-tree-item file" style="margin-left: ${level * 20}px" onclick="app.previewFileById('${fileId}')" data-file-id="${fileId}">
                        <i class="bi bi-${icon} me-2"></i>
                        <span class="file-name" style="cursor: pointer; color: #007bff;">${name}</span>
                    </div>
                `;
            }
        }
        
        return html;
    }

    getFileIcon(extension) {
        const iconMap = {
            'py': 'file-code',
            'html': 'file-earmark-code',
            'css': 'file-earmark-code',
            'js': 'file-earmark-code',
            'json': 'file-earmark-code',
            'txt': 'file-earmark-text',
            'md': 'file-earmark-text',
            'zip': 'file-earmark-zip'
        };
        return iconMap[extension] || 'file';
    }

    previewFile(filename, content) {
        // Show file content in the code preview area
        const ext = filename.split('.').pop().toLowerCase();
        const language = this.getLanguageFromExtension(ext);
        
        const previewHtml = `
            <div class="mb-3">
                <h6><i class="bi bi-file-earmark-code me-2"></i>${filename}</h6>
                <small class="text-muted">${language.toUpperCase()} file</small>
            </div>
            <pre class="bg-light p-3 rounded" style="max-height: 400px; overflow-y: auto;"><code class="language-${language}">${content}</code></pre>
        `;
        
        this.showCodePreview(previewHtml);
    }

    getLanguageFromExtension(ext) {
        const languageMap = {
            'py': 'python',
            'html': 'html',
            'css': 'css',
            'js': 'javascript',
            'json': 'json',
            'txt': 'text',
            'md': 'markdown'
        };
        return languageMap[ext] || 'text';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    previewFileById(fileId) {
        const fileData = this.fileContents[fileId];
        if (fileData) {
            this.previewFile(fileData.name, fileData.content);
        }
    }

    async generateTestcases() {
        if (!this.currentProject) {
            this.showAlert('Please upload a project first', 'warning');
            return;
        }

        const method = document.getElementById('generationMethod').value;
        this.showLoading('Generating testcases...', `Using ${method} method to analyze your project`);

        try {
            const response = await fetch(`${this.apiBaseUrl}/generate-testcases`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    projectId: this.currentProject.id,
                    method: method
                })
            });

            if (!response.ok) {
                throw new Error(`Generation failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.currentProjectData = result;
            
            this.displayTaskConfiguration(result);
            this.showCodePreview(`
                <div class="text-center py-3">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <strong>Testcases Generated Successfully!</strong>
                    <br>
                    <small class="text-muted">Generated ${result.tasks.length} tasks using ${method} method</small>
                </div>
            `);
            
        } catch (error) {
            console.error('Generation error:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showCodePreview(`
                    <div class="text-center py-3">
                        <i class="bi bi-info-circle text-warning me-2"></i>
                        <strong>Using Demo Mode</strong>
                        <br>
                        <small class="text-muted">API server not running. Generating demo testcases with ${method} method.</small>
                    </div>
                `);
                this.loadDemoTestcases();
            } else {
                this.showCodePreview(`
                    <div class="text-center py-3">
                        <i class="bi bi-exclamation-triangle text-danger me-2"></i>
                        <strong>Generation Failed</strong>
                        <br>
                        <small class="text-muted">${error.message}</small>
                    </div>
                `);
            }
        } finally {
            this.hideLoading();
        }
    }

    async runComprehensiveVerification() {
        if (!this.currentProject) {
            this.showAlert('Please upload a project first', 'warning');
            return;
        }

        this.showLoading('Running Comprehensive Verification...', 'Testing Flask app, capturing screenshots, and validating tasks');

        try {
            const response = await fetch(`${this.apiBaseUrl}/comprehensive-verification`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    projectId: this.currentProject.id
                })
            });

            if (!response.ok) {
                throw new Error(`Verification failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayComprehensiveResults(result.results);
            
            this.showCodePreview(`
                <div class="text-center py-3">
                    <i class="bi bi-check-circle text-success me-2"></i>
                    <strong>Comprehensive Verification Complete!</strong>
                    <br>
                    <small class="text-muted">${result.results.summary.passed_tests}/${result.results.summary.total_tests} tests passed</small>
                    <br>
                    <small class="text-muted">${result.results.summary.screenshots_captured} screenshots captured</small>
                </div>
            `);
            
        } catch (error) {
            console.error('Verification error:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showCodePreview(`
                    <div class="text-center py-3">
                        <i class="bi bi-info-circle text-warning me-2"></i>
                        <strong>Using Demo Mode</strong>
                        <br>
                        <small class="text-muted">API server not running. Running demo comprehensive verification.</small>
                    </div>
                `);
                this.runDemoComprehensiveVerification();
            } else {
                this.showCodePreview(`
                    <div class="text-center py-3">
                        <i class="bi bi-exclamation-triangle text-danger me-2"></i>
                        <strong>Verification Failed</strong>
                        <br>
                        <small class="text-muted">${error.message}</small>
                    </div>
                `);
            }
        } finally {
            this.hideLoading();
        }
    }

    displayComprehensiveResults(results) {
        const resultsContainer = document.getElementById('comprehensive-results');
        if (!resultsContainer) return;

        const html = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-clipboard-check me-2"></i>Comprehensive Verification Results
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-primary">${results.summary.total_tests}</h4>
                                <small class="text-muted">Total Tests</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-success">${results.summary.passed_tests}</h4>
                                <small class="text-muted">Passed</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-danger">${results.summary.failed_tests}</h4>
                                <small class="text-muted">Failed</small>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h4 class="text-info">${results.summary.screenshots_captured}</h4>
                                <small class="text-muted">Screenshots</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <h6>Task Analysis:</h6>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Task</th>
                                        <th>Status</th>
                                        <th>Screenshot</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${results.tasks.map(task => `
                                        <tr>
                                            <td>${task.task_name}</td>
                                            <td>
                                                <span class="badge ${task.test_status === 'PASS' ? 'bg-success' : 'bg-danger'}">
                                                    ${task.test_status}
                                                </span>
                                            </td>
                                            <td>
                                                ${task.screenshot_captured ? 
                                                    '<i class="bi bi-camera text-success"></i>' : 
                                                    '<i class="bi bi-camera text-muted"></i>'
                                                }
                                            </td>
                                            <td>
                                                <small class="text-muted">
                                                    ${Object.entries(task.validation_results).map(([key, value]) => 
                                                        `${key}: ${value}`
                                                    ).join(', ')}
                                                </small>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    ${results.summary.errors.length > 0 ? `
                        <div class="alert alert-warning">
                            <h6>Errors:</h6>
                            <ul class="mb-0">
                                ${results.summary.errors.map(error => `<li>${error}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        resultsContainer.innerHTML = html;
        resultsContainer.style.display = 'block';
    }

    runDemoComprehensiveVerification() {
        const demoResults = {
            project_name: 'Demo Project',
            project_description: 'A demo Flask application for testing',
            verification_timestamp: new Date().toLocaleString(),
            total_tasks: 4,
            tasks: [
                {
                    task_id: 1,
                    task_name: 'Project Setup',
                    test_status: 'PASS',
                    screenshot_captured: true,
                    validation_results: {
                        structure_check: 'PASS',
                        content_check: 'PASS',
                        playwright_test: 'PASS'
                    },
                    errors: []
                },
                {
                    task_id: 2,
                    task_name: 'Home Page',
                    test_status: 'PASS',
                    screenshot_captured: true,
                    validation_results: {
                        structure_check: 'PASS',
                        content_check: 'PASS',
                        playwright_test: 'PASS'
                    },
                    errors: []
                },
                {
                    task_id: 3,
                    task_name: 'About Page',
                    test_status: 'PASS',
                    screenshot_captured: true,
                    validation_results: {
                        structure_check: 'PASS',
                        content_check: 'PASS',
                        playwright_test: 'PASS'
                    },
                    errors: []
                },
                {
                    task_id: 4,
                    task_name: 'Contact Page',
                    test_status: 'FAIL',
                    screenshot_captured: true,
                    validation_results: {
                        structure_check: 'PASS',
                        content_check: 'FAIL',
                        playwright_test: 'FAIL'
                    },
                    errors: ['Form validation not implemented', 'Missing email validation']
                }
            ],
            summary: {
                total_tests: 4,
                passed_tests: 3,
                failed_tests: 1,
                screenshots_captured: 4,
                errors: ['Form validation not implemented', 'Missing email validation']
            }
        };
        
        this.displayComprehensiveResults(demoResults);
    }

    loadDemoTestcases() {
        const demoProjectData = {
            project: 'Demo Project',
            description: 'A demo Flask application for testing',
            tasks: [
                {
                    id: 1,
                    name: 'Project Setup',
                    description: 'Set up your Flask project with the basic file structure',
                    required_files: ['app.py', 'templates/', 'static/', 'requirements.txt'],
                    validation_rules: {
                        type: 'structure',
                        points: 10,
                        checks: ['app.py exists', 'templates folder exists']
                    },
                    playwright_test: {
                        route: '/',
                        actions: [],
                        validate: [{'type': 'status_code', 'value': 200}],
                        points: 5
                    },
                    unlock_condition: {'min_score': 0, 'required_tasks': []}
                },
                {
                    id: 2,
                    name: 'Home Page',
                    description: 'Create a home page with welcome message and navigation',
                    required_files: ['templates/index.html', 'templates/base.html', 'app.py'],
                    validation_rules: {
                        type: 'html',
                        file: 'templates/index.html',
                        mustHaveElements: ['h1', 'nav'],
                        mustHaveContent: ['Welcome'],
                        points: 15
                    },
                    playwright_test: {
                        route: '/',
                        actions: [{'selector_type': 'class', 'selector_value': 'nav-link', 'click': True}],
                        validate: [{'type': 'text_present', 'value': 'Welcome', 'tag': 'h1'}],
                        points: 10
                    },
                    unlock_condition: {'min_score': 10, 'required_tasks': [1]}
                },
                {
                    id: 3,
                    name: 'About Page',
                    description: 'Create an about page that displays information about your project',
                    required_files: ['templates/about.html', 'templates/base.html', 'app.py'],
                    validation_rules: {
                        type: 'html',
                        file: 'templates/about.html',
                        mustHaveElements: ['h1', 'p'],
                        mustHaveContent: ['About'],
                        points: 10
                    },
                    playwright_test: {
                        route: '/about',
                        actions: [],
                        validate: [
                            {'type': 'text_present', 'value': 'About', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        points: 5
                    },
                    unlock_condition: {'min_score': 25, 'required_tasks': [1, 2]}
                },
                {
                    id: 4,
                    name: 'Contact Page',
                    description: 'Create a contact page with a form for user inquiries',
                    required_files: ['templates/contact.html', 'templates/base.html', 'app.py'],
                    validation_rules: {
                        type: 'html',
                        file: 'templates/contact.html',
                        mustHaveElements: ['h1', 'form', 'input'],
                        mustHaveContent: ['Contact', 'Name', 'Email', 'Message'],
                        points: 15
                    },
                    playwright_test: {
                        route: '/contact',
                        actions: [
                            {'selector_type': 'name', 'selector_value': 'name', 'input_variants': ['John Doe']},
                            {'selector_type': 'name', 'selector_value': 'email', 'input_variants': ['john@example.com']},
                            {'selector_type': 'name', 'selector_value': 'message', 'input_variants': ['Hello, this is a test message']},
                            {'selector_type': 'type', 'selector_value': 'submit', 'click': True}
                        ],
                        validate: [
                            {'type': 'text_present', 'value': 'Contact', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        points: 10
                    },
                    unlock_condition: {'min_score': 40, 'required_tasks': [1, 2, 3]}
                }
            ]
        };
        
        this.currentProjectData = demoProjectData;
        this.displayTaskConfiguration(demoProjectData);
    }

    displayTaskConfiguration(projectData) {
        const container = document.getElementById('task-configuration');
        
        let html = `
            <div class="mb-3">
                <h6>Project Information</h6>
                <div class="row">
                    <div class="col-6">
                        <input type="text" class="form-control" id="projectName" value="${projectData.project || ''}" placeholder="Project Name">
                    </div>
                    <div class="col-6">
                        <input type="text" class="form-control" id="projectDescription" value="${projectData.description || ''}" placeholder="Project Description">
                    </div>
                </div>
            </div>
            <hr>
            <h6>Tasks Configuration</h6>
        `;

        projectData.tasks.forEach((task, index) => {
            html += this.buildTaskConfigurationHtml(task, index);
        });

        html += `
            <div class="mt-3">
                <button class="btn btn-success me-2" onclick="app.saveProject()">
                    <i class="bi bi-save me-2"></i>Save Project Package
                </button>
                <button class="btn btn-outline-primary" onclick="app.editRawJson()">
                    <i class="bi bi-code me-2"></i>Edit Raw JSON
                </button>
            </div>
        `;

        container.innerHTML = html;
    }

    buildTaskConfigurationHtml(task, index) {
        return `
            <div class="card mb-3">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Task ${task.id}: ${task.name}</h6>
                    <button class="btn btn-sm btn-outline-danger" onclick="app.deleteTask(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-6">
                            <input type="text" class="form-control" value="${task.name}" onchange="app.updateTaskName(${index}, this.value)">
                        </div>
                        <div class="col-6">
                            <input type="text" class="form-control" value="${task.description}" onchange="app.updateTaskDescription(${index}, this.value)">
                        </div>
                    </div>
                    
                    <div class="mb-2">
                        <label class="form-label">Required Files</label>
                        <select class="form-select" multiple onchange="app.updateRequiredFiles(${index}, this)">
                            ${this.buildFileOptions(task.required_files)}
                        </select>
                    </div>
                    
                    <div class="row mb-2">
                        <div class="col-4">
                            <label class="form-label">Validation Points</label>
                            <input type="number" class="form-control" value="${task.validation_rules?.points || 10}" onchange="app.updateValidationPoints(${index}, this.value)">
                        </div>
                        <div class="col-4">
                            <label class="form-label">UI Test Points</label>
                            <input type="number" class="form-control" value="${task.playwright_test?.points || 10}" onchange="app.updateUIPoints(${index}, this.value)">
                        </div>
                        <div class="col-4">
                            <label class="form-label">Route</label>
                            <input type="text" class="form-control" value="${task.playwright_test?.route || ''}" onchange="app.updateRoute(${index}, this.value)">
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    buildFileOptions(requiredFiles) {
        const allFiles = [
            'app.py', 'requirements.txt', 'templates/base.html', 
            'templates/index.html', 'templates/about.html', 
            'templates/contact.html', 'static/style.css', 'static/script.js',
            'main.py', 'run.py', 'config.py', 'models.py', 'views.py',
            'templates/login.html', 'templates/register.html', 'templates/dashboard.html'
        ];
        
        return allFiles.map(file => {
            const selected = requiredFiles?.includes(file) ? 'selected' : '';
            return `<option value="${file}" ${selected}>${file}</option>`;
        }).join('');
    }

    // Student Portal Functions
    async loadProjects() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/projects`);
            if (!response.ok) {
                throw new Error(`Failed to load projects: ${response.statusText}`);
            }
            
            const projects = await response.json();
            this.populateProjectSelect(projects);
            
        } catch (error) {
            console.error('Error loading projects:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showAlert('API server not running. Loading demo projects.', 'warning');
                this.loadDemoProjects();
            } else {
                this.showAlert('Failed to load projects. Please try again.', 'danger');
            }
        }
    }

    loadDemoProjects() {
        const demoProjects = [
            {
                id: 'simple_flask_web_app',
                name: 'Simple Flask Web App',
                description: 'A basic Flask application with home, about, and contact pages'
            },
            {
                id: 'flask_crud_app',
                name: 'Flask CRUD Application',
                description: 'A Flask application with Create, Read, Update, Delete operations'
            }
        ];
        
        this.populateProjectSelect(demoProjects);
    }

    populateProjectSelect(projects) {
        const select = document.getElementById('projectSelect');
        select.innerHTML = '<option value="">Select a project...</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name;
            select.appendChild(option);
        });
    }

    async loadProjectData(projectId) {
        if (!projectId) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/projects/${projectId}`);
            if (!response.ok) {
                throw new Error(`Failed to load project data: ${response.statusText}`);
            }
            
            const projectData = await response.json();
            this.currentProjectData = projectData;
            this.loadStudentProgress();
            
        } catch (error) {
            console.error('Error loading project data:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showAlert('API server not running. Loading demo project data.', 'warning');
                this.loadDemoProjectData(projectId);
            } else {
                this.showAlert('Failed to load project data.', 'danger');
            }
        }
    }

    loadDemoProjectData(projectId) {
        const demoProjectData = {
            project: 'Simple Flask Web App',
            description: 'A basic Flask application with home, about, and contact pages',
            tasks: [
                {
                    id: 1,
                    name: 'Project Setup',
                    description: 'Set up your Flask project with the basic file structure including app.py, templates folder, and static folder',
                    required_files: ['app.py', 'templates/', 'static/', 'requirements.txt'],
                    validation_rules: {
                        type: 'structure',
                        points: 10,
                        checks: ['app.py exists', 'templates folder exists', 'static folder exists']
                    },
                    playwright_test: {
                        route: '/',
                        actions: [],
                        validate: [{'type': 'status_code', 'value': 200}],
                        points: 5
                    },
                    unlock_condition: {'min_score': 0, 'required_tasks': []}
                },
                {
                    id: 2,
                    name: 'Home Page',
                    description: 'Create a home page that displays a welcome message and navigation menu with links to About and Contact pages',
                    required_files: ['templates/index.html', 'templates/base.html', 'app.py'],
                    validation_rules: {
                        type: 'html',
                        file: 'templates/index.html',
                        mustHaveElements: ['h1', 'nav', 'a'],
                        mustHaveContent: ['Welcome', 'Home', 'About', 'Contact'],
                        points: 15
                    },
                    playwright_test: {
                        route: '/',
                        actions: [{'selector_type': 'class', 'selector_value': 'nav-link', 'click': True}],
                        validate: [
                            {'type': 'text_present', 'value': 'Welcome', 'tag': 'h1'},
                            {'type': 'status_code', 'value': 200}
                        ],
                        points: 10
                    },
                    unlock_condition: {'min_score': 10, 'required_tasks': [1]}
                }
            ]
        };
        
        this.currentProjectData = demoProjectData;
        this.loadStudentProgress();
    }

    async loadStudentProgress() {
        const studentId = document.getElementById('studentId').value;
        const projectId = document.getElementById('projectSelect').value;
        
        if (!studentId || !projectId) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/student-progress/${studentId}/${projectId}`);
            if (!response.ok) {
                throw new Error(`Failed to load progress: ${response.statusText}`);
            }
            
            const progress = await response.json();
            this.studentProgress = progress;
            this.updateProgressDisplay(progress);
            this.displayCurrentTask();
            this.displayAllTasks();
            
        } catch (error) {
            console.error('Error loading student progress:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showAlert('API server not running. Loading demo progress data.', 'warning');
                this.loadDemoStudentProgress(studentId, projectId);
            } else {
                this.showAlert('Failed to load student progress.', 'danger');
            }
        }
    }

    loadDemoStudentProgress(studentId, projectId) {
        const demoProgress = {
            student_id: studentId,
            project_id: projectId,
            completed_tasks: [],
            current_task: 1,
            total_score: 0,
            last_updated: new Date().toISOString()
        };
        
        this.studentProgress = demoProgress;
        this.updateProgressDisplay(demoProgress);
        this.displayCurrentTask();
        this.displayAllTasks();
    }

    updateProgressDisplay(progress) {
        document.getElementById('completedTasks').textContent = progress.completed_tasks?.length || 0;
        document.getElementById('currentTask').textContent = progress.current_task || 1;
        document.getElementById('totalScore').textContent = progress.total_score || 0;
        document.getElementById('lastUpdated').textContent = progress.last_updated?.substring(0, 10) || '-';
    }

    displayCurrentTask() {
        if (!this.currentProjectData || !this.studentProgress) return;
        
        const currentTask = this.getCurrentTask();
        if (!currentTask) return;
        
        const container = document.getElementById('current-task-content');
        const isCompleted = this.studentProgress.completed_tasks?.includes(currentTask.id);
        
        container.innerHTML = `
            <h6>Task ${currentTask.id}: ${currentTask.name}</h6>
            <p class="text-muted">${currentTask.description}</p>
            
            <div class="mb-3">
                <strong>Requirements:</strong>
                <ul class="mb-2">
                    ${currentTask.required_files?.map(file => `<li>${file}</li>`).join('') || '<li>No specific requirements</li>'}
                </ul>
            </div>
            
            <div class="mb-3">
                <strong>Points:</strong> ${currentTask.validation_rules?.points || 0} (validation) + ${currentTask.playwright_test?.points || 0} (UI test)
            </div>
            
            ${isCompleted ? 
                '<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>Task completed!</div>' :
                '<div class="alert alert-info"><i class="bi bi-info-circle me-2"></i>Complete this task to unlock the next one</div>'
            }
        `;
        
        document.getElementById('current-task-section').style.display = 'block';
    }

    displayAllTasks() {
        if (!this.currentProjectData) return;
        
        const container = document.getElementById('all-tasks-content');
        let html = '';
        
        this.currentProjectData.tasks.forEach(task => {
            const isCompleted = this.studentProgress?.completed_tasks?.includes(task.id);
            const statusClass = isCompleted ? 'success' : 'secondary';
            const statusIcon = isCompleted ? 'check-circle-fill' : 'circle';
            
            html += `
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">
                            <i class="bi bi-${statusIcon} text-${statusClass} me-2"></i>
                            Task ${task.id}: ${task.name}
                        </h6>
                        <span class="badge bg-${statusClass}">${isCompleted ? 'Completed' : 'Pending'}</span>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">${task.description}</p>
                        <div class="row">
                            <div class="col-6">
                                <strong>Required Files:</strong>
                                <ul class="mb-0">
                                    ${task.required_files?.map(file => `<li>${file}</li>`).join('') || '<li>No specific requirements</li>'}
                                </ul>
                            </div>
                            <div class="col-6">
                                <strong>Points:</strong> ${task.validation_rules?.points || 0} + ${task.playwright_test?.points || 0}
                                ${task.playwright_test?.route ? `<br><strong>Route:</strong> ${task.playwright_test.route}` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }

    getCurrentTask() {
        if (!this.currentProjectData) return null;
        
        const allTasks = this.currentProjectData.tasks;
        const completedTasks = this.studentProgress?.completed_tasks || [];
        
        // Find the first unlocked task that's not completed
        for (const task of allTasks) {
            const requiredTasks = task.unlock_condition?.required_tasks || [];
            const isUnlocked = requiredTasks.every(rt => completedTasks.includes(rt));
            
            if (isUnlocked && !completedTasks.includes(task.id)) {
                return task;
            }
        }
        
        return null;
    }

    // Validation Functions
    async validateSubmission() {
        const fileInput = document.getElementById('studentZip');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showAlert('Please select a ZIP file to upload', 'warning');
            return;
        }

        const studentId = document.getElementById('studentId').value;
        const currentTask = this.getCurrentTask();
        
        if (!currentTask) {
            this.showAlert('No current task available', 'warning');
            return;
        }

        this.showLoading('Validating submission...', 'Running validation tests on your project');

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('studentId', studentId);
            formData.append('taskId', currentTask.id);

            const response = await fetch(`${this.apiBaseUrl}/validate-task`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Validation failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.showAlert(`Validation completed! Score: ${result.total_score} / ${result.max_score}`, 'success');
                this.loadStudentProgress(); // Refresh progress
            } else {
                this.showAlert(`Validation failed: ${result.message || result.error}`, 'danger');
            }
            
        } catch (error) {
            console.error('Validation error:', error);
            
            // Check if it's a network error (API server not running)
            if (error.message.includes('Failed to fetch') || error.message.includes('Method Not Allowed')) {
                this.showAlert('API server not running. Using demo validation.', 'warning');
                this.performDemoValidation(currentTask);
            } else {
                this.showAlert(`Validation failed: ${error.message}`, 'danger');
            }
        } finally {
            this.hideLoading();
        }
    }

    performDemoValidation(currentTask) {
        // Simulate validation with random success/failure
        const success = Math.random() > 0.3; // 70% success rate for demo
        
        if (success) {
            const score = Math.floor(Math.random() * 10) + 15; // Random score between 15-25
            const maxScore = 25;
            
            this.showAlert(`Demo validation completed! Score: ${score} / ${maxScore}`, 'success');
            
            // Update progress in demo mode
            if (this.studentProgress) {
                if (!this.studentProgress.completed_tasks.includes(currentTask.id)) {
                    this.studentProgress.completed_tasks.push(currentTask.id);
                    this.studentProgress.total_score += score;
                    this.studentProgress.current_task = currentTask.id + 1;
                    this.studentProgress.last_updated = new Date().toISOString();
                    
                    this.updateProgressDisplay(this.studentProgress);
                    this.displayCurrentTask();
                    this.displayAllTasks();
                }
            }
        } else {
            this.showAlert('Demo validation failed: Some requirements not met', 'danger');
        }
    }

    async submitTask() {
        const fileInput = document.getElementById('studentZip');
        const file = fileInput.files[0];
        
        if (!file) {
            this.showAlert('Please select a ZIP file to upload', 'warning');
            return;
        }

        this.showAlert('Task submitted successfully!', 'success');
    }

    reuploadProject() {
        document.getElementById('studentZip').value = '';
        this.showAlert('File input cleared. Please select a new ZIP file.', 'info');
    }

    // Utility Functions
    refreshProjects() {
        this.loadProjects();
        this.showAlert('Projects refreshed', 'info');
    }

    // Task Configuration Functions (for Creator Portal)
    updateTaskName(index, value) {
        if (this.currentProjectData?.tasks?.[index]) {
            this.currentProjectData.tasks[index].name = value;
        }
    }

    updateTaskDescription(index, value) {
        if (this.currentProjectData?.tasks?.[index]) {
            this.currentProjectData.tasks[index].description = value;
        }
    }

    updateRequiredFiles(index, selectElement) {
        if (this.currentProjectData?.tasks?.[index]) {
            const selectedFiles = Array.from(selectElement.selectedOptions).map(option => option.value);
            this.currentProjectData.tasks[index].required_files = selectedFiles;
        }
    }

    updateValidationPoints(index, value) {
        if (this.currentProjectData?.tasks?.[index]) {
            if (!this.currentProjectData.tasks[index].validation_rules) {
                this.currentProjectData.tasks[index].validation_rules = {};
            }
            this.currentProjectData.tasks[index].validation_rules.points = parseInt(value);
        }
    }

    updateUIPoints(index, value) {
        if (this.currentProjectData?.tasks?.[index]) {
            if (!this.currentProjectData.tasks[index].playwright_test) {
                this.currentProjectData.tasks[index].playwright_test = {};
            }
            this.currentProjectData.tasks[index].playwright_test.points = parseInt(value);
        }
    }

    updateRoute(index, value) {
        if (this.currentProjectData?.tasks?.[index]) {
            if (!this.currentProjectData.tasks[index].playwright_test) {
                this.currentProjectData.tasks[index].playwright_test = {};
            }
            this.currentProjectData.tasks[index].playwright_test.route = value;
        }
    }

    deleteTask(index) {
        if (this.currentProjectData?.tasks?.[index]) {
            this.currentProjectData.tasks.splice(index, 1);
            this.displayTaskConfiguration(this.currentProjectData);
        }
    }

    async saveProject() {
        if (!this.currentProjectData) {
            this.showAlert('No project data to save', 'warning');
            return;
        }

        this.showLoading('Saving project...', 'Creating project package');

        try {
            const response = await fetch(`${this.apiBaseUrl}/save-project`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.currentProjectData)
            });

            if (!response.ok) {
                throw new Error(`Save failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.showAlert('Project saved successfully!', 'success');
            
        } catch (error) {
            console.error('Save error:', error);
            this.showAlert(`Save failed: ${error.message}`, 'danger');
        } finally {
            this.hideLoading();
        }
    }

    editRawJson() {
        if (!this.currentProjectData) {
            this.showAlert('No project data to edit', 'warning');
            return;
        }

        const jsonString = JSON.stringify(this.currentProjectData, null, 2);
        const newWindow = window.open('', '_blank');
        newWindow.document.write(`
            <html>
                <head><title>Edit Project JSON</title></head>
                <body>
                    <h3>Project Configuration JSON</h3>
                    <textarea style="width: 100%; height: 80vh; font-family: monospace;">${jsonString}</textarea>
                </body>
            </html>
        `);
    }
}

// Global functions for HTML onclick handlers
function showPage(pageName) {
    app.showPage(pageName);
}

function uploadProject() {
    app.uploadProject();
}

function runComprehensiveVerification() {
    app.runComprehensiveVerification();
}

function generateTestcases() {
    app.generateTestcases();
}

function validateSubmission() {
    app.validateSubmission();
}

function submitTask() {
    app.submitTask();
}

function reuploadProject() {
    app.reuploadProject();
}

function refreshProjects() {
    app.refreshProjects();
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new FlaskValidatorApp();
});
