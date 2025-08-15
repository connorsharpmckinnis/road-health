import cv2
from datetime import datetime
import os
import sqlite3
import json



class VideoProcessor:
    @staticmethod
    def extract_all_frames(video, output_folder="v2_frames"):
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video {video}')
        
        source_filename = os.path.basename(video)
        process_datetime = datetime.now()
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        conn = sqlite3.connect("v2_points.db")
        cursor = conn.cursor()
        
        
        saved_count = 0
        
        while True: 
            ret, frame = cap.read()
            if not ret: 
                break
            filename = f"{source_filename}_{saved_count:04d}.png"
            filepath = f"{output_folder}/{filename}"
            cv2.imwrite(filepath, frame)
            
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
            analysis = json.dumps({})
            
            metadata = {
                "frame_filename": filename,
                "timestamp_ms": timestamp_ms,
                "width": width,
                "height": height,
                "fps": fps,
            }

            
            command = """INSERT INTO points (source_filename, frame_filename, process_datetime, timestamp_ms, width, height, fps, analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            
            cursor.execute(command, (source_filename, filename, process_datetime, timestamp_ms, width, height, fps, analysis))
                
            # Update row in the items database that has a matching source_filename value with the new metadata variable
            update_command = """UPDATE items SET metadata = ? WHERE source_filename = ?"""
            cursor.execute(update_command, (json.dumps(metadata), source_filename))
            
            saved_count += 1
            
        cap.release()
        conn.commit()
        cursor.close()
        
        print(f"Extracted {saved_count} frames.")

    @staticmethod
    def extract_frame_per_x_seconds(video, seconds, output_folder="v2_frames"):
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video {video}')
        
        source_filename = os.path.basename(video)
        process_datetime = datetime.now()
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps*seconds)
        
        conn = sqlite3.connect("v2_points.db")
        cursor = conn.cursor()
        
        frame_count = 0
        saved_count = 0
        
        while True: 
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                filename = f"frame_{saved_count:04d}.png"
                filepath = f"{output_folder}/{filename}"
                cv2.imwrite(filepath, frame)
                
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                analysis = json.dumps({})
                
                command = """INSERT INTO points (source_filename, frame_filename, process_datetime, timestamp_ms, width, height, fps, analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
                
                cursor.execute(command, (source_filename, filename, process_datetime, timestamp_ms, width, height, fps, analysis))
                
                saved_count += 1
            
            frame_count += 1
            
        cap.release()
        conn.commit()
        cursor.close()
        
        print(f"Extracted {saved_count} frames from a total of {frame_count} (ratio: {(saved_count/frame_count * fps):.1f})")
        
    @staticmethod
    def extract_frames(video:str, seconds_per_frame=None, output_folder:str="v2_frames"):
        
        
        if seconds_per_frame:
            VideoProcessor.extract_frame_per_x_seconds(video, seconds_per_frame, output_folder)
        else: 
            VideoProcessor.extract_all_frames(video, output_folder)
        
    
    
def main():
    video = "v2_images/conversation.mp4"
    #extract_frame_per_x_seconds(video, 2)
    #extract_all_frames(video)
    
    VideoProcessor.extract_frames(video)
    
if __name__ == "__main__":
    main()