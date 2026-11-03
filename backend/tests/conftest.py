import os, sys, tempfile
from pathlib import Path
os.environ['AIOS_DATA']=tempfile.mkdtemp(prefix='aios-tests-')
os.environ['AIOS_SESSION_TOKEN']='test-session-token'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, migrate
import app.main as main
@pytest.fixture
def client(monkeypatch):
    main.stop.set()
    Base.metadata.drop_all(engine);migrate();main.unlocked=False;main.requests.clear()
    # Tests control workers explicitly so assertions are deterministic.
    monkeypatch.setattr(main,'worker',lambda:None)
    with TestClient(app,headers={'Authorization':'Bearer test-session-token'}) as c:
        yield c
@pytest.fixture
def owner(client):
    assert client.post('/auth/setup',json={'password':'correct-horse-test-password'}).status_code==200
    return client
