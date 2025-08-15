import os
import shutil
import sqlite3
from datetime import datetime
import json

from v2_processing import VideoProcessor
from v2_configurations import road_health, people_counting, audio_sentiment
from v2_analysis import GeminiConnection


# Pick target folder
# Pick mode (Video, timelapse, audio, photo)
# Search for eligible files in target folder
# For each eligible file, run process


def get_eligible_files(target_folder:str, mode:str): # returns dict, list (result, eligible_files)
    eligible_files = []
    mode_to_filetype = {
        "video": [".mp4"],
        "photo": [".png", ".jpg", ".jpeg", ".pdf"],
        "timelapse": [".mp4"],
        "audio": [".mp3", ".m4a"]
    }
    
    extensions = [ext.lower() for ext in mode_to_filetype[mode]]
    
    all_files = os.listdir(target_folder)
    
    for file in all_files:
        ext = os.path.splitext(file)[1].lower()
        if ext in extensions:
            eligible_files.append(file)
    
    result = {f"get_eligible_files({target_folder})": "success"}
    return result, eligible_files


def process_single_file(file: str, mode: str, seconds_per_frame: int, analysis_folder: str, output_folder:str) -> dict:
    filepath = file
    destpath = analysis_folder
    
    conn = sqlite3.connect("v2_points.db")
    cursor = conn.cursor()

    
    # Initial DB save (no metadata, no analysis)
    process_datetime = datetime.now()
    command = """INSERT INTO items (source_filename, process_datetime, metadata, analysis) VALUES (?, ?, ?, ?)"""
    cursor.execute(command, (os.path.basename(file), process_datetime, '', ''))
    conn.commit()
    


    if mode in ("video", "timelapse"):
        if mode == "timelapse":
            VideoProcessor.extract_frames(filepath, seconds_per_frame=0, output_folder=analysis_folder)
        else:
            VideoProcessor.extract_frames(filepath, seconds_per_frame, output_folder=analysis_folder)
        shutil.move(filepath, output_folder)
    elif mode in ("audio", "photo"):
        shutil.move(filepath, destpath)

    result = {f"process_single_file({file})": "success"}
    conn.close()
    return result

def analyze_single_file(client:GeminiConnection, file:str, config, model:str): # Returns dict, dict (result, analysis)
    
    analysis = client.analyze_content(file, config, model=model)
    
    result = {f"analyze_single_file({file})": "success"}
    return result, analysis

def update_item(mode: str, source_filename: str, analysis: dict, frame_filename=None, metadata=None,):
    """
    Updates a single item in the database.
    For 'audio' and 'photo' modes, it performs an exact match on `source_filename`.
    For 'video' and 'timelapse' modes, it performs a substring match.
    """
    conn = sqlite3.connect("v2_points.db")
    cursor = conn.cursor()
    
    analysis_str = json.dumps(analysis or {"Hello": "World"})
    metadata_str = json.dumps(metadata or {"Hello": "World"})

    if mode in ("audio", "photo"):
        update_command = """UPDATE items SET metadata = ?, analysis = ? WHERE source_filename = ?"""
        cursor.execute(update_command, (metadata_str, analysis_str, source_filename))
    elif mode in ("video", "timelapse"):
        # Using LIKE to find a source_filename that CONTAINS the provided string.
        update_both_command = """UPDATE items SET metadata = ?, analysis = ? WHERE source_filename LIKE ?"""
        update_metadata_command = """UPDATE items SET metadata = ? WHERE source_filename LIKE ?"""
        update_analysis_command = """UPDATE items SET analysis = ? WHERE source_filename LIKE ?"""
        filename_pattern = f"%{frame_filename}%"
        
        if metadata and analysis:
            cursor.execute(update_both_command, (metadata_str, analysis_str, filename_pattern))
        elif metadata:
            cursor.execute(update_metadata_command, (metadata_str, filename_pattern))
        elif analysis:
            cursor.execute(update_analysis_command, (analysis_str, filename_pattern))

    conn.commit()
    conn.close()

def main(input_folder:str="default_input", mode:str="video", seconds_per_frame:int=1, analysis_folder:str="v2_analysis", config=people_counting, model="gemini-2.5-flash-lite", output_folder:str="v2_output_content"):
    results = []
    analyses = []
    
    
    client = GeminiConnection()
    
    if os.path.exists(input_folder):
        result, eligible_files = get_eligible_files(input_folder, mode)
    
    results.append(result)
    
    
    
    # Process files (Input -> Analysis)
    for source_file in eligible_files:
        filepath = os.path.join(input_folder, source_file)
        result = process_single_file(filepath, mode, seconds_per_frame, analysis_folder, output_folder)
        results.append(result)
        
        
        # Analyze files (Analysis -> Output)    
        files_to_analyze = os.listdir(analysis_folder)
        for file in files_to_analyze:
            filepath = os.path.join(analysis_folder, file)
            result, analysis = analyze_single_file(client, filepath, config, model)
            print(file)
            if mode == "video" or mode == "timelapse":
                client.update_point(file, analysis)
                update_item(mode, source_file, analysis, file)
            elif mode == "audio":
                update_item(mode, file, analysis=analysis)
                
            file_analysis = {file: analysis}
            results.append(result)
            analyses.append(file_analysis)
            shutil.move(filepath, output_folder)
        
        
        
    client.export_db_to_json()
    client.clear_table()
    
    client.close_db()
        
    
        
        
    
    print(results)
    print("\n\n\n")
    print(analyses)



if __name__ == "__main__":
    input_folder = "v2_input"
    mode = "audio"
    seconds_per_frame = 1
    analysis_folder = "v2_analysis"
    output_folder = "v2_output_content"
    config = audio_sentiment
    model = "gemini-2.5-flash-lite"
    main(input_folder, mode, seconds_per_frame, analysis_folder, config, model, output_folder)