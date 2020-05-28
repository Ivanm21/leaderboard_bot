from google.cloud import secretmanager
import os

class Gcloud:


    def __init__(self, project_id=None):
        self.project_id = project_id

    def access_secret_version(self, project_id=None, secret_id='TELEGRAM_TOKEN', version_id='latest'):
        """
        Access the payload for the given secret version if one exists. The version
        can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
        """

        if not project_id: 
            project_id = self.project_id
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret version.
        name = client.secret_version_path(project_id, secret_id, version_id)

        # Access the secret version.
        response = client.access_secret_version(name)

        # snippet is showing how to access the secret material.
        payload = response.payload.data.decode('UTF-8')
        return payload
