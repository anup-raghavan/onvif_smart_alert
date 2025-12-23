import sys
import argparse
import getpass
import socket
import datetime
from onvif_client import OnvifClient
from stream_player import StreamPlayer

# Set global timeout to prevent infinite hangs
socket.setdefaulttimeout(10.0)

def main():
    print(f"Current System Time: {datetime.datetime.now()}")
    parser = argparse.ArgumentParser(description="Python ONVIF IP Camera Live Viewer")
    parser.add_argument("--ip", help="Camera IP address")
    parser.add_argument("--port", type=int, default=80, help="ONVIF port (default: 80)")
    parser.add_argument("--user", help="Username")
    parser.add_argument("--password", help="Password")
    parser.add_argument("--channel", type=int, help="NVR Channel Number (1-based index)")
    parser.add_argument("--webhook-url", help="URL to trigger (GET request) when a face is detected")
    parser.add_argument("--train", help="Enable Training Mode and specify the name of the person to capture")
    parser.add_argument("--person", help="Name of the person to recognize (Detect Mode)")
    parser.add_argument("--trainer", default="trainer.yml", help="Path to trainer.yml file (default: trainer.yml)")

    args = parser.parse_args()

    # Force OpenCV to use TCP for RTSP (Fixes corruption/drop issues)
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

    # Interactive input if arguments are missing
    ip = args.ip if args.ip else input("Camera IP: ")
    port = args.port # Default already set, but logic below allows override if needed
    if not args.port and not args.ip: # If nothing provided, maybe ask for port too? 
        # But if args.port has default, it is always present.
        # Let's simple check if user wants to change default if interactive
        pass 
        
    user = args.user if args.user else input("Username: ")
    password = args.password if args.password else getpass.getpass("Password: ")

    print(f"\nInitializing ONVIF Client for {ip}:{port}...")
    client = OnvifClient(ip, port, user, password)

    try:
        client.connect()
    except Exception as e:
        print(f"FATAL: Could not connect to camera: {e}")
        sys.exit(1)

    try:
        if args.channel:
            print(f"Selecting profile for Channel {args.channel}...")
            # Convert 1-based channel to 0-based index
            selected_token = client.get_profile_token_by_channel(args.channel - 1)
            print(f"Selected Token for Channel {args.channel}: {selected_token}")
        else:
            print("Retrieving media profiles...")
            profiles = client.get_media_profiles()
            if not profiles:
                print("No media profiles found on device.")
                sys.exit(1)
            
            # Select the first profile for now (Requirement FR-2)
            # Often connection quality is better on sub streams for testing, but requirement says "first available or main"
            # Usually the first one is main.
            selected_profile = profiles[0]
            print(f"Selected Profile:: Name: {selected_profile.Name}, Token: {selected_profile.token}")
            selected_token = selected_profile.token

        print("Requesting Stream URI...")
        uri = client.get_stream_uri(selected_token)
        print(f"Stream URI retrieved: {uri}")
        
    except Exception as e:
        print(f"FATAL: Error during ONVIF setup: {e}")
        sys.exit(1)

    print("\nStarting Video Stream...")
    print("Press 'q' in the video window to exit.")
    if args.webhook_url:
        print(f"Face Detection Webhook Enabled: {args.webhook_url}")
    
    mode = "train" if args.train else "detect"
    person_to_use = args.train if args.train else args.person
    
    # If explicit training mode, output to dataset folder
    
    player = StreamPlayer(
        uri, 
        webhook_url=args.webhook_url, 
        mode=mode,
        train_output_dir="dataset" if mode == "train" else None,
        trainer_file=args.trainer,
        person_name=person_to_use if person_to_use else "Person"
    )
    try:
        # Run blocking loop in main thread
        player.run()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        player.stop()
        print("Exiting application.")

if __name__ == "__main__":
    main()
