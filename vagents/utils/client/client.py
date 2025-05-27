import requests
import importlib
import dill
import json # Added import

class VClient():
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
            
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

        headers: dict[str, str] = {
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
        
        should_stream = request_data.get("stream", False)
        print(f"[VClient] Making request to {self.base_url}/v1/responses with stream={should_stream}")

        response = requests.post(
            f"{self.base_url}/v1/responses",
            headers=headers,
            json=request_data,
            stream=should_stream
        )
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "application/x-ndjson" in content_type:
                processed_chunks = 0
                try:
                    for line_bytes in response.iter_lines():
                        if line_bytes:
                            line_str = line_bytes.decode('utf-8')
                            try:
                                json_chunk = json.loads(line_str)
                                print(f"Stream chunk: {json_chunk}")
                                processed_chunks += 1
                            except json.JSONDecodeError as e:
                                print(f"Error decoding JSON from stream line: '{line_str}', Error: {e}")
                    if processed_chunks == 0:
                        print("Stream did not yield any complete JSON data lines.")

                except requests.exceptions.ChunkedEncodingError as e:
                    print(f"ChunkedEncodingError during streaming: {e}")
                except Exception as e:
                    print(f"Generic error during streaming: {e}")
                finally:
                    if processed_chunks > 0:
                        print(f"Finished processing stream. Total JSON objects processed: {processed_chunks}")
            elif "application/json" in content_type: # Non-streaming JSON
                print("Non-streaming JSON response received successfully.")
                print(f"Response: {response.json()}")
        else:
            print(f"Failed to call response_handler. Status code: {response.status_code}")
            print(f"Response: {response.text}")