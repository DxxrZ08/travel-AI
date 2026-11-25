# AI Travel Planner — Project Review Guide

AI Travel Planner is a full-stack web application for discovering destinations, creating accounts, generating AI travel itineraries, estimating trip budgets, saving trips, chatting with a travel assistant, writing reviews, and managing users as an administrator.

## 1. Technology Stack

| Area | Technology |
|---|---|
| Backend | Python and Flask |
| Authentication | Flask-Login and Werkzeug password hashing |
| Database | SQLite through Flask-SQLAlchemy |
| Frontend | HTML, Jinja templates, CSS, and JavaScript |
| AI service | NVIDIA NIM through the OpenAI-compatible Python client |
| Configuration | Environment variables with python-dotenv |
| Markdown rendering | Python-Markdown |

## 2. How to Run the Project

### Requirements

- Python 3.10 or newer
- Internet access for external images and NVIDIA AI features

### Setup and start

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000**.

On first startup, the application:

1. Creates the SQLite database in the `instance` folder.
2. Creates all database tables.
3. Applies a small compatibility migration for the admin role column when needed.
4. Adds six demo destinations if the destination table is empty.

### Optional AI configuration

Create a `.env` file in the project root:

```text
NVIDIA_API_KEY=nvapi-your-key-here
SECRET_KEY=replace-this-with-a-long-random-secret
```

Without an NVIDIA API key, accounts, destinations, dashboards, and saved-trip features still work. AI itinerary, budget, and chat features report that the service is not configured.

### Firebase Google sign-in

