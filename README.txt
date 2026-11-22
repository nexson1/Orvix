PROJECTHUB FRONTEND STARTER

Files:
- index.html: page structure and UI
- styles.css: responsive visual styling
- app.js: frontend demo interactions and sample data

Run:
1. Extract the ZIP.
2. Open index.html in a browser, or open the folder in VS Code and use Live Server.
3. Try navigation, project creation, task creation, search and filters.

IMPORTANT BACKEND HANDOFF:
This is a frontend prototype with in-memory sample data. It does NOT use Local Storage and does NOT include authentication or a real database.
When you build the Flask backend, replace the sample arrays in app.js with fetch() calls to your Flask API. Suggested API endpoints:
GET/POST /api/projects
GET/POST /api/tasks
PATCH/DELETE /api/tasks/<id>
POST /api/auth/register
POST /api/auth/login
GET /api/users/me

Keep secrets, authentication checks, validation, permissions and database operations on the Flask server.
