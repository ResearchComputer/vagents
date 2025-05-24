import requests
import importlib
import dill
import json # Added import

class VClient():
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        # api_key is initialized but not used in the provided snippet
    
    def register_module(self, path: str, force: bool = False, mcp_configs: list | None = None) : # Added mcp_configs
        """
        Register a module with the server.
        """
        module_path, class_name = path.split(":")
        try:
            module = importlib.import_module(module_path)
            class_obj = getattr(module, class_name)
        except ImportError as e:
            raise ImportError(f"Module {module_path} not found. Error: {e}")
        
        bytestream: bytes = dill.dumps(class_obj)
        
        # Prepare multipart form data
        files_payload = {'module_content': bytestream}
        data_payload = {'force': str(force).lower()} # Send force as string 'true'/'false'

        if mcp_configs is not None:
            data_payload['mcp_configs'] = json.dumps(mcp_configs)

        headers = {
            # "Content-Type" will be set by requests for multipart/form-data
            "Accept": "application/json",
        }
        
        response = requests.post(
            f"{self.base_url}/api/modules",
            headers=headers,
            files=files_payload, # Send bytestream as a file
            data=data_payload    # Send other data like force and mcp_configs
        )
        if response.status_code == 200:
            print("Module registered successfully.")
        else:
            print(f"Failed to register module. Status code: {response.status_code}")
            print(f"Response: {response.text}")

    def call_response_handler(self, request_data: dict):
        """
        Call the response_handler endpoint on the server.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        response = requests.post(
            f"{self.base_url}/v1/responses",
            headers=headers,
            json=request_data,
        )
        if response.status_code == 200:
            # Handle streaming and non-streaming responses
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                for line in response.iter_lines():
                    if line:
                        print(line.decode('utf-8')) # Or process the stream as needed
            else:
                print("Response received successfully.")
                print(f"Response: {response.json()}")
        else:
            print(f"Failed to call response_handler. Status code: {response.status_code}")
            print(f"Response: {response.text}")