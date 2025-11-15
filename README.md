How to Update cloned repo
git branch
git pull origin <branch you want to get>


python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Run the App
uvicorn main:app --host 0.0.0.0 --port 8000