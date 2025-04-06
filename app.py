import openai
import os
from dotenv import load_dotenv
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)


def convertWeightAndHeight(weight, height):
    weight = weight / 2.20462
    height = height * 2.54
    return weight, height

def convertActivityLevel(activityLevel):
    if activityLevel == 1:
        return 1.2
    elif activityLevel == 2:
        return 1.375
    elif activityLevel == 3:
        return 1.55
    elif activityLevel == 4:
        return 1.725
    elif activityLevel == 5:
        return 1.9

def calculateMaintenanceCalories(weight, height, age, gender, activityLevel):
    # Using Harris-Benedict Equation here
    if gender == "male":
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    return bmr * activityLevel

def calculateCaloriesToGainOrLoss(maintenanceCalories, gainOrLossGoal):
    if gainOrLossGoal == "gain":
        return maintenanceCalories + 500
    elif gainOrLossGoal == "lose":
        return maintenanceCalories - 500
    else:
        return maintenanceCalories

def calculateMacros(calories):
    # Example macro split percentages (these can be adjusted)
    protein = calories * 0.25   # calories from protein
    carbs = calories * 0.45     # calories from carbohydrates
    fats = calories * 0.30      # calories from fats

    # Convert calories to grams:
    # Protein and carbs have 4 calories per gram, fat has 9 calories per gram.
    protein_grams = protein / 4
    carbs_grams = carbs / 4
    fats_grams = fats / 9
    return protein_grams, carbs_grams, fats_grams

def generateMealPlan(calories, protein, carbs, fats, weeklyBudget, numberOfMeals):
    prompt = (
        f"Create a daily meal plan that meets the following nutritional targets and constraints, and return the output as clean HTML (without markdown formatting).\n\n"
        f"<h1>Meal Plan Overview</h1>\n"
        f"<h2>Daily Targets</h2>\n"
        f"<ul>\n"
        f"  <li><strong>Calories</strong>: {int(calories)} kcal</li>\n"
        f"  <li><strong>Protein</strong>: {int(protein)} grams</li>\n"
        f"  <li><strong>Carbohydrates</strong>: {int(carbs)} grams</li>\n"
        f"  <li><strong>Fat</strong>: {int(fats)} grams</li>\n"
        f"</ul>\n"
        f"<p><strong>Weekly Budget</strong>: ${weeklyBudget}</p>\n"
        f"<p><strong>Number of Meals per Day</strong>: {numberOfMeals}</p>\n"
        f"<hr>\n"
        f"Now, provide details for each meal (e.g., breakfast, lunch, dinner, etc.) using the following format for each meal:\n"
        f"<h2>Meal [Number]: [Meal Name]</h2>\n"
        f"<p><strong>Description</strong>: [A brief description of the meal]</p>\n"
        f"<p><strong>Nutritional Breakdown</strong>:</p>\n"
        f"<ul>\n"
        f"  <li>Calories: [value] kcal</li>\n"
        f"  <li>Protein: [value] grams</li>\n"
        f"  <li>Carbohydrates: [value] grams</li>\n"
        f"  <li>Fat: [value] grams</li>\n"
        f"</ul>\n"
        f"<p><strong>Ingredients (with cost details)</strong>:</p>\n"
        f"<ul>\n"
        f"  <li>[Ingredient details]</li>\n"
        f"</ul>\n"
        f"<p><strong>Total Cost for this Meal</strong>: ~$[cost]</p>\n"
        f"<hr>\n"
        f"Finally, provide a summary section with the daily totals and weekly expense in HTML.\n"
        f"Make sure the HTML is clean and well-structured for direct embedding on a webpage."
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # or another valid model if desired
        messages=[
            {"role": "system", "content": "You are a professional nutritionist."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def generateWorkoutPlan(fitness_level, workout_goal, days_per_week, equipment):
    prompt = (
        f"Please create a customized workout plan in clean HTML format (without markdown) for a person with the following details:\n"
        f"- **Fitness Level**: {fitness_level}\n"
        f"- **Workout Goal**: {workout_goal}\n"
        f"- **Days per Week**: {days_per_week}\n"
        f"- **Equipment Available**: {equipment}\n\n"
        "Include a warm-up, main workout exercises (with sets, reps, and rest intervals if applicable), and a cool-down section. "
        "Structure the plan with appropriate headings and lists so that it can be directly embedded into a webpage."
    )
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # or another valid model, such as gpt-4 if available
        messages=[
            {"role": "system", "content": "You are a professional personal trainer."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/meal", methods=["GET", "POST"])
def meal_plan():
    if request.method == "POST":
        try:
            weight = float(request.form.get("weight"))
            height = float(request.form.get("height"))
            age = int(request.form.get("age"))
            gender = request.form.get("gender").lower()
            activity_input = int(request.form.get("activity_level"))
            gainOrLossGoal = request.form.get("goal").lower()
            weeklyBudget = float(request.form.get("weekly_budget"))
            numberOfMeals = int(request.form.get("number_of_meals"))
        except Exception as e:
            return f"Input error: {e}"

        weight_kg, height_cm = convertWeightAndHeight(weight, height)
        activityLevel = convertActivityLevel(activity_input)
        maintenanceCalories = calculateMaintenanceCalories(weight_kg, height_cm, age, gender, activityLevel)
        targetCalories = calculateCaloriesToGainOrLoss(maintenanceCalories, gainOrLossGoal)
        protein, carbs, fats = calculateMacros(targetCalories)
        mealPlan = generateMealPlan(targetCalories, protein, carbs, fats, weeklyBudget, numberOfMeals)
        
        return render_template("meal_result.html",
                               targetCalories=int(targetCalories),
                               protein=int(protein),
                               carbs=int(carbs),
                               fats=int(fats),
                               mealPlan=mealPlan)
    # Render the meal plan form on GET requests.
    return render_template("meal.html")

@app.route("/workout", methods=["GET", "POST"])
def workout():
    if request.method == "POST":
        try:
            fitness_level = request.form.get("fitness_level")
            workout_goal = request.form.get("workout_goal")
            days_per_week = int(request.form.get("days_per_week"))
            equipment = request.form.get("equipment")
        except Exception as e:
            return f"Input error: {e}"
        
        workout_plan = generateWorkoutPlan(fitness_level, workout_goal, days_per_week, equipment)
        return render_template("workout_result.html", workoutPlan=workout_plan)
    
    return render_template("workout.html")

if __name__ == "__main__":
    app.run(debug=True)