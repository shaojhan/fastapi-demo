from http import HTTPStatus
from fastapi.testclient import TestClient

def test_read_main(client: TestClient):
    response = client.get('/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Hello World', 'root_path': '/api'}