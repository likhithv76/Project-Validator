# Flask Project Validator - Frontend Migration

This directory contains the migrated frontend from Streamlit to pure HTML, Bootstrap, and JavaScript.

## Files Structure

- `index.html` - Main HTML file with Bootstrap UI
- `script.js` - JavaScript functionality replacing Streamlit components
- `style.css` - Custom CSS styling and responsive design
- `mock_api.py` - Mock Flask API server for testing

## Features Migrated

### ✅ Home Page
- Clean landing page with navigation to Creator/Student portals
- Bootstrap cards for portal selection
- Responsive design

### ✅ Creator Portal
- Project ZIP upload functionality
- File structure visualization
- Auto-testcase generation (AI/Parser methods)
- Task configuration interface
- Project package saving

### ✅ Student Portal
- Project selection dropdown
- Student progress tracking
- Current task display
- Project validation and submission
- All tasks overview

## Quick Start

### 1. Start the Mock API Server
```bash
cd client
python mock_api.py
```

### 2. Open the Frontend
Open `index.html` in your browser or serve it with a simple HTTP server:

```bash
# Using Python's built-in server
python -m http.server 3000

# Or using Node.js
npx serve -p 3000
```

### 3. Access the Application
- Frontend: http://localhost:3000
- API: http://localhost:5000

## API Endpoints

The frontend expects these API endpoints:

- `GET /api/projects` - List available projects
- `GET /api/projects/{id}` - Get project details
- `GET /api/student-progress/{student_id}/{project_id}` - Get student progress
- `POST /api/upload-project` - Upload project ZIP
- `POST /api/generate-testcases` - Generate testcases
- `POST /api/validate-task` - Validate student submission
- `POST /api/save-project` - Save project configuration

## Key Differences from Streamlit

### Navigation
- **Streamlit**: Page switching with `st.switch_page()`
- **HTML/JS**: Single-page application with show/hide divs

### File Upload
- **Streamlit**: `st.file_uploader()`
- **HTML/JS**: `<input type="file">` with FormData API

### State Management
- **Streamlit**: `st.session_state`
- **HTML/JS**: JavaScript class properties and localStorage

### UI Components
- **Streamlit**: `st.columns()`, `st.expander()`, `st.metric()`
- **HTML/JS**: Bootstrap grid system, cards, and custom components

### Alerts and Notifications
- **Streamlit**: `st.success()`, `st.error()`, `st.warning()`
- **HTML/JS**: Bootstrap alerts with custom JavaScript functions

## Customization

### Styling
- Modify `style.css` for custom colors, fonts, and layouts
- Bootstrap classes can be customized with CSS variables
- Dark mode support included

### Functionality
- Extend the `FlaskValidatorApp` class in `script.js`
- Add new API endpoints in `mock_api.py`
- Implement real backend integration

### Responsive Design
- Mobile-first approach with Bootstrap breakpoints
- Custom CSS for tablet and desktop layouts
- Touch-friendly interface elements

## Integration with Real Backend

To integrate with the actual Flask backend:

1. Update the `apiBaseUrl` in `script.js`:
```javascript
this.apiBaseUrl = 'http://your-backend-url/api';
```

2. Ensure your backend implements the required endpoints
3. Handle authentication if needed
4. Add error handling for network issues

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Performance

- No external dependencies except Bootstrap CDN
- Minimal JavaScript bundle size
- Optimized CSS with media queries
- Lazy loading for large file trees

## Security Considerations

- File upload validation needed
- CSRF protection for forms
- Input sanitization
- Secure file handling

## Future Enhancements

- [ ] Real-time progress updates with WebSockets
- [ ] Drag-and-drop file upload
- [ ] Advanced file tree with syntax highlighting
- [ ] Export/import project configurations
- [ ] Multi-language support
- [ ] Progressive Web App (PWA) features
