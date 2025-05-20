from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import date
import re

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="panda",
        database="fitness"
    )
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Email validation: must contain '@'
        if '@' not in email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address!')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT * FROM Users WHERE Email = %s", (email,))
        if cursor.fetchone():
            flash('Email already registered or invalid entry!')
            cursor.close()
            conn.close()
            return render_template('register.html')

        # Generate unique UserID
        cursor.execute("SELECT MAX(UserID) FROM Users")
        result = cursor.fetchone()
        new_id = 1 if result[0] is None else result[0] + 1

        # Insert new user
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO Users (UserID, Name, Email, PasswordHash) VALUES (%s, %s, %s, %s)",
            (new_id, name, email, hashed_password)
        )
        conn.commit()

        flash('Registration successful! Please login.')
        cursor.close()
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['PasswordHash'], password):
            session['user_id'] = user['UserID']
            session['user_name'] = user['Name']
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password')

        cursor.close()
        conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/fitnessgoal', methods=['GET', 'POST'])
def fitnessgoal():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        target_calories = request.form['target_calories']
        target_body_fat = request.form['target_body_fat']
        goal_type = request.form['goal_type']

        # Check if user already has a goal
        cursor.execute("SELECT * FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
        existing_goal = cursor.fetchone()

        if existing_goal:
            # Update existing goal
            cursor.execute("""
                UPDATE FitnessGoal
                SET TargetCalories = %s, TargetBodyFat = %s, GoalType = %s
                WHERE UserID = %s
            """, (target_calories, target_body_fat, goal_type, session['user_id']))
        else:
            # Get next GoalID
            cursor.execute("SELECT MAX(GoalID) FROM FitnessGoal")
            result = cursor.fetchone()
            new_goal_id = 101 if result['MAX(GoalID)'] is None else result['MAX(GoalID)'] + 1

            # Create new goal
            cursor.execute("""
                INSERT INTO FitnessGoal (GoalID, UserID, TargetCalories, TargetBodyFat, GoalType)
                VALUES (%s, %s, %s, %s, %s)
            """, (new_goal_id, session['user_id'], target_calories, target_body_fat, goal_type))

        conn.commit()
        flash('Fitness goal saved successfully!')
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    # Get user's current goals
    cursor.execute("SELECT * FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
    goals = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('fitnessgoal.html', goals=goals)

@app.route('/workoutprogram', methods=['GET', 'POST'])
def workoutprogram():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the user's goal
    cursor.execute("SELECT * FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
    goal = cursor.fetchone()

    if not goal:
        flash('Please set a fitness goal first!')
        cursor.close()
        conn.close()
        return redirect(url_for('fitnessgoal'))

    if request.method == 'POST':
        reps = request.form['reps']
        weight_used = request.form['weight_used']
        calorie_burnt = request.form['calorie_burnt']
        duration = request.form['duration']
        log_date = request.form.get('log_date', date.today().isoformat())

        # Get next ProgramID
        cursor.execute("SELECT MAX(ProgramID) FROM WorkoutProgram")
        result = cursor.fetchone()
        new_program_id = 201 if result['MAX(ProgramID)'] is None else result['MAX(ProgramID)'] + 1

        # Insert workout program
        cursor.execute("""
            INSERT INTO WorkoutProgram 
            (ProgramID, UserID, GoalID, Reps, WeightUsed, CalorieBurnt, Duration, LogDate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_program_id, session['user_id'], goal['GoalID'], reps, weight_used, calorie_burnt, duration, log_date))

        conn.commit()
        flash('Workout program saved successfully!')
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    # Get user's workout history
    cursor.execute("""
        SELECT * FROM WorkoutProgram 
        WHERE UserID = %s 
        ORDER BY LogDate DESC
    """, (session['user_id'],))
    workouts = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('workoutprogram.html', workouts=workouts, date=date)

@app.route('/bodymeasurement', methods=['GET', 'POST'])
def bodymeasurement():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the user's goal
    cursor.execute("SELECT * FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
    goal = cursor.fetchone()

    if not goal:
        flash('Please set a fitness goal first!')
        cursor.close()
        conn.close()
        return redirect(url_for('fitnessgoal'))

    if request.method == 'POST':
        weight = request.form['weight']
        height = request.form['height']
        body_fat = request.form['body_fat']
        chest = request.form['chest']
        hip = request.form['hip']
        log_date = request.form.get('log_date', date.today().isoformat())

        # Get next MeasurementID
        cursor.execute("SELECT MAX(MeasurementID) FROM BodyMeasurement")
        result = cursor.fetchone()
        new_measurement_id = 301 if result['MAX(MeasurementID)'] is None else result['MAX(MeasurementID)'] + 1

        # Insert body measurement
        cursor.execute("""
            INSERT INTO BodyMeasurement 
            (MeasurementID, UserID, GoalID, LogDate, Weight, Height, BodyFatPercentage, Chest, Hip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_measurement_id, session['user_id'], goal['GoalID'], log_date, weight, height, body_fat, chest, hip))

        conn.commit()
        flash('Body measurements saved successfully!')
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    # Get user's measurement history
    cursor.execute("""
        SELECT * FROM BodyMeasurement 
        WHERE UserID = %s 
        ORDER BY LogDate DESC
    """, (session['user_id'],))
    measurements = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('bodymeasurement.html', measurements=measurements, date=date)

@app.route('/nutritionlog', methods=['GET', 'POST'])
def nutritionlog():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the user's goal
    cursor.execute("SELECT * FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
    goal = cursor.fetchone()

    if not goal:
        flash('Please set a fitness goal first!')
        cursor.close()
        conn.close()
        return redirect(url_for('fitnessgoal'))

    if request.method == 'POST':
        meal_type = request.form['meal_type']
        calories = request.form['calories']
        food_item = request.form['food_item']
        carbs = request.form['carbs']
        protein = request.form['protein']
        log_date = request.form.get('log_date', date.today().isoformat())

        # Get next LogID
        cursor.execute("SELECT MAX(LogID) FROM NutritionLog")
        result = cursor.fetchone()
        new_log_id = 401 if result['MAX(LogID)'] is None else result['MAX(LogID)'] + 1

        # Insert nutrition log
        cursor.execute("""
            INSERT INTO NutritionLog 
            (LogID, UserID, GoalID, MealType, Calories, FoodItem, Carbs, Protein, LogDate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (new_log_id, session['user_id'], goal['GoalID'], meal_type, calories, food_item, carbs, protein, log_date))

        conn.commit()
        flash('Nutrition log saved successfully!')
        cursor.close()
        conn.close()
        return redirect(url_for('home'))

    # Get user's nutrition history
    cursor.execute("""
        SELECT * FROM NutritionLog 
        WHERE UserID = %s 
        ORDER BY LogDate DESC
    """, (session['user_id'],))
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('nutritionlog.html', logs=logs, date=date)

@app.route('/myworkoutplan')
def myworkoutplan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT GoalType FROM FitnessGoal WHERE UserID = %s", (session['user_id'],))
    goal = cursor.fetchone()
    cursor.close()
    conn.close()

    if not goal or not goal['GoalType']:
        flash('Please set your fitness goal first!')
        return redirect(url_for('fitnessgoal'))

    goal_type = goal['GoalType'].lower()
    if goal_type == 'basic':
        return render_template('beginner-workout-plan.html')
    elif goal_type == 'intermediate':
        return render_template('intermediate-workout-plan.html')
    elif goal_type == 'advanced':
        return render_template('advanced-workout-plan.html')
    elif goal_type == 'expert':
        return render_template('expert-workout-plan.html')
    else:
        flash('Unknown goal type. Please set your fitness goal again.')
        return redirect(url_for('fitnessgoal'))

if __name__ == '__main__':
    app.run(debug=True)