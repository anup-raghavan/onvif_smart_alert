import os
from onvif import ONVIFCamera
import onvif

class OnvifClient:
    def __init__(self, ip, port, user, password, wsdl_dir=None):
        """
        Initialize the ONVIF client.
        :param ip: IP address of the camera
        :param port: ONVIF service port (default often 80)
        :param user: Username
        :param password: Password
        :param wsdl_dir: Directory containing WSDL files (optional, uses package default if None)
        """
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        if wsdl_dir:
            self.wsdl_dir = wsdl_dir
        else:
            # Robust extraction of wsdl directory
            import sys
            
            package_dir = os.path.dirname(onvif.__file__)
            # Candidates to check
            candidates = [
                os.path.join(package_dir, 'wsdl'), # Standard
                os.path.join(os.path.dirname(package_dir), 'wsdl'), # Sibling to package
                os.path.join(os.path.dirname(os.path.dirname(package_dir)), 'wsdl'), # One level up
                os.path.join(os.path.dirname(os.path.dirname(package_dir)), 'Lib', 'site-packages', 'wsdl'), # The weird case observed
                # Fallback: Absolute path if known (user specific, but safe to check)
                r"C:\Users\anup_\AppData\Roaming\Python\Lib\site-packages\wsdl"
            ]
            
            found = False
            for c in candidates:
                if os.path.isdir(c) and os.path.isfile(os.path.join(c, 'devicemgmt.wsdl')):
                    self.wsdl_dir = c
                    found = True
                    break
            
            if not found:
                # Last resort: fallback to standard and warn
                self.wsdl_dir = candidates[0]
                print(f"WARNING: Could not find 'wsdl' directory containing 'devicemgmt.wsdl'. Defaulting to {self.wsdl_dir}")
        self.camera = None
        self.media_service = None

    def connect(self):
        """
        Connect to the ONVIF Camera and initialize the Media Service.
        """
        print(f"Connecting to ONVIF Camera at {self.ip}:{self.port}...")
        
        # Helper to attempt connection
        def _attempt_connect(encrypt):
            print(f"DEBUG: Attempting connection with encrypt={encrypt}")
            camera = ONVIFCamera(
                self.ip, self.port, self.user, self.password, self.wsdl_dir,
                encrypt=encrypt, no_cache=True
            )
            # Force a simple call to verify connection works (GetDeviceInformation or services)
            # The constructor usually initializes devicemgmt, but let's be sure
            return camera

        try:
            # First attempt: Stanard WS-Security (encrypt=True)
            try:
                self.camera = _attempt_connect(encrypt=True)
            except Exception as e:
                print(f"DEBUG: Connection with encrypt=True failed: {e}")
                print("DEBUG: Retrying with encrypt=False (Digest/Basic)...")
                # Second attempt: Disable WS-Security (encrypt=False) - often required for some NVRs/Cameras
                self.camera = _attempt_connect(encrypt=False)
            
            # Create the media service
            self.media_service = self.camera.create_media_service()
            print("Successfully connected to Media Service.")
        except Exception as e:
            print(f"Failed to connect to ONVIF Camera: {e}")
            print("HINT: Unknown Fault often means Time Synchronization issue. Check if PC time matches Camera time.")
            raise

    def get_media_profiles(self):
        """
        Retrieve all available media profiles.
        """
        if not self.media_service:
            raise RuntimeError("Media service not initialized. Call connect() first.")
        
        try:
            print(" DEBUG: Requesting Media Profiles (GetProfiles)... this might take time on NVRs.")
            profiles = self.media_service.GetProfiles()
            print(f" DEBUG: Received {len(profiles)} profiles.")
            return profiles
        except Exception as e:
            print(f"Error retrieving media profiles: {e}")
            raise

    def get_video_sources(self):
        """
        Retrieve all available video sources (channels).
        """
        if not self.media_service:
            raise RuntimeError("Media service not initialized.")
        try:
            print(" DEBUG: Requesting Video Sources (GetVideoSources)...")
            sources = self.media_service.GetVideoSources()
            print(f" DEBUG: Received {len(sources)} video sources.")
            return sources
        except Exception as e:
            print(f"Error retrieving video sources: {e}")
            raise

    def get_profile_token_by_channel(self, channel_index):
        """
        Find a media profile token that corresponds to a specific channel index (0-based).
        """
        sources = self.get_video_sources()
        if not sources:
            raise RuntimeError("No video sources found on device.")
        
        if channel_index < 0 or channel_index >= len(sources):
            raise ValueError(f"Channel index {channel_index} out of range (Found {len(sources)} sources).")

        target_source_token = sources[channel_index].token
        print(f"Target Source for Channel {channel_index}: {target_source_token}")

        profiles = self.get_media_profiles()
        for p in profiles:
            # Check if profile is bound to the target video source
            if p.VideoSourceConfiguration and p.VideoSourceConfiguration.SourceToken == target_source_token:
                return p.token
        
        raise RuntimeError(f"No media profile found for channel {channel_index} (Source Token: {target_source_token})")

    def get_stream_uri(self, profile_token):
        """
        Get the RTSP Stream URI for a specific profile token.
        """
        if not self.media_service:
            raise RuntimeError("Media service not initialized.")
            
        try:
            # Create the request object for GetStreamUri
            # protocol='RTSP' is standard
            # stream_setup needs to be a dictionary or object matching the WSDL type
            # Force TCP (RTP/RTSP/TCP) if possible via Transport settings
            # Note: wsdl definition for TransportProtocol might be UDP, TCP, RTSP, HTTP.
            # Usually 'RTSP' implies standard RTSP. To force TCP transport, 
            # some clients request HTTP tunneling or specific headers.
            # But here we request the URI. The actual TCP enforcement happens at the Player (Client) side.
            # However, we can ask for 'RTSP' protocol.
            
            stream_setup = {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'
                }
            }
            
            req = self.media_service.create_type('GetStreamUri')
            req.ProfileToken = profile_token
            req.StreamSetup = stream_setup
            
            # Call the service
            res = self.media_service.GetStreamUri(req)
            return res.Uri
        except Exception as e:
            print(f"Error fetching Stream URI: {e}")
            raise
