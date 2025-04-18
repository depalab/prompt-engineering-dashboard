from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import json
import datetime
import uuid
import base64
import anthropic
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.csrf import CSRFProtect
import secrets
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Import the CausalPromptEvaluator
from causal_prompt_evaluator import CausalPromptEvaluator

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['TEMPLATES_AUTO_RELOAD'] = True
csrf = CSRFProtect(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'frames'), exist_ok=True)
os.makedirs('results', exist_ok=True)
os.makedirs('prompts', exist_ok=True)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple user model (in production, use a database)
class User(UserMixin):
    def __init__(self, id, username, password_hash, api_key=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.api_key = api_key

# Mock user database (use a real database in production)
users = {
    '1': User('1', 'admin', generate_password_hash('admin'), None)
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = StringField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class APIKeyForm(FlaskForm):
    api_key = StringField('Anthropic API Key', validators=[DataRequired()])
    submit = SubmitField('Save API Key')

class PromptTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    template = TextAreaField('Prompt Template', validators=[DataRequired()])
    submit = SubmitField('Save Template')

class EvaluationForm(FlaskForm):
    template = SelectField('Prompt Template', validators=[DataRequired()])
    model = SelectField('Model', choices=[
        ('claude-3-7-sonnet-20250219', 'Claude 3.7 Sonnet'),
        ('claude-3-opus-20240229', 'Claude 3 Opus'),
        ('claude-3-5-sonnet-20240620', 'Claude 3.5 Sonnet')
    ])
    frames_folder = FileField('Upload Frames (ZIP)')
    submit = SubmitField('Run Evaluation')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = next((u for u in users.values() if u.username == username), None)
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get count of saved templates
    template_count = len([f for f in os.listdir('prompts') if f.endswith('.json')])
    
    # Get count of completed evaluations
    eval_count = len([f for f in os.listdir('results') if f.endswith('.json')])
    
    # Check if API key is set
    api_key_set = current_user.api_key is not None
    
    return render_template('dashboard.html', 
                          template_count=template_count,
                          eval_count=eval_count,
                          api_key_set=api_key_set)

@app.route('/api-key', methods=['GET', 'POST'])
@login_required
def api_key():
    form = APIKeyForm()
    if form.validate_on_submit():
        # In a real app, you'd encrypt this key before storing
        users[current_user.id].api_key = form.api_key.data
        flash('API Key saved successfully')
        return redirect(url_for('dashboard'))
    
    if current_user.api_key:
        form.api_key.data = current_user.api_key
    
    return render_template('api_key.html', form=form)

@app.route('/prompt-templates')
@login_required
def prompt_templates():
    templates = []
    for filename in os.listdir('prompts'):
        if filename.endswith('.json'):
            with open(os.path.join('prompts', filename), 'r') as f:
                template = json.load(f)
                templates.append(template)
    
    return render_template('prompt_templates.html', templates=templates)

@app.route('/prompt-templates/new', methods=['GET', 'POST'])
@login_required
def new_template():
    form = PromptTemplateForm()
    if form.validate_on_submit():
        template = {
            'id': str(uuid.uuid4()),
            'name': form.name.data,
            'description': form.description.data,
            'template': form.template.data,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        filename = f"{template['id']}.json"
        with open(os.path.join('prompts', filename), 'w') as f:
            json.dump(template, f, indent=2)
        
        flash('Template saved successfully')
        return redirect(url_for('prompt_templates'))
    
    return render_template('new_template.html', form=form)

@app.route('/prompt-templates/<template_id>', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    template_path = os.path.join('prompts', f"{template_id}.json")
    
    if not os.path.exists(template_path):
        flash('Template not found')
        return redirect(url_for('prompt_templates'))
    
    with open(template_path, 'r') as f:
        template = json.load(f)
    
    form = PromptTemplateForm()
    
    if form.validate_on_submit():
        template['name'] = form.name.data
        template['description'] = form.description.data
        template['template'] = form.template.data
        template['updated_at'] = datetime.datetime.now().isoformat()
        
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=2)
        
        flash('Template updated successfully')
        return redirect(url_for('prompt_templates'))
    
    # Pre-fill form
    form.name.data = template['name']
    form.description.data = template['description']
    form.template.data = template['template']
    
    return render_template('edit_template.html', form=form, template=template)

@app.route('/evaluations')
@login_required
def evaluations():
    evaluations = []
    for filename in os.listdir('results'):
        if filename.endswith('.json'):
            with open(os.path.join('results', filename), 'r') as f:
                eval_data = json.load(f)
                evaluations.append(eval_data)
    
    # Sort by timestamp, newest first
    evaluations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return render_template('evaluations.html', evaluations=evaluations)

@app.route('/evaluations/<eval_id>')
@login_required
def view_evaluation(eval_id):
    eval_path = os.path.join('results', f"{eval_id}.json")
    
    if not os.path.exists(eval_path):
        flash('Evaluation not found')
        return redirect(url_for('evaluations'))
    
    with open(eval_path, 'r') as f:
        evaluation = json.load(f)
    
    return render_template('view_evaluation.html', evaluation=evaluation)

@app.route('/new-evaluation', methods=['GET', 'POST'])
@login_required
def new_evaluation():
    # Check if API key is set
    if not current_user.api_key:
        flash('Please set your API key first')
        return redirect(url_for('api_key'))
    
    form = EvaluationForm()
    
    # Populate template choices
    templates = []
    for filename in os.listdir('prompts'):
        if filename.endswith('.json'):
            with open(os.path.join('prompts', filename), 'r') as f:
                template = json.load(f)
                templates.append((template['id'], template['name']))
    
    form.template.choices = templates
    
    if form.validate_on_submit():
        # Process the frames (in a real app, handle ZIP extraction)
        # For this example, we'll assume frames are uploaded individually
        
        # Get selected template
        template_id = form.template.data
        template_path = os.path.join('prompts', f"{template_id}.json")
        
        with open(template_path, 'r') as f:
            template = json.load(f)
        
        # Create a unique ID for this evaluation
        eval_id = str(uuid.uuid4())
        eval_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'frames', eval_id)
        os.makedirs(eval_dir, exist_ok=True)
        
        # In a real app, handle file uploads properly
        # For now, we'll assume the frames are already in the directory
        
        # Initialize the evaluator
        evaluator = CausalPromptEvaluator(current_user.api_key)
        
        # Run the evaluation
        evaluation = evaluator.run_full_evaluation(eval_dir)
        
        # Add additional metadata
        evaluation['id'] = eval_id
        evaluation['template_id'] = template_id
        evaluation['template_name'] = template['name']
        evaluation['model'] = form.model.data
        
        # Save the evaluation results
        with open(os.path.join('results', f"{eval_id}.json"), 'w') as f:
            json.dump(evaluation, f, indent=2)
        
        flash('Evaluation completed successfully')
        return redirect(url_for('view_evaluation', eval_id=eval_id))
    
    return render_template('new_evaluation.html', form=form)

@app.route('/api/templates')
@login_required
def api_templates():
    templates = []
    for filename in os.listdir('prompts'):
        if filename.endswith('.json'):
            with open(os.path.join('prompts', filename), 'r') as f:
                template = json.load(f)
                templates.append(template)
    
    return jsonify(templates)

@app.route('/api/evaluations')
@login_required
def api_evaluations():
    evaluations = []
    for filename in os.listdir('results'):
        if filename.endswith('.json'):
            with open(os.path.join('results', filename), 'r') as f:
                evaluation = json.load(f)
                evaluations.append(evaluation)
    
    return jsonify(evaluations)

if __name__ == '__main__':
    app.run(debug=True)