1. In the [Firebase Console](https://console.firebase.google.com/), create or select a project, add a Web app, then enable **Google** under **Authentication → Sign-in method**.
2. Add the site hostname under **Authentication → Settings → Authorized domains**. For local development, include `localhost` and `127.0.0.1` if you open the app at that address.
3. Add the Web app settings to `.env`:

   ```text
   FIREBASE_API_KEY=your-web-api-key
   FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_APP_ID=your-web-app-id
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=your-sender-id
   ```

4. Configure Firebase Admin credentials for the Flask server. For local development, create a service-account key in **Project settings → Service accounts**, keep the downloaded JSON outside the repository, and set:

   ```text
   FIREBASE_SERVICE_ACCOUNT_KEY=absolute-path-to-service-account.json
   ```

   The service account's `project_id` must match `FIREBASE_PROJECT_ID`. The app checks this before initialization. On supported cloud hosts, use the host's Application Default Credentials instead. Never commit the service-account JSON or put it in browser/client settings.
5. Restart Flask and open `/login` or `/register`. The Google button will use Firebase to sign in and the server will validate the ID token before creating or linking an account. If the browser blocks the sign-in popup, the app falls back to a full-page redirect. Existing accounts are linked by email only when Firebase confirms that email is verified.

The Firebase Web app settings are public client configuration; the Admin service-account key is a server secret. If Firebase is not configured, username/password authentication remains available.

## 3. Project Structure

```text
travel planner/
├── app.py                  Flask application, routes, startup and CSRF protection
├── config.py               Development and production configuration
├── models.py               SQLAlchemy database models and relationships
├── travel_ai.py            NVIDIA/NIM prompts and API integration
├── requirements.txt        Python dependencies
├── instance/               SQLite database
├── static/css/style.css    Complete application styling
├── static/js/main.js       Shared navigation and UI JavaScript
└── templates/              Jinja HTML pages
```

### Important files

- `app.py` is the main application file and contains both public and protected routes.
- `models.py` defines the users, destinations, trips, reviews, and chat-message data structures.
- `travel_ai.py` builds prompts and calls the NVIDIA NIM service.
- `config.py` reads environment variables and configures development or production mode.
- `templates/base.html` contains the shared navigation, footer, and layout.
- `static/css/style.css` controls the visual design and responsive layout.

## 4. Database Design

| Table | Purpose | Main fields and relationships |
|---|---|---|
| `users` | Registered accounts | Username, email, password hash, role, profile information |
| `destinations` | Available travel locations | Name, location, category, cost, rating, image, highlights |
| `trips` | Saved travel plans | User, destination, itinerary, dates, budget, travelers, style |
| `reviews` | Destination feedback | User, destination, numeric rating, title and comment |
| `chat_messages` | Persistent chatbot conversation | User, session, role and message content |

### Relationships

- One user can create many trips, reviews, and chat messages.
- One destination can be linked to many trips and reviews.
- Deleting a user also removes that user's trips, reviews, and chat messages.
- Deleting a destination removes its associated reviews.

## 5. User Features

### Public features

- View the home page, statistics, and featured destinations.
- Search, filter, sort, and browse destinations.
- Open destination details including descriptions, highlights, costs, and reviews.

### Account features

- Register an account with username, email, password, and full name.
- Log in using either username or email.
- Update profile name, email, biography, favorite destination, and travel style.
- Log out securely.

### Authenticated travel features

- Generate an AI trip plan for a destination and number of days.
- Choose budget, travelers, travel style, interests, start date, and special requests.
- Save the generated itinerary to the account.
- View the complete itinerary as rendered Markdown.
- View and delete saved trips.
- Calculate a detailed AI budget by destination, duration, travelers, and budget level.
- Chat with the travel assistant using conversation history.
- Submit one review per destination.

### Administrator features

- View overall destination, user, trip, and administrator totals.
- View recent registrations.
- Search and filter accounts.
- Filter users by normal user or administrator role.

Create or promote an administrator from the project directory:

```powershell
flask --app app create-admin
```

## 6. Application Routes

| Route | Access | Function |
|---|---|---|
| `/` | Public | Home page and destination highlights |
| `/register` | Public | Account registration |
| `/login` | Public | Account login |
| `/logout` | Logged in | Session logout |
| `/dashboard` | Logged in | User overview and recent trips |
| `/destinations` | Public | Search and filter destination catalogue |
| `/destination/<id>` | Public | Destination details and reviews |
| `/destination/<id>/review` | Logged in | Submit a destination review |
| `/plan` | Logged in | Generate and save an AI itinerary |
| `/my-trips` | Logged in | List saved trips |
| `/trip/<id>` | Owner | View a saved trip |
| `/trip/<id>/delete` | Owner | Delete a saved trip |
| `/budget` | Logged in | AI budget calculator |
| `/chat` | Logged in | Travel chatbot interface |
| `/chat/send` | Logged in | Send an AJAX chatbot message |
| `/chat/clear` | Logged in | Start a new chat session |
| `/profile` | Logged in | View and update profile |
| `/admin` | Administrator | System overview |
| `/admin/users` | Administrator | Account search and role filtering |

## 7. Request and Data Flow

### Trip planning flow

1. The user opens `/plan` and submits the planning form.
2. Flask validates and reads the destination, duration, budget, travelers, interests, style, and dates.
3. `travel_ai.py` builds a structured prompt.
4. The NVIDIA OpenAI-compatible API creates the itinerary.
5. Flask saves the result as a `Trip` belonging to the logged-in user.
6. The user is redirected to the trip-detail page.

### Chat flow

1. The browser sends a message to `/chat/send` using JavaScript.
2. The message is stored in the `chat_messages` table.
3. Flask retrieves recent messages for that user's chat session.
4. The conversation is sent to NVIDIA NIM with the chatbot system prompt.
5. The response is saved and returned as JSON.
6. JavaScript displays the assistant response without refreshing the page.

### Destination review flow

1. A logged-in user submits a rating and optional review text.
2. Flask prevents duplicate reviews for the same user and destination.
3. The new review is stored in the database.
4. The destination's average rating and review count are recalculated.
5. The user is returned to the destination page.

## 8. AI Integration Details

`travel_ai.py` provides four main operations:

- `build_travel_prompt(...)` creates a detailed day-by-day trip prompt.
- `build_budget_prompt(...)` creates a category-based budget prompt.
- `get_ai_response(...)` requests a complete AI response.
- `chat_response(...)` sends recent chat history and receives a chatbot response.

The app uses NVIDIA's OpenAI-compatible base URL:

```text
https://integrate.api.nvidia.com/v1
```

The integration includes error handling so API failures are displayed safely instead of crashing the application.

## 9. Security Features

- Passwords are converted to secure hash values using Werkzeug.
- Login is required for personal dashboards, trip features, budgets, chat, and profiles.
- Trip ownership is checked before viewing or deleting a trip.
- Administrator routes use a dedicated `admin_required` decorator.
- Login redirect targets are validated to prevent external same-site redirects.
- State-changing forms are protected with CSRF tokens.
- HTML form and database values should be escaped by template/database boundaries; the application uses Jinja rendering rather than unsafe raw HTML output.
- Session cookies are configured for HTTP-only and SameSite behavior.
- Production mode requires an environment secret key.
- API keys are stored in environment variables or `.env`, not in source code.

## 10. Template and Interface Structure

- `base.html`: shared navigation, messages, footer, and assets.
- `index.html`: landing page.
- `register.html` and `login.html`: authentication forms.
- `dashboard.html`: user overview.
- `destinations.html`: browse and filtering interface.
- `destination_detail.html`: destination information, highlights, and reviews.
- `plan_trip.html`: trip-preference form.
- `my_trips.html`: saved-trip catalogue.
- `trip_detail.html`: itinerary display and deletion control.
- `budget.html`: budget estimate form and result.
- `chatbot.html`: asynchronous chat interface.
- `profile.html`: profile editor.
- `admin_dashboard.html` and `admin_users.html`: administrator pages.
- `errors/`: custom 403, 404, and 500 pages.

## 11. Production Notes

Set production environment variables before starting:

```powershell
$env:FLASK_ENV="production"
$env:SECRET_KEY="use-a-long-random-value"
$env:DATABASE_URL="sqlite:///travel_planner.db"
python app.py
```

Production startup rejects a missing secret key. For an actual deployment, use a production WSGI server and configure HTTPS so the secure session-cookie setting works correctly.

## 12. Features to Demonstrate in the Review

1. Start the server and show the landing page.
2. Browse and filter destinations without logging in.
3. Open a destination and show details and reviews.
4. Register a new account and show automatic login.
5. Open the user dashboard and explain the displayed statistics.
6. Generate a trip with a destination, duration, budget, and interests.
7. Open the saved-trip page and explain the database relationship.
8. Generate a budget estimate.
9. Send several chatbot messages and show persistent history.
10. Update profile details.
11. Log out and log back in.
12. Use the admin CLI and demonstrate the administrator dashboard and user search.
13. Explain CSRF protection, password hashing, route protection, and ownership checks.
14. Explain that SQLite is used for development and that the configuration supports another database URL.
15. Explain the AI fallback behavior when no NVIDIA API key is configured.

## 13. Possible Viva Questions

- **Why Flask?** Flask is lightweight, Python-based, and suitable for an educational full-stack application.
- **What is SQLAlchemy?** It is an ORM that maps Python model classes to database tables.
- **What is Jinja?** It is Flask's server-side HTML templating engine.
- **How are passwords stored?** Only password hashes are stored, not plain-text passwords.
- **How is trip ownership secured?** The route checks whether the trip's `user_id` matches the logged-in account.
- **What is a decorator?** `@login_required` and `@admin_required` wrap routes and enforce access conditions before their main code executes.
- **How does Flask know the current user?** Flask-Login stores a user identifier in the session and restores the user through the `user_loader` callback.
- **What does CSRF protect against?** It ensures that an action request contains a valid token issued for the current browser session.
- **Why an external AI API?** It allows the application to generate high-quality, context-aware itinerary, budget, and chat responses without training a local model.
- **What happens when AI is unavailable?** The application remains usable for non-AI features and shows a clear configuration or service error.
- **How is a chatbot response generated?** Previous messages in the same chat session are sent to the model along with a travel-assistant system prompt.
- **What are the future enhancements?** Real-time flight and hotel APIs, maps, email verification, password recovery, payment integration, weather APIs, and deployment with PostgreSQL.

## 14. Current Validation Status

The project has been checked for:

- Python syntax compilation.
- Flask application startup.
- Public page rendering.
- Authenticated page rendering.
- Route registration.
- Required templates and static assets.

Start the server with `python app.py` and verify the app at **http://127.0.0.1:5000** before the review.
