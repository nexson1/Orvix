from flask import Flask, abort, render_template, redirect, url_for, flash, jsonify, request, current_app
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime , Date, func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
import os
from datetime import datetime, date, timezone,  timedelta
from zoneinfo import ZoneInfo
from flask_migrate import Migrate
import  smtplib
import secrets
from itsdangerous import URLSafeSerializer, SignatureExpired, BadSignature, URLSafeTimedSerializer
import socket
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded




 







load_dotenv()
app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.getenv("REDIS_URL"),
    default_limits=[]
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
database_url = os.getenv('ORVIX_DATABASE_URL')

if database_url:
    database_url = database_url.replace(
        'postgresql://',
        'postgresql+psycopg://',
        1
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)


# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))


# Database model and table
class Users(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))

    def get_reset_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

        return serializer.dumps(self.email, salt='password-reset-salt')
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):

        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

        try:
            email = serializer.loads(
                token,
                salt='password-reset-salt',
                max_age=expires_sec
            )

        except Exception:
            return None

        return Users.query.filter_by(email=email).first()

    
class Projects(UserMixin, db.Model):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(Integer,db.ForeignKey('users.id'),nullable=False)
    tasks = db.relationship('Tasks',back_populates='project')
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),nullable=True)

class Tasks(UserMixin, db.Model):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    task_name: Mapped[str] = mapped_column(String(100))
    task_project: Mapped[str] = mapped_column(String(100))
    due_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default= 'Pending', nullable= False)
    project_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("projects.id"), nullable= False)
    project = db.relationship('Projects', back_populates = 'tasks')
    @property
    def current_status(self):
        if (self.due_date
                and self.due_date < date.today()
                and self.status != "Completed"):
            return "Overdue"

        return self.status
    
with app.app_context():
   db.engine.connect()
   




@app.route('/')
def home():
   return render_template('landingpage.html')

@app.route('/register', methods = ['POST','GET'])
def register():
     if request.method == 'POST':
             email = request.form['email']
             username = request.form['username']
             password = request.form['password']
             confirm_password = request.form['confirm_password']
             if password != confirm_password:
               flash('Passwords do not match!', 'error')
               return redirect(url_for('register'))
             else:
                 hash_and_salted_password = generate_password_hash(
                 password,
                  method='pbkdf2:sha256',
                  salt_length=8)

                 existing_mail = db.session.execute(db.select(Users).where(Users.email == email)).scalar()
                 if existing_mail:
                        flash("Email address already exists!, Login instead", "error")
                        return redirect(url_for("login"))
                 else:
                        new_user = Users(
                           email = email,
                           username =username,
                           password =hash_and_salted_password
                        )
                        db.session.add(new_user)
                        db.session.commit()
                        flash ('Account created', 'success')
                        return redirect(url_for("login"))
                 
            
     return render_template('register.html')



@app.route('/login', methods = ['POST', 'GET'])
@limiter.limit("5 per minute")
def login():
         if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            user = db.session.execute(db.select(Users).where(Users.email == email)).scalar()
            if user and check_password_hash(user.password, password):
               login_user(user)
               flash('Logged in successfully', 'success')
               return redirect(url_for("dashboard"))
            else:
               flash("Invalid Email or password", "error")
         return render_template('login.html')
@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    flash("Too many login attempts. Please wait 1 minute before trying again.", "error")
    return redirect(url_for("login"))

@app.route('/api/search')
@login_required
def search():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({
            'projects': [],
            'tasks': []
        })

    search_term = f"%{query}%"

    # Search projects belonging to the logged-in user
    projects = db.session.execute(
        db.select(Projects).where(
            Projects.user_id == current_user.id,
            db.or_(
                Projects.project_name.ilike(search_term),
                Projects.description.ilike(search_term)
            )
        ).limit(10)
    ).scalars().all()

    # Search tasks belonging to the logged-in user
    tasks = db.session.execute(
        db.select(Tasks)
        .join(Projects, Tasks.project_id == Projects.id)
        .where(
            Projects.user_id == current_user.id,
            db.or_(
                Tasks.task_name.ilike(search_term),
                Tasks.task_project.ilike(search_term),
                Tasks.priority.ilike(search_term),
                Tasks.status.ilike(search_term)
            )
        )
        .limit(10)
    ).scalars().all()

    return jsonify({
        'projects': [
            {
                'id': project.id,
                'name': project.project_name,
                'description': project.description,
                'type': 'Project'
            }
            for project in projects
        ],

        'tasks': [
            {
                'id': task.id,
                'name': task.task_name,
                'project': task.task_project,
                'priority': task.priority,
                'status': task.current_status,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'type': 'Task'
            }
            for task in tasks
        ]
    })


@app.route('/reset-password/<token>', methods = ['POST','GET'])
def reset_password(token):
    user = Users.verify_reset_token(token)

    if user is None:
        flash('That is an invalid or expired token.', 'error')
        return redirect(url_for('recover_password'))
        

    if request.method == 'POST':
        new_password = request.form['new_pass']
        confirm_new_password = request.form['re-password']
        if new_password != confirm_new_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('reset_password', token=token))

        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('login'))

    return render_template('resetpass.html', token=token)





