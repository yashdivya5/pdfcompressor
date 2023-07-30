import os
import requests
from typing import Any, BinaryIO, Literal

class ILovePDF:
    def __init__(self, public_key: str, debug: bool = False):
        self.public_key = public_key
        self.api_version = "v1"
        self.start_server = "api.ilovepdf.com"
        self.working_server = ""
        self.debug = debug
        self.headers = None
        self.auth()

    def auth(self):
        payload = {"public_key": self.public_key}
        response = self._send_request("post", endpoint="auth", payload=payload)
        self.headers = {"Authorization": f"Bearer {response.json()['token']}"}

    def _send_request(self, method: Literal["get", "post", "delete"], endpoint: str, payload: dict = None,
                      files: dict = None, stream: bool = False):
        server = self.working_server or self.start_server
        payload = payload or {}
        url = f"https://{server}/{self.api_version}/{endpoint}"
        if self.debug:
            payload["debug"] = True
        response = getattr(requests, method)(url, data=payload, headers=self.headers, files=files, stream=stream)

        if not response.ok:
            raise ValueError(f"Error: {response.url} returned status code {response.status_code}, "
                             f"reason: '{response.reason}'. Full response text is: '{response.text}'")

        return response


class Task(ILovePDF):
    def __init__(self, public_key: str, tool: str, verbose: bool = False, **kwargs: Any):
        super().__init__(public_key, **kwargs)
        self.files = {}
        self._task_id = ""
        self._process_response = None
        self.verbose = verbose
        self.tool = tool
        self.process_params = {
            "tool": tool,
            "ignore_password": True,
            "output_filename": "{n}-{filename}-{app}",
            "packaged_filename": "{app}ed-PDFs",
        }
        self.start()

    def start(self):
        response = self._send_request("get", f"start/{self.tool}").json()
        if response:
            self.working_server = response["server"]
            self._task_id = response["task"]
        else:
            print("Warning: Starting this task returned empty JSON response. Was likely already started.")

    def add_file(self, file_path: str):
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"'{file_path}' does not exist")

        if file_path in self.files:
            print(f"Warning: File '{file_path}' was already added to this task.")

        self.files[file_path] = ""

    def upload(self):
        payload = {"task": self._task_id}
        for filename in self.files:
            with open(filename, "rb") as file:
                response = self._send_request("post", "upload", payload=payload, files={"file": file}).json()
            self.files[filename] = response["server_filename"]

        return self.files

    def process(self):
        if self.verbose:
            print("Uploading file(s)...")
        self.upload()
        payload = self.process_params.copy()
        payload["task"] = self._task_id

        for idx, (filename, server_filename) in enumerate(self.files.items()):
            payload[f"files[{idx}][filename]"] = filename
            payload[f"files[{idx}][server_filename]"] = server_filename

        response = self._send_request("post", "process", payload=payload).json()
        self._process_response = response
        n_files = response["output_filenumber"]

        assert len(self.files) == response["output_filenumber"], (
            f"Unexpected file count mismatch: task received {len(self.files)} files "
            f"for processing, but only {n_files} were downloaded from server."
        )

        if self.verbose:
            print(f"File(s) uploaded and processed!\n{response = }")

        return response

    def download(self, save_to_dir: str = None):
        if not self._process_response:
            raise ValueError("You called task.download() but there are no files to download")

        endpoint = f"download/{self._task_id}"
        response = self._send_request("get", endpoint, stream=True)

        save_to_dir = save_to_dir or os.getcwd()
        os.makedirs(save_to_dir, exist_ok=True)

        file_path = os.path.join(save_to_dir, self._process_response["download_filename"])

        with open(file_path, "wb") as file:
            file.write(response.content)

        return file_path

    def delete_current_task(self):
        if not self._task_id:
            print("Warning: You're trying to delete a task that was never started")
            return

        self._send_request("delete", f"task/{self._task_id}")
        self._task_id = ""
        self._process_response = None


class Compress(Task):
    def __init__(self, public_key: str, compression_level: str = "recommended", **kwargs: Any):
        super().__init__(public_key, tool="compress", **kwargs)
        assert compression_level in ("low", "recommended", "extreme"), f"Invalid {compression_level=}, " \
                                                                       f"must be one of ('low', 'recommended', 'extreme')"
        self.process_params["compression_level"] = compression_level