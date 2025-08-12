import cv2



class VideoProcessor:
    @staticmethod
    def extract_all_frames(video, output_folder="v2_frames"):
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video {video}')
        
        saved_count = 0
        
        while True: 
            ret, frame = cap.read()
            if not ret: 
                break
            
            filename = f"{output_folder}/frame_{saved_count:04d}.png"
            cv2.imwrite(filename, frame)
            saved_count += 1
            
        cap.release()
        
        print(f"Extracted {saved_count} frames.")

    @staticmethod
    def extract_frame_per_x_seconds(video, seconds, output_folder="v2_frames"):
        cap = cv2.VideoCapture(video)
        if not cap.isOpened():
            raise RuntimeError(f'Cannot open video {video}')
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps*seconds)
        
        frame_count = 0
        saved_count = 0
        
        while True: 
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                filename = f"{output_folder}/frame_{saved_count:04d}.png"
                cv2.imwrite(filename, frame)
                saved_count += 1
            
            frame_count += 1
            
        cap.release()
        
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