@app.route('/password-recovery', methods=['POST', 'GET'])
def recover_password():

    if request.method == 'POST':
        pass_email = request.form['pass_email']

        account_email = db.session.execute(
            db.select(Users).where(Users.email == pass_email)
        ).scalar()

        if account_email:
            token = account_email.get_reset_token()

            link = url_for(
                'reset_password',
                token=token,
                _external=True
            )

    
            email = os.getenv('MY_EMAIL')
            password = os.getenv('MY_PASSWORD')

            message = f"""Subject: Reset Password

Please click this link to reset your password:
{link}
"""

            smtp_ports = [587, 465]

            email_sent = False

            for port in smtp_ports:
                try:
                    print(f"Trying Gmail SMTP port {port}...")

                    if port == 587:
                        with smtplib.SMTP('smtp.gmail.com', port, timeout=20) as connection:
                            connection.starttls()
                            connection.login(email, password)
                            connection.sendmail(email, pass_email, message)

                        f


                    elif port == 465:
                        with smtplib.SMTP_SSL('smtp.gmail.com', port, timeout=20) as connection:
                            connection.login(email, password)
                            connection.sendmail(email, pass_email, message)

                        print(f"Email successfully sent using port {port}!")
                        email_sent = True
                    flash("An email has been sent", "success")
                        
                    break

                except (smtplib.SMTPException, OSError) as error:
                    print(f"Port {port} failed: {error}")
                except Exception as e:
                                    print("ERROR TYPE:", type(e).__name__)
                                    print("ERROR MESSAGE:", str(e))
                                    flash('An error occured','error')

        else:
            flash("Email address not found", "error")

    return render_template('recpass.html')






@app.route('/dashboard')
@login_required
def dashboard():
    now = datetime.now(ZoneInfo("Africa/Lagos"))

    current_month_start = now.replace(
    day=1, hour=0, minute=0, second=0, microsecond=0
    )

    previous_month_start = (
    current_month_start - timedelta(days=1)
    ).replace(day=1)

    next_month_start = (
    current_month_start.replace(day=28) + timedelta(days=4)
    ).replace(day=1)

    projects_this_month = db.session.execute(
    db.select(func.count(Projects.id))
    .where(
        Projects.user_id == current_user.id,
        Projects.created_at >= current_month_start,
        Projects.created_at < next_month_start
    )
    ).scalar()


    projects_last_month = db.session.execute(
    db.select(func.count(Projects.id))
    .where(
        Projects.user_id == current_user.id,
        Projects.created_at >= previous_month_start,
        Projects.created_at < current_month_start
    )
    ).scalar() 


    if projects_last_month > 0:
        project_change_value = (
        (projects_this_month - projects_last_month)
        / projects_last_month
    ) * 100

        project_change = f"{project_change_value:+.0f}%"

        if project_change_value > 0:
            project_change_class = "positive"
            project_change_icon = ""
        elif project_change_value < 0:
            project_change_class = "negative"
            project_change_icon = ""
        else:
            project_change_class = "neutral"
            project_change_icon = ""

    elif projects_this_month > 0:
        project_change = "New"
        project_change_class = "positive"
        project_change_icon = ""

    else:
        project_change = "0%"
        project_change_class = "neutral"
        project_change_icon = ""




    total_tasks = db.session.execute(
        db.select(func.count(Tasks.id))
    .join(Projects)
    .where(Projects.user_id == current_user.id)
    ).scalar()

    completed_tasks = db.session.execute(
    db.select(func.count(Tasks.id))
    .join(Projects)
    .where(
        Projects.user_id == current_user.id,
        Tasks.status == "Completed"
    )
    ).scalar()

    if total_tasks > 0:
        completion_rate = round(
        (completed_tasks / total_tasks) * 100
    )
    else:
        completion_rate = 0



    in_progress_tasks = db.session.execute(
    db.select(func.count(Tasks.id))
    .join(Projects)
    .where(
        Projects.user_id == current_user.id,
        Tasks.status == "In Progress"
    )
    ).scalar()




   
   

    current_time = now.strftime("%A, %B %d, %Y | %I:%M %p")
    hour = now.hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    elif hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"

    display_projects = db.session.execute(
       db.select(Projects)
       .where(Projects.user_id == current_user.id)
       .order_by(Projects.id.desc())
   ).scalars().all()
   
      
      
    display_tasks = db.session.execute(
    db.select(Tasks)
    .join(Projects)
    .where(Projects.user_id == current_user.id)
    .order_by(Tasks.id.desc())
    ).scalars().all()
          
   
    return render_template('index.html', current_time = current_time, projects = display_projects, tasks = display_tasks, greeting=greeting,
                           project_change=project_change,
                           project_change_class=project_change_class,
                            project_change_icon=project_change_icon,
                            total_tasks=total_tasks,
                            completed_tasks=completed_tasks,
                            completion_rate=completion_rate,
                            in_progress_tasks=in_progress_tasks)



@app.route('/create-project', methods=['POST'])
@login_required
def create_project():

     if request.method == 'POST':

        project_name = request.form['name']
        description = request.form['description']

        new_project = Projects(
            project_name=project_name,
            description=description,
            user_id=current_user.id
        )

        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('dashboard'))

@app.route('/create-task', methods=['POST'])
@login_required
def create_task():

    task_name = request.form['name']
    task_project = request.form['project']
    priority = request.form['priority']

    due_date = datetime.strptime(
        request.form['due'], '%Y-%m-%d'
    ).date()

    project = Projects.query.filter_by(
    id=int(task_project),
    user_id=current_user.id
).first_or_404()

   

    new_task = Tasks(
        task_name=task_name,
        task_project= project.project_name,
        project_id=project.id,
        priority=priority,
        due_date=due_date,
    )

    try:
        db.session.add(new_task)
        db.session.commit()

        

    except Exception as e:
        db.session.rollback()
        print("DATABASE ERROR:", e)
        flash('Unable to save task.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/update-status/<int:task_id>', methods=['POST'])
@login_required
def update_status(task_id):

    status_update = db.session.execute(
        db.select(Tasks)
        .join(Projects)
        .where(
            Tasks.id == task_id,
            Projects.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if status_update is None:
        abort(404)

    status_update.status = request.form['status']

    db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
