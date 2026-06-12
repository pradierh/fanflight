#!/bin/bash
python /app/init_database/init_db.py
python /app/init_database/load_static_data.py
python /opt/data/raw_data/replay_job.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload