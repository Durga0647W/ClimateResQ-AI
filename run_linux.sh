#!/bin/bash
python3 -m pip install -r requirements.txt
python3 data/generate_demo_data.py
python3 -m database.seed
streamlit run app.py
