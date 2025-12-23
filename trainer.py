import cv2
import os
import numpy as np

import json

def train_model(data_dir="dataset", model_file="trainer.yml", map_file="names.json"):
    path = data_dir
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    
    imagePaths = [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.jpg') or f.endswith('.png')]     
    faceSamples=[]
    ids = []
    
    # Mapping of Name -> ID
    name_to_id = {}
    current_id = 0
    
    print(f"Training on {len(imagePaths)} images...")
    
    for imagePath in imagePaths:
        try:
            # Filename format expected: Name.Timestamp.Count.jpg
            # User might have legacy files or different formats.
            filename = os.path.split(imagePath)[-1]
            name = filename.split(".")[0]
            
            if name == "user":
                # Legacy or default name, let's treat it as "Unknown" or ask user to rename
                # For now, we'll map it to "Person 1" or similar if we strictly need names
                name = "User"
            
            if name not in name_to_id:
                current_id += 1
                name_to_id[name] = current_id
            
            id_ = name_to_id[name]
            
            PIL_img = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
            img_numpy = np.array(PIL_img,'uint8')
            
            faceSamples.append(img_numpy)
            ids.append(id_)
        except Exception as e:
            print(f"Skipping {imagePath}: {e}")

    if len(faceSamples) == 0:
        print("No training data found.")
        return

    print(f"Detected {len(name_to_id)} unique people: {list(name_to_id.keys())}")
    
    print("Training model...")
    recognizer.train(faceSamples, np.array(ids))
    recognizer.write(model_file)
    print(f"Model saved to {model_file}")
    
    # Save the mapping (ID -> Name) for the player
    # We invert it for easier lookup: ID -> Name
    id_to_name = {v: k for k, v in name_to_id.items()}
    with open(map_file, 'w') as f:
        json.dump(id_to_name, f)
    print(f"Name mapping saved to {map_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--datadir", default="dataset", help="Directory containing face images")
    parser.add_argument("--savefile", default="trainer.yml", help="File to save trained model")
    args = parser.parse_args()
    
    if not os.path.exists(args.datadir):
        print(f"Error: {args.datadir} does not exist.")
    else:
        train_model(args.datadir, args.savefile)
