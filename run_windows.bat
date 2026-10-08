@echo off
python -m pip install -r requirements.txt
python data/generate_demo_data.py
python -m database.seed
streamlit run app.py
pause
