import os
import shutil

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
        "audio": [".mp3"]
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

    if mode in ("video", "timelapse"):
        if mode == "timelapse":
            VideoProcessor.extract_frames(filepath, seconds_per_frame=0, output_folder=analysis_folder)
        else:
            VideoProcessor.extract_frames(filepath, seconds_per_frame, output_folder=analysis_folder)
        shutil.move(filepath, output_folder)
    elif mode in ("audio", "photo"):
        shutil.move(filepath, destpath)

    result = {f"process_single_file({file})": "success"}
    return result

def analyze_single_file(client:GeminiConnection, file:str, config, model:str): # Returns dict, dict (result, analysis)
    
    analysis = client.analyze_content(file, config, model=model)
    
    result = {f"analyze_single_file({file})": "success"}
    return result, analysis




def main(input_folder:str="default_input", mode:str="video", seconds_per_frame:int=1, analysis_folder:str="v2_analysis", config=people_counting, model="gemini-2.5-flash-lite", output_folder:str="v2_output_content"):
    results = []
    analyses = []
    
    
    client = GeminiConnection()
    
    if os.path.exists(input_folder):
        result, eligible_files = get_eligible_files(input_folder, mode)
    
    results.append(result)
    
    
    
    # Process files (Input -> Analysis)
    for file in eligible_files:
        filepath = os.path.join(input_folder, file)
        result = process_single_file(filepath, mode, seconds_per_frame, analysis_folder, output_folder)
        results.append(result)
        
        
        # Analyze files (Analysis -> Output)    
        files_to_analyze = os.listdir(analysis_folder)
        for file in files_to_analyze:
            filepath = os.path.join(analysis_folder, file)
            result, analysis = analyze_single_file(client, filepath, config, model)
            print(file)
            client.update_point(file, analysis)
            
            file_analysis = {file: analysis}
            results.append(result)
            analyses.append(file_analysis)
            shutil.move(filepath, output_folder)
        
    client.export_db_to_json()
    client.clear_points_table()
    
    client.close_db()
        
    
        
        
    
    print(results)
    print("\n\n\n")
    print(analyses)



if __name__ == "__main__":
    input_folder = "v2_input"
    mode = "video"
    seconds_per_frame = 1
    analysis_folder = "v2_analysis"
    output_folder = "v2_output_content"
    config = people_counting
    model = "gemini-2.5-flash-lite"
    main(input_folder, mode, seconds_per_frame, analysis_folder, config, model, output_folder)