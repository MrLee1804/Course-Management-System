from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import pandas as pd
import os
from datetime import datetime, timedelta
import json
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

# Read courses from CSV
def load_courses():
    return pd.read_csv('courses.csv')

# Initialize user data (in a real app, this would be in a database)
users = {
    'demo@example.com': {
        'password': 'demo123',
        'enrolled_courses': [],
        'reviews': {},
        'progress': {},
        'completed_courses': [],
        'quiz_scores': {},
        'forum_posts': [],
        'calendar_events': [],
        'downloads': {},
        'bookmarks': []
    }
}

# Sample quiz data (in a real app, this would be in a database)
quizzes = {
    0: {  # Python Programming Basics
        'questions': [
            {
                'question': 'What is Python?',
                'options': ['A programming language', 'A snake', 'A text editor', 'An operating system'],
                'correct': 0
            },
            {
                'question': 'Which of these is not a Python data type?',
                'options': ['int', 'float', 'string', 'char'],
                'correct': 3
            }
        ]
    }
}

# Sample forum data (in a real app, this would be in a database)
forum_posts = {
    0: [  # Python Programming Basics
        {
            'user': 'demo@example.com',
            'title': 'Help with Python installation',
            'content': 'I need help installing Python on my computer.',
            'date': '2024-03-15',
            'replies': [
                {
                    'user': 'john@example.com',
                    'content': 'Check the installation guide in the course materials.',
                    'date': '2024-03-16'
                }
            ]
        }
    ]
}

# Sample course resources (in a real app, this would be in a file system)
course_resources = {
    0: [  # Python Programming Basics
        {
            'name': 'Python Installation Guide',
            'type': 'pdf',
            'size': '2.5 MB',
            'url': 'static/resources/python_guide.pdf'
        },
        {
            'name': 'Code Examples',
            'type': 'zip',
            'size': '1.8 MB',
            'url': 'static/resources/python_examples.zip'
        }
    ]
}

