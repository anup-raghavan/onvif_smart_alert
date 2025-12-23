import cv2
import threading
import time
import urllib.request

class StreamPlayer:
    def __init__(self, uri, window_name="ONVIF Camera Stream", webhook_url=None, mode="detect", train_output_dir="dataset", trainer_file="trainer.yml", person_name="Unknown"):
        """
        Initialize the StreamPlayer.
        :param uri: RTSP Stream URI
        :param window_name: Name of the display window
        :param webhook_url: URL to trigger on face detection (detect mode)
        :param mode: 'detect' or 'train'
        :param train_output_dir: Directory to save images in train mode
        :param trainer_file: Path to trained model
        :param person_name: Name of the person to recognize
        """
        self.uri = uri
        self.window_name = window_name
        self.webhook_url = webhook_url
        self.mode = mode
        self.train_output_dir = train_output_dir
        self.person_name = person_name
        self.running = False
        self.thread = None
        self.cap = None
        
        # Ensure dataset dir exists if training
        import os
        if self.mode == "train" and not os.path.exists(self.train_output_dir):
            os.makedirs(self.train_output_dir)
            
        # Initialize Face Detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Initialize Face Recognition (LBPH)
        self.names = {}
        if self.mode == "detect" and os.path.exists(trainer_file):
            print(f"Loading Face Recognizer model from {trainer_file}...")
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            self.recognizer.read(trainer_file)
            
            # Load names mapping
            map_file = "names.json"
            if os.path.exists(map_file):
                import json
                with open(map_file, 'r') as f:
                    self.names = json.load(f)
                # Convert keys to int (json keys are always strings)
                self.names = {int(k): v for k, v in self.names.items()}
                print(f"Loaded {len(self.names)} names: {list(self.names.values())}")
        elif self.mode == "detect":
            print("WARNING: No trainer.yml found. Face recognition disabled (Detection only).")

        # Trigger control

        # Trigger control
        self.last_trigger_time = 0
        self.trigger_cooldown = 15.0 # Seconds between triggers
        
        # Performance optimization
        self.frame_count = 0
        self.last_faces = [] # Stores (x,y,w,h)
        self.saved_count = 0 # For training mode
        
        # Stability Filter
        self.consecutive_recognition_count = 0
        self.last_recognized_candidate = None

    def start(self):
        """
        Start the video playback in a separate thread.
        """
        if self.running:
            print("Stream is already running.")
    def run(self):
        """
        Start the video playback (Blocking).
        """
        self.running = True
        self._update()

    def stop(self):
        """
        Stop the video playback.
        """
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyWindow(self.window_name)
        print("Stream player stopped.")

    def _update(self):
        """
        Main video loop.
        """
        # Force TCP (already set in environment, but good to know)
        self.cap = cv2.VideoCapture(self.uri, cv2.CAP_FFMPEG)
        
        if not self.cap.isOpened():
            print(f"Error: Could not open stream {self.uri}")
            self.running = False
            return

        print(f"Opening stream: {self.uri}")

        # Create window with resizing capability
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        while self.running:
            try:
                 # Debug blocking
                 # print("r", end="", flush=True) 
                 ret, frame = self.cap.read()
                 # print("d", end="", flush=True)
            except Exception as e:
                print(f"Error reading frame: {e}")
                break

            if not ret:
                print("\nError: Lost frame or stream ended. Attempting reconnect...")
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.uri, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                   print("Reconnect failed.")
                   break
                continue

            # Force UI update even if processing is slow
            if self.frame_count % 5 == 0:
                 cv2.waitKey(1)

            # Skip frames for face detection to improve performance
            # Process every 30th frame (approx once per second at 30fps)
            self.frame_count += 1
            if self.frame_count % 30 == 0:
                # Resize for faster detection (Use 0.5 instead of 0.25 for better accuracy)
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY) # Actually using gray
                
                # Tuned parameters:
                # - scaleFactor: 1.1 (Standard balance)
                # - minNeighbors: 4 (Standard balance)
                # - minSize: (30, 30) (Detect smaller faces)
                detected_faces = self.face_cascade.detectMultiScale(
                    rgb_small_frame, 
                    scaleFactor=1.1,
                    minNeighbors=4, 
                    minSize=(30, 30)
                )
                
                # Scale back up (multiply by 2 since we resized by 0.5)
                self.last_faces = []
                for (x, y, w, h) in detected_faces:
                    self.last_faces.append((x*2, y*2, w*2, h*2))

            # Draw results from last detection
            for (x, y, w, h) in self.last_faces:
                color = (0, 255, 0) if self.mode == "train" else (255, 0, 0)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # --- TRAINING MODE LOGIC ---
            if self.mode == "train":
                # Show instructions
                cv2.putText(frame, f"Captured: {self.saved_count} (Press 'c' to capture)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Check for 'c' press to capture
                # We handle 'q' globally later, but we need 'c' check here
                # actually, let's do one waitKey call per loop
                pass

            # Global Key Check
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.running = False
                break
            elif key == ord('c') and self.mode == "train":
                if len(self.last_faces) > 0:
                    (x, y, w, h) = self.last_faces[0] 
                    gray_capture = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    face_img = gray_capture[y:y+h, x:x+w]
                    import os
                    filename = f"{self.train_output_dir}/{self.person_name}.{int(time.time())}.{self.saved_count}.jpg"
                    cv2.imwrite(filename, face_img)
                    print(f"Captured {filename}")
                    self.saved_count += 1
                else:
                    print("No face detected to capture!")

            # --- RECOGNITION / WEBHOOK LOGIC (Run if NOT Training) ---
            if self.mode != "train":
                 # Check on detection update only (every 30 frames)
                 if self.frame_count % 30 == 0 and len(self.last_faces) > 0:
                    current_time = time.time()
                    
                    # Recognition Logic
                    recognized_name = None
                    if hasattr(self, 'recognizer'):
                        (x, y, w, h) = self.last_faces[0]
                        # We need full res gray frame for recognition
                        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        face_roi = gray_full[y:y+h, x:x+w]
                        try:
                            # Performance timing
                            t_start = time.time()
                            id, confidence = self.recognizer.predict(face_roi)
                            t_dur = time.time() - t_start
                            if t_dur > 0.1:
                                print(f"WARNING: Recognition took {t_dur:.3f}s")
                            
                            detected_name_candidate = self.names.get(id, "Unknown")
                            print(f"DEBUG: Predicted {detected_name_candidate} with distance {round(confidence)}")
                            
                            if confidence < 45: 
                                recognized_name = detected_name_candidate
                                cv2.putText(frame, f"{recognized_name} ({round(100-confidence)})", (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                            else:
                                cv2.putText(frame, "Unknown", (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        except Exception as e:
                            print(f"Prediction error: {e}")

                    # Stability Filter Logic
                    final_verified_name = None
                    
                    if recognized_name and recognized_name != "Unknown":
                        if recognized_name == self.last_recognized_candidate:
                            self.consecutive_recognition_count += 1
                        else:
                            self.consecutive_recognition_count = 1 
                            self.last_recognized_candidate = recognized_name
                            
                        print(f"DEBUG: Stability Check: {recognized_name} seen {self.consecutive_recognition_count} times.")
                        
                        if self.consecutive_recognition_count >= 2:
                            final_verified_name = recognized_name
                    else:
                        self.consecutive_recognition_count = 0
                        self.last_recognized_candidate = None

                    # Trigger Logic
                    if  current_time - self.last_trigger_time > self.trigger_cooldown:
                        if self.webhook_url and final_verified_name:
                             trigger_url = self.webhook_url
                             print(f"\nFACE VERIFIED STABLE: {final_verified_name}! Triggering Announcement.")
                             import urllib.parse
                             message = f"{final_verified_name} is at the door"
                             encoded_message = urllib.parse.quote(message)
                             
                             if "voicemonkey.io" in self.webhook_url and "trigger" in self.webhook_url:
                                 trigger_url = self.webhook_url.replace("trigger", "announce") + f"&text={encoded_message}"
                             else:
                                 trigger_url = self.webhook_url + f"&text={encoded_message}"
                             
                             self.last_trigger_time = current_time
                             threading.Thread(target=self._fire_webhook, args=(trigger_url,), daemon=True).start()

            # Display the frame
            cv2.imshow(self.window_name, frame)
            
    def _fire_webhook(self, url):
        try:
            with urllib.request.urlopen(url) as response:
                 print(f"Webhook triggered. Status: {response.getcode()}")
        except Exception as e:
            print(f"Failed to trigger webhook: {e}")
