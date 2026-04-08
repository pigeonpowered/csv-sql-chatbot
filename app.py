from flask import Flask, render_template, request
import generator
import os

app = Flask(__name__)
history = []

@app.route("/", methods=['GET', 'POST'])
def home():
    answer = ""
    submitted_text = None

    if request.method == 'POST':
        submitted_text = request.form['textbox']
        answer = get_response(submitted_text)
        history.insert(0,(submitted_text, answer))

    return render_template("page.html", message=history)

@app.route("/app", methods=['GET', 'POST'])
def app_response():
    answer = ""
    submitted_text = request.args.get('text')
    
    if request.method == 'POST' or request.method == 'GET':
        answer = get_response(submitted_text)
        history.append((submitted_text, answer))

    return answer

def get_response(question):
    prompt = generator.SqlPrompt(table = "PS_ACORD_HEADER")

    prompt.set_prompt(question = question)

    prompt.ask_question(question = question, openai_api_key = os.getenv('OPENAI_KEY'))

    return(prompt.query)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)