def generate_certificate(user_email, course_name, instructor):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    
    # Create the PDF content
    story = []
    story.append(Paragraph("Certificate of Completion", title_style))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"This is to certify that", styles['Normal']))
    story.append(Paragraph(user_email, styles['Heading2']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"has successfully completed the course", styles['Normal']))
    story.append(Paragraph(course_name, styles['Heading3']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"under the instruction of", styles['Normal']))
    story.append(Paragraph(instructor, styles['Heading3']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    
    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def get_course_recommendations(user_email, courses):
    if 'user' not in session:
        return []
    
    user_courses = users[user_email]['enrolled_courses']
    if not user_courses:
        return []
    
    # Get categories of enrolled courses
    enrolled_categories = set(courses.iloc[i]['category'] for i in user_courses)
    
    # Find courses in similar categories that user hasn't enrolled in
    recommendations = []
    for idx, course in courses.iterrows():
        if idx not in user_courses and course['category'] in enrolled_categories:
            recommendations.append(course)
    
    # Return up to 3 random recommendations
    return random.sample(recommendations, min(3, len(recommendations)))

@app.route('/')
def home():
    courses = load_courses()
    categories = courses['category'].unique()
    search_query = request.args.get('search', '')
    
    if search_query:
        courses = courses[courses['course_name'].str.contains(search_query, case=False) |
                         courses['description'].str.contains(search_query, case=False)]
    
    recommendations = []
    if 'user' in session:
        recommendations = get_course_recommendations(session['user'], courses)
    
    return render_template('index.html', 
                         courses=courses, 
                         categories=categories, 
                         search_query=search_query,
                         recommendations=recommendations)

@app.route('/category/<category>')
def category(category):
    courses = load_courses()
    category_courses = courses[courses['category'] == category]
    return render_template('category.html', courses=category_courses, category=category)

@app.route('/course/<int:index>')
def course_detail(index):
    courses = load_courses()
    course = courses.iloc[index]
    is_enrolled = False
    user_review = None
    progress = 0
    is_completed = False
    quiz_data = quizzes.get(index, {'questions': []})
    forum_data = forum_posts.get(index, [])
    resources = course_resources.get(index, [])
    
    if 'user' in session:
        user_email = session['user']
        is_enrolled = index in users[user_email]['enrolled_courses']
        user_review = users[user_email]['reviews'].get(str(index))
        progress = users[user_email]['progress'].get(str(index), 0)
        is_completed = index in users[user_email]['completed_courses']
    
    return render_template('course_detail.html', 
                         course=course, 
                         courses=courses,
                         is_enrolled=is_enrolled,
                         user_review=user_review,
                         progress=progress,
                         is_completed=is_completed,
                         quiz_data=quiz_data,
                         forum_data=forum_data,
                         resources=resources)

@app.route('/enroll/<int:index>')
def enroll_course(index):
    if 'user' not in session:
        flash('Please login to enroll in courses', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['enrolled_courses']:
        users[user_email]['enrolled_courses'].append(index)
        users[user_email]['progress'][str(index)] = 0
        flash('Successfully enrolled in the course!', 'success')
    else:
        flash('You are already enrolled in this course', 'info')
    
    return redirect(url_for('course_detail', index=index))

@app.route('/update_progress/<int:index>', methods=['POST'])
def update_progress(index):
    if 'user' not in session:
        flash('Please login to update progress', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['enrolled_courses']:
        flash('Please enroll in the course first', 'warning')
        return redirect(url_for('course_detail', index=index))
    
    progress = int(request.form.get('progress', 0))
    users[user_email]['progress'][str(index)] = progress
    
    # Check if course is completed (progress >= 100)
    if progress >= 100 and index not in users[user_email]['completed_courses']:
        users[user_email]['completed_courses'].append(index)
        flash('Congratulations! You have completed the course!', 'success')
    
    return redirect(url_for('course_detail', index=index))

@app.route('/certificate/<int:index>')
def download_certificate(index):
    if 'user' not in session:
        flash('Please login to download certificate', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['completed_courses']:
        flash('Please complete the course first', 'warning')
        return redirect(url_for('course_detail', index=index))
    
    courses = load_courses()
    course = courses.iloc[index]
    
    buffer = generate_certificate(user_email, course.course_name, course.instructor)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'certificate_{course.course_name.replace(" ", "_")}.pdf'
    )

@app.route('/review/<int:index>', methods=['POST'])
def submit_review(index):
    if 'user' not in session:
        flash('Please login to submit a review', 'warning')
        return redirect(url_for('login'))
    
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    user_email = session['user']
    users[user_email]['reviews'][str(index)] = {
        'rating': rating,
        'comment': comment,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    flash('Thank you for your review!', 'success')
    return redirect(url_for('course_detail', index=index))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email in users and users[email]['password'] == password:
            session['user'] = email
            flash('Successfully logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Successfully logged out!', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please login to access your dashboard', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    courses = load_courses()
    enrolled_courses = [courses.iloc[i] for i in users[user_email]['enrolled_courses']]
    completed_courses = [courses.iloc[i] for i in users[user_email]['completed_courses']]
    reviews = users[user_email]['reviews']
    progress = users[user_email]['progress']
    
    return render_template('dashboard.html', 
                         enrolled_courses=enrolled_courses,
                         completed_courses=completed_courses,
                         reviews=reviews,
                         courses=courses,
                         progress=progress)

@app.route('/quiz/<int:index>', methods=['GET', 'POST'])
def take_quiz(index):
    if 'user' not in session:
        flash('Please login to take the quiz', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['enrolled_courses']:
        flash('Please enroll in the course first', 'warning')
        return redirect(url_for('course_detail', index=index))
    
    courses = load_courses()  # Load courses data
    
    if request.method == 'POST':
        score = 0
        total = len(quizzes[index]['questions'])
        
        for i, question in enumerate(quizzes[index]['questions']):
            answer = int(request.form.get(f'question_{i}', -1))
            if answer == question['correct']:
                score += 1
        
        users[user_email]['quiz_scores'][str(index)] = {
            'score': score,
            'total': total,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        flash(f'Quiz completed! Your score: {score}/{total}', 'success')
        return redirect(url_for('course_detail', index=index))
    
    return render_template('quiz.html', 
                         course=courses.iloc[index],
                         courses=courses,
                         quiz=quizzes[index],
                         index=index)

@app.route('/forum/<int:index>', methods=['GET', 'POST'])
def course_forum(index):
    if 'user' not in session:
        flash('Please login to access the forum', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['enrolled_courses']:
        flash('Please enroll in the course first', 'warning')
        return redirect(url_for('course_detail', index=index))
    
    courses = load_courses()  # Load courses data
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if index not in forum_posts:
            forum_posts[index] = []
        
        forum_posts[index].append({
            'user': user_email,
            'title': title,
            'content': content,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'replies': []
        })
        
        flash('Post created successfully!', 'success')
        return redirect(url_for('course_forum', index=index))
    
    return render_template('forum.html',
                         course=courses.iloc[index],
                         courses=courses,
                         posts=forum_posts.get(index, []),
                         index=index)

@app.route('/reply/<int:index>/<int:post_index>', methods=['POST'])
def reply_to_post(index, post_index):
    if 'user' not in session:
        flash('Please login to reply', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    content = request.form.get('content')
    
    forum_posts[index][post_index]['replies'].append({
        'user': user_email,
        'content': content,
        'date': datetime.now().strftime('%Y-%m-%d')
    })
    
    flash('Reply posted successfully!', 'success')
    return redirect(url_for('course_forum', index=index))

@app.route('/calendar')
def view_calendar():
    if 'user' not in session:
        flash('Please login to view your calendar', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    courses = load_courses()
    enrolled_courses = [courses.iloc[i] for i in users[user_email]['enrolled_courses']]
    
    # Generate calendar events from course schedules
    events = []
    for course in enrolled_courses:
        for week in course.schedule.split('\n'):
            events.append({
                'title': f"{course.course_name} - {week}",
                'start': datetime.now().strftime('%Y-%m-%d'),
                'end': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            })
    
    return render_template('calendar.html', events=events)

@app.route('/download/<int:index>/<int:resource_index>')
def download_resource(index, resource_index):
    if 'user' not in session:
        flash('Please login to download resources', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index not in users[user_email]['enrolled_courses']:
        flash('Please enroll in the course first', 'warning')
        return redirect(url_for('course_detail', index=index))
    
    resource = course_resources[index][resource_index]
    if str(index) not in users[user_email]['downloads']:
        users[user_email]['downloads'][str(index)] = []
    
    users[user_email]['downloads'][str(index)].append({
        'resource': resource['name'],
        'date': datetime.now().strftime('%Y-%m-%d')
    })
    
    try:
        return send_file(resource['url'], as_attachment=True)
    except FileNotFoundError:
        flash('Resource file not found', 'error')
        return redirect(url_for('course_detail', index=index))

@app.route('/search')
def search_courses():
    courses = load_courses()
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    duration = request.args.get('duration', '')
    instructor = request.args.get('instructor', '')
    
    # Filter courses based on search criteria
    filtered_courses = courses
    
    if query:
        filtered_courses = filtered_courses[
            filtered_courses['course_name'].str.contains(query, case=False) |
            filtered_courses['description'].str.contains(query, case=False)
        ]
    
    if category:
        filtered_courses = filtered_courses[filtered_courses['category'] == category]
    
    if duration:
        filtered_courses = filtered_courses[filtered_courses['duration'] == duration]
    
    if instructor:
        filtered_courses = filtered_courses[filtered_courses['instructor'] == instructor]
    
    categories = courses['category'].unique()
    durations = courses['duration'].unique()
    instructors = courses['instructor'].unique()
    
    return render_template('search.html',
                         courses=filtered_courses,
                         categories=categories,
                         durations=durations,
                         instructors=instructors,
                         query=query,
                         selected_category=category,
                         selected_duration=duration,
                         selected_instructor=instructor)

@app.route('/compare')
def compare_courses():
    courses = load_courses()
    course_ids = request.args.getlist('courses')
    selected_courses = []
    
    for course_id in course_ids:
        try:
            index = int(course_id)
            if 0 <= index < len(courses):
                selected_courses.append(courses.iloc[index])
        except ValueError:
            continue
    
    return render_template('compare.html',
                         selected_courses=selected_courses,
                         all_courses=courses)

@app.route('/bookmark/<int:index>')
def toggle_bookmark(index):
    if 'user' not in session:
        flash('Please login to bookmark courses', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    if index in users[user_email]['bookmarks']:
        users[user_email]['bookmarks'].remove(index)
        flash('Course removed from bookmarks', 'info')
    else:
        users[user_email]['bookmarks'].append(index)
        flash('Course added to bookmarks', 'success')
    
    return redirect(url_for('course_detail', index=index))

@app.route('/bookmarks')
def view_bookmarks():
    if 'user' not in session:
        flash('Please login to view your bookmarks', 'warning')
        return redirect(url_for('login'))
    
    user_email = session['user']
    courses = load_courses()
    bookmarked_courses = [courses.iloc[i] for i in users[user_email]['bookmarks']]
    
    return render_template('bookmarks.html', 
                         courses=courses,
                         bookmarked_courses=bookmarked_courses)

if __name__ == '__main__':
    app.run(debug=True) 